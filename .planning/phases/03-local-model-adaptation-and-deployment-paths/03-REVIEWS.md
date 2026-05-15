---
phase: 3
reviewers: [claude]
reviewed_at: 2026-05-14T00:00:00Z
plans_reviewed:
  - 03-01-PLAN.md
  - 03-02-PLAN.md
review_focus: "Does choosing the best model for fine-tuning belong to Phase 3 or Phase 4?"
---

# Cross-AI Plan Review — Phase 3

## Claude Review

## Review: Model Selection Scope — Phase 3 vs Phase 4

### 1. Summary

Model selection (picking which candidate is best for fine-tuning) clearly belongs to Phase 3. The plans already encode this as a prerequisite gate before adaptation work begins.

### 2. Answer

**Model selection belongs to Phase 3.** It is not deferrable to Phase 4.

### 3. Evidence from the Plans

- Locked decisions explicitly state: "Run a three-model pilot before locking the main adaptation path."
- Plan 03-01 exists *specifically* to produce "deterministic baseline-winner and runner-up outputs" before any adapter training.
- Plan 03-02 is gated on Plan 03-01's output: "Training is limited to the baseline winner and runner-up selected in Plan 01."
- Phase 3 success criterion #1 requires "versioned adapted artifacts for the selected 4B baseline winner and runner-up" — selection must complete within Phase 3 for this criterion to be satisfiable.
- Phase 4's goal ("users receive clear risk decisions") and requirements (DET-01/02, XAI-01/02) are about detection behavior and explainability — they consume a trained model, they don't select one.

### 4. Risks if Selection Deferred to Phase 4

| Risk | Impact |
| ---- | ------ |
| Phase 3 cannot produce adapted artifacts without a winner | Success criterion #1 fails; Phase 3 incomplete |
| Phase 4 scope bloats with hardware evaluation it wasn't designed for | Timeline slip, mixed concerns |
| No GGUF quantized path testable in Phase 3 | Success criterion #2 unverifiable |
| Circular dependency: Phase 4 needs trained model -> but can't pick model until Phase 4 | Deadlock |

### 5. Recommendation

Keep model selection in Phase 3 exactly as planned. The pilot scorecard (Plan 03-01) is the correct gate. Phase 4 should receive a locked winner + runner-up as inputs, not make that decision itself.

Only thing Phase 4 owns: whether the *detection behavior* of the adapted model meets DET/XAI requirements — that's evaluation of the trained output, not selection of the base model.

---

## Local Larger Pilot Result

### Run Summary

- Date: 2026-05-14
- Source dataset: `data/processed/recovered-balanced-validated-claude-v2.jsonl`
- Sample strategy: 33 balanced validated samples with a fixed seed (`11 benign`, `11 suspicious`, `11 high-risk`)
- Runtime path: local 4-bit loading on the downloaded checkpoints under `D:\PROJEct\AI MODELS\base`
- Saved outputs:
  - `D:\PROJEct\AI MODELS\manifests\model-registry.json`
  - `data/manifests/phase3-large-pilot-2026-05-14.json`

### Locked Selection

- Baseline winner: `qwen3-4b-instruct-2507`
- Runner-up: `qwen3.5-4b`

### Quick Metrics

| Candidate | Accuracy | Risky recall | Avg sample time | Peak VRAM |
| --------- | -------- | ------------ | --------------- | --------- |
| `qwen3-4b-instruct-2507` | 0.3333 | 0.5000 | 0.3533s | 2.7731 GB |
| `qwen3.5-4b` | 0.3636 | 0.5000 | 0.9449s | 3.2765 GB |
| `qwen2.5-7b-instruct` | 0.4545 | 0.5000 | 0.5562s | 5.6168 GB |

### Lock Rationale

The larger compare did not produce a recall advantage for any checkpoint on this slice, so the Phase 3 selection logic fell back to the repo's intended tradeoff: preserve the 4B laptop-baseline rule, then favor better latency and memory fit. That keeps `qwen3-4b-instruct-2507` as the locked baseline winner and `qwen3.5-4b` as the runner-up for later training and deployment work.
