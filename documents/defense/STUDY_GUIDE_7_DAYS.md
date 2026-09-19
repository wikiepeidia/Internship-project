# VNPhish: 7-Day Study Guide

You have one week to learn your own project well enough to explain it and defend
it. This guide walks the project in the order you built it, from the first web
page you crawled to the app on your screen. Each day has a small amount of code
to read, a small experiment to run, and questions to answer out loud.

How to use it:

1. Do one day at a time, about two to three hours each.
2. Open the files named in the day. Read only the functions listed.
3. Run the exercise. Nothing in this guide loads a model, calls an API, or opens
   the sealed test file.
4. Answer the self-test out loud, without looking. Then check yourself.
5. The "say it aloud" paragraphs are a starting point. Put them in your own words.
   A juror can tell the difference, and only your own wording counts as knowing it.

`CODE_WORKFLOW.md` (same folder) is the reference map. This guide is the way to
learn it. Line numbers below were correct when this guide was written; if one has
drifted, search the file for the function name.

---

## Day 0: get the app running (30 minutes)

**Start the demo.** Double-click `START_DEMO.bat` in the project root. Wait about
20 seconds while the model loads. A browser tab opens. Paste a message and press
analyze. One analysis takes about 30 seconds because it runs on the CPU.

**Why the old launchers stopped working.** Earlier in the project two Windows
environment variables were set to point at the model on the D: drive
(`MODEL_ARTIFACT_ROOT` and `MODEL_REGISTRY_PATH`). Later the settings code gained a
rule that the artifact folder must sit strictly inside a storage folder. With those
two variables the rule fails, so the app refused to start. `START_DEMO.bat` replaces
the variables for its own window only, and points at a local copy of the model:

- model file: `data/runtime/models/exports-v3/qwen-qlora-q8_0.gguf` (4,280,403,232 bytes)
- registry: `data/runtime/manifests/model-registry.json`

The D: drive is untouched.

**What still says "NOT READY", and why.** `python -m src.runtime.cli doctor` and
`analyze` refuse to run. The last check they make ("release-gate-summary") reads the
newest release result in `data/manifests`, which is an early pilot run from May with
verdict BLOCK (its `task_scam` recall was 0.44 against a 0.90 floor). The final
evaluation is not wired into that check. Use the browser demo for the defense. If
someone runs `doctor`, say exactly that.

**Do not touch:**

- `data/splits/test.jsonl`, or list the `data/splits` folder.
- The D: drive model folders.
- The files listed in `data/models/phase41/execution-source-manifest.json`. 31 of the
  37 files in that list still match their recorded SHA-256 byte for byte,
  including the training code. That is your proof that the code in the repository
  is the code that trained the models. Adding even a comment to one of them breaks
  that. This is why the code-comment clean-up skipped `src/model_adaptation/`.
- The sealed export, the erratum, and the manifests.

**Run the tests safely** (from the project root, PowerShell). The guard and the
model paths must be set, or the architecture tests refuse to start:

```powershell
$env:PHASE411_DENY_OPEN_SENTINEL = "1"
$env:PYTHONPATH = "tests/architecture/bootstrap"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"
$env:MODEL_STORAGE_ROOT = "$PWD\data\runtime"
$env:MODEL_ARTIFACT_ROOT = "$PWD\data\runtime\models"
$env:MODEL_REGISTRY_PATH = "$PWD\data\runtime\manifests\model-registry.json"
python -m pytest tests/runtime/test_cli.py tests/runtime/test_service.py -q
```

Run named files only, never `pytest` on its own. The known baseline is four failing
tests that were failing before any of this week's changes (see "Known problems").

---

## The whole project on one page

