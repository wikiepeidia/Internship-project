# Architecture Patterns

**Domain:** Localized explainable LLM for Vietnamese financial phishing/social engineering text detection  
**Project:** Localized Explainable AI (XAI) Engine for Vietnamese phishing triage  
**Researched:** 2026-03-18

## Recommended Architecture

Use an offline-first, modular pipeline with strict stage boundaries:

1. Ingestion and normalization
2. Threat analysis (rules + retrieval + LLM classifier)
3. Explanation synthesis (evidence-grounded)
4. User recommendation generation
5. Logging and evaluation feedback loop

Design principle: high recall on threat detection, deterministic evidence capture, and explainable outputs that are safe for non-technical users.

## Component Boundaries and Interfaces

| Component | Responsibility | Input Interface | Output Interface | Communicates With |
|-----------|----------------|-----------------|------------------|-------------------|
| Client Adapter | Accept raw text from UI, clipboard, or message paste | `POST /analyze` request payload | Canonical analysis request object | Preprocessor |
| Preprocessor | Language normalization, typo/slang cleanup, PII masking tags, URL/phone/entity extraction | Canonical analysis request | Enriched text document with extracted artifacts | Retrieval, Rule Engine, LLM Orchestrator |
| Rule Engine | Fast deterministic high-recall signals (domain spoofing, urgency, payment pressure, impersonation markers) | Enriched text document | Rule signal set with confidence priors | LLM Orchestrator, Evidence Store |
| Retrieval Layer | Fetch known scam patterns, local financial entity knowledge, phrase templates | Enriched text + extracted entities | Ranked context snippets | LLM Orchestrator |
| LLM Orchestrator | Run local model prompt chain for threat class, confidence, rationale candidates | Enriched text + rule signals + retrieved context | Structured threat assessment JSON | Explanation Engine |
| Explanation Engine | Convert model output + evidence into user-readable explanation with citation links to evidence spans | Structured threat assessment + evidence bundle | Explanation object | Recommendation Engine |
| Recommendation Engine | Generate action checklist (block/report/verify channel) by risk level | Explanation object + threat level | User action plan | Response Assembler |
| Response Assembler | Compose final API response in stable schema | Assessment + explanation + recommendations | API response payload | Client Adapter |
| Event Logger | Persist anonymized events, model metadata, latency, confidence, and user feedback | Events from all stages | Append-only local log records | Eval Harness, Monitoring |
| Eval Harness | Replay benchmark datasets, compute metrics, compare against release gates | Dataset + model bundle + pipeline version | Scorecards and pass/fail report | CI, Release Manager |
| Model Runtime | Offline inference engine (GGUF model + tokenizer + runtime config) | Prompt requests | Token stream/JSON output | LLM Orchestrator |
| Model/Rules Registry | Versioned model, prompts, rules, and retrieval snapshots | Version query | Immutable artifact references | Orchestrator, Eval Harness |

## Interface Contracts (Suggested)

### 1. Analyze Request

```json
{
  "request_id": "uuid",
  "channel": "sms|zalo|messenger|telegram|facebook|other",
  "text": "raw user-provided text",
  "locale_hint": "vi|en|mixed",
  "timestamp": "ISO-8601"
}
```

### 2. Threat Assessment

```json
{
  "request_id": "uuid",
  "threat_label": "safe|suspicious|phishing|social_engineering|job_scam",
  "risk_score": 0.0,
  "confidence": 0.0,
  "signals": [
    {"type": "spoofed_domain", "value": "example-paypa1.com", "source": "rule"},
    {"type": "urgency_language", "value": "khoa tai khoan ngay", "source": "llm"}
  ],
  "evidence_spans": [
    {"start": 14, "end": 41, "text": "...", "reason": "impersonation cue"}
  ],
  "model_version": "xai-vi-8b-lora-q4_0@2026-03-18",
  "policy_version": "ruleset-0.1.0"
}
```

