from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.model_adaptation import phase40_local_experiment as local
from src.model_adaptation.phase40_evidence import RunEventKind, load_run_events


def _input_evidence() -> dict[str, object]:
    return {
        "train": {
            "relative_path": "data/splits/train.jsonl",
            "rows": 1658,
            "sha256": local.CANONICAL_TRAIN_SHA256,
        },
        "validation": {
            "relative_path": "data/splits/val.jsonl",
            "rows": 219,
            "sha256": local.CANONICAL_VAL_SHA256,
        },
    }


def _base_provenance() -> dict[str, object]:
    return {
        "schema_version": "phase40-qwen-base-model-snapshot-v1",
        "model_id": local.QWEN_MODEL_ID,
        "model_revision": local.QWEN_REVISION,
        "snapshot_content_sha256": "a" * 64,
        "files": [
            {"relative_path": "config.json", "bytes": 2, "sha256": "b" * 64},
            {
                "relative_path": "model.safetensors",
                "bytes": 4,
                "sha256": "c" * 64,
            },
            {
                "relative_path": "tokenizer_config.json",
                "bytes": 2,
                "sha256": "d" * 64,
            },
        ],
    }


def _torch_identity() -> dict[str, object]:
    return {
        "distribution": "torch",
        "version": "2.12.0+cu132",
        "cuda_version": "13.2",
        "module_path_sha256": "e" * 64,
        "record_sha256": "f" * 64,
    }


def _preinstalled_baseline() -> dict[str, object]:
    return {
        "bitsandbytes_present": True,
        "setup_receipt_relative_path": local.PACKAGE_SETUP_RECEIPT_RELATIVE_PATH.as_posix(),
        "setup_receipt_sha256": "1" * 64,
        "normalized_decision": local.APPROVE_AUTHORITY,
        "decision_was_normalized": True,
        "authority_source": local.PACKAGE_SETUP_AUTHORITY_SOURCE,
        "authority_source_sha256": "2" * 64,
    }


def _fake_setup_receipt() -> tuple[dict[str, object], dict[str, object]]:
    source = "install dependencies only; training starts tomorrow"
    python_identity = {
        "implementation": "CPython",
        "version": "3.13.13",
        "platform": "Windows-test",
        "machine": "AMD64",
        "executable_path_sha256": "3" * 64,
    }
    pre_inventory = local._distribution_inventory_from_rows(
        [["torch", "2.12.0+cu132"]]
    )
    post_inventory = local._distribution_inventory_from_rows(
        [["bitsandbytes", "0.50.1"], ["torch", "2.12.0+cu132"]]
    )
    distribution_identity = {
        "version": "0.50.1",
        "module_path_sha256": "4" * 64,
        "record_sha256": "5" * 64,
    }
    download_url = (
        "https://files.pythonhosted.org/packages/test/"
        + local.BITSANDBYTES_WHEEL_FILENAME
    )
    provenance = local._bitsandbytes_install_provenance(download_url)
    provenance_sha256 = hashlib.sha256(
        local._canonical_json_bytes(provenance)
    ).hexdigest()
    payload: dict[str, object] = {
        "schema_version": local.PACKAGE_SETUP_SCHEMA_VERSION,
        "package": "bitsandbytes",
        "version": "0.50.1",
        "normalized_decision": local.APPROVE_AUTHORITY,
        "decision_was_normalized": True,
        "authority_source": local.PACKAGE_SETUP_AUTHORITY_SOURCE,
        "authority_source_sha256": hashlib.sha256(source.encode()).hexdigest(),
        "normalization_note": local.PACKAGE_SETUP_NORMALIZATION_NOTE,
        "install_provenance_relative_path": (
            local.PACKAGE_SETUP_PROVENANCE_RELATIVE_PATH.as_posix()
        ),
        "install_provenance_sha256": provenance_sha256,
        "python_pre": python_identity,
        "python_post": python_identity,
        "torch_pre": _torch_identity(),
        "torch_post": _torch_identity(),
        "torch_distribution_identity_unchanged": True,
        "inventory_pre": local._distribution_inventory_summary(pre_inventory),
        "inventory_post": local._distribution_inventory_summary(post_inventory),
        "package_delta": {
            "added": [{"name": "bitsandbytes", "version": "0.50.1"}],
            "removed": [],
        },
        "bitsandbytes": {
            "distribution_identity": distribution_identity,
            "runtime_identity": {
                "version": "0.50.1",
                "cuda_kernel_available": True,
            },
        },
        "pip_check": {"exit_code": 0, "output": "No broken requirements found."},
        "installed_utc": "2026-08-24T10:00:00Z",
    }
    current = {
        "python": python_identity,
        "inventory": post_inventory,
        "distribution": distribution_identity,
        "provenance": provenance,
    }
    return payload, current


def _write_fake_setup_artifacts(
    repo: Path, payload: dict[str, object], current: dict[str, object]
) -> Path:
    local._write_immutable_json(
        repo / local.PACKAGE_SETUP_PROVENANCE_RELATIVE_PATH,
        current["provenance"],
    )
    receipt_path = repo / local.PACKAGE_SETUP_RECEIPT_RELATIVE_PATH
    local._write_immutable_json(receipt_path, payload)
    return receipt_path


