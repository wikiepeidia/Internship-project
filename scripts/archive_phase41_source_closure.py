"""Archive and verify the exact source closure that produced Phase 41 evidence."""

from __future__ import annotations

import argparse
from dataclasses import dataclass, replace
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import stat
import sys
from typing import Any, Mapping, Sequence


EXPECTED_SCHEMA_VERSION = "phase41-execution-source-manifest-v1"
EXPECTED_TREE_SHA256 = "c3bbc8c8adaf7579fd2eb9c59a0081613be4b2cae05dfdb64472938c7e6d0434"
EXPECTED_LAUNCHER_SHA256 = "c5f15a32b2c8d8ee196e3ec484707c27c4c05e5389d958626e775e44f52d49e9"
EXPECTED_MANIFEST_SHA256 = "41a3a7e166dd5077b3b2c689868b862bd5665137e1824094eb5ff1cdce2b0c61"
PROVENANCE_LABEL = "post_evaluation_archival_mirror_not_refactored_metric_producer"
RECEIPT_SCHEMA_VERSION = "phase411-source-closure-archival-receipt-v1"
_WINDOWS_REPARSE_POINT = 0x00000400
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_MANIFEST_KEYS = {
    "alternate_evaluators_permitted",
    "closed_import_roots",
    "files",
    "launcher",
    "launcher_host",
    "preparation_scope",
    "python",
    "schema_version",
    "source_tree_sha256",
    "upstream_declared_source_tree_sha256",
}
_SOURCE_PATHS = (
    "src/__init__.py",
    "src/config/__init__.py",
    "src/config/settings.py",
    "src/data_pipeline/__init__.py",
    "src/data_pipeline/schemas.py",
    "src/model_adaptation/__init__.py",
    "src/model_adaptation/catalog.py",
    "src/model_adaptation/cli.py",
    "src/model_adaptation/convert.py",
    "src/model_adaptation/data.py",
    "src/model_adaptation/doctor.py",
    "src/model_adaptation/phase40_callbacks.py",
    "src/model_adaptation/phase40_comparison_launch.py",
    "src/model_adaptation/phase40_contract.py",
    "src/model_adaptation/phase40_evidence.py",
    "src/model_adaptation/phase40_final_authority.py",
    "src/model_adaptation/phase40_gguf.py",
    "src/model_adaptation/phase40_graphs.py",
    "src/model_adaptation/phase40_handoff.py",
    "src/model_adaptation/phase40_metrics.py",
    "src/model_adaptation/phase40_modes.py",
    "src/model_adaptation/phase40_notebooks.py",
    "src/model_adaptation/phase40_phobert_release.py",
    "src/model_adaptation/phase40_production_authorities.py",
    "src/model_adaptation/phase40_release_authorities.py",
    "src/model_adaptation/phase40_review.py",
    "src/model_adaptation/phase40_runtime_materialize.py",
    "src/model_adaptation/phase41_evaluation.py",
    "src/model_adaptation/phase41_protocols.py",
    "src/model_adaptation/phobert_training.py",
    "src/model_adaptation/pilot.py",
    "src/model_adaptation/prompts.py",
    "src/model_adaptation/registry.py",
    "src/model_adaptation/schemas.py",
    "src/model_adaptation/training.py",
    "src/runtime/__init__.py",
    "src/runtime/contracts.py",
)
_WORKTREE_MISMATCHES = (
    "src/model_adaptation/cli.py",
    "src/model_adaptation/phase41_evaluation.py",
)
_REPO_ROOT = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
PRODUCTION_EVIDENCE_ROOT = Path(r"C:\ProgramData\VNPhish\phase41-evaluation-evidence")
PRODUCTION_SOURCE_ROOT = PRODUCTION_EVIDENCE_ROOT / "clean-runtime"
PRODUCTION_LAUNCHER_PATH = (
    PRODUCTION_EVIDENCE_ROOT / "scripts" / "phase41_one_shot_launcher.ps1"
)
PRODUCTION_MANIFEST_PATH = (
    _REPO_ROOT
    / "data/models/phase41/verified-export"
    / "9ac54d58c273ab0a8c2f2b4b61e472a51ca94231a94b6847637ecad6ceee49f7"
    / "execution-source-manifest.json"
)
PRODUCTION_DESTINATION = (
    _REPO_ROOT / "historical/phase41-source-closure" / EXPECTED_TREE_SHA256
)


