---
phase: 32-fallback-recording-full-dry-rehearsal
plan: "01"
subsystem: demo-readiness
tags: [fallback, rehearsal, playwright, launcher, golden-prompts, human-uat]

# Dependency graph
requires:
  - phase: 31-ui-quirks-edge-cases-regression-re-check plan 03
    provides: "stable final demo UI, final Windows launchers, and fresh golden-prompt regression evidence"
provides:
  - "Operator fallback checklist for recording, screenshot sequence, and live-to-fallback pivot rehearsal using the exact two locked golden prompts"
  - "Fresh-process Playwright dry-run harness that starts the final scripts/START_DEMO_UI.bat launcher"
  - "Tracked dry-run JSON proving both locked golden prompts return the expected verdicts through the browser UI"
  - "Explicit human-verification boundary for video copies, screenshot copies, pivot rehearsal, and strict literal cold-boot coverage"
affects: [defense-fallback, demo-readiness, verify-work]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Fresh-process launcher verification: stop existing target-port listeners, invoke the final .bat launcher through cmd.exe, poll the served UI, drive Playwright against that UI, then terminate the launcher process tree."
    - "Human-boundary coverage: artifacts can guide manual fallback evidence, but summary coverage marks manual recording/screenshot/pivot items as human_judgment true."

key-files:
  created:
    - scripts/verify_phase32_fresh_process.py
    - .planning/phases/32-fallback-recording-full-dry-rehearsal/artifacts/32-fallback-operator-checklist.md
    - .planning/phases/32-fallback-recording-full-dry-rehearsal/artifacts/32-fresh-process-dry-run.json
    - .planning/phases/32-fallback-recording-full-dry-rehearsal/32-01-SUMMARY.md
  modified: []

key-decisions:
  - "Use the final scripts/START_DEMO_UI.bat launcher for the automated proof instead of the no-browser verifier path, so the evidence exercises the operator-facing launch route."
  - "Keep FB-01, FB-02, and FB-03 human-routed because the agent cannot truthfully confirm saved video copies, saved screenshot copies, or a live-to-fallback pivot rehearsal without user evidence."
  - "Treat the automated run as a fresh-process FB-04 substitute only; it does not claim literal OS power-cycle/cold-boot coverage for drivers, OneDrive sync, Windows Defender first-run effects, or physical presentation-laptop conditions."
  - "Print the dry-run artifact path as repo-relative text to avoid Windows console encoding failures when the absolute path contains Vietnamese characters."

requirements-completed: [FB-01, FB-02, FB-03, FB-04]

coverage:
  - id: D1
    description: "Fallback video checklist exists with the exact two locked golden prompts and evidence fields for saving the recording in two separate local locations."
    requirement: "FB-01"
    verification:
      - kind: manual_procedural
        ref: ".planning/phases/32-fallback-recording-full-dry-rehearsal/artifacts/32-fallback-operator-checklist.md#fb-01"
        status: unknown
    human_judgment: true
    rationale: "Automation can provide the script, but only the operator can confirm the actual recording exists and is saved in two separate local places."
  - id: D2
    description: "Screenshot fallback checklist exists for the same golden-prompt run, including startup, scam result, benign result, and saved-file evidence."
    requirement: "FB-02"
    verification:
      - kind: manual_procedural
        ref: ".planning/phases/32-fallback-recording-full-dry-rehearsal/artifacts/32-fallback-operator-checklist.md#fb-02"
        status: unknown
    human_judgment: true
    rationale: "Automation cannot confirm the operator's final saved screenshot sequence or storage location."
  - id: D3
    description: "Live-to-fallback pivot rehearsal checklist exists with an operator script and result field."
    requirement: "FB-03"
    verification:
      - kind: manual_procedural
        ref: ".planning/phases/32-fallback-recording-full-dry-rehearsal/artifacts/32-fallback-operator-checklist.md#fb-03"
        status: unknown
    human_judgment: true
    rationale: "The pivot is a human presentation maneuver, not a property of the local app process."
  - id: D4
    description: "Fresh-process substitute starts scripts/START_DEMO_UI.bat, loads the real browser UI, submits both locked golden prompts, and records correct scam/benign verdicts."
    requirement: "FB-04"
    verification:
      - kind: automated_ui
        ref: "python scripts/verify_phase32_fresh_process.py --port 8765 --output .planning/phases/32-fallback-recording-full-dry-rehearsal/artifacts/32-fresh-process-dry-run.json"
        status: pass
      - kind: other
        ref: "32-fresh-process-dry-run.json overall_pass=true, launcher.path=scripts\\START_DEMO_UI.bat, scam=high-risk/bank_impersonation, benign=benign"
        status: pass
    human_judgment: false
  - id: D5
    description: "Strict literal cold-boot interpretation remains human-routed: either confirm the documented fresh-process substitution is accepted for defense readiness or run a post-reboot dry rehearsal manually."
    requirement: "FB-04"
    verification: []
    human_judgment: true
    rationale: "The user explicitly skipped literal shutdown/power-cycle coverage on 2026-07-09; the agent must not infer a physical cold boot from a fresh process."

# Metrics
duration: 23min
completed: 2026-07-09
status: complete
---

# Phase 32 Plan 01: Fallback Checklist and Fresh-Process Dry-Run Summary

