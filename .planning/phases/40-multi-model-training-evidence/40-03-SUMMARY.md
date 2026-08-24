---
phase: 40-multi-model-training-evidence
plan: 03
subsystem: phobert-and-external-run-controllers
tags: [phobert, colab-controller, model-provenance, exact-resume, terminal-evidence]

requires:
  - phase: 40-multi-model-training-evidence
    plan: 02
    provides: Append-only evidence, exact-resume controls, deterministic handoff, and graph replay
provides:
  - Genuine fully trainable four-logit PhoBERT classification backend using the shared canonical validation contract
  - Pinned local Qwen and PhoBERT snapshot acquisition requests with external content-addressed provenance manifests
  - Three thin canonical Colab controllers and a fail-closed static notebook validator
  - Standard-library operator CLI for request verification, acquisition, preflight, training, evidence, graphs, and notebook validation
  - Audit-hardened cumulative resume and staged terminal-evidence commit semantics
affects: [40-04-local-probe, 40-05-colab-runs, 40-06-human-review, 41-held-out-evaluation]

actuals:
  tasks: 2
  commits: 1
  implementation_commit: 95beed5

tech-stack:
  added: []
  patterns:
    - exact immutable model revision plus external sibling content manifest
    - notebook as a thin typed operator controller rather than a second trainer
    - append-only failed-attempt suffix with cumulative telemetry and exact rollback checkpoint
    - staged completed lifecycle with canonical RUN_END appended last

key-files:
  created:
    - src/model_adaptation/phobert_training.py
    - src/model_adaptation/phase40_notebooks.py
    - src/model_adaptation/phase40_operator.py
    - notebooks/phase40/qwen_lora_colab.ipynb
    - notebooks/phase40/qwen_qlora_colab.ipynb
    - notebooks/phase40/phobert_colab.ipynb
    - tests/model_adaptation/test_phase40_phobert.py
    - tests/model_adaptation/test_phase40_notebooks.py
    - tests/model_adaptation/test_phase40_operator.py
  modified:
    - src/model_adaptation/training.py
    - src/model_adaptation/phase40_callbacks.py
    - src/model_adaptation/phase40_evidence.py
    - src/model_adaptation/phase40_handoff.py
    - tests/model_adaptation/test_phase40_training.py
    - tests/model_adaptation/test_phase40_evidence.py
    - tests/model_adaptation/test_phase40_handoff.py

key-decisions:
  - "PhoBERT is ordinary full encoder-plus-classification-head training with exactly four logits; PEFT, LoRA, QLoRA, and bitsandbytes are prohibited from its backend."
  - "Qwen and PhoBERT use exact immutable upstream revisions and verified local snapshots; notebooks never acquire a model without explicit operator authorization."
  - "Every notebook verifies its request, source archive, input archive, model snapshot, and provenance before allowing a training command."
  - "A canonical lifecycle becomes successful only when all evidence has been staged, materialized, verified, and checksum-published before RUN_END is committed."

requirements-completed: []
requirements-enabled: [TRAIN-03, TRAIN-04, TRAIN-05, TRAIN-06]

coverage:
  - id: P1
    description: Full PhoBERT four-logit preprocessing, checkpoint prediction, selection, evidence, and resume path
    requirement: TRAIN-04
    verification:
      - kind: integration
        ref: tests/model_adaptation/test_phase40_phobert.py (31 passed)
        status: pass
    human_judgment: false
  - id: P2
    description: Three canonical thin notebooks and static policy validator
    requirement: TRAIN-03
    verification:
      - kind: integration
        ref: tests/model_adaptation/test_phase40_notebooks.py (48 passed)
        status: pass
    human_judgment: false
  - id: P3
    description: Explicit model acquisition/provenance and safe operator command surface
    requirement: TRAIN-06
    verification:
      - kind: integration
        ref: tests/model_adaptation/test_phase40_operator.py (20 passed)
        status: pass
    human_judgment: false
  - id: P4
    description: Cumulative exact resume and failure-safe terminal evidence across Qwen, PhoBERT, and the shared event contract
    requirement: TRAIN-06
    verification:
      - kind: security-review
        ref: independent final re-audit PASS; focused Qwen/shared suite 90 passed
        status: pass
    human_judgment: false
  - id: P5
    description: Repository compatibility after all audit remediation
    requirement: TRAIN-06
    verification:
      - kind: regression
        ref: python -m pytest -q (869 passed)
        status: pass
    human_judgment: false

completed: 2026-08-24
status: complete
---

# Phase 40 Plan 03: PhoBERT and Canonical External Controllers Summary

