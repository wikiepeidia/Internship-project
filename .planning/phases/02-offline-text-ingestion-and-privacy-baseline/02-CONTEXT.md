<!-- markdownlint-disable MD001 MD022 MD032 MD033 -->

# Phase 2: Offline Text Ingestion and Privacy Baseline - Context

**Gathered:** 2026-05-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver the first local text-analysis runtime for the project: a user can paste one suspicious message at a time into a CLI-backed analyzer, the system accepts Vietnamese and mixed Vietnamese-English text, returns a provisional offline result, and enforces the privacy-first text-only boundary by default. Final trained local model adaptation, stable threat labeling, and the full evidence-linked explanation system remain in later phases.

</domain>

<decisions>
## Implementation Decisions

### User Entry Surface
- **D-01:** Phase 2 should be CLI-first, backed by a reusable Python analyzer service rather than a web UI.
- **D-02:** The primary flow is one pasted message per run, not batch analysis or an interactive session.
- **D-03:** The main user path should be one obvious command with minimal flags.

### Offline Baseline Behavior
- **D-04:** Before the trained local model exists, Phase 2 should use a local heuristic/rule-based screener behind an analyzer interface that later phases can swap out.
- **D-05:** The baseline should use the same three risk tiers already present in the dataset schema (`benign`, `suspicious`, `high-risk`), but clearly mark them as provisional.
- **D-06:** The default output should be a short human-readable summary rather than JSON-only or a bare verdict.

### Privacy and Failure Boundaries
- **D-07:** Raw submitted messages must not be persisted by default.
- **D-08:** Non-text input stays out of scope in Phase 2; reject it and instruct the user to paste extracted text manually.
- **D-09:** If the local analyzer is unavailable or fails, the tool should fail closed, stay local, and give setup/error guidance instead of offering cloud fallback.

### Cue Presentation
- **D-10:** Baseline suspicious cues should quote exact text spans from the pasted message and pair each span with a short plain-language reason.
- **D-11:** Show at most the top three cues in the default result.

### Local Setup and Diagnostics
- **D-12:** The main analyze command should run a self-check and print exact local setup steps automatically when the analyzer environment is not ready.
- **D-13:** Phase 2 should also expose a simple dedicated doctor/check command alongside the main analyze command.

### the agent's Discretion
- Exact command names, parser library, and package/module layout for the CLI/runtime surface.
- Exact heuristic rules, cue-ranking logic, and phrasing of setup guidance.
- Whether optional channel/source hints are added as a non-required input, as long as raw message text remains the only required payload and the text-only scope is preserved.

</decisions>

<specifics>
## Specific Ideas

- Keep the main analyze flow low-friction: one clear command for normal use, with diagnostics available when needed.
- Even in the provisional Phase 2 baseline, the output should point back to exact suspicious text, not only abstract reasons.
- The privacy promise must hold in failure paths too: no accidental cloud submission and no silent raw-message retention.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Scope and Acceptance
- `.planning/PROJECT.md` — Core value and non-negotiable constraints: text-only v1, offline-first privacy, recall-priority posture.
- `.planning/REQUIREMENTS.md` — Phase 2 acceptance criteria for `ING-01`, `ING-02`, and `RUN-01`, plus out-of-scope boundaries for non-text and cloud-default behavior.
- `.planning/ROADMAP.md` — Phase 2 goal, dependency on Phase 1, and success criteria that define the planning target.

### Continuity From Prior Work
- `.planning/STATE.md` — Current project status and active risks that still constrain runtime design.
- `.planning/phases/01-data-foundation-and-split-governance/01-CONTEXT.md` — Carry forward Phase 1 decisions on preserving code-switching, teencode, and normalization fidelity.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/config/settings.py`: existing environment-driven settings object can hold runtime paths, thresholds, and local analyzer configuration.
- `src/data_pipeline/processing/normalizer.py`: `normalize_text` already fixes mojibake, enforces NFC normalization, and preserves Vietnamese code-switch tokens for pasted user input.
- `src/data_pipeline/schemas.py`: existing schema vocabulary already defines `risk_tier` and suspicious-span-oriented fields that the provisional baseline can align with.
- `tests/data_pipeline/test_normalizer.py` and `tests/data_pipeline/test_schemas.py`: existing tests already establish how normalization and schema validation are expected to behave.

### Established Patterns
- Python-only codebase with Pydantic settings/models and pytest-based validation.
- Normalize-first, validate-second data handling pattern.
- Local configuration comes from `.env/` files and OS environment variables; secrets are not hardcoded.

### Integration Points
- The new analyzer service and CLI should sit alongside the existing Python modules and reuse normalization/config rather than duplicating them.
- The provisional risk-tier vocabulary should stay compatible with `DatasetRecord` so later phases can replace the engine without replacing the response contract.
- The doctor/check path should inspect local runtime readiness without retaining submitted message content.

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-offline-text-ingestion-and-privacy-baseline*
*Context gathered: 2026-05-04*

<!-- markdownlint-enable MD001 MD022 MD032 MD033 -->