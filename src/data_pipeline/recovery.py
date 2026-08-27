"""Fail-closed discovery and validation for recoverable generation artifacts."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import stat
from typing import Any

from src.core.integrity import IntegrityError, reject_redirecting_ancestry
from src.data_pipeline.core.records import DatasetRecord


_DIRECT_SYNTHETIC_INPUTS = (
    "generated.jsonl",
    "generated-partial.jsonl",
    "generated-gap-fill-recovered.jsonl",
)
_RUN_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")


class RecoveryValidationError(ValueError):
    """Raised after all candidate recovery inputs have been inspected."""


def _trusted_data_root(data_dir: Path) -> Path:
    root = reject_redirecting_ancestry(
        Path(os.path.abspath(data_dir)), where="recovery data root"
    )
    if not root.is_dir() or root.parent == root:
        raise RecoveryValidationError("recovery data root must be a bounded directory")
    return root


def _regular_member(path: Path, root: Path) -> Path:
    candidate = reject_redirecting_ancestry(path, where="recovery input")
    if root not in candidate.parents:
        raise RecoveryValidationError("recovery input escaped the configured data root")
    try:
        metadata = os.lstat(candidate)
    except OSError as error:
        raise RecoveryValidationError(f"cannot inspect recovery input: {candidate}") from error
    if not stat.S_ISREG(metadata.st_mode):
        raise RecoveryValidationError(f"recovery input is not a regular file: {candidate}")
    return candidate


def _run_checkpoint_paths(root: Path) -> list[Path]:
    runs_root = root / "generation-runs"
    if not runs_root.exists():
        return []
    runs_root = reject_redirecting_ancestry(runs_root, where="generation runs root")
    if not runs_root.is_dir():
        raise RecoveryValidationError("generation runs root is not a directory")
    paths: list[Path] = []
    for run_dir in sorted(runs_root.iterdir(), key=lambda path: path.name):
        if not _RUN_ID_PATTERN.fullmatch(run_dir.name):
            raise RecoveryValidationError(f"invalid generation run id: {run_dir.name!r}")
        run_dir = reject_redirecting_ancestry(run_dir, where="generation run")
        checkpoints = run_dir / "checkpoints"
        if not checkpoints.exists():
            continue
        checkpoints = reject_redirecting_ancestry(
            checkpoints, where="generation checkpoint root"
        )
        if not checkpoints.is_dir():
            raise RecoveryValidationError("generation checkpoint root is not a directory")
        for member in sorted(checkpoints.iterdir(), key=lambda path: path.name):
            if member.name == "generated-partial.jsonl" or (
                member.name.startswith("checkpoint-") and member.name.endswith(".jsonl")
            ):
                paths.append(_regular_member(member, root))
    return paths


def recoverable_record_paths(data_dir: Path) -> list[Path]:
    """Return only closed, non-final generation/checkpoint inputs."""

    root = _trusted_data_root(data_dir)
    paths: list[Path] = []
    synthetic = root / "synthetic"
    if synthetic.exists():
        synthetic = reject_redirecting_ancestry(synthetic, where="synthetic input root")
        if not synthetic.is_dir():
            raise RecoveryValidationError("synthetic input root is not a directory")
        for name in _DIRECT_SYNTHETIC_INPUTS:
            candidate = synthetic / name
            if candidate.exists():
                paths.append(_regular_member(candidate, root))
    paths.extend(_run_checkpoint_paths(root))
    identities: set[str] = set()
    ordered: list[Path] = []
    for path in sorted(paths, key=lambda item: item.relative_to(root).as_posix()):
        identity = path.relative_to(root).as_posix()
        normalized = identity.casefold()
        if normalized in identities:
            raise RecoveryValidationError(f"duplicate recovery source identity: {identity}")
        identities.add(normalized)
        ordered.append(path)
    return ordered


def _strict_json_value(raw: str, *, source: str, line_number: int) -> Any:
    def reject_constant(token: str) -> Any:
        raise ValueError(f"non-standard JSON token {token!r}")

    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key {key!r}")
            result[key] = value
        return result

    try:
        return json.loads(
            raw,
            parse_constant=reject_constant,
            object_pairs_hook=reject_duplicates,
        )
    except (json.JSONDecodeError, ValueError) as error:
        raise RecoveryValidationError(
            f"{source}:{line_number}: invalid strict JSON: {error}"
        ) from error


def _candidate_records(value: Any) -> list[Any]:
    if isinstance(value, dict) and "records" in value:
        records = value["records"]
        if not isinstance(records, list):
            raise RecoveryValidationError("checkpoint records must be a JSON array")
        return records
    return [value]


def load_recoverable_records(
    data_dir: Path,
    source_paths: list[Path],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, int]], int, int, int]:
    """Validate all recovery rows and aggregate every error before returning."""

    root = _trusted_data_root(data_dir)
    loaded = invalid = conflicts = 0
    unique_by_text: dict[str, dict[str, Any]] = {}
    source_stats: dict[str, dict[str, int]] = {}
    errors: list[str] = []
    for supplied_path in source_paths:
        try:
            path = _regular_member(supplied_path, root)
            identity = path.relative_to(root).as_posix()
        except (RecoveryValidationError, ValueError) as error:
            errors.append(str(error))
            invalid += 1
            continue
        if identity in source_stats:
            errors.append(f"duplicate recovery source identity: {identity}")
            invalid += 1
            continue
        stats = {"valid_records": 0, "invalid_items": 0}
        source_stats[identity] = stats
        try:
            text = path.read_bytes().decode("utf-8", errors="strict")
        except (OSError, UnicodeDecodeError) as error:
            errors.append(f"{identity}: not strict UTF-8: {error}")
            stats["invalid_items"] += 1
            invalid += 1
            continue
        for line_number, raw_line in enumerate(text.splitlines(), start=1):
            if not (stripped := raw_line.strip()):
                continue
            try:
                value = _strict_json_value(
                    stripped, source=identity, line_number=line_number
                )
                candidates = _candidate_records(value)
            except RecoveryValidationError as error:
                errors.append(str(error))
                stats["invalid_items"] += 1
                invalid += 1
                continue
            for item_number, candidate in enumerate(candidates, start=1):
                try:
                    record = DatasetRecord.model_validate(candidate).model_dump()
                except Exception as error:
                    errors.append(
                        f"{identity}:{line_number}:{item_number}: invalid DatasetRecord: {error}"
                    )
                    stats["invalid_items"] += 1
                    invalid += 1
                    continue
                loaded += 1
                stats["valid_records"] += 1
                key = record["text"].strip()
                existing = unique_by_text.get(key)
                if existing is None:
                    unique_by_text[key] = record
                elif existing["label"] != record["label"]:
                    conflicts += 1
                    errors.append(f"{identity}:{line_number}: conflicting label for text")
    if errors:
        raise RecoveryValidationError(
            f"recovery validation failed with {len(errors)} error(s): " + " | ".join(errors)
        )
    return unique_by_text, source_stats, loaded, invalid, conflicts


__all__ = (
    "RecoveryValidationError",
    "load_recoverable_records",
    "recoverable_record_paths",
)
