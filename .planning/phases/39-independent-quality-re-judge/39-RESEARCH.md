# Phase 39: Independent Quality Re-Judge - Research

**Researched:** 2026-08-20
**Domain:** Fail-closed dataset-label migration, audit provenance, and delta re-judging
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

The following block is copied verbatim from `39-CONTEXT.md` as the planning constraint.

DATA_39C7A2F1_START

### Locked Decisions

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
- This supersedes the older planning handoff that assigned the actual prose
  placement to Phase 42. Phase 42 may still overhaul surrounding prose, but
  it no longer owns or blocks the JUDGE-03 correction.

### the agent's Discretion
None beyond the above — all grey areas were resolved explicitly, including
the mid-discussion data-consolidation scope change.

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope (the data-directory
consolidation, while not originally scoped as part of Phase 39, was executed
immediately since it's a direct prerequisite for pointing the judge at the
right files, and blocks Phase 40 too if left undone).

DATA_39C7A2F1_END

[VERIFIED: `.planning/phases/39-independent-quality-re-judge/39-CONTEXT.md:14-132`]
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|---|---|---|
| JUDGE-01 | Full repaired corpus judged by an independent third model family via `.planning/codex-judge-instructions.md`, producing a joinable structured result file. | Exact-record carry-forward plus a fresh 541-row delta pass yields honest final-snapshot coverage for all 2,103 projected rows. |
| JUDGE-02 | Manual 100-example human check completed by a Vietnamese-fluent reviewer, results captured for report inclusion. | The current sheet is 98/100 and stale; generate a final-snapshot sheet, carry only byte-equivalent evidence, and obtain human decisions for every remainder. |
| JUDGE-03 | T-test removed from the report; replaced with descriptive quality stats plus the manual-check results. | Produce immutable final stats, complete the human check, edit both active report chapters in Phase 39, compile, and scan report/slide/defense sources before Phase 40. |

[VERIFIED: `.planning/REQUIREMENTS.md:647-651`; the three requirement strings above are verbatim.]
</phase_requirements>

## Summary

The human triage artifact contains all 324 numbered decisions. A strict local parse finds `91` drops and `233` relabels: `48` to `bank_impersonation`, `8` to `benign`, and `177` to `zalo_social_engineering`. Two spellings require transparent normalization only: candidate 103's `Drop` means `Drop row`, and candidate 320's `Beigin` means `benign`; every raw value must remain in the audit trail. [VERIFIED: local read-only parse of `.planning/phases/39-independent-quality-re-judge/MISLABEL triage.md:1-971`; anomalous raw values at lines 307 and 958]

The decisive risk is lineage, not label semantics: `176/177` proposed Zalo relabels are rows from the single seed `seed_157ce0adb043`; the sole independent Zalo relabel is candidate 47 from `seed_c6c8772ac332`. Including all 176 would create a 176/477 (36.9%) single-seed share inside the Zalo class and repeat the exact dominance failure Phase 38 repaired. Quarantine all 176 dominant-seed Zalo relabels, retain their human decisions in provenance, include the one independent Zalo relabel, and regenerate independent roots only in a later data-generation phase. [VERIFIED: candidate identity headers in `39-mislabel-triage-sheet.md:747`, `:1835-4655`; local full-sheet seed aggregation]

On the locked 2,403-row input, that policy plus the 91 human drops and 57 retained relabels projects 2,136 rows. Reapplying the existing global 8% seed cap deterministically removes 33 more rows, leaving 2,103 rows with class counts `743/655/404/301` for `bank_impersonation/benign/task_scam/zalo_social_engineering`. A whole-seed deterministic 80/10/10 reassignment with a new salt projects `1,665/218/220` rows and preserves all four labels in every split. [VERIFIED: read-only execution of `enforce_seed_cap()` and `assign_stratified_group_split()` over current canonical inputs and parsed decisions; source algorithms at `src/data_pipeline/repair_corpus_split_governance.py:230-450`]

