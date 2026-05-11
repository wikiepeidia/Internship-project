# Phase 3: Local Model Adaptation and Deployment Paths - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-09 (updated 2026-05-09)
**Phase:** 03-local-model-adaptation-and-deployment-paths
**Areas discussed:** Qwen checkpoint selection, pilot strategy, requirement fit, fine-tuning artifact strategy

---

## UPDATE SESSION (2026-05-09)

### Model Family Direction Under 8GB VRAM

| Option | Description | Selected |
| --- | --- | --- |
| Keep Gemma as the Phase 3 primary family | Continue the earlier Gemma direction even under the 8GB VRAM constraint | |
| Shift primary direction to Qwen | Optimize for stronger local feasibility on the target laptop hardware | ✓ |
| Explore Gemma and Qwen equally | Keep both families active through planning | |

**User's choice:** Shift the Phase 3 primary direction to Qwen.
**Notes:** The user started from a Gemma idea, then changed direction after comparing local hardware fit and candidate checkpoints.

### Primary Base-Model Track

| Option | Description | Selected |
| --- | --- | --- |
| Qwen 4B primary | Easier fit for 8GB VRAM, safer QLoRA and GGUF path | ✓ |
| Qwen 7B primary | More capacity, but more VRAM pressure and heavier deployment | |
| Dual-track: 4B baseline, 7B stretch | Plan around both from the start | |

**User's choice:** Qwen 4B primary.

### Candidate-Checkpoint Evaluation Policy

| Option | Description | Selected |
| --- | --- | --- |
| Three-model pilot first | Run a small comparison across all listed candidates before locking the main LoRA path | ✓ |
| Primary-first, compare fallbacks only if needed | Start with the primary and only test others on failure | |
| Primary plus one fallback only | Keep the comparison scope smaller | |

**User's choice:** Three-model pilot first.
**Candidate set provided by user:**

- Primary: `https://huggingface.co/Qwen/Qwen3.5-4B`
- Fallback 1: `https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507` (faster token outputs)
- Fallback 2: `https://huggingface.co/Qwen/Qwen2.5-7B-Instruct` (more parameters)

### Requirement Fit Against the Existing 8B Wording

| Option | Description | Selected |
| --- | --- | --- |
| Relax the requirement to allow 4B primary | Prioritize local feasibility on 8GB VRAM over the older 8B-class wording | ✓ |
| Keep 8B-class as mandatory | Phase 3 is incomplete unless an 8B-class adaptation path exists | |
| Keep 4B primary but require one 7B or 8B-class runner-up artifact | Try to stay near the original requirement while preserving the 4B main path | |

**User's choice:** Relax the requirement to allow 4B primary.
**Notes:** This creates a traceability task because current planning docs still describe Phase 3 around an open 8B model.

### Artifact Scope After the Pilot

| Option | Description | Selected |
| --- | --- | --- |
| Only the winning model | Tightest scope and smallest artifact surface | |
| Winner and runner-up | Keep one backup deployment path if the winner later causes runtime or quantization issues | ✓ |
| All three candidates | Maximum flexibility, highest cost | |

**User's choice:** Winner and runner-up.

### Artifact Type for the Selected Models

| Option | Description | Selected |
| --- | --- | --- |
| Adapters plus GGUF builds | Keeps reproducible tuning artifacts and deployment-ready local artifacts | ✓ |
| Adapters only | Smallest scope, but deployment conversion is deferred | |
| GGUF only | Simplest local inference path, weaker reproducibility for continued tuning | |
| Adapters, merged checkpoints, and GGUF builds | Most complete, but heavier in storage and conversion work | |

**User's choice:** Adapters plus GGUF builds.

## Deferred Ideas

- Gemma checkpoint discussion is deferred unless the Qwen pilot underperforms.
- Merged checkpoint export is explicitly out of current Phase 3 scope.
