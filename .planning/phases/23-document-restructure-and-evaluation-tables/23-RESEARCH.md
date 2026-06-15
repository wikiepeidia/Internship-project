# Phase 23: Document Restructure and Evaluation Tables - Research

**Researched:** 2026-06-15  
**Domain:** Local LaTeX thesis restructuring, report-class counters, evaluation table synchronization  
**Confidence:** HIGH - findings are from local project files, phase artifacts, grep scans, and local tool probes. [VERIFIED: local files + local command probes]

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

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

### the agent's Discretion
Implementation choices not specified above are at the agent's discretion, with priority order: department template compliance, compile stability, figure/table numbering safety, readable thesis prose, and minimal source churn.

### Deferred Ideas (OUT OF SCOPE)

## Deferred Ideas

Appendices and defense-slide `Chapter X` scan/update are deferred to Phase 24. Do not add appendices or edit slide sources in this phase.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| STRUCT-01 | Define `\thesissection` macro for Roman numeral headings without corrupting figure/table captions. | Use a macro that steps the underlying `chapter` counter but never redefines `\thechapter`; figure/table captions therefore retain Arabic chapter numbering. [VERIFIED: 23-CONTEXT.md + main.tex] |
| STRUCT-02 | Map six old chapters into five department-template Roman numeral sections. | Drive five visible sections from `main.tex`, remove body-file `\chapter{}` calls, create one small objectives source file, and reuse existing chapter modules. [VERIFIED: 23-CONTEXT.md + chapter source grep] |
| STRUCT-03 | Fix three hardcoded prose chapter references. | `rg` found exactly three compiled body references in `01_introduction.tex`, `04_implementation.tex`, and `06_conclusion_and_future_work.tex`; update to section prose or `\ref{}`-style wording. [VERIFIED: local `rg`] |
| EVAL-06 | Add binary per-class metrics table to Section IV. | Add a new report table with Scam and Non-scam rows, both Precision/Recall/F1 = 1.000, supports 193 and 61. [VERIFIED: 20-CONTEXT.md + 20-01-SUMMARY.md] |
| EVAL-07 | Add binary 2x2 confusion matrix to Section IV. | Add a new report table with TP=193, TN=61, FP=0, FN=0. [VERIFIED: 20-CONTEXT.md + 20-01-SUMMARY.md] |
</phase_requirements>

## Summary

Phase 23 is a local LaTeX-only report phase with no package installation and no web research requirement. [VERIFIED: user prompt + 23-CONTEXT.md] The correct implementation is to keep `report` class chapter numbering internally Arabic for counters and captions, while rendering visible thesis-body headings as Roman template sections through a new `\thesissection` macro in `main.tex`. [VERIFIED: 23-CONTEXT.md + main.tex]

The safest source layout is to keep existing body files as modules, remove their top-level `\chapter{...}` calls, and let `main.tex` own the five department sections. [VERIFIED: chapter source grep + 23-CONTEXT.md] The only new body source recommended is `chapters/02_objectives.tex`, because Chapter 1 objectives must be isolated and rewritten as Section II prose rather than left as an old bullet list inside Section I. [VERIFIED: 01_introduction.tex + 23-CONTEXT.md]

The Phase 20 binary values are resolved: the current `08_evaluation.tex` and `09_confusion.tex` files show the detailed four-class table/matrix, but Phase 20 context and summary explicitly define the binary roll-up as TP=193, TN=61, FP=0, FN=0 and binary Precision/Recall/F1=1.000. [VERIFIED: current slide files + 20-CONTEXT.md + 20-01-SUMMARY.md] Use those Phase 20 artifacts as the report-side source of truth and add binary tables as supplements to the existing four-class report evidence. [VERIFIED: 23-CONTEXT.md + 20-CONTEXT.md]

