"""Fixture-only tests for Phase 40 timing and disposable probe contracts."""

from __future__ import annotations

from dataclasses import asdict, replace
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from src.model_adaptation.phase40_callbacks import (
    CallbackEventKind,
    NoArtifactReceipt,
    Phase40CallbackEvent,
    Phase40EvidenceCallback,
    Phase40ResourceSummary,
    PrestartFailureEvidence,
    PrestartFailureStage,
    ProbeExecutionContract,
    create_no_artifact_receipt,
    discard_probe_artifact,
    require_completed_probe,
    require_full_run_event_stream,
    require_registry_publication_allowed,
    validate_probe_target_steps,
    verify_no_artifact_receipt,
    verify_prestart_failure_evidence,
    verify_probe_discard_receipt,
    write_probe_discard_receipt,
)
from src.model_adaptation.phase40_contract import (
    CanonicalSnapshotRow,
    CanonicalSplitSnapshot,
    HeldOutIdentity,
    Phase40DataContract,
    SplitIdentity,
    derive_snapshot_row_id,
)
from src.model_adaptation.phase40_evidence import (
    AcceleratorIdentity,
    CadenceControls,
    CanonicalSplitEvidence,
    DecoderContractEvidence,
    ExperimentIdentityEvidence,
    NamedControl,
    OptimizerControls,
    PrecisionControls,
    QuantizationProofEvidence,
    ResumeControlledConfig,
    RunEventKind,
    TransferAuthorityEvidence,
    append_run_event,
    load_run_events,
)
from src.model_adaptation.phase40_modes import (
    AdaptationMode,
    ExperimentIdentity,
    ModelFamily,
    QuantizationProof,
    ResolvedQwenMode,
    RunKind,
)
from src.model_adaptation.phase40_metrics import (
    Phase40PredictionRow,
    evaluate_phase40_predictions,
    select_phase40_checkpoint,
)
from src.model_adaptation.phase40_handoff import (
    FullRunRequestIdentity,
    RequestedControlTemplate,
    RunRequest,
)
from src.data_pipeline.schemas import DatasetRecord
from src.model_adaptation.schemas import PilotSelection
from src.model_adaptation.training import (
    PHASE40_BASE_MODEL_MANIFEST_NAME,
    PHASE40_QWEN_MODEL_ID,
    PHASE40_QWEN_REVISION,
    PHASE40_RESUME_HISTORY_NAME,
    PHASE40_RESUME_MANIFEST_NAME,
    Phase40ValidationRecorder,
    _append_callback_run_event,
    _append_full_run_finalization_events,
    _append_runtime_failure_event,
    _callback_event_to_run_event,
    _checkpoint_payload_sha256,
    _build_training_arguments,
    _complete_full_qwen_training,
    _install_measured_checkpoint_wrapper,
    _load_pinned_qwen_base_components,
    _materialize_and_commit_full_run_evidence,
    _materialize_full_run_evidence,
    _prepare_full_run_bundle_root,
    _probe_root,
    _read_checkpoint_resume_manifest,
    _resolve_resume_checkpoint,
    _resume_state_with_failed_suffix,
    _run_post_train_finalization_transaction,
    _write_checkpoint_resume_manifest,
    _verify_requested_runtime_controls,
    _verify_training_argument_controls,
    build_phase40_local_decision_config,
    build_qwen_base_model_acquisition_request,
    build_qwen_base_model_provenance,
    build_phase40_qwen_training_config,
    build_training_config,
    run_phase40_qwen_training,
    run_training,
    seal_qwen_base_model_snapshot,
    validate_qwen_base_model_snapshot,
    verify_qwen_base_model_provenance,
)


