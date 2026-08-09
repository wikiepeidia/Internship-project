---
phase: 39-independent-quality-re-judge
reviewed: 2026-08-08T00:00:00Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - src/data_pipeline/judge_merge.py
  - src/data_pipeline/manual_review_sheet.py
  - tests/data_pipeline/test_judge_merge.py
  - tests/data_pipeline/test_manual_review_sheet.py
findings:
  critical: 0
  warning: 6
  info: 2
  total: 8
status: resolved
resolution:
  commit: ed544f5
  fixed: [WR-01, WR-02, WR-03, WR-04, WR-05, WR-06, IN-01]
  deferred: [IN-02]
---

# Phase 39: Code Review Report

**Reviewed:** 2026-08-08
**Depth:** standard
**Files Reviewed:** 4
**Status:** resolved (see Resolution section)

## Summary

Reviewed `judge_merge.py` and `manual_review_sheet.py` (Phase 39, Plan 01) plus
their test suites at standard depth, cross-checked against
`.planning/codex-judge-instructions.md` (the real, human-authored schema these
tools must parse) and against the actual `data/splits/{train,val,test}.jsonl`
corpus (1918/252/251 = 2421 rows) that will be the real input the moment the
Codex judge pass runs.

Both files are clean, well-organized, and the "fail loudly, never silently
skip" design goal is real for the cases the test suite exercises (malformed
JSON, missing fields, out-of-range scores, seed_id mismatch, missing/duplicate
row_index). No crashes, security issues, or data-loss risks were found — no
Critical findings.

However, the tests only exercise fixtures shaped exactly like the documented
schema; nothing exercises what happens when *real* Codex output deviates from
that shape in the specific ways the review brief asked about. Tracing through
those scenarios against the real corpus surfaced several genuine gaps:

1. Coverage-mismatch error messages are unbounded, untruncated Python list
   dumps — fine for a 1-row typo, unreadable for a batch-boundary
   row_index-reset (a very plausible failure mode given the judge
   instructions explicitly tell Codex to number "batches of 50-100 rows" and
   append after each one).
2. `seed_id` mismatches abort on the *first* one found per split, unlike the
   row_index coverage check, which aggregates all problems before raising —
   so a systemic mismatch (not a one-off typo) turns into a many-round
   fix/re-run debugging loop.
3. Fail-closed guarding is asymmetric: only `--judge-results` (judge_merge.py)
   and `--merged-path` (manual_review_sheet.py) get an actionable
   "here's the exact next command to run" error. Missing/incomplete source
   splits, and a malformed/corrupt `judge-merged.jsonl`, both surface as raw,
   unguided Python tracebacks.
4. The manual-review-sheet renderer's blockquote formatting breaks on
   multi-line message text — confirmed against real data: 57 of 2421 rows in
   the current corpus contain embedded newlines in `text`.

None of these cause data loss or incorrect merging — they degrade the
tool's usefulness specifically in the "confusing real-world Codex output"
scenarios the review was asked to focus on, which is why they're flagged as
Warnings rather than left unaddressed.

## Warnings

### WR-01: Coverage-mismatch errors are unbounded list dumps, not summaries

**File:** `src/data_pipeline/judge_merge.py:135-146`
**Issue:** When `missing`/`duplicates`/`unexpected` row_index sets are
non-empty, the error message embeds the *entire* sorted list with no count
prefix and no truncation:

```python
if missing:
    problems.append(f"missing row_index(es) {missing}")
```

A clean, uniform off-by-one shift across an entire split produces a small,
readable diff (1 missing + 1 unexpected), which is fine. But the judge
instructions (`.planning/codex-judge-instructions.md`) explicitly tell Codex
to process "in batches of 50-100 rows... append your results to the output
file... after each batch" — a well-known LLM failure mode for exactly this
kind of task is restarting `row_index` at 0 for every batch instead of
continuing the running count. Against the real train split (1918 rows,
~19-38 batches at 50-100 rows/batch), that failure mode would produce a
`ValueError` whose message is a wall of up to ~1900 raw integers — effectively
useless for a non-expert user trying to diagnose *what kind* of problem
occurred (one typo vs. a systemic batch-reset).
**Fix:** Prefix each problem with its count, and truncate long lists:

```python
def _summarize(indices: list[int], limit: int = 20) -> str:
    if len(indices) <= limit:
        return str(indices)
    return f"{indices[:limit]} ... and {len(indices) - limit} more"

if missing:
    problems.append(f"missing {len(missing)} row_index(es): {_summarize(missing)}")
```
Consider also detecting the batch-reset pattern (e.g., row_index 0 appearing
as a duplicate more than once) and naming it explicitly in the message.

### WR-02: seed_id mismatch check aborts on the first hit instead of aggregating

