
Completed: *Make the overnight generation run viable* (2/3)

Phase 1 can now run in generation-only mode, resume from checkpoints, and append directly into `data/synthetic/generated.jsonl` while it is still running. I also fixed the parallel worker bug that caused `Anthropic API key is required for complex generation` during resumed runs with `--max-parallel-batches > 1`.

Important reality for tonight:

1. `--bulk-provider gemini` only affects bulk batches.
2. Complex batches still use Claude.
3. That means your overnight machine still needs both `ANTHROPIC_API_KEY` and `GEMINI_API_KEY` configured.
4. Judging is intentionally off for tonight. Use `--generate-only`.
5. Keep `--max-parallel-batches 2` for a safer overnight run.

What you should run on the other PC:

1. From the repo root, first check that the app can see both keys:

```bash
python -c "from src.config.settings import get_settings; s=get_settings(); print({'anthropic': bool(s.anthropic_api_key), 'gemini': bool(s.gemini_api_key), 'openrouter': bool(s.openrouter_api_key)})"
```

Expected result:

```text
{'anthropic': True, 'gemini': True, 'openrouter': False}
```

1. Optional cheap smoke check before the overnight run:

```bash
python -m src.data_pipeline.cli --seed-input data/raw/seeds-2026-04-24.jsonl --target-count 50 --version-tag phase1-uat-gap --bulk-provider gemini --max-parallel-batches 2 --generate-only
```

1. Main overnight command:

```bash
python -m src.data_pipeline.cli --seed-input data/raw/seeds-2026-04-24.jsonl --target-count 3000 --version-tag phase1-uat-gap --bulk-provider gemini --max-parallel-batches 2 --resume --generate-only
```

1. If it stops for any reason, run the exact same resume command again:

```bash
python -m src.data_pipeline.cli --seed-input data/raw/seeds-2026-04-24.jsonl --target-count 3000 --version-tag phase1-uat-gap --bulk-provider gemini --max-parallel-batches 2 --resume --generate-only
```

1. In a second terminal, watch how many rows are already saved:

```bash
python -c "from pathlib import Path; p=Path('data/synthetic/generated.jsonl'); print(sum(1 for _ in p.open('r', encoding='utf-8')) if p.exists() else 0)"
```

1. In another check, see whether the checkpoint is still advancing:

```bash
python -c "from pathlib import Path; p=Path('data/synthetic/.checkpoint.jsonl'); print(sum(1 for _ in p.open('r', encoding='utf-8')) if p.exists() else 0)"
```

1. In the morning, verify the final generated row count:

```bash
python -c "from pathlib import Path; p=Path('data/synthetic/generated.jsonl'); print('generated', sum(1 for _ in p.open('r', encoding='utf-8')) if p.exists() else 0)"
```

Rules for tonight:

1. Do not run the judge.
2. Do not switch back to `--bulk-provider claude` unless Gemini fails repeatedly.
3. Do not raise parallelism above `2` unless the machine is stable and you accept more in-flight cost risk.
4. If you press `Ctrl+C`, completed batches remain reusable. Just resume with the same command.

After the 3000 records are finished:

1. Do sample-based QA, not full per-record judging.
2. Spend the next few dollars on auditing a random subset with Claude or Gemini.
3. If the sample looks strong, treat the 3000-row generated set as the retained Phase 1 artifact and only then decide whether deeper judging is worth it.

dêepseek

```
python.exe -m src.data_pipeline.cli \
  --seed-input data/raw/seeds-2026-04-24.jsonl \
  --target-count 3000 \
  --version-tag phase1-uat-gap \
  --bulk-provider deepseek \
  --resume \
  --generate-only \
  --max-parallel-batches 2
  ```
