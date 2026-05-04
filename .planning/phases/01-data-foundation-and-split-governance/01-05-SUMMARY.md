---
phase: 01-data-foundation-and-split-governance
plan: 05
subsystem: data-pipeline
tags: [cli, dataset, anthropic, gemini, manifests]
requires:
  - phase: 01-02
    provides: seed scraper and normalized raw seed records
  - phase: 01-03
    provides: synthetic generation and judge library surfaces
  - phase: 01-04
    provides: split builder and manifest versioning helpers
provides:
  - repo-level Phase 1 CLI orchestration
  - persisted validated dataset and quality stats paths
  - Phase 1 operator runbook and quickstart
affects: [phase-01-gap-closure, phase-02, docs]
tech-stack:
  added: []
  patterns: [thin CLI over existing pipeline services, retained-seed fast path]
key-files:
  created: [src/data_pipeline/cli.py, tests/data_pipeline/test_phase1_cli.py]
  modified: [readme.md, START_HERE.md]
key-decisions:
  - "Used a thin argparse CLI over the existing scraper, generator, judge, and builder rather than reopening completed Phase 1 internals."
  - "Persisted validated records and quality stats in the CLI so downstream split building has a concrete `data/processed/validated.jsonl` input."
patterns-established:
  - "Operator flow pattern: retained-seed preflight with `--seed-input` before the full retained run."
  - "Pipeline output pattern: stdout emits JSON summary with artifact paths and counts."
requirements-completed: [DATA-01, DATA-02, DATA-03]
duration: 2 min
completed: 2026-05-04
---

# Phase 01 Plan 05: Summary

Phase 1 operator CLI and runbook for scrape, generate, judge, and build dataset execution

## Performance

- Duration: 2 min
- Started: 2026-05-04T16:11:58+07:00
- Completed: 2026-05-04T16:13:32+07:00
- Tasks: 2
- Files modified: 4

## Accomplishments

- Added a repo-level Phase 1 CLI that can start from retained raw seeds or scrape fresh seeds.
- Persisted generated, validated, split, and manifest artifact paths through a single command surface.
- Replaced the empty/template repo guidance with a Phase 1 runbook and quickstart.

## Task Commits

Each task was committed atomically:

1. Task 1: Add a Phase 1 CLI that bridges scrape, generate, judge, and build - 687b64c
2. Task 2: Document the clean Phase 1 operator flow in repo guidance - 7a05f99

## Files Created/Modified

- src/data_pipeline/cli.py - Orchestrates seed loading, generation, judging, validated persistence, and split building.
- tests/data_pipeline/test_phase1_cli.py - Covers retained-seed, fresh-scrape, and failure-path CLI behavior.
- readme.md - Documents the retained-seed path, smoke preflight, and fresh scrape path.
- START_HERE.md - Replaced the template onboarding text with a project-specific Phase 1 quickstart.

## Decisions Made

- Used `python -m src.data_pipeline.cli` as the explicit Phase 1 operator command path.
- Kept the retained-seed path first-class so Phase 1 gap closure does not reopen the scraper unnecessarily.
- Wrote `data/processed/quality-stats.json` alongside `validated.jsonl` so judged output has retained evidence.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- The initial CLI smoke tests used the retained full-run target in fake success paths; the tests were corrected to use a reduced-count preflight and a dedicated out-of-band generation check.

## User Setup Required

External services require manual configuration. See [01-USER-SETUP.md](./01-USER-SETUP.md) for the required API keys and verification steps.

## Next Phase Readiness

- Plan 01-05 is complete and verified.
- Plan 01-06 can now use the retained raw seed artifact to materialize the missing synthetic, validated, split, and manifest outputs.

---
Phase: 01-data-foundation-and-split-governance
Completed: 2026-05-04
