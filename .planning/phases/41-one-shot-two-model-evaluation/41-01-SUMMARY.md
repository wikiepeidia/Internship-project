---
phase: 41-one-shot-two-model-evaluation
plan: 01
subsystem: model-evaluation
tags: [one-shot-evaluation, synthetic-tests, win32, qlora, phobert, tamper-evidence]

requires:
  - phase: 40-multi-model-training-evidence
    provides: Frozen Qwen QLoRA and PhoBERT identities, comparison authority, and human-review closure
  - phase: 39-independent-quality-re-judge
    provides: Opaque held-out metadata contract and prior-human-exposure disclosure
provides:
  - Claim-before-open one-shot evaluation state machine with permanent spent semantics
  - Machine-global content-SHA claim and one-handle immutable cohort boundary
  - Complete frozen Qwen and PhoBERT inference protocols plus clean-runtime launcher
  - Verify-only evidence resealing, deployment-fit precommit, and closed legacy routes
affects: [41-02-production-bootstrap, held-out-evaluation, report-evidence]

actuals:
  tokens: 109081
  tasks: 3
  commits: 22

tech-stack:
  added: []
  patterns:
    - Exclusive durable authority writes with canonical SHA-linked JSON
    - Content-identity one-shot claim before the sole protected OS handle
    - Preloaded immutable model protocols and text-only shared snapshots

key-files:
  created:
    - src/model_adaptation/phase41_evaluation.py
    - src/model_adaptation/phase41_protocols.py
    - scripts/phase41_one_shot_launcher.ps1
    - tests/model_adaptation/test_phase41_evaluation.py
    - tests/model_adaptation/test_phase41_protocols.py
    - tests/model_adaptation/test_phase41_launcher.py
  modified:
    - src/model_adaptation/cli.py
    - tests/model_adaptation/test_cli.py

key-decisions:
  - "All Phase 41 implementation verification before authorization uses synthetic rows, fake predictors, and isolated temporary claim roots only."
  - "The durable claim is keyed by expected content SHA and must exist before the evaluator requests its sole split handle."
  - "Poor held-out performance is terminal evidence; the deployment-fit choice is precommitted and cannot be selected from test results."

patterns-established:
  - "One-shot chronology: prepared -> explicitly_authorized -> spent -> completed or spent_failed."
  - "Predictor isolation: both preloaded models receive the same immutable text-only cohort while labels remain private to metric computation."
  - "Verification isolation: verify-only accepts an output root only and cannot load models, open a split, or spend a claim."

requirements-completed: [EVAL-08, EVAL-09]

coverage:
  - id: D1
    description: Production one-shot state machine, deterministic result evidence, and permanent spent-on-failure behavior
    requirement: EVAL-08
    verification:
      - kind: integration
        ref: "python -m pytest tests/model_adaptation/test_phase41_evaluation.py tests/model_adaptation/test_cli.py -q"
        status: pass
    human_judgment: false
  - id: D2
    description: Machine-global content claim and exactly one reparse-safe Windows handle/read
    requirement: EVAL-09
    verification:
      - kind: integration
        ref: "python -m pytest tests/model_adaptation/test_phase41_evaluation.py tests/model_adaptation/test_phase41_launcher.py -q"
        status: pass
    human_judgment: false
  - id: D3
    description: Frozen Qwen/PhoBERT protocols, clean execution source, and closed alternate evaluation routes
    requirement: EVAL-09
    verification:
      - kind: integration
        ref: "python -m pytest tests/model_adaptation/test_phase41_protocols.py tests/model_adaptation/test_phase41_evaluation.py tests/model_adaptation/test_phase41_launcher.py tests/model_adaptation/test_release_evaluation.py tests/model_adaptation/test_cli.py -q"
        status: pass
      - kind: integration
        ref: "python -m pytest tests/model_adaptation -q"
        status: pass
    human_judgment: false

duration: 3h 36m active
completed: 2026-08-26
status: complete
---

# Phase 41 Plan 01: One-Shot Evaluator Hardening Summary

**A synthetic-only production evaluator now proves claim-before-open, one immutable two-model cohort, permanent replay resistance, complete frozen inference protocols, and tamper-evident terminal evidence without consulting the reserved split.**

## Performance

- **Implementation window:** 2026-08-25T13:24:48Z to 2026-08-25T16:53:28Z
- **Closure revalidation:** 2026-08-26T04:04Z to 2026-08-26T04:11Z
- **Active duration:** approximately 3h 36m
- **Tasks:** 3/3
- **Declared implementation/test files:** 8
- **Final regression:** 866 passed, 2 existing SWIG deprecation warnings

## Accomplishments

- Promoted the synthetic spike into the production `prepared -> explicitly_authorized -> spent -> completed|spent_failed` evaluator with strict canonical authorities, two prediction bundles, recomputable metrics, fixed-order confusion matrices, and byte-stable verify-only checks.
- Protected the irreversible boundary with a machine-global content-SHA claim created before the sole internally owned handle, path/reparse/final-identity checks, one sequential read, shared immutable cohort construction, and permanent post-claim failure evidence.
- Froze complete Qwen QLoRA and PhoBERT protocols, model/tree/runtime identities, clean execution-source inventory, and launcher identity while closing legacy evaluator, alternate loader, retry, split override, registry override, and progress-callback routes.

