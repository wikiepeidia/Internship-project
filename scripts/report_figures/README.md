# Report figures

Each script reads one already-recorded evidence file and writes one PNG into
`documents/reports/latex/figures/`. They are all **read-only** with respect to the
evidence: nothing under `data/models/` is modified, no training, inference, evaluation
or model loading happens, and nothing touches `data/splits/`.

Run any of them from this directory:

```powershell
python plot_gpu_telemetry.py
python plot_checkpoint_sweep.py
python plot_full_run_timeline.py
python plot_corpus_quality.py
python plot_terminal_evaluation.py
```

| Script | Output | Reads |
|---|---|---|
| `plot_gpu_telemetry.py` | `gpu_telemetry_probe.png` | `data/models/phase40/probes/rtx5050-qlora-session-20260825/qlora/telemetry.jsonl` |
| `plot_checkpoint_sweep.py` | `checkpoint_selection_sweep.png` | each `full/<model>/checkpoints/step-*/validation-metrics.json`, plus `full/qwen-qlora/validation-metrics.json` |
| `plot_full_run_timeline.py` | `full_run_timeline.png` | `data/models/phase40/full/qwen-qlora/events.jsonl` |
| `plot_corpus_quality.py` | `corpus_judge_quality.png` | `data/processed/judge-summary.json`, `data/processed/judge-merged.jsonl` |
| `plot_terminal_evaluation.py` | `terminal_evaluation_confusion.png` | the frozen `data/models/phase41/verified-export/*/results.md` |

`vnphish_figs.py` holds the shared palette and axis styling so the four figures read as
one set.

## Two things worth knowing before you defend these

**The step-200 point in the checkpoint sweep.** The Qwen run evaluated every 50 optimizer
steps, 50 through 1245 — 25 evaluations, each recorded as an `evaluation` event in
`events.jsonl`. Only 24 checkpoint *directories* survive, because the selected step-200
checkpoint was promoted out of `checkpoints/` into `adapter-or-model/`. Its metrics live
in the run-root `validation-metrics.json` (macro-F1 0.9885153110), which
`comparison-report.md` independently records as `selected_step=200, macro_F1=0.9885`. So
the step-200 point is real and sourced — it just lives in a different file from the other
24. Step 300 happens to tie it exactly, which is normal here: several other checkpoints
also share identical scores, because greedy decoding on a converged model can produce
identical predictions across the 219 validation rows.

**Why `peak_reserved_bytes` is never plotted.** The run's own hardware block reports the
card as 8,546,484,224 B, while `peak_reserved_bytes` reaches 9,030,336,512 B. The usual
explanation is a Windows driver host-memory spill, but nothing in this repo confirms it.
`peak_allocated_bytes` (4.99 → 5.73 GiB) shows the same thing and every number in it is
defensible, so that is what `plot_full_run_timeline.py` draws.
