# Phase 32 Research: Fallback Recording & Fresh-Process Dry Run

## Scope

Phase 32 is a rehearsal and fallback-readiness phase. The app contract, model behavior, locked golden prompts, UI assets, and CLI commands are frozen from Phases 28-31. The only new automated work should make the final run easy to prove and repeat without changing runtime behavior.

## Relevant Existing Patterns

- `scripts/verify_golden_prompts.py` already defines the locked scam and benign prompt texts and verifies the expected verdicts through the real web UI.
- `scripts/verify_ui_quirks.py` provides the strongest recent subprocess + Playwright + readiness polling + JSON artifact pattern.
- `scripts/START_DEMO_UI.bat` is the final user-facing launcher and must be exercised for the fresh-process dry-run. It invokes `python -m src.runtime.cli demo`, which defaults to `127.0.0.1:8765` and opens a browser tab.
- Phase 30 records the honest defense narration figure as about 27 seconds to first answer, not the older warm-process figure.

## Implementation Approach

Use a new lightweight script, `scripts/verify_phase32_fresh_process.py`, to:

1. Stop any existing listener on the target demo port.
2. Launch `scripts/START_DEMO_UI.bat` through `cmd.exe`, so the real final launcher path is exercised.
3. Poll `http://127.0.0.1:8765/` for readiness.
4. Drive a separate Playwright Chromium session against the same local server.
5. Submit the two locked golden prompts once each and assert the expected verdicts.
6. Write a JSON artifact under the Phase 32 artifacts directory.
7. Terminate the launcher process tree cleanly.

This is a fresh-process proxy, not a literal cold boot. It does not exercise OS startup, driver reinitialization, OneDrive sync catch-up after power-on, or Windows Defender first-run scanning.

## Manual Evidence Boundary

The user explicitly chose manual recording, manual screenshot sequence, and manual live-to-fallback pivot rehearsal. The agent should provide a checklist with exact prompts and evidence fields, but should not mark FB-01, FB-02, or FB-03 complete without user-supplied evidence.

## Pitfalls

- Do not bypass `START_DEMO_UI.bat` with `--no-browser` for the Phase 32 fresh-process dry-run; the launcher path is the point of the test.
- Do not overwrite Phase 28 or Phase 31 golden-prompt artifacts.
- Do not claim literal FB-04 cold-boot coverage from the automated fresh-process run.
- Do not change `src/runtime/demo.py`, `src/runtime/service.py`, `src/runtime/demo_assets/*`, model thresholds, or the locked prompt text.

