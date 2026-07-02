# Phase 29: Environment Parity & Offline Verification - Research

**Researched:** 2026-07-02
**Domain:** Windows environment-variable portability (pydantic-settings), self-hosted web fonts, offline/network-isolation verification of a local WSGI demo, exact dependency pinning
**Confidence:** HIGH — nearly every claim below was verified directly in this exact repo/environment during this research session (empirical command runs), not inferred from general knowledge.

## Summary

This phase closes three concrete, already-identified gaps, all narrowed in scope by CONTEXT.md's D-01/D-02 (presentation laptop = this dev machine, no fresh-install simulation): (1) `MODEL_ARTIFACT_ROOT`/`MODEL_REGISTRY_PATH` must become permanent OS-level environment variables via `setx` so `vnphish` works from any working directory; (2) Be Vietnam Pro must be self-hosted instead of loaded from Google Fonts CDN; (3) `llama-cpp-python` must be exact-pinned in `pyproject.toml`. A fourth item, ENV-02 (prove offline operation), is procedurally different from the other three — it requires an actual physical network disconnect, which this research found has a hard, non-negotiable constraint: **the disconnect step cannot be performed by an autonomous coding-agent action**, because the agent's own operation depends on the same network connectivity being cut. This must be structured as a human-executed manual checklist, not an automated task.

Every fix in this phase is empirically verified in this exact session, not just researched in the abstract. Setting `MODEL_ARTIFACT_ROOT`/`MODEL_REGISTRY_PATH` as OS environment variables was tested directly against `src/config/settings.py` from a simulated non-repo-root working directory and confirmed to correctly override the CWD-relative `.env/.env` fallback-to-defaults behavior — this is the exact mechanism ENV-04 needs, and it is now proven to work, not assumed. Google's own CSS2 API was queried live with a modern browser User-Agent and returned 12 real, directly-downloadable `.woff2` URLs (4 weights × 3 subsets: vietnamese/latin-ext/latin) hosted on `fonts.gstatic.com` — these are the exact bytes currently being loaded from the CDN, now available to vendor locally with zero visual-regression risk. Reading `src/runtime/demo.py` directly revealed a finding CONTEXT.md did not anticipate: there is **no generic static-file route** in the WSGI app — every asset path is hardcoded (`/static/demo.css`, `/static/demo.js`, `/static/i18n.js`). Self-hosting fonts is therefore not a files-only change; it requires a small, deliberately narrow new route in `demo.py`, guarded by an exact-filename allowlist to avoid introducing a path-traversal-capable generic file server.

**Primary recommendation:** Treat ENV-04 as a pure environment-variable change (empirically verified fix, zero code risk), ENV-03 as a small-but-real `demo.py` code change (new allowlisted font route) plus a one-time vendoring step, ENV-05 as a `pyproject.toml` edit with no fresh-install re-test, and ENV-02 as a human-executed manual runbook (not an autonomous agent task) with the agent only handling setup/teardown/evidence-recording around the human-performed network-disconnect window.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Model path resolution (`MODEL_ARTIFACT_ROOT`/`MODEL_REGISTRY_PATH`) | API/Backend (`src/config/settings.py`, pydantic-settings) | OS-level (Windows registry via `setx`) | `Settings` reads the value; the OS registry is where the permanent override is stored — both tiers matter for ENV-04 to hold across reboots |
| Font asset self-hosting | Frontend Server (`src/runtime/demo.py` static route) | Browser/Client (`@font-face` rendering) | `demo.py`'s WSGI app owns serving the bytes; the browser owns interpreting `@font-face`/`unicode-range` — no CDN/edge tier remains after this fix |
| Offline/network-isolation proof (ENV-02) | Browser/Client (DevTools Network tab, physical NIC state) | API/Backend (loopback-only `wsgiref` server, already `127.0.0.1`-bound) | The claim being proven is entirely about what the browser attempts to reach over the network; the backend's job is just to confirm it never initiates outbound calls (already true — `GGUFAnalyzer` loads a local file, no `transformers`/`huggingface_hub` imports) |
| Dependency exact-pinning (ENV-05) | API/Backend (`pyproject.toml` build/install config) | — | Pinning constrains what `pip` resolves for the backend runtime; no other tier is involved |
| `vnphish doctor` readiness re-check (ENV-01) | API/Backend (`src/runtime/doctor.py`) | — | Zero-network, config/existence-only readiness probe; already built, reused as-is per D-02 |

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** The presentation machine is the same laptop used for development — NOT a separate machine. This significantly narrows this phase's scope compared to the original research assumption (which treated "the presentation laptop" as an unknown, possibly-different machine).
- **D-02:** No fresh-install simulation (new venv, new profile, or clean clone) is needed for ENV-01. Phase 28's DIAG-01 already confirmed `vnphish doctor` reports READY on this exact machine. ENV-01 for this phase is reduced to a sanity re-check — confirm doctor still passes — not a from-scratch install test.
- **D-03:** Fix the CWD-relative `.env/.env` model-path fragility by setting **permanent Windows environment variables** via `setx MODEL_ARTIFACT_ROOT` and `setx MODEL_REGISTRY_PATH` — not a launcher script. Current values to preserve: `MODEL_ARTIFACT_ROOT=D:\PROJEct\AI MODELS`, `MODEL_REGISTRY_PATH=D:\PROJEct\AI MODELS\manifests\model-registry.json`. After setting, verify by launching `vnphish doctor` from a working directory OTHER than the repo root and confirming it still resolves the correct off-repo model path.
- **D-04:** Self-host Be Vietnam Pro by downloading the official `.woff2` files directly from Google Fonts (same weights: 400, 500, 600, 700) and vendoring them into `src/runtime/demo_assets/fonts/` (or similar). Do NOT drop the font for a system fallback. Replace the Google Fonts `<link>` lines in `index.html` with local `@font-face` declarations. After the fix, grep all demo assets for any remaining `http(s)://` reference to confirm this was the only CDN dependency.
- **D-05:** Prove offline capability by **actually disabling Wi-Fi/Ethernet** on the laptop during the test, then running the full golden-prompt flow (locked scam + benign prompts from Phase 28) through the real web demo. Do not settle for a lighter grep-only or DevTools-only check. After the network-disabled run succeeds, also confirm via DevTools Network tab that zero external requests were attempted (secondary confirmation, not a replacement).

### Claude's Discretion

