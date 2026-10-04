"""Historical first-pass quote extraction for the Phase 39 Zalo defect.

This helper records the mechanical repair originally applied after the judge
found an outer narrator scaffold. Later full-corpus review proved that the
quoted content itself was still third-person scenario prose, so quote removal
was not a sufficient realism repair. The canonical fix is now
``src.data_pipeline.reconstruct_zalo_direct_catalog``: it validates the exact
legacy formulas and replaces them with locally authored direct messages.

The functions remain for audit reproducibility and their focused regression
tests. They must not be treated as a way to produce the current canonical
Zalo corpus.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from src.data_pipeline.processing.dedup import fuzz
from src.data_pipeline.processing.normalizer import normalize_text
from src.data_pipeline.schemas import DatasetRecord

_SPLIT_NAMES = ("train", "val", "test")
_TARGET_LABEL = "zalo_social_engineering"
_QUOTE_PATTERN = re.compile(r"“([^”]+)”")


def extract_quoted_message(text: str) -> str | None:
    """Pull the narrator-wrapped message out of `text`.

    Returns None if no curly-quoted segment is found (nothing to extract)
    or the extracted result would be too short to be a valid message.
    """
    quotes = _QUOTE_PATTERN.findall(text)
    if not quotes:
        return None
    extracted = " ".join(quote.strip() for quote in quotes).strip()
    if len(extracted) < 10:
        return None
    return extracted


def repair_zalo_rows(
    rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Repair narrator-scaffolded zalo_social_engineering rows in place.

    Every non-zalo row passes through unchanged. Every zalo row either gets
    its text replaced by the extracted message (and is schema-revalidated,
    including that every suspicious_span is still an exact substring), or is
    left completely unchanged if extraction fails or the schema check fails
    -- never silently dropped or corrupted.
    """
    repaired_rows: list[dict[str, Any]] = []
    repaired_count = 0
    unrepairable_count = 0

    for row in rows:
        if row.get("label") != _TARGET_LABEL:
            repaired_rows.append(row)
            continue

        extracted = extract_quoted_message(row["text"])
        if extracted is None:
            unrepairable_count += 1
            repaired_rows.append(row)
            continue

        candidate = dict(row)
        candidate["text"] = extracted
        spans_still_valid = all(
            span in extracted for span in candidate.get("suspicious_spans", [])
        )
        if not spans_still_valid:
            unrepairable_count += 1
            repaired_rows.append(row)
            continue
        try:
            DatasetRecord.model_validate(candidate)
        except Exception:
            unrepairable_count += 1
            repaired_rows.append(row)
            continue

        repaired_rows.append(candidate)
        repaired_count += 1

    return repaired_rows, {
        "zalo_rows_repaired": repaired_count,
        "zalo_rows_unrepairable": unrepairable_count,
    }


def find_new_near_duplicates(
    rows: list[dict[str, Any]],
    threshold: float = 0.95,
) -> list[tuple[int, int]]:
    """Detect lexical near-duplicate pairs among zalo rows after repair.

    Narrator scaffolds differed row-to-row, so stripping them down to the
    shared underlying quoted sentences could in principle collapse
    previously-distinct variants into duplicates. Returns (index, index)
    pairs (positions within the full `rows` list) so the caller can decide
    what to do -- this function only detects, never drops.
    """
    zalo_indices = [i for i, row in enumerate(rows) if row.get("label") == _TARGET_LABEL]
    normalized = {i: normalize_text(rows[i]["text"]).casefold() for i in zalo_indices}

    pairs: list[tuple[int, int]] = []
    for pos, left_index in enumerate(zalo_indices):
        for right_index in zalo_indices[pos + 1 :]:
            ratio = fuzz.ratio(normalized[left_index], normalized[right_index]) / 100.0
            if ratio >= threshold:
                pairs.append((left_index, right_index))
    return pairs


