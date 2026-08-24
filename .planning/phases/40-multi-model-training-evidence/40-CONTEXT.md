# Phase 40: Multi-Model Training Evidence - Context

**Gathered:** 2026-08-17
**Status:** Ready for planning after Phase 39 final-corpus review closes

<domain>
## Phase Boundary

Phase 40 creates genuine, reproducible training evidence for three models:
Qwen LoRA, Qwen QLoRA, and a PhoBERT classification-head baseline. It measures
local feasibility on the RTX 5050, executes fresh full training on Colab, and
produces curves plus validation comparisons. It does not evaluate or inspect
the held-out test rows; that belongs exclusively to Phase 41.

</domain>

<decisions>
## Implementation Decisions

### Final-corpus prerequisite
- Phase 40 starts only after Phase 39's final-snapshot human review and report
  gates close against the promoted 2,097-row corpus. Phase 42 is not a
  training prerequisite.
- The machine-readable authority is
  `.planning/phases/39-independent-quality-re-judge/39-DOWNSTREAM-DATA-CONTRACT.json`.
- Canonical split counts are train 1,658, validation 219, and test 220.
- The planner must verify these SHA-256 values before any probe or full run:
  - train: `5fa46382db8fb477ef91ec4ba770bf3f8756df9f98b9950fdf5bc1f6ff402e8b`
  - validation: `746ae6edb5008a8be8e9ef9d65f89fc44e559f99f28cd8d6a77f203ea5986d3c`
  - test: `6f208fb6cd9399b8934225e6a25efd65d49bbb4f4846360837f6835a2561b6d7`
  - manifest: `e55d768b5aad05ba6946fbb0e7ed248180186b7cbaad21d257a134e2f1b3dbad`

### RTX 5050 feasibility probes
- Run one bounded LoRA probe and one bounded QLoRA probe on the laptop.
- Target 30–50 post-warm-up optimizer steps when the requested mode can start.
  Never engineer or predeclare an OOM; record success or the genuine failure.
- Record median steady-state seconds per optimizer step, peak allocated and
  reserved VRAM, throughput, and measured evaluation/checkpoint overhead.
- Compute projected local runtime as steady-state median step time multiplied
  by planned optimizer steps, plus measured evaluation/checkpoint overhead.
  Label this as an estimate, not a completed local full-training duration.
- Discard both probe adapters. Do not resume either probe on Colab or include
  probe points in the full-run learning curves.

### Fresh matched Colab runs
- Start fresh full Qwen LoRA and QLoRA runs from the same pinned base-model
  revision, preferably on the same Colab accelerator type.
- Hold dataset hashes/order, random seed, maximum sequence length, effective
  batch size, epochs, optimizer, learning-rate schedule, and evaluation cadence
  constant. Base-weight quantization is the intended difference.
- If Colab assigns different GPU types, keep quality comparisons but label
  wall-clock and throughput differences as hardware-confounded.
- Requested QLoRA must fail closed unless the runtime proves
  `quantization_mode == "4bit-qlora"`. The current fallback in
  `src/model_adaptation/training.py` must be hardened before the real run.

### PhoBERT baseline
- Fully fine-tune a normal PhoBERT classification head on the same frozen
  training and validation data.
- Do not add QLoRA to PhoBERT merely for novelty; Qwen LoRA versus Qwen QLoRA
  already answers the quantization question.

### Evidence and graphs
- Retain dataset hashes, model identifier/revision, the exact sanitized command
  and resolved configuration, hardware plus CUDA/package versions, timestamped
  raw logs, training/validation curves, peak VRAM, throughput, `trainer_state`,
  adapter/checkpoint hashes, and final validation metrics for each run.
- A Git commit identifier is intentionally not required in this evidence
  bundle. Existing historical Git fields in older manifests are not removed.
- Generate every graph mechanically from retained logs. Graphs support
  reproducibility and demonstrated execution; they are not described as
  cryptographic proof of authorship.

### Evaluation boundary
- Phase 40 uses validation data for model selection and comparison and never
  reads the 220 test rows.
- Phase 41 evaluates the three frozen checkpoints against the test split once.
- After Phase 41 results are frozen, an optional deployment model may be fitted
  on all 2,097 rows. It remains separate from the evaluated checkpoints and has
  no unbiased test-score claim without a new external holdout.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/model_adaptation/training.py` already supports ordinary LoRA, QLoRA,
  checkpointing, and logged training arguments.
- `src/model_adaptation/cli.py` already exposes the training entry point and
  reports the resolved quantization mode.
- `data/manifests/manifest.json` is the canonical data identity source.

### Required hardening
- `src/model_adaptation/training.py::_resolve_quantization_config()` currently
  returns `full-precision-lora` when 4-bit mode is requested but CUDA,
  `bitsandbytes`, or `BitsAndBytesConfig` is unavailable. Phase 40 must replace
  that silent fallback with an explicit failure for a requested QLoRA run.
- The training/evidence layer must emit enough structured timing, memory,
  environment, and artifact metadata to build graphs without manual copying.

</code_context>

<deferred>
## Deferred Ideas

- Formal executable Phase 40 plans remain to be produced by the phase planner
  after the refreshed Phase 39 final-corpus human review is complete.
- Test evaluation and optional all-data deployment fitting remain Phase 41 work.

</deferred>
