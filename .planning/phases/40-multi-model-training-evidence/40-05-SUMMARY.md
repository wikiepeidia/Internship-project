---
phase: 40-multi-model-training-evidence
plan: 05
subsystem: local-two-model-production-comparison
tags: [qwen, qlora, phobert, gguf, validation, runtime-authority, human-review]

requires:
  - phase: 40-multi-model-training-evidence
    plan: 04
    provides: Sealed ordinary-LoRA resource evidence and genuine local QLoRA feasibility proof
provides:
  - Frozen dual-origin comparison authority for the completed local Qwen QLoRA and PhoBERT runs
  - Portable runtime, Qwen GGUF, and PhoBERT release receipts with external production verification
  - Validation-only two-model comparison over the same 219 canonical rows per model
  - Deterministic 52-row Vietnamese human-review queue for Plan 40-06
affects: [40-06-human-review-closure, 41-held-out-evaluation, report-revision, defense-evidence]

actuals:
  tasks: 3
  implementation_commits: [9f0c218, 0e6c232, ab404d7, 7093a16, 68b3082, b6a5673]

tech-stack:
  added: []
  patterns:
    - immutable source-tree and execution-origin authorities
    - portable receipt verification followed by external live-production closure
    - deterministic selected-prediction comparison and message-bound review queue
    - exact legacy-artifact compatibility without weakening new producer schemas

key-files:
  created:
    - data/models/phase40/comparison-launch-receipt.json
    - data/models/phase40/comparison-launch-capability.claim
    - data/models/phase40/comparison-manifest.json
    - data/models/phase40/comparison-report.md
    - data/models/phase40/selected-prediction-bundles.json
    - data/models/phase40/review/review-queue.jsonl
    - data/models/phase40/review/review-queue-manifest.json
    - data/models/phase40/review/reviewer-return.template.jsonl
    - .planning/phases/40-multi-model-training-evidence/40-VALIDATION-COMPARISON.md
  modified:
    - src/model_adaptation/phase40_comparison_launch.py
    - src/model_adaptation/phase40_phobert_release.py
    - src/model_adaptation/phase40_runtime_materialize.py
    - src/model_adaptation/phobert_training.py

key-decisions:
  - "Both quality models remain the already-completed fresh local runs; Plan 05 performs no retraining and Colab remains dormant."
  - "Ordinary LoRA remains bounded RTX 5050 resource evidence only and contributes no validation predictions or accuracy claim."
  - "Qwen and PhoBERT keep their distinct immutable run origins; the comparison authority selects both without rewriting either history."
  - "One predeclared seed cannot support variance, t-test, significance, or stable-superiority claims, and the speed comparison is explicitly inadmissible."
  - "Plan 40-06 is a real human gate: automation may verify the return file but may not manufacture Vietnamese reviewer judgments."

requirements-completed: []
requirements-enabled: [TRAIN-01, TRAIN-02, TRAIN-03, TRAIN-04, TRAIN-05, TRAIN-06]

completed: 2026-08-26
status: complete
---

# Phase 40 Plan 05: Local Full-Run and Validation Comparison Summary

**Both fresh local quality runs are sealed and comparison-ready. Qwen QLoRA reached macro-F1 0.9885153110 and PhoBERT reached 0.9848929140 on the same 219-row validation snapshot; both passed every risky-class recall floor with zero invalid outputs.**

## Delivered

- Froze the 33-file comparison finalizer source closure with source-tree SHA-256 `520aeb6a58276750c3dd37be1e9ee6983fdd7f6c807c24332625020ec0334cc2` and final comparison-authority file SHA-256 `7ac5541d42a60d7b86619cb34af1006f9b6bad7f34183b5f7073a9574fbd89c7`.
- Bound the verified Qwen Q8_0 GGUF (4,280,403,232 bytes; SHA-256 `457f6f92d36a7d54da9916fd80a4028dcd055a653a015c4877370a0fea4d18ab`) and the final PhoBERT release without copying either large model into Git.
- Sealed the exact runtime dependency authority and two independent materializations. Strict smoke execution now uses a disposable TorchInductor cache while continuing to omit user-identity variables.
- Ran the fixed comparison launcher from a clean isolated root with no reserved-split namespace present. The launcher pinned PowerShell 7.6.1 and Python 3.13.13, verified both model origins and portable receipts, and completed exactly once.
- Retained both quality rows regardless of winner. Qwen selected step 200 with accuracy 0.9908675799; PhoBERT selected step 100 with accuracy 0.9863013699. Risky-class recalls were Qwen 0.9868421053/1.0/1.0 and PhoBERT 1.0/0.9545454545/1.0 for bank/Zalo/task respectively.
- Generated a deterministic 52-row review queue with full canonical messages and exact source-row hashes, plus a return template that Plan 40-06 can validate fail-closed.
- Mirrored the mechanically generated comparison report byte-for-byte into `.planning/phases/40-multi-model-training-evidence/40-VALIDATION-COMPARISON.md`.

## Controlled Compatibility Repairs

- A legacy successful PhoBERT run used older validation-summary key names. Compatibility is exact and PhoBERT-only; the current producer now writes the shared canonical schema.
- Multiple already-verified paths may legitimately carry the same metric SHA-256. Selection is deterministic only after every candidate has passed bundle hash verification; mismatched or unverified duplicates still fail closed.
- The PhoBERT release verifier permits the canonical fixed-input extraction root only in the exact sanitized argument position. General absolute host-path rejection remains active.

The earlier live progress note recorded PhoBERT macro-F1 `0.9815140779573065`. Final selected-prediction recomputation from the frozen raw artifact is `0.9848929139790588`; that mechanically reproduced value controls the comparison, report, and downstream state. The earlier number remains identified as historical progress rather than silently erased.

## Verification

- Clean comparison root: PASS, 219 validation rows per model, 52 review rows, quality comparison admissible.
- External production closure: PASS for Qwen GGUF, PhoBERT release, portable runtime, and exact launch identities.
- Comparison manifest SHA-256: `08f76337dd445a6425be2f8a7514a0b847b50fc29e1ec1b84939a5276dc455d5`.
- Comparison report SHA-256: `fb7424b7139e4e354464b98d10fd4e28376b2963da4c1a21e37ebe147b568dd5`.
- Review queue SHA-256: `c79fff001bdc78b196768f80a76e30b615d32c4e60f27d607e02cd9210f81010`.
- Final model-adaptation regression: 832/832 PASS; two existing SWIG deprecation warnings only.
- Reserved Phase 41 split: not opened, read, hashed, copied, enumerated, or used.

## Next Boundary

Plan 40-06 is blocked on genuine Vietnamese human review of the 52 queued validation rows. An agent may validate and summarize the completed return but must not fill it or infer reviewer decisions. Resume only after the user supplies:

`Vietnamese review complete: data/models/phase40/review/reviewer-return.jsonl`

Phase 41 remains fail-closed until Plan 40-06 accepts that file, resolves the Colab contingency as closed or invoked, and freezes the final two-model identities. No reserved evaluation begins from this summary.

---
*Phase: 40-multi-model-training-evidence*
*Completed: 2026-08-26*
