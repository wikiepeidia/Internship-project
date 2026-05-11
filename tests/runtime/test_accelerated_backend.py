"""Phase 3 accelerated-backend expectations."""

from __future__ import annotations

from pathlib import Path

from src.model_adaptation.schemas import PilotSelection
from src.model_adaptation.training import build_training_config, save_adapter_artifacts
from src.runtime.analyzers.accelerated import AcceleratedAnalyzer
from src.runtime.contracts import AnalysisRequest, AnalysisResult


def _selection() -> PilotSelection:
    return PilotSelection(
        baseline_winner_id="qwen3.5-4b",
        runner_up_id="qwen2.5-7b-instruct",
        selection_notes="Winner and runner-up selected in the pilot.",
    )


def _stage_accelerated_registry(tmp_path: Path) -> Path:
    registry_path = tmp_path / "manifests" / "model-registry.json"
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


def test_accelerated_backend_returns_phase2_contract_shape(tmp_path):
    registry_path = _stage_accelerated_registry(tmp_path)
    backend = AcceleratedAnalyzer(registry_path=registry_path, runtime_profile="accelerated-local")

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
    assert len(result.top_cues) <= 3