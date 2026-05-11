"""Operator-facing CLI for Phase 3 pilot and training workflows."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.config.settings import get_settings
from src.model_adaptation.catalog import build_default_catalog
from src.model_adaptation.pilot import run_pilot
from src.model_adaptation.registry import load_model_registry, save_model_registry
from src.model_adaptation.schemas import ModelRegistry, PilotSelection
from src.model_adaptation.training import build_training_config, run_training


def _default_split_path(split_name: str) -> Path:
    return get_settings().data_dir / "splits" / f"{split_name}.jsonl"


def _default_registry_path() -> Path:
    return get_settings().model_registry_path


def _build_dry_run_pilot_rows() -> list[dict[str, object]]:
    return [
        {
            "candidate_id": "qwen3.5-4b",
            "quality_score": 0.91,
            "recall_score": 0.94,
            "latency_score": 0.83,
            "memory_fit_score": 0.95,
            "profile_notes": "Balanced 4B candidate for the laptop baseline.",
        },
        {
            "candidate_id": "qwen3-4b-instruct-2507",
            "quality_score": 0.89,
            "recall_score": 0.90,
            "latency_score": 0.90,
            "memory_fit_score": 0.94,
            "profile_notes": "Faster 4B fallback with slightly lower recall.",
        },
        {
            "candidate_id": "qwen2.5-7b-instruct",
            "quality_score": 0.96,
            "recall_score": 0.95,
            "latency_score": 0.64,
            "memory_fit_score": 0.57,
            "hardware_penalty": 0.10,
            "profile_notes": "Stronger capacity, but weaker laptop feasibility.",
        },
    ]


def _load_selection(registry_path: Path) -> PilotSelection:
    registry = load_model_registry(registry_path)
    if registry.selection is None:
        raise ValueError("Model registry does not contain a pilot selection")
    return registry.selection


def _resolve_candidate_alias(candidate_arg: str, selection: PilotSelection) -> str:
    if candidate_arg == "baseline-winner":
        return selection.baseline_winner_id
    if candidate_arg == "runner-up":
        return selection.runner_up_id
    return candidate_arg


def build_parser() -> argparse.ArgumentParser:
    """Build the operator parser for pilot and training flows."""

    parser = argparse.ArgumentParser(prog="python -m src.model_adaptation.cli", allow_abbrev=False)
    subparsers = parser.add_subparsers(dest="command", required=True)

    pilot_parser = subparsers.add_parser("pilot", help="Run the Phase 3 pilot scaffold")
    pilot_parser.add_argument("--version-tag", required=True, help="Version tag for pilot outputs")
    pilot_parser.add_argument(
        "--evaluated-split",
        default="val",
        choices=["train", "val", "test", "pilot"],
        help="Split label recorded in pilot scorecards",
    )
    pilot_parser.add_argument(
        "--registry-path",
        type=Path,
        default=_default_registry_path(),
        help="Path to the local model registry JSON",
    )
    pilot_parser.add_argument("--dry-run", action="store_true", help="Use local mock pilot metrics")
    pilot_parser.set_defaults(handler=handle_pilot)

    train_parser = subparsers.add_parser("train", help="Run the Phase 3 training scaffold")
    train_parser.add_argument(
        "--candidate",
        required=True,
        help="Candidate id or alias: baseline-winner | runner-up",
    )
    train_parser.add_argument("--version-tag", required=True, help="Version tag for training outputs")
    train_parser.add_argument(
        "--train-split",
        type=Path,
        default=_default_split_path("train"),
        help="Training split JSONL path",
    )
    train_parser.add_argument(
        "--val-split",
        type=Path,
        default=_default_split_path("val"),
        help="Validation split JSONL path",
    )
    train_parser.add_argument(
        "--output-root",
        type=Path,
        default=get_settings().model_artifact_root,
        help="Root directory for local model artifacts",
    )
    train_parser.add_argument(
        "--registry-path",
        type=Path,
        default=_default_registry_path(),
        help="Path to the local model registry JSON",
    )
    train_parser.add_argument("--dry-run", action="store_true", help="Validate config without a real fine-tune")
    train_parser.set_defaults(handler=handle_train)

    return parser


def handle_pilot(args: argparse.Namespace) -> int:
    """Run the lightweight pilot scoring scaffold and persist selection metadata."""

    if not args.dry_run:
        raise RuntimeError("Pilot execution currently supports --dry-run only")

    scorecards, selection = run_pilot(
        build_default_catalog(),
        _build_dry_run_pilot_rows(),
        evaluated_split=args.evaluated_split,
    )
    registry = ModelRegistry(
        version_tag=args.version_tag,
        selection=selection,
        scorecards=scorecards,
    )
    save_model_registry(registry, args.registry_path)
    print(
        f"Pilot dry-run complete: baseline={selection.baseline_winner_id} "
        f"runner-up={selection.runner_up_id} registry={args.registry_path}"
    )
    return 0


def handle_train(args: argparse.Namespace) -> int:
    """Run the dry-run training scaffold for the selected candidate alias."""

    selection = _load_selection(args.registry_path)
    resolved_candidate_id = _resolve_candidate_alias(args.candidate, selection)
    config = build_training_config(
        candidate_id=resolved_candidate_id,
        train_split_path=args.train_split,
        val_split_path=args.val_split,
        version_tag=args.version_tag,
        output_root=args.output_root,
        registry_path=args.registry_path,
        selection=selection,
        dry_run=args.dry_run,
    )
    result = run_training(config, selection=selection)
    print(
        f"Training {'dry-run' if result['dry_run'] else 'run'} complete: "
        f"candidate={result['candidate_id']} train_examples={result['train_examples']} "
        f"val_examples={result['val_examples']}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for the Phase 3 operator tooling."""

    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.handler(args)
    except (RuntimeError, ValueError, FileNotFoundError) as exc:
        print(str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())