# Phase 40 Local RTX 5050 Probe Report

Status: Both local decision branches are sealed. The ordinary-LoRA run retained an honest incomplete resource-pressure outcome; the separately dated genuine QLoRA probe reached its exact 5+40-step target, verified, and discarded every runtime/model artifact.

## Claim boundary

These runs are feasibility and resource evidence only. They are not completed full-training runs, an accuracy comparison, or proof that LoRA is impossible. The QLoRA ETA is an extrapolation from its bounded same-machine probe, not an observed full-run duration. The held-out partition was not used. No adapter or checkpoint from either disposable run may seed a later run.

## Environment and controls

- GPU: NVIDIA GeForce RTX 5050 Laptop GPU, 8,151 MiB reported device memory.
- System RAM: 33,943,490,560 bytes reported by telemetry (31.61 GiB).
- Base model: `Qwen/Qwen3-4B-Instruct-2507`, pinned revision `cdbee75f17c01a7cc42f958dc650907174af0554`, reused from the verified existing snapshot.
- Mode: genuine full-precision LoRA; the base was frozen and 504 adapter tensors were trainable. No four-bit mode or semantic fallback was used.
- Frozen run controls: sequence length 1,024; per-device batch 1; gradient accumulation 4; effective batch 4; planned 1,245 optimizer steps; five excluded warm-up steps; 40-step evidence target; cumulative 1,800-second soft and 3,600-second hard LoRA limits.
- Runtime stack used by the GPU process: Torch `2.12.0+cu132`, Transformers `5.9.0`, PEFT `0.19.1`, Accelerate `1.13.0`.

## Audited chronology

1. The first LoRA attempt ended before `Trainer` construction and before optimizer step 1 because Transformers 5.9 normalized `warmup_ratio=0.03` into its new `warmup_steps=0.03` representation. Its strict verifier still expected the older raw representation `warmup_steps=0`. That attempt retained zero optimizer steps, peaked at only 76 MiB device VRAM, and classified memory pressure as not proven. It is infrastructure compatibility evidence, not a memory result.
2. Commits `62b2f1e` and `803c3b3` added semantic Transformers 5.9 verification and one hash-sealed retry. The original outcome, ledger entry, clock, and cumulative LoRA limits were preserved; 35.656 seconds from attempt 1 were deducted from the retry limits.
3. The retry used stage `lora-retry-1` and run ID `rtx5050-lora-retry-1` under the original decision clock. It retained 31 optimizer-step events: five warm-up and 26 measured steps.
4. At the cumulative soft boundary, the extension gate sampled during a long in-flight optimizer step. The last optimizer event was 24.218 seconds old, while the controller's progress-freshness limit was four seconds. Although the median step was about 53 seconds and the remaining 14 target steps fitted both the hard and global limits, the one-shot gate did not extend.
5. The 15-second boundary-stop grace was shorter than a normal optimizer step, so the child ended without a canonical `run_end`. Terminal telemetry records the literal reason `parent_controller_error`. The original controller exception was not retained; a later Windows `Access is denied` while removing an empty read-only OneDrive runtime directory masked it. A termination race is a plausible diagnosis, not a proven fact.
6. Recovery commits `e8eb645` and `edb3ee8` performed no model load or training. They bound the original run code to commit `803c3b3`, proved that no matching child process or model artifact remained, cleared only the bounded read-only runtime residue, verified its discard receipt, and sealed the literal error outcome. The recovery command is idempotent.

## Retained LoRA measurements

| Measure | Retained value | Interpretation |
|---|---:|---|
| Telemetry samples | 840 | Append-only samples over 1,782.206 seconds (29m42.206s) |
| Optimizer steps | 31 observed | 5 warm-up + 26 measured; target 40 was not reached |
| Measured step time | median 53.274s; mean 54.588s | Range 42.207–67.187s |
| Provisional 1,245-step compute ETA | median 18.42h; mean 18.88h | Extrapolation only; excludes evaluation/checkpoint overhead and is based on an incomplete 26-step window |
| Logged losses | finite | Four logged values decreased from 2.00825 to 0.63348; this is a runtime-health check, not an accuracy result |
| Device VRAM | peak 7,902 / 8,151 MiB; minimum 9 MiB free | Sustained device-memory pressure |
| Pressure evidence | 826 consecutive qualifying samples | Far exceeds the declared three-sample `>=95% used` and `<=512 MiB free` predicate |
| Torch memory | peak allocated 9,700,071,424 bytes; peak reserved 13,400,801,280 bytes | Torch-reported allocator values are retained as measured; they are not relabeled as physical VRAM |
| Process RSS | peak 7,677,739,008 bytes (7.15 GiB) | Training-process host memory |
| System RAM | peak used 22,479,200,256 bytes; minimum available 11,464,290,304 bytes (33.77%) | No sustained system-RAM pressure under the declared `<=10% available` predicate |
| GPU utilization | peak 100% | The GPU was actively computing |
| Temperature / power | peak 61C / 28.70W | No thermal-stop evidence |
| OOM | none observed | No CUDA or system out-of-memory exception was recorded |

