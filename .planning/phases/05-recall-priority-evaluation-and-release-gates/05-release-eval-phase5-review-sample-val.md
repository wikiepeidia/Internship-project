# Phase 5 Release Evaluation: phase5-review-sample-val

- verdict: BLOCK
- risky_recall_floor: 0.9
- macro_f1: 0.25
- weighted_f1: 1.0
- evaluated_rows: 12

## Per-label metrics

- bank_impersonation: precision=0.0 recall=0.0 f1=0.0 support=0
- zalo_social_engineering: precision=0.0 recall=0.0 f1=0.0 support=0
- task_scam: precision=1.0 recall=1.0 f1=1.0 support=12
- benign: precision=0.0 recall=0.0 f1=0.0 support=0

## Blocker reasons

- Missing support for risky label bank_impersonation in release-eval split data\splits\val.jsonl
- Missing support for risky label zalo_social_engineering in release-eval split data\splits\val.jsonl
- Release blocker: bank_impersonation has zero held-out support in the evaluated snapshot.
- Release blocker: zalo_social_engineering has zero held-out support in the evaluated snapshot.

## Flag reasons

- None

## Explanation rubric summary

- evaluated_risky_predictions: 12
- manual_reviewed_predictions: 12
