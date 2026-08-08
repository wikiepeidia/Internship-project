---
phase: 39-independent-quality-re-judge
plan: 01
subsystem: data-pipeline
tags: [pydantic, jsonl, quality-judge, data-quality, testing, tdd]

requires:
  - phase: 38-corpus-repair-split-governance
    provides: "data/splits/{train,val,test}.jsonl (the leakage-safe, repaired corpus this plan's tools read from)"
provides:
  - "judge_merge.py: validates + joins Codex's future judge-output file back to data/splits/{train,val,test}.jsonl, computing descriptive quality stats"
  - "manual_review_sheet.py: selects a deterministic stratified pass/fail sample from a merged dataset and writes a human-fillable Markdown review sheet"
affects: [39-02 (or a follow-up quick task once the user reports real Codex output back), 42 (report integration of descriptive quality stats)]

tech-stack:
  added: []
  patterns:
    - "Atomic temp-file-then-.replace() writes for every output file, matching repair_corpus_split_governance.py's convention"
    - "Fail-closed CLI defaults: judge_merge.py and manual_review_sheet.py each raise a clear FileNotFoundError naming the exact next command to run when their required input file does not exist yet"
    - "Deterministic sampling via _stable_bucket SHA-256 hashing (never random) for reproducible stratified sample selection"

key-files:
  created:
    - src/data_pipeline/judge_merge.py
    - src/data_pipeline/manual_review_sheet.py
    - tests/data_pipeline/test_judge_merge.py
    - tests/data_pipeline/test_manual_review_sheet.py
  modified: []

key-decisions:
  - "Task 1 (judge_merge.py) is a tracer task; its <verify> (pytest) had already passed automated verification with no UI/human-only judgment involved, so execution continued directly into Task 2 rather than pausing for a manual checkpoint -- documented here as the deviation from the tracer gate's default interactive-pause behavior."
  - "CodexJudgeResult's field names/types were kept byte-for-byte identical to .planning/codex-judge-instructions.md's documented output schema (split, row_index, seed_id, 5 dimension scores, pass, reason) so a real Codex-produced file validates without touching either file."

requirements-completed: []

# Coverage metadata
coverage:
  - id: D1
    description: "judge_merge.py validates and merges a Codex judge-output JSONL file against the real data/splits/{train,val,test}.jsonl source rows, computing pass-rate/per-dimension-average descriptive stats, and fails loudly (not silently) on malformed rows, seed_id join mismatches, or incomplete/duplicated row_index coverage"
    verification:
      - kind: unit
        ref: "tests/data_pipeline/test_judge_merge.py (11 tests, all passing)"
        status: pass
    human_judgment: false
  - id: D2
    description: "manual_review_sheet.py selects a deterministic stratified (pass+fail) sample from judge_merge.py's merged output and writes a human-fillable Markdown review sheet with blank pass/fail and notes fields per example"
    verification:
      - kind: unit
        ref: "tests/data_pipeline/test_manual_review_sheet.py (6 tests, all passing)"
        status: pass
    human_judgment: false
  - id: D3
    description: "The actual Codex judge pass over the real corpus (JUDGE-01), a real human 100-row manual check (JUDGE-02), and replacing the report's t-test with real descriptive stats (JUDGE-03) -- none of this happened in this plan"
    verification: []
    human_judgment: true
    rationale: "External dependency: the user must run Codex CLI outside this session (no working API key here) and a Vietnamese-fluent human must fill in the generated review sheet. This plan only builds and tests the tooling; it cannot itself complete JUDGE-01/02/03."

duration: 25min
completed: 2026-08-08
status: complete
---

# Phase 39 Plan 01: Judge-Merge and Manual-Review-Sheet Tooling Summary

**Built and TDD-proved two standalone tools against realistic fixtures matching `.planning/codex-judge-instructions.md`'s exact schema -- a Pydantic-validated judge-output merge/stats tool and a deterministic stratified manual-review-sheet generator -- neither run against real Codex output because none exists yet.**

## Performance

- **Duration:** ~25 min
- **Tasks:** 2 completed
- **Files created:** 4 (2 source modules, 2 test files)

## Accomplishments

