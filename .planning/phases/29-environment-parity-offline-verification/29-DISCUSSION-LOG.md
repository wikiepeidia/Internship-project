# Phase 29: Environment Parity & Offline Verification - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-02
**Phase:** 29-Environment Parity & Offline Verification
**Areas discussed:** Fresh-install simulation, Env var portability fix, Font self-hosting approach, Offline test invasiveness

---

## Fresh-Install Simulation

| Option | Description | Selected |
|--------|-------------|----------|
| Fresh venv in a new folder | Clean directory, new venv, pip install from scratch | |
| New Windows user profile | More thorough but heavier to set up | |
| Skip fresh-install, just re-verify current setup | Lower rigor — confirm doctor passes after reboot | |

**User's choice:** None of the above — skip entirely. "We don't need this, I am running on my laptop anyway."
**Notes:** Presentation machine = dev machine, confirmed. Phase 28's DIAG-01 already proved doctor READY on this exact machine. ENV-01 reduced to a sanity re-check, not a from-scratch install test.

---

## Env Var Portability Fix

| Option | Description | Selected |
|--------|-------------|----------|
| Permanent Windows env var via setx | Works from any terminal/folder forever, survives reboots | ✓ |
| Launcher script sets env vars first | No permanent system change, but must remember to use the script | |

**User's choice:** Permanent Windows env var via setx (Recommended)

---

## Font Self-Hosting Approach

| Option | Description | Selected |
|--------|-------------|----------|
| Download official .woff2 from Google Fonts | Same weights, exact glyphs already tested for Vietnamese diacritics | ✓ |
| Use a system-installed fallback instead | Simpler but changes the demo's visual identity | |

**User's choice:** Download official .woff2 from Google Fonts (Recommended)

---

## Offline Test Invasiveness

| Option | Description | Selected |
|--------|-------------|----------|
| Actually disable Wi-Fi during the test | Real proof, not just inference | ✓ |
| Lighter check: grep + DevTools only | No need to cut connectivity | |

**User's choice:** Actually disable Wi-Fi during the test (Recommended)

---

## Claude's Discretion

- Exact `setx` invocation syntax and current-session env var handling
- Vendored font file directory naming/structure
- Wi-Fi re-enable / post-test doctor re-check procedure

## Deferred Ideas

None — discussion stayed within phase scope.

## Incidental Finding

While confirming current `MODEL_ARTIFACT_ROOT`/`MODEL_REGISTRY_PATH` values, `.env/.env` was read and found to contain live API keys (Anthropic, OpenRouter, DeepSeek, etc.) in plaintext alongside the model paths. Confirmed gitignored and never committed to git history — no leak. Not in scope for this phase (unrelated to model-path env vars), noted here for awareness only.
