---
quick_id: 260808-otp
subsystem: data-pipeline
tags: [vietnamese, zalo, synthetic-data, leakage-governance, grouped-splits]
status: complete
requires:
  - phase: 38-corpus-repair-and-split-governance
    provides: seed-cap enforcement, evidence-span repair, and versioned split manifests
provides:
  - 300-row offline Codex-authored Zalo replacement with 60 independent seed lineages
  - replacement-aware Phase 38 v3 corpus with whole-seed 80/10/10 splits
  - normalized exact and 0.95 lexical leakage gates with manifest integrity checks
affects: [training-corpus, held-out-evaluation, phase-38, phase-39, phase-40]
tech-stack:
  added: []
  patterns: [static reviewed scenario catalog, provider-free TieredGenerator finalization, atomic versioned data writes]
key-files:
  created:
    - src/data_pipeline/generation/zalo_codex_catalog.py
    - src/data_pipeline/generation/zalo_codex_recovery.py
    - tests/data_pipeline/test_zalo_codex_recovery.py
    - data/synthetic/zalo-social-engineering-codex-2026-08-08.jsonl
    - data/splits/phase38-corpus-repaired-v3/train.jsonl
    - data/splits/phase38-corpus-repaired-v3/val.jsonl
    - data/splits/phase38-corpus-repaired-v3/test.jsonl
    - data/manifests/manifest-phase38-corpus-repaired-v3.json
  modified:
    - src/data_pipeline/repair_corpus_split_governance.py
    - tests/data_pipeline/test_repair_corpus_full_scale.py
key-decisions:
  - "Reuse TieredGenerator._finalize_records through object.__new__ so local rows follow the provider contract without initializing settings, clients, or providers."
  - "Treat each semantic scenario anchor as one lineage and derive one seed_id shared by all five variants."
  - "Apply normalized 0.95 lexical dedup to the replacement-enabled effective pool before the seed cap and grouped split."
metrics:
  duration: 38min
  completed: 2026-08-08
  tasks: 3
  tracked_files: 5
  local_data_files: 5
---

# Quick Task 260808-otp: Leakage-Safe Zalo Replacement Summary

**A provider-free 300-row Vietnamese Zalo corpus now replaces the legacy one-seed population with 60 semantic lineages and produces a seed-disjoint, deduplicated Phase 38 v3 split.**

## Performance

- **Started:** 2026-08-08T11:29:08Z
- **Completed:** 2026-08-08T12:06:58Z
- **Duration:** 38 minutes
- **Tasks:** 3/3
- **Tracked files:** 5
- **Ignored local artifacts:** 5

## Corpus Results

### Offline replacement

| Metric | Result |
| --- | ---: |
| Rows | 300 |
| Independent semantic roots / unique seed groups | 60 |
| Variants per seed group | 5 |
| Label | `zalo_social_engineering` |
| Schema source | `synthetic_openai_compatible` |
| Actual authoring runtime | `gpt-5.6-sol-codex-session` |
| External API/provider calls | 0 |
| Catalog content SHA-256 | `a7d13c2f5232c493c4579be2b3aacee6605aee95459fcd557af34b138214fb31` |
| JSONL file SHA-256 | `77dfb8c0f4f83c0c090adf7d12cb5010d3f4574777134ce44d29a678769db4ff` |

All 300 rows validate against `DatasetRecord`; all evidence spans are non-empty literal substrings; all explanations meet the schema floor; normalized text is unique; and no pair reaches the repository lexical duplicate threshold of 0.95.

### Replacement and repair accounting

| Stage | Rows |
| --- | ---: |
| Locked source rows pooled | 3,413 |
| Legacy Zalo rows removed | 825 |
| Offline replacement rows added | 300 |
| Effective replacement pool | 2,888 |
| Unrecoverable-span rows removed | 2 |
| Global normalized/lexical duplicate rows removed | 371 |
| Seed-cap rows removed | 94 |
| Final v3 rows | 2,421 |

The repair pass corrected evidence spans in 95 rows. The largest final seed group contains 193/2,421 rows (`7.9719%`), below the 8% cap.

### Final split support

| Split | Total rows | Unique seed groups | Bank | Benign | Task scam | Zalo rows | Zalo seed groups | SHA-256 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| train | 1,918 | 103 | 583 | 541 | 604 | 190 | 38 | `ea5ef4e96f03cf0a45790d00643da551b0e1fc4d4cb6a093594b20adaa2ce020` |
| val | 252 | 19 | 75 | 66 | 71 | 40 | 8 | `6d51dbc253e71d52df7759f5bf4caba00afaee09aefd04819af94fa8269cb8e1` |
| test | 251 | 25 | 65 | 57 | 59 | 70 | 14 | `1dfcfab980e0784011a2fb8c3f4105f82a02092d499bc7ff10441b020e01caf9` |

