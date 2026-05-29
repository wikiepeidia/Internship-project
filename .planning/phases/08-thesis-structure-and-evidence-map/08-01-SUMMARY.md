---
phase: 08-thesis-structure-and-evidence-map
plan: 01
subsystem: thesis-manuscript
tags:
  - thesis
  - evidence-map
  - writing-guardrails
  - latex
dependency_graph:
  requires:
    - 07b-01
  provides:
    - evidence-map locked for Phase 9 drafting
    - writing guardrails preventing tone drift
    - six-chapter manuscript structure finalized
  affects:
    - documents/reports/latex/
    - .planning/phases/09-core-thesis-chapter-drafting/
tech_stack:
  added: []
  patterns:
    - LaTeX manuscript with six-chapter structure
    - EVIDENCE_MAP.md for chapter-by-chapter evidence anchoring
    - WRITING_GUARDRAILS.md for tone and honesty enforcement
key_files:
  created:
    - .planning/phases/08-thesis-structure-and-evidence-map/08-EVIDENCE_MAP.md
    - .planning/phases/08-thesis-structure-and-evidence-map/08-WRITING_GUARDRAILS.md
  modified:
    - documents/reports/latex/chapters/frontmatter/titlepage.tex
    - documents/reports/latex/chapters/05_evaluation_and_discussion.tex
decisions:
  - Six-chapter main.tex structure is the working thesis template; no parallel tree created
  - Chapter 5 evidence must come from tracked manifests and saved evaluation artifacts only; off-repo training numbers are appendix-only
  - Final release verdict uses plain prose (not release-ready under its own safety gate) in thesis body; literal label stays in tables or appendix
metrics:
  duration: ~30 minutes
  completed: 2026-05-29
---

# Phase 8 Plan 01: Thesis chapter lock and evidence map — Summary

Six-chapter LaTeX manuscript locked with GRADUATION THESIS label, chapter-by-chapter evidence map, and anti-AI-like tone guardrails ready for Phase 9 drafting.

## What Was Done

### Output 1: main.tex structure locked and titlepage refreshed

The existing `documents/reports/latex/main.tex` already matched the exact required eight-input structure (frontmatter/titlepage, frontmatter/preface, 01-06 chapters). No structural change was needed.

`documents/reports/latex/chapters/frontmatter/titlepage.tex` still carried the label "GRADUATION INTERNSHIP REPORT" from the original draft era. That label was changed to "GRADUATION THESIS" so the cover page matches the graduation submission context. The `preface.tex` abstract already described the system and final results honestly and needed no changes.

### Output 2: EVIDENCE_MAP.md created

`documents/reports/latex/EVIDENCE_MAP.md` contains exactly six rows, one per final chapter. Each row includes:
- **Chapter file**: the exact .tex path
- **Claim boundary**: what the chapter is allowed to assert
- **Primary evidence**: at least one named repo artifact, document path, or verified external URL
- **Support type**: describes how the evidence supports the claim
- **Extraction note**: instructions for pulling the evidence into prose
- **Caution**: explicit limit or avoidance rule preventing overclaiming

A git-trackable copy is saved at `.planning/phases/08-thesis-structure-and-evidence-map/08-EVIDENCE_MAP.md`.

### Output 3: WRITING_GUARDRAILS.md created

`documents/reports/latex/WRITING_GUARDRAILS.md` records six rule sections:
1. **Working template rule**: current main.tex is the manuscript template; no new chapter architecture
2. **Evidence boundary for Chapter 5**: tracked manifests and saved artifacts only; off-repo numbers are appendix-only
3. **Tone rules**: short declarative sentences, measured verbs (shows/indicates/suggests), no AI-like stock phrases, no inflated claims
4. **Process-language filter**: no GSD, roadmap language, phase numbers, STATE.md, or UAT inside thesis prose
5. **Claim discipline**: every strong claim must point to a named artifact or verified external source
6. **Citation boundary**: Phase 8 seeds entries only; in-text citations and bibliography rendering are deferred to Phase 9

A git-trackable copy is saved at `.planning/phases/08-thesis-structure-and-evidence-map/08-WRITING_GUARDRAILS.md`.

### Output 4: Chapter stale-language cleanup

All chapter files were scanned against the stale-language pattern. Two issues were found and fixed:

1. **titlepage.tex**: "GRADUATION INTERNSHIP REPORT" → "GRADUATION THESIS" (thesis-facing label)
2. **05_evaluation_and_discussion.tex**: "The Phase~7 closeout record passed all five user-acceptance checks" → "The final closeout verification passed all five acceptance checks" (removes internal phase reference and UAT wording)

The all-chapter scan found no other instances of stale planning language (ROADMAP, STATE.md, UAT literal, Phase N references, pending-evaluation wording, or draft-report labels) in any of the six chapter files, titlepage, preface, or main.tex.

