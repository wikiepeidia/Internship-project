"""Deterministic group splitting and explicit-root dataset versioning."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import math
import os
from pathlib import Path
import subprocess
import tempfile
from typing import Any, Literal

from src.core.integrity import (
    IntegrityError,
    atomic_replace_new_artifact,
    reject_redirecting_ancestry,
)
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


def split_dataset(
    records: list[dict[str, Any]],
    split_ratios: tuple[float, float, float] = DEFAULT_SPLIT_RATIOS,
    salt: str = "v1.0",
) -> dict[SplitName, list[dict[str, Any]]]:
    """Split complete seed groups, failing when a label lacks group diversity."""

    split_ratios = validate_split_ratios(split_ratios)
    splits: dict[SplitName, list[dict[str, Any]]] = {
        "train": [],
        "val": [],
        "test": [],
    }
    active_names = tuple(
        name
        for name, ratio in zip(("train", "val", "test"), split_ratios, strict=True)
        if ratio > 0
    )
    groups: dict[str, dict[str, list[dict[str, Any]]]] = {}
    seed_labels: dict[str, str] = {}
    for record in records:
        validated = DatasetRecord.model_validate(record).model_dump()
        seed_id, label = validated["seed_id"], validated["label"]
        previous = seed_labels.setdefault(seed_id, label)
        if previous != label:
            raise ValueError(f"seed {seed_id!r} spans multiple labels")
        groups.setdefault(label, {}).setdefault(seed_id, []).append(validated)

    for label, seed_groups in groups.items():
        if len(seed_groups) < len(active_names):
            raise ValueError(
                f"label {label!r} has {len(seed_groups)} seed groups; "
                f"{len(active_names)} are required for group-safe splitting"
            )
        assignments = _assign_seed_group_splits(
            list(seed_groups), split_ratios, f"{salt}:{label}"
        )
        if set(assignments) != set(seed_groups):
            raise ValueError("group-safe split did not assign every seed")
        for seed_id, group_records in seed_groups.items():
            splits[assignments[seed_id]].extend(group_records)

    if sum(map(len, splits.values())) != len(records):
        raise ValueError("group-safe split did not assign every record exactly once")
    return splits


def _manifest_jsonl_paths(data_dir: Path) -> tuple[Path, tuple[Path, ...]]:
    root = reject_redirecting_ancestry(
        Path(os.path.abspath(data_dir)), where="dataset manifest root"
    )
    if not root.is_dir():
        raise IntegrityError("dataset manifest root must be an existing directory")
    members: list[Path] = []
    for current, directories, filenames in os.walk(root, followlinks=False):
        current_path = reject_redirecting_ancestry(
            Path(current), where="dataset manifest directory"
        )
        for name in tuple(directories):
            reject_redirecting_ancestry(
                current_path / name, where="dataset manifest directory"
            )
        for name in filenames:
            if name.endswith(".jsonl"):
                members.append(
                    reject_redirecting_ancestry(
                        current_path / name, where="dataset manifest member"
                    )
                )
    return root, tuple(sorted(members))


def _jsonl_facts(path: Path) -> tuple[bytes, int]:
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise IntegrityError(f"manifest member is not strict UTF-8: {path}") from error
    return raw, sum(1 for line in text.splitlines() if line.strip())


def build_manifest(data_dir: Path, version_tag: str) -> ManifestEntry:
    """Build a strict SHA-256 manifest under an explicit dataset root."""

    root, jsonl_files = _manifest_jsonl_paths(data_dir)
    git_commit = None
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            cwd=str(root),
            check=False,
        )
        if result.returncode == 0:
            git_commit = result.stdout.strip()
    except FileNotFoundError:
        pass
    files: dict[str, ManifestFile] = {}
    for jsonl_file in jsonl_files:
        raw, records = _jsonl_facts(jsonl_file)
        files[jsonl_file.relative_to(root).as_posix()] = ManifestFile(
            sha256=hashlib.sha256(raw).hexdigest(),
            records=records,
            bytes=len(raw),
        )
    return ManifestEntry(
        version=version_tag,
        build_timestamp=datetime.now(timezone.utc).isoformat(),
        git_commit=git_commit,
        files=files,
    )


def verify_manifest(
    manifest: ManifestEntry,
    data_dir: Path,
) -> tuple[bool, list[str]]:
    """Reconcile exact members, bytes, rows, and hashes under one root."""

    try:
        root, paths = _manifest_jsonl_paths(data_dir)
    except (IntegrityError, OSError) as error:
        return False, [str(error)]
    actual = {path.relative_to(root).as_posix(): path for path in paths}
    expected = set(manifest.files)
    errors = [f"Missing file: {name}" for name in sorted(expected - set(actual))]
    errors.extend(f"Unexpected file: {name}" for name in sorted(set(actual) - expected))
    for name in sorted(expected & set(actual)):
        expected_facts = manifest.files[name]
        try:
            raw, records = _jsonl_facts(actual[name])
        except (IntegrityError, OSError) as error:
            errors.append(f"Invalid file {name}: {error}")
            continue
        if hashlib.sha256(raw).hexdigest() != expected_facts.sha256:
            errors.append(f"Hash mismatch for {name}")
        if len(raw) != expected_facts.bytes:
            errors.append(f"Byte-count mismatch for {name}")
        if records != expected_facts.records:
            errors.append(f"Record-count mismatch for {name}")
    return not errors, errors


def save_manifest(
    manifest: ManifestEntry,
    output_path: Path,
    *,
    replace: bool = False,
) -> Path:
    """Publish a complete manifest with an explicit replacement policy."""

    target = reject_redirecting_ancestry(
        Path(os.path.abspath(output_path)), where="dataset manifest output"
    )
    parent = reject_redirecting_ancestry(
        target.parent, where="dataset manifest output parent"
    )
    if not parent.is_dir():
        raise IntegrityError("dataset manifest output parent must already exist")
    payload = (manifest.model_dump_json(indent=2) + "\n").encode("utf-8")
    if not replace:
        return atomic_replace_new_artifact(target, payload, where="dataset manifest")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".tmp", dir=parent
    )
    temporary = Path(temporary_name)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    if temporary.read_bytes() != payload:
        raise IntegrityError("dataset manifest staging bytes changed")
    os.replace(temporary, target)
    return target


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