**File:** `src/data_pipeline/judge_merge.py:153-161`
**Issue:** The row_index coverage check (missing/duplicate/unexpected)
correctly aggregates *all* problems for a split before raising once. The
seed_id cross-check that immediately follows does not — it raises on the
very first mismatch it encounters while iterating `sorted(actual_indices)`:

```python
for row_index in sorted(actual_indices):
    result = by_split[split_name][row_index]
    source_row = source_rows[row_index]
    if result.seed_id != source_row["seed_id"]:
        raise ValueError(...)  # stops here, rest of split never checked
```

For a one-off typo this is fine. But if the real cause is systemic (e.g. a
row_index shift that's internally self-consistent in count but off by N, so
every row past the shift point has a "wrong" seed_id), the user only ever
learns about one mismatched row per run, fixes it, re-runs, and discovers the
next one — repeating potentially dozens of times across a 1918-row split
before the merge succeeds.
**Fix:** Collect all seed_id mismatches for the split (row_index, expected,
actual) into a list and raise once with all of them, mirroring the
missing/duplicate/unexpected aggregation immediately above it.

### WR-03: Fail-closed guarding is asymmetric — only one input file gets an actionable error

**File:** `src/data_pipeline/judge_merge.py:96` (`load_source_splits`), `:261-267` (`main`)
**Issue:** `main()` explicitly checks `args.judge_results.exists()` and
raises a `FileNotFoundError` naming the exact next command to run (paste the
instructions into Codex CLI, etc.). No equivalent check exists for
`--splits-dir` / `data/splits/{train,val,test}.jsonl` — `load_source_splits`
just calls `split_path.open("r", ...)` directly, so a missing/renamed split
file surfaces as a bare `FileNotFoundError: [Errno 2] No such file or
directory: 'data/splits/train.jsonl'` with no guidance.

More importantly: the judge instructions tell Codex to append to
`codex-judge-pass.jsonl` incrementally, batch by batch, and *not* to wait
until the end. If a user runs `judge_merge.py` while Codex is still mid-run
(a very plausible real workflow — "let me check progress"), the partial file
will look, from this tool's point of view, structurally identical to broken
output: both manifest as `missing row_index(es) [...]` for the tail of the
split. There is nothing in the error message that distinguishes "you're not
done yet" from "the output is genuinely malformed."
**Fix:** Add the same existence check for each `splits_dir / f"{name}.jsonl"`
before opening. For the in-progress case, consider a heuristic: if `missing`
forms a single contiguous suffix starting partway through the file (e.g.
`missing == list(range(min(missing), len(source_rows)))`), phrase the error
as "looks like Codex hasn't finished this split yet" rather than a generic
coverage error.

### WR-04: `manual_review_sheet.py` has no schema validation on its input, unlike `judge_merge.py`

**File:** `src/data_pipeline/manual_review_sheet.py:157-164` (`_load_merged`), `:188-192` (`main`)
**Issue:** `judge_merge.py`'s `load_judge_results` reports malformed JSON and
schema violations with a specific 1-based line number
(`judge-results line {N} is not valid JSON: ...` /
`... failed schema validation: ...`). `manual_review_sheet.py`'s
`_load_merged` does none of this — it's a bare `json.loads(stripped)` per
line with no Pydantic model and no per-row key checks:

```python
def _load_merged(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                rows.append(json.loads(stripped))
    return rows
```

If a user points `--merged-path` at the wrong file (typo, stale path from
before a rerun, or a `judge-merged.jsonl` that got truncated by an
interrupted write despite the atomic-replace convention), the failure mode
is a raw `KeyError: 'judge_pass'` (or `'text'`, `'label'`, etc.) deep inside
`select_stratified_sample` or `_render_example`, with no hint about which
row or what's actually wrong.
**Fix:** Validate each row has the expected keys (or reuse a lightweight
Pydantic model for the merged-row shape) and raise a `ValueError` naming the
line number and the missing key, matching `judge_merge.py`'s convention.

### WR-05: Multi-line message text breaks the review sheet's Markdown structure

**File:** `src/data_pipeline/manual_review_sheet.py:96`
**Issue:** `_render_example` blockquotes the message text with a single
`"> "` prefix applied only to the start of the string:

```python
f"> {row['text']}",
```

If `row['text']` contains an embedded newline, every line after the first is
emitted as bare (non-blockquoted) Markdown. Confirmed against the real
corpus this tool will actually run against:

```
57 of 2421 rows in data/splits/{train,val,test}.jsonl contain '\n' in text
```

For those rows, a line that happens to start with `-`, `#`, `*`, or that is
exactly `---` (a common pattern in real message text — separators, list-style
scam instructions, etc.) will render as a Markdown list item, heading, or —
worst case — a horizontal rule that is visually identical to the sheet's own
section separator used between examples (line 109: `"---"`). This can make
one example visually bleed into the next for the human doing the JUDGE-02
manual check, exactly the kind of subtle corruption that's hard to notice
while skimming 100 examples.
**Fix:**

