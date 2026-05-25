---
phase: 06-local-demo-ui-for-non-technical-verification
plan: 01
subsystem: runtime
tags: [demo-ui, local-server, runtime-cli]
requires:
  - phase: 05-recall-priority-evaluation-and-release-gates
    provides: Existing release-gated runtime contract and saved release artifact workflow.
provides:
  - Local WSGI demo UI under src/runtime/demo.py
  - Separate demo HTML, CSS, and JS assets for the non-technical verification flow
  - Runtime CLI demo command and user-facing launch instructions
affects: [runtime-cli, docs, milestone-closeout]
tech-stack:
  added: []
  patterns: [local demo server, contract-backed zero-prompt flow, separated static assets]
key-files:
  created:
    - src/runtime/demo.py
    - src/runtime/demo_assets/index.html
    - src/runtime/demo_assets/demo.css
    - src/runtime/demo_assets/demo.js
    - tests/runtime/test_demo.py
    - .planning/phases/06-local-demo-ui-for-non-technical-verification/06-01-PLAN.md
  modified:
    - src/runtime/cli.py
    - tests/runtime/test_cli.py
    - readme.md
    - docs/user/USER_GUIDE.md
    - .planning/STATE.md
    - .planning/ROADMAP.md
    - .planning/REQUIREMENTS.md
key-decisions:
  - Reused the existing runtime service directly instead of introducing Flask, FastAPI, or a second backend surface.
  - Served separate HTML, CSS, and JS assets from a local WSGI app so the demo stays lightweight and offline-first.
  - Kept Phase 6 presentation work honest about the existing Phase 5 release artifacts without changing the saved `BLOCK` verdict.
requirements-completed:
  - UI-01
  - UI-02
duration: 12 min
completed: 2026-05-25
---

# Phase 06 Plan 01: Local demo UI summary

**Phase 6 shipped as one local demo slice over the existing runtime contract, giving non-technical users a browser UI for pasted-message analysis without adding a separate framework or widening scope beyond text-only local inference**

## Accomplishments

- Added `src/runtime/demo.py`, a minimal local WSGI app that serves the demo page and exposes `/api/analyze` on top of `RuntimeService.analyze_text()`.
- Added separate static assets under `src/runtime/demo_assets/` for the browser UI, including a responsive textarea-first layout, channel selector, and result rendering for risk tier, labels, grounded cues, and recommendations.
- Extended `src/runtime/cli.py` with `vnphish demo` and `python -m src.runtime.cli demo` so users can launch the local demo server from the existing runtime surface.
- Updated `readme.md` and `docs/user/USER_GUIDE.md` with demo-launch instructions.

## Verification

- `python -m pytest tests/runtime/test_demo.py tests/runtime/test_cli.py -q`
- `curl -s http://127.0.0.1:8765/ | head -n 20` after launching `python -m src.runtime.cli demo --host 127.0.0.1 --port 8765 --no-browser`

## Notes

- The demo remains text-only and local-first.
- It wraps the shipped runtime contract and does not alter the saved Phase 5 release artifact, which still truthfully records a `BLOCK` verdict for the held-out evaluation batch.