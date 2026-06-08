# Phase 13 Plan 01 — Report: Dataset & QLoRA Documentation

**Status:** COMPLETE  
**Date:** 2026-06-05

## What was done

### Chapter 3 — Data Construction section
- Changed "public Vietnamese warning sources" → `tinnhiemmang.vn` cybercrime alert portal (GAP-01)
- Added `claude-3-5-haiku` API as the generation model in the pipeline description (GAP-02)
- Quality-judge stats already present (49/50 batches, 4.68 realism, 4.96 label-correctness)

### Chapter 3 — QLoRA section
- Added hyperparameters inline: r=16, α=32, 4-bit NF4 + double quantization (GAP-05)
- Added runtime=1,733s to the paragraph
- Added `\input{tables/qlora_config}` with new table file (GAP-05)
- GGUF Q8_0 export rationale already present in prose (GAP-06)

### New file: tables/qlora_config.tex
Tabular with: base model, r, α, quantization, train examples, val examples, checkpoint, loss, runtime, export format.

## Guardrail check
- No mention of 0.44 recall or "repaired" dataset — ✅
- Seed source = tinnhiemmang.vn — ✅
- Dataset presented as intentional pipeline design — ✅
