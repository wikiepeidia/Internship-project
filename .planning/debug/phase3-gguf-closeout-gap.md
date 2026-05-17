---
status: diagnosed
trigger: "Phase 3 closeout verification after both 4B adapter runs completed."
created: 2026-05-17
updated: 2026-05-17
---

# Phase 3 GGUF Closeout Gap

## Symptoms

- Expected: A real conversion flow should turn the trained baseline adapter into a registered GGUF artifact so the `gguf-laptop` runtime profile becomes ready.
- Actual: `convert_to_gguf(..., dry_run=False)` raises `RuntimeError: Real GGUF conversion is not wired in yet; use dry_run=True`, no GGUF artifact is registered, and `RUNTIME_BACKEND=gguf RUNTIME_PROFILE=gguf-laptop python -m src.runtime.cli doctor` reports not ready.
- Error messages: `RuntimeError: Real GGUF conversion is not wired in yet; use dry_run=True`
- Timeline: Verified on 2026-05-17 after the baseline and runner-up retained-dataset training runs completed.
- Reproduction: Build a GGUF request for `qwen3-4b-instruct-2507` against `D:/PROJEct/AI MODELS/manifests/model-registry.json`, call `convert_to_gguf(request, dry_run=False)`, then run the runtime doctor with `RUNTIME_BACKEND=gguf` and `RUNTIME_PROFILE=gguf-laptop`.

## Resolution

root_cause: "The conversion helper intentionally hard-stops on all non-dry-run requests, and the operator CLI still has no command that invokes a real adapter-to-GGUF conversion and registration path."
fix_direction: "Implement the real conversion path, register the produced GGUF artifact in the model registry, and re-run the public GGUF runtime doctor against the actual file."
files_involved:

- src/model_adaptation/convert.py
- src/model_adaptation/cli.py
- D:\PROJEct\AI MODELS\manifests\model-registry.json
