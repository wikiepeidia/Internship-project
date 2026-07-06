# Phase 31: UI Quirks, Edge Cases & Regression Re-check - Pattern Map

**Mapped:** 2026-07-06  
**Files analyzed:** 12 likely new/modified files  
**Analogs found:** 10 / 12  

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `scripts/verify_ui_quirks.py` | utility/script | request-response + event-driven + file-I/O | `scripts/verify_golden_prompts.py`; `scripts/measure_cold_latency.py` | exact |
| `scripts/verify_golden_prompts.py` (optional extension; prefer rerun only) | utility/script | request-response + file-I/O | `scripts/verify_golden_prompts.py` | exact/self |
| `src/runtime/cli.py` | controller/CLI | request-response | `src/runtime/cli.py` | exact/self |
| `tests/runtime/test_cli.py` | test | request-response | `tests/runtime/test_cli.py` | exact/self |
| `scripts/START_DEMO_UI.bat` | launcher/config | process invocation | none in repo; command analog in `scripts/measure_cold_latency.py` | no local batch analog |
| `scripts/START_TEXT_ANALYZE.bat` | launcher/config | process invocation + stdin/user input | none in repo; command analog in `src/runtime/cli.py` | no local batch analog |
| `tests/runtime/test_ui_quirks_script.py` (optional) | test | file-I/O + transform | `tests/runtime/test_latency_measurement.py` | exact role-match |
| `src/runtime/demo_assets/demo.js` (conditional UIQ-04 only) | component/controller | event-driven + request-response | `src/runtime/demo_assets/demo.js` | exact/self |
| `src/runtime/demo_assets/index.html` (conditional UIQ-04 only) | component/template | event-driven DOM render | `src/runtime/demo_assets/index.html` | exact/self |
| `src/runtime/demo_assets/i18n.js` (conditional UIQ-04 copy only) | config/copy | transform | `src/runtime/demo_assets/i18n.js` | exact/self |
| `src/runtime/demo_assets/demo.css` (conditional UIQ-04 only) | component/style | DOM render/layout | `src/runtime/demo_assets/demo.css` | exact/self |
| `tests/runtime/test_demo.py` (conditional asset/static-contract test updates) | test | request-response + static contract | `tests/runtime/test_demo.py` | exact/self |

## Pattern Assignments

### `scripts/verify_ui_quirks.py` (utility/script, request-response + event-driven + file-I/O)

**Primary analogs:** `scripts/verify_golden_prompts.py`, `scripts/measure_cold_latency.py`

**Imports pattern** (`scripts/verify_golden_prompts.py` lines 5-13):
```python
import argparse
import json
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
```

**Argument/output pattern** (`scripts/measure_cold_latency.py` lines 39-49, 83-91):
```python
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

def build_output_path(...):
    timestamp = (recorded_at or utc_now()).strftime("%Y%m%dT%H%M%SZ")
    return artifact_dir / f"30-latency-{condition}-{run_purpose}-{timestamp}.json"
```

For Phase 31, copy the `--port`, `--output`, `--headed`, timestamped artifact, and `Path` handling. The default artifact should be `.planning/phases/31-ui-quirks-edge-cases-regression-re-check/artifacts/31-ui-quirks-results.json` unless the planner deliberately chooses timestamped files.

**Demo process lifecycle** (`scripts/measure_cold_latency.py` lines 142-179):
```python
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

def wait_for_server(page: Any, process: subprocess.Popen[str], demo_url: str, started_at: float) -> float:
    ...
    page.goto(demo_url, wait_until="domcontentloaded", timeout=2_000)
```

Use this stronger Phase 30 form over `verify_golden_prompts.py` because it captures stdout/stderr and avoids relying on the installed `vnphish` shim.

