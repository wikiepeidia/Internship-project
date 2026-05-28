---
phase: 07a-task-scam-recall-recovery
plan: "02"
subsystem: training
tags: [colab, notebook, peft, transformers, bitsandbytes, huggingface, qlora, training, evaluation]

requires:
  - phase: 07a-task-scam-recall-recovery-01
    provides: gate bug fix in release_evaluation.py so per-label recall floors block correctly

provides:
  - H100fixedv5.ipynb with self-contained training section (cells A through G) appended after the stop_all_processes cell
  - Colab-ready training workflow for qwen3-4b-instruct-2507 baseline-winner with version-tag task-scam-recovery-2026-05-28
  - Colab evaluation cells that compute per-label recall and write eval-snapshot-task-scam-recovery.json

affects:
  - 07a-task-scam-recall-recovery-03
  - phase 5 evaluation snapshot (overwritten by evaluate-release-split after Colab training completes)

tech-stack:
  added:
    - peft>=0.12.0 (QLoRA adapter training on Colab H100)
    - bitsandbytes>=0.44.0 (quantization support for H100)
    - accelerate>=1.0.0 (multi-device training)
    - huggingface_hub snapshot_download (base model pull from HF)
  patterns:
    - Version-tagged training artifacts (task-scam-recovery-2026-05-28)
    - Colab session dual-role pattern: vLLM generation then training in same session
    - Adapter zip-and-download pattern for local registry registration
    - PeftModel eval inference with fallback prompt when repo classify function unavailable

