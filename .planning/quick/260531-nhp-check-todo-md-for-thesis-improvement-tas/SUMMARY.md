---
quick_task: "260531-nhp"
slug: "check-todo-md-for-thesis-improvement-tas"
status: complete
completed_at: "2026-05-31T10:00:00Z"
---

# Quick Task Summary

## Verdict

No top-level TODO item is inherently out of scope for the current GSD project. The active milestone is thesis writing and evidence packaging, so architecture figures, tables, citations, error analysis, and submission polish all fit the current Phase 8-10 deliverables.

The scope risks are narrower:

- some TODO details are stale relative to the current repaired holdout,
- some items stay in scope only if they document the implemented system rather than imply new product work,
- some optional measurements stay in scope only when backed by existing tracked evidence.

## Task-by-Task Assessment

1. Task 1, architecture figure: in scope. It documents the implemented text-only pipeline and matches the current thesis-polish milestone.
2. Task 2, dataset statistics: in scope. Use the frozen dataset and split artifacts that actually exist; do not invent extra provenance claims.
3. Task 3, confusion matrix: in scope, but it must use the current repaired-holdout result set rather than the older blocked run.
4. Task 4, error analysis: in scope, but the TODO text is stale. It still cites the older 210-row, 18-task-scam, 0.44-recall result, while the current closeout state records 254 held-out rows, 62 task-scam rows, and task-scam recall 0.871.
5. Task 5, references and citations: in scope. The exclusions in TODO are correct: do not add SHAP or LIME because they are not part of the implemented system.
6. Task 6, example explainability output: in scope if it mirrors the shipped runtime contract: risk tier, threat labels, grounded cues, and safe recommendations.
7. Task 7, Phase 3 pilot screening: in scope if it remains an engineering screening narrative and not a statistical benchmark claim.
8. Task 8, hardware and runtime characteristics: in scope for descriptive hardware profiles and any already measured runtime facts. It becomes a scope stretch only if it turns into a new benchmarking campaign not supported by tracked artifacts.
9. Task 9, threat model section: in scope and aligned with the locked text-only boundary.
10. Task 10, data pipeline figure: in scope as documentation of the existing dataset lineage.
11. Task 11, runtime architecture figure: in scope if it reflects the implemented CLI, runtime service, backend selection, and renderer. It is out of scope if it introduces unimplemented subsystems or cloud behavior.
12. Task 12, future work expansion: in scope only as future work. Multimodal, OCR, screenshot, and image-based fraud detection must remain explicitly deferred and must not be written as present capability.

## Practical Out-of-Scope Lines

The following interpretations would go out of scope for this project:

- adding or implying OCR, image, audio, voice, QR, APK, or multimodal detection as implemented work,
- introducing cloud inference or generic cybersecurity-assistant claims,
- running brand-new large benchmark or hardware-measurement campaigns just to satisfy thesis polish,
- rewriting future work into a new product roadmap unrelated to the current evidence base.

## Follow-up Notes

- The biggest immediate issue is staleness, not scope: TODO Task 4 still reflects the pre-recovery evaluation numbers.
- The current milestone already frames the work as documentation-first, so the safest next step is to refresh stale TODO details and then execute the remaining thesis-polish items against existing artifacts.
