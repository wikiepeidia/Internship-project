# Phase 40: Multi-Model Training Evidence - Pattern Map

**Mapped:** 2026-08-24
**Files classified:** 25 source, test, notebook, and runtime-artifact paths/groups
**Positive/partial analogs:** 19 / 25
**Safety boundary:** No model download, package installation, training, or reserved-split access was performed.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `src/model_adaptation/phase40_contract.py` | utility / config guard | file-I/O, validation | `src/model_adaptation/data.py` | role-match after a new reject-before-open guard |
| `src/model_adaptation/phase40_modes.py` | service / model factory | request-response, model construction | `src/model_adaptation/training.py` | partial; current quantization resolution is an anti-pattern |
| `src/model_adaptation/phase40_metrics.py` | evaluation service | batch transform | `src/model_adaptation/release_evaluation.py` | role-match; replace multi-label and benign fallback semantics |
| `src/model_adaptation/phase40_evidence.py` | service / typed model | file-I/O, batch finalization | `src/model_adaptation/registry.py` + `src/model_adaptation/schemas.py` | role-match; atomic immutable finalization is new |
| `src/model_adaptation/phase40_callbacks.py` | hook | event-driven, streaming file-I/O | none | no Trainer callback/evidence-event analog |
| `src/model_adaptation/phase40_graphs.py` | utility | file-I/O, transform | none | no raw-log-to-graph renderer exists |
| `src/model_adaptation/phobert_training.py` | model-training service | batch | `src/model_adaptation/training.py` | role-match; classifier-head and segmentation are new |
| `src/model_adaptation/training.py` | model-training service | batch | same file | exact modification seam |
| `src/model_adaptation/doctor.py` | diagnostic utility | request-response | same file | exact modification seam |
| `src/model_adaptation/cli.py` | controller / route | request-response | same file | exact modification seam |
| `src/model_adaptation/data.py` | utility | file-I/O, transform | same file | exact modification seam |
| `src/model_adaptation/prompts.py` | utility | transform | same file | exact modification seam |
| `src/model_adaptation/registry.py` | service | file-I/O | same file | exact modification seam; publication rules must change |
| `tests/model_adaptation/test_phase40_contract.py` | test | file-I/O, request-response | `tests/model_adaptation/test_training.py` | role-match with synthetic JSONL fixtures |
| `tests/model_adaptation/test_phase40_quantization.py` | test | request-response | `tests/model_adaptation/test_training.py` | role-match with fake modules/monkeypatch |
| `tests/model_adaptation/test_phase40_metrics.py` | test | batch transform | `tests/model_adaptation/test_training.py` | structural match; strict invalid-output cases are new |
| `tests/model_adaptation/test_phase40_evidence.py` | test | file-I/O, transform | `tests/model_adaptation/test_training.py` | structural match; atomic/hash-chain cases are new |
| `tests/model_adaptation/test_phase40_training.py` | test | batch | `tests/model_adaptation/test_training.py` | exact extension pattern |
| `tests/model_adaptation/test_phase40_phobert.py` | test | batch | `tests/model_adaptation/test_training.py` | role-match with fake model/tokenizer |
| `tests/model_adaptation/test_phase40_notebooks.py` | test | file-I/O, static transform | none | no notebook validator exists |
| `tests/model_adaptation/conftest.py` | test provider | file-I/O, event-driven fixtures | helpers in `tests/model_adaptation/test_training.py` | role-match; extract shared fakes here |
| `notebooks/phase40/qwen_lora_colab.ipynb` | config / external controller | batch, file-I/O | none | create fresh; historical notebooks are unsafe templates |
| `notebooks/phase40/qwen_qlora_colab.ipynb` | config / external controller | batch, file-I/O | `notebooks/T4_qlora_retrain_gguf.ipynb` | anti-pattern reference only, not a copy source |
| `notebooks/phase40/phobert_colab.ipynb` | config / external controller | batch, file-I/O | none | no PhoBERT training notebook exists |
| `data/models/phase40/<run-id>/{resolved-config.json,run-evidence.json,events.jsonl,trainer_state.json,curves/,adapter-or-model/}` | immutable run artifact | streaming and batch file-I/O | `data/manifests/final-qlora-evidence-2026-06.json` | partial schema example; historical paths/claims must not carry forward |

