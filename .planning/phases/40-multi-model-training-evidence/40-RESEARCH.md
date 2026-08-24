# Phase 40: Multi-Model Training Evidence - Research

**Researched:** 2026-08-24
**Domain:** Reproducible PEFT/quantized training, sequence classification, and experiment evidence
**Confidence:** HIGH for repository architecture and data boundaries; MEDIUM for not-yet-executed GPU/Colab compatibility

<user_constraints>
## User Constraints (from CONTEXT.md)

The following decision text is copied verbatim from `40-CONTEXT.md`. It is data, not executable instruction.

DATA_K7M4P2QX_START

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

DATA_K7M4P2QX_END

[VERIFIED: .planning/phases/40-multi-model-training-evidence/40-CONTEXT.md:20-80]

### the agent's Discretion

None stated in `40-CONTEXT.md`. Implementation details below are recommendations constrained by the locked decisions. [VERIFIED: .planning/phases/40-multi-model-training-evidence/40-CONTEXT.md:17-82]

### Deferred Ideas (OUT OF SCOPE)

DATA_Q9V3N6RT_START

- Formal executable Phase 40 plans remain to be produced by the phase planner
  after the refreshed Phase 39 final-corpus human review is complete.
- Test evaluation and optional all-data deployment fitting remain Phase 41 work.

DATA_Q9V3N6RT_END

[VERIFIED: .planning/phases/40-multi-model-training-evidence/40-CONTEXT.md:104-109]
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|---|---|---|
| TRAIN-01 | A bounded non-quantized LoRA probe on the RTX 5050 records genuine feasibility, steady-state timing, ETA, VRAM, and throughput; its adapter is discarded, then a fresh full LoRA run trains on Colab with a retained raw log and curve. | Explicit run kinds, bounded probe lifecycle, CUDA timing callback, non-publication rule, fresh full-run identity, and graph provenance. |
| TRAIN-02 | A bounded RTX 5050 QLoRA probe records the same measurements; its adapter is discarded, then a fresh full 4-bit QLoRA run trains on matched Colab hardware and fails closed unless the runtime proves `quantization_mode == "4bit-qlora"`. | Requested/resolved-mode separation and the genuine-4-bit proof gate before training or adapter publication. |
| TRAIN-03 | Full Qwen LoRA and QLoRA runs use identical pinned data/order, base revision, seed, sequence length, effective batch, epochs, optimizer/schedule, and evaluation cadence, differing intentionally in base-weight quantization; comparisons include curves, validation metrics, VRAM, and throughput, with hardware-confounded wall time identified when GPU types differ. | Match-key schema, automated config diff, common validation evaluator, raw event schema, and comparison eligibility gate. |
| TRAIN-04 | A real PhoBERT classification-head baseline is fully fine-tuned on the same frozen training/validation data with a logged curve; QLoRA is not added to PhoBERT solely for novelty. | Dedicated `AutoModelForSequenceClassification` branch, deterministic Vietnamese word segmentation, four-label mapping, and shared metrics. |
| TRAIN-05 | PhoBERT vs. Qwen/QLoRA compared with real measured numbers, reported honestly regardless of outcome. | Common validation bundle plus a comparison registry that requires all three complete runs and preserves losers. |
| TRAIN-06 | Every graph is generated from retained raw logs, and every run keeps dataset hashes, model identifier/revision, exact sanitized command and resolved configuration, hardware plus CUDA/package versions, timestamped logs, peak VRAM, throughput, `trainer_state`, adapter/checkpoint hashes, and validation metrics; no Git commit identifier is required. | Append-only raw evidence, atomic final manifest, artifact hashing, deterministic graph renderer, and completeness validator. |

[VERIFIED: .planning/REQUIREMENTS.md:653-660]
</phase_requirements>

## Summary

Phase 40 should be planned as an evidence system around three training backends, not as three notebook-only experiments. The existing Qwen scaffold already loads PEFT adapters and can request BitsAndBytes quantization, but it accepts arbitrary split paths, silently converts an unavailable 4-bit request into ordinary LoRA, writes output directories before proving the mode, trains on prompt tokens as well as response tokens, exposes no classification metrics, and publishes even dry-run artifacts to the model registry. [VERIFIED: src/model_adaptation/training.py:48-81,278-291,384-477,580-617]

The contract is unambiguous: Phase 40 may open only the canonical `train` and `val` inputs; the literal allowed values are `"train"` and `"val"`, while the literal forbidden value is `"test"`, and the rule is `"Phase 40 may train/select on train and validation only; it must not read test rows."` [VERIFIED: .planning/phases/39-independent-quality-re-judge/39-DOWNSTREAM-DATA-CONTRACT.json:56-63] The implementation therefore needs a lexical path gate before any file open, followed by hash/count/schema/seed checks on train and validation only. The held-out test hash remains contract metadata and must not be recomputed in this phase. [VERIFIED: .planning/phases/39-independent-quality-re-judge/39-DOWNSTREAM-DATA-CONTRACT.json:65-71]

