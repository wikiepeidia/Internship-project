# Feature Landscape: Chapter-to-Section Mapping (v2.2 Department Template)

**Domain:** LaTeX thesis restructuring — 6 numbered chapters → 5 Roman numeral department sections
**Researched:** 2026-06-15
**Scope anchor:** Content already written; this is a structural remapping exercise, not new research.
**Source documents read:** `chapters/01_introduction.tex`, `02_related_work_and_background.tex`,
`03_methodology_and_system_design.tex`, `04_implementation.tex`,
`05_evaluation_and_discussion.tex`, `06_conclusion_and_future_work.tex`;
department template from `documents/reports/example/2026_required_format_thesis.md`.

---

## Chapter-to-Section Mapping Table

| Existing Chapter | Content summary | Target Section | Disposition |
|---|---|---|---|
| Ch 1 — Introduction | Background & motivation, problem statement, objectives & scope (bullet list), report organization | I/ Introduction (partially) + II/ Objectives | Split: narrative goes to I/, objectives bullet list becomes II/ |
| Ch 2 — Related Work and Background | Vietnamese phishing context, local inference as privacy control (with OpenAI/Samsung incidents + cloud_vs_local figure), explainability rationale, open-weight model trade-offs, evaluation priorities | I/ Introduction (majority) | Move: literature review and scientific background are exactly what the department template wants in I/ |
| Ch 3 — Methodology and System Design | Data construction + split governance, offline runtime baseline, model selection + QLoRA adaptation (with equations, tables), explainable decisioning, design principles | III/ Materials and Methods | Direct map: methodology + reproducible system description = department III/ |
| Ch 4 — Implementation | Codebase organization (tree), data pipeline impl, runtime contracts (with TikZ figure), backend implementations, model adaptation workflow, packaging + example output | III/ Materials and Methods (majority) + IV/ Results (example output) | Partial split: structural/method content → III/; the worked example analysis output → IV/ as first results illustration |
| Ch 5 — Evaluation and Discussion | Data quality checks, candidate selection record, end-to-end verification, expanded-holdout results (tables, recall barchart, confusion matrix), interpretation, error analysis, limits | IV/ Results and Discussion | Direct map: student's own results + critical analysis = department IV/ |
| Ch 6 — Conclusion and Future Work | Main takeaways, evaluation meaning, limitations, future work (3 directions) | V/ Conclusion & Perspective | Direct map: achievements + perspectives = department V/ |

---

## Per-Section Notes

### I/ Introduction (target: 2–3 pages)

**Sources to merge:**

- Ch 1, Section 1 "Background and Motivation" — 1 paragraph on design constraints and safety question.
- Ch 1, Section 2 "Problem Statement" — 2 paragraphs on cloud privacy risk and Vietnamese phishing gap.
- Ch 2 (entire chapter) — Vietnamese phishing context, local inference privacy rationale with documented cloud incidents, explainability as safety control, open-weight model trade-offs, evaluation priorities.

**What to exclude from Ch 1:**

- "Objectives and Scope" bullet list → moves to II/ instead.
- "Report Organization" paragraph → becomes obsolete once chapter numbering is replaced by Roman numeral sections; drop or rewrite as a 1-sentence structural note at end of I/.

**Ch 2 fits naturally here** because the department template defines I/ as "global context, literature review, main questions and objectives including the presentation of the problem with the scientific background." Ch 2 is exactly that.

**Page-length estimate:**

- Ch 1 narrative (excluding objectives bullets and report organization): ~0.5 pages.
- Ch 2 full content (5 sections): ~2.5–3 pages as currently written (heavy, citation-dense prose).
- Combined target: 3–3.5 pages. This is slightly over the 2–3 page guideline.
- **Trimming needed:** Ch 2 Section 4 "Open-Weight Local Models" is the longest section and overlaps with III/ Materials. Its second paragraph (Google Gemini Nano deployment rationale) can move to III/ as a justification note rather than background. This trims approximately 0.3–0.4 pages from I/.
- After trim: ~2.8–3 pages. Borderline acceptable; tighter editing of Ch 2 prose could bring it to 2.5 pages cleanly.

