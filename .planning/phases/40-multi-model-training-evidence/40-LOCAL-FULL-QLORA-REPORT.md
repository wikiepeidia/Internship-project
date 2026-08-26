# Phase 40 Local Full QLoRA Run

> **Historical execution log (not current status).** The time-stamped sections below intentionally preserve what was known while training was live. Both local models later completed successfully, the frozen validation comparison and Vietnamese review closed, and the Colab contingency was not used. For current completion claims, use `40-VALIDATION-COMPARISON.md`, `40-VIETNAMESE-ERROR-REVIEW.md`, and `40-VERIFICATION.md`.

**First attempt started:** 2026-08-25 08:59 +07:00

**Clean v3 run started:** 2026-08-25 10:21 +07:00

**Status:** Qwen QLoRA running unattended; verified Qwen-to-PhoBERT continuation armed. This is an in-progress execution record, not a completion claim.

## Authority and route

The operator selected a fresh step-zero full QLoRA run on the RTX 5050 after the bounded probe proved genuine four-bit training feasible. No probe adapter, checkpoint, or event stream was reused. The run consumes only the canonical 1,658-row training and 219-row validation members from the train/validation-only archive. The reserved evaluation partition remains outside this run.

- Package root: `D:\PROJEct\AI MODELS\phase40-full-local-20260825`
- Active immutable result root: `transfer-root-v3\data\models\phase40\full\qwen-qlora`
- Active mutable trainer root: `work-v3\phase40-qwen-qlora-full-seed42-v1\phase40-comparison\qwen3-4b-instruct-2507\trainer`
- Active source runtime: `source-runtime-v3`
- Request SHA-256: `2512dbe6d7c5b8c16141ebdbdc848382e56b3a5737e8aeea51d7fb89447c643a`
- Source archive SHA-256: `eae64f17383d749a7759391d766ad59b337d35155ae89744adeaba8631e71a66`
- Source inventory SHA-256: `5903dd5d68881916424e0b529760c3e8810b89a7c207aa714f13171fccf02a3d`
- Input archive SHA-256: `12136f9a79e7c9852f6b317f284a9a018710aa66af54de4714ec66e8cf92bf84`
- Base revision: `cdbee75f17c01a7cc42f958dc650907174af0554`
- Supervisor source SHA-256: `43c4b9db4923ba601f06fa01130f85f74313731a5954a6f86c5d6039d796675b`
- Telemetry logger SHA-256: `1bc33f3726b57297a3cc5a69b36831bbd602edac680ba329224b14cf06231c70`

The sealed v3 package passed its deterministic preparation verifier, request/source/input verifier, and QLoRA doctor before launch. The doctor confirmed CUDA, `bitsandbytes==0.50.1`, the pinned base snapshot, and genuine four-bit run identity without downloading or replacing the model.

## Preserved v2 attempt and restart reason

The first local attempt was not discarded or rewritten as a success. It reached materially complete checkpoints 50 and 100 carrying adapter, optimizer, scheduler, RNG, trainer state, resume manifest, and sealed history. Neither checkpoint was admitted for an actual resume after the full verifier exposed the two operator defects below. Checkpoint 50 produced 219 ordered predictions with 192 correct and zero invalid outputs (87.67% validation accuracy). Checkpoint 100 produced 210 correct predictions with one invalid output (95.89% validation accuracy). These are intermediate validation observations, not final-model claims.

Exact-resume testing then exposed two operator defects:

1. The mutable output root omitted the run ID, so the strict resume verifier correctly rejected the checkpoint as outside its run-scoped work root.
2. The operator reconstructed the controlled configuration through Python-object validation even though the sealed JSON contains enum and tuple representations; the backend's canonical JSON validator was already correct.

The trainer was intentionally interrupted during the step-150 validation boundary so the defects could be repaired before a real crash required recovery. Its append-only terminal event records `failure_category=interrupted`, `error_type=KeyboardInterrupt`, step 150, and resource-state SHA-256 `94abbbcedaf57f8a106404d6d333687a68c29c3a33221c7c331b3950ee5f4c05`. The stopped event stream SHA-256 is `103db67231afffd71d19530ca09439cb02d3deb559fc21499f8557e5502deb2b`; the v2 system-telemetry SHA-256 is `d80171a8172170d2fc30ce61c9d4cfffd6ad98edaa4a55c84775bfcd01eac667`. The stopped mutable tree is preserved under `resume-work-v2\phase40-qwen-qlora-full-seed42-v1`; its telemetry remains `controller\system-telemetry.csv`. No v2 checkpoint is reused by v3.

