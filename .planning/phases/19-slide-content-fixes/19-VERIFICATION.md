---
phase: "19-slide-content-fixes"
verified: "2026-06-09T00:00:00Z"
status: human_needed
score: 7/8 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Run: cd documents/reports/latex && xelatex -interaction=nonstopmode slides.tex && grep -c '! LaTeX Error' slides.log"
    expected: "Exit code 0; slides.log contains 'Output written on slides.pdf (16 pages)'; grep returns 0"
    why_human: "XeLaTeX is not available in the verification environment; compile result cannot be confirmed programmatically"
---

# Phase 19: Slide Content Fixes — Verification Report

**Phase Goal:** All defense slides corrected per supervisor feedback — title clarity, agenda renamed, pipeline slide naming fixed, synthetic data note added, Pydantic explained, API leak privacy research replaces jailbreak content, training time clarified, quantization mismatch explained, and a reference slide added.
**Verified:** 2026-06-09
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Slide 1 title says "Fine-Tuning a Local LLM for Vietnamese Financial Phishing Detection"; footer short title says "Local LLM Fine-Tuning --- Vietnamese Phishing" | VERIFIED | `slides.tex` line 62: `\title[Local LLM Fine-Tuning --- Vietnamese Phishing]{Fine-Tuning a Local LLM for Vietnamese\\Financial Phishing Detection}` |
| 2 | Slide 2 frame title reads "Table of Contents" | VERIFIED | `02_agenda.tex` line 3: `\begin{frame}[t]{Table of Contents}` |
| 3 | Section order: 1=Motivation, 2=Why Local?, 3=Training Pipeline, 4=Data Pipeline, 5=Model, 6=Evaluation, 7=Demo, 8=Conclusion | VERIFIED | `slides.tex` lines 78-102: `\section{1. Motivation}`, `\section{2. Why Local?}`, `\section{3. Training Pipeline}`, `\section{4. Data Pipeline}`, `\section{5. Model}`, `\section{6. Evaluation}`, `\section{7. Demo}`, `\section{8. Conclusion}` — exact order confirmed |
| 4 | Slide 4 (04_architecture.tex) frame title "Training Pipeline Overview"; framesubtitle updated; synthetic data footnote added | VERIFIED | `04_architecture.tex` line 2: `\begin{frame}{Training Pipeline Overview}`; line 3: `\framesubtitle{Offline Training Pipeline \textrightarrow{} Local Inference}`; line 12: `\footnote{\scriptsize Synthetic data used for training only --- val/test splits use seed-collected messages only.}` |
| 5 | Slide 5 (05_data.tex) right column contains Pydantic quality gate bullet with 49/50 batches statistic | VERIFIED | `05_data.tex` line 22: `\item \textbf{Pydantic quality gate:} schema validation + realism scoring; 49/50 batches passed (${\geq}4/5$ realism)` |
| 6 | Slide 6 (06_why_local.tex) first frame is "Privacy Risk: Cloud API Data Leakage" with OpenAI Mar 2023 and Samsung 2023 incidents; jailbreak/rufusai.png reference removed | VERIFIED | `06_why_local.tex` line 2: `\begin{frame}[t,shrink=12]{Privacy Risk: Cloud API Data Leakage}`; line 7: `\textbf{OpenAI ChatGPT (March 2023):} Redis cache bug...`; line 8: `\textbf{Samsung Semiconductor (2023):} Engineers pasted confidential chip design code...`; grep for "rufusai" returns 0 matches |
| 7 | Slide 8 (07_model.tex) Runtime row shows ~29 min; CPU Deployment block has three items: Stage 1 (NF4 training), Stage 2 (GGUF Q8_0 export), latency | VERIFIED | `07_model.tex` line 24: `\textbf{Runtime}    & 1{,}733\,s (${\approx}29$\,min, CUDA)`; lines 39-41: Stage 1 (training) NF4, Stage 2 (export) GGUF Q8_0, ${\approx}13$s warm latency — old single-line "Exported to GGUF Q8_0" is absent |
| 8 | slides/sections/13_references.tex exists with References frame and four bibitems; slides.tex inputs it after Conclusion; XeLaTeX compiles clean | PARTIAL — file and wiring VERIFIED; compile needs human | `13_references.tex` line 2: `\begin{frame}[allowframebreaks]{References}` with all four bibitems (openai2023breach, samsung2023leak, dettmers2023qlora, qwen2024); `slides.tex` line 104: `\input{slides/sections/13_references.tex}` after Conclusion inputs and before `\end{document}`; XeLaTeX compile cannot be run in this environment |

