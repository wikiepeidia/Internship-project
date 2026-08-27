"""Strict phase-neutral contracts for frozen two-model evaluation facts.

This module intentionally defines data contracts only.  It has no evaluator,
runner, predictor, threshold, model-loading, or training entry point.
"""

from __future__ import annotations

import math
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)


ThreatLabel = Literal[
    "bank_impersonation",
    "zalo_social_engineering",
    "task_scam",
    "benign",
]
ModelRole = Literal["qwen", "phobert"]
Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]

LABEL_ORDER: tuple[ThreatLabel, ...] = (
    "bank_impersonation",
    "zalo_social_engineering",
    "task_scam",
    "benign",
)
PREDICTION_COLUMNS: tuple[str, ...] = (*LABEL_ORDER, "invalid_output")
MODEL_ROLE_ORDER: tuple[ModelRole, ...] = ("qwen", "phobert")
COMPARISON_PREFIXES: tuple[str, ...] = (
    "PhoBERT higher on:",
    "Qwen higher on:",
    "Ties:",
)
_METRIC_TOLERANCE = 1e-12


class _StrictContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)


class PerClassMetrics(_StrictContract):
    """Precision, recall, and F1 facts for one locked threat label."""

    label: ThreatLabel
    precision: float = Field(ge=0.0, le=1.0)
    recall: float = Field(ge=0.0, le=1.0)
    f1: float = Field(ge=0.0, le=1.0)
    support: int = Field(ge=0)


class ModelMetrics(_StrictContract):
    """Complete immutable metric facts for one evaluated model role."""

    accuracy: float = Field(ge=0.0, le=1.0)
    confusion_matrix: tuple[tuple[int, ...], ...]
    evaluated_rows: int = Field(gt=0)
    invalid_output_count: int = Field(ge=0)
    invalid_output_rate: float = Field(ge=0.0, le=1.0)
    label_order: tuple[ThreatLabel, ...]
    macro_f1: float = Field(ge=0.0, le=1.0)
    per_class: tuple[PerClassMetrics, ...]
    prediction_columns: tuple[str, ...]
    risky_to_benign_count: int = Field(ge=0)
    risky_to_invalid_count: int = Field(ge=0)
    weighted_f1: float = Field(ge=0.0, le=1.0)

    @field_validator("label_order")
    @classmethod
    def require_label_order(
        cls, value: tuple[ThreatLabel, ...]
    ) -> tuple[ThreatLabel, ...]:
        if value != LABEL_ORDER:
            raise ValueError("label order must match the locked four-label order")
        return value

    @field_validator("prediction_columns")
    @classmethod
    def require_prediction_columns(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if value != PREDICTION_COLUMNS:
            raise ValueError("prediction columns must match the locked output order")
        return value

    @field_validator("confusion_matrix")
    @classmethod
    def require_confusion_shape(
        cls, value: tuple[tuple[int, ...], ...]
    ) -> tuple[tuple[int, ...], ...]:
        if len(value) != len(LABEL_ORDER) or any(
            len(row) != len(PREDICTION_COLUMNS) for row in value
        ):
            raise ValueError("confusion matrix must have four rows and five columns")
        if any(count < 0 for row in value for count in row):
            raise ValueError("confusion matrix counts must be non-negative")
        return value

    @model_validator(mode="after")
    def require_internal_consistency(self) -> "ModelMetrics":
        if tuple(item.label for item in self.per_class) != LABEL_ORDER:
            raise ValueError("per-class metrics must follow the locked label order")
        if any(
            item.support != sum(self.confusion_matrix[index])
            for index, item in enumerate(self.per_class)
        ):
            raise ValueError("per-class support must match each confusion row")
        matrix_total = sum(sum(row) for row in self.confusion_matrix)
        support_total = sum(item.support for item in self.per_class)
        if matrix_total != self.evaluated_rows or support_total != self.evaluated_rows:
            raise ValueError("evaluated rows must equal confusion and support totals")
        invalid_total = sum(row[-1] for row in self.confusion_matrix)
        if invalid_total != self.invalid_output_count:
            raise ValueError("invalid output count must match the confusion matrix")
        expected_rate = self.invalid_output_count / self.evaluated_rows
        if not math.isclose(self.invalid_output_rate, expected_rate, abs_tol=1e-12):
            raise ValueError("invalid output rate must match evaluated rows")
        correct = sum(self.confusion_matrix[index][index] for index in range(4))
        if not math.isclose(self.accuracy, correct / self.evaluated_rows, abs_tol=1e-12):
            raise ValueError("accuracy must match the confusion matrix")
        risky_to_benign = sum(row[3] for row in self.confusion_matrix[:3])
        if self.risky_to_benign_count != risky_to_benign:
            raise ValueError("risky-to-benign count must match the confusion matrix")
        risky_to_invalid = sum(row[4] for row in self.confusion_matrix[:3])
        if self.risky_to_invalid_count != risky_to_invalid:
            raise ValueError("risky-to-invalid count must match the confusion matrix")

        expected_f1: list[float] = []
        for index, item in enumerate(self.per_class):
            true_positive = self.confusion_matrix[index][index]
            predicted = sum(row[index] for row in self.confusion_matrix)
            precision = true_positive / predicted if predicted else 0.0
            recall = true_positive / item.support if item.support else 0.0
            f1 = (
                2 * precision * recall / (precision + recall)
                if precision + recall
                else 0.0
            )
            for name, supplied, expected in (
                ("precision", item.precision, precision),
                ("recall", item.recall, recall),
                ("f1", item.f1, f1),
            ):
                if not math.isclose(supplied, expected, abs_tol=_METRIC_TOLERANCE):
                    raise ValueError(
                        f"{item.label} {name} must match the confusion matrix"
                    )
            expected_f1.append(f1)
        macro_f1 = sum(expected_f1) / len(expected_f1)
        weighted_f1 = sum(
            score * item.support
            for score, item in zip(expected_f1, self.per_class, strict=True)
        ) / self.evaluated_rows
        if not math.isclose(self.macro_f1, macro_f1, abs_tol=_METRIC_TOLERANCE):
            raise ValueError("macro F1 must match the confusion matrix")
        if not math.isclose(
            self.weighted_f1, weighted_f1, abs_tol=_METRIC_TOLERANCE
        ):
            raise ValueError("weighted F1 must match the confusion matrix")
        return self


class EvaluatedSnapshot(_StrictContract):
    """Hash-only metadata for the shared evaluation cohort."""

    byte_count: int = Field(alias="bytes", ge=0)
    records: int = Field(gt=0)
    sha256: Sha256


class EvaluatedModel(_StrictContract):
    """Frozen identity and facts for one role in the comparison."""

    artifact_sha256: Sha256
    metrics: ModelMetrics
    predictions_sha256: Sha256
    role: ModelRole
    run_id: str = Field(min_length=1)
    selected_checkpoint_identity: str = Field(min_length=1)

    @field_validator("run_id", "selected_checkpoint_identity")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("identity text must not be blank")
        return value

    @model_validator(mode="after")
    def require_checkpoint_identity(self) -> "EvaluatedModel":
        prefix = (
            "adapter-state-sha256:"
            if self.role == "qwen"
            else "model-state-sha256:"
        )
        digest = self.selected_checkpoint_identity.removeprefix(prefix)
        if (
            not self.selected_checkpoint_identity.startswith(prefix)
            or len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)
        ):
            raise ValueError("checkpoint identity does not match the fixed model role")
        return self


