---
phase: 34-speaking-script-qa-preparation
plan: "01"
subsystem: docs
tags: [presentation, qa-prep, defense]

requires:
  - phase: 33-emergency-10-minute-slide-compression
    provides: final 12-frame deck, 33-RUN-PLAN.md timing budget (~8:05)
provides:
  - Talking-point speaking script for all 12 defense slides, timed to the 8:05 budget
  - Comprehensive Q&A preparation document covering data governance, QLoRA internals, recall-floor rationale, and an explicit "does this look AI-generated" defense section
affects: [none — terminal phase of milestone v5.3]

tech-stack:
  added: []
  patterns: []

key-files:
  created:
    - documents/reports/supervisor/defense_speaking_script.md (gitignored — see note below)
    - documents/reports/supervisor/defense_qa_preparation.md (gitignored — see note below)
  modified: []

key-decisions:
  - "Deliverables written directly by the orchestrator rather than through the full discuss-phase/plan-phase/executor subagent pipeline — this is pure content-writing with no architectural ambiguity, and the defense is same-day-plus-one; subagent round-trips were the dominant remaining time cost, not writing itself."
  - "documents/reports/supervisor/ is gitignored project-wide (confirmed: the pre-existing mock_defense_script.md in the same directory was also never committed). Both new files intentionally follow that same convention rather than force-adding against .gitignore — this SUMMARY.md is the tracked record of their existence and content scope."
  - "Grounded every technical claim in the current locked thesis chapters (03_methodology_and_system_design.tex, 05_evaluation_and_discussion.tex) and current tables (qlora_config.tex, dataset_statistics.tex), not in the stale June mock_defense_script.md, which had different numbers (macro F1 0.9553 vs. current 0.9625) from an earlier report revision."
  - "Explicitly include the task_scam 0.44->0.871 recall-recovery story in the Q&A doc even though the locked report itself doesn't narrate it (per the Phase 13 GAP-08 writing guardrail against 'recovery' language) — reasoned that silence in the report isn't a contradiction with the presenter explaining real development history live, and this specific story is the strongest available answer to the judge's 'sounds AI-generated' concern since it demonstrates genuine diagnose-and-fix ownership."

requirements-completed: [SCRIPT-01, SCRIPT-02, SCRIPT-03, QA-01, QA-02, QA-03, QA-04]

coverage:
  - id: D1
    description: "Talking-point cues exist for all 12 main slides in current deck order, phrased as spoken fragments not full sentences"
    requirement: "SCRIPT-01, SCRIPT-03"
    verification:
      - kind: manual_procedural
        ref: "documents/reports/supervisor/defense_speaking_script.md — one section per slide, cue-bullet format throughout"
        status: pass
    human_judgment: false
  - id: D2
    description: "Speaking cues sized to the 33-RUN-PLAN.md ~8:05 timing budget"
    requirement: "SCRIPT-02"
    verification:
      - kind: manual_procedural
        ref: "Per-slide seconds table in defense_speaking_script.md sums to 485s (8:05), matching 33-RUN-PLAN.md's TIME-05 table exactly"
        status: pass
    human_judgment: false
  - id: D3
    description: "Q&A doc covers data pipeline/governance, QLoRA/model adaptation, architecture/privacy rationale, evaluation/metrics, limitations, and design-choice justifications"
    requirement: "QA-01"
    verification:
      - kind: manual_procedural
        ref: "defense_qa_preparation.md sections 1-6 cover each named area with numbered Q&A pairs"
        status: pass
    human_judgment: false
  - id: D4
    description: "Answers written in plain, first-person, explainable language with concrete numbers, not dense AI-polished prose"
    requirement: "QA-02"
    verification: []
    human_judgment: true
    rationale: "Prose register/tone is inherently a human-judgment call — the student should read the doc and confirm the voice feels usable and natural to actually say out loud, not just structurally correct."
  - id: D5
    description: "Q&A explicitly addresses the AI-generated-report concern with ready talking points"
    requirement: "QA-03"
    verification:
      - kind: manual_procedural
        ref: "defense_qa_preparation.md Section 0, placed first, directly addresses authorship questions with a concrete framing and an explicit 'what NOT to do'"
        status: pass
    human_judgment: false
  - id: D6
    description: "Q&A organized by topic for fast lookup"
    requirement: "QA-04"
    verification:
      - kind: manual_procedural
        ref: "8 numbered topic sections (0-8) plus a quick-reference numbers table (Section 7)"
        status: pass
    human_judgment: false

duration: ~50min
completed: 2026-07-14
status: complete
---

# Phase 34: Speaking Script & Q&A Preparation Summary

**Talking-point speaking script for all 12 defense slides (timed to 8:05) and a comprehensive, topic-organized Q&A preparation document — including a direct defense against the judge's "sounds AI-generated" concern, grounded in the current locked thesis chapters and exact reported numbers.**

## Performance

- **Duration:** ~50 min
- **Completed:** 2026-07-14
- **Tasks:** 2 (speaking script; Q&A prep) — executed directly, not through subagent plan/execute pipeline
- **Files created:** 2 (both intentionally gitignored per project convention)

## Accomplishments

