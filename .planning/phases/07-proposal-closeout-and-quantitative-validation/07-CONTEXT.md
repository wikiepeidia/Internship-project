# Phase 7: Proposal Closeout and Quantitative Validation - Context

**Gathered:** 2026-05-25
**Status:** Complete; dataset closeout, repaired-holdout evidence refresh, UAT, and security audit are all finished

## Phase Boundary

Close the two remaining school-facing quantitative claims with one frozen dataset lineage and one honest held-out evaluation package for the locked baseline winner.

**Scope guardrails:**

- Keep the model-selection decision locked to the current baseline winner unless the user explicitly reopens it.
- Treat `data/synthetic/recovered-balanced.jsonl` and `data/splits/recovered-balanced/` as the active closeout lineage.
- Spend no more frontier API budget on broad exploratory generation; only targeted gap-closing work is still justified.
- Do not claim proposal-closeout quality from the older `data/splits/val.jsonl` sample run.
- Keep the release evidence path anchored to the shipped runtime contract rather than inventing a separate evaluator-only model path.

## Current Verified Status

- The balanced closeout corpus now exists at `data/synthetic/recovered-balanced.jsonl` with 3,000 rows.
- The repaired split root now lives at `data/splits/recovered-balanced/`.
- `audit_release_eval_support` on `data/splits/recovered-balanced/val.jsonl` passed with support `{bank_impersonation: 56, zalo_social_engineering: 75, task_scam: 18, benign: 61}`.
- The splitter repair now preserves seed grouping where possible and falls back cleanly for underdiverse labels so risky classes can populate active splits.
- The GGUF runtime evaluation path was repaired by raising the context window to 2,048 and preferring chat JSON mode, which stopped the malformed truncated payload problem.
- The first full repaired-holdout rerun then exposed a second runtime issue: the Phase 4 safety floor could escalate benign outputs on generic `credential_request` helper cues and then crash when no in-scope label was inferable. The local-model fallback now preserves the original benign decision when helper cues are too generic to map safely.
- `src.model_adaptation.cli` now includes `evaluate-release-split`, with progress output and periodic snapshot checkpoint writes.
- Registry lookup now prefers the latest registered adapter and GGUF artifacts, so future train and convert runs will actually be used by the runtime.
- The real closeout retrain has now completed at `D:/PROJEct/AI MODELS/proposal-closeout-full-2026-05-26/qwen3-4b-instruct-2507/trainer/checkpoint-505` with `train_examples=2018` and `val_examples=210`.
- The refreshed GGUF artifact now exists at `D:/PROJEct/AI MODELS/proposal-closeout-gguf-2026-05-26/qwen3-4b-instruct-2507/gguf-laptop.gguf`.
- The working local conversion path on this machine required `GGUF_CONVERTER_SCRIPT` pointed at the Python 3.13 site-packages `convert_hf_to_gguf.py` and a direct `q8_0` output profile because `llama-quantize` is not installed.
- The repaired-holdout evaluation completed end-to-end against `data/splits/recovered-balanced/val.jsonl`, producing a 210-row snapshot with `macro_f1=0.7431` and `weighted_f1=0.8618`.
- The regenerated explanation review pack now exists at `.planning/phases/05-recall-priority-evaluation-and-release-gates/05-explanation-review-pack.json`, was completed manually, and stayed schema-valid after the runtime hardening fixes.
- The final release-eval artifacts now exist at `.planning/phases/05-recall-priority-evaluation-and-release-gates/05-release-eval-phase5-recovered-balanced-val.md` and `data/manifests/phase5-release-eval-phase5-recovered-balanced-val.json`.
- The final proposal evidence path is honest: the repaired-holdout release verdict is `BLOCK` because `task_scam` recall is `0.44`, below the locked `0.90` floor, while `bank_impersonation` recall is `0.9821` and `zalo_social_engineering` recall is `0.9867`.
- Focused validation after the runtime hardening: `python -m pytest tests/runtime/test_local_model.py -q` passed with `13 passed`, and `python -m pytest tests/model_adaptation/test_release_evaluation.py -q` passed with `7 passed` after snapshot-resume coverage was added.
- Phase 7 UAT is complete at `.planning/phases/07-proposal-closeout-and-quantitative-validation/07-UAT.md`.
- Phase 7 security is verified at `.planning/phases/07-proposal-closeout-and-quantitative-validation/07-SECURITY.md` with `threats_open: 0`.

## Locked Decisions

