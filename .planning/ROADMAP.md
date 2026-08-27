# Roadmap: Localized Explainable AI (XAI) Engine for Vietnamese Financial Phishing and Threat Detection

**Created:** 2026-03-18
**Granularity:** standard
**v1 scope guardrails:** text-only inputs, offline-first privacy, recall-priority safety gates, minimal local demo UI only after evaluation gates

## Phases

- [x] **Phase 1: Data Foundation and Split Governance** - Build reproducible Vietnamese threat datasets from NCSC seed sources with contamination controls.
- [x] **Phase 2: Offline Text Ingestion and Privacy Baseline** - Deliver text-only message intake and default local/offline inference behavior.
- [x] **Phase 3: Local Model Adaptation and Deployment Paths** - Fine-tune the locked Qwen baseline with LoRA/QLoRA and provide laptop GGUF inference plus optional prosumer acceleration paths.
- [x] **Phase 4: Threat Detection and Explainable Decisioning** - Deliver risk-tier classification, threat-type labeling, and evidence-bound recommendations. Closed 2026-05-25 after Phase 4 UAT passed and the security review verified `threats_open: 0`.
- [x] **Phase 5: Recall-Priority Evaluation and Release Gates** - Enforce measurable quality, recall safety thresholds, and explanation-quality acceptance gates. Closed 2026-05-25 after the release-gate engine and paired artifacts shipped; the saved sample run remains `BLOCK` because held-out bank and zalo support are absent.
- [x] **Phase 6: Local Demo UI for Non-Technical Verification** - Wrap the approved local runtime path in a minimal text-only demo interface aligned with the internship proposal. Closed 2026-05-25 after a local demo server, browser UI, and `vnphish demo` launch path shipped.
- [x] **Phase 7: Proposal Closeout and Quantitative Validation** - Freeze final dataset and evaluation artifacts so the remaining school-facing quantitative claims can be proven honestly. Closed 2026-05-26 after the recovered-balanced lineage, repaired held-out evaluation package, UAT, and security audit were finalized.
- [x] **Phase 7a: task_scam Recall Recovery** - Audit existing task_scam data, strengthen generation prompts, generate targeted samples, retrain on Colab H100, fix evaluation gate bug, and re-run holdout evaluation until task_scam recall ≥0.80. Closed 2026-05-28: task_scam recall=0.871, verdict PASS.
- [x] **Phase 7b: App Response Optimization** - Profile and fix local demo response latency by tuning llama.cpp threading, batch, and context-window parameters. Closed 2026-05-29: CPU warm latency ~13s, within thesis demo target.
- [x] **Phase 8: Thesis Structure and Evidence Map** - Lock the graduation-thesis outline, section claims, and supporting repo evidence.
- [x] **Phase 9: Core Thesis Chapter Drafting** - Draft the main technical thesis chapters from the implemented system and final evidence base.
- [x] **Phase 10: Final Thesis Review and Submission Polish** - Finish tone, references, formatting, and judging-ready submission polish. Closed 2026-06-03.
- [x] **Phase 11: Beamer Defense Presentation (Metropolis prototype)** - Built Metropolis-themed skeleton; superseded by Phase 12 revamp.
- [x] **Phase 12: CambridgeUS Presentation Revamp** - Rebuild the defense deck with CambridgeUS/beaver theme, USTH logo, section header, footer, block environments, and polished content slides. Closed 2026-06-05: zero XeLaTeX errors.
- [x] **Phase 13: Content Gap Closure — Dataset & QLoRA** - Document dataset pipeline (tinnhiemmang.vn + claude-3-5-haiku + Pydantic judge) and QLoRA config in thesis report and defense slides. Closed 2026-06-08: all 8 GAP requirements met, zero compile errors.
- [x] **Phase 14: CSS + HTML Scaffolding** - Rewrite demo.css and index.html with chat-bubble layout, Be Vietnam Pro CDN, dvh viewport, pre-rendered ARIA live region, and no-id templates. Closed 2026-06-08.
- [x] **Phase 15: i18n.js + demo.py Static Route** - Ship the bilingual string table as a separate JS module and add one static route in demo.py to serve it. Closed 2026-06-09.
- [x] **Phase 16: demo.js Core Fetch Lifecycle** - Full JS rewrite delivering the end-to-end chat interaction: user bubble, typing indicator, bot bubble, error bubble, AbortController, in-memory history, and rAF scroll. Closed 2026-06-09.
- [x] **Phase 17: Polish + Edge Cases** - Add collapsible details sections, bubble entrance animations with reduced-motion support, clear button, and sample button auto-submit. Closed 2026-06-09.
- [x] **Phase 18: Mobile + Accessibility Validation** - Verify dvh/iOS keyboard behavior, Vietnamese diacritic rendering on macOS and Linux, and screen reader announcement correctness across the completed UI. Closed 2026-06-09.
- [x] **Phase 19: Slide Content Fixes** - Fix all LaTeX slide content per supervisor feedback: title clarity, agenda → table of contents, pipeline naming, synthetic data note, Pydantic/T-test note, API leak privacy research, training time label, quantization explanation, and reference slide. Closed 2026-06-09: all 7 SLIDE requirements met, zero XeLaTeX errors, 16-page PDF.
- [x] **Phase 20: Binary Evaluation Re-run + Eval Slide Updates** - Re-evaluate model as binary scam vs non-scam (2-class); update slides 9-10 with new results in table format. Closed 2026-06-09: per-class metrics table + binary 2×2 matrix added; EVAL-04 EVAL-05 met, zero XeLaTeX errors.
- [x] **Phase 21: Thesis Report Revisions** - Update report sections to match corrected slide content; add ChatGPT/cloud API data leakage evidence to privacy section. Closed 2026-06-09: Chapter 2 jailbreak examples replaced with OpenAI March 2023 + Samsung 2023 data leakage incidents; REPORT-01 REPORT-02 met, thesis compiles clean (23 pages).
- [x] **Phase 22: Cover Page, Certification Letter, and Front Matter** - Reformat the titlepage to department template spec, insert the missing certification letter, and reorder/add front matter sections. Closed 2026-06-15: cover page, certification, front matter order, abbreviations, and abstract keywords compile-verified.
- [x] **Phase 23: Document Restructure and Evaluation Tables** - Replace the 6-chapter numbered structure with 5 Roman numeral sections, fix all prose chapter cross-references, and sync binary evaluation tables from Phase 20 slides. Closed 2026-06-15.
- [x] **Phase 24: Appendices, Slides Sync, and Final Compile** - Add appendices section, scan and fix any "Chapter X" references in slides, and verify the full document compiles clean with XeLaTeX. Closed 2026-06-15.

### v3.0 — Supervisor Comments & Literature Review (2026-06-18)

- [x] **Phase 25: Literature Review Research & Writing** - Research 20-30 papers, restructure ch02 into proper literature review with gap analysis. Covers Vietnamese phishing, LLM fraud detection, local NLP, QLoRA/PEFT, synthetic data, XAI for cybersecurity.
- [x] **Phase 26: Baseline Evaluation & Dataset Clarification** - Run base Qwen3.5-4B (no adapter) on 254 holdout, add comparison table to report+slides, state 100% synthetic explicitly.
- [x] **Phase 27: Page Count & Final Polish** - Verify 28-35 pages per department standard, final consistency sweep.

### v5.1 — Demo Verification & Presentation Readiness (target: complete before defense window opens 2026-07-13)

**Note:** Verification/hardening milestone only — backend/API contract stays frozen; fixes are external scripts/launchers, self-hosted assets, and targeted pins, not redesign.

- [x] **Phase 28: Baseline Readiness & Zero-Code Diagnostics** - Confirm `vnphish doctor` and `vnphish analyze` work correctly on the dev machine using existing zero-code tooling; select and lock 2 golden demo prompts (scam + benign) proven correct across repeated runs, for the ~1-minute live demo window. (completed 2026-07-02)
- [x] **Phase 29: Environment Parity & Offline Verification** - Verify a fresh install on the actual presentation laptop is READY, fully offline, and free of CDN/CWD-relative-path leaks. (completed 2026-07-05)
- [x] **Phase 30: Latency Diagnosis & Targeted Fix** - Measure true cold-boot latency on the presentation laptop and apply one targeted fix only if a specific bottleneck is found. (completed 2026-07-06, AC-only per D-10 SUPERSEDED)
- [x] **Phase 31: UI Quirks, Edge Cases & Regression Re-check** - Re-test the full edge-case matrix and CLI entrypoint clarity after all fixes land, without breaking the frozen backend contract. (completed 2026-07-08)
- [x] **Phase 32: Fallback Recording & Full Dry Rehearsal** - Demo-focused closeout: final launcher dry-run passed; fallback video/screenshot/pivot items documented as accepted-risk caveats. (completed 2026-07-09)

### v5.2 — Emergency Slide Fix — 10-Minute Presentation (target: within defense window 13-20 July 2026)

**Note:** Emergency milestone, single-phase by design — all 7 requirements are tightly coupled edits to the same slide deck (`documents/reports/latex/slides.tex`), not independent workstreams.

- [x] **Phase 33: Emergency 10-Minute Slide Compression** - Audit current slide/section timing, trim non-methodology sections while protecting Architecture/Data/Model depth, land at ~10 slides, sync the demo slide to the 2 locked golden prompts, and lock the demo-in-slot decision. (completed 2026-07-13)

### v5.3 — Slide Scripts & Q&A Preparation (target: before defense 2026-07-15)

**Note:** Emergency milestone, defense is tomorrow (2026-07-15). Two independent, non-overlapping content deliverables — presenter speaking-cue script and Q&A preparation document — touch different files and share no state, but are bundled into a single phase per the smallest-viable-phase-count directive; expected to execute as parallel plans/tasks within one wave rather than as separate phases. Pure content-writing (markdown), not code — the locked thesis report and slide deck are not modified by this milestone.

- [x] **Phase 34: Speaking Script & Q&A Preparation** - Write talking-point speaking cues for all 12 defense slides (short spoken fragments, timed to the `33-RUN-PLAN.md` ~8:05 budget) and a topic-organized Q&A preparation document in plain first-person language, with explicit talking points for authorship/understanding challenges. (completed 2026-07-14)

### v6.0 — Report Revision (target: written revision only, no second oral defense)

**Note:** Content-addition/clarity revision within the report's existing voice — not a rewrite. Closes six defense-transcript gaps in dependency order: problem framing (must exist before architecture text references it) -> architecture rationale (establishes verbalizer/generative-classification vocabulary the labeling section reuses) -> dataset/labeling methodology (single most-repeated transcript gap) -> consistency audit and citation verification (audits everything written, so runs last). Slides are LOCKED and out of scope; this milestone touches the thesis report only.

- [x] **Phase 35: Problem Framing & Architecture Rationale** - State the classification problem explicitly and justify the generative-classification architecture (QLoRA decoder vs. classification head; Qwen vs. PhoBERT). (completed 2026-07-21)
- [x] **Phase 36: Dataset Construction & Labeling Methodology** - Add the explicit, unmissable labeling section: JSON schema, generation-time label assignment, worked example, train-vs-val/test label distinction. (completed 2026-07-21)
- [x] **Phase 37: Consistency Audit & Citation Verification** - Reconcile all confusion-matrix/split counts against real evaluation artifacts, add error-analysis examples, verify citations, and confirm voice/scope guardrails hold. (completed 2026-07-21)

### v7.0 — Retake Redemption (target: retake defense ~2026-10-07, Wave 2)

**Note:** After an F grade, this milestone rebuilds credibility through genuine, hard-to-fake evidence (real training curves, a disclosed-and-repaired corpus, a restored real failure-and-recovery story, an authentically voiced report, and defense-ready code). Real sequencing dependencies, not phase-number order alone, govern execution: data repair and re-judging precede training; the two fresh full models are local Qwen QLoRA followed by local PhoBERT; and the completed ordinary-LoRA probe supplies resource/ETA evidence only. Colab is a version-pinned validation-stage contingency, not the primary training route, and any decision to use it must close before the reserved test is opened. Phase 41 then evaluates the two frozen full models exactly once; its result cannot trigger tuning or dataset repair on the same holdout. Phase 41.1 separates the active application from historical experiment machinery without rewriting the frozen evidence-producing source, so Phase 42 can explain a coherent current architecture. The report and slide overhauls share the Phase 41 evidence (the report is additionally gated on a pending reference-report artifact — see Phase 42). Phase 44 remains last and is the student's own file-by-file comment walkthrough and defense rehearsal, not another structural rewrite.

