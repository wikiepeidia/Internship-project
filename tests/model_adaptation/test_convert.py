"""Wave 0 GGUF conversion tests for Phase 3 artifact staging."""

from __future__ import annotations

from pathlib import Path

from src.model_adaptation.convert import build_gguf_request, convert_to_gguf
from src.model_adaptation.registry import load_model_registry
from src.model_adaptation.schemas import PilotSelection
from src.model_adaptation.training import build_training_config, save_adapter_artifacts


def _selection() -> PilotSelection:
    return PilotSelection(
        baseline_winner_id="qwen3.5-4b",
        runner_up_id="qwen2.5-7b-instruct",
        selection_notes="Winner and runner-up selected in the pilot.",
    )


def _stage_adapter(tmp_path: Path, candidate_id: str) -> Path:
    registry_path = tmp_path / "manifests" / "model-registry.json"
    config = build_training_config(
        candidate_id=candidate_id,
        train_split_path=tmp_path / "splits" / "train.jsonl",
        val_split_path=tmp_path / "splits" / "val.jsonl",
        version_tag="phase3-smoke",
        output_root=tmp_path / "models",
        registry_path=registry_path,
        selection=_selection(),
        dry_run=True,
    )
    save_adapter_artifacts(config, selection=_selection())
    return registry_path


def test_build_gguf_request_uses_adapter_artifact(tmp_path):
    registry_path = _stage_adapter(tmp_path, "qwen3.5-4b")

    request = build_gguf_request(
        "qwen3.5-4b",
        "phase3-smoke",
        registry_path=registry_path,
        output_root=tmp_path / "models",
        selection=_selection(),
    )

    assert request.candidate_id == "qwen3.5-4b"
    assert request.adapter_path.exists()
    assert request.output_path.name == "gguf-laptop.gguf"
    assert request.quantization_profile == "q4_k_m"


def test_convert_to_gguf_dry_run_registers_metadata_for_baseline_winner_and_runner_up(tmp_path):
    registry_path = _stage_adapter(tmp_path, "qwen3.5-4b")
    _stage_adapter(tmp_path, "qwen2.5-7b-instruct")

    baseline_request = build_gguf_request(
        "qwen3.5-4b",
        "phase3-smoke",
        registry_path=registry_path,
        output_root=tmp_path / "models",
        selection=_selection(),
    )
    runner_up_request = build_gguf_request(
        "qwen2.5-7b-instruct",
        "phase3-smoke",
        registry_path=registry_path,
        output_root=tmp_path / "models",
        selection=_selection(),
    )

    baseline_result = convert_to_gguf(
        baseline_request,
        registry_path=registry_path,
        selection=_selection(),
        dry_run=True,
    )
    runner_up_result = convert_to_gguf(
        runner_up_request,
        registry_path=registry_path,
        selection=_selection(),
        dry_run=True,
    )
    loaded_registry = load_model_registry(registry_path)
    gguf_artifacts = [artifact for artifact in loaded_registry.artifacts if artifact.artifact_type == "gguf"]

    assert baseline_result["dry_run"] is True
    assert runner_up_result["dry_run"] is True
    assert {artifact.candidate_id for artifact in gguf_artifacts} == {
        "qwen3.5-4b",
        "qwen2.5-7b-instruct",
    }
    assert {artifact.profile_name for artifact in gguf_artifacts} == {"gguf-laptop", "gguf-runner-up"}