```python
quoted_text = row["text"].replace("\n", "\n> ")
lines = [
    ...,
    f"> {quoted_text}",
    ...,
]
```

### WR-06: `CodexJudgeResult` silently drops unexpected/misnamed fields instead of rejecting them

**File:** `src/data_pipeline/judge_merge.py:39-43`
**Issue:** The model's docstring and module docstring both claim the tool
"never skips a bad line silently" and re-raises "any malformed JSON or schema
violation." But `ConfigDict(populate_by_name=True)` does not set
`extra="forbid"`, so Pydantic v2's default `extra="ignore"` behavior applies:
any field Codex appends that isn't one of the declared ones (a typo'd key
name, a renamed field, an extra diagnostic field) is silently dropped rather
than raising. This is exactly the "a row Codex appended with a slightly
different shape" scenario called out in the review brief — a shape
difference that happens to *add* an unexpected key currently passes through
undetected, weakening the stated fail-closed guarantee.
**Fix:**

```python
model_config = ConfigDict(populate_by_name=True, extra="forbid")
```

## Info

### IN-01: `reason` field has no length constraint unlike sibling `seed_id`

**File:** `src/data_pipeline/judge_merge.py:54`
**Issue:** `seed_id: str = Field(min_length=1)` enforces non-empty, but
`reason: str` has no such constraint, so an empty-string `reason` from Codex
(e.g. a truncated/interrupted write) validates cleanly even though the
judge instructions require "a short reason, max 18 words" for every row.
**Fix:** `reason: str = Field(min_length=1)`.

### IN-02: Cross-module dependency on a private (underscore-prefixed) helper

**File:** `src/data_pipeline/manual_review_sheet.py:26`
**Issue:** `from src.data_pipeline.processing.splitter import _stable_bucket`
imports a leading-underscore symbol from an unrelated module. This works
today and is intentionally the *same* hashing scheme used for corpus
splitting (arguably desirable for consistency), but nothing marks
`_stable_bucket` as a stable public contract between the two modules — a
future refactor of `splitter.py` could rename or remove it without any
signal that `manual_review_sheet.py`'s determinism depends on it.
**Fix:** Either promote `_stable_bucket` to a shared, non-underscored utility
module, or add a comment/test in `splitter.py` noting the external
dependency.

---

## Resolution

**Fixed in commit `ed544f5`** (2026-08-08), before handoff to the user for
the real Codex judge run — these were real, predictable failure modes for
the exact next step (real, messy Codex output landing), not speculative
code-quality concerns:

- **WR-01** — coverage-mismatch errors now report a count plus the first 20
  indices instead of dumping the full raw list, and the duplicate-index case
  now names the likely cause (Codex restarting `row_index` at 0 per batch
  instead of continuing the running count across the whole split).
- **WR-02** — seed_id mismatches are now collected across the whole split and
  raised once, mirroring the row_index coverage check instead of stopping at
  the first hit.
- **WR-03** — `load_source_splits` now checks each `{split}.jsonl` exists
  before opening it and raises an actionable `FileNotFoundError` naming the
  missing file, symmetric with the existing `--judge-results` guard in
  `main()`. (The mid-batch-run heuristic suggested in the finding's "Fix"
  section was not built — out of scope for a pre-handoff hardening pass; the
  now-actionable missing-file/coverage errors are sufficient for the user to
  self-diagnose "not done yet" vs. "genuinely broken.")
- **WR-04** — `_load_merged` now validates required keys per row and raises
  `ValueError` naming the 1-based line number and the missing key(s), instead
  of deferring to a bare `KeyError` inside sample selection or rendering.
- **WR-05** — `_render_example` now renders `text` via a proper multi-line
  blockquote helper (`_format_blockquote`, prefixing every line with `>` +
  space) instead of a bare `"> {text}"` that only blockquoted the first line.
- **WR-06** — `CodexJudgeResult` now sets `extra="forbid"`, so an unexpected
  or misnamed field from Codex raises instead of being silently dropped.
- **IN-01** — `reason` now has `min_length=1`, matching `seed_id`'s
  non-empty constraint.

**Deferred: IN-02** (private `_stable_bucket` import from `splitter.py`) —
cosmetic/maintainability only, no behavioral risk for the upcoming Codex
handoff. Left as-is; revisit if `splitter.py` is refactored.

Verification: added regression tests for each fixed finding (coverage-error
truncation/aggregation, missing-split-file guard, `_load_merged` schema
validation, multi-line blockquote rendering). Full suite: 365/365 passing
(`tests/data_pipeline/`: 183/183). No corpus files were touched — this was a
tooling-only fix.

---

_Reviewed: 2026-08-08_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
