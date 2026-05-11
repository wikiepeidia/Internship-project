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
            baseline_winner_id="qwen3.5-4b",
            runner_up_id="qwen2.5-7b-instruct",
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

    assert sorted(subparsers_action.choices.keys()) == ["pilot", "train"]


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
    assert captured_candidates == ["qwen3.5-4b", "qwen2.5-7b-instruct"]


def test_train_command_returns_error_for_non_selected_candidate(tmp_path):
    cli_module = _load_cli_module()
    registry_path = tmp_path / "manifests" / "model-registry.json"
    _write_registry(registry_path)

    exit_code = cli_module.main(
        [
            "train",
            "--candidate",
            "qwen3-4b-instruct-2507",
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