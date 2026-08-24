---
phase: 39-independent-quality-re-judge
plan: 04
subsystem: data-pipeline
tags: [codex-judge, semantic-repair, quarantine, exact-evidence, convergence]

requires:
  - phase: 39-independent-quality-re-judge
    provides: hash-bound 1,562-carry / 541-fresh queue over the staged 2,103-row candidate
provides:
  - 541 independently authored and validated initial Codex judgments in nine restartable batches
  - Two bounded semantic repair/re-judge iterations with 63 exact before/after digest edges
  - Fail-closed machine-readable quarantine of four fresh-judge-proven label defects
  - Deterministic 8% cap replay, two recorded cap drops, and whole-seed re-split to 2,097 rows
  - Exact final-coordinate evidence partition of 1,561 carries plus 536 fresh verdicts
  - Recomputing zero-unresolved semantic convergence ledger over 35 artifacts
affects: [39-05, 39-06, JUDGE-01, final-corpus-promotion, report-quality-statistics]

actuals:
  tokens: not_measured
  tasks: 2
  commits: 0

tech-stack:
  added: []
  patterns:
    - current-session row-by-row judgment
    - restricted three-field semantic repair
    - fresh-verdict-after-digest
    - judge-proven semantic quarantine
    - deterministic cap and whole-seed split replay
    - exact final-coordinate evidence rebasing

key-files:
  created:
    - data/processed/phase39-final-judge-batches/iteration-00/batch-0001-results.jsonl
    - data/processed/phase39-final-judge-batches/iteration-00/batch-0002-results.jsonl
    - data/processed/phase39-final-judge-batches/iteration-00/batch-0003-results.jsonl
    - data/processed/phase39-final-judge-batches/iteration-00/batch-0004-results.jsonl
    - data/processed/phase39-final-judge-batches/iteration-00/batch-0005-results.jsonl
    - data/processed/phase39-final-judge-batches/iteration-00/batch-0006-results.jsonl
    - data/processed/phase39-final-judge-batches/iteration-00/batch-0007-results.jsonl
    - data/processed/phase39-final-judge-batches/iteration-00/batch-0008-results.jsonl
    - data/processed/phase39-final-judge-batches/iteration-00/batch-0009-results.jsonl
    - data/processed/phase39-semantic-repairs/iteration-00.jsonl
    - data/processed/phase39-semantic-repairs/iteration-01.jsonl
    - data/processed/phase39-final-judge-batches/iteration-01/
    - data/processed/phase39-final-judge-batches/iteration-02/
    - data/processed/phase39-semantic-quarantine/
    - data/processed/phase39-final-evidence/carry.jsonl
    - data/processed/phase39-semantic-convergence.json
  modified:
    - data/processed/codex-final-delta-judge.jsonl
    - data/processed/phase39-mislabel-candidate/manifest.json
    - data/processed/phase39-mislabel-candidate/splits/train.jsonl
    - data/processed/phase39-mislabel-candidate/splits/val.jsonl
    - data/processed/phase39-mislabel-candidate/splits/test.jsonl
    - src/data_pipeline/apply_mislabel_triage.py
    - src/data_pipeline/judge_merge.py
    - tests/data_pipeline/test_apply_mislabel_triage.py
    - tests/data_pipeline/test_judge_merge.py

key-decisions:
  - "Human-approved relabels remain authoritative even where the fresh judge disagrees; the low label score and reason remain visible rather than being rewritten into agreement."
  - "The four wedding-collection Zalo rows contained no fraud or impersonation cue and could not be repaired through risk tier, spans, or XAI; they were quarantined only after explicit user authorization."
  - "Removing those four rows triggered the existing iterative 8% cap, so the two additional deterministic cap drops are recorded as separate full-record artifacts."
  - "Final evidence is recomposed at new coordinates by exact digest: only removed records lose evidence, unchanged fresh verdicts retain their scores/reasons, and repaired digests retain their later verdicts."

requirements-completed: []

