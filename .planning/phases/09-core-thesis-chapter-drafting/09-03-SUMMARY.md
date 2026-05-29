---
phase: "09"
plan: "03"
subsystem: thesis-citation-pass-and-bibliography
tags: [latex, thesis, citations, bibliography, bibtex]
dependency_graph:
  requires: [09-01, 09-02]
  provides: [citation-wired-chapters-1-2, active-bibliography]
  affects:
    - documents/reports/latex/chapters/01_introduction.tex
    - documents/reports/latex/chapters/02_related_work_and_background.tex
    - documents/reports/latex/main.tex
tech_stack:
  added: []
  patterns: [latex-bibtex-citation, ieeetr-bibliography-style]
key_files:
  created: []
  modified:
    - documents/reports/latex/chapters/01_introduction.tex
    - documents/reports/latex/chapters/02_related_work_and_background.tex
    - documents/reports/latex/main.tex
decisions:
  - "groupib2022laser citation combined with ais2024biometricwarning in a single \\cite{ais2024biometricwarning,groupib2022laser} command at the threat-context sentence in Ch1, following standard LaTeX multi-cite practice"
  - "Chapter 1 stale scope paragraph updated to reflect Phase 7a PASS verdict: task-scam recall 0.871 on 62 held-out examples, all floors cleared — not the earlier BLOCK/falls-short wording"
  - "nist2026privacyframework cite placed at the privacy-control sentence in Ch2 Section 'Local Inference as a Privacy Control', consistent with existing placement in Ch3 and Ch4 from Plan 02"
  - "4B-vs-8B paragraph in Ch2 expanded to mention the 7B candidate evaluated in the pilot comparison, reconciling the hardware-fit narrative between Ch2 and Ch3"
  - "Bibliography block in main.tex uncommented (both \\renewcommand{\\bibname}{References} and \\bibliography{references}); all six BibTeX keys confirmed present in references.bib before enabling"
metrics:
  duration: "~8 minutes"
  completed: "2026-05-29T02:10:00Z"
  tasks_completed: 3
  tasks_total: 3
---

# Phase 09 Plan 03: Citation Pass and Bibliography Enabling — Summary

Citation wiring across Chapters 1 and 2, stale scope paragraph correction, and bibliography activation in main.tex using six pre-seeded BibTeX entries (all keys were already in references.bib from Phase 8).

## What Was Built

Three tasks completed:

**Task 1 — Chapter 1 citations and scope update:**
- Inserted `\cite{ais2024biometricwarning,groupib2022laser}` at the threat-context sentence in the chapter opening (SMS/Zalo phishing, banking details paragraph).
- Replaced the stale Objectives and Scope closing sentence ("still falls short on task-scam recall") with the correct final verdict: "all three risky classes cleared their per-class recall floors, with task-scam recall reaching 0.871 on 62 held-out examples."
- Scanned entire chapter — no forbidden terms found (Phase 7a, GSD, UAT, BLOCK, roadmap, PLAN.md).

**Task 2 — Chapter 2 citations and 4B paragraph expansion:**
- Inserted `\cite{rjoub2023surveyxai}` at the end of the Explainability section's structured-evidence sentence.
- Added EXPLICATE anchoring sentence with `\cite{lim2025explicate}` in the Explainability section.
- Inserted `\cite{nist2026privacyframework}` at the privacy-control sentence in the Local Inference section.
- Expanded the 4B-primary path sentence in Open-Weight Local Models to name the 7B candidate evaluated in the pilot comparison before locking the 4B path.
- Scanned entire chapter — no forbidden terms found.

**Task 3 — Bibliography audit and main.tex activation:**
- Collected all `\cite{}` keys across all six chapter files: five unique keys in use (ais2024biometricwarning, groupib2022laser, nist2026privacyframework, rjoub2023surveyxai, lim2025explicate). All five confirmed present in references.bib. The sixth key (oregonstate2026formatting) exists in references.bib but is not cited in any chapter — acceptable per plan.
- Uncommented `\renewcommand{\bibname}{References}` and `\bibliography{references}` in main.tex (lines 80-81, immediately before `\end{document}`).
- Confirmed `\bibliographystyle{ieeetr}` remains at line 58 in preamble.

## Deviations from Plan

None — plan executed exactly as written. All six BibTeX keys were already present in references.bib from Phase 8 seeding, so no new entries needed to be added.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes introduced. This plan is documentation-only.

## Known Stubs

None. All citation markers point to real BibTeX entries. Bibliography rendering is now active.

## Self-Check

- `\cite{ais2024biometricwarning,groupib2022laser}` confirmed present in 01_introduction.tex (line 3)
- `0.871` confirmed present in 01_introduction.tex (line 19)
- "still falls short on task-scam recall" confirmed absent from 01_introduction.tex
- `\cite{rjoub2023surveyxai}`, `\cite{lim2025explicate}`, `\cite{nist2026privacyframework}` confirmed present in 02_related_work_and_background.tex
- "7B model" confirmed present in 02_related_work_and_background.tex
- `\bibliography{references}` at line 81 of main.tex (no leading `%`)
- `\renewcommand{\bibname}{References}` at line 80 of main.tex (no leading `%`)
- `\bibliographystyle{ieeetr}` at line 58 of main.tex
- All 5 used citation keys confirmed in references.bib

## Self-Check: PASSED
