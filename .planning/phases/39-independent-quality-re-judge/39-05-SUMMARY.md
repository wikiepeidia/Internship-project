---
phase: 39-independent-quality-re-judge
plan: 05
subsystem: data-pipeline
tags: [atomic-promotion, judge-provenance, manifest, rollback, downstream-contract]

requires:
  - phase: 39-independent-quality-re-judge
    provides: 2,097-row zero-unresolved staged candidate with 1,561 carries and 536 fresh verdicts
provides:
  - One atomically promoted, reload-validated canonical corpus and judge release
  - Byte-identical backup of the historical 2,421-row judge bundle
  - Complete current-coordinate judge, merged, summary, and per-row provenance evidence
  - Manifest-derived Phase 40/41 data contract and refreshed active planning clauses
affects: [39-06, 39-07, 40, 41, JUDGE-01, EVAL-08, EVAL-09]

actuals:
  tokens: not_measured
  tasks: 2
  commits: 0

tech-stack:
  added: []
  patterns:
    - byte-preserved historical evidence backup
    - exact carry/fresh provenance composition
    - all-destination rollback transaction
    - manifest-derived downstream contract

key-files:
  created:
    - data/backup/pre-phase39-mislabel-triage/processed/codex-judge-pass.jsonl
    - data/backup/pre-phase39-mislabel-triage/processed/judge-merged.jsonl
    - data/backup/pre-phase39-mislabel-triage/processed/judge-summary.json
    - data/processed/phase39-mislabel-decision-manifest.jsonl
    - data/processed/phase39-mislabel-quarantine.jsonl
    - data/processed/phase39-seed-cap-drops.jsonl
    - data/processed/phase39-final-judge-provenance.jsonl
    - .planning/phases/39-independent-quality-re-judge/39-DOWNSTREAM-DATA-CONTRACT.json
  modified:
    - data/splits/train.jsonl
    - data/splits/val.jsonl
    - data/splits/test.jsonl
    - data/manifests/manifest.json
    - data/processed/codex-judge-pass.jsonl
    - data/processed/judge-merged.jsonl
    - data/processed/judge-summary.json
    - src/data_pipeline/judge_merge.py
    - .planning/PROJECT.md
    - .planning/REQUIREMENTS.md
    - .planning/ROADMAP.md
    - .planning/STATE.md
    - .planning/phases/40-multi-model-training-evidence/40-CONTEXT.md
    - tests/data_pipeline/test_apply_mislabel_triage.py
    - tests/data_pipeline/test_judge_merge.py
    - tests/data_pipeline/test_reconstruct_zalo_direct_catalog.py
    - tests/data_pipeline/test_repair_corpus_full_scale.py

key-decisions:
  - "The final release derives its profile from the recomputed 2,097-row candidate; no obsolete 2,103-row projection was forced."
  - "Historical verdicts are reusable only when their seven-field record digest and score/pass/reason evidence digest match the byte-preserved 2,421-row merged backup."
  - "The manifest hashes the judge/provenance bundle, while the downstream contract hashes the final manifest; no self-referential manifest hash is embedded."
  - "Phase 40 remains blocked by Phase 39's final human/report gates, but Phase 42 is not a training prerequisite."

requirements-completed: [JUDGE-01]

coverage:
  - id: D1
    description: The canonical release has exact corpus, judge, provenance, and descriptive-stat coverage.
    requirement: JUDGE-01
    verification:
      - kind: integration
        ref: judge_merge validate-final-release
        status: pass
    human_judgment: false
  - id: D2
    description: Phase 40/41 active data contracts match the promoted manifest and held-out boundary.
    requirement: EVAL-08/EVAL-09 prerequisite
    verification:
      - kind: test
        ref: test_downstream_contract_matches_live_manifest_and_active_planning_regions
        status: pass
    human_judgment: false

duration: about 2h
completed: 2026-08-21
status: complete
---

# Phase 39 Plan 05: Canonical Release and Downstream Contract Summary