coverage:
  - id: D1
    description: Every initial fresh target has a current-session five-score verdict in an immutable validated batch.
    requirement: JUDGE-01
    verification:
      - kind: integration
        ref: iteration-00 complete manifest, 541 targets in 64/64/64/64/64/64/64/64/29 batches
        status: pass
    human_judgment: true
  - id: D2
    description: Every permitted semantic change is exact-digest bound and has a later fresh verdict.
    requirement: JUDGE-01
    verification:
      - kind: integration
        ref: phase39-semantic-convergence.json, 63 repair edges across two iterations
        status: pass
    human_judgment: true
  - id: D3
    description: The authorized four-row quarantine and two cap drops reproduce from immutable source artifacts.
    requirement: JUDGE-01
    verification:
      - kind: unit
        ref: tests/data_pipeline/test_apply_mislabel_triage.py and test_judge_merge.py
        status: pass
      - kind: integration
        ref: validate-convergence --require-zero-unresolved
        status: pass
    human_judgment: false

duration: about 2h
completed: 2026-08-21
status: complete
---

# Phase 39 Plan 04: Final Codex Judgment and Semantic Convergence Summary

**All 541 initial fresh targets were judged row by row in this Codex session. Sixty-three permitted semantic changes received later fresh verdicts, four genuinely unrepairable label defects were explicitly quarantined, and the resulting 2,097-row staged candidate now has a recomputing zero-unresolved convergence ledger.**

## Performance

- **Duration:** about 2 hours
- **Completed:** 2026-08-21
- **Initial judgments:** 541
- **Semantic repair edges:** 63 across two iterations
- **Judge-proven quarantines:** 4
- **Additional deterministic cap drops:** 2
- **Commits:** 0, by explicit parent-task instruction
- **External API/plugin/web/third-party model calls:** 0

## Initial Fresh Judgment

All nine iteration-00 result files were authored from their full target records,
validated against exact target order/coordinates/digests, and only then marked
complete. The complete manifest SHA-256 is
`9c9a2b68cab132b077c8ba4c1b9513246bba54ed0948e5f5dbf9ca065ea89bd1`.

| Batch | Rows | Pass | Fail |
|---|---:|---:|---:|
| 0001 | 64 | 41 | 23 |
| 0002 | 64 | 42 | 22 |
| 0003 | 64 | 58 | 6 |
| 0004 | 64 | 63 | 1 |
| 0005 | 64 | 50 | 14 |
| 0006 | 64 | 40 | 24 |
| 0007 | 64 | 61 | 3 |
| 0008 | 64 | 56 | 8 |
| 0009 | 29 | 28 | 1 |
| **Total** | **541** | **439** | **102** |

Initial dimension averages and below-3 counts were:

| Dimension | Mean | Score below 3 |
|---|---:|---:|
| realism | 3.7246 | 63 |
| label correctness | 4.6802 | 14 |
| code-switch naturalness | 4.5360 | 3 |
| risk-tier correctness | 4.6802 | 29 |
| suspicious-span accuracy | 4.6858 | 32 |

These failures remain evidence. They were not default-passed, suppressed, or
rewritten to improve aggregate statistics.

## Semantic Repair and Re-Judgment

Iteration 00 reviewed an explicit union of **84 identities**: all 57 admitted
human relabels, every fresh risk/span/label defect, and 20 additional concrete
XAI overreach findings. Its 84 target and decision artifacts have SHA-256
`9cdf07ffc16880eb3442ab161553284724da73b3607bea3cde6bf870d49d5c5c`
and `f3d4dcb72f5cc31888934bf996db6cc9bbdcf5b68c0d8aaa38a87df7982dbf67`.

- 62 decisions changed only `risk_tier`, `suspicious_spans`, or
  `xai_explanation` and produced exact before/after digest edges.
- Iteration 01 freshly re-judged all 62 after-digests: 49 pass and 13 fail.
  All span defects were resolved. Twelve label failures were retained as honest
  human-authority disagreements; two rows still failed realism; one Shopee row
  exposed a remaining permitted risk-tier defect.
- Iteration 01 repaired that one Shopee row to benign risk, empty spans, and a
  grounded explanation. Iteration 02 freshly judged the new after-digest. Its
  risk, span, and XAI fields passed; the human-authoritative label disagreement
  remained visible.

| Artifact | Rows | SHA-256 |
|---|---:|---|
| iteration-01 manifest | 62 targets | `76df5490ee4fc47fb02e36592559bbdc8214546114e03f81c3e450bd32a3b379` |
| iteration-01 results | 62 | `e07763029715b640fcf08ac22dc18cb8cefc942e6b4dcbb619ad80815cfcb5aa` |
| iteration-01 semantic decisions | 1 | `e8b3412fda2a98c8310486c02618f3d10fe6d096c6491f14b2dceda8fc47d917` |
| iteration-02 manifest | 1 target | `916c6669b62caad08cddc1e78ba2fbd7c63face2b420fa8938122483a7e144ae` |
| iteration-02 result | 1 | `387d760f8c47d4eca004448c213290e8ba66cf538a0373c760cab3e152d3c3a7` |