| # | What happened (your words) | What the code does | Main files | Report |
| - | --- | --- | --- | --- |
| 1 | Scraped scam-warning pages | Downloads pages, pulls out the message text, keeps the source URL | `scraper/ncsc_scraper.py`, `scraper/extractors.py`, `scraper/real_sources.py` | Ch. I, III |
| 2 | Claude wrote the fake scam messages | Turns each seed into labeled variants, in batches | `generation/generator.py`, `generation/prompts.py` | Ch. III |
| 3 | Rate limit, crash, overwritten data, fix | Saves each finished batch so a rerun can resume | `generator.py` (checkpoints) | Ch. IV, Appx |
| 4 | A judge model scored every message | Five scores 1 to 5, pass needs all at least 3 | `generation/quality_judge.py`, `judge_merge.py` | Ch. III, V |
| 5 | You reviewed 100 by hand | A stratified sample, compared with the judge | `manual_review_sheet.py` | Ch. V |
| 6 | Zalo messages were narration, some had placeholders | Rebuilt from 60 preserved scenarios, offline | `zalo_codex_recovery.py`, `zalo_direct_*.py` | Ch. IV, V |
| 7 | Clean dataset of 2,097 messages | Dedup, whole-scenario split 1,658 / 219 / 220 | `core/text.py`, `core/splits.py`, `repair_corpus_split_governance.py` | Ch. III |
| 8 | Chose the Qwen model, measured memory | Weighted score of recall, quality, memory, speed | `model_adaptation/catalog.py`, `pilot.py` | Ch. III |
| 9 | LoRA versus QLoRA smoke test | Short runs that record memory and step time | `phase40_modes.py`, training configs | Ch. IV, V |
| 10 | Trained Qwen QLoRA, then PhoBERT | Two training recipes, same data, same seed | `training.py`, `phobert_training.py` | Ch. IV |
| 11 | Compared stock, QLoRA, PhoBERT | Validation to pick checkpoints, one final test | `phase40_metrics.py`, `modeling/evaluation.py` | Ch. V |
| 12 | Exported Qwen to a file the laptop can run | Merge, convert to GGUF, quantize to Q8_0 | `model_adaptation/convert.py`, `phase40_gguf.py` | Ch. IV |
| 13 | The app | Model answer plus hand-written safety rules | `runtime/service.py`, `analyzers/local_model.py` | Ch. IV |

Note on the order of your memory: "stock model versus QLoRA versus PhoBERT" happened
on two occasions. During training, 219 validation messages picked each model's best
checkpoint. Afterwards, both finished models were run once on the 220 messages that
had been set aside. The older stock-versus-QLoRA number (0.6702 to 0.9625) is from an
earlier 254-message set, not from the final 220. Keep those apart when you speak.

---

## Day 1: what a row is, and where the seeds come from

**Goal:** know the one data shape that everything else depends on, and explain how
the seed messages were collected.

**Read (in this order):**

- `SeedRecord` — `src/data_pipeline/core/records.py:71`. A seed has `text`,
  `source_url`, `scrape_timestamp`, and an optional label hint.
- `DatasetRecord` — `src/data_pipeline/core/records.py:175`. Seven fields: `text`,
  `label`, `risk_tier`, `suspicious_spans`, `xai_explanation`, `source`, `seed_id`.
  It rejects unknown fields, unknown labels, blank text, and any suspicious span
  that is not copied word for word from the text.
- `NCSCScraper` — `src/data_pipeline/scraper/ncsc_scraper.py:14`. Despite the name,
  its list of sites includes `tinnhiemmang.vn`, `chongluadao.vn` and `scam.vn`.
- `extract_advisory_links` — `src/data_pipeline/scraper/extractors.py:109`, and
  `extract_phishing_payloads` — `src/data_pipeline/scraper/extractors.py:175`.
  The first finds article links, the second pulls the scam message out of a page.
- `collect_source` — `src/data_pipeline/scraper/real_sources.py:326`. The stricter
  second route: it refuses a source unless collecting and reusing it is allowed,
  and `redact_victim_pii` — `src/data_pipeline/scraper/real_sources.py:113` removes
  personal details.

**Look at real data.** Open `data/raw/seeds-2026-04-24.jsonl` in your editor. It has
300 seeds, all from `tinnhiemmang.vn`, none with a label hint, median length about
270 characters. Read five of them. Notice that a seed is one real warning, not a
finished training example.

**Exercise:** `python documents/defense/study_exercises.py 1`. You will see a good
row accepted, then two bad rows refused.

**Say it aloud:** "A seed is a real public warning with its source. It has no label.
Every row the model trains on is a seven-field record, and the code refuses any row
whose highlighted phrases are not actually in the message. That check is structural.
It does not tell me whether the message is realistic or correctly labeled. That is
the judge's job, later."

**Self-test:**

1. What are the seven fields? Which one is the class the model must predict?
2. Why must a suspicious span be an exact substring of the text?
3. Why does a seed carry no label?
4. Two scraping routes exist in the code. Which one made your 300 seeds, and how
   would you find out? (The file only tells you the host. Be ready to say which
   you ran.)

---

## Day 2: generation, rate limits, and the overwrite trap

**Goal:** explain how one seed becomes many labeled messages, and how a crash in
the middle is survived.

**Read:**