class ArchiveError(RuntimeError):
    """Raised when the fixed source closure cannot be archived or verified."""


@dataclass(frozen=True, slots=True)
class _ArchiveLayout:
    manifest_path: Path
    evidence_root: Path
    source_root: Path
    launcher_path: Path
    destination: Path
    repo_root: Path
    expected_manifest_sha256: str
    expected_schema_version: str
    expected_tree_sha256: str
    expected_launcher_sha256: str
    expected_source_paths: tuple[str, ...]
    expected_worktree_mismatches: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ArchiveReceipt:
    schema_version: str
    manifest_sha256: str
    source_tree_sha256: str
    launcher_sha256: str
    source_manifest_origin: str
    clean_runtime_origin: str
    launcher_origin: str
    archived_at_utc: str
    archive_destination: str
    file_count: int
    payload_file_count: int
    current_worktree_mismatches: tuple[dict[str, str], ...]
    provenance_label: str
    receipt_sha256: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "archive_destination": self.archive_destination,
            "archived_at_utc": self.archived_at_utc,
            "clean_runtime_origin": self.clean_runtime_origin,
            "current_worktree_mismatches": list(self.current_worktree_mismatches),
            "file_count": self.file_count,
            "launcher_origin": self.launcher_origin,
            "launcher_sha256": self.launcher_sha256,
            "manifest_sha256": self.manifest_sha256,
            "payload_file_count": self.payload_file_count,
            "provenance_label": self.provenance_label,
            "receipt_sha256": self.receipt_sha256,
            "schema_version": self.schema_version,
            "source_manifest_origin": self.source_manifest_origin,
            "source_tree_sha256": self.source_tree_sha256,
        }


@dataclass(frozen=True, slots=True)
class _CapturedClosure:
    manifest_raw: bytes
    records: tuple[dict[str, Any], ...]
    launcher_record: dict[str, Any]
    payloads: tuple[tuple[str, bytes], ...]
    mismatches: tuple[dict[str, str], ...]


