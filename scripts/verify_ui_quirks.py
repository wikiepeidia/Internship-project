"""Verify Phase 31 UI quirks (edge cases, double-submit, console/page errors) through the real local demo UI."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "vnphish.phase31.ui-quirks.v1"
CASE_NAMES = ("empty", "very_long", "malformed", "mixed_vi_en", "double_submit")
ARTIFACT_DIR = Path(".planning/phases/31-ui-quirks-edge-cases-regression-re-check/artifacts")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_case_selection(value: str) -> list[str]:
    """Parse a comma-separated case-name subset, validated against CASE_NAMES."""

    cases = [part.strip().casefold() for part in value.split(",") if part.strip()]
    if not cases:
        raise argparse.ArgumentTypeError("at least one case name is required")
    unknown = sorted(set(cases) - set(CASE_NAMES))
    if unknown:
        raise argparse.ArgumentTypeError(f"unknown case name(s): {', '.join(unknown)}")
    return cases


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Show the browser window instead of headless Chromium",
    )
    parser.add_argument(
        "--cases",
        type=parse_case_selection,
        default=list(CASE_NAMES),
        help="Comma-separated subset of cases to run (default: all)",
    )
    return parser


def build_output_path(output: Path | None = None, *, artifact_dir: Path = ARTIFACT_DIR) -> Path:
    """Default the evidence artifact under the Phase 31 artifacts dir, or use an explicit path."""

    if output is not None:
        return output
    return artifact_dir / "31-ui-quirks-results.json"


def request_latency_ms(response: Any) -> float | None:
    """Extract request latency from a Playwright response, matching the Phase 30 helper behavior."""

    timing_attr = response.request.timing
    timing = timing_attr() if callable(timing_attr) else timing_attr
    try:
        return float(timing["responseEnd"] - timing["requestStart"])
    except (KeyError, TypeError, ValueError):
        return None


def double_submit_passed(
    *,
    completed_analyze_response_count: int,
    completed_superseded_response_count: int,
    abort_error_bubble_count: int,
    typing_count: int,
    button_disabled: bool,
) -> bool:
    """UIQ-02/D-04: pass only when exactly one response completes cleanly with no leftover evidence of a race."""

    return (
        completed_analyze_response_count == 1
        and completed_superseded_response_count == 0
        and abort_error_bubble_count == 0
        and typing_count == 0
        and button_disabled is False
    )


def build_case_record(name: str, *, passed: bool, **fields: Any) -> dict[str, Any]:
    """Build a per-case evidence record with explicit status/passed fields, never raw input text."""

    record: dict[str, Any] = {"name": name, "status": "pass" if passed else "fail", "passed": bool(passed)}
    record.update(fields)
    return record


def build_artifact(
    *,
    cases: list[dict[str, Any]],
    console_messages: list[dict[str, Any]],
    page_errors: list[str],
    demo_process: dict[str, Any] | None = None,
    recorded_at: datetime | None = None,
) -> dict[str, Any]:
    """Build the top-level artifact; overall_pass is true only when every case passed."""

    overall_pass = bool(cases) and all(case.get("passed") is True for case in cases)
    return {
        "schema": SCHEMA_VERSION,
        "recorded_at": (recorded_at or utc_now()).isoformat(),
        "overall_pass": overall_pass,
        "cases": cases,
        "console_messages": console_messages,
        "page_errors": page_errors,
        "demo_process": demo_process,
    }


def write_artifact(path: Path, artifact: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    # Placeholder entry point: Task 2 of Plan 31-01 wires this to the real Playwright
    # browser verification. Keeping this minimal here means --help and the pure helper
    # tests above stay independent of Playwright/browser startup.
    build_parser().parse_args(argv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
