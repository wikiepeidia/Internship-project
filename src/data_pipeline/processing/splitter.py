"""Compatibility facade for deterministic split governance."""

from __future__ import annotations

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

    ratios = split_ratios or get_data_settings().split_ratios
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
    return splits


__all__ = (
    "SplitName",
    "_stable_bucket",
    "assign_seed_split",
    "split_and_dedup",
    "split_dataset",
)
