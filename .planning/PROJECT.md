# Localized Explainable AI (XAI) Engine for Vietnamese Financial Phishing and Threat Detection

## What This Is

This project builds a localized, offline-capable LLM system that detects, classifies, and explains Vietnamese financial phishing and social engineering messages from raw text. It is designed for general consumers who want zero-prompt verification of suspicious communications without sending private data to cloud APIs. The system prioritizes high-recall threat detection and actionable, understandable explanations.

## Core Value

Users can safely verify suspicious Vietnamese financial messages on-device with explainable, high-recall detection that minimizes dangerous misses.

## Requirements

### Validated

- Phase 1 complete and closed (implementation 2026-04-20, retained artifact closure 2026-05-07): reproducible data foundation established with seed scraping, synthetic generation, recovered-artifact curation, quality judging, deterministic split governance, and SHA256 manifest verification.
- Phase 4 complete and closed (implementation plus UAT/security closeout 2026-05-25): the local runtime now returns stable risk tiers, in-scope threat labels, grounded cues, and safe next steps through the shipped GGUF and accelerated paths, with fail-closed doctor-backed defaults.
- Phase 6 complete and closed (implementation plus UAT closeout 2026-05-25): the repo now ships a defense-ready local demo UI over the existing runtime contract and keeps the interface text-only and local-first.
- Phase 14 complete and closed (2026-06-08): the local demo now has a static chat-shell scaffold with Be Vietnam Pro, `100dvh`, a page-load ARIA live thread, a pinned safe-area composer, and clone-safe `data-slot` templates.
- Milestone v2.2 complete and closed (2026-06-15/16): thesis reformatted to the USTH ICT Bachelor Thesis department template — cover page, certification letter, front matter order, abbreviations table, 5-section Roman numeral restructure, appendices, evaluation tables synced to slides.
- Milestone v3.0 complete and closed (2026-06-18): supervisor comments addressed — literature review added (20+ new citations), baseline Qwen3.5-4B comparison run added, synthetic-data-percentage stated explicitly, page count brought to department target.
- Milestone v4.0 complete and closed (2026-06-19/20): pre-print academic review passed (20 findings fixed) — thesis print-ready at 33 pages, 36 citations, 24 abbreviations, zero compile errors.
- Milestone v5.0 complete and closed (2026-06-20): final audit pass — report LOCKED for print.
- Milestone v5.2 complete and closed (2026-07-13): defense deck compressed 15->12 main frames, Architecture/Data/Model methodology depth untouched, XeLaTeX compiles clean, demo synced to locked golden prompts.
- Milestone v5.3 complete and closed (2026-07-15, defense day): speaking script + Q&A preparation written for the defense; substantial additional slide iteration and live-rehearsal material followed in the same milestone tail (see `.planning/milestones/v5.3-SUMMARY.md`). Defense held 2026-07-15 — complete.
- Phase 28 complete and corrected (2026-07-02): dev-machine baseline diagnostics passed; the final golden demo prompts are a no-OTP malicious-link Vietcombank scam and a legitimate VPBank Smart OTP benign notice, each locked through five stable real web-demo runs; the corrected warm-latency baseline is `22705.562 ms` for Phase 30 comparison.
- Phase 31 complete and verified (2026-07-08): the browser edge-case matrix (empty/very-long/malformed/mixed-language) and rapid double-submit race are covered by an automated real-demo verifier with `overall_pass: true`; the double-submit controller-ownership race was fixed in `demo.js`; `vnphish analyze` vs `vnphish demo` CLI confusion is resolved via clearer help text and two double-click Windows launchers; golden prompts remain stable 5/5 scam and 5/5 benign after the fix, with no backend/template regressions.
- Phase 32 closed for demo-focused defense readiness (2026-07-09): the final `scripts/START_DEMO_UI.bat` launcher passed a fresh-process browser dry-run with both locked golden prompts (`high-risk`/`bank_impersonation` scam and `benign` OTP notice), doctor remains READY, and 30 focused runtime/UI tests passed. Fallback recording, screenshot sequence, and pivot rehearsal were not supplied or verified; they are documented as accepted-risk skips because the operator scoped defense readiness mostly to the live demo. Slide sync remains a separate near-term presentation task.
- Milestone v6.0 complete and closed (2026-07-21): report revision closing the defense's dataset-labeling gap — explicit JSON schema/label-field section, generative-classification (verbalizer) architecture rationale, honest Qwen-vs-PhoBERT comparison, concrete error analysis, and a full consistency/citation audit, all within the report's existing voice.
- Phase 38 complete and closed (2026-08-08): corpus repaired and re-split by seed-group hash (80/10/10, zero leakage, 8% seed cap, zero invalid evidence spans). Execution surfaced a real, previously-hidden problem — `zalo_social_engineering`'s entire 825-row population traced to one seed_id, so correct group-integrity splitting left val/test with zero support for that class. Closed same-day via quick task `260808-otp`: 300 offline Codex-authored replacement rows across 60 independent seed lineages, re-run to `phase38-corpus-repaired-v3` (2,421 rows, all 4 labels present in every split). Post-review also found and fixed 2 real bugs in the shared repair pipeline (`9577394`) before either could affect a future run. All 5 acceptance gates independently re-verified against the real v3 files, not just self-reported.

