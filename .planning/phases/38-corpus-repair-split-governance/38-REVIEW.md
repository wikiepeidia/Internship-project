---
phase: 38-corpus-repair-split-governance
reviewed: 2026-08-08T00:00:00Z
depth: standard
files_reviewed: 6
files_reviewed_list:
  - src/data_pipeline/repair_corpus_split_governance.py
  - src/data_pipeline/generation/zalo_codex_catalog.py
  - src/data_pipeline/generation/zalo_codex_recovery.py
  - tests/data_pipeline/test_repair_corpus_split_governance.py
  - tests/data_pipeline/test_repair_corpus_full_scale.py
  - tests/data_pipeline/test_zalo_codex_recovery.py
findings:
  critical: 2
  warning: 4
  info: 3
  total: 9
status: critical_fixed
resolution:
  critical_fixed: 2
  fixed_manually_at: 2026-08-08
  fixed_commit: 9577394
  deferred: 4 warning + 3 info (non-blocking, do not affect v3 corpus already on disk)
---

# Phase 38: Code Review Report

**Reviewed:** 2026-08-08
**Depth:** standard
**Files Reviewed:** 6 (3 source modules + 3 test modules; 3 `*-SUMMARY.md` docs read as context only, excluded from scope per review conventions)
**Status:** issues_found

## Summary

Reviewed the Phase 38 corpus-repair/split-governance pipeline (`repair_corpus_split_governance.py`) and its same-day `260808-otp` follow-up (`zalo_codex_catalog.py`, `zalo_codex_recovery.py`, plus the replacement-corpus support bolted onto the repair module). The core group-hash splitting, seed-cap trim loop, and evidence-span repair logic are carefully engineered and internally consistent — termination of the cap-trim loop is provably guaranteed, the group-integrity/label-support guard (`_ensure_label_support`) correctly re-verifies that a donor split retains support for every label it's *currently* carrying (including the label being moved) before releasing a seed group, and the atomic tmp-file-then-replace write pattern is used consistently for both splits and manifest.

However, two real correctness defects were found, both directly relevant to the review's stated focus (dedup/cap/repair interaction edge cases):

1. The new replacement-row validator silently makes an advertised CLI option (`--replacement-label benign`) permanently unusable by rejecting the exact "legitimately empty `suspicious_spans`" case that a near-identical function elsewhere in the same file was already patched to handle correctly one plan earlier (38-02's "empty-vs-unrecoverable" fix). The same bug class was reintroduced in new code in the same file.
2. The global lexical-duplicate gate that 260808-otp's own SUMMARY says is "required to satisfy the plan's explicit leakage and fail-closed gates" is wired so it only runs when `--replacement-input` is supplied — meaning the base repair pipeline (no replacement) still has zero cross-record duplicate detection. This is not a hypothetical: the project's own audit already found "14 lexical near-duplicate matches across split boundaries" in the v2 corpus, which was produced by exactly this code path without the gate firing.

Both are detailed below with concrete fixes.

## Critical Issues

### CR-01: `--replacement-label benign` is permanently broken — reintroduces the exact bug class already fixed in `repair_evidence_spans`

**File:** `src/data_pipeline/repair_corpus_split_governance.py:85-88`
**Issue:** `validate_replacement_records` rejects any replacement row whose `suspicious_spans` is empty:

```python
if not payload["suspicious_spans"] or any(
    not span or span not in payload["text"] for span in payload["suspicious_spans"]
):
    raise ValueError(f"replacement row {index} has an invalid evidence span")
```

`_LABELS` (line 36) includes `"benign"`, and `--replacement-label` (line 538) exposes all four labels via `choices=_LABELS`, so `--replacement-label benign` is a documented, reachable code path. But `DatasetRecord.suspicious_spans` legitimately defaults to `[]` for benign rows (schema default, `src/data_pipeline/schemas.py:96-99`), and 38-02's own SUMMARY explicitly documents that conflating "originally empty spans" with "spans that became unrecoverable" is a real bug that once destroyed all 750 benign rows in production (see `repair_evidence_spans`'s docstring and the regression test `test_repair_evidence_spans_keeps_row_that_originally_had_zero_spans`). `validate_replacement_records` reintroduces that exact conflation in new code: `not payload["suspicious_spans"]` is `True` for every valid benign row, so **every** legitimately-empty-span benign replacement row raises `ValueError`, making the `benign` replacement path unconditionally fail on any real benign data.

**Fix:**
```python
if replacement_label != "benign":
    if not payload["suspicious_spans"] or any(
        not span or span not in payload["text"] for span in payload["suspicious_spans"]
    ):
        raise ValueError(f"replacement row {index} has an invalid evidence span")
elif any(not span or span not in payload["text"] for span in payload["suspicious_spans"]):
    raise ValueError(f"replacement row {index} has an invalid evidence span")
```
(i.e. mirror the "originally empty is fine, non-empty-but-unrecoverable is not" distinction that `repair_evidence_spans` already implements correctly.)