**Cross-references:** The `cloud_vs_local_dataflow` figure lives in Ch 2 and should stay here in I/ as-is.

---

### II/ Objectives (target: 2–3 sentences, standalone section)

**Source:** Ch 1, Section 3 "Objectives and Scope" — the bullet list of 4 objectives.

**Transform needed:** The department format specifies "submit your goal and summarize the strategy in 2-3 concise sentences." The existing content is a 4-bullet list. It must be collapsed into 2–3 prose sentences.

**Existing bullets:**
1. Build reproducible Vietnamese phishing dataset pipeline.
2. Deliver text-only local runtime (privacy by default).
3. Adapt local model via LoRA/QLoRA + deploy via GGUF and accelerated paths.
4. Return structured explainability outputs (risk tier, labels, cues, recommendations).

**Recommended prose form (draft):**
> This project aims to build and evaluate a localized, offline-capable explainable AI pipeline for detecting Vietnamese financial phishing messages while preserving user privacy by default. The strategy combines a reproducible synthetic dataset pipeline, parameter-efficient QLoRA adaptation of a 4B open-weight model, GGUF quantization for consumer hardware deployment, and a structured explainability layer returning risk tiers, threat labels, grounded cues, and safe next steps.

This is 2 sentences, uses all 4 bullets, stays within the format requirement. The Ch 1 sentence "The thesis documents completed work…with task-scam recall reaching 0.871 on 62 held-out examples" can optionally become sentence 3 (adds result preview). New writing required: **1 paragraph rewrite** of existing bullet list — minimal effort, all content is already present.

---

### III/ Materials and Methods

**Sources to merge (in order):**

1. Ch 3, Section 2 "Data Construction and Split Governance" — corpus assembly, synthetic generation pipeline, quality judge, split governance. This is the "materials" part.
2. Ch 3, Section 3 "Offline Text Runtime Baseline" — runtime design, privacy constraint.
3. Ch 3, Section 4 "Local Model Selection and Deployment Paths" — pilot evaluation, QLoRA config (with equation and qlora_config table), GGUF export. This is the "methods" part.
4. Ch 3, Section 5 "Explainable Threat Decisioning" — decision layer design rules.
5. Ch 3, Section 6 "Design Principles" — reusable local-first principles.
6. Ch 4, Sections 1–5 (Codebase Organization, Data Pipeline Impl, Runtime Contracts, Backend Implementations, Model Adaptation Workflow) — implementation detail that is part of the reproducible method description.

**What stays out of III/:**

- Ch 4, Section 6 "Operator Surface and Packaging" subsection "Example Analysis Output" (the worked Vietnamese SMS example) → moves to IV/ as the opening illustration of results.
- Ch 4, Section 6 packaging prose (pyproject.toml dependency groups, `vnphish demo` command) → keep in III/ as it is part of reproducibility.
- The pilot comparison table (`tables/pilot_comparison`) lives in Ch 3 and stays in III/.
- The dataset statistics table (`tables/dataset_statistics`) lives in Ch 3 and stays in III/.
- The runtime contract TikZ figure (in Ch 4) stays in III/ as method documentation.
- The system_overview figure (currently in Ch 3 preamble) stays in III/.

**Department requirement check:** "include all information necessary for a third person to reproduce your experiments (in detail but condensed)." Ch 3 + Ch 4 together already satisfy this. No new method text is needed.

**Section ordering concern:** Ch 3 (high-level methodology) followed by Ch 4 (low-level codebase details) currently reads as a natural progression. In III/, the merge should maintain this order: data → runtime → model selection → adaptation → deployment → codebase detail. The `Development Structure` opening of Ch 3 can serve as III/'s introductory paragraph with the milestone_summary table removed or moved to front matter.

---

### IV/ Results and Discussion

**Sources to merge:**

