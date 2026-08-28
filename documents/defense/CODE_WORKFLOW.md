# VNPhish: End-to-End Code Workflow

This is the current defense map for the repository. It points to maintained
source files instead of copying source into a second tutorial tree. Historical
walkthroughs and old defense scripts are archived under `historical/docs/` and
must not be used as current metric or architecture authority.

## Thirty-second description

VNPhish is a local, text-only Vietnamese phishing-analysis prototype. It accepts
one message plus an optional channel hint and returns a provisional risk tier,
threat labels, a short explanation, exact grounded cues copied from the input,
and safe recommendations. The research workflow also builds a governed
four-class dataset, trains a Qwen QLoRA model and a PhoBERT classifier, and
records one frozen shared-cohort evaluation.

The four dataset labels are:

- `bank_impersonation`
- `zalo_social_engineering`
- `task_scam`
- `benign`

## Exact task, input, and output

There are two related contracts.

### Dataset and training contract

Each governed JSONL row has exactly these fields:

```json
{
  "text": "raw Vietnamese message",
  "label": "task_scam",
  "risk_tier": "high-risk",
  "suspicious_spans": ["exact substring copied from text"],
  "xai_explanation": "short reason",
  "source": "provenance category",
  "seed_id": "stable root-scenario identifier"
}
```

The schema authority is `DatasetRecord` in
`src/data_pipeline/core/records.py`. The class target is stored in `label`.
`risk_tier` is a separate severity field; it is not the class label.

### Installed runtime contract

Input:

- one raw text message;
- optional channel: `unknown`, `sms`, `zalo`, `messenger`, `telegram`, or
  `facebook`.

Output:

- provisional `risk_tier`;
- short summary;
- up to three grounded cues;
- up to two threat labels;
- up to three safe recommendations;
- backend identity and normalized text.

The runtime is text-only. OCR, images, audio, automatic URL opening, and raw-text
persistence are outside the current contract.

## What to open first during a code review

Open these files in order. This is a reading order, not a command sequence.

| Order | File | What it proves |
| ---: | --- | --- |
| 1 | `src/data_pipeline/core/records.py` | Seed and dataset schemas; label and evidence-span validation |
| 2 | `src/data_pipeline/scraper/real_sources.py` | Audited acquisition policy, rights gate, bounded HTTP, and PII redaction |
| 3 | `src/data_pipeline/workflows.py` | Maintained data orchestration |
| 4 | `src/data_pipeline/generation/generator.py` | Synthetic batch generation, finalization, source, and `seed_id` derivation |
| 5 | `src/data_pipeline/generation/quality_judge.py` | Five-dimension semantic quality judge |
| 6 | `src/data_pipeline/publication.py` | Transactional reviewed-dataset publication |
| 7 | `src/data_pipeline/core/text.py` | Exact and lexical near-duplicate control |
| 8 | `src/data_pipeline/core/splits.py` | Complete-seed-group assignment and leakage rejection |
| 9 | `src/data_pipeline/processing/splitter.py` | Cross-split semantic collision cleanup and coverage checks |
| 10 | `src/data_pipeline/versioning/build.py` | Versioned files and SHA-256 manifest |
| 11 | `src/modeling/training.py` | Phase-neutral training service |
| 12 | `src/modeling/legacy_adapters.py` | Explicit bridge to retained experiment implementations |
| 13 | `src/model_adaptation/data.py` | Qwen assistant JSON and response-only token labels |
| 14 | `src/model_adaptation/phobert_training.py` | PhoBERT preprocessing, label IDs, and classifier training |
| 15 | `src/model_adaptation/phase40_metrics.py` | Strict prediction alignment and metric generation |
| 16 | `src/modeling/evidence.py` | Read-only reporting authority for frozen results |
| 17 | `src/runtime/cli.py` | Installed `analyze`, `doctor`, and `demo` interface |
| 18 | `src/runtime/service.py` | Input-to-result orchestration |
| 19 | `src/modeling/inference.py` | Backend-independent inference contract |
| 20 | `src/runtime/analyzers/local_model.py` | Structured parsing, exact-span grounding, and safety rules |

