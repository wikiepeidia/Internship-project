"""Wave 0 CLI tests for the Phase 3 operator tooling."""

from __future__ import annotations

import argparse
import importlib
from pathlib import Path
from types import SimpleNamespace

from src.model_adaptation.registry import save_model_registry
from src.model_adaptation.schemas import ModelRegistry, PilotSelection


def _load_cli_module():
    return importlib.import_module("src.model_adaptation.cli")


def _write_registry(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    registry = ModelRegistry(
        version_tag="phase3-smoke",
        selection=PilotSelection(
            baseline_winner_id="qwen3-4b-instruct-2507",
            runner_up_id="qwen3.5-4b",
            selection_notes="Pilot winner and runner-up for CLI tests.",
        ),
    )
    save_model_registry(registry, path)


def test_cli_exposes_pilot_and_train_commands():
    cli_module = _load_cli_module()
    parser = cli_module.build_parser()

    subparsers_action = next(
        action for action in parser._actions if isinstance(action, argparse._SubParsersAction)
    )

    assert sorted(subparsers_action.choices.keys()) == ["convert", "doctor", "pilot", "train"]


def test_default_split_path_prefers_retained_lineage_when_present(tmp_path, monkeypatch):
    cli_module = _load_cli_module()
    retained_root = tmp_path / "data" / "splits" / "recovered-balanced-claude-v2"
    retained_root.mkdir(parents=True)
    (retained_root / "train.jsonl").write_text("", encoding="utf-8")

    class FakeSettings:
        data_dir = tmp_path / "data"

    monkeypatch.setattr(cli_module, "get_settings", lambda: FakeSettings())

    assert cli_module._default_split_path("train") == retained_root / "train.jsonl"


def test_train_dry_run_uses_baseline_winner_and_runner_up_only(tmp_path, monkeypatch):
    cli_module = _load_cli_module()
    registry_path = tmp_path / "manifests" / "model-registry.json"
    _write_registry(registry_path)
    captured_candidates: list[str] = []

    def fake_build_training_config(**kwargs):
        captured_candidates.append(kwargs["candidate_id"])
        return SimpleNamespace(candidate_id=kwargs["candidate_id"], dry_run=kwargs["dry_run"])

    def fake_run_training(config, *, selection=None):
        return {
            "dry_run": config.dry_run,
            "candidate_id": config.candidate_id,
            "train_examples": 2,
            "val_examples": 1,
        }

    monkeypatch.setattr(cli_module, "build_training_config", fake_build_training_config)
    monkeypatch.setattr(cli_module, "run_training", fake_run_training)

    baseline_exit = cli_module.main(
        [
            "train",
            "--candidate",
            "baseline-winner",
            "--version-tag",
            "phase3-smoke",
            "--train-split",
            str(tmp_path / "train.jsonl"),
            "--val-split",
            str(tmp_path / "val.jsonl"),
            "--registry-path",
            str(registry_path),
            "--dry-run",
        ]
    )
    runner_up_exit = cli_module.main(
        [
            "train",
            "--candidate",
            "runner-up",
            "--version-tag",
            "phase3-smoke",
            "--train-split",
            str(tmp_path / "train.jsonl"),
            "--val-split",
            str(tmp_path / "val.jsonl"),
            "--registry-path",
            str(registry_path),
            "--dry-run",
        ]
    )

    assert baseline_exit == 0
    assert runner_up_exit == 0
    assert captured_candidates == ["qwen3-4b-instruct-2507", "qwen3.5-4b"]


def test_train_command_returns_error_for_non_selected_candidate(tmp_path):
    cli_module = _load_cli_module()
    registry_path = tmp_path / "manifests" / "model-registry.json"
    _write_registry(registry_path)

    exit_code = cli_module.main(
        [
            "train",
            "--candidate",
            "qwen2.5-7b-instruct",
            "--version-tag",
            "phase3-smoke",
            "--train-split",
            str(tmp_path / "train.jsonl"),
            "--val-split",
            str(tmp_path / "val.jsonl"),
            "--registry-path",
            str(registry_path),
            "--dry-run",
        ]
    )

    assert exit_code == 1


def test_doctor_command_formats_report_and_returns_success(monkeypatch, capsys):
    cli_module = _load_cli_module()

    monkeypatch.setattr(
        cli_module,
        "run_training_doctor",
        lambda **kwargs: SimpleNamespace(ready=True),
    )
    monkeypatch.setattr(cli_module, "format_training_doctor_report", lambda status: "TRAIN READY")

    exit_code = cli_module.main(["doctor", "--candidate", "baseline-winner"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "TRAIN READY" in captured.out


def test_convert_command_resolves_baseline_winner_alias(tmp_path, monkeypatch, capsys):
    cli_module = _load_cli_module()
    registry_path = tmp_path / "manifests" / "model-registry.json"
    _write_registry(registry_path)
    captured: dict[str, object] = {}

    def fake_build_gguf_request(candidate_id, version_tag, **kwargs):
        captured["candidate_id"] = candidate_id
        captured["version_tag"] = version_tag
        return SimpleNamespace(candidate_id=candidate_id, profile_name="gguf-laptop", output_path=tmp_path / "artifact.gguf")

    def fake_convert_to_gguf(request, **kwargs):
        artifact_record = SimpleNamespace(
            candidate_id=request.candidate_id,
            profile_name=request.profile_name,
            local_path=request.output_path,
        )
        return {"dry_run": True, "artifact_record": artifact_record}

    monkeypatch.setattr(cli_module, "build_gguf_request", fake_build_gguf_request)
    monkeypatch.setattr(cli_module, "convert_to_gguf", fake_convert_to_gguf)

    exit_code = cli_module.main(
        [
            "convert",
            "--candidate",
            "baseline-winner",
            "--version-tag",
            "phase3-gguf",
            "--registry-path",
            str(registry_path),
            "--dry-run",
        ]
    )
    captured_output = capsys.readouterr()

    assert exit_code == 0
    assert captured["candidate_id"] == "qwen3-4b-instruct-2507"
    assert captured["version_tag"] == "phase3-gguf"
    assert "Conversion dry-run complete" in captured_output.out