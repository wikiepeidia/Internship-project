"""Machine-bound, read-only readiness audit for the active Phase 40 chain.

The audit opens only the fixed authorities named below. It never discovers,
stats, hashes, or opens the reserved evaluation split, and it never starts a
GPU process. PASS means the armed fresh-launch chain matches its reviewed
identities; automated PhoBERT resume remains deliberately disabled.
"""

from __future__ import annotations

import argparse
import ctypes
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any


EXPECTED_RUNTIME_ROOT = Path(r"D:\PROJEct\AI MODELS\phase40-full-local-20260825")
EXPECTED_REQUEST_SHA256 = "2512dbe6d7c5b8c16141ebdbdc848382e56b3a5737e8aeea51d7fb89447c643a"
EXPECTED_AMENDMENT_SHA256 = "c183415cee6aa4b0b45184dedede44097e89594a2e50c564280854ea377ebc84"
EXPECTED_CONFIG_SHA256 = "f6bedc5ddc04ca50ba5f737aaf1003b3e27dac676d8082eba33d6cecd97df629"
EXPECTED_SOURCE_ARCHIVE_SHA256 = "eae64f17383d749a7759391d766ad59b337d35155ae89744adeaba8631e71a66"
EXPECTED_SOURCE_MANIFEST_SHA256 = "5903dd5d68881916424e0b529760c3e8810b89a7c207aa714f13171fccf02a3d"
EXPECTED_CONTROLLER_SHA256 = "63f47598fe81749b961ca7c5f056fe4e63925f2ad93f94f9beabafd047246b26"
EXPECTED_CONTROLLER_PARSE_RECEIPT_SHA256 = (
    "31614ba1d26bf7b334377e7b98eafd36e1e61230d99d18a05d7ba30a5b1e9ad0"
)
EXPECTED_CONTROLLER_PREFLIGHT_SHA256 = (
    "7f11d2e964243ad329bc0ce18af05dd0e9594c809801fdce873208cc3895f8b2"
)
EXPECTED_TELEMETRY_SCRIPT_SHA256 = (
    "1bc33f3726b57297a3cc5a69b36831bbd602edac680ba329224b14cf06231c70"
)
EXPECTED_PYTHON_CACHE_ROOT = Path(
    r"D:\PROJEct\AI MODELS\phase40-full-local-20260825\python-cache-v9-11a6227c284f478ba73dd1ae6fa129c1"
)
EXPECTED_CONTROLLER_LEASE_PATH = Path(
    r"D:\PROJEct\AI MODELS\phase40-full-local-20260825\controller\phase40-phobert-chain-controller.lease"
)
EXPECTED_BASE_MANIFEST_SHA256 = "b94e490259cdb42f0fa6c177421519bb4a3944d2693e249bcf8e358cb92dc3f6"
EXPECTED_QWEN_RUN_ID = "phase40-qwen-qlora-full-seed42-v1"
EXPECTED_PHOBERT_RUN_ID = "phase40-phobert-full-seed42-v1"
EXPECTED_PHOBERT_MODEL_ID = "vinai/phobert-base-v2"
EXPECTED_PHOBERT_REVISION = "e966aac8cb889325e073aa5f28ff70aca4dbc8c3"

# PID alone is not authority. Each fixed process is also bound to its creation
# FILETIME and executable image, preventing a recycled handle from passing.
PROCESS_IDENTITIES = (
    (19772, 134321016774482304, Path(r"C:\Users\wikiepeidia\AppData\Local\Programs\Python\Python313\python.exe"), "qwen-trainer"),
    (1576, 134321017671588653, Path(r"C:\Program Files\PowerShell\7\pwsh.exe"), "qwen-supervisor"),
    (20064, 134321351510583152, Path(r"C:\Program Files\PowerShell\7\pwsh.exe"), "phobert-chain-controller"),
)


