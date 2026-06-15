# Phase 23: Document Restructure and Evaluation Tables - Context

**Gathered:** 2026-06-15
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase restructures the thesis body from six numbered chapters into five department-template Roman numeral sections and adds binary evaluation tables to the results section. It owns `main.tex` section-heading mechanics, body-source inclusion order/content mapping, the three stale prose `Chapter~N` references, and report-side evaluation tables. It must preserve Phase 22 front matter, preserve bibliography behavior, avoid corrupting figure/table numbering, and defer appendices plus slide text sync to Phase 24.

</domain>

<decisions>
## Implementation Decisions

### Structure Mechanics
- Define a local `\thesissection` macro in `main.tex` that renders visible headings as `I/`, `II/`, `III/`, `IV/`, and `V/` without redefining `\thechapter` globally.
- Keep figure/table numbering safe by continuing to let the underlying report `chapter` counter drive captions; do not use `\renewcommand{\thechapter}{\Roman{chapter}}`.
- Prefer minimal package churn. Use existing `titlesec`, `hyperref`, and report-class primitives unless a compile failure proves a new dependency is necessary.
- Keep existing chapter files as source modules where practical, but change their top-level heading calls or create small wrapper files if that is safer for content mapping.

### Content Mapping
- Section I/ Introduction should contain Chapter 1 narrative plus the current Chapter 2 background content.
- Section II/ Objectives should contain the current Chapter 1 objectives rewritten as standalone prose, not as the old introduction bullet list.
- Section III/ Materials and Methods should contain current Chapter 3 methodology plus Chapter 4 implementation content.
- Section IV/ Results and Discussion should contain current Chapter 5 evaluation and discussion content, plus the Phase 20 binary evaluation tables.
- Section V/ Conclusion and Perspective should contain current Chapter 6 conclusion, limitations, and future work content.

### Cross-References and Evaluation Tables
- Replace the three known stale prose references: `01_introduction.tex` report organization line, `04_implementation.tex` Chapter~5 reference, and `06_conclusion_and_future_work.tex` Chapter~5 reference.
- Add a binary per-class metrics table in the results section consistent with Phase 20 slides: Scam vs Non-scam, Precision 1.000, Recall 1.000, F1 1.000, support 193/61 as applicable.
- Add a binary 2x2 confusion matrix in the results section consistent with Phase 20 slides: Scam/Scam = 193, Scam/Non-scam = 0, Non-scam/Scam = 0, Non-scam/Non-scam = 61.
- Keep the existing 4-class evaluation discussion and tables; binary tables supplement them rather than replacing the detailed evidence.

### Autonomous Defaults
- This context was generated through smart discuss in autonomous mode; the agent selected recommended answers from ROADMAP, REQUIREMENTS, STATE, Phase 20 slide files, and current LaTeX source.
- Implementation choices not specified above are at the agent's discretion, with priority order: department template compliance, compile stability, figure/table numbering safety, readable thesis prose, and minimal source churn.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `documents/reports/latex/main.tex` currently inputs six body chapter files after Phase 22 front matter.
- Body chapters currently use `\chapter{...}` at the top of files `01` through `06`.
- `documents/reports/latex/chapters/05_evaluation_and_discussion.tex` already includes 4-class evaluation prose, `tables/evaluation_snapshot`, `figures/recall_barchart`, and `tables/confusion_matrix`.
- Phase 20 slide source contains the binary values: `slides/sections/08_evaluation.tex` has the perfect binary result block, and `slides/sections/09_confusion.tex` has the binary confusion matrix values.

### Established Patterns
- Thesis tables live in `documents/reports/latex/tables/` and are `\input{tables/...}` from chapter files.
- Table style uses `booktabs`, `\cellcolor{CVBLUE!15}`, and labels such as `tab:confusion-matrix`.
- Report compile target is `documents/reports/latex/main.tex` with XeLaTeX and BibTeX.

### Integration Points
- `main.tex` is the best place to define `\thesissection` and drive the five visible thesis sections.
- Evaluation table additions can be separate files under `documents/reports/latex/tables/` and input from `05_evaluation_and_discussion.tex`.
- Existing references to old numbered chapters are literal prose only; no broad label/counter migration should be needed.

</code_context>

<specifics>
## Specific Ideas

Phase 23 must satisfy:
- STRUCT-01: define `\thesissection` macro for Roman numeral headings without corrupting figure/table captions.
- STRUCT-02: map six old chapters into five department sections.
- STRUCT-03: fix three hardcoded `Chapter~N` prose references.
- EVAL-06: add binary per-class metrics table to Section IV.
- EVAL-07: add binary 2x2 confusion matrix to Section IV.

</specifics>

<deferred>
## Deferred Ideas

Appendices and defense-slide `Chapter X` scan/update are deferred to Phase 24. Do not add appendices or edit slide sources in this phase.

</deferred>
