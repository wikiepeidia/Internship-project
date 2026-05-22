<!-- markdownlint-disable MD022 MD032 MD033 MD034 MD055 MD056 MD060 -->

# Phase 3: Local Model Adaptation and Deployment Paths - Research

**Researched:** 2026-05-09
**Domain:** Local Qwen checkpoint selection, parameter-efficient fine-tuning, GGUF packaging, and runtime profile switching
**Confidence:** MEDIUM

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Phase 3 should pivot from the earlier Gemma idea to a Qwen-centered path because the current deciding constraint is realistic local operation on 8GB VRAM.
- **D-02:** Run a three-model pilot before locking the main adaptation path.
- **D-03:** Primary pilot candidate: `https://huggingface.co/Qwen/Qwen3.5-4B`
- **D-04:** Fallback candidate 1: `https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507`
- **D-05:** Fallback candidate 2: `https://huggingface.co/Qwen/Qwen2.5-7B-Instruct`
- **D-06:** The pilot is a real checkpoint comparison, not a loose backup list.
- **D-07:** Relax the old `MOD-01` 8B-only wording to allow a 4B primary path when that better fits the 8GB VRAM target.
- **D-08:** After the pilot, build full adaptation artifacts for the winning model and the runner-up.
- **D-09:** Required Phase 3 artifact pair: adapters plus GGUF builds.
- **D-10:** Large model artifacts stay local-only and untracked by git.
- **D-11:** Phase 3 must preserve the existing `AnalyzerBackend` seam and the typed Phase 2 runtime contracts.
- **D-12:** Runtime selection must stay explicit and local-first. Do not introduce cloud-default inference.

### Claude's Discretion
- Exact pilot evaluation rubric and candidate-selection thresholds.
- Exact QLoRA stack and conversion pipeline details.
- Exact accelerated runtime implementation, as long as it preserves the Phase 2 runtime seam and local-only posture.
- Whether the primary 4B path lands on a base or instruct checkpoint variant if upstream availability changes.

### Deferred Ideas (OUT OF SCOPE)
- Revisit Gemma only if the Qwen pilot underperforms on quality or hardware feasibility.
- Merged checkpoints are not required in the Phase 3 baseline.
- Final threat-labeling, explanation-policy tuning, and release gating remain Phase 4/5 work.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MOD-01 | System supports LoRA-based fine-tuning of an open-source model using project dataset artifacts. | Recommends a pilot-first QLoRA pipeline over the existing Phase 1 splits, with adapter manifests and reproducible config snapshots. |
| RUN-02 | System provides a GGUF quantized inference path that works on consumer laptop CPU/iGPU baseline. | Recommends adapter-to-GGUF packaging backed by `llama.cpp` or `llama-cpp-python`, with explicit profile metadata and CPU-safe defaults. |
| RUN-03 | System provides an optional accelerated inference path for prosumer GPU hardware. | Recommends a second local backend profile using the same typed runtime contract, with doctor checks that make hardware/profile readiness explicit. |
|

**Traceability note:** Phase 3 is now aligned around a 4B-primary path for the laptop baseline, with larger comparison candidates treated as optional capacity checks rather than the default deployment target.
</phase_requirements>

## Project Constraints (from workspace and prior phases)

- Prefer `C:/Users/wikiepeidia/AppData/Local/Programs/Python/Python313/python.exe` when concrete Python execution matters in this repo.
- Do not create virtual-environment directories inside the OneDrive workspace.
- Keep raw user text local and memory-only by default; Phase 3 must not weaken the Phase 2 privacy boundary.
- Reuse the existing dataset-manifest pattern from `src/data_pipeline/versioning/manifest.py` instead of inventing a second lineage format for model artifacts.
- Preserve the shipped Phase 2 runtime surface: `AnalysisRequest`, `AnalysisResult`, `DoctorStatus`, `AnalyzerBackend`, `RuntimeService`, and the stdin-first CLI entrypoint.

## Summary