- [x] **Phase 38: Corpus Repair & Split Governance** - Repair the synthetic corpus's structural bugs (seed concentration, invalid evidence spans, cross-split seed leakage) against concrete acceptance gates and lock a seed-disjoint 80/10/10 split. (completed 2026-08-08)
- [x] **Phase 39: Independent Quality Re-Judge** - Re-run the quality pass with Codex, disclose the 296-row same-family reconstruction exception, complete a genuine manual 100-example human check, and retire the t-test. (completed 2026-08-24)
- [x] **Phase 40: Multi-Model Training Evidence** - Preserve the bounded RTX 5050 LoRA/QLoRA resource probes, then finish fresh full local Qwen QLoRA and PhoBERT runs with auditable logs and genuine curves; make no full-LoRA accuracy claim. (completed 2026-08-26)
- [x] **Phase 41: Held-Out Evaluation Discipline** - Evaluate the two finalized full models exactly once against the reserved test split and report the results plainly. (completed 2026-08-26)
- [ ] **Phase 41.1: Codebase Architecture Overhaul** - Separate the stable application, reusable training/evaluation services, and immutable historical experiment tooling behind compatibility-preserving interfaces before the report rewrite.
- [ ] **Phase 42: Report Overhaul** - Rewrite the thesis chapter by chapter in an authentic student voice (gated on a real reference report), integrating the real training evidence and the restored recovery story.
- [ ] **Phase 43: Slide Overhaul** - Rebuild the defense deck around the real pipeline stages with real graphs and progressive reveals; lift LOCKED status for this milestone only.
- [ ] **Phase 44: Code Cleanup & Defense Prep** - Guided file-by-file walkthrough where the student writes their own replacement comments, covering SHA-256/manifest-integrity explicitly; sequenced last, right before the retake.

## Phase Details

### Phase 1: Data Foundation and Split Governance

**Goal**: A reproducible, versioned text dataset pipeline exists for Vietnamese financial phishing model development and evaluation.
**Depends on**: Nothing (first phase)
**Requirements**: DATA-01, DATA-02, DATA-03
**Success Criteria** (what must be TRUE):

1. Team can run one command flow and produce normalized seed records from NCSC sources without manual spreadsheet cleanup.
2. Team can generate and review a curated synthetic dataset in the 2,000-3,000 JSONL target band.
3. Every dataset build is versioned with reproducible lineage and split definitions that prevent train/eval leakage.
4. Evaluators can reproduce the same train/validation/test splits from versioned artifacts on another machine.

**Plans**: 6 plans

Plans:

- [x] 01-01-PLAN.md -- Project skeleton, Pydantic schemas, config, and test infrastructure
- [x] 01-02-PLAN.md -- NCSC seed scraper with BS4/Playwright, text normalizer, seed JSONL output
- [x] 01-03-PLAN.md -- Tiered LLM synthetic generation pipeline with quality judge
- [x] 01-04-PLAN.md -- Split governance, semantic dedup, SHA256 versioning, pipeline orchestrator
- [x] 01-05-PLAN.md -- Repo-level Phase 1 CLI and retained-seed operator flow
- [x] 01-06-PLAN.md -- Retained artifact gap closure and final recovered dataset lineage

### Phase 2: Offline Text Ingestion and Privacy Baseline

**Goal**: Users can submit suspicious text and receive analysis while keeping content local by default.
**Depends on**: Phase 1
**Requirements**: ING-01, ING-02, RUN-01
**Success Criteria** (what must be TRUE):

1. User can paste raw messages from SMS, Zalo, Messenger, Telegram, or Facebook into the analyzer.
2. System correctly accepts Vietnamese and mixed Vietnamese-English content, including common code-switch phrasing.
3. In default operation, message text is analyzed without cloud API submission and still returns a usable result offline.
4. Product behavior and docs clearly state v1 is text-only; image/OCR and voice channels are not accepted.

**Plans**: 3 plans

Plans:

- [x] 02-01-PLAN.md -- Runtime contracts, privacy defaults, and Wave 0 tests
- [x] 02-02-PLAN.md -- Heuristic analyzer, normalize-first service, and privacy-safe rendering
- [x] 02-03-PLAN.md -- Doctor command, stdin-first CLI, console script wiring, and user-facing docs

### Phase 3: Local Model Adaptation and Deployment Paths

**Goal**: The project can adapt an open local model family to domain data with a 4B-primary path for 8GB VRAM and run it locally across target hardware tiers.
**Depends on**: Phase 2
**Requirements**: MOD-01, RUN-02, RUN-03

**Follow-up note (2026-05-17)**: The Phase 3 pilot winner is locked to `qwen3-4b-instruct-2507` with `qwen3.5-4b` as runner-up. Both retained-dataset adapter runs completed on the target laptop GPU, the baseline and runner-up GGUF artifacts are now generated under the off-repo D-drive model root, `gguf-laptop` and `accelerated-local` have both passed real doctor plus live analyze smokes, and the supervisor-facing 8B-to-4B reconciliation note is now recorded. The CPU/iGPU target in this phase refers to GGUF inference after adaptation, not to CPU-only fine-tuning.

**Success Criteria** (what must be TRUE):

1. Team can execute a LoRA fine-tuning pipeline on the project dataset and produce versioned adapted artifacts for the selected 4B baseline winner and runner-up.
2. User can run a GGUF quantized model path on consumer laptop CPU/iGPU baseline hardware.
3. User can optionally switch to an accelerated path on prosumer GPU hardware with consistent output schema.
4. Runtime selection is explicit and does not require switching to cloud-default inference.

**Plans**: 7 plans

Plans:

- [x] 03-01-PLAN.md -- Candidate registry, pilot scorecard, and local model-artifact manifests
- [x] 03-02-PLAN.md -- QLoRA training scaffold and adapter artifact flow for winner plus runner-up
- [x] 03-03-PLAN.md -- GGUF conversion, CPU baseline backend, and explicit runtime profile selection
- [x] 03-04-PLAN.md -- Accelerated local backend, profile-aware doctor checks, and local-model docs
- [x] 03-05-PLAN.md -- Real GGUF conversion, operator convert command, and doctor-ready registered artifact closeout
- [x] 03-06-PLAN.md -- Trained runner-up accelerated inference closeout and contract-stable runtime proof
- [x] 03-07-PLAN.md -- Supervisor-facing 8B-to-4B reconciliation note and proposal addendum

### Phase 4: Threat Detection and Explainable Decisioning

**Goal**: Users receive clear risk decisions, in-scope threat labels, and evidence-bound safety guidance for pasted text.
**Depends on**: Phase 3
**Requirements**: DET-01, DET-02, XAI-01, XAI-02
**Success Criteria** (what must be TRUE):

1. For each message, system returns one risk tier: benign, suspicious, or high-risk.
2. For risky inputs, system returns one or more in-scope labels: bank impersonation, account takeover/social engineering, or light-work-high-pay task scam.
3. Explanations cite concrete suspicious cues or spans from the provided text rather than generic warnings.
4. Output includes actionable user-safe recommendations (for example, do not click links and verify identity via trusted channels).
5. Responses are provided in a structured format that is stable for downstream UI and testing.

**Plans**: 4 plans

Plans:

#### Phase 5 Wave 1

- [x] 04-01-PLAN.md -- Additive Phase 4 contract, shared decision-layer interface, and Wave 0 runtime verification scaffold

#### Phase 5 Wave 2 *(blocked on Phase 5 Wave 1 completion)*

- [x] 04-02-PLAN.md -- Shared local-model decision schema, grounding checks, deterministic safety helper, and recommendation sanitization

#### Phase 5 Wave 3 *(blocked on Phase 5 Wave 2 completion)*

- [x] 04-03-PLAN.md -- GGUF and accelerated Phase 4 integration plus terminal analyze presentation

#### Wave 4 *(blocked on Wave 3 completion)*

- [x] 04-04-PLAN.md -- Explicit `gguf-laptop` default-profile promotion with doctor-backed fail-closed safety

#### Cross-cutting constraints

- Keep GGUF and accelerated-local aligned through one shared Phase 4 decision layer instead of backend-specific decision logic.
- Preserve grounded cues and safe user-next-step recommendations without widening the existing analyze, render, or doctor operator surfaces.
- Keep explicit runtime-profile selection and fail-closed local behavior intact, including after the `gguf-laptop` default promotion.

### Phase 5: Recall-Priority Evaluation and Release Gates

**Goal**: Release decisions are controlled by safety-focused evaluation gates, with recall prioritized for high-harm scam classes.
**Depends on**: Phase 4
**Requirements**: EVAL-01, EVAL-02, EVAL-03

**Follow-up note (2026-05-25)**: Phase 5 is now fully implemented. The project ships a fail-closed readiness audit, a saved evaluation snapshot, a completed explanation review-pack checkpoint, a final `release-eval` command, and paired markdown plus JSON release artifacts. The current saved run `phase5-review-sample-val` is truthfully `BLOCK` because `data/splits/val.jsonl` contains `task_scam` only and has zero held-out support for `bank_impersonation` and `zalo_social_engineering`.
**Success Criteria** (what must be TRUE):

1. Evaluation reports include overall F1 and per-class metrics on held-out offline data.
2. Go/no-go gating enforces recall-priority thresholds to minimize false negatives on high-harm classes.
3. Explanation outputs pass a defined quality rubric for correctness, relevance, and actionability.
4. A release candidate cannot be marked ready if recall or explanation-quality thresholds fail.

**Plans**: 4 plans

Plans:

#### Wave 1

- [x] 05-01-PLAN.md -- Held-out release-eval readiness audit and shared Phase 5 contracts

#### Wave 2 *(blocked on Wave 1 completion)*

- [x] 05-02-PLAN.md -- Contract-bound offline evaluator and explicit-label metrics

#### Wave 3 *(blocked on Wave 2 completion)*

- [x] 05-03-PLAN.md -- Risky-only explanation rubric scoring, saved manual review pack, and pre-verdict review command

#### Phase 5 Wave 4 *(blocked on Phase 5 Wave 3 completion and the completed Phase 5 manual review pack)*

- [x] 05-04-PLAN.md -- Recall-first verdict synthesis, paired release artifacts, and operator release-eval command

### Phase 6: Local Demo UI for Non-Technical Verification

**Goal**: Give non-technical users a minimal local interface to paste suspicious text and view the approved Phase 5 release-gated analysis without using the CLI.
**Depends on**: Phase 5
**Requirements**: UI-01, UI-02

**Follow-up note (2026-05-25)**: Phase 6 shipped as one lightweight local demo slice. The project now serves a browser UI from `src/runtime/demo.py`, launches it through `vnphish demo`, and renders risk tier, threat labels, grounded cues, and safe recommendations from the existing runtime contract without adding OCR, cloud-default behavior, or a separate frontend framework.
**Success Criteria** (what must be TRUE):

1. A user can paste suspicious message text into a local demo interface without learning CLI commands.
2. The interface presents risk tier, threat labels, grounded cues, and safe recommendations from the shipped local runtime.
3. The demo stays text-only and local-first rather than adding OCR, screenshots, or cloud-default processing.
4. The interface is presentation-ready for internship demo use while preserving the Phase 5 release-gated output contract.

**Plans**: 1 plan

Plans:

- [x] 06-01-PLAN.md -- Local demo server, browser UI, and runtime-backed zero-prompt analysis flow

### Phase 7: Proposal Closeout and Quantitative Validation

**Goal**: Close the two remaining proposal-facing quantitative claims with one final validated dataset artifact and one valid held-out evaluation package for the locked baseline winner.
**Depends on**: Phase 6
**Requirements**: CLS-01, CLS-02, CLS-03