- The Phase 7 closeout dataset lineage is the recovered-balanced corpus, not the older generic `validated.jsonl` path.
- The held-out evaluation path for proposal closeout is `data/splits/recovered-balanced/val.jsonl`.
- The locked baseline winner remains `qwen3-4b-instruct-2507` / `baseline-winner`.
- A full retrain is optional for closeout, but if it is performed, the new adapter must be converted to GGUF before the default runtime-backed Phase 5 evaluation path can use it.
- On this machine, the practical convert command is the `GGUF_CONVERTER_SCRIPT=... python -m src.model_adaptation.cli convert ... --quantization-profile q8_0` variant, not the plain `q4_k_m` default.
- The 20 minute training run completed earlier in the day was only a smoke test and is not acceptable as final closeout evidence.
- The operational sequence for the final evidence refresh is: optional `train` -> `convert` -> `evaluate-release-split` -> `prepare-explanation-review` -> manual review -> `release-eval`.

## Canonical Commands

### Optional overnight retrain

```bash
python -m src.model_adaptation.cli train \
 --candidate baseline-winner \
 --version-tag proposal-closeout-full-2026-05-26 \
 --train-split data/splits/recovered-balanced/train.jsonl \
 --val-split data/splits/recovered-balanced/val.jsonl \
 --output-root "D:/PROJEct/AI MODELS" \
 --registry-path "D:/PROJEct/AI MODELS/manifests/model-registry.json" \
 --device cuda \
 --full-precision
```

### Convert after any new retrain

```bash
GGUF_CONVERTER_SCRIPT="C:/Users/wikiepeidia/AppData/Local/Programs/Python/Python313/Lib/site-packages/bin/convert_hf_to_gguf.py" python -m src.model_adaptation.cli convert \
 --candidate baseline-winner \
 --version-tag proposal-closeout-gguf-2026-05-26 \
 --output-root "D:/PROJEct/AI MODELS" \
 --registry-path "D:/PROJEct/AI MODELS/manifests/model-registry.json" \
 --quantization-profile q8_0
```

### Refresh the repaired-holdout snapshot

```bash
python -m src.model_adaptation.cli evaluate-release-split \
 --split-path data/splits/recovered-balanced/val.jsonl \
 --snapshot-path .planning/phases/05-recall-priority-evaluation-and-release-gates/05-evaluation-snapshot.json \
 --run-id phase5-recovered-balanced-val \
 --progress-every 1 \
 --checkpoint-every 1
```

### Build the new review pack

```bash
python -m src.model_adaptation.cli prepare-explanation-review \
 --snapshot-path .planning/phases/05-recall-priority-evaluation-and-release-gates/05-evaluation-snapshot.json \
 --output-path .planning/phases/05-recall-priority-evaluation-and-release-gates/05-explanation-review-pack.json
```

### Final verdict synthesis after manual review

```bash
python -m src.model_adaptation.cli release-eval \
 --snapshot-path .planning/phases/05-recall-priority-evaluation-and-release-gates/05-evaluation-snapshot.json \
 --review-pack-path .planning/phases/05-recall-priority-evaluation-and-release-gates/05-explanation-review-pack.json \
 --report-dir .planning/phases/05-recall-priority-evaluation-and-release-gates \
 --manifest-dir data/manifests
```

## Risks and Watchpoints

- A real full retrain is an 8-9 hour job on this laptop/GPU.
- The current default runtime path reads the GGUF artifact, so evaluating immediately after retraining without conversion will not measure the refreshed model.
- The local Python shell currently resolves `python` to `C:/Users/wikiepeidia/AppData/Local/Programs/Python/Python313/python.exe`, and the converter script needed `gguf` plus `sentencepiece` installed there before GGUF export would run.
- The saved Phase 5 artifacts under `.planning/phases/05-recall-priority-evaluation-and-release-gates/` and `data/manifests/` are now the refreshed closeout evidence path; the important remaining weakness is model quality, not artifact freshness.
- The runner-up GGUF artifact exists but is not the shipped closeout path; keep `gguf-laptop` and `accelerated-local` as the validated runtime profiles.

## Current Re-entry Point

- The train, convert, repaired-holdout evaluation, manual review checkpoint, release-eval synthesis, UAT, and security steps are complete.
- Resume from here only to start next-milestone planning or to investigate the documented `task_scam` recall blocker.

---

*Phase: 07-proposal-closeout-and-quantitative-validation*
*Context created: 2026-05-25 after recovered-balanced closeout, repaired holdout support, GGUF evaluation fixes, and TODO sequencing*