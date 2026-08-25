"""Dated, fail-closed RTX 5050 QLoRA continuation for Phase 40.

This module deliberately does not resume or mutate the expired LoRA decision
root.  It hash-links that complete historical tree as read-only input, starts a
fresh immutable 7,200-second clock, and runs one genuine 5-warm-up + 40-measured
step QLoRA probe.  Only the canonical train and validation splits are inputs;
the reserved test partition is outside this module's interface.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import time
from typing import Callable, Mapping, Sequence

from src.model_adaptation import phase40_local_experiment as local


SESSION_ROOT_RELATIVE_PATH = Path(
    "data/models/phase40/probes/rtx5050-qlora-session-20260825"
)
SOURCE_ROOT_RELATIVE_PATH = local.DECISION_ROOT_RELATIVE_PATH
SESSION_ID = "rtx5050-qlora-session-20260825"
RUN_ID = "rtx5050-qlora"
MODULE_NAME = "src.model_adaptation.phase40_qlora_session"
OPERATOR_CODE_RELATIVE_PATH = Path("src/model_adaptation/phase40_qlora_session.py")
SESSION_WINDOW_SECONDS = 7200.0
TELEMETRY_INTERVAL_SECONDS = 2.0

CLOCK_SCHEMA = "phase40-qlora-session-clock-v1"
STATE_SCHEMA = "phase40-qlora-session-state-v1"
LEDGER_SCHEMA = "phase40-qlora-session-ledger-v1"
SOURCE_LINK_SCHEMA = "phase40-qlora-source-decision-link-v1"
AUTHORITY_SCHEMA = "phase40-qlora-session-package-authority-v1"
PACKAGE_SCHEMA = "phase40-qlora-session-package-runtime-v1"
OUTCOME_SCHEMA = "phase40-qlora-session-outcome-v1"
FINALIZE_SCHEMA = "phase40-qlora-session-finalize-v1"
MANIFEST_SCHEMA = "phase40-qlora-session-manifest-v1"
CONTROLLER_FAILURE_SCHEMA = "phase40-qlora-session-controller-failure-v1"
TREE_ALGORITHM = "sorted-relative-path-size-sha256-canonical-json-v1"

LEDGER_STAGES = (
    "preflight",
    "record-authority",
    "verify-package",
    "qlora",
    "finalize",
)
SOURCE_STAGES = ("preflight", "lora", local.LORA_RETRY_STAGE)
SOURCE_REQUIRED_ARTIFACTS = (
    "decision-state.json",
    "stage-ledger.jsonl",
    "lora/outcome.json",
    f"{local.LORA_RETRY_STAGE}/outcome.json",
    f"{local.LORA_RETRY_STAGE}/retry-authority.json",
    f"{local.LORA_RETRY_STAGE}/recovery-seal.json",
    f"{local.LORA_RETRY_STAGE}/recovery-finalization.json",
    f"{local.LORA_RETRY_STAGE}/discard-receipt.json",
)


@dataclass(frozen=True, slots=True)
class TreeSnapshot:
    sha256: str
    file_count: int
    total_bytes: int
    files: tuple[dict[str, object], ...]

    def summary(self) -> dict[str, object]:
        return {
            "algorithm": TREE_ALGORITHM,
            "sha256": self.sha256,
            "file_count": self.file_count,
            "total_bytes": self.total_bytes,
        }


@dataclass(frozen=True, slots=True)
class ChildExecution:
    returncode: int
    stop_reason: str


def _repo_root(path: Path) -> Path:
    root = Path(path).resolve(strict=True)
    if not root.is_dir() or root.is_symlink() or local._is_reparse_point(root):
        raise ValueError("repository root must be one real directory")
    return root


def _expected_paths(repo_root: Path) -> dict[str, Path]:
    root = _repo_root(repo_root)
    return {
        "repo": root,
        "session": root / SESSION_ROOT_RELATIVE_PATH,
        "source": root / SOURCE_ROOT_RELATIVE_PATH,
        "train": root / local.TRAIN_RELATIVE_PATH,
        "validation": root / local.VAL_RELATIVE_PATH,
        "contract": root / local.DOWNSTREAM_CONTRACT_RELATIVE_PATH,
    }


def _validate_fixed_session_root(repo_root: Path, session_root: Path) -> dict[str, Path]:
    paths = _expected_paths(repo_root)
    supplied = Path(session_root)
    if ".." in supplied.parts or not local._same_path(supplied, paths["session"]):
        raise ValueError("session root is not the fixed dated Phase 40 QLoRA root")
    if paths["session"].exists() and local._is_reparse_point(paths["session"]):
        raise ValueError("session root must not be a link or reparse point")
    return paths


def _operator_code_identity(repo_root: Path) -> dict[str, object]:
    path = Path(repo_root) / OPERATOR_CODE_RELATIVE_PATH
    if not path.is_file() or path.is_symlink() or local._is_reparse_point(path):
        raise RuntimeError("dated QLoRA operator code is missing or unsafe")
    return {
        "module": MODULE_NAME,
        "relative_path": OPERATOR_CODE_RELATIVE_PATH.as_posix(),
        "sha256": local._sha256_file(path),
    }


def _forbidden_disposable_component(name: str) -> bool:
    lowered = name.casefold()
    return lowered == "runtime" or lowered == "checkpoints" or lowered.startswith(
        "checkpoint-"
    )


def _secure_tree_snapshot(root: Path, *, forbid_disposable: bool) -> TreeSnapshot:
    tree = Path(root)
    if not tree.is_dir() or tree.is_symlink() or local._is_reparse_point(tree):
        raise RuntimeError("evidence tree must be one real directory")
    files: list[dict[str, object]] = []
    for current_raw, directory_names, file_names in os.walk(tree, topdown=True):
        current = Path(current_raw)
        if current.is_symlink() or local._is_reparse_point(current):
            raise RuntimeError("evidence tree contains a link or reparse point")
        directory_names.sort()
        file_names.sort()
        for name in directory_names:
            candidate = current / name
            if candidate.is_symlink() or local._is_reparse_point(candidate):
                raise RuntimeError("evidence tree contains a link or reparse point")
            if forbid_disposable and _forbidden_disposable_component(name):
                raise RuntimeError("historical evidence still contains runtime/checkpoints")
        for name in file_names:
            candidate = current / name
            if candidate.is_symlink() or local._is_reparse_point(candidate):
                raise RuntimeError("evidence tree contains a link or reparse point")
            relative = candidate.relative_to(tree).as_posix()
            if forbid_disposable and any(
                _forbidden_disposable_component(part) for part in Path(relative).parts
            ):
                raise RuntimeError("historical evidence still contains runtime/checkpoints")
            files.append(
                {
                    "relative_path": relative,
                    "bytes": candidate.stat().st_size,
                    "sha256": local._sha256_file(candidate),
                }
            )
    files.sort(key=lambda row: str(row["relative_path"]))
    total_bytes = sum(int(row["bytes"]) for row in files)
    digest = hashlib.sha256(
        local._canonical_json_bytes(
            {"algorithm": TREE_ALGORITHM, "files": files}
        )
    ).hexdigest()
    return TreeSnapshot(digest, len(files), total_bytes, tuple(files))


def build_source_decision_link(source_root: Path) -> dict[str, object]:
    """Validate and summarize the expired source without checking its live clock."""

    root = Path(source_root)
    before = _secure_tree_snapshot(root, forbid_disposable=True)
    state = local._read_state_unchecked(root)
    stages = tuple(str(row["stage"]) for row in local._ledger_entries(root))
    if stages != SOURCE_STAGES:
        raise RuntimeError("historical source has an unexpected stage sequence")
    required_hashes: dict[str, str] = {}
    for relative in SOURCE_REQUIRED_ARTIFACTS:
        path = root / relative
        if not path.is_file() or path.is_symlink() or local._is_reparse_point(path):
            raise RuntimeError(f"historical source artifact is missing or unsafe: {relative}")
        required_hashes[relative] = local._sha256_file(path)
    lora = local._read_json(root / "lora/outcome.json")
    retry = local._read_json(root / f"{local.LORA_RETRY_STAGE}/outcome.json")
    after = _secure_tree_snapshot(root, forbid_disposable=True)
    if before != after:
        raise RuntimeError("historical source changed while its read-only link was built")
    return {
        "schema_version": SOURCE_LINK_SCHEMA,
        "source_root_relative_path": SOURCE_ROOT_RELATIVE_PATH.as_posix(),
        "historical_source_read_only": True,
        "source_clock_may_be_expired": True,
        "source_session_id": state.experiment_id,
        "source_stages": list(stages),
        "source_tree": before.summary(),
        "required_artifact_sha256": required_hashes,
        "outcomes": {
            "lora": {
                "status": lora.get("status"),
                "stop_reason": lora.get("stop_reason"),
            },
            local.LORA_RETRY_STAGE: {
                "status": retry.get("status"),
                "stop_reason": retry.get("stop_reason"),
                "retained_optimizer_steps": retry.get("retained_optimizer_steps"),
                "measured_target_reached": retry.get("measured_target_reached"),
            },
        },
        "effective_status": retry.get("status"),
        "effective_stop_reason": retry.get("stop_reason"),
        "runtime_paths_absent": True,
        "checkpoint_paths_absent": True,
    }


def _guard_source(session_root: Path, source_root: Path) -> TreeSnapshot:
    link = local._read_json(Path(session_root) / "source-decision-link.json")
    snapshot = _secure_tree_snapshot(source_root, forbid_disposable=True)
    source_tree = link.get("source_tree")
    if not isinstance(source_tree, Mapping) or source_tree.get("sha256") != snapshot.sha256:
        raise RuntimeError("historical source tree drifted after the continuation was sealed")
    if source_tree.get("file_count") != snapshot.file_count:
        raise RuntimeError("historical source tree file count drifted")
    for relative, expected in dict(link["required_artifact_sha256"]).items():
        if local._sha256_file(Path(source_root) / relative) != expected:
            raise RuntimeError(f"historical source artifact drifted: {relative}")
    return snapshot


def _append_ledger(
    root: Path,
    *,
    stage: str,
    artifact: Path,
    timestamp_utc: str,
    monotonic_seconds: float,
    source_before: str,
    source_after: str,
) -> None:
    if stage not in LEDGER_STAGES:
        raise ValueError("unsupported QLoRA session stage")
    rows = _ledger_rows(root) if (Path(root) / "stage-ledger.jsonl").exists() else []
    expected = LEDGER_STAGES[len(rows)] if len(rows) < len(LEDGER_STAGES) else None
    if stage != expected:
        raise RuntimeError(f"stage replay/reordering refused; expected {expected!r}")
    previous = (
        hashlib.sha256(local._canonical_json_bytes(rows[-1])).hexdigest()
        if rows
        else "0" * 64
    )
    artifact_relative = artifact.resolve(strict=True).relative_to(
        Path(root).resolve(strict=True)
    ).as_posix()
    local._append_jsonl(
        Path(root) / "stage-ledger.jsonl",
        {
            "schema_version": LEDGER_SCHEMA,
            "sequence_id": len(rows),
            "stage": stage,
            "timestamp_utc": timestamp_utc,
            "monotonic_seconds": monotonic_seconds,
            "previous_entry_sha256": previous,
            "artifact": artifact_relative,
            "artifact_sha256": local._sha256_file(artifact),
            "source_tree_before_sha256": source_before,
            "source_tree_after_sha256": source_after,
        },
    )


def _ledger_rows(root: Path) -> list[dict[str, object]]:
    rows = local._load_jsonl(Path(root) / "stage-ledger.jsonl")
    previous = "0" * 64
    for index, row in enumerate(rows):
        required = {
            "schema_version",
            "sequence_id",
            "stage",
            "timestamp_utc",
            "monotonic_seconds",
            "previous_entry_sha256",
            "artifact",
            "artifact_sha256",
            "source_tree_before_sha256",
            "source_tree_after_sha256",
        }
        if set(row) != required or row.get("schema_version") != LEDGER_SCHEMA:
            raise RuntimeError("QLoRA session ledger schema drifted")
        if row.get("sequence_id") != index or row.get("previous_entry_sha256") != previous:
            raise RuntimeError("QLoRA session ledger hash chain is broken")
        if index >= len(LEDGER_STAGES) or row.get("stage") != LEDGER_STAGES[index]:
            raise RuntimeError("QLoRA session ledger stage order drifted")
        relative = local._portable_relative_path(row.get("artifact"))
        artifact = Path(root) / relative
        if local._sha256_file(artifact) != row.get("artifact_sha256"):
            raise RuntimeError(f"QLoRA session ledger artifact drifted: {relative}")
        if row.get("source_tree_before_sha256") != row.get("source_tree_after_sha256"):
            raise RuntimeError("historical source changed during a session stage")
        previous = hashlib.sha256(local._canonical_json_bytes(row)).hexdigest()
    return rows


def _require_stages(root: Path, expected: Sequence[str]) -> None:
    actual = tuple(str(row["stage"]) for row in _ledger_rows(root))
    if actual != tuple(expected):
        raise RuntimeError(f"QLoRA session requires stages {tuple(expected)!r}; got {actual!r}")


def _start_clock(root: Path) -> dict[str, object]:
    session = Path(root)
    if session.exists() or session.is_symlink():
        raise FileExistsError("dated QLoRA session already exists; clock reset refused")
    session.mkdir(parents=True, exist_ok=False)
    started_utc = local._utc_now()
    started = time.monotonic()
    payload = {
        "schema_version": CLOCK_SCHEMA,
        "session_id": SESSION_ID,
        "started_utc": started_utc,
        "started_monotonic": started,
        "deadline_monotonic": started + SESSION_WINDOW_SECONDS,
        "window_seconds": SESSION_WINDOW_SECONDS,
        "boot_identity": local._boot_identity(),
        "session_root_path_sha256": local._path_identity_sha256(session),
    }
    local._write_immutable_json(session / "session-clock.json", payload)
    return payload


def _state(root: Path, *, allow_expired: bool = False) -> dict[str, object]:
    session = Path(root)
    payload = local._read_json(session / "session-state.json")
    required = {
        "schema_version",
        "session_id",
        "clock_sha256",
        "source_link_sha256",
        "input_evidence_sha256",
        "base_model_provenance_sha256",
        "environment_preflight_sha256",
        "package_baseline_sha256",
        "operator_code_artifact_sha256",
        "repo_root_path_sha256",
        "session_root_path_sha256",
    }
    if set(payload) != required or payload.get("schema_version") != STATE_SCHEMA:
        raise RuntimeError("QLoRA session state schema drifted")
    clock = local._read_json(session / "session-clock.json")
    if local._sha256_file(session / "session-clock.json") != payload["clock_sha256"]:
        raise RuntimeError("QLoRA session clock drifted")
    if clock.get("session_id") != SESSION_ID or clock.get("window_seconds") != SESSION_WINDOW_SECONDS:
        raise RuntimeError("QLoRA session clock contract drifted")
    if local._boot_identity() != clock.get("boot_identity"):
        raise RuntimeError("OS boot identity changed during the QLoRA session")
    now = time.monotonic()
    if now < float(clock["started_monotonic"]):
        raise RuntimeError("monotonic clock moved backwards")
    if now > float(clock["deadline_monotonic"]) and not allow_expired:
        raise TimeoutError("fresh QLoRA session's immutable two-hour clock expired")
    artifacts = {
        "source-decision-link.json": "source_link_sha256",
        "input-evidence.json": "input_evidence_sha256",
        "base-model-provenance.json": "base_model_provenance_sha256",
        "environment-preflight.json": "environment_preflight_sha256",
        "package-baseline.json": "package_baseline_sha256",
        "operator-code.json": "operator_code_artifact_sha256",
    }
    for relative, key in artifacts.items():
        if local._sha256_file(session / relative) != payload[key]:
            raise RuntimeError(f"immutable QLoRA preflight artifact drifted: {relative}")
    repository = session.parents[4]
    if local._path_identity_sha256(repository) != payload["repo_root_path_sha256"]:
        raise RuntimeError("QLoRA repository root identity drifted")
    operator = local._read_json(session / "operator-code.json")
    if operator != _operator_code_identity(repository):
        raise RuntimeError("dated QLoRA operator code drifted after preflight")
    if local._path_identity_sha256(session) != payload["session_root_path_sha256"]:
        raise RuntimeError("QLoRA session root identity drifted")
    _ledger_rows(session)
    return payload


def _live_data_and_model_gate(paths: Mapping[str, Path]) -> tuple[dict[str, object], dict[str, object]]:
    for name in ("train", "validation", "contract"):
        path = paths[name]
        if not path.is_file() or path.is_symlink() or local._is_reparse_point(path):
            raise RuntimeError(f"canonical {name} input is missing or unsafe")
    contract_module = __import__(
        "src.model_adaptation.phase40_contract", fromlist=["preflight_phase40_inputs"]
    )
    contract = contract_module.preflight_phase40_inputs(
        paths["train"], paths["validation"], repo_root=paths["repo"]
    )
    input_evidence = local._split_evidence(contract)
    input_evidence["repo_root_path_sha256"] = local._path_identity_sha256(paths["repo"])
    if not local._same_path(local.EXTERNAL_QWEN_SNAPSHOT, local.EXTERNAL_QWEN_SNAPSHOT):
        raise AssertionError("unreachable model identity guard")
    local.validate_external_snapshot_identity(
        local.EXTERNAL_QWEN_SNAPSHOT, local.EXTERNAL_DOWNLOAD_MANIFEST
    )
    training = __import__("src.model_adaptation.training", fromlist=["build_qwen_base_model_provenance"])
    provenance = training.build_qwen_base_model_provenance(
        local.EXTERNAL_QWEN_SNAPSHOT,
        model_id=local.QWEN_MODEL_ID,
        model_revision=local.QWEN_REVISION,
        manifest_path=paths["session"] / "base-model-provenance.json",
    ).portable_manifest()
    local.validate_external_snapshot_identity(
        local.EXTERNAL_QWEN_SNAPSHOT, local.EXTERNAL_DOWNLOAD_MANIFEST
    )
    return input_evidence, provenance


def preflight(repo_root: Path, *, session_root: Path | None = None) -> dict[str, object]:
    paths = _expected_paths(repo_root)
    session = paths["session"] if session_root is None else Path(session_root)
    paths = _validate_fixed_session_root(paths["repo"], session)
    source_before = _secure_tree_snapshot(paths["source"], forbid_disposable=True)
    clock = _start_clock(paths["session"])
    try:
        source_link = build_source_decision_link(paths["source"])
        input_evidence, provenance = _live_data_and_model_gate(paths)
        package_baseline = local.resolve_package_baseline(paths["repo"])
        if package_baseline.get("bitsandbytes_present") is not True:
            raise RuntimeError("QLoRA preflight requires the verified bitsandbytes setup")
        environment = {
            "captured_utc": local._utc_now(),
            "torch": local.capture_torch_identity(),
            "bitsandbytes": local.capture_bitsandbytes_identity(),
            "resources": local.sample_parent_telemetry(None),
        }
        source_after = _secure_tree_snapshot(paths["source"], forbid_disposable=True)
        if source_before != source_after or source_link["source_tree"] != source_after.summary():
            raise RuntimeError("historical source changed during QLoRA preflight")
        link_path = local._write_immutable_json(
            paths["session"] / "source-decision-link.json", source_link
        )
        input_path = local._write_immutable_json(
            paths["session"] / "input-evidence.json", input_evidence
        )
        base_path = local._write_immutable_json(
            paths["session"] / "base-model-provenance.json", provenance
        )
        environment_path = local._write_immutable_json(
            paths["session"] / "environment-preflight.json", environment
        )
        baseline_path = local._write_immutable_json(
            paths["session"] / "package-baseline.json", package_baseline
        )
        operator_path = local._write_immutable_json(
            paths["session"] / "operator-code.json",
            _operator_code_identity(paths["repo"]),
        )
        state = {
            "schema_version": STATE_SCHEMA,
            "session_id": SESSION_ID,
            "clock_sha256": local._sha256_file(paths["session"] / "session-clock.json"),
            "source_link_sha256": local._sha256_file(link_path),
            "input_evidence_sha256": local._sha256_file(input_path),
            "base_model_provenance_sha256": local._sha256_file(base_path),
            "environment_preflight_sha256": local._sha256_file(environment_path),
            "package_baseline_sha256": local._sha256_file(baseline_path),
            "operator_code_artifact_sha256": local._sha256_file(operator_path),
            "repo_root_path_sha256": local._path_identity_sha256(paths["repo"]),
            "session_root_path_sha256": local._path_identity_sha256(paths["session"]),
        }
        state_path = local._write_immutable_json(
            paths["session"] / "session-state.json", state
        )
        stage_after = _secure_tree_snapshot(paths["source"], forbid_disposable=True)
        if source_before != stage_after:
            raise RuntimeError("historical source changed while QLoRA preflight artifacts were written")
        completed_utc = local._utc_now()
        completed_monotonic = time.monotonic()
        if completed_monotonic > float(clock["deadline_monotonic"]):
            raise TimeoutError("QLoRA preflight exceeded its fresh two-hour clock")
        _append_ledger(
            paths["session"],
            stage="preflight",
            artifact=state_path,
            timestamp_utc=completed_utc,
            monotonic_seconds=completed_monotonic,
            source_before=source_before.sha256,
            source_after=stage_after.sha256,
        )
        return {"status": "preflighted", "session_id": SESSION_ID, "window_seconds": 7200}
    except BaseException as exc:
        local._write_immutable_json(
            paths["session"] / "preflight-failure.json",
            {
                "schema_version": "phase40-qlora-session-preflight-failure-v1",
                "error_type": type(exc).__name__,
                "error": local._sanitize_log_text(str(exc)),
                "observed_utc": local._utc_now(),
                "clock_sha256": local._sha256_file(paths["session"] / "session-clock.json"),
            },
        )
        raise


def record_authority(repo_root: Path) -> dict[str, object]:
    paths = _expected_paths(repo_root)
    _state(paths["session"])
    _require_stages(paths["session"], ("preflight",))
    before = _guard_source(paths["session"], paths["source"])
    baseline = local._read_json(paths["session"] / "package-baseline.json")
    if baseline != local.resolve_package_baseline(paths["repo"]):
        raise RuntimeError("package setup receipt drifted since QLoRA preflight")
    if baseline.get("normalized_decision") != local.APPROVE_AUTHORITY:
        raise RuntimeError("QLoRA package authority was not approved")
    payload = {
        "schema_version": AUTHORITY_SCHEMA,
        "package": "bitsandbytes",
        "version": local.BITSANDBYTES_VERSION,
        "approved": True,
        "decision_text": local.APPROVE_AUTHORITY,
        "decision_source": "verified_preinstalled_setup_receipt",
        "setup_receipt_relative_path": baseline["setup_receipt_relative_path"],
        "setup_receipt_sha256": baseline["setup_receipt_sha256"],
        "source_tree_before_sha256": before.sha256,
        "source_tree_after_sha256": before.sha256,
        "recorded_utc": local._utc_now(),
        "recorded_monotonic": time.monotonic(),
    }
    path = local._write_immutable_json(paths["session"] / "package-authority.json", payload)
    qlora = paths["session"] / "qlora"
    qlora.mkdir(parents=False, exist_ok=False)
    local._write_immutable_bytes(qlora / "package-authority.json", path.read_bytes())
    after = _guard_source(paths["session"], paths["source"])
    _append_ledger(
        paths["session"],
        stage="record-authority",
        artifact=path,
        timestamp_utc=str(payload["recorded_utc"]),
        monotonic_seconds=float(payload["recorded_monotonic"]),
        source_before=before.sha256,
        source_after=after.sha256,
    )
    return payload


def verify_package(repo_root: Path) -> dict[str, object]:
    paths = _expected_paths(repo_root)
    _state(paths["session"])
    _require_stages(paths["session"], ("preflight", "record-authority"))
    before = _guard_source(paths["session"], paths["source"])
    environment = local._read_json(paths["session"] / "environment-preflight.json")
    torch_identity = local.capture_torch_identity()
    bnb_identity = local.capture_bitsandbytes_identity()
    baseline_unchanged = (
        local.resolve_package_baseline(paths["repo"])
        == local._read_json(paths["session"] / "package-baseline.json")
    )
    status = "verified"
    failure: str | None = None
    if torch_identity != environment.get("torch"):
        status, failure = "failed", "Torch identity drifted from QLoRA preflight"
    elif bnb_identity != environment.get("bitsandbytes"):
        status, failure = "failed", "bitsandbytes identity drifted from QLoRA preflight"
    elif bnb_identity.get("version") != local.BITSANDBYTES_VERSION:
        status, failure = "failed", "bitsandbytes version is not exactly 0.50.1"
    elif bnb_identity.get("cuda_kernel_available") is not True:
        status, failure = "failed", "bitsandbytes NF4 CUDA kernel proof failed"
    elif not baseline_unchanged:
        status, failure = "failed", "package baseline drifted"
    payload = {
        "schema_version": PACKAGE_SCHEMA,
        "status": status,
        "failure_reason": failure,
        "torch": torch_identity,
        "bitsandbytes": bnb_identity,
        "torch_identity_unchanged": torch_identity == environment.get("torch"),
        "bitsandbytes_identity_unchanged": bnb_identity == environment.get("bitsandbytes"),
        "package_baseline_unchanged": baseline_unchanged,
        "source_tree_before_sha256": before.sha256,
        "source_tree_after_sha256": before.sha256,
        "verified_utc": local._utc_now(),
        "verified_monotonic": time.monotonic(),
    }
    path = local._write_immutable_json(paths["session"] / "package-runtime.json", payload)
    local._write_immutable_bytes(
        paths["session"] / "qlora/package-runtime.json", path.read_bytes()
    )
    after = _guard_source(paths["session"], paths["source"])
    _append_ledger(
        paths["session"],
        stage="verify-package",
        artifact=path,
        timestamp_utc=str(payload["verified_utc"]),
        monotonic_seconds=float(payload["verified_monotonic"]),
        source_before=before.sha256,
        source_after=after.sha256,
    )
    if failure is not None:
        raise RuntimeError(failure)
    return payload


def _safe_runtime_file(path: Path, runtime: Path) -> Path:
    candidate = local._lexical_absolute(path)
    root = local._lexical_absolute(runtime)
    if not candidate.is_file() or candidate.is_symlink() or local._is_reparse_point(candidate):
        raise RuntimeError("child evidence file is missing or unsafe")
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise RuntimeError("child evidence escaped the disposable runtime") from exc
    return candidate


def _ensure_terminal_telemetry(stage_root: Path, stop_reason: str) -> None:
    path = Path(stage_root) / "telemetry.jsonl"
    if path.is_file():
        rows = local._load_jsonl(path)
        if rows[-1].get("terminal") is True:
            return
        recorder = local.TelemetryRecorder(path, stage="qlora")
        recorder.sequence_id = len(rows)
    else:
        recorder = local.TelemetryRecorder(path, stage="qlora")
    recorder.finish(
        monotonic_seconds=time.monotonic(),
        timestamp_utc=local._utc_now(),
        values=local.null_telemetry_values("controller terminalization"),
        stop_reason=stop_reason,
    )


def _request_stop(
    process: subprocess.Popen[str], runtime: Path, recorder: local.TelemetryRecorder,
    child_events: Path, reason: str, deadline: float,
) -> None:
    stop = runtime / "stop-request.json"
    if not stop.exists():
        stop.write_text('{"stop":true}\n', encoding="ascii")
    grace = min(deadline, time.monotonic() + 15.0)
    while process.poll() is None and time.monotonic() < grace:
        time.sleep(min(TELEMETRY_INTERVAL_SECONDS, max(0.0, grace - time.monotonic())))
        if process.poll() is None and time.monotonic() < deadline:
            recorder.record(
                monotonic_seconds=time.monotonic(),
                timestamp_utc=local._utc_now(),
                values=local.sample_parent_telemetry(
                    process.pid, child_events_path=child_events
                ),
            )
    if process.poll() is None:
        process.terminate()
        terminate_deadline = min(deadline, time.monotonic() + 10.0)
        while process.poll() is None and time.monotonic() < terminate_deadline:
            time.sleep(
                min(
                    TELEMETRY_INTERVAL_SECONDS,
                    max(0.0, terminate_deadline - time.monotonic()),
                )
            )
            if process.poll() is None and time.monotonic() < deadline:
                recorder.record(
                    monotonic_seconds=time.monotonic(),
                    timestamp_utc=local._utc_now(),
                    values=local.sample_parent_telemetry(
                        process.pid, child_events_path=child_events
                    ),
                )
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5.0)


def _execute_real_child(repo_root: Path, session_root: Path, stage_root: Path) -> ChildExecution:
    runtime = stage_root / "runtime"
    control = {
        "session_root": os.fspath(local._lexical_absolute(session_root)),
        "repo_root": os.fspath(local._lexical_absolute(repo_root)),
        "stage_root": os.fspath(local._lexical_absolute(stage_root)),
        "train_split": os.fspath(local._lexical_absolute(repo_root / local.TRAIN_RELATIVE_PATH)),
        "val_split": os.fspath(local._lexical_absolute(repo_root / local.VAL_RELATIVE_PATH)),
        "base_model_path": os.fspath(local._lexical_absolute(local.EXTERNAL_QWEN_SNAPSHOT)),
        "run_id": RUN_ID,
        "adaptation_mode": "qlora",
    }
    control_path = runtime / "child-control.json"
    control_path.write_text(json.dumps(control, sort_keys=True), encoding="utf-8")
    stdout_path = runtime / "child-stdout.log"
    stderr_path = runtime / "child-stderr.log"
    command = [sys.executable, "-m", MODULE_NAME, "--child-control", os.fspath(control_path)]
    environment = dict(os.environ)
    environment.update(
        {"HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "HF_DATASETS_OFFLINE": "1"}
    )
    recorder = local.TelemetryRecorder(stage_root / "telemetry.jsonl", stage="qlora")
    child_events = local._local_child_events_path(stage_root, "qlora")
    clock = local._read_json(session_root / "session-clock.json")
    deadline = float(clock["deadline_monotonic"])
    process: subprocess.Popen[str] | None = None
    job_handle: int | None = None
    stop_reason = "parent_controller_error"
    latest = local.null_telemetry_values("not sampled")
    try:
        with stdout_path.open("w", encoding="utf-8") as stdout, stderr_path.open(
            "w", encoding="utf-8"
        ) as stderr:
            process = subprocess.Popen(
                command,
                stdout=stdout,
                stderr=stderr,
                text=True,
                shell=False,
                cwd=os.fspath(repo_root),
                env=environment,
            )
            job_handle = local._assign_kill_on_close_job(process)
            while process.poll() is None:
                now = time.monotonic()
                latest = local.sample_parent_telemetry(
                    process.pid, child_events_path=child_events
                )
                recorder.record(
                    monotonic_seconds=now,
                    timestamp_utc=local._utc_now(),
                    values=latest,
                )
                if deadline - now <= 15.0:
                    stop_reason = "global_deadline"
                    _request_stop(process, runtime, recorder, child_events, stop_reason, deadline)
                    break
                time.sleep(TELEMETRY_INTERVAL_SECONDS)
            if process.returncode == 0 and stop_reason == "parent_controller_error":
                stop_reason = "evidence_target_reached"
            elif stop_reason == "parent_controller_error":
                stop_reason = "child_error"
    except KeyboardInterrupt:
        stop_reason = "parent_interrupted"
        if process is not None and process.poll() is None:
            _request_stop(process, runtime, recorder, child_events, stop_reason, deadline)
    except BaseException:
        stop_reason = "parent_controller_error"
        if process is not None and process.poll() is None:
            _request_stop(process, runtime, recorder, child_events, stop_reason, deadline)
        raise
    finally:
        try:
            try:
                latest = local.sample_parent_telemetry(
                    None if process is None else process.pid,
                    child_events_path=child_events,
                )
            except BaseException:
                latest = local.null_telemetry_values("terminal sample failed")
            recorder.finish(
                monotonic_seconds=time.monotonic(),
                timestamp_utc=local._utc_now(),
                values=latest,
                stop_reason=stop_reason,
            )
        finally:
            local._close_windows_handle(job_handle)
    return ChildExecution(-1 if process is None else int(process.returncode), stop_reason)


def _clear_runtime_readonly(runtime: Path) -> None:
    root = Path(runtime)
    if not root.is_dir() or root.is_symlink() or local._is_reparse_point(root):
        raise RuntimeError("runtime cleanup boundary is not one real directory")
    discovered: list[Path] = []
    for current_raw, directory_names, file_names in os.walk(root, topdown=True):
        current = Path(current_raw)
        if current.is_symlink() or local._is_reparse_point(current):
            raise RuntimeError("runtime cleanup boundary contains a link/reparse point")
        for name in (*directory_names, *file_names):
            candidate = current / name
            if candidate.is_symlink() or local._is_reparse_point(candidate):
                raise RuntimeError("runtime cleanup boundary contains a link/reparse point")
            discovered.append(candidate)
    for candidate in reversed(discovered):
        mode = stat.S_IRUSR | stat.S_IWUSR
        if candidate.is_dir():
            mode |= stat.S_IXUSR
        os.chmod(candidate, mode)
    os.chmod(root, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)


def _resource_peaks(rows: Sequence[Mapping[str, object]]) -> dict[str, object]:
    keys = (
        "system_ram_used_bytes", "system_ram_available_bytes", "process_rss_bytes",
        "torch_allocated_bytes", "torch_reserved_bytes", "torch_peak_allocated_bytes",
        "torch_peak_reserved_bytes", "device_vram_used_mib", "device_vram_free_mib",
        "gpu_utilization_percent", "gpu_temperature_c", "gpu_power_w",
    )
    result: dict[str, object] = {}
    for key in keys:
        values = [
            float(row[key]) for row in rows
            if isinstance(row.get(key), (int, float)) and not isinstance(row.get(key), bool)
        ]
        result[("minimum_" if key.endswith(("available_bytes", "free_mib")) else "peak_") + key] = (
            (min(values) if key.endswith(("available_bytes", "free_mib")) else max(values))
            if values else None
        )
    return result


def run_qlora(
    repo_root: Path,
    *,
    executor: Callable[[Path, Path, Path], ChildExecution] = _execute_real_child,
) -> dict[str, object]:
    paths = _expected_paths(repo_root)
    _state(paths["session"])
    _require_stages(
        paths["session"], ("preflight", "record-authority", "verify-package")
    )
    package = local._read_json(paths["session"] / "package-runtime.json")
    if package.get("status") != "verified":
        raise RuntimeError("QLoRA cannot start without a verified package gate")
    before = _guard_source(paths["session"], paths["source"])
    qlora = paths["session"] / "qlora"
    if {path.name for path in qlora.iterdir()} != {
        "package-authority.json", "package-runtime.json"
    }:
        raise FileExistsError("QLoRA stage contains unexpected pre-existing artifacts")
    runtime = qlora / "runtime"
    runtime.mkdir(parents=False, exist_ok=False)
    execution: ChildExecution | None = None
    controller_error: BaseException | None = None
    try:
        execution = executor(paths["repo"], paths["session"], qlora)
    except BaseException as exc:
        controller_error = exc
        _ensure_terminal_telemetry(qlora, "parent_controller_error")

    retained_events: Path | None = None
    partial: dict[str, object] | None = None
    proof_path: Path | None = None
    proof: dict[str, object] | None = None
    result: dict[str, object] = {}
    postprocess_error: BaseException | None = None
    raw_hashes: dict[str, str] = {}
    sanitized_hashes: dict[str, str] = {}
    sanitized_text: dict[str, str] = {}
    try:
        result_path = runtime / "child-result.json"
        if result_path.is_file():
            result = local._read_json_allow_absolute(result_path)
        retained_events, partial = local._retain_child_events(
            stage_root=qlora, runtime=runtime, stage="qlora", result=result
        )
        proof_path, proof = local._retain_prestep_quantization_proof(
            stage_root=qlora, runtime=runtime, result=result
        )
    except BaseException as exc:
        postprocess_error = exc
    for stream in ("stdout", "stderr"):
        raw = runtime / f"child-{stream}.log"
        content = raw.read_text(encoding="utf-8", errors="replace") if raw.is_file() else ""
        if raw.is_file():
            raw_hashes[stream] = local._sha256_file(raw)
        sanitized_text[stream] = local._sanitize_log_text(content)
        retained = local._write_immutable_bytes(
            qlora / f"child-{stream}.sanitized.log",
            sanitized_text[stream].encode("utf-8"),
        )
        sanitized_hashes[stream] = local._sha256_file(retained)
    _clear_runtime_readonly(runtime)
    receipt = local.discard_stage_runtime(qlora, run_id=RUN_ID)
    after = _guard_source(paths["session"], paths["source"])
    telemetry = local.verify_telemetry(qlora / "telemetry.jsonl", expected_stage="qlora")
    terminal_reason = str(telemetry[-1]["stop_reason"])
    oom_kind = local._detect_memory_oom_kind(sanitized_text.get("stderr"))
    if controller_error is not None or postprocess_error is not None:
        status = "error"
    elif execution is not None and execution.returncode == 0:
        status = "measured"
    elif oom_kind is not None:
        status = "oom"
    elif terminal_reason == "global_deadline":
        status = "timeout"
    elif terminal_reason == "parent_interrupted":
        status = "interrupted"
    else:
        status = "error"

    measurement: dict[str, object] | None = None
    proof_validated: dict[str, object] | None = None
    validation_error: BaseException | None = None
    if status == "measured":
        try:
            if retained_events is None or proof_path is None or proof is None:
                raise RuntimeError("successful QLoRA child lacks event/proof evidence")
            measurement = local.validate_qlora_events(retained_events)
            proof_validated = local.validate_genuine_qlora_proof(proof)
        except BaseException as exc:
            validation_error = exc
            status = "error"
    failure = controller_error or postprocess_error or validation_error
    if failure is not None:
        local._write_immutable_json(
            qlora / "controller-failure.json",
            {
                "schema_version": CONTROLLER_FAILURE_SCHEMA,
                "error_type": type(failure).__name__,
                "error": local._sanitize_log_text(str(failure)),
                "runtime_absent": not runtime.exists(),
                "observed_utc": local._utc_now(),
            },
        )
    payload: dict[str, object] = {
        "schema_version": OUTCOME_SCHEMA,
        "session_id": SESSION_ID,
        "run_id": RUN_ID,
        "status": status,
        "stop_reason": terminal_reason,
        "measured_target_reached": status == "measured",
        "warmup_optimizer_steps_required": 5,
        "measured_optimizer_steps_required": 40,
        "planned_full_optimizer_steps": 1245,
        "telemetry": "qlora/telemetry.jsonl",
        "telemetry_sha256": local._sha256_file(qlora / "telemetry.jsonl"),
        "resource_peaks": _resource_peaks(telemetry),
        "raw_child_log_sha256": raw_hashes,
        "sanitized_child_log_sha256": sanitized_hashes,
        "discard_receipt": receipt,
        "source_tree_before_sha256": before.sha256,
        "source_tree_after_sha256": after.sha256,
        "completed_utc": local._utc_now(),
        "completed_monotonic": min(
            time.monotonic(),
            float(local._read_json(paths["session"] / "session-clock.json")["deadline_monotonic"]),
        ),
        "post_deadline_sealing_seconds": max(
            0.0,
            time.monotonic()
            - float(local._read_json(paths["session"] / "session-clock.json")["deadline_monotonic"]),
        ),
        "oom_kind": oom_kind,
        "measurement": measurement,
        "proof": proof_validated,
        "controller_failure": (
            "qlora/controller-failure.json" if failure is not None else None
        ),
    }
    if retained_events is not None:
        payload.update(
            {
                "optimizer_events": "qlora/optimizer-events.jsonl",
                "optimizer_events_sha256": local._sha256_file(retained_events),
                "partial_event_summary": partial,
            }
        )
    if proof_path is not None:
        payload.update(
            {
                "quantization_proof": "qlora/quantization-proof.json",
                "quantization_proof_sha256": local._sha256_file(proof_path),
            }
        )
    outcome_path = local._write_immutable_json(qlora / "outcome.json", payload)
    local._write_immutable_bytes(qlora / "run-evidence.json", outcome_path.read_bytes())
    final_source = _guard_source(paths["session"], paths["source"])
    _append_ledger(
        paths["session"],
        stage="qlora",
        artifact=outcome_path,
        timestamp_utc=str(payload["completed_utc"]),
        monotonic_seconds=float(payload["completed_monotonic"]),
        source_before=before.sha256,
        source_after=final_source.sha256,
    )
    return payload


def _manifest_inventory(root: Path) -> list[dict[str, object]]:
    snapshot = _secure_tree_snapshot(root, forbid_disposable=True)
    return [
        row for row in snapshot.files
        if row["relative_path"] not in {"session-manifest.json", "verification.json"}
    ]


def finalize(repo_root: Path) -> dict[str, object]:
    paths = _expected_paths(repo_root)
    _state(paths["session"], allow_expired=True)
    _require_stages(
        paths["session"],
        ("preflight", "record-authority", "verify-package", "qlora"),
    )
    before = _guard_source(paths["session"], paths["source"])
    outcome = local._read_json(paths["session"] / "qlora/outcome.json")
    local.verify_stage_discard(paths["session"] / "qlora", outcome["discard_receipt"])
    if (paths["session"] / "qlora/runtime").exists():
        raise RuntimeError("QLoRA runtime survived its mandatory discard")
    marker = {
        "schema_version": FINALIZE_SCHEMA,
        "session_id": SESSION_ID,
        "qlora_status": outcome.get("status"),
        "qlora_stop_reason": outcome.get("stop_reason"),
        "measured_target_reached": outcome.get("measured_target_reached") is True,
        "routing": (
            "port_identical_controls_to_colab_full_training"
            if outcome.get("status") == "measured"
            else "do_not_claim_eta_or_start_full_training_without_review"
        ),
        "projected_local_runtime_seconds": (
            outcome.get("measurement", {}).get("projected_local_runtime_seconds")
            if isinstance(outcome.get("measurement"), dict)
            else None
        ),
        "source_tree_before_sha256": before.sha256,
        "source_tree_after_sha256": before.sha256,
        "finalized_utc": local._utc_now(),
        "finalized_monotonic": min(
            time.monotonic(),
            float(local._read_json(paths["session"] / "session-clock.json")["deadline_monotonic"]),
        ),
    }
    marker_path = local._write_immutable_json(
        paths["session"] / "finalize-marker.json", marker
    )
    after = _guard_source(paths["session"], paths["source"])
    _append_ledger(
        paths["session"],
        stage="finalize",
        artifact=marker_path,
        timestamp_utc=str(marker["finalized_utc"]),
        monotonic_seconds=float(marker["finalized_monotonic"]),
        source_before=before.sha256,
        source_after=after.sha256,
    )
    inventory = _manifest_inventory(paths["session"])
    manifest = {
        "schema_version": MANIFEST_SCHEMA,
        "session_id": SESSION_ID,
        "historical_source_read_only": True,
        "source_tree_sha256": before.sha256,
        "stage_sequence": list(LEDGER_STAGES),
        "qlora_status": outcome.get("status"),
        "qlora_stop_reason": outcome.get("stop_reason"),
        "measured_target_reached": outcome.get("measured_target_reached") is True,
        "artifact_inventory_algorithm": TREE_ALGORITHM,
        "artifacts": inventory,
        "artifact_count": len(inventory),
    }
    local._write_immutable_json(paths["session"] / "session-manifest.json", manifest)
    return manifest


def verify(repo_root: Path) -> dict[str, object]:
    paths = _expected_paths(repo_root)
    _state(paths["session"], allow_expired=True)
    _require_stages(paths["session"], LEDGER_STAGES)
    before = _guard_source(paths["session"], paths["source"])
    manifest = local._read_json(paths["session"] / "session-manifest.json")
    if manifest.get("schema_version") != MANIFEST_SCHEMA or manifest.get("session_id") != SESSION_ID:
        raise RuntimeError("QLoRA session manifest identity drifted")
    if manifest.get("source_tree_sha256") != before.sha256:
        raise RuntimeError("QLoRA manifest source link drifted")
    inventory = _manifest_inventory(paths["session"])
    if manifest.get("artifacts") != inventory or manifest.get("artifact_count") != len(inventory):
        raise RuntimeError("QLoRA session artifact inventory drifted")
    outcome = local._read_json(paths["session"] / "qlora/outcome.json")
    alias = paths["session"] / "qlora/run-evidence.json"
    if alias.read_bytes() != (paths["session"] / "qlora/outcome.json").read_bytes():
        raise RuntimeError("QLoRA outcome alias drifted")
    local.verify_stage_discard(paths["session"] / "qlora", outcome["discard_receipt"])
    if outcome.get("status") == "measured":
        if outcome.get("measured_target_reached") is not True:
            raise RuntimeError("measured QLoRA outcome lost its exact target proof")
        measurement = local.validate_qlora_events(
            paths["session"] / str(outcome["optimizer_events"])
        )
        proof = local.validate_genuine_qlora_proof(
            local._read_json(paths["session"] / str(outcome["quantization_proof"]))
        )
        if measurement != outcome.get("measurement") or proof != outcome.get("proof"):
            raise RuntimeError("QLoRA measurement/proof drifted")
    elif outcome.get("measurement") is not None:
        raise RuntimeError("partial/failed QLoRA outcome must not publish an ETA")
    after = _guard_source(paths["session"], paths["source"])
    if before != after:
        raise RuntimeError("historical source changed during final verification")
    return {
        "verified": True,
        "session_id": SESSION_ID,
        "status": outcome.get("status"),
        "stop_reason": outcome.get("stop_reason"),
        "source_tree_sha256": after.sha256,
    }


def _child_main(control_path: Path) -> int:
    control = local._read_json_allow_absolute(control_path)
    required = {
        "session_root", "repo_root", "stage_root", "train_split", "val_split",
        "base_model_path", "run_id", "adaptation_mode",
    }
    if set(control) != required or control.get("run_id") != RUN_ID or control.get("adaptation_mode") != "qlora":
        raise RuntimeError("QLoRA child control identity is invalid")
    repo = _repo_root(Path(str(control["repo_root"])))
    paths = _expected_paths(repo)
    if not local._same_path(Path(str(control["session_root"])), paths["session"]):
        raise RuntimeError("QLoRA child session root differs from fixed authority")
    if not local._same_path(Path(str(control["stage_root"])), paths["session"] / "qlora"):
        raise RuntimeError("QLoRA child stage root differs from fixed authority")
    if not local._same_path(Path(str(control["train_split"])), paths["train"]):
        raise RuntimeError("QLoRA child training split differs from canonical allowlist")
    if not local._same_path(Path(str(control["val_split"])), paths["validation"]):
        raise RuntimeError("QLoRA child validation split differs from canonical allowlist")
    if not local._same_path(Path(str(control["base_model_path"])), local.EXTERNAL_QWEN_SNAPSHOT):
        raise RuntimeError("QLoRA child base model differs from pinned local snapshot")
    _state(paths["session"])
    _require_stages(paths["session"], ("preflight", "record-authority", "verify-package"))
    _guard_source(paths["session"], paths["source"])
    package = local._read_json(paths["session"] / "package-runtime.json")
    if local.capture_torch_identity() != package.get("torch"):
        raise RuntimeError("Torch identity drifted after the package gate")
    if local.capture_bitsandbytes_identity() != package.get("bitsandbytes"):
        raise RuntimeError("bitsandbytes identity drifted after the package gate")
    local.validate_external_snapshot_identity(
        local.EXTERNAL_QWEN_SNAPSHOT, local.EXTERNAL_DOWNLOAD_MANIFEST
    )
    contract_module = __import__(
        "src.model_adaptation.phase40_contract", fromlist=["preflight_phase40_inputs"]
    )
    contract = contract_module.preflight_phase40_inputs(
        paths["train"], paths["validation"], repo_root=repo
    )
    if local._split_evidence(contract) != {
        key: value
        for key, value in local._read_json(paths["session"] / "input-evidence.json").items()
        if key in {"train", "validation"}
    }:
        raise RuntimeError("QLoRA child input identity drifted after preflight")
    training = __import__("src.model_adaptation.training", fromlist=["build_phase40_local_decision_config"])
    config = training.build_phase40_local_decision_config(
        adaptation_mode="qlora",
        train_split_path=paths["train"],
        val_split_path=paths["validation"],
        base_model_path=local.EXTERNAL_QWEN_SNAPSHOT,
        decision_stage_root=paths["session"] / "qlora",
        run_id=RUN_ID,
    )
    result = training.run_phase40_local_decision_child(config, data_contract=contract)
    proof = result.get("quantization_proof")
    proof_payload = (
        None
        if proof is None
        else {key: getattr(value, "value", value) for key, value in asdict(proof).items()}
    )
    summary = result.get("resource_summary")
    payload = {
        "events_path": os.fspath(result.get("events_path")),
        "quantization_proof": proof_payload,
        "retained_optimizer_steps": getattr(summary, "retained_optimizer_steps", 0),
        "losses_finite": True,
    }
    runtime = paths["session"] / "qlora/runtime"
    (runtime / "child-result.json").write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True), encoding="utf-8"
    )
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "stage",
        nargs="?",
        choices=("preflight", "record-authority", "verify-package", "qlora", "finalize", "verify"),
    )
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--child-control", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.child_control is not None:
            if args.stage is not None:
                raise ValueError("internal child control cannot be combined with an operator stage")
            return _child_main(args.child_control)
        if args.stage is None:
            raise ValueError("one operator stage is required")
        handlers = {
            "preflight": preflight,
            "record-authority": record_authority,
            "verify-package": verify_package,
            "qlora": run_qlora,
            "finalize": finalize,
            "verify": verify,
        }
        result = handlers[args.stage](args.repo_root)
    except (ImportError, OSError, RuntimeError, TypeError, ValueError, TimeoutError) as exc:
        print(f"Phase 40 dated QLoRA session refused: {local._sanitize_log_text(str(exc))}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
