<!-- markdownlint-disable MD003 MD022 MD036 MD041 MD060 -->

---
phase: 02
slug: offline-text-ingestion-and-privacy-baseline
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-05-04
---

# Phase 02 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `python -m pytest tests/runtime/test_cli.py tests/runtime/test_service.py -q` |
| **Full suite command** | `python -m pytest -q` |
| **Estimated runtime** | ~20 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/runtime/test_contracts.py tests/runtime/test_service.py -q`
- **After every plan wave:** Run `python -m pytest tests/runtime -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 20 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | ING-01 | — | Analyze accepts one pasted text message via stdin or explicit test input, rejects empty payloads, and keeps the interface text-only | integration | `python -m pytest tests/runtime/test_cli.py -q` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 1 | ING-02 | — | Runtime normalizes once, preserves Vietnamese and mixed-language content, and quotes exact normalized spans | unit + integration | `python -m pytest tests/runtime/test_service.py tests/data_pipeline/test_normalizer.py -q` | ❌ W0 | ⬜ pending |
| 02-02-01 | 02 | 2 | RUN-01 | — | Default path stays local, writes no raw text by default, and fails closed with setup guidance | unit + integration | `python -m pytest tests/runtime/test_privacy.py tests/runtime/test_doctor.py -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/runtime/test_contracts.py` — request/result model validation and risk-tier compatibility checks
- [ ] `tests/runtime/test_service.py` — normalize-first orchestration, cue ranking, and exact-span quoting
- [ ] `tests/runtime/test_cli.py` — stdin-first analyze flow, `--text` escape hatch, and text-only rejection messaging
- [ ] `tests/runtime/test_privacy.py` — no raw-text persistence and no network use in the default path
- [ ] `tests/runtime/test_doctor.py` — readiness checks and setup guidance output

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Stdin-first real paste flow feels usable from a shell | ING-01 | Automated tests can validate stdin behavior, but a human should confirm the normal copy-paste path is not awkward | Run `python -m src.runtime.cli analyze`, paste one sample SMS/Zalo-style message, end input, and confirm a provisional result prints without echoing full raw text in an error path |
| Doctor output gives actionable local remediation steps | RUN-01 | Human review is needed to judge whether the setup guidance is concrete enough to follow | Run `python -m src.runtime.cli doctor` in both ready and intentionally misconfigured states and verify the guidance names the missing dependency or configuration clearly |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 20s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

<!-- markdownlint-enable MD003 MD022 MD036 MD041 MD060 -->