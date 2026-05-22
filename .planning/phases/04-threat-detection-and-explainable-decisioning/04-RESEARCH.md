<!-- markdownlint-disable MD022 MD032 MD033 MD034 MD055 MD056 MD060 -->

# Phase 4: Threat Detection and Explainable Decisioning - Research

**Researched:** 2026-05-19  
**Domain:** Contract-stable local threat decisioning over the existing GGUF and accelerated runtime profiles  
**Confidence:** MEDIUM

<user_constraints>
## User Constraints (from CONTEXT.md)

Copied and condensed from [CITED: 04-CONTEXT.md](.planning/phases/04-threat-detection-and-explainable-decisioning/04-CONTEXT.md).

### Locked Decisions
- D-01: Phase 4 starts from the real Phase 3 deployment surfaces: gguf-laptop as the consumer baseline and accelerated-local as the stronger local path.
- D-02: Phase 4 must preserve explicit runtime-profile selection rather than collapsing back to a single hidden backend.
- D-03: The public runtime contract from Phase 2 and Phase 3 remains the compatibility boundary for Phase 4 outputs.
- D-04: Risk-tier output remains exactly three-way: benign, suspicious, and high-risk.
- D-05: In-scope threat labels remain limited to bank impersonation, account takeover or social engineering, and light-work-high-pay task scams.
- D-06: Explanations must cite concrete cues from the provided text and not fall back to generic scam boilerplate.
- D-07: Recommendations must stay user-safe and non-autonomous, such as warning against clicking links or urging trusted-channel verification.
- D-08: Phase 4 should use the retained validated dataset and the trained Phase 3 artifacts as the starting point instead of reopening candidate selection.
- D-09: The locked baseline remains qwen3-4b-instruct-2507; the locked runner-up remains qwen3.5-4b.
- D-10: Any prompt or post-processing changes must remain compatible with later Phase 5 evaluation gates.

### Planning Direction
- Start by tightening the model prompt and response schema around the four required outcomes: risk tier, threat labels, evidence cues, and recommendations.
- Treat evidence linkage as a first-class requirement, not a nice-to-have explanation garnish.
- Keep the baseline gguf-laptop path honest about its likely capability ceiling; if richer explanation quality requires the accelerated path, make that explicit in tests and docs rather than hiding it.
- Use the retained validated split and representative Vietnamese scam patterns to define targeted acceptance fixtures early, before broad prompt iteration.

### Deferred Ideas (OUT OF SCOPE)
- Do not reopen model-family selection or pilot scoring in Phase 4.
- Do not expand to OCR, screenshots, or voice channels.
- Do not move release-gate threshold setting into Phase 4; that belongs in Phase 5.
</user_constraints>

<phase_requirements>
## Phase Requirements

Derived from [CITED: REQUIREMENTS.md](.planning/REQUIREMENTS.md) and [CITED: ROADMAP.md](.planning/ROADMAP.md).

| ID | Description | Research Support |
|----|-------------|------------------|
| DET-01 | System can classify each input message into risk tiers: benign, suspicious, or high-risk. | Keep the three-way tier contract, add a stricter internal decision validator, and use deterministic under-escalation floors for obvious credential, payment, and takeover cues before mapping back into the public result. [CITED: src/runtime/contracts.py](src/runtime/contracts.py); [CITED: src/runtime/analyzers/local_model.py](src/runtime/analyzers/local_model.py); [CITED: 04-AI-SPEC.md](.planning/phases/04-threat-detection-and-explainable-decisioning/04-AI-SPEC.md) |
| DET-02 | System can assign in-scope threat labels: bank impersonation, account takeover or social engineering, and light-work-high-pay task scam. | Reuse the existing internal label vocabulary already present in the dataset and training prompts, then map the internal social-engineering label to user-facing wording at the renderer or presentation edge. [CITED: src/data_pipeline/schemas.py](src/data_pipeline/schemas.py); [CITED: src/model_adaptation/prompts.py](src/model_adaptation/prompts.py); [CITED: 04-AI-SPEC.md](.planning/phases/04-threat-detection-and-explainable-decisioning/04-AI-SPEC.md) |
| XAI-01 | User receives evidence-linked reasons tied to suspicious spans or cues from the input text. | Replace the current one-explanation-for-all-spans shaping with per-cue grounded evidence validation and exact-span membership checks against normalized text. [CITED: src/runtime/analyzers/local_model.py](src/runtime/analyzers/local_model.py); [CITED: src/runtime/service.py](src/runtime/service.py); [CITED: 04-AI-SPEC.md](.planning/phases/04-threat-detection-and-explainable-decisioning/04-AI-SPEC.md) |
| XAI-02 | User receives actionable, safety-focused recommendations. | Add allowlisted recommendation generation plus a denylist or sanitizer that blocks unsafe advice such as replying, clicking, sharing OTP, or transferring money through the suspicious channel. [CITED: 04-AI-SPEC.md](.planning/phases/04-threat-detection-and-explainable-decisioning/04-AI-SPEC.md); [CITED: tests/runtime/test_privacy.py](tests/runtime/test_privacy.py) |

