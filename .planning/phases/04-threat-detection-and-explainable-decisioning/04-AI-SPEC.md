# AI-SPEC — Phase 04: Threat Detection and Explainable Decisioning

> AI design contract generated during `/gsd-ai-integration-phase`. Consumed by `gsd-planner` and `gsd-eval-auditor`.
> Locks framework selection, implementation guidance, and evaluation strategy before planning begins.

<!-- markdownlint-disable MD022 MD031 MD032 MD060 -->

---

## 1. System Classification

**System Type:** Hybrid

**Description:**
This phase extends the repo's existing local runtime into a single-message Vietnamese financial-phishing detector that returns one risk tier, one or more in-scope threat labels, evidence-linked reasons, and safe next-step recommendations. Good behavior means the system stays text-only, offline/local-first, and contract-stable across the `gguf-laptop` and `accelerated-local` profiles while reducing dangerous misses on harmful scams.

**Critical Failure Modes:**
1. A high-harm phishing or social-engineering message is classified as `benign`.
2. The output uses labels outside the approved Phase 4 scope or misses the correct in-scope threat type.
3. The explanation cites spans or evidence that do not exist in the pasted message.
4. The recommendation tells the user to click, reply, share OTP or identity data, or transfer money through the suspicious channel.
5. `gguf-laptop` and `accelerated-local` return incompatible field sets or semantics that break rendering, tests, or operator expectations.

---

## 1b. Domain Context

**Industry Vertical:** Vietnam-facing consumer financial fraud prevention, centered on retail banking phishing and messaging-based social-engineering scams.

**User Population:** General Vietnamese consumers, including non-technical users, who paste a single suspicious SMS, Zalo, Messenger, Facebook, or similar text message into a local/offline checker to decide whether it is safe.

**Stakes Level:** High

**Output Consequence:** The result often drives an immediate real-world choice: whether to click a link, enter banking credentials, share OTP, CCCD, or CVV data, install an app, reply to a sender, or transfer money. A false negative can lead to direct account takeover or financial loss; a false positive mainly creates alert fatigue and unnecessary verification work.

### What Domain Experts Evaluate Against

- **Harm-calibrated risk tiering**
  Good: `high-risk` is used for credential-harvest, fake-bank login, OTP/CVV/password requests, urgent transfer requests, or task scams that require deposit/top-up to unlock earnings; `suspicious` is used for partial or incomplete scam signals; `benign` is reserved for routine notifications with no unsafe ask.
  Bad: obvious credential theft is downgraded to `suspicious`, or routine bank notices are over-escalated to `high-risk`.
  Stakes: Critical.

- **Evidence-bound explanation quality**
  Good: the explanation points to exact cues in the message such as a look-alike domain, shortened URL, `tai khoan bi khoa` pressure, OTP request, personal phone number posing as support, `so moi` or `tai khoan moi` trust-abuse language, or `nap tien lam nhiem vu` wording.
  Bad: generic warnings with no concrete cue or explanations that invent evidence not present in the pasted text.
  Stakes: Critical.

- **Vietnamese channel and language realism**
  Good: the system handles no-diacritic text, teencode, code-switching, Zalo-style chat phrasing, kinship terms, informal pronouns, and local bank-brand references without losing the fraud signal.
  Bad: performance collapses on colloquial or mixed-language messages that look realistic to local users.
  Stakes: High.

- **Safe and specific user guidance**
  Good: recommendations tell the user exactly what to do next without escalating risk, such as not clicking, not sharing OTP/CCCD/CVV, verifying through the official app or published hotline, or calling the known contact directly on a trusted number.
  Bad: vague advice, unsafe advice, or instructions that rely on the suspicious message itself as the verification channel.
  Stakes: High.

- **Benign-notification discrimination**
  Good: legitimate transaction alerts, OTP notices that warn users not to share codes, and official-app references are not over-escalated just because they mention urgency, money, or account activity.
  Bad: all banking language is treated as phishing, making the product noisy and easy to ignore.
  Stakes: High.

### Known Failure Modes in This Domain

