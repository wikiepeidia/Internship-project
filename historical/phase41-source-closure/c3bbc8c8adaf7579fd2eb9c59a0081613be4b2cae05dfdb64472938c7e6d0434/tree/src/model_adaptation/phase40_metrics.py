"""Strict single-label validation metrics for Phase 40 model families."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import json
import math
from numbers import Real
from typing import Sequence

from sklearn.metrics import accuracy_score, confusion_matrix, precision_recall_fscore_support


LABEL_ORDER = (
    "bank_impersonation",
    "zalo_social_engineering",
    "task_scam",
    "benign",
)
RISKY_LABELS = LABEL_ORDER[:3]
PREDICTION_ORDER = LABEL_ORDER + ("invalid_output",)
RISKY_RECALL_FLOORS = {
    "bank_impersonation": 0.90,
    "zalo_social_engineering": 0.90,
    "task_scam": 0.80,
}
_ALLOWED_QWEN_OUTPUT_KEYS = frozenset(
    {"label", "risk_tier", "suspicious_spans", "xai_explanation"}
)


class PredictionState(StrEnum):
    BANK_IMPERSONATION = "bank_impersonation"
    ZALO_SOCIAL_ENGINEERING = "zalo_social_engineering"
    TASK_SCAM = "task_scam"
    BENIGN = "benign"
    INVALID_OUTPUT = "invalid_output"


@dataclass(frozen=True, slots=True)
class ParsedQwenPrediction:
    state: PredictionState
    parser_exception: str | None = None


class _DuplicateKeyError(ValueError):
    pass


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKeyError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _load_qwen_json(raw_prediction: str) -> object:
    def reject_nonstandard_constant(value: str) -> object:
        raise ValueError(f"non-standard JSON constant: {value}")

    return json.loads(
        raw_prediction,
        object_pairs_hook=_reject_duplicate_keys,
        parse_constant=reject_nonstandard_constant,
    )


def parse_qwen_prediction(raw_prediction: str) -> ParsedQwenPrediction:
    """Parse exactly one locked label without normalization or repair."""

    if not isinstance(raw_prediction, str) or not raw_prediction.strip():
        return ParsedQwenPrediction(PredictionState.INVALID_OUTPUT, "empty output")
    try:
        payload = _load_qwen_json(raw_prediction)
        if not isinstance(payload, dict):
            raise ValueError("prediction must be one JSON object")
        unknown_keys = sorted(set(payload).difference(_ALLOWED_QWEN_OUTPUT_KEYS))
        if unknown_keys:
            raise ValueError(f"prediction contains unknown fields: {unknown_keys}")
        if "label" not in payload:
            raise ValueError("prediction is missing label")
        label = payload["label"]
        if not isinstance(label, str):
            raise ValueError("prediction label must be a string")
        if label not in LABEL_ORDER:
            raise ValueError(f"unknown prediction label: {label!r}")
        return ParsedQwenPrediction(PredictionState(label), None)
    except Exception as exc:  # parser failures are retained as explicit invalid output
        return ParsedQwenPrediction(PredictionState.INVALID_OUTPUT, f"{type(exc).__name__}: {exc}")


@dataclass(frozen=True, slots=True)
class Phase40PredictionRow:
    validation_row_id: str
    sequence_index: int
    gold_label: str
    raw_prediction: str
    parsed_state: PredictionState
    parser_exception: str | None
    artifact_identity: str
    checkpoint_step: int
    decoder_do_sample: bool = False
    decoder_num_return_sequences: int = 1
    decoder_max_new_tokens: int = 256
    phobert_logits: tuple[float, ...] | None = None

    def __post_init__(self) -> None:
        self._validate_raw_parse_consistency()
        if not isinstance(self.validation_row_id, str) or not self.validation_row_id:
            raise ValueError("validation_row_id must be non-empty")
        if (
            not isinstance(self.sequence_index, int)
            or isinstance(self.sequence_index, bool)
            or self.sequence_index < 0
        ):
            raise ValueError("sequence_index must be non-negative")
        if self.gold_label not in LABEL_ORDER:
            raise ValueError("gold_label must be one of the four locked labels")
        if not isinstance(self.artifact_identity, str) or not self.artifact_identity:
            raise ValueError("artifact_identity must be non-empty")
        if (
            not isinstance(self.checkpoint_step, int)
            or isinstance(self.checkpoint_step, bool)
            or self.checkpoint_step < 0
        ):
            raise ValueError("checkpoint_step must be non-negative")
        if (
            self.decoder_do_sample is not False
            or self.decoder_num_return_sequences != 1
            or self.decoder_max_new_tokens != 256
        ):
            raise ValueError("Phase 40 decoder controls are immutable")
        if self.phobert_logits is not None:
            if len(self.phobert_logits) != len(LABEL_ORDER) or any(
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                for value in self.phobert_logits
            ):
                raise ValueError("PhoBERT metric row requires four finite raw logits")
            argmax_state = LABEL_ORDER[
                max(
                    range(len(self.phobert_logits)),
                    key=lambda index: self.phobert_logits[index],
                )
            ]
            if self.parsed_state.value != argmax_state:
                raise ValueError("PhoBERT metric-row state differs from retained raw logits")

    def _validate_raw_parse_consistency(self) -> None:
        if not isinstance(self.raw_prediction, str):
            raise ValueError("raw_prediction must be a string")
        if not isinstance(self.parsed_state, PredictionState):
            raise ValueError("parsed_state must be a PredictionState")
        if self.parser_exception is not None and not isinstance(self.parser_exception, str):
            raise ValueError("parser_exception must be a string or None")
        parsed = parse_qwen_prediction(self.raw_prediction)
        if self.parsed_state != parsed.state:
            raise ValueError("parsed_state does not match the strict parse of raw_prediction")
        if self.parser_exception != parsed.parser_exception:
            raise ValueError("parser_exception does not match the strict parse of raw_prediction")

    @classmethod
    def from_raw(
        cls,
        *,
        validation_row_id: str | None,
        sequence_index: int,
        gold_label: str,
        raw_prediction: str,
        artifact_identity: str,
        checkpoint_step: int,
    ) -> "Phase40PredictionRow":
        if validation_row_id is None:
            raise ValueError("validation_row_id must come from a validation snapshot")
        parsed = parse_qwen_prediction(raw_prediction)
        return cls(
            validation_row_id=validation_row_id,
            sequence_index=sequence_index,
            gold_label=gold_label,
            raw_prediction=raw_prediction,
            parsed_state=parsed.state,
            parser_exception=parsed.parser_exception,
            artifact_identity=artifact_identity,
            checkpoint_step=checkpoint_step,
        )

    @classmethod
    def from_phobert_logits(
        cls,
        *,
        validation_row_id: str | None,
        sequence_index: int,
        gold_label: str,
        logits: tuple[float, ...],
        artifact_identity: str,
        checkpoint_step: int,
    ) -> "Phase40PredictionRow":
        if validation_row_id is None:
            raise ValueError("validation_row_id must come from a validation snapshot")
        normalized_logits = tuple(logits)
        if len(normalized_logits) != len(LABEL_ORDER) or any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            for value in normalized_logits
        ):
            raise ValueError("PhoBERT prediction requires four finite raw logits")
        predicted = LABEL_ORDER[
            max(range(len(normalized_logits)), key=lambda index: normalized_logits[index])
        ]
        raw_prediction = json.dumps(
            {"label": predicted},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return cls(
            validation_row_id=validation_row_id,
            sequence_index=sequence_index,
            gold_label=gold_label,
            raw_prediction=raw_prediction,
            parsed_state=PredictionState(predicted),
            parser_exception=None,
            artifact_identity=artifact_identity,
            checkpoint_step=checkpoint_step,
            phobert_logits=normalized_logits,
        )

    def as_json_dict(self) -> dict[str, object]:
        if self.phobert_logits is not None:
            return {
                "validation_row_id": self.validation_row_id,
                "sequence_index": self.sequence_index,
                "gold_label": self.gold_label,
                "logits": list(self.phobert_logits),
                "argmax_state": self.parsed_state.value,
                "artifact_identity": self.artifact_identity,
                "checkpoint_step": self.checkpoint_step,
            }
        return {
            "validation_row_id": self.validation_row_id,
            "sequence_index": self.sequence_index,
            "gold_label": self.gold_label,
            "raw_prediction": self.raw_prediction,
            "parsed_state": self.parsed_state.value,
            "parser_exception": self.parser_exception,
            "artifact_identity": self.artifact_identity,
            "checkpoint_step": self.checkpoint_step,
            "decoder": {
                "do_sample": self.decoder_do_sample,
                "num_return_sequences": self.decoder_num_return_sequences,
                "max_new_tokens": self.decoder_max_new_tokens,
            },
        }


@dataclass(frozen=True, slots=True)
class PerClassMetric:
    label: str
    precision: float
    recall: float
    f1: float
    support: int

    def __post_init__(self) -> None:
        _validate_per_class_metric(self)


@dataclass(frozen=True, slots=True)
class Phase40MetricResult:
    evaluated_rows: int
    per_class: tuple[PerClassMetric, ...]
    macro_f1: float
    weighted_f1: float
    accuracy: float
    invalid_output_count: int
    invalid_output_rate: float
    risky_to_benign_count: int
    risky_to_invalid_count: int
    confusion_matrix: tuple[tuple[int, ...], ...]
    prediction_rows: tuple[Phase40PredictionRow, ...]
    risky_to_benign_row_ids: tuple[str, ...]
    risky_to_invalid_row_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        _validate_metric_result(self)


@dataclass(frozen=True, slots=True)
class CheckpointSelection:
    """Deterministic selected checkpoint and its safety-gate disposition."""

    selected_step: int
    selected_artifact_identity: str
    selected_metrics: Phase40MetricResult
    safety_gate_passed: bool
    status: str
    violations: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _ComputedMetricValues:
    per_class: tuple[PerClassMetric, ...]
    macro_f1: float
    weighted_f1: float
    accuracy: float
    invalid_output_count: int
    invalid_output_rate: float
    risky_to_benign_count: int
    risky_to_invalid_count: int
    confusion_matrix: tuple[tuple[int, ...], ...]
    risky_to_benign_row_ids: tuple[str, ...]
    risky_to_invalid_row_ids: tuple[str, ...]


def _validate_probability(name: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a finite number")
    numeric = float(value)
    if not math.isfinite(numeric):
        raise ValueError(f"{name} must be finite")
    if not 0.0 <= numeric <= 1.0:
        raise ValueError(f"{name} must be between 0 and 1")
    return numeric


def _validate_non_negative_int(name: str, value: object) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return value


def _validate_per_class_metric(metric: PerClassMetric) -> None:
    if not isinstance(metric.label, str) or metric.label not in LABEL_ORDER:
        raise ValueError("per-class label must be one of the four locked labels")
    _validate_probability(f"{metric.label} precision", metric.precision)
    _validate_probability(f"{metric.label} recall", metric.recall)
    _validate_probability(f"{metric.label} f1", metric.f1)
    _validate_non_negative_int(f"{metric.label} support", metric.support)


def _compute_metric_values(
    gold: tuple[str, ...],
    predictions: tuple[Phase40PredictionRow, ...],
) -> _ComputedMetricValues:
    predicted = tuple(row.parsed_state.value for row in predictions)
    precision, recall, f1, support = precision_recall_fscore_support(
        gold,
        predicted,
        labels=list(LABEL_ORDER),
        average=None,
        zero_division=0,
    )
    per_class = tuple(
        PerClassMetric(
            label=label,
            precision=float(precision[index]),
            recall=float(recall[index]),
            f1=float(f1[index]),
            support=int(support[index]),
        )
        for index, label in enumerate(LABEL_ORDER)
    )
    _, _, macro_f1, _ = precision_recall_fscore_support(
        gold,
        predicted,
        labels=list(LABEL_ORDER),
        average="macro",
        zero_division=0,
    )
    _, _, weighted_f1, _ = precision_recall_fscore_support(
        gold,
        predicted,
        labels=list(LABEL_ORDER),
        average="weighted",
        zero_division=0,
    )
    full_matrix = confusion_matrix(gold, predicted, labels=list(PREDICTION_ORDER))
    matrix = tuple(
        tuple(int(value) for value in row)
        for row in full_matrix[: len(LABEL_ORDER), :]
    )
    invalid_count = sum(state == "invalid_output" for state in predicted)
    risky_to_benign = sum(
        gold_label in RISKY_LABELS and predicted_label == "benign"
        for gold_label, predicted_label in zip(gold, predicted, strict=True)
    )
    risky_to_invalid = sum(
        gold_label in RISKY_LABELS and predicted_label == "invalid_output"
        for gold_label, predicted_label in zip(gold, predicted, strict=True)
    )
    risky_to_benign_row_ids = tuple(
        row.validation_row_id
        for gold_label, predicted_label, row in zip(
            gold, predicted, predictions, strict=True
        )
        if gold_label in RISKY_LABELS and predicted_label == "benign"
    )
    risky_to_invalid_row_ids = tuple(
        row.validation_row_id
        for gold_label, predicted_label, row in zip(
            gold, predicted, predictions, strict=True
        )
        if gold_label in RISKY_LABELS and predicted_label == "invalid_output"
    )
    return _ComputedMetricValues(
        per_class=per_class,
        macro_f1=float(macro_f1),
        weighted_f1=float(weighted_f1),
        accuracy=float(accuracy_score(gold, predicted)),
        invalid_output_count=invalid_count,
        invalid_output_rate=invalid_count / len(gold),
        risky_to_benign_count=risky_to_benign,
        risky_to_invalid_count=risky_to_invalid,
        confusion_matrix=matrix,
        risky_to_benign_row_ids=risky_to_benign_row_ids,
        risky_to_invalid_row_ids=risky_to_invalid_row_ids,
    )


def _validate_metric_result(metrics: Phase40MetricResult) -> None:
    _validate_non_negative_int("evaluated_rows", metrics.evaluated_rows)
    if not isinstance(metrics.prediction_rows, tuple) or not metrics.prediction_rows:
        raise ValueError("prediction_rows must be a non-empty tuple")
    for index, row in enumerate(metrics.prediction_rows):
        if not isinstance(row, Phase40PredictionRow):
            raise ValueError("prediction_rows must contain Phase40PredictionRow values")
        row._validate_raw_parse_consistency()
        if row.sequence_index != index:
            raise ValueError("prediction row order must match contiguous sequence_index values")
    row_ids = tuple(row.validation_row_id for row in metrics.prediction_rows)
    if len(set(row_ids)) != len(row_ids):
        raise ValueError("prediction_rows contain duplicate validation_row_id values")
    if metrics.evaluated_rows != len(metrics.prediction_rows):
        raise ValueError("evaluated_rows does not match retained prediction rows")

    if not isinstance(metrics.per_class, tuple) or len(metrics.per_class) != len(LABEL_ORDER):
        raise ValueError("per_class must contain exactly four ordered metric rows")
    for metric in metrics.per_class:
        if not isinstance(metric, PerClassMetric):
            raise ValueError("per_class must contain PerClassMetric values")
        _validate_per_class_metric(metric)
    if tuple(metric.label for metric in metrics.per_class) != LABEL_ORDER:
        raise ValueError("per_class rows do not follow the locked label order")

    _validate_probability("macro_f1", metrics.macro_f1)
    _validate_probability("weighted_f1", metrics.weighted_f1)
    _validate_probability("accuracy", metrics.accuracy)
    _validate_non_negative_int("invalid_output_count", metrics.invalid_output_count)
    _validate_probability("invalid_output_rate", metrics.invalid_output_rate)
    _validate_non_negative_int("risky_to_benign_count", metrics.risky_to_benign_count)
    _validate_non_negative_int("risky_to_invalid_count", metrics.risky_to_invalid_count)

    if not isinstance(metrics.confusion_matrix, tuple) or len(metrics.confusion_matrix) != len(LABEL_ORDER):
        raise ValueError("confusion_matrix must have four ordered gold-label rows")
    for row in metrics.confusion_matrix:
        if not isinstance(row, tuple) or len(row) != len(PREDICTION_ORDER):
            raise ValueError("confusion_matrix must be a locked 4x5 tuple")
        for value in row:
            _validate_non_negative_int("confusion_matrix cell", value)
    if not isinstance(metrics.risky_to_benign_row_ids, tuple):
        raise ValueError("risky_to_benign_row_ids must be a tuple")
    if not isinstance(metrics.risky_to_invalid_row_ids, tuple):
        raise ValueError("risky_to_invalid_row_ids must be a tuple")

    gold = tuple(row.gold_label for row in metrics.prediction_rows)
    expected = _compute_metric_values(gold, metrics.prediction_rows)
    exact_fields = (
        "per_class",
        "macro_f1",
        "weighted_f1",
        "accuracy",
        "invalid_output_count",
        "invalid_output_rate",
        "risky_to_benign_count",
        "risky_to_invalid_count",
        "confusion_matrix",
        "risky_to_benign_row_ids",
        "risky_to_invalid_row_ids",
    )
    for field_name in exact_fields:
        if getattr(metrics, field_name) != getattr(expected, field_name):
            raise ValueError(f"{field_name} does not match retained prediction rows")


def _validate_metric_inputs(
    expected_validation_row_ids: Sequence[str],
    gold_labels: Sequence[str],
    prediction_rows: Sequence[Phase40PredictionRow],
) -> None:
    expected_ids = tuple(expected_validation_row_ids)
    gold = tuple(gold_labels)
    predictions = tuple(prediction_rows)
    if not expected_ids:
        raise ValueError("expected validation row IDs must not be empty")
    if len(set(expected_ids)) != len(expected_ids):
        raise ValueError("expected validation row IDs contain duplicates")
    if len(gold) != len(expected_ids):
        raise ValueError("gold label count does not match expected validation row IDs")
    if any(label not in LABEL_ORDER for label in gold):
        raise ValueError("gold labels must use the locked Phase 40 label order")
    for row in predictions:
        if not isinstance(row, Phase40PredictionRow):
            raise ValueError("prediction rows must contain Phase40PredictionRow values")
        row._validate_raw_parse_consistency()
    actual_ids = tuple(row.validation_row_id for row in predictions)
    if actual_ids != expected_ids:
        raise ValueError("prediction validation_row_id sequence does not exactly match the canonical snapshot")
    if len(set(actual_ids)) != len(actual_ids):
        raise ValueError("prediction validation_row_id values contain duplicates")
    for index, (gold_label, row) in enumerate(zip(gold, predictions, strict=True)):
        if row.sequence_index != index:
            raise ValueError("prediction sequence_index does not match canonical validation order")
        if row.gold_label != gold_label:
            raise ValueError("prediction gold_label does not match canonical validation gold label")


def validate_phase40_prediction_rows(
    *,
    expected_validation_row_ids: Sequence[str],
    gold_labels: Sequence[str],
    prediction_rows: Sequence[Phase40PredictionRow],
) -> None:
    """Public exact-ID/order gate shared by producers and the metric engine."""

    _validate_metric_inputs(expected_validation_row_ids, gold_labels, prediction_rows)


def evaluate_phase40_predictions(
    *,
    expected_validation_row_ids: Sequence[str],
    gold_labels: Sequence[str],
    prediction_rows: Sequence[Phase40PredictionRow],
) -> Phase40MetricResult:
    """Evaluate every canonical validation row with invalid output retained."""

    _validate_metric_inputs(expected_validation_row_ids, gold_labels, prediction_rows)
    gold = tuple(gold_labels)
    predictions = tuple(prediction_rows)
    computed = _compute_metric_values(gold, predictions)
    return Phase40MetricResult(
        evaluated_rows=len(gold),
        per_class=computed.per_class,
        macro_f1=computed.macro_f1,
        weighted_f1=computed.weighted_f1,
        accuracy=computed.accuracy,
        invalid_output_count=computed.invalid_output_count,
        invalid_output_rate=computed.invalid_output_rate,
        risky_to_benign_count=computed.risky_to_benign_count,
        risky_to_invalid_count=computed.risky_to_invalid_count,
        confusion_matrix=computed.confusion_matrix,
        prediction_rows=predictions,
        risky_to_benign_row_ids=computed.risky_to_benign_row_ids,
        risky_to_invalid_row_ids=computed.risky_to_invalid_row_ids,
    )


def _checkpoint_identity(metrics: Phase40MetricResult) -> tuple[int, str]:
    if not metrics.prediction_rows:
        raise ValueError("checkpoint metrics must retain at least one raw prediction row")
    steps = {row.checkpoint_step for row in metrics.prediction_rows}
    artifacts = {row.artifact_identity for row in metrics.prediction_rows}
    if len(steps) != 1 or len(artifacts) != 1:
        raise ValueError("checkpoint metrics mix optimizer steps or artifact identities")
    return next(iter(steps)), next(iter(artifacts))


def _safety_violations(metrics: Phase40MetricResult) -> tuple[str, ...]:
    by_label = {row.label: row for row in metrics.per_class}
    if set(by_label) != set(LABEL_ORDER):
        raise ValueError("checkpoint metrics must contain all four per-class rows")
    violations: list[str] = []
    for label, floor in RISKY_RECALL_FLOORS.items():
        recall = by_label[label].recall
        if recall < floor:
            violations.append(f"{label} recall {recall:.6f} is below {floor:.2f}")
    if metrics.invalid_output_count:
        violations.append(f"invalid_output_count is {metrics.invalid_output_count}, expected 0")
    return tuple(violations)


def select_phase40_checkpoint(
    candidates: Sequence[Phase40MetricResult],
) -> CheckpointSelection:
    """Apply risky-recall admission, macro-F1 ranking, and locked tie-breaks."""

    if not candidates:
        raise ValueError("at least one checkpoint candidate is required")
    indexed: list[tuple[Phase40MetricResult, int, str, tuple[str, ...]]] = []
    canonical_cohort: tuple[tuple[str, int, str], ...] | None = None
    for metrics in candidates:
        if not isinstance(metrics, Phase40MetricResult):
            raise ValueError("checkpoint candidates must be Phase40MetricResult values")
        # Revalidate at the trust boundary even though normal construction also
        # validates. This rejects deserialized or otherwise tampered instances.
        _validate_metric_result(metrics)
        cohort = tuple(
            (row.validation_row_id, row.sequence_index, row.gold_label)
            for row in metrics.prediction_rows
        )
        if canonical_cohort is None:
            canonical_cohort = cohort
        elif cohort != canonical_cohort:
            raise ValueError(
                "checkpoint candidates do not share the same canonical validation cohort"
            )
        step, artifact = _checkpoint_identity(metrics)
        indexed.append((metrics, step, artifact, _safety_violations(metrics)))
    passing = [item for item in indexed if not item[3]]
    pool = passing if passing else indexed
    selected_metrics, selected_step, selected_artifact, violations = sorted(
        pool,
        key=lambda item: (
            -item[0].macro_f1,
            item[0].risky_to_benign_count,
            item[1],
            item[2],
        ),
    )[0]
    passed = bool(passing)
    return CheckpointSelection(
        selected_step=selected_step,
        selected_artifact_identity=selected_artifact,
        selected_metrics=selected_metrics,
        safety_gate_passed=passed,
        status="passed_safety_gate" if passed else "failed_safety_gate",
        violations=() if passed else violations,
    )
