# Defense Q&A Worksheet

This file is for practice, not for memorizing polished prose. The student answers
first. Claude then checks the answer against current source and retained evidence.
Claude must never treat an answer that Claude rewrote as proof that the student
understands it.

Start with the must-pass round. Ask one question at a time and do not reveal the
judge checklist until the student has answered.

## Scoring rule

Score each answer out of 8:

| Dimension | Points | Test |
| --- | ---: | --- |
| Correctness | 0–2 | No factual contradiction with current source/evidence |
| Mechanism | 0–2 | Explains how the code or method works, not only what it produced |
| Evidence | 0–2 | Names a file/function plus a number, artifact, or contract when relevant |
| Limitation | 0–1 | States the boundary of the claim |
| Ownership | 0–1 | Clearly distinguishes the student's decisions/work from model or tool assistance |

Pass is at least 6/8 with no critical contradiction. A critical contradiction is
an automatic retry even when the total would otherwise pass.

Critical contradictions include:

- saying the terminal split was untouched or had zero prior filesystem access;
- saying ordinary LoRA ran out of memory;
- saying PhoBERT is LoRA, QLoRA, or GGUF;
- saying Pydantic performed semantic quality judging;
- claiming statistical significance, a t-test, or stable model superiority;
- interpreting 44/100 as the corpus-wide pass/failure rate;
- claiming the architecture/security review is closed;
- claiming all final rows came from one generator/model family;
- claiming a terminal-evaluation retry or evaluation-driven dataset/model repair;
- inventing a file, metric, hyperparameter, or deployment result.

## Must-pass round

### 1. What exactly is the task, input, and output?

My answer:

> 

File/function I can open:

> 

Number or artifact I cited:

> 

Limitation I stated:

> 

Claude score and correction:

> 

Retry answer:

> 

Judge checklist after the answer: distinguish the four-class dataset task from the
installed text-analysis contract; name raw text plus optional channel as input;
name risk tier, labels, grounded cues, summary, and recommendations as output; state
that OCR/images/audio are outside the current runtime.

### 2. How was the dataset constructed and verified?

My answer:

> 

File/function I can open:

> 

Number or artifact I cited:

> 

Limitation I stated:

> 

Claude score and correction:

> 

Retry answer:

> 

Judge checklist after the answer: roots/seeds, model-assisted variants, structural
schema/span validation, semantic judging and human repair, deduplication,
group-integrity splitting, class/concentration checks, and SHA-256 manifests.
Require disclosure that the content is synthetic/model-assisted and provenance is
mixed.

### 3. Where is the label stored?

My answer:

> 

File/function I can open:

> 

Number or artifact I cited:

> 

Limitation I stated:

> 

Claude score and correction:

> 

Retry answer:

> 

Judge checklist after the answer: point to
`src/data_pipeline/core/records.py::DatasetRecord.label`; distinguish it from
`risk_tier`; name the four allowed string labels.

### 4. How does Qwen training use that label?

My answer:

> 

File/function I can open:

> 

Number or artifact I cited:

> 

Limitation I stated:

> 

Claude score and correction:

> 

Retry answer:

> 

Judge checklist after the answer: `build_training_examples()` serializes the label
inside assistant JSON; `tokenize_phase40_response_only()` masks prompt tokens with
`-100`; the supervised target is the assistant token sequence, not one integer
class ID.

### 5. How does PhoBERT training use the label differently?

My answer:

> 

File/function I can open:

> 

Number or artifact I cited:

> 

Limitation I stated:

> 

Claude score and correction:

> 

Retry answer:

> 

Judge checklist after the answer: show the locked label-to-ID map 0–3,
preprocessing to integer `labels`, and four-logit sequence-classification loss.
State that PhoBERT does not natively generate the richer explanation contract.

### 6. What changes between PhoBERT, ordinary LoRA, and QLoRA?

My answer:

> 

File/function I can open:

> 

Number or artifact I cited:

> 

Limitation I stated:

> 

Claude score and correction:

> 

Retry answer:

> 

Judge checklist after the answer: ordinary Qwen LoRA uses a non-quantized frozen
base plus adapters; QLoRA uses a 4-bit NF4 frozen base plus adapters; PhoBERT is a
fully trained encoder/classifier with four logits. Reject “LoRA OOM” and “PhoBERT
GGUF.”

### 7. How did you prevent duplication and leakage?

My answer:

> 

File/function I can open:

> 

Number or artifact I cited:

> 

Limitation I stated:

> 

Claude score and correction:

> 

Retry answer:

> 

Judge checklist after the answer: exact/near deduplication, `seed_id` as the root
scenario identity, rejection of a seed spanning labels, whole-group deterministic
assignment, cross-split semantic collision checks, post-cleanup class coverage, and
the 8% concentration cap. Paraphrases must not be relabeled as new roots.

### 8. How were the metrics and confusion matrices generated?

My answer:

> 

File/function I can open:

> 

Number or artifact I cited:

> 

Limitation I stated:

> 

Claude score and correction:

> 

Retry answer:

> 

