"""Measure Phase 30 cold-start latency through the real local demo UI."""

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


PROMPTS_PATH = Path(
    ".planning/phases/28-baseline-readiness-zero-code-diagnostics/artifacts/"
    "28-golden-prompt-results.json"
)
ARTIFACT_DIR = Path(".planning/phases/30-latency-diagnosis-targeted-fix/artifacts")
CONDITIONS = ("ac-high-performance", "battery-balanced", "diagnostic")
RUN_PURPOSES = ("diagnostic", "evidence")
PROMPT_NAMES = ("scam", "benign")
SCHEMA_VERSION = "vnphish.phase30.cold-latency.v1"


def parse_prompt_sequence(value: str) -> list[str]:
    """Parse a comma-separated prompt sequence."""

    prompts = [part.strip().casefold() for part in value.split(",") if part.strip()]
    if not prompts:
        raise argparse.ArgumentTypeError("at least one prompt name is required")
    unknown = sorted(set(prompts) - set(PROMPT_NAMES))
    if unknown:
        raise argparse.ArgumentTypeError(f"unknown prompt name(s): {', '.join(unknown)}")
    return prompts


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--condition", choices=CONDITIONS, default="diagnostic")
    parser.add_argument("--run-purpose", choices=RUN_PURPOSES, default="diagnostic")
    parser.add_argument("--post-reboot-confirmed", action="store_true")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--headed", action="store_true", help="Show the browser window instead of headless Chromium")
    parser.add_argument("--prompts", type=parse_prompt_sequence, default=parse_prompt_sequence("scam,benign"))
    parser.add_argument("--prompts-path", type=Path, default=PROMPTS_PATH)
    return parser


def validate_args(args: argparse.Namespace) -> None:
    """Fail closed when a run is labelled as evidence but lacks required proof flags."""

    if args.run_purpose == "evidence" and not args.post_reboot_confirmed:
        raise ValueError("--post-reboot-confirmed is required when --run-purpose evidence is used")
    if args.run_purpose == "evidence" and args.condition == "diagnostic":
        raise ValueError("--condition must be ac-high-performance or battery-balanced for evidence runs")


def load_locked_prompts(path: Path = PROMPTS_PATH) -> dict[str, dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        "scam": {
            "text": data["golden_scam"]["text"],
            "channel": data["golden_scam"]["channel"],
            "expected_risk_tier": "high-risk",
            "expected_labels": ["bank_impersonation"],
        },
        "benign": {
            "text": data["golden_benign"]["text"],
            "channel": data["golden_benign"]["channel"],
            "expected_risk_tier": "benign",
            "expected_labels": ["benign"],
        },
    }


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def build_output_path(
    condition: str,
    run_purpose: str,
    *,
    recorded_at: datetime | None = None,
    artifact_dir: Path = ARTIFACT_DIR,
) -> Path:
    timestamp = (recorded_at or utc_now()).strftime("%Y%m%dT%H%M%SZ")
    return artifact_dir / f"30-latency-{condition}-{run_purpose}-{timestamp}.json"


def command_output(command: list[str], timeout: int = 8) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
        return {
            "command": command,
            "returncode": completed.returncode,
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
        }
    except Exception as exc:  # noqa: BLE001 - diagnostics should record failures, not crash the measurement.
        return {"command": command, "error": str(exc)}


def collect_power_info() -> dict[str, Any]:
    return {
        "power_scheme": command_output(["powercfg", "/GETACTIVESCHEME"]),
        "last_boot_time": command_output(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "(Get-CimInstance Win32_OperatingSystem).LastBootUpTime.ToString('o')",
            ]
        ),
    }


def elapsed_ms(started_at: float) -> float:
    return (time.perf_counter() - started_at) * 1000.0


def request_latency_ms(response: Any) -> float | None:
    timing_attr = response.request.timing
    timing = timing_attr() if callable(timing_attr) else timing_attr
    try:
        return float(timing["responseEnd"] - timing["requestStart"])
    except (KeyError, TypeError, ValueError):
        return None


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
    return {
        "returncode": process.returncode,
        "stdout": stdout,
        "stderr": stderr,
    }


def wait_for_server(page: Any, process: subprocess.Popen[str], demo_url: str, started_at: float) -> float:
    last_error: Exception | None = None
    for _ in range(90):
        if process.poll() is not None:
            raise RuntimeError("vnphish demo exited before the measurement-owned server became reachable")
        try:
            page.goto(demo_url, wait_until="domcontentloaded", timeout=2_000)
            return elapsed_ms(started_at)
        except Exception as exc:  # noqa: BLE001 - readiness probe must retry transient connection errors.
            last_error = exc
            time.sleep(1)
    raise RuntimeError(f"Demo server was not reachable at {demo_url}") from last_error