- Fake sites hide behind bank-like tokens, nested subdomains, shortened links, or look-alike `.net` / `.xyz` domains that resemble legitimate banking or payment brands.
- Zalo, Messenger, and Facebook takeover scams often use informal Vietnamese, no diacritics, family or friend language, or `so moi` excuses that feel socially plausible but are still high-risk.
- Legitimate OTP, low-balance, and transaction-confirmation messages can be over-flagged if the detector treats any banking urgency as malicious.
- `Viec nhe luong cao`, `lam nhiem vu`, commission, deposit, and top-up scams may begin with low-friction promises and only later demand payment; detectors that only look for explicit theft language under-escalate them.
- Attackers often mix one real-looking safety phrase or brand detail into a malicious message, which can trick weak explainers into under-rating a clearly malicious link or credential request.

### Regulatory / Compliance Context

- Decree 13/2023/ND-CP on personal data protection is the clearest direct constraint: message text may contain personal data such as names, phone numbers, account numbers, CCCD details, and transaction data, so evaluation and telemetry design must minimize retention and avoid unnecessary cloud export.
- Vietnam's broader cybersecurity obligations reinforce secure handling of message content, but no Vietnam-specific rule was identified that prescribes this system's exact phishing labels, risk thresholds, or explanation rubric. For Phase 4 and Phase 5, the main compliance implication is privacy-preserving processing plus careful, non-misleading safety wording.

### Domain Expert Roles for Evaluation

| Role | Responsibility |
|------|---------------|
| Retail banking fraud analyst | Calibrate `benign` vs `suspicious` vs `high-risk` boundaries for bank-impersonation and credential-harvest cases. |
| Vietnam trust-and-safety or scam-investigation specialist | Review account-takeover and social-engineering cases from Zalo, Messenger, Facebook, and SMS. |
| Fraud operations reviewer for task scams | Build and label `viec nhe luong cao`, `lam nhiem vu`, commission, deposit, and top-up scam examples. |
| Vietnamese language reviewer with fraud-domain familiarity | Check that explanations quote meaningful cues from real Vietnamese phrasing, slang, and code-switching. |
| Consumer banking support or digital safety educator | Judge whether recommendations are understandable, safe, and actionable for ordinary users. |
| Privacy/compliance reviewer familiar with Vietnam PDPD | Review logging, sampling, and evaluation storage for unnecessary exposure of personal or financial message content. |

---

## 2. Framework Decision

**Selected Framework:** Native repo-local runtime pattern (no new orchestration framework)

**Version:** Python 3.13 with the existing repo runtime stack declared in `pyproject.toml`, including `pydantic>=2.12`, optional `llama-cpp-python>=0.3` for GGUF runtime, and the current local training/runtime dependencies already used by this codebase.

**Rationale:**
This phase is not a RAG system, multi-agent workflow, chatbot, or long-lived tool-calling agent. The repo already has the right architectural seam: typed Pydantic contracts in `src/runtime/contracts.py`, normalization and fail-closed routing in `src/runtime/service.py`, and shared structured-prompt helpers in `src/runtime/analyzers/local_model.py`. Phase 4 is primarily a contract-evolution and structured-local-inference problem. Introducing LangChain, LangGraph, LlamaIndex, or Haystack would add abstraction and dependency surface without solving a real gap in the current offline/local-first design.

**Alternatives Considered:**

| Framework | Ruled Out Because |
|-----------|------------------|
| Haystack | Closest framework fit on paper because it favors explicit NLP pipelines, but the repo already has an explicit native pipeline with typed contracts and local backend routing. |
| LangChain | Structured-output helpers are not enough to justify a new dependency for a narrow, linear, single-message local inference path. |
| LangGraph | Built for stateful branching workflows and persistent agent graphs; Phase 4 is not a graph workflow or agent loop. |
| LlamaIndex | Optimized for retrieval and document-centric systems, which this phase explicitly is not. |

**Vendor Lock-In Accepted:** Partial — lock-in to the repo's local artifact and backend pattern is acceptable; cloud SDK or orchestration-framework lock-in is not.

