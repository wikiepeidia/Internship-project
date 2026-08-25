"""Historical metric helpers for the retired Phase 5 release evaluator.

The old evaluator is deliberately terminal: Phase 41 owns the only supported
reserved-split evaluation path through ``phase41-run-once``.  Keeping the old
callable as an always-failing compatibility sentinel prevents stale imports from
silently becoming a second evaluation authority.
"""

from __future__ import annotations

from pathlib import Path
from typing import NoReturn, Sequence

from sklearn.metrics import f1_score, precision_recall_fscore_support
from sklearn.preprocessing import MultiLabelBinarizer

from src.model_adaptation.schemas import (
    LOCKED_RELEASE_LABELS,
    RISKY_LABEL_RECALL_FLOORS,
    HeldOutSupportAudit,
    OverallMetricSummary,
    PerLabelMetricRow,
    ReleaseEvaluationRow,
)


def _apply_recall_floor_to_audit(
    audit: HeldOutSupportAudit,
    per_label_metrics: list[PerLabelMetricRow],
) -> HeldOutSupportAudit:
    """Rebuild the audit with per-label recall floor violations appended as blockers.

    The initial support audit runs before evaluation and cannot check recall.  After
    metrics are computed this helper adds a blocker reason for every risky label whose
    recall sits below the configured floor, then returns a rebuilt audit so that
    ``audit.ready`` and ``audit.verdict`` correctly reflect the recall gate.
    """
    extra_blockers: list[str] = []
    for metric_row in per_label_metrics:
        if not metric_row.recall_floor_applies:
            continue
        if metric_row.support == 0:
            # Zero-support case is already handled by the support audit; skip.
            continue
        floor = RISKY_LABEL_RECALL_FLOORS.get(metric_row.label, audit.risky_recall_floor)
        if metric_row.recall < floor:
            extra_blockers.append(
                f"Release blocker: {metric_row.label} recall {metric_row.recall:.2f} "
                f"is below required floor {floor:.2f}."
            )
    if not extra_blockers:
        return audit
    combined_blockers = list(audit.blocker_reasons) + extra_blockers
    return HeldOutSupportAudit(
        evaluated_split_path=audit.evaluated_split_path,
        evaluated_split_root=audit.evaluated_split_root,
        support_by_label=dict(audit.support_by_label),
        blocker_reasons=combined_blockers,
        risky_recall_floor=audit.risky_recall_floor,
    )


DEFAULT_EVALUATION_SNAPSHOT_PATH = Path(
    ".planning/phases/05-recall-priority-evaluation-and-release-gates/05-evaluation-snapshot.json"
)


def compute_release_metrics(
    rows: Sequence[ReleaseEvaluationRow],
) -> tuple[OverallMetricSummary, list[PerLabelMetricRow]]:
    """Compute fixed-label macro and weighted F1 plus explicit per-label metrics."""

    if not rows:
        zero_metrics = [
            PerLabelMetricRow(label=label, precision=0.0, recall=0.0, f1=0.0, support=0)
            for label in LOCKED_RELEASE_LABELS
        ]
        return OverallMetricSummary(macro_f1=0.0, weighted_f1=0.0, evaluated_rows=0), zero_metrics

    label_order = list(LOCKED_RELEASE_LABELS)
    binarizer = MultiLabelBinarizer(classes=label_order)
    y_true = binarizer.fit_transform([[row.gold_label] for row in rows])
    y_pred = binarizer.transform([row.predicted_labels for row in rows])

    precision, recall, f1, support = precision_recall_fscore_support(
        y_true,
        y_pred,
        average=None,
        zero_division=0,
    )

    per_label_metrics = [
        PerLabelMetricRow(
            label=label,
            precision=float(precision[index]),
            recall=float(recall[index]),
            f1=float(f1[index]),
            support=int(support[index]),
        )
        for index, label in enumerate(label_order)
    ]
    overall_metrics = OverallMetricSummary(
        macro_f1=float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        weighted_f1=float(f1_score(y_true, y_pred, average="weighted", zero_division=0)),
        evaluated_rows=len(rows),
    )
    return overall_metrics, per_label_metrics


def evaluate_release_split(
    split_path: Path,
    *,
    audit: HeldOutSupportAudit | None = None,
    runtime_service: object | None = None,
    analyze_text: object | None = None,
    snapshot_path: Path = DEFAULT_EVALUATION_SNAPSHOT_PATH,
    run_id: str | None = None,
    progress_callback: object | None = None,
    checkpoint_interval: int | None = None,
) -> NoReturn:
    """Reject every call to the retired evaluator before inspecting any path.

    Identity aliases such as hardlinks, junctions, mapped drives, or Volume-GUID
    paths cannot bypass a guard that accepts no input at all.  Parameters remain
    only to give stale callers a deterministic migration error.
    """

    del (
        split_path,
        audit,
        runtime_service,
        analyze_text,
        snapshot_path,
        run_id,
        progress_callback,
        checkpoint_interval,
    )
    raise RuntimeError(
        "The legacy release evaluator is retired. Use the sole supported "
        "Phase 41 command: phase41-run-once."
    )