**Follow-up note (2026-05-25)**: This milestone should spend the remaining frontier API budget only on targeted dataset closure for missing classes and validated yield, not on broad exploratory regeneration. The outcome must be one frozen dataset lineage and one school-facing held-out metric report.

**Success Criteria** (what must be TRUE):

1. The repo contains one final validated dataset artifact in the 2,500-3,000 JSONL target band, with manifest lineage and per-label counts.
2. The repo contains frozen train, validation, and test splits with seed-disjoint lineage and non-zero held-out support for `bank_impersonation`, `zalo_social_engineering`, `task_scam`, and `benign` in the final evaluation path.
3. The locked baseline winner can be retrained or refreshed from the frozen split set and re-exported to the shipped local runtime path when needed.
4. The repo contains one final held-out evaluation package that explicitly states whether the proposal target F1 >= 0.85 was achieved.

**Plans**: 2 plans

Plans:

- [x] 07-01-PLAN.md -- Final validated dataset build, targeted Claude-assisted gap closure, and frozen split set
- [x] 07-02-PLAN.md -- Final baseline refresh, held-out evaluation package, and proposal-closeout evidence

### Phase 7a: task_scam Recall Recovery

**Goal**: Push `task_scam` recall from 0.44 to ≥0.80 so the held-out evaluation clears the release gate and thesis writing can report an honest PASS verdict.
**Depends on**: Phase 7
**Requirements**: EVAL-02 (recall-priority gating)
**Success Criteria** (what must be TRUE):

1. Existing 750 task_scam samples audited for scenario diversity and linguistic distinctiveness.
2. Generation prompts strengthened with explicit task_scam scenario axes (social media task farms, review-bombing, crypto referral, etc.).
3. New targeted task_scam rows generated to `data/synthetic/task-scam-recovery-2026-05-28.jsonl` (NOT appended directly to recovered-balanced.jsonl — see CONTEXT D-07); splits rebuilt via `--optimize-recovered`.
4. Model retrained on Colab H100 with new data and adapter registered as `task-scam-recovery-2026-05-28`.
5. Evaluation gate bug fixed: per-label recall floor enforced in `blocker_reasons` / `ready` logic.
6. `evaluate-release-split` and `release-eval` re-run; final verdict is PASS with task_scam recall ≥0.80.

**Plans**: 3 plans

Plans:

- [x] 07a-01-PLAN.md -- Gate bug fix, per-label recall floor patch, and task_scam prompt enrichment (Wave 1)
- [x] 07a-02-PLAN.md -- Colab H100 notebook training section (Wave 1)
- [x] 07a-03-PLAN.md -- Operator workflow: generation, split rebuild, retrain, convert, evaluate, and PASS verdict (Wave 2)

### Phase 7b: App Response Optimization

**Goal**: Reduce local demo inference latency so the app is usable for live demonstration during thesis judging.
**Depends on**: Phase 7
**Requirements**: UI-02 (presentation-ready demo)
**Success Criteria** (what must be TRUE):

1. Per-inference latency profiled and bottleneck identified (cold load vs per-request vs context size).
2. llama.cpp `n_threads`, `n_batch`, and `n_ctx` tuned for the target laptop hardware.
3. Demo response feels interactive (target: first token or full response within acceptable time for live use).

**Plans**: 2 plans

Plans:

- [x] 07b-01-PLAN.md -- Prompt stripping, GGUF constant reduction, demo warm-up, and smoke tests
- [~] 07b-02-PLAN.md -- CUDA wheel installation and GPU offload attempt (with CPU fallback) — SKIPPED: out of proposal scope; CPU ~13s meets thesis target

### Phase 8: Thesis Structure and Evidence Map

**Goal**: Lock the thesis structure, chapter claims, and evidence package so drafting can proceed without re-deciding scope.
**Depends on**: Phase 7
**Requirements**: REP-01

**Success Criteria** (what must be TRUE):

1. The thesis has a final chapter outline aligned to the graduation-report objective.
2. Each main chapter has mapped repo evidence such as artifacts, metrics, commands, or documents that can support its claims.
3. A writing guardrail note captures tone, terminology, and honesty constraints, including avoidance of AI-like wording and internal GSD jargon.
4. The remaining writing schedule for the week is concrete enough to drive the drafting work.

**Plans**: 1 plan

Plans:

- [x] 08-01-PLAN.md -- Thesis outline lock, evidence map, and writing guardrails

### Phase 9: Core Thesis Chapter Drafting

**Goal**: Draft the main technical chapters and evidence-grounded discussion for the graduation thesis.
**Depends on**: Phase 8
**Requirements**: REP-02, REP-03

**Success Criteria** (what must be TRUE):

1. Main chapters for the data pipeline, local/offline runtime, and model adaptation are drafted.
2. Thesis sections for risk and explanation design, evaluation approach, and final quantitative results are drafted with honest treatment of the Phase 7 outcome.
3. Key technical claims in the draft are backed by evidence from repo artifacts or measured outcomes rather than planning notes.
4. The draft reads like an undergraduate thesis chapter set rather than a changelog or internal workflow summary.

**Plans**: 3 plans

Plans:

- [x] 09-01-PLAN.md -- Fix stale eval tables and rewrite Chapter 5 and Chapter 6 with Phase 7a numbers
- [x] 09-02-PLAN.md -- Expand Chapter 3 methodology and Chapter 4 implementation with evidence-grounded prose
- [x] 09-03-PLAN.md -- Citation pass for Chapters 1 and 2 and enable bibliography in main.tex

### Phase 10: Final Thesis Review and Submission Polish

**Goal**: Turn the draft into a judging-ready thesis with consistent references, formatting, and tone.
**Depends on**: Phase 9
**Requirements**: REP-04, REP-05

**Success Criteria** (what must be TRUE):

1. Limitations, conclusion, and future-work framing are complete and honest.
2. References, figures or tables, and formatting are consistent and ready for submission.
3. The thesis wording avoids AI-like phrasing, GSD jargon, and internal planning-file references.
4. A final review confirms the thesis is ready to send for graduation judging.

**Plans**: 1 plan

Plans:

- [x] 10-01-PLAN.md -- Final thesis review, references, formatting, and submission package

### Phase 11: Beamer Defense Presentation

**Goal**: A defense-ready LaTeX Beamer slide deck exists that covers all thesis chapters, reuses existing TikZ figures and evaluation tables, and produces a clean printable PDF for the graduation thesis defense.
**Depends on**: Phase 10
**Requirements**: PRES-01 through PRES-13
**Success Criteria** (what must be TRUE):

1. Beamer project compiles with XeLaTeX to a 16:9 PDF with 15–20 content slides and no layout errors.
2. Title slide shows USTH branding (logo, student name, supervisors, date).
3. Slides cover: motivation → threat scope → system architecture → data pipeline → model adaptation → evaluation results → demo output → conclusion + future work.
4. Architecture TikZ diagram, recall bar chart, and confusion matrix appear without modification.
5. Real CLI output (vnphish analyze on bank-impersonation message) appears in implementation/demo slide.
6. Color tokens defined centrally (CVBLUE baseline, user-swappable); 16:9 aspect ratio enforced.
7. Project split into one `.tex` file per section, all `\input{}`-ed from `main-slides.tex`.
8. Deck is printable at A4 grayscale with readable text and no overflow.

**Plans**: 3 plans

Plans:

- [ ] 11-01-PLAN.md -- Beamer project skeleton: 16:9 layout, central color tokens, USTH title slide, multi-file structure, agenda slide
- [ ] 11-02-PLAN.md -- Technical slides: motivation/scope, system architecture, data pipeline, model adaptation, evaluation results (reuse TikZ + tables)
- [ ] 11-03-PLAN.md -- Demo slide (real CLI output), conclusion + future work, handout mode, final compile and polish

### Phase 12: CambridgeUS Presentation Revamp

**Goal**: A defense-ready Beamer slide deck with CambridgeUS/beaver theme, USTH branding, proper header/footer, and polished content slides that compile clean in XeLaTeX.
**Depends on**: Phase 11 (content reference)
**Requirements**: THME-01 through THME-11
**Success Criteria** (what must be TRUE):

1. Deck compiles with XeLaTeX — zero errors, all TikZ figures render, no overful hboxes.
2. Every slide shows the USTH logo, a footer with author/title/frame-counter, and a section navigation header.
3. Title slide shows Phạm Thế Minh, 23BI14279, both supervisors, USTH, and defense year via `\titlepage`.
4. At least 4 slides use `\begin{block}` for visual emphasis of key findings.
5. All 12 content sections from the Phase 11 reference are present with `\framesubtitle` subtitles.
6. Deck prints cleanly at A4 grayscale — no color-dependent content, no layout overflow.

**Plans**:

- [x] 12-01-PLAN.md — Preamble overhaul: CambridgeUS/beaver theme, CVBLUE color integration, logo, footer template, packages.tex cleanup
- [x] 12-02-PLAN.md — Content slide polish: title slide with `\titlepage`, framesubtitle additions, block environment insertions, agenda revamp with `\tableofcontents`
- [x] 12-03-PLAN.md — Compile verification: fix any remaining layout issues, handout mode check, final PDF review

### Phase 13: Content Gap Closure — Dataset & QLoRA

**Goal**: Document the dataset construction pipeline (tinnhiemmang.vn scraping + claude-3-5-haiku generation + Pydantic quality judge) and QLoRA fine-tuning configuration in both the thesis report chapters and the defense slide deck, written as one deliberate design with no reference to iterative recovery history.

**Depends on**: Phase 12 (slides baseline exists)
**Requirements**: GAP-01, GAP-02, GAP-03, GAP-04, GAP-05, GAP-06, GAP-07, GAP-08

**Guardrails:**

- G-01: No 0.44 recall history, no "repaired" dataset language anywhere
- G-02: Seed source = tinnhiemmang.vn; report description ≤1 paragraph
- G-03: Slides must be visual-first — TikZ flow for data, 2-col for QLoRA

**Success Criteria** (what must be TRUE):

1. Chapter 3 dataset section reads as a clean pipeline narrative: scrape seeds → generate with claude-3-5-haiku → judge quality → produce 3,000-sample JSONL corpus.
2. Chapter 3/4 QLoRA section has a training config table with r=16, α=32, NF4, checkpoint-505, loss=0.4951, runtime=1,733s, and explains GGUF Q8_0 rationale.
3. Slide 05 shows a TikZ block-flow diagram (not bullet list) with an inline JSONL snippet.
4. Slide 07 shows a 2-column layout — constraints left, rationale right.
5. XeLaTeX compiles clean — zero errors after slide changes.
6. No mention of recovery iterations or prior recall failures in any new content.

**Plans:**

- [x] 13-01-PLAN.md — Report: expand Chapter 3 dataset section (seed scraping + claude-3-5-haiku generation + quality-judge stats) and Chapter 3/4 QLoRA section (training config table + GGUF rationale)
- [x] 13-02-PLAN.md — Slides: rewrite 05\_data.tex (TikZ block flow + JSONL snippet) and 07\_model.tex (2-col QLoRA layout); compile verification

---

## Milestone v2.0: Chat UI Revamp (Phases 14–18)

**Milestone Goal:** Replace the AI-demo card layout with a bilingual Vietnamese/English chat-bubble interface that feels like a real messenger app. Backend frozen — only `demo.py` static route added.

### Phase 14: CSS + HTML Scaffolding

**Goal**: The page loads with a structurally correct chat-bubble layout, Be Vietnam Pro font, dvh viewport, and an ARIA live region — verifiable before any JavaScript runs.
**Depends on**: Phase 13
**Requirements**: INFRA-01

**Follow-up note (2026-06-08)**: Phase 14 shipped the static vanilla chat shell with Be Vietnam Pro, `100dvh`, a page-load `role="log"` / `aria-live="polite"` thread, a pinned safe-area composer, and `data-slot` template internals. `demo.py` and the analysis API remain unchanged; Phase 16 owns the JavaScript submit-render migration from old inner-ID selectors to `data-slot`.

**Success Criteria** (what must be TRUE):

