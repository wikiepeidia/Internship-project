"""Fixture-only tests for Phase 40 source/data handoff and human review."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
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
    FIXED_ACTIVE_RETURNED_ROOTS,
    FIXED_INPUT_REPOSITORY_PATH,
    FIXED_LORA_PROBE_FILES,
    FIXED_LORA_PROBE_ROOT,
    FIXED_RUN_REQUEST_PATH,
    FIXED_SCOPE_AMENDMENT_PATH,
    FIXED_RETURNED_ROOTS,
    PACKAGE_CANDIDATES,
    PINNED_PHOBERT_REVISION,
    PINNED_QWEN_REVISION,
    REQUIRED_FULL_BUNDLE_FILES,
    ColabOperatorReturn,
    ComparisonArtifacts,
    Phase40ComparisonManifest,
    FullRunRequestIdentity,
    PackageDecision,
    RequestedControlTemplate,
    ReturnedBundleRoot,
    ReturnedGpuIdentity,
    ReviewQueueRow,
    ReviewerReturnRow,
    RunRequest,
    SelectedPredictionBundle,
    _comparison_report,
    _phase40_production_authority_values,
    build_phase40_input_bundle,
    build_phase40_review_queue,
    build_phase40_scope_amendment,
    build_phase40_source_bundle,
    finalize_phase40_comparison,
    finalize_phase40_human_review,
    freeze_phase40_scope_amendment,
    freeze_phase40_run_request,
    load_frozen_phase40_run_request,
    load_frozen_phase40_scope_amendment,
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
        canonical_sequence=1,
        raw_message="Tin nhắn kiểm thử.",
        source_row_sha256="1" * 64,
        gold_label="benign",
        predicted_label="bank_impersonation",
        selected_checkpoint_identity="checkpoint-1",
        model_artifact_identity="artifact-1",
        slice_tags=("benign_to_risky",),
        assessment="prediction_unsupported",
        mechanism_note_vi="cần\n  xem lại\tngữ cảnh",
        shortcut_pattern_note_vi="dựa\n  quá nhiều\tvào từ khóa",
    )

    assert decision.reason == "không chấp thuận trên máy này"
    assert review.mechanism_note_vi == "cần xem lại ngữ cảnh"
    assert review.shortcut_pattern_note_vi == "dựa quá nhiều vào từ khóa"
    with pytest.raises(ValidationError):
        ReviewerReturnRow.model_validate(
            {**review.model_dump(mode="json"), "assessment": "confirmed"}
        )


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


def _review_return(
    row: ReviewQueueRow,
    *,
    assessment: str = "prediction_supported",
    shortcut_pattern_note_vi: str | None = None,
) -> ReviewerReturnRow:
    return ReviewerReturnRow(
        **row.model_dump(mode="json"),
        assessment=assessment,
        mechanism_note_vi="Đã đối chiếu toàn bộ ngữ cảnh và giữ nguyên kết quả.",
        shortcut_pattern_note_vi=shortcut_pattern_note_vi,
    )


def _reviewer_return_bytes(rows: tuple[ReviewerReturnRow, ...]) -> bytes:
    return b"".join(
        (
            json.dumps(
                row.model_dump(mode="json"),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        ).encode("utf-8")
        for row in rows
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
    assessments = (
        "prediction_supported",
        "prediction_unsupported",
        "gold_label_concern",
        "ambiguous",
    )
    reviews = tuple(
        _review_return(
            row,
            assessment=assessments[index % len(assessments)],
            shortcut_pattern_note_vi=(
                "Mô hình có thể dựa quá nhiều vào từ khóa."
                if index % 2 == 0
                else None
            ),
        )
        for index, row in enumerate(queue)
    )
    canonical_review_bytes = _reviewer_return_bytes(reviews)
    canonical_queue_bytes = comparison.review_queue_path.read_bytes()
    original_bytes = b"".join(
        b" " + line + b"\n" for line in canonical_review_bytes.splitlines()
    )
    artifacts = finalize_phase40_human_review(
        queue,
        reviews,
        request=fixture.request,
        repo_root=fixture.repo,
        contract=fixture.contract,
        prediction_bundles=comparison.prediction_bundles,
        queue_manifest_path=comparison.review_queue_manifest_path,
        comparison_manifest_path=comparison.manifest_path,
        scope_amendment_path=fixture.scope_amendment_path,
        output_root=tmp_path / "review",
        queue_bytes=canonical_queue_bytes,
        reviewer_return_bytes=original_bytes,
        vietnamese_fluent_attestation=True,
    )
    before = tuple(path.read_bytes() for path in (
        artifacts.notes_path,
        artifacts.manifest_path,
        artifacts.report_path,
    ))
    manifest = json.loads(artifacts.manifest_path.read_text(encoding="utf-8"))
    report_bytes = artifacts.report_path.read_bytes()
    assert manifest["schema_version"] == "phase40-human-review-v2"
    assert manifest["vietnamese_fluent_attestation"] is True
    assert manifest["reviewer_return_sha256"] == hashlib.sha256(original_bytes).hexdigest()
    assert manifest["notes_sha256"] == hashlib.sha256(before[0]).hexdigest()
    assert manifest["report_sha256"] == hashlib.sha256(report_bytes).hexdigest()
    assert manifest["reviewer_return_sha256"] != manifest["notes_sha256"]
    assert manifest["limitations"] == list(comparison.manifest.limitations)
    summary = manifest["summary"]
    assert summary["overall"]["rows"] == len(queue)
    assert sum(summary["overall"]["assessment_counts"].values()) == len(queue)
    assert [entry["model_run_id"] for entry in summary["per_model"]] == [
        run.run_id for run in comparison.manifest.runs
    ]
    assert [entry["slice"] for entry in summary["per_slice"]] == [
        "invalid_output",
        "risky_to_benign",
        "zalo_involved_misclassification",
        "benign_to_risky",
        "risky_cross_confusion",
        "correct_calibration_sample",
    ]
    assert summary["overall"]["mechanism_note_counts"] == [
        {
            "note_vi": "Đã đối chiếu toàn bộ ngữ cảnh và giữ nguyên kết quả.",
            "rows": len(queue),
        }
    ]
    report = report_bytes.decode("utf-8")
    for heading in (
        "Vietnamese-fluent reviewer attestation: **confirmed**",
        "## Overall summary",
        "## Per-model summary",
        "## Per-slice summary",
        "## Row observations",
        "## Limitations",
    ):
        assert heading in report
    assert "single_training_seed_42_no_variance_or_significance_claim" in report
    assert "development validation data and a single training seed" in report
    finalize_phase40_human_review(
        queue,
        reviews,
        request=fixture.request,
        repo_root=fixture.repo,
        contract=fixture.contract,
        prediction_bundles=comparison.prediction_bundles,
        queue_manifest_path=comparison.review_queue_manifest_path,
        comparison_manifest_path=comparison.manifest_path,
        scope_amendment_path=fixture.scope_amendment_path,
        output_root=tmp_path / "review",
        queue_bytes=canonical_queue_bytes,
        reviewer_return_bytes=original_bytes,
        vietnamese_fluent_attestation=True,
        verify_only=True,
    )
    assert tuple(path.read_bytes() for path in (
        artifacts.notes_path,
        artifacts.manifest_path,
        artifacts.report_path,
    )) == before

    with pytest.raises(ValueError, match="artifact verification failed"):
        finalize_phase40_human_review(
            queue,
            reviews,
            request=fixture.request,
            repo_root=fixture.repo,
            contract=fixture.contract,
            prediction_bundles=comparison.prediction_bundles,
            queue_manifest_path=comparison.review_queue_manifest_path,
            comparison_manifest_path=comparison.manifest_path,
            scope_amendment_path=fixture.scope_amendment_path,
            output_root=tmp_path / "review",
            queue_bytes=canonical_queue_bytes,
            reviewer_return_bytes=b" " + original_bytes,
            vietnamese_fluent_attestation=True,
            verify_only=True,
        )

    mutated_reviews = list(reviews)
    mutated_reviews[0] = mutated_reviews[0].model_copy(
        update={"raw_message": "Nội dung hàng đợi bị thay đổi."}
    )
    with pytest.raises(ValueError, match="immutable queue fields differ"):
        finalize_phase40_human_review(
            queue,
            tuple(mutated_reviews),
            request=fixture.request,
            repo_root=fixture.repo,
            contract=fixture.contract,
            prediction_bundles=comparison.prediction_bundles,
            queue_manifest_path=comparison.review_queue_manifest_path,
            comparison_manifest_path=comparison.manifest_path,
            scope_amendment_path=fixture.scope_amendment_path,
            output_root=tmp_path / "mutated-review",
            queue_bytes=canonical_queue_bytes,
            reviewer_return_bytes=_reviewer_return_bytes(tuple(mutated_reviews)),
            vietnamese_fluent_attestation=True,
        )

    with pytest.raises(ValueError, match="cover every queue key"):
        finalize_phase40_human_review(
            queue,
            tuple(reversed(reviews)),
            request=fixture.request,
            repo_root=fixture.repo,
            contract=fixture.contract,
            prediction_bundles=comparison.prediction_bundles,
            queue_manifest_path=comparison.review_queue_manifest_path,
            comparison_manifest_path=comparison.manifest_path,
            scope_amendment_path=fixture.scope_amendment_path,
            output_root=tmp_path / "bad",
            queue_bytes=canonical_queue_bytes,
            reviewer_return_bytes=b"".join(
                b" " + line + b"\n"
                for line in _reviewer_return_bytes(tuple(reversed(reviews))).splitlines()
            ),
            vietnamese_fluent_attestation=True,
        )

    artifacts.report_path.write_bytes(report_bytes + b"tampered\n")
    with pytest.raises(ValueError, match="artifact verification failed"):
        finalize_phase40_human_review(
            queue,
            reviews,
            request=fixture.request,
            repo_root=fixture.repo,
            contract=fixture.contract,
            prediction_bundles=comparison.prediction_bundles,
            queue_manifest_path=comparison.review_queue_manifest_path,
            comparison_manifest_path=comparison.manifest_path,
            scope_amendment_path=fixture.scope_amendment_path,
            output_root=tmp_path / "review",
            queue_bytes=canonical_queue_bytes,
            reviewer_return_bytes=original_bytes,
            vietnamese_fluent_attestation=True,
            verify_only=True,
        )


def test_local_operator_return_is_exact_and_legacy_decisions_are_non_gating():
    approvals = (
        PackageDecision(package="bitsandbytes==0.50.1", decision="approve"),
        PackageDecision(package="matplotlib==3.11.1", decision="approve"),
    )
    roots = tuple(
        ReturnedBundleRoot(run_id=run_id, path=path)
        for run_id, path in zip(
            ("qwen-qlora", "phobert"),
            FIXED_ACTIVE_RETURNED_ROOTS,
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
    ).bundle_roots) == 2

    rejection = (
        PackageDecision(
            package="bitsandbytes==0.50.1",
            decision="reject",
            reason="Official release evidence was not accepted.",
        ),
        PackageDecision(package="matplotlib==3.11.1", decision="approve"),
    )
    legacy = ColabOperatorReturn(
        package_decisions=rejection,
        bundle_roots=roots,
        gpu_identities=gpus,
    )
    assert legacy.package_decisions == rejection
    assert ColabOperatorReturn(bundle_roots=roots, gpu_identities=gpus).package_decisions == ()
    with pytest.raises(ValueError, match="exactly QLoRA and PhoBERT"):
        ColabOperatorReturn(
            bundle_roots=(
                ReturnedBundleRoot(
                    run_id="qwen-lora",
                    path="data/models/phase40/full/qwen-lora",
                ),
                *roots,
            ),
            gpu_identities=(
                ReturnedGpuIdentity(run_id="qwen-lora", accelerator="NVIDIA H100 80GB"),
                *gpus,
            ),
        )


_FIXTURE_GPU = "NVIDIA L4 fixture"
_FIXTURE_STEP = 1


@dataclass(frozen=True)
class _ComparisonFixture:
    repo: Path
    output_root: Path
    scope_amendment_path: Path
    contract: Phase40DataContract
    request: RunRequest
    operator_return: ColabOperatorReturn
    evidence_by_run: dict[str, RunEvidence]


def _write_lora_probe_fixture(repo: Path) -> None:
    root = repo / FIXED_LORA_PROBE_ROOT
    root.mkdir(parents=True)
    telemetry = b'{"sequence":0,"device_vram_used_mib":7902}\n'
    optimizer = b'{"optimizer_step":31,"step_seconds":53.2743492}\n'
    proof = _quantization_proof(AdaptationMode.LORA).model_dump_json().encode("utf-8")
    discard = {
        "discarded_path_identity": "runtime",
        "path_absent": True,
        "pre_discard_sha256": "a" * 64,
        "removal_result": "removed",
        "run_id": "rtx5050-lora-retry-1",
        "schema_version": "phase40-discard-v1",
    }
    discard_bytes = json.dumps(discard, sort_keys=True, separators=(",", ":")).encode("utf-8")
    payloads = {
        "telemetry.jsonl": telemetry,
        "optimizer-events.jsonl": optimizer,
        "quantization-proof.json": proof,
        "discard-receipt.json": discard_bytes,
    }
    for name, payload in payloads.items():
        (root / name).write_bytes(payload)
    outcome = {
        "schema_version": "phase40-local-outcome-v1",
        "status": "error",
        "stop_reason": "parent_controller_error",
        "measured_target_reached": False,
        "losses_finite": True,
        "observed_optimizer_steps": 31,
        "retained_optimizer_steps": 26,
        "steady_state_step_seconds_median": 53.2743492,
        "telemetry": "lora-retry-1/telemetry.jsonl",
        "telemetry_sha256": hashlib.sha256(telemetry).hexdigest(),
        "optimizer_events": "lora-retry-1/optimizer-events.jsonl",
        "optimizer_events_sha256": hashlib.sha256(optimizer).hexdigest(),
        "quantization_proof": "lora-retry-1/quantization-proof.json",
        "quantization_proof_sha256": hashlib.sha256(proof).hexdigest(),
        "discard_receipt": discard,
        "memory_pressure": {
            "classification": "gpu_pressure",
            "memory_constrained": True,
            "oom_kind": None,
            "peak_device_vram_used_mib": 7902.0,
            "minimum_device_vram_free_mib": 9.0,
        },
        "resource_peaks": {"system_ram_used_bytes": 22_479_200_256.0},
    }
    (root / "outcome.json").write_text(
        json.dumps(outcome, sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
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
        renderer_name="matplotlib",
        renderer_version="3.11.1",
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
        package_versions={
            "python": "3.13.7",
            "torch": "fixture-torch",
            "transformers": "fixture-transformers",
            **(
                {"peft": "fixture-peft", "bitsandbytes": "0.50.1"}
                if requested.adaptation_mode == AdaptationMode.QLORA
                else {}
            ),
        },
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
    (repo / "src" / "__init__.py").write_text("", encoding="utf-8")
    (repo / "src" / "fixture_dependency.py").write_text(
        "VALUE = True\n",
        encoding="utf-8",
    )
    source_file.write_text(
        "from src.fixture_dependency import VALUE\nFIXTURE = VALUE\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        handoff, "PHASE40_SOURCE_ALLOWLIST", ("src/fixture_runtime.py",)
    )
    monkeypatch.setattr(
        handoff,
        "PHASE40_COMPARISON_FINALIZER_SOURCE_ALLOWLIST",
        (
            "src/__init__.py",
            "src/fixture_dependency.py",
            "src/fixture_runtime.py",
        ),
    )
    monkeypatch.setattr(
        handoff,
        "PHASE40_COMPARISON_FINALIZER_ENTRYPOINTS",
        ("src/fixture_runtime.py",),
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
    freeze_phase40_run_request(request, repo_root=repo)
    _write_lora_probe_fixture(repo)
    scope_amendment_path = freeze_phase40_scope_amendment(
        request,
        repo_root=repo,
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
            if run.returned_root in FIXED_ACTIVE_RETURNED_ROOTS
        ),
        gpu_identities=tuple(
            ReturnedGpuIdentity(run_id=run.run_id, accelerator=_FIXTURE_GPU)
            for run in runs
            if run.returned_root in FIXED_ACTIVE_RETURNED_ROOTS
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
            if run.returned_root in FIXED_ACTIVE_RETURNED_ROOTS
        }
    return _ComparisonFixture(
        repo=repo,
        output_root=repo / "data/models/phase40/comparison",
        scope_amendment_path=scope_amendment_path,
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
        scope_amendment_path=fixture.scope_amendment_path,
        output_root=fixture.output_root,
        renderer=_fixture_renderer,
        renderer_name="matplotlib",
        renderer_version="3.11.1",
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


def test_scope_amendment_is_additive_hash_bound_and_probe_only(tmp_path, monkeypatch):
    fixture = _build_comparison_fixture(tmp_path, monkeypatch, create_runs=False)
    request_bytes = (fixture.repo / FIXED_RUN_REQUEST_PATH).read_bytes()
    amendment = load_frozen_phase40_scope_amendment(
        request=fixture.request,
        repo_root=fixture.repo,
        amendment_path=fixture.scope_amendment_path,
    )
    assert fixture.scope_amendment_path == fixture.repo / FIXED_SCOPE_AMENDMENT_PATH
    assert amendment.original_run_request_sha256 == hashlib.sha256(request_bytes).hexdigest()
    assert amendment.active_full_run_ids == ("qwen-qlora", "phobert")
    assert amendment.quality_model_run_ids == amendment.active_full_run_ids
    assert amendment.review_model_run_ids == amendment.active_full_run_ids
    assert amendment.waived_full_run_id == "qwen-lora"
    assert amendment.waiver_action == "withdrawn"
    assert amendment.full_lora_disposition == "cancelled_before_start"
    assert amendment.execution_policy == "local_primary"
    assert amendment.comparison_finalizer_authority.runtime_origin == (
        "local_hash_pinned_source_not_training_runtime_v3"
    )
    assert tuple(
        item.relative_path for item in amendment.lora_probe_authority.artifacts
    ) == FIXED_LORA_PROBE_FILES
    assert (fixture.repo / FIXED_RUN_REQUEST_PATH).read_bytes() == request_bytes

    amendment_path = fixture.repo / FIXED_SCOPE_AMENDMENT_PATH
    amendment_path.write_bytes(
        amendment_path.read_bytes().replace(
            amendment.original_run_request_sha256.encode("ascii"),
            b"0" * 64,
            1,
        )
    )
    with pytest.raises(ValueError, match="different frozen run request"):
        load_frozen_phase40_scope_amendment(
            request=fixture.request,
            repo_root=fixture.repo,
        )


@pytest.mark.parametrize("drift", ("finalizer-source", "probe-telemetry"))
def test_scope_amendment_rejects_bound_authority_drift(tmp_path, monkeypatch, drift):
    fixture = _build_comparison_fixture(tmp_path, monkeypatch, create_runs=False)
    if drift == "finalizer-source":
        (fixture.repo / "src/fixture_dependency.py").write_text(
            "VALUE = False\n",
            encoding="utf-8",
        )
        expected = "finalizer source differs"
    else:
        telemetry = fixture.repo / FIXED_LORA_PROBE_ROOT / "telemetry.jsonl"
        telemetry.write_bytes(telemetry.read_bytes() + b'{"sequence":1}\n')
        expected = "artifact identity mismatch"
    with pytest.raises(ValueError, match=expected):
        load_frozen_phase40_scope_amendment(
            request=fixture.request,
            repo_root=fixture.repo,
        )


def test_comparison_finalizer_authority_rejects_unbound_local_import(
    tmp_path,
    monkeypatch,
):
    fixture = _build_comparison_fixture(tmp_path, monkeypatch, create_runs=False)
    (fixture.repo / "src/unbound_dependency.py").write_text(
        "VALUE = True\n",
        encoding="utf-8",
    )
    (fixture.repo / "src/fixture_runtime.py").write_text(
        "from src.unbound_dependency import VALUE\nFIXTURE = VALUE\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="unbound local module"):
        build_phase40_scope_amendment(
            fixture.request,
            repo_root=fixture.repo,
        )


@pytest.mark.parametrize("mutation", ("missing", "mutated", "supplied-object"))
def test_finalizer_reloads_raw_canonical_request_before_bundle_read(
    tmp_path,
    monkeypatch,
    mutation,
):
    fixture = _build_comparison_fixture(tmp_path, monkeypatch)
    request_path = fixture.repo / FIXED_RUN_REQUEST_PATH
    supplied_request = fixture.request
    if mutation == "missing":
        request_path.unlink()
    elif mutation == "mutated":
        request_path.write_bytes(request_path.read_bytes() + b" ")
    else:
        supplied_request = fixture.request.model_copy(update={"git_commit": "different"})
    opened: list[Path] = []

    def forbidden_bundle_read(path: Path) -> RunEvidence:
        opened.append(path)
        raise AssertionError("bundle verifier must not run before canonical request reload")

    with pytest.raises((FileNotFoundError, RuntimeError, ValueError)):
        finalize_phase40_comparison(
            supplied_request,
            fixture.operator_return,
            repo_root=fixture.repo,
            scope_amendment_path=fixture.scope_amendment_path,
            output_root=fixture.output_root,
            bundle_verifier=forbidden_bundle_read,
            renderer=_fixture_renderer,
            renderer_name="matplotlib",
            renderer_version="3.11.1",
        )
    assert opened == []


def test_human_review_reloads_raw_canonical_request_before_queue_or_bundle_use(
    tmp_path,
    monkeypatch,
):
    fixture = _build_comparison_fixture(tmp_path, monkeypatch, create_runs=False)
    request_path = fixture.repo / FIXED_RUN_REQUEST_PATH
    request_path.write_bytes(request_path.read_bytes() + b" ")
    with pytest.raises((RuntimeError, ValueError)):
        finalize_phase40_human_review(
            (),
            (),
            request=fixture.request,
            repo_root=fixture.repo,
            contract=fixture.contract,
            prediction_bundles=(),
            queue_manifest_path=fixture.repo / "must-not-read-queue-manifest.json",
            comparison_manifest_path=fixture.repo / "must-not-read-comparison.json",
            scope_amendment_path=fixture.scope_amendment_path,
            output_root=fixture.repo / "must-not-write-review",
            queue_bytes=b"",
            reviewer_return_bytes=b"{}\n",
            vietnamese_fluent_attestation=True,
        )


@pytest.mark.parametrize(
    "redirected_gate",
    ("amendment", "finalizer-source", "probe", "returned-root"),
)
def test_finalizer_gates_reject_redirecting_ancestor_components(
    tmp_path,
    monkeypatch,
    redirected_gate,
):
    fixture = _build_comparison_fixture(
        tmp_path,
        monkeypatch,
        create_runs=redirected_gate == "returned-root",
    )
    if redirected_gate == "amendment":
        redirected = fixture.repo / "data/models/phase40"
    elif redirected_gate == "finalizer-source":
        redirected = fixture.repo / "src"
    elif redirected_gate == "probe":
        redirected = fixture.repo / "data/models/phase40/probes/rtx5050-local-decision"
    else:
        redirected = fixture.repo / "data/models/phase40/full"
    real = redirected.with_name(f"{redirected.name}-real")
    redirected.rename(real)
    try:
        os.symlink(real, redirected, target_is_directory=True)
    except (OSError, NotImplementedError) as exc:
        real.rename(redirected)
        pytest.skip(f"directory symlink unavailable: {exc}")

    if redirected_gate != "returned-root":
        operation = lambda: load_frozen_phase40_scope_amendment(
            request=fixture.request,
            repo_root=fixture.repo,
        )
    else:
        opened: list[Path] = []

        def forbidden_bundle_read(path: Path) -> RunEvidence:
            opened.append(path)
            raise AssertionError("redirected root must fail before bundle verification")

        operation = lambda: finalize_phase40_comparison(
            fixture.request,
            fixture.operator_return,
            repo_root=fixture.repo,
            scope_amendment_path=fixture.scope_amendment_path,
            output_root=fixture.output_root,
            bundle_verifier=forbidden_bundle_read,
            renderer=_fixture_renderer,
            renderer_name="matplotlib",
            renderer_version="3.11.1",
        )
    with pytest.raises(ValueError, match="symbolic link or junction"):
        operation()
    if redirected_gate == "returned-root":
        assert opened == []


def test_finalize_comparison_succeeds_and_verify_only_is_byte_stable(
    tmp_path, monkeypatch
):
    fixture = _build_comparison_fixture(tmp_path, monkeypatch)
    artifacts = _finalize_fixture_comparison(fixture)
    assert artifacts.manifest.status == "complete"
    assert artifacts.manifest.validation_rows == 219
    assert artifacts.manifest.quality_comparison_admissible is True
    assert artifacts.manifest.speed_comparison_admissible is False
    assert tuple(run.run_id for run in artifacts.manifest.runs) == (
        "qwen-qlora",
        "phobert",
    )
    assert artifacts.manifest.lora_probe.comparison_eligible is False
    assert artifacts.manifest.lora_probe.predictions_included is False
    assert artifacts.manifest.lora_probe.oom_observed is False
    assert artifacts.manifest.lora_probe.feasibility_claim == (
        "technically_runnable_but_operationally_impractical_under_deadline"
    )
    by_run = {run.run_id: run for run in artifacts.manifest.runs}
    assert by_run["qwen-qlora"].package_versions == (
        fixture.evidence_by_run["qwen-qlora"].package_versions
    )
    assert by_run["phobert"].package_versions == (
        fixture.evidence_by_run["phobert"].package_versions
    )
    assert by_run["qwen-qlora"].required_tool_pins == {
        "bitsandbytes": "0.50.1",
        "matplotlib": "3.11.1",
    }
    assert by_run["phobert"].required_tool_pins == {
        "matplotlib": "3.11.1"
    }
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


def test_checkpoint_metrics_allow_byte_identical_duplicate_artifact_paths(
    tmp_path,
    monkeypatch,
):
    import src.model_adaptation.phase40_handoff as handoff

    fixture = _build_comparison_fixture(tmp_path, monkeypatch)
    evidence = fixture.evidence_by_run["phobert"]
    returned_root = next(
        run.returned_root for run in fixture.request.runs if run.run_id == "phobert"
    )
    run_root = fixture.repo / returned_root
    original = next(
        artifact for artifact in evidence.artifacts if artifact.role == "metrics"
    )
    duplicate_relative = "checkpoints/duplicate/validation-metrics.json"
    duplicate_path = run_root / duplicate_relative
    duplicate_path.parent.mkdir(parents=True)
    duplicate_path.write_bytes((run_root / original.relative_path).read_bytes())
    duplicate = original.model_copy(
        update={
            "logical_name": "validation-metrics-duplicate",
            "relative_path": duplicate_relative,
        }
    )
    duplicated = evidence.model_copy(
        update={"artifacts": (*evidence.artifacts, duplicate)}
    )

    selected, metrics_by_checkpoint = handoff._recompute_checkpoint_selection(
        run_root,
        duplicated,
        fixture.contract.validation_snapshot,
    )

    assert selected.selected_step == evidence.selected_checkpoint.optimizer_step
    selected_metrics = metrics_by_checkpoint[
        (selected.selected_step, selected.selected_artifact_identity)
    ]
    legacy = duplicated.model_copy(
        update={
            "validation_metrics": handoff._legacy_phobert_run_metric_summary(
                selected_metrics
            )
        }
    )
    assert handoff._run_metric_summary_matches(legacy, selected_metrics)
    tampered = legacy.model_copy(
        update={
            "validation_metrics": {
                **legacy.validation_metrics,
                "macro_f1": legacy.validation_metrics["macro_f1"] - 0.01,
            }
        }
    )
    assert not handoff._run_metric_summary_matches(tampered, selected_metrics)


def test_local_comparison_needs_no_colab_package_approval(
    tmp_path, monkeypatch
):
    fixture = _build_comparison_fixture(tmp_path, monkeypatch)
    local_return = ColabOperatorReturn(
        bundle_roots=fixture.operator_return.bundle_roots,
        gpu_identities=fixture.operator_return.gpu_identities,
    )
    artifacts = finalize_phase40_comparison(
        fixture.request,
        local_return,
        repo_root=fixture.repo,
        scope_amendment_path=fixture.scope_amendment_path,
        output_root=fixture.output_root,
        renderer=_fixture_renderer,
        renderer_name="matplotlib",
        renderer_version="3.11.1",
    )
    assert artifacts.manifest.status == "complete"
    assert artifacts.manifest.package_decisions == ()
    assert len(artifacts.prediction_bundles) == 2


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
    target = fixture.repo / FIXED_RETURNED_ROOTS[1] / relative_path
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
        "qwen-qlora",
        "phobert",
    )
    assert by_id["qwen-qlora"].safety_gate_passed is False
    assert by_id["qwen-qlora"].comparison_eligible is True
    assert by_id["qwen-qlora"].risky_recall_by_label["bank_impersonation"] == 0.0
    assert artifacts.manifest.quality_comparison_admissible is False
    assert artifacts.manifest.speed_comparison_admissible is False
    assert "qwen-qlora" in artifacts.report_path.read_text(encoding="utf-8")


def _fixture_human_review_rows(
    comparison: ComparisonArtifacts,
) -> tuple[tuple[ReviewQueueRow, ...], tuple[ReviewerReturnRow, ...], bytes]:
    assert comparison.review_queue_path is not None
    queue = tuple(
        ReviewQueueRow.model_validate_json(line)
        for line in comparison.review_queue_path.read_text(
            encoding="utf-8"
        ).splitlines()
    )
    reviews = tuple(_review_return(row) for row in queue)
    return queue, reviews, _reviewer_return_bytes(reviews)


def _finalize_fixture_human_review(
    fixture: _ComparisonFixture,
    comparison: ComparisonArtifacts,
    *,
    output_root: Path,
    queue_bytes: bytes | None = None,
    reviewer_return_bytes: bytes | None = None,
):
    queue, reviews, canonical_review_bytes = _fixture_human_review_rows(comparison)
    assert comparison.review_queue_path is not None
    assert comparison.review_queue_manifest_path is not None
    return finalize_phase40_human_review(
        queue,
        reviews,
        request=fixture.request,
        repo_root=fixture.repo,
        contract=fixture.contract,
        prediction_bundles=comparison.prediction_bundles,
        queue_manifest_path=comparison.review_queue_manifest_path,
        comparison_manifest_path=comparison.manifest_path,
        scope_amendment_path=fixture.scope_amendment_path,
        output_root=output_root,
        queue_bytes=(
            comparison.review_queue_path.read_bytes()
            if queue_bytes is None
            else queue_bytes
        ),
        reviewer_return_bytes=(
            canonical_review_bytes
            if reviewer_return_bytes is None
            else reviewer_return_bytes
        ),
        vietnamese_fluent_attestation=True,
    )


def test_human_review_rejects_noncanonical_exact_queue_bytes(
    tmp_path,
    monkeypatch,
):
    fixture = _build_comparison_fixture(tmp_path, monkeypatch)
    comparison = _finalize_fixture_comparison(fixture)
    assert comparison.review_queue_path is not None
    original = comparison.review_queue_path.read_bytes()
    noncanonical = b" " + original

    with pytest.raises(ValueError, match="review-queue bytes are not canonical"):
        _finalize_fixture_human_review(
            fixture,
            comparison,
            output_root=tmp_path / "noncanonical-queue",
            queue_bytes=noncanonical,
        )


def _write_mutated_comparison(
    comparison: ComparisonArtifacts,
    payload: dict[str, object],
) -> None:
    import src.model_adaptation.phase40_handoff as handoff

    manifest = handoff.Phase40ComparisonManifest.model_validate(payload)
    comparison.manifest_path.write_bytes(
        handoff._canonical_json_bytes(manifest.model_dump(mode="json"))
    )
    comparison.report_path.write_bytes(handoff._comparison_report(manifest))


def test_human_review_rejects_duplicate_key_in_exact_reviewer_return_bytes(
    tmp_path,
    monkeypatch,
):
    fixture = _build_comparison_fixture(tmp_path, monkeypatch)
    comparison = _finalize_fixture_comparison(fixture)
    _, _, original = _fixture_human_review_rows(comparison)
    duplicated = original.replace(
        b'"assessment":"prediction_supported"',
        b'"assessment":"prediction_supported","assessment":"ambiguous"',
        1,
    )
    assert duplicated != original

    with pytest.raises(ValueError, match="fail schema validation"):
        _finalize_fixture_human_review(
            fixture,
            comparison,
            output_root=tmp_path / "duplicate-review-key",
            reviewer_return_bytes=duplicated,
        )


@pytest.mark.parametrize("field", ("review_queue_rows", "review_queue_sha256"))
def test_human_review_rejects_comparison_queue_identity_drift_with_matching_report(
    tmp_path,
    monkeypatch,
    field: str,
):
    fixture = _build_comparison_fixture(tmp_path, monkeypatch)
    comparison = _finalize_fixture_comparison(fixture)
    payload = comparison.manifest.model_dump(mode="json")
    payload[field] = (
        payload["review_queue_rows"] + 1
        if field == "review_queue_rows"
        else "0" * 64
    )
    _write_mutated_comparison(comparison, payload)

    with pytest.raises(ValueError, match="queue differs from the frozen comparison"):
        _finalize_fixture_human_review(
            fixture,
            comparison,
            output_root=tmp_path / f"comparison-{field}-drift",
        )


def test_human_review_rejects_reviewer_template_hash_drift(tmp_path, monkeypatch):
    fixture = _build_comparison_fixture(tmp_path, monkeypatch)
    comparison = _finalize_fixture_comparison(fixture)
    assert comparison.review_queue_manifest_path is not None
    queue_manifest_path = comparison.review_queue_manifest_path
    payload = json.loads(queue_manifest_path.read_text(encoding="utf-8"))
    payload["reviewer_template_sha256"] = "0" * 64
    queue_manifest_path.write_bytes(
        (
            json.dumps(
                payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        ).encode("utf-8")
    )

    with pytest.raises(ValueError, match="review queue provenance differs"):
        _finalize_fixture_human_review(
            fixture,
            comparison,
            output_root=tmp_path / "template-hash-drift",
        )


@pytest.mark.parametrize(
    "field",
    (
        "source_archive_sha256",
        "source_inventory_sha256",
        "input_archive_sha256",
        "input_manifest_sha256",
        "validation_rows",
        "hardware_confounded",
        "lora_probe",
        "limitations",
    ),
)
def test_human_review_rejects_comparison_provenance_drift_with_matching_report(
    tmp_path,
    monkeypatch,
    field: str,
):
    fixture = _build_comparison_fixture(tmp_path, monkeypatch)
    comparison = _finalize_fixture_comparison(fixture)
    payload = comparison.manifest.model_dump(mode="json")
    if field in {
        "source_archive_sha256",
        "source_inventory_sha256",
        "input_archive_sha256",
        "input_manifest_sha256",
    }:
        payload[field] = "0" * 64
    elif field == "validation_rows":
        payload[field] = payload[field] + 1
    elif field == "hardware_confounded":
        payload[field] = not payload[field]
    elif field == "lora_probe":
        payload[field]["peak_device_vram_used_mib"] += 1.0
    else:
        payload[field].append("unexpected_unfrozen_limitation")
    _write_mutated_comparison(comparison, payload)

    with pytest.raises(ValueError, match="provenance differs from live frozen authorities"):
        _finalize_fixture_human_review(
            fixture,
            comparison,
            output_root=tmp_path / f"comparison-{field}-provenance-drift",
        )


def test_human_review_rejects_live_run_evidence_trailing_byte_drift(
    tmp_path,
    monkeypatch,
):
    fixture = _build_comparison_fixture(tmp_path, monkeypatch)
    comparison = _finalize_fixture_comparison(fixture)
    evidence_path = fixture.repo / FIXED_RETURNED_ROOTS[1] / "run-evidence.json"
    evidence_path.write_bytes(evidence_path.read_bytes() + b" ")

    with pytest.raises(ValueError, match="run-evidence hash drifted"):
        _finalize_fixture_human_review(
            fixture,
            comparison,
            output_root=tmp_path / "run-evidence-byte-drift",
        )


def test_selected_prediction_bundle_loader_parses_qwen_and_phobert_payloads(
    tmp_path,
    monkeypatch,
):
    from src.model_adaptation.phase40_handoff import (
        load_phase40_selected_prediction_bundles,
    )

    fixture = _build_comparison_fixture(tmp_path, monkeypatch)
    comparison = _finalize_fixture_comparison(fixture)
    assert comparison.selected_prediction_bundles_path is not None
    selected_path = comparison.selected_prediction_bundles_path
    raw_payload = json.loads(selected_path.read_text(encoding="utf-8"))
    qwen_rows = raw_payload[0]["predictions"]
    phobert_rows = raw_payload[1]["predictions"]
    assert json.loads(qwen_rows[0]["raw_prediction"])["label"] in LABEL_ORDER
    assert qwen_rows[0]["decoder"] == {
        "do_sample": False,
        "max_new_tokens": 256,
        "num_return_sequences": 1,
    }
    assert len(phobert_rows[0]["logits"]) == len(LABEL_ORDER)
    assert phobert_rows[0]["argmax_state"] in LABEL_ORDER

    loaded = load_phase40_selected_prediction_bundles(
        selected_path,
        comparison_manifest=comparison.manifest,
    )
    assert loaded == comparison.prediction_bundles
    assert tuple(bundle.model_run_id for bundle in loaded) == (
        "qwen-qlora",
        "phobert",
    )


def test_selected_prediction_bundle_loader_rejects_duplicate_and_noncanonical_bytes(
    tmp_path,
    monkeypatch,
):
    from src.model_adaptation.phase40_handoff import (
        load_phase40_selected_prediction_bundles,
    )

    fixture = _build_comparison_fixture(tmp_path, monkeypatch)
    comparison = _finalize_fixture_comparison(fixture)
    assert comparison.selected_prediction_bundles_path is not None
    original = comparison.selected_prediction_bundles_path.read_bytes()

    duplicate = original.replace(
        b'"model_run_id":"qwen-qlora"',
        b'"model_run_id":"qwen-qlora","model_run_id":"qwen-qlora"',
        1,
    )
    assert duplicate != original
    duplicate_path = tmp_path / "selected-predictions-duplicate.json"
    duplicate_path.write_bytes(duplicate)
    duplicate_manifest = comparison.manifest.model_copy(
        update={
            "selected_prediction_bundles_sha256": hashlib.sha256(duplicate).hexdigest()
        }
    )
    with pytest.raises(ValueError, match="strict duplicate-free JSON"):
        load_phase40_selected_prediction_bundles(
            duplicate_path,
            comparison_manifest=duplicate_manifest,
        )

    noncanonical = b" " + original
    noncanonical_path = tmp_path / "selected-predictions-noncanonical.json"
    noncanonical_path.write_bytes(noncanonical)
    noncanonical_manifest = comparison.manifest.model_copy(
        update={
            "selected_prediction_bundles_sha256": hashlib.sha256(
                noncanonical
            ).hexdigest()
        }
    )
    with pytest.raises(ValueError, match="not canonical JSON"):
        load_phase40_selected_prediction_bundles(
            noncanonical_path,
            comparison_manifest=noncanonical_manifest,
        )


def _upgrade_fixture_manifest_to_v3(
    manifest: Phase40ComparisonManifest,
) -> dict[str, object]:
    payload = manifest.model_dump(mode="json")
    payload["schema_version"] = "phase40-comparison-v3"
    payload["source_archive_sha256"] = None
    payload["source_inventory_sha256"] = None
    payload["superseded_scope_amendment_sha256"] = payload[
        "scope_amendment_sha256"
    ]
    payload["final_comparison_authority_sha256"] = "1" * 64
    for index, run in enumerate(payload["runs"]):
        run["origin_request_sha256"] = f"{index + 2:x}" * 64
        run["source_archive_sha256"] = f"{index + 4:x}" * 64
        run["source_inventory_sha256"] = f"{index + 6:x}" * 64
        run["control_template_sha256"] = f"{index + 8:x}" * 64
    payload["request_sha256_by_run"] = {
        run["run_id"]: run["origin_request_sha256"] for run in payload["runs"]
    }
    payload["source_archive_sha256_by_run"] = {
        run["run_id"]: run["source_archive_sha256"] for run in payload["runs"]
    }
    payload["source_inventory_sha256_by_run"] = {
        run["run_id"]: run["source_inventory_sha256"] for run in payload["runs"]
    }
    payload["comparison_launch_receipt_sha256"] = "a" * 64
    payload["qwen_gguf_verification_receipt_sha256"] = "b" * 64
    payload["phobert_release_receipt_authority_sha256"] = "c" * 64
    payload["phobert_segmenter_authority_sha256"] = "d" * 64
    payload["runtime_dependency_authority_sha256"] = "e" * 64
    payload["runtime_materialization_receipt_sha256"] = "f" * 64
    payload["production_authority_verification_mode"] = "portable_receipts_only"
    return payload


def test_comparison_v3_requires_per_run_origins_and_production_closure(
    tmp_path,
    monkeypatch,
):
    fixture = _build_comparison_fixture(tmp_path, monkeypatch)
    legacy = _finalize_fixture_comparison(fixture).manifest
    payload = _upgrade_fixture_manifest_to_v3(legacy)
    upgraded = Phase40ComparisonManifest.model_validate(payload)
    assert upgraded.schema_version == "phase40-comparison-v3"
    assert upgraded.source_archive_sha256 is None
    assert tuple(upgraded.request_sha256_by_run) == tuple(
        run.run_id for run in upgraded.runs
    )
    report = _comparison_report(upgraded).decode("utf-8")
    assert upgraded.runtime_materialization_receipt_sha256 in report
    assert "did not perform live runtime recapture" in report

    payload["request_sha256_by_run"][payload["runs"][1]["run_id"]] = "f" * 64
    with pytest.raises(ValueError, match="run provenance differs"):
        Phase40ComparisonManifest.model_validate(payload)


def test_comparison_v3_requires_runtime_materialization_receipt(
    tmp_path,
    monkeypatch,
):
    fixture = _build_comparison_fixture(tmp_path, monkeypatch)
    payload = _upgrade_fixture_manifest_to_v3(
        _finalize_fixture_comparison(fixture).manifest
    )
    payload["runtime_materialization_receipt_sha256"] = None

    with pytest.raises(ValueError, match="complete portable receipt closure"):
        Phase40ComparisonManifest.model_validate(payload)


def test_comparison_v3_rejects_one_global_source_authority(tmp_path, monkeypatch):
    fixture = _build_comparison_fixture(tmp_path, monkeypatch)
    payload = _upgrade_fixture_manifest_to_v3(
        _finalize_fixture_comparison(fixture).manifest
    )
    payload["source_archive_sha256"] = "f" * 64
    with pytest.raises(ValueError, match="per-run source authorities"):
        Phase40ComparisonManifest.model_validate(payload)


@pytest.mark.parametrize(
    ("field_name", "field_value"),
    (
        ("superseded_scope_amendment_sha256", "1" * 64),
        ("final_comparison_authority_sha256", "2" * 64),
        ("request_sha256_by_run", {"qwen-qlora": "3" * 64}),
        ("source_archive_sha256_by_run", {"qwen-qlora": "4" * 64}),
        ("source_inventory_sha256_by_run", {"qwen-qlora": "5" * 64}),
        ("comparison_launch_receipt_sha256", "6" * 64),
        ("qwen_gguf_verification_receipt_sha256", "7" * 64),
        ("phobert_release_receipt_authority_sha256", "8" * 64),
        ("phobert_segmenter_authority_sha256", "9" * 64),
        ("runtime_dependency_authority_sha256", "a" * 64),
        ("runtime_materialization_receipt_sha256", "b" * 64),
        ("production_authority_verification_mode", "portable_receipts_only"),
    ),
)
def test_comparison_v2_rejects_every_v3_only_manifest_field(
    tmp_path,
    monkeypatch,
    field_name,
    field_value,
):
    fixture = _build_comparison_fixture(tmp_path, monkeypatch)
    payload = _finalize_fixture_comparison(fixture).manifest.model_dump(mode="json")
    payload[field_name] = field_value

    with pytest.raises(ValueError, match="v3-only authority fields"):
        Phase40ComparisonManifest.model_validate(payload)


@pytest.mark.parametrize(
    "field_name",
    (
        "origin_request_sha256",
        "source_archive_sha256",
        "source_inventory_sha256",
        "control_template_sha256",
    ),
)
def test_comparison_v2_rejects_v3_only_run_origins(
    tmp_path,
    monkeypatch,
    field_name,
):
    fixture = _build_comparison_fixture(tmp_path, monkeypatch)
    payload = _finalize_fixture_comparison(fixture).manifest.model_dump(mode="json")
    payload["runs"][0][field_name] = "c" * 64

    with pytest.raises(ValueError, match="v3-only authority fields"):
        Phase40ComparisonManifest.model_validate(payload)


def test_comparison_v3_rejects_historical_prestart_failed_contract(
    tmp_path,
    monkeypatch,
):
    fixture = _build_comparison_fixture(tmp_path, monkeypatch)
    payload = _upgrade_fixture_manifest_to_v3(
        _finalize_fixture_comparison(fixture).manifest
    )
    payload.update(
        status="prestart_failed",
        runs=[],
        quality_comparison_admissible=False,
        hardware_confounded=None,
        review_queue_rows=0,
        review_queue_sha256=None,
        selected_prediction_bundles_sha256=None,
        failure_reason="synthetic pre-start failure",
    )

    with pytest.raises(ValueError, match="v3 comparison cannot use"):
        Phase40ComparisonManifest.model_validate(payload)


def test_comparison_v2_prestart_rejects_v3_only_authority_fields(
    tmp_path,
    monkeypatch,
):
    fixture = _build_comparison_fixture(tmp_path, monkeypatch)
    payload = _finalize_fixture_comparison(fixture).manifest.model_dump(mode="json")
    payload.update(
        status="prestart_failed",
        runs=[],
        quality_comparison_admissible=False,
        hardware_confounded=None,
        review_queue_rows=0,
        review_queue_sha256=None,
        selected_prediction_bundles_sha256=None,
        failure_reason="synthetic historical pre-start failure",
        runtime_materialization_receipt_sha256="d" * 64,
        production_authority_verification_mode="portable_receipts_only",
    )

    with pytest.raises(ValueError, match="v3-only authority fields"):
        Phase40ComparisonManifest.model_validate(payload)


def test_final_comparison_rejects_caller_authored_authority_mapping() -> None:
    with pytest.raises(TypeError, match="fixed receipt loader"):
        _phase40_production_authority_values(
            {"verification_mode": "portable_receipts_only"}
        )
