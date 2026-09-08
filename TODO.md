# TODO — figure set (final: 10)

Reasoning and alternatives: `documents/reports/latex/SCREENSHOT_LIST.md`.
All figures live in `documents\reports\latex\figures\`.

**No hashes anywhere** — not in a caption, not in a folder name in frame, not in terminal
scrollback.

---

## The 10

| # | File | Proves | Status |
|---|---|---|---|
| 1 | `training_console_probe.png` | I trained — real console, loss ticking | ✅ done |
| 2 | `gpu_telemetry_probe.png` | on my own GPU, 97% / 7,516 MiB | ✅ generated |
| 3 | `full_run_timeline.png` | for 14.87 h — and where they went | ✅ generated |
| 4 | `checkpoint_selection_sweep.png` | I selected the model properly | ✅ generated |
| 5 | `terminal_evaluation_confusion.png` | the results, and my mistakes | ✅ generated |
| 6 | `human_review_sheet.png` | a human checked the data | ✅ done, see note |
| 7 | `model_files_on_disk.png` | the artifacts exist — 5.64 GiB | ⚠️ **retake** |
| 8 | `gguf_conversion_receipt.png` | the deployable model loads | ⚠️ **retake** |
| 9 | `seed_data_sample.png` | the real public material I harvested | ✅ done |
| 10 | `corpus_sample.png` | what a governed corpus row looks like | ❌ **capture** |

Plus the two loss-curve PNGs already embedded in chapter 4 — leave them alone, they are
referenced at `04_implementation.tex:91` and `:106`. Report total: 12 figures, against the
11 in the reference thesis that passed. That is the right neighbourhood; do not add more.

---

## Still to do — three things

### 10. `corpus_sample.png` — NEW, the dataset row ★ capture this

**File `data\splits\train.jsonl`, line 222.** Ctrl+G → 222.

That row scored a perfect 5/5/5/5 from the independent judge and carries all seven fields
with three meaningful spans:

```
text        MB Bank thông báo: Smart OTP của bạn sắp hết hạn sau 24h. Để gia hạn
            miễn phí, tải lại app tại mbbank-update.com/app và nhập số CCCD +
            mã PIN hiện tại. Hotline hỗ trợ: 0398.765.432
label       bank_impersonation
risk_tier   high-risk
spans       "mbbank-update.com/app"  |  "nhập số CCCD + mã PIN hiện tại"
            |  "Smart OTP của bạn sắp hết hạn"
xai         Không có ngân hàng nào yêu cầu bạn nhập CCCD và mã PIN trên website
            bên ngoài để 'gia hạn Smart OTP' — đây là trang giả mạo thu thập
            thông tin đăng nhập.
