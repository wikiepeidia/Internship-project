# Phase 28: Baseline Readiness & Zero-Code Diagnostics - Pattern Map

**Mapped:** 2026-07-02
**Files analyzed:** 3 (this phase is verification-only; `src/runtime/**` is frozen/read-only — no production files are modified)
**Analogs found:** 3 / 3

## Scope Note

Phase 28 is explicitly zero-code for the runtime itself (per RESEARCH.md: "no new tooling is built here" beyond a small verification script). No files under `src/runtime/`, `src/data_pipeline/`, or `src/config/` are created or modified. The only new artifacts are:

1. A throwaway Playwright script that drives the real web demo to lock the two golden prompts (GOLD-01/02) and capture warm latency (DIAG-03).
2. A written record of results (golden prompts locked, doctor/analyze pass confirmations, latency reading) for the phase's own SUMMARY/verification trail.

Both are classified and mapped below.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|----------------|
| `scripts/verify_golden_prompts.py` (or equivalent throwaway script path chosen by planner, e.g. under phase artifacts dir) | script/utility (browser automation) | event-driven (drives browser, intercepts one `fetch` response per run) + request-response | `src/data_pipeline/scraper/ncsc_scraper.py::_fetch_with_playwright` (lines 51-62) | role-match (same `sync_playwright` launch/close pattern; different purpose — scraping vs. verification) |
| `.planning/phases/28-baseline-readiness-zero-code-diagnostics/artifacts/golden-prompts.md` (or `.json`) — written record of locked prompts, stability results, latency reading | config/documentation (file-I/O, write-once artifact) | file-I/O (structured write, no read-modify-write) | `data/manifests/phase5-release-eval-phase5-recovered-balanced-val.json` (structure) + prior phase `*-SUMMARY.md` files (narrative convention, e.g. `.planning/phases/22-.../22-01-SUMMARY.md`) | role-match |
| DOM/API contract the script must drive (`#message-input`, `#channel-select`, `#analyze-button`, `/api/analyze` JSON response) — **read-only reference, not modified** | test fixture / contract reference | request-response | `tests/runtime/test_demo.py` (lines 39-116) | exact (same DOM ids and JSON payload shape the script must exercise) |

## Pattern Assignments

### `scripts/verify_golden_prompts.py` (script, browser-driven event/request-response)

**Analog:** `src/data_pipeline/scraper/ncsc_scraper.py::_fetch_with_playwright`

**Imports pattern** (`ncsc_scraper.py` lines 51-54):
```python
def _fetch_with_playwright(self, url: str) -> Optional[BeautifulSoup]:
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
```
Note the project convention: `sync_playwright` is imported **lazily inside the function**, not at module top-level — follow this same lazy-import style in the new script (keeps Playwright an optional/dev-only dependency for anything that imports the module without exercising the browser path).

**Core launch/close pattern** (`ncsc_scraper.py` lines 54-60):
```python
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(url, wait_until="networkidle", timeout=30000)
    html = page.content()
    browser.close()
```
Apply directly: `p.chromium.launch(headless=True)`, a single `page` reused across all 10 submissions (5 scam + 5 benign per D-05/GOLD-02), explicit `browser.close()` at the end (use `try/finally` or keep it inside the `with sync_playwright() as p:` block so it always closes even on assertion failure).

**Error handling pattern** (`ncsc_scraper.py` lines 61-62):
```python
except Exception:
    return None
```
The scraper swallows exceptions and returns `None` because scraping is best-effort. **Do not copy this for the verification script** — the verification script's whole purpose is to surface failures (a candidate that raises or returns an unstable verdict must fail loudly, per D-07 "reject that prompt"), so let exceptions propagate or explicitly `print`+`sys.exit(1)` on instability instead of silently swallowing.

**DOM/API contract to drive** — exact selectors and JSON shape (from `tests/runtime/test_demo.py` lines 39-116 and `src/runtime/demo_assets/demo.js` lines 1-17, 128-176):
```javascript
// demo.js — confirms the DOM ids and the exact fetch call the script must reproduce via Playwright
const messageInput = document.getElementById('message-input');
const channelSelect = document.getElementById('channel-select');
const analyzeButton = document.getElementById('analyze-button');
...
const response = await fetch('/api/analyze', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ text, channel }),
  signal: currentController.signal,
});
```
```python
# tests/runtime/test_demo.py lines 87-115 — confirms the exact JSON response contract
# the script's page.expect_response(...).json() call will receive:
# { "risk_tier": "...", "threat_labels": [...], "top_cues": [{"span":..., "reason":...}],
#   "recommendations": [...], "backend_name": "..." }
```
RESEARCH.md already provides a complete, ready-to-adapt script (`Code Examples` section) built from exactly this analog + contract combination — reuse it directly rather than re-deriving:
```python
from playwright.sync_api import sync_playwright

def run_once(page, text: str, channel: str = "sms"):
    page.fill("#message-input", text)
    page.select_option("#channel-select", channel)
    with page.expect_response(lambda r: "/api/analyze" in r.url) as resp_info:
        page.click("#analyze-button")
    response = resp_info.value
    timing = response.request.timing
    payload = response.json()
    latency_ms = timing["responseEnd"] - timing["requestStart"]
    return payload, latency_ms
```