- `documents/reports/supervisor/defense_speaking_script.md`: cue-based (not verbatim) talking points for all 12 slides in current deck order, with a per-slide timing table summing to exactly 485s / 8:05, matching `33-RUN-PLAN.md`'s TIME-05 budget
- `documents/reports/supervisor/defense_qa_preparation.md`: 9 sections covering — direct AI-generated-authorship defense (Section 0), data pipeline/governance including a plain-language explanation of the data-quality t-test statistics, QLoRA hyperparameters and the NF4-vs-Q8_0 dual-quantization rationale, deployment/runtime privacy-boundary reasoning, evaluation results and the recall-floor design rationale (0.90/0.90/0.80), the task_scam recall-recovery story (0.44→0.871) framed as a strength not a liability, broader design-rationale Q&A (why text-only, why these 4 classes, why explainability), a quick-reference numbers table, and guidance for genuinely-unknown-answer situations
- Reconciled a real numeric discrepancy: the prior `mock_defense_script.md` (2026-06-08/09) cited macro F1 0.9553 and an 8-slide structure; current locked chapters and the current 12-slide deck report macro F1 0.9625 — the new documents use only the current, verified numbers

## Task Commits

No commits — `documents/reports/supervisor/` is gitignored project-wide (the pre-existing `mock_defense_script.md` in the same directory was also never committed, confirmed via empty `git log` on that path). This SUMMARY.md, together with the requirements/roadmap tracking updates, is the committed record of this phase's work.

## Files Created/Modified

- `documents/reports/supervisor/defense_speaking_script.md` — 12-slide talking-point cues + timing checkpoint table (gitignored, not committed)
- `documents/reports/supervisor/defense_qa_preparation.md` — topic-organized Q&A prep, 9 sections (gitignored, not committed)

## Decisions Made

- Skipped the full discuss-phase → research → plan-phase → plan-checker → executor-in-worktree pipeline for this phase. This is pure content-writing grounded in already-verified facts, not a task with architectural ambiguity or code-correctness risk; given the same-day-plus-one deadline, direct execution was the responsible choice over process ceremony. Requirements were still gathered, confirmed, and roadmapped through the standard `/gsd-new-milestone` flow before writing began.
- Grounded every number against the live thesis chapters and tables rather than trusting memory or the stale mock script, which surfaced a real (already-superseded) numeric drift between report revisions.
- Deliberately included the task_scam recall-recovery narrative in the Q&A doc despite the report's Phase-13 writing guardrail against "recovery" language in the *report itself* — reasoned this is presenter-only material answering a live question, not a rewrite of the locked report, and that explaining real development history is the strongest available counter to an "AI-generated, no real understanding" concern.

## Deviations from Plan

None from the roadmap's stated success criteria — all 4 were met. The process deviation (direct execution, no subagent pipeline) is documented above under Decisions Made, not listed as a plan deviation since no PLAN.md was created to deviate from.

## Issues Encountered

None. `documents/reports/supervisor/` being gitignored was expected behavior once checked (matches the pre-existing file in the same directory), not a blocker — adjusted the commit approach accordingly rather than force-adding against the project's own ignore rule.

## User Setup Required

**Action required from the student before the defense:**
- Read both documents fully at least once tonight
- Do one full stopwatch rehearsal against the speaking script's timing table
- Re-read Q&A Section 0 (AI-generated concern) and Section 5 (task_scam recall story) until they can be delivered conversationally, not read

## Post-Ship Follow-Up (2026-07-14, same session)

The student asked for the Q&A doc to be reorganized and substantially deepened after reviewing it: more hostile/rapid-fire question styles, exact QLoRA hyperparameters (not just the summary-table subset), a "why are some F1 scores exactly 1.000 — is that believable" skepticism question, and a general "prove you understand statistics, not just quoted numbers" angle.

**Grounding work done:** dispatched a read-only Explore agent to pull the *actual* LoRA/QLoRA config straight from `src/model_adaptation/training.py` (not the summary table) — confirmed `r=16, alpha=32, dropout=0.05, bias=none, target_modules=` 7 modules (all attention + MLP projections), plus the real training-loop settings (batch size 1, grad-accum 4, lr=2e-4, 1 epoch), cross-checked against the saved `adapter_config.json` and `training-summary.json` for the shipped adapter.

**Training-hardware consistency check:** cross-referenced training-run provenance across all tracked artifacts and the locked thesis chapters. Confirmed the report's existing framing is internally consistent — it does not cite a specific training wall-clock time or device (by design, since that depends on the accelerator used), and no inconsistent claim exists anywhere in the tracked report or slides. Added a new Q&A section (§6, "Training Infrastructure") giving the student a report-consistent answer to use if asked about training hardware live.

**Also found and flagged (not fixed, out of scope):** a separate pre-existing file, `documents/presentation/simple-defense-QA.md` (dated 2026-06-16), cites an earlier superseded training run (macro F1 0.9553, 2,018/210/254 split) that no longer matches the current locked report (F1 0.9625, 2,333/254/413 split). Added an explicit note at the bottom of the reorganized doc telling the student not to cross-reference numbers between the two files.

**Reorganized structure** (`documents/reports/supervisor/defense_qa_preparation.md`, rewritten in place, same filename): §0 meta-strategy (expanded with "judges likely already assume AI was used — understanding is the actual test"), §1 rapid-fire one-liners, §2 general t-test literacy + application, §3 data governance, §4 full QLoRA hyperparameters with derivable-live checkpoint-count trick, §5 quantization, §6 training infrastructure (new), §7 evaluation incl. the F1=1.000 skepticism question (new), §8 task_scam story, §9 design rationale, §10 quick-reference table (expanded), §11 unknown-answer guidance, closing cross-reference-file warning.

## Next Phase Readiness

- Terminal phase of milestone v5.3 — no next phase planned.
- Recommended next GSD step: `/gsd-complete-milestone v5.3` once the student confirms the materials are usable, or simply proceed straight to the defense on 2026-07-15.

---
*Phase: 34-speaking-script-qa-preparation*
*Completed: 2026-07-14*
