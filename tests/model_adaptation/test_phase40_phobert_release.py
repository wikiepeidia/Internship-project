from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path

import pytest

import src.model_adaptation.phase40_phobert_release as release_module
from src.model_adaptation.phase40_contract import HeldOutIdentity
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
    compute_resume_digest,
    finalize_run_evidence,
)
from src.model_adaptation.phase40_graphs import render_phase40_graphs
from src.model_adaptation.phase40_handoff import (
    FIXED_ACTIVE_RETURNED_ROOTS,
    FIXED_INPUT_DRIVE_PATH,
    FIXED_LORA_PROBE_FILES,
    FIXED_LORA_PROBE_ROOT,
    FIXED_RETURNED_ROOTS,
    PACKAGE_CANDIDATES,
    PHASE40_COMPARISON_FINALIZER_SOURCE_ALLOWLIST,
    REQUIRED_FULL_BUNDLE_FILES,
    ComparisonFinalizerAuthority,
    FullRunRequestIdentity,
    InputBundleReference,
    InputDataMember,
    LoraProbeAuthority,
    Phase40ScopeAmendment,
    ProbeArtifactIdentity,
    RequestedControlTemplate,
    RunRequest,
    SourceBundleReference,
    SourceInventoryEntry,
    transfer_authority_from_request,
)
from src.model_adaptation.phase40_modes import (
    AdaptationMode,
    ModelFamily,
    ResolvedQwenMode,
    RunKind,
)
from src.model_adaptation.phase40_release_authorities import ReleaseAuthorityError
from src.model_adaptation.phase40_phobert_release import (
    PHOBERT_RELEASE_BUNDLE_RELATIVE_PATH,
    PHOBERT_RELEASE_MANIFEST_NAME,
    PHOBERT_RELEASE_MODEL_ROOT,
    PHOBERT_RELEASE_RECEIPT_RELATIVE_PATH,
    PHOBERT_RELEASE_TOKENIZER_ROOT,
    PhoBertReleaseError,
    build_phobert_release_bundle,
    load_phobert_release_manifest,
    load_phobert_release_receipt,
    verify_phobert_release_bundle,
)
from src.model_adaptation.phobert_training import (
    PHOBERT_BASE_MODEL_MANIFEST_NAME,
    PHOBERT_BASE_PROVENANCE_SCHEMA,
    PHOBERT_MODEL_ID,
    PHOBERT_MODEL_REVISION,
    PHOBERT_PREPROCESSOR_SHA256,
    PHOBERT_PREPROCESSOR_VERSION,
    PHOBERT_SELECTION_POLICY,
    PHOBERT_SEGMENTER_PACKAGE,
    PHOBERT_SEGMENTER_VERSION,
    PhoBertBaseModelProvenance,
)
from src.model_adaptation.registry import build_model_checksum
from src.model_adaptation.schemas import LOCKED_RELEASE_LABELS


RUN_ID = "phase40-phobert-release-fixture"
MODEL_IDENTITY = "model-state-sha256:" + "b" * 64


@dataclass(frozen=True)
class ReleaseFixture:
    repo_root: Path
    transfer_root: Path
    run_root: Path
    tokenizer_root: Path
    base_provenance_path: Path

    @property
    def bundle_root(self) -> Path:
        return self.transfer_root / Path(PHOBERT_RELEASE_BUNDLE_RELATIVE_PATH)

    @property
    def receipt_path(self) -> Path:
        return self.repo_root / Path(PHOBERT_RELEASE_RECEIPT_RELATIVE_PATH)


