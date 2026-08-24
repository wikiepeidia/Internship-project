# Codex instructions: final-snapshot fresh-delta quality judgment

Use this Codex session locally. Do not use web search, plugins, Claude, a
provider SDK, or any external API. This is judgment work, not data generation.

## Honest scope

The final-snapshot evidence is split into two disjoint parts:

- records that are byte-for-record identical under all seven
  `DatasetRecord` fields use the historical verdict with origin
  `carried_forward_exact_record`;
- only the records in the batch target files below require a new judgment,
  with origin `fresh_final_delta` later assigned by the merge tooling.

This is **full final-snapshot coverage by exact carry-forward plus a fresh
delta**. It is not a fresh full-corpus rerun. Never copy or consult the carried
verdicts while judging the delta.

## Authoritative work queue

Read this manifest first:

`data/processed/phase39-final-judge-batches/iteration-00/manifest.json`

Process its entries in order. For iteration 00 the locked projection is nine
batches: batches 0001-0008 contain 64 targets each and batch 0009 contains 29.
Each manifest entry binds the exact target path, target count, target SHA-256,
future result path, and first/last final coordinate.

Before judging a batch, run the full pending-bundle validator:

```powershell
python -m src.data_pipeline.judge_merge validate-batches `
  --candidate-dir data/processed/phase39-mislabel-candidate `
  --carry data/processed/phase39-final-judge-carry.jsonl `
  --targets data/processed/phase39-final-judge-delta-targets.jsonl `
  --batch-manifest data/processed/phase39-final-judge-batches/iteration-00/manifest.json `
  --require-status pending
```

After one or more batches are complete, the whole manifest can be mixed-state;
validate the specific next target hash from its entry before reading it.

## Per-row judgment

Read every target's seven fields (`text`, `label`, `risk_tier`,
`suspicious_spans`, `xai_explanation`, `source`, `seed_id`) and its final
coordinate and `record_digest`. Independently score these five dimensions from
1 to 5, exactly as in the historical judge contract:

- **realism** — does the text resemble a real Vietnamese scam or benign
  message rather than a narrator scaffold or obvious template?
- **label_correctness** — does the text genuinely belong to the assigned
  four-class label?
- **code_switch_naturalness** — where Vietnamese and English are mixed, is the
  mixing natural rather than forced?
- **risk_tier_correctness** — does the assigned risk tier fit the actual harm,
  urgency, and requested action?
- **suspicious_span_accuracy** — are spans exact literal substrings and do they
  identify meaningful suspicious cues without omitting the decisive cue?

Set `pass` to true only when **all five scores are at least 3**.

Do not use a keyword rule, uniform/default score pattern, copied neighboring
verdict, historical score, or script-generated verdict as a substitute for
reading and judging a row. Every result requires a concrete, non-empty reason.

## Exact result schema

Write one JSON object per line, in exactly the same order as the target file:

```json
{"split":"train","row_index":0,"seed_id":"seed_example","record_digest":"64-lowercase-hex-characters","realism":4,"label_correctness":5,"code_switch_naturalness":4,"risk_tier_correctness":3,"suspicious_span_accuracy":4,"pass":true,"reason":"Natural message; assigned label, risk, and literal cues are consistent."}
```

Requirements:

- copy `split`, `row_index`, `seed_id`, and `record_digest` exactly from the
  target;
- use integer scores from 1 through 5;
- include exactly one non-empty plain-language reason;
- include no additional keys;
- never skip or duplicate a target.

Write to the result path declared for that same batch, for example
`batch-0001-results.jsonl`. Do not append to another batch's file.

## Validate and seal each batch

First validate without changing the manifest:

```powershell
python -m src.data_pipeline.judge_merge validate-batch `
  --batch-manifest data/processed/phase39-final-judge-batches/iteration-00/manifest.json `
  --batch-id batch-0001
```

Only if that passes, validate again and atomically mark the entry complete:

```powershell
python -m src.data_pipeline.judge_merge validate-batch `
  --batch-manifest data/processed/phase39-final-judge-batches/iteration-00/manifest.json `
  --batch-id batch-0001 `
  --mark-complete
```

A complete batch is immutable. On resume, reuse it only if the stored target
and result SHA-256 values reproduce. If a pending result is partial, malformed,
duplicated, wrong-target, or hash-conflicting, leave the manifest pending and
correct that result file explicitly; never overwrite a completed batch.

After all nine entries are complete, concatenate result files in manifest
order into `data/processed/codex-final-delta-judge.jsonl`, then run:

```powershell
python -m src.data_pipeline.judge_merge validate-batches `
  --candidate-dir data/processed/phase39-mislabel-candidate `
  --carry data/processed/phase39-final-judge-carry.jsonl `
  --targets data/processed/phase39-final-judge-delta-targets.jsonl `
  --batch-manifest data/processed/phase39-final-judge-batches/iteration-00/manifest.json `
  --combined-results data/processed/codex-final-delta-judge.jsonl `
  --require-status complete
```

Do not claim completion unless that command passes.
