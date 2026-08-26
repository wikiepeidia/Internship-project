---
phase: 41-one-shot-two-model-evaluation
reviewed: 2026-08-26T15:14:10Z
depth: deep
files_reviewed: 16
files_reviewed_list:
  - scripts/phase41_one_shot_launcher.ps1
  - src/data_pipeline/judge_merge.py
  - src/model_adaptation/cli.py
  - src/model_adaptation/phase40_release_authorities.py
  - src/model_adaptation/phase41_evaluation.py
  - src/model_adaptation/phase41_protocols.py
  - src/model_adaptation/release_evaluation.py
  - tests/data_pipeline/test_apply_mislabel_triage.py
  - tests/model_adaptation/test_cli.py
  - tests/model_adaptation/test_phase40_release_authorities.py
  - tests/model_adaptation/test_phase41_evaluation.py
  - tests/model_adaptation/test_phase41_launcher.py
  - tests/model_adaptation/test_phase41_protocols.py
  - tests/model_adaptation/test_release_evaluation.py
  - data/models/phase41/failed-invocation/25de74c1e779bab818433930fc14a71ccef7886f05e913b472cbbbf060a7dc9c/claim-capable-preclaim-failure.json
  - data/models/phase41/failed-invocation/28374ea5c1f7fee43e12ee0395ad4fcd7c6a2e4801b809131afa6cca2db7e8e7/claim-capable-preclaim-failure.json
findings:
  critical: 2
  warning: 2
  info: 0
  total: 4
status: resolved_with_external_erratum
resolved: 2026-08-26T15:27:19Z
resolution: .planning/phases/41-one-shot-two-model-evaluation/41-REVIEW-RESOLUTION.md
erratum: data/models/phase41/phase41-provenance-erratum.json
---

# Phase 41: Code Review Report

**Reviewed:** 2026-08-26T15:14:10Z  
**Depth:** deep  
**Files Reviewed:** 16  
**Status:** resolved_with_external_erratum  
**Verdict:** RELEASE REMEDIATION PASSED. CR-01/CR-02 and WR-01 are fixed in code and safe tests; WR-02 is explicitly disambiguated in the mandatory external erratum because the sealed terminal export cannot be altered. The terminal model results were not rerun.

## Resolution

All four findings are mapped to fixes and safe verification in `41-REVIEW-RESOLUTION.md`. The mandatory non-sealed companion is `data/models/phase41/phase41-provenance-erratum.json` (SHA-256 `c7be74346f0e217c382e556fbf0a730cb33be50356d4155356a5b024871a1672`). The frozen export tree object remains `df5ae00a1ad5d7400c084e8a19280fb660d1fd96`; no prediction, metric, receipt, or sealed manifest was modified.

## Narrative Findings (AI reviewer)

## Summary

The protected launcher, durable global claim/completion records, claim-before-open implementation, captured-callable validation, model/source/lease binding, scoped delegation checks, prediction evidence, and terminal metrics were traced across the committed Phase 41 source. The committed verified export was also checked independently: all 16 receipt-listed artifacts match their recorded sizes and SHA-256 values, each prediction file contains 220 rows, and metrics recomputed from those prediction artifacts agree with the result records. No model or evaluation command was invoked during this review, and the reserved split or its containing directory was not accessed.

The statistical evaluation remains a single terminal model pass. However, the stronger claim that the held-out file had zero pre-launch access is disproved by a regression test that parsed, statted, and hashed every live split before the launcher, followed by another read after the run. Separately, the verified-export CLI mutates successfully and then reports failure on the repository's Unicode Windows path. Those are current blockers. The five recorded pre-claim launcher failures are distinguished below: their own artifacts consistently record no global/local claim, no evaluation access, and no held-out spend; they are historical fail-closed attempts, not the live defects reported here.

## Critical Issues

### CR-01: Regression validation accessed the held-out split outside the one-shot launcher

**Classification:** BLOCKER  
**Files:** `tests/data_pipeline/test_apply_mislabel_triage.py:913-925`; `src/data_pipeline/judge_merge.py:3162-3197`; `src/data_pipeline/judge_merge.py:3253-3269`; `.planning/phases/41-one-shot-two-model-evaluation/41-02-SUMMARY.md:97-105`; `src/model_adaptation/phase41_evaluation.py:3608-3663`

**Issue:** `test_downstream_contract_matches_live_manifest_and_active_planning_regions` passes the live `data/splits` directory to `validate_downstream_data_contract`. That validator calls `render_downstream_data_contract`, which calls `load_source_splits`, then reads label rows, stats each file, and hashes each file for all split names, including `test`. The Phase 41 summary establishes the chronology: the full suite was run before the one-shot launcher, and this same planning-label test was rerun after its assertion-only repair. Therefore automated regression code parsed/hashed the held-out file before the launcher and reread it after evaluation. It was not used for model tuning, selection, inference, or human inspection, but it directly contradicts the absolute statements that reserved-split access had not been attempted and that the launcher was the only opener. The preauthorization field `reserved_split_access_attempted: False` is a self-assertion and cannot detect this external read.

This does **not** invalidate the measured one-pass model metrics or prove leakage into model decisions. It does invalidate the zero-filesystem-access provenance claim and any report language describing the test split as wholly untouched until the one-shot launcher.

**Fix:**

