---
phase: 40-multi-model-training-evidence
fixed_at: 2026-08-26T03:31:29Z
review_path: .planning/phases/40-multi-model-training-evidence/40-REVIEW.md
iteration: 1
findings_in_scope: 6
fixed: 6
skipped: 0
status: all_fixed
---

# Phase 40: Code Review Fix Report

**Fixed at:** 2026-08-26T03:31:29Z  
**Source review:** `.planning/phases/40-multi-model-training-evidence/40-REVIEW.md`  
**Iteration:** 1

**Summary:**

- Findings in scope: 6
- Fixed: 6
- Skipped: 0

## Fixed Issues

### CR-01: The generated review manifest is rejected by the Phase 41 handoff

**Files modified:** `src/model_adaptation/phase40_review.py`, `src/model_adaptation/phase41_evaluation.py`, `tests/model_adaptation/test_phase40_review.py`, `tests/model_adaptation/test_phase41_protocols.py`, `data/models/phase40/review/human-review-manifest.json`  
**Commits:** `d82dbdb`, `973a7e4`, `28e4cb3`  
**Applied fix:** Added the strict v3 closure contract and exact v2 compatibility branch, bound the new lineage fields through Phase 41, added integration coverage, and migrated the real manifest. Fixed; logic and the real replay received human-verifiable evidence in the tests and artifact hashes.

### CR-02: Queue verification accepts duplicate-key and noncanonical comparison JSON

**Files modified:** `src/model_adaptation/cli.py`, `src/model_adaptation/phase40_review.py`, `tests/model_adaptation/test_cli.py`  
**Commits:** `19c56e4`, `37e308e`  
**Applied fix:** Stable-read the code-fixed comparison authority, reject duplicate keys and partial reads, validate its typed structure, and require byte-exact canonical serialization before either schema branch succeeds. Command-level malformed-input tests now prove the CLI does not print success.

### CR-03: Review verification and publication accept redirected artifact paths

**Files modified:** `src/model_adaptation/cli.py`, `src/model_adaptation/phase40_review.py`, `src/model_adaptation/phase41_evaluation.py`, `tests/model_adaptation/test_cli.py`, `tests/model_adaptation/test_phase40_review.py`, `tests/model_adaptation/test_phase41_protocols.py`  
**Commits:** `f5b7a8c`, `e4d474b`, `542d7eb`  
**Applied fix:** Bound every authority and output to its fixed repository-relative location; rejected symlink, junction/reparse, hard-link, and identity-drift cases; and made the Phase 41 manifest read stable. Redirect tests cover write, verify-only, and downstream ingestion. Fixed; path-identity logic requires human verification alongside the platform tests.

### CR-04: Three-file publication can persist a manifest for an incomplete closure

**Files modified:** `src/model_adaptation/phase40_review.py`, `tests/model_adaptation/test_phase40_review.py`  
**Commits:** `801e713`, `311dc65`  
**Applied fix:** Preflighted all destinations, staged and verified all payloads, promoted notes and report first, and published the authoritative manifest last. Downstream ingestion rehashes the reviewer return, notes, and report. Failure injection at each promotion proves no partial completion marker survives and retry remains possible. Fixed; transactional promotion logic requires human verification alongside these tests.

### WR-01: Unreadable reviewer input escapes the controlled CLI error path

**Files modified:** `src/model_adaptation/cli.py`, `src/model_adaptation/phase40_review.py`, `tests/model_adaptation/test_cli.py`  
**Commits:** `6ec4b52`, `1e1bd00`, `20101a6`  
**Applied fix:** Routed reviewer reads through the hardened loader, translated unsafe/unreadable input to path-free errors, hid malformed-input absolute paths, and made successful output use stable ASCII repository-relative paths so a Unicode Windows checkout cannot fail after publication.

### WR-02: New tests mock away the v3 finalizer and downstream contract

**Files modified:** `tests/model_adaptation/test_phase40_review.py`, `tests/model_adaptation/test_phase41_protocols.py`, `tests/model_adaptation/test_cli.py`  
**Commits:** `973a7e4`, `37e308e`, `542d7eb`  
**Applied fix:** Added real v3 finalization and verify-only replay, exact v2 compatibility, Phase 41 ingestion, row-integrity failures, malformed comparison documents, redirected paths, and per-promotion failure coverage. Only the expensive frozen model-bundle revalidation is replaced by a fixture boundary.

## Verification

- Isolated review-fix worktree: 118 core focused tests passed; 7 additional boundary tests passed.
- Main checkout after integration: 132 focused Phase 40/41 tests passed.
- Main checkout after integration: all `tests/model_adaptation` tests passed (`866 passed`, 2 third-party SWIG deprecation warnings).
- Main checkout after the Windows console fix: `tests/model_adaptation/test_cli.py` passed (`27 passed`).
- Main checkout real closure: the exact documented finalizer completed in `--verify-only` mode without writes.
- OneDrive publication hard-link smoke test passed (`1 passed`).
- Reserved Phase 41 held-out data was not opened, enumerated, statted, or hashed during this fix run.

## Final Artifact Identities

- `reviewer-return.jsonl`: `96ff351e03ba7fee37fef09c1660372dd9ab36a289d8171ffb06893650692074` (62,558 bytes; unchanged)
- `human-review-notes.jsonl`: `64af30d056a4ad3639f05886b0c750d3490421e956ec41291cd406ab2f01e2cf` (62,501 bytes; unchanged)
- `human-review-report.md`: `f4bfac796363e8d43ea55b6fd3415c020cb95c06a712f7aab46b455d8f9e4ae0` (62,014 bytes; unchanged)
- `human-review-manifest.json`: `73895a3b44aaa90c77329f62ccdbc4db6e4d2552c887ee9d3b9b5460d0494bf9` (43,934 bytes; v3)

---

_Fixed: 2026-08-26T03:31:29Z_  
_Fixer: the agent (gsd-code-fixer)_  
_Iteration: 1_
