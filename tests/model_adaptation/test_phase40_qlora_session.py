from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
import subprocess
import sys
import time

import pytest

from src.model_adaptation import phase40_local_experiment as local
from src.model_adaptation import phase40_qlora_session as session


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    for row in rows:
        local._append_jsonl(path, row)


def _events() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []

    def add(kind: str, step: int, second: int, values: dict[str, object]) -> None:
        rows.append(
            {
                "schema_version": "phase40-run-event-v1",
                "sequence_id": len(rows),
                "source_run_id": session.RUN_ID,
                "run_kind": "probe",
                "event_kind": kind,
                "timestamp_utc": f"2026-08-25T01:00:{second:02d}Z",
                "optimizer_step": step,
                "epoch": step / 45,
                "trainer_values": values,
            }
        )

    add("run_start", 0, 0, {"callback_event_kind": "run_start", "run_kind": "probe"})
    for step in range(1, 46):
        add(
            "step_timing",
            step,
            step,
            {
                "callback_event_kind": "optimizer_step",
                "run_kind": "probe",
                "epoch_observed": True,
                "duration_seconds": 1.0 + (step % 4) / 10,
                "is_warmup": step <= 5,
                "examples": 4,
                "tokens": 1024,
                "allocated_bytes": 5000,
                "reserved_bytes": 6000,
                "peak_allocated_bytes": 7000,
                "peak_reserved_bytes": 8000,
            },
        )
    add(
        "evaluation",
        45,
        46,
        {
            "callback_event_kind": "evaluation",
            "run_kind": "probe",
            "duration_seconds": 12.0,
            "eval_runtime": 12.0,
        },
    )
    add(
        "checkpoint",
        45,
        47,
        {
            "callback_event_kind": "checkpoint",
            "run_kind": "probe",
            "duration_seconds": 3.0,
            "measurement_scope": "isolated",
        },
    )
    add("run_end", 45, 48, {"callback_event_kind": "run_end", "run_kind": "probe"})
    return rows


def _proof() -> dict[str, object]:
    return {
        "requested_mode": "qlora",
        "resolved_mode": "4bit-qlora",
        "bitsandbytes_version": "0.50.1",
        "load_in_4bit": True,
        "nf4": True,
        "double_quantization": True,
        "is_loaded_in_4bit": True,
        "linear4bit_modules": 42,
        "kbit_preparation_applied": True,
        "base_weights_frozen": True,
        "adapter_only_trainables": True,
        "adapter_trainable_count": 14,
        "backward_with_adapter_gradients": True,
        "adapter_gradient_finite_count": 14,
        "adapter_gradient_nonzero_count": 12,
    }


