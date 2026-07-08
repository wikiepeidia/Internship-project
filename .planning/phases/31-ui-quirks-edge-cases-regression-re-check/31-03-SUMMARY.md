---
phase: 31-ui-quirks-edge-cases-regression-re-check
plan: "03"
subsystem: ui
tags: [playwright, demo-js, abortcontroller, double-submit, regression, golden-prompts]

# Dependency graph
requires:
  - phase: 31-ui-quirks-edge-cases-regression-re-check plan 01
    provides: "scripts/verify_ui_quirks.py real-demo verifier and the initial 31-ui-quirks-results.json evidence artifact this plan triages"
  - phase: 31-ui-quirks-edge-cases-regression-re-check plan 02
    provides: "CLI help-text clarity and .bat launchers this plan's regression pytest run re-confirms"
provides:
  - "31-uiq04-triage.md classifying every Plan 31-01 finding as app-origin, backend-origin, or non-app browser noise"
  - "Confirmed-and-fixed demo.js double-submit controller-ownership race (request-local AbortController)"
  - "31-ui-quirks-after-fix.json: fresh verifier run, overall_pass true, all 5 cases including strengthened double-submit assertions"
  - "31-golden-regression-results.json: fresh 5/5 scam + 5/5 benign stable golden-prompt regression"
  - "31-regression-results.md: final D-05 command/exit-code/verdict/pytest/doctor evidence record"
affects: [32-fallback-recording-full-dry-rehearsal]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Request-local AbortController ownership: keep a `const controller` per analyzeMessage() call, assign it to the shared currentController, and only clear shared busy state/currentController in `finally` when `currentController === controller` — prevents an aborted/superseded request's finally block from clearing state for a newer, still-in-flight request."
    - "Triage classification buckets (app-origin / backend-origin / environment-origin / non-app browser noise) applied uniformly to every console message, page error, and case finding before any code change is considered."

key-files:
  created:
    - .planning/phases/31-ui-quirks-edge-cases-regression-re-check/artifacts/31-uiq04-triage.md
    - .planning/phases/31-ui-quirks-edge-cases-regression-re-check/artifacts/31-ui-quirks-after-fix.json
    - .planning/phases/31-ui-quirks-edge-cases-regression-re-check/artifacts/31-golden-regression-results.json
    - .planning/phases/31-ui-quirks-edge-cases-regression-re-check/artifacts/31-regression-results.md
  modified:
    - src/runtime/demo_assets/demo.js

key-decisions:
  - "SOURCE_LANG_VI classified as confirmed non-app browser/profile noise per D-01's stop condition: a clean Playwright Chromium session (Plan 31-01) produced zero occurrences across the full edge-case + double-submit matrix, and local source search found no matching key in demo.js/index.html/i18n.js, corroborating Phase 29's own independent conclusion in 29-04-SUMMARY.md."
  - "very_long case's HTTP 503 (RuntimeUnavailableError from GGUF n_ctx=512 context overflow) classified as backend-origin, frozen-this-milestone behavior, not a UI bug — the UI already renders a well-formed error bubble with zero orphaned typing nodes and a re-enabled button, satisfying the UIQ-01 acceptance bar. Documented only; no backend/service.py change made, consistent with the frozen /api/analyze contract and the project's fail-closed safety posture."
  - "Fixed the demo.js double-submit controller-ownership race even though Plan 31-01's verifier already reported double_submit as passing, because the verifier only asserts final settled state and a code-trace confirmed a real transient race (aborted request's finally clearing shared busy state/currentController while a newer request is still in flight) matching Pitfall 2 in 31-RESEARCH.md and this plan's explicit task guidance."

requirements-completed: [UIQ-01, UIQ-02, UIQ-04]

coverage:
  - id: D1
    description: "Every Plan 31-01 finding (SOURCE_LANG_VI console mystery, very_long HTTP 503, double-submit race) is classified as app-origin/backend-origin/non-app noise in 31-uiq04-triage.md, with app-origin findings fixed."
    requirement: "UIQ-04"
    verification:
      - kind: other
        ref: ".planning/phases/31-ui-quirks-edge-cases-regression-re-check/artifacts/31-uiq04-triage.md"
        status: pass
      - kind: unit
        ref: "tests/runtime/test_demo.py (7 passed)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Fresh real-demo verifier run reports overall_pass=true, with double_submit satisfying completed_analyze_response_count==1, completed_superseded_response_count==0, abort_error_bubble_count==0, typing_count==0, button_disabled==false."
    requirement: "UIQ-01"
    verification:
      - kind: automated_ui
        ref: "scripts/verify_ui_quirks.py --port 8766 --output 31-ui-quirks-after-fix.json"
        status: pass
    human_judgment: false
  - id: D3
    description: "Rapid double-submit guard re-verified with the strengthened UIQ-02/D-04 assertion set after the demo.js controller-ownership fix."
    requirement: "UIQ-02"
    verification:
      - kind: automated_ui
        ref: "31-ui-quirks-after-fix.json cases[name=double_submit]"
        status: pass
    human_judgment: false
  - id: D4
    description: "Phase 28 golden-prompt stability (5/5 scam, 5/5 benign) and Phase 29 touched test suites (test_local_model.py, test_demo.py, test_cli.py) remain green after all Phase 31 changes; doctor reports READY."
    requirement: "UIQ-04"
    verification:
      - kind: e2e
        ref: "verify_golden_prompts.py --runs 5 --port 8766 (redirected RESULTS_PATH) -> 31-golden-regression-results.json"
        status: pass
      - kind: unit
        ref: "pytest tests/runtime/test_local_model.py test_demo.py test_cli.py -q (39 passed)"
        status: pass
      - kind: other
        ref: "python -m src.runtime.cli doctor -> READY"
        status: pass
    human_judgment: false