def _initialise(tmp_path: Path, *, monotonic: float = 100.0) -> Path:
    root = tmp_path / "decision"
    local.initialize_decision_root(
        root,
        input_evidence=_input_evidence(),
        base_model_provenance=_base_provenance(),
        torch_identity=_torch_identity(),
        started_utc="2026-08-24T08:00:00Z",
        started_monotonic=monotonic,
        boot_identity="boot-A",
    )
    return root


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _telemetry_rows(stage: str) -> list[dict[str, object]]:
    common = {
        "schema_version": local.TELEMETRY_SCHEMA_VERSION,
        "stage": stage,
        "system_ram_total_bytes": 32_000,
        "system_ram_available_bytes": 16_000,
        "system_ram_used_bytes": 16_000,
        "process_rss_bytes": 10_000,
        "torch_allocated_bytes": 6_000,
        "torch_reserved_bytes": 7_000,
        "torch_peak_allocated_bytes": 6_500,
        "torch_peak_reserved_bytes": 7_500,
        "device_vram_total_mib": 8151,
        "device_vram_used_mib": 7000,
        "device_vram_free_mib": 1151,
        "gpu_utilization_percent": 95,
        "gpu_temperature_c": 72,
        "gpu_power_w": 70.5,
        "gpu_performance_state": "P0",
        "nvidia_raw": "8151, 7000, 1151, 95, 72, 70.5, P0",
    }
    return [
        {
            **common,
            "sequence_id": 0,
            "timestamp_utc": "2026-08-24T08:00:01Z",
            "monotonic_seconds": 101.0,
            "terminal": False,
            "stop_reason": None,
        },
        {
            **common,
            "sequence_id": 1,
            "timestamp_utc": "2026-08-24T08:00:03Z",
            "monotonic_seconds": 103.0,
            "terminal": True,
            "stop_reason": "evidence_target_reached",
        },
    ]


def _qlora_events() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []

    def append_event(
        *,
        event_kind: str,
        optimizer_step: int,
        second: int,
        epoch: float,
        trainer_values: dict[str, object],
    ) -> None:
        rows.append(
            {
                "schema_version": "phase40-run-event-v1",
                "sequence_id": len(rows),
                "source_run_id": "rtx5050-qlora",
                "run_kind": "probe",
                "event_kind": event_kind,
                "timestamp_utc": f"2026-08-24T08:01:{second:02d}Z",
                "optimizer_step": optimizer_step,
                "epoch": epoch,
                "trainer_values": trainer_values,
            }
        )

    append_event(
        event_kind="run_start",
        optimizer_step=0,
        second=0,
        epoch=0.0,
        trainer_values={"callback_event_kind": "run_start", "run_kind": "probe"},
    )
    for step in range(1, 46):
        append_event(
            event_kind="step_timing",
            optimizer_step=step,
            second=step,
            epoch=step / 45,
            trainer_values={
                "callback_event_kind": "optimizer_step",
                "run_kind": "probe",
                "epoch_observed": True,
                "duration_seconds": 1.5 + (step % 3) * 0.1,
                "is_warmup": step <= 5,
                "examples": 4,
                "tokens": 1024,
                "peak_allocated_bytes": 6_000,
                "peak_reserved_bytes": 7_000,
            },
        )
    append_event(
        event_kind="evaluation",
        optimizer_step=45,
        second=46,
        epoch=1.0,
        trainer_values={
            "callback_event_kind": "evaluation",
            "run_kind": "probe",
            "duration_seconds": 12.0,
            "eval_runtime": 12.0,
        },
    )
    append_event(
        event_kind="checkpoint",
        optimizer_step=45,
        second=47,
        epoch=1.0,
        trainer_values={
            "callback_event_kind": "checkpoint",
            "run_kind": "probe",
            "duration_seconds": 3.0,
            "measurement_scope": "isolated",
        },
    )
    append_event(
        event_kind="run_end",
        optimizer_step=45,
        second=48,
        epoch=1.0,
        trainer_values={"callback_event_kind": "run_end", "run_kind": "probe"},
    )
    return rows


def _partial_lora_events() -> list[dict[str, object]]:
    return [
        {
            "schema_version": "phase40-run-event-v1",
            "sequence_id": 0,
            "source_run_id": "rtx5050-lora",
            "run_kind": "probe",
            "event_kind": "run_start",
            "timestamp_utc": "2026-08-24T08:00:30Z",
            "optimizer_step": 0,
            "epoch": 0.0,
            "trainer_values": {
                "callback_event_kind": "run_start",
                "run_kind": "probe",
            },
        },
        {
            "schema_version": "phase40-run-event-v1",
            "sequence_id": 1,
            "source_run_id": "rtx5050-lora",
            "run_kind": "probe",
            "event_kind": "step_timing",
            "timestamp_utc": "2026-08-24T08:00:31Z",
            "optimizer_step": 1,
            "epoch": 0.01,
            "trainer_values": {
                "callback_event_kind": "optimizer_step",
                "run_kind": "probe",
                "epoch_observed": True,
                "duration_seconds": 1.5,
                "is_warmup": True,
                "examples": 4,
                "tokens": 1024,
            },
        },
    ]


def _qlora_proof() -> dict[str, object]:
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


def test_decision_clock_rejects_reset_rollback_reboot_and_expiry(tmp_path: Path) -> None:
    root = _initialise(tmp_path)
    state = local.load_decision_state(
        root,
        now_utc="2026-08-24T08:30:00Z",
        now_monotonic=1900.0,
        boot_identity="boot-A",
    )
    assert state.deadline_monotonic == 7300.0
    with pytest.raises(FileExistsError, match="already exists"):
        _initialise(tmp_path, monotonic=200.0)
    with pytest.raises(RuntimeError, match="monotonic clock moved backwards"):
        local.load_decision_state(
            root,
            now_utc="2026-08-24T08:30:00Z",
            now_monotonic=99.0,
            boot_identity="boot-A",
        )
    with pytest.raises(RuntimeError, match="boot identity changed"):
        local.load_decision_state(
            root,
            now_utc="2026-08-24T08:30:00Z",
            now_monotonic=1900.0,
            boot_identity="boot-B",
        )
    with pytest.raises(TimeoutError, match="two-hour decision window expired"):
        local.load_decision_state(
            root,
            now_utc="2026-08-24T10:00:01Z",
            now_monotonic=7301.0,
            boot_identity="boot-A",
        )


