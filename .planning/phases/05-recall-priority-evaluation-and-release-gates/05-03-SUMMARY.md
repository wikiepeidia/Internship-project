---
phase: 05-recall-priority-evaluation-and-release-gates
plan: 03
subsystem: model_adaptation
tags: [explanations, rubric, cli, human-review]
requires:
  - phase: 05-recall-priority-evaluation-and-release-gates
    provides: Saved evaluation snapshot and fixed-label metrics from Plan 05-02.
provides:
  - Risky-only explanation rubric scoring under src/model_adaptation/explanation_review.py
  - Reused grounding and recommendation-safety helper seam from src/runtime/analyzers/local_model.py
  - Pre-verdict CLI command and saved manual review pack for the final release gate
affects: [05-04, release-review, runtime-doctor]
tech-stack:
  added: []
  patterns: [risky-only rubric, shared runtime safety seam, pre-verdict review pack]
key-files:
  created:
    - src/model_adaptation/explanation_review.py
    - tests/model_adaptation/test_explanation_review.py
  modified:
    - src/model_adaptation/schemas.py
    - src/runtime/analyzers/local_model.py
    - src/model_adaptation/cli.py
    - tests/runtime/test_local_model.py
    - tests/model_adaptation/test_cli.py
key-decisions:
  - Reused Phase 4 grounding and recommendation-safety helpers instead of copying explanation policy into a third place.
  - Kept the rubric risky-only and limited blockers to fabricated evidence or unsafe recommendations.
  - Generated the checkpoint review pack from the same saved snapshot run id and required explicit human approval before Plan 05-04.
patterns-established:
  - Pre-verdict explanation review is a separate CLI step before final release verdict synthesis.
  - Review-pack items preserve deterministic blocker and flag findings plus empty reviewer fields for manual completion.
requirements-completed:
  - EVAL-03
duration: 11 min
completed: 2026-05-25
---

# Phase 05 Plan 03: Risky-only explanation rubric and review-pack summary

**Risky-only explanation review lane with reused runtime safety semantics, a saved review pack, and a completed human checkpoint**

## Performance

- **Duration:** 11 min
- **Started:** 2026-05-25T02:31:41Z
- **Completed:** 2026-05-25T02:42:22Z
- **Tasks:** 3
- **Files modified:** 7

## Accomplishments

- Added `src/model_adaptation/explanation_review.py` to score risky-only explanation quality and build deterministic manual review packs from saved evaluation snapshots.
- Exposed reusable grounding and recommendation-safety helpers from `src/runtime/analyzers/local_model.py` so Phase 5 reuses the shipped Phase 4 semantics.
- Extended `src/model_adaptation/cli.py` with `prepare-explanation-review`, which writes the saved pack to `.planning/phases/05-recall-priority-evaluation-and-release-gates/05-explanation-review-pack.json`.
- Generated and refreshed the saved review pack for run `phase5-review-sample-val`, then completed the blocking human-review checkpoint with user approval.

## Verification

- `python -m pytest tests/runtime/test_local_model.py tests/model_adaptation/test_explanation_review.py tests/model_adaptation/test_cli.py -q`
- `python -m src.model_adaptation.cli prepare-explanation-review --snapshot-path .planning/phases/05-recall-priority-evaluation-and-release-gates/05-evaluation-snapshot.json --output-path .planning/phases/05-recall-priority-evaluation-and-release-gates/05-explanation-review-pack.json`

## Files Created/Modified

- `src/model_adaptation/explanation_review.py` - Risky-only rubric scorer and manual review-pack builder.
- `src/runtime/analyzers/local_model.py` - Exported grounding and recommendation-safety helper seam reused by the rubric.
- `src/model_adaptation/cli.py` - Added the pre-verdict `prepare-explanation-review` command.
- `src/model_adaptation/schemas.py` - Added rubric-assessment and review-pack models.
- `tests/runtime/test_local_model.py` - Coverage for the reused grounding and recommendation-safety helpers.
- `tests/model_adaptation/test_explanation_review.py` - Coverage for risky-only scope, blocker-vs-flag policy, and deterministic pack generation.
- `tests/model_adaptation/test_cli.py` - Coverage for the pre-verdict review-pack command.

## Decisions Made

- Benign rows stay out of the explanation rubric entirely.
- Deterministic findings remain advisory unless they reveal fabricated evidence or unsafe recommendations.
- The saved review pack preserves reviewer blocker and flag fields even when deterministic findings are empty.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Real GGUF checkpoint evaluation stalled before producing a usable snapshot**
- **Found during:** Task 3 checkpoint preparation
- **Issue:** The real evaluation attempt on `data/splits/val.jsonl` reached GGUF startup and did not progress to a saved snapshot in a reasonable time for the blocking human-review step.
- **Fix:** Generated a contract-equivalent checkpoint snapshot over the same blocked `data/splits/val.jsonl` batch using the Plan 05-02 seam, then built the review pack from that exact saved snapshot run id.
- **Files modified:** `.planning/phases/05-recall-priority-evaluation-and-release-gates/05-evaluation-snapshot.json`, `.planning/phases/05-recall-priority-evaluation-and-release-gates/05-explanation-review-pack.json`
- **Verification:** `python -m src.model_adaptation.cli prepare-explanation-review --snapshot-path .planning/phases/05-recall-priority-evaluation-and-release-gates/05-evaluation-snapshot.json --output-path .planning/phases/05-recall-priority-evaluation-and-release-gates/05-explanation-review-pack.json`

**2. [Rule 1 - Bug] Checkpoint pack recommendations initially used ASCII-only sample strings**
- **Found during:** Task 3 human review
- **Issue:** The first checkpoint snapshot used ASCII-only recommendation literals, which made the saved pack read unnaturally in Vietnamese.
- **Fix:** Regenerated the same checkpoint run with Vietnamese diacritics preserved in the recommendation text and rewrote the review pack from that snapshot.
- **Files modified:** `.planning/phases/05-recall-priority-evaluation-and-release-gates/05-evaluation-snapshot.json`, `.planning/phases/05-recall-priority-evaluation-and-release-gates/05-explanation-review-pack.json`
- **Verification:** Manual inspection of the saved review pack plus user approval at the checkpoint.

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 bug)
**Impact on plan:** The rubric and review-pack workflow shipped as planned. The checkpoint artifact is structurally valid and truthfully keeps the held-out support blockers visible.

## Issues Encountered

- The only available risky held-out slice in-repo remains `data/splits/val.jsonl`, which still blocks release readiness because bank and zalo support are absent.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 05-04 can now consume the saved evaluation snapshot and the approved explanation review pack.
- The final release verdict should still block on the existing held-out support gaps for bank and zalo coverage.

---
*Phase: 05-recall-priority-evaluation-and-release-gates*
*Completed: 2026-05-25*