**The semantically converged 2,097-row corpus and its complete judge evidence are now one recoverable canonical release. All live Phase 40/41 data clauses derive from that promoted manifest, while the final human review remains an explicit Phase 39 blocker.**

## Release Gate and Historical Backup

Promotion first re-opened all **35** paths declared by
`phase39-semantic-convergence.json` and independently reproduced:

- 2 semantic iterations;
- 63 restricted repair edges;
- 4 judge-proven semantic quarantines and 2 induced seed-cap drops;
- 1,561 exact carries plus 536 fresh verdicts;
- 2,097 final candidate records; and
- **0 unresolved identities**.

Before replacing any canonical judge path, the complete 2,421-row historical
bundle was copied without JSON reserialization:

| Historical backup | Bytes | SHA-256 |
|---|---:|---|
| `codex-judge-pass.jsonl` | 696,777 | `00f8b4116a6d9cd48317eb7bc7921d44d41c641d1fe9c49aeb8af8fc8e84b142` |
| `judge-merged.jsonl` | 2,522,394 | `e8b4d947271717e56556a74136c57d83dd58589c78699d557999140a9fb55750` |
| `judge-summary.json` | 898 | `b6880a32af17694c4dd8f26528fd2e1d60b9a819f8329be73b3b34704a5eea49` |

Every carried result was then checked against its historical coordinate in
the backed-up merged file. Both the seven-field DatasetRecord digest and the
five-score/pass/reason evidence digest had to match.

## Atomic Promotion and Rollback Proof

Eleven payloads were built and byte-reloaded in staging before the final lock:
three splits, manifest, three migration sidecars, complete judge results,
merged evidence, descriptive summary, and per-record judge provenance.

An injected post-write rejection deliberately failed after all destinations
had been replaced. The transaction restored all seven pre-existing files to
their exact original hashes and removed all four newly-created sidecars. The
first real promotion attempt later found an overly strict post-write
comparison between the numeric validation profile and five additional PASS
markers. That attempt also rolled back completely. The comparison was fixed to
check the numeric profile as a subset and require the PASS markers separately;
the next promotion and full post-write reload succeeded.

Release timestamp: `2026-08-21T19:25:23+07:00`.

## Promoted Corpus

| Split | Rows | Bank | Task scam | Benign | Zalo | Bytes | SHA-256 |
|---|---:|---:|---:|---:|---:|---:|---|
| train | 1,658 | 595 | 306 | 517 | 240 | 1,148,634 | `5fa46382db8fb477ef91ec4ba770bf3f8756df9f98b9950fdf5bc1f6ff402e8b` |
| val | 219 | 76 | 49 | 72 | 22 | 139,120 | `746ae6edb5008a8be8e9ef9d65f89fc44e559f99f28cd8d6a77f203ea5986d3c` |
| test | 220 | 70 | 49 | 66 | 35 | 141,638 | `6f208fb6cd9399b8934225e6a25efd65d49bbb4f4846360837f6835a2561b6d7` |
| **total** | **2,097** | **741** | **404** | **655** | **297** | — | — |

Canonical manifest SHA-256:
`e55d768b5aad05ba6946fbb0e7ed248180186b7cbaad21d257a134e2f1b3dbad`.

Reload validation proves DatasetRecord schema and literal spans, zero
normalized or 0.95 lexical duplicates, whole-seed split disjointness, all four
labels in every split, split-ratio tolerance, and a maximum global seed share
of 167/2,097 = **7.9638%**.

## Complete Final Judge Evidence

The final raw judge file retains the original ten-field result schema and is
ordered by current train/validation/test coordinates. A separate closed
provenance row records the current coordinate, seed, seven-field record digest,
score/pass/reason digest, origin, source hash, and fresh iteration or historical
coordinate.

| Artifact | Rows | SHA-256 |
|---|---:|---|
| final judge results | 2,097 | `688515efbcac4dc5a8070f3ae3172654a908ab7e188c1080d08ad71c9991340e` |
| merged judge evidence | 2,097 | `097924e544502f4ff318f89f47bb2489910928b0eda244f8e55d745253c9ac59` |
| descriptive summary | — | `c3e3ef0c6c8655ccd25a55814aadb99cc9cbf210c4a71c9f4e35a801d78a0d41` |
| per-record provenance | 2,097 | `7cc6f9086a582fd45583d463bab8ce470e3a64d0d786b28afff101219dc097dd` |

