# Phase 13 Plan 02 — Slides: Data Pipeline & Model Adaptation

**Status:** COMPLETE  
**Date:** 2026-06-05

## What was done

### slides/figures/data_pipeline_bare.tex (new)
TikZ 4-step horizontal flow:
- tinnhiemmang.vn Seeds (gray)
- claude-3-5-haiku Generation (CVBLUE)
- Pydantic Judge Quality Gate (orange)
- JSONL Output 3,000 rows (green)
Arrows with labels: "seed records", "batches", "49/50 pass"
Subtitles below each box in \scriptsize.

### slides/sections/05_data.tex (rewrite)
- [fragile] frame
- TikZ flow at 0.82 scalebox (GAP-03)
- 2-column bottom: left=JSONL snippet (text/label/suspicious_spans), right=split stats (GAP-04)

### slides/sections/07_model.tex (rewrite)
- 2-column [T] layout (GAP-07)
- Left: block "QLoRA Configuration" (r=16, α=32, NF4+double quant) + block "Training Results" (2018/210, step 505, loss 0.4951, 1733s)
- Right: block "Why QLoRA?" (6GB VRAM, adapter-only) + block "CPU Deployment" (GGUF Q8_0, ~13s latency)

## Compilation
- slides.tex: zero errors, zero Overfull warnings — ✅
- main.tex: zero errors — ✅

## Guardrail check
- No mention of 0.44 recall or "repaired" dataset — ✅
- Visual-first slides (TikZ flow on data, 2-col on model) — ✅
