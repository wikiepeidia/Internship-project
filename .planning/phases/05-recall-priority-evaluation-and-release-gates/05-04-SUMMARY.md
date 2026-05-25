---
phase: 05-recall-priority-evaluation-and-release-gates
plan: 04
subsystem: model_adaptation
tags: [release-gates, cli, doctor, manifests]
requires:
  - phase: 05-recall-priority-evaluation-and-release-gates
    provides: Saved evaluation snapshot and explicit-label metrics from Plan 05-02.
  - phase: 05-recall-priority-evaluation-and-release-gates
    provides: Completed explanation review pack from Plan 05-03.
provides:
  - Recall-first verdict synthesis under src/model_adaptation/release_gates.py
  - Final release-eval CLI orchestration and paired markdown plus JSON release artifacts
  - Optional runtime doctor summary that reads the latest saved release artifact without recomputing evaluation
affects: [phase-6, release-manifest, runtime-doctor]
tech-stack:
  added: []
  patterns: [recall-first release verdict, canonical paired artifacts, doctor reads saved artifact only]
key-files:
  created:
    - src/model_adaptation/release_gates.py
    - tests/model_adaptation/test_release_gates.py
    - .planning/phases/05-recall-priority-evaluation-and-release-gates/05-release-eval-phase5-review-sample-val.md
    - data/manifests/phase5-release-eval-phase5-review-sample-val.json
  modified:
    - src/model_adaptation/cli.py
    - src/runtime/doctor.py
    - src/model_adaptation/schemas.py
    - src/model_adaptation/explanation_review.py
    - tests/model_adaptation/test_cli.py
    - tests/runtime/test_doctor.py
    - .planning/phases/05-recall-priority-evaluation-and-release-gates/05-explanation-review-pack.json
key-decisions:
  - Kept final release gating inside src/model_adaptation instead of moving evaluation ownership into the live runtime path.
  - Required the saved review pack to be explicitly completed and bound to the same run_id as the saved evaluation snapshot.
  - Let runtime doctor surface the latest saved release artifact summary only, never a recomputed release gate.
patterns-established:
  - One canonical ReleaseEvaluationArtifact now feeds both the phase-local markdown report and the machine-readable manifest.
  - Phase completion can be true even when the current release candidate is BLOCK, because the gate mechanism itself is the delivered Phase 5 capability.
requirements-completed:
  - EVAL-01
  - EVAL-02
  - EVAL-03
duration: 5 min
completed: 2026-05-25
---

# Phase 05 Plan 04: Final recall-first release gate summary

**Final Phase 5 release-gate engine shipped, paired artifacts emitted, and the saved sample run truthfully closed as `BLOCK` because held-out bank and zalo support are still absent**

## Performance

- **Duration:** 5 min
- **Started:** 2026-05-25T02:42:22Z
- **Completed:** 2026-05-25T02:47:42Z
- **Tasks:** 2
- **Files modified:** 10

## Accomplishments

- Added `src/model_adaptation/release_gates.py` to synthesize a canonical `PASS | BLOCK | FLAG` release verdict from the saved readiness audit, per-label metrics, and completed explanation review pack.
- Extended `src/model_adaptation/cli.py` with the final `release-eval` command, which rejects incomplete or mismatched review packs and prints the verdict plus paired artifact paths.
- Updated `src/runtime/doctor.py` so operators can read the latest saved Phase 5 release summary without recomputing evaluation inside the runtime path.
- Recorded the approved review pack as completed, then ran the real Phase 5 `release-eval` command to emit `.planning/phases/05-recall-priority-evaluation-and-release-gates/05-release-eval-phase5-review-sample-val.md` and `data/manifests/phase5-release-eval-phase5-review-sample-val.json`.
- Closed the saved sample run as `BLOCK` with explicit reasons: the evaluated `data/splits/val.jsonl` batch has zero held-out support for `bank_impersonation` and `zalo_social_engineering`.

## Verification

- `python -m pytest tests/model_adaptation/test_release_gates.py tests/model_adaptation/test_cli.py tests/runtime/test_doctor.py -q`
- `python -m pytest tests/model_adaptation/test_schemas.py tests/model_adaptation/test_explanation_review.py tests/model_adaptation/test_release_gates.py tests/model_adaptation/test_cli.py tests/runtime/test_doctor.py -q`
- `python -m src.model_adaptation.cli release-eval --snapshot-path .planning/phases/05-recall-priority-evaluation-and-release-gates/05-evaluation-snapshot.json --review-pack-path .planning/phases/05-recall-priority-evaluation-and-release-gates/05-explanation-review-pack.json`

## Files Created/Modified

- `src/model_adaptation/release_gates.py` - Final recall-first verdict synthesis and paired artifact writers.
- `src/model_adaptation/cli.py` - Added the final `release-eval` operator command.
- `src/runtime/doctor.py` - Added latest-saved release summary reporting.
- `src/model_adaptation/schemas.py` - Added explicit review-pack completion state for the final gate.
- `src/model_adaptation/explanation_review.py` - Initialized newly created review packs as incomplete until human completion.
- `tests/model_adaptation/test_release_gates.py` - Coverage for blocker logic, advisory flags, artifact content, and mismatch or incomplete rejection.
- `tests/model_adaptation/test_cli.py` - Coverage for the final `release-eval` command and its explicit failure paths.
- `tests/runtime/test_doctor.py` - Coverage for reading the latest saved release artifact summary.
- `.planning/phases/05-recall-priority-evaluation-and-release-gates/05-explanation-review-pack.json` - Marked the approved pack as completed.
- `.planning/phases/05-recall-priority-evaluation-and-release-gates/05-release-eval-phase5-review-sample-val.md` - Saved human-readable Phase 5 release report.
- `data/manifests/phase5-release-eval-phase5-review-sample-val.json` - Saved machine-readable Phase 5 release artifact.

## Decisions Made

- Final release evaluation remains an offline model-adaptation concern, not a live runtime-service concern.
- The completed review pack is the human checkpoint record for the same run that receives the final verdict.
- A truthful `BLOCK` artifact is the correct Phase 5 outcome when held-out risky-label coverage is missing, even if the gating machinery itself is fully complete.

## Deviations from Plan

None.

## Issues Encountered

- The only saved Phase 5 evaluation batch still lacks `bank_impersonation` and `zalo_social_engineering` support, so the current release candidate cannot pass the recall-first gate.

## User Setup Required

None - the release gate runs on saved local artifacts only.

## Next Phase Readiness

- Phase 5 implementation is complete.
- The current saved release candidate remains blocked until a held-out batch exists with risky-label coverage for bank and zalo.
- Phase 6 remains intentionally deferred and out of scope for this execution run.

---
*Phase: 05-recall-priority-evaluation-and-release-gates*
*Completed: 2026-05-25*
