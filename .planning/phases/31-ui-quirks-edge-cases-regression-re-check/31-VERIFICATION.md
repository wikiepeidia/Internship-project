---
phase: 31-ui-quirks-edge-cases-regression-re-check
verified: 2026-07-08T13:30:48Z
status: passed
score: 6/6 must-haves verified
overrides_applied: 0
---

# Phase 31: UI Quirks, Edge Cases & Regression Re-check Verification Report

**Phase Goal:** The demo handles the full edge-case matrix without crash or hang, the `analyze`-vs-`demo` CLI entrypoint confusion is resolved, and any fixes from Phases 28-30 have not regressed existing behavior.
**Verified:** 2026-07-08T13:30:48Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Full edge-case matrix (empty, very-long, malformed/off-topic, mixed VI-EN) completes with no crash or hang, driven through the real browser demo | VERIFIED | Independently re-ran `python scripts/verify_ui_quirks.py --port 8767 --output <scratch>.json` live against the real `vnphish demo` subprocess + local GGUF model. Fresh run reproduced `overall_pass: true`, all 4 edge-case entries `passed: true`, `typing_count: 0`, correct terminal-bubble counts, zero new page errors — independent of the claimed `31-ui-quirks-after-fix.json` artifact. |
| 2 | Rapid double-submit leaves exactly one completed response, no superseded response, no AbortError bubble, zero typing nodes, button re-enabled | VERIFIED | Same live re-run: `double_submit` case shows `completed_analyze_response_count: 1`, `completed_superseded_response_count: 0`, `abort_error_bubble_count: 0`, `typing_count: 0`, `button_disabled: false`. Code inspection of `src/runtime/demo_assets/demo.js` lines 128-183 confirms the request-local `AbortController` ownership fix (`if (currentController === controller) { setBusyState(false); currentController = null; }`) is actually present, not just claimed. |
| 3 | CLI help text and/or launchers make `vnphish analyze` (text-only) vs `vnphish demo` (web UI) distinction clear, CLI contract unchanged | VERIFIED | Ran `python -m src.runtime.cli --help`, `analyze --help`, `demo --help` live. Output text explicitly states "Use 'analyze' for terminal text-only checks (no browser). Use 'demo' to start the local browser web UI," and command set is exactly `{analyze, doctor, demo}` — unchanged. `scripts/START_DEMO_UI.bat` and `scripts/START_TEXT_ANALYZE.bat` exist, `cd /d "%~dp0.."`, `chcp 65001`, invoke the correct subcommands, and do not interpolate pasted text into cmd variables (read directly). |
| 4 | All UI quirks found are catalogued and either fixed (app-origin) or documented (non-app), without altering the frozen backend contract or `data-slot` templates | VERIFIED | `31-uiq04-triage.md` classifies all 3 findings (`SOURCE_LANG_VI` = non-app noise, `very_long` 503 = backend-origin/frozen, `double_submit` race = app-origin/fixed). `git show --stat 7ca4d77` confirms only `demo.js` plus artifacts changed — `demo.py`, `service.py`, `index.html` `data-slot` templates untouched. `tests/runtime/test_demo.py` re-run live: 7/7 passed. |
| 5 | `tests/runtime` suite passes green after all Phase 31 changes | VERIFIED | Independently re-ran `python -m pytest tests/runtime/test_ui_quirks_script.py tests/runtime/test_cli.py tests/runtime/test_demo.py -q` -> 30 passed. Also re-ran the plan's exact regression command `python -m pytest tests/runtime/test_local_model.py tests/runtime/test_demo.py tests/runtime/test_cli.py -q` -> 39 passed, matching the SUMMARY's claimed count exactly. |
| 6 | D-05: Phase 28 golden-prompt stability and Phase 29 environment fixes are not regressed | VERIFIED | `31-golden-regression-results.json` shows `golden_scam.stable: true` (5/5 `high-risk`/`bank_impersonation`) and `golden_benign.stable: true` (5/5 `benign`/`benign`), matching the Phase 28-locked verdicts. Independently re-ran `python -m src.runtime.cli doctor` live -> `READY backend=gguf local_only=True text_only=True`, all 12 doctor checks PASS, matching `31-regression-results.md`'s claim. |