The repairs make the mutable output and registry run-ID scoped and make the operator call the same canonical JSON validation boundary as the backend. Focused regression passed before a new request/source package was sealed. A clean v3 run was chosen over hot-patching and resuming v2 so the active result has one unambiguous source authority from step zero.

## Frozen training controls

The run uses genuine NF4 QLoRA with double quantization, BF16 compute, LoRA rank 16, alpha 32, dropout 0.05, batch size 1, gradient accumulation 4, effective batch 4, three epochs, and 1,245 planned optimizer steps. Logging occurs every 10 steps; validation and checkpoint generation occur every 50 steps and at the final step. Every sealed checkpoint must produce ordered predictions for all 219 validation rows.

## Clean v3 live snapshot

At 2026-08-25 10:25 +07:00, trainer PID 19772 had completed optimizer step 50. The initial single-step log reported loss 1.926; the five successive 10-step windows ending at steps 10, 20, 30, 40, and 50 reported 1.589, 0.8664, 0.7249, 0.6687, and 0.5759. The ordinary 219-row pass then completed with `eval_loss=0.4666831791` in 54.1474 seconds, and `checkpoint-50` was saved before deterministic prediction generation began. The optimizer portion reached step 50 in about 167 seconds; batch-one prediction generation remains the expected wall-time bottleneck. The earlier v2 cadence supports a conservative 12–13-hour full-run estimate if every 50-step generation pass remains similarly slow.

At 2026-08-25 11:28 +07:00, step-100 generation had completed and optimization had resumed at step 122 of 1,245. Step-100 `eval_loss` improved to `0.4101715684`; its ordered 219-row generation contained zero invalid outputs and 213 correct predictions (`97.2603%` validation accuracy). This remains an intermediate observation, not a final-model score. Trainer PID 19772, telemetry PID 15308, and supervisor PID 1576 were alive, with no failure event, traceback, OOM, or runtime error. The observed 50-step generation cadence moved the estimated Qwen training finish to approximately 23:30--00:30 +07:00, followed by an estimated 0.5--1.5 hours for evidence finalization and GGUF conversion; both are planning estimates only.

The first telemetry implementation was caught writing blank GPU fields because one `nvidia-smi` line was incorrectly indexed as a character. The four invalid startup samples and buggy logger are preserved as `controller\system-telemetry-v3-startup-invalid.csv` and `controller\phase40-system-telemetry-v3-startup-buggy.ps1`. Training was not interrupted. The corrected logger and supervisor were reattached at 10:22 +07:00.

The corrected telemetry's first 17 samples recorded peak device use 7,512 MiB, minimum free device memory 399 MiB, peak GPU temperature 80C, peak Python RSS 2,360,541,184 bytes, and peak system-RAM use 16,356,241,408 bytes. These are running values, not the final seal. No OOM, NaN, data-contract failure, or thermal stop had occurred.

The earlier 72.83-minute probe figure must not be presented as this run's
end-to-end duration. It extrapolated 1,245 optimizer steps and added only one
measured validation/save overhead. This full evidence contract generates all
219 ordered validation predictions at every 50-step checkpoint and at the
final step. The observed live cadence therefore projects roughly 12.85 hours
for the complete evidence pipeline, with generation rather than optimization
dominating wall time. Because the run is still live, that figure and every
resource/quality snapshot in this section are interim until the final bundle
and telemetry summary verify.

## Unattended recovery and export

The active supervisor is `controller\phase40-full-local-supervisor-v3-run.ps1`; its append-only attachment log is `controller\supervisor-v3-run.log`. If the trainer exits without complete evidence, it ignores any half-sealed checkpoint and permits at most two retries from the newest exact `checkpoint-N` containing both the resume compatibility manifest and sealed history. Every candidate must pass the strict request, input, base, run-ID, checkpoint-history, and hash verifier before resume.

After complete run evidence verifies, the supervisor merges the mechanically selected adapter into the pinned ordinary base, converts Q8_0 with converter SHA-256 `f227273d926fd8ba1c5215ca9ba64d63e641b3277e6f225080b4aac434999b55`, verifies the GGUF manifest, and performs the pinned `llama-cpp-python==0.3.23` CPU load smoke. The final model is routed to `exports-v3\qwen-qlora-q8_0.gguf`; merge scratch stays in `gguf-work-v3`. The supervisor then stops only the exact telemetry logger and writes `controller\system-telemetry-summary-v3.json` with resource extrema and hashes.

## Queued local PhoBERT continuation

