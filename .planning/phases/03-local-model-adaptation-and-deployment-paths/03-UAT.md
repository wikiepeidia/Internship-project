---
status: complete
phase: 03-local-model-adaptation-and-deployment-paths
source: 03-01-SUMMARY.md, 03-02-SUMMARY.md, 03-03-SUMMARY.md, 03-04-SUMMARY.md, documents/internship-proposal.md, .planning/PROJECT.md, .planning/ROADMAP.md, .planning/STATE.md
started: 2026-05-11T14:10:53Z
updated: 2026-05-17T00:00:00Z
---

# Phase 03 UAT

## Current Test

[testing complete]

## Tests

### 1. Pilot dry-run records a locked baseline winner and runner-up

expected: Running the Phase 3 pilot dry-run should complete without downloading models, write a local registry file, and record a 4B baseline winner plus a runner-up for the later training and runtime paths.
result: pass

### 2. Real smoke training works for the baseline winner alias

expected: Running the training CLI with baseline-winner and --smoke-test should resolve to the locked 4B winner, load the local base checkpoint from D drive, run a short real PEFT fine-tune on the local GPU, and save checkpoint plus adapter summary artifacts under the local model root.
result: pass

### 3. Resume from checkpoint works for the baseline winner alias

expected: Re-running the baseline winner smoke command with --resume-from-checkpoint latest should pick up the latest saved trainer checkpoint and continue to a later checkpoint instead of restarting from scratch.
result: pass

### 4. Real smoke training works for the runner-up alias

expected: Running the training CLI with runner-up and --smoke-test should resolve to the selected runner-up candidate, use the local base checkpoint on D drive, and save a short real checkpoint under the local model root without redownloading weights.
result: pass

### 5. GGUF laptop profile is ready and can analyze text locally

expected: With a staged local registry, the public runtime doctor command should report gguf-laptop as ready and the public analyze command should return the normal structured analysis shape without any cloud fallback guidance.
result: pass

### 6. Accelerated profile is ready and can analyze text locally

expected: With a staged local registry, the public runtime doctor command should report accelerated-local as ready and the public analyze command should return the same structured output shape under the accelerated backend.
result: pass

### 7. Proposal direction remains technically aligned after the 8B to 4B adjustment

expected: The live planning state and Phase 3 training path should still satisfy the proposal's core technical intent: text-only local privacy-preserving analysis, LoRA-based domain adaptation, consumer-grade deployment focus, and a justified model-size choice backed by real hardware evidence.
result: pass

### 8. Default training dataset aligns with the retained Phase 1 dataset lineage

expected: The default Phase 3 training command should point at the retained governed split lineage that best represents the project's final Phase 1 dataset evidence, rather than an earlier UAT-gap sample set.
result: pass

### 9. Proposal deviation is explicitly documented for university reporting

expected: The repo should contain a concise supervisor-facing note that explains why the original proposal's 8B fine-tuning task was narrowed to a 4B baseline winner and how this still serves the local deployment and quality goals.
result: pass

### 10. Full retained-dataset baseline training completes and registers artifacts locally

expected: Running the Phase 3 baseline-winner command without --dry-run or --smoke-test should complete a longer retained-dataset QLoRA run, save periodic checkpoints plus an adapter directory under D drive, and register the final adapter artifact in the local model registry.
result: pass

### 11. Full retained-dataset runner-up training completes and registers artifacts locally

expected: Running the Phase 3 runner-up command without --dry-run or --smoke-test should complete a longer retained-dataset QLoRA run, save periodic checkpoints plus an adapter directory under D drive, and register the final adapter artifact in the local model registry.
result: pass

### 12. Real GGUF conversion produces a registered laptop artifact from the trained baseline adapter

expected: Running the real GGUF conversion flow against the trained baseline winner should produce a registered GGUF artifact under D drive, and `RUNTIME_BACKEND=gguf RUNTIME_PROFILE=gguf-laptop python -m src.runtime.cli doctor` should report READY without relying on staged placeholders.
result: pass

### 13. Accelerated runtime uses the trained runner-up artifact for real inference

expected: With the trained runner-up adapter registered, the accelerated runtime should load and use the adapted model for inference instead of rule-based placeholder logic while preserving the stable output schema.
result: pass

### 14. Runtime profile selection remains explicit across local backends

expected: Operators should be able to switch between gguf and accelerated runtime profiles explicitly via settings and receive profile-specific readiness results without any cloud fallback.
result: pass

## Summary

total: 14
passed: 14
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

- none. Phase 3 Wave 5 closeout plans 03-05, 03-06, and 03-07 are complete.

Overall direction remains aligned with the proposal, both retained-dataset 4B training runs are complete, the baseline GGUF laptop path is now converted and smoke-validated on the real D-drive artifact set, the accelerated runner-up path uses the trained adapter for live inference, and the supervisor-facing 8B-to-4B reconciliation note is now present. Phase 4 is unblocked.