1. Ch 4, Subsection "Example Analysis Output" — the worked SMS analysis (Vietnamese input → risk tier, labels, cues, next steps). Department template notes "Never start your result section with a Fig or Table only — an introduction paragraph should be added." The existing prose before the example output block serves as that introduction.
2. Ch 5, Section 1 "Data Quality and Candidate Selection" — earliest quantitative evidence, quality-judge scores.
3. Ch 5, Section 2 "End-to-End Verification" — verification pass, 5 acceptance checks.
4. Ch 5, Section 3 "Expanded-Holdout Results" — accuracy 0.957, macro F1 0.955, per-class table, recall barchart figure, confusion matrix table.
5. Ch 5, Section 4 "Interpretation of the Final Result" — critical analysis, explanation quality cautions. This is the "Discussion" sub-section.
6. Ch 5, Section 5 "Error Analysis" — root cause of 11 misclassifications (bank-naming boundary). Also Discussion.
7. Ch 5, Section 6 "Limits of the Current Evidence" — limitation acknowledgement. Belongs in Discussion.

**Department requirement check:**

- "Description of the student's own research, procedures and results. Interpretation of results; conclusions and review of results comparison with other research; critical assessment." — Ch 5 + the worked example satisfy all of these.
- "Critical analysis and discuss results in regards to data already available in the scientific literature." — Ch 5 Section 4 references `lim2025explicate` as comparison; Ch 5 Section 6 contextualizes against production-scale studies. Adequate coverage exists, though it is thin (2 comparison references). No additional literature comparison is strictly required to satisfy the format, but adding one sentence connecting recall results to the EXPLICATE benchmark numbers would strengthen the Discussion sub-section.

**Subsection structure for IV/:**

```
IV/ Results and Discussion
  1. Results
     1.1  System Demo Output (worked example from Ch 4 §6)
     1.2  Data Quality Evidence (Ch 5 §1 first half)
     1.3  Model Selection Record (Ch 5 §1 second half)
     1.4  End-to-End Verification (Ch 5 §2)
     1.5  Expanded Holdout Evaluation (Ch 5 §3 — main quantitative results)
  2. Discussion
     2.1  Interpretation of Results (Ch 5 §4)
     2.2  Error Analysis (Ch 5 §5)
     2.3  Limitations (Ch 5 §6)
```

---

### V/ Conclusion & Perspective

**Source:** Ch 6 entire chapter — direct map.

- "Main Takeaways" → Conclusion paragraph (achievements).
- "What the Final Evaluation Means" → expands on achievements with the quantitative anchor.
- "Limitations" → brief limitation acknowledgement before perspectives.
- "Future Work" (3 directions) → Perspective paragraph.

**Department requirement:** "The conclusion recapitulates the main achievements of your work and the main perspectives it opens." Ch 6 does exactly this. No new content needed.

**Minor edit needed:** Ch 6 references "Chapter 5" in the phrase "the error analysis in Chapter 5 shows…". This internal cross-reference must be updated to "Section IV" or "the error analysis above" in the restructured document. This is a find-and-replace edit, not new writing.

---

## Content Gaps Requiring New Text

| Gap | Location | Estimated Size | Priority |
|---|---|---|---|
| II/ Objectives prose | Replace 4-bullet list with 2–3 sentences | 1 paragraph (2–3 sentences) | Required — format non-negotiable |
| Ch 1 "Report Organization" replacement | Existing paragraph names chapters; replace with section-aware orientation sentence | 1 sentence | Required — factual update |
| Ch 2 → I/ transition | Ch 2 currently opens as a standalone chapter; needs a 1–2 sentence bridge connecting the introduction narrative to the literature review | 1–2 sentences | Low effort, high readability value |
| IV/ intro paragraph before example output | Department template requires introduction paragraph before first table/figure in results | 1 short paragraph (already partially present as prose before the example block in Ch 4 §6) | Already exists — confirm it is sufficient as-is |
| Ch 5 §4 literature comparison expansion | One sentence connecting holdout recall to published benchmarks (e.g., EXPLICATE baseline numbers) to strengthen Discussion sub-section | 1 sentence | Optional — format compliant without it |
| "Section IV" cross-reference fix in Ch 6 | Replace "Chapter 5" with section-aware reference | 1 find-and-replace | Required — avoids broken references |
| Chapter → Section header renaming throughout | All `\chapter{...}` → `\section*{...}` or equivalent Roman numeral headings | Mechanical edit throughout | Required — automated with sed/find-replace |

