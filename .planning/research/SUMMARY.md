# Project Research Summary

**Project:** Localized Explainable AI (XAI) Engine for Vietnamese Financial Phishing and Threat Detection
**Domain:** Offline-first Vietnamese financial scam text detection with explainable recommendations
**Researched:** 2026-03-18
**Confidence:** HIGH

## Executive Summary

This is a safety-critical consumer product: an offline-first, text-only Vietnamese scam detection assistant that classifies financial phishing and social-engineing content and explains decisions in user-safe language. The strongest expert pattern is a hybrid pipeline, not model-only inference: deterministic rules for high-recall guardrails, retrieval for local financial context, and a quantized local LLM for nuanced language interpretation.

The recommended implementation path is Python-first for data/training/evaluation, then GGUF plus llama.cpp for local runtime on consumer laptops. Product reliability depends on strict structured outputs (JSON contract), evidence-bound explanations, and release gates that prioritize high-harm recall over aggregate headline metrics. For v1, scope discipline is a success factor: keep input text-only and defer multimodal/OCR, autonomous actions, and cloud-default workflows.

Primary risks are false negatives hidden by broad metrics, explanation hallucination, dataset leakage/synthetic mode collapse, quantization regressions, and trust erosion from alert fatigue. Mitigation should be built into roadmap phases (taxonomy policy, split governance, adversarial evaluation, faithfulness checks, quantization regression gates, and post-deploy drift loop), not deferred to post-launch.

## Key Findings

### Recommended Stack

Use Python 3.11-3.12 with PyTorch 2.10.x and Transformers plus PEFT plus TRL for LoRA/QLoRA fine-tuning, and DVC-backed reproducible data artifacts. Serve local inference via GGUF on llama.cpp (optional llama-cpp-python embedding), defaulting to Q4_K_M for CPU baseline and Q5_K_M for quality-first devices.

**Core technologies:**

- Python + PyTorch + Transformers: training and evaluation foundation with strongest ecosystem support.
- PEFT + TRL + bitsandbytes: memory-efficient LoRA/QLoRA adaptation for 7B-8B multilingual models.
- llama.cpp + GGUF: practical offline runtime for consumer laptop deployment.
- FastAPI local service wrapper: stable integration boundary for desktop UX and testing.
- Pydantic schema + constrained JSON output: deterministic explainability contract and regression safety.

### Expected Features

**Must have (table stakes):**

- Text ingestion from pasted messages (Vietnamese and mixed EN/VI).
- Risk classification (benign/suspicious/high risk) with threat type labels.
- Explainable outputs with evidence spans and user-action recommendations.
- Offline-first inference mode and stable JSON response contract.
- Recall-focused release gating with per-class safety checks.

**Should have (competitive):**

- Vietnamese social-engineering tactic detection and code-switch robustness.
- Evidence-grounded explanation cards with confidence and explicit safe actions.
- Risk decomposition dimensions (spoofing/payment-pressure/credential-theft).
- Privacy mode controls (local-only/no persistence/redaction paths).

**Defer (v2+):**

- OCR/screenshot analysis, voice/call analysis.
- Cloud-default inference, omnichannel account scraping integrations.
- Fully autonomous actions (auto-report/auto-block/auto-reply).
- Generic broad cybersecurity assistant behavior.

### Architecture Approach

Adopt a modular offline-first pipeline: Client Adapter -> Preprocessor -> Rule Engine + Retrieval -> LLM Orchestrator -> Explanation Engine -> Recommendation Engine -> Response Assembler, with Event Logger + Eval Harness as first-class subsystems. Enforce structured output contracts and evidence-linking across every explanation claim.

**Major components:**

1. Preprocessor + Rule Engine: high-recall deterministic signals and normalized feature extraction.
2. Retrieval + LLM Orchestrator: grounded contextual reasoning and structured threat assessment.
3. Explanation + Recommendation layers: user-safe rationale tied to explicit evidence spans.
4. Event Logger + Eval Harness: end-to-end regression control, release gates, and drift detection.

### Critical Pitfalls

1. **False-negative risk hidden by aggregate metrics**: enforce per-class high-harm recall gates and class-specific thresholds.
2. **Explanation hallucination/unsupported claims**: require claim-to-span evidence schema and fail closed when evidence is weak.
3. **Dataset leakage and synthetic template collapse**: deduplicate before splitting, split by campaign/time, enforce diversity metrics.
4. **Code-switching/obfuscation bypass**: build normalization and adversarial perturbation suites into training and evaluation.
5. **Quantization regression in local runtime**: maintain FP reference vs quantized golden comparison and fallback model tiers.

## Implications for Roadmap

Based on combined research, this phase order is recommended:

### Phase 1: Taxonomy, Policy, and Contracts

**Rationale:** Everything downstream depends on stable class ontology, risk policy, schema, and acceptance gates.
**Delivers:** Label taxonomy, explanation contract, recommendation policy, release criteria.
**Addresses:** Table-stakes classification and structured output requirements.
**Avoids:** False-negative policy drift, label inconsistency, unsafe explanation format drift.

### Phase 2: Data Foundation and Ingestion Pipeline

**Rationale:** Model quality is bounded by data hygiene and preprocessing robustness.
**Delivers:** Scraping + normalization + dedup + split governance + annotation playbook.
**Uses:** Scrapy/Playwright, Polars/pandas, Pydantic, DVC.
**Implements:** Client Adapter, Preprocessor, baseline Event Logger.

