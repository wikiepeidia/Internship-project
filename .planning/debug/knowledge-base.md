# GSD Debug Knowledge Base

Resolved debug sessions. Used by `gsd-debugger` to surface known-pattern hypotheses at the start of new investigations.

---

## phobert-launch-empty-path — Fresh PhoBERT launch and telemetry seal recovery
- **Date:** 2026-08-26
- **Error patterns:** GetFullPath path is empty, omitted typed PowerShell string, unexpected keyword save_safetensors, canonical request-bound snapshot path, telemetry controlled-stop timeout, comma-decimal elapsed_seconds
- **Root cause(s):** Omitted `[string]` checkpoint input was coerced to empty and passed a null-only guard; PhoBERT directly passed a Transformers-5-removed keyword without signature filtering; v11 mixed request and base authorities across roots; v12 used cancellation-only infinite telemetry and produced locale-comma elapsed values that contradicted its invariant seal parser
- **Fix:** Added fresh controller guards and canonical v12 authority, signature-aware PhoBERT TrainingArguments construction, completed the fresh v12 run, and sealed preserved telemetry through a truth-preserving no-launch v13 repair
- **Files changed:** `src/model_adaptation/phobert_training.py`, `tests/model_adaptation/test_phase40_phobert.py`, `.planning/spikes/001-training-window-readiness/phase40-qwen-to-phobert-chain-v10.ps1`, v11/v12 packagers/controllers/harnesses, v13 seal-only repair and regression/mutation harnesses
- **Why not caught:** No gate exercised typed-string coercion, the installed Transformers constructor, request/base canonical binding, and locale-sensitive telemetry shutdown/sealing as an end-to-end chain; permissive test fakes hid the removed keyword
- **Recurrence guard:** Strict-v5 and kwargs-neighbor tests in `tests/model_adaptation/test_phase40_phobert.py`; v10/v12 CPU controller harnesses; `test-seal-phase40-phobert-v12-telemetry-v13.ps1` and `test-seal-phase40-phobert-v12-telemetry-v13-mutations.ps1`
---