---

## 3. Framework Quick Reference

Phase 4 should document the repo's existing native local runtime pattern as the framework. The framework is a repo-local Python runtime built from typed Pydantic contracts, normalize-first request handling, explicit backend/profile routing, and thin local inference adapters for GGUF and accelerated local models.

### Installation
```bash
python -m pip install -e .[dev]
python -m pip install -e .[dev,runtime]
python -m pip install -e .[dev,train]
python -m src.runtime.cli doctor
```

### Core Imports
```python
from src.runtime.service import build_default_runtime_service
from src.runtime.contracts import AnalysisRequest, AnalysisResult, SuspiciousCue
from src.runtime.analyzers.local_model import (
    build_structured_analysis_prompt,
    extract_structured_payload,
)
```

### Entry Point Pattern
```python
import json

from src.runtime.service import build_default_runtime_service


def main() -> None:
    service = build_default_runtime_service()
    result = service.analyze_text(
        "VPBank: tai khoan cua quy khach se bi khoa neu khong xac minh OTP tai vpbank-safe.example",
        channel="sms",
    )
    print(json.dumps(result.model_dump(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
```

### Key Abstractions

| Concept | What It Is | When You Use It |
|---------|-----------|-----------------|
| `AnalysisRequest` | One-message typed input with normalized text and optional channel | Keep as the public request boundary; do not add conversation state in Phase 4 |
| `AnalysisResult` | Public compatibility contract for CLI, rendering, and tests | Extend carefully or map from a richer internal decision model |
| `RuntimeService` | Normalization, text-only boundary checks, fail-closed handling, backend routing | Keep orchestration here; do not bury policy in backend-specific code |
| `GGUFAnalyzer` | Consumer-laptop baseline inference path via GGUF | Use as the Phase 4 baseline for local privacy-preserving deployment |
| `AcceleratedAnalyzer` | Stronger local CUDA path via `transformers` + `peft` | Use for stronger local hardware and richer explanations when needed |
| `local_model.py` | Shared prompt building, JSON extraction, and result shaping | Make this the single home for schema, parsing, validation, and retry logic |

### Common Pitfalls
1. `channel` exists in the request contract but can be lost if the prompt builder ignores it when it is useful for evidence or label judgment.
2. Reusing one generic explanation across every suspicious span does not satisfy Phase 4's evidence-linked explainability requirement.
3. Expanding the JSON schema too aggressively can exceed the `gguf-laptop` context budget and increase schema-echo or truncation failures.
4. Accepting the first dict-shaped object in the raw output is useful for messy local generations, but it must be followed by strict Pydantic validation or it may accept echoed example JSON.
5. Internal label literals should stay aligned with training and dataset lineage; if `zalo_social_engineering` remains the internal enum, user-facing renderers can map it to `account takeover/social engineering`.

### Recommended Project Structure
```text
src/runtime/
  contracts.py
  service.py
  cli.py
  render.py
  analyzers/
    base.py
    local_model.py
    gguf.py
    accelerated.py
```

---

## 4. Implementation Guidance

**Model Configuration:**
- Baseline local profile: `qwen3-4b-instruct-2507` through the `gguf-laptop` path
- Stronger local profile: `qwen3.5-4b` through the `accelerated-local` path
- GGUF decoding stays deterministic: `temperature=0.0`, `max_tokens=256`, `n_ctx=1024`, `n_gpu_layers=0`
- Accelerated decoding stays deterministic: `do_sample=False`, `max_new_tokens=256`, local files only, optional 4-bit loading only when `bitsandbytes` is available
- If the richer Phase 4 contract does not fit inside `256` output tokens reliably, raise to `320` or `384` only after validating the laptop baseline remains acceptable

**Core Pattern:**
Keep `RuntimeService` responsible for normalization, privacy-safe boundary enforcement, fail-closed behavior, and explicit profile routing. Keep backend modules thin and limited to model loading plus raw text generation. Put the shared decision schema, structured prompt design, JSON extraction, repair retries, and compatibility mapping in `src/runtime/analyzers/local_model.py`. Rendering stays downstream of typed validation.

