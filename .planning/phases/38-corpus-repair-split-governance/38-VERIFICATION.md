---
phase: 38-corpus-repair-split-governance
verified: 2026-08-08T00:00:00Z
status: passed
score: 5/5 must-haves verified
behavior_unverified: 0
overrides_applied: 0
---

# Phase 38: Corpus Repair & Split Governance Verification Report

**Phase Goal:** The synthetic corpus's structural bugs (seed concentration, invalid evidence spans, cross-split seed leakage) are repaired and re-split by seed-group hash against concrete, checkable acceptance gates, giving all downstream re-judging, training, and evaluation work a trustworthy foundation instead of open-ended cleanup.
**Verified:** 2026-08-08
**Status:** passed
**Re-verification:** No — initial verification

**Verified against:** `data/splits/phase38-corpus-repaired-v3/{train,val,test}.jsonl` and `data/manifests/manifest-phase38-corpus-repaired-v3.json` (per task instructions — v3, produced by the same-day quick task `260808-otp`, supersedes the phase's own `v2` output and is the corpus Phase 39/40 will actually consume). `v2` files remain on disk untouched, confirmed superseded in `38-02-SUMMARY.md`'s frontmatter callout.

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Pooled corpus is re-split by seed-group hash; zero `seed_id` appears in more than one of train/val/test.jsonl | VERIFIED | Independently parsed all 2,421 rows across the three real v3 files and computed `seed_id` sets per split: train∩val=0, train∩test=0, val∩test=0. Matches manifest's implicit claim and `260808-otp-SUMMARY.md`'s reported "Seed intersections: 0/0/0". |
| 2 | Largest single seed's share reduced from prior ~25% to a stated, justified cap, before/after recorded in manifest | VERIFIED | Independently recomputed per-seed row counts on the real files: max share is `seed_825b9e38d185` at 193/2421 = 7.9719% (< 8% cap). `manifest-phase38-corpus-repaired-v3.json`'s `repair_stats.seed_concentration_before/after` records three seeds trimmed from 8.07%/8.51%/10.18% down to 7.97% each. (v3's dominant-seed lineage differs from v2's 24.41% seed because that seed was entirely `zalo_social_engineering` and was removed/replaced by `260808-otp` — the "prior ~25%" reduction is traceable across `38-02-SUMMARY.md` → `260808-otp-SUMMARY.md` → this manifest, and the ≤8% cap invariant holds on the real, final corpus regardless of which seed is now largest.) |
| 3 | Zero rows in final corpus have invalid evidence spans | VERIFIED | Independently scanned all `suspicious_spans` entries across all 2,421 rows in the three real v3 files for exact-substring membership in `text`: 0 violations found. |
| 4 | Manifest records locked 80/10/10 split ratio and per-split, per-class row counts for all four labels | VERIFIED | `split_class_distribution` in the real manifest has all three split names, each with non-zero counts for all four labels (`bank_impersonation`, `zalo_social_engineering`, `task_scam`, `benign`) — independently recomputed from the real files and matches the manifest exactly, label-for-label, split-for-split. Actual ratio recomputed from real per-split record counts: 1918/2421=79.22%, 252/2421=10.41%, 251/2421=10.37% — within the 80/10/10 target at ≤1pp tolerance (test asserts this via `pytest.approx(..., abs=0.01)`). Minor note: the manifest records per-split row counts (ratio is derivable) rather than an explicit `target_ratio: [0.8,0.1,0.1]` key — not a gap against the roadmap wording, since the ratio is independently verifiable from the recorded counts, but noted as a nit. |
| 5 | A drafted task_scam 0.44→0.871 recovery narrative exists, grounded in real Phase 7a evidence artifacts | VERIFIED | `.planning/phases/38-corpus-repair-split-governance/38-recovery-narrative-task-scam.md` exists, all 6 required anchors present (0.44, 0.871, 62, 750, 400, `task-scam-recovery-2026-05-28`). Independently cross-checked every cited numeric claim against the real source files: `0.44`/`750`/gate-bug description confirmed in `07a-CONTEXT.md`; `audit.ready=true` despite floor breach confirmed in `07a-CONTEXT.md`/`07a-01-SUMMARY.md`; `0.871` recall / precision 1.000 / F1 0.931 / 62 examples confirmed verbatim in `documents/reports/latex/chapters/05_evaluation_and_discussion.tex` and `dataset_statistics.tex`; bank impersonation (0.862/1.000/0.926/56) and Zalo (1.000/0.987/0.993/75) cross-figures also confirmed verbatim. No invented numbers found. |

**Score:** 5/5 truths verified (0 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `data/splits/phase38-corpus-repaired-v3/train.jsonl` | 1,918 real repaired rows | VERIFIED | Line count matches manifest (1918); SHA-256 independently recomputed and matches manifest exactly (`ea5ef4e9...`) |
| `data/splits/phase38-corpus-repaired-v3/val.jsonl` | 252 real repaired rows | VERIFIED | Line count matches manifest (252); SHA-256 independently recomputed and matches (`6d51dbc2...`) |
| `data/splits/phase38-corpus-repaired-v3/test.jsonl` | 251 real repaired rows | VERIFIED | Line count matches manifest (251); SHA-256 independently recomputed and matches (`1dfcfab9...`) |
| `data/manifests/manifest-phase38-corpus-repaired-v3.json` | manifest recording ratio, per-split per-class counts, repair_stats | VERIFIED | Exists, all fields cross-checked against real split files and matched exactly |
| `.planning/phases/38-corpus-repair-split-governance/38-recovery-narrative-task-scam.md` | evidence-cited recovery narrative | VERIFIED | Exists, all citations independently traced to real source files and confirmed accurate |
| `src/data_pipeline/repair_corpus_split_governance.py` | pipeline module (pool/repair/cap/split/manifest + CLI) | VERIFIED | Exists, imports `_stable_bucket`/`lexical_dedup` as required, 161/161 `tests/data_pipeline/` tests pass |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `repair_corpus_split_governance.py` | `processing/splitter.py` | imports `_stable_bucket` | VERIFIED | Confirmed present, reused not reimplemented (per 38-01-SUMMARY and code review) |
| `repair_corpus_split_governance.py` | `processing/dedup.py` | imports `lexical_dedup` | VERIFIED | Confirmed present, spy-tested in 38-01's test suite |
| `repair_corpus_split_governance.py` | `versioning/manifest.py` | calls `build_manifest()` | VERIFIED | Confirmed via manifest's `"manifest"` sub-object matching `build_manifest()`'s SHA-256/records/bytes shape |
| Old lineage (`recovered-balanced.jsonl`, `recovered-balanced/test.jsonl`) | v3 pipeline input | read-only, not overwritten | VERIFIED | Independently confirmed 3,000 and 413 lines respectively, unchanged (project's `data/` tree is gitignored by convention, so this was confirmed by direct line-count re-check rather than `git diff`) |
| Bugfix commit `9577394` | v3 on-disk files | must NOT have altered v3 | VERIFIED | v3 files' mtimes (2026-08-08T19:06:01+07:00) predate commit `9577394` (2026-08-08T20:47:40+07:00); v3 was produced at commit `8b5336c`, which the fix commit is chronologically after. The fix diff only touches `validate_replacement_records`'s empty-span branch (benign-label path, never exercised by the zalo-label v3 run) and makes the dedup gate unconditional (already ran for v3 since `--replacement-input` was supplied) — both dormant-for-v3 as the review claimed. |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full data_pipeline test suite passes (no regressions after the post-review bugfix) | `python -m pytest tests/data_pipeline/ -q` | 161 passed | PASS |
| Phase 38 + 260808-otp specific test files pass | `python -m pytest tests/data_pipeline/test_repair_corpus_split_governance.py tests/data_pipeline/test_repair_corpus_full_scale.py tests/data_pipeline/test_zalo_codex_recovery.py -q` | 32 passed | PASS |
| Zero cross-split seed_id leakage (independent, not the project's own test) | inline Python script reading all 3 real files | 0/0/0 intersections | PASS |
| Zero invalid evidence spans (independent, not the project's own test) | inline Python script checking exact-substring membership | 0 violations across 2,421 rows | PASS |
| Manifest SHA-256/record counts match real files (independent) | `hashlib.sha256` recompute on all 3 files | exact match on all 3 hashes + record counts + byte counts | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| DATA-04 | 38-01, 38-02 | Corpus pooled, repaired, re-split by seed-group hash, zero cross-split leakage | SATISFIED | Independent seed_id disjointness check on v3, 0/0/0 |
| DATA-05 | 38-01, 38-02 | Seed concentration capped at stated threshold, before/after recorded | SATISFIED | v3 manifest + independent recompute, max share 7.97% ≤ 8% |
| DATA-06 | 38-01, 38-02 | Zero rows with invalid evidence spans | SATISFIED | Independent full-corpus span scan, 0 violations |
| DATA-07 | 38-01, 38-02 | Split ratio locked, recorded in manifest with per-split class distribution | SATISFIED | Manifest + independent recompute match; ratio derivable within 1pp tolerance |
| DATA-08 | 38-02 | task_scam 0.44→0.871 recovery narrative, evidence-grounded | SATISFIED | Narrative file exists, every citation independently traced to real source |

Note: `.planning/REQUIREMENTS.md`'s "v7.0 Traceability" table (bottom section) still shows DATA-04 through DATA-08 as "Pending" even though the requirements checklist above it (line 641-645) already marks them `[x]`. This is a stale-table documentation inconsistency in REQUIREMENTS.md, not a corpus defect — flagged as an info-level nit, not a gap.

### Anti-Patterns Found

None. Grepped `repair_corpus_split_governance.py`, `zalo_codex_catalog.py`, `zalo_codex_recovery.py` for `TBD|FIXME|XXX|TODO|HACK|PLACEHOLDER` and "not yet implemented" style phrases — zero matches.

### Code Review Findings (context, not newly found by this verification)

`38-REVIEW.md` documents 2 critical bugs found in the shared pipeline code post-hoc, both fixed in commit `9577394`. Independently confirmed both bugs were on code paths dormant for the v3 run that's actually on disk (the `benign`-label empty-span branch never exercised by the zalo-label replacement run; the conditional-dedup gap only applicable when `--replacement-input` is absent, which wasn't the case for v3). File mtimes and commit ordering confirm v3 was not regenerated after the fix, so the shipped corpus is unaffected either way. 4 warnings + 3 info findings remain deliberately deferred (non-blocking per the review's own resolution) — these concern defensive hardening for *future* re-runs of this pipeline (e.g. small-corpus cap-floor edge case, weaker validation floor for non-zalo replacement labels), not defects in the delivered v3 corpus.

### Human Verification Required

None. This phase's deliverables are data artifacts (JSONL splits, a manifest, a markdown narrative) whose correctness is fully and independently checkable via file parsing, hashing, and text-content verification — no UI, real-time behavior, or subjective judgment call was required.

### Gaps Summary

No gaps. All 5 ROADMAP success criteria for Phase 38 are independently verified true against the real `phase38-corpus-repaired-v3` files on disk (not v2, not SUMMARY.md narrative). The corpus is seed-disjoint across splits, seed-concentration-capped below 8%, free of invalid evidence spans, manifest-documented with per-split per-class counts for all four labels (improving on v2's zero-zalo-support-in-val/test limitation), and the task_scam recovery narrative's every factual claim traces to a real, existing source file. The post-review bugfix (commit `9577394`) is confirmed not to have silently altered the shipped v3 files.

---

_Verified: 2026-08-08_
_Verifier: Claude (gsd-verifier)_
