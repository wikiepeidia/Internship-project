# Phase 8: Thesis Structure and Evidence Map - Patterns

**Mapped:** 2026-05-26
**Scope:** documentation and report-planning artifacts only

## Summary

Phase 8 should copy its research shape from the existing `08-RESEARCH.md` and the supervisor reports, but copy its execution-plan granularity from `07-02-PLAN.md`. `05-04-PLAN.md` is still useful, but only as a secondary analog for explicit guardrails, acceptance criteria, and verification sections. For chapter-support tables, the strongest pattern is the chapter-by-chapter evidence mapping already inside `08-RESEARCH.md`, backed by concise factual evidence docs such as the Phase 5 release report, Phase 7 UAT, Phase 7 security audit, and the Phase 1 retained-artifact summary.

## Artifact Mapping

| New artifact | Role / flow | Best analogs | Why this matches |
| --- | --- | --- | --- |
| `08-RESEARCH.md` | research artifact / evidence synthesis | `08-RESEARCH.md`; `documents/reports/supervisor/report-08_2026-05-13_to_2026-05-14.md`; `documents/reports/supervisor/report-09_2026-05-15_to_2026-05-17.md` | The existing Phase 8 research file already uses thesis-specific sections such as chapter structure, evidence mapping, writing guardrails, and terminology replacement. The supervisor reports add the closest reader-facing tone for chapter-outline and writing-schedule notes. |
| `08-01-PLAN.md` | phase plan / small execution checklist | `.planning/phases/07-proposal-closeout-and-quantitative-validation/07-02-PLAN.md`; `.planning/phases/05-recall-priority-evaluation-and-release-gates/05-04-PLAN.md` | `07-02-PLAN.md` is the best concise plan analog because it uses direct sections, concrete artifacts, and explicit verification without excessive scaffolding. `05-04-PLAN.md` is the best secondary analog when Phase 8 needs requirement IDs, dependencies, or sharper acceptance criteria. |
| evidence-map table or chapter-support checklist | traceability table / chapter-to-evidence mapping | the `Evidence Mapping` section inside `08-RESEARCH.md`; `documents/reports/supervisor/report-08_2026-05-13_to_2026-05-14.md`; `.planning/phases/01-data-foundation-and-split-governance/01-06-SUMMARY.md`; `.planning/phases/05-recall-priority-evaluation-and-release-gates/05-release-eval-phase5-recovered-balanced-val.md`; `.planning/phases/07-proposal-closeout-and-quantitative-validation/07-UAT.md`; `.planning/phases/07-proposal-closeout-and-quantitative-validation/07-SECURITY.md` | The research note already shows the right row-per-chapter table structure. The supporting docs are compact, factual, and easy to mine into chapter-support rows without turning the checklist into draft prose. |

## Pattern Assignments

### `08-RESEARCH.md`

**Primary analog:** existing `08-RESEARCH.md`

**Secondary analogs:**

- `documents/reports/supervisor/report-08_2026-05-13_to_2026-05-14.md`
- `documents/reports/supervisor/report-09_2026-05-15_to_2026-05-17.md`

**Preserve these patterns:**

- Direct title line with the phase name plus `- Research`.
- A short metadata block near the top such as `Researched`, `Domain`, and `Confidence`.
- Constraint-first sectioning: constraints, requirements, summary, recommended structure, evidence mapping, writing guardrails, risks, and open questions.
- Tables as the main unit of organization for chapters, evidence, risks, sources, and terminology replacements.
- Thesis-facing wording in the body even though the file itself is internal planning support.

**Use the supervisor reports for tone and structure:**

- Number top sections simply when describing report structure or writing sequence.
- Keep bullets short and factual.
- Treat chapter outline and writing schedule as reader-facing report support, not workflow status logging.

### `08-01-PLAN.md`

**Primary analog:** `.planning/phases/07-proposal-closeout-and-quantitative-validation/07-02-PLAN.md`

**Secondary analog:** `.planning/phases/05-recall-priority-evaluation-and-release-gates/05-04-PLAN.md`

**Preserve from `07-02-PLAN.md`:**

- Zero-padded file naming and direct phase-plan heading.
- Brief YAML frontmatter.
- Compact sections in this order: `Objective`, optional `Current status note`, `Must haves`, `Artifacts`, `Verification`, `Success criteria`.
- Tasks phrased as concrete outputs, not abstract thinking goals.
- Verification checks near the bottom.

**Borrow selectively from `05-04-PLAN.md`:**

- explicit requirement IDs when they help;
- dependency and artifact lists when they clarify scope;
- acceptance-criteria rigor when the task needs a hard finish line.

**Granularity to preserve:**

Phase 8 should stay at small-task granularity. A good plan shape is 3-5 tasks such as:

- lock chapter order;
- build chapter-to-evidence table;
- add writing guardrails and terminology replacements;
- extract missing appendix-grade evidence tables;
- set the one-week drafting sequence.

Avoid copying the full XML-style wrapper from `05-04-PLAN.md` unless the docs phase grows into a much larger multi-step execution plan.

### Evidence-map table or chapter-support checklist

**Primary analog:** the `Evidence Mapping` section already inside `08-RESEARCH.md`

**Supporting analogs:**