The mechanical memory classifier is `gpu_pressure`, with basis `three_consecutive_samples_at_or_above_95pct_vram_and_at_or_below_512mib_free`. This supports the report wording "too memory-intensive on this 8 GiB configuration" in the practical headroom sense. It does not support "LoRA cannot run" or "LoRA OOMed": the model performed 31 optimizer steps and no OOM occurred.

## Decision

Ordinary LoRA is technically runnable on this laptop, but it operates with effectively no device-memory headroom and a provisional compute-only schedule near 18.4–18.9 hours. That makes a fresh full local LoRA run operationally unattractive for the current deadline. The separately dated QLoRA experiment below supplies the required independent measurement; its result supersedes any historical recollection about QLoRA speed.

For planning and defense wording, ordinary LoRA is therefore treated as too resource-intensive on the tested laptop. A **32 GB-class system-RAM configuration and more than 8 GB of VRAM are recommended** for a reliable full run with usable headroom. This is a practical recommendation, not a benchmarked strict minimum: telemetry observed 20.94 GiB peak system-RAM use on a 31.61 GiB host, while the 8,151 MiB GPU reached 7,902 MiB used and only 9 MiB minimum free. Likewise, the 18.42–18.88-hour figure is an incomplete-window compute extrapolation that excludes evaluation and checkpoint overhead; it does not guarantee that a full run would finish successfully. The bounded probe itself ended with `parent_controller_error` before its evidence-step target, although no OOM occurred.

The ordinary-LoRA handoff was sealed on 2026-08-24. No further ordinary-LoRA retry is authorized for that decision window.

## Separately dated genuine QLoRA probe — 2026-08-25

The fresh root `data/models/phase40/probes/rtx5050-qlora-session-20260825/` started a new immutable 7,200-second clock. Before model load it hash-linked the complete prior LoRA evidence tree, rebound the canonical train/validation snapshots and pinned Qwen base, bound the dated operator source, and reverified the approved `bitsandbytes==0.50.1` setup receipt. Every stage subsequently rechecked those identities.

The model-level proof resolved the requested mode as `4bit-qlora`: NF4 plus double quantization was active, 252 `Linear4bit` modules were present, the base weights were frozen, 504 adapter tensors were the only trainables, and the pre-step backward pass found 504 finite adapter gradients with 252 nonzero gradients. There was no semantic fallback to ordinary LoRA.

| Measure | Retained value | Interpretation |
|---|---:|---|
| Optimizer steps | 45 observed | Exactly 5 excluded warm-up + 40 measured steps |
| Measured step time | median 3.462389s | Forty ordered post-warm-up measurements |
| Throughput | 1.12034 examples/s; 346.98349 tokens/s | Measured only over the retained 40-step window |
| Validation overhead | 57.9618s | One measured validation pass; `eval_loss=0.467213` is a runtime-health value, not a final accuracy claim |
| Checkpoint overhead | 1.113946s | One isolated measured save |
| Projected 1,245-step local runtime | 4,369.750238s (72m49.750s; 1.214h) | Median step time x 1,245 plus measured validation/save overhead; estimate only |
| Device VRAM | peak 7,516 / 8,151 MiB; minimum 395 MiB free | High utilization but no OOM and no declared pressure failure |
| Torch memory | peak allocated 5,993,058,304 bytes; peak reserved 7,646,216,192 bytes | Allocator telemetry, not relabeled as physical VRAM |
| Process RSS | peak 8,733,491,200 bytes (8.13 GiB) | Training-process host memory |
| System RAM | peak used 22,136,381,440 bytes; minimum available 11,807,109,120 bytes | No system-RAM OOM |
| GPU utilization / temperature / power | peak 97% / 89C / 90.36W | Sustained real GPU execution; no thermal stop was recorded |
| OOM | none observed | The exact evidence target completed |

