"""Strict external preflight authority for the Phase 40 comparison launch.

The PowerShell launcher mirrors this module without importing Python before the
preflight receipt exists.  This module is the canonical schema/verifier used by
the in-process comparison boundary and by synthetic parity tests.
"""

from __future__ import annotations

import base64
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import shutil
import stat
import sys
from typing import Any


SCHEMA_VERSION = "phase40-comparison-launch-receipt-v3"
CLAIM_SCHEMA_VERSION = "phase40-comparison-launch-capability-claim-v1"
CAPABILITY_TTL = timedelta(seconds=60)
CAPABILITY_NONCE_BYTES = 32
CAPABILITY_NONCE_ENV = "PHASE40_COMPARISON_LAUNCH_NONCE"
CAPABILITY_LAUNCHER_PID_ENV = "PHASE40_COMPARISON_LAUNCHER_PID"
CAPABILITY_PENDING_SHA256_ENV = "PHASE40_COMPARISON_PENDING_RECEIPT_SHA256"
FINALIZER_SOURCE_TREE_DOMAIN = b"phase40-comparison-finalizer-source-v1\0"
FIXED_FINAL_AUTHORITY_RELATIVE_PATH = PurePosixPath(
    "data/models/phase40/final-comparison-authority.json"
)
FIXED_RUN_REQUEST_RELATIVE_PATH = PurePosixPath(
    "data/models/phase40/full-run-request.json"
)
FIXED_SCOPE_AMENDMENT_RELATIVE_PATH = PurePosixPath(
    "data/models/phase40/two-full-model-scope-amendment.json"
)
FIXED_PHOBERT_CAPSULE_ROOT_RELATIVE_PATH = PurePosixPath(
    "data/models/phase40/request-authority-roots/phobert-v12"
)
FIXED_PHOBERT_REQUEST_RELATIVE_PATH = (
    FIXED_PHOBERT_CAPSULE_ROOT_RELATIVE_PATH
    / "data/models/phase40/full-run-request.json"
)
FIXED_PHOBERT_CAPSULE_ASSET_RELATIVE_PATHS = (
    FIXED_PHOBERT_CAPSULE_ROOT_RELATIVE_PATH
    / "data/models/phase40/source/phase40-source.zip",
    FIXED_PHOBERT_CAPSULE_ROOT_RELATIVE_PATH
    / "data/models/phase40/source/phase40-source-manifest.json",
    FIXED_PHOBERT_CAPSULE_ROOT_RELATIVE_PATH
    / "data/models/phase40/input/phase40-train-validation.zip",
)
FIXED_RECEIPT_RELATIVE_PATH = PurePosixPath(
    "data/models/phase40/comparison-launch-receipt.json"
)
FIXED_CLAIM_RELATIVE_PATH = PurePosixPath(
    "data/models/phase40/comparison-launch-capability.claim"
)
FIXED_LAUNCHER_RELATIVE_PATH = PurePosixPath(
    "scripts/phase40_comparison_launcher.ps1"
)

# Duplicated deliberately from the final-authority producer.  The external
# launcher must reject a self-consistent authority that expands its read set
# before it opens even the first declared source file.  The producer and this
# consumer are refreshed atomically whenever the finalizer import closure moves.
FINALIZER_SOURCE_ALLOWLIST = (
    "pyproject.toml",
    "scripts/phase40_comparison_launcher.ps1",
    "src/__init__.py",
    "src/config/__init__.py",
    "src/config/settings.py",
    "src/data_pipeline/__init__.py",
    "src/data_pipeline/schemas.py",
    "src/model_adaptation/__init__.py",
    "src/model_adaptation/catalog.py",
    "src/model_adaptation/data.py",
    "src/model_adaptation/phase40_callbacks.py",
    "src/model_adaptation/phase40_comparison_launch.py",
    "src/model_adaptation/phase40_contract.py",
    "src/model_adaptation/phase40_evidence.py",
    "src/model_adaptation/phase40_final_authority.py",
    "src/model_adaptation/phase40_finalize.py",
    "src/model_adaptation/phase40_gguf.py",
    "src/model_adaptation/phase40_graphs.py",
    "src/model_adaptation/phase40_handoff.py",
    "src/model_adaptation/phase40_metrics.py",
    "src/model_adaptation/phase40_modes.py",
    "src/model_adaptation/phase40_phobert_release.py",
    "src/model_adaptation/phase40_production_authorities.py",
    "src/model_adaptation/phase40_release_authorities.py",
    "src/model_adaptation/phase40_runtime_materialize.py",
    "src/model_adaptation/phobert_training.py",
    "src/model_adaptation/pilot.py",
    "src/model_adaptation/prompts.py",
    "src/model_adaptation/registry.py",
    "src/model_adaptation/schemas.py",
    "src/model_adaptation/training.py",
    "src/runtime/__init__.py",
    "src/runtime/contracts.py",
)

ALLOWED_LAUNCHER_HOST_SHA256 = (
    "057a2754877cd356159ea891883179f8620ffdc89d3c70d2c4d1f3ba3f6c49b0"
)
ALLOWED_LAUNCHER_HOST_VERSION = "7.6.1"
ALLOWED_PYTHON_SHA256 = (
    "dc7ecf75280678175b4f931ce05f1ef9c10d48984399ca7de6beee69d71bcb1b"
)
ALLOWED_PYTHON_VERSION = "3.13.13"