def _canonical(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        + b"\n"
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


def _controlled_config() -> ResumeControlledConfig:
    splits = (_split("train", "1"), _split("val", "2"))
    return ResumeControlledConfig(
        schema_version="phase40-resume-controlled-config-v1",
        experiment_identity=ExperimentIdentityEvidence(
            model_family=ModelFamily.PHOBERT,
            adaptation_mode=AdaptationMode.CLASSIFICATION_HEAD,
            run_kind=RunKind.FULL,
        ),
        model_id=PHOBERT_MODEL_ID,
        model_revision=PHOBERT_MODEL_REVISION,
        splits=splits,
        formatter_or_preprocessor_sha256=PHOBERT_PREPROCESSOR_SHA256,
        response_mask_or_preprocessor_version=PHOBERT_PREPROCESSOR_VERSION,
        label_order=tuple(LOCKED_RELEASE_LABELS),
        seed=42,
        data_seed=42,
        max_sequence_length=256,
        truncation_policy="right-token-truncate-record-v1",
        per_device_train_batch_size=4,
        gradient_accumulation_steps=2,
        world_size=1,
        effective_batch_size=8,
        num_train_epochs=3.0,
        max_optimizer_steps=10,
        gradient_checkpointing=False,
        lora_rank=None,
        lora_alpha=None,
        lora_dropout=None,
        lora_bias=None,
        target_modules=(),
        task_type="sequence-classification",
        optimizer=OptimizerControls(
            optimizer="adamw_torch",
            learning_rate=0.00002,
            weight_decay=0.01,
            lr_scheduler_type="linear",
            warmup_steps=0,
            warmup_ratio=0.1,
            max_grad_norm=1.0,
        ),
        precision=PrecisionControls(
            compute_dtype="float32",
            adapter_dtype="not-applicable",
            bf16=False,
            fp16=False,
            tf32=False,
        ),
        cadence=CadenceControls(
            logging_steps=1,
            evaluation_steps=1,
            save_steps=1,
            save_total_limit=2,
            generation_steps=(1,),
        ),
        decoder=None,
        checkpoint_selection_policy=PHOBERT_SELECTION_POLICY,
        checkpoint_selection_policy_version="phase40-checkpoint-selection-v1",
        snapshot_id_algorithm_version="phase40-snapshot-row-id-v1",
        quantization_proof=None,
        accelerator=AcceleratorIdentity(
            accelerator_type="cpu",
            accelerator_name="synthetic",
            compute_capability=None,
            total_memory_bytes=8_000_000_000,
        ),
        additional_controls=(
            NamedControl(name="dynamic_padding", value=True),
            NamedControl(name="local_files_only", value=True),
            NamedControl(name="segmenter_package", value=PHOBERT_SEGMENTER_PACKAGE),
            NamedControl(name="segmenter_version", value=PHOBERT_SEGMENTER_VERSION),
            NamedControl(name="trust_remote_code", value=False),
        ),
    )


def _decoder() -> DecoderContractEvidence:
    return DecoderContractEvidence(
        schema_version="phase40-qwen-decoder-v1",
        do_sample=False,
        num_return_sequences=1,
        max_new_tokens=256,
        output_schema_version="phase40-label-json-v1",
        decoder_version="phase40-deterministic-v1",
        generation_cadence="every-evaluation-and-final",
        raw_prediction_ordering_policy="canonical-validation-order-v1",
    )


def _qwen_proof(mode: AdaptationMode) -> QuantizationProofEvidence:
    qlora = mode == AdaptationMode.QLORA
    return QuantizationProofEvidence(
        requested_mode=mode,
        resolved_mode=(
            ResolvedQwenMode.FOUR_BIT_QLORA
            if qlora
            else ResolvedQwenMode.FULL_PRECISION_LORA
        ),
        bitsandbytes_version="0.50.1" if qlora else None,
        load_in_4bit=qlora,
        nf4=qlora,
        double_quantization=qlora,
        is_loaded_in_4bit=qlora,
        linear4bit_modules=28 if qlora else 0,
        kbit_preparation_applied=qlora,
        base_weights_frozen=True,
        adapter_only_trainables=True,
        adapter_trainable_count=7,
        backward_with_adapter_gradients=qlora,
        adapter_gradient_finite_count=7 if qlora else 0,
        adapter_gradient_nonzero_count=7 if qlora else 0,
    )


def _qwen_controlled_config(mode: AdaptationMode) -> ResumeControlledConfig:
    return ResumeControlledConfig(
        schema_version="phase40-resume-controlled-config-v1",
        experiment_identity=ExperimentIdentityEvidence(
            model_family=ModelFamily.QWEN,
            adaptation_mode=mode,
            run_kind=RunKind.FULL,
        ),
        model_id="Qwen/Qwen3-4B-Instruct-2507",
        model_revision="cdbee75f17c01a7cc42f958dc650907174af0554",
        splits=(_split("train", "1"), _split("val", "2")),
        formatter_or_preprocessor_sha256="a" * 64,
        response_mask_or_preprocessor_version="phase40-response-mask-v1",
        label_order=tuple(LOCKED_RELEASE_LABELS),
        seed=42,
        data_seed=42,
        max_sequence_length=256,
        truncation_policy="right-token-truncate-record-v1",
        per_device_train_batch_size=1,
        gradient_accumulation_steps=8,
        world_size=1,
        effective_batch_size=8,
        num_train_epochs=3.0,
        max_optimizer_steps=10,
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
            logging_steps=1,
            evaluation_steps=1,
            save_steps=1,
            save_total_limit=2,
            generation_steps=(1,),
        ),
        decoder=_decoder(),
        checkpoint_selection_policy="safety-floor-then-macro-f1",
        checkpoint_selection_policy_version="phase40-checkpoint-selection-v1",
        snapshot_id_algorithm_version="phase40-snapshot-row-id-v1",
        quantization_proof=_qwen_proof(mode),
        accelerator=AcceleratorIdentity(
            accelerator_type="cuda",
            accelerator_name="synthetic",
            compute_capability="8.9",
            total_memory_bytes=8_000_000_000,
        ),
        additional_controls=(),
    )


def _requested_template(config: ResumeControlledConfig) -> RequestedControlTemplate:
    payload = config.model_dump(mode="json")
    payload.pop("accelerator")
    return RequestedControlTemplate(controls_without_accelerator=payload)


def _event(sequence: int, kind: RunEventKind, values: dict[str, object]) -> RunEvent:
    return RunEvent(
        schema_version="phase40-run-event-v1",
        sequence_id=sequence,
        event_kind=kind,
        timestamp_utc=datetime(2026, 8, 25, 9, 0, sequence, tzinfo=timezone.utc),
        optimizer_step=0 if sequence == 0 else 1,
        epoch=0.0 if sequence == 0 else 0.25,
        trainer_values=values,
        source_run_id=RUN_ID,
        run_kind=RunKind.FULL,
    )


def _artifact(
    run_root: Path,
    logical_name: str,
    role: str,
    relative_path: str,
) -> ArtifactEvidence:
    path = run_root / relative_path
    return ArtifactEvidence(
        logical_name=logical_name,
        role=role,
        relative_path=relative_path,
        kind="directory" if path.is_dir() else "file",
        sha256=build_model_checksum(path),
    )


def _renderer(data, options) -> bytes:
    return b"synthetic-png\0" + hashlib.sha256(
        data.canonical_bytes + options.sha256.encode("ascii")
    ).digest()