- Exact `setx` invocation syntax and whether to also set the vars in the current session is an implementation detail for the planner/executor.
- Exact vendored font file directory name/path structure under `demo_assets/` is Claude's call.
- How to re-enable Wi-Fi/confirm no side effects after the offline test (e.g. re-running doctor) is standard executor discretion.

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ENV-01 | `vnphish doctor` reports READY on the actual presentation laptop after a fresh install | Narrowed by D-01/D-02 to a sanity re-check only. Re-ran `python -m src.runtime.cli doctor` directly in this session on 2026-07-02: `READY backend=gguf local_only=True text_only=True`, all 11 checks PASS — confirms Phase 28's DIAG-01 result still holds. No fresh install performed or needed. See Common Pitfalls #8 for the scope-creep risk of over-reading the ROADMAP wording. |
| ENV-02 | Demo functions correctly with network/Wi-Fi disabled — zero external requests observed in DevTools | See "Offline Verification Execution Model" pattern below — this is the one requirement in this phase that is NOT a standard autonomous task; it requires a human-executed manual runbook. `netsh interface show interface` (run live in this session) shows this machine has 6 active/enabled interfaces (Wi-Fi, Ethernet, Ethernet 2, Radmin VPN, 2× VMware virtual adapters) — the human must disable ALL physical adapters (Wi-Fi + both Ethernet entries), not just "Wi-Fi", for the test to be a true zero-connectivity proof. |
| ENV-03 | Be Vietnam Pro font is self-hosted instead of loaded from the Google Fonts CDN | 12 real `.woff2` URLs (4 weights × 3 subsets) fetched live from Google's CSS2 API in this session — see Code Examples. `demo.py` has no generic static-file route, so this also requires a small, allowlisted new route (see Architecture Patterns). Grep of `src/runtime/demo_assets/` confirms exactly 3 CDN lines in `index.html` (lines 8, 9, 11) and one unrelated false-positive hit in `demo.js` (a fake `.example` URL embedded in phishing sample text — not a network dependency). |
| ENV-04 | `MODEL_ARTIFACT_ROOT`/`MODEL_REGISTRY_PATH` set as OS-level env vars, independent of CWD-relative `.env/.env` | Empirically verified in this session: simulating CWD=`C:/` reproduces the exact bug (`Settings` falls back to `data/models` / `data/manifests/model-registry.json`); setting the two vars as process environment variables from the same simulated CWD immediately fixes it, resolving to the correct off-repo `D:\PROJEct\AI MODELS\...` paths. `setx` is confirmed (official Microsoft docs) to only affect NEW terminal sessions, never the one it was run in — the verification sequence in Code Examples accounts for this. |
| ENV-05 | `llama-cpp-python` exact-pinned to `0.3.23` in `pyproject.toml` | `pyproject.toml` currently has `runtime = ["llama-cpp-python>=0.3"]` (open-ended) — needs to become `==0.3.23`. Currently-installed version confirmed via `python -c "import llama_cpp; print(llama_cpp.__version__)"` in this session: `0.3.23` — already matches. See "ENV-05 Scope Resolution" below for the recommended narrow interpretation that avoids reintroducing a fresh-install requirement. |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