**Browser submit pattern** (`scripts/measure_cold_latency.py` lines 192-214):
```python
def submit_prompt(page: Any, prompt_name: str, prompt: dict[str, Any], started_at: float) -> dict[str, Any]:
    page.fill("#message-input", prompt["text"])
    page.select_option("#channel-select", prompt["channel"])
    with page.expect_response(lambda response: "/api/analyze" in response.url, timeout=180_000) as response_info:
        page.click("#analyze-button")
    response = response_info.value
    payload = response.json()
    page.wait_for_function("!document.querySelector('#analyze-button').disabled", timeout=5_000)
    ...
    return {
        "prompt": prompt_name,
        "channel": prompt["channel"],
        "risk_tier": payload["risk_tier"],
        "threat_labels": payload["threat_labels"],
        "request_latency_ms": request_latency_ms(response),
    }
```

For UIQ-01, extend the returned case record with response status, final `.message--typing` count, bot/error bubble count, button disabled state, and screenshot path on failure. For UIQ-02, add request counting around `/api/analyze` and trigger re-entry through `form.requestSubmit()`/Enter, not button-only double click.

**Playwright lifecycle pattern** (`scripts/measure_cold_latency.py` lines 217-244):
```python
def run_browser_measurement(...):
    # Lazy import keeps --help and unit tests independent of Playwright/browser availability.
    from playwright.sync_api import sync_playwright

    demo_url = f"http://127.0.0.1:{port}/"
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=not headed)
        try:
            page = browser.new_page()
            page_ready_ms = wait_for_server(page, process, demo_url, started_at)
            results = [submit_prompt(page, name, prompts[name], started_at) for name in prompt_sequence]
            return {"demo_url": demo_url, "page_ready_ms": page_ready_ms, "prompt_results": results}
        finally:
            browser.close()
```

**Failure artifact pattern** (`scripts/measure_cold_latency.py` lines 263-301):
```python
def write_result(path: Path, result: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

...
except Exception as exc:  # noqa: BLE001 - persist failure artifacts for diagnosis.
    result["error"] = {"message": str(exc), "traceback": traceback.format_exc()}
finally:
    if process is not None:
        result["demo_process"] = stop_demo_server(process)
    write_result(output_path, result)
```

No local code currently captures Playwright console/page errors. Add `page.on("console", ...)` and `page.on("pageerror", ...)` in the new verifier only; record them in the JSON artifact for `SOURCE_LANG_VI` triage.

---

### `scripts/verify_golden_prompts.py` (utility/script, request-response + file-I/O)

**Analog:** `scripts/verify_golden_prompts.py`

This file is the baseline to rerun for D-05. Prefer creating `scripts/verify_ui_quirks.py` rather than expanding this file unless the planner explicitly chooses an extension.

**Parser and defaults** (lines 16-40):
```python
DEFAULT_SCAM_TEXT = (...)
DEFAULT_BENIGN_TEXT = (...)
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
```

**Stable verdict loop** (lines 132-146):
```python
def verify_candidate(page: Any, kind: str, text: str, channel: str, runs: int) -> dict[str, Any]:
    candidate_runs: list[dict[str, Any]] = []
    for index in range(runs):
        run = run_once(page, text, channel)
        candidate_runs.append(run)
        print(f"[{kind}] run {index + 1}: risk_tier={run['risk_tier']} labels={run['threat_labels']} latency_ms={run['latency_ms']}")

    verdicts = {(run["risk_tier"], tuple(run["threat_labels"])) for run in candidate_runs}
    stable = len(verdicts) == 1 and all(expected_verdict(kind, run) for run in candidate_runs)
    return {"runs": candidate_runs, "stable": stable}
```

**Apply to:** final regression re-check only. Keep the locked scam/benign expected verdict logic intact.

---

### `src/runtime/cli.py` (controller/CLI, request-response)

**Analog:** `src/runtime/cli.py`

**Imports pattern** (lines 3-15):
```python
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
```