## Authorized Semantic Quarantine

Fresh judgment proved that four rows under `seed_546e81dc221d` described only
ordinary class wedding contributions. Their `zalo_social_engineering` labels
had no fraud/impersonation cue, and the locked semantic repair contract forbids
rewriting text or labels. After explicit authorization, they were quarantined
as `fresh_judge_unrepairable_label` with their complete records and bound
failed verdicts preserved.

The four-row artifact has SHA-256
`c0c1f99b306ffa7f6f1714500c12639fc3a4da03807e45162383c6f71521e4ee`.
Replaying the iterative 8% cap then deterministically removed two more rows:

- `77943909faf965a66a0a44f828aaf09c3237e28983bd40ff6b22ba5de26f401b`
- `e9afa8c5b338db34e96e6b831c6c624ff5066b2250cae2e188aa54f4f0ab7582`

Their full-record cap-drop artifact has SHA-256
`59af75b56c9118b772060d31eb0ec498a664573dcf4b46ed12a4c71c16d2a024`.
The validator reopens the immutable 2,103-row source snapshot, checks all four
fresh verdict bindings, removes exactly those rows, recomputes exactly two cap
drops, replays `phase39-mislabel-triage-v1` whole-seed assignment, and requires
byte-for-byte equality with the staged candidate.

## Final Staged Candidate

| Split | Rows | Bank | Task scam | Benign | Zalo | SHA-256 |
|---|---:|---:|---:|---:|---:|---|
| train | 1,658 | 595 | 306 | 517 | 240 | `5fa46382db8fb477ef91ec4ba770bf3f8756df9f98b9950fdf5bc1f6ff402e8b` |
| val | 219 | 76 | 49 | 72 | 22 | `746ae6edb5008a8be8e9ef9d65f89fc44e559f99f28cd8d6a77f203ea5986d3c` |
| test | 220 | 70 | 49 | 66 | 35 | `6f208fb6cd9399b8934225e6a25efd65d49bbb4f4846360837f6835a2561b6d7` |
| **total** | **2,097** | **741** | **404** | **655** | **297** | — |

- Candidate manifest SHA-256:
  `2ee448d2497aebbd7a0fe66668357bc1b71083c8728cde75fc194df20d5b4645`
- Maximum seed concentration: 167/2,097 = 7.9638%
- No cross-split seed leakage
- No invalid/non-literal suspicious span
- No normalized or 0.95 lexical near-duplicate
- All four labels remain represented in every split
- Split ratios remain within the existing tolerance

## Final Evidence and Convergence

The final coordinate/digest partition is exact and exhaustive:

| Evidence | Rows | SHA-256 |
|---|---:|---|
| final exact carries | 1,561 | `593b34ab8eb01d817b849e26aea1022dac422d2a1ef16822ffe44f5cb24b5ea8` |
| final fresh results | 536 | `8c152b519ca70ac9329b382dcafd8a91f09fcc8f0ed81600cbed0e6b98b584d5` |
| **total** | **2,097** | — |

One removed cap row came from the initial carry set; the four quarantined rows
and the other cap row came from the initial fresh set. Removed digests have no
final evidence row. Every surviving record has exactly one verdict rebased to
its final coordinate, and every repaired digest uses its later fresh verdict.

`phase39-semantic-convergence.json` has SHA-256
`58bb2a814a052f5be78e026694a7f9a11d155977b98e67f40bcb094d98a01dd1`.
The recomputing validator opened 35 declared artifacts and reported:

- 2 semantic iterations
- 63 exact repair edges
- 4 quarantine records plus 2 cap drops
- 2,097 final candidate records
- 536 final fresh results
- **0 unresolved identities**

Important: zero unresolved refers to the bounded semantic consistency work. It
does **not** mean every judge verdict is a pass. The final fresh file contains
461 pass and 75 fail verdicts. Remaining failures—especially realism findings
and reviewer-authoritative label disagreements—must remain visible in Phase 39
quality statistics and must not be described as a perfect corpus.

## Tooling Changes