def test_rejected_held_out_style_path_is_rejected_before_open(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    train = repo / "data/splits/train.jsonl"
    val = repo / "data/splits/val.jsonl"
    authority = repo / local.DOWNSTREAM_CONTRACT_RELATIVE_PATH
    opened: list[object] = []
    monkeypatch.setattr("builtins.open", lambda *args, **kwargs: opened.append(args[0]))
    with pytest.raises(ValueError, match="canonical validation"):
        local.validate_local_input_paths(
            repo_root=repo,
            train_path=train,
            val_path=repo / "data/splits/held-out-fixture.jsonl",
            downstream_contract_path=authority,
            decision_root=repo / local.DECISION_ROOT_RELATIVE_PATH,
        )
    assert opened == []
    assert not (repo / local.DECISION_ROOT_RELATIVE_PATH).exists()


def test_training_stage_rejects_alternate_repo_before_child_or_stage_creation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_repo = tmp_path / "original-repo"
    root = original_repo / local.DECISION_ROOT_RELATIVE_PATH
    original_hash = local._path_identity_sha256(original_repo)
    local.initialize_decision_root(
        root,
        input_evidence=_input_evidence(),
        base_model_provenance=_base_provenance(),
        torch_identity=_torch_identity(),
        started_utc="2026-08-24T08:00:00Z",
        started_monotonic=100.0,
        boot_identity="boot-A",
        repo_root_path_sha256=original_hash,
    )
    alternate = tmp_path / "copied-repo"
    alternate.mkdir()
    monkeypatch.setattr(local, "_boot_identity", lambda: "boot-A")
    monkeypatch.setattr(local.time, "monotonic", lambda: 120.0)
    monkeypatch.setattr(local, "_utc_now", lambda: "2026-08-24T08:00:20Z")
    with pytest.raises(RuntimeError, match="repository root differs"):
        local.run_monitored_training_stage(
            SimpleNamespace(decision_root=root, repo_root=alternate), stage="lora"
        )
    assert not (root / "lora").exists()


def test_external_snapshot_gate_checks_manifest_metadata_and_reparse(tmp_path: Path) -> None:
    snapshot = tmp_path / "snapshot"
    metadata = snapshot / ".cache/huggingface/download"
    metadata.mkdir(parents=True)
    (snapshot / "config.json").write_text("{}", encoding="utf-8")
    (snapshot / "tokenizer_config.json").write_text("{}", encoding="utf-8")
    (snapshot / "model-00001-of-00001.safetensors").write_bytes(b"model")
    (snapshot / "model.safetensors.index.json").write_text(
        json.dumps({"weight_map": {"x": "model-00001-of-00001.safetensors"}}),
        encoding="utf-8",
    )
    for name in (
        "config.json",
        "tokenizer_config.json",
        "model.safetensors.index.json",
        "model-00001-of-00001.safetensors",
    ):
        (metadata / f"{name}.metadata").write_text(
            local.QWEN_REVISION + "\nmetadata\n", encoding="utf-8"
        )
    manifest = tmp_path / "download-manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "models": [
                    {
                        "candidate_id": "qwen3-4b-instruct-2507",
                        "repo_id": local.QWEN_MODEL_ID,
                        "local_path": str(snapshot),
                        "size_bytes": sum(
                            p.stat().st_size for p in snapshot.rglob("*") if p.is_file()
                        ),
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    result = local.validate_external_snapshot_identity(
        snapshot,
        manifest,
        expected_snapshot_path=snapshot,
        reparse_checker=lambda path: False,
    )
    assert result["model_revision"] == local.QWEN_REVISION
    with pytest.raises(ValueError, match="reparse point"):
        local.validate_external_snapshot_identity(
            snapshot,
            manifest,
            expected_snapshot_path=snapshot,
            reparse_checker=lambda path: path.name == "config.json",
        )


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (
            "8151, 7000, 1151, 95, 72, 70.5, P0",
            {"device_vram_total_mib": 8151, "gpu_temperature_c": 72},
        ),
        (
            "malformed nvidia output",
            {"device_vram_total_mib": None, "gpu_temperature_c": None},
        ),
    ],
)
def test_nvidia_parser_preserves_raw_and_explicit_nulls(raw, expected) -> None:
    parsed = local.parse_nvidia_smi_csv(raw)
    assert parsed["nvidia_raw"] == raw
    assert all(parsed[key] == value for key, value in expected.items())


def test_telemetry_requires_order_freshness_and_terminal_reason(tmp_path: Path) -> None:
    path = tmp_path / "telemetry.jsonl"
    for row in _telemetry_rows("lora"):
        local.append_telemetry_sample(path, row)
    rows = local.verify_telemetry(path, expected_stage="lora")
    assert rows[-1]["terminal"] is True
    stale = _telemetry_rows("lora")
    stale[1]["monotonic_seconds"] = 106.0
    stale_path = tmp_path / "stale.jsonl"
    _write_jsonl(stale_path, stale)
    with pytest.raises(RuntimeError, match="stale"):
        local.verify_telemetry(stale_path, expected_stage="lora")