**Tool Use:**
This system is not a tool-calling agent. The only acceptable "tools" are in-process Python helpers such as normalization, regex feature extraction, model-registry lookup, and schema validation. Do not add web search, retrieval middleware, cloud inference, or cloud-default SDK dependencies as part of Phase 4.

**State Management:**
- Single-message request scope only
- No conversation memory
- No retrieval memory
- No raw-text persistence
- Model objects may stay cached in memory per analyzer instance
- If duplicate-analysis caching is added later, key it by a local hash of normalized text plus runtime profile plus contract version

**Context Window Strategy:**
Keep one-message inference self-contained and do not introduce RAG for Phase 4. Pass only the compact schema, one small example, the normalized message text, and the channel hint when it is not `unknown`. If the message is long, preserve high-signal cues first: URLs, domains, OTP requests, bank or payment-brand mentions, urgency language, credential requests, money-transfer requests, and task-scam deposit cues.

---

## 4b. AI Systems Best Practices

### Structured Outputs with Pydantic

The repo already depends on Pydantic v2, so Phase 4 should validate structured local output after JSON extraction instead of delegating schema guarantees to a cloud SDK wrapper. The right pattern is: raw generation from GGUF or `transformers`, `extract_structured_payload(...)`, `ThreatDecision.model_validate(payload)`, then a compatibility mapping back to the public `AnalysisResult`.

```python
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


RiskTier = Literal["benign", "suspicious", "high-risk"]
ThreatLabel = Literal["bank_impersonation", "zalo_social_engineering", "task_scam", "benign"]
CueType = Literal[
    "url",
    "otp_request",
    "spoofed_brand",
    "urgency",
    "credential_request",
    "payment_request",
    "contact_takeover",
    "job_offer",
    "generic",
]
Priority = Literal["low", "medium", "high"]


class EvidenceReason(BaseModel):
    model_config = ConfigDict(extra="forbid")

    span: str = Field(min_length=1, max_length=160)
    reason: str = Field(min_length=1, max_length=240)
    cue_type: CueType
    supports_labels: list[ThreatLabel] = Field(min_length=1, max_length=2)
    severity: Priority = "medium"

    @field_validator("span", "reason")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value must not be blank")
        return value


class Recommendation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=180)
    priority: Priority = "medium"
    offline_safe: bool = True

    @field_validator("text")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("text must not be blank")
        return value


class ThreatDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    risk_tier: RiskTier
    threat_labels: list[ThreatLabel] = Field(min_length=1, max_length=2)
    decision_summary: str = Field(min_length=12, max_length=280)
    evidence: list[EvidenceReason] = Field(default_factory=list, max_length=5)
    recommendations: list[Recommendation] = Field(min_length=1, max_length=3)
    provisional: bool = True

    @field_validator("decision_summary")
    @classmethod
    def reject_blank_summary(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("decision_summary must not be blank")
        return value

    @model_validator(mode="after")
    def validate_consistency(self) -> "ThreatDecision":
        if "benign" in self.threat_labels and len(self.threat_labels) > 1:
            raise ValueError("benign cannot be combined with threat labels")
        if self.risk_tier == "benign" and self.threat_labels != ["benign"]:
            raise ValueError("benign tier must map to benign only")
        if self.risk_tier != "benign" and "benign" in self.threat_labels:
            raise ValueError("non-benign tier cannot include benign")
        if self.risk_tier == "high-risk" and not self.evidence:
            raise ValueError("high-risk decisions require evidence")
        return self
```

Recommended local retry policy:
- Attempt 1: deterministic structured prompt with compact schema and one example
- Attempt 2: repair prompt using the prior raw output plus validation errors, still JSON-only
- Attempt 3: one final minimal repair prompt only if needed on stronger local hardware or offline eval runs

What to log: backend name, runtime profile, contract version, validation error class, output length, and retry count.

What not to log: raw message text, full prompts, or full unredacted model output.

### Async-First Design

