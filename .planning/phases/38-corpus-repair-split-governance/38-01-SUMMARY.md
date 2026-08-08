---
phase: 38-corpus-repair-split-governance
plan: 01
subsystem: data-pipeline
tags: [python, pydantic, jsonl, sha256, dataset-governance, tdd]

# Dependency graph
requires: []
provides:
  - "src/data_pipeline/repair_corpus_split_governance.py — pool_records, repair_evidence_spans, repair_all_evidence_spans, enforce_seed_cap, assign_stratified_group_split, build_repair_manifest, and CLI main()"
  - "Full unit + end-to-end tracer test suite proving each function against real and synthetic fixtures"
affects: [38-02, 39-independent-quality-rejudge, 40-training]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Compose around existing manifest/split/dedup primitives rather than reimplementing (reuses _stable_bucket from splitter.py, lexical_dedup from dedup.py, build_manifest from versioning/manifest.py)"
    - "Two-tier evidence-span repair: exact substring kept as-is, case-insensitive re-extraction repairs the majority of mismatches, drop only the individual span (row dropped only if zero spans survive)"
    - "Iterative seed-cap enforcement recomputes each seed's share against the CURRENT (shrinking) total after every trim, not the original total"
    - "Deterministic SHA-256 hash bucketing for seed-group ordering (never random.shuffle) so split assignment is reproducible without RNG state"

key-files:
  created:
    - src/data_pipeline/repair_corpus_split_governance.py
    - tests/data_pipeline/test_repair_corpus_split_governance.py
  modified: []

key-decisions:
  - "build_repair_manifest() calls build_manifest() only (not save_manifest()) — matches the plan's detailed action text and 38-RESEARCH.md's Pattern 3 code example, which explicitly has the caller write the composed dict via json.dump() separately since the payload has extra fields beyond the ManifestEntry shape that save_manifest() writes"
  - "enforce_seed_cap() takes no salt parameter (matches the plan's declared signature exactly); the seed-cap survivor ordering uses an internal module constant salt instead of exposing it as an argument"
  - "assign_stratified_group_split()'s greedy scoring uses the corpus's actual observed per-class proportions (computed from the input records) as its target, not a hardcoded 25% per class, per 38-RESEARCH.md Open Question 2"

patterns-established:
  - "One-off corpus repair scripts live directly under src/data_pipeline/ (not a scratch/tmp location) and are committed like any other pipeline module, per 38-CONTEXT.md"

requirements-completed: [DATA-04, DATA-05, DATA-06, DATA-07]