## Pattern Assignments

### `src/model_adaptation/phase40_contract.py` (utility/config guard, file-I/O)

**Analogs:** `src/model_adaptation/data.py`, `src/model_adaptation/schemas.py`

Use the existing absolute-import and typed-record convention, but put a new lexical allowlist in front of it. The current loader is useful only after the supplied paths have been resolved and accepted.

**Typed JSONL loading pattern** (`src/model_adaptation/data.py`, lines 5-23):

```python
import json
from pathlib import Path

from src.data_pipeline.schemas import DatasetRecord

def load_split_records(split_path: Path) -> list[DatasetRecord]:
    records: list[DatasetRecord] = []
    with split_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            records.append(DatasetRecord.model_validate(json.loads(line)))
    return records
```

**Fail-closed schema pattern** (`src/model_adaptation/schemas.py`, lines 136-170):

```python
class ModelArtifactRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    local_path: Path
    sha256: str = Field(min_length=64, max_length=64)

    @model_validator(mode="after")
    def validate_tracking_flags(self) -> "ModelArtifactRecord":
        if self.local_only and self.tracked_in_git:
            raise ValueError("local-only artifacts cannot be marked as tracked in git")
        return self
```

**Phase 40 assignment:**

- Expose a two-input API for canonical `train` then `val`; do not expose an `all splits` helper.
- Resolve and compare candidate paths before calling `open`, `read_text`, `rglob`, or a generic loader.
- After acceptance, verify the Phase 39 contract version, train/validation hashes and counts, validation supports, schema, and zero `seed_id` overlap.
- Carry the upstream held-out hash as metadata only; never recompute it in Phase 40.
- Tests must pass synthetic decoy paths and spy on the opener, proving rejection causes zero open calls.

There is no existing repository analog for reject-before-open. The planner should treat this ordering as a new security invariant, not infer it from `load_split_records()`.

---

### `src/model_adaptation/phase40_modes.py` and `src/model_adaptation/training.py` (model factory/training service)

**Analog:** `src/model_adaptation/training.py`

**Reuse the stable adapter target list** (lines 22-30):

```python
DEFAULT_TARGET_MODULES: tuple[str, ...] = (
    "q_proj", "k_proj", "v_proj", "o_proj",
    "gate_proj", "up_proj", "down_proj",
)
```

**Reuse the Transformers-version compatibility pattern** (lines 332-381):

```python
parameter_names = set(inspect.signature(transformers_module.TrainingArguments.__init__).parameters)
training_kwargs = {
    "output_dir": str(training_output_dir),
    "report_to": [],
    "save_safetensors": True,
}
if "eval_strategy" in parameter_names:
    training_kwargs["eval_strategy"] = "steps" if has_eval_data else "no"
elif "evaluation_strategy" in parameter_names:
    training_kwargs["evaluation_strategy"] = "steps" if has_eval_data else "no"
supported_kwargs = {
    key: value for key, value in training_kwargs.items()
    if key in parameter_names and value is not None
}
return transformers_module.TrainingArguments(**supported_kwargs)
```

**Reuse the narrow Trainer seam** (lines 468-493):

```python
trainer = transformers_module.Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=eval_dataset if len(eval_dataset) else None,
    data_collator=...,
)
train_result = trainer.train(resume_from_checkpoint=...)
trainer.save_state()
```

**Do not copy the current mode resolver** (lines 278-291):

```python
if not config.use_4bit or device != "cuda" or importlib.util.find_spec("bitsandbytes") is None:
    return None, "full-precision-lora"
if not hasattr(transformers_module, "BitsAndBytesConfig"):
    return None, "full-precision-lora"
```

This silently substitutes ordinary LoRA for requested QLoRA. Phase 40 needs positive `requested_mode={lora,qlora,phobert}` and a separately recorded resolved mode. QLoRA raises before run-directory/model-artifact creation unless CUDA, the approved bitsandbytes runtime, NF4/double-quant settings, `is_loaded_in_4bit`, positive `Linear4bit` count, frozen base parameters, LoRA-only trainables, and a finite adapter gradient are all proved. LoRA symmetrically proves zero 4-bit base modules.