Phase 3 should be planned as a split between model adaptation plumbing and runtime integration, not as one undifferentiated "train a model" step. The safest path is: define a candidate registry and pilot scorecard first, train only the winning model plus runner-up with a reproducible QLoRA flow, convert those artifacts into GGUF builds for the laptop baseline, then expose an explicit accelerated local profile that still returns the same Phase 2 result schema.

The current repo already has the right runtime seam for this: `AnalyzerBackend` in `src/runtime/analyzers/base.py`, typed request/result contracts in `src/runtime/contracts.py`, and local-only boundary enforcement in `src/runtime/service.py`. Phase 3 does not need a second user-facing analyzer path. It needs a model-adaptation package that feeds artifacts into the existing runtime.

**Primary recommendation:** Create a new `src/model_adaptation/` package for candidate metadata, pilot evaluation, training, and conversion. Keep runtime backends under `src/runtime/analyzers/` so the Phase 2 CLI remains stable while backend selection becomes explicit through settings and doctor checks.

## Standard Stack

### Core

| Library | Version family | Purpose | Why this fits Phase 3 |
|---------|----------------|---------|------------------------|
| Python | 3.13 | Training orchestration, registry, CLI glue | Already the repo standard and matches the preferred local interpreter. |
| PyTorch | 2.x | Model training and accelerated inference path | Standard base for PEFT and local GPU execution. |
| Transformers | 4.5x+ | Checkpoint loading, tokenization, local model APIs | Needed for Qwen-family checkpoint handling and a consistent HF workflow. |
| PEFT | 0.1x | LoRA and QLoRA adapters | Directly supports the adapter-first artifact strategy. |
| Accelerate | 1.x | Training orchestration and device placement | Standard glue for local fine-tuning workflows. |
| TRL `SFTTrainer` | 0.2x | Supervised fine-tuning wrapper | Good fit for instruction-style adaptation without overbuilding RL-heavy workflows. |
| llama.cpp / llama-cpp-python | current tested build | GGUF conversion target and CPU baseline runtime | Best fit for the explicit local GGUF path in `RUN-02`. |
| safetensors | current | Safe checkpoint storage | Standard for adapter and merged-weight metadata handling. |

### Supporting

| Library | Purpose | When to Use |
|---------|---------|-------------|
| bitsandbytes | 4-bit QLoRA on supported GPU setups | Use when the local hardware and OS support it; keep a dry-run path so the workflow still validates on machines without GPU support. |
| huggingface_hub | Resolving remote checkpoint metadata and downloads | Use for checkpoint provenance and local cache management, not for pushing project artifacts remotely. |
| psutil | Lightweight hardware/profile detection | Use inside doctor/profile checks when deciding whether GGUF or accelerated mode is viable. |
| hashlib / json / pathlib | Manifests, checksums, and local metadata | Reuse the same integrity style the dataset pipeline already uses. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Adapter-first artifacts | Merged checkpoints only | Simpler runtime distribution, but much worse for reproducibility, retraining, and local storage discipline. |
| GGUF CPU baseline | Transformers-only runtime everywhere | Easier one-stack story, but weaker for the laptop CPU/iGPU requirement and larger runtime footprint. |
| Pilot-first checkpoint selection | Train one checkpoint immediately | Faster to start, but risky because Phase 3 is explicitly balancing local feasibility against model capacity. |
| vLLM/TensorRT-LLM as primary runtime | Local workstation/server profile | Strong server stacks, but not the right default for offline consumer-laptop deployment. |

## Architecture Patterns

### Recommended Project Structure

