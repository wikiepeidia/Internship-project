# Phase 31: UI Quirks, Edge Cases & Regression Re-check - Context

**Gathered:** 2026-07-06
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase re-tests the full edge-case matrix through the real web demo, resolves the `vnphish analyze`-vs-`demo` CLI entrypoint confusion, re-verifies the double-submit guard, triages one specific mystery console error found in Phase 29, and confirms none of Phases 28-30's fixes regressed existing behavior. It does not touch fallback recording or full dry rehearsal (Phase 32), and does not reopen latency work (Phase 30 closed with `NO_FIX_APPLIED`).

</domain>

<decisions>
## Implementation Decisions

### Mystery Console Error
- **D-01:** Phase 29 found `ERROR SOURCE_LANG_VI` in the browser console during offline verification, with no matching key/string found anywhere in the local runtime or frontend source (`29-04-SUMMARY.md`). Phase 31 must reproduce it (open the demo, watch DevTools console) and triage: if it traces to actual app code, fix it as a UIQ-04 quirk; if it's confirmed browser/extension noise (e.g., a Chrome DevTools extension artifact, unrelated to `demo.js`/`index.html`), document that finding and stop — do not open-ended hunt for a root cause once non-app origin is confirmed.

### CLI Entrypoint Fix (UIQ-03)
- **D-02:** Ship both fixes together: (1) launcher scripts (`scripts/START_DEMO_UI.bat`, `scripts/START_TEXT_ANALYZE.bat` or similar, per Phase 28 research's original recommendation) for double-click use by a non-technical committee member, AND (2) improved argparse `help=`/description text in `src/runtime/cli.py` so `vnphish --help`, `vnphish analyze --help`, and `vnphish demo --help` clearly state "text-only, no browser page" vs "opens the web UI". Do not restructure the CLI contract itself (subcommand names, flags) — this is additive clarity only, consistent with the milestone's "backend/API contract stays frozen" rule.

### Edge-Case Testing (UIQ-01)
- **D-03:** Test the edge-case matrix (empty input, very long text, malformed/off-topic text, mixed Vietnamese-English) through the real web demo, not CLI-only — reuse the Playwright pattern established in `scripts/verify_golden_prompts.py` (Phase 28) rather than writing an unrelated new harness. A new script or an extension of the existing one is the planner's call, per Phase 28's own precedent of preferring a separate script when the concern (edge-case correctness) is distinct from what's already there (golden-prompt stability).

### Double-Submit Re-verification (UIQ-02)
- **D-04:** Re-verify the `AbortController` re-entrant-submit guard via an automated Playwright test that fires rapid repeated submissions and asserts exactly one in-flight request completes cleanly (no orphaned typing indicator, no unhandled rejection) — not a manual click-spam test. This fits the same Playwright-based approach as D-03 and Phase 28/29's established pattern.

### Regression Re-check Scope
- **D-05:** "Regression re-check" for Phases 28-30 means: re-run Phase 28's golden-prompt stability check (the locked scam + benign prompts, via `scripts/verify_golden_prompts.py` or equivalent) to confirm the 2 runtime bugs fixed in Phase 28 (legitimate-OTP-as-benign, no-OTP-link-scam-detection) are still correctly handled after Phase 29's font-route/env-var changes, and re-run the existing test suites touched by Phase 29 (`tests/runtime/test_local_model.py`, `tests/runtime/test_demo.py`). Phase 30 made no source changes (`NO_FIX_APPLIED`), so there is nothing to regression-check from Phase 30 specifically beyond confirming the demo still starts and serves correctly.

### Claude's Discretion
- Exact launcher script naming/wording and exact new `--help` text phrasing.
- Whether edge-case and double-submit tests live in one new script or two.
- Order of task execution within the phase (the planner should sequence so any UIQ-04 fixes happen before the final regression re-check, to catch late-breaking issues).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Research (this milestone)
- `.planning/research/SUMMARY.md` §"Phase 4: UI Quirks, Edge Cases & Regression Re-check" — original research framing for this phase
- `.planning/research/PITFALLS.md` — Pitfall 7 (`wsgiref` single-threaded re-entrancy / double-submit)
- `.planning/research/ARCHITECTURE.md` — CLI entrypoint disambiguation guidance (launcher scripts over CLI contract changes)

### Prior Phases
- `.planning/phases/28-baseline-readiness-zero-code-diagnostics/28-01-SUMMARY.md` — the 2 real runtime bugs fixed (legitimate bank OTP as benign, no-OTP link-based scam detection)
- `.planning/phases/28-baseline-readiness-zero-code-diagnostics/artifacts/28-golden-prompt-results.json` — locked golden prompts to re-verify for regression
- `.planning/phases/29-environment-parity-offline-verification/29-04-SUMMARY.md` — source of the `ERROR SOURCE_LANG_VI` finding
- `.planning/phases/29-environment-parity-offline-verification/29-VERIFICATION.md` — what Phase 29 changed (font route, env vars, pin) that regression-checking must cover
- `.planning/phases/30-latency-diagnosis-targeted-fix/30-02-SUMMARY.md` — confirms no source changes from Phase 30

### Requirements & Roadmap
- `.planning/REQUIREMENTS.md` §"v5.1 Requirements" — UIQ-01 through UIQ-04
- `.planning/ROADMAP.md` §"Phase 31: UI Quirks, Edge Cases & Regression Re-check"

### Source Code
- `src/runtime/cli.py` — `build_parser()`, `handle_analyze`, `handle_demo` — target for D-02's help-text improvements
- `scripts/verify_golden_prompts.py` — Phase 28's Playwright pattern to extend/reuse for D-03/D-04
- `src/runtime/demo_assets/demo.js` — `AbortController` guard implementation to re-verify (D-04)
- `tests/runtime/test_local_model.py`, `tests/runtime/test_demo.py` — regression test suites to re-run (D-05)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `scripts/verify_golden_prompts.py` (Phase 28) already owns a `vnphish demo` subprocess and drives the real browser via Playwright — the natural base to extend for edge-case and double-submit testing rather than building new subprocess/browser-launch scaffolding.
- Phase 28's locked golden prompts (`28-golden-prompt-results.json`) are the exact regression baseline to re-run.

### Established Patterns
- No launcher `.bat`/`.ps1` scripts exist yet in `scripts/` — this is new ground for D-02, not an extension of an existing pattern.
- `src/runtime/cli.py`'s `build_parser()` already has `help=` strings on every subcommand/argument; D-02 extends this existing convention rather than introducing a new one.

### Integration Points
- Any UIQ-04 fixes discovered during console-error triage or edge-case testing must not alter the frozen `/api/analyze` contract or the `data-slot` template structure (per project-wide hard constraints in STATE.md).

</code_context>

<specifics>
## Specific Ideas

- Reproduce `ERROR SOURCE_LANG_VI` first; only chase further if it's confirmed to originate from app code.
- Ship launcher `.bat` scripts AND improved `--help` text together for the CLI fix.
- All new automated checks (edge cases, double-submit) go through the real web demo via Playwright, consistent with Phase 28/29's established approach.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 31-UI Quirks, Edge Cases & Regression Re-check*
*Context gathered: 2026-07-06*
