# Requirements: Localized Explainable AI (XAI) Engine for Vietnamese Financial Phishing and Threat Detection

**Defined:** 2026-03-18
**Updated:** 2026-06-18 (v3.0 — Supervisor Comments + Literature Review)

## v3.0 Requirements — Supervisor Comments & Department Standards

| Req | Phase | Description |
| --- | ----- | ----------- |
| LIT-01 | 25 | Literature review: 20-30 citations covering Vietnamese phishing detection, LLM-based fraud/threat detection, local/privacy-preserving NLP, QLoRA/PEFT for classification, synthetic data quality in NLP, and XAI for cybersecurity |
| LIT-02 | 25 | Restructure ch02 into a proper literature review with comparison of existing approaches and clear research gap identification |
| LIT-03 | 25 | All new citations added to references.bib with full metadata |
| BASE-01 | 26 | Run base Qwen3.5-4B (no QLoRA adapter) on the 254 holdout and record per-class precision/recall/F1 |
| BASE-02 | 26 | Add baseline vs fine-tuned comparison table to ch05 (and slides) showing performance improvement |
| DATA-04 | 26 | State explicitly in ch03 that 100% of the corpus is synthetic, with clear rationale |
| PAGE-01 | 27 | Main content 28-35 pages (not counting images or appendix) per department standard |
| PAGE-02 | 27 | Final consistency sweep: slide-report sync, model names, numbers |
**Core Value:** Users can safely verify suspicious Vietnamese financial messages on-device with explainable, high-recall detection that minimizes dangerous misses.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Data Pipeline

- [x] **DATA-01**: System can scrape seed Vietnamese financial threat examples from NCSC sources into normalized raw records.
- [x] **DATA-02**: System can generate a curated synthetic training dataset of 2,000-3,000 JSONL samples from seed data using a controlled LLM generation pipeline.
- [x] **DATA-03**: System can maintain reproducible dataset versions with split governance to reduce leakage and evaluation contamination.

### Ingestion

- [x] **ING-01**: User can paste raw text messages for analysis from channels such as SMS, Zalo, Messenger, Telegram, and Facebook.
- [x] **ING-02**: System can process Vietnamese and mixed Vietnamese-English text, including common code-switch patterns.

### Detection

- [x] **DET-01**: System can classify each input message into risk tiers: benign, suspicious, or high-risk.
- [x] **DET-02**: System can assign in-scope threat labels: bank impersonation, account takeover/social engineering, and light-work-high-pay task scam.

### Explainability

- [x] **XAI-01**: User receives evidence-linked reasons tied to suspicious spans or cues from the input text.
- [x] **XAI-02**: User receives actionable, safety-focused recommendations (for example: do not click links, verify identity via trusted voice call).

### Demo Interface

- [x] **UI-01**: Non-technical users can paste suspicious text into a minimal local demo interface without using CLI syntax.
- [x] **UI-02**: The demo interface clearly presents risk tier, threat labels, grounded cues, and safe recommendations in a zero-prompt flow.

### Runtime and Deployment

- [x] **RUN-01**: User can run inference in local/offline mode without sending message content to cloud APIs in default operation.
- [x] **RUN-02**: System provides a GGUF quantized inference path that works on consumer laptop CPU/iGPU baseline.
- [x] **RUN-03**: System provides an optional accelerated inference path for prosumer GPU hardware.

### Model Adaptation

- [x] **MOD-01**: System supports LoRA-based fine-tuning of an open-source local model family using project dataset artifacts, with a 4B-primary path for 8GB VRAM and optional larger comparison candidates.

### Evaluation and Safety Gates

- [x] **EVAL-01**: Offline evaluation reports include overall F1 score and per-class metrics on held-out data.
- [x] **EVAL-02**: Release gating enforces recall-priority thresholds that minimize false negatives for high-harm scam classes.
- [x] **EVAL-03**: Release gating includes explanation quality checks using a defined rubric for correctness, relevance, and actionability.

## Proposal Closeout Requirements

Requirements for the follow-up milestone that closes the two remaining quantitative claims in the school proposal.

### Dataset Finalization