class FakeClock:
    def __init__(self) -> None:
        self.value = 0.0

    def __call__(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


class FakeCuda:
    def __init__(self, *, allocated: int = 1_000, reserved: int = 2_000) -> None:
        self.allocated = allocated
        self.reserved = reserved
        self.calls: list[str] = []

    def synchronize(self) -> None:
        self.calls.append("synchronize")

    def reset_peak_memory_stats(self) -> None:
        self.calls.append("reset_peak_memory_stats")

    def max_memory_allocated(self) -> int:
        self.calls.append("max_memory_allocated")
        return self.allocated

    def max_memory_reserved(self) -> int:
        self.calls.append("max_memory_reserved")
        return self.reserved


def test_transformers_v5_fractional_warmup_and_token_counter_are_verified(
    tmp_path: Path,
) -> None:
    transformers = pytest.importorskip("transformers")
    config = build_phase40_local_decision_config(
        adaptation_mode="lora",
        train_split_path=tmp_path / "train.jsonl",
        val_split_path=tmp_path / "val.jsonl",
        base_model_path=tmp_path / "base",
        decision_stage_root=tmp_path / "decision/lora",
    )
    arguments = _build_training_arguments(
        transformers,
        config,
        tmp_path / "trainer",
        has_eval_data=True,
        device="cuda",
        use_bf16=False,
    )
    assert arguments.warmup_steps == 0.03
    assert arguments.warmup_ratio is None
    assert arguments.get_warmup_steps(config.max_steps) == 2
    assert arguments.include_num_input_tokens_seen == "all"
    _verify_training_argument_controls(
        arguments,
        config,
        device="cuda",
        use_bf16=False,
    )

    arguments.warmup_ratio = 0.03
    with pytest.raises(RuntimeError, match="warm-up controls"):
        _verify_training_argument_controls(
            arguments,
            config,
            device="cuda",
            use_bf16=False,
        )
    arguments.warmup_ratio = None
    arguments.include_num_input_tokens_seen = "yes"
    with pytest.raises(RuntimeError, match="include_num_input_tokens_seen"):
        _verify_training_argument_controls(
            arguments,
            config,
            device="cuda",
            use_bf16=False,
        )


FIXED_UTC = datetime(2026, 8, 24, 12, 0, tzinfo=timezone.utc)


def _sealed_qwen_snapshot(root: Path):
    root.mkdir(parents=True)
    (root / "config.json").write_text("{}\n", encoding="utf-8")
    (root / "tokenizer_config.json").write_text("{}\n", encoding="utf-8")
    (root / "model.safetensors").write_bytes(b"fixture-qwen-weights")
    return seal_qwen_base_model_snapshot(root)


def _lora_quantization_proof() -> QuantizationProof:
    return QuantizationProof(
        requested_mode=AdaptationMode.LORA,
        resolved_mode=ResolvedQwenMode.FULL_PRECISION_LORA,
        bitsandbytes_version=None,
        load_in_4bit=False,
        nf4=False,
        double_quantization=False,
        is_loaded_in_4bit=False,
        linear4bit_modules=0,
        kbit_preparation_applied=False,
        base_weights_frozen=True,
        adapter_only_trainables=True,
        adapter_trainable_count=2,
        backward_with_adapter_gradients=False,
        adapter_gradient_finite_count=0,
        adapter_gradient_nonzero_count=0,
    )


def _resume_config(*, seed: int = 42) -> ResumeControlledConfig:
    split_sha = hashlib.sha256(b"split").hexdigest()
    row_sha = hashlib.sha256(b"rows").hexdigest()
    return ResumeControlledConfig(
        schema_version="phase40-resume-controlled-config-v1",
        experiment_identity=ExperimentIdentityEvidence(
            model_family=ModelFamily.QWEN,
            adaptation_mode=AdaptationMode.LORA,
            run_kind=RunKind.FULL,
        ),
        model_id="qwen3-4b-instruct-2507",
        model_revision=PHASE40_QWEN_REVISION,
        splits=(
            CanonicalSplitEvidence(
                logical_name="train",
                relative_path="data/splits/train.jsonl",
                records=4,
                bytes=40,
                sha256=split_sha,
                ordered_row_ids_sha256=row_sha,
            ),
            CanonicalSplitEvidence(
                logical_name="val",
                relative_path="data/splits/val.jsonl",
                records=4,
                bytes=40,
                sha256=split_sha,
                ordered_row_ids_sha256=row_sha,
            ),
        ),
        formatter_or_preprocessor_sha256="1" * 64,
        response_mask_or_preprocessor_version="phase40-response-only-mask-v1",
        label_order=(
            "bank_impersonation",
            "zalo_social_engineering",
            "task_scam",
            "benign",
        ),
        seed=seed,
        data_seed=42,
        max_sequence_length=1024,
        truncation_policy="reject-over-max",
        per_device_train_batch_size=1,
        gradient_accumulation_steps=4,
        world_size=1,
        effective_batch_size=4,
        num_train_epochs=3.0,
        max_optimizer_steps=100,
        gradient_checkpointing=True,
        lora_rank=16,
        lora_alpha=32,
        lora_dropout=0.05,
        lora_bias="none",
        target_modules=(
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ),
        task_type="CAUSAL_LM",
        optimizer=OptimizerControls(
            optimizer="adamw_torch",
            learning_rate=2e-4,
            weight_decay=0.0,
            lr_scheduler_type="linear",
            warmup_steps=0,
            warmup_ratio=0.03,
            max_grad_norm=1.0,
        ),
        precision=PrecisionControls(
            compute_dtype="float16",
            adapter_dtype="float32",
            bf16=False,
            fp16=True,
            tf32=False,
        ),
        cadence=CadenceControls(
            logging_steps=10,
            evaluation_steps=50,
            save_steps=50,
            save_total_limit=2,
            generation_steps=(50, 100),
        ),
        decoder=DecoderContractEvidence(
            schema_version="phase40-qwen-decoder-v1",
            do_sample=False,
            num_return_sequences=1,
            max_new_tokens=256,
            output_schema_version="phase40-prediction-row-v1",
            decoder_version="phase40-qwen-greedy-v1",
            generation_cadence="every-validation-checkpoint-and-final",
            raw_prediction_ordering_policy="canonical-validation-sequence",
        ),
        checkpoint_selection_policy="macro-f1-safety-gate",
        checkpoint_selection_policy_version="phase40-checkpoint-selection-v1",
        snapshot_id_algorithm_version="phase40-snapshot-row-id-v1",
        quantization_proof=QuantizationProofEvidence(**asdict(_lora_quantization_proof())),
        accelerator=AcceleratorIdentity(
            accelerator_type="cuda",
            accelerator_name="fixture-gpu",
            compute_capability="8.9",
            total_memory_bytes=8_000_000,
        ),
        additional_controls=(NamedControl(name="report_to", value="none"),),
    )


def _requested_template(config: ResumeControlledConfig) -> RequestedControlTemplate:
    payload = config.model_dump(mode="json")
    payload.pop("accelerator")
    return RequestedControlTemplate(controls_without_accelerator=payload)


def _selection() -> PilotSelection:
    return PilotSelection(
        baseline_winner_id="qwen3-4b-instruct-2507",
        runner_up_id="qwen3.5-4b",
        selection_notes="Phase 40 fixture selection.",
    )


def _transfer_authority() -> TransferAuthorityEvidence:
    return TransferAuthorityEvidence(
        schema_version="phase40-transfer-authority-v1",
        source_archive_sha256="a" * 64,
        source_inventory_sha256="b" * 64,
        input_archive_sha256="c" * 64,
        input_manifest_sha256="d" * 64,
        source_repository_relative_archive_path=(
            "data/models/phase40/source/phase40-source.zip"
        ),
        source_repository_relative_inventory_path=(
            "data/models/phase40/source/phase40-source-manifest.json"
        ),
        input_repository_relative_path=(
            "data/models/phase40/input/phase40-train-validation.zip"
        ),
        input_drive_path=(
            "/content/drive/MyDrive/internship-phase40/phase40-train-validation.zip"
        ),
        input_extraction_root="/content/phase40-input-v1",
        input_members=("phase40-input-manifest.json", "train.jsonl", "val.jsonl"),
        no_held_out_boundary=True,
    )


def _fixture_contract(tmp_path: Path, *, all_labels: bool = False) -> Phase40DataContract:
    base_record = DatasetRecord(
        text="Ngân hàng yêu cầu gửi mã OTP ngay.",
        label="bank_impersonation",
        risk_tier="high-risk",
        suspicious_spans=["mã OTP"],
        xai_explanation="Yêu cầu OTP dưới danh nghĩa ngân hàng.",
        source="synthetic_claude",
        seed_id="fixture-root",
    )
    labels = (
        "bank_impersonation",
        "zalo_social_engineering",
        "task_scam",
        "benign",
    )
    records = (
        tuple(
            base_record.model_copy(
                update={
                    "label": label,
                    "risk_tier": "benign" if label == "benign" else "high-risk",
                    "suspicious_spans": [] if label == "benign" else ["mã OTP"],
                    "seed_id": f"fixture-{label}",
                }
            )
            for label in labels
        )
        if all_labels
        else (base_record,)
    )

    def snapshot(split_name: str) -> CanonicalSplitSnapshot:
        record_payloads = tuple(record.model_dump_json().encode("utf-8") for record in records)
        whole = b"".join(payload + b"\n" for payload in record_payloads)
        identity = SplitIdentity(
            split_name=split_name,
            relative_path=f"data/splits/{split_name}.jsonl",
            records=len(records),
            bytes=len(whole),
            sha256=hashlib.sha256(whole).hexdigest(),
            label_counts=tuple(
                (label, sum(record.label == label for record in records)) for label in labels
            ),
        )
        rows = tuple(
            CanonicalSnapshotRow(
                split_name=split_name,
                canonical_index=index,
                record_bytes=record_bytes,
                record=record,
                raw_message=record.text,
                source_row_sha256=hashlib.sha256(record_bytes).hexdigest(),
                snapshot_row_id=derive_snapshot_row_id(
                    split_name,
                    index,
                    hashlib.sha256(record_bytes).hexdigest(),
                ),
            )
            for index, (record, record_bytes) in enumerate(zip(records, record_payloads, strict=True))
        )
        return CanonicalSplitSnapshot(
            split_name=split_name,
            identity=identity,
            whole_file_bytes=whole,
            whole_file_sha256=identity.sha256,
            rows=rows,
        )

    train = snapshot("train")
    val = snapshot("val")
    return Phase40DataContract(
        ordered_identities=(train.identity, val.identity),
        train_snapshot=train,
        validation_snapshot=val,
        held_out_test=HeldOutIdentity(
            path="data/splits/test.jsonl",
            records=1,
            bytes=1,
            sha256="0" * 64,
            evaluation_phase=41,
            touch_policy="opaque fixture metadata only",
        ),
    )


def _probe_identity(mode: AdaptationMode = AdaptationMode.LORA) -> ExperimentIdentity:
    return ExperimentIdentity(ModelFamily.QWEN, mode, RunKind.PROBE)


def test_probe_callback_synchronizes_excludes_warmup_and_derives_exact_eta():
    clock = FakeClock()
    cuda = FakeCuda()
    sink: list[object] = []
    callback = Phase40EvidenceCallback(
        run_id="probe-qwen-lora",
        run_kind=RunKind.PROBE,
        warmup_optimizer_steps=1,
        target_post_warmup_steps=30,
        examples_per_optimizer_step=4,
        planned_full_optimizer_steps=100,
        event_sink=sink.append,
        clock=clock,
        utc_clock=lambda: FIXED_UTC,
        cuda=cuda,
    )
    state = SimpleNamespace(global_step=0, epoch=0.0, num_input_tokens_seen=0)
    control = object()

    assert callback.on_train_begin(None, state, control) is control
    for step in range(1, 32):
        assert callback.on_step_begin(None, state, control) is control
        clock.advance(100.0 if step == 1 else float(step - 1))
        state.global_step = step
        state.epoch = step / 31
        state.num_input_tokens_seen += 100
        assert callback.on_step_end(None, state, control) is control

    assert callback.on_log(None, state, control, logs={"loss": 0.25}) is control
    assert (
        callback.on_evaluate(
            None,
            state,
            control,
            metrics={"eval_loss": 0.5, "eval_runtime": 3.0},
        )
        is control
    )
    assert callback.on_save(None, state, control, checkpoint_runtime_seconds=5.0) is control
    clock.advance(8.0)
    assert callback.on_train_end(None, state, control) is control

    summary = callback.summary()
    assert summary.retained_optimizer_steps == 30
    assert summary.observed_optimizer_steps == 31
    assert summary.steady_state_step_seconds_median == 15.5
    assert summary.examples_per_second == pytest.approx(120 / 465)
    assert summary.tokens_per_second == pytest.approx(3_000 / 465)
    assert summary.peak_allocated_bytes == 1_000
    assert summary.peak_reserved_bytes == 2_000
    assert summary.evaluation_overhead_seconds == 3.0
    assert summary.checkpoint_overhead_seconds == 5.0
    assert summary.measured_overhead_seconds == 8.0
    assert summary.projected_local_runtime_seconds == 15.5 * 100 + 8.0
    assert summary.projected_local_runtime_is_estimate is True
    assert summary.actual_wall_seconds == 573.0

    assert cuda.calls.count("reset_peak_memory_stats") == 1
    assert cuda.calls.count("synchronize") == 64
    events = callback.events
    assert tuple(event.sequence_id for event in events) == tuple(range(len(events)))
    assert sink == list(events)
    assert events[1].event_kind == CallbackEventKind.OPTIMIZER_STEP
    assert events[1].is_warmup is True
    assert events[2].is_warmup is False
    assert all(event.run_kind == RunKind.PROBE for event in events)
    assert events[-3].optimizer_step == events[-2].optimizer_step
    with pytest.raises(ValueError, match="probe events"):
        require_full_run_event_stream(events)


def test_callback_refuses_nan_logs_and_unmeasured_overhead():
    clock = FakeClock()
    callback = Phase40EvidenceCallback(
        run_id="full-fixture",
        run_kind=RunKind.FULL,
        warmup_optimizer_steps=0,
        examples_per_optimizer_step=1,
        tokens_per_optimizer_step=10,
        planned_full_optimizer_steps=1,
        clock=clock,
        utc_clock=lambda: FIXED_UTC,
    )
    state = SimpleNamespace(global_step=0, epoch=0.0)
    control = object()
    callback.on_train_begin(None, state, control)
    with pytest.raises(ValueError, match="finite"):
        callback.on_log(None, state, control, logs={"loss": float("nan")})
    callback.on_step_begin(None, state, control)
    clock.advance(1.0)
    state.global_step = 1
    callback.on_step_end(None, state, control)
    callback.on_evaluate(None, state, control, metrics={"eval_loss": 0.2})
    callback.on_save(None, state, control)
    clock.advance(1.0)
    callback.on_train_end(None, state, control)
    with pytest.raises(RuntimeError, match="without eval_runtime"):
        callback.summary()


@pytest.mark.parametrize("target", [None, True, 29, 51, 30.0])
def test_probe_target_rejects_every_value_outside_integer_30_to_50(target):
    with pytest.raises(ValueError, match="probe target"):
        validate_probe_target_steps(target)


def test_probe_contract_locks_cap_and_rejects_resume_before_trainer_start():
    contract = ProbeExecutionContract(
        run_id="probe-30",
        requested_identity=_probe_identity(),
        target_post_warmup_steps=30,
        warmup_optimizer_steps=5,
    )
    assert contract.total_optimizer_steps == 35
    assert validate_probe_target_steps(30) == 30
    assert validate_probe_target_steps(50) == 50

    trainer = Mock()
    with pytest.raises(ValueError, match="cannot accept resume"):
        ProbeExecutionContract(
            run_id="probe-resume",
            requested_identity=_probe_identity(),
            target_post_warmup_steps=40,
            resume_from_checkpoint="checkpoint-10",
        )
    trainer.assert_not_called()


def test_registry_guard_leaves_publisher_unreachable_for_probe_or_incomplete_full():
    publisher = Mock()
    with pytest.raises(RuntimeError, match="never registry-publishable"):
        require_registry_publication_allowed(
            run_kind=RunKind.PROBE,
            evidence_complete=True,
            evidence_verified=True,
        )
    with pytest.raises(RuntimeError, match="complete hash-verified"):
        require_registry_publication_allowed(
            run_kind=RunKind.FULL,
            evidence_complete=False,
            evidence_verified=True,
        )
    publisher.assert_not_called()

    require_registry_publication_allowed(
        run_kind=RunKind.FULL,
        evidence_complete=True,
        evidence_verified=True,
    )
    publisher("verified-full")
    publisher.assert_called_once_with("verified-full")


def _completed_probe_summary(run_id: str) -> Phase40ResourceSummary:
    return Phase40ResourceSummary(
        source_run_id=run_id,
        run_kind=RunKind.PROBE,
        warmup_optimizer_steps=5,
        observed_optimizer_steps=35,
        retained_optimizer_steps=30,
        steady_state_step_seconds_median=2.0,
        examples_per_second=1.0,
        tokens_per_second=10.0,
        peak_allocated_bytes=100,
        peak_reserved_bytes=200,
        evaluation_overhead_seconds=3.0,
        checkpoint_overhead_seconds=4.0,
        measured_overhead_seconds=7.0,
        actual_wall_seconds=80.0,
        planned_full_optimizer_steps=100,
        projected_local_runtime_seconds=207.0,
    )


def test_probe_success_requires_bounded_removal_and_verified_discard_receipt(tmp_path):
    probe_root = tmp_path / "probe"
    adapter = probe_root / "adapter"
    adapter.mkdir(parents=True)
    (adapter / "adapter.bin").write_bytes(b"fixture-adapter")
    (adapter / "config.json").write_text("{}", encoding="utf-8")

    receipt = discard_probe_artifact(
        run_id="probe-success",
        probe_root=probe_root,
        discarded_path_identity="adapter",
    )
    assert not adapter.exists()
    assert len(receipt.pre_discard_sha256) == 64
    verify_probe_discard_receipt(receipt, probe_root=probe_root)

    receipt_path = probe_root / "discard-receipt.json"
    assert write_probe_discard_receipt(receipt, receipt_path) == receipt_path
    assert write_probe_discard_receipt(receipt, receipt_path) == receipt_path
    with pytest.raises(FileExistsError, match="different"):
        write_probe_discard_receipt(
            replace(receipt, pre_discard_sha256="0" * 64),
            receipt_path,
        )

    contract = ProbeExecutionContract(
        run_id="probe-success",
        requested_identity=_probe_identity(),
        target_post_warmup_steps=30,
        warmup_optimizer_steps=5,
    )
    require_completed_probe(
        contract=contract,
        summary=_completed_probe_summary("probe-success"),
        discard_receipt=receipt,
        probe_root=probe_root,
    )

    adapter.mkdir()
    with pytest.raises(ValueError, match="exists again"):
        require_completed_probe(
            contract=contract,
            summary=_completed_probe_summary("probe-success"),
            discard_receipt=receipt,
            probe_root=probe_root,
        )


def test_discard_rejects_traversal_without_touching_outside_file(tmp_path):
    probe_root = tmp_path / "probe"
    probe_root.mkdir()
    outside = tmp_path / "outside.bin"
    outside.write_bytes(b"must-survive")

    with pytest.raises(ValueError, match="unsafe|relative"):
        discard_probe_artifact(
            run_id="probe-unsafe",
            probe_root=probe_root,
            discarded_path_identity="../outside.bin",
        )
    assert outside.read_bytes() == b"must-survive"


def test_prestart_failure_requires_identity_authority_environment_and_no_artifacts(tmp_path):
    probe_root = tmp_path / "probe"
    probe_root.mkdir()
    no_artifacts = create_no_artifact_receipt(
        run_id="probe-prestart",
        probe_root=probe_root,
        expected_path_identities=("adapter", "checkpoints"),
    )
    evidence = PrestartFailureEvidence(
        run_id="probe-prestart",
        requested_identity=_probe_identity(AdaptationMode.QLORA),
        failure_stage=PrestartFailureStage.CAPABILITY_PREFLIGHT,
        environment_reference="environment.json#sha256-fixture",
        authority_reference="package-authority.json#decision-rejected",
        no_artifact_receipt=no_artifacts,
    )
    verify_prestart_failure_evidence(evidence, probe_root=probe_root)
    assert evidence.requested_identity.adaptation_mode == AdaptationMode.QLORA

    with pytest.raises(ValueError, match="authority_reference"):
        PrestartFailureEvidence(
            run_id="probe-prestart",
            requested_identity=_probe_identity(AdaptationMode.QLORA),
            failure_stage=PrestartFailureStage.PACKAGE_AUTHORITY,
            environment_reference="environment.json",
            authority_reference="",
            no_artifact_receipt=no_artifacts,
        )

    (probe_root / "adapter").mkdir()
    with pytest.raises(ValueError, match="unexpectedly exists"):
        verify_no_artifact_receipt(no_artifacts, probe_root=probe_root)


def test_no_artifact_receipt_rejects_run_drift_and_unsafe_identities():
    with pytest.raises(ValueError, match="unsafe"):
        NoArtifactReceipt(
            run_id="probe",
            expected_path_identities=("../adapter",),
            paths_absent=True,
        )

    receipt = NoArtifactReceipt(
        run_id="different-run",
        expected_path_identities=("adapter",),
        paths_absent=True,
    )
    with pytest.raises(ValueError, match="run IDs differ"):
        PrestartFailureEvidence(
            run_id="probe",
            requested_identity=_probe_identity(),
            failure_stage=PrestartFailureStage.MODE_PROOF,
            environment_reference="environment.json",
            authority_reference="authority.json",
            no_artifact_receipt=receipt,
        )


def test_callback_event_maps_losslessly_to_append_only_run_event(tmp_path):
    callback_event = Phase40CallbackEvent(
        sequence_id=0,
        source_run_id="full-fixture",
        run_kind=RunKind.FULL,
        event_kind=CallbackEventKind.OPTIMIZER_STEP,
        timestamp_utc="2026-08-24T12:00:00Z",
        optimizer_step=7,
        epoch=0.5,
        duration_seconds=1.25,
        is_warmup=False,
        values=(("loss", 0.75), ("tokens", 128)),
    )
    event = _callback_event_to_run_event(callback_event)
    assert event.event_kind == RunEventKind.STEP_TIMING
    assert event.run_kind == RunKind.FULL
    assert event.trainer_values == {
        "loss": 0.75,
        "tokens": 128,
        "callback_event_kind": "optimizer_step",
        "run_kind": "full",
        "epoch_observed": True,
        "duration_seconds": 1.25,
        "is_warmup": False,
    }

    event_path = tmp_path / "outside-trainer" / "events.jsonl"
    _append_callback_run_event(event_path, callback_event)
    loaded = load_run_events(event_path, expected_run_id="full-fixture")
    assert loaded == (event,)
    assert event_path.parent.name == "outside-trainer"


def test_exact_resume_manifest_rejects_control_or_payload_drift(tmp_path):
    training_root = tmp_path / "trainer"
    checkpoint = training_root / "checkpoint-7"
    checkpoint.mkdir(parents=True)
    (checkpoint / "adapter_model.bin").write_bytes(b"checkpoint-state")
    (checkpoint / "trainer_state.json").write_text(
        json.dumps({"global_step": 7}),
        encoding="utf-8",
    )
    controlled = _resume_config()
    manifest_path = _write_checkpoint_resume_manifest(
        checkpoint,
        checkpoint_step=7,
        controlled_config=controlled,
    )
    assert manifest_path.name == PHASE40_RESUME_MANIFEST_NAME
    assert len(_checkpoint_payload_sha256(checkpoint)) == 64

    config = SimpleNamespace(
        run_kind=RunKind.FULL,
        resume_from_checkpoint=str(checkpoint),
    )
    assert _resolve_resume_checkpoint(config, training_root, controlled) == checkpoint.resolve()
    with pytest.raises(RuntimeError, match="not exactly compatible"):
        _resolve_resume_checkpoint(config, training_root, _resume_config(seed=43))

    (checkpoint / "adapter_model.bin").write_bytes(b"mutated-checkpoint-state")
    with pytest.raises(RuntimeError, match="payload SHA-256"):
        _read_checkpoint_resume_manifest(checkpoint, controlled_config=controlled)


def test_resume_rejects_latest_and_fresh_run_rejects_existing_checkpoint(tmp_path):
    with pytest.raises(ValueError, match="latest"):
        _resolve_resume_checkpoint(
            SimpleNamespace(run_kind=RunKind.FULL, resume_from_checkpoint="latest"),
            tmp_path / "missing",
            _resume_config(),
        )

    training_root = tmp_path / "trainer"
    (training_root / "checkpoint-9").mkdir(parents=True)
    with pytest.raises(RuntimeError, match="fresh full run found existing checkpoints"):
        _resolve_resume_checkpoint(
            SimpleNamespace(run_kind=RunKind.FULL, resume_from_checkpoint=None),
            training_root,
            None,
        )


def test_measured_checkpoint_wrapper_seals_manifest_after_real_save_hook(tmp_path):
    training_root = tmp_path / "trainer"
    state = SimpleNamespace(global_step=5)

    class FakeTrainer:
        def __init__(self):
            self.state = state

        def _save_checkpoint(self):
            checkpoint = training_root / "checkpoint-5"
            checkpoint.mkdir(parents=True)
            (checkpoint / "adapter_model.bin").write_bytes(b"state")
            (checkpoint / "trainer_state.json").write_text(
                json.dumps({"global_step": 5}),
                encoding="utf-8",
            )
            return "saved"

    times = iter((10.0, 12.5))
    cuda = FakeCuda()
    trainer = FakeTrainer()
    durations: list[float] = []
    returned = _install_measured_checkpoint_wrapper(
        trainer,
        training_output_dir=training_root,
        controlled_config=_resume_config(),
        cuda_timing=cuda,
        clock=lambda: next(times),
        checkpoint_durations=durations,
    )
    assert returned is durations
    assert trainer._save_checkpoint() == "saved"
    assert durations == [2.5]
    assert cuda.calls[:2] == ["synchronize", "synchronize"]
    assert (training_root / "checkpoint-5" / PHASE40_RESUME_MANIFEST_NAME).is_file()


def test_callback_resume_aggregates_telemetry_and_can_finish_without_new_steps():
    clock = FakeClock()
    first_state = SimpleNamespace(global_step=0, epoch=0.0, num_input_tokens_seen=0)
    first = Phase40EvidenceCallback(
        run_id="qwen-lora-resume",
        run_kind=RunKind.FULL,
        warmup_optimizer_steps=0,
        examples_per_optimizer_step=2,
        planned_full_optimizer_steps=2,
        clock=clock,
        utc_clock=lambda: FIXED_UTC,
        cuda=FakeCuda(),
    )
    first.on_train_begin(None, first_state, None)
    first.on_step_begin(None, first_state, None)
    clock.advance(2.0)
    first_state.global_step = 1
    first_state.num_input_tokens_seen = 10
    first.on_step_end(None, first_state, None)
    first.on_evaluate(None, first_state, None, metrics={"eval_runtime": 1.0})
    first.on_save(None, first_state, None, checkpoint_runtime_seconds=0.5)
    sealed_state = first.checkpoint_state()

    final_clock = FakeClock()
    final_state = SimpleNamespace(global_step=1, epoch=0.5, num_input_tokens_seen=10)
    resumed = Phase40EvidenceCallback(
        run_id="qwen-lora-resume",
        run_kind=RunKind.FULL,
        warmup_optimizer_steps=0,
        examples_per_optimizer_step=2,
        planned_full_optimizer_steps=2,
        resume_state=sealed_state,
        clock=final_clock,
        utc_clock=lambda: FIXED_UTC,
        cuda=FakeCuda(),
    )
    resumed.on_train_begin(None, final_state, None)
    final_clock.advance(1.0)
    resumed.on_train_end(None, final_state, None)
    no_new_steps = resumed.summary()
    assert no_new_steps.observed_optimizer_steps == 1
    assert no_new_steps.retained_optimizer_steps == 1
    assert no_new_steps.steady_state_step_seconds_median == 2.0
    assert no_new_steps.actual_wall_seconds == 3.0
    assert no_new_steps.evaluation_overhead_seconds == 1.0
    assert no_new_steps.checkpoint_overhead_seconds == 0.5

    aggregate_clock = FakeClock()
    aggregate_state = SimpleNamespace(global_step=1, epoch=0.5, num_input_tokens_seen=10)
    aggregate = Phase40EvidenceCallback(
        run_id="qwen-lora-resume",
        run_kind=RunKind.FULL,
        warmup_optimizer_steps=0,
        examples_per_optimizer_step=2,
        planned_full_optimizer_steps=2,
        resume_state=sealed_state,
        clock=aggregate_clock,
        utc_clock=lambda: FIXED_UTC,
        cuda=FakeCuda(allocated=1_500, reserved=2_500),
    )
    aggregate.on_train_begin(None, aggregate_state, None)
    aggregate.on_step_begin(None, aggregate_state, None)
    aggregate_clock.advance(3.0)
    aggregate_state.global_step = 2
    aggregate_state.num_input_tokens_seen = 20
    aggregate.on_step_end(None, aggregate_state, None)
    aggregate.on_evaluate(None, aggregate_state, None, metrics={"eval_runtime": 2.0})
    aggregate.on_save(None, aggregate_state, None, checkpoint_runtime_seconds=0.75)
    aggregate_clock.advance(1.0)
    aggregate.on_train_end(None, aggregate_state, None)
    summary = aggregate.summary()
    assert summary.observed_optimizer_steps == 2
    assert summary.retained_optimizer_steps == 2
    assert summary.steady_state_step_seconds_median == 2.5
    assert summary.examples_per_second == pytest.approx(0.8)
    assert summary.tokens_per_second == pytest.approx(4.0)
    assert summary.evaluation_overhead_seconds == 3.0
    assert summary.checkpoint_overhead_seconds == 1.25
    assert summary.actual_wall_seconds == 6.0
    assert summary.peak_allocated_bytes == 1_500


def _resume_history_fixture(tmp_path: Path):
    contract = _fixture_contract(tmp_path / "data", all_labels=True)
    retained_root = tmp_path / "retained"
    identity_by_name: dict[str, str] = {}
    recorder = Phase40ValidationRecorder(
        tokenizer=None,
        candidate=None,
        validation_snapshot=contract.validation_snapshot,
        training_output_dir=tmp_path / "trainer",
        prediction_output_dir=tmp_path / "predictions",
        retained_artifact_root=retained_root,
        artifact_identity_prover=lambda _model, _path: "unused",
        stored_artifact_identity_loader=lambda path: identity_by_name[path.name],
    )
    for step, digit in ((5, "a"), (10, "b")):
        identity = f"adapter-state-sha256:{digit * 64}"
        retained = retained_root / f"step-{step}-{digit * 64}"
        retained.mkdir(parents=True)
        (retained / "adapter_config.json").write_text("{}\n", encoding="utf-8")
        (retained / "adapter_model.bin").write_bytes(f"adapter-{step}".encode("ascii"))
        identity_by_name[retained.name] = identity
        rows = tuple(
            Phase40PredictionRow.from_raw(
                validation_row_id=row.validation_row_id,
                sequence_index=index,
                gold_label=row.record.label,
                raw_prediction=json.dumps({"label": row.record.label}),
                artifact_identity=identity,
                checkpoint_step=step,
            )
            for index, row in enumerate(contract.validation_snapshot.rows)
        )
        metrics = evaluate_phase40_predictions(
            expected_validation_row_ids=contract.validation_snapshot.validation_row_ids,
            gold_labels=tuple(row.record.label for row in contract.validation_snapshot.rows),
            prediction_rows=rows,
        )
        recorder.metrics_by_candidate[(step, identity)] = metrics
        recorder.retained_paths[(step, identity)] = retained
    telemetry_state = {
        "schema_version": "phase40-callback-resume-state-v1",
        "run_id": "qwen-lora-history",
        "run_kind": "full",
        "warmup_optimizer_steps": 0,
        "examples_per_optimizer_step": 1,
        "planned_full_optimizer_steps": 10,
        "observed_optimizer_steps": 10,
        "retained_step_seconds": [1.0] * 10,
        "retained_examples": 10,
        "retained_tokens": 100,
        "evaluation_overhead_seconds": [2.0, 2.0],
        "checkpoint_overhead_seconds": [0.5, 0.5],
        "unmeasured_evaluations": 0,
        "unmeasured_checkpoints": 0,
        "peak_allocated_bytes": 100,
        "peak_reserved_bytes": 200,
        "actual_wall_seconds": 15.0,
    }
    return contract, recorder, identity_by_name, telemetry_state


def _checkpoint_event_log(path: Path) -> None:
    for sequence_id, (kind, step, duration) in enumerate(
        (
            (CallbackEventKind.TRAIN_BEGIN, 0, None),
            (CallbackEventKind.CHECKPOINT, 10, 0.5),
        )
    ):
        _append_callback_run_event(
            path,
            Phase40CallbackEvent(
                sequence_id=sequence_id,
                source_run_id="qwen-lora-history",
                run_kind=RunKind.FULL,
                event_kind=kind,
                timestamp_utc="2026-08-24T12:00:00Z",
                optimizer_step=step,
                epoch=float(step) / 10,
                duration_seconds=duration,
                is_warmup=None,
                values=(),
            ),
        )


def test_checkpoint_resume_restores_all_candidates_and_rejects_history_tamper(tmp_path):
    contract, recorder, identity_by_name, telemetry_state = _resume_history_fixture(tmp_path)
    snapshot = _sealed_qwen_snapshot(tmp_path / "base-model")
    event_path = tmp_path / "events.jsonl"
    _checkpoint_event_log(event_path)
    checkpoint = tmp_path / "trainer" / "checkpoint-10"
    checkpoint.mkdir(parents=True)
    (checkpoint / "adapter_model.bin").write_bytes(b"checkpoint-state")
    (checkpoint / "trainer_state.json").write_text(
        json.dumps({"global_step": 10}), encoding="utf-8"
    )
    controlled = _resume_config()
    history = recorder.resume_history_payload(telemetry_state)
    _write_checkpoint_resume_manifest(
        checkpoint,
        checkpoint_step=10,
        controlled_config=controlled,
        resume_history=history,
        event_path=event_path,
        base_model_snapshot=snapshot,
    )
    _read_checkpoint_resume_manifest(
        checkpoint,
        controlled_config=controlled,
        event_path=event_path,
        base_model_snapshot=snapshot,
        require_cumulative_history=True,
    )

    restored = Phase40ValidationRecorder(
        tokenizer=None,
        candidate=None,
        validation_snapshot=contract.validation_snapshot,
        training_output_dir=tmp_path / "trainer",
        prediction_output_dir=tmp_path / "predictions-restored",
        retained_artifact_root=tmp_path / "retained",
        artifact_identity_prover=lambda _model, _path: "unused",
        stored_artifact_identity_loader=lambda path: identity_by_name[path.name],
    )
    restored_state = restored.restore_resume_history(history)
    assert restored_state == telemetry_state
    assert restored.metrics_by_candidate == recorder.metrics_by_candidate
    assert restored.select() == recorder.select()

    history_path = checkpoint / PHASE40_RESUME_HISTORY_NAME
    tampered = json.loads(history_path.read_text(encoding="utf-8"))
    tampered["candidates"].pop(0)
    history_path.write_text(json.dumps(tampered), encoding="utf-8")
    with pytest.raises(RuntimeError, match="payload SHA-256|history SHA-256"):
        _read_checkpoint_resume_manifest(
            checkpoint,
            controlled_config=controlled,
            event_path=event_path,
            base_model_snapshot=snapshot,
            require_cumulative_history=True,
        )


def test_resume_history_rejects_candidate_omission_even_when_checkpoint_is_resealed(tmp_path):
    contract, recorder, identity_by_name, telemetry_state = _resume_history_fixture(tmp_path)
    omitted = recorder.resume_history_payload(telemetry_state)
    omitted["candidates"] = []
    restored = Phase40ValidationRecorder(
        tokenizer=None,
        candidate=None,
        validation_snapshot=contract.validation_snapshot,
        training_output_dir=tmp_path / "trainer",
        prediction_output_dir=tmp_path / "predictions-restored",
        retained_artifact_root=tmp_path / "retained",
        artifact_identity_prover=lambda _model, _path: "unused",
        stored_artifact_identity_loader=lambda path: identity_by_name[path.name],
    )
    with pytest.raises(RuntimeError, match="omitted its validation candidates"):
        restored.restore_resume_history(omitted)


def test_qwen_model_provenance_rejects_hash_manifest_and_revision_drift(tmp_path):
    snapshot_root = tmp_path / "base-model"
    external_manifest = tmp_path / "manifests" / "qwen.json"
    snapshot_root.mkdir()
    (snapshot_root / "config.json").write_text("{}\n", encoding="utf-8")
    (snapshot_root / "tokenizer_config.json").write_text("{}\n", encoding="utf-8")
    (snapshot_root / "model.safetensors").write_bytes(b"weights")
    provenance = build_qwen_base_model_provenance(
        snapshot_root,
        manifest_path=external_manifest,
    )
    assert provenance.model_dump(mode="json") == provenance.portable_manifest()
    external_manifest.parent.mkdir()
    external_manifest.write_bytes(
        json.dumps(
            provenance.portable_manifest(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\n"
    )
    verified = verify_qwen_base_model_provenance(
        snapshot_root,
        external_manifest,
    )
    assert verified.snapshot_content_sha256 == provenance.snapshot_content_sha256
    request = build_qwen_base_model_acquisition_request(snapshot_root)
    assert request.snapshot_download_kwargs() == {
        "repo_id": PHASE40_QWEN_MODEL_ID,
        "revision": PHASE40_QWEN_REVISION,
        "local_dir": str(snapshot_root),
    }

    (snapshot_root / "model.safetensors").write_bytes(b"drifted-weights")
    with pytest.raises(RuntimeError, match="inventory or file hashes drifted"):
        verify_qwen_base_model_provenance(snapshot_root, external_manifest)
    (snapshot_root / "model.safetensors").write_bytes(b"weights")
    manifest_payload = json.loads(external_manifest.read_text(encoding="utf-8"))
    manifest_payload["model_revision"] = "0" * 40
    external_manifest.write_text(json.dumps(manifest_payload), encoding="utf-8")
    with pytest.raises(RuntimeError, match="identity/revision drifted"):
        verify_qwen_base_model_provenance(snapshot_root, external_manifest)


def test_pinned_qwen_load_passes_exact_revision_to_tokenizer_and_model(tmp_path):
    calls: dict[str, tuple[str, dict[str, object]]] = {}

    class TokenizerLoader:
        @staticmethod
        def from_pretrained(path, **kwargs):
            calls["tokenizer"] = (path, kwargs)
            return SimpleNamespace(pad_token=None, eos_token="<eos>", unk_token=None)

    class ModelLoader:
        @staticmethod
        def from_pretrained(path, **kwargs):
            calls["model"] = (path, kwargs)
            return SimpleNamespace()

    config = build_training_config(
        candidate_id="qwen3-4b-instruct-2507",
        train_split_path=tmp_path / "train.jsonl",
        val_split_path=tmp_path / "val.jsonl",
        version_tag="revision-load-fixture",
        output_root=tmp_path / "output",
        registry_path=tmp_path / "registry.json",
        selection=_selection(),
        adaptation_mode=AdaptationMode.LORA,
        run_kind=RunKind.PROBE,
        probe_post_warmup_steps=30,
    )
    transformers = SimpleNamespace(
        AutoTokenizer=TokenizerLoader,
        AutoModelForCausalLM=ModelLoader,
    )
    tokenizer, _ = _load_pinned_qwen_base_components(
        transformers_module=transformers,
        torch_module=SimpleNamespace(float32="float32"),
        config=config,
        base_model_path=tmp_path / "base-model",
        device="cpu",
        quantization_config=None,
    )
    assert tokenizer.pad_token == "<eos>"
    assert calls["tokenizer"][1]["revision"] == PHASE40_QWEN_REVISION
    assert calls["model"][1]["revision"] == PHASE40_QWEN_REVISION
    assert calls["tokenizer"][1]["local_files_only"] is True
    assert calls["model"][1]["local_files_only"] is True


@pytest.mark.parametrize(
    ("start_step", "include_completed_step", "expected_training_kind"),
    ((300, True, RunEventKind.STEP_TIMING), (312, False, RunEventKind.TRAIN_LOG)),
)
def test_full_finalization_closes_real_candidate_lifecycle_after_resume(
    tmp_path,
    start_step,
    include_completed_step,
    expected_training_kind,
):
    from src.model_adaptation.phase40_evidence import _validate_complete_full_lifecycle

    contract = _fixture_contract(tmp_path / "data", all_labels=True)
    event_path = tmp_path / "events.jsonl"
    begin = Phase40CallbackEvent(
        sequence_id=0,
        source_run_id="qwen-lora-finalize",
        run_kind=RunKind.FULL,
        event_kind=CallbackEventKind.TRAIN_BEGIN,
        timestamp_utc="2026-08-24T12:00:00Z",
        optimizer_step=start_step,
        epoch=2.5,
        duration_seconds=None,
        is_warmup=None,
        values=(),
    )
    _append_callback_run_event(event_path, begin)
    next_sequence = 1
    if include_completed_step:
        _append_callback_run_event(
            event_path,
            Phase40CallbackEvent(
                sequence_id=next_sequence,
                source_run_id="qwen-lora-finalize",
                run_kind=RunKind.FULL,
                event_kind=CallbackEventKind.OPTIMIZER_STEP,
                timestamp_utc="2026-08-24T12:00:01Z",
                optimizer_step=312,
                epoch=3.0,
                duration_seconds=1.0,
                is_warmup=False,
                values=(
                    ("examples", 4),
                    ("peak_allocated_bytes", 100),
                    ("peak_reserved_bytes", 200),
                    ("tokens", 20),
                ),
            ),
        )
        next_sequence += 1

    identity = "adapter-state-sha256:" + "c" * 64
    rows = tuple(
        Phase40PredictionRow.from_raw(
            validation_row_id=row.validation_row_id,
            sequence_index=index,
            gold_label=row.record.label,
            raw_prediction=json.dumps({"label": row.record.label}),
            artifact_identity=identity,
            checkpoint_step=312,
        )
        for index, row in enumerate(contract.validation_snapshot.rows)
    )
    metrics = evaluate_phase40_predictions(
        expected_validation_row_ids=contract.validation_snapshot.validation_row_ids,
        gold_labels=tuple(row.record.label for row in contract.validation_snapshot.rows),
        prediction_rows=rows,
    )
    artifact = tmp_path / "final-adapter"
    artifact.mkdir()
    (artifact / "adapter_config.json").write_text("{}\n", encoding="utf-8")
    (artifact / "adapter_model.bin").write_bytes(b"final-state")
    deferred_end = Phase40CallbackEvent(
        sequence_id=next_sequence,
        source_run_id="qwen-lora-finalize",
        run_kind=RunKind.FULL,
        event_kind=CallbackEventKind.TRAIN_END,
        timestamp_utc="2026-08-24T12:00:02Z",
        optimizer_step=312,
        epoch=3.0,
        duration_seconds=2.0,
        is_warmup=None,
        values=(("peak_allocated_bytes", 100), ("peak_reserved_bytes", 200)),
    )
    _append_full_run_finalization_events(
        event_path,
        run_id="qwen-lora-finalize",
        final_step=312,
        final_epoch=3.0,
        artifact_identity=identity,
        artifact_path=artifact,
        metrics=metrics,
        deferred_train_end=deferred_end,
    )
    events = load_run_events(event_path, expected_run_id="qwen-lora-finalize")
    _validate_complete_full_lifecycle(events)
    assert expected_training_kind in {event.event_kind for event in events}
    assert events[-3].event_kind == RunEventKind.EVALUATION
    assert events[-3].trainer_values["artifact_identity"] == identity
    assert events[-2].event_kind == RunEventKind.CHECKPOINT
    assert events[-2].trainer_values["artifact_identity"] == identity
    assert events[-1].event_kind == RunEventKind.RUN_END


def test_failed_suffix_resources_survive_checkpoint_resume_and_reject_tamper(tmp_path):
    _, _, _, base_state = _resume_history_fixture(tmp_path)
    event_path = tmp_path / "events.jsonl"
    _checkpoint_event_log(event_path)
    checkpoint_event_count = len(load_run_events(event_path))

    def append_same_attempt_suffix(event):
        if event.event_kind == CallbackEventKind.TRAIN_BEGIN:
            return
        _append_callback_run_event(
            event_path,
            replace(event, sequence_id=event.sequence_id - 1),
            sequence_offset=checkpoint_event_count,
        )

    clock = FakeClock()
    state = SimpleNamespace(global_step=10, epoch=1.0, num_input_tokens_seen=100)
    failed = Phase40EvidenceCallback(
        run_id="qwen-lora-history",
        run_kind=RunKind.FULL,
        warmup_optimizer_steps=0,
        examples_per_optimizer_step=1,
        planned_full_optimizer_steps=10,
        resume_state=base_state,
        event_sink=append_same_attempt_suffix,
        clock=clock,
        utc_clock=lambda: FIXED_UTC,
        cuda=FakeCuda(allocated=300, reserved=400),
    )
    failed.on_train_begin(None, state, None)
    failed.on_step_begin(None, state, None)
    clock.advance(2.0)
    state.global_step = 11
    state.num_input_tokens_seen = 110
    failed.on_step_end(None, state, None)
    failed.on_evaluate(None, state, None, metrics={"eval_runtime": 1.5})
    clock.advance(1.5)
    clock.advance(0.5)
    failure_state = failed.failure_state()
    _append_runtime_failure_event(
        event_path,
        run_id="qwen-lora-history",
        run_kind=RunKind.FULL,
        requested_mode=AdaptationMode.LORA,
        error=RuntimeError("fixture interruption"),
        resource_state=failure_state,
    )

    merged = _resume_state_with_failed_suffix(
        base_state,
        event_path=event_path,
        checkpoint_event_count=checkpoint_event_count,
    )
    assert merged["observed_optimizer_steps"] == 11
    assert merged["retained_step_seconds"][-1] == 2.0
    assert merged["retained_examples"] == 11
    assert merged["retained_tokens"] == 110
    assert merged["evaluation_overhead_seconds"][-1] == 1.5
    assert merged["peak_allocated_bytes"] == 300
    assert merged["peak_reserved_bytes"] == 400
    assert merged["actual_wall_seconds"] == 19.0

    final_clock = FakeClock()
    final_state = SimpleNamespace(global_step=10, epoch=1.0, num_input_tokens_seen=100)
    resumed = Phase40EvidenceCallback(
        run_id="qwen-lora-history",
        run_kind=RunKind.FULL,
        warmup_optimizer_steps=0,
        examples_per_optimizer_step=1,
        planned_full_optimizer_steps=10,
        resume_state=merged,
        clock=final_clock,
        utc_clock=lambda: FIXED_UTC,
        cuda=FakeCuda(allocated=250, reserved=350),
    )
    resumed.on_train_begin(None, final_state, None)
    final_clock.advance(1.0)
    resumed.on_train_end(None, final_state, None)
    summary = resumed.summary()
    assert summary.observed_optimizer_steps == 11
    assert summary.actual_wall_seconds == 20.0
    assert summary.peak_allocated_bytes == 300

    events = list(load_run_events(event_path))
    failure = events[-1]
    tampered_values = dict(failure.trainer_values)
    tampered_state = dict(tampered_values["resource_state"])
    tampered_state["retained_tokens"] += 1
    tampered_values["resource_state"] = tampered_state
    events[-1] = failure.model_copy(update={"trainer_values": tampered_values})
    tampered_path = tmp_path / "events-tampered.jsonl"
    tampered_path.write_text(
        "".join(event.model_dump_json() + "\n" for event in events),
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="resource state SHA-256 drifted"):
        _resume_state_with_failed_suffix(
            base_state,
            event_path=tampered_path,
            checkpoint_event_count=checkpoint_event_count,
        )

    foreign = list(load_run_events(event_path))
    foreign[-1] = foreign[-1].model_copy(update={"source_run_id": "foreign-run"})
    foreign_path = tmp_path / "events-foreign.jsonl"
    foreign_path.write_text(
        "".join(event.model_dump_json() + "\n" for event in foreign),
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="mixes source run IDs"):
        _resume_state_with_failed_suffix(
            base_state,
            event_path=foreign_path,
            checkpoint_event_count=checkpoint_event_count,
        )


def test_final_evaluation_failure_after_sealed_checkpoint_is_terminal_and_resumable(
    tmp_path,
    monkeypatch,
):
    from src.model_adaptation.phase40_evidence import _validate_complete_full_lifecycle

    contract, recorder, identity_by_name, checkpoint_state = _resume_history_fixture(tmp_path)
    snapshot = _sealed_qwen_snapshot(tmp_path / "base-model")
    event_path = tmp_path / "events.jsonl"
    _checkpoint_event_log(event_path)
    checkpoint_event_count = len(load_run_events(event_path))
    checkpoint = tmp_path / "trainer" / "checkpoint-10"
    checkpoint.mkdir(parents=True)
    (checkpoint / "adapter_model.bin").write_bytes(b"checkpoint-state")
    (checkpoint / "trainer_state.json").write_text(
        json.dumps({"global_step": 10}),
        encoding="utf-8",
    )
    controlled = _resume_config()
    history = recorder.resume_history_payload(checkpoint_state)
    _write_checkpoint_resume_manifest(
        checkpoint,
        checkpoint_step=10,
        controlled_config=controlled,
        resume_history=history,
        event_path=event_path,
        base_model_snapshot=snapshot,
    )

    clock = FakeClock()
    callback_state = SimpleNamespace(global_step=10, epoch=1.0, num_input_tokens_seen=100)
    completed = Phase40EvidenceCallback(
        run_id="qwen-lora-history",
        run_kind=RunKind.FULL,
        warmup_optimizer_steps=0,
        examples_per_optimizer_step=1,
        planned_full_optimizer_steps=10,
        resume_state=checkpoint_state,
        clock=clock,
        utc_clock=lambda: FIXED_UTC,
        cuda=FakeCuda(allocated=250, reserved=350),
    )
    completed.on_train_begin(None, callback_state, None)
    clock.advance(0.25)
    completed.on_train_end(None, callback_state, None)
    completed_state = completed.completed_state()

    def fail_final_evaluation(**_kwargs):
        raise RuntimeError("injected final record_final_if_needed failure")

    monkeypatch.setattr(recorder, "record_final_if_needed", fail_final_evaluation)

    class Saveable:
        def __init__(self, filename: str) -> None:
            self.filename = filename

        def save_pretrained(self, path: str) -> None:
            target = Path(path)
            target.mkdir(parents=True, exist_ok=True)
            (target / self.filename).write_bytes(b"fixture")

    finalizer = lambda: _complete_full_qwen_training(
        runtime_config=SimpleNamespace(
            output_root=tmp_path / "models",
            version_tag="post-train-failure",
            candidate_id="qwen3-4b-instruct-2507",
            run_kind=RunKind.FULL,
        ),
        validation_recorder=recorder,
        controlled_config=controlled,
        deferred_train_end=completed.events[-1],
        model=Saveable("adapter_model.bin"),
        tokenizer=Saveable("tokenizer_config.json"),
        trainer=SimpleNamespace(state=callback_state),
        event_path=event_path,
        evidence_root=tmp_path / "evidence",
        training_output_dir=tmp_path / "trainer",
        base_model_snapshot=snapshot,
        base_model_path=tmp_path / "base-model",
        device="cuda",
        resource_summary=completed.summary(),
        quantization_proof=_lora_quantization_proof(),
        data_contract=contract,
        train_result=SimpleNamespace(metrics={}),
        train_examples=(),
        val_examples=(),
        train_dataset=None,
        resume_checkpoint=checkpoint,
        torch_module=None,
        transformers_module=None,
        peft_module=None,
    )
    with pytest.raises(RuntimeError, match="injected final record_final_if_needed failure"):
        _run_post_train_finalization_transaction(
            finalizer,
            event_path=event_path,
            run_id="qwen-lora-history",
            requested_mode=AdaptationMode.LORA,
            resource_state=completed_state,
        )

    failed_events = load_run_events(event_path, expected_run_id="qwen-lora-history")
    assert [event.event_kind for event in failed_events[-2:]] == [
        RunEventKind.RESOURCE,
        RunEventKind.FAILURE,
    ]
    assert failed_events[-2].trainer_values["resource_state"] == completed_state
    assert failed_events[-1].trainer_values["resource_state"] == completed_state
    manifest = _read_checkpoint_resume_manifest(
        checkpoint,
        controlled_config=controlled,
        event_path=event_path,
        base_model_snapshot=snapshot,
        require_cumulative_history=True,
    )
    merged_state = _resume_state_with_failed_suffix(
        checkpoint_state,
        event_path=event_path,
        checkpoint_event_count=manifest["run_event_count"],
    )
    assert merged_state == completed_state

    tampered_events = list(failed_events)
    resource = tampered_events[-2]
    resource_values = dict(resource.trainer_values)
    tampered_resource_state = dict(resource_values["resource_state"])
    tampered_resource_state["actual_wall_seconds"] += 1.0
    resource_values["resource_state"] = tampered_resource_state
    tampered_events[-2] = resource.model_copy(update={"trainer_values": resource_values})
    tampered_path = tmp_path / "events-post-train-tampered.jsonl"
    tampered_path.write_text(
        "".join(event.model_dump_json() + "\n" for event in tampered_events),
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="post-train resource state SHA-256 drifted"):
        _resume_state_with_failed_suffix(
            checkpoint_state,
            event_path=tampered_path,
            checkpoint_event_count=checkpoint_event_count,
        )

    restored = Phase40ValidationRecorder(
        tokenizer=None,
        candidate=None,
        validation_snapshot=contract.validation_snapshot,
        training_output_dir=tmp_path / "trainer",
        prediction_output_dir=tmp_path / "predictions-restored",
        retained_artifact_root=tmp_path / "retained",
        artifact_identity_prover=lambda _model, _path: "unused",
        stored_artifact_identity_loader=lambda path: identity_by_name[path.name],
    )
    assert restored.restore_resume_history(history) == checkpoint_state
    _append_callback_run_event(
        event_path,
        Phase40CallbackEvent(
            sequence_id=0,
            source_run_id="qwen-lora-history",
            run_kind=RunKind.FULL,
            event_kind=CallbackEventKind.TRAIN_BEGIN,
            timestamp_utc="2026-08-24T12:00:03Z",
            optimizer_step=10,
            epoch=1.0,
            duration_seconds=None,
            is_warmup=None,
            values=(),
        ),
        sequence_offset=len(failed_events),
    )
    final_key = next(key for key in restored.metrics_by_candidate if key[0] == 10)
    final_metrics = restored.metrics_by_candidate[final_key]
    final_artifact = restored.retained_paths[final_key]
    _append_full_run_finalization_events(
        event_path,
        run_id="qwen-lora-history",
        final_step=10,
        final_epoch=1.0,
        artifact_identity=final_key[1],
        artifact_path=final_artifact,
        metrics=final_metrics,
        deferred_train_end=Phase40CallbackEvent(
            sequence_id=1,
            source_run_id="qwen-lora-history",
            run_kind=RunKind.FULL,
            event_kind=CallbackEventKind.TRAIN_END,
            timestamp_utc="2026-08-24T12:00:04Z",
            optimizer_step=10,
            epoch=1.0,
            duration_seconds=0.1,
            is_warmup=None,
            values=(("peak_allocated_bytes", 250), ("peak_reserved_bytes", 350)),
        ),
    )
    completed_events = load_run_events(event_path, expected_run_id="qwen-lora-history")
    _validate_complete_full_lifecycle(completed_events)
    assert completed_events[-1].event_kind == RunEventKind.RUN_END


def test_staged_materialization_failure_precedes_run_end_and_exact_resume_commits(
    tmp_path,
    monkeypatch,
):
    import src.model_adaptation.training as training_module
    from src.model_adaptation.phase40_evidence import _validate_complete_full_lifecycle

    contract, recorder, _, checkpoint_state = _resume_history_fixture(tmp_path)
    snapshot = _sealed_qwen_snapshot(tmp_path / "base-model")
    run_root = tmp_path / "returned" / "qwen-lora-history"
    config = build_training_config(
        candidate_id="qwen3-4b-instruct-2507",
        train_split_path=tmp_path / "train.jsonl",
        val_split_path=tmp_path / "val.jsonl",
        version_tag="materialization-edge",
        output_root=tmp_path / "models",
        registry_path=tmp_path / "registry.json",
        selection=_selection(),
        adaptation_mode=AdaptationMode.LORA,
        run_kind=RunKind.FULL,
        run_id="qwen-lora-history",
        transfer_authority=_transfer_authority(),
        requested_control_template=_requested_template(_resume_config()),
        sanitized_argv=("phase40-train", "--run-id=qwen-lora-history"),
        run_bundle_root=run_root,
    )
    event_path = run_root / "events.jsonl"
    _checkpoint_event_log(event_path)
    checkpoint_event_count = len(load_run_events(event_path))
    checkpoint = tmp_path / "trainer" / "checkpoint-10"
    checkpoint.mkdir(parents=True)
    (checkpoint / "adapter_model.bin").write_bytes(b"checkpoint-state")
    (checkpoint / "trainer_state.json").write_text(
        json.dumps({"global_step": 10}),
        encoding="utf-8",
    )
    controlled = _resume_config()
    history = recorder.resume_history_payload(checkpoint_state)
    _write_checkpoint_resume_manifest(
        checkpoint,
        checkpoint_step=10,
        controlled_config=controlled,
        resume_history=history,
        event_path=event_path,
        base_model_snapshot=snapshot,
    )
    final_key = next(key for key in recorder.metrics_by_candidate if key[0] == 10)
    final_metrics = recorder.metrics_by_candidate[final_key]
    final_artifact = recorder.retained_paths[final_key]
    selection = select_phase40_checkpoint(tuple(recorder.metrics_by_candidate.values()))

    clock = FakeClock()
    trainer_state = SimpleNamespace(global_step=10, epoch=1.0, num_input_tokens_seen=100)
    completed = Phase40EvidenceCallback(
        run_id="qwen-lora-history",
        run_kind=RunKind.FULL,
        warmup_optimizer_steps=0,
        examples_per_optimizer_step=1,
        planned_full_optimizer_steps=10,
        resume_state=checkpoint_state,
        clock=clock,
        utc_clock=lambda: FIXED_UTC,
        cuda=FakeCuda(allocated=250, reserved=350),
    )
    completed.on_train_begin(None, trainer_state, None)
    clock.advance(0.25)
    completed.on_train_end(None, trainer_state, None)

    def materialize(*_args, **_kwargs):
        return _materialize_and_commit_full_run_evidence(
            config,
            final_step=10,
            final_epoch=1.0,
            final_artifact_identity=final_key[1],
            final_artifact_path=final_artifact,
            final_metrics=final_metrics,
            deferred_train_end=completed.events[-1],
            data_contract=contract,
            controlled_config=controlled,
            quantization_proof=_lora_quantization_proof(),
            checkpoint_selection=selection,
            validation_recorder=recorder,
            adapter_output_dir=final_artifact,
            training_output_dir=tmp_path / "trainer",
            event_path=event_path,
            resource_summary=SimpleNamespace(),
            torch_module=None,
            transformers_module=None,
            peft_module=None,
            base_model_snapshot=snapshot,
        )

    def fail_staged_materializer(*_args, event_path, **_kwargs):
        projected = load_run_events(event_path, expected_run_id="qwen-lora-history")
        assert projected[-1].event_kind == RunEventKind.RUN_END
        canonical = load_run_events(
            run_root / "events.jsonl",
            expected_run_id="qwen-lora-history",
        )
        assert canonical[-1].event_kind == RunEventKind.CHECKPOINT
        raise RuntimeError("injected staged evidence materialization failure")

    monkeypatch.setattr(
        training_module,
        "_materialize_full_run_evidence",
        fail_staged_materializer,
    )
    with pytest.raises(RuntimeError, match="injected staged evidence materialization failure"):
        _run_post_train_finalization_transaction(
            materialize,
            event_path=event_path,
            run_id="qwen-lora-history",
            requested_mode=AdaptationMode.LORA,
            resource_state=completed.completed_state,
            failure_resource_state_provider=completed.failure_state,
        )

    failed_events = load_run_events(event_path, expected_run_id="qwen-lora-history")
    assert [event.event_kind for event in failed_events[-2:]] == [
        RunEventKind.RESOURCE,
        RunEventKind.FAILURE,
    ]
    assert not any(event.event_kind == RunEventKind.RUN_END for event in failed_events)
    assert tuple(path.name for path in run_root.iterdir()) == ("events.jsonl",)
    manifest = _read_checkpoint_resume_manifest(
        checkpoint,
        controlled_config=controlled,
        event_path=event_path,
        base_model_snapshot=snapshot,
        require_cumulative_history=True,
    )
    merged = _resume_state_with_failed_suffix(
        checkpoint_state,
        event_path=event_path,
        checkpoint_event_count=manifest["run_event_count"],
    )
    assert merged == completed.completed_state()

    _append_callback_run_event(
        event_path,
        Phase40CallbackEvent(
            sequence_id=0,
            source_run_id="qwen-lora-history",
            run_kind=RunKind.FULL,
            event_kind=CallbackEventKind.TRAIN_BEGIN,
            timestamp_utc="2026-08-24T12:00:03Z",
            optimizer_step=10,
            epoch=1.0,
            duration_seconds=None,
            is_warmup=None,
            values=(),
        ),
        sequence_offset=len(failed_events),
    )
    resume_clock = FakeClock()
    resumed = Phase40EvidenceCallback(
        run_id="qwen-lora-history",
        run_kind=RunKind.FULL,
        warmup_optimizer_steps=0,
        examples_per_optimizer_step=1,
        planned_full_optimizer_steps=10,
        resume_state=merged,
        clock=resume_clock,
        utc_clock=lambda: FIXED_UTC,
        cuda=FakeCuda(allocated=240, reserved=340),
    )
    resumed.on_train_begin(None, trainer_state, None)
    resume_clock.advance(0.1)
    resumed.on_train_end(None, trainer_state, None)

    verified = SimpleNamespace(status="complete")

    def successful_staged_materializer(*_args, event_path, run_root_override, **_kwargs):
        projected = load_run_events(event_path, expected_run_id="qwen-lora-history")
        _validate_complete_full_lifecycle(projected)
        evidence_path = Path(run_root_override) / "run-evidence.json"
        evidence_path.write_text('{"status":"complete"}\n', encoding="utf-8")
        return evidence_path, verified

    monkeypatch.setattr(
        training_module,
        "_materialize_full_run_evidence",
        successful_staged_materializer,
    )
    completed_path, completed_evidence = _run_post_train_finalization_transaction(
        lambda: _materialize_and_commit_full_run_evidence(
            config,
            final_step=10,
            final_epoch=1.0,
            final_artifact_identity=final_key[1],
            final_artifact_path=final_artifact,
            final_metrics=final_metrics,
            deferred_train_end=resumed.events[-1],
            data_contract=contract,
            controlled_config=controlled,
            quantization_proof=_lora_quantization_proof(),
            checkpoint_selection=selection,
            validation_recorder=recorder,
            adapter_output_dir=final_artifact,
            training_output_dir=tmp_path / "trainer",
            event_path=event_path,
            resource_summary=SimpleNamespace(),
            torch_module=None,
            transformers_module=None,
            peft_module=None,
            base_model_snapshot=snapshot,
        ),
        event_path=event_path,
        run_id="qwen-lora-history",
        requested_mode=AdaptationMode.LORA,
        resource_state=resumed.completed_state,
        failure_resource_state_provider=resumed.failure_state,
    )
    assert completed_path == run_root / "run-evidence.json"
    assert completed_evidence is verified
    final_events = load_run_events(event_path, expected_run_id="qwen-lora-history")
    _validate_complete_full_lifecycle(final_events)
    assert final_events[-1].event_kind == RunEventKind.RUN_END


def test_missing_train_end_state_is_terminal_and_uses_active_resource_fallback(tmp_path):
    _, _, _, checkpoint_state = _resume_history_fixture(tmp_path)
    event_path = tmp_path / "events.jsonl"
    _checkpoint_event_log(event_path)
    checkpoint_event_count = len(load_run_events(event_path))
    clock = FakeClock()
    state = SimpleNamespace(global_step=10, epoch=1.0, num_input_tokens_seen=100)
    callback = Phase40EvidenceCallback(
        run_id="qwen-lora-history",
        run_kind=RunKind.FULL,
        warmup_optimizer_steps=0,
        examples_per_optimizer_step=1,
        planned_full_optimizer_steps=10,
        resume_state=checkpoint_state,
        clock=clock,
        utc_clock=lambda: FIXED_UTC,
        cuda=FakeCuda(allocated=250, reserved=350),
    )
    callback.on_train_begin(None, state, None)
    clock.advance(0.5)
    finalizer = Mock(side_effect=AssertionError("finalization ran without train_end"))

    with pytest.raises(RuntimeError, match="completed callback state"):
        _run_post_train_finalization_transaction(
            finalizer,
            event_path=event_path,
            run_id="qwen-lora-history",
            requested_mode=AdaptationMode.LORA,
            resource_state=callback.completed_state,
            failure_resource_state_provider=callback.failure_state,
        )

    finalizer.assert_not_called()
    events = load_run_events(event_path, expected_run_id="qwen-lora-history")
    assert events[-1].event_kind == RunEventKind.FAILURE
    assert events[-1].trainer_values["resource_state"] is not None
    merged = _resume_state_with_failed_suffix(
        checkpoint_state,
        event_path=event_path,
        checkpoint_event_count=checkpoint_event_count,
    )
    assert merged["actual_wall_seconds"] == 15.5


def test_qwen_acquisition_rejects_symlinked_destination_ancestor(tmp_path):
    real_parent = tmp_path / "real-parent"
    real_parent.mkdir()
    linked_parent = tmp_path / "linked-parent"
    try:
        linked_parent.symlink_to(real_parent, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"filesystem cannot create directory symlinks: {exc}")
    with pytest.raises(ValueError, match="must not traverse symlinks"):
        build_qwen_base_model_acquisition_request(linked_parent / "future-snapshot")


def test_probe_run_path_accepts_only_verified_discarded_result(tmp_path, monkeypatch):
    import src.model_adaptation.training as training_module

    contract = _fixture_contract(tmp_path)
    config = build_training_config(
        candidate_id="qwen3-4b-instruct-2507",
        train_split_path=tmp_path / "train.jsonl",
        val_split_path=tmp_path / "val.jsonl",
        version_tag="phase40-probe-fixture",
        output_root=tmp_path / "models",
        registry_path=tmp_path / "registry.json",
        selection=_selection(),
        adaptation_mode=AdaptationMode.LORA,
        run_kind=RunKind.PROBE,
        run_id="probe-fixture",
        probe_post_warmup_steps=30,
    )
    publisher = Mock(side_effect=AssertionError("probe reached registry publication"))
    monkeypatch.setattr(training_module, "save_adapter_artifacts", publisher)

    def fake_probe_backend(*_args):
        probe_root = _probe_root(config)
        trainer_root = probe_root / "trainer"
        trainer_root.mkdir(parents=True)
        (trainer_root / "checkpoint.bin").write_bytes(b"disposable")
        receipt = discard_probe_artifact(
            run_id="probe-fixture",
            probe_root=probe_root,
            discarded_path_identity="trainer",
        )
        event_path = tmp_path / "probe-evidence" / "events.jsonl"
        for sequence_id, (kind, step) in enumerate(
            ((CallbackEventKind.TRAIN_BEGIN, 0), (CallbackEventKind.TRAIN_END, 35))
        ):
            _append_callback_run_event(
                event_path,
                Phase40CallbackEvent(
                    sequence_id=sequence_id,
                    source_run_id="probe-fixture",
                    run_kind=RunKind.PROBE,
                    event_kind=kind,
                    timestamp_utc="2026-08-24T12:00:00Z",
                    optimizer_step=step,
                    epoch=float(step),
                    duration_seconds=80.0 if kind == CallbackEventKind.TRAIN_END else None,
                    is_warmup=None,
                    values=(),
                ),
            )
        return {
            "artifact_path": None,
            "quantization_proof": _lora_quantization_proof(),
            "probe_contract": ProbeExecutionContract(
                run_id="probe-fixture",
                requested_identity=config.experiment_identity,
                target_post_warmup_steps=30,
                warmup_optimizer_steps=5,
            ),
            "resource_summary": _completed_probe_summary("probe-fixture"),
            "discard_receipt": receipt,
            "resume_from_checkpoint": None,
            "events_path": event_path,
        }

    monkeypatch.setattr(training_module, "_run_local_adapter_training", fake_probe_backend)
    result = run_training(config, data_contract=contract, selection=_selection())
    assert result["run_kind"] == RunKind.PROBE
    assert result["artifact_record"] is None
    assert not (_probe_root(config) / "trainer").exists()
    assert not config.registry_path.exists()
    publisher.assert_not_called()


def test_probe_invalid_cap_is_rejected_before_backend(tmp_path, monkeypatch):
    import src.model_adaptation.training as training_module

    contract = _fixture_contract(tmp_path)
    config = build_training_config(
        candidate_id="qwen3-4b-instruct-2507",
        train_split_path=tmp_path / "train.jsonl",
        val_split_path=tmp_path / "val.jsonl",
        version_tag="phase40-invalid-probe",
        output_root=tmp_path / "models",
        registry_path=tmp_path / "registry.json",
        selection=_selection(),
        adaptation_mode=AdaptationMode.LORA,
        run_kind=RunKind.PROBE,
        probe_post_warmup_steps=29,
    )
    backend = Mock(side_effect=AssertionError("invalid probe reached backend"))
    monkeypatch.setattr(training_module, "_run_local_adapter_training", backend)
    with pytest.raises(ValueError, match="inclusive 30-50"):
        run_training(config, data_contract=contract, selection=_selection())
    backend.assert_not_called()


def test_probe_rejects_request_bound_full_bundle_root(tmp_path):
    with pytest.raises(ValueError, match="reserved for immutable full-run evidence"):
        build_training_config(
            candidate_id="qwen3-4b-instruct-2507",
            train_split_path=tmp_path / "train.jsonl",
            val_split_path=tmp_path / "val.jsonl",
            version_tag="phase40-probe-bundle-rejection",
            output_root=tmp_path / "models",
            registry_path=tmp_path / "registry.json",
            selection=_selection(),
            adaptation_mode=AdaptationMode.LORA,
            run_kind=RunKind.PROBE,
            probe_post_warmup_steps=30,
            run_bundle_root=tmp_path / "returned" / "probe",
        )


def test_full_requires_request_authority_and_bundle_before_backend(tmp_path, monkeypatch):
    import src.model_adaptation.training as training_module

    contract = _fixture_contract(tmp_path)
    common = {
        "candidate_id": "qwen3-4b-instruct-2507",
        "train_split_path": tmp_path / "train.jsonl",
        "val_split_path": tmp_path / "val.jsonl",
        "version_tag": "phase40-full-preflight",
        "output_root": tmp_path / "models",
        "registry_path": tmp_path / "registry.json",
        "selection": _selection(),
        "adaptation_mode": AdaptationMode.LORA,
        "run_kind": RunKind.FULL,
        "run_id": "qwen-lora-preflight",
        "transfer_authority": _transfer_authority(),
        "sanitized_argv": ("phase40-train", "--run-id=qwen-lora-preflight"),
    }
    backend = Mock(side_effect=AssertionError("invalid full run reached backend"))
    monkeypatch.setattr(training_module, "_run_local_adapter_training", backend)

    without_template = build_training_config(
        **common,
        run_bundle_root=tmp_path / "returned" / "qwen-lora",
    )
    with pytest.raises(RuntimeError, match="requested_control_template"):
        run_training(without_template, data_contract=contract, selection=_selection())

    without_root = build_training_config(
        **common,
        requested_control_template=_requested_template(_resume_config()),
    )
    with pytest.raises(RuntimeError, match="request-bound run_bundle_root"):
        run_training(without_root, data_contract=contract, selection=_selection())
    backend.assert_not_called()


def test_full_bundle_root_is_empty_for_fresh_run_and_controls_are_frozen(tmp_path):
    controlled = _resume_config()
    config = build_training_config(
        candidate_id="qwen3-4b-instruct-2507",
        train_split_path=tmp_path / "train.jsonl",
        val_split_path=tmp_path / "val.jsonl",
        version_tag="phase40-full-root-fixture",
        output_root=tmp_path / "models",
        registry_path=tmp_path / "registry.json",
        selection=_selection(),
        adaptation_mode=AdaptationMode.LORA,
        run_kind=RunKind.FULL,
        run_id="qwen-lora-root-fixture",
        transfer_authority=_transfer_authority(),
        requested_control_template=_requested_template(controlled),
        sanitized_argv=("phase40-train", "--run-id=qwen-lora-root-fixture"),
        run_bundle_root=tmp_path / "returned" / "qwen-lora",
    )
    _verify_requested_runtime_controls(config, controlled)
    with pytest.raises(RuntimeError, match="differs from the frozen"):
        _verify_requested_runtime_controls(config, _resume_config(seed=43))

    root = _prepare_full_run_bundle_root(config, create=True)
    assert root == config.run_bundle_root
    (root / "unexpected.txt").write_text("not an immutable bundle", encoding="utf-8")
    with pytest.raises(FileExistsError, match="requires an empty"):
        _prepare_full_run_bundle_root(config, create=False)


def test_request_constructor_derives_qwen_controls_and_paths(tmp_path):
    contract = _fixture_contract(tmp_path, all_labels=True)
    controlled = _resume_config().model_copy(
        update={
            "model_id": "Qwen/Qwen3-4B-Instruct-2507",
            "splits": tuple(
                CanonicalSplitEvidence(
                    logical_name=name,
                    relative_path=snapshot.identity.relative_path,
                    records=snapshot.identity.records,
                    bytes=snapshot.identity.bytes,
                    sha256=snapshot.whole_file_sha256,
                    ordered_row_ids_sha256=hashlib.sha256(
                        b"phase40-ordered-row-ids-v1\0"
                        + b"".join(
                            row_id.encode("ascii") + b"\n" for row_id in snapshot.row_ids
                        )
                    ).hexdigest(),
                )
                for name, snapshot in (
                    ("train", contract.train_snapshot),
                    ("val", contract.validation_snapshot),
                )
            ),
            "additional_controls": tuple(
                sorted(
                    (
                        NamedControl(name="input_archive_sha256", value="c" * 64),
                        NamedControl(name="input_manifest_sha256", value="d" * 64),
                        NamedControl(name="local_files_only", value=True),
                        NamedControl(name="report_to", value="none"),
                        NamedControl(name="save_safetensors", value=True),
                        NamedControl(name="source_archive_sha256", value="a" * 64),
                        NamedControl(name="source_inventory_sha256", value="b" * 64),
                        NamedControl(name="trust_remote_code", value=True),
                    ),
                    key=lambda item: item.name,
                )
            ),
        }
    )
    template = _requested_template(controlled)
    requested_run = FullRunRequestIdentity(
        run_id="qwen-lora",
        model_family=ModelFamily.QWEN,
        adaptation_mode=AdaptationMode.LORA,
        returned_root="data/models/phase40/full/qwen-lora",
    )
    input_bundle = SimpleNamespace(
        repository_relative_path=(
            "data/models/phase40/input/phase40-train-validation.zip"
        ),
        archive_sha256="c" * 64,
        manifest_sha256="d" * 64,
        drive_path=(
            "/content/drive/MyDrive/internship-phase40/phase40-train-validation.zip"
        ),
        extraction_root="/content/phase40-input-v1",
        members=("phase40-input-manifest.json", "train.jsonl", "val.jsonl"),
    )
    source_bundle = SimpleNamespace(
        repository_relative_archive_path=(
            "data/models/phase40/source/phase40-source.zip"
        ),
        archive_sha256="a" * 64,
        repository_relative_inventory_path=(
            "data/models/phase40/source/phase40-source-manifest.json"
        ),
        inventory_sha256="b" * 64,
    )
    request = RunRequest.model_construct(
        runs=(requested_run,),
        source_bundle=source_bundle,
        input_bundle=input_bundle,
        control_template_by_run={"qwen-lora": template},
        control_template_digest_by_run={"qwen-lora": template.sha256},
        no_held_out_boundary=True,
    )
    config = build_phase40_qwen_training_config(
        run_request=request,
        run_id="qwen-lora",
        data_contract=contract,
        repo_root=tmp_path,
        work_root=tmp_path / "work",
        base_model_path=tmp_path / "base-model",
        sanitized_argv=("phase40-train", "--run-id=qwen-lora"),
    )
    assert config.run_bundle_root == tmp_path / requested_run.returned_root
    assert config.candidate_id == "qwen3-4b-instruct-2507"
    assert config.model_id == "Qwen/Qwen3-4B-Instruct-2507"
    assert config.requested_control_template == template
    assert config.learning_rate == controlled.optimizer.learning_rate
    assert config.max_steps == controlled.max_optimizer_steps
    assert config.save_steps == controlled.cadence.save_steps
    assert config.registry_path == tmp_path / "work" / "unused-model-registry.json"


def test_registry_free_comparison_retains_failed_safety_evidence(tmp_path, monkeypatch):
    import src.model_adaptation.training as training_module

    torch = pytest.importorskip("torch")
    contract = _fixture_contract(tmp_path, all_labels=True)
    snapshot = _sealed_qwen_snapshot(tmp_path / "base-model")
    config = build_training_config(
        candidate_id="qwen3-4b-instruct-2507",
        train_split_path=tmp_path / "train.jsonl",
        val_split_path=tmp_path / "val.jsonl",
        version_tag="phase40-comparison-fixture",
        output_root=tmp_path / "work",
        registry_path=tmp_path / "must-not-exist-registry.json",
        selection=_selection(),
        adaptation_mode=AdaptationMode.LORA,
        run_kind=RunKind.FULL,
        run_id="qwen-lora-failed-safety",
        transfer_authority=_transfer_authority(),
        requested_control_template=_requested_template(_resume_config()),
        sanitized_argv=("phase40-train", "--run-id=qwen-lora-failed-safety"),
        run_bundle_root=tmp_path / "returned" / "qwen-lora",
    )
    config = replace(
        config,
        model_id=PHASE40_QWEN_MODEL_ID,
        base_model_path=snapshot.local_snapshot_path,
    )
    adapter = training_module._adapter_output_dir(config)
    adapter.mkdir(parents=True)
    (adapter / "adapter_config.json").write_text("{}", encoding="utf-8")
    adapter_state = {"adapter.lora_A.weight": torch.tensor([[1.0, 2.0]])}
    torch.save(adapter_state, adapter / "adapter_model.bin")
    (adapter / PHASE40_BASE_MODEL_MANIFEST_NAME).write_bytes(
        training_module._canonical_json_line(snapshot.portable_manifest())
    )
    artifact_identity = training_module._adapter_state_identity(
        adapter_state,
        torch_module=torch,
    )
    rows = tuple(
        Phase40PredictionRow.from_raw(
            validation_row_id=row.validation_row_id,
            sequence_index=index,
            gold_label=row.record.label,
            raw_prediction=json.dumps({"label": "benign"}),
            artifact_identity=artifact_identity,
            checkpoint_step=10,
        )
        for index, row in enumerate(contract.validation_snapshot.rows)
    )
    metrics = evaluate_phase40_predictions(
        expected_validation_row_ids=contract.validation_snapshot.validation_row_ids,
        gold_labels=tuple(row.record.label for row in contract.validation_snapshot.rows),
        prediction_rows=rows,
    )
    checkpoint_selection = select_phase40_checkpoint((metrics,))
    assert checkpoint_selection.safety_gate_passed is False
    trainer_result = {
        "artifact_path": adapter,
        "quantization_proof": _lora_quantization_proof(),
        "checkpoint_selection": checkpoint_selection,
        "checkpoint_candidates": (metrics,),
        "selected_artifact_identity": artifact_identity,
        "formatter_sha256": "2" * 64,
        "formatter_version": training_module.PHASE40_FORMATTER_VERSION,
        "response_mask_version": training_module.PHASE40_RESPONSE_MASK_VERSION,
        "canonical_train_sha256": contract.train_snapshot.whole_file_sha256,
        "canonical_val_sha256": contract.validation_snapshot.whole_file_sha256,
        "canonical_train_row_ids_sha256": training_module._snapshot_row_id_digest(
            contract.train_snapshot
        ),
        "canonical_val_row_ids_sha256": training_module._snapshot_row_id_digest(
            contract.validation_snapshot
        ),
        "base_model_source": snapshot.evidence_payload(),
    }
    publisher = Mock(side_effect=AssertionError("comparison run mutated legacy registry"))
    evidence = SimpleNamespace(status="complete")
    evidence_verifier = Mock(return_value=evidence)
    monkeypatch.setattr(training_module, "save_adapter_artifacts", publisher)
    monkeypatch.setattr(training_module, "_authorize_phase40_qwen_request", Mock())
    monkeypatch.setattr(
        training_module,
        "_run_local_adapter_training",
        Mock(return_value=trainer_result),
    )
    monkeypatch.setattr(
        training_module,
        "_verify_full_run_evidence_for_publication",
        evidence_verifier,
    )

    result = run_phase40_qwen_training(
        config,
        data_contract=contract,
        run_request=SimpleNamespace(),
        repo_root=tmp_path,
    )
    assert result["safety_gate_passed"] is False
    assert result["verified_evidence"] is evidence
    assert result["artifact_record"] is None
    assert result["registry_published"] is False
    publisher.assert_not_called()
    evidence_verifier.assert_called_once()


def test_full_materializer_builds_and_reverifies_fixed_bundle(tmp_path, monkeypatch):
    import src.model_adaptation.training as training_module
    from src.model_adaptation.phase40_graphs import render_phase40_graphs as real_render

    torch = pytest.importorskip("torch")
    contract = _fixture_contract(tmp_path, all_labels=True)
    snapshot = _sealed_qwen_snapshot(tmp_path / "base-model")
    transfer = _transfer_authority()
    config = build_training_config(
        candidate_id="qwen3-4b-instruct-2507",
        train_split_path=tmp_path / "train.jsonl",
        val_split_path=tmp_path / "val.jsonl",
        version_tag="phase40-full-fixture",
        output_root=tmp_path / "models",
        registry_path=tmp_path / "registry.json",
        selection=_selection(),
        adaptation_mode=AdaptationMode.LORA,
        run_kind=RunKind.FULL,
        run_id="qwen-lora-fixture",
        transfer_authority=transfer,
        sanitized_argv=(
            "phase40-train",
            "--run-id=qwen-lora-fixture",
            "--adaptation-mode=lora",
        ),
        run_bundle_root=tmp_path / "returned" / "qwen-lora",
    )
    config = replace(
        config,
        model_id=PHASE40_QWEN_MODEL_ID,
        base_model_path=snapshot.local_snapshot_path,
    )
    controlled = _resume_config().model_copy(
        update={
            "model_id": PHASE40_QWEN_MODEL_ID,
            "splits": tuple(
                CanonicalSplitEvidence(
                    logical_name=name,
                    relative_path=snapshot.identity.relative_path,
                    records=snapshot.identity.records,
                    bytes=snapshot.identity.bytes,
                    sha256=snapshot.whole_file_sha256,
                    ordered_row_ids_sha256=hashlib.sha256(
                        b"phase40-ordered-row-ids-v1\0"
                        + b"".join(
                            row_id.encode("ascii") + b"\n" for row_id in snapshot.row_ids
                        )
                    ).hexdigest(),
                )
                for name, snapshot in (
                    ("train", contract.train_snapshot),
                    ("val", contract.validation_snapshot),
                )
            ),
            "additional_controls": tuple(
                sorted(
                    (
                        NamedControl(name="input_archive_sha256", value="c" * 64),
                        NamedControl(name="input_manifest_sha256", value="d" * 64),
                        NamedControl(name="report_to", value="none"),
                        NamedControl(name="source_archive_sha256", value="a" * 64),
                        NamedControl(name="source_inventory_sha256", value="b" * 64),
                    ),
                    key=lambda item: item.name,
                )
            ),
        }
    )
    config = replace(
        config,
        requested_control_template=_requested_template(controlled),
    )
    artifact_identity = "adapter-state-sha256:" + "e" * 64
    rows = tuple(
        Phase40PredictionRow.from_raw(
            validation_row_id=row.validation_row_id,
            sequence_index=index,
            gold_label=row.record.label,
            raw_prediction=json.dumps({"label": row.record.label}),
            artifact_identity=artifact_identity,
            checkpoint_step=10,
        )
        for index, row in enumerate(contract.validation_snapshot.rows)
    )
    metrics = evaluate_phase40_predictions(
        expected_validation_row_ids=contract.validation_snapshot.validation_row_ids,
        gold_labels=tuple(row.record.label for row in contract.validation_snapshot.rows),
        prediction_rows=rows,
    )
    selection = select_phase40_checkpoint((metrics,))
    recorder = SimpleNamespace(metrics_by_candidate={(10, artifact_identity): metrics})

    run_root = training_module._evidence_root(config)
    event_path = run_root / "events.jsonl"
    callback_events = (
        (CallbackEventKind.TRAIN_BEGIN, 0, (), None),
        (CallbackEventKind.LOG, 5, (("loss", 0.5),), None),
        (CallbackEventKind.EVALUATION, 10, (("eval_loss", 0.4),), 1.0),
        (CallbackEventKind.CHECKPOINT, 10, (("measurement_scope", "isolated"),), 2.0),
        (CallbackEventKind.TRAIN_END, 10, (), 20.0),
    )
    for sequence_id, (kind, step, values, duration) in enumerate(callback_events):
        _append_callback_run_event(
            event_path,
            Phase40CallbackEvent(
                sequence_id=sequence_id,
                source_run_id="qwen-lora-fixture",
                run_kind=RunKind.FULL,
                event_kind=kind,
                timestamp_utc="2026-08-24T12:00:00Z",
                optimizer_step=step,
                epoch=float(step) / 10,
                duration_seconds=duration,
                is_warmup=False if kind == CallbackEventKind.OPTIMIZER_STEP else None,
                values=values,
            ),
        )

    training_root = tmp_path / "trainer"
    training_root.mkdir()
    (training_root / "trainer_state.json").write_text(
        json.dumps({"global_step": 10}),
        encoding="utf-8",
    )
    adapter = tmp_path / "adapter"
    adapter.mkdir()
    (adapter / "adapter_config.json").write_text("{}", encoding="utf-8")
    (adapter / "adapter_model.bin").write_bytes(b"adapter")
    (adapter / PHASE40_BASE_MODEL_MANIFEST_NAME).write_bytes(
        training_module._canonical_json_line(snapshot.portable_manifest())
    )
    resource = Phase40ResourceSummary(
        source_run_id="qwen-lora-fixture",
        run_kind=RunKind.FULL,
        warmup_optimizer_steps=0,
        observed_optimizer_steps=10,
        retained_optimizer_steps=10,
        steady_state_step_seconds_median=1.0,
        examples_per_second=1.0,
        tokens_per_second=10.0,
        peak_allocated_bytes=100,
        peak_reserved_bytes=200,
        evaluation_overhead_seconds=1.0,
        checkpoint_overhead_seconds=2.0,
        measured_overhead_seconds=3.0,
        actual_wall_seconds=20.0,
        planned_full_optimizer_steps=100,
        projected_local_runtime_seconds=103.0,
    )
    monkeypatch.setattr(
        training_module,
        "render_phase40_graphs",
        lambda root: real_render(
            root,
            renderer=lambda _data, _options: b"fixture-png",
            renderer_name="fixture-renderer",
            renderer_version="1.0",
        ),
    )
    evidence_path, evidence = _materialize_full_run_evidence(
        config,
        data_contract=contract,
        controlled_config=controlled,
        quantization_proof=_lora_quantization_proof(),
        checkpoint_selection=selection,
        validation_recorder=recorder,
        adapter_output_dir=adapter,
        training_output_dir=training_root,
        event_path=event_path,
        resource_summary=resource,
        torch_module=torch,
        transformers_module=SimpleNamespace(__version__="5.0.0"),
        peft_module=SimpleNamespace(__version__="0.18.0"),
        base_model_snapshot=snapshot,
    )
    assert evidence_path == run_root / "run-evidence.json"
    assert evidence.transfer_authority == transfer
    assert evidence.validation_metrics["macro_f1"] == 1.0
    assert (run_root / "adapter-or-model").is_dir()
    assert (run_root / "predictions.json").is_file()
    assert (run_root / "validation-metrics.json").is_file()
    assert (run_root / "curves" / "loss-curves.png").read_bytes() == b"fixture-png"
