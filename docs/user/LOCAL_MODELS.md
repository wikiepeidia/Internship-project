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
2. Run the Phase 3 training dry-run for `baseline-winner` and `runner-up`.
3. Stage the `GGUF` baseline artifact.
4. Select the target profile in settings.
5. Run the doctor command before `analyze`.