coverage:
  - id: D1
    description: "pool_records() concatenates two JSONL files without dropping rows or fields"
    requirement: "DATA-04"
    verification:
      - kind: unit
        ref: "tests/data_pipeline/test_repair_corpus_split_governance.py#test_pool_records_combines_files_without_dropping_rows"
        status: pass
    human_judgment: false
  - id: D2
    description: "repair_evidence_spans() repairs case-insensitive span mismatches (incl. the real row-1 bug) via exact-cased re-extraction, drops only truly unrecoverable spans, and drops a row only when zero spans survive"
    requirement: "DATA-06"
    verification:
      - kind: unit
        ref: "tests/data_pipeline/test_repair_corpus_split_governance.py#test_repair_evidence_spans_keeps_exact_substring_unchanged"
        status: pass
      - kind: unit
        ref: "tests/data_pipeline/test_repair_corpus_split_governance.py#test_repair_evidence_spans_real_row1_case_mismatch"
        status: pass
      - kind: unit
        ref: "tests/data_pipeline/test_repair_corpus_split_governance.py#test_repair_evidence_spans_drops_unmatched_diacritic_span_but_keeps_row"
        status: pass
      - kind: unit
        ref: "tests/data_pipeline/test_repair_corpus_split_governance.py#test_repair_evidence_spans_drops_row_when_all_spans_unrecoverable"
        status: pass
      - kind: unit
        ref: "tests/data_pipeline/test_repair_corpus_split_governance.py#test_repair_all_evidence_spans_drops_unrecoverable_row_and_counts_it"
        status: pass
    human_judgment: false
  - id: D3
    description: "enforce_seed_cap() trims an over-8%-cap seed_id group using lexical_dedup-selected diverse survivors (not first-N truncation), recording before/after concentration"
    requirement: "DATA-05"
    verification:
      - kind: unit
        ref: "tests/data_pipeline/test_repair_corpus_split_governance.py#test_enforce_seed_cap_trims_over_cap_seed_using_lexical_dedup"
        status: pass
    human_judgment: false
  - id: D4
    description: "assign_stratified_group_split() never splits a seed_id across two splits, is deterministic (hash-based, not RNG), and targets the corpus's observed class mix rather than a hardcoded 25% each"
    requirement: "DATA-04"
    verification:
      - kind: unit
        ref: "tests/data_pipeline/test_repair_corpus_split_governance.py#test_assign_stratified_group_split_is_deterministic"
        status: pass
      - kind: unit
        ref: "tests/data_pipeline/test_repair_corpus_split_governance.py#test_assign_stratified_group_split_targets_observed_class_mix_not_25_25_25_25"
        status: pass
    human_judgment: false
  - id: D5
    description: "build_repair_manifest() composes split_class_distribution + repair_stats around the unmodified build_manifest() output"
    requirement: "DATA-07"
    verification:
      - kind: unit
        ref: "tests/data_pipeline/test_repair_corpus_split_governance.py#test_build_repair_manifest_calls_build_manifest_and_composes_dict"
        status: pass
    human_judgment: false
  - id: D6
    description: "Full pool -> repair -> cap -> split chain proven end-to-end against a real 70-row subset (60 rows recovered-balanced.jsonl + 10 rows test.jsonl): zero invalid spans survive, zero seed_id crosses more than one split"
    requirement: "DATA-04"
    verification:
      - kind: unit
        ref: "tests/data_pipeline/test_repair_corpus_split_governance.py#test_end_to_end_tracer_real_70_row_subset"
        status: pass
    human_judgment: false

duration: 42min
completed: 2026-08-08
status: complete
---

# Phase 38 Plan 1: Corpus Repair/Cap/Split/Manifest Pipeline Summary

**Built and TDD-proved the full pool -> evidence-span-repair -> seed-cap -> stratified-split -> manifest pipeline in one module, reusing `_stable_bucket`, `lexical_dedup`, and `build_manifest` from the existing codebase, and end-to-end verified against a real 70-row subset of the actual corpus.**

## Performance

- **Duration:** ~42 min
- **Started:** 2026-08-08T09:37:00Z (approx.)
- **Completed:** 2026-08-08T10:19:11Z
- **Tasks:** 2 (Task 1: tracer build + core behavior; Task 2: hardening/edge-case coverage)
- **Files modified:** 2 (both new files)

## Accomplishments

- `src/data_pipeline/repair_corpus_split_governance.py` implements all five pipeline functions plus a CLI `main()`:
  `pool_records`, `repair_evidence_spans`, `repair_all_evidence_spans`, `enforce_seed_cap`, `assign_stratified_group_split`, `build_repair_manifest`.
- Evidence-span repair verified against the *real* row-1 case-mismatch bug from `data/synthetic/recovered-balanced.jsonl` (span `"tai khoan..."` correctly re-extracted to the exact-cased `"Tai khoan..."` substring, the other two spans untouched).
- Seed-concentration capping verified to actually invoke `lexical_dedup` (via spy) when trimming an over-cap group, and to order survivors deterministically via `_stable_bucket` rather than first-N truncation.
- Stratified split assignment verified deterministic across repeated calls with the same salt, and verified to target the corpus's *observed* class mix (tested with an intentionally skewed 40/20/20/20 fixture) rather than a hardcoded 25% per class.
- Manifest composition verified to call the real `build_manifest()` (spy) and wrap it with `split_class_distribution` + `repair_stats`, without modifying the shared `ManifestEntry`/`ManifestFile` schema.
- End-to-end tracer test chains all four core functions against a **real** 70-row subset (60 rows of `data/synthetic/recovered-balanced.jsonl` + 10 rows of `data/splits/recovered-balanced/test.jsonl`), asserting zero invalid (non-exact-substring) spans survive and zero `seed_id` crosses more than one assigned split.

