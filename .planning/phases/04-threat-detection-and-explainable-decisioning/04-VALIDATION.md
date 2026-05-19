<!-- markdownlint-disable MD003 MD022 MD036 MD041 MD060 -->

---
phase: 04
slug: threat-detection-and-explainable-decisioning
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-05-19
---

# Phase 04 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `python -m pytest tests/runtime/test_contracts.py tests/runtime/test_service.py tests/runtime/test_runtime_profiles.py -q` |
| **Full suite command** | `python -m pytest tests/runtime -q` |
| **Estimated runtime** | ~25 seconds for contract-heavy checks; local model smokes may be manual |

---

## Sampling Rate

- **After every task commit:** Run the narrowest task-specific pytest command from the active plan.
- **After every plan wave:** Run `python -m pytest tests/runtime -q`
- **Before `/gsd-verify-work`:** Full Phase 4 runtime suite must be green.
- **Max feedback latency:** 25 seconds for automated checks; profile-quality smokes may be manual.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | DET-01 | Contract drift | Additive runtime contract preserves one risk tier while preparing internal decision-schema evolution without breaking the public result surface | unit + regression | `python -m pytest tests/runtime/test_contracts.py -q` | ✅ existing | ⬜ pending |
| 04-01-02 | 01 | 1 | DET-02 | Label-taxonomy drift | Runtime fixtures lock the in-scope label set and preserve profile-parity expectations across GGUF and accelerated paths | unit + regression | `python -m pytest tests/runtime/test_runtime_profiles.py tests/runtime/test_local_model.py -q` | ❌ W0 | ⬜ pending |
| 04-01-03 | 01 | 1 | XAI-01, XAI-02 | Output-surface drift | CLI and render coverage lock risk tier, evidence, and recommendation presentation without widening the public command surface | unit + integration | `python -m pytest tests/runtime/test_render.py tests/runtime/test_cli.py -q` | ❌ W0 | ⬜ pending |
| 04-02-01 | 02 | 2 | DET-01, DET-02 | Shared-decision drift | Shared local-model decision schema validates risk tier, internal labels, and additive mapping into AnalysisResult | unit | `python -m pytest tests/runtime/test_local_model.py -q` | ❌ W0 | ⬜ pending |
| 04-02-02 | 02 | 2 | XAI-01 | Evidence hallucination | Exact-span validation rejects evidence not found in normalized text and repair logic preserves deterministic behavior | unit + regression | `python -m pytest tests/runtime/test_local_model.py tests/runtime/test_service.py -q` | ❌ W0 | ⬜ pending |
| 04-02-03 | 02 | 2 | XAI-02 | Unsafe guidance | Recommendation sanitizer blocks click, reply, OTP, CCCD, CVV, install, and transfer guidance routed through the suspicious message | unit + privacy | `python -m pytest tests/runtime/test_local_model.py tests/runtime/test_privacy.py -q` | ❌ W0 | ⬜ pending |
| 04-03-01 | 03 | 3 | DET-01, DET-02, XAI-01 | Profile-parity drift | GGUF and accelerated backends emit the same field set, label vocabulary, and bounded evidence behavior after shared decision integration lands | unit + integration | `python -m pytest tests/runtime/test_gguf_backend.py tests/runtime/test_accelerated_backend.py tests/runtime/test_runtime_profiles.py -q` | ✅ existing | ⬜ pending |
| 04-03-02 | 03 | 3 | XAI-02 | Operator-surface drift | Analyze output remains terminal-friendly and safe while exposing risk tier, user-facing labels, grounded cues, and safe next steps | integration | `python -m pytest tests/runtime/test_cli.py tests/runtime/test_render.py -q` | ❌ W0 | ⬜ pending |
| 04-04-01 | 04 | 4 | DET-01, DET-02, XAI-01, XAI-02 | Default-profile regression | Any promotion from heuristic default to `gguf-laptop` remains explicit, doctor-backed, and CLI-safe | integration | `python -m pytest tests/runtime/test_runtime_profiles.py tests/runtime/test_doctor.py tests/runtime/test_cli.py -q` | ✅ existing | ⬜ pending |
| 04-04-02 | 04 | 4 | DET-01, DET-02, XAI-01, XAI-02 | Fail-closed default routing | Plain `analyze` uses the promoted GGUF default when ready, preserves explicit overrides, and still stops at doctor guidance instead of silently falling back when the promoted default is unavailable | integration | `python -m pytest tests/runtime/test_cli.py tests/runtime/test_runtime_profiles.py -q` | ✅ existing | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/runtime/test_local_model.py` - shared decision-schema, evidence grounding, repair, and recommendation-sanitizer coverage
- [ ] `tests/runtime/test_render.py` - user-facing render coverage for risk tier, labels, cues, and recommendations
- [ ] `tests/runtime/test_runtime_profiles.py` - extend with profile-semantic parity for labels, grounding, and recommendations
- [ ] `tests/runtime/test_contracts.py` - extend with additive Phase 4 contract assertions
- [ ] `tests/runtime/test_service.py` - extend with normalized-text grounding and fail-closed integration behavior
- [ ] `tests/runtime/test_privacy.py` - extend with no-raw-text logging assertions for richer Phase 4 outputs

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `gguf-laptop` explanation quality is still usable on real consumer hardware | XAI-01, XAI-02 | Mocked tests cannot prove that the laptop baseline remains understandable and grounded once the richer schema lands | Run `python -m src.runtime.cli analyze --text "<representative suspicious text>"` with `RUNTIME_BACKEND=gguf` and `RUNTIME_PROFILE=gguf-laptop`; confirm the output includes grounded cues and safe next steps without schema breakage |
| Accelerated profile stays contract-compatible while improving explanation richness | DET-01, DET-02, XAI-01, XAI-02 | Stronger hardware may improve quality, but it must not drift semantically from the laptop baseline | Run the same representative fixture pack on `accelerated-local` and compare risk tier, label set, evidence behavior, and recommendations against `gguf-laptop` |
| Curated benign banking pack is not over-escalated | DET-01 | Automated suites can count false positives, but a human should confirm that the examples are truly benign and representative | Review the redacted benign fixture pack and confirm at least 80% remain `benign` before Phase 4 closeout |

---

## Validation Sign-Off

- [x] All planned task slices have task-level automated verification commands or Wave 0 dependencies.
- [x] Sampling continuity: no three consecutive tasks without automated verify.
- [x] Wave 0 covers new shared-decision and render test surfaces before prompt-heavy implementation work.
- [x] No watch-mode flags.
- [x] Feedback latency target stays under 25 seconds for automated checks.
- [x] `nyquist_compliant: true` set in frontmatter.

**Approval:** pending

<!-- markdownlint-enable MD003 MD022 MD036 MD041 MD060 -->