**Other required replacements:**

- Current code creates trainer/adapter directories before mode proof (`training.py`, lines 391-397); gate first.
- Current code concatenates prompt and response and applies `DataCollatorForLanguageModeling` to the whole sequence (`training.py`, lines 233-241 and 448-477); replace with response-only labels and `-100` prompt/padding masks.
- Current resume logic accepts `latest` or any existing path (`training.py`, lines 294-319); require an exact compatibility digest over data/model/mode/preprocessor/seed/training controls.
- Current dry run and every completed run publish via the registry (`training.py`, lines 580-617); probes must never resume or publish and must emit a discard receipt.

---

### `src/model_adaptation/phobert_training.py` (model-training service, batch)

**Analog:** the orchestration boundary in `src/model_adaptation/training.py`; there is no existing PhoBERT backend.

Copy the dependency-injection shape—resolved immutable config, typed train/validation examples, narrow Trainer construction, and returned artifact metadata—but not the causal-LM formatter, PEFT, bitsandbytes, or whole-string collator.

The new backend must use `AutoModelForSequenceClassification(..., num_labels=4, id2label=..., label2id=...)`, fully train encoder plus head, use deterministic word segmentation and max length 256, and retain raw/segmented text plus truncation evidence. The locked order comes from `src/model_adaptation/schemas.py`, lines 24-29:

```python
LOCKED_RELEASE_LABELS = (
    "bank_impersonation",
    "zalo_social_engineering",
    "task_scam",
    "benign",
)
```

Do not extend the old candidate union (`schemas.py`, lines 13-20) or catalog (`catalog.py`, lines 11-35) as an implicit model-revision source. Phase 40 resolved configs must record immutable Qwen and PhoBERT revisions explicitly.

---

### `src/model_adaptation/phase40_metrics.py` (evaluation service, batch transform)

**Analog:** `src/model_adaptation/release_evaluation.py`

**Reuse sklearn and explicit fixed-order per-class output** (lines 147-186):

```python
label_order = list(LOCKED_RELEASE_LABELS)
precision, recall, f1, support = precision_recall_fscore_support(
    y_true,
    y_pred,
    average=None,
    zero_division=0,
)
per_label_metrics = [
    PerLabelMetricRow(
        label=label,
        precision=float(precision[index]),
        recall=float(recall[index]),
        f1=float(f1[index]),
        support=int(support[index]),
    )
    for index, label in enumerate(label_order)
]
```

**Do not reuse these semantics:**

- `MultiLabelBinarizer` at `release_evaluation.py`, lines 159-163: Phase 40 is one gold class and one predicted state.
- Benign fallback at lines 90-96:

```python
if result.risk_tier == "benign":
    return ["benign"]
return []
```

The Phase 40 parser accepts exactly one locked class; malformed JSON, empty/multiple/unknown labels, and parser exceptions become `invalid_output`. They remain in the denominator and occupy a fifth prediction column. Never infer a safe label from risk tier, keywords, aliases, or absent output.

The shared evaluator must produce accuracy, macro and weighted F1, per-class precision/recall/F1/support, a 4-by-5 confusion matrix, invalid count/rate, and explicit risky-to-benign/risky-to-invalid slices for both Qwen and PhoBERT.

---

### `src/model_adaptation/phase40_evidence.py`, `phase40_callbacks.py`, `phase40_graphs.py`, and `registry.py`

**Analogs:** `src/model_adaptation/registry.py`, `src/model_adaptation/schemas.py`

**Copy the stable file/directory SHA-256 pattern** (`registry.py`, lines 11-36):

```python
def _update_digest_from_file(digest, file_path: Path) -> None:
    with file_path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)

def build_model_checksum(file_path: Path) -> str:
    if not file_path.exists():
        raise FileNotFoundError(f"Missing artifact file: {file_path}")
    if file_path.is_file():
        digest = hashlib.sha256()
        _update_digest_from_file(digest, file_path)
        return digest.hexdigest()
    digest = hashlib.sha256()
    for child in sorted(path for path in file_path.rglob("*") if path.is_file()):
        digest.update(child.relative_to(file_path).as_posix().encode("utf-8"))
        digest.update(b"\0")
        _update_digest_from_file(digest, child)
        digest.update(b"\0")
    return digest.hexdigest()
```

