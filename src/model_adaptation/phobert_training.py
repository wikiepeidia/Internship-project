"""Full PhoBERT classification-head training for Phase 40.

This module is deliberately separate from the Qwen adapter path.  It lazily
loads only the encoder training stack, preserves the canonical snapshot row
identities through preprocessing and every validation checkpoint, and emits
the same metric/evidence contract consumed by the Phase 40 comparison.

The public runner is dependency-injectable so its complete lifecycle can be
proved without downloading a model or using a GPU.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
import hashlib
import importlib
import importlib.metadata
import inspect
import json
import math
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
from statistics import median
import tempfile
import time
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.model_adaptation.phase40_contract import (
    CanonicalSplitSnapshot,
    Phase40DataContract,
)
from src.model_adaptation.phase40_callbacks import (
    CallbackEventKind,
    CudaTimingAdapter,
    NoCudaTimingAdapter,
    Phase40CallbackEvent,
    Phase40EvidenceCallback,
    Phase40ResourceSummary,
    TorchCudaTimingAdapter,
)
from src.model_adaptation.phase40_evidence import (
    AcceleratorIdentity,
    ArtifactEvidence,
    CadenceControls,
    CanonicalSplitEvidence,
    EvidenceStatus,
    ExperimentIdentityEvidence,
    NamedControl,
    OptimizerControls,
    PrecisionControls,
    ResumeControlledConfig,
    RunEvent,
    RunEventKind,
    RunEvidence,
    RuntimeHardwareEvidence,
    SelectedCheckpointEvidence,
    TransferAuthorityEvidence,
    ValidationCheckpointEvidence,
    append_run_event,
    compute_resume_digest,
    finalize_run_evidence,
    load_run_events,
    sanitize_argv,
    sanitize_package_versions,
    verify_phase40_bundle,
)
from src.model_adaptation.phase40_graphs import GraphRenderer, render_phase40_graphs
from src.model_adaptation.phase40_metrics import (
    LABEL_ORDER,
    CheckpointSelection,
    Phase40MetricResult,
    Phase40PredictionRow,
    PredictionState,
    evaluate_phase40_predictions,
    select_phase40_checkpoint,
)
from src.model_adaptation.phase40_modes import AdaptationMode, ModelFamily, RunKind
from src.model_adaptation.registry import build_model_checksum


PHOBERT_MODEL_ID = "vinai/phobert-base-v2"
PHOBERT_MODEL_REVISION = "e966aac8cb889325e073aa5f28ff70aca4dbc8c3"
PHOBERT_SEGMENTER_PACKAGE = "underthesea"
PHOBERT_SEGMENTER_VERSION = "9.5.0"
PHOBERT_PREPROCESSOR_VERSION = "phase40-phobert-preprocessor-v1"
PHOBERT_MAX_LENGTH = 256
PHOBERT_LABEL_TO_ID = {label: index for index, label in enumerate(LABEL_ORDER)}
PHOBERT_ID_TO_LABEL = {index: label for label, index in PHOBERT_LABEL_TO_ID.items()}
PHOBERT_SELECTION_POLICY = "risky-recall-zero-invalid-macro-f1-risky-benign-earlier-step-v1"
PHOBERT_SNAPSHOT_ID_VERSION = "phase40-snapshot-row-id-v1"
_SAFE_RUN_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,95}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_WEIGHT_NAMES = frozenset({"model.safetensors", "pytorch_model.bin"})
PHOBERT_RESUME_MANIFEST_NAME = "phase40-resume-manifest.json"
PHOBERT_BASE_PROVENANCE_SCHEMA = "phase40-phobert-base-provenance-v1"
PHOBERT_BASE_MODEL_MANIFEST_NAME = "phase40-base-model-provenance.json"


def _lexical_absolute(path: Path) -> Path:
    return Path(os.path.abspath(os.path.normpath(os.fspath(path))))


def _reject_symlink_ancestors(path: Path, *, description: str) -> Path:
    """Return a lexical absolute path only when every existing component is real."""

    absolute = _lexical_absolute(Path(path))
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"{description} traverses a symlink: {current}")
    return absolute


def _reject_tree_symlinks(root: Path, *, description: str) -> None:
    root = _reject_symlink_ancestors(root, description=description)
    if root.exists() and any(entry.is_symlink() for entry in root.rglob("*")):
        raise ValueError(f"{description} contains a symlink")


class PhoBertResumeCandidate(BaseModel):
    """One already-evaluated checkpoint retained across an exact resume."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    optimizer_step: int = Field(ge=0)
    artifact_identity: str
    retained_model_relative_path: str
    predictions_relative_path: str
    predictions_sha256: str
    metrics_relative_path: str
    metrics_sha256: str

    @field_validator("artifact_identity")
    @classmethod
    def validate_model_identity(cls, value: str) -> str:
        prefix = "model-state-sha256:"
        if not value.startswith(prefix) or not _SHA256_RE.fullmatch(value.removeprefix(prefix)):
            raise ValueError("resume candidate requires a model-state-sha256 identity")
        return value

    @field_validator("predictions_sha256", "metrics_sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if not _SHA256_RE.fullmatch(value):
            raise ValueError("resume candidate SHA-256 is invalid")
        return value


class PhoBertResumeTelemetry(BaseModel):
    """Cumulative, event-derived resource facts sealed at one checkpoint."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["phase40-phobert-resume-telemetry-v1"]
    observed_optimizer_steps: int = Field(gt=0)
    retained_step_durations_seconds: tuple[float, ...]
    retained_examples: int = Field(ge=0)
    retained_tokens: int = Field(ge=0)
    peak_allocated_bytes: int = Field(ge=0)
    peak_reserved_bytes: int = Field(ge=0)
    evaluation_overhead_seconds: float = Field(ge=0)
    checkpoint_overhead_seconds: float = Field(ge=0)
    attempt_count: int = Field(gt=0)
    actual_wall_seconds: float = Field(gt=0)

    @model_validator(mode="after")
    def validate_resource_facts(self) -> "PhoBertResumeTelemetry":
        if self.peak_reserved_bytes < self.peak_allocated_bytes:
            raise ValueError("PhoBERT resume peak reserved bytes cannot be below allocated bytes")
        if any(not math.isfinite(value) or value <= 0 for value in self.retained_step_durations_seconds):
            raise ValueError("PhoBERT resume retained step durations must be positive and finite")
        for value in (
            self.evaluation_overhead_seconds,
            self.checkpoint_overhead_seconds,
            self.actual_wall_seconds,
        ):
            if not math.isfinite(value):
                raise ValueError("PhoBERT resume resource seconds must be finite")
        if self.retained_step_durations_seconds:
            if self.retained_examples <= 0 or self.retained_tokens <= 0:
                raise ValueError("PhoBERT retained timings require positive example/token totals")
        elif self.retained_examples or self.retained_tokens:
            raise ValueError("PhoBERT retained totals cannot exist without retained timings")
        if len(self.retained_step_durations_seconds) > self.observed_optimizer_steps:
            raise ValueError("PhoBERT retained timings cannot exceed observed optimizer steps")
        return self


class PhoBertBaseModelProvenance(BaseModel):
    """Offline authority binding the exact local snapshot to the approved model."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["phase40-phobert-base-provenance-v1"]
    model_id: Literal[PHOBERT_MODEL_ID]
    model_revision: Literal[PHOBERT_MODEL_REVISION]
    local_path_sha256: str
    content_sha256: str
    file_count: int = Field(gt=0)
    total_bytes: int = Field(gt=0)

    @field_validator("local_path_sha256", "content_sha256")
    @classmethod
    def validate_digest(cls, value: str) -> str:
        if not _SHA256_RE.fullmatch(value):
            raise ValueError("PhoBERT base-model provenance SHA-256 is invalid")
        return value


@dataclass(frozen=True, slots=True)
class PhoBertBaseModelAcquisitionRequest:
    """Network-free specification for an operator-owned pinned download."""

    model_id: str
    model_revision: str
    local_snapshot_path: Path

    def __post_init__(self) -> None:
        if self.model_id != PHOBERT_MODEL_ID or self.model_revision != PHOBERT_MODEL_REVISION:
            raise ValueError("PhoBERT acquisition is locked to the exact Phase 40 model revision")
        if not self.local_snapshot_path.is_absolute():
            raise ValueError("PhoBERT acquisition destination must be absolute")
        _reject_symlink_ancestors(
            self.local_snapshot_path, description="PhoBERT acquisition destination"
        )

    def snapshot_download_kwargs(self) -> dict[str, object]:
        return {
            "repo_id": self.model_id,
            "revision": self.model_revision,
            "local_dir": str(self.local_snapshot_path),
        }


@dataclass(frozen=True, slots=True)
class PhoBertBaseModelSnapshot:
    """Validated local bytes and canonical provenance for the pinned snapshot."""

    model_id: str
    model_revision: str
    local_snapshot_path: Path
    manifest_path: Path
    snapshot_content_sha256: str
    manifest_sha256: str
    local_path_sha256: str
    file_count: int
    total_bytes: int

    def __post_init__(self) -> None:
        if self.model_id != PHOBERT_MODEL_ID or self.model_revision != PHOBERT_MODEL_REVISION:
            raise ValueError("PhoBERT snapshot identity or pinned revision drifted")
        if not self.local_snapshot_path.is_absolute() or not self.manifest_path.is_absolute():
            raise ValueError("PhoBERT snapshot and manifest paths must be absolute")
        for digest in (
            self.snapshot_content_sha256,
            self.manifest_sha256,
            self.local_path_sha256,
        ):
            if not _SHA256_RE.fullmatch(digest):
                raise ValueError("PhoBERT snapshot SHA-256 is invalid")
        if self.file_count <= 0 or self.total_bytes <= 0:
            raise ValueError("PhoBERT snapshot inventory must be non-empty")

    def portable_manifest(self) -> dict[str, object]:
        return PhoBertBaseModelProvenance(
            schema_version=PHOBERT_BASE_PROVENANCE_SCHEMA,
            model_id=self.model_id,
            model_revision=self.model_revision,
            local_path_sha256=self.local_path_sha256,
            content_sha256=self.snapshot_content_sha256,
            file_count=self.file_count,
            total_bytes=self.total_bytes,
        ).model_dump(mode="json")


class PhoBertResumeManifest(BaseModel):
    """Exact, run-bound resume authority sealed inside one Trainer checkpoint."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["phase40-phobert-resume-v2"]
    run_id: str
    checkpoint_step: int = Field(gt=0)
    checkpoint_relative_path: str
    checkpoint_payload_sha256: str
    model_state_identity: str
    controlled_config_digest: str
    model_id: Literal[PHOBERT_MODEL_ID]
    model_revision: Literal[PHOBERT_MODEL_REVISION]
    base_model_content_sha256: str
    base_model_manifest_sha256: str
    base_model_local_path_sha256: str
    preprocessor_sha256: str
    validation_row_ids_sha256: str
    sealed_event_bytes: int = Field(gt=0)
    sealed_event_sha256: str
    telemetry_sha256: str
    telemetry: PhoBertResumeTelemetry
    candidates: tuple[PhoBertResumeCandidate, ...] = Field(min_length=1)

    @field_validator(
        "checkpoint_payload_sha256",
        "controlled_config_digest",
        "base_model_content_sha256",
        "base_model_manifest_sha256",
        "base_model_local_path_sha256",
        "preprocessor_sha256",
        "validation_row_ids_sha256",
        "sealed_event_sha256",
        "telemetry_sha256",
    )
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if not _SHA256_RE.fullmatch(value):
            raise ValueError("PhoBERT resume manifest SHA-256 is invalid")
        return value

    @field_validator("model_state_identity")
    @classmethod
    def validate_model_identity(cls, value: str) -> str:
        return PhoBertResumeCandidate.validate_model_identity(value)

    @model_validator(mode="after")
    def validate_candidate_history(self) -> "PhoBertResumeManifest":
        keys = tuple((item.optimizer_step, item.artifact_identity) for item in self.candidates)
        if keys != tuple(sorted(keys)) or len(set(keys)) != len(keys):
            raise ValueError("PhoBERT resume candidates must be unique and deterministically ordered")
        if (self.checkpoint_step, self.model_state_identity) not in set(keys):
            raise ValueError("resume checkpoint state is absent from its candidate history")
        expected_telemetry_sha256 = hashlib.sha256(
            b"phase40-phobert-resume-telemetry-v1\0"
            + _canonical_json_bytes(self.telemetry.model_dump(mode="json"))
        ).hexdigest()
        if self.telemetry_sha256 != expected_telemetry_sha256:
            raise ValueError("PhoBERT resume telemetry SHA-256 mismatch")
        return self


def _canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


_PREPROCESSOR_POLICY = {
    "schema_version": PHOBERT_PREPROCESSOR_VERSION,
    "model_id": PHOBERT_MODEL_ID,
    "model_revision": PHOBERT_MODEL_REVISION,
    "segmenter": "underthesea.word_tokenize(format=text)",
    "segmenter_version": PHOBERT_SEGMENTER_VERSION,
    "max_length": PHOBERT_MAX_LENGTH,
    "truncation": "right",
    "padding": "dynamic-longest",
    "label_order": list(LABEL_ORDER),
}
PHOBERT_PREPROCESSOR_SHA256 = hashlib.sha256(
    b"phase40-phobert-preprocessor-v1\0" + _canonical_json_bytes(_PREPROCESSOR_POLICY)
).hexdigest()


@dataclass(frozen=True, slots=True)
class PhoBertSegmentation:
    """One raw message after deterministic segmentation and token counting."""

    raw_text: str
    segmented_text: str
    token_count: int
    retained_token_count: int
    truncated: bool
    max_length: int
    segmenter_version: str
    preprocessor_version: str
    preprocessor_sha256: str
    input_ids: tuple[int, ...]
    attention_mask: tuple[int, ...]

    def __post_init__(self) -> None:
        self.raw_text.encode("utf-8", errors="strict")
        self.segmented_text.encode("utf-8", errors="strict")
        if not self.raw_text or not self.segmented_text.strip():
            raise ValueError("raw and segmented PhoBERT text must be non-empty")
        if self.segmenter_version != PHOBERT_SEGMENTER_VERSION:
            raise ValueError("PhoBERT segmenter version differs from the frozen package pin")
        if self.preprocessor_version != PHOBERT_PREPROCESSOR_VERSION:
            raise ValueError("PhoBERT preprocessor version drift")
        if self.preprocessor_sha256 != PHOBERT_PREPROCESSOR_SHA256:
            raise ValueError("PhoBERT preprocessor policy hash drift")
        if self.max_length != PHOBERT_MAX_LENGTH:
            raise ValueError("PhoBERT max length must remain 256")
        if self.token_count < 1 or self.retained_token_count < 1:
            raise ValueError("PhoBERT tokenization cannot produce an empty row")
        if self.retained_token_count != len(self.input_ids):
            raise ValueError("retained token count differs from input_ids")
        if len(self.attention_mask) != len(self.input_ids):
            raise ValueError("attention_mask length differs from input_ids")
        if any(not isinstance(value, int) or isinstance(value, bool) for value in self.input_ids):
            raise ValueError("input_ids must contain integers")
        if any(value not in (0, 1) for value in self.attention_mask):
            raise ValueError("attention_mask must contain zero or one")
        if self.truncated != (self.token_count > self.retained_token_count):
            raise ValueError("PhoBERT truncation flag differs from retained token counts")
        if self.retained_token_count > self.max_length:
            raise ValueError("PhoBERT tokenization exceeds the 256-token model limit")


@dataclass(frozen=True, slots=True)
class PhoBertPreprocessingRecord:
    """Canonical snapshot identity plus its exact PhoBERT model input."""

    split_name: Literal["train", "val"]
    canonical_index: int
    snapshot_row_id: str
    source_row_sha256: str
    gold_label: str
    label_id: int
    segmentation: PhoBertSegmentation

    def __post_init__(self) -> None:
        if self.canonical_index < 0:
            raise ValueError("canonical_index must be non-negative")
        if not self.snapshot_row_id or not _SHA256_RE.fullmatch(self.source_row_sha256):
            raise ValueError("preprocessing record lacks a canonical source identity")
        if self.gold_label not in LABEL_ORDER:
            raise ValueError("preprocessing gold label is outside the locked label order")
        if self.label_id != PHOBERT_LABEL_TO_ID[self.gold_label]:
            raise ValueError("preprocessing label ID differs from the locked label mapping")

    def model_inputs(self) -> dict[str, object]:
        return {
            "input_ids": list(self.segmentation.input_ids),
            "attention_mask": list(self.segmentation.attention_mask),
            "labels": self.label_id,
        }

    def as_json_dict(self) -> dict[str, object]:
        return {
            "split_name": self.split_name,
            "canonical_index": self.canonical_index,
            "snapshot_row_id": self.snapshot_row_id,
            "source_row_sha256": self.source_row_sha256,
            "raw_text": self.segmentation.raw_text,
            "segmented_text": self.segmentation.segmented_text,
            "gold_label": self.gold_label,
            "label_id": self.label_id,
            "token_count": self.segmentation.token_count,
            "retained_token_count": self.segmentation.retained_token_count,
            "truncated": self.segmentation.truncated,
            "max_length": self.segmentation.max_length,
            "segmenter_version": self.segmentation.segmenter_version,
            "preprocessor_version": self.segmentation.preprocessor_version,
            "preprocessor_sha256": self.segmentation.preprocessor_sha256,
        }


@dataclass(frozen=True, slots=True)
class PhoBertRawPredictionRow:
    """Four raw classifier logits bound to one immutable validation row."""

    validation_row_id: str
    canonical_index: int
    source_row_sha256: str
    raw_message: str
    gold_label: str
    logits: tuple[float, float, float, float]
    argmax_state: str
    artifact_identity: str
    checkpoint_step: int

    def __post_init__(self) -> None:
        if not self.validation_row_id or self.canonical_index < 0:
            raise ValueError("PhoBERT prediction lacks its canonical validation identity")
        if not _SHA256_RE.fullmatch(self.source_row_sha256):
            raise ValueError("PhoBERT prediction source row SHA-256 is invalid")
        self.raw_message.encode("utf-8", errors="strict")
        if self.gold_label not in LABEL_ORDER or self.argmax_state not in LABEL_ORDER:
            raise ValueError("PhoBERT prediction uses a label outside the locked order")
        if len(self.logits) != len(LABEL_ORDER) or any(
            isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)
            for value in self.logits
        ):
            raise ValueError("PhoBERT prediction requires exactly four finite raw logits")
        expected = LABEL_ORDER[max(range(len(self.logits)), key=lambda index: self.logits[index])]
        if self.argmax_state != expected:
            raise ValueError("PhoBERT argmax state differs from the retained raw logits")
        prefix = "model-state-sha256:"
        if not self.artifact_identity.startswith(prefix) or not _SHA256_RE.fullmatch(
            self.artifact_identity.removeprefix(prefix)
        ):
            raise ValueError("PhoBERT checkpoint requires a model-state-sha256 identity")
        if self.checkpoint_step < 0:
            raise ValueError("checkpoint_step must be non-negative")

    def as_metric_row(self) -> Phase40PredictionRow:
        raw_prediction = json.dumps(
            {"label": self.argmax_state},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return Phase40PredictionRow(
            validation_row_id=self.validation_row_id,
            sequence_index=self.canonical_index,
            gold_label=self.gold_label,
            raw_prediction=raw_prediction,
            parsed_state=PredictionState(self.argmax_state),
            parser_exception=None,
            artifact_identity=self.artifact_identity,
            checkpoint_step=self.checkpoint_step,
        )

    def as_json_dict(self) -> dict[str, object]:
        return {
            "validation_row_id": self.validation_row_id,
            "canonical_index": self.canonical_index,
            "sequence_index": self.canonical_index,
            "source_row_sha256": self.source_row_sha256,
            "raw_message": self.raw_message,
            "gold_label": self.gold_label,
            "label_order": list(LABEL_ORDER),
            "logits": list(self.logits),
            "argmax_state": self.argmax_state,
            "artifact_identity": self.artifact_identity,
            "checkpoint_step": self.checkpoint_step,
        }


@dataclass(frozen=True, slots=True)
class PhoBertTrainingConfig:
    """Frozen controls for the only supported PhoBERT experiment tuple."""

    run_id: str
    run_bundle_root: Path
    work_root: Path
    local_base_model_path: Path
    transfer_authority: TransferAuthorityEvidence
    sanitized_argv: tuple[str, ...]
    base_model_provenance_path: Path | None = None
    model_id: str = PHOBERT_MODEL_ID
    model_revision: str = PHOBERT_MODEL_REVISION
    seed: int = 42
    data_seed: int = 42
    max_length: int = PHOBERT_MAX_LENGTH
    per_device_train_batch_size: int = 16
    gradient_accumulation_steps: int = 1
    num_train_epochs: float = 3.0
    max_optimizer_steps: int = 312
    learning_rate: float = 2e-5
    weight_decay: float = 0.01
    optimizer_name: str = "adamw_torch"
    lr_scheduler_type: str = "linear"
    warmup_steps: int = 0
    warmup_ratio: float = 0.1
    max_grad_norm: float = 1.0
    logging_steps: int = 10
    evaluation_steps: int = 50
    save_total_limit: int = 2
    gradient_checkpointing: bool = False
    bf16: bool = False
    fp16: bool = True
    tf32: bool = False
    local_files_only: bool = True
    resume_from_checkpoint: Path | None = None

    def __post_init__(self) -> None:
        if not _SAFE_RUN_ID_RE.fullmatch(self.run_id):
            raise ValueError("PhoBERT run_id must be a safe normalized identifier")
        if self.model_id != PHOBERT_MODEL_ID or self.model_revision != PHOBERT_MODEL_REVISION:
            raise ValueError("PhoBERT model ID and immutable revision are fixed")
        if self.seed != 42 or self.data_seed != 42:
            raise ValueError("PhoBERT Phase 40 seeds are fixed at 42")
        if self.max_length != PHOBERT_MAX_LENGTH:
            raise ValueError("PhoBERT max_length must remain 256")
        positive_ints = (
            self.per_device_train_batch_size,
            self.gradient_accumulation_steps,
            self.max_optimizer_steps,
            self.logging_steps,
            self.evaluation_steps,
            self.save_total_limit,
        )
        if any(isinstance(value, bool) or not isinstance(value, int) or value <= 0 for value in positive_ints):
            raise ValueError("PhoBERT batch, step, and cadence controls must be positive integers")
        if self.num_train_epochs <= 0 or self.learning_rate <= 0 or self.weight_decay < 0:
            raise ValueError("PhoBERT optimizer controls are invalid")
        if self.warmup_steps < 0 or not 0 <= self.warmup_ratio <= 1 or self.max_grad_norm <= 0:
            raise ValueError("PhoBERT warmup/gradient controls are invalid")
        if self.bf16 and self.fp16:
            raise ValueError("PhoBERT cannot enable BF16 and FP16 together")
        if not isinstance(self.transfer_authority, TransferAuthorityEvidence):
            raise ValueError("complete PhoBERT training requires request-bound transfer authority")
        sanitize_argv(self.sanitized_argv)
        if self.resume_from_checkpoint is not None and str(self.resume_from_checkpoint).casefold() == "latest":
            raise ValueError("PhoBERT resume requires an exact checkpoint path; latest is forbidden")
        if not self.run_bundle_root.is_absolute() or not self.work_root.is_absolute():
            raise ValueError("PhoBERT run_bundle_root and work_root must be absolute")
        bundle_root = _reject_symlink_ancestors(
            self.run_bundle_root, description="PhoBERT run_bundle_root"
        )
        work_root = _reject_symlink_ancestors(self.work_root, description="PhoBERT work_root")
        if not self.local_base_model_path.is_absolute():
            raise ValueError("PhoBERT local base-model path must be absolute")
        base_root = _reject_symlink_ancestors(
            self.local_base_model_path, description="PhoBERT local base-model path"
        )
        configured_provenance_path = (
            base_root.with_name(f"{base_root.name}.provenance.json")
            if self.base_model_provenance_path is None
            else self.base_model_provenance_path
        )
        if not configured_provenance_path.is_absolute():
            raise ValueError("PhoBERT base-model provenance path must be absolute")
        provenance_path = _reject_symlink_ancestors(
            configured_provenance_path, description="PhoBERT base-model provenance path"
        )
        if self.resume_from_checkpoint is not None and self.resume_from_checkpoint.is_absolute():
            _reject_symlink_ancestors(
                self.resume_from_checkpoint, description="PhoBERT resume checkpoint"
            )
        if bundle_root == work_root or bundle_root in work_root.parents or work_root in bundle_root.parents:
            raise ValueError("PhoBERT returned bundle and mutable work roots must be disjoint")
        for output_root in (bundle_root, work_root):
            if (
                output_root == base_root
                or output_root in base_root.parents
                or base_root in output_root.parents
                or output_root == provenance_path
                or output_root in provenance_path.parents
            ):
                raise ValueError("PhoBERT base-model authority must be disjoint from output roots")
        if provenance_path == base_root or base_root in provenance_path.parents:
            raise ValueError("PhoBERT provenance manifest must be external to the snapshot")

    @property
    def identity(self) -> ExperimentIdentityEvidence:
        return ExperimentIdentityEvidence(
            model_family=ModelFamily.PHOBERT,
            adaptation_mode=AdaptationMode.CLASSIFICATION_HEAD,
            run_kind=RunKind.FULL,
        )

    @property
    def resolved_base_model_provenance_path(self) -> Path:
        base_root = _lexical_absolute(self.local_base_model_path)
        return (
            base_root.with_name(f"{base_root.name}.provenance.json")
            if self.base_model_provenance_path is None
            else _lexical_absolute(self.base_model_provenance_path)
        )

    @property
    def evaluation_schedule(self) -> tuple[int, ...]:
        steps = list(range(self.evaluation_steps, self.max_optimizer_steps + 1, self.evaluation_steps))
        if not steps or steps[-1] != self.max_optimizer_steps:
            steps.append(self.max_optimizer_steps)
        return tuple(steps)


Segmenter = Callable[[str], str]
LogitPredictor = Callable[[Any, Sequence[PhoBertPreprocessingRecord], Any], Sequence[Sequence[float]]]
ModelStateIdentityProver = Callable[[Path], str]


@dataclass(frozen=True, slots=True)
class PhoBertTrainingDependencies:
    """Injected runtime seams; defaults lazily resolve the approved local stack."""

    segmenter: Segmenter | None = None
    segmenter_version: str | None = None
    tokenizer_factory: Callable[..., Any] | None = None
    model_factory: Callable[..., Any] | None = None
    training_arguments_factory: Callable[..., Any] | None = None
    data_collator_factory: Callable[..., Any] | None = None
    trainer_factory: Callable[..., Any] | None = None
    trainer_callback_base: type[Any] | None = None
    logits_predictor: LogitPredictor | None = None
    model_state_identity_prover: ModelStateIdentityProver | None = None
    graph_renderer: GraphRenderer | None = None
    graph_renderer_name: str | None = None
    graph_renderer_version: str | None = None
    package_versions: Mapping[str, str] | None = None
    accelerator: AcceleratorIdentity | None = None
    hardware: RuntimeHardwareEvidence | None = None
    torch_module: Any | None = None
    telemetry_clock: Callable[[], float] = time.perf_counter
    telemetry_utc_clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc)
    cuda_timing_adapter: CudaTimingAdapter | None = None


@dataclass(frozen=True, slots=True)
class PhoBertTrainingResult:
    run_root: Path
    evidence_path: Path
    evidence: RunEvidence
    controlled_config: ResumeControlledConfig
    preprocessing_records: tuple[PhoBertPreprocessingRecord, ...]
    checkpoint_metrics: tuple[Phase40MetricResult, ...]
    selection: CheckpointSelection


class _PhoBertDataset:
    def __init__(self, rows: Sequence[PhoBertPreprocessingRecord]) -> None:
        self._rows = tuple(rows)

    def __len__(self) -> int:
        return len(self._rows)

    def __getitem__(self, index: int) -> dict[str, object]:
        return self._rows[index].model_inputs()


def _token_ids(payload: Any) -> tuple[int, ...]:
    if isinstance(payload, Mapping):
        payload = payload.get("input_ids")
    if hasattr(payload, "tolist"):
        payload = payload.tolist()
    if isinstance(payload, tuple):
        payload = list(payload)
    if isinstance(payload, list) and payload and isinstance(payload[0], list):
        if len(payload) != 1:
            raise ValueError("PhoBERT tokenizer returned an unexpected batch")
        payload = payload[0]
    if not isinstance(payload, list) or not payload:
        raise ValueError("PhoBERT tokenizer returned empty input_ids")
    if any(not isinstance(value, int) or isinstance(value, bool) for value in payload):
        raise ValueError("PhoBERT tokenizer returned non-integer input_ids")
    return tuple(payload)


def _attention_mask(payload: Any, expected_length: int) -> tuple[int, ...]:
    raw = payload.get("attention_mask") if isinstance(payload, Mapping) else None
    if raw is None:
        return (1,) * expected_length
    if hasattr(raw, "tolist"):
        raw = raw.tolist()
    if isinstance(raw, tuple):
        raw = list(raw)
    if isinstance(raw, list) and raw and isinstance(raw[0], list):
        if len(raw) != 1:
            raise ValueError("PhoBERT tokenizer returned an unexpected attention batch")
        raw = raw[0]
    if not isinstance(raw, list) or len(raw) != expected_length or any(value not in (0, 1) for value in raw):
        raise ValueError("PhoBERT tokenizer returned an invalid attention_mask")
    return tuple(raw)


def _default_segmenter(raw_text: str) -> str:
    module = importlib.import_module("underthesea")
    result = module.word_tokenize(raw_text, format="text")
    if not isinstance(result, str):
        raise RuntimeError("underthesea.word_tokenize(format=text) returned a non-string")
    return result


def segment_for_phobert(
    raw_text: str,
    *,
    tokenizer: Any,
    segmenter: Segmenter | None = None,
    segmenter_version: str = PHOBERT_SEGMENTER_VERSION,
    max_length: int = PHOBERT_MAX_LENGTH,
) -> PhoBertSegmentation:
    """Segment one message and retain exact full/truncated token evidence."""

    if not isinstance(raw_text, str) or not raw_text:
        raise ValueError("PhoBERT raw_text must be a non-empty string")
    raw_text.encode("utf-8", errors="strict")
    if segmenter_version != PHOBERT_SEGMENTER_VERSION:
        raise ValueError("PhoBERT segmenter version differs from the frozen 9.5.0 pin")
    if max_length != PHOBERT_MAX_LENGTH:
        raise ValueError("PhoBERT max_length must remain 256")
    segmented = (segmenter or _default_segmenter)(raw_text)
    if not isinstance(segmented, str) or not segmented.strip():
        raise ValueError("PhoBERT segmentation produced empty output")
    segmented.encode("utf-8", errors="strict")
    full_payload = tokenizer(
        segmented,
        add_special_tokens=True,
        truncation=False,
        padding=False,
    )
    full_ids = _token_ids(full_payload)
    retained_payload = tokenizer(
        segmented,
        add_special_tokens=True,
        truncation=True,
        max_length=max_length,
        padding=False,
    )
    retained_ids = _token_ids(retained_payload)
    if len(retained_ids) > len(full_ids) or retained_ids != full_ids[: len(retained_ids)]:
        raise ValueError("PhoBERT tokenizer did not apply deterministic right truncation")
    attention = _attention_mask(retained_payload, len(retained_ids))
    return PhoBertSegmentation(
        raw_text=raw_text,
        segmented_text=segmented,
        token_count=len(full_ids),
        retained_token_count=len(retained_ids),
        truncated=len(retained_ids) < len(full_ids),
        max_length=max_length,
        segmenter_version=segmenter_version,
        preprocessor_version=PHOBERT_PREPROCESSOR_VERSION,
        preprocessor_sha256=PHOBERT_PREPROCESSOR_SHA256,
        input_ids=retained_ids,
        attention_mask=attention,
    )


def preprocess_phobert_snapshot(
    snapshot: CanonicalSplitSnapshot,
    *,
    tokenizer: Any,
    segmenter: Segmenter | None,
    segmenter_version: str,
) -> tuple[PhoBertPreprocessingRecord, ...]:
    if snapshot.split_name not in ("train", "val") or not snapshot.rows:
        raise ValueError("PhoBERT preprocessing requires a non-empty canonical train/val snapshot")
    records = tuple(
        PhoBertPreprocessingRecord(
            split_name=snapshot.split_name,
            canonical_index=row.canonical_index,
            snapshot_row_id=row.snapshot_row_id,
            source_row_sha256=row.source_row_sha256,
            gold_label=row.record.label,
            label_id=PHOBERT_LABEL_TO_ID[row.record.label],
            segmentation=segment_for_phobert(
                row.raw_message,
                tokenizer=tokenizer,
                segmenter=segmenter,
                segmenter_version=segmenter_version,
            ),
        )
        for row in snapshot.rows
    )
    expected_ids = snapshot.row_ids
    if tuple(record.snapshot_row_id for record in records) != expected_ids:
        raise RuntimeError("PhoBERT preprocessing changed canonical snapshot row identities")
    return records


def build_phobert_prediction_rows(
    *,
    validation_snapshot: CanonicalSplitSnapshot,
    preprocessing_records: Sequence[PhoBertPreprocessingRecord],
    logits: Sequence[Sequence[float]],
    artifact_identity: str,
    checkpoint_step: int,
) -> tuple[PhoBertRawPredictionRow, ...]:
    """Bind four logits to IDs copied only from the immutable validation snapshot."""

    if validation_snapshot.split_name != "val" or not validation_snapshot.rows:
        raise ValueError("PhoBERT prediction requires a non-empty validation snapshot")
    records = tuple(preprocessing_records)
    raw_logits = tuple(logits)
    expected_ids = validation_snapshot.validation_row_ids
    actual_ids = tuple(record.snapshot_row_id for record in records)
    if actual_ids != expected_ids:
        raise ValueError("PhoBERT preprocessing IDs do not exactly match the validation snapshot")
    if len(raw_logits) != len(expected_ids):
        raise ValueError("PhoBERT logits count does not match the validation snapshot")
    predictions: list[PhoBertRawPredictionRow] = []
    for expected_index, (snapshot_row, record, row_logits) in enumerate(
        zip(validation_snapshot.rows, records, raw_logits, strict=True)
    ):
        if (
            record.split_name != "val"
            or record.canonical_index != expected_index
            or snapshot_row.canonical_index != expected_index
            or record.source_row_sha256 != snapshot_row.source_row_sha256
            or record.gold_label != snapshot_row.record.label
            or record.segmentation.raw_text != snapshot_row.raw_message
        ):
            raise ValueError("PhoBERT preprocessing row differs from its immutable validation row")
        values = tuple(row_logits)
        if len(values) != len(LABEL_ORDER) or any(
            isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)
            for value in values
        ):
            raise ValueError("PhoBERT classifier must emit exactly four finite logits per row")
        normalized = tuple(float(value) for value in values)
        argmax = LABEL_ORDER[max(range(len(normalized)), key=lambda index: normalized[index])]
        predictions.append(
            PhoBertRawPredictionRow(
                validation_row_id=snapshot_row.validation_row_id or "",
                canonical_index=expected_index,
                source_row_sha256=snapshot_row.source_row_sha256,
                raw_message=snapshot_row.raw_message,
                gold_label=snapshot_row.record.label,
                logits=normalized,  # type: ignore[arg-type]
                argmax_state=argmax,
                artifact_identity=artifact_identity,
                checkpoint_step=checkpoint_step,
            )
        )
    return tuple(predictions)


def _ordered_row_ids_sha256(snapshot: CanonicalSplitSnapshot) -> str:
    digest = hashlib.sha256(b"phase40-ordered-row-ids-v1\0")
    for row_id in snapshot.row_ids:
        digest.update(row_id.encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def _split_evidence(contract: Phase40DataContract) -> tuple[CanonicalSplitEvidence, CanonicalSplitEvidence]:
    return tuple(
        CanonicalSplitEvidence(
            logical_name=logical_name,
            relative_path=snapshot.identity.relative_path.replace("\\", "/"),
            records=snapshot.identity.records,
            bytes=snapshot.identity.bytes,
            sha256=snapshot.whole_file_sha256,
            ordered_row_ids_sha256=_ordered_row_ids_sha256(snapshot),
        )
        for logical_name, snapshot in (
            ("train", contract.train_snapshot),
            ("val", contract.validation_snapshot),
        )
    )  # type: ignore[return-value]


def build_phobert_controlled_config(
    config: PhoBertTrainingConfig,
    contract: Phase40DataContract,
    *,
    accelerator: AcceleratorIdentity,
) -> ResumeControlledConfig:
    additional = (
        NamedControl(name="dynamic_padding", value=True),
        NamedControl(name="input_archive_sha256", value=config.transfer_authority.input_archive_sha256),
        NamedControl(name="input_manifest_sha256", value=config.transfer_authority.input_manifest_sha256),
        NamedControl(name="local_files_only", value=config.local_files_only),
        NamedControl(name="report_to", value="none"),
        NamedControl(name="segmenter_package", value=PHOBERT_SEGMENTER_PACKAGE),
        NamedControl(name="segmenter_version", value=PHOBERT_SEGMENTER_VERSION),
        NamedControl(name="source_archive_sha256", value=config.transfer_authority.source_archive_sha256),
        NamedControl(name="source_inventory_sha256", value=config.transfer_authority.source_inventory_sha256),
        NamedControl(name="trust_remote_code", value=False),
    )
    return ResumeControlledConfig(
        schema_version="phase40-resume-controlled-config-v1",
        experiment_identity=config.identity,
        model_id=config.model_id,
        model_revision=config.model_revision,
        splits=_split_evidence(contract),
        formatter_or_preprocessor_sha256=PHOBERT_PREPROCESSOR_SHA256,
        response_mask_or_preprocessor_version=PHOBERT_PREPROCESSOR_VERSION,
        label_order=tuple(LABEL_ORDER),
        seed=config.seed,
        data_seed=config.data_seed,
        max_sequence_length=config.max_length,
        truncation_policy="right-token-truncate-record-v1",
        per_device_train_batch_size=config.per_device_train_batch_size,
        gradient_accumulation_steps=config.gradient_accumulation_steps,
        world_size=1,
        effective_batch_size=config.per_device_train_batch_size * config.gradient_accumulation_steps,
        num_train_epochs=config.num_train_epochs,
        max_optimizer_steps=config.max_optimizer_steps,
        gradient_checkpointing=config.gradient_checkpointing,
        lora_rank=None,
        lora_alpha=None,
        lora_dropout=None,
        lora_bias=None,
        target_modules=(),
        task_type="sequence-classification",
        optimizer=OptimizerControls(
            optimizer=config.optimizer_name,
            learning_rate=config.learning_rate,
            weight_decay=config.weight_decay,
            lr_scheduler_type=config.lr_scheduler_type,
            warmup_steps=config.warmup_steps,
            warmup_ratio=config.warmup_ratio,
            max_grad_norm=config.max_grad_norm,
        ),
        precision=PrecisionControls(
            compute_dtype="bfloat16" if config.bf16 else "float16" if config.fp16 else "float32",
            adapter_dtype="not-applicable",
            bf16=config.bf16,
            fp16=config.fp16,
            tf32=config.tf32,
        ),
        cadence=CadenceControls(
            logging_steps=config.logging_steps,
            evaluation_steps=config.evaluation_steps,
            save_steps=config.evaluation_steps,
            save_total_limit=config.save_total_limit,
            generation_steps=config.evaluation_schedule,
        ),
        decoder=None,
        checkpoint_selection_policy=PHOBERT_SELECTION_POLICY,
        checkpoint_selection_policy_version="phase40-checkpoint-selection-v1",
        snapshot_id_algorithm_version=PHOBERT_SNAPSHOT_ID_VERSION,
        quantization_proof=None,
        accelerator=accelerator,
        additional_controls=additional,
    )


def _assert_plain_full_classifier(model: Any) -> None:
    config = getattr(model, "config", None)
    if config is None or int(getattr(config, "num_labels", -1)) != len(LABEL_ORDER):
        raise RuntimeError("PhoBERT model must expose exactly four logits")
    raw_id2label = getattr(config, "id2label", None)
    raw_label2id = getattr(config, "label2id", None)
    normalized_id2label = (
        {int(key): value for key, value in raw_id2label.items()}
        if isinstance(raw_id2label, Mapping)
        else None
    )
    if normalized_id2label != PHOBERT_ID_TO_LABEL or raw_label2id != PHOBERT_LABEL_TO_ID:
        raise RuntimeError("PhoBERT model label mapping drifted from the locked order")
    parameters = tuple(model.named_parameters())
    if not parameters:
        raise RuntimeError("PhoBERT model exposes no parameters")
    trainable = tuple(name for name, parameter in parameters if getattr(parameter, "requires_grad", False))
    frozen = tuple(name for name, parameter in parameters if not getattr(parameter, "requires_grad", False))
    if frozen:
        raise RuntimeError(f"PhoBERT requires full encoder/head training; frozen parameters: {frozen[:5]}")
    if any("lora_" in name.casefold() for name in trainable):
        raise RuntimeError("PhoBERT cannot contain LoRA parameters")
    head_markers = ("classifier", "classification_head", "score", "out_proj")
    head = tuple(name for name in trainable if any(marker in name.casefold() for marker in head_markers))
    encoder = tuple(name for name in trainable if name not in head)
    if not head or not encoder:
        raise RuntimeError("PhoBERT trainability proof requires both encoder and classification head")
    if getattr(model, "peft_config", None):
        raise RuntimeError("PhoBERT cannot be a PEFT model")
    if bool(getattr(model, "is_loaded_in_4bit", False)) or getattr(model, "quantization_method", None):
        raise RuntimeError("PhoBERT cannot use a quantized model path")
    modules = tuple(model.modules()) if callable(getattr(model, "modules", None)) else ()
    if any(type(module).__module__.startswith("bitsandbytes.") for module in modules):
        raise RuntimeError("PhoBERT cannot contain bitsandbytes modules")


def _model_state_identity(artifact_path: Path) -> str:
    path = _reject_symlink_ancestors(
        Path(artifact_path), description="PhoBERT checkpoint model state"
    )
    if not path.is_dir() or path.is_symlink():
        raise RuntimeError("PhoBERT checkpoint must be a non-symlink directory")
    entries = tuple(path.rglob("*"))
    if any(entry.is_symlink() for entry in entries):
        raise RuntimeError("PhoBERT checkpoint model state contains a symlink")
    weight_files = tuple(
        sorted(
            (
                child
                for child in entries
                if child.is_file()
                and (
                    child.name in _WEIGHT_NAMES
                    or child.name.startswith("model-") and child.suffix == ".safetensors"
                    or child.name.startswith("pytorch_model-") and child.suffix == ".bin"
                )
            ),
            key=lambda child: child.relative_to(path).as_posix(),
        )
    )
    if not weight_files:
        raise RuntimeError("PhoBERT checkpoint contains no recognized model weight file")
    digest = hashlib.sha256(b"phase40-phobert-model-state-v1\0")
    for weight_path in weight_files:
        digest.update(weight_path.relative_to(path).as_posix().encode("utf-8"))
        digest.update(b"\0")
        with weight_path.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
        digest.update(b"\0")
    return f"model-state-sha256:{digest.hexdigest()}"


def _copy_directory_immutable(source: Path, target: Path) -> Path:
    source = _reject_symlink_ancestors(
        Path(source), description="PhoBERT immutable artifact source"
    )
    target = _reject_symlink_ancestors(
        Path(target), description="PhoBERT immutable artifact target"
    )
    if not source.is_dir() or source.is_symlink() or any(path.is_symlink() for path in source.rglob("*")):
        raise ValueError("PhoBERT model artifact source must be a non-symlink directory")
    source_sha = build_model_checksum(source)
    if target.exists():
        _reject_tree_symlinks(target, description="PhoBERT immutable artifact target")
        if target.is_dir() and not target.is_symlink() and build_model_checksum(target) == source_sha:
            return target
        raise FileExistsError(f"immutable PhoBERT artifact target differs: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{target.name}.", dir=target.parent))
    temporary.rmdir()
    try:
        shutil.copytree(source, temporary, copy_function=shutil.copy2)
        _reject_tree_symlinks(temporary, description="PhoBERT immutable artifact copy")
        if build_model_checksum(temporary) != source_sha:
            raise RuntimeError("PhoBERT artifact copy changed content identity")
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
    return target


def _atomic_write(path: Path, payload: bytes) -> Path:
    if not payload:
        raise ValueError("immutable PhoBERT artifact cannot be empty")
    path = _reject_symlink_ancestors(Path(path), description="PhoBERT atomic output")
    if path.exists():
        if path.is_file() and path.read_bytes() == payload:
            return path
        raise FileExistsError(f"immutable PhoBERT artifact differs: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile("wb", dir=path.parent, prefix=f".{path.name}.", delete=False)
    temporary = Path(handle.name)
    try:
        with handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        if temporary.read_bytes() != payload:
            raise RuntimeError("PhoBERT artifact temp read-back mismatch")
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()
    return path


def _atomic_replace(path: Path, payload: bytes) -> Path:
    """Atomically replace the mutable checkpoint seal, never a symlink."""

    if not payload:
        raise ValueError("PhoBERT checkpoint seal cannot be empty")
    path = _reject_symlink_ancestors(Path(path), description="PhoBERT checkpoint seal")
    if path.exists() and (not path.is_file() or path.is_symlink()):
        raise FileExistsError("PhoBERT checkpoint seal target is not a safe regular file")
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile("wb", dir=path.parent, prefix=f".{path.name}.", delete=False)
    temporary = Path(handle.name)
    try:
        with handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        if temporary.read_bytes() != payload:
            raise RuntimeError("PhoBERT checkpoint seal temp read-back mismatch")
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()
    if path.read_bytes() != payload:
        raise RuntimeError("PhoBERT checkpoint seal read-back mismatch")
    return path


def _base_model_path_sha256(path: Path) -> str:
    absolute = _reject_symlink_ancestors(path, description="PhoBERT local base-model path")
    normalized = os.path.normcase(os.fspath(absolute)).replace("\\", "/")
    return hashlib.sha256(
        b"phase40-phobert-local-base-path-v1\0" + normalized.encode("utf-8", errors="strict")
    ).hexdigest()


def _base_model_content_facts(path: Path) -> tuple[str, int, int]:
    root = _reject_symlink_ancestors(path, description="PhoBERT local base-model path")
    if not root.is_dir() or root.is_symlink():
        raise FileNotFoundError("PhoBERT local base-model path is not a safe directory")
    entries = tuple(root.rglob("*"))
    if any(entry.is_symlink() for entry in entries):
        raise ValueError("PhoBERT local base-model snapshot contains a symlink")
    files = tuple(
        sorted(
            (
                entry
                for entry in entries
                if entry.is_file()
            ),
            key=lambda entry: entry.relative_to(root).as_posix(),
        )
    )
    if not files:
        raise RuntimeError("PhoBERT local base-model snapshot is empty")
    relative_names = {entry.relative_to(root).as_posix() for entry in files}
    if "config.json" not in relative_names:
        raise RuntimeError("PhoBERT local base-model snapshot lacks config.json")
    try:
        model_config = json.loads((root / "config.json").read_text(encoding="utf-8", errors="strict"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("PhoBERT local base-model config.json is invalid") from exc
    if not isinstance(model_config, dict):
        raise RuntimeError("PhoBERT local base-model config.json must contain an object")
    has_weights = any(
        entry.stat().st_size > 0
        and (
            entry.name in _WEIGHT_NAMES
            or entry.name.startswith("model-") and entry.suffix == ".safetensors"
            or entry.name.startswith("pytorch_model-") and entry.suffix == ".bin"
        )
        for entry in files
    )
    if not has_weights:
        raise RuntimeError("PhoBERT local base-model snapshot lacks recognized model weights")
    tokenizer_names = {"tokenizer.json", "vocab.txt", "sentencepiece.bpe.model"}
    if not any(entry.name in tokenizer_names and entry.stat().st_size > 0 for entry in files):
        raise RuntimeError("PhoBERT local base-model snapshot lacks tokenizer assets")
    digest = hashlib.sha256(b"phase40-phobert-local-base-content-v1\0")
    total_bytes = 0
    for entry in files:
        relative = entry.relative_to(root).as_posix()
        size = entry.stat().st_size
        total_bytes += size
        digest.update(relative.encode("utf-8", errors="strict"))
        digest.update(b"\0")
        digest.update(str(size).encode("ascii"))
        digest.update(b"\0")
        with entry.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
        digest.update(b"\0")
    return digest.hexdigest(), len(files), total_bytes


def build_phobert_base_model_acquisition_request(
    local_snapshot_path: Path,
    *,
    model_id: str = PHOBERT_MODEL_ID,
    model_revision: str = PHOBERT_MODEL_REVISION,
) -> PhoBertBaseModelAcquisitionRequest:
    """Describe, but never perform, acquisition of the pinned PhoBERT snapshot."""

    destination = Path(local_snapshot_path)
    if not destination.is_absolute():
        raise ValueError("PhoBERT acquisition destination must be absolute")
    return PhoBertBaseModelAcquisitionRequest(
        model_id=model_id,
        model_revision=model_revision,
        local_snapshot_path=_reject_symlink_ancestors(
            destination, description="PhoBERT acquisition destination"
        ),
    )


def _resolved_phobert_manifest_path(snapshot_path: Path, manifest_path: Path | None) -> Path:
    root = _reject_symlink_ancestors(snapshot_path, description="PhoBERT local base-model path")
    output = _reject_symlink_ancestors(
        root.with_name(f"{root.name}.provenance.json") if manifest_path is None else manifest_path,
        description="PhoBERT base-model provenance path",
    )
    if output == root or root in output.parents:
        raise ValueError("PhoBERT provenance manifest must be external to the snapshot")
    return output


def _build_phobert_snapshot(
    snapshot_path: Path,
    *,
    manifest_path: Path | None = None,
) -> tuple[PhoBertBaseModelSnapshot, bytes]:
    request = build_phobert_base_model_acquisition_request(snapshot_path)
    output = _resolved_phobert_manifest_path(request.local_snapshot_path, manifest_path)
    content_sha256, file_count, total_bytes = _base_model_content_facts(
        request.local_snapshot_path
    )
    provenance = PhoBertBaseModelProvenance(
        schema_version=PHOBERT_BASE_PROVENANCE_SCHEMA,
        model_id=request.model_id,
        model_revision=request.model_revision,
        local_path_sha256=_base_model_path_sha256(request.local_snapshot_path),
        content_sha256=content_sha256,
        file_count=file_count,
        total_bytes=total_bytes,
    )
    payload = _json_line(provenance.model_dump(mode="json"))
    return (
        PhoBertBaseModelSnapshot(
            model_id=request.model_id,
            model_revision=request.model_revision,
            local_snapshot_path=request.local_snapshot_path,
            manifest_path=output,
            snapshot_content_sha256=content_sha256,
            manifest_sha256=hashlib.sha256(payload).hexdigest(),
            local_path_sha256=provenance.local_path_sha256,
            file_count=file_count,
            total_bytes=total_bytes,
        ),
        payload,
    )


def seal_phobert_base_model_snapshot(
    snapshot_path: Path,
    *,
    model_id: str = PHOBERT_MODEL_ID,
    model_revision: str = PHOBERT_MODEL_REVISION,
    manifest_path: Path | None = None,
) -> PhoBertBaseModelSnapshot:
    """Seal a pre-acquired snapshot without importing a client or using a network."""

    build_phobert_base_model_acquisition_request(
        snapshot_path,
        model_id=model_id,
        model_revision=model_revision,
    )
    snapshot, payload = _build_phobert_snapshot(snapshot_path, manifest_path=manifest_path)
    _atomic_write(snapshot.manifest_path, payload)
    return snapshot


def validate_phobert_base_model_snapshot(
    snapshot_path: Path,
    *,
    expected_model_id: str = PHOBERT_MODEL_ID,
    expected_model_revision: str = PHOBERT_MODEL_REVISION,
    manifest_path: Path | None = None,
) -> PhoBertBaseModelSnapshot:
    """Fail closed if local model bytes, path, or canonical manifest drifted."""

    build_phobert_base_model_acquisition_request(
        snapshot_path,
        model_id=expected_model_id,
        model_revision=expected_model_revision,
    )
    expected, canonical_payload = _build_phobert_snapshot(
        snapshot_path, manifest_path=manifest_path
    )
    if not expected.manifest_path.is_file() or expected.manifest_path.is_symlink():
        raise RuntimeError("PhoBERT base-model provenance manifest is missing or unsafe")
    actual_payload = expected.manifest_path.read_bytes()
    if actual_payload != canonical_payload:
        raise RuntimeError("PhoBERT base-model provenance does not match the local snapshot")
    if hashlib.sha256(actual_payload).hexdigest() != expected.manifest_sha256:
        raise RuntimeError("PhoBERT base-model provenance manifest hash drifted")
    return expected


def seal_phobert_base_model_provenance(
    local_base_model_path: Path,
    provenance_path: Path,
) -> Path:
    """Compatibility wrapper for callers that explicitly place the manifest."""

    return seal_phobert_base_model_snapshot(
        local_base_model_path,
        manifest_path=provenance_path,
    ).manifest_path


def verify_phobert_base_model_provenance(
    local_base_model_path: Path,
    provenance_path: Path,
) -> PhoBertBaseModelSnapshot:
    """Compatibility wrapper for exact snapshot plus explicit-manifest validation."""

    return validate_phobert_base_model_snapshot(
        local_base_model_path,
        manifest_path=provenance_path,
    )


def _json_line(value: object) -> bytes:
    return _canonical_json_bytes(value) + b"\n"


def _jsonl(values: Sequence[Mapping[str, object]]) -> bytes:
    return b"".join(_json_line(value) for value in values)


def _metric_summary(metrics: Phase40MetricResult) -> dict[str, object]:
    return {
        "evaluated_rows": metrics.evaluated_rows,
        "per_class": [asdict(row) for row in metrics.per_class],
        "macro_f1": metrics.macro_f1,
        "weighted_f1": metrics.weighted_f1,
        "accuracy": metrics.accuracy,
        "invalid_output_count": metrics.invalid_output_count,
        "invalid_output_rate": metrics.invalid_output_rate,
        "risky_to_benign_count": metrics.risky_to_benign_count,
        "risky_to_invalid_count": metrics.risky_to_invalid_count,
        "confusion_matrix": [list(row) for row in metrics.confusion_matrix],
        "risky_to_benign_row_ids": list(metrics.risky_to_benign_row_ids),
        "risky_to_invalid_row_ids": list(metrics.risky_to_invalid_row_ids),
    }


def _run_metric_summary(metrics: Phase40MetricResult) -> dict[str, float]:
    result = {
        "macro_f1": metrics.macro_f1,
        "weighted_f1": metrics.weighted_f1,
        "accuracy": metrics.accuracy,
        "invalid_output_rate": metrics.invalid_output_rate,
        "risky_to_benign_count": float(metrics.risky_to_benign_count),
    }
    result.update({f"recall.{row.label}": row.recall for row in metrics.per_class})
    return result


def _default_logits_predictor(
    model: Any,
    records: Sequence[PhoBertPreprocessingRecord],
    collator: Any,
    *,
    torch_module: Any,
) -> tuple[tuple[float, ...], ...]:
    was_training = bool(getattr(model, "training", False))
    if callable(getattr(model, "eval", None)):
        model.eval()
    outputs: list[tuple[float, ...]] = []
    context = torch_module.no_grad() if hasattr(torch_module, "no_grad") else _NullContext()
    try:
        with context:
            for record in records:
                batch = collator([record.model_inputs()])
                device = getattr(model, "device", None)
                if device is not None:
                    batch = {
                        key: value.to(device) if hasattr(value, "to") else value
                        for key, value in batch.items()
                    }
                batch.pop("labels", None)
                result = model(**batch)
                logits = getattr(result, "logits", None)
                if logits is None:
                    raise RuntimeError("PhoBERT model output is missing logits")
                if hasattr(logits, "detach"):
                    logits = logits.detach()
                if hasattr(logits, "cpu"):
                    logits = logits.cpu()
                if hasattr(logits, "tolist"):
                    logits = logits.tolist()
                if isinstance(logits, list) and len(logits) == 1 and isinstance(logits[0], list):
                    logits = logits[0]
                outputs.append(tuple(logits))
    finally:
        if callable(getattr(model, "train", None)):
            model.train(was_training)
    return tuple(outputs)


class _NullContext:
    def __enter__(self) -> None:
        return None

    def __exit__(self, *_: object) -> None:
        return None


@dataclass(frozen=True, slots=True)
class _Candidate:
    step: int
    artifact_identity: str
    retained_model_path: Path
    prediction_path: Path
    metrics_path: Path
    raw_rows: tuple[PhoBertRawPredictionRow, ...]
    metrics: Phase40MetricResult


def _portable_relative(path: Path, root: Path, *, description: str) -> str:
    absolute_root = _reject_symlink_ancestors(root, description=f"{description} root")
    absolute_path = _reject_symlink_ancestors(path, description=description)
    try:
        relative = absolute_path.relative_to(absolute_root).as_posix()
    except ValueError as exc:
        raise ValueError(f"{description} is outside its authorized root") from exc
    pure = PurePosixPath(relative)
    if not relative or pure.is_absolute() or any(part in ("", ".", "..") for part in pure.parts):
        raise ValueError(f"{description} is not a normalized relative path")
    return relative


def _path_from_relative(root: Path, value: str, *, description: str) -> Path:
    if not isinstance(value, str) or "\\" in value:
        raise ValueError(f"{description} must be a POSIX relative path")
    pure = PurePosixPath(value)
    if not value or pure.is_absolute() or any(part in ("", ".", "..") for part in pure.parts):
        raise ValueError(f"{description} must be a normalized relative path")
    root = _reject_symlink_ancestors(root, description=f"{description} root")
    path = _reject_symlink_ancestors(
        root / Path(*pure.parts), description=description
    )
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"{description} escapes its authorized root") from exc
    current = root
    for part in pure.parts:
        current = current / part
        if current.exists() and current.is_symlink():
            raise ValueError(f"{description} traverses a symlink")
    return path


def _checkpoint_payload_sha256(checkpoint_path: Path) -> str:
    checkpoint = _reject_symlink_ancestors(
        Path(checkpoint_path), description="PhoBERT resume checkpoint"
    )
    if not checkpoint.is_dir() or checkpoint.is_symlink():
        raise ValueError("PhoBERT resume checkpoint must be a non-symlink directory")
    entries = tuple(checkpoint.rglob("*"))
    if any(child.is_symlink() for child in entries):
        raise ValueError("PhoBERT resume checkpoint contains a symlink")
    files = tuple(
        sorted(
            (
                child
                for child in entries
                if child.is_file()
                and child != checkpoint / PHOBERT_RESUME_MANIFEST_NAME
            ),
            key=lambda child: child.relative_to(checkpoint).as_posix(),
        )
    )
    if not files:
        raise ValueError("PhoBERT resume checkpoint payload is empty")
    digest = hashlib.sha256(b"phase40-phobert-checkpoint-payload-v1\0")
    for child in files:
        digest.update(child.relative_to(checkpoint).as_posix().encode("utf-8"))
        digest.update(b"\0")
        with child.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
        digest.update(b"\0")
    return digest.hexdigest()


def _checkpoint_step(checkpoint_path: Path, work_root: Path) -> int:
    expected_parent = _reject_symlink_ancestors(
        work_root / "trainer", description="PhoBERT trainer work root"
    )
    checkpoint = _reject_symlink_ancestors(
        checkpoint_path, description="PhoBERT resume checkpoint"
    )
    if checkpoint.parent != expected_parent:
        raise ValueError("PhoBERT resume path must be an exact work-root trainer checkpoint-N")
    match = re.fullmatch(r"checkpoint-([1-9][0-9]*)", checkpoint.name)
    if match is None:
        raise ValueError("PhoBERT resume path must name one exact checkpoint-N")
    return int(match.group(1))


def _telemetry_sha256(telemetry: PhoBertResumeTelemetry) -> str:
    return hashlib.sha256(
        b"phase40-phobert-resume-telemetry-v1\0"
        + _canonical_json_bytes(telemetry.model_dump(mode="json"))
    ).hexdigest()


def _load_event_payload(payload: bytes, *, expected_run_id: str) -> tuple[RunEvent, ...]:
    if not payload or not payload.endswith(b"\n"):
        raise RuntimeError("PhoBERT sealed event history is empty or partial")
    try:
        lines = payload.decode("utf-8", errors="strict").splitlines()
    except UnicodeDecodeError as exc:
        raise RuntimeError("PhoBERT sealed event history is not strict UTF-8") from exc
    events: list[RunEvent] = []
    for index, line in enumerate(lines):
        if not line:
            raise RuntimeError("PhoBERT sealed event history contains an empty record")
        try:
            event = RunEvent.model_validate_json(line)
        except Exception as exc:
            raise RuntimeError(f"invalid PhoBERT sealed event at position {index}") from exc
        if event.sequence_id != index:
            raise RuntimeError("PhoBERT sealed event sequence is not contiguous")
        if event.source_run_id != expected_run_id or event.run_kind != RunKind.FULL:
            raise RuntimeError("PhoBERT sealed event identity drift")
        if events:
            previous = events[-1]
            if previous.event_kind == RunEventKind.RUN_END:
                raise RuntimeError("PhoBERT sealed event history appends after run_end")
            if previous.event_kind == RunEventKind.FAILURE:
                if event.event_kind not in {RunEventKind.RUN_START, RunEventKind.RUN_END}:
                    raise RuntimeError("PhoBERT failed attempt has a nonterminal suffix")
            elif event.event_kind == RunEventKind.RUN_START:
                raise RuntimeError("PhoBERT resume attempt lacks a preceding failure")
            elif event.optimizer_step < previous.optimizer_step:
                raise RuntimeError("PhoBERT sealed event optimizer steps moved backward")
        events.append(event)
    return tuple(events)


def _finite_event_number(
    value: object,
    *,
    description: str,
    positive: bool = False,
) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RuntimeError(f"PhoBERT {description} is not numeric")
    result = float(value)
    if not math.isfinite(result) or result < 0 or (positive and result <= 0):
        raise RuntimeError(f"PhoBERT {description} is not valid seconds")
    return result


def _event_non_negative_int(value: object, *, description: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise RuntimeError(f"PhoBERT {description} is not a non-negative integer")
    return value


def _derive_resume_telemetry(events: Sequence[RunEvent]) -> PhoBertResumeTelemetry:
    """Rebuild cumulative facts solely from the append-only, sealed event stream."""

    observed_steps: set[tuple[int, int]] = set()
    retained_durations: list[float] = []
    retained_examples = 0
    retained_tokens = 0
    peak_allocated = 0
    peak_reserved = 0
    evaluation_overhead = 0.0
    checkpoint_overhead = 0.0
    attempt_walls: list[float] = []
    current_attempt_wall: float | None = None
    started = False
    attempt_index = -1

    for event in events:
        values = event.trainer_values
        if event.event_kind == RunEventKind.RUN_START:
            if started:
                if current_attempt_wall is None:
                    raise RuntimeError("PhoBERT prior resume attempt lacks sealed wall telemetry")
                attempt_walls.append(current_attempt_wall)
            started = True
            attempt_index += 1
            current_attempt_wall = None
            continue
        if not started:
            raise RuntimeError("PhoBERT telemetry event history does not begin with run_start")
        if values.get("restored_resume_history") is True:
            continue
        if event.event_kind == RunEventKind.STEP_TIMING:
            sample_key = (attempt_index, event.optimizer_step)
            if sample_key in observed_steps:
                raise RuntimeError("PhoBERT telemetry repeats an optimizer-step sample in one attempt")
            observed_steps.add(sample_key)
            duration = _finite_event_number(
                values.get("duration_seconds"),
                description="optimizer-step duration",
                positive=True,
            )
            is_warmup = values.get("is_warmup")
            if not isinstance(is_warmup, bool):
                raise RuntimeError("PhoBERT optimizer-step warmup flag is invalid")
            allocated = _event_non_negative_int(
                values.get("peak_allocated_bytes"), description="peak allocated bytes"
            )
            reserved = _event_non_negative_int(
                values.get("peak_reserved_bytes"), description="peak reserved bytes"
            )
            if reserved < allocated:
                raise RuntimeError("PhoBERT optimizer-step peak memory facts are inconsistent")
            peak_allocated = max(peak_allocated, allocated)
            peak_reserved = max(peak_reserved, reserved)
            if not is_warmup:
                examples = _event_non_negative_int(
                    values.get("examples"), description="retained examples"
                )
                tokens = _event_non_negative_int(
                    values.get("tokens"), description="retained tokens"
                )
                if examples <= 0 or tokens <= 0:
                    raise RuntimeError("PhoBERT retained optimizer step lacks examples or tokens")
                retained_durations.append(duration)
                retained_examples += examples
                retained_tokens += tokens
        elif event.event_kind == RunEventKind.EVALUATION and "eval_runtime" in values:
            evaluation_overhead += _finite_event_number(
                values["eval_runtime"], description="evaluation overhead"
            )
        elif event.event_kind == RunEventKind.CHECKPOINT and "checkpoint_runtime_seconds" in values:
            checkpoint_overhead += _finite_event_number(
                values["checkpoint_runtime_seconds"], description="checkpoint overhead"
            )
        elif event.event_kind == RunEventKind.RESOURCE:
            if "peak_allocated_bytes" in values:
                peak_allocated = max(
                    peak_allocated,
                    _event_non_negative_int(
                        values["peak_allocated_bytes"], description="resource peak allocated bytes"
                    ),
                )
            if "peak_reserved_bytes" in values:
                peak_reserved = max(
                    peak_reserved,
                    _event_non_negative_int(
                        values["peak_reserved_bytes"], description="resource peak reserved bytes"
                    ),
                )
            if "actual_wall_seconds" in values:
                current_attempt_wall = _finite_event_number(
                    values["actual_wall_seconds"],
                    description="attempt wall time",
                    positive=True,
                )

    if not started or current_attempt_wall is None:
        raise RuntimeError("PhoBERT current attempt lacks sealed wall telemetry")
    attempt_walls.append(current_attempt_wall)
    if not observed_steps:
        raise RuntimeError("PhoBERT resume telemetry lacks optimizer-step history")
    return PhoBertResumeTelemetry(
        schema_version="phase40-phobert-resume-telemetry-v1",
        observed_optimizer_steps=len(observed_steps),
        retained_step_durations_seconds=tuple(retained_durations),
        retained_examples=retained_examples,
        retained_tokens=retained_tokens,
        peak_allocated_bytes=peak_allocated,
        peak_reserved_bytes=peak_reserved,
        evaluation_overhead_seconds=evaluation_overhead,
        checkpoint_overhead_seconds=checkpoint_overhead,
        attempt_count=len(attempt_walls),
        actual_wall_seconds=float(sum(attempt_walls)),
    )


def _resource_summary_from_telemetry(
    telemetry: PhoBertResumeTelemetry,
    *,
    config: PhoBertTrainingConfig,
) -> Phase40ResourceSummary:
    durations = telemetry.retained_step_durations_seconds
    if not durations:
        raise RuntimeError("PhoBERT cumulative telemetry lacks post-warm-up optimizer steps")
    retained_seconds = float(sum(durations))
    steady_median = float(median(durations))
    measured_overhead = (
        telemetry.evaluation_overhead_seconds + telemetry.checkpoint_overhead_seconds
    )
    return Phase40ResourceSummary(
        source_run_id=config.run_id,
        run_kind=RunKind.FULL,
        warmup_optimizer_steps=config.warmup_steps,
        observed_optimizer_steps=telemetry.observed_optimizer_steps,
        retained_optimizer_steps=len(durations),
        steady_state_step_seconds_median=steady_median,
        examples_per_second=telemetry.retained_examples / retained_seconds,
        tokens_per_second=telemetry.retained_tokens / retained_seconds,
        peak_allocated_bytes=telemetry.peak_allocated_bytes,
        peak_reserved_bytes=telemetry.peak_reserved_bytes,
        evaluation_overhead_seconds=telemetry.evaluation_overhead_seconds,
        checkpoint_overhead_seconds=telemetry.checkpoint_overhead_seconds,
        measured_overhead_seconds=measured_overhead,
        actual_wall_seconds=telemetry.actual_wall_seconds,
        planned_full_optimizer_steps=config.max_optimizer_steps,
        projected_local_runtime_seconds=(
            steady_median * config.max_optimizer_steps + measured_overhead
        ),
        projected_local_runtime_is_estimate=True,
    )


def _resume_candidate_record(candidate: _Candidate, *, run_root: Path, work_root: Path) -> PhoBertResumeCandidate:
    return PhoBertResumeCandidate(
        optimizer_step=candidate.step,
        artifact_identity=candidate.artifact_identity,
        retained_model_relative_path=_portable_relative(
            candidate.retained_model_path, work_root, description="retained checkpoint model"
        ),
        predictions_relative_path=_portable_relative(
            candidate.prediction_path, run_root, description="checkpoint predictions"
        ),
        predictions_sha256=build_model_checksum(candidate.prediction_path),
        metrics_relative_path=_portable_relative(
            candidate.metrics_path, run_root, description="checkpoint metrics"
        ),
        metrics_sha256=build_model_checksum(candidate.metrics_path),
    )


def seal_phobert_resume_checkpoint(
    checkpoint_path: Path,
    *,
    config: PhoBertTrainingConfig,
    controlled_config: ResumeControlledConfig,
    candidates: Sequence[_Candidate],
    base_model_snapshot: PhoBertBaseModelSnapshot | None = None,
    identity_prover: ModelStateIdentityProver = _model_state_identity,
) -> Path:
    """Seal one exact Trainer checkpoint with cumulative validation history."""

    checkpoint = _reject_symlink_ancestors(
        checkpoint_path, description="PhoBERT resume checkpoint"
    )
    step = _checkpoint_step(checkpoint, config.work_root)
    if step > config.max_optimizer_steps:
        raise ValueError("PhoBERT resume checkpoint exceeds the controlled maximum step")
    identity = identity_prover(checkpoint)
    snapshot = base_model_snapshot or validate_phobert_base_model_snapshot(
        config.local_base_model_path,
        manifest_path=config.resolved_base_model_provenance_path,
    )
    candidate_records = tuple(
        sorted(
            (
                _resume_candidate_record(candidate, run_root=config.run_bundle_root, work_root=config.work_root)
                for candidate in candidates
            ),
            key=lambda item: (item.optimizer_step, item.artifact_identity),
        )
    )
    event_path = config.run_bundle_root / "events.jsonl"
    event_payload = event_path.read_bytes()
    events = load_run_events(event_path, expected_run_id=config.run_id)
    telemetry = _derive_resume_telemetry(events)
    manifest = PhoBertResumeManifest(
        schema_version="phase40-phobert-resume-v2",
        run_id=config.run_id,
        checkpoint_step=step,
        checkpoint_relative_path=_portable_relative(
            checkpoint, config.work_root, description="resume checkpoint"
        ),
        checkpoint_payload_sha256=_checkpoint_payload_sha256(checkpoint),
        model_state_identity=identity,
        controlled_config_digest=compute_resume_digest(controlled_config),
        model_id=config.model_id,
        model_revision=config.model_revision,
        base_model_content_sha256=snapshot.snapshot_content_sha256,
        base_model_manifest_sha256=snapshot.manifest_sha256,
        base_model_local_path_sha256=snapshot.local_path_sha256,
        preprocessor_sha256=PHOBERT_PREPROCESSOR_SHA256,
        validation_row_ids_sha256=controlled_config.splits[1].ordered_row_ids_sha256,
        sealed_event_bytes=len(event_payload),
        sealed_event_sha256=hashlib.sha256(event_payload).hexdigest(),
        telemetry_sha256=_telemetry_sha256(telemetry),
        telemetry=telemetry,
        candidates=candidate_records,
    )
    manifest_path = _atomic_replace(
        checkpoint / PHOBERT_RESUME_MANIFEST_NAME,
        _json_line(manifest.model_dump(mode="json")),
    )
    read_back = PhoBertResumeManifest.model_validate_json(
        manifest_path.read_text(encoding="utf-8", errors="strict")
    )
    if read_back != manifest:
        raise RuntimeError("PhoBERT resume manifest semantic read-back mismatch")
    return manifest_path


def _raw_prediction_from_json(payload: Mapping[str, object]) -> PhoBertRawPredictionRow:
    required = {
        "validation_row_id",
        "canonical_index",
        "sequence_index",
        "source_row_sha256",
        "raw_message",
        "gold_label",
        "label_order",
        "logits",
        "argmax_state",
        "artifact_identity",
        "checkpoint_step",
    }
    if set(payload) != required or payload.get("label_order") != list(LABEL_ORDER):
        raise ValueError("resumed PhoBERT prediction row schema or label order drifted")
    if payload.get("canonical_index") != payload.get("sequence_index"):
        raise ValueError("resumed PhoBERT prediction sequence index drifted")
    logits = payload.get("logits")
    if not isinstance(logits, list):
        raise ValueError("resumed PhoBERT prediction logits are missing")
    return PhoBertRawPredictionRow(
        validation_row_id=payload["validation_row_id"],  # type: ignore[arg-type]
        canonical_index=payload["canonical_index"],  # type: ignore[arg-type]
        source_row_sha256=payload["source_row_sha256"],  # type: ignore[arg-type]
        raw_message=payload["raw_message"],  # type: ignore[arg-type]
        gold_label=payload["gold_label"],  # type: ignore[arg-type]
        logits=tuple(logits),  # type: ignore[arg-type]
        argmax_state=payload["argmax_state"],  # type: ignore[arg-type]
        artifact_identity=payload["artifact_identity"],  # type: ignore[arg-type]
        checkpoint_step=payload["checkpoint_step"],  # type: ignore[arg-type]
    )


def _load_resumed_candidate(
    record: PhoBertResumeCandidate,
    *,
    config: PhoBertTrainingConfig,
    validation_snapshot: CanonicalSplitSnapshot,
    identity_prover: ModelStateIdentityProver,
) -> _Candidate:
    model_path = _path_from_relative(
        config.work_root, record.retained_model_relative_path, description="retained checkpoint model"
    )
    prediction_path = _path_from_relative(
        config.run_bundle_root, record.predictions_relative_path, description="checkpoint predictions"
    )
    metrics_path = _path_from_relative(
        config.run_bundle_root, record.metrics_relative_path, description="checkpoint metrics"
    )
    if identity_prover(model_path) != record.artifact_identity:
        raise RuntimeError("resumed retained PhoBERT model identity mismatch")
    if build_model_checksum(prediction_path) != record.predictions_sha256:
        raise RuntimeError("resumed PhoBERT prediction artifact hash mismatch")
    if build_model_checksum(metrics_path) != record.metrics_sha256:
        raise RuntimeError("resumed PhoBERT metric artifact hash mismatch")
    text = prediction_path.read_text(encoding="utf-8", errors="strict")
    if not text.endswith("\n") or any(not line for line in text.splitlines()):
        raise RuntimeError("resumed PhoBERT predictions are partial or empty")
    raw_rows = tuple(_raw_prediction_from_json(json.loads(line)) for line in text.splitlines())
    if tuple(row.validation_row_id for row in raw_rows) != validation_snapshot.validation_row_ids:
        raise RuntimeError("resumed PhoBERT predictions changed validation row identities")
    if any(
        row.canonical_index != index
        or row.source_row_sha256 != validation_snapshot.rows[index].source_row_sha256
        or row.raw_message != validation_snapshot.rows[index].raw_message
        or row.gold_label != validation_snapshot.rows[index].record.label
        or row.artifact_identity != record.artifact_identity
        or row.checkpoint_step != record.optimizer_step
        for index, row in enumerate(raw_rows)
    ):
        raise RuntimeError("resumed PhoBERT prediction content differs from the canonical snapshot")
    metrics = evaluate_phase40_predictions(
        expected_validation_row_ids=validation_snapshot.validation_row_ids,
        gold_labels=tuple(row.record.label for row in validation_snapshot.rows),
        prediction_rows=tuple(row.as_metric_row() for row in raw_rows),
    )
    try:
        stored_metrics = json.loads(metrics_path.read_text(encoding="utf-8", errors="strict"))
    except json.JSONDecodeError as exc:
        raise RuntimeError("resumed PhoBERT metrics are invalid JSON") from exc
    if stored_metrics != _metric_summary(metrics):
        raise RuntimeError("resumed PhoBERT metrics differ from recomputed raw predictions")
    return _Candidate(
        record.optimizer_step,
        record.artifact_identity,
        model_path,
        prediction_path,
        metrics_path,
        raw_rows,
        metrics,
    )


def _last_attempt_wall_seconds(events: Sequence[RunEvent]) -> float:
    last_start = max(
        index for index, event in enumerate(events) if event.event_kind == RunEventKind.RUN_START
    )
    wall_values = [
        _finite_event_number(
            event.trainer_values["actual_wall_seconds"],
            description="attempt wall time",
            positive=True,
        )
        for event in events[last_start + 1 :]
        if event.event_kind == RunEventKind.RESOURCE
        and "actual_wall_seconds" in event.trainer_values
    ]
    if not wall_values:
        raise RuntimeError("PhoBERT sealed checkpoint lacks an attempt wall snapshot")
    return wall_values[-1]


def _validate_failed_attempt_suffix(
    *,
    sealed_events: Sequence[RunEvent],
    full_events: Sequence[RunEvent],
    checkpoint_step: int,
    max_optimizer_steps: int,
) -> tuple[RunEvent, ...]:
    """Accept only same-attempt work ending in a measured terminal failure."""

    suffix = tuple(full_events[len(sealed_events) :])
    if not suffix:
        return ()
    if tuple(full_events[: len(sealed_events)]) != tuple(sealed_events):
        raise RuntimeError("PhoBERT resume event prefix changed semantically")
    if len(suffix) < 2:
        raise RuntimeError("PhoBERT resume event suffix is nonterminal")
    terminal_resource, failure = suffix[-2:]
    if terminal_resource.event_kind != RunEventKind.RESOURCE or failure.event_kind != RunEventKind.FAILURE:
        raise RuntimeError("PhoBERT resume event suffix lacks terminal resource/failure events")
    if any(
        event.event_kind
        not in {RunEventKind.STEP_TIMING, RunEventKind.TRAIN_LOG, RunEventKind.EVALUATION}
        for event in suffix[:-2]
    ):
        raise RuntimeError("PhoBERT resume event suffix contains an unsafe lifecycle event")
    if any(event.trainer_values.get("restored_resume_history") is True for event in suffix):
        raise RuntimeError("PhoBERT resume event suffix cannot contain restored lifecycle events")
    for event in suffix:
        if not checkpoint_step <= event.optimizer_step <= max_optimizer_steps:
            raise RuntimeError("PhoBERT resume event suffix optimizer step is out of bounds")
    if any(
        event.event_kind == RunEventKind.STEP_TIMING
        and event.optimizer_step <= checkpoint_step
        for event in suffix[:-2]
    ):
        raise RuntimeError("PhoBERT resume suffix repeats work at or before its sealed checkpoint")
    terminal_values = terminal_resource.trainer_values
    if terminal_values.get("attempt_terminal") is not True or terminal_values.get("completed") is not False:
        raise RuntimeError("PhoBERT resume suffix resource event is not a failed attempt terminal")
    terminal_wall = _finite_event_number(
        terminal_values.get("actual_wall_seconds"),
        description="terminal failed-attempt wall time",
        positive=True,
    )
    if terminal_wall < _last_attempt_wall_seconds(sealed_events):
        raise RuntimeError("PhoBERT resume suffix attempt wall time moved backward")
    failure_values = failure.trainer_values
    if failure_values.get("stage") != "training" or not isinstance(
        failure_values.get("error_type"), str
    ) or not failure_values["error_type"]:
        raise RuntimeError("PhoBERT resume suffix failure record is invalid")
    if failure.optimizer_step != terminal_resource.optimizer_step:
        raise RuntimeError("PhoBERT resume suffix terminal steps differ")
    if suffix[:-2] and failure.optimizer_step != suffix[-3].optimizer_step:
        raise RuntimeError("PhoBERT resume suffix failure is detached from post-checkpoint work")
    _derive_resume_telemetry(full_events)
    return suffix


def verify_phobert_resume_checkpoint(
    checkpoint_path: Path,
    *,
    config: PhoBertTrainingConfig,
    controlled_config: ResumeControlledConfig,
    validation_snapshot: CanonicalSplitSnapshot,
    base_model_snapshot: PhoBertBaseModelSnapshot | None = None,
    identity_prover: ModelStateIdentityProver = _model_state_identity,
) -> tuple[PhoBertResumeManifest, tuple[_Candidate, ...]]:
    """Verify an exact in-work-root checkpoint and its cumulative history."""

    checkpoint = _reject_symlink_ancestors(
        checkpoint_path, description="PhoBERT resume checkpoint"
    )
    step = _checkpoint_step(checkpoint, config.work_root)
    manifest_path = checkpoint / PHOBERT_RESUME_MANIFEST_NAME
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise RuntimeError("PhoBERT resume checkpoint lacks its exact manifest")
    try:
        manifest = PhoBertResumeManifest.model_validate_json(
            manifest_path.read_text(encoding="utf-8", errors="strict")
        )
    except Exception as exc:
        raise RuntimeError("PhoBERT resume checkpoint manifest is invalid") from exc
    snapshot = base_model_snapshot or validate_phobert_base_model_snapshot(
        config.local_base_model_path,
        manifest_path=config.resolved_base_model_provenance_path,
    )
    expected_bindings = (
        (manifest.run_id, config.run_id, "run ID"),
        (manifest.checkpoint_step, step, "checkpoint step"),
        (
            manifest.checkpoint_relative_path,
            _portable_relative(checkpoint, config.work_root, description="resume checkpoint"),
            "checkpoint path",
        ),
        (manifest.model_id, config.model_id, "model ID"),
        (manifest.model_revision, config.model_revision, "model revision"),
        (
            manifest.base_model_content_sha256,
            snapshot.snapshot_content_sha256,
            "base-model content",
        ),
        (
            manifest.base_model_manifest_sha256,
            snapshot.manifest_sha256,
            "base-model manifest",
        ),
        (
            manifest.base_model_local_path_sha256,
            snapshot.local_path_sha256,
            "base-model local path",
        ),
        (manifest.preprocessor_sha256, PHOBERT_PREPROCESSOR_SHA256, "preprocessor"),
        (
            manifest.validation_row_ids_sha256,
            controlled_config.splits[1].ordered_row_ids_sha256,
            "validation row IDs",
        ),
        (
            manifest.controlled_config_digest,
            compute_resume_digest(controlled_config),
            "controlled config",
        ),
        (
            manifest.checkpoint_payload_sha256,
            _checkpoint_payload_sha256(checkpoint),
            "checkpoint payload",
        ),
        (manifest.model_state_identity, identity_prover(checkpoint), "model state"),
    )
    for actual, expected, description in expected_bindings:
        if actual != expected:
            raise RuntimeError(f"PhoBERT resume {description} mismatch")
    events_path = config.run_bundle_root / "events.jsonl"
    event_payload = events_path.read_bytes()
    sealed_payload = event_payload[: manifest.sealed_event_bytes]
    if len(event_payload) < manifest.sealed_event_bytes or hashlib.sha256(
        sealed_payload
    ).hexdigest() != manifest.sealed_event_sha256:
        raise RuntimeError("PhoBERT resume sealed event history mismatch")
    sealed_events = _load_event_payload(sealed_payload, expected_run_id=config.run_id)
    sealed_telemetry = _derive_resume_telemetry(sealed_events)
    if sealed_telemetry != manifest.telemetry or _telemetry_sha256(
        sealed_telemetry
    ) != manifest.telemetry_sha256:
        raise RuntimeError("PhoBERT resume sealed telemetry mismatch")
    events = load_run_events(events_path, expected_run_id=config.run_id)
    _validate_failed_attempt_suffix(
        sealed_events=sealed_events,
        full_events=events,
        checkpoint_step=step,
        max_optimizer_steps=config.max_optimizer_steps,
    )
    if not any(
        event.event_kind == RunEventKind.CHECKPOINT and event.optimizer_step == step
        for event in sealed_events
    ):
        raise RuntimeError("PhoBERT resume event history lacks the selected checkpoint")
    candidates = tuple(
        _load_resumed_candidate(
            record,
            config=config,
            validation_snapshot=validation_snapshot,
            identity_prover=identity_prover,
        )
        for record in manifest.candidates
    )
    return manifest, candidates


class _EventWriter:
    def __init__(self, path: Path, run_id: str) -> None:
        self.path = path
        self.run_id = run_id

    def append(self, kind: RunEventKind, step: int, epoch: float, values: Mapping[str, object]) -> None:
        existing = load_run_events(self.path) if self.path.exists() else ()
        append_run_event(
            self.path,
            RunEvent(
                schema_version="phase40-run-event-v1",
                sequence_id=len(existing),
                event_kind=kind,
                timestamp_utc=datetime.now(timezone.utc),
                optimizer_step=step,
                epoch=max(0.0, float(epoch)),
                trainer_values=dict(values),
                source_run_id=self.run_id,
                run_kind=RunKind.FULL,
            ),
        )


class _CheckpointRecorder:
    def __init__(
        self,
        *,
        run_root: Path,
        work_root: Path,
        validation_snapshot: CanonicalSplitSnapshot,
        preprocessing_records: Sequence[PhoBertPreprocessingRecord],
        predictor: LogitPredictor,
        collator: Any,
        identity_prover: ModelStateIdentityProver,
        event_writer: _EventWriter,
    ) -> None:
        self.run_root = run_root
        self.work_root = work_root
        self.validation_snapshot = validation_snapshot
        self.preprocessing_records = tuple(preprocessing_records)
        self.predictor = predictor
        self.collator = collator
        self.identity_prover = identity_prover
        self.event_writer = event_writer
        self.candidates: dict[tuple[int, str], _Candidate] = {}

    def record(self, model: Any, step: int, artifact_path: Path, epoch: float) -> _Candidate:
        if step < 0 or not Path(artifact_path).is_dir():
            raise RuntimeError("PhoBERT validation checkpoint is missing")
        identity = self.identity_prover(Path(artifact_path))
        if not identity.startswith("model-state-sha256:") or not _SHA256_RE.fullmatch(
            identity.removeprefix("model-state-sha256:")
        ):
            raise RuntimeError("PhoBERT identity prover returned an invalid model-state identity")
        key = (step, identity)
        if key in self.candidates:
            return self.candidates[key]
        digest = identity.removeprefix("model-state-sha256:")
        candidate_root = self.run_root / "checkpoints" / f"step-{step}-{digest}"
        retained = _copy_directory_immutable(
            Path(artifact_path),
            self.work_root / "retained-checkpoints" / f"step-{step}-{digest}",
        )
        if self.identity_prover(retained) != identity:
            raise RuntimeError("retained PhoBERT model changed its state identity")
        raw_logits = self.predictor(model, self.preprocessing_records, self.collator)
        raw_rows = build_phobert_prediction_rows(
            validation_snapshot=self.validation_snapshot,
            preprocessing_records=self.preprocessing_records,
            logits=raw_logits,
            artifact_identity=identity,
            checkpoint_step=step,
        )
        prediction_path = _atomic_write(
            candidate_root / "predictions.json",
            _jsonl([row.as_json_dict() for row in raw_rows]),
        )
        metric_rows = tuple(row.as_metric_row() for row in raw_rows)
        metrics = evaluate_phase40_predictions(
            expected_validation_row_ids=self.validation_snapshot.validation_row_ids,
            gold_labels=tuple(row.record.label for row in self.validation_snapshot.rows),
            prediction_rows=metric_rows,
        )
        metrics_path = _atomic_write(candidate_root / "validation-metrics.json", _json_line(_metric_summary(metrics)))
        candidate = _Candidate(step, identity, retained, prediction_path, metrics_path, raw_rows, metrics)
        self.candidates[key] = candidate
        one = select_phase40_checkpoint((metrics,))
        self.event_writer.append(
            RunEventKind.EVALUATION,
            step,
            epoch,
            {"macro_f1": metrics.macro_f1, "safety_gate_passed": one.safety_gate_passed},
        )
        self.event_writer.append(
            RunEventKind.CHECKPOINT,
            step,
            epoch,
            {"artifact_identity": identity, "prediction_rows": len(raw_rows)},
        )
        return candidate


def _scalar_trainer_values(values: Mapping[str, Any]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in values.items():
        if isinstance(value, bool) or isinstance(value, int):
            result[str(key)] = value
        elif isinstance(value, float) and math.isfinite(value):
            result[str(key)] = value
    return result


class _AttemptClock:
    """One monotonic source shared by callbacks, checkpoint timing, and seals."""

    def __init__(self, source: Callable[[], float]) -> None:
        self._source = source
        self._started_at: float | None = None
        self._last_value: float | None = None
        self._finished = False

    def _read(self) -> float:
        value = float(self._source())
        if not math.isfinite(value):
            raise RuntimeError("PhoBERT telemetry clock returned a non-finite value")
        if self._last_value is not None and value < self._last_value:
            raise RuntimeError("PhoBERT telemetry clock moved backward")
        self._last_value = value
        return value

    def begin(self) -> None:
        if self._started_at is not None:
            raise RuntimeError("PhoBERT attempt clock began more than once")
        self._started_at = self._read()

    def __call__(self) -> float:
        if self._started_at is None or self._finished:
            raise RuntimeError("PhoBERT telemetry clock used outside an active attempt")
        return self._read()

    def snapshot_seconds(self) -> float:
        if self._started_at is None or self._last_value is None:
            raise RuntimeError("PhoBERT attempt wall time is unavailable")
        elapsed = self._last_value - self._started_at
        if not math.isfinite(elapsed) or elapsed <= 0:
            raise RuntimeError("PhoBERT attempt wall time must be positive and finite")
        return elapsed

    def finish(self) -> float:
        if self._finished:
            raise RuntimeError("PhoBERT attempt clock ended more than once")
        self._read()
        self._finished = True
        return self.snapshot_seconds()


def _build_callback(
    base: type[Any],
    *,
    recorder: _CheckpointRecorder,
    event_writer: _EventWriter,
    checkpoint_sealer: Callable[[Path], Path],
    telemetry: Phase40EvidenceCallback,
    checkpoint_durations: list[float],
    attempt_wall_seconds: Callable[[], float],
) -> Any:
    class _Callback(base):
        def on_train_begin(self, args, state, control, **kwargs):  # noqa: ANN001
            return telemetry.on_train_begin(args, state, control, **kwargs)

        def on_step_begin(self, args, state, control, **kwargs):  # noqa: ANN001
            return telemetry.on_step_begin(args, state, control, **kwargs)

        def on_step_end(self, args, state, control, **kwargs):  # noqa: ANN001
            return telemetry.on_step_end(args, state, control, **kwargs)

        def on_log(self, args, state, control, logs=None, **kwargs):  # noqa: ANN001
            values = _scalar_trainer_values(logs or {})
            if values:
                kind = RunEventKind.EVALUATION if "eval_loss" in values else RunEventKind.TRAIN_LOG
                event_writer.append(kind, int(state.global_step), float(state.epoch or 0.0), values)
            return telemetry.on_log(args, state, control, logs=logs, **kwargs)

        def on_evaluate(self, args, state, control, metrics=None, **kwargs):  # noqa: ANN001
            values = _scalar_trainer_values(metrics or {})
            if values:
                event_writer.append(
                    RunEventKind.EVALUATION,
                    int(state.global_step),
                    float(state.epoch or 0.0),
                    values,
                )
            return telemetry.on_evaluate(args, state, control, metrics=metrics, **kwargs)

        def on_save(self, args, state, control, model=None, **kwargs):  # noqa: ANN001
            if model is None:
                raise RuntimeError("PhoBERT Trainer on_save did not provide the model")
            if not checkpoint_durations:
                raise RuntimeError("PhoBERT Trainer on_save lacks isolated checkpoint timing")
            duration = checkpoint_durations.pop(0)
            checkpoint_path = Path(args.output_dir) / f"checkpoint-{int(state.global_step)}"
            recorder.record(
                model,
                int(state.global_step),
                checkpoint_path,
                float(state.epoch or 0.0),
            )
            result = telemetry.on_save(
                args,
                state,
                control,
                checkpoint_runtime_seconds=duration,
                **kwargs,
            )
            event_writer.append(
                RunEventKind.CHECKPOINT,
                int(state.global_step),
                float(state.epoch or 0.0),
                {
                    "checkpoint_runtime_seconds": duration,
                    "measurement_scope": "isolated",
                },
            )
            event_writer.append(
                RunEventKind.RESOURCE,
                int(state.global_step),
                float(state.epoch or 0.0),
                {
                    "actual_wall_seconds": attempt_wall_seconds(),
                    "telemetry_snapshot": True,
                },
            )
            checkpoint_sealer(checkpoint_path)
            return result

        def on_train_end(self, args, state, control, **kwargs):  # noqa: ANN001
            if checkpoint_durations:
                raise RuntimeError("PhoBERT checkpoint timing was not paired with on_save")
            return telemetry.on_train_end(args, state, control, **kwargs)

    return _Callback()


def _install_checkpoint_timing(
    trainer: Any,
    *,
    clock: Callable[[], float],
    cuda: CudaTimingAdapter,
    durations: list[float],
) -> list[float]:
    original = getattr(trainer, "_save_checkpoint", None)
    if not callable(original):
        raise RuntimeError("PhoBERT Trainer lacks the checkpoint hook required for isolated timing")
    def measured_save_checkpoint(*args: Any, **kwargs: Any) -> Any:
        cuda.synchronize()
        started = float(clock())
        result = original(*args, **kwargs)
        cuda.synchronize()
        duration = float(clock()) - started
        if not math.isfinite(duration) or duration < 0:
            raise RuntimeError("PhoBERT checkpoint duration must be finite and non-negative")
        durations.append(duration)
        return result

    trainer._save_checkpoint = measured_save_checkpoint
    return durations


def _telemetry_event_sink(event_writer: _EventWriter) -> Callable[[Phase40CallbackEvent], None]:
    def sink(event: Phase40CallbackEvent) -> None:
        if event.event_kind == CallbackEventKind.OPTIMIZER_STEP:
            values = dict(event.values)
            values["duration_seconds"] = event.duration_seconds
            values["is_warmup"] = event.is_warmup
            event_writer.append(
                RunEventKind.STEP_TIMING,
                event.optimizer_step,
                float(event.epoch or 0.0),
                values,
            )
        elif event.event_kind == CallbackEventKind.TRAIN_END:
            values = dict(event.values)
            values["actual_wall_seconds"] = event.duration_seconds
            event_writer.append(
                RunEventKind.RESOURCE,
                event.optimizer_step,
                float(event.epoch or 0.0),
                values,
            )

    return sink


def _restore_final_attempt_lifecycle(
    *,
    event_writer: _EventWriter,
    events: Sequence[RunEvent],
    final_step: int,
    final_epoch: float,
    candidates: Sequence[_Candidate],
) -> None:
    """Expose sealed history in a zero-work finalization attempt without new samples."""

    last_start = max(
        index for index, event in enumerate(events) if event.event_kind == RunEventKind.RUN_START
    )
    training = [
        index
        for index, event in enumerate(events)
        if index > last_start
        and event.event_kind in {RunEventKind.TRAIN_LOG, RunEventKind.STEP_TIMING}
    ]
    evaluations = [
        index
        for index, event in enumerate(events)
        if index > last_start and event.event_kind == RunEventKind.EVALUATION
    ]
    checkpoints = [
        index
        for index, event in enumerate(events)
        if index > last_start and event.event_kind == RunEventKind.CHECKPOINT
    ]
    if (
        training
        and evaluations
        and checkpoints
        and last_start < training[0] < evaluations[-1] < checkpoints[-1]
    ):
        return
    historical_step = next(
        (
            event
            for event in reversed(events[:last_start])
            if event.event_kind == RunEventKind.STEP_TIMING
            and event.trainer_values.get("restored_resume_history") is not True
        ),
        None,
    )
    if historical_step is None or not candidates:
        raise RuntimeError("PhoBERT final resume lacks sealed lifecycle history")
    candidate = max(candidates, key=lambda item: (item.step, item.artifact_identity))
    event_writer.append(
        RunEventKind.STEP_TIMING,
        final_step,
        final_epoch,
        {
            "restored_resume_history": True,
            "source_optimizer_step": historical_step.optimizer_step,
        },
    )
    event_writer.append(
        RunEventKind.EVALUATION,
        final_step,
        final_epoch,
        {
            "macro_f1": candidate.metrics.macro_f1,
            "restored_resume_history": True,
            "source_optimizer_step": candidate.step,
        },
    )
    event_writer.append(
        RunEventKind.CHECKPOINT,
        final_step,
        final_epoch,
        {
            "artifact_identity": candidate.artifact_identity,
            "restored_resume_history": True,
            "source_optimizer_step": candidate.step,
        },
    )


def _resolve_default_dependencies(dependencies: PhoBertTrainingDependencies) -> PhoBertTrainingDependencies:
    needs_stack = any(
        value is None
        for value in (
            dependencies.tokenizer_factory,
            dependencies.model_factory,
            dependencies.training_arguments_factory,
            dependencies.data_collator_factory,
            dependencies.trainer_factory,
            dependencies.trainer_callback_base,
        )
    )
    transformers_module = importlib.import_module("transformers") if needs_stack else None
    torch_module = dependencies.torch_module
    if torch_module is None and (dependencies.logits_predictor is None or dependencies.hardware is None):
        torch_module = importlib.import_module("torch")
    segmenter_version = dependencies.segmenter_version
    if segmenter_version is None:
        segmenter_version = importlib.metadata.version(PHOBERT_SEGMENTER_PACKAGE)
    package_versions = dependencies.package_versions
    if package_versions is None:
        package_versions = {
            "python": platform.python_version(),
            "torch": str(getattr(torch_module, "__version__", "unknown")),
            "transformers": str(getattr(transformers_module, "__version__", "unknown")),
            "underthesea": segmenter_version,
        }
    if dependencies.accelerator is None:
        cuda = getattr(torch_module, "cuda", None)
        cuda_available = bool(cuda is not None and cuda.is_available())
        if cuda_available:
            props = cuda.get_device_properties(0)
            capability = cuda.get_device_capability(0)
            accelerator = AcceleratorIdentity(
                accelerator_type="cuda",
                accelerator_name=str(cuda.get_device_name(0)),
                compute_capability=f"{capability[0]}.{capability[1]}",
                total_memory_bytes=int(props.total_memory),
            )
        else:
            accelerator = AcceleratorIdentity(
                accelerator_type="cpu", accelerator_name="cpu", compute_capability=None, total_memory_bytes=0
            )
    else:
        accelerator = dependencies.accelerator
    if dependencies.hardware is None:
        cuda_version = getattr(getattr(torch_module, "version", None), "cuda", None)
        hardware = RuntimeHardwareEvidence(
            python_version=platform.python_version(),
            platform=platform.platform(),
            cuda_version=None if cuda_version is None else str(cuda_version),
            cudnn_version=None,
            gpu_name=accelerator.accelerator_name if accelerator.accelerator_type == "cuda" else None,
            gpu_compute_capability=accelerator.compute_capability if accelerator.accelerator_type == "cuda" else None,
            gpu_total_memory_bytes=accelerator.total_memory_bytes if accelerator.accelerator_type == "cuda" else None,
            bf16_enabled=False,
            fp16_enabled=accelerator.accelerator_type == "cuda",
            tf32_enabled=False,
        )
    else:
        hardware = dependencies.hardware
    predictor = dependencies.logits_predictor
    if predictor is None:
        if torch_module is None:
            raise RuntimeError("default PhoBERT prediction requires torch")
        predictor = lambda model, records, collator: _default_logits_predictor(
            model, records, collator, torch_module=torch_module
        )
    cuda_timing_adapter = dependencies.cuda_timing_adapter
    if cuda_timing_adapter is None:
        cuda_timing_adapter = (
            TorchCudaTimingAdapter(torch_module.cuda)
            if torch_module is not None and hasattr(torch_module, "cuda")
            else NoCudaTimingAdapter()
        )
    return replace(
        dependencies,
        segmenter=dependencies.segmenter or _default_segmenter,
        segmenter_version=segmenter_version,
        tokenizer_factory=dependencies.tokenizer_factory or transformers_module.AutoTokenizer.from_pretrained,
        model_factory=(
            dependencies.model_factory
            or transformers_module.AutoModelForSequenceClassification.from_pretrained
        ),
        training_arguments_factory=dependencies.training_arguments_factory or transformers_module.TrainingArguments,
        data_collator_factory=dependencies.data_collator_factory or transformers_module.DataCollatorWithPadding,
        trainer_factory=dependencies.trainer_factory or transformers_module.Trainer,
        trainer_callback_base=dependencies.trainer_callback_base or transformers_module.TrainerCallback,
        logits_predictor=predictor,
        model_state_identity_prover=dependencies.model_state_identity_prover or _model_state_identity,
        package_versions=package_versions,
        accelerator=accelerator,
        hardware=hardware,
        torch_module=torch_module,
        cuda_timing_adapter=cuda_timing_adapter,
    )


def _build_phobert_training_arguments(
    training_arguments_factory: Callable[..., Any],
    training_kwargs: Mapping[str, Any],
) -> Any:
    parameters = inspect.signature(training_arguments_factory).parameters
    accepts_arbitrary_kwargs = any(
        parameter.kind is inspect.Parameter.VAR_KEYWORD
        for parameter in parameters.values()
    )
    supported_kwargs = (
        dict(training_kwargs)
        if accepts_arbitrary_kwargs
        else {
            key: value
            for key, value in training_kwargs.items()
            if key in parameters
        }
    )
    return training_arguments_factory(**supported_kwargs)


def _prepare_run_root(path: Path, *, resume: bool) -> Path:
    root = Path(path)
    if not root.is_absolute():
        raise ValueError("PhoBERT run_bundle_root must be an absolute request-bound path")
    root = _reject_symlink_ancestors(root, description="PhoBERT returned bundle root")
    if root.exists():
        if not root.is_dir() or root.is_symlink():
            raise FileExistsError("PhoBERT returned bundle root is not a safe directory")
        _reject_tree_symlinks(root, description="PhoBERT returned bundle root")
        if not resume and any(root.iterdir()):
            raise FileExistsError("PhoBERT fresh full-run root must not already contain artifacts")
        if resume:
            if (root / "run-evidence.json").exists():
                raise FileExistsError("a finalized PhoBERT bundle cannot be resumed")
            if not (root / "events.jsonl").is_file():
                raise RuntimeError("PhoBERT resume requires its existing append-only event history")
    else:
        if resume:
            raise FileNotFoundError("PhoBERT resume requires the existing run-bound evidence root")
        root.mkdir(parents=True)
    return root


def _prepare_work_root(config: PhoBertTrainingConfig) -> tuple[Path, Path | None]:
    root = _reject_symlink_ancestors(
        Path(config.work_root), description="PhoBERT mutable work_root"
    )
    resume = config.resume_from_checkpoint is not None
    if root.exists():
        if not root.is_dir() or root.is_symlink():
            raise FileExistsError("PhoBERT mutable work_root is not a safe directory")
        _reject_tree_symlinks(root, description="PhoBERT mutable work_root")
        if not resume and any(root.iterdir()):
            raise FileExistsError("PhoBERT fresh work_root must not already contain artifacts")
    else:
        if resume:
            raise FileNotFoundError("PhoBERT resume requires an existing mutable work_root")
        root.mkdir(parents=True)
    if not resume:
        return root, None
    supplied = Path(config.resume_from_checkpoint)
    if not supplied.is_absolute():
        supplied = root / supplied
    checkpoint = _reject_symlink_ancestors(
        supplied, description="PhoBERT exact resume checkpoint"
    )
    _checkpoint_step(checkpoint, root)
    if not checkpoint.is_dir() or checkpoint.is_symlink():
        raise FileNotFoundError("PhoBERT exact resume checkpoint is missing or unsafe")
    if (root / "final-model").exists():
        raise FileExistsError("completed PhoBERT work artifacts cannot be resumed")
    return root, checkpoint


def _artifact(
    run_root: Path,
    logical_name: str,
    role: str,
    path: Path,
    *,
    kind: str = "file",
) -> ArtifactEvidence:
    artifact_path = _reject_symlink_ancestors(
        path, description=f"PhoBERT {logical_name} artifact"
    )
    if artifact_path.is_dir():
        _reject_tree_symlinks(
            artifact_path, description=f"PhoBERT {logical_name} artifact"
        )
    return ArtifactEvidence(
        logical_name=logical_name,
        role=role,
        relative_path=_portable_relative(
            artifact_path, run_root, description=f"{logical_name} artifact"
        ),
        kind=kind,
        sha256=build_model_checksum(artifact_path),
    )


def _selection_rationale(selection: CheckpointSelection) -> str:
    if selection.safety_gate_passed:
        return (
            "passed risky recall and zero invalid admission; selected by macro f1, "
            "risky-to-benign, earlier-step, artifact tie breaks"
        )
    violations = "; ".join(selection.violations)
    return f"no checkpoint passed safety admission; retained best visible macro f1 candidate; {violations}"


def run_phobert_training(
    config: PhoBertTrainingConfig,
    data_contract: Phase40DataContract,
    *,
    dependencies: PhoBertTrainingDependencies | None = None,
    requested_control_template: Any | None = None,
) -> PhoBertTrainingResult:
    """Run the full four-logit PhoBERT experiment and finalize its evidence."""

    if not isinstance(config, PhoBertTrainingConfig):
        raise TypeError("config must be PhoBertTrainingConfig")
    if not isinstance(data_contract, Phase40DataContract):
        raise TypeError("data_contract must be the canonical Phase40DataContract")
    if not data_contract.train_snapshot.rows or not data_contract.validation_snapshot.rows:
        raise ValueError("PhoBERT refuses an empty train or validation snapshot")
    base_model_snapshot = verify_phobert_base_model_provenance(
        config.local_base_model_path,
        config.resolved_base_model_provenance_path,
    )
    resolved = _resolve_default_dependencies(dependencies or PhoBertTrainingDependencies())
    if resolved.segmenter_version != PHOBERT_SEGMENTER_VERSION:
        raise RuntimeError("PhoBERT requires the pinned underthesea 9.5.0 runtime")
    if (
        resolved.hardware.bf16_enabled != config.bf16
        or resolved.hardware.fp16_enabled != config.fp16
        or resolved.hardware.tf32_enabled != config.tf32
    ):
        raise RuntimeError("PhoBERT runtime precision evidence differs from the controlled precision")
    work_root, resume_checkpoint = _prepare_work_root(config)
    controlled = build_phobert_controlled_config(
        config,
        data_contract,
        accelerator=resolved.accelerator,
    )
    if requested_control_template is not None:
        verifier = getattr(requested_control_template, "verify_runtime_config", None)
        if not callable(verifier):
            raise TypeError("requested_control_template lacks verify_runtime_config")
        verifier(controlled)
    run_root = _prepare_run_root(config.run_bundle_root, resume=resume_checkpoint is not None)
    resumed_candidates: tuple[_Candidate, ...] = ()
    if resume_checkpoint is not None:
        _, resumed_candidates = verify_phobert_resume_checkpoint(
            resume_checkpoint,
            config=config,
            controlled_config=controlled,
            validation_snapshot=data_contract.validation_snapshot,
            base_model_snapshot=base_model_snapshot,
            identity_prover=resolved.model_state_identity_prover,
        )
    event_writer = _EventWriter(run_root / "events.jsonl", config.run_id)
    origin_step = 0 if resume_checkpoint is None else _checkpoint_step(resume_checkpoint, work_root)
    event_writer.append(
        RunEventKind.RUN_START,
        origin_step,
        0.0,
        {
            "origin_step": origin_step,
            "fresh_full_run": resume_checkpoint is None,
            "base_model_content_sha256": base_model_snapshot.snapshot_content_sha256,
            "base_model_manifest_sha256": base_model_snapshot.manifest_sha256,
            "base_model_local_path_sha256": base_model_snapshot.local_path_sha256,
        },
    )

    tokenizer = resolved.tokenizer_factory(
        str(base_model_snapshot.local_snapshot_path),
        revision=config.model_revision,
        local_files_only=config.local_files_only,
        trust_remote_code=False,
        use_fast=True,
    )
    train_records = preprocess_phobert_snapshot(
        data_contract.train_snapshot,
        tokenizer=tokenizer,
        segmenter=resolved.segmenter,
        segmenter_version=resolved.segmenter_version,
    )
    validation_records = preprocess_phobert_snapshot(
        data_contract.validation_snapshot,
        tokenizer=tokenizer,
        segmenter=resolved.segmenter,
        segmenter_version=resolved.segmenter_version,
    )
    all_preprocessing = train_records + validation_records
    preprocessing_path = _atomic_write(
        run_root / "preprocessing.jsonl",
        _jsonl([record.as_json_dict() for record in all_preprocessing]),
    )

    model = resolved.model_factory(
        str(base_model_snapshot.local_snapshot_path),
        revision=config.model_revision,
        num_labels=len(LABEL_ORDER),
        id2label=PHOBERT_ID_TO_LABEL,
        label2id=PHOBERT_LABEL_TO_ID,
        local_files_only=config.local_files_only,
        trust_remote_code=False,
    )
    _assert_plain_full_classifier(model)
    collator = resolved.data_collator_factory(tokenizer=tokenizer, padding="longest", return_tensors="pt")
    resolved_config_path = _atomic_write(
        run_root / "resolved-config.json",
        _json_line(controlled.model_dump(mode="json")),
    )

    trainer_root = work_root / "trainer"
    training_args = _build_phobert_training_arguments(
        resolved.training_arguments_factory,
        {
            "output_dir": str(trainer_root),
            "seed": config.seed,
            "data_seed": config.data_seed,
            "max_steps": config.max_optimizer_steps,
            "num_train_epochs": config.num_train_epochs,
            "per_device_train_batch_size": config.per_device_train_batch_size,
            "per_device_eval_batch_size": config.per_device_train_batch_size,
            "gradient_accumulation_steps": config.gradient_accumulation_steps,
            "learning_rate": config.learning_rate,
            "weight_decay": config.weight_decay,
            "optim": config.optimizer_name,
            "lr_scheduler_type": config.lr_scheduler_type,
            "warmup_steps": config.warmup_steps,
            "warmup_ratio": config.warmup_ratio,
            "max_grad_norm": config.max_grad_norm,
            "logging_strategy": "steps",
            "logging_steps": config.logging_steps,
            "eval_strategy": "steps",
            "eval_steps": config.evaluation_steps,
            "save_strategy": "steps",
            "save_steps": config.evaluation_steps,
            "save_total_limit": config.save_total_limit,
            "load_best_model_at_end": False,
            "report_to": "none",
            "remove_unused_columns": False,
            "bf16": config.bf16,
            "fp16": config.fp16,
            "tf32": config.tf32,
            "gradient_checkpointing": config.gradient_checkpointing,
            "save_safetensors": True,
        },
    )
    recorder = _CheckpointRecorder(
        run_root=run_root,
        work_root=work_root,
        validation_snapshot=data_contract.validation_snapshot,
        preprocessing_records=validation_records,
        predictor=resolved.logits_predictor,
        collator=collator,
        identity_prover=resolved.model_state_identity_prover,
        event_writer=event_writer,
    )
    recorder.candidates.update(
        {(candidate.step, candidate.artifact_identity): candidate for candidate in resumed_candidates}
    )
    average_tokens = max(
        1,
        round(
            sum(record.segmentation.retained_token_count for record in train_records)
            / len(train_records)
        ),
    )
    attempt_clock = _AttemptClock(resolved.telemetry_clock)
    telemetry = Phase40EvidenceCallback(
        run_id=config.run_id,
        run_kind=RunKind.FULL,
        warmup_optimizer_steps=config.warmup_steps,
        target_post_warmup_steps=None,
        examples_per_optimizer_step=(
            config.per_device_train_batch_size * config.gradient_accumulation_steps
        ),
        planned_full_optimizer_steps=config.max_optimizer_steps,
        tokens_per_optimizer_step=(
            average_tokens
            * config.per_device_train_batch_size
            * config.gradient_accumulation_steps
        ),
        event_sink=_telemetry_event_sink(event_writer),
        clock=attempt_clock,
        utc_clock=resolved.telemetry_utc_clock,
        cuda=resolved.cuda_timing_adapter,
    )
    checkpoint_durations: list[float] = []
    callback = _build_callback(
        resolved.trainer_callback_base,
        recorder=recorder,
        event_writer=event_writer,
        checkpoint_sealer=lambda checkpoint_path: seal_phobert_resume_checkpoint(
            checkpoint_path,
            config=config,
            controlled_config=controlled,
            candidates=tuple(recorder.candidates.values()),
            base_model_snapshot=base_model_snapshot,
            identity_prover=resolved.model_state_identity_prover,
        ),
        telemetry=telemetry,
        checkpoint_durations=checkpoint_durations,
        attempt_wall_seconds=attempt_clock.snapshot_seconds,
    )
    trainer = resolved.trainer_factory(
        model=model,
        args=training_args,
        train_dataset=_PhoBertDataset(train_records),
        eval_dataset=_PhoBertDataset(validation_records),
        data_collator=collator,
        callbacks=[callback],
    )
    _install_checkpoint_timing(
        trainer,
        clock=attempt_clock,
        cuda=resolved.cuda_timing_adapter,
        durations=checkpoint_durations,
    )
    attempt_clock.begin()
    try:
        trainer.train(
            resume_from_checkpoint=(str(resume_checkpoint) if resume_checkpoint is not None else None)
        )
    except Exception as exc:
        failed_state = getattr(trainer, "state", None)
        failed_step = max(origin_step, int(getattr(failed_state, "global_step", origin_step)))
        failed_epoch = float(getattr(failed_state, "epoch", 0.0) or 0.0)
        event_writer.append(
            RunEventKind.RESOURCE,
            failed_step,
            failed_epoch,
            {
                "actual_wall_seconds": attempt_clock.finish(),
                "attempt_terminal": True,
                "completed": False,
            },
        )
        event_writer.append(
            RunEventKind.FAILURE,
            failed_step,
            failed_epoch,
            {"error_type": type(exc).__name__, "stage": "training"},
        )
        failed_checkpoint = trainer_root / f"checkpoint-{failed_step}"
        if failed_checkpoint.is_dir() and any(
            candidate.step == failed_step for candidate in recorder.candidates.values()
        ):
            seal_phobert_resume_checkpoint(
                failed_checkpoint,
                config=config,
                controlled_config=controlled,
                candidates=tuple(recorder.candidates.values()),
                base_model_snapshot=base_model_snapshot,
                identity_prover=resolved.model_state_identity_prover,
            )
        raise
    successful_attempt_wall = attempt_clock.finish()
    state = getattr(trainer, "state", None)
    final_step = int(getattr(state, "global_step", -1))
    final_epoch = float(getattr(state, "epoch", config.num_train_epochs) or config.num_train_epochs)
    if final_step != config.max_optimizer_steps:
        raise RuntimeError(
            f"PhoBERT ended at optimizer step {final_step}, expected {config.max_optimizer_steps}"
        )
    event_writer.append(
        RunEventKind.RESOURCE,
        final_step,
        final_epoch,
        {
            "actual_wall_seconds": successful_attempt_wall,
            "attempt_terminal": True,
            "completed": True,
        },
    )
    cumulative_telemetry = _derive_resume_telemetry(
        load_run_events(run_root / "events.jsonl", expected_run_id=config.run_id)
    )
    resource_summary = _resource_summary_from_telemetry(cumulative_telemetry, config=config)
    final_source = work_root / "final-model"
    trainer.save_model(str(final_source))
    recorder.record(model, final_step, final_source, final_epoch)
    observed_steps = {candidate.step for candidate in recorder.candidates.values()}
    if observed_steps != set(config.evaluation_schedule):
        raise RuntimeError(
            "PhoBERT checkpoint cadence mismatch: "
            f"expected {config.evaluation_schedule}, got {tuple(sorted(observed_steps))}"
        )
    checkpoint_metrics = tuple(
        candidate.metrics
        for candidate in sorted(recorder.candidates.values(), key=lambda item: (item.step, item.artifact_identity))
    )
    selection = select_phase40_checkpoint(checkpoint_metrics)
    selected = recorder.candidates[(selection.selected_step, selection.selected_artifact_identity)]
    selected_model_path = _copy_directory_immutable(selected.retained_model_path, run_root / "adapter-or-model")
    retained_base_provenance = _atomic_write(
        selected_model_path / PHOBERT_BASE_MODEL_MANIFEST_NAME,
        base_model_snapshot.manifest_path.read_bytes(),
    )
    if build_model_checksum(retained_base_provenance) != base_model_snapshot.manifest_sha256:
        raise RuntimeError("retained PhoBERT base-model provenance hash drifted")

    if callable(getattr(trainer, "save_state", None)):
        trainer.save_state()
    trainer_state_source = trainer_root / "trainer_state.json"
    if (
        not trainer_state_source.is_file()
        or trainer_state_source.is_symlink()
        or trainer_state_source.stat().st_size == 0
    ):
        raise RuntimeError("PhoBERT Trainer did not persist trainer_state.json")
    trainer_state_path = _atomic_write(run_root / "trainer_state.json", trainer_state_source.read_bytes())
    selected_predictions_path = _atomic_write(run_root / "predictions.json", selected.prediction_path.read_bytes())
    selected_metrics_path = _atomic_write(run_root / "validation-metrics.json", selected.metrics_path.read_bytes())
    final_resume_checkpoint = trainer_root / f"checkpoint-{final_step}"
    if not final_resume_checkpoint.is_dir() and resume_checkpoint is not None:
        final_resume_checkpoint = resume_checkpoint
    if final_resume_checkpoint.is_dir():
        seal_phobert_resume_checkpoint(
            final_resume_checkpoint,
            config=config,
            controlled_config=controlled,
            candidates=tuple(recorder.candidates.values()),
            base_model_snapshot=base_model_snapshot,
            identity_prover=resolved.model_state_identity_prover,
        )
    _restore_final_attempt_lifecycle(
        event_writer=event_writer,
        events=load_run_events(run_root / "events.jsonl", expected_run_id=config.run_id),
        final_step=final_step,
        final_epoch=final_epoch,
        candidates=tuple(recorder.candidates.values()),
    )
    event_writer.append(
        RunEventKind.RUN_END,
        final_step,
        final_epoch,
        {
            "selected_step": selection.selected_step,
            "safety_gate_passed": selection.safety_gate_passed,
            "completed": True,
            "observed_optimizer_steps": resource_summary.observed_optimizer_steps,
            "evaluation_overhead_seconds": resource_summary.evaluation_overhead_seconds,
            "checkpoint_overhead_seconds": resource_summary.checkpoint_overhead_seconds,
            "actual_wall_seconds": resource_summary.actual_wall_seconds,
        },
    )
    load_run_events(run_root / "events.jsonl", expected_run_id=config.run_id)

    graph = render_phase40_graphs(
        run_root,
        renderer=resolved.graph_renderer,
        renderer_name=resolved.graph_renderer_name,
        renderer_version=resolved.graph_renderer_version,
    )
    artifacts: dict[str, ArtifactEvidence] = {
        "events": _artifact(run_root, "events", "events", run_root / "events.jsonl"),
        "graph-data-loss": _artifact(
            run_root, "graph-data-loss", "graph_data", run_root / "curves/normalized-loss-curves.json"
        ),
        "graph-manifest-loss": _artifact(
            run_root, "graph-manifest-loss", "graph_manifest", run_root / "curves/graph-provenance.json"
        ),
        "graph-output-loss": _artifact(
            run_root, "graph-output-loss", "graph_output", run_root / "curves/loss-curves.png"
        ),
        "model-artifact": _artifact(
            run_root, "model-artifact", "model_artifact", selected_model_path, kind="directory"
        ),
        "predictions": _artifact(run_root, "predictions", "predictions", selected_predictions_path),
        "preprocessing": _artifact(run_root, "preprocessing", "preprocessing", preprocessing_path),
        "resolved-config": _artifact(run_root, "resolved-config", "resolved_config", resolved_config_path),
        "trainer-state": _artifact(run_root, "trainer-state", "trainer_state", trainer_state_path),
        "validation-metrics": _artifact(
            run_root, "validation-metrics", "metrics", selected_metrics_path
        ),
    }
    checkpoint_evidence: list[ValidationCheckpointEvidence] = []
    for candidate in sorted(recorder.candidates.values(), key=lambda item: (item.step, item.artifact_identity)):
        if candidate is selected:
            prediction_artifact = artifacts["predictions"]
            metric_artifact = artifacts["validation-metrics"]
        else:
            digest = candidate.artifact_identity.removeprefix("model-state-sha256:")
            prediction_name = f"predictions-step-{candidate.step}-{digest}"
            metric_name = f"validation-metrics-step-{candidate.step}-{digest}"
            prediction_artifact = _artifact(
                run_root, prediction_name, "predictions", candidate.prediction_path
            )
            metric_artifact = _artifact(run_root, metric_name, "metrics", candidate.metrics_path)
            artifacts[prediction_name] = prediction_artifact
            artifacts[metric_name] = metric_artifact
        one = select_phase40_checkpoint((candidate.metrics,))
        checkpoint_evidence.append(
            ValidationCheckpointEvidence(
                optimizer_step=candidate.step,
                artifact_identity=candidate.artifact_identity,
                predictions_sha256=prediction_artifact.sha256,
                metrics_sha256=metric_artifact.sha256,
                macro_f1=candidate.metrics.macro_f1,
                safety_gate_passed=one.safety_gate_passed,
                invalid_output_count=candidate.metrics.invalid_output_count,
            )
        )
    sorted_artifacts = tuple(sorted(artifacts.values(), key=lambda item: item.logical_name))
    if verify_phobert_base_model_provenance(
        config.local_base_model_path,
        config.resolved_base_model_provenance_path,
    ) != base_model_snapshot:
        raise RuntimeError("PhoBERT base-model provenance changed during training")
    evidence = RunEvidence(
        schema_version="phase40-run-evidence-v1",
        run_id=config.run_id,
        run_kind=RunKind.FULL,
        experiment_identity=config.identity,
        model_id=config.model_id,
        model_revision=config.model_revision,
        splits=controlled.splits,
        seed=config.seed,
        data_seed=config.data_seed,
        resolved_config_sha256=artifacts["resolved-config"].sha256,
        resume_digest=compute_resume_digest(controlled),
        prompt_or_preprocessor_sha256=PHOBERT_PREPROCESSOR_SHA256,
        decoder_contract=None,
        decoder_contract_sha256=None,
        sanitized_argv=config.sanitized_argv,
        package_versions=sanitize_package_versions(resolved.package_versions),
        hardware=resolved.hardware,
        quantization=None,
        peak_allocated_bytes=resource_summary.peak_allocated_bytes,
        peak_reserved_bytes=resource_summary.peak_reserved_bytes,
        steady_step_seconds_median=resource_summary.steady_state_step_seconds_median,
        validation_metrics=_run_metric_summary(selection.selected_metrics),
        validation_checkpoints=tuple(checkpoint_evidence),
        selected_checkpoint=SelectedCheckpointEvidence(
            optimizer_step=selection.selected_step,
            artifact_identity=selection.selected_artifact_identity,
            safety_gate_passed=selection.safety_gate_passed,
            rationale=_selection_rationale(selection),
        ),
        artifacts=sorted_artifacts,
        artifact_sha256={artifact.logical_name: artifact.sha256 for artifact in sorted_artifacts},
        graph_provenance=(graph.as_evidence(),),
        transfer_authority=config.transfer_authority,
        status=EvidenceStatus.COMPLETE,
        comparison_eligible=True,
        failure_reason=None,
        git_commit=None,
    )
    evidence_path = finalize_run_evidence(run_root, evidence)
    verified = verify_phase40_bundle(run_root, evidence_path=evidence_path)
    if verified != evidence:
        raise RuntimeError("PhoBERT evidence changed during final verification")
    return PhoBertTrainingResult(
        run_root=run_root,
        evidence_path=evidence_path,
        evidence=verified,
        controlled_config=controlled,
        preprocessing_records=all_preprocessing,
        checkpoint_metrics=checkpoint_metrics,
        selection=selection,
    )


__all__ = [
    "PHOBERT_BASE_MODEL_MANIFEST_NAME",
    "PHOBERT_ID_TO_LABEL",
    "PHOBERT_LABEL_TO_ID",
    "PHOBERT_MAX_LENGTH",
    "PHOBERT_MODEL_ID",
    "PHOBERT_MODEL_REVISION",
    "PHOBERT_PREPROCESSOR_SHA256",
    "PHOBERT_PREPROCESSOR_VERSION",
    "PHOBERT_SEGMENTER_VERSION",
    "PhoBertBaseModelProvenance",
    "PhoBertBaseModelAcquisitionRequest",
    "PhoBertBaseModelSnapshot",
    "PhoBertPreprocessingRecord",
    "PhoBertRawPredictionRow",
    "PhoBertSegmentation",
    "PhoBertTrainingConfig",
    "PhoBertTrainingDependencies",
    "PhoBertTrainingResult",
    "build_phobert_controlled_config",
    "build_phobert_base_model_acquisition_request",
    "build_phobert_prediction_rows",
    "preprocess_phobert_snapshot",
    "run_phobert_training",
    "seal_phobert_base_model_provenance",
    "seal_phobert_base_model_snapshot",
    "segment_for_phobert",
    "verify_phobert_base_model_provenance",
    "validate_phobert_base_model_snapshot",
]
