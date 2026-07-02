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
- Milestone v2.2 complete and closed (2026-06-15/16): thesis reformatted to the USTH ICT Bachelor Thesis department template — cover page, certification letter, front matter order, abbreviations table, 5-section Roman numeral restructure, appendices, evaluation tables synced to slides.
- Milestone v3.0 complete and closed (2026-06-18): supervisor comments addressed — literature review added (20+ new citations), baseline Qwen3.5-4B comparison run added, synthetic-data-percentage stated explicitly, page count brought to department target.
- Milestone v4.0 complete and closed (2026-06-19/20): pre-print academic review passed (20 findings fixed) — thesis print-ready at 33 pages, 36 citations, 24 abbreviations, zero compile errors.
- Milestone v5.0 complete and closed (2026-06-20): final audit pass — report LOCKED for print.
- Phase 28 complete and corrected (2026-07-02): dev-machine baseline diagnostics passed; the final golden demo prompts are a no-OTP malicious-link Vietcombank scam and a legitimate VPBank Smart OTP benign notice, each locked through five stable real web-demo runs; the corrected warm-latency baseline is `22705.562 ms` for Phase 30 comparison.

### Active

- [ ] Verify the local demo runs reliably end-to-end (functional, offline, edge cases) on the presentation laptop before the defense window (13-20 July 2026).
- [ ] Fix known demo latency/performance issue.
- [ ] Fix CLI entrypoint confusion between `vnphish analyze` (text-only, no page) and `vnphish demo` (web UI).
- [ ] Fix any UI quirks surfaced during verification.
- [ ] Prepare a fallback (recording or screenshots) in case the live demo fails during the defense.

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

## Current Milestone: v5.1 Demo Verification & Presentation Readiness

**Goal:** Confirm the local demo runs reliably end-to-end on the presentation laptop before the 13-20 July 2026 defense window, fix known issues, and prep a fallback in case the live demo fails.

**Target features:**

- End-to-end functional verification: sample scam + benign messages across all in-scope threat classes, confirm risk tier + explanation + safe-steps output
- Offline/portability check on the presentation laptop (no network calls, model loads from local artifact root)
- Edge case handling verification (empty input, very long text, malformed/non-scam text)
- Fix: demo latency/performance issue
- Fix: CLI entrypoint confusion between `vnphish analyze` (text-only, no page) and `vnphish demo` (web UI)
- Fix: any UI quirks surfaced during verification
- Fallback plan: recorded screen capture or screenshots as backup if the live demo fails during defense

## Completed Milestone: v2.2 Report Formatting — Department Template

**Closed:** 2026-06-15/16

**Delivered:**

- Cover page: "BACHELOR THESIS" label + "By / Title:" layout matching department template
- Supervisor certification letter page added
- List of Abbreviations section added (2-column table)
- Abstract: 6 English keywords + ≤250 words (125 words)
- Front matter order: TOC → Acknowledgements → List of Abbreviations → List of Tables → List of Figures → Abstract
- Restructured 6 numbered chapters → 5 Roman numeral sections via `\thesissection` macro (figure/table numbering preserved)
- Appendices section added
- Slides scanned and "Chapter X" references fixed
- Binary per-class metrics table and 2×2 confusion matrix synced to Results section

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

- All phases across milestones v1.0–v5.0 are complete and closed.
- Thesis report is print-ready and LOCKED (33 pages, 36 citations, 24 abbreviations, zero compile errors).
- v5.1 is active: Phase 28 closed and corrected the dev-machine baseline plus no-OTP golden-prompt lock; Phase 29 now verifies the actual presentation-laptop environment, offline behavior, and portability before the 13-20 July 2026 defense presentation.

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
Last updated: 2026-07-02 after Phase 28 no-OTP golden-prompt correction — Phase 29 environment parity is next
