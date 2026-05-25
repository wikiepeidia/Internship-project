---
phase: 05-recall-priority-evaluation-and-release-gates
plan: 01
subsystem: model_adaptation
tags: [pydantic, release-eval, held-out-audit, testing]
requires:
  - phase: 04-threat-detection-and-explainable-decisioning
    provides: Phase 4 runtime contracts and public analysis surface reused by Phase 5.
provides:
  - Typed Phase 5 release-evaluation contracts under src/model_adaptation/schemas.py
  - Fail-closed held-out release-eval support audit under src/model_adaptation/release_readiness.py
  - Regression coverage for locked verdicts, reviewable rows, and risky-label support blocking
affects: [05-02, 05-03, 05-04, release-evaluation]
tech-stack:
  added: []
  patterns: [fail-closed audit, locked label order, typed release artifacts]
key-files:
  created:
    - src/model_adaptation/release_readiness.py
    - tests/model_adaptation/test_release_readiness.py
  modified:
    - src/model_adaptation/schemas.py
    - tests/model_adaptation/test_schemas.py
key-decisions:
  - Kept Phase 5 release contracts inside src/model_adaptation so the offline release-engineering layer does not widen runtime contracts.
  - Normalized held-out support counts to the full locked label order and auto-blocked missing risky-label support.
patterns-established:
  - Release-eval audits record explicit blocker reasons instead of inferring readiness from split naming.
  - Reviewable evaluation rows must preserve normalized text or reviewable source text for later human-review packing.
requirements-completed:
  - EVAL-01
  - EVAL-02
duration: 25 min
completed: 2026-05-25
---

# Phase 05 Plan 01: Shared release-evaluation contracts and fail-closed held-out audit summary

**Typed Phase 5 release contracts with a fail-closed risky-label support audit over the held-out slice**

## Performance

- **Duration:** 25 min
- **Started:** 2026-05-25T02:03:00Z
- **Completed:** 2026-05-25T02:28:22Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Added typed Phase 5 models for verdicts, held-out audits, evaluation rows, per-label metrics, rubric summaries, and release artifacts in src/model_adaptation/schemas.py.
- Added src/model_adaptation/release_readiness.py to resolve the held-out release-eval path and block when any risky label has zero support.
- Added focused regression coverage for the locked verdict surface, reviewable evaluation rows, full label-order counts, and fail-closed risky-label gaps.
- Updated the stale settings-default test to assert code defaults instead of local env-file overrides from this workspace.

## Verification

- `python -m pytest tests/model_adaptation/test_schemas.py tests/model_adaptation/test_release_readiness.py -q`

## Files Created/Modified

- `src/model_adaptation/schemas.py` - Phase 5 typed contracts for audits, evaluation rows, metrics, rubric summaries, and release artifacts.
- `src/model_adaptation/release_readiness.py` - Held-out release-eval path resolution and risky-label support audit.
- `tests/model_adaptation/test_schemas.py` - Contract coverage for locked verdicts, risky-label metadata, and required artifact fields.
- `tests/model_adaptation/test_release_readiness.py` - Coverage for explicit label-order counts and fail-closed risky-label blocking.

## Decisions Made

- Kept Phase 5 release contracts in `src/model_adaptation` to preserve the Phase 4 runtime boundary.
- Required `ReleaseEvaluationRow` to carry reviewable source text or normalized text so later review-pack generation stays local and typed.
- Treated missing risky-label support as a release blocker even when the split file exists.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Existing settings-default test was stale against current runtime defaults**

- **Found during:** Task 1 verification
- **Issue:** `tests/model_adaptation/test_schemas.py` still expected the old heuristic runtime defaults and local repo paths, while `src/config/settings.py` now defaults to `gguf` and this workspace carries off-repo model-path overrides.
- **Fix:** Updated the test to assert code defaults by isolating it from env-file and shell overrides.
- **Files modified:** `tests/model_adaptation/test_schemas.py`
- **Verification:** `python -m pytest tests/model_adaptation/test_schemas.py tests/model_adaptation/test_release_readiness.py -q`

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** The fix was required to keep the plan verification command honest. No Phase 5 scope expansion.

## Issues Encountered

- Local `.env/.env` overrides for model artifact paths would have made the settings-default assertion machine-specific. The test was hardened to validate code defaults instead.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 05-01 now provides the locked schema and held-out readiness seam needed by 05-02.
- The next slice is the contract-bound evaluator and metric engine in `src/model_adaptation/release_evaluation.py`.

---
*Phase: 05-recall-priority-evaluation-and-release-gates*
*Completed: 2026-05-25*
