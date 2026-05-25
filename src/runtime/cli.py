"""CLI entry point for the Phase 2 local runtime."""

import argparse
import sys
from typing import get_args

from src.runtime.contracts import ChannelName
from src.runtime.demo import run_demo_server
from src.runtime.doctor import format_doctor_report, run_runtime_doctor
from src.runtime.render import render_analysis_result, render_runtime_error
from src.runtime.service import (
    RuntimeBoundaryError,
    RuntimeUnavailableError,
    build_default_runtime_service,
)


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for the local runtime."""

    parser = argparse.ArgumentParser(prog="vnphish", allow_abbrev=False)
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze_parser = subparsers.add_parser("analyze", help="Analyze one pasted message")
    analyze_parser.add_argument("--text", help="Optional explicit message text for automation")
    analyze_parser.add_argument(
        "--channel",
        choices=get_args(ChannelName),
        default="unknown",
        help="Optional channel hint for the pasted message",
    )
    analyze_parser.set_defaults(handler=handle_analyze)

    doctor_parser = subparsers.add_parser("doctor", help="Check local runtime readiness")
    doctor_parser.set_defaults(handler=handle_doctor)

    demo_parser = subparsers.add_parser("demo", help="Start the local demo UI for non-technical verification")
    demo_parser.add_argument("--host", default="127.0.0.1", help="Host interface for the local demo server")
    demo_parser.add_argument("--port", type=int, default=8765, help="Port for the local demo server")
    demo_parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not open the demo UI automatically in the default browser",
    )
    demo_parser.set_defaults(handler=handle_demo)

    return parser


def read_message_from_stdin() -> str:
    """Read one message from stdin for the stdin-first analyze flow."""

    return sys.stdin.read().strip()


def handle_analyze(args: argparse.Namespace) -> int:
    """Run the local analyze flow after a readiness check."""

    status = run_runtime_doctor()
    if not status.ready:
        print(format_doctor_report(status))
        return 2

    message_text = args.text if args.text is not None else read_message_from_stdin()
    service = build_default_runtime_service()

    try:
        result = service.analyze_text(message_text, channel=args.channel)
    except (RuntimeBoundaryError, RuntimeUnavailableError) as exc:
        print(render_runtime_error(str(exc), exc.steps))
        return 1

    print(render_analysis_result(result))
    return 0


def handle_doctor(args: argparse.Namespace) -> int:
    """Run the doctor command and print the readiness report."""

    status = run_runtime_doctor()
    print(format_doctor_report(status))
    return 0 if status.ready else 1


def handle_demo(args: argparse.Namespace) -> int:
    """Start the local demo server."""

    return run_demo_server(host=args.host, port=args.port, open_browser=not args.no_browser)


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for module and console-script execution."""

    parser = build_parser()
    args = parser.parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())