# ============================================================
# STEP 7 of 10 — Runtime Entry Point (`vnphish analyze`)
# ============================================================
# Canonical source (this numbered copy exists ONLY for defense-day
# navigation — it is not a second implementation and is not imported
# by anything): src/runtime/cli.py
#
# What this file does: the argparse CLI. handle_analyze() (line ~84)
# is where a live message actually enters the system: it runs a
# readiness check FIRST (before touching any model), reads the message
# text, builds the runtime service (step 8), calls
# service.analyze_text(), and prints the rendered result. This is the
# file to open first if a judge says "show me what happens when I type
# vnphish analyze."
#
# See also: documents/reports/supervisor/defense_code_navigation.md
# ============================================================

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
    """
    Build the CLI parser for the local runtime.

    Three subcommands, each mapped to a handler via set_defaults(handler=...)
    below — that's the whole dispatch mechanism: main() just calls
    whatever `args.handler` argparse resolved to, no manual if/elif chain
    needed. allow_abbrev=False: disables argparse's default behavior of
    accepting unambiguous prefixes of long options (e.g. --tex for --text)
    — deliberately requiring exact flag names so command invocations are
    unambiguous and copy-pasteable/scriptable without surprise abbreviation
    collisions as more flags get added later.
    """

    parser = argparse.ArgumentParser(
        prog="vnphish",
        allow_abbrev=False,
        description=(
            "Local Vietnamese financial phishing/threat detection runtime. "
            "Use 'analyze' for terminal text-only checks (no browser). "
            "Use 'demo' to start the local browser web UI."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Analyze one pasted message in the terminal (text-only, no browser)",
        description=(
            "Analyze one pasted message directly in the terminal. This is a "
            "text-only command: it opens no browser page. Paste the message "
            "and finish stdin (Ctrl+Z then Enter on Windows) or pass --text "
            "for automation."
        ),
    )
    analyze_parser.add_argument(
        "--text",
        help="Optional explicit message text for automation (skips stdin)",
    )
    # --channel: a HINT only (e.g. "sms", "zalo", "email", "unknown") —
    # get_args(ChannelName) pulls the allowed values directly from the
    # ChannelName Literal type in contracts.py, so this argparse choices
    # list can never drift out of sync with the actual type definition.
    # This is context for the model/rules, not something that changes
    # WHETHER analysis runs — a message is still analyzed even with
    # channel="unknown" (the default).
    analyze_parser.add_argument(
        "--channel",
        choices=get_args(ChannelName),
        default="unknown",
        help="Optional channel hint for the pasted message",
    )
    analyze_parser.set_defaults(handler=handle_analyze)

    doctor_parser = subparsers.add_parser("doctor", help="Check local runtime readiness")
    doctor_parser.set_defaults(handler=handle_doctor)

    demo_parser = subparsers.add_parser(
        "demo",
        help="Start the local demo web UI in your browser for non-technical verification",
        description=(
            "Start the local demo web UI. This launches a local web server and "
            "opens the demo page in your default browser (unless --no-browser "
            "is passed)."
        ),
    )
    demo_parser.add_argument("--host", default="127.0.0.1", help="Host interface for the local demo server")
    demo_parser.add_argument("--port", type=int, default=8765, help="Port for the local demo server")
    demo_parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not open the demo web UI automatically in the default browser",
    )
    demo_parser.set_defaults(handler=handle_demo)

    return parser


def read_message_from_stdin() -> str:
    """Read one message from stdin for the stdin-first analyze flow."""
    # stdin is the DEFAULT way to feed a message in (paste + EOF) — --text
    # exists purely as an automation/scripting escape hatch (see
    # handle_analyze below) so tests and batch scripts don't need to pipe
    # stdin.
    return sys.stdin.read().strip()


def handle_analyze(args: argparse.Namespace) -> int:
    """
    Run the local analyze flow after a readiness check.

    THIS FUNCTION IS THE ANSWER to "show me what happens when I type
    vnphish analyze" — four steps, in order:
      1. run_runtime_doctor() FIRST, before anything else — checks the
         model file/registry/dependencies are actually in place. This is
         deliberate ordering: fail with a clear, actionable readiness
         report (return code 2) rather than a confusing crash halfway
         through model loading if something's missing.
      2. Get the message text — either from --text (automation) or by
         reading stdin (the interactive/manual-paste path).
      3. build_default_runtime_service() constructs the SAME
         RuntimeService used everywhere else in this project (the browser
         demo, step 8) — there's no CLI-specific analysis logic here, this
         function is purely argument-handling + calling into the shared
         service.
      4. Call service.analyze_text() — this is the handoff into step 8.
         RuntimeBoundaryError/RuntimeUnavailableError are the two
         EXPECTED failure modes (e.g. text-only boundary violation, model
         backend unavailable) and get a clean rendered error + exit code
         1; anything else propagates as an unhandled exception (a genuine
         bug, not a normal operational failure), which is intentional —
         this except clause is narrow, not a blanket catch-all.
    """

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
    # Same run_runtime_doctor() call handle_analyze makes internally before
    # every analysis — exposed here as its own standalone command so a
    # judge (or the presenter) can check "is everything wired up correctly"
    # WITHOUT needing to also analyze a throwaway message just to trigger
    # the check.
    status = run_runtime_doctor()
    print(format_doctor_report(status))
    return 0 if status.ready else 1


def handle_demo(args: argparse.Namespace) -> int:
    """Start the local demo server."""
    # Thin passthrough to run_demo_server (src/runtime/demo.py) — the
    # browser-based demo UI, which internally calls the exact same
    # RuntimeService.analyze_text() as handle_analyze above, just over
    # HTTP instead of directly in-process. Not a second implementation.
    return run_demo_server(host=args.host, port=args.port, open_browser=not args.no_browser)


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for module and console-script execution."""

    # Windows may default to a legacy code page that cannot print Vietnamese
    # model output. Keep redirected and test streams unchanged.
    # (Concretely: Windows' default terminal code page, cp1252 or similar,
    # can't represent Vietnamese diacritics like ệ/ạ/ề — without this
    # reconfigure, printing real model output would either crash with a
    # UnicodeEncodeError or silently mangle the text. The `hasattr` guard
    # matters because sys.stdout might be replaced with something that
    # DOESN'T have .reconfigure() — e.g. under pytest's output capturing,
    # or when a caller has redirected stdout to a plain file-like object —
    # and forcing this would break those cases instead of helping them.)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = build_parser()
    args = parser.parse_args(argv)
    # The actual dispatch: whichever subparser matched set `args.handler`
    # via set_defaults above (handle_analyze / handle_doctor / handle_demo)
    # — just call it. Every handler returns an int, which becomes this
    # process's exit code via `raise SystemExit(main())` below.
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