</phase_requirements>

## Project Constraints

- v1 remains text-only and offline/local-first. Phase 4 improves decision quality on top of local inference instead of widening input scope or adding cloud behavior. [CITED: .planning/STATE.md](.planning/STATE.md); [CITED: 04-CONTEXT.md](.planning/phases/04-threat-detection-and-explainable-decisioning/04-CONTEXT.md); [CITED: 04-AI-SPEC.md](.planning/phases/04-threat-detection-and-explainable-decisioning/04-AI-SPEC.md)
- Build on the existing RuntimeService, AnalyzerBackend, analyze command, and doctor command instead of replacing them. [CITED: src/runtime/service.py](src/runtime/service.py); [CITED: src/runtime/analyzers/base.py](src/runtime/analyzers/base.py); [CITED: src/runtime/cli.py](src/runtime/cli.py); [CITED: tests/runtime/test_cli.py](tests/runtime/test_cli.py)
- Preserve privacy-safe handling of raw message text: no raw-text persistence, no network fallback, and no raw message text leaked into failure output. [CITED: src/runtime/service.py](src/runtime/service.py); [CITED: tests/runtime/test_privacy.py](tests/runtime/test_privacy.py)
- No new orchestration framework is needed or desired. The AI-SPEC already locked the native repo-local runtime pattern as the framework choice. [CITED: 04-AI-SPEC.md](.planning/phases/04-threat-detection-and-explainable-decisioning/04-AI-SPEC.md)
- Explicit runtime profile selection must remain intact across gguf-laptop and accelerated-local. Phase 4 should not hide profile differences behind a single opaque backend. [CITED: src/config/settings.py](src/config/settings.py); [CITED: src/runtime/service.py](src/runtime/service.py); [CITED: tests/runtime/test_runtime_profiles.py](tests/runtime/test_runtime_profiles.py)
- Nyquist validation is enabled, so the planner should treat executable runtime tests as first-class Phase 4 work before broad prompt tuning. [CITED: .planning/config.json](.planning/config.json)
- Repo copilot instructions add GSD workflow routing but no additional code-level runtime constraint for this phase. [CITED: .github/copilot-instructions.md](.github/copilot-instructions.md)

## Summary

Phase 4 is primarily a contract-evolution and shared-decision-layer phase, not a framework phase and not a hardware phase. The repo already has the right seam: a narrow public result contract in [src/runtime/contracts.py](src/runtime/contracts.py), normalize-first orchestration and fail-closed behavior in [src/runtime/service.py](src/runtime/service.py), thin profile-specific analyzers in [src/runtime/analyzers/gguf.py](src/runtime/analyzers/gguf.py) and [src/runtime/analyzers/accelerated.py](src/runtime/analyzers/accelerated.py), and a shared prompt and JSON extraction helper in [src/runtime/analyzers/local_model.py](src/runtime/analyzers/local_model.py). The main gap is that the current model-backed runtime only returns risk_tier, suspicious_spans, and one explanation, which is not enough to satisfy DET-02 or XAI-02 and is only partially sufficient for XAI-01. [CITED: src/runtime/contracts.py](src/runtime/contracts.py); [CITED: src/runtime/analyzers/local_model.py](src/runtime/analyzers/local_model.py)