- `build_complex_prompt` — `src/data_pipeline/generation/prompts.py:53`,
  `build_bulk_prompt` — `src/data_pipeline/generation/prompts.py:86`,
  `build_benign_prompt` — `src/data_pipeline/generation/prompts.py:160`. Skim the
  text of the prompts. This is where you told the model what a bank-impersonation or
  task-scam message looks like, and where the "different kinds of task scam" list
  lives (`_build_task_scam_diversity_block` — `src/data_pipeline/generation/prompts.py:33`).
- `TieredGenerator` — `src/data_pipeline/generation/generator.py:123`. "Tiered"
  means two kinds of request: a few high-quality ones ("complex", 3 messages per
  request, sent to Claude) and many cheaper ones ("bulk", 5 per request, sent to
  another provider if configured).
- `generate_dataset` — `src/data_pipeline/generation/generator.py:211`. Works out how
  many messages each of the four classes needs, then runs batches.
- `_build_batch_specs` — `src/data_pipeline/generation/generator.py:545`. Plans the
  batches: about 20 percent of each class as "complex", the rest as "bulk", and
  picks seeds round-robin.
- `_finalize_records` — `src/data_pipeline/generation/generator.py:491`. For every
  message the model returns: fix the label and risk-tier spelling, add the source,
  add a `seed_id`, and validate with `DatasetRecord`.
- `_derive_seed_id` — `src/data_pipeline/generation/generator.py:511`. The `seed_id`
  is a hash of the source URL plus the seed text. Every variant of one seed shares
  it. This is what later keeps variants together in one split.
- `_call_claude` — `src/data_pipeline/generation/generator.py:368`. One request, no
  retry. If the provider says "rate limit", it raises and the run stops.
- `_persist_completed_batch` — `src/data_pipeline/generation/generator.py:703`,
  `_save_batch_checkpoint` — `src/data_pipeline/generation/generator.py:756` and
  `_prepare_resume_state` — `src/data_pipeline/generation/generator.py:515`.

**This is your "rate limit, then overwritten data, then fix" story in code.** After
every finished batch, the generator appends the records to a partial file and writes
a checkpoint (it keeps the last five). If the run dies, starting again *with*
resume reads the checkpoints and continues. Starting again *without* resume does
the opposite: it deletes the checkpoint files and the partial output, and starts
from nothing. That is the trap. Look at `_prepare_resume_state`, the branch
`if not resume`. Two leftover files from the real run are in
`data/synthetic/` (`.checkpoint.jsonl` and `.checkpoint(1).jsonl`).

**Say it aloud:** "The generator plans batches per class, calls a model for each,
and checks every message against the schema. It saves after every batch. When the
provider rate-limited us the run stopped, and a rerun without resume would have
wiped the partial data, which is what happened once. The fix was to resume from the
checkpoints."

**Self-test:**

1. What does `seed_id` mean and why do all variants of a seed share one?
2. What is the difference between a complex batch and a bulk batch?
3. What happens on a rate-limit error? What happens if you rerun without resume?
4. Why is the message's `source` field a fixed list of values?

**Know this weakness before a juror finds it:** the same seed can be reused for
different classes, but the `seed_id` does not include the class. The splitter
refuses a seed that has two labels. So a fresh provider run is not guaranteed to
produce a publishable dataset. Do not offer the provider workflow as a clean rebuild.
Do not "fix" it by adding the class name to the id: that hides the problem without
creating independent scenarios.

---

## Day 3: the judge, the human review, and the repairs

**Goal:** tell the quality-control story with numbers, without pretending you can
recite 3,000-line files. Most of this code is one-off repair tooling. The story
matters more than the functions.

**Read only these:**

- `JudgeVerdict` — `src/data_pipeline/generation/quality_judge.py:42`. Five scores
  from 1 to 5: realism, label correctness, code-switch naturalness, risk-tier
  correctness, suspicious-span accuracy.
- `QualityJudge.judge_record` — `src/data_pipeline/generation/quality_judge.py:89`.
  A message passes only if all five scores are at least 3.
- `QualityJudge._select_judge_model` — `src/data_pipeline/generation/quality_judge.py:170`.
  The judge is chosen to be a different model from the one that wrote the message.
- `select_stratified_sample` — `src/data_pipeline/manual_review_sheet.py:89` and
  `write_review_sheet` — `src/data_pipeline/manual_review_sheet.py:175`. Builds the
  sheet you filled in by hand, mixing messages the judge passed and failed.
- `validate_direct_message` — `src/data_pipeline/generation/zalo_codex_recovery.py:128`.
  The check that refuses "third-person story" text and leftover `[ ]`, `{ }`, `< >`.
