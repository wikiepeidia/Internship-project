# Feature Landscape: Localized Explainable AI for Vietnamese Financial Scam Detection

Domain: Vietnamese financial scam/phishing detection from raw text
Researched: 2026-03-18
Scope anchor (v1): text-only Vietnamese + mixed EN/VI, explainable output, privacy/offline-first

## Framing

This domain typically combines three product layers:
1. Threat classification from short, noisy user text (SMS/chat/social messages).
2. Explainable risk communication that non-technical users can act on immediately.
3. Privacy-preserving deployment (on-device or hybrid modes) for sensitive financial content.

For this project, the roadmap should treat on-device explainability and local language fit as non-negotiable table stakes, not premium extras.

## Table Stakes

Features users expect for a credible Vietnamese scam checker. Missing any of these makes the product feel unsafe or incomplete.

| Feature | Why Expected | Complexity | Key Dependencies |
|---|---|---|---|
| Text ingestion for pasted messages (VN + mixed EN/VI) | Users copy from SMS/Zalo/Messenger/Telegram/Facebook into a checker | Low | Input normalization, Unicode handling, language-mix tokenizer |
| Financial-scam risk classification (benign/suspicious/high risk) | Core promise is threat triage | Medium | Domain dataset, fine-tuned model, threshold calibration |
| Threat type labeling (bank impersonation, account takeover social engineering, job/task scam) | Users need to know what kind of scam this is | Medium | Taxonomy design, labeled examples, multi-class inference |
| Explainable output with evidence spans | Users must see why the system flagged the text | Medium | Rationale generation schema, phrase-level indicators, explanation quality checks |
| Actionable recommendations | Product utility depends on clear next steps, not just labels | Low | Policy templates, threat-to-action mapping, localized wording |
| Offline-first inference mode | Financial text privacy is a first-order requirement | High | Quantized local model runtime, packaging, device compatibility |
| Recall-focused safety tuning with evaluation gate | Missing real scams is high-cost; users expect conservative safety behavior | Medium | Evaluation set, recall/F1 tracking, threshold policy |
| Structured result schema for downstream UX | Stable output required for UI, logging, and future integrations | Low | JSON schema, validator, contract tests |

Category summary:
- Category complexity: Medium-High overall (mostly due to local inference and robust explanation quality).
- Category key dependencies: high-quality VN scam corpus, robust labeling taxonomy, local model optimization (LoRA + quantization), evaluation pipeline emphasizing recall.

## Differentiators

Features that can materially separate this product from generic scam checkers, while still fitting v1 constraints.

| Feature | Value Proposition | Complexity | Key Dependencies |
|---|---|---|---|
| Vietnamese social-engineering tactic detector (relationship trust abuse, authority pressure, urgency patterns) | Catches local persuasion styles missed by generic models | Medium | Curated local examples, pattern library, prompt/fine-tune alignment |
| Evidence-grounded explanation cards (claim, evidence text spans, confidence, user-safe action) | Increases trust and reduces over-reliance on opaque scores | Medium | Explainability schema, extraction post-processing, confidence calibration |
| Risk decomposition score (spoofing signals, payment-pressure signals, credential-theft signals) | Helps users understand risk dimensions, not single-number black box | Medium | Feature engineering or classifier heads, calibrated aggregation |
| Privacy mode controls (strict local-only, no persistence, optional redaction before save) | Strong trust signal for sensitive financial data | Medium | Local storage policy, secure defaults, redaction pipeline |
| Vietnamese-first language robustness (slang, typo tolerance, code-switching EN/VI) | Better real-world capture on noisy text | High | Data augmentation, tokenizer strategy, adversarial validation |
| Explanation quality guardrails (ban fabricated claims outside input text) | Reduces hallucinated reasoning and legal trust risk | Medium | Grounding checks, explanation verifier rules, rejection fallback |

Category summary:
- Category complexity: Medium-High.
- Category key dependencies: localized behavioral threat intelligence, explanation-grounding validation, confidence calibration, robust EN/VI mixed-text preprocessing.

## Anti-Features

Features to explicitly avoid in v1 because they increase risk, cost, and delivery time without matching the current scope.

| Anti-Feature | Why Avoid | What to Do Instead | Complexity Risk if Included | Key Dependency Burden |
|---|---|---|---|---|
| OCR/image/screenshot analysis | Violates text-only boundary; adds major CV pipeline and quality variance | Keep strict paste-text workflow and improve text normalization | High | OCR engine, image preprocessing, OCR post-correction |
| Voice/call analysis | Expands into ASR + acoustic fraud signals and multilingual speech noise issues | Stay with raw text artifacts users can copy | High | Speech models, diarization, audio privacy pipeline |
| Generic all-domain cyber assistant | Dilutes financial scam focus and harms precision/recall tuning | Stay narrowly focused on financial phishing/social engineering | High | Broad taxonomy, broad datasets, larger model footprint |
| Cloud-only inference default | Conflicts with privacy/offline-first value proposition | Local-first, optional explicit opt-in cloud for future versions | Medium | Secure cloud infra, consent/legal controls, transport security audits |
| Fully autonomous user actions (auto-report, auto-block, auto-reply) | High false-positive harm and user trust risk in early versions | Provide recommendations and manual one-click guidance only | Medium | Integration APIs, irreversible-action safeguards, legal review |
| Real-time omnichannel scraping of personal accounts | Privacy and platform compliance risk; huge integration complexity | Manual user-provided text input only in v1 | High | OAuth integrations, compliance framework, monitoring stack |

Category summary:
- Category complexity: High and scope-destabilizing.
- Category key dependencies: multimodal pipelines, third-party platform integrations, legal/compliance overhead, larger infra footprint.

## Feature Dependencies Map (v1)

1. Input normalization and language handling -> threat classification and threat type labeling
2. Threat classification and threat type labeling -> explainable evidence output
3. Explainable evidence output -> actionable recommendations and user trust
4. Local inference optimization -> privacy/offline-first promise
5. Evaluation harness (recall-focused) -> safe release gate for all inference features

## v1 Recommendation (Grounded)

Prioritize in order:
1. Text ingestion + VN/mixed EN/VI normalization
2. Risk classification + threat type labeling (financial scam taxonomy only)
3. Explainable structured output (evidence spans + actionable recommendations)
4. Offline-first local inference packaging and performance baseline
5. Recall-focused evaluation gate and thresholding policy

Defer:
- Multimodal input (images/audio), autonomous actions, broad cybersecurity copilot behavior, deep third-party channel integrations.

## Scope Creep Warnings

1. Explainability creep: avoid moving from evidence-grounded explanations to open-ended advisory chatbot behavior.
2. Modality creep: adding OCR or audio before text-only quality targets are met will likely delay core reliability.
3. Product-surface creep: integrations (messaging APIs, bank APIs) can consume roadmap capacity before core model quality stabilizes.
4. Compliance creep: cloud defaults or account scraping can trigger legal/privacy obligations earlier than the team can safely support.
5. Taxonomy creep: adding too many scam classes too early reduces per-class quality and weakens recall.

Practical guardrail: require any new feature proposal to pass a v1 fit check against all four constraints (text-only, VN+EN/VI language reality, explainable output, privacy/offline-first). If one fails, queue for post-v1.
