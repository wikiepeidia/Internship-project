# Roadmap: Localized Explainable AI (XAI) Engine for Vietnamese Financial Phishing and Threat Detection

**Created:** 2026-03-18
**Granularity:** standard
**v1 scope guardrails:** text-only inputs, offline-first privacy, recall-priority safety gates

**Milestone note:** v2 Thesis Report is a documentation and planning milestone for judge-facing thesis preparation. It does not change the completion status of v1 product Phases 4 and 5.

## Phases

- [x] **Phase 1: Data Foundation and Split Governance** - Build reproducible Vietnamese threat datasets from NCSC seed sources with contamination controls.
- [x] **Phase 2: Offline Text Ingestion and Privacy Baseline** - Deliver text-only message intake and default local/offline inference behavior.
- [x] **Phase 3: Local Model Adaptation and Deployment Paths** - Fine-tune the base model with LoRA and provide laptop baseline plus optional prosumer acceleration paths.
- [ ] **Phase 4: Threat Detection and Explainable Decisioning** - Deliver risk-tier classification, threat-type labeling, and evidence-bound recommendations.
- [ ] **Phase 5: Recall-Priority Evaluation and Release Gates** - Enforce measurable quality, recall safety thresholds, and explanation-quality acceptance gates.
- [ ] **Phase 6: Thesis Architecture and Evidence Baseline** - Lock the thesis structure, artifact inventory, and completed-vs-planned framing for judge-facing writing.
- [ ] **Phase 7: Planned Detection and Evaluation Chapters** - Convert pending Phase 4 and Phase 5 work into thesis-grade specification chapters without overstating implementation.
- [ ] **Phase 8: Writing Schedule, Risks, and Submission Readiness** - Define the dated writing path, risk register, and final checklist for thesis handoff.

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
**Success Criteria** (what must be TRUE):

1. Team can execute a LoRA fine-tuning pipeline on the project dataset and produce versioned adapted artifacts for the selected 4B baseline winner and runner-up.
2. User can run a GGUF quantized model path on consumer laptop CPU/iGPU baseline hardware.
3. User can optionally switch to an accelerated path on prosumer GPU hardware with consistent output schema.
4. Runtime selection is explicit and does not require switching to cloud-default inference.
**Plans**: 4 plans

Plans:

- [x] 03-01-PLAN.md -- Candidate registry, pilot scorecard, and local model-artifact manifests
- [x] 03-02-PLAN.md -- QLoRA training pipeline and adapter artifact builds for winner plus runner-up
- [x] 03-03-PLAN.md -- GGUF conversion, CPU baseline backend, and explicit runtime profile selection
- [x] 03-04-PLAN.md -- Accelerated local backend, profile-aware doctor checks, and local-model docs

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
**Plans**: TBD

### Phase 5: Recall-Priority Evaluation and Release Gates

**Goal**: Release decisions are controlled by safety-focused evaluation gates, with recall prioritized for high-harm scam classes.
**Depends on**: Phase 4
**Requirements**: EVAL-01, EVAL-02, EVAL-03
**Success Criteria** (what must be TRUE):

1. Evaluation reports include overall F1 and per-class metrics on held-out offline data.
2. Go/no-go gating enforces recall-priority thresholds to minimize false negatives on high-harm classes.
3. Explanation outputs pass a defined quality rubric for correctness, relevance, and actionability.
4. A release candidate cannot be marked ready if recall or explanation-quality thresholds fail.
**Plans**: TBD

## Milestone Boundary Note

Within v2 Thesis Report, product Phases 4 and 5 remain pending implementation work. They should be represented in thesis material as proposed or planned chapters, not as implemented or validated results.

### Phase 6: Thesis Architecture and Evidence Baseline

**Goal**: Lock the thesis structure and evidence map so the report clearly distinguishes completed implementation from planned future work.
**Depends on**: Phase 3
**Requirements**: TR-01, TR-02
**Success Criteria** (what must be TRUE):