**Score:** 6/6 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `scripts/verify_ui_quirks.py` | Reusable real-demo Playwright verifier for edge cases, double-submit, console/page-error capture | VERIFIED | Exists (21KB), `SCHEMA_VERSION`/`CASE_NAMES` present, `overall_pass` is derived (`bool(cases) and all(passed)`), not hardcoded. Live-executed successfully during this verification. |
| `tests/runtime/test_ui_quirks_script.py` | Fast unit coverage for verifier helpers | VERIFIED | Exists, 10 tests, all pass (confirmed via live pytest run). |
| `.planning/.../artifacts/31-ui-quirks-results.json` | Initial UIQ-01/02/04 evidence | VERIFIED | Exists, schema matches, `overall_pass: true`, all 5 cases present. |
| `.planning/.../artifacts/31-ui-quirks-after-fix.json` | Passing verifier run after fixes | VERIFIED | Exists, `overall_pass: true`; independently reproduced with a fresh live run producing identical pass pattern. |
| `.planning/.../artifacts/31-uiq04-triage.md` | Quirk classification and fix notes | VERIFIED | Exists, classifies all 3 findings with reasoning and disposition. |
| `.planning/.../artifacts/31-golden-regression-results.json` | Fresh 5-run scam/benign regression evidence | VERIFIED | Exists, both `stable: true`. |
| `.planning/.../artifacts/31-regression-results.md` | Final command evidence for golden prompts, tests, doctor | VERIFIED | Exists, contains commands, exit codes, `READY`, `NO_FIX_APPLIED` note — all independently re-confirmed live in this verification. |
| `src/runtime/cli.py` | Additive argparse help/description text | VERIFIED | `analyze`/`demo` help text explicitly disambiguates terminal vs. browser; command set unchanged. |
| `tests/runtime/test_cli.py` | Regression coverage for CLI help + launchers | VERIFIED | 13 test functions present including all claimed help-text and launcher-safety tests; all pass. |
| `scripts/START_DEMO_UI.bat` | Double-click launcher for web UI | VERIFIED | Exists, correct subcommand (`demo`), repo-root cd, UTF-8 chcp. |
| `scripts/START_TEXT_ANALYZE.bat` | Double-click launcher for terminal analyzer | VERIFIED | Exists, correct subcommand (`analyze`), no text interpolation into cmd variables. |
| `src/runtime/demo_assets/demo.js` | Request-local `AbortController` ownership fix | VERIFIED | Code read directly: `finally` block only clears shared state `if (currentController === controller)`, exactly matching the claimed fix. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `scripts/verify_ui_quirks.py` | `src.runtime.cli demo` | `subprocess.Popen([sys.executable, "-m", "src.runtime.cli", "demo", "--no-browser", "--port", ...])` | WIRED | Confirmed via grep (line 193) and live execution — subprocess actually starts the real demo server. |
| `scripts/verify_ui_quirks.py` | `POST /api/analyze` | Playwright drives real browser form/Enter submission and fetch instrumentation | WIRED | Confirmed via grep (`/api/analyze` referenced 4x) and live run — actual HTTP request/response counts populate the artifact (backend log shows real `POST /api/analyze` calls). |
| `scripts/START_DEMO_UI.bat` | `src/runtime/cli.py` | `python -m src.runtime.cli demo` | WIRED | Confirmed in file content. |
| `scripts/START_TEXT_ANALYZE.bat` | `src/runtime/cli.py` | `python -m src.runtime.cli analyze` | WIRED | Confirmed in file content. |
| `31-ui-quirks-results.json` | `src/runtime/demo_assets/*` | Only app-origin failures justify vanilla asset changes | WIRED | `31-uiq04-triage.md` traces each finding to a disposition; `git show --stat 7ca4d77` confirms only `demo.js` was touched (the one app-origin finding), consistent with the triage decision. |
| `src/runtime/demo_assets/index.html` | `tests/runtime/test_demo.py` | Template/static-contract tests preserve `data-slot` internals | WIRED | `test_demo.py` re-run live: 7/7 passed, confirming no template/contract regression. |
| `31-golden-regression-results.json` | Phase 28 locked prompts | `verify_golden_prompts.py` logic, redirected `RESULTS_PATH` | WIRED | Golden scam/benign text in the artifact matches Phase 28's locked prompts (Vietcombank no-OTP scam, VPBank Smart OTP benign); `stable: true` for both. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|---------------------|--------|
| `31-ui-quirks-after-fix.json` `overall_pass` | `overall_pass` | `build_artifact()`: `overall_pass = bool(cases) and all(case.get("passed") is True for case in cases)` | Yes | FLOWING — derived boolean, not hand-set. Verified twice: once via the executor's committed artifact, once via an independent fresh live run in this verification producing the same result against the real GGUF backend. |
| `31-golden-regression-results.json` verdicts | `risk_tier`/`threat_labels` | Real GGUF model inference via `vnphish demo` subprocess, 5 scam + 5 benign live HTTP round-trips | Yes | FLOWING — non-trivial per-run latency (15-22s each, consistent with real local LLM inference, not a stub/mock). |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full edge-case + double-submit matrix passes live | `python scripts/verify_ui_quirks.py --port 8767 --output <scratch>.json` | `overall_pass: true`, all 5 cases pass, identical pattern to committed artifact | PASS |
| Focused unit/regression suites pass | `python -m pytest tests/runtime/test_ui_quirks_script.py tests/runtime/test_cli.py tests/runtime/test_demo.py -q` | `30 passed` | PASS |
| Plan 31-03's exact final regression command | `python -m pytest tests/runtime/test_local_model.py tests/runtime/test_demo.py tests/runtime/test_cli.py -q` | `39 passed` (matches SUMMARY claim exactly) | PASS |
| Doctor readiness | `python -m src.runtime.cli doctor` | `READY backend=gguf local_only=True text_only=True`, 12/12 checks PASS | PASS |
| CLI help disambiguation | `python -m src.runtime.cli --help` / `analyze --help` / `demo --help` | Text explicitly distinguishes terminal-only `analyze` from browser-launching `demo`; command set unchanged | PASS |
| UI-SPEC long-token wrap concern (informational, beyond plan scope) | Custom Playwright script filling `VERY_LONG_TEXT` into `#message-input` and measuring `.message__bubble`/`.message__text` `scrollWidth` vs `clientWidth` | `scrollWidth === clientWidth` for both (760px/760px, 726px/726px) — no horizontal overflow | PASS (no code change needed; confirms UI-SPEC's wrap requirement is already satisfied by default browser line-breaking on the URL's hyphens/slashes) |

