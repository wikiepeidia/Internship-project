---
phase: 30-latency-diagnosis-targeted-fix
plan: 01
subsystem: runtime-verification
tags: [latency, cold-boot, playwright, gguf, demo-readiness]

provides:
  - "Dedicated Phase 30 cold-latency measurement harness"
  - "Evidence-run guard requiring explicit post-reboot confirmation"
  - "AC/High Performance and battery/Balanced human runbook"
  - "Unit coverage for measurement helper logic without loading the real GGUF model"

requirements-progress: [PERF-01 setup, PERF-03 setup]
duration: 22m
completed: 2026-07-05
---

# Phase 30 Plan 01 Summary: Cold-Latency Measurement Harness

Plan 30-01 is complete. It created the tooling and runbook needed for the real post-reboot evidence run, without applying any performance fix.

## Accomplishments

- Added `scripts/measure_cold_latency.py`, a script-owned `vnphish demo` + Playwright measurement harness.
- The harness times process launch through page readiness and first browser answer, while also recording browser request latency for each prompt.
- Evidence runs are guarded: `--run-purpose evidence` requires `--post-reboot-confirmed` and a real AC/battery condition.
- The harness loads the locked Phase 28 golden prompts directly from the machine-readable JSON artifact.
- Added `tests/runtime/test_latency_measurement.py` for prompt loading, evidence guard behavior, request timing extraction, output path construction, and prompt parsing.
- Added `.planning/phases/30-latency-diagnosis-targeted-fix/artifacts/30-cold-latency-runbook.md` with separate AC/High Performance and battery/Balanced reboot procedures.

## Verification

- `python -m pytest tests\runtime\test_latency_measurement.py -q` -> 6 passed.
- `python scripts\measure_cold_latency.py --help` -> CLI displayed successfully without loading the model.
- `python scripts\measure_cold_latency.py --condition ac-high-performance --run-purpose evidence` -> failed closed before launch because `--post-reboot-confirmed` was missing.
- `python -m pytest tests\runtime\test_demo.py tests\runtime\test_gguf_backend.py tests\runtime\test_latency_measurement.py -q` -> 17 passed.

## Deferred

PERF-01 and PERF-03 are not complete yet. They require the human to run the AC/High Performance and battery/Balanced post-reboot evidence commands from the runbook. No targeted fix is allowed until Plan 30-02 compares those two evidence artifacts.

## Files Created

- `scripts/measure_cold_latency.py`
- `tests/runtime/test_latency_measurement.py`
- `.planning/phases/30-latency-diagnosis-targeted-fix/artifacts/30-cold-latency-runbook.md`

---

*Phase: 30-Latency Diagnosis & Targeted Fix*
*Completed: 2026-07-05*
