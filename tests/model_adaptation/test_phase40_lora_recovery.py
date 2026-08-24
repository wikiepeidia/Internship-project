from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import stat
from types import SimpleNamespace

import pytest

from src.model_adaptation import phase40_callbacks as callbacks
from src.model_adaptation import phase40_local_experiment as local
from src.model_adaptation import phase40_lora_recovery as recovery


MEASURED_DURATIONS = [
    53.83673200000021,
    58.86228259999962,
    53.34186970000019,
    55.97138210000003,
    53.20682869999973,
    50.11833260000003,
    42.207156999999825,
    47.30428839999968,
    61.84722639999973,
    51.899407699999756,
    50.302978899999744,
    50.55842180000036,
    52.50571839999975,
    58.282910999999785,
    50.2177372000001,
    57.50406579999981,
    61.704953899999964,
    52.66051180000022,
    67.18717640000023,
    62.95956070000011,
    58.45152069999949,
    51.067807999999786,
    58.72214079999958,
    48.140658299999814,
    51.28991320000023,
    59.124662199999875,
]


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _retry_events() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    started = datetime(2026, 8, 24, 11, 49, 48, tzinfo=timezone.utc)

    def append(kind: str, step: int, values: dict[str, object]) -> None:
        rows.append(
            {
                "schema_version": "phase40-run-event-v1",
                "sequence_id": len(rows),
                "source_run_id": local.LORA_RETRY_RUN_ID,
                "run_kind": "probe",
                "event_kind": kind,
                "timestamp_utc": (started + timedelta(seconds=len(rows))).isoformat().replace(
                    "+00:00", "Z"
                ),
                "optimizer_step": step,
                "epoch": step / 414.5,
                "trainer_values": values,
            }
        )

    append("run_start", 0, {"callback_event_kind": "run_start", "run_kind": "probe"})
    durations = [62.9364263, 55.6205447, 55.0299961, 54.3002981, 58.8482647]
    durations.extend(MEASURED_DURATIONS)
    for step, duration in enumerate(durations, start=1):
        append(
            "step_timing",
            step,
            {
                "callback_event_kind": "optimizer_step",
                "run_kind": "probe",
                "epoch_observed": True,
                "duration_seconds": duration,
                "is_warmup": step <= 5,
                "examples": 4,
                "tokens": 1200,
            },
        )
        if step in {1, 10, 20, 30}:
            append(
                "train_log",
                step,
                {
                    "callback_event_kind": "log",
                    "run_kind": "probe",
                    "epoch_observed": True,
                    "loss": 1.0 / step,
                },
            )
    return rows


def test_audited_partial_retry_is_31_observed_26_measured_and_not_complete(
    tmp_path: Path,
) -> None:
    stage = tmp_path / local.LORA_RETRY_STAGE
    first = float(recovery.LIVE_FINGERPRINTS["first_monotonic"])
    terminal = float(recovery.LIVE_FINGERPRINTS["terminal_monotonic"])
    rows: list[dict[str, object]] = []
    for sequence in range(840):
        rows.append(
            {
                "schema_version": local.TELEMETRY_SCHEMA_VERSION,
                "sequence_id": sequence,
                "stage": local.LORA_RETRY_STAGE,
                "monotonic_seconds": first + (terminal - first) * sequence / 839,
                "terminal": sequence == 839,
                "stop_reason": "parent_controller_error" if sequence == 839 else None,
            }
        )
    _write_jsonl(stage / "telemetry.jsonl", rows)
    events = _retry_events()
    assert len(events) == 36 and events[-1]["event_kind"] == "step_timing"
    _write_jsonl(stage / "optimizer-events.jsonl", events)
    telemetry, summary = recovery._validate_terminal_and_events(
        stage,
        SimpleNamespace(deadline_monotonic=8556.9330494),
        {"retry_soft_limit_seconds": 1764.3438601},
    )
    assert telemetry[-1]["stop_reason"] == "parent_controller_error"
    assert summary["observed_optimizer_steps"] == 31
    assert summary["retained_optimizer_steps"] == 26
    assert summary["losses_finite"] is True
    assert round(summary["steady_state_step_seconds_median"], 3) == 53.274


