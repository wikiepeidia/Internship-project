# Phase 4: Threat Detection and Explainable Decisioning - Context

**Gathered:** 2026-05-17
**Status:** Ready to start

## Phase Boundary

Turn the now-real local deployment paths from Phase 3 into a domain-faithful detector that returns stable risk tiers, in-scope threat labels, evidence-bound explanations, and actionable safety guidance for pasted text messages.

**Scope guardrails:**

- Keep v1 text-only and offline/local-first.
- Build on the existing runtime contracts and CLI surfaces instead of replacing them.
- Focus on DET and XAI behavior, not new training hardware experiments or release-gate benchmarking.
- Preserve privacy-safe handling of raw message text.

**CPU clarification:** The project's consumer CPU or iGPU target was already addressed in Phase 3 through the GGUF inference path. Phase 4 is about improving decision quality and explanation quality on top of those local runtimes, not about making fine-tuning run on CPU.

## Implementation Decisions

### Accepted Inputs and Runtime Baseline

- **D-01:** Phase 4 starts from the real Phase 3 deployment surfaces: `gguf-laptop` as the consumer baseline and `accelerated-local` as the stronger local path.
- **D-02:** Phase 4 must preserve explicit runtime-profile selection rather than collapsing back to a single hidden backend.
- **D-03:** The public runtime contract from Phase 2 and Phase 3 remains the compatibility boundary for Phase 4 outputs.

### Detection and Label Scope

- **D-04:** Risk-tier output remains exactly three-way: `benign`, `suspicious`, and `high-risk`.
- **D-05:** In-scope threat labels remain limited to bank impersonation, account takeover or social engineering, and light-work-high-pay task scams.
- **D-06:** Explanations must cite concrete cues from the provided text and not fall back to generic scam boilerplate.
- **D-07:** Recommendations must stay user-safe and non-autonomous, such as warning against clicking links or urging trusted-channel verification.

### Data and Model Assumptions

- **D-08:** Phase 4 should use the retained validated dataset and the trained Phase 3 artifacts as the starting point instead of reopening candidate selection.
- **D-09:** The locked baseline remains `qwen3-4b-instruct-2507`; the locked runner-up remains `qwen3.5-4b`.
- **D-10:** Any prompt or post-processing changes must remain compatible with later Phase 5 evaluation gates.

## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Requirements and Status

- `.planning/REQUIREMENTS.md` — `DET-01`, `DET-02`, `XAI-01`, and `XAI-02` define the Phase 4 acceptance surface.
- `.planning/PROJECT.md` — Core constraints: text-only v1, offline/local inference, privacy-first behavior, and the clarified CPU baseline.
- `.planning/ROADMAP.md` — Phase 4 goal, dependencies, and success criteria.
- `.planning/STATE.md` — Phase 3 is complete and Phase 4 is the active re-entry point.

### Upstream Phase Artifacts

- `.planning/phases/03-local-model-adaptation-and-deployment-paths/03-UAT.md` — Phase 3 closeout status and evidence.
- `.planning/phases/03-local-model-adaptation-and-deployment-paths/03-05-SUMMARY.md` — Real GGUF conversion and baseline laptop runtime closeout.
- `.planning/phases/03-local-model-adaptation-and-deployment-paths/03-06-SUMMARY.md` — Real accelerated runner-up runtime closeout.
- `.planning/phases/03-local-model-adaptation-and-deployment-paths/03-07-SUMMARY.md` — Supervisor-facing proposal reconciliation note.

## Existing Code Insights

### Reusable Assets

- `src/runtime/contracts.py` already defines the structured result contract that Phase 4 should enrich without destabilizing.
- `src/runtime/service.py` already centralizes request normalization, fail-closed behavior, and backend routing.
- `src/runtime/analyzers/gguf.py` now provides the real baseline local inference path for consumer hardware.
- `src/runtime/analyzers/accelerated.py` now provides the real accelerated runner-up path for stronger local hardware.
- `src/runtime/analyzers/local_model.py` already contains shared structured-prompt and parse helpers that Phase 4 can refine.

### Established Patterns

- Runtime profile selection is explicit and should stay explicit.
- Doctor readiness and analyze behavior are already validated entrypoints and should remain the operator-facing surface.
- Structured output stability matters because later tests and user-facing rendering depend on the current typed contract.

### Integration Points

- Phase 4 should improve classification quality, label assignment, evidence extraction, and recommendations without breaking the Phase 2 CLI or Phase 3 local-model loading.
- Changes made in Phase 4 should be measurable later by Phase 5 evaluation gates rather than relying only on anecdotal smoke tests.

## Specific Ideas

- Start by tightening the model prompt and response schema around the four required outcomes: risk tier, threat labels, evidence cues, and recommendations.
- Treat evidence linkage as a first-class requirement, not a nice-to-have explanation garnish.
- Keep the baseline `gguf-laptop` path honest about its likely capability ceiling; if richer explanation quality requires the accelerated path, that should be explicit in tests and docs rather than hidden.
- Use the retained validated split and representative Vietnamese scam patterns to define targeted acceptance fixtures early, before broad prompt iteration.

## Deferred Ideas

- Do not reopen model-family selection or pilot scoring in Phase 4.
- Do not expand to OCR, screenshots, or voice channels.
- Do not move release-gate threshold setting into Phase 4; that belongs in Phase 5.

## Current Re-entry Point

- Phase 3 is complete and no longer the blocker.
- The next actionable work is to define and implement the Phase 4 decision contract over the existing real local backends.
- The first planning question for Phase 4 is not hardware. It is how to make risk tiers, threat labels, evidence cues, and recommendations accurate enough to satisfy `DET-01`, `DET-02`, `XAI-01`, and `XAI-02`.

---

*Phase: 04-threat-detection-and-explainable-decisioning*
*Context created: 2026-05-17 after Phase 3 closeout*
