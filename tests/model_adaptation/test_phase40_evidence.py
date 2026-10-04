from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.model_adaptation.phase40_evidence import (
    AcceleratorIdentity,
    ArtifactEvidence,
    CadenceControls,
    CanonicalSplitEvidence,
    DecoderContractEvidence,
    EvidenceStatus,
    ExperimentIdentityEvidence,
    NamedControl,
    OptimizerControls,
    PrecisionControls,
    QuantizationProofEvidence,
    ResumeControlledConfig,
    RunEvent,
    RunEventKind,
    RunEvidence,
    RuntimeHardwareEvidence,
    SelectedCheckpointEvidence,
    TransferAuthorityEvidence,
    ValidationCheckpointEvidence,
    append_run_event,
    compare_qwen_configs,
    compute_resume_digest,
    finalize_run_evidence,
    load_run_events,
    sanitize_argv,
    sanitize_environment,
    verify_phase40_bundle,
)
from src.model_adaptation.phase40_graphs import (
    GraphRenderOptions,
    build_normalized_graph_data,
    render_phase40_graphs,
    verify_graph_provenance,
)
from src.model_adaptation.phase40_modes import (
    AdaptationMode,
    ModelFamily,
    ResolvedQwenMode,
    RunKind,
)
from src.model_adaptation.registry import build_model_checksum
from src.model_adaptation.schemas import LOCKED_RELEASE_LABELS


RUN_ID = "phase40-fixture-run"
ADAPTER_IDENTITY = "adapter-state-sha256:" + "a" * 64
MODEL_IDENTITY = "model-state-sha256:" + "b" * 64


def _event(
    sequence_id: int,
    kind: RunEventKind,
    step: int,
    values: dict[str, object],
    *,
    epoch: float = 0.25,
    run_kind: RunKind = RunKind.FULL,
) -> RunEvent:
    return RunEvent(
        schema_version="phase40-run-event-v1",
        sequence_id=sequence_id,
        event_kind=kind,
        timestamp_utc=datetime(2026, 8, 24, 9, 0, sequence_id, tzinfo=timezone.utc),
        optimizer_step=step,
        epoch=epoch,
        trainer_values=values,
        source_run_id=RUN_ID,
        run_kind=run_kind,
    )


def _write_raw_sources(run_root: Path) -> None:
    run_root.mkdir()
    events = run_root / "events.jsonl"
    for event in (
        _event(0, RunEventKind.RUN_START, 0, {"status": "started"}, epoch=0.0),
        _event(1, RunEventKind.TRAIN_LOG, 1, {"loss": 1.25, "learning_rate": 0.0002}),
        _event(2, RunEventKind.TRAIN_LOG, 1, {"loss": 1.0, "learning_rate": 0.0002}),
        _event(3, RunEventKind.EVALUATION, 1, {"eval_loss": 0.9}),
        _event(4, RunEventKind.CHECKPOINT, 1, {"checkpoint_saved": True}),
        _event(5, RunEventKind.RUN_END, 1, {"status": "completed"}),
    ):
        append_run_event(events, event)
    (run_root / "resolved-config.json").write_text(
        _resume_config().model_dump_json(),
        encoding="utf-8",
    )
    (run_root / "trainer_state.json").write_text(
        json.dumps({"global_step": 1, "epoch": 0.25}),
        encoding="utf-8",
    )
    (run_root / "predictions.jsonl").write_text(
        json.dumps({"validation_row_id": "p40-row-v1-fixture-1", "label": "benign"})
        + "\n"
        + json.dumps({"validation_row_id": "p40-row-v1-fixture-2", "label": "task_scam"})
        + "\n",
        encoding="utf-8",
    )
    (run_root / "validation-metrics.json").write_text(
        json.dumps({"macro_f1": 1.0, "checkpoint_step": 1}),
        encoding="utf-8",
    )
    model = run_root / "adapter-or-model"
    model.mkdir()
    (model / "adapter_config.json").write_text("{}", encoding="utf-8")
    (model / "adapter_model.safetensors").write_bytes(b"fixture-adapter-weights")


def _fixture_renderer(data, options) -> bytes:
    digest = hashlib.sha256(data.canonical_bytes + options.sha256.encode("ascii")).digest()
    return b"fixture-png\0" + digest


def _artifact(run_root: Path, logical_name: str, role: str, relative_path: str) -> ArtifactEvidence:
    path = run_root / relative_path
    return ArtifactEvidence(
        logical_name=logical_name,
        role=role,
        relative_path=relative_path,
        kind="directory" if path.is_dir() else "file",
        sha256=build_model_checksum(path),
    )


