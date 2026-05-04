# VN Phishing Detection

Localized explainable AI pipeline for Vietnamese financial phishing detection.

## Phase 1 Operator Flow

Phase 1 builds and retains the dataset artifacts needed for downstream model work.
The repo now exposes a single operator command path through `python -m src.data_pipeline.cli`.

## Prerequisites

- Python 3.12
- Dependencies installed with `python -m pip install -e .[dev]`
- Environment variables:
	- `ANTHROPIC_API_KEY` for complex synthetic generation
	- `GEMINI_API_KEY` for bulk generation and quality judging
	- `OPENROUTER_API_KEY` optional fallback for bulk generation

## Fast Path: Use the Retained Raw Seeds

Use the existing retained seed artifact when you want to reproduce Phase 1 outputs without reopening scraping.

```bash
python -m src.data_pipeline.cli --seed-input data/raw/seeds-2026-04-24.jsonl --target-count 2500 --version-tag phase1-uat-gap
```

## Smoke Check

Run a smaller preflight first when you only want to validate the command path and artifact wiring.

```bash
python -m src.data_pipeline.cli --seed-input data/raw/seeds-2026-04-24.jsonl --target-count 50 --version-tag phase1-uat-gap
```

## Fresh Scrape Path

If you need a new seed batch, omit `--seed-input` and the CLI will scrape first, then continue through generation, judging, and split building.

```bash
python -m src.data_pipeline.cli --target-count 2500 --version-tag phase1-fresh
```

## Expected Outputs

Successful runs retain these artifacts in the workspace:

- `data/synthetic/generated.jsonl`
- `data/processed/validated.jsonl`
- `data/processed/quality-stats.json`
- `data/splits/train.jsonl`
- `data/splits/val.jsonl`
- `data/splits/test.jsonl`
- `data/manifests/manifest-<version-tag>.json`

The CLI prints a JSON summary to stdout with counts and output paths, including the final manifest path.

## Notes

- The retained Phase 1 dataset target band is `2000-3000` generated records.
- If the judged output is empty, the CLI exits non-zero instead of silently writing incomplete artifacts.
- If `--seed-input` points to a missing file, the CLI exits non-zero immediately.
