# Screenshot shopping list — what to capture, in order

Companion to `WRITING_GUARDRAILS_REPORT.md` §3 and §6b.

**Headline finding: you do not need to re-run training.** Six parallel audits of the
repo confirmed that real, captured training console output, real GPU attestation, real
per-step loss, and a 14.87-hour run receipt already exist on disk from the August runs.
A live re-run is also effectively impossible — the base weights live only on the
protected D: drive, `data/manifests/model-registry.json` is absent on this machine, and
PhoBERT has no training CLI at all. So: **screenshot the recorded evidence, don't
re-train.**

The jury said *less code*. Every item below replaces a code listing.

---

## Tier A — capture right now, nothing needs starting

Open the file / run the command, screenshot the window. Priority order.

### A1. Real training console output (loss ticking, tqdm bars) ★ highest value
Kills: *"you didn't train anything."*

```powershell
code "data\models\phase40\probes\rtx5050-qlora-session-20260825\qlora\child-stderr.sanitized.log"
```
Shows real progress bars: `Loading weights: 43%|####3 | 172/398 [00:02<00:03, 70.95it/s]`,
then `100%|##########| 45/45 [03:42<00:00, 3.70s/it]`, then the 219-row validation bar.

Companion (same folder, stdout — the numeric side):
```powershell
code "data\models\phase40\probes\rtx5050-qlora-session-20260825\qlora\child-stdout.sanitized.log"
```
Real HuggingFace trainer dicts: `loss 1.926 → 0.6283`, grad_norm, learning_rate,
`train_tokens_per_second ~271–343`.

> **CAPTION CONSTRAINT — do not get this wrong.** This is the **45-step resource probe**,
> not the accepted 1,245-step run. Caption it as *"console output from the QLoRA resource
> probe used to measure per-step cost on the laptop GPU before committing to the full run."*
> Calling it the full run is misrepresentation and a jury can catch it from the step count.

### A2. GPU telemetry recorded *under load* — the real nvidia-smi figure ★
Kills: *"you didn't have hardware / you never actually loaded that GPU."*

```powershell
code "data\models\phase40\probes\rtx5050-qlora-session-20260825\qlora\telemetry.jsonl"
```
126 timestamped samples over 262.9 s. **95 of 126 samples at ≥50% GPU utilisation.**
Peak row, verbatim:
```json
{"device_vram_free_mib": 1011, "device_vram_total_mib": 8151, "device_vram_used_mib": 6900,
 "gpu_performance_state": "P4", "gpu_power_w": 86.67, "gpu_temperature_c": 84,
 "gpu_utilization_percent": 97, "nvidia_raw": "8151, 6900, 1011, 97, 84, 86.67, P4"}
```
Run-wide peaks: **97% utilisation, 90.36 W, 86 °C, 7,516 of 8,151 MiB VRAM (395 MiB free).**

`nvidia_raw` is literal `nvidia-smi` stdout — the harness shells out to
`nvidia-smi --query-gpu=memory.total,memory.used,memory.free,utilization.gpu,temperature.gpu,power.draw,pstate`
(`src/model_adaptation/phase40_local_experiment.py:3152`). This is **strictly stronger than a
Task Manager screenshot**: it is a time series, not a moment, and it carries the raw tool output.

Second, independent trace (29.7 minutes, 840 samples, 100% utilisation, 7,902 MiB used) —
this is where the 7,902/8,151 MiB figure already in your report comes from:
```powershell
code "data\models\phase40\probes\rtx5050-local-decision\lora-retry-1\telemetry.jsonl"
```

> **CAPTION:** *"GPU telemetry sampled during the 45-step QLoRA resource probe,
> 2026-08-25 00:54–00:59 UTC."* Give the run identity every time — see the caption rule at
> the bottom of this file.

### A2b. Pre-flight hardware attestation (supporting shot, NOT a load figure)
```powershell
code "data\models\phase40\probes\rtx5050-qlora-session-20260825\environment-preflight.json"
```
`cuda_device_name: NVIDIA GeForce RTX 5050 Laptop GPU`, `compiled_with_cuda: true`,
`linear4bit_available: true`, `cuda_compute_capability [12, 0]`, bitsandbytes present.

