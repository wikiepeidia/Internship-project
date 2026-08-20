# Phase 39 Mislabel Audit and Lineage Disposition

## Scope and wording for the report

A Vietnamese-fluent project reviewer manually examined all **324 live `task_scam` records** that the independent Codex pass scored below 3/5 for label correctness. This was a targeted review of judge-flagged candidates, **not independent annotation of the full corpus**.

The review selected **91 records for removal** and made **233 semantic relabel decisions**: 48 as `bank_impersonation`, 177 as `zalo_social_engineering`, and 8 as `benign`. Candidate 103's exact raw `Drop` was normalized to `drop`; candidate 320's exact raw `Beigin` was normalized to `benign`. No decision was inferred from the reviewer's free-text note.

## Lineage-safe admission

The label judgment and training admission decision are separate. Of the 177 human-approved Zalo relabels, **176 share the single seed `seed_157ce0adb043`**. Those 176 records remain documented as semantically approved but are quarantined from training because they are variants of one non-independent root scenario. Candidate 47 (`seed_c6c8772ac332`) is the one independently seeded Zalo relabel admitted from this audit.

The resulting human dispositions are therefore:

- 91 human drops
- 57 admitted label-only relabels
- 176 shared-lineage quarantines

Every admitted relabel changes only `label`; text, risk tier, suspicious spans, XAI explanation, source, and seed ID are byte/value-preserved. Risk tier, spans, and explanation are awaiting the separately hash-bound semantic judge step.

## Staged projection

After the human dispositions, 2,136 rows remained. The existing iterative global 8% seed cap removed 33 additional rows with a dedicated audit trail. Whole seed groups were then reassigned deterministically with salt `phase39-mislabel-triage-v1`.

| Split | Rows | Bank | Task scam | Benign | Zalo |
|---|---:|---:|---:|---:|---:|
| train | 1,665 | 597 | 306 | 517 | 245 |
| val | 218 | 76 | 49 | 72 | 21 |
| test | 220 | 70 | 49 | 66 | 35 |
| **total** | **2,103** | **743** | **404** | **655** | **301** |

The Zalo subset has 301 rows across 61 seed groups; its largest seed contributes 5/301 (1.6611%). The largest seed in the full staged corpus contributes 168/2,103 (7.9886%). No seed crosses splits, every split contains all four labels, all listed suspicious spans are literal substrings, and normalized/lexical duplicates at the 0.95 threshold are zero.

This **2,103-row result is a staged projection, not a frozen release**. It still requires the Phase 39 semantic delta judge and final promotion gate.

## Immutable evidence

- Compact 324-decision audit SHA-256: `c408dcf4161d84056b7c22e1fb3e975352a52cd5fbf2b111f11b5dfece0c089c`
- Historical merged judge SHA-256: `e8b4d947271717e56556a74136c57d83dd58589c78699d557999140a9fb55750`
- Candidate train SHA-256: `9aff01cc3bc0300e5ef92c8c8463d25c9daccf6afcf9ebd2452b8fa32fdde2af`
- Candidate val SHA-256: `7eaafe13a354feb81e6fa8b6a1ae55d74067362cc942332ee4bbd9c57945b81d`
- Candidate test SHA-256: `84ffc0620d3d0e57af300e1bf2e9330e0bbd7fa0178258a640de85f02c4f4bc3`
- Protected 100-row review sheet SHA-256: `e078b3bf6efd29c8f80f7ea8afaeb1121803c4ce8322fe4a497dd997b9b17743`
- Protected historical triage sheet SHA-256: `39ca1768c0a114156aece97e7dff2269b074a5125d59b8592f215e3e36415cc7`

The live `data/splits/{train,val,test}.jsonl`, live manifest, historical judge output, and all three user review artifacts were read-only inputs during this stage.
