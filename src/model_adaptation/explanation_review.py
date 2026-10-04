"""Risky-only explanation rubric scoring and manual review pack generation for Phase 5."""

from __future__ import annotations

from pathlib import Path

from src.model_adaptation.schemas import (
    LOCKED_RISKY_LABELS,
    ExplanationReviewItem,
    ExplanationReviewPack,
    ExplanationRubricAssessment,
    ReleaseEvaluationRow,
    ReleaseEvaluationSnapshot,
)
from src.runtime.analyzers.local_model import (
    DEFAULT_RISKY_RECOMMENDATIONS,
    cue_span_is_grounded,
    is_recommendation_safe,
)


LABEL_ALIGNMENT_CUE_TYPES: dict[str, set[str]] = {
    "bank_impersonation": {"otp_request", "url", "spoofed_brand", "credential_request", "payment_request"},
    "zalo_social_engineering": {"contact_takeover", "urgency"},
    "task_scam": {"job_offer", "payment_request", "urgency"},
}
LABEL_ALIGNMENT_TEXT_MARKERS: dict[str, tuple[str, ...]] = {
    "bank_impersonation": ("otp", "ngan hang", "bank", "http", "https"),
    "zalo_social_engineering": ("zalo", "nguoi quen", "tai khoan bi chiem"),
    "task_scam": ("luong cao", "hoa hong", "phi kich hoat", "nhiem vu", "cong viec online"),
}


def _row_is_risky(row: ReleaseEvaluationRow) -> bool:
    return row.risk_tier != "benign" or any(label in LOCKED_RISKY_LABELS for label in row.predicted_labels)


def _reviewable_text(row: ReleaseEvaluationRow) -> str:
    return row.reviewable_source_text or row.normalized_text or ""


def _dedupe_preserve_order(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))


def _has_label_alignment_signal(row: ReleaseEvaluationRow, reference_text: str) -> bool:
    cue_types = {cue.cue_type for cue in row.top_cues if cue.cue_type}
    lowered_text = reference_text.casefold()

    for label in row.predicted_labels:
        if label == "benign":
            continue
        allowed_cue_types = LABEL_ALIGNMENT_CUE_TYPES.get(label, set())
        if cue_types & allowed_cue_types:
            continue
        markers = LABEL_ALIGNMENT_TEXT_MARKERS.get(label, ())
        if any(marker in lowered_text for marker in markers):
            continue
        return False
    return True


def _uses_generic_safe_advice(row: ReleaseEvaluationRow) -> bool:
    return bool(row.recommendations) and all(text in DEFAULT_RISKY_RECOMMENDATIONS for text in row.recommendations)


def score_explanation_rubric(row: ReleaseEvaluationRow) -> ExplanationRubricAssessment:
    """Score one release-evaluation row with a risky-only explanation rubric."""

    if not _row_is_risky(row):
        return ExplanationRubricAssessment(applies=False)

    reference_text = _reviewable_text(row)
    blocker_reasons: list[str] = []
    flag_reasons: list[str] = []

    if not row.top_cues:
        flag_reasons.append("Grounding flag: risky prediction did not surface any reviewable cues.")

    for cue in row.top_cues:
        if not cue_span_is_grounded(reference_text, cue.span):
            blocker_reasons.append(
                f"Fabricated evidence blocker: cue span '{cue.span}' was not found in the reviewable text."
            )

    for recommendation in row.recommendations:
        if not is_recommendation_safe(recommendation):
            blocker_reasons.append(f"Unsafe recommendation blocker: {recommendation}")

    if not _has_label_alignment_signal(row, reference_text):
        flag_reasons.append("Label alignment flag: predicted labels are weakly supported by the captured cues.")

    if _uses_generic_safe_advice(row):
        flag_reasons.append("Recommendation quality flag: explanation fell back to generic safe advice.")

    return ExplanationRubricAssessment(
        applies=True,
        blocker_reasons=_dedupe_preserve_order(blocker_reasons),
        flag_reasons=_dedupe_preserve_order(flag_reasons),
    )


def build_manual_review_pack(
    snapshot: ReleaseEvaluationSnapshot,
    *,
    snapshot_path: Path,
    sample_size: int | None = None,
) -> ExplanationReviewPack:
    """Select a deterministic risky-only subset from one saved evaluation snapshot."""

    indexed_risky_rows = [
        (index, row)
        for index, row in enumerate(snapshot.rows)
        if _row_is_risky(row)
    ]
    indexed_risky_rows.sort(
        key=lambda item: (
            item[1].gold_label,
            ",".join(item[1].predicted_labels),
            _reviewable_text(item[1]),
            item[0],
        )
    )
    if sample_size is not None:
        indexed_risky_rows = indexed_risky_rows[:sample_size]

    items: list[ExplanationReviewItem] = []
    for index, row in indexed_risky_rows:
        assessment = score_explanation_rubric(row)
        items.append(
            ExplanationReviewItem(
                row_index=index,
                gold_label=row.gold_label,
                predicted_labels=list(row.predicted_labels),
                risk_tier=row.risk_tier,
                reviewable_text=_reviewable_text(row),
                top_cues=list(row.top_cues),
                recommendations=list(row.recommendations),
                deterministic_blocker_reasons=list(assessment.blocker_reasons),
                deterministic_flag_reasons=list(assessment.flag_reasons),
                reviewer_blocker_reasons=[],
                reviewer_flag_reasons=[],
            )
        )

    return ExplanationReviewPack(
        run_id=snapshot.run_id,
        source_snapshot_path=snapshot_path,
        items=items,
        review_completed=False,
        review_notes=None,
    )