"""Phase 3 explicit runtime-profile selection tests."""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest
import src.runtime.analyzers.accelerated as accelerated_module
import src.runtime.analyzers.gguf as gguf_module

from src.model_adaptation.convert import build_gguf_request, convert_to_gguf
from src.model_adaptation.schemas import PilotSelection
from src.model_adaptation.training import build_training_config, save_adapter_artifacts


def _load_service_module():
    return importlib.import_module("src.runtime.service")


def _load_doctor_module():
    return importlib.import_module("src.runtime.doctor")


def _selection() -> PilotSelection:
    return PilotSelection(
        baseline_winner_id="qwen3-4b-instruct-2507",
        runner_up_id="qwen3.5-4b",
        selection_notes="Winner and runner-up selected in the pilot.",
    )


def _stage_gguf_registry(tmp_path: Path) -> Path:
    registry_path = tmp_path / "manifests" / "model-registry.json"
    (tmp_path / "models" / "base" / "qwen3-4b-instruct-2507").mkdir(parents=True, exist_ok=True)
    config = build_training_config(
        candidate_id="qwen3-4b-instruct-2507",
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
        "qwen3-4b-instruct-2507",
        "phase3-smoke",
        registry_path=registry_path,
        output_root=tmp_path / "models",
        selection=_selection(),
    )
    convert_to_gguf(request, registry_path=registry_path, selection=_selection(), dry_run=True)
    return registry_path


def _stage_accelerated_registry(tmp_path: Path) -> Path:
    registry_path = tmp_path / "manifests" / "model-registry-accelerated.json"
    (tmp_path / "models" / "base" / "qwen3.5-4b").mkdir(parents=True, exist_ok=True)
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
    settings = type(
        "FakeSettings",
        (),
        {
            "runtime_backend": "gguf",
            "runtime_profile": "gguf-laptop",
            "runtime_profile_gguf": "gguf-laptop",
            "runtime_profile_gguf_runner_up": "gguf-runner-up",
            "runtime_profile_accelerated": "accelerated-local",
            "model_registry_path": registry_path,
            "model_artifact_root": tmp_path / "models",
            "runtime_max_cues": 3,
            "runtime_min_text_chars": 8,
            "runtime_store_raw_text": False,
            "runtime_fail_closed": True,
            "runtime_text_only_message": (
                "Text-only v1: paste extracted text manually. Images/OCR and audio are not accepted in Phase 2."
            ),
        },
    )()

    monkeypatch.setattr(service_module, "get_settings", lambda: settings)
    monkeypatch.setattr(gguf_module, "get_settings", lambda: settings)
    monkeypatch.setattr(
        service_module.GGUFAnalyzer,
        "_load_runtime",
        lambda self, artifact_path: {"artifact_path": artifact_path},
    )
    monkeypatch.setattr(
        service_module.GGUFAnalyzer,
        "_infer_payload",
        lambda self, runtime, text: {
            "risk_tier": "high-risk",
            "suspicious_spans": ["https://vpbank-safe.example", "OTP"],
            "xai_explanation": "GGUF mocked response.",
        },
    )

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
    settings = type(
        "FakeSettings",
        (),
        {
            "runtime_backend": "gguf",
            "runtime_profile": "gguf-laptop",
            "runtime_profile_gguf": "gguf-laptop",
            "runtime_profile_gguf_runner_up": "gguf-runner-up",
            "runtime_profile_accelerated": "accelerated-local",
            "model_registry_path": registry_path,
            "model_artifact_root": tmp_path / "models",
            "runtime_max_cues": 3,
            "runtime_fail_closed": True,
            "runtime_store_raw_text": False,
        },
    )()

    monkeypatch.setattr(doctor_module, "get_settings", lambda: settings)
    monkeypatch.setattr(gguf_module, "get_settings", lambda: settings)
    monkeypatch.setattr(
        doctor_module.GGUFAnalyzer,
        "_load_runtime",
        lambda self, artifact_path: {"artifact_path": artifact_path},
    )

    status = doctor_module.run_runtime_doctor()
    report = doctor_module.format_doctor_report(status)

    assert status.ready is True
    assert status.backend_name == "gguf"
    assert "cloud" not in report.casefold()