### Active

- [x] Complete the Codex quality pass on the repaired corpus with a joinable structured JSONL bundle, explicitly disclose that 296 surviving GPT/Codex-authored Zalo reconstructions share the judge family, and pair it with a genuine manual 100-example human check.
- [x] Cut the t-test from the report; replace with plain descriptive quality stats and the manual-check results.
- [ ] Restore the genuine task_scam 0.44→0.871 recovery story into the report.
- [x] Complete the bounded ordinary-LoRA resource probe on the RTX 5050 and discard its adapter; the former full ordinary-LoRA accuracy run is withdrawn, not claimed as completed.
- [ ] Finish the fresh full genuine 4-bit Qwen QLoRA run locally, verify its evidence, and export its retained deployment artifact to GGUF.
- [ ] Fully fine-tune and graph a fresh local PhoBERT classification-head baseline on the same frozen training/validation data.
- [ ] Compare the two full local models on validation, using Colab only as a version-pinned recovery contingency before the reserved test is opened if validation quality makes recovery necessary.
- [ ] Run the current reserved 220-row test split exactly once, at the end, across Qwen QLoRA and PhoBERT; test results must never trigger retraining or dataset repair, and only afterward may a separate deployment model use all 2,097 rows.
- [ ] Overhaul the report in an authentic USTH-student voice, chapter by chapter, once the reference report arrives.
- [ ] Overhaul the slides around real pipeline stages with real graphs and progressive reveals.
- [ ] Guided code-comment cleanup as defense-prep, sequenced last.

### Out of Scope

- Image processing, computer vision, OCR, and screenshot analysis — v1 scope is strictly raw text inputs only.
- Generic broad cybersecurity assistant behaviors beyond financial phishing/social engineering triage — focus is narrow, domain-specific fraud detection.

## Context

The project addresses two core failures in cloud LLM use for fraud checks: privacy risk when users paste sensitive financial text, and weak recognition of local Vietnamese scam patterns, slang, and spoofing tactics. Input sources are copied raw text from channels such as SMS, Zalo, Messenger, Telegram, and Facebook. Threat classes in scope include bank impersonation with malicious domains, account-takeover/social-engineering scams (including compromised contact trust abuse), and "light work, high pay" employment task scams. The data pipeline collects and expands Vietnamese seed threats into a governed synthetic JSONL corpus. The current adaptation path measures ordinary LoRA only as a bounded local feasibility probe, then trains two fresh full models on the RTX 5050 laptop: genuine 4-bit Qwen QLoRA for structured generation and a PhoBERT classification-head baseline. The selected Qwen artifact is quantized to GGUF for local inference, and both full models are evaluated with recall emphasized against the F1 target of >= 0.85.

## Constraints