**The hardware-free training layer is complete: PhoBERT is a real four-class baseline, Qwen/PhoBERT model inputs are pinned and content-verified, and all three Colab notebooks are thin, statically gated controllers over one audited repository implementation.**

## Delivered

- Added a genuine `vinai/phobert-base-v2` four-logit sequence classifier pinned to revision `e966aac8cb889325e073aa5f28ff70aca4dbc8c3`, with the encoder and head fully trainable, deterministic Vietnamese segmentation evidence, max length 256, shared immutable validation IDs, raw logits, shared metrics, and safety-gated checkpoint selection.
- Pinned Qwen to `Qwen/Qwen3-4B-Instruct-2507` revision `cdbee75f17c01a7cc42f958dc650907174af0554`; tokenizer and model receive that same revision and load only from a verified local snapshot for training.
- Added external sibling provenance manifests for both base-model snapshots, including deterministic content inventories, exact model identities, and redirect-resistant path validation.
- Added a ten-command standard-library operator CLI, including an explicit-authority model-acquisition command. Existing valid snapshots are reused without importing the hub or requesting a network operation.
- Added three fresh 16-cell notebooks for Qwen LoRA, Qwen QLoRA, and PhoBERT. Each verifies the typed request, source archive, input archive, local model snapshot, and manifest before doctor/resume/train/evidence/graph/export steps.
- Added a static notebook validator that rejects stale data paths, reserved-partition readers, embedded credentials, implicit modes, unpinned dependencies/models, inline trainers/evaluators/graphs, and unverified archives.
- Hardened exact resume across Qwen and PhoBERT so cumulative candidates, raw predictions, metric hashes, resource telemetry, model provenance, and the append-only event prefix survive interruption and are rejected if truncated, mutated, or foreign.

## Independent Audit Remediation

The final security review found and closed six implementation-level gaps without changing the scientific plan:

1. PhoBERT failed-attempt suffixes now preserve cumulative measured telemetry while rejecting malformed, truncated, foreign-run, or nonterminal suffixes.
2. Optimizer-step rollback is permitted only at the exact `FAILURE -> RUN_START` retry boundary; rollback within an attempt remains invalid.
3. Qwen near-final and zero-new-step resumes now retain real checkpoint identity and finish through one valid lifecycle.
4. Qwen failed attempts retain and verify cumulative timing, CUDA peaks, candidates, raw predictions, and metric identities.
5. Model-acquisition requests reject symbolic-link ancestors before any downloader call can be constructed.
6. Post-trainer evidence is now built and verified against a private projected lifecycle, checksum-published, and committed by appending canonical `RUN_END` last. Materialization, publication, or callback-state failure instead records measured `RESOURCE -> FAILURE`, cleans partial outputs, and remains exactly resumable.

The independent final re-audit returned **PASS with no remaining blocker**.

## Verification

- Focused Qwen plus shared lifecycle suite: 90/90 PASS.
- PhoBERT suite: 31/31 PASS.
- Notebook validator suite: 48/48 PASS.
- Operator suite: 20/20 PASS.
- Source-handoff closure suite: 17/17 PASS, including extraction and subprocess imports from the generated allowlisted archive.
- Full model-adaptation suite: 407/407 PASS.
- Full repository suite: 869/869 PASS in 584.84 seconds; two pre-existing SWIG deprecation warnings only.
- Both repository notebook-validator entry points: PASS for all three notebooks.
- Notebook JSON parse, Python compilation, and `git diff --check`: PASS.
- Real split files, held-out test rows, model downloads, package installation, GPU/Colab execution, web/API calls, and external services used: 0.
- Implementation commit: `95beed5`, created after the user lifted the earlier no-commit constraint.

## User Setup Required

Plan 40-04 is the next boundary and was not started. It requires an attended operator checkpoint for the local environment/package decision, authorized base-model acquisition or verified existing snapshots, and the RTX 5050 LoRA/QLoRA probes. Plan 40-05 later requires explicit Colab/Drive authority. These operations must record real outcomes and must not be simulated.

## Next Phase Readiness

The code, notebooks, provenance, evidence, and resume contracts are ready for Plan 40-04. Execution is intentionally stopped before any install, download, GPU allocation, real training, Colab action, or held-out access.

## Self-Check: PASSED

- Every declared Plan 40-03 artifact exists and is covered by executable fixture tests.
- The independent final security audit reports PASS with no blocker.
- The reserved Phase 41 partition was never opened, hashed, globbed, or enumerated.
- No Git mutation occurred during execution; the later authorized implementation commit is `95beed5`. No model acquisition, package change, hardware run, or external action occurred.

---
*Phase: 40-multi-model-training-evidence*
*Completed: 2026-08-24*
