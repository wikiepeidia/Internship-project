---
quick_id: 260702-ldt
status: complete
completed: 2026-07-02
commit: 4350e63
---

# Quick Task 260702-ldt Summary

## Goal

Remove the OTP sentence from the Phase 28 scam golden prompt and confirm the shorter prompt still works as the malicious-link demo case.

## What Changed

- Updated `scripts/verify_golden_prompts.py` so the Vietcombank scam default ends after `(mien phi).`
- Made evidence grounding case-insensitive so model evidence like `tai khoan cua ban...` can ground against `Tai khoan cua ban...`.
- Extended the safety floor so bank-branded URL/link-lock scams stay non-benign even without OTP.
- Updated Phase 28 results, verification, summary, project state, and quick-task history.

## Result

Final scam prompt:

```text
【VIETCOMBANK】 Tai khoan cua ban vua bi truy cap tu thiet bi la luc 03:47 SA. Neu ko phai ban, bam vao link de khoa ngay: http://vcb-secure-alert.net/lock?id=9182736 hoac goi 1800.9999 (mien phi).
```

Browser verifier result:

| Prompt | Verdict | Runs | Stable |
| --- | --- | --- | --- |
| Vietcombank no-OTP malicious-link scam | `high-risk` + `bank_impersonation` | 5/5 | true |
| VPBank Smart OTP benign notice | `benign` + `benign` | 5/5 | true |

Updated DIAG-03 warm-latency baseline: `22705.562 ms`.

## Verification

- `vnphish analyze` on the no-OTP Vietcombank scam -> `Risk tier: High risk`, `Threat labels: Bank impersonation`.
- `python scripts\verify_golden_prompts.py` completed during the interrupted run and wrote stable JSON.
- `python -c ... no-otp golden json ok` passed.
- `python scripts\verify_golden_prompts.py --help` passed.
- `python -m pytest tests\runtime` -> 78 passed.

## Files

- `scripts/verify_golden_prompts.py`
- `src/runtime/analyzers/local_model.py`
- `tests/runtime/test_local_model.py`
- `.planning/phases/28-baseline-readiness-zero-code-diagnostics/artifacts/28-golden-prompt-results.json`
- `.planning/phases/28-baseline-readiness-zero-code-diagnostics/artifacts/28-RESULTS.md`
- `.planning/phases/28-baseline-readiness-zero-code-diagnostics/28-01-SUMMARY.md`
- `.planning/phases/28-baseline-readiness-zero-code-diagnostics/28-VERIFICATION.md`
- `.planning/PROJECT.md`
- `.planning/STATE.md`