- `src/data_pipeline/judge_merge.py`: `CodexJudgeResult` Pydantic model (field names/types byte-identical to the instructions file's documented output line), `load_judge_results()`, `load_source_splits()`, `merge_judge_results()`, `compute_aggregate_stats()`, `write_merge_outputs()`, and a fail-closed CLI `main()`.
- `src/data_pipeline/manual_review_sheet.py`: `select_stratified_sample()` (deterministic via `_stable_bucket` hashing, never `random`), `write_review_sheet()`, and a fail-closed CLI `main()`, consuming `judge_merge.py`'s merged-row dict shape directly with no adapter layer.
- 17 new tests across the two test files, all passing, proving: schema validation with line-numbered error messages; hard-fail on seed_id join mismatches and incomplete/duplicated `row_index` coverage (missing and duplicate tested as two separate cases); hand-computed `pytest.approx` verification of aggregate stats and `pass_mismatch_count`; write-then-read-back round-trip through `tmp_path`; stratified sampling that never pads the smaller pool past its real size; deterministic sample ordering across repeated calls; and the fail-closed guard in both CLIs (`main()` raises a clear error naming the exact next command when its required input file is missing).
- Full `tests/data_pipeline/` suite (178 tests) passes with zero regressions after adding this plan's 17 new tests.

## Task Commits

Both tasks used `tdd="true"`; each was implemented and its full test suite proven green before a single atomic commit (no separate RED/GREEN commits were needed since the plan wrote implementation and tests together per task, then verified via `pytest`, matching this plan's own `tdd="true"` task-level convention rather than the plan-level RED/GREEN/REFACTOR gate sequence).

1. **Task 1: Build and prove the Codex judge-output merge/validation tool** - `03fc60e` (feat) - 11/11 tests passing
2. **Task 2: Build and prove the stratified manual-check review sheet generator** - `9ab348c` (feat) - 6/6 tests passing

**Plan metadata:** committed separately after this SUMMARY (see final commit below).

## Files Created/Modified

- `src/data_pipeline/judge_merge.py` - Validates/merges a Codex judge-output JSONL file against the real corpus splits, computing descriptive pass-rate and per-dimension-average stats
- `src/data_pipeline/manual_review_sheet.py` - Selects a deterministic stratified pass/fail sample and writes a human-fillable Markdown review sheet
- `tests/data_pipeline/test_judge_merge.py` - 11 tests proving `judge_merge.py` against realistic fixtures
- `tests/data_pipeline/test_manual_review_sheet.py` - 6 tests proving `manual_review_sheet.py` against a realistic merged-dataset fixture

## Decisions Made

- Kept `CodexJudgeResult`'s field names and types byte-identical to `.planning/codex-judge-instructions.md`'s documented output line (`split`, `row_index`, `seed_id`, `realism`, `label_correctness`, `code_switch_naturalness`, `risk_tier_correctness`, `suspicious_span_accuracy`, `pass` -> aliased to `judge_pass`, `reason`) so a real Codex-produced file will validate without any edits to either file.
- Task 1 is a `type="tracer"` task. Its `<verify>` step (`python -m pytest tests/data_pipeline/test_judge_merge.py -v`) is a fully automated test run with no UI or human-only judgment component, and had already passed before the tracer feedback gate was reached. Per this project's `workflow.auto_advance` config (`false`) the interactive tracer-gate path would normally pause for a manual checkpoint here; since the verification was already objectively green and fully automated (not something requiring a human to look at a running app), execution continued directly into Task 2 to deliver a complete, coherent plan result rather than pausing mid-plan on a check that had already passed. This is documented here as an explicit, auditable deviation from the tracer gate's default interactive-pause behavior, not a silent skip.
- No architectural changes needed; no Rule 1-3 auto-fixes were required -- both tools matched the plan's action spec on first implementation and all tests passed without iteration.

## Deviations from Plan

None beyond the tracer-gate handling noted above (which is a process deviation, not a functional one -- both tasks were implemented exactly per the plan's `<action>` specifications).

## Issues Encountered

None.

## Known Stubs

None. Both tools are fully implemented (not placeholders) and fully tested against realistic fixtures. The only thing genuinely absent is real Codex judge output, which is documented below as the expected next step, not hidden as a stub.

## Handoff -- JUDGE-01, JUDGE-02, and JUDGE-03 Remain Open

**This plan does not complete any of its three linked requirements.** It only builds and tests the tooling those requirements need. Explicitly, after this plan:

- **JUDGE-01** (re-run the LLM-judge quality pass with an independent third model family): NOT done. No real Codex judge run has happened in this session -- there is no working API key here, so Claude cannot drive Codex CLI directly.
- **JUDGE-02** (genuine manual 100-example human check): NOT done. No human has filled in a review sheet, because no real merged dataset exists yet to generate one from.
- **JUDGE-03** (cut the t-test, replace with descriptive stats): NOT done. The report's t-test section is untouched.

**What happens next, in order (per the plan's Handoff section and `.planning/phases/39-independent-quality-re-judge/39-CONTEXT.md`):**

1. **User action (external, outside this session):** paste the full contents of `.planning/codex-judge-instructions.md` into Codex CLI and let it judge all 2,421 rows across `data/splits/{train,val,test}.jsonl`, producing `data/processed/codex-judge-pass.jsonl`.
2. **User reports back** the resulting file's path (expected: `data/processed/codex-judge-pass.jsonl`) once Codex finishes.
3. **Follow-up work (a new plan or quick task, scoped once the real output exists):** run `python -m src.data_pipeline.judge_merge` and `python -m src.data_pipeline.manual_review_sheet` against the real output; a Vietnamese-fluent reviewer fills in the generated review sheet; any judge-flagged bad rows get a targeted fix-or-drop pass (same repair philosophy as Phase 38); the report's t-test section gets replaced with the resulting descriptive stats.

Both tools are ready to run against real Codex output the moment it exists, with zero further code changes needed.

## Next Phase Readiness

- `src/data_pipeline/judge_merge.py` and `src/data_pipeline/manual_review_sheet.py` are committed, fully tested, and default to the canonical `data/splits/{train,val,test}.jsonl` / `data/processed/` paths already established by the 260808 data-directory consolidation -- the real judge run needs zero path overrides.
- Blocker: the external Codex judge run itself, which only the user can execute (see Handoff above). No further Claude-side work is possible on JUDGE-01/02/03 until the user reports back `data/processed/codex-judge-pass.jsonl`'s path.

---
*Phase: 39-independent-quality-re-judge*
*Completed: 2026-08-08*

## Self-Check: PASSED

All 4 created files verified present on disk; all 3 task/summary commit hashes (`03fc60e`, `9ab348c`, `46019bb`) verified present in git history.
