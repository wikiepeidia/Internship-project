# Requirements: Localized Explainable AI (XAI) Engine for Vietnamese Financial Phishing and Threat Detection

**Defined:** 2026-03-18
**Updated:** 2026-08-25 (v7.0 — local two-model training amendment)

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

- [x] **ENV-01**: `vnphish doctor` reports READY on the actual presentation laptop after a fresh install.
- [x] **ENV-02**: Demo functions correctly with network/Wi-Fi disabled — zero external requests observed in DevTools, confirming the offline claim.
- [x] **ENV-03**: Be Vietnam Pro font is self-hosted instead of loaded from the Google Fonts CDN.
- [x] **ENV-04**: `MODEL_ARTIFACT_ROOT` and `MODEL_REGISTRY_PATH` are set as explicit OS-level environment variables so launching `vnphish` from any working directory still resolves the correct off-repo model path (not dependent on CWD-relative `.env/.env` discovery).
- [x] **ENV-05**: `llama-cpp-python` is exact-pinned to the validated version (`0.3.23`) in `pyproject.toml`.

### Latency Diagnosis & Fix

- [x] **PERF-01**: True cold-boot-to-first-answer latency is measured on the presentation laptop (not just warm latency).
- [x] **PERF-02**: If a specific, measured latency bottleneck is found, one targeted fix (e.g., explicit `n_threads`) is applied and re-measured before/after; no fix is applied without a measured cause.
- [x] **PERF-03**: Latency is verified under AC power (High Performance plan), post-reboot. Battery/Balanced-plan measurement is descoped — the laptop runs 1-2h on battery and a charger-backup plan covers the defense-day worst case, so battery-specific throttling is an accepted risk, not a measured one.

### UI Quirks, Edge Cases & CLI

- [x] **UIQ-01**: Full edge-case matrix (empty input, very long text, malformed/off-topic text, mixed Vietnamese-English) is re-tested with no crash or hang.
- [x] **UIQ-02**: Rapid double-submit is tested to confirm the existing `AbortController` guard still prevents re-entrant requests.
- [x] **UIQ-03**: CLI entrypoint confusion between `vnphish analyze` (text-only) and `vnphish demo` (web UI) is resolved via help text and/or launcher scripts, without changing the CLI contract.
- [x] **UIQ-04**: Any UI quirks found during testing are catalogued and fixed without altering the frozen backend contract or breaking `data-slot` templates.

### Fallback & Rehearsal

- [x] **FB-01**: Accepted-risk closeout documented for the fallback recording requirement; no recording files were supplied or verified because defense readiness was scoped mostly to the live demo.
- [x] **FB-02**: Accepted-risk closeout documented for the screenshot fallback requirement; no screenshot sequence was supplied or verified because defense readiness was scoped mostly to the live demo.
- [x] **FB-03**: Accepted-risk closeout documented for the live-to-fallback pivot requirement; no pivot rehearsal was supplied or verified because defense readiness was scoped mostly to the live demo.
- [x] **FB-04**: Final-launcher fresh-process dry-run completed with both locked prompts passing; accepted as the defense-readiness substitute, not a literal OS power-cycle cold boot.

| DIAG-01 | Phase 28 | Complete |
| DIAG-02 | Phase 28 | Complete |
| DIAG-03 | Phase 28 | Complete |
| GOLD-01 | Phase 28 | Complete |
| GOLD-02 | Phase 28 | Complete |
| ENV-01 | Phase 29 | Complete |
| ENV-02 | Phase 29 | Complete |
| ENV-03 | Phase 29 | Complete |
| ENV-04 | Phase 29 | Complete |
| ENV-05 | Phase 29 | Complete |
| PERF-01 | Phase 30 | Complete |
| PERF-02 | Phase 30 | Complete |
| PERF-03 | Phase 30 | Complete |
| UIQ-01 | Phase 31 | Complete |
| UIQ-02 | Phase 31 | Complete |
| UIQ-03 | Phase 31 | Complete |
| UIQ-04 | Phase 31 | Complete |
| FB-01 | Phase 32 | Complete (accepted risk) |
| FB-02 | Phase 32 | Complete (accepted risk) |
| FB-03 | Phase 32 | Complete (accepted risk) |
| FB-04 | Phase 32 | Complete (fresh-process substitute) |

**Coverage (v5.1):**