## End-to-end dataset workflow

```text
public advisories or retained seed JSONL
  -> SeedRecord / ProvenancedSeedRecord
  -> optional model-assisted candidate generation
  -> DatasetRecord structural validation
  -> staged write + reload equality check
  -> semantic quality judging and human review/repairs
  -> lexical deduplication
  -> group-integrity split by label and seed_id
  -> cross-split semantic collision removal
  -> label coverage and seed-concentration checks
  -> train / validation / terminal-evaluation JSONL
  -> SHA-256 manifests
```

### 1. Public-source acquisition

The stronger audited acquisition lane is
`src/data_pipeline/scraper/real_sources.py`.

- `SourcePolicy` binds a publisher, URL, allowed hosts, rights status, adapter,
  and field map.
- `BoundedHttpClient` enforces host, timeout, polite-delay, and response-size
  bounds.
- `collect_source()` refuses a source unless collection and redistribution are
  both allowed.
- The collector redacts victim PII and can enforce a pinned byte size and hash.
- `deduplicate_records()` removes URL, exact-text, and near-duplicate records.

`ProvenancedSeedRecord` deliberately contains no project label or risk tier.
Acquisition evidence therefore cannot silently become labeled training data.

The retained compatibility workflow also contains
`src/data_pipeline/scraper/ncsc_scraper.py`. It extracts and normalizes advisory
content when no seed file is supplied, but it does not replace the stronger
rights-policy evidence lane above.

### 2. Seed contract

`SeedRecord` contains:

- `text`;
- `source_url`;
- `scrape_timestamp`;
- optional historical `raw_label_hint`.

For ordinary newly acquired public records, the label hint must remain null.
The seed is a semantic root from which variants may be created.

### 3. Orchestration

The maintained domain operation is
`src/data_pipeline/workflows.py::build_training_corpus()`.

It performs the following work:

1. load strict UTF-8 seed JSONL or invoke the retained scraper;
2. create an owned resumable generation workspace;
3. call `TieredGenerator.generate_dataset()`;
4. validate, stage, reload, and compare the candidate records;
5. optionally run semantic judging;
6. publish one reviewed generation transactionally.

`src/data_pipeline/cli.py` is a thin compatibility operator interface.
`run_phase1()` forwards to `build_training_corpus()`; the CLI is not the domain
implementation itself.

### 4. Candidate generation

`TieredGenerator.generate_dataset()` targets the four classes and batches complex
and bulk requests. Provider responses must parse as JSON. `_finalize_records()`:

1. normalizes label and risk aliases;
2. adds source provenance;
3. derives `seed_id` from `source_url|text`;
4. validates the completed object with `DatasetRecord`.

Every variant finalized from one root receives the same `seed_id`. This is
essential: paraphrasing does not create an independent scenario.

`generation_runs.stage_generated_records()` then writes the candidate, reloads
it, validates it again, and checks equality with the submitted records.

#### Open generator caveat

The retained generator is not currently a guaranteed one-command corpus rebuild.
`_build_batch_specs()` can reuse one `SeedRecord` across different threat classes,
while `_derive_seed_id()` does not include the class. The maintained splitter
correctly rejects any seed that spans labels. A realistic regeneration can
therefore fail closed at publication.

That behavior protects the dataset from false seed diversity, but the assignment
logic still needs a future design fix: each active class must receive genuinely
independent roots, not label-suffixed copies of one root. Do not run or advertise
the provider workflow as a clean rebuild until this is resolved.

### 5. Structural and semantic validation

`DatasetRecord` rejects:

- unknown fields;
- unknown labels or risk tiers;
- blank text or seed IDs;
- duplicate or blank evidence spans;
- any evidence span that is not an exact substring of `text`.

