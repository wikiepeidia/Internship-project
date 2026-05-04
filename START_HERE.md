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

If budget matters more than judged artifacts right now, use `--generate-only`. That skips all per-record LLM judging and appends finished batches directly into `data/synthetic/generated.jsonl`.

```bash
python -m src.data_pipeline.cli --seed-input data/raw/seeds-2026-04-24.jsonl --target-count 3000 --version-tag phase1-uat-gap --bulk-provider auto --max-parallel-batches 2 --resume --generate-only
```

## 4. Smoke Check First

Use this smaller run to validate the CLI and output wiring before the full retained-count pass.

```bash
python -m src.data_pipeline.cli --seed-input data/raw/seeds-2026-04-24.jsonl --target-count 50 --version-tag phase1-uat-gap
```

## 5. Long Claude Run With Checkpoints

Use small concurrent batches so you can see progress and keep completed generation work if the run is interrupted.

```bash
python -m src.data_pipeline.cli --seed-input data/raw/seeds-2026-04-24.jsonl --target-count 3000 --version-tag phase1-uat-gap --bulk-provider auto --max-parallel-batches 2 --generate-only
```

If you stop the run or the process exits after some completed batches, resume it with:

```bash
python -m src.data_pipeline.cli --seed-input data/raw/seeds-2026-04-24.jsonl --target-count 3000 --version-tag phase1-uat-gap --bulk-provider auto --max-parallel-batches 2 --resume --generate-only
```

## 6. Fresh Scrape Path

Only use this when you actually want a new seed batch.

```bash
python -m src.data_pipeline.cli --target-count 2500 --version-tag phase1-fresh
```

## 7. Outputs to Check

After a successful run, confirm these files exist:

- `data/synthetic/generated.jsonl`
- `data/processed/validated.jsonl`
- `data/processed/quality-stats.json`
- `data/splits/train.jsonl`
- `data/splits/val.jsonl`
- `data/splits/test.jsonl`
- `data/manifests/manifest-<version-tag>.json`

The CLI prints a JSON summary with counts and artifact paths so you can verify the run without opening the code.
Progress messages are written to `stderr`, and interrupted long runs keep incremental generation checkpoint files under `data/synthetic/` until the final run completes successfully.
When `--generate-only` is active, `data/synthetic/generated.jsonl` is the only required output and it grows incrementally during the run.
