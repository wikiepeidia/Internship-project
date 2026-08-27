"""Phase-neutral contracts and readers for active runtime artifacts."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal, Mapping

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from src.core.integrity import (
    IntegrityError,
    atomic_replace_new_artifact,
    prepare_bounded_output,
    strict_json_object,
)


LockedCandidateId = Literal[
    "qwen3.5-4b",
    "qwen3-4b-instruct-2507",
    "qwen2.5-7b-instruct",
]
ArtifactType = Literal["adapter", "gguf"]
EvaluatedSplit = Literal["train", "val", "test", "pilot"]
ThreatLabel = Literal[
    "bank_impersonation",
    "zalo_social_engineering",
    "task_scam",
    "benign",
]
RiskyThreatLabel = Literal["bank_impersonation", "zalo_social_engineering", "task_scam"]
ReleaseVerdict = Literal["PASS", "BLOCK", "FLAG"]

LOCKED_RELEASE_LABELS: tuple[ThreatLabel, ...] = (
    "bank_impersonation",
    "zalo_social_engineering",
    "task_scam",
    "benign",
)
LOCKED_RISKY_LABELS: tuple[RiskyThreatLabel, ...] = (
    "bank_impersonation",
    "zalo_social_engineering",
    "task_scam",
)
UNIFORM_RISKY_RECALL_FLOOR = 0.90
RISKY_LABEL_RECALL_FLOORS: dict[str, float] = {
    "bank_impersonation": 0.90,
    "zalo_social_engineering": 0.90,
    "task_scam": 0.80,
}
LAPTOP_BASELINE_CANDIDATE_IDS: tuple[LockedCandidateId, ...] = (
    "qwen3.5-4b",
    "qwen3-4b-instruct-2507",
)


class ArtifactError(RuntimeError):
    """Raised when an active artifact does not satisfy its contract."""


class PilotScorecard(BaseModel):
    """Deterministic pilot metrics for one candidate on one split."""

    model_config = ConfigDict(extra="forbid")

    candidate_id: LockedCandidateId
    hf_source: str = Field(min_length=1)
    evaluated_split: EvaluatedSplit = "val"
    quality_score: float = Field(ge=0.0, le=1.0)
    recall_score: float = Field(ge=0.0, le=1.0)
    latency_score: float = Field(ge=0.0, le=1.0)
    memory_fit_score: float = Field(ge=0.0, le=1.0)
    hardware_penalty: float = Field(default=0.0, ge=0.0)
    profile_notes: str = Field(min_length=1)
    local_output_path: Path | None = None

    @field_validator("hf_source", "profile_notes")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value must not be blank")
        return value

    @field_validator("local_output_path", mode="before")
    @classmethod
    def reject_blank_path_input(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            raise ValueError("path must not be blank")
        return value


class PilotSelection(BaseModel):
    """Selected laptop baseline winner plus runner-up."""

    model_config = ConfigDict(extra="forbid")

    baseline_winner_id: LockedCandidateId
    runner_up_id: LockedCandidateId
    selection_notes: str | None = None

    @field_validator("selection_notes")
    @classmethod
    def reject_blank_notes(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("selection_notes must not be blank")
        return value

    @model_validator(mode="after")
    def validate_selection(self) -> "PilotSelection":
        if self.baseline_winner_id not in LAPTOP_BASELINE_CANDIDATE_IDS:
            raise ValueError("baseline_winner_id must be one of the locked 4B laptop candidates")
        if self.runner_up_id == self.baseline_winner_id:
            raise ValueError("runner_up_id must differ from baseline_winner_id")
        return self


class ModelArtifactRecord(BaseModel):
    """Metadata for a local model artifact tracked outside git."""

    model_config = ConfigDict(extra="forbid")

    candidate_id: LockedCandidateId
    artifact_type: ArtifactType
    version_tag: str = Field(min_length=1)
    local_path: Path
    sha256: str = Field(min_length=64, max_length=64)
    tracked_in_git: bool = False
    local_only: bool = True
    profile_name: str | None = None

    @field_validator("version_tag", "sha256", "profile_name")
    @classmethod
    def reject_blank_text(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("value must not be blank")
        return value

    @field_validator("local_path", mode="before")
    @classmethod
    def reject_blank_path_input(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            raise ValueError("local_path must not be blank")
        return value

    @model_validator(mode="after")
    def validate_tracking_flags(self) -> "ModelArtifactRecord":
        if self.local_only and self.tracked_in_git:
            raise ValueError("local-only artifacts cannot be marked as tracked in git")
        return self


class ModelRegistry(BaseModel):
    """Persisted selection and artifact metadata for active model work."""

    model_config = ConfigDict(extra="forbid")

    version_tag: str = Field(min_length=1)
    selection: PilotSelection | None = None
    scorecards: list[PilotScorecard] = Field(default_factory=list)
    artifacts: list[ModelArtifactRecord] = Field(default_factory=list)

    @field_validator("version_tag")
    @classmethod
    def reject_blank_version_tag(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("version_tag must not be blank")
        return value


class HeldOutSupportAudit(BaseModel):
    """Typed fail-closed support audit for a held-out release slice."""

    model_config = ConfigDict(extra="forbid")

    evaluated_split_path: Path
    evaluated_split_root: Path | None = None
    locked_label_order: tuple[ThreatLabel, ...] = LOCKED_RELEASE_LABELS
    risky_labels: tuple[RiskyThreatLabel, ...] = LOCKED_RISKY_LABELS
    risky_recall_floor: float = Field(default=UNIFORM_RISKY_RECALL_FLOOR, ge=0.0, le=1.0)
    support_by_label: dict[ThreatLabel, int]
    blocker_reasons: list[str] = Field(default_factory=list)
    ready: bool = False
    verdict: ReleaseVerdict = "BLOCK"

    @field_validator("support_by_label", mode="before")
    @classmethod
    def normalize_support_by_label(cls, value: object) -> dict[ThreatLabel, int]:
        if not isinstance(value, Mapping):
            raise ValueError("support_by_label must be an object")
        unknown_labels = sorted(set(value).difference(LOCKED_RELEASE_LABELS))
        if unknown_labels:
            raise ValueError(f"unknown labels in support_by_label: {', '.join(unknown_labels)}")
        normalized: dict[ThreatLabel, int] = {}
        for label in LOCKED_RELEASE_LABELS:
            count = value.get(label, 0)
            if isinstance(count, bool) or not isinstance(count, int) or count < 0:
                raise ValueError("support counts must be non-negative integers")
            normalized[label] = count
        return normalized

    @field_validator("blocker_reasons")
    @classmethod
    def reject_blank_blocker_reasons(cls, value: list[str]) -> list[str]:
        if any(not reason.strip() for reason in value):
            raise ValueError("blocker reasons must not be blank")
        return value

    @model_validator(mode="after")
    def align_status_with_blockers(self) -> "HeldOutSupportAudit":
        if self.locked_label_order != LOCKED_RELEASE_LABELS:
            raise ValueError("locked_label_order must match the locked release labels")
        if self.risky_labels != LOCKED_RISKY_LABELS:
            raise ValueError("risky_labels must match the locked risky labels")

        root = self.evaluated_split_root
        path = self.evaluated_split_path
        if root is not None:
            if not root.is_absolute() or ".." in root.parts or "\x00" in os.fspath(root):
                raise ValueError("evaluated_split_root must be canonical and absolute")
            root = Path(os.path.abspath(os.path.normpath(os.fspath(root))))
            candidate = path if path.is_absolute() else root / path
            candidate = Path(os.path.abspath(os.path.normpath(os.fspath(candidate))))
            if candidate == root or root not in candidate.parents:
                raise ValueError("evaluated_split_path must be below evaluated_split_root")
            self.evaluated_split_root = root
            self.evaluated_split_path = candidate
        elif not path.is_absolute() or ".." in path.parts or "\x00" in os.fspath(path):
            raise ValueError(
                "evaluated_split_path must be absolute when evaluated_split_root is omitted"
            )

        computed_reasons = [
            f"missing held-out support for {label}"
            for label in LOCKED_RELEASE_LABELS
            if self.support_by_label[label] == 0
        ]
        if "blocker_reasons" in self.model_fields_set and self.blocker_reasons != computed_reasons:
            raise ValueError("blocker_reasons are inconsistent with held-out support")
        computed_ready = not computed_reasons
        computed_verdict: ReleaseVerdict = "PASS" if computed_ready else "BLOCK"
        if "ready" in self.model_fields_set and self.ready is not computed_ready:
            raise ValueError("ready is inconsistent with held-out support")
        if "verdict" in self.model_fields_set and self.verdict != computed_verdict:
            raise ValueError("verdict is inconsistent with held-out support")
        self.blocker_reasons = computed_reasons
        self.ready = computed_ready
        self.verdict = computed_verdict
        return self


class PerLabelMetricRow(BaseModel):
    """Per-label precision, recall, and F1 for release reporting."""

    model_config = ConfigDict(extra="forbid")

    label: ThreatLabel
    precision: float = Field(ge=0.0, le=1.0)
    recall: float = Field(ge=0.0, le=1.0)
    f1: float = Field(ge=0.0, le=1.0)
    support: int = Field(ge=0)
    recall_floor_applies: bool = False

    @model_validator(mode="after")
    def align_risky_label_flag(self) -> "PerLabelMetricRow":
        self.recall_floor_applies = self.label in LOCKED_RISKY_LABELS
        return self


class OverallMetricSummary(BaseModel):
    """Overall held-out metric summary used by the release gate."""

    model_config = ConfigDict(extra="forbid")

    macro_f1: float = Field(ge=0.0, le=1.0)
    weighted_f1: float = Field(ge=0.0, le=1.0)
    evaluated_rows: int = Field(gt=0)


class ExplanationRubricSummary(BaseModel):
    """Merged deterministic and manual explanation-review findings."""

    model_config = ConfigDict(extra="forbid")

    evaluated_risky_predictions: int = Field(ge=0)
    manual_reviewed_predictions: int = Field(ge=0)
    blocker_reasons: list[str] = Field(default_factory=list)
    flag_reasons: list[str] = Field(default_factory=list)

    @field_validator("blocker_reasons", "flag_reasons")
    @classmethod
    def reject_blank_reasons(cls, value: list[str]) -> list[str]:
        if any(not reason.strip() for reason in value):
            raise ValueError("reasons must not be blank")
        return value

    @model_validator(mode="after")
    def validate_review_counts(self) -> "ExplanationRubricSummary":
        if self.manual_reviewed_predictions > self.evaluated_risky_predictions:
            raise ValueError("manual_reviewed_predictions cannot exceed evaluated_risky_predictions")
        return self


class ReleaseEvaluationArtifact(BaseModel):
    """Canonical release-evaluation contract for active read-only consumers."""

    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(min_length=1)
    verdict: ReleaseVerdict
    risky_recall_floor: float = Field(default=UNIFORM_RISKY_RECALL_FLOOR, ge=0.0, le=1.0)
    overall_metrics: OverallMetricSummary
    per_label_metrics: list[PerLabelMetricRow] = Field(default_factory=list)
    blocker_reasons: list[str] = Field(default_factory=list)
    flag_reasons: list[str] = Field(default_factory=list)
    explanation_rubric_summary: ExplanationRubricSummary
    readiness_audit: HeldOutSupportAudit | None = None

    @field_validator("run_id")
    @classmethod
    def reject_blank_run_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("run_id must not be blank")
        return value

    @field_validator("blocker_reasons", "flag_reasons")
    @classmethod
    def reject_blank_release_reasons(cls, value: list[str]) -> list[str]:
        if any(not reason.strip() for reason in value):
            raise ValueError("reasons must not be blank")
        return value

    @model_validator(mode="after")
    def require_full_label_metrics(self) -> "ReleaseEvaluationArtifact":
        metric_labels = [row.label for row in self.per_label_metrics]
        if metric_labels != list(LOCKED_RELEASE_LABELS):
            raise ValueError("per_label_metrics must follow the locked release label order")
        if self.readiness_audit is None:
            raise ValueError("readiness_audit is required")
        support_total = sum(row.support for row in self.per_label_metrics)
        if support_total != self.overall_metrics.evaluated_rows:
            raise ValueError("per-label support must equal evaluated_rows")
        for row in self.per_label_metrics:
            if self.readiness_audit.support_by_label[row.label] != row.support:
                raise ValueError("metric support must match readiness_audit support")

        below_floor = [
            row.label
            for row in self.per_label_metrics
            if row.label in LOCKED_RISKY_LABELS
            and row.recall < RISKY_LABEL_RECALL_FLOORS[row.label]
        ]
        has_blocker = bool(
            self.blocker_reasons
            or self.explanation_rubric_summary.blocker_reasons
            or not self.readiness_audit.ready
            or below_floor
        )
        has_flag = bool(
            self.flag_reasons or self.explanation_rubric_summary.flag_reasons
        )
        expected: ReleaseVerdict = (
            "BLOCK" if has_blocker else "FLAG" if has_flag else "PASS"
        )
        if self.verdict != expected:
            raise ValueError(
                f"verdict {self.verdict!r} is inconsistent with release evidence; "
                f"expected {expected!r}"
            )
        return self


def find_latest_artifact(
    registry: ModelRegistry,
    *,
    candidate_id: str,
    artifact_type: ArtifactType,
) -> ModelArtifactRecord | None:
    """Return the latest matching local artifact without trainer ownership."""

    for artifact in reversed(registry.artifacts):
        if artifact.candidate_id == candidate_id and artifact.artifact_type == artifact_type:
            return artifact
    return None


def _manifest_models(payload: Mapping[str, Any]) -> list[Any]:
    models = payload.get("models", [])
    if not isinstance(models, list):
        raise ArtifactError("download manifest models must be a list")
    return models


def load_download_manifest(output_root: Path) -> dict[str, Path]:
    """Load the candidate-to-local-path mapping from a download manifest."""

    manifest_path = Path(output_root) / "manifests" / "download-manifest.json"
    if not manifest_path.exists():
        return {}
    try:
        payload = strict_json_object(manifest_path, where="download manifest")
    except IntegrityError as exc:
        raise ArtifactError(str(exc)) from exc

    model_paths: dict[str, Path] = {}
    for index, model in enumerate(_manifest_models(payload)):
        if not isinstance(model, Mapping):
            raise ArtifactError(f"download manifest model {index} must be an object")
        candidate_id = model.get("candidate_id")
        local_path = model.get("local_path")
        if not isinstance(candidate_id, str) or not candidate_id:
            raise ArtifactError(
                f"download manifest model {index} requires a non-empty candidate_id"
            )
        if not isinstance(local_path, str) or not local_path:
            raise ArtifactError(
                f"download manifest model {index} requires a non-empty local_path"
            )
        if candidate_id in model_paths:
            raise ArtifactError(
                f"download manifest contains duplicate candidate_id {candidate_id!r}"
            )
        model_paths[candidate_id] = Path(local_path)
    return model_paths


def load_model_registry(input_path: Path) -> ModelRegistry:
    """Load an active model registry from strict UTF-8 JSON."""

    try:
        payload = strict_json_object(Path(input_path), where="model registry")
        return ModelRegistry.model_validate(payload)
    except (IntegrityError, ValidationError) as exc:
        raise ArtifactError(str(exc)) from exc


def save_model_registry(
    registry: ModelRegistry,
    output_path: Path,
    *,
    storage_root: Path,
) -> Path:
    """Publish a new registry below one explicit trusted storage root."""

    target = Path(output_path)
    try:
        root = Path(storage_root)
        if not root.is_absolute() or not target.is_absolute():
            raise IntegrityError("model registry root and path must be absolute")
        if any(".." in path.parts or "\x00" in os.fspath(path) for path in (root, target)):
            raise IntegrityError("model registry root and path must be canonical")
        normalized_root = Path(os.path.abspath(os.path.normpath(os.fspath(root))))
        normalized_target = Path(os.path.abspath(os.path.normpath(os.fspath(target))))
        try:
            relative = normalized_target.relative_to(normalized_root)
        except ValueError as exc:
            raise IntegrityError("model registry must be below model storage root") from exc
        target = prepare_bounded_output(
            normalized_root,
            relative,
            where="model registry",
        )
        serialized = registry.model_dump_json(indent=2).replace("\n", os.linesep)
        atomic_replace_new_artifact(
            target,
            serialized.encode("utf-8"),
            where="model registry",
        )
    except (IntegrityError, OSError) as exc:
        raise ArtifactError(str(exc)) from exc
    return target


def load_release_evaluation_artifact(input_path: Path) -> ReleaseEvaluationArtifact:
    """Load a release artifact without rewriting its source bytes."""

    try:
        payload = strict_json_object(Path(input_path), where="release evaluation artifact")
        return ReleaseEvaluationArtifact.model_validate(payload)
    except (IntegrityError, ValidationError) as exc:
        raise ArtifactError(str(exc)) from exc
