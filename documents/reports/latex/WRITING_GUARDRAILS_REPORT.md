# Writing Guardrails — derived from a real passed report

**Source:** `docs/2026-07-02_09-20-59_nghiemxuanson_23bi14388_bachelor_thesis_.1.35m.pdf`
(Nghiêm Xuân Sơn, 23BI14388, USTH ICT — "Development of an Automated Device Posture
Assessment and Remediation Tool for Appgate SDP ZTNA"). Same department, same jury pool,
same internship-report format. He passed. This file records what his report actually does,
and what that means for ours.

Different topic (Zero Trust endpoint agent vs. our phishing detection), so do not copy his
content. Copy his **shape, evidence habits, and restraint**.

---

## 1. The headline numbers

| | His report | Ours (current) |
|---|---|---|
| Total pages | **40** (38 body + refs + 1 appendix page) | ~similar, but denser/heavier |
| Chapters | **5** (I–V, Roman numerals) | 6 + appendices |
| Figures | **11** | needs counting — but almost none are evidence screenshots |
| Tables | **2** | more, and more elaborate |
| Code snippets | **9**, each 5–10 lines | fewer, longer |
| References | **12** | more |
| Cryptographic hashes / manifests | **zero** | currently a whole theme |

The lesson is not "write less." It is **every single figure, table and snippet in his report
earns its place, and nothing is there to look rigorous.**

---

## 2. His chapter structure (copy this)

```
ACKNOWLEDGEMENTS
LIST OF ABBREVIATIONS        <- one page, alphabetical, plain
LIST OF TABLES
LIST OF FIGURES              <- full caption text repeated here
ABSTRACT                     <- ONE paragraph + "Key words:" line
I/   INTRODUCTION            <- Context, Motivation, Literature Review (3 short subsections)
II/  OBJECTIVES              <- Primary Objectives (4 bullets), Secondary Objectives (4 bullets)
III/ MATERIALS AND METHODS   <- the biggest chapter (~20 pages): what he used, what he built
IV/  RESULTS AND DISCUSSION  <- Evaluation Scenarios, System Performance, Challenges & Limitations
V/   CONCLUSION & PERSPECTIVE<- Conclusion, Perspectives for Future Development
REFERENCES
APPENDICES                   <- deployment screenshots that didn't fit the body
```

Notice what is **absent**: no "methodology philosophy" chapter, no separate "related work"
chapter, no long theory. Literature review is ~2 pages *inside* the Introduction.

---

## 3. The thing we were actually missing: he proves he did the work

This is the whole ballgame. Our previous report had no operational evidence, so the jury
concluded we didn't build or train anything. His report is full of unglamorous proof:

- **Figure 4 / 5** — CLI screenshots of the appliance consoles showing assigned static IPs.
  Just a terminal, showing a real machine he configured.
- **Figure 9** — a screenshot of the client UI showing **"Blocked — Access Denied: Your
  Windows Firewall is currently disabled."** He broke his own system on purpose and
  photographed it reacting.
- **Figure 10** — the admin console showing a live session: entitlements, four conditions all
  showing "Met", tunnel IPv4/IPv6, bandwidth counters, timestamps.
- **Figure 11** — **Windows Task Manager** showing `agent.exe` at 0.1% CPU / 2.7 MB RAM.
- **Appendix Figure A** — the VirtualBox VM console mid-setup ("This appliance has not yet
  been seeded"), showing the raw provisioning menu.

None of it is polished. That is exactly why it reads as real.

**Our equivalent evidence to capture (screenshot shopping list — do this first, before
writing prose):**

1. **Training actually running** — terminal mid-training: loss values ticking, step counter,
   timestamps visible. Both models (Qwen QLoRA, PhoBERT).
2. **GPU/VRAM monitor during training** — Task Manager Performance tab or `nvidia-smi`,
   showing the RTX 5050 actually loaded. This single screenshot kills "you didn't train."
3. **The loss curves we already generated** in Phase 40 — as plain figures.
4. **Model files on disk** — file explorer or `ls -la` showing the adapter/checkpoint files
   with real sizes and timestamps.
5. **`vnphish doctor`** output in a terminal — the environment check passing.
6. **`vnphish analyze` on a real Vietnamese scam message** — terminal showing the label, risk
   tier, and the highlighted suspicious span.
7. **The local demo UI in a browser** — paste a message, show the verdict.
8. **The evaluation run's terminal output** — the one-shot test-set run finishing, printing
   the accuracy/macro-F1.
9. **A data sample** — a few real corpus rows on screen (JSONL in an editor), so the jury sees
   the actual data shape.
10. **Optional but strong:** wall-clock training duration visible somewhere (start/end
    timestamps in the log).

Every one of these is a screenshot you can take from work already done. This is the single
highest-value thing to spend the next few days on.

---

## 4. How he reports performance (steal this exactly)

No statistics. No confidence intervals. No significance tests. He writes:

> **CPU Usage:** During the idle sleep phase, CPU consumption drops to 0%. During the active
> 1-second scanning burst … CPU usage momentarily peaks at approximately 1% on a standard
> modern CPU (e.g., Intel Core i5).
> **RAM Consumption:** … roughly 1MB to 5MB …

and then breaks latency into three named components (Detection 10s, Telemetry <1s,
Enforcement sub-second), sums them, and states the honest total:

> the maximum theoretical latency … is approximately **10 to 12 seconds**.

That's it. Measured, decomposed, stated, judged acceptable. **This is the register our
evaluation chapter should be in.** We have far stronger numbers than he does — we just have
to present them this plainly and stop hedging them into invisibility.

---

## 5. How he shows contribution without overclaiming

**Table 2** is one small table with four columns: *Evaluation Criteria | Traditional VPN |
NAC | Proposed System (Appgate SDP + Custom Agent)*, across five rows (Trust Model, Network
Visibility, Posture Assessment, Auto-Remediation, Lateral Movement).

His work is a column. Instantly legible. A jury member can see the contribution in five
seconds without reading a word of prose.

**Our version should be a table where our system is a column** — e.g. rows for
*handles Vietnamese*, *runs locally / offline*, *explains its decision (spans)*, *four-class
labelling*, *no data leaves the machine* — compared against generic cloud spam filters or a
keyword/rules baseline. One table. Five or six rows.

---

## 6. He documents his own limits — deliberately

Section **5.3 "Limitations of Hardware-Level Remediation"** exists purely to say: my agent
*could* try to auto-fix Secure Boot and BitLocker, and I decided it must not, because
modifying UEFI from a background script is restricted for good reason and dynamic BitLocker
provisioning risks data loss. So it denies access and logs instead.

He gets credit for the boundary he *didn't* cross. Same with **"Challenges and Limitations"**
in Chapter IV, where he tells the real story of fighting Cloudflare 522 errors until he
worked out the SNI/Host-header issue.

**Our equivalents, stated the same way, plainly:**
- one seed, one run — so no claim of stable superiority between the two models;
- the corpus is model-assisted (synthetic), reviewed by an independent judge and by hand —
  say it directly, in our own words, in the methodology chapter, not buried;
- one held-out evaluation pass, run once, no retries or tuning afterwards;
- the local runtime is a prototype, not a deployed product.

Stating these *first*, in our own voice, is what removes their power as jury ambushes.

---

## 7. Register and tone

- Plain declarative sentences. "The system detects…", "The agent verifies…", "Experimental
  results demonstrate…".
- No promotional adjectives. He never writes "state-of-the-art", "cutting-edge",
  "revolutionary".
- Figures get a caption **and**, for the important ones, a short italic *Description:*
  paragraph saying what the reader should notice and why it matters.
- Code snippets get one sentence of setup before and one sentence of interpretation after.
  Never a snippet dropped in silently.
- He names files by **function** — `scanner.py`, `agent.py`, `audit_firewall.ps1`,
  `fix_defender.ps1` — never by project chronology.

---

## 8. Direct consequences for our report

**Kill entirely:**
- **SHA-256 / manifest / hash-integrity discussion.** His report contains zero of it. It reads
  as defensive over-engineering and it already burned us once in the live defense. Keep the
  integrity machinery in the code; keep it out of the report prose.
- **"Phase 40 / Phase 41" language.** Internal chronology means nothing to a jury and makes
  the work look like a process log. Refer to things by what they are: "the training pipeline",
  "the held-out evaluation", "the corpus repair step". (The *code* keeps its names — that's a
  separate, deliberate compatibility decision. Only the report changes.)
- Any sentence that exists to sound rigorous rather than to say something.

**Add:**
- The screenshot evidence set in §3. This is the fix for the actual F-grade cause.
- A one-table contribution comparison (§5).
- A short, honest "Challenges and Limitations" section with the real debugging stories —
  the corpus quality problem we found and fixed is a *good* story, not a shameful one.

**Restructure:**
- Consider collapsing toward his 5-chapter shape. Our current 6-chapter + appendices layout is
  close; the gain is mostly in trimming, not renaming.

---

## 9. What this means for how we work now

Prose is drafted by hand, by the student, chapter by chapter — Claude only tightens grammar
and tone and checks numbers against `EVIDENCE_MAP.md`. That constraint is unchanged and is
the point: the jury's real objection was credibility, and credibility comes from being able
to defend every sentence live.

Suggested order of work given the remaining time:

1. **Capture the screenshots** (§3) — highest value, mostly mechanical, unblocks everything.
2. Draft **Chapter IV (Results)** first, in your own words, around those screenshots.
3. Then **Chapter III (Methods)** — what you built, in function-named terms.
4. Then Introduction / Objectives / Conclusion, which are the easiest to write once the middle
   is solid.
5. Strip SHA-256 and phase-number language throughout as a final pass.