**Fallback evidence is staged honestly: the final Windows demo launcher passed a fresh-process browser dry-run for both locked golden prompts, while recording, screenshot, pivot, and strict cold-boot acceptance remain explicit human checks.**

## Performance

- **Duration:** ~23 min
- **Started:** 2026-07-09T13:33:00Z
- **Completed:** 2026-07-09T13:56:00Z
- **Tasks:** 2 completed
- **Files modified:** 4 tracked outputs (1 script, 1 checklist, 1 forced-added JSON artifact, 1 summary)

## Accomplishments

- Added `scripts/verify_phase32_fresh_process.py`, a reusable Phase 32 verifier that loads the locked golden prompts from `scripts/verify_golden_prompts.py`, cross-checks the Phase 28 artifact when present, starts the real `scripts/START_DEMO_UI.bat` launcher, drives the served browser UI with Playwright, and writes structured evidence.
- Added `32-fallback-operator-checklist.md` with exact manual steps for FB-01 video recording, FB-02 screenshots, and FB-03 live-to-fallback pivot rehearsal, including the exact two locked golden prompt texts.
- Ran the fresh-process dry-run successfully through the final launcher path. `32-fresh-process-dry-run.json` records `overall_pass: true`, scam verdict `high-risk` with `bank_impersonation`, benign verdict `benign` with only `benign`, and an explicit scope notice that this is not literal cold-boot coverage.
- Preserved the manual boundary. The checklist and summary do not claim the operator has already saved videos/screenshots, rehearsed the pivot, or performed a physical OS power cycle.

## Task Commits

Each task/evidence step was committed atomically:

1. **Task 1: Add fallback checklist and fresh-process dry-run harness** - `d44352e` (feat)
2. **Task 1 fix: Print dry-run artifact path safely on Windows Unicode paths** - `3bfea16` (fix)
3. **Task 2: Record fresh-process dry-run evidence** - `fd5221d` (test)

## Files Created/Modified

- `scripts/verify_phase32_fresh_process.py` - Fresh-process launcher-backed Playwright verifier for the final demo UI path.
- `.planning/phases/32-fallback-recording-full-dry-rehearsal/artifacts/32-fallback-operator-checklist.md` - Human operator checklist for fallback recording, screenshot sequence, and pivot rehearsal.
- `.planning/phases/32-fallback-recording-full-dry-rehearsal/artifacts/32-fresh-process-dry-run.json` - Tracked dry-run evidence proving the final launcher path served the UI and returned the expected golden-prompt verdicts.
- `.planning/phases/32-fallback-recording-full-dry-rehearsal/32-01-SUMMARY.md` - This summary and coverage routing record.

## Decisions Made

- The automated verifier launches `scripts/START_DEMO_UI.bat` through `cmd.exe /c` instead of calling `vnphish demo --no-browser` directly, because Phase 32 needs confidence in the actual operator-facing launcher.
- The script stops pre-existing listeners on the target port before launching the fresh process, matching the defense-day expectation that the user starts from a clean local demo session.
- The fresh-process run is evidence for a launcher-backed rehearsal substitute, not a literal cold boot. The dry-run JSON says so directly in `scope_notice`.
- The manual fallback assets remain human verification items. They are checklist-guided, not auto-passed.

## Deviations from Plan

One small fix was needed after the first successful dry-run wrote a green JSON artifact: printing the absolute artifact path failed under the Windows console code page because the repo path contains Vietnamese characters. The script now prints a repo-relative path, which preserved the same evidence flow and passed on rerun.

**Total deviations:** 1 auto-fixed execution-environment issue.
**Impact on plan:** No scope change. The dry-run evidence is stronger after the rerun because the command exited 0 and the artifact remained green.

## Issues Encountered

- The final `.bat` launcher may open the user's normal browser as designed. The verifier still drives its own Playwright browser against the same local server, then shuts down the launcher process tree.
- Literal shutdown/power-cycle coverage was intentionally not performed by the agent. This remains a human decision/check in `32-VERIFICATION.md` and `32-UAT.md`.

## User Setup Required

Human fallback evidence is still required before Phase 32 can be marked fully complete:

- Record the two-prompt fallback video and save it in two local locations.
- Save the screenshot sequence as the secondary fallback.
- Rehearse the live-to-fallback pivot at least once.
- Confirm whether the documented fresh-process substitute is acceptable for FB-04, or perform a literal post-reboot dry rehearsal with `scripts/START_DEMO_UI.bat`.

## Next Phase Readiness

There is no next v5.1 phase. Phase 32 is implementation-complete but verification is intentionally `human_needed`; `32-UAT.md` holds the remaining operator checks for `$gsd-verify-work 32`.

---
*Phase: 32-fallback-recording-full-dry-rehearsal*
*Completed: 2026-07-09*

## Self-Check: PASSED

- FOUND: `scripts/verify_phase32_fresh_process.py`
- FOUND: `.planning/phases/32-fallback-recording-full-dry-rehearsal/artifacts/32-fallback-operator-checklist.md`
- FOUND: `.planning/phases/32-fallback-recording-full-dry-rehearsal/artifacts/32-fresh-process-dry-run.json`
- FOUND: `.planning/phases/32-fallback-recording-full-dry-rehearsal/32-01-SUMMARY.md`
- FOUND commit: `d44352e` (feat)
- FOUND commit: `3bfea16` (fix)
- FOUND commit: `fd5221d` (test)