def _seed_repo(tmp_path: Path, monkeypatch, name: str = "repo") -> tuple[Path, dict[str, object], dict[str, object]]:
    repo = tmp_path / name
    repo.mkdir()
    operator = repo / session.OPERATOR_CODE_RELATIVE_PATH
    operator.parent.mkdir(parents=True)
    operator.write_bytes(Path(session.__file__).read_bytes())

    paths = session._expected_paths(repo)
    source = paths["source"]
    source.mkdir(parents=True)
    source_artifact = local._write_immutable_json(source / "artifact.json", {"sealed": True})
    source_snapshot = session._secure_tree_snapshot(source, forbid_disposable=True)

    root = paths["session"]
    root.mkdir(parents=True)
    now = time.monotonic()
    clock = {
        "schema_version": session.CLOCK_SCHEMA,
        "session_id": session.SESSION_ID,
        "started_utc": local._utc_now(),
        "started_monotonic": now,
        "deadline_monotonic": now + session.SESSION_WINDOW_SECONDS,
        "window_seconds": session.SESSION_WINDOW_SECONDS,
        "boot_identity": local._boot_identity(),
        "session_root_path_sha256": local._path_identity_sha256(root),
    }
    clock_path = local._write_immutable_json(root / "session-clock.json", clock)
    link = {
        "schema_version": session.SOURCE_LINK_SCHEMA,
        "source_root_relative_path": session.SOURCE_ROOT_RELATIVE_PATH.as_posix(),
        "historical_source_read_only": True,
        "source_tree": source_snapshot.summary(),
        "required_artifact_sha256": {
            "artifact.json": local._sha256_file(source_artifact)
        },
    }
    link_path = local._write_immutable_json(root / "source-decision-link.json", link)
    input_path = local._write_immutable_json(root / "input-evidence.json", {"train": {}, "validation": {}})
    base_path = local._write_immutable_json(root / "base-model-provenance.json", {"model": "pinned"})
    torch_identity = {
        "distribution": "torch",
        "version": "2.12.0+cu132",
        "cuda_version": "13.2",
        "module_path_sha256": "1" * 64,
        "record_sha256": "2" * 64,
    }
    bnb_identity = {
        "version": "0.50.1",
        "cuda_kernel_available": True,
        "nf4_roundtrip_finite": True,
    }
    environment_path = local._write_immutable_json(
        root / "environment-preflight.json",
        {"torch": torch_identity, "bitsandbytes": bnb_identity},
    )
    baseline = {
        "bitsandbytes_present": True,
        "setup_receipt_relative_path": local.PACKAGE_SETUP_RECEIPT_RELATIVE_PATH.as_posix(),
        "setup_receipt_sha256": "3" * 64,
        "normalized_decision": local.APPROVE_AUTHORITY,
        "decision_was_normalized": True,
        "authority_source": local.PACKAGE_SETUP_AUTHORITY_SOURCE,
        "authority_source_sha256": "4" * 64,
    }
    baseline_path = local._write_immutable_json(root / "package-baseline.json", baseline)
    operator_path = local._write_immutable_json(
        root / "operator-code.json", session._operator_code_identity(repo)
    )
    state = {
        "schema_version": session.STATE_SCHEMA,
        "session_id": session.SESSION_ID,
        "clock_sha256": local._sha256_file(clock_path),
        "source_link_sha256": local._sha256_file(link_path),
        "input_evidence_sha256": local._sha256_file(input_path),
        "base_model_provenance_sha256": local._sha256_file(base_path),
        "environment_preflight_sha256": local._sha256_file(environment_path),
        "package_baseline_sha256": local._sha256_file(baseline_path),
        "operator_code_artifact_sha256": local._sha256_file(operator_path),
        "repo_root_path_sha256": local._path_identity_sha256(repo),
        "session_root_path_sha256": local._path_identity_sha256(root),
    }
    state_path = local._write_immutable_json(root / "session-state.json", state)
    session._append_ledger(
        root,
        stage="preflight",
        artifact=state_path,
        timestamp_utc=local._utc_now(),
        monotonic_seconds=now + 0.1,
        source_before=source_snapshot.sha256,
        source_after=source_snapshot.sha256,
    )
    monkeypatch.setattr(local, "resolve_package_baseline", lambda _repo: dict(baseline))
    monkeypatch.setattr(local, "capture_torch_identity", lambda: dict(torch_identity))
    monkeypatch.setattr(local, "capture_bitsandbytes_identity", lambda: dict(bnb_identity))
    return repo, torch_identity, bnb_identity


def _package_ready(repo: Path) -> None:
    session.record_authority(repo)
    session.verify_package(repo)


def _successful_executor(_repo: Path, _root: Path, stage: Path) -> session.ChildExecution:
    runtime = stage / "runtime"
    recorder = local.TelemetryRecorder(stage / "telemetry.jsonl", stage="qlora")
    now = time.monotonic()
    values = local.null_telemetry_values("fake")
    values.update(
        {
            "device_vram_total_mib": 8151,
            "device_vram_used_mib": 6200,
            "device_vram_free_mib": 1951,
            "gpu_utilization_percent": 90,
        }
    )
    recorder.record(monotonic_seconds=now, timestamp_utc=local._utc_now(), values=values)
    recorder.finish(
        monotonic_seconds=now + 1,
        timestamp_utc=local._utc_now(),
        values=values,
        stop_reason="evidence_target_reached",
    )
    events = local._local_child_events_path(stage, "qlora")
    events.parent.mkdir(parents=True)
    _write_jsonl(events, _events())
    proof = _proof()
    local._write_immutable_json(runtime / "quantization-proof-prestep.json", proof)
    (runtime / "child-stdout.log").write_text("training complete\n", encoding="utf-8")
    (runtime / "child-stderr.log").write_text("", encoding="utf-8")
    (runtime / "child-result.json").write_text(
        json.dumps({"events_path": str(events.resolve()), "quantization_proof": proof}),
        encoding="utf-8",
    )
    return session.ChildExecution(0, "evidence_target_reached")


