---
phase: 29-environment-parity-offline-verification
plan: 03
subsystem: config
tags: [windows-env, setx, portability, doctor, evidence]

requires:
  - phase: 29-environment-parity-offline-verification
    provides: "ENV-01 doctor sanity baseline and local runtime readiness"
provides:
  - "Permanent Windows user-level MODEL_ARTIFACT_ROOT environment variable"
  - "Permanent Windows user-level MODEL_REGISTRY_PATH environment variable"
  - "Registry proof and fresh-terminal cross-directory doctor proof for ENV-04"
affects: [phase-29-offline-verification, phase-30-latency-diagnosis, phase-32-dry-rehearsal]

tech-stack:
  added: []
  patterns:
    - "Use user-level setx for persistent model path portability on the presentation laptop"
    - "Verify setx writes via registry query and fresh-terminal runtime check"

key-files:
  created:
    - .planning/phases/29-environment-parity-offline-verification/artifacts/29-env04-evidence.md
  modified:
    - .planning/phases/29-environment-parity-offline-verification/artifacts/29-env04-evidence.md

key-decisions:
  - "Used user-scope setx only; no machine-wide /m flag and no elevation."
  - "Did not read or modify .env/.env because it contains unrelated secrets and OS env vars now supersede only the two model-path keys."
  - "Accepted the current doctor formatter's lack of explicit model-path detail because fresh-terminal env-var output plus READY from C:\\ proves the runtime path setup."

patterns-established:
  - "For setx changes, registry proof verifies persistence and human fresh-terminal proof verifies runtime visibility."

requirements-completed: [ENV-04]

coverage:
  - id: D1
    description: "MODEL_ARTIFACT_ROOT and MODEL_REGISTRY_PATH are persisted in HKCU\\Environment with the expected off-repo values."
    requirement: ENV-04
    verification:
      - kind: manual_procedural
        ref: "reg query HKCU\\Environment /v MODEL_ARTIFACT_ROOT and /v MODEL_REGISTRY_PATH"
        status: pass
    human_judgment: false
  - id: D2
    description: "A brand-new terminal can see both OS env vars and run vnphish doctor from C:\\ with READY status."
    requirement: ENV-04
    verification:
      - kind: manual_procedural
        ref: "human fresh-terminal PowerShell check pasted into 29-env04-evidence.md"
        status: pass
    human_judgment: false

duration: 12 min
completed: 2026-07-05
status: complete
---

# Phase 29 Plan 03: Permanent Model Environment Variables Summary

**Windows user-level model path variables now survive new terminals and support `vnphish doctor` from outside the repo root**

## Performance

- **Duration:** 12 min
- **Started:** 2026-07-05T20:56:00+07:00
- **Completed:** 2026-07-05T21:08:11+07:00
- **Tasks:** 3
- **Files modified:** 1

## Accomplishments

- Set `MODEL_ARTIFACT_ROOT` to `D:\PROJEct\AI MODELS` using user-level `setx`.
- Set `MODEL_REGISTRY_PATH` to `D:\PROJEct\AI MODELS\manifests\model-registry.json` using user-level `setx`.
- Verified both persistent values through `reg query "HKCU\Environment"`.
- Recorded the user's fresh-terminal PowerShell output showing both environment variables are visible after `setx`.
- Recorded a fresh-terminal `vnphish doctor` run from `C:\` reporting `READY backend=gguf local_only=True text_only=True`.
- Removed the temporary `.continue-here.md` checkpoint marker after the human verification was satisfied.

## Task Commits

Each task was committed atomically:

1. **Task 1: Set permanent OS-level env vars and prove registry write** - `26bc604` (docs)
2. **Task 2/3: Record fresh-terminal runtime proof** - `3843f9d` (docs)

**Plan metadata:** captured in the close-out commit.

## Files Created/Modified

- `.planning/phases/29-environment-parity-offline-verification/artifacts/29-env04-evidence.md` - registry proof plus fresh-terminal runtime proof.
- `.planning/phases/29-environment-parity-offline-verification/.continue-here.md` - temporary checkpoint file, removed after verification.

## Decisions Made

- Used exactly the locked D-03 values and avoided reading `.env/.env`.
- Treated the current doctor output as sufficient runtime proof when paired with the fresh-terminal environment-variable checks, because the formatter reports readiness but not the resolved model path detail.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Evidence Format] Doctor no longer prints resolved model path detail**
- **Found during:** Task 2 (fresh-terminal verification)
- **Issue:** The plan expected `backend-ready` to print an explicit `D:\PROJEct\AI MODELS\...` path, but current output only prints `backend=gguf ready=True`.
- **Fix:** Recorded the exact doctor output transparently and paired it with the fresh-terminal env-var output as the path proof.
- **Files modified:** `.planning/phases/29-environment-parity-offline-verification/artifacts/29-env04-evidence.md`
- **Verification:** Evidence file contains both expected env-var values and READY doctor output from `C:\`.
- **Committed in:** `3843f9d`

---

**Total deviations:** 1 auto-fixed (1 evidence-format mismatch)
**Impact on plan:** ENV-04 remains satisfied; no code or runtime behavior changed.

## Issues Encountered

None.

## User Setup Required

None - the required user verification was completed during execution.

## Verification

- `reg query "HKCU\Environment" /v MODEL_ARTIFACT_ROOT` -> `D:\PROJEct\AI MODELS`.
- `reg query "HKCU\Environment" /v MODEL_REGISTRY_PATH` -> `D:\PROJEct\AI MODELS\manifests\model-registry.json`.
- Fresh terminal from user: `$env:MODEL_ARTIFACT_ROOT` and `$env:MODEL_REGISTRY_PATH` showed both expected values.
- Fresh terminal from `C:\`: `vnphish doctor` reported `READY backend=gguf local_only=True text_only=True`.

## Next Phase Readiness

Phase 29 can proceed to the ENV-02 offline network-disconnect runbook. The demo no longer depends on CWD-relative `.env/.env` for model path resolution in newly opened terminals.

---
*Phase: 29-environment-parity-offline-verification*
*Completed: 2026-07-05*