def test_live_fingerprint_tamper_fails_closed(tmp_path: Path, monkeypatch) -> None:
    stage = tmp_path / local.LORA_RETRY_STAGE
    stage.mkdir()
    paths = {
        "telemetry_sha256": stage / "telemetry.jsonl",
        "optimizer_events_sha256": stage / "optimizer-events.jsonl",
        "quantization_proof_sha256": stage / "quantization-proof.json",
        "sanitized_stdout_sha256": stage / "child-stdout.sanitized.log",
        "sanitized_stderr_sha256": stage / "child-stderr.sanitized.log",
    }
    for index, path in enumerate(paths.values()):
        path.write_text(f"fixture-{index}\n", encoding="utf-8")
    fingerprints = dict(recovery.LIVE_FINGERPRINTS)
    fingerprints.update({name: local._sha256_file(path) for name, path in paths.items()})
    monkeypatch.setattr(recovery, "LIVE_FINGERPRINTS", fingerprints)
    recovery._validate_live_fingerprints(stage)
    (stage / "optimizer-events.jsonl").write_text("tampered\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="fingerprint drifted"):
        recovery._validate_live_fingerprints(stage)


def test_runtime_inventory_rejects_unexpected_adapter_file(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    for relative in recovery._RUNTIME_DIRECTORIES:
        (runtime / relative).mkdir(parents=True, exist_ok=True)
    for relative in recovery._RUNTIME_FILES:
        path = runtime / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixture\n", encoding="utf-8")
    readonly = runtime / sorted(recovery._RUNTIME_DIRECTORIES)[-1]
    os.chmod(readonly, stat.S_IREAD)
    try:
        inventory, readonly_directories = recovery._runtime_inventory(runtime)
        assert inventory
        assert readonly_directories
        (runtime / "adapter_model.safetensors").write_bytes(b"forbidden")
        with pytest.raises(RuntimeError, match="inventory differs"):
            recovery._runtime_inventory(runtime)
    finally:
        os.chmod(readonly, stat.S_IWRITE)


def test_discard_clears_only_bounded_readonly_runtime(tmp_path: Path) -> None:
    probe = tmp_path / "probe"
    nested = probe / "runtime/evidence/run"
    nested.mkdir(parents=True)
    (nested / "empty.txt").write_text("fixture", encoding="utf-8")
    os.chmod(nested, stat.S_IREAD)
    os.chmod(nested.parent, stat.S_IREAD)
    receipt = callbacks.discard_probe_artifact(
        run_id=local.LORA_RETRY_RUN_ID,
        probe_root=probe,
        discarded_path_identity="runtime",
    )
    assert receipt.path_absent is True
    assert not (probe / "runtime").exists()


def test_readonly_cleanup_rejects_root_link_before_resolve(tmp_path: Path, monkeypatch) -> None:
    target = tmp_path / "runtime"
    target.mkdir()
    observed: list[Path] = []

    def marked(path: Path) -> bool:
        observed.append(Path(path))
        return Path(path) == target

    monkeypatch.setattr(callbacks, "_is_link_or_reparse", marked)
    with pytest.raises(ValueError, match="link or reparse"):
        callbacks._clear_bounded_windows_readonly_tree(target)
    assert observed == [target]


def test_post_discard_resume_accepts_only_hash_bound_historical_seal(
    tmp_path: Path, monkeypatch
) -> None:
    stage = tmp_path / local.LORA_RETRY_STAGE
    stage.mkdir()
    for name in recovery._BASE_STAGE_FILES:
        (stage / name).write_text(f"{name}\n", encoding="utf-8")
    for name in ("recovery-seal.json", "discard-receipt.json", "controller-failure.json"):
        (stage / name).write_text("{}\n", encoding="utf-8")
    recovery._validate_stage_entries(stage)
    assert not (stage / "runtime").exists()

    sealed_code = {"commit": "a" * 40, "source_sha256": {}}
    seal = {
        "schema_version": recovery.RECOVERY_SCHEMA_VERSION,
        "stage": local.LORA_RETRY_STAGE,
        "run_id": local.LORA_RETRY_RUN_ID,
        "recovery_reason": recovery.RECOVERY_REASON,
        "recovery_code": sealed_code,
        "telemetry_sha256": local._sha256_file(stage / "telemetry.jsonl"),
        "optimizer_events_sha256": local._sha256_file(
            stage / "optimizer-events.jsonl"
        ),
        "quantization_proof_sha256": local._sha256_file(
            stage / "quantization-proof.json"
        ),
    }
    observed: list[object] = []
    monkeypatch.setattr(
        recovery,
        "_verify_committed_recovery_code",
        lambda _repo, identity: observed.append(identity) or identity,
    )
    recovery._verify_existing_seal(seal, stage, tmp_path)
    assert observed == [sealed_code]
    seal["optimizer_events_sha256"] = "0" * 64
    with pytest.raises(RuntimeError, match="immutable evidence"):
        recovery._verify_existing_seal(seal, stage, tmp_path)


def test_outcome_uses_canonical_partial_summary_and_keeps_median_separate() -> None:
    enriched = {
        "observed_optimizer_steps": 31,
        "retained_optimizer_steps": 26,
        "losses_finite": True,
        "measured_step_seconds": MEASURED_DURATIONS,
        "optimizer_events_sha256": "a" * 64,
        "terminal_event_kind": "step_timing",
        "steady_state_step_seconds_median": 53.27434919999996,
    }
    canonical = recovery._canonical_partial_summary(enriched)
    assert "steady_state_step_seconds_median" not in canonical
    assert canonical["retained_optimizer_steps"] == 26
    assert enriched["steady_state_step_seconds_median"] == 53.27434919999996
