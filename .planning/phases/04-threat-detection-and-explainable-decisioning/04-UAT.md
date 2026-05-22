---
status: testing
phase: 04-threat-detection-and-explainable-decisioning
source:
  - 04-01-SUMMARY.md
  - 04-02-SUMMARY.md
  - 04-03-SUMMARY.md
  - 04-04-SUMMARY.md
started: 2026-05-19T00:00:00Z
updated: 2026-05-22T00:00:00Z
---

# Phase 4 UAT

## Current Test

number: complete
name: Phase 4 UAT session complete pending GGUF runtime follow-up
expected: |
  All currently runnable Phase 4 checks have been executed in this shell. Remaining gap is the default GGUF path, which still depends on `llama-cpp-python` being available.
awaiting: user response

## Tests

### 1. Default GGUF Analyze Flow

expected: On a ready local setup, running the existing analyze command without extra backend flags should use the shipped GGUF default and print a summary-first report with risk tier, mapped threat labels, grounded cues, and safe next steps, without raw JSON.
result: blocked
blocked_by: other
reason: "After migrating the repo to Python 3.13 and reinstalling base dependencies, the default `analyze` flow now reaches the runtime doctor gate but stops at `NOT READY backend=gguf` with `backend-ready: FAIL - backend=gguf ready=False`. The app correctly stays fail-closed, but this shell still lacks a ready GGUF runtime for the default-profile smoke."

### 2. Fail-Closed Doctor Guidance

expected: If the promoted GGUF default is not ready, analyze should stop with doctor guidance instead of silently falling back to heuristic output.
result: pass

### 3. Explicit Accelerated Override

expected: An explicit accelerated profile selection should still work and should return the same Phase 4 field set through the same analyze command surface.
result: pass

### 4. Safe User Guidance

expected: Risky model-backed results should not tell the user to click, reply, share OTP or identity data, install an app from the message, or transfer money; they should present safe next steps instead.
result: pass

## Summary

total: 4
passed: 3
blocked: 1
issues: 0
pending: 0
skipped: 0

## Gaps

- Live model-backed UAT remains environment-constrained only for the default GGUF path: the GGUF artifact is present but `llama-cpp-python` is still missing in this Python 3.13 environment.
