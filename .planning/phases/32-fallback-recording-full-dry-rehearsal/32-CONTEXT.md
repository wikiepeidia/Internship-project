# Phase 32: Fallback Recording & Full Dry Rehearsal - Context

**Gathered:** 2026-07-09
**Status:** Ready for planning
**Mode:** Smart discuss (autonomous, batched grey-area questions)

<domain>
## Phase Boundary

This phase prepares the defense-day fallback safety net: a recorded video and screenshot sequence of the 2 locked golden prompts (scam + benign, from Phase 28), at least one rehearsed live-to-fallback pivot, and one dry rehearsal proving the demo starts cleanly from a fresh state using the final Phase 31 launchers. It does not change the backend, model, prompts, UI, or CLI — those are frozen inputs from Phases 28-31. It does not redesign the release gate or retrain anything.

</domain>

<decisions>
## Implementation Decisions

### Capture Method (FB-01/FB-02)
- The user will personally screen-record the real desktop demo themselves (OBS/Xbox Game Bar or similar) — not automated by the agent. The agent does not build Playwright-based video/screenshot capture tooling for this.
- Save locations for the two local copies of the recording/screenshots are the user's own discretion — the agent does not manage or script folder placement for this.
- Screenshot sequence granularity/tooling is the user's own discretion, done manually alongside the recording.
- Agent's role here is limited to making the golden-prompt run trivially reproducible for recording: confirm the exact locked scam/benign text (reused verbatim from `28-golden-prompt-results.json` / `scripts/verify_golden_prompts.py` defaults) is easy to find and paste.

### Live-to-Fallback Pivot Rehearsal (FB-03)
- The user will personally rehearse the pivot (simulating a live-demo failure and switching to the recording/screenshots) — no scripted interruption or agent involvement needed.
- Agent's role is limited to (optionally) providing a short written pivot checklist/runbook the user can follow while rehearsing on their own; the agent does not perform or verify the rehearsal itself.

### Cold-Boot Dry Rehearsal (FB-04) — SUBSTITUTED SCOPE, explicit user decision 2026-07-09
- User explicitly chose to **skip the literal full shutdown/power-cycle**. Substitute: the agent builds and runs an automated **fresh-process dry-run** — stop any running demo process, launch a completely new process via the actual `scripts/START_DEMO_UI.bat` launcher (not a bypassed direct CLI invocation, since FB-04 specifically requires "using final launchers"), wait for real readiness, then run both locked golden prompts once each through the real browser UI and confirm stable/correct verdicts.
- **Explicit gap, must be documented, not overstated:** this fresh-process substitute does NOT exercise true cold-boot-specific effects (OS/driver reinitialization, OneDrive re-sync catch-up after a real power-on, Windows Defender re-scan behavior on first launch). It is a lighter automated proxy for FB-04, not literal compliance with the ROADMAP success criterion #4 ("full cold-boot dry rehearsal"). This substitution and its rationale (user time constraint, accepted risk) must be recorded plainly in the plan's artifacts/evidence and in the phase SUMMARY — do not claim literal cold-boot coverage. If the user later wants true cold-boot coverage before 2026-07-13, they can do it manually; that remains their action, not the agent's.
- The presentation laptop is confirmed to be this same machine (Phase 29 evidence: `D:\PROJEct\AI MODELS`, `MODEL_ARTIFACT_ROOT`/`MODEL_REGISTRY_PATH` env vars, `vnphish doctor` READY from `C:\`) — no separate/unknown hardware involved.

### Claude's Discretion
- Exact artifact filenames/JSON schema for the FB-04 fresh-process dry-run evidence.
- Exact wording/format of the optional FB-01/02/03 human checklist (short, plain, not overbuilt — the user is doing these steps themselves).
- How the fresh-process harness attaches Playwright to the browser session launched by `START_DEMO_UI.bat` (the .bat opens a system default browser via `python -m src.runtime.cli demo`, not a Playwright-controlled one) — the agent should poll for server readiness on the known port and drive a separate Playwright instance against that same localhost port, consistent with the Phase 28/30/31 verifier pattern.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `scripts/verify_golden_prompts.py` — already owns a `vnphish demo` subprocess lifecycle, locked scam/benign text (`DEFAULT_SCAM_TEXT`, `DEFAULT_BENIGN_TEXT`), Playwright browser drive, and stable/verdict recording. Closest analog for the FB-04 fresh-process dry-run script.
- `scripts/verify_ui_quirks.py` (Phase 31) — Playwright subprocess lifecycle pattern with readiness polling, console/error capture, process cleanup in `finally`.
- `scripts/START_DEMO_UI.bat` (Phase 31) — the actual launcher FB-04 must exercise; `cd /d "%~dp0.."`, `chcp 65001`, invokes `python -m src.runtime.cli demo`.

### Established Patterns
- All Phase 28/30/31 browser verifiers reuse the same subprocess + Playwright + readiness-polling + `finally`-cleanup shape. FB-04's harness should follow the same shape rather than inventing a new one.
- `playwright>=1.58` is already a project dependency — no new dependency needed for the FB-04 automated portion.

### Integration Points
- FB-04 harness needs to determine the port/URL the `.bat`-launched process will serve on (check `src/runtime/cli.py` demo command default port) so Playwright can attach independently of whatever system browser window the `.bat` auto-opens.

</code_context>

<specifics>
## Specific Ideas

- Locked golden prompts (verbatim, do not alter): scam = Vietcombank no-OTP malicious-link alert; benign = VPBank Smart OTP notice. Exact text lives in `scripts/verify_golden_prompts.py` (`DEFAULT_SCAM_TEXT`, `DEFAULT_BENIGN_TEXT`) and `.planning/phases/28-baseline-readiness-zero-code-diagnostics/artifacts/28-golden-prompt-results.json`.
- FB-04 dry-run must invoke the real `.bat` launcher, not a bypassed direct CLI call, per the requirement's "using final launchers" wording.

</specifics>

<deferred>
## Deferred Ideas

- Automated Playwright video/screenshot capture tooling for FB-01/FB-02 — user chose manual screen-recording instead; not built this phase.
- Scripted live-demo-kill for FB-03 rehearsal — user chose to rehearse this personally; not built this phase.
- Literal full shutdown/power-cycle cold-boot test — explicitly descoped by user decision 2026-07-09; substituted with fresh-process dry-run (see Decisions above). Not a deferred-to-later item, a permanent scope substitution for this phase.

</deferred>
