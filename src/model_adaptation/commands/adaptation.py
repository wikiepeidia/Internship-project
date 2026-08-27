"""Pilot, training, conversion, and doctor command family."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Callable


Handler = Callable[[argparse.Namespace], int]


def _register_pilot(
    subparsers: argparse._SubParsersAction, handler: Handler
) -> None:
    parser = subparsers.add_parser("pilot", help="Run the Phase 3 pilot scaffold")
    parser.add_argument("--version-tag", required=True, help="Version tag for pilot outputs")
    parser.add_argument(
        "--evaluated-split",
        default="val",
        choices=["train", "val", "test", "pilot"],
        help="Split label recorded in pilot scorecards",
    )
    parser.add_argument(
        "--registry-path",
        type=Path,
        default=None,
        help="Path to the local model registry JSON",
    )
    parser.add_argument("--dry-run", action="store_true", help="Use local mock pilot metrics")
    parser.set_defaults(handler=handler)


def _add_training_core_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--candidate",
        required=True,
        help="Candidate id or alias: baseline-winner | runner-up",
    )
    parser.add_argument("--version-tag", required=True, help="Version tag for training outputs")
    parser.add_argument(
        "--train-split", type=Path, required=True, help="Canonical data/splits/train.jsonl path"
    )
    parser.add_argument(
        "--val-split", type=Path, required=True, help="Canonical data/splits/val.jsonl path"
    )
    parser.add_argument(
        "--output-root", type=Path, default=None, help="Root directory for local model artifacts"
    )
    parser.add_argument(
        "--registry-path", type=Path, default=None, help="Path to the local model registry JSON"
    )
    parser.add_argument(
        "--base-model-path", type=Path, default=None, help="Override the local base checkpoint path"
    )
    parser.add_argument(
        "--num-train-epochs",
        type=float,
        default=1.0,
        help="Epoch count for full runs when --max-steps is not set",
    )
    parser.add_argument(
        "--max-steps", type=int, default=None, help="Maximum optimizer steps; use small values for smoke tests"
    )


def _add_training_optimizer_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--per-device-train-batch-size", type=int, default=1, help="Per-device train batch size"
    )
    parser.add_argument(
        "--gradient-accumulation-steps", type=int, default=4, help="Gradient accumulation steps"
    )
    parser.add_argument("--learning-rate", type=float, default=2e-4, help="Learning rate for adapter tuning")
    parser.add_argument(
        "--logging-steps", type=int, default=10, help="Training log interval in optimizer steps"
    )
    parser.add_argument(
        "--save-steps", type=int, default=50, help="Checkpoint save interval in optimizer steps"
    )
    parser.add_argument(
        "--save-total-limit", type=int, default=2, help="Maximum number of saved checkpoints to keep"
    )
    parser.add_argument(
        "--max-seq-length", type=int, default=1024, help="Maximum tokenized sequence length"
    )
    parser.add_argument(
        "--resume-from-checkpoint",
        default=None,
        help="Exact checkpoint-N path with a verified compatibility manifest; 'latest' is forbidden",
    )
    parser.add_argument(
        "--device",
        choices=["auto", "cpu", "cuda"],
        default="auto",
        help="Execution device for the training backend",
    )
    parser.add_argument(
        "--smoke-test", action="store_true", help="Run a short checkpoint-friendly preflight training job"
    )


def _add_training_evidence_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--adaptation-mode",
        required=True,
        choices=["lora", "qlora"],
        help="Explicit adapter mode; QLoRA never falls back to LoRA",
    )
    parser.add_argument(
        "--run-kind",
        choices=["probe", "full"],
        default="full",
        help="Bounded probe or full evidence-producing run",
    )
    parser.add_argument(
        "--post-warmup-steps",
        type=int,
        default=None,
        help="Required 30-50 post-warm-up optimizer steps for a probe run",
    )
    parser.add_argument(
        "--warmup-steps", type=int, default=5, help="Measured probe warm-up optimizer steps (default: 5)"
    )
    parser.add_argument("--run-id", default=None, help="Safe immutable Phase 40 run identifier")
    parser.add_argument(
        "--model-revision",
        default="cdbee75f17c01a7cc42f958dc650907174af0554",
        help="Pinned 40-hex base-model revision",
    )
    parser.add_argument(
        "--run-request-path",
        type=Path,
        default=None,
        help="Verified Phase 40 full-run request supplying transfer authority (required for full publication)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Validate config without a real fine-tune")


def _register_train(
    subparsers: argparse._SubParsersAction, handler: Handler
) -> None:
    parser = subparsers.add_parser("train", help="Run the Phase 3 training scaffold")
    _add_training_core_arguments(parser)
    _add_training_optimizer_arguments(parser)
    _add_training_evidence_arguments(parser)
    parser.set_defaults(handler=handler)


def _register_convert(
    subparsers: argparse._SubParsersAction, handler: Handler
) -> None:
    parser = subparsers.add_parser("convert", help="Convert one trained adapter into a GGUF artifact")
    parser.add_argument(
        "--candidate", required=True, help="Candidate id or alias: baseline-winner | runner-up"
    )
    parser.add_argument("--version-tag", required=True, help="Version tag for GGUF outputs")
    parser.add_argument(
        "--output-root", type=Path, default=None, help="Root directory for local model artifacts"
    )
    parser.add_argument(
        "--registry-path", type=Path, default=None, help="Path to the local model registry JSON"
    )
    parser.add_argument(
        "--quantization-profile", default="q4_k_m", help="Requested GGUF quantization profile"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Validate conversion wiring without producing GGUF output"
    )
    parser.set_defaults(handler=handler)


def _register_doctor(
    subparsers: argparse._SubParsersAction, handler: Handler
) -> None:
    parser = subparsers.add_parser("doctor", help="Check local Phase 3 training readiness")
    parser.add_argument(
        "--candidate", default="baseline-winner", help="Candidate id or alias: baseline-winner | runner-up"
    )
    parser.add_argument("--train-split", type=Path, default=None, help="Training split JSONL path")
    parser.add_argument("--val-split", type=Path, default=None, help="Validation split JSONL path")
    parser.add_argument(
        "--output-root", type=Path, default=None, help="Root directory for local model artifacts"
    )
    parser.add_argument(
        "--registry-path", type=Path, default=None, help="Path to the local model registry JSON"
    )
    parser.set_defaults(handler=handler)
    parser.add_argument(
        "--adaptation-mode",
        required=True,
        choices=["lora", "qlora"],
        help="Mode whose readiness must be checked without fallback",
    )


def register_commands(
    subparsers: argparse._SubParsersAction,
    *,
    pilot: Handler,
    train: Handler,
    convert: Handler,
    doctor: Handler,
) -> None:
    """Register the four active adaptation commands in frozen order."""

    _register_pilot(subparsers, pilot)
    _register_train(subparsers, train)
    _register_convert(subparsers, convert)
    _register_doctor(subparsers, doctor)


def _default_split_root() -> Path:
    from src.config.settings import get_settings

    settings = get_settings()
    retained_root = settings.data_dir / "splits" / "recovered-balanced-claude-v2"
    if retained_root.exists():
        return retained_root
    return settings.data_dir / "splits"


def _default_split_path(split_name: str) -> Path:
    return _default_split_root() / f"{split_name}.jsonl"


def _default_registry_path() -> Path:
    from src.config.settings import get_settings

    return get_settings().model_registry_path


def _default_phase_five_split_path() -> Path:
    """Retain the retired helper name without restoring any evaluation route."""

    raise RuntimeError(
        "The legacy Phase 5 split evaluator is retired; use phase41-run-once."
    )


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


def _load_selection(registry_path: Path):  # noqa: ANN202
    from src.model_adaptation.registry import load_model_registry

    registry = load_model_registry(registry_path)
    if registry.selection is None:
        raise ValueError("Model registry does not contain a pilot selection")
    return registry.selection


def _resolve_candidate_alias(candidate_arg: str, selection):  # noqa: ANN001, ANN201
    if candidate_arg == "baseline-winner":
        return selection.baseline_winner_id
    if candidate_arg == "runner-up":
        return selection.runner_up_id
    return candidate_arg


def handle_pilot(args: argparse.Namespace) -> int:
    """Run the lightweight pilot scoring scaffold and persist selection metadata."""

    from src.model_adaptation.catalog import build_default_catalog
    from src.model_adaptation.pilot import run_pilot
    from src.model_adaptation.registry import save_model_registry
    from src.model_adaptation.schemas import ModelRegistry

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
    registry_path = args.registry_path or _default_registry_path()
    save_model_registry(registry, registry_path)
    print(
        f"Pilot dry-run complete: baseline={selection.baseline_winner_id} "
        f"runner-up={selection.runner_up_id} registry={registry_path}"
    )
    return 0


def handle_train(args: argparse.Namespace) -> int:
    """Run the training flow for the selected candidate alias."""

    from src.config.settings import get_settings
    from src.model_adaptation.phase40_contract import preflight_phase40_inputs
    from src.model_adaptation.phase40_handoff import (
        RunRequest,
        transfer_authority_from_request,
        verify_phase40_run_request,
    )
    from src.model_adaptation.phase40_modes import AdaptationMode, RunKind
    from src.model_adaptation.training import build_training_config, run_training

    data_contract = preflight_phase40_inputs(
        args.train_split, args.val_split, repo_root=Path.cwd()
    )
    registry_path = args.registry_path or _default_registry_path()
    output_root = args.output_root or get_settings().model_artifact_root
    selection = _load_selection(registry_path)
    resolved_candidate_id = _resolve_candidate_alias(args.candidate, selection)
    transfer_authority = None
    if args.run_request_path is not None:
        run_request = RunRequest.model_validate_json(
            args.run_request_path.read_text(encoding="utf-8", errors="strict")
        )
        verify_phase40_run_request(run_request, repo_root=Path.cwd())
        if args.run_id is None or args.run_id not in {run.run_id for run in run_request.runs}:
            raise ValueError("--run-id must identify one run in --run-request-path")
        requested = next(run for run in run_request.runs if run.run_id == args.run_id)
        if (
            requested.model_family.value != "qwen"
            or requested.adaptation_mode != AdaptationMode(args.adaptation_mode)
            or requested.run_kind != RunKind.FULL.value
        ):
            raise ValueError("training CLI identity differs from its frozen run request")
        transfer_authority = transfer_authority_from_request(run_request)
    config = build_training_config(
        candidate_id=resolved_candidate_id,
        train_split_path=args.train_split,
        val_split_path=args.val_split,
        version_tag=args.version_tag,
        output_root=output_root,
        registry_path=registry_path,
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
        adaptation_mode=AdaptationMode(args.adaptation_mode),
        run_kind=RunKind(args.run_kind),
        probe_post_warmup_steps=args.post_warmup_steps,
        probe_warmup_steps=args.warmup_steps,
        run_id=args.run_id,
        model_revision=args.model_revision,
        transfer_authority=transfer_authority,
        sanitized_argv=getattr(args, "_phase40_raw_argv", None),
    )
    result = run_training(config, data_contract=data_contract, selection=selection)
    summary_parts = [
        f"candidate={result['candidate_id']}",
        f"train_examples={result['train_examples']}",
        f"val_examples={result['val_examples']}",
    ]
    if not result["dry_run"]:
        for key, label in (
            ("device", "device"),
            ("quantization_mode", "quantization"),
            ("checkpoint_path", "checkpoint"),
            ("summary_path", "summary"),
        ):
            if result.get(key) is not None:
                summary_parts.append(f"{label}={result[key]}")
    print(f"Training {'dry-run' if result['dry_run'] else 'run'} complete: {' '.join(summary_parts)}")
    return 0


def handle_convert(args: argparse.Namespace) -> int:
    """Run the GGUF conversion flow for the selected candidate alias."""

    from src.config.settings import get_settings
    from src.model_adaptation.convert import build_gguf_request, convert_to_gguf

    registry_path = args.registry_path or _default_registry_path()
    output_root = args.output_root or get_settings().model_artifact_root
    selection = _load_selection(registry_path)
    resolved_candidate_id = _resolve_candidate_alias(args.candidate, selection)
    request = build_gguf_request(
        resolved_candidate_id,
        args.version_tag,
        registry_path=registry_path,
        output_root=output_root,
        selection=selection,
        quantization_profile=args.quantization_profile,
    )
    result = convert_to_gguf(
        request,
        registry_path=registry_path,
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

    from src.config.settings import get_settings
    from src.model_adaptation.doctor import (
        format_training_doctor_report,
        run_training_doctor,
    )
    from src.model_adaptation.phase40_modes import AdaptationMode

    registry_path = args.registry_path or _default_registry_path()
    train_split = args.train_split or _default_split_path("train")
    val_split = args.val_split or _default_split_path("val")
    output_root = args.output_root or get_settings().model_artifact_root
    status = run_training_doctor(
        candidate=args.candidate,
        adaptation_mode=AdaptationMode(args.adaptation_mode),
        train_split=train_split,
        val_split=val_split,
        output_root=output_root,
        registry_path=registry_path,
    )
    print(format_training_doctor_report(status))
    return 0 if status.ready else 1
