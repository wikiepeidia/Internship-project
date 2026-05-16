---
status: diagnosed
phase: 03-local-model-adaptation-and-deployment-paths
source: 03-01-SUMMARY.md, 03-02-SUMMARY.md, 03-03-SUMMARY.md, 03-04-SUMMARY.md, documents/internship-proposal.md, .planning/PROJECT.md, .planning/ROADMAP.md, .planning/STATE.md
started: 2026-05-11T14:10:53Z
updated: 2026-05-16T00:00:00Z
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
result: issue
reported: "The active training CLI and doctor defaults still point to data/splits/train.jsonl and val.jsonl (37/12 rows from manifest-phase1-uat-gap), while Phase 1 closure and the larger local pilot treat recovered-balanced-claude-v2 as the final retained dataset evidence (476/207/208 governed rows)."
severity: major

### 9. Proposal deviation is explicitly documented for university reporting

expected: The repo should contain a concise supervisor-facing note that explains why the original proposal's 8B fine-tuning task was narrowed to a 4B baseline winner and how this still serves the local deployment and quality goals.
result: issue
reported: "The planning docs justify the 4B decision internally, but there is not yet a dedicated supervisor-facing reconciliation note for the proposal's original 8B wording."
severity: minor

## Summary

total: 9
passed: 7
issues: 2
pending: 0
skipped: 0
blocked: 0

## Gaps

- truth: "The default Phase 3 training command should target the retained governed dataset lineage adopted at Phase 1 closure."
  status: failed
  reason: "Quick proposal check found that `src.model_adaptation.cli` defaults to `data/splits/train.jsonl` and `val.jsonl` (37/12 rows from `phase1-uat-gap`), while Phase 1 closure designates `recovered-balanced-claude-v2` (476/207/208) as the final retained dataset evidence and the larger Phase 3 pilot used the retained recovered-balanced validated source."
  severity: major
  test: 8
  root_cause: "The CLI helper `_default_split_path()` still resolves to the legacy top-level `data/splits/*.jsonl` files created for the earlier `phase1-uat-gap` lineage, and no retained-dataset profile or updated default was added after the recovered dataset closure."
  artifacts:
  - path: "src/model_adaptation/cli.py"
    issue: "Train and doctor defaults still point to `data/splits/*.jsonl`."
  - path: ".planning/phases/01-data-foundation-and-split-governance/01-06-SUMMARY.md"
    issue: "Phase 1 closure declares `recovered-balanced-claude-v2` as the final retained dataset evidence."
  - path: ".planning/phases/03-local-model-adaptation-and-deployment-paths/03-REVIEWS.md"
    issue: "The larger locked pilot cites `recovered-balanced-validated-claude-v2.jsonl` as its source dataset."
  missing:
  - "Retarget the Phase 3 train and doctor defaults to the retained `recovered-balanced-claude-v2` split lineage, or add an explicit dataset-profile argument and make the retained lineage the documented main-run command."
  - "Re-run the short smoke command once against the retained dataset path before launching the longer baseline training run."
  debug_session: ""

- truth: "The project should preserve a supervisor-facing explanation for the proposal deviation from an 8B target to a 4B baseline winner."
  status: failed
  reason: "The internal planning files now justify the 4B-primary decision, but the university proposal still says Task 3 fine-tunes an 8B model and no dedicated reconciliation note exists yet for external reporting."
  severity: minor
  test: 9
  root_cause: "The proposal was written before the local pilot and hardware-fit comparison locked the 4B baseline, so the deviation was captured in planning artifacts but not yet translated into a supervisor-facing progress note."
  artifacts:
  - path: "documents/internship-proposal.md"
    issue: "Task 3 still states an open-source 8B model."
  - path: ".planning/PROJECT.md"
    issue: "Current plan now uses a 4B-primary path."
  - path: ".planning/ROADMAP.md"
    issue: "Phase 3 follow-up note locks the 4B winner and runner-up."
  missing:
  - "Add a brief supervisor or progress note that explains the 8B-to-4B decision as a quality and hardware-fit optimization rather than a scope reduction."
  - "Mention that the 7B path remains a comparison or accelerated-path option, so larger-model exploration was not discarded outright."
  debug_session: ""

Overall direction remains aligned with the proposal, but the next longer training run should use the retained final dataset lineage and the 8B-to-4B rationale should be recorded explicitly for university-facing reporting.
