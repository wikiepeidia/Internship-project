# Phase 31: UI Quirks, Edge Cases & Regression Re-check - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-06
**Phase:** 31-UI Quirks, Edge Cases & Regression Re-check
**Areas discussed:** Mystery console error, CLI entrypoint fix, Edge-case test method, Double-submit re-verification

---

## Mystery Console Error

| Option | Description | Selected |
|--------|-------------|----------|
| Reproduce + triage, fix only if real | Determine app-code vs browser noise; fix only if real | ✓ |
| Deep root-cause regardless | Trace to definitive source even if harmless | |
| Ignore it | Skip entirely, already judged non-blocking | |

**User's choice:** Reproduce + triage, fix only if real (Recommended)

---

## CLI Entrypoint Fix (UIQ-03)

| Option | Description | Selected |
|--------|-------------|----------|
| Both: launcher scripts + better --help text | Covers GUI-minded and terminal users | ✓ |
| Launcher scripts only | Simplest for double-click use | |
| Better --help text only | No new files | |

**User's choice:** Both: launcher scripts + better --help text (Recommended)

---

## Edge-Case Test Method (UIQ-01)

| Option | Description | Selected |
|--------|-------------|----------|
| Web demo, reuse Phase 28's script pattern | Tests the real committee-facing path | ✓ |
| CLI only | Faster but misses UI-layer issues | |
| Both CLI and web demo | More thorough, more time | |

**User's choice:** Web demo, reuse Phase 28's script pattern (Recommended)

---

## Double-Submit Re-verification (UIQ-02)

| Option | Description | Selected |
|--------|-------------|----------|
| Automated Playwright rapid-fire test | Scriptable, repeatable | ✓ |
| Manual click-spam test | Human-driven | |

**User's choice:** Automated Playwright rapid-fire test (Recommended)

---

## Claude's Discretion

- Launcher script naming/wording, exact --help text phrasing
- Whether edge-case and double-submit tests live in one script or two
- Task execution order within the phase

## Deferred Ideas

None — discussion stayed within phase scope.
