"""Phase 41 compatibility commands with evaluator imports deferred to handlers."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Callable


Handler = Callable[[argparse.Namespace], int]
PRECLAIM_AUDIT = Path("data/models/phase41/preclaim-audit/41-02-preclaim-failure.json")
STAGED_PRECLAIM_AUDIT = Path(
    "data/models/phase41/failed-invocation/"
    "44c654a9bc92151a00231fcbf9e73209ab9e0802239ffbd0597efa4d8f353401/"
    "claim-capable-preclaim-failure.json"
)
ARGUMENT_PRECLAIM_AUDIT = Path(
    "data/models/phase41/failed-invocation/"
    "0cdd803d0f145b147e34c5a8b0a9b1846496192bf6b002a46c3dbccaaf2e9c22/"
    "claim-capable-preclaim-failure.json"
)
CAPTURED_HELPER_PRECLAIM_AUDIT = Path(
    "data/models/phase41/failed-invocation/"
    "28374ea5c1f7fee43e12ee0395ad4fcd7c6a2e4801b809131afa6cca2db7e8e7/"
    "claim-capable-preclaim-failure.json"
)
AUTONOMOUS_RESEAL_DELEGATION = Path(
    "data/models/phase41/autonomous-reseal-delegation.json"
)


def _add_output_root(parser: argparse.ArgumentParser, help_text: str) -> None:
    parser.add_argument("--output-root", type=Path, default=None, help=help_text)


def _register_prepare(
    subparsers: argparse._SubParsersAction,
    handler: Handler,
) -> None:
    parser = subparsers.add_parser(
        "phase41-prepare-evaluation",
        help="Freeze the code-fixed Phase 41 preauthorization without opening the holdout",
    )
    _add_output_root(
        parser,
        "Fixed ProgramData operational root (default; overrides must match it)",
    )
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--phase39-contract-path", type=Path, required=True)
    parser.add_argument(
        "--phase40-comparison-manifest-path", type=Path, required=True
    )
    parser.add_argument("--phase40-review-manifest-path", type=Path, required=True)
    parser.add_argument(
        "--preclaim-rejection-audit-path", type=Path, default=PRECLAIM_AUDIT
    )
    parser.add_argument(
        "--staged-preclaim-failure-audit-path",
        type=Path,
        default=STAGED_PRECLAIM_AUDIT,
    )
    parser.add_argument(
        "--argument-preclaim-failure-audit-path",
        type=Path,
        default=ARGUMENT_PRECLAIM_AUDIT,
    )
    parser.add_argument(
        "--autonomous-reseal-delegation-path",
        type=Path,
        default=AUTONOMOUS_RESEAL_DELEGATION,
    )
    parser.add_argument(
        "--captured-helper-preclaim-failure-audit-path",
        type=Path,
        default=CAPTURED_HELPER_PRECLAIM_AUDIT,
    )
    parser.set_defaults(handler=handler)


def _register_authority_commands(
    subparsers: argparse._SubParsersAction,
    handlers: dict[str, Handler],
) -> None:
    output_help = "Fixed ProgramData operational root (default)"
    parser = subparsers.add_parser(
        "phase41-verify-preauthorization",
        help="Verify frozen Phase 41 preauthorization without loading models or data",
    )
    _add_output_root(parser, output_help)
    parser.set_defaults(handler=handlers["phase41-verify-preauthorization"])

    parser = subparsers.add_parser(
        "phase41-authorize-evaluation",
        help="Record the exact explicit one-shot authorization",
    )
    _add_output_root(parser, output_help)
    parser.add_argument("--prepared-sha256", required=True)
    parser.add_argument(
        "--statement",
        required=True,
        help="Exact Phase 41 checkpoint signal; extra text is rejected",
    )
    parser.set_defaults(handler=handlers["phase41-authorize-evaluation"])

    parser = subparsers.add_parser(
        "phase41-run-once",
        help="Run the sole canonical two-model reserved evaluation",
    )
    _add_output_root(parser, output_help)
    parser.set_defaults(handler=handlers["phase41-run-once"])

    parser = subparsers.add_parser(
        "phase41-freeze-deployment-fit-disposition",
        help="Freeze the precommitted post-evaluation deployment-fit choice",
    )
    _add_output_root(parser, output_help)
    parser.set_defaults(
        handler=handlers["phase41-freeze-deployment-fit-disposition"]
    )

    parser = subparsers.add_parser(
        "phase41-export-evidence",
        help="Mirror verified ProgramData evidence into an immutable repo export",
    )
    _add_output_root(parser, output_help)
    parser.add_argument(
        "--repository-output-root", type=Path, default=Path("data/models/phase41")
    )
    parser.set_defaults(handler=handlers["phase41-export-evidence"])

    parser = subparsers.add_parser(
        "phase41-verify-evidence",
        help="Verify terminal evidence without an opener, split, predictor, or model",
    )
    _add_output_root(parser, output_help)
    parser.set_defaults(handler=handlers["phase41-verify-evidence"])


def register_commands(
    subparsers: argparse._SubParsersAction,
    **handlers: Handler,
) -> None:
    """Register the seven frozen Phase 41 command surfaces in order."""

    _register_prepare(subparsers, handlers["phase41-prepare-evaluation"])
    _register_authority_commands(subparsers, handlers)


def _print_console_safe(message: object, *, stream=None) -> None:
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


def _phase41_output_root(value: Path | None) -> Path:
    if value is not None:
        return value
    from src.model_adaptation.phase41_evaluation import phase41_operational_root

    return phase41_operational_root()


def handle_phase41_prepare_evaluation(args: argparse.Namespace) -> int:
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
            args, "preclaim_rejection_audit_path", PRECLAIM_AUDIT
        ),
        staged_preclaim_failure_audit_path=getattr(
            args, "staged_preclaim_failure_audit_path", STAGED_PRECLAIM_AUDIT
        ),
        argument_preclaim_failure_audit_path=getattr(
            args, "argument_preclaim_failure_audit_path", ARGUMENT_PRECLAIM_AUDIT
        ),
        autonomous_reseal_delegation_path=getattr(
            args, "autonomous_reseal_delegation_path", AUTONOMOUS_RESEAL_DELEGATION
        ),
        captured_helper_preclaim_failure_audit_path=getattr(
            args,
            "captured_helper_preclaim_failure_audit_path",
            CAPTURED_HELPER_PRECLAIM_AUDIT,
        ),
    )
    print(
        f"Phase 41 prepared: request={prepared.path} "
        f"sha256={prepared.prepared_sha256}"
    )
    return 0


def handle_phase41_verify_preauthorization(args: argparse.Namespace) -> int:
    from src.model_adaptation.phase41_evaluation import verify_phase41_preauthorization

    prepared = verify_phase41_preauthorization(_phase41_output_root(args.output_root))
    print(f"Phase 41 preauthorization verified: sha256={prepared.prepared_sha256}")
    return 0


def handle_phase41_authorize_evaluation(args: argparse.Namespace) -> int:
    from src.model_adaptation.phase41_evaluation import authorize_phase41_evaluation

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


def handle_phase41_freeze_deployment_fit_disposition(
    args: argparse.Namespace,
) -> int:
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
