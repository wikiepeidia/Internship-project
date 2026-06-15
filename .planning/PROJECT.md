# Localized Explainable AI (XAI) Engine for Vietnamese Financial Phishing and Threat Detection

## What This Is

This project builds a localized, offline-capable LLM system that detects, classifies, and explains Vietnamese financial phishing and social engineering messages from raw text. It is designed for general consumers who want zero-prompt verification of suspicious communications without sending private data to cloud APIs. The system prioritizes high-recall threat detection and actionable, understandable explanations.

## Core Value

Users can safely verify suspicious Vietnamese financial messages on-device with explainable, high-recall detection that minimizes dangerous misses.

## Requirements

### Validated

- Phase 1 complete and closed (implementation 2026-04-20, retained artifact closure 2026-05-07): reproducible data foundation established with seed scraping, synthetic generation, recovered-artifact curation, quality judging, deterministic split governance, and SHA256 manifest verification.
- Phase 4 complete and closed (implementation plus UAT/security closeout 2026-05-25): the local runtime now returns stable risk tiers, in-scope threat labels, grounded cues, and safe next steps through the shipped GGUF and accelerated paths, with fail-closed doctor-backed defaults.
- Phase 6 complete and closed (implementation plus UAT closeout 2026-05-25): the repo now ships a defense-ready local demo UI over the existing runtime contract and keeps the interface text-only and local-first.
- Phase 14 complete and closed (2026-06-08): the local demo now has a static chat-shell scaffold with Be Vietnam Pro, `100dvh`, a page-load ARIA live thread, a pinned safe-area composer, and clone-safe `data-slot` templates.

### Active

- [ ] Reformat LaTeX thesis to USTH ICT Bachelor Thesis department template: cover page, certification letter, front matter structure, 5-section Roman numeral restructure, abbreviations, appendices, evaluation tables sync.

### Out of Scope

- Image processing, computer vision, OCR, and screenshot analysis — v1 scope is strictly raw text inputs only.
- Generic broad cybersecurity assistant behaviors beyond financial phishing/social engineering triage — focus is narrow, domain-specific fraud detection.

## Context

The project addresses two core failures in cloud LLM use for fraud checks: privacy risk when users paste sensitive financial text, and weak recognition of local Vietnamese scam patterns, slang, and spoofing tactics. Input sources are copied raw text from channels such as SMS, Zalo, Messenger, Telegram, and Facebook. Threat classes in scope include bank impersonation with malicious domains, account-takeover/social-engineering scams (including compromised contact trust abuse), and "light work, high pay" employment task scams. The initial data pipeline will scrape seed threats from Vietnam NCSC, expand to 2,000-3,000 synthetic JSONL samples via frontier LLM API, then fine-tune an open local model family with LoRA through a 4B-primary path for 8GB VRAM, quantize selected artifacts to GGUF for local inference, and evaluate against an F1 target of >= 0.85 with recall emphasized.

## Constraints

- **Input Scope**: Raw text only (Vietnamese + mixed Vietnamese-English) — maintain strict v1 boundaries and reduce implementation surface.
- **Privacy**: Offline-capable inference for user-facing checks — sensitive financial text should not require cloud API submission.
- **Deployment Target**: Consumer laptops (CPU/iGPU) as baseline with GGUF quantization; optional prosumer GPU acceleration — maximize practical accessibility.
- **Model Strategy**: Parameter-efficient LoRA fine-tuning on an open-source local model family with a 4B-primary path and optional larger comparison candidates — balance capability with local deployment feasibility.
- **Data Source Dependency**: NCSC seed extraction quality impacts downstream synthetic data quality — pipeline reliability is critical.
- **Evaluation Policy**: Recall-first release gate with explicit explanation review and paired markdown plus JSON artifacts — reduce dangerous false negatives without hiding review context.

## Key Decisions

| Decision | Rationale | Outcome |
| ---------- | ----------- | ------- |
| Keep v1 strictly text-only | Tight scope improves delivery speed and quality for highest-risk channel | — Pending |
| Use localized domain fine-tuning instead of general cloud prompting | Better fit for Vietnamese fraud patterns and privacy requirements | — Pending |
| Optimize baseline runtime for consumer laptops via GGUF quantization | Enables broad real-world access without dedicated GPU | — Pending |
| Require explainable structured output, not binary labels | Vulnerable users need actionable reasoning and recommendations | — Pending |
| Use explicit recall-first release gates with explanation review and `PASS/BLOCK/FLAG` artifacts | Missing a true threat is costlier than false alarms, and the release decision must stay reviewable | Accepted 2026-05-25 |
| Lock `qwen3-4b-instruct-2507` as the laptop baseline winner and `qwen3.5-4b` as the runner-up for local training/deployment | Larger local pilot on 33 balanced validated samples kept the 4B baseline rule while favoring the best latency and memory fit under the 8GB-VRAM target | Accepted 2026-05-14 |
| Add a proposal-aligned minimal local demo UI as a separate final milestone phase after release gates | The proposal promises a non-technical zero-prompt interface, but Phase 5 should stay focused on evaluation and release readiness first | Accepted 2026-05-25 |
| Start a dedicated Phase 7 closeout milestone for dataset-scale and held-out-metric proof | The shipped six-phase v1 implementation is complete, but the school-facing quantitative claims still need one frozen dataset artifact and one valid final evaluation run | Accepted 2026-05-25 |