- **Input Scope**: Raw text only (Vietnamese + mixed Vietnamese-English) — maintain strict v1 boundaries and reduce implementation surface.
- **Privacy**: Offline-capable inference for user-facing checks — sensitive financial text should not require cloud API submission.
- **Deployment Target**: Consumer laptops (CPU/iGPU) as baseline with GGUF quantization; optional prosumer GPU acceleration — maximize practical accessibility.
- **Model Strategy**: Two fresh full local models — Qwen3-4B-Instruct-2507 with genuine 4-bit QLoRA and a PhoBERT classification head — plus one discarded-adapter ordinary-LoRA resource probe; no full-LoRA accuracy claim.
- **Compute Boundary**: Primary training and evidence come from the RTX 5050 laptop. Colab is retained only as a version-pinned validation-stage recovery contingency before the reserved test is opened, never as a response to held-out test results.
- **Data Source Dependency**: NCSC seed extraction quality impacts downstream synthetic data quality — pipeline reliability is critical.
- **Evaluation Policy**: Recall-first release gate with explicit explanation review and paired markdown plus JSON artifacts — reduce dangerous false negatives without hiding review context.

## Key Decisions

| Decision | Rationale | Outcome |
| ---------- | ----------- | ------- |
| Keep v1 strictly text-only | Tight scope improves delivery speed and quality for highest-risk channel | — Pending |
| Use localized domain fine-tuning instead of general cloud prompting | Better fit for Vietnamese fraud patterns and privacy requirements | — Pending |
| Optimize baseline runtime for consumer laptops via GGUF quantization | Enables broad real-world access without dedicated GPU | — Pending |
| Require explainable structured output, not binary labels | Vulnerable users need actionable reasoning and recommendations | — Pending |
| Use explicit recall-first release gates with explanation review and `PASS/BLOCK/FLAG` artifacts | Missing a true threat is costlier than false alarms, and the release decision must stay reviewable | Accepted 2026-05-25 |
| Lock `qwen3-4b-instruct-2507` as the laptop baseline winner and `qwen3.5-4b` as the runner-up for local training/deployment | Larger local pilot on 33 balanced validated samples kept the 4B baseline rule while favoring the best latency and memory fit under the 8GB-VRAM target | Accepted 2026-05-14 |
| Add a proposal-aligned minimal local demo UI as a separate final milestone phase after release gates | The proposal promises a non-technical zero-prompt interface, but Phase 5 should stay focused on evaluation and release readiness first | Accepted 2026-05-25 |
| Start a dedicated Phase 7 closeout milestone for dataset-scale and held-out-metric proof | The shipped six-phase v1 implementation is complete, but the school-facing quantitative claims still need one frozen dataset artifact and one valid final evaluation run | Accepted 2026-05-25 |
| Amend Phase 40 to two full local models plus one bounded ordinary-LoRA probe | The local LoRA probe established genuine resource pressure and an impractical ETA; completing Qwen QLoRA and PhoBERT on the target laptop preserves hardware provenance and saves the remaining delivery time. The former full-LoRA accuracy requirement is withdrawn rather than marked passed. Colab remains only a pre-test validation contingency. | Accepted 2026-08-25 |

## Current Milestone: v7.0 Retake Redemption

**Goal:** Rebuild the project's credibility for a full retake defense (target ~2026-10-07, Wave 2) after an F grade. The defense transcript's most damaging complaint wasn't the report's tone — it was that nothing in the visible evidence (no training graph, uniformly "succeeded" data/eval story, code comments that read as scaffolded) proved the student actually did the work. This milestone produces genuine, hard-to-fake evidence: real curves for two fresh full local models, a measured and honestly bounded ordinary-LoRA feasibility probe, a repaired corpus with disclosed structural bugs, a restored real failure-and-recovery story, an authentically voiced report, and a code-cleanup pass that doubles as defense preparation.

**Target features:**