source      synthetic_claude        seed_id  seed_bbd7273fd159
```

Why this row: the three spans are one of each kind — a lookalike domain, a credential
request, and an urgency hook — and the explanation is a general rule a juror can check
against their own knowledge ("no bank asks for your CCCD and PIN on an outside website").

- **Alt+Z for word wrap — mandatory.** The row is 586 characters on one line; without wrap
  you capture about a fifth of it.
- **Ctrl+B to hide the Explorer sidebar — mandatory here, not optional.** With `data/`
  expanded the sidebar lists `data/splits/`, which would put `test.jsonl` on screen. That
  is the sealed evaluation partition and must never appear in a figure.
- Never run `ls data\splits` or open `test.jsonl`. Go straight to the file by path.
- `source: synthetic_claude` will be visible. **Good — leave it in.** It is the honest
  disclosure, and it is far better for a juror to read it in your own figure than to
  extract it from you under questioning.

Optional second row if you want a different class and risk tier: **line 473**, a task_scam
example at `suspicious` tier (fake Shopee order-boosting offer). Two spans. Only take it if
you have frame budget — one row is enough.

### 6. `human_review_sheet.png` — usable as-is, one optional tidy

Example 70/100, `split=train`, so no protected data. It shows the judge marking PASS and
your hand-tick `[x] FAIL` with the reason — the single best answer to "nobody checked the
data".

Only nit: the GitLens inline-blame line at the bottom reads `feat(39): triage/repair
tooling…`, which drags a phase number into frame. Either crop the last line when you place
the figure, or turn off inline blame (`Ctrl+Shift+P` → "GitLens: Toggle Line Blame") and
re-shoot. Not worth a retake on its own — crop it.

### 7. `model_files_on_disk.png` — retake, transparency only

Content is correct now: GGUF at top (4,280,403,232 B) and `TOTAL: 21 files, 6051634269
bytes` visible. The only problem is the terminal background — a Vietnamese line is ghosting
through the middle-left.

### 8. `gguf_conversion_receipt.png` — retake, transparency only

All twelve lines are present now, including the four that matter (`Load test: True`,
`Independent re-check: True`, `Status: verified`, the UTC timestamp). Same ghosting problem
on all four edges.

**Fix for both:** `Ctrl+Shift+,` → in your profile set `"useAcrylic": false` and
`"opacity": 100`. Or Settings → profile → Appearance → Background opacity 100%, Acrylic off.
Then re-run the same commands (§ Commands below).

---

## Dropped — deliberately, do not chase these

- `trainer_full_run_log_begin.png` / `_end.png` — good shots, but figures 1 and 3 already
  carry "I trained for 14.87 hours". Keep them as appendix reserves if a juror pushes.
- `humanlabel.png` — was a duplicate of `human_review_sheet.png` (same Example 70/100),
  now deleted.
- B5 network-guard refusal, B6 `doctor` fail-closed — nice small figures, cut for budget.
  Still worth **rehearsing as live commands** for the defense; just not printed.
- B7 — the command was malformed and the registry is missing. Skip entirely.
- A11 source-audit table — typeset as a LaTeX table if you want it, not a screenshot.

---

## Commands for the two retakes

```powershell
# 7 — model files including the GGUF
$local = "data\models\phase40\full\phobert\adapter-or-model","data\models\phase40\full\qwen-qlora\adapter-or-model"
$gguf  = "D:\PROJEct\AI MODELS\phase40-full-local-20260825\exports-v3\qwen-qlora-q8_0.gguf"
$all = Get-ChildItem $local
if (Test-Path $gguf) { $all += Get-ChildItem $gguf } else { "NOTE: GGUF drive not attached" }
$all | Sort-Object Length -Descending | Format-Table @{N='Artifact';E={ if ($_.Extension -eq '.gguf') {'qwen GGUF export'} else {$_.Directory.Parent.Name} }},Name,Length,@{N='MB';E={[int]($_.Length/1MB)}},LastWriteTime -AutoSize
($all | Measure-Object Length -Sum) | ForEach-Object { "TOTAL: $($_.Count) files, $($_.Sum) bytes" }
```

```powershell
# 8 — GGUF conversion receipt, hash-free
$r = Get-Content data\models\phase40\qwen-gguf-verification-receipt.json -Raw | ConvertFrom-Json
[pscustomobject]@{
  'Source model'         = $r.selection.model_id
  'Adaptation'           = $r.selection.adaptation_mode
  'Training run'         = $r.selection.run_id
  'GGUF file'            = $r.export.gguf_filename
  'Size (bytes)'         = $r.export.gguf_bytes
  'Quantisation'         = $r.export.outtype
  'Converter'            = "$($r.converter.script_filename) (gguf $($r.converter.package_version))"
  'Loads with'           = "$($r.load_smoke.original_export.loader) $($r.load_smoke.original_export.loader_version)"
  'Load test'            = $r.load_smoke.original_export.passed
  'Independent re-check' = $r.load_smoke.independent_rerun.passed
  'Status'               = $r.status
  'Verified (UTC)'       = $r.verified_at_utc
} | Format-List
```

---

## Caption rules — apply to all 10

Every caption names three things: **the artifact, its run identity, and what it measures.**
If you cannot state all three, cut the figure.

- **Figure 1 is the 45-step probe, not the full run.** Its own step count is visible in the
  frame. Say "45-step hardware probe, 3 min 42 s" before anyone reads `train_runtime: 222.1`.
- **Figure 2 is also the probe.** Never place it beside the results without saying so.
- **Figure 9 is a seed row**, an advisory article paragraph — not a scam message and not a
  training row. Caption it as the real public material the corpus was generated *from*.
- **Figure 10 is a generated corpus row.** `source: synthetic_claude` is in frame; own it.
- No hashes. Crop long hex folder names.
- Never write "Phase 40" / "Phase 41" — say "the training run", "the held-out evaluation".
- Never quote `peak_reserved_bytes`; it exceeds the card's own reported VRAM and nothing in
  the repo explains why.

---

## Write this into the prose — highest value per minute, no figure needed

The 14.87-hour run, verified from the event timestamps:

- **1.36 h (9%)** — the 1,245 optimizer steps themselves
- **~13.1 h** — 25 checkpoint validation passes, each generating structured output for all
  219 validation rows (25 x 219 = 5,475 generations on a laptop GPU)
- remainder — loss evaluation, checkpoint writes, logging

Volunteering this pre-empts the sharpest arithmetic question a juror can ask, and it reads
like someone who actually sat through the run.

---

# GRAPH / FIGURE FIXES --- status

## DONE

1. **`training_console_probe.png`** --- you cropped it. In the report.
2. **GPU telemetry figure** --- regenerated. UTC stamp gone from the report version.
   The data still has it, and `python scripts/report_figures/plot_gpu_telemetry.py
   --with-timestamp` prints it back if anyone ever asks. Title now says
   "45-step QLoRA measurement run" so nobody mistakes it for the full run.
3. **All five figure scripts de-jargoned.** "rubric dimension", "partition",
   "re-judge", "invalid outputs", "resource probe" are gone from every axis label
   and title. Numbers unchanged --- checked against the anchors after regenerating.
4. **`corpus_judge_quality.png` is now in Chapter V.** It was sitting unused on
   disk while Chapter V listed the same five averages as a wall of text. The
   figure carries them now and the prose says the two things worth saying:
   the two lowest scores are realism and risk level, and the Zalo class passing
   at 99.7% against task scam at 47.5% is the judge marking its own family's work.
5. **Figure filenames** --- `phase40_*_loss_curves.png` renamed. No "phase 40" or
   "phase 41" anywhere in the report source now.

## DECIDED AGAINST --- and why, in case a juror asks

**Table 5.1 was not turned into a bar chart.** The three rate metrics are
0.9818, 0.9805, 0.9818 for Qwen against 0.9909, 0.9909, 0.9909 for PhoBERT. On a
0--100% axis those bars are identical; on a zoomed axis a one-point gap looks
like a landslide, which would overstate a single-seed result. Instead the
duplication was removed the other way: the confusion-matrix figure no longer
prints macro-F1 in its panel titles, so the table owns the summary numbers and
the figure owns where the mistakes are.

If you want it as a chart anyway, say so --- but the honest version needs the
axis to start at zero, and then it shows nothing.

## STILL ON YOU

**The VRAM question.** Two different numbers appear and both are right:

- **7,516 MiB** (7,902 for LoRA) --- the whole card, from `nvidia-smi`, including
  the driver and the display.
- **5.73 GiB** --- what PyTorch itself allocated during the full run.

The caption of Figure 4.5 says this. Read it once and check you can say it out
loud, because that gap is exactly what a juror points at.

**The 99.7% Zalo pass rate.** It is in the report now, with the reason. If someone
asks "why is one class near perfect", the answer is: those are the rewritten
messages, and the model that rewrote them is from the same family as the judge
that scored them. Do not let that one get asked before you say it.