**Parser pattern** (lines 18-47):
```python
def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for the local runtime."""

    parser = argparse.ArgumentParser(prog="vnphish", allow_abbrev=False)
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze_parser = subparsers.add_parser("analyze", help="Analyze one pasted message")
    analyze_parser.add_argument("--text", help="Optional explicit message text for automation")
    ...
    analyze_parser.set_defaults(handler=handle_analyze)

    doctor_parser = subparsers.add_parser("doctor", help="Check local runtime readiness")
    doctor_parser.set_defaults(handler=handle_doctor)

    demo_parser = subparsers.add_parser("demo", help="Start the local demo UI for non-technical verification")
    ...
    demo_parser.set_defaults(handler=handle_demo)
```

For UIQ-03, only add `description=`, clearer `help=`, or `epilog=` text. Do not rename subcommands, add new required flags, or change handler dispatch.

**Handler pattern** (lines 56-88):
```python
def handle_analyze(args: argparse.Namespace) -> int:
    status = run_runtime_doctor()
    if not status.ready:
        print(format_doctor_report(status))
        return 2

    message_text = args.text if args.text is not None else read_message_from_stdin()
    service = build_default_runtime_service()
    ...
    print(render_analysis_result(result))
    return 0

def handle_demo(args: argparse.Namespace) -> int:
    return run_demo_server(host=args.host, port=args.port, open_browser=not args.no_browser)
```

**Main pattern** (lines 91-101):
```python
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

parser = build_parser()
args = parser.parse_args(argv)
return args.handler(args)
```

Keep the Windows UTF-8 stdout guard.

---

### `tests/runtime/test_cli.py` (test, request-response)

**Analog:** `tests/runtime/test_cli.py`

**Module loading pattern** (lines 1-12):
```python
import argparse
import importlib
import io
import sys

from src.runtime.contracts import AnalysisResult, DoctorStatus

def _load_cli_module():
    return importlib.import_module("src.runtime.cli")
```

**Parser contract pattern** (lines 93-101):
```python
def test_cli_only_exposes_analyze_doctor_and_demo_commands():
    cli_module = _load_cli_module()
    parser = cli_module.build_parser()

    subparsers_action = next(
        action for action in parser._actions if isinstance(action, argparse._SubParsersAction)
    )

    assert sorted(subparsers_action.choices.keys()) == ["analyze", "demo", "doctor"]
```

Add help-text tests beside this. Use `parser.format_help()` for root help and `subparsers_action.choices["analyze"].format_help()` / `["demo"].format_help()` for subcommand help. Assert semantic phrases such as text-only/no browser for `analyze` and opens web UI/browser for `demo`.

**Handler monkeypatch pattern** (lines 104-123):
```python
def test_demo_command_starts_local_demo_server(monkeypatch):
    cli_module = _load_cli_module()
    captured = {}

    def fake_run_demo_server(*, host: str, port: int, open_browser: bool) -> int:
        captured["host"] = host
        captured["port"] = port
        captured["open_browser"] = open_browser
        return 0

    monkeypatch.setattr(cli_module, "run_demo_server", fake_run_demo_server)
    exit_code = cli_module.main(["demo", "--host", "127.0.0.1", "--port", "8765", "--no-browser"])
```

Use this style if a launcher smoke test is added in pytest; avoid starting a real server.

---

### `scripts/START_DEMO_UI.bat` (launcher/config, process invocation)

**Analog:** no existing `.bat`, `.cmd`, or `.ps1` files under `scripts/`.

**Closest command source** (`scripts/measure_cold_latency.py` lines 142-145):
```python
[sys.executable, "-m", "src.runtime.cli", "demo", "--no-browser", "--port", str(port)]
```

**Console script source** (`pyproject.toml` lines 42-43):
```toml
[project.scripts]
vnphish = "src.runtime.cli:main"
```

For a double-click launcher, use `python -m src.runtime.cli demo` from the repo root instead of assuming the `vnphish` console script is on `PATH`. If placed directly in `scripts/`, the batch file should `cd /d "%~dp0.."` before invoking Python.

---

### `scripts/START_TEXT_ANALYZE.bat` (launcher/config, process invocation)

**Analog:** no existing `.bat`, `.cmd`, or `.ps1` files under `scripts/`.

