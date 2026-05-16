# Local Model Profiles

## Scope

Phase 3 keeps the runtime local-only and text-only while adding explicit profile selection for local model artifacts. The public runtime commands stay the same:

```bash
vnphish doctor
vnphish analyze
python -m src.runtime.cli doctor
python -m src.runtime.cli analyze
```

The difference is which local backend/profile is selected through settings.

Important distinction:

- LoRA/QLoRA is the Phase 3 training path used to adapt the selected Qwen checkpoints.
- GGUF is the laptop CPU/iGPU inference artifact used after training.
- In other words, the CPU baseline in Phase 3 is for local inference, not for the main fine-tuning step.

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

1. Run the Phase 3 pilot dry-run to record the baseline winner and runner-up.
2. Run the Phase 3 training doctor to confirm local dependencies, base-model paths, and smoke-test commands.
3. Run a short Phase 3 smoke training job for `baseline-winner`, let it save checkpoints, then resume from `latest` if the short probe succeeds.
4. Run the Phase 3 training dry-run or full run for `runner-up` when needed.
5. Stage the `GGUF` baseline artifact.
6. Select the target profile in settings.
7. Run the runtime doctor command before `analyze`.

Phase 3 operator commands:

```bash
python -m src.model_adaptation.cli doctor --candidate baseline-winner
python -m src.model_adaptation.cli train --candidate baseline-winner --version-tag phase3-smoke --smoke-test
python -m src.model_adaptation.cli train --candidate baseline-winner --version-tag phase3-main --resume-from-checkpoint latest
```

If the local environment is missing the training stack, install the optional extra first:

```bash
python -m pip install -e .[dev,train]
```