> **CORRECTION — an earlier version of this file was wrong about this artifact.** This is an
> **idle pre-flight snapshot**: `gpu_utilization_percent: 0`, `device_vram_used_mib: 94`,
> `gpu_power_w: 13.11`, `captured_utc 2026-08-25T00:54:12Z` — **33 seconds before** the first
> telemetry sample at `00:54:45Z`. It proves the hardware and the bitsandbytes CUDA kernel
> were present *before* the run. It does **not** show the GPU under load. Never caption it as
> a training-load figure. Use A2 for that.

### A3. Full-run receipt — 14.87 hours, real UTC start/end, peak VRAM
Kills: *"this was a toy run."*

```powershell
python -c "import json;e=[json.loads(l) for l in open('data/models/phase40/full/qwen-qlora/events.jsonl',encoding='utf-8')];print('start',e[0]['timestamp_utc']);print('end  ',e[-1]['timestamp_utc']);print('events',len(e))"
```
`start 2026-08-25T03:22:03Z → end 2026-08-25T18:14:04Z`, 1,450 logged events.
An overnight run with real clock bookends. Unglamorous = credible.

### A4. Per-step training table from the accepted run
```powershell
code "data\models\phase40\full\qwen-qlora\trainer_state.json"
```
`global_step 1245`, `epoch 3.0`, 151 log entries, step 1 loss `1.9258`,
`train_loss 0.30299`, `train_runtime 53518.68` s, `num_input_tokens_seen 1562313`.
Screenshot the top of `log_history` — the descending loss column is the point.

### A5. Loss curves (already rendered PNGs — just insert them)
```
data\models\phase40\full\qwen-qlora\curves\loss-curves.png
data\models\phase40\full\phobert\curves\loss-curves.png
```
Train loss 1.93 → ~0.13, validation flattening ~0.33. **Keep the visible train/val gap**
and say what it is in one sentence. Do not smooth or re-render — re-rendering overwrites
the frozen bundle.

### A6. Model files on disk with real sizes and timestamps
Kills: *"you downloaded this from GitHub."*

```powershell
Get-ChildItem "data\models\phase40\full\phobert\adapter-or-model","data\models\phase40\full\qwen-qlora\adapter-or-model" |
  Sort-Object Length -Descending | Format-Table Name,Length,LastWriteTime -AutoSize
```
PhoBERT `model.safetensors` 540,029,536 B and `optimizer.pt` 1,080,179,339 B;
Qwen `adapter_model.safetensors` 132,187,888 B. All stamped 26 Aug 2026.

Optional one-liner beneath it (very strong, one line):
```powershell
Get-ChildItem -Recurse -File "data\models\phase40\full" | Measure-Object -Sum Length | Select-Object Count,Sum
```
→ 101 files, 1,780,070,336 bytes (1.66 GiB) of locally produced artifacts.

### A7. Frozen evaluation results — both models, per class
```powershell
code "data\models\phase41\verified-export\9ac54d58c273ab0a8c2f2b4b61e472a51ca94231a94b6847637ecad6ceee49f7\results.md"
```
Qwen macro-F1 `0.980493`, PhoBERT `0.990892`, per-class P/R/F1, confusion matrices,
invalid-output column all zeros.

> Crop the folder name out of the shot, or screenshot the rendered content only — that
> long hex directory name is exactly the kind of noise you decided to cut.

### A8. Checkpoint selection sweep (proves real model selection, not a lucky number)
```powershell
python -c "import json,glob,re;o=sorted((int(re.search(r'step-(\d+)-',p).group(1)),json.load(open(p,encoding='utf-8'))['macro_f1']) for p in glob.glob('data/models/phase40/full/qwen-qlora/checkpoints/*/validation-metrics.json'));[print('step %-5d macro_f1 %.6f'%(s,f)) for s,f in o]"
```
step 50 → 0.794701, step 100 → 0.961251, step 150 → **0.902879 (a dip)**, step 300 → 0.988515,
plateau ~0.981521 to step 1245. The non-monotonic dip is what makes it read as real. Keep it.