### 3. Explanation and Recommendation

```json
{
  "summary": "High risk financial phishing likely.",
  "why": [
    "Message creates urgency to bypass verification.",
    "Sender requests credential or transfer action.",
    "Link/domain pattern is inconsistent with official institution naming."
  ],
  "recommendations": [
    "Do not click links or share OTP/password.",
    "Call official hotline from bank website, not message contact.",
    "Report message in the platform and block sender."
  ],
  "user_safe_mode": true
}
```

### 4. Logging Event

```json
{
  "event_id": "uuid",
  "request_id": "uuid",
  "stage": "preprocess|rules|retrieval|llm|explanation|recommendation",
  "latency_ms": 0,
  "artifact_versions": {
    "model": "...",
    "prompt": "...",
    "rules": "..."
  },
  "risk_score": 0.0,
  "decision": "...",
  "feedback": "optional_user_feedback"
}
```

## Data Flow (Ingestion -> Analysis -> Explanation -> Recommendation -> Logging/Eval)

1. Ingestion receives raw text and metadata from the client adapter.
2. Preprocessor normalizes Vietnamese/mixed text, extracts URLs, entities, and suspicious lexical cues.
3. Rule Engine computes deterministic risk signals to protect recall and catch obvious fraud patterns.
4. Retrieval Layer pulls local threat patterns and institution references to ground model reasoning.
5. LLM Orchestrator runs offline model inference and emits a structured threat assessment.
6. Explanation Engine transforms assessment into human-readable rationale tied to evidence spans.
7. Recommendation Engine maps risk level and scam type to concrete user actions.
8. Response Assembler returns stable schema to client.
9. Event Logger stores per-stage telemetry and prediction artifacts.
10. Eval Harness consumes logs plus benchmark sets to produce quality, recall, and latency reports.
11. Release Manager promotes model/rules only if evaluation gates are met.

## Offline Deployment Architecture

### Topology

- Desktop or local service host (consumer laptop, CPU/iGPU baseline)
- Embedded model runtime process (GGUF + quantized 8B LoRA merge)
- Local vector/rule store and retrieval index (on-device)
- Local encrypted event store (SQLite or append-only JSONL + encryption)
- Optional air-gapped update package import for model/rule updates

### Runtime Packaging

- Single installer bundle contains:
  - Inference runtime binaries
  - Quantized model artifacts
  - Prompt templates and rules
  - Local knowledge snapshot (financial entities, known patterns)
- No outbound network requirement for inference path.
- Update mechanism is explicit and versioned (manual package or signed internal updater).

### Security/Privacy Boundaries

- Raw user text never leaves local device in production mode.
- PII masking for logs by default; full raw text logging disabled unless debug mode is explicitly enabled.
- Tamper-evident version metadata for model and rules to preserve auditability.

## Evaluation Harness Architecture

### Core Harness Components

| Component | Responsibility |
|-----------|----------------|
| Dataset Manager | Curate train/validation/test sets (real + synthetic Vietnamese scams, mixed-language edge cases) |
| Scenario Generator | Build adversarial and mutation tests (typo, slang, obfuscation, unicode confusables) |
| Runner | Execute pipeline versions against fixed benchmark suites |
| Metrics Engine | Compute recall, precision, F1, calibration, explanation quality, latency |
| Threshold Gate | Enforce release criteria with recall-priority policy |
| Regression Tracker | Compare current run vs previous approved baseline |
| Error Analyzer | Cluster false negatives/positives and map to remediation actions |

### Evaluation Data Flow

1. Select immutable benchmark suite by version.
2. Run full pipeline end-to-end (not model-only) to capture system behavior.
3. Store predictions, explanations, and recommendations.
4. Score across detection, explanation fidelity, and user-action quality.
5. Produce fail report highlighting high-severity false negatives.
6. Feed errors into data improvement loop (rules update, retrieval update, fine-tune data updates).

### Minimum Release Gates (suggested)

