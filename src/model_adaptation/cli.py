"""Thin compatibility CLI for model adaptation and historical evidence commands."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from src.model_adaptation.commands import adaptation, legacy_phase40, legacy_phase41
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


def _load_jsonl_models_from_bytes(  # noqa: ANN001
    payload: bytes, path: Path, model_type, *, description: str | None = None
):
    return legacy_phase40._load_jsonl_models_from_bytes(
        payload, path, model_type, description=description
    )


def _load_phase40_review_authorities(args: argparse.Namespace):  # noqa: ANN201
    return legacy_phase40._load_phase40_review_authorities(args)


def _phase41_output_root(value: Path | None) -> Path:
    return legacy_phase41._phase41_output_root(value)


def build_parser() -> argparse.ArgumentParser:
    """Build the exact historical 23-command parser without implementation imports."""

    parser = argparse.ArgumentParser(
        prog="python -m src.model_adaptation.cli", allow_abbrev=False
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    adaptation.register_commands(
        subparsers,
        pilot=handle_pilot,
        train=handle_train,
        convert=handle_convert,
        doctor=handle_doctor,
    )
    legacy_phase40.register_commands(
        subparsers,
        **{
            "phase40-preflight": handle_phase40_preflight,
            "phase40-build-source-bundle": handle_phase40_build_source_bundle,
            "phase40-build-input-bundle": handle_phase40_build_input_bundle,
            "phase40-verify-input-bundle": handle_phase40_verify_input_bundle,
            "phase40-verify-run-request": handle_phase40_verify_run_request,
            "phase40-verify-run-evidence": handle_phase40_verify_run_evidence,
            "phase40-render-graphs": handle_phase40_render_graphs,
            "phase40-validate-notebooks": handle_phase40_validate_notebooks,
            "phase40-finalize-comparison": handle_phase40_finalize_comparison,
            "phase40-freeze-scope-amendment": handle_phase40_freeze_scope_amendment,
            "phase40-verify-review-queue": handle_phase40_verify_review_queue,
            "phase40-finalize-human-review": handle_phase40_finalize_human_review,
        },
    )
    legacy_phase41.register_commands(
        subparsers,
        **{
            "phase41-prepare-evaluation": handle_phase41_prepare_evaluation,
            "phase41-verify-preauthorization": handle_phase41_verify_preauthorization,
            "phase41-authorize-evaluation": handle_phase41_authorize_evaluation,
            "phase41-run-once": handle_phase41_run_once,
            "phase41-freeze-deployment-fit-disposition": handle_phase41_freeze_deployment_fit_disposition,
            "phase41-export-evidence": handle_phase41_export_evidence,
            "phase41-verify-evidence": handle_phase41_verify_evidence,
        },
    )
    return parser


def handle_pilot(args: argparse.Namespace) -> int:
    return dispatch("pilot", args)


def handle_train(args: argparse.Namespace) -> int:
    return dispatch("train", args)


def handle_convert(args: argparse.Namespace) -> int:
    return dispatch("convert", args)


def handle_doctor(args: argparse.Namespace) -> int:
    return dispatch("doctor", args)


def handle_phase40_preflight(args: argparse.Namespace) -> int:
    return dispatch("phase40-preflight", args)


def handle_phase40_build_source_bundle(args: argparse.Namespace) -> int:
    return dispatch("phase40-build-source-bundle", args)


def handle_phase40_build_input_bundle(args: argparse.Namespace) -> int:
    return dispatch("phase40-build-input-bundle", args)


def handle_phase40_verify_input_bundle(args: argparse.Namespace) -> int:
    return dispatch("phase40-verify-input-bundle", args)


def handle_phase40_verify_run_request(args: argparse.Namespace) -> int:
    return dispatch("phase40-verify-run-request", args)


def handle_phase40_verify_run_evidence(args: argparse.Namespace) -> int:
    return dispatch("phase40-verify-run-evidence", args)


def handle_phase40_render_graphs(args: argparse.Namespace) -> int:
    return dispatch("phase40-render-graphs", args)


def handle_phase40_validate_notebooks(args: argparse.Namespace) -> int:
    return dispatch("phase40-validate-notebooks", args)


def handle_phase40_finalize_comparison(args: argparse.Namespace) -> int:
    return dispatch("phase40-finalize-comparison", args)


def handle_phase40_freeze_scope_amendment(args: argparse.Namespace) -> int:
    return dispatch("phase40-freeze-scope-amendment", args)


def handle_phase40_verify_review_queue(args: argparse.Namespace) -> int:
    return dispatch("phase40-verify-review-queue", args)


def handle_phase40_finalize_human_review(args: argparse.Namespace) -> int:
    return dispatch("phase40-finalize-human-review", args)


def handle_phase41_prepare_evaluation(args: argparse.Namespace) -> int:
    return dispatch("phase41-prepare-evaluation", args)


def handle_phase41_verify_preauthorization(args: argparse.Namespace) -> int:
    return dispatch("phase41-verify-preauthorization", args)


def handle_phase41_authorize_evaluation(args: argparse.Namespace) -> int:
    return dispatch("phase41-authorize-evaluation", args)


def handle_phase41_run_once(args: argparse.Namespace) -> int:
    """Compatibility marker: run_phase41_once(_phase41_output_root(args.output_root))."""

    return dispatch("phase41-run-once", args)


def handle_phase41_freeze_deployment_fit_disposition(
    args: argparse.Namespace,
) -> int:
    return dispatch("phase41-freeze-deployment-fit-disposition", args)


def handle_phase41_export_evidence(args: argparse.Namespace) -> int:
    return dispatch("phase41-export-evidence", args)


def handle_phase41_verify_evidence(args: argparse.Namespace) -> int:
    return dispatch("phase41-verify-evidence", args)


def main(argv: list[str] | None = None) -> int:
    """Parse once, preserve raw argv, and translate the frozen exception set."""

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
