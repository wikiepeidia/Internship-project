---
phase: 28-baseline-readiness-zero-code-diagnostics
plan: 01
subsystem: testing
tags: [diagnostics, playwright, gguf, demo-readiness, golden-prompts]

requires:
  - phase: 27-page-count-and-final-polish
    provides: "Closed prior milestone and locked thesis/report baseline before v5.1 demo readiness work"
provides:
  - "Dev-machine vnphish doctor readiness proof"
  - "Four-class vnphish analyze evidence record with risk tier, labels, grounded cue field, and safe next steps"
  - "Reusable Playwright script that drives the real vnphish demo UI through /api/analyze"
  - "Locked scam and benign golden prompts, each stable across five real web-demo runs"
  - "First warm-latency baseline for Phase 30 comparison"
affects: [phase-29-environment-parity, phase-30-latency-diagnosis, phase-32-fallback-recording]

tech-stack:
  added: []
  patterns:
    - "Script-owned vnphish demo subprocess with bounded page.goto readiness polling"
    - "Fail-loud Playwright verification with machine-readable JSON result artifact"

key-files:
  created:
    - scripts/verify_golden_prompts.py
    - .planning/phases/28-baseline-readiness-zero-code-diagnostics/artifacts/28-RESULTS.md
    - .planning/phases/28-baseline-readiness-zero-code-diagnostics/artifacts/28-golden-prompt-results.json
  modified:
    - .planning/phases/28-baseline-readiness-zero-code-diagnostics/28-01-PLAN.md
    - .planning/phases/28-baseline-readiness-zero-code-diagnostics/28-RESEARCH.md

key-decisions:
  - "Original lock used the TPBank OTP-style bank-impersonation fallback and the obviously-safe conftest benign fixture."
  - "Post-closeout quick corrections relocked the final live-demo pair to a no-OTP malicious-link Vietcombank scam and a legitimate VPBank Smart OTP benign notice after fixing legitimate OTP false positives and case-insensitive evidence grounding."
  - "Recorded benign grounded cues as count=0 rather than fabricating suspicious evidence, matching the runtime contract where clearly benign messages may have top_cues: []."

patterns-established:
  - "Phase 28 browser checks use Playwright against the real web UI and the real /api/analyze endpoint, not direct service calls."
  - "Ignored diagnostic JSON artifacts that are plan outputs must be force-added when they are part of the evidence record."

requirements-completed: [DIAG-01, DIAG-02, DIAG-03, GOLD-01, GOLD-02]

duration: 1h 6m
completed: 2026-07-02
---

# Phase 28 Plan 01: Baseline Readiness and Golden Prompt Lock Summary

**Dev-machine diagnostics proved the local demo path is ready, with two stable golden prompts and a warm-latency baseline captured through the real web UI**

## Performance

- **Duration:** 1h 6m
- **Started:** 2026-07-02T13:49:00+07:00
- **Completed:** 2026-07-02T14:54:32+07:00
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments

- `vnphish doctor` exited 0 and reported `READY backend=gguf local_only=True text_only=True`.
- `vnphish analyze` passed the Phase 28 four-class smoke set: bank impersonation, Zalo social engineering, task scam, and benign.
- The three threat-class rows recorded non-empty grounded cues and safe next steps; the benign row recorded risk/label, `count=0` grounded cues, and a safe next step.
- `scripts/verify_golden_prompts.py` now drives `vnphish demo` through a script-owned server and the real browser `/api/analyze` flow.
- Original Phase 28 lock: the TPBank scam prompt locked 5/5 as `suspicious` + `bank_impersonation`; the benign fixture locked 5/5 as `benign` + `benign`.
- Post-closeout correction `260702-l0q`: legitimate bank OTP notices now render benign, enabling a bank-OTP benign golden prompt.
- Post-closeout correction `260702-ldt`: final live-demo lock is the no-OTP malicious-link Vietcombank scam (`high-risk` + `bank_impersonation`, 5/5) and VPBank Smart OTP benign notice (`benign`, 5/5).
- DIAG-03 warm-latency baseline recorded from the latest corrected first Playwright response timing: `22705.562 ms`.