- `apply_mislabel_triage.py` now supports a closed
  `phase39-semantic-quarantine-v1` contract. The original locked 2,103-row path
  remains unchanged when no contract is present.
- The quarantine validator re-hashes repository-relative artifacts, validates
  the original locked source profile, binds full records to failing fresh label
  verdicts, and reproduces removal/cap/split output and manifest/run hashes.
- `judge_merge.py` now records an explicit final expected profile, semantic
  quarantine transition, final carry artifact, exact final coordinate coverage,
  and permitted supersession/removal lineage for repaired digests.
- Both validators reject alternate CLI evidence paths, stale carry provenance,
  unexpected evidence for removed rows, missing later verdicts, and profile or
  artifact drift.

## Verification

- Focused Phase 39 modules: **62 passed** in 118.73s.
- Final `test_judge_merge.py` rerun after evidence-path hardening: **27 passed**.
- Full `tests/data_pipeline`: **286 passed** in 185.96s.
- Only two unchanged third-party SWIG deprecation warnings were emitted.
- `git diff --check`: passed; only line-ending notices were printed.
- Exact convergence command with `--require-zero-unresolved`: passed.

Protected inputs remain byte-identical:

- live train: `6454a271c6133f1ebbd41010390b8ea6ceae0a8ab0a75b2ab545099db3319ee8`
- live val: `7adfe8cd9a124dbb3d87046bb32f9fbd127d3e344c45be77c8bb9efa700aaa75`
- live test: `019aec39979429ca8005dd299d2ddaf7d3ecfdade259eecc4d3129adaed25938`
- live manifest: `4794cedae52cc5531083a569c3e63c419335a0544f365f4a4d6245048efc2b90`
- manual review sheet: `e078b3bf6efd29c8f80f7ea8afaeb1121803c4ce8322fe4a497dd997b9b17743`
- historical triage sheet: `39ca1768c0a114156aece97e7dff2269b074a5125d59b8592f215e3e36415cc7`
- authoritative compact audit: `c408dcf4161d84056b7c22e1fb3e975352a52cd5fbf2b111f11b5dfece0c089c`

## Task Commits

No staging or commits were performed. The parent task explicitly prohibited
`git add`, commit, stash, checkout, and reset operations. All work remains in
the shared worktree for inspection.

## Deviations from Plan

### Judge-proven rows required an explicit disposition

- **Issue:** Four generated wedding-collection messages had a malicious Zalo
  label but no fraud cue. Risk/span/XAI edits could not repair that label defect.
- **Resolution:** Execution first left them unresolved and stopped promotion.
  After explicit user authorization, a candidate-only, machine-audited
  quarantine removed those four, replayed the 8% cap, and recorded two induced
  drops before re-splitting.
- **Impact:** Final candidate count is 2,097 rather than 2,103. No live canonical
  row or historical audit claim was changed.

### Iteration-01 carry provenance was tightened before sealing

- **Issue:** The first repair queue draft contained only 62 changed targets and
  an empty carry, so the exhaustive bundle validator rejected it.
- **Resolution:** A 2,103-row immutable prior-evidence snapshot was constructed;
  iteration 01 was rebuilt as 2,041 exact carries plus 62 fresh targets before
  its result was accepted.
- **Impact:** No judgment or candidate row was lost. The strict validator caught
  the incomplete provenance before the batch was marked complete.

### Managed Windows pytest temporary directory

- **Issue:** pytest could not access its default `%TEMP%` numbered directory.
- **Resolution:** Tests used unique workspace-local base directories, which were
  safely removed after completion.
- **Impact:** None on source, data, or test results.

## Next Phase Readiness

- Plan 39-05 may consume the validated 2,097-row candidate, 1,561 final carries,
  536 final fresh verdicts, and zero-unresolved convergence ledger for its
  atomic promotion gate.
- Promotion must use the new explicit expected profile; it must not silently
  restore the old 2,103-row lock or omit the four quarantine/two cap-drop audit
  artifacts.
- The 75 final fresh `pass:false` verdicts remain reportable evidence. Later
  Phase 39 work should summarize their realism and human-authority disagreement
  categories honestly rather than claiming universal judge approval.
- The live corpus, live manifest, historical judge evidence, and protected
  human sheets remain untouched and ready for the Plan 39-05 transaction.

## Self-Check: PASSED

---
*Phase: 39-independent-quality-re-judge*
*Completed: 2026-08-21*
