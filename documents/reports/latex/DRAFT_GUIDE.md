# Draft guide — what each chapter says, in plain words

**How to use this.** This is deliberately written as scrappy bullets, not as report prose,
so you cannot paste it into the report. Read the bullets, understand the content, then
write the chapter in your own sentences. Hand it back and I fix grammar only.

**The one rule:** if you cannot say a sentence out loud in your own words, do not put it in
the report. A jury that already suspects fabrication reads perfect English as more evidence
of it. Rough and yours beats polished and borrowed.

---

## Numbers you must know cold

These come up in every chapter. If a juror asks and you hesitate, that's the whole game.

| Thing | Number |
|---|---|
| Final corpus | **2,097** rows, 4 classes |
| Splits | 1,658 train / 219 validation / **220 terminal** |
| Class counts | 741 bank / 655 benign / 404 task scam / 297 Zalo |
| Judge pass rate | 1,395 of 2,097 = **66.52%** |
| Your own human sample | 100 rows, **44 PASS / 56 FAIL**, agrees with judge 87/100 |
| Qwen training | 1,245 steps, 3 epochs, seed 42, **14.87 hours** |
| PhoBERT training | 312 steps, 3 epochs, seed 42, ~2 minutes |
| Selected checkpoints | Qwen step **200**, PhoBERT step **100** |
| Validation macro-F1 | Qwen 0.9885, PhoBERT 0.9849 |
| **Terminal** macro-F1 | Qwen **0.980493**, PhoBERT **0.990892** |
| Terminal errors | Qwen 4 of 220, PhoBERT 2 of 220 |
| Safety count | **Both models: exactly 1 risky→benign error.** A tie. |
| Invalid outputs | **0** from both |
| GGUF | 4,280,403,232 bytes, Q8_0 |
| GPU | RTX 5050 Laptop, 8,151 MiB |

**The single most useful sentence you can have ready:** *"PhoBERT scored higher overall, but
on the one metric that matters for a phishing detector — a dangerous message called safe —
they tied at one error each. And it's one seed, so I can't claim a winner."*

---

## Chapter 1 — Introduction

**Job:** say what the problem is and what you set out to do. Nothing technical yet.

What it currently says:
- Vietnamese phishing arrives by SMS and Zalo/Messenger/Telegram. Those messages contain
  bank details, OTPs, account-recovery prompts — things you don't want to upload anywhere.
- "Localized" means **two** things and you need both: (a) runs on-device, no cloud calls,
  so private messages stay private; (b) the model is tuned to *Vietnamese* scam patterns,
  not generic multilingual.
- Three constraints you set yourself: text only, offline by default, prioritise catching
  the dangerous classes.
- The actual ML task: **supervised four-class classification.** One message in, one label
  out — bank impersonation / Zalo social engineering / task scam / benign — plus a risk
  tier and evidence spans.
- Three research questions: RQ1 what performance do the two models get; RQ2 is this
  feasible on a laptop and why QLoRA over LoRA; RQ3 can it explain itself instead of just
  giving a score.
- Contributions: the governed corpus, the Zalo repair, two locally trained models, the
  GGUF export, one terminal evaluation, and the code reorganisation.
- Scope limits: no images/QR, no voice, no deepfakes, no malware. Not real traffic.

**Juror will ask:** "Why not just use ChatGPT?" → privacy: the message never leaves the
laptop. That's the whole point of the project.

---

## Chapter 2 — Related work, then Objectives

**Job:** show you read the field, then list what you promised to deliver.

- Related work covers Vietnamese NLP (PhoBERT, ViSoBERT), phishing detection with LLMs,
  parameter-efficient fine-tuning (LoRA, QLoRA), and explainability.
- Objectives chapter lists **six deliverables**: build the corpus, do human review with
  lineage governance, repair the Zalo scaffolding problem, measure LoRA vs QLoRA on real
  hardware, train both models and verify the GGUF, and reorganise the code.
