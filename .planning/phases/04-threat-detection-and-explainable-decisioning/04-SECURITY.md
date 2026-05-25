---
phase: 04
slug: threat-detection-and-explainable-decisioning
status: verified
threats_open: 0
asvs_level: 1
created: 2026-05-25
---

<!-- markdownlint-disable MD060 MD047 -->

# Phase 04 - Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| shared contract -> CLI and tests | Additive Phase 4 fields must preserve the existing operator surface while exposing risk tier, labels, cues, and recommendations through the same command path. | Structured analysis results and terminal-safe summary text |
| local-model interface -> GGUF and accelerated backends | Both local profiles must route raw model output through one shared decision layer instead of backend-specific semantics. | Untrusted model JSON, normalized text, validated decision fields |
| model output -> structured payload | Local generation stays untrusted until risk tier, labels, evidence, and recommendations pass schema and grounding validation. | Raw generated text, extracted JSON, exact evidence spans |
| richer output fields -> terminal rendering | User-facing wording must stay concise, grounded, and privacy-safe without leaking raw payloads or debug data. | Threat labels, grounded cues, safe next steps |
| default settings -> runtime service builder | The promoted default backend/profile must remain explicit, local-only, and fail-closed when resources are missing. | Backend selection, runtime profile, doctor readiness state |
| doctor-backed analyze path -> operator expectations | Readiness and remediation must be visible before analyze proceeds so missing local resources do not silently downgrade behavior. | Doctor checks, setup steps, fail-closed guidance |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-04-01-01 | Tampering | src/runtime/contracts.py | mitigate | `AnalysisResult` keeps `risk_tier`, `summary`, and `top_cues` while adding `threat_labels` and `recommendations`; `tests/runtime/test_contracts.py` locks the additive contract and cue cap. | closed |
| T-04-01-02 | Integrity | src/runtime/analyzers/local_model.py | mitigate | `ThreatDecision`, `SUPPORTED_THREAT_LABELS`, `_build_threat_decision()`, and `build_analysis_result()` enforce one shared label and decision surface; `tests/runtime/test_local_model.py` rejects unsupported labels and invalid tiers. | closed |
| T-04-01-03 | Information Disclosure | src/runtime/render.py | mitigate | `render_analysis_result()` only emits bounded summary, risk tier, mapped labels, grounded cues, and next steps; `tests/runtime/test_render.py` and `tests/runtime/test_cli.py` lock the terminal surface without raw JSON dumps. | closed |
| T-04-01-SC | Tampering | pytest runtime scaffolding | mitigate | Focused runtime regressions in `tests/runtime/test_contracts.py`, `tests/runtime/test_local_model.py`, `tests/runtime/test_render.py`, `tests/runtime/test_service.py`, and `tests/runtime/test_cli.py` keep Phase 4 changes narrow and deterministic. | closed |
| T-04-02-01 | Integrity | src/runtime/analyzers/local_model.py | mitigate | `_build_threat_decision()` validates risk tier, label vocabulary, evidence, and recommendations before mapping into `AnalysisResult`; `tests/runtime/test_local_model.py` covers the accepted and rejected payload shapes. | closed |
| T-04-02-02 | Tampering | src/runtime/analyzers/rules.py | mitigate | `build_default_rules()` is only used by helper-cue logic and `_apply_safety_floor()` in `src/runtime/analyzers/local_model.py`; it raises risky benign outputs without replacing model-backed semantics, and `tests/runtime/test_local_model.py` verifies the bounded floor behavior. | closed |
| T-04-02-03 | Information Disclosure | tests/runtime/test_privacy.py | mitigate | `tests/runtime/test_privacy.py` asserts that Phase 4 parse failures redact both user text and raw model output, while `src/runtime/service.py` converts backend explosions into generic local-runtime failures. | closed |
| T-04-02-SC | Tampering | shared decision parsing | mitigate | `extract_structured_payload()`, `_normalize_text_list()`, `normalize_threat_labels()`, `_coerce_payload_evidence()`, and the Pydantic validators keep parsing compact and deterministic with no unbounded retry loop; `tests/runtime/test_local_model.py` exercises the rejection path. | closed |
| T-04-03-01 | Integrity | src/runtime/analyzers/gguf.py | mitigate | `GGUFAnalyzer` keeps model loading local, builds one structured prompt, extracts one payload, and hands result shaping to `build_analysis_result()`; `tests/runtime/test_gguf_backend.py` verifies Phase 4 fields on the GGUF path. | closed |
| T-04-03-02 | Integrity | src/runtime/analyzers/accelerated.py | mitigate | `AcceleratedAnalyzer` mirrors the GGUF pattern and reuses the same shared prompt/parser/result helpers; `tests/runtime/test_accelerated_backend.py` verifies aligned Phase 4 fields on the accelerated path. | closed |
| T-04-03-03 | Information Disclosure | src/runtime/render.py | mitigate | Renderer output is limited to mapped user-facing labels, top cues, and next steps, with no internal payload or debug dump path; `tests/runtime/test_render.py` and `tests/runtime/test_cli.py` lock that output. | closed |
| T-04-03-SC | Tampering | cross-profile parity tests | mitigate | `tests/runtime/test_runtime_profiles.py` asserts that GGUF and accelerated outputs share the same Phase 4 field set and semantics while keeping distinct backend identities. | closed |
| T-04-04-01 | Denial of Service | src/config/settings.py | mitigate | `Settings()` now defaults to `runtime_backend="gguf"` and `runtime_profile="gguf-laptop"`, while `src/runtime/service.py` checks doctor readiness and fails closed; `tests/runtime/test_doctor.py`, `tests/runtime/test_runtime_profiles.py`, and `tests/runtime/test_cli.py` verify the promoted default and not-ready behavior. | closed |
| T-04-04-02 | Integrity | src/runtime/service.py | mitigate | `_build_backend_from_settings()` only accepts explicit backend/profile pairs, and `analyze_text()` raises `RuntimeUnavailableError` when doctor readiness fails instead of falling back to heuristic; `tests/runtime/test_runtime_profiles.py` covers explicit profile selection and unknown-profile rejection. | closed |
| T-04-04-03 | Repudiation | src/runtime/doctor.py | mitigate | `RuntimeDoctor.run()` records backend, profile, fail-closed, raw-text, and backend-ready checks with remediation commands; `tests/runtime/test_doctor.py` locks the reported guidance and promoted default wording. | closed |
| T-04-04-SC | Tampering | default-profile promotion | mitigate | Phase 4 kept default promotion isolated in dedicated settings, doctor, runtime-profile, and CLI regressions (`tests/runtime/test_contracts.py`, `tests/runtime/test_doctor.py`, `tests/runtime/test_runtime_profiles.py`, `tests/runtime/test_cli.py`). | closed |

*Status: open · closed*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

No accepted risks.

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-05-25 | 16 | 16 | 0 | GitHub Copilot |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-05-25

<!-- markdownlint-enable MD060 MD047 -->