Pydantic supplies structural validation. It does not judge whether a message is
natural or correctly labeled.

`QualityJudge` performs the semantic check. It scores realism, label correctness,
code-switch naturalness, risk-tier correctness, and suspicious-span accuracy.
A routine candidate passes only when every dimension is at least 3.

Phase 39's Codex instruction files, judge merge, manual-review sheets, narrator
repair, and mislabel triage are preserved audit evidence and one-off migrations.
They are not the normal forward generation path.

### 6. Why the Zalo/Codex files still exist

The following unattractive names are intentionally preserved:

- `src/data_pipeline/generation/zalo_codex_catalog.py`;
- `src/data_pipeline/generation/zalo_codex_recovery.py`;
- `src/data_pipeline/generation/zalo_direct_actions.py`;
- `src/data_pipeline/generation/zalo_direct_messages*.py`;
- `src/data_pipeline/reconstruct_zalo_direct_catalog.py`.

They record the exact one-off reconstruction that replaced narrator-style Zalo
rows with direct messages from 60 semantic roots. Their paths participate in
provenance, tests, the migration registry, and corpus-governance code. Renaming or
deleting them just to make the tree prettier would damage reproducibility.

Treat them as historical repair provenance, not active runtime modules and not a
claim that an external provider is required by the installed application.

### 7. Deduplication and leakage-safe splitting

`lexical_dedup()` retains the first member of exact or near-exact clusters at the
configured threshold, currently 0.95.

`split_dataset()` then:

1. validates every row;
2. verifies one `seed_id` maps to only one label;
3. groups rows by `label -> seed_id`;
4. fails if any label lacks enough independent roots for all active splits;
5. deterministically orders whole seed groups with salted SHA-256;
6. assigns the complete group to train, validation, or terminal evaluation.

The default target ratio is 80/10/10. Variants of one scenario cannot cross the
partition boundary.

`split_and_dedup()` adds a semantic cross-split check. Validation rows are checked
against train; terminal-evaluation rows are checked against the retained train and
validation rows. Collisions are removed before class coverage is checked again.

`DatasetBuilder.build_splits()` writes partitions and a SHA-256 manifest.
`publish_reviewed_dataset()` stages rows, statistics, partitions, and manifests,
verifies exact membership, and atomically changes the current pointer.

### 8. Current promoted snapshot

These counts are copied from the retained governance/report authority; this guide
does not reopen the sealed terminal partition.

| Class | Train | Validation | Terminal evaluation | Total |
| --- | ---: | ---: | ---: | ---: |
| Bank impersonation | 595 | 76 | 70 | 741 |
| Benign | 517 | 72 | 66 | 655 |
| Task scam | 306 | 49 | 49 | 404 |
| Zalo social engineering | 240 | 22 | 35 | 297 |
| **Total** | **1,658** | **219** | **220** | **2,097** |

Whole-seed split disjointness passed. The largest retained seed group contains 167
rows, or 7.9638% of the corpus, below the declared 8% cap.

## How training uses the label

### Qwen QLoRA

`src/model_adaptation/data.py::build_training_examples()` serializes the dataset
fields into an assistant JSON response. The string in `record["label"]` therefore
appears as supervised answer text.

`tokenize_phase40_response_only()` masks all system and user prompt tokens with
`-100`. Only assistant-response token IDs remain in the Hugging Face `labels`
tensor. Qwen learns to generate the full structured JSON response, including the
class label, risk tier, spans, and explanation.

This is supervised learning even though the output is generated token by token.
It is not a four-logit classification head.

### PhoBERT

PhoBERT uses a fixed mapping:

| Label | ID |
| --- | ---: |
| `bank_impersonation` | 0 |
| `zalo_social_engineering` | 1 |
| `task_scam` | 2 |
| `benign` | 3 |

`preprocess_phobert_snapshot()` maps the string label to this integer and emits
`input_ids`, `attention_mask`, and `labels`. The sequence-classification model
produces four logits; ordinary classification loss trains the encoder and head.