```text
src/
├── config/
│   └── settings.py
├── model_adaptation/
│   ├── __init__.py
│   ├── schemas.py          # candidate, scorecard, artifact manifest DTOs
│   ├── catalog.py          # locked candidate set and profile metadata
│   ├── registry.py         # local artifact metadata, checksums, selection records
│   ├── pilot.py            # three-model pilot evaluation harness
│   ├── data.py             # dataset formatting and split loading for tuning
│   ├── prompts.py          # prompt formatting / chat template helpers
│   ├── training.py         # QLoRA orchestration and adapter save flow
│   ├── convert.py          # adapter -> GGUF packaging helpers
│   └── cli.py             # dry-run friendly operator entrypoints
└── runtime/
    ├── contracts.py
    ├── service.py
    ├── doctor.py
    └── analyzers/
        ├── base.py
        ├── heuristic.py
        ├── gguf.py         # CPU/iGPU baseline profile
        └── accelerated.py  # optional GPU profile
```

### Pattern 1: Candidate Registry Before Training

**What:** Represent each checkpoint candidate, hardware assumptions, artifact outputs, and pilot results as typed metadata before starting expensive adaptation work.

**Why:** Phase 3 is not just "train Qwen." It is "choose a realistic local model path under 8GB VRAM and keep a backup profile." A registry makes that explicit and auditable.

### Pattern 2: Adapter-First Artifact Lifecycle

**What:** Treat adapters as the source-of-truth training artifact, then derive GGUF deployment builds from the selected models.

**Why:** This matches the user decision to keep adapters plus GGUF, avoids git bloat, and makes continued tuning possible without re-downloading or re-merging everything.

### Pattern 3: Explicit Runtime Profiles Behind One Analyzer Contract

**What:** Add new model backends that implement `AnalyzerBackend`, while keeping `RuntimeService` and the CLI centered on the same typed Phase 2 contracts.

**Why:** This keeps Phase 3 compatible with existing runtime tests and leaves Phase 4 free to expand decision quality without rewriting entry surfaces.

### Pattern 4: Manifest-Backed Local Artifacts

**What:** Reuse checksum and version-manifest ideas from `src/data_pipeline/versioning/manifest.py` for adapters, GGUF files, and pilot scorecards.

**Why:** The repo already has a good integrity pattern. Phase 3 should extend it for model artifacts instead of inventing a second, incompatible lineage scheme.

## Integration With Existing Code

- `src/runtime/analyzers/base.py`: keep this as the backend seam. New GGUF and accelerated analyzers should implement the existing protocol.
- `src/runtime/contracts.py`: preserve `AnalysisResult` and `DoctorStatus` shape so the CLI and future Phase 4 logic stay stable.
- `src/runtime/service.py`: continue enforcing normalize-first input handling, text-only boundary checks, and fail-closed behavior.
- `src/config/settings.py`: extend runtime and model-adaptation fields here rather than introducing a parallel config system.
- `src/data_pipeline/versioning/manifest.py`: mirror its checksum and save behavior for model-artifact metadata.
- `data/splits/`: use existing Phase 1 split artifacts as the pilot and fine-tuning source of truth.

## Anti-Patterns to Avoid

- **Training before candidate bookkeeping exists:** this makes winner/runner-up selection opaque and hard to reproduce.
- **Pushing raw model binaries into git:** Phase 3 artifacts are large and intentionally local-only.
- **Adding a second public runtime surface:** the Phase 2 CLI already exists; Phase 3 should extend the backend, not fork the product interface.
- **Treating GGUF as the only artifact:** this loses the retraining-friendly adapter path the user explicitly asked to keep.
- **Using cloud fallback to hide local failures:** Phase 3 must keep local failure explicit, visible, and doctor-diagnosable.

## Recommended Build Profiles

### Profile A: Laptop Baseline

- Winning or runner-up GGUF build
- CPU or iGPU-friendly quantized runtime
- Explicit doctor checks for local model path readiness
- Same `AnalysisResult` contract as Phase 2

### Profile B: Optional Accelerated Local Path

- Same selected checkpoint family, but loaded through a stronger local backend
- Explicit profile selection and hardware readiness reporting
- No schema drift relative to the GGUF baseline

## Research Outcome

Phase 3 should be planned as four executable steps: candidate registry and pilot harness, QLoRA adapter training, GGUF baseline runtime integration, and accelerated-profile integration plus docs and regression coverage.

## RESEARCH COMPLETE
