---
phase: 31-ui-quirks-edge-cases-regression-re-check
plan: "01"
subsystem: testing
tags: [playwright, verifier, ui-quirks, double-submit, console-capture, wsgiref]

# Dependency graph
requires:
  - phase: 28-baseline-readiness-zero-code-diagnostics
    provides: verify_golden_prompts.py subprocess + Playwright pattern reused for the new verifier
  - phase: 30-latency-diagnosis-targeted-fix
    provides: measure_cold_latency.py stronger subprocess lifecycle (stdout/stderr capture, sys.executable -m src.runtime.cli demo) reused directly
provides:
  - scripts/verify_ui_quirks.py real-demo Playwright verifier covering UIQ-01 edge cases, UIQ-02/D-04 double-submit, and UIQ-04/D-01 console/page-error capture
  - .planning/phases/31-ui-quirks-edge-cases-regression-re-check/artifacts/31-ui-quirks-results.json initial evidence artifact (overall_pass=true)
affects: [31-02-cli-clarity-and-launchers, 31-03-uiq04-triage-and-conditional-fixes]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "window.fetch instrumentation via page.add_init_script to observe completed vs. aborted /api/analyze calls from the client side, without touching the frozen demo.js contract"
    - "Explicit per-case status/passed contract (build_case_record/build_artifact) so overall_pass is derived, never hand-set"

key-files:
  created:
    - scripts/verify_ui_quirks.py
    - tests/runtime/test_ui_quirks_script.py
    - .planning/phases/31-ui-quirks-edge-cases-regression-re-check/artifacts/31-ui-quirks-results.json
  modified: []

key-decisions:
  - "Force-added the produced JSON evidence artifact despite the repo-wide .planning/**/*.json gitignore rule, following the existing 28-golden-prompt-results.json precedent, because the plan's files_modified explicitly declares this file as a Plan 31-03 dependency."
  - "Used a window.fetch wrapper injected via page.add_init_script (not a demo.js change) to get ground-truth completed/aborted signal per /api/analyze call for the double-submit case, since DOM-only inspection couldn't distinguish a superseded-but-completed response from a correctly aborted one."
  - "Drove double-submit through the textarea + Enter/form.requestSubmit() path per D-04, not button double-click, since the button disables after the first submit and would otherwise produce a false pass."

requirements-completed: [UIQ-01, UIQ-02, UIQ-04]

# Metrics
duration: 21min
completed: 2026-07-08
---

# Phase 31 Plan 01: Real-Demo UI Quirks Verifier Summary

**Playwright verifier (`scripts/verify_ui_quirks.py`) drives the real `vnphish demo` browser UI through 4 edge cases plus a fetch-instrumented double-submit case, writing `31-ui-quirks-results.json` evidence with `overall_pass=true` on this run.**

## Performance

- **Duration:** 21 min
- **Started:** 2026-07-08T12:27:34Z
- **Completed:** 2026-07-08T12:48:10Z
- **Tasks:** 2 completed (3 commits: RED test, GREEN helpers, GREEN browser implementation)
- **Files modified:** 3 (2 created source/test files, 1 evidence artifact)

## Accomplishments

- Built a reusable, real-browser (not HTTP-only) UI quirks verifier that reuses the Phase 28/30 subprocess + Playwright patterns exactly (`sys.executable -m src.runtime.cli demo --no-browser --port`, stdout/stderr capture, terminate/kill in `finally`).
- Covered UIQ-01's full edge-case matrix (empty, bounded very-long with an unbroken long token, malformed/off-topic, mixed Vietnamese-English) driven through the real form/button path.
- Covered UIQ-02/D-04 double-submit through the textarea/Enter path with `window.fetch` instrumentation that distinguishes "completed" vs. "aborted" `/api/analyze` calls client-side, confirming the existing `AbortController` guard currently passes all five UIQ-02 sub-criteria.
- Covered UIQ-04/D-01 by attaching `page.on("console", ...)` / `page.on("pageerror", ...)` before any navigation; this clean run captured zero page errors and no `SOURCE_LANG_VI` occurrence, which is useful negative evidence for Plan 31-03's D-01 triage.
- Ran the verifier live against the real demo and local GGUF model; wrote the initial `31-ui-quirks-results.json` evidence artifact with `overall_pass: true` (all 5 cases passed).

