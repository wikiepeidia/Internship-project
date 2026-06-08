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

### Active

- [ ] Replace AI-demo card layout with a bilingual Vietnamese/English chat-bubble interface (vanilla HTML/CSS/JS, no framework).

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

## Current Milestone: v2.0 Chat UI Revamp

**Goal:** Replace the AI-demo card layout with a bilingual Vietnamese/English chat-bubble interface that feels like a real messenger app.

**Target features:**

- Chat thread layout: user text appears as right-aligned bubble, bot reply as left-aligned bubble
- Bot reply: single structured bubble containing risk tier badge + Vietnamese verdict + grounded cues + safe next steps
- Bilingual UI text — Vietnamese primary, English for technical terms (e.g., Risk tier)
- Channel selector embedded in chat input bar (small pill or inline dropdown beside send button)
- Vanilla HTML/CSS/JS — no framework, no build step; Python WSGI backend unchanged

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

- All 13 phases complete across milestones v1.0, v1.2, v1.5.
- Thesis report and defense slides are content-complete and compile-clean.
- Project is ready for graduation submission or the next milestone.

---
Last updated: 2026-06-08 after milestone v1.5 (content gap closure) closed all phases complete
