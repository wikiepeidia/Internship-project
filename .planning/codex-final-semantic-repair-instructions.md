# Codex instructions: hash-bound semantic consistency decisions

Use this Codex session locally. Do not use web search, plugins, Claude, a
provider SDK, or an external API. These decisions correct cross-field
consistency only; they do not authorize new data, new labels, row removal, or
manufactured seed diversity.

## Target set

Build the semantic-review target set as the union of:

1. every one of the 57 admitted human relabels recorded in
   `data/processed/phase39-mislabel-candidate/phase39-mislabel-decision-manifest.jsonl`;
2. every fresh judge result whose `risk_tier_correctness` or
   `suspicious_span_accuracy` score is below 3; and
3. any fresh reason that identifies a concrete risk/span/XAI inconsistency.

Deduplicate by the current exact seven-field `record_digest`. Every target
must receive one explicit decision. A decision that repeats all three current
values is an explicit keep; a decision that changes at least one permitted
value is a repair.

## Permitted scope

You may provide resulting values only for:

- `risk_tier` (`benign`, `suspicious`, or `high-risk`);
- `suspicious_spans` (a list of exact, meaningful literal substrings); and
- `xai_explanation` (grounded in the message and at least 20 characters).

You must not alter `text`, `label`, `source`, or `seed_id`. Do not remove a
row, relabel it again, rewrite the message, split a seed, or invent a new seed.
If a row genuinely cannot be repaired within the three permitted fields, mark
it unresolved in the convergence work rather than forcing a decision or
silently dropping it.

Every non-empty suspicious span must occur verbatim in `text`, including the
same case, accents, punctuation, and spacing. Do not use paraphrases as spans.
The explanation must describe evidence actually present in the text and must
remain consistent with the already-authorized label and resulting risk tier.

## Exact decision schema

Write one compact JSON object per target:

```json
{"expected_record_digest":"64-lowercase-hex-characters","new_risk_tier":"high-risk","new_suspicious_spans":["exact substring from text"],"new_xai_explanation":"Grounded Vietnamese explanation of the exact message cues.","notes":"Repair: risk and evidence fields now match the requested unsafe action."}
```

The object has exactly five keys:

- `expected_record_digest`: copy the target's current digest exactly;
- `new_risk_tier`: the resulting value, even for an explicit keep;
- `new_suspicious_spans`: the complete resulting list, even for a keep;
- `new_xai_explanation`: the complete resulting explanation, even for a keep;
- `notes`: a non-empty statement beginning with `Keep:` or `Repair:` and the
  concrete rationale.

No extra key such as `label`, `text`, `source`, `seed_id`, or a free-form
replacement record is allowed. The closed Pydantic contract rejects it.

## Iteration and convergence rule

Iteration 00 decisions go to
`data/processed/phase39-semantic-repairs/iteration-00.jsonl`. Apply them only
through `CodexSemanticRepairDecision` and `apply_semantic_repairs()` in
`src/data_pipeline/apply_mislabel_triage.py`.

For every decision that changes the record digest:

1. record the exact before/after digest edge;
2. revalidate schema and literal spans;
3. create a new target for the after-digest in a later numbered judge
   iteration;
4. perform a fresh five-score judgment under the delta-judge instructions;
5. keep both old and new evidence in the convergence ledger.

If the later judgment still exposes a permitted semantic defect, repeat once
in iteration 01 and re-judge in iteration 02. After two repair attempts, retain
the identity as unresolved and stop before promotion. Never erase the row or
declare convergence to make the count fit.

`data/processed/phase39-semantic-convergence.json` is valid only when the
recomputing validator opens every declared candidate, target, repair, batch,
and result artifact; reproduces every hash; reports `unresolved_count: 0`; and
finds a later fresh verdict for every repaired after-digest:

```powershell
python -m src.data_pipeline.judge_merge validate-convergence `
  --convergence data/processed/phase39-semantic-convergence.json `
  --candidate-dir data/processed/phase39-mislabel-candidate `
  --carry data/processed/phase39-final-judge-carry.jsonl `
  --fresh-results data/processed/codex-final-delta-judge.jsonl `
  --require-zero-unresolved
```

A hand-written `unresolved_count: 0` is not evidence; the validator must pass.