def drop_near_duplicate_zalo_rows(
    rows: list[dict[str, Any]],
    threshold: float = 0.95,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Drop later-occurring zalo rows that are lexical near-duplicates of an
    earlier zalo row, keeping the first occurrence -- same keep-first
    convention as repair_corpus_split_governance.deduplicate_normalized_records.

    Only a same-seed_id duplicate pair is auto-dropped: stripping the
    narrator scaffold can collapse two of a seed's own augmentation variants
    down to the same underlying quoted sentences, which is benign (the seed
    still keeps its other variants, and group-integrity is untouched since
    both rows already belonged to the same seed and split). A duplicate pair
    across two DIFFERENT seed_ids is not auto-dropped -- that would be a
    genuine annotation problem, not a scaffold-collapse artifact, so this
    raises instead.
    """
    zalo_indices = [i for i, row in enumerate(rows) if row.get("label") == _TARGET_LABEL]
    normalized = {i: normalize_text(rows[i]["text"]).casefold() for i in zalo_indices}

    keep = [True] * len(rows)
    survivors_normalized: list[tuple[int, str]] = []
    cross_seed_pairs: list[tuple[int, int]] = []
    dropped_indices: list[int] = []

    for index in zalo_indices:
        candidate = normalized[index]
        match_index = next(
            (
                kept_index
                for kept_index, kept_text in survivors_normalized
                if fuzz.ratio(candidate, kept_text) / 100.0 >= threshold
            ),
            None,
        )
        if match_index is None:
            survivors_normalized.append((index, candidate))
            continue
        if rows[index]["seed_id"] == rows[match_index]["seed_id"]:
            keep[index] = False
            dropped_indices.append(index)
        else:
            cross_seed_pairs.append((match_index, index))

    if cross_seed_pairs:
        raise ValueError(
            f"found {len(cross_seed_pairs)} near-duplicate pair(s) across DIFFERENT "
            f"seed_ids after repair: {cross_seed_pairs[:10]} -- this is not the benign "
            "within-seed-variant collapse this script auto-handles; investigate before "
            "proceeding."
        )

    survivors = [row for index, row in enumerate(rows) if keep[index]]
    return survivors, {"zalo_near_duplicates_dropped": len(dropped_indices)}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                rows.append(json.loads(stripped))
    return rows


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path = Path(path)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    with temp_path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    temp_path.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Repair the zalo_social_engineering narrator-scaffold defect in "
            "data/splits/{train,val,test}.jsonl by extracting the quoted "
            "message and dropping the narrator wrapper."
        )
    )
    parser.add_argument("--splits-dir", type=Path, default=Path("data/splits"))
    args = parser.parse_args()

    splits_dir = Path(args.splits_dir)
    totals = {
        "zalo_rows_repaired": 0,
        "zalo_rows_unrepairable": 0,
        "zalo_near_duplicates_dropped": 0,
    }

    per_split_rows: dict[str, list[dict[str, Any]]] = {}
    for split_name in _SPLIT_NAMES:
        split_path = splits_dir / f"{split_name}.jsonl"
        if not split_path.exists():
            raise FileNotFoundError(f"{split_path} does not exist")
        rows = _read_jsonl(split_path)
        repaired_rows, stats = repair_zalo_rows(rows)
        deduped_rows, dedup_stats = drop_near_duplicate_zalo_rows(repaired_rows)

        per_split_rows[split_name] = deduped_rows
        totals["zalo_rows_repaired"] += stats["zalo_rows_repaired"]
        totals["zalo_rows_unrepairable"] += stats["zalo_rows_unrepairable"]
        totals["zalo_near_duplicates_dropped"] += dedup_stats["zalo_near_duplicates_dropped"]
        print(
            f"{split_name}: repaired {stats['zalo_rows_repaired']}, "
            f"unrepairable {stats['zalo_rows_unrepairable']}, "
            f"near-duplicates dropped {dedup_stats['zalo_near_duplicates_dropped']}"
        )

    for split_name, rows in per_split_rows.items():
        _write_jsonl(splits_dir / f"{split_name}.jsonl", rows)

    print(
        f"Total: repaired {totals['zalo_rows_repaired']}, "
        f"unrepairable {totals['zalo_rows_unrepairable']}, "
        f"near-duplicates dropped {totals['zalo_near_duplicates_dropped']}"
    )


if __name__ == "__main__":
    main()
