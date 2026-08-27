"""Fail-closed evidence, resume, and comparison contracts for Phase 40.

This module deliberately has no Trainer, CUDA, model, or plotting imports.  It
owns the immutable boundary between append-only raw observations and claims
that may later be published by the training/comparison orchestration.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from enum import StrEnum
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import tempfile
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.model_adaptation.phase40_modes import (
    AdaptationMode,
    ExperimentIdentity,
    ModelFamily,
    QuantizationProof,
    ResolvedQwenMode,
    RunKind,
)
from src.model_adaptation.registry import build_model_checksum
from src.model_adaptation.schemas import LOCKED_RELEASE_LABELS


Sha256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
GitCommit = Annotated[str, Field(pattern=r"^[0-9a-f]{40}$")]
_SAFE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_MODEL_ID_PATTERN = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}(?:/[A-Za-z0-9][A-Za-z0-9._-]{0,127})?$"
)
_CONTROL_NAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,127}$")
_SECRET_OPTION_PATTERN = re.compile(
    r"(?:^|[-_.])(?:api[-_]?key|auth(?:orization)?|bearer|credential|"
    r"password|passwd|secret|access[-_]?token|refresh[-_]?token|hf[-_]?token)"
    r"(?:$|[-_.])",
    re.IGNORECASE,
)
_SECRET_VALUE_PATTERNS = (
    re.compile(r"^sk-[A-Za-z0-9_-]{8,}$"),
    re.compile(r"^hf_[A-Za-z0-9]{8,}$"),
    re.compile(r"^Bearer\s+\S+$", re.IGNORECASE),
    re.compile(r"^eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$"),
)
_ALLOWED_ENVIRONMENT_KEYS = frozenset(
    {
        "python_version",
        "platform",
        "cuda_version",
        "cudnn_version",
        "gpu_name",
        "gpu_compute_capability",
        "gpu_total_memory_bytes",
        "bf16_enabled",
        "fp16_enabled",
        "tf32_enabled",
    }
)
_ALLOWED_PHASE40_OPERATOR_PATH_ROOTS = (
    "/content/drive/MyDrive/internship-phase40",
    "/content/phase40-input-v1",
    "/content/phase40-source-v1",
)


class _StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        allow_inf_nan=False,
    )


def _require_safe_identifier(value: str, *, field_name: str) -> str:
    if not isinstance(value, str) or not _SAFE_ID_PATTERN.fullmatch(value):
        raise ValueError(f"{field_name} must be a non-empty portable identifier")
    return value


def _require_model_identifier(value: str) -> str:
    if not isinstance(value, str) or not _MODEL_ID_PATTERN.fullmatch(value):
        raise ValueError("model identifier must be a portable model name or owner/model pair")
    return value


def _is_absolute_or_personal_path(value: str) -> bool:
    if value.startswith("~"):
        return True
    if PureWindowsPath(value).is_absolute() or PurePosixPath(value).is_absolute():
        return True
    normalized = value.replace("\\", "/").casefold()
    return normalized.startswith(("/home/", "/users/")) or "/onedrive - " in normalized


def _is_allowed_phase40_operator_path(value: str) -> bool:
    """Allow only the fixed, non-personal Colab namespaces frozen by Phase 40."""

    if not isinstance(value, str) or "\\" in value:
        return False
    candidate = value.strip()
    if not candidate.startswith("/content/") or ".." in PurePosixPath(candidate).parts:
        return False
    return any(
        candidate == root or candidate.startswith(root + "/")
        for root in _ALLOWED_PHASE40_OPERATOR_PATH_ROOTS
    )


def _reject_sensitive_text(value: str, *, field_name: str, reject_paths: bool = True) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    if any(character in value for character in ("\x00", "\r", "\n")):
        raise ValueError(f"{field_name} contains a control character")
    if _SECRET_OPTION_PATTERN.search(value):
        raise ValueError(f"{field_name} contains a credential/secret marker")
    if any(pattern.fullmatch(value.strip()) for pattern in _SECRET_VALUE_PATTERNS):
        raise ValueError(f"{field_name} looks like credential material")
    if reject_paths and _is_absolute_or_personal_path(value):
        raise ValueError(f"{field_name} contains an absolute or personal path")
    return value


def _validate_json_value(value: Any, *, location: str) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{location} contains NaN or infinity")
        return value
    if isinstance(value, list):
        return [_validate_json_value(item, location=f"{location}[]") for item in value]
    if isinstance(value, tuple):
        return tuple(_validate_json_value(item, location=f"{location}[]") for item in value)
    if isinstance(value, dict):
        if any(not isinstance(key, str) or not key for key in value):
            raise ValueError(f"{location} contains a non-string or empty key")
        return {
            key: _validate_json_value(item, location=f"{location}.{key}")
            for key, item in value.items()
        }
    raise ValueError(f"{location} contains a non-JSON value: {type(value).__name__}")


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _domain_sha256(domain: str, value: Any) -> str:
    digest = hashlib.sha256()
    digest.update(domain.encode("ascii"))
    digest.update(b"\0")
    digest.update(_canonical_json_bytes(value))
    return digest.hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _portable_relative_path(value: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise ValueError("artifact paths must be non-empty POSIX relative paths")
    if PureWindowsPath(value).is_absolute():
        raise ValueError("artifact paths must not be Windows absolute paths")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
        raise ValueError("artifact paths must be normalized run-relative paths")
    if value.startswith("~"):
        raise ValueError("artifact paths must not contain a home-directory alias")
    return path.as_posix()


def _run_relative_path(run_root: Path, relative_path: str) -> Path:
    relative = _portable_relative_path(relative_path)
    root = Path(os.path.abspath(os.path.normpath(os.fspath(run_root))))
    candidate = Path(os.path.abspath(os.path.normpath(os.fspath(root / relative))))
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError("artifact path escapes the run root") from exc
    current = root
    for part in PurePosixPath(relative).parts:
        current = current / part
        if current.exists() and current.is_symlink():
            raise ValueError(f"artifact path traverses a symlink: {relative}")
    return candidate


def _atomic_write_bytes(path: Path, payload: bytes) -> Path:
    """Write immutable bytes with sibling temp/fsync/replace/read-back semantics."""

    path = Path(path)
    if path.exists():
        if not path.is_file():
            raise FileExistsError(f"atomic output path is not a file: {path}")
        if path.read_bytes() == payload:
            return path
        raise FileExistsError(f"immutable output already contains different bytes: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        mode="wb",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    )
    temporary = Path(handle.name)
    try:
        with handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        if temporary.read_bytes() != payload:
            raise RuntimeError("atomic temp-file read-back mismatch")
        os.replace(temporary, path)
        if path.read_bytes() != payload:
            raise RuntimeError("atomic output read-back mismatch")
    finally:
        if temporary.exists():
            temporary.unlink()
    return path


class RunEventKind(StrEnum):
    RUN_START = "run_start"
    TRAIN_LOG = "train_log"
    STEP_TIMING = "step_timing"
    EVALUATION = "evaluation"
    CHECKPOINT = "checkpoint"
    RESOURCE = "resource"
    RUN_END = "run_end"
    FAILURE = "failure"


class RunEvent(_StrictModel):
    """One append-only raw Trainer observation."""

    schema_version: Literal["phase40-run-event-v1"]
    sequence_id: int = Field(ge=0)
    event_kind: RunEventKind
    timestamp_utc: datetime
    optimizer_step: int = Field(ge=0)
    epoch: float = Field(ge=0)
    trainer_values: dict[str, Any] = Field(min_length=1)
    source_run_id: str
    run_kind: RunKind

    @field_validator("source_run_id")
    @classmethod
    def validate_run_id(cls, value: str) -> str:
        return _require_safe_identifier(value, field_name="source_run_id")

    @field_validator("timestamp_utc")
    @classmethod
    def require_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp_utc must be timezone-aware")
        if value.utcoffset().total_seconds() != 0:
            raise ValueError("timestamp_utc must use UTC")
        return value.astimezone(timezone.utc)

    @field_validator("trainer_values")
    @classmethod
    def validate_trainer_values(cls, value: dict[str, Any]) -> dict[str, Any]:
        return _validate_json_value(value, location="trainer_values")


def _event_jsonl_bytes(event: RunEvent) -> bytes:
    return _canonical_json_bytes(event.model_dump(mode="json")) + b"\n"


def _event_transition_error(previous: RunEvent, current: RunEvent) -> str | None:
    """Return why an append is invalid, including exact failed-attempt restarts."""

    if previous.event_kind == RunEventKind.RUN_END:
        return "event log cannot append after run_end"
    if previous.event_kind == RunEventKind.FAILURE:
        if current.event_kind == RunEventKind.RUN_END:
            return None
        if current.event_kind != RunEventKind.RUN_START:
            return "a failed attempt must be followed by run_end or a new run_start"
        # A resume may legitimately restart from the last sealed checkpoint,
        # below work observed immediately before the failure.  This is the
        # sole optimizer-step rollback allowed in an append-only run log.
        return None
    if current.event_kind == RunEventKind.RUN_START:
        return "a subsequent run_start requires a preceding failure event"
    if current.optimizer_step < previous.optimizer_step:
        return "event optimizer steps must not move backward within an attempt"
    return None


def load_run_events(
    event_path: Path,
    *,
    expected_sha256: str | None = None,
    expected_run_id: str | None = None,
) -> tuple[RunEvent, ...]:
    """Load an event log without repairing, sorting, or dropping any row."""

    event_path = Path(event_path)
    if not event_path.is_file() or event_path.stat().st_size == 0:
        raise RuntimeError(f"event log is missing or empty: {event_path}")
    payload = event_path.read_bytes()
    if expected_sha256 is not None and hashlib.sha256(payload).hexdigest() != expected_sha256:
        raise RuntimeError("event log SHA-256 mismatch")
    if not payload.endswith(b"\n"):
        raise RuntimeError("event log has a partial final record")
    try:
        lines = payload.decode("utf-8", errors="strict").splitlines()
    except UnicodeDecodeError as exc:
        raise RuntimeError("event log is not strict UTF-8") from exc
    if not lines or any(not line for line in lines):
        raise RuntimeError("event log contains an empty record")
    events: list[RunEvent] = []
    for index, line in enumerate(lines):
        try:
            event = RunEvent.model_validate_json(line)
        except Exception as exc:  # Pydantic exposes multiple concrete validation errors.
            raise RuntimeError(f"invalid event record at sequence position {index}") from exc
        if event.sequence_id != index:
            raise RuntimeError(
                f"event sequence must be contiguous from zero: position={index}, "
                f"sequence_id={event.sequence_id}"
            )
        if events:
            transition_error = _event_transition_error(events[-1], event)
            if transition_error is not None:
                raise RuntimeError(transition_error)
        if events and event.source_run_id != events[0].source_run_id:
            raise RuntimeError("event log mixes source run IDs")
        if events and event.run_kind != events[0].run_kind:
            raise RuntimeError("event log mixes probe and full run kinds")
        events.append(event)
    if expected_run_id is not None and events[0].source_run_id != expected_run_id:
        raise RuntimeError("event source run ID does not match run evidence")
    return tuple(events)


def append_run_event(event_path: Path, event: RunEvent) -> Path:
    """Append one validated event while preserving the existing byte sequence."""

    event_path = Path(event_path)
    if event_path.exists() and event_path.is_symlink():
        raise ValueError("event log must not be a symlink")
    if event_path.exists():
        existing = load_run_events(event_path)
        if event.sequence_id != len(existing):
            raise ValueError("appended event sequence_id is not the next contiguous value")
        if event.source_run_id != existing[0].source_run_id:
            raise ValueError("appended event source_run_id does not match the log")
        if event.run_kind != existing[0].run_kind:
            raise ValueError("appended event run_kind does not match the log")
        transition_error = _event_transition_error(existing[-1], event)
        if transition_error is not None:
            raise ValueError(transition_error)
    elif event.sequence_id != 0:
        raise ValueError("the first event sequence_id must be zero")
    event_path.parent.mkdir(parents=True, exist_ok=True)
    with event_path.open("ab") as handle:
        handle.write(_event_jsonl_bytes(event))
        handle.flush()
        os.fsync(handle.fileno())
    load_run_events(event_path, expected_run_id=event.source_run_id)
    return event_path


class EvidenceStatus(StrEnum):
    INCOMPLETE = "incomplete"
    PRESTART_FAILED = "prestart_failed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"
    COMPLETE = "complete"


class ExperimentIdentityEvidence(_StrictModel):
    model_family: ModelFamily
    adaptation_mode: AdaptationMode
    run_kind: RunKind

    @model_validator(mode="after")
    def validate_supported_identity(self) -> "ExperimentIdentityEvidence":
        ExperimentIdentity(self.model_family, self.adaptation_mode, self.run_kind)
        return self


class CanonicalSplitEvidence(_StrictModel):
    logical_name: Literal["train", "val"]
    relative_path: str
    records: int = Field(gt=0)
    bytes: int = Field(gt=0)
    sha256: Sha256
    ordered_row_ids_sha256: Sha256

    @field_validator("relative_path")
    @classmethod
    def validate_relative_path(cls, value: str) -> str:
        return _portable_relative_path(value)


class QuantizationProofEvidence(_StrictModel):
    requested_mode: AdaptationMode
    resolved_mode: ResolvedQwenMode
    bitsandbytes_version: str | None
    load_in_4bit: bool
    nf4: bool
    double_quantization: bool
    is_loaded_in_4bit: bool
    linear4bit_modules: int = Field(ge=0)
    kbit_preparation_applied: bool
    base_weights_frozen: bool
    adapter_only_trainables: bool
    adapter_trainable_count: int = Field(ge=0)
    backward_with_adapter_gradients: bool
    adapter_gradient_finite_count: int = Field(ge=0)
    adapter_gradient_nonzero_count: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_real_proof(self) -> "QuantizationProofEvidence":
        QuantizationProof(**self.model_dump())
        return self


class DecoderContractEvidence(_StrictModel):
    schema_version: Literal["phase40-qwen-decoder-v1"]
    do_sample: bool
    num_return_sequences: int = Field(gt=0)
    max_new_tokens: int = Field(gt=0)
    output_schema_version: str
    decoder_version: str
    generation_cadence: str
    raw_prediction_ordering_policy: str

    @field_validator(
        "output_schema_version",
        "decoder_version",
        "generation_cadence",
        "raw_prediction_ordering_policy",
    )
    @classmethod
    def validate_contract_text(cls, value: str) -> str:
        return _require_safe_identifier(value, field_name="decoder contract field")

    @property
    def sha256(self) -> str:
        return _domain_sha256(
            "phase40-qwen-decoder-contract-v1",
            self.model_dump(mode="json"),
        )


class RuntimeHardwareEvidence(_StrictModel):
    python_version: str
    platform: str
    cuda_version: str | None
    cudnn_version: str | None
    gpu_name: str | None
    gpu_compute_capability: str | None
    gpu_total_memory_bytes: int | None = Field(default=None, ge=0)
    bf16_enabled: bool
    fp16_enabled: bool
    tf32_enabled: bool

    @field_validator(
        "python_version",
        "platform",
        "cuda_version",
        "cudnn_version",
        "gpu_name",
        "gpu_compute_capability",
    )
    @classmethod
    def validate_safe_fact(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _reject_sensitive_text(value, field_name="runtime fact", reject_paths=True)


class ArtifactEvidence(_StrictModel):
    logical_name: str
    role: Literal[
        "events",
        "trainer_state",
        "resolved_config",
        "predictions",
        "metrics",
        "model_artifact",
        "graph_data",
        "graph_manifest",
        "graph_output",
        "preprocessing",
        "discard_receipt",
        "failure_evidence",
    ]
    relative_path: str
    kind: Literal["file", "directory"]
    sha256: Sha256

    @field_validator("logical_name")
    @classmethod
    def validate_logical_name(cls, value: str) -> str:
        return _require_safe_identifier(value, field_name="artifact logical_name")

    @field_validator("relative_path")
    @classmethod
    def validate_relative_path(cls, value: str) -> str:
        return _portable_relative_path(value)


class ValidationCheckpointEvidence(_StrictModel):
    optimizer_step: int = Field(ge=0)
    artifact_identity: str
    predictions_sha256: Sha256
    metrics_sha256: Sha256
    macro_f1: float = Field(ge=0, le=1)
    safety_gate_passed: bool
    invalid_output_count: int = Field(ge=0)

    @field_validator("artifact_identity")
    @classmethod
    def validate_artifact_identity(cls, value: str) -> str:
        prefixes = ("adapter-state-sha256:", "model-state-sha256:")
        prefix = next((candidate for candidate in prefixes if value.startswith(candidate)), None)
        if prefix is None:
            raise ValueError(
                "checkpoint artifact identity must be adapter-state-sha256 or "
                "model-state-sha256"
            )
        digest = value.removeprefix(prefix)
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError("checkpoint artifact identity has an invalid digest")
        return value


class SelectedCheckpointEvidence(_StrictModel):
    optimizer_step: int = Field(ge=0)
    artifact_identity: str
    safety_gate_passed: bool
    rationale: str

    @field_validator("artifact_identity")
    @classmethod
    def validate_artifact_identity(cls, value: str) -> str:
        return ValidationCheckpointEvidence.validate_artifact_identity(value)

    @field_validator("rationale")
    @classmethod
    def validate_rationale(cls, value: str) -> str:
        return _reject_sensitive_text(value, field_name="checkpoint rationale", reject_paths=True)


class GraphProvenanceEvidence(_StrictModel):
    graph_id: str
    renderer: str
    renderer_version: str
    options_sha256: Sha256
    event_source_logical_name: str
    event_source_sha256: Sha256
    metrics_source_logical_name: str
    metrics_source_sha256: Sha256
    model_artifact_logical_name: str
    model_artifact_sha256: Sha256
    normalized_data_logical_name: str
    normalized_data_sha256: Sha256
    output_logical_name: str
    output_sha256: Sha256

    @field_validator(
        "graph_id",
        "event_source_logical_name",
        "metrics_source_logical_name",
        "model_artifact_logical_name",
        "normalized_data_logical_name",
        "output_logical_name",
    )
    @classmethod
    def validate_identifiers(cls, value: str) -> str:
        return _require_safe_identifier(value, field_name="graph provenance identifier")

    @field_validator("renderer", "renderer_version")
    @classmethod
    def validate_renderer(cls, value: str) -> str:
        return _reject_sensitive_text(value, field_name="renderer fact", reject_paths=True)


class TransferAuthorityEvidence(_StrictModel):
    """Request-bound identity of the only authorized Colab transfer inputs."""

    schema_version: Literal["phase40-transfer-authority-v1"]
    source_archive_sha256: Sha256
    source_inventory_sha256: Sha256
    input_archive_sha256: Sha256
    input_manifest_sha256: Sha256
    source_repository_relative_archive_path: Literal[
        "data/models/phase40/source/phase40-source.zip"
    ]
    source_repository_relative_inventory_path: Literal[
        "data/models/phase40/source/phase40-source-manifest.json"
    ]
    input_repository_relative_path: Literal[
        "data/models/phase40/input/phase40-train-validation.zip"
    ]
    input_drive_path: Literal[
        "/content/drive/MyDrive/internship-phase40/phase40-train-validation.zip"
    ]
    input_extraction_root: Literal["/content/phase40-input-v1"]
    input_members: tuple[
        Literal["phase40-input-manifest.json"],
        Literal["train.jsonl"],
        Literal["val.jsonl"],
    ]
    no_held_out_boundary: Literal[True]


class RunEvidence(_StrictModel):
    """Complete typed evidence manifest for one Phase 40 run."""

    schema_version: Literal["phase40-run-evidence-v1"]
    run_id: str
    run_kind: RunKind
    experiment_identity: ExperimentIdentityEvidence
    model_id: str
    model_revision: GitCommit
    splits: tuple[CanonicalSplitEvidence, CanonicalSplitEvidence]
    seed: int
    data_seed: int
    resolved_config_sha256: Sha256
    resume_digest: Sha256
    prompt_or_preprocessor_sha256: Sha256
    decoder_contract: DecoderContractEvidence | None
    decoder_contract_sha256: Sha256 | None
    sanitized_argv: tuple[str, ...] = Field(min_length=1)
    package_versions: dict[str, str] = Field(min_length=1)
    hardware: RuntimeHardwareEvidence
    quantization: QuantizationProofEvidence | None
    peak_allocated_bytes: int = Field(ge=0)
    peak_reserved_bytes: int = Field(ge=0)
    steady_step_seconds_median: float | None = Field(default=None, gt=0)
    validation_metrics: dict[str, float]
    validation_checkpoints: tuple[ValidationCheckpointEvidence, ...]
    selected_checkpoint: SelectedCheckpointEvidence | None
    artifacts: tuple[ArtifactEvidence, ...]
    artifact_sha256: dict[str, Sha256]
    graph_provenance: tuple[GraphProvenanceEvidence, ...]
    transfer_authority: TransferAuthorityEvidence | None = None
    status: EvidenceStatus
    comparison_eligible: bool
    failure_reason: str | None
    git_commit: GitCommit | None = None

    @field_validator("run_id")
    @classmethod
    def validate_run_identifier(cls, value: str) -> str:
        return _require_safe_identifier(value, field_name="run identifier")

    @field_validator("model_id")
    @classmethod
    def validate_model_identifier(cls, value: str) -> str:
        return _require_model_identifier(value)

    @field_validator("sanitized_argv")
    @classmethod
    def validate_sanitized_argv(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return sanitize_argv(value)

    @field_validator("package_versions")
    @classmethod
    def validate_package_versions(cls, value: dict[str, str]) -> dict[str, str]:
        return sanitize_package_versions(value)

    @field_validator("validation_metrics")
    @classmethod
    def validate_metrics(cls, value: dict[str, float]) -> dict[str, float]:
        if any(not _CONTROL_NAME_PATTERN.fullmatch(name) for name in value):
            raise ValueError("validation metric names must be portable control names")
        if any(not math.isfinite(metric) for metric in value.values()):
            raise ValueError("validation metrics must be finite")
        return value

    @field_validator("failure_reason")
    @classmethod
    def validate_failure_reason(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _reject_sensitive_text(value, field_name="failure_reason", reject_paths=True)

    @model_validator(mode="after")
    def validate_evidence_contract(self) -> "RunEvidence":
        if self.run_kind != self.experiment_identity.run_kind:
            raise ValueError("run_kind must match experiment_identity")
        if tuple(split.logical_name for split in self.splits) != ("train", "val"):
            raise ValueError("Phase 40 evidence must contain train then val only")
        logical_names = tuple(artifact.logical_name for artifact in self.artifacts)
        if logical_names != tuple(sorted(logical_names)) or len(set(logical_names)) != len(logical_names):
            raise ValueError("artifacts must be unique and sorted by logical_name")
        expected_hashes = {artifact.logical_name: artifact.sha256 for artifact in self.artifacts}
        if self.artifact_sha256 != expected_hashes:
            raise ValueError("artifact_sha256 must exactly match the ordered artifact records")
        role_records: dict[str, list[ArtifactEvidence]] = {}
        for artifact in self.artifacts:
            role_records.setdefault(artifact.role, []).append(artifact)
        resolved_configs = role_records.get("resolved_config", [])
        if resolved_configs and (
            len(resolved_configs) != 1
            or resolved_configs[0].sha256 != self.resolved_config_sha256
        ):
            raise ValueError("resolved config artifact does not match resolved_config_sha256")
        if self.decoder_contract is None:
            if self.decoder_contract_sha256 is not None:
                raise ValueError("decoder hash cannot exist without a decoder contract")
        elif self.decoder_contract_sha256 != self.decoder_contract.sha256:
            raise ValueError("decoder contract SHA-256 mismatch")
        if self.experiment_identity.model_family == ModelFamily.QWEN:
            if self.status == EvidenceStatus.COMPLETE:
                if self.decoder_contract is None or self.quantization is None:
                    raise ValueError("complete Qwen evidence requires decoder and quantization proof")
                if (
                    self.decoder_contract.do_sample
                    or self.decoder_contract.num_return_sequences != 1
                    or self.decoder_contract.max_new_tokens != 256
                ):
                    raise ValueError("complete Qwen evidence violates the locked decoder controls")
            if self.quantization is not None and (
                self.quantization.requested_mode != self.experiment_identity.adaptation_mode
            ):
                raise ValueError("quantization proof requested mode does not match experiment identity")
        elif self.quantization is not None or self.decoder_contract is not None:
            raise ValueError("PhoBERT evidence cannot contain Qwen quantization/decoder contracts")
        checkpoint_prefix = (
            "adapter-state-sha256:"
            if self.experiment_identity.model_family == ModelFamily.QWEN
            else "model-state-sha256:"
        )
        checkpoint_identities = tuple(
            checkpoint.artifact_identity for checkpoint in self.validation_checkpoints
        ) + (
            (self.selected_checkpoint.artifact_identity,)
            if self.selected_checkpoint is not None
            else ()
        )
        if any(not identity.startswith(checkpoint_prefix) for identity in checkpoint_identities):
            raise ValueError(
                "checkpoint artifact identity prefix differs from the model-family contract"
            )
        if self.status == EvidenceStatus.COMPLETE:
            if self.failure_reason is not None:
                raise ValueError("complete evidence cannot contain a failure_reason")
            if self.run_kind == RunKind.FULL:
                if self.transfer_authority is None:
                    raise ValueError("complete full evidence requires transfer authority")
                required_roles = {
                    "events",
                    "trainer_state",
                    "resolved_config",
                    "predictions",
                    "metrics",
                    "model_artifact",
                    "graph_data",
                    "graph_manifest",
                    "graph_output",
                }
                actual_roles = {artifact.role for artifact in self.artifacts}
                missing = sorted(required_roles - actual_roles)
                if missing:
                    raise ValueError(f"complete full evidence is missing artifact roles: {missing}")
                if (
                    self.experiment_identity.model_family == ModelFamily.PHOBERT
                    and len(role_records.get("preprocessing", [])) != 1
                ):
                    raise ValueError(
                        "complete PhoBERT evidence requires exactly one preprocessing artifact"
                    )
                if not self.validation_metrics or not self.validation_checkpoints:
                    raise ValueError("complete full evidence requires validation metrics/checkpoints")
                if self.selected_checkpoint is None or not self.graph_provenance:
                    raise ValueError("complete full evidence requires selection and graph provenance")
            else:
                if "discard_receipt" not in {artifact.role for artifact in self.artifacts}:
                    raise ValueError("a complete probe requires a discard receipt")
                if self.comparison_eligible:
                    raise ValueError("probe evidence is never comparison eligible")
        else:
            if self.comparison_eligible:
                raise ValueError("incomplete/failed evidence is never comparison eligible")
            if self.status != EvidenceStatus.INCOMPLETE and self.failure_reason is None:
                raise ValueError("failed/interrupted evidence requires a sanitized failure_reason")
        if self.selected_checkpoint is not None:
            candidate_keys = {
                (checkpoint.optimizer_step, checkpoint.artifact_identity)
                for checkpoint in self.validation_checkpoints
            }
            ordered_candidate_keys = tuple(
                (checkpoint.optimizer_step, checkpoint.artifact_identity)
                for checkpoint in self.validation_checkpoints
            )
            if (
                len(candidate_keys) != len(ordered_candidate_keys)
                or ordered_candidate_keys != tuple(sorted(ordered_candidate_keys))
            ):
                raise ValueError("validation checkpoints must be unique and deterministically ordered")
            selected_key = (
                self.selected_checkpoint.optimizer_step,
                self.selected_checkpoint.artifact_identity,
            )
            if selected_key not in candidate_keys:
                raise ValueError("selected checkpoint is absent from validation checkpoints")
        prediction_hashes = {
            artifact.sha256 for artifact in role_records.get("predictions", [])
        }
        metric_hashes = {artifact.sha256 for artifact in role_records.get("metrics", [])}
        for checkpoint in self.validation_checkpoints:
            if checkpoint.predictions_sha256 not in prediction_hashes:
                raise ValueError("checkpoint prediction hash is absent from prediction artifacts")
            if checkpoint.metrics_sha256 not in metric_hashes:
                raise ValueError("checkpoint metric hash is absent from metric artifacts")
        if self.peak_reserved_bytes < self.peak_allocated_bytes:
            raise ValueError("peak reserved bytes cannot be lower than peak allocated bytes")
        artifact_map = {artifact.logical_name: artifact for artifact in self.artifacts}
        graph_ids = tuple(provenance.graph_id for provenance in self.graph_provenance)
        if graph_ids != tuple(sorted(graph_ids)) or len(set(graph_ids)) != len(graph_ids):
            raise ValueError("graph provenance must be unique and sorted by graph_id")
        for provenance in self.graph_provenance:
            required_links = (
                (provenance.event_source_logical_name, provenance.event_source_sha256),
                (provenance.metrics_source_logical_name, provenance.metrics_source_sha256),
                (provenance.model_artifact_logical_name, provenance.model_artifact_sha256),
                (provenance.normalized_data_logical_name, provenance.normalized_data_sha256),
                (provenance.output_logical_name, provenance.output_sha256),
            )
            for logical_name, expected_sha in required_links:
                artifact = artifact_map.get(logical_name)
                if artifact is None or artifact.sha256 != expected_sha:
                    raise ValueError("graph provenance is not bound to evidence artifacts")
        return self


def sanitize_argv(argv: Sequence[str]) -> tuple[str, ...]:
    """Validate an already-structured argv without redaction or silent dropping."""

    sanitized: list[str] = []
    for index, raw in enumerate(argv):
        if not isinstance(raw, str) or not raw:
            raise ValueError(f"argv[{index}] must be a non-empty string")
        option_name, separator, option_value = raw.partition("=")
        if option_name.startswith("-") and _SECRET_OPTION_PATTERN.search(option_name.lstrip("-")):
            raise ValueError(f"argv[{index}] names a secret-bearing option")
        _reject_sensitive_text(
            raw,
            field_name=f"argv[{index}]",
            reject_paths=not _is_allowed_phase40_operator_path(raw),
        )
        if separator:
            _reject_sensitive_text(
                option_value,
                field_name=f"argv[{index}] value",
                reject_paths=not _is_allowed_phase40_operator_path(option_value),
            )
        sanitized.append(raw)
    return tuple(sanitized)


def sanitize_package_versions(package_versions: Mapping[str, str]) -> dict[str, str]:
    """Return exact non-secret package facts in deterministic key order."""

    if not package_versions:
        raise ValueError("package_versions must not be empty")
    sanitized: dict[str, str] = {}
    for name in sorted(package_versions):
        version = package_versions[name]
        if not _CONTROL_NAME_PATTERN.fullmatch(name):
            raise ValueError(f"invalid package name in evidence: {name!r}")
        sanitized[name] = _reject_sensitive_text(
            version,
            field_name=f"package_versions.{name}",
            reject_paths=True,
        )
    return sanitized


def sanitize_environment(environment: Mapping[str, Any]) -> RuntimeHardwareEvidence:
    """Accept only the explicit non-secret hardware/runtime allowlist."""

    unknown = set(environment) - _ALLOWED_ENVIRONMENT_KEYS
    missing = _ALLOWED_ENVIRONMENT_KEYS - set(environment)
    if unknown:
        raise ValueError(f"environment contains non-allowlisted keys: {sorted(unknown)}")
    if missing:
        raise ValueError(f"environment is missing allowlisted facts: {sorted(missing)}")
    return RuntimeHardwareEvidence.model_validate(dict(environment))


def _verify_artifact(run_root: Path, artifact: ArtifactEvidence) -> Path:
    path = _run_relative_path(run_root, artifact.relative_path)
    if artifact.kind == "file":
        if not path.is_file() or path.stat().st_size == 0:
            raise RuntimeError(f"required evidence file is missing or empty: {artifact.logical_name}")
    else:
        if not path.is_dir() or not any(child.is_file() for child in path.rglob("*")):
            raise RuntimeError(f"required evidence directory is missing or empty: {artifact.logical_name}")
        if any(child.is_symlink() for child in path.rglob("*")):
            raise RuntimeError(f"required evidence directory contains a symlink: {artifact.logical_name}")
    actual_sha = build_model_checksum(path)
    if actual_sha != artifact.sha256:
        raise RuntimeError(f"artifact SHA-256 mismatch: {artifact.logical_name}")
    return path


def _validate_required_json(
    path: Path,
    *,
    logical_name: str,
    allow_jsonl: bool = False,
) -> None:
    try:
        text = path.read_text(encoding="utf-8", errors="strict")
        payload = json.loads(text)
    except UnicodeDecodeError as exc:
        raise RuntimeError(f"{logical_name} is not strict UTF-8") from exc
    except json.JSONDecodeError as exc:
        if not allow_jsonl:
            raise RuntimeError(f"{logical_name} is not strict UTF-8 JSON") from exc
        lines = text.splitlines()
        if not lines or any(not line for line in lines):
            raise RuntimeError(f"{logical_name} JSONL contains an empty record") from exc
        try:
            payload = [json.loads(line) for line in lines]
        except json.JSONDecodeError as jsonl_exc:
            raise RuntimeError(f"{logical_name} is not strict UTF-8 JSON/JSONL") from jsonl_exc
    if not isinstance(payload, (dict, list)) or not payload:
        raise RuntimeError(f"{logical_name} JSON payload is empty")
    _validate_json_value(payload, location=logical_name)


def _verify_bundle_records(run_root: Path, evidence: RunEvidence) -> None:
    artifact_paths: dict[str, Path] = {}
    for artifact in evidence.artifacts:
        artifact_paths[artifact.logical_name] = _verify_artifact(run_root, artifact)
    events = [artifact for artifact in evidence.artifacts if artifact.role == "events"]
    if evidence.status == EvidenceStatus.COMPLETE and len(events) != 1:
        raise RuntimeError("complete evidence requires exactly one event log")
    if events:
        loaded_events = load_run_events(
            artifact_paths[events[0].logical_name],
            expected_sha256=events[0].sha256,
            expected_run_id=evidence.run_id,
        )
        if any(event.run_kind != evidence.run_kind for event in loaded_events):
            raise RuntimeError("event run_kind does not match run evidence")
        if evidence.status == EvidenceStatus.COMPLETE and evidence.run_kind == RunKind.FULL:
            _validate_complete_full_lifecycle(loaded_events)
    for artifact in evidence.artifacts:
        if artifact.role in {"trainer_state", "resolved_config", "metrics", "predictions"}:
            if artifact.kind != "file":
                raise RuntimeError(f"{artifact.role} evidence must be a file")
            _validate_required_json(
                artifact_paths[artifact.logical_name],
                logical_name=artifact.logical_name,
                allow_jsonl=artifact.role in {"metrics", "predictions"},
            )
    resolved_config_artifacts = [
        artifact for artifact in evidence.artifacts if artifact.role == "resolved_config"
    ]
    if evidence.status == EvidenceStatus.COMPLETE:
        if len(resolved_config_artifacts) != 1:
            raise RuntimeError("complete evidence requires exactly one resolved config")
        resolved_path = artifact_paths[resolved_config_artifacts[0].logical_name]
        resolved = ResumeControlledConfig.model_validate_json(
            resolved_path.read_text(encoding="utf-8", errors="strict")
        )
        if compute_resume_digest(resolved) != evidence.resume_digest:
            raise RuntimeError("resolved config does not match the resume digest")
        resolved_bindings = (
            (resolved.experiment_identity, evidence.experiment_identity, "experiment identity"),
            (resolved.model_id, evidence.model_id, "model ID"),
            (resolved.model_revision, evidence.model_revision, "model revision"),
            (resolved.splits, evidence.splits, "canonical split identities"),
            (resolved.seed, evidence.seed, "seed"),
            (resolved.data_seed, evidence.data_seed, "data seed"),
            (
                resolved.formatter_or_preprocessor_sha256,
                evidence.prompt_or_preprocessor_sha256,
                "formatter/preprocessor hash",
            ),
            (resolved.decoder, evidence.decoder_contract, "decoder contract"),
            (resolved.quantization_proof, evidence.quantization, "quantization proof"),
        )
        for actual, expected, field_name in resolved_bindings:
            if actual != expected:
                raise RuntimeError(f"resolved config {field_name} does not match run evidence")
    graph_manifests = [
        artifact for artifact in evidence.artifacts if artifact.role == "graph_manifest"
    ]
    if graph_manifests:
        from src.model_adaptation.phase40_graphs import verify_graph_provenance

        verified_graphs = {
            graph.graph_id: graph.as_evidence()
            for graph in (
                verify_graph_provenance(
                    run_root,
                    provenance_relative_path=artifact.relative_path,
                )
                for artifact in graph_manifests
            )
        }
        expected_graphs = {
            provenance.graph_id: provenance for provenance in evidence.graph_provenance
        }
        if verified_graphs != expected_graphs:
            raise RuntimeError("graph manifests do not match run evidence provenance")


def _validate_complete_full_lifecycle(events: tuple[RunEvent, ...]) -> None:
    """Require an observed full lifecycle; hashes alone cannot claim completion."""

    if events[0].event_kind != RunEventKind.RUN_START:
        raise RuntimeError("complete full lifecycle must begin with run_start")
    if events[-1].event_kind != RunEventKind.RUN_END:
        raise RuntimeError("complete full lifecycle must end with run_end")
    last_start_index = max(
        index for index, event in enumerate(events) if event.event_kind == RunEventKind.RUN_START
    )
    if any(
        index > last_start_index and event.event_kind == RunEventKind.FAILURE
        for index, event in enumerate(events)
    ):
        raise RuntimeError("complete full lifecycle final attempt cannot contain a failure event")
    training_indexes = [
        index
        for index, event in enumerate(events)
        if index > last_start_index
        and event.event_kind in {RunEventKind.TRAIN_LOG, RunEventKind.STEP_TIMING}
    ]
    evaluation_indexes = [
        index
        for index, event in enumerate(events)
        if index > last_start_index and event.event_kind == RunEventKind.EVALUATION
    ]
    checkpoint_indexes = [
        index
        for index, event in enumerate(events)
        if index > last_start_index and event.event_kind == RunEventKind.CHECKPOINT
    ]
    if not training_indexes:
        raise RuntimeError("complete full lifecycle requires a step timing/log event")
    if not evaluation_indexes:
        raise RuntimeError("complete full lifecycle requires an evaluation event")
    if not checkpoint_indexes:
        raise RuntimeError("complete full lifecycle requires a checkpoint event")
    if not (
        last_start_index
        < training_indexes[0]
        < evaluation_indexes[-1]
        < checkpoint_indexes[-1]
        < len(events) - 1
    ):
        raise RuntimeError(
            "complete full lifecycle must order training before evaluation, checkpoint, and run_end"
        )


def finalize_run_evidence(
    run_root: Path,
    evidence: RunEvidence | Mapping[str, Any],
    *,
    output_path: Path | None = None,
) -> Path:
    """Verify every retained artifact, atomically write evidence, then verify again."""

    run_root = Path(run_root)
    if not run_root.is_dir() or run_root.is_symlink():
        raise ValueError("run_root must be an existing non-symlink directory")
    evidence_payload = (
        evidence.model_dump(mode="json")
        if isinstance(evidence, RunEvidence)
        else _validate_json_value(dict(evidence), location="run evidence")
    )
    validated = RunEvidence.model_validate_json(_canonical_json_bytes(evidence_payload))
    if validated.status != EvidenceStatus.COMPLETE:
        raise ValueError("only complete evidence can be finalized")
    _verify_bundle_records(run_root, validated)
    if output_path is None:
        destination = run_root / "run-evidence.json"
    else:
        destination = Path(output_path)
        if not destination.is_absolute():
            destination = run_root / destination
    absolute_root = Path(os.path.abspath(os.path.normpath(os.fspath(run_root))))
    absolute_destination = Path(os.path.abspath(os.path.normpath(os.fspath(destination))))
    try:
        absolute_destination.relative_to(absolute_root)
    except ValueError as exc:
        raise ValueError("run evidence output must stay inside run_root") from exc
    serialized = validated.model_dump(mode="json")
    if serialized.get("git_commit") is None:
        serialized.pop("git_commit", None)
    payload = _canonical_json_bytes(serialized) + b"\n"
    _atomic_write_bytes(absolute_destination, payload)
    read_back = RunEvidence.model_validate_json(absolute_destination.read_text(encoding="utf-8"))
    if read_back != validated:
        raise RuntimeError("run evidence semantic read-back mismatch")
    verify_phase40_bundle(run_root, evidence_path=absolute_destination)
    return absolute_destination


def verify_phase40_bundle(
    run_root: Path,
    *,
    evidence_path: Path | None = None,
    allow_prestart_failure: bool = False,
) -> RunEvidence:
    """Rehash and schema-verify one immutable train/validation-only run bundle."""

    if not isinstance(allow_prestart_failure, bool):
        raise TypeError("allow_prestart_failure must be a boolean")
    run_root = Path(run_root)
    if not run_root.is_dir() or run_root.is_symlink():
        raise ValueError("run_root must be an existing non-symlink directory")
    if evidence_path is None:
        path = run_root / "run-evidence.json"
    else:
        path = Path(evidence_path)
        if not path.is_absolute():
            path = run_root / path
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError("run-evidence.json is missing or empty")
    absolute_root = Path(os.path.abspath(os.path.normpath(os.fspath(run_root))))
    absolute_path = Path(os.path.abspath(os.path.normpath(os.fspath(path))))
    try:
        absolute_path.relative_to(absolute_root)
    except ValueError as exc:
        raise ValueError("evidence_path must stay inside run_root") from exc
    if path.is_symlink():
        raise ValueError("evidence_path must not be a symlink")
    evidence = RunEvidence.model_validate_json(path.read_text(encoding="utf-8", errors="strict"))
    allowed_status = evidence.status == EvidenceStatus.COMPLETE or (
        allow_prestart_failure and evidence.status == EvidenceStatus.PRESTART_FAILED
    )
    if not allowed_status:
        raise RuntimeError("Phase 40 bundle is not complete")
    _verify_bundle_records(run_root, evidence)
    return evidence


class AcceleratorIdentity(_StrictModel):
    accelerator_type: str
    accelerator_name: str
    compute_capability: str | None
    total_memory_bytes: int = Field(ge=0)

    @field_validator("accelerator_type", "accelerator_name", "compute_capability")
    @classmethod
    def validate_fact(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _reject_sensitive_text(value, field_name="accelerator identity", reject_paths=True)


class PrecisionControls(_StrictModel):
    compute_dtype: str
    adapter_dtype: str
    bf16: bool
    fp16: bool
    tf32: bool


class OptimizerControls(_StrictModel):
    optimizer: str
    learning_rate: float = Field(gt=0)
    weight_decay: float = Field(ge=0)
    lr_scheduler_type: str
    warmup_steps: int = Field(ge=0)
    warmup_ratio: float = Field(ge=0, le=1)
    max_grad_norm: float = Field(gt=0)


class CadenceControls(_StrictModel):
    logging_steps: int = Field(gt=0)
    evaluation_steps: int = Field(gt=0)
    save_steps: int = Field(gt=0)
    save_total_limit: int = Field(gt=0)
    generation_steps: tuple[int, ...] = Field(min_length=1)

    @field_validator("generation_steps")
    @classmethod
    def validate_generation_steps(cls, value: tuple[int, ...]) -> tuple[int, ...]:
        if any(step < 0 for step in value) or any(right <= left for left, right in zip(value, value[1:])):
            raise ValueError("generation_steps must be strictly increasing non-negative steps")
        return value


class NamedControl(_StrictModel):
    name: str
    value: Any

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not _CONTROL_NAME_PATTERN.fullmatch(value):
            raise ValueError("additional control name is invalid")
        return value

    @field_validator("value")
    @classmethod
    def validate_value(cls, value: Any) -> Any:
        return _validate_json_value(value, location="additional control")


class ResumeControlledConfig(_StrictModel):
    """The complete exact-equality contract used for restart and Qwen matching."""

    schema_version: Literal["phase40-resume-controlled-config-v1"]
    experiment_identity: ExperimentIdentityEvidence
    model_id: str
    model_revision: GitCommit
    splits: tuple[CanonicalSplitEvidence, CanonicalSplitEvidence]
    formatter_or_preprocessor_sha256: Sha256
    response_mask_or_preprocessor_version: str
    label_order: tuple[str, ...]
    seed: int
    data_seed: int
    max_sequence_length: int = Field(gt=0)
    truncation_policy: str
    per_device_train_batch_size: int = Field(gt=0)
    gradient_accumulation_steps: int = Field(gt=0)
    world_size: int = Field(gt=0)
    effective_batch_size: int = Field(gt=0)
    num_train_epochs: float = Field(gt=0)
    max_optimizer_steps: int = Field(gt=0)
    gradient_checkpointing: bool
    lora_rank: int | None = Field(default=None, gt=0)
    lora_alpha: int | None = Field(default=None, gt=0)
    lora_dropout: float | None = Field(default=None, ge=0, lt=1)
    lora_bias: str | None
    target_modules: tuple[str, ...]
    task_type: str
    optimizer: OptimizerControls
    precision: PrecisionControls
    cadence: CadenceControls
    decoder: DecoderContractEvidence | None
    checkpoint_selection_policy: str
    checkpoint_selection_policy_version: str
    snapshot_id_algorithm_version: str
    quantization_proof: QuantizationProofEvidence | None
    accelerator: AcceleratorIdentity
    additional_controls: tuple[NamedControl, ...]

    @field_validator("model_id")
    @classmethod
    def validate_model_identifier(cls, value: str) -> str:
        return _require_model_identifier(value)

    @field_validator(
        "response_mask_or_preprocessor_version",
        "truncation_policy",
        "task_type",
        "checkpoint_selection_policy",
        "checkpoint_selection_policy_version",
        "snapshot_id_algorithm_version",
    )
    @classmethod
    def validate_control_text(cls, value: str) -> str:
        return _require_safe_identifier(value, field_name="resume control")

    @field_validator("label_order")
    @classmethod
    def validate_label_order(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if value != tuple(LOCKED_RELEASE_LABELS):
            raise ValueError("label_order must preserve the locked four-class order")
        return value

    @field_validator("target_modules")
    @classmethod
    def validate_target_modules(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(set(value)) != len(value) or any(not _CONTROL_NAME_PATTERN.fullmatch(item) for item in value):
            raise ValueError("target_modules must be unique ordered control names")
        return value

    @field_validator("additional_controls")
    @classmethod
    def validate_additional_controls(cls, value: tuple[NamedControl, ...]) -> tuple[NamedControl, ...]:
        names = [control.name for control in value]
        if len(names) != len(set(names)):
            raise ValueError("additional control names must be unique")
        return value

    @model_validator(mode="after")
    def validate_control_contract(self) -> "ResumeControlledConfig":
        if self.experiment_identity.run_kind != RunKind.FULL:
            raise ValueError("resume-controlled configs must describe full runs")
        if tuple(split.logical_name for split in self.splits) != ("train", "val"):
            raise ValueError("resume controls require train then val split identities")
        expected_effective_batch = (
            self.per_device_train_batch_size * self.gradient_accumulation_steps * self.world_size
        )
        if self.effective_batch_size != expected_effective_batch:
            raise ValueError("effective_batch_size does not match batch/accumulation/world size")
        if self.experiment_identity.model_family == ModelFamily.QWEN:
            required_adapter_fields = (
                self.lora_rank,
                self.lora_alpha,
                self.lora_dropout,
                self.lora_bias,
            )
            if any(value is None for value in required_adapter_fields) or not self.target_modules:
                raise ValueError("Qwen controls require complete LoRA adapter settings")
            if self.decoder is None or self.quantization_proof is None:
                raise ValueError("Qwen controls require decoder and quantization proof")
            if self.quantization_proof.requested_mode != self.experiment_identity.adaptation_mode:
                raise ValueError("Qwen quantization proof does not match experiment identity")
        else:
            if self.decoder is not None or self.quantization_proof is not None:
                raise ValueError("PhoBERT controls cannot contain Qwen decoder/quantization proof")
            if any(
                value is not None
                for value in (
                    self.lora_rank,
                    self.lora_alpha,
                    self.lora_dropout,
                    self.lora_bias,
                )
            ) or self.target_modules:
                raise ValueError("PhoBERT controls cannot contain LoRA adapter settings")
            if self.task_type != "sequence-classification":
                raise ValueError("PhoBERT task_type must be sequence-classification")
        return self


class ConfigDifference(_StrictModel):
    path: str
    left: Any
    right: Any

    @field_validator("left", "right")
    @classmethod
    def validate_json_values(cls, value: Any) -> Any:
        return _validate_json_value(value, location="config difference")


class QwenConfigComparison(_StrictModel):
    schema_version: Literal["phase40-qwen-config-comparison-v1"]
    admissible: bool
    hardware_confounded: bool
    speed_comparison_admissible: bool
    left_resume_digest: Sha256
    right_resume_digest: Sha256
    forbidden_differences: tuple[ConfigDifference, ...]
    allowed_quantization_differences: tuple[ConfigDifference, ...]
    hardware_differences: tuple[ConfigDifference, ...]


_ALLOWED_QWEN_QUANTIZATION_PATHS = frozenset(
    {
        "experiment_identity.adaptation_mode",
        "quantization_proof.requested_mode",
        "quantization_proof.resolved_mode",
        "quantization_proof.bitsandbytes_version",
        "quantization_proof.load_in_4bit",
        "quantization_proof.nf4",
        "quantization_proof.double_quantization",
        "quantization_proof.is_loaded_in_4bit",
        "quantization_proof.linear4bit_modules",
        "quantization_proof.kbit_preparation_applied",
        "quantization_proof.backward_with_adapter_gradients",
        "quantization_proof.adapter_gradient_finite_count",
        "quantization_proof.adapter_gradient_nonzero_count",
    }
)


def _coerce_resume_config(
    config: ResumeControlledConfig | Mapping[str, Any],
) -> ResumeControlledConfig:
    payload = (
        config.model_dump(mode="json")
        if isinstance(config, ResumeControlledConfig)
        else _validate_json_value(dict(config), location="resume config")
    )
    return ResumeControlledConfig.model_validate_json(_canonical_json_bytes(payload))


def compute_resume_digest(config: ResumeControlledConfig | Mapping[str, Any]) -> str:
    """Hash every restart-controlled field with no tolerance or omitted keys."""

    validated = _coerce_resume_config(config)
    return _domain_sha256(
        "phase40-resume-controlled-config-v1",
        validated.model_dump(mode="json"),
    )


def _json_differences(left: Any, right: Any, *, path: str = "") -> list[ConfigDifference]:
    if type(left) is not type(right):
        return [ConfigDifference(path=path or "$", left=left, right=right)]
    if isinstance(left, dict):
        differences: list[ConfigDifference] = []
        for key in sorted(set(left) | set(right)):
            child_path = f"{path}.{key}" if path else key
            if key not in left:
                differences.append(ConfigDifference(path=child_path, left=None, right=right[key]))
            elif key not in right:
                differences.append(ConfigDifference(path=child_path, left=left[key], right=None))
            else:
                differences.extend(_json_differences(left[key], right[key], path=child_path))
        return differences
    if isinstance(left, list):
        if left == right:
            return []
        return [ConfigDifference(path=path or "$", left=left, right=right)]
    if left != right:
        return [ConfigDifference(path=path or "$", left=left, right=right)]
    return []


def compare_qwen_configs(
    left: ResumeControlledConfig | Mapping[str, Any],
    right: ResumeControlledConfig | Mapping[str, Any],
) -> QwenConfigComparison:
    """Compare Qwen controls exactly, allowing only quantization and hardware facts."""

    left_config = _coerce_resume_config(left)
    right_config = _coerce_resume_config(right)
    if (
        left_config.experiment_identity.model_family != ModelFamily.QWEN
        or right_config.experiment_identity.model_family != ModelFamily.QWEN
    ):
        raise ValueError("compare_qwen_configs accepts Qwen configs only")
    left_payload = left_config.model_dump(mode="json")
    right_payload = right_config.model_dump(mode="json")
    differences = _json_differences(left_payload, right_payload)
    allowed_quantization: list[ConfigDifference] = []
    hardware: list[ConfigDifference] = []
    forbidden: list[ConfigDifference] = []
    modes = {
        left_config.experiment_identity.adaptation_mode,
        right_config.experiment_identity.adaptation_mode,
    }
    is_matched_mode_pair = modes == {AdaptationMode.LORA, AdaptationMode.QLORA}
    for difference in differences:
        if difference.path.startswith("accelerator."):
            hardware.append(difference)
        elif difference.path in _ALLOWED_QWEN_QUANTIZATION_PATHS and is_matched_mode_pair:
            allowed_quantization.append(difference)
        else:
            forbidden.append(difference)
    hardware_confounded = bool(hardware)
    admissible = not forbidden
    return QwenConfigComparison(
        schema_version="phase40-qwen-config-comparison-v1",
        admissible=admissible,
        hardware_confounded=hardware_confounded,
        speed_comparison_admissible=admissible and not hardware_confounded,
        left_resume_digest=compute_resume_digest(left_config),
        right_resume_digest=compute_resume_digest(right_config),
        forbidden_differences=tuple(forbidden),
        allowed_quantization_differences=tuple(allowed_quantization),
        hardware_differences=tuple(hardware),
    )


__all__ = [
    "AcceleratorIdentity",
    "ArtifactEvidence",
    "CadenceControls",
    "CanonicalSplitEvidence",
    "ConfigDifference",
    "DecoderContractEvidence",
    "EvidenceStatus",
    "ExperimentIdentityEvidence",
    "GraphProvenanceEvidence",
    "NamedControl",
    "OptimizerControls",
    "PrecisionControls",
    "QuantizationProofEvidence",
    "QwenConfigComparison",
    "ResumeControlledConfig",
    "RunEvent",
    "RunEventKind",
    "RunEvidence",
    "RuntimeHardwareEvidence",
    "SelectedCheckpointEvidence",
    "TransferAuthorityEvidence",
    "ValidationCheckpointEvidence",
    "append_run_event",
    "compare_qwen_configs",
    "compute_resume_digest",
    "finalize_run_evidence",
    "load_run_events",
    "sanitize_argv",
    "sanitize_environment",
    "sanitize_package_versions",
    "verify_phase40_bundle",
]