1. Opening `index.html` in a browser shows a chat-shell layout (header, scrollable thread area, fixed input bar at the bottom) with no JS errors.
2. Be Vietnam Pro loads from Google Fonts CDN and Vietnamese diacritics render without stacking artifacts on macOS and Linux.
3. The page height fills the viewport using `100dvh` without a horizontal scrollbar; the thread area scrolls independently when content overflows.
4. A `<div role="log" aria-live="polite">` chat thread element is present in the DOM at page load (not injected by JS) so screen readers can announce new messages.
5. No template element uses an `id` attribute on its inner content nodes; all slots are identified by `data-slot` attributes.

**Plans**: 1 plan
Plans:

- [x] 14-01-PLAN.md -- Static chat shell scaffold

**UI hint**: yes

### Phase 15: i18n.js + demo.py Static Route

**Goal**: All UI strings are managed from a single bilingual JS module served by the backend, with no strings hardcoded in HTML.
**Depends on**: Phase 14
**Requirements**: I18N-01, I18N-02, INFRA-02
**Success Criteria** (what must be TRUE):

1. Fetching `GET /static/i18n.js` returns a valid JS file with an `I18N` constant containing keys for all UI labels, placeholders, bot reply text, and error messages.
2. All visible UI text (input placeholder, send button label, channel selector options, error messages) is rendered from `I18N` keys — zero literal strings hardcoded in `index.html`.
3. Labels use Vietnamese as the primary language; English technical terms appear in parentheses (for example, "Nguy hiểm cao (High risk)").
4. `demo.py` serves `i18n.js` via the new static route without modifying any existing route or the `POST /api/analyze` contract.

**Plans**: 1 plan
Plans:

- [x] 15-01-PLAN.md -- i18n.js creation, demo.py static route, index.html data-i18n migration, and test updates

### Phase 16: demo.js Core Fetch Lifecycle

**Goal**: Users can submit a message and receive a structured bot reply through the complete JS fetch lifecycle, with all chat interaction behaviors working end-to-end.
**Depends on**: Phase 15
**Requirements**: CHAT-01, CHAT-02, CHAT-03, CHAT-04, INPUT-01, INPUT-02, INPUT-03, INPUT-04
**Success Criteria** (what must be TRUE):

1. User types a message and presses Enter; it appears as a right-aligned bubble in the thread and the textarea clears.
2. Animated typing dots appear immediately after the user bubble while the local model processes the request (visible for the full 5–30 s inference window).
3. A left-aligned bot bubble appears containing the risk tier badge, Vietnamese verdict, grounded cues, and safe next steps drawn from the API response.
4. The thread scrolls to show the newest bubble after each append, without visible race or anchor jump.
5. Pressing Shift+Enter inserts a newline in the textarea without triggering a send.
6. The channel selector (SMS, Zalo, Messenger, Telegram, Facebook) is embedded in the input bar and its value is included in the API request payload.
7. The send button is disabled and shows a visual in-flight state while a request is pending; a network or model error appends a left-aligned error bubble and re-enables the send button.
8. An in-memory `history[]` array accumulates all sent messages for the tab lifetime; reloading the page clears history (no localStorage).

**Plans**: 2 planned

- [x] 30-01-PLAN.md — Build a cold-latency measurement harness and AC/battery post-reboot runbook (PERF-01, PERF-03 setup)
- [ ] 30-02-PLAN.md — Human AC/Balanced evidence checkpoint, latency comparison, and no-fix-or-one-fix decision record (PERF-01, PERF-02, PERF-03)

**UI hint**: yes

### Phase 17: Polish + Edge Cases

**Goal**: The chat interface handles edge cases gracefully and delivers the differentiating UX behaviors described in the feature table.
**Depends on**: Phase 16
**Requirements**: POLISH-01, POLISH-02, POLISH-03
**Success Criteria** (what must be TRUE):

1. Each bot bubble's grounded cues section and safe next steps section are individually collapsible via `<details>` elements; both start expanded by default.
2. Clicking the clear button removes all bubbles from the thread and aborts any in-flight fetch request in one action.
3. Each new bubble animates in with a subtle entrance effect (for example, fade-slide); the animation does not play when the `prefers-reduced-motion` media query is active.
4. Clicking the sample button loads a pre-written Vietnamese phishing message into the textarea and auto-submits it, producing a complete bot reply with no manual send step.

**Plans**: 3 plans

Plans:

- [x] 31-01-PLAN.md -- Real-demo Playwright edge-case, double-submit, and console-capture verifier
- [x] 31-02-PLAN.md -- CLI help text disambiguation and Windows launchers
- [x] 31-03-PLAN.md -- UIQ-04 triage, final verifier pass, and Phase 28-30 regression evidence

**UI hint**: yes

### Phase 18: Mobile + Accessibility Validation

**Goal**: The completed chat UI works correctly on mobile viewports with iOS soft keyboard, renders Vietnamese diacritics on non-Windows systems, and meets screen reader expectations.
**Depends on**: Phase 17
**Requirements**: (integration verification — all v2.0 requirements are covered by Phases 14–17; this phase validates cross-cutting system behavior)
**Success Criteria** (what must be TRUE):

1. On a mobile viewport with a soft keyboard active, the input bar remains visible and the thread area shrinks to fill the remaining height without content being hidden behind the keyboard (dvh + safe-area-inset-bottom behavior confirmed).
2. Vietnamese diacritics in bot replies and UI labels render without stacking or clipping artifacts when viewed in Chrome/Firefox on macOS and Ubuntu with Be Vietnam Pro loaded.
3. A screen reader (VoiceOver or NVDA) announces each new message appended to the chat thread without requiring the user to navigate manually to the thread region.
4. Submitting a long message (near the runtime text-length cap) returns a valid bot bubble without layout breakage or scroll anchor failure.
5. Clicking "clear" while a request is in-flight cancels the fetch cleanly — no unhandled promise rejection, no orphaned typing indicator left in the DOM.

**Plans**: TBD

**Closeout note (2026-07-09):** Phase 32 was closed under a demo-focused defense-readiness scope. The final `scripts/START_DEMO_UI.bat` launcher passed a fresh-process browser dry-run with both locked golden prompts. Fallback recording, screenshot sequence, and pivot rehearsal were not supplied or verified; they are documented as accepted risks in `32-UAT.md`, `32-VERIFICATION.md`, and `32-DEFENSE-READINESS.md`.

---

### Phase 19: Slide Content Fixes

**Goal**: All defense slides are corrected per supervisor feedback — title clarity, agenda renamed, pipeline slide naming fixed, synthetic data note added, Pydantic explained, API leak research replaces jailbreak content, training time clarified, quantization mismatch explained, and a reference slide added.
**Depends on**: Phase 18
**Requirements**: SLIDE-01, SLIDE-02, SLIDE-03, SLIDE-04, SLIDE-05, SLIDE-06, SLIDE-07
**Success Criteria** (what must be TRUE):

1. Slide 1 title clearly communicates scope as model fine-tuning / training, not building a production app.
2. Slide 2 heading reads "Table of Contents"; slide ordering has Why Local after Motivation.
3. Slide 4 does not use "System Architecture" as the heading; synthetic data note states it is not used for val/test; section heading says "Data Splits".
4. Slide 5 includes a brief explanation of Pydantic's role as the quality judge; T-test or quality metric is mentioned.
5. Slide 6 privacy content references researched ChatGPT/cloud API data leakage incidents (no jailbreak content).
6. Slide 8 (training) clarifies 1,733s = seconds; explains QLoRA 4-bit for training efficiency vs GGUF Q8_0 for CPU inference.
7. A Reference slide exists at the end of the deck.
8. Deck compiles clean with XeLaTeX — zero errors.

**Plans**: 1 plan

Plans:

- [ ] 19-01-PLAN.md -- All slide content fixes: title, section reorder, pipeline rename, synthetic data note, Pydantic note, API leak frame, training time, quantization explanation, reference slide

---

### Phase 20: Binary Evaluation Re-run + Eval Slide Updates

**Goal**: The model is evaluated as a 2-class binary classifier (scam vs non-scam); slides 9-10 are updated with the new binary results presented in table format instead of bar charts.
**Depends on**: Phase 19
**Requirements**: EVAL-04, EVAL-05
**Success Criteria** (what must be TRUE):

1. A binary evaluation run exists for scam vs non-scam (2-class) on the held-out split.
2. Slides 9 and 10 present binary evaluation results in table format.
3. Bar charts on slides 9-10 are replaced or converted to tables.
4. Deck compiles clean with XeLaTeX — zero errors.

**Plans**: TBD

---

### Phase 21: Thesis Report Revisions

**Goal**: Thesis report sections are updated to match the corrected slide content from phases 19-20; the privacy section is updated with ChatGPT/cloud API data leakage evidence.
**Depends on**: Phase 20
**Requirements**: REPORT-01, REPORT-02
**Success Criteria** (what must be TRUE):

1. Report sections that overlap with corrected slide content (title framing, pipeline description, privacy/why-local, training/quantization) are updated to match.
2. Privacy or "Why Local" section in the report includes evidence of ChatGPT/cloud API data leakage incidents.
3. Thesis report compiles clean with XeLaTeX — zero errors.

**Plans**: TBD

---

## Milestone v2.2: Report Formatting — Department Template (Phases 22–24)

**Milestone Goal:** Reformat the LaTeX thesis to comply with the USTH ICT Bachelor Thesis department template; sync evaluation tables and slides.

### Phase 22: Cover Page, Certification Letter, and Front Matter

**Goal**: The thesis titlepage, certification letter, and front matter sections all match the USTH ICT Bachelor Thesis department template, in the correct order and with required content.
**Depends on**: Phase 21
**Requirements**: COVER-01, CERT-01, FRONT-01, FRONT-02, FRONT-03
**Success Criteria** (what must be TRUE):

1. The titlepage renders "BACHELOR THESIS" (not "GRADUATION THESIS") and uses the "By \<student name\> / Title: \<title\>" layout matching the department template.
2. A supervisor certification letter page ("To whom it may concern…") appears immediately after the titlepage, unnumbered, before roman numeral front matter begins.
3. Front matter sections appear in the department-required order: TOC → Acknowledgements → List of Abbreviations → List of Tables → List of Figures → Abstract.
4. A 2-column List of Abbreviations table is present covering all acronyms used in the thesis (AI, LLM, XAI, GGUF, QLoRA, LoRA, NF4, and others).
5. The Abstract contains 6 English keywords and the body is verified ≤250 words.

**Plans**: 1 plan

Plans:

- [x] 22-01-PLAN.md -- Cover page, certification letter, front matter order, abbreviations, and abstract keywords

---

### Phase 23: Document Restructure and Evaluation Tables

**Goal**: The thesis body is restructured from 6 numbered chapters into 5 Roman numeral sections matching the department template, with all prose cross-references updated and binary evaluation tables synced from Phase 20 slides.
**Depends on**: Phase 22
**Requirements**: STRUCT-01, STRUCT-02, STRUCT-03, EVAL-06, EVAL-07
**Success Criteria** (what must be TRUE):

1. A `\thesissection` macro is defined in the main.tex preamble that renders Roman numeral headings (I/, II/, …, V/) without affecting figure and table caption numbering.
2. The 5 sections are present with correct content mapping: I/ Introduction (Ch1 narrative + Ch2), II/ Objectives (Ch1 objectives as prose), III/ Materials and Methods (Ch3 + Ch4), IV/ Results and Discussion (Ch5), V/ Conclusion and Perspective (Ch6).
3. All 3 hardcoded "Chapter~N" prose cross-references (ch01 line ~22, ch04 line ~126, ch06 line ~20) are updated to Roman numeral or `\ref{}` form.
4. Section IV/ Results and Discussion contains a binary per-class metrics table consistent with the Phase 20 slide content.
5. Section IV/ Results and Discussion contains a 2×2 confusion matrix consistent with the Phase 20 slide content.
6. The thesis compiles clean with XeLaTeX after restructure — zero errors, correct figure and table numbering throughout.

**Plans**: 1 plan

Plans:

- [x] 23-01-PLAN.md -- Roman section macro, body restructure, binary eval tables, stale ref fixes

---

### Phase 24: Appendices, Slides Sync, and Final Compile

