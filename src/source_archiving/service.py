"""Capture, publish, and verify deterministic source-closure archives."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
import os
from pathlib import Path, PurePosixPath
import secrets
from typing import Any, Callable, Mapping, Sequence

from .contracts import (
    ArchiveError,
    ArchiveReceipt,
    EXPECTED_LAUNCHER_SHA256,
    EXPECTED_MANIFEST_SHA256,
    EXPECTED_RECEIPT_SHA256,
    EXPECTED_SCHEMA_VERSION,
    EXPECTED_TREE_SHA256,
    LAUNCHER_RELATIVE_PATH,
    MANIFEST_ARCHIVE_NAME,
    PROVENANCE_LABEL,
    RECEIPT_ARCHIVE_NAME,
    RECEIPT_SCHEMA_VERSION,
    TREE_ARCHIVE_NAME,
    _ArchiveLayout,
    _CapturedClosure,
    _SOURCE_PATHS,
    _WORKTREE_MISMATCHES,
    _bounded_relative,
    _canonical_json,
    _manifest_records,
    _require_sha256,
    _sha256,
    _strict_json,
)
from .filesystem import (
    PublicationHook,
    _PublicationBinding,
    _absolute,
    _capture_file,
    _paths_overlap,
    _publication_test_hook,
    _scan_exact_tree,
    _validate_ancestry,
    _validate_output_destination,
    _verify_archive_root_members,
    _write_exclusive,
)


_REPO_ROOT = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
PRODUCTION_EVIDENCE_ROOT = Path(r"C:\ProgramData\VNPhish\phase41-evaluation-evidence")
PRODUCTION_SOURCE_ROOT = PRODUCTION_EVIDENCE_ROOT / "clean-runtime"
PRODUCTION_LAUNCHER_PATH = PRODUCTION_EVIDENCE_ROOT.joinpath(
    *PurePosixPath(LAUNCHER_RELATIVE_PATH).parts
)
PRODUCTION_MANIFEST_PATH = (
    _REPO_ROOT
    / "data/models/phase41/verified-export"
    / "9ac54d58c273ab0a8c2f2b4b61e472a51ca94231a94b6847637ecad6ceee49f7"
    / MANIFEST_ARCHIVE_NAME
)
PRODUCTION_DESTINATION = (
    _REPO_ROOT / "historical/phase41-source-closure" / EXPECTED_TREE_SHA256
)

WriteExclusive = Callable[[_PublicationBinding, Path, bytes], None]
TokenHex = Callable[[int], str]


def _worktree_mismatches(
    layout: _ArchiveLayout,
    records: Sequence[Mapping[str, Any]],
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
                {
                    "actual_sha256": actual,
                    "expected_sha256": record["sha256"],
                    "path": record["path"],
                }
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
    _validate_ancestry(
        layout.evidence_root,
        layout.source_root,
        target_file=False,
        where="clean runtime",
    )
    _validate_ancestry(
        layout.evidence_root,
        layout.launcher_path,
        target_file=True,
        where="fixed launcher",
    )
    payloads: list[tuple[str, bytes]] = []
    for record in records:
        source = layout.source_root / PurePosixPath(record["path"])
        _validate_ancestry(
            layout.source_root,
            source,
            target_file=True,
            where=record["path"],
        )
        payloads.append(
            (record["path"], _capture_file(source, record, where=record["path"]))
        )
    launcher_raw = _capture_file(
        layout.launcher_path,
        launcher_record,
        where="fixed launcher",
    )
    payloads.append((launcher_record["path"], launcher_raw))
    return _CapturedClosure(
        manifest_raw=manifest_raw,
        records=records,
        launcher_record=launcher_record,
        payloads=tuple(payloads),
        mismatches=_worktree_mismatches(layout, records),
    )


def _receipt_without_hash(receipt: ArchiveReceipt) -> dict[str, Any]:
    payload = receipt.as_dict()
    payload.pop("receipt_sha256")
    return payload


def _publish(
    layout: _ArchiveLayout,
    captured: _CapturedClosure,
    *,
    write_exclusive: WriteExclusive = _write_exclusive,
    publication_test_hook: PublicationHook = _publication_test_hook,
    clock: type[datetime] = datetime,
    token_hex: TokenHex = secrets.token_hex,
) -> ArchiveReceipt:
    destination = _validate_output_destination(layout.destination)
    staging = destination.with_name(f".{destination.name}.staging-{token_hex(8)}")
    stage_layout = replace(layout, destination=staging)
    with _PublicationBinding(
        destination,
        staging,
        publication_test_hook=publication_test_hook,
    ) as binding:
        binding.create_staging()
        write_exclusive(binding, Path(MANIFEST_ARCHIVE_NAME), captured.manifest_raw)
        for relative, raw in captured.payloads:
            write_exclusive(
                binding,
                Path(TREE_ARCHIVE_NAME) / PurePosixPath(relative),
                raw,
            )
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
            archived_at_utc=clock.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
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
        receipt_raw = _canonical_json(receipt.as_dict())
        if (
            layout.expected_receipt_sha256 is not None
            and _sha256(receipt_raw) != layout.expected_receipt_sha256
        ):
            raise ArchiveError("archival receipt does not match independent digest authority")
        write_exclusive(binding, Path(RECEIPT_ARCHIVE_NAME), receipt_raw)
        _receipt_from_raw(receipt_raw, clock=clock)
        binding.publish()
        return _verify_archived_source_closure_for_test(layout, clock=clock)


def _verify_payloads(
    layout: _ArchiveLayout,
    records: Sequence[Mapping[str, Any]],
    launcher: Mapping[str, Any],
    manifest_raw: bytes,
) -> None:
    manifest_copy = layout.destination / MANIFEST_ARCHIVE_NAME
    manifest_record = {"bytes": len(manifest_raw), "sha256": _sha256(manifest_raw)}
    if _capture_file(
        manifest_copy,
        manifest_record,
        where="archived manifest",
    ) != manifest_raw:
        raise ArchiveError("archived manifest bytes drifted")
    expected: dict[str, Mapping[str, Any]] = {
        f"{TREE_ARCHIVE_NAME}/{record['path']}": record for record in records
    }
    expected[f"{TREE_ARCHIVE_NAME}/{launcher['path']}"] = launcher
    for relative, record in expected.items():
        path = layout.destination / PurePosixPath(relative)
        raw = _capture_file(path, record, where=f"archived {relative}")
        if _sha256(raw) != record["sha256"]:
            raise ArchiveError(f"archived {relative} hash drifted")
    actual_files, actual_directories = _scan_exact_tree(
        layout.destination / TREE_ARCHIVE_NAME
    )
    expected_files = {
        relative.removeprefix(f"{TREE_ARCHIVE_NAME}/") for relative in expected
    }
    expected_directories = {
        parent.as_posix()
        for relative in expected_files
        for parent in PurePosixPath(relative).parents
        if parent.as_posix() != "."
    }
    if actual_files != expected_files or actual_directories != expected_directories:
        raise ArchiveError("archived tree has extra or missing membership")


def _receipt_from_raw(
    raw: bytes,
    *,
    clock: type[datetime] = datetime,
) -> ArchiveReceipt:
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
            item["expected_sha256"],
            where=f"receipt mismatch {index} expected SHA-256",
        )
        if item["actual_sha256"] != "missing":
            _require_sha256(
                item["actual_sha256"],
                where=f"receipt mismatch {index} actual SHA-256",
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
        parsed_timestamp = clock.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")
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


def _verify_archived_source_closure_for_test(
    layout: _ArchiveLayout,
    *,
    clock: type[datetime] = datetime,
) -> ArchiveReceipt:
    _validate_ancestry(
        layout.destination.parent,
        layout.destination,
        target_file=False,
        where="archive destination",
    )
    _verify_archive_root_members(layout.destination)
    manifest_copy = layout.destination / MANIFEST_ARCHIVE_NAME
    try:
        manifest_raw = manifest_copy.read_bytes()
    except OSError as exc:
        raise ArchiveError("archived manifest is missing") from exc
    records, launcher = _manifest_records(layout, manifest_raw)
    _verify_payloads(layout, records, launcher, manifest_raw)
    try:
        receipt_raw = (layout.destination / RECEIPT_ARCHIVE_NAME).read_bytes()
    except OSError as exc:
        raise ArchiveError("archival receipt is missing") from exc
    if layout.expected_receipt_sha256 is not None:
        _require_sha256(
            layout.expected_receipt_sha256,
            where="independent archival receipt SHA-256",
        )
        if _sha256(receipt_raw) != layout.expected_receipt_sha256:
            raise ArchiveError("archival receipt does not match independent digest authority")
    receipt = _receipt_from_raw(receipt_raw, clock=clock)
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
            raise ArchiveError(
                "archival receipt mismatch facts do not bind the source manifest"
            )
    return receipt


def _archive_bound_source_closure_for_test(
    layout: _ArchiveLayout,
    *,
    write_exclusive: WriteExclusive = _write_exclusive,
    publication_test_hook: PublicationHook = _publication_test_hook,
    clock: type[datetime] = datetime,
    token_hex: TokenHex = secrets.token_hex,
) -> ArchiveReceipt:
    captured = _capture_closure(layout)
    return _publish(
        layout,
        captured,
        write_exclusive=write_exclusive,
        publication_test_hook=publication_test_hook,
        clock=clock,
        token_hex=token_hex,
    )


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
        expected_receipt_sha256=EXPECTED_RECEIPT_SHA256,
    )


def archive_bound_source_closure() -> ArchiveReceipt:
    """Capture the code-fixed production closure into its fixed archive once."""

    return _archive_bound_source_closure_for_test(_production_layout())


def verify_archived_source_closure() -> ArchiveReceipt:
    """Verify only the archived closure and fixed manifest authority."""

    return _verify_archived_source_closure_for_test(_production_layout())