key-files:
  created:
    - notebooks/H100fixedv5.ipynb (first tracked version — added to git via gitignore negation)
  modified:
    - .gitignore (added !notebooks/*.ipynb to allow tracking H100fixedv5.ipynb)

key-decisions:
  - "Add gitignore negation !notebooks/*.ipynb — the notebook was blocked by *.ipynb gitignore rule and could not be committed without it"
  - "Use snapshot_download for base model download in Colab (D-08 requirement: load from HuggingFace, not local D: drive)"
  - "Cell G uses per-label floors FLOORS dict matching D-01 (task_scam=0.80, bank/zalo=0.90) — consistent with Phase 7a gate fix"
  - "VERSION_TAG hardcoded as task-scam-recovery-2026-05-28 in Cell C per D-10 decision"

patterns-established:
  - "Colab notebook dual-role pattern: vLLM generation section + training section in same notebook, separated by stop_all_processes"
  - "Training section cell ordering: install -> clone/upload -> configure -> download-base-model -> train -> zip -> eval-inference -> snapshot-write"

requirements-completed:
  - EVAL-02

duration: 15min
completed: 2026-05-28
---

# Phase 7a Plan 02: Training Section Cells for H100fixedv5.ipynb Summary

**Self-contained H100 Colab training section with 9 cells (1 markdown + 8 code) appended after stop_all_processes, covering install, clone, config, HF model download, train CLI, adapter zip, adapter eval inference, and snapshot write for version-tag task-scam-recovery-2026-05-28.**

## Performance

- **Duration:** 15 min
- **Started:** 2026-05-28T03:40:53Z
- **Completed:** 2026-05-28T03:55:00Z
- **Tasks:** 1
- **Files modified:** 2 (notebooks/H100fixedv5.ipynb, .gitignore)

## Accomplishments

- Appended 9 new cells (1 markdown header + 8 code cells) to H100fixedv5.ipynb after the existing stop_all_processes cell, enabling the operator to retrain qwen3-4b-instruct-2507 on H100 without any notebook editing mid-session
- Cell 4b downloads Qwen/Qwen3-4B-Instruct-2507 from HuggingFace Hub before training, solving the Colab base-model-path pitfall (local D: drive not available on Colab)
- Cell G writes /content/eval-snapshot-task-scam-recovery.json with per-label recall using the D-01 floors (task_scam=0.80, bank/zalo=0.90), matching the gate fix from plan 07a-01
- All 8 required verification strings confirmed present; existing cells (ACTIVE_ROLE, stop_all_processes, vLLM startup) unchanged

## Task Commits

1. **Task 1: Append training section cells to H100fixedv5.ipynb** - `e556084` (feat)

## Files Created/Modified

- `notebooks/H100fixedv5.ipynb` - New file: H100 Colab notebook with existing vLLM generation section plus 9 new training section cells (A through G); first tracked version in git
- `.gitignore` - Added `!notebooks/*.ipynb` negation rule after `*.ipynb` to allow tracking notebooks in the notebooks/ directory

## Cells Added (count and types)

| # | Cell ID | Type | Purpose |
|---|---------|------|---------|
| 1 | a1b2c3d4 | markdown | Section header: Phase 7a Training Section prerequisites and workflow |
| 2 | b2c3d4e5 | code (Cell A) | Install peft, transformers, accelerate, bitsandbytes, datasets |
| 3 | c3d4e5f6 | code (Cell B) | Clone repo from GitHub or accept manual upload; verify split files |
| 4 | d4e5f6a7 | code (Cell C) | Configure MODEL_ARTIFACT_ROOT, MODEL_REGISTRY_PATH, seed empty registry |
| 5 | e5f6a7b8 | code (Cell 4b) | Download Qwen/Qwen3-4B-Instruct-2507 from HuggingFace via snapshot_download |
| 6 | f6a7b8c9 | code (Cell D) | Run src.model_adaptation.cli train --version-tag task-scam-recovery-2026-05-28 --device cuda --full-precision |
| 7 | a7b8c9d0 | code (Cell E) | Zip adapter via shutil.make_archive; print download instructions |
| 8 | b8c9d0e1 | code (Cell F) | Load PeftModel + base model; run inference on /content/val.jsonl |
| 9 | c9d0e1f2 | code (Cell G) | Compute per-label recall; write eval-snapshot-task-scam-recovery.json |

**Version tag used in training command:** `task-scam-recovery-2026-05-28`

## Existing Cells Confirmed Unchanged

The following cells from the original notebook were confirmed intact (same cell IDs, same source):

| Cell ID | Content |
|---------|---------|
| 83777174 | Phase 7 H100 Colab Endpoint Notebook markdown header |
| 5a04df79 | vllm + pyngrok install (%%capture) |
| fd73909e | Imports, ACTIVE_ROLE, MODEL_PROFILES, WORKDIR setup |
| 5554e7b4 | Helper functions: tail_log, stop_all_processes, start_vllm_server, etc. |
| e2e3d518 | server_process = start_vllm_server() |
| 8c27feb8 | wait_for_vllm_ready(...) |
| 930f199c | start_tunnel() — prints OPENAI_COMPATIBLE_* env and local CLI command |
| b676efc2 | How To Use This Notebook markdown |
| ca6822ab | stop_all_processes(kill_tunnel=True) |

## Verification Output

```
Checks: [True, True, True, True, True, True, True, True]
PASS
```

All 8 required strings verified: task-scam-recovery-2026-05-28, peft, bitsandbytes, src.model_adaptation.cli, shutil.make_archive, stop_all_processes, eval-snapshot-task-scam-recovery, PeftModel.

Additional checks:
- `valid JSON` — notebook parses as valid JSON
- `existing cells intact` — stop_all_processes and ACTIVE_ROLE confirmed in full source

## Decisions Made

- Added `!notebooks/*.ipynb` negation to `.gitignore` because `*.ipynb` (line 141) was blocking the notebook from being tracked. This is the correct approach for intentionally-tracked Colab notebooks in this repo.
- Matched Cell G recall floors to D-01 decision: task_scam=0.80, bank_impersonation=0.90, zalo_social_engineering=0.90 — consistent with the gate fix applied in plan 07a-01.
- Used `COLAB_VAL_SPLIT` variable (defined in Cell B) throughout cells F and G to avoid hardcoded paths — consistent with the configuration-in-one-place pattern established in Cell C.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added gitignore negation to allow tracking notebooks/H100fixedv5.ipynb**
- **Found during:** Task 1 (notebook commit)
- **Issue:** `.gitignore` contains `*.ipynb` on line 141, which caused git to ignore `notebooks/H100fixedv5.ipynb` entirely. The file could not be staged or committed without overriding this rule.
- **Fix:** Added `!notebooks/*.ipynb` negation line immediately after `*.ipynb` in `.gitignore`. This allows all files under `notebooks/` with `.ipynb` extension to be tracked while keeping the general ignore rule for other locations.
- **Files modified:** `.gitignore`
- **Verification:** `git status` showed `?? notebooks/H100fixedv5.ipynb` after the edit, confirming the negation took effect.
- **Committed in:** `e556084` (same commit as the notebook)

---

**Total deviations:** 1 auto-fixed (1 blocking — gitignore rule prevented commit)
**Impact on plan:** Fix was required for correctness; without it the primary deliverable could not be committed. No scope creep.

## Issues Encountered

- The notebook file `notebooks/H100fixedv5.ipynb` was only present in the main project working directory, not in the git worktree. The file was first modified in the main project dir, then copied into the worktree's notebooks/ directory before staging. This is expected behavior for worktrees that start from a branch where the file was never committed.
- The worktree had an empty `notebooks/.gitkeep` — the notebook is now the first real file in that directory tracked by git.

## Known Stubs

- `REPO_URL = "https://github.com/YOUR_ORG/YOUR_REPO.git"` in Cell B — operator must replace with the actual repository URL before cloning. This is intentional and clearly labeled in a comment. The cell raises `RuntimeError` with a clear message if the clone fails.

## Threat Flags

None — no new network endpoints, auth paths, file access patterns, or schema changes introduced. The notebook cells operate within the Colab filesystem (/content/) and the existing HuggingFace Hub download pattern.

## Next Phase Readiness

- Notebook is ready for the operator's H100 Colab session workflow (plan 07a-03: run generation, rebuild splits locally, upload splits to Colab, run training section cells)
- Plan 07a-03 (evaluate-release-split re-run and final release-eval) can proceed after the adapter is downloaded locally and registered in the off-repo model registry

---
*Phase: 07a-task-scam-recall-recovery*
*Completed: 2026-05-28*

## Self-Check: PASSED

- [x] `notebooks/H100fixedv5.ipynb` exists in worktree: FOUND
- [x] `.gitignore` modified with negation: FOUND
- [x] Commit e556084 exists: FOUND
- [x] Verification command output: PASS (all 8 checks True)
- [x] SUMMARY.md created at correct path
