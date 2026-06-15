# Technology Stack: LaTeX Department Template Compliance (v2.2)

**Project:** VN Phishing Detection Thesis — USTH ICT Bachelor Template Reformat
**Milestone:** v2.2 Report Formatting
**Researched:** 2026-06-15
**Scope:** LaTeX packages and commands needed for the five formatting changes ONLY.
  Existing packages (fontspec, titlesec, tocloft, geometry, fancyhdr, natbib, hyperref,
  booktabs, longtable, array, setspace, tikz, enumitem) are treated as already available.

---

## Executive Summary

All five formatting requirements can be implemented with ZERO new LaTeX packages.
Every mechanism is either a plain LaTeX command or an already-loaded package feature
(titlesec, tocloft, natbib). The key insight is that the `report` class chapter/section
machinery can be fully replaced via `\renewcommand` and `\titleformat` without adding
any dependency.

---

## 1. Roman Numeral Section Headings (I/ Introduction, II/ Objectives, …)

### Requirement
Replace "Chapter 1 / Introduction" with "I/ Introduction" at the top level. Department
format uses an uppercase Roman numeral followed by a forward slash, no "Chapter" word.

### Package needed
**None.** titlesec is already loaded.

### Approach
Redefine the chapter counter representation and the chapter title format.

```latex
% In main.tex, AFTER \usepackage{titlesec}

% Step 1: make the chapter counter print as Roman numerals (I, II, III …)
\renewcommand{\thechapter}{\Roman{chapter}}

% Step 2: reformat the chapter heading display
% Format: "I/ Introduction" — bold, centered, no "Chapter" label
\titleformat{\chapter}[block]
  {\normalfont\Large\bfseries\centering}  % font / alignment
  {\thechapter/}                           % label: "I/"
  {0.5em}                                  % sep between label and title
  {}                                        % before-code (nothing)
\titlespacing*{\chapter}{0pt}{-10pt}{12pt}
```

This replaces the existing `\titleformat{\chapter}` line in main.tex (currently line 72).

### TOC impact
tocloft already uses `\thechapter` when building the TOC entry, so the TOC will
automatically read "I Introduction …… 1" once `\thechapter` is changed to `\Roman`.
No tocloft changes required beyond what is already set.

### Cross-reference impact
`\ref{chap:intro}` will now produce "I" instead of "1". The in-text prose in
01_introduction.tex ("Chapter~2 summarizes …", "Chapter~5 reports …") must be updated
to "Section~II", "Section~V", etc., or replaced with `\ref{}` calls. This is a content
edit, not a package change.

### No-new-package path
This IS the no-new-package path. titlesec covers it completely.

---

## 2. List of Abbreviations (2-column glossary table)

### Requirement
A dedicated front-matter page listing abbreviations in a left-aligned abbreviation
column and a right-aligned/left-aligned expansion column.

### Package needed
**None.** longtable + array are already loaded.

### Approach — manual table (recommended for a short list)

Create `chapters/frontmatter/abbreviations.tex`:

```latex
\chapter*{List of Abbreviations}
\addcontentsline{toc}{chapter}{List of Abbreviations}

\begin{longtable}{@{} p{3.2cm} @{\hspace{0.8cm}} p{10.5cm} @{}}
  \toprule
  \textbf{Abbreviation} & \textbf{Definition} \\
  \midrule
  \endhead
  \bottomrule
  \endfoot

  AI       & Artificial Intelligence \\
  API      & Application Programming Interface \\
  BERT     & Bidirectional Encoder Representations from Transformers \\
  CPU      & Central Processing Unit \\
  F1       & Harmonic mean of Precision and Recall \\
  GGUF     & GPT-Generated Unified Format \\
  GPU      & Graphics Processing Unit \\
  ICT      & Information and Communication Technology \\
  LLM      & Large Language Model \\
  LoRA     & Low-Rank Adaptation \\
  NLP      & Natural Language Processing \\
  OTP      & One-Time Password \\
  QLoRA    & Quantized Low-Rank Adaptation \\
  SMS      & Short Message Service \\
  USTH     & University of Science and Technology of Hanoi \\
  XAI      & Explainable Artificial Intelligence \\
\end{longtable}
```

