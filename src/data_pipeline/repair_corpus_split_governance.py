"""One-off corpus repair, seed-cap enforcement, stratified split, and
manifest composition for Phase 38 (Corpus Repair & Split Governance).

Pools the main synthetic corpus with the reserved test split, repairs
case-mismatched evidence spans, caps seed_id concentration at a stated
percentage of the final corpus, assigns each seed_id's whole row-group to
train/val/test via a deterministic SHA-256 hash (never RNG), and composes a
manifest that extends the project's existing SHA-256 manifest pattern
without modifying the shared ManifestEntry/ManifestFile schema.

This is a one-time repair script, not a permanent addition to the
generation-time validators (see 38-CONTEXT.md).
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from src.data_pipeline.processing.dedup import lexical_dedup
from src.data_pipeline.processing.splitter import _stable_bucket
from src.data_pipeline.schemas import DatasetRecord
from src.data_pipeline.versioning.manifest import build_manifest

# Deterministic-order salt used only to pick a stable, reproducible ordering
# of lexical_dedup's survivors when trimming an over-cap seed group. Not
# related to the split-assignment salt.
_SEED_CAP_ORDER_SALT = "phase38-corpus-repaired-v2-seed-cap-order"

_LABELS = ("bank_impersonation", "zalo_social_engineering", "task_scam", "benign")


def pool_records(paths: list[Path]) -> list[dict[str, Any]]:
    """Read and concatenate JSONL rows from the given files, in order.

    Every original field is preserved; rows are plain dicts (no
    DatasetRecord validation here — validation happens at write time).
    """
    records: list[dict[str, Any]] = []
    for path in paths:
        with Path(path).open("r", encoding="utf-8") as handle:
            for line in handle:
                stripped = line.strip()
                if not stripped:
                    continue
                records.append(json.loads(stripped))
    return records


def repair_evidence_spans(record: dict[str, Any]) -> dict[str, Any] | None:
    """Repair a record's suspicious_spans against its text.

    - A span that is already an exact substring of text is kept unchanged.
    - A span with only a case-insensitive match in text is re-extracted to
      the exact-cased substring found in text.
    - A span with no match in text even case-insensitively is dropped.
    - If zero spans survive, the row is dropped entirely (returns None) —
      an empty span list is never returned for a surviving row.
    """
    text = record["text"]
    repaired_spans: list[str] = []

    for span in record.get("suspicious_spans", []):
        if span in text:
            repaired_spans.append(span)
            continue
        index = text.lower().find(span.lower())
        if index >= 0:
            repaired_spans.append(text[index : index + len(span)])
        # else: unrecoverable, drop this individual span

    if not repaired_spans:
        return None

    repaired = dict(record)
    repaired["suspicious_spans"] = repaired_spans
    return repaired


def repair_all_evidence_spans(
    records: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Repair evidence spans for every record, aggregating repair stats."""
    survivors: list[dict[str, Any]] = []
    rows_span_repaired = 0
    rows_dropped_unrecoverable_span = 0

    for record in records:
        repaired = repair_evidence_spans(record)
        if repaired is None:
            rows_dropped_unrecoverable_span += 1
            continue
        if repaired["suspicious_spans"] != record.get("suspicious_spans", []):
            rows_span_repaired += 1
        survivors.append(repaired)

    stats = {
        "rows_pooled": len(records),
        "rows_span_repaired": rows_span_repaired,
        "rows_dropped_unrecoverable_span": rows_dropped_unrecoverable_span,
    }
    return survivors, stats


