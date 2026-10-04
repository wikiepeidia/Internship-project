"""Phase 40 compatibility command family with handler-local dependencies."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Callable


Handler = Callable[[argparse.Namespace], int]


def _add_review_authority_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--request-path", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--scope-amendment-path", type=Path, required=True)
    parser.add_argument("--comparison-manifest-path", type=Path, required=True)
    parser.add_argument("--selected-predictions-path", type=Path, required=True)
    parser.add_argument("--queue-path", type=Path, required=True)


def _register_transfer_commands(
    subparsers: argparse._SubParsersAction,
    handlers: dict[str, Handler],
) -> None:
    parser = subparsers.add_parser(
        "phase40-preflight",
        help="Authorize the canonical Phase 40 train and validation snapshots",
    )
    parser.add_argument(
        "--train-split",
        type=Path,
        required=True,
        help="Canonical data/splits/train.jsonl path",
    )
    parser.add_argument(
        "--val-split",
        type=Path,
        required=True,
        help="Canonical data/splits/val.jsonl path",
    )
    parser.set_defaults(handler=handlers["phase40-preflight"])

    parser = subparsers.add_parser(
        "phase40-build-source-bundle",
        help="Build the deterministic allowlisted Phase 40 source transfer bundle",
    )
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--output-root", type=Path, required=True)
    parser.set_defaults(handler=handlers["phase40-build-source-bundle"])

    parser = subparsers.add_parser(
        "phase40-build-input-bundle",
        help="Build the deterministic canonical train/validation-only transfer bundle",
    )
    parser.add_argument("--train-split", type=Path, required=True)
    parser.add_argument("--val-split", type=Path, required=True)
    parser.add_argument("--output-path", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--reference-output", type=Path, default=None)
    parser.set_defaults(handler=handlers["phase40-build-input-bundle"])

    parser = subparsers.add_parser(
        "phase40-verify-input-bundle",
        help="Verify a request-bound input archive before opening its data members",
    )
    parser.add_argument("--archive-path", type=Path, required=True)
    parser.add_argument("--reference-path", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--extraction-root", type=Path, default=None)
    parser.add_argument("--verify-only", action="store_true")
    parser.set_defaults(handler=handlers["phase40-verify-input-bundle"])


def _register_evidence_commands(
    subparsers: argparse._SubParsersAction,
    handlers: dict[str, Handler],
) -> None:
    parser = subparsers.add_parser(
        "phase40-verify-run-request",
        help="Verify the immutable Phase 40 source and train/validation transfer authorities",
    )
    parser.add_argument("--request-path", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.set_defaults(handler=handlers["phase40-verify-run-request"])

    parser = subparsers.add_parser(
        "phase40-verify-run-evidence",
        help="Rehash and verify one complete Phase 40 run-evidence bundle",
    )
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument(
        "--allow-prestart-failure",
        action="store_true",
        help="Explicitly accept a hash-verified pre-start failure record",
    )
    parser.set_defaults(handler=handlers["phase40-verify-run-evidence"])

    parser = subparsers.add_parser(
        "phase40-render-graphs",
        help="Rebuild Phase 40 loss graphs from retained raw events and metrics",
    )
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--smoothing-window", type=int, default=None)
    parser.add_argument("--dpi", type=int, default=120)
    parser.set_defaults(handler=handlers["phase40-render-graphs"])

    parser = subparsers.add_parser(
        "phase40-validate-notebooks",
        help="Statically validate the three canonical Phase 40 notebook controllers",
    )
    parser.add_argument("--root", type=Path, required=True)
    parser.set_defaults(handler=handlers["phase40-validate-notebooks"])


def _register_review_commands(
    subparsers: argparse._SubParsersAction,
    handlers: dict[str, Handler],
) -> None:
    parser = subparsers.add_parser(
        "phase40-finalize-comparison",
        help="Reverify local QLoRA/PhoBERT plus the resource-only LoRA probe",
    )
    parser.add_argument("--request-path", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--scope-amendment-path", type=Path, required=True)
    parser.add_argument(
        "--package-decision",
        action="append",
        default=[],
        metavar="PACKAGE=approve|reject:REASON",
    )
    parser.add_argument(
        "--bundle-root", action="append", default=[], metavar="RUN_ID=REPOSITORY_PATH"
    )
    parser.add_argument(
        "--gpu-identity", action="append", default=[], metavar="RUN_ID=GPU_NAME"
    )
    parser.add_argument("--verify-only", action="store_true")
    parser.set_defaults(handler=handlers["phase40-finalize-comparison"])

    parser = subparsers.add_parser(
        "phase40-freeze-scope-amendment",
        help="Freeze the request-bound local two-full-model scope waiver",
    )
    parser.add_argument("--request-path", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.set_defaults(handler=handlers["phase40-freeze-scope-amendment"])

    parser = subparsers.add_parser(
        "phase40-verify-review-queue",
        help="Re-derive a frozen review queue from comparison/input authorities",
    )
    _add_review_authority_arguments(parser)
    parser.set_defaults(handler=handlers["phase40-verify-review-queue"])

    parser = subparsers.add_parser(
        "phase40-finalize-human-review",
        help="Freeze exact-coverage Vietnamese review notes without changing predictions",
    )
    _add_review_authority_arguments(parser)
    parser.add_argument("--queue-manifest-path", type=Path, required=True)
    parser.add_argument("--reviewer-return-path", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument(
        "--vietnamese-fluent-attestation", action="store_true", required=True
    )
    parser.add_argument("--verify-only", action="store_true")
    parser.set_defaults(handler=handlers["phase40-finalize-human-review"])


def register_commands(
    subparsers: argparse._SubParsersAction,
    **handlers: Handler,
) -> None:
    """Register all twelve Phase 40 commands in their frozen order."""

    _register_transfer_commands(subparsers, handlers)
    _register_evidence_commands(subparsers, handlers)
    _register_review_commands(subparsers, handlers)


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


def _parse_package_decision(value: str):  # noqa: ANN202
    from src.model_adaptation.phase40_handoff import PackageDecision

    if "=" not in value:
        raise ValueError("package decision must use PACKAGE=approve or PACKAGE=reject:REASON")
    package, raw_decision = value.rsplit("=", 1)
    decision, reason_separator, reason = raw_decision.partition(":")
    return PackageDecision(
        package=package,
        decision=decision,
        reason=(reason if reason_separator else None),
    )


def _parse_returned_root(value: str):  # noqa: ANN202
    from src.model_adaptation.phase40_handoff import ReturnedBundleRoot

    run_id, separator, path = value.partition("=")
    if not separator:
        raise ValueError("bundle root must use RUN_ID=REPOSITORY_PATH")
    return ReturnedBundleRoot(run_id=run_id, path=path)


def _parse_gpu_identity(value: str):  # noqa: ANN202
    from src.model_adaptation.phase40_handoff import ReturnedGpuIdentity

    run_id, separator, accelerator = value.partition("=")
    if not separator:
        raise ValueError("GPU identity must use RUN_ID=GPU_NAME")
    return ReturnedGpuIdentity(run_id=run_id, accelerator=accelerator)


def handle_phase40_preflight(args: argparse.Namespace) -> int:
    from src.model_adaptation.phase40_contract import preflight_phase40_inputs

    contract = preflight_phase40_inputs(
        args.train_split, args.val_split, repo_root=Path.cwd()
    )
    for identity in contract.ordered_identities:
        print(
            f"{identity.split_name}: records={identity.records} bytes={identity.bytes} "
            f"sha256={identity.sha256}"
        )
    return 0


def handle_phase40_build_source_bundle(args: argparse.Namespace) -> int:
    from src.model_adaptation.phase40_handoff import build_phase40_source_bundle

    built = build_phase40_source_bundle(args.repo_root, args.output_root)
    print(built.reference.model_dump_json())
    return 0


def handle_phase40_build_input_bundle(args: argparse.Namespace) -> int:
    from src.model_adaptation.phase40_contract import preflight_phase40_inputs
    from src.model_adaptation.phase40_handoff import build_phase40_input_bundle

    contract = preflight_phase40_inputs(
        args.train_split, args.val_split, repo_root=args.repo_root
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
    from src.model_adaptation.phase40_handoff import InputBundleReference

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
    from src.model_adaptation.phase40_handoff import RunRequest, verify_phase40_run_request

    request = RunRequest.model_validate_json(args.request_path.read_text(encoding="utf-8"))
    verify_phase40_run_request(request, repo_root=args.repo_root)
    print(f"Phase 40 run request verified: {args.request_path}")
    return 0


def handle_phase40_verify_run_evidence(args: argparse.Namespace) -> int:
    from src.model_adaptation.phase40_evidence import verify_phase40_bundle

    evidence = verify_phase40_bundle(
        args.run_root, allow_prestart_failure=args.allow_prestart_failure
    )
    print(
        f"Phase 40 run evidence verified: run_id={evidence.run_id} "
        f"status={evidence.status.value} root={args.run_root}"
    )
    return 0


def handle_phase40_render_graphs(args: argparse.Namespace) -> int:
    from src.model_adaptation.phase40_graphs import render_phase40_graphs

    provenance = render_phase40_graphs(
        args.run_root, smoothing_window=args.smoothing_window, dpi=args.dpi
    )
    print(
        f"Phase 40 graph regenerated: graph={provenance.graph_id} "
        f"output={provenance.output.relative_path}"
    )
    return 0


def handle_phase40_validate_notebooks(args: argparse.Namespace) -> int:
    from src.model_adaptation.phase40_notebooks import validate_phase40_notebooks

    issues = tuple(validate_phase40_notebooks(args.root))
    if issues:
        for issue in issues:
            print(str(issue))
        return 1
    print(f"Phase 40 notebooks validated: root={args.root} count=3")
    return 0


def handle_phase40_freeze_scope_amendment(args: argparse.Namespace) -> int:
    from src.model_adaptation.phase40_handoff import freeze_phase40_scope_amendment

    request = load_frozen_phase40_run_request(
        repo_root=args.repo_root, request_path=args.request_path
    )
    path = freeze_phase40_scope_amendment(request, repo_root=args.repo_root)
    display_path = path.relative_to(Path(args.repo_root).resolve(strict=True)).as_posix()
    print(f"Phase 40 two-model scope amendment frozen: {display_path}")
    return 0


def handle_phase40_finalize_comparison(args: argparse.Namespace) -> int:
    from src.model_adaptation.phase40_handoff import LocalTwoModelOperatorReturn

    request = load_frozen_phase40_run_request(
        repo_root=args.repo_root, request_path=args.request_path
    )
    operator_return = LocalTwoModelOperatorReturn(
        package_decisions=tuple(
            _parse_package_decision(value) for value in args.package_decision
        ),
        bundle_roots=tuple(_parse_returned_root(value) for value in args.bundle_root),
        gpu_identities=tuple(_parse_gpu_identity(value) for value in args.gpu_identity),
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


def _verify_review_comparison(request, comparison, args) -> None:  # noqa: ANN001
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
        return
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


def _load_phase40_review_authorities(args: argparse.Namespace):  # noqa: ANN201
    from src.model_adaptation.phase40_handoff import ReviewQueueRow
    from src.model_adaptation.phase40_review import (
        FIXED_REVIEW_QUEUE_PATH,
        FIXED_SELECTED_PREDICTIONS_PATH,
        read_canonical_phase40_review_regular_bytes,
    )

    request = load_frozen_phase40_run_request(
        repo_root=args.repo_root, request_path=args.request_path
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
    _verify_review_comparison(request, comparison, args)
    selected_path, selected_bytes = read_canonical_phase40_review_regular_bytes(
        repo_root=args.repo_root,
        supplied_path=args.selected_predictions_path,
        expected_relative=FIXED_SELECTED_PREDICTIONS_PATH,
        description="selected prediction bundles",
    )
    bundles = load_phase40_selected_prediction_bundles(
        selected_path, comparison_manifest=comparison
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
        queue_bytes, queue_path, ReviewQueueRow, description="review queue"
    )
    verify_phase40_review_queue(
        queue, contract=contract, prediction_bundles=bundles
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
    from src.model_adaptation.phase40_handoff import ReviewerReturnRow
    from src.model_adaptation.phase40_review import (
        FIXED_REVIEWER_RETURN_PATH,
        read_canonical_phase40_review_regular_bytes,
    )

    request, contract, _, bundles, queue, queue_bytes = (
        _load_phase40_review_authorities(args)
    )
    reviewer_return_path, reviewer_return_bytes = read_canonical_phase40_review_regular_bytes(
        repo_root=args.repo_root,
        supplied_path=args.reviewer_return_path,
        expected_relative=FIXED_REVIEWER_RETURN_PATH,
        description="reviewer return",
    )
    reviews = _load_jsonl_models_from_bytes(
        reviewer_return_bytes,
        reviewer_return_path,
        ReviewerReturnRow,
        description="reviewer return",
    )
    finalize_phase40_human_review(
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


def load_frozen_phase40_run_request(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
    from src.model_adaptation.phase40_handoff import load_frozen_phase40_run_request as implementation

    return implementation(*args, **kwargs)
def verify_phase40_input_bundle(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
    from src.model_adaptation.phase40_handoff import verify_phase40_input_bundle as implementation

    return implementation(*args, **kwargs)
def finalize_phase40_comparison(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
    from src.model_adaptation.phase40_handoff import finalize_phase40_comparison as implementation

    return implementation(*args, **kwargs)
def load_frozen_phase40_scope_amendment(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
    from src.model_adaptation.phase40_handoff import load_frozen_phase40_scope_amendment as implementation

    return implementation(*args, **kwargs)
def load_phase40_selected_prediction_bundles(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
    from src.model_adaptation.phase40_handoff import load_phase40_selected_prediction_bundles as implementation

    return implementation(*args, **kwargs)
def verify_phase40_review_queue(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
    from src.model_adaptation.phase40_handoff import verify_phase40_review_queue as implementation

    return implementation(*args, **kwargs)
def load_canonical_phase40_comparison_manifest(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
    from src.model_adaptation.phase40_review import load_canonical_phase40_comparison_manifest as implementation

    return implementation(*args, **kwargs)
def load_phase40_review_authority(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
    from src.model_adaptation.phase40_review import load_phase40_review_authority as implementation

    return implementation(*args, **kwargs)


def verify_phase40_final_review_comparison(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
    from src.model_adaptation.phase40_review import verify_phase40_final_review_comparison as implementation

    return implementation(*args, **kwargs)


def finalize_phase40_human_review(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
    from src.model_adaptation.phase40_review import finalize_phase40_human_review as implementation

    return implementation(*args, **kwargs)