**Process-management pattern (starting/stopping `vnphish demo` for the script):** RESEARCH.md's "Don't Hand-Roll" table specifies: launch the server as a script-owned `subprocess.Popen(["vnphish", "demo", "--no-browser", "--port", "8765"])` and call `.terminate()`/`.kill()` on that exact handle when done — never a broad `taskkill /IM python.exe`-style pattern-based kill (this was explicitly blocked once already in this project's research session). No in-repo analog for `subprocess.Popen` server lifecycle exists to copy from (see "No Analog Found" below) — treat RESEARCH.md's guidance as the canonical source here.

---

### `.planning/phases/28-baseline-readiness-zero-code-diagnostics/artifacts/golden-prompts.md` (or `.json`) (documentation/config, file-I/O)

**Analog (structure for a JSON variant):** `data/manifests/phase5-release-eval-phase5-recovered-balanced-val.json`

**Core pattern** (lines 1-9) — flat, run-scoped result record with a top-line verdict field:
```json
{
  "run_id": "phase5-recovered-balanced-val",
  "verdict": "BLOCK",
  "risky_recall_floor": 0.9,
  "overall_metrics": { "macro_f1": 0.74, "weighted_f1": 0.86, "evaluated_rows": 210 }
}
```
Adapt shape for this phase's artifact: `{"golden_scam": {"text": ..., "verdict": ..., "runs": [...], "stable": true}, "golden_benign": {...}, "diag03_latency_ms": ..., "recorded": "2026-07-02"}`.

**Analog (structure for a narrative `.md` variant):** `.planning/phases/22-cover-page-certification-letter-and-front-matter/22-01-SUMMARY.md` — YAML-frontmatter-style key-value block (`key-files`, `key-decisions`, `requirements-completed`) followed by narrative. If the planner prefers a human-readable artifact over JSON, follow this project's existing `*-SUMMARY.md` frontmatter convention (`requirements-completed: [DIAG-01, DIAG-02, DIAG-03, GOLD-01, GOLD-02]`, `key-decisions: [...]`) rather than inventing a new format.

**Recommendation:** since this is a verification/diagnostic phase whose main consumer is the human defense-prep process (not downstream code), a single markdown artifact following the `*-SUMMARY.md` convention — recording the locked golden-scam text, locked golden-benign text, the 5/5 stability confirmation, and the one recorded latency figure — is sufficient. A DevTools screenshot (per RESEARCH.md Approach A) should be saved alongside it in the same `artifacts/` directory.

---

## Shared Patterns

### Lazy Playwright import
**Source:** `src/data_pipeline/scraper/ncsc_scraper.py` line 53 (`from playwright.sync_api import sync_playwright` inside the function body, not at module top)
**Apply to:** the new verification script — keeps the import scoped to only the code path that needs a browser.

### Readiness/error-code contract for CLI commands (context only — not modified this phase)
**Source:** `src/runtime/cli.py` lines 56-88 (`handle_analyze`, `handle_doctor`, `handle_demo`)
**Apply to:** anyone running DIAG-01/DIAG-02 manually or from a smoke-test wrapper needs to know: `doctor` exit `0`=ready/`1`=not ready; `analyze` exit `0`=success/`1`=boundary or unavailable error/`2`=doctor pre-flight failed. No new code needed — this is reference knowledge for interpreting command output when recording DIAG-01/02 results, not a pattern to copy into new code.

### DOM contract / JSON response contract for the demo
**Source:** `src/runtime/demo_assets/demo.js` (lines 1-17, 128-176) and `src/runtime/demo_assets/index.html` (ids referenced in `tests/runtime/test_demo.py` lines 46-70)
**Apply to:** the verification script (see Pattern Assignments above) — this is the single source of truth for selectors and payload shape; do not invent new selectors.

## No Analog Found

| File/Concern | Role | Data Flow | Reason |
|---|---|---|---|
| Script-owned server lifecycle (`subprocess.Popen` launch of `vnphish demo`, tracked handle, explicit `.terminate()`) | process-management utility | event-driven | No existing script in this repo launches and owns a subprocess server for the duration of a script run — `ncsc_scraper.py` only launches a browser (not a server); `tests/runtime/test_demo.py` calls `build_demo_app` in-process via WSGI test harness rather than spawning a real server process. Use RESEARCH.md's "Don't Hand-Roll" guidance (Popen + `.terminate()`, or a `page.goto` retry/timeout for readiness detection) as the canonical source since no in-repo precedent exists. |

## Metadata

**Analog search scope:** `src/data_pipeline/scraper/`, `src/runtime/` (cli.py, doctor.py, demo.py, demo_assets/), `tests/runtime/`, `data/manifests/`, `.planning/phases/22-*/`
**Files scanned:** `src/data_pipeline/scraper/ncsc_scraper.py`, `src/runtime/cli.py`, `src/runtime/doctor.py`, `src/runtime/demo_assets/demo.js`, `tests/runtime/test_demo.py`, `tests/runtime/conftest.py`, `data/manifests/phase5-release-eval-phase5-recovered-balanced-val.json`, `.planning/phases/22-cover-page-certification-letter-and-front-matter/22-01-SUMMARY.md`
**Pattern extraction date:** 2026-07-02
