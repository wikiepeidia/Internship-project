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
- [ ] **Phase 7a: task_scam Recall Recovery** - Audit existing task_scam data, strengthen generation prompts, generate targeted samples, retrain on Colab H100, fix evaluation gate bug, and re-run holdout evaluation until task_scam recall ≥0.80.
- [ ] **Phase 7b: App Response Optimization** - Profile and fix local demo response latency by tuning llama.cpp threading, batch, and context-window parameters.
- [x] **Phase 8: Thesis Structure and Evidence Map** - Lock the graduation-thesis outline, section claims, and supporting repo evidence.
- [x] **Phase 9: Core Thesis Chapter Drafting** - Draft the main technical thesis chapters from the implemented system and final evidence base.
- [ ] **Phase 10: Final Thesis Review and Submission Polish** - Finish tone, references, formatting, and judging-ready submission polish.

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
- [ ] 07a-03-PLAN.md -- Operator workflow: generation, split rebuild, retrain, convert, evaluate, and PASS verdict (Wave 2)

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

- [ ] 10-01-PLAN.md -- Final thesis review, references, formatting, and submission package

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
| 7a. task_scam Recall Recovery | 0/3 | Planned | — |
| 7b. App Response Optimization | 1/2 | In Progress | — |
| 8. Thesis Structure and Evidence Map | 1/1 | Complete | 2026-05-29 |
| 9. Core Thesis Chapter Drafting | 3/3 | Complete | 2026-05-29 |
| 10. Final Thesis Review and Submission Polish | 0/1 | Planned | — |

## Coverage Validation

- tracked requirements total: 26
- tracked requirements mapped: 26
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
