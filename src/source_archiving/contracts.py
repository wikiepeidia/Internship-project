"""Value contracts for deterministic source-closure archives."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from typing import Any


EXPECTED_SCHEMA_VERSION = "phase41-execution-source-manifest-v1"
EXPECTED_TREE_SHA256 = "c3bbc8c8adaf7579fd2eb9c59a0081613be4b2cae05dfdb64472938c7e6d0434"
EXPECTED_LAUNCHER_SHA256 = "c5f15a32b2c8d8ee196e3ec484707c27c4c05e5389d958626e775e44f52d49e9"
EXPECTED_MANIFEST_SHA256 = "41a3a7e166dd5077b3b2c689868b862bd5665137e1824094eb5ff1cdce2b0c61"
EXPECTED_RECEIPT_SHA256 = "ca4ca1bf019b567d5bfa2380658a11245d76543b323ce5e2fcf6cfe3f525213a"
PROVENANCE_LABEL = "post_evaluation_archival_mirror_not_refactored_metric_producer"
RECEIPT_SCHEMA_VERSION = "phase411-source-closure-archival-receipt-v1"
MANIFEST_ARCHIVE_NAME = "execution-source-manifest.json"
RECEIPT_ARCHIVE_NAME = "archival-receipt.json"
TREE_ARCHIVE_NAME = "tree"
LAUNCHER_RELATIVE_PATH = "scripts/phase41_one_shot_launcher.ps1"
SOURCE_MODEL_CLI = "src/model_adaptation/cli.py"
SOURCE_PHASE41_EVALUATION = "src/model_adaptation/phase41_evaluation.py"
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
    SOURCE_MODEL_CLI,
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
    SOURCE_PHASE41_EVALUATION,
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
_WORKTREE_MISMATCHES = (SOURCE_MODEL_CLI, SOURCE_PHASE41_EVALUATION)


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
    expected_receipt_sha256: str | None = None


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
            {
                "bytes": size,
                "path": relative,
                "sha256": _require_sha256(
                    item.get("sha256"), where=f"manifest file {index} SHA-256"
                ),
            }
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
        launcher_path != LAUNCHER_RELATIVE_PATH
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