The `@{}` suppresses default longtable left/right padding. `@{\hspace{0.8cm}}`
creates the visual gap between columns without a visible rule. `booktabs` \toprule/
\midrule/\bottomrule give the same ruled style already used in the thesis tables.

### Alternative: `glossaries` package
The `glossaries` package supports auto-sorted abbreviation lists and in-text `\gls{}`
calls. It is significantly heavier (generates auxiliary files, requires `makeglossaries`
or `bib2gls` pass). For a thesis with a static abbreviation list that will not be
referenced inline, the longtable approach is strongly preferred. Do NOT add glossaries
for this use case.

### No-new-package path
longtable + array + booktabs. All already loaded. No new packages.

---

## 3. Supervisor Certification Letter Page

### Requirement
A standalone page with: a "To Whom It May Concern" block-letter header, certification
text, date/location line, and a signature block for the supervisor. No ornamental border
needed (titlepage.tex has a TikZ border; the certification page is typically plain).

### Package needed
**None.** This is a pure layout page using existing geometry/fontspec.

### Approach

Create `chapters/frontmatter/certification.tex`:

```latex
\newpage
\thispagestyle{empty}   % no header/footer on this page

\begin{center}
  {\Large\bfseries SUPERVISOR CERTIFICATION}
\end{center}

\vspace{1.5cm}

\noindent\textbf{To Whom It May Concern,}

\vspace{0.8cm}

\noindent I, \textbf{Giang Anh Tuan}, Internal Supervisor at the Department of
Information and Communication Technology, University of Science and Technology of
Hanoi (USTH), hereby certify that the Bachelor Thesis entitled:

\vspace{0.6cm}

\begin{center}
  \textit{Localized Explainable AI Engine for Vietnamese Financial Phishing Detection}
\end{center}

\vspace{0.6cm}

\noindent was prepared by student \textbf{Phạm Thế Minh} (Student ID: 23BI14279)
under my supervision during the academic year 2025--2026 and fulfills the requirements
for the Bachelor of Science degree in Information and Communication Technology.

\vspace{1.2cm}

\noindent Hanoi, \today

\vspace{2.5cm}

\noindent\begin{tabular}{@{}l@{\hspace{4cm}}l@{}}
  \textbf{Student}      & \textbf{Internal Supervisor} \\[3.5cm]
  Phạm Thế Minh         & Giang Anh Tuan \\
\end{tabular}
```

### Placement in main.tex
Input this immediately after `\input{chapters/frontmatter/titlepage}` and before
the roman-numeral front matter begins.

### XeLaTeX note
fontspec is already active; `\today` in XeLaTeX with `babel[english]` produces
"June 15, 2026" style — acceptable. If a Vietnamese date format is needed, add
`\renewcommand{\today}{ngày ... tháng ... năm ...}` locally on the page.

### No-new-package path
This IS the no-new-package path.

---

## 4. Front Matter Reordering

### Current order (preface.tex)
Abstract → Acknowledgements → TOC → List of Figures → List of Tables

### Required order (department template)
TOC → Acknowledgements → List of Abbreviations → List of Tables → List of Figures → Abstract

### Package needed
**None.** This is a structural edit to preface.tex (and main.tex input ordering).

### New preface.tex structure

```latex
\pagenumbering{roman}

% 1. Table of Contents
{\singlespacing
\tableofcontents
}
\clearpage

% 2. Acknowledgements
\chapter*{Acknowledgements}
\addcontentsline{toc}{chapter}{Acknowledgements}
The author gratefully acknowledges ...

\clearpage

% 3. List of Abbreviations (new file)
\input{chapters/frontmatter/abbreviations}
\clearpage

% 4. List of Tables
{\singlespacing
\addcontentsline{toc}{chapter}{\listtablename}
\listoftables
}
\clearpage

% 5. List of Figures
{\singlespacing
\addcontentsline{toc}{chapter}{\listfigurename}
\listoffigures
}
\clearpage

% 6. Abstract
\chapter*{Abstract}
\addcontentsline{toc}{chapter}{Abstract}
...abstract text...

\cleardoublepage
\pagenumbering{arabic}
```

### tocloft note
The `\addcontentsline{toc}{chapter}{...}` calls for List of Tables and List of
Figures already exist in the current preface.tex. Moving them to a new position
in the file is the entire change required — tocloft configuration in main.tex
does not need editing.

