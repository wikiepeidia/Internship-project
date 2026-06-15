# Phase 22: Cover Page, Certification Letter, and Front Matter - Research

**Researched:** 2026-06-15
**Domain:** Local LaTeX thesis front matter
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

## Implementation Decisions

### Department Template Fidelity
- Use the department-required thesis label `BACHELOR THESIS` and replace the current `Prepared By` block with an explicit `By Phạm Thế Minh` and `Title: ...` layout while preserving USTH/ICT identity, supervisors, student ID, and date.
- Keep the existing border, USTH logo, Times New Roman font, and current geometry unless the department-template fields require local spacing adjustments.
- Add the supervisor certification as its own unnumbered page immediately after the titlepage and before roman front matter starts.
- Use plain formal certification wording beginning with `To whom it may concern` and naming the student, thesis title, department, and supervisors; leave signature/date lines suitable for final manual completion.

### Front Matter Structure
- Make `preface.tex` own the entire front matter sequence after certification: table of contents, acknowledgements, list of abbreviations, list of tables, list of figures, abstract.
- Start roman page numbering after the certification page so the certification remains unnumbered and outside the roman front matter sequence.
- Add each unnumbered front matter chapter to the table of contents deliberately where appropriate.
- Preserve the existing transition to arabic numbering immediately before the main body starts.

### Abbreviations and Abstract
- Add a two-column abbreviations table using existing `longtable`/`array` support; include at least AI, API, F1, GGUF, GPU, ICT, JSONL, LLM, LoRA, NF4, NCSC, OTP, PEFT, QLoRA, USTH, VRAM, and XAI if used in the thesis.
- Keep the abstract body concise and truthful to current results, with macro F1 = 0.9553 and task-scam recall = 0.871 if retained.
- Add exactly 6 English keywords after the abstract body.
- Verify the abstract body is no more than 250 words; keywords are metadata and not counted as abstract prose unless a local checker says otherwise.

### the agent's Discretion

### Autonomous Defaults
- This context was generated through smart discuss in autonomous mode; the agent selected recommended answers from ROADMAP, REQUIREMENTS, STATE, and current LaTeX source.
- Implementation choices not specified above are at the agent's discretion, with priority order: department template requirements, compile stability, minimal package churn, and readability.

### Deferred Ideas (OUT OF SCOPE)

## Deferred Ideas

Document body restructure, Roman numeral thesis sections, evaluation tables, appendices, and slide wording sync are deferred to Phases 23 and 24.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| COVER-01 | Thesis title page uses "BACHELOR THESIS" label and "By \<student name\> / Title: \<title\>" layout. | Modify only `chapters/frontmatter/titlepage.tex`; current stale label and `Prepared By` block were found there. [VERIFIED: .planning/REQUIREMENTS.md + rg codebase] |
| CERT-01 | Supervisor certification letter page added after titlepage, unnumbered, before roman front matter begins. | Add `chapters/frontmatter/certification.tex` and input it between titlepage and preface in `main.tex`. [VERIFIED: .planning/REQUIREMENTS.md + documents/reports/latex/main.tex] |
| FRONT-01 | Front matter order is TOC -> Acknowledgements -> List of Abbreviations -> List of Tables -> List of Figures -> Abstract. | Reorder `chapters/frontmatter/preface.tex`; current order is Abstract -> Acknowledgements -> TOC -> List of Figures -> List of Tables. [VERIFIED: .planning/REQUIREMENTS.md + documents/reports/latex/chapters/frontmatter/preface.tex] |
| FRONT-02 | List of Abbreviations 2-column table covers thesis acronyms. | Use existing `longtable`, `array`, and `L{}` column support from `main.tex`; acronym grep found required terms in report sources. [VERIFIED: main.tex + rg codebase + kpsewhich] |
| FRONT-03 | Abstract has 6 English keywords and body is verified at <=250 words. | Existing abstract body is 125 words by local PowerShell count before adding keywords. [VERIFIED: local word-count command] |
</phase_requirements>

