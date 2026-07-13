# Phase 33: Emergency 10-Minute Slide Compression - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-13
**Phase:** 33-emergency-10-minute-slide-compression
**Areas discussed:** Consolidation map, Backup vs delete, Demo-in-slot (raised via freeform)

---

## Gray Area Selection

| Option | Description | Selected |
|--------|-------------|----------|
| Consolidation map | Exactly which frames merge/cut to go 15→10 | ✓ |
| Backup vs delete | Trimmed content kept as hidden backup slides, or deleted | ✓ |
| Demo-in-slot rule | Trigger for cutting the demo, what the demo slide shows | (answered via freeform, not formally selected) |
| Timing budget | Seconds/slide assumption for the audit/rehearsal estimate | (not selected — left to Claude's discretion) |

**User's freeform note (first turn):** "for Demo silde, just keep it when i record i will place it with my pdf editor and rehearse to see whether i could reach 9 m, so dont touch demo and some ending slides" — prompted a plain-text follow-up to clarify which "ending slides."

---

## Ending Slides Clarification

| Option | Description | Selected |
|--------|-------------|----------|
| Contributions (11) | Leave standalone | (superseded — merge approved next turn) |
| Future Work (12) | Leave standalone | (superseded — merge approved next turn) |
| Thank You (15) | Leave standalone | ✓ |
| References (13) | Leave standalone | ✓ |

**User's response:** "Thank You (15), References (13), Contribution+future work see if you can consolidate to one slide keep also the Live Demo site, but after compiling pdf i would place the video on top of it to avoid losing structure"

**Notes:** Confirmed Contributions+Future CAN merge (contradicts the initial "leave ending slides untouched" framing — user refined it to mean "don't touch References/Thank You," not "don't touch Contributions/Future"). Confirmed demo slide layout must stay stable for later manual video overlay.

---

## Consolidation Map Confirmation

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, use this map | Title+Agenda merge, Problem+WhyLocal merge, Evaluation+Confusion merge, Contributions+Future merge — 11 total | Partially — see notes |
| Adjust | Change which slides merge | — |

**User's response:** "demo just x1 keep the demo As-is." — approved the Problem+WhyLocal, Evaluation+Confusion, and Contributions+Future merges, but added that Demo's 2 frames should also combine into 1 (content unchanged).

**Follow-up correction (final turn):** "Title, agenda keep normal, and go" — retracted the Title+Agenda merge; both stay separate, standalone frames.

**Final map:** Title (standalone), Agenda (standalone), Problem+WhyLocal (merged), Architecture (untouched), Data (untouched), Model (untouched), Evaluation+Confusion (merged), Contributions+Future (merged), Demo (2→1 frame, content unchanged), Thank You (untouched), References (untouched) = **11 frames**.

---

## Backup vs Delete

| Option | Description | Selected |
|--------|-------------|----------|
| Delete outright | Simpler, matches the emergency time budget | — |
| Keep as hidden backup slide(s) | Beamer appendix/backup section after Thank You, not counted in main total | ✓ |

**User's choice:** Keep as hidden backup slide(s).
**Notes:** Trimmed content from the three merges goes to a non-numbered backup section, available for Q&A but not part of the 10-11 slide rehearsal count.

---

## Claude's Discretion

- Exact titles/wording for the 4 merged frames.
- Exact backup-slide LaTeX mechanics (`\appendix`, frame-numbering suppression).
- Whether the Contributions+Future merged frame keeps the "Conclusion" section label.
- 2-column vs stacked layout for merged frames.
- Per-slide timing budget/assumption for TIME-01/TIME-05 (no fixed rate given by user).

## Deferred Ideas

- Literal LaTeX video embedding (`movie15`/`multimedia`) — rejected; user places video manually via PDF editor post-compile.
