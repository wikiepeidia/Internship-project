---
phase: 40-multi-model-training-evidence
reviewed: 2026-08-26T02:57:12Z
depth: deep
files_reviewed: 7
files_reviewed_list:
  - src/model_adaptation/phase40_review.py
  - src/model_adaptation/cli.py
  - tests/model_adaptation/test_cli.py
  - tests/model_adaptation/test_phase40_final_authority.py
  - data/models/phase40/review/human-review-manifest.json
  - data/models/phase40/review/human-review-notes.jsonl
  - data/models/phase40/review/human-review-report.md
findings:
  critical: 4
  warning: 2
  info: 0
  total: 6
status: resolved
---

# Phase 40: Code Review Report

**Reviewed:** 2026-08-26T02:57:12Z  
**Depth:** deep  
**Files Reviewed:** 7  
**Status:** resolved

## Summary

The initial Plan 06 review confirmed byte-identical Plan 05 artifacts and exact 52-row coverage, then found six release-blocking or warning-level boundaries in schema handoff, canonical parsing, path identity, transactional publication, error handling, and integration coverage. All six are now resolved; the original findings remain below as audit history and the final **Resolution** section records the fixes, tests, and real v3 replay.

Plan 05's frozen authority, comparison manifest/report, launch receipts, prediction bundles, and runtime receipts have no Git diff from `e59fdaa`; the frozen source-tree identity remains `520aeb6a58276750c3dd37be1e9ee6983fdd7f6c807c24332625020ec0334cc2`.

## Narrative Findings (AI reviewer)

## Critical Issues

### CR-01: The generated review manifest is rejected by the Phase 41 handoff

**File:** `C:\Users\wikiepeidia\OneDrive - caugiay.edu.vn\bài tập\usth\GEN14\INTERNSHIP\Internship-project\src\model_adaptation\phase40_review.py:552-586`  
**Cross-module boundary:** `C:\Users\wikiepeidia\OneDrive - caugiay.edu.vn\bài tập\usth\GEN14\INTERNSHIP\Internship-project\src\model_adaptation\phase41_evaluation.py:4704-4748`

**Issue:** The v3-backed finalizer adds `superseded_scope_amendment_sha256` and `final_comparison_authority_sha256`, but still labels the artifact `phase40-human-review-v2`. The committed real manifest contains both fields. Phase 41 requires an exact older v2 field set and rejects any extra key at line 4736, so the real Phase 40 closure cannot advance through `prepare_phase41_from_canonical_authorities`.

**Fix:** Introduce `phase40-human-review-v3` with both lineage fields required. Update the Phase 41 loader to branch strictly by schema: retain the exact historical v2 contract, and for v3 require both new fields and bind them to the v3 comparison manifest. Add an integration test that passes the actual v3 review-manifest shape through the Phase 41 closure loader.

### CR-02: Queue verification accepts duplicate-key and noncanonical comparison JSON

**File:** `C:\Users\wikiepeidia\OneDrive - caugiay.edu.vn\bài tập\usth\GEN14\INTERNSHIP\Internship-project\src\model_adaptation\cli.py:955-957`  
**Affected success path:** `C:\Users\wikiepeidia\OneDrive - caugiay.edu.vn\bài tập\usth\GEN14\INTERNSHIP\Internship-project\src\model_adaptation\cli.py:1007-1013`

**Issue:** `_load_phase40_review_authorities` calls Pydantic's `model_validate_json()` directly. That parser accepts duplicate object keys with last-value-wins semantics and does not require the bytes to equal canonical JSON. The queue-only command never reaches the stricter parser in `finalize_phase40_human_review`, so it can print a successful authority verification for a byte-mutated or ambiguous comparison document.

**Fix:** Read the comparison bytes once through a hardened regular-file loader, parse with the existing duplicate-key-rejecting strict JSON hook, validate the typed model, and require exact equality with canonical serialized bytes before selecting either the v2 or v3 authority branch. Add duplicate-key, whitespace/noncanonical, and partial-file negative tests against `phase40-verify-review-queue` itself.

### CR-03: Review verification and publication accept redirected artifact paths

**File:** `C:\Users\wikiepeidia\OneDrive - caugiay.edu.vn\bài tập\usth\GEN14\INTERNSHIP\Internship-project\src\model_adaptation\phase40_review.py:377-382,460-469,521-530,588-605`  
**Related input path:** `C:\Users\wikiepeidia\OneDrive - caugiay.edu.vn\bài tập\usth\GEN14\INTERNSHIP\Internship-project\src\model_adaptation\cli.py:1021-1025`

**Issue:** Comparison, queue-manifest, reviewer-return, and output paths are opened without rejecting symlink/junction/reparse ancestry. In `verify_only`, `is_file()` plus `read_bytes()` follows a symlink leaf, so byte-identical files outside the intended authority root are accepted under an authoritative repository path. Normal publication rejects an existing symlink leaf but still follows a redirected parent when creating temporary files. This violates the fixed local artifact boundary and permits misleading verification or writes outside the requested tree.