The most defensible design is to introduce a richer internal decision object for Phase 4, validate it strictly, then map it additively into the existing public AnalysisResult contract instead of replacing the CLI or service surface. That lets the planner keep the existing analyze and doctor entrypoints, preserve profile-aware backend loading, and still deliver threat labels, evidence-bound cues, and safe recommendations. It also keeps Phase 5 evaluation tractable because both local profiles can be forced through one shared decision schema and one shared set of guardrails. [CITED: src/runtime/cli.py](src/runtime/cli.py); [CITED: src/runtime/analyzers/local_model.py](src/runtime/analyzers/local_model.py); [CITED: 04-AI-SPEC.md](.planning/phases/04-threat-detection-and-explainable-decisioning/04-AI-SPEC.md)

One important planning wrinkle is that the current runtime default is still heuristic, while the Phase 4 context explicitly says the phase starts from gguf-laptop and accelerated-local. That means the planner should treat “promote the default shipped backend from heuristic to gguf-laptop” as an explicit late-wave decision instead of letting it happen implicitly. [CITED: src/config/settings.py](src/config/settings.py); [CITED: 04-CONTEXT.md](.planning/phases/04-threat-detection-and-explainable-decisioning/04-CONTEXT.md); [ASSUMED]

**Primary recommendation:** Add a shared validated decision layer in [src/runtime/analyzers/local_model.py](src/runtime/analyzers/local_model.py) that produces an internal Phase 4 threat decision, then map it additively into AnalysisResult while keeping RuntimeService, AnalyzerBackend, analyze and doctor, and the two real local profiles intact. [CITED: src/runtime/contracts.py](src/runtime/contracts.py); [CITED: src/runtime/service.py](src/runtime/service.py); [CITED: src/runtime/analyzers/local_model.py](src/runtime/analyzers/local_model.py)

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|--------------|----------------|-----------|
| Single-message intake, normalization, text-only boundary, and fail-closed handling | RuntimeService | CLI | This logic is already centralized in [src/runtime/service.py](src/runtime/service.py) and should stay backend-agnostic. [CITED: src/runtime/service.py](src/runtime/service.py) |
| Risk-tier, threat-label, evidence, and recommendation semantics | Shared local model decision layer | Profile-specific analyzer | Both real profiles must emit the same semantics, so the owning logic should live above gguf.py and accelerated.py, not inside them independently. [CITED: src/runtime/analyzers/local_model.py](src/runtime/analyzers/local_model.py); [CITED: src/runtime/analyzers/gguf.py](src/runtime/analyzers/gguf.py); [CITED: src/runtime/analyzers/accelerated.py](src/runtime/analyzers/accelerated.py) |
| Raw generation and model loading | Profile-specific analyzer | Model registry | GGUF and accelerated backends already differ in model loading and should remain thin adapters around generation only. [CITED: src/runtime/analyzers/gguf.py](src/runtime/analyzers/gguf.py); [CITED: src/runtime/analyzers/accelerated.py](src/runtime/analyzers/accelerated.py) |
| Human-readable presentation | Renderer | CLI | Output formatting belongs in [src/runtime/render.py](src/runtime/render.py), not in backend code. [CITED: src/runtime/render.py](src/runtime/render.py); [CITED: src/runtime/cli.py](src/runtime/cli.py) |
| Runtime readiness and profile gating | Doctor | Analyzer doctor methods | The doctor path already validates backend readiness and profile selection and should remain the operator-facing readiness surface. [CITED: src/runtime/doctor.py](src/runtime/doctor.py); [CITED: tests/runtime/test_doctor.py](tests/runtime/test_doctor.py) |
| Safety floors for obvious harmful cues | Shared deterministic helper | Shared decision validator | The existing rules surface is a good seed for a profile-independent safety floor, but it should support the model-backed decision path rather than replace it. [CITED: src/runtime/analyzers/rules.py](src/runtime/analyzers/rules.py); [CITED: src/runtime/analyzers/heuristic.py](src/runtime/analyzers/heuristic.py); [CITED: 04-AI-SPEC.md](.planning/phases/04-threat-detection-and-explainable-decisioning/04-AI-SPEC.md) |

## Standard Stack

No new core dependency is required for the recommended Phase 4 path. The standard stack is the existing Phase 2 and Phase 3 runtime stack plus stricter decision-schema and guardrail code. [CITED: pyproject.toml](pyproject.toml); [CITED: 04-AI-SPEC.md](.planning/phases/04-threat-detection-and-explainable-decisioning/04-AI-SPEC.md)

### Core