def test_gguf_and_accelerated_profiles_share_phase_four_semantics(tmp_path, monkeypatch):
    service_module = _load_service_module()
    gguf_registry_path = _stage_gguf_registry(tmp_path)
    accelerated_registry_path = _stage_accelerated_registry(tmp_path)
    sample_text = (
        "VPBank cảnh báo tài khoản sẽ bị khóa trong 24h. Không chia sẻ OTP và không bấm "
        "https://vpbank-safe.example"
    )

    gguf_settings = type(
        "GGUFSettings",
        (),
        {
            "runtime_backend": "gguf",
            "runtime_profile": "gguf-laptop",
            "runtime_profile_gguf": "gguf-laptop",
            "runtime_profile_gguf_runner_up": "gguf-runner-up",
            "runtime_profile_accelerated": "accelerated-local",
            "model_registry_path": gguf_registry_path,
            "model_artifact_root": tmp_path / "models",
            "runtime_max_cues": 3,
            "runtime_min_text_chars": 8,
            "runtime_store_raw_text": False,
            "runtime_fail_closed": True,
            "runtime_text_only_message": (
                "Text-only v1: paste extracted text manually. Images/OCR and audio are not accepted in Phase 2."
            ),
        },
    )()
    accelerated_settings = type(
        "AcceleratedSettings",
        (),
        {
            "runtime_backend": "accelerated",
            "runtime_profile": "accelerated-local",
            "runtime_profile_gguf": "gguf-laptop",
            "runtime_profile_gguf_runner_up": "gguf-runner-up",
            "runtime_profile_accelerated": "accelerated-local",
            "model_registry_path": accelerated_registry_path,
            "model_artifact_root": tmp_path / "models",
            "runtime_max_cues": 3,
            "runtime_min_text_chars": 8,
            "runtime_store_raw_text": False,
            "runtime_fail_closed": True,
            "runtime_text_only_message": (
                "Text-only v1: paste extracted text manually. Images/OCR and audio are not accepted in Phase 2."
            ),
        },
    )()

    monkeypatch.setattr(
        service_module.GGUFAnalyzer,
        "_load_runtime",
        lambda self, artifact_path: {"artifact_path": artifact_path},
    )
    monkeypatch.setattr(
        service_module.GGUFAnalyzer,
        "_infer_payload",
        lambda self, runtime, text: {
            "risk_tier": "suspicious",
            "threat_labels": ["bank_impersonation"],
            "suspicious_spans": ["OTP"],
            "xai_explanation": "GGUF mocked response.",
            "recommendations": ["Khong bam vao lien ket trong tin nhan."],
        },
    )
    monkeypatch.setattr(
        service_module.AcceleratedAnalyzer,
        "_load_runtime",
        lambda self, *, adapter_path, base_model_path: {"adapter_path": adapter_path, "base_model_path": base_model_path},
    )
    monkeypatch.setattr(
        service_module.AcceleratedAnalyzer,
        "_infer_payload",
        lambda self, runtime, text: {
            "risk_tier": "suspicious",
            "threat_labels": ["bank_impersonation"],
            "suspicious_spans": ["OTP"],
            "xai_explanation": "Accelerated mocked response.",
            "recommendations": ["Khong bam vao lien ket trong tin nhan."],
        },
    )

    monkeypatch.setattr(service_module, "get_settings", lambda: gguf_settings)
    monkeypatch.setattr(gguf_module, "get_settings", lambda: gguf_settings)
    gguf_result = service_module.build_default_runtime_service().analyze_text(sample_text, channel="sms")

    monkeypatch.setattr(service_module, "get_settings", lambda: accelerated_settings)
    monkeypatch.setattr(accelerated_module, "get_settings", lambda: accelerated_settings)
    accelerated_result = service_module.build_default_runtime_service().analyze_text(sample_text, channel="sms")

    assert set(gguf_result.model_dump().keys()) == set(accelerated_result.model_dump().keys())
    assert gguf_result.risk_tier == accelerated_result.risk_tier == "suspicious"
    assert gguf_result.threat_labels == ["bank_impersonation"]
    assert accelerated_result.threat_labels == ["bank_impersonation"]
    assert gguf_result.recommendations == ["Khong bam vao lien ket trong tin nhan."]
    assert accelerated_result.recommendations == ["Khong bam vao lien ket trong tin nhan."]
    assert gguf_result.backend_name == "gguf"
    assert accelerated_result.backend_name == "accelerated"


def test_accelerated_profile_stays_explicit_when_model_loader_is_mocked(tmp_path, monkeypatch):
    service_module = _load_service_module()
    accelerated_registry_path = _stage_accelerated_registry(tmp_path)
    settings = type(
        "AcceleratedSettings",
        (),
        {
            "runtime_backend": "accelerated",
            "runtime_profile": "accelerated-local",
            "runtime_profile_gguf": "gguf-laptop",
            "runtime_profile_gguf_runner_up": "gguf-runner-up",
            "runtime_profile_accelerated": "accelerated-local",
            "model_registry_path": accelerated_registry_path,
            "model_artifact_root": tmp_path / "models",
            "runtime_max_cues": 3,
            "runtime_min_text_chars": 8,
            "runtime_store_raw_text": False,
            "runtime_fail_closed": True,
            "runtime_text_only_message": (
                "Text-only v1: paste extracted text manually. Images/OCR and audio are not accepted in Phase 2."
            ),
        },
    )()

    monkeypatch.setattr(service_module, "get_settings", lambda: settings)
    monkeypatch.setattr(accelerated_module, "get_settings", lambda: settings)
    monkeypatch.setattr(
        service_module.AcceleratedAnalyzer,
        "_load_runtime",
        lambda self, *, adapter_path, base_model_path: {"adapter_path": adapter_path, "base_model_path": base_model_path},
    )
    monkeypatch.setattr(
        service_module.AcceleratedAnalyzer,
        "_infer_payload",
        lambda self, runtime, text: {
            "risk_tier": "high-risk",
            "suspicious_spans": ["http://verify-vcb.example/", "OTP"],
            "xai_explanation": "Accelerated mocked response.",
        },
    )

    service = service_module.build_default_runtime_service()
    result = service.analyze_text(
        "Vietcombank canh bao tai khoan cua ban dang bi tam khoa. Vui long nhap OTP tai http://verify-vcb.example/ de xac minh.",
        channel="sms",
    )

    assert service.backend.backend_name == "accelerated"
    assert result.backend_name == "accelerated"
    assert result.risk_tier == "high-risk"