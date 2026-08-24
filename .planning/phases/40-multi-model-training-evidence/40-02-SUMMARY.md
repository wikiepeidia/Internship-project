---
phase: 40-multi-model-training-evidence
plan: 02
subsystem: reproducible-training-evidence
tags: [append-only-events, exact-resume, probe-discard, immutable-handoff, comparison-review]

requires:
  - phase: 40-multi-model-training-evidence
    plan: 01
    provides: Immutable snapshots, explicit Qwen modes, deterministic validation, and safety-gated checkpoint selection
provides:
  - Append-only run events and hash-verified complete evidence bundles
  - Bounded non-publishable probe lifecycle with measured ETA and discard receipts
  - Exact full-run resume controls and request-bound registry-free comparison execution
  - Deterministic source/input archives and a typed three-run Colab handoff
  - Mechanical three-model comparison, graph replay, review queue, and review persistence contracts
affects: [40-03-phobert-notebooks, 40-04-local-probe, 40-05-colab-runs, 40-06-human-review]

actuals:
  tasks: 3
  commits: 1
  implementation_commit: 95beed5

tech-stack:
  added: []
  patterns:
    - append-only observations followed by atomic immutable finalization
    - cumulative resume manifests bound to append-only event prefixes and retained telemetry
    - projected terminal lifecycle verified before canonical RUN_END commit
    - exact request templates with runtime hardware supplied only after execution
    - deterministic ZIP transfer with verify-before-data-open
    - request-bound evidence roots separated from mutable training work roots
    - registry-free scientific comparison runs that retain safety failures

key-files:
  created:
    - src/model_adaptation/phase40_callbacks.py
    - src/model_adaptation/phase40_evidence.py
    - src/model_adaptation/phase40_graphs.py
    - src/model_adaptation/phase40_handoff.py
    - tests/model_adaptation/test_phase40_evidence.py
    - tests/model_adaptation/test_phase40_handoff.py
    - tests/model_adaptation/test_phase40_training.py
  modified:
    - src/model_adaptation/training.py
    - src/model_adaptation/cli.py
    - tests/model_adaptation/test_cli.py
    - tests/model_adaptation/test_training.py
    - tests/model_adaptation/test_phase40_quantization.py

key-decisions:
  - "A full comparison run writes final evidence directly to its request-bound returned root; mutable checkpoints remain under a separate work root."
  - "A probe is capped at 30-50 post-warm-up optimizer steps, cannot resume or publish, and must end with a verified discard receipt."
  - "A full resume accepts one explicit checkpoint only when every controlled field and retained payload hash matches; latest-style discovery is forbidden."
  - "The train/validation transfer archive contains exactly its manifest, train.jsonl, and val.jsonl, and validates its directory and hashes before opening either data member."
  - "Failed safety gates remain complete scientific evidence but are not admissible as release-ready results."
  - "Single-seed results explicitly support no variance, t-test, significance, or stable-superiority claim."
  - "A failed attempt may resume from its exact sealed checkpoint only through a bounded same-run terminal suffix; arbitrary event rollback remains forbidden."
  - "Canonical RUN_END is the final commit point, after staged evidence materialization, verification, and byte-checked publication all succeed."

requirements-completed: []
requirements-enabled: [TRAIN-01, TRAIN-02, TRAIN-03, TRAIN-05, TRAIN-06]

coverage:
  - id: E1
    description: Append-only event/evidence lifecycle and deterministic graph replay
    requirement: TRAIN-06
    verification:
      - kind: integration
        ref: tests/model_adaptation/test_phase40_evidence.py
        status: pass
    human_judgment: false
  - id: E2
    description: Probe timing, disposal, full authority, exact resume, and registry-free Qwen comparison execution
    requirement: TRAIN-01
    verification:
      - kind: integration
        ref: tests/model_adaptation/test_phase40_training.py
        status: pass
    human_judgment: false
  - id: E3
    description: Deterministic source/input handoff, returned-bundle comparison, and immutable review queue
    requirement: TRAIN-05
    verification:
      - kind: integration
        ref: tests/model_adaptation/test_phase40_handoff.py
        status: pass
    human_judgment: false
  - id: E4
    description: Model-adaptation compatibility regression
    requirement: TRAIN-06
    verification:
      - kind: regression
        ref: python -m pytest tests/model_adaptation -q (407 passed after post-completion security remediation)
        status: pass
    human_judgment: false

completed: 2026-08-24
status: complete
---

