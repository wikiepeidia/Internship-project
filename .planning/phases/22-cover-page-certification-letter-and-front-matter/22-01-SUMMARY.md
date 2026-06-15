---
phase: 22-cover-page-certification-letter-and-front-matter
plan: 01
subsystem: latex-frontmatter
tags: [latex, xelatex, bibtex, thesis, frontmatter]

requires:
  - phase: 21-thesis-report-revisions
    provides: "Compile-clean thesis report baseline before department-template formatting"
provides:
  - "Department-template title page with BACHELOR THESIS, By, and Title layout"
  - "Standalone unnumbered certification letter inserted before roman front matter"
  - "Required front matter order with List of Abbreviations and abstract keywords"
affects: [phase-23-document-restructure, phase-24-final-compile, thesis-report]

tech-stack:
  added: []
  patterns: ["Reuse existing LaTeX longtable/array/booktabs support for static abbreviations", "Keep certification before preface so roman numbering starts after certification"]

key-files:
  created:
    - documents/reports/latex/chapters/frontmatter/certification.tex
  modified:
    - documents/reports/latex/main.tex
    - documents/reports/latex/chapters/frontmatter/titlepage.tex
    - documents/reports/latex/chapters/frontmatter/preface.tex

key-decisions:
  - "Kept certification outside roman numbering by inserting it before preface.tex and avoiding pagenumbering/addcontentsline there."
  - "Used a static longtable abbreviations list with existing packages instead of adding glossary tooling."
  - "Kept body chapters, numbering, appendices, evaluation tables, and slides untouched for Phase 23/24 scope."

patterns-established:
  - "Front matter source order: titlepage -> certification -> preface -> body chapters."
  - "preface.tex owns roman-numbered TOC, acknowledgements, abbreviations, generated lists, abstract, and arabic numbering transition."

requirements-completed: [COVER-01, CERT-01, FRONT-01, FRONT-02, FRONT-03]

duration: 5min
completed: 2026-06-15
---

# Phase 22 Plan 01: Cover Page, Certification Letter, and Front Matter Summary

**USTH ICT thesis front matter now has the department cover layout, an unnumbered certification letter, required section order, abbreviations table, and six-keyword abstract.**

## Performance

- **Duration:** 5 min
- **Started:** 2026-06-15T11:22:09Z
- **Completed:** 2026-06-15T11:26:59Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments

- Updated the title page from `GRADUATION THESIS` / `Prepared By` to `BACHELOR THESIS`, `By Phạm Thế Minh`, and `Title:` layout.
- Added `certification.tex` and wired it between `titlepage` and `preface`, before roman numbering begins.
- Reordered front matter to TOC, Acknowledgements, List of Abbreviations, List of Tables, List of Figures, Abstract.
- Added a two-column abbreviations longtable covering AI, API, F1, GGUF, GPU, ICT, JSONL, LLM, LoRA, NF4, NCSC, OTP, PEFT, QLoRA, USTH, VRAM, and XAI.
- Kept the abstract body at 125 words and added exactly six English keyword phrases.

## Task Commits

1. **Task 1: Update cover page and insert certification page** - `839751d` (feat)
2. **Task 2: Reorder front matter, add abbreviations, and update abstract keywords** - `62ea9ce` (feat)
3. **Task 3: Compile and prove Phase 22 scope stayed clean** - `5030fcb` (chore, empty verification commit)

## Files Created/Modified

- `documents/reports/latex/main.tex` - Inputs certification after titlepage and before preface.
- `documents/reports/latex/chapters/frontmatter/titlepage.tex` - Implements BACHELOR THESIS and By / Title cover layout.
- `documents/reports/latex/chapters/frontmatter/certification.tex` - Adds formal unnumbered supervisor certification letter.
- `documents/reports/latex/chapters/frontmatter/preface.tex` - Owns required roman front matter order, abbreviations, and abstract metadata.

## Verification

- Task 1 static source check: passed.
- Task 2 static source check: passed.
- Abstract body word count: 125 words, excluding keyword line.
- Compile: passed with clean aux removal followed by XeLaTeX, BibTeX, XeLaTeX, XeLaTeX from `documents/reports/latex`.
- Log scan: passed; `main.log` contains no fatal errors, emergency stops, undefined control sequences, or LaTeX errors.
- Scope guard: passed; Phase 22 thesis source changes are limited to `main.tex`, `titlepage.tex`, `certification.tex`, and `preface.tex`.

## Decisions Made

- Reused existing `longtable`, `array`, `L{}`, and `booktabs` support; no new LaTeX packages were added.
- Kept supervisor names as already used in the thesis source: Giang Anh Tuan and Nguyen Viet Anh.
- Kept certification out of TOC and roman numbering per plan.

## Deviations from Plan

None - product scope executed exactly as written.

## Issues Encountered

- `gsd-tools` was not available on PATH, so planning-state updates were made manually.
- The thesis source tree is ignored by `.gitignore` via `documents/*`; implementation commits used scoped `git add -f` for only the four Phase 22 source files.
- Task 3 produced no source changes after verification, so it was recorded as an empty chore commit.

## Known Stubs

None found. Changed files were scanned for TODO/FIXME/placeholder text and hardcoded empty-value patterns.

## Threat Flags

None. Phase 22 introduced no new network endpoints, auth paths, file access patterns, or schema changes.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Phase 23 can start from the updated front matter. Body restructuring, Roman numeral thesis sections, evaluation table sync, appendices, and slide reference updates remain deferred to Phases 23 and 24.

## Self-Check: PASSED

- Created files exist: `certification.tex`, `22-01-SUMMARY.md`.
- Modified files exist: `main.tex`, `titlepage.tex`, `preface.tex`.
- Commits found: `839751d`, `62ea9ce`, `5030fcb`.

---
*Phase: 22-cover-page-certification-letter-and-front-matter*
*Completed: 2026-06-15*