**Goal**: The thesis has a properly placed appendices section, the defense slides contain no stale "Chapter X" references, and the full document compiles clean end-to-end.
**Depends on**: Phase 23
**Requirements**: APPEND-01, SYNC-01
**Success Criteria** (what must be TRUE):

1. An Appendices section exists at the end of the thesis document with at least one labelled appendix placeholder.
2. The defense slide source files contain no instances of "Chapter X" text that reference the old numbered chapter structure.
3. The full thesis compiles clean with XeLaTeX using the safe sequence (delete aux files + 3 XeLaTeX passes + 1 BibTeX pass) — zero errors, zero unresolved references.
4. The compiled PDF page count and section numbering are visually verified as correct.

**Plans**: 1 plan

Plans:

- [x] 24-01-PLAN.md -- Appendices section, slides scan for Chapter references, final XeLaTeX compile verification

---

## Milestone v5.1: Demo Verification & Presentation Readiness (Phases 28-32) (Phase Details)

**Milestone Goal:** Confirm the local demo runs reliably end-to-end on the presentation laptop before the 13-20 July 2026 defense window, fix known issues (latency, CLI entrypoint confusion, UI quirks), lock 2 golden demo prompts (scam + benign) proven stable across repeated runs for the real ~1-minute live-demo window, and prepare a rehearsed fallback in case the live demo fails. This is a verification/hardening milestone, not new-feature work — the backend/API contract stays frozen; findings are fixed non-invasively (external scripts/launchers, self-hosted assets, targeted version pins) rather than through redesign.

**Hard deadline:** The defense window opens 2026-07-13. All 5 phases must be completable well before that date, in strict sequence — each phase gates the next (doctor pass gates functional verification, which gates edge-case/offline passes, which gate fallback recording).

### Phase 28: Baseline Readiness & Zero-Code Diagnostics

**Goal**: Establish whether the demo's core functionality is reproducibly correct on the dev machine, using only existing zero-code diagnostics, before any further verification work begins — and lock the exact 2 prompts (scam + benign) that will be used for the real ~1-minute live demo.
**Depends on**: Phase 27 (prior milestone closed; first phase of v5.1)
**Requirements**: DIAG-01, DIAG-02, DIAG-03, GOLD-01, GOLD-02
**Success Criteria** (what must be TRUE):

1. `vnphish doctor` exits 0 and reports READY status on the dev machine.
2. `vnphish analyze` produces the correct risk tier, threat label, grounded cues, and safe-steps output for one sample message per in-scope threat class (bank impersonation, account-takeover/social-engineering, task scam) plus one benign message — all 4 samples correct.
3. A first-pass warm-latency reading for a demo request is captured via browser DevTools Network tab and recorded for later comparison.
4. One scam message and one benign message are selected as the fixed live-demo script and each is run at least 5 times, producing the identical correct verdict every run — any prompt that flips is rejected and replaced until a stable pair is found.

**Plans**: 1 plan

Plans:

- [x] 28-01-PLAN.md -- DIAG-01 doctor confirmation, DIAG-02 four-class CLI correctness pass, Playwright golden-prompt verification script, and GOLD-01/GOLD-02/DIAG-03 locking

### Phase 29: Environment Parity & Offline Verification

**Goal**: The demo installs cleanly and runs correctly on the actual presentation laptop, fully offline, with no reliance on CWD-relative environment discovery or CDN dependencies.
**Depends on**: Phase 28
**Requirements**: ENV-01, ENV-02, ENV-03, ENV-04, ENV-05
**Success Criteria** (what must be TRUE):

1. `vnphish doctor` reports READY on the actual presentation laptop after a fresh `pip install -e .[dev,runtime]`.
2. With Wi-Fi/Ethernet disabled, the demo completes a full `analyze` request end-to-end with zero external requests observed in the DevTools Network tab.
3. `index.html` references only self-hosted `.woff2` font files for Be Vietnam Pro — no Google Fonts CDN link remains.
4. Launching `vnphish` from a working directory other than the repo root still resolves the correct off-repo model path, using explicit OS-level `MODEL_ARTIFACT_ROOT` and `MODEL_REGISTRY_PATH` environment variables rather than CWD-relative `.env/.env` discovery.
5. `pyproject.toml` exact-pins `llama-cpp-python==0.3.23`, and a fresh install on the presentation laptop resolves to exactly that version.

**Plans:**

- [x] 29-01-PLAN.md — Self-host Be Vietnam Pro: vendor 12 .woff2 files, add an allowlisted /static/fonts/<filename> route to demo.py, remove Google Fonts CDN links (ENV-03)
- [x] 29-02-PLAN.md — ENV-01 doctor sanity re-check and ENV-05 exact-pin llama-cpp-python==0.3.23 in pyproject.toml
- [x] 29-03-PLAN.md — Set MODEL_ARTIFACT_ROOT/MODEL_REGISTRY_PATH as permanent OS-level env vars via setx, human-verified from a new terminal outside the repo root (ENV-04)
- [x] 29-04-PLAN.md — Human-executed offline network-disconnect runbook proving the demo works with zero external requests, using the two locked Phase 28 golden prompts (ENV-02)

### Phase 30: Latency Diagnosis & Targeted Fix

**Goal**: The true cold-boot-to-first-answer latency on the presentation laptop is known, and — only if a specific, measured bottleneck is found — exactly one targeted fix is applied and re-measured.
**Depends on**: Phase 29
**Requirements**: PERF-01, PERF-02, PERF-03
**Success Criteria** (what must be TRUE):

1. Cold-boot-to-first-answer latency (measured from a post-reboot first request, not a warm request) is measured and recorded on the presentation laptop. — MET: ~27.0s total, ~21.9s per-request, AC/High Performance.
2. If a specific bottleneck is identified (for example, an unset `n_threads` default), exactly one targeted fix is applied with a before/after measurement; if no clear bottleneck is found, no fix is applied and that decision is documented. — MET: `NO_FIX_APPLIED` (no isolating diagnostic evidence for any single parameter).
3. ~~Latency is measured and recorded under both AC power (High Performance plan) and battery/Balanced power plan, with the two results compared.~~ Descoped to AC-only per operator decision (D-10 SUPERSEDED 2026-07-06) — laptop battery life + charger backup cover the defense-day risk.

**Plans**: 2/2 plans executed. Closed 2026-07-06.

- [x] 30-01-PLAN.md — Build a cold-latency measurement harness and AC/battery post-reboot runbook (PERF-01, PERF-03 setup)
- [x] 30-02-PLAN.md — Human AC evidence checkpoint, latency comparison, and no-fix decision record (PERF-01, PERF-02, PERF-03)

### Phase 31: UI Quirks, Edge Cases & Regression Re-check

**Goal**: The demo handles the full edge-case matrix without crash or hang, the `analyze`-vs-`demo` CLI entrypoint confusion is resolved, and any fixes from Phases 28-30 have not regressed existing behavior.
**Depends on**: Phase 30
**Requirements**: UIQ-01, UIQ-02, UIQ-03, UIQ-04
**Success Criteria** (what must be TRUE):

1. The full edge-case matrix (empty input, very long text, malformed/off-topic text, mixed Vietnamese-English) completes with no crash or hang.
2. Rapid double-submit produces exactly one in-flight request; the existing `AbortController` guard still prevents re-entrant requests.
3. CLI help text and/or launcher scripts make the `vnphish analyze` (text-only) vs `vnphish demo` (web UI) distinction clear, with the CLI contract itself unchanged.
4. All UI quirks found during this milestone's testing are catalogued and fixed without altering the frozen backend contract or breaking `data-slot` templates, and the `tests/runtime` suite passes green.

**Plans**: TBD
**UI hint**: yes

### Phase 32: Fallback Recording & Full Dry Rehearsal

**Goal**: A rehearsed, verified fallback exists so the defense can proceed even if the live demo fails, validated by one full cold-boot dry rehearsal on the actual presentation laptop.
**Depends on**: Phase 31
**Requirements**: FB-01, FB-02, FB-03, FB-04
**Success Criteria** (what must be TRUE):

1. A recorded video of one successful run using the 2 locked golden prompts (scam + benign, matching the real live-demo script) is saved in two separate local locations.
2. A static screenshot sequence of the same golden-prompt run is saved as a secondary fallback.
3. A live-to-fallback pivot (simulating a live demo failure and switching to the recording or screenshots) has been rehearsed at least once.
4. A full cold-boot dry rehearsal is completed on the actual presentation laptop using the final launchers, completed before the defense window opens (2026-07-13).

**Plans**: TBD

### Phase 33: Emergency 10-Minute Slide Compression

**Goal**: The defense slide deck reliably fits a 10-minute presentation slot without cutting Architecture/Data/Model methodology depth, the demo slide reflects the 2 Phase-32 locked golden prompts, and the demo-in-slot decision is locked.
**Depends on**: Phase 32
**Requirements**: TIME-01, TIME-02, TIME-03, TIME-04, TIME-05, GDEMO-01, GDEMO-02
**Success Criteria** (what must be TRUE):