1. Split downstream validation into a metadata-only planning validator and an explicitly data-touching integrity validator. Phase 41 preauthorization/default regression suites must consume only the committed manifest/contract metadata and must not accept a live split directory.
2. Mark the data-touching validator test as an explicit integration/audit test excluded from all preauthorization and one-shot-safe test commands. Add a sentinel test that supplies a trap path and proves the Phase 41-safe suite cannot open, parse, stat, enumerate, or hash any split file.
3. Preserve the immutable terminal results and do not rerun evaluation. Add a corrective audit record that discloses one pre-launch automated parse/stat/hash and one post-run automated reread, while stating accurately that neither influenced model training, tuning, selection, or inference.
4. Correct Phase 41/42/report language and generated evidence fields so they claim one terminal **model evaluation pass**, not zero prior filesystem access. A future run may set `reserved_split_access_attempted` only from an enforceable access boundary or external access audit, not an unconditional literal.

### CR-02: Unicode console output turns a completed export into a reported failure

**Classification:** BLOCKER  
**Files:** `src/model_adaptation/cli.py:1272-1282`; `src/model_adaptation/cli.py:1296-1306`; `.planning/phases/41-one-shot-two-model-evaluation/41-02-SUMMARY.md:99`

**Issue:** `handle_phase41_export_evidence` completes the copy and writes the receipt before interpolating the destination `Path` into a normal `print`. On the actual Windows legacy console, the Vietnamese characters in the repository path caused a `charmap` encoding failure after the successful mutation. `main` catches that `UnicodeEncodeError` through `ValueError` and returns exit code 1. The operator therefore receives a failure status even though the final export exists and is complete; an automated retry then fails because the immutable destination already exists. This violates reliable exactly-once operator semantics and makes successful evidence delivery indistinguishable from failure at the CLI boundary.

**Fix:** Emit paths through a console-safe output helper (UTF-8 where supported, otherwise `backslashreplace`/ASCII-safe representation) and make the error channel use the same helper. Add a Windows regression test with strict CP-1252-like stdout and a non-encodable repository path. The handler must return 0 after a completed export and its receipt must remain verifiable; console rendering must never change command success.

## Warnings

### WR-01: Failed export copies leave an unrecoverable partial final destination

**Classification:** WARNING  
**Files:** `src/model_adaptation/phase41_evaluation.py:5255-5306`; `tests/model_adaptation/test_phase41_evaluation.py:1315-1367`

**Issue:** Export creates the final immutable destination before copying artifacts. Any exception after `mkdir` leaves a partial final tree, while every later call rejects that tree solely because it exists. The corruption test confirms only that the receipt is absent; it neither requires cleanup nor proves a safe retry. A transient I/O error can therefore permanently block export even though the authoritative operational evidence remains valid.

**Fix:** Copy into a unique sibling staging directory, verify all bytes/hashes and write the receipt there, then atomically rename the complete directory to the final manifest-hash destination. Clean only the uniquely created staging directory on failure. Alternatively, implement a strictly hash-verified resume path that accepts no mismatching pre-existing bytes.

### WR-02: The canonical preauthorization conflates two different pre-claim failures

**Classification:** WARNING  
**Files:** `src/model_adaptation/phase41_evaluation.py:96-112`; `src/model_adaptation/phase41_evaluation.py:167-174`; `src/model_adaptation/phase41_evaluation.py:3608-3659`; `src/model_adaptation/phase41_evaluation.py:3913-3953`; `src/model_adaptation/phase41_evaluation.py:5811-5903`; `data/models/phase41/failed-invocation/25de74c1e779bab818433930fc14a71ccef7886f05e913b472cbbbf060a7dc9c/claim-capable-preclaim-failure.json:1`; `data/models/phase41/failed-invocation/28374ea5c1f7fee43e12ee0395ad4fcd7c6a2e4801b809131afa6cca2db7e8e7/claim-capable-preclaim-failure.json:1`

**Issue:** The sole authority field and receipt member are named `captured_helper_preclaim_failure_audit`, but the code-fixed path and validator actually require the later `phase41-qwen-lease-preclaim-failure-v1` artifact with failure stage `staged_production_qwen_lease_identity`. The earlier, distinct `phase41-captured-helper-preclaim-failure-v1` artifact at `25de74...` is committed and records a fail-closed captured-helper identity rejection, but it is not independently hash-bound into the canonical final preauthorization/export chain. As a result, the summary's five-failure history is preserved in repository side artifacts but not completely or unambiguously authenticated by the canonical receipt.

The two audited failures themselves are not live execution defects: both inspected records report no claim, no evaluation access, and no held-out spend. The defect is the conflated name and missing independent binding.

**Fix:** Introduce distinct `captured_helper_identity_preclaim_failure_audit_sha256` and `model_lease_preclaim_failure_audit_sha256` fields, validate each artifact against its own schema/stage/meaning, embed both records in preauthorization, and include both (or a hash-bound audit index covering both) in the verified export. Do not rename one failure type to stand for the other.

## Historical Zero-Access Failures (Not Findings)

The following five superseded attempts were separately recorded as failing before a claim or evaluation access: repository reparse ancestry, staged loader source-location identity, missing explicit `OutputRoot`, captured-helper identity, and model/base-lease identity. Their fail-closed behavior should remain in the report as implementation/audit history. They do not excuse or cause CR-01, which came from an unrelated regression-test call path outside the launcher.

## Required Disposition

- Do not rerun either model and do not alter the frozen prediction or metric artifacts.
- Fix the regression-suite access boundary and Unicode CLI behavior.
- Publish a corrective provenance disclosure for the automated pre-launch and post-run held-out reads.
- Repair the export transaction boundary and bind the two distinct pre-claim failure audits before calling the Phase 41 evidence package fully self-describing.

---

_Reviewed: 2026-08-26T15:14:10Z_  
_Reviewer: the agent (gsd-code-reviewer)_  
_Depth: deep_
