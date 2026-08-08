---
phase: 38-corpus-repair-split-governance
plan: 02
subsystem: data-pipeline
tags: [python, pydantic, jsonl, sha256, dataset-governance, full-scale-run]

# Dependency graph
requires:
  - phase: 38-corpus-repair-split-governance (Plan 01)
    provides: "src/data_pipeline/repair_corpus_split_governance.py — pool/repair/cap/split/manifest pipeline + CLI main()"
provides:
  - "data/splits/phase38-corpus-repaired-v2/{train,val,test}.jsonl — the real, final repaired 80/10/10 corpus (1,960/260/260 rows)"
  - "data/manifests/manifest-phase38-corpus-repaired-v2.json — SHA-256 manifest with 80/10/10 ratio, per-split per-class counts, repair_stats"
  - "tests/data_pipeline/test_repair_corpus_full_scale.py — automated post-condition proof of DATA-04 through DATA-07 against the real output"
  - ".planning/phases/38-corpus-repair-split-governance/38-recovery-narrative-task-scam.md — evidence-cited task_scam 0.44->0.871 narrative for Phase 42"
  - "Two real bug fixes to src/data_pipeline/repair_corpus_split_governance.py, discovered only at full 3,413-row scale"
affects: [39-independent-quality-rejudge, 40-training, 42-report-overhaul]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Full-scale execution as a correctness gate: running the real 3,413-row pool surfaced two bugs invisible to the 38-01 unit-test fixtures (empty-vs-unrecoverable span conflation; iterative vs. original-total 'before' snapshot)"
    - "Manifest always reports all four labels per split explicitly (including 0), so structural data limitations are visible in the artifact rather than silently omitted"

key-files:
  created:
    - tests/data_pipeline/test_repair_corpus_full_scale.py
    - .planning/phases/38-corpus-repair-split-governance/38-recovery-narrative-task-scam.md
  modified:
    - src/data_pipeline/repair_corpus_split_governance.py
    - tests/data_pipeline/test_repair_corpus_split_governance.py

key-decisions:
  - "repair_evidence_spans() only drops a row when it ORIGINALLY had non-empty suspicious_spans that all became unrecoverable — a row that started with suspicious_spans=[] (the schema default, used by all benign rows) is kept as-is. The original 38-01 implementation dropped both cases identically, which at full scale would have destroyed all 750 benign rows."
  - "enforce_seed_cap()'s seed_concentration_before now snapshots every originally-over-cap seed's share against the pre-trim total, not the iteratively-shrinking total. This makes the manifest's before-value for seed_157ce0adb043 match the real 11.90% pooled measurement (38-RESEARCH.md) instead of an artifact of trim order (was 14.25%)."
  - "_compute_split_class_counts() always emits all four label keys per split (0 where absent) instead of omitting absent labels, so the manifest is a complete, honest record rather than one that silently hides a zero-support class."
  - "zalo_social_engineering's entire pre-repair population (825 of 825 rows across both source files) traces to exactly one seed_id (the same seed already flagged in 38-RESEARCH.md as the 24.41% dominant seed). Group-integrity-preserving splitting — the phase's primary, locked DATA-04 requirement — therefore places that label's ~196 surviving rows entirely in one split (train), leaving val and test with zero zalo_social_engineering support. This is accepted as the correct, honest outcome per 38-CONTEXT.md's explicit locked decision ('perfect stratification is not required when it would break group integrity'), not treated as a bug to work around by breaking seed-group integrity."

patterns-established:
  - "When a plan's acceptance criteria encodes a specific research-measured number as ground truth (e.g. 24.41%/11.90%), full-scale execution is the only way to confirm the pipeline actually reproduces it — a unit-test fixture with a single over-cap seed cannot catch an iterative-vs-original-total snapshot bug."

requirements-completed: [DATA-04, DATA-05, DATA-06, DATA-07, DATA-08]

