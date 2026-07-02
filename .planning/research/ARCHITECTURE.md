# Architecture Research

**Domain:** Pre-presentation verification & hardening of an existing local Python/wsgiref demo app (offline GGUF LLM inference)
**Researched:** 2026-07-02
**Confidence:** HIGH (based on direct source reading of `src/runtime/*` and `tests/runtime/*`) / MEDIUM for llama.cpp performance tuning claims (WebSearch-verified, not benchmarked on the actual presentation laptop yet)

> Note: this file replaces a prior milestone's LaTeX-layout architecture note (v2.2 report formatting), which is no longer relevant to the active v5.1 "Demo Verification & Presentation Readiness" milestone. That content is preserved in git history if needed again.

## Standard Architecture

### System Overview (As-Is, Verified by Reading Source)

```
┌─────────────────────────────────────────────────────────────────────┐
│  Entry points (frozen contract surface)                             │
│  ┌────────────────────┐        ┌──────────────────────────────────┐ │
│  │ vnphish CLI         │        │ vnphish demo (wsgiref server)    │ │
│  │ src/runtime/cli.py  │        │ src/runtime/demo.py              │ │
│  │ analyze / doctor /  │        │ DemoApp: GET / , /static/*.css,  │ │
│  │ demo subcommands    │        │ /static/*.js, POST /api/analyze  │ │
│  └─────────┬───────────┘        └───────────────┬──────────────────┘ │
│            │                                    │                    │
├────────────┴────────────────────────────────────┴────────────────────┤
│                    RuntimeService (src/runtime/service.py)           │
│  normalize_text → boundary checks → backend.doctor() → backend.      │
│  analyze() → cue-count trim → AnalysisResult                         │
├────────────────────────────────────────────────────────────────────┤
│  AnalyzerBackend (selected by Settings.runtime_backend)              │
│  ┌───────────────┐ ┌────────────────────┐ ┌────────────────────┐    │
│  │ HeuristicAnal.│ │ GGUFAnalyzer        │ │ AcceleratedAnalyzer│    │
│  │ (no model)    │ │ llama_cpp.Llama,    │ │ (transformers, not │    │
│  │               │ │ n_ctx=512, n_gpu_   │ │ default profile)   │    │
│  │               │ │ layers=0 (CPU only) │ │                    │    │
│  └───────────────┘ └─────────┬──────────┘ └────────────────────┘    │
├─────────────────────────────┴────────────────────────────────────────┤
│  Local artifacts (off-repo, env-overridden)                          │
│  D:\PROJEct\AI MODELS\...\gguf-laptop.gguf                            │
│  model-registry.json (selection metadata)                            │
│  .env/.env → MODEL_ARTIFACT_ROOT, MODEL_REGISTRY_PATH overrides      │
└────────────────────────────────────────────────────────────────────┘
```

The web demo and the CLI `analyze` command are two independent entry points into the **same** `RuntimeService`/`GGUFAnalyzer` stack — they do not share process state, so verifying one does not verify the other's wiring (host/port args, browser launch, stdin handling, JSON body parsing).

### Component Responsibilities