## Summary

Phase 22 should be a narrow LaTeX front-matter edit: update the existing title page, add one certification page, and reorder `preface.tex` without touching body chapter inputs. The current entrypoint already inputs `chapters/frontmatter/titlepage` followed by `chapters/frontmatter/preface`, so the lowest-risk integration is inserting `chapters/frontmatter/certification` between those two inputs. [VERIFIED: documents/reports/latex/main.tex]

No new LaTeX package is needed for this phase. `main.tex` already loads `longtable`, `array`, `booktabs`, `tocloft`, and defines `\newcolumntype{L}[1]`, and the local MiKTeX installation resolves `longtable.sty`, `array.sty`, and `booktabs.sty`. [VERIFIED: main.tex + local MiKTeX probe]

**Primary recommendation:** Modify `main.tex`, `titlepage.tex`, and `preface.tex`; add `certification.tex`; then run the clean XeLaTeX/BibTeX sequence from `documents/reports/latex/`. [VERIFIED: 22-CONTEXT.md + local tool probe]

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|--------------|----------------|-----------|
| Title page layout | LaTeX frontmatter source | PDF build output | `titlepage.tex` owns the cover-page visual structure and currently contains the stale label. [VERIFIED: documents/reports/latex/chapters/frontmatter/titlepage.tex] |
| Certification page insertion | LaTeX entrypoint | Frontmatter source | `main.tex` controls file order, so it should input certification after titlepage and before preface. [VERIFIED: documents/reports/latex/main.tex] |
| Roman front matter order | Frontmatter source | PDF TOC/list artifacts | `preface.tex` starts roman numbering and currently owns Abstract, Acknowledgements, TOC, LoF, LoT, and arabic transition. [VERIFIED: documents/reports/latex/chapters/frontmatter/preface.tex] |
| Abbreviations list | Frontmatter source | Existing table packages | A two-column table can use the existing `longtable` plus `L{}` column type from the preamble. [VERIFIED: main.tex + kpsewhich] |
| Abstract keyword/count gate | Frontmatter source | Local verification command | The abstract body lives in `preface.tex`; verification should count body prose separately from keyword metadata. [VERIFIED: documents/reports/latex/chapters/frontmatter/preface.tex + 22-CONTEXT.md] |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| XeLaTeX / MiKTeX-XeTeX | 4.18 (MiKTeX 26.5) | Compile the thesis with Times New Roman through `fontspec`. | Existing manuscript declares XeLaTeX and uses `fontspec`; local compiler is installed. [VERIFIED: main.tex + local `xelatex --version`] |
| BibTeX / MiKTeX-BibTeX | 4.2 (MiKTeX 26.5) | Rebuild bibliography and resolve citation side effects during clean compile. | Existing `main.tex` uses `natbib`, `ieeetr`, and `\bibliography{references}`. [VERIFIED: main.tex + local `bibtex --version`] |
| `longtable` | installed via MiKTeX tools bundle | Abbreviations table that can remain stable if it grows beyond one page. | Already loaded in `main.tex`; local `kpsewhich` resolves the package. [VERIFIED: main.tex + kpsewhich] |
| `array` | installed via MiKTeX tools bundle | Fixed-width ragged-right abbreviation-description columns. | Already loaded and used to define `L{}` in `main.tex`. [VERIFIED: main.tex + kpsewhich] |
| `booktabs` | installed via MiKTeX booktabs bundle | Clean horizontal rules in tables. | Already loaded in `main.tex`; no package churn needed. [VERIFIED: main.tex + kpsewhich] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `tocloft` | existing project package | Existing TOC/list spacing control. | Keep current settings; do not redesign list spacing in Phase 22. [VERIFIED: main.tex] |
| `hyperref` | existing project package | Link TOC entries and page anchors. | Keep loaded last as currently configured; do not reorder packages in Phase 22. [VERIFIED: main.tex] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Inline abbreviation table in `preface.tex` | Add `chapters/frontmatter/abbreviations.tex` | A separate file is cleaner for long lists, but Phase 22 context says `preface.tex` should own the full sequence; inline is lower churn. [VERIFIED: 22-CONTEXT.md] |
| Existing table packages | Add `nomencl`, `glossaries`, or `acro` | New packages add compile/indexing complexity and are unnecessary for a static two-column list. [ASSUMED] |

