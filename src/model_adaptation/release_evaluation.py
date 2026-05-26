"""Offline release-evaluation harness and explicit-label metric engine for Phase 5."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Callable, Sequence

from sklearn.metrics import f1_score, precision_recall_fscore_support
from sklearn.preprocessing import MultiLabelBinarizer

from src.data_pipeline.schemas import DatasetRecord
from src.model_adaptation.data import load_split_records
from src.model_adaptation.release_readiness import audit_release_eval_support
from src.model_adaptation.schemas import (
    LOCKED_RELEASE_LABELS,
    HeldOutSupportAudit,
    OverallMetricSummary,
    PerLabelMetricRow,
    ReleaseEvaluationRow,
    ReleaseEvaluationSnapshot,
)
from src.runtime.contracts import AnalysisResult, ChannelName, ThreatLabel
from src.runtime.service import RuntimeService, build_default_runtime_service


DEFAULT_EVALUATION_SNAPSHOT_PATH = Path(
    ".planning/phases/05-recall-priority-evaluation-and-release-gates/05-evaluation-snapshot.json"
)

AnalyzeText = Callable[[str, ChannelName], AnalysisResult]
ProgressCallback = Callable[[int, int], None]


def _default_run_id() -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"phase5-release-eval-{timestamp}"


def _resolve_analyze_callable(
    runtime_service: RuntimeService | None,
    analyze_text: AnalyzeText | None,
) -> AnalyzeText:
    if runtime_service is not None and analyze_text is not None:
        raise ValueError("Provide either runtime_service or analyze_text, not both")
    if analyze_text is not None:
        return analyze_text
    if runtime_service is not None:
        return runtime_service.analyze_text
    return build_default_runtime_service().analyze_text


def _normalize_predicted_labels(result: AnalysisResult) -> list[ThreatLabel]:
    locked_predictions = [label for label in LOCKED_RELEASE_LABELS if label in result.threat_labels]
    if locked_predictions:
        return locked_predictions
    if result.risk_tier == "benign":
        return ["benign"]
    return []


def _write_snapshot(snapshot: ReleaseEvaluationSnapshot, snapshot_path: Path) -> None:
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text(snapshot.model_dump_json(indent=2), encoding="utf-8")


def _load_resumable_rows(
    *,
    split_path: Path,
    records: Sequence[DatasetRecord],
    snapshot_path: Path,
    run_id: str,
) -> list[ReleaseEvaluationRow]:
    if not snapshot_path.exists():
        return []

    snapshot = ReleaseEvaluationSnapshot.model_validate_json(snapshot_path.read_text(encoding="utf-8"))
    if snapshot.run_id != run_id or snapshot.evaluated_split_path != split_path:
        return []

    if len(snapshot.rows) > len(records):
        return []

    for saved_row, record in zip(snapshot.rows, records):
        if saved_row.gold_label != record.label or saved_row.reviewable_source_text != record.text:
            return []

    return list(snapshot.rows)


def _build_snapshot(
    *,
    split_path: Path,
    audit: HeldOutSupportAudit,
    rows: Sequence[ReleaseEvaluationRow],
    run_id: str,
) -> ReleaseEvaluationSnapshot:
    overall_metrics, per_label_metrics = compute_release_metrics(rows)
    return ReleaseEvaluationSnapshot(
        run_id=run_id,
        evaluated_split_path=split_path,
        audit=audit,
        overall_metrics=overall_metrics,
        per_label_metrics=per_label_metrics,
        rows=list(rows),
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
    runtime_service: RuntimeService | None = None,
    analyze_text: AnalyzeText | None = None,
    snapshot_path: Path = DEFAULT_EVALUATION_SNAPSHOT_PATH,
    run_id: str | None = None,
    progress_callback: ProgressCallback | None = None,
    checkpoint_interval: int | None = None,
) -> ReleaseEvaluationSnapshot:
    """Evaluate one held-out split through the public runtime contract and save a snapshot."""

    resolved_audit = audit if audit is not None else audit_release_eval_support(split_path=split_path)
    analyze = _resolve_analyze_callable(runtime_service, analyze_text)
    records: list[DatasetRecord] = load_split_records(split_path)
    resolved_run_id = run_id or _default_run_id()
    rows = _load_resumable_rows(
        split_path=split_path,
        records=records,
        snapshot_path=snapshot_path,
        run_id=resolved_run_id,
    )
    total_records = len(records)

    if progress_callback is not None and rows:
        progress_callback(len(rows), total_records)

    for index, record in enumerate(records[len(rows) :], start=len(rows) + 1):
        result = analyze(record.text, channel="unknown")
        rows.append(
            ReleaseEvaluationRow(
                gold_label=record.label,
                predicted_labels=_normalize_predicted_labels(result),
                risk_tier=result.risk_tier,
                summary=result.summary,
                top_cues=list(result.top_cues),
                recommendations=list(result.recommendations),
                backend_name=result.backend_name,
                channel="unknown",
                split_provenance=str(split_path),
                normalized_text=result.normalized_text,
                reviewable_source_text=record.text,
            )
        )

        if progress_callback is not None:
            progress_callback(index, total_records)

        if checkpoint_interval is not None and checkpoint_interval > 0 and index % checkpoint_interval == 0 and index < total_records:
            checkpoint_snapshot = _build_snapshot(
                split_path=split_path,
                audit=resolved_audit,
                rows=rows,
                run_id=resolved_run_id,
            )
            _write_snapshot(checkpoint_snapshot, snapshot_path)

    snapshot = _build_snapshot(
        split_path=split_path,
        audit=resolved_audit,
        rows=rows,
        run_id=resolved_run_id,
    )
    _write_snapshot(snapshot, snapshot_path)
    return snapshot