### Phase 3: Rule and Retrieval Safety Baseline

**Rationale:** High-recall deterministic coverage should exist before model sophistication.
**Delivers:** Rule Engine v1, local threat pattern retrieval, risk priors.
**Addresses:** Immediate table-stakes risk triage and explainability grounding.
**Avoids:** LLM-only blind spots and avoidable false negatives.

### Phase 4: Fine-Tuning, Calibration, and Runtime Integration

**Rationale:** After safe data/rules baseline, integrate domain-adapted local model and calibrate risk decisions.
**Delivers:** LoRA/QLoRA model, class thresholds, local llama.cpp GGUF runtime path.
**Uses:** Transformers/PEFT/TRL/bitsandbytes, llama.cpp.
**Implements:** LLM Orchestrator and model registry versioning.

### Phase 5: Explanation and Recommendation Hardening

**Rationale:** User trust and safety outcomes depend on explanation faithfulness and actionable guidance quality.
**Delivers:** Evidence-bound rationale generation, confidence-aware recommendation templates.
**Addresses:** Explainability table stakes and alert-fatigue mitigation.
**Avoids:** Hallucinated rationale and panic-biased recommendations.

### Phase 6: Evaluation, Quantization Regression, and Release Gates

**Rationale:** Safety-critical launch requires end-to-end gates on both quality and edge performance.
**Delivers:** Benchmark runner, adversarial suites, quantized-vs-reference deltas, go/no-go gates.
**Uses:** scikit-learn metrics, pytest golden outputs, custom faithfulness checks.
**Implements:** Eval Harness + release manager criteria.

### Phase 7: Post-Deploy Drift and Update Loop

**Rationale:** Scam language and attack patterns evolve continuously.
**Delivers:** Drift dashboard, incident review loop, lexicon refresh, model/rule update cycle.
**Addresses:** Ongoing recall protection and trust maintenance.
**Avoids:** Lexicon drift and silent field degradation.

### Phase Ordering Rationale

- Dependencies require policy/contracts before data, data before model, and stable detection before explanation polish.
- Safety-first sequencing (rules + retrieval before full LLM reliance) reduces early false-negative exposure.
- Evaluation and regression controls are explicit pre-release phases to prevent metric illusions and quantization regressions.

### Research Flags

Phases likely needing deeper research during planning:

- **Phase 4:** Base-model selection and LoRA configuration tradeoffs for Vietnamese + mixed-language robustness.
- **Phase 6:** Exact acceptance thresholds for recall, faithfulness, and latency by target hardware class.
- **Phase 7:** Drift signal thresholds and refresh cadence tied to real incident rates.

Phases with standard patterns (can likely skip dedicated research phase):

- **Phase 2:** Scraping and data-governance pipeline patterns are mature and well-documented.
- **Phase 3:** Rule-engine and retrieval baseline architecture follows established safety-critical NLP patterns.

## Concrete Guidance for Requirements and Roadmap Derivation

Use these requirement buckets directly:

- Functional requirements: ingestion, classification, threat typing, explanation schema, recommendations.
- Safety requirements: per-class high-harm recall gates, hallucination prevention, fallback behavior.
- Privacy requirements: local-only inference path, redacted logs by default, explicit consent for any raw-text retention.
- Performance requirements: CPU baseline latency and quantized-regression deltas vs reference model.
- Operability requirements: artifact versioning, reproducible data/model lineage, drift monitoring loop.

Roadmap derivation rules:

- Gate each phase with measurable exit criteria (schema conformance, per-class recall, faithfulness pass rate, latency budget).
- Tie every major pitfall to at least one prevention task in the owning phase.
- Keep v1 scope aligned to the four hard constraints: text-only, VN/mixed-language robustness, explainability, offline-first privacy.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Strong alignment with current official ecosystems and stable local-inference patterns. |
| Features | HIGH | Table-stakes and anti-features are clear and consistent across domain framing. |
| Architecture | HIGH | Pipeline boundaries and contracts are well-defined and implementation-ready. |
| Pitfalls | HIGH | Risks are domain-specific with concrete warning signals and mitigations. |

**Overall confidence:** HIGH

### Gaps to Address

- Final numeric thresholds for release gates require pilot calibration on real-world traffic slices.
- Exact 7B-8B base checkpoint choice should be validated against Vietnamese slang and code-switch stress tests.
- Recommendation wording may need legal/compliance review before broad public distribution.

## Sources

### Primary (HIGH confidence)

- Internal synthesis from: .planning/research/STACK.md, .planning/research/FEATURES.md, .planning/research/ARCHITECTURE.md, .planning/research/PITFALLS.md
- PyTorch local install/stable matrix: <https://pytorch.org/get-started/locally/>
- Hugging Face Transformers docs: <https://huggingface.co/docs/transformers/index>
- Hugging Face PEFT docs: <https://huggingface.co/docs/peft/index>
- Hugging Face TRL docs: <https://huggingface.co/docs/trl/index>
- llama.cpp repository/docs: <https://github.com/ggml-org/llama.cpp>
- scikit-learn docs: <https://scikit-learn.org/stable/>

### Secondary (MEDIUM confidence)

- ONNX Runtime docs (runtime alternative context): <https://onnxruntime.ai/docs/>
- LM Studio docs (local runtime ecosystem signal): <https://lmstudio.ai/docs>

---
*Research completed: 2026-03-18*
*Ready for roadmap: yes*