- `enforce_seed_cap` — `src/data_pipeline/repair_corpus_split_governance.py:226` and
  `assign_stratified_group_split` — `src/data_pipeline/repair_corpus_split_governance.py:318`.

**Skim, do not study:** `judge_merge.py` (about 3,900 lines), `apply_mislabel_triage.py`
(about 2,100 lines), `manual_review_sheet.py` beyond the two functions above,
`zalo_direct_messages_*.py`, `reconstruct_zalo_direct_catalog.py`. They are preserved
evidence of one-off repairs. Their names contain "codex" because a Codex model did
the judging and the rewriting. In the report they are simply "a judge model". Their
paths are recorded in tests and manifests, so do not rename or delete them.

**The story, with numbers to know cold:**

- The judge scored all 2,097 messages: 1,395 passed, 66.52 percent.
- You reviewed 100 messages by hand, chosen evenly across the four classes and across
  judge pass and fail. You passed 44 of them. You and the judge agreed on 87 of the
  100. The 44 is a fact about that sample, not a failure rate for the whole corpus.
- A review of 324 messages with doubtful labels found 233 that needed a different
  label. Only 57 corrections were applied, because the other 176 all came from one
  source article, and counting them would have made a class look more varied than it
  is.
- 240 Zalo messages were written as narration ("a scammer contacts the victim...")
  instead of as real chat messages. They were rebuilt, offline with no API call, from
  60 preserved scenarios. The first repair only stripped quotation marks and turned out
  not to be enough, so it was replaced.
- Other classes carried leftover template text. The check that now refuses it
  (`validate_direct_message`, above) rejects bracket characters such as `[ ]`, `{ }`
  and `< >`.

**Where the evidence lives:** `data/models/phase40/review/human-review-report.md`.

**Say it aloud:** "A structural check cannot tell a realistic message from a fake
one, so a judge model scored every message and I checked 100 by hand. The judge and I
agreed on 87. My review also found a real defect: one class was written as narration
rather than chat, so we rebuilt it from 60 scenarios rather than shipping it."

**Self-test:**

1. Why score with a judge at all, if the schema already validates rows?
2. Why was the human sample drawn across judge passes and fails?
3. 44 out of 100 passed. Does that mean 44 percent of the dataset is good?
   (No. Say why.)
4. Why were only 57 of 233 label corrections applied?

---

## Day 4: cleaning and splitting

**Goal:** explain, with a working example, why the split cannot leak.

**Read:**

- `normalize_text` — `src/data_pipeline/core/text.py:32`. Repairs broken characters
  (mojibake), normalizes Vietnamese accents to one standard form, collapses spaces.
- `lexical_dedup` — `src/data_pipeline/core/text.py:40`. Keeps the first of any
  cluster of messages that are 95 percent or more alike.
- `split_dataset` — `src/data_pipeline/core/splits.py:154`. Groups rows by label and
  then by `seed_id`. It refuses a `seed_id` that has two labels. It refuses a label
  with fewer scenarios than splits. It orders whole scenarios by a salted SHA-256
  hash and cuts them 80 / 10 / 10 by *scenario count*, not row count. That is why
  your split is 1,658 / 219 / 220 and not exactly 80 / 10 / 10.
- `split_and_dedup` — `src/data_pipeline/processing/splitter.py:28`. After the
  split, checks validation against train and the final set against both, and removes
  messages that are too similar across splits.
- `build_manifest` — `src/data_pipeline/core/splits.py:327`,
  `verify_manifest` — `src/data_pipeline/core/splits.py:361` and
  `publish_reviewed_dataset` — `src/data_pipeline/publication.py:83`. Write the files
  with SHA-256 hashes, then switch the "current" pointer in one step.

**The reason for all of it:** two messages from one article can differ by only a bank
name or an amount. If one is in training and its twin is in the test set, the model
"passes" by remembering, and the score means nothing. Keeping a whole scenario in one
split prevents that.

**Exercises:** `python documents/defense/study_exercises.py 2 3`. In exercise 3 you
will see 20 scenarios split into train, val and test, confirm no scenario appears in
two splits, and then watch the code refuse a scenario that carries two labels.

**Final numbers:**

| Class | Train | Validation | Final test | Total |
| --- | ---: | ---: | ---: | ---: |
| Bank impersonation | 595 | 76 | 70 | 741 |
| Benign | 517 | 72 | 66 | 655 |
| Task scam | 306 | 49 | 49 | 404 |
| Zalo social engineering | 240 | 22 | 35 | 297 |
| **Total** | **1,658** | **219** | **220** | **2,097** |

