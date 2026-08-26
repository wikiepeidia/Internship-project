# Phase 40 Local Two-Full-Model Comparison

Status: **complete**

This experiment uses one predeclared training seed (42). It does not estimate run-to-run variance, statistical significance, or stable superiority; no t-test claim is made.

Primary execution: local laptop. Colab is validation-only contingency before the held-out boundary is opened.
Each training run remains governed by its immutable origin request/source authority; the post-run comparison selects those origins without rewriting either run.
Full Qwen LoRA was withdrawn and cancelled before its production run; its bounded local probe is resource evidence only and contributes no predictions.
LoRA probe: observed_steps=31, retained_steps=26, median_step_seconds=53.274, peak_VRAM_MiB=7902.0, minimum_free_VRAM_MiB=9.0
The probe completed optimizer steps with finite loss and no OOM; the waiver is an operational resource/deadline decision, not a claim that LoRA cannot run.

Validation rows per model: 219
Quality comparison admissible: True
Hardware-confounded timing/throughput: False
Speed comparison admissible: False
Human-review queue rows: 52
Authority verification at comparison time: portable receipts only; live external model and runtime recapture remain separate gates.
Runtime materialization receipt SHA-256: `2f5a4f30971d5fea2842bf3042c23fe653bd20973848a181553c5d40680a401a` (portable receipt binding only; comparison finalization did not perform live runtime recapture).

## Retained runs

- `phase40-qwen-qlora-full-seed42-v1` (qwen/qlora): safety_gate=True, comparison_eligible=True, selected_step=200, macro_F1=0.9885, invalid_outputs=0, risky_recall=[bank_impersonation=0.9868, zalo_social_engineering=1.0000, task_scam=1.0000], GPU=NVIDIA GeForce RTX 5050 Laptop GPU, exact_run_packages=[bitsandbytes=0.50.1, peft=0.19.1, python=3.13.13, torch=2.12.0+cu132, transformers=5.9.0], required_tool_pins=[bitsandbytes=0.50.1, matplotlib=3.11.1]
- `phase40-phobert-full-seed42-v12` (phobert/classification-head): safety_gate=True, comparison_eligible=True, selected_step=100, macro_F1=0.9849, invalid_outputs=0, risky_recall=[bank_impersonation=1.0000, zalo_social_engineering=0.9545, task_scam=1.0000], GPU=NVIDIA GeForce RTX 5050 Laptop GPU, exact_run_packages=[python=3.13.13, torch=2.12.0+cu132, transformers=5.9.0, underthesea=9.5.0], required_tool_pins=[matplotlib=3.11.1]

Both submitted complete quality runs are retained, including any failed safety gate; a failed gate is never silently dropped or presented as a deployable winner.

