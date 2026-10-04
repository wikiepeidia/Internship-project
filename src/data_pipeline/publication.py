"""Transactional publication of one reviewed dataset generation."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Any, Callable
import uuid

from src.core.integrity import (
    IntegrityError,
    atomic_replace_artifact,
    canonical_json_bytes,
    prepare_bounded_output,
    read_file_bytes,
    reject_redirecting_ancestry,
    sha256_bytes,
    write_bytes_exclusive,
)
from src.data_pipeline.core.records import DatasetRecord


@dataclass(frozen=True, slots=True)
class PublishedDatasetGeneration:
    generation_id: str
    root: Path
    current_pointer: Path
    validated_path: Path
    quality_stats_path: Path
    split_manifest_path: Path
    generation_manifest_path: Path
    split_counts: dict[str, int]


def _owned_directory(root: Path, relative: Path, *, where: str) -> Path:
    return prepare_bounded_output(root, relative / ".directory-boundary", where=where).parent


def _validated_bytes(records: list[dict[str, Any]]) -> bytes:
    return b"".join(
        (DatasetRecord.model_validate(record).model_dump_json() + "\n").encode("utf-8")
        for record in records
    )


def _stats_bytes(stats: Any) -> bytes:
    if hasattr(stats, "model_dump"):
        value = stats.model_dump(mode="json")
    elif isinstance(stats, dict):
        value = stats
    else:
        raise IntegrityError("quality statistics must be a typed model or object")
    return canonical_json_bytes(value)


def _generation_members(stage: Path) -> list[dict[str, object]]:
    expected = {
        "validated.jsonl",
        "quality-stats.json",
        "split-manifest.json",
        "splits/train.jsonl",
        "splits/val.jsonl",
        "splits/test.jsonl",
    }
    actual = {
        path.relative_to(stage).as_posix()
        for path in stage.rglob("*")
        if path.is_file()
    }
    if actual != expected:
        raise IntegrityError(
            f"dataset generation membership differs: missing={sorted(expected-actual)} "
            f"unexpected={sorted(actual-expected)}"
        )
    result: list[dict[str, object]] = []
    for name in sorted(expected):
        raw = read_file_bytes(stage / name, where=f"dataset generation member {name}")
        result.append({"path": name, "bytes": len(raw), "sha256": sha256_bytes(raw)})
    return result


def publish_reviewed_dataset(
    records: list[dict[str, Any]],
    quality_stats: Any,
    data_dir: Path,
    version_tag: str,
    builder_factory: Callable[..., Any],
) -> PublishedDatasetGeneration:
    """Stage rows, statistics, splits, and manifests; then switch one pointer."""

    root = reject_redirecting_ancestry(
        Path(os.path.abspath(data_dir)), where="dataset publication root"
    )
    if not root.is_dir() or root.parent == root:
        raise IntegrityError("dataset publication root must be a bounded directory")
    publication_root = _owned_directory(
        root, Path("dataset-generations"), where="dataset publication"
    )
    staging_root = _owned_directory(
        root, Path("dataset-generations/staging"), where="dataset staging"
    )
    versions_root = _owned_directory(
        root, Path("dataset-generations/versions"), where="dataset versions"
    )
    generation_id = uuid.uuid4().hex
    stage = _owned_directory(
        root,
        Path("dataset-generations/staging") / generation_id,
        where="dataset generation stage",
    )
    validated = write_bytes_exclusive(
        stage / "validated.jsonl", _validated_bytes(records), where="validated rows"
    )
    stats = write_bytes_exclusive(
        stage / "quality-stats.json", _stats_bytes(quality_stats), where="quality statistics"
    )
    splits_dir = _owned_directory(
        root,
        Path("dataset-generations/staging") / generation_id / "splits",
        where="dataset generation splits",
    )
    build = builder_factory(version_tag=version_tag).build_splits(
        input_path=validated,
        output_dir=splits_dir,
    )
    split_manifest = stage / "split-manifest.json"
    members = _generation_members(stage)
    generation_manifest = write_bytes_exclusive(
        stage / "generation-manifest.json",
        canonical_json_bytes(
            {
                "schema": "vnphish-reviewed-dataset-generation-v1",
                "generation_id": generation_id,
                "version_tag": version_tag,
                "members": members,
            }
        ),
        where="dataset generation manifest",
    )
    final = versions_root / generation_id
    os.rename(stage, final)
    final_manifest = final / generation_manifest.name
    pointer = publication_root / "current.json"
    atomic_replace_artifact(
        pointer,
        canonical_json_bytes(
            {
                "schema": "vnphish-reviewed-dataset-pointer-v1",
                "generation_id": generation_id,
                "relative_path": f"versions/{generation_id}",
                "manifest_sha256": sha256_bytes(
                    read_file_bytes(final_manifest, where="dataset generation manifest")
                ),
            }
        ),
        where="dataset generation pointer",
    )
    return PublishedDatasetGeneration(
        generation_id=generation_id,
        root=final,
        current_pointer=pointer,
        validated_path=final / validated.name,
        quality_stats_path=final / stats.name,
        split_manifest_path=final / split_manifest.name,
        generation_manifest_path=final_manifest,
        split_counts=dict(build["splits"]),
    )


__all__ = ("PublishedDatasetGeneration", "publish_reviewed_dataset")