**Installation:** No package installation is required. [VERIFIED: main.tex + local MiKTeX probe]

## Package Legitimacy Audit

No external packages are installed in this phase, so the package legitimacy gate is not applicable. [VERIFIED: 22-CONTEXT.md]

## Architecture Patterns

### System Architecture Diagram

```text
main.tex
  -> titlepage.tex
       -> bordered cover with BACHELOR THESIS / By / Title layout
  -> certification.tex
       -> unnumbered, empty-style certification page outside roman numbering
  -> preface.tex
       -> \pagenumbering{roman}
       -> TOC
       -> Acknowledgements
       -> List of Abbreviations
       -> List of Tables
       -> List of Figures
       -> Abstract + 6 keywords
       -> \pagenumbering{arabic}
  -> existing body chapter inputs unchanged
```

This flow matches the existing source orchestration while inserting certification before roman front matter. [VERIFIED: documents/reports/latex/main.tex + 22-CONTEXT.md]

### Recommended Project Structure

```text
documents/reports/latex/
├── main.tex
└── chapters/frontmatter/
    ├── titlepage.tex
    ├── certification.tex
    └── preface.tex
```

`certification.tex` is the only new source file recommended for Phase 22; `titlepage.tex`, `preface.tex`, and `main.tex` are the only existing files likely to change. [VERIFIED: current frontmatter directory listing + 22-CONTEXT.md]

### Pattern 1: Titlepage Label and Layout Without New Packages

**What:** Keep the existing `titlepage`, TikZ border, USTH logo, font settings, and tabular primitives, but replace the stale thesis label and prepared-by block with explicit `By` and `Title:` lines. [VERIFIED: titlepage.tex + 22-CONTEXT.md]

**When to use:** Use this for COVER-01 only; do not change `geometry`, add cover packages, or move logo assets. [VERIFIED: 22-CONTEXT.md]

**Example:**

```latex
% Source: local pattern from titlepage.tex, adapted for Phase 22
{\fontsize{13}{15}\selectfont\bfseries\addfontfeatures{LetterSpace=5.0} BACHELOR THESIS\par}
\vspace{0.7cm}
{\large By Phạm Thế Minh\par}
\vspace{0.35cm}
{\large\bfseries Title:\par}
{\fontsize{22}{27}\selectfont\bfseries Localized Explainable AI Engine\par}
{\fontsize{15}{19}\selectfont for Vietnamese Financial Phishing Detection\par}
```

### Pattern 2: Certification Page Outside Roman Front Matter

**What:** Add a standalone unnumbered page with `\thispagestyle{empty}` and `\clearpage`, then input it before `preface.tex`. [VERIFIED: 22-CONTEXT.md + main.tex]

**When to use:** Use this when a front-matter page must appear after the title page but before `\pagenumbering{roman}`. [VERIFIED: 22-CONTEXT.md]

**Example:**

```latex
% main.tex
\input{chapters/frontmatter/titlepage}
\input{chapters/frontmatter/certification}
\input{chapters/frontmatter/preface}
```

```latex
% chapters/frontmatter/certification.tex
\clearpage
\thispagestyle{empty}

\chapter*{Certification Letter}
To whom it may concern,

% formal certification wording here

\vfill
\begin{tabular}{@{}p{0.45\textwidth}p{0.45\textwidth}@{}}
Internal Supervisor & External Supervisor \\
\\[2.5cm]
Giang Anh Tuan & Nguyen Viet Anh \\
\end{tabular}

\clearpage
```

