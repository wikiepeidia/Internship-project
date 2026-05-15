# Phase 3: Local Model Adaptation and Deployment Paths - Context

**Gathered:** 2026-05-09
**Status:** Reopened for real training follow-through

## Phase Boundary

Adapt the current local runtime from Phase 2 to a real local model backend and deployment artifact flow. Phase 3 should select a Qwen-family checkpoint through a short pilot on the project dataset, fine-tune the selected models with parameter-efficient adaptation, and ship laptop-safe local deployment artifacts without changing the Phase 2 CLI or runtime contract.

**Scope guardrails:**

- Keep v1 text-only and offline/local-first.
- Preserve the existing stdin-first CLI and typed runtime contract surfaces.
- Stay focused on model adaptation and runtime deployment paths, not final DET/XAI behavior tuning or release-gate evaluation.
- Large model artifacts remain local-only and untracked.

**Hardware constraint:** Planning should optimize around an 8GB VRAM laptop target, then keep an optional stronger-hardware path explicit rather than implicit.

## Implementation Decisions

### Model Family and Pilot Strategy

- **D-01:** Pivot the Phase 3 primary model family from the earlier Gemma discussion toward Qwen because the current decision driver is 8GB VRAM feasibility on local hardware.
- **D-02:** Run a three-model pilot on the project dataset before committing to the main LoRA/QLoRA path.
- **D-03:** Primary pilot candidate: `https://huggingface.co/Qwen/Qwen3.5-4B`
- **D-04:** Fallback candidate 1: `https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507` (user rationale: faster token outputs)
- **D-05:** Fallback candidate 2: `https://huggingface.co/Qwen/Qwen2.5-7B-Instruct` (user rationale: larger-parameter comparison)
- **D-06:** The pilot is intended as a real checkpoint comparison, not just a contingency list; all three candidates should be evaluated before full adaptation scope is locked.

### Requirement Interpretation

- **D-07:** `MOD-01` and the Phase 3 goal are interpreted as a 4B-primary local model path with optional larger comparison candidates because the user explicitly prioritized local feasibility on 8GB VRAM over the older 8B-only wording.
- **D-07a:** Operationally, the laptop baseline winner must come from the 4B candidate subset; the 7B candidate remains a comparison or accelerated-path option, not the default laptop baseline.

### Artifact Strategy

- **D-08:** After the pilot, produce full adaptation artifacts for the winning model and the runner-up, not just the winner.
- **D-09:** Required Phase 3 artifact set for those two models is adapters plus GGUF builds.
- **D-10:** Merged checkpoints are not required for Phase 3 scope.
- **D-11:** Large training and deployment artifacts stay local-only and untracked by git.

### Locked Follow-up Decisions (2026-05-14)

- **D-15:** The larger local pilot on 33 balanced validated samples locked `qwen3-4b-instruct-2507` as the laptop baseline winner.
- **D-16:** `qwen3.5-4b` remains the locked runner-up for adaptation follow-through and backup deployment work.
- **D-17:** Phase 3 is reopened until a real non-dry-run QLoRA training path is executable for the locked winner and runner-up.
- **D-18:** The CPU/iGPU target in Phase 3 refers to GGUF inference after adaptation. LoRA/QLoRA remains the training method, and the current plan assumes local GPU-capable execution for real training rather than CPU-only fine-tuning.

### Runtime Compatibility Constraints

- **D-12:** Phase 3 must preserve the existing `AnalyzerBackend` seam and swap the backend behind that interface rather than replacing the Phase 2 runtime surface.
- **D-13:** Phase 3 must keep the typed request, result, and doctor contracts stable enough for the existing CLI and runtime tests to remain meaningful.
- **D-14:** Runtime selection must stay explicit and local-first; Phase 3 must not introduce cloud-default inference.

### Claude's Discretion

- Exact pilot evaluation protocol and selection rubric for the three candidate checkpoints.
- Exact PEFT/QLoRA configuration, conversion pipeline, and quantization settings.
- Whether the primary Qwen 4B path should use a base or instruct checkpoint variant if upstream availability or compatibility changes during planning.
- Exact accelerated runtime implementation for stronger hardware, as long as it stays consistent with the offline/local deployment requirement and the Phase 2 backend seam.

## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Requirements and Status

