# Phase 12: CambridgeUS Presentation Revamp — Context

**Gathered:** 2026-06-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Rebuild the entire LaTeX Beamer visual layer using CambridgeUS/beaver theme with USTH branding. Phase 11 Metropolis slides are the content reference only — all preamble and layout code is rewritten. Output: a clean-compiling XeLaTeX Beamer deck that a graduation thesis committee finds professional.

</domain>

<decisions>
## Implementation Decisions

### Color Strategy

- **D-01:** Keep `\usecolortheme{beaver}` as-is. Beaver's crimson/dark-red is the PRIMARY structural color (80%) — frametitle, section bars, navigation header, major headings.
- **D-02:** CVBLUE (#1A5276) is the SECONDARY semantic accent (15%) — block titles, performance numbers (e.g., F1 scores, recall values), architecture diagram highlights. Use `\textcolor{CVBLUE}{...}` inline for numbers.
- **D-03:** Normal text stays black/dark gray (5%). No additional color introductions.
- **Rationale:** This is a graduation thesis defense, not a startup pitch. Beaver crimson signals university defense; CVBLUE marks what matters technically.

### Section Navigation + Agenda

- **D-04:** Add numbered `\section{}` markers in `slides.tex` before each content group: `\section{1. Motivation}`, `\section{2. Architecture}`, `\section{3. Data Pipeline}`, `\section{4. Why Local?}`, `\section{5. Model}`, `\section{6. Evaluation}`, `\section{7. Demo}`, `\section{8. Conclusion}`.
- **D-05:** Agenda slide (`02_agenda.tex`) uses `\tableofcontents` — auto-populates from `\section{}` markers. Remove the current manual two-column list.
- **D-06:** No `\section{}` before the title slide (01) or agenda slide (02) — they are pre-section frames.

### Block Environments

- **D-07:** **Definite blocks:**
  - Problem slide: `\begin{block}{Problem Statement}` wrapping the thesis thesis claim at the bottom, mirroring the reference pattern.
  - Evaluation slide: `\begin{block}{Result}` with `\textcolor{CVBLUE}{0.9553}` as the macro F1 headline.
- **D-08:** **Executor discretion (read reference_themes.tex):** Apply blocks to Contributions, Future Work, Why Local, and Demo slides following the reference's judgment on where blocks add visual hierarchy vs noise.

### Title Slide

- **D-09:** Use `\begin{frame}[plain]\titlepage\end{frame}` — CambridgeUS auto-renders author, title, institute, date with theme styling.
- **D-10:** Set in `slides.tex` preamble: `\title[Short Title]{Full Thesis Title}`, `\author[Phạm Thế Minh]{Phạm Thế Minh \\ {\small Student ID: 23BI14279}}`, `\institute[USTH]{University of Science and Technology of Hanoi (USTH) \\ {\small Supervisors: Giang Anh Tuấn \quad|\quad Nguyễn Việt Anh}}`, `\date{2026}`.
- **D-11:** Logo via `\logo{\includegraphics[height=0.5cm]{usth.png}}` — identical to reference.

### Figure Sizing

- **D-12:** Preserve the `\scalebox{factor}{\input{slides/figures/..._bare.tex}}` strategy from Phase 11 bug fixes. Tune `factor` per figure individually after first compile in CambridgeUS.
- **D-13:** Do NOT globally replace `\scalebox` with `\resizebox`. Do NOT redesign TikZ unless it genuinely fails to fit at any reasonable scale.
- **D-14:** Goal: fit CambridgeUS content area (shorter than Metropolis by ~1.2cm due to header + footer bars) while maximizing readability.

### Text Overflow Policy (tiered)

- **D-15:** Tier 1 — **Cut content aggressively first.** Defense slides are verbal; bullet points are memory aids not transcripts. Remove sub-bullets and explanatory text. One idea per bullet.
- **D-16:** Tier 2 — **Split frame if still dense.** A 15-slide deck becoming 17 slides is better than unreadable slides. Example: "Evaluation" can become "Evaluation Results" + "Error Analysis" naturally.
- **D-17:** Font size reduction (`\small`, `\footnotesize`) is a tool of last resort — prefer cutting first.

### Claude's Discretion

- Exact `\scalebox` factors for each figure (tune after first compile).
- Which additional slides beyond Problem and Evaluation get blocks (guided by reference_themes.tex study).
- Exact section name wording if numbered labels feel awkward for a specific section.
- Whether the confusion matrix slide (09) gets grouped under section 6 Evaluation or gets its own sub-section.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Theme Reference (highest priority)
- `documents/reports/latex/slides/reference_themes.tex` — Full working CambridgeUS/beaver presentation. Canonical template for: footer template, logo placement, `\section{}` naming convention, block environment usage, figure scaling with `\scalebox`, `\framesubtitle` placement, metadata setup. Study this file before writing any preamble or slide code.

### Existing Slide Files (content to preserve + adapt)
- `documents/reports/latex/slides.tex` — Current entry point. Needs: theme switch, metadata, `\section{}` markers added.
- `documents/reports/latex/slides/preamble/packages.tex` — Already stripped to safe Beamer-compatible packages. Do not add conflicting packages.
- `documents/reports/latex/slides/preamble/colors.tex` — CVBLUE `#1A5276` token defined here. Do not redefine; reference this file.
- `documents/reports/latex/slides/sections/` — All 12 section files. Content reference; some slides need cutting/block additions.

### Bare Figure Files (use these, not the thesis figure files)
- `documents/reports/latex/slides/figures/system_overview_bare.tex` — TikZ only, no float wrapper. Use in slide 04.
- `documents/reports/latex/slides/figures/cloud_vs_local_bare.tex` — TikZ only. Use in slide 06.
- `documents/reports/latex/slides/figures/recall_barchart_bare.tex` — TikZ only. Use in slide 08.

### Requirements
- `.planning/REQUIREMENTS.md` §v1.4 — THME-01 through THME-11, all for Phase 12.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `\usecolortheme{beaver}` setup from reference_themes.tex: copy verbatim, then layer CVBLUE overrides on top.
- Footer template in reference_themes.tex (lines 29-44): copy exactly — three `beamercolorbox` blocks for author/title/frame counter.
- `\logo{\includegraphics[height=0.5cm]{usth.png}}` from reference (line 47): copy exactly.
- `\setbeamertemplate{navigation symbols}{}` from reference (line 26): copy — removes clutter navigation icons.
- `\setbeamercolor{framesubtitle}{fg=darkgray}` from reference (line 21): copy.
- Bare TikZ figures in `slides/figures/` already have correct `\scalebox` wrappers from Phase 11 fix; keep those patterns.

### Established Patterns
- **No `\begin{figure}` or `\begin{table}` inside frames** — Phase 11 bug fix established that float wrappers cause Beamer crashes. Use bare TikZ input or inline tabulars only.
- **XeLaTeX compiler** — `slides.tex` uses `\setsansfont`/`\setmonofont`; keep XeLaTeX. The reference uses pdfLaTeX but that is irrelevant — our deck stays on XeLaTeX.
- **`[fragile]` on lstlisting frames** — slide 10_demo.tex uses `\begin{frame}[fragile]`; preserve this.

### Integration Points
- `usth.png` lives in `pics/` relative to `slides.tex`; `\graphicspath{{figures/}{pics/}}` already set.
- `rufusai.png` referenced in `06_why_local.tex` — same `pics/` search path.
- Confusion matrix data is inlined in `09_confusion.tex` (no external file dependency after Phase 11 fix).

</code_context>

<specifics>
## Specific Ideas

- **Reference-first principle:** User explicitly loves the reference_themes.tex presentation. When in doubt about any visual decision, match what the reference does. It is the design spec.
- **Graduation thesis identity:** This is NOT a tech company slide deck. Beaver crimson = university formality. CVBLUE = technical precision for numbers only. Keep this balance.
- **Evaluation numbers in CVBLUE:** `\textcolor{CVBLUE}{0.9553}` (Macro F1), `\textcolor{CVBLUE}{0.871}` (task-scam recall) — these are the headline results and should visually pop.
- **`\framesubtitle` everywhere possible** — Reference uses it on every non-plain frame. Same pattern expected here.
- **Slide count budget:** Target 15–17 content slides. Splitting Evaluation into two frames is acceptable and expected.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 12-cambridgeus-presentation-revamp*
*Context gathered: 2026-06-04*