- [ ] **CLS-01**: System can produce one final validated dataset artifact in the 2,500-3,000 JSONL band, with manifest lineage and per-label counts.

### Evaluation Readiness

- [ ] **CLS-02**: System can freeze train, validation, and test splits with seed-disjoint lineage and non-zero held-out support for `bank_impersonation`, `zalo_social_engineering`, `task_scam`, and `benign` in the final evaluation path.

### Quantitative Closeout

- [ ] **CLS-03**: System can generate a final held-out evaluation report for the locked baseline winner, including macro and weighted F1, per-class precision/recall/F1, and an explicit statement of whether the proposal target F1 >= 0.85 was achieved.

## v1.3 Requirements — Beamer Presentation

Requirements for the defense-ready slide deck milestone.

### Presentation Structure

- [ ] **PRES-01**: Beamer document compiles with XeLaTeX and produces a PDF slide deck covering all thesis chapters in logical order (motivation → system → results → conclusion).
- [ ] **PRES-02**: Slide deck includes a USTH-branded title slide with student name, supervisors, and date.
- [ ] **PRES-03**: Slide count is appropriate for a graduation thesis defense (target 15–20 content slides, excluding title and agenda).

### Content Reuse

- [ ] **PRES-04**: Architecture diagram from thesis (TikZ system overview) appears in a dedicated slide without modification.
- [ ] **PRES-05**: Recall bar chart and confusion matrix from thesis appear in the evaluation slide.
- [ ] **PRES-06**: Real CLI output example (vnphish analyze) appears in the demo/implementation slide.

### Evaluation Narrative

- [ ] **PRES-07**: Evaluation slide presents macro F1 (0.9553), per-class recall table, and the error analysis finding (bank-naming boundary) clearly for judges.

### Handout Readiness

- [ ] **PRES-08**: Slide deck is printable — no overlapping elements, readable at A4 grayscale, no reliance on animation-only content.

### Layout and Theme

