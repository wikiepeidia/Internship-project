---
status: complete
phase: 04-threat-detection-and-explainable-decisioning
source:
  - 04-01-SUMMARY.md
  - 04-02-SUMMARY.md
  - 04-03-SUMMARY.md
  - 04-04-SUMMARY.md
started: 2026-05-19T00:00:00Z
updated: 2026-05-25T00:00:00Z
---

# Phase 4 UAT

## Current Test

[testing complete]

## Tests

### 1. Default GGUF Analyze Flow

expected: On a ready local setup, running the existing analyze command without extra backend flags should use the shipped GGUF default and print a summary-first report with risk tier, mapped threat labels, grounded cues, and safe next steps, without raw JSON.
result: pass

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
passed: 4
blocked: 0
issues: 0
pending: 0
skipped: 0

## Gaps

none at the current Phase 4 UAT level