All four labels have nonzero support in every split. The 80/10/10 split is `79.22% / 10.41% / 10.37%`, within the one-percentage-point acceptance tolerance.

## Independent Leakage and Integrity Audit

| Gate | Result |
| --- | --- |
| Seed intersections: train/val, train/test, val/test | `0 / 0 / 0` |
| Invalid or non-literal evidence spans | `0` |
| Normalized duplicate rows in final corpus | `0` |
| Cross-split lexical matches at ratio >= 0.95 | `0 / 0 / 0` |
| Seeds above 8% | `0` |
| Manifest SHA/count/byte mismatches | `0` |
| Input and v2 backup hash changes | `0` |
| Repeated materialization byte changes | `0` |

The final manifest SHA-256 is `074e86335fc8c5c13fb8eada440c6df8347a9aacde56bc50917a5298342c5b7f`; every nested file hash, record count, and byte count was recomputed independently and matched.

## Verification Commands

- `python -m src.data_pipeline.generation.zalo_codex_recovery --output data/synthetic/zalo-social-engineering-codex-2026-08-08.jsonl`
- `python -m pytest tests/data_pipeline/test_zalo_codex_recovery.py -v` — **9 passed**
- `python -m src.data_pipeline.repair_corpus_split_governance --input-main data/synthetic/recovered-balanced.jsonl --input-reserved data/splits/recovered-balanced/test.jsonl --replacement-input data/synthetic/zalo-social-engineering-codex-2026-08-08.jsonl --replacement-label zalo_social_engineering --output-dir data/splits/phase38-corpus-repaired-v3 --version-tag phase38-corpus-repaired-v3 --cap-pct 0.08 --split-ratios 0.8,0.1,0.1`
- `python -m pytest tests/data_pipeline/test_repair_corpus_full_scale.py -v` — **9 passed**
- `python -m pytest tests/data_pipeline/test_repair_corpus_split_governance.py tests/data_pipeline/test_repair_corpus_full_scale.py -v` — **23 passed**
- `python -m pytest tests/data_pipeline/ -v` — **161 passed**
- Local Python audit recomputing split/class/seed counts, intersections, exact spans, normalized duplicates, RapidFuzz 0.95 cross-split matches, cap share, SHA-256, record counts, and byte counts — **all gates passed**

## Task Commits

1. **Task 1: Author and materialize the offline Codex provider corpus** — `db74e66`
2. **Task 2: Replace the old class and rebuild the versioned corpus** — `8b5336c`
3. **Task 3: Complete regression and independent audit** — verification-only; no additional tracked-code change

Planning artifacts and ignored local data were intentionally not committed. `STATE.md` and `ROADMAP.md` were intentionally left unchanged per orchestrator scope.

## Decisions Made

- Per-row provenance remains the schema-supported `synthetic_openai_compatible`, while manifest/build metadata names `gpt-5.6-sol-codex-session` as the actual local authoring path and records zero external calls.
- A root's seed is derived from its immutable semantic anchor through the existing SHA-256 `TieredGenerator` algorithm; wording variants never create new seeds.
- Replacement validation completes before any output write, and split/manifest outputs use temporary files followed by replacement.
- The grouped stratifier may move only whole seed groups to fill an otherwise-empty label/split cell; it never falls back to row-level splitting.

## Deviations from Plan

None — the global lexical dedup pass, grouped label-support guard, and atomic validation/write path were required to satisfy the plan's explicit leakage and fail-closed gates.

## Issues Encountered

- The pre-existing v2 corpus had 14 lexical near-duplicate matches across split boundaries at the 0.95 threshold. The replacement-enabled v3 path now deduplicates the effective pool before cap enforcement and grouped assignment; v2 bytes remain unchanged.
- The original Zalo population shared one seed with eight non-Zalo rows. Replacement filters by label rather than deleting the entire seed, preserving those unrelated bank rows.

## Known Stubs

None.

## User Setup Required

None. Generation and verification are completely local and require no credentials or external service.

## Self-Check: PASSED

- All five tracked implementation/test files exist.
- Both implementation commits exist in git history.
- The replacement JSONL, three v3 split JSONLs, and v3 manifest exist locally.
- Summary claims match the independently recomputed audit and the final on-disk hashes.