**Copy typed JSON serialization/read-back validation** (`registry.py`, lines 39-50) but strengthen the writer:

```python
output_path.write_text(registry.model_dump_json(indent=2), encoding="utf-8")
return ModelRegistry.model_validate_json(input_path.read_text(encoding="utf-8"))
```

Phase 40 must write a temporary sibling, flush/fsync, atomically replace, and read-validate once. The current direct overwrite is not an atomic-finalization analog.

**New patterns with no current analog:**

- `phase40_callbacks.py`: append-only JSONL step/eval/save events, CUDA synchronization around timing, post-warm-up median, peak allocated/reserved VRAM, examples/s, tokens/s, and measured overhead. Callback code observes state; it does not alter loss/control flow.
- `phase40_graphs.py`: deterministic raw-events-to-graph/table rendering with source hash, renderer version/options, and output hash. No pasted arrays or notebook-only plotting.
- `phase40_evidence.py`: immutable unique run IDs, `probe|full` lifecycle, sanitized argv/environment allowlist, requested/resolved mode proof, data/model/preprocessor hashes, trainer state, prediction/metric/artifact/graph hashes, and comparison eligibility.
- `registry.py`: publish only a complete verified full run. A probe, failed proof, incomplete evidence bundle, or incompatible resumed run never enters the comparison registry.

The legacy `training-summary.json` contains only device/mode/counts and aggregate Trainer metrics; it is insufficient. The legacy `final-qlora-evidence-2026-06.json` demonstrates path/hash nesting but records recovered-balanced inputs, an absolute personal deployment path, and a summary-string QLoRA claim. Treat it as an evidence-gap/anti-pattern fixture, not a Phase 40 schema.

---

### `src/model_adaptation/cli.py` and `doctor.py` (controller and diagnostic utility)

**Analogs:** same files.

**Copy subcommand dispatch and non-traceback operator errors** (`cli.py`, lines 111-115 and 572-581):

```python
parser = argparse.ArgumentParser(
    prog="python -m src.model_adaptation.cli",
    allow_abbrev=False,
)
subparsers = parser.add_subparsers(dest="command", required=True)

args = parser.parse_args(argv)
try:
    return args.handler(args)
except (RuntimeError, ValueError, FileNotFoundError) as exc:
    print(str(exc))
    return 1
```

**Copy explicit handler-to-config wiring** (`cli.py`, lines 424-468), but require positive intent fields rather than deriving mode from absence of a flag.

**Anti-patterns to remove from Phase 40 commands:**

- `_default_split_root()` prefers `data/splits/recovered-balanced-claude-v2` (`cli.py`, lines 26-35).
- `--full-precision` is a negative flag (`cli.py`, lines 241-245), and handler wiring turns its absence into `use_4bit=True` (`cli.py`, line 451).
- Generic Phase 3/5 subcommands accept broad split paths. Phase 40 commands must call their contract preflight before imports/output creation and have no reserved-split argument.

**Doctor pattern:** keep one `DoctorCheck` per capability and compute readiness from `all(check.passed ...)` (`doctor.py`, lines 55-58 and 187-195). Replace these current false-positive checks:

- CUDA unavailable still passes (`doctor.py`, lines 252-256).
- Missing bitsandbytes still passes and advertises fallback (`doctor.py`, lines 258-268).

Readiness must be mode-specific: LoRA, QLoRA, and PhoBERT receive independent PASS/FAIL states. Doctor remains side-effect-free and must not install packages, download models, create an experiment directory, or silently substitute a mode.

---

### `src/model_adaptation/data.py` and `prompts.py` (transform utilities)

**Analogs:** same files.

Reuse Pydantic record loading only after the Phase 40 allowlist. Preserve the deterministic response-object construction in `data.py`, lines 26-50, and the locked response-label text in `prompts.py`, lines 14-20.

Do not copy the instruction concatenation in `prompts.py`, lines 21-28, unchanged. Phase 40 needs separate chat roles: stable system instruction, raw message fenced as user data, and assistant JSON response. Hash the formatter and response-mask algorithm; tokenize prompt/response separately; block answer truncation.

---

### Phase 40 tests and fixtures