The current runtime is synchronous, which is fine for CLI use. If a later API or batch runner becomes async, wrap blocking GGUF or `transformers.generate(...)` calls with `asyncio.to_thread()` or an executor. Do not run blocking local generation directly inside an async request handler.

The common mistake to avoid is mixing `asyncio.run()` into environments that already have an event loop. Keep the synchronous inference core pure and add async wrappers outside it only when needed.

For Phase 4's JSON contract, prefer full completion over streaming. Validate the entire object first, then render it.

### Prompt Engineering Discipline

Treat prompt construction as two logical layers even if the backend receives one concatenated string:
- a stable system-style instruction block defining role, allowed labels, safety limits, and JSON-only output
- a user-style payload block containing channel and normalized message text

Few-shot examples must stay minimal. On `gguf-laptop`, one short in-domain example is enough. Large example sets waste context budget and increase schema-echo failures. Always set explicit output limits (`max_tokens` or `max_new_tokens`) and keep generation deterministic.

### Context Window Management

This phase is not RAG. The context strategy is message-local and deterministic:
- use normalized message text only
- include the channel when available
- keep the schema compact
- keep one example only
- preserve exact suspicious spans from the message whenever possible

If the message is too long for the laptop baseline, preserve likely threat evidence before trimming: URLs and domains, OTP or verification-code requests, bank or payment-brand mentions, urgency language, requests for credentials or transfers, and task-scam deposit cues. Keep the structured contract identical across `gguf-laptop` and `accelerated-local`.

### Cost and Latency Budget

The runtime budget is local latency, memory, and user patience rather than API cost:
- one model generation on the happy path
- at most one repair retry on `gguf-laptop`
- up to two retries only on stronger local hardware or offline evaluation runs
- deterministic decoding everywhere to reduce repeat cost

Prefer deterministic local helpers first: regex extraction for URLs, OTP phrases, money-transfer requests, urgency markers, spoofed-brand cues, and label normalization. Reserve full local model generation for the final structured decision and explanation.

---

## 5. Evaluation Strategy

Phase 4 and Phase 5 should stay inside the repo's native local-runtime pattern: deterministic Python gates for contract and classification behavior, a small redacted reference pack for explanation and recommendation review, and explicit side-by-side evaluation of `gguf-laptop` versus `accelerated-local`.

### Dimensions

| Dimension | Rubric (Pass/Fail or 1-5) | Measurement Approach | Priority |
|-----------|---------------------------|----------------------|----------|
| Single-message task completion | Pass when every non-empty input returns exactly one risk tier and a schema-valid structured result; any `suspicious` or `high-risk` result includes at least one in-scope label, at least one grounded cue, and at least one safe recommendation. Fail on missing or conflicting fields. | Code | Critical |
| Recall-first harmful risk-tier behavior | Pass when harmful-not-benign recall is at least 0.95 on both local profiles and explicit OTP/CVV/CCCD, password-reset, suspicious-domain, or deposit-request scams never land in `benign`. Fail on any harmful-to-benign miss in the guarded subset. | Code | Critical |
| In-scope label precision and benign-notification discrimination | Pass when macro F1 across bank impersonation, account takeover/social engineering, and task scam is at least 0.85 and at least 80% of curated legitimate banking notifications stay `benign`. Fail on out-of-scope labels or excessive benign escalation. | Code | High |
| Evidence grounding quality | Pass when every risky output cites at least one exact cue present in the message and the explanation remains bound to message evidence; target calibrated grounding pass rate is at least 0.90 on the curated rubric pack. Fail on generic or invented evidence. | LLM Judge | Critical |
| Structured-output robustness under local generation noise | Pass when parse and validation success is at least 0.99 across 5 repeated runs per fixture per profile and required enums stay in-range. Fail on frequent repair dependence or contract drift. | Code | Critical |
| Vietnamese and mixed-language robustness | Pass when harmful recall on mixed Vietnamese-English or slang-heavy fixtures stays within 5 percentage points of the pure-Vietnamese slice. Fail when code-switching materially worsens harmful detection. | Code | High |
| Recommendation safety | Pass when human review finds no advice telling the user to click, reply, share OTP/CCCD/CVV, transfer money, or trust contact details inside the suspicious message, and at least 95% of risky outputs include a concrete safe next step. Fail on any unsafe advice. | Human | Critical |
| Contract stability across local profiles | Pass when `gguf-laptop` and `accelerated-local` emit the same field set, same enum space, same label vocabulary, and the same bounded cue behavior. Fail on profile-specific contract divergence. | Code | High |
| Baseline versus accelerated quality gap | Pass when `gguf-laptop` stays within 10 percentage points of `accelerated-local` on harmful recall and grounding pass rate, with no critical safety dimension green only on the stronger profile. Fail when safe behavior exists only on stronger hardware. | Code | High |

