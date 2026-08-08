# Phase 38: Corpus Repair & Split Governance - Context

**Gathered:** 2026-08-08
**Status:** Ready for planning

<domain>
## Phase Boundary

The synthetic corpus's structural bugs (seed concentration, invalid evidence
spans, cross-split seed leakage) are repaired and re-split by seed-group hash
against concrete, checkable acceptance gates. This phase produces a trustworthy
data foundation for all downstream re-judging, training, and evaluation work —
it does not itself run any model training or judging.

</domain>

<decisions>
## Implementation Decisions

### Split Ratio & Grouping
- Split ratio: 80/10/10 (train/val/test), by row count.
- Grouping key: `seed_id` — every row belonging to the same seed group must
  land in exactly one split.
- Group-to-split assignment: deterministic hash of `seed_id` (not
  `random.shuffle` with a stored seed) so re-running the split logic is
  reproducible without depending on RNG state.
- Stratification: best-effort per-class balance within the group constraint —
  greedily assign groups while tracking running per-class counts, preferring
  assignments that keep the four classes' proportions close across splits.
  Perfect stratification is not required when it would break group integrity.

### Seed Concentration Cap
- Target cap: no single `seed_id` may account for more than 8% of the final
  corpus (down from the current ~25% for the dominant seed).
- Enforcement: drop excess rows from over-represented seed groups rather than
  generating new seeds or new synthetic rows.
- "Same seed" is defined as an exact `seed_id` match — no fuzzy/near-duplicate
  seed-text clustering.
- When trimming an over-represented seed group down to the cap, keep the most
  textually diverse subset (via the existing `lexical_dedup` distance
  function) and drop the rest, rather than arbitrary/first-N truncation.

### Invalid Evidence Span Repair
- For the 131 rows with invalid evidence spans: attempt automatic
  re-extraction of a valid span from the row's existing `text` +
  `xai_explanation` fields first (no new API calls, no data loss where
  avoidable).
- Validation rule stays exact-substring: a span is valid only if it is an
  exact substring of `text` (matches the existing schema's intent — no
  fuzzy/normalized matching).
- If no valid span can be recovered after the repair attempt, drop the row
  entirely rather than keeping it with an empty span list (an empty span list
  would weaken the evidence-grounded design principle this whole system is
  built on).
- This repair logic lives in a new one-off script under `src/data_pipeline/`
  — it is a one-time corpus repair, not a permanent addition to the
  generation-time validators.

### Manifest & Recovery Narrative
- The repair's output manifest extends the project's existing SHA-256
  manifest pattern (same fields/style as the manifests already produced
  elsewhere in `src/data_pipeline/versioning/`), not a new ad-hoc format.
- Deliverable includes a standalone markdown snippet containing the drafted
  `task_scam` 0.44→0.871 recovery narrative, grounded in the real Phase 7a
  evidence artifacts, ready to paste into the report's Data Construction
  chapter during Phase 42 (Report Overhaul) — this phase drafts it, Phase 42
  places it.
- The repair script is committed under `src/data_pipeline/` like the rest of
  the pipeline, not left as an uncommitted scratch script.
- Old pre-repair corpus files (`data/synthetic/recovered-balanced.jsonl`,
  `data/splits/recovered-balanced/*.jsonl`) are kept as a backup/reference,
  not deleted, consistent with how this project has handled prior data
  changes (e.g. the `data/backup/` directory already holds earlier snapshots).

### Claude's Discretion
None — all four grey areas were accepted as recommended without changes.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/data_pipeline/processing/dedup.py::lexical_dedup` — existing
  near-duplicate detection, reusable for the "keep most diverse subset when
  trimming an over-represented seed" rule.
- `src/data_pipeline/versioning/manifest.py` — existing SHA-256 manifest
  pattern to extend rather than reinvent.
- `src/data_pipeline/schemas.py::DatasetRecord` — the schema `text`, `label`,
  `risk_tier`, `suspicious_spans`, `xai_explanation`, `source`, `seed_id`
  fields the repair script reads/writes against.

### Established Patterns
- Dataset builds are versioned via manifests with SHA-256 content hashes
  (established since Phase 1); the repair output should follow the same
  discipline so it can be cited in the report the same way prior artifacts
  already are.
- Prior data-recovery work (Phase 7a, `task-scam-recovery-2026-05-28`) is the
  precedent for how this project documents a real data problem and its fix —
  this phase's recovery-narrative deliverable follows that same honest,
  evidenced pattern rather than inventing new framing.

### Integration Points
- Input: `data/synthetic/recovered-balanced.jsonl` (3,000 rows) pooled with
  the reserved `data/splits/recovered-balanced/test.jsonl` (413 rows).
- Output: new `train.jsonl` / `val.jsonl` / `test.jsonl` at a new, clearly
  versioned path (not overwriting the existing `recovered-balanced/` split
  directory, per the "keep old files as backup" decision above) plus a
  manifest and the recovery-narrative markdown snippet.
- Downstream consumers: Phase 39 (independent quality re-judge) reads the
  repaired corpus; Phase 40 (training) reads the new split files.

</code_context>

<specifics>
## Specific Ideas

No specific implementation references beyond the four decision areas above —
this phase follows the established manifest/versioning conventions already
present in the codebase.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope. (The independent Codex judge
pass and manual 100-example human check are explicitly Phase 39's scope, not
this phase's.)

</deferred>
