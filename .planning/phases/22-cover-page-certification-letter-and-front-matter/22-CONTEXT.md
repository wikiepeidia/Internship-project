# Phase 22: Cover Page, Certification Letter, and Front Matter - Context

**Gathered:** 2026-06-15
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase reformats only the thesis front matter in `documents/reports/latex/`: title page wording/layout, an added supervisor certification letter page, front matter ordering, a List of Abbreviations, and abstract keywords/word-count verification. It must not restructure the thesis body, change chapter numbering, alter evaluation content, or add packages unless existing LaTeX primitives are insufficient.

</domain>

<decisions>
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

### Autonomous Defaults
- This context was generated through smart discuss in autonomous mode; the agent selected recommended answers from ROADMAP, REQUIREMENTS, STATE, and current LaTeX source.
- Implementation choices not specified above are at the agent's discretion, with priority order: department template requirements, compile stability, minimal package churn, and readability.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `documents/reports/latex/main.tex` already orchestrates `chapters/frontmatter/titlepage` and `chapters/frontmatter/preface` before body chapters.
- `documents/reports/latex/chapters/frontmatter/titlepage.tex` contains the current title page, USTH logo include, border, student/supervisor table, and stale `GRADUATION THESIS` label.
- `documents/reports/latex/chapters/frontmatter/preface.tex` currently contains Abstract, Acknowledgements, TOC, List of Figures, List of Tables, then switches to arabic numbering.
- Existing packages in `main.tex` already include `longtable`, `array`, `booktabs`, and `tocloft`, enough for the abbreviations table and front matter formatting.

### Established Patterns
- Front matter sections use `\chapter*{...}` plus `\addcontentsline{toc}{chapter}{...}`.
- Compile target is XeLaTeX from `documents/reports/latex/`.
- The project keeps thesis report work in the existing LaTeX tree rather than creating a parallel manuscript.

### Integration Points
- Add the certification page as a new `chapters/frontmatter/certification.tex` and input it from `main.tex` between titlepage and preface.
- Keep body chapter inputs unchanged in Phase 22; Phase 23 owns document restructuring.
- Use the safe compile sequence from STATE if references or TOC entries need multiple passes.

</code_context>

<specifics>
## Specific Ideas

The roadmap requirement text is authoritative for this phase:
- COVER-01: `BACHELOR THESIS` label and `By <student name> / Title: <title>` layout.
- CERT-01: certification letter page after titlepage, unnumbered, before roman front matter.
- FRONT-01: TOC -> Acknowledgements -> List of Abbreviations -> List of Tables -> List of Figures -> Abstract.
- FRONT-02: two-column abbreviation list covering thesis acronyms.
- FRONT-03: Abstract has 6 English keywords and verified body length no more than 250 words.

</specifics>

<deferred>
## Deferred Ideas

Document body restructure, Roman numeral thesis sections, evaluation tables, appendices, and slide wording sync are deferred to Phases 23 and 24.

</deferred>
