# Phase 39: Independent Quality Re-Judge - Context

**Gathered:** 2026-08-08
**Status:** Ready for planning

<domain>
## Phase Boundary

The repaired corpus (Phase 38's output) is independently judged for content
quality by a third model family (Codex) and a genuine human reviewer,
replacing the retired t-test with descriptive stats that can withstand
defense scrutiny. This phase does not touch corpus structure (splits, seed
groups, leakage) — that was Phase 38's job. It measures and, where a row is
genuinely bad, fixes content quality on the already-structurally-sound
corpus.

</domain>

<decisions>
## Implementation Decisions

### Data Directory Consolidation (discovered during discuss, executed before the rest of this phase)
- The `data/` tree had accumulated multiple competing split lineages
  (`recovered-balanced/`, `recovered-balanced-claude-v2/`, standalone
  top-level `train/val/test.jsonl`, `phase38-corpus-repaired-v2/`,
  `phase38-corpus-repaired-v3/`) plus versioned manifests and superseded
  synthetic source files. All of it was confusing to navigate and risked
  the same "which file is real" ambiguity that caused defense confusion
  before.
- Consolidated to a single canonical set: `data/splits/{train,val,test}.jsonl`
  (promoted from v3, the current leakage-safe corpus) and
  `data/manifests/manifest.json` (promoted from the v3 manifest).
- Every other lineage moved, byte-unchanged, to
  `data/backup/pre-260808-consolidation/{splits,synthetic,manifests}/` —
  nothing deleted, everything reversible.
- Code/test paths updated to match: `tests/data_pipeline/test_repair_corpus_split_governance.py`
  and `test_repair_corpus_full_scale.py` now point at the backup locations
  for their historical-input assertions; `repair_corpus_split_governance.py`'s
  CLI defaults updated to the new canonical layout, plus a new
  `--manifest-path` flag decoupling the manifest filename from
  `--version-tag` (previously every re-run with a new tag would silently
  create a new manifest file instead of updating the canonical one — exactly
  the clutter problem this consolidation fixed).
- `src/model_adaptation/cli.py`'s `_default_split_root()` /
  `_default_phase_five_split_path()` needed **no code changes** — their
  existing fallback-chain design (check a specific legacy dir, else fall
  through to the generic `data/splits/`) automatically resolves correctly
  once the legacy dirs are gone. Verified directly against the live repo,
  not just unit tests.
- `.planning/codex-judge-instructions.md` updated to point at the three new
  canonical split files (not a single pooled file — the corpus is now
  pre-split), with a `split` field added to the judge's output schema so
  results can still be joined back unambiguously.
- Historical STATE.md/ROADMAP.md entries describing old paths (e.g. Phase 7's
  `recovered-balanced.jsonl`) were left untouched — they correctly describe
  what was true when those phases ran; this project's convention treats that
  log as append-only history, not a live pointer.
- 229/229 tests pass after the reorganization (`tests/data_pipeline/` +
  `tests/model_adaptation/`), including live (non-tmp_path) verification
  that Phase 40's training CLI now defaults to the correct, current corpus.

### Judge Execution & Handoff Boundary
- Judge target: the three new canonical files, `data/splits/{train,val,test}.jsonl`
  — every row (2,421 total), not a sample.
- Handoff boundary: Claude prepares and finalizes all tooling (the judge
  instructions file, a merge/verification script for the judge's output),
  commits it, then stops. The user runs Codex externally (pasting the
  instructions file) and reports the resulting output file back — Claude
  cannot drive Codex CLI directly (no working API key; established earlier
  this milestone).
- "Done" for Claude's side of this sub-task: a committed, correctly-pointed
  instructions file plus a script that can validate and merge whatever
  Codex produces, ready to run the moment the output file exists.

### Fixing Flagged Rows & Manual Check
- Fix strategy for judge-flagged bad rows: attempt a targeted fix where
  feasible (e.g. re-derive an explanation or span), drop only if unfixable
  — same repair philosophy as Phase 38, not a blanket drop-everything-flagged
  policy.
- 100-manual-check sample: stratified — a mix of judge-pass and judge-fail
  rows, not pure random, so the check validates the judge's calls in both
  directions rather than only checking one side.
- Claude prepares the manual-check review sheet (row text + judge verdict,
  blank pass/fail column) for the user to fill in — the user does not have
  to hand-pick rows from raw JSONL themselves.
- Report integration: a descriptive table (pass rate + per-dimension means
  from the Codex judge, plus the manual-check pass rate) replaces the
  t-test in Chapter III's quality-check paragraph, in place — not a new
  standalone section.

### Claude's Discretion
None beyond the above — all grey areas were resolved explicitly, including
the mid-discussion data-consolidation scope change.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/data_pipeline/repair_corpus_split_governance.py` — now the single
  source of truth for how the corpus was built; its CLI defaults now match
  the live `data/` layout.
- `.planning/codex-judge-instructions.md` — already exists from earlier in
  this milestone, now updated for the consolidated paths and the
  three-file/`split`-field output shape.
- `src/data_pipeline/schemas.py::DatasetRecord` — the same schema the judge
  scores against (label, risk_tier, suspicious_spans, xai_explanation).

### Established Patterns
- Non-destructive reorganization: move to `data/backup/`, never delete —
  same pattern Phase 38 and 260808-otp already used for superseded corpus
  versions.
- Fail-closed CLI defaults: scripts should resolve to the *current* correct
  data without needing an explicit override, the way
  `_default_split_root()`'s fallback chain now does.

### Integration Points
- Input: `data/splits/{train,val,test}.jsonl` (2,421 rows total).
- Output: `data/processed/codex-judge-pass.jsonl` (Codex's judge results,
  produced externally), a manual-check review sheet, and — once both exist
  — descriptive stats ready to paste into Chapter III of the report
  (Phase 42's job to place, this phase's job to produce).

</code_context>

<specifics>
## Specific Ideas

No specific implementation references beyond the decisions above.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope (the data-directory
consolidation, while not originally scoped as part of Phase 39, was executed
immediately since it's a direct prerequisite for pointing the judge at the
right files, and blocks Phase 40 too if left undone).

</deferred>