**Total new prose required: 1 paragraph + 2–3 sentences.** All other changes are restructuring, reordering, and header renaming of existing content.

---

## Merge/Split Strategy (Minimizing New Writing)

**Rule:** Move entire sections as atomic units wherever possible. Only split at subsection boundaries.

```
KEEP INTACT (no restructuring inside the section):
  Ch 2 §1 Vietnamese Phishing Context   → I/ body
  Ch 2 §2 Local Inference as Privacy    → I/ body
  Ch 2 §3 Explainability                → I/ body
  Ch 2 §4 Open-Weight Models (partial)  → I/ body (trim Gemini para → III/)
  Ch 2 §5 Evaluation Priorities         → I/ body
  Ch 3 §2 Data Construction             → III/ §1
  Ch 3 §3 Runtime Baseline              → III/ §2
  Ch 3 §4 Model Selection + QLoRA       → III/ §3
  Ch 3 §5 Explainable Decisioning       → III/ §4
  Ch 3 §6 Design Principles             → III/ §5
  Ch 4 §1 Codebase Organization         → III/ §6
  Ch 4 §2 Data Pipeline Impl            → III/ §7
  Ch 4 §3 Runtime Contracts             → III/ §8
  Ch 4 §4 Backend Implementations       → III/ §9
  Ch 4 §5 Model Adaptation Workflow     → III/ §10
  Ch 4 §6 Packaging (prose only)        → III/ §11
  Ch 5 §1–§6 (all)                      → IV/ (split into Results + Discussion)
  Ch 6 §1–§4 (all)                      → V/

SPLIT (extract subsection or paragraph):
  Ch 1 §1–§2 narrative                  → I/ opening
  Ch 1 §3 objectives bullets            → II/ (rewrite as prose)
  Ch 1 §4 report organization           → Drop or replace with 1 sentence
  Ch 4 §6 subsection "Example Analysis" → IV/ Results §1 (extract from III/)
  Ch 2 §4 second paragraph (Gemini)     → III/ justification note (extract from I/)

NEW TEXT:
  II/ Objectives prose                   → 2–3 sentences (write fresh from bullets)
  Ch 2 → Ch 1 bridge sentence            → 1–2 sentences
  Ch 6 cross-reference fix               → 1 find-and-replace
```

---

## Section Length Estimates (vs Department Guidance)

| Section | Department Guidance | Estimated length from merged content | Status |
|---|---|---|---|
| I/ Introduction | 2–3 pages | ~2.5–3 pages (Ch 1 narrative + Ch 2) | Borderline — trim Ch 2 §4 second paragraph |
| II/ Objectives | 2–3 sentences | Currently 4 bullets → needs rewrite | Gap — requires 1 paragraph rewrite |
| III/ Materials and Methods | Reproducible, publication-style | ~5–7 pages (Ch 3 + Ch 4) | Comfortable — department format has no page limit here |
| IV/ Results and Discussion | Student's own results + discussion vs literature | ~4–5 pages (Ch 5 + worked example) | Comfortable |
| V/ Conclusion & Perspective | Achievements + perspectives | ~1.5–2 pages (Ch 6) | Comfortable |

---

## Confidence Assessment

| Area | Confidence | Basis |
|---|---|---|
| Chapter content inventory | HIGH | Read all 6 chapter .tex files directly |
| Department section requirements | HIGH | Read official 2026_required_format_thesis.md directly |
| Page-length estimates | MEDIUM | Based on prose density in .tex files; actual compiled length may vary by ±0.5 pages depending on figure placement and table sizes |
| "Objectives prose" rewrite adequacy | HIGH | Department spec is unambiguous (2–3 sentences); existing bullet content provides all the raw material |
| Literature comparison coverage in Discussion | MEDIUM | Ch 5 references EXPLICATE and one other; sufficient for format compliance, thin for academic strength |
