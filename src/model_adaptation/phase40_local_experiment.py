"""Fail-closed local LoRA/QLoRA decision experiment for Phase 40.

The module deliberately separates portable evidence from disposable runtime
files.  One immutable genesis record owns the two-hour clock; later commands
append stage claims and may never reset that clock.  The real held-out split is
not an input to any public function in this module.
"""

from __future__ import annotations

import argparse
import csv
import ctypes
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import importlib
import importlib.metadata
import importlib.util
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import statistics
import subprocess
import sys
import time
from typing import Any, Callable, Mapping, Sequence


QWEN_MODEL_ID = "Qwen/Qwen3-4B-Instruct-2507"
QWEN_REVISION = "cdbee75f17c01a7cc42f958dc650907174af0554"
BITSANDBYTES_VERSION = "0.50.1"
APPROVE_AUTHORITY = "approve bitsandbytes 0.50.1"
REJECT_AUTHORITY_PREFIX = "reject bitsandbytes 0.50.1: "

DECISION_ROOT_RELATIVE_PATH = Path(
    "data/models/phase40/probes/rtx5050-local-decision"
)
TRAIN_RELATIVE_PATH = Path("data/splits/train.jsonl")
VAL_RELATIVE_PATH = Path("data/splits/val.jsonl")
DOWNSTREAM_CONTRACT_RELATIVE_PATH = Path(
    ".planning/phases/39-independent-quality-re-judge/"
    "39-DOWNSTREAM-DATA-CONTRACT.json"
)
EXTERNAL_QWEN_SNAPSHOT = Path(
    r"D:\PROJEct\AI MODELS\base\qwen3-4b-instruct-2507"
)
EXTERNAL_DOWNLOAD_MANIFEST = Path(
    r"D:\PROJEct\AI MODELS\manifests\download-manifest.json"
)

CANONICAL_TRAIN_ROWS = 1658
CANONICAL_VAL_ROWS = 219
CANONICAL_TRAIN_SHA256 = (
    "5fa46382db8fb477ef91ec4ba770bf3f8756df9f98b9950fdf5bc1f6ff402e8b"
)
CANONICAL_VAL_SHA256 = (
    "746ae6edb5008a8be8e9ef9d65f89fc44e559f99f28cd8d6a77f203ea5986d3c"
)

DECISION_WINDOW_SECONDS = 7200.0
LORA_SOFT_LIMIT_SECONDS = 1800.0
LORA_HARD_LIMIT_SECONDS = 3600.0
WARMUP_OPTIMIZER_STEPS = 5
MEASURED_OPTIMIZER_STEPS = 40
PLANNED_FULL_OPTIMIZER_STEPS = 1245
TELEMETRY_INTERVAL_SECONDS = 2.0
TELEMETRY_STALE_AFTER_SECONDS = 4.0

STATE_SCHEMA_VERSION = "phase40-local-decision-state-v1"
CLOCK_SCHEMA_VERSION = "phase40-local-decision-clock-v1"
LEDGER_SCHEMA_VERSION = "phase40-local-stage-ledger-v1"
TELEMETRY_SCHEMA_VERSION = "phase40-local-telemetry-v1"
OUTCOME_SCHEMA_VERSION = "phase40-local-outcome-v1"
AUTHORITY_SCHEMA_VERSION = "phase40-package-authority-v1"
PACKAGE_SCHEMA_VERSION = "phase40-package-runtime-v1"
MANIFEST_SCHEMA_VERSION = "phase40-local-decision-manifest-v1"

_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_WINDOWS_ABSOLUTE = re.compile(r"^[A-Za-z]:[\\/]")
_STAGE_ORDER = (
    "preflight",
    "lora",
    "record-authority",
    "verify-package",
    "qlora",
    "finalize",
)
_TELEMETRY_VALUE_KEYS = {
    "system_ram_total_bytes",
    "system_ram_available_bytes",
    "system_ram_used_bytes",
    "process_rss_bytes",
    "torch_allocated_bytes",
    "torch_reserved_bytes",
    "torch_peak_allocated_bytes",
    "torch_peak_reserved_bytes",
    "device_vram_total_mib",
    "device_vram_used_mib",
    "device_vram_free_mib",
    "gpu_utilization_percent",
    "gpu_temperature_c",
    "gpu_power_w",
    "gpu_performance_state",
    "nvidia_raw",
}


class _DuplicateJsonKey(ValueError):
    pass


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateJsonKey(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _canonical_json_bytes(value: object) -> bytes:
    _require_portable(value)
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def _require_portable(value: object, *, location: str = "$") -> None:
    if value is None or isinstance(value, (bool, int)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"non-finite number in retained evidence at {location}")
        return
    if isinstance(value, Path):
        raise ValueError(f"Path objects are forbidden in retained evidence at {location}")
    if isinstance(value, str):
        if _WINDOWS_ABSOLUTE.match(value) or value.startswith(("/", "\\\\")):
            raise ValueError(f"absolute path is forbidden in retained evidence at {location}")
        if "\x00" in value:
            raise ValueError(f"NUL is forbidden in retained evidence at {location}")
        return
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) or not key for key in value):
            raise ValueError(f"retained evidence keys must be non-empty strings at {location}")
        for key, item in value.items():
            _require_portable(item, location=f"{location}.{key}")
        return
    if isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _require_portable(item, location=f"{location}[{index}]")
        return
    raise ValueError(f"unsupported retained evidence type at {location}: {type(value).__name__}")