- It then says honestly which ones landed and which didn't: deployment fitting deliberately
  deferred; the code reorganisation improved structure but a later review found security
  findings, so it's reported as a structural win, not a closed security claim.

**Write this in your own words** — it's the easiest chapter to make sound like you, because
it's just "here's what I said I'd do, here's what happened."

---

## Chapter 3 — Methodology and system design

**Job:** how the thing was built. Biggest chapter.

### Data construction (the part jurors attack)
- Seeds came from a crawler over `tinnhiemmang.vn` alert pages.
- Those seeds were expanded into a **synthetic** corpus. Say this plainly and early.
- Every generated row passes a **Pydantic schema gate** — types, required fields, allowed
  labels, score ranges, span structure.
- **Pydantic is NOT the semantic judge.** It checks shape only. A separate model judge
  scores meaning. Get this distinction right; it's a classic trap.
- Split governance: rows are grouped by `seed_id`, and a whole seed group goes to one split.
  So a paraphrase of a training message can never appear in the test set.
- Concentration cap: largest seed is 7.9638% of the corpus, under the 8% you predeclared.

**Figures here:** `seed_data_sample.png` (real scraped advisory text with URL + timestamp)
and `human_review_sheet.png` (you overruling the judge). `corpus_sample.png` goes here too
once you shoot it.

### Training method
- Qwen3-4B-Instruct with **NF4 QLoRA**: base weights frozen in 4-bit, only the low-rank
  A and B matrices get updated. 252 Linear4bit modules, 504 trainable adapter tensors.
- Loss is ordinary causal-LM cross-entropy over the whole response *including the literal
  label text*, so a wrong label costs you loss directly.
- PhoBERT is the contrast: a full, non-quantised four-class classification head.
- Both on the same 1,658 train / 219 validation identities, seed 42.

**Juror will ask:** "What does QLoRA actually do?" → the big model sits frozen in 4-bit so
it fits in 8 GB; you train two small matrices bolted onto it. That's it. Be able to say
that without notes.

---

## Chapter 4 — Implementation

**Job:** what you actually ran, with evidence.

- Section on the system boundary and the artifact flow diagram.
- Dataset construction and repair: 2,097 judge verdicts joined from 1,561 carried +
  536 freshly judged.
- **The probes.** You measured before committing:
  - Ordinary LoRA: ran, but stopped with `parent_controller_error` after 31 events. Peaked
    at 7,902/8,151 MiB with **9 MiB free**. Median step 53.27 s. Projected 18.42 hours.
  - **No OOM happened.** Never say LoRA ran out of memory — it didn't, it was just
    impractical. This is a rule.
  - QLoRA probe: 5 warm-up + 40 measured steps, 395 MiB free, median step 3.46 s.
- **The full runs.** Qwen 1,245 steps over 14.87 hours; PhoBERT 312 steps in ~2 minutes.
- Artifact export: selected Qwen adapter merged with the pinned base, converted through
  llama.cpp to one Q8_0 GGUF, and load-smoked twice (original + independent).

**Figures here:** `training_console_probe.png`, `full_run_timeline.png`,
`checkpoint_selection_sweep.png`, `model_files_on_disk.png`, plus the two loss curves.

**The 14.87-hour explanation — put this in, it's your best paragraph.** The steps themselves
were only 1.36 hours (9%). The other ~13 hours is 25 checkpoint validation passes, each one
generating structured output for all 219 validation rows — 5,475 generations total on a
laptop GPU. Volunteering this kills the obvious question before it's asked.

---

## Chapter 5 — Evaluation and discussion

**Job:** four *different* kinds of evidence, kept separate on purpose.

The chapter opens by saying why they're separate: a good validation score doesn't prove the
data is realistic, a resource probe doesn't prove accuracy, and one terminal run doesn't
tell you anything about variance. Keep that framing — it's the honest spine of the chapter.