def _write_run(
    run_root: Path,
    base_payload: bytes,
    transfer_authority: TransferAuthorityEvidence,
    *,
    model_cache_hint: str | None = None,
    model_weight_payload: bytes = b"synthetic-classifier-weights",
    sanitized_argv: tuple[str, ...] = ("train", "--model-family=phobert"),
    trainer_cache_hint: str | None = None,
) -> Path:
    run_root.mkdir(parents=True)
    events_path = run_root / "events.jsonl"
    for event in (
        _event(0, RunEventKind.RUN_START, {"status": "started"}),
        _event(1, RunEventKind.TRAIN_LOG, {"loss": 0.75}),
        _event(2, RunEventKind.EVALUATION, {"eval_loss": 0.5}),
        _event(3, RunEventKind.CHECKPOINT, {"checkpoint_saved": True}),
        _event(4, RunEventKind.RUN_END, {"status": "completed"}),
    ):
        append_run_event(events_path, event)

    controlled = _controlled_config()
    (run_root / "resolved-config.json").write_text(
        controlled.model_dump_json(),
        encoding="utf-8",
    )
    trainer_state: dict[str, object] = {"epoch": 0.25, "global_step": 1}
    if trainer_cache_hint is not None:
        trainer_state["cache_hint"] = trainer_cache_hint
    (run_root / "trainer_state.json").write_text(
        json.dumps(trainer_state),
        encoding="utf-8",
    )
    (run_root / "predictions.jsonl").write_text(
        json.dumps({"validation_row_id": "fixture-1", "label": "benign"}) + "\n",
        encoding="utf-8",
    )
    (run_root / "validation-metrics.json").write_text(
        json.dumps({"checkpoint_step": 1, "macro_f1": 1.0}),
        encoding="utf-8",
    )
    (run_root / "preprocessing.json").write_text(
        json.dumps(
            {
                "preprocessor_sha256": PHOBERT_PREPROCESSOR_SHA256,
                "segmenter": PHOBERT_SEGMENTER_PACKAGE,
                "segmenter_version": PHOBERT_SEGMENTER_VERSION,
            }
        ),
        encoding="utf-8",
    )
    model_root = run_root / "adapter-or-model"
    model_root.mkdir()
    model_config: dict[str, object] = {
        "architectures": ["RobertaForSequenceClassification"],
        "num_labels": 4,
    }
    if model_cache_hint is not None:
        model_config["cache_hint"] = model_cache_hint
    (model_root / "config.json").write_text(
        json.dumps(model_config),
        encoding="utf-8",
    )
    (model_root / "model.safetensors").write_bytes(model_weight_payload)
    (model_root / PHOBERT_BASE_MODEL_MANIFEST_NAME).write_bytes(base_payload)

    graph = render_phase40_graphs(
        run_root,
        renderer=_renderer,
        renderer_name="synthetic-renderer",
        renderer_version="1.0",
        smoothing_window=2,
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
                _artifact(
                    run_root,
                    "model-artifact",
                    "model_artifact",
                    "adapter-or-model",
                ),
                _artifact(run_root, "predictions", "predictions", "predictions.jsonl"),
                _artifact(
                    run_root,
                    "preprocessing",
                    "preprocessing",
                    "preprocessing.json",
                ),
                _artifact(
                    run_root,
                    "resolved-config",
                    "resolved_config",
                    "resolved-config.json",
                ),
                _artifact(
                    run_root,
                    "trainer-state",
                    "trainer_state",
                    "trainer_state.json",
                ),
                _artifact(
                    run_root,
                    "validation-metrics",
                    "metrics",
                    "validation-metrics.json",
                ),
            ),
            key=lambda item: item.logical_name,
        )
    )
    predictions_sha = next(item.sha256 for item in artifacts if item.role == "predictions")
    metrics_sha = next(item.sha256 for item in artifacts if item.role == "metrics")
    checkpoint = ValidationCheckpointEvidence(
        optimizer_step=1,
        artifact_identity=MODEL_IDENTITY,
        predictions_sha256=predictions_sha,
        metrics_sha256=metrics_sha,
        macro_f1=1.0,
        safety_gate_passed=True,
        invalid_output_count=0,
    )
    evidence = RunEvidence(
        schema_version="phase40-run-evidence-v1",
        run_id=RUN_ID,
        run_kind=RunKind.FULL,
        experiment_identity=controlled.experiment_identity,
        model_id=controlled.model_id,
        model_revision=controlled.model_revision,
        splits=controlled.splits,
        seed=controlled.seed,
        data_seed=controlled.data_seed,
        resolved_config_sha256=next(
            item.sha256 for item in artifacts if item.role == "resolved_config"
        ),
        resume_digest=compute_resume_digest(controlled),
        prompt_or_preprocessor_sha256=PHOBERT_PREPROCESSOR_SHA256,
        decoder_contract=None,
        decoder_contract_sha256=None,
        sanitized_argv=sanitized_argv,
        package_versions={"torch": "synthetic", "transformers": "synthetic"},
        hardware=RuntimeHardwareEvidence(
            python_version="3.13.7",
            platform="Windows-11",
            cuda_version=None,
            cudnn_version=None,
            gpu_name=None,
            gpu_compute_capability=None,
            gpu_total_memory_bytes=None,
            bf16_enabled=False,
            fp16_enabled=False,
            tf32_enabled=False,
        ),
        quantization=None,
        peak_allocated_bytes=100,
        peak_reserved_bytes=200,
        steady_step_seconds_median=0.25,
        validation_metrics={"macro_f1": 1.0},
        validation_checkpoints=(checkpoint,),
        selected_checkpoint=SelectedCheckpointEvidence(
            optimizer_step=1,
            artifact_identity=MODEL_IDENTITY,
            safety_gate_passed=True,
            rationale="Passed every safety floor and maximized macro F1.",
        ),
        artifacts=artifacts,
        artifact_sha256={item.logical_name: item.sha256 for item in artifacts},
        graph_provenance=(graph.as_evidence(),),
        transfer_authority=transfer_authority,
        status=EvidenceStatus.COMPLETE,
        comparison_eligible=True,
        failure_reason=None,
    )
    return finalize_run_evidence(run_root, evidence)