The biggest single scenario holds 167 rows, 7.96 percent of the corpus, under the 8
percent cap (`enforce_seed_cap`).

**Say it aloud:** "I cut the data by scenario, not by message. All variants of one
scenario go to the same split, so the model is never tested on a near-copy of
something it trained on. The code refuses a scenario with two labels and a class
with too few scenarios."

**Self-test:**

1. Why is the test set 220 and not exactly 10 percent of 2,097?
2. What would go wrong if you split by message?
3. What does `lexical_dedup` do at 0.95?
4. Which two checks does `split_dataset` fail on?

---

## Day 5: choosing the model and training it

**Goal:** explain the two training recipes side by side, and how the model was chosen.

**Choosing the model.**

- `build_default_catalog` — `src/model_adaptation/catalog.py:8`. Three candidates:
  `Qwen3.5-4B`, `Qwen3-4B-Instruct-2507` and `Qwen2.5-7B-Instruct`.
- `_effective_score` — `src/model_adaptation/pilot.py:23`. The score is 45 percent
  recall on risky messages, 30 percent quality, 15 percent memory fit and 10 percent
  speed, minus a hardware penalty. Recall comes first on purpose: missing a scam is
  worse than a false alarm.
- `select_baseline_and_runner_up` — `src/model_adaptation/pilot.py:66`. The
  laptop winner has to be one of the 4B models. The winner was
  `qwen3-4b-instruct-2507`. In your report the three models were tried on the same 33
  example messages, caught risky messages at the same rate, and were separated by
  memory and time.

**LoRA versus QLoRA smoke test.** LoRA adds small trainable "adapter" layers to a
frozen model. QLoRA does the same but stores the frozen model in 4-bit numbers
(NF4), so it needs far less memory. On the RTX 5050 with 8,151 MiB:

- ordinary LoRA peaked at 7,902 MiB, left only 9 MiB free, and pointed to roughly
  18 hours. It did not run out of memory. It was impractical. Never say "OOM".
- QLoRA peaked at 7,516 MiB at a median of 3.46 seconds per step.

The two runs used matching settings apart from the quantization
(`data/models/phase40/matched-qwen-config.json`, `comparison.admissible: true`).

**How the training data is shaped (Qwen).**

- `format_training_prompt` — `src/model_adaptation/prompts.py:11` builds the prompt:
  the message plus the JSON shape wanted back.
- `build_training_examples` — `src/model_adaptation/data.py:26` pairs each prompt with
  the correct answer: a JSON text with `label`, `risk_tier`, `suspicious_spans` and
  `xai_explanation`.
- `tokenize_phase40_response_only` — `src/model_adaptation/training.py:613`. The
  prompt tokens are set to `-100`, which means "ignore in the loss". The model is only
  graded on the answer it writes. So Qwen learns to *write* the label as text. It has
  no four-way output layer.

**PhoBERT (the other recipe).**

- `PHOBERT_LABEL_TO_ID` — `src/model_adaptation/phobert_training.py:95`. The four
  labels become 0 to 3 in a fixed order: bank_impersonation, zalo_social_engineering,
  task_scam, benign.
- `segment_for_phobert` — `src/model_adaptation/phobert_training.py:767`. PhoBERT was
  trained on Vietnamese with words already separated, so each message goes through
  `underthesea` word segmentation first, then the tokenizer, cut at 256 tokens.
- The model is a standard sequence classifier: four numbers out, the biggest wins.
  Every weight is trained. It is not LoRA, not QLoRA, and there is no GGUF for it.

**Exercise:** `python documents/defense/study_exercises.py 5`. It prints the real
settings side by side from the saved config files. Learn this table:

| | Qwen QLoRA | PhoBERT |
| --- | --- | --- |
| Model | Qwen3-4B-Instruct-2507 | vinai/phobert-base-v2 |
| What is trained | LoRA adapters (rank 16, alpha 32, dropout 0.05) on a 4-bit base | Every weight plus a 4-way head |
| Learning rate | 0.0002 | 0.00002 |
| Batch | 1 x 4 accumulation = 4 | 16 |
| Epochs and steps | 3 epochs, 1,245 steps | 3 epochs, 312 steps |
| Longest input | 1,024 tokens | 256 tokens |
| Seed | 42 | 42 |
| Checkpoint every | 50 steps | 50 steps |
| Best checkpoint chosen | step 200 | step 100 |