### Pattern 3: Required Front Matter Order

**What:** Move the abstract block to the end of `preface.tex`, place `\tableofcontents` first after `\pagenumbering{roman}`, and order lists as List of Tables before List of Figures. [VERIFIED: 22-CONTEXT.md + preface.tex]

**When to use:** Use this for FRONT-01; leave body chapter inputs unchanged until Phase 23. [VERIFIED: ROADMAP.md + 22-CONTEXT.md]

**Example:**

```latex
\pagenumbering{roman}

{\singlespacing
\tableofcontents
}

\clearpage
\chapter*{Acknowledgements}
\addcontentsline{toc}{chapter}{Acknowledgements}

\clearpage
\chapter*{List of Abbreviations}
\addcontentsline{toc}{chapter}{List of Abbreviations}

\clearpage
{\singlespacing
\addcontentsline{toc}{chapter}{\listtablename}
\listoftables
}

\clearpage
{\singlespacing
\addcontentsline{toc}{chapter}{\listfigurename}
\listoffigures
}

\clearpage
\chapter*{Abstract}
\addcontentsline{toc}{chapter}{Abstract}

\cleardoublepage
\pagenumbering{arabic}
```

### Pattern 4: Abbreviations Table With Existing Packages

**What:** Use `longtable` with the existing `L{}` column type and `booktabs` rules. [VERIFIED: main.tex + kpsewhich]

**When to use:** Use this for FRONT-02; keep it static and deterministic. [VERIFIED: .planning/REQUIREMENTS.md]

**Example:**

```latex
\begin{longtable}{@{}p{0.22\textwidth}L{0.68\textwidth}@{}}
\toprule
\textbf{Abbreviation} & \textbf{Meaning} \\
\midrule
AI & Artificial Intelligence \\
API & Application Programming Interface \\
F1 & Harmonic mean of precision and recall \\
GGUF & GPT-Generated Unified Format \\
GPU & Graphics Processing Unit \\
ICT & Information and Communication Technology \\
JSONL & JSON Lines \\
LLM & Large Language Model \\
LoRA & Low-Rank Adaptation \\
NF4 & NormalFloat 4-bit quantization \\
NCSC & National Cyber Security Center \\
OTP & One-Time Password \\
PEFT & Parameter-Efficient Fine-Tuning \\
QLoRA & Quantized Low-Rank Adaptation \\
USTH & University of Science and Technology of Hanoi \\
VRAM & Video Random Access Memory \\
XAI & Explainable Artificial Intelligence \\
\bottomrule
\end{longtable}
```

The abbreviation candidates above are supported by acronym usage in the report and by the Phase 22 context list. [VERIFIED: rg codebase + 22-CONTEXT.md]

### Anti-Patterns to Avoid

- **Adding a glossary package for a static list:** New indexing or glossary tooling is unnecessary for this phase and adds compile risk. [ASSUMED]
- **Starting roman numbering in `titlepage.tex` or `certification.tex`:** The context requires certification outside roman front matter; keep `\pagenumbering{roman}` in `preface.tex`. [VERIFIED: 22-CONTEXT.md + preface.tex]
- **Reordering body chapters in Phase 22:** Body restructure is explicitly deferred to Phase 23. [VERIFIED: 22-CONTEXT.md + ROADMAP.md]
- **Changing `\thechapter` or section numbering now:** Roman thesis sections belong to Phase 23 and must not be mixed into front-matter work. [VERIFIED: ROADMAP.md + STATE.md]
- **Putting List of Figures before List of Tables:** The required order places List of Tables before List of Figures. [VERIFIED: .planning/REQUIREMENTS.md]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cover border | Manual page-size measurements outside existing TikZ overlay | Existing `tikzpicture` border in `titlepage.tex` | Current border already renders inside page geometry and preserves template identity. [VERIFIED: titlepage.tex] |
| Abbreviation layout | Ad hoc spaces or manual line breaks | `longtable` + `L{}` + `booktabs` | Existing packages support stable columns without adding dependencies. [VERIFIED: main.tex + kpsewhich] |
| TOC/list ordering | Manual typed list titles without LaTeX list commands | `\tableofcontents`, `\listoftables`, `\listoffigures` | Existing commands generate page references and list entries from compiled artifacts. [ASSUMED] |
| Abstract word count | Manual count only | Local script/PowerShell count over the abstract body block | Current body count was reproducibly measured as 125 words. [VERIFIED: local word-count command] |