def _write_upstream_authorities(repo_root: Path) -> RunRequest:
    data_members = (
        InputDataMember(
            logical_name="train",
            member_name="train.jsonl",
            records=4,
            bytes=256,
            sha256="1" * 64,
            crc32="1" * 8,
            ordered_row_ids_sha256="f" * 64,
        ),
        InputDataMember(
            logical_name="val",
            member_name="val.jsonl",
            records=4,
            bytes=256,
            sha256="2" * 64,
            crc32="2" * 8,
            ordered_row_ids_sha256="f" * 64,
        ),
    )
    input_bundle = InputBundleReference(
        archive_sha256="8" * 64,
        manifest_sha256="9" * 64,
        data_members=data_members,
        phase39_data_contract_sha256="a" * 64,
        held_out_opaque=HeldOutIdentity(
            path="opaque/held-out.jsonl",
            records=8,
            bytes=512,
            sha256="e" * 64,
            evaluation_phase=41,
            touch_policy="opaque-until-phase41",
        ),
    )
    source_file = SourceInventoryEntry(
        path="src/synthetic.py",
        bytes=1,
        sha256="4" * 64,
    )
    source_bundle = SourceBundleReference(
        archive_sha256="6" * 64,
        inventory_sha256="7" * 64,
        files=(source_file,),
    )
    identities = (
        FullRunRequestIdentity(
            run_id="qwen-lora",
            model_family=ModelFamily.QWEN,
            adaptation_mode=AdaptationMode.LORA,
            returned_root=FIXED_RETURNED_ROOTS[0],
        ),
        FullRunRequestIdentity(
            run_id="qwen-qlora",
            model_family=ModelFamily.QWEN,
            adaptation_mode=AdaptationMode.QLORA,
            returned_root=FIXED_RETURNED_ROOTS[1],
        ),
        FullRunRequestIdentity(
            run_id=RUN_ID,
            model_family=ModelFamily.PHOBERT,
            adaptation_mode=AdaptationMode.CLASSIFICATION_HEAD,
            returned_root=FIXED_RETURNED_ROOTS[2],
        ),
    )
    configs = {
        "qwen-lora": _qwen_controlled_config(AdaptationMode.LORA),
        "qwen-qlora": _qwen_controlled_config(AdaptationMode.QLORA),
        RUN_ID: _controlled_config(),
    }
    templates = {
        run_id: _requested_template(config) for run_id, config in configs.items()
    }
    request = RunRequest(
        runs=identities,
        source_bundle=source_bundle,
        input_bundle=input_bundle,
        package_candidates=PACKAGE_CANDIDATES,
        expected_bundle_files=REQUIRED_FULL_BUNDLE_FILES,
        control_template_by_run=templates,
        control_template_digest_by_run={
            run_id: template.sha256 for run_id, template in templates.items()
        },
        no_held_out_boundary=True,
    )
    request_payload = _canonical(request.model_dump(mode="json"))
    request_path = repo_root / "data" / "models" / "phase40" / "full-run-request.json"
    request_path.write_bytes(request_payload)

    probe = LoraProbeAuthority(
        root=FIXED_LORA_PROBE_ROOT,
        artifacts=tuple(
            ProbeArtifactIdentity(
                relative_path=name,
                bytes=1,
                sha256=hashlib.sha256(name.encode("utf-8")).hexdigest(),
            )
            for name in FIXED_LORA_PROBE_FILES
        ),
    )
    finalizer_files = tuple(
        SourceInventoryEntry(
            path=name,
            bytes=1,
            sha256=hashlib.sha256(name.encode("utf-8")).hexdigest(),
        )
        for name in PHASE40_COMPARISON_FINALIZER_SOURCE_ALLOWLIST
    )
    finalizer = ComparisonFinalizerAuthority(
        files=finalizer_files,
        source_tree_sha256=hashlib.sha256(
            b"phase40-comparison-finalizer-source-v1\0"
            + _canonical([item.model_dump(mode="json") for item in finalizer_files])
        ).hexdigest(),
    )
    amendment = Phase40ScopeAmendment(
        original_run_request_sha256=hashlib.sha256(request_payload).hexdigest(),
        active_full_run_ids=("qwen-qlora", RUN_ID),
        active_returned_roots=FIXED_ACTIVE_RETURNED_ROOTS,
        waived_full_run_id="qwen-lora",
        lora_probe_authority=probe,
        comparison_finalizer_authority=finalizer,
        quality_model_run_ids=("qwen-qlora", RUN_ID),
        review_model_run_ids=("qwen-qlora", RUN_ID),
    )
    amendment_path = (
        repo_root
        / "data"
        / "models"
        / "phase40"
        / "two-full-model-scope-amendment.json"
    )
    amendment_path.write_bytes(_canonical(amendment.model_dump(mode="json")))
    return request