**Primary recommendation:** implement one fail-closed migration that reconstructs candidate identity from the historical merged JSONL, binds by `(seed_id, SHA256(canonicalized full text))`, quarantines the 176 non-independent Zalo rows, stages and revalidates a 2,103-row candidate bundle, then atomically promotes splits, manifest, quarantine, and audit artifacts together.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|---|---|---|---|
| Parse and normalize human decisions | Data pipeline | Storage | Decisions are untrusted local input and require strict schema/coverage checks. |
| Resolve rows without stale indices | Data pipeline | Storage | Identity comes from seed plus full text; split positions are regenerated outputs. |
| Quarantine dominant lineage | Data pipeline | Storage | It is a corpus-admission policy, not a label rewrite. |
| Validate and re-split | Data pipeline | Storage | Existing schema, cap, duplicate, and group-split gates own these invariants. |
| Promote candidate and provenance | Storage | Data pipeline | All canonical bytes must move as one rollback-capable bundle. |
| Final judge/manual evidence | Data pipeline | Report | Evidence is computed here; prose placement is downstream. |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---|---:|---|---|
| Python stdlib (`json`, `hashlib`, `unicodedata`, `pathlib`, `re`, `collections`) | project runtime | Strict parsing, canonical identities, hashes, file I/O | Already used; no package install or network path. |
| Pydantic | installed project dependency | Validate every final `DatasetRecord` | The source schema is already authoritative. |
| Existing Phase 38/39 helpers | in-repo | Seed cap, whole-group split, duplicate checks, atomic promotion | Reuses tested project semantics instead of creating parallel rules. |

The authoritative record enums are `label = {"bank_impersonation", "zalo_social_engineering", "task_scam", "benign"}`, `risk_tier = {"benign", "suspicious", "high-risk"}`, and `source = {"ncsc_seed", "synthetic_claude", "synthetic_gemini", "synthetic_openrouter", "synthetic_deepseek", "synthetic_openai_compatible"}`. [VERIFIED: `src/data_pipeline/schemas.py:82-114`; values reproduced verbatim]

**Installation:** none. No package-legitimacy gate is triggered.

## Architecture Patterns

### System Architecture Diagram

```text
MISLABEL triage.md (324 raw decisions)
             + historical judge-merged.jsonl
             + locked live splits/manifest
                         |
              strict parse + coverage
                         |
        seed_id + SHA256(canonical full text)
                         |
       +-----------------+------------------+
       |                                    |
91 drops + 57 relabels          176 Zalo rows from one seed
       |                                    |
       v                                    v
 admitted pool                    immutable quarantine artifact
       |
global 8% cap -> whole-seed 80/10/10 split
       |
schema/span/dedup/leakage/class-support/hash validation
       |
staged bundle -> atomic promote/rollback -> canonical final snapshot
       |
exact-record judge carry (1,562) + fresh delta judge (541)
       |
final 100-row human sheet -> descriptive report artifacts
```

### Recommended Project Structure

```text
src/data_pipeline/apply_mislabel_triage.py
tests/data_pipeline/test_apply_mislabel_triage.py
data/processed/phase39-mislabel-candidate-*/
data/processed/phase39-mislabel-quarantine.jsonl
data/processed/phase39-mislabel-audit.jsonl
data/processed/phase39-final-judge-provenance.jsonl
.planning/phases/39-independent-quality-re-judge/39-REPORT-NOTE.md
```

### Pattern 1: Conservative identity, never `row_index`

Canonicalize text only by Unicode NFC, CRLF/CR to LF, and removal of a terminal newline. Do not casefold, collapse internal whitespace, or strip punctuation. Hash the complete canonicalized text, combine it with `seed_id`, and require exactly one current match. Reconstruct the ordered 324 candidates from `judge-merged.jsonl` using `select_mislabel_candidates()` plus `partition_by_live_presence()`; the historical file still yields `329` flagged, `324` live, `5` removed. [VERIFIED: `src/data_pipeline/generate_mislabel_triage_sheet.py:39-92,125-180`; live read-only result]

The Markdown sheet is presentation, not identity authority: the worktree version has editor-added angle autolinks and blank quote lines. Use it only as a cross-check after decoding those presentation changes. This avoids the observed result where a naive worktree-text join matched only 322/324 while the historical raw-record reconstruction matched all 324. [VERIFIED: worktree diff and local identity audit]

### Pattern 2: Decision normalization is explicit and closed

Accept exactly candidate numbers `1..324` once each. Map only raw `103.Drop` to `drop` and raw `320.Relabel to: Beigin` to `benign`; store `raw_decision`, `normalized_action`, and `normalization_reason`. Reject every other unknown spelling, label, duplicate, omission, or extra line. [VERIFIED: `MISLABEL triage.md:307,958`; schema enum at `src/data_pipeline/schemas.py:90-91`]

### Pattern 3: Preserve non-label fields exactly

For every admitted relabel, change only `label`. Assert equality before/after for `text`, `risk_tier`, `suspicious_spans`, `xai_explanation`, `source`, and `seed_id`. Drops and quarantines remove rows from the admitted pool but retain complete original records in the audit artifacts.

### Pattern 4: Candidate-first, rollback-capable promotion

Build all outputs in memory, validate, write a non-empty-only candidate directory, reload and revalidate, verify hashes, then promote splits + manifest + audit + quarantine as one payload bundle. If any replace or post-promotion verification fails, restore and hash-check every original destination. This is the established F-01 pattern. [VERIFIED: `src/data_pipeline/reconstruct_zalo_direct_catalog.py:538-667,726-847`; rollback tests at `tests/data_pipeline/test_reconstruct_zalo_direct_catalog.py:151-251`]