1. **Corpus quality.** 66.52% judge pass. Rubric means: realism 4.020, label correctness
   4.851, code-switch 4.672, risk tier 4.119, span accuracy 4.745. Your human sample:
   44/100 pass, 87/100 agreement with the judge.
   - The 324-candidate task-scam review: you approved 233 relabels but **only admitted 57**.
     176 were thrown out because they shared one non-independent lineage. **This is a
     strength, not a weakness** — you applied your own rule even when it cost you data.
2. **Resource evidence.** The probes above. Conclusion is deliberately narrow: LoRA was
   runnable but had no headroom and a bad deadline; QLoRA had headroom.
3. **Development validation.** Qwen 0.9885 at step 200, PhoBERT 0.9849 at step 100.
4. **Terminal evaluation.** One pass, 220 rows. Qwen 0.980493, PhoBERT 0.990892.

**Figures here:** `gpu_telemetry_probe.png`, `terminal_evaluation_confusion.png`,
`gguf_conversion_receipt.png`.

### The Limits section — do not cut this
Nine explicit limitations: synthetic corpus, bounded human corroboration, judge-family
overlap on the reconstructed Zalo rows, one seed, the evaluation-file access disclosure,
terminal policy, artifact scope, open architecture review debt, operational generalisation.

This section is why the report survives cross-examination. Every one of these is a question
a juror would otherwise ask *you*, and you answered it first.

### The provenance correction — keep it exactly as it is
The report says the phrase "zero prior filesystem access" **would be false**, because
automated integrity tests parsed, statted, and hashed the split files before the terminal
run. Those reads showed nothing to a human, ran no model, and changed no result.

Say it exactly that way: *one shared-cohort evaluation pass; earlier automated tests had
read the files without model inference or human viewing.* Never say "untouched" or "zero
access". This is the correction that turns a weakness into evidence you're careful.

---

## Chapter 6 — Conclusion

**Job:** what you built, what it showed, what's next. No new facts.

- Restates: governed corpus, two locally trained models, verified GGUF, one terminal
  evaluation, reorganised code.
- Repeats the honesty: single-run observations, no variance, no significance, no fair
  speed comparison between a generative and a discriminative model.
- Future work: real-traffic validation, more seeds, human evaluation of explanation
  quality, closing the security findings.

---

## Things you must never write

- t-test, p-value, confidence interval, statistical significance, "stable winner"
- "LoRA ran out of memory" / OOM — it didn't
- a completed full-LoRA accuracy number — doesn't exist
- PhoBERT GGUF — doesn't exist
- completed deployment fitting — deferred on purpose
- a fair Qwen-vs-PhoBERT speed comparison — inadmissible, different output mechanisms
- 44/100 as a corpus-wide failure rate — it's a stratified sample
- "Pydantic judged quality" — it validates structure only
- "the architecture review is closed" — six critical findings are open
- any SHA-256 value, or "Phase 40 / Phase 41" in prose

---

## Practical to-dos while you rewrite

1. **Add a sentence referencing each new figure.** Eight of them currently have no
   "as shown in Figure~\ref{...}" in the text. When you rewrite a section, mention its
   figure naturally — that's the normal academic pattern and it makes placement stable.
   Labels available: `fig:seed-sample`, `fig:human-review`, `fig:probe-console`,
   `fig:run-timeline`, `fig:checkpoint-sweep`, `fig:artifacts-on-disk`, `fig:gpu-telemetry`,
   `fig:gguf-receipt`, `fig:terminal-confusion`.
2. **Capture `corpus_sample.png`** (train.jsonl line 222) and uncomment the block in
   chapter 3 — it's marked with a TODO comment.
3. **Close Foxit PDF Editor** before building, or the build fails on a locked file.
4. Build with: `pwsh -File documents\reports\latex\build_report.ps1`

## Suggested order

Chapter 5 first (you know these numbers best and it's the chapter jurors dig into), then
chapter 4, then 3. Leave 1, 2 and 6 for last — they're the easiest once the middle is solid.
