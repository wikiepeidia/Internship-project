---
phase: 29-environment-parity-offline-verification
plan: 04
subsystem: verification
tags: [offline, devtools, demo, human-checkpoint, evidence]

requires:
  - phase: 29-environment-parity-offline-verification
    provides: "Self-hosted demo fonts from 29-01 and runtime/env readiness from 29-02/29-03"
provides:
  - "Pre-filled offline verification runbook with locked Phase 28 prompts"
  - "Human-executed offline verdict evidence for scam and benign golden prompts"
  - "DevTools Network screenshot evidence and post-test doctor READY confirmation"
affects: [phase-30-latency-diagnosis, phase-31-ui-regression, phase-32-dry-rehearsal]

tech-stack:
  added: []
  patterns:
    - "Use a human checkpoint for physical network-disconnect verification that would sever the agent session"
    - "Record browser-extension DevTools noise separately from app/backend network dependencies"

key-files:
  created:
    - .planning/phases/29-environment-parity-offline-verification/artifacts/29-env02-runbook.md
    - .planning/phases/29-environment-parity-offline-verification/artifacts/29-env02-devtools-screenshot.png
    - .planning/phases/29-environment-parity-offline-verification/artifacts/29-env02-offline-results.md
  modified:
    - src/runtime/analyzers/local_model.py
    - tests/runtime/test_local_model.py
    - .planning/phases/29-environment-parity-offline-verification/artifacts/29-env02-offline-results.md

key-decisions:
  - "Accepted the offline run as ENV-02 passing because both locked prompts rendered the expected verdicts with network disabled and no app/backend external requests were observed."
  - "Recorded DevTools browser-extension stylesheet entries as evidence noise rather than demo network dependencies."
  - "Improved the benign OTP fallback recommendation copy after the offline run exposed awkward Vietnamese text."

patterns-established:
  - "For defense-facing offline claims, combine human network-disconnect evidence, screenshot proof, and post-test doctor confirmation."
  - "When DevTools includes extension resources, preserve the deviation and distinguish it from application traffic."

requirements-completed: [ENV-02]

coverage:
  - id: D1
    description: "The locked Vietcombank scam prompt rendered high-risk with bank_impersonation while offline."
    requirement: ENV-02
    verification:
      - kind: manual_procedural
        ref: ".planning/phases/29-environment-parity-offline-verification/artifacts/29-env02-offline-results.md"
        status: pass
    human_judgment: true
  - id: D2
    description: "The locked VPBank Smart OTP benign prompt rendered benign with benign as the threat label while offline."
    requirement: ENV-02
    verification:
      - kind: manual_procedural
        ref: ".planning/phases/29-environment-parity-offline-verification/artifacts/29-env02-offline-results.md"
        status: pass
    human_judgment: true
  - id: D3
    description: "DevTools screenshot shows no demo app/backend external network dependency; Google Fonts requests are absent."
    requirement: ENV-02
    verification:
      - kind: screenshot
        ref: ".planning/phases/29-environment-parity-offline-verification/artifacts/29-env02-devtools-screenshot.png"
        status: pass_with_noise
      - kind: other
        ref: "python -m src.runtime.cli doctor"
        status: pass
    human_judgment: true

duration: 19 min
completed: 2026-07-05
status: complete
---

# Phase 29 Plan 04: Offline Demo Verification Summary

**The real browser demo was verified offline with the two locked golden prompts, screenshot evidence, and post-test runtime readiness**

## Performance

- **Duration:** 19 min active agent time, plus human offline verification time.
- **Started:** 2026-07-05T21:13:00+07:00
- **Completed:** 2026-07-05T21:32:30+07:00
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments

- Created a pre-filled human runbook with the exact locked Phase 28 scam and benign prompts copied from JSON.
- Confirmed both locked prompt records were stable and the runbook contained all 9 required offline-test steps.
- Captured human-reported offline verdicts: scam -> `high-risk` + `bank_impersonation`; benign -> `benign` + `benign`.
- Saved DevTools Network screenshot evidence at `artifacts/29-env02-devtools-screenshot.png`.
- Re-ran `python -m src.runtime.cli doctor` after network restoration; it still reported `READY backend=gguf local_only=True text_only=True`.
- Improved the benign OTP fallback recommendation copy and locked that behavior with a focused unit assertion.

## Task Commits

Each task was committed atomically:

