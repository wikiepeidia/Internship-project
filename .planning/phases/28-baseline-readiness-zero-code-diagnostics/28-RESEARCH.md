# Phase 28: Baseline Readiness & Zero-Code Diagnostics - Research

**Researched:** 2026-07-02
**Domain:** Zero-code readiness diagnostics + browser-driven stability verification for an existing local Python (`wsgiref`) + GGUF/llama.cpp demo, on Windows
**Confidence:** HIGH (nearly everything below was directly executed/observed on this exact dev machine during research, not inferred)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Golden Prompt Selection**
- **D-01:** Do not ask the user for exact wording — select and verify a candidate from existing sample/test data rather than inventing new text.
- **D-02:** The golden "scam" prompt must represent the **bank impersonation** threat class (most universally recognizable to a non-technical committee).
- **D-03:** Strong existing candidate found during discussion: `src/runtime/demo_assets/demo.js` already ships a `sampleText` constant used by the demo's sample button — a VPBank OTP-lock impersonation message in Vietnamese. This is the natural first candidate to test for stability; use it unless it fails the 5-run stability check, in which case fall back to another bank-impersonation example from `data/splits/*/val.jsonl` or held-out test fixtures.

**Benign Prompt Difficulty**
- **D-04:** The golden benign prompt must be **obviously safe** — a clean, unambiguous "no threat" message. Do NOT use a trickier "looks suspicious but legitimate" message. Rationale: for a ~1-minute live demo in front of a defense committee, an unambiguous correct result is worth more than demonstrating precision on a hard edge case — there's no room for a surprising misfire live.
- Look for benign-labeled examples in existing test fixtures (`tests/runtime/*`, `data/splits/*/val.jsonl` with `label: benign`) rather than writing one from scratch.

**Verification Path**
- **D-05:** The 5+ repeated-run stability check for both golden prompts runs through the **actual web demo** (`vnphish demo`, real browser, real fetch to `/api/analyze`), not just the CLI. Rationale: this must match exactly what the committee will see live — a CLI-only check could miss UI-layer issues (rendering, template population) that the live audience would actually see.
- DIAG-02 (the broader 4-message correctness pass: one per threat class + benign) may still use the CLI (`vnphish analyze`) since that's a broader sanity check, not the golden-prompt lock.

**Decoding Determinism**
- **D-06:** Confirmed via code inspection: both `GGUFAnalyzer` (`src/runtime/analyzers/gguf.py`) and the accelerated backend (`src/runtime/analyzers/accelerated.py`) already hardcode `temperature=0.0` / `do_sample=False` — decoding is already greedy/deterministic. **No config change is needed or in scope for this phase.**
- **D-07:** If a golden prompt candidate still flips between correct/incorrect across the 5+ runs despite greedy decoding (e.g. from CPU floating-point nondeterminism), the response is to **reject that prompt and try a different candidate** — do NOT spend phase time investigating the root cause of the nondeterminism itself. Root-causing decoding nondeterminism is explicitly out of scope for this milestone (verification/hardening only, no runtime redesign).

### Claude's Discretion
- The exact final golden prompt text (once a stable candidate is confirmed) is Claude's call — pick from the candidates above, run the stability check, and lock whichever passes 5/5 clean.
- How the 5+ repeated runs are executed (manual browser repetition vs. a lightweight Playwright script) is an implementation detail for the planner/executor, not a discussion decision — Phase 28 research already recommends Playwright is already a project dependency.

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DIAG-01 | `vnphish doctor` reports READY on the dev machine before any other verification proceeds | **Already verified TRUE during this research session** (see Summary) — exact command, exit code, and full report captured below; planner should treat this as a fast confirmation step, not an open risk |
| DIAG-02 | `vnphish analyze` produces correct risk tier, threat label, grounded cues, and safe-steps output for one sample message per in-scope threat class (bank impersonation, account-takeover/social-engineering, task scam) plus one benign message | CLI exit-code contract documented; exact `data/splits/recovered-balanced/val.jsonl` filter recipe provided for finding per-class candidates; one candidate per class already smoke-tested in this session |
| DIAG-03 | A first-pass warm-latency reading for a demo request is captured via browser DevTools Network tab and recorded for later comparison | Manual DevTools procedure documented; scriptable Playwright equivalent (`request.timing`) documented as a more rigorous, reusable alternative that also satisfies GOLD-02 in the same pass |
| GOLD-01 | One scam message and one benign message are selected as the fixed live-demo script | Concrete candidate pool identified for both classes, with one candidate (the default `demo.js` sampleText) already proven to **fail outright** in this session — a load-bearing finding for planning |
| GOLD-02 | Each golden prompt is run at least 5 times, producing the identical correct verdict every run | Playwright script pattern provided that reuses one warm browser/server session across all 5 runs (matching real defense-day conditions) and captures DIAG-03 timing in the same pass |
</phase_requirements>

## Summary

This phase requires no new tooling — `vnphish doctor`, `vnphish analyze`, and `vnphish demo` already exist and were exercised directly against this repo during this research session (not merely read as source). Three concrete, HIGH-confidence, directly-observed facts should drive planning:

