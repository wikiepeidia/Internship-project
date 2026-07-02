# Feature Research

**Domain:** Pre-demo verification & hardening for a live academic thesis-defense demo of a local/offline LLM tool
**Researched:** 2026-07-02
**Confidence:** MEDIUM (synthesized from general live-demo/deployment best practices + direct inspection of this repo's actual CLI/server code; no single canonical "thesis demo checklist" source exists, so items are triangulated across multiple domains: conference-demo lore, air-gapped deployment QA, and local-LLM latency practice)

## Codebase Grounding

Before listing findings, the actual runtime was inspected directly (not assumed) so recommendations map to real code:

- `src/runtime/cli.py` — `vnphish analyze` (stdin/`--text`, prints to terminal, runs `run_runtime_doctor()` first and exits 2 if not ready) vs `vnphish demo` (`--host`, `--port 8765`, `--no-browser`, opens a browser tab). This confirms the PROJECT.md-reported "CLI entrypoint confusion" is real: two subcommands with silently different output surfaces (terminal text vs. browser UI) and no cross-referencing help text pointing a user from one to the other.
- `src/runtime/demo.py` — the demo server is a single-threaded `wsgiref.simple_server.make_server` WSGI app (stdlib, no gunicorn/uvicorn workers). It calls `app.service.backend.doctor()` once at startup ("Warming up local model...") before serving — this is an existing warm-up step, not a gap. But because `wsgiref.simple_server` handles one request at a time by default, **a slow in-flight `/api/analyze` call will block any concurrent request** (e.g., a double-click submit, or a second browser tab) — relevant to the reported latency issue and worth explicit verification.
- `src/runtime/doctor.py` — `vnphish doctor` already checks Python version, required imports, settings load, backend readiness (heuristic/gguf/accelerated), fail-closed default, and `runtime_store_raw_text=False`. This is a strong existing pre-flight tool — the verification checklist should **use it**, not duplicate it.
- No apparent request timeout, no explicit "already processing" UI guard was seen in the reviewed `demo.py` beyond the client-side `AbortController` mentioned in PROJECT.md (re-entrant fetch guard) — confirms the fetch-guard is a client-side mitigation for the single-threaded server characteristic above.

## Feature Landscape

### Table Stakes (Verification/Hardening Actions Every Defense-Ready Local-LLM Demo Needs)

These are non-negotiable pre-defense checks. Skipping any of them risks a visible on-stage failure in front of the committee.

| Feature/Action | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Run `vnphish doctor` on the **actual presentation laptop**, not the dev machine | Confirms model artifacts, backend, and fail-closed defaults are present on the exact hardware that will be used live — dev-machine-only testing is the single most common cause of "works on my machine" demo failure | LOW | Already built; just needs to be run and its output screenshotted/logged as verification evidence |
| End-to-end functional pass across all in-scope threat classes (bank impersonation, account-takeover/social-engineering, "light work high pay" scams) + at least one clearly benign message | Confirms risk tier + threat label + grounded cues + safe-steps render correctly for every class the thesis claims to cover — an untested class failing live undermines the exact claim being defended | LOW-MEDIUM | Use committed sample/eval texts where possible so outputs are reproducible and can be compared run-to-run |
| Network-isolation check: disconnect Wi-Fi/Ethernet on the presentation laptop and re-run the full flow | Directly validates the "offline/local-only, no cloud submission" claim that is central to the thesis's privacy argument — a live network call (even a benign favicon/telemetry request) visibly contradicts the pitch if a committee member notices browser dev tools or a delay tied to DNS timeout | LOW | Airplane mode or physically unplugging is sufficient; watch browser Network tab for any non-localhost request |
| Model loads from the **local artifact path actually present on the presentation laptop**, not a path that only exists on the dev machine | Cross-machine path/config drift (env vars, `.env`, absolute paths) is a top cause of "doctor passes on dev, fails on stage" | LOW-MEDIUM | Copy or sync the exact model directory used at development time; re-run doctor after transfer |
| Edge-case input pass: empty input, whitespace-only, very long text (paste a huge block), non-scam/off-topic text, mixed Vietnamese-English, malformed/garbled text | These are the inputs most likely to be tried by curious committee members deviating from the rehearsed script; a crash or unhandled exception here is far more damaging than a wrong classification | LOW-MEDIUM | `analyze_text` / `_handle_analyze` already validates `text` is a string and `channel` is in the allowed enum and returns 400 for bad requests — confirm the UI surfaces these gracefully rather than a raw stack trace or silent hang |
| Verify the **CLI vs demo UI distinction** is either fixed or scripted around | `vnphish analyze` prints text-only to a terminal; `vnphish demo` starts a browser UI on port 8765 — if the presenter types the wrong one live, or forgets `--no-browser` state, it costs visible fumbling time | LOW | Minimum viable fix: update `--help` strings to cross-reference each other, or just standardize the exact command the presenter will type and rehearse it verbatim (see Anti-Features — do not build a bigger CLI redesign) |
| Latency/timing measurement: time several representative analyze calls end-to-end (first call cold vs subsequent warm) | The known latency issue must be *quantified*, not just "fixed" — if it can't be eliminated, the presenter needs to know the real number to narrate through it confidently ("this typically takes N seconds because...") | LOW-MEDIUM | The server already warms the model once at startup (`doctor()` call in `run_demo_server`); confirm this warm-up actually keeps weights resident through the full 13-20 July window of no-network usage, and measure per-request latency after warm-up, not just startup time |
| Concurrency/re-entrancy check: submit two requests in quick succession (double-click, or open a second tab) while a first request is in flight | The demo server is single-threaded `wsgiref`; a nervous presenter double-clicking submit is a realistic live failure mode | LOW | Confirm the existing client-side `AbortController`/fetch-guard actually prevents this, and that the *second* legitimate use (opening the tool again after closing it) still works cleanly |
| Rehearsal with a timer, on the real laptop, in the room's actual conditions (screen resolution/projector, Wi-Fi off) if possible | Matches general live-demo best practice ("appease the demo gods": test on the exact hardware/software combination that will be used, not an approximation) | LOW | At least one full dry run on battery power (not just plugged in) since laptop throttling under battery can change CPU inference latency |
| Freeze code/config a few days before the defense window opens (13 July) | Last-minute changes are the single most cited cause of live-demo breakage in software-demo literature ("freeze code three to four days before the demo") | LOW (process, not code) | Aligns with the milestone already being scoped as verification-only, not new development — reinforce as a hard rule for this milestone |
| Prepared fallback: recorded screen capture (video) of a full successful run, plus static screenshots of key states (result cards for each threat class) | If live demo fails (laptop dies, model crashes, Wi-Fi captive portal steals focus, projector driver issue), presenter needs an immediate, rehearsed pivot rather than dead air | LOW-MEDIUM | Record on the *same* laptop/config being verified, so the recording matches what committee expects to see live; keep on a USB stick and locally on disk (not only cloud) in case laptop needs replacing |
| Battery/power check: laptop charger present, laptop tested on AC power at the venue if possible | Trivial but a real, common failure class ("bring two of everything") | LOW | Not a software task, but part of the "verification" checklist scope |

### Differentiators (What Separates a Genuinely Defense-Ready Demo from a "Technically Working" One)

Not required to avoid embarrassment, but they are what makes the demo feel controlled and convincing to a committee evaluating rigor.

| Feature/Action | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| A short, memorized "narration script" that explains the expected ~N-second latency *before* it happens | Turns a known weakness (latency) into a demonstrated understanding of the system's tradeoffs (CPU/iGPU inference cost vs. cloud) — committees react far better to "here's why, and here's the number" than silence while waiting | LOW | Pure presentation prep, zero code; directly reinforces the thesis's own "why local, not cloud" argument from Chapter 2 |
| A pre-selected, rehearsed set of 3-5 input messages (one per threat class + one benign) copied into a text file/clipboard manager ready to paste | Removes live-typing risk (typos, forgetting Vietnamese diacritics, freezing under pressure) and guarantees results match what was verified in advance | LOW | Should be the *same* messages used in the end-to-end verification pass above — one artifact serving both QA and live use |
| A visible, explicit "offline" cue during the demo (e.g., narrate turning off Wi-Fi on stage, or show a simple network-off indicator) | Makes the privacy/local-only claim *demonstrated* rather than merely *asserted* — for an academic committee, showing beats telling | MEDIUM | Physically toggling Wi-Fi live is higher-risk (OS reconnect delays, projector/display driver reliance on network in some setups) — validate this specific action during rehearsal, don't improvise it live for the first time |
| Doctor output shown once, upfront, as "system readiness proof" (e.g., running `vnphish doctor` on-screen before the live analyze demo) | Uses an artifact that already exists in the codebase to visibly establish credibility/rigor before the "trick" part of the demo runs | LOW | Zero new code — reuses `format_doctor_report()` output already built for this purpose |
| A one-page "if X fails, do Y" incident-response card kept next to the laptop (not shown to committee) | Reduces presenter panic and recovery time under live pressure — matches general demo-god wisdom that the presenter's calm handling of a hiccup often matters more than the hiccup itself | LOW | E.g., "if analyze hangs >15s → say the line about CPU latency and wait; if it errors → switch to backup video; if Wi-Fi popup steals focus → close and continue" |

### Anti-Features (Explicitly Avoid This Close to the Defense — 13-20 July 2026)

Things that look like reasonable "improvements" but introduce risk with no defense-relevant payoff, or are simply out of scope for a QA/hardening milestone.

| Feature/Action | Why Requested/Tempting | Why Problematic | Alternative |
|---------|---------------|------------------|-------------|
| Redesigning the UI (new layout, new visual style, new components) | "While I'm in there fixing bugs, I could also make it look nicer" | Every UI change is a new untested surface days before a live, unrepeatable event; directly contradicts the "code freeze before demo" principle that is the single most consistent piece of live-demo advice found across sources | Fix only the specific UI quirks already surfaced during verification; leave everything else untouched |
| Rebuilding/renaming the CLI (e.g., merging `analyze` and `demo` into a new unified command, restructuring argparse subcommands) | The entrypoint confusion feels like it "should" be solved architecturally | A CLI restructure risks breaking the `analyze`/`doctor`/`demo` contract relied on by existing tests (`tests/runtime/test_cli.py`) and by any rehearsed muscle-memory commands, for a problem that is really a presenter-facing communication issue, not a technical one | Fix `--help` text/README to disambiguate, and standardize + rehearse the exact one or two commands the presenter will actually type live |
| Adding new model capabilities, new threat classes, or new UI features not already shipped | Momentum from earlier milestones; "since I'm testing, why not add X" | This milestone is explicitly QA/hardening only per PROJECT.md ("Out of Scope" already excludes new domains); new capabilities are unverified by definition and reintroduce exactly the risk this milestone exists to remove | Log any such idea as a v6/future backlog item, do not implement before 20 July |
| Switching the demo server to a "production-grade" WSGI server (gunicorn/uvicorn) or adding multi-threading/concurrency support to fix the single-threaded blocking behavior | Feels like the "correct" fix for the concurrency limitation found in `demo.py` | Swapping the server stack this close to defense is an infrastructure change with new dependencies, new failure modes, and no time for equivalent-depth testing, for a problem that a client-side re-entrant-fetch guard (already implemented) plus presenter discipline (don't double-click) already mitigates adequately for a single-presenter live demo | Verify the existing `AbortController` guard behaves correctly under a double-click/second-tab test; do not touch the server threading model |
| Deep model-level latency optimization (re-quantizing, swapping GGUF backend, changing runtime profile) days before the defense | The latency issue is "known" so it feels urgent to root-cause and fix at the model layer | Requantizing or swapping runtime profiles this close to a fixed presentation date without a full evaluation re-run risks silently changing the model's classification behavior/accuracy that the thesis's own evaluation chapter already reports and locks — a regression here is worse than a slow-but-correct demo | Measure and narrate the existing latency (see Differentiators); if a *trivial*, well-understood latency fix exists (e.g., ensuring warm-up already keeps the model resident, confirming no redundant reloads), apply only that narrowly, then re-run the full evaluation-adjacent smoke tests before treating it as done |
| Adding telemetry, analytics, or "nice to have" logging/instrumentation for the demo itself | Feels useful for "knowing how the demo went" | New instrumentation is new code that could itself introduce a bug or an unexpected network call, directly undermining the offline/privacy claim being verified | Manual note-taking or the pre-planned recording/screenshots (already in scope) is sufficient evidence-gathering for a one-time defense event |
| Testing on/porting to a different OS or a "just in case" second machine with a different environment setup than what was actually developed on | Seems like it increases redundancy | Unless there is a truly identical, already-provisioned backup laptop, spending verification time provisioning a second environment from scratch this close to the deadline is higher-risk than hardening the one real presentation laptop thoroughly | If a backup laptop exists, it must already have the identical artifact root/model files staged well in advance — do not attempt first-time setup during the verification window |

## Feature Dependencies

```
[vnphish doctor passes on presentation laptop]
    └──requires──> [Model artifacts physically present/synced on that laptop]
                       └──requires──> [Correct artifact-root path/config on that laptop, not dev-machine-only]

[End-to-end functional verification across threat classes]
    └──requires──> [vnphish doctor passes] (fail-closed default means analyze exits 2 / demo won't serve meaningfully if not ready)

[Offline/network-isolation check]
    └──enhances──> [Privacy claim credibility in the live demo]

[Edge-case input pass] ──uses──> [Same sample messages prepared for "pre-selected rehearsed inputs" differentiator]

[Latency measurement] ──informs──> [Presenter narration script for latency]

[Recorded video/screenshot fallback]
    └──requires──> [End-to-end functional verification already passing] (record the verified-good run, not an ad hoc one)

[CLI help-text fix] ──conflicts──> [CLI restructure/redesign] (only one is in scope this milestone; see Anti-Features)

[Any UI quirk fix] ──conflicts──> [UI redesign] (fix only what verification surfaces; no aesthetic rework)
```

### Dependency Notes

- **Functional verification requires `doctor` passing:** both `handle_analyze` and `run_demo_server` are effectively gated by runtime readiness (`analyze` explicitly checks `run_runtime_doctor()` and exits 2 if not ready; `demo` calls `backend.doctor()` at startup as a warm-up). There is no point testing threat-class outputs before confirming the readiness check passes on the actual presentation hardware.
- **Network-isolation check enhances but does not block functional verification:** it should be run as an additional pass after normal functional verification succeeds online, to isolate whether anything unexpectedly depends on network access.
- **Edge-case testing and rehearsed-input prep share one artifact:** the same curated message set (bank impersonation, account-takeover, job-scam, benign) used to verify correctness should double as the presenter's live-demo script, so there is only one "known good" input set to maintain, not two diverging ones.
- **Latency measurement informs narration, not code changes:** per the anti-features above, the default assumption should be "measure and narrate" rather than "re-engineer," unless a trivially safe fix is found.
- **CLI and UI fixes conflict with their respective redesigns:** this is the central scope-creep guardrail for this milestone — every fix should be evaluated against "does this reduce or increase the amount of untested surface area before 13 July."

## MVP Definition

### Launch With (v5.1 Milestone — Due Before 13 July 2026)

Minimum viable verification pass — what's needed to be confident the live demo will not embarrass the presenter.

- [ ] `vnphish doctor` run and passing on the actual presentation laptop — non-negotiable baseline readiness proof
- [ ] Full functional pass: one message per in-scope threat class + one benign message, on the presentation laptop, confirming risk tier + threat label + cues + safe-steps render correctly
- [ ] Offline pass: same messages re-run with network disabled, confirming identical behavior and no network calls
- [ ] Edge-case pass: empty input, very long input, malformed/off-topic input handled without a raw crash or hang visible in the UI
- [ ] Latency measured and quantified (cold vs. warm), with a one-line presenter explanation ready
- [ ] CLI entrypoint disambiguation: at minimum, `--help` text or a README note clarifying `analyze` (terminal) vs `demo` (browser UI), and the presenter's exact command(s) rehearsed
- [ ] Concurrency/double-submit check: confirm the existing fetch-guard prevents a broken state on double-click or duplicate tab
- [ ] Recorded video (full successful run) + screenshots of each threat-class result, saved locally in at least two places (laptop + USB)
- [ ] Any UI quirk found during the above passes fixed narrowly (no redesign)

### Add After Validation (Only If Time Remains Before 13 July)

- [ ] Presenter incident-response card (if X fails, do Y) — pure documentation, near-zero risk to add
- [ ] A rehearsed live "toggle Wi-Fi off" moment in the presentation script — only if tested safely in advance and proven not to disrupt the projector/display setup

### Future Consideration (Explicitly Deferred Past the Defense — v6+)

- [ ] Any UI redesign or visual polish
- [ ] CLI subcommand restructuring or unification
- [ ] Swapping the WSGI dev server for a production-grade multi-threaded server
- [ ] Model-level latency optimization beyond confirming existing warm-up behavior
- [ ] New telemetry/logging instrumentation for the demo

## Feature Prioritization Matrix

| Feature/Action | User Value (Defense Success) | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| `doctor` pass on presentation laptop | HIGH | LOW | P1 |
| Functional pass across threat classes | HIGH | LOW-MEDIUM | P1 |
| Offline/network-isolation check | HIGH | LOW | P1 |
| Edge-case input pass | HIGH | LOW-MEDIUM | P1 |
| CLI entrypoint disambiguation (docs/help only) | MEDIUM-HIGH | LOW | P1 |
| Latency measurement + narration prep | MEDIUM-HIGH | LOW-MEDIUM | P1 |
| Concurrency/double-submit check | MEDIUM | LOW | P1 |
| Recorded video/screenshot fallback | HIGH | LOW-MEDIUM | P1 |
| Narrow UI quirk fixes (only what's surfaced) | MEDIUM | LOW | P1 |
| Rehearsed pre-selected input script | MEDIUM | LOW | P2 |
| Presenter incident-response card | MEDIUM | LOW | P2 |
| Live Wi-Fi-off toggle moment | LOW-MEDIUM | LOW (but risk if untested) | P3 |
| UI redesign | LOW (for this milestone) | HIGH | Out of scope |
| CLI restructure | LOW (for this milestone) | MEDIUM-HIGH | Out of scope |
| Production WSGI server swap | LOW (for this milestone) | MEDIUM | Out of scope |
| Model-level latency re-engineering | LOW (for this milestone), HIGH risk | HIGH | Out of scope |

**Priority key:**
- P1: Must have for the 13-20 July defense window
- P2: Should have if time remains
- P3: Nice to have, only if it can be validated safely without adding risk

## Competitor/Reference Analysis

Not a market-competitive product; "competitors" here are analogous demo/verification practices from other domains.

| Practice | Conference tech-talk demos | Enterprise sales-software demos | This project's approach |
|---------|--------------------|--------------------|--------------|
| Code freeze before the event | Freeze 3-4 days out; no last-minute changes | Dry run day-of, environment locked | Adopt: freeze this milestone's fixes days before 13 July, verification-only after |
| Backup for live failure | Pre-recorded backup video/screenshots | Pre-recorded fallback + sandbox environment | Adopt: recorded full run + screenshots per threat class |
| Environment parity | Test on the exact hardware/software used live | Reproduce a staging environment matching prod | Adopt: verify on the actual presentation laptop, not dev machine |
| Handling known slowness | Narrate through it, don't hide it | Pre-warm systems, skip slow steps in script | Adopt: measure latency, prepare a narration line, keep warm-up already in place |

## Sources

- [Essential Checklist for Your Next Software Demo Prep](https://www.sharefable.com/blog/ultimate-checklist-for-software-demo-presentation) — MEDIUM confidence, general SaaS demo checklist, cross-referenced against academic-specific advice
- [How to Appease the Demo Gods](http://www2.rdrop.com/~paulmck/DemoGods/) — MEDIUM confidence, widely cited engineering-conference demo-failure lore; principle of code-freeze days before demo and testing only what's rehearsed
- [Don't Tempt The Demo Gods (Hackaday)](https://hackaday.com/2016/04/30/dont-tempt-the-demo-gods/) — MEDIUM confidence, corroborates "bring two of everything," avoid last-minute changes
- [Ten tips for a great demo — Steve Clayton](https://www.stevecla.com/musings/ten-tips-for-a-great-demo/24/8/2014) — LOW-MEDIUM confidence, general practitioner advice
- [How to Be a Demo God — Guy Kawasaki](https://guykawasaki.com/how_to_be_a_dem/) — LOW-MEDIUM confidence, widely referenced but anecdotal
- [Virtual Thesis Defense — recording a stressful Zoom presentation](https://jaan.io/virtual-thesis-defense-recording-zoom-presentation/) — MEDIUM confidence, direct academic-defense context; corroborates pre-recorded backup video practice and redundant recording setups
- [Testing Your Application in Air-Gapped Environments with Compatibility Matrix (Replicated)](https://www.replicated.com/blog/testing-your-application-in-air-gapped-environments-with-compatibility-matrix) — MEDIUM confidence, corroborates "every item in an air-gapped checklist must be verified, missing one is a failure point," and reproducing the sealed/offline environment before relying on it
- [Air-Gapped REST API Deployment Best Practices (hoop.dev)](https://hoop.dev/blog/air-gapped-rest-api-deployment-best-practices-for-secure-offline-environments) — MEDIUM confidence, corroborates verifying no unintended network egress as an explicit, automatable check
- [Optimize LLM response costs and latency with effective caching (AWS)](https://aws.amazon.com/blogs/database/optimize-llm-response-costs-and-latency-with-effective-caching/) and general local-LLM guides (sitepoint.com, ikangai.com) — LOW-MEDIUM confidence, general local-inference latency/keep-resident practice, used only to frame the "measure and narrate, don't re-engineer" recommendation
- Direct repo inspection (HIGH confidence, primary source): `src/runtime/cli.py`, `src/runtime/demo.py`, `src/runtime/doctor.py` in this repository — used to ground every finding in the actual entrypoints, server threading model, and existing readiness tooling rather than assumptions
- `.planning/PROJECT.md` — HIGH confidence, primary source for milestone scope, known issues, and explicit out-of-scope boundaries

---
*Feature research for: pre-demo verification & presentation hardening (thesis defense, local offline LLM demo)*
*Researched: 2026-07-02*
