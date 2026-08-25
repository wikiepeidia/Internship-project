# Phase 40 Colab contingency handoff (historical)

Status: frozen historical/contingency artifact; not executed and not part of the primary path under the user-approved 2026-08-25 scope amendment.

The additive machine authority is `data/models/phase40/two-full-model-scope-amendment.json`, bound to immutable request SHA-256 `2512dbe6d7c5b8c16141ebdbdc848382e56b3a5737e8aeea51d7fb89447c643a`. The original request remains byte-unchanged.

Do not execute this handoff by default. The primary path is local QLoRA, verified Q8_0 GGUF, then local PhoBERT and a two-model validation comparison. Full ordinary LoRA is retired; its sealed laptop probe is resource/ETA evidence only.

This artifact may be activated only before the reserved Phase 41 partition is opened and only if frozen development-validation review finds a local model result unacceptable. Activation requires a recorded reason and a fresh step-zero run for only the affected QLoRA or PhoBERT branch. It must never be triggered by held-out results, and it cannot be used to tune, repair the dataset, or reselect a checkpoint after the reserved partition has been opened.

If that contingency is explicitly activated, use a fresh Colab runtime. Do not reuse a probe adapter, local full-run checkpoint, or previous notebook runtime. The canonical input contains train and validation only; the reserved Phase 41 partition is not transferred.

## Upload once to Drive

Copy the repository `data/models/phase40/` authority artifacts beneath `/content/drive/MyDrive/internship-phase40/repository/data/models/phase40/` and copy the exact input archive to `/content/drive/MyDrive/internship-phase40/phase40-train-validation.zip`. Do not rename either authority.

## Historical generated run order and amended authority

1. `notebooks/phase40/qwen_lora_colab.ipynb` — historical only; do not run under the amended scope.
2. `notebooks/phase40/qwen_qlora_colab.ipynb` — contingency only for an unacceptable local QLoRA validation result before the reserved-test gate.
3. `notebooks/phase40/phobert_colab.ipynb` — contingency only for an unacceptable local PhoBERT validation result before the reserved-test gate.

The original request and these notebooks remain immutable historical provenance. Their existence does not prove that any Colab run occurred. Any explicitly activated contingency notebook must still verify source, request, model snapshot, and exact input archive before training, then persist command logs, raw training events, trainer state, validation predictions, deterministic graphs, and the complete returned bundle in Drive.

The QLoRA contingency remains 3 epochs / 1,245 optimizer steps at effective batch 4. The local 5+40 QLoRA cap is probe evidence only and cannot seed a full run. The retired ordinary-LoRA notebook is not an authorized full run.

Qwen GGUF export uses `gguf==0.19.0`, the request-independent reviewed converter script hash `f227273d926fd8ba1c5215ca9ba64d63e641b3277e6f225080b4aac434999b55`, and locked `q8_0`. Browser download remains a separate optional human-run cell after manifest verification.

## Frozen identities

- Request SHA-256: `2512dbe6d7c5b8c16141ebdbdc848382e56b3a5737e8aeea51d7fb89447c643a`
- Input archive SHA-256: `12136f9a79e7c9852f6b317f284a9a018710aa66af54de4714ec66e8cf92bf84`
- Source archive SHA-256: `eae64f17383d749a7759391d766ad59b337d35155ae89744adeaba8631e71a66`
- QLoRA full steps: `1245`

A complete run may resume only from one exact compatibility-verified checkpoint. A fresh run always starts at step zero.