**Primary recommendation:** Edit `main.tex`, all six body chapter files, add `chapters/02_objectives.tex`, add two report table files under `tables/`, then run clean XeLaTeX/BibTeX/XeLaTeX/XeLaTeX verification from `documents/reports/latex/`. [VERIFIED: local files + STATE.md + local compiler probes]

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Roman visible thesis sections | LaTeX document structure | Body chapter modules | `main.tex` owns package setup and body inclusion order, so it should own the macro and five section boundaries. [VERIFIED: main.tex + 23-CONTEXT.md] |
| Figure/table numbering preservation | LaTeX counters | Caption rendering | Captions derive from the underlying chapter counter, so the macro must not redefine `\thechapter`. [VERIFIED: 23-CONTEXT.md + main.tex] |
| Objective rewrite | Body chapter prose | `main.tex` inclusion order | Existing objectives live in `01_introduction.tex`; Phase 23 requires them as standalone Section II prose. [VERIFIED: 01_introduction.tex + 23-CONTEXT.md] |
| Binary report tables | Report table sources | Evaluation chapter | Existing report tables live in `documents/reports/latex/tables/` and are included from Chapter 5/Section IV. [VERIFIED: table file listing + 05_evaluation_and_discussion.tex] |
| Compile verification | Local LaTeX toolchain | Generated aux files | Local XeLaTeX and BibTeX are installed; clean aux removal prevents stale TOC/list/reference state from hiding regressions. [VERIFIED: local `xelatex --version` + `bibtex --version` + STATE.md] |

## Standard Stack

### Core

| Library / Tool | Version | Purpose | Why Standard |
|----------------|---------|---------|--------------|
| LaTeX `report` class | Built into current manuscript | Chapter counter, body structure, figure/table numbering. | Existing `main.tex` uses `\documentclass[11pt,a4paper]{report}`; preserving this avoids template churn. [VERIFIED: main.tex] |
| XeLaTeX / MiKTeX-XeTeX | 4.18 (MiKTeX 26.5) | Compile Unicode thesis with `fontspec` and Times New Roman. | Existing manuscript declares XeLaTeX and uses `fontspec`; local compiler is installed. [VERIFIED: main.tex + local `xelatex --version`] |
| BibTeX / MiKTeX-BibTeX | 4.2 (MiKTeX 26.5) | Rebuild bibliography after structure changes. | Existing `main.tex` uses `natbib`, `ieeetr`, and `\bibliography{references}`. [VERIFIED: main.tex + local `bibtex --version`] |
| `titlesec` | Installed via MiKTeX | Existing heading spacing/formatting support. | Current preamble already loads `titlesec`; no new heading package is needed. [VERIFIED: main.tex + local `kpsewhich titlesec.sty`] |
| `booktabs` | Installed via MiKTeX | Professional evaluation and confusion tables. | Existing tables already use `\toprule`, `\midrule`, and `\bottomrule`. [VERIFIED: main.tex + local `kpsewhich booktabs.sty` + tables/confusion_matrix.tex] |
| `xcolor` with table option | Installed via MiKTeX | `CVBLUE` and `\cellcolor{CVBLUE!15}` table highlights. | Existing report confusion matrix uses `\cellcolor{CVBLUE!15}` and preamble loads `\usepackage[table]{xcolor}`. [VERIFIED: main.tex + local `kpsewhich xcolor.sty` + tables/confusion_matrix.tex] |
| `hyperref` | Installed via MiKTeX | TOC links and anchors after manual section entries. | Existing preamble already loads `hyperref`; `\phantomsection` is available for manual TOC entries. [VERIFIED: main.tex + local `kpsewhich hyperref.sty`] |

### Supporting

| Library / Tool | Version | Purpose | When to Use |
|----------------|---------|---------|-------------|
| `rg` | Available in shell session | Locate stale chapter prose references and verify source changes. | Use before and after edits for `Chapter~N` / `Chapter N` scans. [VERIFIED: local `rg` output] |
| Existing generated aux files | Present after Phase 22 compile | Evidence of current build state, not source of truth. | Delete before final verification so TOC/list/reference state regenerates from edited source. [VERIFIED: local `Get-ChildItem main.*` + STATE.md] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `\thesissection` with manual visible heading | `\renewcommand{\thechapter}{\Roman{chapter}}` | Rejected because it would make figure/table numbering Roman-prefixed, contrary to Phase 23 constraints. [VERIFIED: 23-CONTEXT.md + STATE.md] |
| Reusing old `\chapter{}` calls in body files | `\chapter[...]{I/ Introduction}` | Rejected because default chapter title formatting would still render `Chapter 1` unless more global formatting is changed. [VERIFIED: main.tex heading format] |
| Replacing the existing four-class matrix | Add binary tables as supplements | Rejected because Phase 23 explicitly says keep detailed four-class evaluation discussion and tables. [VERIFIED: 23-CONTEXT.md] |

**Installation:**

```bash
# No npm, pip, cargo, or new LaTeX package install is required for Phase 23.
```

## Package Legitimacy Audit

