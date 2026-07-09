---
phase: "32-fallback-recording-full-dry-rehearsal"
verified: "2026-07-09T13:56:00Z"
status: human_needed
score: 6/10 must-haves verified
overrides_applied: 0
human_verification:
  - test: "FB-01 fallback video saved in two local locations"
    expected: "A recording of the two locked golden prompts is saved in two separate local locations, and both files are playable without network access."
    why_human: "The agent can provide the checklist and prompts, but cannot confirm the operator-created recording files or storage locations."
  - test: "FB-02 screenshot sequence saved as secondary fallback"
    expected: "A static screenshot sequence exists for startup, scam result, benign result, and fallback-ready location, using the same two locked golden prompts."
    why_human: "The agent did not capture or inspect the operator's final saved screenshot files."
  - test: "FB-03 live-to-fallback pivot rehearsed"
    expected: "The presenter has rehearsed simulating a live-demo failure and switching smoothly to the fallback recording or screenshot sequence."
    why_human: "This is a human presentation maneuver, not a property of the software process."
  - test: "FB-04 strict cold-boot acceptance"
    expected: "Either the documented fresh-process substitute is explicitly accepted for defense readiness, or the operator performs a literal post-reboot dry rehearsal with scripts/START_DEMO_UI.bat before 2026-07-13."
    why_human: "The agent launched a fresh process through the final .bat file, but did not and cannot truthfully claim a physical OS power-cycle cold boot."
---

# Phase 32: Fallback Recording & Full Dry Rehearsal Verification Report

**Phase Goal:** A rehearsed, verified fallback exists so the defense can proceed even if the live demo fails, validated by one full cold-boot dry rehearsal on the actual presentation laptop.
**Verified:** 2026-07-09T13:56:00Z
**Status:** human_needed
**Re-verification:** No - initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | The fallback checklist exists and includes exact FB-01 recording instructions for the two locked golden prompts | VERIFIED | `.planning/phases/32-fallback-recording-full-dry-rehearsal/artifacts/32-fallback-operator-checklist.md` exists and contains the Vietcombank scam prompt plus VPBank Smart OTP benign prompt. |
| 2 | The screenshot sequence checklist exists for FB-02 and is clearly manual fallback evidence | VERIFIED | Same checklist has startup, scam verdict, benign verdict, and saved-location screenshot steps. |
| 3 | The live-to-fallback pivot checklist exists for FB-03 | VERIFIED | Same checklist includes the failure simulation and pivot narration steps. |
| 4 | The dry-run harness uses the final operator launcher path | VERIFIED | `scripts/verify_phase32_fresh_process.py` launches `scripts/START_DEMO_UI.bat` via `cmd.exe /c`; the JSON artifact records `launcher.path: scripts\\START_DEMO_UI.bat`. |
| 5 | The fresh-process dry-run returned the correct scam verdict | VERIFIED | `32-fresh-process-dry-run.json` records `golden_scam.passed: true`, `risk_tier: high-risk`, and `threat_labels: [bank_impersonation]`. |
| 6 | The fresh-process dry-run returned the correct benign verdict | VERIFIED | `32-fresh-process-dry-run.json` records `golden_benign.passed: true`, `risk_tier: benign`, and `threat_labels: [benign]`. |
| 7 | The dry-run evidence states the cold-boot limitation plainly | VERIFIED | `scope_notice` says this is a fresh-process substitute only and not literal cold-boot coverage for OS, driver, OneDrive sync, or Windows Defender first-run effects. |
| 8 | A recorded video has been saved in two local locations | HUMAN NEEDED | Checklist exists, but no operator recording files were supplied or verified. |
| 9 | A screenshot sequence has been saved as the secondary fallback | HUMAN NEEDED | Checklist exists, but no operator screenshot sequence was supplied or verified. |
| 10 | The live-to-fallback pivot and strict cold-boot acceptance have been completed | HUMAN NEEDED | Pivot rehearsal is a human presentation action; strict physical cold boot was intentionally substituted with a fresh-process run and needs operator acceptance or a post-reboot run. |

