# Phase 33: Presenter Run Plan — 10-Minute Defense Slot

**Defense date:** 15 July 2026
**Deck:** `documents/reports/latex/slides.tex` → `slides.pdf` (12 main frames + 3-frame hidden backup appendix)

**Post-ship refinement (2026-07-13, same day):** after reviewing the compiled PDF, the user asked for two more changes: (1) trim the Motivation & Why Local and Contributions & Future Work frames further — dense prose isn't needed since delivery will lean on a separate spoken script, slides should read as short anchor phrases only; (2) split the merged "Live Demo" frame back into two: a **Sample Output** frame (the static worked example — no longer called "live" since it isn't) and a separate, deliberately minimal **Demo** frame reserved for the pasted-in recorded video (also not called "live" — the actual demo is a video, not performed live). Frame count moved from 11 to 12; everything below reflects the current, final state.

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

## TIME-05 — Final estimate (after compression + trim/split refinement, real content)

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

This is a rehearsal estimate, not a guarantee — **rehearse the real compiled deck with a stopwatch** before the defense. You now have a comfortable margin (~2 min), which gives you room to actually talk through the content from your own script rather than reading the slide text verbatim — that was the point of trimming.

## GDEMO-02 — Demo-in-slot decision (locked)

- There are now two separate frames for this: **Sample Output** (the static worked example) and **Demo** (a deliberately minimal frame reserved for your pasted-in video). Both **stay in the main deck**. ~65s of the 8:05 estimate above is reserved for the Demo frame.
- **This is not a hard commitment to show the demo no matter what.** If your full rehearsal of the compiled deck shows the talk doesn't fit in 10 minutes, **cutting the Demo frame during rehearsal is your own call to make** — it was deliberately left as your decision, not pre-decided by this phase (D-09).
- The Demo frame's layout is deliberately minimal/mostly blank so that, after compiling, you can place your recorded video on top of it with a PDF editor without needing to touch the LaTeX again (D-10). Neither frame is called "Live" anymore, since the shown demo is a recorded video, not something performed live.

## GDEMO-01 — Live-demo / recording checklist

**Important: the text printed on the Sample Output slide is illustrative only.** It is the original example wording and was deliberately left untouched (per your instruction not to edit that slide's static text — see D-07). **Do not assume that printed text is what you should actually type or paste when recording your demo video.**

When you actually run or record the live demo, use these two locked prompts verbatim (from `scripts/verify_golden_prompts.py`):

**Scam prompt** (`DEFAULT_SCAM_TEXT`, channel `sms`) — expect **high-risk / bank_impersonation**:
> 【VIETCOMBANK】 Tai khoan cua ban vua bi truy cap tu thiet bi la luc 03:47 SA. Neu ko phai ban, bam vao link de khoa ngay: http://vcb-secure-alert.net/lock?id=9182736 hoac goi 1800.9999 (mien phi).

Cross-referenced against Phase 28's `golden_scam` result: 5/5 stable, correct verdict every run.

**Benign prompt** (`DEFAULT_BENIGN_TEXT`, channel `sms`) — expect **benign / benign**:
> VPBank Smart OTP: Mã xác thực của bạn là 847291. Mã này có hiệu lực trong 90 giây để xác nhận đăng nhập Internet Banking. Tuyệt đối KHÔNG chia sẻ mã này với bất kỳ ai, kể cả nhân viên ngân hàng.

Cross-referenced against Phase 28's `golden_benign` result: 5/5 stable, correct verdict every run.

The 10-minute slot only has room to show one of these in the recorded video (the scam one, matching the Sample Output slide's framing) — but if a judge asks "what about a legitimate message?", the benign prompt above is your ready answer, already proven stable.

## Closing notes

- **D-12 date fix:** the title slide now correctly reads `15 July 2026` (was `14 July 2026`).
- **Sample Output vs. Demo split:** what was one merged "Live Demo" frame is now two — **Sample Output** (the worked text example, static, not live) and **Demo** (a near-blank frame for your video, also not called live). This reads more honestly: nothing in the deck itself is actually performed live.
- **Backup appendix:** `slides/sections/14_backup.tex` adds 3 hidden frames after Thank You and References, reached only past the main 12-slide sequence (Beamer `\appendix`, footline denominator frozen at 12 via `\insertmainframenumber`). These are Q&A-only — not part of the timed 10-minute walkthrough — and preserve the fuller detail trimmed out of the Motivation & Why Local, Evaluation Results, and Contributions & Future Work frames (including the extra sentences trimmed in this same-day follow-up pass).
