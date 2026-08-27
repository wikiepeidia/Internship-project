"""Phase-neutral contracts and readers for active runtime artifacts."""

from __future__ import annotations

import os
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Mapping

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from src.core.integrity import (
    IntegrityError,
    artifact_digest,
    atomic_replace_new_artifact,
    bounded_descendant,
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
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
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
        candidate = Path(value) if isinstance(value, (str, os.PathLike)) else None
        if candidate is not None and (
            candidate.is_absolute()
            or ".." in candidate.parts
            or "\x00" in os.fspath(candidate)
        ):
            raise ValueError("local_path must be a normalized relative path")
        return value

    @model_validator(mode="after")
    def validate_tracking_flags(self) -> "ModelArtifactRecord":
        if not self.local_only or self.tracked_in_git:
            raise ValueError("model artifacts must be local-only and untracked")
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
    @model_validator(mode="after")
    def align_artifact_versions(self) -> "ModelRegistry":
        if any(artifact.version_tag != self.version_tag for artifact in self.artifacts):
            raise ValueError("artifact version_tag must match registry version_tag")
        return self


class DownloadedModelRecord(BaseModel):
    """Strict hashed identity for one locally downloaded base model."""
    model_config = ConfigDict(extra="forbid")
    candidate_id: LockedCandidateId
    local_path: Path
    revision: str = Field(min_length=1, pattern=r"^.*\S.*$")
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    file_count: int = Field(gt=0)
    total_bytes: int = Field(ge=0)
    @field_validator("local_path", mode="before")
    @classmethod
    def require_relative_model_path(cls, value: object) -> object:
        candidate = Path(value) if isinstance(value, (str, os.PathLike)) else None
        if candidate is None or candidate.is_absolute() or ".." in candidate.parts:
            raise ValueError("downloaded model path must be relative")
        if "\x00" in os.fspath(candidate) or not os.fspath(candidate).strip():
            raise ValueError("downloaded model path must be canonical and non-empty")
        return value


class DownloadManifest(BaseModel):
    """Strict v2 inventory for locally downloaded base models."""
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["model-download-manifest-v2"]
    models: list[DownloadedModelRecord]
    @model_validator(mode="after")
    def reject_duplicate_candidates(self) -> "DownloadManifest":
        candidates = [model.candidate_id for model in self.models]
        if len(candidates) != len(set(candidates)):
            raise ValueError("download manifest contains duplicate candidate_id")
        return self


@dataclass(frozen=True)
class VerifiedArtifact:
    """Root-bound artifact identity safe to reverify immediately before loading."""
    root: Path
    relative_path: Path
    candidate_id: str
    sha256: str
    file_count: int | None = None
    total_bytes: int | None = None
    @property
    def path(self) -> Path:
        return bounded_descendant(self.root, self.relative_path, where="model artifact")


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
        if self.risky_recall_floor != UNIFORM_RISKY_RECALL_FLOOR:
            raise ValueError("risky_recall_floor must match the immutable release floor")

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
        denominator = self.precision + self.recall
        computed_f1 = (
            0.0 if denominator == 0.0 else 2.0 * self.precision * self.recall / denominator
        )
        if not math.isclose(self.f1, computed_f1, rel_tol=0.0, abs_tol=1e-9):
            raise ValueError("f1 must be recomputed from precision and recall")
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
        if self.risky_recall_floor != UNIFORM_RISKY_RECALL_FLOOR:
            raise ValueError("risky_recall_floor must match the immutable release floor")
        if self.readiness_audit.risky_recall_floor != self.risky_recall_floor:
            raise ValueError("release and readiness risky_recall_floor values must agree")
        support_total = sum(row.support for row in self.per_label_metrics)
        if support_total != self.overall_metrics.evaluated_rows:
            raise ValueError("per-label support must equal evaluated_rows")
        for row in self.per_label_metrics:
            if self.readiness_audit.support_by_label[row.label] != row.support:
                raise ValueError("metric support must match readiness_audit support")

        expected_macro_f1 = sum(row.f1 for row in self.per_label_metrics) / len(
            self.per_label_metrics
        )
        expected_weighted_f1 = (
            sum(row.f1 * row.support for row in self.per_label_metrics) / support_total
        )
        if not math.isclose(
            self.overall_metrics.macro_f1,
            expected_macro_f1,
            rel_tol=0.0,
            abs_tol=1e-9,
        ):
            raise ValueError("overall macro_f1 must match per-label metrics")
        if not math.isclose(
            self.overall_metrics.weighted_f1,
            expected_weighted_f1,
            rel_tol=0.0,
            abs_tol=1e-9,
        ):
            raise ValueError("overall weighted_f1 must match supported per-label metrics")

        below_floor = [
            row.label
            for row in self.per_label_metrics
            if row.label in LOCKED_RISKY_LABELS
            and row.recall < self.risky_recall_floor
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


def _bounded_supplied(root: Path, supplied: Path, *, where: str) -> Path:
    trusted_root = Path(root)
    if not trusted_root.is_absolute():
        raise IntegrityError(f"{where} root must be absolute")
    candidate = Path(supplied)
    if candidate.is_absolute():
        try:
            candidate = candidate.relative_to(trusted_root)
        except ValueError as exc:
            raise IntegrityError(f"{where} must be below its trusted root") from exc
    return bounded_descendant(trusted_root, candidate, where=where)


def load_download_manifest(output_root: Path) -> dict[str, DownloadedModelRecord]:
    """Load a strict, root-bound base-model manifest without verifying loaders."""
    try:
        manifest_path = _bounded_supplied(
            Path(output_root),
            Path("manifests/download-manifest.json"),
            where="download manifest",
        )
        try:
            os.lstat(manifest_path)
        except FileNotFoundError:
            return {}
        payload = strict_json_object(manifest_path, where="download manifest")
        manifest = DownloadManifest.model_validate(payload)
    except (IntegrityError, OSError, ValidationError) as exc:
        raise ArtifactError(str(exc)) from exc
    return {record.candidate_id: record for record in manifest.models}


def verify_artifact_identity(artifact: VerifiedArtifact) -> Path:
    """Reverify one root-bound identity and return its canonical local path."""
    try:
        path = artifact.path
        digest, file_count, total_bytes = artifact_digest(path)
    except (IntegrityError, OSError) as exc:
        raise ArtifactError(str(exc)) from exc
    if digest != artifact.sha256:
        raise ArtifactError("model artifact SHA-256 mismatch")
    if artifact.file_count is not None and file_count != artifact.file_count:
        raise ArtifactError("model artifact file count mismatch")
    if artifact.total_bytes is not None and total_bytes != artifact.total_bytes:
        raise ArtifactError("model artifact byte count mismatch")
    return path


def resolve_downloaded_model(output_root: Path, candidate_id: str) -> VerifiedArtifact:
    """Resolve and verify one strict base-model manifest record."""
    record = load_download_manifest(output_root).get(candidate_id)
    if record is None:
        raise FileNotFoundError(f"Missing base model manifest entry for candidate_id={candidate_id}")
    artifact = VerifiedArtifact(
        root=Path(output_root),
        relative_path=record.local_path,
        candidate_id=record.candidate_id,
        sha256=record.sha256,
        file_count=record.file_count,
        total_bytes=record.total_bytes,
    )
    verify_artifact_identity(artifact)
    return artifact


def load_model_registry(input_path: Path, *, storage_root: Path) -> ModelRegistry:
    """Load an active model registry from strict UTF-8 JSON."""
    try:
        target = _bounded_supplied(
            Path(storage_root), Path(input_path), where="model registry"
        )
        payload = strict_json_object(target, where="model registry")
        return ModelRegistry.model_validate(payload)
    except (IntegrityError, OSError, ValidationError) as exc:
        raise ArtifactError(str(exc)) from exc


def resolve_registry_artifact(
    registry: ModelRegistry,
    *,
    artifact_root: Path,
    candidate_id: str,
    artifact_type: ArtifactType,
    profile_name: str,
) -> VerifiedArtifact:
    """Resolve and verify one exact registry artifact identity."""
    record = find_latest_artifact(
        registry, candidate_id=candidate_id, artifact_type=artifact_type
    )
    if record is None:
        raise FileNotFoundError(
            f"Missing {artifact_type} artifact for candidate_id={candidate_id}"
        )
    if record.profile_name != profile_name:
        raise ArtifactError("model artifact profile does not match the runtime profile")
    artifact = VerifiedArtifact(
        root=Path(artifact_root),
        relative_path=record.local_path,
        candidate_id=record.candidate_id,
        sha256=record.sha256,
    )
    verify_artifact_identity(artifact)
    return artifact


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
