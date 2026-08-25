# Phase 40: Multi-Model Training Evidence - Context

**Gathered:** 2026-08-17
**Status:** Executing Plan 40-05; the dated execution amendment supersedes the earlier Colab-only routing language below

<domain>
## Phase Boundary

Phase 40 creates genuine, reproducible full-training evidence for two models:
Qwen QLoRA and a PhoBERT classification-head baseline. A bounded ordinary-LoRA
probe remains part of the resource-feasibility evidence, but ordinary LoRA is
not a third full model. The phase measures local feasibility on the RTX 5050,
executes the two fresh full runs locally, and produces curves plus a
validation-only comparison. It does not evaluate or inspect the held-out test
rows; that belongs exclusively to Phase 41.

### Execution amendment — 2026-08-25

The operator changed the full QLoRA route after the genuine RTX 5050 probe
proved four-bit training feasible. The fresh full QLoRA run starts locally at
step zero from the same pinned base and frozen controls, under the same
train/validation-only evidence contract; it does not reuse a probe adapter or
checkpoint. Colab remains available for ordinary LoRA, PhoBERT, or recovery,
but a complete verified local QLoRA run satisfies that branch and must not be
duplicated on Colab merely to obtain graphs. Raw logs, checkpoint generations,
validation metrics, system/GPU telemetry, and GGUF verification provide the
required evidence locally. Any speed comparison against a model trained on a
different accelerator is explicitly hardware-confounded.

### User-approved local-only scope amendment — 2026-08-25

This amendment is the controlling execution scope. The primary sequence is
fresh local Qwen QLoRA, verified run evidence, verified Q8_0 GGUF export, then
fresh local PhoBERT on the same train/validation authority. The sealed
ordinary-LoRA probe is retained exactly as resource-pressure and ETA evidence;
no full ordinary-LoRA run is required or authorized. The quality comparison is
therefore Qwen QLoRA versus PhoBERT. It does not claim a full-run
LoRA-versus-QLoRA accuracy result.

The earlier three-run request and generated Colab handoff remain immutable
historical provenance and are not evidence that those runs executed. Colab is
not part of the primary path and must not be used merely to obtain faster
hardware or prettier graphs. It may be activated only as a documented
contingency before the reserved Phase 41 partition is opened, and only if the
frozen validation review finds the local result unacceptable. Once the
reserved partition has been opened, its outcome must never trigger retraining,
dataset repair, Colab use, or checkpoint reselection.

Machine-readable additive authority is
`data/models/phase40/two-full-model-scope-amendment.json`. It binds immutable
request SHA-256 `2512dbe6d7c5b8c16141ebdbdc848382e56b3a5737e8aeea51d7fb89447c643a`,
activates only the QLoRA and PhoBERT run IDs, and embeds the exact allowlisted
post-amendment finalizer files plus `comparison_finalizer_authority.source_tree_sha256`.
The active training/GGUF/PhoBERT chain remains bound to immutable
`source-runtime-v3`; the amended comparison finalizer runs only from a repo
tree matching the embedded authority and never mutates v3.

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

### Fresh full runs (originally Colab-first)
- Start one fresh genuine four-bit Qwen QLoRA run and one fresh PhoBERT
  classification-head run locally from their pinned base revisions. No
  ordinary-LoRA full run follows the sealed probe.
- Hold each model's frozen dataset hashes/order, random seed, epochs, and
  declared architecture-appropriate controls constant. Qwen and PhoBERT are
  compared on the same validation identities and evaluator, not falsely
  described as optimizer- or tokenization-matched architectures.
- The 72.83-minute QLoRA probe estimate covers the extrapolated optimizer
  schedule plus one measured evaluation/save overhead. It is not an observed
  end-to-end duration for the full evidence cadence. The live full-run cadence
  currently projects roughly 12.85 hours because repeated 219-row generation
  dominates wall time; that value remains interim until final evidence seals.
- Requested QLoRA must fail closed unless the runtime proves
  `quantization_mode == "4bit-qlora"`. The current fallback in
  `src/model_adaptation/training.py` must be hardened before the real run.

### PhoBERT baseline
- Fully fine-tune a normal PhoBERT classification head on the same frozen
  training and validation data.
- Do not add QLoRA to PhoBERT merely for novelty. The bounded LoRA/QLoRA probes
  answer the laptop resource-treatment question; the two complete models
  answer the validation-quality question.

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
- Phase 41 evaluates the two frozen checkpoints against the test split once.
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

- Formal executable Phase 40 plans were produced after Phase 39 closure; Plans
  40-01 through 40-04 are complete and Plan 40-05 is executing.
- Test evaluation and optional all-data deployment fitting remain Phase 41 work.

</deferred>
