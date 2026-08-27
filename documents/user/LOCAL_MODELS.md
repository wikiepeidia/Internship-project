# Local Model Profiles

## Scope

The runtime stays local-only and text-only while explicit profiles select local model artifacts. The public runtime commands stay the same:

```bash
vnphish doctor
vnphish analyze
python -m src.runtime.cli doctor
python -m src.runtime.cli analyze
```

The difference is which local backend/profile is selected through settings.

Important distinction:

- LoRA/QLoRA is the model-adaptation path used to train the selected Qwen checkpoints.
- GGUF is the laptop CPU/iGPU inference artifact used after training.
- In other words, the CPU baseline is for local inference, not for the main fine-tuning step.

## Profiles

### GGUF Laptop Baseline

- Backend: `gguf`
- Profile: `gguf-laptop`
- Target: the pilot-selected 4B baseline winner
- Artifact expectation: registered `GGUF` artifact under the local model registry
- Best for: consumer laptop CPU/iGPU baseline

### Accelerated Local Profile

- Backend: `accelerated`
- Profile: `accelerated-local`
- Target: the selected runner-up path for stronger local hardware
- Artifact expectation: registered local adapter/runtime artifact for the accelerated path
- Best for: stronger local GPU or prosumer hardware

## Explicit Selection

Profile selection is explicit. Do not rely on silent fallback between profiles.

Typical settings values are:

```text
runtime_backend=gguf
runtime_profile=gguf-laptop
```

or:

```text
runtime_backend=accelerated
runtime_profile=accelerated-local
```

If the selected profile is not ready, the runtime fails closed and the doctor report explains why.

## Doctor Expectations

Use the doctor command after changing profiles:

```bash
vnphish doctor
python -m src.runtime.cli doctor
```

The doctor report should name the selected backend and profile, then report profile-specific readiness details such as:

- missing local model registry
- missing `GGUF` artifact for the laptop baseline
- missing accelerated local artifact for the stronger-hardware profile
- invalid profile selection

The doctor guidance remains local-only. It should not suggest cloud fallback.

## Artifact Expectations

- Large model binaries remain local-only and untracked by git.
- The model registry stores metadata, checksums, and selection state.
- `GGUF` artifacts support the laptop baseline.
- Adapter artifacts support continued tuning and the accelerated local profile.

## Operator Flow

Recommended order:

1. Run the model pilot dry-run to record the baseline winner and runner-up.
2. Run the training doctor to confirm local dependencies, base-model paths, and smoke-test commands.
3. Run a short smoke training job for `baseline-winner`, let it save checkpoints, then resume from `latest` if the short probe succeeds.
4. Run the training dry-run or full run for `runner-up` when needed.
5. Stage the `GGUF` baseline artifact.
6. Select the target profile in settings.
7. Run the runtime doctor command before `analyze`.

Model-adaptation operator commands:

<!-- legacy-local-model-cli:start -->
```bash
python -m src.model_adaptation.cli doctor --candidate baseline-winner
python -m src.model_adaptation.cli train --candidate baseline-winner --version-tag phase3-smoke --smoke-test
python -m src.model_adaptation.cli train --candidate baseline-winner --version-tag phase3-main --resume-from-checkpoint latest
```
<!-- legacy-local-model-cli:end -->

If the local environment is missing the training stack, install the optional extra first:

```bash
python -m pip install -e .[dev,train]
```

## Colab Generation

If you want to avoid paid API generation for dataset experiments, you can run an OpenAI-compatible server from Google Colab and point the existing generator CLI at it.

Recommended hardware:

- `H100` first choice
- `A100` second choice
- `L4` only for smaller or quantized checkpoints
- `T4` and `G4` are fallback-only and not a good fit for stable 32B generation

Recommended serving pattern:

1. In Colab, start a vLLM OpenAI-compatible server for an instruction model such as `Qwen/Qwen2.5-32B-Instruct-AWQ`.
2. Expose the server URL securely.
3. Set these local environment values in `.env/.env`:

```text
OPENAI_COMPATIBLE_BASE_URL=https://your-colab-endpoint.example/v1
OPENAI_COMPATIBLE_API_KEY=optional-token
OPENAI_COMPATIBLE_MODEL=Qwen/Qwen2.5-32B-Instruct-AWQ
```

4. Run the existing generator with the explicit provider:

```bash
python -m src.data_pipeline.cli \
	--seed-input data/raw/seeds-2026-04-24.jsonl \
	--target-count 3000 \
	--version-tag proposal-closeout \
	--bulk-provider openai-compatible \
	--generate-only \
	--resume
```

This route reuses the existing checkpoint and JSONL flow, but generation quality depends on the served checkpoint and prompt discipline. Use `generate-only` first, then judge or rebalance after the raw artifact looks healthy.
