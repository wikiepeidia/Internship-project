"""Recall-first release verdict synthesis and artifact writers for Phase 5."""

from __future__ import annotations

from pathlib import Path

from src.model_adaptation.schemas import (
    LOCKED_RISKY_LABELS,
    ExplanationReviewPack,
    ExplanationRubricSummary,
    ReleaseEvaluationArtifact,
    ReleaseEvaluationSnapshot,
)


DEFAULT_PHASE_FIVE_REPORT_DIR = Path(".planning/phases/05-recall-priority-evaluation-and-release-gates")
DEFAULT_PHASE_FIVE_MANIFEST_DIR = Path("data/manifests")


def _dedupe_preserve_order(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))


def synthesize_release_verdict(
    snapshot: ReleaseEvaluationSnapshot,
    review_pack: ExplanationReviewPack,
) -> ReleaseEvaluationArtifact:
    """Merge readiness, metrics, and review findings into one canonical Phase 5 verdict."""

    if snapshot.run_id != review_pack.run_id:
        raise ValueError("Review pack run_id does not match the saved evaluation snapshot")
    if not review_pack.review_completed:
        raise ValueError("Explanation review pack is incomplete")

    blocker_reasons = list(snapshot.audit.blocker_reasons)
    flag_reasons: list[str] = []

    for metric_row in snapshot.per_label_metrics:
        if metric_row.label not in LOCKED_RISKY_LABELS:
            continue
        if metric_row.support == 0:
            blocker_reasons.append(
                f"Release blocker: {metric_row.label} has zero held-out support in the evaluated snapshot."
            )
            continue
        if metric_row.recall < snapshot.audit.risky_recall_floor:
            blocker_reasons.append(
                f"Release blocker: {metric_row.label} recall {metric_row.recall:.2f} is below required floor {snapshot.audit.risky_recall_floor:.2f}."
            )

    rubric_blockers: list[str] = []
    rubric_flags: list[str] = []
    for item in review_pack.items:
        rubric_blockers.extend(item.deterministic_blocker_reasons)
        rubric_blockers.extend(item.reviewer_blocker_reasons)
        rubric_flags.extend(item.deterministic_flag_reasons)
        rubric_flags.extend(item.reviewer_flag_reasons)

    blocker_reasons = _dedupe_preserve_order(blocker_reasons + rubric_blockers)
    flag_reasons = _dedupe_preserve_order(rubric_flags)

    verdict = "BLOCK" if blocker_reasons else "FLAG" if flag_reasons else "PASS"
    rubric_summary = ExplanationRubricSummary(
        evaluated_risky_predictions=len(review_pack.items),
        manual_reviewed_predictions=len(review_pack.items) if review_pack.review_completed else 0,
        blocker_reasons=_dedupe_preserve_order(rubric_blockers),
        flag_reasons=flag_reasons,
    )
    return ReleaseEvaluationArtifact(
        run_id=snapshot.run_id,
        verdict=verdict,
        risky_recall_floor=snapshot.audit.risky_recall_floor,
        overall_metrics=snapshot.overall_metrics,
        per_label_metrics=snapshot.per_label_metrics,
        blocker_reasons=blocker_reasons,
        flag_reasons=flag_reasons,
        explanation_rubric_summary=rubric_summary,
        readiness_audit=snapshot.audit,
    )


def write_release_artifacts(
    artifact: ReleaseEvaluationArtifact,
    *,
    report_dir: Path = DEFAULT_PHASE_FIVE_REPORT_DIR,
    manifest_dir: Path = DEFAULT_PHASE_FIVE_MANIFEST_DIR,
) -> tuple[Path, Path]:
    """Write the phase-local markdown report and machine-readable JSON artifact."""

    report_dir.mkdir(parents=True, exist_ok=True)
    manifest_dir.mkdir(parents=True, exist_ok=True)

    markdown_path = report_dir / f"05-release-eval-{artifact.run_id}.md"
    json_path = manifest_dir / f"phase5-release-eval-{artifact.run_id}.json"

    markdown_lines = [
        f"# Phase 5 Release Evaluation: {artifact.run_id}",
        "",
        f"- verdict: {artifact.verdict}",
        f"- risky_recall_floor: {artifact.risky_recall_floor}",
        f"- macro_f1: {artifact.overall_metrics.macro_f1}",
        f"- weighted_f1: {artifact.overall_metrics.weighted_f1}",
        f"- evaluated_rows: {artifact.overall_metrics.evaluated_rows}",
        "",
        "## Per-label metrics",
        "",
    ]
    for row in artifact.per_label_metrics:
        markdown_lines.append(
            f"- {row.label}: precision={row.precision} recall={row.recall} f1={row.f1} support={row.support}"
        )

    markdown_lines.extend(["", "## Blocker reasons", ""])
    if artifact.blocker_reasons:
        markdown_lines.extend(f"- {reason}" for reason in artifact.blocker_reasons)
    else:
        markdown_lines.append("- None")

    markdown_lines.extend(["", "## Flag reasons", ""])
    if artifact.flag_reasons:
        markdown_lines.extend(f"- {reason}" for reason in artifact.flag_reasons)
    else:
        markdown_lines.append("- None")

    markdown_lines.extend(
        [
            "",
            "## Explanation rubric summary",
            "",
            f"- evaluated_risky_predictions: {artifact.explanation_rubric_summary.evaluated_risky_predictions}",
            f"- manual_reviewed_predictions: {artifact.explanation_rubric_summary.manual_reviewed_predictions}",
        ]
    )
    if artifact.explanation_rubric_summary.blocker_reasons:
        markdown_lines.extend(
            f"- rubric_blocker: {reason}"
            for reason in artifact.explanation_rubric_summary.blocker_reasons
        )
    if artifact.explanation_rubric_summary.flag_reasons:
        markdown_lines.extend(
            f"- rubric_flag: {reason}"
            for reason in artifact.explanation_rubric_summary.flag_reasons
        )

    markdown_path.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")
    json_path.write_text(artifact.model_dump_json(indent=2), encoding="utf-8")
    return markdown_path, json_path