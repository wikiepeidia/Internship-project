---
gsd_state_version: 1.0
milestone: v1.1
milestone_name: proposal-closeout
status: phase7-planned
last_updated: "2026-05-25T08:03:07Z"
progress:
  total_phases: 7
  completed_phases: 6
  total_plans: 27
  completed_plans: 25
  percent: 93
---

# STATE: Localized Explainable AI (XAI) Engine for Vietnamese Financial Phishing and Threat Detection

## Project Reference

- Core value: Users can safely verify suspicious Vietnamese financial messages on-device with explainable, high-recall detection that minimizes dangerous misses.
- Current milestone focus: Close the two remaining school-facing quantitative claims with one final validated dataset lineage and one final held-out evaluation package for the locked baseline winner.
- Hard constraints:
  - Text-only input boundary for v1 (no OCR/image, no audio/voice)
  - Offline/local inference as default privacy posture
  - Recall-priority release policy for high-harm scam classes
  - No metric laundering: final proposal claims must be backed by frozen held-out artifacts, not blended counts or unsupported splits

## Current Position

Phase: 07 (proposal-closeout-and-quantitative-validation) — PLANNED
Plan: Start with dataset closeout and split freezing, then refresh the locked baseline winner and regenerate the held-out evaluation package.

- Current phase: 7 - Proposal Closeout and Quantitative Validation (planned)
- Next phase: Phase 7 begins with final validated dataset build and frozen split closure
- Project status: The base six-phase v1 implementation milestone is complete. Phase 7 exists to finish the two remaining proposal-facing quantitative claims: a final validated 2,500-3,000 sample dataset artifact and a final held-out metric report for the locked baseline winner.
- Overall progress: Six of seven phases are complete, with the closeout milestone still pending.
- Progress bar: [===== ] 93%

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
- Phase 4 closed with a shared local-model decision layer, exact evidence grounding, safe recommendation sanitization, and contract-stable GGUF plus accelerated outputs guarded by 51 passing runtime tests.
- Phase 7 is reserved for proposal closeout only: finalize one validated dataset lineage and one honest held-out evaluation package before making stronger school-facing quantitative claims.

### Requirement Coverage Snapshot

- tracked requirements: 21
- mapped to phases: 21
- Unmapped: 0

### Active Risks and Watchpoints

- Data leakage risk between training and evaluation splits.
- Explanation hallucination risk without strict evidence-linking.
- Quantization regressions that reduce recall on high-harm scam classes.
- Mixed-language/code-switch robustness drift over time.
- Primary live seed sources remain brittle in this environment (`canhbao.khonggianmang.vn` DNS failure, `scam.vn` HTTP 403); `tinnhiemmang.vn/canh-bao-lua-dao` is the current working fallback.
- The optional `gguf-runner-up` profile now has a registered artifact, but a direct `llama_cpp` load smoke still failed on that runner-up GGUF file; the validated shipped local paths remain `gguf-laptop` and `accelerated-local`.
- The remaining Claude API budget is small, so it should be spent only on targeted missing-class generation or judging work that improves final validated yield.

## Session Continuity

- Last session: 2026-05-25
- Stopped at: Phase 6 execution is complete. The runtime now includes `src/runtime/demo.py`, separated browser assets under `src/runtime/demo_assets/`, and a `vnphish demo` launch path. The saved Phase 5 release artifact remains `BLOCK` because the held-out evaluation split still lacks bank and zalo support.
- Local model artifacts intentionally live off-repo at `D:\PROJEct\AI MODELS`; `.env/.env` overrides `MODEL_ARTIFACT_ROOT` and `MODEL_REGISTRY_PATH` there to avoid OneDrive sync interference and costly redownloads.
- The three locked Qwen base checkpoints are already downloaded under `D:\PROJEct\AI MODELS\base`, with a local download manifest at `D:\PROJEct\AI MODELS\manifests\download-manifest.json`, so future work should reuse those files instead of downloading again.
- The locked pilot selection is now persisted at `D:\PROJEct\AI MODELS\manifests\model-registry.json`, with the larger comparison summary mirrored in `data/manifests/phase3-large-pilot-2026-05-14.json`.
- Successful smoke artifacts now exist under `D:\PROJEct\AI MODELS\phase3-smoke-baseline-20260516\qwen3-4b-instruct-2507` and `D:\PROJEct\AI MODELS\phase3-smoke-runnerup-20260516\qwen3.5-4b`, including checkpoint directories and adapter summaries.
- The retained-dataset baseline training artifacts now exist under `D:\PROJEct\AI MODELS\phase3-main-20260517\qwen3-4b-instruct-2507`, with the final checkpoint at `trainer\checkpoint-357`, the adapter directory registered in the model registry, and a training summary reporting 476 train examples, 207 validation examples, `train_loss=0.4951`, and `train_runtime=1733.30s`.
- The retained-dataset runner-up training artifacts now exist under `D:\PROJEct\AI MODELS\phase3-runnerup-main-20260517\qwen3.5-4b`, with the final checkpoint at `trainer\checkpoint-357`, the adapter directory registered in the model registry, and a training summary reporting 476 train examples, 207 validation examples, `train_loss=0.4768`, and `train_runtime=4290.87s`.
- The baseline GGUF artifact now exists under `D:\PROJEct\AI MODELS\phase3-gguf-real-2026-05-17\qwen3-4b-instruct-2507\gguf-laptop.gguf`, is registered in the off-repo model registry, and has passed real `gguf-laptop` doctor plus analyze smokes.
- The runner-up GGUF artifact now exists under `D:\PROJEct\AI MODELS\phase3-gguf-real-2026-05-17\qwen3.5-4b\gguf-runner-up.gguf` and is registered in the off-repo model registry, though only artifact creation was validated successfully; a direct `gguf-runner-up` loader smoke still failed and remains a non-blocking follow-up.
- Phase 5 context, execution summaries, release report, and saved manifest artifacts now exist under `.planning/phases/05-recall-priority-evaluation-and-release-gates/` and `data/manifests/`.
- Phase 6 runtime-backed demo artifacts now exist under `.planning/phases/06-local-demo-ui-for-non-technical-verification/`, and the user-facing launch path is `vnphish demo` or `python -m src.runtime.cli demo`.
- Phase 7 should start under `.planning/phases/07-proposal-closeout-and-quantitative-validation/` with a dataset-closeout plan followed by a held-out evaluation-closeout plan.
- Resume file: none (no `HANDOFF.json`, `.continue-here`, or interrupted-agent artifact detected)
- Next command: start Phase 7 with the dataset-closeout plan, then move to the held-out evaluation-closeout plan.
