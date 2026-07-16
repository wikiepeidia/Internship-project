# Milestones

## v2.0 v2.0 (Shipped: 2026-06-09)

**Phases completed:** 5 phases, 3 plans, 4 tasks

**Key accomplishments:**

- Static vanilla chat shell with Be Vietnam Pro, 100dvh layout, ARIA live thread, and clone-safe data-slot templates
- New file: `src/runtime/demo_assets/i18n.js`
- Rewritten: `src/runtime/demo_assets/demo.js`
- Modified: `src/runtime/demo_assets/i18n.js`
- Code fix: `src/runtime/demo_assets/demo.css`

---

## v2.1 Defense Corrections (Shipped: 2026-06-09)

**Status:** Complete

**Phases completed:** 3 phases (19, 20, 21)

**Key accomplishments:**

- Phase 19: Slide title → "Fine-Tuning a Local LLM for Vietnamese Financial Phishing Detection"; section reorder (Why Local? after Motivation); Training Pipeline naming; Pydantic gate note; API leak privacy frame (OpenAI March 2023 + Samsung 2023); 29-min label; two-stage NF4/Q8_0 quantization explanation; References slide — 16-page deck, zero errors
- Phase 20: Bar chart replaced with per-class metrics table; binary 2×2 confusion matrix added — binary F1 = 1.000 (perfect scam/benign separation)
- Phase 21: Chapter 2 jailbreak examples replaced with ChatGPT/cloud API data leakage incidents; thesis compiles clean (23 pages)

---

## v5.2 Emergency Slide Fix — 10-Minute Presentation (Shipped: 2026-07-13)

**Status:** Complete

**Phases completed:** 1 phase (33)

**Key accomplishments:**

- Deck compressed 15 → 12 main frames via 4 merges; Architecture/Data/Model sections confirmed byte-identical (zero methodology depth lost)
- Hidden 3-frame Beamer backup appendix for Q&A depth; title-slide date fixed
- Demo section synced to the 2 locked golden prompts; demo-in-slot decision locked in `33-RUN-PLAN.md`
- Final timing ~8:05, comfortably under the 10:00 target

Full detail: `.planning/milestones/v5.2-SUMMARY.md`

---

## v5.3 Slide Scripts & Q&A Preparation (Shipped: 2026-07-15, defense day)

**Status:** Complete

**Phases completed:** 1 phase (34), plus substantial same-milestone-tail work executed directly (untracked as formal phases, given the deadline)

**Key accomplishments:**

- Speaking script + topic-organized Q&A preparation document written for the live defense
- Slide iteration continued through defense eve: Demo cut to backup, Sample Output reinstated with a real live-verified golden-prompt run, a full report-vs-slides numeric audit (one model-name mismatch found and fixed), jargon trimmed from Evaluation/Contributions slides
- `defense-walkthrough` branch merged into `main`; all 10 code-walkthrough files heavily commented; real final datasets copied into `walkthrough/data/` with checksum verification
- Two new prep docs written under live pressure: `defense_walkthrough.md` (slide-anchored Q&A) and `defense_qa2.md` (live in-room judge-behavior notes captured during the actual defense)
- **Defense held 2026-07-15, complete.** Judges requested a report revision — see `.planning/PROJECT.md` Current Milestone section for the specific gaps raised live. Slides are now LOCKED.

Full detail: `.planning/milestones/v5.3-SUMMARY.md`

---
