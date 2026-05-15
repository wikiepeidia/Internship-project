---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: phase3-training-ready
last_updated: "2026-05-14T00:00:00.000Z"
progress:
  total_phases: 5
  completed_phases: 2
  total_plans: 13
  completed_plans: 12
  percent: 52
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

Phase: 03 (local-model-adaptation-and-deployment-paths) — READY FOR REAL TRAINING
Plan: Phase 3 pilot winner is locked; real fine-tuning readiness is the next action

- Current phase: 3 - Local Model Adaptation and Deployment Paths
- Current plan: The larger local pilot is complete and the baseline winner is locked, but real fine-tuning has not started because the repo currently exposes only a dry-run training scaffold and the local environment is missing parts of the QLoRA stack.
- Project status: Phases 1 and 2 are complete. Phase 3 is reopened for real training readiness and execution before Phase 4 planning resumes.
- Overall progress: Two phases are fully closed; Phase 3 remains active for real-training follow-through.
- Progress bar: [===--] 52%

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
- A larger local pilot on 33 balanced validated samples locked `qwen3-4b-instruct-2507` as the laptop baseline winner and `qwen3.5-4b` as the runner-up; the 7B checkpoint remains a comparison or accelerated-path option.
- Real non-dry-run training remains Phase 3 work until a concrete trainer callable is wired and the missing local QLoRA packages are installed.

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
- Real training readiness gap: the current CLI and training module support dry-run scaffolding, but non-dry-run execution still needs a concrete trainer callable plus `peft`, `trl`, and `datasets` in the local environment.

## Session Continuity

- Last session: 2026-05-14
- Stopped at: Completed a larger Phase 3 local pilot and saved the locked winner/runner-up selection into the off-repo model registry. The next step is to make real Phase 3 training executable, not to start Phase 4 yet.
- Local model artifacts intentionally live off-repo at `D:\PROJEct\AI MODELS`; `.env/.env` overrides `MODEL_ARTIFACT_ROOT` and `MODEL_REGISTRY_PATH` there to avoid OneDrive sync interference and costly redownloads.
- The three locked Qwen base checkpoints are already downloaded under `D:\PROJEct\AI MODELS\base`, with a local download manifest at `D:\PROJEct\AI MODELS\manifests\download-manifest.json`, so future work should reuse those files instead of downloading again.
- The locked pilot selection is now persisted at `D:\PROJEct\AI MODELS\manifests\model-registry.json`, with the larger comparison summary mirrored in `data/manifests/phase3-large-pilot-2026-05-14.json`.
- Resume file: none
- Next command: continue Phase 3 training readiness for `qwen3-4b-instruct-2507`