def test_lora_memory_classifier_uses_sustained_boundary_samples() -> None:
    gpu_rows = [
        {
            "sequence_id": index,
            "device_vram_total_mib": 8_000,
            "device_vram_used_mib": 7_600,
            "device_vram_free_mib": 512,
            "system_ram_total_bytes": 32_000,
            "system_ram_available_bytes": 16_000,
        }
        for index in range(3)
    ]

    gpu = local.classify_lora_memory_pressure(gpu_rows, terminal_status="timeout")

    assert gpu["classification"] == "gpu_pressure"
    assert gpu["supporting_sample_sequences"] == [0, 1, 2]
    assert gpu["peak_device_vram_used_mib"] == 7_600
    assert gpu["minimum_device_vram_free_mib"] == 512

    system_rows = [
        {
            "sequence_id": index,
            "device_vram_total_mib": 8_000,
            "device_vram_used_mib": 1_000,
            "device_vram_free_mib": 7_000,
            "system_ram_total_bytes": 20_000,
            "system_ram_available_bytes": 2_000,
        }
        for index in range(3)
    ]
    system = local.classify_lora_memory_pressure(
        system_rows, terminal_status="measured"
    )
    assert system["classification"] == "system_pressure"
    assert system["minimum_system_ram_available_percent"] == 10.0


def test_lora_memory_classifier_fails_closed_for_short_or_malformed_samples() -> None:
    rows = [
        {
            "sequence_id": 0,
            "device_vram_total_mib": 8_000,
            "device_vram_used_mib": 7_999,
            "device_vram_free_mib": 1,
            "system_ram_total_bytes": None,
            "system_ram_available_bytes": "unknown",
        },
        {
            "sequence_id": 1,
            "device_vram_total_mib": 8_000,
            "device_vram_used_mib": 7_999,
            "device_vram_free_mib": 1,
            "system_ram_total_bytes": float("nan"),
            "system_ram_available_bytes": 0,
        },
        {
            "sequence_id": 2,
            "device_vram_total_mib": "8151",
            "device_vram_used_mib": None,
            "device_vram_free_mib": None,
            "system_ram_total_bytes": 32_000,
            "system_ram_available_bytes": 16_000,
        },
    ]

    result = local.classify_lora_memory_pressure(
        rows, terminal_status="oom", oom_kind="unverified"
    )

    assert result["classification"] == "not_proven_memory_constrained"
    assert result["memory_constrained"] is False
    assert result["gpu_pressure_sample_sequences"] == []


@pytest.mark.parametrize("oom_kind", ["cuda", "system"])
def test_lora_memory_classifier_definitive_for_explicit_oom(oom_kind: str) -> None:
    result = local.classify_lora_memory_pressure(
        [], terminal_status="oom", oom_kind=oom_kind
    )
    assert result["classification"] == "definitive_memory_infeasible"
    assert result["basis"] == f"explicit_{oom_kind}_oom"
    assert result["memory_constrained"] is True


@pytest.mark.parametrize(
    ("steps", "finite", "age", "median", "now", "expected"),
    [
        (0, True, 0.5, None, 1800.0, False),
        (1, False, 0.5, 2.0, 1800.0, False),
        (1, True, 5.0, 2.0, 1800.0, False),
        (39, True, 0.5, 2.0, 1800.0, True),
        (39, True, 0.5, 1900.0, 1800.0, False),
    ],
)
def test_lora_extension_is_narrow_and_cannot_cross_hard_limit(
    steps, finite, age, median, now, expected
) -> None:
    assert (
        local.lora_should_extend(
            retained_steps=steps,
            losses_finite=finite,
            telemetry_age_seconds=age,
            median_step_seconds=median,
            elapsed_seconds=now,
            remaining_decision_seconds=7200.0 - now,
        )
        is expected
    )


@pytest.mark.parametrize("mutation", ["missing", "extra", "reordered"])
def test_qlora_events_require_exact_five_plus_forty(tmp_path: Path, mutation: str) -> None:
    rows = _qlora_events()
    step_indexes = [
        index for index, row in enumerate(rows) if row["event_kind"] == "step_timing"
    ]
    if mutation == "missing":
        rows.pop(step_indexes[19])
    elif mutation == "extra":
        duplicate = dict(rows[step_indexes[-1]])
        duplicate["trainer_values"] = dict(duplicate["trainer_values"])
        evaluation_index = next(
            index for index, row in enumerate(rows) if row["event_kind"] == "evaluation"
        )
        rows.insert(evaluation_index, duplicate)
    else:
        rows[step_indexes[4]], rows[step_indexes[5]] = (
            rows[step_indexes[5]],
            rows[step_indexes[4]],
        )
    for index, row in enumerate(rows):
        row["sequence_id"] = index
    path = tmp_path / "events.jsonl"
    _write_jsonl(path, rows)
    with pytest.raises(RuntimeError):
        local.validate_qlora_events(path)


