# Phase 30: Latency Diagnosis & Targeted Fix - Research

**Researched:** 2026-07-05
**Domain:** Windows laptop cold-start latency measurement for a local Python `wsgiref` + GGUF/llama.cpp demo
**Confidence:** HIGH for code-path findings, MEDIUM for fix candidates until post-reboot AC/battery measurements exist.

## Summary

Phase 30 should be treated as a measurement-first phase. The repository already has a browser-driven verifier (`scripts/verify_golden_prompts.py`) and warm browser timing evidence from Phase 28, but it does not measure true cold-boot-to-first-answer latency. The important code-path finding is that `vnphish demo` deliberately warms the GGUF backend before the server starts accepting browser traffic: `run_demo_server()` builds the app, calls `app.service.backend.doctor()`, then starts `wsgiref`. Therefore a cold measurement must include server startup/model warm-up time as well as the first `/api/analyze` request time.

The main plausible code-level bottleneck visible in source is that `GGUFAnalyzer._load_runtime()` passes `n_ctx=512`, `n_gpu_layers=0`, and `verbose=False` to `llama_cpp.Llama`, but does not pass `n_threads`. That is only a candidate. It must not be changed unless the Phase 30 measurements or a follow-up diagnostic point to thread selection as the specific cause.

The agent can build a measurement harness and runbook autonomously, but cannot satisfy PERF-01/PERF-03 alone because those requirements explicitly depend on a real post-reboot first request and power-state changes on the presentation laptop. Those steps require a human checkpoint.

## Direct Findings

| Finding | Evidence | Impact |
| --- | --- | --- |
| `vnphish demo` warms the model before serving the page. | `src/runtime/demo.py` calls `app.service.backend.doctor()` before `make_server(...).serve_forever()`. | A cold measurement must time process launch through first answer, not just browser request latency. |
| `vnphish analyze` is not representative of the live demo path. | `src/runtime/cli.py` runs `run_runtime_doctor()` then builds a separate default runtime service. | Do not use CLI-only timing for PERF-01. |
| Existing Phase 28 timing is warm, not cold boot. | `28-golden-prompt-results.json` records first browser request `22705.562 ms` and subsequent warm requests around 15.7-17.1s. | Useful comparison baseline, but cannot close PERF-01. |
| GGUF runtime has no explicit `n_threads`. | `src/runtime/analyzers/gguf.py` `llama_cpp.Llama(...)` call omits `n_threads`. | Candidate targeted fix only after measurement supports it. |
| Power condition must be recorded with evidence. | ROADMAP/REQUIREMENTS require both AC/High Performance and battery/Balanced. | Harness should capture user condition labels and best-effort `powercfg /GETACTIVESCHEME` output. |

## Measurement Architecture

Use a dedicated script instead of overloading Phase 28's verifier. Phase 28 verifies stability through a warmed demo server; Phase 30 needs a cold-start evidence artifact with different semantics.

Recommended script: `scripts/measure_cold_latency.py`.

Recommended behavior:
- Reads locked golden prompts from `.planning/phases/28-baseline-readiness-zero-code-diagnostics/artifacts/28-golden-prompt-results.json`.
- Starts `python -m src.runtime.cli demo --no-browser --port <port>` as a script-owned subprocess.
- Starts the stopwatch before the subprocess launch.
- Uses Playwright to retry `page.goto()` until the demo page is reachable; this page-ready timestamp includes model warm-up because the server is not listening before warm-up finishes.
- Submits the scam prompt first, then optionally the benign prompt, through the real browser UI.
- Records:
  - condition label (`ac-high-performance`, `battery-balanced`, or diagnostic)
  - `post_reboot_confirmed`
  - process launch timestamp
  - page-ready elapsed time
  - total elapsed time to first answer
  - browser request timing for each `/api/analyze` response
  - risk tier and labels for each prompt
  - best-effort Windows power plan output
  - best-effort Windows last boot time
  - captured demo stdout/stderr after shutdown
- Writes one JSON artifact per run under `.planning/phases/30-latency-diagnosis-targeted-fix/artifacts/`.

Evidence-run guard:
- A run marked as evidence must require `--post-reboot-confirmed`.
- Non-reboot diagnostic runs are allowed but must be labeled `diagnostic` and cannot satisfy PERF-01.

## Human Runbook Requirements

The runbook should instruct the operator to perform two evidence runs:

1. AC/High Performance:
   - Plug in AC power.
   - Select High Performance or best-performance power mode.
   - Reboot.
   - Open a fresh terminal after login.
   - Run the measurement script with `--condition ac-high-performance --run-purpose evidence --post-reboot-confirmed`.

2. Battery/Balanced:
   - Unplug AC power.
   - Select Balanced power plan/mode.
   - Reboot.
   - Open a fresh terminal after login.
   - Run the measurement script with `--condition battery-balanced --run-purpose evidence --post-reboot-confirmed`.

The runbook should tell the user to report the two produced JSON artifact paths back to the agent. The agent then creates a comparison/decision record and either:
- records "no fix applied" if no specific bottleneck is identified, or
- stops for a targeted one-fix plan if the evidence points to exactly one measurable bottleneck.

## Fix Gate

No source change should happen before the AC and battery evidence exists.

Allowed outcomes:

| Evidence Result | Correct Action |
| --- | --- |
| Startup/model warm-up dominates but no code-level bottleneck is isolated. | Record true latency; no fix applied. |
| Request latency dominates and a single GGUF parameter is clearly implicated. | Apply one targeted GGUF fix, add a small unit test for the parameter, re-run before/after measurement. |
| AC and battery differ substantially but no application bottleneck is identified. | Record comparison; no app fix. Treat power-mode selection as rehearsal/runbook guidance for Phase 32. |
| Measurement artifacts are missing, not post-reboot, or mislabeled. | Do not close PERF-01/PERF-03; ask for rerun. |

## Verification Strategy

Automated before the human checkpoint:
- `python scripts/measure_cold_latency.py --help`
- Unit tests around prompt loading, argparse evidence guard, latency extraction, and artifact path construction.

Human after checkpoint:
- Two JSON artifacts exist, one AC/High Performance and one battery/Balanced.
- Both artifacts have `run_purpose=evidence` and `post_reboot_confirmed=true`.
- The first prompt result is the locked scam verdict: `high-risk` + `bank_impersonation`.
- The comparison record explicitly decides whether a fix is justified.

## Open Questions

None that should block building the harness. The exact targeted fix, if any, is intentionally deferred until the real measurements exist.

## Sources

- `src/runtime/demo.py` -- demo warm-up and server start order.
- `src/runtime/cli.py` -- CLI/demo entrypoint differences.
- `src/runtime/analyzers/gguf.py` -- llama.cpp runtime construction.
- `scripts/verify_golden_prompts.py` -- existing Playwright pattern and request timing helper.
- `.planning/phases/28-baseline-readiness-zero-code-diagnostics/artifacts/28-golden-prompt-results.json` -- locked prompts and warm latency.
- `.planning/phases/29-environment-parity-offline-verification/29-VERIFICATION.md` -- presentation laptop and offline environment verified before this phase.