| Component | Responsibility | Verification relevance |
|-----------|----------------|-------------------------|
| `src/runtime/cli.py` | argparse dispatch for `analyze`/`doctor`/`demo`; owns the exact subcommand names presenters must remember | Root cause of "CLI entrypoint confusion" — fixable via help text/launcher, not a contract change |
| `src/runtime/demo.py` (`DemoApp`, `run_demo_server`) | wsgiref WSGI app; serves 4 static assets + 1 POST endpoint; does model warmup once at server start | Best neutral point to wrap for server-side latency logging without touching the JSON wire contract |
| `src/runtime/service.py` (`RuntimeService`) | Normalize-first orchestration; boundary/empty/short-text checks; calls `backend.doctor()` on **every** `analyze_text()` call, not just at startup | Doctor call is cheap once `GGUFAnalyzer._cached_doctor_status` is warm — but this is the layer to time to separate "normalize+validate" cost from "model inference" cost |
| `src/runtime/doctor.py` (`RuntimeDoctor`) | Readiness checks: python version, imports, settings load, backend-specific checks including an actual `GGUFAnalyzer.doctor()` model load probe | This is the tool for the offline-portability pass — `vnphish doctor` is a complete, zero-network, self-diagnosing readiness report already built |
| `src/runtime/analyzers/gguf.py` (`GGUFAnalyzer`) | Resolves artifact path from registry, loads `llama_cpp.Llama` (cached instance), runs `create_chat_completion`/`create_completion` with `max_tokens=250`, `n_ctx=512`, `n_gpu_layers=0` (hardcoded CPU-only) | Primary latency suspect: no explicit `n_threads`, hardcoded `n_gpu_layers=0`, fixed 512-token context regardless of laptop hardware |
| `src/runtime/analyzers/local_model.py` | Prompt building (`build_structured_analysis_prompt`, no truncation) + JSON payload extraction/validation via Pydantic (`ThreatDecision`) | Long-input edge case risk: full message text is concatenated into the prompt with **no length cap**, but `n_ctx=512` is fixed — long pastes can overflow context and produce truncated/unparseable JSON, surfacing as a generic `RuntimeUnavailableError` rather than a clear "text too long" message |
| `src/config/settings.py` (`Settings`) | pydantic-settings; reads `.env/APIKEY.json`/`.env/.env` **relative to current working directory**, with OS env vars as override | Portability trap: if the presentation laptop launches `vnphish` from a shortcut/terminal whose CWD isn't the repo root, the relative `.env/.env` file is silently not found and `model_artifact_root`/`model_registry_path` fall back to repo-relative defaults (`data/models`, `data/manifests/model-registry.json`) instead of the off-repo `D:\PROJEct\AI MODELS` path |
| `src/runtime/demo_assets/{demo.js,demo.css,index.html,i18n.js}` | Static, unauthenticated assets; `demo.js` owns the `fetch('/api/analyze')` call and all DOM rendering | Safe to instrument client-side (not part of the "backend contract" — it's presentation-layer JS already modified across prior milestones) |

## Recommended Structure for the Verification Pass

No new `src/` package is warranted — this is a hardening milestone, not a feature milestone. The right footprint is a handful of **new, additive, non-shipped files** that never touch `src/runtime/service.py`, `src/runtime/analyzers/*`, or the `/api/analyze` wire contract:

```
scripts/
├── verify_latency.py        # NEW — external timing harness, imports build_default_runtime_service
│                             #   directly (no monkeypatching of src/), times normalize→doctor→
│                             #   analyze as three separate perf_counter spans, runs N sample
│                             #   messages, prints a table. Never imported by src/ or shipped.
├── defense/
│   ├── START_DEMO_UI.bat    # NEW — cd's to repo root, activates venv, sets
│   │                         #   MODEL_ARTIFACT_ROOT/MODEL_REGISTRY_PATH explicitly (not relying
│   │                         #   on .env discovery), runs `vnphish demo`
│   ├── START_TEXT_ANALYZE.bat # NEW — same env setup, runs `vnphish analyze` in a loop-friendly
│   │                         #   console window, for the "text-only, no page" fallback path
│   └── record_fallback.md   # NEW — checklist, not code: which scam/benign/edge messages to run
│                             #   on camera, in what order, using which recorder
tests/runtime/
└── test_demo_latency_smoke.py  # OPTIONAL NEW — a fast pytest that asserts a fake/heuristic
                                  #   backend request completes under a generous ceiling
                                  #   (protects against future accidental regressions, not a
                                  #   real GGUF benchmark since CI likely lacks the model file)
```

### Structure Rationale

- **`scripts/verify_latency.py` lives outside `src/`:** it is diagnostic tooling for one milestone, not part of the shipped runtime or the frozen `/api/analyze` contract. Keeping it out of `src/runtime` means zero risk of accidentally changing import-time behavior of the demo/CLI.
- **`scripts/defense/*.bat` replace "remembering CLI subcommands":** this directly resolves the "CLI entrypoint confusion between `vnphish analyze` and `vnphish demo`" item without touching `cli.py`'s argparse contract at all. If a code-level fix is still wanted, the only safe addition is an argparse `epilog`/`--help` text clarification in `build_parser()` (additive string only, no argument/flag changes, no behavior change to any handler).
- **No new `src/` module:** every actual instrumentation need (timing, portability check, recording) is satisfiable by external tooling or additive scripts, consistent with "backend frozen except the i18n.js route."

## Architectural Patterns

### Pattern 1: Outer WSGI Timing Middleware (server-side latency, zero contract risk)

**What:** Wrap the existing `DemoApp` instance from *outside* `demo.py`, at the point `make_server()` is called, with a thin function that times `app(environ, start_response)` using `time.perf_counter()` and logs to stdout/stderr.
**When to use:** When you need to know total server-side latency (including model warmup misses) without changing what bytes go back to the browser.
**Trade-offs:** Because `_json_response`/`_text_response` in `demo.py` build the full response body into a `list[bytes]` *before* calling `start_response`, a naive "time between call and return" wrapper already captures the full request-processing time — there is no streaming/generator response to worry about here (confirmed by reading `demo.py`: every handler returns a fully-materialized list, never a generator). This makes the simple wrapper pattern sufficient; the more complex "wrap the iterable's `close()`" pattern documented for general WSGI middleware is unnecessary in this codebase.

**Example (belongs in a new, tiny wrapper — NOT edited into `DemoApp`):**
```python
# in run_demo_server(), wrap only at server-construction time:
import time

def _timed(app):
    def _wrapped(environ, start_response):
        t0 = time.perf_counter()
        result = app(environ, start_response)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        if environ.get("PATH_INFO") == "/api/analyze":
            print(f"[latency] /api/analyze took {elapsed_ms:.0f} ms")
        return result
    return _wrapped

with make_server(host, port, _timed(app)) as server:
    ...
```
This can be added as a small, reviewable diff to `run_demo_server` (it changes zero response bytes, zero status codes, zero headers — it only adds a print statement), or kept entirely external as a `scripts/` wrapper that monkeypatches `make_server` for a one-off verification run. Given the deadline, the monkeypatch-in-a-script approach is lower-risk because it requires no commit to `src/runtime/demo.py` at all.

### Pattern 2: Client-Side `performance.now()` Around the Existing `fetch` Call

**What:** In `demo.js`'s `analyzeMessage()`, wrap the existing `fetch('/api/analyze', ...)` call with `performance.now()` before/after and `console.log` (or a `data-*` attribute) the round trip.
**When to use:** To measure what the presenter/audience actually experiences (network + JSON parse + DOM render), not just backend compute.
**Trade-offs:** Requires a small `demo.js` edit. `demo.js` is a static asset, not the request/response schema, so it is not part of the "frozen backend contract" — but it is still shipped/rendered code, so keep the change to `console.log` only (invisible in the UI) unless the roadmap explicitly wants a visible "analyzed in Xs" badge as a UI polish item.

```javascript
const t0 = performance.now();
const response = await fetch('/api/analyze', { ... });
const payload = await response.json();
console.log(`[latency] round trip ${(performance.now() - t0).toFixed(0)} ms`);
```

### Pattern 3: Browser DevTools Network Tab (zero code, zero risk)

**What:** Open the demo in a browser, open DevTools → Network, submit a message, read the `/api/analyze` request's Time column (TTFB + content download).
**When to use:** First diagnostic step, always — it requires no code changes whatsoever and directly answers "is the bottleneck server compute or something else (browser rendering, extension interference, etc.)."
**Trade-offs:** Doesn't break down *why* the backend is slow (normalize vs. doctor vs. model inference), only that it is. Use this first; only add Pattern 1/2 instrumentation if this doesn't already explain the reported issue.

## Data Flow

### Latency-Relevant Request Flow (current, as built)

```
Browser fetch POST /api/analyze
    ↓
DemoApp.__call__ → DemoApp._handle_analyze
    ↓ (JSON parse, channel validation — cheap, in-process)
RuntimeService.analyze_text(text, channel)
    ↓ normalize_text(text)                      [cheap]
    ↓ boundary checks (empty/short/non-text)     [cheap]
    ↓ self.backend.doctor()                      [cheap AFTER warmup — GGUFAnalyzer
    │                                              caches DoctorStatus once ready]
    ↓ backend.analyze(request)
        ↓ GGUFAnalyzer._resolve_artifact_path()  [cheap — registry JSON read]
        ↓ GGUFAnalyzer._load_runtime()           [cached after first call —
        │                                          run_demo_server already calls
        │                                          app.service.backend.doctor() once
        │                                          at startup as a warmup, so the
        │                                          FIRST real request should NOT pay
        │                                          model-load cost]
        ↓ GGUFAnalyzer._infer_payload()          [*** dominant cost: CPU token
        │                                          generation, up to 250 tokens,
        │                                          n_gpu_layers=0 hardcoded, no
        │                                          explicit n_threads ***]
        ↓ extract_structured_payload + Pydantic validation [cheap]
    ↓ AnalysisResult
    ↓ result.model_dump(mode="json")
Browser renders result bubble
```

**Key implication for diagnosis:** given the warmup call already exists in `run_demo_server` (`app.service.backend.doctor()` before `make_server`), a slow *first* request is a different bug (warmup not actually loading weights, or doctor() being skipped) than a slow *every* request (CPU generation is simply slow on this hardware). The verification pass must distinguish these two cases before proposing a fix, since they have different remedies (warmup fix vs. `n_threads`/`n_gpu_layers`/`max_tokens` tuning).

### Offline-Portability Data Flow (env resolution — the part that breaks silently)

```
Settings() instantiated (pydantic-settings)
    ↓ reads .env/APIKEY.json, .env/.env  — PATH IS RELATIVE TO CURRENT WORKING DIRECTORY
    ↓ (if CWD ≠ repo root when `vnphish` is launched, these files are NOT found)
    ↓ OS environment variables override file values IF SET
    ↓ falls back to Settings field defaults:
        model_artifact_root = Path("data/models")            ← repo-relative default
        model_registry_path = Path("data/manifests/model-registry.json")  ← repo-relative default
    ↓ GGUFAnalyzer reads registry_path → if wrong path, doctor() correctly
      reports "Missing model registry" (fail-closed) rather than silently using
      a stale/wrong model — this is a SAFE failure mode, but it looks identical
      to "the demo is broken" to a presenter who doesn't know why
```

This confirms the fail-closed design (`runtime_fail_closed: bool = True` in `Settings`) protects against wrong/missing models being used silently — but it does **not** protect against a working-directory mismatch producing a confusing "NOT READY" report on defense day. The fix is procedural (always launch from repo root, or set OS-level persistent env vars via `setx` so `.env/.env` discovery is not load-bearing), not a code change.

## Scaling Considerations — Reframed as "Verification Load Profile"

This app will never see concurrent-user scale; the only "load" that matters is defense-day conditions:

| Scenario | What matters | Verification approach |
|----------|---------------|------------------------|
| Single presenter, single browser tab, sequential messages | Per-request latency (the reported issue) | DevTools Network tab + `scripts/verify_latency.py`, sample messages across all 4 threat classes + benign |
| Cold start (laptop just booted, model never loaded) | Time from `vnphish demo` invocation to "Warming up local model..." → ready | Time the warmup print-to-ready-print gap once per cold boot rehearsal |
| Network fully disabled (airplane mode / no Wi-Fi) | Zero outbound calls anywhere in the request path | `wsgiref.make_server` binds `127.0.0.1` only; `llama_cpp.Llama(model_path=...)` loads a local file with no download step (unlike `AcceleratedAnalyzer`, which is not the default profile and should stay untouched); confirm no `transformers`/`huggingface_hub` cache-miss network calls are reachable from the `gguf` backend path — `GGUFAnalyzer` never imports those |
| Different Windows user profile / different machine | `.env/.env` CWD-relative discovery, PATH availability of `python`/`vnphish` console script, presence of the Visual C++ runtime `llama-cpp-python` wheels typically need, permission to read `D:\PROJEct\AI MODELS` from that profile | Dedicated dry run: new user profile (or a second laptop), fresh `pip install -e .[dev,runtime]`, explicit OS-level env vars, `vnphish doctor` must report READY before trusting `vnphish demo` |

### "First Bottleneck" Priority

1. **Per-token CPU generation cost in `GGUFAnalyzer._infer_payload`** (no `n_threads` set, `n_gpu_layers=0` hardcoded, `max_tokens=250`) — almost certainly the dominant cost once warmup is confirmed to be working. Diagnose with `scripts/verify_latency.py` timing spans before touching any tuning parameter.
2. **CWD-relative `.env` discovery** — not a runtime performance issue, but the single most likely cause of "it worked on my machine, broke on the presentation laptop" if the launch shortcut's working directory differs from the repo root.

## Anti-Patterns to Avoid in This Milestone

### Anti-Pattern 1: Adding a New `src/runtime` Module for "Observability"

**What people do:** Build a metrics/logging subsystem (structured logging, a `/metrics` endpoint, a timing decorator library) inside `src/runtime/` to "properly" instrument the app.
**Why it's wrong:** This milestone is QA/hardening with a hard deadline (defense window opens in ~11 days from today). Any new importable module inside `src/runtime` risks touching import order, doctor checks, or test fixtures that 9 existing `tests/runtime/*.py` files depend on. It also drifts toward "restructuring the app," which is explicitly out of scope.
**Instead:** Use external scripts (`scripts/verify_latency.py`) and browser DevTools. If a tiny in-process print statement is truly needed (Pattern 1 above), keep it to a 5-line addition in `run_demo_server` only, never a new module.

### Anti-Pattern 2: Building an In-App "Record Demo" Feature

**What people do:** Add a "record this session" button or server-side screenshot/video capture endpoint to the demo UI itself.
**Why it's wrong:** Directly contradicts the project's own "Out of Scope" line (`Image processing, computer vision, OCR, and screenshot analysis`) and the frozen-backend constraint — it would add a new endpoint and new dependencies (screen/video capture libraries) with days left before the defense.
**Instead:** Fallback recording is a pure **external tooling** concern: OBS Studio (portable build, no install needed, works fully offline) or the Windows built-in Xbox Game Bar (`Win+G`) for screen capture; Windows `Snipping Tool`/`PrtScn` for stills. Record against the *finished, verified* demo running normally through the browser and CLI — the recording step should be last in the build order, not implemented as app code.

### Anti-Pattern 3: Tuning `n_threads`/`n_gpu_layers` Before Measuring

**What people do:** See "latency issue" in the backlog and immediately start changing `GGUFAnalyzer._load_runtime()` parameters.
**Why it's wrong:** Without first separating "cold load" from "per-request generation" and without knowing the actual presentation laptop's core count, a blind tuning pass can make things worse (llama.cpp CPU throughput does not scale linearly with thread count past ~4-8 threads due to memory-bandwidth limits) and burns limited pre-defense time on speculative fixes.
**Instead:** Run `scripts/verify_latency.py` on the actual presentation laptop first, record a baseline (cold vs. warm, across 4-5 representative messages), then apply one targeted change (e.g., explicit `n_threads=<measured optimum>`) and re-measure before/after.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| None (by design) | N/A | `gguf` backend path has zero network dependency — `llama_cpp.Llama(model_path=...)` is a local file load; this should be explicitly re-verified with network disabled as part of the portability pass, not just assumed from reading the code |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| CLI (`cli.py`) ↔ `RuntimeService` | Direct Python call, in-process | `handle_analyze` runs `run_runtime_doctor()` itself before building the service — this is a *second*, separate doctor invocation from the one `RuntimeService.analyze_text()` runs internally; both are cheap once warm, but worth knowing when timing "why does `vnphish analyze` feel slower than the web demo's second request" |
| Web demo (`demo.py`) ↔ `RuntimeService` | Direct Python call, in-process, via `build_demo_app()`/`build_default_runtime_service()` | Only `DemoApp` calls `app.service.backend.doctor()` once eagerly at server start (the warmup); the CLI path never pre-warms, so the *first* `vnphish analyze` invocation in a fresh process always pays full model-load cost — this asymmetry is a legitimate source of "CLI feels slower/different from the web demo" confusion and should be verified/documented, not silently fixed by changing CLI behavior (which would touch the frozen contract) |
| `demo.js` (browser) ↔ `DemoApp` (`POST /api/analyze`) | `fetch` + JSON, single endpoint, no auth, no streaming | Response is small, fully-materialized JSON — safe for either server-side (Pattern 1) or client-side (Pattern 2) timing without touching the schema itself |
| `Settings` ↔ filesystem | pydantic-settings `env_file` resolution, CWD-relative | The single highest-risk integration point for the portability check — verify explicitly with `python -c "from src.config.settings import get_settings; s=get_settings(); print(s.model_artifact_root, s.model_registry_path)"` run from a directory other than the repo root, with and without OS-level env vars set |

## Suggested Build Order (Deadline-Aware)

Today is 2026-07-02; defense window opens 2026-07-13 (~11 days). Order below front-loads the cheapest, zero-risk diagnostics and defers any code change until it's proven necessary, ending with the fallback recording only once the live demo is trustworthy:

1. **`vnphish doctor`** — baseline readiness on the current dev machine. Zero code, minutes.
2. **CLI functional pass** — `vnphish analyze --text "..."` across sample scam (bank impersonation, task scam, zalo social engineering) + benign + edge cases (empty string, very long paste exceeding ~512-token context, malformed/gibberish text). Validates the model/backend in isolation from the web layer and from browser variables.
3. **Browser DevTools Network tab pass** — launch `vnphish demo`, submit the same sample set, read per-request timings. Zero code. Often sufficient to characterize the reported latency issue.
4. **If deeper breakdown is needed:** add `scripts/verify_latency.py` (external, per Pattern 1/3) to separate cold-load vs. warm per-request vs. normalize/doctor overhead. Only then consider one targeted tuning change (`n_threads`, or reducing `GGUF_COMPLETION_MAX_TOKENS` if 250 tokens is generating more than needed) and re-measure.
5. **CLI entrypoint confusion fix** — ship `scripts/defense/START_DEMO_UI.bat` and `scripts/defense/START_TEXT_ANALYZE.bat` (zero risk, immediately usable); optionally add an argparse epilog clarifying the two commands in `cli.py` (additive text only).
6. **Offline-portability pass** — new Windows user profile or second machine: fresh `pip install -e .[dev,runtime]`, explicit OS-level `MODEL_ARTIFACT_ROOT`/`MODEL_REGISTRY_PATH` env vars (do not rely on `.env/.env` discovery), network disabled, run `vnphish doctor` → `vnphish demo` → `vnphish analyze`. This is the step most likely to surface a "worked on my machine" surprise and should not be left until the day before the defense.
7. **UI quirks pass** — exercise the demo UI itself (long text, rapid double-submit given the existing `AbortController` logic in `demo.js`, clear button, sample button) and log anything visually broken.
8. **Fallback recording** — only after 1-7 are green: use OBS Studio (portable, offline) or Windows Game Bar to record (a) the full happy-path web demo across the 4 threat classes + benign, (b) one edge case handled gracefully, (c) the CLI fallback path via `START_TEXT_ANALYZE.bat`. Take stills as a lighter-weight backup to the video.
9. **Full dry rehearsal on the actual presentation laptop**, cold boot, using the `scripts/defense/*.bat` launchers exactly as planned for the defense — validates that steps 5-6's fixes actually hold end-to-end under real conditions, not just in isolation.

## Sources

- Direct source reading (HIGH confidence): `src/runtime/cli.py`, `src/runtime/demo.py`, `src/runtime/service.py`, `src/runtime/doctor.py`, `src/runtime/analyzers/gguf.py`, `src/runtime/analyzers/local_model.py`, `src/config/settings.py`, `src/runtime/demo_assets/demo.js`, `tests/runtime/test_cli.py`, `tests/runtime/test_gguf_latency.py` (note: despite the filename, this file tests prompt-stripping/JSON parsing, not actual timing — no existing latency instrumentation was found anywhere in the repo), `.planning/STATE.md` (confirms `.env/.env` off-repo model path override), `TODO.md`, `REAL_LIFE_SCAM_TEST_DEMO.md`.
- [Diagnosing Latency in llama.cpp Python Wrapper for Short Prompts (GitHub Discussion)](https://github.com/abetlen/llama-cpp-python/discussions/2073) — MEDIUM confidence, community discussion, informs the "measure before tuning n_threads" recommendation.
- [llama.cpp: CPU vs GPU, shared VRAM and Inference Speed (DEV Community)](https://dev.to/maximsaplin/llamacpp-cpu-vs-gpu-shared-vram-and-inference-speed-3jpl) — MEDIUM confidence, corroborates memory-bandwidth-bound CPU thread scaling.
- [Performance monitoring of real WSGI application traffic (Graham Dumpleton)](https://grahamdumpleton.me/posts/2015/05/performance-monitoring-of-real-wsgi/) — MEDIUM confidence, standard WSGI middleware timing pattern; confirmed applicable here because this app's WSGI handlers never return generator/streaming bodies (verified by reading `demo.py`).
- [WSGI Middleware to record Request and Response data (Gist)](https://gist.github.com/georgevreilly/5762777) — MEDIUM confidence, general pattern reference for the timing wrapper shape.

---
*Architecture research for: pre-presentation demo verification & hardening*
*Researched: 2026-07-02*
