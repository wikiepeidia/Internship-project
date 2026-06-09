# Phase 19: Slide Content Fixes - Context

**Gathered:** 2026-06-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix all defense slides per supervisor feedback. No new features — corrections only. All files live under `documents/reports/latex/slides/`. The main entry point is `slides.tex`; section files are in `slides/sections/`. After all edits the deck must compile clean with XeLaTeX (zero errors).

</domain>

<decisions>
## Implementation Decisions

### Title and Project Scope Framing

- New main title: `Fine-Tuning a Local LLM for Vietnamese Financial Phishing Detection` — states what was done (fine-tuning) without overpromising a production app
- Remove "Explainable AI" from the title; in Contributions slide (11) note "evidence-linked cues and grounded recommendations" as the modest, accurate framing
- New short title in footline: `Local LLM Fine-Tuning — Vietnamese Phishing`
- Edit location: `slides.tex` lines `\title[...]` and `\title`

### Structural Fixes — Reordering and Slide 4/5

- Move "Why Local?" section to section 2 (right after Motivation, before Architecture/Pipeline): reorder `\section` and `\input` entries in `slides.tex`
- Rename slide 4 frame title from "System Architecture" to `Training Pipeline Overview`; update `\framesubtitle` accordingly
- Add a footnote note on slide 4: "Synthetic data used for training only — val/test splits use seed-collected messages only"
- On slide 5 (Data Pipeline), add one-line note beneath figure: "Pydantic schema validator used as quality judge: batches with realism score ≥ 4/5 accepted (49/50 batches passed)"
- "Versioned Splits" → "Data Splits" wherever it appears in slides (check TikZ figures too)
- Rename slide 2 frame title from `{Agenda}` to `{Table of Contents}`

### Privacy Slide Replacement (Slide 6)

- Replace the jailbreak content frame entirely with a new frame titled `Privacy Risk: Cloud API Data Leakage`
- Two documented incidents to cite:
  1. OpenAI ChatGPT March 2023 data breach — payment card info and chat history of ~1.2% of users exposed due to a Redis cache bug
  2. Samsung Semiconductor 2023 — engineers pasted confidential chip design code and meeting notes into ChatGPT; data stored on OpenAI servers
- Use text-only 2-column layout (no image): left col = incident bullets, right col = block "Why Local Inference?" showing how a local model avoids this risk
- Remove the Amazon Rufus image dependency
- Keep the second existing frame ("Architectural Solution: Local Data Boundary") with its cloud_vs_local TikZ figure — this stays after the new privacy frame

### Training Metrics Clarity (Slide 8 = 07_model.tex)

- Fix `1{,}733\,s` → `1{,}733\,s (${\approx}29$ min)` so the committee cannot misread it as "1 second"
- Replace the current CPU Deployment block's single-line mention of Q8_0 with a two-stage explanation:
  - **Stage 1 — Training:** NF4 4-bit quantization loads the *base model weights* into GPU VRAM during QLoRA fine-tuning (saves ~50% VRAM vs fp16)
  - **Stage 2 — Export:** After training, adapter is merged back into the base model (restored to fp16), then re-quantized to GGUF Q8_0 for llama.cpp CPU inference (8-bit = better precision than NF4, well-supported by llama.cpp)
  - This directly answers "where are the extra 4 bits" — they come back during the merge+re-quantize export step

### Reference Slide

- Add a References frame at the end of the deck (before or after Thank You) listing:
  - The Samsung ChatGPT leak citation
  - The OpenAI March 2023 breach citation
  - Existing key references already in the thesis bib (e.g., QLoRA paper, Qwen paper)
- Use `\begin{frame}[allowframebreaks]{References}` with `\bibliography` or a manual `\begin{thebibliography}` block

### Claude's Discretion

- Exact wording of reference slide entries (use APA-style inline citations or short BibTeX keys matching `main.bib`)
- Exact LaTeX framing of the two-stage quantization explanation (block environment vs itemize vs table row)
- Whether "Data Splits" vs "Versioned Splits" appears in the TikZ data pipeline figure — if it does, update the figure source; if not, skip

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets

- `slides.tex` — main entry point; `\title`, `\author`, `\institute`, `\date`, `\section`/`\input` structure
- `slides/sections/01_title.tex` — `\titlepage` frame (no edits needed, title metadata is in `slides.tex`)
- `slides/sections/02_agenda.tex` — `{Agenda}` frame title, `\tableofcontents` 2-col layout
- `slides/sections/04_architecture.tex` — `{System Architecture}` title, `\scalebox{0.70}{\input{...system_overview_bare.tex}}`, footnote text
- `slides/sections/05_data.tex` — data pipeline TikZ figure, JSONL snippet, split counts
- `slides/sections/06_why_local.tex` — TWO frames: (1) jailbreak frame with `rufusai.png` image, (2) cloud_vs_local figure frame
- `slides/sections/07_model.tex` — QLoRA config + training results table, Why QLoRA + CPU Deployment blocks
- `slides/sections/12_future.tex` — contains Thank You frame; reference slide should be inserted before or after this
- `slides/figures/data_pipeline_bare.tex` — TikZ source for data pipeline figure; check for "Versioned Splits" text

### Established Patterns

- CambridgeUS/beaver theme with CVBLUE color tokens
- `\begin{block}{...}` for call-out boxes
- `\begin{columns}[t]` for 2-col layouts
- `\footnotesize`, `\scriptsize` for dense content
- `[shrink=N]` option on frames with tight content
- `\framesubtitle` for secondary context
- `\input{slides/figures/...}` for TikZ figures

### Integration Points

- Section ordering controlled in `slides.tex` via `\section{}` + `\input{}` pairs
- New privacy frame replaces first frame of `06_why_local.tex` (the jailbreak frame)
- Reference slide: add a new file `slides/sections/13_references.tex` and `\input` it in `slides.tex` after section 8 (Conclusion)

</code_context>

<specifics>
## Specific Ideas

- Supervisor said "only training model not making app" → new title must foreground "fine-tuning" / "training"
- Supervisor said "api leak recommended + privacy issue, require researching for chatgpt leaked data problem" → use the two specific incidents (OpenAI March 2023 + Samsung 2023); both are well-documented and credible for a defense
- Supervisor said `1{,}733\,s` was confusing → use `(${\approx}29$ min)` parenthetical
- Supervisor said QLoRA 4-bit vs GGUF 8-bit "no sense, where extra 4 bit" → explain as two-stage process: NF4 during training (VRAM trick), Q8_0 after merge+export (inference format)

</specifics>

<deferred>
## Deferred Ideas

- Phase 20 will handle binary evaluation (scam vs non-scam) on slides 9-10 — those slides are NOT touched in this phase
- Phase 21 will update the thesis report to match these slide corrections

</deferred>