The child completed with `measured / evidence_target_reached`. Its event verifier accepted exactly 45 ordered optimizer steps, one validation event, one checkpoint event, finite losses, and a canonical `run_end`. The controller then hashed and removed the disposable runtime; neither `runtime` nor any checkpoint directory remains. The final five-stage ledger and 22-artifact manifest reverify against the unchanged historical source tree.

The result shows that full QLoRA is locally feasible under the tested controls and is dramatically faster than ordinary LoRA on this laptop. It does not prove that a fresh 1,245-step run will finish in exactly 72.83 minutes, because the value is an extrapolation and longer-run overhead/thermal behavior may differ. Per the operator's execution choice, Phase 40 still ports the identical Qwen controls to a fresh step-zero Colab QLoRA run so the retained full logs, curves, checkpoints, validation outputs, and GGUF export share the canonical comparison workflow. Colab is therefore an evidence-packaging/reproducibility route, not justified by a false claim that this measured laptop QLoRA probe was too slow.

### Later routing note

After this immutable probe report was sealed, the operator changed the fresh full QLoRA route back to the laptop to preserve Colab credit. That later decision does not alter any probe measurement above. The full run starts independently at step zero, keeps the same frozen controls and evidence cadence, and is reported separately in `40-LOCAL-FULL-QLORA-REPORT.md`. If its complete bundle verifies, it satisfies the QLoRA full-run branch and is not repeated on Colab.

## Evidence references

- First attempt: `data/models/phase40/probes/rtx5050-local-decision/lora/`
- Audited retry authority and retained partial evidence: `data/models/phase40/probes/rtx5050-local-decision/lora-retry-1/`
- Retry optimizer-event SHA-256: `f7a7868d4b8643d36995dab28b123cfb3e3e4d52f0af44fcd244b36d3e0c50e7`
- Retry source code commits: `62b2f1e`, `803c3b3`; recovery code commits: `e8eb645`, `edb3ee8`.
- Recovery-seal SHA-256: `2dd2f94c907a7184d5a799862c0750c43649b29edcd52531383d4a0abca75abc`.
- Recovery-finalization SHA-256: `e846e0640abdac3db05a00ef8bdc7ca142fea7c197c7cac261d7f04115d05f4a`.
- Final retry outcome SHA-256, as sealed in the append-only ledger: `749ac7523088726afa9fa27d8e3b575b5d5358e4bf26df549025b1dd55114a3f`.
- Runtime discard pre-image SHA-256: `aaf5f47cec79ecbb7aa13f29c210037b9b7865d61d1dbfcf01d36d19f2d31871`; the receipt verifies `runtime` is absent.
- Final verification: recovery idempotence PASS; Python compilation PASS; `git diff --check` PASS; model-adaptation tests 455/455 PASS.

### QLoRA evidence references

- Dated session root: `data/models/phase40/probes/rtx5050-qlora-session-20260825/`.
- Operator source SHA-256 bound at preflight: `1787da088ff5d31cbcf439e4b9c7ef76809e6701ba1da5c2f706a4b15760868c`.
- Historical LoRA source-tree SHA-256 before/after every stage: `46bce0f7e3807f62465c84492e524327e0df9b5cf8beaf938bd7f101109e9271`.
- QLoRA optimizer-event SHA-256: `60e8c573e9763cab0f8073a47889ea678c69309d1defa3247e2ee671383bee72`.
- Quantization-proof SHA-256: `aca5a27ecbcf47f25500e5ec011566caa6478e6253a78eb5451a0d4ca93cd4ef`.
- Telemetry SHA-256: `d0a3cdf734a92977070b4efee348087c6c475d32a33d281e2a2896e0439cf3a0`.
- Outcome SHA-256: `456d385e48fe0cf63e89c4aa5714aa016c93bb3b846c50f86fd3dee68213edce`.
- Final ledger SHA-256: `418403f154f9efaa7ad71c8aeb44d8bd68088b44dad7d3b386fda71822f640a3`.
- Session-manifest SHA-256: `ef992ddd7f0af03df2ca44c352f044e042d5d9c963afa7b89366ec22aeb4a795`.
- Final verification: session verifier PASS; runtime absent; checkpoints absent; GPU memory released.
