"""Operator-facing CLI for model adaptation and the Phase 41 one-shot authority."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

from src.model_adaptation.commands import adaptation
from src.model_adaptation.commands.router import dispatch


def _print_console_safe(message: object, *, stream=None) -> None:
    """Write one line without letting a legacy console change command success."""

    target = sys.stdout if stream is None else stream
    text = f"{message}\n"
    encoding = getattr(target, "encoding", None) or "utf-8"
    try:
        safe_text = text.encode(encoding, errors="backslashreplace").decode(encoding)
    except LookupError:
        safe_text = text.encode("ascii", errors="backslashreplace").decode("ascii")
    try:
        target.write(safe_text)
    except UnicodeEncodeError:
        target.write(text.encode("ascii", errors="backslashreplace").decode("ascii"))
    flush = getattr(target, "flush", None)
    if callable(flush):
        flush()


def _default_split_root() -> Path:
    return adaptation._default_split_root()


def _default_split_path(split_name: str) -> Path:
    return adaptation._default_split_path(split_name)


def _default_registry_path() -> Path:
    return adaptation._default_registry_path()


def _default_phase_five_split_path() -> Path:
    return adaptation._default_phase_five_split_path()


def _build_dry_run_pilot_rows() -> list[dict[str, object]]:
    return adaptation._build_dry_run_pilot_rows()


def _load_selection(registry_path: Path):  # noqa: ANN202
    return adaptation._load_selection(registry_path)


def _resolve_candidate_alias(candidate_arg: str, selection):  # noqa: ANN001, ANN201
    return adaptation._resolve_candidate_alias(candidate_arg, selection)


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


def _load_jsonl_models_from_bytes(  # noqa: ANN001
    payload: bytes,
    path: Path,
    model_type,
    *,
    description: str | None = None,
):
    display = description if description is not None else os.fspath(path)
    if not payload:
        raise ValueError(f"required JSONL input is missing or empty: {display}")
    try:
        text = payload.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ValueError(f"JSONL input is not strict UTF-8: {display}") from exc
    if not text.endswith("\n"):
        raise ValueError(f"JSONL input has a partial final record: {display}")
    rows = []
    for index, line in enumerate(text.splitlines()):
        if not line:
            raise ValueError(f"JSONL input contains an empty row: {display}")
        try:
            parsed = json.loads(line, object_pairs_hook=_reject_duplicate_json_keys)
            if not isinstance(parsed, dict):
                raise ValueError("JSONL row must be one object")
            rows.append(model_type.model_validate(parsed))
        except Exception as exc:
            raise ValueError(f"invalid JSONL row {index}: {display}") from exc
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

    adaptation.register_commands(
        subparsers,
        pilot=handle_pilot,
        train=handle_train,
        convert=handle_convert,
        doctor=handle_doctor,
    )

    phase40_preflight_parser = subparsers.add_parser(
        "phase40-preflight",
        help="Authorize the canonical Phase 40 train and validation snapshots",
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

    phase41_prepare_parser = subparsers.add_parser(
        "phase41-prepare-evaluation",
        help="Freeze the code-fixed Phase 41 preauthorization without opening the holdout",
    )
    phase41_prepare_parser.add_argument(
        "--output-root", type=Path, default=None,
        help="Fixed ProgramData operational root (default; overrides must match it)",
    )
    phase41_prepare_parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    phase41_prepare_parser.add_argument(
        "--phase39-contract-path", type=Path, required=True
    )
    phase41_prepare_parser.add_argument(
        "--phase40-comparison-manifest-path", type=Path, required=True
    )
    phase41_prepare_parser.add_argument(
        "--phase40-review-manifest-path", type=Path, required=True
    )
    phase41_prepare_parser.add_argument(
        "--preclaim-rejection-audit-path",
        type=Path,
        default=Path(
            "data/models/phase41/preclaim-audit/"
            "41-02-preclaim-failure.json"
        ),
    )
    phase41_prepare_parser.add_argument(
        "--staged-preclaim-failure-audit-path",
        type=Path,
        default=Path(
            "data/models/phase41/failed-invocation/"
            "44c654a9bc92151a00231fcbf9e73209ab9e0802239ffbd0597efa4d8f353401/"
            "claim-capable-preclaim-failure.json"
        ),
    )
    phase41_prepare_parser.add_argument(
        "--argument-preclaim-failure-audit-path",
        type=Path,
        default=Path(
            "data/models/phase41/failed-invocation/"
            "0cdd803d0f145b147e34c5a8b0a9b1846496192bf6b002a46c3dbccaaf2e9c22/"
            "claim-capable-preclaim-failure.json"
        ),
    )
    phase41_prepare_parser.add_argument(
        "--autonomous-reseal-delegation-path",
        type=Path,
        default=Path("data/models/phase41/autonomous-reseal-delegation.json"),
    )
    phase41_prepare_parser.add_argument(
        "--captured-helper-preclaim-failure-audit-path",
        type=Path,
        default=Path(
            "data/models/phase41/failed-invocation/"
            "28374ea5c1f7fee43e12ee0395ad4fcd7c6a2e4801b809131afa6cca2db7e8e7/"
            "claim-capable-preclaim-failure.json"
        ),
    )
    phase41_prepare_parser.set_defaults(handler=handle_phase41_prepare_evaluation)

    phase41_verify_pre_parser = subparsers.add_parser(
        "phase41-verify-preauthorization",
        help="Verify frozen Phase 41 preauthorization without loading models or data",
    )
    phase41_verify_pre_parser.add_argument(
        "--output-root", type=Path, default=None,
        help="Fixed ProgramData operational root (default)",
    )
    phase41_verify_pre_parser.set_defaults(
        handler=handle_phase41_verify_preauthorization
    )

    phase41_authorize_parser = subparsers.add_parser(
        "phase41-authorize-evaluation",
        help="Record the exact explicit one-shot authorization",
    )
    phase41_authorize_parser.add_argument(
        "--output-root", type=Path, default=None,
        help="Fixed ProgramData operational root (default)",
    )
    phase41_authorize_parser.add_argument("--prepared-sha256", required=True)
    phase41_authorize_parser.add_argument(
        "--statement",
        required=True,
        help="Exact Phase 41 checkpoint signal; extra text is rejected",
    )
    phase41_authorize_parser.set_defaults(handler=handle_phase41_authorize_evaluation)

    phase41_run_parser = subparsers.add_parser(
        "phase41-run-once",
        help="Run the sole canonical two-model reserved evaluation",
    )
    phase41_run_parser.add_argument(
        "--output-root", type=Path, default=None,
        help="Fixed ProgramData operational root (default)",
    )
    phase41_run_parser.set_defaults(handler=handle_phase41_run_once)

    phase41_disposition_parser = subparsers.add_parser(
        "phase41-freeze-deployment-fit-disposition",
        help="Freeze the precommitted post-evaluation deployment-fit choice",
    )
    phase41_disposition_parser.add_argument(
        "--output-root", type=Path, default=None,
        help="Fixed ProgramData operational root (default)",
    )
    phase41_disposition_parser.set_defaults(
        handler=handle_phase41_freeze_deployment_fit_disposition
    )

    phase41_export_parser = subparsers.add_parser(
        "phase41-export-evidence",
        help="Mirror verified ProgramData evidence into an immutable repo export",
    )
    phase41_export_parser.add_argument(
        "--output-root", type=Path, default=None,
        help="Fixed ProgramData operational root (default)",
    )
    phase41_export_parser.add_argument(
        "--repository-output-root",
        type=Path,
        default=Path("data/models/phase41"),
    )
    phase41_export_parser.set_defaults(handler=handle_phase41_export_evidence)

    phase41_verify_parser = subparsers.add_parser(
        "phase41-verify-evidence",
        help="Verify terminal evidence without an opener, split, predictor, or model",
    )
    phase41_verify_parser.add_argument(
        "--output-root", type=Path, default=None,
        help="Fixed ProgramData operational root (default)",
    )
    phase41_verify_parser.set_defaults(handler=handle_phase41_verify_evidence)

    return parser


def _legacy_handle_pilot(args: argparse.Namespace) -> int:
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


def _legacy_handle_train(args: argparse.Namespace) -> int:
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


def _legacy_handle_convert(args: argparse.Namespace) -> int:
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


def _legacy_handle_doctor(args: argparse.Namespace) -> int:
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


def handle_pilot(args: argparse.Namespace) -> int:
    return dispatch("pilot", args)


def handle_train(args: argparse.Namespace) -> int:
    return dispatch("train", args)


def handle_convert(args: argparse.Namespace) -> int:
    return dispatch("convert", args)


def handle_doctor(args: argparse.Namespace) -> int:
    return dispatch("doctor", args)


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
    comparison, _ = load_canonical_phase40_comparison_manifest(
        repo_root=args.repo_root,
        comparison_manifest_path=args.comparison_manifest_path,
    )
    if comparison.schema_version == "phase40-comparison-v3":
        final, scope_amendment_bytes = load_phase40_review_authority(
            repo_root=args.repo_root,
            request=request,
            scope_amendment_path=args.scope_amendment_path,
        )
        verify_phase40_final_review_comparison(
            comparison,
            final_authority=final,
            scope_amendment_bytes=scope_amendment_bytes,
        )
    else:
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
            raise ValueError(
                "comparison manifest differs from the frozen scope amendment"
            )
    selected_path, selected_bytes = read_canonical_phase40_review_regular_bytes(
        repo_root=args.repo_root,
        supplied_path=args.selected_predictions_path,
        expected_relative=FIXED_SELECTED_PREDICTIONS_PATH,
        description="selected prediction bundles",
    )
    bundles = load_phase40_selected_prediction_bundles(
        selected_path,
        comparison_manifest=comparison,
    )
    _, selected_bytes_after = read_canonical_phase40_review_regular_bytes(
        repo_root=args.repo_root,
        supplied_path=selected_path,
        expected_relative=FIXED_SELECTED_PREDICTIONS_PATH,
        description="selected prediction bundles",
    )
    if selected_bytes_after != selected_bytes:
        raise ValueError("selected prediction bundles changed while loading")
    queue_path, queue_bytes = read_canonical_phase40_review_regular_bytes(
        repo_root=args.repo_root,
        supplied_path=args.queue_path,
        expected_relative=FIXED_REVIEW_QUEUE_PATH,
        description="review queue",
    )
    queue = _load_jsonl_models_from_bytes(
        queue_bytes,
        queue_path,
        ReviewQueueRow,
        description="review queue",
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
    reviewer_return_path, reviewer_return_bytes = (
        read_canonical_phase40_review_regular_bytes(
            repo_root=args.repo_root,
            supplied_path=args.reviewer_return_path,
            expected_relative=FIXED_REVIEWER_RETURN_PATH,
            description="reviewer return",
        )
    )
    reviews = _load_jsonl_models_from_bytes(
        reviewer_return_bytes,
        reviewer_return_path,
        ReviewerReturnRow,
        description="reviewer return",
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
        "Phase 40 human review finalized: "
        "notes=data/models/phase40/review/human-review-notes.jsonl "
        "report=data/models/phase40/review/human-review-report.md"
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


def _phase41_output_root(value: Path | None) -> Path:
    from src.model_adaptation.phase41_evaluation import phase41_operational_root

    return value if value is not None else phase41_operational_root()


def handle_phase41_prepare_evaluation(args: argparse.Namespace) -> int:
    """Freeze authorities from code-fixed Phase 39/40 handoff locations."""

    from src.model_adaptation.phase41_evaluation import (
        prepare_phase41_from_canonical_authorities,
    )

    prepared = prepare_phase41_from_canonical_authorities(
        _phase41_output_root(args.output_root),
        repo_root=args.repo_root,
        phase39_contract_path=args.phase39_contract_path,
        phase40_comparison_manifest_path=args.phase40_comparison_manifest_path,
        phase40_review_manifest_path=args.phase40_review_manifest_path,
        preclaim_rejection_audit_path=getattr(
            args,
            "preclaim_rejection_audit_path",
            Path(
                "data/models/phase41/preclaim-audit/"
                "41-02-preclaim-failure.json"
            ),
        ),
        staged_preclaim_failure_audit_path=getattr(
            args,
            "staged_preclaim_failure_audit_path",
            Path(
                "data/models/phase41/failed-invocation/"
                "44c654a9bc92151a00231fcbf9e73209ab9e0802239ffbd0597efa4d8f353401/"
                "claim-capable-preclaim-failure.json"
            ),
        ),
        argument_preclaim_failure_audit_path=getattr(
            args,
            "argument_preclaim_failure_audit_path",
            Path(
                "data/models/phase41/failed-invocation/"
                "0cdd803d0f145b147e34c5a8b0a9b1846496192bf6b002a46c3dbccaaf2e9c22/"
                "claim-capable-preclaim-failure.json"
            ),
        ),
        autonomous_reseal_delegation_path=getattr(
            args,
            "autonomous_reseal_delegation_path",
            Path("data/models/phase41/autonomous-reseal-delegation.json"),
        ),
        captured_helper_preclaim_failure_audit_path=getattr(
            args,
            "captured_helper_preclaim_failure_audit_path",
            Path(
                "data/models/phase41/failed-invocation/"
                "28374ea5c1f7fee43e12ee0395ad4fcd7c6a2e4801b809131afa6cca2db7e8e7/"
                "claim-capable-preclaim-failure.json"
            ),
        ),
    )
    print(
        f"Phase 41 prepared: request={prepared.path} "
        f"sha256={prepared.prepared_sha256}"
    )
    return 0


def handle_phase41_verify_preauthorization(args: argparse.Namespace) -> int:
    from src.model_adaptation.phase41_evaluation import (
        verify_phase41_preauthorization,
    )

    prepared = verify_phase41_preauthorization(_phase41_output_root(args.output_root))
    print(f"Phase 41 preauthorization verified: sha256={prepared.prepared_sha256}")
    return 0


def handle_phase41_authorize_evaluation(args: argparse.Namespace) -> int:
    from src.model_adaptation.phase41_evaluation import (
        authorize_phase41_evaluation,
    )

    path = authorize_phase41_evaluation(
        _phase41_output_root(args.output_root),
        prepared_sha256=args.prepared_sha256,
        statement=args.statement,
    )
    print(f"Phase 41 explicitly authorized: {path}")
    return 0


def handle_phase41_run_once(args: argparse.Namespace) -> int:
    from src.model_adaptation.phase41_evaluation import run_phase41_once

    manifest = run_phase41_once(_phase41_output_root(args.output_root))
    print(f"Phase 41 completed: evidence={manifest.path}")
    return 0


def handle_phase41_freeze_deployment_fit_disposition(args: argparse.Namespace) -> int:
    from src.model_adaptation.phase41_evaluation import (
        freeze_deployment_fit_disposition,
    )

    path = freeze_deployment_fit_disposition(_phase41_output_root(args.output_root))
    print(f"Phase 41 deployment-fit disposition frozen: {path}")
    return 0


def handle_phase41_export_evidence(args: argparse.Namespace) -> int:
    from src.model_adaptation.phase41_evaluation import (
        export_phase41_evidence_to_repository,
    )

    path = export_phase41_evidence_to_repository(
        _phase41_output_root(args.output_root),
        repository_output_root=args.repository_output_root,
    )
    _print_console_safe(f"Phase 41 verified evidence exported: {path}")
    return 0


def handle_phase41_verify_evidence(args: argparse.Namespace) -> int:
    from src.model_adaptation.phase41_evaluation import verify_phase41_evidence

    manifest = verify_phase41_evidence(_phase41_output_root(args.output_root))
    print(
        f"Phase 41 evidence verified: manifest={manifest.path} "
        f"sha256={manifest.evidence_manifest_sha256}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for the model-adaptation operator tooling."""

    parser = build_parser()
    args = parser.parse_args(argv)
    args._phase40_raw_argv = tuple(sys.argv[1:] if argv is None else argv)
    try:
        return args.handler(args)
    except (RuntimeError, ValueError, FileNotFoundError) as exc:
        _print_console_safe(str(exc), stream=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