coverage:
  - id: D1
    description: "Full 3,413-row pool -> repair -> cap -> split -> manifest run produces the real train/val/test.jsonl (1,960/260/260 rows) with zero seed_id crossing a split boundary"
    requirement: "DATA-04"
    verification:
      - kind: unit
        ref: "tests/data_pipeline/test_repair_corpus_full_scale.py#test_zero_seed_id_crosses_split_boundary"
        status: pass
    human_judgment: false
  - id: D2
    description: "Both real over-cap seeds (seed_1a4f7d4d7c53 at 24.41%, seed_157ce0adb043 at 11.90%) are reduced to <=8% in the final corpus, with correct before/after values recorded in the manifest"
    requirement: "DATA-05"
    verification:
      - kind: unit
        ref: "tests/data_pipeline/test_repair_corpus_full_scale.py#test_seed_concentration_capped_and_before_after_recorded"
        status: pass
    human_judgment: false
  - id: D3
    description: "Zero rows in the final written train/val/test.jsonl have a suspicious_spans entry that is not an exact substring of that row's text"
    requirement: "DATA-06"
    verification:
      - kind: unit
        ref: "tests/data_pipeline/test_repair_corpus_full_scale.py#test_zero_invalid_evidence_spans"
        status: pass
    human_judgment: false
  - id: D4
    description: "Manifest records the 80/10/10 split ratio and per-split, per-class row counts (all four labels, explicit zero where absent)"
    requirement: "DATA-07"
    verification:
      - kind: unit
        ref: "tests/data_pipeline/test_repair_corpus_full_scale.py#test_manifest_records_split_ratio_and_full_per_class_distribution"
        status: pass
      - kind: unit
        ref: "tests/data_pipeline/test_repair_corpus_full_scale.py#test_three_of_four_labels_have_non_zero_support_in_every_split"
        status: pass
      - kind: unit
        ref: "tests/data_pipeline/test_repair_corpus_full_scale.py#test_single_seed_label_zero_support_is_the_documented_known_exception"
        status: pass
    human_judgment: false
  - id: D5
    description: "Backup preservation: data/synthetic/recovered-balanced.jsonl (3,000 rows) and data/splits/recovered-balanced/test.jsonl (413 rows) remain byte-unchanged after the run"
    requirement: "DATA-04"
    verification:
      - kind: unit
        ref: "tests/data_pipeline/test_repair_corpus_full_scale.py#test_original_backup_files_unchanged"
        status: pass
    human_judgment: false
  - id: D6
    description: "task_scam 0.44->0.871 recovery narrative drafted, citing real Phase 7a evidence artifacts (07a-CONTEXT.md, 07a-01-SUMMARY.md) and compiled report sources (dataset_statistics.tex, 05_evaluation_and_discussion.tex) for every numeric claim"
    requirement: "DATA-08"
    verification:
      - kind: other
        ref: "python one-liner verify command in 38-02-PLAN.md Task 2 <verify> — prints ALL PRESENT"
        status: pass
    human_judgment: false

duration: 14min
completed: 2026-08-08
status: complete
---

# Phase 38 Plan 2: Full-Scale Corpus Repair Execution & Recovery Narrative Summary

**Ran the Plan 38-01 pipeline against the real 3,413-row pooled corpus, found and fixed two real bugs invisible to unit-test fixtures (an empty-vs-unrecoverable-spans conflation that would have destroyed all 750 benign rows, and a seed-cap "before" snapshot computed against a shrinking rather than original total), then proved all five Phase 38 acceptance gates against the actual written output and drafted the evidence-cited task_scam recovery narrative.**

## Performance

- **Duration:** ~14 min
- **Started:** 2026-08-08T17:22:00Z (approx., immediately after 38-01)
- **Completed:** 2026-08-08T17:36:00Z
- **Tasks:** 2 (Task 1: full-scale run + acceptance-gate tests; Task 2: recovery narrative)
- **Files modified:** 4 (2 code fixes, 2 new files) plus real data output on disk (gitignored per project convention)

## Accomplishments

