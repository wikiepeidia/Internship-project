"""Owned generation-run paths, ledgers, staging, and identity-bound cleanup."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import stat
from typing import Any
import uuid

from src.core.integrity import (
    canonical_json_bytes,
    IntegrityError,
    prepare_bounded_output,
    read_file_bytes,
    reject_redirecting_ancestry,
    sha256_bytes,
    strict_json_object,
    write_bytes_exclusive,
)
from src.data_pipeline.core.records import DatasetRecord


_RUN_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
_MARKER_SCHEMA = "vnphish-generation-run-v1"
_CANDIDATE_SCHEMA = "vnphish-generated-candidate-v1"


@dataclass(frozen=True, slots=True)
class OwnedFile:
    path: Path
    device: int
    inode: int
    size: int
    modified_ns: int


@dataclass(frozen=True, slots=True)
class GenerationRun:
    data_root: Path
    run_id: str
    run_root: Path
    checkpoints: Path
    marker: Path
    ledger: Path


@dataclass(frozen=True, slots=True)
class GeneratedCandidate:
    """Hash-bound generated rows accepted by the judging workflow."""

    path: Path
    run_id: str
    sha256: str
    row_count: int
    raw: bytes


def _trusted_root(data_dir: Path) -> Path:
    root = reject_redirecting_ancestry(
        Path(os.path.abspath(data_dir)), where="generation data root"
    )
    if not root.is_dir() or root.parent == root:
        raise IntegrityError("generation data root must be a bounded directory")
    return root


def _requested_run_id(root: Path, supplied: Path | None, version_tag: str) -> str:
    if supplied is None:
        candidate = version_tag
    else:
        path = Path(supplied)
        if path.is_absolute():
            absolute = reject_redirecting_ancestry(path, where="checkpoint directory")
            try:
                parts = absolute.relative_to(root).parts
            except ValueError as error:
                raise IntegrityError("checkpoint directory escaped the data root") from error
        else:
            if ".." in path.parts or "\x00" in os.fspath(path):
                raise IntegrityError("checkpoint directory must be a bounded run path")
            parts = path.parts
        if len(parts) == 1:
            candidate = parts[0]
        elif len(parts) == 3 and parts[0] == "generation-runs" and parts[2] == "checkpoints":
            candidate = parts[1]
        else:
            raise IntegrityError(
                "checkpoint directory must identify generation-runs/<run-id>/checkpoints"
            )
    if not _RUN_ID.fullmatch(candidate):
        raise IntegrityError(f"invalid generation run id: {candidate!r}")
    return candidate


def _ensure_directory(path: Path, root: Path, *, where: str) -> Path:
    try:
        relative = Path(path).relative_to(root)
    except ValueError as error:
        raise IntegrityError(f"{where} escaped the generation data root") from error
    path = prepare_bounded_output(
        root, relative / ".directory-boundary", where=where
    ).parent
    if root not in path.parents or not path.is_dir():
        raise IntegrityError(f"{where} escaped the generation data root")
    return path


def _marker_payload(root: Path, run_id: str) -> dict[str, str]:
    return {
        "schema": _MARKER_SCHEMA,
        "run_id": run_id,
        "data_root": os.fspath(root),
    }


def _claim_or_validate_run(run: GenerationRun, *, resume: bool) -> None:
    expected = _marker_payload(run.data_root, run.run_id)
    if run.marker.exists():
        actual = strict_json_object(run.marker, where="generation run marker")
        if actual != expected:
            raise IntegrityError("generation run marker does not match the requested run")
        return
    unexpected = [path for path in run.run_root.iterdir() if path != run.checkpoints]
    checkpoint_members = list(run.checkpoints.iterdir())
    if unexpected or checkpoint_members:
        raise IntegrityError("unclaimed generation run directory is not empty")
    if resume:
        raise IntegrityError("cannot resume a generation run without its ownership marker")
    marker_bytes = (json.dumps(expected, sort_keys=True, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )
    write_bytes_exclusive(run.marker, marker_bytes, where="generation run marker")


def prepare_generation_run(
    data_dir: Path,
    *,
    version_tag: str,
    checkpoint_dir: Path | None,
    resume: bool,
) -> GenerationRun:
    """Validate and claim one exact owned generation-run directory."""

    root = _trusted_root(data_dir)
    run_id = _requested_run_id(root, checkpoint_dir, version_tag)
    runs_root = _ensure_directory(root / "generation-runs", root, where="generation runs")
    run_root = _ensure_directory(runs_root / run_id, root, where="generation run")
    checkpoints = _ensure_directory(
        run_root / "checkpoints", root, where="generation checkpoints"
    )
    run = GenerationRun(
        data_root=root,
        run_id=run_id,
        run_root=run_root,
        checkpoints=checkpoints,
        marker=run_root / "ownership.json",
        ledger=run_root / "ledger.json",
    )
    _claim_or_validate_run(run, resume=resume)
    return run


def _owned_file(path: Path, run: GenerationRun) -> OwnedFile:
    candidate = reject_redirecting_ancestry(path, where="generation run member")
    if candidate.parent != run.checkpoints:
        raise IntegrityError("generation run member escaped its checkpoint directory")
    metadata = os.lstat(candidate)
    if not stat.S_ISREG(metadata.st_mode):
        raise IntegrityError("generation run member is not a regular file")
    return OwnedFile(
        path=candidate,
        device=metadata.st_dev,
        inode=metadata.st_ino,
        size=metadata.st_size,
        modified_ns=metadata.st_mtime_ns,
    )


def snapshot_run_files(run: GenerationRun) -> dict[str, OwnedFile]:
    """Capture exact identities of every file in one owned checkpoint directory."""

    snapshot: dict[str, OwnedFile] = {}
    for path in run.checkpoints.iterdir():
        owned = _owned_file(path, run)
        snapshot[path.name] = owned
    return snapshot


def newly_owned_files(
    before: dict[str, OwnedFile],
    after: dict[str, OwnedFile],
) -> tuple[OwnedFile, ...]:
    return tuple(
        after[name]
        for name in sorted(after)
        if name not in before or after[name] != before[name]
    )


def write_run_ledger(run: GenerationRun, files: tuple[OwnedFile, ...]) -> Path:
    payload = {
        "schema": _MARKER_SCHEMA,
        "run_id": run.run_id,
        "owned_files": [
            {
                "path": owned.path.relative_to(run.data_root).as_posix(),
                "device": owned.device,
                "inode": owned.inode,
                "size": owned.size,
                "modified_ns": owned.modified_ns,
            }
            for owned in files
        ],
    }
    value = (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )
    stage = run.run_root / f".ledger-{uuid.uuid4().hex}.tmp"
    write_bytes_exclusive(stage, value, where="generation run ledger stage")
    os.replace(stage, run.ledger)
    return run.ledger


def cleanup_owned_files(files: tuple[OwnedFile, ...]) -> None:
    """Delete only files whose current identity still matches the run ledger."""

    for owned in files:
        try:
            metadata = os.lstat(owned.path)
        except FileNotFoundError:
            continue
        current = (
            metadata.st_dev,
            metadata.st_ino,
            metadata.st_size,
            metadata.st_mtime_ns,
        )
        expected = (owned.device, owned.inode, owned.size, owned.modified_ns)
        if current == expected and stat.S_ISREG(metadata.st_mode):
            owned.path.unlink()


def stage_generated_records(
    run: GenerationRun,
    records: list[dict[str, Any]],
) -> Path:
    """Write and re-validate one unique complete generation candidate."""

    candidate = run.checkpoints / f"generated-complete-{uuid.uuid4().hex}.jsonl"
    with candidate.open("xb") as handle:
        for record in records:
            validated = DatasetRecord.model_validate(record)
            handle.write((validated.model_dump_json() + "\n").encode("utf-8"))
        handle.flush()
        os.fsync(handle.fileno())
    with candidate.open("r", encoding="utf-8", errors="strict") as handle:
        reloaded = [
            DatasetRecord.model_validate_json(line).model_dump()
            for line in handle
            if line.strip()
        ]
    if reloaded != [DatasetRecord.model_validate(record).model_dump() for record in records]:
        raise IntegrityError("generated candidate changed during staging")
    return candidate


def publish_generated_candidate(
    run: GenerationRun,
    candidate: Path,
    stable_name: str,
) -> Path:
    """Atomically replace one fixed stable output after candidate validation."""

    if stable_name not in {"generated.jsonl", "generated-gap-fill-recovered.jsonl"}:
        raise IntegrityError("unsupported stable generation artifact name")
    candidate = _owned_file(candidate, run).path
    synthetic = _ensure_directory(
        run.data_root / "synthetic", run.data_root, where="synthetic output"
    )
    target = synthetic / stable_name
    reject_redirecting_ancestry(target, where="stable generated output")
    os.replace(candidate, target)
    raw = read_file_bytes(target, where="stable generated output")
    row_count = sum(1 for line in raw.splitlines() if line.strip())
    marker = target.with_name(f"{target.name}.provenance.json")
    marker_payload = {
        "schema": _CANDIDATE_SCHEMA,
        "kind": "synthetic_generated_candidate",
        "run_id": run.run_id,
        "path": target.relative_to(run.data_root).as_posix(),
        "sha256": sha256_bytes(raw),
        "row_count": row_count,
    }
    stage = run.run_root / f".candidate-provenance-{uuid.uuid4().hex}.tmp"
    write_bytes_exclusive(
        stage,
        canonical_json_bytes(marker_payload),
        where="generated candidate provenance stage",
    )
    reject_redirecting_ancestry(marker, where="generated candidate provenance")
    os.replace(stage, marker)
    return target


def resolve_generated_candidate(data_dir: Path, supplied_path: Path) -> GeneratedCandidate:
    """Resolve only a hash-bound published synthetic candidate, never a final split."""

    root = _trusted_root(data_dir)
    supplied = Path(supplied_path)
    candidate = supplied if supplied.is_absolute() else root / supplied
    candidate = Path(os.path.abspath(os.path.normpath(os.fspath(candidate))))
    try:
        relative = candidate.relative_to(root)
    except ValueError as error:
        raise IntegrityError("generated candidate escaped the data root") from error
    if not relative.parts or relative.parts[0] in {
        "splits",
        "processed",
        "versions",
        "releases",
    }:
        raise IntegrityError("finalized dataset trees cannot be used as generated input")
    if relative.parts != ("synthetic", candidate.name) or candidate.name not in {
        "generated.jsonl",
        "generated-gap-fill-recovered.jsonl",
    }:
        raise IntegrityError("generated input must be a published synthetic candidate")

    candidate = reject_redirecting_ancestry(candidate, where="generated candidate")
    try:
        marker = reject_redirecting_ancestry(
            candidate.with_name(f"{candidate.name}.provenance.json"),
            where="generated candidate provenance",
        )
        payload = strict_json_object(marker, where="generated candidate provenance")
    except FileNotFoundError as error:
        raise IntegrityError("generated candidate provenance is missing") from error
    expected_fields = {"schema", "kind", "run_id", "path", "sha256", "row_count"}
    if set(payload) != expected_fields:
        raise IntegrityError("generated candidate provenance fields are not closed")
    if payload["schema"] != _CANDIDATE_SCHEMA or payload["kind"] != "synthetic_generated_candidate":
        raise IntegrityError("generated candidate provenance schema is invalid")
    if payload["path"] != relative.as_posix():
        raise IntegrityError("generated candidate provenance path does not match")
    run_id = payload["run_id"]
    if not isinstance(run_id, str) or not _RUN_ID.fullmatch(run_id):
        raise IntegrityError("generated candidate provenance run_id is invalid")
    raw = read_file_bytes(candidate, where="generated candidate")
    digest = sha256_bytes(raw)
    if payload["sha256"] != digest:
        raise IntegrityError("generated candidate hash does not match provenance")
    rows = [line for line in raw.splitlines() if line.strip()]
    if isinstance(payload["row_count"], bool) or payload["row_count"] != len(rows):
        raise IntegrityError("generated candidate row count does not match provenance")
    for line in rows:
        DatasetRecord.model_validate_json(line)
    return GeneratedCandidate(candidate, run_id, digest, len(rows), raw)


__all__ = (
    "GeneratedCandidate",
    "GenerationRun",
    "OwnedFile",
    "cleanup_owned_files",
    "newly_owned_files",
    "prepare_generation_run",
    "publish_generated_candidate",
    "resolve_generated_candidate",
    "snapshot_run_files",
    "stage_generated_records",
    "write_run_ledger",
)
