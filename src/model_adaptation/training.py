"""Dry-run friendly training orchestration for Phase 3 adapter builds."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from src.config.settings import get_settings
from src.model_adaptation.catalog import get_candidate_by_id
from src.model_adaptation.data import build_training_examples, load_split_records
from src.model_adaptation.registry import build_model_checksum, load_model_registry, save_model_registry
from src.model_adaptation.schemas import ModelArtifactRecord, ModelRegistry, PilotSelection


TrainerCallable = Callable[["TrainingConfig", list[dict[str, Any]], list[dict[str, Any]]], dict[str, Any]]


@dataclass(frozen=True)
class TrainingConfig:
    """Resolved training configuration for one selected Phase 3 candidate."""

    candidate_id: str
    baseline_winner_id: str
    runner_up_id: str
    train_split_path: Path
    val_split_path: Path
    version_tag: str
    output_root: Path
    registry_path: Path
    dry_run: bool = False


def _resolve_selection(selection: PilotSelection | None, registry_path: Path | None) -> PilotSelection:
    if selection is not None:
        return selection
    if registry_path is None:
        raise ValueError("selection or registry_path is required")

    registry = load_model_registry(registry_path)
    if registry.selection is None:
        raise ValueError("Model registry does not contain a pilot selection")
    return registry.selection


def _selected_candidate_ids(selection: PilotSelection) -> set[str]:
    return {selection.baseline_winner_id, selection.runner_up_id}


def build_training_config(
    candidate_id: str,
    train_split_path: Path,
    val_split_path: Path,
    version_tag: str,
    output_root: Path,
    *,
    selection: PilotSelection | None = None,
    registry_path: Path | None = None,
    dry_run: bool = False,
) -> TrainingConfig:
    """Build a training config restricted to the pilot-selected candidates."""

    resolved_selection = _resolve_selection(selection, registry_path)
    allowed_candidate_ids = _selected_candidate_ids(resolved_selection)
    if candidate_id not in allowed_candidate_ids:
        raise ValueError("Training is limited to the pilot-selected baseline winner and runner-up")

    resolved_registry_path = registry_path or get_settings().model_registry_path
    get_candidate_by_id(candidate_id)
    return TrainingConfig(
        candidate_id=candidate_id,
        baseline_winner_id=resolved_selection.baseline_winner_id,
        runner_up_id=resolved_selection.runner_up_id,
        train_split_path=train_split_path,
        val_split_path=val_split_path,
        version_tag=version_tag,
        output_root=output_root,
        registry_path=resolved_registry_path,
        dry_run=dry_run,
    )


def save_adapter_artifacts(
    config: TrainingConfig,
    *,
    selection: PilotSelection | None = None,
    artifact_source_path: Path | None = None,
    artifact_bytes: bytes | None = None,
) -> ModelArtifactRecord:
    """Stage one adapter artifact and register its metadata locally."""

    resolved_selection = _resolve_selection(selection, config.registry_path)
    candidate_dir = config.output_root / config.version_tag / config.candidate_id
    candidate_dir.mkdir(parents=True, exist_ok=True)

    artifact_path = artifact_source_path or (candidate_dir / "adapter-placeholder.bin")
    if artifact_source_path is None:
        payload = artifact_bytes or json.dumps(
            {
                "candidate_id": config.candidate_id,
                "version_tag": config.version_tag,
                "mode": "dry-run" if config.dry_run else "staged",
            },
            ensure_ascii=False,
            indent=2,
        ).encode("utf-8")
        artifact_path.write_bytes(payload)

    artifact_record = ModelArtifactRecord(
        candidate_id=config.candidate_id,
        artifact_type="adapter",
        version_tag=config.version_tag,
        local_path=artifact_path,
        sha256=build_model_checksum(artifact_path),
        profile_name="baseline-winner" if config.candidate_id == resolved_selection.baseline_winner_id else "runner-up",
    )

    if config.registry_path.exists():
        registry = load_model_registry(config.registry_path)
    else:
        registry = ModelRegistry(version_tag=config.version_tag, selection=resolved_selection)

    registry.selection = resolved_selection
    registry.version_tag = config.version_tag
    registry.artifacts = [
        existing
        for existing in registry.artifacts
        if not (
            existing.candidate_id == artifact_record.candidate_id
            and existing.artifact_type == artifact_record.artifact_type
            and existing.version_tag == artifact_record.version_tag
        )
    ]
    registry.artifacts.append(artifact_record)
    save_model_registry(registry, config.registry_path)
    return artifact_record


def run_training(
    config: TrainingConfig,
    *,
    selection: PilotSelection | None = None,
    trainer: TrainerCallable | None = None,
) -> dict[str, Any]:
    """Run a dry-run validation or delegate to a pluggable trainer callable."""

    resolved_selection = _resolve_selection(selection, config.registry_path if config.registry_path.exists() else None)
    if config.candidate_id not in _selected_candidate_ids(resolved_selection):
        raise ValueError("Training is limited to the pilot-selected baseline winner and runner-up")

    candidate = get_candidate_by_id(config.candidate_id)
    train_records = load_split_records(config.train_split_path)
    val_records = load_split_records(config.val_split_path)
    train_examples = build_training_examples(train_records, candidate)
    val_examples = build_training_examples(val_records, candidate)

    if config.dry_run:
        artifact_record = save_adapter_artifacts(config, selection=resolved_selection)
        return {
            "dry_run": True,
            "candidate_id": config.candidate_id,
            "train_examples": len(train_examples),
            "val_examples": len(val_examples),
            "artifact_record": artifact_record,
        }

    if trainer is None:
        raise RuntimeError("Non-dry-run training requires a trainer callable")

    trainer_result = trainer(config, train_examples, val_examples)
    artifact_record = save_adapter_artifacts(
        config,
        selection=resolved_selection,
        artifact_source_path=Path(trainer_result["artifact_path"]),
    )
    return {
        "dry_run": False,
        "candidate_id": config.candidate_id,
        "train_examples": len(train_examples),
        "val_examples": len(val_examples),
        "artifact_record": artifact_record,
    }