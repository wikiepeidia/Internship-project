# Phase 28: Baseline Readiness & Zero-Code Diagnostics - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-02
**Phase:** 28-Baseline Readiness & Zero-Code Diagnostics
**Areas discussed:** Golden prompt content, Verification path, Benign message difficulty, Decoding determinism

---

## Golden Prompt Content

| Option | Description | Selected |
|--------|-------------|----------|
| No, pick for me | Select from existing sample/test data and verify it's stable | ✓ |
| Yes, I have specific text | Type the exact scam message to use | |

**User's choice:** No, pick for me (Recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Bank impersonation | Most universally recognizable to a non-technical committee | ✓ |
| Task scam | "Light work, high pay" job scam (Phase 7a recall recovery class) | |
| Account takeover / social engineering | Zalo/Messenger compromised-contact trust abuse | |

**User's choice:** Bank impersonation (Recommended)
**Notes:** Discovered during discussion — `src/runtime/demo_assets/demo.js` already ships a `sampleText` constant (VPBank OTP-lock impersonation message) wired to the demo's sample button. Strong existing candidate.

---

## Verification Path

| Option | Description | Selected |
|--------|-------------|----------|
| Web demo | Matches exactly what the committee will see live | ✓ |
| CLI only | Faster to script for repeated runs, skip browser layer | |
| Both | CLI for quick repetition, then a final web-demo confirmation pass | |

**User's choice:** Web demo (Recommended)

---

## Benign Message Difficulty

| Option | Description | Selected |
|--------|-------------|----------|
| Obviously safe | Lower risk for a ~1-minute live demo — clean, unambiguous result | ✓ |
| Trickier legitimate message | More impressive if it works, but risks an embarrassing false positive live | |

**User's choice:** Obviously safe (Recommended)

---

## Decoding Determinism

**Notes:** Code inspection during discussion confirmed `temperature=0.0` (GGUF) and `do_sample=False` (accelerated) are already hardcoded — decoding is already greedy/deterministic. No config-change question was needed.

| Option | Description | Selected |
|--------|-------------|----------|
| Reject and pick a different message | Don't dig into the model — try other candidates until one is rock-solid across 5+ runs | ✓ |
| Investigate root cause | Worth understanding why greedy decoding still flips, even if it delays Phase 28 | |

**User's choice:** Reject and pick a different message (Recommended)
**Notes:** Root-causing decoding nondeterminism is out of scope for this verification/hardening milestone.

---

## Claude's Discretion

- Exact final golden prompt text (once a stable candidate passes 5/5 runs)
- How the 5+ repeated runs are executed (manual vs. Playwright script)

## Deferred Ideas

None — discussion stayed within phase scope.
