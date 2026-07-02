---
quick_id: 260702-ldt
slug: remove-otp-sentence-from-phase-28-scam-g
status: planned
created: 2026-07-02T08:23:46.178Z
---

# Quick Task 260702-ldt: Remove OTP Sentence From Phase 28 Scam Golden Prompt

## Objective

Update the Phase 28 scam golden prompt so it no longer mentions OTP, because the fake-access/link-lock scenario does not need an OTP sentence.

## Tasks

1. Change the scam prompt default in `scripts/verify_golden_prompts.py`.
2. Confirm the no-OTP prompt still returns `high-risk` + `bank_impersonation`.
3. Preserve the legitimate OTP benign correction from quick task `260702-l0q`.
4. Re-run the real browser verifier for 5 scam and 5 benign submissions.
5. Update Phase 28 artifacts, project state, and this quick-task summary.

## Verification

- `vnphish analyze` on the no-OTP Vietcombank prompt returns `High risk` + `Bank impersonation`.
- `python scripts\verify_golden_prompts.py` exits 0.
- `28-golden-prompt-results.json` records `stable: true` for both prompts, five runs each.
- `python -m pytest tests\runtime` passes.