def _fixture(
    tmp_path: Path,
    name: str = "fixture",
    *,
    evidence_sanitized_argv: tuple[str, ...] = (
        "train",
        "--model-family=phobert",
    ),
    leaked_metadata_target: str | None = None,
    model_weight_payload: bytes = b"synthetic-classifier-weights",
) -> ReleaseFixture:
    root = tmp_path / name
    repo_root = root / "repo"
    transfer_root = root / "transfer"
    run_root = root / "sources" / "run"
    tokenizer_root = root / "sources" / "tokenizer"
    base_provenance_path = root / "sources" / "base-provenance.json"
    (repo_root / "data" / "models" / "phase40").mkdir(parents=True)
    (transfer_root / "data" / "models" / "phase40" / "inference").mkdir(parents=True)
    tokenizer_root.mkdir(parents=True)
    leaked_path = "--cache-dir=D:\\Users\\fixture\\private-cache"
    tokenizer_config: dict[str, object] = {
        "model_max_length": 256,
        "truncation_side": "right",
    }
    if leaked_metadata_target == "tokenizer":
        tokenizer_config["cache_hint"] = leaked_path
    (tokenizer_root / "tokenizer_config.json").write_text(
        json.dumps(tokenizer_config),
        encoding="utf-8",
    )
    (tokenizer_root / "vocab.txt").write_text("<s>\n</s>\nxin\nchao\n", encoding="utf-8")
    base = PhoBertBaseModelProvenance(
        schema_version=PHOBERT_BASE_PROVENANCE_SCHEMA,
        model_id=PHOBERT_MODEL_ID,
        model_revision=PHOBERT_MODEL_REVISION,
        local_path_sha256="c" * 64,
        content_sha256="d" * 64,
        file_count=4,
        total_bytes=1024,
    )
    base_payload = _canonical(base.model_dump(mode="json"))
    base_provenance_path.write_bytes(base_payload)
    request = _write_upstream_authorities(repo_root)
    _write_run(
        run_root,
        base_payload,
        transfer_authority_from_request(request),
        model_cache_hint=(
            leaked_path if leaked_metadata_target == "model" else None
        ),
        model_weight_payload=model_weight_payload,
        sanitized_argv=evidence_sanitized_argv,
        trainer_cache_hint=(
            leaked_path if leaked_metadata_target == "trainer" else None
        ),
    )
    return ReleaseFixture(
        repo_root=repo_root,
        transfer_root=transfer_root,
        run_root=run_root,
        tokenizer_root=tokenizer_root,
        base_provenance_path=base_provenance_path,
    )


def _build(fixture: ReleaseFixture):
    return build_phobert_release_bundle(
        repo_root=fixture.repo_root,
        transfer_root=fixture.transfer_root,
        run_evidence_path=fixture.run_root / "run-evidence.json",
        selected_model_root=fixture.run_root / "adapter-or-model",
        tokenizer_root=fixture.tokenizer_root,
        base_provenance_path=fixture.base_provenance_path,
    )


def test_builds_fixed_external_bundle_and_portable_commit_receipt(tmp_path):
    fixture = _fixture(tmp_path)
    before_run = build_model_checksum(fixture.run_root)
    before_tokenizer = build_model_checksum(fixture.tokenizer_root)

    built = _build(fixture)
    verified = verify_phobert_release_bundle(
        repo_root=fixture.repo_root,
        transfer_root=fixture.transfer_root,
    )

    assert built == verified
    assert built.root == fixture.bundle_root
    assert built.receipt_path == fixture.receipt_path
    assert build_model_checksum(fixture.run_root) == before_run
    assert build_model_checksum(fixture.tokenizer_root) == before_tokenizer
    assert (built.root / PHOBERT_RELEASE_MODEL_ROOT).is_dir()
    assert (built.root / PHOBERT_RELEASE_TOKENIZER_ROOT).is_dir()
    assert built.manifest.selected_model["checkpoint_identity"] == MODEL_IDENTITY
    assert built.manifest.run["selected_optimizer_step"] == 1
    assert built.manifest.run["global_optimizer_step"] == 1
    assert built.receipt.bundle_root_sha256 == built.bundle_root_sha256
    assert built.receipt.tokenizer_sha256 == built.manifest.tokenizer_tree.content_sha256
    request_path = fixture.repo_root / "data/models/phase40/full-run-request.json"
    amendment_path = (
        fixture.repo_root
        / "data/models/phase40/two-full-model-scope-amendment.json"
    )
    assert built.receipt.upstream == built.manifest.upstream
    assert built.receipt.upstream["original_run_request_sha256"] == hashlib.sha256(
        request_path.read_bytes()
    ).hexdigest()
    assert built.receipt.upstream["scope_amendment_sha256"] == hashlib.sha256(
        amendment_path.read_bytes()
    ).hexdigest()
    receipt_payload = fixture.receipt_path.read_bytes()
    assert os.fspath(fixture.repo_root).encode() not in receipt_payload
    assert os.fspath(fixture.transfer_root).encode() not in receipt_payload


def test_release_bytes_are_deterministic_across_absolute_roots(tmp_path):
    first = _fixture(tmp_path, "first")
    second = _fixture(tmp_path, "second")

    first_result = _build(first)
    second_result = _build(second)

    assert first_result.manifest == second_result.manifest
    assert first_result.manifest_sha256 == second_result.manifest_sha256
    assert first_result.bundle_root_sha256 == second_result.bundle_root_sha256
    assert first_result.receipt == second_result.receipt
    assert first.receipt_path.read_bytes() == second.receipt_path.read_bytes()


def test_fixed_loaders_do_not_accept_alternate_authority_paths(tmp_path):
    fixture = _fixture(tmp_path)
    built = _build(fixture)

    assert load_phobert_release_manifest(
        transfer_root=fixture.transfer_root
    ) == built.manifest
    assert load_phobert_release_receipt(repo_root=fixture.repo_root) == built.receipt
    alternate = fixture.repo_root / "alternate.json"
    alternate.write_bytes(fixture.receipt_path.read_bytes())

    fixture.receipt_path.unlink()
    with pytest.raises(PhoBertReleaseError, match="missing"):
        load_phobert_release_receipt(repo_root=fixture.repo_root)


def test_build_is_write_once_for_bundle_and_receipt(tmp_path):
    fixture = _fixture(tmp_path)
    _build(fixture)

    with pytest.raises(PhoBertReleaseError, match="already exists"):
        _build(fixture)