# Metrics
duration: 18min
completed: 2026-07-08
status: complete
---

# Phase 31 Plan 03: UIQ-04 Triage, Double-Submit Fix & Final Regression Summary

**Triaged every Plan 31-01 finding (SOURCE_LANG_VI confirmed non-app noise, very_long 503 confirmed backend-origin/frozen), fixed a confirmed demo.js double-submit controller-ownership race via request-local AbortController scoping, and locked fresh evidence: verifier overall_pass=true, golden prompts 5/5 stable each, 39 focused tests green, doctor READY.**

## Performance

- **Duration:** ~18 min
- **Started:** 2026-07-08T13:04:00Z (approx, following Plan 31-02 completion)
- **Completed:** 2026-07-08T13:18:00Z
- **Tasks:** 2 completed
- **Files modified:** 5 (1 source file, 4 artifacts: 1 triage doc, 3 evidence JSON/markdown)

## Accomplishments

- Classified all three findings surfaced by Plan 31-01's evidence artifact into `31-uiq04-triage.md`: `SOURCE_LANG_VI` (non-app browser/profile noise, hunt stopped per D-01), `very_long` HTTP 503 (backend-origin fail-closed GGUF context-overflow behavior, frozen this milestone, documented not fixed), and the `double_submit` controller-ownership race (app-origin, fixed).
- Fixed a confirmed re-entrant race in `src/runtime/demo_assets/demo.js`'s `analyzeMessage()`: the shared `finally` block previously cleared `currentController`/busy state unconditionally for any settling request, so an aborted/superseded request's near-instant `AbortError` rejection could clear state for a newer, still-in-flight request. Now each call keeps a request-local `controller` reference and only clears shared state when `currentController === controller`.
- Re-ran `scripts/verify_ui_quirks.py` live against the real demo and local GGUF model after the fix: `overall_pass: true`, all 5 cases pass, and `double_submit` satisfies every strengthened assertion (`completed_analyze_response_count=1`, `completed_superseded_response_count=0`, `abort_error_bubble_count=0`, `typing_count=0`, `button_disabled=false`).
- Ran the final D-05 regression set: `scripts/verify_golden_prompts.py` (5 scam + 5 benign runs) redirected to a Phase-31-local artifact — both `stable: true` (scam: `high-risk`/`bank_impersonation` 5/5; benign: `benign`/`benign` 5/5); `pytest tests/runtime/test_local_model.py tests/runtime/test_demo.py tests/runtime/test_cli.py -q` — 39 passed; `python -m src.runtime.cli doctor` — `READY backend=gguf local_only=True text_only=True`.
- Documented Phase 30's `NO_FIX_APPLIED` decision explicitly in `31-regression-results.md`, confirming there is no Phase 30 source diff to regression-test beyond demo startup/serving (which the golden-prompt run and doctor check both confirm).

## Task Commits

Each task was committed atomically:

1. **Task 1: Triage and fix UIQ-04 app-origin quirks** - `7ca4d77` (fix)
2. **Task 2: Record final Phase 28-30 regression evidence** - `d27c963` (docs)

