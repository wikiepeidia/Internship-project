"""Strict external preflight authority for the Phase 40 comparison launch.

The PowerShell launcher mirrors this module without importing Python before the
preflight receipt exists.  This module is the canonical schema/verifier used by
the in-process comparison boundary and by synthetic parity tests.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import shutil
import stat
from typing import Any


SCHEMA_VERSION = "phase40-comparison-launch-receipt-v1"
FINALIZER_SOURCE_TREE_DOMAIN = b"phase40-comparison-finalizer-source-v1\0"
FIXED_RUN_REQUEST_RELATIVE_PATH = PurePosixPath(
    "data/models/phase40/full-run-request.json"
)
FIXED_SCOPE_AMENDMENT_RELATIVE_PATH = PurePosixPath(
    "data/models/phase40/two-full-model-scope-amendment.json"
)
FIXED_RECEIPT_RELATIVE_PATH = PurePosixPath(
    "data/models/phase40/comparison-launch-receipt.json"
)
FIXED_LAUNCHER_RELATIVE_PATH = PurePosixPath(
    "scripts/phase40_comparison_launcher.ps1"
)

# Duplicated deliberately from the source-amendment producer.  The external
# launcher must reject a self-consistent amendment that expands its read set
# before it opens even the first declared source file.  The producer and this
# consumer are refreshed atomically whenever the finalizer import closure moves.
FINALIZER_SOURCE_ALLOWLIST = (
    "pyproject.toml",
    "src/__init__.py",
    "src/config/__init__.py",
    "src/config/settings.py",
    "src/data_pipeline/__init__.py",
    "src/data_pipeline/processing/__init__.py",
    "src/data_pipeline/processing/normalizer.py",
    "src/data_pipeline/schemas.py",
    "src/model_adaptation/__init__.py",
    "src/model_adaptation/catalog.py",
    "src/model_adaptation/cli.py",
    "src/model_adaptation/convert.py",
    "src/model_adaptation/data.py",
    "src/model_adaptation/doctor.py",
    "src/model_adaptation/explanation_review.py",
    "src/model_adaptation/phase40_callbacks.py",
    "src/model_adaptation/phase40_contract.py",
    "src/model_adaptation/phase40_evidence.py",
    "src/model_adaptation/phase40_graphs.py",
    "src/model_adaptation/phase40_handoff.py",
    "src/model_adaptation/phase40_metrics.py",
    "src/model_adaptation/phase40_modes.py",
    "src/model_adaptation/phase40_notebooks.py",
    "src/model_adaptation/pilot.py",
    "src/model_adaptation/prompts.py",
    "src/model_adaptation/registry.py",
    "src/model_adaptation/release_evaluation.py",
    "src/model_adaptation/release_gates.py",
    "src/model_adaptation/release_readiness.py",
    "src/model_adaptation/schemas.py",
    "src/model_adaptation/training.py",
    "src/runtime/__init__.py",
    "src/runtime/analyzers/__init__.py",
    "src/runtime/analyzers/accelerated.py",
    "src/runtime/analyzers/base.py",
    "src/runtime/analyzers/gguf.py",
    "src/runtime/analyzers/heuristic.py",
    "src/runtime/analyzers/local_model.py",
    "src/runtime/analyzers/rules.py",
    "src/runtime/contracts.py",
    "src/runtime/service.py",
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
    "src.model_adaptation.cli",
    "phase40-finalize-comparison",
    "--request-path",
    FIXED_RUN_REQUEST_RELATIVE_PATH.as_posix(),
    "--scope-amendment-path",
    FIXED_SCOPE_AMENDMENT_RELATIVE_PATH.as_posix(),
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
        "phase40-phobert-full-seed42-v1="
        "data/models/phase40/full/phobert"
    ),
    "--gpu-identity",
    (
        "phase40-qwen-qlora-full-seed42-v1="
        "NVIDIA GeForce RTX 5050 Laptop GPU"
    ),
    "--gpu-identity",
    (
        "phase40-phobert-full-seed42-v1="
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
_AMENDMENT_KEYS = {
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
    "request",
    "scope_amendment",
    "finalizer_authority",
    "launcher",
    "launcher_host",
    "python",
    "finalizer_command",
    "preflight_started_at_utc",
    "preflight_completed_at_utc",
    "receipt_created_at_utc",
    "prelaunch_state",
    "receipt_sha256",
}
_REQUEST_RECEIPT_KEYS = {"relative_path", "sha256"}
_AMENDMENT_RECEIPT_KEYS = {
    "relative_path",
    "sha256",
    "original_run_request_sha256",
}
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
    if relative == "pyproject.toml":
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


def _validate_request(request: Mapping[str, Any]) -> None:
    _require_exact_keys(request, _REQUEST_KEYS, where="Phase 40 run request")
    if request.get("schema_version") != "phase40-full-run-request-v1":
        raise RuntimeError("Phase 40 run-request schema drifted")
    if request.get("no_held_out_boundary") is not True:
        raise RuntimeError("Phase 40 run request does not preserve the held-out boundary")


def _validate_amendment(amendment: Mapping[str, Any], *, request_sha256: str) -> None:
    _require_exact_keys(amendment, _AMENDMENT_KEYS, where="Phase 40 scope amendment")
    if amendment.get("schema_version") != "phase40-two-full-model-scope-amendment-v1":
        raise RuntimeError("Phase 40 scope-amendment schema drifted")
    if amendment.get("original_run_request_path") != FIXED_RUN_REQUEST_RELATIVE_PATH.as_posix():
        raise RuntimeError("scope amendment names an alternate run-request path")
    if amendment.get("original_run_request_sha256") != request_sha256:
        raise RuntimeError("scope amendment binds a different canonical run request")
    active_ids = [
        "phase40-qwen-qlora-full-seed42-v1",
        "phase40-phobert-full-seed42-v1",
    ]
    active_roots = [
        "data/models/phase40/full/qwen-qlora",
        "data/models/phase40/full/phobert",
    ]
    if (
        amendment.get("active_full_run_ids") != active_ids
        or amendment.get("quality_model_run_ids") != active_ids
        or amendment.get("review_model_run_ids") != active_ids
        or amendment.get("active_returned_roots") != active_roots
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
        raise RuntimeError("Phase 40 scope-amendment policy or model set drifted")


def _verified_finalizer_authority(
    root: Path,
    amendment: Mapping[str, Any],
) -> dict[str, Any]:
    authority = amendment.get("comparison_finalizer_authority")
    if not isinstance(authority, Mapping):
        raise RuntimeError("scope amendment has no comparison-finalizer authority")
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


def _authority_snapshot(root: Path) -> dict[str, Any]:
    request_path = _contained_path(root, FIXED_RUN_REQUEST_RELATIVE_PATH)
    amendment_path = _contained_path(root, FIXED_SCOPE_AMENDMENT_RELATIVE_PATH)
    request_bytes, request = _load_canonical_json(
        request_path,
        where="canonical Phase 40 run request",
    )
    amendment_bytes, amendment = _load_canonical_json(
        amendment_path,
        where="canonical Phase 40 scope amendment",
    )
    _validate_request(request)
    request_sha256 = _sha256(request_bytes)
    _validate_amendment(amendment, request_sha256=request_sha256)
    finalizer = _verified_finalizer_authority(root, amendment)
    return {
        "request": {
            "relative_path": FIXED_RUN_REQUEST_RELATIVE_PATH.as_posix(),
            "sha256": request_sha256,
        },
        "scope_amendment": {
            "relative_path": FIXED_SCOPE_AMENDMENT_RELATIVE_PATH.as_posix(),
            "sha256": _sha256(amendment_bytes),
            "original_run_request_sha256": request_sha256,
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


def _receipt_core(
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
    core = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
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
        "prelaunch_state": {
            "python_launched": False,
            "model_bundle_opened": False,
            "reserved_split_access_attempted": False,
        },
    }
    _reject_payload_leakage(core, where="comparison-launch receipt")
    return core


def _validate_receipt_shape(payload: Mapping[str, Any]) -> None:
    _require_exact_keys(payload, _RECEIPT_KEYS, where="comparison-launch receipt")
    nested = (
        ("request", _REQUEST_RECEIPT_KEYS),
        ("scope_amendment", _AMENDMENT_RECEIPT_KEYS),
        ("finalizer_authority", _FINALIZER_AUTHORITY_KEYS),
        ("launcher", _LAUNCHER_RECEIPT_KEYS),
        ("launcher_host", _EXECUTABLE_RECEIPT_KEYS),
        ("python", _EXECUTABLE_RECEIPT_KEYS),
        ("prelaunch_state", _PRELAUNCH_STATE_KEYS),
    )
    for field, keys in nested:
        value = payload.get(field)
        if not isinstance(value, Mapping):
            raise RuntimeError(f"comparison-launch receipt {field} must be an object")
        _require_exact_keys(value, keys, where=f"comparison-launch receipt {field}")
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


def freeze_phase40_comparison_launch_receipt(
    *,
    repo_root: Path,
    launcher_host_authority: ExecutableAuthority | None = None,
    python_authority: ExecutableAuthority | None = None,
    preflight_started_at_utc: str,
    preflight_completed_at_utc: str,
    receipt_created_at_utc: str,
) -> dict[str, Any]:
    """Freeze one create-only prelaunch PASS receipt at the code-fixed path."""

    root = _verified_repo_root(repo_root)
    destination = _receipt_path(root, must_exist=False)
    core = _receipt_core(
        root=root,
        launcher_host_authority=(
            default_launcher_host_authority()
            if launcher_host_authority is None
            else launcher_host_authority
        ),
        python_authority=(
            default_python_authority() if python_authority is None else python_authority
        ),
        preflight_started_at_utc=preflight_started_at_utc,
        preflight_completed_at_utc=preflight_completed_at_utc,
        receipt_created_at_utc=receipt_created_at_utc,
    )
    payload = {
        **core,
        "receipt_sha256": _sha256(_canonical_json_bytes(core)),
    }
    _validate_receipt_shape(payload)
    _write_new_file(destination, _canonical_json_bytes(payload))
    return payload


def verify_phase40_comparison_launch_receipt(
    *,
    repo_root: Path,
    launcher_host_authority: ExecutableAuthority | None = None,
    python_authority: ExecutableAuthority | None = None,
) -> dict[str, Any]:
    """Reopen every fixed authority and verify the portable prelaunch receipt."""

    root = _verified_repo_root(repo_root)
    path = _receipt_path(root, must_exist=True)
    raw, payload = _load_canonical_json(path, where="comparison-launch receipt")
    if raw != _canonical_json_bytes(payload):
        raise RuntimeError("comparison-launch receipt must be canonical JSON")
    _validate_receipt_shape(payload)
    if payload.get("schema_version") != SCHEMA_VERSION or payload.get("status") != "PASS":
        raise RuntimeError("comparison-launch receipt is not a supported PASS receipt")
    self_hash = _require_sha256(
        payload.get("receipt_sha256"),
        where="comparison-launch receipt self-hash",
    )
    core = {key: value for key, value in payload.items() if key != "receipt_sha256"}
    if _sha256(_canonical_json_bytes(core)) != self_hash:
        raise RuntimeError("comparison-launch receipt self-hash mismatch")
    prelaunch = payload["prelaunch_state"]
    if prelaunch != {
        "python_launched": False,
        "model_bundle_opened": False,
        "reserved_split_access_attempted": False,
    }:
        raise RuntimeError("comparison-launch receipt overclaims prelaunch activity")
    if payload.get("finalizer_command") != list(FIXED_FINALIZER_COMMAND):
        raise RuntimeError("comparison-launch receipt finalizer command drifted")
    expected_core = _receipt_core(
        root=root,
        launcher_host_authority=(
            default_launcher_host_authority()
            if launcher_host_authority is None
            else launcher_host_authority
        ),
        python_authority=(
            default_python_authority() if python_authority is None else python_authority
        ),
        preflight_started_at_utc=payload["preflight_started_at_utc"],
        preflight_completed_at_utc=payload["preflight_completed_at_utc"],
        receipt_created_at_utc=payload["receipt_created_at_utc"],
    )
    if core != expected_core:
        raise RuntimeError("comparison-launch receipt is stale or differs from fixed authority")
    _reject_payload_leakage(payload, where="comparison-launch receipt")
    return payload


__all__ = [
    "ALLOWED_LAUNCHER_HOST_SHA256",
    "ALLOWED_LAUNCHER_HOST_VERSION",
    "ALLOWED_PYTHON_SHA256",
    "ALLOWED_PYTHON_VERSION",
    "ExecutableAuthority",
    "FINALIZER_SOURCE_TREE_DOMAIN",
    "FINALIZER_SOURCE_ALLOWLIST",
    "FIXED_FINALIZER_COMMAND",
    "FIXED_LAUNCHER_RELATIVE_PATH",
    "FIXED_RECEIPT_RELATIVE_PATH",
    "FIXED_RUN_REQUEST_RELATIVE_PATH",
    "FIXED_SCOPE_AMENDMENT_RELATIVE_PATH",
    "SCHEMA_VERSION",
    "default_launcher_host_authority",
    "default_python_authority",
    "freeze_phase40_comparison_launch_receipt",
    "verify_phase40_comparison_launch_receipt",
]
