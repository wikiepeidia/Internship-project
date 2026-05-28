<!-- markdownlint-disable MD022 MD034 MD055 MD056 MD060 -->

# Phase 8: Thesis Structure and Evidence Map - Research

**Researched:** 2026-05-26  
**Domain:** undergraduate thesis structure, evidence packaging, and citation shortlist  
**Confidence:** MEDIUM

<user_constraints>

## User Constraints

- The thesis is for graduation judging, not an internal progress report. [CITED: .planning/PROJECT.md] [CITED: user request]
- The writing tone must feel natural for a bachelor undergraduate student. [CITED: .planning/PROJECT.md] [CITED: .planning/STATE.md] [CITED: user request]
- The thesis must avoid AI-like wording. [CITED: .planning/PROJECT.md] [CITED: .planning/STATE.md] [CITED: user request]
- The thesis itself must not expose GSD workflow terms, roadmap language, or internal planning-file names. [CITED: .planning/PROJECT.md] [CITED: .planning/STATE.md] [CITED: user request]
- Research for this phase should include internet search and citation-oriented source finding where possible. [CITED: user request]

</user_constraints>

## Project Constraints (from copilot-instructions.md)

- GSD workflows should not be applied unless they are explicitly requested. [CITED: .github/copilot-instructions.md]
- GSD requests should route through the matching GSD skill or agent. [CITED: .github/copilot-instructions.md]

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|---|---|---|
| REP-01 | Thesis has a finalized chapter outline and evidence map that links each main section to real repo artifacts, experiments, or documents. | This file provides one fixed chapter structure, one chapter-by-chapter evidence map, one citation shortlist, one writing guardrail section, and one one-week writing sequence. [CITED: .planning/REQUIREMENTS.md] [CITED: .planning/ROADMAP.md] |

</phase_requirements>

## Summary

Phase 8 should lock the existing LaTeX manuscript into one exact six-chapter thesis structure, plus front matter, references, and appendices, before any full drafting starts. That shape matches the live `main.tex` file, the current milestone goal, and the short graduation-report window better than opening a new seven-chapter structure this late in the writing cycle. [CITED: documents/reports/latex/main.tex] [CITED: .planning/PROJECT.md] [CITED: .planning/ROADMAP.md] [CITED: documents/reports/supervisor/report-08_2026-05-13_to_2026-05-14.md] [CITED: documents/reports/supervisor/report-09_2026-05-15_to_2026-05-17.md]

The strongest thesis-ready evidence already exists in-repo for project scope, dataset lineage, local runtime behavior, pilot selection, held-out evaluation, acceptance testing, and security review. The weakest area is Chapter 5 model-training proof, because some of the best supporting artifacts still live off-repo under `D:\PROJEct\AI MODELS`; that chapter should therefore rely first on tracked manifests, tracked docs, and carefully copied summary numbers rather than vague recollection. [CITED: .planning/STATE.md] [CITED: data/manifests/phase3-large-pilot-2026-05-14.json] [CITED: .planning/phases/07-proposal-closeout-and-quantitative-validation/07-CONTEXT.md]