## Task Commits

Both tasks were implemented and tested as one cohesive unit (the module's functions and their edge-case coverage were built together in a single TDD pass, since Task 2's hardening tests exercise the same functions Task 1 built and no separable intermediate state existed between them):

1. **Task 1 + Task 2: Build and harden the full repair/cap/split/manifest pipeline** - `3290d4d` (feat)

**Plan metadata:** pending (this commit, made after SUMMARY.md is written)

_Note: All 12 tests (Task 1's tracer/unit tests plus Task 2's determinism/observed-class-mix/full-row-drop/manifest-composition hardening tests) pass together in the single commit above; no bugs were found during Task 2 that required a separate fix commit._

## Files Created/Modified

- `src/data_pipeline/repair_corpus_split_governance.py` - the five pipeline functions (pool/repair/cap/split/manifest) plus CLI `main()`
- `tests/data_pipeline/test_repair_corpus_split_governance.py` - 12 tests covering every function's documented behavior, including the real-data tracer

## Decisions Made

- `build_repair_manifest()` calls `build_manifest()` only, not `save_manifest()`. The plan's `key_links` frontmatter line says both are called "unchanged," but the plan's detailed `<action>` text and 38-RESEARCH.md's Pattern 3 code example both specify that `build_repair_manifest()` returns a composed dict for the *caller* (`main()`) to write via `json.dump()` — since that payload has extra fields (`split_class_distribution`, `repair_stats`) beyond what `save_manifest()`'s `ManifestEntry`-only writer expects. Followed the more detailed, concrete guidance.
- `enforce_seed_cap()` has no `salt` parameter, matching the plan's exact declared signature (`enforce_seed_cap(records, cap_pct=0.08) -> tuple[list[dict], dict]`). The deterministic ordering salt used when selecting `lexical_dedup` survivors is an internal module constant instead.
- `assign_stratified_group_split()`'s target proportions are computed from the actual observed global class mix of the input `records`, not a hardcoded 25% per class, per 38-RESEARCH.md's Open Question 2 recommendation.

## Deviations from Plan

None - plan executed exactly as written. (See "Decisions Made" above for two implementation-detail clarifications where the plan's action text and code example were more specific than its summary-level `key_links` line; both were followed as the more authoritative, detailed guidance and do not change behavior required by any `must_haves.truths` or acceptance criteria.)

## Issues Encountered

- The Task 2 "observed class mix, not hardcoded 25%" test initially failed with a coarse fixture (20 seed groups x 5 rows = 100 rows) because the small val/test split targets (10 rows = 2 groups) sometimes landed zero `task_scam` groups by chance, making that split's proportion equidistant from both 25% and 40% in the wrong direction. This was a test-fixture granularity issue, not an implementation bug — fixed by using finer-grained groups (100 seed groups x 2 rows = 200 rows) so every split has enough group-assignment resolution to reflect the observed mix. Confirmed via passing test afterward.

## User Setup Required

None - no external service configuration required. Pure offline Python module, no new dependencies.

## Next Phase Readiness

- `main()` is fully wired (pool -> repair -> cap -> split -> write validated JSONL -> manifest) and ready for Plan 38-02 to invoke against the full 3,413-row pooled corpus without further code changes.
- The module correctly avoids `split_dataset()`'s underdiverse-label record-level fallback (38-RESEARCH.md Pitfall 4) by implementing its own group-integrity-preserving greedy stratification from scratch.
- No blockers. Plan 38-02 can proceed directly to running `main()` at full scale and validating the real cap/leakage/span-validity numbers cited in 38-RESEARCH.md (two over-cap seeds, 171 total bad-span rows).

---
*Phase: 38-corpus-repair-split-governance*
*Completed: 2026-08-08*
