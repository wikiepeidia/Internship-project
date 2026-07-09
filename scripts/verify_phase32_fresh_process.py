"""Verify Phase 32 fresh-process demo readiness through the final .bat launcher."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BAT_PATH = ROOT / "scripts" / "START_DEMO_UI.bat"
PHASE28_GOLDEN_PATH = (
    ROOT
    / ".planning"
    / "phases"
    / "28-baseline-readiness-zero-code-diagnostics"
    / "artifacts"
    / "28-golden-prompt-results.json"
)
DEFAULT_OUTPUT = (
    ROOT
    / ".planning"
    / "phases"
    / "32-fallback-recording-full-dry-rehearsal"
    / "artifacts"
    / "32-fresh-process-dry-run.json"
)
SCHEMA_VERSION = "vnphish.phase32.fresh-process-dry-run.v1"
SCOPE_NOTICE = (
    "fresh-process substitute only; not literal cold-boot coverage for OS, driver, "
    "OneDrive sync, or Windows Defender first-run effects"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--headed", action="store_true", help="Show the Playwright browser window")
    parser.add_argument("--readiness-timeout", type=int, default=180)
    return parser


def load_golden_module() -> Any:
    module_path = ROOT / "scripts" / "verify_golden_prompts.py"
    spec = importlib.util.spec_from_file_location("verify_golden_prompts", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_golden_prompts() -> dict[str, dict[str, str]]:
    module = load_golden_module()
    prompts = {
        "golden_scam": {
            "text": str(module.DEFAULT_SCAM_TEXT),
            "channel": "sms",
            "source": "scripts/verify_golden_prompts.py:DEFAULT_SCAM_TEXT",
        },
        "golden_benign": {
            "text": str(module.DEFAULT_BENIGN_TEXT),
            "channel": "sms",
            "source": "scripts/verify_golden_prompts.py:DEFAULT_BENIGN_TEXT",
        },
    }
    if PHASE28_GOLDEN_PATH.exists():
        data = json.loads(PHASE28_GOLDEN_PATH.read_text(encoding="utf-8"))
        for key in ("golden_scam", "golden_benign"):
            if data[key]["text"] != prompts[key]["text"]:
                raise RuntimeError(f"{key} text differs between Phase 28 artifact and script constant")
            if data[key]["channel"] != prompts[key]["channel"]:
                raise RuntimeError(f"{key} channel differs between Phase 28 artifact and script constant")
            prompts[key]["phase28_artifact"] = str(PHASE28_GOLDEN_PATH.relative_to(ROOT))
    return prompts


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_port_listeners(port: int, netstat_output: str) -> list[int]:
    listeners: set[int] = set()
    suffix_pattern = re.compile(rf":{port}$")
    for line in netstat_output.splitlines():
        parts = line.split()
        if len(parts) < 5 or parts[0].upper() != "TCP":
            continue
        local_address = parts[1]
        state = parts[3].upper()
        pid_text = parts[-1]
        if state != "LISTENING" or not suffix_pattern.search(local_address):
            continue
        if pid_text.isdigit():
            listeners.add(int(pid_text))
    return sorted(listeners)


def stop_port_listeners(port: int) -> list[dict[str, Any]]:
    if os.name != "nt":
        return []
    netstat = subprocess.run(
        ["netstat", "-ano", "-p", "tcp"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    stopped: list[dict[str, Any]] = []
    for pid in parse_port_listeners(port, netstat.stdout):
        result = subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        stopped.append(
            {
                "pid": pid,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        )
    return stopped


def start_launcher() -> subprocess.Popen[str]:
    if not BAT_PATH.exists():
        raise RuntimeError(f"Launcher not found: {BAT_PATH}")
    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    if os.name == "nt":
        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) | getattr(
            subprocess, "CREATE_NO_WINDOW", 0
        )
        return subprocess.Popen(
            ["cmd.exe", "/c", str(BAT_PATH)],
            cwd=str(ROOT),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=creationflags,
            env=env,
        )
    return subprocess.Popen(
        [str(BAT_PATH)],
        cwd=str(ROOT),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )


def stop_launcher(process: subprocess.Popen[str]) -> dict[str, Any]:
    if process.poll() is None:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
        else:
            process.terminate()
    try:
        stdout, stderr = process.communicate(timeout=15)
    except subprocess.TimeoutExpired:
        process.kill()
        stdout, stderr = process.communicate(timeout=15)
    return {"pid": process.pid, "returncode": process.returncode, "stdout": stdout, "stderr": stderr}


def request_latency_ms(response: Any) -> float | None:
    timing_attr = response.request.timing
    timing = timing_attr() if callable(timing_attr) else timing_attr
    try:
        return float(timing["responseEnd"] - timing["requestStart"])
    except (KeyError, TypeError, ValueError):
        return None


def wait_for_server(page: Any, process: subprocess.Popen[str], demo_url: str, timeout: int) -> float:
    deadline = time.monotonic() + timeout
    start = time.monotonic()
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Launcher exited before server was reachable (returncode={process.returncode})")
        try:
            page.goto(demo_url, wait_until="domcontentloaded", timeout=2_000)
            return (time.monotonic() - start) * 1000.0
        except Exception as exc:  # noqa: BLE001 - readiness probe retries transient connection errors.
            last_error = exc
            time.sleep(1)
    raise RuntimeError(f"Demo server was not reachable at {demo_url}") from last_error


def expected_verdict(kind: str, payload: dict[str, Any]) -> bool:
    labels = tuple(payload.get("threat_labels") or [])
    if kind == "golden_scam":
        return payload.get("risk_tier") != "benign" and "bank_impersonation" in labels
    return payload.get("risk_tier") == "benign" and labels == ("benign",)


def submit_prompt(page: Any, *, kind: str, text: str, channel: str) -> dict[str, Any]:
    page.fill("#message-input", text)
    page.select_option("#channel-select", channel)
    with page.expect_response(lambda response: "/api/analyze" in response.url, timeout=180_000) as response_info:
        page.click("#analyze-button")
    response = response_info.value
    payload = response.json()
    page.wait_for_function("!document.querySelector('#analyze-button').disabled", timeout=180_000)
    page.wait_for_function("!document.querySelector('.message--typing')", timeout=180_000)
    if response.status >= 400:
        raise RuntimeError(f"/api/analyze returned HTTP {response.status}: {payload}")
    return {
        "risk_tier": payload["risk_tier"],
        "threat_labels": payload["threat_labels"],
        "latency_ms": request_latency_ms(response),
        "passed": expected_verdict(kind, payload),
    }


def run_browser(args: argparse.Namespace, process: subprocess.Popen[str], prompts: dict[str, dict[str, str]]) -> dict[str, Any]:
    from playwright.sync_api import sync_playwright

    demo_url = f"http://127.0.0.1:{args.port}/"
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=not args.headed)
        try:
            page = browser.new_page()
            console_messages: list[dict[str, Any]] = []
            page_errors: list[str] = []
            page.on("console", lambda msg: console_messages.append({"type": msg.type, "text": msg.text}))
            page.on("pageerror", lambda exc: page_errors.append(str(exc)))
            page_ready_ms = wait_for_server(page, process, demo_url, args.readiness_timeout)
            results = {
                "golden_scam": submit_prompt(
                    page,
                    kind="golden_scam",
                    text=prompts["golden_scam"]["text"],
                    channel=prompts["golden_scam"]["channel"],
                ),
                "golden_benign": submit_prompt(
                    page,
                    kind="golden_benign",
                    text=prompts["golden_benign"]["text"],
                    channel=prompts["golden_benign"]["channel"],
                ),
            }
            return {
                "demo_url": demo_url,
                "page_ready_ms": page_ready_ms,
                "results": results,
                "console_messages": console_messages,
                "page_errors": page_errors,
            }
        finally:
            browser.close()


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output_path = args.output if args.output.is_absolute() else ROOT / args.output
    prompts = load_golden_prompts()
    stopped_before_launch: list[dict[str, Any]] = []
    process: subprocess.Popen[str] | None = None
    launcher_result: dict[str, Any] | None = None
    browser_result: dict[str, Any] = {}
    error: dict[str, Any] | None = None
    started_at = utc_now()

    try:
        stopped_before_launch = stop_port_listeners(args.port)
        process = start_launcher()
        browser_result = run_browser(args, process, prompts)
    except Exception as exc:  # noqa: BLE001 - persist failure evidence for diagnosis.
        error = {"message": str(exc), "traceback": traceback.format_exc()}
    finally:
        if process is not None:
            launcher_result = stop_launcher(process)

    results = browser_result.get("results", {})
    overall_pass = (
        error is None
        and bool(results)
        and all(result.get("passed") is True for result in results.values())
        and not browser_result.get("page_errors")
    )
    payload: dict[str, Any] = {
        "schema": SCHEMA_VERSION,
        "recorded_at": utc_now(),
        "started_at": started_at,
        "overall_pass": overall_pass,
        "scope_notice": SCOPE_NOTICE,
        "launcher": {
            "path": str(BAT_PATH.relative_to(ROOT)),
            "invoked_via": "cmd.exe /c" if os.name == "nt" else "direct",
            "process": launcher_result,
            "stopped_existing_port_listeners": stopped_before_launch,
        },
        "port": args.port,
        "prompt_source": prompts,
        **browser_result,
    }
    if error is not None:
        payload["error"] = error
    write_json(output_path, payload)
    print(output_path)
    return 0 if overall_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
