---
phase: 39-independent-quality-re-judge
plan: 03
subsystem: data-pipeline
tags: [llm-judge, sha256, delta-evidence, restartable-batches, semantic-convergence]

requires:
  - phase: 39-independent-quality-re-judge
    provides: reload-validated 2,103-row Plan 39-02 candidate and historical 2,421-row judge evidence
provides:
  - Seven-field exact-record digest and evidence-digest contracts
  - Unique-only historical carry with final-coordinate rebasing and immutable provenance
  - Hash-bound 541-row fresh work queue in nine restartable pending batches
  - Closed semantic-convergence schema requiring later fresh evidence for every repaired digest
  - Local-only delta-judge and restricted semantic-repair operator instructions
affects: [39-04, 39-05, final-judge-evidence, semantic-repair]

actuals:
  tokens: 29501
  tasks: 2
  commits: 0

tech-stack:
  added: []
  patterns: [all-seven-field digest identity, exact-evidence carry, immutable batch completion, recomputing convergence ledger]

key-files:
  created:
    - .planning/codex-final-delta-judge-instructions.md
    - .planning/codex-final-semantic-repair-instructions.md
    - data/processed/phase39-final-judge-carry.jsonl
    - data/processed/phase39-final-judge-delta-targets.jsonl
    - data/processed/phase39-final-judge-batches/iteration-00/
  modified:
    - src/data_pipeline/judge_merge.py
    - tests/data_pipeline/test_judge_merge.py

key-decisions:
  - "Historical scores carry only from one unique exact digest over all seven DatasetRecord fields; ambiguous history becomes fresh work."
  - "Carried scores/reason/pass remain unchanged, while current coordinates replace historical coordinates and the old coordinates remain provenance only."
  - "Batch preparation creates no result file and no prefabricated verdict; only a validated result can atomically move one manifest entry to complete."
  - "A semantic convergence claim is invalid unless every declared artifact re-hashes and every changed after-digest has a verdict in a later iteration."

patterns-established:
  - "Queue identity: (final split, final row_index, seed_id, seven-field record_digest)."
  - "Restart contract: completed target/result bytes are immutable; pending partial/conflicting output never becomes complete."

requirements-completed: []

coverage:
  - id: D1
    description: Exact-record carry and fresh-delta preparation is closed, digest-bound, and exhaustive over the staged final snapshot.
    requirement: JUDGE-01
    verification:
      - kind: unit
        ref: tests/data_pipeline/test_judge_merge.py#digest_carry_delta_batch_convergence (13 passed)
        status: pass
      - kind: integration
        ref: python -m src.data_pipeline.judge_merge validate-batches --require-status pending (1,562 carry + 541 delta = 2,103)
        status: pass
    human_judgment: false
  - id: D2
    description: Nine deterministic pending batches contain the full 541-row queue and no fabricated result file.
    requirement: JUDGE-01
    verification:
      - kind: integration
        ref: two identical python -m src.data_pipeline.judge_merge prepare-final runs reproduced all queue hashes
        status: pass
      - kind: integration
        ref: filesystem audit found zero batch-*-results.jsonl files
        status: pass
    human_judgment: false
  - id: D3
    description: Actual row-by-row fresh judgment and semantic decisions remain the next plan's model-judgment work.
    requirement: JUDGE-01
    verification: []
    human_judgment: true
    rationale: Tooling deliberately cannot infer or prefill the 541 fresh judgments or semantic keep/repair decisions.

duration: about 20min
completed: 2026-08-21
status: complete
---

# Phase 39 Plan 03: Exact Carry and Fresh-Delta Queue Summary

**The 2,103-row staged snapshot now has an exact, reproducible partition of 1,562 historical carries and 541 genuinely fresh judgments, with all fresh work split into nine immutable pending batches.**

## Performance

- **Duration:** about 20 minutes
- **Completed:** 2026-08-21T18:26:04+07:00
- **Tasks:** 2
- **Implementation/evidence files:** 5 logical deliverables plus 12 ignored generated queue artifacts

## Accomplishments

- Added a Pydantic-validated SHA-256 identity over all seven `DatasetRecord` fields. A change to text, label, risk tier, spans, XAI explanation, source, or seed ID forces fresh judgment.
- Added a separate judge-evidence digest over all five scores, declared pass, and reason.
- Rebased unique exact historical verdicts to current final coordinates while retaining old coordinates and all source hashes only in provenance.
- Routed ambiguous historical digests to fresh targets and proved carry/delta sets are disjoint and exhaustive.
- Added strict fresh-result, batch-manifest, artifact-reference, repair-edge, and semantic-convergence models.
- Added fail-closed batch completion: a missing, partial, duplicated, wrong-target, or hash-conflicting result cannot update pending state; a valid completed batch is restart-idempotent.
- Authored local-only instructions that preserve the historical five-score rubric and explicitly prohibit scripted, copied, default, historical, or externally sourced fresh verdicts.
- Materialized the real locked queue and reproduced it byte-for-byte on a second run.

## Task Commits

No staging or commits were performed. The parent task explicitly prohibited
`git add`, commit, stash, checkout, and reset operations. All Plan 39-03 work
remains in the shared worktree for the parent orchestrator and user to inspect.