| Component or Library | Repo Version Floor or Current Use | Phase 4 Role | Why Standard Here |
|----------------------|-----------------------------------|--------------|-------------------|
| Python | 3.13 | Runtime orchestration and typed decisioning | Already the repo baseline and the required runtime for the current service, CLI, and analyzers. [CITED: pyproject.toml](pyproject.toml); [CITED: src/runtime/service.py](src/runtime/service.py) |
| pydantic | >=2.12 | Strict decision-schema validation and public contract stability | The repo already uses Pydantic models for requests, results, and doctor output; Phase 4 should extend that pattern instead of delegating structure to raw generation alone. [CITED: pyproject.toml](pyproject.toml); [CITED: src/runtime/contracts.py](src/runtime/contracts.py) |
| pydantic-settings | >=2.0 | Backend and profile configuration | Existing settings already control backend, profile, cue caps, and privacy flags; Phase 4 should keep using that single configuration path. [CITED: pyproject.toml](pyproject.toml); [CITED: src/config/settings.py](src/config/settings.py) |
| llama-cpp-python | >=0.3 | GGUF baseline inference on gguf-laptop | This is already the Phase 3 local baseline path and should remain the consumer-hardware delivery surface. [CITED: pyproject.toml](pyproject.toml); [CITED: src/runtime/analyzers/gguf.py](src/runtime/analyzers/gguf.py) |
| torch plus transformers plus peft plus accelerate | torch >=2.4, transformers >=4.45, peft >=0.12, accelerate >=0.33 | Accelerated-local inference on the stronger profile | This is already the Phase 3 accelerated path; Phase 4 should reuse it rather than introduce a second accelerated stack. [CITED: pyproject.toml](pyproject.toml); [CITED: src/runtime/analyzers/accelerated.py](src/runtime/analyzers/accelerated.py) |
| normalize_text plus deterministic regex or cue helpers | Existing repo code | Evidence normalization and safety-floor feature extraction | RuntimeService already normalizes once, and the current rules catalog gives a seed set for exact-cue extraction and minimum-risk floors. [CITED: src/runtime/service.py](src/runtime/service.py); [CITED: src/runtime/analyzers/rules.py](src/runtime/analyzers/rules.py) |

### Supporting

| Component | Current Role | Phase 4 Use |
|-----------|--------------|-------------|
| [src/model_adaptation/prompts.py](src/model_adaptation/prompts.py) | Training prompt schema | Keep runtime label vocabulary aligned with the existing training data schema so Phase 5 evaluation does not need label remapping in the middle of the pipeline. [CITED: src/model_adaptation/prompts.py](src/model_adaptation/prompts.py) |
| [src/data_pipeline/schemas.py](src/data_pipeline/schemas.py) | Dataset label and risk-tier source of truth | Reuse the existing internal labels bank_impersonation, zalo_social_engineering, task_scam, benign and map user-facing wording at the edge. [CITED: src/data_pipeline/schemas.py](src/data_pipeline/schemas.py) |
| [tests/runtime](tests/runtime) | Current contract, privacy, doctor, and profile tests | Extend this suite first with DET and XAI behavior tests before broad prompt iteration. [CITED: tests/runtime/test_contracts.py](tests/runtime/test_contracts.py); [CITED: tests/runtime/test_privacy.py](tests/runtime/test_privacy.py); [CITED: tests/runtime/test_runtime_profiles.py](tests/runtime/test_runtime_profiles.py) |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Native repo-local runtime pattern | LangChain, LangGraph, Haystack, or LlamaIndex | The AI-SPEC already ruled these out because Phase 4 is a narrow, single-message, local structured-output problem and the repo already has the correct seam. [CITED: 04-AI-SPEC.md](.planning/phases/04-threat-detection-and-explainable-decisioning/04-AI-SPEC.md) |
| Additive public contract evolution | A new Phase-4-only public result object exposed directly from the CLI | That would break the existing RuntimeService, render, CLI, and profile-parity tests instead of extending them. [CITED: src/runtime/contracts.py](src/runtime/contracts.py); [CITED: src/runtime/render.py](src/runtime/render.py); [CITED: tests/runtime/test_runtime_profiles.py](tests/runtime/test_runtime_profiles.py) |
| Shared guardrails plus model output | Pure model-only free-form explanations and recommendations | Model-only free text is harder to keep safe, harder to keep profile-consistent, and harder to test against exact-span grounding requirements. [CITED: 04-AI-SPEC.md](.planning/phases/04-threat-detection-and-explainable-decisioning/04-AI-SPEC.md) |
| Internal label alignment with dataset schema | Fresh label literals created inside runtime backends | That would add unnecessary remapping risk between training data, runtime output, and later evaluation. [CITED: src/data_pipeline/schemas.py](src/data_pipeline/schemas.py); [CITED: src/model_adaptation/prompts.py](src/model_adaptation/prompts.py) |