## Task Commits

Each planned task followed RED/GREEN TDD and was then hardened by security-focused fixes:

1. **Task 1: Synthetic end-to-end production state machine** — `18a56df` (RED), `1940e24` (GREEN)
2. **Task 2: Sole Windows handle and machine-global claim** — `c81fd44` (RED), `0b9b2ae` (GREEN)
3. **Task 3: Frozen model protocols and closed alternate routes** — `4cb43ae` (RED), `cdbb373` (GREEN)
4. **Boundary hardening** — `535ba9c` through `e1454e1` (16 focused security/correctness commits)

## Files Created/Modified

- `src/model_adaptation/phase41_evaluation.py` — strict authorities, claim/open chronology, shared snapshot, metrics, terminal records, evidence verification, and canonical preparation checks.
- `src/model_adaptation/phase41_protocols.py` — immutable Qwen/PhoBERT protocols, model-tree leases, identity checks, preloaded predictors, and synthetic smoke requirements.
- `src/model_adaptation/cli.py` — six constrained Phase 41 verbs with no public split/model/registry/retry override on the run path.
- `scripts/phase41_one_shot_launcher.ps1` — self-bound clean-runtime launcher and protected registry/source preflight.
- `tests/model_adaptation/test_phase41_evaluation.py` — state, replay, tamper, terminal, metric, and evidence regressions using synthetic fixtures.
- `tests/model_adaptation/test_phase41_protocols.py` — protocol drift, immutable-loader, ancestry, runtime, closure, and route-isolation regressions.
- `tests/model_adaptation/test_phase41_launcher.py` — clean-runtime and launcher-source binding regressions.
- `tests/model_adaptation/test_cli.py` — parser/help/signature and CLI boundary regressions.

## Decisions Made

- Kept all preauthorization engineering tests synthetic and temporary; neither test execution nor closure inspected the reserved partition or loaded a production model artifact.
- Made content SHA, rather than checkout path or output directory, the replay identity so copied bytes cannot create a new opportunity.
- Required both predictors to be loaded, identity-checked, leased, and smoke-tested before claim creation; lazy loading after the irreversible claim is forbidden.
- Preserved a separate, precommitted deployment-fit disposition that cannot turn terminal test outcomes into a model-selection claim.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Security] Hardened runtime, authority, and filesystem identities after the initial GREEN implementations**

- **Found during:** post-task adversarial review across Tasks 1-3
- **Issue:** the initial feature commits satisfied the planned behaviors but further review exposed forgery and time-of-check/time-of-use surfaces around production capabilities, model roots, loader identity, path ancestry, live leases, terminal seals, and authority lineage.
- **Fix:** added 16 focused hardening commits (`535ba9c` through `e1454e1`) covering those production boundaries and their regressions.
- **Files modified:** the declared Phase 41 production and test files only.
- **Verification:** 58/58 tracer tests, 36/36 handle tests, 119/119 combined protocol/legacy-route tests, and 866/866 full model-adaptation tests.

**2. [Rule 3 - Blocking] Closed the plan after Phase 40 authority refreshes**

- **Found during:** closure revalidation
- **Issue:** Plan 01 code existed, but its summary had not been sealed after later Phase 40 comparison/review authority migrations.
- **Fix:** re-ran every plan-level suite and the complete model-adaptation regression against the current authorities, then created this canonical summary.
- **Files modified:** `.planning/phases/41-one-shot-two-model-evaluation/41-01-SUMMARY.md`.
- **Verification:** all 1,079 executed test instances passed across the three focused commands and full-suite command (overlapping suites intentionally counted as executions).

---

**Total deviations:** 2 auto-fixed (1 missing critical security hardening, 1 blocking closure drift).
**Impact on plan:** The deviations strengthened the declared one-shot boundary and restored auditable closure; they did not access data, authorize an evaluation, spend a claim, or change the plan's architecture.

## Issues Encountered

- The canonical production bootstrap intentionally remains fail-closed until Plan 41-02 freezes live production identities and reaches the explicit human authorization gate. This is the next plan's work, not a Plan 01 stub.
- The full suite emitted two pre-existing SWIG deprecation warnings; no test failed.

## User Setup Required

None for Plan 01. Provisioning and live preauthorization preparation belong to Plan 41-02 and must still stop before the exact human authorization signal.

## Next Phase Readiness

- Ready for Plan 41-02 to derive the live authorities from the finalized Phase 39/40 evidence and prepare only safe preauthorization artifacts.
- The reserved split remains unopened and no production one-shot authorization or machine-global claim has been created.
- Plan 41-02 must display the frozen identities/disclosures and stop at the blocking authorization gate; it must not infer the user's deployment-fit choice.

## Self-Check: PASSED

- All eight declared implementation/test files exist.
- All six RED/GREEN task commits and the final authority-hardening commit exist in git history.
- No `TODO`, `FIXME`, `coming soon`, or placeholder pattern remains in the declared files.
- All focused and full regression commands passed with synthetic fixtures only.

---
*Phase: 41-one-shot-two-model-evaluation*
*Completed: 2026-08-26*
