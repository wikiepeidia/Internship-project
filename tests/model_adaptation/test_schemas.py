"""Wave 0 schema tests for the Phase 3 model-adaptation foundation."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from src.config.settings import Settings
from src.model_adaptation.catalog import build_default_catalog, get_candidate_by_id
from src.model_adaptation.schemas import ModelArtifactRecord, ModelCandidate, PilotSelection


def test_catalog_contains_locked_qwen_candidates():
    catalog = build_default_catalog()

    assert [candidate.candidate_id for candidate in catalog] == [
        "qwen3.5-4b",
        "qwen3-4b-instruct-2507",
        "qwen2.5-7b-instruct",
    ]
    assert [candidate.hf_source for candidate in catalog] == [
        "Qwen/Qwen3.5-4B",
        "Qwen/Qwen3-4B-Instruct-2507",
        "Qwen/Qwen2.5-7B-Instruct",
    ]
    assert [candidate.role for candidate in catalog] == ["primary", "fallback", "fallback"]
    assert [candidate.size_label for candidate in catalog] == ["4B", "4B", "7B"]
    assert get_candidate_by_id("qwen3.5-4b").hf_source == "Qwen/Qwen3.5-4B"


def test_model_candidate_rejects_blank_identifiers():
    with pytest.raises(ValidationError):
        ModelCandidate(
            candidate_id="qwen3.5-4b",
            hf_source="   ",
            family="Qwen",
            role="primary",
            size_label="4B",
            notes="Laptop baseline.",
        )


def test_pilot_selection_requires_4b_baseline_winner():
    with pytest.raises(ValidationError):
        PilotSelection(
            baseline_winner_id="qwen2.5-7b-instruct",
            runner_up_id="qwen3.5-4b",
        )


def test_model_artifact_record_defaults_to_local_only():
    record = ModelArtifactRecord(
        candidate_id="qwen3.5-4b",
        artifact_type="adapter",
        version_tag="phase3-smoke",
        local_path=Path("data/models/qwen3.5-4b/adapter.bin"),
        sha256="a" * 64,
    )

    assert record.local_only is True
    assert record.tracked_in_git is False


def test_model_artifact_record_rejects_blank_path():
    with pytest.raises(ValidationError):
        ModelArtifactRecord(
            candidate_id="qwen3.5-4b",
            artifact_type="gguf",
            version_tag="phase3-smoke",
            local_path="   ",
            sha256="b" * 64,
        )


def test_settings_expose_phase3_model_defaults_without_changing_runtime_defaults():
    settings = Settings()

    assert settings.runtime_backend == "heuristic"
    assert settings.runtime_profile == "heuristic"
    assert settings.runtime_profile_gguf == "gguf-laptop"
    assert settings.runtime_profile_accelerated == "accelerated-local"
    assert settings.model_artifact_root == Path("data/models")
    assert settings.model_registry_path == Path("data/manifests/model-registry.json")