**Key insight:** This phase is formatting orchestration, not a new LaTeX subsystem; reuse current report primitives and keep changes easy to visually diff. [VERIFIED: 22-CONTEXT.md]

## Common Pitfalls

### Pitfall 1: Certification Accidentally Enters Roman Numbering

**What goes wrong:** The certification page receives a roman numeral or appears in the front-matter sequence. [VERIFIED: 22-CONTEXT.md]
**Why it happens:** `\pagenumbering{roman}` is currently at the top of `preface.tex`; moving it earlier would include certification. [VERIFIED: preface.tex]
**How to avoid:** Keep certification before `preface.tex`, set `\thispagestyle{empty}`, and do not call `\pagenumbering{roman}` in the certification file. [VERIFIED: 22-CONTEXT.md]
**Warning signs:** Certification page has a visible page number or TOC entry. [ASSUMED]

### Pitfall 2: Stale TOC/List Pages After One Compile

**What goes wrong:** The PDF appears to have old page numbers or missing front-matter entries. [ASSUMED]
**Why it happens:** TOC, LoT, and LoF are generated from auxiliary files across compile passes. [ASSUMED]
**How to avoid:** Delete auxiliary files, then run XeLaTeX, BibTeX, XeLaTeX, XeLaTeX. [VERIFIED: STATE.md + local compiler availability]
**Warning signs:** `main.toc`, `main.lot`, or `main.lof` contents do not reflect the new order. [ASSUMED]

### Pitfall 3: Abstract Keyword Count Blends Into Body Count

**What goes wrong:** The checker counts keywords as abstract prose and reports a higher word count than intended. [VERIFIED: 22-CONTEXT.md]
**Why it happens:** Keywords are placed immediately after the abstract body without a detectable delimiter. [ASSUMED]
**How to avoid:** Put keywords after a clear line such as `\noindent\textbf{Keywords:}` and count only text before that marker. [ASSUMED]
**Warning signs:** The word-count command includes keyword terms or reports a count inconsistent with manual body-only review. [ASSUMED]

### Pitfall 4: Acronym List Misses Terms Already Used

**What goes wrong:** The abbreviation list omits common report acronyms such as API, OTP, QLoRA, or GGUF. [VERIFIED: rg codebase]
**Why it happens:** Acronyms are spread across chapters, figures, tables, and slides. [VERIFIED: rg codebase]
**How to avoid:** Build the initial list from the Phase 22 context and run `rg` over report `.tex` files before finalizing. [VERIFIED: 22-CONTEXT.md + rg codebase]
**Warning signs:** `rg` finds all-caps technical terms absent from the table. [ASSUMED]

## Code Examples

### Clean Compile Sequence

```powershell
Set-Location documents/reports/latex
Remove-Item -ErrorAction SilentlyContinue `
  main.aux,main.bbl,main.blg,main.lof,main.log,main.lot,main.out,main.toc
