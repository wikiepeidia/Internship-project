---
phase: "19-slide-content-fixes"
plan: "01"
subsystem: defense-slides
tags: [latex, beamer, slides, defense, content-fixes]
dependency_graph:
  requires: []
  provides:
    - "Updated defense slide deck with supervisor feedback applied"
    - "Title communicates fine-tuning scope"
    - "Privacy motivation grounded in documented API leak incidents"
    - "Two-stage quantization story clearly explained"
    - "Reference slide with four citations"
  affects:
    - "documents/reports/latex/slides.tex"
    - "documents/reports/latex/slides/sections/02_agenda.tex"
    - "documents/reports/latex/slides/sections/04_architecture.tex"
    - "documents/reports/latex/slides/sections/05_data.tex"
    - "documents/reports/latex/slides/sections/06_why_local.tex"
    - "documents/reports/latex/slides/sections/07_model.tex"
    - "documents/reports/latex/slides/sections/13_references.tex"
tech_stack:
  added: []
  patterns:
    - "Beamer \begin{frame}[shrink=N] for content-heavy slides"
    - "\\thebibliography manual block (no BibTeX backend) in Beamer"
key_files:
  created:
    - "documents/reports/latex/slides/sections/13_references.tex"
  modified:
    - "documents/reports/latex/slides.tex"
    - "documents/reports/latex/slides/sections/02_agenda.tex"
    - "documents/reports/latex/slides/sections/04_architecture.tex"
    - "documents/reports/latex/slides/sections/05_data.tex"
    - "documents/reports/latex/slides/sections/06_why_local.tex"
    - "documents/reports/latex/slides/sections/07_model.tex"
decisions:
  - "Added [shrink=12] to the API leak frame to resolve 63pt overfull vbox; content-heavy two-column layout needs shrink on CambridgeUS theme"
  - "Used manual \\thebibliography (no BibTeX backend) for references frame to keep Beamer file self-contained"
  - "Section reorder places Why Local? at position 2 so the privacy motivation precedes the technical pipeline"
metrics:
  duration: "~15 minutes"
  completed: "2026-06-09"
  tasks_completed: 5
  tasks_total: 5
  files_created: 1
  files_modified: 6
---

# Phase 19 Plan 01: Slide Content Fixes Summary

**One-liner:** Applied all 7 supervisor-feedback categories to the Beamer defense deck — title to Fine-Tuning scope, section reorder (Why Local? at pos 2), Training Pipeline rename, Pydantic quality gate stat, API leak frame replacing jailbreak frame, 29-min runtime label plus two-stage NF4/Q8_0 quantization story, and new 4-citation references slide; deck compiles clean (16 pages, zero errors).

## Tasks Completed

### Task 1 — Title, footline, agenda rename, section reorder (SLIDE-01, SLIDE-02)

**slides.tex:**
- `\title[...]` updated: short title "Local LLM Fine-Tuning --- Vietnamese Phishing", long title "Fine-Tuning a Local LLM for Vietnamese Financial Phishing Detection"
- Section order changed: 1=Motivation, 2=Why Local?, 3=Training Pipeline, 4=Data Pipeline, 5=Model, 6=Evaluation, 7=Demo, 8=Conclusion
- `\input{slides/sections/13_references.tex}` added after Conclusion inputs, before `\end{document}`

**02_agenda.tex:**
- Frame title changed from `{Agenda}` to `{Table of Contents}`

### Task 2 — Training Pipeline rename, synthetic data footnote, Pydantic bullet (SLIDE-03, SLIDE-04)

**04_architecture.tex:**
- Frame title: `{System Architecture}` → `{Training Pipeline Overview}`
- Framesubtitle: `{End-to-End System Overview}` → `{Offline Training Pipeline \textrightarrow{} Local Inference}`
- Footnote added: `\footnote{\scriptsize Synthetic data used for training only --- val/test splits use seed-collected messages only.}`

**05_data.tex:**
- Third bullet added to right-column itemize: `\item \textbf{Pydantic quality gate:} schema validation + realism scoring; 49/50 batches passed (${\geq}4/5$ realism)`

### Task 3 — Replace jailbreak frame with API leak frame (SLIDE-05)

**06_why_local.tex:**
- Entire first frame ("Liability and Hallucination Risk" with rufusai.png) replaced with "Privacy Risk: Cloud API Data Leakage" frame
- New frame documents OpenAI ChatGPT March 2023 Redis cache bug (1.2% user data exposed) and Samsung Semiconductor 2023 chip design code leak
- Cloud API risk model column added (transit, retention, breach, policy risks)
- Second frame ("Architectural Solution: Local Data Boundary") preserved unchanged except caption updated: "eliminates the prompt injection surface shown on the previous slide" → "sensitive data never leaves the device"

