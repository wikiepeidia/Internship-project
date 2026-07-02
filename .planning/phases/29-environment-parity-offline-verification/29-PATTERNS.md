# Phase 29: Environment Parity & Offline Verification - Pattern Map

**Mapped:** 2026-07-02
**Files analyzed:** 6 (1 route/logic edit, 1 template edit, 1 stylesheet edit, 12 new binary assets treated as 1 group, 1 config edit, 1 test file edit)
**Analogs found:** 5 / 6 (all code/text files have exact self-analogs in the same file; the vendored `.woff2` binaries have no in-repo precedent)

This phase is dominated by small, additive edits to files that already contain the pattern they need to extend (the best analog for each edited file is usually itself, a few lines away). Only one genuinely new code construct is introduced: an allowlisted static-file GET route in `src/runtime/demo.py`. ENV-01 (doctor re-check), ENV-02 (offline runbook), and ENV-04 (`setx` env vars) touch **no source files** — confirmed by reading `src/config/settings.py`, which already implements OS-env-var-over-`.env`-file precedence via `pydantic-settings`' built-in `env_file` mechanism (lines 67-71) — so they are out of scope for this pattern map and are not listed as files-to-modify below.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|----------------|
| `src/runtime/demo.py` (add font route) | route | request-response / file-I/O | itself — existing static routes, same file, lines 60-67 | exact (self-pattern) |
| `src/runtime/demo_assets/fonts/*.woff2` (12 new binary files) | asset (static binary) | file-I/O | none in-repo | none |
| `src/runtime/demo_assets/index.html` (remove CDN `<link>` lines) | component (template) | request-response | itself — same file, lines 4-15 | exact (self-pattern) |
| `src/runtime/demo_assets/demo.css` (add `@font-face` block) | component (stylesheet) | request-response | itself — same file, lines 1-40 | exact (self-pattern) |
| `pyproject.toml` (tighten `llama-cpp-python` pin) | config | batch (dependency resolution) | itself — same file, `optional-dependencies` block, lines 28-40 | exact (self-pattern) |
| `tests/runtime/test_demo.py` (add font-route test + fix stale CDN assertion) | test | request-response | itself — `test_demo_static_assets_are_served`, lines 142-156, and `_call_app`, lines 18-36 | exact (self-pattern) |
| `.env/.env` (optional: add a one-line comment above the two model-path keys) | config | n/a | none — manual comment only, no code pattern | none (see note below) |

## Pattern Assignments

### `src/runtime/demo.py` (route, request-response / file-I/O)

**Analog:** itself — `DemoApp.__call__`'s existing hardcoded static-asset routes.

This file has **no generic static-file handler**; every asset path is an exact-match route. The new font route must follow this same exact-match style, not introduce a path-join/catch-all.

**Imports pattern** (lines 1-16):
```python
"""Local demo UI server for the Phase 6 non-technical verification flow."""

from __future__ import annotations

import json
import webbrowser
from pathlib import Path
from typing import Callable, get_args
from wsgiref.simple_server import make_server

from src.runtime.contracts import ChannelName
from src.runtime.service import (
    RuntimeBoundaryError,
    RuntimeUnavailableError,
    build_default_runtime_service,
)


ASSET_DIR = Path(__file__).with_name("demo_assets")
```
No new imports are needed for the font route (`ASSET_DIR / "fonts" / filename` and the existing `_text_response` helper cover it).