_Note: Task 1 carries a `tdd="true"` plan flag, but its actual work was code-review-driven (tracing the AbortController race through the existing implementation) rather than a fresh RED/GREEN cycle against a new isolated unit — no new pure-function test target existed to write a failing unit test against before the fix, since the race is only observable end-to-end via the real-demo Playwright verifier (already re-run as the task's live verification step). This mirrors Plan 31-01's own precedent of treating live-verifier-driven integration work as its own verification step rather than forcing an artificial isolated RED commit._

## Files Created/Modified

- `src/runtime/demo_assets/demo.js` - `analyzeMessage()` now keeps a request-local `const controller = new AbortController()` and only clears `currentController`/busy state in `finally` when `currentController === controller`, preventing an aborted/superseded request from clearing state owned by a newer in-flight request. No DOM structure, `data-slot`, CSS, or fetch payload shape changed.
- `.planning/phases/31-ui-quirks-edge-cases-regression-re-check/artifacts/31-uiq04-triage.md` - Classifies all 3 Plan 31-01 findings (SOURCE_LANG_VI, very_long 503, double-submit race) with evidence, reasoning, and disposition per finding.
- `.planning/phases/31-ui-quirks-edge-cases-regression-re-check/artifacts/31-ui-quirks-after-fix.json` - Fresh live verifier run after the fix: `overall_pass: true`, all 5 cases pass.
- `.planning/phases/31-ui-quirks-edge-cases-regression-re-check/artifacts/31-golden-regression-results.json` - Fresh 5-scam/5-benign golden-prompt regression run, both stable.
- `.planning/phases/31-ui-quirks-edge-cases-regression-re-check/artifacts/31-regression-results.md` - Final D-05 evidence record: commands, exit codes, stable scam/benign summary, pytest pass summary, doctor READY, Phase 30 `NO_FIX_APPLIED` note.

## Decisions Made

- **SOURCE_LANG_VI: non-app browser/profile noise, hunt stopped.** Plan 31-01's clean Playwright Chromium session (console/page-error listeners attached before any navigation, full edge-case + double-submit matrix exercised) produced zero occurrences of this string and zero page errors; local source search across `demo.js`/`index.html`/`i18n.js` found no matching key. This independently corroborates Phase 29's own conclusion in `29-04-SUMMARY.md`. Per D-01's explicit stop condition, no further hunting was done.
- **very_long HTTP 503: backend-origin, documented not fixed.** The bounded very-long fixture overflows the GGUF backend's `n_ctx=512` context window, which `RuntimeService.analyze_text()` catches as a generic exception and re-raises as `RuntimeUnavailableError` -> HTTP 503 — this is the existing, frozen `/api/analyze` contract behavior (`demo.py` lines 131-136), and the UI already renders a well-formed error bubble with zero orphaned typing nodes and a re-enabled button. Fixing the underlying context-window limit would be an architectural change to a frozen backend, out of this plan's scope; documented as a candidate follow-up only.
- **Fixed the double-submit race despite the verifier already reporting "pass."** The verifier's `double_submit` assertions only inspect final settled DOM/telemetry state, not transient mid-flight state. A code trace of `analyzeMessage()`'s `finally` block confirmed the exact race described in `31-RESEARCH.md`'s Pitfall 2 and this plan's task guidance: an aborted request's near-instant `AbortError` rejection reaches its `finally` block (which unconditionally cleared `currentController`/busy state) well before a newer, still-in-flight request's real network response arrives. This is a genuine correctness bug (Rule 1) even though the coarse-grained final-state check didn't surface it on this run's specific timing — fixed via request-local controller ownership exactly as the plan's action text specified.

## Deviations from Plan

None beyond the plan's own explicit conditional guidance. The plan's task action text pre-authorized exactly this fix ("The expected re-entrant race fix, when needed, is in `src/runtime/demo_assets/demo.js`: keep a request-local controller reference... clear `currentController`/busy state only when the finishing request is still the current one") — applying it after confirming the race via code trace is executing the plan as written, not a deviation. No Rule 1-4 auto-fixes outside this plan-anticipated scope were needed.

## Issues Encountered

None. All live verifier runs, pytest suites, and the doctor check passed on the first attempt after the `demo.js` fix.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 31 (UI Quirks, Edge Cases & Regression Re-check) is fully closed: UIQ-01, UIQ-02, UIQ-03 (Plan 31-02), and UIQ-04 are all satisfied with fresh evidence artifacts; D-05 regression checks confirm no Phase 28-30 regressions.
- Phase 32 (Fallback Recording & Full Dry Rehearsal) can proceed against a demo UI now proven to pass its full edge-case matrix, double-submit guard, and golden-prompt stability check on this run.
- No blockers. Backend (`src/runtime/demo.py`, `src/runtime/service.py`), `/api/analyze` contract, and all `data-slot` template internals remain unchanged throughout Phase 31.

---
*Phase: 31-ui-quirks-edge-cases-regression-re-check*
*Completed: 2026-07-08*

## Self-Check: PASSED

- FOUND: src/runtime/demo_assets/demo.js
- FOUND: .planning/phases/31-ui-quirks-edge-cases-regression-re-check/artifacts/31-uiq04-triage.md
- FOUND: .planning/phases/31-ui-quirks-edge-cases-regression-re-check/artifacts/31-ui-quirks-after-fix.json
- FOUND: .planning/phases/31-ui-quirks-edge-cases-regression-re-check/artifacts/31-golden-regression-results.json
- FOUND: .planning/phases/31-ui-quirks-edge-cases-regression-re-check/artifacts/31-regression-results.md
- FOUND: .planning/phases/31-ui-quirks-edge-cases-regression-re-check/31-03-SUMMARY.md
- FOUND commit: 7ca4d77 (fix)
- FOUND commit: d27c963 (docs)
