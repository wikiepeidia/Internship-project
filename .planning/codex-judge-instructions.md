# Codex CLI instructions: independent LLM-judge pass on the repaired corpus

Paste this whole file into Codex CLI as your instructions.

## Task

You are an independent quality judge for a Vietnamese financial-phishing
detection dataset. This dataset already has a `label` (one of
`bank_impersonation`, `zalo_social_engineering`, `task_scam`, `benign`), a
`risk_tier`, `suspicious_spans`, and an `xai_explanation` field per row. You
are NOT generating new data and NOT deciding whether the row belongs in
training — you are scoring it, independently, the same way a second
reviewer would.

**Input files (judge all three, in this order):**

- `data/splits/train.jsonl`
- `data/splits/val.jsonl`
- `data/splits/test.jsonl`

This is the final, repaired, leakage-safe corpus (Phase 38 + the same-day
zalo-replacement fix) — the current, only version. There is no older/pre-repair
file to worry about avoiding; the live `data/` tree only ever holds this one.

**Do not modify any input file. Do not write anything into `data/synthetic/`,
`data/processed/`, or `data/splits/`.** Your only output is the judge-results
file described below.

## Batching

Process the file in batches of 50-100 rows at a time (your context window
can hold more, but judgment quality per row matters more than batch size —
don't do the whole file in one shot). After each batch, append your results
to the output file (see below) — do not wait until the end to write
everything at once, in case the session gets interrupted.

## Per-row scoring

For each row, score these five dimensions from 1 to 5, exactly matching the
existing project's judge schema so results are directly comparable:

- **realism** — does this read like a real-world Vietnamese scam/benign
  message, not obviously templated or artificial?
- **label_correctness** — does the message text actually match the assigned
  `label`? (Not "did the generator follow instructions" — does the content
  itself genuinely belong to this class?)
- **code_switch_naturalness** — if the message mixes Vietnamese and English,
  does the mixing read naturally, not forced?
- **risk_tier_correctness** — does the assigned `risk_tier` match how
  urgent/dangerous the message actually reads?
- **suspicious_span_accuracy** — are the `suspicious_spans` exact substrings
  of the message text, and do they point at genuinely suspicious content
  (not irrelevant or missing cues)?

Mark `pass: true` only if all five scores are at least 3.

## Output format

Append one JSON line per row to `data/processed/codex-judge-pass.jsonl`,
using this exact shape:

```json
{"split": "train", "row_index": 0, "seed_id": "seed_157ce0adb043", "realism": 4, "label_correctness": 5, "code_switch_naturalness": 4, "risk_tier_correctness": 5, "suspicious_span_accuracy": 4, "pass": true, "reason": "short reason, max 18 words"}
```

- `split`: which of the three files this row came from (`"train"`, `"val"`,
  or `"test"`) — required now that there are three input files, not one.
- `row_index`: the row's 0-based line number within that specific split file
  — this is how results get joined back to the source rows later, so
  `split` + `row_index` together must be exact and unambiguous.
- `seed_id`: copy directly from the row (for cross-checking against seed-group
  grouping).
- Keep `reason` short — one sentence max, plain language, no padding.

## After each batch

Print a short summary: how many rows in this batch, how many passed, and the
running average for each of the five dimensions so far. Don't stop between
batches unless something looks structurally wrong (e.g. malformed rows,
missing fields) — flag those rows in the output with `pass: false` and a
reason like `"malformed row: missing suspicious_spans field"` rather than
skipping them silently.

## When done

Print a final aggregate: total rows judged, overall pass rate, and the
average score per dimension across the whole file. That aggregate is what
gets cited in the report (replacing the retired t-test), alongside a
separate manual 100-example human check done outside this process.
