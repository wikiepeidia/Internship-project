---
phase: "32-fallback-recording-full-dry-rehearsal"
verified: "2026-07-09T14:11:00Z"
status: passed
score: "7/10 truths verified; 3 fallback-asset checks skipped as accepted risk"
overrides_applied: 0
accepted_risks:
  - test: "FB-01 fallback video saved in two local locations"
    disposition: "skipped"
    reason: "Operator scoped defense readiness mostly to the live demo on 2026-07-09; no recording files were supplied or verified."
  - test: "FB-02 screenshot sequence saved as secondary fallback"
    disposition: "skipped"
    reason: "Operator scoped defense readiness mostly to the live demo on 2026-07-09; no screenshot sequence was supplied or verified."
  - test: "FB-03 live-to-fallback pivot rehearsed"
    disposition: "skipped"
    reason: "Operator scoped defense readiness mostly to the live demo on 2026-07-09; no pivot rehearsal confirmation was supplied."
---

# Phase 32: Fallback Recording & Full Dry Rehearsal Verification Report

**Phase Goal:** A rehearsed, verified fallback exists so the defense can proceed even if the live demo fails, validated by one full cold-boot dry rehearsal on the actual presentation laptop.
**Verified:** 2026-07-09T14:11:00Z
**Status:** passed with accepted fallback risk
**Re-verification:** Yes - refreshed after the operator narrowed the defense-readiness question to the live demo path.

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | The fallback checklist exists and includes exact FB-01 recording instructions for the two locked golden prompts | VERIFIED | `.planning/phases/32-fallback-recording-full-dry-rehearsal/artifacts/32-fallback-operator-checklist.md` exists and contains the Vietcombank scam prompt plus VPBank Smart OTP benign prompt. |
| 2 | The screenshot sequence checklist exists for FB-02 and is clearly manual fallback evidence | VERIFIED | Same checklist has startup, scam verdict, benign verdict, and saved-location screenshot steps. |
| 3 | The live-to-fallback pivot checklist exists for FB-03 | VERIFIED | Same checklist includes the failure simulation and pivot narration steps. |
| 4 | The dry-run harness uses the final operator launcher path | VERIFIED | `scripts/verify_phase32_fresh_process.py` launches `scripts/START_DEMO_UI.bat` via `cmd.exe /c`; the refreshed JSON artifact records `launcher.path: scripts\\START_DEMO_UI.bat`. |
| 5 | The refreshed final-launcher dry-run returned the correct scam verdict | VERIFIED | `32-fresh-process-dry-run.json` records `golden_scam.passed: true`, `risk_tier: high-risk`, `threat_labels: [bank_impersonation]`, and latency about 22.1s. |
| 6 | The refreshed final-launcher dry-run returned the correct benign verdict | VERIFIED | `32-fresh-process-dry-run.json` records `golden_benign.passed: true`, `risk_tier: benign`, `threat_labels: [benign]`, and latency about 21.0s. |
| 7 | The dry-run evidence states the cold-boot limitation plainly | VERIFIED | `scope_notice` says this is a fresh-process substitute only and not literal cold-boot coverage for OS, driver, OneDrive sync, or Windows Defender first-run effects. |
| 8 | A recorded video has been saved in two local locations | SKIPPED / ACCEPTED RISK | No operator recording files were supplied. The user scoped this closeout to demo readiness mostly, so the missing fallback recording is documented as an accepted risk rather than a software gap. |
| 9 | A screenshot sequence has been saved as the secondary fallback | SKIPPED / ACCEPTED RISK | No operator screenshot sequence was supplied. The user scoped this closeout to demo readiness mostly, so the missing screenshot fallback is documented as an accepted risk rather than a software gap. |
| 10 | The live-to-fallback pivot and strict cold-boot acceptance have been completed | PARTIAL / SUBSTITUTE ACCEPTED | The fresh-process final-launcher run is accepted as the defense-readiness substitute. A literal OS power-cycle and human pivot rehearsal were not performed in this session. |

