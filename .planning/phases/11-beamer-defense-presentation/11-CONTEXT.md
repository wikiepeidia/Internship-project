# Phase 11: Beamer Defense Presentation — Context

**Gathered:** 2026-06-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Produce a defense-ready 16:9 Beamer slide deck for the graduation thesis defense. 13 content slides, ~15-minute talk, calibrated to cover all contributions without opening difficult jury questions. Multi-file structure mirroring thesis, living in `documents/reports/latex/slides/`. Reuses all existing TikZ figures and tables from the thesis without duplication.

</domain>

<decisions>
## Implementation Decisions

### Theme

- **D-01:** Use **Metropolis** Beamer theme (`\usetheme{metropolis}`). Modern, minimal, clean — standard in academic defenses. Needs `beamertheme-metropolis` (included in TeX Live 2016+).
- **D-02:** Aspect ratio **16:9** — `\documentclass[aspectratio=169]{beamer}`.

### Colors

- **D-03:** Primary accent color = **CVBLUE `#1A5276`** — matches thesis. Applied via `\definecolor{CVBLUE}{HTML}{1A5276}` and set as Metropolis `themecolor`. All other colors derive from this token so the full deck recolors in one line.
- **D-04:** Centralize color tokens in a `preamble/colors.tex` file, `\input{}`-ed from `main-slides.tex` before theme setup.

### Slide Structure (13 content slides, ~15 min)

- **D-05:** Locked slide sequence:
  1. Title slide
  2. Agenda
  3. Problem — Vietnamese phishing + privacy gap (why this project exists)
  4. System architecture (reuse TikZ system_overview figure)
  5. Data pipeline — headline numbers only (3,000 corpus, 4 classes, 49/50 quality)
  6. Why local model / not cloud API (Chevrolet / Air Canada / Rufus AI examples, one sentence each)
  7. Model adaptation — QLoRA on Qwen 4B, GGUF export, 13s warm latency
  8. Evaluation results — recall bar chart (reuse TikZ)
  9. Confusion matrix + error finding — bank-naming boundary, one sentence explanation
  10. Live demo — real CLI output (vnphish analyze on Vietcombank message)
  11. Contributions summary — 4 bullet points
  12. Limitations + Future work (image/OCR direction highlighted)
  13. Thank you / Questions

- **D-06:** Slides designed to answer "what did you build and does it work?" — avoid exposing raw training parameters (checkpoint step numbers, loss values) or the 518 filtered rows math, which invite hard follow-up questions.
- **D-07:** Limitations slide is brief (3 bullets max) and positioned after contributions — frames the limitations as "known and controlled" rather than "problems".

### File Organization

- **D-08:** `slides.tex` lives at the **same level as `main.tex`** — i.e., `documents/reports/latex/slides.tex`. This is the Beamer entry point. Thesis entry point remains `main.tex`. Both files share the same `figures/`, `tables/`, `pics/`, and `references.bib` with zero path gymnastics.
- **D-09:** Slide section content lives in `slides/` subdirectory — one `.tex` per logical section:
  ```
  documents/reports/latex/
  ├── main.tex                   ← thesis (unchanged)
  ├── slides.tex                 ← Beamer entry point (NEW)
  ├── references.bib             ← shared by both
  ├── figures/                   ← shared TikZ figures
  ├── tables/                    ← shared tables
  ├── pics/                      ← shared images (usth.png, rufusai.png)
  ├── chapters/                  ← thesis chapters (unchanged)
  └── slides/                    ← slide section files (NEW)
      ├── preamble/
      │   ├── colors.tex         ← CVBLUE token + Metropolis color setup
      │   └── packages.tex       ← Beamer-specific packages
      └── sections/
          ├── 01_title.tex
          ├── 02_agenda.tex
          ├── 03_problem.tex
          ├── 04_architecture.tex
          ├── 05_data.tex
          ├── 06_why_local.tex
          ├── 07_model.tex
          ├── 08_evaluation.tex
          ├── 09_confusion.tex
          ├── 10_demo.tex
          ├── 11_contributions.tex
          └── 12_future.tex
  ```
- **D-10:** All paths in `slides.tex` are identical to `main.tex` — `\input{figures/recall_barchart.tex}`, `\graphicspath{{figures/}{pics/}}`, `\bibliography{references}`. No `../` anywhere. On Overleaf: upload the full `latex/` folder, switch the main document setting between `main.tex` (thesis) and `slides.tex` (presentation).

### Figure and Table Reuse

- **D-11:** Reuse from thesis without copying — `\input{figures/recall_barchart.tex}`, `\input{figures/system_overview_placeholder.tex}`, `\input{tables/confusion_matrix.tex}`. Paths are identical to thesis usage.
- **D-12:** Confusion matrix and evaluation snapshot table may need `\footnotesize` or `\scriptsize` scaling inside Beamer frames to fit 16:9. Planner should handle this per table.
- **D-13:** Recall bar chart TikZ already uses CVBLUE — will match slide colors automatically.

### Presentation Constraints

- **D-14:** Target talk time = 13 minutes (1 slide/min average). 2-minute buffer before jury Q&A starts.
- **D-15:** No animations or overlays that require multiple PDF pages — keep handout-compatible (`\setbeamercovered{invisible}` if overlays used, but prefer static frames).
- **D-16:** Each slide has ONE main point. No walls of text — max 5 bullet points per frame, prefer 3.

</decisions>

<assets>
## Existing Assets for Reuse

| Asset | Path | Used in slide |
|-------|------|--------------|
| System overview TikZ | `figures/system_overview_placeholder.tex` | #4 Architecture |
| Recall bar chart TikZ | `figures/recall_barchart.tex` | #8 Evaluation |
| Cloud vs local flow TikZ | `figures/cloud_vs_local_dataflow.tex` | #6 Why local |
| Confusion matrix table | `../tables/confusion_matrix.tex` | #9 Confusion |
| Evaluation snapshot table | `../tables/evaluation_snapshot.tex` | #8 or appendix |
| Rufus AI screenshot | `pics/rufusai.png` | #6 Why local |
| USTH logo | `pics/usth.png` | #1 Title |
| Real CLI output | verbatim in `10_demo.tex` | #10 Demo |

</assets>

<deferred>
## Deferred Ideas (out of scope for Phase 11)

- Handout PDF with 4-per-page layout — can be added post-defense with `\usepackage{pgfpages}` + `\pgfpagesuselayout{4 on 1}` but not required for Phase 11.
- Animated section transitions — out of scope, keep static for handout compatibility.

</deferred>
</content>
</invoke>