"""Fixture-only tests for Phase 40 source/data handoff and human review."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Callable

import pytest
from pydantic import ValidationError

from src.data_pipeline.schemas import DatasetRecord
from src.model_adaptation.phase40_contract import (
    CanonicalSnapshotRow,
    CanonicalSplitSnapshot,
    HeldOutIdentity,
    Phase40DataContract,
    SplitIdentity,
    derive_snapshot_row_id,
)
from src.model_adaptation.phase40_handoff import (
    FIXED_INPUT_REPOSITORY_PATH,
    FIXED_RUN_REQUEST_PATH,
    FIXED_RETURNED_ROOTS,
    PACKAGE_CANDIDATES,
    PINNED_PHOBERT_REVISION,
    PINNED_QWEN_REVISION,
    REQUIRED_FULL_BUNDLE_FILES,
    ColabOperatorReturn,
    ComparisonArtifacts,
    FullRunRequestIdentity,
    PackageDecision,
    RequestedControlTemplate,
    ReturnedBundleRoot,
    ReturnedGpuIdentity,
    ReviewQueueRow,
    ReviewerReturnRow,
    RunRequest,
    SelectedPredictionBundle,
    build_phase40_input_bundle,
    build_phase40_review_queue,
    build_phase40_source_bundle,
    finalize_phase40_comparison,
    finalize_phase40_human_review,
    freeze_phase40_run_request,
    load_frozen_phase40_run_request,
    verify_phase40_input_bundle,
    verify_phase40_review_queue,
    verify_phase40_source_bundle,
)
from src.model_adaptation.phase40_evidence import (
    AcceleratorIdentity,
    ArtifactEvidence,
    CadenceControls,
    CanonicalSplitEvidence,
    DecoderContractEvidence,
    EvidenceStatus,
    ExperimentIdentityEvidence,
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
from src.model_adaptation.phase40_metrics import (
    LABEL_ORDER,
    RISKY_RECALL_FLOORS,
    Phase40MetricResult,
    Phase40PredictionRow,
    evaluate_phase40_predictions,
    select_phase40_checkpoint,
)
from src.model_adaptation.phase40_modes import (
    AdaptationMode,
    ModelFamily,
    ResolvedQwenMode,
    RunKind,
)
from src.model_adaptation.registry import build_model_checksum


def _record(label: str, index: int, split_name: str) -> DatasetRecord:
    return DatasetRecord(
        text=f"Tin nhắn {split_name} số {index} cho nhãn {label}.",
        label=label,
        risk_tier="benign" if label == "benign" else "high-risk",
        suspicious_spans=[] if label == "benign" else [label],
        xai_explanation=f"Giải thích kiểm thử đủ dài cho {split_name} {index} và {label}.",
        source="synthetic_claude",
        seed_id=f"{split_name}-seed-{index}",
    )


def test_operator_and_reviewer_free_text_is_single_line() -> None:
    decision = PackageDecision(
        package="bitsandbytes==0.50.1",
        decision="reject",
        reason="không\n  chấp thuận\ttrên máy này",
    )
    review = ReviewerReturnRow(
        model_run_id="qwen-lora",
        validation_row_id="validation-row-1",
        decision="questioned",
        note_vi="cần\n  xem lại\tngữ cảnh",
    )

    assert decision.reason == "không chấp thuận trên máy này"
    assert review.note_vi == "cần xem lại ngữ cảnh"


def _snapshot(split_name: str, count: int) -> CanonicalSplitSnapshot:
    rows = []
    labels = [LABEL_ORDER[index % len(LABEL_ORDER)] for index in range(count)]
    for index, label in enumerate(labels):
        record = _record(label, index, split_name)
        record_bytes = record.model_dump_json().encode("utf-8")
        digest = hashlib.sha256(record_bytes).hexdigest()
        rows.append(
            CanonicalSnapshotRow(
                split_name=split_name,
                canonical_index=index,
                record_bytes=record_bytes,
                record=record,
                raw_message=record.text,
                source_row_sha256=digest,
                snapshot_row_id=derive_snapshot_row_id(split_name, index, digest),
            )
        )
    payload = b"\n".join(row.record_bytes for row in rows) + b"\n"
    identity = SplitIdentity(
        split_name,
        f"data/splits/{split_name}.jsonl",
        len(rows),
        len(payload),
        hashlib.sha256(payload).hexdigest(),
        tuple((label, labels.count(label)) for label in LABEL_ORDER),
    )
    return CanonicalSplitSnapshot(
        split_name,
        identity,
        payload,
        identity.sha256,
        tuple(rows),
    )


def _contract(*, train_count: int = 8, validation_count: int = 8) -> Phase40DataContract:
    train = _snapshot("train", train_count)
    val = _snapshot("val", validation_count)
    return Phase40DataContract(
        ordered_identities=(train.identity, val.identity),
        train_snapshot=train,
        validation_snapshot=val,
        held_out_test=HeldOutIdentity(
            path="data/splits/test.jsonl",
            records=220,
            bytes=12345,
            sha256="a" * 64,
            evaluation_phase=41,
            touch_policy="opaque until Phase 41",
        ),
    )


def test_input_bundle_is_byte_stable_exact_three_member_and_reconstructs_ids(tmp_path):
    repo = tmp_path / "repo"
    output = repo / FIXED_INPUT_REPOSITORY_PATH
    contract = _contract()

    first = build_phase40_input_bundle(contract, output)
    first_bytes = output.read_bytes()
    second = build_phase40_input_bundle(contract, output)
    assert output.read_bytes() == first_bytes
    assert second.reference == first.reference

    opened: list[str] = []

    def opener(archive, member_name):
        opened.append(member_name)
        return archive.open(member_name, "r")

    verified = verify_phase40_input_bundle(
        output,
        first.reference,
        repo_root=repo,
        member_opener=opener,
        materialize=False,
    )
    assert opened == ["train.jsonl", "val.jsonl"]
    assert verified.train_snapshot.whole_file_bytes == contract.train_snapshot.whole_file_bytes
    assert verified.validation_snapshot.validation_row_ids == contract.validation_snapshot.validation_row_ids
    assert verified.held_out_test == contract.held_out_test


def test_input_bundle_rejects_path_and_archive_mutation_before_data_member_open(tmp_path):
    repo = tmp_path / "repo"
    output = repo / FIXED_INPUT_REPOSITORY_PATH
    built = build_phase40_input_bundle(_contract(), output)
    opened: list[str] = []

    def opener(archive, member_name):
        opened.append(member_name)
        return archive.open(member_name, "r")

    with pytest.raises(ValueError, match="request-bound"):
        verify_phase40_input_bundle(
            tmp_path / "decoy.zip",
            built.reference,
            repo_root=repo,
            member_opener=opener,
            materialize=False,
        )
    assert opened == []

    output.write_bytes(output.read_bytes() + b"mutation")
    with pytest.raises(ValueError, match="archive SHA-256"):
        verify_phase40_input_bundle(
            output,
            built.reference,
            repo_root=repo,
            member_opener=opener,
            materialize=False,
        )
    assert opened == []


def test_input_bundle_rejects_request_rehashed_member_mutation_before_data_open(tmp_path):
    import io
    import zipfile
    import src.model_adaptation.phase40_handoff as handoff

    repo = tmp_path / "repo"
    output = repo / FIXED_INPUT_REPOSITORY_PATH
    built = build_phase40_input_bundle(_contract(), output)
    with zipfile.ZipFile(io.BytesIO(output.read_bytes()), "r") as archive:
        manifest = archive.read("phase40-input-manifest.json")
        train = bytearray(archive.read("train.jsonl"))
        val = archive.read("val.jsonl")
    train[0] ^= 1
    mutated = handoff._deterministic_zip(
        (
            ("phase40-input-manifest.json", manifest),
            ("train.jsonl", bytes(train)),
            ("val.jsonl", val),
        )
    )
    output.write_bytes(mutated)
    mutated_reference = built.reference.model_copy(
        update={"archive_sha256": hashlib.sha256(mutated).hexdigest()}
    )
    opened: list[str] = []

    def opener(archive, member_name):
        opened.append(member_name)
        return archive.open(member_name, "r")

    with pytest.raises(ValueError, match="central-directory identity"):
        verify_phase40_input_bundle(
            output,
            mutated_reference,
            repo_root=repo,
            member_opener=opener,
            materialize=False,
        )
    assert opened == []

def test_source_bundle_is_deterministic_and_verifies_inventory(tmp_path, monkeypatch):
    import src.model_adaptation.phase40_handoff as handoff

    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "src" / "a.py").write_text("A = 1\n", encoding="utf-8")
    (repo / "src" / "b.py").write_text("B = 2\n", encoding="utf-8")
    monkeypatch.setattr(handoff, "PHASE40_SOURCE_ALLOWLIST", ("src/b.py", "src/a.py"))
    output = repo / "data/models/phase40/source"

    first = build_phase40_source_bundle(repo, output)
    archive_bytes = first.archive_path.read_bytes()
    inventory_bytes = first.inventory_path.read_bytes()
    second = build_phase40_source_bundle(repo, output)
    assert second.archive_path.read_bytes() == archive_bytes
    assert second.inventory_path.read_bytes() == inventory_bytes
    assert second.reference == first.reference
    assert [entry.path for entry in verify_phase40_source_bundle(
        repo_root=repo,
        reference=first.reference,
    ).files] == ["src/a.py", "src/b.py"]

    (repo / "src" / "a.py").write_text("A = 9\n", encoding="utf-8")
    changed = build_phase40_source_bundle(repo, output)
    assert changed.reference.archive_sha256 != first.reference.archive_sha256


def test_source_bundle_is_import_closed_for_operator_and_both_training_backends(tmp_path):
    import os
    import shutil
    import subprocess
    import sys
    import zipfile

    import src.model_adaptation.phase40_handoff as handoff

    project_root = Path(__file__).resolve().parents[2]
    repo = tmp_path / "repo"
    for relative_name in handoff.PHASE40_SOURCE_ALLOWLIST:
        source = project_root / relative_name
        assert source.is_file(), f"allowlisted Phase 40 source is missing: {relative_name}"
        destination = repo / relative_name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)

    built = build_phase40_source_bundle(repo, repo / "data/models/phase40/source")
    verify_phase40_source_bundle(repo_root=repo, reference=built.reference)
    extracted = tmp_path / "extracted"
    with zipfile.ZipFile(built.archive_path, "r") as archive:
        archive.extractall(extracted)

    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(extracted)
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.model_adaptation.phase40_operator",
            "--help",
        ],
        cwd=extracted,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
        check=False,
        timeout=30,
    )
    assert completed.returncode == 0, completed.stderr
    assert "phase40-train-qwen" in completed.stdout
    assert "phase40-train-phobert" in completed.stdout

    backend_import = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import src.model_adaptation.training; "
                "import src.model_adaptation.phobert_training; "
                "print('phase40-backends-imported')"
            ),
        ],
        cwd=extracted,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
        check=False,
        timeout=30,
    )
    assert backend_import.returncode == 0, backend_import.stderr
    assert backend_import.stdout.strip() == "phase40-backends-imported"


def _prediction_bundle(
    contract: Phase40DataContract,
    run_id: str,
    predicted: list[str],
) -> SelectedPredictionBundle:
    identity = f"adapter-state-sha256:{hashlib.sha256(run_id.encode()).hexdigest()}"
    rows = tuple(
        Phase40PredictionRow.from_raw(
            validation_row_id=source.validation_row_id,
            sequence_index=index,
            gold_label=source.record.label,
            raw_prediction=(
                "not-json"
                if label == "invalid_output"
                else json.dumps({"label": label})
            ),
            artifact_identity=identity,
            checkpoint_step=50,
        )
        for index, (source, label) in enumerate(
            zip(contract.validation_snapshot.rows, predicted, strict=True)
        )
    )
    return SelectedPredictionBundle(
        model_run_id=run_id,
        model_artifact_identity=f"model:{run_id}",
        selected_checkpoint_identity=identity,
        predictions=rows,
    )


def test_review_queue_covers_all_slices_binds_messages_and_deduplicates(tmp_path):
    contract = _contract()
    gold = [row.record.label for row in contract.validation_snapshot.rows]
    error_predictions = [
        "benign",
        "task_scam",
        "invalid_output",
        "bank_impersonation",
        "zalo_social_engineering",
        "benign",
        "bank_impersonation",
        "benign",
    ]
    bundles = (
        _prediction_bundle(contract, "qwen-lora", gold),
        _prediction_bundle(contract, "qwen-qlora", error_predictions),
    )
    queue = build_phase40_review_queue(contract, bundles)
    assert len({row.key for row in queue}) == len(queue)
    all_tags = {tag for row in queue for tag in row.slice_tags}
    assert all_tags == {
        "invalid_output",
        "risky_to_benign",
        "zalo_involved_misclassification",
        "benign_to_risky",
        "risky_cross_confusion",
        "correct_calibration_sample",
    }
    source_by_id = {
        row.snapshot_row_id: row for row in contract.validation_snapshot.rows
    }
    for row in queue:
        source = source_by_id[row.validation_row_id]
        assert row.raw_message == source.raw_message
        assert row.source_row_sha256 == source.source_row_sha256
    assert verify_phase40_review_queue(
        queue,
        contract=contract,
        prediction_bundles=bundles,
    ) == queue

    mutated = list(queue)
    mutated[0] = mutated[0].model_copy(update={"raw_message": "nội dung bị thay đổi"})
    with pytest.raises(ValueError, match="differs"):
        verify_phase40_review_queue(
            mutated,
            contract=contract,
            prediction_bundles=bundles,
        )


def test_human_review_requires_exact_ordered_coverage_and_is_verify_only_stable(
    tmp_path, monkeypatch
):
    fixture = _build_comparison_fixture(tmp_path, monkeypatch)
    comparison = _finalize_fixture_comparison(fixture)
    assert comparison.review_queue_path is not None
    assert comparison.review_queue_manifest_path is not None
    queue = tuple(
        ReviewQueueRow.model_validate_json(line)
        for line in comparison.review_queue_path.read_text(encoding="utf-8").splitlines()
    )
    reviews = tuple(
        ReviewerReturnRow(
            model_run_id=row.model_run_id,
            validation_row_id=row.validation_row_id,
            decision="confirmed",
            note_vi="Đã đối chiếu ngữ cảnh đầy đủ và giữ nguyên kết quả.",
        )
        for row in queue
    )
    artifacts = finalize_phase40_human_review(
        queue,
        reviews,
        contract=fixture.contract,
        prediction_bundles=comparison.prediction_bundles,
        queue_manifest_path=comparison.review_queue_manifest_path,
        comparison_manifest_path=comparison.manifest_path,
        output_root=tmp_path / "review",
        vietnamese_fluent_attestation=True,
    )
    before = tuple(path.read_bytes() for path in (
        artifacts.notes_path,
        artifacts.manifest_path,
        artifacts.report_path,
    ))
    finalize_phase40_human_review(
        queue,
        reviews,
        contract=fixture.contract,
        prediction_bundles=comparison.prediction_bundles,
        queue_manifest_path=comparison.review_queue_manifest_path,
        comparison_manifest_path=comparison.manifest_path,
        output_root=tmp_path / "review",
        vietnamese_fluent_attestation=True,
        verify_only=True,
    )
    assert tuple(path.read_bytes() for path in (
        artifacts.notes_path,
        artifacts.manifest_path,
        artifacts.report_path,
    )) == before

    with pytest.raises(ValueError, match="cover every queue key"):
        finalize_phase40_human_review(
            queue,
            tuple(reversed(reviews)),
            contract=fixture.contract,
            prediction_bundles=comparison.prediction_bundles,
            queue_manifest_path=comparison.review_queue_manifest_path,
            comparison_manifest_path=comparison.manifest_path,
            output_root=tmp_path / "bad",
            vietnamese_fluent_attestation=True,
        )


def test_operator_return_is_exact_and_rejection_cannot_claim_roots():
    approvals = (
        PackageDecision(package="bitsandbytes==0.50.1", decision="approve"),
        PackageDecision(package="matplotlib==3.11.1", decision="approve"),
    )
    roots = tuple(
        ReturnedBundleRoot(run_id=run_id, path=path)
        for run_id, path in zip(
            ("qwen-lora", "qwen-qlora", "phobert"),
            (
                "data/models/phase40/full/qwen-lora",
                "data/models/phase40/full/qwen-qlora",
                "data/models/phase40/full/phobert",
            ),
            strict=True,
        )
    )
    gpus = tuple(
        ReturnedGpuIdentity(run_id=root.run_id, accelerator="NVIDIA H100 80GB")
        for root in roots
    )
    assert len(ColabOperatorReturn(
        package_decisions=approvals,
        bundle_roots=roots,
        gpu_identities=gpus,
    ).bundle_roots) == 3

    rejection = (
        PackageDecision(
            package="bitsandbytes==0.50.1",
            decision="reject",
            reason="Official release evidence was not accepted.",
        ),
        PackageDecision(package="matplotlib==3.11.1", decision="approve"),
    )
    with pytest.raises(ValueError, match="cannot claim"):
        ColabOperatorReturn(
            package_decisions=rejection,
            bundle_roots=roots,
            gpu_identities=gpus,
        )


_FIXTURE_GPU = "NVIDIA L4 fixture"
_FIXTURE_STEP = 1


@dataclass(frozen=True)
class _ComparisonFixture:
    repo: Path
    output_root: Path
    contract: Phase40DataContract
    request: RunRequest
    operator_return: ColabOperatorReturn
    evidence_by_run: dict[str, RunEvidence]


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


def _quantization_proof(mode: AdaptationMode) -> QuantizationProofEvidence:
    if mode == AdaptationMode.LORA:
        return QuantizationProofEvidence(
            requested_mode=mode,
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
            adapter_trainable_count=8,
            backward_with_adapter_gradients=False,
            adapter_gradient_finite_count=0,
            adapter_gradient_nonzero_count=0,
        )
    if mode != AdaptationMode.QLORA:
        raise ValueError("only Qwen modes have quantization proof fixtures")
    return QuantizationProofEvidence(
        requested_mode=mode,
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
        adapter_trainable_count=8,
        backward_with_adapter_gradients=True,
        adapter_gradient_finite_count=8,
        adapter_gradient_nonzero_count=8,
    )


def _split_evidence(input_bundle) -> tuple[CanonicalSplitEvidence, CanonicalSplitEvidence]:
    return tuple(
        CanonicalSplitEvidence(
            logical_name=member.logical_name,
            relative_path=f"canonical/{member.member_name}",
            records=member.records,
            bytes=member.bytes,
            sha256=member.sha256,
            ordered_row_ids_sha256=member.ordered_row_ids_sha256,
        )
        for member in input_bundle.data_members
    )


def _controlled_config(
    *,
    model_family: ModelFamily,
    adaptation_mode: AdaptationMode,
    input_bundle,
    accelerator_name: str = _FIXTURE_GPU,
) -> ResumeControlledConfig:
    qwen = model_family == ModelFamily.QWEN
    return ResumeControlledConfig(
        schema_version="phase40-resume-controlled-config-v1",
        experiment_identity=ExperimentIdentityEvidence(
            model_family=model_family,
            adaptation_mode=adaptation_mode,
            run_kind=RunKind.FULL,
        ),
        model_id=(
            "Qwen/Qwen3-4B-Instruct-2507" if qwen else "vinai/phobert-base-v2"
        ),
        model_revision=PINNED_QWEN_REVISION if qwen else PINNED_PHOBERT_REVISION,
        splits=_split_evidence(input_bundle),
        formatter_or_preprocessor_sha256=("b" if qwen else "c") * 64,
        response_mask_or_preprocessor_version=(
            "phase40-response-mask-v1" if qwen else "phase40-phobert-preprocessor-v1"
        ),
        label_order=LABEL_ORDER,
        seed=42,
        data_seed=42,
        max_sequence_length=256,
        truncation_policy="right-truncate-v1",
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,
        world_size=1,
        effective_batch_size=8,
        num_train_epochs=1.0,
        max_optimizer_steps=1,
        gradient_checkpointing=qwen,
        lora_rank=8 if qwen else None,
        lora_alpha=16 if qwen else None,
        lora_dropout=0.05 if qwen else None,
        lora_bias="none" if qwen else None,
        target_modules=("q_proj", "v_proj") if qwen else (),
        task_type="causal-lm" if qwen else "sequence-classification",
        optimizer=OptimizerControls(
            optimizer="adamw-torch",
            learning_rate=0.0002,
            weight_decay=0.01,
            lr_scheduler_type="linear",
            warmup_steps=0,
            warmup_ratio=0.0,
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
            save_total_limit=1,
            generation_steps=(1,),
        ),
        decoder=_decoder() if qwen else None,
        checkpoint_selection_policy="safety-floor-then-macro-f1",
        checkpoint_selection_policy_version="phase40-selection-v1",
        snapshot_id_algorithm_version="phase40-snapshot-row-id-v1",
        quantization_proof=_quantization_proof(adaptation_mode) if qwen else None,
        accelerator=AcceleratorIdentity(
            accelerator_type="cuda",
            accelerator_name=accelerator_name,
            compute_capability="8.9",
            total_memory_bytes=24_000_000_000,
        ),
        additional_controls=(),
    )


def _requested_template(config: ResumeControlledConfig) -> RequestedControlTemplate:
    payload = config.model_dump(mode="json")
    payload.pop("accelerator")
    return RequestedControlTemplate(controls_without_accelerator=payload)


def _transfer_authority(request: RunRequest) -> TransferAuthorityEvidence:
    return TransferAuthorityEvidence(
        schema_version="phase40-transfer-authority-v1",
        source_archive_sha256=request.source_bundle.archive_sha256,
        source_inventory_sha256=request.source_bundle.inventory_sha256,
        input_archive_sha256=request.input_bundle.archive_sha256,
        input_manifest_sha256=request.input_bundle.manifest_sha256,
        source_repository_relative_archive_path=(
            request.source_bundle.repository_relative_archive_path
        ),
        source_repository_relative_inventory_path=(
            request.source_bundle.repository_relative_inventory_path
        ),
        input_repository_relative_path=request.input_bundle.repository_relative_path,
        input_drive_path=request.input_bundle.drive_path,
        input_extraction_root=request.input_bundle.extraction_root,
        input_members=request.input_bundle.members,
        no_held_out_boundary=True,
    )


def _metric_payload(metrics: Phase40MetricResult) -> dict[str, object]:
    return {
        "evaluated_rows": metrics.evaluated_rows,
        "per_class": [asdict(row) for row in metrics.per_class],
        "macro_f1": metrics.macro_f1,
        "weighted_f1": metrics.weighted_f1,
        "accuracy": metrics.accuracy,
        "invalid_output_count": metrics.invalid_output_count,
        "invalid_output_rate": metrics.invalid_output_rate,
        "risky_to_benign_count": metrics.risky_to_benign_count,
        "risky_to_invalid_count": metrics.risky_to_invalid_count,
        "confusion_matrix": [list(row) for row in metrics.confusion_matrix],
        "risky_to_benign_row_ids": list(metrics.risky_to_benign_row_ids),
        "risky_to_invalid_row_ids": list(metrics.risky_to_invalid_row_ids),
    }


def _run_metric_summary(metrics: Phase40MetricResult) -> dict[str, float]:
    by_label = {row.label: row for row in metrics.per_class}
    summary = {
        "accuracy": metrics.accuracy,
        "invalid_output_count": float(metrics.invalid_output_count),
        "invalid_output_rate": metrics.invalid_output_rate,
        "macro_f1": metrics.macro_f1,
        "risky_to_benign_count": float(metrics.risky_to_benign_count),
        "risky_to_invalid_count": float(metrics.risky_to_invalid_count),
        "weighted_f1": metrics.weighted_f1,
    }
    summary.update(
        {f"recall_{label}": by_label[label].recall for label in RISKY_RECALL_FLOORS}
    )
    return dict(sorted(summary.items()))


def _fixture_renderer(data, options) -> bytes:
    digest = hashlib.sha256(data.canonical_bytes + options.sha256.encode("ascii")).digest()
    return b"phase40-fixture-png\0" + digest


def _write_event_log(run_root: Path, run_id: str) -> None:
    events = (
        (RunEventKind.RUN_START, 0, 0.0, {"status": "started"}),
        (RunEventKind.TRAIN_LOG, 1, 0.5, {"loss": 1.0, "learning_rate": 0.0002}),
        (RunEventKind.EVALUATION, 1, 1.0, {"eval_loss": 0.5}),
        (RunEventKind.CHECKPOINT, 1, 1.0, {"checkpoint_saved": True}),
        (RunEventKind.RUN_END, 1, 1.0, {"status": "completed"}),
    )
    for sequence_id, (kind, step, epoch, values) in enumerate(events):
        append_run_event(
            run_root / "events.jsonl",
            RunEvent(
                schema_version="phase40-run-event-v1",
                sequence_id=sequence_id,
                event_kind=kind,
                timestamp_utc=datetime(
                    2026, 8, 24, 12, 0, sequence_id, tzinfo=timezone.utc
                ),
                optimizer_step=step,
                epoch=epoch,
                trainer_values=values,
                source_run_id=run_id,
                run_kind=RunKind.FULL,
            ),
        )


def _artifact(
    run_root: Path, logical_name: str, role: str, relative_path: str
) -> ArtifactEvidence:
    path = run_root / relative_path
    return ArtifactEvidence(
        logical_name=logical_name,
        role=role,
        relative_path=relative_path,
        kind="directory" if path.is_dir() else "file",
        sha256=build_model_checksum(path),
    )


def _predicted_labels(
    contract: Phase40DataContract, *, fail_safety: bool
) -> tuple[str, ...]:
    labels = [row.record.label for row in contract.validation_snapshot.rows]
    if fail_safety:
        labels = ["benign" if label == "bank_impersonation" else label for label in labels]
    return tuple(labels)


def _write_complete_run(
    *,
    repo: Path,
    request: RunRequest,
    requested: FullRunRequestIdentity,
    contract: Phase40DataContract,
    config: ResumeControlledConfig,
    fail_safety: bool,
) -> RunEvidence:
    run_root = repo / requested.returned_root
    run_root.mkdir(parents=True)
    _write_event_log(run_root, requested.run_id)
    (run_root / "resolved-config.json").write_text(
        config.model_dump_json(), encoding="utf-8"
    )
    (run_root / "trainer_state.json").write_text(
        json.dumps({"epoch": 1.0, "global_step": _FIXTURE_STEP}), encoding="utf-8"
    )
    model_root = run_root / "adapter-or-model"
    model_root.mkdir()
    (model_root / "config.json").write_text("{}", encoding="utf-8")
    (model_root / "weights.safetensors").write_bytes(
        f"fixture weights for {requested.run_id}".encode("utf-8")
    )

    artifact_identity = (
        (
            "adapter-state-sha256:"
            if requested.model_family == ModelFamily.QWEN
            else "model-state-sha256:"
        )
        + hashlib.sha256(requested.run_id.encode("utf-8")).hexdigest()
    )
    predicted_labels = _predicted_labels(contract, fail_safety=fail_safety)
    metric_rows = tuple(
        Phase40PredictionRow.from_raw(
            validation_row_id=source.validation_row_id,
            sequence_index=index,
            gold_label=source.record.label,
            raw_prediction=json.dumps({"label": predicted_label}),
            artifact_identity=artifact_identity,
            checkpoint_step=_FIXTURE_STEP,
        )
        for index, (source, predicted_label) in enumerate(
            zip(contract.validation_snapshot.rows, predicted_labels, strict=True)
        )
    )
    if requested.model_family == ModelFamily.QWEN:
        prediction_payload = [row.as_json_dict() for row in metric_rows]
    else:
        prediction_payload = []
        for row in metric_rows:
            logits = [0.0] * len(LABEL_ORDER)
            logits[LABEL_ORDER.index(row.parsed_state.value)] = 1.0
            prediction_payload.append(
                {
                    "validation_row_id": row.validation_row_id,
                    "sequence_index": row.sequence_index,
                    "gold_label": row.gold_label,
                    "artifact_identity": row.artifact_identity,
                    "checkpoint_step": row.checkpoint_step,
                    "logits": logits,
                    "argmax_state": row.parsed_state.value,
                }
            )
    (run_root / "predictions.json").write_text(
        json.dumps(prediction_payload, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )
    metrics = evaluate_phase40_predictions(
        expected_validation_row_ids=contract.validation_snapshot.validation_row_ids,
        gold_labels=tuple(row.record.label for row in contract.validation_snapshot.rows),
        prediction_rows=metric_rows,
    )
    selection = select_phase40_checkpoint((metrics,))
    (run_root / "validation-metrics.json").write_text(
        json.dumps(_metric_payload(metrics), ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )
    if requested.model_family == ModelFamily.PHOBERT:
        (run_root / "preprocessing.json").write_text(
            json.dumps(
                {
                    "preprocessor_version": "phase40-phobert-preprocessor-v1",
                    "rows": len(contract.validation_snapshot.rows),
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )
    graph = render_phase40_graphs(
        run_root,
        renderer=_fixture_renderer,
        renderer_name="fixture-renderer",
        renderer_version="1.0",
    )
    artifact_values = [
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
        _artifact(run_root, "predictions", "predictions", "predictions.json"),
        _artifact(
            run_root, "resolved-config", "resolved_config", "resolved-config.json"
        ),
        _artifact(run_root, "trainer-state", "trainer_state", "trainer_state.json"),
        _artifact(
            run_root,
            "validation-metrics",
            "metrics",
            "validation-metrics.json",
        ),
    ]
    if requested.model_family == ModelFamily.PHOBERT:
        artifact_values.append(
            _artifact(
                run_root,
                "preprocessing",
                "preprocessing",
                "preprocessing.json",
            )
        )
    artifacts = tuple(sorted(artifact_values, key=lambda value: value.logical_name))
    by_logical_name = {artifact.logical_name: artifact for artifact in artifacts}
    checkpoint = ValidationCheckpointEvidence(
        optimizer_step=_FIXTURE_STEP,
        artifact_identity=artifact_identity,
        predictions_sha256=by_logical_name["predictions"].sha256,
        metrics_sha256=by_logical_name["validation-metrics"].sha256,
        macro_f1=metrics.macro_f1,
        safety_gate_passed=selection.safety_gate_passed,
        invalid_output_count=metrics.invalid_output_count,
    )
    evidence = RunEvidence(
        schema_version="phase40-run-evidence-v1",
        run_id=requested.run_id,
        run_kind=RunKind.FULL,
        experiment_identity=config.experiment_identity,
        model_id=config.model_id,
        model_revision=config.model_revision,
        splits=config.splits,
        seed=config.seed,
        data_seed=config.data_seed,
        resolved_config_sha256=by_logical_name["resolved-config"].sha256,
        resume_digest=compute_resume_digest(config),
        prompt_or_preprocessor_sha256=config.formatter_or_preprocessor_sha256,
        decoder_contract=config.decoder,
        decoder_contract_sha256=(config.decoder.sha256 if config.decoder else None),
        sanitized_argv=("train", f"--run-id={requested.run_id}"),
        package_versions={"torch": "fixture"},
        hardware=RuntimeHardwareEvidence(
            python_version="3.13.7",
            platform="fixture-linux",
            cuda_version="13.0",
            cudnn_version="9.9",
            gpu_name=_FIXTURE_GPU,
            gpu_compute_capability="8.9",
            gpu_total_memory_bytes=24_000_000_000,
            bf16_enabled=True,
            fp16_enabled=False,
            tf32_enabled=True,
        ),
        quantization=config.quantization_proof,
        peak_allocated_bytes=1_000,
        peak_reserved_bytes=2_000,
        steady_step_seconds_median=0.5,
        validation_metrics=_run_metric_summary(metrics),
        validation_checkpoints=(checkpoint,),
        selected_checkpoint=SelectedCheckpointEvidence(
            optimizer_step=_FIXTURE_STEP,
            artifact_identity=artifact_identity,
            safety_gate_passed=selection.safety_gate_passed,
            rationale="Mechanically selected from the only retained fixture checkpoint.",
        ),
        artifacts=artifacts,
        artifact_sha256={artifact.logical_name: artifact.sha256 for artifact in artifacts},
        graph_provenance=(graph.as_evidence(),),
        transfer_authority=_transfer_authority(request),
        status=EvidenceStatus.COMPLETE,
        comparison_eligible=True,
        failure_reason=None,
    )
    finalize_run_evidence(run_root, evidence)
    return evidence


def _build_comparison_fixture(
    tmp_path: Path,
    monkeypatch,
    *,
    failing_run_id: str | None = None,
    create_runs: bool = True,
) -> _ComparisonFixture:
    import src.model_adaptation.phase40_handoff as handoff

    repo = tmp_path / "repo"
    source_file = repo / "src" / "fixture_runtime.py"
    source_file.parent.mkdir(parents=True)
    source_file.write_text("FIXTURE = True\n", encoding="utf-8")
    monkeypatch.setattr(
        handoff, "PHASE40_SOURCE_ALLOWLIST", ("src/fixture_runtime.py",)
    )
    contract = _contract(train_count=16, validation_count=219)
    built_input = build_phase40_input_bundle(
        contract,
        repo / FIXED_INPUT_REPOSITORY_PATH,
        repo_root=repo,
    )
    built_source = build_phase40_source_bundle(
        repo, repo / "data/models/phase40/source"
    )
    runs = tuple(
        FullRunRequestIdentity(
            run_id=run_id,
            model_family=family,
            adaptation_mode=mode,
            returned_root=root,
        )
        for run_id, family, mode, root in (
            (
                "qwen-lora",
                ModelFamily.QWEN,
                AdaptationMode.LORA,
                FIXED_RETURNED_ROOTS[0],
            ),
            (
                "qwen-qlora",
                ModelFamily.QWEN,
                AdaptationMode.QLORA,
                FIXED_RETURNED_ROOTS[1],
            ),
            (
                "phobert",
                ModelFamily.PHOBERT,
                AdaptationMode.CLASSIFICATION_HEAD,
                FIXED_RETURNED_ROOTS[2],
            ),
        )
    )
    configs = {
        run.run_id: _controlled_config(
            model_family=run.model_family,
            adaptation_mode=run.adaptation_mode,
            input_bundle=built_input.reference,
        )
        for run in runs
    }
    templates = {
        run_id: _requested_template(config) for run_id, config in configs.items()
    }
    request = RunRequest(
        runs=runs,
        source_bundle=built_source.reference,
        input_bundle=built_input.reference,
        package_candidates=PACKAGE_CANDIDATES,
        expected_bundle_files=REQUIRED_FULL_BUNDLE_FILES,
        control_template_by_run=templates,
        control_template_digest_by_run={
            run_id: template.sha256 for run_id, template in templates.items()
        },
        no_held_out_boundary=True,
    )
    approvals = tuple(
        PackageDecision(package=package, decision="approve")
        for package in PACKAGE_CANDIDATES
    )
    operator_return = ColabOperatorReturn(
        package_decisions=approvals,
        bundle_roots=tuple(
            ReturnedBundleRoot(run_id=run.run_id, path=run.returned_root)
            for run in runs
        ),
        gpu_identities=tuple(
            ReturnedGpuIdentity(run_id=run.run_id, accelerator=_FIXTURE_GPU)
            for run in runs
        ),
    )
    evidence_by_run = {}
    if create_runs:
        evidence_by_run = {
            run.run_id: _write_complete_run(
                repo=repo,
                request=request,
                requested=run,
                contract=contract,
                config=configs[run.run_id],
                fail_safety=run.run_id == failing_run_id,
            )
            for run in runs
        }
    return _ComparisonFixture(
        repo=repo,
        output_root=repo / "data/models/phase40/comparison",
        contract=contract,
        request=request,
        operator_return=operator_return,
        evidence_by_run=evidence_by_run,
    )


def _finalize_fixture_comparison(fixture: _ComparisonFixture, **kwargs) -> ComparisonArtifacts:
    return finalize_phase40_comparison(
        fixture.request,
        fixture.operator_return,
        repo_root=fixture.repo,
        output_root=fixture.output_root,
        renderer=_fixture_renderer,
        renderer_name="fixture-renderer",
        renderer_version="1.0",
        **kwargs,
    )


def test_requested_controls_and_run_request_are_exact_and_reject_drift(
    tmp_path, monkeypatch
):
    fixture = _build_comparison_fixture(tmp_path, monkeypatch, create_runs=False)
    request = fixture.request
    assert tuple(request.control_template_by_run) == (
        "qwen-lora",
        "qwen-qlora",
        "phobert",
    )
    for run_id, template in request.control_template_by_run.items():
        assert "accelerator" not in template.controls_without_accelerator
        assert template.sha256 == request.control_template_digest_by_run[run_id]
        assert template.materialize_for_validation().seed == 42

    missing = dict(
        request.control_template_by_run["qwen-lora"].controls_without_accelerator
    )
    missing.pop("seed")
    with pytest.raises(ValidationError, match="requested controls must be exact"):
        RequestedControlTemplate(controls_without_accelerator=missing)

    guessed_hardware = dict(
        request.control_template_by_run["qwen-lora"].controls_without_accelerator
    )
    guessed_hardware["accelerator"] = {"accelerator_name": "guessed"}
    with pytest.raises(ValidationError, match="must not contain guessed"):
        RequestedControlTemplate(controls_without_accelerator=guessed_hardware)

    changed = dict(
        request.control_template_by_run["qwen-qlora"].controls_without_accelerator
    )
    changed["optimizer"] = dict(changed["optimizer"])
    changed["optimizer"]["learning_rate"] = 0.0003
    changed_template = RequestedControlTemplate(controls_without_accelerator=changed)
    payload = request.model_dump(mode="python")
    payload["control_template_by_run"]["qwen-qlora"] = changed_template
    payload["control_template_digest_by_run"]["qwen-qlora"] = changed_template.sha256
    with pytest.raises(ValidationError, match="beyond base-weight quantization"):
        RunRequest.model_validate(payload)

    changed_model = dict(
        request.control_template_by_run["phobert"].controls_without_accelerator
    )
    changed_model["model_id"] = "vinai/phobert-base"
    changed_model_template = RequestedControlTemplate(
        controls_without_accelerator=changed_model
    )
    payload = request.model_dump(mode="python")
    payload["control_template_by_run"]["phobert"] = changed_model_template
    payload["control_template_digest_by_run"]["phobert"] = changed_model_template.sha256
    with pytest.raises(ValidationError, match="model ID is not the pinned"):
        RunRequest.model_validate(payload)


def test_full_run_request_freezes_only_at_canonical_path_and_reverifies_authorities(
    tmp_path, monkeypatch
):
    fixture = _build_comparison_fixture(tmp_path, monkeypatch, create_runs=False)
    canonical = fixture.repo / FIXED_RUN_REQUEST_PATH

    frozen = freeze_phase40_run_request(fixture.request, repo_root=fixture.repo)
    original_bytes = frozen.read_bytes()
    assert frozen == canonical
    assert load_frozen_phase40_run_request(repo_root=fixture.repo) == fixture.request

    replay = freeze_phase40_run_request(fixture.request, repo_root=fixture.repo)
    assert replay.read_bytes() == original_bytes

    with pytest.raises(ValueError, match="not canonical"):
        freeze_phase40_run_request(
            fixture.request,
            repo_root=fixture.repo,
            output_path=fixture.repo / "request-copy.json",
        )

    canonical.write_bytes(original_bytes + b" ")
    with pytest.raises((RuntimeError, ValidationError, ValueError)):
        load_frozen_phase40_run_request(repo_root=fixture.repo)


def test_finalize_comparison_succeeds_and_verify_only_is_byte_stable(
    tmp_path, monkeypatch
):
    fixture = _build_comparison_fixture(tmp_path, monkeypatch)
    artifacts = _finalize_fixture_comparison(fixture)
    assert artifacts.manifest.status == "complete"
    assert artifacts.manifest.validation_rows == 219
    assert artifacts.manifest.quality_comparison_admissible is True
    assert artifacts.manifest.speed_comparison_admissible is True
    assert len(artifacts.manifest.runs) == 3
    assert artifacts.review_queue_path is not None
    assert artifacts.review_queue_manifest_path is not None
    assert artifacts.reviewer_template_path is not None
    assert artifacts.selected_prediction_bundles_path is not None
    paths = (
        artifacts.manifest_path,
        artifacts.report_path,
        artifacts.review_queue_path,
        artifacts.review_queue_manifest_path,
        artifacts.reviewer_template_path,
        artifacts.selected_prediction_bundles_path,
    )
    before = tuple(path.read_bytes() for path in paths)
    replay = _finalize_fixture_comparison(fixture, verify_only=True)
    assert replay.manifest == artifacts.manifest
    assert tuple(path.read_bytes() for path in paths) == before


def test_package_rejection_writes_prestart_failure_without_opening_bundle_roots(
    tmp_path, monkeypatch
):
    fixture = _build_comparison_fixture(tmp_path, monkeypatch, create_runs=False)
    rejected = ColabOperatorReturn(
        package_decisions=(
            PackageDecision(
                package=PACKAGE_CANDIDATES[0],
                decision="reject",
                reason="Approved release evidence was unavailable.",
            ),
            PackageDecision(package=PACKAGE_CANDIDATES[1], decision="approve"),
        )
    )
    opened_roots: list[Path] = []

    def forbidden_bundle_verifier(path: Path) -> RunEvidence:
        opened_roots.append(path)
        raise AssertionError("a package rejection must not open a returned bundle root")

    artifacts = finalize_phase40_comparison(
        fixture.request,
        rejected,
        repo_root=fixture.repo,
        output_root=fixture.output_root,
        bundle_verifier=forbidden_bundle_verifier,
    )
    assert opened_roots == []
    assert artifacts.manifest.status == "prestart_failed"
    assert artifacts.manifest.quality_comparison_admissible is False
    assert artifacts.prediction_bundles == ()
    assert not any((fixture.repo / root).exists() for root in FIXED_RETURNED_ROOTS)


@pytest.mark.parametrize(
    ("drift_name", "relative_path", "mutate"),
    (
        (
            "config",
            "resolved-config.json",
            lambda payload: payload.replace(b'"max_optimizer_steps":1', b'"max_optimizer_steps":2'),
        ),
        (
            "prediction",
            "predictions.json",
            lambda payload: payload + b" ",
        ),
        (
            "metrics",
            "validation-metrics.json",
            lambda payload: payload + b" ",
        ),
        (
            "graph",
            "curves/loss-curves.png",
            lambda payload: payload + b"drift",
        ),
    ),
)
def test_finalize_comparison_rejects_returned_artifact_drift(
    tmp_path,
    monkeypatch,
    drift_name: str,
    relative_path: str,
    mutate: Callable[[bytes], bytes],
):
    fixture = _build_comparison_fixture(tmp_path, monkeypatch)
    target = fixture.repo / FIXED_RETURNED_ROOTS[0] / relative_path
    original = target.read_bytes()
    mutated = mutate(original)
    assert mutated != original, f"{drift_name} mutation must change bytes"
    target.write_bytes(mutated)
    with pytest.raises(RuntimeError, match="artifact SHA-256 mismatch"):
        _finalize_fixture_comparison(fixture)


def test_failed_safety_run_is_retained_but_comparison_is_inadmissible(
    tmp_path, monkeypatch
):
    fixture = _build_comparison_fixture(
        tmp_path, monkeypatch, failing_run_id="qwen-qlora"
    )
    artifacts = _finalize_fixture_comparison(fixture)
    by_id = {run.run_id: run for run in artifacts.manifest.runs}
    assert tuple(run.run_id for run in artifacts.manifest.runs) == (
        "qwen-lora",
        "qwen-qlora",
        "phobert",
    )
    assert by_id["qwen-qlora"].safety_gate_passed is False
    assert by_id["qwen-qlora"].comparison_eligible is True
    assert by_id["qwen-qlora"].risky_recall_by_label["bank_impersonation"] == 0.0
    assert artifacts.manifest.quality_comparison_admissible is False
    assert artifacts.manifest.speed_comparison_admissible is False
    assert "qwen-qlora" in artifacts.report_path.read_text(encoding="utf-8")
