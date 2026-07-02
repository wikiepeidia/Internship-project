# Phase 29: Environment Parity & Offline Verification - Context

**Gathered:** 2026-07-02
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase verifies the demo runs cleanly and fully offline on the presentation machine — which is confirmed to be the same laptop used for development, not a separate machine — and fixes the two real portability/offline gaps found by prior research: CWD-relative `.env/.env` model-path resolution, and the Google Fonts CDN dependency. It does not touch latency tuning (Phase 30), UI/CLI fixes (Phase 31), or fallback recording (Phase 32).

</domain>

<decisions>
## Implementation Decisions

### Presentation Machine Identity
- **D-01:** The presentation machine is the same laptop used for development — NOT a separate machine. This significantly narrows this phase's scope compared to the original research assumption (which treated "the presentation laptop" as an unknown, possibly-different machine).
- **D-02:** No fresh-install simulation (new venv, new profile, or clean clone) is needed for ENV-01. Phase 28's DIAG-01 already confirmed `vnphish doctor` reports READY on this exact machine. ENV-01 for this phase is reduced to a sanity re-check — confirm doctor still passes — not a from-scratch install test.

### Env Var Portability (ENV-04)
- **D-03:** Fix the CWD-relative `.env/.env` model-path fragility (identified in Phase 28 research as the single highest-risk portability issue — `Settings` resolves `.env/.env` relative to current working directory, so launching `vnphish` from a different folder silently falls back to the wrong model path) by setting **permanent Windows environment variables** via `setx MODEL_ARTIFACT_ROOT` and `setx MODEL_REGISTRY_PATH` — not a launcher script. Rationale: works from any terminal/folder forever, survives reboots, zero per-launch setup or discipline required (a launcher script only helps if the user remembers to always use it).
- Current values to preserve (from `.env/.env`): `MODEL_ARTIFACT_ROOT=D:\PROJEct\AI MODELS`, `MODEL_REGISTRY_PATH=D:\PROJEct\AI MODELS\manifests\model-registry.json`.
- After setting the permanent env vars, verify by launching `vnphish doctor` from a working directory OTHER than the repo root (e.g. `cd C:\` first) and confirming it still resolves the correct off-repo model path instead of failing or falling back to a repo-relative path.

### Font Self-Hosting (ENV-03)
- **D-04:** Self-host Be Vietnam Pro by downloading the official `.woff2` files directly from Google Fonts (same weights currently loaded: 400, 500, 600, 700) and vendoring them into `src/runtime/demo_assets/fonts/` (or similar). Do NOT drop the font for a system fallback — the font choice is part of the shipped visual identity from prior UI milestones (v2.0) and was specifically chosen/tested for Vietnamese diacritic rendering.
- Replace the `<link rel="preconnect" href="https://fonts.googleapis.com">` / `fonts.gstatic.com` / `fonts.googleapis.com/css2?family=Be+Vietnam+Pro...` lines in `src/runtime/demo_assets/index.html` with local `@font-face` declarations pointing at the vendored files.
- After the fix, grep all demo assets for any remaining `http(s)://` reference to confirm this was the only CDN dependency (per Phase 28 research, this is a "confirmed, already-identified leak" — no other CDN references are expected, but must be verified, not assumed).

### Offline Verification Method (ENV-02)
- **D-05:** Prove offline capability by **actually disabling Wi-Fi/Ethernet** on the laptop during the test, then running the full golden-prompt flow (the locked scam + benign prompts from Phase 28) through the real web demo. Do not settle for a lighter grep-only or DevTools-only check — the user wants real proof, not just inference, since this is a claim that will be stated to the defense committee.
- After the network-disabled run succeeds, also confirm via DevTools Network tab that zero external requests were attempted (this is a secondary confirmation, not a replacement for actually cutting connectivity).

### Claude's Discretion
- Exact `setx` invocation syntax and whether to also set the vars in the current session (`set` before `setx` takes effect in new shells) is an implementation detail for the planner/executor.
- Exact vendored font file directory name/path structure under `demo_assets/` is Claude's call, following whatever pattern is cleanest given the existing `demo_assets/` layout.
- How to re-enable Wi-Fi/confirm no side effects after the offline test (e.g. re-running doctor) is standard executor discretion.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Research (this milestone)
- `.planning/research/SUMMARY.md` §"Phase 2: Environment Parity & Offline Verification" — the original research plan for this phase (written before D-01/D-02 narrowed scope; treat its "fresh laptop" framing as superseded by D-01/D-02, but its ENV-03/ENV-04/ENV-05 guidance still applies)
- `.planning/research/PITFALLS.md` — Pitfall 1 (environment drift / CWD-relative `.env` discovery), Pitfall 3 (Google Fonts CDN leak) — both directly scoped by this phase
- `.planning/research/ARCHITECTURE.md` — `Settings` (pydantic-settings) CWD-relative `.env/.env` resolution mechanics

### Prior Phase (28)
- `.planning/phases/28-baseline-readiness-zero-code-diagnostics/28-CONTEXT.md` — locked golden prompts (scam + benign) to reuse for this phase's offline verification run
- `.planning/phases/28-baseline-readiness-zero-code-diagnostics/artifacts/28-golden-prompt-results.json` — the exact locked prompt text and channel to reuse
- `.planning/phases/28-baseline-readiness-zero-code-diagnostics/28-01-SUMMARY.md` — records 2 real runtime bugs found/fixed during Phase 28 (legitimate bank OTP false positive, no-OTP link scam false negative) — informs what "correct" means for the reused golden prompts

### Requirements & Roadmap
- `.planning/REQUIREMENTS.md` §"v5.1 Requirements" — ENV-01 through ENV-05
- `.planning/ROADMAP.md` §"Phase 29: Environment Parity & Offline Verification" — success criteria

### Source Code
- `src/config/settings.py` — `Settings` class, CWD-relative `.env/.env` discovery logic to work around via D-03
- `.env/.env` — current `MODEL_ARTIFACT_ROOT` / `MODEL_REGISTRY_PATH` values to preserve when moving to OS-level env vars (gitignored, contains other unrelated API keys — do not touch those)
- `src/runtime/demo_assets/index.html` (lines ~8-11) — Google Fonts CDN links to replace per D-04
- `src/runtime/doctor.py` — `run_runtime_doctor()` used for the ENV-01 sanity re-check

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Phase 28's locked golden prompts (Vietcombank malicious-link scam, VPBank Smart OTP benign) are the exact inputs to reuse for the ENV-02 offline verification run — no new test messages needed.
- Phase 28's `scripts/verify_golden_prompts.py` Playwright script may be reusable or adaptable for driving the offline verification run through the real web demo, rather than writing a new script from scratch.

### Established Patterns
- `.env/.env` is gitignored and currently holds `MODEL_ARTIFACT_ROOT` and `MODEL_REGISTRY_PATH` alongside unrelated cloud API keys (Anthropic, OpenRouter, DeepSeek, etc. used by other dev tooling in this repo) — the env-var migration in this phase only concerns the two model-path variables, not the API keys.
- Be Vietnam Pro is currently loaded at weights 400/500/600/700 via Google Fonts `css2` API — the self-hosted replacement must cover the same four weights to avoid a visual regression.

### Integration Points
- `Settings` (pydantic-settings) reads `MODEL_ARTIFACT_ROOT`/`MODEL_REGISTRY_PATH` — once these exist as OS-level env vars, `Settings` should pick them up automatically without code changes (env vars typically take precedence over or supplement `.env` file values in pydantic-settings' resolution order) — the planner/executor should confirm this precedence behavior rather than assume it.

</code_context>

<specifics>
## Specific Ideas

- Use `setx` for permanent env vars, preserving current `D:\PROJEct\AI MODELS` values.
- Download real Be Vietnam Pro `.woff2` files (400/500/600/700) from Google Fonts, vendor locally, replace CDN `<link>` tags with local `@font-face`.
- Prove offline capability with an actual Wi-Fi-off test run using Phase 28's locked golden prompts, not just static analysis.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 29-Environment Parity & Offline Verification*
*Context gathered: 2026-07-02*