### A9. Your own handwritten review sheets ★ underrated
Kills: *"an AI made your dataset and nobody checked it."*

```powershell
code ".planning\phases\39-independent-quality-re-judge\FINALtriage.md"
code ".planning\phases\39-independent-quality-re-judge\39-manual-review-sheet.md"
```
100 numbered PASS/FAIL verdicts in your own words, plus checkbox lines you edited by hand
(`[ok ] PASS` — the stray space is visible proof a human typed it). This is the single best
answer to the synthetic-data objection, and it is *yours*, so you can defend it live.

### A10. Real corpus rows on screen
```powershell
Get-Content -Path data\raw\seeds-2026-04-24.jsonl -TotalCount 2 -Encoding utf8 |
  ForEach-Object { $_ | ConvertFrom-Json | ConvertTo-Json -Depth 3 }
```
Real Vietnamese advisory text with `source_url: https://tinnhiemmang.vn/...` and
`scrape_timestamp: 2026-04-24T02:19:25Z`. **This is your tinnhiemmang.vn figure** — the
seed provenance, not a live crawl (live crawling is forbidden by their robots/terms, and
your own source audit says so).

If you want a *training row* instead, open the exact file path only —
`Get-Content data\splits\train.jsonl -TotalCount 3`. **Never run `ls data\splits`** and
never touch `test.jsonl`; the held-out split is sealed.

### A11. The 23-endpoint source audit table
Kills: *"you didn't even look for real data."*
```powershell
code ".planning\quick\260806-ubr-audit-and-acquire-crawlable-real-vietnam\260806-ubr-SOURCE-AUDIT.md"
```
Screenshot the "Endpoint evidence" table: 74 advisories, 125,608 blacklist indicators,
13,412 SCAM.VN reports — and the eligible column reading 0, with the legal reason.
This turns "we used synthetic data" from a weakness into a documented decision.

### A12. Judge summary — corpus quality, in plain numbers
```powershell
Get-Content data\processed\judge-summary.json -TotalCount 40
```
`total 2097`, `passed 1395`, `pass_rate 0.6652`, the five average rubric scores, per-split
rates, and `external_api_call_count 0`.

---

## Things you must never say

**"The demo is a side product of the Jupyter notebook."** It is false and git refutes it in
thirty seconds: `src/runtime/` first commit **2026-05-11**, `notebooks/` first commit
**2026-05-25**. The only three tracked notebooks are Colab *training* notebooks and contain
**zero** references to the demo, the runtime CLI, `DemoApp`, or wsgi. The runtime is 2,580
lines across 13 modules with 3,149 lines of dedicated tests, and `vnphish` is a real console
entry point declared in `pyproject.toml:55`. Saying this converts a real contribution into an
apparent lie in front of a jury that already suspects one.

If you want to cut the browser screenshot, the honest reason is: *the model-backed path cannot
run on this machine because the model registry is absent.* That reason survives a follow-up.

**"I chose not to re-run the training."** You couldn't. Say instead: *"the base weights are on
an external drive and the accepted run takes fifteen hours — here is the receipt from the run
I did."* Claiming a decision where there was an impossibility layers a second problem onto the
first, and a juror can expose it by saying "then re-run it for me now."

**"Less code" does not mean "fewer images."** There is no recorded jury objection to figures.
The passed report replaced code *with* images. Reading the instruction the other way points
exactly the wrong direction.

---

## Prose fix needed before any figure decision

`documents/reports/latex/chapters/04_implementation.tex:119` currently claims the service
"dispatches to a heuristic, GGUF, or accelerated-local analyzer, and returns a structured risk
tier, threat labels, grounded cues, and safety recommendations." No chapter discloses that the
GGUF and accelerated paths cannot resolve without `data/manifests/model-registry.json`, which
is absent — and the heuristic backend returns **no** threat labels and **no** recommendations.

Add one sentence: the runtime ships three analyzer backends; the GGUF and accelerated paths
resolve artifacts through a model registry not present on the demonstration machine, so the
demonstrated path is the rule-based backend.