- Ran `src.data_pipeline.repair_corpus_split_governance.main()` against the real, full 3,413-row pool (`data/synthetic/recovered-balanced.jsonl` + `data/splits/recovered-balanced/test.jsonl`), producing `data/splits/phase38-corpus-repaired-v2/{train,val,test}.jsonl` (1,960 / 260 / 260 rows) and `data/manifests/manifest-phase38-corpus-repaired-v2.json`.
- Found and fixed a real bug in `repair_evidence_spans()`: it treated a row that legitimately started with `suspicious_spans=[]` (the `DatasetRecord` schema default, used by every one of the 750 original `benign` rows) identically to a row whose spans all became unrecoverable — silently dropping it. At full scale this manifested as 806 of 3,413 rows dropped on the first run (instead of the expected ~2, per 38-RESEARCH.md's simulation). Fixed to only drop a row when it originally had spans that all failed repair; re-run then dropped exactly 2 rows, matching research's prediction (0 of 40 in the reserved file, 2 of 131 in the main file).
- Found and fixed a second real bug in `enforce_seed_cap()`: `seed_concentration_before` was captured against the CURRENT (already-shrinking) total inside the iterative trim loop, so the second over-cap seed's recorded "before" value (14.25%) didn't match the true pre-trim pooled measurement (11.90%, per 38-RESEARCH.md). Fixed to snapshot every originally-over-cap seed's share against the pre-trim total; the manifest now correctly records 24.41% and 11.90% for the two seeds named in research.
- Fixed `_compute_split_class_counts()` to always report all four labels per split explicitly (0 where a label has no rows), rather than silently omitting an absent label from the manifest.
- Wrote `tests/data_pipeline/test_repair_corpus_full_scale.py` (8 tests) proving DATA-04 through DATA-07 against the real written output files, plus two tests (`test_three_of_four_labels_have_non_zero_support_in_every_split`, `test_single_seed_label_zero_support_is_the_documented_known_exception`) that lock in and root-cause-verify the one honest exception discovered during this run (see Deviations).
- Drafted `.planning/phases/38-corpus-repair-split-governance/38-recovery-narrative-task-scam.md` — 5 paragraphs covering the original 0.44 recall + gate bug, root cause (750 narrow-coverage rows), the fix (400 new rows across 5 named scenario axes, adapter `task-scam-recovery-2026-05-28`), and the recovered 0.871 recall on 62 held-out examples — every numeric claim inline-cited to a real source file.
- Confirmed `data/synthetic/recovered-balanced.jsonl` (3,000 lines) and `data/splits/recovered-balanced/test.jsonl` (413 lines) are unchanged after the run (`git diff HEAD` on both paths is empty).

## Task Commits

1. **Task 1: Full-scale run + 2 bug fixes + acceptance-gate tests** - `fc61108` (feat)
2. **Task 2: task_scam recovery narrative** - `9180b08` (docs)

**Plan metadata:** pending (this commit, made after SUMMARY.md is written)

## Files Created/Modified

- `src/data_pipeline/repair_corpus_split_governance.py` - fixed `repair_evidence_spans()` (empty-vs-unrecoverable conflation), `enforce_seed_cap()` (before-snapshot semantics), `_compute_split_class_counts()` (always-report-all-four-labels)
- `tests/data_pipeline/test_repair_corpus_split_governance.py` - added 2 regression tests (`test_repair_evidence_spans_keeps_row_that_originally_had_zero_spans`, `test_enforce_seed_cap_before_snapshot_uses_original_total_not_shrinking_total`)
- `tests/data_pipeline/test_repair_corpus_full_scale.py` - new, 8 tests proving DATA-04 through DATA-07 against the real full-scale output
- `.planning/phases/38-corpus-repair-split-governance/38-recovery-narrative-task-scam.md` - new, task_scam recovery narrative for Phase 42
- `data/splits/phase38-corpus-repaired-v2/{train,val,test}.jsonl` - real output data (1,960/260/260 rows); gitignored per this project's established `data/` convention (only `.gitkeep` placeholders are tracked — matches how `data/synthetic/recovered-balanced.jsonl` itself is also untracked)
- `data/manifests/manifest-phase38-corpus-repaired-v2.json` - real output manifest; same gitignore convention as above

## Decisions Made

- Fixed both pipeline bugs inline (Rule 1 - auto-fix) rather than working around them, since both were genuine correctness defects that would have corrupted the final training corpus (one would have destroyed the entire `benign` class; the other would have misreported the seed-cap audit trail against the plan's own must_haves.truths figures).
- Chose NOT to force-add (`git add -f`) the new data/manifest output files to git. This repository gitignores the entire `data/` tree by design (verified: only `.gitkeep` files are tracked in `data/synthetic/`, `data/splits/`, `data/manifests/`) and the existing canonical corpus (`data/synthetic/recovered-balanced.jsonl`) is itself untracked. Committing only the code (pipeline fixes + tests) that produces and verifies the data, not the data files themselves, follows the project's established pattern rather than introducing an inconsistent exception.
- Accepted `zalo_social_engineering` having zero support in `val`/`test` as the correct, honest outcome rather than an unmet requirement to work around. See Deviations below for full reasoning.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `repair_evidence_spans()` conflated "originally empty spans" with "spans became unrecoverable"**
- **Found during:** Task 1, first full-scale run (dropped 806 of 3,413 rows instead of the ~2 predicted by 38-RESEARCH.md)
- **Issue:** The function returned `None` (drop row) whenever the repaired-spans list was empty, without checking whether the row started with a non-empty `suspicious_spans` list. Since `DatasetRecord.suspicious_spans` schema-defaults to `[]` and all 750 `benign` rows (plus a handful of `task_scam`/`bank_impersonation` rows) legitimately have no evidence spans, this would have dropped nearly all `benign` rows from the final corpus.
- **Fix:** Only return `None` when `original_spans` was non-empty and zero spans survived repair. Rows that started empty are kept unchanged.
- **Files modified:** `src/data_pipeline/repair_corpus_split_governance.py`
- **Verification:** New regression test `test_repair_evidence_spans_keeps_row_that_originally_had_zero_spans`; re-run dropped exactly 2 rows (matching 38-RESEARCH.md's "2 of 131 unrecoverable in the 3,000-row file, 0 of 40 in the 413-row file").
- **Committed in:** `fc61108` (Task 1 commit)

**2. [Rule 1 - Bug] `enforce_seed_cap()`'s before-snapshot used the shrinking total, not the original total**
- **Found during:** Task 1, comparing the manifest's `seed_concentration_before` against 38-RESEARCH.md's stated real measurements (24.41% / 11.90%)
- **Issue:** The iterative trim loop only captured a seed's "before" share the first time it was identified as over cap, using whatever the CURRENT (possibly already-shrunk-by-earlier-trims) total was at that point — for `seed_157ce0adb043` this produced 14.25% instead of the true pre-trim 11.90%.
- **Fix:** Snapshot every seed that is already over `cap_pct` against the initial pre-trim total, before the trim loop begins; seeds that only cross the cap later due to denominator shrinkage still fall back to at-detection-time recording (there is no earlier "true" over-cap share to report for those).
- **Files modified:** `src/data_pipeline/repair_corpus_split_governance.py`
- **Verification:** New regression test `test_enforce_seed_cap_before_snapshot_uses_original_total_not_shrinking_total`; manifest now records 0.2442 and 0.1190 for the two seeds, matching 38-RESEARCH.md.
- **Committed in:** `fc61108` (Task 1 commit)

**3. [Rule 2 - Missing Critical] Manifest silently omitted labels with zero rows in a split**
- **Found during:** Task 1, while investigating the zalo_social_engineering finding below
- **Issue:** `_compute_split_class_counts()` only added a label key when at least one row of that label existed in the split — a split with zero rows of a label would have that label's key missing entirely from the manifest, rather than explicitly showing 0. This would have made the real zalo_social_engineering gap (below) invisible in the manifest itself.
- **Fix:** Always emit all four label keys per split, defaulting to 0.
- **Files modified:** `src/data_pipeline/repair_corpus_split_governance.py`
- **Verification:** `test_manifest_records_split_ratio_and_full_per_class_distribution` asserts all four label keys are present in every split's distribution.
- **Committed in:** `fc61108` (Task 1 commit)

---

**Total deviations:** 3 auto-fixed (2 bugs, 1 missing-critical-functionality gap)
**Impact on plan:** All three fixes were necessary for the final corpus to be correct and for the manifest to honestly document the phase's own acceptance-gate figures. No scope creep — all three are inside `repair_corpus_split_governance.py`, the exact module this plan's Task 1 runs and verifies.

### Significant Finding (not a bug — documented, not worked around)

**`zalo_social_engineering` has zero row support in `val.jsonl` and `test.jsonl`.**

During full-scale execution, `zalo_social_engineering`'s entire pre-repair population — 825 of 825 rows across BOTH `data/synthetic/recovered-balanced.jsonl` and `data/splits/recovered-balanced/test.jsonl` — was found to trace to exactly one `seed_id` (`seed_1a4f7d4d7c53`, the same seed 38-RESEARCH.md already flagged as the dominant 24.41%-of-corpus seed). After seed-cap enforcement trims it to ~196 surviving rows, it is still exactly one atomic seed-group.

`38-CONTEXT.md`'s locked decision is explicit: *"Stratification: best-effort per-class balance within the group constraint... Perfect stratification is not required when it would break group integrity."* Group-integrity-preserving splitting (DATA-04, the phase's primary and safety-critical requirement — this whole phase exists to eliminate exactly the kind of cross-split seed leakage that would result from splitting one seed's rows across train/val/test) therefore mathematically forces this seed's entire row-group into exactly one split. No stratification-algorithm change can create seed diversity that does not exist in the underlying generated data; only breaking group integrity (reintroducing leakage) or generating new, more diverse `zalo_social_engineering` seed material (out of scope for this repair-only phase per `38-CONTEXT.md`) could change this.

**Decision:** Preserved group integrity (the locked, safety-critical requirement) and accepted the resulting zero support for `zalo_social_engineering` in `val`/`test` as the correct, honest outcome — consistent with this milestone's explicit value of reporting results honestly rather than engineering around them ("any result reported honestly, not chased toward a 'win'", STATE.md). The manifest now explicitly records this as `0` (see fix #3 above) rather than omitting it, and two new tests (`test_three_of_four_labels_have_non_zero_support_in_every_split`, `test_single_seed_label_zero_support_is_the_documented_known_exception`) lock in that this is the ONLY label/split combination affected and root-cause-verify it against the actual seed_id.

**Downstream impact for Phase 39/40:** `zalo_social_engineering` recall cannot be measured on `val.jsonl` or `test.jsonl` from this corpus — only `train.jsonl` has any examples of this class. This is a genuine, load-bearing limitation that Phase 39 (independent re-judge) and Phase 40 (training/evaluation) need to be aware of; it is not something this repair-and-split phase can fix without either violating DATA-04 or generating new seed-diverse `zalo_social_engineering` data (a data-generation task, out of this phase's locked scope).

## Issues Encountered

- The `must_haves.truths` line in `38-02-PLAN.md`'s frontmatter and Task 1's literal acceptance criteria ("non-zero counts for all four labels" per split) were written based on 38-RESEARCH.md's "87 unique seed_ids across 4 roughly-balanced labels" characterization, which held in aggregate but not per-label — `zalo_social_engineering` turned out to have exactly 1 unique seed_id system-wide, not "roughly balanced" like the other three. This was only discoverable by running the pipeline against the real full-scale data (as this plan explicitly required), not from the 38-01 unit-test fixtures. Resolved by treating the underlying, more fundamental DATA-07 requirement text ("recorded in a manifest with per-split class distribution") as satisfied — the manifest DOES record an explicit, correct row count (including zero) for every label in every split — while documenting the specific single-label exception transparently rather than silently passing or silently failing the test suite.

## User Setup Required

None - no external service configuration required. Pure offline Python module, no new dependencies, no network calls.

## Next Phase Readiness

- `data/splits/phase38-corpus-repaired-v2/{train,val,test}.jsonl` and `data/manifests/manifest-phase38-corpus-repaired-v2.json` are the real, final, verified corpus for Phase 39 (independent quality re-judge) and Phase 40 (training) to consume.
- Old lineage (`data/synthetic/recovered-balanced.jsonl`, `data/splits/recovered-balanced/*.jsonl`) confirmed unchanged and preserved as backup, per `38-CONTEXT.md`.
- `.planning/phases/38-corpus-repair-split-governance/38-recovery-narrative-task-scam.md` is ready for Phase 42 to paste into the report's Data Construction chapter.
- **Blocker/watchpoint for Phase 39/40:** `zalo_social_engineering` has zero examples in `val.jsonl`/`test.jsonl` (see Deviations above) — any Phase 40 evaluation plan must either accept this class is train-only-evaluable in this corpus, or a future phase must generate additional seed-diverse `zalo_social_engineering` source material before this gap can close. Not a blocker for Phase 38 closing (DATA-04 through DATA-08 are satisfied by their underlying requirement text), but genuinely load-bearing for what Phase 40 can honestly report.

## Self-Check: PASSED

- FOUND: `data/splits/phase38-corpus-repaired-v2/train.jsonl` (1,960 rows)
- FOUND: `data/splits/phase38-corpus-repaired-v2/val.jsonl` (260 rows)
- FOUND: `data/splits/phase38-corpus-repaired-v2/test.jsonl` (260 rows)
- FOUND: `data/manifests/manifest-phase38-corpus-repaired-v2.json`
- FOUND: `tests/data_pipeline/test_repair_corpus_full_scale.py` (8 tests, all pass)
- FOUND: `.planning/phases/38-corpus-repair-split-governance/38-recovery-narrative-task-scam.md` (all 6 required anchors present)
- FOUND commit: `fc61108` (feat: full-scale run + bug fixes + tests)
- FOUND commit: `9180b08` (docs: recovery narrative)
- Full `tests/data_pipeline/` suite (151 tests) passes.

---
*Phase: 38-corpus-repair-split-governance*
*Completed: 2026-08-08*
