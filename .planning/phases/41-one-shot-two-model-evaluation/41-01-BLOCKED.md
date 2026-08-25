---
phase: 41-one-shot-two-model-evaluation
plan: 01
status: blocked
blocked_at: production-authority-derivation
blocked_code: phase40_comparison_launch_receipt_contract_missing
additional_blocked_code: phase40_runtime_dependency_byte_authority_missing
synthetic_verification:
  integrated_focused: 103 passed
  full_model_adaptation: 626 passed
  protocol_host: 33 passed
  runtime_authority: 28 passed
  peer_review: 36 passed
  launcher_ast_tokens: 2835
---

# Phase 41 Plan 01: Blocked Production-Authority Handoff

Phase 41's synthetic-only state machine, replay boundary, clean-runtime source closure, and model-specific protocol validators are implemented, regression-clean, and peer-reviewed PASS. The plan is not complete: canonical preparation cannot safely derive or write production protocols until Phase 40 produces and binds the authorities listed below. Every production preauthorization, authorization, run, evidence-verification, and low-level launcher-capability verb independently rejects output-root declarations with `phase40_comparison_launch_receipt_contract_missing`; no caller-authored production JSON can substitute for the missing code-fixed upstream closure.

No real reserved split, real model artifact, GPU, training run, or evaluation was accessed while implementing or verifying this plan.

## Completed Synthetic Preparation

- The irreversible state-machine semantics are exercised end to end with temporary synthetic JSONL, fake predictors, and synthetic protocol authorities; this private tracer is durably marked synthetic and is not the production entry.
- The content-SHA claim precedes the sole split-handle acquisition; successful and spent-failed terminal states are deterministic and verify-only is byte-stable.
- The launcher resolves the machine claim registry from the Windows Known Folder API, verifies its protected owner/DACL, locks every authority and source handle, materializes an exact source-only clean runtime, pins the Python executable by path/hash/version, and starts the fixed CLI with `-I -S -s -B`.
- The launcher passes a one-use inherited stdin-pipe capability without writing its nonce or handle to disk, the environment, or the command line. Bound project code verifies the real pipe type, server PID, live parent process, and locked parent executable bytes; the evaluator consumes the capability immediately before the durable global claim, and the verified predictors retain it with their immutable model leases through final evidence sealing.
- The public production entry accepts only the output root, internally owns both real model loads, and exposes predictor injection only through a private synthetic-runtime seam.
- Durable preparation scope is explicit. Synthetic requests, protocols, launcher hosts, authority hashes, predictors, and materialization receipts can never enter a production verb; production requests require the comparison-launch, selected-Qwen GGUF, PhoBERT tokenizer, PhoBERT segmenter, and frozen-runtime authority hashes through request, preauthorization, authorization, and materialization binding.
- The production entry captures the reviewed predictor classes, slot/property descriptors, unbound property getters, methods, and protocol helper code before capability acquisition. It revalidates their exact source/code identities at every critical boundary and calls the captured unbound functions directly, so in-place class monkeypatching cannot forge a lease-less verified predictor.
- Clean-runtime imports execute the already verified in-memory source bytes while preserving their locked materialized origins, so a file added or changed after inventory verification cannot enter the process.
- Runtime protocol validation binds separately sealed absolute model-bundle roots, lifetime locks over each model/base snapshot, exact Python/package/CUDA identities, genuine Qwen four-bit NF4 loading and deterministic decoder controls, plus the frozen PhoBERT tokenizer/segmenter contract.
- Qwen uses the Phase 40 chat/parser contract with zero retries or repairs. PhoBERT uses raw UTF-8 text, `underthesea` 9.5.0, right truncation, length 256, and dynamic-longest padding.
- A fixed evidence allowlist, non-success machine-global completion journal, final protected completion transition, and precommitted deployment-fit choice prevent traversal, post-result choice, local resealing, and successful-after-partial-write claims. A failed local or protected finalization deterministically replaces the provisional local terminal with `spent_failed`.

## Blocking Phase 40 Producers

### 1. External comparison-launch receipt

Phase 40 planning requires an independent PowerShell/OS source preflight before the comparison finalizer starts, but the repository has no canonical receipt path, strict schema, producer, verifier, or comparison-manifest field that binds such a receipt. Phase 41 will not infer a PASS from the final comparison manifest or invent a receipt format.

Required upstream output: a canonical, strict, self-hashed receipt produced before Python comparison launch and bound to the request, scope amendment, exact finalizer inventory/tree, launcher identity, PASS result, and launch chronology; the Phase 40 comparison/review closure must bind its hash.

### 2. Selected-run GGUF verification authority

`phase40_gguf.py` can export and verify a GGUF export manifest, but the canonical two-model comparison/review closure does not expose a selected-Qwen GGUF verification receipt or bind its hash. The documentation-level `qwen-gguf-verification-receipt.json` expectation therefore has no trusted producer/consumer chain for Phase 41.

Required upstream output: a canonical receipt that binds the selected Qwen run/checkpoint, GGUF export-manifest hash, output hash and quantization, converter authority, successful load smoke, and verification time; the comparison manifest must bind that receipt.

### 3. Retained PhoBERT tokenizer authority

The PhoBERT trainer retains the selected model directory as `adapter-or-model`, but it does not explicitly retain and inventory the exact tokenizer assets needed for inference. Phase 41 cannot safely assume that `Trainer.save_model` preserved tokenizer files or reconstruct them from an unbound cache.

