"""GGUF conversion helpers for Phase 3 local deployment artifacts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from src.config.settings import get_settings
from src.model_adaptation.registry import build_model_checksum, load_model_registry, save_model_registry
from src.model_adaptation.schemas import ModelArtifactRecord, ModelRegistry, PilotSelection


@dataclass(frozen=True)
class GGUFConversionRequest:
    """Resolved request for converting one registered adapter into a GGUF artifact."""

    candidate_id: str
    version_tag: str
    adapter_path: Path
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

    adapter_record = next(
        (
            artifact
            for artifact in registry.artifacts
            if artifact.candidate_id == candidate_id and artifact.artifact_type == "adapter"
        ),
        None,
    )
    if adapter_record is None:
        raise ValueError(f"No registered adapter artifact found for candidate_id={candidate_id}")

    profile_name = "gguf-laptop" if candidate_id == resolved_selection.baseline_winner_id else "gguf-runner-up"
    output_path = resolved_output_root / version_tag / candidate_id / f"{profile_name}.gguf"
    return GGUFConversionRequest(
        candidate_id=candidate_id,
        version_tag=version_tag,
        adapter_path=adapter_record.local_path,
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
) -> dict[str, object]:
    """Validate or stage one GGUF conversion request locally."""

    if not request.adapter_path.exists():
        raise FileNotFoundError(f"Missing adapter artifact: {request.adapter_path}")
    if not dry_run:
        raise RuntimeError("Real GGUF conversion is not wired in yet; use dry_run=True")

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