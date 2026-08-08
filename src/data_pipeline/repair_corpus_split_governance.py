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

from src.data_pipeline.generation.zalo_codex_recovery import BUILD_METADATA
from src.data_pipeline.processing.dedup import fuzz
from src.data_pipeline.processing.dedup import lexical_dedup
from src.data_pipeline.processing.normalizer import normalize_text
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


def _normalized_text(text: str) -> str:
    return normalize_text(text).casefold()


def validate_replacement_records(
    records: list[dict[str, Any]],
    replacement_label: str,
) -> list[dict[str, Any]]:
    """Validate a replacement completely before the original pool is changed."""
    if not records:
        raise ValueError("replacement input is empty")

    validated: list[dict[str, Any]] = []
    normalized_texts: list[str] = []
    seen_normalized: set[str] = set()
    for index, record in enumerate(records):
        try:
            payload = DatasetRecord.model_validate(record).model_dump()
        except Exception as exc:
            raise ValueError(f"replacement row {index} is not schema-valid: {exc}") from exc
        if payload["label"] != replacement_label:
            raise ValueError(
                f"replacement row {index} has label {payload['label']!r}, expected {replacement_label!r}"
            )
        if payload["source"] != BUILD_METADATA["schema_source"]:
            raise ValueError(
                f"replacement row {index} has source {payload['source']!r}, "
                f"expected {BUILD_METADATA['schema_source']!r}"
            )
        if not payload["suspicious_spans"] or any(
            not span or span not in payload["text"] for span in payload["suspicious_spans"]
        ):
            raise ValueError(f"replacement row {index} has an invalid evidence span")

        normalized = _normalized_text(payload["text"])
        if normalized in seen_normalized:
            raise ValueError(f"replacement row {index} duplicates normalized text")
        seen_normalized.add(normalized)
        normalized_texts.append(normalized)
        validated.append(payload)

    for left_index, left in enumerate(normalized_texts):
        for right_index in range(left_index + 1, len(normalized_texts)):
            ratio = fuzz.ratio(left, normalized_texts[right_index]) / 100.0
            if ratio >= 0.95:
                raise ValueError(
                    f"replacement rows {left_index} and {right_index} are lexical near-duplicates "
                    f"({ratio:.3f})"
                )

    unique_seeds = {record["seed_id"] for record in validated}
    if len(unique_seeds) < 3:
        raise ValueError("replacement must contain at least three distinct seed groups")
    return validated


