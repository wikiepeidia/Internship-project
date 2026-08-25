# Phase 40 Colab run handoff

Status: frozen and launch-ready after the local QLoRA proof was imported as a control expectation.

Run each notebook in a fresh Colab runtime. Do not reuse a probe adapter or a previous notebook runtime. The canonical input contains train and validation only; the reserved Phase 41 partition is not transferred.

## Upload once to Drive

Copy the repository `data/models/phase40/` authority artifacts beneath `/content/drive/MyDrive/internship-phase40/repository/data/models/phase40/` and copy the exact input archive to `/content/drive/MyDrive/internship-phase40/phase40-train-validation.zip`. Do not rename either authority.

## Run order

1. `notebooks/phase40/qwen_lora_colab.ipynb`
2. `notebooks/phase40/qwen_qlora_colab.ipynb`
3. `notebooks/phase40/phobert_colab.ipynb`

Each notebook verifies source, request, model snapshot, and exact input archive before training. It persists command logs, raw training events, trainer state, validation predictions, deterministic graphs, and the complete returned bundle in Drive.

The Qwen full runs are both 3 epochs / 1,245 optimizer steps at effective batch 4. The local 5+40 QLoRA cap is probe evidence only and is not used by either full run.

Qwen GGUF export uses `gguf==0.19.0`, the request-independent reviewed converter script hash `f227273d926fd8ba1c5215ca9ba64d63e641b3277e6f225080b4aac434999b55`, and locked `q8_0`. Browser download remains a separate optional human-run cell after manifest verification.

## Frozen identities

- Request SHA-256: `93b49371db184f28b2fb362da94ce99298f64487820176d2b10f65871ed3b8b8`
- Input archive SHA-256: `12136f9a79e7c9852f6b317f284a9a018710aa66af54de4714ec66e8cf92bf84`
- Source archive SHA-256: `f7566931dfb6f28471dc0ca97c71e21eec4ae5a50471cc088794185816ba3e85`
- QLoRA full steps: `1245`

A complete run may resume only from one exact compatibility-verified checkpoint. A fresh run always starts at step zero.
