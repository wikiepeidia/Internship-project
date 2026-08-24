---
phase: 40-multi-model-training-evidence
plan: 01
subsystem: model-adaptation-safety-contracts
tags: [canonical-snapshot, qlora-proof, response-only-loss, deterministic-validation, checkpoint-selection]

requires:
  - phase: 39-independent-quality-re-judge
    provides: Canonical train/validation identities, opaque held-out metadata, and the downstream data authority
provides:
  - Fail-closed canonical train/validation preflight with immutable byte-faithful snapshots and stable row IDs
  - Positive typed Qwen LoRA/QLoRA identities and two-stage genuine-QLoRA proof
  - Response-only Qwen supervision with versioned formatter and masking provenance
  - Strict raw-output parser, complete fixed-label metrics, and safety-gated checkpoint selection
  - Actual saved-checkpoint and final-step deterministic validation generation
affects: [40-02-evidence-lifecycle, 40-03-phobert, 40-04-local-probe, 40-05-colab-runs, 41-held-out-evaluation]

actuals:
  tokens: 48379
  tasks: 3
  commits: 1
  implementation_commit: 95beed5

tech-stack:
  added: []
  patterns:
    - lexical authorization followed by redirect-component rejection before open
    - immutable exact-byte dataset snapshots as downstream authority
    - requested-versus-resolved adaptation modes with typed proof objects
    - response-only chat-template masking and formatter hashing
    - raw-generation retention with recomputed fail-closed metrics

key-files:
  created:
    - src/model_adaptation/phase40_contract.py
    - src/model_adaptation/phase40_modes.py
    - src/model_adaptation/phase40_metrics.py
    - tests/model_adaptation/test_phase40_contract.py
    - tests/model_adaptation/test_phase40_quantization.py
    - tests/model_adaptation/test_phase40_metrics.py
  modified:
    - src/model_adaptation/cli.py
    - src/model_adaptation/doctor.py
    - src/model_adaptation/training.py
    - tests/model_adaptation/test_cli.py
    - tests/model_adaptation/test_doctor.py
    - tests/model_adaptation/test_training.py

key-decisions:
  - "Training consumes a preflighted Phase40DataContract and never reopens caller paths through the legacy loader."
  - "A requested QLoRA run resolves only after approved bitsandbytes, NF4/double-quant, real Linear4bit, frozen-base, adapter-only, and response-masked backward-gradient proof."
  - "Checkpoint validation runs against each actual saved model state; an offline schedule cannot relabel one current model as historical checkpoints."
  - "Raw model output is reparsed at every metric trust boundary, and all aggregate metrics are recomputed from retained rows."
  - "The reserved Phase 41 partition remains opaque metadata and is never opened by Phase 40 code or fixtures."

patterns-established:
  - "Reject before open: authorize every operator-controlled path lexically, then reject symlink/junction components before reading authority or data."
  - "Evidence from sources: retain exact raw bytes, raw generations, parser exceptions, stable row IDs, and checkpoint artifact hashes before computing summaries."
  - "No semantic fallback: missing QLoRA capability, invalid output, inconsistent metrics, or omitted adaptation mode is an explicit failure."

requirements-completed: []
requirements-enabled: [TRAIN-02, TRAIN-03, TRAIN-06]

coverage:
  - id: D1
    description: Canonical train/validation-only preflight and immutable byte-faithful row snapshots
    requirement: TRAIN-03
    verification:
      - kind: integration
        ref: tests/model_adaptation/test_phase40_contract.py (44 passed)
        status: pass
    human_judgment: false
  - id: D2
    description: Explicit LoRA/QLoRA identity with fail-closed genuine four-bit proof and mode-specific doctor
    requirement: TRAIN-02
    verification:
      - kind: unit
        ref: tests/model_adaptation/test_phase40_quantization.py (39 passed)
        status: pass
    human_judgment: false
  - id: D3
    description: Response-only Qwen masking with stable formatter and masking provenance
    requirement: TRAIN-03
    verification:
      - kind: unit
        ref: tests/model_adaptation/test_phase40_metrics.py response-only fixtures
        status: pass
    human_judgment: false
  - id: D4
    description: Deterministic saved-checkpoint generation, strict invalid-output metrics, and safety-gated checkpoint selection
    requirement: TRAIN-06
    verification:
      - kind: integration
        ref: tests/model_adaptation/test_phase40_metrics.py (43 passed)
        status: pass
    human_judgment: false
  - id: D5
    description: Production training consumes immutable snapshots and preserves all Phase 40 invariants without regressing the repository
    requirement: TRAIN-06
    verification:
      - kind: integration
        ref: python -m pytest -q --basetemp .tmp/pytest-p40-01-full-final (660 passed)
        status: pass
    human_judgment: false