1. **Task 1: Pre-flight and human runbook** - `14cfe37` (docs)
2. **Task 2: Human checkpoint handoff/evidence capture** - `0a87ea8`, `3f60234` (wip docs)
3. **Task 3: Final offline evidence record** - `6c34e4d` (docs)

Additional follow-up fix:

- **Benign OTP recommendation copy polish** - `f3c1772` (fix)

**Plan metadata:** captured in the close-out commit.

## Files Created/Modified

- `.planning/phases/29-environment-parity-offline-verification/artifacts/29-env02-runbook.md` - human offline verification runbook with exact locked prompts.
- `.planning/phases/29-environment-parity-offline-verification/artifacts/29-env02-devtools-screenshot.png` - DevTools Network screenshot evidence.
- `.planning/phases/29-environment-parity-offline-verification/artifacts/29-env02-offline-results.md` - final ENV-02 evidence record.
- `src/runtime/analyzers/local_model.py` - improved benign OTP fallback recommendation copy.
- `tests/runtime/test_local_model.py` - regression assertion for the improved benign recommendation.

## Decisions Made

- Preserved the human checkpoint boundary because physically disabling Wi-Fi/Ethernet would sever the agent's own network session.
- Accepted extension/content-script stylesheet entries in DevTools as browser noise, not application network dependencies, because the screenshot shows no app/backend non-loopback host and no Google Fonts request.
- Treated `ERROR SOURCE_LANG_VI` as a non-network console deviation; source search found no matching local runtime/frontend key.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - User-Facing Explanation Quality] Benign OTP recommendation copy was awkward**
- **Found during:** Task 2 (human offline verification)
- **Issue:** The benign OTP result rendered the correct `benign` verdict but the fallback recommendation was awkward ASCII Vietnamese.
- **Fix:** Replaced `DEFAULT_BENIGN_RECOMMENDATION` with natural Vietnamese copy and added a focused regression assertion.
- **Files modified:** `src/runtime/analyzers/local_model.py`, `tests/runtime/test_local_model.py`
- **Verification:** `python -m pytest tests\runtime\test_local_model.py -q` -> 19 passed; real CLI benign golden prompt returned `Benign` with the improved next step.
- **Committed in:** `f3c1772`

**2. [Rule 1 - Evidence Format] DevTools screenshot contains browser-extension stylesheet noise**
- **Found during:** Task 3 (screenshot evidence review)
- **Issue:** Screenshot shows `about:client`-initiated CSS entries from browser extension/content-script resources, despite no app/backend external request.
- **Fix:** Recorded the noise transparently in `29-env02-offline-results.md` and scoped the ENV-02 judgment to app/backend traffic and Google Fonts absence.
- **Files modified:** `.planning/phases/29-environment-parity-offline-verification/artifacts/29-env02-offline-results.md`
- **Verification:** Screenshot artifact present; evidence record documents the exact entries and the absence of app/backend external traffic.
- **Committed in:** `6c34e4d`

---

**Total deviations:** 2 auto-fixed/documented (1 copy quality, 1 evidence-format noise).
**Impact on plan:** ENV-02 remains satisfied; the deviations improve defense-facing evidence clarity without changing runtime risk labels or backend behavior.

## Issues Encountered

- Browser console showed `ERROR SOURCE_LANG_VI`; no matching key or source path was found in local runtime/frontend source. Recorded as non-network console noise for Phase 31 follow-up if it reappears.

## User Setup Required

None - the required human offline verification was completed during execution.

## Verification

- `python -m src.runtime.cli doctor` -> exit 0, `READY backend=gguf local_only=True text_only=True`.
- `python -m pytest tests\runtime\test_local_model.py -q` -> 19 passed.
- Evidence artifact contains `high-risk`, `bank_impersonation`, `benign`, screenshot reference, and post-test doctor `READY`.
- Screenshot artifact exists at `.planning/phases/29-environment-parity-offline-verification/artifacts/29-env02-devtools-screenshot.png`.

## Next Phase Readiness

Phase 30 can begin latency diagnosis against a demo environment now proven to be self-hosted, OS-env portable, exact-pinned, and functional offline. Phase 31 should keep an eye on the `SOURCE_LANG_VI` console warning if browser-console polish is in scope.

---
*Phase: 29-environment-parity-offline-verification*
*Completed: 2026-07-05*

