"""Archive and verify an immutable source closure for reproducible evidence."""

from __future__ import annotations

import argparse
from contextlib import ExitStack
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

import src.source_archiving as source_archiving


# Compatibility aliases intentionally expose the former module surface while
# raw archive identities remain owned by the domain package.
ArchiveError = source_archiving.ArchiveError
ArchiveReceipt = source_archiving.ArchiveReceipt
EXPECTED_SCHEMA_VERSION = source_archiving.EXPECTED_SCHEMA_VERSION
EXPECTED_TREE_SHA256 = source_archiving.EXPECTED_TREE_SHA256
EXPECTED_LAUNCHER_SHA256 = source_archiving.EXPECTED_LAUNCHER_SHA256
EXPECTED_MANIFEST_SHA256 = source_archiving.EXPECTED_MANIFEST_SHA256
PROVENANCE_LABEL = source_archiving.PROVENANCE_LABEL
RECEIPT_SCHEMA_VERSION = source_archiving.RECEIPT_SCHEMA_VERSION
MANIFEST_ARCHIVE_NAME = source_archiving.MANIFEST_ARCHIVE_NAME
RECEIPT_ARCHIVE_NAME = source_archiving.RECEIPT_ARCHIVE_NAME
TREE_ARCHIVE_NAME = source_archiving.TREE_ARCHIVE_NAME
LAUNCHER_RELATIVE_PATH = source_archiving.LAUNCHER_RELATIVE_PATH
SOURCE_MODEL_CLI = source_archiving.SOURCE_MODEL_CLI
SOURCE_PHASE41_EVALUATION = source_archiving.SOURCE_PHASE41_EVALUATION
_WINDOWS_REPARSE_POINT = source_archiving._WINDOWS_REPARSE_POINT
_SHA256_RE = source_archiving._SHA256_RE
_MANIFEST_KEYS = source_archiving._MANIFEST_KEYS
_SOURCE_PATHS = source_archiving._SOURCE_PATHS
_WORKTREE_MISMATCHES = source_archiving._WORKTREE_MISMATCHES
_REPO_ROOT = source_archiving._REPO_ROOT
PRODUCTION_EVIDENCE_ROOT = source_archiving.PRODUCTION_EVIDENCE_ROOT
PRODUCTION_SOURCE_ROOT = source_archiving.PRODUCTION_SOURCE_ROOT
PRODUCTION_LAUNCHER_PATH = source_archiving.PRODUCTION_LAUNCHER_PATH
PRODUCTION_MANIFEST_PATH = source_archiving.PRODUCTION_MANIFEST_PATH
PRODUCTION_DESTINATION = source_archiving.PRODUCTION_DESTINATION
_ArchiveLayout = source_archiving._ArchiveLayout
_CapturedClosure = source_archiving._CapturedClosure
_PublicationBinding = source_archiving._PublicationBinding
_canonical_json = source_archiving._canonical_json
_sha256 = source_archiving._sha256
_strict_json = source_archiving._strict_json
_require_sha256 = source_archiving._require_sha256
_bounded_relative = source_archiving._bounded_relative
_manifest_records = source_archiving._manifest_records
_absolute = source_archiving._absolute
_redirecting = source_archiving._redirecting
_validate_ancestry = source_archiving._validate_ancestry
_validate_output_destination = source_archiving._validate_output_destination
_paths_overlap = source_archiving._paths_overlap
_capture_file = source_archiving._capture_file
_worktree_mismatches = source_archiving._worktree_mismatches
_capture_closure = source_archiving._capture_closure
_receipt_without_hash = source_archiving._receipt_without_hash
_verify_payloads = source_archiving._verify_payloads
_scan_exact_tree = source_archiving._scan_exact_tree
_verify_archive_root_members = source_archiving._verify_archive_root_members
_production_layout = source_archiving._production_layout

# These two names are deliberate monkeypatch seams. Wrappers below resolve
# their current values at call time rather than capturing function objects.
_publication_test_hook = source_archiving._publication_test_hook
_write_exclusive = source_archiving._write_exclusive


def _receipt_from_raw(raw: bytes) -> ArchiveReceipt:
    return source_archiving._receipt_from_raw(raw, clock=datetime)


def _publish(layout: _ArchiveLayout, captured: _CapturedClosure) -> ArchiveReceipt:
    return source_archiving._publish(
        layout,
        captured,
        write_exclusive=_write_exclusive,
        publication_test_hook=_publication_test_hook,
        clock=datetime,
        token_hex=secrets.token_hex,
    )


def _archive_bound_source_closure_for_test(layout: _ArchiveLayout) -> ArchiveReceipt:
    return source_archiving._archive_bound_source_closure_for_test(
        layout,
        write_exclusive=_write_exclusive,
        publication_test_hook=_publication_test_hook,
        clock=datetime,
        token_hex=secrets.token_hex,
    )


def _verify_archived_source_closure_for_test(layout: _ArchiveLayout) -> ArchiveReceipt:
    return source_archiving._verify_archived_source_closure_for_test(
        layout,
        clock=datetime,
    )


def archive_bound_source_closure() -> ArchiveReceipt:
    """Capture the code-fixed production closure into its fixed archive once."""

    return _archive_bound_source_closure_for_test(_production_layout())


def verify_archived_source_closure() -> ArchiveReceipt:
    """Verify only the archived closure and fixed manifest authority."""

    return _verify_archived_source_closure_for_test(_production_layout())


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


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=("archive", "verify"),
        help="archive a source closure or verify an existing archive",
    )
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
