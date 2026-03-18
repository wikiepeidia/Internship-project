# STATE: Localized Explainable AI (XAI) Engine for Vietnamese Financial Phishing and Threat Detection

## Project Reference

- Core value: Users can safely verify suspicious Vietnamese financial messages on-device with explainable, high-recall detection that minimizes dangerous misses.
- Current milestone focus: Deliver v1 text-only offline phishing detection with evidence-bound explanations and recall-priority safety gates.
- Hard constraints:
  - Text-only input boundary for v1 (no OCR/image, no audio/voice)
  - Offline/local inference as default privacy posture
  - Recall-priority release policy for high-harm scam classes

## Current Position

- Current phase: 1 - Data Foundation and Split Governance
- Current plan: Not started (planning only)
- Project status: Roadmap created
- Overall progress: 0/5 phases complete
- Progress bar: [-----] 0%

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

## Session Continuity

- Last major action: Generated roadmap and requirement traceability mappings.
- Next command: /gsd-plan-phase 1
- If resuming later: Verify phase 1 data pipeline assumptions, then generate PLAN for Phase 1 with measurable acceptance checks.
