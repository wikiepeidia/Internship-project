"""Training orchestration for Phase 3 adapter builds."""

from __future__ import annotations

import importlib
import inspect
import hashlib
import json
import math
import os
import platform
import re
import shutil
import tempfile
import time
from contextlib import nullcontext
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from pathlib import PurePosixPath
from typing import Any, Callable, Mapping, Sequence

from src.config.settings import get_settings
from src.model_adaptation.catalog import build_default_catalog, get_candidate_by_id
from src.model_adaptation.data import build_training_examples
from src.model_adaptation.phase40_contract import (
    CanonicalSplitSnapshot,
    Phase40DataContract,
)
from src.model_adaptation.phase40_callbacks import (
    CallbackEventKind,
    Phase40CallbackEvent,
    Phase40EvidenceCallback,
    ProbeExecutionContract,
    TorchCudaTimingAdapter,
    discard_probe_artifact,
    require_completed_probe,
    require_registry_publication_allowed,
    verify_probe_discard_receipt,
    write_probe_discard_receipt,
)
from src.model_adaptation.phase40_evidence import (
    AcceleratorIdentity,
    ArtifactEvidence,
    CadenceControls,
    CanonicalSplitEvidence,
    DecoderContractEvidence,
    EvidenceStatus,
    ExperimentIdentityEvidence,
    NamedControl,
    OptimizerControls,
    PrecisionControls,
    QuantizationProofEvidence,
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
    verify_phase40_bundle,
)
from src.model_adaptation.phase40_graphs import render_phase40_graphs
from src.model_adaptation.phase40_handoff import (
    RequestedControlTemplate,
    RunRequest,
    transfer_authority_from_request,
)
from src.model_adaptation.phase40_metrics import (
    CheckpointSelection,
    LABEL_ORDER,
    Phase40MetricResult,
    Phase40PredictionRow,
    evaluate_phase40_predictions,
    select_phase40_checkpoint,
    validate_phase40_prediction_rows,
)
from src.model_adaptation.phase40_modes import (
    AdaptationMode,
    AdapterGradientCheck,
    ExperimentIdentity,
    ModelFamily,
    QuantizationProof,
    QwenPreloadCapabilities,
    ResolvedQwenMode,
    RunKind,
    prove_qwen_mode,
    prove_qwen_preload,
)
from src.model_adaptation.registry import build_model_checksum, load_model_registry, save_model_registry
from src.model_adaptation.schemas import ModelArtifactRecord, ModelRegistry, PilotSelection


DEFAULT_TARGET_MODULES: tuple[str, ...] = (
    "q_proj",
    "k_proj",
    "v_proj",
    "o_proj",
    "gate_proj",
    "up_proj",
    "down_proj",
)
SMOKE_TEST_MAX_STEPS = 2
PHASE40_FORMATTER_VERSION = "phase40-qwen-chat-v1"
PHASE40_RESPONSE_MASK_VERSION = "phase40-response-only-mask-v1"
_RAW_MESSAGE_OPEN = "<UNTRUSTED_RAW_MESSAGE_JSON>"
_RAW_MESSAGE_CLOSE = "</UNTRUSTED_RAW_MESSAGE_JSON>"
_ADAPTER_CONFIG_NAME = "adapter_config.json"
_ADAPTER_WEIGHT_NAMES = ("adapter_model.safetensors", "adapter_model.bin")
PHASE40_QWEN_REVISION = "cdbee75f17c01a7cc42f958dc650907174af0554"
PHASE40_QWEN_MODEL_ID = "Qwen/Qwen3-4B-Instruct-2507"
PHASE40_BASE_MODEL_MANIFEST_NAME = "phase40-base-model-provenance.json"
PHASE40_BASE_MODEL_MANIFEST_SCHEMA_VERSION = "phase40-qwen-base-model-snapshot-v1"
PHASE40_RESUME_MANIFEST_NAME = "phase40-resume-manifest.json"
PHASE40_RESUME_HISTORY_NAME = "phase40-resume-history.json"
PHASE40_RESUME_HISTORY_SCHEMA_VERSION = "phase40-qwen-resume-history-v1"
PHASE40_RESUME_MANIFEST_SCHEMA_VERSION = "phase40-checkpoint-resume-v2"
PHASE40_SNAPSHOT_ID_ALGORITHM_VERSION = "phase40-snapshot-row-id-v1"
PHASE40_CHECKPOINT_SELECTION_POLICY = "macro-f1-safety-gate"
PHASE40_CHECKPOINT_SELECTION_POLICY_VERSION = "phase40-checkpoint-selection-v1"
PHASE40_DECODER_OUTPUT_SCHEMA_VERSION = "phase40-prediction-row-v1"
PHASE40_DECODER_VERSION = "phase40-qwen-greedy-v1"
PHASE40_GENERATION_CADENCE = "every-validation-checkpoint-and-final"
PHASE40_PREDICTION_ORDERING_POLICY = "canonical-validation-sequence"
_RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def _normalized_absolute_path(path: Path) -> Path:
    return Path(os.path.abspath(os.path.normpath(os.fspath(path))))


def _reject_existing_symlink_traversal(path: Path, *, description: str) -> None:
    current = Path(path)
    while True:
        if current.exists() and current.is_symlink():
            raise ValueError(f"{description} must not traverse symlinks")
        if current.parent == current:
            break
        current = current.parent


@dataclass(frozen=True, slots=True)
class QwenBaseModelFileIdentity:
    """One regular file in a pinned local Qwen snapshot."""

    relative_path: str
    bytes: int
    sha256: str

    def __post_init__(self) -> None:
        path = PurePosixPath(self.relative_path)
        if (
            not self.relative_path
            or path.is_absolute()
            or ".." in path.parts
            or self.relative_path != path.as_posix()
        ):
            raise ValueError("base-model file identity must be a normalized relative path")
        if not isinstance(self.bytes, int) or isinstance(self.bytes, bool) or self.bytes < 0:
            raise ValueError("base-model file size must be a non-negative integer")
        if not re.fullmatch(r"[0-9a-f]{64}", self.sha256):
            raise ValueError("base-model file identity requires a lowercase SHA-256")


@dataclass(frozen=True, slots=True)
class QwenBaseModelSnapshot:
    """Validated local bytes for the exact Phase 40 Qwen model revision."""

    model_id: str
    model_revision: str
    local_snapshot_path: Path
    manifest_path: Path
    files: tuple[QwenBaseModelFileIdentity, ...]
    snapshot_content_sha256: str
    manifest_sha256: str

    def __post_init__(self) -> None:
        if self.model_id != PHASE40_QWEN_MODEL_ID:
            raise ValueError("Phase 40 Qwen snapshot has the wrong exact model_id")
        if self.model_revision != PHASE40_QWEN_REVISION:
            raise ValueError("Phase 40 Qwen snapshot has the wrong pinned revision")
        if self.local_snapshot_path != _normalized_absolute_path(self.local_snapshot_path):
            raise ValueError("Phase 40 Qwen snapshot path must be normalized and absolute")
        if self.manifest_path != _normalized_absolute_path(self.manifest_path):
            raise ValueError(
                "Phase 40 Qwen provenance manifest path must be normalized and absolute"
            )
        if not self.files or tuple(item.relative_path for item in self.files) != tuple(
            sorted(item.relative_path for item in self.files)
        ):
            raise ValueError("base-model snapshot inventory must be non-empty and sorted")
        if len({item.relative_path for item in self.files}) != len(self.files):
            raise ValueError("base-model snapshot inventory paths must be unique")
        for digest in (self.snapshot_content_sha256, self.manifest_sha256):
            if not re.fullmatch(r"[0-9a-f]{64}", digest):
                raise ValueError("base-model snapshot hashes must be lowercase SHA-256")

    def portable_manifest(self) -> dict[str, Any]:
        """Return path-free provenance safe to retain in transferred evidence."""

        return {
            "schema_version": PHASE40_BASE_MODEL_MANIFEST_SCHEMA_VERSION,
            "model_id": self.model_id,
            "model_revision": self.model_revision,
            "snapshot_content_sha256": self.snapshot_content_sha256,
            "files": [asdict(item) for item in self.files],
        }

    def evidence_payload(self) -> dict[str, Any]:
        payload = self.portable_manifest()
        payload["manifest_sha256"] = self.manifest_sha256
        return payload

    def model_dump(self, *, mode: str = "json") -> dict[str, Any]:
        """Pydantic-compatible portable serialization for operator integration."""

        if mode != "json":
            raise ValueError("Qwen base-model provenance supports only mode='json'")
        return self.portable_manifest()


@dataclass(frozen=True, slots=True)
class QwenBaseModelAcquisitionRequest:
    """Network-free specification an operator may pass to snapshot_download later."""

    model_id: str
    model_revision: str
    local_snapshot_path: Path

    def __post_init__(self) -> None:
        if self.model_id != PHASE40_QWEN_MODEL_ID:
            raise ValueError("Qwen acquisition is locked to the Phase 40 model_id")
        if self.model_revision != PHASE40_QWEN_REVISION:
            raise ValueError("Qwen acquisition is locked to the Phase 40 revision")
        if self.local_snapshot_path != _normalized_absolute_path(self.local_snapshot_path):
            raise ValueError("Qwen acquisition destination must be normalized and absolute")
        _reject_existing_symlink_traversal(
            self.local_snapshot_path,
            description="Qwen acquisition destination",
        )

    def snapshot_download_kwargs(self) -> dict[str, Any]:
        """Return explicit kwargs without importing or calling Hugging Face."""

        return {
            "repo_id": self.model_id,
            "revision": self.model_revision,
            "local_dir": str(self.local_snapshot_path),
        }


def build_qwen_base_model_acquisition_request(
    local_snapshot_path: Path,
    *,
    model_id: str = PHASE40_QWEN_MODEL_ID,
    model_revision: str = PHASE40_QWEN_REVISION,
) -> QwenBaseModelAcquisitionRequest:
    """Describe, but never perform, acquisition of the one pinned Qwen snapshot."""

    return QwenBaseModelAcquisitionRequest(
        model_id=model_id,
        model_revision=model_revision,
        local_snapshot_path=Path(local_snapshot_path),
    )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _inventory_qwen_base_model_snapshot(snapshot_path: Path) -> tuple[QwenBaseModelFileIdentity, ...]:
    root = Path(snapshot_path)
    if not root.is_absolute() or not root.is_dir() or root.is_symlink():
        raise ValueError("Qwen base-model snapshot must be an absolute non-symlink directory")
    _reject_existing_symlink_traversal(root, description="Qwen base-model snapshot")
    files: list[QwenBaseModelFileIdentity] = []
    for path in root.rglob("*"):
        if path.is_symlink():
            raise ValueError("Qwen base-model snapshot must not contain symlinks")
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if relative == PHASE40_BASE_MODEL_MANIFEST_NAME:
            continue
        files.append(
            QwenBaseModelFileIdentity(
                relative_path=relative,
                bytes=path.stat().st_size,
                sha256=_sha256_file(path),
            )
        )
    inventory = tuple(sorted(files, key=lambda item: item.relative_path))
    names = {item.relative_path for item in inventory}
    if not {"config.json", "tokenizer_config.json"}.issubset(names):
        raise RuntimeError("Qwen snapshot is missing config.json or tokenizer_config.json")
    if not any(name.endswith((".safetensors", ".bin")) for name in names):
        raise RuntimeError("Qwen snapshot is missing model weight bytes")
    return inventory


def _snapshot_content_sha256(files: Sequence[QwenBaseModelFileIdentity]) -> str:
    digest = hashlib.sha256(b"phase40-qwen-base-model-snapshot-v1\0")
    for item in files:
        path_bytes = item.relative_path.encode("utf-8")
        digest.update(len(path_bytes).to_bytes(8, "big"))
        digest.update(path_bytes)
        digest.update(item.bytes.to_bytes(8, "big"))
        digest.update(bytes.fromhex(item.sha256))
    return digest.hexdigest()


def seal_qwen_base_model_snapshot(
    snapshot_path: Path,
    *,
    model_id: str = PHASE40_QWEN_MODEL_ID,
    model_revision: str = PHASE40_QWEN_REVISION,
    manifest_path: Path | None = None,
) -> QwenBaseModelSnapshot:
    """Create the deterministic provenance manifest after an operator acquires bytes."""

    request = build_qwen_base_model_acquisition_request(
        Path(snapshot_path),
        model_id=model_id,
        model_revision=model_revision,
    )
    provenance = build_qwen_base_model_provenance(
        request.local_snapshot_path,
        model_id=request.model_id,
        model_revision=request.model_revision,
        manifest_path=manifest_path,
    )
    manifest_bytes = _canonical_json_line(provenance.portable_manifest())
    _write_immutable_bytes(provenance.manifest_path, manifest_bytes)
    return provenance


def _resolved_qwen_manifest_path(snapshot_path: Path, manifest_path: Path | None) -> Path:
    snapshot = Path(snapshot_path)
    resolved = (
        snapshot / PHASE40_BASE_MODEL_MANIFEST_NAME
        if manifest_path is None
        else Path(manifest_path)
    )
    if not resolved.is_absolute():
        raise ValueError("Qwen base-model provenance manifest path must be absolute")
    normalized = _normalized_absolute_path(resolved)
    snapshot_normalized = snapshot.resolve(strict=True)
    if normalized == snapshot_normalized or normalized in snapshot_normalized.parents:
        raise ValueError("Qwen base-model provenance manifest path is unsafe")
    if normalized.is_relative_to(snapshot_normalized) and normalized != (
        snapshot_normalized / PHASE40_BASE_MODEL_MANIFEST_NAME
    ):
        raise ValueError("an in-snapshot Qwen manifest must use the fixed canonical filename")
    _reject_existing_symlink_traversal(
        normalized,
        description="Qwen base-model provenance manifest",
    )
    return normalized


def build_qwen_base_model_provenance(
    base_model_path: Path,
    *,
    model_id: str = PHASE40_QWEN_MODEL_ID,
    model_revision: str = PHASE40_QWEN_REVISION,
    manifest_path: Path | None = None,
) -> QwenBaseModelSnapshot:
    """Hash a local snapshot and build typed provenance without writing or networking."""

    request = build_qwen_base_model_acquisition_request(
        Path(base_model_path),
        model_id=model_id,
        model_revision=model_revision,
    )
    resolved_manifest_path = _resolved_qwen_manifest_path(
        request.local_snapshot_path,
        manifest_path,
    )
    files = _inventory_qwen_base_model_snapshot(request.local_snapshot_path)
    portable = {
        "schema_version": PHASE40_BASE_MODEL_MANIFEST_SCHEMA_VERSION,
        "model_id": request.model_id,
        "model_revision": request.model_revision,
        "snapshot_content_sha256": _snapshot_content_sha256(files),
        "files": [asdict(item) for item in files],
    }
    manifest_bytes = _canonical_json_line(portable)
    return QwenBaseModelSnapshot(
        model_id=request.model_id,
        model_revision=request.model_revision,
        local_snapshot_path=request.local_snapshot_path,
        manifest_path=resolved_manifest_path,
        files=files,
        snapshot_content_sha256=portable["snapshot_content_sha256"],
        manifest_sha256=hashlib.sha256(manifest_bytes).hexdigest(),
    )


