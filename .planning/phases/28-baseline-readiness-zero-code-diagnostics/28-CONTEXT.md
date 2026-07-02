# Phase 28: Baseline Readiness & Zero-Code Diagnostics - Context

**Gathered:** 2026-07-02
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase establishes whether the demo's core functionality is reproducibly correct on the dev machine, using only existing zero-code diagnostics (`vnphish doctor`, `vnphish analyze`, browser DevTools) — no new tooling is built here. It also selects and locks the exact 2 prompts (1 scam + 1 benign) that will be used for the real ~1-minute live demo during the defense, proving each is correct across 5+ repeated runs before being locked. It does not touch environment portability (Phase 29), latency tuning (Phase 30), UI/CLI fixes (Phase 31), or fallback recording (Phase 32).

</domain>

<decisions>
## Implementation Decisions

### Golden Prompt Selection
- **D-01:** Do not ask the user for exact wording — select and verify a candidate from existing sample/test data rather than inventing new text.
- **D-02:** The golden "scam" prompt must represent the **bank impersonation** threat class (most universally recognizable to a non-technical committee).
- **D-03:** Strong existing candidate found during discussion: `src/runtime/demo_assets/demo.js` already ships a `sampleText` constant used by the demo's sample button — a VPBank OTP-lock impersonation message in Vietnamese. This is the natural first candidate to test for stability; use it unless it fails the 5-run stability check, in which case fall back to another bank-impersonation example from `data/splits/*/val.jsonl` or held-out test fixtures.

### Benign Prompt Difficulty
- **D-04:** The golden benign prompt must be **obviously safe** — a clean, unambiguous "no threat" message. Do NOT use a trickier "looks suspicious but legitimate" message. Rationale: for a ~1-minute live demo in front of a defense committee, an unambiguous correct result is worth more than demonstrating precision on a hard edge case — there's no room for a surprising misfire live.
- Look for benign-labeled examples in existing test fixtures (`tests/runtime/*`, `data/splits/*/val.jsonl` with `label: benign`) rather than writing one from scratch.

### Verification Path
- **D-05:** The 5+ repeated-run stability check for both golden prompts runs through the **actual web demo** (`vnphish demo`, real browser, real fetch to `/api/analyze`), not just the CLI. Rationale: this must match exactly what the committee will see live — a CLI-only check could miss UI-layer issues (rendering, template population) that the live audience would actually see.
- DIAG-02 (the broader 4-message correctness pass: one per threat class + benign) may still use the CLI (`vnphish analyze`) since that's a broader sanity check, not the golden-prompt lock.

### Decoding Determinism
- **D-06:** Confirmed via code inspection: both `GGUFAnalyzer` (`src/runtime/analyzers/gguf.py`) and the accelerated backend (`src/runtime/analyzers/accelerated.py`) already hardcode `temperature=0.0` / `do_sample=False` — decoding is already greedy/deterministic. **No config change is needed or in scope for this phase.**
- **D-07:** If a golden prompt candidate still flips between correct/incorrect across the 5+ runs despite greedy decoding (e.g. from CPU floating-point nondeterminism), the response is to **reject that prompt and try a different candidate** — do NOT spend phase time investigating the root cause of the nondeterminism itself. Root-causing decoding nondeterminism is explicitly out of scope for this milestone (verification/hardening only, no runtime redesign).

### Claude's Discretion
- The exact final golden prompt text (once a stable candidate is confirmed) is Claude's call — pick from the candidates above, run the stability check, and lock whichever passes 5/5 clean.
- How the 5+ repeated runs are executed (manual browser repetition vs. a lightweight Playwright script) is an implementation detail for the planner/executor, not a discussion decision — Phase 28 research already recommends Playwright is already a project dependency.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Research (this milestone)
- `.planning/research/SUMMARY.md` — full v5.1 research synthesis; Phase 28 maps to its "Phase 1: Baseline Readiness & Zero-Code Diagnostics" section
- `.planning/research/STACK.md` — confirms `llama-cpp-python==0.3.23` pin, Playwright already installed for browser-level checks
- `.planning/research/FEATURES.md` — table-stakes verification checklist this phase implements
- `.planning/research/PITFALLS.md` — CLI vs demo readiness-check divergence (`run_runtime_doctor()` vs `service.backend.doctor()`), warm-vs-cold latency caveat

### Requirements & Roadmap
- `.planning/REQUIREMENTS.md` §"v5.1 Requirements — Demo Verification & Presentation Readiness" — DIAG-01..03, GOLD-01, GOLD-02
- `.planning/ROADMAP.md` §"Phase 28: Baseline Readiness & Zero-Code Diagnostics" — success criteria

### Source Code
- `src/runtime/cli.py` — `handle_analyze`, `handle_doctor`, `handle_demo` entrypoints
- `src/runtime/doctor.py` — `run_runtime_doctor()` readiness probe
- `src/runtime/analyzers/gguf.py` (lines ~82, ~97, ~103) — confirmed `temperature=0.0`
- `src/runtime/analyzers/accelerated.py` (line ~143) — confirmed `do_sample=False`
- `src/runtime/demo_assets/demo.js` (line ~17) — existing `sampleText` (VPBank OTP scam) — golden-prompt candidate

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/runtime/demo_assets/demo.js`'s `sampleText` constant is a ready-made bank-impersonation message already wired to the demo's "sample button" (`sample-button` id) — clicking it auto-fills and can auto-submit. Ideal first candidate for the golden scam prompt with zero new content to write.
- `vnphish doctor` (`src/runtime/doctor.py`) is an existing, zero-network readiness probe — use it as-is, don't duplicate its checks.
- Playwright is already a project dependency (used by the NCSC scraper) — available for scripting the repeated browser-level stability runs without adding a new dependency.

### Established Patterns
- Decoding is already greedy (`temperature=0.0`, `do_sample=False`) in both backends — determinism is a code-level guarantee already, not something this phase needs to add.
- `vnphish analyze` and `vnphish demo` use *different* readiness-check code paths (`run_runtime_doctor()` vs `service.backend.doctor()` inside `demo.py`) — a clean `doctor` report doesn't guarantee `demo` starts cleanly; both should be checked independently.

### Integration Points
- Golden-prompt stability verification should hit the real `/api/analyze` endpoint through the browser (per D-05), not just call `RuntimeService` directly in a script.

</code_context>

<specifics>
## Specific Ideas

- Golden scam prompt: default to the existing `demo.js` `sampleText` (VPBank OTP-lock impersonation) unless it fails stability testing.
- Golden benign prompt: pick an obviously-safe example from existing benign-labeled test fixtures, not the trickier "looks suspicious but legitimate" style.
- Both golden prompts get tested for stability via the real web demo in a browser (Playwright-scriptable), 5+ runs each, 100% consistent correct verdict required to lock.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 28-Baseline Readiness & Zero-Code Diagnostics*
*Context gathered: 2026-07-02*