xelatex -interaction=nonstopmode main.tex
bibtex main
xelatex -interaction=nonstopmode main.tex
xelatex -interaction=nonstopmode main.tex
```

This matches the project-state safe sequence and local compiler availability. [VERIFIED: STATE.md + local `xelatex --version` + local `bibtex --version`]

### Abstract Body Word Count

```powershell
$text = Get-Content -Raw documents/reports/latex/chapters/frontmatter/preface.tex
$match = [regex]::Match(
  $text,
  '(?s)\\chapter\*\{Abstract\}.*?\\addcontentsline\{toc\}\{chapter\}\{Abstract\}\s*(.*?)\s*(\\noindent\\textbf\{Keywords:|\\cleardoublepage|$)'
)
$body = $match.Groups[1].Value -replace '\\[a-zA-Z]+(\[[^\]]*\])?(\{[^}]*\})?', ' ' -replace '[{}]', ' '
[regex]::Matches($body, "[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)?").Count
```

The current abstract body counted this way is 125 words before adding keywords. [VERIFIED: local word-count command]

### Six Keyword Line

```latex
\vspace{0.5em}
\noindent\textbf{Keywords:} Vietnamese phishing detection; local LLM; explainable AI; QLoRA; GGUF; financial fraud.
```

This gives exactly six semicolon-separated English keyword phrases. [ASSUMED]

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Current source order: Abstract -> Acknowledgements -> TOC -> List of Figures -> List of Tables | Required order: TOC -> Acknowledgements -> List of Abbreviations -> List of Tables -> List of Figures -> Abstract | Phase 22 | Planner should treat `preface.tex` reordering as the core implementation task. [VERIFIED: preface.tex + REQUIREMENTS.md] |
| Current title label: `GRADUATION THESIS` | Required label: `BACHELOR THESIS` | Phase 22 | Single titlepage text/layout update satisfies the label part of COVER-01. [VERIFIED: titlepage.tex + REQUIREMENTS.md] |
| No certification source file in frontmatter directory | Add `chapters/frontmatter/certification.tex` | Phase 22 | Certification can remain isolated and unnumbered. [VERIFIED: current frontmatter listing + 22-CONTEXT.md] |

**Deprecated/outdated:**
- `GRADUATION THESIS` label: replace with `BACHELOR THESIS` for department-template compliance. [VERIFIED: titlepage.tex + REQUIREMENTS.md]
- `Prepared By` heading: replace with explicit `By Phạm Thế Minh` plus `Title:` layout. [VERIFIED: titlepage.tex + 22-CONTEXT.md]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | New glossary/indexing packages are unnecessary for a static abbreviations list. | Alternatives / Anti-Patterns | If the department mandates a generated glossary package, planner must revise the implementation. |
| A2 | TOC, LoT, and LoF behavior requires multiple compile passes. | Pitfalls / Don't Hand-Roll | If the local build tool handles this automatically, extra passes are harmless but slower. |
| A3 | The keyword line example contains exactly six acceptable English keyword phrases. | Code Examples | User or department may prefer different keyword phrases. |

## Open Questions

1. **Supervisor names with Vietnamese diacritics**
   - What we know: Current titlepage uses `Giang Anh Tuan` and `Nguyen Viet Anh`; context says preserve supervisors. [VERIFIED: titlepage.tex + 22-CONTEXT.md]
   - What's unclear: Whether final department copy should use `Giang Anh Tuấn` and `Nguyễn Việt Anh`. [ASSUMED]
   - Recommendation: Keep existing spelling unless the user supplies the exact department-approved form. [ASSUMED]

2. **Certification signature formatting**
   - What we know: Context requires signature/date lines suitable for final manual completion. [VERIFIED: 22-CONTEXT.md]
   - What's unclear: Whether USTH ICT has a required signature block order beyond internal/external supervisor lines. [ASSUMED]
   - Recommendation: Use a conservative two-column supervisor signature block and leave date blanks. [ASSUMED]

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| XeLaTeX | Thesis compile | yes | MiKTeX-XeTeX 4.18 (MiKTeX 26.5) | Overleaf XeLaTeX if local build fails. [VERIFIED: local `xelatex --version` + main.tex comments] |
| BibTeX | Bibliography compile pass | yes | MiKTeX-BibTeX 4.2 (MiKTeX 26.5) | Overleaf BibTeX if local build fails. [VERIFIED: local `bibtex --version` + main.tex] |
| `longtable.sty` | Abbreviations table | yes | local MiKTeX path resolved | Use plain `tabular` if unavailable, but it is available locally. [VERIFIED: kpsewhich] |
| `array.sty` | Fixed-width `L{}` column | yes | local MiKTeX path resolved | Use `p{}` columns if unavailable, but it is available locally. [VERIFIED: kpsewhich] |
| `booktabs.sty` | Table rules | yes | local MiKTeX path resolved | Use `\hline` if unavailable, but it is available locally. [VERIFIED: kpsewhich] |

**Missing dependencies with no fallback:** None. [VERIFIED: local tool probe]

**Missing dependencies with fallback:** None found for Phase 22. [VERIFIED: local tool probe]

## Security Domain

Security enforcement is not explicitly disabled in `.planning/config.json`, so this section is included. [VERIFIED: .planning/config.json]

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | no | No authentication surface changes in a local LaTeX document formatting phase. [VERIFIED: Phase 22 scope in 22-CONTEXT.md] |
| V3 Session Management | no | No session state or web runtime changes. [VERIFIED: Phase 22 scope in 22-CONTEXT.md] |
| V4 Access Control | no | No authorization boundary changes. [VERIFIED: Phase 22 scope in 22-CONTEXT.md] |
| V5 Input Validation | no | No runtime user input path changes; only static LaTeX source edits. [VERIFIED: Phase 22 scope in 22-CONTEXT.md] |
| V6 Cryptography | no | No cryptographic behavior changes. [VERIFIED: Phase 22 scope in 22-CONTEXT.md] |

### Known Threat Patterns for Local LaTeX Front Matter

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Accidental inclusion of private draft notes in certification or abstract | Information Disclosure | Review changed `.tex` files before commit; keep wording formal and submission-safe. [ASSUMED] |
| Build artifact confusion after front-matter reorder | Tampering | Clean auxiliary files before final compile and inspect generated PDF order. [VERIFIED: STATE.md] |

## Sources

### Primary (HIGH confidence)

- `.planning/phases/22-cover-page-certification-letter-and-front-matter/22-CONTEXT.md` - locked Phase 22 decisions, deferred scope, and implementation integration points.
- `.planning/REQUIREMENTS.md` - COVER-01, CERT-01, FRONT-01, FRONT-02, FRONT-03 requirement text.
- `.planning/ROADMAP.md` - Phase 22 boundary and Phase 23/24 deferrals.
- `.planning/STATE.md` - active milestone state and safe compile sequence.
- `documents/reports/latex/main.tex` - package imports, compiler comments, frontmatter input order, bibliography commands.
- `documents/reports/latex/chapters/frontmatter/titlepage.tex` - current titlepage layout and stale label.
- `documents/reports/latex/chapters/frontmatter/preface.tex` - current front-matter order and abstract body.

### Secondary (MEDIUM confidence)

- Local command probes: `xelatex --version`, `bibtex --version`, `kpsewhich longtable.sty`, `kpsewhich array.sty`, `kpsewhich booktabs.sty`.
- Local `rg` acronym scan over `documents/reports/latex`.
- Local PowerShell abstract word-count command.

### Tertiary (LOW confidence)

- General LaTeX behavior claims marked `[ASSUMED]` because the user requested local research with no web lookup.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - existing packages and local tools were verified by source and command probes.
- Architecture: HIGH - file ownership and ordering are visible in local LaTeX sources and Phase 22 context.
- Pitfalls: MEDIUM - certification scope and current ordering are verified; general LaTeX aux-file behavior is marked as assumed.

**Research date:** 2026-06-15
**Valid until:** 2026-07-15 for this local LaTeX phase unless department template requirements change.

