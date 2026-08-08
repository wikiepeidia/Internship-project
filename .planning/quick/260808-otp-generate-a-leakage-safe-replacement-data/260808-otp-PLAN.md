---
quick_id: 260808-otp
type: quick
status: planned
description: Generate a leakage-safe, seed-diverse replacement for zalo_social_engineering without external provider calls
files_modified:
  - src/data_pipeline/generation/zalo_codex_catalog.py
  - src/data_pipeline/generation/zalo_codex_recovery.py
  - src/data_pipeline/repair_corpus_split_governance.py
  - tests/data_pipeline/test_zalo_codex_recovery.py
  - tests/data_pipeline/test_repair_corpus_full_scale.py
  - data/synthetic/zalo-social-engineering-codex-2026-08-08.jsonl
  - data/splits/phase38-corpus-repaired-v3/train.jsonl
  - data/splits/phase38-corpus-repaired-v3/val.jsonl
  - data/splits/phase38-corpus-repaired-v3/test.jsonl
  - data/manifests/manifest-phase38-corpus-repaired-v3.json
---

# Quick Task 260808-otp Plan

## Objective

Replace the one-lineage `zalo_social_engineering` population with a locally authored,
reproducible Codex corpus that follows the existing provider response contract but makes
zero network/API calls. Rebuild the Phase 38 corpus as a new v3 artifact while preserving
the original source files and v2 output. The result must retain whole-seed split integrity,
valid evidence spans, the 8% seed cap, and meaningful Zalo support in train, validation,
and test.

## Task 1: Author and materialize the offline Codex provider corpus

**Files:** `src/data_pipeline/generation/zalo_codex_catalog.py`,
`src/data_pipeline/generation/zalo_codex_recovery.py`,
`tests/data_pipeline/test_zalo_codex_recovery.py`,
`data/synthetic/zalo-social-engineering-codex-2026-08-08.jsonl`

**Action:**

- Add a static, reviewable catalog of at least 60 genuinely independent Zalo social-
  engineering root scenarios. Independence must come from different social relationship,
  impersonator persona, pretext, manipulation mechanism, requested action, and consequence;
  changing only names, amounts, URLs, or wording does not create a new root.
- Give each root at least five fully authored Vietnamese variants. All variants of one root
  use the seed derived from that root's stable anchor; no variant may receive a fresh seed.
- Match the raw JSON-array contract consumed by `TieredGenerator` (`text`, `label`,
  `risk_tier`, `suspicious_spans`, `xai_explanation`) and reuse the generator's normalization/
  finalization semantics locally. Record honest provenance as the existing
  `synthetic_openai_compatible` source and add build metadata identifying
  `gpt-5.6-sol-codex-session`, not Claude, as the actual authoring path.
- Materialize exactly the validated records to the ignored local JSONL output without
  instantiating or calling Anthropic, Gemini, OpenRouter, DeepSeek, OpenAI-compatible HTTP,
  web, plugins, or any other provider. Compute every suspicious span from literal text so it
  is an exact substring.
- Reject duplicate normalized text, lexical near-duplicates at the repository's chosen
  threshold, wrong labels, fewer than 60 distinct seed groups, fewer than five variants per
  group, invalid spans, or explanations shorter than the schema floor.

**Verify:**

`python -m src.data_pipeline.generation.zalo_codex_recovery --output data/synthetic/zalo-social-engineering-codex-2026-08-08.jsonl`

`python -m pytest tests/data_pipeline/test_zalo_codex_recovery.py -v`

**Done:** At least 300 schema-valid Zalo rows exist locally, distributed across at least 60
semantic root lineages; every lineage contains related variants under one seed, all texts are
globally exact/near-deduplicated, all spans are exact, and tests prove generation used no
network provider.

## Task 2: Replace the old class atomically and rebuild the versioned corpus

**Files:** `src/data_pipeline/repair_corpus_split_governance.py`,
`tests/data_pipeline/test_repair_corpus_full_scale.py`,
`data/splits/phase38-corpus-repaired-v3/{train,val,test}.jsonl`,
`data/manifests/manifest-phase38-corpus-repaired-v3.json`

**Action:**

- Add an explicit optional replacement-input path to the Phase 38 repair pipeline. When
  enabled for `zalo_social_engineering`, filter every old row of that label from the pooled
  3,413-row sources and add only the validated offline Codex replacement. Fail closed if the
  replacement contains another label, duplicate text, invalid spans, or fewer than three
  distinct seed groups. Leave both original inputs and all v2 artifacts byte-unchanged.
- Preserve the 8% cap and whole-seed group assignment. Improve the deterministic grouped
  stratification only as needed to guarantee that a label with adequate independent groups
  receives whole groups in all three splits; never fall back to row-level splitting.
- Build `phase38-corpus-repaired-v3` and extend repair manifest statistics with old Zalo rows
  removed, replacement rows added, replacement unique-seed count, generation provenance,
  and external API call count (`0`).
- Replace the full-scale test's single-seed exception with positive gates: all four labels
  have nonzero support in every split; Zalo has at least 150 train rows, 25 validation rows,
  and 25 test rows; each held-out split has at least five distinct Zalo seed groups; no seed
  crosses split boundaries; exact text and lexical near-duplicates do not cross boundaries;
  every span is exact; every seed remains below 8%; manifest hashes/counts match files.

**Verify:**

`python -m src.data_pipeline.repair_corpus_split_governance --input-main data/synthetic/recovered-balanced.jsonl --input-reserved data/splits/recovered-balanced/test.jsonl --replacement-input data/synthetic/zalo-social-engineering-codex-2026-08-08.jsonl --replacement-label zalo_social_engineering --output-dir data/splits/phase38-corpus-repaired-v3 --version-tag phase38-corpus-repaired-v3 --cap-pct 0.08 --split-ratios 0.8,0.1,0.1`

`python -m pytest tests/data_pipeline/test_repair_corpus_full_scale.py -v`

**Done:** v3 is reproducible from the locked original inputs plus the offline replacement;
train/val/test all exceed the Zalo row and lineage floors, with zero cross-split seed leakage,
zero invalid spans, zero prohibited near-duplicate leakage, honest manifest provenance, and
unchanged source/v2 backups.

## Task 3: Run the complete local regression gate and commit atomically

**Files:** all files above plus this quick task's summary artifact.

**Action:** Run the focused generator and full-scale gates, then the complete local
`tests/data_pipeline` suite. Inspect the final manifest and independently recompute counts,
seed intersections, span validity, normalized duplicates, and file hashes. Confirm the git
diff contains only intended tracked implementation/tests/planning files; local data artifacts
may remain ignored by repository policy but must exist and validate in this workspace.

**Verify:**

`python -m pytest tests/data_pipeline/ -v`

`git status --short`

**Done:** All tests pass without network access, the manifest and independent audit agree,
the implementation and tests are committed atomically, and `260808-otp-SUMMARY.md` records
the exact final counts, unique-seed counts, split support, commands, and commit hashes.

