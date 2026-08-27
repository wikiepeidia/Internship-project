"""Fail-closed discovery and validation for recoverable generation artifacts."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import stat
from typing import Any
import uuid

from src.core.integrity import (
    IntegrityError,
    prepare_bounded_output,
    reject_redirecting_ancestry,
)
from src.data_pipeline.core.records import DatasetRecord
from src.data_pipeline.core.splits import (
    build_manifest,
    save_manifest,
    split_dataset,
    verify_manifest,
)


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


def _read_salvage_sources(
    root: Path,
    sources: list[Path],
) -> tuple[list[dict[str, Any]], dict[Path, bytes], int]:
    records: list[dict[str, Any]] = []
    captured: dict[Path, bytes] = {}
    by_text: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    nonblank = duplicates = 0
    for path in sources:
        identity = path.relative_to(root).as_posix()
        raw = path.read_bytes()
        captured[path] = raw
        try:
            text = raw.decode("utf-8", errors="strict")
        except UnicodeDecodeError as error:
            errors.append(f"{identity}: not strict UTF-8: {error}")
            continue
        for line_number, line in enumerate(text.splitlines(), start=1):
            if not (stripped := line.strip()):
                continue
            nonblank += 1
            try:
                value = _strict_json_value(
                    stripped, source=identity, line_number=line_number
                )
                record = DatasetRecord.model_validate(value).model_dump()
            except Exception as error:
                errors.append(f"{identity}:{line_number}: invalid DatasetRecord: {error}")
                continue
            key = record["text"].strip()
            existing = by_text.get(key)
            if existing is None:
                by_text[key] = record
                records.append(record)
            elif existing == record:
                duplicates += 1
            else:
                errors.append(f"{identity}:{line_number}: conflicting duplicate text")
    if nonblank == 0:
        errors.append("salvage requires at least one nonempty source")
    if errors:
        raise RecoveryValidationError(
            f"salvage validation failed with {len(errors)} error(s): " + " | ".join(errors)
        )
    return records, captured, duplicates


def _ensure_owned_directory(root: Path, relative: Path) -> Path:
    target = prepare_bounded_output(
        root,
        relative / ".directory-boundary",
        where="recovery-owned directory",
    ).parent
    if root not in target.parents or not target.is_dir():
        raise RecoveryValidationError("recovery-owned directory escaped its data root")
    return target


def _validated_jsonl_bytes(records: list[dict[str, Any]]) -> bytes:
    rendered = b"".join(
        (DatasetRecord.model_validate(record).model_dump_json() + "\n").encode("utf-8")
        for record in records
    )
    for line in rendered.decode("utf-8", errors="strict").splitlines():
        DatasetRecord.model_validate_json(line)
    return rendered


def _write_exclusive_bytes(path: Path, value: bytes) -> Path:
    with path.open("xb") as handle:
        handle.write(value)
        handle.flush()
        os.fsync(handle.fileno())
    if path.read_bytes() != value:
        raise RecoveryValidationError(f"recovery write changed bytes: {path}")
    return path


def salvage_partial_records(data_dir: Path) -> dict[str, Any]:
    """Validate and atomically salvage generated and partial artifacts."""

    root = _trusted_data_root(data_dir)
    synthetic = root / "synthetic"
    if not synthetic.is_dir():
        raise RecoveryValidationError("salvage requires an existing synthetic directory")
    synthetic = reject_redirecting_ancestry(synthetic, where="salvage source root")
    generated = synthetic / "generated.jsonl"
    partial = synthetic / "generated-partial.jsonl"
    sources = [
        _regular_member(path, root)
        for path in (generated, partial)
        if path.exists()
    ]
    if not sources:
        raise RecoveryValidationError("salvage requires at least one existing source")
    records, captured, duplicates = _read_salvage_sources(root, sources)
    candidate = _validated_jsonl_bytes(records)
    token = uuid.uuid4().hex
    stage = synthetic / f".generated.salvage-{token}.tmp"
    _write_exclusive_bytes(stage, candidate)

    backup_path: Path | None = None
    old_generated = captured.get(generated)
    if old_generated:
        backups = _ensure_owned_directory(root, Path("recovery/backups"))
        digest = hashlib.sha256(old_generated).hexdigest()
        backup_path = backups / f"generated-{digest}.jsonl"
        try:
            _write_exclusive_bytes(backup_path, old_generated)
        except FileExistsError:
            if backup_path.read_bytes() != old_generated:
                raise RecoveryValidationError("content-addressed salvage backup collision")

    receipts = _ensure_owned_directory(root, Path("recovery/receipts"))
    receipt_path = receipts / f"salvage-{token}.json"
    receipt = {
        "status": "validated-for-publish",
        "sources": [path.relative_to(root).as_posix() for path in sources],
        "candidate_sha256": hashlib.sha256(candidate).hexdigest(),
        "records": len(records),
        "backup": backup_path.relative_to(root).as_posix() if backup_path else None,
    }
    _write_exclusive_bytes(
        receipt_path,
        (json.dumps(receipt, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8"),
    )
    if old_generated is not None and generated.read_bytes() != old_generated:
        raise RecoveryValidationError("generated source changed before salvage publication")
    if old_generated is None and generated.exists():
        raise RecoveryValidationError("generated target appeared before salvage publication")
    os.replace(stage, generated)
    return {
        "generated_before": sum(
            1 for line in (old_generated or b"").decode("utf-8").splitlines() if line.strip()
        ),
        "partial_before": sum(
            1
            for line in captured.get(partial, b"").decode("utf-8").splitlines()
            if line.strip()
        ),
        "merged_unique": len(records),
        "duplicates_dropped": duplicates,
        "generated_path": str(generated),
        "partial_path_kept": str(partial),
        "backup_path": str(backup_path) if backup_path else None,
        "receipt_path": str(receipt_path),
    }


def _write_generation_jsonl(path: Path, records: list[dict[str, Any]]) -> Path:
    return _write_exclusive_bytes(path, _validated_jsonl_bytes(records))


def publish_recovered_outputs(
    data_dir: Path,
    exact_records: list[dict[str, Any]],
    balanced_records: list[dict[str, Any]],
) -> dict[str, Any]:
    """Publish one immutable recovery generation, then switch one pointer."""

    from src.config.settings import get_data_settings

    root = _trusted_data_root(data_dir)
    recovery_root = _ensure_owned_directory(root, Path("recovery"))
    staging_root = _ensure_owned_directory(root, Path("recovery/staging"))
    versions_root = _ensure_owned_directory(root, Path("recovery/versions"))
    generation_id = uuid.uuid4().hex
    stage = _ensure_owned_directory(root, Path("recovery/staging") / generation_id)
    merged = _write_generation_jsonl(stage / "merged.jsonl", exact_records)
    balanced = _write_generation_jsonl(stage / "balanced.jsonl", balanced_records)
    split_root = _ensure_owned_directory(
        root, Path("recovery/staging") / generation_id / "splits"
    )
    split_counts: dict[str, int] = {}
    split_records = split_dataset(
        balanced_records,
        split_ratios=get_data_settings().split_ratios,
    )
    for split_name in ("train", "val", "test"):
        rows = split_records[split_name]
        _write_generation_jsonl(split_root / f"{split_name}.jsonl", rows)
        split_counts[split_name] = len(rows)
    manifest = build_manifest(stage, f"recovery-{generation_id}")
    manifest_path = save_manifest(manifest, stage / "generation-manifest.json")
    valid, errors = verify_manifest(manifest, stage)
    if not valid:
        raise RecoveryValidationError(
            "recovery generation verification failed: " + " | ".join(errors)
        )
    final = versions_root / generation_id
    os.rename(stage, final)
    final_manifest = final / manifest_path.name
    pointer = recovery_root / "current.json"
    pointer_stage = recovery_root / f".current-{generation_id}.tmp"
    pointer_payload = {
        "generation_id": generation_id,
        "relative_path": f"versions/{generation_id}",
        "manifest_sha256": hashlib.sha256(final_manifest.read_bytes()).hexdigest(),
    }
    _write_exclusive_bytes(
        pointer_stage,
        (json.dumps(pointer_payload, sort_keys=True, separators=(",", ":")) + "\n").encode(
            "utf-8"
        ),
    )
    os.replace(pointer_stage, pointer)
    return {
        "generation_id": generation_id,
        "current_pointer": pointer,
        "manifest_path": final_manifest,
        "merged_path": final / merged.name,
        "balanced_path": final / balanced.name,
        "split_dir": final / split_root.name,
        "split_counts": split_counts,
    }


__all__ = (
    "RecoveryValidationError",
    "load_recoverable_records",
    "publish_recovered_outputs",
    "recoverable_record_paths",
    "salvage_partial_records",
)
