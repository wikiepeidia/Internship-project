# Phase 33: Emergency 10-Minute Slide Compression - Context

**Gathered:** 2026-07-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Compress the defense Beamer deck (`documents/reports/latex/slides.tex` + `documents/reports/latex/slides/sections/*.tex`) from its current 15 frames down to ~10-11 frames so it reliably fits a 10-minute presentation slot. Architecture (04), Data (05), and Model (07) sections must keep their full existing depth — no content cuts there. The demo slide's stale sample-output text must be synced to the actual locked scam golden prompt. No backend/model/prompt changes — this is a slides-only phase. The title slide's printed defense date is **14 July 2026 — tomorrow** relative to today (2026-07-13), so this is genuinely a same-day-or-next-day emergency, not a loose "sometime in the 13-20 July window" task.

</domain>

<decisions>
## Implementation Decisions

### Slide Consolidation Map (target: 11 frames, from current 15)

- **D-01:** Keep Title (`01_title.tex`) and Agenda (`02_agenda.tex`) as separate, untouched standalone frames — do NOT merge them.
- **D-02:** Merge Problem (`03_problem.tex`) + Why-Local (`06_why_local.tex`) into one combined "Motivation & Why Local" frame.
- **D-03:** Merge Evaluation (`08_evaluation.tex`) + Confusion (`09_confusion.tex`) into one combined "Evaluation Results" frame (metrics table + confusion matrix, e.g. two-column layout).
- **D-04:** Merge Contributions (`11_contributions.tex`) + Future/Limitations (`12_future.tex`) into one combined "Contributions & Future Work" frame. **Repositioning required:** in `slides.tex`, `12_future.tex` currently sits under `\section{6. Limitations}` (before Evaluation), while `11_contributions.tex` sits under `\section{8. Conclusion}` (after Evaluation). The merged frame must be moved to one place in the `\input` sequence — put it in the Conclusion position (after the merged Evaluation frame, before Demo).
- **D-05:** Combine Demo's 2 existing frames (`10_demo.tex` has a "Sample Output" frame and a separate "Live Demo" transition frame) into a **single** frame. Keep the layout SIMPLE and STABLE — the user will manually overlay a screen-recorded video on top of this slide using a PDF editor after compiling, so avoid busy multi-column redesigns or backgrounds that would make later video placement awkward.
- **D-06:** Architecture (`04_architecture.tex`), Data (`05_data.tex`), Model (`07_model.tex`), References (`13_references.tex`), and Thank You (`15_thankyou.tex`) remain **completely untouched** — no content cuts, no merges, no reordering.
- **Result:** 15 → 11 frames: Title, Agenda, Motivation+WhyLocal, Architecture, Data, Model, Evaluation+Confusion, Contributions+Future, Demo (combined), Thank You, References.

### Demo Content Sync (GDEMO-01) — REVISED

- **D-07 (superseded — see correction below):** ~~Replace the static "Sample Output" text in `10_demo.tex` with the real locked scam text.~~ **User correction:** Do NOT edit the static "Sample Output" text in `10_demo.tex` — leave it exactly as it is. The recorded video (D-10) will visually cover this slide once placed via the PDF editor, so editing LaTeX text that won't be seen is wasted effort and adds unnecessary compile risk this close to the defense.
- **D-08 (revised):** GDEMO-01 ("demo references the locked golden prompts, not stale wording") is satisfied through the **recording itself**, not the LaTeX. When the user records the live demo, they must actually type/paste the real locked `DEFAULT_SCAM_TEXT` from `scripts/verify_golden_prompts.py`:
  > "【VIETCOMBANK】 Tai khoan cua ban vua bi truy cap tu thiet bi la luc 03:47 SA. Neu ko phai ban, bam vao link de khoa ngay: http://vcb-secure-alert.net/lock?id=9182736 hoac goi 1800.9999 (mien phi)."

  This is a **recording-content rule for the user to follow**, not a task this phase's LaTeX edits perform. The plan should surface this as a clear reminder/checklist item rather than a code change.
- **D-08b:** Do not add the benign golden prompt to the slide — not applicable now that the static slide text isn't being touched at all.

### Title Slide Date Fix (new — found during planning, not in original REQUIREMENTS.md scope, but user-approved)

- **D-12:** `slides.tex` line 69 currently prints `\date{14 July 2026}`. The actual confirmed defense date is **15 July 2026**. Fix this one-line date string. This is a factual-correctness fix the user explicitly approved when it was surfaced — small, isolated, zero risk to the consolidation work.

### Demo-in-Slot Decision (GDEMO-02)

- **D-09:** Keep the demo frame in the main deck (do not cut it structurally). The user will personally rehearse the full compiled deck to confirm it fits ~9 minutes (with ~1 minute reserved for the recorded video). If rehearsal shows it doesn't fit, cutting the demo is the **user's own call during rehearsal** — not this phase's decision, and not the agent's job to pre-emptively remove.
- **D-10:** After the PDF compiles, the user will manually place a screen-recorded video on top of the demo slide using a PDF editor. The agent's only responsibility toward this is D-05 (keep the demo frame's LaTeX layout simple/stable so the later manual overlay doesn't require restructuring).

### Cut Content Handling

- **D-11:** Content trimmed while merging (Problem+WhyLocal, Evaluation+Confusion, Contributions+Future) is **not deleted** — move it into a hidden Beamer backup/appendix section placed after Thank You and References (standard `\appendix` + non-numbered frames), so it doesn't count toward the main ~10-11 slide total or `\inserttotalframenumber`, but stays available if judges ask follow-up questions.