FIXED_FINALIZER_COMMAND = (
    "python",
    "-s",
    "-B",
    "-m",
    "src.model_adaptation.phase40_finalize",
    "--repo-root",
    ".",
    "--output-root",
    "data/models/phase40",
    "--bundle-root",
    (
        "phase40-qwen-qlora-full-seed42-v1="
        "data/models/phase40/full/qwen-qlora"
    ),
    "--bundle-root",
    (
        "phase40-phobert-full-seed42-v12="
        "data/models/phase40/full/phobert"
    ),
    "--gpu-identity",
    (
        "phase40-qwen-qlora-full-seed42-v1="
        "NVIDIA GeForce RTX 5050 Laptop GPU"
    ),
    "--gpu-identity",
    (
        "phase40-phobert-full-seed42-v12="
        "NVIDIA GeForce RTX 5050 Laptop GPU"
    ),
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_SAFE_FACT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_ABSOLUTE_PATH_RE = re.compile(
    r"(?i)(?:^[A-Z]:[\\/]|^\\\\|^/(?:home|users)/|[A-Z]:[\\/]Users[\\/])"
)
_SECRET_RE = re.compile(
    r"(?i)(?:api[_-]?key|authorization|bearer|credential|password|secret)"
)
_REDIRECTING_REPARSE_TAGS = frozenset(
    {
        getattr(stat, "IO_REPARSE_TAG_SYMLINK", 0xA000000C),
        getattr(stat, "IO_REPARSE_TAG_MOUNT_POINT", 0xA0000003),
    }
)

_REQUEST_KEYS = {
    "schema_version",
    "runs",
    "source_bundle",
    "input_bundle",
    "package_candidates",
    "expected_bundle_files",
    "control_template_by_run",
    "control_template_digest_by_run",
    "no_held_out_boundary",
    "git_commit",
}
_FINAL_AUTHORITY_KEYS = {
    "schema_version",
    "superseded_scope_amendment",
    "request_authorities",
    "selected_runs",
    "quality_model_run_ids",
    "review_model_run_ids",
    "shared_input_authority",
    "waived_full_run_id",
    "waiver_action",
    "lora_probe_authority",
    "comparison_finalizer_authority",
    "recovery_policy",
    "execution_policy",
    "no_held_out_boundary",
}
_HISTORICAL_AMENDMENT_KEYS = {
    "schema_version",
    "original_run_request_path",
    "original_run_request_sha256",
    "active_full_run_ids",
    "active_returned_roots",
    "waived_full_run_id",
    "waived_returned_root",
    "full_lora_disposition",
    "waiver_action",
    "waiver_basis",
    "lora_probe_authority",
    "comparison_finalizer_authority",
    "quality_model_run_ids",
    "review_model_run_ids",
    "execution_policy",
    "colab_contingency_policy",
    "no_held_out_boundary",
}
_REQUEST_AUTHORITY_KEYS = {
    "authority_id",
    "root_policy",
    "request_sha256",
}
_SELECTED_RUN_KEYS = {
    "run_id",
    "request_authority_id",
    "requested_run_id",
    "returned_root",
}
_SUPERSEDED_AMENDMENT_KEYS = {"relative_path", "sha256", "schema_version"}
_FINALIZER_AUTHORITY_KEYS = {
    "schema_version",
    "runtime_origin",
    "files",
    "source_tree_sha256",
}
_INVENTORY_ENTRY_KEYS = {"path", "bytes", "sha256"}
_MAX_PORTABLE_FILE_BYTES = (1 << 63) - 1
_RECEIPT_KEYS = {
    "schema_version",
    "status",
    "final_comparison_authority",
    "request_authorities",
    "superseded_scope_amendment",
    "finalizer_authority",
    "launcher",
    "launcher_host",
    "python",
    "finalizer_command",
    "preflight_started_at_utc",
    "preflight_completed_at_utc",
    "receipt_created_at_utc",
    "prelaunch_state",
    "launch_capability",
    "receipt_sha256",
}
_FINAL_AUTHORITY_RECEIPT_KEYS = {"relative_path", "sha256"}
_REQUEST_AUTHORITY_RECEIPT_KEYS = {
    "authority_id",
    "root_policy",
    "request",
    "assets",
}
_REQUEST_RECEIPT_KEYS = {"relative_path", "sha256"}
_ASSET_RECEIPT_KEYS = {"relative_path", "bytes", "sha256"}
_AMENDMENT_RECEIPT_KEYS = {"relative_path", "sha256", "schema_version"}
_LAUNCHER_RECEIPT_KEYS = {"relative_path", "bytes", "sha256"}
_EXECUTABLE_RECEIPT_KEYS = {
    "path_policy",
    "portable_path",
    "path_sha256",
    "bytes",
    "sha256",
    "version",
}
_PRELAUNCH_STATE_KEYS = {
    "python_launched",
    "model_bundle_opened",
    "reserved_split_access_attempted",
}
_CAPABILITY_KEYS = {
    "state",
    "nonce_sha256",
    "launcher_process_id",
    "child_process_id",
    "issued_at_utc",
    "expires_at_utc",
    "consumed_at_utc",
    "pending_receipt_sha256",
    "claim_relative_path",
}
_CLAIM_KEYS = {
    "schema_version",
    "state",
    "nonce_sha256",
    "launcher_process_id",
    "child_process_id",
    "pending_receipt_sha256",
    "claimed_at_utc",
    "claim_sha256",
}


@dataclass(frozen=True, slots=True)
class ExecutableAuthority:
    """Out-of-payload authority used to verify one executable identity."""

    path: Path
    path_policy: str
    portable_path: str
    expected_sha256: str
    version: str


def _absolute(path: Path) -> Path:
    return Path(os.path.abspath(os.path.normpath(os.fspath(path))))


def _component_chain(path: Path) -> tuple[Path, ...]:
    components: list[Path] = []
    current = _absolute(path)
    while True:
        components.append(current)
        if current.parent == current:
            break
        current = current.parent
    return tuple(reversed(components))


def _reject_reparse_components(path: Path, *, allow_missing_leaf: bool = False) -> None:
    components = _component_chain(path)
    for index, component in enumerate(components):
        if not component.exists():
            if allow_missing_leaf and index == len(components) - 1:
                return
            raise FileNotFoundError(component)
        metadata = os.lstat(component)
        tag = getattr(metadata, "st_reparse_tag", 0)
        if stat.S_ISLNK(metadata.st_mode) or tag in _REDIRECTING_REPARSE_TAGS:
            raise ValueError(f"authority path contains a reparse point: {component}")


def _reject_lexical_traversal(path: Path, *, where: str) -> None:
    text = os.fspath(path)
    if not isinstance(text, str) or not text or "\x00" in text:
        raise ValueError(f"{where} must be a non-empty path")
    if ".." in PurePosixPath(text.replace("\\", "/")).parts:
        raise ValueError(f"{where} must not contain path traversal")


def _verified_repo_root(repo_root: Path) -> Path:
    requested = Path(repo_root)
    _reject_lexical_traversal(requested, where="repository root")
    if not requested.is_absolute():
        raise ValueError("repository root must be absolute")
    root = _absolute(requested)
    _reject_reparse_components(root)
    if not root.is_dir() or root.is_symlink():
        raise ValueError("repository root must be an existing non-reparse directory")
    return root


def _contained_path(root: Path, relative: PurePosixPath) -> Path:
    candidate = _absolute(root / relative)
    if candidate != root and root not in candidate.parents:
        raise ValueError("fixed authority path escaped the repository root")
    return candidate


def _regular_file(path: Path, *, where: str) -> Path:
    candidate = _absolute(path)
    _reject_reparse_components(candidate)
    if not candidate.is_file() or candidate.is_symlink():
        raise ValueError(f"{where} must be a regular non-reparse file")
    return candidate


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _canonical_json_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _decode_json_object(payload: bytes, *, where: str) -> dict[str, Any]:
    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key in {where}: {key}")
            result[key] = value
        return result

    def reject_constant(value: str) -> None:
        raise ValueError(f"non-finite JSON number in {where}: {value}")

    try:
        decoded = payload.decode("utf-8", errors="strict")
        value = json.loads(
            decoded,
            object_pairs_hook=reject_duplicates,
            parse_constant=reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"{where} must be strict UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise RuntimeError(f"{where} must be one JSON object")
    return value


def _reject_supplementary_json_property_names(value: object, *, where: str) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if any(ord(character) > 0xFFFF for character in key):
                raise ValueError(
                    f"{where} contains a supplementary Unicode property name"
                )
            _reject_supplementary_json_property_names(
                child,
                where=f"{where}.{key}",
            )
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_supplementary_json_property_names(
                child,
                where=f"{where}[{index}]",
            )


def _load_canonical_json(path: Path, *, where: str) -> tuple[bytes, dict[str, Any]]:
    source = _regular_file(path, where=where)
    raw = source.read_bytes()
    value = _decode_json_object(raw, where=where)
    _reject_supplementary_json_property_names(value, where=where)
    if raw != _canonical_json_bytes(value):
        raise RuntimeError(f"{where} must be canonical JSON")
    return raw, value


def _require_exact_keys(value: Mapping[str, Any], expected: set[str], *, where: str) -> None:
    if set(value) != expected:
        raise RuntimeError(
            f"{where} keys mismatch; missing={sorted(expected - set(value))}, "
            f"extra={sorted(set(value) - expected)}"
        )


def _require_sha256(value: object, *, where: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise ValueError(f"{where} must be a lowercase SHA-256")
    return value


def _safe_relative_path(value: object, *, where: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise ValueError(f"{where} must be a safe repository-relative POSIX path")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or path.as_posix() != value
        or any(part in {"", ".", ".."} for part in path.parts)
        or PureWindowsPath(value).is_absolute()
        or any(":" in part or any(ord(character) < 32 for character in part) for part in path.parts)
    ):
        raise ValueError(f"{where} must be a safe repository-relative POSIX path")
    return value


def _safe_finalizer_source_path(value: object, *, where: str) -> str:
    relative = _safe_relative_path(value, where=where)
    parts = PurePosixPath(relative).parts
    if relative in {
        "pyproject.toml",
        FIXED_LAUNCHER_RELATIVE_PATH.as_posix(),
    }:
        return relative
    if len(parts) < 2 or parts[0] != "src" or not parts[-1].endswith(".py"):
        raise ValueError(
            f"{where} must stay inside the allowed Python source namespace"
        )
    return relative


def _safe_fact(value: object, *, where: str) -> str:
    if not isinstance(value, str) or not _SAFE_FACT_RE.fullmatch(value):
        raise ValueError(f"{where} must be a short portable fact")
    return value


def _parse_canonical_utc(value: object, *, where: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise RuntimeError(f"{where} must be a canonical UTC timestamp")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise RuntimeError(f"{where} must be a canonical UTC timestamp") from exc
    canonical = parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if canonical != value:
        raise RuntimeError(f"{where} must be a canonical UTC timestamp")
    return parsed


def _reject_payload_leakage(value: object, *, where: str) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if _SECRET_RE.search(str(key)):
                raise ValueError(f"{where} contains a secret-like field")
            _reject_payload_leakage(child, where=f"{where}.{key}")
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            _reject_payload_leakage(child, where=f"{where}[{index}]")
        return
    if isinstance(value, str) and (
        _ABSOLUTE_PATH_RE.search(value)
        or PureWindowsPath(value).is_absolute()
        or PurePosixPath(value).is_absolute()
    ):
        raise ValueError(f"{where} leaks an absolute filesystem path")


def _normalized_path_sha256(path: Path) -> str:
    normalized = os.path.normcase(os.fspath(_absolute(path))).replace("\\", "/")
    return _sha256(normalized.encode("utf-8"))


def _executable_payload(authority: ExecutableAuthority, *, where: str) -> dict[str, Any]:
    if not isinstance(authority, ExecutableAuthority):
        raise TypeError(f"{where} authority must be ExecutableAuthority")
    path = Path(authority.path)
    _reject_lexical_traversal(path, where=f"{where} executable path")
    if not path.is_absolute():
        raise ValueError(f"{where} executable path must be absolute")
    executable = _regular_file(path, where=f"{where} executable")
    portable_path = _safe_relative_path(
        authority.portable_path,
        where=f"{where} portable path",
    )
    expected_sha256 = _require_sha256(
        authority.expected_sha256,
        where=f"{where} expected SHA-256",
    )
    actual = executable.read_bytes()
    if _sha256(actual) != expected_sha256:
        raise RuntimeError(f"{where} executable differs from its allowed authority")
    return {
        "path_policy": _safe_fact(authority.path_policy, where=f"{where} path policy"),
        "portable_path": portable_path,
        "path_sha256": _normalized_path_sha256(executable),
        "bytes": len(actual),
        "sha256": expected_sha256,
        "version": _safe_fact(authority.version, where=f"{where} version"),
    }


def default_launcher_host_authority() -> ExecutableAuthority:
    if os.name != "nt":
        raise RuntimeError("the canonical comparison launcher host is Windows-only")
    return ExecutableAuthority(
        path=Path(r"C:\Program Files\PowerShell\7\pwsh.exe"),
        path_policy="windows_known_folder_program_files",
        portable_path="PowerShell/7/pwsh.exe",
        expected_sha256=ALLOWED_LAUNCHER_HOST_SHA256,
        version=ALLOWED_LAUNCHER_HOST_VERSION,
    )


def default_python_authority() -> ExecutableAuthority:
    resolved = shutil.which("python")
    if resolved is None:
        raise RuntimeError("the canonical Phase 40 Python executable is unavailable")
    return ExecutableAuthority(
        path=Path(resolved),
        path_policy="path_resolution_exact_hash",
        portable_path="python.exe",
        expected_sha256=ALLOWED_PYTHON_SHA256,
        version=ALLOWED_PYTHON_VERSION,
    )


def _validate_request(
    request: Mapping[str, Any],
    *,
    expected_run_id: str,
    expected_run_ids: tuple[str, str, str],
    where: str,
) -> None:
    _require_exact_keys(request, _REQUEST_KEYS, where="Phase 40 run request")
    if request.get("schema_version") != "phase40-full-run-request-v1":
        raise RuntimeError(f"{where} schema drifted")
    if request.get("no_held_out_boundary") is not True:
        raise RuntimeError(f"{where} does not preserve the held-out boundary")
    runs = request.get("runs")
    if (
        not isinstance(runs, list)
        or len(runs) != len(expected_run_ids)
        or any(not isinstance(run, Mapping) for run in runs)
        or tuple(run.get("run_id") for run in runs) != expected_run_ids
    ):
        raise RuntimeError(f"{where} run IDs/order drifted")
    templates = request.get("control_template_by_run")
    digests = request.get("control_template_digest_by_run")
    if (
        not isinstance(templates, Mapping)
        or expected_run_id not in templates
        or not isinstance(digests, Mapping)
        or expected_run_id not in digests
    ):
        raise RuntimeError(f"{where} lacks the selected run control authority")


def _validate_superseded_amendment(
    amendment: Mapping[str, Any],
    *,
    expected: Mapping[str, Any],
    amendment_sha256: str,
    original_request_sha256: str,
) -> None:
    _require_exact_keys(
        amendment,
        _HISTORICAL_AMENDMENT_KEYS,
        where="historical Phase 40 scope amendment",
    )
    _require_exact_keys(
        expected,
        _SUPERSEDED_AMENDMENT_KEYS,
        where="superseded scope-amendment authority",
    )
    if (
        expected.get("relative_path")
        != FIXED_SCOPE_AMENDMENT_RELATIVE_PATH.as_posix()
        or expected.get("schema_version")
        != "phase40-two-full-model-scope-amendment-v1"
        or _require_sha256(
            expected.get("sha256"),
            where="superseded scope-amendment SHA-256",
        )
        != amendment_sha256
        or amendment.get("schema_version")
        != "phase40-two-full-model-scope-amendment-v1"
        or amendment.get("original_run_request_path")
        != FIXED_RUN_REQUEST_RELATIVE_PATH.as_posix()
        or amendment.get("original_run_request_sha256")
        != original_request_sha256
        or amendment.get("active_full_run_ids")
        != [
            "phase40-qwen-qlora-full-seed42-v1",
            "phase40-phobert-full-seed42-v1",
        ]
        or amendment.get("quality_model_run_ids")
        != [
            "phase40-qwen-qlora-full-seed42-v1",
            "phase40-phobert-full-seed42-v1",
        ]
        or amendment.get("review_model_run_ids")
        != [
            "phase40-qwen-qlora-full-seed42-v1",
            "phase40-phobert-full-seed42-v1",
        ]
        or amendment.get("active_returned_roots")
        != [
            "data/models/phase40/full/qwen-qlora",
            "data/models/phase40/full/phobert",
        ]
        or amendment.get("waived_full_run_id")
        != "phase40-qwen-lora-full-seed42-v1"
        or amendment.get("waived_returned_root")
        != "data/models/phase40/full/qwen-lora"
        or amendment.get("full_lora_disposition") != "cancelled_before_start"
        or amendment.get("waiver_action") != "withdrawn"
        or amendment.get("waiver_basis")
        != "bounded_local_probe_established_resource_pressure_and_deadline_mismatch"
        or amendment.get("execution_policy") != "local_primary"
        or amendment.get("colab_contingency_policy")
        != "validation_only_before_held_out_open_if_local_quality_unacceptable"
        or amendment.get("no_held_out_boundary") is not True
    ):
        raise RuntimeError("superseded scope-amendment authority drifted")


def _verified_finalizer_authority(
    root: Path,
    authority: Mapping[str, Any],
) -> dict[str, Any]:
    _require_exact_keys(
        authority,
        _FINALIZER_AUTHORITY_KEYS,
        where="comparison-finalizer authority",
    )
    if (
        authority.get("schema_version")
        != "phase40-comparison-finalizer-authority-v1"
        or authority.get("runtime_origin")
        != "local_hash_pinned_source_not_training_runtime_v3"
    ):
        raise RuntimeError("comparison-finalizer authority schema or origin drifted")
    raw_files = authority.get("files")
    if not isinstance(raw_files, list) or not raw_files:
        raise RuntimeError("comparison-finalizer authority must contain source files")
    declared: list[dict[str, Any]] = []
    for index, raw_entry in enumerate(raw_files):
        if not isinstance(raw_entry, Mapping):
            raise RuntimeError(f"comparison source entry {index} must be an object")
        _require_exact_keys(
            raw_entry,
            _INVENTORY_ENTRY_KEYS,
            where=f"comparison source entry {index}",
        )
        relative = _safe_finalizer_source_path(
            raw_entry.get("path"),
            where=f"comparison source entry {index} path",
        )
        expected_bytes = raw_entry.get("bytes")
        if (
            isinstance(expected_bytes, bool)
            or not isinstance(expected_bytes, int)
            or expected_bytes < 0
            or expected_bytes > _MAX_PORTABLE_FILE_BYTES
        ):
            raise ValueError(f"comparison source entry {relative} has invalid byte count")
        expected_sha256 = _require_sha256(
            raw_entry.get("sha256"),
            where=f"comparison source entry {relative} SHA-256",
        )
        declared.append(
            {"path": relative, "bytes": expected_bytes, "sha256": expected_sha256}
        )

    declared_paths = tuple(entry["path"] for entry in declared)
    if declared_paths != FINALIZER_SOURCE_ALLOWLIST:
        raise ValueError(
            "comparison source inventory must equal the code-fixed source allowlist"
        )
    if _canonical_json_bytes(raw_files) != _canonical_json_bytes(declared):
        raise RuntimeError("comparison source inventory has noncanonical token types")
    expected_tree = _sha256(
        FINALIZER_SOURCE_TREE_DOMAIN + _canonical_json_bytes(declared)
    )
    tree = _require_sha256(
        authority.get("source_tree_sha256"),
        where="comparison-finalizer source-tree SHA-256",
    )
    if expected_tree != tree:
        raise RuntimeError("comparison-finalizer source-tree hash mismatch")

    # The complete namespace, shape, and tree gate above deliberately precedes
    # every source-path stat/open/read.  A later hostile entry can never cause
    # earlier authority paths (or any reserved data namespace) to be touched.
    verified: list[dict[str, Any]] = []
    for entry in declared:
        relative = entry["path"]
        source = _regular_file(
            _contained_path(root, PurePosixPath(relative)),
            where=f"comparison source {relative}",
        )
        payload = source.read_bytes()
        if len(payload) != entry["bytes"] or _sha256(payload) != entry["sha256"]:
            raise RuntimeError(f"comparison source identity mismatch: {relative}")
        verified.append(
            {"path": relative, "bytes": len(payload), "sha256": entry["sha256"]}
        )
    if _canonical_json_bytes(verified) != _canonical_json_bytes(declared):
        raise RuntimeError("verified comparison source inventory changed after opening")
    return {
        "schema_version": "phase40-comparison-finalizer-authority-v1",
        "runtime_origin": "local_hash_pinned_source_not_training_runtime_v3",
        "files": verified,
        "source_tree_sha256": tree,
    }


def _verified_capsule_assets(
    root: Path,
    request: Mapping[str, Any],
) -> list[dict[str, Any]]:
    source = request.get("source_bundle")
    inputs = request.get("input_bundle")
    if not isinstance(source, Mapping) or not isinstance(inputs, Mapping):
        raise RuntimeError("PhoBERT recovery request asset authority is malformed")
    expected = (
        (
            "data/models/phase40/source/phase40-source.zip",
            source.get("archive_sha256"),
        ),
        (
            "data/models/phase40/source/phase40-source-manifest.json",
            source.get("inventory_sha256"),
        ),
        (
            "data/models/phase40/input/phase40-train-validation.zip",
            inputs.get("archive_sha256"),
        ),
    )
    declared_paths = (
        source.get("repository_relative_archive_path"),
        source.get("repository_relative_inventory_path"),
        inputs.get("repository_relative_path"),
    )
    if declared_paths != tuple(path for path, _ in expected):
        raise RuntimeError("PhoBERT recovery request names alternate capsule assets")

    verified: list[dict[str, Any]] = []
    for fixed_relative, (declared_relative, expected_sha256) in zip(
        FIXED_PHOBERT_CAPSULE_ASSET_RELATIVE_PATHS,
        expected,
        strict=True,
    ):
        if fixed_relative.as_posix() != (
            FIXED_PHOBERT_CAPSULE_ROOT_RELATIVE_PATH / declared_relative
        ).as_posix():
            raise AssertionError("fixed PhoBERT capsule asset path drifted")
        expected_hash = _require_sha256(
            expected_sha256,
            where=f"PhoBERT capsule asset {declared_relative} SHA-256",
        )
        asset = _regular_file(
            _contained_path(root, fixed_relative),
            where=f"fixed PhoBERT capsule asset {declared_relative}",
        )
        payload = asset.read_bytes()
        if _sha256(payload) != expected_hash:
            raise RuntimeError(
                f"PhoBERT capsule asset identity mismatch: {declared_relative}"
            )
        if declared_relative.endswith(".json"):
            _load_canonical_json(
                asset,
                where="PhoBERT capsule source inventory",
            )
        verified.append(
            {
                "relative_path": fixed_relative.as_posix(),
                "bytes": len(payload),
                "sha256": expected_hash,
            }
        )
    return verified


def _validate_final_authority(
    authority: Mapping[str, Any],
    *,
    qwen_request_sha256: str,
    phobert_request_sha256: str,
    amendment: Mapping[str, Any],
    amendment_sha256: str,
    qwen_request: Mapping[str, Any],
    phobert_request: Mapping[str, Any],
) -> Mapping[str, Any]:
    _require_exact_keys(
        authority,
        _FINAL_AUTHORITY_KEYS,
        where="Phase 40 final comparison authority",
    )
    if (
        authority.get("schema_version")
        != "phase40-final-comparison-authority-v1"
        or authority.get("recovery_policy")
        != "additive_per_run_request_authority_no_evidence_rewrite_v1"
        or authority.get("execution_policy") != "local_primary"
        or authority.get("no_held_out_boundary") is not True
        or authority.get("waived_full_run_id")
        != "phase40-qwen-lora-full-seed42-v1"
        or authority.get("waiver_action") != "withdrawn"
    ):
        raise RuntimeError("Phase 40 final comparison policy drifted")

    expected_request_authorities = [
        {
            "authority_id": "qwen-v1-origin",
            "root_policy": "repository_root",
            "request_sha256": qwen_request_sha256,
        },
        {
            "authority_id": "phobert-v12-recovery",
            "root_policy": "fixed_phobert_v12_capsule",
            "request_sha256": phobert_request_sha256,
        },
    ]
    raw_request_authorities = authority.get("request_authorities")
    if not isinstance(raw_request_authorities, list):
        raise RuntimeError("final comparison request authorities must be an array")
    for index, item in enumerate(raw_request_authorities):
        if not isinstance(item, Mapping):
            raise RuntimeError(f"request authority {index} must be an object")
        _require_exact_keys(
            item,
            _REQUEST_AUTHORITY_KEYS,
            where=f"request authority {index}",
        )
        _require_sha256(
            item.get("request_sha256"),
            where=f"request authority {index} SHA-256",
        )
    if raw_request_authorities != expected_request_authorities:
        raise RuntimeError("final comparison request authorities drifted")

    expected_runs = [
        {
            "run_id": "phase40-qwen-qlora-full-seed42-v1",
            "request_authority_id": "qwen-v1-origin",
            "requested_run_id": "phase40-qwen-qlora-full-seed42-v1",
            "returned_root": "data/models/phase40/full/qwen-qlora",
        },
        {
            "run_id": "phase40-phobert-full-seed42-v12",
            "request_authority_id": "phobert-v12-recovery",
            "requested_run_id": "phase40-phobert-full-seed42-v12",
            "returned_root": "data/models/phase40/full/phobert",
        },
    ]
    raw_runs = authority.get("selected_runs")
    if not isinstance(raw_runs, list):
        raise RuntimeError("final comparison selected runs must be an array")
    for index, item in enumerate(raw_runs):
        if not isinstance(item, Mapping):
            raise RuntimeError(f"selected run {index} must be an object")
        _require_exact_keys(item, _SELECTED_RUN_KEYS, where=f"selected run {index}")
    active_ids = [item["run_id"] for item in expected_runs]
    if (
        raw_runs != expected_runs
        or authority.get("quality_model_run_ids") != active_ids
        or authority.get("review_model_run_ids") != active_ids
    ):
        raise RuntimeError("final comparison selected model set drifted")

    superseded = authority.get("superseded_scope_amendment")
    if not isinstance(superseded, Mapping):
        raise RuntimeError("final comparison lacks superseded amendment authority")
    _validate_superseded_amendment(
        amendment,
        expected=superseded,
        amendment_sha256=amendment_sha256,
        original_request_sha256=qwen_request_sha256,
    )
    if authority.get("lora_probe_authority") != amendment.get("lora_probe_authority"):
        raise RuntimeError("final comparison LoRA-probe authority drifted")
    shared_input = authority.get("shared_input_authority")
    if (
        shared_input != qwen_request.get("input_bundle")
        or shared_input != phobert_request.get("input_bundle")
    ):
        raise RuntimeError("final comparison shared-input authority drifted")
    finalizer = authority.get("comparison_finalizer_authority")
    if not isinstance(finalizer, Mapping):
        raise RuntimeError("final comparison lacks finalizer source authority")
    return finalizer


def _authority_snapshot(root: Path) -> dict[str, Any]:
    final_path = _contained_path(root, FIXED_FINAL_AUTHORITY_RELATIVE_PATH)
    qwen_request_path = _contained_path(root, FIXED_RUN_REQUEST_RELATIVE_PATH)
    phobert_request_path = _contained_path(root, FIXED_PHOBERT_REQUEST_RELATIVE_PATH)
    amendment_path = _contained_path(root, FIXED_SCOPE_AMENDMENT_RELATIVE_PATH)
    final_bytes, authority = _load_canonical_json(
        final_path,
        where="canonical Phase 40 final comparison authority",
    )
    qwen_request_bytes, qwen_request = _load_canonical_json(
        qwen_request_path,
        where="canonical Phase 40 Qwen request",
    )
    phobert_request_bytes, phobert_request = _load_canonical_json(
        phobert_request_path,
        where="canonical Phase 40 PhoBERT recovery request",
    )
    amendment_bytes, amendment = _load_canonical_json(
        amendment_path,
        where="canonical superseded Phase 40 scope amendment",
    )
    _validate_request(
        qwen_request,
        expected_run_id="phase40-qwen-qlora-full-seed42-v1",
        expected_run_ids=(
            "phase40-qwen-lora-full-seed42-v1",
            "phase40-qwen-qlora-full-seed42-v1",
            "phase40-phobert-full-seed42-v1",
        ),
        where="Phase 40 Qwen request",
    )
    _validate_request(
        phobert_request,
        expected_run_id="phase40-phobert-full-seed42-v12",
        expected_run_ids=(
            "phase40-qwen-lora-full-seed42-v1",
            "phase40-qwen-qlora-full-seed42-v1",
            "phase40-phobert-full-seed42-v12",
        ),
        where="Phase 40 PhoBERT recovery request",
    )
    qwen_sha256 = _sha256(qwen_request_bytes)
    phobert_sha256 = _sha256(phobert_request_bytes)
    amendment_sha256 = _sha256(amendment_bytes)
    raw_finalizer = _validate_final_authority(
        authority,
        qwen_request_sha256=qwen_sha256,
        phobert_request_sha256=phobert_sha256,
        amendment=amendment,
        amendment_sha256=amendment_sha256,
        qwen_request=qwen_request,
        phobert_request=phobert_request,
    )
    finalizer = _verified_finalizer_authority(root, raw_finalizer)
    capsule_assets = _verified_capsule_assets(root, phobert_request)
    return {
        "final_comparison_authority": {
            "relative_path": FIXED_FINAL_AUTHORITY_RELATIVE_PATH.as_posix(),
            "sha256": _sha256(final_bytes),
        },
        "request_authorities": [
            {
                "authority_id": "qwen-v1-origin",
                "root_policy": "repository_root",
                "request": {
                    "relative_path": FIXED_RUN_REQUEST_RELATIVE_PATH.as_posix(),
                    "sha256": qwen_sha256,
                },
                "assets": [],
            },
            {
                "authority_id": "phobert-v12-recovery",
                "root_policy": "fixed_phobert_v12_capsule",
                "request": {
                    "relative_path": FIXED_PHOBERT_REQUEST_RELATIVE_PATH.as_posix(),
                    "sha256": phobert_sha256,
                },
                "assets": capsule_assets,
            },
        ],
        "superseded_scope_amendment": {
            "relative_path": FIXED_SCOPE_AMENDMENT_RELATIVE_PATH.as_posix(),
            "sha256": amendment_sha256,
            "schema_version": "phase40-two-full-model-scope-amendment-v1",
        },
        "finalizer_authority": finalizer,
    }


def _launcher_payload(root: Path) -> dict[str, Any]:
    path = _regular_file(
        _contained_path(root, FIXED_LAUNCHER_RELATIVE_PATH),
        where="canonical comparison launcher",
    )
    payload = path.read_bytes()
    return {
        "relative_path": FIXED_LAUNCHER_RELATIVE_PATH.as_posix(),
        "bytes": len(payload),
        "sha256": _sha256(payload),
    }


def _receipt_authority_core(
    *,
    root: Path,
    launcher_host_authority: ExecutableAuthority,
    python_authority: ExecutableAuthority,
    preflight_started_at_utc: str,
    preflight_completed_at_utc: str,
    receipt_created_at_utc: str,
) -> dict[str, Any]:
    started = _parse_canonical_utc(
        preflight_started_at_utc,
        where="preflight_started_at_utc",
    )
    completed = _parse_canonical_utc(
        preflight_completed_at_utc,
        where="preflight_completed_at_utc",
    )
    created = _parse_canonical_utc(
        receipt_created_at_utc,
        where="receipt_created_at_utc",
    )
    if completed < started or created < completed:
        raise RuntimeError("comparison-launch receipt chronology is invalid")
    snapshot = _authority_snapshot(root)
    return {
        "schema_version": SCHEMA_VERSION,
        **snapshot,
        "launcher": _launcher_payload(root),
        "launcher_host": _executable_payload(
            launcher_host_authority,
            where="launcher host",
        ),
        "python": _executable_payload(python_authority, where="Python"),
        "finalizer_command": list(FIXED_FINALIZER_COMMAND),
        "preflight_started_at_utc": preflight_started_at_utc,
        "preflight_completed_at_utc": preflight_completed_at_utc,
        "receipt_created_at_utc": receipt_created_at_utc,
    }


def _positive_process_id(value: object, *, where: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise RuntimeError(f"{where} must be a positive integer process ID")
    return value


def _validate_launch_capability(
    capability: Mapping[str, Any],
    *,
    status: object,
    receipt_created_at_utc: object,
) -> None:
    _require_exact_keys(
        capability,
        _CAPABILITY_KEYS,
        where="comparison-launch receipt launch capability",
    )
    nonce_sha256 = _require_sha256(
        capability.get("nonce_sha256"),
        where="comparison-launch capability nonce hash",
    )
    del nonce_sha256
    _positive_process_id(
        capability.get("launcher_process_id"),
        where="comparison-launch capability launcher",
    )
    if capability.get("claim_relative_path") != FIXED_CLAIM_RELATIVE_PATH.as_posix():
        raise RuntimeError("comparison-launch capability claim path drifted")
    issued = _parse_canonical_utc(
        capability.get("issued_at_utc"),
        where="comparison-launch capability issued_at_utc",
    )
    expires = _parse_canonical_utc(
        capability.get("expires_at_utc"),
        where="comparison-launch capability expires_at_utc",
    )
    created = _parse_canonical_utc(
        receipt_created_at_utc,
        where="receipt_created_at_utc",
    )
    if issued != created or expires <= issued or expires - issued > CAPABILITY_TTL:
        raise RuntimeError("comparison-launch capability lifetime is invalid")

    if status == "PENDING":
        if capability.get("state") != "pending":
            raise RuntimeError("PENDING receipt lacks a pending launch capability")
        if any(
            capability.get(field) is not None
            for field in (
                "child_process_id",
                "consumed_at_utc",
                "pending_receipt_sha256",
            )
        ):
            raise RuntimeError("PENDING receipt overclaims capability consumption")
        return
    if status != "PASS" or capability.get("state") != "consumed":
        raise RuntimeError("comparison-launch receipt status is unsupported")
    _positive_process_id(
        capability.get("child_process_id"),
        where="comparison-launch capability child",
    )
    consumed = _parse_canonical_utc(
        capability.get("consumed_at_utc"),
        where="comparison-launch capability consumed_at_utc",
    )
    if consumed < issued or consumed > expires:
        raise RuntimeError("comparison-launch capability consumption time is invalid")
    _require_sha256(
        capability.get("pending_receipt_sha256"),
        where="comparison-launch capability PENDING receipt hash",
    )


def _pending_receipt_payload(
    *,
    root: Path,
    launcher_host_authority: ExecutableAuthority,
    python_authority: ExecutableAuthority,
    preflight_started_at_utc: str,
    preflight_completed_at_utc: str,
    receipt_created_at_utc: str,
    nonce_sha256: str,
    launcher_process_id: int,
    expires_at_utc: str,
) -> dict[str, Any]:
    """Build PENDING bytes for parity tests; production writes them in PowerShell."""

    core = {
        **_receipt_authority_core(
            root=root,
            launcher_host_authority=launcher_host_authority,
            python_authority=python_authority,
            preflight_started_at_utc=preflight_started_at_utc,
            preflight_completed_at_utc=preflight_completed_at_utc,
            receipt_created_at_utc=receipt_created_at_utc,
        ),
        "status": "PENDING",
        "prelaunch_state": {
            "python_launched": False,
            "model_bundle_opened": False,
            "reserved_split_access_attempted": False,
        },
        "launch_capability": {
            "state": "pending",
            "nonce_sha256": _require_sha256(
                nonce_sha256,
                where="comparison-launch capability nonce hash",
            ),
            "launcher_process_id": _positive_process_id(
                launcher_process_id,
                where="comparison-launch capability launcher",
            ),
            "child_process_id": None,
            "issued_at_utc": receipt_created_at_utc,
            "expires_at_utc": expires_at_utc,
            "consumed_at_utc": None,
            "pending_receipt_sha256": None,
            "claim_relative_path": FIXED_CLAIM_RELATIVE_PATH.as_posix(),
        },
    }
    _reject_payload_leakage(core, where="comparison-launch receipt")
    payload = {
        **core,
        "receipt_sha256": _sha256(_canonical_json_bytes(core)),
    }
    _validate_receipt_shape(payload)
    return payload


def _validate_receipt_shape(payload: Mapping[str, Any]) -> None:
    _require_exact_keys(payload, _RECEIPT_KEYS, where="comparison-launch receipt")
    nested = (
        ("final_comparison_authority", _FINAL_AUTHORITY_RECEIPT_KEYS),
        ("superseded_scope_amendment", _AMENDMENT_RECEIPT_KEYS),
        ("finalizer_authority", _FINALIZER_AUTHORITY_KEYS),
        ("launcher", _LAUNCHER_RECEIPT_KEYS),
        ("launcher_host", _EXECUTABLE_RECEIPT_KEYS),
        ("python", _EXECUTABLE_RECEIPT_KEYS),
        ("prelaunch_state", _PRELAUNCH_STATE_KEYS),
        ("launch_capability", _CAPABILITY_KEYS),
    )
    for field, keys in nested:
        value = payload.get(field)
        if not isinstance(value, Mapping):
            raise RuntimeError(f"comparison-launch receipt {field} must be an object")
        _require_exact_keys(value, keys, where=f"comparison-launch receipt {field}")
    request_authorities = payload.get("request_authorities")
    if not isinstance(request_authorities, list) or len(request_authorities) != 2:
        raise RuntimeError(
            "comparison-launch receipt request authorities must be the exact pair"
        )
    for index, authority in enumerate(request_authorities):
        if not isinstance(authority, Mapping):
            raise RuntimeError(
                f"comparison-launch receipt request authority {index} must be an object"
            )
        _require_exact_keys(
            authority,
            _REQUEST_AUTHORITY_RECEIPT_KEYS,
            where=f"comparison-launch receipt request authority {index}",
        )
        request = authority.get("request")
        assets = authority.get("assets")
        if not isinstance(request, Mapping) or not isinstance(assets, list):
            raise RuntimeError(
                f"comparison-launch receipt request authority {index} is malformed"
            )
        _require_exact_keys(
            request,
            _REQUEST_RECEIPT_KEYS,
            where=f"comparison-launch receipt request {index}",
        )
        for asset_index, asset in enumerate(assets):
            if not isinstance(asset, Mapping):
                raise RuntimeError(
                    f"comparison-launch receipt asset {index}:{asset_index} must be an object"
                )
            _require_exact_keys(
                asset,
                _ASSET_RECEIPT_KEYS,
                where=f"comparison-launch receipt asset {index}:{asset_index}",
            )
    authority = payload["finalizer_authority"]
    files = authority.get("files")
    if not isinstance(files, list) or not files:
        raise RuntimeError("comparison-launch receipt finalizer files must be a non-empty list")
    for index, entry in enumerate(files):
        if not isinstance(entry, Mapping):
            raise RuntimeError(f"comparison-launch receipt source entry {index} must be an object")
        _require_exact_keys(
            entry,
            _INVENTORY_ENTRY_KEYS,
            where=f"comparison-launch receipt source entry {index}",
        )
    status = payload.get("status")
    _validate_launch_capability(
        payload["launch_capability"],
        status=status,
        receipt_created_at_utc=payload.get("receipt_created_at_utc"),
    )
    expected_prelaunch = {
        "python_launched": status == "PASS",
        "model_bundle_opened": False,
        "reserved_split_access_attempted": False,
    }
    if payload["prelaunch_state"] != expected_prelaunch:
        raise RuntimeError("comparison-launch receipt prelaunch state is invalid")


def _receipt_path(root: Path, *, must_exist: bool) -> Path:
    path = _contained_path(root, FIXED_RECEIPT_RELATIVE_PATH)
    if must_exist:
        return _regular_file(path, where="canonical comparison-launch receipt")
    parent = path.parent
    if parent.exists():
        _reject_reparse_components(parent)
    else:
        existing = parent
        while not existing.exists():
            existing = existing.parent
        _reject_reparse_components(existing)
    if path.exists():
        raise FileExistsError(f"refusing to overwrite comparison-launch receipt: {path}")
    return path


def _write_new_file(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def _claim_path(root: Path, *, must_exist: bool) -> Path:
    path = _contained_path(root, FIXED_CLAIM_RELATIVE_PATH)
    if must_exist:
        return _regular_file(path, where="comparison-launch capability claim")
    _reject_reparse_components(path, allow_missing_leaf=True)
    if path.exists():
        raise FileExistsError("comparison-launch capability was already claimed")
    return path


def _format_canonical_utc(value: datetime) -> str:
    utc = value.astimezone(timezone.utc)
    text = utc.isoformat(timespec="microseconds").replace("+00:00", "Z")
    return text.replace(".000000Z", "Z")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parent_process_id() -> int:
    return os.getppid()


def _current_process_id() -> int:
    return os.getpid()


def _current_working_directory() -> Path:
    return Path.cwd()


def _current_python_executable() -> Path:
    return Path(sys.executable)


def _python_invocation_flags_are_hardened() -> bool:
    return bool(sys.flags.no_user_site and sys.dont_write_bytecode)


def _parent_process_image_path(process_id: int) -> Path:
    if os.name != "nt":
        raise RuntimeError("comparison-launch parent identity is Windows-only")
    import ctypes
    from ctypes import wintypes

    process_query_limited_information = 0x1000
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    open_process = kernel32.OpenProcess
    open_process.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    open_process.restype = wintypes.HANDLE
    query_image = kernel32.QueryFullProcessImageNameW
    query_image.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.LPWSTR,
        ctypes.POINTER(wintypes.DWORD),
    ]
    query_image.restype = wintypes.BOOL
    close_handle = kernel32.CloseHandle
    close_handle.argtypes = [wintypes.HANDLE]
    close_handle.restype = wintypes.BOOL
    handle = open_process(process_query_limited_information, False, process_id)
    if not handle:
        raise RuntimeError("cannot open comparison-launch parent process")
    try:
        size = wintypes.DWORD(32768)
        buffer = ctypes.create_unicode_buffer(size.value)
        if not query_image(handle, 0, buffer, ctypes.byref(size)):
            raise RuntimeError("cannot resolve comparison-launch parent executable")
        return Path(buffer.value)
    finally:
        close_handle(handle)


def _same_absolute_path(left: Path, right: Path) -> bool:
    return os.path.normcase(os.fspath(_absolute(left))) == os.path.normcase(
        os.fspath(_absolute(right))
    )


def _take_capability_environment() -> tuple[str, str, str]:
    values = tuple(
        os.environ.pop(name, None)
        for name in (
            CAPABILITY_NONCE_ENV,
            CAPABILITY_LAUNCHER_PID_ENV,
            CAPABILITY_PENDING_SHA256_ENV,
        )
    )
    if any(not isinstance(value, str) or not value for value in values):
        raise RuntimeError("comparison finalizer requires a fresh launcher capability")
    return values  # type: ignore[return-value]


def _decode_capability_nonce(value: str) -> bytes:
    try:
        decoded = base64.b64decode(value, validate=True)
    except (ValueError, TypeError) as exc:
        raise RuntimeError("comparison-launch capability nonce is malformed") from exc
    if (
        len(decoded) != CAPABILITY_NONCE_BYTES
        or base64.b64encode(decoded).decode("ascii") != value
    ):
        raise RuntimeError("comparison-launch capability nonce has the wrong size")
    return decoded


def _claim_payload(
    *,
    capability: Mapping[str, Any],
    pending_receipt_sha256: str,
    child_process_id: int,
    claimed_at_utc: str,
) -> dict[str, Any]:
    core = {
        "schema_version": CLAIM_SCHEMA_VERSION,
        "state": "consumed",
        "nonce_sha256": capability["nonce_sha256"],
        "launcher_process_id": capability["launcher_process_id"],
        "child_process_id": child_process_id,
        "pending_receipt_sha256": pending_receipt_sha256,
        "claimed_at_utc": claimed_at_utc,
    }
    return {**core, "claim_sha256": _sha256(_canonical_json_bytes(core))}


def _atomic_replace_file(path: Path, payload: bytes) -> None:
    temporary = path.with_name(
        f".{path.name}.{_current_process_id()}.{_sha256(os.urandom(32))}.tmp"
    )
    _reject_reparse_components(temporary, allow_missing_leaf=True)
    try:
        _write_new_file(temporary, payload)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _load_receipt(root: Path) -> tuple[bytes, dict[str, Any]]:
    raw, payload = _load_canonical_json(
        _receipt_path(root, must_exist=True),
        where="comparison-launch receipt",
    )
    if raw != _canonical_json_bytes(payload):
        raise RuntimeError("comparison-launch receipt must be canonical JSON")
    _validate_receipt_shape(payload)
    self_hash = _require_sha256(
        payload.get("receipt_sha256"),
        where="comparison-launch receipt self-hash",
    )
    core = {key: value for key, value in payload.items() if key != "receipt_sha256"}
    if not hmac.compare_digest(_sha256(_canonical_json_bytes(core)), self_hash):
        raise RuntimeError("comparison-launch receipt self-hash mismatch")
    return raw, payload


def _verify_receipt_authority(
    *,
    root: Path,
    payload: Mapping[str, Any],
    launcher_host_authority: ExecutableAuthority,
    python_authority: ExecutableAuthority,
) -> None:
    expected = _receipt_authority_core(
        root=root,
        launcher_host_authority=launcher_host_authority,
        python_authority=python_authority,
        preflight_started_at_utc=payload["preflight_started_at_utc"],
        preflight_completed_at_utc=payload["preflight_completed_at_utc"],
        receipt_created_at_utc=payload["receipt_created_at_utc"],
    )
    for key, value in expected.items():
        if payload.get(key) != value:
            raise RuntimeError(
                "comparison-launch receipt is stale or differs from fixed authority"
            )
    if payload.get("finalizer_command") != list(FIXED_FINALIZER_COMMAND):
        raise RuntimeError("comparison-launch receipt finalizer command drifted")


def consume_phase40_comparison_launch_capability(
    *,
    repo_root: Path,
    argv: list[str],
) -> dict[str, Any]:
    """Consume the exact launcher's fresh capability before importing finalization."""

    nonce_text, launcher_pid_text, pending_sha256_text = (
        _take_capability_environment()
    )
    nonce = _decode_capability_nonce(nonce_text)
    pending_sha256 = _require_sha256(
        pending_sha256_text,
        where="launcher-provided PENDING receipt hash",
    )
    if not launcher_pid_text.isascii() or not launcher_pid_text.isdecimal():
        raise RuntimeError("launcher process ID environment value is malformed")
    launcher_process_id = _positive_process_id(
        int(launcher_pid_text),
        where="launcher process ID environment value",
    )
    if launcher_pid_text != str(launcher_process_id):
        raise RuntimeError("launcher process ID environment value is noncanonical")
    root = _verified_repo_root(repo_root)
    if not _same_absolute_path(_current_working_directory(), root):
        raise RuntimeError("comparison finalizer working directory drifted")
    if argv != list(FIXED_FINALIZER_COMMAND[5:]):
        raise RuntimeError("comparison finalizer argv differs from the fixed command")
    if not _python_invocation_flags_are_hardened():
        raise RuntimeError("comparison finalizer lacks the fixed -s -B Python flags")

    raw, pending = _load_receipt(root)
    if pending.get("status") != "PENDING":
        raise RuntimeError("comparison-launch capability is not pending")
    if not hmac.compare_digest(_sha256(raw), pending_sha256):
        raise RuntimeError("launcher-provided PENDING receipt hash mismatch")
    capability = pending["launch_capability"]
    if not hmac.compare_digest(_sha256(nonce), capability["nonce_sha256"]):
        raise RuntimeError("comparison-launch capability nonce mismatch")
    if capability["launcher_process_id"] != launcher_process_id:
        raise RuntimeError("comparison-launch capability launcher PID mismatch")
    if _parent_process_id() != launcher_process_id:
        raise RuntimeError("comparison finalizer was not spawned by the fixed launcher")
    now = _utc_now()
    issued = _parse_canonical_utc(
        capability["issued_at_utc"],
        where="comparison-launch capability issued_at_utc",
    )
    expires = _parse_canonical_utc(
        capability["expires_at_utc"],
        where="comparison-launch capability expires_at_utc",
    )
    if now < issued or now > expires:
        raise RuntimeError("comparison-launch capability is not currently fresh")

    launcher_host = default_launcher_host_authority()
    python_authority = default_python_authority()
    if not _same_absolute_path(
        _parent_process_image_path(launcher_process_id),
        launcher_host.path,
    ):
        raise RuntimeError("comparison-launch parent executable identity drifted")
    if not _same_absolute_path(_current_python_executable(), python_authority.path):
        raise RuntimeError("comparison finalizer Python executable identity drifted")
    _verify_receipt_authority(
        root=root,
        payload=pending,
        launcher_host_authority=launcher_host,
        python_authority=python_authority,
    )

    child_process_id = _positive_process_id(
        _current_process_id(),
        where="comparison finalizer child",
    )
    consumed_at_utc = _format_canonical_utc(now)
    claim = _claim_payload(
        capability=capability,
        pending_receipt_sha256=pending_sha256,
        child_process_id=child_process_id,
        claimed_at_utc=consumed_at_utc,
    )
    claim_path = _claim_path(root, must_exist=False)
    _write_new_file(claim_path, _canonical_json_bytes(claim))

    reread_raw, reread_pending = _load_receipt(root)
    if reread_raw != raw or reread_pending != pending:
        raise RuntimeError("PENDING comparison-launch receipt changed while claiming")
    pass_core = {
        key: value for key, value in pending.items() if key != "receipt_sha256"
    }
    pass_core["status"] = "PASS"
    pass_core["prelaunch_state"] = {
        "python_launched": True,
        "model_bundle_opened": False,
        "reserved_split_access_attempted": False,
    }
    pass_core["launch_capability"] = {
        **capability,
        "state": "consumed",
        "child_process_id": child_process_id,
        "consumed_at_utc": consumed_at_utc,
        "pending_receipt_sha256": pending_sha256,
    }
    passed = {
        **pass_core,
        "receipt_sha256": _sha256(_canonical_json_bytes(pass_core)),
    }
    _validate_receipt_shape(passed)
    passed_bytes = _canonical_json_bytes(passed)
    _atomic_replace_file(_receipt_path(root, must_exist=True), passed_bytes)
    final_raw, final_payload = _load_receipt(root)
    if final_raw != passed_bytes or final_payload != passed:
        raise RuntimeError("consumed comparison-launch receipt was not durable")
    return passed


def _verify_claim(root: Path, capability: Mapping[str, Any]) -> None:
    raw, claim = _load_canonical_json(
        _claim_path(root, must_exist=True),
        where="comparison-launch capability claim",
    )
    if raw != _canonical_json_bytes(claim):
        raise RuntimeError("comparison-launch capability claim must be canonical JSON")
    _require_exact_keys(claim, _CLAIM_KEYS, where="comparison-launch capability claim")
    if claim.get("schema_version") != CLAIM_SCHEMA_VERSION or claim.get("state") != "consumed":
        raise RuntimeError("comparison-launch capability claim schema or state drifted")
    self_hash = _require_sha256(
        claim.get("claim_sha256"),
        where="comparison-launch capability claim self-hash",
    )
    core = {key: value for key, value in claim.items() if key != "claim_sha256"}
    if not hmac.compare_digest(_sha256(_canonical_json_bytes(core)), self_hash):
        raise RuntimeError("comparison-launch capability claim self-hash mismatch")
    expected = {
        "schema_version": CLAIM_SCHEMA_VERSION,
        "state": "consumed",
        "nonce_sha256": capability["nonce_sha256"],
        "launcher_process_id": capability["launcher_process_id"],
        "child_process_id": capability["child_process_id"],
        "pending_receipt_sha256": capability["pending_receipt_sha256"],
        "claimed_at_utc": capability["consumed_at_utc"],
    }
    if core != expected:
        raise RuntimeError("comparison-launch capability claim differs from PASS receipt")


def verify_phase40_comparison_launch_receipt(
    *,
    repo_root: Path,
    launcher_host_authority: ExecutableAuthority | None = None,
    python_authority: ExecutableAuthority | None = None,
) -> dict[str, Any]:
    """Reopen every fixed authority and verify the consumed launch receipt."""

    root = _verified_repo_root(repo_root)
    _, payload = _load_receipt(root)
    if payload.get("schema_version") != SCHEMA_VERSION or payload.get("status") != "PASS":
        raise RuntimeError("comparison-launch receipt is not a supported PASS receipt")
    _verify_receipt_authority(
        root=root,
        payload=payload,
        launcher_host_authority=(
            default_launcher_host_authority()
            if launcher_host_authority is None
            else launcher_host_authority
        ),
        python_authority=(
            default_python_authority() if python_authority is None else python_authority
        ),
    )
    _verify_claim(root, payload["launch_capability"])
    _reject_payload_leakage(payload, where="comparison-launch receipt")
    return payload


__all__ = [
    "ALLOWED_LAUNCHER_HOST_SHA256",
    "ALLOWED_LAUNCHER_HOST_VERSION",
    "ALLOWED_PYTHON_SHA256",
    "ALLOWED_PYTHON_VERSION",
    "CAPABILITY_LAUNCHER_PID_ENV",
    "CAPABILITY_NONCE_ENV",
    "CAPABILITY_PENDING_SHA256_ENV",
    "CLAIM_SCHEMA_VERSION",
    "ExecutableAuthority",
    "FINALIZER_SOURCE_TREE_DOMAIN",
    "FINALIZER_SOURCE_ALLOWLIST",
    "FIXED_CLAIM_RELATIVE_PATH",
    "FIXED_FINAL_AUTHORITY_RELATIVE_PATH",
    "FIXED_FINALIZER_COMMAND",
    "FIXED_LAUNCHER_RELATIVE_PATH",
    "FIXED_PHOBERT_CAPSULE_ASSET_RELATIVE_PATHS",
    "FIXED_PHOBERT_CAPSULE_ROOT_RELATIVE_PATH",
    "FIXED_PHOBERT_REQUEST_RELATIVE_PATH",
    "FIXED_RECEIPT_RELATIVE_PATH",
    "FIXED_RUN_REQUEST_RELATIVE_PATH",
    "FIXED_SCOPE_AMENDMENT_RELATIVE_PATH",
    "SCHEMA_VERSION",
    "consume_phase40_comparison_launch_capability",
    "default_launcher_host_authority",
    "default_python_authority",
    "verify_phase40_comparison_launch_receipt",
]
