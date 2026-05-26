---
status: complete
phase: 07-proposal-closeout-and-quantitative-validation
source:
  - 07-01-PLAN.md
  - 07-02-PLAN.md
  - 07-CONTEXT.md
started: 2026-05-26T05:17:30Z
updated: 2026-05-26T05:20:27Z
---

# Phase 7 UAT

## Current Test

[testing complete]

## Tests

### 1. Recovered-Balanced Evidence Path
expected: Phase 7 should now have one active closeout lineage under the recovered-balanced artifacts. The dataset path should be data/synthetic/recovered-balanced.jsonl, the held-out path should be data/splits/recovered-balanced/val.jsonl, and the final reporting path should no longer rely on the older generic data/splits/val.jsonl sample evidence.
result: pass

### 2. Fresh Baseline Runtime Artifact
expected: The closeout evidence path should point at the refreshed baseline-winner GGUF artifact from proposal-closeout-gguf-2026-05-26, and the documented convert path should use the Python 3.13 convert_hf_to_gguf.py script with q8_0 instead of the broken default q4_k_m route.
result: pass

### 3. Repaired-Holdout Snapshot Refresh
expected: Running the repaired-holdout evaluation should complete on data/splits/recovered-balanced/val.jsonl and save a 210-row Phase 5 snapshot tied to that repaired split rather than the older sample split.
result: pass

### 4. Review Pack Regeneration
expected: The explanation review pack should regenerate from the fresh repaired-holdout snapshot, stay structurally valid, and be reviewable without schema or runtime crashes.
result: pass

### 5. Final Proposal Verdict Artifact
expected: The final release-eval artifacts should provide one explicit school-facing answer with macro and weighted F1, per-label metrics, and a PASS/BLOCK/FLAG verdict. For the current closeout run, the verdict should honestly be BLOCK because task_scam recall is below the locked 0.90 floor.
result: pass

## Summary

total: 5
passed: 5
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

none at the current Phase 7 UAT level