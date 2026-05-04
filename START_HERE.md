# START HERE — Phase 1 Dataset Quickstart

Use this file when you want to reproduce the retained Phase 1 dataset artifacts from a clean checkout.

## 1. Install Dependencies

```bash
python -m pip install -e .[dev]
```

## 2. Set Environment Variables

Required:

- `ANTHROPIC_API_KEY`
- `GEMINI_API_KEY`

Optional:

- `OPENROUTER_API_KEY`

## 3. Fast Path: Reuse the Retained Raw Seeds

This path starts from the existing raw seed artifact and does not reopen scraping.

```bash
python -m src.data_pipeline.cli --seed-input data/raw/seeds-2026-04-24.jsonl --target-count 2500 --version-tag phase1-uat-gap
```

## 4. Smoke Check First

Use this smaller run to validate the CLI and output wiring before the full retained-count pass.

```bash
python -m src.data_pipeline.cli --seed-input data/raw/seeds-2026-04-24.jsonl --target-count 50 --version-tag phase1-uat-gap
```

## 5. Fresh Scrape Path

Only use this when you actually want a new seed batch.

```bash
python -m src.data_pipeline.cli --target-count 2500 --version-tag phase1-fresh
```

## 6. Outputs to Check

After a successful run, confirm these files exist:

- `data/synthetic/generated.jsonl`
- `data/processed/validated.jsonl`
- `data/processed/quality-stats.json`
- `data/splits/train.jsonl`
- `data/splits/val.jsonl`
- `data/splits/test.jsonl`
- `data/manifests/manifest-<version-tag>.json`

The CLI prints a JSON summary with counts and artifact paths so you can verify the run without opening the code.
- [ ] `PRD.md` — executive summary, personas, numbered FR-XXX requirements, NFRs, out of scope, open questions
- [ ] `docs/technical/ARCHITECTURE.md` — tech stack table and infrastructure environments filled in
- [ ] `docs/technical/DESIGN_SYSTEM.md` — copied from template (placeholder tables OK until design work begins)
- [ ] `docs/technical/DECISIONS.md` — ADR-001 filled in with real tech stack rationale
- [ ] `docs/content/CONTENT_STRATEGY.md` — brand voice and personas filled in (or marked `[N/A]` if internal tool with no public-facing pages)

**Backlog**
- [ ] `TODO.md` contains only real tasks — no placeholder `#001`–`#008` entries remain
- [ ] Every TODO item has a corresponding `.tasks/NNN-*.md` file
- [ ] Every `.tasks/NNN-*.md` file has: description, acceptance criteria, `prd_refs`, `agent`, `created_at`
- [ ] `blocks` / `blocked_by` dependencies are set correctly where tasks depend on each other
- [ ] "Up Next" contains the first tasks that are ready to start, ordered by dependency
- [ ] Task #000 remains in Completed

**Sign-off**
- [ ] Summary presented to user (Phase 4)
- [ ] User confirmed satisfaction
- [ ] This file deleted