### Pattern 5: Re-freeze splits after destructive triage

Keeping old assignments after quarantine would leave `1,656/240/240` rows before cap, no longer an 80/10/10 snapshot. After the cap, reassign complete seed groups with a new version salt using `assign_stratified_group_split()`; never move individual rows. The verified projection is:

| Split | Rows | bank | task | benign | Zalo |
|---|---:|---:|---:|---:|---:|
| train | 1,665 | 597 | 306 | 517 | 245 |
| val | 218 | 76 | 49 | 72 | 21 |
| test | 220 | 70 | 49 | 66 | 35 |

[VERIFIED: local read-only projection using salt `phase39-mislabel-triage-v1`; group assignment algorithm at `src/data_pipeline/repair_corpus_split_governance.py:322-450`]

## Immutable Audit and Report Provenance

The manifest must preserve all prior history and append a `task_scam_mislabel_triage` block containing: input split/manifest hashes; decision-sheet hash; historical merged-judge hash; parser/source-code hashes; raw/normalized decision counts; both normalization events; every accepted/dropped/quarantined candidate identity; the quarantine policy and `seed_157ce0adb043`; pre/post cap shares and 33 cap drops; split salt and final distribution; final output hashes; and implementation Git/dirty status. The current manifest already preserves earlier repair chronology and content hashes, so append rather than replace. [VERIFIED: `data/manifests/manifest.json:1-196`; established append pattern at `src/data_pipeline/reconstruct_zalo_direct_catalog.py:466-536`]

Recommended report notice, after final numbers are frozen:

> Independent review found 324 `task_scam` label candidates. Human triage marked 91 for removal and 233 for relabeling. Because 176 proposed Zalo relabels shared one seed lineage, they were quarantined rather than admitted, preventing a single root from dominating that class. The final release was then re-capped, split by seed group, and independently re-judged; historical judge scores were reused only for byte-equivalent records, while every changed record received a fresh judgment.

Do not say that the 176 rows were “wrong”; the human label decision can be correct while the rows remain unsuitable for training because their lineage is non-independent.

## Minimal Honest Final-Snapshot Re-Judge

After quarantine and cap, exactly 1,562 of the projected 2,103 final records are full-record identical to rows in the historical judge output; 541 are new or changed: `301` Zalo, `184` task-scam risk repairs, `48` bank relabels, and `8` benign relabels. [VERIFIED: local seven-field exact-record comparison after projected cap]

Use this minimum honest strategy:

1. Compute a digest over all seven `DatasetRecord` fields, not text alone.
2. Carry forward a historical verdict only when that full-record digest has one unique historical match.
3. Rebase its `split`/`row_index` to the final snapshot and record old coordinates plus `verdict_origin=carried_forward_exact_record` in a sidecar.
4. Send all 541 unmatched/changed records through a fresh Codex delta judge and mark `verdict_origin=fresh_final_delta`.
5. Materialize one final joinable result covering exactly 2,103 current rows and recompute all descriptive statistics from that file.

This is “full final-snapshot judge coverage by exact carry-forward plus fresh delta,” not a “fresh full-corpus rerun.” If the report wants to claim the latter, all 2,103 rows must be judged again.

## Minimal Honest Final 100-Row Human Review

The present manual sheet is not final evidence: it has 49 PASS, 49 FAIL, and two blank decisions (examples 26 and 87), so it is 98/100 complete. All 14 old `zalo_social_engineering` examples were judged against narrator-scaffold text that no longer exists. [VERIFIED: blank lines at `39-manual-review-sheet.md:449,1511`; example identities at `:438,1500`; local full-sheet verdict/label parse]

Generate a fresh 100-row sheet from the final combined judge file, stratified across judge PASS/FAIL, all four labels, and carry/fresh origins. Carry a prior human verdict only when both the seven-field record digest and the complete judge-evidence digest (scores, verdict, reason) are identical and the old mark is unambiguous. Prefill those rows with `human_verdict_origin=carried_forward_exact_evidence`; leave every other row blank for the Vietnamese reviewer. JUDGE-02 closes only when the final sheet has exactly 100 unambiguous decisions and a machine-generated summary bound to the final manifest hash.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---|---|---|---|
| Record validation | Ad-hoc key checks | `DatasetRecord.model_validate()` | Enforces authoritative enums and lengths. |
| Seed cap | One-pass percentage arithmetic | `enforce_seed_cap()` | Recomputes denominator after trims. |
| Split allocation | Row-level shuffle | `assign_stratified_group_split()` | Preserves whole-seed integrity and label support. |
| Atomic promotion | Sequential in-place edits | F-01 bundle/rollback pattern | Prevents half-promoted corpus state. |
| Fresh judgment of unchanged rows | Blind full rerun or stale row-index copy | Full-record digest carry-forward | Minimizes work without overstating freshness. |