def test_build_and_verify_reject_stale_canonical_upstream(tmp_path):
    before_build = _fixture(tmp_path, "before-build")
    amendment_path = (
        before_build.repo_root
        / "data/models/phase40/two-full-model-scope-amendment.json"
    )
    amendment = json.loads(amendment_path.read_text(encoding="utf-8"))
    amendment["original_run_request_sha256"] = "0" * 64
    amendment_path.write_bytes(_canonical(amendment))
    with pytest.raises(PhoBertReleaseError, match="does not bind"):
        _build(before_build)

    after_build = _fixture(tmp_path, "after-build")
    _build(after_build)
    request_path = after_build.repo_root / "data/models/phase40/full-run-request.json"
    request_path.write_bytes(request_path.read_bytes() + b"\n")
    with pytest.raises(PhoBertReleaseError, match="canonical"):
        verify_phobert_release_bundle(
            repo_root=after_build.repo_root,
            transfer_root=after_build.transfer_root,
        )


@pytest.mark.parametrize(
    "target",
    ("tokenizer", "model", "manifest", "receipt"),
)
def test_verification_rejects_every_published_byte_drift(tmp_path, target):
    fixture = _fixture(tmp_path)
    _build(fixture)
    paths = {
        "tokenizer": fixture.bundle_root / PHOBERT_RELEASE_TOKENIZER_ROOT / "vocab.txt",
        "model": fixture.bundle_root / PHOBERT_RELEASE_MODEL_ROOT / "model.safetensors",
        "manifest": fixture.bundle_root / PHOBERT_RELEASE_MANIFEST_NAME,
        "receipt": fixture.receipt_path,
    }
    with paths[target].open("ab") as handle:
        handle.write(b"drift")

    with pytest.raises((PhoBertReleaseError, OSError)):
        verify_phobert_release_bundle(
            repo_root=fixture.repo_root,
            transfer_root=fixture.transfer_root,
        )


def test_verification_rejects_added_or_deleted_bundle_members(tmp_path):
    added = _fixture(tmp_path, "added")
    _build(added)
    (added.bundle_root / PHOBERT_RELEASE_TOKENIZER_ROOT / "injected.py").write_text(
        "malicious = True",
        encoding="utf-8",
    )
    with pytest.raises(PhoBertReleaseError, match="inventory|hash"):
        verify_phobert_release_bundle(
            repo_root=added.repo_root,
            transfer_root=added.transfer_root,
        )

    deleted = _fixture(tmp_path, "deleted")
    _build(deleted)
    (deleted.bundle_root / PHOBERT_RELEASE_TOKENIZER_ROOT / "vocab.txt").unlink()
    with pytest.raises(PhoBertReleaseError):
        verify_phobert_release_bundle(
            repo_root=deleted.repo_root,
            transfer_root=deleted.transfer_root,
        )


def test_build_rejects_base_provenance_or_model_artifact_drift(tmp_path):
    base_drift = _fixture(tmp_path, "base-drift")
    base_drift.base_provenance_path.write_bytes(
        base_drift.base_provenance_path.read_bytes().replace(b'"dddd', b'"eeee', 1)
    )
    with pytest.raises(PhoBertReleaseError, match="differs"):
        _build(base_drift)

    model_drift = _fixture(tmp_path, "model-drift")
    (model_drift.run_root / "adapter-or-model" / "model.safetensors").write_bytes(
        b"different-weights"
    )
    with pytest.raises((PhoBertReleaseError, RuntimeError), match="SHA-256|hash|artifact"):
        _build(model_drift)


def test_build_rejects_noncanonical_or_wrong_source_paths(tmp_path):
    fixture = _fixture(tmp_path)
    with pytest.raises(PhoBertReleaseError, match="canonical"):
        build_phobert_release_bundle(
            repo_root=fixture.repo_root / ".." / "repo",
            transfer_root=fixture.transfer_root,
            run_evidence_path=fixture.run_root / "run-evidence.json",
            selected_model_root=fixture.run_root / "adapter-or-model",
            tokenizer_root=fixture.tokenizer_root,
            base_provenance_path=fixture.base_provenance_path,
        )

    wrong_model = fixture.run_root.parent / "wrong-model"
    wrong_model.mkdir()
    (wrong_model / "model.safetensors").write_bytes(b"wrong")
    with pytest.raises(PhoBertReleaseError, match="does not match"):
        build_phobert_release_bundle(
            repo_root=fixture.repo_root,
            transfer_root=fixture.transfer_root,
            run_evidence_path=fixture.run_root / "run-evidence.json",
            selected_model_root=wrong_model,
            tokenizer_root=fixture.tokenizer_root,
            base_provenance_path=fixture.base_provenance_path,
        )


def test_build_rejects_symlink_or_reparse_tokenizer_root(tmp_path, monkeypatch):
    fixture = _fixture(tmp_path)
    link = fixture.tokenizer_root.parent / "tokenizer-link"
    try:
        link.symlink_to(fixture.tokenizer_root, target_is_directory=True)
    except OSError:
        pytest.skip("Windows test token cannot create a directory symlink")

    link_key = os.path.normcase(os.path.abspath(os.fspath(link)))

    def guard_probe(original):
        def guarded(path: Path, *args, **kwargs):
            if os.path.normcase(os.path.abspath(os.fspath(path))) == link_key:
                raise AssertionError(
                    "redirecting tokenizer root was probed before its lease"
                )
            return original(path, *args, **kwargs)

        return guarded

    monkeypatch.setattr(Path, "is_dir", guard_probe(Path.is_dir))
    monkeypatch.setattr(Path, "is_file", guard_probe(Path.is_file))
    monkeypatch.setattr(Path, "exists", guard_probe(Path.exists))

    with pytest.raises((PhoBertReleaseError, ReleaseAuthorityError, OSError)):
        build_phobert_release_bundle(
            repo_root=fixture.repo_root,
            transfer_root=fixture.transfer_root,
            run_evidence_path=fixture.run_root / "run-evidence.json",
            selected_model_root=fixture.run_root / "adapter-or-model",
            tokenizer_root=link,
            base_provenance_path=fixture.base_provenance_path,
        )


