"""Tests for deterministic split assignment and cross-split cleanup."""

from __future__ import annotations

from src.data_pipeline.processing.splitter import assign_seed_split, split_and_dedup, split_dataset


def test_assign_seed_split_is_deterministic():
    first = assign_seed_split("seed-001", salt="v1.0")
    second = assign_seed_split("seed-001", salt="v1.0")

    assert first == second


def test_split_ratios():
    counts = {"train": 0, "val": 0, "test": 0}
    for index in range(1000):
        counts[assign_seed_split(f"seed-{index:04d}")] += 1

    assert 750 <= counts["train"] <= 850
    assert 50 <= counts["val"] <= 150
    assert 50 <= counts["test"] <= 150


def test_seed_grouping(sample_validated_records):
    grouped_records = [record for record in sample_validated_records if record["seed_id"] == "seed-0"]
    assert len(grouped_records) == 4

    splits = split_dataset(sample_validated_records, salt="seed-grouping")
    split_names = [name for name, records in splits.items() if any(record["seed_id"] == "seed-0" for record in records)]

    assert split_names
    target_split = split_names[0]
    assert sum(record["seed_id"] == "seed-0" for record in splits[target_split]) == 4


def test_split_dataset_preserves_all_records(sample_validated_records):
    splits = split_dataset(sample_validated_records, salt="preserve-all")

    assert set(splits) == {"train", "val", "test"}
    assert sum(len(records) for records in splits.values()) == len(sample_validated_records)


def test_split_and_dedup(sample_validated_records, monkeypatch):
    extra_records = sample_validated_records + [
        {
            **sample_validated_records[0],
            "text": sample_validated_records[0]["text"],
            "seed_id": "seed-extra-0",
        }
    ]

    monkeypatch.setattr(
        "src.data_pipeline.processing.dedup.lexical_dedup",
        lambda records, threshold=0.95: records[:-1],
    )
    monkeypatch.setattr(
        "src.data_pipeline.processing.dedup.cross_split_dedup",
        lambda train_records, val_records, test_records, threshold=0.85, model_name="paraphrase-multilingual-MiniLM-L12-v2", encoder=None: {
            "val": ["0"] if val_records else [],
            "test": [],
        },
    )

    splits = split_and_dedup(extra_records, salt="integration")

    assert set(splits) == {"train", "val", "test"}
    assert sum(len(records) for records in splits.values()) == len(sample_validated_records) - 1