**Analyze command behavior** (`src/runtime/cli.py` lines 24-32, 50-74):
```python
analyze_parser = subparsers.add_parser("analyze", help="Analyze one pasted message")
analyze_parser.add_argument("--text", help="Optional explicit message text for automation")
...
message_text = args.text if args.text is not None else read_message_from_stdin()
...
print(render_analysis_result(result))
```

For the text-only launcher, run `python -m src.runtime.cli analyze` from repo root and leave the console open for pasted stdin or use a prompt wrapper. Do not point this launcher at `demo`; its label must make clear that it is terminal/text-only and opens no browser page.

---

### `tests/runtime/test_ui_quirks_script.py` (optional test, file-I/O + transform)

**Analog:** `tests/runtime/test_latency_measurement.py`

**Script module loading pattern** (lines 1-17):
```python
from __future__ import annotations

import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

def _load_module():
    path = Path("scripts/measure_cold_latency.py")
    spec = importlib.util.spec_from_file_location("measure_cold_latency", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module
```

Copy this shape for `scripts/verify_ui_quirks.py`; keep tests focused on pure helpers: argument validation, output path construction, case definitions, latency extraction, and artifact serialization. Do not launch Playwright or the real model from pytest.

**Helper-test pattern** (lines 81-100):
```python
def test_build_output_path_includes_condition_purpose_and_timestamp(tmp_path):
    module = _load_module()
    recorded_at = datetime(2026, 7, 5, 14, 45, tzinfo=timezone.utc)

    output = module.build_output_path(..., artifact_dir=tmp_path)

    assert output == tmp_path / "30-latency-ac-high-performance-evidence-20260705T144500Z.json"
```

---

### `src/runtime/demo_assets/demo.js` (conditional component/controller, event-driven + request-response)

**Analog:** `src/runtime/demo_assets/demo.js`

**State and DOM refs** (lines 1-17):
```javascript
const form = document.getElementById('analysis-form');
const messageInput = document.getElementById('message-input');
const channelSelect = document.getElementById('channel-select');
const analyzeButton = document.getElementById('analyze-button');
...
const history = [];
let currentController = null;
```

**`data-slot` and empty-list rendering** (lines 32-46, 90-115):
```javascript
function createListItems(listNode, values) {
  listNode.replaceChildren();
  if (!values || !values.length) {
    const item = document.createElement('li');
    item.textContent = window.I18N?.LIST_EMPTY ?? 'Không có';
    listNode.append(item);
    return;
  }
  ...
}

article.querySelector('[data-slot="verdict"]').textContent = result.summary;
...
createListItems(article.querySelector('[data-slot="grounded-cues"]'), ...);
createListItems(article.querySelector('[data-slot="recommendations"]'), result.recommendations);
```

**Fetch/error/typing lifecycle** (lines 128-176):
```javascript
async function analyzeMessage(event) {
  event.preventDefault();
  const text = messageInput.value.trim();
  if (!text) return;
  ...
  if (currentController) currentController.abort();
  currentController = new AbortController();
  ...
  const typingEl = appendTypingBubble();

  try {
    const response = await fetch('/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, channel }),
      signal: currentController.signal,
    });
    const payload = await response.json();
    typingEl.remove();
    ...
  } catch (err) {
    typingEl.remove();
    if (err.name !== 'AbortError') {
      appendErrorBubble(...);
    }
  } finally {
    setBusyState(false);
    currentController = null;
  }
}
```

If UIQ-02 fails, the likely local fix is in this region: keep a local `controller` variable per request and only clear busy state/controller in `finally` when that request is still current. Preserve `AbortError` swallowing and `typingEl.remove()`.

**Re-entry path to test** (lines 181-185, 195-199):
```javascript
messageInput.addEventListener('keydown', (event) => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    form.requestSubmit();
  }
});
...
form.requestSubmit();
```

UIQ-02 should exercise this form submit path, not only button double-click.

---

### `src/runtime/demo_assets/index.html` (conditional component/template, event-driven DOM render)

**Analog:** `src/runtime/demo_assets/index.html`