## Architecture Patterns

### Pattern 1: Internal Threat Decision, Additive Public AnalysisResult

The current public AnalysisResult is too small for DET-02 and XAI-02 because it exposes risk_tier, summary, top_cues, backend_name, provisional, and normalized_text, but no threat labels or structured recommendations. The cleanest Phase 4 pattern is to introduce a richer internal decision object with risk tier, internal threat labels, evidence items, and safe recommendations, validate that object strictly, then map it additively into AnalysisResult so the public seam survives. The public summary field can remain, while top_cues stays the short human-readable evidence slice for the CLI. [CITED: src/runtime/contracts.py](src/runtime/contracts.py); [CITED: 04-AI-SPEC.md](.planning/phases/04-threat-detection-and-explainable-decisioning/04-AI-SPEC.md)

A practical implication is that the planner should preserve the current top_cues cap of three. Both the Pydantic contract and the doctor path assume that cap today, so richer evidence should live internally or in additive fields rather than by silently widening the existing cue list. [CITED: src/runtime/contracts.py](src/runtime/contracts.py); [CITED: src/runtime/doctor.py](src/runtime/doctor.py); [CITED: src/runtime/service.py](src/runtime/service.py)

### Pattern 2: Shared Decision Schema and Guardrails in local_model.py, Thin Backends

The current GGUF and accelerated analyzers already share prompt-building, JSON extraction, and result shaping through [src/runtime/analyzers/local_model.py](src/runtime/analyzers/local_model.py). That file is therefore the highest-leverage Phase 4 implementation surface. Expand it to own the richer schema, channel-aware prompt construction, strict validation, exact-span grounding checks, retry or repair logic, label normalization, and recommendation sanitization. Keep [src/runtime/analyzers/gguf.py](src/runtime/analyzers/gguf.py) and [src/runtime/analyzers/accelerated.py](src/runtime/analyzers/accelerated.py) limited to model loading and raw generation. [CITED: src/runtime/analyzers/local_model.py](src/runtime/analyzers/local_model.py); [CITED: src/runtime/analyzers/gguf.py](src/runtime/analyzers/gguf.py); [CITED: src/runtime/analyzers/accelerated.py](src/runtime/analyzers/accelerated.py)

This matters because the current backends load different artifacts and even different base candidates, so any duplicated decision logic will drift semantically across profiles. The shared layer is what keeps the schema and safety behavior aligned despite different model runtimes. [CITED: src/runtime/analyzers/gguf.py](src/runtime/analyzers/gguf.py); [CITED: src/runtime/analyzers/accelerated.py](src/runtime/analyzers/accelerated.py)

### Pattern 3: Channel-Aware Prompting with Exact-Span Evidence Validation

AnalysisRequest already carries channel, but the current model prompt builder only accepts text. That is a real gap because channel can change how social-engineering messages should be interpreted, especially for Zalo, Messenger, Telegram, and Facebook takeover cases. The prompt builder should therefore accept the request or a text-plus-channel input and include channel only when it is known, while keeping the request single-message and text-only. [CITED: src/runtime/contracts.py](src/runtime/contracts.py); [CITED: src/runtime/analyzers/local_model.py](src/runtime/analyzers/local_model.py); [CITED: 04-AI-SPEC.md](.planning/phases/04-threat-detection-and-explainable-decisioning/04-AI-SPEC.md)

The second half of the pattern is evidence validation. The current result shaper applies one generic explanation to every suspicious span and assigns one generic cue type, which does not satisfy the “evidence-linked reasons” requirement. Phase 4 should validate that every evidence span exists in the normalized input before it reaches render output and should keep per-cue reasoning separate from the overall summary. [CITED: src/runtime/analyzers/local_model.py](src/runtime/analyzers/local_model.py); [CITED: src/runtime/service.py](src/runtime/service.py)

### Pattern 4: Hybrid Model Decision Plus Deterministic Safety Floor