1. **DIAG-01 is already satisfied on the dev machine today.** Running `vnphish doctor` (or `python -m src.runtime.cli doctor`) returns exit code `0` and prints `READY backend=gguf local_only=True text_only=True` with all 12 sub-checks passing. This phase's doctor task is a fast confirmation/documentation step, not an open risk.
2. **The default golden-scam candidate from CONTEXT.md (D-03) currently fails outright, reproducibly, via CLI `analyze`.** Submitting the exact `demo.js` `sampleText` string ("VPBank cảnh báo account Internet Banking...") through `vnphish analyze` raises `RuntimeUnavailableError` ("Local runtime is unavailable...") on **both** of two consecutive attempts in this session — not a flip between correct/incorrect, a hard failure every time. Per D-07, this means: reject it immediately, do not spend phase time investigating why (a plausible but unconfirmed cause is prompt+URL token count interacting with the tuned `n_ctx=512`/`max_tokens=250` budget), and move straight to a fallback bank-impersonation candidate. A validated fallback candidate is already identified below (see Common Pitfalls #1 and Code Examples).
3. **`vnphish analyze` (CLI) and `vnphish demo` (web) have meaningfully different latency profiles for reasons that matter to how GOLD-02/DIAG-03 should be executed.** `handle_analyze` calls `run_runtime_doctor()` (which builds and loads a throw-away `GGUFAnalyzer`) and *then* `build_default_runtime_service()` (which builds and loads a second, separate `GGUFAnalyzer`) — the GGUF model is loaded from disk **twice** per CLI invocation. Measured in this session: ~12s per `vnphish analyze` call (double load + inference) vs. ~6.5-10s per warm `/api/analyze` request through an already-running `vnphish demo` server (single load at server startup, reused for every request). This is exactly why D-05 requires the golden-prompt stability check to go through the actual web demo, not the CLI — the CLI's timing/behavior is not representative of what the committee will see live.

The benign candidate question (additional_context item 3) has a clean answer: `tests/runtime/conftest.py`'s existing `sample_benign_message` fixture ("Chào bạn, lịch họp nhóm được dời sang 9h sáng mai tại phòng học tầng 3. Nếu bận thì báo lại giúp mình trước tối nay." — a meeting-reschedule message with no money, no links, no urgency, no OTP) is a better D-04 match than anything in `data/splits/recovered-balanced/val.jsonl`'s `label=benign` rows, most of which are bank-notification-flavored ("Mã OTP của bạn là...", "Tài khoản của bạn hiện có số dư...") and read as exactly the "looks suspicious but legitimate" style D-04 says to avoid. This fixture message was confirmed to classify correctly (`Risk tier: Benign`, `Threat labels: Benign`) via both CLI and a live `/api/analyze` POST in this session.

**Primary recommendation:** Run `vnphish doctor` first (already known-good, ~instant); then CLI-smoke-test all 4 DIAG-02 candidates before touching the browser; then write one small Playwright script (reusing the pattern already in `src/data_pipeline/scraper/ncsc_scraper.py`) that opens `vnphish demo` once, submits each golden candidate 5 times through the real page, and captures both the JSON verdict (GOLD-02) and `request.timing` (DIAG-03) in the same loop — this satisfies three requirements (DIAG-03, GOLD-01, GOLD-02) with one artifact instead of three separate manual passes.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Readiness probe (`doctor`) | Backend / CLI process | — | Pure in-process Python check (imports, settings, model load probe); no browser or network involved |
| CLI functional pass (`analyze`) | Backend / CLI process | — | Direct `RuntimeService` call from a fresh process; exercises model correctness in isolation from the web layer |
| Golden-prompt stability check | Browser / Client (driving) + API/Backend (serving) | — | Per D-05, must traverse the real `fetch('/api/analyze')` call inside an actual page load — this is explicitly a cross-tier check, not backend-only |
| Warm-latency capture | Browser / Client (measurement point) | API/Backend (source of the delay) | DevTools Network tab and Playwright's `request.timing` both measure from the browser's perspective, which is what a live audience experiences; the actual cost is backend CPU inference |
| Benign/scam candidate sourcing | Data / Storage (`data/splits/*`, `tests/runtime/conftest.py`) | — | Read-only lookup against already-committed fixtures/dataset files; no new component needed |

## Standard Stack

### Core (already installed — nothing new to add this phase)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `llama-cpp-python` | `0.3.23` (confirmed installed via `pip show`) | GGUF CPU inference backend behind `vnphish doctor`/`analyze`/`demo` | Already the validated version this project's behavior was tuned against; pinning it in `pyproject.toml` is Phase 29's job (ENV-05), not this phase's — this phase only needs it to already work, which it does |
| Playwright (Python, sync API) | `1.60.0` (confirmed installed; Chromium launches successfully in this environment with **no extra `playwright install` step needed**) | Drives the real browser for the D-05-mandated stability check | Already a project dependency (`src/data_pipeline/scraper/ncsc_scraper.py`'s `_fetch_with_playwright` method is the existing in-repo pattern to imitate: `from playwright.sync_api import sync_playwright`, `p.chromium.launch(headless=True)`, `browser.close()` in a `try/finally`-safe `with` block) |
| `vnphish` console script | maps to `src.runtime.cli:main` (`pyproject.toml` `[project.scripts]`) | Entry point for `doctor`/`analyze`/`demo` | Confirmed on `PATH` in this dev environment (`where vnphish` resolves to a `.exe` shim); works identically to `python -m src.runtime.cli <cmd>` |
| CPython | `3.13.13` | Runtime interpreter | Already installed and matches `pyproject.toml`'s `>=3.13` requirement |

**No installation commands needed for this phase.** Nothing new is added; every tool used here is already present and already working on this machine as of 2026-07-02.

## Package Legitimacy Audit

**Not applicable this phase.** Phase 28 installs zero new packages — `llama-cpp-python` and `playwright` are pre-existing project dependencies exercised as-is (confirmed present via `pip show` in this session). The Package Legitimacy Gate protocol is skipped per its own scope note ("whenever this phase installs external packages" — this phase does not). If the planner later decides a throwaway script needs an extra dev-only library (unlikely; everything needed is stdlib + Playwright + `llama_cpp`), re-run the gate at that point.

## Architecture Patterns

### Concrete Mechanics: `vnphish doctor` (DIAG-01)

**Command (either form works identically):**
```bash
vnphish doctor
# or, if the console script isn't on PATH for some reason:
python -m src.runtime.cli doctor
```

**Exit code contract** (from `src/runtime/cli.py::handle_doctor`, confirmed by direct execution):
- `0` — `status.ready is True` (prints `READY backend=... local_only=... text_only=...` as the first line)
- `1` — `status.ready is False` (prints `NOT READY backend=... local_only=... text_only=...` plus per-check `PASS`/`FAIL` lines and a `Setup steps:` block)

**Actual output captured in this session (2026-07-02, this dev machine):**
```
llama_context: n_ctx_seq (512) < n_ctx_train (262144) -- the full capacity of the model will not be utilized
READY backend=gguf local_only=True text_only=True
- python-version: PASS - python=3.13
- import:ftfy: PASS - Imported ftfy successfully.
- import:pydantic: PASS - Imported pydantic successfully.
- import:pydantic_settings: PASS - Imported pydantic_settings successfully.
- settings-load: PASS - Runtime settings loaded successfully.
- runtime-backend: PASS - settings.runtime_backend='gguf'
- runtime-profile: PASS - runtime_profile=gguf-laptop
- runtime-max-cues: PASS - runtime_max_cues=3
- runtime-fail-closed: PASS - runtime_fail_closed=True
- runtime-store-raw-text: PASS - runtime_store_raw_text=False
- backend-ready: PASS - backend=gguf ready=True
- release-gate-summary: PASS - latest_verdict=BLOCK run_id=phase5-recovered-balanced-val manifest=data\manifests\phase5-release-eval-phase5-recovered-balanced-val.json
```
Exit code: `0`. **DIAG-01 is satisfied right now, on this machine, with zero changes needed.**

Two things in this output need interpretation, not fixing (see Common Pitfalls #2 and #5):
- The `llama_context: n_ctx_seq (512) < n_ctx_train (262144)...` line is a `llama.cpp` informational message printed to stdout/stderr *before* the doctor report — it looks alarming but is not a failure and is not part of the doctor's own checks.
- The `release-gate-summary` check reports `PASS` (meaning "I could read *a* release-eval file") even though the `latest_verdict` embedded in that file is `BLOCK` — this is a stale, pre-Phase-7a-recovery artifact, not the actual final verdict (which is PASS per `STATE.md`'s Phase 7a resolution). The doctor check does not distinguish "verdict is PASS" from "verdict is BLOCK" — it only checks "file is readable." Don't be alarmed if this line is shown live; it is cosmetic and does not gate `ready`.

### Concrete Mechanics: `vnphish analyze` (DIAG-02)

**Command forms:**
```bash
vnphish analyze --text "message text here" --channel sms
# or stdin form:
echo "message text here" | vnphish analyze
```

**Exit code contract** (from `handle_analyze`, confirmed by direct execution and by reading `src/runtime/cli.py`):
- `2` — pre-flight `run_runtime_doctor()` reports not ready; prints the doctor report and exits before touching the model at all
- `1` — `RuntimeBoundaryError` (input too short/empty/non-text) or `RuntimeUnavailableError` (backend failed after doctor passed, e.g., a malformed/unparseable model response) — prints `render_runtime_error(...)` output
- `0` — success; prints `render_analysis_result(...)` output (summary, `Risk tier: <Benign|Suspicious|High risk>`, `Threat labels: <...>`, up to 3 grounded cues, up to 3 safe-step recommendations)

**Output format reference** (from `src/runtime/render.py`, display-string mapping confirmed by reading source):
- Risk tiers render as `Benign` / `Suspicious` / `High risk` (title case; underlying enum values are lowercase `benign`/`suspicious`/`high-risk`)
- Threat labels render as `Bank impersonation` / `Zalo social engineering` / `Task scam` / `Benign` (underlying enum values: `bank_impersonation`, `zalo_social_engineering`, `task_scam`, `benign`)

**Timing observed in this session:** ~12s per `vnphish analyze` invocation (fresh process; see "Why CLI feels slower" below). Each call prints the `llama_context: n_ctx_seq...` warning **twice** — this is a directly-observable symptom (not just a code-reading inference) of the double model-load described in the Summary.

**Why CLI feels slower than the demo (confirmed, not assumed):** `handle_analyze` calls `run_runtime_doctor()` first (which internally builds a fresh `RuntimeDoctor().run()` → `GGUFAnalyzer(...).doctor()`, loading the model once into a throwaway instance), then calls `build_default_runtime_service()` (which builds a **second**, independent `GGUFAnalyzer` instance via `_build_backend_from_settings`) and runs the real analysis on that second instance. The two `GGUFAnalyzer` instances do not share `_cached_runtime` (it's an instance attribute, not a module-level singleton), so the model file is read from disk and loaded into `llama_cpp.Llama` twice per CLI process. `vnphish demo`, by contrast, builds one `DemoApp`/`RuntimeService`/`GGUFAnalyzer` at server startup and reuses it for the whole server lifetime — only the very first request pays load cost, every subsequent request is inference-only.

### Concrete Mechanics: `vnphish demo` + browser-driven verification (GOLD-01/02, D-05)

**Starting the server for a scripted check:**
```bash
vnphish demo --no-browser --port 8765
```
`--no-browser` is important for scripted/headless verification — without it, `webbrowser.open_new_tab` fires and steals focus (confirmed: `python -c "import webbrowser; print(webbrowser.get())"` resolves to `webbrowser.WindowsDefault`, i.e. it will actually open the OS default browser — Edge, on this machine).

**Readiness detection gotcha (Windows-specific):** the server prints `Warming up local model...` then `Local demo UI: http://...` to stdout *before* calling `make_server(...).serve_forever()`, but when the process is launched in the background from a POSIX-emulation shell (Git Bash `(cmd &)`), Python's stdout buffering meant these prints did not reliably appear in a redirected log file in this session even several seconds after the process was confirmed to be serving requests. **Do not rely on parsing stdout to detect "server is ready" in a Windows/Git-Bash automation script.** Instead, poll the port directly (e.g., retry a lightweight `GET /` or attempt a socket connect in a loop with a short sleep) or, better, let Playwright's own `page.goto(url)` retry/timeout handle this — a `page.goto` against a not-yet-listening port will simply raise/timeout, which is a clean, scriptable signal.

**Existing DOM selectors to drive** (confirmed present in `src/runtime/demo_assets/index.html` and asserted by `tests/runtime/test_demo.py`):
| Element | Selector | Behavior |
|---|---|---|
| Message textarea | `#message-input` | `page.fill(...)` |
| Channel picker | `#channel-select` | `page.select_option(...)`; valid values: `unknown`, `sms`, `zalo`, `messenger`, `telegram`, `facebook` |
| Submit | `#analyze-button` (or `form.requestSubmit()` via Enter key on the textarea) | Triggers `demo.js`'s `analyzeMessage()` → `fetch('/api/analyze', ...)` |
| Sample-fill shortcut | `#sample-button` | Fills `#message-input` with the hardcoded `sampleText` (the D-03 candidate) **and auto-submits** (`form.requestSubmit()` is called inside the click handler) — useful only if the default candidate is kept; if it's rejected per the Summary's finding, drive `#message-input` directly with the replacement text instead |
| Result verdict slots (post-render) | `[data-slot="risk-tier"]`, `[data-slot="verdict"]`, `[data-slot="labels"]`, `[data-slot="grounded-cues"]`, `[data-slot="recommendations"]` inside `#result-panel` | Can be read via `page.text_content(...)` if the plan wants to assert on rendered DOM in addition to the raw JSON response (recommended if catching template-layer bugs matters, per D-05's own stated rationale) |

**Capturing the verdict without scraping the DOM (simpler, and still satisfies D-05):** use Playwright's `page.expect_response(...)` to intercept the real `/api/analyze` response and call `.json()` on it directly. This still travels through the real browser + real fetch + real WSGI endpoint (satisfying "actual web demo," not a direct `RuntimeService` call) while avoiding brittle DOM-text parsing. See Code Examples below.

### DevTools Network Tab Capture (DIAG-03) — Two Valid Approaches

**Approach A — Manual, literal reading of the requirement text:**
1. Launch `vnphish demo` normally (with the browser opening).
2. Open DevTools (F12) → Network tab, filter to `Fetch/XHR`.
3. Submit one message.
4. Click the `/api/analyze` row → note the `Time` column value (and/or the Timing sub-tab's `Waiting (TTFB)` breakdown).
5. **Make it "recordable/reportable," not just eyeballed:** take a screenshot of the Network panel row (Win+Shift+S or the browser's own screenshot tool) and save it under the phase's artifact directory (e.g. `.planning/phases/28-baseline-readiness-zero-code-diagnostics/artifacts/diag-03-warm-latency.png`), and write the exact millisecond figure into a short note in the same folder or into the phase's execution log. A screenshot with no saved number, or a number with no saved screenshot, both fail "recorded for later comparison" — do both.

**Approach B — Scripted, reusable, and recommended (produces the same numbers DevTools would show, but saved automatically):**
Playwright's `Request.timing` property (confirmed via official Playwright Python docs, `https://playwright.dev/python/docs/api/class-request`) returns a dict with the same Resource-Timing-API fields Chrome's Network panel uses internally: `startTime`, `domainLookupStart/End`, `connectStart/End`, `requestStart`, `responseStart`, `responseEnd` (all in ms relative to `startTime`; `-1` if unavailable). `responseEnd - requestStart` (or `- responseStart` for just the download phase) is the DevTools-equivalent "Time" figure for that request. Because this is captured programmatically, it can be written straight to a JSON/CSV artifact — satisfying "recorded for later comparison" more rigorously than a single screenshot, and it can be captured **during the same Playwright run that does the GOLD-02 5x stability check**, so DIAG-03 and GOLD-02 share one script instead of needing two separate verification passes. Recommend running Approach B as the primary method and taking one Approach-A screenshot alongside it as the literal human-visible artifact the requirement text describes.

### Sourcing the Golden Benign Prompt (D-04) — Concrete File Paths

Two candidate pools exist; they are **not equally good** for D-04's "obviously safe" requirement:

1. **`tests/runtime/conftest.py`, fixture `sample_benign_message`** (line 18):
   ```
   "Chào bạn, lịch họp nhóm được dời sang 9h sáng mai tại phòng học tầng 3. "
   "Nếu bận thì báo lại giúp mình trước tối nay."
   ```
   No money, no link, no OTP, no urgency word, no institution name — this is the clean, unambiguous kind of benign message D-04 asks for. **Confirmed in this session** to classify correctly via both `vnphish analyze` and a live `/api/analyze` POST: `risk_tier: benign`, `threat_labels: ["benign"]`.

2. **`data/splits/recovered-balanced/val.jsonl`, rows where `"label": "benign"`** (61 of them; JSONL fields: `text`, `label`, `risk_tier`, `suspicious_spans`, `xai_explanation`, `source`, `seed_id`). **Caution:** most of these are bank/OTP-notification-flavored (e.g., `"Mã OTP của bạn là 123456. Hãy nhập mã này để xác minh giao dịch của bạn..."`, `"Tài khoản của bạn hiện có số dư 10,000,000 VND..."`) — exactly the "looks suspicious but legitimate" style D-04 explicitly says to avoid for the live-demo golden prompt. (16 of the 61 rows have a matching `risk_tier: "benign"` too — the rest are `label=benign` but `risk_tier=suspicious`, i.e. the dataset itself treats them as edge cases, not obviously-safe examples.) Use this pool only as a backup source if the conftest fixture somehow fails stability testing, and if so, prefer a non-bank-themed row if one exists.

**Recommendation:** use the `conftest.py` fixture as the primary D-04 candidate; it does not need the `data/splits` fallback.

### Sourcing DIAG-02's Other Threat-Class Candidates

Filter recipe for `data/splits/recovered-balanced/val.jsonl` (Python, UTF-8-safe):
```python
import json
rows = [json.loads(l) for l in open("data/splits/recovered-balanced/val.jsonl", encoding="utf-8")]
by_label = {}
for r in rows:
    by_label.setdefault(r["label"], []).append(r)
# bank_impersonation: 56 rows, some risk_tier="high-risk"
# zalo_social_engineering: 75 rows, some risk_tier="high-risk"
# task_scam: 62 rows — all risk_tier="suspicious" in this split (none are "high-risk")
# benign: 61 rows (see caveat above)
```
One candidate per remaining class already smoke-tested successfully in this session:
- **bank_impersonation fallback** (used after the default D-03 candidate failed — see Common Pitfalls #1): `"Thông báo từ TPBank: OTP của bạn là 847291. KHÔNG chia sẻ mã này với bất kỳ ai. Nếu bạn ko thực hiện giao dịch, gọi ngay 0938.xxx.xxx để được hỗ trợ khóa account."` → classified `risk_tier: suspicious`, `threat_labels: ["bank_impersonation"]`, 3 grounded cues, 3 safe-step recommendations. Correct threat label; risk tier is `suspicious` not `high-risk` (the dataset's own gold label for this exact row is `high-risk`) — worth knowing the model may render this specific message slightly more conservatively than the dataset's own annotation, though it still correctly flags it as non-benign bank impersonation.
- **zalo_social_engineering candidates found but not yet CLI-tested in this session** (time-boxed): `"Bro ơi mình đang ở nước ngoài, điện thoại hỏng ko gọi dc. Mày có thể mua giúp tao thẻ Viettel 500k rồi chụp mã gửi qua Zalo k? Tao về trả liền, cần gấp lắm 😭"` (157 chars, `risk_tier: high-risk` gold label) is a good short first candidate to try.
- **task_scam candidates** in this split are all `risk_tier: suspicious` (none `high-risk`) — e.g. `"Bạn ơi, tài khoản của bạn đang có vấn đề. Vui lòng đăng nhập vào app và kiểm tra lại. Nếu cần hỗ trợ, gọi 0123456789. Thanks!"` (125 chars) is the shortest.

These are **starting points for the planner/executor to smoke-test**, not final locked choices — DIAG-02 only requires one correct example per class, and picking/confirming the exact final wording is implementation work, not research.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|--------------|-----|
| Detecting server readiness before scripting against it | A custom HTTP-polling readiness wrapper with retry/backoff logic | `page.goto(url, timeout=...)` inside the Playwright script itself, or a trivial `for _ in range(N): try socket.connect(...) except: sleep(...)` loop | Playwright already has a configurable navigation timeout; a bespoke readiness poller adds code for no benefit |
| Verifying the golden-prompt result "hits the real demo" (D-05) | A raw `requests.post('/api/analyze', ...)` script | Playwright driving an actual page load + `page.expect_response(...)` around a real click | A direct HTTP client call bypasses the browser entirely and does **not** satisfy D-05's explicit rationale (catching UI/template-layer issues); it would be functionally indistinguishable from testing `RuntimeService` directly |
| Measuring warm latency | A custom timing decorator wrapped around `DemoApp.__call__` | Playwright's built-in `request.timing` property (Resource Timing API-equivalent, zero code change to `src/runtime/`) | Zero-risk, zero-touch to any frozen backend file; produces the same numbers a human would read off DevTools |
| Killing/restarting the demo server during a repeated-run script | Shell `taskkill /IM python.exe` or other broad process-pattern kills | Launch the server as a `subprocess.Popen` **owned by the same script**, and call `.terminate()`/`.kill()` on that specific process object when done | Pattern-based kills (by image name) can match unrelated Python processes on the same machine — the Bash tool in this research session explicitly blocked a `taskkill /IM python.exe` for this exact reason; killing a script-owned `Popen` handle, or finding the exact PID via `netstat -ano | grep :<port>` first, avoids the risk entirely |

**Key insight:** every requirement in this phase (DIAG-01/02/03, GOLD-01/02) is satisfiable with tools that already exist in this repo or ship with Playwright — there is no legitimate reason to write new HTTP clients, timing instrumentation, or process-management utilities from scratch.

## Common Pitfalls

### Pitfall 1: The CONTEXT.md default golden-scam candidate fails outright (not just "flips")
**What goes wrong:** `demo.js`'s `sampleText` ("VPBank cảnh báo account Internet Banking của bạn sẽ bị khóa trong 24h. Không chia sẻ mã OTP hoặc Smart OTP và không bấm vào link đăng nhập https://vpbank-secure.example để xác minh ngay.") raises `RuntimeUnavailableError` via `vnphish analyze` — confirmed twice in this session, not a one-off.
**Why it happens (unconfirmed hypothesis, not root-caused per D-07):** the message includes a URL, which may tokenize unusually and interact with the tuned `n_ctx=512`/`max_tokens=250` budget, producing a truncated/unparseable model JSON response that `extract_structured_payload` cannot parse — `RuntimeService.analyze_text` catches any such exception and re-raises it as the generic `RuntimeUnavailableError`, masking the real cause.
**How to avoid:** per D-07, do not investigate further — treat this candidate as already-failed and go straight to the fallback (the TPBank candidate validated above, or another short, URL-free `bank_impersonation` row from `data/splits/recovered-balanced/val.jsonl`).
**Warning signs:** any candidate that contains a URL is at higher risk of the same failure mode; prefer OTP/hotline-style bank-impersonation text without embedded links for the golden prompt specifically (embedded-link scam behavior can still be covered by the broader DIAG-02 4-message pass using a different, non-golden example).

### Pitfall 2: `doctor`'s `release-gate-summary` check can show a stale `BLOCK` verdict while still reporting `PASS`
**What goes wrong:** `RuntimeDoctor._check_latest_release_gate_summary` picks the most-recently-modified file matching `data/manifests/phase5-release-eval-*.json` by mtime. Both files currently matching that glob predate the Phase 7a task-scam-recall recovery fix (2026-05-28); the actual final PASS verdict lives in a differently-named artifact (`.planning/phases/07a-.../eval-snapshot-task-scam-recovery.json`) that this glob does not match. The check's own `passed` field is `True` as long as it can *read* a file — it never inspects whether `verdict == "PASS"`.
**Why it happens:** the check was written before the Phase 7a recovery artifact existed under a different filename pattern, and nobody has needed to update the glob since (this phase should not — that's a code change, out of scope).
**How to avoid:** if `vnphish doctor`'s output is shown live or screenshotted as a "system readiness proof" (a FEATURES.md differentiator), be ready to explain that `release-gate-summary`'s printed `verdict=BLOCK` refers to a superseded pre-recovery snapshot, not the thesis's actual final evaluation result (task_scam recall 0.871, PASS, per `STATE.md`). Do not attempt to fix the glob this phase — it is cosmetic (does not affect `ready`) and touching `doctor.py` is out of scope for a zero-code-diagnostics phase.
**Warning signs:** anyone reading the full doctor report line-by-line (rather than just the top-line `READY`/`NOT READY`) could be confused by this; worth a one-line note in whatever artifact records the DIAG-01 pass.

### Pitfall 3: Vietnamese text embedded directly in a `curl -d "..."` command line gets corrupted on Windows/Git Bash
**What goes wrong:** `curl -X POST ... -d '{"text": "Chào bạn, ..."}'` produced `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xe0 in position 11: invalid continuation byte` server-side — confirmed directly in this session — even though the exact same Vietnamese string passed as a `--text` argument to `vnphish analyze` (not through curl) worked perfectly.
**Why it happens:** Git Bash/MSYS's argument-passing layer re-encodes or mis-escapes multi-byte UTF-8 sequences embedded inline in a `-d`/`--data` string differently than it does for a plain CLI positional/flag argument.
**How to avoid:** never embed Vietnamese sample text directly in a `curl -d "..."` one-liner on this Windows/Git-Bash setup. Either (a) write the JSON payload to a UTF-8-encoded file first and use `curl --data-binary @file.json`, or (b) skip `curl` entirely for anything involving realistic Vietnamese content and drive the request through Playwright (which handles encoding correctly via the browser's own `fetch`) or a Python `requests`/`urllib` call.
**Warning signs:** a `500`/`UnicodeDecodeError` on a request that "should" be fine, specifically when Vietnamese diacritics are involved and the request was built via a raw shell one-liner.

### Pitfall 4: Backgrounding `vnphish demo` in Git Bash doesn't reliably surface readiness prints
**What goes wrong:** `(vnphish demo --no-browser --port 8766 > log.txt 2>&1 &)` did not show the expected `"Warming up local model..."` / `"Local demo UI: ..."` lines in `log.txt` even ~10+ seconds after the server was independently confirmed (via a successful `curl`/Playwright request) to be up and serving.
**Why it happens:** Python's stdout buffering behavior differs for a backgrounded subshell without an attached TTY on Windows/Git Bash; the `llama_context:` line from the C++ layer appeared in the log (unbuffered/stderr-adjacent), but the plain Python `print()` calls did not flush in time to be observed.
**How to avoid:** don't gate a script's "is the server ready yet" logic on parsing stdout on this platform. Poll the port/URL directly instead (a `page.goto` retry, or a short socket-connect loop).
**Warning signs:** a script that waits for a specific stdout string to appear in a log file may hang or false-negative on Windows even though the server is actually fine.

### Pitfall 5: A green `vnphish doctor` does not guarantee `vnphish demo`/`vnphish analyze` behave identically
**Already documented in the milestone-level PITFALLS.md (Pitfall 8)** — reconfirmed here as directly relevant to this phase's own two DIAG checks: `run_runtime_doctor()` (used by `analyze`) and `service.backend.doctor()` (used internally by `demo`) are two different call paths that happen to both currently pass, but this phase's own success criteria (item 1 vs. item 2) already treat them as separate checks for exactly this reason — run both, don't assume one implies the other.

## Code Examples

### One script satisfying GOLD-02 (5x stability) and DIAG-03 (latency) together

```python
# Source: pattern combines src/data_pipeline/scraper/ncsc_scraper.py's existing
# sync_playwright usage with the DemoApp DOM/API contract confirmed in
# tests/runtime/test_demo.py and src/runtime/demo_assets/{index.html,demo.js}.
# Requires `vnphish demo --no-browser --port 8765` already running separately
# (see Pitfall 4 for why readiness should be detected via page.goto, not stdout).

from playwright.sync_api import sync_playwright

GOLDEN_SCAM = "Thông báo từ TPBank: OTP của bạn là 847291. KHÔNG chia sẻ mã này với bất kỳ ai. Nếu bạn ko thực hiện giao dịch, gọi ngay 0938.xxx.xxx để được hỗ trợ khóa account."
GOLDEN_BENIGN = "Chào bạn, lịch họp nhóm được dời sang 9h sáng mai tại phòng học tầng 3. Nếu bận thì báo lại giúp mình trước tối nay."
RUNS = 5
DEMO_URL = "http://127.0.0.1:8765/"


def run_once(page, text: str, channel: str = "sms"):
    page.fill("#message-input", text)
    page.select_option("#channel-select", channel)
    with page.expect_response(lambda r: "/api/analyze" in r.url) as resp_info:
        page.click("#analyze-button")
    response = resp_info.value
    timing = response.request.timing  # Resource-Timing-API dict, same as DevTools
    payload = response.json()
    latency_ms = timing["responseEnd"] - timing["requestStart"]
    return payload, latency_ms


def verify_stable(page, label: str, text: str, channel: str = "sms"):
    results = []
    for i in range(RUNS):
        payload, latency_ms = run_once(page, text, channel)
        results.append((payload["risk_tier"], tuple(payload["threat_labels"]), latency_ms))
        print(f"[{label}] run {i + 1}: risk_tier={payload['risk_tier']} "
              f"labels={payload['threat_labels']} latency={latency_ms:.0f}ms")
    verdicts = {(r[0], r[1]) for r in results}
    stable = len(verdicts) == 1
    print(f"[{label}] STABLE={stable} across {RUNS} runs")
    return stable, results


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(DEMO_URL, timeout=30_000)  # raises/timeouts cleanly if server isn't up yet

    scam_stable, scam_results = verify_stable(page, "SCAM", GOLDEN_SCAM)
    benign_stable, benign_results = verify_stable(page, "BENIGN", GOLDEN_BENIGN)

    browser.close()

# DIAG-03: the first latency reading from either loop above already satisfies
# "a first-pass warm-latency reading ... recorded for later comparison" —
# write scam_results[0] / benign_results[0] to a small JSON/markdown artifact.
```

**Why this satisfies D-05:** `page.click("#analyze-button")` fires the real `demo.js` submit handler, which calls the real browser `fetch('/api/analyze', ...)`, hitting the real `wsgiref` server and the real `RuntimeService`/`GGUFAnalyzer` — indistinguishable from what a human clicking the button would trigger, and reusing one `page`/browser session across all 10 total submissions (5 scam + 5 benign) mirrors the real defense's "one warm server, several quick submissions in a row" usage pattern rather than paying a fresh model-load cost per run.

**Optional DOM-level cross-check** (only if the plan wants to also catch template/rendering bugs, per D-05's stated UI-layer rationale): after `run_once`, additionally assert `page.text_content('#result-panel [data-slot="risk-tier"]')` matches the expected tier, and that `#result-panel [data-slot="labels"]` contains the expected label text — this exercises the client-side rendering path in addition to the raw JSON contract.

## State of the Art

Not meaningfully applicable to this phase — it exercises pre-existing, already-built tooling (`doctor`, `analyze`, `demo`) rather than adopting any new pattern. The one relevant "old vs. new" fact is that `llama-cpp-python==0.3.23` (installed, validated) vs. `0.3.32` (latest upstream) is a real divergence, but pinning/upgrading it is explicitly Phase 29's job (ENV-05), not actionable here — Phase 28 only needs the currently-installed `0.3.23` to keep working, which it does.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|----------------|
| A1 | The root cause of the default `demo.js` sampleText's failure is prompt/URL token count interacting with the `n_ctx=512` budget | Common Pitfalls #1 | LOW — this is explicitly labeled a hypothesis, not a finding to act on; per D-07 the phase response (reject and use a fallback candidate) is identical regardless of the true cause |
| A2 | The `zalo_social_engineering` candidate suggested ("Bro ơi mình đang ở nước ngoài...") will classify correctly | Sourcing DIAG-02 Candidates | LOW-MEDIUM — this specific row was identified from the dataset but not yet smoke-tested via `vnphish analyze` in this session (time-boxed); the planner/executor should verify it before locking it into a plan, same as any other DIAG-02 candidate |
| A3 | Playwright's `request.timing` values are a faithful proxy for what a human would read in Chrome DevTools' Network panel `Time` column | DevTools Network Tab Capture | LOW — this is the standard W3C Resource Timing API, the same data model DevTools itself is built on, confirmed via official Playwright docs; residual risk is only in exactly which two fields to subtract for "the" DevTools number (requestStart→responseEnd vs. startTime→responseEnd), a labeling nuance, not a wrong-tool risk |

## Open Questions

1. **Will the TPBank fallback bank-impersonation candidate (or another `data/splits` row) pass the 5x stability check through the actual web demo, given it only produced `risk_tier: suspicious` (not `high-risk`) on its single CLI test in this session?**
   - What we know: it correctly identifies `threat_labels: ["bank_impersonation"]` with grounded cues and safe-step recommendations every time tested so far (1 run).
   - What's unclear: whether "suspicious" (non-benign, correct label) counts as an acceptable "correct verdict" for GOLD-02's locking bar, or whether the plan should specifically seek a candidate that renders `high-risk` for a more dramatic live-demo moment.
   - Recommendation: leave this to the planner/executor — D-04's own rationale ("no room for a surprising misfire live... unambiguous correct result") arguably applies just as well to the scam side: prefer whichever validated bank-impersonation candidate renders `high-risk` most consistently, but `suspicious` + correct label should not be treated as a failure if no `high-risk` candidate is found stable.
2. **Has the `zalo_social_engineering` and `task_scam` DIAG-02 candidates actually been smoke-tested end-to-end?**
   - What we know: candidates were identified and filtered from `data/splits/recovered-balanced/val.jsonl` but only the bank_impersonation and benign candidates were run through `vnphish analyze` in this research session (time-boxed).
   - What's unclear: whether these two remaining candidates produce clean, correct classifications on the first try, or whether they'll need iteration like the golden-scam prompt did.
   - Recommendation: the planner should budget explicit CLI smoke-test tasks for these two remaining classes before assuming DIAG-02 is a one-shot pass.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|--------------|-----------|---------|----------|
| `vnphish` console script | All DIAG/GOLD checks | ✓ (confirmed: `where vnphish` resolves; `vnphish doctor` ran successfully) | maps to `src.runtime.cli:main` | `python -m src.runtime.cli <command>` (also confirmed working) |
| `llama-cpp-python` | `doctor`/`analyze`/`demo` GGUF backend | ✓ (confirmed via `pip show`) | `0.3.23` | none needed — already the validated version |
| Playwright (Python) + Chromium | GOLD-02 stability script, optional DIAG-03 scripting | ✓ (confirmed: `sync_playwright()` launches Chromium `148.0.7778.96` with no extra install step) | `1.60.0` | manual browser repetition (Approach A for DIAG-03; manual 5x clicking for GOLD-02) if a script is skipped |
| OS default browser (for `vnphish demo`'s auto-open and manual DevTools use) | DIAG-03 Approach A, general manual verification | ✓ (confirmed: `webbrowser.get()` resolves to `webbrowser.WindowsDefault`) | Edge (Windows 11 default, not independently version-checked) | any browser with DevTools; Playwright's bundled Chromium also has a Network panel if launched headed (`headless=False`) |
| `data/splits/recovered-balanced/val.jsonl` | DIAG-02 / GOLD-01 candidate sourcing | ✓ (confirmed readable, 254 rows across 4 labels) | n/a (data file) | `tests/runtime/conftest.py` fixtures as a smaller backup pool |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** none — everything needed for this phase is already present and already working on this dev machine.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-------------------|
| V2 Authentication | No | Local, single-user, loopback-only demo; no auth surface introduced or touched by this phase |
| V3 Session Management | No | No sessions involved; this phase only reads existing endpoints |
| V4 Access Control | No | No new access boundaries created |
| V5 Input Validation | No (pre-existing only) | `/api/analyze`'s existing text/channel validation (`RuntimeService.analyze_text`, confirmed in `service.py`) is exercised as-is; this phase adds no new input paths |
| V6 Cryptography | No | Not applicable — no crypto touched |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|----------------------|
| Golden-prompt test data accidentally containing real PII/real phone numbers instead of synthetic placeholders | Information Disclosure | Confirmed all candidates identified in this research (TPBank OTP, VPBank, Zalo-transfer message) use placeholder-style numbers (`847291`, `0938.xxx.xxx`, generic amounts) consistent with the project's existing synthetic-data-only posture (`DATA-04`); no new data is being introduced this phase, only selected from already-committed synthetic fixtures |
| Running a headless/scripted browser against a locally-bound server exposing it unintentionally | Elevation of Privilege / Information Disclosure | `vnphish demo` already binds `127.0.0.1` only (confirmed by reading `demo.py`); a Playwright script launched on the same machine connects to that same loopback address — no new exposure is introduced by adding a script, only an additional local client |

This phase introduces no new code, no new endpoints, and no new stored data — its security posture is identical to the already-verified frozen backend it exercises.

## Sources

### Primary (HIGH confidence — directly executed/observed in this session)
- `python -m src.runtime.cli doctor` / `vnphish doctor` — full report and exit code captured live, 2026-07-02, this dev machine.
- `vnphish analyze --text "<demo.js sampleText>"` — reproduced `RuntimeUnavailableError` failure twice.
- `vnphish analyze --text "<sample_benign_message fixture>"` — confirmed correct `Risk tier: Benign` / `Threat labels: Benign`, ~12s wall time.
- `vnphish analyze --text "<TPBank OTP candidate>"` — confirmed correct `Threat labels: Bank impersonation`, `risk_tier: suspicious`.
- `vnphish demo --no-browser --port 8766` + `curl --data-binary @file.json` — confirmed live `/api/analyze` warm request timings of ~6.5-10s and the exact `UnicodeDecodeError` failure mode for inline-Vietnamese `curl -d` calls.
- `where vnphish`, `pip show llama-cpp-python`, `pip show playwright`, `python -c "from playwright.sync_api import sync_playwright; ..."`, `python -c "import webbrowser; print(webbrowser.get())"` — environment availability confirmations.
- Direct source reads: `src/runtime/cli.py`, `src/runtime/doctor.py`, `src/runtime/demo.py`, `src/runtime/service.py`, `src/runtime/analyzers/gguf.py`, `src/runtime/render.py`, `src/runtime/demo_assets/{index.html,demo.js}`, `src/data_pipeline/scraper/ncsc_scraper.py`, `tests/runtime/{conftest.py,test_demo.py,test_cli.py}`, `src/runtime/contracts.py`, `pyproject.toml`.
- `data/splits/recovered-balanced/val.jsonl` — read and filtered directly (254 rows, label/risk_tier distribution confirmed by script).

### Secondary (MEDIUM confidence)
- [Playwright Python — Request class docs](https://playwright.dev/python/docs/api/class-request) — `request.timing` property fields and semantics, fetched via WebFetch in this session (official docs, not training-data recall).

### Tertiary (LOW confidence)
- None used — this research relied on direct execution and official docs rather than unverified community sources.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — nothing new added; all versions confirmed via `pip show` in this exact environment.
- Architecture/mechanics: HIGH — CLI/doctor/demo behavior confirmed by direct execution, not just source reading.
- Golden prompt candidates: HIGH for what was tested (doctor, benign, TPBank bank-impersonation); MEDIUM for the two untested candidates (zalo_social_engineering, task_scam) flagged in Open Questions.
- Pitfalls: HIGH — all 5 pitfalls listed were directly observed in this session, not inferred from documentation.

**Research date:** 2026-07-02
**Valid until:** This research is tied to the exact state of this dev machine's model artifacts, dataset splits, and installed package versions on 2026-07-02. Re-verify the golden-prompt candidate results if the model registry's selected GGUF artifact changes (see `TODO.md`'s pending "Copy GGUF to D:\PROJEct\AI MODELS\qlora-final-2026-06\..." item — the currently-registered `version_tag` is already `qlora-final-2026-06`, so this appears already done, but confirm before trusting these exact classification results if that changes again before the defense).