def _split(logical_name: str, marker: str) -> CanonicalSplitEvidence:
    return CanonicalSplitEvidence(
        logical_name=logical_name,
        relative_path=f"canonical/{logical_name}.jsonl",
        records=4,
        bytes=256,
        sha256=marker * 64,
        ordered_row_ids_sha256=("f" if marker != "f" else "e") * 64,
    )


def _lora_proof() -> QuantizationProofEvidence:
    return QuantizationProofEvidence(
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
        adapter_trainable_count=7,
        backward_with_adapter_gradients=False,
        adapter_gradient_finite_count=0,
        adapter_gradient_nonzero_count=0,
    )


def _qlora_proof() -> QuantizationProofEvidence:
    return QuantizationProofEvidence(
        requested_mode=AdaptationMode.QLORA,
        resolved_mode=ResolvedQwenMode.FOUR_BIT_QLORA,
        bitsandbytes_version="0.50.1",
        load_in_4bit=True,
        nf4=True,
        double_quantization=True,
        is_loaded_in_4bit=True,
        linear4bit_modules=28,
        kbit_preparation_applied=True,
        base_weights_frozen=True,
        adapter_only_trainables=True,
        adapter_trainable_count=7,
        backward_with_adapter_gradients=True,
        adapter_gradient_finite_count=7,
        adapter_gradient_nonzero_count=7,
    )


def _decoder(**updates: object) -> DecoderContractEvidence:
    payload: dict[str, object] = {
        "schema_version": "phase40-qwen-decoder-v1",
        "do_sample": False,
        "num_return_sequences": 1,
        "max_new_tokens": 256,
        "output_schema_version": "phase40-label-json-v1",
        "decoder_version": "phase40-deterministic-v1",
        "generation_cadence": "every-evaluation-and-final",
        "raw_prediction_ordering_policy": "canonical-validation-order-v1",
    }
    payload.update(updates)
    return DecoderContractEvidence.model_validate(payload)


