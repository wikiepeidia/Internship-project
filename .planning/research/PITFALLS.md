# Pitfalls Research: Last-Mile Hardening of a Local Offline LLM Demo Before a Live Thesis Defense

**Domain:** Verifying/hardening an existing local demo (Python `wsgiref` backend + vanilla JS chat UI + GGUF-quantized LLM via llama.cpp-style inference) in the final ~2 weeks before a live, offline, high-stakes academic presentation (13-20 July 2026).
**Researched:** 2026-07-02
**Confidence:** MEDIUM-HIGH (mixed: several findings verified directly against this repo's source; general demo-day and llama.cpp/OS behavior corroborated by external sources; a few items are reasoned from known OS/hardware behavior without a project-specific test yet)

This is not a "what tech should we pick" research pass — the stack is frozen (`wsgiref`, vanilla JS, GGUF). The risk surface here is entirely **verification and environment discipline**: does the thing that already works on the dev machine still work, unattended, offline, on battery, in front of a committee, with no do-overs.

## Critical Pitfalls

### Pitfall 1: Environment drift between the dev machine and the actual presentation laptop

**What goes wrong:**
The demo is verified and "works" on the machine it was built on, but the presentation laptop is a different physical machine (or the same machine after a reset/update) with different drive letters, missing off-repo files, or a different Python environment. The demo fails to start, or starts but silently falls back to a degraded backend, at the worst possible moment.

**Why it happens:**
This repo already stores model artifacts **off-repo** at an absolute Windows path (`D:\PROJEct\AI MODELS`), overridden via a git-ignored `.env/.env` file (`MODEL_ARTIFACT_ROOT`, `MODEL_REGISTRY_PATH`), specifically to dodge OneDrive sync interference (per `.planning/STATE.md`). That means:
- `.env/.env` is **not tracked in git** — a fresh clone or a different laptop has no such file until someone manually recreates it from `.env.example`.
- The model registry stores **absolute paths** (`D:\...`). If the presentation laptop assigns model storage to a different drive letter (e.g., an external SSD mounts as `E:` instead of `D:`), or the files were copied but not into the identical directory structure, the registry silently points at nothing.
- The project itself lives inside a **OneDrive-synced folder** (`OneDrive - caugiay.edu.vn\...`). If the presentation laptop's OneDrive client hasn't finished syncing, or uses Files On-Demand placeholders, opening/reading repo files (even just Python source) can stall or trigger a cloud fetch — exactly the sync interference the off-repo model path was designed to avoid, but for the *code*, not the model.
- `runtime-profile`, `runtime_backend`, and other settings come from environment variables / `.env`, which are invisible in a code diff — nothing in git review will catch a config drift.

**How to avoid:**
- Treat the presentation laptop as the **only machine that matters** for the last verification pass — do not trust "it worked on my dev machine" as sufficient evidence.
- Do a **full dry run from a cold clone**: wipe or use a second user account / fresh checkout, manually create `.env/.env` from `.env.example`, and confirm `vnphish doctor` reports `READY` with zero manual troubleshooting beyond the documented setup steps.
- Verify the absolute model paths in `.env/.env` and in `model-registry.json` actually resolve to files that exist **on the exact drive letter the presentation laptop will use**. If using an external/USB drive, plug it into the presentation laptop once beforehand and confirm the drive letter is stable across reboots (Windows can reassign drive letters).
- If the presentation laptop is different from the dev laptop, pre-sync OneDrive fully and switch to "Always keep on this device" for the whole repo folder before travel, or better: copy the repo out of OneDrive into a plain local folder for the presentation to remove sync as a variable entirely.
- Run `vnphish doctor` on the actual presentation laptop and require a clean `READY` at least 48 hours before the defense window (13 July), with a second confirmation the morning of.

**Warning signs:**
- `vnphish doctor` has only ever been run on the primary dev machine.
- `.env/.env` was last edited/created weeks ago and nobody has re-verified the paths since.
- The presentation laptop is undecided this close to the defense window.
- OneDrive sync status icon shows "syncing" or "online-only" on repo files.

**Verification category:** Offline/portability check (primary), Functional verification (secondary — nothing else is testable until this passes)

---

### Pitfall 2: Cold-start / model-load timing does not match the rehearsed number

**What goes wrong:**
The team rehearses pacing around a known "~13s warm CPU latency" figure (from `.planning/STATE.md`, measured after prompt/context optimization). On presentation day, the actual first response takes far longer — or the whole "Warming up local model..." startup step itself takes much longer than expected — creating dead air in front of the committee.

**Why it happens:**
- **mmap cold-cache effect:** llama.cpp-style loaders use `mmap` by default, which is fast (sub-2s) only when the OS page cache already holds the model file from a recent prior run. After a reboot, sleep/hibernate, or simply not having opened the file recently, the *first* load touches every page from disk, which can be 10-40x slower than the cached case (confirmed pattern across llama.cpp cold-start reports: mmap load can go from ~2s cached to ~15s+ uncached even on NVMe, and much worse on slower disks). The "~13s warm latency" number in this project's own state notes is explicitly a **warm** number — the doctor check does not measure or gate on cold-start behavior at all.
- **Antivirus first-touch scanning:** Windows Defender's real-time protection intercepts and scans files as they're read, and a large GGUF file (multi-GB) being mapped for the first time on the presentation laptop can add many extra seconds of latency the dev machine never showed (if the dev machine already has the file excluded or previously scanned/cached clean).
- **`doctor` checks existence, not performance:** Reading this project's `RuntimeDoctor` implementation, every check is a pass/fail on config, imports, and file presence (`backend-ready`, `runtime-profile`, etc.) — there is no timing assertion anywhere. A green `doctor` report gives false confidence that the demo will *feel* the same as it did during development.
- Presentation laptops are frequently rebooted the morning of (fresh Windows updates, printer setup, projector handshake) — guaranteeing a cold cache at the exact moment it matters most.

**How to avoid:**
- Rehearse the **worst case**, not the best case: reboot the presentation laptop, then immediately run `vnphish demo` and time everything from cold boot to first rendered answer, at least once per rehearsal day.
- Add the model file's directory (or file extension) to a Windows Defender exclusion on the presentation laptop ahead of time, and confirm this is allowed by the venue's device policy.
- Warm the model **once**, deliberately, a few minutes before walking into the room (open the demo, submit one throwaway sample message) so the OS page cache is hot when the real Q&A starts — but don't rely on this as the only safety net (see sleep/lock pitfall below, which can cold the cache again).
- If timing is still inconsistent, consider running `demo` and pre-warming it as the very first action after arriving in the presentation room, before the committee arrives, rather than as a live "watch it boot" moment.

**Warning signs:**
- The "~13s" figure has only ever been measured on a machine that was recently used for development (hot disk cache, hot OS scheduler).
- No one has timed a true cold boot → first answer path.
- Windows Defender has not been checked for exclusions on the model directory.

**Verification category:** Functional verification, Edge-case verification (cold-start is itself an edge case that must be tested explicitly, not assumed away by the warm-path doctor check)

---

### Pitfall 3: The "offline, local-first" demo has a hardcoded internet dependency

**What goes wrong:**
The UI explicitly advertises "Local-first" / "Không gửi dữ liệu lên cloud" (no cloud data sent) in its own header copy, but `index.html` loads its primary typeface from Google Fonts over the network:

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700&display=swap" rel="stylesheet">
```

If the presentation venue has no internet access (common for locked-down defense rooms, or simply flaky campus wifi), the browser will spend time attempting these connections (each `preconnect`/stylesheet fetch has its own DNS/TCP/TLS timeout), then silently fall back to the CSS `font-family` fallback stack. The visual result is a different, untested font rendering — and specifically risks resurfacing the Vietnamese-diacritic-stacking problem that Be Vietnam Pro was chosen to fix (per this project's own `STATE.md`: "Font target: Be Vietnam Pro renders Vietnamese diacritics without stacking"). This is also a credibility risk: a committee member technical enough to open DevTools' Network tab during a "fully offline, local-only" demo would see outbound requests to Google's CDN.

**Why it happens:**
Google Fonts (and other CDN-hosted assets — analytics snippets, icon fonts, CSS frameworks) are added during UI development for convenience and never revisited once the "it looks good" milestone is reached, because on a dev machine with internet, they always resolve near-instantly and the dependency is invisible.

**How to avoid:**
- Self-host the Be Vietnam Pro `.woff2` files under `/static/fonts/` and switch `index.html`/CSS to local `@font-face` declarations — removes the network dependency entirely and removes any timeout risk on a slow/no connection.
- Grep the entire `demo_assets` directory (HTML/CSS/JS) for any other `http(s)://` reference before sign-off — this is the single highest-value offline-verification check to run, since a hardcoded remote URL is invisible in normal (online) testing.
- As part of offline verification, physically disconnect Wi-Fi/Ethernet (or use OS airplane mode) on the test laptop and load the demo fresh — do not just trust code review to catch this.

**Warning signs:**
- Anyone can search the codebase for `googleapis.com`, `gstatic.com`, `cdn.`, `unpkg`, or `jsdelivr` and get a hit in a supposedly offline-first asset directory. (This search currently returns a hit in `src/runtime/demo_assets/index.html`.)
- The demo has never actually been tested with Wi-Fi/Ethernet fully disabled — only tested "on my machine" with normal internet running in the background.

**Verification category:** Offline/portability check — this is the single most concrete, already-confirmed finding in this research pass.

---

### Pitfall 4: Laptop power plan / battery state silently changes CPU inference speed

**What goes wrong:**
The demo is rehearsed on AC power with a "Balanced" or "Performance" power plan, producing the expected ~13s latency. On the day, the laptop runs on battery (podium has no outlet nearby, or the presenter unplugs to walk to the front), and Windows' battery-saving power plan throttles the CPU — inference now takes visibly longer, breaking the rehearsed pacing and possibly making it look like the system "hung."

**Why it happens:**
Windows power plans directly gate CPU maximum processor state: "Balanced" can throttle CPU down significantly on battery, and "Battery saver" is explicitly designed to reduce CPU/background performance to extend runtime. Since this is a CPU-bound GGUF inference workload (not GPU-accelerated on the baseline path), the effect is directly visible in generation latency, not hidden behind GPU headroom the way a lighter workload might tolerate it.

**How to avoid:**
- Always run the live demo **on AC power**, with the laptop plugged in before the presentation starts, and verify the outlet/extension cord situation at the venue in advance (do not assume one exists near the podium).
- Set the Windows power plan to "Best performance" / "High performance" (or pin max processor state to ~100%) explicitly on the presentation laptop, and re-check this setting the morning of — Windows updates and "recommended settings" prompts can silently reset power plans.
- Rehearse at least once **unplugged** on whatever the actual battery level will realistically be (e.g., 60-80%, not 100%) to know the worst-case latency, in case power is lost mid-demo.
- Disable "Battery saver auto-triggers below X%" during the presentation window so a struggling battery doesn't unexpectedly throttle performance without a proactive prompt.

**Warning signs:**
- All latency testing so far has happened plugged in on the dev machine.
- No one has checked which power plan is active on the specific laptop that will be used.
- The venue's podium power situation has not been scouted.

**Verification category:** Functional verification (performance is part of "does it behave as demonstrated"), Edge-case verification (battery-only operation is a real edge case for a laptop-based live demo).

---

### Pitfall 5: No rehearsed fallback, or a fallback that was never actually tested under failure conditions

**What goes wrong:**
The plan is "if the live demo breaks, show a recording/screenshots instead" — but the fallback asset doesn't exist yet, is out of date relative to the current UI, or nobody has actually rehearsed switching to it under time pressure. The presenter freezes or over-apologizes when the live system fails, which experienced demo-day post-mortems consistently identify as more damaging to audience trust than the technical failure itself.

**Why it happens:**
"We'll have a fallback" is treated as a checkbox rather than a rehearsed artifact. Recordings get made once early, then the UI changes (chat bubble redesign, i18n copy edits, a fixed latency bug) and the recording now shows a stale interface that contradicts what's on screen if both are shown side by side, or raises a "wait, why does the live one look different" question.

**How to avoid:**
- Record the fallback **last**, only after all other verification/fix work for this milestone is frozen — never record it first and consider it done.
- Script the fallback narration exactly like the live path: same sample scam message, same expected risk tier and explanation output, so switching between live and recorded feels seamless rather than like admitting failure.
- Actually rehearse the failure-to-fallback transition at least once: deliberately kill the demo process or disconnect power mid-sentence during a practice run, and practice the verbal pivot ("let me show you a recorded run of this same flow") rather than only rehearsing the happy path.
- Keep the fallback in at least two forms — a short screen recording (video) and a handful of annotated screenshots — since video playback itself can fail (wrong file, codec issue, no audio output cable) and a static screenshot fallback is more robust as a last resort.
- Store the fallback locally on the presentation laptop itself (not only cloud storage) — the same offline assumptions that apply to the demo apply to the backup plan.

**Warning signs:**
- The fallback recording predates the most recent UI or latency fix.
- Nobody has practiced narrating over the fallback out loud.
- The fallback only exists in one format, or only in cloud storage.

**Verification category:** Fallback verification — this is the entire purpose of this category; a fallback that hasn't been rehearsed under simulated failure is not verified, it's just recorded.

---

### Pitfall 6: Last-minute UI/prompt fixes silently exceed the tuned context window or break template wiring

**What goes wrong:**
A late "quick fix" to the UI (e.g., adding a field, lengthening placeholder/help text, tweaking the prompt for a fixed wording issue) pushes the effective prompt size past the tightly-tuned `GGUF_CONTEXT_WINDOW=512` budget, or breaks the `data-slot` template contract the JS relies on to render results — and the regression only shows up on specific inputs (e.g., long pasted messages), which may not be the exact samples used in earlier rehearsals.

**Why it happens:**
This project's own history shows the context window and prompt were deliberately shrunk to hit the ~13s target (`GGUF_CONTEXT_WINDOW=512`, `GGUF_COMPLETION_MAX_TOKENS=250`, ~130-150 token stripped prompt, per `STATE.md`) — this is a tight, already-optimized budget with very little headroom. Similarly, the front-end templates were migrated from raw `id` attributes to `data-slot` selectors specifically to avoid ID-collision bugs (`STATE.md`: "Phase 16 must update `demo.js` from old inner-ID queries to `data-slot` selectors"). Any "last-minute" fix that touches prompt text, adds a UI field that flows into the request payload, or edits `index.html`/`demo.js` templates risks silently reintroducing exactly the bug classes that were already fixed, because these fixes are easy to forget once the code "looks fine" in a quick visual check.
- The `runtime_max_text_chars` enforcement (mentioned in `STATE.md`) exists specifically to keep the stripped prompt inside `n_ctx=512` — a UI or prompt-template change that bypasses this path or changes what gets concatenated into the prompt (e.g., adding the channel name in a verbose way) could quietly erode that safety margin without any error, just gradually more truncated/degraded output.

**How to avoid:**
- Freeze any prompt-template edits after the fix list is settled and re-run the full test suite (`tests/runtime`) plus a manual long-message input test after every edit, not just the sample messages already known to work.
- For any UI change: search for existing tests before hand-editing `index.html`/`demo.js` (`tests/runtime/test_demo.py`) and add the smallest possible diff, re-confirming `data-slot` internals are preserved rather than reintroducing bare `id` attributes inside cloned templates.
- Treat "fix any UI quirks surfaced during verification" (an explicit v5.1 active item) as a change that must go through the same edge-case re-test pass as the original build — a fix for one bug is a regression risk for the others.
- Do one final full run-through of all in-scope threat classes plus edge cases (empty input, very long text, malformed/non-scam text) **after** the last UI/prompt fix lands, not before.

**Warning signs:**
- A UI or prompt fix is made and only the specific reported bug is re-tested, not the full sample matrix.
- No one has re-run `tests/runtime/test_demo.py` after the most recent change.
- Long-message edge case wasn't part of the smoke test for the latest fix.

**Verification category:** Functional verification (regression re-check), Edge-case verification (long input specifically threatens this budget).

---

## Moderate Pitfalls

### Pitfall 7: `wsgiref`'s single-threaded nature resurfaces under live, nervous UI interaction

**What goes wrong:**
`wsgiref.simple_server` processes one request at a time on a single thread (confirmed in this repo's own `demo.py` and already documented in this project's prior UI-revamp pitfall research as issue "C2"). A presenter who double-clicks "Phân tích tại máy" out of nerves, or a committee member who submits a second message while the first is still computing (very plausible given ~13s+ latency), can trigger a second request that queues behind the first at the TCP level and appears to hang.

**Why it happens:**
The original fix (`currentController?.abort()` before each new `fetch`, catching `AbortError` silently) was implemented for the chat-UI revamp, but any UI change since then (or an accidental revert) could silently drop this guard, and it is easy to miss in a visual-only review since the bug only manifests under rapid double-submission, not normal single-message use.

**How to avoid:**
Explicitly re-test rapid double-submit (click twice fast, or submit while a prior request is still spinning) as a scripted edge case in this verification pass, not just as a "we fixed this once" assumption. Confirm the abort-controller guard is still present in the current `demo.js`.

**Verification category:** Edge-case verification.

---

### Pitfall 8: CLI entrypoint confusion between `vnphish analyze` and `vnphish demo`

**What goes wrong:**
`vnphish analyze` is a text-only, no-browser flow that reads from `--text` or stdin and prints to the terminal; `vnphish demo` starts the web UI and opens a browser tab. This is already flagged as a known issue in `PROJECT.md` ("Fix CLI entrypoint confusion"). If the presenter (or a helper running the laptop) types the wrong command live, or a rehearsed script/shortcut points at the wrong subcommand, the audience sees a terminal window instead of the expected browser UI, or vice versa.

**Why it happens:**
Both subcommands share the same `vnphish` prefix and overlapping purpose (both "analyze a message"), but one is a CLI debug/automation tool and the other is the actual presentation surface. Notably, `analyze` calls `run_runtime_doctor()` as a pre-flight readiness gate, while `demo` does not call the same top-level doctor — it only calls `service.backend.doctor()` internally inside `run_demo_server`. These are two different readiness-check code paths with potentially different coverage, so "I ran `vnphish doctor` and it passed" does not guarantee `vnphish demo` will encounter the exact same checks at startup.

**How to avoid:**
- Prepare a single, unambiguous launcher (a desktop shortcut, batch file, or clearly labeled terminal alias) that runs exactly `vnphish demo` with the correct flags, so there is no live decision to make about which subcommand to type.
- Run `vnphish doctor` AND a full `vnphish demo` startup (through to a rendered browser page) as two separate explicit checks in the final verification pass — do not treat a passing `doctor` as proof that `demo` will start cleanly.
- Rename or add a help note distinguishing the two subcommands if there's any remaining time budget, per the already-planned fix in `PROJECT.md`.

**Verification category:** Functional verification.

---

### Pitfall 9: Screensaver, sleep, lock screen, or OS update prompts interrupting a live demo

**What goes wrong:**
Vietnamese explanation text can take real time to read aloud; if the presenter talks for 60-90 seconds without touching the keyboard/mouse, the default Windows sleep/lock/screensaver timeout can trigger mid-sentence, requiring a password re-entry in front of the committee. Separately, Windows Update "restart required" nags, or a background app update popping a dialog, can steal focus or force a reboot at the worst time.

**Why it happens:**
Default OS power/lock settings are tuned for everyday productivity use, not for a scenario where the screen is the primary presentation surface but keyboard/mouse activity is intermittent.

**How to avoid:**
Set the presentation laptop's sleep/screen-lock timeout to "Never" (or a generous value like 60+ minutes) for the duration of the defense window, disable Windows Update's automatic restart notifications/scheduling for that day, and put the machine in Airplane Mode or otherwise block update checks entirely (this also reinforces the offline posture from Pitfall 3).

**Verification category:** Offline/portability check, Fallback verification (this is exactly the kind of live disruption the fallback plan should be ready to absorb).

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|-----------------|------------------|
| Load Be Vietnam Pro from Google Fonts CDN instead of self-hosting | Fast to wire up during UI development | Breaks the "local-first / offline" claim exactly when it matters most (no-network venue) | Never for the final presentation build — acceptable only during early dev iteration |
| Skip the cold-boot timing rehearsal because "warm latency was already measured" | Saves rehearsal time | Rehearsed pacing doesn't match reality if the laptop was rebooted that morning | Never this close to the defense; acceptable earlier when latency work was still in progress |
| Treat a green `vnphish doctor` as sufficient proof the demo will run | Quick confidence check | Doctor checks config/existence, not performance, power state, or network isolation — false sense of readiness | Acceptable as one signal among several, never as the sole verification step |
| Record the fallback video early and consider it "done" | One less task on the list | Fallback drifts out of sync with UI/latency fixes made afterward | Never — always record fallback last, after the fix list is frozen |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|-----------------|-------------------|
| Google Fonts CDN (`fonts.googleapis.com`, `fonts.gstatic.com`) | Assuming `preconnect`/`display=swap` degrades gracefully enough to ignore offline | Self-host the `.woff2` files under `/static/` and use local `@font-face`; test with network fully disabled |
| Off-repo model registry (`D:\PROJEct\AI MODELS`) | Assuming absolute paths and drive letters carry over to a different laptop unchanged | Verify the exact drive letter and directory structure on the actual presentation laptop before the defense window; consider a relative or configurable root if time allows |
| Windows Defender real-time protection | Assuming first-run model load timing on the presentation laptop matches dev-machine timing | Add the model directory/extension to a Defender exclusion (where policy allows) and re-time cold start after doing so |
| `wsgiref.simple_server` (single-threaded) | Assuming the earlier AbortController fix is still intact after later UI edits | Explicitly re-test rapid double-submit as part of this verification pass, don't assume a past fix persists |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|-----------------|
| Cold mmap page cache after reboot/sleep | First inference after boot is far slower than the rehearsed ~13s figure | Pre-warm the model once with a throwaway message before the committee arrives; time a true cold-boot path at least once | Every reboot, sleep, or long idle period on the presentation laptop |
| Battery-saver / non-performance power plan | CPU-bound GGUF generation visibly slows down or stutters | Force "High performance" power plan, stay plugged into AC throughout | Any time the laptop is unplugged or Windows auto-switches power mode near a low battery threshold |
| Antivirus first-touch file scanning on a multi-GB GGUF file | Unexplained extra delay only on the presentation laptop, not the dev machine | Add exclusion for the model directory ahead of time (if policy allows) | First access to the model file per boot/session on a machine where it hasn't been scanned/cached yet |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Loading a remote font/CDN asset while marketing the tool as privacy-preserving/local-only | Undermines the core thesis claim in front of the exact audience evaluating that claim; a technical committee member checking DevTools Network tab sees outbound calls | Self-host all static assets; verify zero outbound network calls with Wi-Fi disabled |
| Binding the demo server to a non-loopback host (e.g., `0.0.0.0`) to "share" it over venue Wi-Fi for a projector or second screen | Exposes the local analysis endpoint to anyone else on the same network segment during the defense | Keep the default `127.0.0.1` binding; if a second screen is needed, mirror the primary laptop's display instead of exposing the server over the network |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|--------------|-------------------|
| Font fallback silently swaps in a font that stacks Vietnamese diacritics incorrectly when the Google Fonts CDN is unreachable | Vietnamese text renders visibly wrong exactly during the live demo, undermining polish in front of the committee | Self-host Be Vietnam Pro so the tested, diacritic-safe font is guaranteed regardless of network state |
| Presenter or helper types `vnphish analyze` when `vnphish demo` was intended (or vice versa) | Wrong surface shown live (terminal vs. browser), visible confusion during a high-stakes moment | Pre-built, clearly labeled launcher shortcut that always runs the correct command with the correct flags |
| No visible "processing" affordance during a slow cold-start load | Committee may think the system has frozen/crashed during the "Warming up local model..." step | Confirm the console message and/or browser UI clearly signals "loading, please wait" during doctor warm-up, and rehearse narrating over it |

## "Looks Done But Isn't" Checklist

- [ ] **Offline claim:** Often missing a full network-disabled test pass — verify by disabling Wi-Fi/Ethernet entirely and reloading the demo from a fresh browser tab, confirming zero failed/pending network requests in DevTools.
- [ ] **`vnphish doctor` passing:** Often mistaken for full readiness — verify by also running `vnphish demo` end-to-end through to a rendered first answer, since `doctor` and `demo`'s internal readiness check are not the same code path.
- [ ] **"~13s latency" figure:** Often measured only warm, on the dev machine — verify by timing a true cold boot → first answer path on the actual presentation laptop, on battery and on AC.
- [ ] **Fallback recording:** Often stale relative to the current UI/latency — verify by watching it back-to-back against a live run immediately after the last UI/prompt fix lands.
- [ ] **Edge case coverage (empty input, very long text, malformed/non-scam text):** Often re-tested only for the originally reported bug, not the full matrix, after each late fix — verify by re-running the complete edge-case set after every UI/prompt change, not a subset.
- [ ] **Environment parity:** Often assumed identical to the dev machine — verify `.env/.env` exists and resolves correctly, and that model registry paths point at files that actually exist, on the exact laptop and drive letters used for the defense.

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|----------------|-----------------|
| Live demo fails to load or times out during the defense | LOW (if rehearsed) | Switch immediately to the pre-recorded fallback video/screenshots with a calm, matter-of-fact line ("let me show you a recorded run of this same flow") rather than apologizing at length |
| Font fails to load due to no network, Vietnamese text looks visually broken | LOW | Self-host the font before the defense window; if discovered live, continue — it is a cosmetic issue, not a functional failure, and should not derail the presentation |
| Demo appears to hang after a double-submit | MEDIUM | Refresh the browser tab (in-memory history is lost, which is expected/acceptable per this project's privacy-by-design choice) and resubmit once; rehearse this exact recovery motion beforehand so it looks intentional, not panicked |
| Laptop battery dies or power plan throttles mid-demo | MEDIUM | Have a charged spare laptop with the identical `.env`/model setup as a hot spare, verified working before the defense window, not just "the same laptop, hopefully plugged in in time" |

## Pitfall-to-Verification-Category Mapping

This milestone's four verification categories (per `.planning/PROJECT.md`) are: **Functional**, **Offline/portability**, **Edge-case**, **Fallback**.

| Pitfall | Verification Category | How to Verify Prevention Worked |
|---------|------------------------|-----------------------------------|
| Environment drift (dev machine vs. presentation laptop) | Offline/portability | `vnphish doctor` returns clean `READY` on the exact presentation laptop from a fresh checkout with manually recreated `.env/.env` |
| Cold-start/model-load timing surprise | Functional + Edge-case | Timed cold-boot-to-first-answer run on the presentation laptop, on both AC and battery, matches or beats rehearsed pacing |
| Hardcoded Google Fonts CDN dependency | Offline/portability | Demo loads and renders correctly with Wi-Fi/Ethernet fully disabled; zero pending/failed network requests in DevTools |
| Power plan / battery throttling CPU inference | Functional + Edge-case | Latency measured unplugged on realistic battery level matches the plugged-in baseline closely enough not to disrupt pacing |
| No rehearsed fallback | Fallback | A dry run where the live demo is deliberately killed mid-flow, and the presenter successfully narrates the transition to the recorded fallback without dead air |
| Late UI/prompt fix exceeds context window or breaks templates | Functional + Edge-case | Full edge-case matrix (empty, very long, malformed input) re-passes after every fix, plus `tests/runtime` suite green |
| `wsgiref` single-thread re-entrant submit regression | Edge-case | Rapid double-submit test explicitly re-run and confirmed non-blocking after any JS change |
| CLI entrypoint confusion (`analyze` vs `demo`) | Functional | A single, tested launcher/shortcut exists that always invokes the correct subcommand; no live typing of raw commands required |
| Sleep/lock/update interruptions | Offline/portability + Fallback | Sleep/lock timeout set to effectively "never" and Windows Update paused for the defense window, verified the morning of |

## Sources

- Repository evidence (HIGH confidence, verified directly): `src/runtime/demo_assets/index.html` (Google Fonts CDN links), `src/runtime/demo.py` (`wsgiref.simple_server`, single-request handling), `src/runtime/cli.py` (`analyze` vs `demo` subcommands, differing doctor-check paths), `src/runtime/doctor.py` (`RuntimeDoctor` checks are config/existence-only, no timing/power/network checks), `.planning/STATE.md` (off-repo model root rationale, OneDrive sync interference history, `GGUF_CONTEXT_WINDOW=512` budget, ~13s warm latency figure, prior `wsgiref` re-entrant fetch bug and fix), `.planning/PROJECT.md` (v5.1 milestone scope and known active issues), `.gitignore` (`.env/` excluded from version control).
- [llama.cpp mmap cold-start behavior discussion](https://markaicode.com/architecture/llamacpp-architecture/) — MEDIUM confidence, corroborated by multiple community reports of cold vs. warm mmap load time differences (seconds vs. tens of seconds).
- [Windows Defender real-time protection slowing first file access](https://learn.microsoft.com/en-us/answers/questions/2732424/windows-defender-real-time-protection-service-slow) — MEDIUM confidence, official Microsoft Q&A plus multiple independent reports; exclusion-based mitigation is a documented Defender feature.
- [Google Fonts silently depending on network at every page load](https://medium.com/@bogdanpshonyak/using-google-fonts-offline-b327467e0999) and related offline-Google-Fonts issue reports — MEDIUM confidence, consistent across multiple independent sources.
- [Windows power plan / battery saver CPU throttling](https://www.xda-developers.com/your-windows-power-plan-is-probably-wrong/) — MEDIUM confidence; general Windows power-management behavior, consistent across multiple sources, though exact throttling percentage varies by device/driver.
- [Live demo failure recovery patterns ("confident composure", pre-recorded fallback, rehearsing failure not just the happy path)](https://www.reprise.com/resources/blog/the-art-of-failing-forward-demo-lessons-learned) — MEDIUM confidence, sales/product-demo domain rather than academic defense specifically, but the failure-recovery psychology and rehearsal discipline transfer directly.

---
*Pitfalls research for: last-mile hardening of a local offline LLM demo before a live thesis defense*
*Researched: 2026-07-02*