**Composer and required empty-input guard** (lines 46-70):
```html
<form id="analysis-form" class="composer-panel">
  <label class="field-label" for="message-input" data-i18n="INPUT_LABEL">Tin nhắn hoặc đoạn hội thoại đáng ngờ</label>
  <textarea id="message-input" name="text" rows="4"
    placeholder="Dán nội dung cần kiểm tra. Ví dụ: VPBank cảnh báo tài khoản của bạn sẽ bị khóa trong 24h..."
    required></textarea>
  ...
  <button type="submit" id="analyze-button" class="primary-button" data-i18n="ANALYZE_BTN">Phân tích tại máy</button>
</form>
```

**Template contract** (lines 74-150):
```html
<template id="user-message-template">
  ...
  <p class="message__text" data-slot="text"></p>
</template>

<template id="result-template">
  ...
  <h2 data-slot="verdict"></h2>
  <span class="risk-pill" data-slot="risk-tier"></span>
  ...
  <dd data-slot="labels"></dd>
  <dd data-slot="backend"></dd>
  <ul class="detail-list" data-slot="grounded-cues"></ul>
  <ul class="detail-list" data-slot="recommendations"></ul>
</template>
```

Do not add IDs inside cloned template internals. Use `data-slot` only.

**i18n bootstrap pattern** (lines 152-170):
```html
<script>
document.addEventListener('DOMContentLoaded', function () {
  if (!window.I18N) return;
  document.title = window.I18N.PAGE_TITLE;
  document.getElementById('message-input').setAttribute('placeholder', window.I18N.PLACEHOLDER);
  var els = document.querySelectorAll('[data-i18n]');
  ...
});
</script>
<script src="/static/demo.js" defer></script>
```

New user-facing copy belongs in `i18n.js`, not hardcoded template markup.

---

### `src/runtime/demo_assets/i18n.js` (conditional config/copy, transform)

**Analog:** `src/runtime/demo_assets/i18n.js`

**Copy key pattern** (lines 23-35, 47-54):
```javascript
INPUT_LABEL: "Tin nhắn hoặc đoạn hội thoại đáng ngờ",
PLACEHOLDER: "Dán nội dung cần kiểm tra. Ví dụ: VPBank cảnh báo tài khoản của bạn sẽ bị khóa trong 24h...",
...
ANALYZE_BTN: "Phân tích tại máy",
ANALYZE_BTN_BUSY: "Đang phân tích...",
...
ERR_NETWORK: "Không thể kết nối với runtime cục bộ.",
ERR_NETWORK_STEP: "Thử lại sau khi runtime cục bộ đã tải xong.",
TYPING_META: "Đang phân tích",
TYPING_ARIA: "Đang xử lý",
LIST_EMPTY: "Không có",
CLEAR_BTN: "Xóa"
```

If UIQ-04 needs new copy, add a new key here and reference it by `data-i18n` or `window.I18N?.KEY`. Keep Vietnamese-primary wording and avoid hardcoded strings in `index.html` or templates.

---

### `src/runtime/demo_assets/demo.css` (conditional component/style, DOM render/layout)

**Analog:** `src/runtime/demo_assets/demo.css`

**Font and token pattern** (lines 1-8, 110-129):
```css
/* Self-hosted Be Vietnam Pro. Official Google Fonts WOFF2 files are vendored locally; see 29-RESEARCH.md. */
@font-face {
  font-family: 'Be Vietnam Pro';
  font-style: normal;
  font-weight: 400;
  font-display: swap;
  src: url('/static/fonts/be-vietnam-pro-400-vietnamese.woff2') format('woff2');
  unicode-range: ...;
}

:root {
  --surface: #f6f8fb;
  --surface-subtle: #eef3f7;
  --panel: #ffffff;
  ...
  --red-soft: #fde7e4;
}
```

No new hex literals for UIQ-04. Reuse these custom properties.

