---
gsd_state_version: 1.0
milestone: v1.2
milestone_name: thesis-report-writing-and-evidence-packaging
status: planning
last_updated: "2026-05-28T00:00:00Z"
progress:
  total_phases: 5
  completed_phases: 0
  total_plans: 5
  completed_plans: 0
  percent: 0
---

# STATE: Localized Explainable AI (XAI) Engine for Vietnamese Financial Phishing and Threat Detection

## Project Reference

- Core value: Users can safely verify suspicious Vietnamese financial messages on-device with explainable, high-recall detection that minimizes dangerous misses.
- Current milestone focus: Produce the graduation thesis report, map existing repo evidence into each chapter, and prepare a judging-ready submission.
- Hard constraints:
  - Text-only input boundary for v1 (no OCR/image, no audio/voice)
  - Offline/local inference as default privacy posture
  - Recall-priority release policy for high-harm scam classes
  - No metric laundering: final proposal claims must be backed by frozen held-out artifacts, not blended counts or unsupported splits
  - Thesis writing must use a natural undergraduate tone and avoid AI-like wording or internal GSD jargon

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-05-26 — Milestone v1.2 started

- Current phase: 7a - task_scam Recall Recovery (context gathered, ready to plan)
- Next phase: 7a → 7b → 8 (blocked order)
- Project status: Two technical blockers found during report writing. Recovery phases 7a (task_scam recall) and 7b (app perf) inserted before thesis drafting. Phase 8 is blocked until both close.
- Overall progress: 0 of 5 phases complete in milestone v1.2.
- Progress bar: [......] 0%

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
- The active Phase 7 closeout dataset is `data/synthetic/recovered-balanced.jsonl`, and the repaired held-out evaluation path is `data/splits/recovered-balanced/val.jsonl`; the older `data/splits/val.jsonl` sample run remains historical only.
- Milestone v1.2 is documentation-first: the scope is thesis writing plus evidence packaging, not a new product build.
- The thesis should read like a natural undergraduate report and should not expose internal GSD workflow language or planning-file names.

### Requirement Coverage Snapshot

- tracked requirements: 21
- mapped to phases: 21
- Unmapped: 0

### Active Risks and Watchpoints

- Graduation risk if the thesis overstates blocked quality results or hides the final `task_scam` recall shortfall — blocked until Phase 7a closes with PASS.
- Evaluation gate bug: `audit.ready=true` despite `task_scam` recall=0.44 — must be fixed in Phase 7a before any future eval result is trustworthy.
- Colab H100 Colab session time limit may interrupt long training runs; checkpoint resume is supported in the training CLI.
- The writing window is short, so the outline and evidence map must prevent chapter drift and last-minute scope changes.
- Thesis tone can easily drift into AI-like or internal-process wording if the draft is assembled directly from planning artifacts.
- Data leakage risk between training and evaluation splits.
- Explanation hallucination risk without strict evidence-linking.
- Quantization regressions that reduce recall on high-harm scam classes.
- Mixed-language/code-switch robustness drift over time.
- Primary live seed sources remain brittle in this environment (`canhbao.khonggianmang.vn` DNS failure, `scam.vn` HTTP 403); `tinnhiemmang.vn/canh-bao-lua-dao` is the current working fallback.
- The optional `gguf-runner-up` profile now has a registered artifact, but a direct `llama_cpp` load smoke still failed on that runner-up GGUF file; the validated shipped local paths remain `gguf-laptop` and `accelerated-local`.
- The remaining Claude API budget is small, so it should be spent only on targeted missing-class generation or judging work that improves final validated yield.
- The final repaired-holdout release verdict is `BLOCK` because `task_scam` recall is `0.44`, below the locked `0.90` floor, so any next milestone that targets deployment-grade quality should treat task-scam recovery as the main open model-quality risk.
- The local runtime still trusts the operator-managed off-repo model registry path instead of enforcing a trusted-root allowlist; that residual risk is accepted and documented in `.planning/phases/07-proposal-closeout-and-quantitative-validation/07-SECURITY.md`.

## Session Continuity

- Last session: 2026-05-28
- Stopped at: Phase 7a context gathered. Next work is `/gsd-plan-phase 7a` to plan the task_scam recovery execution.
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
- The balanced closeout corpus now lives at `data/synthetic/recovered-balanced.jsonl` with 3,000 rows.
- The repaired closeout split root now lives at `data/splits/recovered-balanced/`; `audit_release_eval_support` on `data/splits/recovered-balanced/val.jsonl` passed with support `{bank_impersonation: 56, zalo_social_engineering: 75, task_scam: 18, benign: 61}`.
- A full refreshed baseline training run completed on 2026-05-26 with `train_examples=2018`, `val_examples=210`, device `cuda`, full-precision LoRA, final checkpoint `D:\PROJEct\AI MODELS\proposal-closeout-full-2026-05-26\qwen3-4b-instruct-2507\trainer\checkpoint-505`, and training summary `D:\PROJEct\AI MODELS\proposal-closeout-full-2026-05-26\qwen3-4b-instruct-2507\adapter\training-summary.json`.
- A fresh baseline GGUF artifact was then converted successfully to `D:\PROJEct\AI MODELS\proposal-closeout-gguf-2026-05-26\qwen3-4b-instruct-2507\gguf-laptop.gguf` using the local Python 3.13 `convert_hf_to_gguf.py` script with direct `q8_0` output because no `llama-quantize` binary is available in this environment.
- The split repair fixed underdiverse-label handling so seed grouping stays intact when possible while labels with too few unique seeds can still populate active splits.
- The GGUF runtime closeout fix now uses a 2,048-token context window and chat JSON mode so held-out evaluation no longer silently truncates into malformed nested payloads.
- The first repaired-holdout rerun on 2026-05-26 failed at row 9 because the Phase 4 safety floor escalated a benign GGUF output on generic `credential_request` helper cues, then crashed when no in-scope label could be inferred. The local-model helper logic was patched so ambiguous helper cues now preserve the original benign decision instead of forcing a label or crashing.
- `src.model_adaptation.cli` now exposes `evaluate-release-split`, with progress printing and periodic checkpoint writes to the Phase 5 snapshot path.
- Latest-artifact resolution now prefers the newest registered adapter and GGUF artifacts, preventing stale May 16 or 17 artifacts from being selected after future train or convert runs.
- The repaired-holdout refresh completed end-to-end on 2026-05-26, regenerating `05-evaluation-snapshot.json`, `05-explanation-review-pack.json`, and the final release-eval markdown plus JSON artifacts.
- Phase 7 UAT now exists at `.planning/phases/07-proposal-closeout-and-quantitative-validation/07-UAT.md` with 5 of 5 checks passed.
- Phase 7 security now exists at `.planning/phases/07-proposal-closeout-and-quantitative-validation/07-SECURITY.md` with `status: verified` and `threats_open: 0`.
- Resume file: none (no `HANDOFF.json`, `.continue-here`, or interrupted-agent artifact detected)
- Next command: `/gsd-plan-phase 8` to create the execution plan for the thesis structure and evidence-map phase.
