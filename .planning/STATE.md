---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: phase1-closed
last_updated: "2026-05-07T00:00:00.000Z"
progress:
  total_phases: 5
  completed_phases: 1
  total_plans: 9
  completed_plans: 6
  percent: 67
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

Phase: 01 (data-foundation-and-split-governance) — CLOSED
Plan: Phase 1 retained artifact set finalized

- Current phase: 1 - Data Foundation and Split Governance
- Current plan: Phase 1 tracking is closed on the recovered retained artifact lineage, and the next actionable work is Phase 2.
- Project status: Phase 1 now has a final accepted judged dataset at 956 records, balanced at 239 per class, stored under `data/processed/recovered-balanced-validated-claude-v2.jsonl`, plus governed retained splits at `data/splits/recovered-balanced-claude-v2/` and a verified manifest at `data/manifests/manifest-phase1-recovered-balanced-claude-v2.json`.
- Overall progress: Phase 1 implementation, recovery, judging, and retained artifact closure are complete; the project is ready to transition into Phase 2.
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

- Last session: 2026-05-07
- Stopped at: Patched the Phase 1 judge to score `risk_tier` and `suspicious_spans`, ran Claude on `data/synthetic/recovered-balanced.jsonl`, repaired the rejected benign metadata mismatch, accepted the final 956-record balanced judged set as the Phase 1 review artifact, then fixed the small-seed split allocation bug and rebuilt downstream outputs. The accepted judged set now produces 891 retained split records after dedup, with train=476, val=207, test=208, and the manifest verifies cleanly.
- Resume file: .planning/debug/checkpoint-split-w-fix.md
- Next command: Begin Phase 2 planning or execution.
