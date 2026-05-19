---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: phase4-ready
last_updated: "2026-05-19T00:00:00.000Z"
progress:
  total_phases: 5
  completed_phases: 3
  total_plans: 16
  completed_plans: 16
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

Phase: 04 (threat-detection-and-explainable-decisioning) — READY TO START
Plan: Phase 3 closeout is complete; the next action is Phase 4 threat detection and explainable decisioning on top of the now-real local deployment paths

- Current phase: 4 - Threat Detection and Explainable Decisioning
- Current plan: Phase 3 is closed. The baseline winner and runner-up are locked, both retained-dataset adapter runs completed, the real GGUF conversion plus operator convert flow is in place, and both the baseline GGUF path and accelerated runner-up path have passed live local smokes on the D-drive artifact set.
- Project status: Phases 1, 2, and 3 are complete. The project can now move into Phase 4 decisioning work on top of real local deployment paths rather than scaffolds.
- Overall progress: Three phases are fully closed; the next milestone work is threat detection and explainable decisioning.
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
- A larger local pilot on 33 balanced validated samples locked `qwen3-4b-instruct-2507` as the laptop baseline winner and `qwen3.5-4b` as the runner-up; the 7B checkpoint remains a comparison or accelerated-path option.
- Real non-dry-run training is now wired in-repo, using a local PEFT and transformers backend with smoke-tested checkpoint resume for the winner and runner-up.
- The baseline winner `qwen3-4b-instruct-2507` and runner-up `qwen3.5-4b` have now both completed full three-epoch retained-dataset QLoRA runs with saved adapter artifacts and periodic checkpoints under the off-repo model root.

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
- The optional `gguf-runner-up` profile now has a registered artifact, but a direct `llama_cpp` load smoke still failed on that runner-up GGUF file; the validated shipped local paths remain `gguf-laptop` and `accelerated-local`.

## Session Continuity

- Last session: 2026-05-19
- Stopped at: Session resumed. No structured handoff, continue-here checkpoint, or incomplete plan execution was found; the project is proceeding from the existing Phase 4 context into planning.
- Local model artifacts intentionally live off-repo at `D:\PROJEct\AI MODELS`; `.env/.env` overrides `MODEL_ARTIFACT_ROOT` and `MODEL_REGISTRY_PATH` there to avoid OneDrive sync interference and costly redownloads.
- The three locked Qwen base checkpoints are already downloaded under `D:\PROJEct\AI MODELS\base`, with a local download manifest at `D:\PROJEct\AI MODELS\manifests\download-manifest.json`, so future work should reuse those files instead of downloading again.
- The locked pilot selection is now persisted at `D:\PROJEct\AI MODELS\manifests\model-registry.json`, with the larger comparison summary mirrored in `data/manifests/phase3-large-pilot-2026-05-14.json`.
- Successful smoke artifacts now exist under `D:\PROJEct\AI MODELS\phase3-smoke-baseline-20260516\qwen3-4b-instruct-2507` and `D:\PROJEct\AI MODELS\phase3-smoke-runnerup-20260516\qwen3.5-4b`, including checkpoint directories and adapter summaries.
- The retained-dataset baseline training artifacts now exist under `D:\PROJEct\AI MODELS\phase3-main-20260517\qwen3-4b-instruct-2507`, with the final checkpoint at `trainer\checkpoint-357`, the adapter directory registered in the model registry, and a training summary reporting 476 train examples, 207 validation examples, `train_loss=0.4951`, and `train_runtime=1733.30s`.
- The retained-dataset runner-up training artifacts now exist under `D:\PROJEct\AI MODELS\phase3-runnerup-main-20260517\qwen3.5-4b`, with the final checkpoint at `trainer\checkpoint-357`, the adapter directory registered in the model registry, and a training summary reporting 476 train examples, 207 validation examples, `train_loss=0.4768`, and `train_runtime=4290.87s`.
- The baseline GGUF artifact now exists under `D:\PROJEct\AI MODELS\phase3-gguf-real-2026-05-17\qwen3-4b-instruct-2507\gguf-laptop.gguf`, is registered in the off-repo model registry, and has passed real `gguf-laptop` doctor plus analyze smokes.
- The runner-up GGUF artifact now exists under `D:\PROJEct\AI MODELS\phase3-gguf-real-2026-05-17\qwen3.5-4b\gguf-runner-up.gguf` and is registered in the off-repo model registry, though only artifact creation was validated successfully; a direct `gguf-runner-up` loader smoke still failed and remains a non-blocking follow-up.
- Resume file: none
- Next command: `/gsd-plan-phase 4`
