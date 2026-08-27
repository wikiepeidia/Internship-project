"""Compatibility facade for deterministic split governance."""

from __future__ import annotations

import math
from typing import Any

from src.config.settings import get_data_settings
from src.data_pipeline.core.splits import (
    SplitName,
    _stable_bucket,
    assign_seed_split,
    split_dataset as _split_dataset,
)


def split_dataset(
    records: list[dict[str, Any]],
    split_ratios: tuple[float, float, float] | None = None,
    salt: str = "v1.0",
) -> dict[SplitName, list[dict[str, Any]]]:
    """Preserve the old optional-settings split contract."""

    ratios = get_data_settings().split_ratios if split_ratios is None else split_ratios
    return _split_dataset(records, split_ratios=ratios, salt=salt)


def split_and_dedup(
    records: list[dict[str, Any]],
    split_ratios: tuple[float, float, float] | None = None,
    similarity_threshold: float | None = None,
    salt: str = "v1.0",
) -> dict[SplitName, list[dict[str, Any]]]:
    """Run lexical dedup, grouping, and semantic cross-split cleanup."""

    from src.data_pipeline.processing.dedup import cross_split_dedup, lexical_dedup

    settings = get_data_settings()
    ratios = settings.split_ratios if split_ratios is None else split_ratios
    threshold = (
        settings.similarity_threshold
        if similarity_threshold is None
        else similarity_threshold
    )
    if not math.isfinite(threshold) or not 0.0 <= threshold <= 1.0:
        raise ValueError("similarity_threshold must be a finite value in [0, 1]")
    deduped_records = lexical_dedup(records)
    splits = split_dataset(deduped_records, split_ratios=ratios, salt=salt)
    removals = cross_split_dedup(
        splits["train"],
        splits["val"],
        splits["test"],
        threshold=threshold,
    )
    val_remove_set = set(removals.get("val", []))
    test_remove_set = set(removals.get("test", []))
    splits["val"] = [
        record
        for index, record in enumerate(splits["val"])
        if str(index) not in val_remove_set
    ]
    splits["test"] = [
        record
        for index, record in enumerate(splits["test"])
        if str(index) not in test_remove_set
    ]
    active_names = tuple(
        name
        for name, ratio in zip(("train", "val", "test"), ratios, strict=True)
        if ratio > 0
    )
    labels = sorted({record["label"] for record in deduped_records})
    missing: list[str] = []
    for split_name in active_names:
        for label in labels:
            rows = [row for row in splits[split_name] if row["label"] == label]
            seeds = {row["seed_id"] for row in rows}
            if not rows or not seeds:
                missing.append(f"{split_name}/{label}:rows={len(rows)},seeds={len(seeds)}")
    if missing:
        raise ValueError(
            "post-dedup split coverage failed: " + "; ".join(missing)
        )
    return splits


__all__ = (
    "SplitName",
    "_stable_bucket",
    "assign_seed_split",
    "split_and_dedup",
    "split_dataset",
)