- Repair the synthetic corpus's structural bugs (one seed = ~25% of the 3,000-row corpus; a seed crossing all three splits; 131 invalid evidence spans) against concrete, checkable acceptance gates — not open-ended cleanup.
- Complete the Codex quality pass on the repaired corpus, disclose its same-family limitation for 296 surviving reconstructed Zalo rows, and pair it with a genuine manual 100-example human check by a Vietnamese-fluent reviewer.
- Cut the t-test (too statistically sophisticated to be a plausible undergraduate's own idea); replace with plain descriptive quality stats plus the new manual-check results.
- Restore the genuine `task_scam` 0.44→0.871 recall-recovery story into the report — real, evidenced, and previously scrubbed by an earlier guardrail rule that (in hindsight) made the report read as suspiciously frictionless.
- Preserve the completed bounded LoRA/QLoRA probe evidence from the RTX 5050 (VRAM, system RAM, throughput, temperature/power, and extrapolated local ETA), discard both probe adapters, and state clearly that the ordinary-LoRA probe was not a full accuracy run. The former full-LoRA requirement is withdrawn rather than retroactively called successful.
- Complete a fresh full genuine 4-bit Qwen QLoRA run from step zero on the RTX 5050, verify its raw evidence, and export the retained deployment model to GGUF.
- Fully fine-tune and graph a fresh local PhoBERT classification-head baseline on the same frozen training/validation data — answering "why Qwen not PhoBERT" with a measured number, not just an architectural argument. A PhoBERT win is reported honestly; the thesis's claim was never "Qwen is the best classifier."
- Keep Colab only as a version-pinned recovery contingency if validation-stage evidence is unacceptable before the test is opened. It is not part of the primary training claim and cannot be triggered by held-out test results.
- Reserve the current 220-row test split (SHA-256 `6f208fb6cd9399b8934225e6a25efd65d49bbb4f4846360837f6835a2561b6d7`) for one final two-model evaluation. Disclose that test content had prior human exposure during corpus-quality review and thesis drafting; the defensible boundary is one post-freeze model-evaluation pass with no test-driven tuning, not literal human blindness. After those results and checkpoint identities are frozen, an optional separately labeled deployment fit may use all 2,097 rows without claiming an unbiased test score. The live boundary is machine-bound in `.planning/phases/39-independent-quality-re-judge/39-DOWNSTREAM-DATA-CONTRACT.json`.
- Overhaul the report chapter by chapter in an authentic USTH-student voice — student-drafted passages that Claude tightens without altering structure or word choice — gated on a real passed-student reference report the user is sourcing. Derive `WRITING_GUARDRAILS_REPORT.md` from that reference once it arrives.
- Overhaul the slides around the real pipeline stages (get data → train → GGUF → eval) with real graphs from the retrains above, using progressive `\pause` reveals; slides come off LOCKED status for this milestone only.
- Guided, file-by-file code-comment cleanup as defense-prep: Claude walks the student through each file, the student writes their own understanding back in as comments — building both a clean codebase and a personal cheatsheet. Sequenced last, right before the retake.

**Explicit non-goals:** no full ordinary-LoRA training or LoRA accuracy claim; no cloud training in the primary evidence path; no retraining, dataset repair, or model selection in response to the reserved-test result; not adopting the leakage-compromised Hugging Face SMS dataset into training (cited as due-diligence evidence only); not treating a PhoBERT-favorable result as a problem to explain away; not chasing a specific page count as its own goal.

**Timeline:** finish the local Qwen QLoRA and PhoBERT runs first, spend the following day on validation comparison and evidence/report integration, then open the reserved test once only after both model identities are frozen; report/slides/code-cleanup follow on the compressed delivery path before the retake defense.

## Completed Milestone: v6.0 Report Revision

**Closed:** 2026-07-21

**Delivered:**

- Phase 35: explicit early problem-framing (Chapter I) stating the core task is supervised 4-class text classification; a new Chapter III paragraph explaining generative classification via a verbalizer (T5/PET/WT5-grounded) as the reason a decoder-emitted label was used instead of a classification head; an honest Qwen-vs-PhoBERT comparison acknowledging PhoBERT's real strengths while explaining the multi-field output requirement that ruled it out. 5 new verified BibTeX entries added.
- Phase 36: a new record-schema table naming all 7 dataset fields with the `label` field's ground-truth role stated explicitly — the exact thing judges said they couldn't find; an explicit statement (with citation) that labels are assigned at generation time via class-conditioned generation, not a manual post-hoc pass; a real record from the validation split walked through field by field; explicit training-vs-validation/test distinction for how the label field is used.
- Phase 37: split/confusion-matrix counts audited across every table and found already fully consistent; a new error-analysis subsection naming the actual 9 misclassified validation rows and showing the errors trace to a genuine class-boundary overlap in the synthetic corpus, not random model confusion; citation and tone audits passed with no corrections needed.
- Full detail: `.planning/milestones/v6.0-SUMMARY.md`

**Verification:** full safe compile sequence (XeLaTeX x3 + BibTeX) after each phase and at close — zero errors, zero undefined references, 34 pages.

## Completed Milestone: v5.3 Slide Scripts & Q&A Preparation

**Closed:** 2026-07-15 (defense day)

**Delivered:**

- Phase 34: talking-point speaking cues for all main defense slides and a topic-organized Q&A preparation document, both in plain first-person language — directly addressing a judge's informal "reads as AI-generated" feedback
- Substantial same-milestone tail-end iteration (untracked as formal phases, given the deadline): Demo section cut to backup then Sample Output reinstated to the main flow; Sample Output's input/output swapped to the real, live-verified golden scam prompt run (catching and fixing 2 real XeLaTeX rendering bugs along the way); a full report-vs-slides numeric audit that found and fixed one real model-name inconsistency; Evaluation Results and Contributions slides trimmed of jargon/unexplainable bullets per live review
- `defense-walkthrough` branch merged into `main`; all 10 numbered code-walkthrough files given heavy teaching-style comments; `walkthrough/data/` added with SHA-256-verified copies of the real final datasets
- Two new root-level prep docs: `defense_walkthrough.md` (slide-anchored Q&A companion) and `defense_qa2.md` (live in-the-room judge-behavior notes captured during the actual defense)
- Full detail: `.planning/milestones/v5.3-SUMMARY.md`

**Defense outcome:** held 2026-07-15, complete. See "Current Milestone" above for judge feedback driving the next milestone.

## Completed Milestone: v5.2 Emergency Slide Fix — 10-Minute Presentation

**Closed:** 2026-07-14

**Delivered:**

- Phase 33: defense deck compressed from 15 to 12 main frames (7 sections) via targeted merges — Architecture/Data/Model sections kept fully intact, verified byte-identical
- Hidden 3-frame Beamer backup appendix preserving trimmed detail for Q&A, footline denominator frozen via `\insertmainframenumber`
- Title-slide date corrected to 15 July 2026; XeLaTeX compiles clean
- Sample Output and Demo split into separate frames (neither framed as "live" — the demo is a recorded video pasted in afterward)
- `33-RUN-PLAN.md`: baseline vs. final timing (~8:05, ~2 min margin under the 10:00 target), locked demo-in-slot decision, and both golden prompts (scam + benign) for the live demo/recording

## Completed Milestone: v5.1 Demo Verification & Presentation Readiness

**Closed:** 2026-07-09 (demo-readiness path) / slide sync folded into v5.2

**Delivered:**

- Phase 28: dev-machine baseline diagnostics; 2 golden prompts (no-OTP Vietcombank scam + VPBank Smart OTP benign) locked 5/5 through the real web demo
- Phase 29: presentation-laptop environment, offline behavior, and portability verified
- Phase 30: latency diagnosed, no fix needed (warm baseline `22705.562 ms`)
- Phase 31: browser edge-case matrix green; double-submit controller-ownership race fixed in `demo.js`; CLI entrypoint confusion resolved via help text and launchers
- Phase 32: `scripts/START_DEMO_UI.bat` launcher passed a fresh-process dry-run with both golden prompts; doctor READY; 30 runtime/UI tests passed. Fallback recording, screenshot sequence, and pivot rehearsal were accepted-risk skips.

## Completed Milestone: v2.2 Report Formatting — Department Template

**Closed:** 2026-06-15/16

**Delivered:**

- Cover page: "BACHELOR THESIS" label + "By / Title:" layout matching department template
- Supervisor certification letter page added
- List of Abbreviations section added (2-column table)
- Abstract: 6 English keywords + ≤250 words (125 words)
- Front matter order: TOC → Acknowledgements → List of Abbreviations → List of Tables → List of Figures → Abstract
- Restructured 6 numbered chapters → 5 Roman numeral sections via `\thesissection` macro (figure/table numbering preserved)
- Appendices section added
- Slides scanned and "Chapter X" references fixed
- Binary per-class metrics table and 2×2 confusion matrix synced to Results section

## Completed Milestone: v2.1 Defense Corrections

**Closed:** 2026-06-09

**Delivered:**

- Slides fixed per supervisor feedback: title, TOC ordering, pipeline naming, Pydantic gate, QLoRA/GGUF explanation, training time unit
- Privacy section reframed with OpenAI March 2023 + Samsung 2023 API leakage incidents
- Binary evaluation: bar charts replaced with per-class metrics table; 2×2 confusion matrix added (binary F1 = 1.000)
- Thesis Chapter 2: jailbreak examples replaced with cloud API data leakage incidents; 23 pages compile clean
- All 11 v2.1 requirements (SLIDE-01–07, EVAL-04–05, REPORT-01–02) met

## Completed Milestone: v2.0 Chat UI Revamp

**Closed:** 2026-06-09

**Delivered:**

- Bilingual Vietnamese/English chat-bubble interface (vanilla HTML/CSS/JS, no framework)
- `i18n.js` bilingual string table served as a static asset
- Full fetch lifecycle: user bubble, typing indicator, bot bubble, error bubble, AbortController, in-memory history
- Collapsible `<details>` sections, bubble entrance animations, clear button, sample button auto-submit
- `100dvh` + `flex: 1 1 0` + `env(safe-area-inset-bottom)` mobile viewport; screen reader ARIA live region

## Completed Milestone: v1.5 Content Gap Closure — Dataset & QLoRA

**Closed:** 2026-06-08

**Delivered:**

- Slide 05 (Data Pipeline): TikZ 4-step block flow (tinnhiemmang.vn → claude-3-5-haiku → Pydantic Judge → JSONL Output) + inline JSONL schema snippet. Arrow labels removed to prevent overlap.
- Slide 07 (Model): 2-column block layout — QLoRA config (r=16, α=32, NF4, step-505, loss=0.4951, 1,733s) left; hardware rationale (6 GB VRAM, GGUF Q8_0, ~13s CPU) right. All tabular labels shortened to prevent hbox overflow.
- Slide 06 (Why Local): cloud_vs_local figure widened, full-width scalebox 0.85, bullets below.
- Report Chapter 3: tinnhiemmang.vn + claude-3-5-haiku generation in data section; QLoRA forward pass equation h=W₀x+(α/r)BAx; training config table (tables/qlora_config.tex).
- Thesis system overview figure: redesigned wider with CVBLUE/charcoal headers — fits A4 without resizebox.
- All [?] citation issues resolved via bibtex pass. Both thesis and slides compile zero errors.

## Current State

- All phases across milestones v1.0–v5.0 are complete and closed.
- Thesis report is print-ready and LOCKED (33 pages, 36 citations, 24 abbreviations, zero compile errors).
- v5.1 demo readiness is closed for the live-demo path: Phase 28 locked the no-OTP scam + benign OTP prompts; Phase 29 verified the presentation-laptop environment, offline behavior, and portability; Phase 30 diagnosed latency with no fix needed; Phase 31 closed with the UI edge-case matrix green, the double-submit race fixed, and CLI entrypoint confusion resolved via help text and launchers; Phase 32 confirmed the final launcher-backed demo path and documented fallback-media gaps as accepted risk.
- v5.2 complete (2026-07-13): deck compressed 15->12 frames, Architecture/Data/Model untouched, XeLaTeX clean, demo split into Sample Output + Demo frames, timing at ~8:05 (2 min margin).
- v5.3 complete (2026-07-14/15): speaking script + Q&A prep written, followed by extensive same-milestone slide iteration and live-rehearsal material (see `.planning/milestones/v5.3-SUMMARY.md`).
- **DEFENSE HELD 2026-07-15 — COMPLETE.** Slides are now LOCKED, no further edits planned.
- v6.0 complete (2026-07-21): report revision closing all judge-raised gaps (label-mechanism visibility, problem framing, architecture rationale, error analysis, citation/tone audit). Report recompiles clean at 34 pages. No next milestone scoped yet.

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):

1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):

1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
Last updated: 2026-08-25 after approving the local two-model Phase 40 scope: full Qwen QLoRA plus full PhoBERT, with ordinary LoRA retained only as a bounded resource-feasibility probe and Colab as a pre-test validation contingency