duration: 1h15m elapsed including independent review and two full regressions
completed: 2026-08-24
status: complete
---

# Phase 40 Plan 01: Fail-Closed Training Boundary Summary

**Canonical train/validation snapshots now feed response-only Qwen LoRA/QLoRA training, genuine quantization proof, deterministic saved-checkpoint generation, and tamper-resistant safety metrics without touching the held-out partition.**

## Performance

- **Duration:** 1 hour 15 minutes elapsed, including independent review and two full repository regressions
- **Started:** 2026-08-24T10:27:03+07:00
- **Completed:** 2026-08-24T11:42:17+07:00
- **Tasks:** 3
- **Files created/modified:** 17

## Accomplishments

- Added a reject-before-open data boundary that validates canonical authority/train/validation paths, exact bytes, schema, support, seed separation, and deterministic row identities while carrying test only as opaque metadata.
- Replaced implicit quantization behavior with positive experiment identities and two proof stages; genuine QLoRA now requires the approved runtime and real four-bit/gradient evidence, while LoRA proves the symmetric absence of quantization.
- Replaced whole-sequence supervision with response-only labels and right-padding masks, retaining one stable formatter hash across train and validation.
- Added strict raw JSON prediction handling, a fixed 4x5 confusion matrix, complete per-class/aggregate/safety slices, and deterministic safety-gated checkpoint selection.
- Bound generation to saved adapter tensors proven byte-for-tensor equal to the live model state; retained checkpoint identities distinguish a changed final adapter even at the same optimizer step, and only the selected retained state can be published.

## Task Commits

Plan execution remained uncommitted under the original instruction. The user later authorized Git commits, and the integrated Plan 40 implementation was captured in `95beed5`.

## Files Created/Modified

- `src/model_adaptation/phase40_contract.py` - Canonical path, byte, schema, split-integrity, and stable-row-ID contract.
- `src/model_adaptation/phase40_modes.py` - Experiment enums plus preload and loaded-model LoRA/QLoRA proofs.
- `src/model_adaptation/phase40_metrics.py` - Strict parser, retained prediction rows, recomputed metrics, and checkpoint selection.
- `src/model_adaptation/training.py` - Response-only datasets/collator, real gradient probe, immutable-contract consumption, and checkpoint/final generation callback.
- `src/model_adaptation/doctor.py` - Side-effect-free positive-mode readiness with accurate QLoRA failure guidance.
- `src/model_adaptation/cli.py` - Required canonical train/validation and positive-mode inputs, with preflight before registry/output work.
- `tests/model_adaptation/test_phase40_{contract,quantization,metrics}.py` - Fixture-only executable contracts with no real split/model/GPU access.
- Existing model-adaptation/runtime tests - Explicit mode and immutable-contract regression updates.

## Decisions Made

- Canonical snapshots, rather than paths or reparsed JSON, are the only Phase 40 training source after preflight.
- The Stage 2 proof validates facts against the exact `Linear4bit` type exported by the imported bitsandbytes runtime; a resolved mode name or spoofed class metadata cannot substitute for missing evidence.
- A saved-checkpoint callback performs intermediate generation. The final adapter is deduplicated only when both optimizer step and proven tensor-state identity match an already validated checkpoint.
- Metric objects are not trusted merely because they are frozen: construction and selection both reparse raw output and recompute all derived values.

## Deviations from Plan

### Auto-fixed Issues

