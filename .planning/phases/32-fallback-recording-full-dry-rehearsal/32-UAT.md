---
status: testing
phase: 32-fallback-recording-full-dry-rehearsal
source:
  - 32-VERIFICATION.md
started: 2026-07-09T13:56:00Z
updated: 2026-07-09T13:56:00Z
---

# Phase 32 UAT

## Current Test

number: 1
name: FB-01 fallback video saved in two local locations
expected: |
  A recording of the two locked golden prompts is saved in two separate local locations, and both files are playable without network access.
awaiting: user response

## Tests

### 1. FB-01 fallback video saved in two local locations
expected: A recording of the two locked golden prompts is saved in two separate local locations, and both files are playable without network access.
result: [pending]

### 2. FB-02 screenshot sequence saved as secondary fallback
expected: A static screenshot sequence exists for startup, scam result, benign result, and fallback-ready location, using the same two locked golden prompts.
result: [pending]

### 3. FB-03 live-to-fallback pivot rehearsed
expected: The presenter has rehearsed simulating a live-demo failure and switching smoothly to the fallback recording or screenshot sequence.
result: [pending]

### 4. FB-04 strict cold-boot acceptance
expected: Either the documented fresh-process substitute is explicitly accepted for defense readiness, or the operator performs a literal post-reboot dry rehearsal with scripts/START_DEMO_UI.bat before 2026-07-13.
result: [pending]

## Summary

total: 4
passed: 0
issues: 0
pending: 4
skipped: 0
blocked: 0

## Gaps

Automated software proof is green. Manual fallback artifacts and strict cold-boot acceptance are pending operator confirmation.
