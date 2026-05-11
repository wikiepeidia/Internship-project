"""Phase 3 explicit runtime-profile selection tests."""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

from src.model_adaptation.convert import build_gguf_request, convert_to_gguf
from src.model_adaptation.schemas import PilotSelection
from src.model_adaptation.training import build_training_config, save_adapter_artifacts


def _load_service_module():
    return importlib.import_module("src.runtime.service")


def _load_doctor_module():
    return importlib.import_module("src.runtime.doctor")


def _selection() -> PilotSelection:
    return PilotSelection(
        baseline_winner_id="qwen3.5-4b",
        runner_up_id="qwen2.5-7b-instruct",
        selection_notes="Winner and runner-up selected in the pilot.",
    )


def _stage_gguf_registry(tmp_path: Path) -> Path:
    registry_path = tmp_path / "manifests" / "model-registry.json"
    config = build_training_config(
        candidate_id="qwen3.5-4b",
        train_split_path=tmp_path / "splits" / "train.jsonl",
        val_split_path=tmp_path / "splits" / "val.jsonl",
        version_tag="phase3-smoke",
        output_root=tmp_path / "models",
        registry_path=registry_path,
        selection=_selection(),
        dry_run=True,
    )
    save_adapter_artifacts(config, selection=_selection())
    request = build_gguf_request(
        "qwen3.5-4b",
        "phase3-smoke",
        registry_path=registry_path,
        output_root=tmp_path / "models",
        selection=_selection(),
    )
    convert_to_gguf(request, registry_path=registry_path, selection=_selection(), dry_run=True)
    return registry_path


def _stage_accelerated_registry(tmp_path: Path) -> Path:
    registry_path = tmp_path / "manifests" / "model-registry-accelerated.json"
    config = build_training_config(
        candidate_id="qwen2.5-7b-instruct",
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


def test_runtime_service_rejects_unknown_runtime_profile(tmp_path, monkeypatch):
    service_module = _load_service_module()

    class FakeSettings:
        runtime_backend = "gguf"
        runtime_profile = "unknown-profile"
        runtime_profile_gguf = "gguf-laptop"
        runtime_profile_gguf_runner_up = "gguf-runner-up"
        model_registry_path = tmp_path / "manifests" / "model-registry.json"
        runtime_max_cues = 3
        runtime_min_text_chars = 8
        runtime_store_raw_text = False
        runtime_fail_closed = True
        runtime_text_only_message = (
            "Text-only v1: paste extracted text manually. Images/OCR and audio are not accepted in Phase 2."
        )

    monkeypatch.setattr(service_module, "get_settings", lambda: FakeSettings())

    with pytest.raises(ValueError):
        service_module.build_default_runtime_service()


def test_build_default_runtime_service_uses_explicit_gguf_profile(tmp_path, monkeypatch):
    service_module = _load_service_module()
    registry_path = _stage_gguf_registry(tmp_path)

    class FakeSettings:
        runtime_backend = "gguf"
        runtime_profile = "gguf-laptop"
        runtime_profile_gguf = "gguf-laptop"
        runtime_profile_gguf_runner_up = "gguf-runner-up"
        model_registry_path = registry_path
        runtime_max_cues = 3
        runtime_min_text_chars = 8
        runtime_store_raw_text = False
        runtime_fail_closed = True
        runtime_text_only_message = (
            "Text-only v1: paste extracted text manually. Images/OCR and audio are not accepted in Phase 2."
        )

    monkeypatch.setattr(service_module, "get_settings", lambda: FakeSettings())

    service = service_module.build_default_runtime_service()
    result = service.analyze_text(
        "VPBank cảnh báo tài khoản sẽ bị khóa trong 24h. Không chia sẻ OTP và không bấm https://vpbank-safe.example",
        channel="sms",
    )

    assert service.backend.backend_name == "gguf"
    assert result.backend_name == "gguf"
    assert result.risk_tier == "high-risk"


def test_runtime_doctor_reports_gguf_readiness_without_cloud_fallback(tmp_path, monkeypatch):
    doctor_module = _load_doctor_module()
    registry_path = _stage_gguf_registry(tmp_path)

    class FakeSettings:
        runtime_backend = "gguf"
        runtime_profile = "gguf-laptop"
        runtime_profile_gguf = "gguf-laptop"
        runtime_profile_gguf_runner_up = "gguf-runner-up"
        model_registry_path = registry_path
        runtime_max_cues = 3
        runtime_fail_closed = True
        runtime_store_raw_text = False

    monkeypatch.setattr(doctor_module, "get_settings", lambda: FakeSettings())

    status = doctor_module.run_runtime_doctor()
    report = doctor_module.format_doctor_report(status)

    assert status.ready is True
    assert status.backend_name == "gguf"
    assert "cloud" not in report.casefold()


def test_gguf_and_accelerated_profiles_share_contract_shape(tmp_path, monkeypatch):
    service_module = _load_service_module()
    gguf_registry_path = _stage_gguf_registry(tmp_path)
    accelerated_registry_path = _stage_accelerated_registry(tmp_path)
    sample_text = (
        "VPBank cảnh báo tài khoản sẽ bị khóa trong 24h. Không chia sẻ OTP và không bấm "
        "https://vpbank-safe.example"
    )

    class GGUFSettings:
        runtime_backend = "gguf"
        runtime_profile = "gguf-laptop"
        runtime_profile_gguf = "gguf-laptop"
        runtime_profile_gguf_runner_up = "gguf-runner-up"
        runtime_profile_accelerated = "accelerated-local"
        model_registry_path = gguf_registry_path
        runtime_max_cues = 3
        runtime_min_text_chars = 8
        runtime_store_raw_text = False
        runtime_fail_closed = True
        runtime_text_only_message = (
            "Text-only v1: paste extracted text manually. Images/OCR and audio are not accepted in Phase 2."
        )

    class AcceleratedSettings:
        runtime_backend = "accelerated"
        runtime_profile = "accelerated-local"
        runtime_profile_gguf = "gguf-laptop"
        runtime_profile_gguf_runner_up = "gguf-runner-up"
        runtime_profile_accelerated = "accelerated-local"
        model_registry_path = accelerated_registry_path
        runtime_max_cues = 3
        runtime_min_text_chars = 8
        runtime_store_raw_text = False
        runtime_fail_closed = True
        runtime_text_only_message = (
            "Text-only v1: paste extracted text manually. Images/OCR and audio are not accepted in Phase 2."
        )

    monkeypatch.setattr(service_module, "get_settings", lambda: GGUFSettings())
    gguf_result = service_module.build_default_runtime_service().analyze_text(sample_text, channel="sms")

    monkeypatch.setattr(service_module, "get_settings", lambda: AcceleratedSettings())
    accelerated_result = service_module.build_default_runtime_service().analyze_text(sample_text, channel="sms")

    assert set(gguf_result.model_dump().keys()) == set(accelerated_result.model_dump().keys())
    assert gguf_result.backend_name == "gguf"
    assert accelerated_result.backend_name == "accelerated"