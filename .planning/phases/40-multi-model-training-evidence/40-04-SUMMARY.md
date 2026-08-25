---
phase: 40-multi-model-training-evidence
plan: 04
subsystem: local-lora-qlora-resource-decision
tags: [rtx5050, lora, qlora, nf4, telemetry, eta, artifact-discard]

requires:
  - phase: 40-multi-model-training-evidence
    plan: 03
    provides: Audited training backends, evidence lifecycle, and pinned local model inputs
provides:
  - Honest incomplete ordinary-LoRA pressure evidence under the original immutable clock
  - Genuine dated QLoRA 5+40 measurement with NF4 and adapter-gradient proof
  - Recomputable same-machine full-schedule ETA and complete resource telemetry
  - Verified removal of every disposable runtime, checkpoint, and adapter
affects: [40-05-colab-runs, report-revision, defense-evidence]

actuals:
  tasks: 3
  commits: 2
  qlora_implementation_commit: be6f1b9
  colab_handoff_commit: d54e0dd

tech-stack:
  added: [bitsandbytes-0.50.1]
  patterns:
    - immutable dated experiment clock and self-hashed operator
    - parent telemetry with disposable child runtime
    - exact ordered optimizer-event evidence and fail-closed ETA
    - source-tree hash link instead of rewriting expired evidence

key-files:
  created:
    - src/model_adaptation/phase40_qlora_session.py
    - tests/model_adaptation/test_phase40_qlora_session.py
    - data/models/phase40/probes/rtx5050-qlora-session-20260825/session-manifest.json
  modified:
    - .planning/phases/40-multi-model-training-evidence/40-LOCAL-PROBE-REPORT.md
    - .planning/phases/40-multi-model-training-evidence/40-04-PLAN.md

key-decisions:
  - "The expired 2026-08-24 LoRA root remains immutable; QLoRA uses a separately dated root that hash-links the complete prior evidence tree."
  - "The measured 72.83-minute value belongs only to genuine QLoRA; the 18.42-18.88-hour provisional estimate belongs only to incomplete ordinary LoRA."
  - "A local probe never supplies a parent adapter or checkpoint to a full run, even when it completes successfully."
  - "Colab remains the chosen full-run evidence route for complete comparable logs, curves, validation bundles, and GGUF export, not because local QLoRA was proven too slow."

requirements-completed: []
requirements-enabled: [TRAIN-01, TRAIN-02, TRAIN-03, TRAIN-06]

completed: 2026-08-25
status: complete
---

# Phase 40 Plan 04: Local Resource Decision Summary

**The RTX 5050 decision is evidence-backed: ordinary LoRA ran with effectively no VRAM headroom and did not finish its target, while genuine QLoRA completed the exact 5+40 contract and projects about 72.83 minutes for the locked 1,245-step schedule.**

## Delivered

- Preserved the original ordinary-LoRA result literally as `error / parent_controller_error`, with 5 warm-up plus 26 measured steps, no OOM, sustained 7,902/8,151 MiB GPU pressure, and no surviving model artifact.
- Started one new 7,200-second dated QLoRA clock without modifying or resuming the expired root. The session binds its own source SHA, the historical evidence-tree SHA, canonical train/validation identities, pinned Qwen snapshot, package receipt, and live runtime identities.
- Proved real `4bit-qlora`: NF4, double quantization, 252 `Linear4bit` modules, frozen base weights, 504 adapter-only trainables, and finite/nonzero adapter gradients before optimizer step 1.
- Retained exactly five warm-up plus 40 measured steps, one measured validation pass, one isolated checkpoint measurement, terminal resource telemetry, sanitized child logs, and a canonical `run_end`.
- Measured median optimizer time 3.462389 seconds, 1.12034 examples/s, 346.98349 tokens/s, and 59.075746 seconds combined validation/save overhead. The locked formula projects 4,369.750238 seconds, or 72.83 minutes, and labels it as an estimate.
- Recorded peak device use 7,516/8,151 MiB, 395 MiB minimum free, 22,136,381,440 bytes peak system-RAM use, 89C peak temperature, and no OOM or thermal stop.
- Hashed and deleted the disposable runtime/checkpoints, then verified the five-stage ledger and 22-artifact session manifest against the unchanged historical source tree.

## Controlled Deviation

The original plan expected QLoRA under the same local-decision root. That root's immutable two-hour clock had already expired, and its hash-bound historical code/evidence could not be changed honestly. The dated continuation therefore uses a new root and clock while treating the old tree as immutable, hash-linked input. It does not reset, edit, or reinterpret the LoRA result.

## Verification

- Dated session verifier: PASS (`measured / evidence_target_reached`).
- Exact target: 5 warm-up + 40 measured optimizer steps; one validation and one checkpoint event.
- Runtime and checkpoint paths: absent after verified discard.
- Historical source SHA before/after every dated stage: `46bce0f7e3807f62465c84492e524327e0df9b5cf8beaf938bd7f101109e9271`.
- Session-manifest SHA-256: `ef992ddd7f0af03df2ca44c352f044e042d5d9c963afa7b89366ec22aeb4a795`.
- QLoRA focused/historical suite: 46/46 PASS.
- Final model-adaptation regression after Colab/GGUF integration: 484/484 PASS; two existing SWIG deprecation warnings only.
- Reserved Phase 41 split: not opened, hashed, copied, or enumerated.

## Next Boundary

Plan 40-05 Task 1 is already frozen in commit `d54e0dd`. The next action is the explicit human Colab package/model authority checkpoint, followed by three fresh notebook runs. No local probe artifact is transferable.

---
*Phase: 40-multi-model-training-evidence*
*Completed: 2026-08-25*