That single sentence turns an unsupported claim into a documented limitation — and it is what
makes skipping the demo screenshot *honest* rather than evasive. Dropping the picture while
leaving the claim standing is the original F-grade defect applied to a new chapter.

---

## Tier B — I start something, you screenshot, you tell me to stop

Say the word and I run the command; you capture; I Ctrl+C.

### B1. The demo web UI answering a real Vietnamese phishing message ★
The single strongest "the product works" image.

I run:
```powershell
$env:RUNTIME_BACKEND="heuristic"; $env:RUNTIME_PROFILE="heuristic"
$env:MODEL_STORAGE_ROOT="data"; $env:MODEL_ARTIFACT_ROOT="data/models"
python -m src.runtime.cli demo --host 127.0.0.1 --port 8765
```
You paste a Vietnamese scam message, hit **Phân tích tại máy**, screenshot the verdict card.

> Caption honestly: this runs the **rule-based backend**. The fine-tuned model backend
> needs `data/manifests/model-registry.json`, which is not on this machine. Say
> "rule-based local runtime" and you are safe; say "the fine-tuned model" and you are not.

### B2. Task Manager beside the running demo — the reference report's Figure 11
With B1 still running, in a second window:
```powershell
Get-Process python | Select-Object Id,ProcessName,@{n='RAM_MB';e={[math]::Round($_.WorkingSet64/1MB,1)}},CPU,StartTime
```
Screenshot **together with** the browser window. A real PID, real RAM, real start time.
This is the exact shot the passed student used.

### B3. Browser DevTools Network tab during one analysis
Kills: *"it secretly calls the cloud."*
F12 → Network → clear → click analyse. Exactly one XHR:
`POST http://127.0.0.1:8765/api/analyze 200`, plus same-origin static files only.
No CDN, no `fonts.googleapis.com`. Screenshot the whole list.

### B4. The app refusing bad input (break it on purpose)
The reference report's Figure 9 trick — he screenshotted his own system blocking him.
Paste an image/OCR request → red error card, HTTP 400. Or paste `ok ban` → "too short".

### B5. The local-only network guard refusing a public bind — one command, nothing starts
```powershell
python -m src.runtime.cli demo --host 0.0.0.0 --port 8765 --no-browser
```
→ `error: argument --host: demo host must be localhost or an IPv4 loopback address`, exit 2.
Two seconds, no server. Great small figure for the security paragraph.

### B6. `doctor` fail-closed
```powershell
$env:RUNTIME_BACKEND="heuristic"; $env:RUNTIME_PROFILE="heuristic"; $env:MODEL_STORAGE_ROOT="data"; $env:MODEL_ARTIFACT_ROOT="data/models"; $env:MODEL_REGISTRY_PATH="data/manifests/model-registry.json"
function prompt { "PS> " }
Clear-Host
python -m src.runtime.cli doctor; "exit code: $LASTEXITCODE"
```
Verified: 11 checks PASS, exactly one FAIL (the release gate), `NOT READY backend=heuristic`,
exit code 1. **Report it as-is.** A tool that refuses to declare itself ready is a feature —
far more defensible than a doctored all-green screenshot.

> `MODEL_REGISTRY_PATH` is required. Without it settings fail to load entirely and you get
> `backend=unknown` with only 4 PASS — a figure whose headline is "the tool cannot load its
> own configuration". Set the env vars before `Clear-Host` so the long line stays out of frame.

### B7. ~~The trainer refusing a wrong data path~~ — SKIP

The command originally listed here omitted the required `--val-split` flag, so it would
produce an argparse complaint rather than the intended guard message. The model registry
is also absent on this machine, so it may fail on the registry before ever reaching the
path check. Not worth debugging for a figure — B5 and B6 already carry the fail-closed
story.

---

## Tier C — do NOT do these

