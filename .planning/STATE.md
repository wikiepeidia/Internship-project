---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: waiting-review
last_updated: "2026-05-05T11:45:00.000Z"
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

Phase: 01 (data-foundation-and-split-governance) — WAITING FOR JUDGE
Plan: dataset review gate

- Current phase: 1 - Data Foundation and Split Governance
- Current plan: Hold Phase 2 execution while the recovered Phase 1 dataset is judged and curated.
- Project status: Phase 1 implementation work is complete. Recovery and offline optimization produced a merged corpus above the 3,000-record target band and a balanced salvage subset for review; the next decision gate is judging, not more generation.
- Overall progress: Phase 1 generation target reached via recovered artifacts; judging and final acceptance are still pending before Phase 2 execution resumes.
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

- Last session: 2026-05-05
- Stopped at: Recovered and merged historical synthetic artifacts into a 3,074-record exact-unique corpus, produced a 956-record balanced offline subset capped by benign scarcity, and confirmed the current checkpoint files should be treated as salvage artifacts rather than authoritative resume state.
- Resume file: .planning/debug/checkpoint-split-w-fix.md
- Next command: Judge the recovered Phase 1 dataset, then decide whether to accept the balanced salvage set or top up benign coverage before resuming Phase 2.
