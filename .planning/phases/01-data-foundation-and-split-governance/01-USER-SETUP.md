# Phase 01 User Setup

Status: Incomplete

## Required Services

### Anthropic

- Why: complex synthetic generation for the retained Phase 1 dataset flow
- Required env var: `ANTHROPIC_API_KEY`
- Source: Anthropic Console -> API keys

### Gemini

- Why: bulk generation and quality judging in the retained Phase 1 dataset flow
- Required env var: `GEMINI_API_KEY`
- Source: Google AI Studio -> API keys

### OpenRouter

- Optional env var: `OPENROUTER_API_KEY`
- Use only as fallback for bulk generation; it is not required for the main retained-seed path.

## Verification Commands

```bash
python -m src.data_pipeline.cli --help
python -m src.data_pipeline.cli --seed-input data/raw/seeds-2026-04-24.jsonl --target-count 50 --version-tag phase1-uat-gap
```

## Expected Outputs

- `data/synthetic/generated.jsonl`
- `data/processed/validated.jsonl`
- `data/processed/quality-stats.json`
- `data/splits/train.jsonl`
- `data/splits/val.jsonl`
- `data/splits/test.jsonl`
- `data/manifests/manifest-phase1-uat-gap.json`