### Eval Tooling

**Primary Tool:** Python-first local eval runner plus `pytest`, `pydantic`, `scikit-learn`, `polars`, and `promptfoo` only for rubric-based explanation/recommendation regression on a curated redacted fixture pack.

**Setup:**
```bash
python -m pip install -e .[dev]
npm install --global promptfoo
```

**CI/CD Integration:**
```bash
python -m pytest tests/runtime -q
python -m src.runtime.cli doctor
python -m src.runtime.eval --profiles gguf-laptop accelerated-local --heldout --repeats 5 --report-json phase5-eval.json
promptfoo eval --config promptfooconfig.yaml
```

### Reference Dataset

**Size:** Start with 20 redacted rubric fixtures plus the existing held-out split used for deterministic metrics.

**Composition:**
- 4 benign routine banking notifications
- 6 bank-impersonation messages
- 5 account-takeover or social-engineering messages
- 5 light-work-high-pay task-scam messages
- at least 7 mixed-language or code-switched cases
- at least 4 fake-domain camouflage cases
- at least 4 spoofed-trust or compromised-contact cases
- at least 4 upfront-payment task-scam cases

**Labeling:**
Use retained-dataset gold labels where available for risk tier and threat type. For explanation and recommendation review, use one Vietnamese-speaking reviewer plus second-review escalation for disagreements and any possible unsafe-advice case.

---

## 6. Guardrails

### Online (Real-Time)

| Guardrail | Trigger | Intervention |
|-----------|---------|--------------|
| Schema and enum validator | Model output cannot be parsed, required fields are missing, risk tier is outside `benign` / `suspicious` / `high-risk`, label is outside the approved set, or cue fields are blank. | Retry once with deterministic settings. If validation still fails, return a safe fallback result marked provisional, at least `suspicious`, with advice not to click, reply, or transfer until verified through an official channel. |
| High-harm under-escalation floor | Output is `benign` while the input contains explicit credential/payment takeover cues such as OTP, CVV, CCCD, password-reset bait, suspicious domains, or task-scam deposit language. | Raise the minimum tier to `suspicious`; raise to `high-risk` when credential or payment cues appear with a link, spoofed bank identity, or upfront-transfer request. |
| Evidence-grounding check | A risky output contains no exact cue span from the message, or quoted evidence is not found in the normalized input. | Replace the free-form explanation with a short safe fallback explanation tied only to verified cues or the triggered safety rule. |
| Unsafe-recommendation blocker | Recommendation text tells the user to click the message link, reply to the sender, trust phone numbers in the message, share OTP/CCCD/CVV, install an app from the message, or transfer money to verify an account/task. | Strip the unsafe recommendation and replace it with allowlisted guidance such as using the official bank app/site, a known official hotline, or a trusted voice call to the real contact. |
| Privacy-boundary blocker | Any runtime path attempts outbound network access for message analysis or tries to persist raw message text. | Fail closed, emit a local-only remediation message, and record only a redacted guardrail counter. |

### Offline (Flywheel)

