# Phase 33: Presenter Run Plan — 10-Minute Defense Slot

**Defense date:** 15 July 2026
**Deck:** `documents/reports/latex/slides.tex` → `slides.pdf` (11 main frames + 4-frame hidden backup appendix)

**Post-ship refinement (2026-07-13, same day):** after reviewing the compiled PDF, the user asked for two more changes: (1) trim the Motivation & Why Local and Contributions & Future Work frames further — dense prose isn't needed since delivery will lean on a separate spoken script, slides should read as short anchor phrases only; (2) split the merged "Live Demo" frame back into two: a **Sample Output** frame (the static worked example — no longer called "live" since it isn't) and a separate, deliberately minimal **Demo** frame reserved for the pasted-in recorded video (also not called "live" — the actual demo is a video, not performed live). Frame count moved from 11 to 12.

**Second post-ship refinement (2026-07-14, day before defense):** after a rehearsal read-through, the user decided the Sample Output and Demo frames should be cut from the timed main flow entirely and moved to the backup appendix. Two other fixes landed in the same pass: the Training Pipeline slide's out-of-place "Data note" callout was removed (folded into the existing backup Evaluation/Confusion frame's Caution bullet instead), and the Contributions slide's "Future Direction" bullet was rewritten from the actual thesis Future Work chapter (§6) instead of a paraphrase.

**Third post-ship refinement (2026-07-14, same day):** the user asked for **Sample Output specifically** back in the timed main flow — it's a valuable concrete example of the grounded-cue output, not really a "demo." It's back, positioned at the end of the Evaluation Results section (no new ToC entry), right before Conclusion, so it reads as evidence supporting the evaluation claims before the deck wraps up. **Demo (the video placeholder) stays cut**, moved into the backup appendix alongside the other 3 backup frames — if a judge asks for a demo, it happens live during Q&A instead (untimed) using the GDEMO-01 golden prompts below. Main frame count: 10 → 11. Everything below reflects this current, final state.

## TIME-01 — Baseline (before compression)

Measured before any Phase 33 trims — 15 frames across 9 sections.

| # | File | Frame | Est. sec |
|---|------|-------|----------|
| 1 | 01_title.tex | Title | 20 |
| 2 | 02_agenda.tex | Table of Contents | 20 |
| 3 | 03_problem.tex | Problem: Vietnamese Phishing & the Privacy Gap | 60 |
| 4 | 04_architecture.tex | Training Pipeline Overview | 60 |
| 5 | 05_data.tex | Data Pipeline | 75 |
| 6 | 06_why_local.tex | Privacy Risk: Cloud API Data Leakage | 60 |
| 7 | 07_model.tex | Model Adaptation — QLoRA on Qwen3-4B | 60 |
| 8 | 08_evaluation.tex | Evaluation Results | 55 |
| 9 | 09_confusion.tex | Confusion Matrix & Error Analysis | 50 |
| 10a | 10_demo.tex (frame 1) | Sample Output | 35 |
| 10b | 10_demo.tex (frame 2) | Live Demo transition + actual live action | 90 |
| 11 | 11_contributions.tex | Contributions | 45 |
| 12 | 12_future.tex | Limitations & Future Work | 45 |
| 13 | 13_references.tex | References | 15 |
| 15 | 15_thankyou.tex | Thank You | 10 |
| | **TOTAL** | | **700s ≈ 11:40** |

~1:40 over the 10:00 target — this is why Phase 33 exists.

## TIME-05 — Final estimate (SUPERSEDED by TIME-06 below — kept for history)

Computed from the actual final 12-frame content (word-count / 130wpm + table overhead, ×1.15 delivery buffer). Architecture/Data/Model are unchanged from baseline.

| # | Frame | Est. sec | Notes |
|---|-------|----------|-------|
| 1 | Title | 20 | unchanged |
| 2 | Table of Contents | 20 | unchanged |
| 3 | Motivation & Why Local (merged, trimmed to short phrases) | 35 | full detail preserved in backup appendix |
| 4 | Training Pipeline Overview | 60 | **unchanged, untouched (TIME-03)** |
| 5 | Data Pipeline | 75 | **unchanged, untouched (TIME-03)** |
| 6 | Model Adaptation | 60 | **unchanged, untouched (TIME-03)** |
| 7 | Evaluation Results (merged) | 60 | metrics table + confusion matrix, both intact |
| 8 | Contributions & Future Work (merged, trimmed to short phrases) | 30 | full detail preserved in backup appendix |
| 9 | Sample Output | 35 | static worked example (unchanged content, renamed from "Live Demo") |
| 10 | Demo | 65 | new dedicated frame — ~1 min reserved for the pasted-in video (GDEMO-02) |
| 11 | Thank You | 10 | unchanged |
| 12 | References | 15 | unchanged |
| | **TOTAL** | **485s ≈ 8:05** | **115s (almost 2 min) under the 10:00 target** |