- tracked requirements: 21
- mapped to phases: 21 (Phase 28: 5, Phase 29: 5, Phase 30: 3, Phase 31: 4, Phase 32: 4)
- Unmapped: 0

**Coverage (all milestones):**

- tracked requirements: 99 total (78 prior milestones + 21 v5.1)
- mapped to phases: 99
- Unmapped: 0

## v5.2 Requirements — Emergency Slide Fix (10-Minute Presentation)

Requirements for milestone v5.2. Compresses the defense slide deck to reliably fit a 10-minute presentation slot without cutting the Architecture/Data/Model methodology depth, and syncs the demo slide to the Phase 32 locked golden prompts. Emergency milestone — defense window is 13-20 July 2026.

### Timing & Trim

- [x] **TIME-01**: Presenter has a measured baseline of current slide/section count and an estimated total delivery time against the 10-minute target.
- [x] **TIME-02**: Non-methodology sections (title, agenda, problem, why-local, confusion matrix, contributions, future work, references, thank-you) are trimmed or merged to reclaim time.
- [x] **TIME-03**: Architecture, Data pipeline, and Model/Training sections retain their existing explanatory depth — no content cuts.
- [x] **TIME-04**: Final deck lands at or near ~10 slides while still covering problem, methodology, evaluation, and conclusion.
- [x] **TIME-05**: Presenter has a rough per-slide timing estimate (seconds/slide) to rehearse against the 10-minute limit.

### Demo Sync