| Metric | Sampling Strategy | Action on Degradation |
|--------|------------------|----------------------|
| Cross-profile disagreement | Review all held-out or shadow cases where `gguf-laptop` and `accelerated-local` disagree on risk tier, label set, or grounding quality. | Add adjudicated cases to the curated pack and tighten prompts or post-processing where disagreement changes user safety. |
| Benign-notification false positives | Re-run the curated benign pack nightly and before release. | Expand the benign pack and require the next release to clear benign discrimination gates before promotion. |
| Mixed-language robustness drift | Sample code-switched and slang-heavy fixtures in nightly replay and any explicitly redacted operator examples. | Add the exact language pattern to the permanent regression slice and re-check both profiles. |
| Emerging scam-pattern drift | Review new fake-domain camouflage, spoofed-trust, and task-scam escalation patterns seen in testing or operator review. | Redact and add the new pattern to the fixture set, then rerun both profiles before release. |
| Guardrail-hit rate | Sample hashed schema failures, unsafe-recommendation blocks, and under-escalation overrides locally. | Reconstruct only from user-approved redacted copies or synthetic equivalents and convert them into regression cases. |
| Privacy audit | Review any logging path that captures raw text, full prompts, or exportable message bodies. | Treat as release-blocking, remove the capture path, and re-run privacy tests before acceptance. |

---

## 7. Production Monitoring

**Tracing Tool:** Local redacted JSONL or SQLite metrics store by default. Optional Arize Phoenix is allowed only in lab mode on synthetic or manually redacted fixtures; it is not the default production tracing path for raw user messages.

**Key Metrics to Track:**
- schema-valid rate per runtime profile
- safe-fallback rate
- high-harm benign-floor override rate
- unsafe-recommendation block rate
- cross-profile disagreement rate in shadow mode
- mixed-language quality gap
- benign escalation rate on the curated benign pack
- per-profile p95 latency drift
- raw-text retention or export event count

**Alert Thresholds:**
- schema-valid rate below `0.99` over the trailing 200 analyses for either profile, or below `1.00` on the curated release pack
- safe-fallback rate above `0.02` over the trailing 200 analyses
- high-harm benign-floor override rate above `0.01` live or increasing release-over-release
- any unsafe-recommendation block on the curated release pack, or above `0.001` live
- risk-tier disagreement above `0.10` or harmful/not-harmful disagreement above `0.05` in shadow mode
- mixed-language fallback or schema-failure rate more than `2x` the pure-Vietnamese baseline, or nightly harmful recall down by more than 5 points on that slice
- benign escalation above `0.20` on the curated benign pack in nightly replay
- any raw-text retention or export event greater than `0`
- p95 latency doubling relative to the last accepted release for the same hardware/profile class

**Smart Sampling Strategy:**
Capture redacted code metrics on 100% of analyses. Capture 100% of guardrail hits, but store only hashed identifiers and rule counters. Enable shadow comparison on up to 5% of analyses only when both local profiles are installed and shadow mode is explicitly enabled. Run nightly or pre-release replay on the held-out split plus the 20-message curated rubric pack for both profiles. Keep default cloud export at 0% for raw user messages; if any external reporting is needed, export only aggregate counts or fully redacted synthetic fixtures.

---

## Checklist

- [x] System type classified
- [x] Critical failure modes identified (>= 3)
- [x] Domain context researched (Section 1b: vertical, stakes, expert criteria, failure modes)
- [x] Regulatory/compliance context identified or explicitly noted as none
- [x] Domain expert roles defined for evaluation involvement
- [x] Framework selected with rationale documented
- [x] Alternatives considered and ruled out
- [x] Framework quick reference written (install, imports, pattern, pitfalls)
- [x] AI systems best practices written (Section 4b: Pydantic, async, prompt discipline, context)
- [x] Evaluation dimensions grounded in domain rubric ingredients
- [x] Each eval dimension has a concrete rubric (Good/Bad in domain language)
- [x] Eval tooling selected with a privacy-first default and lab-mode override note
- [x] Reference dataset spec written (size >= 10, composition + labeling defined)
- [x] CI/CD eval integration specified
- [x] Online guardrails defined
- [x] Production monitoring configured (tracing tool + sampling strategy)

<!-- markdownlint-enable MD022 MD031 MD032 MD060 -->