## TIME-06 — Superseded intermediate estimate (both Demo frames in backup — kept for history)

| # | Frame | Est. sec | Notes |
|---|-------|----------|-------|
| 1 | Title | 20 | unchanged |
| 2 | Table of Contents | 20 | unchanged, now lists 6 sections |
| 3 | Motivation & Why Local | 35 | full detail preserved in backup appendix |
| 4 | Training Pipeline Overview | 60 | unchanged content; stray "Data note" callout removed (moved to backup) |
| 5 | Data Pipeline | 75 | unchanged |
| 6 | Model Adaptation | 60 | unchanged |
| 7 | Evaluation Results (merged) | 60 | metrics table + confusion matrix, both intact |
| 8 | Contributions & Future Work | 30 | Limitations now boxed to match Contributions; Future Direction re-sourced from thesis §6 |
| 9 | Thank You | 10 | unchanged |
| 10 | References | 15 | unchanged |
| | **TOTAL** | **385s ≈ 6:25** | **215s (3:35) under the 10:00 target** |

## TIME-07 — Current estimate (Sample Output back in main flow, 2026-07-14)

Same as TIME-06, with Sample Output reinserted at the end of the Evaluation Results section (no new ToC entry), right before Conclusion. Demo (the video placeholder) stays in the backup appendix.

| # | Frame | Est. sec | Notes |
|---|-------|----------|-------|
| 1 | Title | 20 | unchanged |
| 2 | Table of Contents | 20 | unchanged, lists 6 sections |
| 3 | Motivation & Why Local | 35 | full detail preserved in backup appendix |
| 4 | Training Pipeline Overview | 60 | unchanged content; stray "Data note" callout removed (moved to backup) |
| 5 | Data Pipeline | 75 | unchanged |
| 6 | Model Adaptation | 60 | unchanged |
| 7 | Evaluation Results (merged) | 60 | metrics table + confusion matrix, both intact |
| 8 | Sample Output | 35 | back in the main flow — static worked example, no live action |
| 9 | Contributions & Future Work | 30 | Limitations boxed to match Contributions; Future Direction re-sourced from thesis §6 |
| 10 | Thank You | 10 | unchanged |
| 11 | References | 15 | unchanged |
| | **TOTAL** | **420s ≈ 7:00** | **180s (3:00) under the 10:00 target** |

This is a rehearsal estimate, not a guarantee — **rehearse the real compiled deck with a stopwatch** before the defense. Still a comfortable 3-minute margin even with Sample Output back in.

## GDEMO-02 — Demo-in-slot decision (SUPERSEDED by GDEMO-04 below — kept for history)

- There are now two separate frames for this: **Sample Output** (the static worked example) and **Demo** (a deliberately minimal frame reserved for your pasted-in video). Both **stay in the main deck**. ~65s of the 8:05 estimate above is reserved for the Demo frame.
- **This is not a hard commitment to show the demo no matter what.** If your full rehearsal of the compiled deck shows the talk doesn't fit in 10 minutes, **cutting the Demo frame during rehearsal is your own call to make** — it was deliberately left as your decision, not pre-decided by this phase (D-09).
- The Demo frame's layout is deliberately minimal/mostly blank so that, after compiling, you can place your recorded video on top of it with a PDF editor without needing to touch the LaTeX again (D-10). Neither frame is called "Live" anymore, since the shown demo is a recorded video, not something performed live.

## GDEMO-03 — Demo-in-slot decision (SUPERSEDED by GDEMO-04 below — kept for history)

- **Sample Output and Demo are both cut from the timed main flow** and moved to the backup appendix. The "Demo" section and its Table of Contents entry are gone — the deck is now 10 main frames across 6 sections.
- Reasoning: with the harsh over-time penalty (going over the slot costs a point), the ~100s these two frames cost wasn't worth it for content that isn't strictly needed to make the case. If a judge asks to see the tool run, do it live during Q&A instead — Q&A time isn't part of the scored slot, so it can't hurt the timing grade. Use the two locked golden prompts below (GDEMO-01) if that happens.
- Both frames are unchanged in content — only their position moved. They're still fully built and ready to present from if you decide differently on the day; just Ctrl+click through the PDF outline/thumbnails to reach them during Q&A.

