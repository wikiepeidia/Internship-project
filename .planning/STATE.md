---
gsd_state_version: 1.0
milestone: v2
milestone_name: thesis-report
status: planning
last_updated: "2026-05-14T00:00:00.000Z"
progress:
  total_phases: 3
  completed_phases: 0
  total_plans: 9
  completed_plans: 0
  percent: 0
---

# STATE: Localized Explainable AI (XAI) Engine for Vietnamese Financial Phishing and Threat Detection

## Project Reference

- Core value: Users can safely verify suspicious Vietnamese financial messages on-device with explainable, high-recall detection that minimizes dangerous misses.
- Current milestone focus: Plan a thesis-grade, judge-facing report that synthesizes implemented Phases 1-3 and specifies pending Phases 4-5 as planned future work.
- Hard constraints:
  - Do not present pending Phase 4 and Phase 5 work as implemented or validated results
  - Keep thesis claims tied to reproducible repo artifacts and supervisor reports
  - Build a dated writing and review path for 2026-05-18 to 2026-05-31

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements

- Current phase: Not started - thesis-report roadmap definition
- Current plan: Milestone v2 Thesis Report is open. The next action is to plan Phase 6, starting with chapter architecture and artifact inventory.
- Project status: Product Phases 1, 2, and 3 are complete. Product Phases 4 and 5 remain pending implementation and are inputs to the thesis specification, not completed results.
- Overall progress: Thesis-report milestone planning has started; execution has not begun.
- Progress bar: [-----] 0%

## Milestone Targets

- Documentation target: Every major completed claim links back to reproducible repo artifacts or supervisor reports.
- Planning target: Pending threat-detection and evaluation work is specified clearly enough for later implementation without status leakage.
- Scheduling target: Writing and review work is broken down across 2026-05-18 to 2026-05-31.
- Submission target: The milestone finishes with a judge-facing readiness checklist.

## Accumulated Context

### Decisions Locked

- Keep v1 strictly text-only to protect scope and delivery certainty.
- Use localized adaptation of an open local model family via LoRA, with a 4B-primary path for 8GB VRAM and optional larger comparison candidates.
- Enforce structured explainability output, not binary-only labels.
- Use explicit release gates that prioritize recall to reduce dangerous false negatives.
- Phase 3 is now planned around a Qwen pilot with a 4B primary path, a three-model comparison, and adapter plus GGUF artifacts for the winner and runner-up.
- Treat v2 as a thesis-report milestone for judge-facing planning rather than a product-release label.
- Use Phases 1-3 as implemented evidence and Phases 4-5 as planned specification inputs in all thesis materials.

### Requirement Coverage Snapshot

- Product v1 requirements mapped: 16
- Thesis-report milestone requirements defined: 8
- Immediate roadmap phases for this milestone: 6, 7, 8

### Active Risks and Watchpoints

- Data leakage risk between training and evaluation splits.
- Explanation hallucination risk without strict evidence-linking.
- Quantization regressions that reduce recall on high-harm scam classes.
- Mixed-language/code-switch robustness drift over time.
- Primary live seed sources remain brittle in this environment (`canhbao.khonggianmang.vn` DNS failure, `scam.vn` HTTP 403); `tinnhiemmang.vn/canh-bao-lua-dao` is the current working fallback.
- Thesis status-leak risk: pending Phase 4 and Phase 5 work must stay clearly labeled as planned rather than completed.
- Short writing-window risk: the report plan needs explicit sequencing across 2026-05-18 to 2026-05-31.

## Session Continuity

- Last session: 2026-05-14
- Stopped at: Milestone v2 Thesis Report initialized with research-backed requirements and a roadmap for Phases 6-8. The next step is Phase 6 planning.
- Local model artifacts intentionally live off-repo at `D:\PROJEct\AI MODELS`; `.env/.env` overrides `MODEL_ARTIFACT_ROOT` and `MODEL_REGISTRY_PATH` there to avoid OneDrive sync interference and costly redownloads.
- The three locked Qwen base checkpoints are already downloaded under `D:\PROJEct\AI MODELS\base`, with a local download manifest at `D:\PROJEct\AI MODELS\manifests\download-manifest.json`, so future work should reuse those files instead of downloading again.
- Resume file: none
- Next command: /gsd-plan-phase 6
