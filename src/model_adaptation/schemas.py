"""Typed metadata models for model adaptation and release evaluation artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.runtime.contracts import ChannelName, RecommendationText, RiskTier, SuspiciousCue, ThreatLabel


LockedCandidateId = Literal[
    "qwen3.5-4b",
    "qwen3-4b-instruct-2507",
    "qwen2.5-7b-instruct",
]
CandidateRole = Literal["primary", "fallback"]
ArtifactType = Literal["adapter", "gguf"]
EvaluatedSplit = Literal["train", "val", "test", "pilot"]
ReleaseVerdict = Literal["PASS", "BLOCK", "FLAG"]
RiskyThreatLabel = Literal["bank_impersonation", "zalo_social_engineering", "task_scam"]

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

# Per-label recall floors — task_scam relaxed to 0.80 per D-01 (linguistically harder class).
RISKY_LABEL_RECALL_FLOORS: dict[str, float] = {
    "bank_impersonation": 0.90,
    "zalo_social_engineering": 0.90,
    "task_scam": 0.80,
}

LOCKED_CANDIDATE_IDS: tuple[LockedCandidateId, ...] = (
    "qwen3.5-4b",
    "qwen3-4b-instruct-2507",
    "qwen2.5-7b-instruct",
)

LAPTOP_BASELINE_CANDIDATE_IDS: tuple[LockedCandidateId, ...] = (
    "qwen3.5-4b",
    "qwen3-4b-instruct-2507",
)


class ModelCandidate(BaseModel):
    """Locked candidate metadata for the Phase 3 Qwen pilot."""

    model_config = ConfigDict(extra="forbid")

    candidate_id: LockedCandidateId
    hf_source: str = Field(min_length=1)
    family: str = Field(min_length=1)
    role: CandidateRole
    size_label: str = Field(min_length=1)
    notes: str = Field(min_length=1)

    @field_validator("hf_source", "family", "size_label", "notes")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value must not be blank")
        return value


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
        if value is None:
            return value
        if isinstance(value, str) and not value.strip():
            raise ValueError("path must not be blank")
        return value


class PilotSelection(BaseModel):
    """Selected laptop baseline winner plus runner-up for later plans."""

    model_config = ConfigDict(extra="forbid")

    baseline_winner_id: LockedCandidateId
    runner_up_id: LockedCandidateId
    selection_notes: str | None = None

    @field_validator("selection_notes")
    @classmethod
    def reject_blank_notes(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if not value.strip():
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
        if value is None:
            return value
        if not value.strip():
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
    """Persisted selection and artifact metadata for Phase 3 model work."""

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
    """Typed fail-closed support audit for the Phase 5 held-out release slice."""

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

    @field_validator("support_by_label")
    @classmethod
    def normalize_support_by_label(cls, value: dict[ThreatLabel, int]) -> dict[ThreatLabel, int]:
        unknown_labels = sorted(set(value).difference(LOCKED_RELEASE_LABELS))
        if unknown_labels:
            raise ValueError(f"unknown labels in support_by_label: {', '.join(unknown_labels)}")

        normalized: dict[ThreatLabel, int] = {}
        for label in LOCKED_RELEASE_LABELS:
            count = int(value.get(label, 0))
            if count < 0:
                raise ValueError("support counts must be non-negative")
            normalized[label] = count
        return normalized

    @field_validator("blocker_reasons")
    @classmethod
    def reject_blank_blocker_reasons(cls, value: list[str]) -> list[str]:
        for reason in value:
            if not reason.strip():
                raise ValueError("blocker reasons must not be blank")
        return value

    @model_validator(mode="after")
    def align_status_with_blockers(self) -> "HeldOutSupportAudit":
        self.ready = not self.blocker_reasons
        self.verdict = "PASS" if self.ready else "BLOCK"
        return self


class ReleaseEvaluationRow(BaseModel):
    """Reviewable evaluation row captured from the public runtime contract."""

    model_config = ConfigDict(extra="forbid")

    gold_label: ThreatLabel
    predicted_labels: list[ThreatLabel] = Field(default_factory=list, max_length=2)
    risk_tier: RiskTier
    summary: str = Field(min_length=1)
    top_cues: list[SuspiciousCue] = Field(default_factory=list, max_length=3)
    recommendations: list[RecommendationText] = Field(default_factory=list, max_length=3)
    backend_name: str = Field(min_length=1)
    channel: ChannelName = "unknown"
    split_provenance: str = Field(min_length=1)
    normalized_text: str | None = None
    reviewable_source_text: str | None = None

    @field_validator("summary", "backend_name", "split_provenance", "normalized_text", "reviewable_source_text")
    @classmethod
    def reject_blank_text(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if not value.strip():
            raise ValueError("value must not be blank")
        return value

    @model_validator(mode="after")
    def require_reviewable_text_source(self) -> "ReleaseEvaluationRow":
        if not self.normalized_text and not self.reviewable_source_text:
            raise ValueError("release evaluation rows require normalized_text or reviewable_source_text")
        return self


class PerLabelMetricRow(BaseModel):
    """Per-label precision/recall/F1 row for held-out reporting."""

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
    evaluated_rows: int = Field(ge=0)


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
        for reason in value:
            if not reason.strip():
                raise ValueError("reasons must not be blank")
        return value

    @model_validator(mode="after")
    def validate_review_counts(self) -> "ExplanationRubricSummary":
        if self.manual_reviewed_predictions > self.evaluated_risky_predictions:
            raise ValueError("manual_reviewed_predictions cannot exceed evaluated_risky_predictions")
        return self


class ReleaseEvaluationArtifact(BaseModel):
    """Canonical release-evaluation artifact shared by markdown and JSON outputs."""

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
        for reason in value:
            if not reason.strip():
                raise ValueError("reasons must not be blank")
        return value

    @model_validator(mode="after")
    def require_full_label_metrics(self) -> "ReleaseEvaluationArtifact":
        metric_labels = [row.label for row in self.per_label_metrics]
        if metric_labels and metric_labels != list(LOCKED_RELEASE_LABELS):
            raise ValueError("per_label_metrics must follow the locked release label order")
        return self


class ReleaseEvaluationSnapshot(BaseModel):
    """Saved phase-local snapshot tying one evaluation run to later review and verdict steps."""

    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(min_length=1)
    evaluated_split_path: Path
    locked_label_order: tuple[ThreatLabel, ...] = LOCKED_RELEASE_LABELS
    audit: HeldOutSupportAudit
    overall_metrics: OverallMetricSummary
    per_label_metrics: list[PerLabelMetricRow] = Field(default_factory=list)
    rows: list[ReleaseEvaluationRow] = Field(default_factory=list)

    @field_validator("run_id")
    @classmethod
    def reject_blank_snapshot_run_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("run_id must not be blank")
        return value

    @model_validator(mode="after")
    def require_locked_metric_order(self) -> "ReleaseEvaluationSnapshot":
        metric_labels = [row.label for row in self.per_label_metrics]
        if metric_labels and metric_labels != list(self.locked_label_order):
            raise ValueError("per_label_metrics must follow the snapshot label order")
        return self


class ExplanationRubricAssessment(BaseModel):
    """Deterministic blocker and flag findings for one risky evaluation row."""

    model_config = ConfigDict(extra="forbid")

    applies: bool = False
    blocker_reasons: list[str] = Field(default_factory=list)
    flag_reasons: list[str] = Field(default_factory=list)

    @field_validator("blocker_reasons", "flag_reasons")
    @classmethod
    def reject_blank_assessment_reasons(cls, value: list[str]) -> list[str]:
        for reason in value:
            if not reason.strip():
                raise ValueError("reasons must not be blank")
        return value


class ExplanationReviewItem(BaseModel):
    """One risky prediction selected for manual explanation review."""

    model_config = ConfigDict(extra="forbid")

    row_index: int = Field(ge=0)
    gold_label: ThreatLabel
    predicted_labels: list[ThreatLabel] = Field(default_factory=list, max_length=2)
    risk_tier: RiskTier
    reviewable_text: str = Field(min_length=1)
    top_cues: list[SuspiciousCue] = Field(default_factory=list, max_length=3)
    recommendations: list[RecommendationText] = Field(default_factory=list, max_length=3)
    deterministic_blocker_reasons: list[str] = Field(default_factory=list)
    deterministic_flag_reasons: list[str] = Field(default_factory=list)
    reviewer_blocker_reasons: list[str] = Field(default_factory=list)
    reviewer_flag_reasons: list[str] = Field(default_factory=list)

    @field_validator(
        "reviewable_text",
        "deterministic_blocker_reasons",
        "deterministic_flag_reasons",
        "reviewer_blocker_reasons",
        "reviewer_flag_reasons",
    )
    @classmethod
    def reject_blank_review_item_fields(cls, value: str | list[str]) -> str | list[str]:
        if isinstance(value, str):
            if not value.strip():
                raise ValueError("value must not be blank")
            return value
        for reason in value:
            if not reason.strip():
                raise ValueError("reasons must not be blank")
        return value


class ExplanationReviewPack(BaseModel):
    """Phase-local risky-only review pack generated before the final release verdict."""

    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(min_length=1)
    source_snapshot_path: Path
    items: list[ExplanationReviewItem] = Field(default_factory=list)
    review_completed: bool = False
    review_notes: str | None = None

    @field_validator("run_id")
    @classmethod
    def reject_blank_review_pack_run_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("run_id must not be blank")
        return value

    @field_validator("review_notes")
    @classmethod
    def reject_blank_review_notes(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if not value.strip():
            raise ValueError("review_notes must not be blank")
        return value