## Current Milestone: v2.2 Report Formatting — Department Template

**Goal:** Reformat the LaTeX thesis to comply with the USTH ICT Bachelor Thesis department template; sync slides and any missing evaluation tables.

**Target features:**

- Cover page: "BACHELOR THESIS" label + "By / Title:" layout matching department template
- Supervisor certification letter page (currently missing)
- List of Abbreviations section (currently missing)
- Abstract: 6 English keywords + ≤250 words
- Front matter order: TOC → Acknowledgements → List of Abbreviations → List of Tables → List of Figures → Abstract
- Restructure 6 numbered chapters → 5 Roman numeral sections (I/ Introduction, II/ Objectives, III/ Materials & Methods, IV/ Results & Discussion, V/ Conclusion & Perspective)
- Appendices section (currently missing)
- Slides: scan + fix any "Chapter X" references
- Results section: add/sync binary per-class metrics table and 2×2 confusion matrix to match slide content

## Completed Milestone: v2.1 Defense Corrections

**Closed:** 2026-06-09

**Delivered:**

- Slides fixed per supervisor feedback: title, TOC ordering, pipeline naming, Pydantic gate, QLoRA/GGUF explanation, training time unit
- Privacy section reframed with OpenAI March 2023 + Samsung 2023 API leakage incidents
- Binary evaluation: bar charts replaced with per-class metrics table; 2×2 confusion matrix added (binary F1 = 1.000)
- Thesis Chapter 2: jailbreak examples replaced with cloud API data leakage incidents; 23 pages compile clean
- All 11 v2.1 requirements (SLIDE-01–07, EVAL-04–05, REPORT-01–02) met

## Completed Milestone: v2.0 Chat UI Revamp

**Closed:** 2026-06-09

**Delivered:**

- Bilingual Vietnamese/English chat-bubble interface (vanilla HTML/CSS/JS, no framework)
- `i18n.js` bilingual string table served as a static asset
- Full fetch lifecycle: user bubble, typing indicator, bot bubble, error bubble, AbortController, in-memory history
- Collapsible `<details>` sections, bubble entrance animations, clear button, sample button auto-submit
- `100dvh` + `flex: 1 1 0` + `env(safe-area-inset-bottom)` mobile viewport; screen reader ARIA live region

## Completed Milestone: v1.5 Content Gap Closure — Dataset & QLoRA

**Closed:** 2026-06-08

**Delivered:**

- Slide 05 (Data Pipeline): TikZ 4-step block flow (tinnhiemmang.vn → claude-3-5-haiku → Pydantic Judge → JSONL Output) + inline JSONL schema snippet. Arrow labels removed to prevent overlap.
- Slide 07 (Model): 2-column block layout — QLoRA config (r=16, α=32, NF4, step-505, loss=0.4951, 1,733s) left; hardware rationale (6 GB VRAM, GGUF Q8_0, ~13s CPU) right. All tabular labels shortened to prevent hbox overflow.
- Slide 06 (Why Local): cloud_vs_local figure widened, full-width scalebox 0.85, bullets below.
- Report Chapter 3: tinnhiemmang.vn + claude-3-5-haiku generation in data section; QLoRA forward pass equation h=W₀x+(α/r)BAx; training config table (tables/qlora_config.tex).
- Thesis system overview figure: redesigned wider with CVBLUE/charcoal headers — fits A4 without resizebox.
- All [?] citation issues resolved via bibtex pass. Both thesis and slides compile zero errors.

## Current State

- All 21 phases across milestones v1.0–v2.1 are complete and closed.
- Thesis content and defense slides are complete and compile-clean (XeLaTeX, 23 pages).
- v2.2 starts: reformatting the thesis report to match the USTH ICT Bachelor Thesis department template.

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):

1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):

1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
Last updated: 2026-06-15 after v2.2 milestone started — department template formatting
