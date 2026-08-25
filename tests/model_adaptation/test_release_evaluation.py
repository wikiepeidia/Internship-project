"""Tests for the retired evaluator sentinel and reusable metric helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

import src.model_adaptation.release_evaluation as release_evaluation_module
from src.model_adaptation.release_evaluation import (
    _apply_recall_floor_to_audit,
    compute_release_metrics,
    evaluate_release_split,
)
from src.model_adaptation.schemas import (
    LOCKED_RELEASE_LABELS,
    HeldOutSupportAudit,
    PerLabelMetricRow,
    ReleaseEvaluationRow,
)
from src.runtime.contracts import SuspiciousCue


class _ExplodingPath:
    """A path-shaped sentinel that fails if the retired route inspects it."""

    def __fspath__(self) -> str:
        raise AssertionError("retired evaluator must not convert a path")

    def __str__(self) -> str:
        raise AssertionError("retired evaluator must not stringify a path")


@pytest.mark.parametrize(
    "alias_kind",
    [
        "canonical lexical spelling",
        "hardlink identity alias",
        "junction identity alias",
        "mapped-drive identity alias",
        "Volume-GUID identity alias",
        "device-namespace identity alias",
    ],
)
def test_retired_release_evaluator_rejects_every_identity_route_without_path_access(
    alias_kind: str,
):
    sentinel = _ExplodingPath()

    with pytest.raises(RuntimeError, match="phase41-run-once"):
        evaluate_release_split(
            sentinel,  # type: ignore[arg-type]
            audit=sentinel,  # type: ignore[arg-type]
            runtime_service=sentinel,
            analyze_text=sentinel,
            snapshot_path=sentinel,  # type: ignore[arg-type]
            run_id=alias_kind,
            progress_callback=sentinel,
            checkpoint_interval=1,
        )


def test_retired_release_evaluator_has_no_loader_or_runtime_import_surface():
    forbidden_names = {
        "audit_release_eval_support",
        "build_default_runtime_service",
        "load_split_records",
    }

    assert forbidden_names.isdisjoint(vars(release_evaluation_module))


def _build_row(gold_label: str, predicted_labels: list[str]) -> ReleaseEvaluationRow:
    return ReleaseEvaluationRow(
        gold_label=gold_label,
        predicted_labels=predicted_labels,
        risk_tier="benign" if gold_label == "benign" else "high-risk",
        summary="Tom tat du de hop le cho hang danh gia.",
        top_cues=[SuspiciousCue(span="OTP", reason="Tin nhan de cap ma xac thuc nhay cam")],
        recommendations=["Khong chuyen tien truoc khi xac minh."],
        backend_name="fake-runtime",
        split_provenance="synthetic-only.jsonl",
        reviewable_source_text="Tin nhan mau synthetic.",
    )


def _clean_audit() -> HeldOutSupportAudit:
    return HeldOutSupportAudit(
        evaluated_split_path=Path("synthetic-only.jsonl"),
        support_by_label={label: 10 for label in LOCKED_RELEASE_LABELS},
        blocker_reasons=[],
    )


def test_release_metrics_keep_zero_support_labels_visible():
    overall_metrics, per_label_metrics = compute_release_metrics(
        [
            _build_row("bank_impersonation", ["bank_impersonation"]),
            _build_row("benign", ["benign"]),
        ]
    )

    assert overall_metrics.evaluated_rows == 2
    assert [row.label for row in per_label_metrics] == list(LOCKED_RELEASE_LABELS)
    assert next(row for row in per_label_metrics if row.label == "zalo_social_engineering").support == 0
    assert next(row for row in per_label_metrics if row.label == "task_scam").support == 0


def test_release_metrics_report_macro_and_weighted_f1():
    overall_metrics, _ = compute_release_metrics(
        [
            _build_row("bank_impersonation", ["bank_impersonation"]),
            _build_row("benign", ["benign"]),
        ]
    )

    assert overall_metrics.macro_f1 == pytest.approx(0.5)
    assert overall_metrics.weighted_f1 == pytest.approx(1.0)


def test_release_metrics_preserve_multilabel_predictions():
    _, per_label_metrics = compute_release_metrics(
        [
            _build_row("bank_impersonation", ["task_scam", "bank_impersonation"]),
            _build_row("task_scam", ["task_scam"]),
        ]
    )

    bank_metrics = next(row for row in per_label_metrics if row.label == "bank_impersonation")
    task_metrics = next(row for row in per_label_metrics if row.label == "task_scam")

    assert bank_metrics.recall == pytest.approx(1.0)
    assert task_metrics.precision == pytest.approx(0.5)


def test_apply_recall_floor_adds_blocker_for_failing_label():
    low_recall_metrics = [
        PerLabelMetricRow(label="bank_impersonation", precision=1.0, recall=1.0, f1=1.0, support=10),
        PerLabelMetricRow(label="zalo_social_engineering", precision=1.0, recall=1.0, f1=1.0, support=10),
        PerLabelMetricRow(label="task_scam", precision=0.5, recall=0.44, f1=0.47, support=18),
        PerLabelMetricRow(label="benign", precision=1.0, recall=1.0, f1=1.0, support=10),
    ]

    updated_audit = _apply_recall_floor_to_audit(_clean_audit(), low_recall_metrics)

    assert updated_audit.ready is False
    assert updated_audit.verdict == "BLOCK"
    assert any("task_scam" in reason and "0.44" in reason for reason in updated_audit.blocker_reasons)


def test_apply_recall_floor_returns_same_audit_when_all_floors_met():
    audit = _clean_audit()
    passing_metrics = [
        PerLabelMetricRow(label="bank_impersonation", precision=1.0, recall=0.95, f1=0.97, support=10),
        PerLabelMetricRow(label="zalo_social_engineering", precision=1.0, recall=0.92, f1=0.96, support=10),
        PerLabelMetricRow(label="task_scam", precision=0.9, recall=0.91, f1=0.90, support=18),
        PerLabelMetricRow(label="benign", precision=1.0, recall=1.0, f1=1.0, support=10),
    ]

    assert _apply_recall_floor_to_audit(audit, passing_metrics) is audit


def test_task_scam_floor_is_point_eight_not_point_nine():
    audit = _clean_audit()
    metrics = [
        PerLabelMetricRow(label="bank_impersonation", recall=0.95, precision=0.95, f1=0.95, support=10),
        PerLabelMetricRow(label="zalo_social_engineering", recall=0.91, precision=0.91, f1=0.91, support=10),
        PerLabelMetricRow(label="task_scam", recall=0.82, precision=0.82, f1=0.82, support=10),
        PerLabelMetricRow(label="benign", recall=0.85, precision=0.85, f1=0.85, support=10),
    ]

    result = _apply_recall_floor_to_audit(audit, metrics)

    assert result.ready is True
    assert result.verdict == "PASS"
