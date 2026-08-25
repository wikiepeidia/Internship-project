"""Operator-facing CLI for Phase 3 pilot, training, and conversion workflows."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

from src.config.settings import get_settings
from src.model_adaptation.catalog import build_default_catalog
from src.model_adaptation.convert import build_gguf_request, convert_to_gguf
from src.model_adaptation.doctor import format_training_doctor_report, run_training_doctor
from src.model_adaptation.explanation_review import build_manual_review_pack
from src.model_adaptation.pilot import run_pilot
from src.model_adaptation.phase40_contract import preflight_phase40_inputs
from src.model_adaptation.phase40_handoff import (
    InputBundleReference,
    LocalTwoModelOperatorReturn,
    PackageDecision,
    Phase40ComparisonManifest,
    ReturnedBundleRoot,
    ReturnedGpuIdentity,
    ReviewQueueManifest,
    ReviewQueueRow,
    ReviewerReturnRow,
    RunRequest,
    build_phase40_input_bundle,
    build_phase40_source_bundle,
    finalize_phase40_comparison,
    finalize_phase40_human_review,
    freeze_phase40_scope_amendment,
    load_frozen_phase40_run_request,
    load_frozen_phase40_scope_amendment,
    load_phase40_selected_prediction_bundles,
    transfer_authority_from_request,
    verify_phase40_input_bundle,
    verify_phase40_review_queue,
    verify_phase40_run_request,
)
from src.model_adaptation.phase40_evidence import verify_phase40_bundle
from src.model_adaptation.phase40_graphs import render_phase40_graphs
from src.model_adaptation.phase40_modes import AdaptationMode, RunKind
from src.model_adaptation.release_evaluation import evaluate_release_split
from src.model_adaptation.release_gates import write_release_artifacts, synthesize_release_verdict
from src.model_adaptation.registry import load_model_registry, save_model_registry
from src.model_adaptation.schemas import (
    ExplanationReviewPack,
    ModelRegistry,
    PilotSelection,
    ReleaseEvaluationSnapshot,
)
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


def _default_phase_five_snapshot_path() -> Path:
    return Path(".planning/phases/05-recall-priority-evaluation-and-release-gates/05-evaluation-snapshot.json")


def _default_phase_five_split_path() -> Path:
    settings = get_settings()
    repaired_holdout = settings.data_dir / "splits" / "recovered-balanced" / "val.jsonl"
    if repaired_holdout.exists():
        return repaired_holdout
    return _default_split_path("val")


def _default_phase_five_review_pack_path() -> Path:
    return Path(".planning/phases/05-recall-priority-evaluation-and-release-gates/05-explanation-review-pack.json")


def _default_phase_five_report_dir() -> Path:
    return Path(".planning/phases/05-recall-priority-evaluation-and-release-gates")


def _default_phase_five_manifest_dir() -> Path:
    return Path("data/manifests")


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


def _add_phase40_review_authority_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--request-path", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--scope-amendment-path", type=Path, required=True)
    parser.add_argument("--comparison-manifest-path", type=Path, required=True)
    parser.add_argument("--selected-predictions-path", type=Path, required=True)
    parser.add_argument("--queue-path", type=Path, required=True)


def _reject_duplicate_json_keys(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _load_jsonl_models_from_bytes(payload: bytes, path: Path, model_type):  # noqa: ANN001
    if not payload:
        raise ValueError(f"required JSONL input is missing or empty: {path}")
    try:
        text = payload.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ValueError(f"JSONL input is not strict UTF-8: {path}") from exc
    if not text.endswith("\n"):
        raise ValueError(f"JSONL input has a partial final record: {path}")
    rows = []
    for index, line in enumerate(text.splitlines()):
        if not line:
            raise ValueError(f"JSONL input contains an empty row: {path}")
        try:
            parsed = json.loads(line, object_pairs_hook=_reject_duplicate_json_keys)
            if not isinstance(parsed, dict):
                raise ValueError("JSONL row must be one object")
            rows.append(model_type.model_validate(parsed))
        except Exception as exc:
            raise ValueError(f"invalid JSONL row {index}: {path}") from exc
    return tuple(rows)


def _load_jsonl_models(path: Path, model_type):  # noqa: ANN001
    if not path.is_file():
        raise ValueError(f"required JSONL input is missing or empty: {path}")
    return _load_jsonl_models_from_bytes(path.read_bytes(), path, model_type)


def _parse_package_decision(value: str) -> PackageDecision:
    if "=" not in value:
        raise ValueError("package decision must use PACKAGE=approve or PACKAGE=reject:REASON")
    package, raw_decision = value.rsplit("=", 1)
    decision, reason_separator, reason = raw_decision.partition(":")
    return PackageDecision(
        package=package,
        decision=decision,
        reason=(reason if reason_separator else None),
    )


def _parse_returned_root(value: str) -> ReturnedBundleRoot:
    run_id, separator, path = value.partition("=")
    if not separator:
        raise ValueError("bundle root must use RUN_ID=REPOSITORY_PATH")
    return ReturnedBundleRoot(run_id=run_id, path=path)


def _parse_gpu_identity(value: str) -> ReturnedGpuIdentity:
    run_id, separator, accelerator = value.partition("=")
    if not separator:
        raise ValueError("GPU identity must use RUN_ID=GPU_NAME")
    return ReturnedGpuIdentity(run_id=run_id, accelerator=accelerator)


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
        default=None,
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
        required=True,
        help="Canonical data/splits/train.jsonl path",
    )
    train_parser.add_argument(
        "--val-split",
        type=Path,
        required=True,
        help="Canonical data/splits/val.jsonl path",
    )
    train_parser.add_argument(
        "--output-root",
        type=Path,
        default=None,
        help="Root directory for local model artifacts",
    )
    train_parser.add_argument(
        "--registry-path",
        type=Path,
        default=None,
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
        help="Exact checkpoint-N path with a verified compatibility manifest; 'latest' is forbidden",
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
        "--adaptation-mode",
        required=True,
        choices=[AdaptationMode.LORA.value, AdaptationMode.QLORA.value],
        help="Explicit adapter mode; QLoRA never falls back to LoRA",
    )
    train_parser.add_argument(
        "--run-kind",
        choices=[RunKind.PROBE.value, RunKind.FULL.value],
        default=RunKind.FULL.value,
        help="Bounded probe or full evidence-producing run",
    )
    train_parser.add_argument(
        "--post-warmup-steps",
        type=int,
        default=None,
        help="Required 30-50 post-warm-up optimizer steps for a probe run",
    )
    train_parser.add_argument(
        "--warmup-steps",
        type=int,
        default=5,
        help="Measured probe warm-up optimizer steps (default: 5)",
    )
    train_parser.add_argument(
        "--run-id",
        default=None,
        help="Safe immutable Phase 40 run identifier",
    )
    train_parser.add_argument(
        "--model-revision",
        default="cdbee75f17c01a7cc42f958dc650907174af0554",
        help="Pinned 40-hex base-model revision",
    )
    train_parser.add_argument(
        "--run-request-path",
        type=Path,
        default=None,
        help="Verified Phase 40 full-run request supplying transfer authority (required for full publication)",
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
        default=None,
        help="Root directory for local model artifacts",
    )
    convert_parser.add_argument(
        "--registry-path",
        type=Path,
        default=None,
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
        default=None,
        help="Training split JSONL path",
    )
    doctor_parser.add_argument(
        "--val-split",
        type=Path,
        default=None,
        help="Validation split JSONL path",
    )
    doctor_parser.add_argument(
        "--output-root",
        type=Path,
        default=None,
        help="Root directory for local model artifacts",
    )
    doctor_parser.add_argument(
        "--registry-path",
        type=Path,
        default=None,
        help="Path to the local model registry JSON",
    )
    doctor_parser.set_defaults(handler=handle_doctor)

    evaluate_release_parser = subparsers.add_parser(
        "evaluate-release-split",
        help="Run the Phase 5 held-out evaluation and save the snapshot as it progresses",
    )
    evaluate_release_parser.add_argument(
        "--split-path",
        type=Path,
        default=None,
        help="Held-out split JSONL path to evaluate",
    )
    evaluate_release_parser.add_argument(
        "--snapshot-path",
        type=Path,
        default=_default_phase_five_snapshot_path(),
        help="Output path for the saved evaluation snapshot",
    )
    evaluate_release_parser.add_argument(
        "--run-id",
        default=None,
        help="Optional stable run id recorded in the snapshot",
    )
    evaluate_release_parser.add_argument(
        "--progress-every",
        type=int,
        default=1,
        help="Print progress every N evaluated rows; use 0 to disable progress output",
    )
    evaluate_release_parser.add_argument(
        "--checkpoint-every",
        type=int,
        default=1,
        help="Rewrite the snapshot every N evaluated rows; use 0 to disable intermediate checkpoints",
    )
    evaluate_release_parser.set_defaults(handler=handle_evaluate_release_split)

    review_parser = subparsers.add_parser(
        "prepare-explanation-review",
        help="Build the risky-only Phase 5 explanation review pack from a saved evaluation snapshot",
    )
    review_parser.add_argument(
        "--snapshot-path",
        type=Path,
        default=_default_phase_five_snapshot_path(),
        help="Saved evaluation snapshot JSON path",
    )
    review_parser.add_argument(
        "--output-path",
        type=Path,
        default=_default_phase_five_review_pack_path(),
        help="Output path for the phase-local explanation review pack",
    )
    review_parser.add_argument(
        "--sample-size",
        type=int,
        default=None,
        help="Optional cap for deterministic risky-row sampling",
    )
    review_parser.set_defaults(handler=handle_prepare_explanation_review)

    release_eval_parser = subparsers.add_parser(
        "release-eval",
        help="Synthesize the final Phase 5 release verdict from the saved snapshot and completed review pack",
    )
    release_eval_parser.add_argument(
        "--snapshot-path",
        type=Path,
        default=_default_phase_five_snapshot_path(),
        help="Saved evaluation snapshot JSON path",
    )
    release_eval_parser.add_argument(
        "--review-pack-path",
        type=Path,
        default=_default_phase_five_review_pack_path(),
        help="Completed explanation review pack JSON path",
    )
    release_eval_parser.add_argument(
        "--report-dir",
        type=Path,
        default=_default_phase_five_report_dir(),
        help="Output directory for the phase-local markdown report",
    )
    release_eval_parser.add_argument(
        "--manifest-dir",
        type=Path,
        default=_default_phase_five_manifest_dir(),
        help="Output directory for the machine-readable release artifact",
    )
    release_eval_parser.set_defaults(handler=handle_release_eval)

    phase40_preflight_parser = subparsers.add_parser(
        "phase40-preflight",
        help="Authorize the canonical Phase 40 train and validation snapshots",
    )
    doctor_parser.add_argument(
        "--adaptation-mode",
        required=True,
        choices=[AdaptationMode.LORA.value, AdaptationMode.QLORA.value],
        help="Mode whose readiness must be checked without fallback",
    )
    phase40_preflight_parser.add_argument(
        "--train-split",
        type=Path,
        required=True,
        help="Canonical data/splits/train.jsonl path",
    )
    phase40_preflight_parser.add_argument(
        "--val-split",
        type=Path,
        required=True,
        help="Canonical data/splits/val.jsonl path",
    )
    phase40_preflight_parser.set_defaults(handler=handle_phase40_preflight)

    phase40_source_parser = subparsers.add_parser(
        "phase40-build-source-bundle",
        help="Build the deterministic allowlisted Phase 40 source transfer bundle",
    )
    phase40_source_parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    phase40_source_parser.add_argument("--output-root", type=Path, required=True)
    phase40_source_parser.set_defaults(handler=handle_phase40_build_source_bundle)

    phase40_input_parser = subparsers.add_parser(
        "phase40-build-input-bundle",
        help="Build the deterministic canonical train/validation-only transfer bundle",
    )
    phase40_input_parser.add_argument("--train-split", type=Path, required=True)
    phase40_input_parser.add_argument("--val-split", type=Path, required=True)
    phase40_input_parser.add_argument("--output-path", type=Path, required=True)
    phase40_input_parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    phase40_input_parser.add_argument("--reference-output", type=Path, default=None)
    phase40_input_parser.set_defaults(handler=handle_phase40_build_input_bundle)

    phase40_verify_input_parser = subparsers.add_parser(
        "phase40-verify-input-bundle",
        help="Verify a request-bound input archive before opening its data members",
    )
    phase40_verify_input_parser.add_argument("--archive-path", type=Path, required=True)
    phase40_verify_input_parser.add_argument("--reference-path", type=Path, required=True)
    phase40_verify_input_parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    phase40_verify_input_parser.add_argument("--extraction-root", type=Path, default=None)
    phase40_verify_input_parser.add_argument("--verify-only", action="store_true")
    phase40_verify_input_parser.set_defaults(handler=handle_phase40_verify_input_bundle)

    phase40_request_parser = subparsers.add_parser(
        "phase40-verify-run-request",
        help="Verify the immutable Phase 40 source and train/validation transfer authorities",
    )
    phase40_request_parser.add_argument("--request-path", type=Path, required=True)
    phase40_request_parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    phase40_request_parser.set_defaults(handler=handle_phase40_verify_run_request)

    phase40_evidence_parser = subparsers.add_parser(
        "phase40-verify-run-evidence",
        help="Rehash and verify one complete Phase 40 run-evidence bundle",
    )
    phase40_evidence_parser.add_argument("--run-root", type=Path, required=True)
    phase40_evidence_parser.add_argument(
        "--allow-prestart-failure",
        action="store_true",
        help="Explicitly accept a hash-verified pre-start failure record",
    )
    phase40_evidence_parser.set_defaults(handler=handle_phase40_verify_run_evidence)

    phase40_graph_parser = subparsers.add_parser(
        "phase40-render-graphs",
        help="Rebuild Phase 40 loss graphs from retained raw events and metrics",
    )
    phase40_graph_parser.add_argument("--run-root", type=Path, required=True)
    phase40_graph_parser.add_argument("--smoothing-window", type=int, default=None)
    phase40_graph_parser.add_argument("--dpi", type=int, default=120)
    phase40_graph_parser.set_defaults(handler=handle_phase40_render_graphs)

    phase40_notebook_parser = subparsers.add_parser(
        "phase40-validate-notebooks",
        help="Statically validate the three canonical Phase 40 notebook controllers",
    )
    phase40_notebook_parser.add_argument("--root", type=Path, required=True)
    phase40_notebook_parser.set_defaults(handler=handle_phase40_validate_notebooks)

    phase40_comparison_parser = subparsers.add_parser(
        "phase40-finalize-comparison",
        help="Reverify local QLoRA/PhoBERT plus the resource-only LoRA probe",
    )
    phase40_comparison_parser.add_argument("--request-path", type=Path, required=True)
    phase40_comparison_parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    phase40_comparison_parser.add_argument("--output-root", type=Path, required=True)
    phase40_comparison_parser.add_argument(
        "--scope-amendment-path", type=Path, required=True
    )
    phase40_comparison_parser.add_argument(
        "--package-decision",
        action="append",
        default=[],
        metavar="PACKAGE=approve|reject:REASON",
    )
    phase40_comparison_parser.add_argument(
        "--bundle-root", action="append", default=[], metavar="RUN_ID=REPOSITORY_PATH"
    )
    phase40_comparison_parser.add_argument(
        "--gpu-identity", action="append", default=[], metavar="RUN_ID=GPU_NAME"
    )
    phase40_comparison_parser.add_argument("--verify-only", action="store_true")
    phase40_comparison_parser.set_defaults(handler=handle_phase40_finalize_comparison)

    phase40_scope_parser = subparsers.add_parser(
        "phase40-freeze-scope-amendment",
        help="Freeze the request-bound local two-full-model scope waiver",
    )
    phase40_scope_parser.add_argument("--request-path", type=Path, required=True)
    phase40_scope_parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    phase40_scope_parser.set_defaults(handler=handle_phase40_freeze_scope_amendment)

    phase40_queue_parser = subparsers.add_parser(
        "phase40-verify-review-queue",
        help="Re-derive a frozen review queue from comparison/input authorities",
    )
    _add_phase40_review_authority_arguments(phase40_queue_parser)
    phase40_queue_parser.set_defaults(handler=handle_phase40_verify_review_queue)

    phase40_human_parser = subparsers.add_parser(
        "phase40-finalize-human-review",
        help="Freeze exact-coverage Vietnamese review notes without changing predictions",
    )
    _add_phase40_review_authority_arguments(phase40_human_parser)
    phase40_human_parser.add_argument("--queue-manifest-path", type=Path, required=True)
    phase40_human_parser.add_argument("--reviewer-return-path", type=Path, required=True)
    phase40_human_parser.add_argument("--output-root", type=Path, required=True)
    phase40_human_parser.add_argument(
        "--vietnamese-fluent-attestation", action="store_true", required=True
    )
    phase40_human_parser.add_argument("--verify-only", action="store_true")
    phase40_human_parser.set_defaults(handler=handle_phase40_finalize_human_review)

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
    registry_path = args.registry_path or _default_registry_path()
    save_model_registry(registry, registry_path)
    print(
        f"Pilot dry-run complete: baseline={selection.baseline_winner_id} "
        f"runner-up={selection.runner_up_id} registry={registry_path}"
    )
    return 0


def handle_train(args: argparse.Namespace) -> int:
    """Run the dry-run training scaffold for the selected candidate alias."""

    data_contract = preflight_phase40_inputs(
        args.train_split,
        args.val_split,
        repo_root=Path.cwd(),
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


def handle_evaluate_release_split(args: argparse.Namespace) -> int:
    """Evaluate one held-out split through the runtime and save a Phase 5 snapshot."""

    progress_every = args.progress_every if args.progress_every > 0 else None
    checkpoint_every = args.checkpoint_every if args.checkpoint_every > 0 else None

    def _emit_progress(current: int, total: int) -> None:
        if progress_every is None:
            return
        if current == 1 or current == total or current % progress_every == 0:
            print(f"Phase 5 evaluation progress: {current}/{total}")

    split_path = args.split_path or _default_phase_five_split_path()
    snapshot = evaluate_release_split(
        split_path,
        snapshot_path=args.snapshot_path,
        run_id=args.run_id,
        progress_callback=_emit_progress if progress_every is not None else None,
        checkpoint_interval=checkpoint_every,
    )
    print(
        f"Evaluation snapshot ready: rows={snapshot.overall_metrics.evaluated_rows} "
        f"verdict={snapshot.audit.verdict} snapshot={args.snapshot_path}"
    )
    return 0


def handle_prepare_explanation_review(args: argparse.Namespace) -> int:
    """Generate the pre-verdict risky-only explanation review pack for Phase 5."""

    snapshot = ReleaseEvaluationSnapshot.model_validate_json(args.snapshot_path.read_text(encoding="utf-8"))
    pack = build_manual_review_pack(
        snapshot,
        snapshot_path=args.snapshot_path,
        sample_size=args.sample_size,
    )
    args.output_path.parent.mkdir(parents=True, exist_ok=True)
    args.output_path.write_text(pack.model_dump_json(indent=2), encoding="utf-8")
    print(f"Explanation review pack ready: {args.output_path}")
    return 0


def handle_release_eval(args: argparse.Namespace) -> int:
    """Run the final Phase 5 release verdict synthesis and artifact writing flow."""

    snapshot = ReleaseEvaluationSnapshot.model_validate_json(args.snapshot_path.read_text(encoding="utf-8"))
    review_pack = ExplanationReviewPack.model_validate_json(args.review_pack_path.read_text(encoding="utf-8"))
    artifact = synthesize_release_verdict(snapshot, review_pack)
    report_path, manifest_path = write_release_artifacts(
        artifact,
        report_dir=args.report_dir,
        manifest_dir=args.manifest_dir,
    )
    print(
        f"Release eval complete: verdict={artifact.verdict} "
        f"report={report_path} manifest={manifest_path}"
    )
    return 0


def handle_phase40_preflight(args: argparse.Namespace) -> int:
    """Validate only the canonical train/validation inputs and print identities."""

    contract = preflight_phase40_inputs(
        args.train_split,
        args.val_split,
        repo_root=Path.cwd(),
    )
    for identity in contract.ordered_identities:
        print(
            f"{identity.split_name}: records={identity.records} bytes={identity.bytes} "
            f"sha256={identity.sha256}"
        )
    return 0


def handle_phase40_build_source_bundle(args: argparse.Namespace) -> int:
    """Build and print the exact deterministic source transfer identity."""

    built = build_phase40_source_bundle(args.repo_root, args.output_root)
    print(built.reference.model_dump_json())
    return 0


def handle_phase40_build_input_bundle(args: argparse.Namespace) -> int:
    """Build an exact-byte train/validation archive from canonical preflight."""

    contract = preflight_phase40_inputs(
        args.train_split,
        args.val_split,
        repo_root=args.repo_root,
    )
    built = build_phase40_input_bundle(
        contract, args.output_path, repo_root=args.repo_root
    )
    reference_bytes = (built.reference.model_dump_json(indent=2) + "\n").encode("utf-8")
    if args.reference_output is not None:
        args.reference_output.parent.mkdir(parents=True, exist_ok=True)
        args.reference_output.write_bytes(reference_bytes)
    print(built.reference.model_dump_json())
    return 0


def handle_phase40_verify_input_bundle(args: argparse.Namespace) -> int:
    """Verify a typed input reference and optionally materialize fixed outputs."""

    reference = InputBundleReference.model_validate_json(
        args.reference_path.read_text(encoding="utf-8")
    )
    contract = verify_phase40_input_bundle(
        args.archive_path,
        reference,
        repo_root=args.repo_root,
        extraction_root=args.extraction_root,
        materialize=not args.verify_only,
    )
    print(
        f"Phase 40 input bundle verified: train={len(contract.train_snapshot.rows)} "
        f"val={len(contract.validation_snapshot.rows)} archive={args.archive_path}"
    )
    return 0


def handle_phase40_verify_run_request(args: argparse.Namespace) -> int:
    """Verify a frozen run request and both of its transfer authorities."""

    request = RunRequest.model_validate_json(args.request_path.read_text(encoding="utf-8"))
    verify_phase40_run_request(request, repo_root=args.repo_root)
    print(f"Phase 40 run request verified: {args.request_path}")
    return 0


def handle_phase40_verify_run_evidence(args: argparse.Namespace) -> int:
    evidence = verify_phase40_bundle(
        args.run_root,
        allow_prestart_failure=args.allow_prestart_failure,
    )
    print(
        f"Phase 40 run evidence verified: run_id={evidence.run_id} "
        f"status={evidence.status.value} root={args.run_root}"
    )
    return 0


def handle_phase40_render_graphs(args: argparse.Namespace) -> int:
    provenance = render_phase40_graphs(
        args.run_root,
        smoothing_window=args.smoothing_window,
        dpi=args.dpi,
    )
    print(
        f"Phase 40 graph regenerated: graph={provenance.graph_id} "
        f"output={provenance.output.relative_path}"
    )
    return 0


def handle_phase40_freeze_scope_amendment(args: argparse.Namespace) -> int:
    request = load_frozen_phase40_run_request(
        repo_root=args.repo_root,
        request_path=args.request_path,
    )
    path = freeze_phase40_scope_amendment(
        request,
        repo_root=args.repo_root,
    )
    display_path = path.relative_to(Path(args.repo_root).resolve(strict=True)).as_posix()
    print(f"Phase 40 two-model scope amendment frozen: {display_path}")
    return 0


def handle_phase40_finalize_comparison(args: argparse.Namespace) -> int:
    request = load_frozen_phase40_run_request(
        repo_root=args.repo_root,
        request_path=args.request_path,
    )
    operator_return = LocalTwoModelOperatorReturn(
        package_decisions=tuple(
            _parse_package_decision(value) for value in args.package_decision
        ),
        bundle_roots=tuple(_parse_returned_root(value) for value in args.bundle_root),
        gpu_identities=tuple(
            _parse_gpu_identity(value) for value in args.gpu_identity
        ),
    )
    artifacts = finalize_phase40_comparison(
        request,
        operator_return,
        repo_root=args.repo_root,
        scope_amendment_path=args.scope_amendment_path,
        output_root=args.output_root,
        verify_only=args.verify_only,
    )
    print(
        f"Phase 40 comparison {artifacts.manifest.status}: "
        f"manifest={artifacts.manifest_path} report={artifacts.report_path}"
    )
    return 0


def _load_phase40_review_authorities(args: argparse.Namespace):  # noqa: ANN201
    request = load_frozen_phase40_run_request(
        repo_root=args.repo_root,
        request_path=args.request_path,
    )
    contract = verify_phase40_input_bundle(
        Path(args.repo_root) / request.input_bundle.repository_relative_path,
        request.input_bundle,
        repo_root=args.repo_root,
        materialize=False,
    )
    comparison = Phase40ComparisonManifest.model_validate_json(
        args.comparison_manifest_path.read_text(encoding="utf-8", errors="strict")
    )
    amendment = load_frozen_phase40_scope_amendment(
        request=request,
        repo_root=args.repo_root,
        amendment_path=args.scope_amendment_path,
    )
    if (
        hashlib.sha256(args.scope_amendment_path.read_bytes()).hexdigest()
        != comparison.scope_amendment_sha256
        or amendment.original_run_request_sha256
        != comparison.original_run_request_sha256
    ):
        raise ValueError("comparison manifest differs from the frozen scope amendment")
    bundles = load_phase40_selected_prediction_bundles(
        args.selected_predictions_path,
        comparison_manifest=comparison,
    )
    try:
        queue_bytes = args.queue_path.read_bytes()
    except OSError as exc:
        raise ValueError(
            f"required JSONL input is missing or unreadable: {args.queue_path}"
        ) from exc
    queue = _load_jsonl_models_from_bytes(
        queue_bytes,
        args.queue_path,
        ReviewQueueRow,
    )
    verify_phase40_review_queue(
        queue,
        contract=contract,
        prediction_bundles=bundles,
    )
    return request, contract, comparison, bundles, queue, queue_bytes


def handle_phase40_verify_review_queue(args: argparse.Namespace) -> int:
    _, _, comparison, _, queue, queue_bytes = _load_phase40_review_authorities(args)
    if comparison.review_queue_sha256 is None:
        raise ValueError("comparison manifest has no review-queue identity")
    if hashlib.sha256(queue_bytes).hexdigest() != comparison.review_queue_sha256:
        raise ValueError("review queue file hash differs from the comparison manifest")
    print(f"Phase 40 review queue verified: rows={len(queue)} path={args.queue_path}")
    return 0


def handle_phase40_finalize_human_review(args: argparse.Namespace) -> int:
    request, contract, _, bundles, queue, queue_bytes = (
        _load_phase40_review_authorities(args)
    )
    reviewer_return_bytes = args.reviewer_return_path.read_bytes()
    reviews = _load_jsonl_models_from_bytes(
        reviewer_return_bytes,
        args.reviewer_return_path,
        ReviewerReturnRow,
    )
    artifacts = finalize_phase40_human_review(
        queue,
        reviews,
        request=request,
        repo_root=args.repo_root,
        contract=contract,
        prediction_bundles=bundles,
        queue_manifest_path=args.queue_manifest_path,
        comparison_manifest_path=args.comparison_manifest_path,
        scope_amendment_path=args.scope_amendment_path,
        output_root=args.output_root,
        queue_bytes=queue_bytes,
        reviewer_return_bytes=reviewer_return_bytes,
        vietnamese_fluent_attestation=args.vietnamese_fluent_attestation,
        verify_only=args.verify_only,
    )
    print(
        f"Phase 40 human review finalized: notes={artifacts.notes_path} "
        f"report={artifacts.report_path}"
    )
    return 0


def handle_phase40_validate_notebooks(args: argparse.Namespace) -> int:
    """Compatibility entrypoint for the Plan 40-03 documented verification command."""

    from src.model_adaptation.phase40_notebooks import validate_phase40_notebooks

    issues = tuple(validate_phase40_notebooks(args.root))
    if issues:
        for issue in issues:
            print(str(issue))
        return 1
    print(f"Phase 40 notebooks validated: root={args.root} count=3")
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for the Phase 3 and Phase 5 operator tooling."""

    parser = build_parser()
    args = parser.parse_args(argv)
    args._phase40_raw_argv = tuple(sys.argv[1:] if argv is None else argv)
    try:
        return args.handler(args)
    except (RuntimeError, ValueError, FileNotFoundError) as exc:
        print(str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