External research worked well enough to produce a usable citation shortlist, but not every target page could be fully extracted in-session. Reviewed sources are listed separately from follow-up targets so Phase 9 drafting can cite real URLs without pretending every link was fully verified in this session. [CITED: https://tinnhiemmang.vn/canh-bao-mao-danh-ngan-hang-huong-dan-nguoi-dung-xac-thuc-sinh-trac-hoc] [CITED: https://www.group-ib.com/media-center/press-releases/massive-phishing-campaign-vietnam-banks/] [CITED: https://arxiv.org/abs/2503.20796] [CITED: https://arxiv.org/html/2303.12942] [CITED: https://www.nist.gov/privacy-framework] [CITED: https://graduate.oregonstate.edu/current-students/thesis-guide/formatting-thesis-or-dissertation]

**Primary recommendation:** Keep the existing six-chapter LaTeX outline, lock every chapter against named repo artifacts now, and treat Phase 9 as straight drafting rather than outline discovery. [CITED: documents/reports/latex/main.tex] [CITED: .planning/ROADMAP.md] [CITED: .planning/REQUIREMENTS.md]

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale | Source |
|---|---|---|---|---|
| Graduation-facing narrative | Thesis draft | Supervisor reports | The report must read as a judged academic document, not as an execution log. | [CITED: .planning/PROJECT.md] [CITED: documents/reports/supervisor/report-08_2026-05-13_to_2026-05-14.md] |
| Problem context and related work | External citations | Proposal and project docs | Background claims need public sources, while project scope still comes from the approved topic and repo constraints. | [CITED: documents/internship-proposal.md] [CITED: .planning/PROJECT.md] [CITED: https://tinnhiemmang.vn/canh-bao-mao-danh-ngan-hang-huong-dan-nguoi-dung-xac-thuc-sinh-trac-hoc] [CITED: https://arxiv.org/html/2303.12942] |
| Implementation claims | Repo artifacts | User docs and tests | System behavior is best supported by tracked docs, manifests, and test surfaces, not by memory. | [CITED: readme.md] [CITED: docs/user/USER_GUIDE.md] [CITED: docs/user/LOCAL_MODELS.md] [CITED: .planning/STATE.md] |
| Quantitative claims | Release-eval artifacts | UAT and security summaries | The final school-facing result is controlled by the repaired-holdout evaluation package and its audits. | [CITED: data/manifests/phase5-release-eval-phase5-recovered-balanced-val.json] [CITED: .planning/phases/05-recall-priority-evaluation-and-release-gates/05-release-eval-phase5-recovered-balanced-val.md] [CITED: .planning/phases/07-proposal-closeout-and-quantitative-validation/07-UAT.md] [CITED: .planning/phases/07-proposal-closeout-and-quantitative-validation/07-SECURITY.md] |
| Tone and honesty guardrails | This research note | Final result artifacts | Tone and honesty need to be fixed before drafting so the result chapter does not drift into overclaiming. | [CITED: .planning/PROJECT.md] [CITED: .planning/STATE.md] [CITED: user request] |
| Week plan for drafting | Phase 8 research output | Existing evidence inventory | The remaining writing window is short, so sequencing needs to follow evidence readiness rather than chapter preference. | [CITED: .planning/ROADMAP.md] [CITED: documents/reports/supervisor/report-08_2026-05-13_to_2026-05-14.md] [CITED: user request] |

## Recommended Thesis Structure

### Front Matter

- Title page, abstract, acknowledgements, table of contents, list of figures, list of tables, references, and appendices are all normal parts of a standard thesis package. [CITED: https://graduate.oregonstate.edu/current-students/thesis-guide/formatting-thesis-or-dissertation]
- Use external university guidance only as structure support unless the supervisor or school provides a stricter local template. [ASSUMED]

### Main Chapters

| Chapter | Thesis-Facing Title | What This Chapter Should Claim | Core Subsections | Source |
|---|---|---|---|---|
| 1 | Introduction | The project addresses Vietnamese financial phishing text with a local, explainable, text-only system and a bounded undergraduate scope. | problem context; motivation; objectives; scope; thesis contributions; chapter roadmap | [CITED: documents/internship-proposal.md] [CITED: .planning/PROJECT.md] [CITED: .planning/REQUIREMENTS.md] [CITED: documents/reports/latex/chapters/01_introduction.tex] |
| 2 | Related Work and Background | The thesis is grounded in public phishing or scam context, privacy reasoning, and explainable AI literature rather than only self-description. | Vietnamese scam patterns; phishing tactics; local or offline privacy rationale; explainable AI background; related work | [CITED: https://tinnhiemmang.vn/canh-bao-mao-danh-ngan-hang-huong-dan-nguoi-dung-xac-thuc-sinh-trac-hoc] [CITED: https://www.group-ib.com/media-center/press-releases/massive-phishing-campaign-vietnam-banks/] [CITED: https://www.nist.gov/privacy-framework] [CITED: https://arxiv.org/html/2303.12942] [CITED: https://arxiv.org/abs/2503.20796] [CITED: documents/reports/latex/chapters/02_related_work_and_background.tex] |
| 3 | Methodology and System Design | The methodology chapter should explain the reproducible dataset workflow together with the end-to-end local system design and privacy boundary. | seed collection; synthetic generation; judging and split governance; overall pipeline; privacy boundary; explainable decision design | [CITED: readme.md] [CITED: data/manifests/manifest-phase1-recovered-balanced-claude-v2.json] [CITED: data/processed/recovered-balanced-quality-stats-claude-v2.json] [CITED: .planning/phases/01-data-foundation-and-split-governance/01-06-SUMMARY.md] [CITED: documents/reports/latex/chapters/03_methodology_and_system_design.tex] |
| 4 | Implementation | The implementation chapter should describe the realized software subsystems, runtime operator flow, model adaptation path, deployment profiles, and demo integration. | CLI and contracts; runtime behavior; model selection and deployment path; GGUF and accelerated profiles; demo UI linkage | [CITED: readme.md] [CITED: docs/user/USER_GUIDE.md] [CITED: docs/user/LOCAL_MODELS.md] [CITED: data/manifests/phase3-large-pilot-2026-05-14.json] [CITED: .planning/phases/06-local-demo-ui-for-non-technical-verification/06-01-SUMMARY.md] [CITED: documents/reports/latex/chapters/04_implementation.tex] |
| 5 | Evaluation and Discussion | The final result chapter must report the repaired holdout, per-label metrics, explanation review findings, and the honest release-readiness outcome. | evaluation setup; repaired-holdout lineage; per-class metrics; explanation-review summary; final verdict; discussion | [CITED: data/manifests/phase5-release-eval-phase5-recovered-balanced-val.json] [CITED: .planning/phases/05-recall-priority-evaluation-and-release-gates/05-release-eval-phase5-recovered-balanced-val.md] [CITED: .planning/phases/05-recall-priority-evaluation-and-release-gates/05-VALIDATION.md] [CITED: .planning/phases/07-proposal-closeout-and-quantitative-validation/07-UAT.md] [CITED: documents/reports/latex/chapters/05_evaluation_and_discussion.tex] |
| 6 | Conclusion and Future Work | The thesis should close by stating clearly what was achieved, what remained weak, and what next work is justified by the evidence. | limitations; conclusion; realistic future work; closing contribution statement | [CITED: .planning/PROJECT.md] [CITED: .planning/STATE.md] [CITED: data/manifests/phase5-release-eval-phase5-recovered-balanced-val.json] [CITED: .planning/phases/07-proposal-closeout-and-quantitative-validation/07-SECURITY.md] [CITED: documents/reports/latex/chapters/06_conclusion_and_future_work.tex] |

### Back Matter and Appendix Plan

- Keep the appendix for evidence that is too detailed for the main story: command excerpts, manifest excerpts, split-count tables, per-label metrics, interface screenshot, and any copied training-summary numbers that are needed for transparency. [ASSUMED]
- Do not paste large raw-text review records from the explanation review pack into the thesis body. That file is better treated as internal supporting evidence than reader-facing narrative. [CITED: .planning/phases/07-proposal-closeout-and-quantitative-validation/07-SECURITY.md] [CITED: .planning/phases/05-recall-priority-evaluation-and-release-gates/05-VALIDATION.md]

## Evidence Mapping

| Chapter | Strongest Repo Evidence | Useful Commands or Reproducibility Anchors | Candidate Figure or Table | Readiness | Cautions |
|---|---|---|---|---|---|
| 1. Introduction | `documents/internship-proposal.md`; `documents/reports/supervisor/report-08_2026-05-13_to_2026-05-14.md`; `documents/reports/latex/chapters/01_introduction.tex`; `docs/user/USER_GUIDE.md` | `vnphish analyze`; `vnphish demo` as concrete examples of the user-facing goal [CITED: docs/user/USER_GUIDE.md] | Table: objectives and scope boundaries | High [CITED: documents/internship-proposal.md] | Do not describe the thesis as a status update, a phase recap, or a planning exercise. [CITED: .planning/PROJECT.md] |
| 2. Related Work and Background | Public source shortlist below; `readme.md`; `documents/reports/latex/chapters/02_related_work_and_background.tex` | None required; this chapter is citation-heavy rather than command-heavy. [ASSUMED] | Table: threat categories and cited sources | Medium [CITED: https://tinnhiemmang.vn/canh-bao-mao-danh-ngan-hang-huong-dan-nguoi-dung-xac-thuc-sinh-trac-hoc] | Keep background claims tied to verified external citations, not to project-planning files. [ASSUMED] |
| 3. Methodology and System Design | `data/raw/seeds-2026-04-24.jsonl`; `data/synthetic/recovered-balanced.jsonl`; `data/processed/recovered-balanced-quality-stats-claude-v2.json`; `data/manifests/manifest-phase1-recovered-balanced-claude-v2.json`; `.planning/phases/01-data-foundation-and-split-governance/01-06-SUMMARY.md`; `documents/reports/latex/chapters/03_methodology_and_system_design.tex` | `python -m src.data_pipeline.cli --seed-input data/raw/seeds-2026-04-24.jsonl --target-count 3000 --version-tag proposal-closeout --resume` [CITED: .planning/phases/07-proposal-closeout-and-quantitative-validation/07-01-PLAN.md] | Figure: data pipeline and system overview; Table: split counts and manifest hashes | High [CITED: readme.md] [CITED: data/manifests/manifest-phase1-recovered-balanced-claude-v2.json] | Distinguish the 956-record retained Phase 1 judged lineage from the later 3,000-row closeout corpus so counts do not get mixed. [CITED: .planning/phases/01-data-foundation-and-split-governance/01-06-SUMMARY.md] [CITED: .planning/STATE.md] |
| 4. Implementation | `readme.md`; `docs/user/USER_GUIDE.md`; `docs/user/LOCAL_MODELS.md`; `data/manifests/phase3-large-pilot-2026-05-14.json`; `.planning/phases/06-local-demo-ui-for-non-technical-verification/06-01-SUMMARY.md`; `documents/reports/latex/chapters/04_implementation.tex` | `vnphish doctor`; `vnphish analyze`; `vnphish demo`; `python -m pytest tests/runtime -q` [CITED: docs/user/USER_GUIDE.md] [CITED: documents/reports/supervisor/report-09_2026-05-15_to_2026-05-17.md] | Figure: end-to-end local flow; Screenshot: demo UI; Table: runtime profiles and model path | High [CITED: docs/user/USER_GUIDE.md] [CITED: data/manifests/phase3-large-pilot-2026-05-14.json] | Explain directly that the executed route reconciled the earlier 8B idea into a 4B-primary local path after real pilot evidence. [CITED: documents/internship-proposal.md] [CITED: documents/reports/supervisor/report-09_2026-05-15_to_2026-05-17.md] |
| 5. Evaluation and Discussion | `data/manifests/phase5-release-eval-phase5-recovered-balanced-val.json`; `.planning/phases/05-recall-priority-evaluation-and-release-gates/05-release-eval-phase5-recovered-balanced-val.md`; `.planning/phases/05-recall-priority-evaluation-and-release-gates/05-evaluation-snapshot.json`; `.planning/phases/07-proposal-closeout-and-quantitative-validation/07-UAT.md`; `.planning/phases/07-proposal-closeout-and-quantitative-validation/07-SECURITY.md`; `documents/reports/latex/chapters/05_evaluation_and_discussion.tex` | `python -m src.model_adaptation.cli evaluate-release-split --split-path data/splits/recovered-balanced/val.jsonl ...`; `python -m src.model_adaptation.cli release-eval ...` [CITED: .planning/phases/07-proposal-closeout-and-quantitative-validation/07-CONTEXT.md] | Table: final per-label metrics; Bar chart: recall by class; Table: explanation-review flags | High [CITED: data/manifests/phase5-release-eval-phase5-recovered-balanced-val.json] | Never report weighted F1 alone; always pair it with macro F1, per-label recall, and the final verdict. [CITED: data/manifests/phase5-release-eval-phase5-recovered-balanced-val.json] |
| 6. Conclusion and Future Work | `data/manifests/phase5-release-eval-phase5-recovered-balanced-val.json`; `.planning/phases/07-proposal-closeout-and-quantitative-validation/07-SECURITY.md`; `documents/reports/latex/chapters/06_conclusion_and_future_work.tex` | None required; this chapter should synthesize, not introduce new procedure. [ASSUMED] | Table: achieved vs not achieved; short future-work list | High [CITED: data/manifests/phase5-release-eval-phase5-recovered-balanced-val.json] | Future work should stay close to actual gaps like `task_scam` recall and stronger evaluation, not turn into a broad new product roadmap. [CITED: .planning/STATE.md] [CITED: user request] |

## Evidence to Extract Before Phase 9 Drafting

- Build one clean dataset table from `data/manifests/manifest-phase1-recovered-balanced-claude-v2.json`, `data/processed/recovered-balanced-quality-stats-claude-v2.json`, and `.planning/STATE.md`. [CITED: data/manifests/manifest-phase1-recovered-balanced-claude-v2.json] [CITED: data/processed/recovered-balanced-quality-stats-claude-v2.json] [CITED: .planning/STATE.md]
- Copy one pilot-comparison table directly from `data/manifests/phase3-large-pilot-2026-05-14.json` so Chapter 5 uses exact numbers. [CITED: data/manifests/phase3-large-pilot-2026-05-14.json]
- Capture one demo screenshot after `vnphish demo` or from the local demo assets for Chapter 4. [CITED: .planning/phases/06-local-demo-ui-for-non-technical-verification/06-01-SUMMARY.md] [CITED: docs/user/USER_GUIDE.md]
- Copy one final metrics table directly from `data/manifests/phase5-release-eval-phase5-recovered-balanced-val.json`. [CITED: data/manifests/phase5-release-eval-phase5-recovered-balanced-val.json]
- Decide whether any off-repo training summary numbers from `D:\PROJEct\AI MODELS` will be quoted in Chapter 5; if yes, pull them into an appendix-friendly markdown table first. [CITED: .planning/STATE.md] [ASSUMED]

## Citation and Source-Finding

### Reviewed Sources Usable Now

| Topic | Source URL | Type | What It Can Support | Confidence |
|---|---|---|---|---|
| Vietnamese phishing and financial-scam context | https://tinnhiemmang.vn/canh-bao-mao-danh-ngan-hang-huong-dan-nguoi-dung-xac-thuc-sinh-trac-hoc | National cybersecurity portal article | Bank impersonation tied to biometric-verification policy, fake calls or messages, Zalo or Facebook contact, fake links, fake apps, and the advice to verify via official channels. [CITED: https://tinnhiemmang.vn/canh-bao-mao-danh-ngan-hang-huong-dan-nguoi-dung-xac-thuc-sinh-trac-hoc] | High |
| Vietnamese banking-phishing campaign patterns | https://www.group-ib.com/media-center/press-releases/massive-phishing-campaign-vietnam-banks/ | Vendor threat-intelligence report | Major-bank impersonation, OTP hijacking, SMS or Telegram or Facebook lures, short-lived domains, and campaign scale details that fit the thesis problem context. [CITED: https://www.group-ib.com/media-center/press-releases/massive-phishing-campaign-vietnam-banks/] | Medium |
| XAI background for cybersecurity | https://arxiv.org/html/2303.12942 | Academic survey | Why explainability matters for trust, privacy, false positives or false negatives, and the accuracy-versus-interpretability tradeoff in cybersecurity. [CITED: https://arxiv.org/html/2303.12942] | Medium |
| Explainable phishing-detection example | https://arxiv.org/abs/2503.20796 | Academic preprint | A recent phishing-detection design that combines classifier outputs with LIME and SHAP plus user-facing explanation layers. [CITED: https://arxiv.org/abs/2503.20796] | Medium |
| Privacy and local-processing rationale | https://www.nist.gov/privacy-framework | Official framework page | Privacy-risk framing, protection of individuals' privacy, and the value of managing privacy risk rather than ignoring it. [CITED: https://www.nist.gov/privacy-framework] | High |
| Generic thesis structure or formatting guidance | https://graduate.oregonstate.edu/current-students/thesis-guide/formatting-thesis-or-dissertation | Official university thesis guide | Standard thesis order, chapter expectations, references, figures or tables, and document hygiene for a judged submission. [CITED: https://graduate.oregonstate.edu/current-students/thesis-guide/formatting-thesis-or-dissertation] | Medium |

### High-Probability Targets Not Fully Reviewed In-Session

| Topic | URL | Why It Still Looks Useful | In-Session Status |
|---|---|---|---|
| Official Vietnamese government guidance on scam websites | https://baochinhphu.vn/bo-cong-an-huong-dan-cach-nhan-dien-website-lua-dao-102250124133511758.htm | Government-facing language may strengthen the introduction or public-risk framing. [ASSUMED] | Blocked by page restrictions during this session. |
| Additional thesis chapter-writing guidance | https://www.monash.edu/student-academic-success/excel-at-writing/how-to-write/thesis-chapter/reporting-and-discussion-thesis-chapters | Could help with writing the results or discussion chapter more naturally. [ASSUMED] | HTTP 403 in-session. |
| Broader Vietnam scam report | https://saferinternetlab.org/wp-content/uploads/2025/05/Online-Fraud-and-Scams-in-Vietnam.pdf | Could provide higher-level scam landscape context beyond single incident posts. [ASSUMED] | PDF extraction failed in-session. |

### Source Use Recommendation

- Use the reviewed URLs above immediately for Phase 9 drafting. [CITED: https://tinnhiemmang.vn/canh-bao-mao-danh-ngan-hang-huong-dan-nguoi-dung-xac-thuc-sinh-trac-hoc] [CITED: https://www.group-ib.com/media-center/press-releases/massive-phishing-campaign-vietnam-banks/] [CITED: https://arxiv.org/abs/2503.20796] [CITED: https://arxiv.org/html/2303.12942] [CITED: https://www.nist.gov/privacy-framework] [CITED: https://graduate.oregonstate.edu/current-students/thesis-guide/formatting-thesis-or-dissertation]
- Treat the blocked or partially extracted targets as follow-up validation leads, not as already-reviewed evidence. [ASSUMED]
- Do not invent publication details or page-specific claims from the blocked targets unless they are opened and checked manually later. [CITED: user request]

## Writing Guardrails

### Claims to Avoid

- Do not say the system is deployment-ready or production-safe for general users. The final release-readiness artifact is still `BLOCK`. [CITED: data/manifests/phase5-release-eval-phase5-recovered-balanced-val.json] [CITED: .planning/phases/05-recall-priority-evaluation-and-release-gates/05-release-eval-phase5-recovered-balanced-val.md]
- Do not write that the proposal target was fully achieved without qualification. The repaired-holdout package shows `weighted_f1=0.8618`, `macro_f1=0.7431`, and a failed `task_scam` recall floor. [CITED: data/manifests/phase5-release-eval-phase5-recovered-balanced-val.json]
- Do not collapse weighted F1 into an undefined phrase like "the final F1 score was above 0.85". That wording would hide the weaker macro result and the blocked verdict. [CITED: data/manifests/phase5-release-eval-phase5-recovered-balanced-val.json]
- Do not imply the dataset is purely real-world user data. The project combines seed scraping, synthetic generation, judging, and repaired or recovered lineage work. [CITED: documents/internship-proposal.md] [CITED: readme.md] [CITED: .planning/phases/01-data-foundation-and-split-governance/01-06-SUMMARY.md] [CITED: .planning/phases/07-proposal-closeout-and-quantitative-validation/07-CONTEXT.md]
- Do not say local or offline use eliminates privacy risk. A safer phrasing is that the default analysis path reduces the need to send suspicious messages to cloud services. [CITED: docs/user/USER_GUIDE.md] [CITED: .planning/PROJECT.md] [CITED: https://www.nist.gov/privacy-framework]
- Do not mention `Phase 5`, `Phase 7`, `ROADMAP`, `STATE.md`, or other planning filenames inside thesis prose. Convert them to academic descriptions such as "final held-out evaluation report" or "security audit summary". [CITED: .planning/PROJECT.md] [CITED: user request]

### Honest Wording for the Final `BLOCK` Verdict

- Recommended long form: "In the final held-out evaluation, the system performed strongly on bank impersonation and Zalo or social-engineering cases, but it did not meet the required recall threshold for the task scam class. For that reason, the final release-readiness verdict remained `BLOCK`, and this limitation is reported explicitly rather than hidden." [CITED: data/manifests/phase5-release-eval-phase5-recovered-balanced-val.json] [CITED: .planning/phases/05-recall-priority-evaluation-and-release-gates/05-release-eval-phase5-recovered-balanced-val.md]
- Recommended short form: "The final closeout evaluation remained `BLOCK` because `task_scam` recall was `0.44`, below the project floor of `0.90`, even though weighted F1 reached `0.8618`." [CITED: data/manifests/phase5-release-eval-phase5-recovered-balanced-val.json]
- If the committee dislikes all-caps verdict labels in prose, define it once as "not release-ready under the project's own safety gate" and keep the literal `BLOCK` label in a table, footnote, or appendix. [ASSUMED]

### Repo-to-Thesis Terminology Map

| Internal Term or File Style | Thesis-Facing Replacement | Source |
|---|---|---|
| `05-release-eval-phase5-recovered-balanced-val.md` | final held-out evaluation report | [CITED: .planning/phases/05-recall-priority-evaluation-and-release-gates/05-release-eval-phase5-recovered-balanced-val.md] |
| `07-UAT.md` | acceptance test summary | [CITED: .planning/phases/07-proposal-closeout-and-quantitative-validation/07-UAT.md] |
| `07-SECURITY.md` | security audit summary | [CITED: .planning/phases/07-proposal-closeout-and-quantitative-validation/07-SECURITY.md] |
| `manifest-phase1-recovered-balanced-claude-v2.json` | dataset lineage manifest | [CITED: data/manifests/manifest-phase1-recovered-balanced-claude-v2.json] |
| `phase3-large-pilot-2026-05-14.json` | pilot model comparison manifest | [CITED: data/manifests/phase3-large-pilot-2026-05-14.json] |
| `baseline-winner` | selected 4B baseline model | [CITED: data/manifests/phase3-large-pilot-2026-05-14.json] |
| `gguf-laptop` | quantized local laptop inference build | [CITED: docs/user/LOCAL_MODELS.md] |

### Tone Guidance

- Prefer short declarative sentences and measured verbs such as "shows", "indicates", "suggests", and "did not meet". [ASSUMED]
- Prefer neutral thesis phrasing such as "This thesis presents..." or "The system was evaluated on..." if no school-specific preference is known. [ASSUMED]
- Use exact numbers when they exist and simpler wording when they do not. [CITED: data/manifests/phase5-release-eval-phase5-recovered-balanced-val.json]
- Avoid inflated phrases such as "state-of-the-art", "revolutionary", "highly robust", "clearly proves", or "in today's rapidly evolving landscape" unless a citation and metric truly justify them. [ASSUMED]
- Keep strengths and limitations at the same level of specificity so the report sounds honest rather than promotional. [CITED: .planning/PROJECT.md] [CITED: .planning/STATE.md]

## One-Week Writing Sequence

| Date | Focus | Concrete Output | Milestone Effect | Source |
|---|---|---|---|---|
| 2026-05-26 | Lock six-chapter structure and evidence map | Finalize this research note; freeze the current `main.tex` chapter order; prepare one evidence row per chapter | Completes Phase 8 core objective | [CITED: documents/reports/latex/main.tex] [CITED: .planning/ROADMAP.md] [CITED: user request] |
| 2026-05-27 | Draft Chapter 1 and citation-ready Chapter 2 notes | Write introduction, objectives, scope, and expand background notes with reviewed URLs inserted into the bibliography target list | Starts Phase 9 on the easiest evidence-ready chapters | [CITED: documents/internship-proposal.md] [CITED: https://tinnhiemmang.vn/canh-bao-mao-danh-ngan-hang-huong-dan-nguoi-dung-xac-thuc-sinh-trac-hoc] |
| 2026-05-28 | Draft Chapter 3 | Write methodology and system-design sections for data construction, governance, and privacy-safe pipeline flow | Keeps drafting tied to hard artifacts, not memory | [CITED: data/manifests/manifest-phase1-recovered-balanced-claude-v2.json] [CITED: data/processed/recovered-balanced-quality-stats-claude-v2.json] |
| 2026-05-29 | Draft Chapter 4 | Write implementation details for runtime, model adaptation, deployment profiles, and demo linkage | Covers software realization before the final results chapter | [CITED: docs/user/USER_GUIDE.md] [CITED: data/manifests/phase3-large-pilot-2026-05-14.json] |
| 2026-05-30 | Draft Chapter 5 | Write evaluation setup, metrics table, explanation-review summary, and honest plain-prose discussion of the final blocked result | Completes the most decision-sensitive results chapter | [CITED: data/manifests/phase5-release-eval-phase5-recovered-balanced-val.json] [CITED: .planning/phases/05-recall-priority-evaluation-and-release-gates/05-release-eval-phase5-recovered-balanced-val.md] |
| 2026-05-31 | Draft Chapter 6 and normalize terminology | Write conclusion, limitations, and realistic future work; normalize terminology and collect remaining appendix items | Bridges Phase 9 drafting into Phase 10 review and formatting | [CITED: .planning/STATE.md] [CITED: user request] |
| 2026-06-01 | Final chapter sweep and reference polish | Add in-text citations, enable bibliography rendering, and run one full consistency pass on the thesis | Starts Phase 10 review with the full six-chapter draft in place | [CITED: documents/reports/latex/main.tex] [CITED: user request] |

## Risks

| Risk | Why It Matters | Mitigation | Source |
|---|---|---|---|
| Dataset-count confusion between retained Phase 1 evidence and Phase 7 closeout evidence | The thesis can accidentally merge the 956-record retained judged lineage with the 3,000-row closeout corpus and create a false dataset story. | State clearly which artifact supports training lineage and which supports final closeout evaluation. | [CITED: .planning/phases/01-data-foundation-and-split-governance/01-06-SUMMARY.md] [CITED: .planning/STATE.md] |
| Weighted F1 can be misread as full success | `weighted_f1=0.8618` looks strong in isolation, but the final verdict still remained `BLOCK`. | Always report weighted F1, macro F1, per-label recall, and the verdict together. | [CITED: data/manifests/phase5-release-eval-phase5-recovered-balanced-val.json] |
| Chapter 5 evidence is partly off-repo | Some of the most concrete training outputs and GGUF artifacts live outside the repo. | Pull only exact copied summary numbers into appendix-friendly notes and keep the thesis wording modest if those notes are not collected. | [CITED: .planning/STATE.md] [ASSUMED] |
| External citation coverage is still uneven | Vietnam-specific prevalence and scam-trend claims can become weak if the thesis relies on only one advisory post. | Use the reviewed URLs now and manually inspect one or two blocked targets later if stronger context is needed. | [CITED: https://tinnhiemmang.vn/canh-bao-mao-danh-ngan-hang-huong-dan-nguoi-dung-xac-thuc-sinh-trac-hoc] [CITED: https://www.group-ib.com/media-center/press-releases/massive-phishing-campaign-vietnam-banks/] |
| No school-specific formatting guide was found in the repo | Chapter order and front matter may still need adjustment if the supervisor or department gives a template later. | Treat the external university guides as generic structure help, not binding local policy. | [CITED: https://graduate.oregonstate.edu/current-students/thesis-guide/formatting-thesis-or-dissertation] [ASSUMED] |
| Internal-review artifacts can leak the wrong tone | Planning summaries and review packs sound procedural and can make the thesis read like a workflow log. | Use those files only as evidence backstops, then rewrite in normal academic prose. | [CITED: .planning/PROJECT.md] [CITED: user request] |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|---|---|---|
| A1 | No stricter USTH-specific thesis template is currently available in the repo. | Recommended Thesis Structure | A later supervisor template could still change formatting details. |
| A2 | The current six-chapter LaTeX structure is the working manuscript architecture for this milestone. | Recommended Thesis Structure | A later mandatory local template could require structural adjustment. |
| A3 | Off-repo training summaries are optional appendix support, not mandatory Chapter 5 evidence. | Evidence Mapping / Risks | Chapter 5 stays focused on tracked manifests and saved evaluation artifacts. |

## Resolved Phase 8 Decisions

1. **Working thesis template rule**
   - Decision: use the current six-chapter `documents/reports/latex/main.tex` structure as the working manuscript template for this milestone. [CITED: documents/reports/latex/main.tex]
   - Boundary: if a later supervisor or USTH template appears, it should override formatting expectations first rather than reopen the evidence map immediately. [ASSUMED]

2. **Chapter 5 evidence-depth rule**
   - Decision: Chapter 5 must be supportable from tracked manifests, saved evaluation artifacts, and reader-facing repo docs. [CITED: data/manifests/phase3-large-pilot-2026-05-14.json] [CITED: data/manifests/phase5-release-eval-phase5-recovered-balanced-val.json] [CITED: docs/user/LOCAL_MODELS.md]
   - Boundary: off-repo training numbers are optional appendix-only support if they are copied into a local note later; they are not required to complete the thesis draft. [CITED: .planning/STATE.md] [ASSUMED]

3. **Final verdict wording rule**
   - Decision: thesis paragraphs should use plain prose such as "the system was not release-ready under the project's own safety gate" while the literal `BLOCK` label is reserved for tables, appendix notes, or guardrail guidance. [CITED: data/manifests/phase5-release-eval-phase5-recovered-balanced-val.json] [ASSUMED]
   - Reason: this keeps the report honest without making the body text sound like an internal workflow log. [CITED: user request] [CITED: .planning/PROJECT.md]

## Sources

### Repo Sources

- `.planning/PROJECT.md`
- `.planning/REQUIREMENTS.md`
- `.planning/ROADMAP.md`
- `.planning/STATE.md`
- `documents/internship-proposal.md`
- `documents/reports/supervisor/report-08_2026-05-13_to_2026-05-14.md`
- `documents/reports/supervisor/report-09_2026-05-15_to_2026-05-17.md`
- `readme.md`
- `docs/user/USER_GUIDE.md`
- `docs/user/LOCAL_MODELS.md`
- `data/manifests/manifest-phase1-recovered-balanced-claude-v2.json`
- `data/manifests/phase3-large-pilot-2026-05-14.json`
- `data/manifests/phase5-release-eval-phase5-recovered-balanced-val.json`
- `data/processed/recovered-balanced-quality-stats-claude-v2.json`
- `.planning/phases/01-data-foundation-and-split-governance/01-06-SUMMARY.md`
- `.planning/phases/05-recall-priority-evaluation-and-release-gates/05-release-eval-phase5-recovered-balanced-val.md`
- `.planning/phases/05-recall-priority-evaluation-and-release-gates/05-VALIDATION.md`
- `.planning/phases/06-local-demo-ui-for-non-technical-verification/06-01-SUMMARY.md`
- `.planning/phases/07-proposal-closeout-and-quantitative-validation/07-CONTEXT.md`
- `.planning/phases/07-proposal-closeout-and-quantitative-validation/07-UAT.md`
- `.planning/phases/07-proposal-closeout-and-quantitative-validation/07-SECURITY.md`

### Web Sources Reviewed In-Session

- https://tinnhiemmang.vn/canh-bao-mao-danh-ngan-hang-huong-dan-nguoi-dung-xac-thuc-sinh-trac-hoc
- https://www.group-ib.com/media-center/press-releases/massive-phishing-campaign-vietnam-banks/
- https://arxiv.org/abs/2503.20796
- https://arxiv.org/html/2303.12942
- https://www.nist.gov/privacy-framework
- https://graduate.oregonstate.edu/current-students/thesis-guide/formatting-thesis-or-dissertation

### Web Targets For Follow-Up Validation

- https://baochinhphu.vn/bo-cong-an-huong-dan-cach-nhan-dien-website-lua-dao-102250124133511758.htm
- https://www.monash.edu/student-academic-success/excel-at-writing/how-to-write/thesis-chapter/reporting-and-discussion-thesis-chapters
- https://saferinternetlab.org/wp-content/uploads/2025/05/Online-Fraud-and-Scams-in-Vietnam.pdf

## Metadata

**Confidence breakdown:**

- Thesis structure: HIGH - the repo objective, roadmap, supervisor notes, and generic thesis guidance all point to the same standard-report shape. [CITED: .planning/PROJECT.md] [CITED: .planning/ROADMAP.md] [CITED: documents/reports/supervisor/report-08_2026-05-13_to_2026-05-14.md] [CITED: https://graduate.oregonstate.edu/current-students/thesis-guide/formatting-thesis-or-dissertation]
- Evidence mapping: HIGH - the main claims are anchored to existing manifests, docs, summaries, and evaluation artifacts. [CITED: data/manifests/manifest-phase1-recovered-balanced-claude-v2.json] [CITED: data/manifests/phase3-large-pilot-2026-05-14.json] [CITED: data/manifests/phase5-release-eval-phase5-recovered-balanced-val.json]
- External citation shortlist: MEDIUM - several useful URLs were reviewed, but some strong Vietnam-specific targets were only partially accessible in-session. [CITED: https://tinnhiemmang.vn/canh-bao-mao-danh-ngan-hang-huong-dan-nguoi-dung-xac-thuc-sinh-trac-hoc] [CITED: https://www.group-ib.com/media-center/press-releases/massive-phishing-campaign-vietnam-banks/] [CITED: https://arxiv.org/abs/2503.20796] [CITED: https://arxiv.org/html/2303.12942] [CITED: https://www.nist.gov/privacy-framework]

**Research date:** 2026-05-26  
**Valid until:** 2026-06-02 for drafting use, or until a supervisor-specific template overrides the structure. [ASSUMED]

<!-- markdownlint-enable MD022 MD034 MD055 MD056 MD060 -->