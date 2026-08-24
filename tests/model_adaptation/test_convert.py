"""GGUF conversion tests for Phase 3 artifact staging and real-conversion dispatch."""

from __future__ import annotations

from pathlib import Path

from src.model_adaptation.convert import build_gguf_request, convert_to_gguf
from src.model_adaptation.phase40_modes import AdaptationMode
from src.model_adaptation.registry import load_model_registry
from src.model_adaptation.schemas import PilotSelection
from src.model_adaptation.training import build_training_config, save_adapter_artifacts


def _selection() -> PilotSelection:
    return PilotSelection(
        baseline_winner_id="qwen3-4b-instruct-2507",
        runner_up_id="qwen3.5-4b",
        selection_notes="Winner and runner-up selected in the pilot.",
    )


def _stage_adapter(tmp_path: Path, candidate_id: str, *, version_tag: str = "phase3-smoke") -> Path:
    registry_path = tmp_path / "manifests" / "model-registry.json"
    base_model_dir = tmp_path / "models" / "base" / candidate_id
    base_model_dir.mkdir(parents=True, exist_ok=True)
    config = build_training_config(
        candidate_id=candidate_id,
        train_split_path=tmp_path / "splits" / "train.jsonl",
        val_split_path=tmp_path / "splits" / "val.jsonl",
        version_tag=version_tag,
        output_root=tmp_path / "models",
        registry_path=registry_path,
        selection=_selection(),
        adaptation_mode=AdaptationMode.LORA,
        dry_run=True,
    )
    save_adapter_artifacts(config, selection=_selection())
    return registry_path


def test_build_gguf_request_uses_adapter_artifact(tmp_path):
    registry_path = _stage_adapter(tmp_path, "qwen3-4b-instruct-2507")
    _stage_adapter(tmp_path, "qwen3.5-4b")

    request = build_gguf_request(
        "qwen3-4b-instruct-2507",
        "phase3-smoke",
        registry_path=registry_path,
        output_root=tmp_path / "models",
        selection=_selection(),
    )

    assert request.candidate_id == "qwen3-4b-instruct-2507"
    assert request.adapter_path.exists()
    assert request.base_model_path.exists()
    assert request.output_path.name == "gguf-laptop.gguf"
    assert request.quantization_profile == "q4_k_m"


def test_build_gguf_request_uses_latest_adapter_artifact(tmp_path):
    registry_path = _stage_adapter(tmp_path, "qwen3-4b-instruct-2507", version_tag="phase3-old")
    _stage_adapter(tmp_path, "qwen3-4b-instruct-2507", version_tag="phase3-new")

    request = build_gguf_request(
        "qwen3-4b-instruct-2507",
        "phase3-gguf-new",
        registry_path=registry_path,
        output_root=tmp_path / "models",
        selection=_selection(),
    )

    assert request.adapter_path == tmp_path / "models" / "phase3-new" / "qwen3-4b-instruct-2507" / "adapter-placeholder.bin"


def test_convert_to_gguf_dry_run_registers_metadata_for_baseline_winner_and_runner_up(tmp_path):
    registry_path = _stage_adapter(tmp_path, "qwen3-4b-instruct-2507")
    _stage_adapter(tmp_path, "qwen3.5-4b")

    baseline_request = build_gguf_request(
        "qwen3-4b-instruct-2507",
        "phase3-smoke",
        registry_path=registry_path,
        output_root=tmp_path / "models",
        selection=_selection(),
    )
    runner_up_request = build_gguf_request(
        "qwen3.5-4b",
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
        "qwen3-4b-instruct-2507",
        "qwen3.5-4b",
    }
    assert {artifact.profile_name for artifact in gguf_artifacts} == {"gguf-laptop", "gguf-runner-up"}


def test_convert_to_gguf_invokes_real_converter_without_runtime_error(tmp_path):
    registry_path = _stage_adapter(tmp_path, "qwen3-4b-instruct-2507")
    request = build_gguf_request(
        "qwen3-4b-instruct-2507",
        "phase3-main",
        registry_path=registry_path,
        output_root=tmp_path / "models",
        selection=_selection(),
    )
    captured_candidates: list[str] = []

    def fake_converter(conversion_request):
        captured_candidates.append(conversion_request.candidate_id)
        conversion_request.output_path.write_bytes(b"gguf-bytes")
        return conversion_request.output_path

    result = convert_to_gguf(
        request,
        registry_path=registry_path,
        selection=_selection(),
        dry_run=False,
        converter=fake_converter,
    )
    loaded_registry = load_model_registry(registry_path)
    gguf_artifacts = [artifact for artifact in loaded_registry.artifacts if artifact.artifact_type == "gguf"]

    assert result["dry_run"] is False
    assert captured_candidates == ["qwen3-4b-instruct-2507"]
    assert gguf_artifacts[-1].candidate_id == "qwen3-4b-instruct-2507"
    assert gguf_artifacts[-1].local_path == request.output_path


def test_convert_to_gguf_registers_after_real_output_exists(tmp_path):
    registry_path = _stage_adapter(tmp_path, "qwen3-4b-instruct-2507")
    request = build_gguf_request(
        "qwen3-4b-instruct-2507",
        "phase3-main",
        registry_path=registry_path,
        output_root=tmp_path / "models",
        selection=_selection(),
    )

    def fake_converter(conversion_request):
        loaded_before = load_model_registry(registry_path)
        assert not [artifact for artifact in loaded_before.artifacts if artifact.artifact_type == "gguf"]
        conversion_request.output_path.write_bytes(b"gguf-bytes")
        return conversion_request.output_path

    convert_to_gguf(
        request,
        registry_path=registry_path,
        selection=_selection(),
        dry_run=False,
        converter=fake_converter,
    )
    loaded_registry = load_model_registry(registry_path)
    gguf_artifacts = [artifact for artifact in loaded_registry.artifacts if artifact.artifact_type == "gguf"]

    assert len(gguf_artifacts) == 1
    assert gguf_artifacts[0].local_path.exists()
