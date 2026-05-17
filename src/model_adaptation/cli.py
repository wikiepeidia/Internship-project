"""Operator-facing CLI for Phase 3 pilot, training, and conversion workflows."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.config.settings import get_settings
from src.model_adaptation.catalog import build_default_catalog
from src.model_adaptation.convert import build_gguf_request, convert_to_gguf
from src.model_adaptation.doctor import format_training_doctor_report, run_training_doctor
from src.model_adaptation.pilot import run_pilot
from src.model_adaptation.registry import load_model_registry, save_model_registry
from src.model_adaptation.schemas import ModelRegistry, PilotSelection
from src.model_adaptation.training import build_training_config, run_training


def _default_split_root() -> Path:
    settings = get_settings()
    retained_root = settings.data_dir / "splits" / "recovered-balanced-claude-v2"
    if retained_root.exists():
        return retained_root
    return settings.data_dir / "splits"


def _default_split_path(split_name: str) -> Path:
    return _default_split_root() / f"{split_name}.jsonl"


def _default_registry_path() -> Path:
    return get_settings().model_registry_path


def _build_dry_run_pilot_rows() -> list[dict[str, object]]:
    return [
        {
            "candidate_id": "qwen3-4b-instruct-2507",
            "quality_score": 0.91,
            "recall_score": 0.94,
            "latency_score": 0.90,
            "memory_fit_score": 0.97,
            "profile_notes": "Locked 4B baseline winner for the laptop profile.",
        },
        {
            "candidate_id": "qwen3.5-4b",
            "quality_score": 0.89,
            "recall_score": 0.90,
            "latency_score": 0.83,
            "memory_fit_score": 0.94,
            "profile_notes": "Locked 4B runner-up for the accelerated profile.",
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
    """Build the operator parser for pilot, training, and conversion flows."""

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
    train_parser.add_argument(
        "--base-model-path",
        type=Path,
        default=None,
        help="Override the local base checkpoint path",
    )
    train_parser.add_argument(
        "--num-train-epochs",
        type=float,
        default=1.0,
        help="Epoch count for full runs when --max-steps is not set",
    )
    train_parser.add_argument(
        "--max-steps",
        type=int,
        default=None,
        help="Maximum optimizer steps; use small values for smoke tests",
    )
    train_parser.add_argument(
        "--per-device-train-batch-size",
        type=int,
        default=1,
        help="Per-device train batch size",
    )
    train_parser.add_argument(
        "--gradient-accumulation-steps",
        type=int,
        default=4,
        help="Gradient accumulation steps",
    )
    train_parser.add_argument(
        "--learning-rate",
        type=float,
        default=2e-4,
        help="Learning rate for adapter tuning",
    )
    train_parser.add_argument(
        "--logging-steps",
        type=int,
        default=10,
        help="Training log interval in optimizer steps",
    )
    train_parser.add_argument(
        "--save-steps",
        type=int,
        default=50,
        help="Checkpoint save interval in optimizer steps",
    )
    train_parser.add_argument(
        "--save-total-limit",
        type=int,
        default=2,
        help="Maximum number of saved checkpoints to keep",
    )
    train_parser.add_argument(
        "--max-seq-length",
        type=int,
        default=1024,
        help="Maximum tokenized sequence length",
    )
    train_parser.add_argument(
        "--resume-from-checkpoint",
        default=None,
        help="Checkpoint path to resume from, or 'latest'",
    )
    train_parser.add_argument(
        "--device",
        choices=["auto", "cpu", "cuda"],
        default="auto",
        help="Execution device for the training backend",
    )
    train_parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="Run a short checkpoint-friendly preflight training job",
    )
    train_parser.add_argument(
        "--full-precision",
        action="store_true",
        help="Disable optional 4-bit loading and force full-precision LoRA",
    )
    train_parser.add_argument("--dry-run", action="store_true", help="Validate config without a real fine-tune")
    train_parser.set_defaults(handler=handle_train)

    convert_parser = subparsers.add_parser("convert", help="Convert one trained adapter into a GGUF artifact")
    convert_parser.add_argument(
        "--candidate",
        required=True,
        help="Candidate id or alias: baseline-winner | runner-up",
    )
    convert_parser.add_argument("--version-tag", required=True, help="Version tag for GGUF outputs")
    convert_parser.add_argument(
        "--output-root",
        type=Path,
        default=get_settings().model_artifact_root,
        help="Root directory for local model artifacts",
    )
    convert_parser.add_argument(
        "--registry-path",
        type=Path,
        default=_default_registry_path(),
        help="Path to the local model registry JSON",
    )
    convert_parser.add_argument(
        "--quantization-profile",
        default="q4_k_m",
        help="Requested GGUF quantization profile",
    )
    convert_parser.add_argument("--dry-run", action="store_true", help="Validate conversion wiring without producing GGUF output")
    convert_parser.set_defaults(handler=handle_convert)

    doctor_parser = subparsers.add_parser("doctor", help="Check local Phase 3 training readiness")
    doctor_parser.add_argument(
        "--candidate",
        default="baseline-winner",
        help="Candidate id or alias: baseline-winner | runner-up",
    )
    doctor_parser.add_argument(
        "--train-split",
        type=Path,
        default=_default_split_path("train"),
        help="Training split JSONL path",
    )
    doctor_parser.add_argument(
        "--val-split",
        type=Path,
        default=_default_split_path("val"),
        help="Validation split JSONL path",
    )
    doctor_parser.add_argument(
        "--output-root",
        type=Path,
        default=get_settings().model_artifact_root,
        help="Root directory for local model artifacts",
    )
    doctor_parser.add_argument(
        "--registry-path",
        type=Path,
        default=_default_registry_path(),
        help="Path to the local model registry JSON",
    )
    doctor_parser.set_defaults(handler=handle_doctor)

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
        base_model_path=args.base_model_path,
        num_train_epochs=args.num_train_epochs,
        max_steps=args.max_steps,
        per_device_train_batch_size=args.per_device_train_batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        learning_rate=args.learning_rate,
        logging_steps=args.logging_steps,
        save_steps=args.save_steps,
        save_total_limit=args.save_total_limit,
        max_seq_length=args.max_seq_length,
        smoke_test=args.smoke_test,
        resume_from_checkpoint=args.resume_from_checkpoint,
        device=args.device,
        use_4bit=not args.full_precision,
    )
    result = run_training(config, selection=selection)
    summary_parts = [
        f"candidate={result['candidate_id']}",
        f"train_examples={result['train_examples']}",
        f"val_examples={result['val_examples']}",
    ]
    if not result["dry_run"]:
        if result.get("device") is not None:
            summary_parts.append(f"device={result['device']}")
        if result.get("quantization_mode") is not None:
            summary_parts.append(f"quantization={result['quantization_mode']}")
        if result.get("checkpoint_path") is not None:
            summary_parts.append(f"checkpoint={result['checkpoint_path']}")
        if result.get("summary_path") is not None:
            summary_parts.append(f"summary={result['summary_path']}")
    print(f"Training {'dry-run' if result['dry_run'] else 'run'} complete: {' '.join(summary_parts)}")
    return 0


def handle_convert(args: argparse.Namespace) -> int:
    """Run the GGUF conversion flow for the selected candidate alias."""

    selection = _load_selection(args.registry_path)
    resolved_candidate_id = _resolve_candidate_alias(args.candidate, selection)
    request = build_gguf_request(
        resolved_candidate_id,
        args.version_tag,
        registry_path=args.registry_path,
        output_root=args.output_root,
        selection=selection,
        quantization_profile=args.quantization_profile,
    )
    result = convert_to_gguf(
        request,
        registry_path=args.registry_path,
        selection=selection,
        dry_run=args.dry_run,
    )
    artifact_record = result["artifact_record"]
    print(
        f"Conversion {'dry-run' if result['dry_run'] else 'run'} complete: "
        f"candidate={artifact_record.candidate_id} profile={artifact_record.profile_name} artifact={artifact_record.local_path}"
    )
    return 0


def handle_doctor(args: argparse.Namespace) -> int:
    """Run the training doctor command and print the readiness report."""

    status = run_training_doctor(
        candidate=args.candidate,
        train_split=args.train_split,
        val_split=args.val_split,
        output_root=args.output_root,
        registry_path=args.registry_path,
    )
    print(format_training_doctor_report(status))
    return 0 if status.ready else 1


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