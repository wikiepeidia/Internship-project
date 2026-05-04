---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: unknown
last_updated: "2026-05-04T09:58:27.513Z"
progress:
  total_phases: 5
  completed_phases: 0
  total_plans: 9
  completed_plans: 5
  percent: 56
---

# STATE: Localized Explainable AI (XAI) Engine for Vietnamese Financial Phishing and Threat Detection

## Project Reference

- Core value: Users can safely verify suspicious Vietnamese financial messages on-device with explainable, high-recall detection that minimizes dangerous misses.
- Current milestone focus: Deliver v1 text-only offline phishing detection with evidence-bound explanations and recall-priority safety gates.
- Hard constraints:
  - Text-only input boundary for v1 (no OCR/image, no audio/voice)
  - Offline/local inference as default privacy posture
  - Recall-priority release policy for high-harm scam classes

## Current Position

Phase: 01 (data-foundation-and-split-governance) — EXECUTING
Plan: 1 of 6

- Current phase: 2 - Offline Text Ingestion and Privacy Baseline
- Current plan: Phase 2 planned (3 execution plans ready)
- Project status: Phase 1 remains complete and verified; Phase 2 planning is checker-clean with 3 execution plans ready for the offline text-ingestion runtime.
- Overall progress: 1/5 phases complete (4/4 plans in Phase 1 complete)
- Progress bar: [=----] 20%

## Performance Metrics (Baseline Targets)

- Quality target: Offline F1 >= 0.85 with per-class reporting
- Safety priority: Recall-first thresholds for high-harm classes before release
- Explainability target: Rubric pass for correctness, relevance, and actionability
- Runtime target: Local GGUF path on consumer laptop CPU/iGPU baseline; optional prosumer GPU acceleration path

## Accumulated Context

### Decisions Locked

- Keep v1 strictly text-only to protect scope and delivery certainty.
- Use localized adaptation of an open 8B model via LoRA, then deploy local quantized runtime.
- Enforce structured explainability output, not binary-only labels.
- Use explicit release gates that prioritize recall to reduce dangerous false negatives.

### Requirement Coverage Snapshot

- v1 requirements: 16
- Mapped to phases: 16
- Unmapped: 0

### Active Risks and Watchpoints

- Data leakage risk between training and evaluation splits.
- Explanation hallucination risk without strict evidence-linking.
- Quantization regressions that reduce recall on high-harm scam classes.
- Mixed-language/code-switch robustness drift over time.
- Primary live seed sources remain brittle in this environment (`canhbao.khonggianmang.vn` DNS failure, `scam.vn` HTTP 403); `tinnhiemmang.vn/canh-bao-lua-dao` is the current working fallback.

## Session Continuity

- Last session: 2026-05-04
- Stopped at: Phase 2 planning completed after the research, planner, and checker loop produced 02-01 through 02-03 with explicit docs coverage and fail-closed CLI error handling.
- Resume file: .planning/phases/02-offline-text-ingestion-and-privacy-baseline/02-01-PLAN.md
- Next command: /gsd-execute-phase 2
