---
phase: 28-baseline-readiness-zero-code-diagnostics
status: passed
verified: 2026-07-02T15:15:06+07:00
plans: [28-01]
requirements: [DIAG-01, DIAG-02, DIAG-03, GOLD-01, GOLD-02]
commits: [a509b8b, c3ac707, 2807b54, 7e10592, 2597078]
score: 5/5 must-haves verified
---

# Phase 28 Verification

**Verdict:** PASS

## Goal Achievement

Phase 28 proved the dev-machine demo baseline. A post-closeout quick correction then fixed legitimate bank OTP false positives and relocked the final live-demo prompts through the real web demo. The corrected warm-latency baseline is recorded for Phase 30.

## Observable Truths

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | `vnphish doctor` reports READY on the dev machine. | VERIFIED | `28-RESULTS.md` records exit code 0 and `READY backend=gguf local_only=True text_only=True`. |
| 2 | `vnphish analyze` correctly covers bank impersonation, Zalo social engineering, task scam, and benign. | VERIFIED | `28-RESULTS.md` has four DIAG-02 rows with correct risk tier and threat label. The three threat rows have non-empty grounded cues; the benign row explicitly records `count=0`. |
| 3 | Exactly one scam prompt and one benign prompt are locked for the live-demo script. | VERIFIED | `28-RESULTS.md` lists the malicious-link Vietcombank scam prompt and VPBank Smart OTP benign prompt as the final locked texts. |
| 4 | Each locked prompt is stable across five real web-demo runs. | VERIFIED | `28-golden-prompt-results.json` has 5 scam and 5 benign runs with `stable: true`; `28-RESULTS.md` transcribes both 5-run tables with `STABLE=true`. |
| 5 | A warm-latency baseline is captured for later comparison. | VERIFIED | `28-RESULTS.md` records `26627.258 ms` from Playwright `response.request.timing` for the first real browser `/api/analyze` response in the corrected relock run. |

**Score:** 5/5 truths verified

## Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `scripts/verify_golden_prompts.py` | Playwright verifier for the real demo UI | VERIFIED | 200 lines; syntax check passes; `--help` exposes scam/benign text and channel overrides, port, and run count. |
| `.planning/phases/28-baseline-readiness-zero-code-diagnostics/artifacts/28-RESULTS.md` | Consolidated DIAG and GOLD evidence record | VERIFIED | Contains DIAG-01, DIAG-02, corrected GOLD-01/GOLD-02, and corrected DIAG-03 sections. |
| `.planning/phases/28-baseline-readiness-zero-code-diagnostics/artifacts/28-golden-prompt-results.json` | Machine-readable stability and latency results | VERIFIED | JSON check confirms both `golden_scam.stable` and `golden_benign.stable` are true with five runs each. |
| `.planning/phases/28-baseline-readiness-zero-code-diagnostics/28-01-SUMMARY.md` | Standard plan execution summary | VERIFIED | Captures task commits, decisions, benign `count=0` interpretation, and next-phase readiness. |

## Key Link Verification

| From | To | Via | Status |
| --- | --- | --- | --- |
| `scripts/verify_golden_prompts.py` | `/api/analyze` | Playwright `page.expect_response` around `#analyze-button` click | WIRED |
| `28-RESULTS.md` | `28-golden-prompt-results.json` | Locked prompt text and stability tables transcribed from JSON | WIRED |

## Behavioral Spot-Checks

| Check | Command | Result | Status |
| --- | --- | --- | --- |
| Script syntax | `python -c "import ast; ast.parse(...)"` | `syntax ok` | PASS |
| Script CLI contract | `python scripts\verify_golden_prompts.py --help` | Exposes `--scam-text`, `--scam-channel`, `--benign-text`, `--benign-channel`, `--port`, `--runs` | PASS |
| Golden JSON stability | Python JSON assertion over `28-golden-prompt-results.json` | `stable json ok` | PASS |
| Legitimate OTP correction | `python -m pytest tests\runtime\test_local_model.py` | 18 passed | PASS |
| Requirement status | `rg DIAG-01...GOLD-02 .planning\REQUIREMENTS.md` | All five Phase 28 requirements checked and marked Complete | PASS |

## Requirements Coverage

| Requirement | Status | Evidence |
| --- | --- | --- |
| DIAG-01 | SATISFIED | Doctor READY output and exit code 0 recorded in `28-RESULTS.md`. |
| DIAG-02 | SATISFIED | Four-class CLI table records correct labels, risk tiers, grounded-cue field, and next steps. |
| DIAG-03 | SATISFIED | Corrected first warm-latency value `26627.258 ms` recorded with method and date. |
| GOLD-01 | SATISFIED | One scam and one benign prompt locked as final demo script. |
| GOLD-02 | SATISFIED | Both locked prompts produced identical correct verdicts across five web-demo runs. |

## Anti-Patterns Found

| Pattern | Status | Notes |
| --- | --- | --- |
| Production runtime changes | REVIEWED | Runtime post-processing was deliberately changed in quick task `260702-l0q` to keep legitimate bank OTP notices benign while preserving link-based bank impersonation detection. |
| Silent verifier failures | CLEAR | `verify_golden_prompts.py` exits nonzero on unstable or wrong verdicts and writes diagnostics. |
| Orphaned demo process | CLEAR | The verifier owns and terminates its `vnphish demo` subprocess in `finally`; no lingering process was found after the interrupted session. |

## Human Verification Required

None for Phase 28. Phase 29 still requires the actual presentation laptop for environment parity and offline verification.

## Gaps Summary

No Phase 28 gaps found. Phase 28 is ready to close and Phase 29 can use the locked prompts and latency baseline.

---

_Verified: 2026-07-02T15:15:06+07:00_
_Verifier: Codex inline verifier_
