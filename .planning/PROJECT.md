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

- [ ] Close the two remaining proposal-facing quantitative claims with one final validated 2,500-3,000 sample dataset artifact and one honest held-out evaluation report for the locked baseline winner.

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

## Current Milestone: v1.5 Content Gap Closure — Dataset & QLoRA

**Goal:** Fill the critical content gaps in both the thesis report and the defense slides: (1) dataset construction via tinnhiemmang.vn seed scraping and claude-3-5-haiku synthetic generation, and (2) QLoRA fine-tuning with verified hyperparameters and training metrics.

**Target features:**

- Slide 05 (Data Pipeline): visual TikZ block flow — tinnhiemmang.vn seeds → claude-3-5-haiku API → Pydantic Judge → JSONL Output — plus an inline JSONL snippet
- Slide 07 (Model): 2-column layout showing QLoRA constraints (r=16, α=32, NF4, loss=0.4951, 1,733s) and hardware rationale (6 GB VRAM, GGUF Q8_0 for CPU)
- Report Chapter 3: ≤1-paragraph dataset scraping section + claude-3-5-haiku generation prose + quality-judge stats
- Report Chapter 3/4: QLoRA training config table (r=16, α=32, checkpoint-505, loss=0.4951, 1,733s) with adapter→GGUF rationale
- All content written as intentional pipeline design — no 0.44 recall history, no "repaired" dataset language

## Current State

- Phase 1 remains complete and closed on the retained recovered dataset lineage.
- Phase 2 is complete: the repo has a shipped local heuristic runtime with typed contracts, a doctor command, a stdin-first CLI, `vnphish` console script wiring, and user-facing docs for the Phase 2 privacy boundary.
- Phase 3 is complete: the repo has a locked Qwen pilot catalog, real local PEFT and transformers training, completed retained-dataset adapter runs for `qwen3-4b-instruct-2507` and `qwen3.5-4b`, a real GGUF conversion path, a doctor-ready baseline GGUF runtime, and a real accelerated runner-up runtime.
- The consumer-laptop CPU or iGPU target is already satisfied as an inference requirement through the GGUF path. Training remains a GPU-capable local workflow, not a CPU-only objective.
- The base six-phase v1 milestone is complete, including the runtime-backed local demo UI and Phase 5/6 UAT closure.
- Immediate focus is now Phase 7 proposal closeout: finalize one validated 2,500-3,000 row dataset artifact, freeze seed-disjoint train/val/test splits with held-out risky-label coverage, retrain the locked baseline winner if needed, and generate one final held-out evaluation package that states whether the proposal F1 target was met.

---
Last updated: 2026-05-25 after the six-phase v1 implementation milestone closed and a new Phase 7 proposal-closeout milestone was queued