Judge checklist after the answer: exact row-ID/order/gold/candidate alignment;
strict Qwen JSON parsing versus PhoBERT argmax; locked label order; per-class,
macro, weighted, accuracy, confusion matrix, invalid-output, and dangerous-error
metrics. Require validation versus terminal-evaluation separation.

### 9. What failed, why, and what would you change?

My answer:

> 

File/function I can open:

> 

Number or artifact I cited:

> 

Limitation I stated:

> 

Claude score and correction:

> 

Retry answer:

> 

Judge checklist after the answer: choose concrete examples such as narrator-style
Zalo rows, root concentration, Qwen operator defects, launcher setup failures,
prior-access wording, and open architecture debt. The answer must connect each
failure to a control or future design change, not hide it.

### 10. What is your personal contribution?

My answer:

> 

File/function I can open:

> 

Number or artifact I cited:

> 

Limitation I stated:

> 

Claude score and correction:

> 

Retry answer:

> 

Judge checklist after the answer: the student must name decisions and work they can
explain—schema, seed-group governance, validation gates, training/evaluation
protocol, failure handling, runtime integration, and evidence/report discipline.
AI assistance must be disclosed without surrendering or fabricating ownership.

## Extended question bank

Claude should choose questions based on weak prior answers. It must not reveal the
“strong answer must cover” column before the student answers.

### Dataset and provenance

| # | Jury question | Evidence to inspect | Strong answer must cover |
| ---: | --- | --- | --- |
| 11 | Why start from root seeds instead of generating unrelated messages from scratch? | `core/records.py`, `generation/generator.py` | Traceability, variant grouping, reproducibility, and leakage control; seeds do not automatically prove realism |
| 12 | How were the four classes chosen? | schema enum, report methodology | Project scope and distinct operational patterns; acknowledge overlap and limited taxonomy |
| 13 | Show one JSON row and point to the training indicator. | `DatasetRecord`, safe fixture/example | `label` is the class; `risk_tier` is severity; spans/explanation are auxiliary supervised fields |
| 14 | Why is synthetic data a weakness? | report evidence map, Phase 39 note | Generator style/bias, coverage limits, same-family exception, and need for broader real-world validation |
| 15 | What does the automated judge actually judge? | `quality_judge.py` | Five semantic dimensions and threshold; separate this from Pydantic schema validation |
| 16 | What does 44/100 mean? | final manual sheet, report evidence map | Stratified bounded corroboration: 44 PASS, 56 FAIL, 87 agreement; not population prevalence |
| 17 | Why are Codex-named Zalo files still in source? | migration registry and catalog modules | Exact one-off repair provenance and path-bound reproducibility; not an installed runtime/provider dependency |
| 18 | How do you know suspicious spans are grounded? | `DatasetRecord`, local-model parser | Every span is an exact substring; runtime rechecks grounding; semantic usefulness is a separate question |
| 19 | Could the same scam appear under two labels? | `split_dataset()` | Ambiguity is possible conceptually, but one `seed_id` spanning stored labels fails closed; taxonomy decisions need review |
| 20 | Can the whole corpus be regenerated with one command today? | `generator._build_batch_specs`, `split_dataset()` | No guaranteed clean rebuild: retained cross-class seed reuse can fail closed; future fix needs independent class roots, not fake IDs |

### Training and model design

| # | Jury question | Evidence to inspect | Strong answer must cover |
| ---: | --- | --- | --- |
| 21 | Why is Qwen training supervised classification if it generates JSON? | `data.py` | Label tokens are part of the gold assistant response and prompt tokens are masked |
| 22 | Why not attach a four-class head to Qwen? | model/output contracts | A head would simplify class prediction but would not directly produce spans/explanations/recommendations; discuss tradeoff, not absolute superiority |
| 23 | Why use Qwen when PhoBERT measured higher on the terminal cohort? | frozen metrics | Qwen provides richer structured local output; PhoBERT measured higher on one cohort; no stable-winner claim |
| 24 | Why NF4 in training and Q8_0 at runtime? | QLoRA mode proof, GGUF receipt | Different purposes: training memory versus portable local inference; only Qwen exported to GGUF |
| 25 | How do you prove it was genuinely QLoRA? | `phase40_modes.py` | bitsandbytes version/config, real `Linear4bit`, frozen base, adapter-only trainables, nonzero finite gradients |
| 26 | What happened in the ordinary LoRA experiment? | local probe report | No OOM; near-full VRAM and long incomplete-window ETA; resource probe only, no accuracy comparison |
| 27 | How was a checkpoint selected? | `phase40_metrics.py` | Recall/invalid-output gates first, then deterministic ranking; validation only |
| 28 | Why only one training seed? | verification/report limits | Time/resource constraint; deterministic evidence, but no variance or significance conclusion |
| 29 | What did conversion to GGUF change? | GGUF receipt, runtime analyzer | Packaging/quantized runtime artifact; it did not retrain the model or create PhoBERT GGUF evidence |
| 30 | Are Qwen and PhoBERT speed results directly comparable? | evidence map | No: generative structured decoding versus classifier forward pass; current protocol does not support a fair speed ranking |