- [x] **GDEMO-01**: Demo section of the slides references the 2 Phase-32 locked golden prompts (Vietcombank no-OTP scam + VPBank Smart OTP benign), not older/stale wording. (Delivered via the presenter run-plan's recording checklist rather than a slide-text edit — the static demo-slide text is deliberately unchanged because it will be covered by the user's own video overlay; see 33-CONTEXT.md D-07/D-08.)
- [x] **GDEMO-02**: The demo-in-slot approach (1-minute reserved demo vs. cutting the demo if timing doesn't fit) is decided and reflected in both the deck and the presenter's run plan.

| TIME-01 | Phase 33 | Complete |
| TIME-02 | Phase 33 | Complete |
| TIME-03 | Phase 33 | Complete |
| TIME-04 | Phase 33 | Complete |
| TIME-05 | Phase 33 | Complete |
| GDEMO-01 | Phase 33 | Complete |
| GDEMO-02 | Phase 33 | Complete |

**Coverage (v5.2):**

- tracked requirements: 7
- mapped to phases: 7
- Unmapped: 0

**Coverage (all milestones):**

- tracked requirements: 106 total (99 prior milestones + 7 v5.2)
- mapped to phases: 106
- Unmapped: 0

## v5.3 Requirements — Slide Scripts & Q&A Preparation

Requirements for milestone v5.3. Emergency milestone — defense is 15 July 2026 (tomorrow). Produces presenter support material only; the thesis report itself is locked and not modified.

### Speaking Script

- [x] **SCRIPT-01**: Talking-point speaking cues exist for each of the 12 main slides (Title, Agenda, Motivation & Why Local, Architecture, Data, Model, Evaluation Results, Contributions & Future Work, Sample Output, Demo, Thank You, References), matching current slide content and order.
- [x] **SCRIPT-02**: Cues for each slide fit within that slide's allotted seconds from `33-RUN-PLAN.md`'s ~8:05 timing budget.
- [x] **SCRIPT-03**: Cues are phrased as short spoken fragments/keywords the presenter elaborates on live, not full sentences to memorize and recite verbatim.

### Q&A Preparation

- [x] **QA-01**: Q&A document covers all major report aspects: data pipeline/dataset, model adaptation (QLoRA/GGUF), architecture/privacy rationale, evaluation/metrics, limitations, and design-choice justifications (why local, why this model, why these threat classes).
- [x] **QA-02**: Each answer is written in plain, first-person, explainable language — concrete numbers and reasoning, not dense AI-polished prose — so the student can internalize and reproduce it in their own words.
- [x] **QA-03**: Q&A explicitly addresses the "does this look AI-generated" risk raised by the judge's informal preview — includes ready talking points if a judge questions authorship or understanding.
- [x] **QA-04**: Q&A is organized by topic/category for fast lookup during last-minute review and live reference.

Deliverables: `documents/reports/supervisor/defense_speaking_script.md`, `documents/reports/supervisor/defense_qa_preparation.md` (both gitignored per project convention — see `.planning/phases/34-speaking-script-qa-preparation/34-01-SUMMARY.md` for the tracked record).

| SCRIPT-01 | Phase 34 | Complete |
| SCRIPT-02 | Phase 34 | Complete |
| SCRIPT-03 | Phase 34 | Complete |
| QA-01 | Phase 34 | Complete |
| QA-02 | Phase 34 | Complete |
| QA-03 | Phase 34 | Complete |
| QA-04 | Phase 34 | Complete |

**Coverage (v5.3):**

- tracked requirements: 7
- mapped to phases: 7
- Unmapped: 0

**Coverage (all milestones):**

- tracked requirements: 113 total (106 prior milestones + 7 v5.3)
- mapped to phases: 113
- Unmapped: 0

## v6.0 Requirements — Report Revision

Requirements for milestone v6.0. Defense held 2026-07-15; judges requested a revision (`documents/Transcript defense.md`). This is content-addition/clarity work within the report's existing voice — not a rewrite. The dominant, most-repeated transcript gap (~10 phrasings) was that the training-label mechanism could not be located or explained live; that gap, more than tone, triggered the AI-authorship suspicion. Slides are LOCKED and out of scope; this milestone touches the thesis report only.

### Problem Framing

- [ ] **FRAME-01**: Report explicitly states early (before methodology/architecture discussion) that this is a supervised multi-class text classification problem with a named 4-class taxonomy.

### Architecture Justification

- [ ] **ARCH-01**: Report explains why classification is achieved via generative structured output (a QLoRA-tuned decoder emitting a label field) rather than an encoder + classification head, using the "generative classification" / verbalizer framing established in research.
- [ ] **ARCH-02**: Report includes an honest Qwen-vs-PhoBERT comparison — task-shape (multi-field structured generation: label + evidence + recommendation) as the primary argument, multilingual extension as secondary, PhoBERT's genuine strengths (Vietnamese-specialized, strong at single-label classification) acknowledged rather than dismissed.

### Dataset & Labeling Methodology

- [ ] **LABEL-01**: Report shows the full JSON record schema (an example record + field-by-field breakdown), with the `label` field's role explicitly named.
- [ ] **LABEL-02**: Report explicitly states labels are assigned at generation time (label-conditioned synthetic generation), not via a separate manual post-hoc labeling pass, with supporting citation.
- [ ] **LABEL-03**: Report includes a first-person worked-example walkthrough of one full record, end to end.
- [ ] **LABEL-04**: Report explicitly distinguishes why training requires the label field while validation/test framing differs.

### Consistency & Evidence Audit

- [ ] **AUDIT-01**: All confusion-matrix and train/val/test split counts are reconciled to one consistent source of truth, referenced identically everywhere they appear in the report (body text, tables, appendix).
- [ ] **AUDIT-02**: Report includes a short error-analysis subsection with 2-3 concrete worked misclassification examples drawn from the actual confusion matrix (the 8 task-scam + 1 Zalo → bank-impersonation errors).
- [ ] **AUDIT-03**: The SHA-256/manifest-integrity rationale is stated as a crisp, explicit sentence in the report text, not just implied.

### Citation Integration

- [ ] **CITE-01**: Every new academic claim introduced by this revision (generative-classification/verbalizer framing, label-conditioned-generation precedent, Qwen-vs-PhoBERT comparison points) has a real, verified BibTeX entry in `references.bib` and a proper `\cite{}` in text — no bare claims.
- [ ] **CITE-02**: Existing citations in sections touched by this revision are checked for accuracy/completeness (light audit, not a full bibliography rewrite).

### Tone & Scope Guardrails

- [ ] **VOICE-01**: New content matches the existing report's plain, direct register — no inflated/thesaurus vocabulary, no invented terminology for its own sake. Reads as honestly closing real gaps, not as a defensive rewrite. Already-strong existing sections are left untouched, not padded.

**Explicit non-goal:** page-count is not a target pursued independently — closing the gaps above should organically add genuine depth; content unrelated to a named gap is out of scope.

## v6.0 Traceability

| Requirement | Phase | Status |
| ----------- | ----- | ------ |
| FRAME-01 | Phase 35 | Complete |
| ARCH-01 | Phase 35 | Complete |
| ARCH-02 | Phase 35 | Complete |
| LABEL-01 | Phase 36 | Complete |
| LABEL-02 | Phase 36 | Complete |
| LABEL-03 | Phase 36 | Complete |
| LABEL-04 | Phase 36 | Complete |
| AUDIT-01 | Phase 37 | Complete (verified consistent, no edit needed) |
| AUDIT-02 | Phase 37 | Complete |
| AUDIT-03 | Phase 37 | Complete (verified already explicit, no edit needed) |
| CITE-01 | Phase 37 | Complete |
| CITE-02 | Phase 37 | Complete (audited, no corrections needed) |
| VOICE-01 | Phase 37 | Complete |

**Coverage (v6.0):**

- tracked requirements: 13
- mapped to phases: 13
- Unmapped: 0

**Coverage (all milestones):**

- tracked requirements: 126 total (113 prior milestones + 13 v6.0)
- mapped to phases: 126
- Unmapped: 0

## v7.0 Requirements — Retake Redemption

Requirements for milestone v7.0. After an F grade, the goal is a full retake defense (~2026-10-07, Wave 2) rebuilt on genuine, hard-to-fake evidence — not another polish pass. The defense transcript's most damaging complaint wasn't tone, it was that nothing proved the student did the work (no training graph, uniformly "succeeded" data/eval story, code that reads as scaffolded).

### Data Repair

- [x] **DATA-04**: Corpus pooled (3,000 + 413 reserved rows), repaired, and re-split by seed-group hash (not row-level) — no `seed_id` may cross a split boundary.
- [x] **DATA-05**: Seed concentration measurably reduced and capped at a stated, justified threshold (currently one seed = 25% of the corpus).
- [x] **DATA-06**: Zero rows with invalid evidence spans (currently 131) — repaired in place where fixable, dropped only where not.
- [x] **DATA-07**: Split ratio locked (80/10/10 proposed) and recorded in a manifest with per-split class distribution.
- [x] **DATA-08**: The genuine `task_scam` 0.44→0.871 recovery story restored into the report as an evidenced iteration narrative.

### Independent Quality Re-Judge

- [x] **JUDGE-01**: Full repaired corpus has a joinable structured Codex result file via `.planning/codex-judge-instructions.md`; Codex is cross-family relative to the original Claude generation lineage, while the 296 surviving GPT/Codex-authored Zalo reconstructions are explicitly disclosed as a same-family exception and separately sampled in the human review.
- [x] **JUDGE-02**: Manual 100-example human check completed by a Vietnamese-fluent reviewer, results captured for report inclusion.
- [x] **JUDGE-03**: T-test removed from the report; replaced with descriptive quality stats plus the manual-check results.

### Real Multi-Model Training Evidence

**Scope amendment (accepted 2026-08-25):** the deliverable is two fresh full local models (Qwen genuine QLoRA and PhoBERT) plus a bounded ordinary-LoRA resource probe whose adapter is discarded. The previous full ordinary-LoRA accuracy-run requirement is withdrawn, not passed. Colab is outside the primary training path and remains available only as a version-pinned validation-stage recovery contingency before the reserved test is opened.

- [x] **TRAIN-01**: A bounded non-quantized LoRA probe on the RTX 5050 records genuine feasibility, steady-state timing, ETA, VRAM, system RAM, temperature, power, and throughput, then discards its probe adapter. The former requirement for a fresh full ordinary-LoRA accuracy run is explicitly withdrawn by the 2026-08-25 local two-model scope amendment; it is not represented as a completed full training run.
- [x] **TRAIN-02**: A bounded RTX 5050 QLoRA probe records the same measurements and discards its adapter; a separate fresh full Qwen run then trains from step zero on the local RTX 5050 under the verified evidence pipeline and fails closed unless the runtime proves `quantization_mode == "4bit-qlora"`. The retained Qwen artifact is the genuine full QLoRA model, exported to GGUF after verification.
- [x] **TRAIN-03**: The former full-run LoRA-vs-QLoRA accuracy comparison is superseded. The report compares ordinary LoRA and QLoRA only as bounded, same-laptop resource-feasibility probes (VRAM, system RAM, throughput, temperature/power, and extrapolated ETA), makes no LoRA-vs-QLoRA accuracy claim, and identifies QLoRA as the only full Qwen training route retained in scope.
- [x] **TRAIN-04**: A real PhoBERT classification-head baseline is fully fine-tuned on the same frozen training/validation data with a logged curve; QLoRA is not added to PhoBERT solely for novelty.
- [x] **TRAIN-05**: The two fresh full local models — PhoBERT classification head and Qwen genuine QLoRA — are compared with real measured validation numbers, reported honestly regardless of outcome; the bounded ordinary-LoRA probe is reported only as resource evidence.
- [x] **TRAIN-06**: Every graph is generated from retained raw logs. Both fresh full local runs and the bounded LoRA/QLoRA probes retain dataset hashes, model identifier/revision, exact sanitized command and resolved configuration, local hardware plus CUDA/package versions, timestamped logs, peak VRAM/system RAM, temperature/power where captured, throughput, applicable `trainer_state`, adapter/checkpoint hashes, and validation metrics. Any contingency Colab artifact must be isolated, version-pinned, and labeled as external recovery evidence rather than silently mixed with the primary local runs; no Git commit identifier is required.

### Held-Out Evaluation Discipline

- [x] **EVAL-08**: The current canonical 220-row test partition (SHA-256 `6f208fb6cd9399b8934225e6a25efd65d49bbb4f4846360837f6835a2561b6d7`) receives exactly one model-evaluation pass, after the two full local models (Qwen QLoRA and PhoBERT) are finalized, under identical conditions. The final evidence discloses known prior human/content exposure from corpus-quality review and thesis drafting plus the automated pre/post-run integrity reads recorded in `data/models/phase41/phase41-provenance-erratum.json`, instead of claiming literal untouchedness or global zero filesystem access. Colab remains an optional validation-stage contingency only before model-evaluation access; held-out results must never trigger retraining, dataset repair, threshold selection, or model selection.
- [x] **EVAL-09**: Final held-out results for both full models are frozen and reported plainly, including a PhoBERT win over the deployed Qwen system. The ordinary-LoRA probe receives no held-out accuracy claim. Any later all-2,097-row deployment fit is separate and carries no unbiased test-score claim.

**Downstream handoff:** Phase 42 and Phase 43 must use the committed Phase 41 verified export and `data/models/phase41/phase41-provenance-erratum.json` together. The erratum's corrected access limitation and terminal no-retry/no-tuning policy are required context, not optional commentary.

### Codebase Architecture Overhaul

- [x] **REFACTOR-01**: Preserve a hash-bound immutable legacy boundary for the exact Phase 40/41 source closure, verified evidence export, provenance erratum, schema strings, artifact names, and four evaluated model roots; refactored code must never be described as the code that generated the frozen metrics.
- [x] **REFACTOR-02**: Decompose `src/model_adaptation/cli.py` into a thin lazy compatibility dispatcher and focused command modules while preserving the installed `vnphish` interface plus every supported legacy subcommand, flag, exit code, and machine-readable output contract.
- [x] **REFACTOR-03**: Establish phase-neutral active boundaries for shared integrity primitives, Qwen/PhoBERT training, inference, evaluation, and evidence reading; eliminate active import cycles without modifying or reserializing frozen historical artifacts.
- [ ] **REFACTOR-04**: Separate reusable data-pipeline core logic from generation/review workflows and one-off corpus migrations; retain original module/command paths as tested shims or hash-recorded archive entries until all callers are proven migrated.
- [x] **REFACTOR-05**: Add synthetic-only characterization, CLI-contract, import-boundary, dependency-cycle, and artifact-byte tests that prove compatibility without accessing or rerunning the reserved held-out evaluation.
- [x] **REFACTOR-06**: Produce a report-ready architecture/provenance map plus an exact D-drive storage inventory identifying required models, optional deployment exports, historical evidence, and explicitly reviewed cleanup candidates; no automated deletion is authorized by this requirement.

### Report Overhaul

- [ ] **REPORT-03**: `WRITING_GUARDRAILS_REPORT.md` derived from a real passed-student reference report once obtained.
- [ ] **REPORT-04**: Each chapter rewritten from student-drafted passages; Claude tightens grammar only, never restructures voice.
- [ ] **REPORT-05**: SHA-256 explanation reworded for tone only (kept, not removed) — matches the corrected, simple explanation already agreed.
- [ ] **REPORT-06**: New content (training graphs, PhoBERT comparison, recovery story, repair methodology) integrated into the right chapters.

### Slide Overhaul

- [ ] **SLIDE-08**: Deck restructured around real pipeline stages (get data → train → GGUF → eval).
- [ ] **SLIDE-09**: Progressive `\pause` reveals added per slide.
- [ ] **SLIDE-10**: New real graphs embedded in the relevant slides.
- [ ] **SLIDE-11**: Deck comes off LOCKED status for this milestone; prior locked deck archived for reference.

### Code Cleanup / Defense Prep

- [ ] **CODE-01**: Guided file-by-file walkthrough covering every major module; AI-style verbose docstrings/comments removed.
- [ ] **CODE-02**: Student writes their own replacement comments per file — a real defense cheatsheet, not cosmetic cleanup.
- [ ] **CODE-03**: SHA-256/manifest-integrity concept explicitly covered in the walkthrough (confirmed live-defense gap).
- [ ] **CODE-04**: Sequenced last, immediately before the retake.

**Out of scope:** adopting the leakage-compromised Hugging Face SMS dataset into training (cited as due-diligence evidence only); chasing a specific page count as a goal; treating a PhoBERT win over the deployed system as a problem to explain away; inventing a full-LoRA accuracy result from the bounded resource probe.

## v7.0 Traceability

| Requirement | Phase | Status |
| ----------- | ----- | ------ |
| DATA-04 | Phase 38 | Complete (v3, post-260808-otp) |
| DATA-05 | Phase 38 | Complete (v3, post-260808-otp) |
| DATA-06 | Phase 38 | Complete (v3, post-260808-otp) |
| DATA-07 | Phase 38 | Complete (v3, post-260808-otp) |
| DATA-08 | Phase 38 | Complete |
| JUDGE-01 | Phase 39 | Complete |
| JUDGE-02 | Phase 39 | Complete |
| JUDGE-03 | Phase 39 | Complete |
| TRAIN-01 | Phase 40 | Complete (bounded probe); former full-LoRA clause withdrawn 2026-08-25 |
| TRAIN-02 | Phase 40 | Complete (genuine QLoRA probe, fresh local full run, verified Q8_0 GGUF) |
| TRAIN-03 | Phase 40 | Complete (resource-only LoRA/QLoRA comparison; no full-LoRA accuracy claim) |
| TRAIN-04 | Phase 40 | Complete (fresh full local PhoBERT classification-head run) |
| TRAIN-05 | Phase 40 | Complete (frozen two-model validation comparison plus 52-row human review) |
| TRAIN-06 | Phase 40 | Complete (hash-linked local evidence and raw-log graphs; Colab closed unused) |
| EVAL-08 | Phase 41 | Complete (single shared-cohort model evaluation; terminal no-retry evidence; mandatory provenance erratum) |
| EVAL-09 | Phase 41 | Complete (both results frozen; PhoBERT advantage reported; deployment fit deferred) |
| REFACTOR-01 | Phase 41.1 | Complete |
| REFACTOR-02 | Phase 41.1 | Complete |
| REFACTOR-03 | Phase 41.1 | Complete |
| REFACTOR-04 | Phase 41.1 | Complete |
| REFACTOR-05 | Phase 41.1 | Complete |
| REFACTOR-06 | Phase 41.1 | Complete |
| REPORT-03 | Phase 42 | Pending |
| REPORT-04 | Phase 42 | Pending |
| REPORT-05 | Phase 42 | Pending |
| REPORT-06 | Phase 42 | Pending |
| SLIDE-08 | Phase 43 | Pending |
| SLIDE-09 | Phase 43 | Pending |
| SLIDE-10 | Phase 43 | Pending |
| SLIDE-11 | Phase 43 | Pending |
| CODE-01 | Phase 44 | Pending |
| CODE-02 | Phase 44 | Pending |
| CODE-03 | Phase 44 | Pending |
| CODE-04 | Phase 44 | Pending |

**Coverage (v7.0):**

- tracked requirements: 34
- mapped to phases: 34
- Unmapped: 0

**Coverage (all milestones):**

- tracked requirements: 160 total (126 prior milestones + 34 v7.0)
- mapped to phases: 160
- Unmapped: 0

---
*Requirements defined: 2026-03-18*
*Last updated: 2026-08-26 — Phase 41 verified complete; EVAL-08/EVAL-09 remain complete, and Phase 42/43 must consume the verified export plus provenance erratum together.*
