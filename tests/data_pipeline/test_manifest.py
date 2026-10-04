"""Tests for manifests and full dataset build orchestration."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from src.data_pipeline.schemas import DatasetRecord, ManifestEntry
from src.data_pipeline.versioning.build import DatasetBuilder
from src.data_pipeline.versioning.manifest import build_manifest, save_manifest, verify_manifest


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def test_build_manifest(sample_validated_records, tmp_path):
    train_path = tmp_path / "train.jsonl"
    val_path = tmp_path / "val.jsonl"
    _write_jsonl(train_path, sample_validated_records[:3])
    _write_jsonl(val_path, sample_validated_records[3:5])

    manifest = build_manifest(tmp_path, "v1.0.0")

    assert isinstance(manifest, ManifestEntry)
    assert manifest.version == "v1.0.0"
    assert manifest.files["train.jsonl"].sha256 == hashlib.sha256(train_path.read_bytes()).hexdigest()
    assert manifest.files["train.jsonl"].records == 3
    assert manifest.files["val.jsonl"].bytes == val_path.stat().st_size


def test_verify_manifest_valid(sample_validated_records, tmp_path):
    train_path = tmp_path / "train.jsonl"
    _write_jsonl(train_path, sample_validated_records[:2])
    manifest = build_manifest(tmp_path, "v1.0.0")

    valid, errors = verify_manifest(manifest, tmp_path)

    assert valid is True
    assert errors == []


def test_verify_manifest_tampered(sample_validated_records, tmp_path):
    train_path = tmp_path / "train.jsonl"
    _write_jsonl(train_path, sample_validated_records[:2])
    manifest = build_manifest(tmp_path, "v1.0.0")
    train_path.write_text("tampered\n", encoding="utf-8")

    valid, errors = verify_manifest(manifest, tmp_path)

    assert valid is False
    assert any("Hash mismatch" in error for error in errors)


def test_verify_manifest_missing(sample_validated_records, tmp_path):
    train_path = tmp_path / "train.jsonl"
    _write_jsonl(train_path, sample_validated_records[:2])
    manifest = build_manifest(tmp_path, "v1.0.0")
    train_path.unlink()

    valid, errors = verify_manifest(manifest, tmp_path)

    assert valid is False
    assert any("Missing file" in error for error in errors)


def test_dataset_builder_build_splits(sample_validated_records, sample_validated_jsonl, tmp_path, monkeypatch):
    settings = SimpleNamespace(data_dir=tmp_path, similarity_threshold=0.85)
    monkeypatch.setattr("src.data_pipeline.versioning.build.get_settings", lambda: settings)

    def fake_split_and_dedup(records, split_ratios=None, similarity_threshold=None, salt="v1.0"):
        return {
            "train": records[:10],
            "val": records[10:15],
            "test": records[15:],
        }

    monkeypatch.setattr("src.data_pipeline.versioning.build.split_and_dedup", fake_split_and_dedup)

    builder = DatasetBuilder(version_tag="v1.0.0")
    result = builder.build_splits(
        input_path=sample_validated_jsonl,
        output_dir=tmp_path / "splits",
    )

    manifest_path = Path(result["manifest_path"])
    assert (tmp_path / "splits" / "train.jsonl").exists()
    assert (tmp_path / "splits" / "val.jsonl").exists()
    assert (tmp_path / "splits" / "test.jsonl").exists()
    assert manifest_path.exists()

    for split_name in ("train", "val", "test"):
        split_path = tmp_path / "splits" / f"{split_name}.jsonl"
        with split_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                DatasetRecord.model_validate(json.loads(line))

    manifest = ManifestEntry.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    assert manifest.files["train.jsonl"].records == 10


def test_save_manifest(sample_manifest_entry, tmp_path):
    output_path = tmp_path / "manifests" / "manifest-v1.0.0.json"
    saved_path = save_manifest(sample_manifest_entry, output_path)

    assert saved_path.exists()
    assert ManifestEntry.model_validate_json(saved_path.read_text(encoding="utf-8")).version == "v1.0.0"