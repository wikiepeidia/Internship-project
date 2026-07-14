# ============================================================
# STEP 4 of 10 — Deterministic, Seed-Aware Train/Val/Test Split
# ============================================================
# Canonical source (this numbered copy exists ONLY for defense-day
# navigation — it is not a second implementation and is not imported
# by anything): src/data_pipeline/processing/splitter.py
#
# What this file does: assigns every judged-and-passed record (from
# step 3) to train/val/test using a deterministic hash of its seed_id,
# so all synthetic variants of one real seed stay in the same split —
# this is the anti-leakage mechanism referenced constantly in the Q&A
# prep doc. Calls into dedup.py for lexical + embedding-based cleanup.
#
# See also: documents/reports/supervisor/defense_code_navigation.md
# ============================================================

"""Deterministic split assignment with seed-level grouping and dedup integration."""

from __future__ import annotations

import hashlib
from typing import Any, Literal

from src.config.settings import get_settings
from src.data_pipeline.schemas import DatasetRecord


SplitName = Literal["train", "val", "test"]


def _stable_bucket(value: str, salt: str) -> float:
    digest = hashlib.sha256(f"{salt}:{value}".encode("utf-8")).hexdigest()
    return int(digest[:8], 16) / 0xFFFFFFFF


def _seed_bucket(seed_id: str, salt: str) -> float:
    return _stable_bucket(seed_id, salt)


def _record_bucket(record: dict[str, Any], salt: str) -> float:
    record_key = "|".join(
        [
            str(record.get("label", "")),
            str(record.get("seed_id", "")),
            str(record.get("text", "")),
        ]
    )
    return _stable_bucket(record_key, salt)


def _allocate_split_counts(
    total_seeds: int,
    split_ratios: tuple[float, float, float],
) -> dict[SplitName, int]:
    split_names: tuple[SplitName, SplitName, SplitName] = ("train", "val", "test")
    raw_counts = {
        split_name: total_seeds * ratio
        for split_name, ratio in zip(split_names, split_ratios, strict=True)
    }
    counts = {
        split_name: int(raw_counts[split_name])
        for split_name in split_names
    }

    remaining = total_seeds - sum(counts.values())
    remainder_order = sorted(
        split_names,
        key=lambda split_name: (raw_counts[split_name] - counts[split_name], -split_names.index(split_name)),
        reverse=True,
    )
    for split_name in remainder_order:
        if remaining <= 0:
            break
        counts[split_name] += 1
        remaining -= 1

    active_splits = [split_name for split_name, ratio in zip(split_names, split_ratios, strict=True) if ratio > 0]
    if total_seeds >= len(active_splits):
        for split_name in active_splits:
            if counts[split_name] > 0:
                continue
            donor = max(
                (name for name in active_splits if counts[name] > 1),
                key=lambda name: (counts[name], raw_counts[name] - counts[name], -split_names.index(name)),
                default=None,
            )
            if donor is None:
                break
            counts[donor] -= 1
            counts[split_name] += 1

    return counts


def _assign_seed_group_splits(
    seed_ids: list[str],
    split_ratios: tuple[float, float, float],
    salt: str,
) -> dict[str, SplitName]:
    ordered_seed_ids = sorted(seed_ids, key=lambda seed_id: (_seed_bucket(seed_id, salt), seed_id))
    counts = _allocate_split_counts(len(ordered_seed_ids), split_ratios)
    assignments: dict[str, SplitName] = {}
    cursor = 0
    for split_name in ("train", "val", "test"):
        next_cursor = cursor + counts[split_name]
        for seed_id in ordered_seed_ids[cursor:next_cursor]:
            assignments[seed_id] = split_name
        cursor = next_cursor
    return assignments


def assign_seed_split(
    seed_id: str,
    split_ratios: tuple[float, float, float] = (0.8, 0.1, 0.1),
    salt: str = "v1.0",
) -> SplitName:
    """Return a deterministic split name derived from the seed identifier."""
    bucket = _seed_bucket(seed_id, salt)
    if bucket < split_ratios[0]:
        return "train"
    if bucket < split_ratios[0] + split_ratios[1]:
        return "val"
    return "test"


def split_dataset(
    records: list[dict[str, Any]],
    split_ratios: tuple[float, float, float] | None = None,
    salt: str = "v1.0",
) -> dict[SplitName, list[dict[str, Any]]]:
    """Split records while preserving seed groups when feasible and label support when not."""
    settings = get_settings()
    ratios = split_ratios or settings.split_ratios
    splits: dict[SplitName, list[dict[str, Any]]] = {"train": [], "val": [], "test": []}
    active_split_count = sum(1 for ratio in ratios if ratio > 0)
    label_seed_groups: dict[str, dict[str, list[dict[str, Any]]]] = {}
    retained_seed_groups: dict[str, list[dict[str, Any]]] = {}
    underdiverse_label_records: dict[str, list[dict[str, Any]]] = {}

    for record in records:
        validated = DatasetRecord.model_validate(record).model_dump()
        label_seed_groups.setdefault(validated["label"], {}).setdefault(validated["seed_id"], []).append(validated)

    underdiverse_labels = {
        label
        for label, seed_groups in label_seed_groups.items()
        if len(seed_groups) < active_split_count
    }

    for label_seed_group in label_seed_groups.values():
        for seed_id, group_records in label_seed_group.items():
            if any(group_record["label"] in underdiverse_labels for group_record in group_records):
                for group_record in group_records:
                    if group_record["label"] in underdiverse_labels:
                        underdiverse_label_records.setdefault(group_record["label"], []).append(group_record)
                    else:
                        retained_seed_groups.setdefault(seed_id, []).append(group_record)
                continue
            retained_seed_groups.setdefault(seed_id, []).extend(group_records)

    if retained_seed_groups:
        assignments = _assign_seed_group_splits(list(retained_seed_groups), ratios, salt)
        for seed_id, group_records in retained_seed_groups.items():
            splits[assignments[seed_id]].extend(group_records)

    for label, label_records in underdiverse_label_records.items():
        ordered_records = sorted(
            label_records,
            key=lambda group_record: (
                _record_bucket(group_record, f"{salt}:{label}"),
                group_record["seed_id"],
                group_record["text"],
            ),
        )
        counts = _allocate_split_counts(len(ordered_records), ratios)
        cursor = 0
        for split_name in ("train", "val", "test"):
            next_cursor = cursor + counts[split_name]
            splits[split_name].extend(ordered_records[cursor:next_cursor])
            cursor = next_cursor

    return splits


def split_and_dedup(
    records: list[dict[str, Any]],
    split_ratios: tuple[float, float, float] | None = None,
    similarity_threshold: float | None = None,
    salt: str = "v1.0",
) -> dict[SplitName, list[dict[str, Any]]]:
    """Run lexical dedup, deterministic splitting, and semantic cross-split cleanup."""
    from src.data_pipeline.processing.dedup import cross_split_dedup, lexical_dedup

    settings = get_settings()
    threshold = similarity_threshold or settings.similarity_threshold

    deduped_records = lexical_dedup(records)
    splits = split_dataset(deduped_records, split_ratios=split_ratios, salt=salt)
    removals = cross_split_dedup(
        splits["train"],
        splits["val"],
        splits["test"],
        threshold=threshold,
    )

    val_remove_set = set(removals.get("val", []))
    test_remove_set = set(removals.get("test", []))
    splits["val"] = [record for index, record in enumerate(splits["val"]) if str(index) not in val_remove_set]
    splits["test"] = [record for index, record in enumerate(splits["test"]) if str(index) not in test_remove_set]
    return splits