**Proof it was really QLoRA.** A flag alone proves nothing. `prove_qwen_mode` —
`src/model_adaptation/phase40_modes.py:306` counts the layers that are really 4-bit
(252), checks that only adapter tensors are trainable (504) and that the base is
frozen. The counts are stored with the run.

**Big files: what to read.** `training.py` is 5,279 lines and `phobert_training.py`
is 3,209, and most of both is verification and record-keeping. In `training.py` read
only lines 522 to 730 (the masking and the collator). In `phobert_training.py` read
lines 95, 759 to 910. Skip the rest, and skip every `phase40_*` and `phase41_*` file.

**Say it aloud:** "I picked Qwen3-4B by measuring recall, quality, memory and speed on
a small test. Ordinary LoRA fit on my 8 GB laptop card only barely and would have
taken about 18 hours, so I used QLoRA, which stores the frozen model in 4 bits. Qwen
learns to write the JSON answer, including the label. PhoBERT is a different design:
a classifier with a four-way output. Both trained on the same messages with the same
seed."

**Self-test:**

1. Why is Qwen's label "text" while PhoBERT's is a number?
2. What does masking the prompt with -100 do?
3. Why was ordinary LoRA not chosen? What number would you quote? (Do not say OOM.)
4. Why does PhoBERT need word segmentation first?
5. Why can PhoBERT not write the explanation?

---

## Day 6: evaluation and the export

**Goal:** explain how the scores were made, why they can be trusted, and what they
cannot claim.

**Read:**

- `parse_qwen_prediction` — `src/model_adaptation/phase40_metrics.py:71`. Qwen's raw
  text must parse as JSON with a known label. Anything else counts as an *invalid
  output*. It is not quietly repaired. Both models had zero invalid outputs.
- `evaluate_phase40_predictions` — `src/model_adaptation/phase40_metrics.py:533`.
  Checks every prediction lines up with the right message in the right order, then
  computes precision, recall, F1 per class, macro and weighted F1, and the confusion
  matrix. It counts risky messages that were called benign.
- `select_phase40_checkpoint` — `src/model_adaptation/phase40_metrics.py:586`. Picks
  the best saved checkpoint: first it drops any with low risky-class recall or any
  invalid output, then ranks the rest by macro F1.
- PhoBERT's answer: the highest of four numbers, in the fixed label order
  (`build_phobert_prediction_rows` — `src/model_adaptation/phobert_training.py:853`).

**The two evaluations (say them separately):**

| | Validation (219 messages) | Final test (220 messages, run once) |
| --- | ---: | ---: |
| Qwen QLoRA macro F1 | 0.9885 (step 200) | 0.980493 |
| PhoBERT macro F1 | 0.9849 (step 100) | 0.990892 |

The validation set helped pick each model's checkpoint. The final 220 were locked
away at the split and used once, with no retraining or threshold change afterwards.
Each model called exactly one dangerous message safe. Both numbers come from one
training run with one seed, so the gap between 0.980 and 0.991 describes this
comparison. It is not proof that PhoBERT is better, and there is no significance
test or confidence interval. The stock-model comparison (0.6702 macro F1 without
training, 0.9625 after) is on the older 254-message set.

**Wording you must keep:** exactly one shared-cohort evaluation pass. Earlier
automated integrity tests had read and hashed the files without running a model or
showing a message to a person. Never say "untouched" or "zero prior access".

**The export.**

- `convert_to_gguf` — `src/model_adaptation/convert.py:347`. The best adapter is
  merged into the base model (`_materialize_merged_model` — `src/model_adaptation/convert.py:111`),
  converted to the GGUF format, and quantized to 8-bit (Q8_0).
- NF4 is how the model was stored during *training*. Q8_0 is how it is stored for
  *running*. Only Qwen has a GGUF.
- Before the app loads the file, `verify_artifact_identity` (`src/artifacts.py`)
  checks its SHA-256. The verified file is 4,280,403,232 bytes, SHA-256
  `457f6f92...ea4d18ab`.

**Report facts in code:** `load_reporting_authority` in `src/modeling/evidence.py`
verifies the frozen results. Never rerun the final evaluation to "check" a number.

**Say it aloud:** "I picked each model's best checkpoint on 219 validation messages.
Then I ran both finished models once on 220 messages that had been set aside from the
start, and did not change anything after seeing the result. PhoBERT scored a little
higher, 0.991 to 0.980. With one run of each I can't call that a real difference. Qwen
is the one that also writes the explanation, which is why the app ships Qwen."

**Self-test:**