Phase 4 should not fall back to the heuristic analyzer as the main delivery engine, but the existing rules catalog is still useful. It already captures OTP, credential prompts, link prompts, urgency, bank impersonation, and task-scam language. That makes it a good seed for a deterministic under-escalation floor and a verified evidence extractor that can backstop the model on obvious high-harm cues. [CITED: src/runtime/analyzers/rules.py](src/runtime/analyzers/rules.py); [CITED: src/runtime/analyzers/heuristic.py](src/runtime/analyzers/heuristic.py); [CITED: 04-AI-SPEC.md](.planning/phases/04-threat-detection-and-explainable-decisioning/04-AI-SPEC.md)

The planner should therefore treat deterministic cue extraction as a shared helper, not as a separate backend. That aligns with the AI-SPEC guidance to prefer deterministic local helpers for URLs, OTP phrases, urgency, brand spoofing, and payment cues before or alongside full model judgment. [CITED: 04-AI-SPEC.md](.planning/phases/04-threat-detection-and-explainable-decisioning/04-AI-SPEC.md)

## Likely Plan and Wave Split

This phase should probably be split into multiple plans or waves rather than one large implementation block. The split is clear from the current codebase shape. [CITED: src/runtime/contracts.py](src/runtime/contracts.py); [CITED: src/runtime/analyzers/local_model.py](src/runtime/analyzers/local_model.py); [CITED: tests/runtime/test_runtime_profiles.py](tests/runtime/test_runtime_profiles.py)

1. Wave 0 or Plan A: contract and test scaffolding. Extend the runtime contract additively, define the internal decision schema, and add runtime fixtures for DET-01, DET-02, XAI-01, and XAI-02 before broad prompt iteration. This is necessary because Nyquist validation is enabled and the current suite does not yet cover labels, recommendation safety, or exact-span grounding. [CITED: .planning/config.json](.planning/config.json); [CITED: tests/runtime/test_contracts.py](tests/runtime/test_contracts.py); [CITED: tests/runtime/test_runtime_profiles.py](tests/runtime/test_runtime_profiles.py)
2. Wave 1 or Plan B: shared decision layer in [src/runtime/analyzers/local_model.py](src/runtime/analyzers/local_model.py). Implement channel-aware prompting, payload validation, repair or retry policy, exact-span membership checks, recommendation sanitization, and mapping into the public result. [CITED: src/runtime/analyzers/local_model.py](src/runtime/analyzers/local_model.py); [CITED: 04-AI-SPEC.md](.planning/phases/04-threat-detection-and-explainable-decisioning/04-AI-SPEC.md)
3. Wave 2 or Plan C: backend integration and presentation. Wire both real profiles through the shared decision layer, keep profile selection explicit, and update [src/runtime/render.py](src/runtime/render.py) so the CLI can show risk tier, labels, evidence, and safe next steps without changing the analyze and doctor surface. [CITED: src/runtime/analyzers/gguf.py](src/runtime/analyzers/gguf.py); [CITED: src/runtime/analyzers/accelerated.py](src/runtime/analyzers/accelerated.py); [CITED: src/runtime/render.py](src/runtime/render.py); [CITED: src/runtime/cli.py](src/runtime/cli.py)
4. Optional late wave: default profile promotion. If product intent is that plain vnphish analyze should now use the local model path by default, make the switch from heuristic to gguf-laptop explicit and test-backed at the end of the phase rather than mixing it into early contract work. [CITED: src/config/settings.py](src/config/settings.py); [ASSUMED]

## Integration With Existing Code