def test_live_source_leases_block_mutation_during_copy(tmp_path, monkeypatch):
    fixture = _fixture(tmp_path)
    original = release_module._copy_tree_from_authority
    attacks: list[str] = []

    def hostile_copy(source_root, destination_root, authority, source_lease):
        if source_root == fixture.tokenizer_root:
            original_payload = (source_root / "vocab.txt").read_bytes()
            try:
                (source_root / "vocab.txt").write_bytes(b"x" * len(original_payload))
            except PermissionError:
                attacks.append("blocked")
            else:
                attacks.append("accepted")
        return original(source_root, destination_root, authority, source_lease)

    monkeypatch.setattr(release_module, "_copy_tree_from_authority", hostile_copy)
    built = _build(fixture)

    assert attacks == ["blocked"]
    assert (
        built.root / PHOBERT_RELEASE_TOKENIZER_ROOT / "vocab.txt"
    ).read_text(encoding="utf-8") == "<s>\n</s>\nxin\nchao\n"


def test_final_bundle_lease_blocks_same_size_mutation_before_receipt_publish(
    tmp_path,
    monkeypatch,
):
    fixture = _fixture(tmp_path)
    original_move = release_module._move_path_write_through
    attacks: list[str] = []

    def hostile_move(source: Path, destination: Path) -> None:
        if destination == fixture.receipt_path:
            model_path = (
                fixture.bundle_root
                / PHOBERT_RELEASE_MODEL_ROOT
                / "model.safetensors"
            )
            original_payload = model_path.read_bytes()
            try:
                with model_path.open("r+b") as handle:
                    handle.write(b"x" * len(original_payload))
                    handle.flush()
                    os.fsync(handle.fileno())
            except OSError as exc:
                if (
                    getattr(exc, "winerror", None) not in {5, 32, 33}
                    and getattr(exc, "errno", None) != 13
                ):
                    raise
                attacks.append("blocked")
            else:
                attacks.append("accepted")
        original_move(source, destination)

    monkeypatch.setattr(release_module, "_move_path_write_through", hostile_move)
    built = _build(fixture)
    verified = verify_phobert_release_bundle(
        repo_root=fixture.repo_root,
        transfer_root=fixture.transfer_root,
    )

    assert attacks == ["blocked"]
    assert verified == built


@pytest.mark.parametrize("metadata_target", ("model", "tokenizer", "trainer"))
def test_build_rejects_absolute_paths_in_copied_portable_metadata(
    tmp_path,
    metadata_target,
):
    fixture = _fixture(
        tmp_path,
        leaked_metadata_target=metadata_target,
    )

    with pytest.raises(PhoBertReleaseError, match="absolute host path"):
        _build(fixture)


@pytest.mark.parametrize(
    "metadata_payload",
    (
        r'{"cache_hint":"\u002fhome\u002freviewer\u002fcache"}',
        r'{"\u002froot\u002fprivate-key":true}',
        '{"cache_hint":"/root/private-cache"}',
        '{"cache_hint":"--cache-dir=/opt/private-cache"}',
        '{"cache_hint":"file:///root/private-cache"}',
        '{"cache_hint":"--cache-uri=file://host/private-cache"}',
    ),
)
def test_build_rejects_decoded_json_and_all_posix_absolute_paths(
    tmp_path,
    metadata_payload,
):
    fixture = _fixture(tmp_path)
    (fixture.tokenizer_root / "tokenizer_config.json").write_text(
        metadata_payload,
        encoding="utf-8",
    )

    with pytest.raises(PhoBertReleaseError, match="absolute host path"):
        _build(fixture)


def test_non_file_urls_remain_portable_metadata(tmp_path):
    fixture = _fixture(tmp_path)
    (fixture.tokenizer_root / "tokenizer_config.json").write_text(
        json.dumps(
            {
                "documentation": "https://example.invalid/tokenizer/config",
                "registry": "s3://portable-bucket/model",
            }
        ),
        encoding="utf-8",
    )

    built = _build(fixture)

    assert built.root == fixture.bundle_root


def test_build_rejects_absolute_path_in_safetensors_json_header(tmp_path):
    header = b'{"__metadata__":{"cache_hint":"/root/private-cache"}}'
    safetensors = len(header).to_bytes(8, "little") + header + b"tensor-bytes"
    fixture = _fixture(tmp_path, model_weight_payload=safetensors)

    with pytest.raises(PhoBertReleaseError, match="absolute host path"):
        _build(fixture)


def test_tokenizer_lexical_assets_preserve_ordinary_path_like_tokens(tmp_path):
    fixture = _fixture(tmp_path)
    lexical_tokens = (
        "<s>\n</s>\n/\n/root\nfile:///root\n"
        "D:\\Users\\literal-token\nhttps://example.invalid/token\n"
    )
    (fixture.tokenizer_root / "vocab.txt").write_text(
        lexical_tokens,
        encoding="utf-8",
    )
    (fixture.tokenizer_root / "merges.txt").write_text(
        "/ root\nfile: ///root\n",
        encoding="utf-8",
    )

    built = _build(fixture)

    assert (
        built.root / PHOBERT_RELEASE_TOKENIZER_ROOT / "vocab.txt"
    ).read_text(encoding="utf-8") == lexical_tokens


