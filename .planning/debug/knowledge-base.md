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

## phase40-review-authority-drift — Plan 06 rejected frozen Plan 05 review authority
- **Date:** 2026-08-26
- **Error patterns:** Phase40ScopeAmendment.comparison_finalizer_authority, comparison finalizer authority must bind the exact source allowlist, reviewer judgments blocked, historical scope amendment, recovery request
- **Root cause(s):** Plan 06 retained the pre-Plan-05 live scope-amendment and single-request authority contract in both its shared CLI loader and human-review re-verifier, so it rejected the intentionally historical source inventory and could not resolve the selected PhoBERT v12 run through its recovery request
- **Fix:** Added an additive Plan 06 review consumer outside the frozen Plan 05 comparison closure; it authenticates the canonical final authority and both request roots as frozen upstream provenance, binds the v3 manifest and queue to that authority, resolves each run through its own origin, and preserves legacy v2 routing
- **Files changed:** `src/model_adaptation/phase40_review.py`, `src/model_adaptation/cli.py`, `tests/model_adaptation/test_phase40_final_authority.py`, `tests/model_adaptation/test_cli.py`, `data/models/phase40/review/human-review-notes.jsonl`, `data/models/phase40/review/human-review-manifest.json`, `data/models/phase40/review/human-review-report.md`
- **Why not caught:** The Phase 40 test gate covered the Plan 05 authority producer and legacy Plan 06 path separately, but no regression exercised a v3 review consumer after legitimate source-closure drift with a recovery-request-selected run
- **Recurrence guard:** Regression tests `test_review_handoff_accepts_hash_bound_historical_scope_source`, `test_review_handoff_rejects_noncanonical_scope_path`, and `test_phase40_v3_review_loader_uses_frozen_upstream_authority` enforce the live-rerun versus frozen-upstream boundary, canonical path binding, and persistent v3 CLI routing
---
