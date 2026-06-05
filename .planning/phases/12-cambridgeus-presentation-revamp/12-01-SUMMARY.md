---
phase: 12-cambridgeus-presentation-revamp
plan: "01"
subsystem: latex-slides
tags: [beamer, CambridgeUS, theme, preamble, XeLaTeX]
dependency_graph:
  requires: []
  provides: [CambridgeUS-preamble, CVBLUE-color-token, section-markers, footline-template, USTH-logo]
  affects: [slides/sections/*.tex, compile-plan-03]
tech_stack:
  added: []
  patterns: [CambridgeUS/beaver theme, 3-column beamercolorbox footline, short-form bracket metadata, section-before-input pattern]
key_files:
  created: []
  modified:
    - documents/reports/latex/slides.tex
    - documents/reports/latex/slides/preamble/colors.tex
decisions:
  - "Keep 12pt font size (not 10pt from reference) — plan instruction explicit; tune if compile overflow requires"
  - "CambridgeUS count=2 in slides.tex is correct: one in \\usetheme{CambridgeUS} and one in a comment line"
  - "Section count verification: 8 \\section{} commands confirmed by grep; comment line on 70 contains text reference only"
  - "documents/ is gitignored — LaTeX edits tracked on disk; SUMMARY.md is the only git artifact for this plan"
metrics:
  duration: "15 minutes"
  completed: "2026-06-05"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 2
---

# Phase 12 Plan 01: CambridgeUS Preamble Overhaul Summary

**One-liner:** Replaced Metropolis theme with CambridgeUS/beaver, added USTH logo, 3-column custom footline, CVBLUE block title override, D-10 short-form metadata, and 8 section markers; cleaned Metropolis colorlets from colors.tex.

## Tasks Completed

| Task | Name | Status | Files |
|------|------|--------|-------|
| 1 | Replace Metropolis preamble with CambridgeUS/beaver | Done | documents/reports/latex/slides.tex |
| 2 | Clean up colors.tex — remove Metropolis colorlets | Done | documents/reports/latex/slides/preamble/colors.tex |

## What Was Built

### Task 1: slides.tex — CambridgeUS/beaver preamble

`documents/reports/latex/slides.tex` was fully rewritten from a Metropolis skeleton to a CambridgeUS/beaver entry point:

**Theme block (replaced):**
- `\usetheme{metropolis}` → `\usetheme{CambridgeUS}` + `\usecolortheme{beaver}`
- Removed all four Metropolis-only `\setbeamercolor` hooks: `frametitle`, `progress bar`, `title separator`, `alerted text`

**Added CambridgeUS overrides:**
- `\setbeamercolor{block title}{fg=white, bg=CVBLUE}` (D-02)
- `\setbeamercolor{block body}{bg=CVBLUE!10!white}`
- `\setbeamercolor{framesubtitle}{fg=darkgray}` + `\setbeamerfont{framesubtitle}{...}` (from reference)
- `\setbeamerfont{section in head/foot}{series=\bfseries}` (from reference)
- `\setbeamertemplate{navigation symbols}{}` (from reference)

**Custom 3-column footline (verbatim from reference_themes.tex lines 29–44):**
- Left: `\insertshortauthor`
- Center: `\insertshorttitle`
- Right: `\insertshortdate{}` + `\insertframenumber{} / \inserttotalframenumber`

**Logo (verbatim from reference_themes.tex line 47):**
- `\logo{\includegraphics[height=0.5cm]{usth.png}}`

**Metadata replaced with D-10 short-form bracket syntax (Unicode characters directly):**
- `\title[Localized XAI for Vietnamese Phishing]{Localized Explainable AI for Vietnamese\\Financial Phishing Detection}`
- `\author[Phạm Thế Minh]{Phạm Thế Minh \\ {\small Student ID: 23BI14279}}`
- `\institute[USTH]{University of Science and Technology of Hanoi (USTH) \\ {\small Supervisors: Giang Anh Tuấn \quad|\quad Nguyễn Việt Anh}}`
- `\date{2026}`

**Section markers (8 total, per D-04, D-06):**
No `\section{}` before slide 01 or 02. First marker between 02_agenda.tex and 03_problem.tex:
1. `\section{1. Motivation}` → 03_problem.tex
2. `\section{2. Architecture}` → 04_architecture.tex
3. `\section{3. Data Pipeline}` → 05_data.tex
4. `\section{4. Why Local?}` → 06_why_local.tex
5. `\section{5. Model}` → 07_model.tex
6. `\section{6. Evaluation}` → 08_evaluation.tex + 09_confusion.tex (09 grouped under section 6, per open question 3)
7. `\section{7. Demo}` → 10_demo.tex
8. `\section{8. Conclusion}` → 11_contributions.tex + 12_future.tex

All preserved from Metropolis version: `\documentclass[aspectratio=169,12pt]{beamer}` (12pt kept), `\setsansfont`, `\setmonofont`, `\graphicspath`, `\setbeamercovered{invisible}`, `\begin{document}...\end{document}`, all 12 `\input{slides/sections/...}` calls.

### Task 2: colors.tex — Metropolis colorlets removed

`documents/reports/latex/slides/preamble/colors.tex` stripped to its essential CVBLUE definition:

```latex
%% Central color token — change one hex value to recolor the whole deck
\definecolor{CVBLUE}{HTML}{1A5276}
```

Removed:
- `\colorlet{CVBLUElight}{CVBLUE!15}` (Metropolis-only artifact)
- `\colorlet{CVBLUEdark}{CVBLUE!85}` (Metropolis-only artifact)
- Comment block "Metropolis theme color wiring (must come AFTER \usetheme{metropolis})" (no longer accurate)

The `CVBLUE!10!white` expression used in `\setbeamercolor{block body}` in slides.tex is an inline xcolor tint resolved at use time — no named colorlet required.

## Verification Results

| Check | Expected | Actual | Pass |
|-------|----------|--------|------|
| `\usetheme{CambridgeUS}` in slides.tex | 1 | 1 | Yes |
| `\usecolortheme{beaver}` in slides.tex | 1 | 1 | Yes |
| `\setbeamercolor{block title}` in slides.tex | 1 | 1 | Yes |
| `\logo{...}` in slides.tex | 1 | 1 | Yes |
| `\insertframenumber` in slides.tex | 1 | 1 | Yes |
| `\section{1. Motivation}` in slides.tex | 1 | 1 | Yes |
| `\section{8. Conclusion}` in slides.tex | 1 | 1 | Yes |
| "metropolis" in slides.tex (ci) | 0 | 0 | Yes |
| "progress bar" in slides.tex | 0 | 0 | Yes |
| "title separator" in slides.tex | 0 | 0 | Yes |
| `\title[...]` short-form in slides.tex | 1 | 1 | Yes |
| `\author[...]` short-form in slides.tex | 1 | 1 | Yes |
| `\institute[...]` short-form in slides.tex | 1 | 1 | Yes |
| `\definecolor{CVBLUE}{HTML}{1A5276}` in colors.tex | 1 | 1 | Yes |
| CVBLUElight in colors.tex | 0 | 0 | Yes |
| CVBLUEdark in colors.tex | 0 | 0 | Yes |
| "metropolis" in colors.tex | 0 | 0 | Yes |

## Deviations from Plan

None — plan executed exactly as written.

The plan specified preserving 12pt font size (noting reference uses 10pt but plan explicitly says keep 12pt) — preserved as instructed.

## Known Stubs

None. Plan 01 is a preamble/theme layer only. No data sources, no content rendering. Downstream Plans 02 and 03 depend on this clean preamble.

## Threat Flags

None. LaTeX source editing only — no network, no runtime state, no secrets. T-12-01 accepted as per plan threat model.

## Self-Check

### Created files exist:
- `.planning/phases/12-cambridgeus-presentation-revamp/12-01-SUMMARY.md` — this file

### Modified files (on disk, gitignored):
- `documents/reports/latex/slides.tex` — verified: contains `\usetheme{CambridgeUS}`, no "metropolis", 8 section markers, `\logo{`, `\insertframenumber`, D-10 metadata
- `documents/reports/latex/slides/preamble/colors.tex` — verified: contains only `\definecolor{CVBLUE}{HTML}{1A5276}`, no CVBLUElight, no CVBLUEdark

### Self-Check: PASSED