def test_mixed_tokenizer_json_exempts_only_schema_lexical_subtrees(tmp_path):
    lexical_payload: dict[str, object] = {
        "version": "1.0",
        "added_tokens": [
            {"id": 4, "content": "/", "special": False},
            {"id": 5, "content": "file:///root", "special": False},
        ],
        "model": {
            "type": "BPE",
            "vocab": {
                "/root": 0,
                "file:///root": 1,
                "D:\\Users\\literal-token": 2,
            },
            "merges": ["/ root", "file: ///root"],
        },
        "post_processor": {
            "special_tokens": {
                "/root": {
                    "id": "/root",
                    "ids": [3],
                    "tokens": ["file:///root"],
                }
            }
        },
    }
    safe = _fixture(tmp_path, "mixed-safe")
    (safe.tokenizer_root / "tokenizer.json").write_text(
        json.dumps(lexical_payload),
        encoding="utf-8",
    )

    safe_bundle = _build(safe)

    assert safe_bundle.root == safe.bundle_root

    hostile = _fixture(tmp_path, "mixed-hostile")
    hostile_payload = dict(lexical_payload)
    hostile_payload["cache_hint"] = "file:///root/private-cache"
    (hostile.tokenizer_root / "tokenizer.json").write_text(
        json.dumps(hostile_payload),
        encoding="utf-8",
    )

    with pytest.raises(PhoBertReleaseError, match="absolute host path"):
        _build(hostile)

    nested_hostile = _fixture(tmp_path, "mixed-nested-hostile")
    nested_payload = json.loads(json.dumps(lexical_payload))
    nested_payload["post_processor"]["special_tokens"]["/root"][
        "cache_hint"
    ] = "file:///root/private-cache"
    (nested_hostile.tokenizer_root / "tokenizer.json").write_text(
        json.dumps(nested_payload),
        encoding="utf-8",
    )

    with pytest.raises(PhoBertReleaseError, match="absolute host path"):
        _build(nested_hostile)


def test_build_rejects_decoded_absolute_path_in_jsonl_metadata(tmp_path):
    fixture = _fixture(tmp_path)
    (fixture.tokenizer_root / "metadata.jsonl").write_text(
        '{"kind":"safe"}\n'
        r'{"cache_hint":"\u002froot\u002fprivate-cache"}'
        "\n",
        encoding="utf-8",
    )

    with pytest.raises(PhoBertReleaseError, match="absolute host path"):
        _build(fixture)


def test_run_evidence_path_exception_cannot_be_reused_in_sanitized_argv(tmp_path):
    fixture = _fixture(
        tmp_path,
        evidence_sanitized_argv=(
            "train",
            f"--cache-dir={FIXED_INPUT_DRIVE_PATH}",
        ),
    )

    with pytest.raises(PhoBertReleaseError, match="absolute host path"):
        _build(fixture)


def test_opaque_model_weights_do_not_trigger_text_path_scanner(tmp_path):
    opaque_weights = (
        b"\x00\xffopaque-prefix\x80"
        b"D:\\Users\\fixture\\not-text-metadata\x00"
        b"/root/arbitrary-weight-bytes\xfe"
    )
    fixture = _fixture(tmp_path, model_weight_payload=opaque_weights)

    built = _build(fixture)
    verified = verify_phobert_release_bundle(
        repo_root=fixture.repo_root,
        transfer_root=fixture.transfer_root,
    )

    assert verified == built
    assert (
        fixture.bundle_root / PHOBERT_RELEASE_MODEL_ROOT / "model.safetensors"
    ).read_bytes() == opaque_weights


def test_public_entrypoints_lease_redirecting_roots_before_path_probes(
    tmp_path,
    monkeypatch,
):
    fixture = _fixture(tmp_path)
    _build(fixture)
    transfer_alias = tmp_path / "transfer-alias"
    repo_alias = tmp_path / "repo-alias"
    try:
        transfer_alias.symlink_to(fixture.transfer_root, target_is_directory=True)
        repo_alias.symlink_to(fixture.repo_root, target_is_directory=True)
    except OSError:
        pytest.skip("Windows test token cannot create directory symlinks")

    guarded_roots = tuple(
        os.path.normcase(os.path.abspath(os.fspath(path)))
        for path in (transfer_alias, repo_alias)
    )

    def guard_probe(original):
        def guarded(path: Path, *args, **kwargs):
            key = os.path.normcase(os.path.abspath(os.fspath(path)))
            if any(
                key == root or key.startswith(root + os.sep)
                for root in guarded_roots
            ):
                raise AssertionError("redirecting caller path was probed before its lease")
            return original(path, *args, **kwargs)

        return guarded

    monkeypatch.setattr(Path, "is_dir", guard_probe(Path.is_dir))
    monkeypatch.setattr(Path, "is_file", guard_probe(Path.is_file))
    monkeypatch.setattr(Path, "exists", guard_probe(Path.exists))

    with pytest.raises((PhoBertReleaseError, ReleaseAuthorityError, OSError)):
        verify_phobert_release_bundle(
            repo_root=fixture.repo_root,
            transfer_root=transfer_alias,
        )
    with pytest.raises((PhoBertReleaseError, ReleaseAuthorityError, OSError)):
        load_phobert_release_manifest(transfer_root=transfer_alias)
    with pytest.raises((PhoBertReleaseError, ReleaseAuthorityError, OSError)):
        load_phobert_release_receipt(repo_root=repo_alias)


def test_copy_failure_never_publishes_bundle_or_commit_receipt(tmp_path, monkeypatch):
    fixture = _fixture(tmp_path)

    def fail_copy(*_args, **_kwargs):
        raise PhoBertReleaseError("synthetic copy failure")

    monkeypatch.setattr(release_module, "_copy_tree_from_authority", fail_copy)
    with pytest.raises(PhoBertReleaseError, match="synthetic copy failure"):
        _build(fixture)

    assert not fixture.bundle_root.exists()
    assert not fixture.receipt_path.exists()


def test_receipt_cannot_substitute_for_missing_fixed_bundle(tmp_path):
    fixture = _fixture(tmp_path)
    _build(fixture)
    moved = fixture.transfer_root / "elsewhere"
    fixture.bundle_root.rename(moved)

    with pytest.raises(PhoBertReleaseError, match="missing"):
        verify_phobert_release_bundle(
            repo_root=fixture.repo_root,
            transfer_root=fixture.transfer_root,
        )