**Vietnamese line-height and layout containment** (lines 140-149, 255-270, 315-351):
```css
body {
  min-height: 100dvh;
  overflow: hidden;
  font-family: "Be Vietnam Pro", "Segoe UI Variable Display", system-ui, sans-serif;
  font-size: 16px;
  line-height: 1.65;
}

.chat-frame {
  flex: 1 1 0;
  min-height: 0;
}

.message__bubble {
  max-width: min(760px, calc(100% - 46px));
}

.message__text {
  font-size: 1rem;
  line-height: 1.65;
}
```

**Long text and composer constraints** (lines 407-413, 540-554):
```css
textarea {
  min-height: 96px;
  max-height: 28dvh;
  resize: vertical;
  line-height: 1.65;
}

.meta-grid dd {
  overflow-wrap: anywhere;
}

.detail-list {
  line-height: 1.65;
}
```

If long text overflows in a new/touched container, copy the `overflow-wrap: anywhere` treatment rather than inventing a new layout.

---

### `tests/runtime/test_demo.py` (conditional test, request-response + static contract)

**Analog:** `tests/runtime/test_demo.py`

**WSGI test helper** (lines 18-36):
```python
def _call_app(app, *, method: str, path: str, body: bytes = b"", content_type: str = "application/json"):
    status_line: dict[str, str] = {}
    headers_out: dict[str, str] = {}
    environ = {...}
    setup_testing_defaults(environ)
    ...
    response_body = b"".join(app(environ, start_response))
    return status_line["value"], headers_out, response_body
```

**Static HTML/template contract** (lines 39-86):
```python
assert "fonts.googleapis.com" not in html
assert "fonts.gstatic.com" not in html
assert 'id="analysis-form"' in html
assert 'id="result-panel"' in html
assert 'role="log"' in html
assert 'aria-live="polite"' in html
...
assert 'data-slot="risk-tier"' in html
assert 'data-slot="verdict"' in html
assert 'data-slot="labels"' in html
...
for template_id in forbidden_template_ids:
    assert f'id="{template_id}"' not in html
```

If UIQ-04 touches templates, add/adjust assertions here first.

**API contract and error payload** (lines 88-138):
```python
status, headers, body = _call_app(app, method="POST", path="/api/analyze", body=request_body)
payload = json.loads(body.decode("utf-8"))

assert status.startswith("200")
assert headers["Content-Type"].startswith("application/json")
assert payload["risk_tier"] == "high-risk"
...
assert payload["error"]["message"] == "Message text is too short for reliable local analysis."
assert payload["error"]["steps"] == [...]
```

Use these tests to guard the frozen `/api/analyze` response shape; do not change the backend contract for this phase.

## Shared Patterns

### Playwright Verifier Lifecycle

**Source:** `scripts/measure_cold_latency.py` lines 142-179, 217-244  
**Apply to:** `scripts/verify_ui_quirks.py`

Use `sys.executable -m src.runtime.cli demo --no-browser --port`, wait with `page.goto(..., wait_until="domcontentloaded")`, close the browser in `finally`, terminate/kill the subprocess in `finally`, and persist stdout/stderr in the JSON artifact.

### Playwright Response Assertions

**Source:** `scripts/verify_golden_prompts.py` lines 108-122 and `scripts/measure_cold_latency.py` lines 192-214  
**Apply to:** all real-demo verifier cases

Use `page.expect_response(lambda response: "/api/analyze" in response.url, timeout=...)` around the user action, then `response.json()`, then wait for `#analyze-button` to be enabled. Add DOM counts after settle:

```python
typing_count = page.locator(".message--typing").count()
button_disabled = page.locator("#analyze-button").evaluate("node => node.disabled")
```

No existing local code captures console/page errors; add that in the new script and record it, especially for `SOURCE_LANG_VI`.

### CLI Contract

**Source:** `src/runtime/cli.py` lines 18-47; `tests/runtime/test_cli.py` lines 93-101  
**Apply to:** `src/runtime/cli.py`, `tests/runtime/test_cli.py`, launcher docs/evidence

