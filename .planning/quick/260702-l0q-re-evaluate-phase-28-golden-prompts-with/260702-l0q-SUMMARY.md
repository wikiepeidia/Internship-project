---
quick_id: 260702-l0q
status: complete
completed: 2026-07-02
commit: 2597078
---

# Quick Task 260702-l0q Summary

## Goal

Re-evaluate the Phase 28 golden prompts after review showed the original OTP-style scam was too ambiguous: legitimate bank OTP notices should be benign, while the live-demo scam should include clear malicious link/action pressure.

## What Changed

- Added a narrow runtime correction for legitimate bank OTP notices in `src/runtime/analyzers/local_model.py`.
- Added regression tests for:
  - VPBank Smart OTP benign notice.
  - Techcombank transaction OTP benign notice.
  - Vietcombank fake-access alert with malicious link remaining `bank_impersonation`.
- Updated `scripts/verify_golden_prompts.py` defaults to the corrected final prompt pair.
- Re-ran the real Playwright browser verifier through `vnphish demo` for 5 runs each.
- Updated Phase 28 evidence artifacts, verification notes, `PROJECT.md`, and `STATE.md`.

## Result

Before the fix:

- Techcombank normal OTP notice returned `Suspicious / Bank impersonation`.
- VPBank Smart OTP notice returned `Suspicious / Bank impersonation`.

After the fix:

- Techcombank normal OTP notice returns `Benign`.
- VPBank Smart OTP notice returns `Benign`.
- Vietcombank malicious-link prompt returns `High risk / Bank impersonation`.

Corrected golden prompt stability:

| Prompt | Verdict | Runs | Stable |
| --- | --- | --- | --- |
| Vietcombank malicious-link scam | `high-risk` + `bank_impersonation` | 5/5 | true |
| VPBank Smart OTP benign notice | `benign` + `benign` | 5/5 | true |

Corrected DIAG-03 warm-latency baseline: `26627.258 ms`.

## Verification

- `python -m pytest tests\runtime\test_local_model.py` -> 18 passed.
- `vnphish analyze` on VPBank Smart OTP -> `Risk tier: Benign`, `Threat labels: Benign`.
- `vnphish analyze` on Techcombank OTP -> `Risk tier: Benign`, `Threat labels: Benign`.
- `vnphish analyze` on Vietcombank malicious-link scam -> `Risk tier: High risk`, `Threat labels: Bank impersonation`.
- `python scripts\verify_golden_prompts.py` -> exit 0; both golden prompts stable 5/5.

## Files

- `src/runtime/analyzers/local_model.py`
- `tests/runtime/test_local_model.py`
- `scripts/verify_golden_prompts.py`
- `.planning/phases/28-baseline-readiness-zero-code-diagnostics/artifacts/28-golden-prompt-results.json`
- `.planning/phases/28-baseline-readiness-zero-code-diagnostics/artifacts/28-RESULTS.md`
- `.planning/phases/28-baseline-readiness-zero-code-diagnostics/28-01-SUMMARY.md`
- `.planning/phases/28-baseline-readiness-zero-code-diagnostics/28-VERIFICATION.md`
- `.planning/PROJECT.md`
- `.planning/STATE.md`