def _read_json(path: Path) -> dict[str, object]:
    path = Path(path)
    if not path.is_file() or path.is_symlink():
        raise FileNotFoundError(f"missing safe JSON artifact: {path}")
    try:
        payload = json.loads(
            path.read_text(encoding="utf-8", errors="strict"),
            object_pairs_hook=_reject_duplicate_keys,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, _DuplicateJsonKey) as exc:
        raise RuntimeError(f"invalid strict JSON artifact: {path.name}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"JSON artifact must contain an object: {path.name}")
    _require_portable(payload)
    return payload


def _write_immutable_json(path: Path, payload: Mapping[str, object]) -> Path:
    output = Path(path)
    data = _canonical_json_bytes(dict(payload))
    if output.exists():
        if output.is_symlink() or output.read_bytes() != data:
            raise FileExistsError(f"refusing to replace immutable artifact: {output.name}")
        return output
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.parent.is_symlink():
        raise ValueError("immutable evidence parent must not be a symlink")
    temporary = output.with_name(f".{output.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, output)
    finally:
        if temporary.exists():
            temporary.unlink()
    return output


def _write_immutable_bytes(path: Path, data: bytes) -> Path:
    output = Path(path)
    if output.exists() or output.is_symlink():
        if output.is_file() and not output.is_symlink() and output.read_bytes() == data:
            return output
        raise FileExistsError(f"refusing to replace immutable artifact: {output.name}")
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.parent.is_symlink() or _is_reparse_point(output.parent):
        raise ValueError("immutable evidence parent must not be a link or reparse point")
    temporary = output.with_name(f".{output.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, output)
    finally:
        if temporary.exists():
            temporary.unlink()
    return output


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _parse_utc(value: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("UTC timestamps must use the canonical trailing-Z form")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError("invalid UTC timestamp") from exc
    return parsed.astimezone(timezone.utc)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _lexical_absolute(path: Path) -> Path:
    return Path(os.path.abspath(os.path.normpath(os.fspath(path))))


def _same_path(left: Path, right: Path) -> bool:
    return os.path.normcase(os.fspath(_lexical_absolute(left))) == os.path.normcase(
        os.fspath(_lexical_absolute(right))
    )


def _path_identity_sha256(path: Path) -> str:
    return hashlib.sha256(
        os.path.normcase(os.fspath(_lexical_absolute(path))).encode("utf-8")
    ).hexdigest()


def _boot_identity() -> str:
    """Return a stable-enough, path-free identity for the current OS boot."""

    try:
        psutil = importlib.import_module("psutil")
        boot_epoch = int(psutil.boot_time())
        return hashlib.sha256(f"{os.name}\0{boot_epoch}".encode("utf-8")).hexdigest()
    except (ImportError, OSError, ValueError):
        pass
    if os.name != "nt":
        boot_id = Path("/proc/sys/kernel/random/boot_id")
        if boot_id.is_file():
            value = boot_id.read_text(encoding="ascii", errors="strict").strip()
            return hashlib.sha256(value.encode("ascii")).hexdigest()
    uptime_seconds: float
    if os.name == "nt":
        uptime_seconds = float(ctypes.windll.kernel32.GetTickCount64()) / 1000.0
    else:
        uptime_seconds = time.monotonic()
    boot_epoch_minute = int((time.time() - uptime_seconds) // 60)
    material = f"{os.name}\0{boot_epoch_minute}".encode("utf-8")
    return hashlib.sha256(material).hexdigest()


@dataclass(frozen=True, slots=True)
class LocalDecisionState:
    experiment_id: str
    started_utc: str
    started_monotonic: float
    deadline_monotonic: float
    decision_window_seconds: float
    boot_identity: str
    input_evidence_sha256: str
    base_model_provenance_sha256: str
    torch_identity_sha256: str
    decision_root_path_sha256: str
    package_baseline_sha256: str
    clock_genesis_sha256: str
    repo_root_path_sha256: str | None = None
    schema_version: str = STATE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != STATE_SCHEMA_VERSION:
            raise ValueError("unsupported local-decision state schema")
        if self.experiment_id != "rtx5050-local-decision":
            raise ValueError("unexpected local-decision experiment identity")
        _parse_utc(self.started_utc)
        if self.decision_window_seconds != DECISION_WINDOW_SECONDS:
            raise ValueError("local decision window must be exactly 7,200 seconds")
        if self.deadline_monotonic != self.started_monotonic + self.decision_window_seconds:
            raise ValueError("local decision deadline does not match its immutable start")
        if not self.boot_identity:
            raise ValueError("local decision state requires a boot identity")
        for value in (
            self.input_evidence_sha256,
            self.base_model_provenance_sha256,
            self.torch_identity_sha256,
            self.decision_root_path_sha256,
            self.package_baseline_sha256,
            self.clock_genesis_sha256,
        ):
            if not _HEX64.fullmatch(value):
                raise ValueError("local decision state contains an invalid artifact hash")
        if self.repo_root_path_sha256 is not None and not _HEX64.fullmatch(
            self.repo_root_path_sha256
        ):
            raise ValueError("local decision state contains an invalid repository-root hash")

    def as_json_dict(self) -> dict[str, object]:
        return asdict(self)


def _append_jsonl(path: Path, payload: Mapping[str, object]) -> Path:
    output = Path(path)
    data = _canonical_json_bytes(dict(payload))
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.is_symlink() or output.parent.is_symlink():
        raise ValueError("append-only evidence must not use symlinks")
    with output.open("ab") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    return output


def _load_jsonl(path: Path) -> list[dict[str, object]]:
    path = Path(path)
    if not path.is_file() or path.is_symlink():
        raise FileNotFoundError(f"missing append-only artifact: {path.name}")
    result: list[dict[str, object]] = []
    with path.open("r", encoding="utf-8", errors="strict", newline="") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.endswith("\n"):
                raise RuntimeError(f"JSONL line {line_number} is not newline terminated")
            try:
                value = json.loads(line, object_pairs_hook=_reject_duplicate_keys)
            except (json.JSONDecodeError, _DuplicateJsonKey) as exc:
                raise RuntimeError(f"invalid JSONL line {line_number}") from exc
            if not isinstance(value, dict):
                raise RuntimeError(f"JSONL line {line_number} is not an object")
            _require_portable(value)
            result.append(value)
    if not result:
        raise RuntimeError(f"append-only artifact is empty: {path.name}")
    return result


def _ledger_entries(root: Path) -> list[dict[str, object]]:
    path = Path(root) / "stage-ledger.jsonl"
    rows = _load_jsonl(path)
    previous_hash = "0" * 64
    for index, row in enumerate(rows):
        required = {
            "schema_version",
            "sequence_id",
            "stage",
            "timestamp_utc",
            "monotonic_seconds",
            "previous_entry_sha256",
            "artifact_sha256",
            "artifact",
        }
        if set(row) != required:
            raise RuntimeError("stage ledger entry has missing or extra fields")
        if row["schema_version"] != LEDGER_SCHEMA_VERSION or row["sequence_id"] != index:
            raise RuntimeError("stage ledger sequence is invalid")
        if row["previous_entry_sha256"] != previous_hash:
            raise RuntimeError("stage ledger hash chain is broken")
        artifact_relative = _portable_relative_path(row["artifact"])
        artifact_path = Path(root) / artifact_relative
        if (
            not isinstance(row["artifact_sha256"], str)
            or not artifact_path.is_file()
            or _sha256_file(artifact_path) != row["artifact_sha256"]
        ):
            raise RuntimeError(f"stage ledger artifact drifted: {artifact_relative}")
        previous_hash = hashlib.sha256(_canonical_json_bytes(row)).hexdigest()
    stages = [str(row["stage"]) for row in rows]
    if len(stages) != len(set(stages)):
        raise RuntimeError("a local decision stage was replayed")
    return rows


def _append_stage(root: Path, *, stage: str, timestamp_utc: str, monotonic: float, artifact: Path) -> None:
    rows = _ledger_entries(root) if (Path(root) / "stage-ledger.jsonl").exists() else []
    if stage in {str(row["stage"]) for row in rows}:
        raise FileExistsError(f"stage already recorded: {stage}")
    previous_hash = (
        hashlib.sha256(_canonical_json_bytes(rows[-1])).hexdigest()
        if rows
        else "0" * 64
    )
    try:
        artifact_relative = Path(artifact).resolve(strict=True).relative_to(
            Path(root).resolve(strict=True)
        ).as_posix()
    except (FileNotFoundError, ValueError) as exc:
        raise ValueError("stage artifact must be one existing file under the decision root") from exc
    _append_jsonl(
        Path(root) / "stage-ledger.jsonl",
        {
            "schema_version": LEDGER_SCHEMA_VERSION,
            "sequence_id": len(rows),
            "stage": stage,
            "timestamp_utc": timestamp_utc,
            "monotonic_seconds": monotonic,
            "previous_entry_sha256": previous_hash,
            "artifact_sha256": _sha256_file(artifact),
            "artifact": artifact_relative,
        },
    )


def start_decision_clock(
    decision_root: Path,
    *,
    started_utc: str | None = None,
    started_monotonic: float | None = None,
    boot_identity: str | None = None,
) -> dict[str, object]:
    """Create the one clock genesis immediately after lexical path authority."""

    root = Path(decision_root)
    if root.exists() or root.is_symlink():
        raise FileExistsError("local decision root already exists; its clock cannot be reset")
    timestamp = _utc_now() if started_utc is None else started_utc
    monotonic = time.monotonic() if started_monotonic is None else float(started_monotonic)
    boot = _boot_identity() if boot_identity is None else boot_identity
    _parse_utc(timestamp)
    if not math.isfinite(monotonic) or monotonic < 0 or not boot:
        raise ValueError("local decision clock inputs are invalid")
    root.mkdir(parents=True, exist_ok=False)
    payload = {
        "schema_version": CLOCK_SCHEMA_VERSION,
        "experiment_id": "rtx5050-local-decision",
        "started_utc": timestamp,
        "started_monotonic": monotonic,
        "deadline_monotonic": monotonic + DECISION_WINDOW_SECONDS,
        "decision_window_seconds": DECISION_WINDOW_SECONDS,
        "boot_identity": boot,
        "decision_root_path_sha256": _path_identity_sha256(root),
    }
    _write_immutable_json(root / "decision-clock.json", payload)
    return payload


def initialize_decision_root(
    decision_root: Path,
    *,
    input_evidence: Mapping[str, object],
    base_model_provenance: Mapping[str, object],
    torch_identity: Mapping[str, object],
    package_baseline: Mapping[str, object] | None = None,
    started_utc: str | None = None,
    started_monotonic: float | None = None,
    boot_identity: str | None = None,
    clock_genesis: Mapping[str, object] | None = None,
    repo_root_path_sha256: str | None = None,
) -> LocalDecisionState:
    root = Path(decision_root)
    if clock_genesis is None:
        genesis = start_decision_clock(
            root,
            started_utc=started_utc,
            started_monotonic=started_monotonic,
            boot_identity=boot_identity,
        )
        completed_timestamp = str(genesis["started_utc"])
        completed_monotonic = float(genesis["started_monotonic"])
    else:
        genesis = dict(clock_genesis)
        persisted_genesis = _read_json(root / "decision-clock.json")
        if genesis != persisted_genesis:
            raise RuntimeError("supplied clock genesis differs from its immutable artifact")
        if set(path.name for path in root.iterdir()) != {"decision-clock.json"}:
            raise RuntimeError("preflight clock root contains unexpected artifacts")
        completed_timestamp = _utc_now()
        completed_monotonic = time.monotonic()
        if completed_monotonic > float(genesis["deadline_monotonic"]):
            raise TimeoutError("preflight exceeded the immutable two-hour decision window")
        if _boot_identity() != genesis["boot_identity"]:
            raise RuntimeError("OS rebooted while preflight sealed the model snapshot")
    required_clock_fields = {
        "schema_version",
        "experiment_id",
        "started_utc",
        "started_monotonic",
        "deadline_monotonic",
        "decision_window_seconds",
        "boot_identity",
        "decision_root_path_sha256",
    }
    if (
        set(genesis) != required_clock_fields
        or genesis.get("schema_version") != CLOCK_SCHEMA_VERSION
        or genesis.get("experiment_id") != "rtx5050-local-decision"
        or genesis.get("decision_window_seconds") != DECISION_WINDOW_SECONDS
        or float(genesis["deadline_monotonic"])
        != float(genesis["started_monotonic"]) + DECISION_WINDOW_SECONDS
    ):
        raise RuntimeError("immutable local-decision clock genesis is invalid")
    timestamp = str(genesis["started_utc"])
    monotonic = float(genesis["started_monotonic"])
    boot = str(genesis["boot_identity"])
    baseline = (
        {"bitsandbytes_present": False}
        if package_baseline is None
        else dict(package_baseline)
    )
    if set(baseline) != {"bitsandbytes_present"} or not isinstance(
        baseline["bitsandbytes_present"], bool
    ):
        raise ValueError("package baseline must record one boolean bitsandbytes presence fact")
    for payload in (input_evidence, base_model_provenance, torch_identity, baseline):
        _require_portable(payload)

    input_path = _write_immutable_json(root / "input-evidence.json", input_evidence)
    base_path = _write_immutable_json(
        root / "base-model-provenance.json", base_model_provenance
    )
    torch_path = _write_immutable_json(
        root / "environment-preflight.json", torch_identity
    )
    package_path = _write_immutable_json(root / "package-baseline.json", baseline)
    state = LocalDecisionState(
        experiment_id="rtx5050-local-decision",
        started_utc=timestamp,
        started_monotonic=monotonic,
        deadline_monotonic=monotonic + DECISION_WINDOW_SECONDS,
        decision_window_seconds=DECISION_WINDOW_SECONDS,
        boot_identity=boot,
        input_evidence_sha256=_sha256_file(input_path),
        base_model_provenance_sha256=_sha256_file(base_path),
        torch_identity_sha256=_sha256_file(torch_path),
        decision_root_path_sha256=_path_identity_sha256(root),
        package_baseline_sha256=_sha256_file(package_path),
        clock_genesis_sha256=_sha256_file(root / "decision-clock.json"),
        repo_root_path_sha256=repo_root_path_sha256,
    )
    state_path = _write_immutable_json(root / "decision-state.json", state.as_json_dict())
    _append_stage(
        root,
        stage="preflight",
        timestamp_utc=completed_timestamp,
        monotonic=completed_monotonic,
        artifact=state_path,
    )
    return state


def _read_state_unchecked(root: Path) -> LocalDecisionState:
    root = Path(root)
    if root.is_symlink() or _is_reparse_point(root):
        raise RuntimeError("local decision root must not be a symlink or reparse point")
    payload = _read_json(root / "decision-state.json")
    try:
        state = LocalDecisionState(**payload)
    except (TypeError, ValueError) as exc:
        raise RuntimeError("immutable local-decision state is invalid") from exc
    actual_root_hash = _path_identity_sha256(root)
    if actual_root_hash != state.decision_root_path_sha256:
        raise RuntimeError("local decision output root drifted")
    artifacts = (
        ("input-evidence.json", state.input_evidence_sha256),
        ("base-model-provenance.json", state.base_model_provenance_sha256),
        ("environment-preflight.json", state.torch_identity_sha256),
        ("package-baseline.json", state.package_baseline_sha256),
        ("decision-clock.json", state.clock_genesis_sha256),
    )
    for relative, expected in artifacts:
        if _sha256_file(root / relative) != expected:
            raise RuntimeError(f"immutable preflight artifact drifted: {relative}")
    ledger = _ledger_entries(root)
    if not ledger or ledger[0]["stage"] != "preflight":
        raise RuntimeError("local decision ledger lacks its preflight genesis")
    stage_indexes = [_STAGE_ORDER.index(str(row["stage"])) for row in ledger]
    if stage_indexes != sorted(stage_indexes):
        raise RuntimeError("local decision stages are reordered")
    previous_monotonic = state.started_monotonic
    previous_utc = _parse_utc(state.started_utc)
    for row in ledger:
        monotonic = float(row["monotonic_seconds"])
        timestamp = _parse_utc(str(row["timestamp_utc"]))
        if monotonic < previous_monotonic or monotonic > state.deadline_monotonic:
            raise RuntimeError("stage ledger clock is outside the immutable decision window")
        if timestamp < previous_utc:
            raise RuntimeError("stage ledger UTC clock moved backwards")
        previous_monotonic = monotonic
        previous_utc = timestamp
    return state


def load_decision_state(
    decision_root: Path,
    *,
    now_utc: str | None = None,
    now_monotonic: float | None = None,
    boot_identity: str | None = None,
) -> LocalDecisionState:
    state = _read_state_unchecked(decision_root)
    timestamp = _utc_now() if now_utc is None else now_utc
    monotonic = time.monotonic() if now_monotonic is None else float(now_monotonic)
    boot = _boot_identity() if boot_identity is None else boot_identity
    if boot != state.boot_identity:
        raise RuntimeError("OS boot identity changed during the local decision")
    if monotonic < state.started_monotonic:
        raise RuntimeError("monotonic clock moved backwards")
    if _parse_utc(timestamp) < _parse_utc(state.started_utc):
        raise RuntimeError("UTC clock moved backwards")
    if monotonic > state.deadline_monotonic:
        raise TimeoutError("immutable two-hour decision window expired")
    return state


def _load_state_for_terminal_evidence(
    decision_root: Path,
    *,
    now_utc: str,
    now_monotonic: float,
    boot_identity: str | None,
    allow_expired: bool,
) -> tuple[LocalDecisionState, float]:
    state = _read_state_unchecked(decision_root)
    boot = _boot_identity() if boot_identity is None else boot_identity
    if boot != state.boot_identity:
        raise RuntimeError("OS boot identity changed during the local decision")
    if now_monotonic < state.started_monotonic:
        raise RuntimeError("monotonic clock moved backwards")
    if _parse_utc(now_utc) < _parse_utc(state.started_utc):
        raise RuntimeError("UTC clock moved backwards")
    if now_monotonic > state.deadline_monotonic and not allow_expired:
        raise TimeoutError("immutable two-hour decision window expired")
    return state, min(now_monotonic, state.deadline_monotonic)


def validate_local_input_paths(
    *,
    repo_root: Path,
    train_path: Path,
    val_path: Path,
    downstream_contract_path: Path,
    decision_root: Path,
) -> dict[str, Path]:
    """Authorize every local path lexically before any data file is opened."""

    root = _lexical_absolute(repo_root)
    expected = {
        "train": root / TRAIN_RELATIVE_PATH,
        "validation": root / VAL_RELATIVE_PATH,
        "contract": root / DOWNSTREAM_CONTRACT_RELATIVE_PATH,
        "decision_root": root / DECISION_ROOT_RELATIVE_PATH,
    }
    supplied = {
        "train": Path(train_path),
        "validation": Path(val_path),
        "contract": Path(downstream_contract_path),
        "decision_root": Path(decision_root),
    }
    messages = {
        "train": "train input is not the canonical training path",
        "validation": "validation input is not the canonical validation path",
        "contract": "downstream contract is not the canonical Phase 39 authority",
        "decision_root": "decision root is not the fixed Phase 40 evidence root",
    }
    for name in expected:
        raw = os.fspath(supplied[name]).replace("\\", "/")
        if ".." in supplied[name].parts or "/./" in f"/{raw}/":
            raise ValueError(f"{messages[name]}; path aliases are forbidden")
        if not _same_path(supplied[name], expected[name]):
            raise ValueError(messages[name])
    for name in ("train", "validation", "contract"):
        candidate = expected[name]
        if candidate.exists() and _is_reparse_point(candidate):
            raise ValueError(f"{messages[name]}; links and reparse points are forbidden")
    if root.exists() and _is_reparse_point(root):
        raise ValueError("repository root must not be a link or reparse point")
    return {name: _lexical_absolute(value) for name, value in expected.items()}


def _is_reparse_point(path: Path) -> bool:
    try:
        stat_result = os.lstat(path)
    except FileNotFoundError:
        return False
    attributes = getattr(stat_result, "st_file_attributes", 0)
    reparse_flag = getattr(stat_result, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(attributes & reparse_flag) or Path(path).is_symlink()


def _path_chain(path: Path) -> tuple[Path, ...]:
    current = _lexical_absolute(path)
    chain = [current]
    while current.parent != current:
        current = current.parent
        chain.append(current)
    return tuple(reversed(chain))


def validate_external_snapshot_identity(
    snapshot_path: Path,
    download_manifest_path: Path,
    *,
    expected_snapshot_path: Path = EXTERNAL_QWEN_SNAPSHOT,
    reparse_checker: Callable[[Path], bool] = _is_reparse_point,
) -> dict[str, object]:
    snapshot = _lexical_absolute(snapshot_path)
    expected = _lexical_absolute(expected_snapshot_path)
    if not _same_path(snapshot, expected):
        raise ValueError("external Qwen snapshot path is not the exact approved D: snapshot")
    if not snapshot.is_dir():
        raise FileNotFoundError("external Qwen snapshot is missing")
    for component in _path_chain(snapshot):
        if component.exists() and reparse_checker(component):
            raise ValueError("external Qwen snapshot path contains a reparse point")
    inventory_list: list[Path] = []
    for current_raw, directory_names, file_names in os.walk(snapshot, topdown=True):
        current = Path(current_raw)
        if reparse_checker(current):
            raise ValueError("external Qwen snapshot inventory contains a reparse point")
        for name in tuple(directory_names):
            directory = current / name
            if reparse_checker(directory):
                raise ValueError("external Qwen snapshot inventory contains a reparse point")
        for name in file_names:
            path = current / name
            if reparse_checker(path):
                raise ValueError("external Qwen snapshot inventory contains a reparse point")
            if path.is_file():
                inventory_list.append(path)
    inventory = tuple(sorted(inventory_list))

    manifest = _read_json_allow_absolute(download_manifest_path)
    models = manifest.get("models")
    if not isinstance(models, list):
        raise RuntimeError("download manifest lacks its models array")
    matches = [
        item
        for item in models
        if isinstance(item, dict)
        and item.get("candidate_id") == "qwen3-4b-instruct-2507"
    ]
    if len(matches) != 1:
        raise RuntimeError("download manifest must bind exactly one Qwen candidate")
    entry = matches[0]
    if entry.get("repo_id") != QWEN_MODEL_ID:
        raise RuntimeError("download manifest Qwen repository identity drifted")
    local_path = entry.get("local_path")
    if not isinstance(local_path, str) or not _same_path(Path(local_path), snapshot):
        raise RuntimeError("download manifest Qwen local path drifted")
    declared_size = entry.get("size_bytes")
    if not isinstance(declared_size, int) or isinstance(declared_size, bool) or declared_size <= 0:
        raise RuntimeError("download manifest Qwen size is invalid")
    inventory_size = sum(path.stat().st_size for path in inventory)
    if inventory_size != declared_size:
        raise RuntimeError("download manifest Qwen byte size drifted")

    index_path = snapshot / "model.safetensors.index.json"
    if not index_path.is_file():
        raise RuntimeError("Qwen snapshot lacks model.safetensors.index.json")
    index = _read_json(index_path)
    weight_map = index.get("weight_map")
    if not isinstance(weight_map, dict) or not weight_map:
        raise RuntimeError("Qwen weight index lacks its shard map")
    shard_names = tuple(sorted(set(weight_map.values())))
    if any(not isinstance(name, str) or PurePosixPath(name).name != name for name in shard_names):
        raise RuntimeError("Qwen weight index contains an unsafe shard name")
    critical = (
        "config.json",
        "tokenizer_config.json",
        "model.safetensors.index.json",
        *shard_names,
    )
    metadata_root = snapshot / ".cache/huggingface/download"
    for name in critical:
        if not (snapshot / name).is_file():
            raise RuntimeError(f"Qwen snapshot lacks load-critical file: {name}")
        metadata_path = metadata_root / f"{name}.metadata"
        if not metadata_path.is_file() or reparse_checker(metadata_path):
            raise RuntimeError(f"Qwen snapshot lacks safe revision metadata: {name}")
        with metadata_path.open("r", encoding="utf-8", errors="strict") as handle:
            revision = handle.readline().strip()
        if revision != QWEN_REVISION:
            raise RuntimeError(f"Qwen local-dir revision metadata drifted: {name}")
    return {
        "model_id": QWEN_MODEL_ID,
        "model_revision": QWEN_REVISION,
        "declared_snapshot_bytes": declared_size,
        "critical_metadata_files": list(critical),
        "offline": True,
        "local_files_only": True,
        "trust_remote_code": False,
    }


def _read_json_allow_absolute(path: Path) -> dict[str, object]:
    path = Path(path)
    if not path.is_file() or path.is_symlink():
        raise FileNotFoundError(f"missing safe JSON input: {path}")
    try:
        value = json.loads(
            path.read_text(encoding="utf-8", errors="strict"),
            object_pairs_hook=_reject_duplicate_keys,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, _DuplicateJsonKey) as exc:
        raise RuntimeError(f"invalid strict JSON input: {path.name}") from exc
    if not isinstance(value, dict):
        raise RuntimeError(f"JSON input root must be an object: {path.name}")
    return value


def parse_nvidia_smi_csv(raw: str) -> dict[str, object]:
    fields: dict[str, object] = {
        "device_vram_total_mib": None,
        "device_vram_used_mib": None,
        "device_vram_free_mib": None,
        "gpu_utilization_percent": None,
        "gpu_temperature_c": None,
        "gpu_power_w": None,
        "gpu_performance_state": None,
        "nvidia_raw": str(raw)[:2048],
    }
    try:
        values = next(csv.reader([raw], skipinitialspace=True))
        if len(values) != 7:
            return fields
        integers = [int(values[index].strip()) for index in range(5)]
        power = float(values[5].strip())
        pstate = values[6].strip()
        if not math.isfinite(power) or not pstate:
            return fields
    except (ValueError, StopIteration, csv.Error):
        return fields
    fields.update(
        {
            "device_vram_total_mib": integers[0],
            "device_vram_used_mib": integers[1],
            "device_vram_free_mib": integers[2],
            "gpu_utilization_percent": integers[3],
            "gpu_temperature_c": integers[4],
            "gpu_power_w": power,
            "gpu_performance_state": pstate,
        }
    )
    return fields


def null_telemetry_values(raw: str) -> dict[str, object]:
    values = {key: None for key in _TELEMETRY_VALUE_KEYS}
    values["nvidia_raw"] = str(raw)[:2048]
    return values


def append_telemetry_sample(path: Path, sample: Mapping[str, object]) -> Path:
    payload = dict(sample)
    required = {
        "schema_version",
        "sequence_id",
        "stage",
        "timestamp_utc",
        "monotonic_seconds",
        "terminal",
        "stop_reason",
        *_TELEMETRY_VALUE_KEYS,
    }
    if set(payload) != required:
        raise ValueError("telemetry sample has missing or extra fields")
    if payload["schema_version"] != TELEMETRY_SCHEMA_VERSION:
        raise ValueError("telemetry sample schema is unsupported")
    if not isinstance(payload["sequence_id"], int) or isinstance(payload["sequence_id"], bool):
        raise ValueError("telemetry sequence_id must be an integer")
    _parse_utc(str(payload["timestamp_utc"]))
    if payload["terminal"] is True and not payload["stop_reason"]:
        raise ValueError("terminal telemetry requires a literal stop reason")
    if payload["terminal"] is False and payload["stop_reason"] is not None:
        raise ValueError("non-terminal telemetry cannot carry a stop reason")
    return _append_jsonl(path, payload)


class TelemetryRecorder:
    def __init__(self, path: Path, *, stage: str) -> None:
        if stage not in {"lora", "qlora"}:
            raise ValueError("telemetry stage must be lora or qlora")
        self.path = Path(path)
        self.stage = stage
        self.sequence_id = 0
        self.finished = False

    def record(
        self,
        *,
        monotonic_seconds: float,
        timestamp_utc: str,
        values: Mapping[str, object],
    ) -> None:
        if self.finished:
            raise RuntimeError("telemetry recorder is already terminal")
        self._write(monotonic_seconds, timestamp_utc, values, False, None)

    def finish(
        self,
        *,
        monotonic_seconds: float,
        timestamp_utc: str,
        values: Mapping[str, object],
        stop_reason: str,
    ) -> None:
        if self.finished:
            raise RuntimeError("telemetry recorder is already terminal")
        self._write(monotonic_seconds, timestamp_utc, values, True, stop_reason)
        self.finished = True

    def _write(
        self,
        monotonic_seconds: float,
        timestamp_utc: str,
        values: Mapping[str, object],
        terminal: bool,
        stop_reason: str | None,
    ) -> None:
        if set(values) != _TELEMETRY_VALUE_KEYS:
            raise ValueError("telemetry values have missing or extra fields")
        append_telemetry_sample(
            self.path,
            {
                "schema_version": TELEMETRY_SCHEMA_VERSION,
                "sequence_id": self.sequence_id,
                "stage": self.stage,
                "timestamp_utc": timestamp_utc,
                "monotonic_seconds": float(monotonic_seconds),
                "terminal": terminal,
                "stop_reason": stop_reason,
                **dict(values),
            },
        )
        self.sequence_id += 1


def verify_telemetry(path: Path, *, expected_stage: str) -> list[dict[str, object]]:
    rows = _load_jsonl(path)
    for index, row in enumerate(rows):
        if row.get("sequence_id") != index or row.get("stage") != expected_stage:
            raise RuntimeError("telemetry sequence/stage drifted")
        if row.get("schema_version") != TELEMETRY_SCHEMA_VERSION:
            raise RuntimeError("telemetry schema drifted")
        if index and float(row["monotonic_seconds"]) < float(rows[index - 1]["monotonic_seconds"]):
            raise RuntimeError("telemetry monotonic clock moved backwards")
        if index and float(row["monotonic_seconds"]) - float(
            rows[index - 1]["monotonic_seconds"]
        ) > TELEMETRY_STALE_AFTER_SECONDS:
            raise RuntimeError("telemetry stream became stale")
    if any(row.get("terminal") is True for row in rows[:-1]):
        raise RuntimeError("telemetry continued after a terminal sample")
    if rows[-1].get("terminal") is not True or not rows[-1].get("stop_reason"):
        raise RuntimeError("telemetry lacks its terminal stop reason")
    return rows


def lora_should_extend(
    *,
    retained_steps: int,
    losses_finite: bool,
    telemetry_age_seconds: float,
    median_step_seconds: float | None,
    elapsed_seconds: float,
    remaining_decision_seconds: float,
) -> bool:
    if not 1 <= retained_steps < MEASURED_OPTIMIZER_STEPS:
        return False
    if losses_finite is not True or telemetry_age_seconds > TELEMETRY_STALE_AFTER_SECONDS:
        return False
    if median_step_seconds is None or not math.isfinite(median_step_seconds) or median_step_seconds <= 0:
        return False
    if elapsed_seconds < LORA_SOFT_LIMIT_SECONDS or elapsed_seconds >= LORA_HARD_LIMIT_SECONDS:
        return False
    estimated_remaining = (MEASURED_OPTIMIZER_STEPS - retained_steps) * median_step_seconds
    return (
        elapsed_seconds + estimated_remaining <= LORA_HARD_LIMIT_SECONDS
        and estimated_remaining <= remaining_decision_seconds
    )


def validate_qlora_events(path: Path) -> dict[str, object]:
    evidence = importlib.import_module("src.model_adaptation.phase40_evidence")
    events = evidence.load_run_events(
        Path(path),
        expected_run_id="rtx5050-qlora",
    )
    if not events or any(getattr(event.run_kind, "value", event.run_kind) != "probe" for event in events):
        raise RuntimeError("QLoRA event evidence must retain probe lineage")
    if getattr(events[0].event_kind, "value", events[0].event_kind) != "run_start":
        raise RuntimeError("QLoRA event evidence must begin with run_start")
    if getattr(events[-1].event_kind, "value", events[-1].event_kind) != "run_end":
        raise RuntimeError("QLoRA event evidence must end with run_end")
    if any(
        getattr(event.event_kind, "value", event.event_kind) == "failure"
        for event in events
    ):
        raise RuntimeError("successful QLoRA event evidence contains a failure")
    rows = [event.model_dump(mode="json") for event in events]
    optimizer = [
        row
        for row in rows
        if row.get("event_kind") == "step_timing"
    ]
    exact_error = "QLoRA requires exactly 5 warm-up plus 40 ordered measured optimizer steps"
    if len(optimizer) != WARMUP_OPTIMIZER_STEPS + MEASURED_OPTIMIZER_STEPS:
        raise RuntimeError(exact_error)
    expected_steps = list(range(1, 46))
    if [row.get("optimizer_step") for row in optimizer] != expected_steps:
        raise RuntimeError(exact_error)
    if [_event_value(row, "is_warmup") for row in optimizer] != (
        [True] * WARMUP_OPTIMIZER_STEPS + [False] * MEASURED_OPTIMIZER_STEPS
    ):
        raise RuntimeError(exact_error)
    retained = optimizer[WARMUP_OPTIMIZER_STEPS:]
    durations = [_event_value(row, "duration_seconds") for row in retained]
    if any(
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(float(value))
        or float(value) <= 0
        for value in durations
    ):
        raise RuntimeError(exact_error)
    evaluation = [row for row in rows if row.get("event_kind") == "evaluation"]
    checkpoint = [row for row in rows if row.get("event_kind") == "checkpoint"]
    if len(evaluation) != 1 or len(checkpoint) != 1:
        raise RuntimeError("QLoRA ETA requires one measured evaluation and checkpoint overhead")
    overheads = [
        _event_value(evaluation[0], "duration_seconds"),
        _event_value(checkpoint[0], "duration_seconds"),
    ]
    if any(not isinstance(value, (int, float)) or float(value) < 0 for value in overheads):
        raise RuntimeError("QLoRA overhead events are not measured")
    values = [_event_values(row) for row in retained]
    if any(not isinstance(value, dict) for value in values):
        raise RuntimeError("QLoRA optimizer events lack throughput values")
    retained_seconds = sum(float(value) for value in durations)
    examples = sum(int(value.get("examples") or 0) for value in values if isinstance(value, dict))
    tokens = sum(int(value.get("tokens") or 0) for value in values if isinstance(value, dict))
    if examples <= 0 or tokens <= 0:
        raise RuntimeError("QLoRA optimizer events lack measured examples/tokens")
    median = float(statistics.median(float(value) for value in durations))
    measured_overhead = sum(float(value) for value in overheads)
    return {
        "warmup_optimizer_steps": WARMUP_OPTIMIZER_STEPS,
        "retained_optimizer_steps": MEASURED_OPTIMIZER_STEPS,
        "planned_full_optimizer_steps": PLANNED_FULL_OPTIMIZER_STEPS,
        "steady_state_step_seconds_median": median,
        "measured_step_seconds": [float(value) for value in durations],
        "examples_per_second": examples / retained_seconds,
        "tokens_per_second": tokens / retained_seconds,
        "evaluation_overhead_seconds": float(overheads[0]),
        "checkpoint_overhead_seconds": float(overheads[1]),
        "measured_overhead_seconds": measured_overhead,
        "projected_local_runtime_seconds": (
            median * PLANNED_FULL_OPTIMIZER_STEPS + measured_overhead
        ),
        "projected_local_runtime_is_estimate": True,
        "optimizer_events_sha256": _sha256_file(path),
    }


def _event_values(row: Mapping[str, object]) -> dict[str, object]:
    values = row.get("trainer_values")
    return dict(values) if isinstance(values, dict) else {}


def _event_value(row: Mapping[str, object], name: str) -> object:
    if name in row:
        return row[name]
    return _event_values(row).get(name)


def validate_genuine_qlora_proof(proof: Mapping[str, object]) -> dict[str, object]:
    modes = importlib.import_module("src.model_adaptation.phase40_modes")
    try:
        typed = modes.QuantizationProof(**dict(proof))
    except (TypeError, ValueError) as exc:
        raise RuntimeError("incomplete genuine QLoRA quantization proof") from exc
    payload = asdict(typed)
    for key, value in tuple(payload.items()):
        payload[key] = getattr(value, "value", value)
    return payload


def discard_stage_runtime(stage_root: Path, *, run_id: str) -> dict[str, object]:
    callbacks = importlib.import_module("src.model_adaptation.phase40_callbacks")
    stage = Path(stage_root)
    runtime = stage / "runtime"
    if not runtime.is_dir() or runtime.is_symlink() or _is_reparse_point(runtime):
        raise RuntimeError("stage runtime must be one real directory before disposal")
    for current_raw, directory_names, file_names in os.walk(runtime, topdown=True):
        current = Path(current_raw)
        if _is_reparse_point(current):
            raise RuntimeError("stage runtime contains a link or reparse point")
        for name in tuple(directory_names):
            if _is_reparse_point(current / name):
                raise RuntimeError("stage runtime contains a link or reparse point")
        for name in file_names:
            if _is_reparse_point(current / name):
                raise RuntimeError("stage runtime contains a link or reparse point")
    receipt = callbacks.discard_probe_artifact(
        run_id=run_id,
        probe_root=stage,
        discarded_path_identity="runtime",
    )
    payload = receipt.as_json_dict()
    _write_immutable_json(stage / "discard-receipt.json", payload)
    callbacks.verify_probe_discard_receipt(receipt, probe_root=stage)
    return payload


def verify_stage_discard(stage_root: Path, receipt: Mapping[str, object]) -> None:
    callbacks = importlib.import_module("src.model_adaptation.phase40_callbacks")
    try:
        typed = callbacks.ProbeDiscardReceipt(**dict(receipt))
    except (TypeError, ValueError) as exc:
        raise RuntimeError("invalid stage discard receipt") from exc
    callbacks.verify_probe_discard_receipt(typed, probe_root=Path(stage_root))


def _require_prior_stages(root: Path, expected: Sequence[str]) -> None:
    actual = tuple(str(row["stage"]) for row in _ledger_entries(root))
    if actual != tuple(expected):
        raise RuntimeError(
            f"local decision stage order mismatch: expected {tuple(expected)}, got {actual}"
        )


def _write_qlora_prestart_failure(
    decision_root: Path,
    *,
    failure_stage: str,
    stop_reason: str,
) -> tuple[dict[str, object], Path]:
    root = Path(decision_root)
    qlora_root = root / "qlora"
    qlora_root.mkdir(parents=False, exist_ok=True)
    if qlora_root.is_symlink() or _is_reparse_point(qlora_root):
        raise RuntimeError("QLoRA evidence root must not be a link or reparse point")
    callbacks = importlib.import_module("src.model_adaptation.phase40_callbacks")
    modes = importlib.import_module("src.model_adaptation.phase40_modes")
    receipt = callbacks.create_no_artifact_receipt(
        run_id="rtx5050-qlora",
        probe_root=qlora_root,
        expected_path_identities=("runtime",),
    )
    stage_enum = callbacks.PrestartFailureStage(failure_stage)
    typed = callbacks.PrestartFailureEvidence(
        run_id="rtx5050-qlora",
        requested_identity=modes.ExperimentIdentity(
            modes.ModelFamily.QWEN,
            modes.AdaptationMode.QLORA,
            modes.RunKind.PROBE,
        ),
        failure_stage=stage_enum,
        environment_reference="environment-preflight.json",
        authority_reference="qlora/package-authority.json",
        no_artifact_receipt=receipt,
    )
    callbacks.verify_prestart_failure_evidence(typed, probe_root=qlora_root)
    receipt_payload = asdict(receipt)
    receipt_payload["expected_path_identities"] = list(receipt.expected_path_identities)
    payload = {
        "schema_version": "phase40-local-qlora-prestart-v1",
        "status": "prestart_failure",
        "stop_reason": stop_reason,
        "run_id": typed.run_id,
        "requested_identity": {
            "model_family": typed.requested_identity.model_family.value,
            "adaptation_mode": typed.requested_identity.adaptation_mode.value,
            "run_kind": typed.requested_identity.run_kind.value,
        },
        "failure_stage": typed.failure_stage.value,
        "environment_reference": typed.environment_reference,
        "environment_sha256": _sha256_file(root / "environment-preflight.json"),
        "authority_reference": typed.authority_reference,
        "no_artifact_receipt": receipt_payload,
        "eta": None,
        "quantization_proof": None,
        "optimizer_events": None,
    }
    path = _write_immutable_json(qlora_root / "run-evidence.json", payload)
    return payload, path


def _write_qlora_prestart_rejection(decision_root: Path) -> tuple[dict[str, object], Path]:
    return _write_qlora_prestart_failure(
        decision_root,
        failure_stage="package_authority",
        stop_reason="package_authority_rejected",
    )


def _load_and_verify_qlora_prestart_failure(
    decision_root: Path,
    link_payload: Mapping[str, object],
    *,
    expected_failure_stage: str,
    expected_stop_reason: str,
) -> dict[str, object]:
    root = Path(decision_root)
    relative = _portable_relative_path(link_payload.get("qlora_prestart_evidence"))
    if relative != "qlora/run-evidence.json":
        raise RuntimeError("package gate points at an unexpected QLoRA receipt")
    path = root / relative
    expected_hash = link_payload.get("qlora_prestart_evidence_sha256")
    if not isinstance(expected_hash, str) or _sha256_file(path) != expected_hash:
        raise RuntimeError("QLoRA pre-start evidence hash differs from its package gate")
    payload = _read_json(path)
    required = {
        "schema_version",
        "status",
        "stop_reason",
        "run_id",
        "requested_identity",
        "failure_stage",
        "environment_reference",
        "environment_sha256",
        "authority_reference",
        "no_artifact_receipt",
        "eta",
        "quantization_proof",
        "optimizer_events",
    }
    if set(payload) != required or (
        payload.get("schema_version") != "phase40-local-qlora-prestart-v1"
        or payload.get("status") != "prestart_failure"
        or payload.get("stop_reason") != expected_stop_reason
        or payload.get("run_id") != "rtx5050-qlora"
        or payload.get("requested_identity")
        != {
            "model_family": "qwen",
            "adaptation_mode": "qlora",
            "run_kind": "probe",
        }
        or payload.get("failure_stage") != expected_failure_stage
        or payload.get("environment_reference") != "environment-preflight.json"
        or payload.get("authority_reference") != "qlora/package-authority.json"
        or any(payload.get(key) is not None for key in ("eta", "quantization_proof", "optimizer_events"))
    ):
        raise RuntimeError("QLoRA pre-start failure evidence is invalid")
    if payload.get("environment_sha256") != _sha256_file(
        root / "environment-preflight.json"
    ):
        raise RuntimeError("QLoRA pre-start environment reference drifted")
    receipt_payload = payload.get("no_artifact_receipt")
    if not isinstance(receipt_payload, dict):
        raise RuntimeError("QLoRA pre-start receipt is missing")
    identities = receipt_payload.get("expected_path_identities")
    if not isinstance(identities, list):
        raise RuntimeError("QLoRA pre-start receipt identities are invalid")
    callbacks = importlib.import_module("src.model_adaptation.phase40_callbacks")
    receipt = callbacks.NoArtifactReceipt(
        **{
            **receipt_payload,
            "expected_path_identities": tuple(identities),
        }
    )
    modes = importlib.import_module("src.model_adaptation.phase40_modes")
    typed = callbacks.PrestartFailureEvidence(
        run_id="rtx5050-qlora",
        requested_identity=modes.ExperimentIdentity(
            modes.ModelFamily.QWEN,
            modes.AdaptationMode.QLORA,
            modes.RunKind.PROBE,
        ),
        failure_stage=callbacks.PrestartFailureStage(expected_failure_stage),
        environment_reference="environment-preflight.json",
        authority_reference="qlora/package-authority.json",
        no_artifact_receipt=receipt,
    )
    callbacks.verify_prestart_failure_evidence(typed, probe_root=root / "qlora")
    forbidden = (
        "telemetry.jsonl",
        "optimizer-events.jsonl",
        "quantization-proof.json",
        "outcome.json",
    )
    if any((root / "qlora" / name).exists() for name in forbidden):
        raise RuntimeError("QLoRA pre-start branch contains fabricated runtime evidence")
    return payload


def _load_and_verify_qlora_prestart_rejection(
    decision_root: Path, authority: Mapping[str, object]
) -> dict[str, object]:
    if authority.get("approved") is not False:
        raise RuntimeError("QLoRA pre-start rejection requires rejected package authority")
    return _load_and_verify_qlora_prestart_failure(
        decision_root,
        authority,
        expected_failure_stage="package_authority",
        expected_stop_reason="package_authority_rejected",
    )


def record_package_authority(
    decision_root: Path,
    decision: str,
    *,
    now_utc: str | None = None,
    now_monotonic: float | None = None,
    boot_identity: str | None = None,
) -> dict[str, object]:
    root = Path(decision_root)
    timestamp = _utc_now() if now_utc is None else now_utc
    monotonic = time.monotonic() if now_monotonic is None else float(now_monotonic)
    load_decision_state(
        root,
        now_utc=timestamp,
        now_monotonic=monotonic,
        boot_identity=boot_identity,
    )
    if (root / "package-authority.json").exists():
        raise FileExistsError("bitsandbytes authority is already recorded")
    _require_prior_stages(root, ("preflight", "lora"))
    if decision == APPROVE_AUTHORITY:
        approved = True
        reason = None
        prestart_path = None
    elif decision.startswith(REJECT_AUTHORITY_PREFIX):
        approved = False
        reason = decision.removeprefix(REJECT_AUTHORITY_PREFIX).strip()
        if not reason or len(reason) > 500 or any(character in reason for character in "\r\n\x00"):
            raise ValueError("package rejection reason must be one sanitized line")
        if _sanitize_log_text(reason) != reason:
            raise ValueError("package rejection reason must not retain an absolute path")
        _, prestart_path = _write_qlora_prestart_rejection(root)
    else:
        raise ValueError(
            "authority must be exactly 'approve bitsandbytes 0.50.1' or the exact reject form"
        )
    payload = {
        "schema_version": AUTHORITY_SCHEMA_VERSION,
        "package": "bitsandbytes",
        "version": BITSANDBYTES_VERSION,
        "approved": approved,
        "rejection_reason": reason,
        "decision_text": decision,
        "recorded_utc": timestamp,
        "recorded_monotonic": monotonic,
        "qlora_prestart_evidence": (
            None if prestart_path is None else "qlora/run-evidence.json"
        ),
        "qlora_prestart_evidence_sha256": (
            None if prestart_path is None else _sha256_file(prestart_path)
        ),
    }
    path = _write_immutable_json(root / "package-authority.json", payload)
    qlora_root = root / "qlora"
    qlora_root.mkdir(parents=False, exist_ok=True)
    _write_immutable_json(qlora_root / "package-authority.json", payload)
    _append_stage(
        root,
        stage="record-authority",
        timestamp_utc=timestamp,
        monotonic=monotonic,
        artifact=path,
    )
    return payload


def verify_package_runtime(
    decision_root: Path,
    *,
    bitsandbytes_identity: Mapping[str, object],
    torch_identity: Mapping[str, object],
    now_utc: str | None = None,
    now_monotonic: float | None = None,
    boot_identity: str | None = None,
) -> dict[str, object]:
    root = Path(decision_root)
    timestamp = _utc_now() if now_utc is None else now_utc
    monotonic = time.monotonic() if now_monotonic is None else float(now_monotonic)
    load_decision_state(
        root,
        now_utc=timestamp,
        now_monotonic=monotonic,
        boot_identity=boot_identity,
    )
    _require_prior_stages(root, ("preflight", "lora", "record-authority"))
    authority = _read_json(root / "package-authority.json")
    if authority.get("approved") is not True:
        raise RuntimeError("bitsandbytes was rejected; package verification is forbidden")
    preflight_torch = _read_json(root / "environment-preflight.json")
    failure_reason: str | None = None
    if dict(torch_identity) != preflight_torch:
        failure_reason = "Torch identity changed during bitsandbytes installation"
    elif bitsandbytes_identity.get("version") != BITSANDBYTES_VERSION:
        failure_reason = "installed bitsandbytes version is not exactly 0.50.1"
    elif bitsandbytes_identity.get("cuda_kernel_available") is not True:
        failure_reason = "bitsandbytes CUDA kernel capability proof failed"
    prestart_path: Path | None = None
    if failure_reason is not None:
        _, prestart_path = _write_qlora_prestart_failure(
            root,
            failure_stage="capability_preflight",
            stop_reason="package_runtime_verification_failed",
        )
    payload = {
        "schema_version": PACKAGE_SCHEMA_VERSION,
        "status": "verified" if failure_reason is None else "failed",
        "bitsandbytes": dict(bitsandbytes_identity),
        "torch": dict(torch_identity),
        "torch_unchanged": dict(torch_identity) == preflight_torch,
        "failure_reason": failure_reason,
        "verified_utc": timestamp,
        "verified_monotonic": monotonic,
        "qlora_prestart_evidence": (
            None if prestart_path is None else "qlora/run-evidence.json"
        ),
        "qlora_prestart_evidence_sha256": (
            None if prestart_path is None else _sha256_file(prestart_path)
        ),
    }
    path = _write_immutable_json(root / "package-runtime.json", payload)
    _write_immutable_json(root / "qlora/package-runtime.json", payload)
    _append_stage(
        root,
        stage="verify-package",
        timestamp_utc=timestamp,
        monotonic=monotonic,
        artifact=path,
    )
    if failure_reason is not None:
        raise RuntimeError(failure_reason)
    return payload


def write_stage_outcome(
    decision_root: Path,
    *,
    stage: str,
    outcome: Mapping[str, object],
    now_utc: str | None = None,
    now_monotonic: float | None = None,
    boot_identity: str | None = None,
) -> dict[str, object]:
    if stage not in {"lora", "qlora"}:
        raise ValueError("training outcome stage must be lora or qlora")
    root = Path(decision_root)
    timestamp = _utc_now() if now_utc is None else now_utc
    monotonic = time.monotonic() if now_monotonic is None else float(now_monotonic)
    payload = dict(outcome)
    state, ledger_monotonic = _load_state_for_terminal_evidence(
        root,
        now_utc=timestamp,
        now_monotonic=monotonic,
        boot_identity=boot_identity,
        allow_expired=payload.get("stop_reason") == "global_deadline",
    )
    if stage == "lora":
        _require_prior_stages(root, ("preflight",))
    else:
        _require_prior_stages(
            root,
            ("preflight", "lora", "record-authority", "verify-package"),
        )
    required_common = {"status", "stop_reason", "telemetry", "discard_receipt"}
    if not required_common.issubset(payload):
        raise ValueError("training outcome lacks terminal evidence")
    if payload["status"] not in {"measured", "oom", "timeout", "interrupted", "error"}:
        raise ValueError("training outcome has an unsupported status")
    if not isinstance(payload["stop_reason"], str) or not payload["stop_reason"]:
        raise ValueError("training outcome requires a literal stop reason")
    telemetry_rel = _portable_relative_path(payload["telemetry"])
    telemetry_path = root / telemetry_rel
    telemetry = verify_telemetry(telemetry_path, expected_stage=stage)
    if telemetry[-1].get("stop_reason") != payload["stop_reason"]:
        raise RuntimeError("training outcome stop reason differs from terminal telemetry")
    receipt = payload["discard_receipt"]
    if not isinstance(receipt, Mapping):
        raise ValueError("training outcome discard receipt must be an object")
    verify_stage_discard(root / stage, receipt)
    enriched: dict[str, object] = {
        "schema_version": OUTCOME_SCHEMA_VERSION,
        **payload,
        "telemetry": telemetry_rel,
        "telemetry_sha256": _sha256_file(telemetry_path),
        "terminal_telemetry_sequence": telemetry[-1]["sequence_id"],
        "completed_utc": timestamp,
        "completed_monotonic": ledger_monotonic,
        "evidence_sealed_monotonic": monotonic,
        "post_deadline_sealing_seconds": max(
            0.0, monotonic - state.deadline_monotonic
        ),
    }
    if "optimizer_events" in payload:
        events_rel = _portable_relative_path(payload["optimizer_events"])
        expected_prefix = f"{stage}/"
        if not events_rel.startswith(expected_prefix):
            raise ValueError("optimizer event evidence belongs to a different stage")
        event_path = root / events_rel
        partial_summary = _partial_optimizer_summary(
            event_path,
            run_id=f"rtx5050-{stage}",
        )
        supplied_partial = payload.get("partial_event_summary")
        if supplied_partial is not None and supplied_partial != partial_summary:
            raise RuntimeError("partial optimizer summary differs from raw events")
        supplied_hash = payload.get("optimizer_events_sha256")
        if supplied_hash is not None and supplied_hash != _sha256_file(event_path):
            raise RuntimeError("optimizer event hash differs from raw events")
        enriched.update(
            {
                "optimizer_events": events_rel,
                "optimizer_events_sha256": _sha256_file(event_path),
                "partial_event_summary": partial_summary,
            }
        )
    if stage == "qlora" and payload["status"] == "measured":
        events_rel = _portable_relative_path(payload.get("optimizer_events"))
        proof_rel = _portable_relative_path(payload.get("quantization_proof"))
        event_summary = validate_qlora_events(root / events_rel)
        proof = validate_genuine_qlora_proof(_read_json(root / proof_rel))
        enriched.update(
            {
                "optimizer_events": events_rel,
                "quantization_proof": proof_rel,
                "quantization_proof_sha256": _sha256_file(root / proof_rel),
                "measurement": event_summary,
                "proof": proof,
            }
        )
    elif stage == "qlora" and "quantization_proof" in payload:
        proof_rel = _portable_relative_path(payload["quantization_proof"])
        proof = validate_genuine_qlora_proof(_read_json(root / proof_rel))
        enriched.update(
            {
                "quantization_proof": proof_rel,
                "quantization_proof_sha256": _sha256_file(root / proof_rel),
                "proof": proof,
            }
        )
    path = _write_immutable_json(root / stage / "outcome.json", enriched)
    if stage == "qlora":
        _write_immutable_json(root / stage / "run-evidence.json", enriched)
    _append_stage(
        root,
        stage=stage,
        timestamp_utc=timestamp,
        monotonic=ledger_monotonic,
        artifact=path,
    )
    return enriched


def _portable_relative_path(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError("evidence reference must be a non-empty relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or path.as_posix() != value:
        raise ValueError("evidence reference must be a normalized relative path")
    if any(":" in part for part in path.parts):
        raise ValueError("evidence reference contains an unsafe path component")
    return value


def finalize_local_decision(
    decision_root: Path,
    *,
    now_utc: str | None = None,
    now_monotonic: float | None = None,
    boot_identity: str | None = None,
) -> dict[str, object]:
    root = Path(decision_root)
    timestamp = _utc_now() if now_utc is None else now_utc
    monotonic = time.monotonic() if now_monotonic is None else float(now_monotonic)
    try:
        state = load_decision_state(
            root,
            now_utc=timestamp,
            now_monotonic=monotonic,
            boot_identity=boot_identity,
        )
        ledger_monotonic = monotonic
    except TimeoutError:
        terminal_candidates = (
            root / "qlora/outcome.json",
            root / "lora/outcome.json",
        )
        terminal = next(
            (_read_json(path) for path in terminal_candidates if path.is_file()),
            None,
        )
        if terminal is None or terminal.get("stop_reason") != "global_deadline":
            raise
        state, ledger_monotonic = _load_state_for_terminal_evidence(
            root,
            now_utc=timestamp,
            now_monotonic=monotonic,
            boot_identity=boot_identity,
            allow_expired=True,
        )
    stages = tuple(str(row["stage"]) for row in _ledger_entries(root))
    authority = _read_json(root / "package-authority.json")
    approved = authority.get("approved") is True
    package_runtime = (
        _read_json(root / "package-runtime.json")
        if (root / "package-runtime.json").is_file()
        else None
    )
    package_failed = (
        approved
        and isinstance(package_runtime, dict)
        and package_runtime.get("status") == "failed"
    )
    if not approved:
        expected = ("preflight", "lora", "record-authority")
    elif package_failed:
        expected = ("preflight", "lora", "record-authority", "verify-package")
    else:
        expected = (
            "preflight",
            "lora",
            "record-authority",
            "verify-package",
            "qlora",
        )
    if stages != expected:
        raise RuntimeError("local decision cannot finalize from incomplete or reordered stages")
    lora = _read_json(root / "lora/outcome.json")
    if not approved:
        qlora = _load_and_verify_qlora_prestart_rejection(root, authority)
    elif package_failed and isinstance(package_runtime, dict):
        qlora = _load_and_verify_qlora_prestart_failure(
            root,
            package_runtime,
            expected_failure_stage="capability_preflight",
            expected_stop_reason="package_runtime_verification_failed",
        )
    else:
        qlora = _read_json(root / "qlora/outcome.json")
    recommendation = (
        "local_full_qlora_candidate"
        if qlora.get("status") == "measured"
        else "colab_fallback"
    )
    # Seal the ledger's final stage before hashing it into the manifest.
    marker = _write_immutable_json(
        root / "finalize-marker.json",
        {
            "schema_version": "phase40-local-finalize-marker-v1",
            "completed_utc": timestamp,
            "completed_monotonic": ledger_monotonic,
            "evidence_sealed_monotonic": monotonic,
        },
    )
    _append_stage(
        root,
        stage="finalize",
        timestamp_utc=timestamp,
        monotonic=ledger_monotonic,
        artifact=marker,
    )
    artifact_paths: list[Path] = []
    for current_raw, directory_names, file_names in os.walk(root, topdown=True):
        current = Path(current_raw)
        if _is_reparse_point(current):
            raise RuntimeError("local decision evidence contains a link or reparse point")
        for name in tuple(directory_names):
            directory = current / name
            if _is_reparse_point(directory):
                raise RuntimeError("local decision evidence contains a link or reparse point")
        for name in file_names:
            path = current / name
            if _is_reparse_point(path):
                raise RuntimeError("local decision evidence contains a link or reparse point")
            if path.is_file() and path.name != "decision-manifest.json":
                artifact_paths.append(path)
    hashes = {
        path.relative_to(root).as_posix(): _sha256_file(path)
        for path in sorted(artifact_paths)
    }
    manifest = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "experiment_id": state.experiment_id,
        "decision_window_seconds": state.decision_window_seconds,
        "elapsed_seconds": ledger_monotonic - state.started_monotonic,
        "evidence_sealed_monotonic": monotonic,
        "completed_utc": timestamp,
        "stages": [str(row["stage"]) for row in _ledger_entries(root)],
        "lora": lora,
        "qlora": qlora,
        "recommendation": recommendation,
        "artifact_sha256": hashes,
        "probe_artifacts_retained": False,
        "accuracy_claim_from_partial_lora": False,
    }
    _write_immutable_json(root / "decision-manifest.json", manifest)
    return manifest


def verify_local_decision(decision_root: Path) -> dict[str, object]:
    root = Path(decision_root)
    state = _read_state_unchecked(root)
    manifest = _read_json(root / "decision-manifest.json")
    if manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        raise RuntimeError("local decision manifest schema drifted")
    if (
        manifest.get("experiment_id") != state.experiment_id
        or manifest.get("decision_window_seconds") != state.decision_window_seconds
        or manifest.get("probe_artifacts_retained") is not False
        or manifest.get("accuracy_claim_from_partial_lora") is not False
    ):
        raise RuntimeError("local decision manifest changed its locked experiment contract")
    hashes = manifest.get("artifact_sha256")
    if not isinstance(hashes, dict) or not hashes:
        raise RuntimeError("local decision manifest lacks artifact hashes")
    actual_artifacts: set[str] = set()
    for current_raw, directory_names, file_names in os.walk(root, topdown=True):
        current = Path(current_raw)
        if _is_reparse_point(current):
            raise RuntimeError("local decision evidence contains a link or reparse point")
        for name in tuple(directory_names):
            if _is_reparse_point(current / name):
                raise RuntimeError("local decision evidence contains a link or reparse point")
        for name in file_names:
            path = current / name
            if _is_reparse_point(path):
                raise RuntimeError("local decision evidence contains a link or reparse point")
            if path.name != "decision-manifest.json":
                actual_artifacts.add(path.relative_to(root).as_posix())
    if set(hashes) != actual_artifacts:
        raise RuntimeError("local decision artifact inventory differs from its manifest")
    for relative, expected in hashes.items():
        normalized = _portable_relative_path(relative)
        path = root / normalized
        if not isinstance(expected, str) or _sha256_file(path) != expected:
            raise RuntimeError(f"local decision artifact hash drifted: {normalized}")
    ledger_stages = [str(row["stage"]) for row in _ledger_entries(root)]
    if manifest.get("stages") != ledger_stages or ledger_stages[-1:] != ["finalize"]:
        raise RuntimeError("local decision manifest stage sequence drifted")
    elapsed = manifest.get("elapsed_seconds")
    if (
        not isinstance(elapsed, (int, float))
        or isinstance(elapsed, bool)
        or not 0 <= float(elapsed) <= DECISION_WINDOW_SECONDS
    ):
        raise RuntimeError("local decision manifest exceeds its two-hour decision window")
    finalize_marker = _read_json(root / "finalize-marker.json")
    if (
        manifest.get("completed_utc") != finalize_marker.get("completed_utc")
        or manifest.get("evidence_sealed_monotonic")
        != finalize_marker.get("evidence_sealed_monotonic")
        or float(elapsed)
        != float(finalize_marker.get("completed_monotonic", -1))
        - state.started_monotonic
    ):
        raise RuntimeError("local decision manifest timing differs from its final ledger marker")
    authority = _read_json(root / "package-authority.json")
    if _read_json(root / "qlora/package-authority.json") != authority:
        raise RuntimeError("QLoRA package-authority copy drifted")
    package_runtime = (
        _read_json(root / "package-runtime.json")
        if (root / "package-runtime.json").is_file()
        else None
    )
    if package_runtime is not None and _read_json(
        root / "qlora/package-runtime.json"
    ) != package_runtime:
        raise RuntimeError("QLoRA package-runtime copy drifted")
    lora = _read_json(root / "lora/outcome.json")
    if manifest.get("lora") != lora:
        raise RuntimeError("manifest-embedded LoRA outcome drifted")
    lora_telemetry_path = root / _portable_relative_path(lora["telemetry"])
    verify_telemetry(lora_telemetry_path, expected_stage="lora")
    if lora.get("telemetry_sha256") != _sha256_file(lora_telemetry_path):
        raise RuntimeError("LoRA telemetry hash differs from its outcome")
    verify_stage_discard(root / "lora", lora["discard_receipt"])
    if "optimizer_events" in lora:
        lora_event_path = root / _portable_relative_path(lora["optimizer_events"])
        lora_partial = _partial_optimizer_summary(
            lora_event_path, run_id="rtx5050-lora"
        )
        if (
            lora.get("optimizer_events_sha256") != _sha256_file(lora_event_path)
            or lora.get("partial_event_summary") != lora_partial
        ):
            raise RuntimeError("LoRA partial optimizer evidence drifted")
    qlora = manifest.get("qlora")
    if qlora is not None:
        if not isinstance(qlora, dict):
            raise RuntimeError("local decision QLoRA outcome is invalid")
        if qlora.get("status") == "prestart_failure":
            if authority.get("approved") is False:
                persisted_prestart = _load_and_verify_qlora_prestart_rejection(
                    root, authority
                )
            elif isinstance(package_runtime, dict) and package_runtime.get("status") == "failed":
                persisted_prestart = _load_and_verify_qlora_prestart_failure(
                    root,
                    package_runtime,
                    expected_failure_stage="capability_preflight",
                    expected_stop_reason="package_runtime_verification_failed",
                )
            else:
                raise RuntimeError("QLoRA pre-start failure lacks its package gate")
            if persisted_prestart != qlora:
                raise RuntimeError("manifest-embedded QLoRA pre-start evidence drifted")
            if manifest.get("recommendation") != "colab_fallback":
                raise RuntimeError("QLoRA pre-start failure must route to the Colab fallback")
            return {
                "verified": True,
                "recommendation": manifest["recommendation"],
                "manifest_sha256": _sha256_file(root / "decision-manifest.json"),
            }
        persisted_qlora = _read_json(root / "qlora/outcome.json")
        if persisted_qlora != qlora:
            raise RuntimeError("manifest-embedded QLoRA outcome drifted")
        if _read_json(root / "qlora/run-evidence.json") != persisted_qlora:
            raise RuntimeError("QLoRA run-evidence alias differs from its outcome")
        qlora_telemetry_path = root / _portable_relative_path(qlora["telemetry"])
        verify_telemetry(qlora_telemetry_path, expected_stage="qlora")
        if qlora.get("telemetry_sha256") != _sha256_file(qlora_telemetry_path):
            raise RuntimeError("QLoRA telemetry hash differs from its outcome")
        verify_stage_discard(root / "qlora", qlora["discard_receipt"])
        if "optimizer_events" in qlora:
            partial_event_path = root / _portable_relative_path(
                qlora["optimizer_events"]
            )
            partial_summary = _partial_optimizer_summary(
                partial_event_path, run_id="rtx5050-qlora"
            )
            if (
                qlora.get("optimizer_events_sha256")
                != _sha256_file(partial_event_path)
                or qlora.get("partial_event_summary") != partial_summary
            ):
                raise RuntimeError("QLoRA partial optimizer evidence drifted")
        if "quantization_proof" in qlora:
            partial_proof_path = root / _portable_relative_path(
                qlora["quantization_proof"]
            )
            if qlora.get("quantization_proof_sha256") != _sha256_file(
                partial_proof_path
            ):
                raise RuntimeError("QLoRA quantization-proof hash differs from its outcome")
            validate_genuine_qlora_proof(_read_json(partial_proof_path))
        if qlora.get("status") == "measured":
            event_path = root / _portable_relative_path(qlora["optimizer_events"])
            event_summary = validate_qlora_events(event_path)
            recorded_measurement = qlora.get("measurement")
            if not isinstance(recorded_measurement, dict) or recorded_measurement != event_summary:
                raise RuntimeError("QLoRA ETA measurement differs from its raw events")
    expected_recommendation = (
        "local_full_qlora_candidate"
        if isinstance(qlora, dict) and qlora.get("status") == "measured"
        else "colab_fallback"
    )
    if manifest.get("recommendation") != expected_recommendation:
        raise RuntimeError("local decision recommendation differs from verified evidence")
    return {
        "verified": True,
        "recommendation": manifest["recommendation"],
        "manifest_sha256": _sha256_file(root / "decision-manifest.json"),
    }


def capture_torch_identity() -> dict[str, object]:
    torch = importlib.import_module("torch")
    module_path = Path(torch.__file__).resolve(strict=True)
    try:
        distribution = importlib.metadata.distribution("torch")
    except importlib.metadata.PackageNotFoundError as exc:
        raise RuntimeError("Torch distribution metadata is unavailable") from exc
    record_files = [
        item
        for item in (distribution.files or ())
        if PurePosixPath(str(item).replace("\\", "/")).name == "RECORD"
    ]
    if len(record_files) != 1:
        raise RuntimeError("Torch distribution RECORD identity is ambiguous")
    record_path = Path(distribution.locate_file(record_files[0]))
    if not record_path.is_file():
        raise RuntimeError("Torch distribution RECORD is missing")
    cuda_version = getattr(getattr(torch, "version", None), "cuda", None)
    return {
        "distribution": "torch",
        "version": str(torch.__version__),
        "cuda_version": None if cuda_version is None else str(cuda_version),
        "module_path_sha256": hashlib.sha256(
            os.path.normcase(os.fspath(module_path)).encode("utf-8")
        ).hexdigest(),
        "record_sha256": _sha256_file(record_path),
    }


def capture_bitsandbytes_identity() -> dict[str, object]:
    try:
        version = importlib.metadata.version("bitsandbytes")
    except importlib.metadata.PackageNotFoundError as exc:
        raise RuntimeError("bitsandbytes is not installed") from exc
    if version != BITSANDBYTES_VERSION:
        raise RuntimeError("installed bitsandbytes version is not exactly 0.50.1")
    bnb = importlib.import_module("bitsandbytes")
    torch = importlib.import_module("torch")
    linear4bit = getattr(getattr(bnb, "nn", None), "Linear4bit", None)
    capability = getattr(getattr(torch, "cuda", None), "get_device_capability", None)
    available = bool(
        isinstance(linear4bit, type)
        and getattr(torch.cuda, "is_available", lambda: False)()
        and callable(capability)
        and capability()
    )
    return {"version": version, "cuda_kernel_available": available}


def _split_evidence(contract: object) -> dict[str, object]:
    train = getattr(contract, "train_snapshot")
    validation = getattr(contract, "validation_snapshot")
    train_rows = len(getattr(train, "rows"))
    validation_rows = len(getattr(validation, "rows"))
    train_sha = getattr(train, "whole_file_sha256")
    validation_sha = getattr(validation, "whole_file_sha256")
    if (train_rows, train_sha) != (CANONICAL_TRAIN_ROWS, CANONICAL_TRAIN_SHA256):
        raise RuntimeError("canonical training identity differs from the frozen Phase 40 input")
    if (validation_rows, validation_sha) != (CANONICAL_VAL_ROWS, CANONICAL_VAL_SHA256):
        raise RuntimeError("canonical validation identity differs from the frozen Phase 40 input")
    return {
        "train": {
            "relative_path": TRAIN_RELATIVE_PATH.as_posix(),
            "rows": train_rows,
            "sha256": train_sha,
        },
        "validation": {
            "relative_path": VAL_RELATIVE_PATH.as_posix(),
            "rows": validation_rows,
            "sha256": validation_sha,
        },
    }


def _run_preflight(args: argparse.Namespace) -> dict[str, object]:
    required = (
        "repo_root",
        "train_split",
        "val_split",
        "downstream_contract",
        "base_model_path",
        "download_manifest",
    )
    if any(getattr(args, name, None) is None for name in required):
        raise ValueError(f"preflight requires: {', '.join(required)}")
    if getattr(args, "decision_window_seconds", DECISION_WINDOW_SECONDS) != DECISION_WINDOW_SECONDS:
        raise ValueError("decision window must be exactly 7,200 seconds")
    if getattr(args, "model_id", QWEN_MODEL_ID) != QWEN_MODEL_ID:
        raise ValueError("preflight model ID differs from the locked Qwen identity")
    if getattr(args, "model_revision", QWEN_REVISION) != QWEN_REVISION:
        raise ValueError("preflight model revision differs from the locked Qwen revision")
    paths = validate_local_input_paths(
        repo_root=args.repo_root,
        train_path=args.train_split,
        val_path=args.val_split,
        downstream_contract_path=args.downstream_contract,
        decision_root=args.decision_root,
    )
    if not _same_path(args.base_model_path, EXTERNAL_QWEN_SNAPSHOT):
        raise ValueError("preflight base-model path is not the exact approved D: snapshot")
    if not _same_path(args.download_manifest, EXTERNAL_DOWNLOAD_MANIFEST):
        raise ValueError("preflight download manifest is not the exact approved manifest")
    if _is_reparse_point(args.download_manifest):
        raise ValueError("preflight download manifest must not be a link or reparse point")
    clock_genesis = start_decision_clock(args.decision_root)
    os.environ.update(
        {
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "HF_DATASETS_OFFLINE": "1",
        }
    )
    try:
        validate_external_snapshot_identity(args.base_model_path, args.download_manifest)
        contract_module = importlib.import_module("src.model_adaptation.phase40_contract")
        contract = contract_module.preflight_phase40_inputs(
            paths["train"],
            paths["validation"],
            repo_root=paths["decision_root"].parents[4],
        )
        input_evidence = _split_evidence(contract)
        repo_root_path_sha256 = _path_identity_sha256(args.repo_root)
        input_evidence["repo_root_path_sha256"] = repo_root_path_sha256
        input_evidence["environment_baseline"] = {
            "captured_utc": _utc_now(),
            "resources": sample_parent_telemetry(None),
            "packages": {
                name: (
                    importlib.metadata.version(name)
                    if importlib.util.find_spec(name) is not None
                    else None
                )
                for name in ("transformers", "peft", "accelerate", "bitsandbytes")
            },
        }
        training = importlib.import_module("src.model_adaptation.training")
        provenance = training.build_qwen_base_model_provenance(
            _lexical_absolute(args.base_model_path),
            model_id=QWEN_MODEL_ID,
            model_revision=QWEN_REVISION,
            manifest_path=_lexical_absolute(args.decision_root)
            / "base-model-provenance.json",
        ).portable_manifest()
        validate_external_snapshot_identity(args.base_model_path, args.download_manifest)
        bitsandbytes_present = importlib.util.find_spec("bitsandbytes") is not None
        if bitsandbytes_present:
            raise RuntimeError("bitsandbytes must be absent before the LoRA-first experiment")
        state = initialize_decision_root(
            args.decision_root,
            input_evidence=input_evidence,
            base_model_provenance=provenance,
            torch_identity=capture_torch_identity(),
            package_baseline={"bitsandbytes_present": bitsandbytes_present},
            clock_genesis=clock_genesis,
            repo_root_path_sha256=repo_root_path_sha256,
        )
    except BaseException as exc:
        _write_immutable_json(
            Path(args.decision_root) / "preflight-failure.json",
            {
                "schema_version": "phase40-local-preflight-failure-v1",
                "error_type": type(exc).__name__,
                "error": _sanitize_log_text(str(exc)),
                "observed_utc": _utc_now(),
                "observed_monotonic": time.monotonic(),
                "clock_genesis_sha256": _sha256_file(
                    Path(args.decision_root) / "decision-clock.json"
                ),
            },
        )
        raise
    return {
        "status": "preflighted",
        "experiment_id": state.experiment_id,
        "decision_window_seconds": state.decision_window_seconds,
    }


def _system_memory_values(pid: int | None) -> dict[str, object]:
    try:
        psutil = importlib.import_module("psutil")
        memory = psutil.virtual_memory()
        rss = psutil.Process(pid).memory_info().rss if pid is not None else None
        return {
            "system_ram_total_bytes": int(memory.total),
            "system_ram_available_bytes": int(memory.available),
            "system_ram_used_bytes": int(memory.used),
            "process_rss_bytes": None if rss is None else int(rss),
        }
    except (ImportError, OSError):
        return {
            "system_ram_total_bytes": None,
            "system_ram_available_bytes": None,
            "system_ram_used_bytes": None,
            "process_rss_bytes": None,
        }


def sample_parent_telemetry(
    pid: int | None,
    *,
    child_events_path: Path | None = None,
) -> dict[str, object]:
    values = {
        **_system_memory_values(pid),
        "torch_allocated_bytes": None,
        "torch_reserved_bytes": None,
        "torch_peak_allocated_bytes": None,
        "torch_peak_reserved_bytes": None,
    }
    command = [
        "nvidia-smi",
        "--query-gpu=memory.total,memory.used,memory.free,utilization.gpu,temperature.gpu,power.draw,pstate",
        "--format=csv,noheader,nounits",
    ]
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=1,
            shell=False,
        )
        raw = completed.stdout.strip() if completed.returncode == 0 else completed.stderr.strip()
    except (OSError, subprocess.SubprocessError) as exc:
        raw = f"nvidia-smi unavailable: {type(exc).__name__}"
    values.update(parse_nvidia_smi_csv(raw))
    if child_events_path is not None:
        latest = _latest_complete_jsonl_row(child_events_path)
        if latest is not None:
            event_values = _event_values(latest)
            current_allocated = event_values.get("allocated_bytes")
            current_reserved = event_values.get("reserved_bytes")
            allocated = event_values.get("peak_allocated_bytes")
            reserved = event_values.get("peak_reserved_bytes")
            if isinstance(current_allocated, int) and not isinstance(current_allocated, bool):
                values["torch_allocated_bytes"] = current_allocated
            if isinstance(current_reserved, int) and not isinstance(current_reserved, bool):
                values["torch_reserved_bytes"] = current_reserved
            if isinstance(allocated, int) and not isinstance(allocated, bool):
                values["torch_peak_allocated_bytes"] = allocated
            if isinstance(reserved, int) and not isinstance(reserved, bool):
                values["torch_peak_reserved_bytes"] = reserved
    return values


def _latest_complete_jsonl_row(path: Path) -> dict[str, object] | None:
    path = Path(path)
    if not path.is_file() or path.is_symlink():
        return None
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if not data.endswith(b"\n"):
        data = data.rsplit(b"\n", 1)[0] + b"\n" if b"\n" in data else b""
    if not data:
        return None
    try:
        row = json.loads(data.rstrip(b"\n").rsplit(b"\n", 1)[-1].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    return row if isinstance(row, dict) else None


def _local_child_events_path(stage_root: Path, stage: str) -> Path:
    return (
        Path(stage_root)
        / "runtime"
        / "local-decision-work"
        / "qwen3-4b-instruct-2507"
        / "evidence"
        / f"rtx5050-{stage}"
        / "events.jsonl"
    )


def _live_lora_progress(path: Path) -> dict[str, object]:
    if not Path(path).is_file():
        return {
            "retained_steps": 0,
            "losses_finite": False,
            "median_step_seconds": None,
            "telemetry_age_seconds": math.inf,
        }
    try:
        rows = _load_jsonl(path)
    except (OSError, RuntimeError, UnicodeDecodeError):
        return {
            "retained_steps": 0,
            "losses_finite": False,
            "median_step_seconds": None,
            "telemetry_age_seconds": math.inf,
        }
    step_rows = [row for row in rows if row.get("event_kind") == "step_timing"]
    retained = [row for row in step_rows if _event_value(row, "is_warmup") is False]
    durations = [float(_event_value(row, "duration_seconds")) for row in retained]
    loss_values = [
        _event_values(row).get("loss")
        for row in rows
        if row.get("event_kind") == "train_log" and "loss" in _event_values(row)
    ]
    losses_finite = bool(loss_values) and all(
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
        for value in loss_values
    )
    return {
        "retained_steps": len(retained),
        "losses_finite": losses_finite,
        "median_step_seconds": (
            None if not durations else float(statistics.median(durations))
        ),
        "telemetry_age_seconds": max(0.0, time.time() - Path(path).stat().st_mtime),
    }


def _safe_child_runtime_file(path: Path, *, runtime_root: Path) -> Path:
    candidate = _lexical_absolute(path)
    runtime = _lexical_absolute(runtime_root)
    if not _same_path(candidate, path) or not candidate.is_file():
        raise RuntimeError("child evidence file is missing or path-normalized")
    try:
        candidate.relative_to(runtime)
    except ValueError as exc:
        raise RuntimeError("child evidence file escaped its disposable runtime") from exc
    for component in _path_chain(candidate):
        if component == runtime.parent:
            continue
        if component == runtime or runtime in component.parents:
            if component.exists() and _is_reparse_point(component):
                raise RuntimeError("child evidence traverses a link or reparse point")
    return candidate


def _partial_optimizer_summary(path: Path, *, run_id: str) -> dict[str, object]:
    evidence = importlib.import_module("src.model_adaptation.phase40_evidence")
    events = evidence.load_run_events(Path(path), expected_run_id=run_id)
    if any(getattr(event.run_kind, "value", event.run_kind) != "probe" for event in events):
        raise RuntimeError("partial optimizer events lost probe lineage")
    step_events = [
        event
        for event in events
        if getattr(event.event_kind, "value", event.event_kind) == "step_timing"
    ]
    retained = [
        event
        for event in step_events
        if event.trainer_values.get("is_warmup") is False
    ]
    durations = [
        float(event.trainer_values["duration_seconds"])
        for event in retained
        if isinstance(event.trainer_values.get("duration_seconds"), (int, float))
        and not isinstance(event.trainer_values.get("duration_seconds"), bool)
        and math.isfinite(float(event.trainer_values["duration_seconds"]))
        and float(event.trainer_values["duration_seconds"]) > 0
    ]
    losses = [
        event.trainer_values.get("loss")
        for event in events
        if getattr(event.event_kind, "value", event.event_kind) == "train_log"
        and "loss" in event.trainer_values
    ]
    return {
        "observed_optimizer_steps": len(step_events),
        "retained_optimizer_steps": len(retained),
        "losses_finite": bool(losses)
        and all(
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(float(value))
            for value in losses
        ),
        "measured_step_seconds": durations,
        "optimizer_events_sha256": _sha256_file(path),
        "terminal_event_kind": getattr(
            events[-1].event_kind, "value", events[-1].event_kind
        ),
    }


def _retain_child_events(
    *,
    stage_root: Path,
    runtime: Path,
    stage: str,
    result: Mapping[str, object],
) -> tuple[Path | None, dict[str, object] | None]:
    expected = _local_child_events_path(stage_root, stage)
    supplied = result.get("events_path")
    if supplied is not None and (
        not isinstance(supplied, str) or not _same_path(Path(supplied), expected)
    ):
        raise RuntimeError("child result referenced a non-canonical event path")
    if not expected.is_file():
        return None, None
    source = _safe_child_runtime_file(expected, runtime_root=runtime)
    retained = _write_immutable_bytes(
        stage_root / "optimizer-events.jsonl",
        source.read_bytes(),
    )
    return retained, _partial_optimizer_summary(
        retained,
        run_id=f"rtx5050-{stage}",
    )


def _retain_prestep_quantization_proof(
    *, stage_root: Path, runtime: Path, result: Mapping[str, object]
) -> tuple[Path | None, dict[str, object] | None]:
    source = runtime / "quantization-proof-prestep.json"
    result_proof = result.get("quantization_proof")
    if not source.is_file():
        if result_proof is not None:
            raise RuntimeError("child result claimed a quantization proof without its pre-step seal")
        return None, None
    safe_source = _safe_child_runtime_file(source, runtime_root=runtime)
    proof = _read_json(safe_source)
    if isinstance(result_proof, Mapping) and dict(result_proof) != proof:
        raise RuntimeError("child result quantization proof differs from its pre-step seal")
    retained = _write_immutable_json(stage_root / "quantization-proof.json", proof)
    return retained, proof


def _sanitize_log_text(text: str) -> str:
    result = str(text)
    result = re.sub(r"[A-Za-z]:[\\/][^\r\n\t ]+", "<absolute-path>", result)
    result = re.sub(r"/(?:[^\s/]+/)+[^\s]+", "<absolute-path>", result)
    return result[:1_000_000]


def _assign_kill_on_close_job(process: subprocess.Popen[str]) -> int | None:
    """Bind the sole Windows child to a kill-on-parent-close Job Object."""

    if os.name != "nt":
        return None
    process_handle = getattr(process, "_handle", None)
    if process_handle is None:  # Test doubles and non-CPython process wrappers.
        return None
    from ctypes import wintypes

    class _IoCounters(ctypes.Structure):
        _fields_ = [
            ("ReadOperationCount", ctypes.c_ulonglong),
            ("WriteOperationCount", ctypes.c_ulonglong),
            ("OtherOperationCount", ctypes.c_ulonglong),
            ("ReadTransferCount", ctypes.c_ulonglong),
            ("WriteTransferCount", ctypes.c_ulonglong),
            ("OtherTransferCount", ctypes.c_ulonglong),
        ]

    class _BasicLimit(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_longlong),
            ("PerJobUserTimeLimit", ctypes.c_longlong),
            ("LimitFlags", wintypes.DWORD),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", wintypes.DWORD),
            ("Affinity", ctypes.c_size_t),
            ("PriorityClass", wintypes.DWORD),
            ("SchedulingClass", wintypes.DWORD),
        ]

    class _ExtendedLimit(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", _BasicLimit),
            ("IoInfo", _IoCounters),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        ]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateJobObjectW.argtypes = (ctypes.c_void_p, wintypes.LPCWSTR)
    kernel32.CreateJobObjectW.restype = wintypes.HANDLE
    kernel32.SetInformationJobObject.argtypes = (
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
    )
    kernel32.SetInformationJobObject.restype = wintypes.BOOL
    kernel32.AssignProcessToJobObject.argtypes = (wintypes.HANDLE, wintypes.HANDLE)
    kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel32.CloseHandle.restype = wintypes.BOOL
    handle = kernel32.CreateJobObjectW(None, None)
    if not handle:
        raise OSError(ctypes.get_last_error(), "CreateJobObjectW failed")
    limits = _ExtendedLimit()
    limits.BasicLimitInformation.LimitFlags = 0x00002000
    try:
        if not kernel32.SetInformationJobObject(
            handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)
        ):
            raise OSError(ctypes.get_last_error(), "SetInformationJobObject failed")
        if not kernel32.AssignProcessToJobObject(handle, wintypes.HANDLE(process_handle)):
            raise OSError(ctypes.get_last_error(), "AssignProcessToJobObject failed")
    except BaseException:
        kernel32.CloseHandle(handle)
        raise
    return int(handle)


def _close_windows_handle(handle: int | None) -> None:
    if handle is None or os.name != "nt":
        return
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel32.CloseHandle.restype = wintypes.BOOL
    if not kernel32.CloseHandle(wintypes.HANDLE(handle)):
        raise OSError(ctypes.get_last_error(), "CloseHandle failed")


def _run_monitored_training_stage_impl(
    args: argparse.Namespace, *, stage: str
) -> dict[str, object]:
    root = Path(args.decision_root)
    state = load_decision_state(root)
    supplied_repo_hash = _path_identity_sha256(args.repo_root)
    if (
        state.repo_root_path_sha256 is not None
        and supplied_repo_hash != state.repo_root_path_sha256
    ):
        raise RuntimeError("repository root differs from the immutable preflight authority")
    if stage == "lora":
        _require_prior_stages(root, ("preflight",))
    else:
        _require_prior_stages(
            root, ("preflight", "lora", "record-authority", "verify-package")
        )
    stage_root = root / stage
    if stage_root.is_symlink() or _is_reparse_point(stage_root):
        raise FileExistsError(f"{stage} stage root is an unsafe link or reparse point")
    if stage_root.exists():
        allowed_existing = (
            stage == "qlora"
            and stage_root.is_dir()
            and {path.name for path in stage_root.iterdir()}
            == {"package-authority.json", "package-runtime.json"}
        )
        if not allowed_existing:
            raise FileExistsError(f"{stage} stage already exists")
    runtime = stage_root / "runtime"
    runtime.mkdir(parents=True, exist_ok=False)
    control = {
        "stage": stage,
        "train_split": os.fspath(_lexical_absolute(Path(args.repo_root) / TRAIN_RELATIVE_PATH)),
        "val_split": os.fspath(_lexical_absolute(Path(args.repo_root) / VAL_RELATIVE_PATH)),
        "repo_root": os.fspath(_lexical_absolute(args.repo_root)),
        "base_model_path": os.fspath(_lexical_absolute(EXTERNAL_QWEN_SNAPSHOT)),
        "stage_root": os.fspath(_lexical_absolute(stage_root)),
    }
    # Runtime control is intentionally disposable and may contain absolute paths.
    control_path = runtime / "child-control.json"
    control_path.write_text(json.dumps(control, sort_keys=True), encoding="utf-8")
    stdout_path = runtime / "child-stdout.log"
    stderr_path = runtime / "child-stderr.log"
    command = [
        sys.executable,
        "-m",
        "src.model_adaptation.phase40_local_experiment",
        "--child-control",
        os.fspath(control_path),
    ]
    environment = dict(os.environ)
    environment.update(
        {
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "HF_DATASETS_OFFLINE": "1",
        }
    )
    recorder = TelemetryRecorder(stage_root / "telemetry.jsonl", stage=stage)
    stop_reason = "error"
    process: subprocess.Popen[str] | None = None
    job_handle: int | None = None
    started = time.monotonic()
    latest_values = null_telemetry_values("not sampled")
    child_events_path = _local_child_events_path(stage_root, stage)
    lora_extension_decided = False

    def request_boundary_stop(
        reason: str, *, absolute_deadline: float | None = None
    ) -> None:
        nonlocal stop_reason, latest_values
        if process is None:
            return
        stop_reason = reason
        stop_path = runtime / "stop-request.json"
        if not stop_path.exists():
            stop_path.write_text('{"stop":true}\n', encoding="ascii")
        grace_deadline = time.monotonic() + 15.0
        if absolute_deadline is not None:
            grace_deadline = min(grace_deadline, absolute_deadline)
        while process.poll() is None and time.monotonic() < grace_deadline:
            time.sleep(min(TELEMETRY_INTERVAL_SECONDS, max(0.0, grace_deadline - time.monotonic())))
            if absolute_deadline is not None and time.monotonic() >= absolute_deadline:
                break
            latest_values = sample_parent_telemetry(
                process.pid, child_events_path=child_events_path
            )
            recorder.record(
                monotonic_seconds=time.monotonic(),
                timestamp_utc=_utc_now(),
                values=latest_values,
            )
        if process.poll() is None:
            process.terminate()
            terminate_deadline = time.monotonic() + 10.0
            if absolute_deadline is not None:
                terminate_deadline = min(terminate_deadline, absolute_deadline)
            while process.poll() is None and time.monotonic() < terminate_deadline:
                time.sleep(
                    min(
                        TELEMETRY_INTERVAL_SECONDS,
                        max(0.0, terminate_deadline - time.monotonic()),
                    )
                )
                if absolute_deadline is not None and time.monotonic() >= absolute_deadline:
                    break
                latest_values = sample_parent_telemetry(
                    process.pid, child_events_path=child_events_path
                )
                recorder.record(
                    monotonic_seconds=time.monotonic(),
                    timestamp_utc=_utc_now(),
                    values=latest_values,
                )
        if process.poll() is None:
            process.kill()
            wait_seconds = 5.0
            if absolute_deadline is not None:
                wait_seconds = max(0.1, min(wait_seconds, absolute_deadline - time.monotonic()))
            process.wait(timeout=wait_seconds)

    try:
        with stdout_path.open("w", encoding="utf-8") as stdout_handle, stderr_path.open(
            "w", encoding="utf-8"
        ) as stderr_handle:
            process = subprocess.Popen(
                command,
                stdout=stdout_handle,
                stderr=stderr_handle,
                text=True,
                shell=False,
                cwd=os.fspath(_lexical_absolute(args.repo_root)),
                env=environment,
            )
            job_handle = _assign_kill_on_close_job(process)
            while process.poll() is None:
                now = time.monotonic()
                elapsed = now - started
                latest_values = sample_parent_telemetry(
                    process.pid, child_events_path=child_events_path
                )
                recorder.record(
                    monotonic_seconds=now,
                    timestamp_utc=_utc_now(),
                    values=latest_values,
                )
                if (
                    stage == "lora"
                    and elapsed >= LORA_SOFT_LIMIT_SECONDS
                    and not lora_extension_decided
                ):
                    progress = _live_lora_progress(child_events_path)
                    may_extend = lora_should_extend(
                        retained_steps=int(progress["retained_steps"]),
                        losses_finite=bool(progress["losses_finite"]),
                        telemetry_age_seconds=float(progress["telemetry_age_seconds"]),
                        median_step_seconds=progress["median_step_seconds"],
                        elapsed_seconds=elapsed,
                        remaining_decision_seconds=max(
                            0.0, state.deadline_monotonic - now
                        ),
                    )
                    lora_extension_decided = True
                    if not may_extend:
                        request_boundary_stop("soft_timebox")
                        break
                stage_limit = (
                    LORA_HARD_LIMIT_SECONDS
                    if stage == "lora"
                    else DECISION_WINDOW_SECONDS
                )
                global_deadline = state.deadline_monotonic
                stage_deadline = started + stage_limit
                effective_deadline = min(global_deadline, stage_deadline)
                if effective_deadline - now <= 15.0:
                    request_boundary_stop(
                        "global_deadline" if global_deadline <= stage_deadline else "hard_timebox",
                        absolute_deadline=effective_deadline,
                    )
                    break
                time.sleep(TELEMETRY_INTERVAL_SECONDS)
            if process.returncode == 0 and stop_reason == "error":
                stop_reason = "evidence_target_reached"
            elif stop_reason == "error":
                stop_reason = "child_error"
    except KeyboardInterrupt:
        if process is not None and process.poll() is None:
            request_boundary_stop("parent_interrupted")
        else:
            stop_reason = "parent_interrupted"
    except BaseException:
        if process is not None and process.poll() is None:
            request_boundary_stop("parent_controller_error")
        else:
            stop_reason = "parent_controller_error"
        raise
    finally:
        try:
            try:
                latest_values = sample_parent_telemetry(
                    None if process is None else process.pid,
                    child_events_path=child_events_path,
                )
            except BaseException:
                latest_values = null_telemetry_values("terminal sample failed")
            recorder.finish(
                monotonic_seconds=time.monotonic(),
                timestamp_utc=_utc_now(),
                values=latest_values,
                stop_reason=stop_reason,
            )
        finally:
            _close_windows_handle(job_handle)

    result_path = runtime / "child-result.json"
    result = _read_json_allow_absolute(result_path) if result_path.is_file() else {}
    events_path, partial_event_summary = _retain_child_events(
        stage_root=stage_root,
        runtime=runtime,
        stage=stage,
        result=result,
    )
    proof_path, proof = _retain_prestep_quantization_proof(
        stage_root=stage_root,
        runtime=runtime,
        result=result,
    )
    raw_log_hashes: dict[str, str] = {}
    sanitized_log_hashes: dict[str, str] = {}
    for name, source in (("stdout", stdout_path), ("stderr", stderr_path)):
        content = source.read_text(encoding="utf-8", errors="replace") if source.exists() else ""
        if source.exists():
            raw_log_hashes[name] = _sha256_file(source)
        sanitized_path = stage_root / f"child-{name}.sanitized.log"
        sanitized_path.write_text(
            _sanitize_log_text(content), encoding="utf-8"
        )
        sanitized_log_hashes[name] = _sha256_file(sanitized_path)
    receipt = discard_stage_runtime(stage_root, run_id=f"rtx5050-{stage}")
    if process is not None and process.returncode == 0:
        status = "measured"
    elif "out of memory" in _sanitize_log_text(
        (stage_root / "child-stderr.sanitized.log").read_text(encoding="utf-8")
    ).casefold():
        status = "oom"
    elif stop_reason in {"soft_timebox", "hard_timebox", "global_deadline"}:
        status = "timeout"
    elif stop_reason == "parent_interrupted":
        status = "interrupted"
    else:
        status = "error"
    telemetry_rows = verify_telemetry(stage_root / "telemetry.jsonl", expected_stage=stage)
    resource_peaks = {
        key: max(
            (
                float(row[key])
                for row in telemetry_rows
                if isinstance(row.get(key), (int, float))
                and not isinstance(row.get(key), bool)
            ),
            default=None,
        )
        for key in (
            "system_ram_used_bytes",
            "process_rss_bytes",
            "torch_allocated_bytes",
            "torch_reserved_bytes",
            "torch_peak_allocated_bytes",
            "torch_peak_reserved_bytes",
            "device_vram_used_mib",
            "gpu_utilization_percent",
            "gpu_temperature_c",
            "gpu_power_w",
        )
    }
    outcome: dict[str, object] = {
        "status": status,
        "stop_reason": stop_reason,
        "telemetry": f"{stage}/telemetry.jsonl",
        "discard_receipt": receipt,
        "resource_peaks": resource_peaks,
        "raw_child_log_sha256": raw_log_hashes,
        "sanitized_child_log_sha256": sanitized_log_hashes,
    }
    if stage == "lora":
        retained_steps = (
            int(partial_event_summary["retained_optimizer_steps"])
            if partial_event_summary is not None
            else 0
        )
        losses_finite = (
            bool(partial_event_summary["losses_finite"])
            if partial_event_summary is not None
            else False
        )
        outcome.update(
            {
                "retained_optimizer_steps": retained_steps,
                "losses_finite": losses_finite,
            }
        )
        if events_path is not None and partial_event_summary is not None:
            outcome.update(
                {
                    "optimizer_events": "lora/optimizer-events.jsonl",
                    "optimizer_events_sha256": partial_event_summary[
                        "optimizer_events_sha256"
                    ],
                    "partial_event_summary": partial_event_summary,
                }
            )
    elif status == "measured":
        if events_path is None or proof_path is None or proof is None:
            raise RuntimeError("successful QLoRA child lacks its raw event/proof evidence")
        outcome.update(
            {
                "optimizer_events": "qlora/optimizer-events.jsonl",
                "quantization_proof": "qlora/quantization-proof.json",
            }
        )
    else:
        if events_path is not None and partial_event_summary is not None:
            outcome.update(
                {
                    "optimizer_events": "qlora/optimizer-events.jsonl",
                    "optimizer_events_sha256": partial_event_summary[
                        "optimizer_events_sha256"
                    ],
                    "partial_event_summary": partial_event_summary,
                }
            )
        if proof_path is not None and proof is not None:
            outcome["quantization_proof"] = "qlora/quantization-proof.json"
    return write_stage_outcome(root, stage=stage, outcome=outcome)


def run_monitored_training_stage(
    args: argparse.Namespace, *, stage: str
) -> dict[str, object]:
    """Run one child and guarantee bounded termination/runtime disposal on every exit."""

    root = Path(args.decision_root)
    stage_root = root / stage
    runtime = stage_root / "runtime"
    try:
        return _run_monitored_training_stage_impl(args, stage=stage)
    except BaseException as exc:
        if not stage_root.is_dir() or stage_root.is_symlink():
            raise
        partial_summary: dict[str, object] | None = None
        proof_path: Path | None = None
        if runtime.is_dir() and not runtime.is_symlink():
            result_path = runtime / "child-result.json"
            try:
                result = (
                    _read_json_allow_absolute(result_path)
                    if result_path.is_file()
                    else {}
                )
                _, partial_summary = _retain_child_events(
                    stage_root=stage_root,
                    runtime=runtime,
                    stage=stage,
                    result=result,
                )
                proof_path, _ = _retain_prestep_quantization_proof(
                    stage_root=stage_root,
                    runtime=runtime,
                    result=result,
                )
            except BaseException:
                partial_summary = None
                proof_path = None
            for name in ("stdout", "stderr"):
                source = runtime / f"child-{name}.log"
                if source.is_file() and not source.is_symlink():
                    _write_immutable_bytes(
                        stage_root / f"child-{name}.sanitized.log",
                        _sanitize_log_text(
                            source.read_text(encoding="utf-8", errors="replace")
                        ).encode("utf-8"),
                    )
            try:
                receipt = discard_stage_runtime(
                    stage_root, run_id=f"rtx5050-{stage}"
                )
            except BaseException:
                raise
        elif (stage_root / "discard-receipt.json").is_file():
            receipt = _read_json(stage_root / "discard-receipt.json")
        else:
            raise
        failure_payload = {
            "schema_version": "phase40-local-controller-failure-v1",
            "stage": stage,
            "error_type": type(exc).__name__,
            "error": _sanitize_log_text(str(exc)),
            "observed_utc": _utc_now(),
            "runtime_absent": not runtime.exists() and not runtime.is_symlink(),
        }
        _write_immutable_json(stage_root / "controller-failure.json", failure_payload)
        outcome_path = stage_root / "outcome.json"
        telemetry_path = stage_root / "telemetry.jsonl"
        if not outcome_path.exists() and telemetry_path.is_file():
            try:
                terminal = verify_telemetry(
                    telemetry_path, expected_stage=stage
                )[-1]
                stop_reason = str(terminal["stop_reason"])
                if stop_reason == "evidence_target_reached":
                    raise RuntimeError(
                        "post-child evidence failure cannot retain a successful terminal outcome"
                    )
                outcome: dict[str, object] = {
                    "status": "interrupted"
                    if stop_reason == "parent_interrupted"
                    else "error",
                    "stop_reason": stop_reason,
                    "telemetry": f"{stage}/telemetry.jsonl",
                    "discard_receipt": receipt,
                    "controller_failure": f"{stage}/controller-failure.json",
                }
                retained_events = stage_root / "optimizer-events.jsonl"
                if retained_events.is_file() and partial_summary is not None:
                    outcome.update(
                        {
                            "optimizer_events": f"{stage}/optimizer-events.jsonl",
                            "optimizer_events_sha256": _sha256_file(retained_events),
                            "partial_event_summary": partial_summary,
                        }
                    )
                if stage == "qlora" and proof_path is not None:
                    outcome["quantization_proof"] = "qlora/quantization-proof.json"
                write_stage_outcome(root, stage=stage, outcome=outcome)
            except BaseException:
                # The original controller error remains authoritative; retained files and
                # a verified discard receipt still make the failed transaction auditable.
                pass
        raise


def run_operator_stage(args: argparse.Namespace) -> dict[str, object]:
    stage = str(args.stage)
    _validate_stage_argv(args, stage=stage)
    if stage == "preflight":
        return _run_preflight(args)
    if stage == "record-authority":
        decision = getattr(args, "authority_decision", None)
        if decision is None:
            raise ValueError("record-authority requires --authority-decision")
        return record_package_authority(args.decision_root, decision)
    if stage == "verify-package":
        try:
            bitsandbytes_identity = capture_bitsandbytes_identity()
        except (ImportError, OSError, RuntimeError, TypeError, ValueError) as exc:
            bitsandbytes_identity = {
                "version": None,
                "cuda_kernel_available": False,
                "capture_error_type": type(exc).__name__,
                "capture_error": _sanitize_log_text(str(exc)),
            }
        try:
            torch_identity = capture_torch_identity()
        except (ImportError, OSError, RuntimeError, TypeError, ValueError) as exc:
            torch_identity = {
                "distribution": "torch",
                "capture_error_type": type(exc).__name__,
                "capture_error": _sanitize_log_text(str(exc)),
            }
        return verify_package_runtime(
            args.decision_root,
            bitsandbytes_identity=bitsandbytes_identity,
            torch_identity=torch_identity,
        )
    if stage in {"lora", "qlora"}:
        if getattr(args, "repo_root", None) is None:
            raise ValueError(f"{stage} requires --repo-root")
        if stage == "lora":
            baseline = _read_json(Path(args.decision_root) / "package-baseline.json")
            if baseline.get("bitsandbytes_present") is not False:
                raise RuntimeError("LoRA-first package baseline is not clean")
            if importlib.util.find_spec("bitsandbytes") is not None:
                raise RuntimeError("bitsandbytes was installed before the LoRA stage")
        return run_monitored_training_stage(args, stage=stage)
    if stage == "finalize":
        return finalize_local_decision(args.decision_root)
    if stage == "verify":
        return verify_local_decision(args.decision_root)
    raise ValueError(f"unsupported local decision stage: {stage}")


def _validate_stage_argv(args: argparse.Namespace, *, stage: str) -> None:
    raw = tuple(getattr(args, "_phase40_raw_argv", ()))
    supplied_flags = {
        token.split("=", 1)[0]
        for token in raw
        if isinstance(token, str) and token.startswith("--")
    }
    common = {"--stage", "--decision-root"}
    allowed = {
        "preflight": common
        | {
            "--repo-root",
            "--train-split",
            "--val-split",
            "--downstream-contract",
            "--base-model-path",
            "--download-manifest",
            "--model-id",
            "--model-revision",
            "--decision-window-seconds",
        },
        "record-authority": common | {"--authority-decision"},
        "lora": common
        | {
            "--repo-root",
            "--lora-soft-limit-seconds",
            "--lora-hard-limit-seconds",
            "--warmup-steps",
            "--evidence-target-steps",
        },
        "verify-package": common,
        "qlora": common | {"--repo-root", "--warmup-steps", "--post-warmup-steps"},
        "finalize": common,
        "verify": common,
    }
    if stage not in allowed:
        raise ValueError(f"unsupported local decision stage: {stage}")
    forbidden = supplied_flags - allowed[stage]
    if forbidden:
        raise ValueError(
            f"stage {stage} received inappropriate fields: {', '.join(sorted(forbidden))}"
        )
    if stage == "lora" and (
        args.lora_soft_limit_seconds != LORA_SOFT_LIMIT_SECONDS
        or args.lora_hard_limit_seconds != LORA_HARD_LIMIT_SECONDS
        or args.warmup_steps != WARMUP_OPTIMIZER_STEPS
        or args.evidence_target_steps != MEASURED_OPTIMIZER_STEPS
    ):
        raise ValueError("LoRA stage controls are frozen at 1800/3600 seconds and 5+40 steps")
    if stage == "qlora" and (
        args.warmup_steps != WARMUP_OPTIMIZER_STEPS
        or args.post_warmup_steps != MEASURED_OPTIMIZER_STEPS
    ):
        raise ValueError("QLoRA stage controls are frozen at exactly 5+40 steps")


def _child_main(control_path: Path) -> int:
    control = _read_json_allow_absolute(control_path)
    expected = {"stage", "train_split", "val_split", "repo_root", "base_model_path", "stage_root"}
    if set(control) != expected:
        raise RuntimeError("local training child control has missing or extra fields")
    stage = str(control["stage"])
    if stage not in {"lora", "qlora"}:
        raise RuntimeError("local training child stage is invalid")
    os.environ.update(
        {"HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "HF_DATASETS_OFFLINE": "1"}
    )
    stage_root = Path(str(control["stage_root"]))
    decision_root = stage_root.parent
    repo_root = Path(str(control["repo_root"]))
    if stage_root.name != stage:
        raise RuntimeError("training child stage root differs from its requested stage")
    if not _same_path(Path(str(control["train_split"])), repo_root / TRAIN_RELATIVE_PATH):
        raise RuntimeError("training child train input differs from the canonical allowlist")
    if not _same_path(Path(str(control["val_split"])), repo_root / VAL_RELATIVE_PATH):
        raise RuntimeError("training child validation input differs from the canonical allowlist")
    state = _read_state_unchecked(decision_root)
    supplied_repo_hash = _path_identity_sha256(repo_root)
    if (
        state.repo_root_path_sha256 is not None
        and supplied_repo_hash != state.repo_root_path_sha256
    ):
        raise RuntimeError("training child repository root differs from preflight authority")
    _require_prior_stages(
        decision_root,
        ("preflight",)
        if stage == "lora"
        else ("preflight", "lora", "record-authority", "verify-package"),
    )
    if stage == "qlora":
        authority = _read_json(decision_root / "package-authority.json")
        package = _read_json(decision_root / "package-runtime.json")
        if authority.get("approved") is not True or package.get("torch_unchanged") is not True:
            raise RuntimeError("QLoRA child lacks approved package/Torch authority")
        if capture_torch_identity() != package.get("torch"):
            raise RuntimeError("Torch identity drifted after the package verification gate")
        if capture_bitsandbytes_identity() != package.get("bitsandbytes"):
            raise RuntimeError("bitsandbytes identity drifted after the package verification gate")
    elif importlib.util.find_spec("bitsandbytes") is not None:
        raise RuntimeError("ordinary LoRA child refuses a post-preflight bitsandbytes install")
    validate_external_snapshot_identity(
        Path(str(control["base_model_path"])), EXTERNAL_DOWNLOAD_MANIFEST
    )
    contract_module = importlib.import_module("src.model_adaptation.phase40_contract")
    contract = contract_module.preflight_phase40_inputs(
        Path(str(control["train_split"])),
        Path(str(control["val_split"])),
        repo_root=Path(str(control["repo_root"])),
    )
    training = importlib.import_module("src.model_adaptation.training")
    config = training.build_phase40_local_decision_config(
        adaptation_mode=stage,
        train_split_path=Path(str(control["train_split"])),
        val_split_path=Path(str(control["val_split"])),
        base_model_path=Path(str(control["base_model_path"])),
        decision_stage_root=stage_root,
    )
    result = training.run_phase40_local_decision_child(config, data_contract=contract)
    proof = result.get("quantization_proof")
    proof_payload = None
    if proof is not None:
        proof_payload = {
            key: getattr(value, "value", value) for key, value in asdict(proof).items()
        }
    summary = result.get("resource_summary")
    payload = {
        "events_path": os.fspath(result.get("events_path")),
        "quantization_proof": proof_payload,
        "retained_optimizer_steps": getattr(summary, "retained_optimizer_steps", 0),
        "losses_finite": True,
    }
    runtime = Path(str(control["stage_root"])) / "runtime"
    (runtime / "child-result.json").write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True), encoding="utf-8"
    )
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="phase40-local-experiment")
    parser.add_argument("--child-control", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        return _child_main(args.child_control)
    except (ImportError, OSError, RuntimeError, TypeError, ValueError) as exc:
        print(_sanitize_log_text(str(exc)), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
