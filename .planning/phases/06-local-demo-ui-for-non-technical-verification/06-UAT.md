---
status: complete
phase: 06-local-demo-ui-for-non-technical-verification
source:
  - 06-01-SUMMARY.md
started: 2026-05-25T07:26:39Z
updated: 2026-05-25T07:47:04Z
---

# Phase 6 UAT

## Current Test

[testing complete]

## Tests

### 1. Local Demo Launch

expected: Running vnphish demo or python -m src.runtime.cli demo should start a local browser demo address without requiring a second framework or extra backend-specific flags.
result: pass

### 2. Zero-Prompt Text Intake

expected: The demo page should show a textarea-first message input, a channel selector, analyze action, and explicit text-only local boundary messaging so a non-technical user can start without CLI syntax.
result: pass

### 3. Browser Result Rendering

expected: Submitting a suspicious message in the demo should render the shipped runtime contract in the browser: summary, risk tier, threat labels, grounded cues, and safe next steps.
result: pass

### 4. Local Boundary Error Handling

expected: If the user submits too-short text or a non-text placeholder, the demo should show a local error message and next steps instead of crashing or widening beyond the text-only boundary.
result: pass

## Summary

total: 4
passed: 4
blocked: 0
issues: 0
pending: 0
skipped: 0

## Gaps

none at the current Phase 6 UAT level
