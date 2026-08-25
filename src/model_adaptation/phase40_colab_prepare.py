"""Freeze the launch-ready Phase 40 Colab transfer without touching Phase 41 data.

This is a preparation and verification CLI, not a training entry point.  It
preflights only the canonical train/validation snapshots, creates deterministic
source and input archives, freezes exact full-run controls, and writes an
operator handoff whose expensive actions remain explicit.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any, Mapping, Sequence

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.model_adaptation.phase40_contract import Phase40DataContract, preflight_phase40_inputs
from src.model_adaptation.phase40_evidence import (
    AcceleratorIdentity,
    CadenceControls,
    CanonicalSplitEvidence,
    DecoderContractEvidence,
    ExperimentIdentityEvidence,
    NamedControl,
    OptimizerControls,
    PrecisionControls,
    QuantizationProofEvidence,
    ResumeControlledConfig,
    compare_qwen_configs,
)
from src.model_adaptation.phase40_handoff import (
    FIXED_GGUF_TOOL_AUTHORITY_PATH,
    FIXED_INPUT_REPOSITORY_PATH,
    FIXED_MATCHED_QWEN_CONFIG_PATH,
    FIXED_PHOBERT_CONFIG_PATH,
    FIXED_RETURNED_ROOTS,
    FIXED_RUN_REQUEST_PATH,
    FIXED_SOURCE_ARCHIVE_PATH,
    FIXED_SOURCE_INVENTORY_PATH,
    PACKAGE_CANDIDATES,
    PINNED_PHOBERT_MODEL_ID,
    PINNED_PHOBERT_REVISION,
    PINNED_QWEN_MODEL_ID,
    PINNED_QWEN_REVISION,
    REQUIRED_FULL_BUNDLE_FILES,
    FullRunRequestIdentity,
    RequestedControlTemplate,
    RunRequest,
    build_phase40_input_bundle,
    build_phase40_source_bundle,
    freeze_phase40_run_request,
    load_frozen_phase40_run_request,
    verify_phase40_input_bundle,
    verify_phase40_source_bundle,
)
from src.model_adaptation.phase40_metrics import LABEL_ORDER
from src.model_adaptation.phase40_modes import (
    AdaptationMode,
    ModelFamily,
    ResolvedQwenMode,
    RunKind,
)
from src.model_adaptation.phase40_notebooks import validate_phase40_notebooks
from src.model_adaptation.phobert_training import (
    PHOBERT_PREPROCESSOR_SHA256,
    PHOBERT_PREPROCESSOR_VERSION,
    PHOBERT_SEGMENTER_PACKAGE,
    PHOBERT_SEGMENTER_VERSION,
)


PREPARATION_SCHEMA_VERSION = "phase40-colab-preparation-v1"
MATCHED_QWEN_SCHEMA_VERSION = "phase40-matched-qwen-controls-v1"
PHOBERT_CONFIG_SCHEMA_VERSION = "phase40-phobert-controls-v1"
GGUF_AUTHORITY_SCHEMA_VERSION = "phase40-gguf-tool-authority-v1"
QWEN_FORMATTER_SHA256 = "e75025061007de35e53c188cc23d6c3d678ed13bc991149e5ed2c793400489b5"
GGUF_PACKAGE = "gguf"
GGUF_PACKAGE_VERSION = "0.19.0"
GGUF_CONVERTER_BASENAME = "convert_hf_to_gguf.py"
GGUF_CONVERTER_SHA256 = "f227273d926fd8ba1c5215ca9ba64d63e641b3277e6f225080b4aac434999b55"
GGUF_OUTTYPE = "q8_0"
QWEN_FULL_OPTIMIZER_STEPS = 1245
PHOBERT_FULL_OPTIMIZER_STEPS = 312
FIXED_PREPARATION_MANIFEST_PATH = "data/models/phase40/colab-preparation-manifest.json"
FIXED_HANDOFF_PATH = (
    ".planning/phases/40-multi-model-training-evidence/40-COLAB-RUN-HANDOFF.md"
)
FIXED_LORA_PROOF_PATH = (
    "data/models/phase40/probes/rtx5050-local-decision/"
    "lora-retry-1/quantization-proof.json"
)
FIXED_QLORA_PROOF_PATH = (
    "data/models/phase40/probes/rtx5050-qlora-session-20260825/"
    "qlora/quantization-proof.json"
)
RUN_IDENTITIES = (
    ("phase40-qwen-lora-full-seed42-v1", ModelFamily.QWEN, AdaptationMode.LORA, FIXED_RETURNED_ROOTS[0]),
    ("phase40-qwen-qlora-full-seed42-v1", ModelFamily.QWEN, AdaptationMode.QLORA, FIXED_RETURNED_ROOTS[1]),
    (
        "phase40-phobert-full-seed42-v1",
        ModelFamily.PHOBERT,
        AdaptationMode.CLASSIFICATION_HEAD,
        FIXED_RETURNED_ROOTS[2],
    ),
)
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _canonical_json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _atomic_write(path: Path, payload: bytes) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        mode="wb", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
    )
    temporary = Path(handle.name)
    try:
        with handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()
    if path.read_bytes() != payload:
        raise RuntimeError(f"artifact read-back mismatch: {path}")
    return path


def _write_frozen(path: Path, payload: bytes) -> Path:
    path = Path(path)
    if path.exists():
        if not path.is_file() or path.is_symlink() or path.read_bytes() != payload:
            raise RuntimeError(f"frozen artifact already exists with different bytes: {path}")
        return path
    return _atomic_write(path, payload)


def _read_json_object(path: Path) -> dict[str, object]:
    path = Path(path)
    if not path.is_file() or path.is_symlink():
        raise FileNotFoundError(f"missing safe JSON artifact: {path}")
    value = json.loads(path.read_text(encoding="utf-8", errors="strict"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON artifact root must be an object: {path}")
    return value


def _repo_path(root: Path, relative: str) -> Path:
    candidate = Path(os.path.abspath(os.path.normpath(os.fspath(root / relative))))
    expected_root = Path(os.path.abspath(os.path.normpath(os.fspath(root))))
    try:
        candidate.relative_to(expected_root)
    except ValueError as exc:
        raise ValueError(f"repository artifact escapes root: {relative}") from exc
    return candidate


class GgufToolAuthority(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = GGUF_AUTHORITY_SCHEMA_VERSION
    package: str = GGUF_PACKAGE
    package_version: str = GGUF_PACKAGE_VERSION
    converter_basename: str = GGUF_CONVERTER_BASENAME
    converter_sha256: str = GGUF_CONVERTER_SHA256
    outtype: str = GGUF_OUTTYPE
    source_kind: str = "pypi-package"

    @field_validator("converter_sha256")
    @classmethod
    def validate_hash(cls, value: str) -> str:
        if not _SHA256_RE.fullmatch(value):
            raise ValueError("converter authority requires a lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_fixed_authority(self) -> "GgufToolAuthority":
        expected = (
            GGUF_AUTHORITY_SCHEMA_VERSION,
            GGUF_PACKAGE,
            GGUF_PACKAGE_VERSION,
            GGUF_CONVERTER_BASENAME,
            GGUF_CONVERTER_SHA256,
            GGUF_OUTTYPE,
            "pypi-package",
        )
        actual = (
            self.schema_version,
            self.package,
            self.package_version,
            self.converter_basename,
            self.converter_sha256,
            self.outtype,
            self.source_kind,
        )
        if actual != expected:
            raise ValueError("GGUF converter authority differs from the reviewed fixed identity")
        return self


class FrozenArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str
    bytes: int = Field(gt=0)
    sha256: str

    @field_validator("sha256")
    @classmethod
    def validate_hash(cls, value: str) -> str:
        if not _SHA256_RE.fullmatch(value):
            raise ValueError("artifact identity requires a lowercase SHA-256")
        return value


class ColabPreparationManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = PREPARATION_SCHEMA_VERSION
    artifacts: tuple[FrozenArtifact, ...]
    run_ids: tuple[str, str, str]
    qwen_full_optimizer_steps: int = QWEN_FULL_OPTIMIZER_STEPS
    phobert_full_optimizer_steps: int = PHOBERT_FULL_OPTIMIZER_STEPS
    no_held_out_boundary: bool = True

    @model_validator(mode="after")
    def validate_closed_manifest(self) -> "ColabPreparationManifest":
        paths = tuple(item.path for item in self.artifacts)
        if paths != tuple(sorted(paths)) or len(paths) != len(set(paths)):
            raise ValueError("preparation artifacts must be unique and sorted")
        expected_ids = tuple(item[0] for item in RUN_IDENTITIES)
        if self.run_ids != expected_ids:
            raise ValueError("preparation run identities are not the three fixed fresh runs")
        if (
            self.schema_version != PREPARATION_SCHEMA_VERSION
            or self.qwen_full_optimizer_steps != QWEN_FULL_OPTIMIZER_STEPS
            or self.phobert_full_optimizer_steps != PHOBERT_FULL_OPTIMIZER_STEPS
            or self.no_held_out_boundary is not True
        ):
            raise ValueError("preparation manifest changed its fixed execution boundary")
        return self


@dataclass(frozen=True, slots=True)
class PreparedColabHandoff:
    request: RunRequest
    request_path: Path
    manifest: ColabPreparationManifest
    manifest_path: Path
    handoff_path: Path


def _ordered_row_ids_sha256(member: Any) -> str:
    value = str(member.ordered_row_ids_sha256)
    if not _SHA256_RE.fullmatch(value):
        raise ValueError("input member row-ID sequence hash is invalid")
    return value


def _split_evidence(input_reference: Any) -> tuple[CanonicalSplitEvidence, CanonicalSplitEvidence]:
    return tuple(
        CanonicalSplitEvidence(
            logical_name=member.logical_name,
            relative_path=f"data/splits/{member.member_name}",
            records=member.records,
            bytes=member.bytes,
            sha256=member.sha256,
            ordered_row_ids_sha256=_ordered_row_ids_sha256(member),
        )
        for member in input_reference.data_members
    )  # type: ignore[return-value]


def _load_proof(path: Path, expected_mode: AdaptationMode) -> QuantizationProofEvidence:
    _read_json_object(path)
    proof = QuantizationProofEvidence.model_validate_json(path.read_bytes())
    if proof.requested_mode != expected_mode:
        raise ValueError(f"quantization proof at {path} has the wrong requested mode")
    return proof


def _qwen_control(
    *,
    mode: AdaptationMode,
    input_reference: Any,
    source_reference: Any,
    proof: QuantizationProofEvidence,
) -> ResumeControlledConfig:
    additional = tuple(
        sorted(
            (
                NamedControl(name="input_archive_sha256", value=input_reference.archive_sha256),
                NamedControl(name="input_manifest_sha256", value=input_reference.manifest_sha256),
                NamedControl(name="local_files_only", value=True),
                NamedControl(name="report_to", value="none"),
                NamedControl(name="save_safetensors", value=True),
                NamedControl(name="source_archive_sha256", value=source_reference.archive_sha256),
                NamedControl(name="source_inventory_sha256", value=source_reference.inventory_sha256),
                NamedControl(name="trust_remote_code", value=False),
            ),
            key=lambda item: item.name,
        )
    )
    generation_steps = tuple(range(50, QWEN_FULL_OPTIMIZER_STEPS + 1, 50))
    if generation_steps[-1] != QWEN_FULL_OPTIMIZER_STEPS:
        generation_steps += (QWEN_FULL_OPTIMIZER_STEPS,)
    return ResumeControlledConfig(
        schema_version="phase40-resume-controlled-config-v1",
        experiment_identity=ExperimentIdentityEvidence(
            model_family=ModelFamily.QWEN,
            adaptation_mode=mode,
            run_kind=RunKind.FULL,
        ),
        model_id=PINNED_QWEN_MODEL_ID,
        model_revision=PINNED_QWEN_REVISION,
        splits=_split_evidence(input_reference),
        formatter_or_preprocessor_sha256=QWEN_FORMATTER_SHA256,
        response_mask_or_preprocessor_version="phase40-response-only-mask-v1",
        label_order=tuple(LABEL_ORDER),
        seed=42,
        data_seed=42,
        max_sequence_length=1024,
        truncation_policy="reject-over-max",
        per_device_train_batch_size=1,
        gradient_accumulation_steps=4,
        world_size=1,
        effective_batch_size=4,
        num_train_epochs=3.0,
        max_optimizer_steps=QWEN_FULL_OPTIMIZER_STEPS,
        gradient_checkpointing=True,
        lora_rank=16,
        lora_alpha=32,
        lora_dropout=0.05,
        lora_bias="none",
        target_modules=(
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ),
        task_type="CAUSAL_LM",
        optimizer=OptimizerControls(
            optimizer="adamw_torch",
            learning_rate=2e-4,
            weight_decay=0.0,
            lr_scheduler_type="linear",
            warmup_steps=0,
            warmup_ratio=0.03,
            max_grad_norm=1.0,
        ),
        precision=PrecisionControls(
            compute_dtype="bfloat16",
            # PEFT 0.19.1 defaults autocast_adapter_dtype=True, so both the
            # BF16 LoRA path and the 4-bit QLoRA path train FP32 adapters.
            adapter_dtype="float32",
            bf16=True,
            fp16=False,
            tf32=False,
        ),
        cadence=CadenceControls(
            logging_steps=10,
            evaluation_steps=50,
            save_steps=50,
            save_total_limit=2,
            generation_steps=generation_steps,
        ),
        decoder=DecoderContractEvidence(
            schema_version="phase40-qwen-decoder-v1",
            do_sample=False,
            num_return_sequences=1,
            max_new_tokens=256,
            output_schema_version="phase40-prediction-row-v1",
            decoder_version="phase40-qwen-greedy-v1",
            generation_cadence="every-validation-checkpoint-and-final",
            raw_prediction_ordering_policy="canonical-validation-sequence",
        ),
        checkpoint_selection_policy="macro-f1-safety-gate",
        checkpoint_selection_policy_version="phase40-checkpoint-selection-v1",
        snapshot_id_algorithm_version="phase40-snapshot-row-id-v1",
        quantization_proof=proof,
        accelerator=AcceleratorIdentity(
            accelerator_type="operator-supplied",
            accelerator_name="operator-supplied",
            compute_capability=None,
            total_memory_bytes=0,
        ),
        additional_controls=additional,
    )


def _phobert_control(*, input_reference: Any, source_reference: Any) -> ResumeControlledConfig:
    additional = (
        NamedControl(name="dynamic_padding", value=True),
        NamedControl(name="input_archive_sha256", value=input_reference.archive_sha256),
        NamedControl(name="input_manifest_sha256", value=input_reference.manifest_sha256),
        NamedControl(name="local_files_only", value=True),
        NamedControl(name="report_to", value="none"),
        NamedControl(name="segmenter_package", value=PHOBERT_SEGMENTER_PACKAGE),
        NamedControl(name="segmenter_version", value=PHOBERT_SEGMENTER_VERSION),
        NamedControl(name="source_archive_sha256", value=source_reference.archive_sha256),
        NamedControl(name="source_inventory_sha256", value=source_reference.inventory_sha256),
        NamedControl(name="trust_remote_code", value=False),
    )
    schedule = tuple(range(50, PHOBERT_FULL_OPTIMIZER_STEPS + 1, 50))
    if schedule[-1] != PHOBERT_FULL_OPTIMIZER_STEPS:
        schedule += (PHOBERT_FULL_OPTIMIZER_STEPS,)
    return ResumeControlledConfig(
        schema_version="phase40-resume-controlled-config-v1",
        experiment_identity=ExperimentIdentityEvidence(
            model_family=ModelFamily.PHOBERT,
            adaptation_mode=AdaptationMode.CLASSIFICATION_HEAD,
            run_kind=RunKind.FULL,
        ),
        model_id=PINNED_PHOBERT_MODEL_ID,
        model_revision=PINNED_PHOBERT_REVISION,
        splits=_split_evidence(input_reference),
        formatter_or_preprocessor_sha256=PHOBERT_PREPROCESSOR_SHA256,
        response_mask_or_preprocessor_version=PHOBERT_PREPROCESSOR_VERSION,
        label_order=tuple(LABEL_ORDER),
        seed=42,
        data_seed=42,
        max_sequence_length=256,
        truncation_policy="right-token-truncate-record-v1",
        per_device_train_batch_size=16,
        gradient_accumulation_steps=1,
        world_size=1,
        effective_batch_size=16,
        num_train_epochs=3.0,
        max_optimizer_steps=PHOBERT_FULL_OPTIMIZER_STEPS,
        gradient_checkpointing=False,
        lora_rank=None,
        lora_alpha=None,
        lora_dropout=None,
        lora_bias=None,
        target_modules=(),
        task_type="sequence-classification",
        optimizer=OptimizerControls(
            optimizer="adamw_torch",
            learning_rate=2e-5,
            weight_decay=0.01,
            lr_scheduler_type="linear",
            warmup_steps=0,
            warmup_ratio=0.03,
            max_grad_norm=1.0,
        ),
        precision=PrecisionControls(
            compute_dtype="float16",
            adapter_dtype="not-applicable",
            bf16=False,
            fp16=True,
            tf32=False,
        ),
        cadence=CadenceControls(
            logging_steps=10,
            evaluation_steps=50,
            save_steps=50,
            save_total_limit=2,
            generation_steps=schedule,
        ),
        decoder=None,
        checkpoint_selection_policy=(
            "risky-recall-zero-invalid-macro-f1-risky-benign-earlier-step-v1"
        ),
        checkpoint_selection_policy_version="phase40-checkpoint-selection-v1",
        snapshot_id_algorithm_version="phase40-snapshot-row-id-v1",
        quantization_proof=None,
        accelerator=AcceleratorIdentity(
            accelerator_type="operator-supplied",
            accelerator_name="operator-supplied",
            compute_capability=None,
            total_memory_bytes=0,
        ),
        additional_controls=additional,
    )


def _template(control: ResumeControlledConfig) -> RequestedControlTemplate:
    payload = control.model_dump(mode="json")
    payload.pop("accelerator")
    return RequestedControlTemplate(controls_without_accelerator=payload)


def build_launch_ready_request(
    *,
    input_reference: Any,
    source_reference: Any,
    lora_proof: QuantizationProofEvidence,
    qlora_proof: QuantizationProofEvidence,
) -> tuple[RunRequest, dict[str, ResumeControlledConfig]]:
    controls = {
        RUN_IDENTITIES[0][0]: _qwen_control(
            mode=AdaptationMode.LORA,
            input_reference=input_reference,
            source_reference=source_reference,
            proof=lora_proof,
        ),
        RUN_IDENTITIES[1][0]: _qwen_control(
            mode=AdaptationMode.QLORA,
            input_reference=input_reference,
            source_reference=source_reference,
            proof=qlora_proof,
        ),
        RUN_IDENTITIES[2][0]: _phobert_control(
            input_reference=input_reference,
            source_reference=source_reference,
        ),
    }
    templates = {run_id: _template(control) for run_id, control in controls.items()}
    request = RunRequest(
        runs=tuple(
            FullRunRequestIdentity(
                run_id=run_id,
                model_family=family,
                adaptation_mode=mode,
                returned_root=root,
            )
            for run_id, family, mode, root in RUN_IDENTITIES
        ),
        source_bundle=source_reference,
        input_bundle=input_reference,
        package_candidates=PACKAGE_CANDIDATES,
        expected_bundle_files=REQUIRED_FULL_BUNDLE_FILES,
        control_template_by_run=templates,
        control_template_digest_by_run={
            run_id: template.sha256 for run_id, template in templates.items()
        },
        no_held_out_boundary=True,
        git_commit=None,
    )
    verify_launch_ready_request(request)
    return request, controls


def verify_launch_ready_request(request: RunRequest) -> RunRequest:
    """Enforce the production profile beyond the generic fixture-capable schema."""

    request = request if isinstance(request, RunRequest) else RunRequest.model_validate(request)
    if tuple(run.run_id for run in request.runs) != tuple(item[0] for item in RUN_IDENTITIES):
        raise ValueError("launch request run IDs/order differ from the production profile")
    controls = {
        run_id: template.materialize_for_validation()
        for run_id, template in request.control_template_by_run.items()
    }
    lora = controls[RUN_IDENTITIES[0][0]]
    qlora = controls[RUN_IDENTITIES[1][0]]
    phobert = controls[RUN_IDENTITIES[2][0]]
    comparison = compare_qwen_configs(lora, qlora)
    if not comparison.admissible or comparison.forbidden_differences:
        raise ValueError("production Qwen full controls differ beyond quantization")
    for qwen in (lora, qlora):
        if (
            qwen.num_train_epochs != 3.0
            or qwen.max_optimizer_steps != QWEN_FULL_OPTIMIZER_STEPS
            or qwen.per_device_train_batch_size != 1
            or qwen.gradient_accumulation_steps != 4
            or qwen.effective_batch_size != 4
            or qwen.max_sequence_length != 1024
            or qwen.optimizer.learning_rate != 2e-4
            or qwen.optimizer.warmup_ratio != 0.03
            or qwen.cadence.logging_steps != 10
            or qwen.cadence.evaluation_steps != 50
            or qwen.cadence.save_steps != 50
            or qwen.precision.bf16 is not True
            or qwen.precision.fp16 is not False
        ):
            raise ValueError("Qwen launch controls differ from the exact 3-epoch/1,245-step profile")
    if lora.quantization_proof is None or lora.quantization_proof.resolved_mode != ResolvedQwenMode.FULL_PRECISION_LORA:
        raise ValueError("LoRA launch controls lack the ordinary unquantized proof contract")
    if qlora.quantization_proof is None or qlora.quantization_proof.resolved_mode != ResolvedQwenMode.FOUR_BIT_QLORA:
        raise ValueError("QLoRA launch controls lack the genuine NF4 proof contract")
    if (
        phobert.num_train_epochs != 3.0
        or phobert.max_optimizer_steps != PHOBERT_FULL_OPTIMIZER_STEPS
        or phobert.per_device_train_batch_size != 16
        or phobert.max_sequence_length != 256
        or phobert.optimizer.learning_rate != 2e-5
        or phobert.optimizer.warmup_ratio != 0.03
        or phobert.task_type != "sequence-classification"
    ):
        raise ValueError("PhoBERT launch controls differ from the exact full baseline profile")
    if any(run.step_origin != 0 or run.probe_parent is not None for run in request.runs):
        raise ValueError("all production full runs must start fresh at optimizer step zero")
    return request


def _matched_qwen_payload(
    controls: Mapping[str, ResumeControlledConfig],
) -> dict[str, object]:
    lora = controls[RUN_IDENTITIES[0][0]]
    qlora = controls[RUN_IDENTITIES[1][0]]
    comparison = compare_qwen_configs(lora, qlora)
    return {
        "schema_version": MATCHED_QWEN_SCHEMA_VERSION,
        "planned_optimizer_steps": QWEN_FULL_OPTIMIZER_STEPS,
        "num_train_epochs": 3.0,
        "lora": lora.model_dump(mode="json"),
        "qlora": qlora.model_dump(mode="json"),
        "comparison": comparison.model_dump(mode="json"),
        "probe_step_cap_is_not_full_run": 45,
    }


def _phobert_payload(controls: Mapping[str, ResumeControlledConfig]) -> dict[str, object]:
    return {
        "schema_version": PHOBERT_CONFIG_SCHEMA_VERSION,
        "planned_optimizer_steps": PHOBERT_FULL_OPTIMIZER_STEPS,
        "num_train_epochs": 3.0,
        "control": controls[RUN_IDENTITIES[2][0]].model_dump(mode="json"),
    }


def _artifact(path: Path, *, root: Path) -> FrozenArtifact:
    payload = path.read_bytes()
    relative = path.relative_to(root).as_posix()
    return FrozenArtifact(path=relative, bytes=len(payload), sha256=_sha256(payload))


def _handoff_markdown(request: RunRequest, manifest: ColabPreparationManifest) -> bytes:
    qwen = request.control_template_by_run[RUN_IDENTITIES[1][0]].materialize_for_validation()
    lines = [
        "# Phase 40 Colab run handoff",
        "",
        "Status: frozen and launch-ready after the local QLoRA proof was imported as a control expectation.",
        "",
        "Run each notebook in a fresh Colab runtime. Do not reuse a probe adapter or a previous notebook runtime. "
        "The canonical input contains train and validation only; the reserved Phase 41 partition is not transferred.",
        "",
        "## Upload once to Drive",
        "",
        "Copy the repository `data/models/phase40/` authority artifacts beneath "
        "`/content/drive/MyDrive/internship-phase40/repository/data/models/phase40/` and copy the exact input archive to "
        "`/content/drive/MyDrive/internship-phase40/phase40-train-validation.zip`. Do not rename either authority.",
        "",
        "## Run order",
        "",
        "1. `notebooks/phase40/qwen_lora_colab.ipynb`",
        "2. `notebooks/phase40/qwen_qlora_colab.ipynb`",
        "3. `notebooks/phase40/phobert_colab.ipynb`",
        "",
        "Each notebook verifies source, request, model snapshot, and exact input archive before training. "
        "It persists command logs, raw training events, trainer state, validation predictions, deterministic graphs, and the complete returned bundle in Drive.",
        "",
        "The Qwen full runs are both 3 epochs / 1,245 optimizer steps at effective batch 4. "
        "The local 5+40 QLoRA cap is probe evidence only and is not used by either full run.",
        "",
        "Qwen GGUF export uses `gguf==0.19.0`, the request-independent reviewed converter script hash "
        f"`{GGUF_CONVERTER_SHA256}`, and locked `q8_0`. Browser download remains a separate optional human-run cell after manifest verification.",
        "",
        "## Frozen identities",
        "",
        f"- Request SHA-256: `{next(item.sha256 for item in manifest.artifacts if item.path == FIXED_RUN_REQUEST_PATH)}`",
        f"- Input archive SHA-256: `{request.input_bundle.archive_sha256}`",
        f"- Source archive SHA-256: `{request.source_bundle.archive_sha256}`",
        f"- QLoRA full steps: `{qwen.max_optimizer_steps}`",
        "",
        "A complete run may resume only from one exact compatibility-verified checkpoint. A fresh run always starts at step zero.",
        "",
    ]
    return "\n".join(lines).encode("utf-8")


def _verify_frozen_configs(root: Path, request: RunRequest) -> dict[str, ResumeControlledConfig]:
    qwen_payload = _read_json_object(_repo_path(root, FIXED_MATCHED_QWEN_CONFIG_PATH))
    phobert_payload = _read_json_object(_repo_path(root, FIXED_PHOBERT_CONFIG_PATH))
    if qwen_payload.get("schema_version") != MATCHED_QWEN_SCHEMA_VERSION:
        raise ValueError("matched Qwen config schema is invalid")
    if phobert_payload.get("schema_version") != PHOBERT_CONFIG_SCHEMA_VERSION:
        raise ValueError("PhoBERT config schema is invalid")
    controls = {
        RUN_IDENTITIES[0][0]: ResumeControlledConfig.model_validate_json(
            _canonical_json_bytes(qwen_payload.get("lora"))
        ),
        RUN_IDENTITIES[1][0]: ResumeControlledConfig.model_validate_json(
            _canonical_json_bytes(qwen_payload.get("qlora"))
        ),
        RUN_IDENTITIES[2][0]: ResumeControlledConfig.model_validate_json(
            _canonical_json_bytes(phobert_payload.get("control"))
        ),
    }
    for run_id, control in controls.items():
        request.control_template_by_run[run_id].verify_runtime_config(control)
    if qwen_payload != _matched_qwen_payload(controls):
        raise ValueError("matched Qwen config bytes do not represent the exact controls")
    if phobert_payload != _phobert_payload(controls):
        raise ValueError("PhoBERT config bytes do not represent the exact controls")
    return controls


def _preparation_artifact_paths(root: Path) -> tuple[Path, ...]:
    return tuple(
        _repo_path(root, relative)
        for relative in (
            FIXED_GGUF_TOOL_AUTHORITY_PATH,
            FIXED_INPUT_REPOSITORY_PATH,
            FIXED_MATCHED_QWEN_CONFIG_PATH,
            FIXED_PHOBERT_CONFIG_PATH,
            FIXED_RUN_REQUEST_PATH,
            FIXED_SOURCE_ARCHIVE_PATH,
            FIXED_SOURCE_INVENTORY_PATH,
        )
    )


def verify_colab_handoff(repo_root: Path) -> PreparedColabHandoff:
    root = Path(repo_root).resolve(strict=True)
    issues = validate_phase40_notebooks(root / "notebooks/phase40")
    if issues:
        raise RuntimeError("canonical notebook validation failed: " + "; ".join(map(str, issues[:5])))
    request = load_frozen_phase40_run_request(repo_root=root)
    verify_launch_ready_request(request)
    controls = _verify_frozen_configs(root, request)
    verify_launch_ready_request(request)
    authority = GgufToolAuthority.model_validate(
        _read_json_object(_repo_path(root, FIXED_GGUF_TOOL_AUTHORITY_PATH))
    )
    if authority != GgufToolAuthority():
        raise ValueError("GGUF authority changed")
    paths = _preparation_artifact_paths(root)
    expected_manifest = ColabPreparationManifest(
        artifacts=tuple(sorted((_artifact(path, root=root) for path in paths), key=lambda item: item.path)),
        run_ids=tuple(item[0] for item in RUN_IDENTITIES),
    )
    manifest_path = _repo_path(root, FIXED_PREPARATION_MANIFEST_PATH)
    actual_manifest = ColabPreparationManifest.model_validate(
        _read_json_object(manifest_path)
    )
    if actual_manifest != expected_manifest:
        raise ValueError("Colab preparation manifest differs from current frozen artifacts")
    handoff_path = _repo_path(root, FIXED_HANDOFF_PATH)
    expected_handoff = _handoff_markdown(request, actual_manifest)
    if not handoff_path.is_file() or handoff_path.is_symlink() or handoff_path.read_bytes() != expected_handoff:
        raise ValueError("Colab operator handoff is missing or differs from frozen authorities")
    # Keep explicit references alive for static analyzers and guard against a
    # future accidental dead-code removal of config verification.
    if len(controls) != 3:
        raise RuntimeError("exactly three frozen controls are required")
    return PreparedColabHandoff(
        request=request,
        request_path=_repo_path(root, FIXED_RUN_REQUEST_PATH),
        manifest=actual_manifest,
        manifest_path=manifest_path,
        handoff_path=handoff_path,
    )


def prepare_colab_handoff(
    repo_root: Path,
    *,
    lora_proof_path: Path | None = None,
    qlora_proof_path: Path | None = None,
) -> PreparedColabHandoff:
    root = Path(repo_root).resolve(strict=True)
    request_path = _repo_path(root, FIXED_RUN_REQUEST_PATH)
    if request_path.exists():
        return verify_colab_handoff(root)
    issues = validate_phase40_notebooks(root / "notebooks/phase40")
    if issues:
        raise RuntimeError("canonical notebook validation failed: " + "; ".join(map(str, issues[:5])))
    lora_proof = _load_proof(
        Path(lora_proof_path or _repo_path(root, FIXED_LORA_PROOF_PATH)),
        AdaptationMode.LORA,
    )
    qlora_proof = _load_proof(
        Path(qlora_proof_path or _repo_path(root, FIXED_QLORA_PROOF_PATH)),
        AdaptationMode.QLORA,
    )
    contract: Phase40DataContract = preflight_phase40_inputs(
        root / "data/splits/train.jsonl",
        root / "data/splits/val.jsonl",
        repo_root=root,
    )
    for returned_root in FIXED_RETURNED_ROOTS:
        if _repo_path(root, returned_root).exists():
            raise RuntimeError(f"fresh full-run returned root already exists: {returned_root}")
    input_bundle = build_phase40_input_bundle(
        contract,
        _repo_path(root, FIXED_INPUT_REPOSITORY_PATH),
        repo_root=root,
    )
    verify_phase40_input_bundle(
        input_bundle.archive_path,
        input_bundle.reference,
        repo_root=root,
        materialize=False,
    )
    source_bundle = build_phase40_source_bundle(
        root,
        _repo_path(root, FIXED_SOURCE_ARCHIVE_PATH).parent,
    )
    verify_phase40_source_bundle(repo_root=root, reference=source_bundle.reference)
    request, controls = build_launch_ready_request(
        input_reference=input_bundle.reference,
        source_reference=source_bundle.reference,
        lora_proof=lora_proof,
        qlora_proof=qlora_proof,
    )
    _write_frozen(
        _repo_path(root, FIXED_MATCHED_QWEN_CONFIG_PATH),
        _canonical_json_bytes(_matched_qwen_payload(controls)),
    )
    _write_frozen(
        _repo_path(root, FIXED_PHOBERT_CONFIG_PATH),
        _canonical_json_bytes(_phobert_payload(controls)),
    )
    _write_frozen(
        _repo_path(root, FIXED_GGUF_TOOL_AUTHORITY_PATH),
        _canonical_json_bytes(GgufToolAuthority().model_dump(mode="json")),
    )
    freeze_phase40_run_request(request, repo_root=root)
    paths = _preparation_artifact_paths(root)
    manifest = ColabPreparationManifest(
        artifacts=tuple(sorted((_artifact(path, root=root) for path in paths), key=lambda item: item.path)),
        run_ids=tuple(item[0] for item in RUN_IDENTITIES),
    )
    manifest_path = _write_frozen(
        _repo_path(root, FIXED_PREPARATION_MANIFEST_PATH),
        _canonical_json_bytes(manifest.model_dump(mode="json")),
    )
    handoff_path = _write_frozen(
        _repo_path(root, FIXED_HANDOFF_PATH),
        _handoff_markdown(request, manifest),
    )
    return verify_colab_handoff(root)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="phase40-colab-prepare",
        description="Freeze or verify the train/validation-only Phase 40 Colab handoff",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare = subparsers.add_parser("prepare")
    prepare.add_argument("--repo-root", type=Path, default=Path("."))
    prepare.add_argument("--lora-proof", type=Path, default=None)
    prepare.add_argument("--qlora-proof", type=Path, default=None)
    verify = subparsers.add_parser("verify")
    verify.add_argument("--repo-root", type=Path, default=Path("."))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "prepare":
            result = prepare_colab_handoff(
                args.repo_root,
                lora_proof_path=args.lora_proof,
                qlora_proof_path=args.qlora_proof,
            )
        else:
            result = verify_colab_handoff(args.repo_root)
    except (FileNotFoundError, OSError, RuntimeError, TypeError, ValueError) as exc:
        print(str(exc), file=os.sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "handoff_path": result.handoff_path.as_posix(),
                "manifest_path": result.manifest_path.as_posix(),
                "request_path": result.request_path.as_posix(),
                "run_ids": list(result.manifest.run_ids),
                "verified": True,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "ColabPreparationManifest",
    "GGUF_CONVERTER_SHA256",
    "GgufToolAuthority",
    "PreparedColabHandoff",
    "build_launch_ready_request",
    "prepare_colab_handoff",
    "verify_colab_handoff",
    "verify_launch_ready_request",
]