### Evaluation, evidence, and claims

| # | Jury question | Evidence to inspect | Strong answer must cover |
| ---: | --- | --- | --- |
| 31 | What is the difference between validation and terminal evaluation? | training-evaluation doc | Validation selects checkpoints; terminal cohort is one final descriptive pass with no feedback loop |
| 32 | Was the terminal partition untouched? | mandatory erratum | No. Automated integrity reads occurred before inference; exactly one model-evaluation pass occurred and did not influence training/repair |
| 33 | Why is there no t-test? | evidence map | One seed/run per family gives no run-to-run sample for valid inference; report descriptive metrics only |
| 34 | What does SHA-256 contribute? | manifests/evidence loader | Identity and tamper detection; not realism, correctness, privacy, or generalization |
| 35 | How do malformed Qwen outputs affect metrics? | strict parser | They become `invalid_output`; they are not repaired into a favorable class |
| 36 | Which error is most safety-sensitive? | metric engine | Risky-to-benign and risky-to-invalid paths; explain why recall floors matter |
| 37 | Explain one confusion matrix. | retained metric summary | Rows/columns and concrete misclassifications; do not invent counts from memory |
| 38 | Why can’t you claim PhoBERT is the winner? | evidence map | Higher terminal value on one fixed cohort is descriptive, with one seed and no variance estimate |
| 39 | Did evaluation cause dataset or model repair? | terminal policy and review resolution | No retraining, repair, thresholding, checkpoint reselection, retry, or contingency activation |
| 40 | What remains unverified? | evidence map/review | Real-world generalization, deployment fit, review/security closure, multi-seed variance, broader human annotation |

### Runtime and architecture

| # | Jury question | Evidence to inspect | Strong answer must cover |
| ---: | --- | --- | --- |
| 41 | Follow one input from CLI to final output. | `runtime/cli.py`, `service.py`, `inference.py`, `local_model.py` | Readiness, normalization, request, backend, strict parse, grounding/safety, result, rendering |
| 42 | How does the browser UI connect to the same model path? | `runtime/demo.py`, service | HTTP UI is a wrapper around the same runtime service/contract, not a second model implementation |
| 43 | Is there RAG or a knowledge base? | runtime/modeling map | No. It is local supervised inference plus deterministic validation/safety rules |
| 44 | Why text-only? | runtime contract | Bounded scope/privacy/reproducibility; images/OCR/audio are future work, not hidden features |
| 45 | What protects user privacy? | service/contracts/docs | Local inference intent and no raw-text persistence by default; do not overclaim production security |
| 46 | Why are phase-numbered files still present? | `src/README.md`, adapters | Frozen compatibility/provenance implementation behind domain interfaces; current review still reports debt |
| 47 | Is the codebase production-ready? | Phase 41.1 review | No: six critical and three warnings remain; explain improvements and limits honestly |
| 48 | What failed in the architecture review? | `41.1-REVIEW.md` | Give one concrete security or boundary issue and proposed fix, not merely the count |
| 49 | What would you change with another month? | open debt + generator caveat | Fix generator root assignment, close security findings, multi-seed evaluation, broader human data, deployment fit |
| 50 | How would another developer reproduce the result? | manifests, configs, evidence docs | Exact environment/config/artifact identities and frozen receipts; distinguish reproducibility from rerunning terminal evaluation |

### Ownership and research conduct

| # | Jury question | Evidence to inspect | Strong answer must cover |
| ---: | --- | --- | --- |
| 51 | Did AI tools help generate data, code, or prose? | provenance/report notes | Disclose tool assistance, human decisions/review, same-family limitation, and what the student can independently explain |
| 52 | What decision was yours rather than the model’s? | planning/source/evidence | Name a concrete design choice and rationale; avoid claiming authorship of work not understood |
| 53 | How did you detect a plausible-looking but bad result? | narrator repair/manual review | Structural checks were insufficient; semantic judge and human audit exposed realism/label problems |
| 54 | What result are you least confident in? | limitations | Choose a real limitation and explain how to improve the evidence |
| 55 | If you do not know an answer in the defense, what do you do? | source map | Say what is known, point to the authority, state uncertainty, and do not invent precision |

## Claude coaching protocol

Use this prompt when starting a practice session:

```text
You are a strict internship-defense jury. Read CLAUDE.md,
documents/defense/CODE_WORKFLOW.md, this worksheet, and the report evidence map.
Ask one question at a time. Do not reveal the checklist or a model answer before I
answer. Quote my answer verbatim into the matching worksheet entry, then score it
out of 8 for correctness, mechanism, evidence, limitation, and ownership. Mark any
unsupported precision or prohibited claim as wrong. If I score below 6/8 or make a
critical contradiction, explain the smallest correction and require me to answer
again. Do not count your rewritten answer as proof that I understand it.
```

## Practice-session log

Date:

> 

Questions attempted:

> 

First-pass scores:

> 

Repeated weaknesses:

> 

Files I could not navigate quickly:

> 

Claims I must stop saying:

> 

Next drill:

> 