No external package-manager dependencies are installed in this phase. [VERIFIED: user prompt + 23-CONTEXT.md] Existing MiKTeX LaTeX packages are already available locally via `kpsewhich`. [VERIFIED: local `kpsewhich titlesec.sty booktabs.sty xcolor.sty hyperref.sty` probes]

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| none | n/a | n/a | n/a | n/a | OK | No install planned. [VERIFIED: 23-CONTEXT.md] |

**Packages removed due to [SLOP] verdict:** none. [VERIFIED: no package install planned]  
**Packages flagged as suspicious [SUS]:** none. [VERIFIED: no package install planned]

## Architecture Patterns

### System Architecture Diagram

```text
main.tex
  |
  |-- preamble: existing packages + new \thesissection macro
  |
  |-- front matter inputs from Phase 22
  |
  |-- \thesissection{Introduction}
  |     |-- input chapters/01_introduction.tex without objectives/chapter command
  |     `-- input chapters/02_related_work_and_background.tex without chapter command
  |
  |-- \thesissection{Objectives}
  |     `-- input chapters/02_objectives.tex rewritten from old Ch1 objectives
  |
  |-- \thesissection{Materials and Methods}
  |     |-- input chapters/03_methodology_and_system_design.tex without chapter command
  |     `-- input chapters/04_implementation.tex without chapter command
  |
  |-- \thesissection{Results and Discussion}
  |     `-- input chapters/05_evaluation_and_discussion.tex
  |           |-- existing four-class evidence
  |           |-- input tables/binary_metrics.tex
  |           `-- input tables/binary_confusion_matrix.tex
  |
  `-- \thesissection{Conclusion and Perspective}
        `-- input chapters/06_conclusion_and_future_work.tex without chapter command
```

This data flow keeps section ownership in `main.tex`, prose ownership in chapter modules, and table ownership under `tables/`. [VERIFIED: main.tex + chapter files + table file listing]

### Recommended Project Structure

```text
documents/reports/latex/
├── main.tex
├── chapters/
│   ├── 01_introduction.tex
│   ├── 02_objectives.tex                  # new
│   ├── 02_related_work_and_background.tex
│   ├── 03_methodology_and_system_design.tex
│   ├── 04_implementation.tex
│   ├── 05_evaluation_and_discussion.tex
│   └── 06_conclusion_and_future_work.tex
└── tables/
    ├── binary_metrics.tex                 # new
    ├── binary_confusion_matrix.tex         # new
    └── confusion_matrix.tex