# Phase 40 Plan 02: Reproducible Training Evidence Summary

**Every Phase 40 run now has a fail-closed path from immutable train/validation authority to replayable events, exact resume controls, verified artifacts, deterministic graphs, and an honest comparison record.**

## Delivered

- Added typed append-only events, runtime/hardware facts, controlled configs, artifact hashes, graph provenance, transfer authority, and atomic evidence verification.
- Added real probe timing/resource capture, bounded post-warm-up sampling, ETA calculation, non-resumable/non-publishable enforcement, and verifiable artifact disposal.
- Added exact checkpoint resume manifests covering inputs, model/revision, mode, formatter, seeds, optimizer, precision, cadence, decoder, and saved payload hashes.
- Added deterministic source and train/validation-only input bundles, strict request schemas, fixed returned roots, and typed package/GPU operator returns.
- Added comparison finalization that reopens all evidence, recomputes checkpoint metrics/selection from raw predictions, regenerates graphs, enforces the Qwen quantization-only delta, and retains failed safety runs without presenting them as deployable.
- Added stable-ID-bound Vietnamese review queue generation and exact-coverage human-review persistence.
- Added `build_phase40_qwen_training_config` and `run_phase40_qwen_training`, deriving controls from the frozen request and deliberately avoiding legacy registry mutation.
- Hardened exact resume after completion: manifests now bind cumulative checkpoint candidates, raw predictions, metrics, telemetry, event-prefix identity, and pinned local base-model provenance.
- Moved canonical `RUN_END` to a staged final commit after evidence materialization and verification; failures retain measured `RESOURCE -> FAILURE` evidence and remain exactly resumable.

## Deviations Resolved

1. Full evidence originally inherited a mutable work-root convention. Final evidence now materializes directly in the immutable request-bound returned root, with overlap/symlink/fresh-versus-resume checks.
2. The first request draft guessed accelerator facts. Hardware is now absent from the pre-run template and verified only from returned runtime evidence.
3. Comparison validation originally trusted summaries too much. It now reloads raw checkpoint predictions and metric files, recomputes every shared metric and selection decision, and regenerates graphs.
4. Legacy training required pilot registry state and rejected safety-failed outputs. A separate comparison execution seam now needs no registry and returns complete safety-failed evidence for honest analysis.
5. Free-text operator/reviewer fields are normalized to one line before Markdown generation.
6. Post-completion review found that a failed-attempt suffix, cumulative telemetry, and retained candidate history needed stronger binding. Resume validation now accepts only the bounded same-run terminal suffix, rejects mutation/truncation/foreign events, and carries cumulative resource evidence across retries.
7. Post-completion review found that evidence materialization could fail after an early `RUN_END`, masking the failure and preventing resume. Completed evidence is now built and verified against a projected private lifecycle, outputs are checksum-verified before publication, and the exact canonical event suffix is appended last.
8. Base-model identity is now content-addressed through external sibling provenance manifests for the exact pinned Qwen and PhoBERT revisions; path and ancestor redirects fail before acquisition or model construction.

No deviation added a package, download, GPU action, external API, real training run, or held-out access.

## Verification

- Evidence + training + handoff integration: 107/107 PASS.
- Full model-adaptation suite: 407/407 PASS.
- Full repository regression after the final audit repair: 869/869 PASS; two pre-existing SWIG deprecation warnings only.
- Independent security re-audit: PASS, with all resume, telemetry, lifecycle, provenance, and symlink blockers closed.
- Python compile checks: PASS.
- Deterministic graph/source/input reconstruction and verify-only replay: PASS in fixtures.
- Real split, reserved held-out partition, GPU, package installer, network, and external service access: 0.
- Implementation commit: `95beed5`, created after the user lifted the earlier no-commit constraint.

## User Setup Required

None for this plan. Package legitimacy, model acquisition, GPU execution, Colab/Drive authority, and human review remain explicit later checkpoints.

## Next Phase Readiness

Plan 40-03 can add the ordinary full PhoBERT classification baseline and three statically gated Colab controllers on top of these evidence and handoff contracts.

## Self-Check: PASSED

- All declared Plan 40-02 implementation artifacts exist.
- Focused and model-adaptation regressions pass.
- The held-out partition was never opened, hashed, globbed, or enumerated.
- No Git mutation occurred during execution; the later authorized implementation commit is `95beed5`. No external action occurred.

---
*Phase: 40-multi-model-training-evidence*
*Completed: 2026-08-24*
