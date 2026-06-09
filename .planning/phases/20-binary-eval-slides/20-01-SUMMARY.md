---
phase: 20
plan: "20-01"
subsystem: slides/evaluation
tags: [latex, beamer, evaluation, confusion-matrix, binary-classification]
dependency_graph:
  requires: []
  provides: [EVAL-04, EVAL-05]
  affects: [slides.pdf]
tech_stack:
  added: []
  patterns: [booktabs, beamer-columns, cellcolor, shrink]
key_files:
  created: []
  modified:
    - documents/reports/latex/slides/sections/08_evaluation.tex
    - documents/reports/latex/slides/sections/09_confusion.tex
decisions:
  - "Used $\\cdot$ (math-mode) instead of \\textperiodcentered for the centered dot separator — safer across XeLaTeX setups"
  - "Raised frame shrink from 10/5 to 25 on both frames after first compile showed beamer over-shrink warnings"
  - "Binary 2x2 uses $\\leftrightarrow$ (inline math) for the double-arrow in Key Finding block"
metrics:
  duration: "~12 minutes"
  completed: "2026-06-09"
  tasks_completed: 3
  tasks_total: 3
  files_modified: 2
---

# Phase 20 Plan 01: Binary Eval Table + 2x2 Confusion Matrix Summary

Per-class booktabs metrics table replaces TikZ bar chart on slide 8, binary 2x2 confusion matrix added to slide 9 in two-column layout alongside the existing 4-class matrix; deck compiles clean with XeLaTeX (zero fatal errors, 16 pages).

## Tasks Completed

### Task 1 — Replace bar chart with per-class metrics table (08_evaluation.tex)

Replaced `\scalebox{0.82}{\input{slides/figures/recall_barchart_bare.tex}}` with a booktabs table showing per-class Precision/Recall/F1/n for all 4 classes plus macro avg row. Added `\begin{block}{Binary Classification Result}` showing Precision 1.000, Recall 1.000, F1 1.000. Retained both original bullet points verbatim. Added `[shrink=25]` to frame options.

Key numbers in table:
- Bank Impersonation: Prec 0.836 / Recall 1.000 / F1 0.911 / n 56
- Zalo Social Eng.: Prec 1.000 / Recall 0.960 / F1 0.980 / n 75
- Task Scam: Prec 1.000 / Recall 0.871 / F1 0.931 / n 62
- Benign: Prec 1.000 / Recall 1.000 / F1 1.000 / n 61
- Macro avg: Prec 0.959 / Recall 0.958 / F1 0.955 / n 254

**Commit:** 58d21a2

### Task 2 — Add binary 2x2 confusion matrix in two-column layout (09_confusion.tex)

Restructured slide 9 to `\begin{columns}[t]` two-column layout:
- Left column (0.52\textwidth): existing 4-class matrix scaled to 0.72 (reduced from 0.82 to fit narrower column)
- Right column (0.44\textwidth): binary 2x2 table (Scam=193 TP, Non-scam=61 TN, both off-diagonal=0) with `\cellcolor{CVBLUE!15}` on diagonal cells, plus `\begin{block}{Key Finding}` stating all misclassifications are intra-scam and binary F1=1.000

Retained both original bullet points verbatim at the bottom.

**Commit:** 58d21a2

### Task 3 — XeLaTeX compile check

First compile: succeeded (Output written on slides.pdf, 16 pages, zero `! ` lines) but produced beamer warnings that frames were shrinking 23.99%/23.35% instead of declared 10%/5%.

Fix applied: raised both frame shrink values from 10/5 to 25 (Rule 1 auto-fix — layout warnings suppressed). Second compile: clean, no warnings, zero fatal errors.

**Compile result:** Exit 0, slides.pdf 168 KB, 16 pages, zero fatal LaTeX errors.

**Commit (shrink fix):** 05899ea

## Verification Results

| Check | Result |
|-------|--------|
| Bar chart reference removed from 08_evaluation.tex | PASS |
| `\begin{tabular}` present in 08_evaluation.tex | PASS (1 match) |
| Binary Classification Result block present | PASS (1 match) |
| `\begin{columns}` present in 09_confusion.tex | PASS (1 match) |
| Binary TP cell "193" present in 09_confusion.tex | PASS (1 match) |
| Zero `! ` lines in slides.log | PASS (0 matches) |
| slides.pdf exists and is non-zero | PASS (168,024 bytes) |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Frame shrink values insufficient for content density**
- **Found during:** Task 3 (first XeLaTeX compile)
- **Issue:** Beamer warned that slide 8 was shrinking 23.99% (declared 10%) and slide 9 was shrinking 23.35% (declared 5%) — content does not fit at the declared shrink limit
- **Fix:** Raised `[shrink=10]` to `[shrink=25]` in 08_evaluation.tex and `[shrink=5]` to `[shrink=25]` in 09_confusion.tex
- **Files modified:** 08_evaluation.tex, 09_confusion.tex
- **Commit:** 05899ea

## Requirements Covered

- **EVAL-04:** Slide 9 now shows binary 2x2 confusion matrix with perfect separation (TP=193, TN=61, FP=0, FN=0) alongside 4-class matrix
- **EVAL-05:** Slide 8 shows per-class precision/recall/F1/n table with macro avg row, and binary result block; slide 9 Key Finding block references binary F1=1.000

## Known Stubs

None — all numeric values are locked from the evaluation snapshot (20-CONTEXT.md).

## Threat Flags

None — no new network endpoints, auth paths, file access patterns, or schema changes introduced. Pure LaTeX edits.

## Self-Check: PASSED

- documents/reports/latex/slides/sections/08_evaluation.tex: exists, modified 2026-06-09
- documents/reports/latex/slides/sections/09_confusion.tex: exists, modified 2026-06-09
- documents/reports/latex/slides.pdf: exists, 168,024 bytes
- Commit 58d21a2: confirmed in git log
- Commit 05899ea: confirmed in git log
- slides.log: zero `! ` lines