**Score:** 7/8 truths fully verified; 1 truth partially verified (file+wiring VERIFIED, compile result UNCERTAIN)

---

### Per-Requirement Verdicts

#### SLIDE-01 — PASS

**Requirement:** Title updated to "Fine-Tuning a Local LLM for Vietnamese Financial Phishing Detection" in slides.tex

**Evidence:**
- File: `documents/reports/latex/slides.tex`, line 62
- Exact text: `\title[Local LLM Fine-Tuning --- Vietnamese Phishing]{Fine-Tuning a Local LLM for Vietnamese\\Financial Phishing Detection}`
- Short title in footer bracket: "Local LLM Fine-Tuning --- Vietnamese Phishing"
- Long title: "Fine-Tuning a Local LLM for Vietnamese Financial Phishing Detection"

**Verdict: PASS** — Both title variants match the requirement exactly.

---

#### SLIDE-02 — PASS

**Requirement A:** "Agenda" → "Table of Contents" in 02_agenda.tex
**Requirement B:** Section reorder — "Why Local?" at position 2, after Motivation

**Evidence A:**
- File: `documents/reports/latex/slides/sections/02_agenda.tex`, line 3
- Exact text: `\begin{frame}[t]{Table of Contents}`

**Evidence B:**
- File: `documents/reports/latex/slides.tex`, lines 78-102
- `\section{1. Motivation}` (line 78)
- `\section{2. Why Local?}` (line 81)
- `\section{3. Training Pipeline}` (line 84)
- `\section{4. Data Pipeline}` (line 87)
- `\section{5. Model}` (line 90)
- `\section{6. Evaluation}` (line 93)
- `\section{7. Demo}` (line 97)
- `\section{8. Conclusion}` (line 100)

**Verdict: PASS** — Frame title renamed and full 8-section order is correct.

---

#### SLIDE-03 — PASS

**Requirement:** Slide 4 frame title → "Training Pipeline Overview"; framesubtitle updated; synthetic data footnote added (04_architecture.tex)

**Evidence:**
- File: `documents/reports/latex/slides/sections/04_architecture.tex`
- Line 2: `\begin{frame}{Training Pipeline Overview}` — old "System Architecture" is gone
- Line 3: `\framesubtitle{Offline Training Pipeline \textrightarrow{} Local Inference}` — old "End-to-End System Overview" is gone
- Line 12: `\footnote{\scriptsize Synthetic data used for training only --- val/test splits use seed-collected messages only.}` — footnote present

**Verdict: PASS** — All three sub-requirements met.

---

#### SLIDE-04 — PASS

**Requirement:** Pydantic quality gate bullet added to 05_data.tex (49/50 batches passed)

**Evidence:**
- File: `documents/reports/latex/slides/sections/05_data.tex`, line 22
- Exact text: `\item \textbf{Pydantic quality gate:} schema validation + realism scoring; 49/50 batches passed (${\geq}4/5$ realism)`
- Located in the right-column itemize block as the third item

**Verdict: PASS** — Bullet present with exact statistic.

---

#### SLIDE-05 — PASS

**Requirement:** Jailbreak frame replaced with "Privacy Risk: Cloud API Data Leakage" (OpenAI March 2023 + Samsung 2023 incidents) in 06_why_local.tex

