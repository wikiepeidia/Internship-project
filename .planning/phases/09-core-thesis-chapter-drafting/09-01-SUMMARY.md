---
phase: "09"
plan: "01"
subsystem: thesis-evaluation-chapters
tags: [latex, thesis, evaluation, metrics-correction]
dependency_graph:
  requires: [08-01]
  provides: [correct-evaluation-tables, corrected-chapter-5, corrected-chapter-6]
  affects: [documents/reports/latex/tables/evaluation_snapshot.tex, documents/reports/latex/tables/milestone_summary.tex, documents/reports/latex/chapters/05_evaluation_and_discussion.tex, documents/reports/latex/chapters/06_conclusion_and_future_work.tex]
tech_stack:
  added: []
  patterns: [latex-tabular, per-label-metrics-prose]
key_files:
  created: []
  modified:
    - documents/reports/latex/tables/evaluation_snapshot.tex
    - documents/reports/latex/tables/milestone_summary.tex
    - documents/reports/latex/chapters/05_evaluation_and_discussion.tex
    - documents/reports/latex/chapters/06_conclusion_and_future_work.tex
decisions:
  - "Used 0.871 recall (not rounded 0.87) from frozen eval-snapshot-task-scam-recovery.json as authoritative value"
  - "Chapter 6 historical 0.44 reference rewritten without the decimal to satisfy verify constraint; narrative context preserved via 'well below the project safety floor' phrasing"
  - "Macro F1 reported as 0.955 in prose and 0.9553 in table, both derived from (0.9106+0.9796+0.9310+1.0)/4"
metrics:
  duration: "~15 minutes"
  completed: "2026-05-29T01:45:00Z"
  tasks_completed: 3
  tasks_total: 3
---

# Phase 09 Plan 01: Fix Stale Evaluation Numbers in Thesis Chapters Summary

All four thesis output files now report the authoritative final evaluation numbers (254 rows, task_scam recall 0.871, macro F1 0.9553, verdict PASS) sourced from the frozen eval-snapshot-task-scam-recovery.json artifact.

## What Was Done

### Task 1: Replace stale numbers in both evaluation tables

Rewrote `evaluation_snapshot.tex` completely. Key changes:

- "Held-out evaluation rows" changed from 210 to 254
- "Per-label support" updated from `18 task` to `62 task`
- "Release verdict" changed from "BLOCK; task-scam recall 0.44 below 0.90 floor" to "PASS; all risky class recall floors cleared"
- Removed stale "Weighted F1 0.8618" row (not in Phase 7a snapshot)
- Updated "Macro F1" from 0.7431 to 0.9553 with correct source anchor
- Added four new per-label metric rows (bank impersonation, zalo social engineering, task scam, benign) with recall/precision/F1 from the frozen JSON
- Retained "Explanation review summary" row unchanged (still valid as design caution evidence)

Rewrote `milestone_summary.tex` Final evaluation row: Status changed from "Release blocked" to "Complete"; completion note changed from "task-scam recall 0.44" to "PASS; task-scam recall 0.871".

### Task 2: Rewrite Chapter 5 with Phase 7a numbers and expanded honest interpretation

Rewrote `05_evaluation_and_discussion.tex`. Key changes:

- Opening paragraph: removed the sentence claiming "task-scam recall is still too low for a release recommendation"; replaced with honest framing that the system cleared recall floors but task-scam holdout remains small and two explanation cautions stand
- Section "Repaired-Holdout Results": fully replaced stale 210-row/0.44-recall/0.7431-F1 content with four paragraphs covering (1) the intermediate snapshot motivation, (2) the 254-row headline result (accuracy 0.957, macro F1 0.955), (3) per-class prose results, and (4) safety gate outcome with honest residual confusion notes
- Section "Interpretation": rewritten around the PASS verdict; retains both explanation quality flags as design caution notes; added `\cite{lim2025explicate}` comparison reference
- Section "Limits": updated with 18->62 task-scam support growth; notes residual bank/task confusion pattern
- No forbidden terms ("Phase 7a", "Phase 5", "BLOCK", "GSD", "UAT", "roadmap") appear anywhere in the chapter

### Task 3: Correct Chapter 6 conclusion

Updated `06_conclusion_and_future_work.tex`. Key changes:

- "What the Final Evaluation Means" section: fully rewritten with three paragraphs covering (1) headline: 254 rows, all floors cleared, task_scam recall 0.871; (2) honest qualification: small holdout, two explanation flags; (3) historical context: earlier small-holdout result described as "well below the project's safety floor" without using the 0.44 decimal (satisfying the verify constraint while preserving narrative context)
- Future Work section opening: updated from "improve task-scam detection rather than chase small gains" (implying task scam still broken) to "broaden the holdout evaluation and close the residual explanation quality gap rather than restart detection modeling from scratch"
- No forbidden terms appear

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Verify constraint conflict in Task 3**
- **Found during:** Task 3 verification
- **Issue:** The plan's action section says to write "An earlier evaluation run showed task-scam recall at 0.44 on only 18 examples" and "The improvement from 0.44 to 0.871..." but the verify section says `grep -c "0.44" 06_conclusion_and_future_work.tex` must return 0. These are contradictory.
- **Fix:** The verify constraint is the binding acceptance criterion. Rewrote Paragraph 3 to say "task-scam recall well below the project's safety floor, with only 18 held-out examples" and "The subsequent improvement to 0.871 recall on a larger holdout set of 62 examples" — preserving all narrative intent without the 0.44 decimal.
- **Files modified:** `documents/reports/latex/chapters/06_conclusion_and_future_work.tex`

## Known Stubs

None. All four files report real authoritative numbers sourced from the frozen evaluation artifact.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes introduced. All changes are LaTeX prose and table edits in thesis output files.

## Threat Mitigation Check (T-09-01, T-09-02, T-09-03)

- T-09-01 (Tampering): All row values verified against eval-snapshot-task-scam-recovery.json before commit. String-match acceptance criteria passed.
- T-09-02 (Information Disclosure): Forbidden-term scan complete. "Phase 7", "BLOCK", "0.44" absent from all prose files. Verified via grep.
- T-09-03 (Spoofing): Macro F1 = 0.9553 = (0.9106 + 0.9796 + 0.9310 + 1.0) / 4. Stale 0.7431 value removed.

## Self-Check

### Files created/modified

- `documents/reports/latex/tables/evaluation_snapshot.tex` — FOUND (gitignored, not committed)
- `documents/reports/latex/tables/milestone_summary.tex` — FOUND (gitignored, not committed)
- `documents/reports/latex/chapters/05_evaluation_and_discussion.tex` — FOUND (gitignored, not committed)
- `documents/reports/latex/chapters/06_conclusion_and_future_work.tex` — FOUND (gitignored, not committed)

### Verification results

| Check | Expected | Actual | Status |
|-------|----------|--------|--------|
| 0.44 in evaluation_snapshot.tex | 0 | 0 | PASS |
| 254 in evaluation_snapshot.tex | >=1 | 1 | PASS |
| 0.871 in ch05 | >=1 | 1 | PASS |
| 0.44 in ch06 | 0 | 0 | PASS |
| Phase 7 in ch05 | 0 | 0 | PASS |
| Phase 7 in ch06 | 0 | 0 | PASS |
| BLOCK in ch05 | 0 | 0 | PASS |
| 0.4444 in ch05 | 0 | 0 | PASS |
| 210 evaluated in ch05 | 0 | 0 | PASS |
| PASS in milestone_summary.tex | >=1 | 1 | PASS |
| 0.44 in milestone_summary.tex | 0 | 0 | PASS |

## Self-Check: PASSED
