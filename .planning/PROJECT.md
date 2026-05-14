# Localized Explainable AI (XAI) Engine for Vietnamese Financial Phishing and Threat Detection

## What This Is

This project builds a localized, offline-capable LLM system that detects, classifies, and explains Vietnamese financial phishing and social engineering messages from raw text. It is designed for general consumers who want zero-prompt verification of suspicious communications without sending private data to cloud APIs. The system prioritizes high-recall threat detection and actionable, understandable explanations.

## Core Value

Users can safely verify suspicious Vietnamese financial messages on-device with explainable, high-recall detection that minimizes dangerous misses.

## Current Milestone: v2 Thesis Report

**Goal:** Produce a thesis-grade report plan that synthesizes completed project evidence, translates pending detection and evaluation work into explicit specification chapters, and prepares a dated writing path for judge-facing submission.

**Target outcomes:**

- Lock a chapter architecture and evidence inventory that cleanly separates implemented work from planned future work.
- Define thesis-ready specification chapters for Phase 4 threat detection/explainability and Phase 5 evaluation/release gates.
- Produce a dated writing and review window for 2026-05-18 to 2026-05-31 plus final readiness criteria for judge handoff.

## Requirements

### Validated

- Phase 1 complete and closed (implementation 2026-04-20, retained artifact closure 2026-05-07): reproducible data foundation established with seed scraping, synthetic generation, recovered-artifact curation, quality judging, deterministic split governance, and SHA256 manifest verification.
- Phase 2 complete (2026-05-09): local/offline text ingestion, privacy-safe runtime contracts, and stdin-first analyzer flow are in place.
- Phase 3 complete (2026-05-11): local model adaptation scaffolding, GGUF baseline runtime selection, accelerated local profile support, and model artifact guidance are in place.

### Active

- [ ] Synthesize Phases 1-3 into a thesis-ready evidence baseline with reproducible references to datasets, manifests, runtime code, and model artifacts.
- [ ] Define the pending Phase 4 and Phase 5 work as planned report chapters without overstating implementation status.
- [ ] Produce a dated writing and review plan for 2026-05-18 to 2026-05-31 for the judge-facing thesis package.

### Out of Scope

- Image processing, computer vision, OCR, and screenshot analysis — v1 scope is strictly raw text inputs only.
- Generic broad cybersecurity assistant behaviors beyond financial phishing/social engineering triage — focus is narrow, domain-specific fraud detection.

## Context

The project addresses two core failures in cloud LLM use for fraud checks: privacy risk when users paste sensitive financial text, and weak recognition of local Vietnamese scam patterns, slang, and spoofing tactics. Input sources are copied raw text from channels such as SMS, Zalo, Messenger, Telegram, and Facebook. Threat classes in scope include bank impersonation with malicious domains, account-takeover/social-engineering scams (including compromised contact trust abuse), and "light work, high pay" employment task scams. The initial data pipeline will scrape seed threats from Vietnam NCSC, expand to 2,000-3,000 synthetic JSONL samples via frontier LLM API, then fine-tune an open local model family with LoRA through a 4B-primary path for 8GB VRAM, quantize selected artifacts to GGUF for local inference, and evaluate against an F1 target of >= 0.85 with recall emphasized. The current v2 milestone is a documentation and planning track for a thesis-grade report that will be handed to the judge and supervisor. It must synthesize completed work from Phases 1-3, preserve pending Phases 4-5 as planned future work, and avoid any language that implies the unfinished detection and evaluation stack has already been delivered.

## Constraints

- **Input Scope**: Raw text only (Vietnamese + mixed Vietnamese-English) — maintain strict v1 boundaries and reduce implementation surface.
- **Privacy**: Offline-capable inference for user-facing checks — sensitive financial text should not require cloud API submission.
- **Deployment Target**: Consumer laptops (CPU/iGPU) as baseline with GGUF quantization; optional prosumer GPU acceleration — maximize practical accessibility.
- **Model Strategy**: Parameter-efficient LoRA fine-tuning on an open-source local model family with a 4B-primary path and optional larger comparison candidates — balance capability with local deployment feasibility.
- **Data Source Dependency**: NCSC seed extraction quality impacts downstream synthetic data quality — pipeline reliability is critical.
- **Evaluation Policy**: Balanced acceptance gate (recall, explanation quality, latency), with aggressive recall priority — reduce false negatives in safety-critical context.

## Key Decisions

| Decision | Rationale | Outcome |
| ---------- | ----------- | ------- |
| Keep v1 strictly text-only | Tight scope improves delivery speed and quality for highest-risk channel | — Pending |
| Use localized domain fine-tuning instead of general cloud prompting | Better fit for Vietnamese fraud patterns and privacy requirements | — Pending |
| Optimize baseline runtime for consumer laptops via GGUF quantization | Enables broad real-world access without dedicated GPU | — Pending |
| Require explainable structured output, not binary labels | Vulnerable users need actionable reasoning and recommendations | — Pending |
| Prioritize recall in evaluation while using balanced release gates | Missing a true threat is costlier than false alarms | — Pending |
| Treat v2 as a thesis-report milestone, not a product-release label | Supervisor/judge planning is needed before the remaining implementation closes | Accepted 2026-05-14 |
| Separate implemented evidence (Phases 1-3) from planned work (Phases 4-5) in all report language | Prevents false completion claims in judge-facing material | Accepted 2026-05-14 |

## Current State

- Product implementation remains mid-v1: Phase 1, Phase 2, and Phase 3 are complete and provide the evidence base for the report.
- Phase 4 threat detection/explainable decisioning and Phase 5 evaluation/release gates remain pending product work and will be represented as planned specification chapters in the thesis.
- The active milestone is v2 Thesis Report, a documentation and planning track for judge-facing submission rather than a claim of product completion.
- Next focus: Phase 6 thesis architecture and evidence baseline.

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):

1. Requirements invalidated? -> Move to Out of Scope with reason
2. Requirements validated? -> Move to Validated with phase reference
3. New requirements emerged? -> Add to Active
4. Decisions to log? -> Add to Key Decisions
5. "What This Is" still accurate? -> Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):

1. Full review of all sections
2. Core Value check - still the right priority?
3. Audit Out of Scope - reasons still valid?
4. Update Context with current state

---
Last updated: 2026-05-14 for v2 thesis-report planning