def validate_qwen_base_model_snapshot(
    snapshot_path: Path,
    *,
    expected_model_id: str = PHASE40_QWEN_MODEL_ID,
    expected_model_revision: str = PHASE40_QWEN_REVISION,
    manifest_path: Path | None = None,
) -> QwenBaseModelSnapshot:
    """Fail closed if a pinned local snapshot or its manifest has drifted."""

    request = build_qwen_base_model_acquisition_request(
        Path(snapshot_path),
        model_id=expected_model_id,
        model_revision=expected_model_revision,
    )
    resolved_manifest_path = _resolved_qwen_manifest_path(
        request.local_snapshot_path,
        manifest_path,
    )
    if not resolved_manifest_path.is_file() or resolved_manifest_path.is_symlink():
        raise RuntimeError("Qwen snapshot lacks its trusted provenance manifest")
    manifest_bytes = resolved_manifest_path.read_bytes()
    try:
        payload = json.loads(manifest_bytes.decode("utf-8", errors="strict"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("Qwen snapshot provenance is not strict UTF-8 JSON") from exc
    expected_keys = {
        "schema_version",
        "model_id",
        "model_revision",
        "snapshot_content_sha256",
        "files",
    }
    if not isinstance(payload, dict) or set(payload) != expected_keys:
        raise RuntimeError("Qwen snapshot provenance has missing or extra fields")
    if payload["schema_version"] != PHASE40_BASE_MODEL_MANIFEST_SCHEMA_VERSION:
        raise RuntimeError("Qwen snapshot provenance schema version is unsupported")
    if payload["model_id"] != request.model_id or payload["model_revision"] != request.model_revision:
        raise RuntimeError("Qwen snapshot provenance model identity/revision drifted")
    try:
        recorded_files = tuple(QwenBaseModelFileIdentity(**item) for item in payload["files"])
    except (TypeError, ValueError) as exc:
        raise RuntimeError("Qwen snapshot provenance inventory is invalid") from exc
    actual_files = _inventory_qwen_base_model_snapshot(request.local_snapshot_path)
    if recorded_files != actual_files:
        raise RuntimeError("Qwen snapshot inventory or file hashes drifted")
    content_sha256 = _snapshot_content_sha256(actual_files)
    if payload["snapshot_content_sha256"] != content_sha256:
        raise RuntimeError("Qwen snapshot content hash drifted")
    canonical_manifest = _canonical_json_line(payload)
    if manifest_bytes != canonical_manifest:
        raise RuntimeError("Qwen snapshot provenance manifest is not canonical")
    return QwenBaseModelSnapshot(
        model_id=request.model_id,
        model_revision=request.model_revision,
        local_snapshot_path=request.local_snapshot_path,
        manifest_path=resolved_manifest_path,
        files=actual_files,
        snapshot_content_sha256=content_sha256,
        manifest_sha256=hashlib.sha256(manifest_bytes).hexdigest(),
    )


def verify_qwen_base_model_provenance(
    base_model_path: Path,
    manifest_path: Path,
    *,
    model_id: str = PHASE40_QWEN_MODEL_ID,
    model_revision: str = PHASE40_QWEN_REVISION,
) -> QwenBaseModelSnapshot:
    """Operator-facing alias for exact snapshot plus explicit-manifest validation."""

    return validate_qwen_base_model_snapshot(
        base_model_path,
        expected_model_id=model_id,
        expected_model_revision=model_revision,
        manifest_path=manifest_path,
    )


def _validate_qwen_base_model_evidence_payload(payload: object) -> dict[str, Any]:
    expected_keys = {
        "schema_version",
        "model_id",
        "model_revision",
        "snapshot_content_sha256",
        "files",
        "manifest_sha256",
    }
    if not isinstance(payload, dict) or set(payload) != expected_keys:
        raise RuntimeError("checkpoint base-model source provenance has missing or extra fields")
    if payload["schema_version"] != PHASE40_BASE_MODEL_MANIFEST_SCHEMA_VERSION:
        raise RuntimeError("checkpoint base-model source provenance schema is unsupported")
    if payload["model_id"] != PHASE40_QWEN_MODEL_ID:
        raise RuntimeError("checkpoint base-model source has the wrong exact model_id")
    if payload["model_revision"] != PHASE40_QWEN_REVISION:
        raise RuntimeError("checkpoint base-model source has the wrong pinned revision")
    try:
        files = tuple(QwenBaseModelFileIdentity(**item) for item in payload["files"])
    except (TypeError, ValueError) as exc:
        raise RuntimeError("checkpoint base-model source inventory is invalid") from exc
    if not files or tuple(item.relative_path for item in files) != tuple(
        sorted(item.relative_path for item in files)
    ):
        raise RuntimeError("checkpoint base-model source inventory is not canonical")
    if payload["snapshot_content_sha256"] != _snapshot_content_sha256(files):
        raise RuntimeError("checkpoint base-model source content hash is inconsistent")
    portable = {key: payload[key] for key in expected_keys if key != "manifest_sha256"}
    if payload["manifest_sha256"] != hashlib.sha256(_canonical_json_line(portable)).hexdigest():
        raise RuntimeError("checkpoint base-model source manifest hash is inconsistent")
    return payload


@dataclass(frozen=True, slots=True)
class ResponseOnlyTokenizedExample:
    """One Qwen example whose loss labels cover only the assistant answer."""

    input_ids: tuple[int, ...]
    attention_mask: tuple[int, ...]
    labels: tuple[int, ...]
    raw_message: str
    formatter_version: str
    formatter_sha256: str

    def as_item(self) -> dict[str, list[int]]:
        return {
            "input_ids": list(self.input_ids),
            "attention_mask": list(self.attention_mask),
            "labels": list(self.labels),
        }


def build_phase40_chat_messages(example: dict[str, Any]) -> tuple[dict[str, str], ...]:
    """Separate existing instructions, untrusted raw text, and assistant JSON."""

    prompt = str(example["prompt"])
    raw_message = str(example["text"])
    suffix = f"Message text: {raw_message}"
    if not prompt.endswith(suffix):
        raise ValueError("legacy Qwen prompt does not end at the exact raw-message boundary")
    system_instruction = prompt[: -len(suffix)].rstrip("\n")
    if not system_instruction:
        raise ValueError("Qwen system instruction must not be empty")
    user_payload = json.dumps(
        {"raw_message": raw_message},
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return (
        {"role": "system", "content": system_instruction},
        {
            "role": "user",
            "content": f"{_RAW_MESSAGE_OPEN}\n{user_payload}\n{_RAW_MESSAGE_CLOSE}",
        },
        {"role": "assistant", "content": str(example["response"])},
    )


def _token_id_list(value: Any) -> list[int]:
    if hasattr(value, "tolist"):
        value = value.tolist()
    if isinstance(value, tuple):
        value = list(value)
    if isinstance(value, list) and len(value) == 1 and isinstance(value[0], list):
        value = value[0]
    if not isinstance(value, list) or any(isinstance(item, bool) or not isinstance(item, int) for item in value):
        raise ValueError("chat template must return one integer token sequence")
    return value


def _formatter_sha256(
    tokenizer: Any,
    *,
    system_instruction: str,
    max_length: int,
) -> str:
    template = getattr(tokenizer, "chat_template", None)
    if not isinstance(template, str) or not template:
        raise ValueError("Qwen tokenizer must expose a non-empty chat_template")
    manifest = {
        "formatter_version": PHASE40_FORMATTER_VERSION,
        "response_mask_version": PHASE40_RESPONSE_MASK_VERSION,
        "chat_template": template,
        "system_instruction": system_instruction,
        "raw_message_envelope": [_RAW_MESSAGE_OPEN, _RAW_MESSAGE_CLOSE],
        "json_serialization": {"ensure_ascii": False, "separators": [",", ":"]},
        "assistant_response_serialization": (
            "exact preformatted JSON from build_training_examples; no parse, repair, or normalization"
        ),
        "prompt_add_generation_prompt": True,
        "full_add_generation_prompt": False,
        "enable_thinking": False,
        "mask_value": -100,
        "max_length": max_length,
        "unicode_normalization": "none",
    }
    encoded = json.dumps(
        manifest,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def tokenize_phase40_response_only(
    example: dict[str, Any],
    tokenizer: Any,
    *,
    max_length: int,
) -> ResponseOnlyTokenizedExample:
    """Tokenize without truncation and mask every non-assistant target token."""

    messages = build_phase40_chat_messages(example)
    common_kwargs = {
        "tokenize": True,
        "truncation": False,
        "return_dict": False,
        "enable_thinking": False,
    }
    prompt_ids = _token_id_list(
        tokenizer.apply_chat_template(
            messages[:2],
            add_generation_prompt=True,
            **common_kwargs,
        )
    )
    full_ids = _token_id_list(
        tokenizer.apply_chat_template(
            messages,
            add_generation_prompt=False,
            **common_kwargs,
        )
    )
    if full_ids[: len(prompt_ids)] != prompt_ids:
        raise ValueError("Qwen chat template lost the prompt/assistant token boundary")
    answer_ids = full_ids[len(prompt_ids) :]
    if not answer_ids:
        raise ValueError("Qwen assistant answer produced no supervised tokens")
    if len(full_ids) > max_length:
        raise ValueError(
            f"Qwen response would truncate at max length {max_length}: total tokens={len(full_ids)}"
        )
    labels = [-100] * len(prompt_ids) + answer_ids
    return ResponseOnlyTokenizedExample(
        input_ids=tuple(full_ids),
        attention_mask=(1,) * len(full_ids),
        labels=tuple(labels),
        raw_message=str(example["text"]),
        formatter_version=PHASE40_FORMATTER_VERSION,
        formatter_sha256=_formatter_sha256(
            tokenizer,
            system_instruction=messages[0]["content"],
            max_length=max_length,
        ),
    )


class _ResponseOnlyDataset:
    def __init__(self, examples: Sequence[dict[str, Any]], tokenizer: Any, max_length: int) -> None:
        tokenized = tuple(
            tokenize_phase40_response_only(example, tokenizer, max_length=max_length)
            for example in examples
        )
        formatter_hashes = {item.formatter_sha256 for item in tokenized}
        formatter_versions = {item.formatter_version for item in tokenized}
        if len(formatter_hashes) > 1 or len(formatter_versions) > 1:
            raise RuntimeError("Qwen examples resolved to inconsistent formatter contracts")
        self.formatter_sha256 = next(iter(formatter_hashes), None)
        self.formatter_version = next(iter(formatter_versions), PHASE40_FORMATTER_VERSION)
        self.response_mask_version = PHASE40_RESPONSE_MASK_VERSION
        self._items = [item.as_item() for item in tokenized]

    def __len__(self) -> int:
        return len(self._items)

    def __getitem__(self, index: int) -> dict[str, Any]:
        return self._items[index]


class Phase40ResponseOnlyCollator:
    """Right-pad Qwen batches while preserving response-only ``-100`` labels."""

    def __init__(
        self,
        *,
        pad_token_id: int,
        tensor_factory: Callable[[list[list[int]]], Any] | None = None,
    ) -> None:
        if pad_token_id is None:
            raise ValueError("pad_token_id is required for response-only collation")
        self.pad_token_id = int(pad_token_id)
        if tensor_factory is None:
            torch_module = importlib.import_module("torch")
            tensor_factory = lambda values: torch_module.tensor(values, dtype=torch_module.long)
        self.tensor_factory = tensor_factory

    def __call__(self, features: Sequence[dict[str, Sequence[int]]]) -> dict[str, Any]:
        if not features:
            raise ValueError("response-only collator requires at least one feature")
        max_length = max(len(feature["input_ids"]) for feature in features)
        input_ids: list[list[int]] = []
        attention_masks: list[list[int]] = []
        labels: list[list[int]] = []
        for feature in features:
            ids = list(feature["input_ids"])
            mask = list(feature["attention_mask"])
            target = list(feature["labels"])
            if not (len(ids) == len(mask) == len(target)):
                raise ValueError("response-only feature fields must have equal lengths")
            padding = max_length - len(ids)
            input_ids.append(ids + [self.pad_token_id] * padding)
            attention_masks.append(mask + [0] * padding)
            labels.append(target + [-100] * padding)
        return {
            "input_ids": self.tensor_factory(input_ids),
            "attention_mask": self.tensor_factory(attention_masks),
            "labels": self.tensor_factory(labels),
        }


def _move_generation_input(value: Any, model: Any) -> Any:
    if not hasattr(value, "to"):
        return value
    device = getattr(model, "device", None)
    if device is None:
        try:
            device = next(model.parameters()).device
        except (AttributeError, StopIteration):
            return value
    return value.to(device)


def _attention_for_generation(input_ids: Any) -> Any:
    if hasattr(input_ids, "new_ones"):
        return input_ids.new_ones(input_ids.shape)
    return [1] * len(_token_id_list(input_ids))


def _first_generated_sequence(value: Any) -> list[int]:
    if hasattr(value, "tolist"):
        value = value.tolist()
    if isinstance(value, tuple):
        value = list(value)
    if not isinstance(value, list) or not value:
        raise RuntimeError("model.generate returned no sequence")
    sequence = value[0] if isinstance(value[0], list) else value
    if any(isinstance(item, bool) or not isinstance(item, int) for item in sequence):
        raise RuntimeError("model.generate returned a non-integer token sequence")
    return list(sequence)


def _prediction_jsonl_bytes(rows: Sequence[Phase40PredictionRow]) -> bytes:
    return b"".join(
        (
            json.dumps(
                row.as_json_dict(),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        ).encode("utf-8")
        for row in rows
    )


def _publish_prediction_jsonl(
    output_path: Path,
    payload: bytes,
    *,
    expected_validation_row_ids: Sequence[str],
) -> None:
    if output_path.exists():
        existing = output_path.read_bytes()
        if existing == payload:
            return
        raise FileExistsError(f"prediction artifact already exists with different bytes: {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        mode="wb",
        dir=output_path.parent,
        prefix=f".{output_path.name}.",
        suffix=".tmp",
        delete=False,
    )
    temporary_path = Path(handle.name)
    try:
        with handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        read_back = temporary_path.read_bytes()
        if read_back != payload:
            raise RuntimeError("prediction artifact temp-file read-back mismatch")
        try:
            decoded = read_back.decode("utf-8", errors="strict").splitlines()
            parsed = [json.loads(line) for line in decoded]
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeError("prediction artifact temp file is not valid UTF-8 JSONL") from exc
        actual_ids = tuple(row.get("validation_row_id") for row in parsed)
        if actual_ids != tuple(expected_validation_row_ids):
            raise RuntimeError("prediction artifact temp file changed validation row order")
        os.replace(temporary_path, output_path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def generate_qwen_validation_predictions(
    *,
    model: Any,
    tokenizer: Any,
    candidate: Any,
    validation_snapshot: CanonicalSplitSnapshot,
    artifact_identity: str,
    checkpoint_step: int,
    output_path: Path,
) -> tuple[Phase40PredictionRow, ...]:
    """Generate and atomically persist one deterministic canonical validation pass."""

    if validation_snapshot.split_name != "val":
        raise ValueError("Qwen validation generation requires the canonical validation snapshot")
    expected_ids = validation_snapshot.validation_row_ids
    gold_labels = tuple(row.record.label for row in validation_snapshot.rows)
    was_training = getattr(model, "training", False)
    if hasattr(model, "eval"):
        model.eval()
    try:
        try:
            torch_module = importlib.import_module("torch")
            inference_context = torch_module.inference_mode()
        except ImportError:
            inference_context = nullcontext()
        generated_rows: list[Phase40PredictionRow] = []
        with inference_context:
            for index, snapshot_row in enumerate(validation_snapshot.rows):
                example = build_training_examples([snapshot_row.record], candidate)[0]
                messages = build_phase40_chat_messages(example)
                input_ids = tokenizer.apply_chat_template(
                    messages[:2],
                    tokenize=True,
                    add_generation_prompt=True,
                    truncation=False,
                    return_dict=False,
                    return_tensors="pt",
                    enable_thinking=False,
                )
                prompt_ids = _token_id_list(input_ids)
                input_ids = _move_generation_input(input_ids, model)
                attention_mask = _attention_for_generation(input_ids)
                generated = model.generate(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                    do_sample=False,
                    num_return_sequences=1,
                    max_new_tokens=256,
                )
                full_sequence = _first_generated_sequence(generated)
                if full_sequence[: len(prompt_ids)] != prompt_ids:
                    raise RuntimeError("generated sequence does not preserve the exact prompt prefix")
                suffix_ids = full_sequence[len(prompt_ids) :]
                raw_prediction = tokenizer.decode(
                    suffix_ids,
                    skip_special_tokens=True,
                    clean_up_tokenization_spaces=False,
                )
                generated_rows.append(
                    Phase40PredictionRow.from_raw(
                        validation_row_id=snapshot_row.validation_row_id,
                        sequence_index=index,
                        gold_label=snapshot_row.record.label,
                        raw_prediction=raw_prediction,
                        artifact_identity=artifact_identity,
                        checkpoint_step=checkpoint_step,
                    )
                )
    finally:
        if hasattr(model, "train"):
            model.train(was_training)

    rows = tuple(generated_rows)
    validate_phase40_prediction_rows(
        expected_validation_row_ids=expected_ids,
        gold_labels=gold_labels,
        prediction_rows=rows,
    )
    payload = _prediction_jsonl_bytes(rows)
    _publish_prediction_jsonl(
        Path(output_path),
        payload,
        expected_validation_row_ids=expected_ids,
    )
    return rows


@dataclass(frozen=True, slots=True)
class QwenValidationCheckpointSource:
    """One immutable checkpoint load supplied to an offline validation schedule."""

    checkpoint_step: int
    model: Any
    tokenizer: Any
    artifact_identity: str


def generate_qwen_validation_schedule(
    *,
    candidate: Any,
    validation_snapshot: CanonicalSplitSnapshot,
    checkpoint_sources: Sequence[QwenValidationCheckpointSource],
    evaluation_steps: Sequence[int],
    final_step: int,
    output_dir: Path,
) -> dict[int, tuple[Phase40PredictionRow, ...]]:
    """Validate distinct loaded checkpoint states at every declared step and final."""

    steps: list[int] = []
    for step in (*evaluation_steps, final_step):
        if step < 0:
            raise ValueError("evaluation steps must be non-negative")
        if step not in steps:
            steps.append(step)
    sources = tuple(checkpoint_sources)
    if tuple(source.checkpoint_step for source in sources) != tuple(steps):
        raise ValueError("checkpoint sources must exactly match declared evaluation/final step order")
    if len({id(source.model) for source in sources}) != len(sources):
        raise ValueError("offline validation cannot reuse one current model as historical checkpoints")
    if len({source.artifact_identity for source in sources}) != len(sources):
        raise ValueError("each validation checkpoint requires a distinct artifact identity")
    return {
        source.checkpoint_step: generate_qwen_validation_predictions(
            model=source.model,
            tokenizer=source.tokenizer,
            candidate=candidate,
            validation_snapshot=validation_snapshot,
            artifact_identity=source.artifact_identity,
            checkpoint_step=source.checkpoint_step,
            output_path=Path(output_dir) / f"predictions-step-{source.checkpoint_step}.jsonl",
        )
        for source in sources
    }


def _adapter_weight_path(artifact_path: Path) -> Path:
    candidates = [artifact_path / name for name in _ADAPTER_WEIGHT_NAMES if (artifact_path / name).is_file()]
    if len(candidates) != 1:
        raise RuntimeError(
            f"adapter artifact must contain exactly one supported weight file: {artifact_path}"
        )
    if not (artifact_path / _ADAPTER_CONFIG_NAME).is_file():
        raise RuntimeError(f"adapter artifact is missing {_ADAPTER_CONFIG_NAME}: {artifact_path}")
    return candidates[0]


def _load_saved_adapter_state(artifact_path: Path, *, torch_module: Any) -> dict[str, Any]:
    weight_path = _adapter_weight_path(Path(artifact_path))
    if weight_path.suffix == ".safetensors":
        try:
            safetensors_torch = importlib.import_module("safetensors.torch")
        except ImportError as exc:
            raise RuntimeError("safetensors is required to verify the saved adapter") from exc
        state = safetensors_torch.load_file(str(weight_path), device="cpu")
    else:
        try:
            state = torch_module.load(str(weight_path), map_location="cpu", weights_only=True)
        except TypeError as exc:
            raise RuntimeError("safe weights-only torch.load support is required") from exc
    if not isinstance(state, dict) or not state:
        raise RuntimeError("saved adapter state must be a non-empty tensor mapping")
    return {str(key): value for key, value in state.items()}


def _cpu_tensor(value: Any) -> Any:
    if not hasattr(value, "detach") or not hasattr(value, "cpu"):
        raise RuntimeError("adapter state contains a non-tensor value")
    return value.detach().cpu().contiguous()


def _adapter_state_identity(state: dict[str, Any], *, torch_module: Any) -> str:
    digest = hashlib.sha256(b"phase40-adapter-state-v1\0")
    for name in sorted(state):
        tensor = _cpu_tensor(state[name])
        digest.update(name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(tensor.dtype).encode("ascii"))
        digest.update(b"\0")
        digest.update(json.dumps(list(tensor.shape), separators=(",", ":")).encode("ascii"))
        digest.update(b"\0")
        try:
            tensor_bytes = tensor.view(torch_module.uint8).numpy().tobytes()
        except (AttributeError, RuntimeError, TypeError) as exc:
            raise RuntimeError("adapter tensor cannot be serialized for identity proof") from exc
        digest.update(tensor_bytes)
        digest.update(b"\0")
    return f"adapter-state-sha256:{digest.hexdigest()}"


def _prove_saved_adapter_matches_live(
    model: Any,
    artifact_path: Path,
    *,
    torch_module: Any,
    peft_module: Any,
) -> str:
    getter = getattr(peft_module, "get_peft_model_state_dict", None)
    if getter is None:
        raise RuntimeError("PEFT get_peft_model_state_dict is required for artifact proof")
    live_state_raw = getter(model)
    if not isinstance(live_state_raw, dict) or not live_state_raw:
        raise RuntimeError("live adapter state must be a non-empty tensor mapping")
    live_state = {str(key): _cpu_tensor(value) for key, value in live_state_raw.items()}
    saved_state = {
        key: _cpu_tensor(value)
        for key, value in _load_saved_adapter_state(artifact_path, torch_module=torch_module).items()
    }
    if set(live_state) != set(saved_state):
        raise RuntimeError("saved adapter keys do not match the live adapter state")
    for name in sorted(live_state):
        if not bool(torch_module.equal(live_state[name], saved_state[name])):
            raise RuntimeError(f"saved adapter tensor does not match live state: {name}")
    live_identity = _adapter_state_identity(live_state, torch_module=torch_module)
    saved_identity = _adapter_state_identity(saved_state, torch_module=torch_module)
    if live_identity != saved_identity:
        raise RuntimeError("saved adapter identity does not match the live adapter identity")
    return saved_identity


def _retain_adapter_payload(source: Path, target: Path) -> Path:
    """Copy only the verified loadable adapter payload to an immutable path."""

    source = Path(source)
    target = Path(target)
    weight_path = _adapter_weight_path(source)
    source_files = (source / _ADAPTER_CONFIG_NAME, weight_path)
    if target.exists():
        target_weight = _adapter_weight_path(target)
        target_files = (target / _ADAPTER_CONFIG_NAME, target_weight)
        if all(
            source_file.read_bytes() == target_file.read_bytes()
            for source_file, target_file in zip(source_files, target_files, strict=True)
        ):
            return target
        raise FileExistsError(f"retained adapter path already contains different bytes: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{target.name}.", dir=target.parent))
    try:
        for source_file in source_files:
            shutil.copy2(source_file, temporary / source_file.name)
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
    return target


class Phase40ValidationRecorder:
    """Bind real Trainer save events to checkpoint-specific raw generations."""

    def __init__(
        self,
        *,
        tokenizer: Any,
        candidate: Any,
        validation_snapshot: CanonicalSplitSnapshot,
        training_output_dir: Path,
        prediction_output_dir: Path,
        retained_artifact_root: Path,
        artifact_identity_prover: Callable[[Any, Path], str],
        stored_artifact_identity_loader: Callable[[Path], str] | None = None,
    ) -> None:
        if validation_snapshot.split_name != "val":
            raise ValueError("checkpoint validation requires a validation snapshot")
        self.tokenizer = tokenizer
        self.candidate = candidate
        self.validation_snapshot = validation_snapshot
        self.training_output_dir = Path(training_output_dir)
        self.prediction_output_dir = Path(prediction_output_dir)
        self.retained_artifact_root = Path(retained_artifact_root)
        self.artifact_identity_prover = artifact_identity_prover
        self.stored_artifact_identity_loader = stored_artifact_identity_loader
        self.metrics_by_candidate: dict[tuple[int, str], Phase40MetricResult] = {}
        self.retained_paths: dict[tuple[int, str], Path] = {}

    def record(
        self,
        *,
        model: Any,
        checkpoint_step: int,
        artifact_path: Path,
        artifact_scope: str,
    ) -> Phase40MetricResult:
        artifact_path = Path(artifact_path)
        if not artifact_path.exists():
            raise RuntimeError(
                f"validation checkpoint artifact is missing at step {checkpoint_step}: {artifact_path}"
            )
        artifact_identity = self.artifact_identity_prover(model, artifact_path)
        identity_prefix = "adapter-state-sha256:"
        identity_digest = artifact_identity.removeprefix(identity_prefix)
        if (
            not artifact_identity.startswith(identity_prefix)
            or len(identity_digest) != 64
            or any(character not in "0123456789abcdef" for character in identity_digest)
        ):
            raise RuntimeError("adapter identity prover returned an invalid state identity")
        candidate_key = (checkpoint_step, artifact_identity)
        if candidate_key in self.metrics_by_candidate:
            return self.metrics_by_candidate[candidate_key]
        retained_path = _retain_adapter_payload(
            artifact_path,
            self.retained_artifact_root / f"step-{checkpoint_step}-{identity_digest}",
        )
        retained_identity = self.artifact_identity_prover(model, retained_path)
        if retained_identity != artifact_identity:
            raise RuntimeError("retained adapter identity changed during materialization")
        rows = generate_qwen_validation_predictions(
            model=model,
            tokenizer=self.tokenizer,
            candidate=self.candidate,
            validation_snapshot=self.validation_snapshot,
            artifact_identity=artifact_identity,
            checkpoint_step=checkpoint_step,
            output_path=(
                self.prediction_output_dir
                / f"predictions-{artifact_scope}-step-{checkpoint_step}-{identity_digest}.jsonl"
            ),
        )
        metrics = evaluate_phase40_predictions(
            expected_validation_row_ids=self.validation_snapshot.validation_row_ids,
            gold_labels=tuple(row.record.label for row in self.validation_snapshot.rows),
            prediction_rows=rows,
        )
        self.metrics_by_candidate[candidate_key] = metrics
        self.retained_paths[candidate_key] = retained_path
        return metrics

    def record_saved_checkpoint(self, *, model: Any, checkpoint_step: int) -> Phase40MetricResult:
        return self.record(
            model=model,
            checkpoint_step=checkpoint_step,
            artifact_path=self.training_output_dir / f"checkpoint-{checkpoint_step}",
            artifact_scope="checkpoint",
        )

    def record_final_if_needed(
        self,
        *,
        model: Any,
        final_step: int,
        final_artifact_path: Path,
    ) -> Phase40MetricResult:
        return self.record(
            model=model,
            checkpoint_step=final_step,
            artifact_path=final_artifact_path,
            artifact_scope="final",
        )

    def select(self) -> CheckpointSelection:
        return select_phase40_checkpoint(tuple(self.metrics_by_candidate.values()))

    def retained_path_for(self, selection: CheckpointSelection) -> Path:
        key = (selection.selected_step, selection.selected_artifact_identity)
        try:
            return self.retained_paths[key]
        except KeyError as exc:
            raise RuntimeError("selected checkpoint has no retained adapter payload") from exc

    def resume_history_payload(self, telemetry_state: Mapping[str, object]) -> dict[str, Any]:
        """Serialize every measured candidate into a checkpoint-contained history."""

        candidates: list[dict[str, Any]] = []
        for (step, artifact_identity), metrics in sorted(self.metrics_by_candidate.items()):
            retained_path = self.retained_paths.get((step, artifact_identity))
            if retained_path is None:
                raise RuntimeError("validation candidate lacks its retained adapter payload")
            try:
                retained_relative = retained_path.relative_to(self.retained_artifact_root)
            except ValueError as exc:
                raise RuntimeError("retained adapter path escapes its canonical history root") from exc
            if len(retained_relative.parts) != 1 or retained_relative.name != retained_relative.as_posix():
                raise RuntimeError("retained adapter history path must be one direct child")
            prediction_rows = [row.as_json_dict() for row in metrics.prediction_rows]
            metric_payload = _canonical_json_line(_json_ready(asdict(metrics)))
            candidates.append(
                {
                    "checkpoint_step": step,
                    "artifact_identity": artifact_identity,
                    "prediction_rows": prediction_rows,
                    "predictions_sha256": hashlib.sha256(
                        _prediction_jsonl_bytes(metrics.prediction_rows)
                    ).hexdigest(),
                    "metrics_sha256": hashlib.sha256(metric_payload).hexdigest(),
                    "retained_adapter_directory": retained_relative.as_posix(),
                    "retained_adapter_sha256": build_model_checksum(retained_path),
                }
            )
        if not candidates:
            raise RuntimeError("resume history requires at least one validation candidate")
        return {
            "schema_version": PHASE40_RESUME_HISTORY_SCHEMA_VERSION,
            "candidates": candidates,
            "telemetry_state": dict(telemetry_state),
        }

    def restore_resume_history(self, payload: Mapping[str, object]) -> Mapping[str, object]:
        """Restore checkpoint candidates only after revalidating rows, metrics, and adapters."""

        if not isinstance(payload, Mapping) or set(payload) != {
            "schema_version",
            "candidates",
            "telemetry_state",
        }:
            raise RuntimeError("Qwen resume history has missing or extra fields")
        if payload["schema_version"] != PHASE40_RESUME_HISTORY_SCHEMA_VERSION:
            raise RuntimeError("Qwen resume history schema version is unsupported")
        candidates = payload["candidates"]
        telemetry_state = payload["telemetry_state"]
        if not isinstance(candidates, list) or not candidates:
            raise RuntimeError("Qwen resume history omitted its validation candidates")
        if not isinstance(telemetry_state, Mapping):
            raise RuntimeError("Qwen resume history omitted its telemetry state")
        if self.metrics_by_candidate or self.retained_paths:
            raise RuntimeError("Qwen resume history can restore only into an empty recorder")
        if self.stored_artifact_identity_loader is None:
            raise RuntimeError("Qwen resume history lacks a stored-adapter identity loader")

        restored_metrics: dict[tuple[int, str], Phase40MetricResult] = {}
        restored_paths: dict[tuple[int, str], Path] = {}
        previous_key: tuple[int, str] | None = None
        for candidate in candidates:
            expected_keys = {
                "checkpoint_step",
                "artifact_identity",
                "prediction_rows",
                "predictions_sha256",
                "metrics_sha256",
                "retained_adapter_directory",
                "retained_adapter_sha256",
            }
            if not isinstance(candidate, dict) or set(candidate) != expected_keys:
                raise RuntimeError("Qwen resume candidate has missing or extra fields")
            step = candidate["checkpoint_step"]
            identity = candidate["artifact_identity"]
            if not isinstance(step, int) or isinstance(step, bool) or step < 0:
                raise RuntimeError("Qwen resume candidate has an invalid checkpoint step")
            if not isinstance(identity, str) or not re.fullmatch(
                r"adapter-state-sha256:[0-9a-f]{64}", identity
            ):
                raise RuntimeError("Qwen resume candidate has an invalid adapter identity")
            key = (step, identity)
            if previous_key is not None and key <= previous_key:
                raise RuntimeError("Qwen resume candidates must be unique and canonically ordered")
            previous_key = key
            raw_rows = candidate["prediction_rows"]
            if not isinstance(raw_rows, list) or not raw_rows:
                raise RuntimeError("Qwen resume candidate omitted prediction rows")
            rows: list[Phase40PredictionRow] = []
            for raw in raw_rows:
                if not isinstance(raw, dict):
                    raise RuntimeError("Qwen resume prediction row is not an object")
                try:
                    decoder = raw["decoder"]
                    row = Phase40PredictionRow.from_raw(
                        validation_row_id=raw["validation_row_id"],
                        sequence_index=raw["sequence_index"],
                        gold_label=raw["gold_label"],
                        raw_prediction=raw["raw_prediction"],
                        artifact_identity=raw["artifact_identity"],
                        checkpoint_step=raw["checkpoint_step"],
                    )
                except (KeyError, TypeError, ValueError) as exc:
                    raise RuntimeError("Qwen resume prediction row is invalid") from exc
                if not isinstance(decoder, dict) or row.as_json_dict() != raw:
                    raise RuntimeError("Qwen resume prediction row changed its locked parse/decoder")
                rows.append(row)
            restored_rows = tuple(rows)
            predictions_sha256 = hashlib.sha256(_prediction_jsonl_bytes(restored_rows)).hexdigest()
            if candidate["predictions_sha256"] != predictions_sha256:
                raise RuntimeError("Qwen resume prediction history SHA-256 drifted")
            metrics = evaluate_phase40_predictions(
                expected_validation_row_ids=self.validation_snapshot.validation_row_ids,
                gold_labels=tuple(row.record.label for row in self.validation_snapshot.rows),
                prediction_rows=restored_rows,
            )
            metrics_sha256 = hashlib.sha256(
                _canonical_json_line(_json_ready(asdict(metrics)))
            ).hexdigest()
            if candidate["metrics_sha256"] != metrics_sha256:
                raise RuntimeError("Qwen resume metric history SHA-256 drifted")
            directory = candidate["retained_adapter_directory"]
            if (
                not isinstance(directory, str)
                or PurePosixPath(directory).is_absolute()
                or len(PurePosixPath(directory).parts) != 1
                or directory != PurePosixPath(directory).as_posix()
            ):
                raise RuntimeError("Qwen resume retained-adapter path is unsafe")
            retained_path = self.retained_artifact_root / directory
            if (
                not retained_path.is_dir()
                or retained_path.is_symlink()
                or build_model_checksum(retained_path) != candidate["retained_adapter_sha256"]
            ):
                raise RuntimeError("Qwen resume retained adapter is missing or changed")
            if self.stored_artifact_identity_loader(retained_path) != identity:
                raise RuntimeError("Qwen resume retained adapter identity drifted")
            if any(row.artifact_identity != identity or row.checkpoint_step != step for row in rows):
                raise RuntimeError("Qwen resume predictions differ from their candidate identity")
            restored_metrics[key] = metrics
            restored_paths[key] = retained_path

        self.metrics_by_candidate.update(restored_metrics)
        self.retained_paths.update(restored_paths)
        return telemetry_state


def _build_validation_trainer_callback(
    transformers_module: Any,
    recorder: Phase40ValidationRecorder,
) -> Any:
    """Create a real Trainer callback without importing Transformers at module load."""

    callback_base = getattr(transformers_module, "TrainerCallback", object)

    class _ValidationCallback(callback_base):
        def on_save(self, args, state, control, model=None, **kwargs):  # noqa: ANN001
            if model is None:
                raise RuntimeError("Trainer on_save did not provide the checkpoint model")
            recorder.record_saved_checkpoint(
                model=model,
                checkpoint_step=int(state.global_step),
            )
            return control

    return _ValidationCallback()


@dataclass(frozen=True)
class TrainingConfig:
    """Resolved training configuration for one selected Phase 3 candidate."""

    candidate_id: str
    baseline_winner_id: str
    runner_up_id: str
    train_split_path: Path
    val_split_path: Path
    version_tag: str
    output_root: Path
    registry_path: Path
    adaptation_mode: AdaptationMode
    run_kind: RunKind
    model_id: str | None = None
    dry_run: bool = False
    base_model_path: Path | None = None
    base_model_manifest_path: Path | None = None
    num_train_epochs: float = 1.0
    max_steps: int = -1
    per_device_train_batch_size: int = 1
    gradient_accumulation_steps: int = 4
    learning_rate: float = 2e-4
    logging_steps: int = 10
    save_steps: int = 50
    save_total_limit: int = 2
    max_seq_length: int = 1024
    smoke_test: bool = False
    resume_from_checkpoint: str | None = None
    device: str = "auto"
    gradient_checkpointing: bool = True
    local_files_only: bool = True
    trust_remote_code: bool = True
    lora_r: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.05
    lora_bias: str = "none"
    target_modules: tuple[str, ...] = DEFAULT_TARGET_MODULES
    model_revision: str = PHASE40_QWEN_REVISION
    run_id: str | None = None
    probe_post_warmup_steps: int | None = None
    probe_warmup_steps: int = 5
    seed: int = 42
    data_seed: int = 42
    optimizer_name: str = "adamw_torch"
    weight_decay: float = 0.0
    lr_scheduler_type: str = "linear"
    warmup_steps: int = 0
    warmup_ratio: float = 0.03
    max_grad_norm: float = 1.0
    tf32: bool = False
    transfer_authority: TransferAuthorityEvidence | None = None
    requested_control_template: RequestedControlTemplate | None = None
    sanitized_argv: tuple[str, ...] | None = None
    run_bundle_root: Path | None = None
    dataloader_num_workers: int = 0
    controller_stop_request_path: Path | None = None
    planned_full_optimizer_steps_override: int | None = None
    local_decision: bool = False

    def __post_init__(self) -> None:
        mode = AdaptationMode(self.adaptation_mode)
        kind = RunKind(self.run_kind)
        ExperimentIdentity(ModelFamily.QWEN, mode, kind)
        object.__setattr__(self, "adaptation_mode", mode)
        object.__setattr__(self, "run_kind", kind)
        if self.model_id is not None and (
            not isinstance(self.model_id, str)
            or not re.fullmatch(
                r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}(?:/[A-Za-z0-9][A-Za-z0-9._-]{0,127})?",
                self.model_id,
            )
        ):
            raise ValueError("Phase 40 model_id must be a portable model name or owner/model pair")
        if self.base_model_manifest_path is not None and self.base_model_path is None:
            raise ValueError("base_model_manifest_path requires an explicit base_model_path")
        if self.lora_bias != "none":
            raise ValueError("Phase 40 Qwen LoRA bias must be 'none'")
        if self.target_modules != DEFAULT_TARGET_MODULES:
            raise ValueError("Phase 40 Qwen target_modules must be the seven locked projections")
        if not re.fullmatch(r"[0-9a-f]{40}", self.model_revision):
            raise ValueError("Phase 40 model_revision must be a full lowercase 40-hex revision")
        if self.run_id is not None and not _RUN_ID_PATTERN.fullmatch(self.run_id):
            raise ValueError("Phase 40 run_id must be a normalized portable identifier")
        if self.probe_warmup_steps < 0:
            raise ValueError("probe_warmup_steps must be non-negative")
        if kind == RunKind.FULL and self.probe_post_warmup_steps is not None:
            raise ValueError("probe_post_warmup_steps is reserved for probe runs")
        if kind == RunKind.PROBE and self.resume_from_checkpoint is not None:
            raise ValueError("Phase 40 probes cannot accept resume input")
        if self.seed < 0 or self.data_seed < 0:
            raise ValueError("Phase 40 seeds must be non-negative")
        if self.weight_decay < 0 or self.warmup_steps < 0 or not 0 <= self.warmup_ratio <= 1:
            raise ValueError("Phase 40 optimizer warm-up/decay controls are invalid")
        if self.max_grad_norm <= 0:
            raise ValueError("Phase 40 max_grad_norm must be positive")
        if self.transfer_authority is not None and not isinstance(
            self.transfer_authority,
            TransferAuthorityEvidence,
        ):
            raise ValueError("transfer_authority must be typed Phase 40 transfer evidence")
        if self.requested_control_template is not None and not isinstance(
            self.requested_control_template,
            RequestedControlTemplate,
        ):
            raise ValueError(
                "requested_control_template must be a typed Phase 40 request control template"
            )
        if self.sanitized_argv is not None and (
            not isinstance(self.sanitized_argv, tuple)
            or not self.sanitized_argv
            or any(not isinstance(value, str) or not value for value in self.sanitized_argv)
        ):
            raise ValueError("sanitized_argv must be a non-empty tuple of argument strings")
        if kind == RunKind.PROBE and self.run_bundle_root is not None:
            raise ValueError("run_bundle_root is reserved for immutable full-run evidence")
        if (
            not isinstance(self.dataloader_num_workers, int)
            or isinstance(self.dataloader_num_workers, bool)
            or self.dataloader_num_workers < 0
        ):
            raise ValueError("dataloader_num_workers must be a non-negative integer")
        if self.planned_full_optimizer_steps_override is not None and (
            not isinstance(self.planned_full_optimizer_steps_override, int)
            or isinstance(self.planned_full_optimizer_steps_override, bool)
            or self.planned_full_optimizer_steps_override <= 0
        ):
            raise ValueError("planned full optimizer-step override must be positive")
        if self.local_decision:
            if kind != RunKind.PROBE:
                raise ValueError("local decision training must remain run_kind=probe")
            if self.controller_stop_request_path is None:
                raise ValueError("local decision training requires a controller stop path")
            if self.dataloader_num_workers != 0:
                raise ValueError("local decision training fixes data-loader workers to zero")
            if self.smoke_test:
                raise ValueError("local decision training forbids the smoke-test mutation")
            if self.resume_from_checkpoint is not None:
                raise ValueError("local decision training cannot resume")
            if not self.local_files_only or self.trust_remote_code:
                raise ValueError("local decision training must be offline with remote code disabled")

    @property
    def experiment_identity(self) -> ExperimentIdentity:
        return ExperimentIdentity(ModelFamily.QWEN, self.adaptation_mode, self.run_kind)


def _resolve_selection(selection: PilotSelection | None, registry_path: Path | None) -> PilotSelection:
    if selection is not None:
        return selection
    if registry_path is None:
        raise ValueError("selection or registry_path is required")

    registry = load_model_registry(registry_path)
    if registry.selection is None:
        raise ValueError("Model registry does not contain a pilot selection")
    return registry.selection


def _selected_candidate_ids(selection: PilotSelection) -> set[str]:
    return {selection.baseline_winner_id, selection.runner_up_id}


def build_training_config(
    candidate_id: str,
    train_split_path: Path,
    val_split_path: Path,
    version_tag: str,
    output_root: Path,
    *,
    adaptation_mode: AdaptationMode | str,
    selection: PilotSelection | None = None,
    registry_path: Path | None = None,
    dry_run: bool = False,
    base_model_path: Path | None = None,
    base_model_manifest_path: Path | None = None,
    num_train_epochs: float = 1.0,
    max_steps: int | None = None,
    per_device_train_batch_size: int = 1,
    gradient_accumulation_steps: int = 4,
    learning_rate: float = 2e-4,
    logging_steps: int = 10,
    save_steps: int = 50,
    save_total_limit: int = 2,
    max_seq_length: int = 1024,
    smoke_test: bool = False,
    resume_from_checkpoint: str | None = None,
    device: str = "auto",
    gradient_checkpointing: bool = True,
    local_files_only: bool = True,
    trust_remote_code: bool = True,
    run_kind: RunKind | str = RunKind.FULL,
    lora_r: int = 16,
    lora_alpha: int = 32,
    lora_dropout: float = 0.05,
    lora_bias: str = "none",
    target_modules: tuple[str, ...] = DEFAULT_TARGET_MODULES,
    model_revision: str = PHASE40_QWEN_REVISION,
    run_id: str | None = None,
    probe_post_warmup_steps: int | None = None,
    probe_warmup_steps: int = 5,
    seed: int = 42,
    data_seed: int = 42,
    optimizer_name: str = "adamw_torch",
    weight_decay: float = 0.0,
    lr_scheduler_type: str = "linear",
    warmup_steps: int = 0,
    warmup_ratio: float = 0.03,
    max_grad_norm: float = 1.0,
    tf32: bool = False,
    transfer_authority: TransferAuthorityEvidence | None = None,
    requested_control_template: RequestedControlTemplate | None = None,
    sanitized_argv: tuple[str, ...] | None = None,
    run_bundle_root: Path | None = None,
    dataloader_num_workers: int = 0,
    controller_stop_request_path: Path | None = None,
    planned_full_optimizer_steps_override: int | None = None,
    local_decision: bool = False,
) -> TrainingConfig:
    """Build a training config restricted to the pilot-selected candidates."""

    resolved_selection = _resolve_selection(selection, registry_path)
    allowed_candidate_ids = _selected_candidate_ids(resolved_selection)
    if candidate_id not in allowed_candidate_ids:
        raise ValueError("Training is limited to the pilot-selected baseline winner and runner-up")

    resolved_registry_path = registry_path or get_settings().model_registry_path
    get_candidate_by_id(candidate_id)
    resolved_max_steps = -1 if max_steps is None else max_steps
    resolved_logging_steps = logging_steps
    resolved_save_steps = save_steps
    resolved_gradient_accumulation_steps = gradient_accumulation_steps
    if smoke_test:
        if max_steps is None or max_steps < 0:
            resolved_max_steps = SMOKE_TEST_MAX_STEPS
        resolved_logging_steps = 1
        resolved_save_steps = 1
        resolved_gradient_accumulation_steps = 1
    return TrainingConfig(
        candidate_id=candidate_id,
        baseline_winner_id=resolved_selection.baseline_winner_id,
        runner_up_id=resolved_selection.runner_up_id,
        train_split_path=train_split_path,
        val_split_path=val_split_path,
        version_tag=version_tag,
        output_root=output_root,
        registry_path=resolved_registry_path,
        dry_run=dry_run,
        base_model_path=base_model_path,
        base_model_manifest_path=base_model_manifest_path,
        num_train_epochs=num_train_epochs,
        max_steps=resolved_max_steps,
        per_device_train_batch_size=per_device_train_batch_size,
        gradient_accumulation_steps=resolved_gradient_accumulation_steps,
        learning_rate=learning_rate,
        logging_steps=resolved_logging_steps,
        save_steps=resolved_save_steps,
        save_total_limit=save_total_limit,
        max_seq_length=max_seq_length,
        smoke_test=smoke_test,
        resume_from_checkpoint=resume_from_checkpoint,
        device=device,
        gradient_checkpointing=gradient_checkpointing,
        local_files_only=local_files_only,
        trust_remote_code=trust_remote_code,
        adaptation_mode=AdaptationMode(adaptation_mode),
        run_kind=RunKind(run_kind),
        lora_r=lora_r,
        lora_alpha=lora_alpha,
        lora_dropout=lora_dropout,
        lora_bias=lora_bias,
        target_modules=target_modules,
        model_revision=model_revision,
        run_id=run_id,
        probe_post_warmup_steps=probe_post_warmup_steps,
        probe_warmup_steps=probe_warmup_steps,
        seed=seed,
        data_seed=data_seed,
        optimizer_name=optimizer_name,
        weight_decay=weight_decay,
        lr_scheduler_type=lr_scheduler_type,
        warmup_steps=warmup_steps,
        warmup_ratio=warmup_ratio,
        max_grad_norm=max_grad_norm,
        tf32=tf32,
        transfer_authority=transfer_authority,
        requested_control_template=requested_control_template,
        sanitized_argv=sanitized_argv,
        run_bundle_root=run_bundle_root,
        dataloader_num_workers=dataloader_num_workers,
        controller_stop_request_path=controller_stop_request_path,
        planned_full_optimizer_steps_override=planned_full_optimizer_steps_override,
        local_decision=local_decision,
    )


def _candidate_output_dir(config: TrainingConfig) -> Path:
    return config.output_root / config.version_tag / config.candidate_id


def _resolved_model_id(config: TrainingConfig) -> str:
    return config.model_id or config.candidate_id


def _resolved_run_id(config: TrainingConfig) -> str:
    if config.run_id is not None:
        return config.run_id
    raw = "-".join(
        (
            config.version_tag,
            config.candidate_id,
            config.adaptation_mode.value,
            config.run_kind.value,
        )
    )
    normalized = re.sub(r"[^A-Za-z0-9._-]+", "-", raw).strip("-._")[:128]
    if not normalized or not _RUN_ID_PATTERN.fullmatch(normalized):
        raise ValueError("could not derive a safe Phase 40 run_id")
    return normalized


def _probe_root(config: TrainingConfig) -> Path:
    if config.run_kind != RunKind.PROBE:
        raise ValueError("probe root is available only for probe runs")
    return _candidate_output_dir(config) / "probes" / _resolved_run_id(config)


def _evidence_root(config: TrainingConfig) -> Path:
    if config.run_kind == RunKind.FULL:
        if config.run_bundle_root is None:
            raise RuntimeError(
                "full Phase 40 execution requires an explicit request-bound run_bundle_root"
            )
        return Path(config.run_bundle_root)
    return _candidate_output_dir(config) / "evidence" / _resolved_run_id(config)


def _require_full_execution_authority(config: TrainingConfig) -> None:
    """Reject an unbound full run before any model/backend side effect."""

    if config.run_kind != RunKind.FULL:
        return
    if config.transfer_authority is None:
        raise RuntimeError("full Phase 40 execution requires explicit transfer authority")
    if config.requested_control_template is None:
        raise RuntimeError(
            "full Phase 40 execution requires its frozen requested_control_template"
        )
    if config.run_bundle_root is None:
        raise RuntimeError(
            "full Phase 40 execution requires an explicit request-bound run_bundle_root"
        )
    if config.sanitized_argv is None:
        raise RuntimeError("full Phase 40 execution requires the actual sanitized CLI argv")


def _absolute_non_symlink_bundle_root(config: TrainingConfig) -> Path:
    """Resolve the explicit root lexically while refusing symlink traversal/overlap."""

    root = _evidence_root(config)
    if not root.is_absolute():
        raise ValueError("run_bundle_root must be an absolute request-bound path")
    if ".." in root.parts:
        raise ValueError("run_bundle_root must not contain parent traversal")
    normalized = Path(os.path.abspath(os.path.normpath(os.fspath(root))))
    if normalized == Path(normalized.anchor):
        raise ValueError("run_bundle_root must not be a filesystem root")

    current = normalized
    while True:
        if current.exists() and current.is_symlink():
            raise ValueError("run_bundle_root must not traverse a symlink")
        if current.parent == current:
            break
        current = current.parent

    work_root = Path(
        os.path.abspath(os.path.normpath(os.fspath(_candidate_output_dir(config))))
    )
    if normalized == work_root or normalized in work_root.parents or work_root in normalized.parents:
        raise ValueError("run_bundle_root must not overlap the mutable candidate work root")
    return normalized


def _prepare_full_run_bundle_root(
    config: TrainingConfig,
    *,
    create: bool,
) -> Path:
    """Validate and optionally reserve the request-bound immutable full-run root."""

    if config.run_kind != RunKind.FULL:
        raise ValueError("full-run bundle root preparation is available only for full runs")
    root = _absolute_non_symlink_bundle_root(config)
    if root.exists():
        if not root.is_dir() or root.is_symlink():
            raise ValueError("run_bundle_root must be a non-symlink directory")
        if any(path.is_symlink() for path in root.rglob("*")):
            raise ValueError("run_bundle_root must not contain symlinks")
        has_entries = any(root.iterdir())
        if config.resume_from_checkpoint is None:
            if has_entries:
                raise FileExistsError(
                    "fresh Phase 40 full run requires an empty request-bound bundle root"
                )
        else:
            if not has_entries:
                raise RuntimeError("exact resume requires the original non-empty run bundle")
            events = load_run_events(root / "events.jsonl", expected_run_id=_resolved_run_id(config))
            if events[-1].event_kind == RunEventKind.RUN_END:
                raise RuntimeError("completed full-run evidence cannot be resumed")
    elif config.resume_from_checkpoint is not None:
        raise RuntimeError("exact resume requires the original request-bound run bundle")

    if create:
        root.mkdir(parents=True, exist_ok=True)
        if not root.is_dir() or root.is_symlink():
            raise RuntimeError("could not reserve a non-symlink run_bundle_root")
    return root


def _verify_requested_runtime_controls(
    config: TrainingConfig,
    controlled_config: ResumeControlledConfig,
) -> None:
    """Bind measured runtime hardware to the otherwise frozen request controls."""

    if config.run_kind != RunKind.FULL:
        return
    template = config.requested_control_template
    if template is None:
        raise RuntimeError(
            "full Phase 40 execution requires its frozen requested_control_template"
        )
    template.verify_runtime_config(controlled_config)


def _training_output_dir(config: TrainingConfig) -> Path:
    if config.run_kind == RunKind.PROBE:
        return _probe_root(config) / "trainer"
    return _candidate_output_dir(config) / "trainer"


def _adapter_output_dir(config: TrainingConfig) -> Path:
    if config.run_kind == RunKind.PROBE:
        return _probe_root(config) / "adapter"
    return _candidate_output_dir(config) / "adapter"


def _final_adapter_output_dir(config: TrainingConfig) -> Path:
    if config.run_kind == RunKind.PROBE:
        return _probe_root(config) / "final-adapter"
    return _candidate_output_dir(config) / "final-adapter"


def _snapshot_row_id_digest(snapshot: CanonicalSplitSnapshot) -> str:
    digest = hashlib.sha256(b"phase40-ordered-row-ids-v1\0")
    for row_id in snapshot.row_ids:
        digest.update(row_id.encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def _load_download_manifest(output_root: Path) -> dict[str, Path]:
    manifest_path = output_root / "manifests" / "download-manifest.json"
    if not manifest_path.exists():
        return {}

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    model_paths: dict[str, Path] = {}
    for model in payload.get("models", []):
        candidate_id = model.get("candidate_id")
        local_path = model.get("local_path")
        if candidate_id and local_path:
            model_paths[str(candidate_id)] = Path(str(local_path))
    return model_paths


def _resolve_base_model_path(config: TrainingConfig) -> Path:
    if config.base_model_path is not None:
        if config.base_model_path.exists():
            return config.base_model_path
        raise FileNotFoundError(f"Missing base model path: {config.base_model_path}")

    manifest_model_paths = _load_download_manifest(config.output_root)
    manifest_path = manifest_model_paths.get(config.candidate_id)
    if manifest_path is not None and manifest_path.exists():
        return manifest_path

    fallback_path = config.output_root / "base" / config.candidate_id
    if fallback_path.exists():
        return fallback_path

    raise FileNotFoundError(
        f"Missing base model for candidate_id={config.candidate_id}. "
        f"Expected {config.output_root / 'manifests' / 'download-manifest.json'} or {fallback_path}"
    )


def _import_training_stack() -> tuple[Any, Any, Any]:
    modules: dict[str, Any] = {}
    missing_modules: list[str] = []
    for module_name in ("torch", "transformers", "peft", "accelerate"):
        try:
            modules[module_name] = importlib.import_module(module_name)
        except ImportError:
            missing_modules.append(module_name)

    if missing_modules:
        missing = ", ".join(missing_modules)
        raise RuntimeError(
            f"Missing training dependencies: {missing}. "
            "Install them with python -m pip install -e .[dev,train]"
        )
    return modules["torch"], modules["transformers"], modules["peft"]


def _resolve_device(torch_module: Any, requested_device: str) -> str:
    if requested_device == "auto":
        return "cuda" if torch_module.cuda.is_available() else "cpu"
    if requested_device == "cuda" and not torch_module.cuda.is_available():
        raise RuntimeError("CUDA was requested for training, but torch.cuda.is_available() is false")
    if requested_device not in {"cpu", "cuda"}:
        raise ValueError("device must be one of: auto, cpu, cuda")
    return requested_device


def _validate_qwen_training_device(identity: ExperimentIdentity, device: str) -> None:
    if identity.adaptation_mode == AdaptationMode.QLORA and device != "cuda":
        raise RuntimeError("QLoRA requires the resolved training device to be CUDA")


def _resolve_torch_dtype(torch_module: Any, device: str) -> Any:
    if device == "cuda":
        return torch_module.bfloat16 if torch_module.cuda.is_bf16_supported() else torch_module.float16
    return torch_module.float32


def _load_pinned_qwen_base_components(
    *,
    transformers_module: Any,
    torch_module: Any,
    config: TrainingConfig,
    base_model_path: Path,
    device: str,
    quantization_config: Any | None,
) -> tuple[Any, Any]:
    """Load only the verified local bytes while retaining the pinned HF revision argument."""

    tokenizer = transformers_module.AutoTokenizer.from_pretrained(
        str(base_model_path),
        revision=config.model_revision,
        local_files_only=config.local_files_only,
        trust_remote_code=config.trust_remote_code,
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token or tokenizer.unk_token
    tokenizer.padding_side = "right"

    model_load_kwargs: dict[str, Any] = {
        "revision": config.model_revision,
        "local_files_only": config.local_files_only,
        "trust_remote_code": config.trust_remote_code,
        "low_cpu_mem_usage": True,
    }
    if quantization_config is not None:
        model_load_kwargs["quantization_config"] = quantization_config
        model_load_kwargs["device_map"] = {"": 0}
    else:
        model_load_kwargs["torch_dtype"] = _resolve_torch_dtype(torch_module, device)
    model = transformers_module.AutoModelForCausalLM.from_pretrained(
        str(base_model_path),
        **model_load_kwargs,
    )
    return tokenizer, model


def _collect_qwen_preload_capabilities(
    torch_module: Any,
    transformers_module: Any,
    peft_module: Any,
    identity: ExperimentIdentity,
) -> tuple[QwenPreloadCapabilities, Any | None]:
    """Inspect mode capabilities without loading a model or creating outputs."""

    cuda_available = bool(torch_module.cuda.is_available())
    if identity.adaptation_mode == AdaptationMode.LORA:
        return (
            QwenPreloadCapabilities(
                cuda_available=cuda_available,
                bitsandbytes_imported=False,
                bitsandbytes_version=None,
                bitsandbytes_config_available=False,
                linear4bit_type=None,
                kbit_preparation_available=False,
            ),
            None,
        )

    try:
        bitsandbytes_module = importlib.import_module("bitsandbytes")
    except ImportError:
        bitsandbytes_module = None
    linear4bit_type = None
    if bitsandbytes_module is not None:
        linear4bit_type = getattr(getattr(bitsandbytes_module, "nn", None), "Linear4bit", None)
    capabilities = QwenPreloadCapabilities(
        cuda_available=cuda_available,
        bitsandbytes_imported=bitsandbytes_module is not None,
        bitsandbytes_version=(
            str(getattr(bitsandbytes_module, "__version__", ""))
            if bitsandbytes_module is not None
            else None
        ),
        bitsandbytes_config_available=hasattr(transformers_module, "BitsAndBytesConfig"),
        linear4bit_type=linear4bit_type,
        kbit_preparation_available=hasattr(peft_module, "prepare_model_for_kbit_training"),
    )
    return capabilities, bitsandbytes_module


def _build_quantization_config(
    transformers_module: Any,
    torch_module: Any,
    config: TrainingConfig,
    device: str,
) -> Any | None:
    if config.adaptation_mode == AdaptationMode.LORA:
        return None
    compute_dtype = _resolve_torch_dtype(torch_module, device)
    return transformers_module.BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=compute_dtype,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
    )


def _run_adapter_gradient_probe(
    model: Any,
    tokenized_item: dict[str, Sequence[int]],
    *,
    torch_module: Any,
) -> tuple[AdapterGradientCheck, ...]:
    """Run one non-optimizing micro-batch and inspect adapter gradients."""

    encoded = {
        key: torch_module.tensor([list(value)], dtype=torch_module.long)
        for key, value in tokenized_item.items()
    }
    trainable_parameters = [
        parameter
        for name, parameter in model.named_parameters()
        if parameter.requires_grad and "lora_" in name.casefold()
    ]
    if not trainable_parameters:
        raise RuntimeError("QLoRA gradient proof found no adapter trainable parameters")
    device = getattr(trainable_parameters[0], "device", None)
    batch = {
        key: value.to(device) if device is not None and hasattr(value, "to") else value
        for key, value in encoded.items()
    }
    was_training = getattr(model, "training", True)
    if hasattr(model, "train"):
        model.train()
    if hasattr(model, "zero_grad"):
        model.zero_grad(set_to_none=True)
    try:
        # The tokenized item already carries the response-only labels. Passing a
        # second labels keyword would fail on real models; replacing them with
        # input_ids would silently prove gradients under whole-sequence loss.
        outputs = model(**batch)
        loss = getattr(outputs, "loss", outputs[0] if isinstance(outputs, (tuple, list)) else None)
        if loss is None or not bool(torch_module.isfinite(loss.detach()).all().item()):
            raise RuntimeError("QLoRA gradient-proof loss is missing or non-finite")
        loss.backward()
        checks: list[AdapterGradientCheck] = []
        for name, parameter in model.named_parameters():
            if not parameter.requires_grad or "lora_" not in name.casefold():
                continue
            gradient = getattr(parameter, "grad", None)
            checks.append(
                AdapterGradientCheck(
                    parameter_name=name,
                    is_finite=(
                        gradient is not None
                        and bool(torch_module.isfinite(gradient.detach()).all().item())
                    ),
                    is_nonzero=(
                        gradient is not None
                        and bool(torch_module.count_nonzero(gradient.detach()).item())
                    ),
                )
            )
        return tuple(checks)
    finally:
        if hasattr(model, "zero_grad"):
            model.zero_grad(set_to_none=True)
        if hasattr(model, "train"):
            model.train(was_training)


def _require_quantization_proof(
    config: TrainingConfig,
    value: object,
) -> QuantizationProof:
    if not isinstance(value, QuantizationProof):
        raise RuntimeError("trainer result is missing a complete quantization proof")
    if value.requested_mode != config.adaptation_mode:
        raise RuntimeError("quantization proof requested mode does not match TrainingConfig")
    expected_resolved = (
        ResolvedQwenMode.FOUR_BIT_QLORA
        if config.adaptation_mode == AdaptationMode.QLORA
        else ResolvedQwenMode.FULL_PRECISION_LORA
    )
    if value.resolved_mode != expected_resolved:
        raise RuntimeError("quantization proof resolved mode does not match TrainingConfig")
    return value


def _planned_optimizer_steps(config: TrainingConfig, train_examples: int) -> int:
    if train_examples <= 0:
        raise ValueError("Phase 40 training requires at least one training example")
    if config.planned_full_optimizer_steps_override is not None:
        return config.planned_full_optimizer_steps_override
    if config.max_steps > 0:
        return config.max_steps
    steps_per_epoch = math.ceil(
        train_examples
        / (config.per_device_train_batch_size * config.gradient_accumulation_steps)
    )
    return max(1, math.ceil(steps_per_epoch * config.num_train_epochs))


def _generation_steps(*, planned_optimizer_steps: int, cadence_steps: int) -> tuple[int, ...]:
    if planned_optimizer_steps <= 0 or cadence_steps <= 0:
        raise ValueError("Phase 40 generation cadence requires positive steps")
    steps = list(range(cadence_steps, planned_optimizer_steps + 1, cadence_steps))
    if not steps or steps[-1] != planned_optimizer_steps:
        steps.append(planned_optimizer_steps)
    return tuple(steps)


def _accelerator_identity(torch_module: Any, device: str) -> AcceleratorIdentity:
    if device != "cuda":
        return AcceleratorIdentity(
            accelerator_type="cpu",
            accelerator_name="cpu",
            compute_capability=None,
            total_memory_bytes=0,
        )
    cuda = torch_module.cuda
    properties = cuda.get_device_properties(0)
    capability = cuda.get_device_capability(0)
    return AcceleratorIdentity(
        accelerator_type="cuda",
        accelerator_name=str(cuda.get_device_name(0)),
        compute_capability=f"{int(capability[0])}.{int(capability[1])}",
        total_memory_bytes=int(properties.total_memory),
    )


def _adapter_compute_dtype(model: Any) -> str:
    for _, parameter in model.named_parameters():
        if getattr(parameter, "requires_grad", False):
            value = str(getattr(parameter, "dtype", "unknown"))
            return value.removeprefix("torch.")
    raise RuntimeError("Phase 40 model has no trainable adapter parameter dtype")


def _build_resume_controlled_config(
    config: TrainingConfig,
    *,
    data_contract: Phase40DataContract,
    formatter_sha256: str,
    quantization_proof: QuantizationProof,
    planned_optimizer_steps: int,
    model: Any,
    torch_module: Any,
    device: str,
    use_bf16: bool,
) -> ResumeControlledConfig:
    """Freeze every field that may affect a restarted full Qwen run."""

    if config.run_kind != RunKind.FULL:
        raise ValueError("resume-controlled configs describe full runs only")
    if not re.fullmatch(r"[0-9a-f]{64}", formatter_sha256):
        raise ValueError("formatter_sha256 must be a lowercase SHA-256")
    splits = tuple(
        CanonicalSplitEvidence(
            logical_name=logical_name,
            relative_path=snapshot.identity.relative_path.replace("\\", "/"),
            records=snapshot.identity.records,
            bytes=snapshot.identity.bytes,
            sha256=snapshot.whole_file_sha256,
            ordered_row_ids_sha256=_snapshot_row_id_digest(snapshot),
        )
        for logical_name, snapshot in (
            ("train", data_contract.train_snapshot),
            ("val", data_contract.validation_snapshot),
        )
    )
    precision = PrecisionControls(
        compute_dtype=("bfloat16" if use_bf16 else "float16" if device == "cuda" else "float32"),
        adapter_dtype=_adapter_compute_dtype(model),
        bf16=use_bf16,
        fp16=device == "cuda" and not use_bf16,
        tf32=config.tf32,
    )
    additional_controls = [
        NamedControl(name="local_files_only", value=config.local_files_only),
        NamedControl(name="report_to", value="none"),
        NamedControl(name="save_safetensors", value=True),
        NamedControl(name="trust_remote_code", value=config.trust_remote_code),
    ]
    if config.transfer_authority is not None:
        additional_controls.extend(
            (
                NamedControl(
                    name="input_archive_sha256",
                    value=config.transfer_authority.input_archive_sha256,
                ),
                NamedControl(
                    name="input_manifest_sha256",
                    value=config.transfer_authority.input_manifest_sha256,
                ),
                NamedControl(
                    name="source_archive_sha256",
                    value=config.transfer_authority.source_archive_sha256,
                ),
                NamedControl(
                    name="source_inventory_sha256",
                    value=config.transfer_authority.source_inventory_sha256,
                ),
            )
        )
    return ResumeControlledConfig(
        schema_version="phase40-resume-controlled-config-v1",
        experiment_identity=ExperimentIdentityEvidence(
            model_family=ModelFamily.QWEN,
            adaptation_mode=config.adaptation_mode,
            run_kind=RunKind.FULL,
        ),
        model_id=_resolved_model_id(config),
        model_revision=config.model_revision,
        splits=splits,
        formatter_or_preprocessor_sha256=formatter_sha256,
        response_mask_or_preprocessor_version=PHASE40_RESPONSE_MASK_VERSION,
        label_order=tuple(LABEL_ORDER),
        seed=config.seed,
        data_seed=config.data_seed,
        max_sequence_length=config.max_seq_length,
        truncation_policy="reject-over-max",
        per_device_train_batch_size=config.per_device_train_batch_size,
        gradient_accumulation_steps=config.gradient_accumulation_steps,
        world_size=1,
        effective_batch_size=(
            config.per_device_train_batch_size * config.gradient_accumulation_steps
        ),
        num_train_epochs=config.num_train_epochs,
        max_optimizer_steps=planned_optimizer_steps,
        gradient_checkpointing=config.gradient_checkpointing,
        lora_rank=config.lora_r,
        lora_alpha=config.lora_alpha,
        lora_dropout=config.lora_dropout,
        lora_bias=config.lora_bias,
        target_modules=config.target_modules,
        task_type="CAUSAL_LM",
        optimizer=OptimizerControls(
            optimizer=config.optimizer_name,
            learning_rate=config.learning_rate,
            weight_decay=config.weight_decay,
            lr_scheduler_type=config.lr_scheduler_type,
            warmup_steps=config.warmup_steps,
            warmup_ratio=config.warmup_ratio,
            max_grad_norm=config.max_grad_norm,
        ),
        precision=precision,
        cadence=CadenceControls(
            logging_steps=config.logging_steps,
            evaluation_steps=config.save_steps,
            save_steps=config.save_steps,
            save_total_limit=config.save_total_limit,
            generation_steps=_generation_steps(
                planned_optimizer_steps=planned_optimizer_steps,
                cadence_steps=config.save_steps,
            ),
        ),
        decoder=DecoderContractEvidence(
            schema_version="phase40-qwen-decoder-v1",
            do_sample=False,
            num_return_sequences=1,
            max_new_tokens=256,
            output_schema_version=PHASE40_DECODER_OUTPUT_SCHEMA_VERSION,
            decoder_version=PHASE40_DECODER_VERSION,
            generation_cadence=PHASE40_GENERATION_CADENCE,
            raw_prediction_ordering_policy=PHASE40_PREDICTION_ORDERING_POLICY,
        ),
        checkpoint_selection_policy=PHASE40_CHECKPOINT_SELECTION_POLICY,
        checkpoint_selection_policy_version=PHASE40_CHECKPOINT_SELECTION_POLICY_VERSION,
        snapshot_id_algorithm_version=PHASE40_SNAPSHOT_ID_ALGORITHM_VERSION,
        quantization_proof=QuantizationProofEvidence(**asdict(quantization_proof)),
        accelerator=_accelerator_identity(torch_module, device),
        additional_controls=tuple(sorted(additional_controls, key=lambda item: item.name)),
    )


def _checkpoint_payload_sha256(checkpoint_path: Path) -> str:
    """Hash one checkpoint directory while excluding only its own resume manifest."""

    checkpoint_path = Path(checkpoint_path)
    if not checkpoint_path.is_dir() or checkpoint_path.is_symlink():
        raise ValueError("checkpoint payload must be an existing non-symlink directory")
    files: list[tuple[str, Path]] = []
    for path in checkpoint_path.rglob("*"):
        if path.is_symlink():
            raise ValueError("checkpoint payload must not contain symlinks")
        if not path.is_file():
            continue
        relative = path.relative_to(checkpoint_path).as_posix()
        if relative == PHASE40_RESUME_MANIFEST_NAME:
            continue
        files.append((relative, path))
    if not files:
        raise RuntimeError("checkpoint payload is empty")
    digest = hashlib.sha256(b"phase40-checkpoint-payload-v1\0")
    for relative, path in sorted(files):
        encoded_relative = relative.encode("utf-8")
        digest.update(len(encoded_relative).to_bytes(8, "big"))
        digest.update(encoded_relative)
        digest.update(path.stat().st_size.to_bytes(8, "big"))
        with path.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
    return digest.hexdigest()


def _canonical_json_line(payload: dict[str, Any]) -> bytes:
    return (
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _run_event_prefix_sha256(event_path: Path, event_count: int) -> str:
    if not isinstance(event_count, int) or isinstance(event_count, bool) or event_count <= 0:
        raise ValueError("run-event prefix count must be a positive integer")
    path = Path(event_path)
    if not path.is_file() or path.is_symlink():
        raise RuntimeError("run-event prefix requires a safe existing event log")
    lines = path.read_bytes().splitlines(keepends=True)
    if len(lines) < event_count:
        raise RuntimeError("run-event log is shorter than its checkpoint-sealed prefix")
    return hashlib.sha256(b"".join(lines[:event_count])).hexdigest()


def _validate_qwen_resume_history_envelope(payload: object) -> dict[str, Any]:
    if not isinstance(payload, dict) or set(payload) != {
        "schema_version",
        "candidates",
        "telemetry_state",
    }:
        raise RuntimeError("Qwen resume history has missing or extra fields")
    if payload["schema_version"] != PHASE40_RESUME_HISTORY_SCHEMA_VERSION:
        raise RuntimeError("Qwen resume history schema version is unsupported")
    if not isinstance(payload["candidates"], list) or not payload["candidates"]:
        raise RuntimeError("Qwen resume history omitted its validation candidates")
    telemetry = payload["telemetry_state"]
    if not isinstance(telemetry, dict) or not isinstance(telemetry.get("run_id"), str):
        raise RuntimeError("Qwen resume history omitted its telemetry run identity")
    return payload


def _write_immutable_bytes(path: Path, payload: bytes) -> Path:
    path = Path(path)
    if path.exists():
        if path.is_file() and path.read_bytes() == payload:
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
            raise RuntimeError("immutable temp-file read-back mismatch")
        os.replace(temporary, path)
        if path.read_bytes() != payload:
            raise RuntimeError("immutable output read-back mismatch")
    finally:
        if temporary.exists():
            temporary.unlink()
    return path


def _write_checkpoint_resume_manifest(
    checkpoint_path: Path,
    *,
    checkpoint_step: int,
    controlled_config: ResumeControlledConfig,
    resume_history: Mapping[str, object] | None = None,
    event_path: Path | None = None,
    base_model_snapshot: QwenBaseModelSnapshot | None = None,
) -> Path:
    checkpoint_path = Path(checkpoint_path)
    expected_name = f"checkpoint-{checkpoint_step}"
    if checkpoint_step < 0 or checkpoint_path.name != expected_name:
        raise ValueError("checkpoint path and checkpoint_step identity differ")
    optional_bindings = (resume_history, event_path, base_model_snapshot)
    if any(value is not None for value in optional_bindings) and not all(
        value is not None for value in optional_bindings
    ):
        raise ValueError(
            "checkpoint history, event prefix, and base-model provenance must be sealed together"
        )
    history_sha256: str | None = None
    event_count: int | None = None
    event_prefix_sha256: str | None = None
    model_source: dict[str, Any] | None = None
    if resume_history is not None:
        normalized_history = _validate_qwen_resume_history_envelope(dict(resume_history))
        events = load_run_events(
            Path(event_path),
            expected_run_id=normalized_history["telemetry_state"]["run_id"],
        )
        if (
            events[-1].event_kind != RunEventKind.CHECKPOINT
            or events[-1].optimizer_step != checkpoint_step
        ):
            raise RuntimeError("checkpoint resume history is not aligned to its last run event")
        history_payload = _canonical_json_line(normalized_history)
        history_path = _write_immutable_bytes(
            checkpoint_path / PHASE40_RESUME_HISTORY_NAME,
            history_payload,
        )
        history_sha256 = _sha256_file(history_path)
        # load_run_events already validates sequence integrity.  The raw prefix hash binds the
        # exact bytes that existed when this checkpoint became resumable.
        event_count = len(events)
        event_prefix_sha256 = _run_event_prefix_sha256(Path(event_path), event_count)
        model_source = base_model_snapshot.evidence_payload()
    payload = {
        "schema_version": PHASE40_RESUME_MANIFEST_SCHEMA_VERSION,
        "checkpoint_step": checkpoint_step,
        "resume_digest": compute_resume_digest(controlled_config),
        "controlled_config": controlled_config.model_dump(mode="json"),
        "resume_history_sha256": history_sha256,
        "run_event_count": event_count,
        "run_event_prefix_sha256": event_prefix_sha256,
        "base_model_source": model_source,
        "checkpoint_payload_sha256": _checkpoint_payload_sha256(checkpoint_path),
    }
    return _write_immutable_bytes(
        checkpoint_path / PHASE40_RESUME_MANIFEST_NAME,
        _canonical_json_line(payload),
    )


def _read_checkpoint_resume_manifest(
    checkpoint_path: Path,
    *,
    controlled_config: ResumeControlledConfig,
    event_path: Path | None = None,
    base_model_snapshot: QwenBaseModelSnapshot | None = None,
    require_cumulative_history: bool = False,
) -> dict[str, Any]:
    manifest_path = checkpoint_path / PHASE40_RESUME_MANIFEST_NAME
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise RuntimeError("checkpoint is missing a trusted Phase 40 resume manifest")
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8", errors="strict"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("checkpoint resume manifest is not strict UTF-8 JSON") from exc
    expected_keys = {
        "schema_version",
        "checkpoint_step",
        "resume_digest",
        "controlled_config",
        "resume_history_sha256",
        "run_event_count",
        "run_event_prefix_sha256",
        "base_model_source",
        "checkpoint_payload_sha256",
    }
    if not isinstance(payload, dict) or set(payload) != expected_keys:
        raise RuntimeError("checkpoint resume manifest has missing or extra fields")
    if payload["schema_version"] != PHASE40_RESUME_MANIFEST_SCHEMA_VERSION:
        raise RuntimeError("checkpoint resume manifest schema version is unsupported")
    step_text = checkpoint_path.name.removeprefix("checkpoint-")
    if not step_text.isdigit() or payload["checkpoint_step"] != int(step_text):
        raise RuntimeError("checkpoint resume manifest step does not match its directory")
    try:
        stored_config = ResumeControlledConfig.model_validate_json(
            json.dumps(
                payload["controlled_config"],
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        )
    except Exception as exc:
        raise RuntimeError("checkpoint resume controlled config is invalid") from exc
    stored_digest = compute_resume_digest(stored_config)
    current_digest = compute_resume_digest(controlled_config)
    if payload["resume_digest"] != stored_digest:
        raise RuntimeError("checkpoint resume manifest digest does not match its stored config")
    if stored_digest != current_digest or stored_config != controlled_config:
        raise RuntimeError("checkpoint resume controls are not exactly compatible")
    actual_payload_sha256 = _checkpoint_payload_sha256(checkpoint_path)
    if payload["checkpoint_payload_sha256"] != actual_payload_sha256:
        raise RuntimeError("checkpoint payload SHA-256 does not match its resume manifest")
    history_bindings = (
        payload["resume_history_sha256"],
        payload["run_event_count"],
        payload["run_event_prefix_sha256"],
        payload["base_model_source"],
    )
    if any(value is None for value in history_bindings):
        if any(value is not None for value in history_bindings):
            raise RuntimeError("checkpoint cumulative resume bindings are only partially present")
        if require_cumulative_history:
            raise RuntimeError("checkpoint lacks cumulative validation/telemetry/model history")
    else:
        history_path = checkpoint_path / PHASE40_RESUME_HISTORY_NAME
        if not history_path.is_file() or history_path.is_symlink():
            raise RuntimeError("checkpoint is missing its cumulative Qwen resume history")
        if payload["resume_history_sha256"] != _sha256_file(history_path):
            raise RuntimeError("checkpoint cumulative resume history SHA-256 drifted")
        try:
            history_payload = json.loads(history_path.read_text(encoding="utf-8", errors="strict"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeError("checkpoint cumulative resume history is invalid JSON") from exc
        if history_path.read_bytes() != _canonical_json_line(history_payload):
            raise RuntimeError("checkpoint cumulative resume history is not canonical")
        history_payload = _validate_qwen_resume_history_envelope(history_payload)
        if not isinstance(payload["run_event_count"], int) or isinstance(
            payload["run_event_count"], bool
        ) or payload["run_event_count"] <= 0:
            raise RuntimeError("checkpoint run-event prefix count is invalid")
        if not re.fullmatch(r"[0-9a-f]{64}", str(payload["run_event_prefix_sha256"])):
            raise RuntimeError("checkpoint run-event prefix SHA-256 is invalid")
        if event_path is not None:
            load_run_events(
                Path(event_path),
                expected_run_id=history_payload["telemetry_state"]["run_id"],
            )
            actual_prefix = _run_event_prefix_sha256(
                Path(event_path),
                payload["run_event_count"],
            )
            if payload["run_event_prefix_sha256"] != actual_prefix:
                raise RuntimeError("checkpoint run-event prefix SHA-256 drifted")
        source_payload = _validate_qwen_base_model_evidence_payload(
            payload["base_model_source"]
        )
        if base_model_snapshot is not None and source_payload != base_model_snapshot.evidence_payload():
            raise RuntimeError("checkpoint base-model source differs from the local snapshot")
    trainer_state_path = checkpoint_path / "trainer_state.json"
    if trainer_state_path.is_file():
        try:
            trainer_state = json.loads(trainer_state_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise RuntimeError("checkpoint trainer_state.json is invalid") from exc
        if trainer_state.get("global_step") != payload["checkpoint_step"]:
            raise RuntimeError("checkpoint trainer state step does not match its resume manifest")
    return payload


def _resolve_resume_checkpoint(
    config: TrainingConfig,
    training_output_dir: Path,
    controlled_config: ResumeControlledConfig | None = None,
    *,
    event_path: Path | None = None,
    base_model_snapshot: QwenBaseModelSnapshot | None = None,
) -> Path | None:
    """Resolve only an explicit, contained, exact-compatible full-run checkpoint."""

    if config.run_kind == RunKind.PROBE:
        if config.resume_from_checkpoint is not None:
            raise ValueError("Phase 40 probes cannot accept resume input")
        return None
    if config.resume_from_checkpoint == "latest":
        raise ValueError("lexical 'latest' resume is forbidden; provide one exact checkpoint path")
    checkpoint_dirs = tuple(
        path for path in Path(training_output_dir).glob("checkpoint-*") if path.is_dir()
    )
    if not config.resume_from_checkpoint:
        if checkpoint_dirs:
            raise RuntimeError(
                "fresh full run found existing checkpoints; provide one exact compatible checkpoint "
                "or choose a new run output"
            )
        return None
    if controlled_config is None:
        raise ValueError("exact resume requires a typed ResumeControlledConfig")
    output_root = Path(training_output_dir).resolve(strict=True)
    resume_path = Path(config.resume_from_checkpoint)
    if not resume_path.is_absolute():
        resume_path = Path.cwd() / resume_path
    if not resume_path.is_dir() or resume_path.is_symlink():
        raise FileNotFoundError(f"Missing safe checkpoint directory: {resume_path}")
    resolved = resume_path.resolve(strict=True)
    if resolved.parent != output_root or not re.fullmatch(r"checkpoint-[0-9]+", resolved.name):
        raise ValueError("resume checkpoint must be one direct checkpoint-N child of this full run")
    _read_checkpoint_resume_manifest(
        resolved,
        controlled_config=controlled_config,
        event_path=event_path,
        base_model_snapshot=base_model_snapshot,
        require_cumulative_history=(getattr(config, "transfer_authority", None) is not None),
    )
    return resolved


def _json_ready(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    return value


_CALLBACK_TO_RUN_EVENT_KIND: dict[CallbackEventKind, RunEventKind] = {
    CallbackEventKind.TRAIN_BEGIN: RunEventKind.RUN_START,
    CallbackEventKind.OPTIMIZER_STEP: RunEventKind.STEP_TIMING,
    CallbackEventKind.LOG: RunEventKind.TRAIN_LOG,
    CallbackEventKind.EVALUATION: RunEventKind.EVALUATION,
    CallbackEventKind.CHECKPOINT: RunEventKind.CHECKPOINT,
    CallbackEventKind.TRAIN_END: RunEventKind.RUN_END,
}


def _callback_event_to_run_event(
    event: Phase40CallbackEvent,
    *,
    sequence_offset: int = 0,
) -> RunEvent:
    """Losslessly normalize one callback observation into the append-only schema."""

    if not isinstance(event, Phase40CallbackEvent):
        raise TypeError("callback event conversion requires Phase40CallbackEvent")
    values: dict[str, Any] = dict(event.values)
    values["callback_event_kind"] = event.event_kind.value
    values["run_kind"] = event.run_kind.value
    values["epoch_observed"] = event.epoch is not None
    if event.duration_seconds is not None:
        values["duration_seconds"] = event.duration_seconds
    if event.is_warmup is not None:
        values["is_warmup"] = event.is_warmup
    return RunEvent(
        schema_version="phase40-run-event-v1",
        sequence_id=sequence_offset + event.sequence_id,
        event_kind=_CALLBACK_TO_RUN_EVENT_KIND[event.event_kind],
        timestamp_utc=datetime.fromisoformat(event.timestamp_utc.replace("Z", "+00:00")),
        optimizer_step=event.optimizer_step,
        epoch=0.0 if event.epoch is None else event.epoch,
        trainer_values=values,
        source_run_id=event.source_run_id,
        run_kind=event.run_kind,
    )


def _append_callback_run_event(
    event_path: Path,
    event: Phase40CallbackEvent,
    *,
    sequence_offset: int = 0,
) -> None:
    append_run_event(
        Path(event_path),
        _callback_event_to_run_event(event, sequence_offset=sequence_offset),
    )


def _append_full_run_finalization_events(
    event_path: Path,
    *,
    run_id: str,
    final_step: int,
    final_epoch: float,
    artifact_identity: str,
    artifact_path: Path,
    metrics: Phase40MetricResult,
    deferred_train_end: Phase40CallbackEvent,
) -> None:
    """Close a full attempt only after its actual final candidate has been evaluated."""

    if deferred_train_end.event_kind != CallbackEventKind.TRAIN_END:
        raise RuntimeError("full-run finalization requires the deferred Trainer train_end event")
    if deferred_train_end.source_run_id != run_id or deferred_train_end.run_kind != RunKind.FULL:
        raise RuntimeError("deferred train_end belongs to a different full run")
    if deferred_train_end.optimizer_step != final_step:
        raise RuntimeError("deferred train_end step differs from the actual final candidate")
    if not re.fullmatch(r"adapter-state-sha256:[0-9a-f]{64}", artifact_identity):
        raise RuntimeError("full-run finalization received an invalid adapter identity")
    if any(
        row.artifact_identity != artifact_identity or row.checkpoint_step != final_step
        for row in metrics.prediction_rows
    ):
        raise RuntimeError("final metrics are not tied to the actual final adapter candidate")
    artifact_path = Path(artifact_path)
    if not artifact_path.is_dir() or artifact_path.is_symlink():
        raise RuntimeError("full-run finalization requires the actual final adapter directory")

    existing = load_run_events(Path(event_path), expected_run_id=run_id)
    last_start_index = max(
        index for index, event in enumerate(existing) if event.event_kind == RunEventKind.RUN_START
    )

    def append_bound(kind: RunEventKind, values: Mapping[str, Any]) -> None:
        current = load_run_events(Path(event_path), expected_run_id=run_id)
        append_run_event(
            Path(event_path),
            RunEvent(
                schema_version="phase40-run-event-v1",
                sequence_id=len(current),
                event_kind=kind,
                timestamp_utc=datetime.now(timezone.utc),
                optimizer_step=final_step,
                epoch=final_epoch,
                trainer_values=dict(values),
                source_run_id=run_id,
                run_kind=RunKind.FULL,
            ),
        )

    has_attempt_training_observation = any(
        index > last_start_index
        and event.event_kind in {RunEventKind.TRAIN_LOG, RunEventKind.STEP_TIMING}
        for index, event in enumerate(existing)
    )
    if not has_attempt_training_observation:
        append_bound(
            RunEventKind.TRAIN_LOG,
            {
                "finalization_only": True,
                "optimizer_steps_executed_in_attempt": 0,
                "resume_no_optimizer_work": True,
            },
        )
    metric_sha256 = hashlib.sha256(
        _canonical_json_line(_json_ready(asdict(metrics)))
    ).hexdigest()
    append_bound(
        RunEventKind.EVALUATION,
        {
            "artifact_identity": artifact_identity,
            "evaluation_scope": "actual-final-candidate",
            "evaluated_rows": metrics.evaluated_rows,
            "invalid_output_count": metrics.invalid_output_count,
            "macro_f1": metrics.macro_f1,
            "metrics_sha256": metric_sha256,
        },
    )
    append_bound(
        RunEventKind.CHECKPOINT,
        {
            "artifact_identity": artifact_identity,
            "artifact_payload_sha256": build_model_checksum(artifact_path),
            "artifact_scope": "final-adapter",
            "checkpoint_step": final_step,
            "metrics_sha256": metric_sha256,
        },
    )
    train_end_values = dict(deferred_train_end.values)
    train_end_values.update(
        {
            "actual_final_artifact_identity": artifact_identity,
            "callback_event_kind": CallbackEventKind.TRAIN_END.value,
            "duration_seconds": deferred_train_end.duration_seconds,
            "epoch_observed": deferred_train_end.epoch is not None,
            "run_kind": RunKind.FULL.value,
        }
    )
    append_bound(RunEventKind.RUN_END, train_end_values)


def _append_runtime_failure_event(
    event_path: Path,
    *,
    run_id: str,
    run_kind: RunKind,
    requested_mode: AdaptationMode,
    error: BaseException,
    resource_state: Mapping[str, object] | None = None,
) -> None:
    """Retain a sanitized failure marker after any already-appended raw events."""

    event_path = Path(event_path)
    existing = load_run_events(event_path, expected_run_id=run_id) if event_path.exists() else ()
    failure_category = (
        "interrupted"
        if isinstance(error, (KeyboardInterrupt, SystemExit))
        else "out_of_memory"
        if isinstance(error, MemoryError) or "out of memory" in str(error).casefold()
        else "runtime_failure"
    )
    resource_payload = None if resource_state is None else dict(resource_state)
    resource_sha256 = (
        None
        if resource_payload is None
        else hashlib.sha256(_canonical_json_line(resource_payload)).hexdigest()
    )
    append_run_event(
        event_path,
        RunEvent(
            schema_version="phase40-run-event-v1",
            sequence_id=len(existing),
            event_kind=RunEventKind.FAILURE,
            timestamp_utc=datetime.now(timezone.utc),
            optimizer_step=existing[-1].optimizer_step if existing else 0,
            epoch=existing[-1].epoch if existing else 0.0,
            trainer_values={
                "error_type": type(error).__name__,
                "failure_category": failure_category,
                "requested_adaptation_mode": requested_mode.value,
                "resource_state": resource_payload,
                "resource_state_sha256": resource_sha256,
            },
            source_run_id=run_id,
            run_kind=run_kind,
        ),
    )


def _append_post_train_finalization_failure(
    event_path: Path,
    *,
    run_id: str,
    requested_mode: AdaptationMode,
    error: BaseException,
    resource_state: Mapping[str, object],
) -> None:
    """Terminate a failed artifact/evidence transaction after Trainer ended cleanly."""

    state = _validated_callback_resume_state(dict(resource_state))
    state_sha256 = hashlib.sha256(_canonical_json_line(state)).hexdigest()
    existing = load_run_events(Path(event_path), expected_run_id=run_id)
    if existing[-1].event_kind in {RunEventKind.FAILURE, RunEventKind.RUN_END}:
        raise RuntimeError("post-train finalization cannot terminate an already terminal event log")
    append_run_event(
        Path(event_path),
        RunEvent(
            schema_version="phase40-run-event-v1",
            sequence_id=len(existing),
            event_kind=RunEventKind.RESOURCE,
            timestamp_utc=datetime.now(timezone.utc),
            optimizer_step=existing[-1].optimizer_step,
            epoch=existing[-1].epoch,
            trainer_values={
                "measurement_scope": "completed-trainer-before-finalization-failure",
                "resource_state": state,
                "resource_state_sha256": state_sha256,
            },
            source_run_id=run_id,
            run_kind=RunKind.FULL,
        ),
    )
    _append_runtime_failure_event(
        event_path,
        run_id=run_id,
        run_kind=RunKind.FULL,
        requested_mode=requested_mode,
        error=error,
        resource_state=state,
    )


def _run_post_train_finalization_transaction(
    finalizer: Callable[[], dict[str, Any]],
    *,
    event_path: Path,
    run_id: str,
    requested_mode: AdaptationMode,
    resource_state: Mapping[str, object] | Callable[[], Mapping[str, object]],
    failure_resource_state_provider: Callable[[], Mapping[str, object]] | None = None,
) -> dict[str, Any]:
    """Run all post-Trainer work behind one append-only terminal failure boundary."""

    try:
        resolved_resource_state = _validated_callback_resume_state(
            dict(resource_state() if callable(resource_state) else resource_state)
        )
    except BaseException as exc:
        fallback_state: Mapping[str, object] | None = None
        if failure_resource_state_provider is not None:
            try:
                fallback_state = _validated_callback_resume_state(
                    dict(failure_resource_state_provider())
                )
            except BaseException:
                fallback_state = None
        _append_runtime_failure_event(
            event_path,
            run_id=run_id,
            run_kind=RunKind.FULL,
            requested_mode=requested_mode,
            error=exc,
            resource_state=fallback_state,
        )
        raise

    try:
        return finalizer()
    except BaseException as exc:
        _append_post_train_finalization_failure(
            event_path,
            run_id=run_id,
            requested_mode=requested_mode,
            error=exc,
            resource_state=resolved_resource_state,
        )
        raise


def _validated_callback_resume_state(payload: object) -> dict[str, object]:
    if not isinstance(payload, dict):
        raise RuntimeError("failed-attempt resource state must be a JSON object")
    try:
        Phase40EvidenceCallback(
            run_id=payload["run_id"],
            run_kind=payload["run_kind"],
            warmup_optimizer_steps=payload["warmup_optimizer_steps"],
            examples_per_optimizer_step=payload["examples_per_optimizer_step"],
            planned_full_optimizer_steps=payload["planned_full_optimizer_steps"],
            resume_state=payload,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise RuntimeError("failed-attempt resource state is invalid") from exc
    return payload


def _require_resource_state_extension(
    previous: Mapping[str, object],
    current: Mapping[str, object],
) -> None:
    identity_fields = (
        "schema_version",
        "run_id",
        "run_kind",
        "warmup_optimizer_steps",
        "examples_per_optimizer_step",
        "planned_full_optimizer_steps",
    )
    if any(current[name] != previous[name] for name in identity_fields):
        raise RuntimeError("failed-attempt resource state belongs to incompatible controls")
    for field_name in (
        "retained_step_seconds",
        "evaluation_overhead_seconds",
        "checkpoint_overhead_seconds",
    ):
        prior_values = previous[field_name]
        current_values = current[field_name]
        if not isinstance(prior_values, list) or not isinstance(current_values, list):
            raise RuntimeError("failed-attempt resource histories must be arrays")
        if current_values[: len(prior_values)] != prior_values:
            raise RuntimeError("failed-attempt resource history overwrote its checkpoint prefix")
    for field_name in (
        "observed_optimizer_steps",
        "retained_examples",
        "retained_tokens",
        "unmeasured_evaluations",
        "unmeasured_checkpoints",
        "peak_allocated_bytes",
        "peak_reserved_bytes",
        "actual_wall_seconds",
    ):
        if current[field_name] < previous[field_name]:
            raise RuntimeError("failed-attempt resource counters moved backward")


def _resume_state_with_failed_suffix(
    checkpoint_state: Mapping[str, object],
    *,
    event_path: Path,
    checkpoint_event_count: int,
) -> Mapping[str, object]:
    """Incorporate append-only failed work after a sealed checkpoint without replacing it."""

    base = _validated_callback_resume_state(dict(checkpoint_state))
    events = load_run_events(Path(event_path), expected_run_id=str(base["run_id"]))
    suffix = events[checkpoint_event_count:]
    if not suffix:
        return base
    if suffix[-1].event_kind != RunEventKind.FAILURE:
        raise RuntimeError("post-checkpoint event suffix lacks a terminal failure/interruption")
    if any(event.event_kind == RunEventKind.RUN_END for event in suffix):
        raise RuntimeError("completed post-checkpoint event suffix cannot be resumed")
    for index, event in enumerate(suffix):
        if event.event_kind == RunEventKind.RUN_START and index > 0:
            if suffix[index - 1].event_kind != RunEventKind.FAILURE:
                raise RuntimeError("post-checkpoint resume attempt lacks a terminal failure boundary")
        if (
            event.event_kind == RunEventKind.RESOURCE
            and event.trainer_values.get("measurement_scope")
            == "completed-trainer-before-finalization-failure"
        ):
            if index + 1 >= len(suffix) or suffix[index + 1].event_kind != RunEventKind.FAILURE:
                raise RuntimeError("post-train resource evidence is not bound to its failure")
            resource_state = _validated_callback_resume_state(
                event.trainer_values.get("resource_state")
            )
            resource_sha256 = event.trainer_values.get("resource_state_sha256")
            expected_sha256 = hashlib.sha256(_canonical_json_line(resource_state)).hexdigest()
            if resource_sha256 != expected_sha256:
                raise RuntimeError("post-train resource state SHA-256 drifted")
            failure_values = suffix[index + 1].trainer_values
            if (
                failure_values.get("resource_state") != resource_state
                or failure_values.get("resource_state_sha256") != expected_sha256
            ):
                raise RuntimeError("post-train resource evidence differs from its failure")

    previous: Mapping[str, object] = base
    failure_states: list[dict[str, object]] = []
    for event in suffix:
        if event.event_kind != RunEventKind.FAILURE:
            continue
        resource_state = event.trainer_values.get("resource_state")
        resource_sha256 = event.trainer_values.get("resource_state_sha256")
        current = _validated_callback_resume_state(resource_state)
        if (
            not isinstance(resource_sha256, str)
            or resource_sha256
            != hashlib.sha256(_canonical_json_line(current)).hexdigest()
        ):
            raise RuntimeError("failed-attempt resource state SHA-256 drifted")
        _require_resource_state_extension(previous, current)
        previous = current
        failure_states.append(current)
    if not failure_states:
        raise RuntimeError("post-checkpoint failure omitted resource evidence")
    cumulative = failure_states[-1]

    step_events = [event for event in suffix if event.event_kind == RunEventKind.STEP_TIMING]
    retained_step_events = [
        event for event in step_events if event.trainer_values.get("is_warmup") is False
    ]
    base_durations = base["retained_step_seconds"]
    expected_durations = cumulative["retained_step_seconds"][len(base_durations) :]
    actual_durations = [event.trainer_values.get("duration_seconds") for event in retained_step_events]
    if expected_durations != actual_durations:
        raise RuntimeError("failed-attempt step timing history differs from append-only events")
    if cumulative["observed_optimizer_steps"] - base["observed_optimizer_steps"] != len(
        step_events
    ):
        raise RuntimeError("failed-attempt completed-step count differs from append-only events")
    expected_examples = sum(
        int(event.trainer_values.get("examples", 0)) for event in retained_step_events
    )
    if cumulative["retained_examples"] - base["retained_examples"] != expected_examples:
        raise RuntimeError("failed-attempt example count differs from append-only events")
    expected_tokens = sum(
        int(event.trainer_values.get("tokens", 0) or 0) for event in retained_step_events
    )
    if cumulative["retained_tokens"] - base["retained_tokens"] != expected_tokens:
        raise RuntimeError("failed-attempt token count differs from append-only events")

    for event_kind, state_field in (
        (RunEventKind.EVALUATION, "evaluation_overhead_seconds"),
        (RunEventKind.CHECKPOINT, "checkpoint_overhead_seconds"),
    ):
        appended = cumulative[state_field][len(base[state_field]) :]
        observed = [
            event.trainer_values.get("duration_seconds")
            for event in suffix
            if event.event_kind == event_kind
            and event.trainer_values.get("duration_seconds") is not None
        ]
        if appended != observed:
            raise RuntimeError("failed-attempt overhead history differs from append-only events")
    return cumulative


def _install_measured_checkpoint_wrapper(
    trainer: Any,
    *,
    training_output_dir: Path,
    controlled_config: ResumeControlledConfig | None,
    cuda_timing: Any,
    clock: Callable[[], float] = time.perf_counter,
    checkpoint_durations: list[float] | None = None,
) -> list[float]:
    """Measure only Trainer checkpoint I/O and seal full-run resume manifests."""

    original = getattr(trainer, "_save_checkpoint", None)
    if not callable(original):
        raise RuntimeError("Trainer lacks the checkpoint hook required for isolated timing")
    durations = checkpoint_durations if checkpoint_durations is not None else []

    def measured_save_checkpoint(*args: Any, **kwargs: Any) -> Any:
        cuda_timing.synchronize()
        started = float(clock())
        result = original(*args, **kwargs)
        cuda_timing.synchronize()
        duration = float(clock()) - started
        if not math.isfinite(duration) or duration < 0:
            raise RuntimeError("isolated checkpoint duration must be finite and non-negative")
        step = int(getattr(getattr(trainer, "state", None), "global_step", -1))
        checkpoint_path = Path(training_output_dir) / f"checkpoint-{step}"
        if controlled_config is not None:
            _write_checkpoint_resume_manifest(
                checkpoint_path,
                checkpoint_step=step,
                controlled_config=controlled_config,
            )
        durations.append(duration)
        return result

    trainer._save_checkpoint = measured_save_checkpoint
    return durations


def _build_phase40_runtime_callback(
    transformers_module: Any,
    *,
    evidence_callback: Phase40EvidenceCallback,
    checkpoint_durations: list[float],
    validation_recorder: Phase40ValidationRecorder | None,
    checkpoint_manifest_sealer: Callable[[Path, Mapping[str, object]], Path] | None = None,
    controller_stop_request_path: Path | None = None,
) -> Any:
    """Forward Trainer events unchanged while binding isolated save timing."""

    callback_base = getattr(transformers_module, "TrainerCallback", object)

    class _RuntimeCallback(callback_base):
        def on_train_begin(self, args, state, control, **kwargs):  # noqa: ANN001
            return evidence_callback.on_train_begin(args, state, control, **kwargs)

        def on_step_begin(self, args, state, control, **kwargs):  # noqa: ANN001
            return evidence_callback.on_step_begin(args, state, control, **kwargs)

        def on_step_end(self, args, state, control, **kwargs):  # noqa: ANN001
            result = evidence_callback.on_step_end(args, state, control, **kwargs)
            if controller_stop_request_path is not None:
                stop_path = Path(controller_stop_request_path)
                if stop_path.is_symlink():
                    raise RuntimeError("controller stop request must not be a symlink")
                if stop_path.is_file():
                    setattr(result, "should_training_stop", True)
            return result

        def on_log(self, args, state, control, logs=None, **kwargs):  # noqa: ANN001
            return evidence_callback.on_log(args, state, control, logs=logs, **kwargs)

        def on_evaluate(self, args, state, control, metrics=None, **kwargs):  # noqa: ANN001
            return evidence_callback.on_evaluate(
                args,
                state,
                control,
                metrics=metrics,
                **kwargs,
            )

        def on_save(self, args, state, control, model=None, **kwargs):  # noqa: ANN001
            if not checkpoint_durations:
                raise RuntimeError("Trainer on_save lacks its isolated checkpoint timing")
            duration = checkpoint_durations.pop(0)
            evidence_callback.on_save(
                args,
                state,
                control,
                checkpoint_runtime_seconds=duration,
                **kwargs,
            )
            if validation_recorder is not None:
                if model is None:
                    raise RuntimeError("Trainer on_save did not provide the checkpoint model")
                validation_recorder.record_saved_checkpoint(
                    model=model,
                    checkpoint_step=int(state.global_step),
                )
            if checkpoint_manifest_sealer is not None:
                if validation_recorder is None:
                    raise RuntimeError("checkpoint history sealer requires validation evidence")
                checkpoint_path = (
                    validation_recorder.training_output_dir
                    / f"checkpoint-{int(state.global_step)}"
                )
                checkpoint_manifest_sealer(
                    checkpoint_path,
                    evidence_callback.checkpoint_state(),
                )
            return control

        def on_train_end(self, args, state, control, **kwargs):  # noqa: ANN001
            if checkpoint_durations:
                raise RuntimeError("checkpoint timing was not paired with Trainer on_save")
            return evidence_callback.on_train_end(args, state, control, **kwargs)

    return _RuntimeCallback()


def _build_training_arguments(
    transformers_module: Any,
    config: TrainingConfig,
    training_output_dir: Path,
    *,
    has_eval_data: bool,
    device: str,
    use_bf16: bool,
) -> Any:
    parameter_names = set(inspect.signature(transformers_module.TrainingArguments.__init__).parameters)
    training_kwargs: dict[str, Any] = {
        "output_dir": str(training_output_dir),
        "num_train_epochs": config.num_train_epochs,
        "max_steps": config.max_steps,
        "per_device_train_batch_size": config.per_device_train_batch_size,
        "per_device_eval_batch_size": 1,
        "gradient_accumulation_steps": config.gradient_accumulation_steps,
        "learning_rate": config.learning_rate,
        "logging_steps": config.logging_steps,
        "save_steps": config.save_steps,
        "save_total_limit": config.save_total_limit,
        "eval_steps": config.save_steps if has_eval_data else None,
        "remove_unused_columns": False,
        "report_to": [],
        "logging_first_step": True,
        "save_safetensors": True,
        "dataloader_pin_memory": device == "cuda",
        "dataloader_num_workers": config.dataloader_num_workers,
        "fp16": device == "cuda" and not use_bf16,
        "bf16": use_bf16,
        "gradient_checkpointing": config.gradient_checkpointing,
        "seed": config.seed,
        "data_seed": config.data_seed,
        "optim": config.optimizer_name,
        "weight_decay": config.weight_decay,
        "lr_scheduler_type": config.lr_scheduler_type,
        "warmup_steps": config.warmup_steps,
        "warmup_ratio": config.warmup_ratio,
        "max_grad_norm": config.max_grad_norm,
        "tf32": config.tf32,
        "include_num_input_tokens_seen": True,
        "logging_strategy": "steps",
        "save_strategy": "steps",
    }
    if "eval_strategy" in parameter_names:
        training_kwargs["eval_strategy"] = "steps" if has_eval_data else "no"
    elif "evaluation_strategy" in parameter_names:
        training_kwargs["evaluation_strategy"] = "steps" if has_eval_data else "no"

    if "use_cpu" in parameter_names:
        training_kwargs["use_cpu"] = device == "cpu"
    elif "no_cuda" in parameter_names:
        training_kwargs["no_cuda"] = device == "cpu"

    if "overwrite_output_dir" in parameter_names:
        training_kwargs["overwrite_output_dir"] = False

    supported_kwargs = {
        key: value
        for key, value in training_kwargs.items()
        if key in parameter_names and value is not None
    }
    return transformers_module.TrainingArguments(**supported_kwargs)


def _control_value(value: Any) -> Any:
    return getattr(value, "value", value)


def _verify_training_argument_controls(
    training_args: Any,
    config: TrainingConfig,
    *,
    device: str,
    use_bf16: bool,
) -> None:
    """Reject a Trainer version that did not retain the frozen run controls."""

    expected = {
        "max_steps": config.max_steps,
        "per_device_train_batch_size": config.per_device_train_batch_size,
        "gradient_accumulation_steps": config.gradient_accumulation_steps,
        "learning_rate": config.learning_rate,
        "logging_steps": config.logging_steps,
        "save_steps": config.save_steps,
        "save_total_limit": config.save_total_limit,
        "eval_steps": config.save_steps,
        "seed": config.seed,
        "data_seed": config.data_seed,
        "optim": config.optimizer_name,
        "weight_decay": config.weight_decay,
        "lr_scheduler_type": config.lr_scheduler_type,
        "warmup_steps": config.warmup_steps,
        "warmup_ratio": config.warmup_ratio,
        "max_grad_norm": config.max_grad_norm,
        "tf32": config.tf32,
        "fp16": device == "cuda" and not use_bf16,
        "bf16": use_bf16,
        "gradient_checkpointing": config.gradient_checkpointing,
        "include_num_input_tokens_seen": True,
        "logging_strategy": "steps",
        "save_strategy": "steps",
    }
    for name, expected_value in expected.items():
        if not hasattr(training_args, name):
            raise RuntimeError(f"TrainingArguments omitted required Phase 40 control: {name}")
        actual = _control_value(getattr(training_args, name))
        if actual != expected_value:
            raise RuntimeError(
                f"TrainingArguments changed required Phase 40 control {name}: "
                f"expected {expected_value!r}, got {actual!r}"
            )
    evaluation_strategy = getattr(
        training_args,
        "eval_strategy",
        getattr(training_args, "evaluation_strategy", None),
    )
    if _control_value(evaluation_strategy) != "steps":
        raise RuntimeError("TrainingArguments must preserve step-based validation cadence")
    if int(getattr(training_args, "world_size", 1)) != 1:
        raise RuntimeError("Phase 40 evidence contract supports one training process only")
    if config.local_decision and int(
        getattr(training_args, "dataloader_num_workers", -1)
    ) != 0:
        raise RuntimeError("local decision data-loader workers must remain zero")


def _copy_directory_immutable(source: Path, target: Path) -> Path:
    source = Path(source)
    target = Path(target)
    if not source.is_dir() or source.is_symlink():
        raise ValueError("model artifact source must be an existing non-symlink directory")
    if any(path.is_symlink() for path in source.rglob("*")):
        raise ValueError("model artifact source must not contain symlinks")
    source_sha256 = build_model_checksum(source)
    if target.exists():
        if target.is_dir() and not target.is_symlink() and build_model_checksum(target) == source_sha256:
            return target
        raise FileExistsError(f"immutable model artifact target contains different bytes: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{target.name}.", dir=target.parent))
    temporary.rmdir()
    try:
        shutil.copytree(source, temporary, copy_function=shutil.copy2)
        if build_model_checksum(temporary) != source_sha256:
            raise RuntimeError("model artifact copy changed content identity")
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
    return target


def _runtime_package_versions(
    *,
    torch_module: Any,
    transformers_module: Any,
    peft_module: Any,
    quantization_proof: QuantizationProof,
) -> dict[str, str]:
    versions = {
        "python": platform.python_version(),
        "torch": str(getattr(torch_module, "__version__", "unknown")),
        "transformers": str(getattr(transformers_module, "__version__", "unknown")),
        "peft": str(getattr(peft_module, "__version__", "unknown")),
    }
    if quantization_proof.bitsandbytes_version is not None:
        versions["bitsandbytes"] = quantization_proof.bitsandbytes_version
    if any(value == "unknown" for value in versions.values()):
        raise RuntimeError("Phase 40 evidence requires exact runtime package versions")
    return dict(sorted(versions.items()))


def _runtime_hardware_evidence(
    *,
    torch_module: Any,
    controlled_config: ResumeControlledConfig,
) -> RuntimeHardwareEvidence:
    accelerator = controlled_config.accelerator
    cuda_version = getattr(getattr(torch_module, "version", None), "cuda", None)
    cudnn_version: str | None = None
    cudnn = getattr(getattr(torch_module, "backends", None), "cudnn", None)
    if cudnn is not None and callable(getattr(cudnn, "version", None)):
        raw_cudnn_version = cudnn.version()
        cudnn_version = None if raw_cudnn_version is None else str(raw_cudnn_version)
    return RuntimeHardwareEvidence(
        python_version=platform.python_version(),
        platform=platform.platform(),
        cuda_version=None if cuda_version is None else str(cuda_version),
        cudnn_version=cudnn_version,
        gpu_name=(
            accelerator.accelerator_name
            if accelerator.accelerator_type == "cuda"
            else None
        ),
        gpu_compute_capability=(
            accelerator.compute_capability
            if accelerator.accelerator_type == "cuda"
            else None
        ),
        gpu_total_memory_bytes=(
            accelerator.total_memory_bytes
            if accelerator.accelerator_type == "cuda"
            else None
        ),
        bf16_enabled=controlled_config.precision.bf16,
        fp16_enabled=controlled_config.precision.fp16,
        tf32_enabled=controlled_config.precision.tf32,
    )


def _materialize_full_run_evidence(
    config: TrainingConfig,
    *,
    data_contract: Phase40DataContract,
    controlled_config: ResumeControlledConfig,
    quantization_proof: QuantizationProof,
    checkpoint_selection: CheckpointSelection,
    validation_recorder: Phase40ValidationRecorder,
    adapter_output_dir: Path,
    training_output_dir: Path,
    event_path: Path,
    resource_summary: Any,
    torch_module: Any,
    transformers_module: Any,
    peft_module: Any,
    base_model_snapshot: QwenBaseModelSnapshot,
    run_root_override: Path | None = None,
) -> tuple[Path, RunEvidence]:
    """Materialize and rehash the fixed complete full-run bundle."""

    if config.transfer_authority is None:
        raise RuntimeError("complete full evidence requires explicit transfer authority")
    if config.sanitized_argv is None:
        raise RuntimeError("complete full evidence requires the actual sanitized CLI argv")
    from src.model_adaptation.phase40_handoff import _metric_summary, _run_metric_summary

    run_root = _evidence_root(config) if run_root_override is None else Path(run_root_override)
    if event_path != run_root / "events.jsonl":
        raise RuntimeError("event log is outside the canonical full-run evidence root")
    load_run_events(event_path, expected_run_id=_resolved_run_id(config))

    resolved_config_path = _write_immutable_bytes(
        run_root / "resolved-config.json",
        _canonical_json_line(controlled_config.model_dump(mode="json")),
    )
    trainer_state_source = training_output_dir / "trainer_state.json"
    if not trainer_state_source.is_file() or trainer_state_source.stat().st_size == 0:
        raise RuntimeError("Trainer did not persist a non-empty trainer_state.json")
    trainer_state_path = _write_immutable_bytes(
        run_root / "trainer_state.json",
        trainer_state_source.read_bytes(),
    )
    model_artifact_path = _copy_directory_immutable(
        adapter_output_dir,
        run_root / "adapter-or-model",
    )
    retained_base_source = model_artifact_path / PHASE40_BASE_MODEL_MANIFEST_NAME
    if (
        not retained_base_source.is_file()
        or retained_base_source.is_symlink()
        or retained_base_source.read_bytes()
        != _canonical_json_line(base_model_snapshot.portable_manifest())
    ):
        raise RuntimeError("returned adapter did not retain exact base-model source provenance")

    artifact_records: dict[str, ArtifactEvidence] = {}
    artifact_by_role_sha: dict[tuple[str, str], ArtifactEvidence] = {}

    def add_artifact(
        logical_name: str,
        role: str,
        path: Path,
        *,
        kind: str = "file",
    ) -> ArtifactEvidence:
        relative_path = Path(path).relative_to(run_root).as_posix()
        sha256 = build_model_checksum(path)
        existing = artifact_by_role_sha.get((role, sha256))
        if existing is not None:
            return existing
        artifact = ArtifactEvidence(
            logical_name=logical_name,
            role=role,
            relative_path=relative_path,
            kind=kind,
            sha256=sha256,
        )
        if logical_name in artifact_records:
            raise RuntimeError(f"duplicate evidence logical name: {logical_name}")
        artifact_records[logical_name] = artifact
        artifact_by_role_sha[(role, sha256)] = artifact
        return artifact

    add_artifact("events", "events", event_path)
    add_artifact("model-artifact", "model_artifact", model_artifact_path, kind="directory")
    resolved_artifact = add_artifact("resolved-config", "resolved_config", resolved_config_path)
    add_artifact("trainer-state", "trainer_state", trainer_state_path)

    selected_key = (
        checkpoint_selection.selected_step,
        checkpoint_selection.selected_artifact_identity,
    )
    checkpoint_evidence: list[ValidationCheckpointEvidence] = []
    metric_entries = sorted(
        validation_recorder.metrics_by_candidate.items(),
        key=lambda item: (item[0] != selected_key, item[0]),
    )
    for (step, artifact_identity), metrics in metric_entries:
        identity_digest = artifact_identity.removeprefix("adapter-state-sha256:")
        if (step, artifact_identity) == selected_key:
            prediction_path = run_root / "predictions.json"
            metric_path = run_root / "validation-metrics.json"
            prediction_logical_name = "predictions"
            metric_logical_name = "validation-metrics"
        else:
            checkpoint_relative = Path("checkpoints") / f"step-{step}-{identity_digest}"
            prediction_path = run_root / checkpoint_relative / "predictions.json"
            metric_path = run_root / checkpoint_relative / "validation-metrics.json"
            prediction_logical_name = f"predictions-step-{step}-{identity_digest}"
            metric_logical_name = f"validation-metrics-step-{step}-{identity_digest}"
        _write_immutable_bytes(prediction_path, _prediction_jsonl_bytes(metrics.prediction_rows))
        _write_immutable_bytes(
            metric_path,
            _canonical_json_line(_metric_summary(metrics)),
        )
        prediction_artifact = add_artifact(
            prediction_logical_name,
            "predictions",
            prediction_path,
        )
        metric_artifact = add_artifact(metric_logical_name, "metrics", metric_path)
        one_candidate = select_phase40_checkpoint((metrics,))
        checkpoint_evidence.append(
            ValidationCheckpointEvidence(
                optimizer_step=step,
                artifact_identity=artifact_identity,
                predictions_sha256=prediction_artifact.sha256,
                metrics_sha256=metric_artifact.sha256,
                macro_f1=metrics.macro_f1,
                safety_gate_passed=one_candidate.safety_gate_passed,
                invalid_output_count=metrics.invalid_output_count,
            )
        )
    if not (run_root / "predictions.json").is_file() or not (
        run_root / "validation-metrics.json"
    ).is_file():
        raise RuntimeError("selected checkpoint did not materialize canonical evidence files")

    graph = render_phase40_graphs(run_root)
    add_artifact("graph-data-loss", "graph_data", run_root / "curves/normalized-loss-curves.json")
    add_artifact("graph-manifest-loss", "graph_manifest", run_root / "curves/graph-provenance.json")
    add_artifact("graph-output-loss", "graph_output", run_root / "curves/loss-curves.png")

    selected_metrics = checkpoint_selection.selected_metrics
    evidence = RunEvidence(
        schema_version="phase40-run-evidence-v1",
        run_id=_resolved_run_id(config),
        run_kind=RunKind.FULL,
        experiment_identity=ExperimentIdentityEvidence(
            model_family=ModelFamily.QWEN,
            adaptation_mode=config.adaptation_mode,
            run_kind=RunKind.FULL,
        ),
        model_id=_resolved_model_id(config),
        model_revision=config.model_revision,
        splits=controlled_config.splits,
        seed=config.seed,
        data_seed=config.data_seed,
        resolved_config_sha256=resolved_artifact.sha256,
        resume_digest=compute_resume_digest(controlled_config),
        prompt_or_preprocessor_sha256=controlled_config.formatter_or_preprocessor_sha256,
        decoder_contract=controlled_config.decoder,
        decoder_contract_sha256=(
            None if controlled_config.decoder is None else controlled_config.decoder.sha256
        ),
        sanitized_argv=config.sanitized_argv,
        package_versions=_runtime_package_versions(
            torch_module=torch_module,
            transformers_module=transformers_module,
            peft_module=peft_module,
            quantization_proof=quantization_proof,
        ),
        hardware=_runtime_hardware_evidence(
            torch_module=torch_module,
            controlled_config=controlled_config,
        ),
        quantization=QuantizationProofEvidence(**asdict(quantization_proof)),
        peak_allocated_bytes=resource_summary.peak_allocated_bytes,
        peak_reserved_bytes=resource_summary.peak_reserved_bytes,
        steady_step_seconds_median=resource_summary.steady_state_step_seconds_median,
        validation_metrics=_run_metric_summary(selected_metrics),
        validation_checkpoints=tuple(
            sorted(
                checkpoint_evidence,
                key=lambda item: (item.optimizer_step, item.artifact_identity),
            )
        ),
        selected_checkpoint=SelectedCheckpointEvidence(
            optimizer_step=checkpoint_selection.selected_step,
            artifact_identity=checkpoint_selection.selected_artifact_identity,
            safety_gate_passed=checkpoint_selection.safety_gate_passed,
            rationale=(
                "highest admissible macro f1 with locked deterministic tie breaks"
                if checkpoint_selection.safety_gate_passed
                else "best retained checkpoint failed locked safety admission"
            ),
        ),
        artifacts=tuple(sorted(artifact_records.values(), key=lambda item: item.logical_name)),
        artifact_sha256={
            artifact.logical_name: artifact.sha256
            for artifact in sorted(artifact_records.values(), key=lambda item: item.logical_name)
        },
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
        raise RuntimeError("full-run evidence changed during final verification")
    return evidence_path, verified


def _remove_uncommitted_bundle_outputs(paths: Sequence[Path], *, run_root: Path) -> None:
    """Remove only outputs created by the current not-yet-terminal publish attempt."""

    root = Path(run_root).resolve(strict=True)
    for path in reversed(tuple(paths)):
        target = Path(path)
        resolved = target.resolve(strict=False)
        if resolved.parent != root:
            raise RuntimeError("uncommitted evidence cleanup escaped the canonical bundle root")
        if target.is_symlink():
            raise RuntimeError("uncommitted evidence output unexpectedly became a symlink")
        if target.is_dir():
            shutil.rmtree(target)
        elif target.exists():
            target.unlink()


def _prepublish_verified_staging_bundle(
    staging_root: Path,
    *,
    run_root: Path,
) -> tuple[Path, ...]:
    """Copy verified non-event outputs before the append-only lifecycle commit."""

    staging = Path(staging_root).resolve(strict=True)
    canonical = Path(run_root).resolve(strict=True)
    created: list[Path] = []
    try:
        for source in sorted(staging.iterdir(), key=lambda item: item.name):
            if source.name == "events.jsonl":
                continue
            if source.is_symlink():
                raise RuntimeError("staged evidence bundle contains a symlink")
            target = canonical / source.name
            if target.exists() or target.is_symlink():
                raise FileExistsError(
                    f"canonical evidence output already exists before lifecycle commit: {target}"
                )
            created.append(target)
            if source.is_dir():
                _copy_directory_immutable(source, target)
            elif source.is_file():
                _write_immutable_bytes(target, source.read_bytes())
            else:
                raise RuntimeError("staged evidence bundle contains a non-file entry")
            if build_model_checksum(target) != build_model_checksum(source):
                raise RuntimeError("prepublished evidence output differs from verified staging")
        return tuple(created)
    except BaseException:
        _remove_uncommitted_bundle_outputs(created, run_root=canonical)
        raise


def _materialize_and_commit_full_run_evidence(
    config: TrainingConfig,
    *,
    final_step: int,
    final_epoch: float,
    final_artifact_identity: str,
    final_artifact_path: Path,
    final_metrics: Phase40MetricResult,
    deferred_train_end: Phase40CallbackEvent,
    data_contract: Phase40DataContract,
    controlled_config: ResumeControlledConfig,
    quantization_proof: QuantizationProof,
    checkpoint_selection: CheckpointSelection,
    validation_recorder: Phase40ValidationRecorder,
    adapter_output_dir: Path,
    training_output_dir: Path,
    event_path: Path,
    resource_summary: Any,
    torch_module: Any,
    transformers_module: Any,
    peft_module: Any,
    base_model_snapshot: QwenBaseModelSnapshot,
) -> tuple[Path, RunEvidence]:
    """Verify a projected completed bundle, then commit its exact lifecycle last."""

    run_root = _evidence_root(config).resolve(strict=True)
    canonical_event_path = Path(event_path)
    if canonical_event_path.resolve(strict=True) != (run_root / "events.jsonl").resolve(
        strict=True
    ):
        raise RuntimeError("full-run event path differs from its canonical bundle root")
    existing_events = load_run_events(
        canonical_event_path,
        expected_run_id=_resolved_run_id(config),
    )
    staging_root = Path(
        tempfile.mkdtemp(prefix=f".{run_root.name}.finalize-", dir=run_root.parent)
    )
    published: tuple[Path, ...] = ()
    lifecycle_committed = False
    try:
        staged_event_path = staging_root / "events.jsonl"
        _write_immutable_bytes(staged_event_path, canonical_event_path.read_bytes())
        _append_full_run_finalization_events(
            staged_event_path,
            run_id=_resolved_run_id(config),
            final_step=final_step,
            final_epoch=final_epoch,
            artifact_identity=final_artifact_identity,
            artifact_path=final_artifact_path,
            metrics=final_metrics,
            deferred_train_end=deferred_train_end,
        )
        projected_events = load_run_events(
            staged_event_path,
            expected_run_id=_resolved_run_id(config),
        )
        if projected_events[: len(existing_events)] != existing_events:
            raise RuntimeError("projected final lifecycle changed the append-only event prefix")
        projected_suffix = projected_events[len(existing_events) :]
        if not projected_suffix or projected_suffix[-1].event_kind != RunEventKind.RUN_END:
            raise RuntimeError("projected final lifecycle lacks its terminal run_end")

        staged_evidence_path, verified_evidence = _materialize_full_run_evidence(
            config,
            data_contract=data_contract,
            controlled_config=controlled_config,
            quantization_proof=quantization_proof,
            checkpoint_selection=checkpoint_selection,
            validation_recorder=validation_recorder,
            adapter_output_dir=adapter_output_dir,
            training_output_dir=training_output_dir,
            event_path=staged_event_path,
            resource_summary=resource_summary,
            torch_module=torch_module,
            transformers_module=transformers_module,
            peft_module=peft_module,
            base_model_snapshot=base_model_snapshot,
            run_root_override=staging_root,
        )
        evidence_relative_path = staged_evidence_path.relative_to(staging_root)
        canonical_evidence_path = run_root / evidence_relative_path
        published = _prepublish_verified_staging_bundle(
            staging_root,
            run_root=run_root,
        )
        if canonical_evidence_path not in published:
            raise RuntimeError("verified staged evidence was not prepublished")

        current_events = load_run_events(
            canonical_event_path,
            expected_run_id=_resolved_run_id(config),
        )
        if current_events != existing_events:
            raise RuntimeError("canonical event log changed during evidence staging")
        for event in projected_suffix:
            append_run_event(canonical_event_path, event)
        lifecycle_committed = True
        return canonical_evidence_path, verified_evidence
    except BaseException:
        if not lifecycle_committed and published:
            _remove_uncommitted_bundle_outputs(published, run_root=run_root)
        raise
    finally:
        shutil.rmtree(staging_root, ignore_errors=True)


def _complete_full_qwen_training(
    *,
    runtime_config: TrainingConfig,
    validation_recorder: Phase40ValidationRecorder,
    controlled_config: ResumeControlledConfig,
    deferred_train_end: Phase40CallbackEvent,
    model: Any,
    tokenizer: Any,
    trainer: Any,
    event_path: Path,
    evidence_root: Path,
    training_output_dir: Path,
    base_model_snapshot: QwenBaseModelSnapshot,
    base_model_path: Path,
    device: str,
    resource_summary: Any,
    quantization_proof: QuantizationProof,
    data_contract: Phase40DataContract,
    train_result: Any,
    train_examples: Sequence[dict[str, Any]],
    val_examples: Sequence[dict[str, Any]],
    train_dataset: Any,
    resume_checkpoint: Path | None,
    torch_module: Any,
    transformers_module: Any,
    peft_module: Any,
) -> dict[str, Any]:
    """Complete the artifact/evidence transaction after Trainer ended successfully."""

    final_adapter_output_dir = _final_adapter_output_dir(runtime_config)
    final_adapter_output_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(final_adapter_output_dir))
    tokenizer.save_pretrained(str(final_adapter_output_dir))

    final_step = int(getattr(getattr(trainer, "state", None), "global_step", 0))
    final_metrics = validation_recorder.record_final_if_needed(
        model=model,
        final_step=final_step,
        final_artifact_path=final_adapter_output_dir,
    )
    final_epoch = float(getattr(getattr(trainer, "state", None), "epoch", 0.0) or 0.0)
    if not math.isfinite(final_epoch) or final_epoch < 0:
        raise RuntimeError("Trainer final epoch must be finite and non-negative")
    final_identity = final_metrics.prediction_rows[0].artifact_identity
    checkpoint_selection = validation_recorder.select()
    selected_source = validation_recorder.retained_path_for(checkpoint_selection)
    adapter_output_dir = _retain_adapter_payload(
        selected_source,
        _adapter_output_dir(runtime_config),
    )
    selected_state_identity = _adapter_state_identity(
        _load_saved_adapter_state(adapter_output_dir, torch_module=torch_module),
        torch_module=torch_module,
    )
    if selected_state_identity != checkpoint_selection.selected_artifact_identity:
        raise RuntimeError("materialized selected adapter does not match checkpoint selection")
    tokenizer.save_pretrained(str(adapter_output_dir))
    base_model_provenance_path = _write_immutable_bytes(
        adapter_output_dir / PHASE40_BASE_MODEL_MANIFEST_NAME,
        _canonical_json_line(base_model_snapshot.portable_manifest()),
    )

    final_checkpoint_path = training_output_dir / f"checkpoint-{final_step}"
    checkpoint_path = final_checkpoint_path if final_checkpoint_path.is_dir() else None
    training_summary = {
        "candidate_id": runtime_config.candidate_id,
        "run_id": _resolved_run_id(runtime_config),
        "run_kind": runtime_config.run_kind.value,
        "base_model_path": base_model_path,
        "device": device,
        "requested_adaptation_mode": runtime_config.adaptation_mode.value,
        "model_revision": runtime_config.model_revision,
        "base_model_source": base_model_snapshot.evidence_payload(),
        "quantization_mode": quantization_proof.resolved_mode.value,
        "quantization_proof": asdict(quantization_proof),
        "resume_digest": compute_resume_digest(controlled_config),
        "resume_controlled_config": controlled_config.model_dump(mode="json"),
        "resume_from_checkpoint": resume_checkpoint,
        "checkpoint_path": checkpoint_path,
        "smoke_test": runtime_config.smoke_test,
        "train_examples": len(train_examples),
        "val_examples": len(val_examples),
        "canonical_inputs": {
            "train": {
                "records": data_contract.train_snapshot.identity.records,
                "bytes": data_contract.train_snapshot.identity.bytes,
                "sha256": data_contract.train_snapshot.whole_file_sha256,
                "ordered_row_ids_sha256": _snapshot_row_id_digest(data_contract.train_snapshot),
            },
            "val": {
                "records": data_contract.validation_snapshot.identity.records,
                "bytes": data_contract.validation_snapshot.identity.bytes,
                "sha256": data_contract.validation_snapshot.whole_file_sha256,
                "ordered_row_ids_sha256": _snapshot_row_id_digest(
                    data_contract.validation_snapshot
                ),
            },
        },
        "formatter_version": train_dataset.formatter_version,
        "formatter_sha256": train_dataset.formatter_sha256,
        "response_mask_version": train_dataset.response_mask_version,
        "validation_checkpoints": {
            f"{step}:{artifact_identity}": _json_ready(asdict(metrics))
            for (step, artifact_identity), metrics in validation_recorder.metrics_by_candidate.items()
        },
        "checkpoint_selection": _json_ready(asdict(checkpoint_selection)),
        "selected_adapter": {
            "state_identity": selected_state_identity,
            "path": adapter_output_dir,
            "payload_sha256": build_model_checksum(adapter_output_dir),
        },
        "metrics": train_result.metrics,
        "resource_summary": _json_ready(asdict(resource_summary)),
        "events_path": event_path,
    }
    summary_path = adapter_output_dir / "training-summary.json"
    summary_path.write_text(
        json.dumps(_json_ready(training_summary), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    run_id = _resolved_run_id(runtime_config)
    evidence_path, verified_evidence = _materialize_and_commit_full_run_evidence(
        runtime_config,
        final_step=final_step,
        final_epoch=final_epoch,
        final_artifact_identity=final_identity,
        final_artifact_path=final_adapter_output_dir,
        final_metrics=final_metrics,
        deferred_train_end=deferred_train_end,
        data_contract=data_contract,
        controlled_config=controlled_config,
        quantization_proof=quantization_proof,
        checkpoint_selection=checkpoint_selection,
        validation_recorder=validation_recorder,
        adapter_output_dir=adapter_output_dir,
        training_output_dir=training_output_dir,
        event_path=event_path,
        resource_summary=resource_summary,
        torch_module=torch_module,
        transformers_module=transformers_module,
        peft_module=peft_module,
        base_model_snapshot=base_model_snapshot,
    )
    return {
        "artifact_path": adapter_output_dir,
        "base_model_path": base_model_path,
        "device": device,
        "quantization_mode": quantization_proof.resolved_mode.value,
        "quantization_proof": quantization_proof,
        "run_id": run_id,
        "run_kind": RunKind.FULL,
        "model_revision": runtime_config.model_revision,
        "base_model_source": base_model_snapshot.evidence_payload(),
        "base_model_provenance_path": base_model_provenance_path,
        "resume_controlled_config": controlled_config,
        "resume_digest": compute_resume_digest(controlled_config),
        "resume_from_checkpoint": resume_checkpoint,
        "checkpoint_path": checkpoint_path,
        "summary_path": summary_path,
        "checkpoint_selection": checkpoint_selection,
        "checkpoint_candidates": tuple(validation_recorder.metrics_by_candidate.values()),
        "formatter_sha256": train_dataset.formatter_sha256,
        "formatter_version": train_dataset.formatter_version,
        "response_mask_version": train_dataset.response_mask_version,
        "canonical_train_sha256": data_contract.train_snapshot.whole_file_sha256,
        "canonical_val_sha256": data_contract.validation_snapshot.whole_file_sha256,
        "canonical_train_row_ids_sha256": _snapshot_row_id_digest(data_contract.train_snapshot),
        "canonical_val_row_ids_sha256": _snapshot_row_id_digest(
            data_contract.validation_snapshot
        ),
        "selected_artifact_identity": selected_state_identity,
        "events_path": event_path,
        "resource_summary": resource_summary,
        "evidence_root": evidence_root,
        "evidence_path": evidence_path,
        "verified_evidence": verified_evidence,
    }


def _run_local_adapter_training(
    config: TrainingConfig,
    train_examples: list[dict[str, Any]],
    val_examples: list[dict[str, Any]],
    data_contract: Phase40DataContract,
) -> dict[str, Any]:
    run_id = _resolved_run_id(config)
    planned_full_optimizer_steps = _planned_optimizer_steps(config, len(train_examples))
    probe_contract: ProbeExecutionContract | None = None
    runtime_config = config
    if config.run_kind == RunKind.PROBE:
        if config.probe_post_warmup_steps is None:
            raise RuntimeError(
                "probe discard/evidence lifecycle requires an explicit 30-50 "
                "post-warm-up optimizer-step target"
            )
        probe_contract = ProbeExecutionContract(
            run_id=run_id,
            requested_identity=config.experiment_identity,
            target_post_warmup_steps=config.probe_post_warmup_steps,
            warmup_optimizer_steps=config.probe_warmup_steps,
            resume_from_checkpoint=config.resume_from_checkpoint,
        )
        runtime_config = replace(
            config,
            max_steps=probe_contract.total_optimizer_steps,
            save_steps=(
                config.save_steps
                if config.local_decision and config.adaptation_mode == AdaptationMode.LORA
                else probe_contract.total_optimizer_steps
            ),
            smoke_test=False,
        )

    base_model_path = _resolve_base_model_path(config)
    base_model_snapshot: QwenBaseModelSnapshot | None = None
    if runtime_config.run_kind == RunKind.FULL or runtime_config.local_decision:
        if _resolved_model_id(runtime_config) != PHASE40_QWEN_MODEL_ID:
            raise RuntimeError("Phase 40 Qwen training requires the exact locked model_id")
        if runtime_config.model_revision != PHASE40_QWEN_REVISION:
            raise RuntimeError("Phase 40 Qwen training requires the exact pinned revision")
        base_model_snapshot = validate_qwen_base_model_snapshot(
            base_model_path,
            expected_model_id=_resolved_model_id(runtime_config),
            expected_model_revision=runtime_config.model_revision,
            manifest_path=runtime_config.base_model_manifest_path,
        )

    torch_module, transformers_module, peft_module = _import_training_stack()
    device = _resolve_device(torch_module, config.device)
    identity = config.experiment_identity
    _validate_qwen_training_device(identity, device)
    capabilities, _ = _collect_qwen_preload_capabilities(
        torch_module,
        transformers_module,
        peft_module,
        identity,
    )
    preload_proof = prove_qwen_preload(identity, capabilities)
    quantization_config = _build_quantization_config(
        transformers_module,
        torch_module,
        config,
        device,
    )
    tokenizer, model = _load_pinned_qwen_base_components(
        transformers_module=transformers_module,
        torch_module=torch_module,
        config=config,
        base_model_path=base_model_path,
        device=device,
        quantization_config=quantization_config,
    )
    if config.gradient_checkpointing and hasattr(model, "gradient_checkpointing_enable"):
        model.gradient_checkpointing_enable()
        if hasattr(model, "config"):
            model.config.use_cache = False
    kbit_preparation_applied = False
    if config.adaptation_mode == AdaptationMode.QLORA:
        model = peft_module.prepare_model_for_kbit_training(model)
        kbit_preparation_applied = True

    lora_config = peft_module.LoraConfig(
        r=config.lora_r,
        lora_alpha=config.lora_alpha,
        lora_dropout=config.lora_dropout,
        bias=config.lora_bias,
        task_type="CAUSAL_LM",
        target_modules=list(config.target_modules),
    )
    model = peft_module.get_peft_model(model, lora_config)
    if tokenizer.pad_token_id is not None and getattr(model.config, "pad_token_id", None) is None:
        model.config.pad_token_id = tokenizer.pad_token_id
    if tokenizer.pad_token_id is None:
        raise RuntimeError("Qwen tokenizer has no pad/eos/unk token available for right padding")

    train_dataset = _ResponseOnlyDataset(
        train_examples,
        tokenizer,
        config.max_seq_length,
    )
    eval_dataset = _ResponseOnlyDataset(
        val_examples,
        tokenizer,
        config.max_seq_length,
    )
    if not train_dataset.formatter_sha256 or not eval_dataset.formatter_sha256:
        raise RuntimeError("Phase 40 train and validation formatter provenance must be non-empty")
    if train_dataset.formatter_sha256 != eval_dataset.formatter_sha256:
        raise RuntimeError("Phase 40 train and validation formatter hashes do not match")

    gradient_checks: tuple[AdapterGradientCheck, ...] = ()
    backward_performed = False
    if config.adaptation_mode == AdaptationMode.QLORA:
        if not train_examples:
            raise RuntimeError("QLoRA gradient proof requires at least one training example")
        gradient_checks = _run_adapter_gradient_probe(
            model,
            train_dataset[0],
            torch_module=torch_module,
        )
        backward_performed = True
    quantization_proof = prove_qwen_mode(
        identity,
        preload_proof=preload_proof,
        model=model,
        quantization_config=quantization_config,
        kbit_preparation_applied=kbit_preparation_applied,
        backward_performed=backward_performed,
        adapter_gradients=gradient_checks,
    )
    if runtime_config.local_decision:
        if runtime_config.controller_stop_request_path is None:
            raise RuntimeError("local decision lost its controller stop-request authority")
        _write_immutable_bytes(
            Path(runtime_config.controller_stop_request_path).parent
            / "quantization-proof-prestep.json",
            _canonical_json_line(_json_ready(asdict(quantization_proof))),
        )

    use_bf16 = device == "cuda" and torch_module.cuda.is_bf16_supported()
    controlled_config: ResumeControlledConfig | None = None
    if runtime_config.run_kind == RunKind.FULL:
        controlled_config = _build_resume_controlled_config(
            runtime_config,
            data_contract=data_contract,
            formatter_sha256=train_dataset.formatter_sha256,
            quantization_proof=quantization_proof,
            planned_optimizer_steps=planned_full_optimizer_steps,
            model=model,
            torch_module=torch_module,
            device=device,
            use_bf16=use_bf16,
        )
        _verify_requested_runtime_controls(runtime_config, controlled_config)

    # No trainer/model artifact path exists until both proof stages have completed.
    evidence_root = (
        _prepare_full_run_bundle_root(runtime_config, create=True)
        if runtime_config.run_kind == RunKind.FULL
        else _evidence_root(runtime_config)
    )
    training_output_dir = _training_output_dir(runtime_config)
    training_output_dir.mkdir(parents=True, exist_ok=True)
    evidence_root.mkdir(parents=True, exist_ok=True)
    event_path = evidence_root / "events.jsonl"
    resume_checkpoint = _resolve_resume_checkpoint(
        runtime_config,
        training_output_dir,
        controlled_config,
        event_path=event_path if runtime_config.resume_from_checkpoint is not None else None,
        base_model_snapshot=base_model_snapshot,
    )
    event_sequence_offset = 0
    if event_path.exists():
        if resume_checkpoint is None:
            raise FileExistsError("fresh Phase 40 run cannot reuse an existing event log")
        existing_events = load_run_events(event_path, expected_run_id=run_id)
        if existing_events[-1].event_kind == RunEventKind.RUN_END:
            raise RuntimeError("completed full-run evidence cannot be resumed")
        event_sequence_offset = len(existing_events)
    elif resume_checkpoint is not None:
        raise RuntimeError("exact resume requires the original append-only event log")

    training_args = _build_training_arguments(
        transformers_module,
        runtime_config,
        training_output_dir,
        has_eval_data=len(eval_dataset) > 0,
        device=device,
        use_bf16=use_bf16,
    )
    _verify_training_argument_controls(
        training_args,
        runtime_config,
        device=device,
        use_bf16=use_bf16,
    )
    validation_recorder: Phase40ValidationRecorder | None = None
    if runtime_config.run_kind == RunKind.FULL:
        validation_recorder = Phase40ValidationRecorder(
            tokenizer=tokenizer,
            candidate=get_candidate_by_id(runtime_config.candidate_id),
            validation_snapshot=data_contract.validation_snapshot,
            training_output_dir=training_output_dir,
            prediction_output_dir=_candidate_output_dir(runtime_config) / "validation",
            retained_artifact_root=_candidate_output_dir(runtime_config) / "retained-adapters",
            artifact_identity_prover=lambda current_model, artifact_path: (
                _prove_saved_adapter_matches_live(
                    current_model,
                    artifact_path,
                    torch_module=torch_module,
                    peft_module=peft_module,
                )
            ),
            stored_artifact_identity_loader=lambda artifact_path: _adapter_state_identity(
                _load_saved_adapter_state(artifact_path, torch_module=torch_module),
                torch_module=torch_module,
            ),
        )
    resume_telemetry_state: Mapping[str, object] | None = None
    if resume_checkpoint is not None:
        if validation_recorder is None:
            raise RuntimeError("exact Qwen resume requires validation history restoration")
        history_path = resume_checkpoint / PHASE40_RESUME_HISTORY_NAME
        try:
            history_payload = json.loads(history_path.read_text(encoding="utf-8", errors="strict"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeError("exact Qwen resume history cannot be loaded") from exc
        checkpoint_telemetry_state = validation_recorder.restore_resume_history(history_payload)
        if controlled_config is None or base_model_snapshot is None:
            raise RuntimeError("exact Qwen resume lost its controlled model provenance")
        resume_manifest = _read_checkpoint_resume_manifest(
            resume_checkpoint,
            controlled_config=controlled_config,
            event_path=event_path,
            base_model_snapshot=base_model_snapshot,
            require_cumulative_history=True,
        )
        resume_telemetry_state = _resume_state_with_failed_suffix(
            checkpoint_telemetry_state,
            event_path=event_path,
            checkpoint_event_count=resume_manifest["run_event_count"],
        )
    timing_adapter = TorchCudaTimingAdapter(torch_module.cuda)
    deferred_full_train_end: list[Phase40CallbackEvent] = []

    def runtime_event_sink(event: Phase40CallbackEvent) -> None:
        if runtime_config.local_decision:
            values = dict(event.values)
            for field_name, method_name in (
                ("allocated_bytes", "memory_allocated"),
                ("reserved_bytes", "memory_reserved"),
            ):
                method = getattr(torch_module.cuda, method_name, None)
                try:
                    observed = int(method()) if callable(method) else None
                except (RuntimeError, TypeError, ValueError):
                    observed = None
                if observed is not None and observed >= 0:
                    values[field_name] = observed
            event = replace(event, values=tuple(sorted(values.items())))
        if (
            runtime_config.run_kind == RunKind.FULL
            and event.event_kind == CallbackEventKind.TRAIN_END
        ):
            deferred_full_train_end.append(event)
            return
        _append_callback_run_event(
            event_path,
            event,
            sequence_offset=event_sequence_offset,
        )

    evidence_callback = Phase40EvidenceCallback(
        run_id=run_id,
        run_kind=runtime_config.run_kind,
        warmup_optimizer_steps=(
            probe_contract.warmup_optimizer_steps if probe_contract is not None else 0
        ),
        target_post_warmup_steps=(
            probe_contract.target_post_warmup_steps if probe_contract is not None else None
        ),
        examples_per_optimizer_step=(
            runtime_config.per_device_train_batch_size
            * runtime_config.gradient_accumulation_steps
        ),
        planned_full_optimizer_steps=planned_full_optimizer_steps,
        event_sink=runtime_event_sink,
        resume_state=resume_telemetry_state,
        cuda=timing_adapter,
    )
    trainer_kwargs: dict[str, Any] = {
        "model": model,
        "args": training_args,
        "train_dataset": train_dataset,
        "eval_dataset": eval_dataset if len(eval_dataset) else None,
        "data_collator": Phase40ResponseOnlyCollator(
            pad_token_id=tokenizer.pad_token_id,
        ),
    }
    trainer_parameters = set(inspect.signature(transformers_module.Trainer.__init__).parameters)
    checkpoint_durations: list[float] = []
    checkpoint_manifest_sealer: Callable[[Path, Mapping[str, object]], Path] | None = None
    if validation_recorder is not None:
        if controlled_config is None or base_model_snapshot is None:
            raise RuntimeError("full Qwen checkpoint sealing lacks controlled model provenance")

        def seal_checkpoint(
            checkpoint_path: Path,
            telemetry_state: Mapping[str, object],
        ) -> Path:
            history = validation_recorder.resume_history_payload(telemetry_state)
            return _write_checkpoint_resume_manifest(
                checkpoint_path,
                checkpoint_step=int(checkpoint_path.name.removeprefix("checkpoint-")),
                controlled_config=controlled_config,
                resume_history=history,
                event_path=event_path,
                base_model_snapshot=base_model_snapshot,
            )

        checkpoint_manifest_sealer = seal_checkpoint
    runtime_callback = _build_phase40_runtime_callback(
        transformers_module,
        evidence_callback=evidence_callback,
        checkpoint_durations=checkpoint_durations,
        validation_recorder=validation_recorder,
        checkpoint_manifest_sealer=checkpoint_manifest_sealer,
        controller_stop_request_path=runtime_config.controller_stop_request_path,
    )
    if "callbacks" in trainer_parameters:
        trainer_kwargs["callbacks"] = [runtime_callback]
    if "processing_class" in trainer_parameters:
        trainer_kwargs["processing_class"] = tokenizer
    elif "tokenizer" in trainer_parameters:
        trainer_kwargs["tokenizer"] = tokenizer
    trainer = transformers_module.Trainer(
        **trainer_kwargs,
    )
    _install_measured_checkpoint_wrapper(
        trainer,
        training_output_dir=training_output_dir,
        controlled_config=(controlled_config if validation_recorder is None else None),
        cuda_timing=timing_adapter,
        checkpoint_durations=checkpoint_durations,
    )
    if "callbacks" not in trainer_parameters:
        if not hasattr(trainer, "add_callback"):
            raise RuntimeError("Trainer cannot install the required Phase 40 runtime callback")
        trainer.add_callback(runtime_callback)

    if (
        runtime_config.run_kind == RunKind.FULL
        and resume_checkpoint is None
        and int(getattr(getattr(trainer, "state", None), "global_step", 0)) != 0
    ):
        raise RuntimeError("fresh Phase 40 full runs must originate at optimizer step zero")

    try:
        train_result = trainer.train(
            resume_from_checkpoint=(str(resume_checkpoint) if resume_checkpoint is not None else None)
        )
    except BaseException as exc:
        try:
            failure_resource_state = evidence_callback.failure_state()
        except RuntimeError:
            failure_resource_state = None
        _append_runtime_failure_event(
            event_path,
            run_id=run_id,
            run_kind=runtime_config.run_kind,
            requested_mode=runtime_config.adaptation_mode,
            error=exc,
            resource_state=failure_resource_state,
        )
        if "out of memory" in str(exc).casefold():
            raise RuntimeError(
                "Local training ran out of memory. The requested adaptation mode and partial "
                "append-only evidence were preserved; any retry must use an exact compatible "
                "checkpoint or a fresh run."
            ) from exc
        raise

    if probe_contract is not None:
        trainer.save_state()
        resource_summary = evidence_callback.summary()
        load_run_events(event_path, expected_run_id=run_id)
        resource_summary_path = _write_immutable_bytes(
            evidence_root / "resource-summary.json",
            _canonical_json_line(_json_ready(asdict(resource_summary))),
        )
        probe_root = _probe_root(runtime_config)
        discard_receipt = discard_probe_artifact(
            run_id=run_id,
            probe_root=probe_root,
            discarded_path_identity="trainer",
        )
        discard_receipt_path = write_probe_discard_receipt(
            discard_receipt,
            evidence_root / "probe-discard-receipt.json",
        )
        verify_probe_discard_receipt(discard_receipt, probe_root=probe_root)
        require_completed_probe(
            contract=probe_contract,
            summary=resource_summary,
            discard_receipt=discard_receipt,
            probe_root=probe_root,
        )
        return {
            "artifact_path": None,
            "artifact_record": None,
            "base_model_path": base_model_path,
            "device": device,
            "run_id": run_id,
            "run_kind": RunKind.PROBE,
            "quantization_mode": quantization_proof.resolved_mode.value,
            "quantization_proof": quantization_proof,
            "resume_from_checkpoint": None,
            "checkpoint_path": None,
            "events_path": event_path,
            "resource_summary": resource_summary,
            "resource_summary_path": resource_summary_path,
            "discard_receipt": discard_receipt,
            "discard_receipt_path": discard_receipt_path,
            "probe_contract": probe_contract,
            "requested_adaptation_mode": runtime_config.adaptation_mode.value,
            "trainer_metrics": train_result.metrics,
        }

    def finalize_full_run() -> dict[str, Any]:
        trainer.save_state()
        resource_summary = evidence_callback.summary()
        load_run_events(event_path, expected_run_id=run_id)
        if validation_recorder is None or controlled_config is None:
            raise RuntimeError("full run lost its validation/resume evidence contracts")
        if base_model_snapshot is None:
            raise RuntimeError("full Qwen result lost its base-model provenance")
        if len(deferred_full_train_end) != 1:
            raise RuntimeError(
                "full run did not observe exactly one deferred Trainer train_end event"
            )
        return _complete_full_qwen_training(
            runtime_config=runtime_config,
            validation_recorder=validation_recorder,
            controlled_config=controlled_config,
            deferred_train_end=deferred_full_train_end[0],
            model=model,
            tokenizer=tokenizer,
            trainer=trainer,
            event_path=event_path,
            evidence_root=evidence_root,
            training_output_dir=training_output_dir,
            base_model_snapshot=base_model_snapshot,
            base_model_path=base_model_path,
            device=device,
            resource_summary=resource_summary,
            quantization_proof=quantization_proof,
            data_contract=data_contract,
            train_result=train_result,
            train_examples=train_examples,
            val_examples=val_examples,
            train_dataset=train_dataset,
            resume_checkpoint=resume_checkpoint,
            torch_module=torch_module,
            transformers_module=transformers_module,
            peft_module=peft_module,
        )

    return _run_post_train_finalization_transaction(
        finalize_full_run,
        event_path=event_path,
        run_id=run_id,
        requested_mode=runtime_config.adaptation_mode,
        resource_state=evidence_callback.completed_state,
        failure_resource_state_provider=evidence_callback.failure_state,
    )


def save_adapter_artifacts(
    config: TrainingConfig,
    *,
    selection: PilotSelection | None = None,
    artifact_source_path: Path | None = None,
    artifact_bytes: bytes | None = None,
) -> ModelArtifactRecord:
    """Stage one adapter artifact and register its metadata locally."""

    resolved_selection = _resolve_selection(selection, config.registry_path)
    candidate_dir = config.output_root / config.version_tag / config.candidate_id
    candidate_dir.mkdir(parents=True, exist_ok=True)

    artifact_path = artifact_source_path or (candidate_dir / "adapter-placeholder.bin")
    if artifact_source_path is None:
        payload = artifact_bytes or json.dumps(
            {
                "candidate_id": config.candidate_id,
                "version_tag": config.version_tag,
                "mode": "dry-run" if config.dry_run else "staged",
            },
            ensure_ascii=False,
            indent=2,
        ).encode("utf-8")
        artifact_path.write_bytes(payload)

    artifact_record = ModelArtifactRecord(
        candidate_id=config.candidate_id,
        artifact_type="adapter",
        version_tag=config.version_tag,
        local_path=artifact_path,
        sha256=build_model_checksum(artifact_path),
        profile_name="baseline-winner" if config.candidate_id == resolved_selection.baseline_winner_id else "runner-up",
    )

    if config.registry_path.exists():
        registry = load_model_registry(config.registry_path)
    else:
        registry = ModelRegistry(version_tag=config.version_tag, selection=resolved_selection)

    registry.selection = resolved_selection
    registry.version_tag = config.version_tag
    registry.artifacts = [
        existing
        for existing in registry.artifacts
        if not (
            existing.candidate_id == artifact_record.candidate_id
            and existing.artifact_type == artifact_record.artifact_type
            and existing.version_tag == artifact_record.version_tag
        )
    ]
    registry.artifacts.append(artifact_record)
    save_model_registry(registry, config.registry_path)
    return artifact_record


def _verify_full_run_evidence_for_publication(
    config: TrainingConfig,
    *,
    data_contract: Phase40DataContract,
    trainer_result: dict[str, Any],
    checkpoint_selection: CheckpointSelection,
) -> RunEvidence:
    """Re-open and bind the complete bundle immediately before registry mutation."""

    evidence_root_value = trainer_result.get("evidence_root")
    evidence_path_value = trainer_result.get("evidence_path")
    if not isinstance(evidence_root_value, (str, os.PathLike)) or not isinstance(
        evidence_path_value,
        (str, os.PathLike),
    ):
        raise RuntimeError(
            "full training completed without a finalized evidence bundle; registry publication "
            "remains blocked"
        )
    evidence_root = Path(evidence_root_value)
    evidence_path = Path(evidence_path_value)
    evidence = verify_phase40_bundle(evidence_root, evidence_path=evidence_path)
    if config.transfer_authority is None:
        raise RuntimeError(
            "full-run registry publication requires explicit source/input transfer authority"
        )
    if evidence.transfer_authority != config.transfer_authority:
        raise RuntimeError("verified evidence has the wrong source/input transfer authority")
    expected_splits = (
        (
            "train",
            data_contract.train_snapshot.whole_file_sha256,
            _snapshot_row_id_digest(data_contract.train_snapshot),
        ),
        (
            "val",
            data_contract.validation_snapshot.whole_file_sha256,
            _snapshot_row_id_digest(data_contract.validation_snapshot),
        ),
    )
    actual_splits = tuple(
        (split.logical_name, split.sha256, split.ordered_row_ids_sha256)
        for split in evidence.splits
    )
    if actual_splits != expected_splits:
        raise RuntimeError("verified evidence is bound to different canonical split bytes/order")
    if evidence.run_kind != RunKind.FULL or evidence.experiment_identity.run_kind != RunKind.FULL:
        raise RuntimeError("registry publication evidence must describe a full run")
    if evidence.experiment_identity.model_family != ModelFamily.QWEN:
        raise RuntimeError("registry publication evidence has the wrong model family")
    if evidence.experiment_identity.adaptation_mode != config.adaptation_mode:
        raise RuntimeError("registry publication evidence has the wrong adaptation mode")
    if evidence.run_id != _resolved_run_id(config):
        raise RuntimeError("registry publication evidence has the wrong run ID")
    if evidence.model_id != _resolved_model_id(config) or evidence.model_revision != config.model_revision:
        raise RuntimeError("registry publication evidence has the wrong model identity/revision")
    if evidence.resume_digest != trainer_result.get("resume_digest"):
        raise RuntimeError("registry publication evidence has the wrong resume digest")
    if evidence.prompt_or_preprocessor_sha256 != trainer_result.get("formatter_sha256"):
        raise RuntimeError("registry publication evidence has the wrong formatter identity")
    selected = evidence.selected_checkpoint
    if selected is None or (
        selected.optimizer_step,
        selected.artifact_identity,
        selected.safety_gate_passed,
    ) != (
        checkpoint_selection.selected_step,
        checkpoint_selection.selected_artifact_identity,
        checkpoint_selection.safety_gate_passed,
    ):
        raise RuntimeError("registry publication evidence has the wrong selected checkpoint")
    return evidence


def _authorize_phase40_qwen_request(
    config: TrainingConfig,
    *,
    data_contract: Phase40DataContract,
    run_request: RunRequest,
    repo_root: Path,
) -> None:
    """Bind a registry-free Qwen execution to one exact verified request entry."""

    if not isinstance(run_request, RunRequest):
        raise TypeError("comparison training requires a typed Phase 40 RunRequest")
    if config.run_kind != RunKind.FULL or config.dry_run:
        raise ValueError("Phase 40 comparison training accepts only non-dry full runs")
    run_id = _resolved_run_id(config)
    matches = tuple(run for run in run_request.runs if run.run_id == run_id)
    if len(matches) != 1:
        raise ValueError("training run ID is not an exact unique RunRequest identity")
    requested = matches[0]
    if requested.model_family != ModelFamily.QWEN:
        raise ValueError("Qwen comparison training cannot execute a non-Qwen request")
    if requested.adaptation_mode != config.adaptation_mode:
        raise ValueError("training mode differs from the exact RunRequest identity")

    template = run_request.control_template_by_run.get(run_id)
    if template is None or config.requested_control_template != template:
        raise ValueError("training controls differ from the exact RunRequest template")
    if run_request.control_template_digest_by_run.get(run_id) != template.sha256:
        raise ValueError("RunRequest control-template digest does not match its template")
    if config.transfer_authority != transfer_authority_from_request(run_request):
        raise ValueError("training transfer authority differs from the exact RunRequest")

    repository = Path(repo_root)
    if not repository.is_absolute() or not repository.is_dir() or repository.is_symlink():
        raise ValueError("repo_root must be an existing absolute non-symlink directory")
    repository = Path(os.path.abspath(os.path.normpath(os.fspath(repository))))
    expected_root = Path(
        os.path.abspath(os.path.normpath(os.fspath(repository / requested.returned_root)))
    )
    try:
        expected_root.relative_to(repository)
    except ValueError as exc:
        raise ValueError("RunRequest returned root escapes repo_root") from exc
    if _absolute_non_symlink_bundle_root(config) != expected_root:
        raise ValueError("run_bundle_root differs from the exact RunRequest returned root")

    requested_config = template.materialize_for_validation()
    if (
        requested_config.experiment_identity.model_family != ModelFamily.QWEN
        or requested_config.experiment_identity.adaptation_mode != config.adaptation_mode
        or requested_config.experiment_identity.run_kind != RunKind.FULL
        or requested_config.model_id != _resolved_model_id(config)
        or requested_config.model_revision != config.model_revision
    ):
        raise ValueError("training model identity differs from the exact RunRequest template")
    expected_splits = tuple(
        (
            split_name,
            snapshot.identity.records,
            snapshot.identity.bytes,
            snapshot.whole_file_sha256,
            _snapshot_row_id_digest(snapshot),
        )
        for split_name, snapshot in (
            ("train", data_contract.train_snapshot),
            ("val", data_contract.validation_snapshot),
        )
    )
    requested_splits = tuple(
        (
            split.logical_name,
            split.records,
            split.bytes,
            split.sha256,
            split.ordered_row_ids_sha256,
        )
        for split in requested_config.splits
    )
    if requested_splits != expected_splits:
        raise ValueError("authorized data contract differs from the exact RunRequest inputs")


def build_phase40_qwen_training_config(
    *,
    run_request: RunRequest,
    run_id: str,
    data_contract: Phase40DataContract,
    repo_root: Path,
    work_root: Path,
    base_model_path: Path | None,
    sanitized_argv: tuple[str, ...],
    base_model_manifest_path: Path | None = None,
    resume_from_checkpoint: str | None = None,
    device: str = "auto",
) -> TrainingConfig:
    """Construct a full Qwen config mechanically from one frozen request template."""

    if not isinstance(run_request, RunRequest):
        raise TypeError("Phase 40 config construction requires a typed RunRequest")
    matches = tuple(run for run in run_request.runs if run.run_id == run_id)
    if len(matches) != 1:
        raise ValueError("run_id is not an exact unique RunRequest identity")
    requested_run = matches[0]
    if requested_run.model_family != ModelFamily.QWEN:
        raise ValueError("Qwen config construction cannot consume a non-Qwen request")
    template = run_request.control_template_by_run.get(run_id)
    if template is None:
        raise ValueError("RunRequest is missing the selected run control template")
    if run_request.control_template_digest_by_run.get(run_id) != template.sha256:
        raise ValueError("RunRequest control-template digest does not match its template")
    controlled = template.materialize_for_validation()
    additional = {item.name: item.value for item in controlled.additional_controls}
    if set(additional) != {
        "input_archive_sha256",
        "input_manifest_sha256",
        "local_files_only",
        "report_to",
        "save_safetensors",
        "source_archive_sha256",
        "source_inventory_sha256",
        "trust_remote_code",
    }:
        raise ValueError("RunRequest Qwen additional controls are not the exact runtime set")
    if additional["report_to"] != "none" or additional["save_safetensors"] is not True:
        raise ValueError("RunRequest Qwen output/report controls are not locked")
    if not isinstance(additional["local_files_only"], bool) or not isinstance(
        additional["trust_remote_code"], bool
    ):
        raise ValueError("RunRequest Qwen loading controls must be booleans")
    if controlled.task_type != "CAUSAL_LM":
        raise ValueError("RunRequest Qwen task_type must be CAUSAL_LM")
    if controlled.cadence.evaluation_steps != controlled.cadence.save_steps:
        raise ValueError("RunRequest validation/save cadence must be identical")
    if controlled.cadence.generation_steps != _generation_steps(
        planned_optimizer_steps=controlled.max_optimizer_steps,
        cadence_steps=controlled.cadence.save_steps,
    ):
        raise ValueError("RunRequest generation cadence is not mechanically reproducible")

    repository = Path(repo_root)
    mutable_root = Path(work_root)
    if not repository.is_absolute() or not mutable_root.is_absolute():
        raise ValueError("repo_root and work_root must be absolute")
    matching_candidates = tuple(
        candidate
        for candidate in build_default_catalog()
        if controlled.model_id in {candidate.candidate_id, candidate.hf_source}
    )
    if len(matching_candidates) != 1:
        raise ValueError("RunRequest Qwen model_id is not one exact locked catalog model")
    candidate = matching_candidates[0]
    config = TrainingConfig(
        candidate_id=candidate.candidate_id,
        baseline_winner_id="qwen3-4b-instruct-2507",
        runner_up_id="qwen3.5-4b",
        train_split_path=Path(run_request.input_bundle.extraction_root) / "train.jsonl",
        val_split_path=Path(run_request.input_bundle.extraction_root) / "val.jsonl",
        version_tag="phase40-comparison",
        output_root=mutable_root,
        registry_path=mutable_root / "unused-model-registry.json",
        adaptation_mode=controlled.experiment_identity.adaptation_mode,
        run_kind=RunKind.FULL,
        model_id=controlled.model_id,
        dry_run=False,
        base_model_path=base_model_path,
        base_model_manifest_path=base_model_manifest_path,
        num_train_epochs=controlled.num_train_epochs,
        max_steps=controlled.max_optimizer_steps,
        per_device_train_batch_size=controlled.per_device_train_batch_size,
        gradient_accumulation_steps=controlled.gradient_accumulation_steps,
        learning_rate=controlled.optimizer.learning_rate,
        logging_steps=controlled.cadence.logging_steps,
        save_steps=controlled.cadence.save_steps,
        save_total_limit=controlled.cadence.save_total_limit,
        max_seq_length=controlled.max_sequence_length,
        smoke_test=False,
        resume_from_checkpoint=resume_from_checkpoint,
        device=device,
        gradient_checkpointing=controlled.gradient_checkpointing,
        local_files_only=additional["local_files_only"],
        trust_remote_code=additional["trust_remote_code"],
        lora_r=controlled.lora_rank,
        lora_alpha=controlled.lora_alpha,
        lora_dropout=controlled.lora_dropout,
        lora_bias=controlled.lora_bias,
        target_modules=controlled.target_modules,
        model_revision=controlled.model_revision,
        run_id=run_id,
        seed=controlled.seed,
        data_seed=controlled.data_seed,
        optimizer_name=controlled.optimizer.optimizer,
        weight_decay=controlled.optimizer.weight_decay,
        lr_scheduler_type=controlled.optimizer.lr_scheduler_type,
        warmup_steps=controlled.optimizer.warmup_steps,
        warmup_ratio=controlled.optimizer.warmup_ratio,
        max_grad_norm=controlled.optimizer.max_grad_norm,
        tf32=controlled.precision.tf32,
        transfer_authority=transfer_authority_from_request(run_request),
        requested_control_template=template,
        sanitized_argv=sanitized_argv,
        run_bundle_root=repository / requested_run.returned_root,
    )
    _authorize_phase40_qwen_request(
        config,
        data_contract=data_contract,
        run_request=run_request,
        repo_root=repository,
    )
    return config


def _validate_completed_full_training_result(
    config: TrainingConfig,
    *,
    data_contract: Phase40DataContract,
    trainer_result: dict[str, Any],
) -> tuple[QuantizationProof, CheckpointSelection, Path, RunEvidence]:
    """Verify one complete full result without deciding whether it may be deployed."""

    quantization_proof = _require_quantization_proof(
        config,
        trainer_result.get("quantization_proof"),
    )
    checkpoint_selection = trainer_result.get("checkpoint_selection")
    if not isinstance(checkpoint_selection, CheckpointSelection):
        raise RuntimeError("trainer result is missing validated checkpoint selection evidence")
    checkpoint_candidates = trainer_result.get("checkpoint_candidates")
    if not isinstance(checkpoint_candidates, tuple) or not checkpoint_candidates:
        raise RuntimeError("trainer result is missing checkpoint metric candidates")
    if select_phase40_checkpoint(checkpoint_candidates) != checkpoint_selection:
        raise RuntimeError("checkpoint selection does not match retained metric candidates")
    if trainer_result.get("selected_artifact_identity") != (
        checkpoint_selection.selected_artifact_identity
    ):
        raise RuntimeError("selected adapter identity does not match checkpoint selection evidence")
    base_model_path = _resolve_base_model_path(config)
    base_model_snapshot = validate_qwen_base_model_snapshot(
        base_model_path,
        expected_model_id=_resolved_model_id(config),
        expected_model_revision=config.model_revision,
        manifest_path=config.base_model_manifest_path,
    )
    if trainer_result.get("base_model_source") != base_model_snapshot.evidence_payload():
        raise RuntimeError("trainer result base-model source provenance mismatch")
    expected_provenance = {
        "canonical_train_sha256": data_contract.train_snapshot.whole_file_sha256,
        "canonical_val_sha256": data_contract.validation_snapshot.whole_file_sha256,
        "canonical_train_row_ids_sha256": _snapshot_row_id_digest(
            data_contract.train_snapshot
        ),
        "canonical_val_row_ids_sha256": _snapshot_row_id_digest(
            data_contract.validation_snapshot
        ),
        "response_mask_version": PHASE40_RESPONSE_MASK_VERSION,
        "formatter_version": PHASE40_FORMATTER_VERSION,
    }
    for field_name, expected_value in expected_provenance.items():
        if trainer_result.get(field_name) != expected_value:
            raise RuntimeError(f"trainer result provenance mismatch: {field_name}")
    formatter_sha256 = trainer_result.get("formatter_sha256")
    if not isinstance(formatter_sha256, str) or len(formatter_sha256) != 64:
        raise RuntimeError("trainer result is missing formatter SHA-256 provenance")
    artifact_path_value = trainer_result.get("artifact_path")
    if not isinstance(artifact_path_value, (str, os.PathLike)):
        raise RuntimeError("trainer result is missing the selected adapter artifact path")
    artifact_path = Path(artifact_path_value)
    if artifact_path.resolve(strict=False) != _adapter_output_dir(config).resolve(strict=False):
        raise RuntimeError("trainer result returned a non-canonical adapter artifact path")
    retained_source_path = artifact_path / PHASE40_BASE_MODEL_MANIFEST_NAME
    if (
        not retained_source_path.is_file()
        or retained_source_path.is_symlink()
        or retained_source_path.read_bytes()
        != _canonical_json_line(base_model_snapshot.portable_manifest())
    ):
        raise RuntimeError("selected adapter lacks exact base-model source provenance")
    try:
        torch_module = importlib.import_module("torch")
    except ImportError as exc:
        raise RuntimeError("torch is required to verify the selected adapter artifact") from exc
    published_artifact_identity = _adapter_state_identity(
        _load_saved_adapter_state(artifact_path, torch_module=torch_module),
        torch_module=torch_module,
    )
    if published_artifact_identity != checkpoint_selection.selected_artifact_identity:
        raise RuntimeError(
            "selected checkpoint identity does not match the adapter artifact being returned"
        )
    evidence = _verify_full_run_evidence_for_publication(
        config,
        data_contract=data_contract,
        trainer_result=trainer_result,
        checkpoint_selection=checkpoint_selection,
    )
    return quantization_proof, checkpoint_selection, artifact_path, evidence


def run_phase40_qwen_training(
    config: TrainingConfig,
    *,
    data_contract: Phase40DataContract,
    run_request: RunRequest,
    repo_root: Path,
) -> dict[str, Any]:
    """Execute one request-bound Qwen comparison run without registry mutation."""

    if not isinstance(data_contract, Phase40DataContract):
        raise TypeError("comparison training requires a preflighted Phase40DataContract")
    _require_full_execution_authority(config)
    _authorize_phase40_qwen_request(
        config,
        data_contract=data_contract,
        run_request=run_request,
        repo_root=repo_root,
    )
    _prepare_full_run_bundle_root(config, create=False)

    candidate = get_candidate_by_id(config.candidate_id)
    train_examples = build_training_examples(
        [row.record for row in data_contract.train_snapshot.rows],
        candidate,
    )
    val_examples = build_training_examples(
        [row.record for row in data_contract.validation_snapshot.rows],
        candidate,
    )
    try:
        trainer_result = _run_local_adapter_training(
            config,
            train_examples,
            val_examples,
            data_contract,
        )
    except BaseException as exc:
        event_path = _evidence_root(config) / "events.jsonl"
        if not event_path.exists():
            event_path.parent.mkdir(parents=True, exist_ok=True)
            _append_runtime_failure_event(
                event_path,
                run_id=_resolved_run_id(config),
                run_kind=config.run_kind,
                requested_mode=config.adaptation_mode,
                error=exc,
            )
        raise

    quantization_proof, checkpoint_selection, artifact_path, evidence = (
        _validate_completed_full_training_result(
            config,
            data_contract=data_contract,
            trainer_result=trainer_result,
        )
    )
    return {
        "dry_run": False,
        "candidate_id": config.candidate_id,
        "run_id": _resolved_run_id(config),
        "run_kind": RunKind.FULL,
        "train_examples": len(train_examples),
        "val_examples": len(val_examples),
        "artifact_path": artifact_path,
        "artifact_record": None,
        "registry_published": False,
        "safety_gate_passed": checkpoint_selection.safety_gate_passed,
        "quantization_proof": quantization_proof,
        "verified_evidence": evidence,
        **{
            key: value
            for key, value in trainer_result.items()
            if key not in {"artifact_path", "quantization_proof", "verified_evidence"}
        },
    }


def build_phase40_local_decision_config(
    *,
    adaptation_mode: AdaptationMode | str,
    train_split_path: Path,
    val_split_path: Path,
    base_model_path: Path,
    decision_stage_root: Path,
) -> TrainingConfig:
    """Build the exact disposable RTX 5050 decision-run controls.

    The 45-step execution cap is deliberately separate from the 1,245-step
    full-run ETA denominator.  This is not the legacy ``smoke_test`` path.
    """

    mode = AdaptationMode(adaptation_mode)
    if mode not in {AdaptationMode.LORA, AdaptationMode.QLORA}:
        raise ValueError("local Qwen decision mode must be lora or qlora")
    stage_root = _normalized_absolute_path(Path(decision_stage_root))
    runtime_root = stage_root / "runtime"
    _reject_existing_symlink_traversal(
        stage_root,
        description="local decision stage root",
    )
    return TrainingConfig(
        candidate_id="qwen3-4b-instruct-2507",
        baseline_winner_id="qwen3-4b-instruct-2507",
        runner_up_id="qwen3.5-4b",
        train_split_path=Path(train_split_path),
        val_split_path=Path(val_split_path),
        version_tag="local-decision-work",
        output_root=runtime_root,
        registry_path=runtime_root / "unused-model-registry.json",
        adaptation_mode=mode,
        run_kind=RunKind.PROBE,
        model_id=PHASE40_QWEN_MODEL_ID,
        dry_run=False,
        base_model_path=_normalized_absolute_path(Path(base_model_path)),
        base_model_manifest_path=stage_root.parent / "base-model-provenance.json",
        num_train_epochs=3.0,
        max_steps=5 + 40,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=4,
        learning_rate=2e-4,
        logging_steps=10,
        save_steps=50,
        save_total_limit=2,
        max_seq_length=1024,
        smoke_test=False,
        resume_from_checkpoint=None,
        device="cuda",
        gradient_checkpointing=True,
        local_files_only=True,
        trust_remote_code=False,
        lora_r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        lora_bias="none",
        target_modules=DEFAULT_TARGET_MODULES,
        model_revision=PHASE40_QWEN_REVISION,
        run_id=f"rtx5050-{mode.value}",
        probe_post_warmup_steps=40,
        probe_warmup_steps=5,
        seed=42,
        data_seed=42,
        optimizer_name="adamw_torch",
        weight_decay=0.0,
        lr_scheduler_type="linear",
        warmup_steps=0,
        warmup_ratio=0.03,
        max_grad_norm=1.0,
        tf32=False,
        dataloader_num_workers=0,
        controller_stop_request_path=runtime_root / "stop-request.json",
        planned_full_optimizer_steps_override=1245,
        local_decision=True,
    )


def run_phase40_local_decision_child(
    config: TrainingConfig,
    *,
    data_contract: Phase40DataContract,
) -> dict[str, Any]:
    """Run one non-publishable child after the parent has sealed authority."""

    if not isinstance(config, TrainingConfig) or config.local_decision is not True:
        raise TypeError("local decision child requires its typed local TrainingConfig")
    if config.run_kind != RunKind.PROBE or config.resume_from_checkpoint is not None:
        raise RuntimeError("local decision child cannot resume or become a full run")
    if config.max_steps != 45 or config.planned_full_optimizer_steps_override != 1245:
        raise RuntimeError("local decision child lost its 45-step/1,245-step contract")
    selection = PilotSelection(
        baseline_winner_id="qwen3-4b-instruct-2507",
        runner_up_id="qwen3.5-4b",
        selection_notes="Disposable Phase 40 RTX 5050 local decision experiment",
    )
    result = run_training(config, data_contract=data_contract, selection=selection)
    if result.get("artifact_record") is not None or result.get("artifact_path") is not None:
        raise RuntimeError("local decision child returned a publishable adapter")
    return result


def run_training(
    config: TrainingConfig,
    *,
    data_contract: Phase40DataContract,
    selection: PilotSelection | None = None,
) -> dict[str, Any]:
    """Train only from an already-authorized immutable Phase 40 snapshot."""

    if not isinstance(data_contract, Phase40DataContract):
        raise TypeError("run_training requires a preflighted Phase40DataContract")

    resolved_selection = _resolve_selection(selection, config.registry_path if config.registry_path.exists() else None)
    if config.candidate_id not in _selected_candidate_ids(resolved_selection):
        raise ValueError("Training is limited to the pilot-selected baseline winner and runner-up")

    candidate = get_candidate_by_id(config.candidate_id)
    train_records = [row.record for row in data_contract.train_snapshot.rows]
    val_records = [row.record for row in data_contract.validation_snapshot.rows]
    train_examples = build_training_examples(train_records, candidate)
    val_examples = build_training_examples(val_records, candidate)

    if config.dry_run:
        return {
            "dry_run": True,
            "candidate_id": config.candidate_id,
            "train_examples": len(train_examples),
            "val_examples": len(val_examples),
            "requested_adaptation_mode": config.adaptation_mode.value,
            "artifact_record": None,
        }

    if config.run_kind == RunKind.FULL:
        _require_full_execution_authority(config)
        _prepare_full_run_bundle_root(config, create=False)

    if config.run_kind == RunKind.PROBE and config.probe_post_warmup_steps is None:
        raise RuntimeError(
            "probe discard/evidence lifecycle requires an explicit 30-50 "
            "post-warm-up optimizer-step target"
        )
    expected_probe_contract: ProbeExecutionContract | None = None
    if config.run_kind == RunKind.PROBE:
        expected_probe_contract = ProbeExecutionContract(
            run_id=_resolved_run_id(config),
            requested_identity=config.experiment_identity,
            target_post_warmup_steps=config.probe_post_warmup_steps,
            warmup_optimizer_steps=config.probe_warmup_steps,
            resume_from_checkpoint=config.resume_from_checkpoint,
        )

    try:
        trainer_result = _run_local_adapter_training(
            config,
            train_examples,
            val_examples,
            data_contract,
        )
    except BaseException as exc:
        event_path = _evidence_root(config) / "events.jsonl"
        if not event_path.exists():
            event_path.parent.mkdir(parents=True, exist_ok=True)
            _append_runtime_failure_event(
                event_path,
                run_id=_resolved_run_id(config),
                run_kind=config.run_kind,
                requested_mode=config.adaptation_mode,
                error=exc,
            )
        raise
    quantization_proof = _require_quantization_proof(
        config,
        trainer_result.get("quantization_proof"),
    )
    if config.run_kind == RunKind.PROBE:
        probe_contract = trainer_result.get("probe_contract")
        resource_summary = trainer_result.get("resource_summary")
        discard_receipt = trainer_result.get("discard_receipt")
        if not isinstance(probe_contract, ProbeExecutionContract):
            raise RuntimeError("probe trainer result is missing its typed execution contract")
        if probe_contract != expected_probe_contract:
            raise RuntimeError("probe trainer result drifted from its preflighted execution contract")
        if trainer_result.get("artifact_path") is not None:
            raise RuntimeError("probe trainer result retained a publishable adapter path")
        if trainer_result.get("resume_from_checkpoint") is not None:
            raise RuntimeError("probe trainer result retained forbidden resume lineage")
        require_completed_probe(
            contract=probe_contract,
            summary=resource_summary,
            discard_receipt=discard_receipt,
            probe_root=_probe_root(config),
        )
        event_path = trainer_result.get("events_path")
        if not isinstance(event_path, (str, os.PathLike)):
            raise RuntimeError("probe trainer result is missing append-only events")
        events = load_run_events(Path(event_path), expected_run_id=probe_contract.run_id)
        if any(event.run_kind != RunKind.PROBE for event in events):
            raise RuntimeError("probe event log contains non-probe lineage")
        return {
            "dry_run": False,
            "candidate_id": config.candidate_id,
            "run_id": probe_contract.run_id,
            "run_kind": RunKind.PROBE,
            "train_examples": len(train_examples),
            "val_examples": len(val_examples),
            "artifact_record": None,
            "quantization_proof": quantization_proof,
            **{key: value for key, value in trainer_result.items() if key != "artifact_path"},
        }

    checkpoint_selection = trainer_result.get("checkpoint_selection")
    if not isinstance(checkpoint_selection, CheckpointSelection):
        raise RuntimeError("trainer result is missing validated checkpoint selection evidence")
    if not checkpoint_selection.safety_gate_passed:
        raise RuntimeError(
            "selected checkpoint failed the Phase 40 safety gate; registry publication is blocked"
        )
    checkpoint_candidates = trainer_result.get("checkpoint_candidates")
    if not isinstance(checkpoint_candidates, tuple) or not checkpoint_candidates:
        raise RuntimeError("trainer result is missing checkpoint metric candidates")
    recomputed_selection = select_phase40_checkpoint(checkpoint_candidates)
    if recomputed_selection != checkpoint_selection:
        raise RuntimeError("checkpoint selection does not match retained metric candidates")
    if trainer_result.get("selected_artifact_identity") != checkpoint_selection.selected_artifact_identity:
        raise RuntimeError("published adapter identity does not match checkpoint selection evidence")
    expected_provenance = {
        "canonical_train_sha256": data_contract.train_snapshot.whole_file_sha256,
        "canonical_val_sha256": data_contract.validation_snapshot.whole_file_sha256,
        "canonical_train_row_ids_sha256": _snapshot_row_id_digest(data_contract.train_snapshot),
        "canonical_val_row_ids_sha256": _snapshot_row_id_digest(data_contract.validation_snapshot),
        "response_mask_version": PHASE40_RESPONSE_MASK_VERSION,
        "formatter_version": PHASE40_FORMATTER_VERSION,
    }
    for field_name, expected_value in expected_provenance.items():
        if trainer_result.get(field_name) != expected_value:
            raise RuntimeError(f"trainer result provenance mismatch: {field_name}")
    formatter_sha256 = trainer_result.get("formatter_sha256")
    if not isinstance(formatter_sha256, str) or len(formatter_sha256) != 64:
        raise RuntimeError("trainer result is missing formatter SHA-256 provenance")
    artifact_path_value = trainer_result.get("artifact_path")
    if not isinstance(artifact_path_value, (str, os.PathLike)):
        raise RuntimeError("trainer result is missing the selected adapter artifact path")
    artifact_path = Path(artifact_path_value)
    expected_artifact_path = _adapter_output_dir(config)
    if artifact_path.resolve(strict=False) != expected_artifact_path.resolve(strict=False):
        raise RuntimeError("trainer result returned a non-canonical adapter artifact path")
    try:
        torch_module = importlib.import_module("torch")
    except ImportError as exc:
        raise RuntimeError("torch is required to verify the selected adapter artifact") from exc
    published_artifact_identity = _adapter_state_identity(
        _load_saved_adapter_state(artifact_path, torch_module=torch_module),
        torch_module=torch_module,
    )
    if published_artifact_identity != checkpoint_selection.selected_artifact_identity:
        raise RuntimeError(
            "selected checkpoint identity does not match the adapter artifact being published"
        )
    _verify_full_run_evidence_for_publication(
        config,
        data_contract=data_contract,
        trainer_result=trainer_result,
        checkpoint_selection=checkpoint_selection,
    )
    require_registry_publication_allowed(
        run_kind=config.run_kind,
        evidence_complete=True,
        evidence_verified=True,
    )
    artifact_record = save_adapter_artifacts(
        config,
        selection=resolved_selection,
        artifact_source_path=artifact_path,
    )
    result = {
        "dry_run": False,
        "candidate_id": config.candidate_id,
        "train_examples": len(train_examples),
        "val_examples": len(val_examples),
        "artifact_record": artifact_record,
        "quantization_proof": quantization_proof,
    }
    result.update({key: value for key, value in trainer_result.items() if key != "artifact_path"})
    return result