def _canonical_json(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _write_console_safe(message: object) -> None:
    """Write exact text without letting a legacy Windows console change success."""

    text = str(message)
    target = sys.stdout
    encoding = getattr(target, "encoding", None) or "utf-8"
    try:
        safe_text = text.encode(encoding, errors="backslashreplace").decode(encoding)
    except LookupError:
        safe_text = text.encode("ascii", errors="backslashreplace").decode("ascii")
    try:
        target.write(safe_text)
    except UnicodeEncodeError:
        target.write(text.encode("ascii", errors="backslashreplace").decode("ascii"))
    flush = getattr(target, "flush", None)
    if callable(flush):
        flush()


def _strict_json(raw: bytes, *, where: str) -> dict[str, Any]:
    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ArchiveError(f"{where} contains duplicate JSON key {key!r}")
            result[key] = value
        return result

    def reject_non_finite(token: str) -> Any:
        raise ArchiveError(f"{where} contains non-standard JSON token {token!r}")

    try:
        value = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=reject_duplicates,
            parse_constant=reject_non_finite,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ArchiveError(f"{where} must be strict UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise ArchiveError(f"{where} must be a JSON object")
    return value


def _require_sha256(value: object, *, where: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise ArchiveError(f"{where} must be lowercase SHA-256")
    return value


def _bounded_relative(value: object, *, where: str) -> str:
    if not isinstance(value, str) or not value or "\x00" in value or "\\" in value:
        raise ArchiveError(f"{where} path is invalid")
    path = PurePosixPath(value)
    if path.is_absolute() or value != path.as_posix() or any(
        part in {"", ".", ".."} for part in path.parts
    ):
        raise ArchiveError(f"{where} path must be bounded POSIX-relative")
    return value


def _manifest_records(
    layout: _ArchiveLayout, raw: bytes
) -> tuple[tuple[dict[str, Any], ...], dict[str, Any]]:
    if _sha256(raw) != layout.expected_manifest_sha256:
        raise ArchiveError("manifest SHA-256 does not match the fixed authority")
    manifest = _strict_json(raw, where="execution source manifest")
    if set(manifest) != _MANIFEST_KEYS:
        raise ArchiveError("execution source manifest schema fields are not exact")
    if manifest.get("schema_version") != layout.expected_schema_version:
        raise ArchiveError("execution source manifest schema version is wrong")
    if manifest.get("source_tree_sha256") != layout.expected_tree_sha256:
        raise ArchiveError("execution source manifest tree SHA-256 is wrong")
    files = manifest.get("files")
    if not isinstance(files, list):
        raise ArchiveError("execution source manifest files must be a list")
    records: list[dict[str, Any]] = []
    for index, item in enumerate(files):
        if not isinstance(item, dict) or set(item) != {"bytes", "path", "sha256"}:
            raise ArchiveError(f"manifest file record {index} schema is invalid")
        relative = _bounded_relative(item.get("path"), where=f"manifest file {index}")
        size = item.get("bytes")
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            raise ArchiveError(f"manifest file {index} bytes are invalid")
        records.append(
            {"bytes": size, "path": relative, "sha256": _require_sha256(
                item.get("sha256"), where=f"manifest file {index} SHA-256"
            )}
        )
    paths = tuple(item["path"] for item in records)
    if paths != layout.expected_source_paths or len(set(paths)) != len(paths):
        raise ArchiveError("manifest source membership or order is not exact")
    launcher = manifest.get("launcher")
    if not isinstance(launcher, dict) or set(launcher) != {"bytes", "path", "sha256"}:
        raise ArchiveError("manifest launcher schema is invalid")
    launcher_path = _bounded_relative(launcher.get("path"), where="manifest launcher")
    launcher_size = launcher.get("bytes")
    launcher_sha = _require_sha256(launcher.get("sha256"), where="launcher SHA-256")
    if (
        launcher_path != "scripts/phase41_one_shot_launcher.ps1"
        or not isinstance(launcher_size, int)
        or isinstance(launcher_size, bool)
        or launcher_size < 0
        or launcher_sha != layout.expected_launcher_sha256
    ):
        raise ArchiveError("manifest launcher authority is not exact")
    return tuple(records), {
        "bytes": launcher_size,
        "path": launcher_path,
        "sha256": launcher_sha,
    }


def _absolute(path: Path) -> Path:
    return Path(os.path.abspath(os.path.normpath(os.fspath(path))))


def _redirecting(metadata: os.stat_result) -> bool:
    return bool(
        stat.S_ISLNK(metadata.st_mode)
        or int(getattr(metadata, "st_file_attributes", 0)) & _WINDOWS_REPARSE_POINT
    )


def _validate_ancestry(root: Path, target: Path, *, target_file: bool, where: str) -> None:
    root_abs, target_abs = _absolute(root), _absolute(target)
    try:
        common = Path(os.path.commonpath((os.fspath(root_abs), os.fspath(target_abs))))
    except ValueError as exc:
        raise ArchiveError(f"{where} escaped its fixed evidence root") from exc
    if common != root_abs or target_abs == root_abs:
        raise ArchiveError(f"{where} escaped its fixed evidence root")
    components = [root_abs]
    relative = target_abs.relative_to(root_abs)
    current = root_abs
    for part in relative.parts:
        current /= part
        components.append(current)
    for component in components:
        try:
            metadata = os.lstat(component)
        except OSError as exc:
            raise ArchiveError(f"{where} is missing") from exc
        if _redirecting(metadata):
            raise ArchiveError(f"{where} ancestry contains a symlink or reparse point")
    final = os.lstat(target_abs)
    if target_file and not stat.S_ISREG(final.st_mode):
        raise ArchiveError(f"{where} must be a regular file")
    if not target_file and not stat.S_ISDIR(final.st_mode):
        raise ArchiveError(f"{where} must be a directory")


def _validate_output_destination(path: Path) -> Path:
    supplied = Path(path)
    if not supplied.is_absolute() or ".." in supplied.parts or "\x00" in os.fspath(supplied):
        raise ArchiveError("archive destination must be canonical and absolute")
    destination = _absolute(supplied)
    parent = destination.parent
    if os.path.lexists(destination):
        raise ArchiveError("archive destination already exists; collision refused")
    for component in reversed((parent, *parent.parents)):
        try:
            metadata = os.lstat(component)
        except OSError as exc:
            raise ArchiveError("archive destination parent is missing") from exc
        if _redirecting(metadata):
            raise ArchiveError("archive destination ancestry contains a symlink or reparse point")
    if not stat.S_ISDIR(os.lstat(parent).st_mode):
        raise ArchiveError("archive destination parent must be a directory")
    return destination


def _paths_overlap(first: Path, second: Path) -> bool:
    first_abs, second_abs = _absolute(first), _absolute(second)
    try:
        common = Path(os.path.commonpath((os.fspath(first_abs), os.fspath(second_abs))))
    except ValueError:
        return False
    return common in {first_abs, second_abs}


def _capture_file(path: Path, record: Mapping[str, Any], *, where: str) -> bytes:
    before = os.lstat(path)
    if _redirecting(before) or not stat.S_ISREG(before.st_mode):
        raise ArchiveError(f"{where} must be a non-redirecting regular file")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise ArchiveError(f"cannot capture {where}") from exc
    try:
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    if (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino):
        raise ArchiveError(f"{where} changed identity during capture")
    raw = b"".join(chunks)
    if len(raw) != record["bytes"]:
        raise ArchiveError(f"{where} bytes/hash do not match the manifest")
    if _sha256(raw) != record["sha256"]:
        raise ArchiveError(f"{where} hash does not match the manifest")
    return raw


def _worktree_mismatches(
    layout: _ArchiveLayout, records: Sequence[Mapping[str, Any]]
) -> tuple[dict[str, str], ...]:
    mismatches: list[dict[str, str]] = []
    for record in records:
        path = _absolute(layout.repo_root / PurePosixPath(record["path"]))
        try:
            raw = path.read_bytes()
            actual = _sha256(raw)
        except OSError:
            actual = "missing"
        if actual != record["sha256"]:
            mismatches.append(
                {"actual_sha256": actual, "expected_sha256": record["sha256"], "path": record["path"]}
            )
    if tuple(item["path"] for item in mismatches) != layout.expected_worktree_mismatches:
        raise ArchiveError("current worktree mismatch set is not the fixed expected set")
    return tuple(mismatches)


def _capture_closure(layout: _ArchiveLayout) -> _CapturedClosure:
    _validate_output_destination(layout.destination)
    if _paths_overlap(layout.source_root, layout.destination) or _paths_overlap(
        layout.evidence_root, layout.destination
    ):
        raise ArchiveError("source and archive destination overlap")
    try:
        manifest_raw = layout.manifest_path.read_bytes()
    except OSError as exc:
        raise ArchiveError("fixed execution source manifest is missing") from exc
    records, launcher_record = _manifest_records(layout, manifest_raw)
    _validate_ancestry(layout.evidence_root, layout.source_root, target_file=False, where="clean runtime")
    _validate_ancestry(layout.evidence_root, layout.launcher_path, target_file=True, where="fixed launcher")
    payloads: list[tuple[str, bytes]] = []
    for record in records:
        source = layout.source_root / PurePosixPath(record["path"])
        _validate_ancestry(layout.source_root, source, target_file=True, where=record["path"])
        payloads.append((record["path"], _capture_file(source, record, where=record["path"])))
    launcher_raw = _capture_file(layout.launcher_path, launcher_record, where="fixed launcher")
    payloads.append((launcher_record["path"], launcher_raw))
    return _CapturedClosure(
        manifest_raw=manifest_raw,
        records=records,
        launcher_record=launcher_record,
        payloads=tuple(payloads),
        mismatches=_worktree_mismatches(layout, records),
    )


def _ensure_archive_parent(root: Path, parent: Path) -> None:
    root_abs, parent_abs = _absolute(root), _absolute(parent)
    try:
        relative = parent_abs.relative_to(root_abs)
    except ValueError as exc:
        raise ArchiveError("archive member escaped its staging root") from exc
    current = root_abs
    for part in relative.parts:
        current /= part
        try:
            os.mkdir(current)
        except FileExistsError:
            pass
        metadata = os.lstat(current)
        if _redirecting(metadata) or not stat.S_ISDIR(metadata.st_mode):
            raise ArchiveError("archive member ancestry is not a regular directory")


def _write_exclusive(root: Path, relative: Path, raw: bytes) -> None:
    path = _absolute(root / relative)
    _ensure_archive_parent(root, path.parent)
    flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_BINARY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    try:
        descriptor = os.open(path, flags, 0o600)
    except OSError as exc:
        raise ArchiveError(f"exclusive archive write failed: {path.name}") from exc
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise ArchiveError("exclusive archive target is not a regular file")
        view = memoryview(raw)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise ArchiveError("exclusive archive write made no progress")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    after = os.lstat(path)
    if _redirecting(after) or (after.st_dev, after.st_ino) != (metadata.st_dev, metadata.st_ino):
        raise ArchiveError("exclusive archive target changed identity")


def _receipt_without_hash(receipt: ArchiveReceipt) -> dict[str, Any]:
    payload = receipt.as_dict()
    payload.pop("receipt_sha256")
    return payload


def _publish(layout: _ArchiveLayout, captured: _CapturedClosure) -> ArchiveReceipt:
    destination = _validate_output_destination(layout.destination)
    staging = destination.with_name(
        f".{destination.name}.staging-{secrets.token_hex(8)}"
    )
    _validate_output_destination(staging)
    try:
        os.mkdir(staging)
    except OSError as exc:
        raise ArchiveError("archive staging collision during publication") from exc
    stage_layout = replace(layout, destination=staging)
    _write_exclusive(
        staging,
        Path("execution-source-manifest.json"),
        captured.manifest_raw,
    )
    for relative, raw in captured.payloads:
        _write_exclusive(staging, Path("tree") / PurePosixPath(relative), raw)
    _verify_payloads(
        stage_layout,
        captured.records,
        captured.launcher_record,
        captured.manifest_raw,
    )
    provisional = ArchiveReceipt(
        schema_version=RECEIPT_SCHEMA_VERSION,
        manifest_sha256=_sha256(captured.manifest_raw),
        source_tree_sha256=layout.expected_tree_sha256,
        launcher_sha256=layout.expected_launcher_sha256,
        source_manifest_origin=os.fspath(_absolute(layout.manifest_path)),
        clean_runtime_origin=os.fspath(_absolute(layout.source_root)),
        launcher_origin=os.fspath(_absolute(layout.launcher_path)),
        archived_at_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        archive_destination=os.fspath(_absolute(layout.destination)),
        file_count=len(captured.records),
        payload_file_count=len(captured.records) + 1,
        current_worktree_mismatches=captured.mismatches,
        provenance_label=PROVENANCE_LABEL,
        receipt_sha256="",
    )
    receipt_payload = _receipt_without_hash(provisional)
    receipt_payload["current_worktree_mismatches"] = provisional.current_worktree_mismatches
    receipt_payload["receipt_sha256"] = _sha256(
        _canonical_json(_receipt_without_hash(provisional))
    )
    receipt = ArchiveReceipt(**receipt_payload)
    _write_exclusive(
        staging,
        Path("archival-receipt.json"),
        _canonical_json(receipt.as_dict()),
    )
    _receipt_from_raw((staging / "archival-receipt.json").read_bytes())
    _validate_output_destination(destination)
    try:
        os.rename(staging, destination)
    except OSError as exc:
        raise ArchiveError(
            f"archive staging retained after failed publication: {staging}"
        ) from exc
    return _verify_archived_source_closure_for_test(layout)


def _verify_payloads(
    layout: _ArchiveLayout,
    records: Sequence[Mapping[str, Any]],
    launcher: Mapping[str, Any],
    manifest_raw: bytes,
) -> None:
    manifest_copy = layout.destination / "execution-source-manifest.json"
    manifest_record = {
        "bytes": len(manifest_raw),
        "sha256": _sha256(manifest_raw),
    }
    if _capture_file(manifest_copy, manifest_record, where="archived manifest") != manifest_raw:
        raise ArchiveError("archived manifest bytes drifted")
    expected: dict[str, Mapping[str, Any]] = {
        f"tree/{record['path']}": record for record in records
    }
    expected[f"tree/{launcher['path']}"] = launcher
    for relative, record in expected.items():
        path = layout.destination / PurePosixPath(relative)
        raw = _capture_file(path, record, where=f"archived {relative}")
        if _sha256(raw) != record["sha256"]:
            raise ArchiveError(f"archived {relative} hash drifted")
    actual_files, actual_directories = _scan_exact_tree(layout.destination / "tree")
    expected_files = {relative.removeprefix("tree/") for relative in expected}
    expected_directories = {
        parent.as_posix()
        for relative in expected_files
        for parent in PurePosixPath(relative).parents
        if parent.as_posix() != "."
    }
    if actual_files != expected_files or actual_directories != expected_directories:
        raise ArchiveError("archived tree has extra or missing membership")


def _scan_exact_tree(root: Path) -> tuple[set[str], set[str]]:
    root_metadata = os.lstat(root)
    if _redirecting(root_metadata) or not stat.S_ISDIR(root_metadata.st_mode):
        raise ArchiveError("archived tree root must be a non-redirecting directory")
    files: set[str] = set()
    directories: set[str] = set()

    def visit(directory: Path, prefix: PurePosixPath) -> None:
        try:
            entries = tuple(os.scandir(directory))
        except OSError as exc:
            raise ArchiveError("cannot enumerate archived tree safely") from exc
        for entry in entries:
            metadata = entry.stat(follow_symlinks=False)
            relative = prefix / entry.name
            name = relative.as_posix()
            if _redirecting(metadata):
                raise ArchiveError("archived tree contains a link or reparse member")
            if stat.S_ISREG(metadata.st_mode):
                files.add(name)
            elif stat.S_ISDIR(metadata.st_mode):
                directories.add(name)
                visit(Path(entry.path), relative)
            else:
                raise ArchiveError("archived tree contains a non-file member")

    visit(root, PurePosixPath())
    return files, directories


def _verify_archive_root_members(destination: Path) -> None:
    expected = {
        "execution-source-manifest.json": "file",
        "tree": "directory",
        "archival-receipt.json": "file",
    }
    actual: dict[str, str] = {}
    for entry in os.scandir(destination):
        metadata = entry.stat(follow_symlinks=False)
        if _redirecting(metadata):
            raise ArchiveError("archive root contains a link or reparse member")
        if stat.S_ISREG(metadata.st_mode):
            actual[entry.name] = "file"
        elif stat.S_ISDIR(metadata.st_mode):
            actual[entry.name] = "directory"
        else:
            raise ArchiveError("archive root contains a non-file member")
    if actual != expected:
        raise ArchiveError("archive root membership is not exact")


def _receipt_from_raw(raw: bytes) -> ArchiveReceipt:
    payload = _strict_json(raw, where="archival receipt")
    expected_keys = set(ArchiveReceipt.__dataclass_fields__)
    if set(payload) != expected_keys:
        raise ArchiveError("archival receipt schema fields are not exact")
    mismatches = payload.get("current_worktree_mismatches")
    if not isinstance(mismatches, list) or not all(
        isinstance(item, dict)
        and set(item) == {"actual_sha256", "expected_sha256", "path"}
        for item in mismatches
    ):
        raise ArchiveError("archival receipt mismatch records are malformed")
    for index, item in enumerate(mismatches):
        _bounded_relative(item["path"], where=f"receipt mismatch {index} path")
        _require_sha256(
            item["expected_sha256"], where=f"receipt mismatch {index} expected SHA-256"
        )
        if item["actual_sha256"] != "missing":
            _require_sha256(
                item["actual_sha256"], where=f"receipt mismatch {index} actual SHA-256"
            )
    for field_name in (
        "manifest_sha256",
        "source_tree_sha256",
        "launcher_sha256",
        "receipt_sha256",
    ):
        _require_sha256(payload.get(field_name), where=f"receipt {field_name}")
    for field_name in ("file_count", "payload_file_count"):
        value = payload.get(field_name)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ArchiveError(f"receipt {field_name} must be a non-negative integer")
    timestamp = payload.get("archived_at_utc")
    if not isinstance(timestamp, str):
        raise ArchiveError("receipt timestamp must be canonical UTC text")
    try:
        parsed_timestamp = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise ArchiveError("receipt timestamp must be canonical UTC text") from exc
    if parsed_timestamp.strftime("%Y-%m-%dT%H:%M:%SZ") != timestamp:
        raise ArchiveError("receipt timestamp must be canonical UTC text")
    for field_name in (
        "source_manifest_origin",
        "clean_runtime_origin",
        "launcher_origin",
        "archive_destination",
        "provenance_label",
        "schema_version",
    ):
        value = payload.get(field_name)
        if not isinstance(value, str) or not value:
            raise ArchiveError(f"receipt {field_name} must be non-empty text")
    payload["current_worktree_mismatches"] = tuple(mismatches)
    try:
        receipt = ArchiveReceipt(**payload)
    except TypeError as exc:
        raise ArchiveError("archival receipt schema is invalid") from exc
    expected_hash = _sha256(_canonical_json(_receipt_without_hash(receipt)))
    if receipt.receipt_sha256 != expected_hash:
        raise ArchiveError("archival receipt self-hash is invalid")
    return receipt


def _verify_archived_source_closure_for_test(layout: _ArchiveLayout) -> ArchiveReceipt:
    _validate_ancestry(
        layout.destination.parent,
        layout.destination,
        target_file=False,
        where="archive destination",
    )
    _verify_archive_root_members(layout.destination)
    manifest_copy = layout.destination / "execution-source-manifest.json"
    try:
        manifest_raw = manifest_copy.read_bytes()
    except OSError as exc:
        raise ArchiveError("archived manifest is missing") from exc
    records, launcher = _manifest_records(layout, manifest_raw)
    _verify_payloads(layout, records, launcher, manifest_raw)
    try:
        receipt = _receipt_from_raw((layout.destination / "archival-receipt.json").read_bytes())
    except OSError as exc:
        raise ArchiveError("archival receipt is missing") from exc
    if (
        receipt.schema_version != RECEIPT_SCHEMA_VERSION
        or receipt.manifest_sha256 != layout.expected_manifest_sha256
        or receipt.source_tree_sha256 != layout.expected_tree_sha256
        or receipt.launcher_sha256 != layout.expected_launcher_sha256
        or receipt.source_manifest_origin != os.fspath(_absolute(layout.manifest_path))
        or receipt.clean_runtime_origin != os.fspath(_absolute(layout.source_root))
        or receipt.launcher_origin != os.fspath(_absolute(layout.launcher_path))
        or receipt.archive_destination != os.fspath(_absolute(layout.destination))
        or receipt.file_count != len(records)
        or receipt.payload_file_count != len(records) + 1
        or receipt.provenance_label != PROVENANCE_LABEL
        or tuple(item.get("path") for item in receipt.current_worktree_mismatches)
        != layout.expected_worktree_mismatches
    ):
        raise ArchiveError("archival receipt does not bind the fixed closure")
    record_hashes = {record["path"]: record["sha256"] for record in records}
    for mismatch in receipt.current_worktree_mismatches:
        if mismatch["expected_sha256"] != record_hashes.get(mismatch["path"]):
            raise ArchiveError("archival receipt mismatch facts do not bind the source manifest")
    return receipt


def _archive_bound_source_closure_for_test(layout: _ArchiveLayout) -> ArchiveReceipt:
    return _publish(layout, _capture_closure(layout))


def _production_layout() -> _ArchiveLayout:
    return _ArchiveLayout(
        manifest_path=PRODUCTION_MANIFEST_PATH,
        evidence_root=PRODUCTION_EVIDENCE_ROOT,
        source_root=PRODUCTION_SOURCE_ROOT,
        launcher_path=PRODUCTION_LAUNCHER_PATH,
        destination=PRODUCTION_DESTINATION,
        repo_root=_REPO_ROOT,
        expected_manifest_sha256=EXPECTED_MANIFEST_SHA256,
        expected_schema_version=EXPECTED_SCHEMA_VERSION,
        expected_tree_sha256=EXPECTED_TREE_SHA256,
        expected_launcher_sha256=EXPECTED_LAUNCHER_SHA256,
        expected_source_paths=_SOURCE_PATHS,
        expected_worktree_mismatches=_WORKTREE_MISMATCHES,
    )


def archive_bound_source_closure() -> ArchiveReceipt:
    """Capture the code-fixed ProgramData closure into its fixed archive once."""

    return _archive_bound_source_closure_for_test(_production_layout())


def verify_archived_source_closure() -> ArchiveReceipt:
    """Verify only the archived closure and fixed manifest authority, not current HEAD."""

    return _verify_archived_source_closure_for_test(_production_layout())


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("archive", "verify"))
    args = parser.parse_args(argv)
    receipt = (
        archive_bound_source_closure()
        if args.command == "archive"
        else verify_archived_source_closure()
    )
    _write_console_safe(_canonical_json(receipt.as_dict()).decode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
