# Codex CLI instructions: task_scam risk_tier + suspicious_spans repair

Paste this whole file into Codex CLI as your instructions.

## Background

The independent judge pass you already ran (see
`.planning/codex-judge-instructions.md`) flagged 187 `task_scam` rows where
the message text is correctly labeled (`label_correctness >= 3`, you agreed
the row genuinely is a task_scam) but `risk_tier` is wrong: the row is tagged
`"suspicious"` when the message actually demands an upfront payment, deposit,
OTP disclosure, or credential/identity-document upload before any benefit —
which your own judge pass consistently scored as warranting `"high-risk"`
instead. A scripted keyword-based fix was tried first and only caught 38% of
these cases against your own verdicts, so this needs your judgment again,
same as the original judge pass — but this time repairing, not just scoring.

Two known-correct target values in the schema:
`risk_tier` is one of `"benign"`, `"suspicious"`, `"high-risk"` (never
anything else).

## Task

You are NOT re-judging the whole corpus and NOT touching `label` or
`xai_explanation`. For each row listed in
`data/processed/task-scam-risk-tier-repair-targets.jsonl` (187 rows, one JSON
object per line: `split`, `row_index`, `seed_id`, `current_risk_tier`,
`current_suspicious_spans`, `original_judge_risk_tier_correctness`,
`original_judge_reason` — that last field is literally your own prior
verdict, restated, so you have the original reasoning in front of you):

1. Look up the actual row: `data/splits/{split}.jsonl`, line `row_index`
   (0-based). Confirm `seed_id` matches — if it doesn't, stop and report the
   mismatch instead of guessing.
2. Decide the correct `risk_tier` for this row's actual text. Use the same
   standard you already applied during judging: an upfront payment/deposit
   demand, OTP disclosure request, or credential/identity-document request
   before any benefit is delivered is `"high-risk"`, not `"suspicious"`. If,
   on closer look, you think `"suspicious"` was actually correct and your
   original judge score was wrong, keep it as `"suspicious"` and say so in
   `notes` — you're not obligated to always change it.
3. If you change `risk_tier` to `"high-risk"`, extend `suspicious_spans` to
   include the exact substring covering "the decisive unsafe action" (the
   payment/deposit/OTP/credential phrase itself) if it's not already
   captured — every span must be an exact, case-sensitive substring of the
   row's `text` field, copy-pasted, not paraphrased. Keep any existing valid
   spans; only add what's missing (or leave `suspicious_spans` unchanged if
   it already covers the decisive action).
4. Do not touch `text`, `label`, or `xai_explanation`. Do not modify
   `data/splits/*.jsonl` directly — write only to the output file below.

**Do not modify any input file.** Your only output is the repair-results file
described below.

## Batching

Process in batches of 30-50 rows (this needs closer per-row reading than the
original judge pass, since you're producing new content — go slower, not
faster). Append after each batch, don't wait until the end.

## Output format

Append one JSON line per row to
`data/processed/codex-task-scam-risk-tier-repair.jsonl`, using this exact
shape:

```json
{"split": "train", "row_index": 42, "seed_id": "seed_abc123", "new_risk_tier": "high-risk", "new_suspicious_spans": ["đặt cọc 200k", "0987654321"], "changed": true, "notes": "short reason, max 18 words"}
```

- `split` / `row_index` / `seed_id`: copy exactly from the target row so
  results can be joined back unambiguously.
- `new_risk_tier`: your final decision (`"benign"`, `"suspicious"`, or
  `"high-risk"`) — even if unchanged from `current_risk_tier`, always include
  it.
- `new_suspicious_spans`: the FULL final list (not just additions) — even if
  unchanged from `current_suspicious_spans`, always include it. Every string
  must be an exact substring of the row's real `text`.
- `changed`: `true` if either field differs from the row's current value,
  `false` if you're confirming the original was already correct.
- `notes`: one short sentence — why you changed it, or why you kept it as-is.

You must output exactly 187 lines, one per target row, in any order — every
row in the targets file needs a decision, not just the ones you'd change.

## When done

Print a final aggregate: how many rows you changed vs. kept as-is, and how
many of the changes were `"suspicious"` -> `"high-risk"` vs. the reverse (if
any). Stop there — merging this back into the corpus is handled separately.
