# Stack Research

**Domain:** Demo verification & presentation hardening (existing local Python + wsgiref + vanilla-JS demo, GGUF/llama.cpp CPU inference)
**Researched:** 2026-07-02
**Confidence:** HIGH (codebase-grounded) / MEDIUM (external latency-tuning claims, verified against official docs and one GitHub maintainer discussion)

## Scope Note

This is a v5.1 hardening milestone, ~10 days before the defense (13-20 July 2026). The existing stack (`llama-cpp-python`, `wsgiref`, vanilla HTML/CSS/JS, `pytest`) already works and is validated by 5 prior milestones. **The goal here is near-zero-risk verification and diagnosis tooling, not new product dependencies.** Every recommendation below is either (a) already installed in this environment, (b) a stdlib/OS-native tool, or (c) a small, dev-only, zero-runtime-footprint addition. Nothing here touches `pyproject.toml` `dependencies` (the shipped runtime path) — additions go in `dev`/`runtime` extras only, or are external, non-Python tools.

Confirmed directly from the codebase (`src/runtime/analyzers/gguf.py`, `src/runtime/demo.py`, `src/runtime/service.py`, `src/data_pipeline/processing/normalizer.py`, `tests/runtime/test_demo.py`, `pyproject.toml`):

- The ~13s latency is a **warm** per-request cost, not a cold-load cost. `run_demo_server()` calls `app.service.backend.doctor()` at startup, which triggers `GGUFAnalyzer._load_runtime()` once and caches the `llama_cpp.Llama` instance (`_cached_runtime`). Every `/api/analyze` call reuses it — the model is not reloaded per request.
- Text normalization (`ftfy.fix_text` + NFC + whitespace collapse, in `normalize_text`) is negligible. No heavy NLP (no `underthesea`) runs on the request path. The 13s sits inside `llama_cpp`'s decode step, not Python-side preprocessing.
- `GGUFAnalyzer` hardcodes `n_gpu_layers=0`, `n_ctx=512`, `verbose=False`, and does **not** pass `n_threads`, `n_batch`, or `flash_attn` — all sit at `llama_cpp.Llama.__init__` defaults, confirmed by direct introspection in this environment: `n_threads=None` (library auto-picks), `n_batch=512`, `n_ubatch=512`, `flash_attn=False`, `verbose=True` (overridden to `False` in this codebase).
- `pyproject.toml` pins `llama-cpp-python>=0.3` (open-ended) and `playwright>=1.58` (open-ended). Installed versions in this dev environment are `llama_cpp_python==0.3.23` and `playwright==1.60.0`, Python `3.13.13`. **Upstream latest is `llama-cpp-python==0.3.32`** (released 2026-06-29) — a fresh `pip install -e .[dev,runtime]` on the presentation laptop today would silently resolve to 0.3.32, not the 0.3.23 this system was actually validated against.
- `psutil==7.2.2` is present in this dev environment only as a transitive dependency of the `train` extra (`accelerate`/`peft`), which is **not** part of `dev` or `runtime` extras. It will likely be absent on a presentation laptop that only runs the documented install command (`python -m pip install -e .[dev]`, per `doctor.py`'s `INSTALL_COMMAND`).
- The existing test (`tests/runtime/test_demo.py`) already exercises the WSGI app in-process via `wsgiref.util.setup_testing_defaults` — this covers HTML/JSON contract shape but **never renders in a real browser**, so JS/DOM-level "UI quirks" (the exact class of bug flagged as unverified in the milestone) are structurally invisible to it.

## Recommended Stack

### Core Technologies (already present — pin, don't add)

| Technology | Version to lock | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| `llama-cpp-python` | `==0.3.23` (exact pin, not `>=0.3`) | GGUF local inference backend | This is the exact version the ~13s latency and demo behavior were validated against. Upstream `0.3.32`'s changelog includes chat-template loading fixes and KV-cache/embedding changes — behavior-affecting for a fine-tuned model's chat-template path. Re-validating a newer version 10 days out is not worth the risk; freeze what already works. |
| CPython | `3.13.13` (or nearest 3.13.x) | Runtime interpreter | Matches this dev environment; `pyproject.toml` requires `>=3.13`. Wheel availability for `llama-cpp-python` on a given Python/OS/arch combo is one of the most common "worked on my machine" failures for this library — verify a prebuilt wheel (not a source build) installs cleanly on the actual presentation laptop before the defense window. |
| `wsgiref.simple_server` (stdlib) | n/a | Local demo HTTP server | Already the shipped server; zero new dependency needed. Note it is single-threaded/synchronous — fine for a one-person live demo, but a second tab or stray request will queue rather than run concurrently. Not worth changing this close to the defense, just worth knowing. |
| Playwright (Python) | `==1.60.0` (already installed, pin it) | Automated **real-browser** E2E smoke test of the demo UI, and scripted fallback screenshots | Already a project dependency (used by `src/data_pipeline/scraper/ncsc_scraper.py`), so a browser-driven smoke test costs zero new install surface. It is the only tool in the stack that can catch actual DOM/JS "UI quirks" (fetch lifecycle, i18n toggle, typing-indicator removal, ARIA live region updates) — the existing `wsgiref`-environ unit test never runs `demo.js` in a JS engine. |

### Supporting Libraries (small, dev-only additions)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `psutil` | `==7.2.2` (pin explicitly under `dev` extra) | CPU/RAM sampling during a manual latency run (confirm no swapping, confirm thread usage matches core count) | Add explicitly — do not rely on it arriving transitively via `train` extras, since it will be absent from a `[dev,runtime]`-only install on the presentation laptop. Use only in a throwaway diagnostic script, never imported by `src/runtime/`. |
| `py-spy` | `0.4.2` | Sampling profiler to attach to the running `vnphish demo` process (`py-spy top --pid <pid>` or `py-spy record -o out.svg --pid <pid>`), to rule out Python-side overhead vs. llama.cpp decode time | Only reach for this if `llama_cpp`'s built-in verbose timings (below) don't explain the 13s. External, attaches without code changes, zero risk to the demo process. Likely unnecessary given the codebase already caches the runtime and preprocessing is negligible — try the free option first. |
| `llama_cpp` verbose timing (built-in, no install) | n/a (already in `0.3.23`) | Get a load/prompt-eval/decode timing breakdown and tokens/sec | Temporarily flip `GGUFAnalyzer._load_runtime`'s `verbose=False` to `True` (or gate it behind an env var) for one diagnostic run of `vnphish analyze`, capture the printed timings, then revert to `False` before the defense. This is the cheapest, zero-dependency first step for latency diagnosis — try it **before** `py-spy`. |

### Development Tools (non-Python, for verification and fallback)

| Tool | Purpose | Notes |
|------|---------|-------|
| Browser DevTools (Chrome/Edge, built-in, F12) — Network tab | Verify the offline/portability requirement: with Wi-Fi and Ethernet disabled, drive the demo and confirm the Network tab shows only requests to `127.0.0.1:8765`, zero external hosts | Zero install. Directly and visibly verifies "no network calls" rather than inferring it from code review alone. |
| Windows Power Plan (`Settings > Power` or `powercfg`) | Set the presentation laptop to **High performance** / **Best performance**, not Balanced/Battery Saver, before measuring or presenting | Balanced/power-saver plans throttle sustained CPU clocks on Windows laptops, directly inflating llama.cpp decode latency. Zero-risk, one-click, high-payoff — check this explicitly on the actual presentation laptop rather than assuming AC power alone is sufficient. |
| OBS Studio | Primary defense fallback: pre-recorded screen capture of a full successful demo run (load page → paste sample scam text → risk tier + explanation renders → paste a benign message → paste an edge case) | Version `32.1.2` (stable, released 2026-04-21), free, open-source (GPL-2.0), fully offline, no account or subscription. Use "Display Capture" or "Window Capture," export to a local MP4. Record in advance under realistic conditions (same laptop, same power plan) so playback timing matches what the committee would otherwise see live. |
| Windows Game Bar (`Win+G`, built-in) | Secondary/backup recorder if OBS setup time is a concern | Already ships with Windows 10/11, zero install. Less capture-region control than OBS, but useful as a fallback-of-the-fallback if OBS setup can't be completed in time. |
| PowerPoint/Keynote embedded video | Delivery mechanism for the recorded fallback | Embed the MP4 directly into the defense slide deck rather than keeping it as a separate file to alt-tab to — turns a failed live demo into "advance to next slide" instead of a visible app-switch scramble. |

## Installation

```bash
# Pin the exact validated inference version — do NOT let a fresh install
# silently resolve to a newer, unvalidated llama-cpp-python.
python -m pip install -e ".[dev,runtime]" "llama-cpp-python==0.3.23"

# Dev-only diagnostics (not part of the shipped runtime path)
python -m pip install psutil==7.2.2 py-spy==0.4.2

# Playwright browsers for the new browser-driven smoke test.
# NOTE: this installs Playwright's OWN bundled Chromium for the automated
# test only — it does NOT affect what browser opens for the live demo
# (webbrowser.open_new_tab uses the OS default browser). If browsers are
# already installed for the scraper, this is a no-op.
python -m playwright install chromium

# OBS Studio — download the Windows installer directly (not via pip):
# https://obsproject.com/download  (version 32.1.2, Windows 10/11 64-bit)
```

```toml
# pyproject.toml — tighten the open-ended runtime pin and add explicit dev diagnostics
[project.optional-dependencies]
dev = [
    "pytest>=9.0",
    "psutil==7.2.2",
    "py-spy==0.4.2",
]
runtime = [
    "llama-cpp-python==0.3.23",
]
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|--------------------------|
| Reuse existing Playwright for browser E2E smoke test | `pytest-playwright` plugin | If you want pytest fixtures (`page`, `browser`) and built-in HTML reporting for a longer-lived test suite. For a one-off pre-defense smoke script, driving `playwright.sync_api` directly avoids one more dependency and config surface with no functional loss. |
| `llama_cpp` built-in `verbose=True` timings first | `py-spy` / full profiler first | Use `py-spy` only if verbose timings show the bottleneck sits *outside* `create_chat_completion` (unlikely given this codebase's caching, but worth ruling out before assuming a C++-side fix is needed). |
| OBS Studio for fallback recording | Native Windows Game Bar only | If time before the defense is extremely tight and one quick recording is all that's needed, Game Bar is faster with zero setup — acceptable as the *only* fallback if OBS setup can't be completed, but OBS gives more control over capture region/quality. |
| Exact-pin `llama-cpp-python==0.3.23` | Upgrade to `0.3.32` and re-validate | Only if a specific, named bug in `0.3.23` is actually blocking the defense and the fix is confirmed present in the `0.3.32` changelog — then budget real time to re-run the eval/UAT checks, not just a visual smoke test. |
| `psutil` for lightweight CPU/RAM sampling | Windows Task Manager / Resource Monitor (GUI, no install) | If you don't want any additional pip install at all, Task Manager's Performance tab gives the same CPU-utilization-during-inference signal manually, just without a saved log. Fine for a single manual check. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|--------------|
| Upgrading `llama-cpp-python` to latest (`0.3.32`) this close to the defense | Changelog includes chat-template loading fixes and KV-cache/embedding changes — behavior-affecting for a fine-tuned model's exact prompt/response path that has already been validated. A regression discovered on defense week has no time to fix. | Pin `==0.3.23` exactly; only upgrade with a specific, verified reason and time to re-run the release-gate eval. |
| Enabling GPU offload (`n_gpu_layers > 0`, Vulkan/CUDA build of `llama-cpp-python`) on the presentation laptop | Untested iGPU/driver combinations are one of the most common `llama.cpp` crash and correctness sources (driver mismatch, VRAM sizing, silent fallback to CPU with a confusing error). The project's own constraint is "CPU/iGPU baseline" — the validated path is CPU-only. | Keep `n_gpu_layers=0`; tune `n_threads`/power plan instead (see Stack Patterns below) if latency needs to improve. |
| Adding an observability/telemetry stack (Prometheus, Grafana, LangSmith, W&B) to watch the demo | Massive overkill for a single local demo verified by one person before one event; adds setup risk and moving parts with no payoff for this milestone. | `llama_cpp`'s built-in verbose timings + manual stopwatch + Task Manager, escalate to `py-spy` only if needed. |
| Selenium or Cypress (Node-based) for the E2E smoke test | Playwright is already installed and is the project's existing browser-automation dependency (used by the scraper). Adding a second, redundant browser-automation stack for one smoke test increases dependency surface for zero benefit. | Playwright `sync_api`, driven directly in a plain script or `pytest` test. |
| Cloud-based screen recorders (Loom, Camtasia trial, cloud-synced OBS projects) | Violates the offline/local-first posture of the whole project and risks needing network access or an account login on defense day. | OBS Studio (fully offline, GPL, free) or Windows Game Bar. |
| Leaving `llama-cpp-python>=0.3` and `playwright>=1.58` unbounded in `pyproject.toml` | Any fresh install (a new laptop, a wiped venv, someone else helping set up) can silently resolve to a newer minor/patch version than what was actually validated, right when reproducibility matters most. | Exact-pin both for the remainder of this milestone; loosen again post-defense if desired. |

## Stack Patterns by Variant

**If the presentation laptop has a different core count than this dev machine:**
- Do not assume `n_threads=None` (library auto-pick) is optimal on a different CPU. Run a one-time diagnostic (`verbose=True` for a single `vnphish analyze` call) on the actual presentation laptop, then try setting `n_threads` to the laptop's *physical* core count (not logical/hyperthreaded count) as a bounded experiment — community guidance and llama.cpp's own maintainers note 4-8 threads is often the sweet spot for short-context CPU inference, and more threads can *hurt* via memory contention. Only ship the change if it measurably helps on that exact machine; otherwise leave the default.
- Because CPU-bound decode throughput does not scale linearly with thread count past the memory-bandwidth ceiling, and this is a common regression, not just an upside, in llama.cpp community discussions.

**If time allows only one latency intervention before the defense:**
- Set the laptop's Windows power plan to High performance and re-measure before touching any code or model config.
- Because this is zero-risk (no code change, fully reversible) and Balanced/power-saver throttling is a common, easy-to-miss cause of "why is it slower on this laptop than my dev machine."

**If the live demo fails during the defense:**
- Have the OBS-recorded MP4 embedded directly in the slide deck as the primary fallback, and a Playwright-scripted PNG screenshot sequence (of the same sample inputs) as a secondary, playback-risk-free fallback if video codec/driver issues also affect the presentation machine.
- Because a video can fail to play (codec, driver, audio-monitor routing) in ways a static image cannot — a screenshot sequence is the most degradation-resistant fallback available using tools already in the stack.

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|------------------|-------|
| `llama-cpp-python==0.3.23` | Python 3.13.x (Windows, 64-bit) | Confirmed installed and importable in this exact environment (`3.13.13`). Re-verify a wheel (not source build) installs on the presentation laptop's Python 3.13.x before the defense — a source build under time pressure with no compiler toolchain is a real failure mode for this library. |
| `playwright==1.60.0` | Python 3.13.x | Already installed and working (`sync_playwright` import verified in this environment). `python -m playwright install chromium` is needed only for the new automated smoke test, not for the live demo itself. |
| `psutil==7.2.2` | Python 3.13.x | Already resolvable in this environment (currently only via `train` extra's transitive chain); pin it directly under `dev` so it doesn't silently disappear on a `[dev,runtime]`-only install. |
| `wsgiref` (stdlib) | Any CPython 3.x | No compatibility risk — ships with Python. |

## Sources

- Codebase inspection (HIGH confidence): `src/runtime/analyzers/gguf.py`, `src/runtime/demo.py`, `src/runtime/service.py`, `src/runtime/doctor.py`, `src/data_pipeline/processing/normalizer.py`, `tests/runtime/test_demo.py`, `pyproject.toml`; installed package versions confirmed via `pip show`/`pip list` and `inspect.signature(llama_cpp.Llama.__init__)` in this exact environment.
- [llama-cpp-python PyPI](https://pypi.org/project/llama-cpp-python/) and [Changelog](https://llama-cpp-python.readthedocs.io/en/stable/changelog/) — confirmed latest release `0.3.32` (2026-06-29) vs. installed `0.3.23`. MEDIUM confidence (WebSearch-derived changelog summary, not directly diffed).
- [Diagnosing Latency in llama-cpp-python Wrapper for Short Prompts — GitHub Discussion #2073](https://github.com/abetlen/llama-cpp-python/discussions/2073) — confirms Python/C++ boundary overhead and pre-warming as the standard mitigation; this project's `GGUFAnalyzer` already caches the loaded runtime, so this overhead is already mitigated in this codebase. MEDIUM confidence.
- [Optimal parameters for parallel inference — llama.cpp GitHub Discussion #18308](https://github.com/ggml-org/llama.cpp/discussions/18308) and community CPU-tuning writeups on `n_threads`/`n_batch` — MEDIUM confidence, cross-checked against the library's own default signature (`n_threads=None`, `n_batch=512`, `flash_attn=False`) inspected directly in this environment (HIGH confidence for the defaults themselves).
- [OBS Project official download](https://obsproject.com/download) plus version-tracking cross-check — confirmed current stable `32.1.2` (2026-04-21), free/open-source/offline. MEDIUM confidence.
- [pytest-localserver PyPI](https://pypi.org/project/pytest-localserver/) — considered and rejected in favor of the project's existing `wsgiref.util.setup_testing_defaults` pattern (already proven in `tests/runtime/test_demo.py`) plus Playwright for real-browser coverage; no new dependency needed for WSGI-level testing. LOW confidence, informational only (not adopted).
- [py-spy PyPI](https://pypi.org/project/py-spy/) — confirmed latest version `0.4.2` (2026-04-24). MEDIUM confidence.

---
*Stack research for: Demo verification & presentation hardening (v5.1 milestone)*
*Researched: 2026-07-02*