**Fix:** Resolve every review input/output against the trusted lexical repository root, require the fixed canonical Phase 40 relative path where the workflow defines one, and call `_reject_redirecting_path_components` before every read or write. Require non-symlink regular leaves, reject reparse ancestry and unexpected link counts where supported, and recheck the held file identity after reading. Cover leaf symlinks and ancestor junctions in both write and verify-only tests.

### CR-04: Three-file publication can persist a manifest for an incomplete closure

**File:** `C:\Users\wikiepeidia\OneDrive - caugiay.edu.vn\bài tập\usth\GEN14\INTERNSHIP\Internship-project\src\model_adaptation\phase40_review.py:594-605`

**Issue:** Notes, manifest, and report are written sequentially, with the manifest written before the report. If the report destination is conflicting, redirected, read-only, or otherwise fails, the function returns an error after already persisting a manifest that claims the report hash. The downstream Phase 41 loader currently validates hash strings in the manifest but does not re-open the notes/report files, so a partial publication can be mistaken for a complete human-review closure once CR-01 is repaired.

**Fix:** Preflight all destinations before changing any path, stage and verify all payloads in a non-redirecting directory, and publish a completion manifest only after notes and report are durably in place. Make downstream consumption rehash the reviewer return, notes, and report against the manifest. A failure-injection test at each promotion step must prove that no authoritative completion marker remains for a partial set.

## Warnings

### WR-01: Unreadable reviewer input escapes the controlled CLI error path

**File:** `C:\Users\wikiepeidia\OneDrive - caugiay.edu.vn\bài tập\usth\GEN14\INTERNSHIP\Internship-project\src\model_adaptation\cli.py:1021`

**Issue:** `reviewer_return_path.read_bytes()` is not wrapped, while `main()` only catches `RuntimeError`, `ValueError`, and `FileNotFoundError`. `PermissionError`, `IsADirectoryError`, and other `OSError` cases therefore emit an uncontrolled traceback and may disclose a personal absolute path.

**Fix:** Use the same hardened regular-file loader as the other review inputs, translate `OSError` into a concise `ValueError`, and avoid echoing an untrusted absolute path in the public error.

### WR-02: New tests mock away the v3 finalizer and downstream contract

**File:** `C:\Users\wikiepeidia\OneDrive - caugiay.edu.vn\bài tập\usth\GEN14\INTERNSHIP\Internship-project\tests\model_adaptation\test_cli.py:182-268`  
**Related coverage:** `C:\Users\wikiepeidia\OneDrive - caugiay.edu.vn\bài tập\usth\GEN14\INTERNSHIP\Internship-project\tests\model_adaptation\test_phase40_final_authority.py:192-243`

**Issue:** The CLI test replaces every new authority function and only checks call routing; the authority tests cover source drift and one decoy scope path but never run real v3 human finalization, artifact publication, verify-only, or Phase 41 consumption. This is why all tests pass while CR-01 through CR-04 remain reachable.

**Fix:** Add end-to-end fixture coverage for one complete v3 review closure, exact v2 compatibility, v3-to-Phase-41 ingestion, duplicate comparison keys, noncanonical bytes, missing/duplicate/reordered review rows, redirected inputs/outputs, and injected multi-file publication failures.

## Resolution

All six findings were resolved on 2026-08-26. The final implementation:

- versions and consumes an exact `phase40-human-review-v3` closure while retaining exact historical v2 compatibility;
- strictly parses canonical, duplicate-free comparison JSON;
- binds all review inputs and outputs to code-fixed regular files with redirect and identity-drift defenses;
- stages all output payloads and publishes the completion manifest last;
- sanitizes reviewer-input failures and emits path-independent, Windows-console-safe success output; and
- exercises real v3 finalization, replay, Phase 41 ingestion, malformed inputs, redirects, and every publication-failure boundary.

The real 52-row review closure was migrated and replayed in `--verify-only` mode. The reviewer return remained byte-identical at SHA-256 `96ff351e03ba7fee37fef09c1660372dd9ab36a289d8171ffb06893650692074`; notes and report hashes were unchanged. The v3 manifest SHA-256 is `73895a3b44aaa90c77329f62ccdbc4db6e4d2552c887ee9d3b9b5460d0494bf9`.

Verification passed in the main checkout: 132 focused Phase 40/41 tests and all 866 `tests/model_adaptation` tests. See `40-REVIEW-FIX.md` for the atomic commit map and exact verification record.

---

_Reviewed: 2026-08-26T02:57:12Z_  
_Reviewer: the agent (gsd-code-reviewer)_  
_Depth: deep_