def _oom_executor(_repo: Path, _root: Path, stage: Path) -> session.ChildExecution:
    runtime = stage / "runtime"
    recorder = local.TelemetryRecorder(stage / "telemetry.jsonl", stage="qlora")
    recorder.finish(
        monotonic_seconds=time.monotonic(),
        timestamp_utc=local._utc_now(),
        values=local.null_telemetry_values("fake oom"),
        stop_reason="child_error",
    )
    (runtime / "child-stdout.log").write_text("", encoding="utf-8")
    (runtime / "child-stderr.log").write_text(
        "torch.cuda.OutOfMemoryError: CUDA out of memory\n", encoding="utf-8"
    )
    return session.ChildExecution(1, "child_error")


def test_source_link_accepts_expired_history_without_loading_live_clock(
    tmp_path: Path, monkeypatch
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    for relative in session.SOURCE_REQUIRED_ARTIFACTS:
        path = source / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = (
            {"status": "error", "stop_reason": "child_error"}
            if relative == "lora/outcome.json"
            else {
                "status": "error",
                "stop_reason": "parent_controller_error",
                "retained_optimizer_steps": 26,
                "measured_target_reached": False,
            }
            if relative.endswith("/outcome.json")
            else {"sealed": True}
        )
        local._write_immutable_json(path, payload)
    monkeypatch.setattr(
        local, "_read_state_unchecked", lambda _root: SimpleNamespace(experiment_id="expired-source")
    )
    monkeypatch.setattr(
        local,
        "_ledger_entries",
        lambda _root: [{"stage": stage} for stage in session.SOURCE_STAGES],
    )
    link = session.build_source_decision_link(source)
    assert link["source_clock_may_be_expired"] is True
    assert link["historical_source_read_only"] is True
    assert link["source_stages"] == list(session.SOURCE_STAGES)


def test_source_tree_mutation_and_reparse_fail_closed(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "source"
    source.mkdir()
    artifact = local._write_immutable_json(source / "artifact.json", {"value": 1})
    snapshot = session._secure_tree_snapshot(source, forbid_disposable=True)
    root = tmp_path / "session"
    root.mkdir()
    local._write_immutable_json(
        root / "source-decision-link.json",
        {
            "source_tree": snapshot.summary(),
            "required_artifact_sha256": {"artifact.json": local._sha256_file(artifact)},
        },
    )
    artifact.write_text('{"value":2}\n', encoding="utf-8")
    with pytest.raises(RuntimeError, match="drifted"):
        session._guard_source(root, source)

    unsafe = source / "unsafe"
    unsafe.mkdir()
    original = local._is_reparse_point
    monkeypatch.setattr(
        local,
        "_is_reparse_point",
        lambda path: Path(path).name == "unsafe" or original(Path(path)),
    )
    with pytest.raises(RuntimeError, match="reparse"):
        session._secure_tree_snapshot(source, forbid_disposable=True)


def test_fixed_root_clock_replay_and_operator_code_drift_are_rejected(
    tmp_path: Path, monkeypatch
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    paths = session._expected_paths(repo)
    with pytest.raises(ValueError, match="fixed dated"):
        session._validate_fixed_session_root(repo, repo / "alternate")
    paths["session"].parent.mkdir(parents=True)
    session._start_clock(paths["session"])
    with pytest.raises(FileExistsError, match="clock reset"):
        session._start_clock(paths["session"])

    repo2, _, _ = _seed_repo(tmp_path, monkeypatch, "repo2")
    operator = repo2 / session.OPERATOR_CODE_RELATIVE_PATH
    operator.write_text(operator.read_text(encoding="utf-8") + "\n# drift\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="operator code drifted"):
        session._state(session._expected_paths(repo2)["session"])


def test_package_identity_drift_is_sealed_and_blocks_training(tmp_path: Path, monkeypatch) -> None:
    repo, _, _ = _seed_repo(tmp_path, monkeypatch)
    session.record_authority(repo)
    monkeypatch.setattr(
        local,
        "capture_bitsandbytes_identity",
        lambda: {"version": "0.50.1", "cuda_kernel_available": False},
    )
    with pytest.raises(RuntimeError, match="bitsandbytes identity drifted"):
        session.verify_package(repo)
    root = session._expected_paths(repo)["session"]
    assert local._read_json(root / "package-runtime.json")["status"] == "failed"
    assert tuple(row["stage"] for row in session._ledger_rows(root)) == (
        "preflight",
        "record-authority",
        "verify-package",
    )


def test_fake_exact_five_plus_forty_lifecycle_seals_eta_and_discards_runtime(
    tmp_path: Path, monkeypatch
) -> None:
    repo, _, _ = _seed_repo(tmp_path, monkeypatch)
    _package_ready(repo)
    outcome = session.run_qlora(repo, executor=_successful_executor)
    root = session._expected_paths(repo)["session"]
    assert outcome["status"] == "measured"
    assert outcome["measurement"]["warmup_optimizer_steps"] == 5
    assert outcome["measurement"]["retained_optimizer_steps"] == 40
    assert outcome["measurement"]["projected_local_runtime_is_estimate"] is True
    assert outcome["proof"]["resolved_mode"] == "4bit-qlora"
    assert not (root / "qlora/runtime").exists()
    assert outcome["discard_receipt"]["path_absent"] is True
    manifest = session.finalize(repo)
    assert manifest["measured_target_reached"] is True
    assert session.verify(repo)["verified"] is True


def test_explicit_oom_is_not_given_eta_and_runtime_is_discarded(
    tmp_path: Path, monkeypatch
) -> None:
    repo, _, _ = _seed_repo(tmp_path, monkeypatch)
    _package_ready(repo)
    outcome = session.run_qlora(repo, executor=_oom_executor)
    root = session._expected_paths(repo)["session"]
    assert outcome["status"] == "oom"
    assert outcome["oom_kind"] == "cuda"
    assert outcome["measurement"] is None
    assert not (root / "qlora/runtime").exists()
    session.finalize(repo)
    assert session.verify(repo)["status"] == "oom"


def test_child_rejects_noncanonical_validation_before_any_data_contract_open(
    tmp_path: Path, monkeypatch
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    paths = session._expected_paths(repo)
    control = {
        "session_root": str(paths["session"]),
        "repo_root": str(repo),
        "stage_root": str(paths["session"] / "qlora"),
        "train_split": str(paths["train"]),
        "val_split": str(repo / "data/splits/not-validation.jsonl"),
        "base_model_path": str(local.EXTERNAL_QWEN_SNAPSHOT),
        "run_id": session.RUN_ID,
        "adaptation_mode": "qlora",
    }
    monkeypatch.setattr(local, "_read_json_allow_absolute", lambda _path: control)
    with pytest.raises(RuntimeError, match="validation split"):
        session._child_main(tmp_path / "unused-control.json")
    assert set(paths) == {"repo", "session", "source", "train", "validation", "contract"}


def test_literal_module_name_launches_the_real_cli(tmp_path: Path) -> None:
    assert session.MODULE_NAME == "src.model_adaptation.phase40_qlora_session"
    completed = subprocess.run(
        [sys.executable, "-m", session.MODULE_NAME, "--child-control", str(tmp_path / "missing.json")],
        cwd=Path.cwd(),
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert completed.returncode == 1
    assert "python -m __main__" not in completed.stderr
