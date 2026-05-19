"""Phase 3 accelerated-backend expectations."""

from __future__ import annotations

from pathlib import Path

import src.runtime.analyzers.accelerated as accelerated_module
from src.model_adaptation.schemas import PilotSelection
from src.model_adaptation.training import build_training_config, save_adapter_artifacts
from src.runtime.contracts import AnalysisRequest, AnalysisResult


def _selection() -> PilotSelection:
    return PilotSelection(
        baseline_winner_id="qwen3-4b-instruct-2507",
        runner_up_id="qwen3.5-4b",
        selection_notes="Winner and runner-up selected in the pilot.",
    )


def _stage_accelerated_registry(tmp_path: Path) -> Path:
    registry_path = tmp_path / "manifests" / "model-registry.json"
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


def test_accelerated_analyze_returns_phase_four_result_fields(tmp_path, monkeypatch):
    registry_path = _stage_accelerated_registry(tmp_path)
    settings = type(
        "FakeSettings",
        (),
        {
            "runtime_profile_accelerated": "accelerated-local",
            "runtime_profile": "accelerated-local",
            "model_registry_path": registry_path,
            "model_artifact_root": tmp_path / "models",
        },
    )()
    captured: dict[str, object] = {}

    def fake_load_runtime(self, *, adapter_path, base_model_path):
        captured["adapter_path"] = adapter_path
        captured["base_model_path"] = base_model_path
        return {"adapter_path": adapter_path, "base_model_path": base_model_path}

    def fake_infer_payload(self, runtime, text):
        captured["text"] = text
        return {
            "risk_tier": "benign",
            "suspicious_spans": ["xác minh"],
            "xai_explanation": "Model output judged this message benign despite the old heuristic keywords.",
        }

    monkeypatch.setattr(accelerated_module, "get_settings", lambda: settings)
    monkeypatch.setattr(accelerated_module.AcceleratedAnalyzer, "_load_runtime", fake_load_runtime)
    monkeypatch.setattr(accelerated_module.AcceleratedAnalyzer, "_infer_payload", fake_infer_payload)

    backend = accelerated_module.AcceleratedAnalyzer(
        registry_path=registry_path,
        runtime_profile="accelerated-local",
    )
    status = backend.doctor()
    result = backend.analyze(
        AnalysisRequest(
            text=(
                "Techcombank cảnh báo tài khoản sẽ bị khóa trong 24h. Không chia sẻ OTP và không bấm "
                "https://techcombank-safe.example để xác minh."
            ),
            channel="sms",
        )
    )

    assert status.ready is True
    assert isinstance(result, AnalysisResult)
    assert result.backend_name == "accelerated"
    assert result.risk_tier == "high-risk"
    assert result.threat_labels == ["bank_impersonation"]
    assert result.recommendations
    assert Path(captured["adapter_path"]).name == "adapter-placeholder.bin"
    assert len(result.top_cues) <= 3


def test_accelerated_doctor_fails_when_runner_up_resources_cannot_load(tmp_path, monkeypatch):
    registry_path = _stage_accelerated_registry(tmp_path)
    settings = type(
        "FakeSettings",
        (),
        {
            "runtime_profile_accelerated": "accelerated-local",
            "runtime_profile": "accelerated-local",
            "model_registry_path": registry_path,
            "model_artifact_root": tmp_path / "models",
        },
    )()

    def fake_load_runtime(self, *, adapter_path, base_model_path):
        raise RuntimeError("runner-up loader failed")

    monkeypatch.setattr(accelerated_module, "get_settings", lambda: settings)
    monkeypatch.setattr(accelerated_module.AcceleratedAnalyzer, "_load_runtime", fake_load_runtime)

    status = accelerated_module.AcceleratedAnalyzer(
        registry_path=registry_path,
        runtime_profile="accelerated-local",
    ).doctor()

    assert status.ready is False
    assert any(
        check.name == "accelerated-runtime-load" and check.passed is False
        for check in status.checks
    )