def _transfer_authority() -> TransferAuthorityEvidence:
    return TransferAuthorityEvidence(
        schema_version="phase40-transfer-authority-v1",
        source_archive_sha256="6" * 64,
        source_inventory_sha256="7" * 64,
        input_archive_sha256="8" * 64,
        input_manifest_sha256="9" * 64,
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


def _complete_evidence(run_root: Path, graph) -> RunEvidence:
    controlled_config = ResumeControlledConfig.model_validate_json(
        (run_root / "resolved-config.json").read_text(encoding="utf-8")
    )
    artifacts = tuple(
        sorted(
            (
                _artifact(run_root, "events", "events", "events.jsonl"),
                _artifact(
                    run_root,
                    "graph-data-loss",
                    "graph_data",
                    "curves/normalized-loss-curves.json",
                ),
                _artifact(
                    run_root,
                    "graph-manifest-loss",
                    "graph_manifest",
                    "curves/graph-provenance.json",
                ),
                _artifact(
                    run_root,
                    "graph-output-loss",
                    "graph_output",
                    "curves/loss-curves.png",
                ),
                _artifact(run_root, "model-artifact", "model_artifact", "adapter-or-model"),
                _artifact(run_root, "predictions", "predictions", "predictions.jsonl"),
                _artifact(run_root, "resolved-config", "resolved_config", "resolved-config.json"),
                _artifact(run_root, "trainer-state", "trainer_state", "trainer_state.json"),
                _artifact(
                    run_root,
                    "validation-metrics",
                    "metrics",
                    "validation-metrics.json",
                ),
            ),
            key=lambda artifact: artifact.logical_name,
        )
    )
    decoder = _decoder()
    checkpoint = ValidationCheckpointEvidence(
        optimizer_step=1,
        artifact_identity=ADAPTER_IDENTITY,
        predictions_sha256=next(a.sha256 for a in artifacts if a.logical_name == "predictions"),
        metrics_sha256=next(
            a.sha256 for a in artifacts if a.logical_name == "validation-metrics"
        ),
        macro_f1=1.0,
        safety_gate_passed=True,
        invalid_output_count=0,
    )
    return RunEvidence(
        schema_version="phase40-run-evidence-v1",
        run_id=RUN_ID,
        run_kind=RunKind.FULL,
        experiment_identity=ExperimentIdentityEvidence(
            model_family=ModelFamily.QWEN,
            adaptation_mode=AdaptationMode.LORA,
            run_kind=RunKind.FULL,
        ),
        model_id="qwen3.5-4b",
        model_revision="a" * 40,
        splits=controlled_config.splits,
        seed=42,
        data_seed=42,
        resolved_config_sha256=next(
            a.sha256 for a in artifacts if a.logical_name == "resolved-config"
        ),
        resume_digest=compute_resume_digest(controlled_config),
        prompt_or_preprocessor_sha256=controlled_config.formatter_or_preprocessor_sha256,
        decoder_contract=decoder,
        decoder_contract_sha256=decoder.sha256,
        sanitized_argv=("train", "--adaptation-mode=lora", "--max-new-tokens=256"),
        package_versions={"accelerate": "1.13.0", "torch": "2.12.0"},
        hardware=RuntimeHardwareEvidence(
            python_version="3.13.7",
            platform="Windows-11",
            cuda_version="13.0",
            cudnn_version="9.9",
            gpu_name="RTX-5050",
            gpu_compute_capability="12.0",
            gpu_total_memory_bytes=8_000_000_000,
            bf16_enabled=True,
            fp16_enabled=False,
            tf32_enabled=True,
        ),
        quantization=_lora_proof(),
        peak_allocated_bytes=1_000,
        peak_reserved_bytes=2_000,
        steady_step_seconds_median=0.5,
        validation_metrics={"macro_f1": 1.0},
        validation_checkpoints=(checkpoint,),
        selected_checkpoint=SelectedCheckpointEvidence(
            optimizer_step=1,
            artifact_identity=ADAPTER_IDENTITY,
            safety_gate_passed=True,
            rationale="Passed safety floors and had the highest macro F1.",
        ),
        artifacts=artifacts,
        artifact_sha256={artifact.logical_name: artifact.sha256 for artifact in artifacts},
        graph_provenance=(graph.as_evidence(),),
        transfer_authority=_transfer_authority(),
        status=EvidenceStatus.COMPLETE,
        comparison_eligible=True,
        failure_reason=None,
    )


def _render(run_root: Path):
    return render_phase40_graphs(
        run_root,
        renderer=_fixture_renderer,
        renderer_name="fixture-renderer",
        renderer_version="1.0",
        smoothing_window=2,
    )


def test_synthetic_event_log_finalizes_and_replays_graph_deterministically(tmp_path):
    run_root = tmp_path / "run"
    _write_raw_sources(run_root)
    graph_first = _render(run_root)
    normalized_first = (run_root / "curves" / "normalized-loss-curves.json").read_bytes()
    provenance_first = (run_root / "curves" / "graph-provenance.json").read_bytes()

    graph_second = _render(run_root)
    assert graph_second == graph_first
    assert (run_root / "curves" / "normalized-loss-curves.json").read_bytes() == normalized_first
    assert (run_root / "curves" / "graph-provenance.json").read_bytes() == provenance_first
    assert graph_first.options.raw_points_authoritative is True
    assert graph_first.options.smoothing_label == "trailing-mean-window-2"

    evidence = _complete_evidence(run_root, graph_first)
    evidence_path = finalize_run_evidence(run_root, evidence)
    assert verify_phase40_bundle(run_root) == evidence
    persisted = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert "git_commit" not in persisted
    assert persisted["splits"][0]["logical_name"] == "train"
    assert persisted["splits"][1]["logical_name"] == "val"


def test_complete_full_evidence_requires_transfer_authority(tmp_path):
    run_root = tmp_path / "run"
    _write_raw_sources(run_root)
    evidence = _complete_evidence(run_root, _render(run_root))
    payload = evidence.model_dump(mode="python")
    payload.pop("transfer_authority")

    with pytest.raises(ValidationError, match="transfer authority"):
        RunEvidence.model_validate(payload)


def test_checkpoint_identity_prefix_is_bound_to_model_family(tmp_path):
    run_root = tmp_path / "run"
    _write_raw_sources(run_root)
    qwen = _complete_evidence(run_root, _render(run_root))

    wrong_qwen = qwen.model_dump(mode="python")
    wrong_qwen["validation_checkpoints"][0]["artifact_identity"] = MODEL_IDENTITY
    wrong_qwen["selected_checkpoint"]["artifact_identity"] = MODEL_IDENTITY
    with pytest.raises(ValidationError, match="model-family contract"):
        RunEvidence.model_validate(wrong_qwen)

    phobert = qwen.model_dump(mode="python")
    phobert["experiment_identity"] = {
        "model_family": ModelFamily.PHOBERT,
        "adaptation_mode": AdaptationMode.CLASSIFICATION_HEAD,
        "run_kind": RunKind.FULL,
    }
    phobert["model_id"] = "phobert-base-v2"
    phobert["decoder_contract"] = None
    phobert["decoder_contract_sha256"] = None
    phobert["quantization"] = None
    phobert["validation_checkpoints"][0]["artifact_identity"] = MODEL_IDENTITY
    phobert["selected_checkpoint"]["artifact_identity"] = MODEL_IDENTITY
    phobert["artifacts"] = list(phobert["artifacts"])
    phobert["artifacts"].append(
        {
            "logical_name": "preprocessing",
            "role": "preprocessing",
            "relative_path": "preprocessing.json",
            "kind": "file",
            "sha256": "c" * 64,
        }
    )
    phobert["artifacts"].sort(key=lambda artifact: artifact["logical_name"])
    phobert["artifacts"] = tuple(phobert["artifacts"])
    phobert["artifact_sha256"] = {
        artifact["logical_name"]: artifact["sha256"] for artifact in phobert["artifacts"]
    }

    validated = RunEvidence.model_validate(phobert)
    assert validated.validation_checkpoints[0].artifact_identity == MODEL_IDENTITY


@pytest.mark.parametrize("field_name", tuple(TransferAuthorityEvidence.model_fields))
def test_transfer_authority_rejects_every_missing_field(field_name):
    payload = _transfer_authority().model_dump(mode="python")
    payload.pop(field_name)

    with pytest.raises(ValidationError):
        TransferAuthorityEvidence.model_validate(payload)


@pytest.mark.parametrize(
    ("field_name", "mutated_value"),
    [
        ("schema_version", "phase40-transfer-authority-v2"),
        ("source_archive_sha256", "g" * 64),
        ("source_inventory_sha256", "0" * 63),
        ("input_archive_sha256", "A" * 64),
        ("input_manifest_sha256", "not-a-sha256"),
        ("source_repository_relative_archive_path", "alternate/source.zip"),
        ("source_repository_relative_inventory_path", "alternate/manifest.json"),
        ("input_repository_relative_path", "alternate/input.zip"),
        ("input_drive_path", "/content/drive/MyDrive/alternate.zip"),
        ("input_extraction_root", "/content/alternate"),
        ("input_members", ("phase40-input-manifest.json", "val.jsonl", "train.jsonl")),
        ("no_held_out_boundary", False),
    ],
)
def test_transfer_authority_rejects_mutated_contract_fields(field_name, mutated_value):
    payload = _transfer_authority().model_dump(mode="python")
    payload[field_name] = mutated_value

    with pytest.raises(ValidationError):
        TransferAuthorityEvidence.model_validate(payload)


def test_transfer_authority_is_frozen():
    authority = _transfer_authority()
    with pytest.raises(ValidationError, match="frozen"):
        authority.input_archive_sha256 = "f" * 64


def test_event_log_preserves_adjacent_same_step_but_rejects_gaps_and_nonfinite(tmp_path):
    valid = tmp_path / "valid.jsonl"
    append_run_event(valid, _event(0, RunEventKind.TRAIN_LOG, 4, {"loss": 1.0}))
    append_run_event(valid, _event(1, RunEventKind.EVALUATION, 4, {"eval_loss": 0.8}))
    assert [event.optimizer_step for event in load_run_events(valid)] == [4, 4]

    gap = tmp_path / "gap.jsonl"
    gap.write_text(
        _event(0, RunEventKind.TRAIN_LOG, 1, {"loss": 1.0}).model_dump_json()
        + "\n"
        + _event(2, RunEventKind.EVALUATION, 2, {"eval_loss": 0.8}).model_dump_json()
        + "\n",
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="contiguous"):
        load_run_events(gap)

    nonfinite = tmp_path / "nonfinite.jsonl"
    nonfinite.write_text(
        '{"schema_version":"phase40-run-event-v1","sequence_id":0,'
        '"event_kind":"train_log","timestamp_utc":"2026-08-24T09:00:00Z",'
        '"optimizer_step":0,"epoch":0.0,"trainer_values":{"loss":NaN},'
        f'"source_run_id":"{RUN_ID}","run_kind":"full"}}\n',
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="invalid event"):
        load_run_events(nonfinite)


def test_event_log_rejects_mixed_probe_and_full_lineage(tmp_path):
    event_path = tmp_path / "events.jsonl"
    append_run_event(
        event_path,
        _event(0, RunEventKind.RUN_START, 0, {"status": "started"}),
    )
    with pytest.raises(ValueError, match="run_kind"):
        append_run_event(
            event_path,
            _event(
                1,
                RunEventKind.TRAIN_LOG,
                1,
                {"loss": 1.0},
                run_kind=RunKind.PROBE,
            ),
        )

    mixed_path = tmp_path / "mixed.jsonl"
    mixed_path.write_text(
        _event(0, RunEventKind.RUN_START, 0, {"status": "started"}).model_dump_json()
        + "\n"
        + _event(
            1,
            RunEventKind.TRAIN_LOG,
            1,
            {"loss": 1.0},
            run_kind=RunKind.PROBE,
        ).model_dump_json()
        + "\n",
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="mixes probe and full"):
        load_run_events(mixed_path)


def test_event_log_allows_step_rollback_only_at_failed_attempt_restart(tmp_path):
    event_path = tmp_path / "events.jsonl"
    for event in (
        _event(0, RunEventKind.RUN_START, 0, {"status": "started"}),
        _event(1, RunEventKind.TRAIN_LOG, 305, {"loss": 0.4}),
        _event(2, RunEventKind.FAILURE, 305, {"failure_category": "runtime_failure"}),
        _event(3, RunEventKind.RUN_START, 300, {"status": "resumed"}),
        _event(4, RunEventKind.STEP_TIMING, 301, {"duration_seconds": 0.5}),
    ):
        append_run_event(event_path, event)
    assert [event.optimizer_step for event in load_run_events(event_path)] == [
        0,
        305,
        305,
        300,
        301,
    ]

    direct_rollback = tmp_path / "direct-rollback.jsonl"
    append_run_event(
        direct_rollback,
        _event(0, RunEventKind.RUN_START, 0, {"status": "started"}),
    )
    append_run_event(
        direct_rollback,
        _event(1, RunEventKind.TRAIN_LOG, 305, {"loss": 0.4}),
    )
    with pytest.raises(ValueError, match="preceding failure"):
        append_run_event(
            direct_rollback,
            _event(2, RunEventKind.RUN_START, 300, {"status": "resumed"}),
        )

    post_failure_work = tmp_path / "post-failure-work.jsonl"
    for event in (
        _event(0, RunEventKind.RUN_START, 0, {"status": "started"}),
        _event(1, RunEventKind.FAILURE, 8, {"failure_category": "runtime_failure"}),
    ):
        append_run_event(post_failure_work, event)
    with pytest.raises(ValueError, match="run_end or a new run_start"):
        append_run_event(
            post_failure_work,
            _event(2, RunEventKind.TRAIN_LOG, 9, {"loss": 0.3}),
        )


def _rewrite_events(event_path: Path, events: tuple[RunEvent, ...]) -> None:
    event_path.unlink()
    for sequence_id, event in enumerate(events):
        append_run_event(
            event_path,
            event.model_copy(update={"sequence_id": sequence_id}),
        )


def _graph_bound_to_current_events(run_root: Path, graph):
    return graph.model_copy(
        update={
            "event_source": graph.event_source.model_copy(
                update={"sha256": build_model_checksum(run_root / "events.jsonl")}
            )
        }
    )


def test_complete_evidence_rejects_event_lineage_mismatch(tmp_path):
    run_root = tmp_path / "run"
    _write_raw_sources(run_root)
    event_path = run_root / "events.jsonl"
    events = load_run_events(event_path)
    _rewrite_events(
        event_path,
        tuple(event.model_copy(update={"run_kind": RunKind.PROBE}) for event in events),
    )
    graph = _render(run_root)

    with pytest.raises(RuntimeError, match="event run_kind does not match"):
        finalize_run_evidence(run_root, _complete_evidence(run_root, graph))


@pytest.mark.parametrize(
    ("omitted_kinds", "message"),
    [
        ({RunEventKind.RUN_START}, "begin with run_start"),
        ({RunEventKind.TRAIN_LOG, RunEventKind.STEP_TIMING}, "step timing/log"),
        ({RunEventKind.EVALUATION}, "evaluation event"),
        ({RunEventKind.CHECKPOINT}, "checkpoint event"),
        ({RunEventKind.RUN_END}, "end with run_end"),
    ],
)
def test_complete_full_evidence_requires_every_lifecycle_stage(
    tmp_path,
    omitted_kinds,
    message,
):
    run_root = tmp_path / "run"
    _write_raw_sources(run_root)
    graph = _render(run_root)
    event_path = run_root / "events.jsonl"
    retained = tuple(
        event
        for event in load_run_events(event_path)
        if event.event_kind not in omitted_kinds
    )
    _rewrite_events(event_path, retained)
    graph = _graph_bound_to_current_events(run_root, graph)

    with pytest.raises(RuntimeError, match=message):
        finalize_run_evidence(run_root, _complete_evidence(run_root, graph))


def test_complete_full_evidence_rejects_out_of_order_lifecycle(tmp_path):
    run_root = tmp_path / "run"
    _write_raw_sources(run_root)
    graph = _render(run_root)
    event_path = run_root / "events.jsonl"
    events = load_run_events(event_path)
    checkpoint = next(event for event in events if event.event_kind == RunEventKind.CHECKPOINT)
    evaluation = next(event for event in events if event.event_kind == RunEventKind.EVALUATION)
    reordered = tuple(
        event
        for event in events
        if event.event_kind not in {RunEventKind.CHECKPOINT, RunEventKind.EVALUATION, RunEventKind.RUN_END}
    ) + (
        checkpoint,
        evaluation,
        events[-1],
    )
    _rewrite_events(event_path, reordered)
    graph = _graph_bound_to_current_events(run_root, graph)

    with pytest.raises(RuntimeError, match="order training before evaluation"):
        finalize_run_evidence(run_root, _complete_evidence(run_root, graph))


def test_complete_full_evidence_retains_failed_attempt_before_successful_resume(tmp_path):
    run_root = tmp_path / "run"
    _write_raw_sources(run_root)
    event_path = run_root / "events.jsonl"
    resumed = (
        _event(0, RunEventKind.RUN_START, 0, {"status": "started"}, epoch=0.0),
        _event(1, RunEventKind.TRAIN_LOG, 1, {"loss": 1.25}),
        _event(2, RunEventKind.FAILURE, 1, {"failure_category": "runtime_failure"}),
        _event(3, RunEventKind.RUN_START, 1, {"status": "resumed"}),
        _event(4, RunEventKind.STEP_TIMING, 1, {"duration_seconds": 0.5}),
        _event(5, RunEventKind.EVALUATION, 1, {"eval_loss": 0.9}),
        _event(6, RunEventKind.CHECKPOINT, 1, {"checkpoint_saved": True}),
        _event(7, RunEventKind.RUN_END, 1, {"status": "completed"}),
    )
    _rewrite_events(event_path, resumed)
    graph = _render(run_root)

    evidence_path = finalize_run_evidence(run_root, _complete_evidence(run_root, graph))
    assert evidence_path.is_file()
    assert any(event.event_kind == RunEventKind.FAILURE for event in load_run_events(event_path))


def test_complete_full_evidence_rejects_failure_in_final_attempt(tmp_path):
    run_root = tmp_path / "run"
    _write_raw_sources(run_root)
    event_path = run_root / "events.jsonl"
    failed = (
        _event(0, RunEventKind.RUN_START, 0, {"status": "started"}, epoch=0.0),
        _event(1, RunEventKind.TRAIN_LOG, 1, {"loss": 1.25}),
        _event(2, RunEventKind.EVALUATION, 1, {"eval_loss": 0.9}),
        _event(3, RunEventKind.CHECKPOINT, 1, {"checkpoint_saved": True}),
        _event(4, RunEventKind.FAILURE, 1, {"failure_category": "runtime_failure"}),
        _event(5, RunEventKind.RUN_END, 1, {"status": "completed"}),
    )
    _rewrite_events(event_path, failed)
    graph = _render(run_root)

    with pytest.raises(RuntimeError, match="final attempt cannot contain a failure"):
        finalize_run_evidence(run_root, _complete_evidence(run_root, graph))


def _prestart_evidence(run_root: Path, complete: RunEvidence) -> RunEvidence:
    diagnostic_path = run_root / "prestart-failure.json"
    diagnostic_path.write_text(
        json.dumps({"status": "prestart_failed", "reason": "package candidate rejected"}),
        encoding="utf-8",
    )
    diagnostic = _artifact(
        run_root,
        "prestart-failure",
        "failure_evidence",
        "prestart-failure.json",
    )
    payload = complete.model_dump(mode="python")
    payload.update(
        {
            "status": EvidenceStatus.PRESTART_FAILED,
            "comparison_eligible": False,
            "failure_reason": "package candidate rejected",
            "peak_allocated_bytes": 0,
            "peak_reserved_bytes": 0,
            "steady_step_seconds_median": None,
            "validation_metrics": {},
            "validation_checkpoints": (),
            "selected_checkpoint": None,
            "artifacts": (diagnostic,),
            "artifact_sha256": {diagnostic.logical_name: diagnostic.sha256},
            "graph_provenance": (),
        }
    )
    return RunEvidence.model_validate(payload)


def test_verify_prestart_failure_requires_explicit_flag_and_rehashes(tmp_path):
    run_root = tmp_path / "run"
    _write_raw_sources(run_root)
    complete = _complete_evidence(run_root, _render(run_root))
    prestart = _prestart_evidence(run_root, complete)
    evidence_path = run_root / "run-evidence.json"
    evidence_path.write_text(prestart.model_dump_json() + "\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="not complete"):
        verify_phase40_bundle(run_root)
    assert verify_phase40_bundle(run_root, allow_prestart_failure=True) == prestart
    with pytest.raises(TypeError, match="must be a boolean"):
        verify_phase40_bundle(run_root, allow_prestart_failure="yes")

    with (run_root / "prestart-failure.json").open("ab") as handle:
        handle.write(b" ")
    with pytest.raises(RuntimeError, match="SHA-256 mismatch"):
        verify_phase40_bundle(run_root, allow_prestart_failure=True)


def test_missing_or_mutated_sources_block_finalize_and_verification(tmp_path):
    run_root = tmp_path / "run"
    _write_raw_sources(run_root)
    graph = _render(run_root)
    evidence = _complete_evidence(run_root, graph)
    (run_root / "trainer_state.json").unlink()
    with pytest.raises(RuntimeError, match="trainer-state"):
        finalize_run_evidence(run_root, evidence)

    (run_root / "trainer_state.json").write_text(
        json.dumps({"global_step": 1, "epoch": 0.25}),
        encoding="utf-8",
    )
    evidence = _complete_evidence(run_root, graph)
    finalize_run_evidence(run_root, evidence)
    with (run_root / "validation-metrics.json").open("ab") as handle:
        handle.write(b" ")
    with pytest.raises(RuntimeError, match="SHA-256 mismatch"):
        verify_phase40_bundle(run_root)
    with pytest.raises(RuntimeError, match="hash mismatch"):
        verify_graph_provenance(run_root)


def test_empty_graph_source_and_missing_evidence_fields_fail_closed(tmp_path):
    run_root = tmp_path / "run"
    _write_raw_sources(run_root)
    (run_root / "validation-metrics.json").write_bytes(b"")
    options = GraphRenderOptions(
        schema_version="phase40-graph-options-v1",
        graph_id="loss-curves",
        smoothing_window=None,
        smoothing_label=None,
        raw_points_authoritative=True,
        output_format="png",
        dpi=120,
    )
    with pytest.raises(RuntimeError, match="missing or empty"):
        build_normalized_graph_data(
            run_root / "events.jsonl",
            run_root / "validation-metrics.json",
            options=options,
        )
    with pytest.raises(ValidationError, match="run_id"):
        RunEvidence.model_validate({"schema_version": "phase40-run-evidence-v1"})


def test_sanitizers_retain_controls_but_reject_credentials_and_personal_paths():
    assert sanitize_argv(("train", "--max-new-tokens=256", "--seed=42")) == (
        "train",
        "--max-new-tokens=256",
        "--seed=42",
    )
    with pytest.raises(ValueError, match="secret-bearing"):
        sanitize_argv(("train", "--api-key=sk-this-must-never-persist"))
    with pytest.raises(ValueError, match="absolute or personal"):
        sanitize_argv(("train", r"C:\Users\student\model"))
    assert sanitize_argv(
        (
            "phase40-train-qwen",
            "--input-archive",
            "/content/drive/MyDrive/internship-phase40/phase40-train-validation.zip",
            "--extraction-root=/content/phase40-input-v1",
            "--output-root",
            "/content/drive/MyDrive/internship-phase40/work/qwen-lora",
        )
    )[0] == "phase40-train-qwen"
    with pytest.raises(ValueError, match="absolute or personal"):
        sanitize_argv(("train", "/content/other-project/private-model"))
    with pytest.raises(ValueError, match="absolute or personal"):
        sanitize_argv(
            (
                "train",
                "/content/drive/MyDrive/internship-phase40/../other-project/model",
            )
        )

    environment = {
        "python_version": "3.13.7",
        "platform": "Linux",
        "cuda_version": "13.0",
        "cudnn_version": "9.9",
        "gpu_name": "T4",
        "gpu_compute_capability": "7.5",
        "gpu_total_memory_bytes": 16_000,
        "bf16_enabled": False,
        "fp16_enabled": True,
        "tf32_enabled": False,
    }
    assert sanitize_environment(environment).gpu_name == "T4"
    with pytest.raises(ValueError, match="non-allowlisted"):
        sanitize_environment({**environment, "API_TOKEN": "secret"})


def _resume_config(
    *,
    mode: AdaptationMode = AdaptationMode.LORA,
    accelerator_name: str = "RTX-5050",
) -> ResumeControlledConfig:
    proof = _lora_proof() if mode == AdaptationMode.LORA else _qlora_proof()
    return ResumeControlledConfig(
        schema_version="phase40-resume-controlled-config-v1",
        experiment_identity=ExperimentIdentityEvidence(
            model_family=ModelFamily.QWEN,
            adaptation_mode=mode,
            run_kind=RunKind.FULL,
        ),
        model_id="qwen3.5-4b",
        model_revision="a" * 40,
        splits=(_split("train", "1"), _split("val", "2")),
        formatter_or_preprocessor_sha256="4" * 64,
        response_mask_or_preprocessor_version="phase40-response-mask-v1",
        label_order=tuple(LOCKED_RELEASE_LABELS),
        seed=42,
        data_seed=42,
        max_sequence_length=1024,
        truncation_policy="reject-target-truncation-v1",
        per_device_train_batch_size=1,
        gradient_accumulation_steps=4,
        world_size=1,
        effective_batch_size=4,
        num_train_epochs=3.0,
        max_optimizer_steps=1200,
        gradient_checkpointing=True,
        lora_rank=16,
        lora_alpha=32,
        lora_dropout=0.05,
        lora_bias="none",
        target_modules=("q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"),
        task_type="CAUSAL_LM",
        optimizer=OptimizerControls(
            optimizer="adamw_torch",
            learning_rate=0.0002,
            weight_decay=0.0,
            lr_scheduler_type="linear",
            warmup_steps=0,
            warmup_ratio=0.03,
            max_grad_norm=1.0,
        ),
        precision=PrecisionControls(
            compute_dtype="bfloat16",
            adapter_dtype="float32",
            bf16=True,
            fp16=False,
            tf32=True,
        ),
        cadence=CadenceControls(
            logging_steps=10,
            evaluation_steps=50,
            save_steps=50,
            save_total_limit=2,
            generation_steps=(50, 100, 150),
        ),
        decoder=_decoder(),
        checkpoint_selection_policy="safety-floor-then-macro-f1",
        checkpoint_selection_policy_version="phase40-checkpoint-selection-v1",
        snapshot_id_algorithm_version="phase40-snapshot-row-id-v1",
        quantization_proof=proof,
        accelerator=AcceleratorIdentity(
            accelerator_type="cuda",
            accelerator_name=accelerator_name,
            compute_capability="12.0" if accelerator_name == "RTX-5050" else "7.5",
            total_memory_bytes=8_000 if accelerator_name == "RTX-5050" else 16_000,
        ),
        additional_controls=(
            NamedControl(name="raw_batch_order", value=["canonical", "no-sort"]),
        ),
    )


@pytest.mark.parametrize(
    "mutator",
    [
        lambda config: config.model_copy(update={"seed": 43}),
        lambda config: config.model_copy(update={"model_revision": "b" * 40}),
        lambda config: config.model_copy(update={"formatter_or_preprocessor_sha256": "5" * 64}),
        lambda config: config.model_copy(
            update={"decoder": config.decoder.model_copy(update={"max_new_tokens": 255})}
        ),
        lambda config: config.model_copy(
            update={
                "cadence": config.cadence.model_copy(
                    update={"generation_steps": (50, 100, 200)}
                )
            }
        ),
        lambda config: config.model_copy(
            update={"target_modules": tuple(reversed(config.target_modules))}
        ),
        lambda config: config.model_copy(
            update={"precision": config.precision.model_copy(update={"tf32": False})}
        ),
    ],
)
def test_resume_digest_changes_for_every_control_mutation(mutator):
    original = _resume_config()
    mutated = mutator(original)
    assert compute_resume_digest(mutated) != compute_resume_digest(original)


def test_qwen_comparison_allows_only_quantization_and_marks_hardware_confounding():
    lora = _resume_config()
    exact = compare_qwen_configs(lora, lora)
    assert exact.admissible is True
    assert exact.hardware_confounded is False
    assert exact.speed_comparison_admissible is True

    qlora = _resume_config(mode=AdaptationMode.QLORA, accelerator_name="T4")
    matched = compare_qwen_configs(lora, qlora)
    assert matched.admissible is True
    assert matched.allowed_quantization_differences
    assert matched.hardware_confounded is True
    assert matched.speed_comparison_admissible is False
    assert matched.forbidden_differences == ()

    drifted = qlora.model_copy(
        update={
            "optimizer": qlora.optimizer.model_copy(update={"learning_rate": 0.00021})
        }
    )
    rejected = compare_qwen_configs(lora, drifted)
    assert rejected.admissible is False
    assert any(diff.path == "optimizer.learning_rate" for diff in rejected.forbidden_differences)


def test_qwen_config_rejects_absent_extra_and_reordered_controls():
    payload = _resume_config().model_dump(mode="python")
    absent = dict(payload)
    absent.pop("seed")
    with pytest.raises(ValidationError):
        compute_resume_digest(absent)

    extra = dict(payload)
    extra["invented_control"] = True
    with pytest.raises(ValidationError):
        compute_resume_digest(extra)

    reordered = _resume_config().model_copy(
        update={"target_modules": tuple(reversed(_resume_config().target_modules))}
    )
    comparison = compare_qwen_configs(_resume_config(), reordered)
    assert comparison.admissible is False
    assert comparison.forbidden_differences[0].path == "target_modules"