**Analog:** `tests/model_adaptation/test_training.py`

**Copy synthetic JSONL fixtures** (lines 19-24):

```python
def _write_split(path: Path, records: list[DatasetRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(record.model_dump_json() + "\n")
```

**Copy fake-backend injection and monkeypatch isolation** (lines 247-295):

```python
def fake_local_backend(config, train_examples, val_examples):
    adapter_dir = tmp_path / "models" / "run" / "adapter"
    adapter_dir.mkdir(parents=True, exist_ok=True)
    return {
        "artifact_path": adapter_dir,
        "quantization_mode": "full-precision-lora",
    }

monkeypatch.setattr(training_module, "_run_local_adapter_training", fake_local_backend)
result = run_training(config, selection=_selection())
```

**Copy signature-accurate fakes** from lines 297-424: the current suite defines small fake `TrainingArguments` classes and captures kwargs instead of importing/running a real model.

Phase 40 test rules:

- Put reusable fake tokenizer/model, fake CUDA timing/memory, synthetic contract, and event-log helpers in `conftest.py`.
- Never download a checkpoint, launch Trainer, require a GPU, enumerate the real split directory, or point a test at the reserved file.
- Patch the opener before contract tests and assert unapproved paths cause zero calls.
- Parameterize every QLoRA proof failure and assert no adapter/evidence/registry writer is called.
- Cover valid labels plus malformed/empty/duplicate/unknown/parser-exception output; every invalid case must stay `invalid_output`.
- Byte-compare regenerated normalized metrics/graph provenance; mutate one source hash and require finalization failure.
- Mutate each resume-controlled field individually and require refusal.
- Parse notebook JSON statically and reject stale recovered-balanced paths, missing pins/modes/revisions, inline training loops, secrets, and any reserved-split reader.

There is no existing `test_phase40_notebooks.py` analog; build it as a static JSON contract test using the same `tmp_path`/plain-assert style.

---

### `notebooks/phase40/*.ipynb` (external controllers)

Create all three notebooks fresh. Historical notebooks are evidence of what must be rejected, not implementation templates.

**Unsafe historical patterns:**

- `notebooks/T4_qlora_retrain_gguf.ipynb`, line 6, tells the operator to upload recovered-balanced train/validation inputs.
- The same notebook uses unbounded dependency ranges (`>=`) at line 15, duplicates model loading/evaluation/training logic in cells, infers QLoRA from the absence of `--full-precision` at lines 117-130, and treats a summary string assertion as mode proof at lines 144-148.
- `notebooks/H100_baseline_eval.ipynb`, lines 14 and 68, points to a recovered-balanced validation set; line 35 uses unpinned packages; line 121 contains fuzzy aliases/keyword fallbacks that can convert malformed output into a class.

**Canonical notebook pattern:**

1. Retrieve a pinned repository revision.
2. Display exact dependency pins and stop for operator authorization before installation/model acquisition.
3. Mount resumable external storage without embedding credentials.
4. Call repository CLI/module APIs for contract preflight, explicit mode proof, fresh full-run start/resume, evidence verification, graph generation, and artifact export.
5. Keep no independent training/evaluation/parser implementation in notebook cells.
6. Never reference or open the reserved split.

The Qwen full notebooks must start at step zero from the same pinned revision and shared config. Probe adapters are neither uploaded nor resumed. PhoBERT calls its classification-head backend, not PEFT/QLoRA.

## Shared Patterns

### Imports and module boundaries

Repository modules use absolute imports such as `from src.model_adaptation.registry import ...` (`training.py`, lines 13-17; `cli.py`, lines 8-23). Keep Phase 40 code in normal modules and make notebooks thin callers.

### Validation

Use Pydantic v2 models with `ConfigDict(extra="forbid")`, `Field` constraints, and `field_validator`/`model_validator` (`schemas.py`, lines 56-73 and 136-170). Reject impossible requested/resolved mode combinations and incomplete evidence during model validation.

### Error handling

Domain helpers raise `ValueError`, `FileNotFoundError`, or `RuntimeError`; the CLI converts these to a concise message and exit code 1 (`cli.py`, lines 572-581). Preserve the original exception as `raise ... from exc` when translating a low-level failure, as the OOM path currently does (`training.py`, lines 479-489). Do not catch a QLoRA proof failure and continue as LoRA.