**Score:** 6/10 truths fully verified by automation/files; 4 truths require human confirmation.

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `scripts/verify_phase32_fresh_process.py` | Fresh-process verifier for the final launcher-backed demo route | VERIFIED | Exists, compiles, exposes `--help`, loads locked prompt constants, writes structured JSON, and terminates the launcher process tree. |
| `32-fallback-operator-checklist.md` | Manual FB-01/FB-02/FB-03 checklist with exact prompt texts | VERIFIED | Exists with recording, screenshot, and pivot sections. |
| `32-fresh-process-dry-run.json` | Automated evidence for the fresh-process FB-04 substitute | VERIFIED | Exists and is tracked in git as `fd5221d`; `overall_pass: true`. |
| `32-01-SUMMARY.md` | Plan summary with deterministic coverage routing | VERIFIED | Exists and routes manual fallback deliverables to human UAT instead of auto-passing them. |

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Script syntax | `python -m py_compile scripts\\verify_phase32_fresh_process.py` | Exit 0 | PASS |
| Help path | `python scripts\\verify_phase32_fresh_process.py --help` | Exit 0 | PASS |
| Checklist contains prompts and caveat | PowerShell content assertion for `VIETCOMBANK`, `VPBank Smart OTP`, and `not a literal cold boot` | Exit 0 | PASS |
| Fresh-process dry-run | `python scripts\\verify_phase32_fresh_process.py --port 8765 --output .planning\\phases\\32-fallback-recording-full-dry-rehearsal\\artifacts\\32-fresh-process-dry-run.json` | Exit 0; JSON `overall_pass: true` | PASS |
| JSON assertion | Python assertion over dry-run JSON for launcher path, scam pass, benign pass, and scope notice | Exit 0 | PASS |

## Requirements Coverage

| Requirement | Description | Status | Evidence |
|-------------|-------------|--------|----------|
| FB-01 | Recorded video of the two locked golden prompts saved in two local locations | HUMAN NEEDED | Checklist exists and prompt text is locked, but actual recording files are not verified. |
| FB-02 | Screenshot sequence of the same golden-prompt run saved as secondary fallback | HUMAN NEEDED | Checklist exists, but actual screenshot files are not verified. |
| FB-03 | Live-to-fallback pivot rehearsed at least once | HUMAN NEEDED | Pivot script exists, but rehearsal completion must be confirmed by the presenter. |
| FB-04 | Full cold-boot dry rehearsal before 2026-07-13 | PARTIAL / SUBSTITUTE | Fresh-process final-launcher dry-run passed. Literal post-reboot cold boot was not performed and must be accepted by the operator as a documented substitution or run manually. |

## Human Verification Required

### 1. FB-01 fallback video saved in two local locations

**Expected:** A recording of the two locked golden prompts is saved in two separate local locations, and both files are playable without network access.
**Why human:** The agent can provide the checklist and prompts, but cannot confirm the operator-created recording files or storage locations.

### 2. FB-02 screenshot sequence saved as secondary fallback

**Expected:** A static screenshot sequence exists for startup, scam result, benign result, and fallback-ready location, using the same two locked golden prompts.
**Why human:** The agent did not capture or inspect the operator's final saved screenshot files.

### 3. FB-03 live-to-fallback pivot rehearsed

**Expected:** The presenter has rehearsed simulating a live-demo failure and switching smoothly to the fallback recording or screenshot sequence.
**Why human:** This is a human presentation maneuver, not a property of the software process.

### 4. FB-04 strict cold-boot acceptance

**Expected:** Either the documented fresh-process substitute is explicitly accepted for defense readiness, or the operator performs a literal post-reboot dry rehearsal with `scripts/START_DEMO_UI.bat` before 2026-07-13.
**Why human:** The agent launched a fresh process through the final `.bat` file, but did not and cannot truthfully claim a physical OS power-cycle cold boot.

## Gaps Summary

No software gaps were found in the automated Phase 32 proof. The final launcher-backed demo route served successfully and both locked golden prompts produced the expected verdicts through the browser UI.

The phase is not marked complete because the core fallback assets and presentation maneuver are operator-owned evidence. `32-UAT.md` contains those checks for `$gsd-verify-work 32`.

---

_Verified: 2026-07-09T13:56:00Z_
_Verifier: Codex (inline GSD verification, no subagent available)_