## Task Commits

Each task was committed atomically (Task 1 followed the full TDD RED -> GREEN cycle since it defines pure, testable helper contracts):

1. **Task 1 (RED): failing helper tests** - `9b69aa3` (test)
2. **Task 1 (GREEN): helper contracts + parser** - `24fcadb` (feat)
3. **Task 2: real-demo browser implementation + evidence artifact** - `f2b9a68` (feat)

_Note: Task 2 is integration-level (drives Playwright against the real local model); its `<verify>` block in the plan specifies pytest (helper tests, unchanged) plus a live artifact-producing run rather than a separate isolated pytest RED step, so no additional `test(...)` commit was created for Task 2 -- consistent with how `scripts/measure_cold_latency.py` / `tests/runtime/test_latency_measurement.py` split pure-helper tests from live-run verification in Phase 30._

## Files Created/Modified

- `scripts/verify_ui_quirks.py` - Real-demo Playwright verifier: `SCHEMA_VERSION`, `CASE_NAMES`, `build_output_path`, `request_latency_ms`, `build_case_record`/`build_artifact`, `double_submit_passed`, `build_parser` (`--port`/`--output`/`--headed`/`--cases`), subprocess lifecycle (`start_demo_server`/`stop_demo_server`/`wait_for_server`), console/page-error capture, DOM helpers (`typing_count`/`button_disabled`/`terminal_bubble_count`/`error_bubble_count`), case runners (`run_empty_case`/`run_text_case`/`run_double_submit_case`), and `main()`.
- `tests/runtime/test_ui_quirks_script.py` - 10 focused unit tests for the pure helper contract, loaded via the `importlib.util` style from `tests/runtime/test_latency_measurement.py`; no Playwright or model dependency.
- `.planning/phases/31-ui-quirks-edge-cases-regression-re-check/artifacts/31-ui-quirks-results.json` - Initial UIQ-01/UIQ-02/UIQ-04 evidence artifact for Plan 31-03.

## Decisions Made

- **Fetch-instrumentation for double-submit ground truth:** Rather than inferring completed-vs-superseded purely from DOM state (which can't disambiguate a correctly-aborted request from a rare race where both complete), `page.add_init_script` wraps `window.fetch` to record per-call `completed`/`aborted`/`status` before demo.js's own handling runs. This is verifier-side instrumentation only -- `demo.js` itself was not touched, preserving the frozen contract.
- **Enter/form path for double-submit, not button double-click:** Per D-04 and Pitfall 1 in `31-RESEARCH.md`, the button disables after the first submit, so a button-only double-click test would trivially pass without exercising the real re-entrant path. The verifier fills the textarea and presses Enter twice in rapid succession instead.
- **No raw arbitrary text persisted in evidence:** Case records store only counts/status/booleans (per the threat register's `T-31-01-I` mitigation and Task 1 test 4's explicit "omits full arbitrary raw input text" requirement); the fixed fixture strings themselves are not embedded in the JSON artifact.
- **Force-added the evidence JSON despite `.planning/**/*.json` being gitignored repo-wide.** Confirmed via `git ls-files` that `28-golden-prompt-results.json` is the sole existing precedent for this (deliberately force-added in `docs(28-01): lock golden prompt results`, `2807b54`), while Phase 30's raw timestamped latency JSON files were intentionally left untracked (only their markdown summaries are tracked, and Phase 30's plan frontmatter never declared a `.json` path in `files_modified`). Since this plan's frontmatter explicitly declares `31-ui-quirks-results.json` in `files_modified` and the `must_haves.artifacts` table names it as a direct Plan 31-03 dependency, it follows the golden-prompt precedent rather than Phase 30's untracked-raw-JSON pattern.

## Deviations from Plan

