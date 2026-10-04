"""Wave 0 registry tests for Phase 3 model metadata persistence."""

from pathlib import Path

import pytest

from src.model_adaptation.registry import build_model_checksum, load_model_registry, save_model_registry
from src.model_adaptation.schemas import ModelArtifactRecord, ModelRegistry, PilotScorecard, PilotSelection


def test_save_and_load_model_registry_round_trip(tmp_path):
    artifact_path = tmp_path / "artifacts" / "qwen3.5-4b.adapter"
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text("adapter-bytes", encoding="utf-8")

    registry = ModelRegistry(
        version_tag="phase3-smoke",
        selection=PilotSelection(
            baseline_winner_id="qwen3.5-4b",
            runner_up_id="qwen2.5-7b-instruct",
            selection_notes="4B wins the laptop baseline; 7B stays as runner-up.",
        ),
        scorecards=[
            PilotScorecard(
                candidate_id="qwen3.5-4b",
                hf_source="Qwen/Qwen3.5-4B",
                evaluated_split="val",
                quality_score=0.89,
                recall_score=0.91,
                latency_score=0.82,
                memory_fit_score=0.95,
                profile_notes="Fits the 8GB VRAM baseline cleanly.",
                local_output_path=tmp_path / "scorecards" / "pilot.json",
            )
        ],
        artifacts=[
            ModelArtifactRecord(
                candidate_id="qwen3.5-4b",
                artifact_type="adapter",
                version_tag="phase3-smoke",
                local_path=artifact_path,
                sha256=build_model_checksum(artifact_path),
            )
        ],
    )

    saved_path = save_model_registry(registry, tmp_path / "manifests" / "model-registry.json")
    loaded = load_model_registry(saved_path)

    assert saved_path.exists()
    assert loaded.version_tag == "phase3-smoke"
    assert loaded.selection is not None
    assert loaded.selection.baseline_winner_id == "qwen3.5-4b"
    assert loaded.selection.runner_up_id == "qwen2.5-7b-instruct"
    assert loaded.artifacts[0].local_only is True
    assert loaded.artifacts[0].tracked_in_git is False
    assert loaded.artifacts[0].sha256 == build_model_checksum(artifact_path)


def test_build_model_checksum_rejects_missing_file(tmp_path):
    missing_path = tmp_path / "missing.gguf"

    with pytest.raises(FileNotFoundError):
        build_model_checksum(missing_path)


def test_build_model_checksum_is_stable(tmp_path):
    artifact_path = tmp_path / "adapter.bin"
    artifact_path.write_text("adapter-bytes", encoding="utf-8")

    first_checksum = build_model_checksum(artifact_path)
    second_checksum = build_model_checksum(artifact_path)

    assert first_checksum == second_checksum
    assert len(first_checksum) == 64


def test_registry_metadata_keeps_artifact_paths_local_only(tmp_path):
    artifact_path = tmp_path / "local" / "runner-up.gguf"
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text("gguf-bytes", encoding="utf-8")

    registry = ModelRegistry(
        version_tag="phase3-registry",
        artifacts=[
            ModelArtifactRecord(
                candidate_id="qwen2.5-7b-instruct",
                artifact_type="gguf",
                version_tag="phase3-registry",
                local_path=artifact_path,
                sha256=build_model_checksum(artifact_path),
                local_only=True,
            )
        ],
    )

    saved_path = save_model_registry(registry, tmp_path / "model-registry.json")
    loaded = load_model_registry(saved_path)

    assert loaded.artifacts[0].local_path == Path(artifact_path)
    assert loaded.artifacts[0].local_only is True
    assert loaded.artifacts[0].tracked_in_git is False