"""Deterministic split assignment with seed-level grouping and dedup integration."""

from __future__ import annotations

import hashlib
from typing import Any, Literal

from src.config.settings import get_settings
from src.data_pipeline.schemas import DatasetRecord


SplitName = Literal["train", "val", "test"]


def assign_seed_split(
    seed_id: str,
    split_ratios: tuple[float, float, float] = (0.8, 0.1, 0.1),
    salt: str = "v1.0",
) -> SplitName:
    """Return a deterministic split name derived from the seed identifier."""
    digest = hashlib.sha256(f"{salt}:{seed_id}".encode("utf-8")).hexdigest()
    bucket = int(digest[:8], 16) / 0xFFFFFFFF
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
    """Split records while keeping every variant of a seed in the same partition."""
    settings = get_settings()
    ratios = split_ratios or settings.split_ratios
    splits: dict[SplitName, list[dict[str, Any]]] = {"train": [], "val": [], "test": []}

    for record in records:
        validated = DatasetRecord.model_validate(record).model_dump()
        split_name = assign_seed_split(validated["seed_id"], ratios, salt)
        splits[split_name].append(validated)

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