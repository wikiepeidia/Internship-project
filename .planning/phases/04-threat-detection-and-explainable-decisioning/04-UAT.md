---
status: testing
phase: 04-threat-detection-and-explainable-decisioning
source:
  - 04-01-SUMMARY.md
  - 04-02-SUMMARY.md
  - 04-03-SUMMARY.md
  - 04-04-SUMMARY.md
started: 2026-05-19T00:00:00Z
updated: 2026-05-19T00:00:00Z
---

## Current Test

number: 1
name: Default GGUF Analyze Flow
expected: |
  On a ready local setup, running the existing analyze command without extra backend flags should use the shipped GGUF default and print a summary-first report that includes:

- a risk tier line
- mapped threat labels
- grounded cues from the message text
- safe next steps
  It should stay on the existing analyze command surface and should not dump raw JSON.
awaiting: user response

## Tests

### 1. Default GGUF Analyze Flow

expected: On a ready local setup, running the existing analyze command without extra backend flags should use the shipped GGUF default and print a summary-first report with risk tier, mapped threat labels, grounded cues, and safe next steps, without raw JSON.
result: pending

### 2. Fail-Closed Doctor Guidance

expected: If the promoted GGUF default is not ready, analyze should stop with doctor guidance instead of silently falling back to heuristic output.
result: pending

### 3. Explicit Accelerated Override

expected: An explicit accelerated profile selection should still work and should return the same Phase 4 field set through the same analyze command surface.
result: pending

### 4. Safe User Guidance

expected: Risky model-backed results should not tell the user to click, reply, share OTP or identity data, install an app from the message, or transfer money; they should present safe next steps instead.
result: pending

## Summary

total: 4
passed: 0
issues: 0
pending: 4
skipped: 0

## Gaps

none yet
