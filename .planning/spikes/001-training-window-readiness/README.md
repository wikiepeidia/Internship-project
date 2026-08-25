---
spike: 001
idea: phase40-idle-readiness
name: training-window-readiness
type: standard
validates: "Given the live QLoRA chain and model-evaluation boundary, when authorities, process/controller state, and downstream contracts are checked without GPU work or further reserved-content access, then launch blockers are exposed and safely contained before PhoBERT and Phase 41."
verdict: PARTIAL
related: []
tags: [phase40, phobert, phase41, safety-gate]
---

# Spike 001: Training-Window Readiness

## What This Validates

Given the active local Qwen QLoRA run, its fail-closed supervisor, the armed Qwen-to-PhoBERT controller, and the reserved Phase 41 model-evaluation boundary, determine whether non-GPU preparation can remove launch and evaluation risks without changing the running experiment or further accessing reserved content. Phase 39 human review and the thesis already exposed test content, so this spike does not claim literal human blindness.

## Research

This is a repository- and runtime-contract question with no new external dependency. The spike therefore uses the project's existing frozen JSON authorities, controller logs, PowerShell syntax parser, standard-library Python, and model-adaptation tests instead of web research or a new package.

| Approach | Tool | Pros | Cons | Status |
|---|---|---|---|---|
| Execute PhoBERT now | Existing trainer | Direct runtime proof | Would compete with QLoRA and violate the no-overlap contract | Rejected |
| Readiness-only static/runtime audit | Existing authorities plus `check_readiness.py` | No GPU competition; repeatable; no reserved-content access by the checker | Cannot prove the future full training run succeeds | Chosen |
| Fresh-only v8 containment | Clean extraction, exclusive controller lease, per-launch source preflight, parsed controller, and terminal telemetry seal | Preserves the immutable v3 training source while bypassing known-broken resume routes | A fresh PhoBERT interruption remains terminal and must be reported | Chosen |
| Synthetic one-shot evaluator prototype | Standard-library Python plus temporary synthetic JSONL | Proves durable claim-before-open and terminal two-model metrics without touching real test data | Still requires production model adapters after both Phase 40 models freeze | Chosen |
| Wait without preparation | None | Zero change risk | Defers preventable failures until the deadline-critical handoff | Rejected |

## How to Run

```powershell
python .planning/spikes/001-training-window-readiness/check_readiness.py `
  --repo-root .
```

Run the synthetic-only one-shot tests:

```powershell
python .planning/spikes/001-training-window-readiness/test_phase41_one_shot_prototype.py
```

Run the synthetic comparison-authority preflight tests:

```powershell
pwsh -NoProfile -File `
  .planning/spikes/001-training-window-readiness/test-comparison-authority-preflight.ps1
```

## What to Expect

The checker emits one JSON document. `verdict` is `PASS` only when fixed authority hashes, the complete amendment/request/config binding, base-model provenance content, retained PowerShell parse receipt, clean-runtime preflight, the exact live `FileShare.None` controller lease, empty controller output/error captures, fresh-only resume policy, and exact PID/creation-time/executable identities pass. It deliberately does not discover or inspect the reserved split and does not load a model.

## Observability

The JSON output includes a timestamp, every named check, its severity, exact evidence, and every file opened by the checker with SHA-256. The command exits nonzero when any blocking check fails. The retained run summary is `READINESS-RESULT.md`; the canonical spike index is the parent `.planning/spikes/MANIFEST.md`.

## Investigation Trail

1. The last durable trainer progress line records QLoRA step 850/1,245. At 2026-08-25T19:11:08+07:00, trainer PID 19772, supervisor PID 1576, and telemetry PID 15308 were still alive; telemetry recorded 7,812/8,151 MiB VRAM, 50% instantaneous GPU utilization, and 62 C. No second GPU workload was started.
2. The Phase 40 PhoBERT controls were confirmed to contain only the 1,658-row training and 219-row validation members, with local-only model loading, revision pinning, FP16, batch 16, sequence length 256, and 312 planned optimizer steps.
3. Independent audit found that v3 PhoBERT resume always fails locally: it selects the Colab archive path, hashes the placeholder accelerator instead of the actual GPU identity, and receives forbidden absolute Windows arguments. v3 also lacked proof of the extracted runtime immediately before launch.
4. The idle predecessor controllers were replaced without touching the Qwen trainer, supervisor, or telemetry recorder. Controller v8 (PID 13180, creation FILETIME `134321337277925629`, SHA-256 `473fb1ae8c4ed154bbf918232ef79fbb04cb4cbeca9b2555fe7adb662812c9e4`) holds one exclusive fixed-path lease, uses a clean 28-file extraction, re-verifies the full source immediately before every Python child, pins and parses the telemetry script, proves an invocation-unique bytecode-cache path absent, and locks automated resume to zero. Three fresh-target gates close the long-wait and doctor windows, any nonzero training exit fails before evidence verification, and the terminal telemetry seal binds sampler start to wrapper process creation while rejecting missing coverage, gaps over 30 seconds, elapsed-clock drift, malformed PID sets, early/nonzero exits, stderr, or unverified summaries.
5. The readiness checker was tightened after peer review: caller-supplied controller/PID authority was removed, full authorities and process creation identities are pinned, reparse ancestors are rejected, the exact Win32 sharing-violation lease proof is required, locked zero-byte controller captures are checked as metadata, the cache path is rechecked absent, opened versus metadata-only files are reported, and claims are scoped to checker actions. The retained v8 check passes 20/20 blocking checks.
6. A Phase 41 prototype now proves `PREPARED -> EXPLICITLY_AUTHORIZED -> SPENT -> COMPLETED|SPENT_FAILED`, with one SHA-keyed canonical claim created before the sole injected opener. Both frozen predictors share one immutable in-memory snapshot that exposes only sequence index, text, and a text-derived opaque row ID; label-bound source/split hashes remain private. Thirteen synthetic tests cover replay across output roots and copied split paths, concurrency, post-claim failure, metric behavior, authority-bound label support, resealed-result tampering, and fixed-order Qwen/PhoBERT confusion-matrix reporting including `invalid_output`. Stored prediction rows retain raw-output hashes/lengths rather than content that could echo reserved messages. Callback counts are prototype contract evidence only: the production executor must own the OS file handle and freeze/hash each model's complete inference protocol (prompt/parser/decoder for Qwen; segmenter/tokenizer/preprocessing/label map for PhoBERT). The prototype registry is repository-local; production must anchor the SHA-keyed claim in protected persistence outside the mutable checkout so copying/deleting the checkout cannot authorize a replay.
7. The comparison-authority PowerShell gate rejects duplicate JSON keys, source/path/reparse drift, and existing or concurrent receipt writers; it binds its own script hash and creates the receipt with `FileMode.CreateNew` plus durable flush. Seven synthetic temporary-fixture tests pass without Python, model, or dataset access. This remains a spike gate, not the final production authority: Plan 40-05 must first materialize the reviewed comparison source into a separate clean root, bind this preflight's own expected hash, and launch isolated Python immediately from that exact root so unlisted startup/import code cannot intervene.

## Results

**PARTIAL.** Fresh-only PhoBERT launch readiness and the one-shot evaluation state machine are validated. The original unattended resume claim is invalidated and disabled; if fresh PhoBERT stops or post-training finalization fails, the run must be preserved and reported rather than silently resumed. This limitation does not block the currently armed fresh attempt, but it prevents a full `VALIDATED` verdict for restart/resume resilience.