### Output 5: references.bib seeded, TODO.md updated

`documents/reports/latex/references.bib` already contained six verified BibTeX entries:
- `ais2024biometricwarning` — Vietnamese national cybersecurity advisory on bank impersonation
- `groupib2022laser` — Group-IB threat intelligence report on Vietnamese banking phishing campaign
- `lim2025explicate` — arXiv preprint on explainable phishing detection with LIME and SHAP
- `rjoub2023surveyxai` — arXiv survey on explainable AI for cybersecurity
- `nist2026privacyframework` — NIST Privacy Framework
- `oregonstate2026formatting` — Oregon State thesis formatting guide (structure reference only)

`documents/reports/latex/TODO.md` already listed chapter citation targets for chapters 1, 2, 3, and 5, the explicit Phase 9 boundary for in-text citation insertion, and the bibliography rendering defer note.

No changes were needed to these files.

## Verification Results

All plan verification checks passed:

- **main.tex structure**: eight `\input{chapters/...}` lines match the expected ordered list exactly
- **EVIDENCE_MAP.md**: header columns correct; six data rows present; each row has non-empty cells in all six columns; each evidence cell contains at least one allowed token (data/, docs/, documents/, .planning/phases/, or http); each caution cell matches the caution/limit/avoid/do not pattern
- **references.bib**: six `@` entries present
- **TODO.md**: contains "citation target", "in-text citation", "bibliography rendering", and "Phase 9" text
- **WRITING_GUARDRAILS.md**: contains all required tone terms (short declarative, measured verbs, AI-like, state-of-the-art, rapidly evolving landscape, GSD, roadmap language, inflated claims)
- **Stale language scan**: clean across all nine checked files after the two fixes above

Note: `latexmk` compilation was not run because the LaTeX toolchain is not in the execution environment. The manuscript structure is confirmed correct by Python-based input-line verification. Full compilation can be run locally or on Overleaf.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] titlepage.tex still carried internship-report label**
- **Found during**: Output 1 / Output 4 stale-language scan
- **Issue**: `chapters/frontmatter/titlepage.tex` contained "GRADUATION INTERNSHIP REPORT" instead of thesis-facing wording, which the plan required to be fixed as part of the label refresh task
- **Fix**: Changed label to "GRADUATION THESIS"
- **Files modified**: `documents/reports/latex/chapters/frontmatter/titlepage.tex`

**2. [Rule 1 - Bug] Chapter 5 contained internal phase reference**
- **Found during**: Output 4 stale-language scan
- **Issue**: `chapters/05_evaluation_and_discussion.tex` contained "The Phase~7 closeout record passed all five user-acceptance checks" — both the Phase N reference and the UAT-flavored "user-acceptance checks" wording were stale internal process language
- **Fix**: Rewritten to "The final closeout verification passed all five acceptance checks"
- **Files modified**: `documents/reports/latex/chapters/05_evaluation_and_discussion.tex`

### Scope Notes

- All thesis manuscript work (titlepage, preface, chapter files, EVIDENCE_MAP, WRITING_GUARDRAILS, references.bib, TODO.md) lives inside `documents/reports/latex/` which is fully gitignored. Git commits in this plan capture only the `.planning/` snapshot copies of EVIDENCE_MAP and WRITING_GUARDRAILS.
- The `latexmk` verification step was skipped because the LaTeX toolchain is not available in the execution environment. The structural verification (Python check of `\input` lines) passed completely.
- EVIDENCE_MAP.md and WRITING_GUARDRAILS.md already existed in `documents/reports/latex/` from prior work in this phase. The plan task was to verify they meet the specification, fix any gaps, and create git-trackable copies in `.planning/phases/08-*`.

## Known Stubs

None. All chapter files contain meaningful scaffold prose tied to the implemented system. Full narrative expansion is deferred to Phase 9 by design.

## Threat Flags

None. This plan created only documentation artifacts (EVIDENCE_MAP, WRITING_GUARDRAILS, chapter cleanup) and did not introduce new network endpoints, auth paths, or file access patterns.

## Self-Check: PASSED

- `.planning/phases/08-thesis-structure-and-evidence-map/08-EVIDENCE_MAP.md` — FOUND
- `.planning/phases/08-thesis-structure-and-evidence-map/08-WRITING_GUARDRAILS.md` — FOUND
- Commit 3de91e3 (EVIDENCE_MAP) — exists
- Commit d78d20d (WRITING_GUARDRAILS) — exists
- `documents/reports/latex/EVIDENCE_MAP.md` passes all six verification assertions — PASS
- `documents/reports/latex/WRITING_GUARDRAILS.md` passes all tone-term checks — PASS
- `documents/reports/latex/chapters/frontmatter/titlepage.tex` — GRADUATION THESIS label confirmed
- Stale language scan — CLEAN across all nine files
