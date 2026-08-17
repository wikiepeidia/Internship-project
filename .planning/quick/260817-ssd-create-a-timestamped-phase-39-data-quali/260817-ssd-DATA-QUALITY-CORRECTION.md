# Zalo Synthetic-Data Quality Correction

**Correction timestamp:** `2026-08-17T13:12:53.817089+00:00` (equivalent to `2026-08-17T20:12:53.817089+07:00`)

**Corrected manifest:** `phase39-f01-zalo-direct-reconstruction-v1`

**Implementation commit:** `3713eb2765ede818c19e5d0fb7fe14c93d4c8f00` (`fix(data): repair F-01 Zalo narration`)

This record preserves the full engineering chronology of the Zalo synthetic-data correction. It is intentionally more candid than the compact thesis wording. The replacement records described below are newly authored synthetic messages. They are not recovered originals and are not independently observed real-world data.

## Detection

An independent Codex judge reviewed the then-canonical 2,421-row corpus. Within its 300-row `zalo_social_engineering` subset, 195 rows received a realism score of 2/5. The repeated failure mode was scenario-description framing: the rows described what a sender would say instead of presenting the sender's message directly. Inspection then established that an outer narrator wrapper was present on all 300 Zalo rows, including rows whose other quality scores were higher.

## First mechanical repair

The first repair mechanically stripped the wrapper from all 300 affected rows; no wrapper was unparseable. Once the embedded text was exposed, 60 rows became same-seed lexical near-duplicates and were removed with a keep-first rule (38 from train, 8 from validation, and 14 from test). This changed the corpus from 2,421 to 2,361 rows.

The smaller denominator then moved three pre-existing large seed groups above the 8% concentration limit. Re-enforcing that limit removed another 18 rows and produced a 2,343-row corpus. Thus the complete first repair was 2,421 to 2,343 rows, not merely the 60-row duplicate reduction.

## Deeper F-01 finding

The wrapper removal did not resolve the underlying text-quality defect. A later full-subset audit proved that every one of the 240 retained Zalo rows still matched one of four narrator-derived formulas. Those formulas were repeated over 60 preserved semantic roots, four formulaic rows per root. The remaining rows were therefore structured scenario descriptions rather than convincing direct sender messages.

## Controlled reconstruction

F-01 replaced those 240 retained rows; it did not recover their original wording. A controlled, model-assisted synthetic-authoring pass in the `gpt-5.6-sol-codex-session` runtime created 300 new direct-message realizations: five messages for each of the 60 preserved semantic roots. Each variant retained its existing `seed_id` lineage and that lineage's prior split assignment. Every non-Zalo record was preserved exactly.

The replacement catalog was materialized through the `offline-static-direct-catalog` path. The authoring contract remained `openai-compatible`, but the reconstruction made zero external API calls (`external_api_call_count: 0`). Its provenance status is `new-semantic-reconstruction-not-verbatim-recovery`. These statements describe a static, no-external-API workflow; they do not claim that a local inference model authored the text.

## Validation evidence

The corrected canonical corpus contains **2,403 rows**:

| Split | All rows | Zalo before F-01 | Zalo after F-01 | Preserved Zalo lineages |
| --- | ---: | ---: | ---: | ---: |
| Train | 1,900 | 152 | 190 | 38 |
| Validation | 252 | 32 | 40 | 8 |
| Test | 251 | 56 | 70 | 14 |

The following gates were run against the complete candidate before promotion and again against the promoted files:

- record-schema and suspicious-span validation: pass;
- all four labels represented in train, validation, and test: pass;
- cross-split `seed_id` disjointness: pass;
- normalized duplicates and lexical near-duplicates at the 0.95 threshold: zero;
- exact preservation of every non-Zalo record: pass;
- preservation of all 60 Zalo lineage-to-split assignments: pass;
- seed concentration: the largest group is `seed_825b9e38d185`, with 187 of 2,403 rows, or `0.077819392426134`, below the 8% cap.

Live artifact identities, recomputed at documentation time, are:

| Artifact | SHA-256 |
| --- | --- |
| `data/manifests/manifest.json` | `4794cedae52cc5531083a569c3e63c419335a0544f365f4a4d6245048efc2b90` |
| Authored Zalo catalog | `f3e1f2f0bdcb5229fc672729eac25879fb8d914ba310695b5939fb57241561fe` |
| `train.jsonl` | `6454a271c6133f1ebbd41010390b8ea6ceae0a8ab0a75b2ab545099db3319ee8` |
| `val.jsonl` | `7adfe8cd9a124dbb3d87046bb32f9fbd127d3e344c45be77c8bb9efa700aaa75` |
| `test.jsonl` | `019aec39979429ca8005dd299d2ddaf7d3ecfdade259eecc4d3129adaed25938` |

The manifest binds these artifacts to implementation commit `3713eb2765ede818c19e5d0fb7fe14c93d4c8f00`. The named hashes and validation results preserve artifact traceability and group integrity. They do not convert the synthetic subset into a human-observed benchmark.

## Provenance interpretation

The preserved semantic roots and seed lineages provide continuity of scenario intent and leakage control. The five new messages per lineage provide new surface realizations, not independent real-world observations and not 300 independent root scenarios. Model assistance is therefore part of the dataset's authorship provenance and must remain disclosed wherever the corrected snapshot is described.

## Report-ready wording contract

The thesis should state, in measured methodology language, that an independent post-generation review identified systematic scenario-framing and narrative artifacts in the synthetic Zalo subset. It should then state that a controlled offline, model-assisted reconstruction used preserved semantic roots and seed lineages to create new direct-message realizations; the affected text was replaced, not recovered; group assignments and all non-Zalo records remained unchanged; and schema/span, label-support, seed-disjointness, duplicate, and seed-cap checks passed. The corrected snapshot must be named as `phase39-f01-zalo-direct-reconstruction-v1` and reported as 2,403 rows (1,900 train, 252 validation, and 251 test).

## Remaining limitations

- The reconstructed Zalo records remain synthetic and model-assisted. They are not a substitute for independently collected, human-labeled Vietnamese scam messages.
- Five variants share each of 60 semantic roots. Group-integrity controls prevent those lineages from crossing splits, but they do not create new root-level diversity.
- The correction changes the canonical dataset snapshot. Training and evaluation results produced from an older corpus remain historical evidence only; they do not measure models retrained on the 2,403-row corrected corpus.
- The corrected corpus is prepared for subsequent retraining and evaluation. Until that work is completed, no existing model metric should be silently relabeled as a result from this snapshot.
