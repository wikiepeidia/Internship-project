---
phase: "07a"
plan: "01"
subsystem: "release-gate + data-generation"
tags: [gate-bug-fix, recall-floor, task-scam, prompt-enrichment, regression-tests]
dependency_graph:
  requires:
    - "src/model_adaptation/release_evaluation.py"
    - "src/model_adaptation/schemas.py (HeldOutSupportAudit)"
    - "src/data_pipeline/generation/prompts.py"
  provides:
    - "Correct per-label recall floor gate in evaluate-release-split"
    - "Enriched task_scam generation prompts with five scenario axes"
  affects:
    - "All future evaluate-release-split runs (snapshot.audit.verdict now reflects recall)"
    - "All future task_scam data generation via build_bulk_prompt and build_complex_prompt"
tech_stack:
  added: []
  patterns:
    - "Post-evaluation audit augmentation pattern: rebuild HeldOutSupportAudit after metrics computed"
    - "Conditional prompt injection: task_scam-specific block only when threat_class matches"
key_files:
  created: []
  modified:
    - "src/model_adaptation/release_evaluation.py"
    - "src/data_pipeline/generation/prompts.py"
    - "tests/model_adaptation/test_release_evaluation.py"
decisions:
  - "Rebuild HeldOutSupportAudit after metrics are computed rather than mutating it in place; pydantic model_validator enforces ready/verdict alignment automatically"
  - "Return the original audit unchanged (is-identity) when no recall floors are breached, avoiding unnecessary object allocation"
  - "Inject task_scam diversity block as conditional suffix in existing prompt functions rather than adding separate task_scam-specific functions, keeping the API surface minimal"
metrics:
  duration: "~15 minutes"
  completed: "2026-05-28"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 3
  tests_added: 4
  tests_total_passing: 256
---

# Phase 7a Plan 01: Gate Bug Fix and task_scam Prompt Enrichment Summary

Recall floor enforcement added to `_build_snapshot` so `snapshot.audit.verdict` correctly shows BLOCK when any risky label recall is below its floor; task_scam generation prompts enriched with five explicit scenario axes and social-engineering pattern requirements.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Gate bug fix + regression tests | 3055b68 | `src/model_adaptation/release_evaluation.py`, `tests/model_adaptation/test_release_evaluation.py` |
| 2 | task_scam prompt enrichment | 3dc8ff8 | `src/data_pipeline/generation/prompts.py` |

## What Was Built

### Task 1: Gate Bug Fix

**Bug:** `snapshot.audit.ready = True` and `snapshot.audit.verdict = "PASS"` even when `task_scam` recall was 0.44. The `HeldOutSupportAudit` was finalized at support-check time (before any evaluation rows existed), so recall information was never incorporated into the audit object stored in the snapshot.

**Root cause:** `_build_snapshot` in `release_evaluation.py` passed the original pre-evaluation `audit` directly into the `ReleaseEvaluationSnapshot` without checking the per-label recall metrics that had just been computed.

**Fix:** Added `_apply_recall_floor_to_audit(audit, per_label_metrics)` helper that:
1. Iterates over `per_label_metrics` entries where `recall_floor_applies=True`
2. Skips zero-support entries (already covered by the support audit)
3. Appends a blocker reason for each risky label whose recall is below `audit.risky_recall_floor`
4. If any extra blockers were found, rebuilds the `HeldOutSupportAudit` with the combined blocker list (the pydantic `model_validator` then automatically sets `ready=False` and `verdict="BLOCK"`)
5. Returns the original audit unchanged (identity) if no recall floors were breached

Called from `_build_snapshot` so every snapshot write (including intermediate checkpoints) reflects the correct gate status based on metrics computed at that point.

**Tests added (4 new, all pass):**
- `test_gate_blocks_when_task_scam_recall_is_below_floor` — integration test: evaluate_release_split with fake analyzer that mispredicts task_scam as benign; asserts `snapshot.audit.verdict == "BLOCK"` and blocker names the label
- `test_gate_passes_when_all_risky_labels_meet_recall_floor` — integration test: perfect analyzer; asserts `snapshot.audit.verdict == "PASS"` and `blocker_reasons == []`
- `test_apply_recall_floor_to_audit_adds_blocker_for_failing_label` — unit test on the helper; feeds recall=0.44 for task_scam, asserts BLOCK verdict and blocker containing "task_scam" and "0.44"
- `test_apply_recall_floor_to_audit_returns_unchanged_audit_when_all_floors_met` — unit test on the helper; feeds all recalls above 0.90 floor, asserts returned object is identical to input (identity)

**Total test suite: 256 passed.**

### Task 2: task_scam Prompt Enrichment

**Change:** Added `_TASK_SCAM_SCENARIO_AXES` constant and `_build_task_scam_diversity_block` helper in `prompts.py`. Both `build_bulk_prompt` and `build_complex_prompt` now inject the diversity block as a conditional suffix when `threat_class == "task_scam"`.

**Five scenario axes defined:**
1. **Like/follow/comment farms** — TikTok/Facebook/YouTube per-task pay that never arrives
2. **Shopee/Lazada review-bombing** — buy-and-review with promised cashback refund that is never returned
3. **Crypto referral schemes** — fake platform registration; withdrawals blocked until "verification fees" paid
4. **Fake purchase seeding** — ghost orders to inflate sales rankings; commission delayed indefinitely
5. **Zalo/Telegram livestream engagement** — staged task series where the final large task requires an "account upgrade fee"

**Social-engineering structure requirements added:**
- Trust-then-disappear: small payments first to build trust, then disappear after larger task or deposit
- Advance-payment: activation/registration/upgrade fee always lost

**Platform names named explicitly:** TikTok, Shopee, Lazada, Binance, Zalo, Telegram

**Isolation confirmed:** Non-task_scam classes (`bank_impersonation`, `benign`, etc.) receive no bleed-through from the task_scam block — verified by sanity checks and existing prompt tests.

## Deviations from Plan

None. The plan was inferred from the phase CONTEXT.md (no 07a-01-PLAN.md existed on any branch). Both tasks align exactly with D-11/D-12 (gate bug) and D-06 (prompt enrichment) from the context decisions.

## Known Stubs

None. Both changes are fully wired:
- The gate fix activates on every call to `evaluate_release_split` / `_build_snapshot`
- The prompt enrichment activates on every `build_bulk_prompt` / `build_complex_prompt` call with `threat_class="task_scam"`

## Threat Flags

None. No new network endpoints, auth paths, file access patterns, or schema changes were introduced.

## Self-Check: PASSED

- `src/model_adaptation/release_evaluation.py` — modified, present
- `src/data_pipeline/generation/prompts.py` — modified, present
- `tests/model_adaptation/test_release_evaluation.py` — modified, present
- Commit 3055b68 — verified in git log
- Commit 3dc8ff8 — verified in git log
- 256 tests pass