Required upstream output: tokenizer files copied into the immutable PhoBERT bundle, an exact tokenizer tree/content digest, and a bundle artifact/manifest field linking that digest to the selected checkpoint and base snapshot.

### 4. Independent PhoBERT segmenter authority

Commit `08761f8` now provides fail-closed runtime/segmenter capture tooling and hostile mutation tests. The remaining blocker is lifecycle integration: Phase 40 has not yet run that tooling against the final post-training inference environment, materialized the resulting canonical segmenter authority beside the selected PhoBERT bundle, or bound its hash and chronology into the final comparison/review closure. A package version alone still does not prove the executable segmentation bytes.

Required upstream output: run the committed capture tool after both final models and inference dependencies are frozen, retain its strict segmenter tree/wheel receipt, and bind that receipt hash into the comparison and Phase 41 request. Phase 41 will not manufacture `segmenter_sha256` or accept an unbound capture.

### 5. Frozen runtime dependency byte authority

Commit `08761f8` now provides strict runtime dependency byte-authority capture and verification tooling. The remaining blocker is canonical post-training materialization and comparison binding: no final receipt has yet been captured from the exact Qwen/PhoBERT inference environment, stored at a code-fixed authority path, chronology-bound after model freeze and before comparison launch, or referenced by the comparison/review closure. Until that happens, same-version package-byte replacement remains outside the production proof boundary.

Required upstream output: run the committed producer on the final installed tree, retain its exact file/package/native-library inventory, verify it independently, and bind its immutable hash into the comparison/model closure. Canonical preparation continues to fail closed with `phase40_runtime_dependency_byte_authority_missing` until that materialized receipt exists; tooling availability alone is not authority completion.

## Verification Evidence

- Integrated Phase 41 evaluation/protocol/launcher/release/CLI suite at code HEAD `e1454e1`: **103 passed** under the normal Windows host token.
- Full `tests/model_adaptation` suite at code HEAD `e1454e1`: **626 passed**, with two existing SWIG deprecation warnings, using the established non-OneDrive Windows temp root.
- Protocol lifetime, direct-root, and ancestor-lock hostile suite at `614947a`: **33 passed** under the unrestricted host token.
- Phase 40 runtime/segmenter authority capture and hostile mutation suite at `08761f8`: **28 passed**.
- Final peer hostile review/regression pass: **36 passed**, verdict **PASS**.
- Restricted managed-token probe: model-root ancestor locking fails closed with WinError 5 before any model use when a required ancestor handle cannot be retained. The production contract is intentionally not weakened to make that restricted environment pass.
- PowerShell launcher AST: clean, **2,835 tokens**.
- `git diff --check`: clean apart from Windows LF-to-CRLF notices.

Implementation commits retained for continuation:

- `18a56df` — Task 1 RED
- `1940e24` — Task 1 GREEN
- `c81fd44` — Task 2 RED
- `0b9b2ae` — Task 2 GREEN
- `4cb43ae` — Task 3 RED
- `cdbb373` — Task 3 initial GREEN
- `535ba9c` — reviewer hardening for source/runtime closure
- `41bd135` — protocol v2 bundle, loader, decoder, and durability hardening
- `2c21e69` — remove legacy executable evaluation routes
- `d89edfd` — preserve inert Phase 40 CLI compatibility without restoring a route
- `6ee04da` — protected registry/materializer/evidence-seal hardening and hostile regressions
- `25cfc19` — align pinned Python runtime identity and execute both embedded launcher programs synthetically
- `0b9c4c2` — lock model/base snapshots through prediction and bind verified wrappers to a live launcher capability
- `c8c857f` — consume the live launcher capability at claim time and close source-import, claim-freeze, and protected-completion races
- `0a32007` — permanently detect transient add-use-delete mutations during model loading
- `60bc8aa` — initial model-root ancestor lock hardening, superseded after review rejected its token-relative fallback
- `634d09c` — move launcher authentication into bound code, internalize model loading, and make protected completion failure-safe
- `d17d488` — remove the unsafe access-denied fallback and fail closed unless every model-root ancestor is handle-locked
- `c1aee15` — remove the forgeable Python capability object and require exact live model leases at every predictor use
- `614947a` — block direct model-root and every retained ancestor rename with lifetime kernel handles
- `11034a0` — separate durable synthetic/production scope and internalize the source-bound production predictor path
- `08761f8` — add strict runtime dependency and PhoBERT segmenter authority capture/verification tooling
- `e1454e1` — reject self-declared production closures, bind the five future authorities end to end, and pin reviewed predictor descriptors

## Next Executable Step

1. Let Phase 40 finish both final models without consulting the reserved split, then run the committed runtime/segmenter capture tooling against the exact post-training inference environment.
2. Produce the still-missing external comparison-launch, selected-Qwen GGUF verification, and retained PhoBERT tokenizer authorities; materialize all five at code-fixed paths and bind their hashes/chronology into the canonical Phase 40 comparison and human-review closure.
3. Resume Plan 41-01 to add production protocol derivation from those typed authorities and replace the stable fail-closed preconditions with canonical artifact generation.
4. Re-run the synthetic focused/full suites and `phase41-verify-preauthorization` before any explicit one-shot authorization. The reserved evaluation must remain unopened until that separate human gate.

`41-01-SUMMARY.md` is intentionally absent, EVAL-08/EVAL-09 remain incomplete, and Phase 41 roadmap progress must not advance while these upstream authorities are missing.