def replace_label_records(
    pooled: list[dict[str, Any]],
    replacement: list[dict[str, Any]],
    replacement_label: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Atomically remove one old label population and append its replacement."""
    validated = validate_replacement_records(replacement, replacement_label)
    retained = [record for record in pooled if record.get("label") != replacement_label]
    removed_count = len(pooled) - len(retained)
    if removed_count == 0:
        raise ValueError(f"source pool has no rows for replacement label {replacement_label!r}")

    retained_normalized = [_normalized_text(record["text"]) for record in retained]
    for replacement_index, record in enumerate(validated):
        candidate = _normalized_text(record["text"])
        for retained_index, existing in enumerate(retained_normalized):
            if fuzz.ratio(candidate, existing) / 100.0 >= 0.95:
                raise ValueError(
                    "replacement row "
                    f"{replacement_index} duplicates retained row {retained_index} at the lexical threshold"
                )

    unique_seed_count = len({record["seed_id"] for record in validated})
    stats = {
        "source_rows_pooled": len(pooled),
        "replacement_label": replacement_label,
        "old_label_rows_removed": removed_count,
        "replacement_rows_added": len(validated),
        "replacement_unique_seed_count": unique_seed_count,
        "generation_provenance": dict(BUILD_METADATA),
        "external_api_call_count": 0,
    }
    if replacement_label == "zalo_social_engineering":
        stats["old_zalo_rows_removed"] = removed_count
    return retained + validated, stats


def deduplicate_normalized_records(
    records: list[dict[str, Any]],
    threshold: float = 0.95,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Drop global normalized exact/lexical duplicates before splitting."""
    survivors: list[dict[str, Any]] = []
    survivor_texts: list[str] = []
    for record in records:
        normalized = _normalized_text(record["text"])
        if any(fuzz.ratio(normalized, seen) / 100.0 >= threshold for seen in survivor_texts):
            continue
        survivors.append(record)
        survivor_texts.append(normalized)
    return survivors, {"rows_dropped_global_lexical_duplicate": len(records) - len(survivors)}


def repair_evidence_spans(record: dict[str, Any]) -> dict[str, Any] | None:
    """Repair a record's suspicious_spans against its text.

    - A span that is already an exact substring of text is kept unchanged.
    - A span with only a case-insensitive match in text is re-extracted to
      the exact-cased substring found in text.
    - A span with no match in text even case-insensitively is dropped.
    - If the record ORIGINALLY had one or more spans and zero survive
      repair, the row is dropped entirely (returns None) — this is the
      "unrecoverable evidence" case DATA-06 targets.
    - If the record ORIGINALLY had zero spans (e.g. a `benign` row, where
      `suspicious_spans` legitimately defaults to `[]` per
      `DatasetRecord.suspicious_spans`'s schema default), the row is kept
      unchanged with its empty span list — this is not an invalid-span row,
      it never had evidence spans to repair.
    """
    text = record["text"]
    original_spans = record.get("suspicious_spans", [])
    repaired_spans: list[str] = []

    for span in original_spans:
        if span in text:
            repaired_spans.append(span)
            continue
        index = text.lower().find(span.lower())
        if index >= 0:
            repaired_spans.append(text[index : index + len(span)])
        # else: unrecoverable, drop this individual span

    if original_spans and not repaired_spans:
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

    seed_concentration_before records each over-cap seed_id's share against
    the ORIGINAL (pre-any-trim) total whenever that seed was already over
    cap_pct at the start — matching the real, reportable "how skewed was
    this seed before any repair work" figure (e.g. the real 24.41%/11.90%
    pooled measurements in 38-RESEARCH.md), not an intermediate value
    already deflated/inflated by earlier seeds' trims. A seed that only
    crosses cap_pct later, purely because trimming other seeds shrank the
    denominator, records its share at first-detection time instead (there is
    no earlier "true" over-cap share to report for that seed).
    """
    current: list[dict[str, Any]] = list(records)
    initial_total = len(current)
    seed_concentration_before: dict[str, float] = {}
    if initial_total:
        initial_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for record in current:
            initial_groups[record["seed_id"]].append(record)
        for seed_id, group in initial_groups.items():
            share = len(group) / initial_total
            if share > cap_pct:
                seed_concentration_before[seed_id] = share
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

    _ensure_label_support(assignments, seed_groups, ratios, salt)
    return assignments


def _ensure_label_support(
    assignments: dict[str, str],
    seed_groups: dict[str, list[dict[str, Any]]],
    ratios: tuple[float, float, float],
    salt: str,
) -> None:
    """Move whole groups only when an adequately diverse label is absent.

    The main greedy pass normally provides support naturally.  This bounded
    repair makes that property explicit without ever falling back to row-level
    splitting.  Candidate moves must leave every label in the donor split.
    """
    split_names = ("train", "val", "test")
    active_splits = [name for name, ratio in zip(split_names, ratios, strict=True) if ratio > 0]
    labels = sorted({record["label"] for rows in seed_groups.values() for record in rows})
    labels_by_seed = {
        seed_id: {record["label"] for record in rows} for seed_id, rows in seed_groups.items()
    }

    for label in labels:
        label_seeds = [seed_id for seed_id, group_labels in labels_by_seed.items() if label in group_labels]
        if len(label_seeds) < len(active_splits):
            continue

        for missing_split in active_splits:
            if any(assignments[seed_id] == missing_split for seed_id in label_seeds):
                continue

            candidates: list[str] = []
            for seed_id in label_seeds:
                donor = assignments[seed_id]
                donor_seed_ids = [sid for sid, split_name in assignments.items() if split_name == donor]
                if all(
                    any(other != seed_id and other_label in labels_by_seed[other] for other in donor_seed_ids)
                    for other_label in labels_by_seed[seed_id]
                ):
                    candidates.append(seed_id)

            if not candidates:
                raise ValueError(
                    f"cannot provide whole-seed support for {label!r} in {missing_split!r}"
                )
            selected = min(
                candidates,
                key=lambda seed_id: (
                    len(seed_groups[seed_id]),
                    _stable_bucket(seed_id, f"{salt}:label-support:{label}:{missing_split}"),
                    seed_id,
                ),
            )
            assignments[selected] = missing_split


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
    """Per-split, per-class row counts, always reporting all four labels.

    A label with zero surviving rows in a given split (e.g. a label whose
    entire seed-group population collapses to a single seed_id after
    capping, forcing group-integrity-preserving assignment to place it in
    only one split) is recorded explicitly as 0 rather than omitted — the
    manifest must be able to answer "how many rows of label X are in split
    Y" for all four labels in every split, even when the honest answer is
    zero.
    """
    counts: dict[str, dict[str, int]] = {}
    for split_name, split_records in splits.items():
        split_counts: dict[str, int] = {label: 0 for label in _LABELS}
        for record in split_records:
            split_counts[record["label"]] += 1
        counts[split_name] = split_counts
    return counts


def _write_splits_atomically(
    output_dir: Path,
    splits: dict[str, list[dict[str, Any]]],
) -> None:
    """Validate every row first, then replace all versioned split files."""
    validated_splits = {
        split_name: [DatasetRecord.model_validate(record).model_dump() for record in records]
        for split_name, records in splits.items()
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    temporary_paths: dict[str, Path] = {}
    for split_name, records in validated_splits.items():
        temporary = output_dir / f".{split_name}.jsonl.tmp"
        with temporary.open("w", encoding="utf-8", newline="\n") as handle:
            for record in records:
                handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
        temporary_paths[split_name] = temporary
    for split_name, temporary in temporary_paths.items():
        temporary.replace(output_dir / f"{split_name}.jsonl")


def _parse_split_ratios(value: str) -> tuple[float, float, float]:
    try:
        ratios = tuple(float(part) for part in value.split(","))
    except ValueError as exc:
        raise ValueError("split ratios must be three comma-separated numbers") from exc
    if len(ratios) != 3 or any(ratio < 0 for ratio in ratios):
        raise ValueError("split ratios must contain exactly three non-negative values")
    if abs(sum(ratios) - 1.0) > 1e-9:
        raise ValueError("split ratios must sum to 1.0")
    return ratios  # type: ignore[return-value]


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
    parser.add_argument("--replacement-input", type=Path)
    parser.add_argument("--replacement-label", choices=_LABELS)
    parser.add_argument(
        "--output-dir", type=Path, default=Path("data/splits/phase38-corpus-repaired-v2")
    )
    parser.add_argument("--version-tag", type=str, default="phase38-corpus-repaired-v2")
    parser.add_argument("--cap-pct", type=float, default=0.08)
    parser.add_argument("--split-ratios", type=str, default="0.8,0.1,0.1")
    args = parser.parse_args()

    if (args.replacement_input is None) != (args.replacement_label is None):
        parser.error("--replacement-input and --replacement-label must be supplied together")
    try:
        ratios = _parse_split_ratios(args.split_ratios)
    except ValueError as exc:
        parser.error(str(exc))

    pooled = pool_records([args.input_main, args.input_reserved])
    effective_pool = pooled
    replacement_stats: dict[str, Any] = {}
    if args.replacement_input is not None and args.replacement_label is not None:
        replacement = pool_records([args.replacement_input])
        effective_pool, replacement_stats = replace_label_records(
            pooled, replacement, args.replacement_label
        )

    repaired, repair_stats = repair_all_evidence_spans(effective_pool)
    repair_stats.update(replacement_stats)
    if args.replacement_input is not None:
        repaired, dedup_stats = deduplicate_normalized_records(repaired, threshold=0.95)
        repair_stats.update(dedup_stats)
    capped, cap_stats = enforce_seed_cap(repaired, cap_pct=args.cap_pct)
    repair_stats.update(cap_stats)

    assignments = assign_stratified_group_split(capped, ratios=ratios, salt=args.version_tag)

    splits: dict[str, list[dict[str, Any]]] = {"train": [], "val": [], "test": []}
    for record in capped:
        splits[assignments[record["seed_id"]]].append(record)

    _write_splits_atomically(args.output_dir, splits)

    split_class_counts = _compute_split_class_counts(splits)
    manifest_payload = build_repair_manifest(
        args.output_dir, args.version_tag, split_class_counts, repair_stats
    )

    manifest_path = Path("data/manifests") / f"manifest-{args.version_tag}.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_manifest = manifest_path.with_suffix(manifest_path.suffix + ".tmp")
    with temporary_manifest.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(manifest_payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    temporary_manifest.replace(manifest_path)

    print(f"Pooled {repair_stats['rows_pooled']} rows")
    print(f"Span-repaired {repair_stats['rows_span_repaired']} rows")
    print(f"Dropped {repair_stats['rows_dropped_unrecoverable_span']} unrecoverable-span rows")
    print(f"Dropped {repair_stats.get('rows_dropped_seed_cap', 0)} seed-cap rows")
    for split_name in ("train", "val", "test"):
        print(f"{split_name}: {len(splits[split_name])} rows")
    print(f"Manifest written to {manifest_path}")


if __name__ == "__main__":
    main()