- `.planning/phases/05-recall-priority-evaluation-and-release-gates/05-release-eval-phase5-recovered-balanced-val.md`
- `.planning/phases/07-proposal-closeout-and-quantitative-validation/07-UAT.md`
- `.planning/phases/07-proposal-closeout-and-quantitative-validation/07-SECURITY.md`
- `.planning/phases/01-data-foundation-and-split-governance/01-06-SUMMARY.md`
- `documents/reports/supervisor/report-08_2026-05-13_to_2026-05-14.md`

**Best table pattern:**

- one row per chapter or claim cluster;
- columns such as `Chapter`, `Claim`, `Primary repo evidence`, `Support type`, `Extraction note`, and `Caution`;
- factual evidence anchors first, then one caution field so later drafting does not overclaim.

**Best source split:**

- structure and chapter intent: `08-RESEARCH.md` plus supervisor reports;
- quantitative findings: Phase 5 release report;
- acceptance proof: Phase 7 UAT;
- safety and risk framing: Phase 7 security;
- dataset lineage and counts: Phase 1 summary plus manifests.

## Naming, Sectioning, and Granularity Patterns To Preserve

- Keep the zero-padded phase prefix in every internal artifact: `08-RESEARCH.md`, `08-01-PLAN.md`, `08-PATTERNS.md`.
- Keep one artifact per purpose. Research holds rationale and evidence options; plan holds actions; checklist or table holds chapter support.
- Prefer short heading ladders over deep nesting.
- Put the most decision-sensitive content high in the file: thesis scope, evidence discipline, writing guardrails, and chapter mapping.
- Use markdown tables whenever the document compares chapters, evidence, risks, or terminology.
- Keep execution tasks atomic enough that each task produces a visible artifact or table update.
- When a thesis-facing deliverable is written later, strip internal filenames and rewrite them as normal academic phrases.

## Likely Evidence Anchors For Thesis Chapters

- `documents/reports/supervisor/report-08_2026-05-13_to_2026-05-14.md` for the initial chapter outline and writing schedule.
- `documents/reports/supervisor/report-09_2026-05-15_to_2026-05-17.md` for the shift from technical progress to report-oriented outline.
- `.planning/phases/01-data-foundation-and-split-governance/01-06-SUMMARY.md` for dataset lineage, counts, and retained-artifact closure.
- `.planning/phases/05-recall-priority-evaluation-and-release-gates/05-release-eval-phase5-recovered-balanced-val.md` for final metrics, verdict, and explanation-quality flags.
- `.planning/phases/07-proposal-closeout-and-quantitative-validation/07-UAT.md` for acceptance-test evidence.
- `.planning/phases/07-proposal-closeout-and-quantitative-validation/07-SECURITY.md` for trust boundaries, threat register, and accepted-risk framing.
- `data/manifests/manifest-phase1-recovered-balanced-claude-v2.json` and `data/manifests/phase3-large-pilot-2026-05-14.json` as appendix-grade tables or figures rather than prose-heavy citations.

## Anti-Patterns

- Do not let thesis-facing deliverables read like `.planning` artifacts. Avoid terms such as `Phase 5`, `ROADMAP`, `STATE.md`, `UAT`, `GSD`, or `validation gap` in chapter prose.
- Do not use `.planning/PROJECT.md` or `.planning/ROADMAP.md` as primary thesis evidence. They are planning guardrails, not reader-facing proof.
- Do not copy the full complexity of `05-04-PLAN.md` into `08-01-PLAN.md`; Phase 8 needs small writing tasks, not a multi-wave engineering shell.
- Do not mix evidence inventory with draft prose. Keep tables and checklists factual, then write narrative separately in Phase 9 drafting.
- Do not cite only weighted F1 or only high-level success language. Evaluation support must carry macro F1, per-label recall, and the blocked verdict together.
- Do not leak raw internal review-pack or planning notation into thesis chapters. Convert filenames into academic labels such as `final held-out evaluation report`, `acceptance test summary`, and `security audit summary`.

## Strongest Analogs

- `08-RESEARCH.md` for thesis-phase research structure and chapter-to-evidence tables.
- `.planning/phases/07-proposal-closeout-and-quantitative-validation/07-02-PLAN.md` for concise, execution-ready plan layout.
- `.planning/phases/05-recall-priority-evaluation-and-release-gates/05-04-PLAN.md` for guardrail and acceptance-criteria rigor, used selectively.
- `documents/reports/supervisor/report-08_2026-05-13_to_2026-05-14.md` and `documents/reports/supervisor/report-09_2026-05-15_to_2026-05-17.md` for thesis/report tone and chapter-outline framing.
- `.planning/phases/05-recall-priority-evaluation-and-release-gates/05-release-eval-phase5-recovered-balanced-val.md`, `.planning/phases/07-proposal-closeout-and-quantitative-validation/07-UAT.md`, `.planning/phases/07-proposal-closeout-and-quantitative-validation/07-SECURITY.md`, and `.planning/phases/01-data-foundation-and-split-governance/01-06-SUMMARY.md` for chapter-support evidence rows.

## PATTERN MAPPING COMPLETE

`08-PATTERNS.md` now points Phase 8 toward thesis-specific research structure, a concise execution-plan shape, and evidence-table patterns that stay factual while keeping internal process jargon out of thesis-facing deliverables.
