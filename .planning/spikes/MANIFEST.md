# Spike Manifest

## Ideas

### phase40-idle-readiness

Use the active local QLoRA training window to remove setup risk from the queued PhoBERT run and the later one-shot model evaluation, without competing for the GPU or further accessing the reserved partition. Prior human/content exposure is disclosed separately.

**Requirements:**

- The active QLoRA trainer and supervisor must not be stopped or duplicated. The idle downstream controller may be replaced only after exact PID/start-time/source-hash checks and only with a parsed, retained, fail-closed version.
- Readiness checks may inspect only Phase 40 authorities, controller state, train/validation configuration, and process health; they must not read, hash, stat, or enumerate `data/splits/test.jsonl`.
- PhoBERT remains strictly sequenced after verified Qwen evidence, verified GGUF export, trainer exit, and the controller's three low-VRAM samples.
- Phase 41 preparation must make no further content access and must fail closed until both model identities, the validation-contingency decision, and an explicit one-shot authorization are frozen. Literal human blindness is not claimed.
- Colab remains a pre-test validation contingency, never an automatic duplicate run or a reaction to held-out results.

## Spikes

| # | Idea | Name | Type | Validates | Verdict | Tags |
|---|------|------|------|-----------|---------|------|
| 001 | phase40-idle-readiness | training-window-readiness | standard | Given the live QLoRA chain and model-evaluation boundary, when static authorities, process/controller state, and downstream contracts are checked without GPU work or further reserved-content access, then launch blockers are exposed and safely contained before PhoBERT and Phase 41. | PARTIAL | phase40, phobert, phase41, safety-gate |