- Recall on phishing/social-engineering classes: prioritize as primary gate.
- Macro F1 for overall classification stability.
- Explanation quality checks:
  - Evidence-grounded reasons present
  - No hallucinated institution/action claims
- Latency budget on consumer hardware.

## Patterns to Follow

### Pattern 1: Hybrid Detection (Rules + Retrieval + LLM)

**What:** Combine deterministic rules with grounded LLM reasoning.  
**When:** Safety-critical scam detection where recall is critical.  
**Why:** Rules catch known high-risk patterns quickly; LLM handles nuanced language and social context.

### Pattern 2: Structured Output First

**What:** Force model outputs into fixed JSON schema before user rendering.  
**When:** Need stable downstream explanation/recommendation logic and evaluability.  
**Why:** Prevent brittle parsing and enable robust regression testing.

### Pattern 3: Evidence-Bound Explanations

**What:** Every explanation claim should map to explicit text spans/rule hits.  
**When:** XAI requirements and trust-sensitive product context.  
**Why:** Improves user trust and reduces unsafe overclaiming.

## Anti-Patterns to Avoid

### Anti-Pattern 1: LLM-Only Classification Without Rules

- What goes wrong: misses simple but dangerous patterns under prompt variance.
- Consequence: preventable false negatives in phishing detection.
- Instead: always include deterministic high-recall guards.

### Anti-Pattern 2: Binary Output Without Action Layer

- What goes wrong: user knows something is risky but has no safe next steps.
- Consequence: reduced practical safety impact.
- Instead: attach scenario-specific recommendations.

### Anti-Pattern 3: Evaluating Model in Isolation

- What goes wrong: hidden failures in retrieval, rules, or rendering are missed.
- Consequence: production regressions despite good offline model scores.
- Instead: evaluate full pipeline end-to-end.

## Build-Order Implications for Phase Planning

Suggested build order for a greenfield milestone:

1. Foundation and contracts first
- Define canonical schemas (`AnalyzeRequest`, `ThreatAssessment`, `Explanation`, `Recommendation`, `EventLog`).
- Establish artifact versioning (model/prompt/rules/retrieval snapshot IDs).

2. Ingestion + preprocessing + logging skeleton
- Build deterministic text normalization and extraction pipeline.
- Wire end-to-end request tracing and event logging before advanced model work.

3. Rule Engine v1 + baseline retrieval
- Implement high-recall deterministic signals for known Vietnamese financial scam patterns.
- Add minimal local knowledge base and retrieval API.

4. Offline model runtime integration
- Integrate quantized local model serving with structured output constraints.
- Produce initial threat labels and confidence.

5. Explanation and recommendation layers
- Add evidence-to-rationale mapping and user action templates by scam type.
- Harden for non-technical clarity and safe guidance wording.

6. Evaluation harness and release gates
- Build benchmark runner, metrics, and regression dashboard/reporting.
- Enforce recall-priority gate and latency gate.

7. Data flywheel and hardening
- Use error clusters to update data, rules, prompts, and retrieval.
- Add adversarial robustness tests (obfuscation, mixed-language manipulation).

### Why this order

- Early schema and logging avoid costly rewrites.
- Rule-first detection provides immediate safety baseline before model maturity.
- Evaluation harness before optimization prevents blind tuning.
- Explanation/recommendation after stable detection avoids amplifying unstable predictions.

## Architecture Risks to Track During Planning

- Retrieval contamination from low-quality synthetic patterns can degrade explanations.
- Over-aggressive normalization can erase signal (slang/spoof tokens).
- Quantization settings may impact calibration and confidence reliability.
- Recommendation policy drift can produce unsafe or outdated advice.

## Planning Notes for Next Milestone Draft

- Treat evaluation harness as a first-class subsystem, not a post-hoc script.
- Allocate explicit phase capacity for Vietnamese linguistic edge cases.
- Include offline packaging and update strategy as part of core architecture, not deployment afterthought.
