"""Narrow, import-closed entrypoint for the final Phase 40 comparison.

The external PowerShell preflight launches this module only after it has
written the fixed comparison-launch receipt.  Keeping the entrypoint separate
from the general CLI prevents Phase 41 code from entering the Phase 40 source
authority through unrelated imports.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from src.model_adaptation.phase40_comparison_launch import (
    consume_phase40_comparison_launch_capability,
)


def _assignment(value: str, *, description: str) -> tuple[str, str]:
    run_id, separator, item = value.partition("=")
    if not separator or not run_id or not item:
        raise argparse.ArgumentTypeError(f"{description} must be RUN_ID=VALUE")
    if run_id != run_id.strip() or item != item.strip():
        raise argparse.ArgumentTypeError(f"{description} cannot contain edge whitespace")
    return run_id, item


def _bundle_root(value: str):
    from src.model_adaptation.phase40_handoff import ReturnedBundleRoot

    run_id, path = _assignment(value, description="bundle root")
    return ReturnedBundleRoot(run_id=run_id, path=path)


def _gpu_identity(value: str):
    from src.model_adaptation.phase40_handoff import ReturnedGpuIdentity

    run_id, accelerator = _assignment(value, description="GPU identity")
    return ReturnedGpuIdentity(run_id=run_id, accelerator=accelerator)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m src.model_adaptation.phase40_finalize",
        description="Finalize the two-origin Phase 40 validation comparison.",
    )
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument(
        "--bundle-root",
        action="append",
        required=True,
        metavar="RUN_ID=REPOSITORY_PATH",
    )
    parser.add_argument(
        "--gpu-identity",
        action="append",
        required=True,
        metavar="RUN_ID=GPU_NAME",
    )
    parser.add_argument("--verify-only", action="store_true")
    return parser


def _run_finalizer(args: argparse.Namespace):
    from src.model_adaptation.phase40_handoff import (
        LocalTwoModelOperatorReturn,
        finalize_phase40_final_comparison,
    )

    operator_return = LocalTwoModelOperatorReturn(
        bundle_roots=tuple(_bundle_root(value) for value in args.bundle_root),
        gpu_identities=tuple(_gpu_identity(value) for value in args.gpu_identity),
    )
    return finalize_phase40_final_comparison(
        operator_return,
        repo_root=args.repo_root,
        output_root=args.output_root,
        verify_only=args.verify_only,
    )


def main(argv: list[str] | None = None) -> int:
    invocation_argv = list(sys.argv[1:] if argv is None else argv)
    args = build_parser().parse_args(invocation_argv)
    consume_phase40_comparison_launch_capability(
        repo_root=Path.cwd(),
        argv=invocation_argv,
    )
    artifacts = _run_finalizer(args)
    print(
        f"Phase 40 comparison {artifacts.manifest.status}: "
        f"manifest={artifacts.manifest_path} report={artifacts.report_path}"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised through subprocess tests
    sys.exit(main())