1. A documented baseline exists: current slide/section count per file (`01_title.tex` through `15_thankyou.tex`) and an estimated total delivery time against the 10-minute target, captured before any trims are made.
2. Non-methodology sections (`01_title`, `02_agenda`, `03_problem`, `06_why_local`, `09_confusion`, `11_contributions`, `12_future`, `13_references`, `15_thankyou`) are visibly trimmed or merged to reclaim time, while `04_architecture.tex`, `05_data.tex`, and `07_model.tex` retain their existing explanatory depth with no content cut.
3. The compiled deck (XeLaTeX, zero errors) lands at or near ~10 slides while still covering problem, methodology, evaluation, and conclusion.
4. A rough per-slide timing estimate (seconds/slide) exists and sums to at or under 10 minutes total, including whatever demo time was decided on, so the presenter can rehearse against the real limit.
5. The demo section (`10_demo.tex`) references the exact 2 Phase-32 locked golden prompts (Vietcombank no-OTP malicious-link scam + VPBank Smart OTP benign notice) with no stale wording, and the demo-in-slot decision (1-minute reserved demo vs. cut-if-timing-doesn't-fit) is written into both the deck and the presenter's run plan.

**Plans**: 1/1 plan executed

Plans:

- [x] 33-01-PLAN.md -- Compress 15->11 frames across 4 merges (Motivation+WhyLocal, Evaluation+Confusion, Contributions+Future, Demo), fix the defense date, wire a hidden backup appendix, XeLaTeX-verify, and write the presenter run plan (baseline+final timing, demo-in-slot decision, golden-prompt recording checklist)

### Phase 34: Speaking Script & Q&A Preparation

**Goal**: The presenter has talking-point speaking cues for all 12 defense slides and a topic-organized Q&A preparation document, both in plain first-person, explainable language, so they can present and defend the work confidently in their own words at the 2026-07-15 defense — directly addressing the judge's informal "reads as AI-generated" feedback.
**Depends on**: Phase 33
**Requirements**: SCRIPT-01, SCRIPT-02, SCRIPT-03, QA-01, QA-02, QA-03, QA-04
**Success Criteria** (what must be TRUE):

1. A speaking-cues document exists covering all 12 main slides in current deck order (Title, Agenda, Motivation & Why Local, Architecture, Data, Model, Evaluation Results, Contributions & Future Work, Sample Output, Demo, Thank You, References), with each slide's cues phrased as short spoken fragments/keywords to elaborate on live — not full sentences to recite — sized to fit that slide's allotted seconds from `33-RUN-PLAN.md`'s ~8:05 timing budget.
2. A Q&A preparation document exists, organized by topic (data pipeline/dataset, model adaptation QLoRA/GGUF, architecture/privacy rationale, evaluation/metrics, limitations, design-choice rationale), with every answer written in plain first-person language backed by concrete numbers and reasoning the presenter can restate in their own words.
3. The Q&A document contains an explicit, ready-to-use set of talking points for "does this look/sound AI-generated" and authorship/understanding-challenge questions from judges.
4. The presenter can locate any topic's answer within seconds during last-minute review — the document is organized with clear per-topic headers/lookup structure, not one undifferentiated block of prose.

**Plans**: 1/1 plan executed

Plans:

- [x] 34-01-PLAN.md (executed directly, no separate PLAN.md file — see 34-01-SUMMARY.md) -- Speaking script + Q&A prep for all 12 slides, both in documents/reports/supervisor/ (gitignored per project convention)

---

## Milestone v6.0: Report Revision (Phases 35-37) (Phase Details)

**Milestone Goal:** Close the specific gaps judges raised live in the defense (`documents/Transcript defense.md`) through targeted content additions to the LaTeX thesis report -- problem framing, architecture rationale, dataset/labeling methodology, and a numeric-consistency plus citation audit -- without shifting the report's existing tone/voice. Slides are LOCKED; this milestone touches the thesis report only (primarily `documents/reports/latex/chapters/03_methodology_and_system_design.tex` and `appendices.tex`, plus `references.bib`). Written revision only -- no second oral defense expected.

### Phase 35: Problem Framing & Architecture Rationale

**Goal**: The report explicitly states the classification problem framing and honestly justifies the architectural choices (generative decoder vs. classification head; Qwen vs. PhoBERT) before any system/data detail -- closing the "why not a classification head" and "why Qwen not PhoBERT" gaps raised live.
**Depends on**: Phase 34 (prior milestone closed; first phase of v6.0)
**Requirements**: FRAME-01, ARCH-01, ARCH-02
**Success Criteria** (what must be TRUE):

1. An early, named subsection (appearing before architecture/data discussion in the methodology chapter) explicitly states the task is supervised multi-class text classification with the 4 named classes.
2. A named subsection ("Why Generative Classification, Not a Classification Head" or equivalent) explains classification via generative structured output using the verbalizer/generative-classification framing, backed by at least one real citation.
3. A named subsection presents an honest Qwen-vs-PhoBERT comparison: task-shape (multi-field structured generation) as the primary argument, multilingual extension as secondary, and PhoBERT's genuine strengths (Vietnamese-specialized, strong single-label classification) acknowledged rather than dismissed.
4. The report compiles clean with XeLaTeX (zero errors) after these additions, and no unrelated existing section's wording is altered.

**Plans**: 1/1 executed directly (see `.planning/milestones/v6.0-SUMMARY.md`)

### Phase 36: Dataset Construction & Labeling Methodology

**Goal**: An explicit, unmissable section documents exactly how training labels work end-to-end -- closing the single most-repeated defense gap (asked roughly ten different ways, never answered).
**Depends on**: Phase 35 (reuses the verbalizer/generative-classification terminology established there)
**Requirements**: LABEL-01, LABEL-02, LABEL-03, LABEL-04
**Success Criteria** (what must be TRUE):

1. A named "Dataset Construction and Labeling Methodology" subsection shows a full example JSON record plus a field-by-field table, with the `label` field's role explicitly named as the ground-truth training class.
2. The subsection explicitly states labels are assigned at generation time (label-conditioned synthetic generation -- each record generated for a target class) rather than a post-hoc manual labeling pass, supported by a real citation.
3. A first-person worked-example walkthrough traces one full record end-to-end (seed input through generation prompt to labeled output).
4. The subsection explicitly distinguishes why the label field is required for training but not for the validation/test framing.
5. The report compiles clean with XeLaTeX (zero errors) after these additions.

**Plans**: 1/1 executed directly (see `.planning/milestones/v6.0-SUMMARY.md`)

### Phase 37: Consistency Audit & Citation Verification

**Goal**: Every number in the report reconciles to one source of truth, every new claim introduced by this revision is properly cited, and the whole revision reads in the report's original voice without touching or padding already-strong sections -- closing the numeric-inconsistency and authorship-suspicion gaps.
**Depends on**: Phase 36 (audits the newly added content plus pre-existing numbers)
**Requirements**: AUDIT-01, AUDIT-02, AUDIT-03, CITE-01, CITE-02, VOICE-01
**Success Criteria** (what must be TRUE):

1. Confusion-matrix and train/val/test split counts are reconciled against the real evaluation artifacts and read identically everywhere they appear in the report (body text, tables, appendix), including a check for any stale binary-classification leftovers from the earlier Phase 20 binary re-run.
2. A short error-analysis subsection exists with 2-3 concrete worked misclassification examples drawn from the actual confusion matrix (task_scam + zalo -> bank_impersonation errors).
3. A crisp, explicit sentence states the SHA-256/manifest-integrity rationale in the report body text.
4. Every new academic claim introduced across Phases 35-36 has a verified BibTeX entry in `references.bib` and a `\cite{}` in text; existing citations in sections touched by this revision are spot-checked for accuracy.
5. A side-by-side comparison of new vs. pre-existing prose shows consistent register (no vocabulary/tone shift); sections unrelated to a named gap remain untouched; the full report compiles clean with XeLaTeX (zero errors).

**Plans**: 1/1 executed directly (see `.planning/milestones/v6.0-SUMMARY.md`)

---

## Milestone v7.0: Retake Redemption (Phases 38-44) (Phase Details)

**Milestone Goal:** After an F grade, rebuild credibility for a full retake defense (~2026-10-07, Wave 2) on genuine, hard-to-fake evidence. Repair the corpus against concrete gates, independently re-judge it (Codex plus a manual human check), preserve measured ordinary-LoRA resource evidence without inventing a full-run accuracy result, train and honestly compare full local Qwen QLoRA and PhoBERT models, evaluate the reserved test split exactly once across those two frozen models, overhaul the report and slides around the real evidence, and close with a guided code-cleanup pass that doubles as the student's own defense cheatsheet.

### Phase 38: Corpus Repair & Split Governance

**Goal**: The synthetic corpus's structural bugs (seed concentration, invalid evidence spans, cross-split seed leakage) are repaired and re-split by seed-group hash against concrete, checkable acceptance gates, giving all downstream re-judging, training, and evaluation work a trustworthy foundation instead of open-ended cleanup.
**Depends on**: Phase 37 (prior milestone closed; first phase of v7.0)
**Requirements**: DATA-04, DATA-05, DATA-06, DATA-07, DATA-08
**Success Criteria** (what must be TRUE):

1. The pooled corpus (3,000 + 413 reserved rows) is re-split by seed-group hash, and a verification pass confirms zero `seed_id` values appear in more than one of `train.jsonl`/`val.jsonl`/`test.jsonl`.
2. The largest single seed's share of the corpus is measurably reduced from the prior ~25% to a stated, justified cap, with the before/after percentage recorded in a manifest.
3. Zero rows in the final corpus have invalid evidence spans (repaired in place where fixable, dropped only where not) — down from the prior 131.
4. A manifest file records the locked 80/10/10 split ratio and per-split, per-class row counts for all four labels (`bank_impersonation`, `zalo_social_engineering`, `task_scam`, `benign`).
5. A drafted `task_scam` 0.44→0.871 recovery narrative exists, grounded in the real Phase 7a evidence artifacts (not invented), ready for the Report Overhaul phase to place in the right chapter.

**Plans**: 2/2 plans executed

- [x] 38-01-PLAN.md
- [x] 38-02-PLAN.md

### Phase 39: Independent Quality Re-Judge

**Goal**: The repaired corpus is verified with a complete Codex result bundle and a genuine human review, with cross-family scope and the 296-row same-family reconstruction exception stated explicitly, replacing the retired t-test with defensible descriptive statistics.
**Depends on**: Phase 38
**Requirements**: JUDGE-01, JUDGE-02, JUDGE-03
**Success Criteria** (what must be TRUE):

1. A joinable structured result file (`data/processed/codex-judge-pass.jsonl`, per `.planning/codex-judge-instructions.md`) exists covering every row of the repaired corpus, with `row_index`/`seed_id` fields that join back to the source rows.
2. A documented manual 100-example human check exists, completed by a Vietnamese-fluent reviewer, with a per-example pass/fail record and a summary suitable for direct report citation.
3. The report's t-test section is removed and replaced with plain descriptive quality stats (pass rate, per-dimension averages from the Codex judge) plus the manual-check results.

**Plans**: 7/7 plans complete

Plans:

- [x] 39-01-PLAN.md -- Codex judge-output merge/validation tool and stratified 100-row manual-review-sheet generator, proven against realistic fixtures
- [x] 39-02-PLAN.md -- Stage the strict 324-decision migration, shared-lineage quarantine, cap, whole-seed re-split, and immutable audit provenance
- [x] 39-03-PLAN.md -- Build exact-record carry-forward tooling and prepare nine deterministic, hash-locked fresh-delta judge batches
- [x] 39-04-PLAN.md -- Run the local Codex batches and converge any semantic repairs through fresh, restartable re-judgment
- [x] 39-05-PLAN.md -- Atomically promote the converged corpus/judge bundle and refresh Phase 40/41 contracts from the live manifest
- [x] 39-06-PLAN.md -- Generate a new final-snapshot 100-row sheet and stop at a genuine blocking human-review checkpoint
- [x] 39-07-PLAN.md -- Finalize the human evidence, replace retired t-test claims, compile/scan active documents, and close JUDGE-01/02/03

### Phase 40: Multi-Model Training Evidence

**Goal**: Two fresh full local models—genuine Qwen QLoRA and PhoBERT—plus one bounded ordinary-LoRA feasibility probe provide logged evidence for the RTX 5050 adaptation decision without claiming unmeasured full-LoRA accuracy.
**Depends on**: Phase 39 (training starts only after Phase 39's final-snapshot human and report gates close; Phase 42 is not a training prerequisite)
**Requirements**: TRAIN-01, TRAIN-02, TRAIN-03, TRAIN-04, TRAIN-05, TRAIN-06
**Success Criteria** (what must be TRUE):

1. The input contract is frozen to `.planning/phases/39-independent-quality-re-judge/39-DOWNSTREAM-DATA-CONTRACT.json`: 1,658 training rows, 219 validation rows, and 220 held-out test rows, with split SHA-256 values `5fa46382db8fb477ef91ec4ba770bf3f8756df9f98b9950fdf5bc1f6ff402e8b`, `746ae6edb5008a8be8e9ef9d65f89fc44e559f99f28cd8d6a77f203ea5986d3c`, and `6f208fb6cd9399b8934225e6a25efd65d49bbb4f4846360837f6835a2561b6d7`. Phase 40 verifies those identities before work begins and never reads test rows for training, tuning, checkpoint selection, or graph generation.
2. Bounded LoRA and QLoRA probes target 30–50 post-warm-up optimizer steps on the RTX 5050. If a bounded controller terminates earlier, the preserved terminal status and measured window remain the result rather than being rerun to manufacture completion. Both probes record the real outcome, median steady-state step time where measurable, peak allocated/reserved VRAM, throughput, and measured evaluation/checkpoint overhead; local ETAs are labeled extrapolations, and all probe adapters are discarded rather than resumed by any full run.
3. The bounded ordinary-LoRA result remains target-hardware feasibility/resource evidence only: no full LoRA is required, its disposable adapter is not reused, and no LoRA accuracy claim is made. Fresh full Qwen QLoRA and PhoBERT runs execute locally on the RTX 5050 from step zero against the frozen train/validation identities. Colab remains an optional contingency only if validation is unacceptable before the reserved test is opened; any fallback must start fresh, preserve its distinct hardware provenance, and refreeze model identities before Phase 41. Any validation-driven dataset repair changes the data contract, invalidates both prior model identities for the final comparison, and likewise requires fresh training and a new freeze before test access.
4. QLoRA fails closed unless the runtime proves `quantization_mode == "4bit-qlora"`; missing CUDA, `bitsandbytes`, or `BitsAndBytesConfig` must stop the run instead of silently producing ordinary LoRA.
5. A real PhoBERT classification-head baseline is fully fine-tuned on the same frozen training/validation data. QLoRA is not applied to PhoBERT merely to create another quantized run.
6. LoRA-versus-QLoRA conclusions are limited to same-laptop feasibility, step-time, memory, temperature, power, and ETA evidence. Full validation-quality comparison is Qwen QLoRA versus PhoBERT only, and reports results honestly regardless of which model scores higher.
7. Each full run retains an evidence bundle containing dataset hashes, model identifier/revision, exact sanitized command and resolved configuration, hardware plus CUDA/package versions, timestamped raw logs, training/validation curves, peak VRAM, throughput, `trainer_state`, adapter/checkpoint hashes, and final validation metrics. The incomplete LoRA probe retains its explicit terminal status and resource evidence rather than pretending to be a full run. A Git commit identifier is not required in these bundles.
8. Every graph traces mechanically to a retained raw log; no graph is hand-drawn, reconstructed from memory, or based on the Phase 41 test partition.

**Plans**: 6/6 complete
**Wave 1**

- [x] 40-01-PLAN.md

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 40-02-PLAN.md

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 40-03-PLAN.md

**Wave 4** *(blocked on Wave 3 completion)*

- [x] 40-04-PLAN.md

**Wave 5** *(blocked on Wave 4 completion)*

- [x] 40-05-PLAN.md

**Wave 6** *(blocked on Wave 5 completion)*

- [x] 40-06-PLAN.md

### Phase 41: Held-Out Evaluation Discipline

**Goal**: The reserved test split is evaluated exactly once against the finalized local Qwen QLoRA and PhoBERT models, after validation-stage contingency decisions are closed, producing one honest two-model comparison before any optional all-data deployment fit.
**Depends on**: Phase 40 (both full local models and their validation review must be complete; any Colab fallback decision must be resolved before this phase opens the reserved test)
**Requirements**: EVAL-08, EVAL-09
**Success Criteria** (what must be TRUE):

1. The current canonical 220-row test partition (SHA-256 `6f208fb6cd9399b8934225e6a25efd65d49bbb4f4846360837f6835a2561b6d7`) is evaluated against the two finalized full models (Qwen QLoRA and PhoBERT) in one model-evaluation run under identical data-handling conditions, with a timestamped log recording that single Phase 41 evaluation access. Prior human/content exposure during corpus-quality work and thesis drafting is disclosed explicitly; it is not misrepresented as untouchedness and must not influence training, checkpoint selection, thresholds, or the validation-contingency decision. The bounded LoRA probe is ineligible for quality evaluation.
2. A results artifact reports macro and weighted F1 plus per-class precision/recall/F1 for both models plainly, including an explicit, unhedged statement if PhoBERT outscores the deployed QLoRA system on any metric.
3. Held-out results are terminal evidence, not a tuning signal: poor test performance is reported honestly and cannot trigger dataset repair, retraining, threshold selection, or repeated evaluation on the same partition. Any later corrected experiment requires a newly acquired untouched holdout for an unbiased claim. Only after the comparison and selected-checkpoint identities are frozen may an optional deployment model be fitted on all 2,097 rows; it is labeled a post-evaluation all-data fit and receives no claim of an unbiased test score.

**Plans**: 2/2 plans executed

Plans:

- [x] 41-01-PLAN.md -- Production one-shot evaluator, protected claim registry, frozen two-model protocols, clean launcher, and synthetic-only hardening
- [x] 41-02-PLAN.md -- Phase 40 closure gate, explicit authorization, exactly one two-model held-out pass, terminal evidence freeze, and all-data deployment-fit disposition

**Verification:** Passed 12/12 on 2026-08-26 after release-review remediation. The broad suite was intentionally not rerun after CR-01; bounded remediation checks passed 7/7 and independent re-review checks passed 6/6.

### Phase 41.1: Codebase Architecture Overhaul (INSERTED)

**Goal:** The active codebase has a coherent, phase-neutral architecture that is easy to operate and explain: thin stable CLIs, separated data/training/inference/evaluation responsibilities, archived one-off migrations, and an explicit immutable boundary around the exact source and model artifacts that produced Phase 40/41 evidence.
**Requirements**: REFACTOR-01, REFACTOR-02, REFACTOR-03, REFACTOR-04, REFACTOR-05, REFACTOR-06
**Depends on:** Phase 41 (the completed evaluation, verified export, provenance erratum, source closure, and exact four model roots are frozen inputs; this phase must not rerun evaluation or change any metric/model claim)
**Success Criteria** (what must be TRUE):

1. The installed `vnphish analyze|doctor|demo` interface and every currently supported `python -m src.model_adaptation.cli` command/flag remain behavior-compatible, while `src/model_adaptation/cli.py` becomes a thin lazy dispatcher rather than a 1,329-line import hub.
2. Forward-facing code uses phase-neutral `integrity`, `training`, `inference`, and `evaluation` boundaries; reusable data logic is separated from judge/review workflows and one-off corpus migrations. Historical Phase 40/41 paths remain available through documented compatibility shims or a hash-bound legacy archive.
3. The completed Phase 40/41 source tree, verified evidence export, provenance erratum, schema strings, serialized field names, artifact filenames, model identities, and exact D-drive model roots remain immutable and are never presented as having been produced by the refactored code.
4. Characterization, import-boundary, CLI-contract, and dependency-cycle tests prove the migration with synthetic/temp fixtures only. No test, planner, or refactor command accesses or reruns the reserved held-out evaluation.
5. Oversized active modules and dependency cycles are reduced through bounded extraction slices, with explicit size/import budgets and no private-symbol mass rewrite in one step.
6. A report-ready architecture/provenance document and reviewed D-drive storage inventory explain what is active, what is historical, which files are safe cleanup candidates, and why the retained artifacts prove the actual training/evaluation story.

**Plans:** 2/6 plans executed

Plans:
**Wave 1**

- [x] 41.1-01-PLAN.md -- Archive the exact Phase 41 producer source and freeze synthetic compatibility/safety baselines

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 41.1-02-PLAN.md -- Replace the model-adaptation CLI hub with a thin static lazy compatibility router

**Wave 3** *(blocked on Wave 2 completion)*

- [ ] 41.1-03-PLAN.md -- Extract integrity, artifact, settings, runtime-import, and dependency-extra boundaries

**Wave 4** *(blocked on Wave 3 completion)*

- [ ] 41.1-04-PLAN.md -- Introduce phase-neutral modeling services, read-only evidence consumption, and one-way legacy adapters

**Wave 5** *(blocked on Wave 4 completion)*

- [ ] 41.1-05-PLAN.md -- Separate reusable data core, external workflows, and traceable one-off migrations

**Wave 6** *(blocked on Wave 5 completion)*

- [ ] 41.1-06-PLAN.md -- Enforce architecture policy and publish report-ready provenance/storage handoff

### Phase 42: Report Overhaul

**Goal**: The thesis report is rewritten chapter by chapter in the student's own authentic voice, now grounded in the real training evidence, restored recovery story, and repair methodology produced above.
**Depends on**: Phase 41.1 (must describe the coherent post-overhaul active architecture while treating Phase 41's verified export and provenance erratum as the immutable metric authority)

**Gating note:** REPORT-03 requires a real passed-student reference report the user is sourcing externally, and `WRITING_GUARDRAILS_REPORT.md` must be derived from that real artifact. A human should confirm the reference report has actually arrived before this phase's chapter-rewrite work begins — do not start REPORT-03/04 against a placeholder or a guessed guardrails file.

**Phase 41 evidence handoff:** Treat the committed verified export under `data/models/phase41/verified-export/9ac54d58c273ab0a8c2f2b4b61e472a51ca94231a94b6847637ecad6ceee49f7/` and `data/models/phase41/phase41-provenance-erratum.json` as one inseparable reporting authority. The report must carry the erratum's limitation language and must not claim literal untouchedness or global zero filesystem access.

**Requirements**: REPORT-03, REPORT-04, REPORT-05, REPORT-06
**Success Criteria** (what must be TRUE):

1. `WRITING_GUARDRAILS_REPORT.md` exists and is derived from an actual, obtained reference report — not written from assumption.
2. Each rewritten chapter traces back to a student-drafted passage that was only tightened for grammar; a draft-vs-final comparison shows structure and word choice remain the student's own.
3. The SHA-256/manifest-integrity explanation is present in the reworded (not removed) text, matching the previously agreed plain-language explanation.
4. The new training graphs (Phase 40), the PhoBERT/held-out comparison (Phase 40/41), the restored `task_scam` recovery story (Phase 38), and the repair methodology (Phase 38) each appear in a specific, correct chapter — none dumped in an appendix.
5. The report compiles clean with XeLaTeX (zero errors) after the chapter rewrite.

**Plans**: 14 plans

Plans:

- [ ] 42-01-PLAN.md -- Safe anti-fabrication contracts, evidence slots, authorship provenance, and compile guard preparation
- [ ] 42-02-PLAN.md -- Human-gated reference intake, Phase 38/40/41 evidence readiness, and deployment-fit disposition gate
- [ ] 42-03-PLAN.md -- Evidence-bound rewrite of Chapters 1-3 from approved student drafts
- [ ] 42-04-PLAN.md -- Evidence-bound rewrite of Chapters 4-5 with training, comparison, and repair evidence
- [ ] 42-05-PLAN.md -- Evidence-bound rewrite of Chapters 6-8 with limitations and terminal conclusions
- [ ] 42-06-PLAN.md -- Authorship provenance, draft-vs-final audit, evidence verification, and clean pre-final compilation
- [ ] 42-07-PLAN.md -- Blocking initial decision on the exact retained review PDF
- [ ] 42-08-PLAN.md -- Explicit approval fast path or one bounded student-authored revision branch
- [ ] 42-09-PLAN.md -- Conditional Chapters 1-3 rerun with complete declared ownership
- [ ] 42-10-PLAN.md -- Conditional Chapters 4-5 rerun with complete declared ownership
- [ ] 42-11-PLAN.md -- Conditional Chapters 6-8, graph, appendix, and evidence-map rerun with complete ownership
- [ ] 42-12-PLAN.md -- Branch consolidation, provenance refresh, and exact review-PDF recompilation
- [ ] 42-13-PLAN.md -- Carry unchanged approval or obtain exact approval of the revised PDF
- [ ] 42-14-PLAN.md -- Final verification and seal of only the currently approved PDF and unchanged source tree

### Phase 43: Slide Overhaul

**Goal**: The defense deck is rebuilt around the real pipeline stages with real graphs and progressive reveals, coming off LOCKED status for this milestone only.
**Depends on**: Phase 41 (same evidence base as Phase 42; the two phases do not depend on each other and can run in parallel or in either order)
**Phase 41 evidence handoff:** Treat the committed verified export under `data/models/phase41/verified-export/9ac54d58c273ab0a8c2f2b4b61e472a51ca94231a94b6847637ecad6ceee49f7/` and `data/models/phase41/phase41-provenance-erratum.json` as one inseparable reporting authority. Slides must preserve the corrected access limitation and the terminal no-retry/no-tuning policy.
**Requirements**: SLIDE-08, SLIDE-09, SLIDE-10, SLIDE-11
**Success Criteria** (what must be TRUE):

1. The deck's section structure follows the real pipeline stages: get data → train → GGUF → eval.
2. Slides covering the training and evaluation results use progressive `\pause` reveals rather than exposing all content at once.
3. The real ordinary-LoRA probe resource/ETA evidence plus full QLoRA and PhoBERT graphs from Phase 40/41 (not illustrative placeholders) are embedded in the relevant slides.
4. The prior LOCKED deck is archived (dated backup file or branch) and the new deck compiles clean with XeLaTeX, with LOCKED status explicitly and only lifted for this milestone.

**Plans**: 2 plans

Plans:

- [ ] 43-01-PLAN.md -- Synthetic evidence renderer, whole-deck archive/hash tooling, anti-fabrication checks, and stage/pause linter
- [ ] 43-02-PLAN.md -- Evidence-gated archive-before-edit rebuild, graph insertion, and two-pass slide compilation

### Phase 44: Code Cleanup & Defense Prep

**Goal**: A guided, file-by-file walkthrough leaves the codebase with genuine student-written comments — a real defense cheatsheet, not cosmetic cleanup — with the SHA-256/manifest-integrity concept explicitly covered, sequenced immediately before the retake so it reflects the final repaired data and training code.
**Depends on**: Phase 42, Phase 43 (must reflect the final repaired data/training code and the finished report/slide evidence; sequenced last by design, immediately before the retake defense)
**Requirements**: CODE-01, CODE-02, CODE-03, CODE-04
**Success Criteria** (what must be TRUE):

1. Every major module has been walked through file-by-file, with prior AI-style verbose docstrings/comments identified and removed.
2. Each walked-through file has replacement comments written by the student in their own words, reviewable as a genuine per-file cheatsheet.
3. At least one walkthrough entry explicitly covers the SHA-256/manifest-integrity concept, closing the confirmed live-defense gap.
4. This phase's work is the last committed activity in the milestone, landing after Phase 42/43 completion and immediately before the retake defense date (~2026-10-07).

**Plans**: 5 plans

Plans:

- [ ] 44-01-PLAN.md -- Exact upstream closure, defense-time authorization, architecture coverage audit, and walkthrough guard
- [ ] 44-02-PLAN.md -- Blocking student-authored data and two-model training walkthrough
- [ ] 44-03-PLAN.md -- Blocking student-authored integrity, evaluation, and local-runtime walkthrough
- [ ] 44-04-PLAN.md -- Hash-bound final student authorship and defense-readiness attestation
- [ ] 44-05-PLAN.md -- Verbatim cheatsheet, manifest, and post-commit final-order seal

---

## Progress Table

| Phase | Plans Complete | Status | Completed |
| ----- | ---------------- | ------ | --------- |
| 1. Data Foundation and Split Governance | 6/6 | Complete | 2026-05-07 |
| 2. Offline Text Ingestion and Privacy Baseline | 3/3 | Complete | 2026-05-09 |
| 3. Local Model Adaptation and Deployment Paths | 7/7 | Complete | 2026-05-17 closeout complete |
| 4. Threat Detection and Explainable Decisioning | 4/4 | Complete | 2026-05-25 |
| 5. Recall-Priority Evaluation and Release Gates | 4/4 | Complete | 2026-05-25 |
| 6. Local Demo UI for Non-Technical Verification | 1/1 | Complete | 2026-05-25 |
| 7. Proposal Closeout and Quantitative Validation | 2/2 | Complete | 2026-05-26 |
| 7a. task_scam Recall Recovery | 3/3 | Complete | 2026-05-28 |
| 7b. App Response Optimization | 2/2 | Complete (07b-02 skipped) | 2026-05-29 |
| 8. Thesis Structure and Evidence Map | 1/1 | Complete | 2026-05-29 |
| 9. Core Thesis Chapter Drafting | 3/3 | Complete | 2026-05-29 |
| 10. Final Thesis Review and Submission Polish | 1/1 | Complete | 2026-06-03 |
| 11. Beamer Defense Presentation (Metropolis prototype) | 3/3 | Superseded by Phase 12 | 2026-06-03 |
| 12. CambridgeUS Presentation Revamp | 3/3 | Complete | 2026-06-05 |
| 13. Content Gap Closure — Dataset & QLoRA | 2/2 | Complete | 2026-06-08 |
| 14. CSS + HTML Scaffolding | 1/1 | Complete | 2026-06-08 |
| 15. i18n.js + demo.py Static Route | 1/1 | Complete | 2026-06-09 |
| 16. demo.js Core Fetch Lifecycle | 1/1 | Complete | 2026-06-09 |
| 17. Polish + Edge Cases | 1/1 | Complete | 2026-06-09 |
| 18. Mobile + Accessibility Validation | 1/1 | Complete | 2026-06-09 |
| 19. Slide Content Fixes | TBD | Complete | 2026-06-09 |
| 20. Binary Evaluation Re-run + Eval Slide Updates | TBD | Complete | 2026-06-09 |
| 21. Thesis Report Revisions | TBD | Complete | 2026-06-09 |
| 22. Cover Page, Certification Letter, and Front Matter | 1/1 | Complete | 2026-06-15 |
| 23. Document Restructure and Evaluation Tables | 1/1 | Complete | 2026-06-15 |
| 24. Appendices, Slides Sync, and Final Compile | 1/1 | Complete | 2026-06-15 |
| 28. Baseline Readiness and Zero-Code Diagnostics | 1/1 | Complete    | 2026-07-02 |
| 29. Environment Parity and Offline Verification | 4/4 | Complete    | 2026-07-05 |
| 30. Latency Diagnosis and Targeted Fix | 2/2 | Complete    | 2026-07-06 |
| 31. UI Quirks, Edge Cases and Regression Re-check | 3/3 | Complete    | 2026-07-08 |
| 32. Fallback Recording and Full Dry Rehearsal | 1/1 | Complete    | 2026-07-09 |
| 33. Emergency 10-Minute Slide Compression | 1/1 | Complete | 2026-07-13 |
| 34. Speaking Script & Q&A Preparation | 1/1 | Complete | 2026-07-14 |
| 35. Problem Framing & Architecture Rationale | 0/TBD | Not started | - |
| 36. Dataset Construction & Labeling Methodology | 0/TBD | Not started | - |
| 37. Consistency Audit & Citation Verification | 0/TBD | Not started | - |
| 38. Corpus Repair and Split Governance | 2/2 | Complete    | 2026-08-08 |
| 39. Independent Quality Re-Judge | 7/7 | Complete   | 2026-08-24 |
| 40. Multi-Model Training Evidence | 6/6 | Complete    | 2026-08-26 |
| 41. Held-Out Evaluation Discipline | 2/2 | Complete | 2026-08-26 |
| 41.1 Codebase Architecture Overhaul | 2/6 | In Progress|  |
| 42. Report Overhaul | 0/TBD | Not started | - |
| 43. Slide Overhaul | 0/TBD | Not started | - |
| 44. Code Cleanup and Defense Prep | 0/TBD | Not started | - |

## Coverage Validation

- tracked requirements total: 160 (126 prior milestones + 34 v7.0)
- tracked requirements mapped: 160
- orphaned tracked requirements: 0
- duplicate mappings: 0

Coverage map:

- DATA-01 -> Phase 1
- DATA-02 -> Phase 1
- DATA-03 -> Phase 1
- ING-01 -> Phase 2
- ING-02 -> Phase 2
- RUN-01 -> Phase 2
- MOD-01 -> Phase 3
- RUN-02 -> Phase 3
- RUN-03 -> Phase 3
- DET-01 -> Phase 4
- DET-02 -> Phase 4
- XAI-01 -> Phase 4
- XAI-02 -> Phase 4
- EVAL-01 -> Phase 5
- EVAL-02 -> Phase 5
- EVAL-03 -> Phase 5
- UI-01 -> Phase 6
- UI-02 -> Phase 6
- CLS-01 -> Phase 7
- CLS-02 -> Phase 7
- CLS-03 -> Phase 7
- REP-01 -> Phase 8
- REP-02 -> Phase 9
- REP-03 -> Phase 9
- REP-04 -> Phase 10
- REP-05 -> Phase 10
- PRES-01 -> Phase 11
- PRES-02 -> Phase 11
- PRES-03 -> Phase 11
- PRES-04 -> Phase 11
- PRES-05 -> Phase 11
- PRES-06 -> Phase 11
- PRES-07 -> Phase 11
- PRES-08 -> Phase 11
- PRES-09 -> Phase 11
- PRES-10 -> Phase 11
- PRES-11 -> Phase 11
- PRES-12 -> Phase 11
- PRES-13 -> Phase 11
- GAP-01 -> Phase 13
- GAP-02 -> Phase 13
- GAP-03 -> Phase 13
- GAP-04 -> Phase 13
- GAP-05 -> Phase 13
- GAP-06 -> Phase 13
- GAP-07 -> Phase 13
- GAP-08 -> Phase 13
- INFRA-01 -> Phase 14
- I18N-01 -> Phase 15
- I18N-02 -> Phase 15
- INFRA-02 -> Phase 15
- CHAT-01 -> Phase 16
- CHAT-02 -> Phase 16
- CHAT-03 -> Phase 16
- CHAT-04 -> Phase 16
- INPUT-01 -> Phase 16
- INPUT-02 -> Phase 16
- INPUT-03 -> Phase 16
- INPUT-04 -> Phase 16
- POLISH-01 -> Phase 17
- POLISH-02 -> Phase 17
- POLISH-03 -> Phase 17
- SLIDE-01 -> Phase 19
- SLIDE-02 -> Phase 19
- SLIDE-03 -> Phase 19
- SLIDE-04 -> Phase 19
- SLIDE-05 -> Phase 19
- SLIDE-06 -> Phase 19
- SLIDE-07 -> Phase 19
- EVAL-04 -> Phase 20
- EVAL-05 -> Phase 20
- REPORT-01 -> Phase 21
- REPORT-02 -> Phase 21
- COVER-01 -> Phase 22
- CERT-01 -> Phase 22
- FRONT-01 -> Phase 22
- FRONT-02 -> Phase 22
- FRONT-03 -> Phase 22
- STRUCT-01 -> Phase 23
- STRUCT-02 -> Phase 23
- STRUCT-03 -> Phase 23
- EVAL-06 -> Phase 23
- EVAL-07 -> Phase 23
- APPEND-01 -> Phase 24
- SYNC-01 -> Phase 24
- DIAG-01 -> Phase 28
- DIAG-02 -> Phase 28
- DIAG-03 -> Phase 28
- GOLD-01 -> Phase 28
- GOLD-02 -> Phase 28
- ENV-01 -> Phase 29
- ENV-02 -> Phase 29
- ENV-03 -> Phase 29
- ENV-04 -> Phase 29
- ENV-05 -> Phase 29
- PERF-01 -> Phase 30
- PERF-02 -> Phase 30
- PERF-03 -> Phase 30
- UIQ-01 -> Phase 31
- UIQ-02 -> Phase 31
- UIQ-03 -> Phase 31
- UIQ-04 -> Phase 31
- FB-01 -> Phase 32
- FB-02 -> Phase 32
- FB-03 -> Phase 32
- FB-04 -> Phase 32
- TIME-01 -> Phase 33
- TIME-02 -> Phase 33
- TIME-03 -> Phase 33
- TIME-04 -> Phase 33
- TIME-05 -> Phase 33
- GDEMO-01 -> Phase 33
- GDEMO-02 -> Phase 33
- SCRIPT-01 -> Phase 34
- SCRIPT-02 -> Phase 34
- SCRIPT-03 -> Phase 34
- QA-01 -> Phase 34
- QA-02 -> Phase 34
- QA-03 -> Phase 34
- QA-04 -> Phase 34
- FRAME-01 -> Phase 35
- ARCH-01 -> Phase 35
- ARCH-02 -> Phase 35
- LABEL-01 -> Phase 36
- LABEL-02 -> Phase 36
- LABEL-03 -> Phase 36
- LABEL-04 -> Phase 36
- AUDIT-01 -> Phase 37
- AUDIT-02 -> Phase 37
- AUDIT-03 -> Phase 37
- CITE-01 -> Phase 37
- CITE-02 -> Phase 37
- VOICE-01 -> Phase 37
- DATA-04 -> Phase 38
- DATA-05 -> Phase 38
- DATA-06 -> Phase 38
- DATA-07 -> Phase 38
- DATA-08 -> Phase 38
- JUDGE-01 -> Phase 39
- JUDGE-02 -> Phase 39
- JUDGE-03 -> Phase 39
- TRAIN-01 -> Phase 40
- TRAIN-02 -> Phase 40
- TRAIN-03 -> Phase 40
- TRAIN-04 -> Phase 40
- TRAIN-05 -> Phase 40
- TRAIN-06 -> Phase 40
- EVAL-08 -> Phase 41
- EVAL-09 -> Phase 41
- REFACTOR-01 -> Phase 41.1
- REFACTOR-02 -> Phase 41.1
- REFACTOR-03 -> Phase 41.1
- REFACTOR-04 -> Phase 41.1
- REFACTOR-05 -> Phase 41.1
- REFACTOR-06 -> Phase 41.1
- REPORT-03 -> Phase 42
- REPORT-04 -> Phase 42
- REPORT-05 -> Phase 42
- REPORT-06 -> Phase 42
- SLIDE-08 -> Phase 43
- SLIDE-09 -> Phase 43
- SLIDE-10 -> Phase 43
- SLIDE-11 -> Phase 43
- CODE-01 -> Phase 44
- CODE-02 -> Phase 44
- CODE-03 -> Phase 44
- CODE-04 -> Phase 44
