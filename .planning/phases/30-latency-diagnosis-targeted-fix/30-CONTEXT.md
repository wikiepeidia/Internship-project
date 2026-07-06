# Phase 30: Latency Diagnosis & Targeted Fix - Context

**Gathered:** 2026-07-05
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase measures true cold-boot-to-first-answer latency on the already-verified presentation laptop, under AC/High Performance power (battery/Balanced descoped per D-10). It may apply exactly one targeted latency fix only if the measured evidence points to one specific bottleneck. If the measurements do not identify a clear cause, this phase records the baseline and explicitly applies no fix.

This phase does not redesign the backend/API contract, change prompts or labels for correctness, fix UI quirks, resolve CLI `analyze` vs `demo` confusion, or create fallback recording assets. Those are either frozen constraints or owned by Phases 31 and 32.

</domain>

<decisions>
## Implementation Decisions

### Measurement Protocol
- **D-01:** Measure the real committee-facing path through `vnphish demo` and the browser `POST /api/analyze` flow, using the same locked Phase 28 golden scam and benign prompts. Do not substitute CLI-only timing, because `vnphish analyze` has a different model-load path and double-loads through doctor plus service creation.
- **D-02:** Cold-boot-to-first-answer means a post-reboot first successful browser analysis answer on the presentation laptop. Process-cold runs are useful diagnostic side evidence, but they cannot satisfy PERF-01 by themselves.
- **D-03:** Break timing into observable segments where practical: reboot/power condition, command launch time, model warm-up/server-ready time, browser page-ready time, first `/api/analyze` request latency, and total operator-visible time to first answer.
- **D-04:** Store raw machine-readable timing evidence and a human-readable summary under this phase's `artifacts/` directory. Evidence must name whether the run was AC/High Performance or battery/Balanced.

### Fix Gate
- **D-05:** No blind tuning. A code/config change is allowed only after the first measurements identify one specific bottleneck with enough evidence to justify it.
- **D-06:** If a bottleneck is found, apply exactly one targeted fix and re-run the same before/after measurement path. Candidate examples include explicit llama.cpp threading if `n_threads` default behavior is shown to be suboptimal, but the measurement result decides the fix.
- **D-07:** Do not combine multiple latency tweaks in one phase. No llama-cpp version upgrade, no prompt/schema redesign, no backend contract change, no batch of "maybe faster" options.
- **D-08:** If no clear bottleneck is found, record "no fix applied" as the correct outcome for PERF-02, with rationale and evidence.

### Human Checkpoint
- **D-09:** The agent must not fake the post-reboot, AC, or battery conditions. Build scripts/runbooks and stop for a human checkpoint when the laptop must actually reboot, unplug, or change power mode.
- **D-10 (SUPERSEDED 2026-07-06):** Originally required AC/High Performance then battery/Balanced. Descoped to AC-only: the laptop runs 1-2h on battery and a charger-backup plan covers the defense-day worst case, so battery-plan throttling is an accepted risk, not a measured one. Only the AC/High Performance post-reboot run is required to close PERF-01/PERF-03.

### the agent's Discretion
- Exact artifact filenames, JSON schema, and console output formatting for the measurement harness are at the agent's discretion, as long as they are simple to run from PowerShell and preserve raw timings.
- The planner may decide whether to extend `scripts/verify_golden_prompts.py` or add a separate Phase 30 script. Prefer a separate script if extending the Phase 28 verifier would blur warm stability verification with cold latency measurement.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & Roadmap
- `.planning/REQUIREMENTS.md` section "v5.1 Requirements -- Demo Verification & Presentation Readiness" -- PERF-01 through PERF-03.
- `.planning/ROADMAP.md` section "Phase 30: Latency Diagnosis & Targeted Fix" -- phase goal and success criteria.
- `.planning/STATE.md` hard constraints and v5.1 notes, especially "no blind tuning" and the Phase 7b warm-latency note.

