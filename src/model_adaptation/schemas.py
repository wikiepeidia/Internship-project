"""Typed metadata models for Phase 3 model selection and artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


LockedCandidateId = Literal[
    "qwen3.5-4b",
    "qwen3-4b-instruct-2507",
    "qwen2.5-7b-instruct",
]
CandidateRole = Literal["primary", "fallback"]
ArtifactType = Literal["adapter", "gguf"]
EvaluatedSplit = Literal["train", "val", "test", "pilot"]

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