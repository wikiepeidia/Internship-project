"""One-shot, evidence-bound recovery for the interrupted Phase 40 LoRA retry.

This module never starts a model process.  It only seals the already-retained
retry evidence after proving that the disposable runtime contains no adapter or
checkpoint and that no matching child process is alive.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import statistics
import subprocess
import sys
import time
from typing import Mapping, Sequence

from src.model_adaptation import phase40_local_experiment as local
from src.model_adaptation.registry import build_model_checksum


RECOVERY_SCHEMA_VERSION = "phase40-lora-retry-recovery-v1"
CONTROLLER_FAILURE_SCHEMA_VERSION = "phase40-controller-failure-recovery-v1"
HISTORICAL_RUN_COMMIT = "803c3b3cec9caceb54732c4c7e94ad6ceb7938a0"
RECOVERY_REASON = (
    "original_controller_error_not_retained; "
    "runtime_cleanup_incomplete_with_readonly_residue"
)
LIVE_FINGERPRINTS: dict[str, object] = {
    "telemetry_sha256": "35dd3d5b6bba556626f508ef8b03ca64a312018f0258098f3c2a8b843ef5a200",
    "optimizer_events_sha256": "f7a7868d4b8643d36995dab28b123cfb3e3e4d52f0af44fcd244b36d3e0c50e7",
    "quantization_proof_sha256": "3cc5390ff3d69bccdfd8db1e7b82f0c1f68c6e1d75764ea9d57cefaf4aa4b6ff",
    "sanitized_stdout_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "sanitized_stderr_sha256": "0a2608746cbedbeac09beb10031127c75a8132b50047d30991a8e169f289c7b0",
    "first_monotonic": 2761.6838294,
    "terminal_monotonic": 4543.8894869,
    "terminal_sequence": 839,
    "observed_optimizer_steps": 31,
    "retained_optimizer_steps": 26,
    "steady_state_step_seconds_median": 53.27434919999996,
}
_BASE_STAGE_FILES = frozenset(
    {
        "retry-authority.json",
        "telemetry.jsonl",
        "optimizer-events.jsonl",
        "quantization-proof.json",
        "child-stdout.sanitized.log",
        "child-stderr.sanitized.log",
    }
)
_RECOVERY_FILES = frozenset(
    {
        "runtime",
        "recovery-seal.json",
        "discard-receipt.json",
        "controller-failure.json",
        "outcome.json",
    }
)
_RUNTIME_FILES = frozenset(
    {
        "child-control.json",
        "child-stderr.log",
        "child-stdout.log",
        "quantization-proof-prestep.json",
        "stop-request.json",
    }
)
_RUNTIME_DIRECTORIES = frozenset(
    {
        "local-decision-work",
        "local-decision-work/qwen3-4b-instruct-2507",
        "local-decision-work/qwen3-4b-instruct-2507/evidence",
        "local-decision-work/qwen3-4b-instruct-2507/evidence/rtx5050-lora-retry-1",
        "local-decision-work/qwen3-4b-instruct-2507/probes",
        "local-decision-work/qwen3-4b-instruct-2507/probes/rtx5050-lora-retry-1",
        "local-decision-work/qwen3-4b-instruct-2507/probes/rtx5050-lora-retry-1/trainer",
    }
)
_RECOVERY_CODE_FILES = (
    "src/model_adaptation/phase40_callbacks.py",
    "src/model_adaptation/phase40_lora_recovery.py",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _git_bytes(repo_root: Path, revision: str, relative: str) -> bytes:
    completed = subprocess.run(
        ["git", "show", f"{revision}:{relative}"],
        cwd=repo_root,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
    )
    return completed.stdout


def _git_commit(repo_root: Path, revision: str = "HEAD") -> str:
    completed = subprocess.run(
        ["git", "rev-parse", revision],
        cwd=repo_root,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
    )
    value = completed.stdout.strip()
    if len(value) != 40 or any(character not in "0123456789abcdef" for character in value):
        raise RuntimeError("recovery Git commit identity is invalid")
    return value


def _verify_historical_run_code(
    repo_root: Path, authority: Mapping[str, object]
) -> dict[str, object]:
    commit = _git_commit(repo_root, HISTORICAL_RUN_COMMIT)
    if commit != HISTORICAL_RUN_COMMIT:
        raise RuntimeError("historical LoRA retry commit identity drifted")
    declared = authority.get("fix_code_sha256")
    if not isinstance(declared, dict) or not declared:
        raise RuntimeError("LoRA retry authority lacks its source hashes")
    observed: dict[str, str] = {}
    for relative, expected in sorted(declared.items()):
        if not isinstance(relative, str) or not isinstance(expected, str):
            raise RuntimeError("LoRA retry source-hash authority is invalid")
        digest = hashlib.sha256(
            _git_bytes(repo_root, HISTORICAL_RUN_COMMIT, relative)
        ).hexdigest()
        if digest != expected:
            raise RuntimeError("historical LoRA retry source differs from its authority")
        observed[relative] = digest
    return {"commit": commit, "source_sha256": observed}


def _recovery_code_identity(repo_root: Path) -> dict[str, object]:
    commit = _git_commit(repo_root)
    hashes: dict[str, str] = {}
    for relative in _RECOVERY_CODE_FILES:
        path = repo_root / relative
        working = path.read_bytes()
        committed = _git_bytes(repo_root, commit, relative)
        if working != committed:
            raise RuntimeError("recovery code must be committed and byte-identical to HEAD")
        hashes[relative] = hashlib.sha256(working).hexdigest()
    return {"commit": commit, "source_sha256": hashes}


def _is_link_or_reparse(path: Path) -> bool:
    observed = os.lstat(path)
    return bool(getattr(observed, "st_reparse_tag", 0)) or path.is_symlink()


def _validate_stage_entries(stage_root: Path) -> None:
    if not stage_root.is_dir() or _is_link_or_reparse(stage_root):
        raise RuntimeError("LoRA retry evidence root is not one real directory")
    names = {entry.name for entry in stage_root.iterdir()}
    if not _BASE_STAGE_FILES.issubset(names) or not names.issubset(
        _BASE_STAGE_FILES | _RECOVERY_FILES
    ):
        raise RuntimeError("LoRA retry evidence root contains an unexpected artifact")
    for entry in stage_root.iterdir():
        if _is_link_or_reparse(entry):
            raise RuntimeError("LoRA retry evidence contains a link or reparse point")


def _runtime_inventory(runtime: Path) -> tuple[list[dict[str, object]], list[str]]:
    lexical = Path(os.path.abspath(os.path.normpath(os.fspath(runtime))))
    if _is_link_or_reparse(lexical):
        raise RuntimeError("retry runtime must not be a link or reparse point")
    root = lexical.resolve(strict=True)
    if not root.is_dir() or _is_link_or_reparse(root):
        raise RuntimeError("retry runtime must be one real directory")
    files: set[str] = set()
    directories: set[str] = set()
    inventory: list[dict[str, object]] = []
    readonly_directories: list[str] = []
    for current_raw, directory_names, file_names in os.walk(root, topdown=True):
        current = Path(current_raw)
        if _is_link_or_reparse(current):
            raise RuntimeError("retry runtime contains a link or reparse point")
        for name in tuple(directory_names):
            candidate = current / name
            if _is_link_or_reparse(candidate):
                raise RuntimeError("retry runtime contains a link or reparse point")
            relative = candidate.relative_to(root).as_posix()
            directories.add(relative)
            attributes = int(getattr(os.lstat(candidate), "st_file_attributes", 0))
            if attributes & 0x1:
                readonly_directories.append(relative)
            inventory.append(
                {"path": relative, "kind": "directory", "file_attributes": attributes}
            )
        for name in file_names:
            candidate = current / name
            if _is_link_or_reparse(candidate) or not candidate.is_file():
                raise RuntimeError("retry runtime contains an unsafe file")
            relative = candidate.relative_to(root).as_posix()
            files.add(relative)
            inventory.append(
                {
                    "path": relative,
                    "kind": "file",
                    "bytes": candidate.stat().st_size,
                    "sha256": local._sha256_file(candidate),
                    "file_attributes": int(
                        getattr(os.lstat(candidate), "st_file_attributes", 0)
                    ),
                }
            )
    if files != _RUNTIME_FILES or directories != _RUNTIME_DIRECTORIES:
        raise RuntimeError("retry runtime inventory differs from the audited residue")
    forbidden = ("adapter", "checkpoint", ".safetensors", ".bin", ".pt", ".pth")
    if any(any(marker in relative.casefold() for marker in forbidden) for relative in files):
        raise RuntimeError("retry runtime contains a model or checkpoint artifact")
    if not readonly_directories:
        raise RuntimeError("retry runtime lacks the observed READONLY cleanup residue")
    return sorted(inventory, key=lambda item: str(item["path"])), sorted(readonly_directories)


def _same_path(left: object, right: Path) -> bool:
    if not isinstance(left, str):
        return False
    return os.path.normcase(os.path.abspath(left)) == os.path.normcase(
        os.path.abspath(os.fspath(right))
    )


def _validate_runtime_controls(runtime: Path, repo_root: Path, stage_root: Path) -> None:
    control = local._read_json_allow_absolute(runtime / "child-control.json")
    expected_keys = {
        "stage",
        "adaptation_mode",
        "run_id",
        "train_split",
        "val_split",
        "repo_root",
        "base_model_path",
        "stage_root",
    }
    if set(control) != expected_keys or (
        control.get("stage") != local.LORA_RETRY_STAGE
        or control.get("adaptation_mode") != "lora"
        or control.get("run_id") != local.LORA_RETRY_RUN_ID
        or not _same_path(control.get("repo_root"), repo_root)
        or not _same_path(control.get("stage_root"), stage_root)
        or not _same_path(control.get("train_split"), repo_root / local.TRAIN_RELATIVE_PATH)
        or not _same_path(control.get("val_split"), repo_root / local.VAL_RELATIVE_PATH)
        or not _same_path(control.get("base_model_path"), local.EXTERNAL_QWEN_SNAPSHOT)
    ):
        raise RuntimeError("retry child control differs from its authorized LoRA identity")
    if local._read_json_allow_absolute(runtime / "stop-request.json") != {"stop": True}:
        raise RuntimeError("retry runtime lacks the exact boundary stop request")


def _validate_quantization_proof(stage_root: Path, runtime: Path) -> dict[str, object]:
    retained = local._read_json(stage_root / "quantization-proof.json")
    prestep = local._read_json(runtime / "quantization-proof-prestep.json")
    if retained != prestep:
        raise RuntimeError("retained quantization proof differs from the pre-step seal")
    required = {
        "requested_mode": "lora",
        "resolved_mode": "full-precision-lora",
        "bitsandbytes_version": None,
        "load_in_4bit": False,
        "nf4": False,
        "double_quantization": False,
        "is_loaded_in_4bit": False,
        "linear4bit_modules": 0,
        "kbit_preparation_applied": False,
        "base_weights_frozen": True,
        "adapter_only_trainables": True,
        "backward_with_adapter_gradients": False,
        "adapter_gradient_finite_count": 0,
        "adapter_gradient_nonzero_count": 0,
    }
    if any(retained.get(key) != value for key, value in required.items()):
        raise RuntimeError("retry proof is not full-precision adapter-only LoRA")
    count = retained.get("adapter_trainable_count")
    if not isinstance(count, int) or isinstance(count, bool) or count <= 0:
        raise RuntimeError("retry proof lacks adapter trainable tensors")
    return retained


def _validate_logs(stage_root: Path, runtime: Path) -> dict[str, object]:
    raw_hashes: dict[str, str] = {}
    sanitized_hashes: dict[str, str] = {}
    for stream in ("stdout", "stderr"):
        raw = runtime / f"child-{stream}.log"
        sanitized = stage_root / f"child-{stream}.sanitized.log"
        raw_text = raw.read_text(encoding="utf-8", errors="replace")
        sanitized_text = sanitized.read_text(encoding="utf-8", errors="strict")
        if local._sanitize_log_text(raw_text) != sanitized_text:
            raise RuntimeError(f"retained {stream} log differs from sanitized raw bytes")
        raw_hashes[stream] = local._sha256_file(raw)
        sanitized_hashes[stream] = local._sha256_file(sanitized)
    if local._detect_memory_oom_kind(
        (stage_root / "child-stderr.sanitized.log").read_text(encoding="utf-8")
    ) is not None:
        raise RuntimeError("recovery cannot relabel an explicit OOM as controller failure")
    return {"raw_sha256": raw_hashes, "sanitized_sha256": sanitized_hashes}


def _validate_live_fingerprints(stage_root: Path) -> None:
    actual = {
        "telemetry_sha256": local._sha256_file(stage_root / "telemetry.jsonl"),
        "optimizer_events_sha256": local._sha256_file(
            stage_root / "optimizer-events.jsonl"
        ),
        "quantization_proof_sha256": local._sha256_file(
            stage_root / "quantization-proof.json"
        ),
        "sanitized_stdout_sha256": local._sha256_file(
            stage_root / "child-stdout.sanitized.log"
        ),
        "sanitized_stderr_sha256": local._sha256_file(
            stage_root / "child-stderr.sanitized.log"
        ),
    }
    for name, observed in actual.items():
        if observed != LIVE_FINGERPRINTS[name]:
            raise RuntimeError(f"audited LoRA retry fingerprint drifted: {name}")


def _validate_terminal_and_events(
    stage_root: Path, state: local.LocalDecisionState, authority: Mapping[str, object]
) -> tuple[list[dict[str, object]], dict[str, object]]:
    telemetry = local.verify_telemetry(
        stage_root / "telemetry.jsonl", expected_stage=local.LORA_RETRY_STAGE
    )
    first = telemetry[0]
    terminal = telemetry[-1]
    if (
        terminal.get("stop_reason") != "parent_controller_error"
        or terminal.get("sequence_id") != LIVE_FINGERPRINTS["terminal_sequence"]
        or not math.isclose(
            float(first["monotonic_seconds"]),
            float(LIVE_FINGERPRINTS["first_monotonic"]),
            abs_tol=1e-9,
        )
        or not math.isclose(
            float(terminal["monotonic_seconds"]),
            float(LIVE_FINGERPRINTS["terminal_monotonic"]),
            abs_tol=1e-9,
        )
        or float(terminal["monotonic_seconds"]) > state.deadline_monotonic
    ):
        raise RuntimeError("retry terminal telemetry differs from the audited controller failure")
    elapsed = float(terminal["monotonic_seconds"]) - float(first["monotonic_seconds"])
    soft_limit = float(authority["retry_soft_limit_seconds"])
    if elapsed < soft_limit or elapsed > soft_limit + 30.0:
        raise RuntimeError("retry failure is outside the bounded soft-stop cleanup interval")
    summary = local._partial_optimizer_summary(
        stage_root / "optimizer-events.jsonl", run_id=local.LORA_RETRY_RUN_ID
    )
    durations = summary.get("measured_step_seconds")
    if not isinstance(durations, list) or len(durations) != 26:
        raise RuntimeError("retry event evidence lacks 26 measured step durations")
    median = statistics.median(float(value) for value in durations)
    if (
        summary.get("observed_optimizer_steps")
        != LIVE_FINGERPRINTS["observed_optimizer_steps"]
        or summary.get("retained_optimizer_steps")
        != LIVE_FINGERPRINTS["retained_optimizer_steps"]
        or summary.get("losses_finite") is not True
        or summary.get("terminal_event_kind") != "step_timing"
        or not math.isclose(
            median,
            float(LIVE_FINGERPRINTS["steady_state_step_seconds_median"]),
            abs_tol=1e-9,
        )
    ):
        raise RuntimeError("retry optimizer evidence differs from the audited partial run")
    return telemetry, {**summary, "steady_state_step_seconds_median": median}


def _assert_no_live_child(control_path: Path) -> dict[str, object]:
    try:
        import psutil
    except ImportError as exc:  # pragma: no cover - production dependency guard
        raise RuntimeError("psutil is required to prove the LoRA child is absent") from exc
    target = os.path.normcase(os.path.abspath(control_path))
    scanned_python = 0
    for process in psutil.process_iter(["pid", "name", "cmdline"]):
        if process.pid == os.getpid():
            continue
        name = str(process.info.get("name") or "").casefold()
        if "python" not in name:
            continue
        scanned_python += 1
        try:
            command = process.info.get("cmdline")
        except (psutil.AccessDenied, psutil.NoSuchProcess) as exc:
            raise RuntimeError("cannot prove an inaccessible Python process is unrelated") from exc
        if command is None:
            raise RuntimeError("cannot prove a Python process with no command line is unrelated")
        normalized = {
            os.path.normcase(os.path.abspath(str(argument))) for argument in command
        }
        if target in normalized:
            raise RuntimeError("the LoRA retry child process is still alive")
    return {
        "method": "psutil_exact_child_control_argument_scan",
        "scanned_python_processes": scanned_python,
        "matching_child_pids": [],
    }


def _resource_peaks(telemetry: Sequence[Mapping[str, object]]) -> dict[str, object]:
    keys = (
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
    return {
        key: max(
            (
                float(row[key])
                for row in telemetry
                if isinstance(row.get(key), (int, float))
                and not isinstance(row.get(key), bool)
            ),
            default=None,
        )
        for key in keys
    }


def _verify_existing_seal(
    seal: Mapping[str, object], stage_root: Path, recovery_code: Mapping[str, object]
) -> None:
    if (
        seal.get("schema_version") != RECOVERY_SCHEMA_VERSION
        or seal.get("stage") != local.LORA_RETRY_STAGE
        or seal.get("run_id") != local.LORA_RETRY_RUN_ID
        or seal.get("recovery_reason") != RECOVERY_REASON
        or seal.get("recovery_code") != recovery_code
        or seal.get("telemetry_sha256")
        != local._sha256_file(stage_root / "telemetry.jsonl")
        or seal.get("optimizer_events_sha256")
        != local._sha256_file(stage_root / "optimizer-events.jsonl")
        or seal.get("quantization_proof_sha256")
        != local._sha256_file(stage_root / "quantization-proof.json")
    ):
        raise RuntimeError("existing recovery seal differs from current immutable evidence")


def recover_lora_retry(
    decision_root: Path,
    *,
    repo_root: Path,
    now_utc: str | None = None,
    now_monotonic: float | None = None,
    boot_identity: str | None = None,
) -> dict[str, object]:
    """Seal the single audited failed retry without starting or loading a model."""

    root = Path(decision_root)
    repository = Path(repo_root).resolve(strict=True)
    stage_root = root / local.LORA_RETRY_STAGE
    timestamp = _utc_now() if now_utc is None else now_utc
    monotonic = time.monotonic() if now_monotonic is None else float(now_monotonic)
    state = local.load_decision_state(
        root,
        now_utc=timestamp,
        now_monotonic=monotonic,
        boot_identity=boot_identity,
    )
    stages = tuple(str(row["stage"]) for row in local._ledger_entries(root))
    if stages == ("preflight", "lora", local.LORA_RETRY_STAGE):
        outcome = local._read_json(stage_root / "outcome.json")
        if (
            outcome.get("status") != "error"
            or outcome.get("stop_reason") != "parent_controller_error"
            or outcome.get("retained_optimizer_steps") != 26
        ):
            raise RuntimeError("completed recovery outcome drifted")
        return outcome
    if stages != ("preflight", "lora"):
        raise RuntimeError("recovery requires the exact preflight,lora ledger prefix")
    _validate_stage_entries(stage_root)
    authority = local._verify_lora_retry_authority(root)
    historical_code = _verify_historical_run_code(repository, authority)
    recovery_code = _recovery_code_identity(repository)
    _validate_live_fingerprints(stage_root)
    telemetry, optimizer = _validate_terminal_and_events(stage_root, state, authority)
    process_absence = _assert_no_live_child(stage_root / "runtime/child-control.json")
    runtime = stage_root / "runtime"
    seal_path = stage_root / "recovery-seal.json"
    seal: dict[str, object]
    if seal_path.is_file():
        seal = local._read_json(seal_path)
        _verify_existing_seal(seal, stage_root, recovery_code)
    else:
        if not runtime.is_dir():
            raise RuntimeError("unsealed recovery is missing its disposable runtime")
        inventory, readonly_directories = _runtime_inventory(runtime)
        _validate_runtime_controls(runtime, repository, stage_root)
        proof = _validate_quantization_proof(stage_root, runtime)
        logs = _validate_logs(stage_root, runtime)
        seal = {
            "schema_version": RECOVERY_SCHEMA_VERSION,
            "stage": local.LORA_RETRY_STAGE,
            "run_id": local.LORA_RETRY_RUN_ID,
            "status": "error",
            "stop_reason": "parent_controller_error",
            "recovery_reason": RECOVERY_REASON,
            "original_controller_error_retained": False,
            "cleanup_masking_basis": "residual_real_directories_with_windows_readonly_attribute",
            "cleanup_caused_original_controller_error": False,
            "termination_race_hypothesis_is_inference": True,
            "retry_authority": f"{local.LORA_RETRY_STAGE}/retry-authority.json",
            "retry_authority_sha256": local._sha256_file(
                stage_root / "retry-authority.json"
            ),
            "historical_training_code": historical_code,
            "recovery_code": recovery_code,
            "telemetry_sha256": local._sha256_file(stage_root / "telemetry.jsonl"),
            "terminal_telemetry_sequence": telemetry[-1]["sequence_id"],
            "terminal_monotonic": telemetry[-1]["monotonic_seconds"],
            "optimizer_events_sha256": local._sha256_file(
                stage_root / "optimizer-events.jsonl"
            ),
            "partial_event_summary": optimizer,
            "quantization_proof_sha256": local._sha256_file(
                stage_root / "quantization-proof.json"
            ),
            "quantization_proof": proof,
            "child_logs": logs,
            "runtime_tree_sha256": build_model_checksum(runtime),
            "runtime_inventory": inventory,
            "readonly_runtime_directories": readonly_directories,
            "process_absence": process_absence,
            "sealed_utc": timestamp,
            "sealed_monotonic": monotonic,
            "remaining_decision_seconds": state.deadline_monotonic - monotonic,
        }
        local._write_immutable_json(seal_path, seal)
    receipt_path = stage_root / "discard-receipt.json"
    if runtime.exists() or runtime.is_symlink():
        if receipt_path.exists() or receipt_path.is_symlink():
            raise RuntimeError("retry runtime and discard receipt coexist")
        inventory, _ = _runtime_inventory(runtime)
        if inventory != seal.get("runtime_inventory"):
            raise RuntimeError("retry runtime changed after recovery authorization")
        receipt = local.discard_stage_runtime(
            stage_root, run_id=local.LORA_RETRY_RUN_ID
        )
    else:
        receipt = local._read_json(receipt_path)
        local.verify_stage_discard(stage_root, receipt)
    if receipt.get("pre_discard_sha256") != seal.get("runtime_tree_sha256"):
        raise RuntimeError("discard receipt differs from the recovery-sealed runtime")
    controller_path = stage_root / "controller-failure.json"
    controller = {
        "schema_version": CONTROLLER_FAILURE_SCHEMA_VERSION,
        "stage": local.LORA_RETRY_STAGE,
        "run_id": local.LORA_RETRY_RUN_ID,
        "status": "error",
        "stop_reason": "parent_controller_error",
        "recovery_reason": RECOVERY_REASON,
        "original_controller_error_retained": False,
        "runtime_absent": True,
        "recovery_seal": f"{local.LORA_RETRY_STAGE}/recovery-seal.json",
        "recovery_seal_sha256": local._sha256_file(seal_path),
        "terminal_monotonic": telemetry[-1]["monotonic_seconds"],
    }
    local._write_immutable_json(controller_path, controller)
    outcome_payload = {
        "status": "error",
        "stop_reason": "parent_controller_error",
        "telemetry": f"{local.LORA_RETRY_STAGE}/telemetry.jsonl",
        "discard_receipt": receipt,
        "controller_failure": f"{local.LORA_RETRY_STAGE}/controller-failure.json",
        "controller_failure_sha256": local._sha256_file(controller_path),
        "recovery_seal": f"{local.LORA_RETRY_STAGE}/recovery-seal.json",
        "recovery_seal_sha256": local._sha256_file(seal_path),
        "recovery_reason": RECOVERY_REASON,
        "retained_optimizer_steps": 26,
        "losses_finite": True,
        "optimizer_events": f"{local.LORA_RETRY_STAGE}/optimizer-events.jsonl",
        "optimizer_events_sha256": optimizer["optimizer_events_sha256"],
        "partial_event_summary": optimizer,
        "quantization_proof": f"{local.LORA_RETRY_STAGE}/quantization-proof.json",
        "quantization_proof_sha256": local._sha256_file(
            stage_root / "quantization-proof.json"
        ),
        "raw_child_log_sha256": seal["child_logs"]["raw_sha256"],
        "sanitized_child_log_sha256": seal["child_logs"]["sanitized_sha256"],
        "resource_peaks": _resource_peaks(telemetry),
        "measured_target_reached": False,
        "observed_optimizer_steps": 31,
        "steady_state_step_seconds_median": optimizer[
            "steady_state_step_seconds_median"
        ],
    }
    outcome_path = stage_root / "outcome.json"
    if outcome_path.is_file():
        outcome = local._read_json(outcome_path)
        if any(outcome.get(key) != value for key, value in outcome_payload.items()):
            raise RuntimeError("partially sealed recovery outcome drifted")
        local._append_stage(
            root,
            stage=local.LORA_RETRY_STAGE,
            timestamp_utc=str(outcome["completed_utc"]),
            monotonic=float(outcome["completed_monotonic"]),
            artifact=outcome_path,
        )
    else:
        outcome = local.write_stage_outcome(
            root,
            stage=local.LORA_RETRY_STAGE,
            outcome=outcome_payload,
            now_utc=timestamp,
            now_monotonic=monotonic,
            boot_identity=boot_identity,
        )
    if tuple(str(row["stage"]) for row in local._ledger_entries(root)) != (
        "preflight",
        "lora",
        local.LORA_RETRY_STAGE,
    ):
        raise RuntimeError("recovery did not seal the exact retry ledger stage")
    return outcome


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("seal-lora-retry-failure",))
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    repository = args.repo_root.resolve(strict=True)
    expected_root = repository / local.DECISION_ROOT_RELATIVE_PATH
    try:
        outcome = recover_lora_retry(expected_root, repo_root=repository)
    except (OSError, RuntimeError, ValueError, TimeoutError) as exc:
        print(f"Phase 40 LoRA recovery refused: {exc}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "stage": local.LORA_RETRY_STAGE,
                "status": outcome["status"],
                "stop_reason": outcome["stop_reason"],
                "retained_optimizer_steps": outcome["retained_optimizer_steps"],
                "outcome": f"{local.LORA_RETRY_STAGE}/outcome.json",
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
