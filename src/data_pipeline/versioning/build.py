"""Dataset build orchestration for split generation and manifest versioning."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.config.settings import get_settings
from src.data_pipeline.processing.splitter import split_and_dedup
from src.data_pipeline.schemas import DatasetRecord
from src.data_pipeline.versioning.manifest import build_manifest, save_manifest


class DatasetBuilder:
    """Load validated records, create governed splits, and emit a version manifest."""

    def __init__(self, version_tag: str = "v1.0") -> None:
        self.settings = get_settings()
        self.version_tag = version_tag

    def load_records(self, jsonl_path: Path) -> list[dict[str, Any]]:
        """Load and validate DatasetRecord lines from a JSONL file."""
        records: list[dict[str, Any]] = []
        with jsonl_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                records.append(DatasetRecord.model_validate(json.loads(line)).model_dump())
        return records

    def build_splits(
        self,
        input_path: Path | None = None,
        output_dir: Path | None = None,
        similarity_threshold: float | None = None,
    ) -> dict[str, Any]:
        """Run the split, dedup, write, and manifest steps for a validated dataset."""
        input_file = input_path or (self.settings.data_dir / "processed" / "validated.jsonl")
        splits_dir = output_dir or (self.settings.data_dir / "splits")
        manifests_dir = (
            self.settings.data_dir / "manifests"
            if output_dir is None
            else splits_dir.parent
        )
        threshold = (
            self.settings.similarity_threshold
            if similarity_threshold is None
            else similarity_threshold
        )

        records = self.load_records(input_file)
        splits = split_and_dedup(records, similarity_threshold=threshold)

        splits_dir.mkdir(parents=True, exist_ok=True)
        split_stats: dict[str, int] = {}
        for split_name, split_records in splits.items():
            split_path = splits_dir / f"{split_name}.jsonl"
            with split_path.open("w", encoding="utf-8") as handle:
                for record in split_records:
                    validated = DatasetRecord.model_validate(record)
                    handle.write(json.dumps(validated.model_dump(), ensure_ascii=False) + "\n")
            split_stats[split_name] = len(split_records)

        manifest = build_manifest(splits_dir, self.version_tag)
        manifest_path = (
            manifests_dir / f"manifest-{self.version_tag}.json"
            if output_dir is None
            else manifests_dir / "split-manifest.json"
        )
        manifests_dir.mkdir(parents=True, exist_ok=True)
        save_manifest(manifest, manifest_path, replace=output_dir is None)

        return {
            "version": self.version_tag,
            "splits": split_stats,
            "manifest_path": str(manifest_path),
            "total_records": sum(split_stats.values()),
        }