**Score:** 7/10 truths verified by files/automation; 3 fallback-asset checks skipped as accepted risk under the operator's demo-focused defense scope.

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `scripts/verify_phase32_fresh_process.py` | Fresh-process verifier for the final launcher-backed demo route | VERIFIED | Exists, compiles, exposes `--help`, loads locked prompt constants, writes structured JSON, and terminates the launcher process tree. |
| `32-fallback-operator-checklist.md` | Manual FB-01/FB-02/FB-03 checklist with exact prompt texts | VERIFIED | Exists with recording, screenshot, and pivot sections. |
| `32-fresh-process-dry-run.json` | Automated evidence for the fresh-process FB-04 substitute | VERIFIED | Refreshed 2026-07-09T14:07:55Z; `overall_pass: true`, final launcher path used, no page errors. |
| `32-UAT.md` | Human/accepted-risk UAT disposition | VERIFIED | Complete with 1 pass, 3 accepted-risk skips, 0 issues. |
| `32-DEFENSE-READINESS.md` | Demo readiness decision snapshot | VERIFIED | Summarizes the final demo-focused verdict and remaining caveats for defense. |

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Doctor readiness | `python -m src.runtime.cli doctor` | `READY backend=gguf local_only=True text_only=True`; all 12 checks PASS | PASS |
| Focused runtime/UI helper tests | `python -m pytest tests/runtime/test_demo.py tests/runtime/test_cli.py tests/runtime/test_ui_quirks_script.py -q` | 30 passed | PASS |
| Script syntax | `python -m py_compile scripts\\verify_phase32_fresh_process.py scripts\\verify_golden_prompts.py scripts\\verify_ui_quirks.py` | Exit 0 | PASS |
| Fresh-process final-launcher dry-run | `python scripts\\verify_phase32_fresh_process.py --port 8765 --output .planning\\phases\\32-fallback-recording-full-dry-rehearsal\\artifacts\\32-fresh-process-dry-run.json` | Exit 0; JSON `overall_pass: true` | PASS |
| JSON assertion | Python assertion over dry-run JSON for launcher path, scam pass, benign pass, and scope notice | Exit 0 | PASS |

## Requirements Coverage

| Requirement | Description | Status | Evidence |
|-------------|-------------|--------|----------|
| FB-01 | Recorded video of the two locked golden prompts saved in two local locations | SKIPPED / ACCEPTED RISK | Checklist exists and prompt text is locked. Actual recording files were not supplied or verified; skipped under demo-focused defense scope. |
| FB-02 | Screenshot sequence of the same golden-prompt run saved as secondary fallback | SKIPPED / ACCEPTED RISK | Checklist exists. Actual screenshot files were not supplied or verified; skipped under demo-focused defense scope. |
| FB-03 | Live-to-fallback pivot rehearsed at least once | SKIPPED / ACCEPTED RISK | Pivot script exists. Rehearsal completion was not supplied or verified; skipped under demo-focused defense scope. |
| FB-04 | Full cold-boot dry rehearsal before 2026-07-13 | SATISFIED BY ACCEPTED SUBSTITUTE | Fresh-process final-launcher dry-run passed and was accepted for defense readiness. Literal post-reboot cold boot remains unclaimed. |

## Defense Readiness Verdict

For the **live demo path**, the project is good enough for the defense as of 2026-07-09:

- `doctor` reports READY on the GGUF/local/text-only runtime.
- Focused runtime, CLI, demo, and UI-quirks helper tests are green.
- The final Windows launcher path starts the real browser UI.
- The two locked golden prompts return the expected decisions through the UI: Vietcombank scam -> `high-risk`/`bank_impersonation`; VPBank Smart OTP -> `benign`.
- Observed per-prompt latency in the refreshed run is about 21-22 seconds, consistent with the known no-fix latency decision and acceptable for a short, scripted live demo if narrated honestly.

Defense caveats:

- Slides are explicitly still pending sync per the operator and are outside this Phase 32 verification.
- Fallback video, screenshot sequence, and pivot rehearsal were not supplied or verified in this session.
- The accepted dry-run is fresh-process launcher coverage, not literal OS power-cycle coverage.

## Gaps Summary

No software gaps were found in the demo path. The remaining gaps are presentation/process caveats, documented as accepted risk: slide sync pending, no verified fallback media, no verified pivot rehearsal, and no literal OS power-cycle dry run.

---

_Verified: 2026-07-09T14:11:00Z_
_Verifier: Codex (inline GSD verification, no subagent available)_
