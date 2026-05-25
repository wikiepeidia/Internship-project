"""Final release-gate synthesis tests for Phase 5."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.model_adaptation.release_gates import synthesize_release_verdict, write_release_artifacts
from src.model_adaptation.schemas import (
    ExplanationReviewItem,
    ExplanationReviewPack,
    ExplanationRubricSummary,
    HeldOutSupportAudit,
    LOCKED_RELEASE_LABELS,
    OverallMetricSummary,
    PerLabelMetricRow,
    ReleaseEvaluationArtifact,
    ReleaseEvaluationSnapshot,
    ReleaseEvaluationRow,
)
from src.runtime.contracts import SuspiciousCue


def _build_snapshot(*, bank_recall: float = 1.0, bank_support: int = 1, audit_blockers: list[str] | None = None) -> ReleaseEvaluationSnapshot:
    audit = HeldOutSupportAudit(
        evaluated_split_path=Path("data/splits/val.jsonl"),
        support_by_label={
            "bank_impersonation": bank_support,
            "zalo_social_engineering": 1,
            "task_scam": 1,
            "benign": 1,
        },
        blocker_reasons=audit_blockers or [],
    )
    rows = [
        ReleaseEvaluationRow(
            gold_label="bank_impersonation",
            predicted_labels=["bank_impersonation"],
            risk_tier="high-risk",
            summary="Tin nhan gia danh ngan hang va yeu cau OTP.",
            top_cues=[SuspiciousCue(span="OTP", reason="Tin nhan nhac ma OTP", cue_type="otp_request")],
            recommendations=["Khong chia se OTP cho nguoi gui tin nhan."],
            backend_name="fake-runtime",
            split_provenance="data/splits/val.jsonl",
            reviewable_source_text="VPBank yeu cau OTP de xac minh giao dich.",
        )
    ]
    per_label_metrics = [
        PerLabelMetricRow(
            label="bank_impersonation",
            precision=1.0,
            recall=bank_recall,
            f1=bank_recall,
            support=bank_support,
        ),
        PerLabelMetricRow(label="zalo_social_engineering", precision=1.0, recall=1.0, f1=1.0, support=1),
        PerLabelMetricRow(label="task_scam", precision=1.0, recall=1.0, f1=1.0, support=1),
        PerLabelMetricRow(label="benign", precision=1.0, recall=1.0, f1=1.0, support=1),
    ]
    return ReleaseEvaluationSnapshot(
        run_id="phase5-run-001",
        evaluated_split_path=Path("data/splits/val.jsonl"),
        audit=audit,
        overall_metrics=OverallMetricSummary(macro_f1=0.8, weighted_f1=0.85, evaluated_rows=len(rows)),
        per_label_metrics=per_label_metrics,
        rows=rows,
    )


def _build_review_pack(*, run_id: str = "phase5-run-001", review_completed: bool = True, reviewer_flags: list[str] | None = None) -> ExplanationReviewPack:
    return ExplanationReviewPack(
        run_id=run_id,
        source_snapshot_path=Path(".planning/phases/05-recall-priority-evaluation-and-release-gates/05-evaluation-snapshot.json"),
        items=[
            ExplanationReviewItem(
                row_index=0,
                gold_label="bank_impersonation",
                predicted_labels=["bank_impersonation"],
                risk_tier="high-risk",
                reviewable_text="VPBank yeu cau OTP de xac minh giao dich.",
                top_cues=[SuspiciousCue(span="OTP", reason="Tin nhan nhac ma OTP", cue_type="otp_request")],
                recommendations=["Khong chia se OTP cho nguoi gui tin nhan."],
                deterministic_blocker_reasons=[],
                deterministic_flag_reasons=[],
                reviewer_blocker_reasons=[],
                reviewer_flag_reasons=reviewer_flags or [],
            )
        ],
        review_completed=review_completed,
        review_notes="approved" if review_completed else None,
    )


def test_release_gate_blocks_on_zero_support_or_recall_floor_miss():
    zero_support_snapshot = _build_snapshot(bank_support=0, audit_blockers=["Missing support for risky label bank_impersonation"])
    review_pack = _build_review_pack()
    zero_support_artifact = synthesize_release_verdict(zero_support_snapshot, review_pack)

    recall_miss_snapshot = _build_snapshot(bank_recall=0.5)
    recall_miss_artifact = synthesize_release_verdict(recall_miss_snapshot, review_pack)

    assert zero_support_artifact.verdict == "BLOCK"
    assert any("Missing support" in reason for reason in zero_support_artifact.blocker_reasons)
    assert recall_miss_artifact.verdict == "BLOCK"
    assert any("below required floor" in reason for reason in recall_miss_artifact.blocker_reasons)


def test_release_gate_flags_nonblocking_explanation_issues():
    snapshot = _build_snapshot()
    review_pack = _build_review_pack(reviewer_flags=["One risky prediction used generic safe advice."])

    artifact = synthesize_release_verdict(snapshot, review_pack)

    assert artifact.verdict == "FLAG"
    assert artifact.blocker_reasons == []
    assert artifact.flag_reasons == ["One risky prediction used generic safe advice."]


    def test_release_gate_rejects_incomplete_or_mismatched_review_pack():
        snapshot = _build_snapshot()

        with pytest.raises(ValueError, match="incomplete"):
            synthesize_release_verdict(snapshot, _build_review_pack(review_completed=False))

        with pytest.raises(ValueError, match="run_id"):
            synthesize_release_verdict(snapshot, _build_review_pack(run_id="phase5-run-999"))


def test_release_artifact_includes_metrics_reasons_and_rubric_summary(tmp_path: Path):
    snapshot = _build_snapshot()
    review_pack = _build_review_pack(reviewer_flags=["One risky prediction used generic safe advice."])
    artifact = synthesize_release_verdict(snapshot, review_pack)

    markdown_path, json_path = write_release_artifacts(
        artifact,
        report_dir=tmp_path / "phase",
        manifest_dir=tmp_path / "manifests",
    )

    assert isinstance(artifact, ReleaseEvaluationArtifact)
    assert markdown_path.exists()
    assert json_path.exists()
    assert "macro_f1" in markdown_path.read_text(encoding="utf-8")
    assert "One risky prediction used generic safe advice." in markdown_path.read_text(encoding="utf-8")
    assert artifact.explanation_rubric_summary == ExplanationRubricSummary(
        evaluated_risky_predictions=1,
        manual_reviewed_predictions=1,
        blocker_reasons=[],
        flag_reasons=["One risky prediction used generic safe advice."],
    )