```

The new files should be limited to the objectives rewrite and two binary tables; existing source modules should otherwise be reused. [VERIFIED: 23-CONTEXT.md + local file listing]

### Pattern 1: Safe `\thesissection` Macro

**What:** Define a body-section command that advances the underlying `chapter` counter, resets dependent counters through normal counter stepping, writes a Roman visible heading, and leaves `\thechapter` Arabic for figures/tables. [VERIFIED: 23-CONTEXT.md + main.tex]

**When to use:** Use exactly five times in `main.tex` for the department-template body sections. [VERIFIED: REQUIREMENTS.md + 23-CONTEXT.md]

**Example:**

```latex
% Source: local research recommendation from main.tex/report-class constraints
\newcommand{\thesissection}[1]{%
  \clearpage
  \refstepcounter{chapter}%
  \phantomsection
  \addcontentsline{toc}{chapter}{\Roman{chapter}/ #1}%
  \markboth{\MakeUppercase{\Roman{chapter}/ #1}}{}%
  \thispagestyle{plain}%
  \vspace*{-20pt}%
  {\normalfont\Large\bfseries \Roman{chapter}/ #1\par}%
  \vspace{10pt}%
}
```

This macro does not call `\renewcommand{\thechapter}{...}` and therefore keeps captions such as Figure 3.1/Table 4.1 rather than Figure III.1/Table IV.1. [VERIFIED: 23-CONTEXT.md + STATE.md]

### Pattern 2: Five-Section Inclusion Order

**What:** Let `main.tex` own section boundaries and include existing content modules below each boundary. [VERIFIED: main.tex + 23-CONTEXT.md]

**When to use:** Use after Phase 22 front matter and before the bibliography block. [VERIFIED: main.tex]

**Example:**

```latex
\thesissection{Introduction}
\input{chapters/01_introduction}
\input{chapters/02_related_work_and_background}

\thesissection{Objectives}
\input{chapters/02_objectives}

\thesissection{Materials and Methods}
\input{chapters/03_methodology_and_system_design}
\input{chapters/04_implementation}

\thesissection{Results and Discussion}
\input{chapters/05_evaluation_and_discussion}

\thesissection{Conclusion and Perspective}
\input{chapters/06_conclusion_and_future_work}
```

The body files should not retain their top-level `\chapter{...}` commands after this inclusion order is introduced. [VERIFIED: chapter source grep + 23-CONTEXT.md]

### Pattern 3: Binary Tables as Additive Evidence

**What:** Add two new report table files and input them near the existing four-class results in `05_evaluation_and_discussion.tex`. [VERIFIED: 05_evaluation_and_discussion.tex + 23-CONTEXT.md]

**When to use:** Place after the current four-class confusion matrix or immediately after its explanatory paragraph so readers see both class-granular and binary-superclass interpretations. [VERIFIED: 05_evaluation_and_discussion.tex + 20-CONTEXT.md]

**Example:**

```latex
\input{figures/recall_barchart}
\input{tables/confusion_matrix}
\input{tables/binary_metrics}
\input{tables/binary_confusion_matrix}
```

Using separate table files matches existing report table organization and avoids overloading `confusion_matrix.tex`. [VERIFIED: table file listing + 23-CONTEXT.md]

### Anti-Patterns to Avoid

- **Global Roman chapter counter:** Do not use `\renewcommand{\thechapter}{\Roman{chapter}}`; it risks Roman figure/table prefixes. [VERIFIED: 23-CONTEXT.md + STATE.md]
- **Duplicating objectives:** Do not leave the old objectives bullet list in Section I and also create Section II; Section II must own the objectives prose. [VERIFIED: 01_introduction.tex + 23-CONTEXT.md]
- **Replacing four-class evidence:** Do not remove the existing `evaluation_snapshot`, recall chart, or four-class confusion matrix; binary tables supplement them. [VERIFIED: 05_evaluation_and_discussion.tex + 23-CONTEXT.md]
- **Editing slides in Phase 23:** Do not edit slide files in this phase; slide sync is Phase 24 scope. [VERIFIED: 23-CONTEXT.md + REQUIREMENTS.md]
- **Relying on stale aux files:** Do not validate TOC/list/reference behavior without deleting `main.aux`, `main.toc`, `main.lot`, `main.lof`, and related outputs first. [VERIFIED: STATE.md + local build artifact listing]

## Exact Source Files Likely Modified or Added

| Path | Action | Reason |
|------|--------|--------|
| `documents/reports/latex/main.tex` | Modify | Add `\thesissection` macro and replace six body inputs with five Roman section blocks. [VERIFIED: main.tex + 23-CONTEXT.md] |
| `documents/reports/latex/chapters/01_introduction.tex` | Modify | Remove top-level `\chapter{Introduction}`, remove/isolate old objectives list, and rewrite report organization references. [VERIFIED: 01_introduction.tex + local `rg`] |
| `documents/reports/latex/chapters/02_objectives.tex` | Add | New standalone Section II prose derived from old Chapter 1 objectives. [VERIFIED: 01_introduction.tex + 23-CONTEXT.md] |
| `documents/reports/latex/chapters/02_related_work_and_background.tex` | Modify | Remove top-level `\chapter{Related Work and Background}` so it sits under Section I. [VERIFIED: 02_related_work_and_background.tex + 23-CONTEXT.md] |
| `documents/reports/latex/chapters/03_methodology_and_system_design.tex` | Modify | Remove top-level `\chapter{Methodology and System Design}` so it sits under Section III. [VERIFIED: 03_methodology_and_system_design.tex + 23-CONTEXT.md] |
| `documents/reports/latex/chapters/04_implementation.tex` | Modify | Remove top-level `\chapter{Implementation}` and update the stale Chapter 5 prose reference. [VERIFIED: 04_implementation.tex + local `rg`] |
| `documents/reports/latex/chapters/05_evaluation_and_discussion.tex` | Modify | Remove top-level `\chapter{Evaluation and Discussion}` and input the two new binary tables. [VERIFIED: 05_evaluation_and_discussion.tex + 23-CONTEXT.md] |
| `documents/reports/latex/chapters/06_conclusion_and_future_work.tex` | Modify | Remove top-level `\chapter{Conclusion and Future Work}`, update heading terminology to Conclusion and Perspective if desired, and fix stale Chapter 5 prose reference. [VERIFIED: 06_conclusion_and_future_work.tex + local `rg`] |
| `documents/reports/latex/tables/binary_metrics.tex` | Add | Report-side binary per-class metrics table required by EVAL-06. [VERIFIED: 23-CONTEXT.md + 20-CONTEXT.md] |
| `documents/reports/latex/tables/binary_confusion_matrix.tex` | Add | Report-side binary 2x2 confusion matrix required by EVAL-07. [VERIFIED: 23-CONTEXT.md + 20-CONTEXT.md] |

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Chapter counter mechanics | A custom integer state variable for section numbers | LaTeX `chapter` counter via `\refstepcounter{chapter}` | Built-in counter stepping handles dependent counter resets for figures/tables/equations. [VERIFIED: LaTeX report pattern inferred from current source + 23-CONTEXT.md] |
| Table styling | Manual spaces, lines, or image tables | Existing `booktabs` tables | Current report tables already use `booktabs` and compile under the current preamble. [VERIFIED: tables/confusion_matrix.tex + main.tex] |
| Binary metrics | Re-run model evaluation or recalculate from raw predictions | Phase 20 locked roll-up values | Phase 20 defines binary metrics as analytically derived from the existing four-class matrix; no code execution is required. [VERIFIED: 20-CONTEXT.md] |
| Slide synchronization | Edit slides in this phase | Defer to Phase 24 | Phase 23 context explicitly defers slide text sync. [VERIFIED: 23-CONTEXT.md] |

**Key insight:** The phase is structurally risky because visible heading format and semantic counters are not the same thing in LaTeX; changing the counter representation globally is the wrong lever. [VERIFIED: 23-CONTEXT.md + STATE.md]

## Runtime State Inventory

> Included because Phase 23 is a document restructure/refactor phase. [VERIFIED: phase scope]

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None - Phase 23 edits static LaTeX source and generated PDF/aux files only. [VERIFIED: 23-CONTEXT.md + local file listing] | No data migration. [VERIFIED: phase scope] |
| Live service config | None - no external service or UI-stored configuration participates in thesis compilation. [VERIFIED: user prompt + 23-CONTEXT.md] | No service config update. [VERIFIED: phase scope] |
| OS-registered state | None - no Windows task, service, or package registration is changed by report source edits. [VERIFIED: phase scope] | No OS registration update. [VERIFIED: phase scope] |
| Secrets/env vars | None - no secret or environment variable is read by the LaTeX compile path. [VERIFIED: main.tex + phase scope] | No secret/env update. [VERIFIED: phase scope] |
| Build artifacts | `main.aux`, `main.bbl`, `main.blg`, `main.lof`, `main.log`, `main.lot`, `main.out`, `main.pdf`, and `main.toc` exist from the Phase 22 compile. [VERIFIED: local `Get-ChildItem documents/reports/latex/main.*`] | Delete stale aux/list/log files before final compile; regenerate PDF through XeLaTeX/BibTeX sequence. [VERIFIED: STATE.md] |

## Common Pitfalls

### Pitfall 1: Roman Headings Corrupt Figure/Table Numbering

**What goes wrong:** Figure/table captions change from Arabic chapter prefixes to Roman prefixes. [VERIFIED: 23-CONTEXT.md + STATE.md]  
**Why it happens:** A global `\thechapter` redefinition affects all places that read the chapter counter, including `\thefigure` and `\thetable`. [VERIFIED: 23-CONTEXT.md]  
**How to avoid:** Use `\thesissection` for visible headings only and leave `\thechapter` unchanged. [VERIFIED: 23-CONTEXT.md]  
**Warning signs:** Compiled captions show `Figure III.1` or `Table IV.1` instead of `Figure 3.1` or `Table 4.1`. [VERIFIED: 23-CONTEXT.md]

### Pitfall 2: Objectives Remain in the Introduction

**What goes wrong:** Section II exists but the old objective bullet list remains under Section I. [VERIFIED: 01_introduction.tex + 23-CONTEXT.md]  
**Why it happens:** The objectives are currently embedded in `01_introduction.tex` under `\section{Objectives and Scope}`. [VERIFIED: 01_introduction.tex]  
**How to avoid:** Move the objective content into new `chapters/02_objectives.tex` and rewrite it as prose. [VERIFIED: 23-CONTEXT.md]  
**Warning signs:** `01_introduction.tex` still contains `\section{Objectives and Scope}` or `\begin{itemize}` with the four implemented objectives after the restructure. [VERIFIED: 01_introduction.tex]

### Pitfall 3: Stale Chapter Prose Survives the Restructure

**What goes wrong:** Body prose still says `Chapter~5` or `Chapter~6` after visible headings are Roman sections. [VERIFIED: local `rg`]  
**Why it happens:** The stale references are literal prose, not LaTeX cross-references. [VERIFIED: local `rg`]  
**How to avoid:** Run `rg -n "Chapter~[0-9]|Chapter [0-9]|chapter~[0-9]|chapter [0-9]" documents/reports/latex/chapters documents/reports/latex/main.tex` before and after edits. [VERIFIED: local `rg`]  
**Warning signs:** The grep command returns any compiled body source after edits. [VERIFIED: local `rg`]

### Pitfall 4: Binary Slide Values Are Treated as Missing

**What goes wrong:** The planner stalls because the current slide files show the four-class table/matrix rather than an explicit binary block. [VERIFIED: current 08_evaluation.tex + 09_confusion.tex]  
**Why it happens:** Phase 20 context and summary record the binary roll-up, while the current slide source in the working tree only shows detailed four-class content. [VERIFIED: 20-CONTEXT.md + 20-01-SUMMARY.md + current slide files]  
**How to avoid:** Use Phase 20 context/summary as authoritative for binary values and state the derivation in report prose. [VERIFIED: 20-CONTEXT.md + 20-01-SUMMARY.md]  
**Warning signs:** Binary table values are omitted or a model re-run is proposed. [VERIFIED: 20-CONTEXT.md]

## Code Examples

### Binary Metrics Table

```latex
% Source: 20-CONTEXT.md + 20-01-SUMMARY.md
\begin{table}[H]
\centering
\caption{Binary scam versus non-scam metrics derived from the internal holdout evaluation.}
\label{tab:binary-metrics}
\setlength{\tabcolsep}{8pt}
\renewcommand{\arraystretch}{1.2}
\begin{tabular}{lcccc}
\toprule
\textbf{Class} & \textbf{Precision} & \textbf{Recall} & \textbf{F1-score} & \textbf{Support} \\
\midrule
Scam     & 1.000 & 1.000 & 1.000 & 193 \\
Non-scam & 1.000 & 1.000 & 1.000 & 61 \\
\midrule
\textbf{Accuracy} & \multicolumn{3}{c}{\textbf{1.000}} & \textbf{254} \\
\bottomrule
\end{tabular}
\end{table}
```

The support values come from collapsing 56 bank impersonation, 75 Zalo social engineering, and 62 task scam rows into Scam, plus 61 benign rows into Non-scam. [VERIFIED: 20-CONTEXT.md + current 08_evaluation.tex]

### Binary Confusion Matrix

```latex
% Source: 20-CONTEXT.md + 20-01-SUMMARY.md
\begin{table}[H]
\centering
\caption{Binary confusion matrix after collapsing all threat classes into Scam.}
\label{tab:binary-confusion-matrix}
\setlength{\tabcolsep}{10pt}
\renewcommand{\arraystretch}{1.3}
\begin{tabular}{lcc}
\toprule
\textbf{True Class \textbackslash\ Predicted} & \textbf{Scam} & \textbf{Non-scam} \\
\midrule
Scam     & \cellcolor{CVBLUE!15}\textbf{193} & 0 \\
Non-scam & 0 & \cellcolor{CVBLUE!15}\textbf{61} \\
\bottomrule
\end{tabular}
\end{table}
```

The binary matrix records no scam-to-benign or benign-to-scam crossings. [VERIFIED: 20-CONTEXT.md + 20-01-SUMMARY.md]

### Chapter Reference Fix Strategy

| File | Current Reference | Recommended Replacement |
|------|-------------------|-------------------------|
| `chapters/01_introduction.tex:22` | Six-sentence `Chapter~2` through `Chapter~6` organization paragraph. [VERIFIED: local `rg`] | Rewrite as Roman-section organization prose: Section I introduces the motivation/background, Section II states objectives, Section III describes materials/methods, Section IV reports results/discussion, and Section V concludes with perspective. [VERIFIED: 23-CONTEXT.md] |
| `chapters/04_implementation.tex:126` | `discussed in Chapter~5` [VERIFIED: local `rg`] | Replace with `discussed in Section IV` or `discussed in the Results and Discussion section`. [VERIFIED: 23-CONTEXT.md] |
| `chapters/06_conclusion_and_future_work.tex:20` | `The error analysis in Chapter~5 shows...` [VERIFIED: local `rg`] | Replace with `The error analysis in Section IV shows...` or `The error analysis in the Results and Discussion section shows...`. [VERIFIED: 23-CONTEXT.md] |

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Six numbered report chapters in `main.tex` | Five visible Roman thesis sections via `\thesissection` | Phase 23 | Satisfies department-template structure while preserving report-class counters. [VERIFIED: REQUIREMENTS.md + 23-CONTEXT.md] |
| Four-class report evidence only | Four-class evidence plus binary scam/non-scam report tables | Phase 23, based on Phase 20 | Adds supervisor-requested binary framing without removing granular error analysis. [VERIFIED: 20-CONTEXT.md + 23-CONTEXT.md] |
| Literal `Chapter~N` prose references | Roman section prose | Phase 23 | Prevents stale wording after visible section restructure. [VERIFIED: local `rg` + 23-CONTEXT.md] |

**Deprecated/outdated:**
- `\chapter{...}` at the top of body modules is outdated for Phase 23 because `main.tex` should own the five visible section boundaries. [VERIFIED: chapter source grep + 23-CONTEXT.md]
- Literal `Chapter~N` prose in compiled body source is outdated after the restructure. [VERIFIED: local `rg`]
- Slide-source edits are out of date for Phase 23 scope and belong to Phase 24. [VERIFIED: 23-CONTEXT.md + REQUIREMENTS.md]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `\refstepcounter{chapter}` is the right primitive for the macro because it steps the chapter counter and resets dependent counters without formatting a default chapter heading. [ASSUMED] | Architecture Patterns | If wrong, the executor may need to switch to a locally patched `\chapter` wrapper after compile verification reveals counter/reset problems. |

All other phase-specific claims are verified from local files or local command probes. [VERIFIED: local files + local probes]

## Open Questions

None - resolved during research. [VERIFIED: 23-CONTEXT.md + 20-CONTEXT.md + current source scans]

Resolved items:
- Binary values are authoritative from Phase 20 context/summary even though current slide files show the four-class table/matrix. [VERIFIED: 20-CONTEXT.md + 20-01-SUMMARY.md + current slide files]
- The only compiled body-source `Chapter~N` references are the three known locations. [VERIFIED: local `rg`]
- Phase 23 should not edit appendices or slide sources. [VERIFIED: 23-CONTEXT.md]

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| XeLaTeX / MiKTeX-XeTeX | Thesis compile | yes | 4.18 (MiKTeX 26.5) | Overleaf XeLaTeX if local compile fails. [VERIFIED: local `xelatex --version` + main.tex] |
| BibTeX / MiKTeX-BibTeX | Bibliography pass | yes | 4.2 (MiKTeX 26.5) | Overleaf BibTeX if local compile fails. [VERIFIED: local `bibtex --version` + main.tex] |
| `titlesec.sty` | Existing heading setup | yes | installed via MiKTeX | Avoid new heading dependencies. [VERIFIED: local `kpsewhich titlesec.sty`] |
| `booktabs.sty` | New binary tables | yes | installed via MiKTeX | Existing table style already depends on it. [VERIFIED: local `kpsewhich booktabs.sty`] |
| `xcolor.sty` | Table cell highlights | yes | installed via MiKTeX | Remove `\cellcolor` highlights if a remote compiler lacks table xcolor support. [VERIFIED: local `kpsewhich xcolor.sty` + main.tex] |
| `hyperref.sty` | TOC anchors for manual entries | yes | installed via MiKTeX | Compile without manual `\phantomsection` only if hyperref behavior conflicts. [VERIFIED: local `kpsewhich hyperref.sty` + main.tex] |

**Missing dependencies with no fallback:** none. [VERIFIED: local tool probes]  
**Missing dependencies with fallback:** none. [VERIFIED: local tool probes]

## Validation Architecture

Skipped because `.planning/config.json` explicitly sets `workflow.nyquist_validation` to `false`. [VERIFIED: .planning/config.json]

## Security Domain

Security enforcement is not explicitly disabled in `.planning/config.json`, so the security domain is included. [VERIFIED: .planning/config.json]

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | no | Static LaTeX source has no authentication flow. [VERIFIED: phase scope] |
| V3 Session Management | no | Static LaTeX source has no sessions. [VERIFIED: phase scope] |
| V4 Access Control | no | Phase 23 does not change application authorization behavior. [VERIFIED: phase scope] |
| V5 Input Validation | yes | Treat LaTeX source as trusted static project input; compile with `-interaction=nonstopmode` and inspect log for fatal errors. [VERIFIED: 23-CONTEXT.md + Phase 22 compile pattern] |
| V6 Cryptography | no | Phase 23 does not introduce cryptographic code. [VERIFIED: phase scope] |

### Known Threat Patterns for Local LaTeX Restructure

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Malformed LaTeX causing compile failure | Denial of Service | Run clean XeLaTeX/BibTeX/XeLaTeX/XeLaTeX sequence and scan `main.log` for fatal errors. [VERIFIED: STATE.md + local compiler availability] |
| Stale aux files hiding TOC/reference bugs | Tampering | Delete generated aux/list/log files before final compile. [VERIFIED: STATE.md + local build artifact listing] |
| Accidental scope expansion into slides/appendices | Tampering | Verify changed file list excludes slide sources and appendices in Phase 23. [VERIFIED: 23-CONTEXT.md] |

## Compile Sequence and Risks

Run from `documents/reports/latex/`: [VERIFIED: STATE.md + Phase 22 research/plan pattern]

```powershell
Remove-Item -ErrorAction SilentlyContinue main.aux,main.bbl,main.blg,main.lof,main.log,main.lot,main.out,main.toc
xelatex -interaction=nonstopmode main.tex
bibtex main
xelatex -interaction=nonstopmode main.tex
xelatex -interaction=nonstopmode main.tex
```

After compile, scan `main.log` for `Fatal error`, `Emergency stop`, `Undefined control sequence`, and `LaTeX Error`. [VERIFIED: Phase 22 verification pattern] Also inspect generated captions for Arabic prefixes such as `Figure 3.1` and `Table 4.1`, not Roman prefixes. [VERIFIED: 23-CONTEXT.md]

Key risks:
- The custom macro may need a small adjustment if TOC hyperlinks point to the wrong vertical location. [ASSUMED]
- Removing body `\chapter{}` lines changes section numbering density; compile and visual review should confirm section headings remain readable. [VERIFIED: chapter source grep + 23-CONTEXT.md]
- Current slide source lacks the explicit binary block despite Phase 20 summary saying it was added; do not use current slide source alone as the binary source of truth. [VERIFIED: current slide files + 20-01-SUMMARY.md]

## Sources

### Primary (HIGH confidence)
- `.planning/phases/23-document-restructure-and-evaluation-tables/23-CONTEXT.md` - phase boundary, locked decisions, deferred scope, table values. [VERIFIED: local file read]
- `.planning/REQUIREMENTS.md` - STRUCT-01/02/03 and EVAL-06/07 requirement definitions. [VERIFIED: local file read]
- `.planning/STATE.md` - locked LaTeX safety constraints and compile sequence. [VERIFIED: local file read]
- `.planning/phases/20-binary-eval-slides/20-CONTEXT.md` - binary metric derivation and values. [VERIFIED: local file read]
- `.planning/phases/20-binary-eval-slides/20-01-SUMMARY.md` - executed Phase 20 binary table/matrix summary. [VERIFIED: local file read]
- `documents/reports/latex/main.tex` - current preamble, body input order, packages. [VERIFIED: local file read]
- `documents/reports/latex/chapters/*.tex` - current body headings, objectives, stale references, evaluation insertion point. [VERIFIED: local file read + local `rg`]
- Local command probes - `xelatex --version`, `bibtex --version`, `kpsewhich titlesec.sty`, `kpsewhich booktabs.sty`, `kpsewhich xcolor.sty`, `kpsewhich hyperref.sty`. [VERIFIED: local command probes]

### Secondary (MEDIUM confidence)
- None - no web or secondary source was needed for this local LaTeX phase. [VERIFIED: user prompt]

### Tertiary (LOW confidence)
- LaTeX primitive behavior of `\refstepcounter{chapter}` as the preferred manual macro primitive is marked in the assumptions log. [ASSUMED]

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - existing local compiler and package availability were probed directly. [VERIFIED: local command probes]
- Architecture: HIGH - phase context locks the macro approach and source files confirm current structure. [VERIFIED: 23-CONTEXT.md + local source reads]
- Pitfalls: HIGH for phase-specific pitfalls from locked context and grep; LOW only for the macro primitive assumption until compile-verified. [VERIFIED: 23-CONTEXT.md + local `rg`; ASSUMED for primitive behavior]

**Research date:** 2026-06-15  
**Valid until:** 2026-07-15 for this static local LaTeX structure, unless Phase 23 implementation changes the source layout first. [ASSUMED]
