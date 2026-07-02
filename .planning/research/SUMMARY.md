# Project Research Summary

**Project:** Localized Explainable AI (XAI) Engine for Vietnamese Financial Phishing and Threat Detection — v5.1 "Demo Verification & Presentation Readiness" milestone
**Domain:** Pre-defense hardening/verification of an existing, working local Python (`wsgiref`) + vanilla-JS demo, backed by offline GGUF/llama.cpp CPU inference
**Researched:** 2026-07-02
**Confidence:** MEDIUM-HIGH

## Executive Summary

This is not a build-from-scratch milestone — it is a **verification and hardening pass** on an already-working product, with a live, unrepeatable thesis defense as the deadline (window opens 2026-07-13, ~11 days out). All four research agents independently converged on the same posture: the stack is frozen, the architecture is sound and already instrument-friendly, and the actual risk is not "what to build" but "does what already works on the dev machine still work, unattended, offline, on the exact presentation laptop, in front of a committee, with no do-overs." The single most concrete, already-confirmed finding across all four files is that `src/runtime/demo_assets/index.html` loads Be Vietnam Pro from Google Fonts over the network — a live, disprovable contradiction of the demo's own "local-first, no cloud" pitch, discoverable by any committee member who opens DevTools.

The recommended approach is almost entirely non-code: pin the exact already-validated dependency versions (`llama-cpp-python==0.3.23`, not the newer `0.3.32` that a fresh install would silently resolve to), reuse existing zero-install diagnostics (`vnphish doctor`, browser DevTools Network tab, `llama_cpp` verbose timings) before writing any new tooling, and treat every fix as an "additive, external, non-shipped" change (scripts/, .bat launchers, self-hosted fonts) rather than touching `src/runtime/service.py` or the `/api/analyze` wire contract. The build order that emerges from combining ARCHITECTURE.md and PITFALLS.md is: cheapest zero-code diagnostics first (doctor, CLI pass, DevTools), then environment-parity verification (the highest-risk unknown, since the presentation laptop's drive letters, OneDrive sync state, and `.env/.env` discovery have never been tested), then targeted fixes only where verification proves a real problem, then fallback recording last.

Key risks, ranked: (1) environment drift between dev machine and presentation laptop — off-repo model paths, git-ignored `.env/.env`, OneDrive sync interference, and absolute Windows drive-letter paths are all invisible in code review and untested outside the dev machine; (2) the rehearsed "~13s" latency figure is a *warm* number only — cold mmap page-cache, Windows Defender first-touch scanning, and battery/power-plan throttling can all silently blow past it on presentation day; (3) the offline claim has a real, already-identified leak (Google Fonts CDN); (4) no fallback has been recorded or rehearsed yet, and recording it too early (before fixes land) creates its own staleness risk. None of these require new technology — they require disciplined, sequenced verification on the actual hardware that will be used live.

## Key Findings

### Recommended Stack

The stack is deliberately **not changing** for this milestone. Every recommendation is either already installed, stdlib, or a small dev-only addition with zero runtime footprint. The core move is defensive pinning: exact-pin `llama-cpp-python==0.3.23` (the version the ~13s latency and chat-template behavior were actually validated against) rather than leaving `pyproject.toml`'s `>=0.3` open-ended, since upstream `0.3.32` (released 2026-06-29, four days before this research) includes chat-template and KV-cache changes that could silently alter output on a fresh install days before the defense.

**Core technologies (pin, don't add):**
- `llama-cpp-python==0.3.23` — exact pin; GGUF CPU inference backend already validated against this version's behavior.
- CPython 3.13.13 (or nearest 3.13.x) — matches dev environment; verify a prebuilt wheel (not source build) installs on the presentation laptop.
- `wsgiref.simple_server` (stdlib) — already the shipped server; single-threaded/synchronous, not worth changing this close to the defense.
- Playwright `==1.60.0` (already installed) — the only tool in the stack that can drive a real browser and catch DOM/JS "UI quirks" that the existing `wsgiref`-environ unit test structurally cannot see.

**Supporting dev-only additions:** `psutil==7.2.2` (pin explicitly — currently only arrives transitively via the unused `train` extra, so it will be *absent* on a laptop that only runs the documented `[dev,runtime]` install), `py-spy` (only if built-in `llama_cpp` verbose timings don't explain the latency), and non-Python tools: browser DevTools Network tab, Windows power plan settings, OBS Studio (offline, free, GPL) for fallback recording.

### Expected Features

FEATURES.md frames this as a verification checklist, not a feature backlog — the "features" are hardening actions, each mapped to real code inspected directly in the repo (`src/runtime/cli.py`, `demo.py`, `doctor.py`).

**Must have (table stakes, P1, due before 13 July):**
- `vnphish doctor` passing on the **actual presentation laptop**, not the dev machine.
- Full functional pass across all in-scope threat classes + one benign message.
- Network-isolation pass (Wi-Fi/Ethernet off) confirming identical behavior and zero external requests.
- Edge-case pass: empty input, very long paste, malformed/off-topic/mixed-language text, no raw crash or hang.
- Latency measured and quantified (cold vs. warm) with a one-line presenter narration ready.
- CLI entrypoint disambiguation (`analyze` vs `demo`) — help-text/launcher fix, not a restructure.
- Concurrency/double-submit check confirming the existing `AbortController` fetch-guard still works.
- Recorded video + screenshots of each threat-class result, stored in two local locations.

**Should have (differentiators):** a memorized narration script for the latency number, a pre-selected rehearsed input set doubling as both QA and live-demo script, a visible "doctor output shown first" credibility beat, a private incident-response card.

**Explicitly defer (v2+/out of scope for this milestone):** any UI redesign, CLI subcommand restructuring, swapping `wsgiref` for a production WSGI server, model-level latency re-engineering (requantizing, changing runtime profile), new telemetry/logging. All four research files independently flag these as tempting-but-risky scope creep this close to the defense.

### Architecture Approach

No new `src/` package is warranted. The existing architecture (CLI + `wsgiref` demo -> `RuntimeService` -> pluggable `AnalyzerBackend` -> local GGUF artifact) already has clean seams for non-invasive verification: a thin outer WSGI timing wrapper (zero contract risk, confirmed safe because `demo.py` never returns streaming/generator responses), client-side `performance.now()` around the existing `fetch` call, and `vnphish doctor` as an already-built, zero-network readiness probe that should be used, not duplicated.

**Major components:**
1. `RuntimeService` — normalize -> boundary checks -> `backend.doctor()` -> `backend.analyze()` orchestration; the layer to time to separate normalize/validate cost from model-inference cost.
2. `GGUFAnalyzer` — loads and caches `llama_cpp.Llama` (`n_gpu_layers=0`, `n_ctx=512`, no explicit `n_threads`); the primary latency suspect and the component to leave untouched unless verification proves a specific, targeted tuning change helps.
3. `Settings` (pydantic-settings) — resolves `.env/.env` **relative to current working directory**; the single highest-risk portability integration point, since a wrong launch CWD silently falls back to repo-relative model paths instead of the real off-repo model root.
4. `DemoApp`/`demo.js` — the presentation-layer surface; safe to instrument client-side since it isn't part of the frozen backend contract, but any prompt/template edit risks re-breaking already-fixed `data-slot`/context-window budget issues.

### Critical Pitfalls

1. **Environment drift (dev machine vs. presentation laptop)** — off-repo absolute model paths, git-ignored `.env/.env`, OneDrive sync interference, and possible drive-letter reassignment are all invisible in code review. Avoid by running a full cold-clone dry run and requiring a clean `vnphish doctor READY` on the *actual* presentation laptop at least 48 hours out, plus a same-morning recheck.
2. **Cold-start timing doesn't match the rehearsed "~13s" figure** — that number is warm-only; mmap cold page cache, Windows Defender first-touch scanning of a multi-GB GGUF file, and a post-reboot state can blow past it. Avoid by rehearsing a true cold-boot-to-first-answer run, adding a Defender exclusion if policy allows, and pre-warming once before the committee arrives.
3. **Hardcoded internet dependency contradicts the "local-first" claim** — Google Fonts CDN links in `index.html` are a confirmed, already-found leak. Avoid by self-hosting the `.woff2` files and grepping all demo assets for any other `http(s)://` reference.
4. **Power plan/battery throttling silently changes CPU inference speed** — a CPU-bound workload on Balanced/Battery Saver runs visibly slower than rehearsed. Avoid by forcing High Performance, staying on AC, and rehearsing at least once unplugged at realistic battery level.
5. **Unrehearsed or stale fallback** — a fallback recorded early goes stale after later UI/latency fixes, and a fallback that's never been exercised under simulated failure isn't actually verified. Avoid by recording last (after freeze), keeping two formats (video + screenshots), and rehearsing the live-to-fallback pivot at least once.

## Implications for Roadmap

Based on combined research, the roadmap for this milestone should be structured as a **strictly sequenced verification pipeline**, not parallel feature phases — dependencies are real (you cannot meaningfully edge-case-test before `doctor` passes; you cannot record a trustworthy fallback before functional verification is green). ARCHITECTURE.md's "Suggested Build Order" and PITFALLS.md's "Pitfall-to-Verification-Category Mapping" independently converge on the same four verification categories already named in PROJECT.md: **Functional, Offline/portability, Edge-case, Fallback**.

### Phase 1: Baseline Readiness & Zero-Code Diagnostics
**Rationale:** Cheapest, zero-risk, zero-code checks first — establishes whether the reported issues are even reproducible before any tooling is built.
**Delivers:** `vnphish doctor` run and confirmed on dev machine; CLI functional pass (`vnphish analyze`) across all threat classes + benign + edge cases in isolation from the web layer; browser DevTools Network-tab latency read.
**Addresses:** FEATURES.md's P1 items — doctor pass, functional pass, latency measurement (first pass).
**Avoids:** Pitfall 8 (CLI entrypoint confusion) surfaces here naturally; Pitfall 2 (cold-start) is *not* fully addressed yet — this phase is warm-path only.

### Phase 2: Environment Parity & Offline Verification (on the actual presentation laptop)
**Rationale:** This is the highest-risk unknown per PITFALLS.md (Pitfall 1) and must not be left until days before the defense — it is the step most likely to surface a "worked on my machine" surprise.
**Delivers:** Fresh `pip install -e .[dev,runtime]` on the real presentation laptop or an equivalent clean profile; explicit OS-level env vars for `MODEL_ARTIFACT_ROOT`/`MODEL_REGISTRY_PATH` (not relying on CWD-relative `.env/.env` discovery); `vnphish doctor` -> `vnphish demo` -> `vnphish analyze` all green with network disabled; Google Fonts self-hosted and grep-verified as the only remaining offline leak.
**Uses:** Stack elements — pinned `llama-cpp-python==0.3.23`, `psutil` for CPU/RAM sampling during the pass.
**Implements:** `Settings`/filesystem integration boundary verification from ARCHITECTURE.md.
**Avoids:** Pitfall 1 (environment drift), Pitfall 3 (hardcoded Google Fonts dependency), Pitfall 9 (sleep/lock/update interruptions — set alongside this pass).

### Phase 3: Latency Diagnosis & Targeted Fix (only if needed)
**Rationale:** Per ARCHITECTURE.md's Anti-Pattern 3 and STACK.md's ordering, diagnose before tuning — a blind tuning pass without first separating cold-load from per-request generation cost can make things worse.
**Delivers:** Cold-boot-to-first-answer timing (not just warm), `llama_cpp` verbose-timing breakdown or `scripts/verify_latency.py` if the built-in timings don't explain the gap, and — only if a specific, measured bottleneck is found — one targeted change (e.g., explicit `n_threads` on the actual laptop's physical core count), re-measured before/after.
**Addresses:** FEATURES.md's "Fix known demo latency/performance issue" active item, without violating the anti-feature "deep model-level latency optimization."
**Avoids:** Pitfall 2 (cold-start timing mismatch), Pitfall 4 (power plan/battery throttling) — both must be measured here on AC and on battery.

### Phase 4: UI Quirks, Edge Cases & Regression Re-check
**Rationale:** Any UI/prompt fix is itself a regression risk (Pitfall 6) against the already-tuned `n_ctx=512` budget and `data-slot` template contract — this phase must run *after* any fixes from Phases 1-3, not before.
**Delivers:** Full edge-case matrix re-run (empty, very long, malformed, mixed-language) after every fix; rapid double-submit / concurrency re-test confirming the `AbortController` guard is intact; `tests/runtime` suite green; CLI entrypoint disambiguation shipped (help text or `.bat` launchers, not a restructure).
**Addresses:** FEATURES.md's edge-case pass, concurrency check, CLI disambiguation, "fix any UI quirks" active item.
**Avoids:** Pitfall 6 (late fixes breaking context budget/templates), Pitfall 7 (`wsgiref` single-threaded re-entrancy).

### Phase 5: Fallback Recording & Full Dry Rehearsal
**Rationale:** Must come last — recording before the fix list is frozen guarantees a stale fallback (Pitfall 5); this phase validates everything above holds end-to-end under real defense-day conditions.
**Delivers:** OBS-recorded full successful run (one message per threat class + benign) plus a static screenshot sequence as a degradation-resistant secondary fallback; a rehearsed live-to-fallback failure pivot; a full cold-boot dry rehearsal on the actual presentation laptop using the final launchers.
**Addresses:** FEATURES.md's "prepare a fallback" active item.
**Avoids:** Pitfall 5 (unrehearsed/stale fallback) directly; reinforces Pitfall 1 and 2 by rehearsing under real cold-boot/laptop conditions one final time.

### Phase Ordering Rationale

- Dependency chain is real and confirmed in FEATURES.md's dependency graph: doctor pass gates functional verification, which gates edge-case and offline passes, which gate the fallback recording. Skipping ahead (e.g., recording a fallback before functional verification is settled) produces exactly the stale-fallback pitfall research flagged.
- Grouping by architecture pattern: Phases 1 and 3 both reuse the "measure before touching code" pattern from ARCHITECTURE.md (DevTools first, then built-in verbose timings, then `py-spy` only as a last resort) — this ordering is itself a research-derived recommendation, not an arbitrary grouping.
- This order front-loads the cheapest/zero-risk diagnostics and pushes any code change to the point where it's proven necessary, consistent with the "code freeze days before the defense" principle that every FEATURES.md and PITFALLS.md source independently corroborates.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 2 (Environment Parity):** OneDrive sync behavior, drive-letter stability across reboots, and Windows Defender exclusion policy at the actual defense venue are environment-specific unknowns not fully resolved by this research pass — flag for `--research-phase` if the presentation laptop's specific configuration is still undecided when planning begins.
- **Phase 3 (Latency Diagnosis):** the "first bottleneck" hypothesis (`n_threads`/`n_gpu_layers` tuning) is MEDIUM confidence (community-sourced, not yet benchmarked on the actual presentation laptop) — worth a short research-phase pass if initial diagnosis doesn't clearly point to CPU generation cost.

Phases with standard patterns (skip research-phase):
- **Phase 1 (Baseline Readiness):** fully documented, zero-code, uses tools already built into the repo (`doctor`, existing CLI, DevTools).
- **Phase 4 (UI Quirks/Regression):** standard regression-testing discipline against an already-understood template/context-budget constraint; no new research needed.
- **Phase 5 (Fallback Recording):** OBS Studio usage and recording discipline are well-documented, low-risk, standard practice.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH (codebase-grounded) / MEDIUM (latency-tuning claims) | Installed versions and defaults confirmed by direct introspection in this environment; external `n_threads`/mmap-tuning claims are WebSearch-derived community consensus, not yet benchmarked on the actual presentation laptop. |
| Features | MEDIUM | No single canonical "thesis demo checklist" source exists; triangulated across conference-demo lore, air-gapped-deployment QA practice, and direct repo inspection of actual CLI/server code (HIGH confidence for the code-grounded parts). |
| Architecture | HIGH (source-read) / MEDIUM (perf-tuning external claims) | Based on direct reading of `src/runtime/*` and `tests/runtime/*`; llama.cpp CPU-scaling and WSGI-middleware-pattern claims are MEDIUM (external, cross-checked but not locally benchmarked). |
| Pitfalls | MEDIUM-HIGH | Several findings (Google Fonts CDN leak, single-threaded `wsgiref`, CWD-relative `.env` resolution) are directly verified against this repo's source (HIGH); OS/hardware behavior (mmap cold-cache, Defender scanning, power-plan throttling) is corroborated by multiple external sources but not yet locally measured on the specific presentation laptop (MEDIUM). |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

- **Presentation laptop identity/specs unknown at research time:** core count, drive letters, OneDrive sync state, and Windows Defender policy on the actual machine are all unresolved — Phase 2 must establish these as ground truth before any latency-tuning decision (Phase 3) is finalized.
- **True cold-boot latency has never been measured:** every existing timing figure (the "~13s") is a warm number from the dev machine. This is a hard gap, not just a confidence caveat — it must be closed empirically in Phase 3, not assumed from research alone.
- **Backup laptop status is unresolved:** PITFALLS.md's recovery-strategy table assumes a "charged spare laptop with identical `.env`/model setup" as the highest-value mitigation for laptop failure, but whether such a spare exists/is provisioned was not confirmed by any research file — flag for the user/planning stage.
- **`llama-cpp-python==0.3.32` upgrade path:** if a specific bug in `0.3.23` is later found to block the defense, STACK.md notes the changelog for `0.3.32` was summarized via WebSearch, not directly diffed — treat any upgrade decision as needing its own verification pass, not a drop-in swap.

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection across all four research files: `src/runtime/cli.py`, `src/runtime/demo.py`, `src/runtime/service.py`, `src/runtime/doctor.py`, `src/runtime/analyzers/gguf.py`, `src/runtime/analyzers/local_model.py`, `src/config/settings.py`, `src/runtime/demo_assets/{index.html,demo.js}`, `tests/runtime/*.py`, `pyproject.toml`.
- `.planning/PROJECT.md` and `.planning/STATE.md` — milestone scope, known active issues, off-repo model path rationale, prior latency/context-window tuning history.
- Installed package version/behavior confirmed via `pip show`/`pip list` and `inspect.signature(llama_cpp.Llama.__init__)` in this exact dev environment.

### Secondary (MEDIUM confidence)
- [llama-cpp-python Changelog / PyPI](https://llama-cpp-python.readthedocs.io/en/stable/changelog/) — confirmed latest release `0.3.32` vs. installed `0.3.23`.
- [Diagnosing Latency in llama-cpp-python Wrapper — GitHub Discussion #2073](https://github.com/abetlen/llama-cpp-python/discussions/2073) and [Optimal parameters for parallel inference — Discussion #18308](https://github.com/ggml-org/llama.cpp/discussions/18308) — CPU thread-scaling and Python/C++ boundary overhead guidance.
- [llama.cpp mmap cold-start behavior](https://markaicode.com/architecture/llamacpp-architecture/) and [Windows Defender real-time protection slowing first file access](https://learn.microsoft.com/en-us/answers/questions/2732424/windows-defender-real-time-protection-service-slow) — corroborate the cold-start/first-touch-scan pitfall.
- [Windows power plan / battery saver CPU throttling](https://www.xda-developers.com/your-windows-power-plan-is-probably-wrong/) and [Google Fonts offline dependency issues](https://medium.com/@bogdanpshonyak/using-google-fonts-offline-b327467e0999) — corroborate power and offline pitfalls respectively.
- [How to Appease the Demo Gods](http://www2.rdrop.com/~paulmck/DemoGods/), [Virtual Thesis Defense recording practice](https://jaan.io/virtual-thesis-defense-recording-zoom-presentation/) — live-demo and academic-defense fallback/rehearsal discipline.

### Tertiary (LOW confidence)
- General SaaS/conference demo-checklist blog posts (ShareFable, Steve Clayton, Guy Kawasaki) — used only to triangulate table-stakes verification actions, not as primary evidence.

---
*Research completed: 2026-07-02*
*Ready for roadmap: yes*
