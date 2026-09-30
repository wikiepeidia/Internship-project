# Code Checklist — one sitting, read-only

10 files. Matches the slide talk order exactly. Read each file's one anchor
function/class, not the whole file. Do not run anything — reading only.

## Skip these directories entirely

- `src/model_adaptation/` — 35 files, almost all one-off phase-40 scripts
  (release gates, GGUF export, notebooks, catalogs...). You only need 3 files
  from here, listed below by name. Everything else in that folder: skip.
- `src/data_pipeline/` top-level loose scripts (`apply_*.py`, `repair_*.py`,
  `recovery.py`, `reconstruct_zalo_direct_catalog.py`, `manual_review_sheet.py`,
  `migrations.py`) — one-off fixers, not the pipeline.
- `src/data_pipeline/generation/zalo_*.py` and `gemini_auth.py` — the one-off
  Zalo rebuild, not the main generation path.
- `src/modeling/training.py`, `inference.py`, `legacy_adapters.py` — thin
  pass-through shims (a few lines each) that just forward to the real code
  below. Know they exist, don't study them.

## Hard rules

- Never open `data/splits/test.jsonl` or list `data/splits/`.
- Never run a training script, `phase41_evaluation.py`, or anything that
  loads a model. Reading source is fine; executing is not.

## The 10 files, in slide order

**II/III — Seed crawl**
`src/data_pipeline/scraper/ncsc_scraper.py` → class `NCSCScraper`.
Hits tinnhiemmang.vn, writes one `SeedRecord` per article.

**IV — Data generation**
`src/data_pipeline/generation/generator.py` → class `TieredGenerator`.
Takes a seed, calls the LLM per class, returns labeled messages.
`src/data_pipeline/generation/prompts.py` → `THREAT_CLASSES` list + the
prompt template — this is "one fixed prompt, seed dropped in."
`src/data_pipeline/generation/quality_judge.py` → class `QualityJudge`.
The automatic judge pass (1,395/2,097 PASS).

**V — Splitting**
`src/data_pipeline/core/splits.py` → function `assign_seed_split`.
This is the real logic — a seed and everything it generated go to one split.
(`processing/splitter.py` is just a one-line facade over this file.)

**VI — Model/training choice (LoRA vs QLoRA)**
`src/model_adaptation/phase40_local_experiment.py` → the 33-message /
GPU-telemetry screening run. Big file, fail-closed by design — just know it's
here and why (the table on slide VI came from this).

**VII — Training Qwen (QLoRA)**
`src/model_adaptation/phase40_qlora_session.py`.
This, not `src/modeling/training.py`, is what actually produced the frozen
Qwen numbers.

**VIII — Training PhoBERT**
`src/model_adaptation/phobert_training.py`.
Same relationship: this is the real trainer, `src/modeling/training.py` just
forwards to it.

**IX/X — Evaluation**
`src/modeling/evidence.py` — read-only loader/validator for the frozen export
(this is what the frozen numbers table comes from).
`src/model_adaptation/phase41_evaluation.py` — the one-shot 220-message
terminal run. **Do not execute.** Just know `run_phase41_once` is the entry
point and that it's fail-closed by design (won't run twice, won't touch the
file if anything looks off).

**XI — Demo Result / runtime app**
`src/runtime/service.py` → class `RuntimeService`, method `analyze_text` —
this is what the demo notebook and the browser demo both call.
`src/runtime/cli.py` → function `handle_analyze` — what `vnphish analyze`
calls (does one more readiness check than `analyze_text` alone).
`src/runtime/analyzers/local_model.py` → function `_apply_safety_floor` —
the rule that can override the model (this is the Input-3 false-alarm logic
on the backup slide).

## If asked "show me the function"

Every anchor above is a real, current symbol — `grep -n "def analyze_text"`
or open the file at that name. If GitNexus is indexed, `context({name: "..."})`
on any of these names gives callers/callees instantly.
