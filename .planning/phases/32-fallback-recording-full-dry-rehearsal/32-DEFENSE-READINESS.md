---
phase: 32-fallback-recording-full-dry-rehearsal
recorded: 2026-07-09T14:09:23Z
status: demo_ready_with_caveats
scope: live demo path primarily; slides sync pending separately
---

# Phase 32 Defense Readiness Snapshot

## Verdict

The project is good enough for the **demo portion** of the defense as of 2026-07-09.

This is not a blanket claim that every presentation artifact is finished. It means the local demo route most likely needed in the room is ready: the runtime is READY, the final Windows demo launcher works, and the two locked golden prompts produce the expected decisions through the browser UI.

## Evidence Refreshed

| Check | Command | Result |
|-------|---------|--------|
| Runtime doctor | `python -m src.runtime.cli doctor` | READY; GGUF backend, local-only, text-only; all checks PASS |
| Focused tests | `python -m pytest tests/runtime/test_demo.py tests/runtime/test_cli.py tests/runtime/test_ui_quirks_script.py -q` | 30 passed |
| Script syntax | `python -m py_compile scripts\\verify_phase32_fresh_process.py scripts\\verify_golden_prompts.py scripts\\verify_ui_quirks.py` | PASS |
| Final launcher dry-run | `python scripts\\verify_phase32_fresh_process.py --port 8765 --output .planning\\phases\\32-fallback-recording-full-dry-rehearsal\\artifacts\\32-fresh-process-dry-run.json` | `overall_pass: true` |

## Golden Prompt Results

| Prompt | Expected | Observed |
|--------|----------|----------|
| Vietcombank malicious-link scam | `high-risk`, `bank_impersonation` | PASS; latency about 22.1s |
| VPBank Smart OTP benign notice | `benign`, `benign` | PASS; latency about 21.0s |

## Defense Script Recommendation

1. Launch with `scripts\\START_DEMO_UI.bat`.
2. Paste the locked Vietcombank malicious-link scam prompt.
3. Narrate the suspicious cues while the model runs: fake bank sender, unknown access pressure, urgent lock action, unsafe link.
4. Paste the locked VPBank Smart OTP benign prompt.
5. Narrate why a legitimate OTP warning without unsafe link/action cues is benign.
6. Keep the wording honest: this is a local text-only demo; image/OCR/audio are out of scope.

## Caveats

- Slides are still pending sync per the operator and are not covered by this Phase 32 closeout.
- The fallback video and screenshot sequence were not supplied or verified in this session.
- The live-to-fallback pivot was not supplied or verified in this session.
- The dry-run is a fresh-process final-launcher proof, not a literal OS shutdown/reboot cold boot.

## Bottom Line

Demo-readiness is green. Presentation readiness is green-with-caveats until the slides are synced and, if time allows, a fallback recording or screenshot set is created.