@dataclass(frozen=True)
class Check:
    name: str
    passed: bool
    severity: str
    evidence: str


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _load_json_bytes(payload: bytes, path: Path) -> dict[str, Any]:
    value = json.loads(payload.decode("utf-8", errors="strict"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def _lexical_absolute(path: Path) -> Path:
    return Path(os.path.abspath(os.path.normpath(os.fspath(path))))


def _reject_reparse_ancestors(path: Path, *, stop: Path) -> None:
    candidate = _lexical_absolute(path)
    boundary = _lexical_absolute(stop)
    try:
        candidate.relative_to(boundary)
    except ValueError as exc:
        raise ValueError(f"Path escaped its authority root: {candidate}") from exc
    current = candidate
    while True:
        stat = os.lstat(current)
        if getattr(stat, "st_file_attributes", 0) & 0x400:
            raise ValueError(f"Reparse point is forbidden in authority path: {current}")
        if current == boundary:
            return
        current = current.parent


class _FileTime(ctypes.Structure):
    _fields_ = (("low", ctypes.c_uint32), ("high", ctypes.c_uint32))

    @property
    def ticks(self) -> int:
        return (int(self.high) << 32) | int(self.low)


def _process_identity(pid: int) -> tuple[int, Path] | None:
    if os.name != "nt":
        return None
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
    kernel32.OpenProcess.restype = ctypes.c_void_p
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel32.CloseHandle.restype = ctypes.c_int
    kernel32.GetProcessTimes.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(_FileTime),
        ctypes.POINTER(_FileTime),
        ctypes.POINTER(_FileTime),
        ctypes.POINTER(_FileTime),
    ]
    kernel32.GetProcessTimes.restype = ctypes.c_int
    kernel32.QueryFullProcessImageNameW.argtypes = [
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_wchar_p,
        ctypes.POINTER(ctypes.c_uint32),
    ]
    kernel32.QueryFullProcessImageNameW.restype = ctypes.c_int
    handle = kernel32.OpenProcess(0x1000, False, pid)
    if not handle:
        return None
    try:
        created = _FileTime()
        exited = _FileTime()
        kernel = _FileTime()
        user = _FileTime()
        if not kernel32.GetProcessTimes(
            handle,
            ctypes.byref(created),
            ctypes.byref(exited),
            ctypes.byref(kernel),
            ctypes.byref(user),
        ):
            return None
        size = ctypes.c_uint32(32768)
        buffer = ctypes.create_unicode_buffer(size.value)
        if not kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
            return None
        return created.ticks, Path(buffer.value)
    finally:
        kernel32.CloseHandle(handle)


def _exclusive_lease_is_held(path: Path) -> tuple[bool, int]:
    """Prove that another live handle currently denies all file sharing."""

    if os.name != "nt":
        return False, 0
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateFileW.argtypes = [
        ctypes.c_wchar_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_void_p,
    ]
    kernel32.CreateFileW.restype = ctypes.c_void_p
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel32.CloseHandle.restype = ctypes.c_int
    handle = kernel32.CreateFileW(
        os.fspath(path),
        0x80000000,  # GENERIC_READ
        0,  # no sharing requested
        None,
        3,  # OPEN_EXISTING
        0x80,  # FILE_ATTRIBUTE_NORMAL
        None,
    )
    invalid = ctypes.c_void_p(-1).value
    if handle == invalid:
        error = ctypes.get_last_error()
        # Only ERROR_SHARING_VIOLATION proves a conflicting live handle. An
        # ACL-driven ERROR_ACCESS_DENIED must never be treated as lease proof.
        return error == 32, error
    kernel32.CloseHandle(handle)
    return False, 0


def _check(condition: bool, name: str, evidence: str, severity: str = "block") -> Check:
    return Check(name=name, passed=condition, severity=severity, evidence=evidence)


def evaluate(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = _lexical_absolute(args.repo_root)
    runtime_root = _lexical_absolute(EXPECTED_RUNTIME_ROOT)
    if not repo_root.is_dir() or not runtime_root.is_dir():
        raise FileNotFoundError("Repository or fixed runtime root is missing")

    paths = {
        "amendment": repo_root / "data/models/phase40/two-full-model-scope-amendment.json",
        "request": repo_root / "data/models/phase40/full-run-request.json",
        "config": repo_root / "data/models/phase40/phobert-config.json",
        "controller": runtime_root / "controller/phase40-qwen-to-phobert-chain-v9.ps1",
        "controller_log": runtime_root / "controller/qwen-to-phobert-chain-v9.log",
        "parse_receipt": runtime_root / "controller/controller-parse-v9.json",
        "preflight": runtime_root / "controller/source-runtime-preflight-v9-armed.json",
        "telemetry_script": runtime_root / "controller/phase40-system-telemetry-v3.ps1",
        "base_manifest": runtime_root / "transfer-root-v3/data/models/phase40/base/phobert-base-v2.provenance.json",
        "source_archive": runtime_root / "transfer-root-v3/data/models/phase40/source/phase40-source.zip",
        "source_manifest": runtime_root / "transfer-root-v3/data/models/phase40/source/phase40-source-manifest.json",
    }
    metadata_paths = {
        "controller_stdout": runtime_root / "controller/qwen-to-phobert-chain-v9.stdout.log",
        "controller_stderr": runtime_root / "controller/qwen-to-phobert-chain-v9.stderr.log",
        "controller_lease": EXPECTED_CONTROLLER_LEASE_PATH,
    }
    for name, path in {**paths, **metadata_paths}.items():
        authority_root = repo_root if name in {"amendment", "request", "config"} else runtime_root
        _reject_reparse_ancestors(path, stop=authority_root)
        if not path.is_file():
            raise FileNotFoundError(f"Required named authority is missing: {path}")

    # Every authority is opened exactly once. All parsing, comparisons, and
    # reported hashes below use this one byte snapshot rather than reopening a
    # mutable path between validation steps.
    snapshots = {name: path.read_bytes() for name, path in paths.items()}
    amendment = _load_json_bytes(snapshots["amendment"], paths["amendment"])
    request = _load_json_bytes(snapshots["request"], paths["request"])
    config = _load_json_bytes(snapshots["config"], paths["config"])
    provenance = _load_json_bytes(snapshots["base_manifest"], paths["base_manifest"])
    preflight = _load_json_bytes(snapshots["preflight"], paths["preflight"])
    parse_receipt = _load_json_bytes(
        snapshots["parse_receipt"], paths["parse_receipt"]
    )
    controller_source = snapshots["controller"].decode("utf-8", errors="strict")
    controller_log = snapshots["controller_log"].decode("utf-8", errors="strict")
    controller_stdout_bytes = metadata_paths["controller_stdout"].stat().st_size
    controller_stderr_bytes = metadata_paths["controller_stderr"].stat().st_size
    lease_held, lease_open_error = _exclusive_lease_is_held(
        metadata_paths["controller_lease"]
    )

    phobert_template = request.get("control_template_by_run", {}).get(EXPECTED_PHOBERT_RUN_ID, {})
    expected_control = dict(phobert_template.get("controls_without_accelerator", {}))
    expected_control["accelerator"] = {
        "accelerator_type": "operator-supplied",
        "accelerator_name": "operator-supplied",
        "compute_capability": None,
        "total_memory_bytes": 0,
    }
    process_checks: list[Check] = []
    for pid, expected_ticks, expected_image, role in PROCESS_IDENTITIES:
        actual = _process_identity(pid)
        process_checks.append(
            _check(
                actual is not None
                and actual[0] == expected_ticks
                and os.path.normcase(os.fspath(actual[1])) == os.path.normcase(os.fspath(expected_image)),
                f"{role}-fixed-process-identity",
                f"pid={pid} expected_ticks={expected_ticks} actual={actual}",
            )
        )

    checks = [
        _check(_sha256_bytes(snapshots["request"]) == EXPECTED_REQUEST_SHA256, "immutable-request-sha256", EXPECTED_REQUEST_SHA256),
        _check(_sha256_bytes(snapshots["amendment"]) == EXPECTED_AMENDMENT_SHA256, "amendment-sha256", EXPECTED_AMENDMENT_SHA256),
        _check(_sha256_bytes(snapshots["config"]) == EXPECTED_CONFIG_SHA256, "phobert-config-sha256", EXPECTED_CONFIG_SHA256),
        _check(_sha256_bytes(snapshots["source_archive"]) == EXPECTED_SOURCE_ARCHIVE_SHA256, "source-archive-sha256", EXPECTED_SOURCE_ARCHIVE_SHA256),
        _check(_sha256_bytes(snapshots["source_manifest"]) == EXPECTED_SOURCE_MANIFEST_SHA256, "source-manifest-sha256", EXPECTED_SOURCE_MANIFEST_SHA256),
        _check(
            amendment.get("schema_version") == "phase40-two-full-model-scope-amendment-v1"
            and amendment.get("original_run_request_sha256") == EXPECTED_REQUEST_SHA256
            and amendment.get("active_full_run_ids") == [EXPECTED_QWEN_RUN_ID, EXPECTED_PHOBERT_RUN_ID]
            and amendment.get("quality_model_run_ids") == [EXPECTED_QWEN_RUN_ID, EXPECTED_PHOBERT_RUN_ID]
            and amendment.get("review_model_run_ids") == [EXPECTED_QWEN_RUN_ID, EXPECTED_PHOBERT_RUN_ID]
            and amendment.get("execution_policy") == "local_primary"
            and amendment.get("no_held_out_boundary") is True,
            "complete-amendment-binding",
            "schema/request/two-model scopes/local policy/no-held-out boundary",
        ),
        _check(
            config.get("schema_version") == "phase40-phobert-controls-v1"
            and config.get("planned_optimizer_steps") == 312
            and config.get("num_train_epochs") == 3.0
            and config.get("control") == expected_control,
            "phobert-control-equals-request-template",
            "full control object equals request template plus placeholder accelerator",
        ),
        _check(
            provenance == {
                "content_sha256": "7f84123042ddb5c78ea174a3a4b8951ca6714321bf7b902641157bf155093ae6",
                "file_count": 18,
                "local_path_sha256": "2f16fd979a4518b1d3eae23d820249c5500a52fb30dc19ebef5d0650967b3a06",
                "model_id": EXPECTED_PHOBERT_MODEL_ID,
                "model_revision": EXPECTED_PHOBERT_REVISION,
                "schema_version": "phase40-phobert-base-provenance-v1",
                "total_bytes": 1085776443,
            }
            and _sha256_bytes(snapshots["base_manifest"]) == EXPECTED_BASE_MANIFEST_SHA256,
            "phobert-base-provenance-content",
            EXPECTED_BASE_MANIFEST_SHA256,
        ),
        _check(
            _sha256_bytes(snapshots["controller"]) == EXPECTED_CONTROLLER_SHA256
            and _sha256_bytes(snapshots["parse_receipt"])
            == EXPECTED_CONTROLLER_PARSE_RECEIPT_SHA256
            and parse_receipt.get("schema_version") == "phase40-controller-parse-v1"
            and parse_receipt.get("controller_sha256") == EXPECTED_CONTROLLER_SHA256
            and parse_receipt.get("parse_error_count") == 0
            and parse_receipt.get("parse_token_count") == 6676
            and parse_receipt.get("reserved_split_access_attempted") is False,
            "controller-source-and-parse-pin",
            EXPECTED_CONTROLLER_SHA256,
        ),
        _check(
            _sha256_bytes(snapshots["preflight"]) == EXPECTED_CONTROLLER_PREFLIGHT_SHA256
            and preflight.get("schema_version") == "phase40-source-runtime-preflight-v3"
            and preflight.get("stage") == "armed"
            and preflight.get("controller_pid") == PROCESS_IDENTITIES[2][0]
            and preflight.get("controller_creation_utc_filetime_ticks")
            == PROCESS_IDENTITIES[2][1]
            and preflight.get("request_sha256") == EXPECTED_REQUEST_SHA256
            and preflight.get("source_archive_sha256") == EXPECTED_SOURCE_ARCHIVE_SHA256
            and preflight.get("source_manifest_sha256") == EXPECTED_SOURCE_MANIFEST_SHA256
            and preflight.get("source_file_count") == 28
            and preflight.get("controller_sha256") == EXPECTED_CONTROLLER_SHA256
            and preflight.get("source_runtime")
            == os.fspath(runtime_root / "source-runtime-v9")
            and preflight.get("telemetry_script_sha256")
            == EXPECTED_TELEMETRY_SCRIPT_SHA256
            and preflight.get("telemetry_script_parse_error_count") == 0
            and preflight.get("python_cache_root")
            == os.fspath(EXPECTED_PYTHON_CACHE_ROOT)
            and preflight.get("python_cache_root_absent") is True
            and preflight.get("adjacent_bytecode_cache_allowed") is False
            and preflight.get("controller_lease_path")
            == os.fspath(EXPECTED_CONTROLLER_LEASE_PATH)
            and preflight.get("controller_lease_held") is True
            and preflight.get("controller_lease_file_share") == "none"
            and preflight.get("reserved_split_access_attempted_by_controller") is False,
            "controller-retained-source-preflight",
            json.dumps(preflight, sort_keys=True),
        ),
        _check(
            _sha256_bytes(snapshots["telemetry_script"])
            == EXPECTED_TELEMETRY_SCRIPT_SHA256,
            "telemetry-script-content-pin",
            EXPECTED_TELEMETRY_SCRIPT_SHA256,
        ),
        _check(
            _lexical_absolute(EXPECTED_PYTHON_CACHE_ROOT).parent == runtime_root
            and not EXPECTED_PYTHON_CACHE_ROOT.exists()
            and not EXPECTED_PYTHON_CACHE_ROOT.is_symlink(),
            "invocation-scoped-python-cache-still-absent",
            os.fspath(EXPECTED_PYTHON_CACHE_ROOT),
        ),
        _check(
            f"controller_pid={PROCESS_IDENTITIES[2][0]} " in controller_log
            and f"controller_creation_utc_filetime_ticks={PROCESS_IDENTITIES[2][1]} "
            in controller_log
            and "frozen source runtime verified stage=armed operation= files=28" in controller_log
            and f"telemetry_sha256={EXPECTED_TELEMETRY_SCRIPT_SHA256}" in controller_log
            and "telemetry_parse_errors=0" in controller_log
            and "lease_held=true" in controller_log
            and f"armed after qwen_supervisor_pid={PROCESS_IDENTITIES[1][0]}" in controller_log,
            "controller-log-binding",
            os.fspath(paths["controller_log"]),
        ),
        _check(controller_stdout_bytes == 0, "controller-stdout-empty", f"bytes={controller_stdout_bytes}"),
        _check(controller_stderr_bytes == 0, "controller-stderr-empty", f"bytes={controller_stderr_bytes}"),
        _check(
            lease_held,
            "exclusive-controller-lease-held",
            f"path={EXPECTED_CONTROLLER_LEASE_PATH} blocked_open_error={lease_open_error}",
        ),
        _check(
            "[ValidateRange(0, 0)]" in controller_source
            and "[int]$MaxResumeAttempts = 0" in controller_source,
            "broken-v3-phobert-resume-disabled",
            "fresh launch only; any incomplete run fails closed",
        ),
        *process_checks,
    ]
    opened_files = [
        {
            "logical_name": name,
            "path": os.fspath(path),
            "sha256": _sha256_bytes(snapshots[name]),
        }
        for name, path in paths.items()
    ]
    metadata_only_files = [
        {
            "logical_name": name,
            "path": os.fspath(path),
            "bytes": path.stat().st_size,
        }
        for name, path in metadata_paths.items()
    ]
    return {
        "schema_version": "phase40-idle-readiness-spike-v2",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "verdict": "PASS" if all(item.passed for item in checks) else "BLOCK",
        "scope": "machine-bound fresh PhoBERT launch readiness; automated resume excluded",
        "reserved_split_access_attempted_by_checker": False,
        "gpu_process_launched_by_checker": False,
        "opened_files": opened_files,
        "metadata_only_files": metadata_only_files,
        "checks": [asdict(item) for item in checks],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    return parser


def main() -> int:
    try:
        result = evaluate(build_parser().parse_args())
    except Exception as error:
        result = {
            "schema_version": "phase40-idle-readiness-spike-v2",
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "verdict": "BLOCK",
            "scope": "machine-bound fresh PhoBERT launch readiness; automated resume excluded",
            "reserved_split_access_attempted_by_checker": False,
            "gpu_process_launched_by_checker": False,
            "opened_files": [],
            "checks": [
                asdict(Check("probe-execution", False, "block", f"{type(error).__name__}: {error}"))
            ],
        }
    # ASCII escaping keeps machine-readable output safe under Windows' legacy
    # console code pages even when the repository path contains Vietnamese.
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if result["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
