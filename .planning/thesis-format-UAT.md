---
title: Thesis Format & Defence Prep — UAT
date: 2026-06-15
status: complete
---

# Thesis Format & Defence Preparation — UAT

All items below were implemented, compiled clean under XeLaTeX, and visually confirmed by the student.

## Cover Page (titlepage.tex)
- [x] UNIVERSITY normal weight, DEPARTMENT bold, BACHELOR THESIS 36pt bold
- [x] Title: "Design and Development of a Localized LLM for Vietnamese Financial Fraud and Phishing Detection" at 17pt (matches proposal title)
- [x] External Supervisor first: Assoc. Prof. Nguyen Viet Anh
- [x] Internal Supervisor second: Dr. Giang Anh Tuan
- [x] Date: Hanoi, July 2026

## Certification Letter (certification.tex)
- [x] "To whom it may concern" dept template text
- [x] Right-aligned block: date line → "Supervisor's Signature" label → signing space → supervisor name

## Front Matter (preface.tex)
- [x] Acknowledgements: dept-recommended tone, Nguyen Viet Anh first, Giang Anh Tuan second
- [x] List of Tables / List of Figures heading size consistent with other front matter headings (via `\chapter*` + `\@starttoc`)
- [x] Abstract: "We present" tone throughout
- [x] TABLE OF CONTENTS heading via `\chapter*` (goes through titlesec, same blue+uppercase+rule as all other headings)

## Chapter Headings (main.tex)
- [x] All `\chapter*` headings: CVBLUE (#1A5276) color, UPPERCASE via `\MakeUppercase`, 1pt blue rule below
- [x] Covers: TABLE OF CONTENTS, ACKNOWLEDGEMENTS, LIST OF ABBREVIATIONS, LIST OF TABLES, LIST OF FIGURES, ABSTRACT, I/ INTRODUCTION … V/ CONCLUSION AND PERSPECTIVE, APPENDICES, REFERENCES
- [x] Page header: "Internship Bachelor Thesis" (was "Bachelor Thesis")
- [x] TOC entries reduced to `\small`

## Report Body
- [x] Tonal fix: "this thesis / the system" → "we / our" throughout all chapters
- [x] Binary scam vs non-scam section deleted (F1 = 1.000 trivially, invites jury questions)
- [x] References fixed: main.bbl committed, all [?] citations now resolve
- [x] GSD internal jargon removed from all tables and ch05 (PASS, review pack, operator flow, Primary Target, acceptance checks)
- [x] "Localized" dual-meaning definition added to ch01 (on-device + Vietnamese domain fine-tuning)
- [x] 8B model mention rewritten: no "original proposal planned 8B" drama; natural three-candidate screening narrative
- [x] Quantization rationale added to ch03: NF4 4-bit for training vs Q8_0 8-bit for inference

## Appendices
- [x] `\chapter*{Appendices}` same tier as other front matter headings
- [x] Appendix 1: Source Code (GitHub link)
- [x] Appendix 2: Dataset Statistics (two booktabs tables)
- [x] Appendix 3: Evaluation Traceability Snapshot (moved from ch05)

## Slides (slides.tex)
- [x] Title: restored to proposal title, `\large` font so it fits 2 lines
- [x] Subtitle: "Bachelor Thesis Defense"
- [x] Footer author short form: "Internship Bachelor"
- [x] Slide 3 (03_problem.tex): "Localized" = (1) on-device + (2) Vietnamese fine-tuning footnote

## Git / Repository
- [x] .gitignore fixed: `documents/*` removed; XeLaTeX build artifacts (*.aux, *.toc, *.lof, *.lot, *.blg, *.nav, *.snm, *.vrb, *.fls, *.fdb_latexmk, *.synctex.gz, PDFs) ignored
- [x] All source files in documents/reports/latex/, documents/user/, documents/reports/supervisor/, documents/presentation/ now tracked normally (no more `git add -f`)