**1. Security hardening: rejected canonical-path symlink and junction redirects**
- **Found during:** Independent post-implementation review of Task 1.
- **Issue:** Lexically canonical paths could still redirect an open to another file, including the reserved partition.
- **Fix:** Added anchor-to-target `lstat` checks for symbolic links and Windows junction tags before the first open, plus zero-open fixture regressions.
- **Verification:** Contract suite, 44/44 passed.
- **Committed in:** `95beed5` (post-execution authorization).

**2. Proof hardening: closed fabricated mode and metric evidence paths**
- **Found during:** Independent post-implementation review of Tasks 2 and 3.
- **Issue:** A class-name impostor could mimic `Linear4bit`; incomplete proof objects and hand-constructed parsed/metric values could contradict their retained sources.
- **Fix:** Required the imported runtime type, validated every proof invariant, reparsed raw predictions, and recomputed metric aggregates/matrices from retained rows.
- **Verification:** Quantization and metrics suites, 78/78 passed.
- **Committed in:** `95beed5` (post-execution authorization).

**3. Production wiring: replaced legacy path reload and static checkpoint schedule**
- **Found during:** Production-path review after the initial fixture tracer passed.
- **Issue:** The backend still reopened paths, the real Trainer had no generation callback, and a helper could label repeated final-model outputs as historical steps.
- **Fix:** Required `Phase40DataContract`, installed a real save callback, handled an unsaved final state, retained every validated adapter before Trainer pruning, materialized the exact selected state, and independently reloaded/rehashed that state immediately before canonical-path registry publication.
- **Verification:** Production-focused Plan 40-01 suite 141/141; repository suite 660/660. An earlier-checkpoint-wins regression proves the final state is not accidentally registered, and an identity mismatch leaves registry bytes unchanged.
- **Committed in:** `95beed5` (post-execution authorization).

**4. Compatibility updates: made programmatic mode intent mandatory**
- **Found during:** Direct API review.
- **Issue:** Non-CLI callers could still inherit a LoRA default even though the CLI required a positive mode.
- **Fix:** Made adaptation mode a required builder/doctor argument and updated existing tests/callers explicitly.
- **Verification:** Model-adaptation suite 193/193 passed.
- **Committed in:** `95beed5` (post-execution authorization).

---

**Total deviations:** 4 auto-fixed (2 security/correctness, 1 production wiring, 1 compatibility).
**Impact on plan:** All changes enforce the plan's existing fail-closed truths; no external service, package installation, model download, GPU run, or held-out access was added.

## Issues Encountered

- The repository-wide suite contains slow existing integration tests; the final run completed normally at 660 passed in 620.99 seconds.
- Two SWIG deprecation warnings remain external to this plan and did not affect results.

## User Setup Required

None for this plan. Package changes, model downloads, GPU execution, and Colab operations remain behind later operator checkpoints.

## Verification

- Focused Plan 40-01 contract/quantization/metrics suite: 127/127 PASS.
- Production-focused Plan 40-01 suite including training publication regressions: 141/141 PASS.
- Model-adaptation suite: 198/198 PASS.
- Full repository suite: 660/660 PASS in 620.99 seconds; two pre-existing SWIG deprecation warnings only.
- `python -m compileall -q src tests`: PASS.
- `git diff --check`: PASS (line-ending notices only).
- Real split, held-out split, model, GPU, package installer, external API, and web access during tests: 0.

## Next Phase Readiness

Plan 40-02 can build append-only run evidence, probe discard receipts, exact resume compatibility, deterministic graph provenance, and typed Colab handoff on top of the immutable snapshot/mode/metric contracts. No operator or GPU checkpoint is needed for its fixture implementation.

## Self-Check: PASSED

- All declared Plan 40-01 artifacts exist.
- Focused and full regression gates pass.
- The held-out partition was never opened, hashed, globbed, or enumerated.
- No Git mutation occurred during execution; the later authorized implementation commit is `95beed5`. No external operation occurred.

---
*Phase: 40-multi-model-training-evidence*
*Completed: 2026-08-24*