def enforce_seed_cap(
    records: list[dict[str, Any]],
    cap_pct: float = 0.08,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Trim seed_id groups exceeding cap_pct of the corpus.

    Repeatedly finds the seed_id with the largest current over-cap share
    (recomputed against the CURRENT total after every trim, since trimming
    shrinks the denominator), uses lexical_dedup to identify near-duplicates
    within that group, orders the deduped survivors deterministically via
    _stable_bucket, and truncates to cap_pct * current_total. Repeats until
    no seed_id exceeds cap_pct.
    """
    current: list[dict[str, Any]] = list(records)
    seed_concentration_before: dict[str, float] = {}
    rows_dropped_seed_cap = 0

    while True:
        total = len(current)
        if total == 0:
            break

        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for record in current:
            groups[record["seed_id"]].append(record)

        worst_seed_id: str | None = None
        worst_share = cap_pct
        for seed_id, group in groups.items():
            share = len(group) / total
            if share > worst_share:
                worst_share = share
                worst_seed_id = seed_id

        if worst_seed_id is None:
            break

        if worst_seed_id not in seed_concentration_before:
            seed_concentration_before[worst_seed_id] = worst_share

        group = groups[worst_seed_id]
        deduped = lexical_dedup(group, threshold=0.95)
        ordered = sorted(
            deduped,
            key=lambda record: (
                _stable_bucket(record["text"], _SEED_CAP_ORDER_SALT),
                record["text"],
            ),
        )
        target_count = int(cap_pct * total)
        survivors = ordered[:target_count]
        rows_dropped_seed_cap += len(group) - len(survivors)

        current = [record for record in current if record["seed_id"] != worst_seed_id] + survivors

    final_total = len(current)
    final_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in current:
        final_groups[record["seed_id"]].append(record)

    seed_concentration_after = {
        seed_id: (len(final_groups.get(seed_id, [])) / final_total if final_total else 0.0)
        for seed_id in seed_concentration_before
    }

    stats = {
        "seed_concentration_before": seed_concentration_before,
        "seed_concentration_after": seed_concentration_after,
        "rows_dropped_seed_cap": rows_dropped_seed_cap,
    }
    return current, stats


def assign_stratified_group_split(
    records: list[dict[str, Any]],
    ratios: tuple[float, float, float] = (0.8, 0.1, 0.1),
    salt: str = "phase38-corpus-repaired-v2",
) -> dict[str, str]:
    """Assign each seed_id's whole row-group to train/val/test.

    Seed groups are ordered deterministically via a SHA-256 hash bucket
    (never random.shuffle). Each group is greedily assigned to whichever
    split currently minimizes deviation from the corpus's OBSERVED global
    per-class proportions (not a hardcoded 25% each), subject to each
    split's running row-count staying near its ratios-derived target. Every
    row of a given seed_id always goes to the same split.
    """
    split_names = ("train", "val", "test")
    total_rows = len(records)
    target_rows = {name: total_rows * ratio for name, ratio in zip(split_names, ratios, strict=True)}

    seed_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        seed_groups[record["seed_id"]].append(record)

    labels = sorted({record["label"] for record in records})
    global_label_counts: dict[str, int] = defaultdict(int)
    for record in records:
        global_label_counts[record["label"]] += 1
    global_proportions = {
        label: (global_label_counts[label] / total_rows if total_rows else 0.0) for label in labels
    }

    ordered_seed_ids = sorted(seed_groups, key=lambda sid: (_stable_bucket(sid, salt), sid))

    running_rows: dict[str, int] = {name: 0 for name in split_names}
    running_class_counts: dict[str, dict[str, int]] = {name: defaultdict(int) for name in split_names}
    assignments: dict[str, str] = {}

    for seed_id in ordered_seed_ids:
        rows = seed_groups[seed_id]
        group_label_counts: dict[str, int] = defaultdict(int)
        for record in rows:
            group_label_counts[record["label"]] += 1

        eligible = [
            name
            for name in split_names
            if running_rows[name] + len(rows) <= target_rows[name] * 1.05
        ]
        if not eligible:
            # Every split is already at/over its tolerance-adjusted budget —
            # last-resort: consider all splits so the group is still placed.
            eligible = list(split_names)

        best_split: str | None = None
        best_score = float("inf")
        for name in eligible:
            hypothetical = dict(running_class_counts[name])
            for label, count in group_label_counts.items():
                hypothetical[label] = hypothetical.get(label, 0) + count
            hyp_total = running_rows[name] + len(rows)
            score = (
                sum(
                    abs(hypothetical.get(label, 0) / hyp_total - global_proportions.get(label, 0.0))
                    for label in labels
                )
                if hyp_total
                else 0.0
            )
            if score < best_score:
                best_split, best_score = name, score

        assert best_split is not None
        assignments[seed_id] = best_split
        running_rows[best_split] += len(rows)
        for label, count in group_label_counts.items():
            running_class_counts[best_split][label] += count

    return assignments


def build_repair_manifest(
    splits_dir: Path,
    version_tag: str,
    split_class_counts: dict[str, dict[str, int]],
    repair_stats: dict[str, Any],
) -> dict[str, Any]:
    """Compose a repair-phase manifest around the existing build_manifest().

    Calls build_manifest() from versioning/manifest.py UNCHANGED to get the
    SHA-256/records/bytes part, then wraps it with extra repair-phase fields
    rather than modifying the shared ManifestEntry/ManifestFile models.
    """
    base_manifest = build_manifest(Path(splits_dir), version_tag)
    return {
        "manifest": json.loads(base_manifest.model_dump_json()),
        "split_class_distribution": split_class_counts,
        "repair_stats": repair_stats,
    }


def _compute_split_class_counts(
    splits: dict[str, list[dict[str, Any]]],
) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = {}
    for split_name, split_records in splits.items():
        split_counts: dict[str, int] = defaultdict(int)
        for record in split_records:
            split_counts[record["label"]] += 1
        counts[split_name] = dict(split_counts)
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Pool, repair, cap, split, and manifest the Phase 38 corpus."
    )
    parser.add_argument(
        "--input-main", type=Path, default=Path("data/synthetic/recovered-balanced.jsonl")
    )
    parser.add_argument(
        "--input-reserved", type=Path, default=Path("data/splits/recovered-balanced/test.jsonl")
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path("data/splits/phase38-corpus-repaired-v2")
    )
    parser.add_argument("--version-tag", type=str, default="phase38-corpus-repaired-v2")
    parser.add_argument("--cap-pct", type=float, default=0.08)
    parser.add_argument("--split-ratios", type=str, default="0.8,0.1,0.1")
    args = parser.parse_args()

    ratios_list = [float(part) for part in args.split_ratios.split(",")]
    ratios: tuple[float, float, float] = (ratios_list[0], ratios_list[1], ratios_list[2])

    pooled = pool_records([args.input_main, args.input_reserved])
    repaired, repair_stats = repair_all_evidence_spans(pooled)
    capped, cap_stats = enforce_seed_cap(repaired, cap_pct=args.cap_pct)
    repair_stats.update(cap_stats)

    assignments = assign_stratified_group_split(capped, ratios=ratios, salt=args.version_tag)

    splits: dict[str, list[dict[str, Any]]] = {"train": [], "val": [], "test": []}
    for record in capped:
        splits[assignments[record["seed_id"]]].append(record)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    for split_name, split_records in splits.items():
        output_path = args.output_dir / f"{split_name}.jsonl"
        with output_path.open("w", encoding="utf-8") as handle:
            for record in split_records:
                validated = DatasetRecord.model_validate(record)
                handle.write(validated.model_dump_json() + "\n")

    split_class_counts = _compute_split_class_counts(splits)
    manifest_payload = build_repair_manifest(
        args.output_dir, args.version_tag, split_class_counts, repair_stats
    )

    manifest_path = Path("data/manifests") / f"manifest-{args.version_tag}.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("w", encoding="utf-8") as handle:
        json.dump(manifest_payload, handle, indent=2, ensure_ascii=False)

    print(f"Pooled {repair_stats['rows_pooled']} rows")
    print(f"Span-repaired {repair_stats['rows_span_repaired']} rows")
    print(f"Dropped {repair_stats['rows_dropped_unrecoverable_span']} unrecoverable-span rows")
    print(f"Dropped {repair_stats.get('rows_dropped_seed_cap', 0)} seed-cap rows")
    for split_name in ("train", "val", "test"):
        print(f"{split_name}: {len(splits[split_name])} rows")
    print(f"Manifest written to {manifest_path}")


if __name__ == "__main__":
    main()
