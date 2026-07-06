# Phase 31: UI Quirks, Edge Cases & Regression Re-check - Research

**Researched:** 2026-07-06
**Domain:** Existing vanilla browser demo regression hardening, Playwright verification, CLI clarity
**Confidence:** HIGH for local codebase findings; MEDIUM for Playwright API details cited from official docs

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

### Mystery Console Error
- **D-01:** Phase 29 found `ERROR SOURCE_LANG_VI` in the browser console during offline verification, with no matching key/string found anywhere in the local runtime or frontend source (`29-04-SUMMARY.md`). Phase 31 must reproduce it (open the demo, watch DevTools console) and triage: if it traces to actual app code, fix it as a UIQ-04 quirk; if it's confirmed browser/extension noise (e.g., a Chrome DevTools extension artifact, unrelated to `demo.js`/`index.html`), document that finding and stop — do not open-ended hunt for a root cause once non-app origin is confirmed.

### CLI Entrypoint Fix (UIQ-03)
- **D-02:** Ship both fixes together: (1) launcher scripts (`scripts/START_DEMO_UI.bat`, `scripts/START_TEXT_ANALYZE.bat` or similar, per Phase 28 research's original recommendation) for double-click use by a non-technical committee member, AND (2) improved argparse `help=`/description text in `src/runtime/cli.py` so `vnphish --help`, `vnphish analyze --help`, and `vnphish demo --help` clearly state "text-only, no browser page" vs "opens the web UI". Do not restructure the CLI contract itself (subcommand names, flags) — this is additive clarity only, consistent with the milestone's "backend/API contract stays frozen" rule.

### Edge-Case Testing (UIQ-01)
- **D-03:** Test the edge-case matrix (empty input, very long text, malformed/off-topic text, mixed Vietnamese-English) through the real web demo, not CLI-only — reuse the Playwright pattern established in `scripts/verify_golden_prompts.py` (Phase 28) rather than writing an unrelated new harness. A new script or an extension of the existing one is the planner's call, per Phase 28's own precedent of preferring a separate script when the concern (edge-case correctness) is distinct from what's already there (golden-prompt stability).

### Double-Submit Re-verification (UIQ-02)
- **D-04:** Re-verify the `AbortController` re-entrant-submit guard via an automated Playwright test that fires rapid repeated submissions and asserts exactly one in-flight request completes cleanly (no orphaned typing indicator, no unhandled rejection) — not a manual click-spam test. This fits the same Playwright-based approach as D-03 and Phase 28/29's established pattern.

### Regression Re-check Scope
- **D-05:** "Regression re-check" for Phases 28-30 means: re-run Phase 28's golden-prompt stability check (the locked scam + benign prompts, via `scripts/verify_golden_prompts.py` or equivalent) to confirm the 2 runtime bugs fixed in Phase 28 (legitimate-OTP-as-benign, no-OTP-link-scam-detection) are still correctly handled after Phase 29's font-route/env-var changes, and re-run the existing test suites touched by Phase 29 (`tests/runtime/test_local_model.py`, `tests/runtime/test_demo.py`). Phase 30 made no source changes (`NO_FIX_APPLIED`), so there is nothing to regression-check from Phase 30 specifically beyond confirming the demo still starts and serves correctly.

### the agent's Discretion
- Exact launcher script naming/wording and exact new `--help` text phrasing.
- Whether edge-case and double-submit tests live in one new script or two.
- Order of task execution within the phase (the planner should sequence so any UIQ-04 fixes happen before the final regression re-check, to catch late-breaking issues).

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| UIQ-01 | Full edge-case matrix is re-tested with no crash or hang. | Use a real-demo Playwright verifier for empty, very long, malformed/off-topic, and mixed Vietnamese-English inputs; assert terminal UI state, no orphaned typing bubble, and no uncaught page errors. [VERIFIED: 31-CONTEXT.md; 31-UI-SPEC.md; scripts/verify_golden_prompts.py] |
| UIQ-02 | Rapid double-submit confirms the existing `AbortController` guard prevents re-entrant requests. | Trigger re-entry through the editable textarea/form path, not only button double-click, because `demo.js` disables the button but keeps the textarea editable and still handles Enter via `form.requestSubmit()`. [VERIFIED: src/runtime/demo_assets/demo.js] |
| UIQ-03 | CLI entrypoint confusion between `analyze` and `demo` is resolved without CLI contract changes. | Add argparse descriptions/help text in `src/runtime/cli.py`, add tests in `tests/runtime/test_cli.py`, and add double-click `.bat` launchers. [VERIFIED: 31-CONTEXT.md; src/runtime/cli.py; tests/runtime/test_cli.py] |
| UIQ-04 | UI quirks found during testing are catalogued and fixed without changing `/api/analyze` or `data-slot` templates. | Console triage must stop if `SOURCE_LANG_VI` is non-app browser/extension noise; any app fix must preserve UI-SPEC tokens, i18n copy, and `data-slot` internals. [VERIFIED: 31-CONTEXT.md; 31-UI-SPEC.md; src/runtime/demo_assets/index.html] |
</phase_requirements>

## Summary

Phase 31 should be planned as a regression lock on an already-shipped UI, not a redesign: the approved UI-SPEC says no new screens, components, colors, spacing, typography, framework, build step, icon library, or registry work belongs in this phase. [VERIFIED: 31-UI-SPEC.md] The project hard constraints also freeze the synchronous `wsgiref` + `POST /api/analyze` backend contract, require vanilla HTML/CSS/JS, prohibit `localStorage`, and preserve `data-slot` template internals. [VERIFIED: STATE.md; 31-CONTEXT.md]

**Primary recommendation:** create one new real-demo Playwright verifier, `scripts/verify_ui_quirks.py`, that reuses Phase 28/30 subprocess/browser patterns, writes a JSON evidence artifact, captures console messages and page errors, and covers UIQ-01/UIQ-02/UIQ-04 discovery before any fix work; then ship UIQ-03 help text and `.bat` launchers; then run final golden-prompt and focused pytest regressions after all fixes. [VERIFIED: scripts/verify_golden_prompts.py; scripts/measure_cold_latency.py; 31-CONTEXT.md]

One planning risk needs explicit handling: `STATE.md` says unusually long messages are blocked by `runtime_max_text_chars`, but `rg` plus direct reads of `src/config/settings.py` and `src/runtime/service.py` found no current `runtime_max_text_chars` setting or enforcement. [VERIFIED: codebase rg; src/config/settings.py; src/runtime/service.py] Do not plan the very-long-text case around a cap that is not implemented; use a bounded, timed Playwright case and treat any hang/failure as a UIQ-04 finding. [VERIFIED: 31-UI-SPEC.md; codebase rg]

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|--------------|----------------|-----------|
| Edge-case matrix UI behavior | Browser / Client | API / Backend | The visible pass/fail is DOM state, console/page errors, typing bubble cleanup, wrapping, and final result/error rendering; `/api/analyze` remains the frozen service dependency. [VERIFIED: 31-UI-SPEC.md; src/runtime/demo_assets/demo.js; src/runtime/demo.py] |
| Rapid repeated submit guard | Browser / Client | API / Backend | `currentController.abort()` and typing/button cleanup live in `demo.js`; the backend is single-threaded `wsgiref` and should not be replaced. [VERIFIED: src/runtime/demo_assets/demo.js; src/runtime/demo.py; .planning/research/PITFALLS.md] |
| CLI entrypoint clarity | CLI / OS launcher | Runtime service | `build_parser()` owns subcommand help and `handle_demo`/`handle_analyze` dispatch; launchers remove live command ambiguity without renaming subcommands. [VERIFIED: src/runtime/cli.py; 31-CONTEXT.md] |
| Golden-prompt regression | Browser / Client + API / Backend | Runtime model | Phase 28 locked the scam/benign prompts through the real web demo and wrote a machine-readable artifact; Phase 31 should rerun that same browser path. [VERIFIED: 28-01-SUMMARY.md; 28-golden-prompt-results.json; scripts/verify_golden_prompts.py] |
| `SOURCE_LANG_VI` triage | Browser / Client | Browser profile/extensions | Source search found no local source match after Phase 29; clean Playwright console capture plus manual original-browser reproduction separates app code from extension/profile noise. [VERIFIED: 29-04-SUMMARY.md; 29-VERIFICATION.md; codebase rg] |

## Recommended Plan Decomposition

| Plan | Scope | Files to Change | Evidence to Produce |
|------|-------|-----------------|---------------------|
| 31-01 Real-demo UI quirks verifier | Add `scripts/verify_ui_quirks.py` using the existing subprocess + Playwright style; cover empty, malformed/off-topic, mixed VI-EN, bounded very-long text, and rapid repeated submit; capture console/page errors. [VERIFIED: scripts/verify_golden_prompts.py; scripts/measure_cold_latency.py; cited Playwright docs] | New `scripts/verify_ui_quirks.py`; optional helper tests such as `tests/runtime/test_ui_quirks_script.py` for pure parsing/output-path helpers. [VERIFIED: tests/runtime/test_latency_measurement.py pattern] | `.planning/phases/31-ui-quirks-edge-cases-regression-re-check/artifacts/31-ui-quirks-results.json` with cases, request counts, DOM counts, console messages, page errors, and pass/fail. [VERIFIED: Phase 28/30 artifact patterns] |
| 31-02 CLI clarity and launchers | Add argparse descriptions/help text and two double-click batch launchers; no subcommand or flag behavior changes. [VERIFIED: 31-CONTEXT.md; src/runtime/cli.py] | Modify `src/runtime/cli.py`; modify `tests/runtime/test_cli.py`; add `scripts/START_DEMO_UI.bat` and `scripts/START_TEXT_ANALYZE.bat`. [VERIFIED: 31-CONTEXT.md; tests/runtime/test_cli.py] | Captured `vnphish --help`, `vnphish analyze --help`, and `vnphish demo --help` output; launcher syntax/static smoke evidence. [VERIFIED: src/runtime/cli.py] |
| 31-03 Conditional UIQ-04 fixes | Only if the verifier finds app-origin issues: fix in existing vanilla assets, using i18n keys for copy and preserving approved CSS tokens and `data-slot` internals. [VERIFIED: 31-UI-SPEC.md] | Possible `src/runtime/demo_assets/demo.js`, `demo.css`, `i18n.js`, or `index.html`; do not change `src/runtime/demo.py` `/api/analyze` shape or service behavior unless a prior decision is reopened. [VERIFIED: 31-UI-SPEC.md; STATE.md] | Before/after verifier JSON; focused pytest for any changed static contract. [VERIFIED: tests/runtime/test_demo.py] |
| 31-04 Final regression re-check | Rerun Phase 28 golden-prompt stability and Phase 29 touched test suites after all fixes. [VERIFIED: 31-CONTEXT.md; 30-02-SUMMARY.md] | No expected source changes. [VERIFIED: 30-02-SUMMARY.md] | Fresh `scripts/verify_golden_prompts.py` result, `tests/runtime/test_local_model.py` green, `tests/runtime/test_demo.py` green, and `tests/runtime/test_cli.py` green if CLI help changed. [VERIFIED: 28-01-SUMMARY.md; 29-VERIFICATION.md] |

## Standard Stack

### Core

| Tool / Library | Version | Purpose | Why Standard |
|----------------|---------|---------|--------------|
| Vanilla HTML/CSS/JS | Existing static assets | Demo UI behavior and rendering | Project hard constraint: no JS framework and no build step. [VERIFIED: STATE.md; 31-UI-SPEC.md] |
| Python Playwright | 1.60.0 | Drive the real browser demo, capture `/api/analyze`, console, and page errors | Existing dependency and established Phase 28/30 pattern; official docs support `expect_response`, console, and page-error capture. [VERIFIED: pyproject.toml; importlib.metadata; CITED: https://playwright.dev/python/docs/api/class-page] |
| pytest | 9.0.3 | Focused regression tests for CLI/static/runtime helpers | Existing configured test runner in `pyproject.toml`; version verified locally. [VERIFIED: pyproject.toml; python -m pytest --version] |
| argparse | Python stdlib | CLI help/description text | Existing `src/runtime/cli.py` parser surface; no dependency required. [VERIFIED: src/runtime/cli.py] |

**Installation:** none. This phase must not add packages. [VERIFIED: 31-CONTEXT.md; STATE.md]

## Package Legitimacy Audit

No external package installation is recommended for Phase 31. [VERIFIED: 31-CONTEXT.md; pyproject.toml] Existing Playwright/pytest dependencies are already in the project and available in this environment. [VERIFIED: importlib.metadata; python -m pytest --version]

## Existing Patterns to Reuse

- `scripts/verify_golden_prompts.py` already owns a `vnphish demo` subprocess, waits for the server with `page.goto()`, uses `page.expect_response()` around `#analyze-button`, extracts JSON, waits for the busy state to clear, writes JSON on failure, and shuts down the subprocess. [VERIFIED: scripts/verify_golden_prompts.py]
- `scripts/measure_cold_latency.py` already loads locked prompts from `28-golden-prompt-results.json`, validates evidence arguments, captures Playwright response timing, records power/process metadata, and writes timestamped JSON artifacts. [VERIFIED: scripts/measure_cold_latency.py; tests/runtime/test_latency_measurement.py]
- `tests/runtime/test_demo.py` protects static HTML route behavior, absence of Google Fonts links, `data-slot` template internals, font route allowlist, and `/api/analyze` JSON error/contract behavior. [VERIFIED: tests/runtime/test_demo.py]
- `tests/runtime/test_cli.py` already inspects the parser and monkeypatches command handlers; add help-text assertions there rather than creating a second CLI test style. [VERIFIED: tests/runtime/test_cli.py]

## Code Examples

### Playwright Harness Shape

```python
# Source: existing scripts/verify_golden_prompts.py + official Playwright Page docs.
console_messages = []
page_errors = []
page.on("console", lambda msg: console_messages.append({"type": msg.type, "text": msg.text}))
page.on("pageerror", lambda exc: page_errors.append(str(exc)))

with page.expect_response(lambda response: "/api/analyze" in response.url, timeout=180_000) as info:
    page.click("#analyze-button")
response = info.value
payload = response.json()
page.wait_for_function("!document.querySelector('#analyze-button').disabled", timeout=5_000)
typing_count = page.locator(".message--typing").count()
```

`page.expect_response()` returns the matched response after the triggering action, and Playwright exposes `page.on("console")`, `page.on("pageerror")`, and `page.page_errors()` for console/error capture. [CITED: https://playwright.dev/python/docs/api/class-page]

### CLI Help Regression Pattern

```python
# Source: tests/runtime/test_cli.py parser-introspection pattern.
parser = cli_module.build_parser()
help_text = parser.format_help()
assert "demo" in help_text
assert "analyze" in help_text
```

Add subparser-level assertions for `analyze --help` and `demo --help` so the distinction is locked by tests, not just manual review. [VERIFIED: tests/runtime/test_cli.py; src/runtime/cli.py]

## Common Pitfalls

### Pitfall 1: False double-submit pass from button-only testing
**What goes wrong:** The button is disabled after first submit, so a double-click-only test may pass without exercising the actual re-entry path. [VERIFIED: src/runtime/demo_assets/demo.js]
**How to avoid:** In Playwright, submit once, immediately fill the still-editable textarea with a second message, and trigger Enter/form submit; assert exactly one terminal bot/error bubble remains for the surviving turn, zero `.message--typing`, no `AbortError` error bubble, and no uncaught page error. [VERIFIED: src/runtime/demo_assets/demo.js; 31-CONTEXT.md]

### Pitfall 2: Unconditional `finally` race in `demo.js`
**What goes wrong:** `analyzeMessage()` sets `currentController = null` and clears busy state in `finally` for every request, so an aborted request can race the surviving request's controller/state. [VERIFIED: src/runtime/demo_assets/demo.js]
**How to avoid:** The verifier must assert button state and controller-visible behavior after rapid re-entry; if it fails, the likely fix is to keep a local `controller` variable and only clear state when `currentController === controller`. [VERIFIED: src/runtime/demo_assets/demo.js]

### Pitfall 3: Long-input cap assumed but not implemented
**What goes wrong:** Planning around `runtime_max_text_chars` would be unsafe because the current settings/service code does not define or enforce it. [VERIFIED: codebase rg; src/config/settings.py; src/runtime/service.py]
**How to avoid:** Use a bounded long input with a hard Playwright timeout and record whether the app returns a result/error bubble, wraps text, clears typing, and stays interactive. [VERIFIED: 31-UI-SPEC.md]

### Pitfall 4: Open-ended `SOURCE_LANG_VI` chase
**What goes wrong:** A browser-extension or DevTools artifact can waste implementation time. [VERIFIED: 29-04-SUMMARY.md; 29-VERIFICATION.md]
**How to avoid:** Capture console in clean Playwright Chromium and in the original human browser; if clean Playwright has no app-origin source and local `rg` still finds no key, document non-app origin and stop. [VERIFIED: codebase rg; CITED: https://playwright.dev/python/docs/api/class-page]

### Pitfall 5: Template/id regression from UI fixes
**What goes wrong:** Adding IDs inside cloned templates can reintroduce the old template collision class. [VERIFIED: STATE.md; tests/runtime/test_demo.py]
**How to avoid:** Any UIQ-04 fix must preserve `data-slot` internals and rerun `tests/runtime/test_demo.py`. [VERIFIED: 31-UI-SPEC.md; tests/runtime/test_demo.py]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Browser regression driving | Raw `requests.post()` script | Playwright driving `vnphish demo` | Direct HTTP bypasses DOM rendering, console errors, typing cleanup, and the real user path. [VERIFIED: 31-CONTEXT.md; scripts/verify_golden_prompts.py] |
| Double-submit mitigation | New threaded/async server | Existing client `AbortController` guard, verified/fixed in `demo.js` if needed | Server replacement would violate the frozen backend posture and add risk. [VERIFIED: STATE.md; .planning/research/PITFALLS.md] |
| CLI clarity | Rename subcommands or restructure flags | Additive argparse help text plus `.bat` launchers | User decision explicitly keeps the CLI contract unchanged. [VERIFIED: 31-CONTEXT.md] |
| UI quirk fixes | New framework, component library, icon library, or build step | Existing vanilla assets and UI-SPEC tokens | Project/UI-SPEC prohibit new UI stack choices for this phase. [VERIFIED: STATE.md; 31-UI-SPEC.md] |
| Console triage | Custom DevTools parser | Playwright console/page-error events plus manual DevTools screenshot/note | Official Playwright API already exposes console and page error data. [CITED: https://playwright.dev/python/docs/api/class-page] |

## Verification Commands

```powershell
python scripts\verify_ui_quirks.py --port 8766 --output .planning\phases\31-ui-quirks-edge-cases-regression-re-check\artifacts\31-ui-quirks-results.json
python scripts\verify_golden_prompts.py --runs 5 --port 8766
python -m pytest tests\runtime\test_local_model.py tests\runtime\test_demo.py tests\runtime\test_cli.py -q
python -m src.runtime.cli doctor
python -m src.runtime.cli --help
python -m src.runtime.cli analyze --help
python -m src.runtime.cli demo --help
rg -n "localStorage|fonts.googleapis.com|fonts.gstatic.com|result-summary|error-message" src/runtime/demo_assets tests/runtime/test_demo.py
```

The first command names a recommended new script; it will not exist until Phase 31 implementation creates it. [VERIFIED: 31-CONTEXT.md] Use a non-default port if another demo server is already running. [VERIFIED: scripts/verify_golden_prompts.py; scripts/measure_cold_latency.py]

## Evidence Requirements

| Evidence | Required Content |
|----------|------------------|
| `31-ui-quirks-results.json` | Case name, input class, channel, response status if any, risk/labels or error payload, request/response counts, `.message--typing` final count, bot/error bubble count, button disabled final state, console messages, page errors, screenshot path on failure. [VERIFIED: Phase 28/30 artifact patterns; cited Playwright docs] |
| CLI help evidence | Before/after text or captured command output proving `analyze` says text-only/no browser and `demo` says opens the web UI. [VERIFIED: 31-CONTEXT.md] |
| Launcher evidence | Static review or smoke output proving `START_DEMO_UI.bat` launches `python -m src.runtime.cli demo` from repo root and `START_TEXT_ANALYZE.bat` launches the text-only analyze path. [VERIFIED: .planning/research/ARCHITECTURE.md; 31-CONTEXT.md] |
| Final regression note | Fresh golden-prompt run plus focused pytest outputs, recorded after any UIQ-04 fix. [VERIFIED: 31-CONTEXT.md] |
| Console triage note | Whether `ERROR SOURCE_LANG_VI` reproduced in clean Playwright, original browser, both, or neither; if non-app, document stop condition. [VERIFIED: 29-VERIFICATION.md; 31-CONTEXT.md] |

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| Python | Scripts, pytest, CLI | Yes | 3.13.13 | None needed. [VERIFIED: python --version] |
| pytest | Regression tests | Yes | 9.0.3 | Manual command review is insufficient; pytest is available. [VERIFIED: python -m pytest --version] |
| Playwright Python | Real-demo browser verifier | Yes | 1.60.0 | Manual browser run only if Playwright unexpectedly fails on target machine. [VERIFIED: importlib.metadata] |
| Playwright Chromium | Headless real-browser automation | Yes | Launch smoke passed | Headed manual DevTools for `SOURCE_LANG_VI` comparison. [VERIFIED: chromium launch smoke] |
| GSD tools | Research cache/protocol | Yes | local shim present | Not required for implementation. [VERIFIED: init.phase-op] |

**Missing dependencies with no fallback:** none found in this session. [VERIFIED: environment probes]

## Security Domain

| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | No | Local loopback demo has no auth change in scope. [VERIFIED: src/runtime/demo.py; STATE.md] |
| V3 Session Management | No | Chat history remains in memory only; `localStorage` is prohibited. [VERIFIED: STATE.md; src/runtime/demo_assets/demo.js] |
| V4 Access Control | No | No new remote endpoint or multi-user access is planned. [VERIFIED: STATE.md; 31-CONTEXT.md] |
| V5 Input Validation | Yes | Preserve existing `/api/analyze` JSON/text/channel validation and client `required` behavior; add UI tests rather than widening accepted inputs. [VERIFIED: src/runtime/demo.py; index.html] |
| V6 Cryptography | No | No crypto change. [VERIFIED: 31-CONTEXT.md] |

Known threat pattern: accidentally persisting or logging raw pasted text would violate the local/privacy posture; the new verifier artifacts should record classifications and sanitized case names, not full arbitrary user-entered raw messages except for the already-locked golden prompts and deliberate test fixtures. [VERIFIED: STATE.md; tests/runtime/test_privacy.py]

## Open Questions

1. **What is the accepted behavior for very-long text if the model cannot return within the harness timeout?**
   - What we know: no current `runtime_max_text_chars` enforcement was found, and the backend contract is frozen. [VERIFIED: codebase rg; src/config/settings.py; src/runtime/service.py; STATE.md]
   - Recommendation: plan a bounded long-input case first; if it fails, treat the smallest client-side guard or documented manual boundary as a UIQ-04 decision point before changing backend behavior. [VERIFIED: 31-UI-SPEC.md]

2. **Does `SOURCE_LANG_VI` reproduce outside the user's original browser profile?**
   - What we know: Phase 29 reported it, and local source search found no matching key/string. [VERIFIED: 29-04-SUMMARY.md; codebase rg]
   - Recommendation: compare clean Playwright Chromium against the original browser DevTools; stop once non-app origin is confirmed. [VERIFIED: 31-CONTEXT.md; cited Playwright docs]

## Assumptions Log

No `[ASSUMED]` claims are used as planning inputs. All implementation recommendations above are grounded in local files, prior phase artifacts, environment probes, or official Playwright documentation. [VERIFIED: local research pass]

## Sources

### Primary
- `.planning/phases/31-ui-quirks-edge-cases-regression-re-check/31-CONTEXT.md` — locked decisions, scope, canonical refs, discretion, deferred items. [VERIFIED: local file read]
- `.planning/phases/31-ui-quirks-edge-cases-regression-re-check/31-UI-SPEC.md` — approved UI contract and regression acceptance bar. [VERIFIED: local file read]
- `.planning/REQUIREMENTS.md`, `.planning/STATE.md`, `.planning/ROADMAP.md` — UIQ-01 through UIQ-04, milestone constraints, Phase 31 success criteria. [VERIFIED: local file read]
- `scripts/verify_golden_prompts.py`, `scripts/measure_cold_latency.py`, `src/runtime/cli.py`, `src/runtime/demo.py`, `src/runtime/demo_assets/*`, `tests/runtime/test_cli.py`, `tests/runtime/test_demo.py`, `tests/runtime/test_local_model.py` — current implementation and test patterns. [VERIFIED: local file read]
- Phase 28-30 summaries and artifacts listed in the user prompt — golden prompt baseline, offline watchpoint, and `NO_FIX_APPLIED` latency decision. [VERIFIED: local file read]

### Official Documentation
- Playwright Python Page API: `expect_response`, `on("console")`, `on("pageerror")`, and `page_errors()`. [CITED: https://playwright.dev/python/docs/api/class-page]

### Environment Probes
- `python --version` -> Python 3.13.13. [VERIFIED: terminal probe]
- `python -m pytest --version` -> pytest 9.0.3. [VERIFIED: terminal probe]
- `importlib.metadata.version("playwright")` -> Playwright 1.60.0; Chromium launch smoke passed. [VERIFIED: terminal probe]
- No `AGENTS.md`, no project-local `.codex/skills` or `.agents/skills`, and no `.planning/graphs/graph.json` found. [VERIFIED: terminal probe]

## RESEARCH COMPLETE
