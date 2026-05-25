"""Phase 3 GGUF backend expectations."""

from __future__ import annotations

import json
from pathlib import Path

import src.runtime.analyzers.gguf as gguf_module
from src.model_adaptation.convert import build_gguf_request, convert_to_gguf
from src.model_adaptation.schemas import PilotSelection
from src.model_adaptation.training import build_training_config, save_adapter_artifacts
from src.runtime.contracts import AnalysisRequest, AnalysisResult


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


def test_gguf_analyze_returns_phase_four_result_fields(tmp_path, monkeypatch):
    registry_path = _stage_gguf_registry(tmp_path)
    settings = type(
        "FakeSettings",
        (),
        {
            "runtime_profile": "gguf-laptop",
            "runtime_profile_gguf": "gguf-laptop",
            "runtime_profile_gguf_runner_up": "gguf-runner-up",
            "model_registry_path": registry_path,
            "model_artifact_root": tmp_path / "models",
        },
    )()
    captured: dict[str, object] = {}

    def fake_load_runtime(self, artifact_path):
        captured["artifact_path"] = artifact_path
        return {"artifact_path": artifact_path}

    def fake_infer_payload(self, runtime, text):
        captured["text"] = text
        return {
            "risk_tier": "high-risk",
            "suspicious_spans": ["https://vpbank-safe.example", "OTP"],
            "xai_explanation": "Model-backed GGUF explanation.",
        }

    monkeypatch.setattr(gguf_module, "get_settings", lambda: settings)
    monkeypatch.setattr(gguf_module.GGUFAnalyzer, "_load_runtime", fake_load_runtime)
    monkeypatch.setattr(gguf_module.GGUFAnalyzer, "_infer_payload", fake_infer_payload)

    backend = gguf_module.GGUFAnalyzer(registry_path=registry_path, runtime_profile="gguf-laptop")
    status = backend.doctor()
    result = backend.analyze(
        AnalysisRequest(
            text=(
                "VPBank cảnh báo account Internet Banking của bạn sẽ bị khóa trong 24h. "
                "Không chia sẻ mã OTP và không bấm vào https://vpbank-safe.example"
            ),
            channel="sms",
        )
    )

    assert status.ready is True
    assert isinstance(result, AnalysisResult)
    assert result.backend_name == "gguf"
    assert result.risk_tier == "high-risk"
    assert result.threat_labels == ["bank_impersonation"]
    assert result.recommendations
    assert Path(captured["artifact_path"]).name == "gguf-laptop.gguf"
    assert len(result.top_cues) <= 3


def test_gguf_load_runtime_uses_larger_context_window(tmp_path, monkeypatch):
    registry_path = _stage_gguf_registry(tmp_path)
    captured: dict[str, object] = {}

    class FakeLlama:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    fake_module = type("FakeLlamaModule", (), {"Llama": FakeLlama})
    monkeypatch.setattr(gguf_module.importlib, "import_module", lambda name: fake_module)

    backend = gguf_module.GGUFAnalyzer(registry_path=registry_path, runtime_profile="gguf-laptop")
    artifact_path = backend._resolve_artifact_path()
    backend._load_runtime(artifact_path)

    assert captured["model_path"] == str(artifact_path)
    assert captured["n_ctx"] == gguf_module.GGUF_CONTEXT_WINDOW
    assert captured["n_gpu_layers"] == 0
    assert captured["verbose"] is False


def test_gguf_infer_payload_prefers_chat_completion_json_mode(tmp_path):
    registry_path = _stage_gguf_registry(tmp_path)
    captured: dict[str, object] = {}

    class FakeRuntime:
        def create_chat_completion(self, **kwargs):
            captured.update(kwargs)
            return {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "risk_tier": "high-risk",
                                    "threat_labels": ["bank_impersonation"],
                                    "decision_summary": "Tin nhan gia danh ngan hang va yeu cau OTP.",
                                    "evidence": [
                                        {
                                            "span": "OTP",
                                            "reason": "Yeu cau ma OTP nhay cam.",
                                            "cue_type": "otp_request",
                                            "supports_labels": ["bank_impersonation"],
                                            "severity": "high",
                                        }
                                    ],
                                    "recommendations": [
                                        {
                                            "text": "Khong chia se OTP cho bat ky ai.",
                                            "priority": "high",
                                            "offline_safe": True,
                                        }
                                    ],
                                },
                                ensure_ascii=False,
                            )
                        }
                    }
                ]
            }

    backend = gguf_module.GGUFAnalyzer(registry_path=registry_path, runtime_profile="gguf-laptop")
    payload = backend._infer_payload(
        FakeRuntime(),
        "VPBank can OTP de xac minh giao dich ngay.",
    )

    assert payload["risk_tier"] == "high-risk"
    assert captured["messages"][0]["role"] == "user"
    assert "VPBank can OTP de xac minh giao dich ngay." in captured["messages"][0]["content"]
    assert captured["max_tokens"] == gguf_module.GGUF_COMPLETION_MAX_TOKENS
    assert captured["temperature"] == 0.0
    assert captured["response_format"] == {"type": "json_object"}


def test_gguf_resolves_latest_registered_artifact(tmp_path):
    registry_path = _stage_gguf_registry(tmp_path)
    request = build_gguf_request(
        "qwen3-4b-instruct-2507",
        "phase3-main",
        registry_path=registry_path,
        output_root=tmp_path / "models",
        selection=_selection(),
    )
    convert_to_gguf(
        request,
        registry_path=registry_path,
        selection=_selection(),
        dry_run=True,
    )

    backend = gguf_module.GGUFAnalyzer(registry_path=registry_path, runtime_profile="gguf-laptop")

    assert backend._resolve_artifact_path() == request.output_path