1. Why two evaluations?
2. What is an "invalid output" and why is it not repaired?
3. What is macro F1 and why use it instead of accuracy? (Classes are unequal in size,
   and macro F1 gives each class the same weight.)
4. What can you not claim about 0.980 versus 0.991?
5. What is the difference between NF4 and Q8_0?

---

## Day 7: the app, then rehearse

**Goal:** trace one message through the app, and rehearse the defense.

**The path of one message:**

1. `handle_analyze` — `src/runtime/cli.py:96`, or the browser route
   `DemoApp._handle_analyze` — `src/runtime/demo.py:125`, hands the text on.
2. `RuntimeService.analyze_text` — `src/runtime/service.py:94`. Cleans the text,
   refuses empty or too-short input, refuses screenshots and audio (it is text only),
   and never stores the raw text.
3. `GGUFAnalyzer.analyze` — `src/runtime/analyzers/gguf.py:241`. Loads the Q8_0 file
   on the CPU, sends one prompt (`build_structured_analysis_prompt` —
   `src/runtime/analyzers/local_model.py:294`) at temperature 0, at most 250 new
   tokens, and pulls the JSON out of the reply (`extract_structured_payload` —
   `src/runtime/analyzers/local_model.py:330`).
4. `build_analysis_result` — `src/runtime/analyzers/local_model.py:787` and
   `_build_threat_decision` — `src/runtime/analyzers/local_model.py:711`. **Here the
   model's answer meets hand-written rules.**
5. The result is at most 3 quoted cues, 2 labels and 3 pieces of advice
   (`AnalysisResult` — `src/runtime/contracts.py:45`).

**The rules after the model (this matters in a defense).**

- `_apply_safety_floor` — `src/runtime/analyzers/local_model.py:623`. If the model
  says "benign" but the text has a credential or payment request, or a bank name
  with a link, the app raises the risk. It catches a scam the model missed.
- `_looks_like_legitimate_bank_otp_notice` — `src/runtime/analyzers/local_model.py:664`
  and `_downgrade_legitimate_otp_notice` — `src/runtime/analyzers/local_model.py:695`.
  If a message is a genuine bank OTP notice (bank name, OTP, "do not share", no link or
  urgency), the app lowers a "suspicious" to "benign".
- `_is_unsafe_recommendation` — `src/runtime/analyzers/local_model.py:575`. Advice
  that tells the user to click, install or call a number is dropped.
- `cue_span_is_grounded` — `src/runtime/analyzers/local_model.py:597`. A quoted cue
  must really appear in the message.

The 0.980 and 0.991 results are model-only. These rules exist only in the app.

**Exercise:** `python documents/defense/study_exercises.py 4`. It feeds fake model
answers through the rules, no model loaded. You will see rule A rescue a missed scam
and rule B fix a plain OTP notice. Then message C, the Input 3 message from your
report, stays "suspicious". The words "Internet Banking" count as a credential cue,
which blocks the OTP rule. That is the honest reason Input 3 is a false alarm, and
it is why the test `test_legitimate_bank_otp_notice_overrides_model_suspicion` fails.
If a juror asks "you wrote an OTP rule, why does Input 3 still fail?", that is the
answer. Do not fix it before the defense: the report describes it as a limitation,
and changing it would make the report wrong.

**Notes from comments that were removed.** These comments held real reasoning, so
here is what they said:

- `render.py`: model-written text can contain terminal control codes (colour codes,
  cursor moves, a bare carriage return). The renderer strips every control character
  before printing, so a crafted message cannot rewrite what appears on the screen.
- `demo.py`: the analysis route rejects a request whose `Content-Type` is present
  but is not JSON, and one whose `Origin` or `Referer` is a different site. Both
  close the trick where another web page makes your browser post to the local demo.
  A missing header is allowed so tests and `curl` still work. The server also only
  binds to `localhost` or a loopback address (`require_loopback_host` —
  `src/runtime/demo.py:196`).
- `cli.py`: the output is forced to UTF-8 because the default Windows code page
  cannot print Vietnamese.
- `repair_corpus_split_governance.py`: the salt that orders scenarios when trimming
  a group over the cap is separate from the salt that assigns splits, on purpose.

**Rehearse.** The two questions you must be able to answer are "What did you
contribute?" and "How does it work in the code?". A good answer names a file or
function, a mechanism, a piece of evidence, and a limitation. A metric alone is not
an answer. Your five-minute code walk, in order:

1. `DatasetRecord` — `src/data_pipeline/core/records.py:175`: what a row is.
2. `_finalize_records` — `src/data_pipeline/generation/generator.py:491`: how a row is
   made and given a `seed_id`.
3. `split_dataset` — `src/data_pipeline/core/splits.py:154`: why the split cannot leak.
4. `tokenize_phase40_response_only` — `src/model_adaptation/training.py:613` and
   `PHOBERT_LABEL_TO_ID` — `src/model_adaptation/phobert_training.py:95`: how each
   model learns the label.
5. `evaluate_phase40_predictions` — `src/model_adaptation/phase40_metrics.py:533`: how
   the score is made.
6. `analyze_text` — `src/runtime/service.py:94`, then `_build_threat_decision` —
   `src/runtime/analyzers/local_model.py:711`: one message, end to end.

Then open `DEFENSE_QA_WORKSHEET.md` and answer its questions out loud. Do not read
the model answers first.

---

## Numbers to know cold

| Fact | Value |
| --- | --- |
| Seeds | 300, all from tinnhiemmang.vn, no label hint |
| Final corpus | 2,097 messages: 741 bank impersonation, 655 benign, 404 task scam, 297 Zalo |
| Split | 1,658 train, 219 validation, 220 final test |
| Judge | 1,395 of 2,097 passed (66.52 percent) |
| Human review | 100 messages, 44 passed, agreed with the judge on 87 |
| Label review | 324 checked, 233 needed a change, 57 applied, 176 held back (one source article) |
| Zalo rebuild | 240 rows rebuilt from 60 scenarios, offline |
| Biggest scenario | 167 rows, 7.96 percent (cap 8 percent) |
| Base model chosen from | 3 Qwen candidates, 33 example messages |
| LoRA on 8 GB card | peak 7,902 of 8,151 MiB, 9 MiB free, about 18 hours, no OOM |
| QLoRA | peak 7,516 MiB, median 3.46 s per step |
| Qwen training | 1,245 steps, best checkpoint step 200 |
| PhoBERT training | 312 steps, best checkpoint step 100 |
| Both | seed 42, 3 epochs |
| Validation macro F1 | Qwen 0.9885, PhoBERT 0.9849 |
| Final macro F1 | Qwen 0.980493, PhoBERT 0.990892 |
| Dangerous mistakes (risky called safe) | 1 each |
| Invalid outputs | 0 each |
| Stock vs QLoRA (older 254-message set) | macro F1 0.6702 to 0.9625 |
| Exported model | Q8_0 GGUF, 4,280,403,232 bytes |

## Known problems: say them before a juror does

1. **The provider generator is not a guaranteed rebuild** (Day 2): a seed can be
   reused across classes while the `seed_id` ignores the class.
2. **Input 3 is a false alarm and the OTP rule cannot fix it** (Day 7).
3. **`doctor` and `analyze` say NOT READY** because the release check reads an old
   pilot result marked BLOCK. The browser demo does not use that check.
4. **Two Windows environment variables point at the old D: layout.** They are why the
   app broke. `START_DEMO.bat` works around them. If you want them gone for good,
   after the defense, remove `MODEL_ARTIFACT_ROOT` and `MODEL_REGISTRY_PATH` from
   your user environment variables and set the three variables in `START_DEMO.bat`
   instead. Removing them will also break any command that still expects the D: model
   folder.
5. **Four tests fail, and failed before this week's changes.** Two are real: the
   OTP rule test above, and `test_recommendation_sanitizer_blocks_unsafe_actions`
   (the advice wording changed from "hoac" to "va khong"). Two are the test guard
   failing to load an unrelated library. Five data-pipeline test files cannot even be
   collected under the guard for the same reason.
6. **The architecture review still lists six critical and three warning findings.**
   Do not call the code secure or production-ready.
7. **One run, one seed.** No significance test, no confidence interval, no "stable
   winner".
8. **Names mislead.** `ncsc_scraper.py` scrapes `tinnhiemmang.vn` and other sites, not
   only the NCSC portal. Files named `codex` are preserved repair evidence, not a
   dependency of the app.

## Files you can safely ignore

- `src/model_adaptation/phase40_*.py`, `phase41_*.py`: sealed evidence and launch
  plumbing, about 45,000 lines between them.
- `src/source_archiving/`, `historical/`, `data/models/phase4*/`: archives.
- `src/data_pipeline/judge_merge.py`, `apply_mislabel_triage.py`,
  `reconstruct_zalo_direct_catalog.py`, `migrations.py`: one-off repairs.
- `.planning/`: project history, not authority.