- Exact carries: **1,561**
- Fresh final-delta verdicts: **536**
- Passed all five dimensions: **1,395 / 2,097 (66.5236%)**
- Failed one or more dimensions: **702 / 2,097**
- Pass-recomputation mismatches: **0**

The pass rate is descriptive evidence, not a claim that every row is perfect.
The 702 failures remain visible, including realism concerns and the previously
documented human-authority label disagreements.

## Downstream Contract Refresh

`39-DOWNSTREAM-DATA-CONTRACT.json` was generated from the promoted manifest
and split bytes. Its SHA-256 is
`ab5946edda619af665d6ae76b2eccd4e4d13bee99fae83bb04defebf29cb13da`.
It fixes the Phase 40 training boundary to train+validation only and reserves
the exact 220-row test hash for one Phase 41 evaluation.

Only live clauses were refreshed:

- PROJECT active/target-feature held-out and all-data counts;
- REQUIREMENTS EVAL-08 and EVAL-09;
- ROADMAP Phase 40 input/dependency and Phase 41 evaluation clauses;
- STATE current milestone focus, current position, and Phase 40 decision; and
- Phase 40 context prerequisite, hashes, and evaluation boundary.

The dated 2026-08-17 quick-task statement about the then-current 2,403-row
snapshot remains unchanged as historical evidence.

## Verification

- `judge_merge validate-final-release`: **passed** on canonical files.
- Downstream contract focused test: **1 passed**.
- `test_apply_mislabel_triage.py`: **36 passed**.
- `test_judge_merge.py`: **30 passed**.
- Rebound historical Phase 38/F-01 suites: **25 passed**.
- Full `tests/data_pipeline`: **290 passed** in 405.60 seconds.
- `git diff --check`: passed; only line-ending notices were emitted.
- External API, web, plugin, and third-party model calls: **0**.
- Commits/staging operations: **0**, per parent-task instruction.

Protected human artifacts remain byte-identical:

- manual review sheet: `e078b3bf6efd29c8f80f7ea8afaeb1121803c4ce8322fe4a497dd997b9b17743`
- historical triage sheet: `39ca1768c0a114156aece97e7dff2269b074a5125d59b8592f215e3e36415cc7`
- authoritative compact audit: `c408dcf4161d84056b7c22e1fb3e975352a52cd5fbf2b111f11b5dfece0c089c`

## Deviations from Plan

### Final count followed the approved converged candidate

- **Plan text:** retained the earlier 2,103-row projection as an acceptance
  default unless an explicit recomputation changed it.
- **Actual:** Plan 39-04's approved, hash-bound semantic quarantine and cap
  replay changed the final count to 2,097.
- **Resolution:** every release value was derived from the candidate and
  convergence ledger; no older count was hardcoded.

### Historical tests were rebound after canonical promotion

- **Issue:** two Phase 38/F-01 regression modules read mutable `data/splits`
  even though their assertions target the earlier 2,343/2,403-row releases.
- **Resolution:** their fixtures now read the existing byte-identical immutable
  `f01-zalo-direct-candidate-20260817-verified` snapshot. A separate Phase 39
  drift test owns the new live contract.
- **Impact:** historical gates retain their original meaning, while the full
  data-pipeline suite passes against the promoted release.

## Next Phase Readiness

Plan 39-06 can now generate the genuinely final-snapshot 100-row human-review
sheet against manifest SHA-256
`e55d768b5aad05ba6946fbb0e7ed248180186b7cbaad21d257a134e2f1b3dbad`.
Phase 40 must not start until that human checkpoint and Plan 39-07's report
gate close. Phase 42 is not an additional training prerequisite.

## Self-Check: PASSED

---
*Phase: 39-independent-quality-re-judge*
*Completed: 2026-08-21*
