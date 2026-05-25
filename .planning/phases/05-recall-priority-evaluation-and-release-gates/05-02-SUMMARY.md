---
phase: 05-recall-priority-evaluation-and-release-gates
plan: 02
subsystem: model_adaptation
tags: [evaluation, sklearn, runtime-service, snapshot]
requires:
  - phase: 05-recall-priority-evaluation-and-release-gates
    provides: Locked release-evaluation contracts and held-out readiness auditing from Plan 05-01.
provides:
  - Contract-bound held-out evaluator under src/model_adaptation/release_evaluation.py
  - Fixed-label overall and per-label metrics over the Phase 4 AnalysisResult surface
  - Saved phase-local evaluation snapshot bound to a run identifier for later review and verdict steps
affects: [05-03, 05-04, release-evaluation]
tech-stack:
  added: []
  patterns: [runtime-bound evaluation, fixed label order metrics, saved snapshot handoff]
key-files:
  created:
    - src/model_adaptation/release_evaluation.py
    - tests/model_adaptation/test_release_evaluation.py
  modified:
    - src/model_adaptation/schemas.py
key-decisions:
  - Kept evaluation ownership in src/model_adaptation and treated RuntimeService.analyze_text as the only scoring seam.
  - Persisted one phase-local evaluation snapshot with a run identifier so later review and final verdict steps can bind to the same evaluated batch.
patterns-established:
  - Release metrics always enumerate the locked label order, including zero-support labels.
  - Benign results without explicit labels are normalized to the benign label for honest fixed-label reporting.
requirements-completed:
  - EVAL-01
  - EVAL-02
duration: 3 min
completed: 2026-05-25
---

# Phase 05 Plan 02: Contract-bound evaluator and explicit-label metrics summary

**Offline release evaluator over the Phase 4 runtime surface with fixed-label metrics and a saved snapshot handoff**

## Performance

- **Duration:** 3 min
- **Started:** 2026-05-25T02:28:22Z
- **Completed:** 2026-05-25T02:31:41Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Added `src/model_adaptation/release_evaluation.py` to load held-out records, score them through `RuntimeService.analyze_text()` or an injected equivalent seam, and capture typed evaluation rows.
- Added fixed-label macro and weighted F1 reporting plus explicit per-label precision, recall, F1, and support for all locked labels.
- Persisted a phase-local evaluation snapshot with a run identifier for the later explanation-review and final verdict plans.
- Added evaluator tests covering runtime-bound row capture, unknown-channel handling, zero-support visibility, macro versus weighted F1, and multilabel metric preservation.

## Verification

- `python -m pytest tests/model_adaptation/test_release_evaluation.py -q`

## Files Created/Modified

- `src/model_adaptation/release_evaluation.py` - Held-out evaluator, metric engine, and snapshot writer.
- `src/model_adaptation/schemas.py` - Added the typed release-evaluation snapshot model.
- `tests/model_adaptation/test_release_evaluation.py` - Coverage for contract-bound evaluation, snapshot persistence, and fixed-label metrics.

## Decisions Made

- Used the public Phase 4 runtime contract as the only evaluation boundary instead of scoring backend-private payloads.
- Saved the evaluation snapshot inside the Phase 5 planning directory so later manual review and final verdict steps can reuse one batch.
- Preserved multilabel predictions during metric computation rather than collapsing them to a single winner.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 05-03 can now consume one saved evaluation snapshot and build a deterministic risky-only review pack.
- The next slice is explanation scoring plus the pre-verdict operator command.

---
*Phase: 05-recall-priority-evaluation-and-release-gates*
*Completed: 2026-05-25*
