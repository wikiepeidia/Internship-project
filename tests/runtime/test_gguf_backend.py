"""Phase 3 GGUF backend expectations."""

from __future__ import annotations

from pathlib import Path

from src.model_adaptation.convert import build_gguf_request, convert_to_gguf
from src.model_adaptation.schemas import PilotSelection
from src.model_adaptation.training import build_training_config, save_adapter_artifacts
from src.runtime.analyzers.gguf import GGUFAnalyzer
from src.runtime.contracts import AnalysisRequest, AnalysisResult


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


def test_gguf_backend_returns_analysis_result_contract(tmp_path):
    registry_path = _stage_gguf_registry(tmp_path)
    backend = GGUFAnalyzer(registry_path=registry_path, runtime_profile="gguf-laptop")

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
    assert len(result.top_cues) <= 3