PhoBERT is a full classifier. It is not LoRA, not QLoRA, and not GGUF. It does not
natively generate Qwen's explanation and recommendation contract.

## Ordinary LoRA, QLoRA, and PhoBERT

| Method | Base model in training | Trainable part | Output form | Project status |
| --- | --- | --- | --- | --- |
| Qwen LoRA probe | Non-quantized Qwen base | LoRA adapters | Structured generated JSON | Bounded resource probe only; no OOM and no completed full-LoRA result |
| Qwen QLoRA | Qwen base loaded in 4-bit NF4 | LoRA adapters | Structured generated JSON | Completed local training; selected adapter merged for export |
| PhoBERT | Non-quantized encoder classifier | Full encoder and classification head | Four class logits | Completed local training; native classifier bundle |

LoRA and QLoRA both freeze the Qwen base and train adapters. QLoRA reduces training
memory by loading the base through bitsandbytes 4-bit NF4 with double quantization.
The implementation proves actual `Linear4bit` modules and finite nonzero adapter
gradients; a CLI flag alone is not accepted as evidence.

The selected Qwen adapter was merged and converted to a Q8_0 GGUF for local
runtime use. NF4 is the training representation; Q8_0 is the runtime export. Only
Qwen has a verified GGUF artifact.

## Metric generation and evaluation authority

`evaluate_phase40_predictions()` is the shared metric engine.

- Qwen output is parsed as strict JSON. Malformed or unknown labels become
  `invalid_output`; they are not silently repaired.
- PhoBERT selects the argmax of exactly four finite logits in the locked label
  order.
- Both paths must match the expected row ID, row order, gold label, and candidate
  identity before scoring.
- The engine calculates per-class precision, recall, and F1; macro and weighted
  F1; accuracy; confusion matrix; invalid-output rate; risky-to-benign errors; and
  risky-to-invalid errors.

Checkpoint selection first enforces risky-class recall floors and zero invalid
outputs, then ranks eligible checkpoints using macro F1, risky-to-benign count,
earlier step, and artifact identity.

Development validation used 219 aligned rows. One frozen terminal evaluation then
used the same 220-row cohort for both selected models. It did not cause retraining,
repair, threshold changes, checkpoint reselection, or a retry.

| Model | Validation macro F1 | Terminal macro F1 |
| --- | ---: | ---: |
| Qwen QLoRA | 0.9885153110 | 0.980493 |
| PhoBERT | 0.9848929140 | 0.990892 |

These are one-seed descriptive results. They do not support a t-test, confidence
interval, statistical significance, stable superiority, or a fair cross-family
speed comparison.

Use `src/modeling/evidence.py::load_reporting_authority()` for report facts. It
verifies the pinned export, links, hashes, source closure, and mandatory erratum.
Do not casually rerun the terminal evaluator.

## Runtime input-to-output workflow

```text
vnphish analyze / python -m src.runtime.cli analyze
  -> cli.handle_analyze()
  -> runtime readiness check
  -> RuntimeService.analyze_text()
  -> normalize text and enforce privacy/input boundaries
  -> AnalysisRequest(text, channel)
  -> modeling.InferenceService.infer()
  -> configured heuristic, GGUF, or accelerated backend
  -> strict structured parsing
  -> exact-span grounding and deterministic safety floor
  -> AnalysisResult
  -> terminal renderer or local browser UI
```

The safety floor can conservatively raise risk or add safe advice when deterministic
cues demand it. It must not invent a cue: each grounded span must be found in the
input text.

## Safe commands for a defense

Read-only discovery:

```powershell
python -m src.data_pipeline.cli --help
python -m src.data_pipeline.scraper.real_sources --help
python -m src.model_adaptation.cli --help
python -m src.runtime.cli --help
```

Runtime readiness and a local text demonstration:

```powershell
python -m src.runtime.cli doctor
python -m src.runtime.cli analyze --text "<Vietnamese message>" --channel zalo
python -m src.runtime.cli demo --host 127.0.0.1 --port 8765 --no-browser
```

