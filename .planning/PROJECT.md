# Localized Explainable AI (XAI) Engine for Vietnamese Financial Phishing and Threat Detection

## What This Is

This project builds a localized, offline-capable LLM system that detects, classifies, and explains Vietnamese financial phishing and social engineering messages from raw text. It is designed for general consumers who want zero-prompt verification of suspicious communications without sending private data to cloud APIs. The system prioritizes high-recall threat detection and actionable, understandable explanations.

## Core Value

Users can safely verify suspicious Vietnamese financial messages on-device with explainable, high-recall detection that minimizes dangerous misses.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Build an offline-first text-only threat analysis pipeline for Vietnamese and mixed Vietnamese-English scam messages.
- [ ] Generate explainable structured outputs with threat reasoning and clear user recommendations.
- [ ] Achieve production-ready local inference with strong phishing recall and robust end-to-end evaluation.

### Out of Scope

- Image processing, computer vision, OCR, and screenshot analysis — v1 scope is strictly raw text inputs only.
- Generic broad cybersecurity assistant behaviors beyond financial phishing/social engineering triage — focus is narrow, domain-specific fraud detection.

## Context

The project addresses two core failures in cloud LLM use for fraud checks: privacy risk when users paste sensitive financial text, and weak recognition of local Vietnamese scam patterns, slang, and spoofing tactics. Input sources are copied raw text from channels such as SMS, Zalo, Messenger, Telegram, and Facebook. Threat classes in scope include bank impersonation with malicious domains, account-takeover/social-engineering scams (including compromised contact trust abuse), and "light work, high pay" employment task scams. The initial data pipeline will scrape seed threats from Vietnam NCSC, expand to 2,000-3,000 synthetic JSONL samples via frontier LLM API, then fine-tune an open 8B model with LoRA, quantize to GGUF for local inference, and evaluate against an F1 target of >= 0.85 with recall emphasized.

## Constraints

- **Input Scope**: Raw text only (Vietnamese + mixed Vietnamese-English) — maintain strict v1 boundaries and reduce implementation surface.
- **Privacy**: Offline-capable inference for user-facing checks — sensitive financial text should not require cloud API submission.
- **Deployment Target**: Consumer laptops (CPU/iGPU) as baseline with GGUF quantization; optional prosumer GPU acceleration — maximize practical accessibility.
- **Model Strategy**: Parameter-efficient LoRA fine-tuning on open-source 8B model — balance capability with local deployment feasibility.
- **Data Source Dependency**: NCSC seed extraction quality impacts downstream synthetic data quality — pipeline reliability is critical.
- **Evaluation Policy**: Balanced acceptance gate (recall, explanation quality, latency), with aggressive recall priority — reduce false negatives in safety-critical context.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Keep v1 strictly text-only | Tight scope improves delivery speed and quality for highest-risk channel | — Pending |
| Use localized domain fine-tuning instead of general cloud prompting | Better fit for Vietnamese fraud patterns and privacy requirements | — Pending |
| Optimize baseline runtime for consumer laptops via GGUF quantization | Enables broad real-world access without dedicated GPU | — Pending |
| Require explainable structured output, not binary labels | Vulnerable users need actionable reasoning and recommendations | — Pending |
| Prioritize recall in evaluation while using balanced release gates | Missing a true threat is costlier than false alarms | — Pending |

---
*Last updated: 2026-03-18 after initialization*