**Existing response helpers to reuse as-is** (lines 22-47):
```python
def _json_response(start_response: Callable, status: str, payload: dict[str, object]) -> list[bytes]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    start_response(
        status,
        [
            ("Content-Type", "application/json; charset=utf-8"),
            ("Content-Length", str(len(body))),
            ("Cache-Control", "no-store"),
        ],
    )
    return [body]


def _text_response(start_response: Callable, status: str, content_type: str, body: bytes) -> list[bytes]:
    start_response(
        status,
        [
            ("Content-Type", content_type),
            ("Content-Length", str(len(body))),
        ],
    )
    return [body]


def _load_asset(name: str) -> bytes:
    return (ASSET_DIR / name).read_bytes()
```
`_text_response` is generic over content type and already used for `text/html`, `text/css`, and `application/javascript` — it is the right helper for `font/woff2` bodies too. `_load_asset` only takes a bare filename relative to `ASSET_DIR`; the new route needs its own `FONT_DIR = ASSET_DIR / "fonts"` plus an allowlist check, since `_load_asset` performs no traversal protection (it's currently safe only because every caller passes a hardcoded literal string, never request-derived input).

**Core routing pattern to extend** (`DemoApp.__call__`, lines 56-71):
```python
    def __call__(self, environ, start_response):
        method = environ.get("REQUEST_METHOD", "GET").upper()
        path = environ.get("PATH_INFO", "/") or "/"

        if method == "GET" and path == "/":
            return _text_response(start_response, "200 OK", "text/html; charset=utf-8", _load_asset("index.html"))
        if method == "GET" and path == "/static/demo.css":
            return _text_response(start_response, "200 OK", "text/css; charset=utf-8", _load_asset("demo.css"))
        if method == "GET" and path == "/static/demo.js":
            return _text_response(start_response, "200 OK", "application/javascript; charset=utf-8", _load_asset("demo.js"))
        if method == "GET" and path == "/static/i18n.js":
            return _text_response(start_response, "200 OK", "application/javascript; charset=utf-8", _load_asset("i18n.js"))
        if method == "POST" and path == "/api/analyze":
            return self._handle_analyze(environ, start_response)

        return _json_response(start_response, "404 Not Found", {"error": {"message": "Not found", "steps": []}})
```
The new font route is a new `if` branch inserted alongside the other `GET`/exact-path branches (before the final fallthrough `return _json_response(..., "404 Not Found", ...)` on line 71), using an allowlist instead of a single hardcoded path — this is the one place this phase departs from pure copy-paste, because 12 filenames (not 1) share the same route prefix. RESEARCH.md's Pattern 2 has the exact recommended code (allowlist `frozenset`, `path.removeprefix("/static/fonts/")`, membership check before any `Path` construction) — copy that block verbatim; it already matches this file's helper signatures with zero changes needed to `_text_response`/`_json_response`.

**Error handling pattern:** This file has no try/except in routing — invalid/unknown paths simply fall through to the shared 404 branch (line 71). The font route must do the same: an unlisted filename returns the same `_json_response(..., "404 Not Found", {"error": {"message": "Not found", "steps": []}})` shape used everywhere else in this file, not a bespoke error format.

---

### `src/runtime/demo_assets/index.html` (component/template, request-response)

**Analog:** itself — the file being edited; only the CDN font `<link>` lines are removed, nothing else in the `<head>` changes.

**Current head block, showing what to remove vs. preserve** (lines 4-15):
```html
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <title>VN Phishing Detection Demo</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link
    href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700&display=swap"
    rel="stylesheet">
  <link rel="stylesheet" href="/static/demo.css">
  <script src="/static/i18n.js"></script>
</head>
```
Lines 8, 9, 11 (the two `preconnect` tags and the `css2` stylesheet link, spanning lines 10-12 as one `<link>` element) are the only lines to delete. Line 13 (`<link rel="stylesheet" href="/static/demo.css">`) and line 14 (`<script src="/static/i18n.js"></script>`) are unrelated existing local-asset references and must be left exactly as-is — the `@font-face` rules live in `demo.css`, which is already linked here, so no new `<link>`/`<script>` tag needs to be added to `index.html` at all for this fix.

---

### `src/runtime/demo_assets/demo.css` (component/stylesheet, request-response)

**Analog:** itself — new `@font-face` block is inserted at the top; the existing font-family consumer reference is untouched.

**Insertion point — top of file, before `:root`** (lines 1-20 currently):
```css
:root {
  --surface: #f6f8fb;
  --surface-subtle: #eef3f7;
  --panel: #ffffff;
  ...
  --shadow: 0 18px 44px rgba(20, 34, 51, 0.12);
}
```
RESEARCH.md's Pattern 3 has the full 12-block `@font-face` CSS (4 weights × 3 unicode-range subsets, with exact URLs matching the allowlist filenames from the `demo.py` route) — insert it verbatim above this `:root` block.

**Existing consumer reference — do not touch** (line 37):
```css
  font-family: "Be Vietnam Pro", "Segoe UI Variable Display", system-ui, sans-serif;
```
`@font-face` is resolved by `font-family` name at render time, not by declaration order or import location, so this line needs zero changes — it will pick up the new local `@font-face` sources automatically once they exist earlier in the same stylesheet.

---

### `pyproject.toml` (config, batch/dependency-resolution)

**Analog:** itself — the sibling `dev`/`train` extras show the same list-of-version-specifier pattern already used for `runtime`.

**Current block to edit** (lines 28-40):
```toml
[project.optional-dependencies]
dev = [
    "pytest>=9.0",
]
train = [
    "torch>=2.4",
    "transformers>=4.45",
    "accelerate>=0.33",
    "peft>=0.12",
]
runtime = [
    "llama-cpp-python>=0.3",
]
```
Change only the `runtime` list's single entry from `"llama-cpp-python>=0.3"` to `"llama-cpp-python==0.3.23"`. Nothing else in this file needs to change (per ENV-05 Scope Resolution in RESEARCH.md — no reinstall, no venv rebuild).

---

### `tests/runtime/test_demo.py` (test, request-response)

**Analog:** `test_demo_static_assets_are_served` (same file, lines 142-156) for the new font-route test; `_call_app` (same file, lines 18-36) is the shared WSGI test harness both tests must use.

**Test harness to reuse unchanged** (lines 18-36):
```python
def _call_app(app, *, method: str, path: str, body: bytes = b"", content_type: str = "application/json"):
    status_line: dict[str, str] = {}
    headers_out: dict[str, str] = {}

    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "CONTENT_TYPE": content_type,
        "CONTENT_LENGTH": str(len(body)),
        "wsgi.input": io.BytesIO(body),
    }
    setup_testing_defaults(environ)

    def start_response(status, headers):
        status_line["value"] = status
        headers_out.update(dict(headers))

    response_body = b"".join(app(environ, start_response))
    return status_line["value"], headers_out, response_body
```

**Closest existing test to model the new one on** (lines 142-156):
```python
def test_demo_static_assets_are_served():
    demo_module = _load_demo_module()
    app = demo_module.build_demo_app(service=object())

    status, headers, body = _call_app(app, method="GET", path="/static/demo.css")

    assert status.startswith("200")
    assert headers["Content-Type"].startswith("text/css")
    css = body.decode("utf-8")
    assert "Be Vietnam Pro" in css
    assert "100dvh" in css
    assert "min-height: 0" in css
    assert "flex: 1 1 0" in css
    assert "env(safe-area-inset-bottom)" in css
    assert "prefers-reduced-motion" in css
```
RESEARCH.md's Pattern 2 already provides the exact new test body (`test_demo_font_assets_are_served`, asserting `200`, `Content-Type: font/woff2`, non-empty `body`) — add it as a new function in this same file, following this test's structure (build app, `_call_app`, assert on status/headers/body).

**CRITICAL — a pre-existing assertion in this same file will break and must be updated as part of this phase's change, not left as a surprise regression:**

`test_demo_index_serves_text_only_form` (line 48) currently asserts:
```python
    assert "Be+Vietnam+Pro" in html or "Be Vietnam Pro" in html
```
This passes today only because `index.html`'s raw HTML contains the literal CDN URL substring `Be+Vietnam+Pro` (line 11). Once the CDN `<link>` lines are deleted from `index.html` (per the `index.html` pattern assignment above), `index.html`'s raw HTML no longer contains either substring — `demo.css` does (line 37), but that's a separate file/response, not part of the `GET /` HTML body this test inspects. This assertion will fail after the ENV-03 fix unless the planner either (a) removes/relaxes it, since checking for the font family name in the HTML was really a proxy for "the CDN link is present" and that proxy is now inverted, or (b) points it at the served `demo.css` response instead (matching the pattern already used in `test_demo_static_assets_are_served` above, which does check `demo.css` for `"Be Vietnam Pro"`). Flag this explicitly in the plan for `tests/runtime/test_demo.py` — do not let it be discovered only at test-run time.

---

## Shared Patterns

### WSGI Exact-Match Static Route (the core reusable mechanism for this whole phase)
**Source:** `src/runtime/demo.py`, lines 56-71 (`DemoApp.__call__`)
**Apply to:** The new font-serving route.
```python
if method == "GET" and path == "/static/demo.css":
    return _text_response(start_response, "200 OK", "text/css; charset=utf-8", _load_asset("demo.css"))
```
Every existing static asset in this app is served by one `if method == "GET" and path == "<exact string>"` branch calling `_text_response`. The font route is the same shape, just with a membership check (`filename in KNOWN_FONT_FILES`) standing in for the exact-string match, because it covers 12 files under one path prefix instead of 1 file at one exact path.

### Allowlist-Before-Filesystem-Access (security-relevant, new to this codebase)
**Source:** RESEARCH.md Pattern 2 / Pitfall 7 (no existing in-repo precedent — this is a new control this phase introduces)
**Apply to:** The new font route only.
```python
KNOWN_FONT_FILES = frozenset({
    "be-vietnam-pro-400-vietnamese.woff2",
    # ... 11 more, one per weight x subset
})
if method == "GET" and path.startswith("/static/fonts/"):
    filename = path.removeprefix("/static/fonts/")
    if filename in KNOWN_FONT_FILES:
        return _text_response(start_response, "200 OK", "font/woff2", (FONT_DIR / filename).read_bytes())
    return _json_response(start_response, "404 Not Found", {"error": {"message": "Not found", "steps": []}})
```
No other route in this file currently constructs a filesystem path from request-derived input (`_load_asset` is always called with a hardcoded literal), so this allowlist pattern has no precedent to copy from elsewhere in the codebase — treat RESEARCH.md's Pattern 2 as the canonical source, not any existing file.

### Config List Edit (exact-pin syntax)
**Source:** `pyproject.toml`, lines 38-40 (`runtime` extra)
**Apply to:** The `llama-cpp-python` version bump only — same list, same syntax, no structural change.

### WSGI Test Harness
**Source:** `tests/runtime/test_demo.py`, lines 18-36 (`_call_app`)
**Apply to:** The new font-route test — reuse `_call_app` and `_load_demo_module`/`build_demo_app(service=object())` exactly as the other static-asset tests do (the font route doesn't touch `self.service`, so a bare `object()` stand-in is sufficient, matching `test_demo_static_assets_are_served` and `test_demo_i18n_js_is_served`).

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `src/runtime/demo_assets/fonts/*.woff2` (12 files) | asset (static binary) | file-I/O | No binary static asset exists anywhere in this repo today to pattern-match against (`demo_assets/` currently holds only `.html`/`.css`/`.js` text files). There is no "vendoring" code pattern to copy — this is a one-time fetch-and-place operation. RESEARCH.md's "Code Examples > Fetching the official Be Vietnam Pro `.woff2` files" section is the authoritative source for the exact `curl` commands and target filenames (matching the `KNOWN_FONT_FILES` allowlist above); the planner should treat that RESEARCH.md section as the direct instruction set, not search for an in-repo analog that doesn't exist. |
| `.env/.env` (optional 1-line comment addition) | config | n/a | No code pattern applies — this is a manual, human-reviewed text comment (per RESEARCH.md Pitfall 4's suggested mitigation: note above the two model-path keys that they're superseded by permanent OS-level `setx` vars). This file is gitignored and contains unrelated secrets (Anthropic/OpenRouter/DeepSeek API keys per CONTEXT.md); the planner/executor must not read, log, or dump its full contents — if this edit is included at all, it should be a targeted, minimal insertion (e.g., via a small script or manual instruction), never a full-file read-and-rewrite. |

## Metadata

**Analog search scope:** `src/runtime/demo.py`, `src/runtime/demo_assets/{index.html,demo.css,demo.js,i18n.js}`, `tests/runtime/test_demo.py`, `pyproject.toml`, `src/config/settings.py` (read to confirm ENV-04 needs no code change).
**Files scanned:** 7 read in full (all ≤ 566 lines; single non-overlapping `Read` call each), plus 2 `Grep` sweeps (binary-serving precedent search across `src/`, `llama-cpp-python` reference search repo-wide) to confirm no existing analog for the font-binary-serving and dependency-pin patterns.
**Pattern extraction date:** 2026-07-02