**Evidence:**
- File: `documents/reports/latex/slides/sections/06_why_local.tex`
- Line 2: `\begin{frame}[t,shrink=12]{Privacy Risk: Cloud API Data Leakage}` — new first frame
- Line 3: `\framesubtitle{Documented Incidents --- Sensitive Data Sent to Cloud APIs}`
- Line 7: `\textbf{OpenAI ChatGPT (March 2023):} Redis cache bug exposed chat history and payment card details of ${\sim}1.2\%$ of active users to other users.`
- Line 8: `\textbf{Samsung Semiconductor (2023):} Engineers pasted confidential chip design code and meeting notes into ChatGPT; data stored on OpenAI servers, triggering an internal investigation.`
- No "rufusai" anywhere in the file — jailbreak frame fully removed
- Second frame `\begin{frame}{Architectural Solution: Local Data Boundary}` preserved at line 29
- Caption at line 36: `{\small Output schema is strictly constrained --- sensitive data never leaves the device.}` — updated from old "prompt injection" wording
- Note: `[shrink=12]` was added to the first frame (deviation from plan's `[t]` only) to fix a 63pt overfull vbox — acceptable and documented in SUMMARY.md

**Verdict: PASS** — Jailbreak frame replaced; real documented incidents present; rufusai removed; second frame intact.

---

#### SLIDE-06 — PASS

**Requirement:** Runtime row updated to include "~29 min"; CPU Deployment block expanded with Stage 1 (NF4) + Stage 2 (GGUF Q8_0) two-stage explanation in 07_model.tex

**Evidence:**
- File: `documents/reports/latex/slides/sections/07_model.tex`
- Line 24: `\textbf{Runtime}    & 1{,}733\,s (${\approx}29$\,min, CUDA)` — includes ~29 min label
- Lines 39-41 (CPU Deployment block):
  - `\item \textbf{Stage 1 (training):} 4-bit NF4 loads base weights into GPU VRAM during QLoRA --- saves ${\approx}50\%$ VRAM vs fp16.`
  - `\item \textbf{Stage 2 (export):} Adapter merged back to fp16; re-quantized to \textbf{GGUF Q8\_0} for \texttt{llama.cpp} CPU runtime.`
  - `\item \textbf{${\approx}13$\,s warm latency} on a standard laptop CPU.`
- Old single-line "Exported to GGUF Q8_0 format via llama.cpp." is absent — confirmed by reading full file

**Verdict: PASS** — Runtime label and two-stage quantization explanation both present.

---

#### SLIDE-07 — PASS (file + wiring); COMPILE: human needed

**Requirement:** New 13_references.tex created; `\input` added to slides.tex; XeLaTeX compiles clean

**Evidence:**
- File: `documents/reports/latex/slides/sections/13_references.tex` — exists (25 lines)
- Line 2: `\begin{frame}[allowframebreaks]{References}`
- All four bibitems present:
  - `\bibitem{openai2023breach}` (line 5)
  - `\bibitem{samsung2023leak}` (line 9)
  - `\bibitem{dettmers2023qlora}` (line 13)
  - `\bibitem{qwen2024}` (line 18)
- Wiring: `slides.tex` line 104: `\input{slides/sections/13_references.tex}` — positioned after `\input{slides/sections/12_future.tex}` (Conclusion) and before `\end{document}`
- XeLaTeX compile: CANNOT VERIFY — XeLaTeX not available in this environment

**Verdict: PASS on file creation and wiring; UNCERTAIN on compile result — human verification required**

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `documents/reports/latex/slides.tex` | Updated title metadata and section order | VERIFIED | Title line 62 correct; section block lines 78-104 correct; `\input{13_references.tex}` at line 104 |
| `documents/reports/latex/slides/sections/02_agenda.tex` | Renamed Table of Contents frame | VERIFIED | Line 3: `\begin{frame}[t]{Table of Contents}` |
| `documents/reports/latex/slides/sections/04_architecture.tex` | Renamed Training Pipeline frame with footnote | VERIFIED | Lines 2, 3, 12 all correct |
| `documents/reports/latex/slides/sections/05_data.tex` | Data slide with Pydantic quality gate bullet | VERIFIED | Line 22 contains full bullet with 49/50 stat |
| `documents/reports/latex/slides/sections/06_why_local.tex` | Replaced first frame with API leak incidents | VERIFIED | Line 2 new frame; OpenAI+Samsung present; rufusai gone |
| `documents/reports/latex/slides/sections/07_model.tex` | Clarified runtime label and two-stage quantization | VERIFIED | Line 24 has ~29 min; Stage 1/Stage 2 items at lines 39-41 |
| `documents/reports/latex/slides/sections/13_references.tex` | New References frame with four citations | VERIFIED | Exists with `\begin{frame}[allowframebreaks]{References}` and 4 bibitems |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| slides.tex | slides/sections/13_references.tex | `\input{slides/sections/13_references.tex}` | WIRED | Line 104, after Conclusion inputs, before `\end{document}` |
| slides.tex | section ordering | `\section{2. Why Local?}` | WIRED | Line 81 confirmed |

### Data-Flow Trace (Level 4)

Not applicable — phase produces static LaTeX document files, not components rendering dynamic data.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| XeLaTeX compile exits 0 | `xelatex -interaction=nonstopmode slides.tex` | CANNOT RUN — no TeX installation | SKIP — human needed |

### Probe Execution

No probe scripts declared for this phase.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| SLIDE-01 | 19-01-PLAN.md | Title updated to fine-tuning scope | SATISFIED | slides.tex line 62 |
| SLIDE-02 | 19-01-PLAN.md | Agenda → Table of Contents; Why Local? at position 2 | SATISFIED | 02_agenda.tex line 3; slides.tex lines 78-84 |
| SLIDE-03 | 19-01-PLAN.md | Frame title "Training Pipeline Overview"; updated framesubtitle; synthetic data footnote | SATISFIED | 04_architecture.tex lines 2, 3, 12 |
| SLIDE-04 | 19-01-PLAN.md | Pydantic quality gate bullet with 49/50 stat | SATISFIED | 05_data.tex line 22 |
| SLIDE-05 | 19-01-PLAN.md | API leak frame with OpenAI+Samsung incidents; rufusai removed | SATISFIED | 06_why_local.tex lines 2-8 |
| SLIDE-06 | 19-01-PLAN.md | Runtime ~29 min; Stage 1 NF4 + Stage 2 GGUF Q8_0 | SATISFIED | 07_model.tex lines 24, 39-41 |
| SLIDE-07 | 19-01-PLAN.md | 13_references.tex created with 4 bibitems; slides.tex inputs it | SATISFIED (file+wiring) | 13_references.tex; slides.tex line 104 |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (all 7 modified/created .tex files) | — | No TBD/FIXME/XXX/TODO/HACK/PLACEHOLDER found | — | None |

No debt markers, no stub returns, no hardcoded empty values in any of the seven files touched by this phase.

**Deviation noted (non-blocking):** `06_why_local.tex` uses `[t,shrink=12]` on the first frame instead of the plan's `[t]` only. This was an auto-fix during compile to resolve a 63pt overfull vbox. The fix is consistent with the pattern used elsewhere in the deck (`[shrink=10]` on the old frame, `[shrink=15]` on the model slide). Documented in SUMMARY.md.

### Human Verification Required

#### 1. XeLaTeX Compile Gate

**Test:** From `documents/reports/latex/`, run `xelatex -interaction=nonstopmode slides.tex` twice (two passes for cross-references), then check `slides.log`
**Expected:** Exit code 0; `slides.log` contains "Output written on slides.pdf (16 pages)"; no `! LaTeX Error` or `! Package` error lines
**Why human:** XeLaTeX is not available in the verification environment; the tool cannot execute the compiler

---

### Gaps Summary

No blocking gaps. All seven LaTeX file changes are correctly implemented:
- SLIDE-01 through SLIDE-07 file edits: all present and correct against exact text requirements
- Key link (13_references.tex wiring) verified
- No anti-patterns or debt markers

The only outstanding item is the XeLaTeX compile gate, which cannot be run programmatically in this environment. The SUMMARY.md documents a clean two-pass compile resulting in a 16-page PDF with zero errors and an auto-fixed shrink parameter on the new frame. If XeLaTeX is available on the local machine, running the compile is the single remaining verification step.

---

_Verified: 2026-06-09_
_Verifier: Claude (gsd-verifier)_