### Probe Execution

Not applicable — no `scripts/*/tests/probe-*.sh` convention exists in this project, and no plan/summary text references a probe-based verification harness for this phase.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|--------------|--------|----------|
| UIQ-01 | 31-01, 31-03 | Full edge-case matrix re-tested, no crash/hang | SATISFIED | Live verifier re-run, all 4 edge cases pass. |
| UIQ-02 | 31-01, 31-03 | Rapid double-submit guard re-verified | SATISFIED | Live verifier re-run + code-level fix confirmed in `demo.js`. |
| UIQ-03 | 31-02 | CLI entrypoint confusion resolved via help text/launchers | SATISFIED | Live `--help` output + `.bat` launcher content confirmed. |
| UIQ-04 | 31-01, 31-03 | UI quirks catalogued/fixed without backend/template breakage | SATISFIED | `31-uiq04-triage.md` + `git show --stat` confirms scope discipline; `test_demo.py` green. |

No orphaned requirements — `.planning/REQUIREMENTS.md` maps exactly UIQ-01 through UIQ-04 to Phase 31, and all four appear in at least one plan's `requirements`/`requirements_addressed` frontmatter (31-01: UIQ-01/02/04; 31-02: UIQ-03; 31-03: UIQ-01/02/04).

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `tests/runtime/test_demo.py` | 198 | `"PLACEHOLDER"` string match | None (false positive) | Asserts a legitimate i18n key name (`PLACEHOLDER` = textarea placeholder copy key in `i18n.js`), not a stub/debt marker. Verified `i18n.js` line 24 contains real Vietnamese placeholder copy. |

No `TBD`/`FIXME`/`XXX`/`TODO`/`HACK` debt markers found in any file modified by this phase (`scripts/verify_ui_quirks.py`, `src/runtime/cli.py`, `src/runtime/demo_assets/demo.js`, both `.bat` launchers, and the three touched test files).

### Human Verification Required

None. All success criteria and must-haves were verified programmatically, including live re-execution of the browser verifier, CLI help commands, pytest suites, and the doctor check — each independently reproduced rather than trusted from SUMMARY.md claims. No `<human-check>` blocks were deferred by any Phase 31 PLAN.md.

### Gaps Summary

No gaps found. All 6 observable truths verified, all 12 required artifacts exist/are substantive/are wired, all 7 key links wired, requirements coverage complete with no orphans, no debt markers in phase-modified files, and 5 independent live behavioral re-executions (verifier, pytest x2, doctor, CLI help) reproduced the same results claimed in the SUMMARY.md files — not merely trusted them.

One informational note: the UI-SPEC's "long unbroken tokens must wrap rather than overflow horizontally" acceptance-bar detail for the `very_long` case was not asserted by the phase's own automated verifier (it only checks DOM counts/status, not `scrollWidth`/`clientWidth`). This verification independently spot-checked it live and confirmed no overflow occurs in practice, so it is not a gap — but future phases touching long-text rendering should be aware the verifier doesn't cover this dimension.

---

_Verified: 2026-07-08T13:30:48Z_
_Verifier: Claude (gsd-verifier)_