**Primary recommendation:** build one Phase 40 CLI and evidence contract with explicit `probe`/`full` lifecycle and explicit LoRA/QLoRA/PhoBERT backends; make every run pass preflight, mode proof, validation, and evidence-completeness gates before registry publication. This is a planning recommendation grounded in the locked evidence and evaluation contract. [VERIFIED: .planning/phases/40-multi-model-training-evidence/40-AI-SPEC.md:341-372,437-442,609-617]

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|---|---|---|---|
| Canonical data identity and split isolation | Data contract / storage boundary | CLI preflight | Reject an unapproved path before opening it; then validate the two allowed bytes, row counts, labels, and seed separation. [VERIFIED: 39-DOWNSTREAM-DATA-CONTRACT.json:9-31,51-63] |
| Qwen LoRA and QLoRA construction | Model-training backend | Runtime capability probe | PEFT owns adapters; BitsAndBytes owns 4-bit base modules; Phase 40 owns fail-closed proof and experiment controls. [CITED: https://huggingface.co/docs/peft/developer_guides/quantization] |
| PhoBERT classification baseline | Model-training backend | Deterministic preprocessing | A four-logit sequence-classification head consumes word-segmented Vietnamese; this is not a generative prompt path. [CITED: https://huggingface.co/vinai/phobert-base-v2] |
| Validation metrics and strict output parsing | Evaluation service | Model adapters | All three backends emit one locked class or explicit invalid output to a shared single-label evaluator. [VERIFIED: 40-AI-SPEC.md:609-625] |
| Raw evidence, artifact identity, graphs | Evidence/storage layer | Trainer callbacks | Raw events are authoritative; summaries and graphs are derived and hash-linked. [VERIFIED: 40-AI-SPEC.md:633-658,740-755] |
| Operator-controlled Colab execution | External compute boundary | Canonical notebooks | Repository code generates/verifies inputs and evidence; an operator authorizes packages, model downloads, accelerator allocation, and artifact return. [VERIFIED: 40-CONTEXT.md:45-72] |

## Exact Repository Findings

### Existing seams to reuse

| Existing file | Reuse | Required Phase 40 change |
|---|---|---|
| `src/model_adaptation/training.py` | `TrainingConfig`, PEFT target-module setup, `Trainer`, checkpoint discovery, adapter save | Split experiment contract from backend execution; add explicit modes, response-only labels, callbacks, metrics, strict resume validation, and a non-publishing probe path. Existing adapter targets are exactly `"q_proj"`, `"k_proj"`, `"v_proj"`, `"o_proj"`, `"gate_proj"`, `"up_proj"`, `"down_proj"`. [VERIFIED: src/model_adaptation/training.py:22-30,332-477] |
| `src/model_adaptation/cli.py` | Existing parser/handler and candidate alias resolution | Replace ambiguous negative `--full-precision` control with a required positive mode and run kind. Current code maps `use_4bit=not args.full_precision`; it cannot prove operator intent. [VERIFIED: src/model_adaptation/cli.py:134-246,424-452] |
| `src/model_adaptation/doctor.py` | Environment-check reporting pattern | Make readiness mode-specific and side-effect-free. Current missing-CUDA and missing-bitsandbytes checks are both marked passed; the exact fallback text is `"bitsandbytes is not installed; the trainer will use full-precision LoRA instead of 4-bit QLoRA."` [VERIFIED: src/model_adaptation/doctor.py:241-269] |
| `src/model_adaptation/data.py` and `prompts.py` | Pydantic row loading and deterministic Qwen formatter | Put an allowlisted Phase 40 boundary in front of them; version/hash the formatter and create response-only masks. The locked prompt label string is `"bank_impersonation | zalo_social_engineering | task_scam | benign"`. [VERIFIED: src/model_adaptation/prompts.py:11-29] |
| `src/model_adaptation/registry.py` | Stable file/directory SHA-256 helper | Reuse hashing but not direct mutable registry publication; Phase 40 needs an immutable per-run evidence directory and atomic finalization. [VERIFIED: src/model_adaptation/registry.py:20-50] |
| `src/model_adaptation/release_evaluation.py` | Per-label metric naming and scikit-learn dependency | Do not reuse its multi-label semantics or production normalization. It uses `MultiLabelBinarizer`, and it converts an otherwise empty prediction to `"benign"` whenever `risk_tier == "benign"`; Phase 40 invalid output must remain invalid. [VERIFIED: src/model_adaptation/release_evaluation.py:90-96,147-186] |
| `src/model_adaptation/schemas.py` | The four class values and Pydantic style | Add Phase 40-specific schemas rather than forcing PhoBERT into the current Qwen-only artifact union. The existing candidate values are exactly `"qwen3.5-4b"`, `"qwen3-4b-instruct-2507"`, and `"qwen2.5-7b-instruct"`; artifact types are only `"adapter"` and `"gguf"`. [VERIFIED: src/model_adaptation/schemas.py:13-29,136-170] |

### Bugs that plans must name explicitly

1. **Silent mode substitution:** `_resolve_quantization_config()` returns `(None, "full-precision-lora")` if 4-bit is requested but the device is not CUDA, bitsandbytes is absent, or `BitsAndBytesConfig` is unavailable. This directly violates TRAIN-02. [VERIFIED: src/model_adaptation/training.py:278-291]
2. **Proof occurs too late and is incomplete:** output directories are created before quantization resolution; the code never verifies `is_loaded_in_4bit`, a positive `Linear4bit` module count, frozen base parameters, LoRA-only trainables, or an actual adapter gradient. [VERIFIED: src/model_adaptation/training.py:384-444] [VERIFIED: 40-AI-SPEC.md:360-364]
3. **Prompt-token loss contamination:** `_build_supervised_text()` concatenates prompt and response, `_TokenizedTextDataset` tokenizes the whole text, and `DataCollatorForLanguageModeling(mlm=False)` labels all non-padding tokens. The matched Qwen experiment requires response-only loss. [VERIFIED: src/model_adaptation/training.py:233-241,448-477] [VERIFIED: 40-AI-SPEC.md:321-325]
4. **No common validation evaluator:** `Trainer` receives only the loss dataset and no `compute_metrics`; release evaluation is multi-label and production-normalized, not the strict Phase 40 single-label task. [VERIFIED: src/model_adaptation/training.py:468-477] [VERIFIED: src/model_adaptation/release_evaluation.py:147-186]
5. **Resume is existence-only:** `latest` chooses the numerically latest directory, and an explicit path is accepted if it exists. No data hash, model revision, mode proof, formatter, labels, seed, optimizer, or schedule compatibility is checked. [VERIFIED: src/model_adaptation/training.py:294-319]
6. **Evidence is underspecified:** current `training-summary.json` stores candidate, base path, device, quantization string, resume/checkpoint, smoke flag, counts, and aggregate trainer metrics, but not the TRAIN-06 provenance bundle. [VERIFIED: src/model_adaptation/training.py:491-520]
7. **Probe leakage into product registry:** dry run calls `save_adapter_artifacts()`, and every non-dry run is registered immediately. A bounded probe needs a separate non-retained, non-publishing lifecycle. [VERIFIED: src/model_adaptation/training.py:580-617]
8. **Stale defaults:** the CLI prefers `data/splits/recovered-balanced-claude-v2` if that directory exists. Phase 40 must not depend on path discovery or historical split names. [VERIFIED: src/model_adaptation/cli.py:26-35]

## Standard Stack

### Core

| Library / facility | Pinned basis | Purpose | Prescription |
|---|---|---|---|
| Python | Project declares `">=3.13"`; inspected host is 3.13.13 | CLI, schemas, training, evidence | Keep repository compatibility; notebook bootstrap must print and retain the actual interpreter version. [VERIFIED: pyproject.toml:5-9] [VERIFIED: environment probe 2026-08-24] |
| PyTorch | Project declares `"torch>=2.4"`; host is `2.12.0+cu132` | CUDA training, memory/timing, gradients | Record `torch.__version__`, CUDA runtime, GPU, driver, BF16 support, peak allocated, and peak reserved per run. [VERIFIED: pyproject.toml:33-38] [VERIFIED: environment probe 2026-08-24] |
| Transformers `Trainer` | Project declares `"transformers>=4.45"`; host is 5.9.0 | Training loop, checkpoints, trainer state | Retain the current compatibility wrapper for `eval_strategy`/`evaluation_strategy`; add callbacks and strict metrics instead of a second training abstraction. [VERIFIED: pyproject.toml:33-38] [CITED: https://huggingface.co/docs/transformers/main_classes/trainer] |
| PEFT | Project declares `"peft>=0.12"`; host is 0.19.1 | LoRA adapters and k-bit preparation | Use the same LoRA config for matched Qwen runs; QLoRA must call `prepare_model_for_kbit_training()` before adapter construction. [VERIFIED: pyproject.toml:33-38] [CITED: https://huggingface.co/docs/peft/developer_guides/quantization] |
| bitsandbytes | Exact pin chosen only after operator compatibility gate | Genuine NF4 4-bit QLoRA | Use `load_in_4bit=True`, NF4, double quantization, and a proved working `Linear4bit` path; never interpret mere import success as a completed proof. [CITED: https://huggingface.co/docs/transformers/quantization/bitsandbytes] [WARNING: flagged as suspicious by package-legitimacy seam; verify before installing.] |
| Pydantic | Project declares `"pydantic>=2.12"`; host is 2.13.4 | Fail-closed run/evidence/config schemas | Reject extra fields, impossible mode proofs, incomplete bundles, and wrong split order before publication. [VERIFIED: pyproject.toml:10-27] [VERIFIED: environment probe 2026-08-24] |
| scikit-learn | Project declares `"scikit-learn>=1.8"`; host is 1.8.0 | Accuracy, precision/recall/F1, confusion matrix | One shared single-label implementation for Qwen and PhoBERT; preserve invalid predictions in the denominator. [VERIFIED: pyproject.toml:24-27] [VERIFIED: 40-AI-SPEC.md:624-626] |

### Supporting

| Library / facility | Purpose | When to use |
|---|---|---|
| `underthesea` | Deterministic Vietnamese word segmentation | The project already declares `"underthesea>=9.2"`; use one versioned segmentation adapter for PhoBERT and retain raw plus segmented text. Exact tokenization behavior still needs a fixture gate. [VERIFIED: pyproject.toml:21-26] [ASSUMED] |
| `hashlib.sha256` plus existing registry hash helpers | Input, checkpoint, adapter, raw-log, graph, and manifest identity | Hash raw bytes after allowlist acceptance; build a hash-linked final manifest. [VERIFIED: src/model_adaptation/registry.py:20-36] |
| Matplotlib | Deterministic PNG/SVG rendering from raw JSONL | Put graph code in a normal module invoked by CLI; notebooks may display the generated files but must not be the sole renderer. [ASSUMED] [WARNING: flagged as suspicious by package-legitimacy seam; verify before adding/installing.] |

### Alternatives explicitly rejected for this phase

| Instead of | Rejected approach | Reason |
|---|---|---|
| Existing `Trainer` + callbacks | A hand-written PyTorch loop | Adds restart, distributed, checkpoint, accumulation, and logging risk without a phase requirement. [VERIFIED: 40-AI-SPEC.md:111-118] |
| Shared deterministic evaluator | An LLM judge or external API | Labels and metrics are fixed and deterministic; raw messages must not be sent to external inference services. [VERIFIED: 40-AI-SPEC.md:576-590,650-653] |
| Dedicated PhoBERT head | Prompt-classifying PhoBERT or adding QLoRA | TRAIN-04 requires a normal fully fine-tuned classification head and explicitly rejects novelty QLoRA. [VERIFIED: .planning/REQUIREMENTS.md:658-658] |
| Fresh canonical notebooks | Editing historical T4/H100 notebooks in place | Historical notebooks encode old recovered-balanced paths and inferred modes; preserving them prevents provenance ambiguity. [VERIFIED: notebooks/T4_qlora_retrain_gguf.ipynb cells 0,7] [VERIFIED: notebooks/H100_baseline_eval.ipynb cells 0-2] |

## Package Legitimacy Audit

No package was installed or downloaded during research. The seam returned `SUS` for both packages below, so execution plans must stop for operator verification before adding or installing them; an official documentation link does not erase that tool verdict.

| Package | Registry | Version evidence | Official provenance | Seam verdict | Disposition |
|---|---|---|---|---|---|
| `bitsandbytes` | PyPI | Registry candidate observed: 0.50.1 [ASSUMED pending legitimacy approval] | Hugging Face maintains the integration/install documentation. [CITED: https://huggingface.co/docs/bitsandbytes/installation] | SUS | Keep only behind a human compatibility/legitimacy checkpoint; pin after import, kernel, `Linear4bit`, forward, backward, and proof tests pass. |
| `matplotlib` | PyPI | Host has 3.11.0; registry candidate observed: 3.11.1 [ASSUMED pending legitimacy approval] | Not independently established by the package-legitimacy seam in this run. [ASSUMED] | SUS | Prefer the already-installed host copy for code-only tests; require operator verification before adding/installing in Colab. |

**Packages removed due to SLOP verdict:** none.
**Packages flagged as suspicious:** `bitsandbytes`, `matplotlib`.

## Architecture Patterns

### System Architecture Diagram

```text
phase40 CLI / canonical notebook
        |
        v
lexical path allowlist  ---- reject before open ----> failed-run receipt (no data bytes)
        |
        v
train+val contract preflight
  hashes / counts / schema / label support / seed disjointness
        |
        v
explicit run_kind + requested_mode + immutable resolved config
        |
        +-------------------+-------------------+
        |                   |                   |
        v                   v                   v
 Qwen LoRA proof       Qwen QLoRA proof     PhoBERT head
 zero Linear4bit       genuine 4-bit gate    segmentation + 4 logits
        |                   |                   |
        +-------------------+-------------------+
                            |
                            v
             Trainer + evidence/timing callbacks
                            |
           +----------------+----------------+
           |                                 |
           v                                 v
 append-only events.jsonl          raw validation predictions
           |                                 |
           +----------------+----------------+
                            v
             shared strict single-label evaluator
                            |
                            v
     evidence completeness + artifact/hash verification
           |                                 |
       probe: discard                  full: publish frozen run
                                           |
                                           v
                       graphs/comparison regenerated from raw logs
```

This flow places every potentially mutating or expensive action after contract and capability gates, and it keeps the external Colab boundary operator-controlled. [VERIFIED: 40-AI-SPEC.md:341-372,424-442,670-672]

### Recommended Project Structure

The following are proposed paths, not claims that the files already exist. [ASSUMED]

```text
src/model_adaptation/
├── phase40_contract.py       # canonical paths/hashes/counts/seed isolation; reject-before-open
├── phase40_modes.py          # requested/resolved modes and 4-bit/LoRA proof
├── phase40_metrics.py        # strict parser, 4x5 confusion matrix, common metrics
├── phase40_evidence.py       # schemas, append-only events, atomic finalize, hashes
├── phase40_callbacks.py      # timing, VRAM, throughput, eval/save overhead
├── phase40_graphs.py         # raw-log -> graph/table renderer
├── phobert_training.py       # segmentation, label map, full classifier training
├── training.py               # hardened Qwen backend, response-only loss, resume gates
├── doctor.py                 # side-effect-free mode-specific capability checks
└── cli.py                    # phase40 preflight/probe/train/verify/graph/compare commands
tests/model_adaptation/
├── test_phase40_contract.py
├── test_phase40_quantization.py
├── test_phase40_metrics.py
├── test_phase40_evidence.py
├── test_phase40_training.py
├── test_phase40_phobert.py
└── test_phase40_notebooks.py
notebooks/phase40/
├── qwen_lora_colab.ipynb
├── qwen_qlora_colab.ipynb
└── phobert_colab.ipynb
```

### Pattern 1: Reject before open

Resolve the operator path without opening it, compare it to the two canonical allowed paths, and reject anything else. Only then read train and validation, compute their SHA-256 values and row counts, validate every row, and prove `seed_id(train) ∩ seed_id(val) == ∅`. Do not implement a helper that “checks all splits,” because that would make the reserved partition easy to open accidentally. The contract quotes allowed splits as `"train"`, `"val"` and forbidden split as `"test"`. [VERIFIED: 39-DOWNSTREAM-DATA-CONTRACT.json:56-63]

The preflight should compare train count/hash `1658` / `5fa46382db8fb477ef91ec4ba770bf3f8756df9f98b9950fdf5bc1f6ff402e8b` and val count/hash `219` / `746ae6edb5008a8be8e9ef9d65f89fc44e559f99f28cd8d6a77f203ea5986d3c`, plus the manifest hash. [VERIFIED: 39-DOWNSTREAM-DATA-CONTRACT.json:4-31] The test hash is copied into evidence as upstream contract metadata only, not recomputed. [VERIFIED: 39-DOWNSTREAM-DATA-CONTRACT.json:65-71]

### Pattern 2: Intent and proof are separate

Use required positive controls for `run_kind` and `requested_mode`. A recommended implementation enum is `run_kind={probe,full}` and `requested_mode={lora,qlora,phobert}`; those spellings are an implementation recommendation, not an existing repository value. [ASSUMED] Evidence then records the exact resolved values already specified by the AI contract: `"full-precision-lora"`, `"4bit-qlora"`, and `"full-phobert"`. [VERIFIED: 40-AI-SPEC.md:483-513]

For QLoRA, proof must precede training and artifact-directory publication:

1. CUDA is explicitly selected and available; bitsandbytes and `BitsAndBytesConfig` import.
2. Load with `load_in_4bit=True`, `bnb_4bit_quant_type="nf4"`, `bnb_4bit_use_double_quant=True`, and the recorded compute dtype.
3. Prove `model.is_loaded_in_4bit is True` and count at least one `bnb.nn.Linear4bit` module.
4. Call `prepare_model_for_kbit_training()`, add PEFT, prove base parameters frozen and trainable parameters are adapter-only.
5. Run one real forward/backward micro-batch and prove at least one finite non-zero LoRA gradient.
6. Only then emit resolved mode `"4bit-qlora"`; otherwise raise, retain a failure receipt, and publish no adapter.

[VERIFIED: 40-AI-SPEC.md:187-217,360-364,483-504] [CITED: https://huggingface.co/docs/peft/developer_guides/quantization]

The ordinary LoRA branch must symmetrically prove zero `Linear4bit` base modules. This prevents a mislabeled “LoRA” comparison after environment-dependent loading. [VERIFIED: 40-AI-SPEC.md:360-364]

### Pattern 3: Matched experiment contract

Serialize a `match_key` from the controlled fields and require equality before comparing full Qwen runs: train/val hashes and order, base identifier and immutable revision, prompt formatter hash, response-mask hash, label order, random seed and data seed, max sequence length, effective batch, epochs/steps, LoRA rank/alpha/dropout/targets, optimizer/scheduler, learning rate, warm-up, precision policy, and log/eval/save cadence. Quantization proof is the sole expected difference. [VERIFIED: 40-CONTEXT.md:45-55] [VERIFIED: 40-AI-SPEC.md:614-614]

Do not claim PhoBERT has a matched optimizer or token budget with Qwen. It shares the data identity, label order, validation evaluator, seed declaration, and evidence schema; model-specific tokenizer/sequence length/optimizer choices remain visible rather than falsely “matched.” [VERIFIED: 40-AI-SPEC.md:633-639]

### Pattern 4: Response-only Qwen supervision

Tokenize the prompt and answer with a boundary-preserving formatter, set prompt and padding labels to `-100`, and train only answer tokens. Retain truncation counts and fail if the answer label can be truncated away. Both Qwen modes must use the same formatter bytes and mask algorithm. This replaces the current whole-string language-model collator behavior. [VERIFIED: src/model_adaptation/training.py:448-477] [VERIFIED: 40-AI-SPEC.md:321-325,569-569]

### Pattern 5: One strict validation evaluator

The Qwen adapter stores raw generated text, accepts exactly one of the four locked labels `"bank_impersonation"`, `"zalo_social_engineering"`, `"task_scam"`, `"benign"`, and maps malformed JSON, missing labels, unknown labels, duplicates, or parser exceptions to `"invalid_output"`. It never repairs, drops, or maps invalid output to benign. [VERIFIED: src/model_adaptation/schemas.py:24-29] [VERIFIED: 40-AI-SPEC.md:609-610,624-626]

Compute accuracy, macro/weighted precision-recall-F1, per-class precision/recall/F1/support, invalid count/rate, risky-to-benign and risky-to-invalid counts, and a 4-gold-row × 5-prediction-column confusion matrix. Invalid predictions stay in the denominator. PhoBERT argmax uses the same label order and schema with a zero invalid column. [VERIFIED: 40-AI-SPEC.md:609-625,740-752]

### Pattern 6: PhoBERT is a full classification-head run

Use `vinai/phobert-base-v2` at an immutable revision with `AutoModelForSequenceClassification`, `num_labels=4`, and explicit `id2label`/`label2id`. The model card states that PhoBERT-base-v2 has 135M parameters, maximum sequence length 256, and requires already word-segmented input. [CITED: https://huggingface.co/vinai/phobert-base-v2]

Use a deterministic, version-recorded segmentation adapter; the deadline-safe recommendation is the project’s existing underthesea dependency, with golden fixtures proving stable segmented output before any run. Preserve raw text, segmented text, token count, and truncation flag per row. This library choice is an implementation assumption and must not be promoted without the fixture gate. [VERIFIED: pyproject.toml:21-26] [ASSUMED]

### Pattern 7: Evidence is append-only first, atomic last

Each attempt receives a unique run directory and starts in `INCOMPLETE` state. Append timestamped step/eval/save/memory events to `events.jsonl`; stream raw validation predictions; save trainer state/checkpoints normally. Finalization validates the whole bundle, hashes every retained artifact and graph, writes a temporary final manifest, atomically renames it, and only then publishes a full-run registry record. Probes never publish adapters. Exact state names are a recommended implementation detail. [ASSUMED] The underlying immutable-run and append-only contract is fixed. [VERIFIED: 40-AI-SPEC.md:437-442,616-617,730-730]

Required evidence fields are the locked TRAIN-06 list plus run ID/kind/status, input contract version, model revision-resolution method, requested/resolved mode and proof, seeds, label order, formatter/preprocessor hash, exact sanitized argv, environment snapshot, hardware identity, raw-log hashes, checkpoint lineage, restart count, raw prediction hash, metric bundle hash, graph provenance, and comparison eligibility. [VERIFIED: .planning/REQUIREMENTS.md:660-660] [VERIFIED: 40-AI-SPEC.md:740-755]

### Pattern 8: Restart compatibility, not checkpoint existence

Probes are non-resumable. A full run resumes only if a stored compatibility digest exactly matches current data hashes, model revision, requested/resolved mode proof, formatter/preprocessor, labels, seeds, batching, optimizer/scheduler, precision, and cadence. On mismatch, refuse resume and require a new run ID; preserve the failed receipt. [VERIFIED: 40-AI-SPEC.md:616-618,716-718]

### Pattern 9: Fresh, canonical, restartable Colab notebooks

Create three new notebooks that call repository CLI/module APIs; do not duplicate training logic in cells. Every notebook must have explicit cells for repository revision retrieval, exact dependency pins, data-contract preflight, model-revision resolution, mode proof, resumable Drive output mounting for full runs, execution, evidence verification, deterministic graph generation, and artifact export. No notebook cell may consult the reserved split or infer mode from an omitted negative flag. [VERIFIED: 40-CONTEXT.md:45-76] [VERIFIED: notebooks/T4_qlora_retrain_gguf.ipynb cells 0,7]

The notebook validator should parse notebook JSON statically and reject stale recovered-balanced paths, unpinned training packages, secret values, test-data readers, inline alternative training loops, a QLoRA notebook without explicit QLoRA mode, or a LoRA notebook requesting 4-bit. [ASSUMED]

## Implementation Plan Map

The planner should split Phase 40 into the following dependency-ordered plans. File names are proposed and may be adjusted, but boundaries should remain. [ASSUMED]

| Plan | Scope | Main files | Exit gate |
|---|---|---|---|
| **40-01: Contract, modes, strict metrics** | Implement reject-before-open train/val contract, schemas, explicit mode/run-kind CLI, QLoRA proof API, response-only data contract, and strict common evaluator. | `phase40_contract.py`, `phase40_modes.py`, `phase40_metrics.py`, `training.py`, `cli.py`, contract/quantization/metrics tests | Fixture-only tests prove no unapproved path is opened; requested QLoRA cannot resolve to LoRA; invalid output is never benign. |
| **40-02: Evidence, timing, graphs, restart** | Add append-only events, CUDA timing/VRAM/throughput callbacks, evidence finalization, artifact hashes, deterministic graphs, config diff, probe non-publication, and full-run resume digest. | `phase40_evidence.py`, `phase40_callbacks.py`, `phase40_graphs.py`, `registry.py`, evidence/training tests | Synthetic logs reproduce graphs/metrics; probes cannot resume/publish; incompatible checkpoint resume fails closed. |
| **40-03: PhoBERT and canonical notebooks** | Add segmentation fixtures, four-class PhoBERT training/evaluation, three fresh canonical Colab notebooks, and static notebook validation. | `phobert_training.py`, `notebooks/phase40/*.ipynb`, PhoBERT/notebook tests | Fake tiny model/tokenizer tests and notebook lint pass without downloads or training. |
| **40-04: Local capability gates and bounded probes** | Run side-effect-free doctor; operator approves missing packages/downloads; execute genuine LoRA and, only if proof passes, QLoRA 30–50-step probes; retain evidence, discard adapters; compute ETA. | External run artifacts under Phase 40 evidence root; no source changes required after validated code | Each runnable probe has genuine raw timings/VRAM/throughput and non-publication proof; genuine failure remains recorded rather than “fixed” into another mode. |
| **40-05: Fresh full Colab runs and comparison** | Operator executes fresh LoRA, QLoRA, and PhoBERT notebooks; return bundles; verify hashes/completeness; regenerate graphs; freeze three validation bundles; issue honest comparison. | External run bundles plus comparison manifest/report artifact | All three evidence bundles validate; Qwen config diff has only allowed quantization differences; hardware confounding is annotated; no test-data access occurred. |

Plans 40-04 and 40-05 are deliberate safe-stop/operator plans because they need packages, model checkpoint availability, GPU/Colab allocation, and hours of external compute. Unattended code execution should finish 40-01 through 40-03 and stop before those authorities. [VERIFIED: 40-CONTEXT.md:33-61]

## Don't Hand-Roll

| Problem | Don't build | Use instead | Why |
|---|---|---|---|
| Adapter injection | Manual low-rank parameter surgery | PEFT `LoraConfig` / `get_peft_model` | Current code already uses it and it exposes trainable parameters for proof. [VERIFIED: src/model_adaptation/training.py:436-444] |
| 4-bit layers | Custom quantized linear kernels | BitsAndBytes through `BitsAndBytesConfig` | Official integration supplies NF4/double-quant loading; Phase 40 adds proof, not kernels. [CITED: https://huggingface.co/docs/transformers/quantization/bitsandbytes] |
| Training/checkpoint loop | New raw PyTorch loop | Transformers `Trainer` plus callbacks | Existing stack already handles accumulation/checkpoint state; callbacks can emit the required evidence. [VERIFIED: src/model_adaptation/training.py:332-493] |
| Metric formulas | Custom F1/confusion arithmetic | scikit-learn with fixed labels and explicit invalid-column transformation | Avoids denominator and zero-support errors while preserving an auditable prediction table. [VERIFIED: pyproject.toml:24-27] |
| Evidence validation | Loose dictionaries and hand-edited JSON | Pydantic models with `extra="forbid"` plus atomic writer | Existing schema conventions already reject unknown fields. [VERIFIED: src/model_adaptation/schemas.py:136-170] |
| Artifact identity | Ad hoc timestamps/file sizes | SHA-256 helper plus a hash-linked manifest | Existing helper already supports files and directories. [VERIFIED: src/model_adaptation/registry.py:20-36] |
| Graph data entry | Copying notebook cell values into chart arrays | Parse retained raw JSONL and write provenance beside each graph | TRAIN-06 requires mechanical regeneration. [VERIFIED: .planning/REQUIREMENTS.md:660-660] |

## Common Pitfalls

### 1. “QLoRA requested” mistaken for “QLoRA executed”

**Failure:** a missing dependency/CUDA capability silently falls back, or a notebook asserts the summary string without proving the loaded module types and gradients.
**Prevention:** require runtime proof before step zero and again in final evidence; no adapter on failure.
**Warning signs:** resolved mode differs from request, `Linear4bit` count is zero, base weights are trainable, or adapter gradients are absent. [VERIFIED: src/model_adaptation/training.py:278-291] [VERIFIED: 40-AI-SPEC.md:716-716]

### 2. Accidental test access through generic helpers

**Failure:** a convenience loader, manifest verifier, glob, notebook upload cell, or “all splits” test opens the held-out file.
**Prevention:** a Phase 40-specific two-input API and fake-path unit tests that spy on `open`; never enumerate or hash the split directory.
**Warning signs:** `test` appears in runtime input lists, metrics, prediction files, or filesystem-read traces. [VERIFIED: 39-DOWNSTREAM-DATA-CONTRACT.json:56-71]

### 3. Comparison drift hidden by one command

**Failure:** LoRA and QLoRA use different seeds, data order, prompt masks, accumulation, scheduler, evaluation cadence, or base revision.
**Prevention:** freeze a shared config, compute a match digest, and fail comparison on any unapproved diff.
**Warning signs:** separate manually edited notebook hyperparameter cells or unpinned model names. [VERIFIED: 40-CONTEXT.md:45-52]

### 4. Invalid generative output counted as safe

**Failure:** production normalization or fallback logic turns malformed/empty output into benign, inflating safety results.
**Prevention:** strict Phase 40 parser and fifth confusion-matrix column.
**Warning signs:** prediction row missing raw output, denominator smaller than validation count, or any repair field in evaluation evidence. [VERIFIED: src/model_adaptation/release_evaluation.py:90-96] [VERIFIED: 40-AI-SPEC.md:609-610]

### 5. Probe evidence mixed into full training

**Failure:** probe checkpoint is resumed in Colab, probe points appear on the full curve, or probe adapter enters the registry.
**Prevention:** separate run kind, separate run ID, non-resumable probe, explicit adapter destruction receipt, and full-run origin step zero.
**Warning signs:** a full run has a parent probe checkpoint or a curve begins above step zero. [VERIFIED: 40-CONTEXT.md:33-43]

### 6. ETA described as completed local training

**Failure:** multiplying observed steps becomes a claimed nine-hour local run.
**Prevention:** formula and fields distinguish measured probe duration, measured overhead, projected steps, and estimated total.
**Warning signs:** “local training time” without `estimate=true` or raw timing events. [VERIFIED: 40-CONTEXT.md:37-41]

### 7. PhoBERT preprocessing or label drift

**Failure:** raw unsegmented Vietnamese is fed to PhoBERT; label indices differ between train and metrics; truncation silently removes cues.
**Prevention:** golden segmentation fixtures, exact four-value mapping, max-length policy, raw/segmented text retention, truncation counts.
**Warning signs:** missing segmentation version/hash, a classifier head not equal to four outputs, or label IDs reconstructed ad hoc. [CITED: https://huggingface.co/vinai/phobert-base-v2] [VERIFIED: src/model_adaptation/schemas.py:24-29]

### 8. Pretty graphs without provenance

**Failure:** chart arrays are pasted or smoothed independently of raw logs.
**Prevention:** graph CLI reads only hashed raw event/metric files and writes a graph manifest with source hashes, renderer version, options, and output hash.
**Warning signs:** no source-log hash, manual spreadsheet intermediate, or graph points absent from events. [VERIFIED: 40-CONTEXT.md:63-72]

### 9. Resume into a changed experiment

**Failure:** `latest` checkpoint exists but belongs to different data, mode, revision, or hyperparameters.
**Prevention:** exact compatibility digest; no `latest` without manifest validation.
**Warning signs:** current implementation’s only checks are existence and directory ordering. [VERIFIED: src/model_adaptation/training.py:294-319]

## Environment Availability

The following is a non-mutating snapshot of the laptop on 2026-08-24. Availability may differ in Colab and must be captured independently for every run.

| Dependency | Required by | Available | Observed version / capability | Safe fallback |
|---|---|---:|---|---|
| Python | All code/tests | Yes | 3.13.13 [VERIFIED: environment probe 2026-08-24] | None required |
| PyTorch + CUDA | Local probes | Yes | torch `2.12.0+cu132`; CUDA available; BF16 reported supported [VERIFIED: environment probe 2026-08-24] | LoRA may record a genuine CPU-only failure only if the requested GPU probe cannot start; do not reinterpret it as completion. |
| Laptop GPU | RTX probes | Yes | NVIDIA GeForce RTX 5050 Laptop GPU, 8,151 MiB, driver 610.88 [VERIFIED: environment probe 2026-08-24] | Record genuine OOM/start failure; never engineer one. |
| Transformers | All models | Yes | 5.9.0 [VERIFIED: environment probe 2026-08-24] | None |
| PEFT | Qwen adapters | Yes | 0.19.1 [VERIFIED: environment probe 2026-08-24] | None |
| Accelerate | Trainer runtime | Yes | 1.13.0 [VERIFIED: environment probe 2026-08-24] | None |
| bitsandbytes | Genuine QLoRA | **No** | Not importable [VERIFIED: environment probe 2026-08-24] | No semantic fallback. Stop at operator install/compatibility checkpoint; LoRA remains a separate mode. |
| scikit-learn | Shared metrics | Yes | 1.8.0 [VERIFIED: environment probe 2026-08-24] | None |
| Matplotlib | Graph rendering | Yes locally | 3.11.0 [VERIFIED: environment probe 2026-08-24] | If absent in Colab, operator verifies and installs a pin; raw logs remain sufficient to render later. |
| PhoBERT checkpoint | PhoBERT full run | Not proven during research | No download or local checkpoint inspection performed [VERIFIED: research safety boundary] | Stop for operator-approved model acquisition; do not substitute another model. |
| Colab accelerator | Full runs | External / unknown | Allocation is not knowable from the repository [ASSUMED] | Capture assigned GPU; if types differ, quality remains comparable but speed is hardware-confounded. |

**Missing dependency with no semantic fallback:** bitsandbytes for requested QLoRA.
**External safe stop:** model/package acquisition and Colab execution require operator action; no installation, download, or training occurred during this research.

## Validation Architecture

`.planning/config.json` sets `workflow.nyquist_validation` to the literal value `false`; this section is nevertheless included because the parent task explicitly required a Phase 40 Validation Architecture. [VERIFIED: .planning/config.json:7-12]

### Test Framework

| Property | Value |
|---|---|
| Framework | pytest; project minimum `"pytest>=9.0"` [VERIFIED: pyproject.toml:29-32] |
| Config | `[tool.pytest.ini_options]`, `testpaths=["tests"]`, `pythonpath=[".", "src"]` [VERIFIED: pyproject.toml:50-52] |
| Existing quick suite | `python -m pytest tests/model_adaptation -q --basetemp .tmp/pytest-phase40-research-20260824` |
| Observed result | `68 passed in 4.47s` [VERIFIED: local pytest run 2026-08-24] |
| Full project suite | `python -m pytest -q --basetemp .tmp/pytest-phase40-full` [ASSUMED: command path; execute during implementation] |

The ordinary pytest temporary directory was denied by the sandbox during research; using a workspace-local `--basetemp` produced the clean 68-test result. This is an environment note, not a source defect. [VERIFIED: local pytest runs 2026-08-24]

### Phase Requirements -> Test Map

All automated tests must use generated fixtures, fake models/tokenizers, monkeypatched imports, and synthetic event logs. CI must never download a model, launch training, require a GPU, or open the reserved split. [VERIFIED: 40-AI-SPEC.md:670-672]

| Req | Behavior | Test type | Fast command | Gap |
|---|---|---|---|---|
| TRAIN-01 | LoRA probe is capped, captures post-warm-up timing/VRAM/throughput/overhead, cannot resume/publish, and full run starts fresh | Unit/integration with fake Trainer/CUDA | `python -m pytest tests/model_adaptation/test_phase40_training.py -q --basetemp .tmp/pytest-p40-train` | Wave 0 file missing |
| TRAIN-02 | Requested QLoRA fails for absent CUDA/bnb/config, false 4-bit flag, zero `Linear4bit`, trainable base, or absent gradient; no adapter is published | Unit with fake modules/model | `python -m pytest tests/model_adaptation/test_phase40_quantization.py -q --basetemp .tmp/pytest-p40-quant` | Wave 0 file missing |
| TRAIN-03 | Match diff accepts only quantization fields; common evaluator and performance evidence are complete; hardware mismatch labels speed confounded | Unit/schema | `python -m pytest tests/model_adaptation/test_phase40_metrics.py tests/model_adaptation/test_phase40_evidence.py -q --basetemp .tmp/pytest-p40-match` | Wave 0 files missing |
| TRAIN-04 | PhoBERT uses deterministic segmentation, four logits/locked label map, full trainables, max-length/truncation evidence, and shared evaluator | Unit with fake tokenizer/classifier | `python -m pytest tests/model_adaptation/test_phase40_phobert.py -q --basetemp .tmp/pytest-p40-phobert` | Wave 0 file missing |
| TRAIN-05 | Comparison requires exactly three complete validation bundles and reports every measured result regardless of winner | Unit/snapshot | `python -m pytest tests/model_adaptation/test_phase40_evidence.py -q --basetemp .tmp/pytest-p40-compare` | Wave 0 file missing |
| TRAIN-06 | Raw log -> metrics/graphs is deterministic; required fields/hashes enforced; sanitized command rejects secrets/personal paths; Git commit absent is valid | Unit/golden-file | `python -m pytest tests/model_adaptation/test_phase40_evidence.py tests/model_adaptation/test_phase40_notebooks.py -q --basetemp .tmp/pytest-p40-evidence` | Wave 0 files missing |

### Required negative and metamorphic tests

- Patch the file opener and prove an unapproved split path is rejected with zero open calls; prove only canonical train then val are opened. Do not point any test at the real reserved file. [VERIFIED: 40-AI-SPEC.md:609-610]
- Flip one byte/count/hash, duplicate a seed across train/val, reorder labels, or swap manifest version; every case must fail before model imports. [VERIFIED: 39-DOWNSTREAM-DATA-CONTRACT.json:2-31,51-63]
- Parameterize every QLoRA proof failure and assert the resolved mode never becomes `"full-precision-lora"` and adapter/registry writers are not called. [VERIFIED: src/model_adaptation/training.py:278-291]
- Feed valid labels, malformed JSON, empty output, duplicate labels, unknown labels, parser exceptions, and benign-looking invalid text; only the four valid values may populate class columns, and all invalid cases populate `"invalid_output"`. [VERIFIED: 40-AI-SPEC.md:609-610,624-626]
- Re-render the same synthetic raw log twice and byte-compare normalized metric JSON plus graph provenance; mutate a source hash and prove finalization fails. [VERIFIED: .planning/REQUIREMENTS.md:660-660]
- Generate a compatible checkpoint manifest and mutate each resume-controlled field one at a time; every mutation must refuse resume. [VERIFIED: 40-AI-SPEC.md:716-718]
- Parse all three notebook JSON files and assert explicit modes, fresh full-run IDs, pins, canonical contract use, evidence verification, no stale recovered-balanced path, no embedded credential, and no direct reserved-split access. [ASSUMED]

### Manual/external validation gates

| Gate | Why not CI | Required evidence |
|---|---|---|
| Laptop LoRA probe | Needs real RTX 5050 behavior | Raw post-warm-up events, CUDA memory summary, ETA derivation, discarded-adapter receipt |
| Laptop QLoRA probe | Requires operator-approved bitsandbytes and genuine kernel/model proof | Package/environment capture, 4-bit proof, raw timings or genuine failure receipt, discarded-adapter receipt |
| Colab full runs | External accelerator and hours of compute | Fresh run IDs, exact notebook/command/config, raw logs, trainer state, checkpoint hashes, returned evidence bundles |
| Final evidence review | Scientific claims require interpretation | Automated completeness PASS plus human confirmation of hardware-confounded speed and all three result rows |

### Sampling Rate

- **Per implementation task:** run the new focused file(s) with a workspace-local `--basetemp`.
- **Per plan merge:** run `python -m pytest tests/model_adaptation -q --basetemp .tmp/pytest-phase40-wave`.
- **Before any real probe:** run all Phase 40 contract, quantization, metrics, evidence, PhoBERT, and notebook tests; then a side-effect-free mode-specific doctor.
- **Before full-run publication:** run an offline evidence verifier against the returned bundle; graph regeneration must be part of that verifier.
- **Phase gate:** full project suite green, three complete validation bundles, comparison manifest valid, and a recorded proof that Phase 40 opened no held-out rows.

### Wave 0 Gaps

- [ ] `tests/model_adaptation/test_phase40_contract.py`
- [ ] `tests/model_adaptation/test_phase40_quantization.py`
- [ ] `tests/model_adaptation/test_phase40_metrics.py`
- [ ] `tests/model_adaptation/test_phase40_evidence.py`
- [ ] `tests/model_adaptation/test_phase40_training.py`
- [ ] `tests/model_adaptation/test_phase40_phobert.py`
- [ ] `tests/model_adaptation/test_phase40_notebooks.py`
- [ ] Deterministic fake tokenizer/model, fake CUDA memory/timing, synthetic train/val contract, and event-log fixtures in existing test support or `tests/model_adaptation/conftest.py`. [ASSUMED]

## Security Domain

Security enforcement is not explicitly disabled in the project configuration, so input validation and evidence-integrity controls apply even though this is an offline training phase. [VERIFIED: .planning/config.json:1-14]

### Applicable ASVS Categories

| Category | Applies | Phase control |
|---|---:|---|
| V2 Authentication | No direct application login | Colab/Drive credentials remain operator-managed and must never enter commands/evidence. [VERIFIED: 40-AI-SPEC.md:424-431] |
| V3 Session Management | No | No user session is introduced. [ASSUMED] |
| V4 Access Control | Yes at filesystem boundary | Canonical path allowlist, reject-before-open, immutable run directories, no arbitrary output overwrite. [VERIFIED: 39-DOWNSTREAM-DATA-CONTRACT.json:56-71] |
| V5 Input Validation | Yes | Pydantic row/config/evidence validation; split hash/count/seed checks; strict model-output parser. [VERIFIED: src/model_adaptation/schemas.py:136-170] |
| V6 Cryptography | Integrity only | Use standard SHA-256 helpers for identity; do not claim graphs or unkeyed hashes prove authorship. [VERIFIED: 40-CONTEXT.md:63-72] |

### Threats and mitigations

| Pattern | STRIDE | Mitigation |
|---|---|---|
| Path traversal or arbitrary split selection | Tampering / Information disclosure | Resolve and allowlist before any open; no directory globbing. |
| Prompt/message content interpreted as control | Tampering | Treat dataset text as data; formatter versioned; no external agent/judge; sanitize only commands/metadata, never silently alter rows. [VERIFIED: 40-AI-SPEC.md:81-81] |
| Secret or personal path leakage in evidence/notebooks | Information disclosure | Structured argv sanitizer and environment allowlist; reject tokens, notebook secrets, absolute personal paths. [VERIFIED: 40-AI-SPEC.md:424-431] |
| Artifact/log substitution | Tampering | Hash-linked evidence manifest, immutable finalization, reverify after Colab copy. [VERIFIED: 40-AI-SPEC.md:730-730] |
| Accidental oversized/OOM run | Denial of service | Bounded probe step caps, preflight sequence/batch config, genuine failure capture, explicit operator checkpoint. [VERIFIED: 40-CONTEXT.md:33-43] |
| Invalid output hidden as benign | Spoofing / integrity failure | Explicit invalid column, raw output retention, denominator preservation. [VERIFIED: 40-AI-SPEC.md:609-610,624-626] |

## Assumptions Log

| # | Claim | Section | Risk if wrong / gate |
|---|---|---|---|
| A1 | underthesea is the deadline-safe PhoBERT word segmenter. | Standard Stack / PhoBERT | Golden fixtures and a recorded version/hash must pass before use; otherwise stop and make a new preprocessing decision. |
| A2 | Matplotlib is the graph renderer. | Standard Stack | Renderer can be replaced without changing raw evidence; operator must approve package addition/install. |
| A3 | Proposed module, CLI, state, and plan names are suitable. | Architecture / Plan Map | Planner may rename while preserving boundaries and tests. |
| A4 | Static notebook JSON lint rules are sufficient before external execution. | Validation | A real Colab operator smoke check is still required after code-only validation. |
| A5 | Colab accelerator availability and package compatibility will be adequate. | Environment | Never presume; capture the assigned hardware and fail/stop honestly. |
| A6 | This phase introduces no application-session management surface. | Security | Reassess if Colab/Drive authentication is automated in repository code. |
| A7 | The proposed full-suite pytest command runs within the available environment. | Validation | Use the focused suite first and preserve any environment-only failure separately from code failures. |
| A8 | The observed PyPI candidates are legitimate versions suitable for consideration. | Package Legitimacy | Both remain blocked by the seam's SUS verdict until operator verification. |

## Open Questions and Safe Resolutions

1. **Which exact bitsandbytes pin works on the laptop and Colab?**
   - Known: the laptop has CUDA 13.2 through PyTorch, but bitsandbytes is absent; official docs describe Windows CUDA 13.x support as a compatibility condition, not proof. [CITED: https://huggingface.co/docs/bitsandbytes/installation]
   - Resolution: operator approves a pin, then the full import/kernel/Linear4bit/forward/backward gate decides. No fallback and no unattended installation.
2. **Which immutable model revisions are locally/externally available?**
   - Known: Phase 40 locks matched Qwen to one pinned revision and PhoBERT to a pinned checkpoint; repository strings alone do not prove checkpoint bytes. [VERIFIED: 40-CONTEXT.md:45-59]
   - Resolution: resolve revision to immutable identity before training, record it, and stop for operator-approved download if missing.
3. **Will the RTX 5050 LoRA or QLoRA probe fit?**
   - Known: hardware is present; fit and speed are empirical.
   - Resolution: bounded probe records success, OOM, or compatibility failure. Never predeclare OOM. [VERIFIED: 40-CONTEXT.md:33-43]
4. **Will Colab allocate matched GPUs?**
   - Known: allocation is external.
   - Resolution: prefer the same type; otherwise preserve quality comparison and label wall time/throughput hardware-confounded. [VERIFIED: 40-CONTEXT.md:45-52]

## Sources

### Primary: repository authorities (HIGH confidence)

- `.planning/phases/40-multi-model-training-evidence/40-CONTEXT.md` — locked phase boundary, probe/full-run design, evidence, evaluation boundary.
- `.planning/phases/40-multi-model-training-evidence/40-AI-SPEC.md` — mode proof, strict evaluator, evidence schema, validation architecture, safety gates.
- `.planning/REQUIREMENTS.md` — TRAIN-01 through TRAIN-06.
- `.planning/phases/39-independent-quality-re-judge/39-DOWNSTREAM-DATA-CONTRACT.json` — canonical upstream identity and train/val-only boundary.
- `src/model_adaptation/training.py`, `cli.py`, `doctor.py`, `schemas.py`, `release_evaluation.py`, `registry.py` — current implementation seams and gaps.
- `pyproject.toml` — project Python/dependency/test declarations.

### Primary: official technical documentation (HIGH/MEDIUM confidence)

- https://huggingface.co/docs/transformers/quantization/bitsandbytes — QLoRA, NF4, double quantization, extra-parameter training limits.
- https://huggingface.co/docs/peft/developer_guides/quantization — k-bit preparation and PEFT sequence.
- https://huggingface.co/docs/bitsandbytes/installation — platform/CUDA prerequisites; compatibility only, not runtime proof.
- https://huggingface.co/docs/transformers/main_classes/trainer — Trainer callbacks/state/checkpoint surface.
- https://huggingface.co/vinai/phobert-base-v2 — PhoBERT architecture, maximum length, and word-segmentation requirement.
- https://docs.pytorch.org/docs/stable/generated/torch.cuda.memory.max_memory_allocated.html — CUDA peak-memory measurement semantics.

## Metadata

**Confidence breakdown:**

- **Repository findings: HIGH** — source-of-truth files were opened with exact line references; the reserved test data file was never opened, read, or hashed.
- **Data boundary: HIGH** — derived from the Phase 39 downstream contract and Phase 40 locked context.
- **Architecture and validation: HIGH** — aligns with the existing AI-SPEC and observed test/code seams.
- **GPU/package feasibility: MEDIUM** — environment was probed, but no package was installed and no model was downloaded or trained.
- **Colab availability/performance: LOW until execution** — external accelerator allocation and runtime compatibility are empirical.

**Research date:** 2026-08-24
**Valid until:** 2026-09-07 for package/GPU details; repository findings remain valid until the cited files change.
