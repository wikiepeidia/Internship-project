# Phase 40 Local Full QLoRA Run

**Started:** 2026-08-25 08:59 +07:00
**Status:** Running unattended; this file is an in-progress execution record, not a completion claim.

## Authority and route

The operator selected a fresh step-zero full QLoRA run on the RTX 5050 after the bounded probe proved genuine four-bit training feasible. No probe adapter, checkpoint, or event stream was reused. The run consumes only the canonical 1,658-row training and 219-row validation members from the train/validation-only archive; Phase 40 does not open the reserved test partition.

- Package root: `D:\PROJEct\AI MODELS\phase40-full-local-20260825`
- Immutable result root: `transfer-root-v2\data\models\phase40\full\qwen-qlora`
- Mutable trainer root: `work-v2\phase40-comparison\qwen3-4b-instruct-2507\trainer`
- Request SHA-256: `93b49371db184f28b2fb362da94ce99298f64487820176d2b10f65871ed3b8b8`
- Source archive SHA-256: `f7566931dfb6f28471dc0ca97c71e21eec4ae5a50471cc088794185816ba3e85`
- Input archive SHA-256: `12136f9a79e7c9852f6b317f284a9a018710aa66af54de4714ec66e8cf92bf84`
- Base revision: `cdbee75f17c01a7cc42f958dc650907174af0554`
- Supervisor source SHA-256: `9ecc6ba3100a3e1119aecd8f0069b79c55ab98410e018ee698ee53153f5d8584`

The v2 request was re-sealed after fixing a Windows portability contradiction: raw evidence correctly rejects personal absolute paths, while the backend requires normalized absolute base-model paths. The operator now records sanitized relative arguments but resolves the base path internally. Focused operator regression passed 22/22 before launch.

## Frozen training controls

The run uses genuine NF4 QLoRA with double quantization, BF16 compute, LoRA rank 16, alpha 32, dropout 0.05, batch size 1, gradient accumulation 4, effective batch 4, three epochs, and 1,245 planned optimizer steps. Logging occurs every 10 steps; validation and checkpoint generation occur every 50 steps and at the final step. Every checkpoint produces ordered predictions for all 219 validation rows.

## Verified live evidence snapshot

Checkpoint 50 completed and is exact-resume safe: adapter, optimizer, scheduler, RNG state, trainer state, compatibility manifest, and sealed resume history are present. Its ordinary validation pass reported `eval_loss=0.4636` over 219 rows in 56.86 seconds. The checkpoint-specific prediction artifact contains exactly 219 ordered rows, all parse successfully, and 192 match their gold label (87.67% validation accuracy; no final-model claim).

The interval from optimizer step 50 to resumed step 51 was about 28 minutes 52 seconds. The 56.86-second loss pass was small relative to sequential batch-one deterministic generation, so validation generation—not optimization or memory—is currently the wall-time bottleneck. Step 100 later reported `eval_loss=0.4157`; its prediction generation was still running when this snapshot was written. The conservative initial end-to-end estimate is roughly 12–13 hours if later generation passes remain as slow as checkpoint 50.

Telemetry snapshot through 2026-08-25 09:48:57 +07:00 (not final): 324 samples; peak device use 7,512 MiB; minimum device free memory 399 MiB; peak GPU temperature 79C; peak GPU power 85.84W; peak Python RSS 8,992,821,248 bytes; peak system-RAM use 21,781,864,448 bytes. No OOM, NaN, data-contract failure, or thermal stop had occurred. The final supervisor seal will replace this running snapshot with complete hashes and extrema.

## Unattended recovery and export

The hidden supervisor is copied under `controller\phase40-full-local-supervisor-v3.ps1`; its append-only attachment log is `controller\supervisor.log`. If the trainer exits without complete evidence, it ignores any half-sealed checkpoint and permits at most two retries from the newest exact `checkpoint-N` containing both the resume compatibility manifest and sealed history. It never uses a lexical `latest` target.

After complete run evidence verifies, the supervisor merges the mechanically selected adapter into the pinned base, converts Q8_0 with converter SHA-256 `f227273d926fd8ba1c5215ca9ba64d63e641b3277e6f225080b4aac434999b55`, verifies the GGUF manifest, and performs the pinned `llama-cpp-python==0.3.23` CPU load smoke. It then stops only the exact telemetry logger and writes `controller\system-telemetry-summary.json` with resource extrema and hashes.

## Remaining completion gates

- Trainer reaches the complete 1,245-step lifecycle or a verified exact resume completes it.
- `phase40-verify-run-evidence` accepts the immutable QLoRA bundle.
- Selected checkpoint, 219-row predictions, metrics, graphs, and adapter hashes all reconcile.
- Q8_0 GGUF export and manifest verification pass, including the CPU load smoke.
- Final telemetry is stopped and hash-sealed.
- Full LoRA, PhoBERT, the three-model validation comparison, and Plan 40-06 review remain separate open work; this run alone does not complete Phase 40.
