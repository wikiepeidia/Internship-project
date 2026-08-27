"""Deterministic group splitting and explicit-root dataset versioning."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import math
from pathlib import Path
import subprocess
from typing import Any, Literal

from src.data_pipeline.core.records import DatasetRecord, ManifestEntry, ManifestFile


SplitName = Literal["train", "val", "test"]
DEFAULT_SPLIT_RATIOS = (0.8, 0.1, 0.1)


def validate_split_ratios(
    split_ratios: tuple[float, float, float],
) -> tuple[float, float, float]:
    """Return three finite non-negative ratios whose sum is exactly one."""

    try:
        values = tuple(split_ratios)
    except TypeError as exc:
        raise ValueError("split ratios must contain exactly three numbers") from exc
    if len(values) != 3:
        raise ValueError("split ratios must contain exactly three numbers")
    if any(
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
        or float(value) < 0.0
        for value in values
    ):
        raise ValueError("split ratios must be finite and non-negative")
    normalized = tuple(float(value) for value in values)
    if not math.isclose(sum(normalized), 1.0, rel_tol=0.0, abs_tol=1e-9):
        raise ValueError("split ratios must sum to one")
    return normalized[0], normalized[1], normalized[2]


def _stable_bucket(value: str, salt: str) -> float:
    digest = hashlib.sha256(f"{salt}:{value}".encode("utf-8")).hexdigest()
    return int(digest[:8], 16) / 0xFFFFFFFF


def _seed_bucket(seed_id: str, salt: str) -> float:
    return _stable_bucket(seed_id, salt)


def _record_bucket(record: dict[str, Any], salt: str) -> float:
    record_key = "|".join(
        (
            str(record.get("label", "")),
            str(record.get("seed_id", "")),
            str(record.get("text", "")),
        )
    )
    return _stable_bucket(record_key, salt)


def _allocate_split_counts(
    total_seeds: int,
    split_ratios: tuple[float, float, float],
) -> dict[SplitName, int]:
    split_ratios = validate_split_ratios(split_ratios)
    split_names: tuple[SplitName, SplitName, SplitName] = ("train", "val", "test")
    raw_counts = {
        name: total_seeds * ratio
        for name, ratio in zip(split_names, split_ratios, strict=True)
    }
    counts = {name: int(raw_counts[name]) for name in split_names}
    remaining = total_seeds - sum(counts.values())
    remainder_order = sorted(
        split_names,
        key=lambda name: (
            raw_counts[name] - counts[name],
            -split_names.index(name),
        ),
        reverse=True,
    )
    for name in remainder_order:
        if remaining <= 0:
            break
        counts[name] += 1
        remaining -= 1

    active = [
        name
        for name, ratio in zip(split_names, split_ratios, strict=True)
        if ratio > 0
    ]
    if total_seeds >= len(active):
        for name in active:
            if counts[name] > 0:
                continue
            donor = max(
                (candidate for candidate in active if counts[candidate] > 1),
                key=lambda candidate: (
                    counts[candidate],
                    raw_counts[candidate] - counts[candidate],
                    -split_names.index(candidate),
                ),
                default=None,
            )
            if donor is None:
                break
            counts[donor] -= 1
            counts[name] += 1
    if sum(counts.values()) != total_seeds:
        raise ValueError("split allocation did not assign every seed")
    return counts


def _assign_seed_group_splits(
    seed_ids: list[str],
    split_ratios: tuple[float, float, float],
    salt: str,
) -> dict[str, SplitName]:
    ordered = sorted(seed_ids, key=lambda seed_id: (_seed_bucket(seed_id, salt), seed_id))
    counts = _allocate_split_counts(len(ordered), split_ratios)
    assignments: dict[str, SplitName] = {}
    cursor = 0
    for split_name in ("train", "val", "test"):
        next_cursor = cursor + counts[split_name]
        assignments.update(
            {seed_id: split_name for seed_id in ordered[cursor:next_cursor]}
        )
        cursor = next_cursor
    return assignments


def assign_seed_split(
    seed_id: str,
    split_ratios: tuple[float, float, float] = DEFAULT_SPLIT_RATIOS,
    salt: str = "v1.0",
) -> SplitName:
    """Return a stable split name derived from one seed identifier."""

    split_ratios = validate_split_ratios(split_ratios)
    bucket = _seed_bucket(seed_id, salt)
    if bucket < split_ratios[0]:
        return "train"
    if bucket < split_ratios[0] + split_ratios[1]:
        return "val"
    return "test"


def _partition_record_groups(
    records: list[dict[str, Any]],
    active_split_count: int,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, list[dict[str, Any]]]]:
    label_groups: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for record in records:
        validated = DatasetRecord.model_validate(record).model_dump()
        label_groups.setdefault(validated["label"], {}).setdefault(
            validated["seed_id"], []
        ).append(validated)
    underdiverse = {
        label for label, groups in label_groups.items() if len(groups) < active_split_count
    }
    retained: dict[str, list[dict[str, Any]]] = {}
    record_level: dict[str, list[dict[str, Any]]] = {}
    for seed_groups in label_groups.values():
        for seed_id, group_records in seed_groups.items():
            for record in group_records:
                if record["label"] in underdiverse:
                    record_level.setdefault(record["label"], []).append(record)
                else:
                    retained.setdefault(seed_id, []).append(record)
    return retained, record_level


def split_dataset(
    records: list[dict[str, Any]],
    split_ratios: tuple[float, float, float] = DEFAULT_SPLIT_RATIOS,
    salt: str = "v1.0",
) -> dict[SplitName, list[dict[str, Any]]]:
    """Split records deterministically, preserving sufficiently diverse seed groups."""

    split_ratios = validate_split_ratios(split_ratios)
    splits: dict[SplitName, list[dict[str, Any]]] = {
        "train": [],
        "val": [],
        "test": [],
    }
    active_count = sum(1 for ratio in split_ratios if ratio > 0)
    retained, record_level = _partition_record_groups(records, active_count)
    if retained:
        assignments = _assign_seed_group_splits(list(retained), split_ratios, salt)
        for seed_id, group_records in retained.items():
            splits[assignments[seed_id]].extend(group_records)

    for label, label_records in record_level.items():
        ordered = sorted(
            label_records,
            key=lambda record: (
                _record_bucket(record, f"{salt}:{label}"),
                record["seed_id"],
                record["text"],
            ),
        )
        counts = _allocate_split_counts(len(ordered), split_ratios)
        cursor = 0
        for split_name in ("train", "val", "test"):
            next_cursor = cursor + counts[split_name]
            splits[split_name].extend(ordered[cursor:next_cursor])
            cursor = next_cursor
    return splits


def build_manifest(data_dir: Path, version_tag: str) -> ManifestEntry:
    """Build a SHA-256 manifest under an explicit dataset root."""

    git_commit = None
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            cwd=str(data_dir),
            check=False,
        )
        if result.returncode == 0:
            git_commit = result.stdout.strip()
    except FileNotFoundError:
        pass
    manifest = ManifestEntry(
        version=version_tag,
        build_timestamp=datetime.now(timezone.utc).isoformat(),
        git_commit=git_commit,
        files={},
    )
    for jsonl_file in sorted(data_dir.rglob("*.jsonl")):
        raw = jsonl_file.read_bytes()
        manifest.files[str(jsonl_file.relative_to(data_dir))] = ManifestFile(
            sha256=hashlib.sha256(raw).hexdigest(),
            records=sum(1 for line in raw.decode("utf-8").splitlines() if line.strip()),
            bytes=len(raw),
        )
    return manifest


def verify_manifest(
    manifest: ManifestEntry,
    data_dir: Path,
) -> tuple[bool, list[str]]:
    """Verify all explicit manifest members against an explicit dataset root."""

    errors: list[str] = []
    for relative_path, file_info in manifest.files.items():
        file_path = data_dir / relative_path
        if not file_path.exists():
            errors.append(f"Missing file: {relative_path}")
            continue
        actual_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()
        if actual_hash != file_info.sha256:
            errors.append(
                f"Hash mismatch for {relative_path}: expected "
                f"{file_info.sha256}, got {actual_hash}"
            )
    return not errors, errors


def save_manifest(manifest: ManifestEntry, output_path: Path) -> Path:
    """Persist a manifest as formatted UTF-8 JSON."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    return output_path


__all__ = (
    "DEFAULT_SPLIT_RATIOS",
    "SplitName",
    "assign_seed_split",
    "build_manifest",
    "save_manifest",
    "split_dataset",
    "validate_split_ratios",
    "verify_manifest",
)
