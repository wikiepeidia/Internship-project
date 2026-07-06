# Phase 30: AC Cold-Latency Measurement & Comparison

**Recorded:** 2026-07-06
**Evidence artifact:** `30-latency-ac-high-performance-evidence-20260706T015126Z.json`

## Battery/Balanced Measurement — Descoped

Per D-10 (SUPERSEDED 2026-07-06), the battery/Balanced-plan measurement was descoped by operator decision: the presentation laptop runs 1-2h on battery, and a charger-backup plan covers the defense-day worst case. This is recorded here explicitly, not silently omitted. Only the AC/High Performance post-reboot measurement below satisfies PERF-01/PERF-03.

## AC/High Performance Post-Reboot Evidence

- Power scheme confirmed active: `Performance` (GUID `27fa6203-3987-4dcc-918d-748559d549ec`) — matches High Performance requirement.
- Last boot time: `2026-06-20T19:38:09.5+07:00` (post-reboot session, per `--post-reboot-confirmed`).
- `run_purpose`: `evidence`. `post_reboot_confirmed`: `true`.

| Metric | Value |
| --- | --- |
| Page-ready time (server start → page loaded) | 4,909.3 ms |
| First `/api/analyze` request latency (scam) | 21,887.9 ms |
| Total time to first answer (page-ready + first request) | 26,995.3 ms (~27.0 s) |
| Second `/api/analyze` request latency (benign, same process) | 21,864.4 ms |
| First prompt verdict | `high-risk` / `bank_impersonation` — matches locked scam verdict |
| Second prompt verdict | `benign` / `benign` — matches locked benign verdict |

## Comparison Against Phase 28 Warm Baseline

Phase 28 measured the same locked scam prompt 5 times in a row within one already-running `vnphish demo` process (not post-reboot):

| Run | Phase 28 warm latency (ms) |
| --- | --- |
| 1 (first request in that session) | 22,705.6 |
| 2 | 17,091.2 |
| 3 | 16,353.2 |
| 4 | 16,658.5 |
| 5 | 16,820.5 |
| **Average of runs 2-5 (steady-state warm)** | **16,730.8** |

## Bottleneck Analysis

Two candidate explanations for total-to-first-answer latency: (a) a one-time cold-start/warm-up tax (page cache, model mmap, thermal ramp-up after reboot) that would show as a slow *first* request followed by faster subsequent ones, or (b) an intrinsic per-request inference cost that is roughly constant regardless of process/session warmth.

The evidence favors (b), not (a):

- Within this single cold-boot session, request 1 (scam, 21,887.9 ms) and request 2 (benign, 21,864.4 ms) are nearly identical — there is no "slow first request, fast second request" pattern that a one-time warm-up tax would produce.
- Phase 28's own **first** request in an already-warm process was 22,705.6 ms — the same order of magnitude as today's cold-boot requests — while only requests 2-5 in that same warm session dropped to ~16.3-17.1 s.
- Page-ready time (4.9 s, covering process launch + `doctor()` model warm-up before serving) is small relative to the ~22 s per-request cost — the dominant cost is generation time per request, not server/model startup.

This points toward per-request CPU-bound decode cost (consistent with `GGUFAnalyzer`'s CPU-only config: `n_gpu_layers=0`, no explicit `n_threads`) as the larger contributor, and reboot/cold-cache effects as a secondary, unisolated factor (today's cold run is ~5 s slower than Phase 28's later warm-session runs, but this single data point cannot separate "cold cache" from ordinary run-to-run variance).

**Critically, no controlled diagnostic was run to isolate a specific GGUF parameter** (e.g., an explicit `n_threads` override compared against the current default) — this measurement establishes the true cold latency, not a parameter-level cause. Per D-05 ("no blind tuning — a code/config change is allowed only after measurements identify one specific bottleneck with enough evidence to justify it"), suspicion of `n_threads` is not the same as evidence of it.

See `30-fix-decision.md` for the resulting PERF-02 decision.