### Task 4 — Training time and two-stage quantization (SLIDE-06)

**07_model.tex:**
- Runtime row: `1{,}733\,s (CUDA)` → `1{,}733\,s (${\approx}29$\,min, CUDA)`
- CPU Deployment block: two items replaced with three items:
  1. Stage 1 (training): 4-bit NF4 loads base weights into GPU VRAM during QLoRA — saves ~50% VRAM vs fp16
  2. Stage 2 (export): Adapter merged back to fp16; re-quantized to GGUF Q8_0 for llama.cpp CPU runtime
  3. ~13s warm latency on a standard laptop CPU

### Task 5 — New References slide and compile verification (SLIDE-07)

**slides/sections/13_references.tex (new file):**
- `\begin{frame}[allowframebreaks]{References}` with manual `\thebibliography{9}` block
- Four entries: openai2023breach, samsung2023leak, dettmers2023qlora, qwen2024

**Compile result:** XeLaTeX ran twice:
1. First pass: overfull vbox (63pt) on the API leak frame (dense two-column layout at [t] alignment)
2. Auto-fixed: added `[shrink=12]` to the API leak frame
3. Second pass: clean — "Output written on slides.pdf (16 pages)", zero `! LaTeX Error` lines

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Added shrink=12 to API leak frame to fix 63pt overfull vbox**
- **Found during:** Task 5 compile verification
- **Issue:** The new two-column API leak frame with itemize lists + block environment overflows the CambridgeUS slide content area by 63pt at `[t]` alignment
- **Fix:** Added `[shrink=12]` to `\begin{frame}[t,shrink=12]{Privacy Risk: Cloud API Data Leakage}` — consistent with the existing `[shrink=10]` on the replaced jailbreak frame and `[shrink=15]` on the model slide
- **Files modified:** `documents/reports/latex/slides/sections/06_why_local.tex`
- **Compile:** Resolved; second pass produced zero warnings

## Known Stubs

None. All slides render real data from training artifacts.

## Threat Flags

None. All edits are static LaTeX text changes; no new network endpoints, auth paths, or schema changes introduced.

## Requirements Coverage

| Requirement | Status | Evidence |
|-------------|--------|----------|
| SLIDE-01 | DONE | `\title[Local LLM Fine-Tuning --- Vietnamese Phishing]{Fine-Tuning a Local LLM...}` in slides.tex |
| SLIDE-02 | DONE | Section 2 = "Why Local?", Section 3 = "Training Pipeline"; 02_agenda.tex frame = "Table of Contents" |
| SLIDE-03 | DONE | 04_architecture.tex frame = "Training Pipeline Overview"; footnote on synthetic data present |
| SLIDE-04 | DONE | 05_data.tex right column has Pydantic quality gate bullet with 49/50 stat |
| SLIDE-05 | DONE | 06_why_local.tex first frame is "Privacy Risk: Cloud API Data Leakage"; rufusai.png removed |
| SLIDE-06 | DONE | 07_model.tex Runtime = "1,733s (~29 min, CUDA)"; Stage 1 NF4 + Stage 2 GGUF Q8_0 items present |
| SLIDE-07 | DONE | slides/sections/13_references.tex created with 4 bibitems; slides.tex inputs it |

## Self-Check: PASSED

All verification checks confirmed:
1. `Fine-Tuning a Local LLM` in slides.tex title — FOUND
2. `Table of Contents` in 02_agenda.tex — FOUND
3. Section 2 = `Why Local?` in slides.tex — FOUND
4. `Training Pipeline Overview` in 04_architecture.tex — FOUND
5. `Synthetic data used for training only` in 04_architecture.tex — FOUND
6. `Pydantic quality gate` in 05_data.tex — FOUND
7. `Privacy Risk: Cloud API Data Leakage` in 06_why_local.tex — FOUND
8. rufusai references in 06_why_local.tex — 0 (REMOVED)
9. `approx}29` in 07_model.tex — FOUND
10. `Stage 1 (training)` in 07_model.tex — FOUND
11. `Stage 2 (export)` in 07_model.tex — FOUND
12. `openai2023breach` in 13_references.tex — FOUND
13. `13_references` input in slides.tex — FOUND
14. XeLaTeX compile: "Output written on slides.pdf (16 pages)", zero `! LaTeX Error` lines — PASSED