Suggested suspicious demonstration message:

```text
【VIETCOMBANK】 Tai khoan cua ban vua bi truy cap tu thiet bi la luc 03:47 SA. Neu ko phai ban, bam vao link de khoa ngay: http://vcb-secure-alert.net/lock?id=9182736 hoac goi 1800.9999 (mien phi).
```

Suggested benign-but-security-related message:

```text
VPBank Smart OTP: Mã xác thực của bạn là 847291. Mã này có hiệu lực trong 90 giây để xác nhận đăng nhập Internet Banking. Tuyệt đối KHÔNG chia sẻ mã này với bất kỳ ai, kể cả nhân viên ngân hàng.
```

Do not live-run provider generation, training, model conversion, or terminal
evaluation during the defense. Explain those stages from configuration, manifests,
receipts, and frozen evidence.

## Failure and recovery chronology

| Failure | What happened | Defensible lesson |
| --- | --- | --- |
| Zalo narrator framing | Generated rows described a scenario instead of presenting the direct message | Semantic review caught a realism defect that structural validation could not; rows were reconstructed from 60 preserved roots, then revalidated and regrouped |
| Seed concentration/leakage pressure | One label originally traced to too little root diversity | Variants retained root IDs and whole groups were assigned together; no fake diversity was created by renaming paraphrases |
| Automated judge disagreement | Judge and human review disagreed on part of a stratified sample | The 44/100 human PASS result is bounded corroboration, not corpus prevalence; agreement was 87/100 |
| Ordinary LoRA resource probe | No OOM occurred, but peak observed VRAM was 7,902/8,151 MiB and the incomplete-window ETA was about 18.42--18.88 hours | Resource measurements supported choosing QLoRA; there is no completed LoRA accuracy comparison |
| First full Qwen attempt | Run-root and canonical-JSON operator defects interrupted the attempt | Failure was preserved; a clean step-zero run supplied the accepted evidence |
| Terminal launcher setup | Five attempts failed before their invocation-local claim boundary | Pre-claim failure is not a model result; exactly one shared-cohort model-evaluation pass was accepted |
| Prior-access wording | Earlier tests had parsed/statted/hashed the terminal files | The result remains one-shot, but “untouched” and “zero prior filesystem access” were retracted in a mandatory erratum |
| Architecture review | Latest review found six critical and three warning issues | The refactor improves navigation but is not security-closed or production-ready |

## Claims you must not make

- Do not call the terminal split untouched or claim zero prior filesystem access.
- Do not claim statistical significance, a stable winner, or run-to-run variance.
- Do not claim ordinary LoRA OOM or a completed LoRA accuracy result.
- Do not claim PhoBERT was converted to GGUF.
- Do not claim deployment fitting is complete.
- Do not turn 44/100 into a corpus-wide pass or failure rate.
- Do not call Pydantic the semantic judge.
- Do not claim the entire final corpus was generated by one model family.
- Do not claim the architecture review is closed.
- Do not imply that the current refactor produced the frozen metrics.

## Best five-minute code walkthrough

1. Open `DatasetRecord` and point to `label`, `seed_id`, and substring-validated
   `suspicious_spans`.
2. Open `build_training_corpus()` and explain orchestration versus implementation.
3. Open `split_dataset()` and show the explicit rejection when one seed spans
   labels, followed by whole-group assignment.
4. Open `build_training_examples()` and
   `tokenize_phase40_response_only()` to show how Qwen receives supervision.
5. Open PhoBERT preprocessing and show `PHOBERT_LABEL_TO_ID`.
6. Open `evaluate_phase40_predictions()` and explain strict aligned predictions.
7. Open `RuntimeService.analyze_text()` and follow one message to
   `AnalysisResult`.

The strongest defense is a mechanism plus a file, an artifact, and a limitation.
Do not answer with a metric alone.