- [src/runtime/contracts.py](src/runtime/contracts.py): this is the public compatibility boundary. Extend AnalysisResult additively rather than replacing it. The likely Phase 4 additions are threat labels and safe recommendations, while summary and top_cues remain the human-readable surface. [CITED: src/runtime/contracts.py](src/runtime/contracts.py)
- [src/runtime/analyzers/local_model.py](src/runtime/analyzers/local_model.py): this is the main Phase 4 implementation surface. The current prompt schema only asks for risk_tier, suspicious_spans, and xai_explanation, and the current result builder collapses per-cue reasoning into one generic explanation. Both limitations should be addressed here first. [CITED: src/runtime/analyzers/local_model.py](src/runtime/analyzers/local_model.py)
- [src/runtime/analyzers/gguf.py](src/runtime/analyzers/gguf.py): keep this file focused on artifact resolution, local model loading, and raw completion. Do not duplicate label mapping, recommendation safety policy, or evidence validation here. [CITED: src/runtime/analyzers/gguf.py](src/runtime/analyzers/gguf.py)
- [src/runtime/analyzers/accelerated.py](src/runtime/analyzers/accelerated.py): same rule as GGUF. This profile loads a different runtime stack and a different selected artifact, so its semantics should come from the shared decision layer, not a second copy of post-processing logic. [CITED: src/runtime/analyzers/accelerated.py](src/runtime/analyzers/accelerated.py)
- [src/runtime/service.py](src/runtime/service.py): keep normalization, boundary checks, fail-closed behavior, and profile routing here. Only add backend-agnostic orchestration hooks if needed. This file should not become the place where label taxonomy or recommendation text is authored. [CITED: src/runtime/service.py](src/runtime/service.py)
- [src/runtime/render.py](src/runtime/render.py): the renderer currently prints only the summary and up to three cues. Phase 4 will need it to surface risk tier, user-facing label wording, grounded cues, and safe recommendations while staying short and terminal-friendly. [CITED: src/runtime/render.py](src/runtime/render.py)
- [src/runtime/cli.py](src/runtime/cli.py): keep the existing analyze and doctor commands. Phase 4 does not need a new orchestration-style command surface. [CITED: src/runtime/cli.py](src/runtime/cli.py); [CITED: tests/runtime/test_cli.py](tests/runtime/test_cli.py)
- [src/runtime/analyzers/rules.py](src/runtime/analyzers/rules.py) and [src/runtime/analyzers/heuristic.py](src/runtime/analyzers/heuristic.py): keep them available as deterministic signal helpers or a fallback test harness, but do not let them remain the main shipped decisioning path for Phase 4. [CITED: src/runtime/analyzers/rules.py](src/runtime/analyzers/rules.py); [CITED: src/runtime/analyzers/heuristic.py](src/runtime/analyzers/heuristic.py); [ASSUMED]
- [src/model_adaptation/prompts.py](src/model_adaptation/prompts.py) and [src/data_pipeline/schemas.py](src/data_pipeline/schemas.py): keep runtime label vocabulary aligned with these files so Phase 5 evaluation does not need a translation layer in the middle of the stack. [CITED: src/model_adaptation/prompts.py](src/model_adaptation/prompts.py); [CITED: src/data_pipeline/schemas.py](src/data_pipeline/schemas.py)

## Validation Architecture

Phase 4 should plan validation early, not after prompt iteration, because the current runtime suite covers baseline contracts and privacy but not Phase 4 semantics. [CITED: .planning/config.json](.planning/config.json); [CITED: tests/runtime/test_contracts.py](tests/runtime/test_contracts.py); [CITED: tests/runtime/test_privacy.py](tests/runtime/test_privacy.py)

| Property | Value |
|----------|-------|
| Test framework | pytest. [CITED: pyproject.toml](pyproject.toml) |
| Existing runtime test surface | [tests/runtime/test_contracts.py](tests/runtime/test_contracts.py), [tests/runtime/test_service.py](tests/runtime/test_service.py), [tests/runtime/test_privacy.py](tests/runtime/test_privacy.py), [tests/runtime/test_runtime_profiles.py](tests/runtime/test_runtime_profiles.py), [tests/runtime/test_gguf_backend.py](tests/runtime/test_gguf_backend.py), [tests/runtime/test_accelerated_backend.py](tests/runtime/test_accelerated_backend.py), [tests/runtime/test_cli.py](tests/runtime/test_cli.py), [tests/runtime/test_doctor.py](tests/runtime/test_doctor.py) |
| Quick validation command | python -m pytest tests/runtime -q. [CITED: src/runtime/doctor.py](src/runtime/doctor.py); [CITED: pyproject.toml](pyproject.toml) |
| Operator readiness check | python -m src.runtime.cli doctor. [CITED: src/runtime/cli.py](src/runtime/cli.py); [CITED: src/runtime/doctor.py](src/runtime/doctor.py) |

The current gaps the planner should account for are clear:

