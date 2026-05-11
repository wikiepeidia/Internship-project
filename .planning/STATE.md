---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: phase4-ready
last_updated: "2026-05-11T14:29:52.000Z"
progress:
  total_phases: 5
  completed_phases: 3
  total_plans: 13
  completed_plans: 13
  percent: 60
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

Phase: 04 (threat-detection-and-explainable-decisioning) — READY FOR CONTEXT
Plan: Phase 3 is complete; Phase 4 discuss-phase is the next action

- Current phase: 4 - Threat Detection and Explainable Decisioning
- Current plan: Phase 3 is complete with the local model adaptation, GGUF baseline, accelerated profile, and profile-aware docs shipped. Phase 4 needs context gathering before planning because no Phase 4 context artifacts exist yet.
- Project status: Phases 1, 2, and 3 are complete. The repo is ready to move from deployment-path scaffolding into threat labeling and explainable decision logic.
- Overall progress: Three of five roadmap phases are complete.
- Progress bar: [====-] 60%

## Performance Metrics (Baseline Targets)

- Quality target: Offline F1 >= 0.85 with per-class reporting
- Safety priority: Recall-first thresholds for high-harm classes before release
- Explainability target: Rubric pass for correctness, relevance, and actionability
- Runtime target: Local GGUF path on consumer laptop CPU/iGPU baseline; optional prosumer GPU acceleration path

## Accumulated Context

### Decisions Locked

- Keep v1 strictly text-only to protect scope and delivery certainty.
- Use localized adaptation of an open local model family via LoRA, with a 4B-primary path for 8GB VRAM and optional larger comparison candidates.
- Enforce structured explainability output, not binary-only labels.
- Use explicit release gates that prioritize recall to reduce dangerous false negatives.
- Phase 3 is now planned around a Qwen pilot with a 4B primary path, a three-model comparison, and adapter plus GGUF artifacts for the winner and runner-up.

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

- Last session: 2026-05-11
- Stopped at: Completed Phase 3, including the accelerated backend, profile-aware doctor guidance, and local-model docs. The next step is Phase 4 discussion/context gathering.
- Local model artifacts intentionally live off-repo at `D:\PROJEct\AI MODELS`; `.env/.env` overrides `MODEL_ARTIFACT_ROOT` and `MODEL_REGISTRY_PATH` there to avoid OneDrive sync interference and costly redownloads.
- The three locked Qwen base checkpoints are already downloaded under `D:\PROJEct\AI MODELS\base`, with a local download manifest at `D:\PROJEct\AI MODELS\manifests\download-manifest.json`, so future work should reuse those files instead of downloading again.
- Resume file: none
- Next command: /gsd-discuss-phase 4