## Locked Queue Result

| Artifact | Rows | SHA-256 |
|---|---:|---|
| exact carry | 1,562 | `6294b03facb5b0d0dd107e48425b131459ac27777d3d299fc1e4ae0a08ad5032` |
| aggregate fresh targets | 541 | `a2afabbca907442c708669f791617dd5f59ecf4f8091a4ffc66287eb875da9ba` |
| iteration-00 manifest | 9 batches | `be537ed4846365135c7bb08797ed57ebbaefb8976aa89466ea3a29c5a1ac8bab` |
| Plan 39-02 candidate manifest | 2,103 | `4ccd1fd828dc9d76c659be84283ed1af00458831f8886a30f34d1bf529040a23` |
| historical merged judge | 2,421 | `e8b4d947271717e56556a74136c57d83dd58589c78699d557999140a9fb55750` |

Batch counts are exactly `64/64/64/64/64/64/64/64/29`. All nine statuses are
`pending`; all result hashes/counts are null; and zero result files exist.

## Files Created/Modified

- `src/data_pipeline/judge_merge.py` — retained the old same-snapshot merge CLI and added exact carry/delta preparation, strict batch state, completion validation, semantic convergence validation, and new subcommands.
- `tests/data_pipeline/test_judge_merge.py` — added all-field digest, carry/fresh, ambiguity, rebasing, batching, restart/conflict, and convergence regressions.
- `.planning/codex-final-delta-judge-instructions.md` — exact current-session scoring and per-batch completion contract.
- `.planning/codex-final-semantic-repair-instructions.md` — explicit keep/repair contract limited to risk tier, literal spans, and grounded XAI.
- `data/processed/phase39-final-judge-carry.jsonl` — carried result plus provenance records.
- `data/processed/phase39-final-judge-delta-targets.jsonl` — current-coordinate seven-field targets with exact record digests.
- `data/processed/phase39-final-judge-batches/iteration-00/` — manifest plus nine target JSONL files; no result JSONL.

## Verification

- Focused tracer: **13 passed**.
- Full `test_judge_merge.py`: **26 passed**.
- Full data-pipeline regression: **275 passed**, with two unchanged third-party SWIG deprecation warnings.
- Real pending-bundle validator: **1,562 carries + 541 targets = 2,103**, nine expected batch sizes, all hashes reproduced.
- Real preparation rerun: identical carry, target, and manifest hashes; no overwrite/conflict and no result generated.
- `python -m compileall` and `git diff --check`: passed.

Input and protected artifact hashes stayed byte-identical:

- live train: `6454a271c6133f1ebbd41010390b8ea6ceae0a8ab0a75b2ab545099db3319ee8`
- live val: `7adfe8cd9a124dbb3d87046bb32f9fbd127d3e344c45be77c8bb9efa700aaa75`
- live test: `019aec39979429ca8005dd299d2ddaf7d3ecfdade259eecc4d3129adaed25938`
- live manifest: `4794cedae52cc5531083a569c3e63c419335a0544f365f4a4d6245048efc2b90`
- manual review sheet: `e078b3bf6efd29c8f80f7ea8afaeb1121803c4ce8322fe4a497dd997b9b17743`
- historical triage sheet: `39ca1768c0a114156aece97e7dff2269b074a5125d59b8592f215e3e36415cc7`
- authoritative compact audit: `c408dcf4161d84056b7c22e1fb3e975352a52cd5fbf2b111f11b5dfece0c089c`
- candidate splits: `9aff01cc...` / `7eaafe13...` / `84ffc062...`

## Decisions Made

- Full-record digest uniqueness, not seed/text or historical coordinates, is the only carry authorization.
- Fresh results include `record_digest` in addition to the old coordinate/seed/five-score contract, so a result cannot silently bind a changed target.
- Explicit semantic keeps repeat the three current permitted values; changed decisions create before/after digest edges and require a later fresh judgment.
- Generic convergence declarations are hash-checked, and any declared Plan 39 batch manifest is also structurally revalidated when its version is recognized.

## Deviations from Plan

### User-directed commit deferral

- **Issue:** Standard GSD execution expects task and summary commits.
- **Resolution:** The parent task explicitly prohibited staging and commits. No Git index or history operation was performed.
- **Impact:** Implementation, artifact, and test acceptance pass; repository-history acceptance is intentionally not claimed.

## Issues Encountered

None remain. Workspace-local pytest base directories were used because the
managed Windows sandbox does not reliably allow pytest's default `%TEMP%`
location; those temporary directories were verified inside the workspace and
removed after the runs.

## User Setup Required

None. Queue preparation was entirely local and made zero external API calls.

## Next Phase Readiness

- Plan 39-04 can judge batches 0001 through 0009 under the prepared instructions and atomically complete each manifest entry.
- Semantic repair/re-judgment can use the closed convergence schema; promotion remains blocked until zero unresolved identities are independently verified.
- The canonical 2,403-row live corpus, live manifest, historical judge evidence, and all protected human sheets remain unchanged.

## Self-Check: PASSED

---
*Phase: 39-independent-quality-re-judge*
*Completed: 2026-08-21*
