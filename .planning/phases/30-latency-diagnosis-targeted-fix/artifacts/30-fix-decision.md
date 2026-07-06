# Phase 30: PERF-02 Fix Decision

**Decision:** `NO_FIX_APPLIED`

## Rationale

Per D-05 ("no blind tuning — a code/config change is allowed only after the first measurements identify one specific bottleneck with enough evidence to justify it"), a fix requires evidence isolating a specific cause, not plausible suspicion.

The single AC post-reboot measurement (see `30-latency-comparison.md`) shows:

- Per-request latency (~21.9 s) is roughly constant across the first and second request in the same cold-boot session — no distinct one-time warm-up spike that a targeted warm-up fix could address.
- The cold-boot per-request cost (~21.9 s) is close in magnitude to Phase 28's own first-request-in-session cost (22.7 s warm), and only moderately above Phase 28's steady-state warm average (16.7 s) — the gap is small enough that it cannot be confidently attributed to a single isolated parameter without a controlled before/after comparison.
- **No diagnostic run was performed to isolate a specific GGUF parameter** (e.g., comparing default `n_threads` behavior against an explicit override). Without that isolating evidence, applying a fix now would be exactly the "blind tuning" D-05 forbids.

This matches Fix Gate row 1 from `30-RESEARCH.md`: *"Startup/model warm-up dominates but no code-level bottleneck is isolated → Record true latency; no fix applied."* The measurement instead shows per-request generation cost dominates over startup cost, but that per-request cost is not isolated to one specific, fixable parameter by this evidence alone.

## What This Closes

- **PERF-01** (true cold-boot-to-first-answer latency measured): CLOSED. Recorded: ~27.0 s total to first answer, ~21.9 s per-request, under AC/High Performance post-reboot conditions.
- **PERF-02** (targeted fix only if a bottleneck is found): CLOSED as `NO_FIX_APPLIED` — no code/config change made to `src/runtime/analyzers/gguf.py` or elsewhere.
- **PERF-03** (latency verified under power conditions): CLOSED for AC/High Performance. Battery/Balanced is explicitly descoped per D-10 (SUPERSEDED) — accepted risk (laptop battery life + charger backup), not a measured requirement.

## For Phase 32 (Fallback & Rehearsal)

The honest cold-boot narration figure is **~27 seconds to first answer** (not the earlier ~13s warm figure from Phase 7b, which only applies to an already-running, previously-warmed process). Phase 32's rehearsal script and presenter narration should use this cold figure, since the live defense demo will be a cold/first-run scenario, not a warm one.