def verdict_matches(prompt_name: str, payload: dict[str, Any], prompt: dict[str, Any]) -> bool:
    labels = list(payload.get("threat_labels", []))
    expected_labels = prompt["expected_labels"]
    if prompt_name == "scam":
        return payload.get("risk_tier") == prompt["expected_risk_tier"] and all(
            label in labels for label in expected_labels
        )
    return payload.get("risk_tier") == prompt["expected_risk_tier"] and labels == expected_labels


def submit_prompt(page: Any, prompt_name: str, prompt: dict[str, Any], started_at: float) -> dict[str, Any]:
    page.fill("#message-input", prompt["text"])
    page.select_option("#channel-select", prompt["channel"])
    with page.expect_response(lambda response: "/api/analyze" in response.url, timeout=180_000) as response_info:
        page.click("#analyze-button")
    response = response_info.value
    payload = response.json()
    page.wait_for_function("!document.querySelector('#analyze-button').disabled", timeout=5_000)
    if response.status >= 400:
        raise RuntimeError(f"/api/analyze returned HTTP {response.status}: {payload}")
    if not verdict_matches(prompt_name, payload, prompt):
        raise RuntimeError(
            f"{prompt_name} prompt returned unexpected verdict: "
            f"risk_tier={payload.get('risk_tier')} labels={payload.get('threat_labels')}"
        )
    return {
        "prompt": prompt_name,
        "channel": prompt["channel"],
        "risk_tier": payload["risk_tier"],
        "threat_labels": payload["threat_labels"],
        "request_latency_ms": request_latency_ms(response),
        "total_elapsed_ms_at_answer": elapsed_ms(started_at),
    }


def run_browser_measurement(
    process: subprocess.Popen[str],
    prompts: dict[str, dict[str, Any]],
    prompt_sequence: list[str],
    *,
    port: int,
    headed: bool,
    started_at: float,
) -> dict[str, Any]:
    # Lazy import keeps --help and unit tests independent of Playwright/browser availability.
    from playwright.sync_api import sync_playwright

    demo_url = f"http://127.0.0.1:{port}/"
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=not headed)
        try:
            page = browser.new_page()
            page_ready_ms = wait_for_server(page, process, demo_url, started_at)
            results = [submit_prompt(page, name, prompts[name], started_at) for name in prompt_sequence]
            return {
                "demo_url": demo_url,
                "page_ready_ms": page_ready_ms,
                "first_answer_prompt": results[0]["prompt"],
                "total_to_first_answer_ms": results[0]["total_elapsed_ms_at_answer"],
                "prompt_results": results,
            }
        finally:
            browser.close()


def base_result(args: argparse.Namespace, recorded_at: datetime) -> dict[str, Any]:
    return {
        "schema": SCHEMA_VERSION,
        "recorded_at": recorded_at.isoformat(),
        "condition": args.condition,
        "run_purpose": args.run_purpose,
        "post_reboot_confirmed": bool(args.post_reboot_confirmed),
        "port": args.port,
        "prompt_sequence": args.prompts,
        "power_info": collect_power_info(),
        "measurement": None,
        "demo_process": None,
        "error": None,
    }


def write_result(path: Path, result: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        validate_args(args)
    except ValueError as exc:
        parser.error(str(exc))

    recorded_at = utc_now()
    output_path = args.output or build_output_path(args.condition, args.run_purpose, recorded_at=recorded_at)
    result = base_result(args, recorded_at)
    prompts = load_locked_prompts(args.prompts_path)

    process: subprocess.Popen[str] | None = None
    started_at = time.perf_counter()
    try:
        process = start_demo_server(args.port)
        result["measurement"] = run_browser_measurement(
            process,
            prompts,
            args.prompts,
            port=args.port,
            headed=args.headed,
            started_at=started_at,
        )
    except Exception as exc:  # noqa: BLE001 - persist failure artifacts for diagnosis.
        result["error"] = {"message": str(exc), "traceback": traceback.format_exc()}
    finally:
        if process is not None:
            result["demo_process"] = stop_demo_server(process)
        write_result(output_path, result)

    print(output_path)
    return 0 if result["error"] is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