### Timing Audit & Budget (TIME-01, TIME-05)

- No fixed seconds-per-slide assumption was given by the user. Claude's discretion: produce the baseline audit and the final per-slide timing estimate from the actual planned spoken content once the merged frames are drafted, not from a flat guessed rate — this gives the user something real to rehearse against.

### Claude's Discretion

- Exact titles/wording for the 4 merged frames — keep concise, one idea per bullet, consistent with the Phase 12 tiered text-overflow policy (cut content first, split frame second, shrink font last — see canonical refs).
- Exact backup-slide LaTeX mechanics (`\appendix`, frame-numbering suppression) for D-11.
- Whether the Contributions+Future merged frame keeps the existing "Conclusion" section label or gets a new section name.
- Exact 2-column vs stacked layout choice for the merged Evaluation+Confusion and Motivation+WhyLocal frames.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Slide Source (edit targets)
- `documents/reports/latex/slides.tex` — main entry point; controls both `\section{}` grouping and the final `\input` slide sequence. Must be edited for the Contributions+Future reposition (D-04) and to reflect the merged/reduced frame set. Title slide prints `\date{14 July 2026}` — the real deadline.
- `documents/reports/latex/slides/sections/01_title.tex`, `02_agenda.tex`, `03_problem.tex`, `04_architecture.tex`, `05_data.tex`, `06_why_local.tex`, `07_model.tex`, `08_evaluation.tex`, `09_confusion.tex`, `10_demo.tex`, `11_contributions.tex`, `12_future.tex`, `13_references.tex`, `15_thankyou.tex` — all individual slide content files (current frame count verified via grep: 15 total, `10_demo.tex` alone has 2).

### Golden Prompt Source of Truth
- `scripts/verify_golden_prompts.py` — `DEFAULT_SCAM_TEXT` / `DEFAULT_BENIGN_TEXT` constants; source of truth for GDEMO-01 sync (D-07).
- `.planning/phases/28-baseline-readiness-zero-code-diagnostics/artifacts/28-golden-prompt-results.json` — locked golden-prompt run evidence (verdicts, labels) to cross-check the sample output shown on the demo slide.

### Prior Slide-Editing Decisions (still binding)
- `.planning/phases/12-cambridgeus-presentation-revamp/12-CONTEXT.md` — CambridgeUS/beaver theme, CVBLUE color usage, and the tiered text-overflow policy (D-15/D-16/D-17: cut content first, split frame second, shrink font as last resort). Also documents the `reference_themes.tex` design-spec file and `\scalebox` figure-sizing convention.
- `.planning/phases/19-slide-content-fixes/19-CONTEXT.md` — established slide editing conventions (block environments, `\framesubtitle`, footnote sizing, columns layout) used when previous supervisor-driven slide fixes were made.

### Requirements & Roadmap
- `.planning/REQUIREMENTS.md` §"v5.2 Requirements — Emergency Slide Fix (10-Minute Presentation)" — TIME-01 through TIME-05, GDEMO-01, GDEMO-02.
- `.planning/ROADMAP.md` — Phase 33 detail section (goal, success criteria).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `\begin{columns}[T]...\end{columns}` two-column pattern (already used in `06_why_local.tex` and `10_demo.tex`) — natural fit for the merged Motivation+WhyLocal and Evaluation+Confusion frames.
- `\begin{block}{...}` call-out environment — already the deck's standard way to headline a key statement/number (used in `03_problem.tex`, `06_why_local.tex`, `11_contributions.tex`, `12_future.tex`).
- `[t,shrink=N]` frame option — already used in `06_why_local.tex` when content is tight; available for merged frames that get dense.

### Established Patterns
- XeLaTeX compiler via `slides.tex` `fontspec`/`\setsansfont`/`\setmonofont` setup — every edit must keep a zero-error compile.
- `\footnotesize` / `\scriptsize` for dense bullets — already the deck's convention, not a new pattern to introduce.
- No `\begin{figure}`/`\begin{table}` float wrappers inside frames (established Phase 11 bug fix) — bare TikZ `\input` or inline tabulars only.

### Integration Points
- `slides.tex`'s `\section{}` labels drive the CambridgeUS navigation mini-header — merging/repositioning sections (D-04) changes what appears there. Currently 9 named sections; expect a small reduction as frames merge.
- `10_demo.tex`'s current 2-frame structure and its `[fragile]` lstlisting option must be preserved when combined into 1 frame (the lstlisting/code-output block is why `[fragile]` is needed).

</code_context>

<specifics>
## Specific Ideas

- Teacher-reported guidance the user cited: ~10 slides is the typical average for a talk this length — this set the TIME-04 target, not a hard department rule.
- The user will rehearse the compiled deck personally to confirm the ~9-minute talk + ~1-minute demo split works; if it doesn't, cutting the demo is their call to make live during rehearsal, not something to pre-decide in this phase.
- The user will manually place their recorded demo video on top of the (unmerged-in-layout-terms) demo slide via a PDF editor after compiling — this is why the demo frame's visual simplicity/stability (D-05) matters more than its content polish.

</specifics>

<deferred>
## Deferred Ideas

- Literal LaTeX video embedding (e.g. `movie15`/`multimedia` package) — considered and explicitly rejected; the user handles video placement manually post-compile via a PDF editor instead.
- Any backend/model/prompt/UI changes — out of scope, frozen since v5.1.

None beyond the above — discussion stayed within phase scope.

</deferred>

---

*Phase: 33-emergency-10-minute-slide-compression*
*Context gathered: 2026-07-13*