`./CLAUDE.md` in this repo contains only GSD workflow meta-instructions (use the get-shit-done skill for `gsd-*` commands, prefer matching custom agents from `.github/agents`, don't apply GSD workflows unless explicitly asked, always offer a next-step prompt after completing a deliverable). It contains no technical coding conventions specific to this codebase. The technical hard constraints that DO apply to this phase come from `.planning/STATE.md`'s "Hard constraints" list, already reflected elsewhere in this document:
- No JS frameworks, no build step — vanilla HTML/CSS/JS only (the font self-hosting fix must be plain `@font-face` CSS, no CSS preprocessor/bundler).
- Backend (synchronous `wsgiref` + `POST /api/analyze`) is frozen; no behavior changes. The new font-serving route is an **additive** GET route for a static asset, not a change to `/api/analyze` — consistent with this constraint.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `llama-cpp-python` | `==0.3.23` (exact pin; already installed) | GGUF local inference backend | This is the exact version the project's validated latency/behavior was measured against (confirmed installed via direct `import llama_cpp; llama_cpp.__version__` check in this session). Upstream latest on PyPI is `0.3.32` (confirmed via `pip index versions llama-cpp-python` in this session) — tightening the pin prevents a future `pip install` from silently resolving to an unvalidated newer version. |
| `pydantic-settings` | `2.14.1` (already installed, no change needed) | `.env`/env-var config resolution | No version change required — this phase only relies on already-shipped, already-installed behavior (OS env vars override `.env` file values). Confirmed via `pip show pydantic-settings` in this session. |

**No new packages are introduced by this phase.** ENV-03's font files are static assets (not a Python/JS package); ENV-04's fix is an OS-level environment-variable change; ENV-05 only tightens an existing pin.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `setx`-based permanent OS env vars (D-03, locked) | A `.bat` launcher script that sets env vars per-invocation | Rejected by the user in discussion: a launcher only helps if the user remembers to always use it; `setx` works from any terminal/shortcut forever with zero per-launch discipline. |
| Downloading `.woff2` directly from Google's own CSS2 API response (`fonts.gstatic.com`) | A third-party self-hosting helper site (e.g. `gwfh.mranftl.com` / google-webfonts-helper) | The third-party helper is a well-known, widely-used community tool, but D-04 explicitly asks for "the official .woff2 files directly from Google Fonts" — querying Google's own `css2` endpoint with a modern browser User-Agent returns direct `fonts.gstatic.com` URLs (Google's own CDN host), avoiding any third-party intermediary entirely. |
| Allowlist-based new font route in `demo.py` | A generic `/static/<path>` catch-all reading any file under `demo_assets/` | A catch-all is less code but reintroduces a classic path-traversal attack surface (`../../` escaping `demo_assets/`) in a WSGI app that currently has zero such surface — not worth it for 12 known, fixed filenames. |

**Installation:** No `pip install` commands are needed for new packages. The only install-adjacent change is editing `pyproject.toml`'s existing `runtime` extra (see Code Examples) — this does not require re-running `pip install -e .[dev,runtime]` per D-01/D-02's explicit skip of fresh-install simulation.

**Version verification:**
```bash
# Confirm current installed version matches the target pin (already done in this research session):
python -c "import llama_cpp; print(llama_cpp.__version__)"
# => 0.3.23  (verified 2026-07-02, this exact environment)

pip index versions llama-cpp-python
# => INSTALLED: 0.3.23   LATEST: 0.3.32  (verified 2026-07-02, PyPI registry)
```

## Package Legitimacy Audit

This phase introduces **zero new packages**. `llama-cpp-python` is an existing dependency already installed and used since Phase 3 of this project (multiple prior milestones' worth of validated use). ENV-05 only tightens the pin from `>=0.3` to `==0.3.23` in `pyproject.toml` — it does not add a new dependency or change what is currently installed.

`slopcheck` could not be installed in this research session (blocked by the sandbox's untrusted-code-integration policy, which is a reasonable default posture, not a research failure). Since no new package is being introduced, the full slopcheck gate is not the relevant control here; instead, direct PyPI registry verification was performed:

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|--------------|-----------|-------------|
| `llama-cpp-python` | PyPI | Est. 2023-present, 190+ published versions from `0.1.1` through `0.3.32` (confirmed via `pip index versions`) | Well-established, widely used llama.cpp Python binding | [github.com/abetlen/llama-cpp-python](https://github.com/abetlen/llama-cpp-python) | Not run (sandbox-blocked); PyPI history strongly indicates legitimate, long-lived project | Approved — pre-existing dependency, tightening pin only, no new install surface |

**Packages removed due to slopcheck `[SLOP]` verdict:** none (no slopcheck run; no new packages).
**Packages flagged as suspicious `[SUS]`:** none.

*Because slopcheck was unavailable, this row would normally be tagged `[ASSUMED]` per protocol — however, since `llama-cpp-python` is not a new install (it has been running in this exact environment across multiple prior milestones and its PyPI version history was directly queried in this session), the planner does not need a `checkpoint:human-verify` gate before editing the pin. A gate would only be warranted if this phase were introducing a *new* package.*

## Architecture Patterns

### System Flow: The Three Code-Touching Fixes

```
ENV-04 (env vars)                    ENV-03 (fonts)                       ENV-05 (pin)
─────────────────                    ───────────────                     ─────────────
[Human/executor runs]                [One-time: fetch 12 .woff2          [Edit pyproject.toml]
  setx MODEL_ARTIFACT_ROOT ...         files from fonts.gstatic.com]        runtime = [
  setx MODEL_REGISTRY_PATH ...              │                                "llama-cpp-python==0.3.23"
        │                                   ▼                               ]
        ▼                            [Vendor into                                │
[Windows registry,                    demo_assets/fonts/]                        ▼
 HKEY_CURRENT_USER\Environment]             │                             [No re-install needed —
        │                                   ▼                              already-installed version
        ▼ (new terminal only)        [Edit index.html: remove             already matches the pin,
[Settings() reads OS env var          <link> CDN tags, add                confirmed 0.3.23 in this
 BEFORE .env/.env file,                <link rel="stylesheet"              session]
 confirmed by direct test              href="/static/demo.css">
 in this session]                      (unchanged) + new @font-face
        │                              rules in demo.css]
        ▼                                   │
[vnphish doctor from                        ▼
 non-repo-root CWD                    [Add allowlisted GET route
 resolves correct                      in demo.py: /static/fonts/<name>
 D:\PROJEct\AI MODELS\... path]        → serves from demo_assets/fonts/,
                                        Content-Type: font/woff2]
```

### Pattern 1: OS Environment Variable Precedence Over `.env` File (verified empirically)

**What:** `pydantic-settings`'s default source priority is: init args > OS environment variables > `.env` file values > field defaults. This was directly tested against this repo's `Settings` class in this research session.

**When to use:** ENV-04 — this is exactly the mechanism that makes `setx`-based permanent env vars work without needing to touch or remove the existing `.env/.env` file's copies of the same two keys.

**Verified reproduction (run in this exact session):**
```bash
# Reproduce the bug: CWD outside repo root, .env/.env not found, falls back to repo-relative defaults
cd C:\
python -c "
from src.config.settings import get_settings
s = get_settings()
print(s.model_artifact_root)     # => data\models   (WRONG — repo-relative default)
print(s.model_registry_path)     # => data\manifests\model-registry.json   (WRONG)
"

# Prove the fix: set the two vars as process env vars from the same CWD
cd C:\
MODEL_ARTIFACT_ROOT="D:\PROJEct\AI MODELS" MODEL_REGISTRY_PATH="D:\PROJEct\AI MODELS\manifests\model-registry.json" python -c "
from src.config.settings import get_settings
s = get_settings()
print(s.model_artifact_root)     # => D:\PROJEct\AI MODELS   (CORRECT)
print(s.model_registry_path)     # => D:\PROJEct\AI MODELS\manifests\model-registry.json   (CORRECT)
"
```
Both commands were run directly in this session on 2026-07-02 and produced exactly the output shown. This is a `[VERIFIED: direct execution in this repo]` claim, the strongest confidence level available.

**Practical implication for D-03:** `.env/.env`'s existing `MODEL_ARTIFACT_ROOT`/`MODEL_REGISTRY_PATH` lines do **not** need to be edited or removed once the OS-level `setx` vars are set — they become harmless, always-overridden duplicates. (See Common Pitfall #4 for the maintenance trap this creates.)

**Source:** [Pydantic Settings docs](https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/) — `[CITED]`: "environment variables will always take priority over values loaded from a dotenv file." Cross-verified against direct execution in this repo — `[VERIFIED]`.

### Pattern 2: Allowlisted Static Font Route (new code, small and narrow)

**What:** `src/runtime/demo.py`'s `DemoApp.__call__` currently hardcodes exact-match routes for `/`, `/static/demo.css`, `/static/demo.js`, `/static/i18n.js`, and `POST /api/analyze` (confirmed by direct reading of the file — there is no generic static-file handler). Self-hosting fonts requires adding a new route, not just copying files.

**When to use:** ENV-03.

**Recommended implementation (exact-filename allowlist, not a generic path-join):**
```python
# in src/runtime/demo.py — additive only, does not touch /api/analyze or existing routes

FONT_DIR = ASSET_DIR / "fonts"
FONT_CONTENT_TYPE = "font/woff2"  # RFC 8081 / IANA-registered MIME type for WOFF2
KNOWN_FONT_FILES = frozenset({
    "be-vietnam-pro-400-vietnamese.woff2",
    "be-vietnam-pro-400-latin-ext.woff2",
    "be-vietnam-pro-400-latin.woff2",
    "be-vietnam-pro-500-vietnamese.woff2",
    "be-vietnam-pro-500-latin-ext.woff2",
    "be-vietnam-pro-500-latin.woff2",
    "be-vietnam-pro-600-vietnamese.woff2",
    "be-vietnam-pro-600-latin-ext.woff2",
    "be-vietnam-pro-600-latin.woff2",
    "be-vietnam-pro-700-vietnamese.woff2",
    "be-vietnam-pro-700-latin-ext.woff2",
    "be-vietnam-pro-700-latin.woff2",
})

# inside DemoApp.__call__, alongside the existing static routes:
if method == "GET" and path.startswith("/static/fonts/"):
    filename = path.removeprefix("/static/fonts/")
    if filename in KNOWN_FONT_FILES:
        return _text_response(
            start_response, "200 OK", FONT_CONTENT_TYPE, (FONT_DIR / filename).read_bytes()
        )
    return _json_response(start_response, "404 Not Found", {"error": {"message": "Not found", "steps": []}})
```
This reuses the existing `_text_response`/`_json_response` helpers with zero changes to their signatures. The allowlist means a request for `/static/fonts/../../.env/.env` (or any other path-traversal attempt) simply misses the set membership check and falls through to 404 — there is no filesystem path construction from unvalidated user input at all, closing off the path-traversal class entirely rather than trying to sanitize it.

**Test pattern to follow** (matches the existing `test_demo_static_assets_are_served` in `tests/runtime/test_demo.py`):
```python
def test_demo_font_assets_are_served():
    app = _build_test_app()
    status, headers, body = _call_app(app, method="GET", path="/static/fonts/be-vietnam-pro-400-vietnamese.woff2")
    assert status.startswith("200")
    assert dict(headers)["Content-Type"] == "font/woff2"
    assert body  # non-empty bytes
```

### Pattern 3: Self-Hosted `@font-face` CSS (exact replacement for the CDN `<link>` tags)

**What:** Replace the 3 CDN lines in `index.html` (lines 8, 9, 11 — the two `<link rel="preconnect">` tags and the `css2` stylesheet link) with nothing (delete them), and add the following block to the **top** of `demo.css` (before the existing `:root` block), preserving `demo.css`'s existing single `<link rel="stylesheet" href="/static/demo.css">` reference in `index.html` (line 13) unchanged.

**Source of the exact `unicode-range`/weight data below:** fetched live from Google's own CSS2 API in this research session (`curl -A "Mozilla/5.0 ... Chrome/124.0.0.0 ..." "https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700&display=swap"`), then verified one URL downloads successfully (`HTTP 200`, `content_type: font/woff2`, `11532` bytes for the 400-weight vietnamese subset). This is `[VERIFIED: live API response, this session, 2026-07-02]` — these are the exact same bytes the CDN `<link>` currently serves, now to be vendored.

```css
/* Self-hosted Be Vietnam Pro — replaces Google Fonts CDN <link> tags.
   Fetched from Google's own fonts.gstatic.com CDN and vendored locally; see 29-RESEARCH.md. */
@font-face {
  font-family: 'Be Vietnam Pro';
  font-style: normal;
  font-weight: 400;
  font-display: swap;
  src: url('/static/fonts/be-vietnam-pro-400-vietnamese.woff2') format('woff2');
  unicode-range: U+0102-0103, U+0110-0111, U+0128-0129, U+0168-0169, U+01A0-01A1, U+01AF-01B0, U+0300-0301, U+0303-0304, U+0308-0309, U+0323, U+0329, U+1EA0-1EF9, U+20AB;
}
@font-face {
  font-family: 'Be Vietnam Pro';
  font-style: normal;
  font-weight: 400;
  font-display: swap;
  src: url('/static/fonts/be-vietnam-pro-400-latin-ext.woff2') format('woff2');
  unicode-range: U+0100-02BA, U+02BD-02C5, U+02C7-02CC, U+02CE-02D7, U+02DD-02FF, U+0304, U+0308, U+0329, U+1D00-1DBF, U+1E00-1E9F, U+1EF2-1EFF, U+2020, U+20A0-20AB, U+20AD-20C0, U+2113, U+2C60-2C7F, U+A720-A7FF;
}
@font-face {
  font-family: 'Be Vietnam Pro';
  font-style: normal;
  font-weight: 400;
  font-display: swap;
  src: url('/static/fonts/be-vietnam-pro-400-latin.woff2') format('woff2');
  unicode-range: U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD;
}
@font-face {
  font-family: 'Be Vietnam Pro';
  font-style: normal;
  font-weight: 500;
  font-display: swap;
  src: url('/static/fonts/be-vietnam-pro-500-vietnamese.woff2') format('woff2');
  unicode-range: U+0102-0103, U+0110-0111, U+0128-0129, U+0168-0169, U+01A0-01A1, U+01AF-01B0, U+0300-0301, U+0303-0304, U+0308-0309, U+0323, U+0329, U+1EA0-1EF9, U+20AB;
}
@font-face {
  font-family: 'Be Vietnam Pro';
  font-style: normal;
  font-weight: 500;
  font-display: swap;
  src: url('/static/fonts/be-vietnam-pro-500-latin-ext.woff2') format('woff2');
  unicode-range: U+0100-02BA, U+02BD-02C5, U+02C7-02CC, U+02CE-02D7, U+02DD-02FF, U+0304, U+0308, U+0329, U+1D00-1DBF, U+1E00-1E9F, U+1EF2-1EFF, U+2020, U+20A0-20AB, U+20AD-20C0, U+2113, U+2C60-2C7F, U+A720-A7FF;
}
@font-face {
  font-family: 'Be Vietnam Pro';
  font-style: normal;
  font-weight: 500;
  font-display: swap;
  src: url('/static/fonts/be-vietnam-pro-500-latin.woff2') format('woff2');
  unicode-range: U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD;
}
@font-face {
  font-family: 'Be Vietnam Pro';
  font-style: normal;
  font-weight: 600;
  font-display: swap;
  src: url('/static/fonts/be-vietnam-pro-600-vietnamese.woff2') format('woff2');
  unicode-range: U+0102-0103, U+0110-0111, U+0128-0129, U+0168-0169, U+01A0-01A1, U+01AF-01B0, U+0300-0301, U+0303-0304, U+0308-0309, U+0323, U+0329, U+1EA0-1EF9, U+20AB;
}
@font-face {
  font-family: 'Be Vietnam Pro';
  font-style: normal;
  font-weight: 600;
  font-display: swap;
  src: url('/static/fonts/be-vietnam-pro-600-latin-ext.woff2') format('woff2');
  unicode-range: U+0100-02BA, U+02BD-02C5, U+02C7-02CC, U+02CE-02D7, U+02DD-02FF, U+0304, U+0308, U+0329, U+1D00-1DBF, U+1E00-1E9F, U+1EF2-1EFF, U+2020, U+20A0-20AB, U+20AD-20C0, U+2113, U+2C60-2C7F, U+A720-A7FF;
}
@font-face {
  font-family: 'Be Vietnam Pro';
  font-style: normal;
  font-weight: 600;
  font-display: swap;
  src: url('/static/fonts/be-vietnam-pro-600-latin.woff2') format('woff2');
  unicode-range: U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD;
}
@font-face {
  font-family: 'Be Vietnam Pro';
  font-style: normal;
  font-weight: 700;
  font-display: swap;
  src: url('/static/fonts/be-vietnam-pro-700-vietnamese.woff2') format('woff2');
  unicode-range: U+0102-0103, U+0110-0111, U+0128-0129, U+0168-0169, U+01A0-01A1, U+01AF-01B0, U+0300-0301, U+0303-0304, U+0308-0309, U+0323, U+0329, U+1EA0-1EF9, U+20AB;
}
@font-face {
  font-family: 'Be Vietnam Pro';
  font-style: normal;
  font-weight: 700;
  font-display: swap;
  src: url('/static/fonts/be-vietnam-pro-700-latin-ext.woff2') format('woff2');
  unicode-range: U+0100-02BA, U+02BD-02C5, U+02C7-02CC, U+02CE-02D7, U+02DD-02FF, U+0304, U+0308, U+0329, U+1D00-1DBF, U+1E00-1E9F, U+1EF2-1EFF, U+2020, U+20A0-20AB, U+20AD-20C0, U+2113, U+2C60-2C7F, U+A720-A7FF;
}
@font-face {
  font-family: 'Be Vietnam Pro';
  font-style: normal;
  font-weight: 700;
  font-display: swap;
  src: url('/static/fonts/be-vietnam-pro-700-latin.woff2') format('woff2');
  unicode-range: U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD;
}
```
The rest of `demo.css` already references `font-family: "Be Vietnam Pro", "Segoe UI Variable Display", system-ui, sans-serif;` (line 37) and needs no change — `@font-face` declarations are resolved by name, not by import location.

### Pattern 4: Offline Verification Execution Model — Human Checkpoint, Not Autonomous Task

**What:** ENV-02 requires actually cutting network connectivity on the machine and proving the demo still works. This research found a hard constraint CONTEXT.md did not flag: **the coding agent executing this phase's plan cannot safely perform the network-disconnect step itself**, because the agent's own session (Claude Code / any LLM-backed coding tool) depends on outbound network access to the model API to keep functioning. If an autonomous task ran `netsh interface set interface "Wi-Fi" disable`, the agent would lose its own connectivity mid-task with no way to re-enable it or report back — a self-inflicted, unrecoverable hang.

Additionally: `netsh interface set interface ... disable` requires an **elevated (Administrator) command prompt** (confirmed via Microsoft Q&A / community docs) — the current shell in this research session is confirmed NOT running as Administrator (`net session` check), so even ignoring the agent-network-dependency problem, the command would fail without a UAC elevation the agent cannot grant itself non-interactively.

**When to use:** Structure ENV-02 as a `checkpoint:human-verify`-style task in the plan: a written runbook the human executes themselves, with the agent only handling the before/after steps (drafting the runbook, preparing the golden-prompt text for copy-paste, and — after the human reports the outcome — re-running `vnphish doctor` to confirm no side effects and recording the evidence in a plan artifact).

**Recommended human runbook (for the plan to embed verbatim):**
1. Open the demo normally first: `vnphish demo` (confirms nothing is already broken before going offline).
2. Open browser DevTools (F12) → Network tab → check "Preserve log".
3. Physically disable ALL of: Wi-Fi, Ethernet, Ethernet 2 (this machine has 6 listed interfaces including a VPN and 2 VMware virtual adapters — confirmed via `netsh interface show interface` in this session; the two physical adapter groups are the ones that matter, since virtual/VPN adapters route through them and go dead automatically once the physical NICs are down). Use Windows Settings → Network & Internet (no admin/CLI needed for the toggle switches) rather than `netsh` (which needs elevation).
4. In the browser, paste the locked scam golden prompt (from `.planning/phases/28-baseline-readiness-zero-code-diagnostics/artifacts/28-golden-prompt-results.json`), submit, confirm `high-risk` + `bank_impersonation` renders correctly.
5. Paste the locked benign golden prompt, submit, confirm `benign` renders correctly.
6. In DevTools Network tab, confirm every request shown is to `127.0.0.1:8765` (or the demo's configured port) — zero entries for any other host, zero "failed"/red entries for `fonts.googleapis.com`/`fonts.gstatic.com`.
7. Take a screenshot of the Network tab as evidence.
8. Re-enable Wi-Fi/Ethernet.
9. Report back to the agent/session; the agent then re-runs `vnphish doctor` to confirm the network toggle had no lingering side effects, and records the screenshot + outcome in the phase's artifacts.

**Trade-offs:** This is slower than an automated test but is the only safe structure given the agent's own network dependency — there is no code-only workaround that preserves both "the agent runs the test" and "the agent survives the test."

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|--------------|-----|
| TTF→WOFF2 font conversion | A local conversion pipeline (fonttools/woff2 CLI) | Google's own CSS2 API, queried with a modern browser User-Agent string, already returns direct `.woff2` URLs (confirmed live in this session) | Zero conversion tooling needed; the bytes are already in the target format, hosted by Google itself |
| Generic static-file serving for `/static/*` | A catch-all path-join handler reading any file under `demo_assets/` | A closed allowlist of exactly 12 known font filenames (Pattern 2 above) | The generic version reintroduces a path-traversal attack surface that does not currently exist anywhere in this WSGI app; the allowlist has zero such surface for a fixed, small file set |
| "Is Wi-Fi disabled" automation | A script that runs `netsh interface set interface ... disable`, waits, then re-enables it, orchestrated by the coding agent | A human-executed manual runbook (Pattern 4) | The agent's own network dependency makes self-disconnecting during its own task execution structurally unsafe — this is not a "nice to automate" gap, it is a real hazard |
| Environment-variable precedence logic | Custom `os.environ.get(...) or settings.field` override code in `src/config/settings.py` | `pydantic-settings`'s built-in precedence (OS env > `.env` file > defaults), already correct and already verified in this session | Adding manual override code duplicates logic pydantic-settings already implements correctly, and risks introducing a second source of truth that can drift from the library's actual behavior |

**Key insight:** every fix in this phase has an existing, already-correct mechanism to lean on (pydantic-settings precedence, Google's own font CDN as a font source, the existing `_text_response` helper pattern in `demo.py`) — the discipline here is *not building new machinery*, only wiring the two or three lines that connect the existing mechanism to this phase's specific gap.

## Common Pitfalls

### Pitfall 1: Treating "disable Wi-Fi and test" as an autonomous, scriptable task

**What goes wrong:** A plan writes ENV-02 as a normal task with bash commands to disable/re-enable the network interface. The agent executing it loses its own connectivity mid-task (its own session depends on the same network path being tested) and cannot recover or report the result.
**Why it happens:** It looks superficially automatable — "just run `netsh interface set interface X disable`" — but the agent doing the disabling is itself a network-dependent process.
**How to avoid:** Structure ENV-02 as a human checkpoint per Pattern 4. The plan should never contain a bash/PowerShell step that disables the machine's own active network adapter as an unattended action.
**Warning signs:** A plan task for ENV-02 has no `checkpoint:human-verify` marker and lists `netsh`/network-toggle commands as agent-executed steps.

### Pitfall 2: Disabling only "Wi-Fi" while other interfaces stay connected

**What goes wrong:** The human disables the Wi-Fi adapter, sees the demo still "works offline," but Ethernet 2 or a VPN adapter is still connected and passing traffic — the test doesn't actually prove what it claims to.
**Why it happens:** "Disable Wi-Fi" is the instinctive read of D-05's wording, but this machine (confirmed via `netsh interface show interface` in this session) has 6 listed interfaces: Wi-Fi, Ethernet, Ethernet 2, Radmin VPN, and 2 VMware virtual adapters — several show as "Connected."
**How to avoid:** The runbook must explicitly disable BOTH physical adapter groups (Wi-Fi and all Ethernet entries), not just the one named in casual conversation. Virtual/VPN adapters (Radmin, VMware) tunnel through the physical NICs, so they should go inert automatically once the physical adapters are down — but the human should glance at their status after disabling the physical NICs as a sanity check.
**Warning signs:** `netsh interface show interface` (run before starting the test) shows more than one "Connected" physical interface, and the runbook only mentions disabling one of them.

### Pitfall 3: Assuming self-hosting fonts is a files-only change

**What goes wrong:** The font files get downloaded and vendored, `index.html`'s `<link>` tags get removed, but the browser shows the fallback font (`Segoe UI Variable Display`) because nothing actually serves `/static/fonts/*.woff2` — a 404.
**Why it happens:** `src/runtime/demo.py` has no generic static-file route (confirmed by direct reading in this session) — every asset path is an exact-match hardcoded route. "Self-host the font" sounds like a pure-asset change, but it requires a matching backend route.
**How to avoid:** Treat ENV-03 as two linked deliverables: (1) vendor the files + rewrite the CSS, AND (2) add the allowlisted route in `demo.py` (Pattern 2) plus a route test.
**Warning signs:** After the fix, `curl http://127.0.0.1:8765/static/fonts/be-vietnam-pro-400-vietnamese.woff2` returns 404.

### Pitfall 4: `.env/.env`'s duplicate values becoming silently dead after `setx`

**What goes wrong:** Months from now, someone edits `.env/.env`'s `MODEL_ARTIFACT_ROOT` line to point at a new location (e.g., after moving the model files), restarts `vnphish`, and is confused when it still uses the old path — because the OS-level `setx` variable (set once in this phase, forgotten about) always wins.
**Why it happens:** OS environment variables unconditionally override `.env` file values in pydantic-settings (verified in this session) — there's no warning or indication that the `.env/.env` edit did nothing.
**How to avoid:** Leave `.env/.env`'s two lines in place (no functional need to remove them — see Pattern 1), but add a one-line comment directly above them noting they're superseded by permanent OS-level env vars set via `setx` on [date], so a future maintainer edits the right thing.
**Warning signs:** A future `.env/.env` change to these two keys has no observable effect after a fresh terminal.

### Pitfall 5: Testing `setx`'s effect in the same terminal that ran it

**What goes wrong:** Immediately after running `setx MODEL_ARTIFACT_ROOT ...`, someone runs `echo %MODEL_ARTIFACT_ROOT%` in the SAME window and sees nothing (or the old value) — and concludes the fix failed, when actually `setx` simply never updates the currently-running shell's environment.
**Why it happens:** Confirmed directly from Microsoft's own `setx` documentation: "Variables set with setx are available in future command windows only, not in the current command window."
**How to avoid:** The verification sequence (Code Examples) must explicitly close the terminal and open a brand-new one before checking. This is the literal mechanism behind ENV-04's success criterion #4 ("launching `vnphish` from a working directory other than the repo root").
**Warning signs:** A verification step checks the env var in the same shell session where `setx` was just run.

### Pitfall 6: Treating the `demo.js` `.example` URL grep hit as a real CDN leak

**What goes wrong:** The mandated grep sweep for `http(s)://` (D-04's verification step) finds a hit in `demo.js` line 17: `https://vpbank-secure.example` — someone "fixes" it by removing the URL from the sample scam text, unintentionally weakening the golden/sample prompt's realism (a phishing message with a fake link IS the point of that sample text).
**Why it happens:** A naive grep can't distinguish "a URL embedded in sample phishing text as bait content" from "an actual network dependency." `.example` is an IANA-reserved TLD (RFC 2606) specifically meant to never resolve — it's inert by design.
**How to avoid:** When running the ENV-03 grep sweep, explicitly document this hit as a confirmed non-issue (reviewed, is example/sample content, not a live network call) rather than silently "fixing" it or silently ignoring it without a note.
**Warning signs:** The grep sweep evidence record doesn't mention the `demo.js` hit at all, or the sample text loses its embedded fake link.

### Pitfall 7: Path traversal in a naively-implemented font route

**What goes wrong:** If the new font-serving route is implemented as `(FONT_DIR / filename).read_bytes()` without the allowlist check, a request like `/static/fonts/../../.env/.env` or `/static/fonts/../../../pyproject.toml` could read arbitrary files relative to `FONT_DIR`.
**Why it happens:** `Path.__truediv__` (the `/` operator) does not sanitize `..` segments by default; a request path passed straight into a filesystem join is a classic path-traversal vector.
**How to avoid:** Use Pattern 2's exact-filename allowlist (`frozenset` membership check) rather than any path-join-and-resolve approach. This is a security-relevant pitfall specific to this phase's new code, not present anywhere else in the current `demo.py`.
**Warning signs:** The new route's code contains a `Path(...) / filename` construction without a preceding allowlist/membership check.

### Pitfall 8: Over-reading ENV-05's ROADMAP wording as requiring a fresh reinstall

**What goes wrong:** ROADMAP.md's success criterion #5 says "a fresh install on the presentation laptop resolves to exactly that version" — read literally, this could tempt someone to uninstall and reinstall `llama-cpp-python` (or worse, recreate a venv) just to "prove" the pin works, directly contradicting D-01/D-02's explicit instruction to skip fresh-install simulation entirely.
**Why it happens:** The ROADMAP wording was written before CONTEXT.md's D-01/D-02 narrowed the phase's scope (this is explicitly flagged in this phase's task description as a "known tension to resolve").
**How to avoid:** See "ENV-05 Scope Resolution" below — treat the pin edit + already-installed-version confirmation as sufficient; do not schedule any reinstall step.
**Warning signs:** A plan task for ENV-05 includes `pip uninstall llama-cpp-python` or `pip install --force-reinstall` anywhere in its steps.

## ENV-05 Scope Resolution

The additional-context prompt explicitly asked for a recommendation on how to interpret ENV-05 consistently with D-01/D-02. Based on this research:

**Recommended interpretation — two-part, no reinstall:**
1. **Static verification:** Edit `pyproject.toml`'s `runtime` extra from `llama-cpp-python>=0.3` to `llama-cpp-python==0.3.23`. This is a plain text edit, zero execution risk.
2. **Analytical verification (not empirical reinstall):** Confirm the *currently installed* version in this environment already equals `0.3.23` — already done in this research session via `python -c "import llama_cpp; print(llama_cpp.__version__)"` → `0.3.23`. Because `pip`'s dependency resolver deterministically honors exact pins (`==`) by construction — this is a guarantee of how pip's resolver works, not something that needs a fresh install to re-prove — the edited pin is sufficient evidence that any *future* install (fresh or otherwise) would resolve to the same version. This mirrors exactly the reasoning D-01/D-02 already applied to ENV-01 (an already-proven `doctor READY` state stands in for a fresh-install re-proof).

**What NOT to do:** Do not run `pip uninstall llama-cpp-python && pip install -e .[dev,runtime]` or create a new venv "just to be sure" — this would reintroduce exactly the fresh-install requirement the user explicitly declined for this milestone, and carries real risk this close to the defense (a source-build fallback if no wheel is cached, network dependency during a phase that's supposed to be about *removing* network dependencies, etc.).

**Flag for the planner:** ROADMAP.md's literal success-criterion wording ("a fresh install ... resolves to exactly that version") should be satisfied by the *pin itself being exact* plus the *already-confirmed installed version matching* — not by an actual re-run of the install. If the planner wants to close the letter of that success criterion more explicitly, the safest option is a one-line `pip show llama-cpp-python` re-confirmation (read-only, no reinstall) after the `pyproject.toml` edit, not a reinstall.

## Code Examples

### Setting the permanent OS-level environment variables (ENV-04)

```bash
# Run once, in any terminal (user-level scope — no admin/elevation needed,
# sufficient since this is a single-user presentation laptop per D-01):
setx MODEL_ARTIFACT_ROOT "D:\PROJEct\AI MODELS"
setx MODEL_REGISTRY_PATH "D:\PROJEct\AI MODELS\manifests\model-registry.json"
```
Source: [Microsoft Learn — setx](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/setx) `[CITED]` — quotes must wrap the value because it contains a space (`AI MODELS`); omit `/m` to avoid requiring an elevated prompt (user-scope is sufficient for a single-user machine).

### Verifying ENV-04's success criterion (must use a NEW terminal — Pitfall 5)

```bash
# Step 1: close the terminal that ran setx completely. Open a brand-new terminal window.
# (Confirmed: setx writes to the registry; only future command windows see the new value.)

# Step 2: confirm the vars are visible in the new terminal, with NO cd yet:
echo %MODEL_ARTIFACT_ROOT%
echo %MODEL_REGISTRY_PATH%

# Step 3: change to a directory OTHER than the repo root, then run doctor:
cd C:\
vnphish doctor
# Expected: "READY backend=gguf ..." with "backend-ready: PASS - backend=gguf ready=True"
# If it instead shows "NOT READY" with a detail like
# "Missing model registry: data\manifests\model-registry.json" (repo-relative, no D:\ prefix),
# the env var did not take effect for this shell — most likely cause: still using the OLD terminal.
```

### Fetching the official Be Vietnam Pro `.woff2` files (ENV-03)

```bash
# Query Google's own CSS2 API with a modern browser User-Agent to get real .woff2 URLs
# (a non-browser UA — e.g. curl's default — gets served TTF-only, no unicode-range,
#  confirmed by direct comparison in this research session):
curl -s -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36" \
  "https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700&display=swap" \
  > bevietnampro.css

# Extract the 12 unique woff2 URLs (4 weights x 3 subsets: vietnamese, latin-ext, latin):
grep -o 'https://fonts.gstatic.com/[^)]*\.woff2' bevietnampro.css | sort -u

# Download each one (rename to a descriptive filename matching Pattern 2's allowlist):
curl -s -o src/runtime/demo_assets/fonts/be-vietnam-pro-400-vietnamese.woff2 \
  "https://fonts.gstatic.com/s/bevietnampro/v12/QdVPSTAyLFyeg_IDWvOJmVES_Hw4BXoKZA.woff2"
# ... repeat for the remaining 11 URLs (see Pattern 3 for the full weight/subset -> URL mapping)
```
Confirmed live in this session: `HTTP 200`, `Content-Type: font/woff2`, `11532` bytes for the 400-weight vietnamese-subset file. `[VERIFIED: direct download in this session, 2026-07-02]`.

### Grep sweep for remaining CDN references (ENV-03 verification)

```bash
grep -rn "http://\|https://" src/runtime/demo_assets/
# Expected findings after the fix:
#   demo.js:17: ...https://vpbank-secure.example... <- CONFIRMED NON-ISSUE (Pitfall 6):
#     this is fake bait-link text inside the golden/sample phishing message, using the
#     IANA-reserved .example TLD (RFC 2606) which never resolves. It is not a network call.
#   (no other hits should remain — the 3 Google Fonts <link> lines in index.html
#    must be gone after the fix)
```

### Exact-pinning `llama-cpp-python` in `pyproject.toml` (ENV-05)

```toml
# Before:
runtime = [
    "llama-cpp-python>=0.3",
]

# After:
runtime = [
    "llama-cpp-python==0.3.23",
]
```
No reinstall needed — see "ENV-05 Scope Resolution" above.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| Be Vietnam Pro loaded from `fonts.googleapis.com`/`fonts.gstatic.com` via `<link>` CDN tags | Self-hosted `.woff2` files vendored under `demo_assets/fonts/`, served by a new allowlisted `demo.py` route | This phase (2026-07) | Removes the last confirmed offline-claim leak; demo works with zero external requests |
| `MODEL_ARTIFACT_ROOT`/`MODEL_REGISTRY_PATH` resolved only via CWD-relative `.env/.env` discovery | Permanent OS-level env vars (`setx`), with `.env/.env` retained as an always-overridden fallback | This phase (2026-07) | `vnphish` works from any launch directory/shortcut, not just when CWD happens to be the repo root |
| `llama-cpp-python>=0.3` (open-ended) | `llama-cpp-python==0.3.23` (exact pin) | This phase (2026-07) | Any future install (this machine or otherwise) is guaranteed to resolve the exact version the project's validated behavior was measured against, not silently drift to `0.3.32`+ |

**Deprecated/outdated:** None of the above are library deprecations — they are project-specific configuration hardening decisions unique to this pre-defense milestone.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Radmin VPN and the 2 VMware virtual network adapters observed as "Connected" on this machine cannot independently reach the public internet once the physical Wi-Fi/Ethernet adapters are disabled (they tunnel/route through the physical NICs, so disabling the physical adapters is sufficient without separately disabling the virtual ones) | Pattern 4 / Pitfall 2 | LOW-MEDIUM: if wrong, the ENV-02 offline test could show a false "zero external requests" result while a virtual adapter still has some residual path out — mitigated by the runbook's instruction to glance at all interface statuses after disabling the physical NICs as a sanity check |
| A2 | The `.woff2` files fetched from `fonts.gstatic.com` in this research session (version `v12` of the Be Vietnam Pro family, specific content-hashed filenames) will still be the current version if the plan is executed noticeably later than 2026-07-02 | Architecture Pattern 3 / Code Examples | LOW: if Google updates the font family version between research and execution, the specific gstatic.com hash URLs in this document may 404 — the mitigation is simply re-running the same `curl` command at execution time to get whatever URLs are current, which is a trivial re-fetch, not a design change |

**If this table is empty:** N/A — two low-risk environmental assumptions are logged above; neither affects the core architectural recommendations (OS-env-var precedence, allowlisted font route, exact pin) which are all `[VERIFIED]`, not assumed.

## Open Questions

1. **Does the presentation venue itself impose any network policy beyond what this dev-machine test can simulate (e.g., a captive portal, or a corporate/campus network with different DNS behavior)?**
   - What we know: This phase tests offline behavior on the actual presentation laptop (same machine per D-01), which resolves the "different machine" unknown entirely.
   - What's unclear: Whether the actual defense room's network environment differs from "no network at all" in some way that matters (e.g., if the presenter accidentally leaves Wi-Fi on and it auto-connects to a venue network with a captive portal that intercepts the Google Fonts request differently than a clean disconnect would). This is out of scope for Phase 29 (which tests "no network"), but worth a one-line mention in Phase 32's rehearsal.
   - Recommendation: No action needed in Phase 29; flag for Phase 32 (Fallback & Rehearsal) as a "confirm Wi-Fi is OFF, not just unconnected" pre-flight check.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `curl` | Downloading `.woff2` files from `fonts.gstatic.com` (ENV-03) | Yes | `8.21.0` (confirmed in this session) | — |
| Playwright (Python) | Reusable golden-prompt script (`scripts/verify_golden_prompts.py`) if the human wants an automated post-reconnect regression check | Yes | `1.60.0` (confirmed in this session) | Manual browser testing (the ENV-02 runbook is manual by design regardless — Pattern 4) |
| `llama-cpp-python` | GGUF inference backend | Yes | `0.3.23` (confirmed in this session, matches target pin exactly) | — |
| Windows Administrator/elevation | `netsh interface set interface ... disable` (NOT recommended — see Pattern 4) | No (current shell confirmed non-admin) | — | Use Windows Settings → Network & Internet toggle switches instead (no elevation needed); this is the recommended path, not a fallback-of-last-resort |
| `setx` | Permanent env var setting (ENV-04) | Yes (built into Windows, `cmd.exe`) | n/a (OS built-in) | — |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** Administrator elevation for `netsh`-based network toggling — fallback is the GUI Network & Internet settings toggle, which is actually the *preferred* path here (no elevation prompt, no risk of a typo'd interface name).

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-------------------|
| V2 Authentication | No | Demo has no auth surface; unchanged by this phase |
| V3 Session Management | No | No sessions; unchanged by this phase |
| V4 Access Control | No | No access-control surface changes |
| V5 Input Validation | Yes | The new font route's `filename` value (derived from `PATH_INFO`, technically attacker-influenceable if the server were ever exposed beyond loopback) must be validated via exact-match allowlist (Pattern 2), not passed into any filesystem path construction unchecked |
| V6 Cryptography | No | No cryptographic operations touched by this phase |
| V12 Files and Resources (informal, not in template list but directly relevant) | Yes | Same allowlist control as V5 above — this is specifically a "file access restricted to an intended directory" control class |
| V14 Configuration | Yes | Exact-pinning `llama-cpp-python==0.3.23` and moving model-path config to OS-level env vars are both configuration-hardening actions this phase performs |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|-----------------------|
| Path traversal via the new `/static/fonts/<filename>` route | Tampering / Information Disclosure | Exact-filename allowlist (`frozenset` membership check) before any filesystem read — Pattern 2, Pitfall 7 |
| Binding the demo server to a non-loopback host to "share" it over venue Wi-Fi | Spoofing / Information Disclosure | Out of scope for this phase's code changes, but worth reconfirming: `demo.py`'s default host remains `127.0.0.1` — this phase does not touch that binding, and should not (already flagged in prior milestone's PITFALLS.md as a "Security Mistake" to avoid) |
| Secrets exposure while documenting `.env/.env`'s preserved values | Information Disclosure | D-03 already scopes this correctly: only the two model-path keys are touched; the plan/executor must not read, log, or commit the full `.env/.env` file (which also contains unrelated API keys for Anthropic/OpenRouter/DeepSeek etc.) — this research session deliberately avoided reading the raw file content for this reason (a direct read attempt was in fact denied by file permissions, which is itself a reasonable existing protection) |

## Sources

### Primary (HIGH confidence — direct execution/reading in this session)
- `src/config/settings.py`, `src/runtime/doctor.py`, `src/runtime/demo.py`, `src/runtime/demo_assets/{index.html,demo.js,demo.css}`, `pyproject.toml` — read directly in this session.
- Direct empirical test: `Settings()` resolution from a simulated non-repo-root CWD, with and without OS-level env vars set — run directly in this session, 2026-07-02.
- `python -c "import llama_cpp; print(llama_cpp.__version__)"` → `0.3.23` — run directly in this session.
- `pip index versions llama-cpp-python` → confirms `0.3.23` installed, `0.3.32` latest on PyPI — run directly in this session.
- `curl -A "<modern Chrome UA>" "https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700&display=swap"` → 12 real `.woff2` URLs with `unicode-range` data — run directly in this session, 2026-07-02.
- Direct test download of one `.woff2` URL → `HTTP 200`, `Content-Type: font/woff2` — run directly in this session.
- `netsh interface show interface` and `net session` (admin-check) — run directly in this session, confirms 6 network interfaces and non-admin shell.
- `.planning/phases/28-baseline-readiness-zero-code-diagnostics/artifacts/28-golden-prompt-results.json` and `28-CONTEXT.md` — locked golden prompts for the ENV-02 runbook.

### Secondary (MEDIUM-HIGH confidence — official docs)
- [Pydantic Settings docs](https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/) — `[CITED]`, confirms OS env vars override `.env` file values; cross-verified by direct execution above (raises this to effectively HIGH confidence).
- [Microsoft Learn — setx](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/setx) — `[CITED]`, official syntax, confirms new-terminal-only effect and the 1024-character value limit (not a concern here — both values are well under that limit).
- RFC 8081 / IANA MIME type registration for `font/woff2` — `[CITED]` via WebSearch cross-referencing multiple independent sources (MDN-equivalent guidance, nginx ticket #1575 discussing the same registration).

### Tertiary (LOW confidence — WebSearch only, used for corroboration)
- General community guidance on `netsh interface set interface ... disable` requiring Administrator elevation — `[CITED]`, corroborated by direct `net session` non-admin check in this session, so treated as effectively verified for this specific machine.
- `google-webfonts-helper` (`gwfh.mranftl.com`) — surfaced during search but explicitly NOT recommended (see Alternatives Considered) since it is a third-party mirror, not "the official Google Fonts" source D-04 asked for.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new packages; existing pin/version directly confirmed via `pip`/`import` in this session.
- Architecture (env var precedence, font route, offline runbook): HIGH — the two highest-risk claims (pydantic-settings precedence, absence of a generic static route in `demo.py`) were both verified by direct execution/reading, not inference.
- Pitfalls: HIGH — pitfalls 1, 2, 5, 6, 7, 8 are all grounded in direct empirical findings from this session (network interface list, `setx` behavior, grep results, code reading); pitfalls 3 and 4 follow directly from those same findings.

**Research date:** 2026-07-02
**Valid until:** Effectively the remainder of this milestone (defense window opens 2026-07-13) — the empirically-verified claims (env var precedence, current installed version, absence of a generic static route) will not change on their own; only the font URL hashes (Assumption A2) carry any time-decay risk, and that risk is trivially mitigated by re-running the fetch command at execution time.
