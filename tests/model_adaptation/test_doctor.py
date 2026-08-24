"""Training doctor expectations for the Phase 3 local adaptation path."""

from __future__ import annotations

import importlib
import json
from pathlib import Path
from types import SimpleNamespace

from src.model_adaptation.registry import save_model_registry
from src.model_adaptation.schemas import ModelRegistry, PilotSelection


def _load_doctor_module():
    return importlib.import_module("src.model_adaptation.doctor")


def _stage_training_paths(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    output_root = tmp_path / "models"
    registry_path = tmp_path / "manifests" / "model-registry.json"
    train_split = tmp_path / "data" / "splits" / "train.jsonl"
    val_split = tmp_path / "data" / "splits" / "val.jsonl"
    train_split.parent.mkdir(parents=True, exist_ok=True)
    train_split.write_text("", encoding="utf-8")
    val_split.write_text("", encoding="utf-8")

    base_model_path = output_root / "base" / "qwen3.5-4b"
    base_model_path.mkdir(parents=True, exist_ok=True)
    manifest_path = output_root / "manifests" / "download-manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            {
                "models": [
                    {
                        "candidate_id": "qwen3.5-4b",
                        "repo_id": "Qwen/Qwen3.5-4B",
                        "local_path": str(base_model_path),
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    save_model_registry(
        ModelRegistry(
            version_tag="phase3-smoke",
            selection=PilotSelection(
                baseline_winner_id="qwen3.5-4b",
                runner_up_id="qwen2.5-7b-instruct",
                selection_notes="Pilot selection for doctor tests.",
            ),
        ),
        registry_path,
    )
    return output_root, registry_path, train_split, val_split


def test_training_doctor_reports_missing_dependency_with_exact_command(monkeypatch, tmp_path):
    doctor_module = _load_doctor_module()
    output_root, registry_path, train_split, val_split = _stage_training_paths(tmp_path)

    class FakeSettings:
        data_dir = tmp_path / "data"
        model_artifact_root = output_root
        model_registry_path = registry_path

    real_import_module = doctor_module.importlib.import_module

    class FakeTorch:
        class cuda:
            @staticmethod
            def is_available() -> bool:
                return False

    def fake_import_module(name: str):
        if name == "peft":
            raise ImportError("peft missing")
        if name == "torch":
            return FakeTorch()
        if name in {"transformers", "accelerate"}:
            return object()
        return real_import_module(name)

    monkeypatch.setattr(doctor_module, "get_settings", lambda: FakeSettings())
    monkeypatch.setattr(doctor_module.importlib, "import_module", fake_import_module)

    status = doctor_module.run_training_doctor(
        candidate="baseline-winner",
        adaptation_mode="lora",
        train_split=train_split,
        val_split=val_split,
        output_root=output_root,
        registry_path=registry_path,
    )
    report = doctor_module.format_training_doctor_report(status)

    assert status.ready is False
    assert any(
        check.remediation_command == "python -m pip install -e .[dev,train]"
        for check in status.checks
    )
    assert "python -m pip install -e .[dev,train]" in report


def test_training_doctor_reports_ready_state_and_smoke_command(monkeypatch, tmp_path):
    doctor_module = _load_doctor_module()
    output_root, registry_path, train_split, val_split = _stage_training_paths(tmp_path)

    class FakeSettings:
        data_dir = tmp_path / "data"
        model_artifact_root = output_root
        model_registry_path = registry_path

    real_import_module = doctor_module.importlib.import_module

    class FakeTorch:
        class cuda:
            @staticmethod
            def is_available() -> bool:
                return True

            @staticmethod
            def get_device_name(index: int) -> str:
                return "Fake GPU"

            @staticmethod
            def get_device_properties(index: int) -> SimpleNamespace:
                return SimpleNamespace(total_memory=8 * 1024**3)

    def fake_import_module(name: str):
        if name == "torch":
            return FakeTorch()
        if name in {"transformers", "peft", "accelerate"}:
            return object()
        return real_import_module(name)

    monkeypatch.setattr(doctor_module, "get_settings", lambda: FakeSettings())
    monkeypatch.setattr(doctor_module.importlib, "import_module", fake_import_module)
    monkeypatch.setattr(doctor_module.importlib.util, "find_spec", lambda name: None)

    status = doctor_module.run_training_doctor(
        candidate="baseline-winner",
        adaptation_mode="lora",
        train_split=train_split,
        val_split=val_split,
        output_root=output_root,
        registry_path=registry_path,
    )
    report = doctor_module.format_training_doctor_report(status)

    assert status.ready is True
    assert status.backend_name == "training"
    assert "Fake GPU" in report
    assert "phase40-smoke" in report
    assert (
        "python -m src.model_adaptation.cli train --candidate baseline-winner "
        "--adaptation-mode lora --run-kind probe --version-tag phase40-smoke --smoke-test"
        in report
    )
