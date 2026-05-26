---
phase: 07
slug: proposal-closeout-and-quantitative-validation
status: verified
threats_open: 0
asvs_level: 1
created: 2026-05-26
---

<!-- markdownlint-disable MD060 MD047 -->

# Phase 07 - Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| off-repo model registry -> GGUF runtime loader | Phase 7 selects the refreshed closeout model from an operator-managed registry and local artifact root outside the repo. | Candidate IDs, artifact paths, SHA256 metadata, GGUF files |
| GGUF output -> shared local decision layer | Raw model JSON remains untrusted until cue types, evidence spans, labels, and recommendations are normalized and validated. | Generated text, evidence spans, cue types, recommendations |
| repaired holdout split -> evaluation snapshot | The held-out split is re-evaluated through the live runtime and persisted for resume and later review. | Synthetic message text, gold labels, predictions, reviewable source text |
| saved snapshot -> review pack -> final release verdict | Phase 7 reuses the saved Phase 5 evidence path, so provenance must survive manual review and final verdict synthesis. | Run IDs, split provenance, review completion state, blocker reasons, metrics |
| local planning artifacts -> school-facing closeout evidence | Internal planning files feed one final proposal answer about the repaired holdout run. | Macro/weighted F1, per-label metrics, release verdict, accepted-risk notes |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-07-01 | Tampering | src/runtime/analyzers/local_model.py | mitigate | `_normalize_evidence_cue_type()`, `_coerce_payload_evidence()`, and `_apply_safety_floor()` normalize unsupported model cue aliases, drop ungrounded evidence, and preserve benign decisions when helper cues are too generic to map safely; `tests/runtime/test_local_model.py` locks the cue-alias and safety-floor regressions. | closed |
| T-07-02 | Denial of Service | src/runtime/analyzers/local_model.py | mitigate | The Phase 7 safety-floor fix catches unmappable benign escalations instead of letting runtime analysis abort, while the typed `ThreatDecision` contract keeps malformed payloads fail-closed; `tests/runtime/test_local_model.py` covers both the harmful-benign escalation path and the preserved-benign path. | closed |
| T-07-03 | Tampering | src/model_adaptation/release_evaluation.py | mitigate | `_load_resumable_rows()` only resumes when `run_id`, `evaluated_split_path`, row count, gold labels, and reviewable source text still match the active split, and checkpoint writes stay schema-backed through `ReleaseEvaluationSnapshot`; `tests/model_adaptation/test_release_evaluation.py` covers periodic checkpoints and resume-from-matching-snapshot behavior. | closed |
| T-07-04 | Repudiation | src/model_adaptation/release_gates.py and src/model_adaptation/schemas.py | mitigate | `ReleaseEvaluationSnapshot` and `ExplanationReviewPack` persist run IDs, split provenance, locked label order, and source snapshot path, while `synthesize_release_verdict()` rejects mismatched `run_id` values and incomplete review packs before writing the final markdown and JSON artifacts. | closed |
| T-07-05 | Spoofing | src/model_adaptation/registry.py and src/runtime/analyzers/gguf.py | mitigate | Phase 7 resolves the shipped runtime artifact from `baseline_winner_id` selection metadata, `find_latest_artifact()` prefers the newest registered GGUF for that candidate, the registry records SHA256 digests for artifacts, and `GGUFAnalyzer` refuses missing artifact paths. | closed |
| T-07-06 | Information Disclosure | repaired-holdout review and release artifacts | mitigate | The closeout evidence path is generated from the synthetic `recovered-balanced` corpus rather than live user submissions, and the school-facing release artifact exposes aggregate metrics and blocker reasons instead of raw payload dumps; raw review text stays confined to the local planning review pack. | closed |
| T-07-07 | Elevation of Privilege | operator-managed off-repo registry manifest | accept | Phase 7 intentionally trusts `D:/PROJEct/AI MODELS/manifests/model-registry.json` and does not enforce a runtime trusted-root allowlist or checksum re-verification when loading the selected GGUF path. This residual risk is accepted because the closeout workflow is single-user and local-only; exploiting the manifest requires pre-existing local write access outside the repo threat envelope. | closed |

*Status: open · closed*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-07-01 | T-07-07 | The Phase 7 runtime trusts the operator-owned off-repo model registry and artifact root instead of enforcing a hardcoded trusted-root allowlist at load time. In this project, that manifest is part of the local single-user workflow, and tampering it already implies local write access beyond the repo's intended threat model. | project local-only trust model | 2026-05-26 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-05-26 | 7 | 7 | 0 | GitHub Copilot |

- Retroactive STRIDE audit: Phase 7 had no formal `<threat_model>` block and no phase summary file, so this register was derived from the executed plan/context/UAT artifacts plus the Phase 7 implementation and regression tests.

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-05-26

<!-- markdownlint-enable MD060 MD047 -->