- `.planning/REQUIREMENTS.md` — `MOD-01`, `RUN-02`, and `RUN-03` define the acceptance surface for the 4B-primary baseline plus optional larger comparison candidates.
- `.planning/PROJECT.md` — Core constraints: text-only v1, offline/local inference, privacy-first behavior.
- `.planning/ROADMAP.md` — Phase 3 success criteria and dependency chain from the shipped Phase 2 runtime.
- `.planning/STATE.md` — Phase 2 is closed; next actionable work is Phase 3 planning.

### Research

- `.planning/research/STACK.md` — Recommended Phase 3 stack: Transformers + PEFT/QLoRA + GGUF + llama.cpp.
- `.planning/research/ARCHITECTURE.md` — Structured-output-first and offline modular runtime patterns.
- `.planning/research/PITFALLS.md` — Quantization regression, privacy logging, synthetic diversity, and recall risks that Phase 3 must not ignore.

## Existing Code Insights

### Reusable Assets

- `src/runtime/analyzers/base.py` already defines the `AnalyzerBackend` protocol seam that Phase 3 should reuse for a real model backend.
- `src/runtime/contracts.py` already defines `AnalysisRequest`, `AnalysisResult`, `SuspiciousCue`, and `DoctorStatus`, which are the compatibility surface for any Phase 3 backend.
- `src/runtime/service.py` already centralizes normalize-first orchestration, boundary checks, fail-closed behavior, and default backend wiring.
- `src/config/settings.py` already exposes runtime flags such as `runtime_backend`, fail-closed policy, cue cap, and raw-text persistence guardrails.
- `src/runtime/cli.py` and `src/runtime/doctor.py` already provide the public runtime entrypoints that Phase 3 should extend rather than replace.

### Established Patterns

- Phase 2 kept privacy and scope boundaries inside the runtime service instead of scattering them across the CLI.
- Backend behavior is already expected to report readiness through `doctor()` and to return typed analysis results through `analyze()`.
- The CLI remains stdin-first and one-message-per-run, which keeps local testing simple and reduces accidental persistence.

### Integration Points

- Phase 3 model selection and adaptation must plug into the current runtime backend seam instead of creating a second inference path.
- GGUF deployment artifacts should support the laptop baseline required by `RUN-02` while keeping room for a stronger accelerated profile for `RUN-03`.
- Any checkpoint-selection pilot should use the Phase 1 dataset artifacts and must preserve the Phase 2 output contract so Phase 4 can build threat labels and explanation logic on top of a stable result surface.

## Specific Ideas

- The current user preference is not "best raw parameter count"; it is "best realistic local path on 8GB VRAM," which is why a 4B Qwen primary track was selected over the earlier Gemma direction.
- The three candidate checkpoints are intentionally mixed across two sizes: two 4B-class candidates for the locked laptop-baseline path and one 7B candidate as a larger-capacity comparison.
- The pilot is not just model research. It should materially decide which model becomes the winning path and which remains the backup deployment path.
- Planning should treat adapters plus GGUF as the minimum useful artifact pair because adapters support reproducibility and continued tuning while GGUF supports local deployment.
- Because large artifacts remain local-only, planning should include manifest, checksum, or version metadata for reproducibility without assuming those binaries live in git.

## Deferred Ideas

- Revisit Gemma only if the Qwen pilot fails quality or hardware-feasibility expectations.
- Exact merged-checkpoint export workflow is deferred; it is out of current Phase 3 scope unless planning later finds a hard blocker without it.
- Final threat-label behavior, explanation rubric, and release-gate metrics remain Phase 4 and Phase 5 concerns and should not expand Phase 3 scope.

## Current Re-entry Point

- The pilot decision is no longer the open question. The next actionable work is to make `src/model_adaptation/training.py` run a real non-dry-run trainer for `qwen3-4b-instruct-2507`, with `qwen3.5-4b` kept as runner-up.
- Missing local readiness items currently known in-chat and in UAT: `peft`, `trl`, `datasets`, plus a concrete trainer callable wired into the current dry-run scaffold.
- GGUF laptop support remains the post-training CPU/iGPU inference target, not the training device target.

---

*Phase: 03-local-model-adaptation-and-deployment-paths*
*Context updated: 2026-05-14 after larger pilot lock and Phase 3 reopen*
