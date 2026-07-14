# ============================================================
# STEP 6 of 10 — Merge Adapter + Export to GGUF Q8_0
# ============================================================
# Canonical source (this numbered copy exists ONLY for defense-day
# navigation — it is not a second implementation and is not imported
# by anything): src/model_adaptation/convert.py
#
# What this file does: takes the adapter saved in step 5,
# _materialize_merged_model() merges the LoRA weights back into the
# base model (PeftModel.merge_and_unload — the model becomes one dense
# model again), then shells out to llama.cpp's convert_hf_to_gguf.py
# (and optionally llama-quantize) to produce the final .gguf file at
# 8-bit precision. register_gguf_artifact() records it in the model
# registry, which step 10 (GGUFAnalyzer) reads at inference time.
#
# See also: documents/reports/supervisor/defense_code_navigation.md
# ============================================================

"""GGUF conversion helpers for Phase 3 local deployment artifacts."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from src.config.settings import get_settings
from src.model_adaptation.registry import build_model_checksum, find_latest_artifact, load_model_registry, save_model_registry
from src.model_adaptation.schemas import ModelArtifactRecord, ModelRegistry, PilotSelection
from src.model_adaptation.training import _load_download_manifest


GGUF_CONVERTER_SCRIPT_ENV = "GGUF_CONVERTER_SCRIPT"
GGUF_QUANTIZE_BIN_ENV = "GGUF_QUANTIZE_BIN"
GGUF_KEEP_MERGED_MODEL_ENV = "GGUF_KEEP_MERGED_MODEL"
GGUF_DIRECT_OUTTYPES = {"f32", "f16", "bf16", "q8_0", "tq1_0", "tq2_0", "auto"}
GGUF_SETUP_GUIDE = (
    "Install a GGUF conversion toolchain such as llama.cpp's convert_hf_to_gguf.py and set "
    f"{GGUF_CONVERTER_SCRIPT_ENV} to that script path. For q4_k_m-style quantization, also provide "
    f"{GGUF_QUANTIZE_BIN_ENV} or a built llama-quantize binary."
)


@dataclass(frozen=True)
class GGUFConversionRequest:
    """Resolved request for converting one registered adapter into a GGUF artifact."""

    candidate_id: str
    version_tag: str
    adapter_path: Path
    base_model_path: Path
    output_path: Path
    quantization_profile: str
    profile_name: str


def _resolve_selection(selection: PilotSelection | None, registry_path: Path) -> PilotSelection:
    if selection is not None:
        return selection
    registry = load_model_registry(registry_path)
    if registry.selection is None:
        raise ValueError("Model registry does not contain a pilot selection")
    return registry.selection


def _resolve_base_model_path(candidate_id: str, output_root: Path) -> Path:
    manifest_model_paths = _load_download_manifest(output_root)
    manifest_path = manifest_model_paths.get(candidate_id)
    if manifest_path is not None and manifest_path.exists():
        return manifest_path

    fallback_path = output_root / "base" / candidate_id
    if fallback_path.exists():
        return fallback_path

    raise FileNotFoundError(
        f"Missing base model for candidate_id={candidate_id}. "
        f"Expected {output_root / 'manifests' / 'download-manifest.json'} or {fallback_path}"
    )


def _resolve_converter_script() -> Path:
    configured_path = os.environ.get(GGUF_CONVERTER_SCRIPT_ENV, "").strip()
    if configured_path:
        script_path = Path(configured_path)
        if script_path.exists():
            return script_path
        raise FileNotFoundError(f"Configured GGUF converter script does not exist: {script_path}")

    candidate_paths = [
        Path.cwd() / "tools" / "llama.cpp" / "convert_hf_to_gguf.py",
        Path(__file__).resolve().parents[2] / "tools" / "llama.cpp" / "convert_hf_to_gguf.py",
    ]
    for script_path in candidate_paths:
        if script_path.exists():
            return script_path

    raise RuntimeError(GGUF_SETUP_GUIDE)


def _resolve_quantize_binary(script_path: Path) -> Path | None:
    configured_path = os.environ.get(GGUF_QUANTIZE_BIN_ENV, "").strip()
    if configured_path:
        quantize_path = Path(configured_path)
        if quantize_path.exists():
            return quantize_path
        raise FileNotFoundError(f"Configured GGUF quantize binary does not exist: {quantize_path}")

    tool_root = script_path.parent
    candidate_paths = [
        tool_root / "llama-quantize",
        tool_root / "llama-quantize.exe",
        tool_root / "build" / "bin" / "llama-quantize",
        tool_root / "build" / "bin" / "llama-quantize.exe",
        tool_root / "build" / "bin" / "Release" / "llama-quantize.exe",
    ]
    for quantize_path in candidate_paths:
        if quantize_path.exists():
            return quantize_path
    return None


def _materialize_merged_model(request: GGUFConversionRequest, merged_model_dir: Path) -> None:
    import importlib

    torch_module = importlib.import_module("torch")
    transformers_module = importlib.import_module("transformers")
    peft_module = importlib.import_module("peft")

    device = "cuda" if torch_module.cuda.is_available() else "cpu"
    model_load_kwargs: dict[str, object] = {
        "local_files_only": True,
        "trust_remote_code": True,
        "low_cpu_mem_usage": True,
    }
    if device == "cuda":
        model_load_kwargs["device_map"] = {"": 0}
        model_load_kwargs["torch_dtype"] = (
            torch_module.bfloat16 if torch_module.cuda.is_bf16_supported() else torch_module.float16
        )
    else:
        model_load_kwargs["torch_dtype"] = torch_module.float32

    tokenizer = transformers_module.AutoTokenizer.from_pretrained(
        str(request.base_model_path),
        local_files_only=True,
        trust_remote_code=True,
    )
    model = transformers_module.AutoModelForCausalLM.from_pretrained(
        str(request.base_model_path),
        **model_load_kwargs,
    )
    peft_model = peft_module.PeftModel.from_pretrained(
        model,
        str(request.adapter_path),
        is_trainable=False,
    )
    merged_model = peft_model.merge_and_unload() if hasattr(peft_model, "merge_and_unload") else peft_model

    merged_model_dir.mkdir(parents=True, exist_ok=True)
    merged_model.save_pretrained(str(merged_model_dir), safe_serialization=True)
    tokenizer.save_pretrained(str(merged_model_dir))


def _invoke_converter_script(
    script_path: Path,
    merged_model_dir: Path,
    output_path: Path,
    outtype: str,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        str(script_path),
        str(merged_model_dir),
        "--outfile",
        str(output_path),
        "--outtype",
        outtype,
    ]
    completed = subprocess.run(command, check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        stderr = completed.stderr.strip()
        stdout = completed.stdout.strip()
        detail = stderr or stdout or "unknown converter failure"
        raise RuntimeError(f"GGUF conversion failed: {detail}")
    if not output_path.exists():
        raise RuntimeError(f"GGUF converter finished without producing output: {output_path}")
    return output_path


def _invoke_quantize_binary(
    quantize_path: Path,
    input_path: Path,
    output_path: Path,
    quantization_profile: str,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        str(quantize_path),
        str(input_path),
        str(output_path),
        quantization_profile.upper(),
    ]
    completed = subprocess.run(command, check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        stderr = completed.stderr.strip()
        stdout = completed.stdout.strip()
        detail = stderr or stdout or "unknown quantizer failure"
        raise RuntimeError(f"GGUF quantization failed: {detail}")
    if not output_path.exists():
        raise RuntimeError(f"GGUF quantizer finished without producing output: {output_path}")
    return output_path


def _run_default_converter(request: GGUFConversionRequest) -> Path:
    script_path = _resolve_converter_script()
    keep_merged = os.environ.get(GGUF_KEEP_MERGED_MODEL_ENV, "").strip().casefold() in {"1", "true", "yes"}

    def convert_from_directory(merged_model_dir: Path) -> Path:
        requested_outtype = request.quantization_profile.casefold()
        if requested_outtype in GGUF_DIRECT_OUTTYPES:
            return _invoke_converter_script(
                script_path,
                merged_model_dir,
                request.output_path,
                requested_outtype,
            )

        quantize_path = _resolve_quantize_binary(script_path)
        if quantize_path is None:
            raise RuntimeError(
                f"Quantization profile {request.quantization_profile!r} requires a llama-quantize binary. {GGUF_SETUP_GUIDE}"
            )

        intermediate_path = request.output_path.with_suffix(".f16.gguf")
        _invoke_converter_script(script_path, merged_model_dir, intermediate_path, "f16")
        try:
            return _invoke_quantize_binary(
                quantize_path,
                intermediate_path,
                request.output_path,
                request.quantization_profile,
            )
        finally:
            if intermediate_path.exists():
                intermediate_path.unlink()

    if keep_merged:
        merged_model_dir = request.output_path.parent / f"{request.profile_name}-merged-hf"
        if merged_model_dir.exists():
            shutil.rmtree(merged_model_dir)
        _materialize_merged_model(request, merged_model_dir)
        return convert_from_directory(merged_model_dir)

    with tempfile.TemporaryDirectory(prefix="phase3-gguf-") as temp_dir:
        merged_model_dir = Path(temp_dir) / "merged-model"
        _materialize_merged_model(request, merged_model_dir)
        return convert_from_directory(merged_model_dir)


def build_gguf_request(
    candidate_id: str,
    version_tag: str,
    *,
    registry_path: Path | None = None,
    output_root: Path | None = None,
    selection: PilotSelection | None = None,
    quantization_profile: str = "q4_k_m",
) -> GGUFConversionRequest:
    """Resolve a GGUF conversion request from registered adapter metadata."""

    settings = get_settings()
    resolved_registry_path = registry_path or settings.model_registry_path
    resolved_output_root = output_root or settings.model_artifact_root
    resolved_selection = _resolve_selection(selection, resolved_registry_path)
    registry = load_model_registry(resolved_registry_path)

    if candidate_id not in {resolved_selection.baseline_winner_id, resolved_selection.runner_up_id}:
        raise ValueError("GGUF conversion is limited to the pilot-selected baseline winner and runner-up")

    adapter_record = find_latest_artifact(
        registry,
        candidate_id=candidate_id,
        artifact_type="adapter",
    )
    if adapter_record is None:
        raise ValueError(f"No registered adapter artifact found for candidate_id={candidate_id}")

    profile_name = "gguf-laptop" if candidate_id == resolved_selection.baseline_winner_id else "gguf-runner-up"
    output_path = resolved_output_root / version_tag / candidate_id / f"{profile_name}.gguf"
    return GGUFConversionRequest(
        candidate_id=candidate_id,
        version_tag=version_tag,
        adapter_path=adapter_record.local_path,
        base_model_path=_resolve_base_model_path(candidate_id, resolved_output_root),
        output_path=output_path,
        quantization_profile=quantization_profile,
        profile_name=profile_name,
    )


def register_gguf_artifact(
    request: GGUFConversionRequest,
    *,
    registry_path: Path | None = None,
    selection: PilotSelection | None = None,
    artifact_source_path: Path | None = None,
    artifact_bytes: bytes | None = None,
) -> ModelArtifactRecord:
    """Register one GGUF artifact in the local model registry."""

    settings = get_settings()
    resolved_registry_path = registry_path or settings.model_registry_path
    resolved_selection = _resolve_selection(selection, resolved_registry_path)

    artifact_path = artifact_source_path or request.output_path
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    if artifact_source_path is None:
        payload = artifact_bytes or json.dumps(
            {
                "candidate_id": request.candidate_id,
                "version_tag": request.version_tag,
                "quantization_profile": request.quantization_profile,
                "profile_name": request.profile_name,
                "mode": "dry-run",
            },
            ensure_ascii=False,
            indent=2,
        ).encode("utf-8")
        artifact_path.write_bytes(payload)

    gguf_record = ModelArtifactRecord(
        candidate_id=request.candidate_id,
        artifact_type="gguf",
        version_tag=request.version_tag,
        local_path=artifact_path,
        sha256=build_model_checksum(artifact_path),
        profile_name=request.profile_name,
    )

    registry = load_model_registry(resolved_registry_path)
    registry.selection = resolved_selection
    registry.version_tag = request.version_tag
    registry.artifacts = [
        existing
        for existing in registry.artifacts
        if not (
            existing.candidate_id == gguf_record.candidate_id
            and existing.artifact_type == gguf_record.artifact_type
            and existing.version_tag == gguf_record.version_tag
        )
    ]
    registry.artifacts.append(gguf_record)
    save_model_registry(registry, resolved_registry_path)
    return gguf_record


def convert_to_gguf(
    request: GGUFConversionRequest,
    *,
    registry_path: Path | None = None,
    selection: PilotSelection | None = None,
    dry_run: bool = False,
    converter: Callable[[GGUFConversionRequest], Path | None] | None = None,
) -> dict[str, object]:
    """Validate or stage one GGUF conversion request locally."""

    if not request.adapter_path.exists():
        raise FileNotFoundError(f"Missing adapter artifact: {request.adapter_path}")
    if not dry_run:
        request.output_path.parent.mkdir(parents=True, exist_ok=True)
        converter_callable = converter or _run_default_converter
        artifact_path = converter_callable(request) or request.output_path
        artifact_path = Path(artifact_path)
        if not artifact_path.exists():
            raise FileNotFoundError(f"GGUF converter did not produce an artifact: {artifact_path}")
        artifact_record = register_gguf_artifact(
            request,
            registry_path=registry_path,
            selection=selection,
            artifact_source_path=artifact_path,
        )
        return {
            "dry_run": False,
            "candidate_id": request.candidate_id,
            "profile_name": request.profile_name,
            "artifact_record": artifact_record,
            "output_path": artifact_path,
        }

    artifact_record = register_gguf_artifact(
        request,
        registry_path=registry_path,
        selection=selection,
    )
    return {
        "dry_run": True,
        "candidate_id": request.candidate_id,
        "profile_name": request.profile_name,
        "artifact_record": artifact_record,
    }