- There are no runtime tests yet for threat_labels, recommendation safety, or exact-span grounding against normalized input. [CITED: tests/runtime/test_contracts.py](tests/runtime/test_contracts.py); [CITED: tests/runtime/test_service.py](tests/runtime/test_service.py)
- Cross-profile testing currently verifies field-shape parity, but not semantic parity for labels, evidence behavior, or safe recommendations. [CITED: tests/runtime/test_runtime_profiles.py](tests/runtime/test_runtime_profiles.py)
- Privacy testing already exists and should remain a non-negotiable regression guard while Phase 4 enriches output fields. [CITED: tests/runtime/test_privacy.py](tests/runtime/test_privacy.py)

## Anti-Patterns

- Replacing the RuntimeService and AnalyzerBackend seam with a new orchestration framework or a second public runtime surface. [CITED: src/runtime/service.py](src/runtime/service.py); [CITED: src/runtime/analyzers/base.py](src/runtime/analyzers/base.py); [CITED: 04-AI-SPEC.md](.planning/phases/04-threat-detection-and-explainable-decisioning/04-AI-SPEC.md)
- Implementing decision semantics separately inside [src/runtime/analyzers/gguf.py](src/runtime/analyzers/gguf.py) and [src/runtime/analyzers/accelerated.py](src/runtime/analyzers/accelerated.py), which would make the two profiles drift. [CITED: src/runtime/analyzers/gguf.py](src/runtime/analyzers/gguf.py); [CITED: src/runtime/analyzers/accelerated.py](src/runtime/analyzers/accelerated.py)
- Letting the model invent evidence or recommendations without exact-span membership checks and recommendation safety filtering. [CITED: 04-AI-SPEC.md](.planning/phases/04-threat-detection-and-explainable-decisioning/04-AI-SPEC.md); [CITED: src/runtime/analyzers/local_model.py](src/runtime/analyzers/local_model.py)
- Renaming internal labels away from the dataset vocabulary inside backend code instead of mapping user-facing wording at the renderer or edge layer. [CITED: src/data_pipeline/schemas.py](src/data_pipeline/schemas.py); [CITED: src/model_adaptation/prompts.py](src/model_adaptation/prompts.py)
- Logging raw message text, full prompts, or unredacted raw model output while debugging Phase 4 behavior. [CITED: tests/runtime/test_privacy.py](tests/runtime/test_privacy.py); [CITED: 04-AI-SPEC.md](.planning/phases/04-threat-detection-and-explainable-decisioning/04-AI-SPEC.md)
- Treating the Phase 2 heuristic rules as the primary Phase 4 detector instead of a deterministic safety helper. [CITED: src/runtime/analyzers/heuristic.py](src/runtime/analyzers/heuristic.py); [CITED: src/runtime/analyzers/rules.py](src/runtime/analyzers/rules.py); [ASSUMED]

## Research Outcome

The planner should treat Phase 4 as a shared decisioning and contract-stability phase over real local backends. The highest-value first move is not prompt tinkering in isolation; it is a Wave 0 slice that defines the additive contract, exact acceptance fixtures, and privacy-safe tests for DET-01, DET-02, XAI-01, and XAI-02. After that, the most important implementation surface is [src/runtime/analyzers/local_model.py](src/runtime/analyzers/local_model.py), because it is the one place that can keep gguf-laptop and accelerated-local aligned without breaking the existing analyze and doctor workflow. [CITED: src/runtime/analyzers/local_model.py](src/runtime/analyzers/local_model.py); [CITED: tests/runtime/test_runtime_profiles.py](tests/runtime/test_runtime_profiles.py); [CITED: .planning/config.json](.planning/config.json)

Confidence is medium because the architecture seam is already clear, the label vocabulary is already present in the repo, and the local runtime profiles are real rather than hypothetical. The remaining uncertainty is not structural; it is quality calibration on the gguf-laptop baseline versus the accelerated-local profile, which is why the planner should split testing and shared decision logic before any default-profile promotion. [CITED: src/runtime/analyzers/gguf.py](src/runtime/analyzers/gguf.py); [CITED: src/runtime/analyzers/accelerated.py](src/runtime/analyzers/accelerated.py); [CITED: 04-CONTEXT.md](.planning/phases/04-threat-detection-and-explainable-decisioning/04-CONTEXT.md); [ASSUMED]

## RESEARCH COMPLETE

<!-- markdownlint-enable MD022 MD032 MD033 MD034 MD055 MD056 MD060 -->