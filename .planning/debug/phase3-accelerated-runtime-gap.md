---
status: diagnosed
trigger: "Phase 3 closeout verification after both 4B adapter runs completed."
created: 2026-05-17
updated: 2026-05-17
---

# Phase 3 Accelerated Runtime Gap

## Symptoms

- Expected: The accelerated local runtime should use the trained runner-up adapter for inference while preserving the stable Phase 4 output schema.
- Actual: `RUNTIME_BACKEND=accelerated RUNTIME_PROFILE=accelerated-local python -m src.runtime.cli doctor` reports ready and `analyze` returns a valid schema, but the backend logic still relies on regex and keyword cues rather than model inference.
- Error messages: None at runtime; the gap is implementation-level rather than a crash.
- Timeline: Verified on 2026-05-17 during Phase 3 closeout checks.
- Reproduction: Read `src/runtime/analyzers/accelerated.py` and compare `doctor()` with `analyze()`; then run the accelerated runtime doctor and analyze commands against the registered runner-up adapter.

## Resolution

root_cause: "The accelerated analyzer was left as a contract-compatible scaffold: readiness checks only confirm artifact presence, and the analyze path never loads the trained runner-up adapter or tokenizer."
fix_direction: "Replace the placeholder cue logic with real local inference on the trained runner-up artifact while keeping the current output contract stable for downstream Phase 4 work."
files_involved:

- src/runtime/analyzers/accelerated.py
- src/runtime/service.py
