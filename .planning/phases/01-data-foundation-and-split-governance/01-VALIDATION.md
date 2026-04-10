---
phase: 1
slug: data-foundation-and-split-governance
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-10
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | tests/conftest.py (Wave 0 installs) |
| **Quick run command** | `python -m pytest tests/ -x -q` |
| **Full suite command** | `python -m pytest tests/ -v --tb=short` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/ -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -v --tb=short`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | DATA-01 | integration | `python -m pytest tests/test_scraper.py -v` | ❌ W0 | ⬜ pending |
| 01-02-01 | 02 | 2 | DATA-02 | integration | `python -m pytest tests/test_synthetic.py -v` | ❌ W0 | ⬜ pending |
| 01-03-01 | 03 | 3 | DATA-03 | unit | `python -m pytest tests/test_splits.py -v` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/conftest.py` — shared fixtures (sample JSONL records, temp directories)
- [ ] `tests/test_scraper.py` — stubs for DATA-01 scraper validation
- [ ] `tests/test_synthetic.py` — stubs for DATA-02 synthetic generation validation
- [ ] `tests/test_splits.py` — stubs for DATA-03 split governance validation
- [ ] `pytest` — if not in project dependencies

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| NCSC site accessibility | DATA-01 | Requires live network access to khonggianmang.vn | Visit site, verify page loads, check DOM selectors match scraper config |
| Synthetic sample realism | DATA-02 | Requires human linguistic judgment for Vietnamese code-switch quality | Review 5-10% random sample for natural code-switching and teencode patterns |
| Cross-split semantic similarity | DATA-03 | Threshold tuning requires human judgment on edge cases | Review flagged near-duplicates at 0.85 cosine threshold, adjust if needed |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