### CR-02: Global lexical-duplicate gate only runs when `--replacement-input` is supplied — base pipeline has zero cross-record dedup, and this has already produced real cross-split leakage

**File:** `src/data_pipeline/repair_corpus_split_governance.py:563-568`
**Issue:**
```python
repaired, repair_stats = repair_all_evidence_spans(effective_pool)
repair_stats.update(replacement_stats)
if args.replacement_input is not None:
    repaired, dedup_stats = deduplicate_normalized_records(repaired, threshold=0.95)
    repair_stats.update(dedup_stats)
capped, cap_stats = enforce_seed_cap(repaired, cap_pct=args.cap_pct)
```
`deduplicate_normalized_records` (the global 0.95 RapidFuzz lexical-duplicate gate added in 260808-otp) is gated behind `args.replacement_input is not None`. `enforce_seed_cap`'s `lexical_dedup` call only dedups *within* the single seed group currently being trimmed — it never catches near-duplicate rows that live in *different* seed groups, which is exactly the failure mode a global gate is needed for.

This is not a theoretical gap: the 260808-otp SUMMARY states directly — *"The pre-existing v2 corpus had 14 lexical near-duplicate matches across split boundaries at the 0.95 threshold."* — and v2 was produced by running this exact `main()` without `--replacement-input`. Any future invocation of this script without a replacement corpus (e.g. repairing a different label population, or re-running after a future data update) reproduces the identical, already-proven leakage bug. Given this module is explicitly meant to be reused production infrastructure ("This is a one-time repair script, not a permanent addition to the generation-time validators" — but still callable generically via CLI for any future repair), the fix should not be conditional on replacement mode.

**Fix:** run the dedup gate unconditionally on `effective_pool`, and update `dedup_stats` to note the change:
```python
repaired, dedup_stats = deduplicate_normalized_records(repaired, threshold=0.95)
repair_stats.update(dedup_stats)
capped, cap_stats = enforce_seed_cap(repaired, cap_pct=args.cap_pct)
```

## Warnings

### WR-01: `enforce_seed_cap` can silently delete an entire seed group (not just trim it) when `cap_pct * total < 1`

**File:** `src/data_pipeline/repair_corpus_split_governance.py:295-297`
**Issue:**
```python
target_count = int(cap_pct * total)
survivors = ordered[:target_count]
```
`target_count` is floored. For any corpus small enough that `cap_pct * total < 1` (e.g. `total < 13` at the default 8% cap), a seed_id that trips the "over cap" check gets `target_count == 0`, i.e. `survivors == []` — the *entire* seed group is dropped, not merely capped. If that seed group is the sole representative of a label at that point in the pipeline, this silently zeroes out a whole class rather than just reducing its concentration. All existing unit fixtures use ≥100-row corpora, so this path is untested. Worth an explicit floor (e.g. `max(1, int(cap_pct * total))`) or an assertion/stat that flags when a trim reduces a group to zero, given how much of this phase's design effort went into avoiding exactly this kind of silent zero-support outcome.

**Fix:**
```python
target_count = max(1, int(cap_pct * total)) if group else 0
```
plus a stat counter for "seed groups fully eliminated by cap trimming" so this doesn't happen invisibly.

### WR-02: Replacement-corpus validation floor is far weaker than the generator's own gate, undermining the guarantee the whole quick task was built to provide

**File:** `src/data_pipeline/repair_corpus_split_governance.py:106-108`
**Issue:** `validate_replacement_records` only requires `len(unique_seeds) >= 3`, with no check on rows-per-seed-group. Compare this to `zalo_codex_recovery.validate_records` (`src/data_pipeline/generation/zalo_codex_recovery.py:134-141`), which enforces `MIN_ROOTS = 60` seed groups and `MIN_VARIANTS_PER_ROOT = 5` variants per group — the exact numbers that were needed to close the "zero held-out support" gap this task fixed. Because `--replacement-input`/`--replacement-label` in `repair_corpus_split_governance.py` is a generic CLI path (not restricted to files produced by `zalo_codex_recovery.py`), a future replacement file that passes the weaker generic gate (e.g. 3 seed groups, 1 row each) could sail through `replace_label_records` and silently reintroduce the same class of zero-val/zero-test-support problem 260808-otp exists to solve, without any error.

**Fix:** either raise the generic floor to something meaningfully protective (e.g. require `min_seed_groups >= 3 * <rows-per-seed floor>` or explicitly require `len(active_splits)`-many seeds with a minimum row count per seed), or have `replace_label_records` accept an explicit `min_seed_groups`/`min_variants_per_group` parameter that callers can tune per use case instead of a hardcoded `3`.

### WR-03: `replace_label_records` is not actually label-generic despite exposing all 4 labels via the CLI