### Prior Phase Evidence
- `.planning/phases/28-baseline-readiness-zero-code-diagnostics/artifacts/28-golden-prompt-results.json` -- locked golden prompt text/channel and warm browser timings.
- `.planning/phases/28-baseline-readiness-zero-code-diagnostics/artifacts/28-RESULTS.md` -- DIAG-03 warm-latency method and baseline.
- `.planning/phases/28-baseline-readiness-zero-code-diagnostics/28-01-SUMMARY.md` -- final prompt lock and Phase 30 comparison context.
- `.planning/phases/29-environment-parity-offline-verification/29-VERIFICATION.md` -- presentation-laptop/offline environment is verified before latency work starts.

### Source Code
- `src/runtime/demo.py` -- `run_demo_server()` builds the app, runs `app.service.backend.doctor()` as warm-up, then starts the WSGI server.
- `src/runtime/analyzers/gguf.py` -- GGUF runtime construction currently sets `n_ctx=512`, `n_gpu_layers=0`, and no explicit `n_threads`.
- `src/runtime/cli.py` -- `vnphish analyze` and `vnphish demo` entrypoint behavior differs.
- `src/runtime/service.py` -- `RuntimeService.analyze_text()` performs backend doctor and analysis flow for `/api/analyze`.
- `scripts/verify_golden_prompts.py` -- existing Playwright/browser script pattern for locked prompts and request timing.
- `tests/runtime/test_gguf_backend.py`, `tests/runtime/test_gguf_latency.py`, `tests/runtime/test_demo.py` -- existing unit-test coverage around GGUF config, prompt budget, and demo routes.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Phase 28's `scripts/verify_golden_prompts.py` already owns a `vnphish demo` subprocess, waits for the page to load, submits the locked prompts through the real browser UI, and records `response.request.timing` latency data.
- The locked golden prompts already exist in `.planning/phases/28-baseline-readiness-zero-code-diagnostics/artifacts/28-golden-prompt-results.json`; Phase 30 should reuse them verbatim.

### Established Patterns
- Runtime settings come from `src/config/settings.py` via pydantic-settings and the Phase 29 OS-level model-path environment variables.
- GGUF runtime loading is instance-local in `GGUFAnalyzer`; `vnphish demo` warms the model once before serving, while `vnphish analyze` performs a separate doctor path before creating the runtime service.
- Existing runtime tests use fake GGUF runtime objects to verify configuration without loading the real model.

### Integration Points
- A measurement harness can start `vnphish demo --no-browser --port <port>`, time process launch until page readiness, submit one or both locked prompts, and write JSON/Markdown artifacts.
- Any targeted GGUF fix would likely touch `src/runtime/analyzers/gguf.py` and must be covered by a small unit test proving the intended llama.cpp parameter is passed.
- Verification must include a human-run artifact because reboot and battery/AC power-plan state cannot be created reliably by the coding agent.

</code_context>

<specifics>
## Specific Ideas

- Prefer a new script such as `scripts/measure_cold_latency.py` that is dedicated to Phase 30 evidence and can be run after reboot in PowerShell.
- Include a runbook that tells the user exactly what to do after reboot: select power mode, run the command, wait for completion, then repeat on battery/Balanced.
- Preserve both total elapsed wall-clock timing and browser request timing so the phase can distinguish startup/model-load cost from per-request inference cost.
- Treat the observed `ERROR SOURCE_LANG_VI` console warning from Phase 29 as a Phase 31 watchpoint unless it blocks latency measurement.

</specifics>

<deferred>
## Deferred Ideas

- UI quirks, console polish, edge-case matrix, double-submit checks, and CLI entrypoint help belong to Phase 31.
- Fallback video/screenshot recording and full dry rehearsal belong to Phase 32.
- Dependency upgrades, prompt redesign, schema changes, and multi-optimization performance work are out of scope for this pre-defense phase unless explicitly promoted into a later phase.

</deferred>

---

*Phase: 30-Latency Diagnosis & Targeted Fix*
*Context gathered: 2026-07-05*