The allowed subcommands remain exactly `analyze`, `demo`, and `doctor`. UIQ-03 is additive wording only: root/subcommand descriptions and help strings.

### UI Template Safety

**Source:** `src/runtime/demo_assets/index.html` lines 74-150; `tests/runtime/test_demo.py` lines 67-83  
**Apply to:** any `index.html`/`demo.js` UIQ-04 fix

Cloned template internals use `data-slot`, not IDs. `tests/runtime/test_demo.py` explicitly forbids old inner IDs such as `result-summary`, `result-risk-tier`, and `error-message`.

### Abort/Re-entry Guard

**Source:** `src/runtime/demo_assets/demo.js` lines 128-176, 181-185  
**Apply to:** `scripts/verify_ui_quirks.py`; conditional `demo.js` fix

Current behavior aborts the previous `currentController`, swallows `AbortError`, removes typing indicators, and clears busy state in `finally`. The verifier must stress the Enter/form submit path because the textarea remains editable while the button is disabled.

### Design Tokens and Long Text

**Source:** `src/runtime/demo_assets/demo.css` lines 110-129, 315-351, 407-413, 540-554  
**Apply to:** conditional `demo.css` UIQ-04 fixes

Use existing CSS custom properties, maintain Vietnamese line-height `1.65`, preserve `max-width` bubble containment, keep textarea `max-height: 28dvh`, and copy `overflow-wrap: anywhere` to any newly affected long-text container.

### Static Backend Contract

**Source:** `src/runtime/demo.py` lines 95-138; `tests/runtime/test_demo.py` lines 88-138  
**Apply to:** all UIQ-04 planning

`POST /api/analyze` parses JSON, validates `text` and `channel`, returns JSON `400` for boundary errors, JSON `503` for runtime unavailable, and JSON `200` with `AnalysisResult.model_dump(mode="json")`. Do not change this shape in Phase 31.

### Regression Re-check Suites

**Source:** `31-CONTEXT.md` D-05 and `31-RESEARCH.md` verification commands  
**Apply to:** final plan verification

Re-run:

```powershell
python scripts\verify_golden_prompts.py --runs 5 --port 8766
python -m pytest tests\runtime\test_local_model.py tests\runtime\test_demo.py tests\runtime\test_cli.py -q
```

Use a non-default port if another demo server is already running.

## No Analog Found

| File/Pattern | Role | Data Flow | Reason |
|--------------|------|-----------|--------|
| `scripts/START_DEMO_UI.bat` | launcher/config | process invocation | No `.bat`, `.cmd`, or `.ps1` scripts exist in `scripts/`; use `python -m src.runtime.cli demo` command source from `scripts/measure_cold_latency.py`. |
| `scripts/START_TEXT_ANALYZE.bat` | launcher/config | process invocation + stdin/user input | No local Windows launcher convention exists; use `src/runtime/cli.py` analyze behavior and `pyproject.toml` console-script mapping as command sources. |
| Playwright console/pageerror capture | verifier behavior | event-driven browser telemetry | No existing script captures console or page errors; implement directly in `scripts/verify_ui_quirks.py` and record JSON evidence. |

## Metadata

**Analog search scope:** `scripts/`, `src/runtime/`, `src/runtime/demo_assets/`, `tests/runtime/`, `.planning/research/`, current Phase 31 artifacts  
**Files scanned:** 185 repo files via `rg --files`  
**Analogs read:** `scripts/verify_golden_prompts.py`, `scripts/measure_cold_latency.py`, `src/runtime/cli.py`, `src/runtime/demo.py`, `src/runtime/demo_assets/demo.js`, `src/runtime/demo_assets/index.html`, `src/runtime/demo_assets/i18n.js`, `src/runtime/demo_assets/demo.css`, `tests/runtime/test_cli.py`, `tests/runtime/test_demo.py`, `tests/runtime/test_latency_measurement.py`, `pyproject.toml`  
**No project-local guidance files:** `AGENTS.md`, `.codex/skills/`, and `.agents/skills/` were not present.  
**Pattern extraction date:** 2026-07-06