class PriorExposureDisclosure(_StrictContract):
    claim: Literal["one_post_freeze_model_evaluation_pass"]
    human_content_exposure_disclosed: Literal[True]


class TerminalEvaluationPolicy(_StrictContract):
    rerun_permitted: Literal[False]
    test_driven_checkpoint_selection_permitted: Literal[False]
    test_driven_contingency_activation_permitted: Literal[False]
    test_driven_dataset_repair_permitted: Literal[False]
    test_driven_training_action_permitted: Literal[False]


class TwoModelEvaluationResult(_StrictContract):
    """Strict reporting contract for one terminal two-model comparison."""

    authorization_sha256: Sha256
    claim_sha256: Sha256
    comparison_statements: tuple[str, ...]
    held_out: EvaluatedSnapshot
    models: tuple[EvaluatedModel, ...]
    prepared_sha256: Sha256
    prior_exposure: PriorExposureDisclosure
    schema_version: Literal["phase41-one-shot-results-v1"]
    status: Literal["completed"]
    terminal_policy: TerminalEvaluationPolicy

    @field_validator("comparison_statements")
    @classmethod
    def require_comparison_statements(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(COMPARISON_PREFIXES) or any(
            not statement.startswith(prefix)
            for statement, prefix in zip(value, COMPARISON_PREFIXES, strict=True)
        ):
            raise ValueError("comparison statements must use the three locked roles")
        return value

    @model_validator(mode="after")
    def require_model_role_order(self) -> "TwoModelEvaluationResult":
        if tuple(item.role for item in self.models) != MODEL_ROLE_ORDER:
            raise ValueError("models must use the fixed order: qwen, phobert")
        qwen, phobert = (item.metrics for item in self.models)
        for category, (statement, prefix) in enumerate(
            zip(self.comparison_statements, COMPARISON_PREFIXES, strict=True)
        ):
            body = statement.removeprefix(prefix).strip().removesuffix(".")
            if body == "none":
                continue
            claims = [claim.strip() for claim in body.split(",") if claim.strip()]
            if not claims:
                raise ValueError("comparison statement must name metrics or 'none'")
            for claim in claims:
                lower_is_better = claim.endswith("(lower_is_better)")
                metric_name = claim.removesuffix("(lower_is_better)")
                qwen_value = _metric_value(qwen, metric_name)
                phobert_value = _metric_value(phobert, metric_name)
                if math.isclose(qwen_value, phobert_value, abs_tol=_METRIC_TOLERANCE):
                    expected_category = 2
                elif (qwen_value < phobert_value) is lower_is_better:
                    expected_category = 1
                else:
                    expected_category = 0
                if category != expected_category:
                    raise ValueError(
                        f"comparison statement reverses metric fact {metric_name!r}"
                    )
        return self


def _metric_value(metrics: ModelMetrics, name: str) -> float:
    summary_names = {
        "accuracy",
        "macro_f1",
        "weighted_f1",
        "invalid_output_count",
        "invalid_output_rate",
        "risky_to_benign_count",
        "risky_to_invalid_count",
    }
    if name in summary_names:
        return float(getattr(metrics, name))
    label, separator, field = name.partition(".")
    if separator and label in LABEL_ORDER and field in {"precision", "recall", "f1"}:
        item = metrics.per_class[LABEL_ORDER.index(label)]
        return float(getattr(item, field))
    raise ValueError(f"unknown comparison metric {name!r}")


__all__ = [
    "LABEL_ORDER",
    "MODEL_ROLE_ORDER",
    "ModelMetrics",
    "PerClassMetrics",
    "TwoModelEvaluationResult",
]