- [ ] **PRES-09**: Slide aspect ratio is 16:9 (widescreen), not 4:3 — using Beamer `aspectratio=169` option.
- [ ] **PRES-10**: Color scheme derives from the thesis CVBLUE (#1A5276) as a reference baseline; user may override with a different palette before finalizing — color tokens defined in one central location so a single change recolors the whole deck.
- [ ] **PRES-11**: Font and table styling (booktabs, Times New Roman or fallback sans-serif) is consistent with the thesis where practical.

### File Organization

- [ ] **PRES-12**: Beamer project is split into multiple files mirroring thesis chapter structure — one `.tex` file per logical section (intro, system, data, model, evaluation, demo, conclusion) — `\input{}`-ed from a single `main-slides.tex` entry point.
- [ ] **PRES-13**: Figures and tables reused from thesis are referenced from the same source paths (or copied with attribution) — no duplication of raw data.

## v1.4 Requirements — CambridgeUS Presentation Revamp

Requirements for rebuilding the defense slide deck with professional CambridgeUS/beaver theme. Supersedes the Metropolis skeleton from v1.3. Phase 11 Metropolis slides serve as content reference only.

### Theme and Visual Identity

- [ ] **THME-01**: Presentation uses `\usetheme{CambridgeUS}` with `\usecolortheme{beaver}` as the base theme engine.
- [ ] **THME-02**: USTH navy (#1A5276) is blended into the CambridgeUS/beaver palette — block titles, header/footer bars, and frametitle derive from CVBLUE; a single color-token change recolors the whole deck.
- [ ] **THME-03**: USTH logo (`usth.png`) appears on every slide via `\logo{}`.
- [ ] **THME-04**: Custom footer shows: author short name (left) | presentation short title (center) | frame N/Total (right) on every content slide.
- [ ] **THME-05**: Section navigation bar in header highlights the current section and lists all section names.

### Slide Content

- [ ] **THME-06**: Title slide uses `\titlepage` with: student name Phạm Thế Minh, student ID 23BI14279, supervisors Giang Anh Tuấn and Nguyễn Việt Anh, USTH, and defense year.
- [ ] **THME-07**: Content slides use `\framesubtitle` for secondary context (e.g., "Problem & Motivation", "QLoRA on Qwen 4B", "Held-out Set (254 messages)").
- [ ] **THME-08**: Key call-out content (problem statement, main findings) uses `\begin{block}` environments for visual emphasis.
- [ ] **THME-09**: All sections from the Phase 11 reference deck are preserved: agenda, problem, architecture, data pipeline, why local, model adaptation, evaluation results, confusion matrix, live demo, contributions, limitations & future work, thank you.

### Compilation and Handout

- [ ] **THME-10**: Presentation compiles clean with XeLaTeX in Overleaf — zero errors, zero unresolved references, all TikZ figures render correctly using bare (no float wrapper) input files.
- [ ] **THME-11**: Deck is printable at A4 grayscale — no overlapping elements, text readable without color, no animation-only content.

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Explainability Enhancements

- **XAI-03**: User receives calibrated confidence scores with uncertainty-aware wording.
- **XAI-04**: User receives risk decomposition dimensions (for example urgency pressure, spoofing likelihood, credential theft intent).

### Runtime Enhancements

- **RUN-04**: System meets explicit latency targets per hardware profile with automated benchmarking dashboards.

### Product and Channel Expansion

- **CHN-01**: System supports OCR/image-based text extraction from screenshots.
- **CHN-02**: System supports audio/voice scam analysis.

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
| ------- | ------ |
| OCR and image understanding | Violates strict v1 text-only boundary and expands scope significantly |
| Voice/call analysis | Requires separate ASR/audio pipeline and is outside current objective |
| Cloud-default inference | Conflicts with privacy-first local/offline value proposition |
| Autonomous actions (auto-report/auto-block/auto-reply) | High harm risk from false positives in early versions |
| Broad generic cybersecurity assistant behavior | Dilutes focused financial scam detection mission |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
| ----------- | ----- | ------ |
| DATA-01 | Phase 1 | Complete |
| DATA-02 | Phase 1 | Complete |
| DATA-03 | Phase 1 | Complete |
| ING-01 | Phase 2 | Complete |
| ING-02 | Phase 2 | Complete |
| DET-01 | Phase 4 | Complete |
| DET-02 | Phase 4 | Complete |
| XAI-01 | Phase 4 | Complete |
| XAI-02 | Phase 4 | Complete |
| RUN-01 | Phase 2 | Complete |
| RUN-02 | Phase 3 | Complete |
| RUN-03 | Phase 3 | Complete |
| MOD-01 | Phase 3 | Complete |
| EVAL-01 | Phase 5 | Complete |
| EVAL-02 | Phase 5 | Complete |
| EVAL-03 | Phase 5 | Complete |
| CLS-01 | Phase 7 | Planned |
| CLS-02 | Phase 7 | Planned |
| CLS-03 | Phase 7 | Planned |
| UI-01 | Phase 6 | Complete |
| UI-02 | Phase 6 | Complete |
| THME-01 | Phase 12 | Planned |
| THME-02 | Phase 12 | Planned |
| THME-03 | Phase 12 | Planned |
| THME-04 | Phase 12 | Planned |
| THME-05 | Phase 12 | Planned |
| THME-06 | Phase 12 | Planned |
| THME-07 | Phase 12 | Planned |
| THME-08 | Phase 12 | Planned |
| THME-09 | Phase 12 | Planned |
| THME-10 | Phase 12 | Planned |
| THME-11 | Phase 12 | Planned |

## v1.5 Requirements — Content Gap Closure

Requirements for filling the dataset and QLoRA documentation gaps in both the thesis report and the defense slides.

### Dataset Documentation

- [ ] **GAP-01**: Report Chapter 3 includes a ≤1-paragraph description of seed collection from tinnhiemmang.vn (Vietnamese cybercrime alert site) written as deliberate pipeline design — no iterative recovery history.
- [ ] **GAP-02**: Report Chapter 3 documents the claude-3-5-haiku synthetic generation pipeline with quality-judge gating stats (49/50 batches passed ≥4/5 realism score).
- [ ] **GAP-03**: Slide 05 (Data Pipeline) shows a visual TikZ block flow: tinnhiemmang.vn Seeds → claude-3-5-haiku API → Pydantic Judge → JSONL Output, replacing the current bullet-only layout.
- [ ] **GAP-04**: Slide 05 includes an inline JSONL snippet showing the schema fields: `text`, `label`, `suspicious_spans`.

### QLoRA Documentation

- [ ] **GAP-05**: Report Chapter 3/4 QLoRA section documents training configuration in a table: base model Qwen3-4B-Instruct-2507, r=16, α=32, 4-bit NF4 + double quant, checkpoint-505, loss=0.4951, runtime=1,733s.
- [ ] **GAP-06**: Report Chapter 3/4 explains the GGUF Q8_0 export rationale (CPU-only runtime on consumer laptop via llama.cpp).
- [ ] **GAP-07**: Slide 07 (Model Adaptation) uses a 2-column layout: left = QLoRA constraints and training metrics; right = hardware rationale (fit 4B model in 6 GB VRAM, GGUF for CPU runtime).

### Writing Guardrails

- [ ] **GAP-08**: All new report and slide content presents dataset and training as a single intentional pipeline — no mention of 0.44 recall failure, "repaired" dataset, or recovery iterations anywhere in report or slides.

| GAP-01 | Phase 13 | Planned |
| GAP-02 | Phase 13 | Planned |
| GAP-03 | Phase 13 | Planned |
| GAP-04 | Phase 13 | Planned |
| GAP-05 | Phase 13 | Planned |
| GAP-06 | Phase 13 | Planned |
| GAP-07 | Phase 13 | Planned |
| GAP-08 | Phase 13 | Planned |

**Coverage (v1.5):**

- tracked requirements: 40 total (32 prior + 8 v1.5)
- mapped to phases: 40
- Unmapped: 0

## v2.0 Requirements — Chat UI Revamp

Requirements for milestone v2.0. Replaces the AI-demo card layout with a bilingual Vietnamese/English chat-bubble interface. Backend is frozen.

### Chat Layout

- [ ] **CHAT-01**: User can send a message and see it appear as a right-aligned bubble in the chat thread
- [ ] **CHAT-02**: User sees the bot reply as a left-aligned bubble containing risk tier badge, Vietnamese verdict, grounded cues, and safe next steps
- [ ] **CHAT-03**: User sees animated typing dots while the local model is analyzing (5–30 s inference window)
- [ ] **CHAT-04**: Chat thread auto-scrolls to the latest message after each new bubble is appended

### Input Bar

- [ ] **INPUT-01**: User sends a message by pressing Enter; Shift+Enter inserts a newline without sending
- [ ] **INPUT-02**: User selects the message channel (SMS, Zalo, Messenger, Telegram, Facebook) via an inline picker beside the send button
- [ ] **INPUT-03**: Send button is disabled while an analysis is in-flight; textarea stays editable so user can prepare the next message
- [ ] **INPUT-04**: User can click a sample button to load a pre-written phishing message and auto-submit it

### Polish

- [ ] **POLISH-01**: User can expand or collapse grounded cues and safe next steps sections via `<details>` elements
- [ ] **POLISH-02**: User can clear the entire chat thread and abort any in-flight request with a single button
- [ ] **POLISH-03**: Each new bubble animates in with a subtle entrance effect; animation is suppressed when `prefers-reduced-motion` is active

### Bilingual

- [ ] **I18N-01**: UI labels, input placeholders, bot reply text, and error messages are Vietnamese primary with English technical terms in parentheses (e.g., "Nguy hiểm cao (High risk)")
- [ ] **I18N-02**: All bilingual strings are managed via a dedicated `i18n.js` file served by the demo server; strings are not hardcoded in HTML

### Infrastructure

- [x] **INFRA-01**: Demo page loads Be Vietnam Pro from Google Fonts CDN to ensure correct Vietnamese diacritic rendering on macOS and Linux
- [ ] **INFRA-02**: `demo.py` serves `i18n.js` as a static file; all other backend routes and the `POST /api/analyze` contract remain unchanged

| CHAT-01 | Phase 16 | Pending |
| CHAT-02 | Phase 16 | Pending |
| CHAT-03 | Phase 16 | Pending |
| CHAT-04 | Phase 16 | Pending |
| INPUT-01 | Phase 16 | Pending |
| INPUT-02 | Phase 16 | Pending |
| INPUT-03 | Phase 16 | Pending |
| INPUT-04 | Phase 16 | Pending |
| POLISH-01 | Phase 17 | Pending |
| POLISH-02 | Phase 17 | Pending |
| POLISH-03 | Phase 17 | Pending |
| I18N-01 | Phase 15 | Pending |
| I18N-02 | Phase 15 | Pending |
| INFRA-01 | Phase 14 | Complete |
| INFRA-02 | Phase 15 | Pending |

**Coverage (v2.0):**

- tracked requirements: 15
- mapped to phases: 15
- Unmapped: 0

**Coverage (all milestones):**

- tracked requirements: 55 total (40 prior milestones + 15 v2.0)
- mapped to phases: 55
- Unmapped: 0

## v2.1 Requirements — Defense Corrections

Requirements for milestone v2.1. Addresses all supervisor feedback on slides, model evaluation, and report. Each maps to roadmap phases 19-21.

### Slide Content Fixes (Phase 19)

- [x] **SLIDE-01**: Title slide revised — clarify scope as fine-tuning a model, not building a production app; "Localized" qualifier explained or replaced.
- [x] **SLIDE-02**: Slide 2 retitled "Table of Contents"; slide order corrected (Why Local moved to follow Motivation).
- [x] **SLIDE-03**: Slide 4 (pipeline) renamed away from "System Architecture"; synthetic data note added clarifying it is not used for val/test; "Versioned Splits" renamed to "Data Splits".
- [x] **SLIDE-04**: Slide 5 (data): brief Pydantic explanation added; T-test or quality metric for synthetic data quality mentioned.
- [x] **SLIDE-05**: Slide 6 (privacy/why local) replaces jailbreak content with researched evidence of ChatGPT/cloud API data leakage incidents.
- [x] **SLIDE-06**: Slide 8 (training): `1,733s` label clarified as seconds not "1 second"; quantization mismatch explained — QLoRA 4-bit for training efficiency vs GGUF Q8_0 for CPU inference.
- [x] **SLIDE-07**: Reference slide added at end of deck.

### Binary Evaluation Re-run (Phase 20)

- [x] **EVAL-04**: Model evaluated as 2-class binary classification: scam vs non-scam.
- [x] **EVAL-05**: Slides 9 and 10 updated with binary evaluation results; bar charts replaced with tables.

### Report Revisions (Phase 21)

- [ ] **REPORT-01**: Report sections updated to match corrected slide content after Phase 19 fixes land.
- [ ] **REPORT-02**: Privacy section updated with researched ChatGPT/cloud API data leakage evidence consistent with Slide 6 fix.

| SLIDE-01 | Phase 19 | Complete |
| SLIDE-02 | Phase 19 | Complete |
| SLIDE-03 | Phase 19 | Complete |
| SLIDE-04 | Phase 19 | Complete |
| SLIDE-05 | Phase 19 | Complete |
| SLIDE-06 | Phase 19 | Complete |
| SLIDE-07 | Phase 19 | Complete |
| EVAL-04 | Phase 20 | Complete |
| EVAL-05 | Phase 20 | Complete |
| REPORT-01 | Phase 21 | Pending |
| REPORT-02 | Phase 21 | Pending |

**Coverage (v2.1):**

- tracked requirements: 11
- mapped to phases: 11
- Unmapped: 0

**Coverage (all milestones):**

- tracked requirements: 66 total (55 prior milestones + 11 v2.1)
- mapped to phases: 66
- Unmapped: 0

## v2.2 Requirements — Report Formatting — Department Template

Requirements for milestone v2.2. Reformats the LaTeX thesis to comply with the USTH ICT Bachelor Thesis department template and syncs evaluation tables with Phase 20 slide content. Each maps to roadmap phases 22+.

### Cover Page

- [x] **COVER-01**: Thesis title page uses "BACHELOR THESIS" label (not "GRADUATION THESIS") and "By \<student name\> / Title: \<title\>" layout matching department template

### Certification

- [x] **CERT-01**: Supervisor certification letter page ("To whom it may concern…") added after titlepage, unnumbered, before roman front matter begins

### Front Matter

- [x] **FRONT-01**: Front matter sections appear in department-required order: TOC → Acknowledgements → List of Abbreviations → List of Tables → List of Figures → Abstract
- [x] **FRONT-02**: List of Abbreviations 2-column table added covering all acronyms used in the thesis (AI, LLM, XAI, GGUF, QLoRA, LoRA, NF4, etc.)
- [x] **FRONT-03**: Abstract updated with 6 English keywords; word count verified ≤250 words

### Document Structure

- [ ] **STRUCT-01**: `\thesissection` macro defined in main.tex preamble for Roman numeral headings (I/, II/, …, V/) without corrupting figure and table caption numbering
- [ ] **STRUCT-02**: Thesis content merged and split into 5 Roman numeral sections: Ch1 narrative + Ch2 → I/ Introduction; Ch1 objectives rewritten as prose → II/ Objectives; Ch3+Ch4 → III/ Materials and Methods; Ch5 → IV/ Results and Discussion; Ch6 → V/ Conclusion and Perspective
- [ ] **STRUCT-03**: All 3 hardcoded "Chapter~N" prose cross-references (ch01:22, ch04:~126, ch06:~20) updated to Roman numeral or `\ref{}` form

### Evaluation Tables

- [ ] **EVAL-06**: IV/ Results section includes binary per-class metrics table consistent with Phase 20 slide content
- [ ] **EVAL-07**: IV/ Results section includes 2×2 confusion matrix consistent with Phase 20 slide content

### Appendices

- [ ] **APPEND-01**: Appendices section added at end of document with at least one appendix placeholder

### Slides Sync

- [ ] **SYNC-01**: Slides scanned for "Chapter X" text references; any found instances updated to match new section format

| COVER-01 | Phase 22 | Complete |
| CERT-01 | Phase 22 | Complete |
| FRONT-01 | Phase 22 | Complete |
| FRONT-02 | Phase 22 | Complete |
| FRONT-03 | Phase 22 | Complete |
| STRUCT-01 | Phase 23 | Pending |
| STRUCT-02 | Phase 23 | Pending |
| STRUCT-03 | Phase 23 | Pending |
| EVAL-06 | Phase 23 | Pending |
| EVAL-07 | Phase 23 | Pending |
| APPEND-01 | Phase 24 | Pending |
| SYNC-01 | Phase 24 | Pending |

**Coverage (v2.2):**

- tracked requirements: 12
- mapped to phases: 12
- Unmapped: 0

**Coverage (all milestones):**

- tracked requirements: 78 total (66 prior milestones + 12 v2.2)
- mapped to phases: 78
- Unmapped: 0

## v5.1 Requirements — Demo Verification & Presentation Readiness

Requirements for milestone v5.1. Verifies and hardens the existing local demo before the 13-20 July 2026 defense presentation. Not a new-feature milestone — the backend/API contract stays frozen; findings are fixed non-invasively (external scripts/launchers, self-hosted assets, targeted pins) rather than through redesign.

### Baseline Diagnostics

- [x] **DIAG-01**: `vnphish doctor` reports READY on the dev machine before any other verification proceeds.
- [x] **DIAG-02**: `vnphish analyze` produces correct risk tier, threat label, grounded cues, and safe-steps output for one sample message per in-scope threat class (bank impersonation, account-takeover/social-engineering, task scam) plus one benign message.
- [x] **DIAG-03**: A first-pass warm-latency reading is captured via browser DevTools Network tab for a demo request.
- [x] **GOLD-01**: One scam message and one benign message are selected as the fixed, timed live-demo script for the ~1-minute presentation window.
- [x] **GOLD-02**: Each golden prompt (scam + benign) is run at least 5 times through `vnphish analyze`/`demo` and produces the identical correct verdict every run before being locked as final; any prompt that flips between correct/incorrect across runs is rejected and replaced.

### Environment Parity & Offline

- [ ] **ENV-01**: `vnphish doctor` reports READY on the actual presentation laptop after a fresh install.
- [ ] **ENV-02**: Demo functions correctly with network/Wi-Fi disabled — zero external requests observed in DevTools, confirming the offline claim.
- [ ] **ENV-03**: Be Vietnam Pro font is self-hosted instead of loaded from the Google Fonts CDN.
- [ ] **ENV-04**: `MODEL_ARTIFACT_ROOT` and `MODEL_REGISTRY_PATH` are set as explicit OS-level environment variables so launching `vnphish` from any working directory still resolves the correct off-repo model path (not dependent on CWD-relative `.env/.env` discovery).
- [ ] **ENV-05**: `llama-cpp-python` is exact-pinned to the validated version (`0.3.23`) in `pyproject.toml`.

### Latency Diagnosis & Fix

- [ ] **PERF-01**: True cold-boot-to-first-answer latency is measured on the presentation laptop (not just warm latency).
- [ ] **PERF-02**: If a specific, measured latency bottleneck is found, one targeted fix (e.g., explicit `n_threads`) is applied and re-measured before/after; no fix is applied without a measured cause.
- [ ] **PERF-03**: Latency is verified under both AC power and battery/Balanced power plan.

### UI Quirks, Edge Cases & CLI

- [ ] **UIQ-01**: Full edge-case matrix (empty input, very long text, malformed/off-topic text, mixed Vietnamese-English) is re-tested with no crash or hang.
- [ ] **UIQ-02**: Rapid double-submit is tested to confirm the existing `AbortController` guard still prevents re-entrant requests.
- [ ] **UIQ-03**: CLI entrypoint confusion between `vnphish analyze` (text-only) and `vnphish demo` (web UI) is resolved via help text and/or launcher scripts, without changing the CLI contract.
- [ ] **UIQ-04**: Any UI quirks found during testing are catalogued and fixed without altering the frozen backend contract or breaking `data-slot` templates.

### Fallback & Rehearsal

- [ ] **FB-01**: A recorded video of a successful run using the 2 locked golden prompts (scam + benign) is saved in two local locations.
- [ ] **FB-02**: A static screenshot sequence of the same golden-prompt run is saved as a secondary fallback.
- [ ] **FB-03**: A live-to-fallback pivot is rehearsed at least once.
- [ ] **FB-04**: A full cold-boot dry rehearsal is completed on the actual presentation laptop using final launchers, before the defense window opens (2026-07-13).

| DIAG-01 | Phase 28 | Complete |
| DIAG-02 | Phase 28 | Complete |
| DIAG-03 | Phase 28 | Complete |
| GOLD-01 | Phase 28 | Complete |
| GOLD-02 | Phase 28 | Complete |
| ENV-01 | Phase 29 | Pending |
| ENV-02 | Phase 29 | Pending |
| ENV-03 | Phase 29 | Pending |
| ENV-04 | Phase 29 | Pending |
| ENV-05 | Phase 29 | Pending |
| PERF-01 | Phase 30 | Pending |
| PERF-02 | Phase 30 | Pending |
| PERF-03 | Phase 30 | Pending |
| UIQ-01 | Phase 31 | Pending |
| UIQ-02 | Phase 31 | Pending |
| UIQ-03 | Phase 31 | Pending |
| UIQ-04 | Phase 31 | Pending |
| FB-01 | Phase 32 | Pending |
| FB-02 | Phase 32 | Pending |
| FB-03 | Phase 32 | Pending |
| FB-04 | Phase 32 | Pending |

**Coverage (v5.1):**

- tracked requirements: 21
- mapped to phases: 21 (Phase 28: 5, Phase 29: 5, Phase 30: 3, Phase 31: 4, Phase 32: 4)
- Unmapped: 0

**Coverage (all milestones):**

- tracked requirements: 99 total (78 prior milestones + 21 v5.1)
- mapped to phases: 99
- Unmapped: 0

---
*Requirements defined: 2026-03-18*
*Last updated: 2026-07-02 — v5.1 roadmap created: 21 requirements mapped to Phases 28-32 (added GOLD-01/02 for the 1-minute live-demo golden-prompt constraint)*
