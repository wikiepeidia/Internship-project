# VN Phishing Detection

Localized explainable AI pipeline for Vietnamese financial phishing detection.

## Phase 2 Local Runtime

Phase 2 adds a stdin-first local runtime for one-message text analysis. The normal path is local-only and does not persist raw text by default.

Text-only v1: paste extracted text manually. Images/OCR and audio are not accepted in Phase 2.

### Quick Start

Install dependencies:

```bash
python -m pip install -e .[dev]
```

Check local readiness:

```bash
vnphish doctor
python -m src.runtime.cli doctor
```

Run the stdin-first analyze flow:

```bash
vnphish analyze
python -m src.runtime.cli analyze
```

Paste one message, then end stdin in your shell.

Optional automation escape hatch:

```bash
vnphish analyze --text "VPBank cảnh báo account Internet Banking của bạn sẽ bị khóa trong 24h. Không chia sẻ mã OTP." --channel sms
python -m src.runtime.cli analyze --text "VPBank cảnh báo account Internet Banking của bạn sẽ bị khóa trong 24h. Không chia sẻ mã OTP." --channel sms
```

`--text` is for automation and testing. The default user path remains stdin-first.

## Phase 3 Local Model Profiles

Phase 3 adds two explicit local-only model profiles behind the same runtime command surface:

- `GGUF` laptop baseline for the selected 4B winner.
- `accelerated` local profile for stronger hardware.

Use `vnphish doctor` or `python -m src.runtime.cli doctor` after selecting the target profile in settings, and see `docs/user/LOCAL_MODELS.md` for the profile matrix, artifact expectations, and doctor guidance.

## Phase 6 Local Demo UI

Phase 6 adds a local browser demo for non-technical verification on top of the existing runtime contract.

Start the demo UI:

```bash
vnphish demo
python -m src.runtime.cli demo
```

Optional local server controls:

```bash
python -m src.runtime.cli demo --host 127.0.0.1 --port 8765 --no-browser
```

The demo remains text-only and local-first. Paste one suspicious message or short conversation, choose an optional channel hint, and the browser UI will render risk tier, threat labels, grounded cues, and safe next steps from the existing runtime output contract.

## Phase 1 Operator Flow

Phase 1 builds and retains the dataset artifacts needed for downstream model work.
The repo now exposes a single operator command path through `python -m src.data_pipeline.cli`.

## Prerequisites

- Python 3.13
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

If you want to finish generation first and postpone all LLM judging, add `--generate-only`. In that mode, completed batches append directly into `data/synthetic/generated.jsonl` and resume from the same checkpoint.

```bash
python -m src.data_pipeline.cli --seed-input data/raw/seeds-2026-04-24.jsonl --target-count 3000 --version-tag phase1-uat-gap --bulk-provider auto --max-parallel-batches 2 --resume --generate-only
```

## Smoke Check

Run a smaller preflight first when you only want to validate the command path and artifact wiring.

```bash
python -m src.data_pipeline.cli --seed-input data/raw/seeds-2026-04-24.jsonl --target-count 50 --version-tag phase1-uat-gap
```

## Safer Long Runs

For expensive retained runs, keep batches small, turn on incremental checkpoints, and only raise parallelism as high as your provider limits can tolerate.

```bash
python -m src.data_pipeline.cli --seed-input data/raw/seeds-2026-04-24.jsonl --target-count 3000 --version-tag phase1-uat-gap --bulk-provider auto --max-parallel-batches 2 --generate-only
```

If the process is interrupted after some batches finish, resume from the saved checkpoint instead of starting over.

```bash
python -m src.data_pipeline.cli --seed-input data/raw/seeds-2026-04-24.jsonl --target-count 3000 --version-tag phase1-uat-gap --bulk-provider auto --max-parallel-batches 2 --resume --generate-only
```

During the run, progress is printed to `stderr`, completed generation batches are checkpointed under `data/synthetic/`, and `data/synthetic/generated.jsonl` is appended incrementally so successful batches are not lost on interruption.

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

When `--generate-only` is active, only `data/synthetic/generated.jsonl` is produced. The judge, validated outputs, splits, and manifest are intentionally skipped.

The CLI prints a JSON summary to stdout with counts and output paths, including the final manifest path.

## Notes

- The retained Phase 1 dataset target band is `2000-3000` generated records.
- If the judged output is empty, the CLI exits non-zero instead of silently writing incomplete artifacts.
- If `--seed-input` points to a missing file, the CLI exits non-zero immediately.
- `--bulk-provider auto` prefers Gemini for bulk generation when `GEMINI_API_KEY` is configured, then falls back to OpenRouter or Claude.
- Dataset artifacts under `data/` are local-only and should not be committed; keep the tracked `.gitkeep` files so fresh clones preserve the directory layout.