### Artifact identity

Use sorted relative paths and content bytes for directory hashes (`registry.py`, lines 20-36). Evidence manifests link raw inputs, raw events, predictions, metrics, graphs, and model artifacts by SHA-256. Hashes demonstrate identity/integrity, not authorship.

### Safe state order

The required order is: lexical allowlist -> train/validation identity and lineage -> explicit requested mode -> runtime mode proof -> immutable run directory -> training/events -> validation -> evidence completeness/hash verification -> probe discard or full-run publication. No expensive or mutating step moves before its gate.

### No authentication surface

Phase 40 adds no application authentication. Colab/Drive/Hugging Face credentials remain operator-managed and must never appear in argv, notebook source, logs, evidence, or environment dumps.

## Anti-Patterns to Block Explicitly

| Anti-pattern | Existing evidence | Phase 40 replacement |
|---|---|---|
| Historical recovered-balanced path discovery | `cli.py:26-35`; `T4_qlora_retrain_gguf.ipynb:6`; `H100_baseline_eval.ipynb:14,68` | Exact canonical train/val allowlist from the Phase 39 downstream contract |
| Missing/invalid output treated as safe | `release_evaluation.py:90-96` | Fifth `invalid_output` state retained in denominator |
| Fuzzy/keyword parser repairs model output | `H100_baseline_eval.ipynb:121`; `T4_qlora_retrain_gguf.ipynb:104` | One strict typed four-label parser, raw output retained |
| QLoRA silently resolves to LoRA | `training.py:278-291`; `doctor.py:258-268` | Requested/resolved separation and full runtime proof, else fail |
| Mode inferred from an omitted negative flag | `cli.py:241-245,451`; `T4_qlora_retrain_gguf.ipynb:117-130` | Required positive `--mode` and `--run-kind` |
| Output directories created before proof | `training.py:391-397` | Complete contract/mode gates first |
| Prompt tokens contribute to loss | `training.py:233-241,448-477` | Response-only labels; prompt/padding `-100` |
| Resume based on directory existence/order | `training.py:294-319` | Exact compatibility digest |
| Probe/dry-run artifact enters registry | `training.py:580-617` | Probe non-resumable, non-publishable, discard receipt |
| Hand-written notebook metrics/graphs | `T4_qlora_retrain_gguf.ipynb:104,226-283` | Shared evaluator and graph module consume retained raw evidence |
| QLoRA proof is a summary string | `T4_qlora_retrain_gguf.ipynb:144-148` | Module type/config/frozen-base/gradient proof in evidence |
| Personal absolute paths in evidence | `final-qlora-evidence-2026-06.json:31-36`; old training summary lines 3 and 7 | Sanitized repo-relative or run-relative paths |

## No Positive Analog Found

| File | Role / Flow | Why planner must use AI-SPEC/RESEARCH instead |
|---|---|---|
| `phase40_contract.py` reject-before-open portion | utility / file-I/O | Existing loaders open arbitrary supplied paths immediately |
| `phase40_callbacks.py` | hook / event-driven | No Trainer callback or append-only step evidence exists |
| `phase40_graphs.py` | utility / file-I/O transform | Existing notebooks compute/plot ad hoc; no provenance renderer exists |
| `test_phase40_notebooks.py` | test / static transform | No notebook JSON lint tests exist |
| `qwen_lora_colab.ipynb` | external controller / batch | No fresh canonical LoRA notebook exists |
| `phobert_colab.ipynb` | external controller / batch | No PhoBERT training path exists |

## Metadata

**Analog search scope:** `src/model_adaptation/`, `tests/model_adaptation/`, `notebooks/`, `data/manifests/`, current model summaries, and Phase 40 upstream contracts.
**Deeply inspected:** 9 model-adaptation modules, 1 training test module, 3 historical notebook/evidence surfaces, 3 manifest/summary artifacts, and the 3 required Phase 40 planning documents.
**Strong analog set:** `training.py`, `cli.py`/`doctor.py`, `release_evaluation.py`, `registry.py`/`schemas.py`, and `test_training.py`.
**Pattern extraction date:** 2026-08-24.
