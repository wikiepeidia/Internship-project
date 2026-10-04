"""Explanation rubric and manual review pack tests for Phase 5."""

from __future__ import annotations

from pathlib import Path

from src.model_adaptation.explanation_review import build_manual_review_pack, score_explanation_rubric
from src.model_adaptation.schemas import (
    LOCKED_RELEASE_LABELS,
    HeldOutSupportAudit,
    OverallMetricSummary,
    PerLabelMetricRow,
    ReleaseEvaluationRow,
    ReleaseEvaluationSnapshot,
)
from src.runtime.contracts import SuspiciousCue


def _build_row(
    gold_label: str,
    predicted_labels: list[str],
    *,
    risk_tier: str,
    reviewable_source_text: str,
    cue_type: str = "otp_request",
    cue_span: str = "OTP",
    recommendations: list[str] | None = None,
) -> ReleaseEvaluationRow:
    return ReleaseEvaluationRow(
        gold_label=gold_label,
        predicted_labels=predicted_labels,
        risk_tier=risk_tier,
        summary="Tom tat du de hop le cho danh gia giai thich Phase 5.",
        top_cues=[SuspiciousCue(span=cue_span, reason="Ly do danh gia dau hieu bat thuong", cue_type=cue_type)],
        recommendations=recommendations or ["Khong chia se OTP cho nguoi gui tin nhan."],
        backend_name="fake-runtime",
        split_provenance="data/splits/val.jsonl",
        reviewable_source_text=reviewable_source_text,
    )


def _build_snapshot(rows: list[ReleaseEvaluationRow]) -> ReleaseEvaluationSnapshot:
    audit = HeldOutSupportAudit(
        evaluated_split_path=Path("data/splits/val.jsonl"),
        support_by_label={label: 1 for label in LOCKED_RELEASE_LABELS},
        blocker_reasons=[],
    )
    return ReleaseEvaluationSnapshot(
        run_id="phase5-run-001",
        evaluated_split_path=Path("data/splits/val.jsonl"),
        audit=audit,
        overall_metrics=OverallMetricSummary(macro_f1=0.8, weighted_f1=0.9, evaluated_rows=len(rows)),
        per_label_metrics=[
            PerLabelMetricRow(label=label, precision=1.0, recall=1.0, f1=1.0, support=1)
            for label in LOCKED_RELEASE_LABELS
        ],
        rows=rows,
    )


def test_explanation_rubric_scopes_to_risky_predictions_only():
    benign_row = _build_row(
        "benign",
        ["benign"],
        risk_tier="benign",
        reviewable_source_text="Hen gap ban vao luc 3 gio chieu mai nhe.",
        cue_span="3 gio",
        cue_type="generic",
        recommendations=["Khong co hanh dong nguy hiem duoc de xuat."],
    )
    risky_row = _build_row(
        "bank_impersonation",
        ["bank_impersonation"],
        risk_tier="high-risk",
        reviewable_source_text="VPBank yeu cau OTP de xac minh giao dich.",
    )

    benign_assessment = score_explanation_rubric(benign_row)
    risky_assessment = score_explanation_rubric(risky_row)

    assert benign_assessment.applies is False
    assert benign_assessment.blocker_reasons == []
    assert benign_assessment.flag_reasons == []
    assert risky_assessment.applies is True


def test_explanation_rubric_blocks_unsafe_recommendations_or_fabricated_evidence():
    risky_row = _build_row(
        "bank_impersonation",
        ["bank_impersonation"],
        risk_tier="high-risk",
        reviewable_source_text="VPBank yeu cau xac minh giao dich ngay.",
        cue_span="OTP",
        recommendations=["Hay bam vao lien ket de xac minh OTP ngay."],
    )

    assessment = score_explanation_rubric(risky_row)

    assert any("fabricated evidence" in reason.casefold() for reason in assessment.blocker_reasons)
    assert any("unsafe recommendation" in reason.casefold() for reason in assessment.blocker_reasons)


def test_explanation_rubric_flags_label_alignment_without_blocking():
    risky_row = _build_row(
        "bank_impersonation",
        ["bank_impersonation"],
        risk_tier="high-risk",
        reviewable_source_text="Thong bao chung chung ve tai khoan cua ban.",
        cue_span="tai khoan",
        cue_type="generic",
        recommendations=["Neu can, hay tu xac minh qua kenh chinh thuc."],
    )

    assessment = score_explanation_rubric(risky_row)

    assert assessment.blocker_reasons == []
    assert any("label alignment" in reason.casefold() for reason in assessment.flag_reasons)


def test_manual_review_pack_selects_risky_predictions_only():
    snapshot = _build_snapshot(
        [
            _build_row(
                "benign",
                ["benign"],
                risk_tier="benign",
                reviewable_source_text="Hen gap ban vao luc 3 gio chieu mai nhe.",
                cue_span="3 gio",
                cue_type="generic",
                recommendations=["Khong co hanh dong nguy hiem duoc de xuat."],
            ),
            _build_row(
                "bank_impersonation",
                ["bank_impersonation"],
                risk_tier="high-risk",
                reviewable_source_text="VPBank yeu cau OTP de xac minh giao dich.",
            ),
            _build_row(
                "task_scam",
                ["task_scam"],
                risk_tier="high-risk",
                reviewable_source_text="Cong viec online luong cao, nop phi kich hoat ngay.",
                cue_type="job_offer",
                cue_span="luong cao",
            ),
        ]
    )

    pack = build_manual_review_pack(snapshot, snapshot_path=Path("data/splits/val.jsonl"))

    assert len(pack.items) == 2
    assert all(item.risk_tier != "benign" for item in pack.items)
    assert all(item.reviewable_text for item in pack.items)
    assert all(hasattr(item, "reviewer_blocker_reasons") for item in pack.items)


def test_manual_review_pack_is_deterministic_for_same_inputs():
    snapshot = _build_snapshot(
        [
            _build_row(
                "task_scam",
                ["task_scam"],
                risk_tier="high-risk",
                reviewable_source_text="Cong viec online luong cao, nop phi kich hoat ngay.",
                cue_type="job_offer",
                cue_span="luong cao",
            ),
            _build_row(
                "bank_impersonation",
                ["bank_impersonation"],
                risk_tier="high-risk",
                reviewable_source_text="VPBank yeu cau OTP de xac minh giao dich.",
            ),
        ]
    )

    first_pack = build_manual_review_pack(snapshot, snapshot_path=Path("data/splits/val.jsonl"), sample_size=1)
    second_pack = build_manual_review_pack(snapshot, snapshot_path=Path("data/splits/val.jsonl"), sample_size=1)

    assert first_pack.model_dump() == second_pack.model_dump()