1. The thesis has a chapter outline that covers background, project framing, implemented evidence, planned detection/evaluation chapters, risks, and conclusions.
2. An artifact inventory maps datasets, manifests, runtime outputs, model assets, docs, and supervisor reports to the right report sections.
3. The report framing explicitly marks Phases 1-3 as completed evidence and Phases 4-5 as planned future work.
4. Each core chapter can be traced either to concrete repo artifacts or to an explicitly planned specification section.
**Plans**: 3 plans

Plans:

- [ ] 06-01-PLAN.md -- Chapter architecture and thesis outline
- [ ] 06-02-PLAN.md -- Artifact inventory and provenance matrix
- [ ] 06-03-PLAN.md -- Completed-vs-planned evidence framing

### Phase 7: Planned Detection and Evaluation Chapters

**Goal**: Produce thesis-grade specification chapters for the unbuilt detection and evaluation work without overstating implementation status.
**Depends on**: Phase 6
**Requirements**: TR-03, TR-04, TR-06
**Success Criteria** (what must be TRUE):

1. The report contains a Phase 4 chapter that specifies risk tiers, threat labels, explanation behavior, and user guidance as planned design.
2. The report contains a Phase 5 chapter that specifies evaluation methodology, recall-priority thresholds, explanation rubric, and release gates as planned validation design.
3. Deferred scope and future work are explicit and do not read as implemented results.
4. A reader can understand the intended end-to-end product path while still seeing that DET/XAI/EVAL work is not yet implemented.
**Plans**: 3 plans

Plans:

- [ ] 07-01-PLAN.md -- Phase 4 threat-detection specification chapter
- [ ] 07-02-PLAN.md -- Phase 5 evaluation and release-gate chapter
- [ ] 07-03-PLAN.md -- Future-work and deferred-scope section

### Phase 8: Writing Schedule, Risks, and Submission Readiness

**Goal**: Turn the thesis package into a supervised, dated writing effort with explicit risks, limitations, and a final submission-readiness gate.
**Depends on**: Phase 7
**Requirements**: TR-05, TR-07, TR-08
**Success Criteria** (what must be TRUE):

1. The thesis includes a risk register covering evidence gaps, pending Phases 4-5, evaluation limitations, and writing/review risks.
2. A dated writing and review schedule covers 2026-05-18 to 2026-05-31 by thesis part or chapter.
3. A final checklist verifies chapter completeness, provenance traceability, figure/table readiness, and judge-facing submission packaging.
4. The milestone ends with a clear readiness decision for supervisor and judge handoff.
**Plans**: 3 plans

Plans:

- [ ] 08-01-PLAN.md -- Risk register and limitations section
- [ ] 08-02-PLAN.md -- 2026-05-18 to 2026-05-31 writing and review schedule
- [ ] 08-03-PLAN.md -- Final review and submission checklist

## Progress Table

| Phase | Plans Complete | Status | Completed |
| ----- | ---------------- | ------ | --------- |
| 1. Data Foundation and Split Governance | 6/6 | Complete | 2026-05-07 |
| 2. Offline Text Ingestion and Privacy Baseline | 3/3 | Complete | 2026-05-09 |
| 3. Local Model Adaptation and Deployment Paths | 4/4 | Complete | 2026-05-11 |
| 4. Threat Detection and Explainable Decisioning | 0/TBD | Not started | - |
| 5. Recall-Priority Evaluation and Release Gates | 0/TBD | Not started | - |
| 6. Thesis Architecture and Evidence Baseline | 0/3 | Not started | - |
| 7. Planned Detection and Evaluation Chapters | 0/3 | Not started | - |
| 8. Writing Schedule, Risks, and Submission Readiness | 0/3 | Not started | - |

## Coverage Validation

- product v1 requirements total: 16
- product v1 requirements mapped: 16
- thesis-report milestone requirements total: 8
- thesis-report milestone requirements mapped: 8
- orphaned active milestone requirements: 0
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
- TR-01 -> Phase 6
- TR-02 -> Phase 6
- TR-03 -> Phase 7
- TR-04 -> Phase 7
- TR-05 -> Phase 8
- TR-06 -> Phase 7
- TR-07 -> Phase 8
- TR-08 -> Phase 8