### hyperref note
hyperref's bookmark order mirrors the TOC order. Because TOC now appears first,
the PDF bookmark tree will correctly list: TOC / Acknowledgements / List of
Abbreviations / List of Tables / List of Figures / Abstract. No hyperref option
changes needed.

---

## 5. Appendices Section (APPENDIX 1, APPENDIX 2 headings)

### Requirement
Post-bibliography section with headings "APPENDIX 1", "APPENDIX 2" (not "Appendix A").
Numbered with Arabic numerals, not letters.

### Package needed
**None.** LaTeX's built-in `\appendix` command plus titlesec covers this.

### Approach

```latex
% In main.tex, AFTER \bibliography{references}

\appendix

% Reset chapter counter to arabic numbering for appendices
\renewcommand{\thechapter}{\arabic{chapter}}

% Reformat chapter heading for appendices: "APPENDIX 1" style
\titleformat{\chapter}[block]
  {\normalfont\Large\bfseries\centering}
  {APPENDIX \thechapter}
  {0.5em}
  {}
\titlespacing*{\chapter}{0pt}{-10pt}{12pt}

\input{chapters/appendix_01}
\input{chapters/appendix_02}
```

Then create `chapters/appendix_01.tex`:

```latex
\chapter{Source Code Repository}
\label{app:code}

The full source code is available at: \url{https://github.com/...}

...
```

This produces the heading "APPENDIX 1" followed by the chapter title on the same
or next line. If the department template requires "APPENDIX 1" as the SOLE heading
(no subtitle), pass an empty title:

```latex
\chapter{}   % produces "APPENDIX 1" with no subtitle
```

### TOC appearance
Appendix chapters will appear in the TOC as "APPENDIX 1 Source Code ……  X". If
appendices should be excluded from the TOC entirely:

```latex
\addtocontents{toc}{\protect\setcounter{tocdepth}{-1}}
\appendix
...
\addtocontents{toc}{\protect\setcounter{tocdepth}{1}}
```

### No-new-package path
`\appendix` + `\renewcommand{\thechapter}` + titlesec `\titleformat`. All available.

---

## Summary: Package Delta

| Requirement | New Package | Mechanism |
|---|---|---|
| Roman numeral headings | None | `\renewcommand{\thechapter}{\Roman{chapter}}` + titlesec `\titleformat` |
| List of Abbreviations | None | longtable + array + booktabs (already loaded) |
| Certification letter | None | Plain LaTeX layout, `tabular`, existing geometry |
| Front matter reorder | None | Structural edit to preface.tex input order |
| Appendices section | None | `\appendix` + `\renewcommand{\thechapter}{\arabic{chapter}}` + titlesec |

**Total new packages required: 0**

---

## XeLaTeX Compatibility Notes

- All commands above are XeLaTeX-compatible. `\Roman`, `\arabic`, `\appendix`,
  longtable, titlesec, and tocloft are engine-agnostic.
- fontspec's `\addfontfeatures{LetterSpace=...}` used in titlepage.tex does not
  interact with any of the above changes.
- The `\thispagestyle{empty}` on the certification page suppresses the fancyhdr
  header/footer. This is the correct approach; do not call `\fancyhf{}` locally
  as that would affect the global fancyhdr state.
- When `\pagenumbering{roman}` is active, all front-matter pages get lowercase
  roman page numbers. The certification letter should appear BEFORE
  `\pagenumbering{roman}` (immediately after titlepage) if it must be unnumbered,
  or be given `\thispagestyle{empty}` explicitly.

---

## Integration Checklist for Phase 22

1. main.tex — replace `\titleformat{\chapter}` block (line 72) with Roman version
2. main.tex — add certification input after titlepage input
3. main.tex — add `\appendix` + retitled format + appendix inputs after bibliography
4. preface.tex — reorder sections per Section 4 above; extract abstract and
   acknowledgements text for easier editing if desired
5. NEW: `chapters/frontmatter/certification.tex`
6. NEW: `chapters/frontmatter/abbreviations.tex`
7. NEW: `chapters/appendix_01.tex`, `chapters/appendix_02.tex` (content TBD)
8. Content edits: update all "Chapter X" cross-references in chapter files to
   "Section~\ref{}" or explicit Roman numeral references