def test_complete_qlora_events_produce_recomputable_eta(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    _write_jsonl(path, _qlora_events())
    events = load_run_events(path, expected_run_id="rtx5050-qlora")
    assert events[0].event_kind == RunEventKind.RUN_START
    assert events[-1].event_kind == RunEventKind.RUN_END
    assert sum(event.event_kind == RunEventKind.STEP_TIMING for event in events) == 45
    evidence = local.validate_qlora_events(path)
    assert evidence["warmup_optimizer_steps"] == 5
    assert evidence["retained_optimizer_steps"] == 40
    assert evidence["planned_full_optimizer_steps"] == 1245
    assert evidence["projected_local_runtime_seconds"] == pytest.approx(
        evidence["steady_state_step_seconds_median"] * 1245 + 15.0
    )


def test_setup_writer_publishes_sanitized_receipt_and_install_provenance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "repo"
    payload, current = _fake_setup_receipt()
    report_path = tmp_path / "ephemeral-pip-report.json"
    report_path.write_text(
        json.dumps(
            {
                "install": [
                    {
                        "metadata": {"name": "bitsandbytes", "version": "0.50.1"},
                        "requested": True,
                        "download_info": {
                            "url": current["provenance"]["official_wheel"]["download_url"],
                            "archive_info": {
                                "hashes": {"sha256": local.BITSANDBYTES_WHEEL_SHA256}
                            },
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        local, "capture_distribution_inventory", lambda: current["inventory"]
    )
    monkeypatch.setattr(local, "capture_python_identity", lambda: current["python"])
    monkeypatch.setattr(local, "capture_torch_identity", _torch_identity)
    monkeypatch.setattr(
        local,
        "capture_bitsandbytes_identity",
        lambda: payload["bitsandbytes"]["runtime_identity"],
    )
    monkeypatch.setattr(
        local,
        "capture_distribution_identity",
        lambda *args, **kwargs: current["distribution"],
    )
    monkeypatch.setattr(
        local,
        "_run_clean_pip_check",
        lambda: {"exit_code": 0, "output": "No broken requirements found."},
    )

    receipt = local.write_bitsandbytes_setup_receipt(
        repo,
        pip_install_report=report_path,
        source_authority_text="install dependencies only; training starts tomorrow",
        pre_install_inventory_sha256=payload["inventory_pre"]["inventory_sha256"],
        pre_install_distribution_count=payload["inventory_pre"]["distribution_count"],
        pre_install_python=current["python"],
        pre_install_torch=_torch_identity(),
        installed_utc="2026-08-24T10:00:00Z",
    )

    receipt_path = repo / local.PACKAGE_SETUP_RECEIPT_RELATIVE_PATH
    provenance_path = repo / local.PACKAGE_SETUP_PROVENANCE_RELATIVE_PATH
    public_text = receipt_path.read_text(encoding="utf-8")
    assert provenance_path.is_file()
    assert receipt["install_provenance_sha256"] == local._sha256_file(provenance_path)
    assert receipt["authority_source"] == local.PACKAGE_SETUP_AUTHORITY_SOURCE
    assert "training starts tomorrow" not in public_text
    assert "distributions" not in public_text
    assert "pip_install_report" not in public_text
    assert local.verify_bitsandbytes_setup_receipt(repo)["setup_receipt_sha256"] == (
        local._sha256_file(receipt_path)
    )


def test_preinstalled_setup_receipt_is_hash_linked_without_runtime_import(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "repo"
    payload, current = _fake_setup_receipt()
    receipt_path = _write_fake_setup_artifacts(repo, payload, current)
    monkeypatch.setattr(local, "capture_python_identity", lambda: current["python"])
    monkeypatch.setattr(local, "capture_torch_identity", _torch_identity)
    monkeypatch.setattr(
        local, "capture_distribution_inventory", lambda: current["inventory"]
    )
    monkeypatch.setattr(
        local,
        "capture_distribution_identity",
        lambda *args, **kwargs: current["distribution"],
    )
    monkeypatch.setattr(
        local,
        "_run_clean_pip_check",
        lambda: {"exit_code": 0, "output": "No broken requirements found."},
    )

    baseline = local.verify_bitsandbytes_setup_receipt(repo)

    assert baseline == {
        "bitsandbytes_present": True,
        "setup_receipt_relative_path": local.PACKAGE_SETUP_RECEIPT_RELATIVE_PATH.as_posix(),
        "setup_receipt_sha256": local._sha256_file(receipt_path),
        "normalized_decision": local.APPROVE_AUTHORITY,
        "decision_was_normalized": True,
        "authority_source": local.PACKAGE_SETUP_AUTHORITY_SOURCE,
        "authority_source_sha256": payload["authority_source_sha256"],
    }


def test_setup_receipt_rejects_torch_or_normalization_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload, current = _fake_setup_receipt()
    payload["decision_was_normalized"] = False
    repo = tmp_path / "normalization-drift"
    _write_fake_setup_artifacts(repo, payload, current)
    with pytest.raises(RuntimeError, match="receipt contract"):
        local.verify_bitsandbytes_setup_receipt(repo)

    payload, current = _fake_setup_receipt()
    repo = tmp_path / "torch-drift"
    _write_fake_setup_artifacts(repo, payload, current)
    monkeypatch.setattr(local, "capture_python_identity", lambda: current["python"])
    monkeypatch.setattr(
        local, "capture_torch_identity", lambda: dict(_torch_identity(), version="2.13.0")
    )
    with pytest.raises(RuntimeError, match="Torch identity drifted"):
        local.verify_bitsandbytes_setup_receipt(repo)


def test_preinstalled_authority_records_normalization_not_fake_verbatim(
    tmp_path: Path,
) -> None:
    root = tmp_path / "decision"
    baseline = _preinstalled_baseline()
    local.initialize_decision_root(
        root,
        input_evidence=_input_evidence(),
        base_model_provenance=_base_provenance(),
        torch_identity=_torch_identity(),
        package_baseline=baseline,
        started_utc="2026-08-24T08:00:00Z",
        started_monotonic=100.0,
        boot_identity="boot-A",
    )
    lora = root / "lora"
    _write_jsonl(lora / "telemetry.jsonl", _telemetry_rows("lora"))
    (lora / "runtime").mkdir(parents=True)
    receipt = local.discard_stage_runtime(lora, run_id="rtx5050-lora")
    local.write_stage_outcome(
        root,
        stage="lora",
        outcome={
            "status": "measured",
            "stop_reason": "evidence_target_reached",
            "telemetry": "lora/telemetry.jsonl",
            "discard_receipt": receipt,
        },
        now_utc="2026-08-24T08:01:00Z",
        now_monotonic=160.0,
        boot_identity="boot-A",
    )
    with pytest.raises(ValueError, match="cannot retroactively"):
        local.record_package_authority(
            root,
            "reject bitsandbytes 0.50.1: changed my mind",
            now_utc="2026-08-24T08:01:01Z",
            now_monotonic=161.0,
            boot_identity="boot-A",
        )

    authority = local.record_package_authority(
        root,
        local.APPROVE_AUTHORITY,
        now_utc="2026-08-24T08:01:02Z",
        now_monotonic=162.0,
        boot_identity="boot-A",
    )

    assert authority["decision_text"] == local.APPROVE_AUTHORITY
    assert authority["decision_source"] == "normalized_preinstalled_setup_receipt"
    assert authority["decision_was_normalized"] is True
    assert authority["normalization_note"] == local.PACKAGE_SETUP_NORMALIZATION_NOTE
    assert authority["setup_receipt_sha256"] == baseline["setup_receipt_sha256"]
    assert authority["authority_source"] == local.PACKAGE_SETUP_AUTHORITY_SOURCE
    assert authority["authority_source_sha256"] == baseline[
        "authority_source_sha256"
    ]


def test_package_authority_and_runtime_proof_fail_closed(tmp_path: Path) -> None:
    root = _initialise(tmp_path)
    lora = root / "lora"
    _write_jsonl(lora / "telemetry.jsonl", _telemetry_rows("lora"))
    (lora / "runtime").mkdir(parents=True)
    receipt = local.discard_stage_runtime(lora, run_id="rtx5050-lora")
    local.write_stage_outcome(
        root,
        stage="lora",
        outcome={
            "status": "measured",
            "stop_reason": "evidence_target_reached",
            "retained_optimizer_steps": 40,
            "losses_finite": True,
            "telemetry": "lora/telemetry.jsonl",
            "discard_receipt": receipt,
        },
        now_utc="2026-08-24T08:01:00Z",
        now_monotonic=160.0,
        boot_identity="boot-A",
    )
    authority = local.record_package_authority(
        root,
        "approve bitsandbytes 0.50.1",
        now_utc="2026-08-24T08:02:00Z",
        now_monotonic=220.0,
        boot_identity="boot-A",
    )
    assert authority["approved"] is True
    with pytest.raises(FileExistsError, match="already recorded"):
        local.record_package_authority(
            root,
            "approve bitsandbytes 0.50.1",
            now_utc="2026-08-24T08:02:01Z",
            now_monotonic=221.0,
            boot_identity="boot-A",
        )
    drifted = dict(_torch_identity(), version="2.13.0")
    with pytest.raises(RuntimeError, match="Torch identity changed"):
        local.verify_package_runtime(
            root,
            bitsandbytes_identity={"version": "0.50.1", "cuda_kernel_available": True},
            torch_identity=drifted,
            now_utc="2026-08-24T08:02:02Z",
            now_monotonic=222.0,
            boot_identity="boot-A",
        )
    failure_manifest = local.finalize_local_decision(
        root,
        now_utc="2026-08-24T08:02:03Z",
        now_monotonic=223.0,
        boot_identity="boot-A",
    )
    assert failure_manifest["qlora"]["failure_stage"] == "capability_preflight"
    assert failure_manifest["recommendation"] == "colab_fallback"
    assert local.verify_local_decision(root)["verified"] is True


def test_package_rejection_seals_qlora_prestart_absence_and_finalizes(
    tmp_path: Path,
) -> None:
    root = _initialise(tmp_path)
    lora = root / "lora"
    _write_jsonl(lora / "telemetry.jsonl", _telemetry_rows("lora"))
    (lora / "runtime").mkdir(parents=True)
    receipt = local.discard_stage_runtime(lora, run_id="rtx5050-lora")
    local.write_stage_outcome(
        root,
        stage="lora",
        outcome={
            "status": "measured",
            "stop_reason": "evidence_target_reached",
            "retained_optimizer_steps": 1,
            "losses_finite": True,
            "telemetry": "lora/telemetry.jsonl",
            "discard_receipt": receipt,
        },
        now_utc="2026-08-24T08:01:00Z",
        now_monotonic=160.0,
        boot_identity="boot-A",
    )
    authority = local.record_package_authority(
        root,
        "reject bitsandbytes 0.50.1: operator rejected the binary wheel",
        now_utc="2026-08-24T08:02:00Z",
        now_monotonic=220.0,
        boot_identity="boot-A",
    )
    assert authority["approved"] is False
    assert authority["qlora_prestart_evidence"] == "qlora/run-evidence.json"
    assert not (root / "qlora/runtime").exists()
    with pytest.raises(RuntimeError, match="rejected"):
        local.verify_package_runtime(
            root,
            bitsandbytes_identity={
                "version": "0.50.1",
                "cuda_kernel_available": True,
            },
            torch_identity=_torch_identity(),
            now_utc="2026-08-24T08:02:01Z",
            now_monotonic=221.0,
            boot_identity="boot-A",
        )
    manifest = local.finalize_local_decision(
        root,
        now_utc="2026-08-24T08:02:02Z",
        now_monotonic=222.0,
        boot_identity="boot-A",
    )
    assert manifest["qlora"]["status"] == "prestart_failure"
    assert manifest["recommendation"] == "colab_fallback"
    assert local.verify_local_decision(root)["verified"] is True


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("nf4", False),
        ("double_quantization", False),
        ("linear4bit_modules", 0),
        ("base_weights_frozen", False),
        ("adapter_gradient_nonzero_count", 0),
    ],
)
def test_incomplete_four_bit_proof_is_rejected(field: str, value: object) -> None:
    proof = dict(_qlora_proof(), **{field: value})
    with pytest.raises(RuntimeError, match="genuine QLoRA"):
        local.validate_genuine_qlora_proof(proof)


def test_discard_receipt_hashes_and_removes_bounded_runtime(tmp_path: Path) -> None:
    stage = tmp_path / "qlora"
    runtime = stage / "runtime"
    (runtime / "trainer/checkpoint-1").mkdir(parents=True)
    (runtime / "trainer/checkpoint-1/model.bin").write_bytes(b"adapter")
    receipt = local.discard_stage_runtime(stage, run_id="rtx5050-qlora")
    assert receipt["path_absent"] is True
    assert not runtime.exists()
    local.verify_stage_discard(stage, receipt)


def test_fake_complete_lifecycle_finalizes_and_verifies(tmp_path: Path) -> None:
    root = _initialise(tmp_path)
    lora = root / "lora"
    _write_jsonl(lora / "telemetry.jsonl", _telemetry_rows("lora"))
    (lora / "runtime").mkdir(parents=True)
    receipt = local.discard_stage_runtime(lora, run_id="rtx5050-lora")
    local.write_stage_outcome(
        root,
        stage="lora",
        outcome={
            "status": "measured",
            "stop_reason": "evidence_target_reached",
            "retained_optimizer_steps": 40,
            "losses_finite": True,
            "telemetry": "lora/telemetry.jsonl",
            "discard_receipt": receipt,
        },
        now_utc="2026-08-24T08:02:00Z",
        now_monotonic=220.0,
        boot_identity="boot-A",
    )
    local.record_package_authority(
        root,
        "approve bitsandbytes 0.50.1",
        now_utc="2026-08-24T08:03:00Z",
        now_monotonic=280.0,
        boot_identity="boot-A",
    )
    local.verify_package_runtime(
        root,
        bitsandbytes_identity={"version": "0.50.1", "cuda_kernel_available": True},
        torch_identity=_torch_identity(),
        now_utc="2026-08-24T08:03:01Z",
        now_monotonic=281.0,
        boot_identity="boot-A",
    )
    qlora = root / "qlora"
    _write_jsonl(qlora / "telemetry.jsonl", _telemetry_rows("qlora"))
    _write_jsonl(qlora / "optimizer-events.jsonl", _qlora_events())
    local._write_immutable_json(qlora / "quantization-proof.json", _qlora_proof())
    (qlora / "runtime").mkdir(parents=True)
    qreceipt = local.discard_stage_runtime(qlora, run_id="rtx5050-qlora")
    local.write_stage_outcome(
        root,
        stage="qlora",
        outcome={
            "status": "measured",
            "stop_reason": "evidence_target_reached",
            "telemetry": "qlora/telemetry.jsonl",
            "optimizer_events": "qlora/optimizer-events.jsonl",
            "quantization_proof": "qlora/quantization-proof.json",
            "discard_receipt": qreceipt,
        },
        now_utc="2026-08-24T08:05:00Z",
        now_monotonic=400.0,
        boot_identity="boot-A",
    )
    manifest = local.finalize_local_decision(
        root,
        now_utc="2026-08-24T08:05:01Z",
        now_monotonic=401.0,
        boot_identity="boot-A",
    )
    assert manifest["recommendation"] == "local_full_qlora_candidate"
    verified = local.verify_local_decision(root)
    assert verified["verified"] is True


def test_global_deadline_can_seal_cleanup_and_finalize_after_7200_seconds(
    tmp_path: Path,
) -> None:
    root = _initialise(tmp_path)
    lora = root / "lora"
    _write_jsonl(lora / "telemetry.jsonl", _telemetry_rows("lora"))
    (lora / "runtime").mkdir(parents=True)
    receipt = local.discard_stage_runtime(lora, run_id="rtx5050-lora")
    local.write_stage_outcome(
        root,
        stage="lora",
        outcome={
            "status": "measured",
            "stop_reason": "evidence_target_reached",
            "telemetry": "lora/telemetry.jsonl",
            "discard_receipt": receipt,
        },
        now_utc="2026-08-24T08:01:00Z",
        now_monotonic=160.0,
        boot_identity="boot-A",
    )
    local.record_package_authority(
        root,
        "approve bitsandbytes 0.50.1",
        now_utc="2026-08-24T08:02:00Z",
        now_monotonic=220.0,
        boot_identity="boot-A",
    )
    local.verify_package_runtime(
        root,
        bitsandbytes_identity={"version": "0.50.1", "cuda_kernel_available": True},
        torch_identity=_torch_identity(),
        now_utc="2026-08-24T08:02:01Z",
        now_monotonic=221.0,
        boot_identity="boot-A",
    )
    qlora = root / "qlora"
    timeout_rows = _telemetry_rows("qlora")
    timeout_rows[0]["monotonic_seconds"] = 7299.0
    timeout_rows[1]["monotonic_seconds"] = 7301.0
    timeout_rows[1]["stop_reason"] = "global_deadline"
    _write_jsonl(qlora / "telemetry.jsonl", timeout_rows)
    (qlora / "runtime").mkdir(parents=True)
    qreceipt = local.discard_stage_runtime(qlora, run_id="rtx5050-qlora")
    outcome = local.write_stage_outcome(
        root,
        stage="qlora",
        outcome={
            "status": "timeout",
            "stop_reason": "global_deadline",
            "telemetry": "qlora/telemetry.jsonl",
            "discard_receipt": qreceipt,
        },
        now_utc="2026-08-24T10:00:05Z",
        now_monotonic=7305.0,
        boot_identity="boot-A",
    )
    assert outcome["completed_monotonic"] == 7300.0
    assert outcome["post_deadline_sealing_seconds"] == 5.0
    manifest = local.finalize_local_decision(
        root,
        now_utc="2026-08-24T10:00:06Z",
        now_monotonic=7306.0,
        boot_identity="boot-A",
    )
    assert manifest["elapsed_seconds"] == 7200.0
    assert local.verify_local_decision(root)["verified"] is True


def test_parent_interruption_still_writes_terminal_sample(tmp_path: Path) -> None:
    path = tmp_path / "telemetry.jsonl"
    sampler = local.TelemetryRecorder(path, stage="lora")
    sampler.record(
        monotonic_seconds=1.0,
        timestamp_utc="2026-08-24T08:00:01Z",
        values=local.null_telemetry_values("not sampled"),
    )
    sampler.finish(
        monotonic_seconds=1.5,
        timestamp_utc="2026-08-24T08:00:02Z",
        values=local.null_telemetry_values("parent interrupted"),
        stop_reason="parent_interrupted",
    )
    assert local.verify_telemetry(path, expected_stage="lora")[-1][
        "stop_reason"
    ] == "parent_interrupted"


def test_monitored_parent_interruption_copies_deterministic_events_and_cleans_runtime(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _initialise(tmp_path)
    repo_root = tmp_path / "fake-repo"
    repo_root.mkdir()
    stage_root = root / "lora"
    child_events = local._local_child_events_path(stage_root, "lora")
    popen_calls: list[dict[str, object]] = []

    class FakePopen:
        pid = 4242

        def __init__(self, command: list[str], **kwargs: object) -> None:
            self.returncode: int | None = None
            self.poll_count = 0
            self.terminate_count = 0
            self.kill_count = 0
            popen_calls.append({"command": command, "kwargs": kwargs, "process": self})
            _write_jsonl(child_events, _partial_lora_events())
            stdout = kwargs["stdout"]
            stderr = kwargs["stderr"]
            stdout.write("fake child started\n")
            stderr.write("fake child interrupted\n")
            stdout.flush()
            stderr.flush()

        def poll(self) -> int | None:
            self.poll_count += 1
            if self.poll_count >= 3:
                self.returncode = 130
            return self.returncode

        def terminate(self) -> None:
            self.terminate_count += 1

        def kill(self) -> None:
            self.kill_count += 1
            self.returncode = -9

        def wait(self, timeout: float | None = None) -> int:
            del timeout
            assert self.returncode is not None
            return self.returncode

    clock = {"now": 120.0}

    def fake_monotonic() -> float:
        clock["now"] += 0.25
        return clock["now"]

    def interrupt_sample(*args: object, **kwargs: object) -> dict[str, object]:
        del args, kwargs
        raise KeyboardInterrupt

    monkeypatch.setattr(local.time, "monotonic", fake_monotonic)
    monkeypatch.setattr(local, "_utc_now", lambda: "2026-08-24T08:00:30Z")
    monkeypatch.setattr(local, "_boot_identity", lambda: "boot-A")
    monkeypatch.setattr(local.subprocess, "Popen", FakePopen)
    monkeypatch.setattr(local, "sample_parent_telemetry", interrupt_sample)

    outcome = local.run_monitored_training_stage(
        SimpleNamespace(decision_root=root, repo_root=repo_root), stage="lora"
    )

    assert outcome["status"] == "interrupted"
    assert outcome["stop_reason"] == "parent_interrupted"
    assert not (stage_root / "runtime").exists()
    local.verify_stage_discard(stage_root, outcome["discard_receipt"])
    copied_events = stage_root / "optimizer-events.jsonl"
    events = load_run_events(copied_events, expected_run_id="rtx5050-lora")
    assert [event.event_kind for event in events] == [
        RunEventKind.RUN_START,
        RunEventKind.STEP_TIMING,
    ]
    terminal = local.verify_telemetry(
        stage_root / "telemetry.jsonl", expected_stage="lora"
    )[-1]
    assert terminal["terminal"] is True
    assert terminal["stop_reason"] == "parent_interrupted"
    assert len(popen_calls) == 1
    call = popen_calls[0]
    assert call["kwargs"]["shell"] is False
    assert call["kwargs"]["env"]["HF_HUB_OFFLINE"] == "1"
    process = call["process"]
    assert process.terminate_count == 0
    assert process.kill_count == 0


def test_local_training_controls_are_frozen_and_not_smoke_mutated(tmp_path: Path) -> None:
    from src.model_adaptation.training import build_phase40_local_decision_config

    config = build_phase40_local_decision_config(
        adaptation_mode="qlora",
        train_split_path=tmp_path / "train.jsonl",
        val_split_path=tmp_path / "val.jsonl",
        base_model_path=tmp_path / "base",
        decision_stage_root=tmp_path / "decision/qlora",
    )
    assert config.per_device_train_batch_size == 1
    assert config.gradient_accumulation_steps == 4
    assert config.max_seq_length == 1024
    assert config.num_train_epochs == 3.0
    assert config.seed == config.data_seed == 42
    assert config.probe_warmup_steps == 5
    assert config.probe_post_warmup_steps == 40
    assert config.max_steps == 45
    assert config.smoke_test is False
    assert config.trust_remote_code is False
    assert config.dataloader_num_workers == 0
