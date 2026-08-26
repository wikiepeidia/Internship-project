# Phase 41 One-Shot Two-Model Evaluation

This artifact contains terminal descriptive measurements only.
The partition had prior human/content exposure during corpus-quality review; this is one post-freeze model-evaluation pass, not a claim of human blindness.
Poor results are terminal evidence and cannot trigger tuning, checkpoint selection, contingency activation, or dataset repair on this partition.

## qwen (phase40-qwen-qlora-full-seed42-v1)

- macro_f1: 0.980493
- weighted_f1: 0.981848
- accuracy: 0.981818
- invalid_output_count: 0
- risky_to_benign_count: 1
- risky_to_invalid_count: 0

| label | precision | recall | f1 | support |
|---|---:|---:|---:|---:|
| bank_impersonation | 1.000000 | 0.942857 | 0.970588 | 70 |
| zalo_social_engineering | 0.921053 | 1.000000 | 0.958904 | 35 |
| task_scam | 1.000000 | 1.000000 | 1.000000 | 49 |
| benign | 0.985075 | 1.000000 | 0.992481 | 66 |

### Confusion matrix

Rows are gold labels; columns are predicted states.

| gold label / predicted state | bank_impersonation | zalo_social_engineering | task_scam | benign | invalid_output |
|---|---:|---:|---:|---:|---:|
| bank_impersonation | 66 | 3 | 0 | 1 | 0 |
| zalo_social_engineering | 0 | 35 | 0 | 0 | 0 |
| task_scam | 0 | 0 | 49 | 0 | 0 |
| benign | 0 | 0 | 0 | 66 | 0 |

## phobert (phase40-phobert-full-seed42-v12)

- macro_f1: 0.990892
- weighted_f1: 0.990925
- accuracy: 0.990909
- invalid_output_count: 0
- risky_to_benign_count: 1
- risky_to_invalid_count: 0

| label | precision | recall | f1 | support |
|---|---:|---:|---:|---:|
| bank_impersonation | 1.000000 | 0.985714 | 0.992806 | 70 |
| zalo_social_engineering | 0.972222 | 1.000000 | 0.985915 | 35 |
| task_scam | 1.000000 | 1.000000 | 1.000000 | 49 |
| benign | 0.984848 | 0.984848 | 0.984848 | 66 |

### Confusion matrix

Rows are gold labels; columns are predicted states.

| gold label / predicted state | bank_impersonation | zalo_social_engineering | task_scam | benign | invalid_output |
|---|---:|---:|---:|---:|---:|
| bank_impersonation | 69 | 0 | 0 | 1 | 0 |
| zalo_social_engineering | 0 | 35 | 0 | 0 | 0 |
| task_scam | 0 | 0 | 49 | 0 | 0 |
| benign | 0 | 1 | 0 | 65 | 0 |

## Plain comparison

- PhoBERT higher on: macro_f1, weighted_f1, accuracy, bank_impersonation.recall, bank_impersonation.f1, zalo_social_engineering.precision, zalo_social_engineering.f1.
- Qwen higher on: benign.precision, benign.recall, benign.f1.
- Ties: bank_impersonation.precision, zalo_social_engineering.recall, task_scam.precision, task_scam.recall, task_scam.f1, invalid_output_count(lower_is_better), risky_to_benign_count(lower_is_better), risky_to_invalid_count(lower_is_better).