## Runtime State Inventory

| Category | Items Found | Action Required |
|---|---|---|
| Stored data | Canonical splits/manifest; historical judge output; three human sheets; future candidate/quarantine/audit files | Back up exact input bytes, append manifest history, and invalidate old positional indices. |
| Live service config | None — the relevant CLIs use local `Path` arguments and files | No service migration. |
| OS-registered state | None — no task/service registration participates in this pipeline | No OS action. |
| Secrets/env vars | None — final migration and comparison require no provider credential | Keep module network-free; fresh Codex delta remains a user-run handoff. |
| Build artifacts | Phase 40 model artifacts do not yet depend on the new final manifest | Freeze the new hashes before any training starts; do not touch model directories. |

## Common Pitfalls

### Pitfall 1: Treating candidate number or old row index as identity
After repairs, 176/324 old positions already differ. Bind by seed plus conservative full-text digest and require uniqueness.

### Pitfall 2: Quietly correcting human typos
Normalizing `Drop` and `Beigin` without preserving raw values makes the audit irreproducible. Record both forms and exact reasons.

### Pitfall 3: Relabeling all 176 dominant-seed rows
Their semantics fit Zalo, but their shared lineage makes them unsuitable as 176 independent training examples. Quarantine is not disagreement with the human reviewer.

### Pitfall 4: Reusing the old manual sheet as final evidence
It is incomplete and includes 14 superseded narrator examples. Preserve it as diagnostic history only.

### Pitfall 5: Updating split files before manifest/audit validation
A process failure can leave mismatched hashes. Stage, reload, validate, promote as one rollback-capable bundle, then verify live bytes.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---|---|---|
| V2 Authentication | no | No user/service authentication path. |
| V3 Session Management | no | No sessions. |
| V4 Access Control | no | Local operator-owned files only. |
| V5 Input Validation | yes | Strict regex coverage + Pydantic + exact identity cardinality. |
| V6 Cryptography | yes | Stdlib SHA-256 for integrity and content identity; no custom crypto. |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---|---|---|
| Edited or malformed decision sheet | Tampering | Exact 1..324 coverage, closed enum, raw-value audit. |
| Stale positional join | Tampering | Seed + full-text digest; reject zero/multiple matches. |
| Partial promotion | Tampering/DoS | Candidate validation plus verified rollback. |
| Inflated independence claim | Repudiation | Quarantine lineage and record disposition in manifest. |
| Stale judge/manual evidence | Repudiation | Exact-evidence carry provenance and fresh delta/supplement. |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|---|---|---|
| A1 | The 2026-08-20 user direction supersedes the older Phase 42 placement handoff: Phase 39 closes JUDGE-03 after the final human review. | Requirements/JUDGE-03 | Phase 40 must not start with stale t-test claims or an open Phase 39 requirement. |

## Open Questions

None. The 2026-08-20 user decision resolves the earlier phase-placement
conflict: Phase 39 performs and verifies the Chapter III/Chapter V correction,
then closes JUDGE-03 before Phase 40. Phase 42 may later revise surrounding
report prose without owning this requirement.

## Sources

### Primary (HIGH confidence)

- `.planning/phases/39-independent-quality-re-judge/39-CONTEXT.md` — locked decisions and handoff boundary.
- `.planning/phases/39-independent-quality-re-judge/MISLABEL triage.md` — human decisions.
- `.planning/phases/39-independent-quality-re-judge/39-mislabel-triage-sheet.md` — candidate identity and judge evidence.
- `.planning/phases/39-independent-quality-re-judge/39-manual-review-sheet.md` — historical human-review completion state.
- `data/processed/judge-merged.jsonl` and `data/splits/*.jsonl` — exact-record identity comparison.
- `data/manifests/manifest.json` — current canonical snapshot and repair history.
- `src/data_pipeline/schemas.py`, `repair_corpus_split_governance.py`, `reconstruct_zalo_direct_catalog.py` — authoritative validation, split, cap, manifest, staging, and rollback patterns.

No web search, third-party API, or new package lookup was used.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — read directly from installed in-repo implementation.
- Architecture: HIGH — based on current migration/promotion code and verified projections.
- Decision counts and lineage: HIGH — parsed all 324 entries and joined all 324 to raw historical/current records.
- Final projected counts: HIGH for the current locked input hashes; fail closed if those hashes change before execution.

**Research date:** 2026-08-20
**Valid until:** canonical split, manifest, decision-sheet, or judge-merged hash changes.
