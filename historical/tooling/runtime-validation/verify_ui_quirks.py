"""Verify Phase 31 UI quirks (edge cases, double-submit, console/page errors) through the real local demo UI."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "vnphish.phase31.ui-quirks.v1"
CASE_NAMES = ("empty", "very_long", "malformed", "mixed_vi_en", "double_submit")
ARTIFACT_DIR = Path(".planning/phases/31-ui-quirks-edge-cases-regression-re-check/artifacts")

# Bounded, deterministic fixtures only -- never persist arbitrary/raw user text (T-31-01-I).
EMPTY_CASE_WAIT_MS = 500
TEXT_CASE_TIMEOUT_MS = 180_000
DOUBLE_SUBMIT_TIMEOUT_MS = 180_000

VERY_LONG_TEXT = (
    "Canh bao lua dao ngan hang, vui long doc ky truoc khi bam vao lien ket ben duoi. " * 12
) + (
    "http://vcb-secure-alert-verification-portal-example-domain-for-load-testing-only"
    ".example/lock?token=abcdefghijklmnopqrstuvwxyz0123456789"
)
MALFORMED_TEXT = (
    "asdkjh 1234 !!! ??? %%% zzz random keyboard mash not resembling any Vietnamese "
    "phishing or benign pattern at all qwerty uiop"
)
MIXED_VI_EN_TEXT = (
    "Xin chao, VPBank canh bao account internet banking cua ban se bi suspended "
    "neu khong verify ngay bay gio. Please click here to confirm: "
    "http://example-mixed-lang-test-domain.example/verify-now"
)
DOUBLE_SUBMIT_FIRST_TEXT = (
    "Tin nhan thu nhat: VPBank canh bao tai khoan cua ban se bi khoa trong 24h "
    "neu khong xac nhan ngay."
)
DOUBLE_SUBMIT_SECOND_TEXT = (
    "Tin nhan thu hai: Ban co the giup minh kiem tra tin nhan ngan hang nay khong?"
)

# Wraps window.fetch (client-side only, does not touch demo.js) so the double-submit
# case can observe which /api/analyze calls actually completed vs. were aborted by
# demo.js's `currentController.abort()` guard, without changing the frozen contract.
DOUBLE_SUBMIT_TELEMETRY_SCRIPT = """
(() => {
  window.__uiQuirksTelemetry = { requests: [] };
  const originalFetch = window.fetch.bind(window);
  window.fetch = function (input, init) {
    const url = typeof input === 'string' ? input : (input && input.url) || '';
    if (!url.includes('/api/analyze')) {
      return originalFetch(input, init);
    }
    const record = {
      index: window.__uiQuirksTelemetry.requests.length,
      completed: false,
      aborted: false,
      status: null,
    };
    window.__uiQuirksTelemetry.requests.push(record);
    const promise = originalFetch(input, init);
    promise.then(
      (response) => { record.completed = true; record.status = response.status; },
      (err) => { if (err && err.name === 'AbortError') { record.aborted = true; } }
    );
    return promise;
  };
})();
"""


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


# ---------------------------------------------------------------------------
# Demo process lifecycle (Phase 30 stronger subprocess form: captures
# stdout/stderr and does not rely on the installed `vnphish` console script).
# ---------------------------------------------------------------------------


def start_demo_server(port: int) -> subprocess.Popen[str]:
    return subprocess.Popen(
        [sys.executable, "-m", "src.runtime.cli", "demo", "--no-browser", "--port", str(port)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def stop_demo_server(process: subprocess.Popen[str]) -> dict[str, Any]:
    if process.poll() is None:
        process.terminate()
    try:
        stdout, stderr = process.communicate(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        stdout, stderr = process.communicate(timeout=10)
    return {"returncode": process.returncode, "stdout": stdout, "stderr": stderr}


def wait_for_server(page: Any, process: subprocess.Popen[str], demo_url: str) -> None:
    last_error: Exception | None = None
    for _ in range(90):
        if process.poll() is not None:
            raise RuntimeError("vnphish demo exited before the verifier-owned server became reachable")
        try:
            page.goto(demo_url, wait_until="domcontentloaded", timeout=2_000)
            return
        except Exception as exc:  # noqa: BLE001 - readiness probe must retry transient connection errors.
            last_error = exc
            time.sleep(1)
    raise RuntimeError(f"Demo server was not reachable at {demo_url}") from last_error


# ---------------------------------------------------------------------------
# Console/page-error capture (UIQ-04/D-01) and DOM-state helpers.
# ---------------------------------------------------------------------------


def _safe_console_location(msg: Any) -> dict[str, Any] | None:
    try:
        location = msg.location
    except Exception:  # noqa: BLE001 - location capture is best-effort evidence only.
        return None
    if isinstance(location, dict):
        return location
    return None


def attach_console_capture(page: Any) -> tuple[list[dict[str, Any]], list[str]]:
    """Attach console/page-error listeners before any navigation, per UIQ-04/D-01."""

    console_messages: list[dict[str, Any]] = []
    page_errors: list[str] = []

    def on_console(msg: Any) -> None:
        console_messages.append(
            {"type": msg.type, "text": msg.text, "location": _safe_console_location(msg)}
        )

    def on_pageerror(exc: Any) -> None:
        page_errors.append(str(exc))

    page.on("console", on_console)
    page.on("pageerror", on_pageerror)
    return console_messages, page_errors


def typing_count(page: Any) -> int:
    return page.locator(".message--typing").count()


def button_disabled(page: Any) -> bool:
    return bool(page.locator("#analyze-button").evaluate("node => node.disabled"))


def terminal_bubble_count(page: Any) -> int:
    return page.locator(".message--result, .message--error").count()


def error_bubble_count(page: Any) -> int:
    return page.locator(".message--error").count()


def reset_thread(page: Any) -> None:
    page.click("#clear-button")
    page.wait_for_timeout(100)


# ---------------------------------------------------------------------------
# Case runners (UIQ-01 edge cases + UIQ-02/D-04 double-submit).
# ---------------------------------------------------------------------------


def run_empty_case(page: Any, page_errors: list[str]) -> dict[str, Any]:
    """UIQ-01: a true empty submit must be blocked client-side by the `required` textarea."""

    page_errors_before = len(page_errors)
    initial_terminal_count = terminal_bubble_count(page)
    analyze_requests: list[Any] = []

    def on_request(request: Any) -> None:
        if "/api/analyze" in request.url:
            analyze_requests.append(request)

    page.on("request", on_request)
    try:
        page.fill("#message-input", "")
        page.click("#analyze-button")
        page.wait_for_timeout(EMPTY_CASE_WAIT_MS)
    finally:
        page.remove_listener("request", on_request)

    new_page_error_count = len(page_errors) - page_errors_before
    fields = {
        "request_count": len(analyze_requests),
        "typing_count": typing_count(page),
        "terminal_bubble_count": terminal_bubble_count(page),
        "button_disabled": button_disabled(page),
        "new_page_error_count": new_page_error_count,
    }
    passed = (
        len(analyze_requests) == 0
        and terminal_bubble_count(page) == initial_terminal_count
        and fields["typing_count"] == 0
        and new_page_error_count == 0
    )
    return build_case_record("empty", passed=passed, **fields)


def run_text_case(
    page: Any,
    name: str,
    text: str,
    *,
    timeout_ms: int,
    page_errors: list[str],
) -> dict[str, Any]:
    """UIQ-01: very_long/malformed/mixed_vi_en must settle to a result or a well-formed error bubble."""

    page_errors_before = len(page_errors)
    request_count = 0

    def on_request(request: Any) -> None:
        nonlocal request_count
        if "/api/analyze" in request.url:
            request_count += 1

    page.on("request", on_request)
    response_count = 0
    response_status: int | None = None
    error_message: str | None = None
    try:
        page.fill("#message-input", text)
        try:
            with page.expect_response(
                lambda response: "/api/analyze" in response.url, timeout=timeout_ms
            ) as response_info:
                page.click("#analyze-button")
            response = response_info.value
            response_count = 1
            response_status = response.status
            page.wait_for_function(
                "!document.querySelector('#analyze-button').disabled", timeout=timeout_ms
            )
            page.wait_for_function(
                "!document.querySelector('.message--typing')", timeout=timeout_ms
            )
        except Exception as exc:  # noqa: BLE001 - always produce case evidence, never crash the whole run.
            error_message = str(exc)
    finally:
        page.remove_listener("request", on_request)

    new_page_error_count = len(page_errors) - page_errors_before
    fields: dict[str, Any] = {
        "request_count": request_count,
        "response_count": response_count,
        "response_status": response_status,
        "typing_count": typing_count(page),
        "terminal_bubble_count": terminal_bubble_count(page),
        "button_disabled": button_disabled(page),
        "new_page_error_count": new_page_error_count,
    }
    if error_message is not None:
        fields["error"] = error_message

    passed = (
        error_message is None
        and request_count >= 1
        and response_count == 1
        and fields["typing_count"] == 0
        and fields["terminal_bubble_count"] >= 1
        and fields["button_disabled"] is False
        and new_page_error_count == 0
    )
    return build_case_record(name, passed=passed, **fields)


def run_double_submit_case(
    page: Any,
    first_text: str,
    second_text: str,
    *,
    timeout_ms: int,
    page_errors: list[str],
) -> dict[str, Any]:
    """UIQ-02/D-04: rapid repeated submit via the textarea/Enter path, not button double-click."""

    page_errors_before = len(page_errors)
    request_count = 0

    def on_request(request: Any) -> None:
        nonlocal request_count
        if "/api/analyze" in request.url:
            request_count += 1

    page.on("request", on_request)
    error_message: str | None = None
    try:
        page.evaluate("() => { window.__uiQuirksTelemetry = { requests: [] }; }")
        page.fill("#message-input", first_text)
        page.press("#message-input", "Enter")
        page.fill("#message-input", second_text)
        page.press("#message-input", "Enter")

        try:
            page.wait_for_function(
                "!document.querySelector('#analyze-button').disabled", timeout=timeout_ms
            )
            page.wait_for_function(
                "!document.querySelector('.message--typing')", timeout=timeout_ms
            )
            page.wait_for_timeout(250)
        except Exception as exc:  # noqa: BLE001 - persist partial evidence, never crash the whole run.
            error_message = str(exc)
    finally:
        page.remove_listener("request", on_request)

    telemetry = page.evaluate("() => window.__uiQuirksTelemetry") or {"requests": []}
    fetch_requests = telemetry.get("requests", [])
    completed = [r for r in fetch_requests if r.get("completed")]
    last_index = len(fetch_requests) - 1 if fetch_requests else -1
    superseded_completed = [r for r in completed if r.get("index") != last_index]
    # Completed responses with a genuine HTTP error status render a legitimate error
    # bubble; anything beyond that among error bubbles is evidence of AbortError
    # leaking through instead of being swallowed silently (demo.js contract).
    legitimate_error_statuses = sum(1 for r in completed if (r.get("status") or 200) >= 400)
    error_dom_count = error_bubble_count(page)

    fields: dict[str, Any] = {
        "request_count": request_count,
        "fetch_request_count": len(fetch_requests),
        "completed_analyze_response_count": len(completed),
        "completed_superseded_response_count": len(superseded_completed),
        "abort_error_bubble_count": max(0, error_dom_count - legitimate_error_statuses),
        "typing_count": typing_count(page),
        "terminal_bubble_count": terminal_bubble_count(page),
        "button_disabled": button_disabled(page),
        "new_page_error_count": len(page_errors) - page_errors_before,
    }
    if error_message is not None:
        fields["error"] = error_message

    passed = (
        error_message is None
        and fields["new_page_error_count"] == 0
        and double_submit_passed(
            completed_analyze_response_count=fields["completed_analyze_response_count"],
            completed_superseded_response_count=fields["completed_superseded_response_count"],
            abort_error_bubble_count=fields["abort_error_bubble_count"],
            typing_count=fields["typing_count"],
            button_disabled=fields["button_disabled"],
        )
    )
    return build_case_record("double_submit", passed=passed, **fields)


# ---------------------------------------------------------------------------
# Browser lifecycle + main.
# ---------------------------------------------------------------------------


def run_browser_verification(
    process: subprocess.Popen[str],
    *,
    port: int,
    headed: bool,
    case_names: list[str],
) -> dict[str, Any]:
    # Lazy import keeps --help and unit tests independent of Playwright/browser availability.
    from playwright.sync_api import sync_playwright

    demo_url = f"http://127.0.0.1:{port}/"
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=not headed)
        try:
            page = browser.new_page()
            console_messages, page_errors = attach_console_capture(page)
            page.add_init_script(DOUBLE_SUBMIT_TELEMETRY_SCRIPT)
            wait_for_server(page, process, demo_url)

            selected = set(case_names)
            cases: list[dict[str, Any]] = []
            for name in CASE_NAMES:
                if name not in selected:
                    continue
                if name == "empty":
                    cases.append(run_empty_case(page, page_errors))
                elif name == "very_long":
                    cases.append(
                        run_text_case(
                            page, "very_long", VERY_LONG_TEXT,
                            timeout_ms=TEXT_CASE_TIMEOUT_MS, page_errors=page_errors,
                        )
                    )
                elif name == "malformed":
                    cases.append(
                        run_text_case(
                            page, "malformed", MALFORMED_TEXT,
                            timeout_ms=TEXT_CASE_TIMEOUT_MS, page_errors=page_errors,
                        )
                    )
                elif name == "mixed_vi_en":
                    cases.append(
                        run_text_case(
                            page, "mixed_vi_en", MIXED_VI_EN_TEXT,
                            timeout_ms=TEXT_CASE_TIMEOUT_MS, page_errors=page_errors,
                        )
                    )
                elif name == "double_submit":
                    cases.append(
                        run_double_submit_case(
                            page, DOUBLE_SUBMIT_FIRST_TEXT, DOUBLE_SUBMIT_SECOND_TEXT,
                            timeout_ms=DOUBLE_SUBMIT_TIMEOUT_MS, page_errors=page_errors,
                        )
                    )
                if name != "double_submit":
                    reset_thread(page)

            return {
                "demo_url": demo_url,
                "cases": cases,
                "console_messages": console_messages,
                "page_errors": page_errors,
            }
        finally:
            browser.close()


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    output_path = build_output_path(args.output)

    process: subprocess.Popen[str] | None = None
    cases: list[dict[str, Any]] = []
    console_messages: list[dict[str, Any]] = []
    page_errors: list[str] = []
    demo_process_info: dict[str, Any] | None = None
    run_error: dict[str, Any] | None = None

    try:
        process = start_demo_server(args.port)
        measurement = run_browser_verification(
            process, port=args.port, headed=args.headed, case_names=args.cases,
        )
        cases = measurement["cases"]
        console_messages = measurement["console_messages"]
        page_errors = measurement["page_errors"]
    except Exception as exc:  # noqa: BLE001 - persist failure evidence, never crash silently.
        run_error = {"message": str(exc), "traceback": traceback.format_exc()}
    finally:
        if process is not None:
            demo_process_info = stop_demo_server(process)

    artifact = build_artifact(
        cases=cases,
        console_messages=console_messages,
        page_errors=page_errors,
        demo_process=demo_process_info,
    )
    if run_error is not None:
        artifact["error"] = run_error
    write_artifact(output_path, artifact)

    print(output_path)
    return 0 if artifact["overall_pass"] and run_error is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
