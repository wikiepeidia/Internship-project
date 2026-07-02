"""Verify Phase 28 golden prompts through the real local demo UI."""

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


DEFAULT_SCAM_TEXT = (
    "【VIETCOMBANK】 Tai khoan cua ban vua bi truy cap tu thiet bi la luc 03:47 SA. "
    "Neu ko phai ban, bam vao link de khoa ngay: http://vcb-secure-alert.net/lock?id=9182736 "
    "hoac goi 1800.9999 (mien phi)."
)
DEFAULT_BENIGN_TEXT = (
    "VPBank Smart OTP: Mã xác thực của bạn là 847291. "
    "Mã này có hiệu lực trong 90 giây để xác nhận đăng nhập Internet Banking. "
    "Tuyệt đối KHÔNG chia sẻ mã này với bất kỳ ai, kể cả nhân viên ngân hàng."
)
RESULTS_PATH = Path(
    ".planning/phases/28-baseline-readiness-zero-code-diagnostics/artifacts/"
    "28-golden-prompt-results.json"
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scam-text", default=DEFAULT_SCAM_TEXT)
    parser.add_argument("--scam-channel", default="sms")
    parser.add_argument("--benign-text", default=DEFAULT_BENIGN_TEXT)
    parser.add_argument("--benign-channel", default="sms")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--runs", type=int, default=5)
    return parser


def new_results(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "golden_scam": {
            "text": args.scam_text,
            "channel": args.scam_channel,
            "runs": [],
            "stable": False,
        },
        "golden_benign": {
            "text": args.benign_text,
            "channel": args.benign_channel,
            "runs": [],
            "stable": False,
        },
        "recorded": datetime.now(timezone.utc).isoformat(),
    }


def write_results(results: dict[str, Any]) -> None:
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def start_demo_server(port: int) -> subprocess.Popen[bytes]:
    return subprocess.Popen(
        ["vnphish", "demo", "--no-browser", "--port", str(port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def stop_demo_server(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)


def wait_for_server(page: Any, process: subprocess.Popen[bytes], demo_url: str) -> None:
    last_error: Exception | None = None
    for _ in range(30):
        if process.poll() is not None:
            raise RuntimeError("vnphish demo exited before the script-owned server became reachable.")
        try:
            page.goto(demo_url, wait_until="domcontentloaded", timeout=2_000)
            return
        except Exception as exc:  # noqa: BLE001 - readiness probe must retry transient connection errors.
            last_error = exc
            time.sleep(1)
    raise RuntimeError(f"Demo server was not reachable at {demo_url}") from last_error


def request_latency_ms(response: Any) -> float | None:
    timing_attr = response.request.timing
    timing = timing_attr() if callable(timing_attr) else timing_attr
    try:
        return float(timing["responseEnd"] - timing["requestStart"])
    except (KeyError, TypeError, ValueError):
        return None


def run_once(page: Any, text: str, channel: str) -> dict[str, Any]:
    page.fill("#message-input", text)
    page.select_option("#channel-select", channel)
    with page.expect_response(lambda response: "/api/analyze" in response.url) as response_info:
        page.click("#analyze-button")
    response = response_info.value
    payload = response.json()
    page.wait_for_function("!document.querySelector('#analyze-button').disabled", timeout=2_000)
    if response.status >= 400:
        raise RuntimeError(f"/api/analyze returned HTTP {response.status}: {payload}")
    return {
        "risk_tier": payload["risk_tier"],
        "threat_labels": payload["threat_labels"],
        "latency_ms": request_latency_ms(response),
    }


def expected_verdict(kind: str, run: dict[str, Any]) -> bool:
    labels = tuple(run["threat_labels"])
    if kind == "golden_scam":
        return run["risk_tier"] != "benign" and "bank_impersonation" in labels
    return run["risk_tier"] == "benign" and labels == ("benign",)


def verify_candidate(page: Any, kind: str, text: str, channel: str, runs: int) -> dict[str, Any]:
    candidate_runs: list[dict[str, Any]] = []
    for index in range(runs):
        run = run_once(page, text, channel)
        candidate_runs.append(run)
        print(
            f"[{kind}] run {index + 1}: "
            f"risk_tier={run['risk_tier']} labels={run['threat_labels']} "
            f"latency_ms={run['latency_ms']}"
        )

    verdicts = {(run["risk_tier"], tuple(run["threat_labels"])) for run in candidate_runs}
    stable = len(verdicts) == 1 and all(expected_verdict(kind, run) for run in candidate_runs)
    print(f"[{kind}] STABLE={stable} verdicts={sorted(verdicts)}")
    return {"runs": candidate_runs, "stable": stable}


def run_browser_verification(args: argparse.Namespace, results: dict[str, Any]) -> None:
    # Lazy import follows the scraper convention; unlike scraping, verification must fail loudly.
    from playwright.sync_api import sync_playwright

    demo_url = f"http://127.0.0.1:{args.port}/"
    process = start_demo_server(args.port)
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                wait_for_server(page, process, demo_url)
                scam = verify_candidate(page, "golden_scam", args.scam_text, args.scam_channel, args.runs)
                results["golden_scam"].update(scam)
                write_results(results)
                benign = verify_candidate(
                    page,
                    "golden_benign",
                    args.benign_text,
                    args.benign_channel,
                    args.runs,
                )
                results["golden_benign"].update(benign)
            finally:
                browser.close()
    finally:
        stop_demo_server(process)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.runs < 1:
        raise SystemExit("--runs must be >= 1")

    results = new_results(args)
    try:
        run_browser_verification(args, results)
    except Exception as exc:  # noqa: BLE001 - write the failure artifact, then surface nonzero.
        results["error"] = str(exc)
        results["traceback"] = traceback.format_exc()
        write_results(results)
        print(results["traceback"], file=sys.stderr)
        return 1

    write_results(results)
    if results["golden_scam"]["stable"] and results["golden_benign"]["stable"]:
        return 0

    print(json.dumps(results, ensure_ascii=False, indent=2), file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