| Idea | Why not |
|---|---|
| Re-run training (even a short probe) for a live console or Task Manager shot | **It cannot start.** `TrainingConfig.local_files_only = True` (`training.py:1378`) and `_resolve_base_model_path` (`:1825`) require an existing local weights directory with no download fallback. The only C: copy is an empty HF cache stub — a 40-byte `refs/main` file, no `blobs/`, no `snapshots/`. `--train-split` must also be byte-exactly the canonical corpus, so no toy file. **Use A1 + A2 instead.** |
| Live PhoBERT training screenshot | No CLI exists for it. Would require writing new code. |
| Re-render the loss-curve PNGs | Overwrites the frozen bundle the report already cites. |
| Any terminal-evaluation / test-split screenshot | Sealed one-shot evidence, `rerun_permitted: false`. Hard boundary. |
| Re-verifying the D: GGUF for the report | Already done and closed (see TODO §0). It is not report material. |
| `ls data\splits` | Enumerates the protected directory. Use exact file paths only. |
| A "live crawl of tinnhiemmang.vn" shot | Their robots/terms forbid it and your own audit records it as forbidden. A1/A10 shows the seed snapshot instead — that's the honest version. |

---

## Figure budget and captions

The passed report had **11 figures, 2 tables, 9 short snippets**. Target the same shape:

- **Must have (8):** A1, A2, A5 (×2 counts as one figure pair), A6, A7, A9, B1, B2.
- **Strong add (4):** A3 or A4 (pick one), A8, A11, B3.
- **Nice if space (3):** A10, A12, B5/B6.
- **Snippets: max 5–6, each under ~10 lines.** Prefer B5/B6/B7 output screenshots over listings.

Every important figure gets a caption **plus** a short italic *Description:* line saying
what the reader should notice — that is exactly what he did.

### The three-part caption rule — apply to every operational figure

Every figure gets: **(1) artifact path, (2) run identity — probe vs full, step count, UTC date,
(3) what it measures.** If you cannot state all three, cut the figure. This is the single rule
that makes recorded evidence safe; without it, a recorded figure is just an image with a story
attached, and this file already got one of them wrong once (see A2b).

Never place probe telemetry next to the results metrics without that caption. Adjacency is an
implicit claim: 45 steps over 4.4 minutes sitting beside numbers from 1,245 steps over 14.87
hours reads as the source of those numbers no matter what the prose says.

### Free credibility, costs one paragraph, no figure

Write the wall-clock decomposition into the prose:

> The 14.87-hour run consists of **1.36 hours of optimizer steps** plus **12.43 hours spread
> across 24 post-checkpoint validation passes.** Median inter-step wall gap 3.893 s against a
> median reported step duration of 3.847 s.

This pre-empts the sharpest arithmetic question a juror can ask ("15 hours for 1,245 steps?")
and it is the kind of thing only someone who sat through the run would volunteer.

**Caption rules:**
- No hashes anywhere — not in a caption, not in frame. Crop long hex directory names out of shots.
- Never plot or quote `peak_reserved_bytes` from the full run: 9,030,336,512 B (8.410 GiB)
  reserved on a card whose own hardware block reports 8,546,484,224 B (7.960 GiB). The likely
  explanation is Windows WDDM host-memory spill, but nothing in the repo confirms it. Use
  `peak_allocated_bytes` instead (4.995 → 5.731 GiB across the run) — it proves the same thing
  and contains no number you would have to defend.
- Say *"on an RTX 5050 Laptop GPU (8,151 MiB), per the run's own hardware record"* — not
  *"trained on this laptop."* Matching GPU name and VRAM proves the same GPU model, not the
  same physical machine.
- Never write "Phase 40" / "Phase 41". Write "the training run", "the held-out evaluation".
- Label the probe as a probe (A1).
- Label the demo backend as rule-based (B1).
- No "real scam cases" — the corpus is model-generated from real advisory seeds, judged and
  hand-reviewed. Say that in one sentence and it stops being an ambush.

---

## Suggested capture session (about 45 minutes)

1. Tier A, top to bottom — pure open-and-screenshot, no state to manage. (~20 min)
2. Tell me to start B1. Capture B1 → B2 → B3 → B4 in one sitting while it's up. (~15 min)
3. Tell me to stop it. Then B5, B6, B7 — each is one command that exits on its own. (~10 min)
4. Drop everything into `documents/reports/latex/figures/` with function-style names
   (`training_console.png`, `gpu_preflight.png`, `demo_verdict.png`, …) — **not** phase numbers.
