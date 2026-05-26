# Phase 5 Release Evaluation: phase5-recovered-balanced-val

- verdict: BLOCK
- risky_recall_floor: 0.9
- macro_f1: 0.7431305566629522
- weighted_f1: 0.8617622153666554
- evaluated_rows: 210

## Per-label metrics

- bank_impersonation: precision=0.7638888888888888 recall=0.9821428571428571 f1=0.859375 support=56
- zalo_social_engineering: precision=0.925 recall=0.9866666666666667 f1=0.9548387096774194 support=75
- task_scam: precision=0.14545454545454545 recall=0.4444444444444444 f1=0.2191780821917808 support=18
- benign: precision=1.0 recall=0.8852459016393442 f1=0.9391304347826087 support=61

## Blocker reasons

- Release blocker: task_scam recall 0.44 is below required floor 0.90.

## Flag reasons

- Label alignment flag: predicted labels are weakly supported by the captured cues.
- Recommendation quality flag: explanation fell back to generic safe advice.

## Explanation rubric summary

- evaluated_risky_predictions: 156
- manual_reviewed_predictions: 156
- rubric_flag: Label alignment flag: predicted labels are weakly supported by the captured cues.
- rubric_flag: Recommendation quality flag: explanation fell back to generic safe advice.