## GDEMO-04 — Demo-in-slot decision (current, locked 2026-07-14)

- **Sample Output is back in the timed main flow** — it's a concrete worked example of the grounded-cue output supporting the evaluation claims, not really a "demo," and worth the ~35s. It sits at the end of the Evaluation Results section, right before Conclusion, for narrative flow: results → concrete example → wrap-up.
- **Demo (the video placeholder) stays cut** — moved into the backup appendix (Backup 4, inside `14_backup.tex`). If a judge asks to see the tool run, do it live during Q&A instead — untimed, using the golden prompts below (GDEMO-01).
- Deck is now 11 main frames across 6 sections, 4-frame backup appendix. ~7:00 total, ~3:00 margin (TIME-07).

## GDEMO-01 — Live-demo / recording checklist

**Important: the text printed on the Sample Output slide is illustrative only.** It is the original example wording and was deliberately left untouched (per your instruction not to edit that slide's static text — see D-07). **Do not assume that printed text is what you should actually type or paste when recording your demo video.**

When you actually run or record the live demo, use these two locked prompts verbatim (from `scripts/verify_golden_prompts.py`):

**Scam prompt** (`DEFAULT_SCAM_TEXT`, channel `sms`) — expect **high-risk / bank_impersonation**:
> 【VIETCOMBANK】 Tai khoan cua ban vua bi truy cap tu thiet bi la luc 03:47 SA. Neu ko phai ban, bam vao link de khoa ngay: http://vcb-secure-alert.net/lock?id=9182736 hoac goi 1800.9999 (mien phi).

Cross-referenced against Phase 28's `golden_scam` result: 5/5 stable, correct verdict every run.

**Benign prompt** (`DEFAULT_BENIGN_TEXT`, channel `sms`) — expect **benign / benign**:
> VPBank Smart OTP: Mã xác thực của bạn là 847291. Mã này có hiệu lực trong 90 giây để xác nhận đăng nhập Internet Banking. Tuyệt đối KHÔNG chia sẻ mã này với bất kỳ ai, kể cả nhân viên ngân hàng.

Cross-referenced against Phase 28's `golden_benign` result: 5/5 stable, correct verdict every run.

Demo (the video placeholder) is backup-only (GDEMO-04), so this is also your primary Q&A answer, not just a recording script: if asked to demo, open the Demo backup frame (or just run `vnphish analyze` directly) and use the scam prompt above, with the benign prompt ready as a follow-up if asked "what about a legitimate message?"

## Closing notes

- **D-12 date fix:** the title slide now correctly reads `15 July 2026` (was `14 July 2026`).
- **Sample Output vs. Demo split:** what was one merged "Live Demo" frame is two — **Sample Output** (the worked text example, static, not live) and **Demo** (a near-blank frame for your video, also not called live). This reads more honestly: nothing in the deck itself is actually performed live. As of GDEMO-04, **Sample Output is back in the main flow** (end of Evaluation Results, before Conclusion); **Demo stays in the backup appendix**.
- **Backup appendix:** `slides/sections/14_backup.tex` now holds all 4 backup frames (the original 3, plus Demo, appended 2026-07-14) — reached only past the main 11-slide sequence (Beamer `\appendix`, footline denominator auto-frozen via Beamer's own built-in `\insertmainframenumber`, no manual counter to maintain). These are Q&A-only — not part of the timed walkthrough — and preserve the fuller detail trimmed out of the Motivation & Why Local, Evaluation Results, and Contributions & Future Work frames, plus the Data note originally (and awkwardly) placed on the Training Pipeline Overview slide, now folded into the Evaluation/Confusion backup frame's Caution bullet instead.
- **Future Direction re-sourced:** the Contributions slide's "Future Direction" bullet previously read as an invented paraphrase; it's now the top two priorities lifted directly from the thesis's own §6 Future Work section (seed-disjoint held-out evaluation; independent human review of grounding/recommendation quality). The third, lowest-priority item from that section (optional OCR preprocessing) was left off the slide for space — it's explicitly called "optional" in the thesis text itself, so cutting it from the slide doesn't misrepresent the priority ordering.