**File:** `src/data_pipeline/repair_corpus_split_governance.py:112-146`
**Issue:** The function is written to accept any `replacement_label` in `_LABELS` (and the CLI's `choices=_LABELS` advertises that), but:
- Its span validation assumes non-empty `suspicious_spans` (see CR-01) — correct only for the three non-benign labels.
- It special-cases one label's stats key: `if replacement_label == "zalo_social_engineering": stats["old_zalo_rows_removed"] = removed_count` (lines 144-146) — a hardcoded, label-specific stat key bolted onto an otherwise generic function, rather than a generically-named key (e.g. `f"old_{replacement_label}_rows_removed"`) that would work uniformly for any label.
This mismatch between the function's generic interface and its label-specific implementation is exactly the kind of gap that produces CR-01-style regressions when the "generic" path is exercised for a label it wasn't actually tested against.

**Fix:** either restrict the CLI/type signature to the labels this code path actually supports (drop `"benign"` from what's offered, or explicitly document the limitation), or finish generalizing the function (fix CR-01, and rename the stats key to be label-parametric).

### WR-04: Misleading CLI progress output when a replacement corpus is supplied

**File:** `src/data_pipeline/repair_corpus_split_governance.py:592`
**Issue:** `print(f"Pooled {repair_stats['rows_pooled']} rows")` prints `repair_stats["rows_pooled"]`, which comes from `repair_all_evidence_spans(effective_pool)` — i.e. the count *after* the replacement swap (e.g. 2,888 in the real v3 run), not the actual number of rows read from `--input-main`/`--input-reserved` (3,413, recorded separately as `repair_stats["source_rows_pooled"]`). A human running the script with `--replacement-input` sees a "Pooled N rows" line that undercounts what was actually read from disk, which is confusing when cross-checking against input file line counts.

**Fix:** print `repair_stats.get('source_rows_pooled', repair_stats['rows_pooled'])`, or print both explicitly ("Pooled {source} source rows, {effective} after replacement").

## Info

### IN-01: Inconsistent case-folding function between span repair and the rest of the module

**File:** `src/data_pipeline/repair_corpus_split_governance.py:189`
**Issue:** `repair_evidence_spans` uses `text.lower()`/`span.lower()` for case-insensitive matching, while every other normalization step in this module (`_normalized_text`, used for dedup and replacement-duplicate checks) uses `.casefold()`. `str.lower()` and `str.casefold()` can diverge for some Unicode characters (e.g. German ß, Turkish İ); harmless for the Vietnamese corpus today, but an easy inconsistency to standardize on `.casefold()` for defense-in-depth given the module already imports/uses it elsewhere.
**Fix:** `index = text.casefold().find(span.casefold())`.

### IN-02: All 5 variants of a scenario root share one identical `xai_explanation` string

**File:** `src/data_pipeline/generation/zalo_codex_catalog.py:118-131`
**Issue:** `explanation` is computed once per `ScenarioRoot` and reused verbatim across all five surface-form renderings (`raw_variants_for_root`). The five rows differ in `text` but are byte-identical in `xai_explanation`. This isn't a leakage bug (dedup/near-dup checks operate on `text`, not `xai_explanation`, and label/spans are correct), but it does mean the corpus offers no explanation-wording diversity within a seed group, which could matter if any downstream model is trained to generate/vary explanations rather than just classify.
**Fix:** consider templating small explanation variations per rendering, or explicitly note this as an intentional simplification if diversity of explanation phrasing isn't a training objective.

### IN-03: Magic thresholds repeated as literals across call sites

**File:** `src/data_pipeline/repair_corpus_split_governance.py:100, 128, 162, 566` and `zalo_codex_recovery.py:35`
**Issue:** The `0.95` lexical-duplicate threshold is hardcoded independently at several call sites in `repair_corpus_split_governance.py` (`validate_replacement_records`, `replace_label_records`, `deduplicate_normalized_records`'s default, and the `main()` call site) instead of referencing a single module-level constant (as `zalo_codex_recovery.py` does with `LEXICAL_DUPLICATE_THRESHOLD`). Not a bug today since all sites agree on `0.95`, but a future edit to one site without the others would silently create inconsistent duplicate-detection behavior across the same run.
**Fix:** hoist `0.95` into a single `_LEXICAL_DUPLICATE_THRESHOLD` module constant and reference it everywhere, mirroring the pattern already used in `zalo_codex_recovery.py`.

---

## Resolution

**CR-01 and CR-02 fixed manually, commit `9577394`.** Both were bugs in shared pipeline code, not in the v3 corpus already on disk (v3 was produced via the replacement path where both bugs were dormant — the empty-spans bug only triggers for a `benign` replacement label, never attempted; the dedup-gate bug only triggers on the non-replacement path, not used to build v3). Fixed anyway since this is infrastructure Phase 39/40 will reuse. 161/161 tests pass after the fix, no regressions.

**WR-01 through WR-04 and the 3 info findings are deferred, not blocking.** None affect the current corpus's validity. Revisit if this pipeline is re-run for a different replacement label or a smaller corpus where the cap-floor edge case (WR-01) becomes reachable.

---

_Reviewed: 2026-08-08_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
