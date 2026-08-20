# Phase 39: Independent Quality Re-Judge - Context

**Gathered:** 2026-08-08
**Status:** Ready for planning

<domain>
## Phase Boundary

The repaired corpus (Phase 38's output) is independently judged for content
quality by a third model family (Codex) and a genuine human reviewer,
replacing the retired t-test with descriptive stats that can withstand
defense scrutiny. The completed Phase 38 structure remains the integrity
baseline, but the Phase 39 continuation may apply the user's 324 targeted
label/drop decisions, quarantine non-independent lineage, re-enforce the
global seed cap, and re-split whole seed groups. Those changes must preserve
Phase 38's leakage, duplicate, span, cap, and provenance guarantees; seed
diversity may never be manufactured.

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
- The initial 2,421-row Codex judgment is historical evidence. Final-snapshot
  coverage is rebuilt over the projected 2,103-row staged corpus using exact
  seven-field record digests: 1,562 unchanged judgments may carry forward
  byte-for-evidence, while all 541 remaining records require fresh judgment.
- The current Codex session performs the fresh work locally in deterministic,
  hash-bound batches. No Claude key, web search, plugin, or external provider
  is involved. Completed batches are immutable and restartable; partial or
  hash-conflicting results fail closed.
- "Done" means a joinable 2,103-row final result whose carried and fresh
  origins are disjoint and complete, plus a machine-verifiable convergence
  ledger proving zero unresolved semantic rows and a later fresh verdict for
  every repaired digest.

### Fixing Flagged Rows & Manual Check
- Apply the 324 authorized human decisions as label-only changes or drops.
  Risk tier, suspicious spans, and XAI remain unchanged unless an explicit,
  identity-bound Codex semantic-repair artifact authorizes the correction;
  every changed digest is freshly re-judged.
- The final 100-row sample is generated anew from the promoted snapshot and
  stratified across labels, judge pass/fail status, and carried/fresh judge
  origin. An old human verdict carries only when both record and full judge-
  evidence digests match and its checkbox is unambiguous; otherwise it stays
  blank for the user.
- The user completes every remaining review row at a blocking human
  checkpoint. No automation may infer or auto-pass human semantics.
- Report integration: a descriptive table (pass rate + per-dimension means
  from the Codex judge, plus the manual-check pass rate) replaces the
  t-test in Chapter III's quality-check paragraph, in place — not a new
  standalone section.

### Superseding Closure Decision (2026-08-20)
- The latest user direction requires JUDGE-03 to close inside Phase 39 after
  the final 100-row human review. Phase 39 therefore edits the active Chapter
  III and Chapter V quality passages, removes the t-test/null-hypothesis/
  p-value claims, inserts verified final descriptive and manual-review
  statistics, compiles the thesis, and scans report/slide/defense sources for
  stale claims before Phase 40 starts.
- This supersedes the older planning handoff that assigned the actual
  prose placement to Phase 42. Phase 42 may still overhaul surrounding prose,
  but it no longer owns or blocks the JUDGE-03 correction.

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
- Output: `data/processed/codex-judge-pass.jsonl` (Codex's judge results), a
  completed final-snapshot manual-check review sheet, descriptive statistics,
  and the Phase 39 Chapter III/Chapter V report correction required by the
  superseding closure decision above.

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