None - plan executed exactly as written. No Rule 1-4 auto-fixes were needed; the implementation matched the plan's task actions and verification blocks on the first pass.

## Issues Encountered

- During my own manual verification (not part of the script), I piped the live run through `tee "$TMPDIR/..."` where `$TMPDIR` was unset in that Bash invocation, causing `tee` to fail with "Permission denied" and making `$?` reflect `tee`'s exit code (1) rather than the verifier's actual exit code. Confirmed the verifier's real exit status was 0 by (a) checking the artifact has no top-level `error` key and `overall_pass: true`, and (b) independently re-running the exact plan-specified Python assertion block against the artifact, which passed. No code change was needed; this was purely an artifact of my ad hoc shell command, not a bug in `scripts/verify_ui_quirks.py`.

## Live Verifier Run - Evidence Notes for Plan 31-03

All 5 cases passed (`overall_pass: true`) against the real demo and local GGUF model on this run:

| Case | Status | Notes |
|------|--------|-------|
| `empty` | pass | No `/api/analyze` request fired; native `required` validation blocked submission as expected. |
| `very_long` | pass | Backend returned **HTTP 503** (`RuntimeUnavailableError`) for the bounded very-long fixture, rendered as a well-formed error bubble (zero orphaned typing nodes, button re-enabled). This satisfies the UI-SPEC's "result bubble OR well-formed error bubble" acceptance bar, but the 503 itself is worth Plan 31-03 triage attention as a potential UIQ-04 candidate (why does very-long input trip runtime unavailability rather than a graceful truncation/validation response?). Not fixed in this plan per scope (`src/runtime/demo.py`/`/api/analyze` frozen). |
| `malformed` | pass | HTTP 200, rendered result bubble, zero orphaned typing nodes. |
| `mixed_vi_en` | pass | HTTP 200, rendered result bubble, zero orphaned typing nodes. |
| `double_submit` | pass | `completed_analyze_response_count=1`, `completed_superseded_response_count=0`, `abort_error_bubble_count=0`, `typing_count=0`, `button_disabled=false` -- confirms the existing `AbortController` guard currently works correctly via the Enter/form path. |

Console/page-error capture: one `console` message of type `error` was captured (`"Failed to load resource: the server responded with a status of 503..."`, correlating with the `very_long` case's 503), and **zero `page_errors`** (no uncaught JS exceptions). The `SOURCE_LANG_VI` string did not appear anywhere in this clean Playwright session's console output -- this is useful negative evidence supporting the D-01 hypothesis that it is non-app browser/extension noise, though the final triage call belongs to Plan 31-03 per the phase's decision protocol (compare against the original browser DevTools too before concluding).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `scripts/verify_ui_quirks.py` is ready for Plan 31-02 (CLI clarity/launchers, independent) and Plan 31-03 (conditional UIQ-04 fixes) to consume as both a reusable verifier and a source of initial evidence.
- Plan 31-03 has two concrete triage items surfaced by this run: (1) the `very_long` case's HTTP 503 from the runtime backend, and (2) confirming the `SOURCE_LANG_VI` non-reproduction in clean Playwright against the original browser DevTools before closing D-01.
- No blockers. `tests/runtime/test_ui_quirks_script.py` (10/10 passing) and the live artifact-producing run both succeeded on the first attempt.

---
*Phase: 31-ui-quirks-edge-cases-regression-re-check*
*Completed: 2026-07-08*

## Self-Check: PASSED

- FOUND: scripts/verify_ui_quirks.py
- FOUND: tests/runtime/test_ui_quirks_script.py
- FOUND: .planning/phases/31-ui-quirks-edge-cases-regression-re-check/artifacts/31-ui-quirks-results.json
- FOUND: .planning/phases/31-ui-quirks-edge-cases-regression-re-check/31-01-SUMMARY.md
- FOUND commit: 9b69aa3 (test)
- FOUND commit: 24fcadb (feat)
- FOUND commit: f2b9a68 (feat)
- FOUND commit: 473c01a (docs)