At 2026-08-25 11:29 +07:00, hidden controller PID 10784 was armed from `controller\phase40-qwen-to-phobert-chain-v3.ps1` (SHA-256 `72504a49aa10dd7d81ff12f263503a0d6dcbea7d7e8b4d0e93446cf3b4382ae7`). It does not compete with the active Qwen process. It first waits for supervisor PID 1576 to terminate, then requires Qwen's final telemetry status to be `complete`, independently re-verifies the immutable Qwen run and GGUF manifest/load smoke, confirms the original trainer is gone, and requires three consecutive GPU-memory samples at or below 2,048 MiB before PhoBERT may start. Startup was verified from `controller\qwen-to-phobert-chain-v3.log`; controller stderr was empty.

The exact `vinai/phobert-base-v2` revision `e966aac8cb889325e073aa5f28ff70aca4dbc8c3` is already present under `transfer-root-v3\data\models\phase40\base\phobert-base-v2`. Its provenance manifest SHA-256 is `b94e490259cdb42f0fa6c177421519bb4a3944d2693e249bcf8e358cb92dc3f6`, and the snapshot-content SHA-256 is `7f84123042ddb5c78ea174a3a4b8951ca6714321bf7b902641157bf155093ae6`. The sealed v3 doctor passed CUDA, dependency, request, input, base-snapshot, and provenance checks before the chain was armed.

If admitted after Qwen, PhoBERT starts a fresh three-epoch classification-head run with the frozen batch size 16, maximum sequence length 256, FP16 controls, and 312 planned optimizer steps. Mutable output is isolated under `phobert-work-v3\phase40-phobert-full-seed42-v1`; immutable evidence returns to `transfer-root-v3\data\models\phase40\full\phobert`; telemetry is written separately to `controller\system-telemetry-phobert-v3.csv`. At most two resumes are allowed, each from an exact sealed `checkpoint-N` only after strict resume verification. Completion additionally requires graph rendering and a second full run-evidence verification. The configuration is preflighted but has not yet had a real VRAM probe; an OOM is preserved as a failed run rather than hidden by changing controls. The planning allowance is 15--45 minutes, with 60 minutes reserved.

## User-approved two-model comparison handoff — 2026-08-25

The primary quality comparison now admits exactly the two completed local bundles under `transfer-root-v3`: Qwen QLoRA and PhoBERT. Additive authority is `data/models/phase40/two-full-model-scope-amendment.json`, bound to immutable request SHA-256 `2512dbe6d7c5b8c16141ebdbdc848382e56b3a5737e8aeea51d7fb89447c643a`. Immutable `source-runtime-v3` remains the authority for the active training, GGUF, and PhoBERT chain and must never be patched with the later two-model finalizer. Comparison finalization instead requires a post-amendment repository tree whose exact allowlisted files verify against `comparison_finalizer_authority.source_tree_sha256` embedded in the amendment; that verified tree is a separate authority, not v3. Absolute D-drive paths remain outside the portable evidence identity. The immutable earlier request and its historically named `ColabOperatorReturn` schema are retained as provenance; their dormant Qwen LoRA slot is not proof of execution and is not a required comparison row under this dated scope amendment.

| Run | Execution origin | Canonical root under `transfer-root-v3` | Accelerator |
|---|---|---|---|
| Qwen QLoRA | Active local v3 run | `data/models/phase40/full/qwen-qlora` | NVIDIA GeForce RTX 5050 Laptop GPU |
| PhoBERT | Queued local v3 run after verified Qwen/GGUF completion | `data/models/phase40/full/phobert` | NVIDIA GeForce RTX 5050 Laptop GPU |

The generated Colab handoff remains historical contingency documentation and was not executed. It is not part of the primary chain and does not authorize full ordinary LoRA. A QLoRA or PhoBERT contingency may be considered only if development-validation review is unacceptable and only before the reserved Phase 41 partition is opened. A held-out result may never be used to trigger Colab training, dataset repair, or checkpoint reselection. Windows platform, sanitized commands, and the actual laptop hardware remain in the local run evidence.

## Remaining completion gates

- Trainer reaches the complete 1,245-step lifecycle or a verified exact resume completes it.
- `phase40-verify-run-evidence` accepts the immutable QLoRA bundle.
- Selected checkpoint, 219-row predictions, metrics, graphs, and adapter hashes all reconcile.
- Q8_0 GGUF export and manifest verification pass, including the CPU load smoke.
- Final telemetry is stopped and hash-sealed.
- The queued PhoBERT run verifies, renders graphs, and seals its dedicated telemetry, or preserves an explicit terminal failure for review.
- The two-model QLoRA-versus-PhoBERT validation comparison and Plan 40-06 review remain separate open work; this unattended chain alone does not complete Phase 40.
- No full ordinary-LoRA run remains: its sealed bounded probe is the final resource/ETA evidence for that branch.