## Task Commits

Each task was committed atomically:

1. **Task 1: DIAG-01 doctor confirmation + DIAG-02 four-class CLI correctness pass** - `a509b8b` (docs)
2. **Task 2: Playwright golden-prompt verification script** - `c3ac707` (feat)
3. **Task 3: Lock GOLD-01/GOLD-02 golden prompts and DIAG-03 latency** - `2807b54` (docs)

**Plan metadata:** captured in the close-out commit.

## Files Created/Modified

- `scripts/verify_golden_prompts.py` - Playwright verification script with lazy import, owned demo subprocess, readiness polling, fail-loud verdict checks, and JSON output.
- `.planning/phases/28-baseline-readiness-zero-code-diagnostics/artifacts/28-RESULTS.md` - Human-readable DIAG-01/02/03 and GOLD-01/02 evidence record.
- `.planning/phases/28-baseline-readiness-zero-code-diagnostics/artifacts/28-golden-prompt-results.json` - Machine-readable 5-run stability and latency artifact.
- `.planning/phases/28-baseline-readiness-zero-code-diagnostics/28-01-PLAN.md` - Corrected DIAG-02 wording for the benign grounded-cue case.
- `.planning/phases/28-baseline-readiness-zero-code-diagnostics/28-RESEARCH.md` - Marked Phase 28 open questions resolved during plan repair.

## Decisions Made

- The original TPBank OTP-style scam prompt was superseded because it was too ambiguous for the live-demo boundary: normal bank OTP notices should be benign, while the demo scam should include clearly malicious link/action cues.
- The final locked scam prompt is the Vietcombank fake-access alert with `http://vcb-secure-alert.net/...` and no OTP sentence; the final locked benign prompt is the VPBank Smart OTP notice.
- A benign output with no `Grounded cues:` section is acceptable when the result is clearly `Benign`; the artifact records this explicitly as `count=0` instead of treating missing suspicious evidence as a runtime failure.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Corrected DIAG-02 benign evidence interpretation**
- **Found during:** Task 1 (DIAG-02 CLI correctness pass)
- **Issue:** The repaired plan wording initially required non-empty grounded cues for all four rows, but the runtime contract and tests allow a clearly benign message to have `top_cues: []`.
- **Fix:** Updated `28-01-PLAN.md` and `28-RESULTS.md` to require non-empty grounded cues for the three threat-class rows, while recording the benign grounded-cue field as `count=0`.
- **Files modified:** `.planning/phases/28-baseline-readiness-zero-code-diagnostics/28-01-PLAN.md`, `.planning/phases/28-baseline-readiness-zero-code-diagnostics/artifacts/28-RESULTS.md`
- **Verification:** Task 1 acceptance checks passed after the correction; plan-level verification confirmed all required evidence is present.
- **Committed in:** close-out metadata commit

---

**Total deviations:** 1 auto-fixed (1 missing critical)
**Impact on plan:** The correction preserves DIAG-02 coverage without inventing suspicious evidence for a benign message. No runtime or production behavior changed.

## Issues Encountered

- The generated `28-golden-prompt-results.json` file is ignored by the artifact ignore rules, so it was force-added to preserve the required machine-readable evidence record.
- The browser verification run was interrupted at the conversation level by Wi-Fi loss, but the underlying script completed successfully and no lingering `vnphish demo` process remained.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Phase 28 evidence is ready for verification and closeout. Phase 29 can use the locked golden prompts and DIAG-03 warm-latency baseline when checking the actual presentation laptop and offline parity.

---
*Phase: 28-baseline-readiness-zero-code-diagnostics*
*Completed: 2026-07-02*
