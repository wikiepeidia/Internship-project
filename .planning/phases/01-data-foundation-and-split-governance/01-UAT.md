---
status: diagnosed
phase: 01-data-foundation-and-split-governance
source:
  - 01-01-SUMMARY.md
  - 01-02-SUMMARY.md
  - 01-03-SUMMARY.md
  - 01-04-SUMMARY.md
started: 2026-04-21T00:00:00Z
updated: 2026-05-04T00:00:00Z
---

# Phase 01 UAT

## Current Test

[testing complete]

## Tests

### 1. Phase 1 pipeline code surface is implemented and validated

expected: The repo should provide implemented and passing modules for seed scraping, synthetic generation, quality judging, split governance, deduplication, and manifest versioning.
result: pass

### 2. Raw seed dataset artifact exists in the current workspace

expected: The workspace should contain a normalized raw seed JSONL artifact under `data/raw` with a first collected batch in the 100-300 record range.
result: pass

### 3. Synthetic dataset artifact exists in the target band

expected: The workspace should contain a curated synthetic JSONL dataset under `data/synthetic` with 2,000-3,000 reviewed records ready for downstream curation.
result: issue
reported: "Only raw seeds are present; there is no generated synthetic dataset artifact in data/synthetic, and the 2,000-3,000 JSONL target cannot be evidenced from this workspace."
severity: major

### 4. Versioned processed and split artifacts exist for reproducible evaluation

expected: The workspace should contain processed validated records, governed train/validation/test split JSONL files, and a manifest proving versioned lineage and leakage-controlled splits.
result: issue
reported: "There is no validated dataset output in data/processed, no split JSONL files in data/splits, and no manifest in data/manifests."
severity: major

### 5. An operator can reproduce Phase 1 outputs from the repo with an explicit command flow

expected: The repo should expose a clear Phase 1 run path, such as documented commands or a packaged entrypoint that ties scraping, generation, judging, and dataset building together from a clean checkout.
result: issue
reported: "The repo has library classes for generation and building, but no documented or packaged end-to-end command flow. readme.md is empty, START_HERE.md is still the template, and no CLI or project script entrypoint is present."
severity: major

## Summary

total: 5
passed: 2
issues: 3
pending: 0
skipped: 0
blocked: 0

## Gaps

- truth: "The workspace contains a curated synthetic JSONL dataset in the 2,000-3,000 target band for Phase 1 review."
  status: failed
  reason: "Workspace inspection shows only `data/raw/seeds-2026-04-24.jsonl` plus `.gitkeep` placeholders. No synthetic dataset artifact exists under `data/synthetic`, so the 2,000-3,000 target band cannot be evidenced from this checkout."
  severity: major
  test: 3
  root_cause: "The synthetic generation and judging code exists, but the workspace does not contain the persisted synthetic output that `TieredGenerator.save_generated()` would write to `data/synthetic/generated.jsonl`. Phase 1 was marked complete based on library and test coverage rather than a retained generated dataset artifact."
  artifacts:
  - path: "data/synthetic/.gitkeep"
    issue: "No generated synthetic JSONL artifact is present"
  - path: "src/data_pipeline/generation/generator.py"
    issue: "Generation code can save `data/synthetic/generated.jsonl`, but no saved output exists in the workspace"
  missing:
  - "Run the generation pipeline against the available seed set and persist the output to `data/synthetic/generated.jsonl`"
  - "Confirm the retained synthetic record count lands in the 2,000-3,000 target band"
  - "Retain evidence of the judged/curated synthetic batch instead of relying only on unit tests"
  debug_session: ""

- truth: "The workspace contains validated records, governed split JSONL files, and a manifest proving reproducible Phase 1 lineage."
  status: failed
  reason: "`data/processed`, `data/splits`, and `data/manifests` still contain only `.gitkeep`, so the reproducible dataset lineage promised by Phase 1 is not materialized in the workspace."
  severity: major
  test: 4
  root_cause: "`DatasetBuilder.build_splits()` expects `data/processed/validated.jsonl`, but no phase step in the current workspace persists the post-judge accepted records to that path. Without that validated input artifact, the split writer and manifest builder were never run to produce train/val/test files and a manifest."
  artifacts:
  - path: "data/processed/.gitkeep"
    issue: "No `validated.jsonl` artifact is present"
  - path: "data/splits/.gitkeep"
    issue: "No governed split JSONL files are present"
  - path: "data/manifests/.gitkeep"
    issue: "No version manifest is present"
  - path: "src/data_pipeline/generation/quality_judge.py"
    issue: "Judge code returns passed records and stats, but does not persist `data/processed/validated.jsonl`"
  - path: "src/data_pipeline/versioning/build.py"
    issue: "Builder defaults to `data/processed/validated.jsonl`, which does not exist in the workspace"
  missing:
  - "Persist the post-judge accepted records to `data/processed/validated.jsonl`"
  - "Run the dataset builder to emit `train.jsonl`, `val.jsonl`, and `test.jsonl` under `data/splits`"
  - "Emit and retain a version manifest under `data/manifests` for the produced split set"
  debug_session: ""

- truth: "A clean operator can reproduce the full Phase 1 pipeline from repository guidance and an explicit command flow."
  status: failed
  reason: "The repo contains importable classes for scraping, generation, judging, and dataset building, but no project-specific runbook or packaged command path to execute the full pipeline from a clean checkout."
  severity: major
  test: 5
  root_cause: "Phase 1 delivered library surfaces but did not surface them as an operator-facing workflow. `readme.md` is empty, `START_HERE.md` is still the template, and `pyproject.toml` does not define a script entrypoint, so the roadmap promise of a reproducible command flow is not met from repository guidance alone."
  artifacts:
  - path: "readme.md"
    issue: "README is empty and does not document Phase 1 execution"
  - path: "START_HERE.md"
    issue: "Still template content; no project-specific Phase 1 run sequence"
  - path: "pyproject.toml"
    issue: "No `[project.scripts]` or other packaged entrypoint exposes a Phase 1 pipeline command"
  missing:
  - "Add a documented Phase 1 run sequence or CLI entrypoint that covers scrape -> generate -> judge -> build"
  - "Document required API keys and exact commands to produce synthetic, processed, split, and manifest artifacts from a clean checkout"
  - "Verify the documented flow on a clean workspace state so another machine can reproduce the same outputs"
  debug_session: ""
