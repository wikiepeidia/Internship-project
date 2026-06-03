# Phase 9: Core Thesis Chapter Drafting — Research

**Researched:** 2026-05-29
**Domain:** LaTeX thesis writing, evidence-grounded academic prose, undergraduate CS report conventions
**Confidence:** HIGH

---

## Summary

Phase 9 drafts the main technical chapters of the graduation thesis. The six-chapter LaTeX manuscript already exists at `documents/reports/latex/` and every chapter has meaningful scaffold prose. Phase 9 is NOT greenfield writing — it is expansion and evidence-grounding of existing scaffolds, plus three urgent corrections.

The most critical planning input is an evidence mismatch that must be fixed before any prose expansion. The current `evaluation_snapshot.tex` table and `05_evaluation_and_discussion.tex` chapter both report the OLD evaluation results (task_scam recall=0.44, support=18, 210 rows, BLOCK verdict). The final correct evaluation — from the Phase 7a Colab run — produces task_scam recall=0.871, support=62, 254 rows, PASS verdict. Every quantitative claim in Chapter 5 and the summary table must be updated before expanding prose.

A second correction is needed in Chapter 6: the conclusion and future work section currently states task-scam recall "of only 0.44", which is stale. After the Phase 7a recovery, the honest closing claim is that task_scam recall cleared the 0.80 gate floor (0.871) but the holdout set is still small and the system carries two explanation quality flags.

The bibliography is also commented out in `main.tex`. Citation insertion into chapter prose and enabling the bibliography render are Phase 9 deliverables deferred from Phase 8.

**Primary recommendation:** Fix the evaluation data mismatch first (table + Chapter 5 numbers + Chapter 6 conclusion), then expand each chapter scaffold with full prose and in-text citations, then enable bibliography rendering.

---

## Project Constraints (from CLAUDE.md)

- Use the get-shit-done skill when the user uses a `gsd-*` command.
- Do not apply GSD workflows unless the user explicitly asks.
- After completing any deliverable, offer the user the next step.

---

<user_constraints>
## User Constraints (from STATE.md locked decisions — equivalent to CONTEXT.md)

### Locked Decisions (must not be reopened)

- Six-chapter `main.tex` structure is the working thesis template; no parallel tree.
- Chapter 5 evidence must come from tracked manifests and saved evaluation artifacts only; off-repo training numbers are appendix-only.
- Final release verdict wording in thesis prose: "not release-ready under its own safety gate"; literal BLOCK label stays in tables, appendix notes, or file names only.
- Thesis must read like a natural undergraduate report; no GSD jargon, no phase numbers, no STATE.md, ROADMAP, UAT, PLAN.md, or internal workflow language in thesis prose.
- No metric laundering: every quantitative claim must point to a named frozen artifact.
- Text-only v1 scope; do not imply OCR, image, audio, or mobile support anywhere.
- Local/offline inference default; do not imply cloud-first processing.
- The final authoritative evaluation is `eval-snapshot-task-scam-recovery.json` (Phase 7a Colab run, 2026-05-28), NOT the earlier `phase5-release-eval-phase5-recovered-balanced-val.json`.

### Claude's Discretion

- Prose style choices within the guardrail rules (short sentences, measured verbs).
- Depth of expansion per section, provided all claims are evidence-grounded.
- Order in which chapter scaffolds are expanded (recommended: fix eval mismatch first, then Ch3, Ch4, Ch2, Ch1, Ch6).

### Deferred Ideas (OUT OF SCOPE for Phase 9)

- Adding new system features or writing any code.
- Changing the chapter architecture.
- Adding figures beyond replacing the system_overview_placeholder.
- Performance optimization or re-running evaluations.
- Final submission formatting polish (that is Phase 10).
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REP-02 | Main chapters drafted | All six chapter scaffolds exist; expansion path is clear; evaluation mismatch blocks Ch5 until fixed |
| REP-03 | Evidence-backed claims | Frozen artifacts identified for each chapter; citation markers must be inserted; bibliography must be enabled |
</phase_requirements>

---

## Architectural Responsibility Map

This is a documentation phase, not a software phase. The "architecture" is the LaTeX manuscript structure.

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Evaluation claim accuracy | Chapter 5 prose + evaluation_snapshot.tex | Phase 7a eval snapshot JSON | All numbers must trace to the frozen artifact |
| Model selection narrative | Chapter 3 (methodology) | Phase 3 pilot manifest | Pilot selection, 4B-primary decision, 8B reconciliation |
| Data pipeline narrative | Chapter 3 + Chapter 4 | Phase 1 manifest + recovered-balanced splits | Dataset size, lineage, quality review numbers |
| Implementation narrative | Chapter 4 | docs/user/USER_GUIDE.md, LOCAL_MODELS.md, src/ package structure | Module names, CLI entry points, runtime profiles |
| Background and citations | Chapter 2 | references.bib (6 entries seeded) | 5 substantive references already in bib; must be inserted in-text |
| Introduction and framing | Chapter 1 | Phase 5 manifest + external threat sources | Context citations needed; scope framing already done |
| Conclusion | Chapter 6 | Phase 7a eval snapshot + LOCAL_MODELS.md | Stale 0.44 number must be updated to 0.871 |
| Bibliography render | main.tex | All chapters with \cite{} markers | Enable after citation pass is complete |

---

## Critical Finding: Evaluation Data Mismatch

This is the highest-priority issue for the planner. Two artifacts are out of sync:

### What the chapters currently say (STALE — must be corrected)

Source: `05_evaluation_and_discussion.tex` and `tables/evaluation_snapshot.tex`

| Metric | Current (stale) | Correct (Phase 7a) |
|--------|----------------|---------------------|
| Total evaluated rows | 210 | 254 |
| task_scam support | 18 | 62 |
| task_scam recall | 0.4444 | 0.8710 |
| task_scam precision | 0.1455 | 1.0 |
| task_scam F1 | 0.2192 | 0.9310 |
| bank_impersonation recall | 0.9821 | 1.0 |
| bank_impersonation precision | 0.7639 | 0.8358 |
| zalo_social_engineering recall | 0.9867 | 0.9600 |
| weighted F1 | 0.8618 | not directly reported in snapshot |
| macro F1 | 0.7431 | not directly reported in snapshot |
| overall accuracy | not reported | 0.9567 (243/254) |
| Release verdict | BLOCK | PASS |
| blocker_reasons | task_scam recall 0.44 below 0.90 floor | none |

Source for correct values: `.planning/phases/07a-task-scam-recall-recovery/eval-snapshot-task-scam-recovery.json`
Source for stale values: `data/manifests/phase5-release-eval-phase5-recovered-balanced-val.json` and `05-release-eval-phase5-recovered-balanced-val.md`

### What Chapter 6 currently says (STALE — must be corrected)

- "task scam recall of only 0.44" — must become 0.871
- "the system is not yet release-ready" — must be updated to reflect PASS verdict while still being honest about the small holdout and two explanation flags

### Explanation flags — still valid

The two explanation quality flags from the Phase 5 manifest are real caution signals that apply to the broader system design and remain valid as limitations, even after the Phase 7a PASS:
- "Label alignment flag: predicted labels are weakly supported by the captured cues."
- "Recommendation quality flag: explanation fell back to generic safe advice."

These should appear in Chapter 5's limitations section as design cautions, not as blockers.

---

## Chapter-by-Chapter State Assessment

### Chapter 1 — Introduction

**File:** `documents/reports/latex/chapters/01_introduction.tex`
**Current state:** Well-written scaffold with all four required sections present.
**What it has:** Background and motivation, problem statement, objectives and scope (4-item list), report organization.
**What it needs:**
- In-text citations for `ais2024biometricwarning` and `groupib2022laser` (cited in TODO.md, currently no `\cite{}` markers in the file).
- Minor prose expansion in the objectives section to mention the evaluation outcome (Phase 7a PASS, task_scam recall = 0.871 cleared the gate).
- The scope paragraph already correctly states the system "still falls short on task-scam recall" — this is now partially stale; the recovery cleared the gate floor but the thesis should honestly note the small holdout size.
**Confidence in current state assessment:** HIGH [VERIFIED: file read]

### Chapter 2 — Related Work and Background

**File:** `documents/reports/latex/chapters/02_related_work_and_background.tex`
**Current state:** Clean scaffold. Five sections cover domain, privacy, explainability, local models, and evaluation priorities.
**What it needs:**
- In-text citations for `rjoub2023surveyxai`, `lim2025explicate`, and `nist2026privacyframework` (no `\cite{}` markers currently present).
- Prose expansion in each section to cite and briefly reference the sources rather than making unattributed general claims.
- Section 4 (Open-Weight Local Models) should mention the 4B-vs-8B reconciliation: the proposal originally planned an 8B path; after the hardware-fit pilot the 4B path was locked as primary with the 7B remaining as a comparison option.
**Confidence:** HIGH [VERIFIED: file read]

### Chapter 3 — Methodology and System Design

**File:** `documents/reports/latex/chapters/03_methodology_and_system_design.tex`
**Current state:** Six-section scaffold. References two `\input{}` tables: `tables/milestone_summary` (exists) and `figures/system_overview_placeholder` (exists as placeholder fbox).
**What it needs:**
- Full prose expansion for each section (Data Construction, Offline Runtime, Local Model Selection, Explainable Decisioning, Design Principles).
- Concrete numbers from manifests: 3,000-row corpus, 49/50 quality pass, balanced four-class split (bank_impersonation, zalo_social_engineering, task_scam, benign), recovered-balanced lineage, train/val/test split counts from `manifest-phase1-recovered-balanced-claude-v2.json` (train=476, val=207, test=208 — NOTE: these are the Phase 3 smoke split counts; the Phase 7 final split has different counts: 2018 train, 210 val after the full closeout training run).
- Pilot comparison narrative: three candidates (qwen3-4b-instruct-2507, qwen3.5-4b, qwen2.5-7b-instruct), recall-first selection, 4B baseline winner, 4B runner-up — from `phase3-large-pilot-2026-05-14.json`.
- Explicit mention of training artifact: QLoRA, three epochs, adapter registered in off-repo model registry.
- In-text citations for `rjoub2023surveyxai` and `nist2026privacyframework`.
- The system overview placeholder should remain as-is for now (Phase 10 can replace it with a real TikZ figure).
**Key numbers for this chapter:**
  - Corpus: 3,000 rows (recovered-balanced.jsonl) [VERIFIED: STATE.md]
  - Classes: 4 (bank_impersonation, zalo_social_engineering, task_scam, benign) [VERIFIED: eval snapshot]
  - Quality review: 49/50 pass, avg realism 4.68, avg label-correctness 4.96 [VERIFIED: evaluation_snapshot.tex]
  - Pilot candidates: qwen3-4b-instruct-2507, qwen3.5-4b, qwen2.5-7b-instruct [VERIFIED: phase3-large-pilot-2026-05-14.json]
  - Selected baseline: qwen3-4b-instruct-2507 [VERIFIED: same]
  - Quantization: q8_0 GGUF [VERIFIED: STATE.md]
**Confidence:** HIGH [VERIFIED: file read + manifest read]

### Chapter 4 — Implementation

**File:** `documents/reports/latex/chapters/04_implementation.tex`
**Current state:** Six-section scaffold covering three subsystem packages (data_pipeline, runtime, model_adaptation).
**What it needs:**
- Prose expansion pulling concrete module names, CLI entry points, and runtime profiles from `docs/user/USER_GUIDE.md` and `docs/user/LOCAL_MODELS.md`.
- Key entry points to mention: `vnphish demo` (demo launch), `python -m src.runtime.cli demo`, the `gguf-laptop` runtime profile, the `accelerated-local` profile.
- Dependency group separation in `pyproject.toml` (dev, train, runtime) is already mentioned — this is correct.
- Do NOT imply OCR, image, audio, or mobile support.
**Confidence:** HIGH [VERIFIED: file read; docs paths need to be read by planner or writer before expansion]

### Chapter 5 — Evaluation and Discussion

**File:** `documents/reports/latex/chapters/05_evaluation_and_discussion.tex`
**Current state:** Four sections. CRITICAL: All quantitative numbers are stale (Phase 5 BLOCK result, not Phase 7a PASS result).
**What it needs (in order):**
1. **First: update the evaluation_snapshot.tex table** with Phase 7a numbers before expanding prose.
2. Update Section "Repaired-Holdout Results" with correct Phase 7a numbers:
   - 254 evaluated rows (not 210)
   - task_scam: recall=0.871, precision=1.0, f1=0.931, support=62
   - bank_impersonation: recall=1.0, precision=0.836, f1=0.911, support=56
   - zalo_social_engineering: recall=0.960, precision=1.0, f1=0.980, support=75
   - benign: recall=1.0, precision=1.0, f1=1.0, support=61
   - overall accuracy: 0.9567 (243/254)
   - Verdict: PASS (all risky class recall floors cleared)
3. Update "Interpretation of the Final Result" — the final verdict is now a PASS, but with caveats: small holdout, two explanation flags, task_scam misclassifications went into bank_impersonation bucket (visible in row data).
4. Update "Limits of the Current Evidence" — task_scam support grew from 18 to 62 but is still a closeout snapshot, not a production-scale study.
5. Add in-text citation for `lim2025explicate` as comparison context.
**Correct evidence anchor:** `.planning/phases/07a-task-scam-recall-recovery/eval-snapshot-task-scam-recovery.json`
**Confidence:** HIGH [VERIFIED: both artifact files read]

### Chapter 6 — Conclusion and Future Work

**File:** `documents/reports/latex/chapters/06_conclusion_and_future_work.tex`
**Current state:** Three sections (Main Takeaways, What the Final Evaluation Means, Future Work).
**What it needs:**
- Update "What the Final Evaluation Means" section: task_scam recall "of only 0.44" must become 0.871. The system now clears its own gate floor but the thesis should honestly note (a) small holdout size, (b) two explanation flags remain.
- The statement "should not describe the current version as ready for deployment in a safety-sensitive setting" is still defensible — the PASS verdict is on a 62-sample closeout set; the explanation flags are real. This honest framing should be kept.
- Future work section is well-written; keep it as-is.
**Confidence:** HIGH [VERIFIED: file read + Phase 7a eval snapshot]

---

## Evidence Anchors per Chapter

| Chapter | Claim type | Artifact path | Status |
|---------|-----------|---------------|--------|
| Ch1 introduction | Threat context | `tinnhiemmang.vn` URL, group-ib URL | In references.bib; need \cite{} in prose |
| Ch1 scope | Implemented objectives | Proposal objectives list + Phase 5 closeout | Need to update scope para re: PASS verdict |
| Ch2 privacy framing | NIST framework | `nist2026privacyframework` | In references.bib; need \cite{} in prose |
| Ch2 explainability | XAI survey + EXPLICATE | `rjoub2023surveyxai`, `lim2025explicate` | In references.bib; need \cite{} in prose |
| Ch3 data pipeline | Corpus size and quality | `manifest-phase1-recovered-balanced-claude-v2.json` | Numbers available; need prose expansion |
| Ch3 model selection | Pilot results | `phase3-large-pilot-2026-05-14.json` | Manifest read; need prose |
| Ch3 4B-vs-8B | Reconciliation note | `documents/internship-proposal.md` + `report-09` | Exists; need prose in methodology |
| Ch4 CLI surface | Entry points | `docs/user/USER_GUIDE.md`, `docs/user/LOCAL_MODELS.md` | Need to read these docs before writing |
| Ch5 eval numbers | Final holdout | `eval-snapshot-task-scam-recovery.json` | MUST use this, not the Phase 5 manifest |
| Ch5 explanation flags | Quality cautions | `phase5-release-eval-phase5-recovered-balanced-val.json` flag_reasons | Use as design limitation |
| Ch5 table | Snapshot table | `tables/evaluation_snapshot.tex` | MUST be updated to Phase 7a numbers first |
| Ch6 conclusion | Final verdict | `eval-snapshot-task-scam-recovery.json` | Update 0.44 -> 0.871 |

---

## What the 4B-vs-8B Reconciliation Needs in Chapter 3

The proposal (Task 3) promised "fine-tuning an open-source 8B parameter model using LoRA". The execution used a 4B primary path. Chapter 3 must address this without apologizing for it. The correct framing [VERIFIED: `03-07-SUMMARY.md` + proposal execution update]:

- The pilot comparison evaluated three candidates including the 7B model.
- On the target 8GB VRAM laptop, the 4B models provided a more reliable hardware fit.
- The 4B-primary path was locked after the hardware-fit pilot; the 7B remains visible as a comparison candidate and accelerated-path option.
- This was a deliberate delivery-quality decision, not a scope reduction.
- The proposal itself now carries a dated execution update (2026-05-17) recording this reconciliation.

The thesis should present this in the model selection section of Chapter 3 as a hardware-justified methodology decision, not as a deviation to apologize for.

---

## Honest Quantitative Claims (Phase 9 approved numbers)

These are the numbers the thesis may assert with evidence. All others require explicit artifact support before use.

**Phase 7a Colab eval (authoritative — use for all Ch5 claims):**
Source: `.planning/phases/07a-task-scam-recall-recovery/eval-snapshot-task-scam-recovery.json`
- Total evaluated: 254
- Accuracy: 0.9567 (243/254)
- Verdict: PASS
- bank_impersonation: recall=1.0, precision=0.836, f1=0.911, support=56
- zalo_social_engineering: recall=0.960, precision=1.0, f1=0.980, support=75
- task_scam: recall=0.871, precision=1.0, f1=0.931, support=62
- benign: recall=1.0, precision=1.0, f1=1.0, support=61

**Phase 5 eval (historical only — do NOT use as the main result):**
Source: `data/manifests/phase5-release-eval-phase5-recovered-balanced-val.json`
- This was the intermediate result before Phase 7a recovery. Use only to show the before/after improvement story if needed. Do not present it as the final result.

**Data pipeline numbers:**
Source: `manifest-phase1-recovered-balanced-claude-v2.json`
- Original Phase 3 split: train=476, val=207, test=208
- Final Phase 7 refresh: train=2018, val=210 (from STATE.md training summary)

**Quality review numbers:**
Source: `tables/evaluation_snapshot.tex` (these are correct, unchanged)
- Quality review: 49/50 pass
- Avg realism: 4.68/5, avg label-correctness: 4.96/5

**Pilot results:**
Source: `phase3-large-pilot-2026-05-14.json`
- Three candidates evaluated on 33 fixed balanced samples
- qwen3-4b-instruct-2507 selected as baseline winner
- qwen3.5-4b as runner-up
- Selection basis: recall-first, hardware-fit (laptop 8GB VRAM)

**Training:**
Source: STATE.md session continuity
- Baseline refresh: 2018 train, 210 val, device cuda, QLoRA, checkpoint-505
- Runner-up: 476 train, 207 val (Phase 3 run)

**Deployment:**
Source: STATE.md session continuity
- GGUF: q8_0 quantization
- Warm latency on CPU: ~13s (after Phase 7b optimization)
- Runtime profile: gguf-laptop (default), accelerated-local (optional)

---

## Common Pitfalls for This Phase

### Pitfall 1: Using the wrong evaluation artifact
**What goes wrong:** Prose or table references the Phase 5 BLOCK result (210 rows, task_scam recall 0.44) instead of the Phase 7a PASS result.
**Root cause:** The `evaluation_snapshot.tex` table was not updated after Phase 7a. The TODO.md citation target still points to `phase5-release-eval-phase5-recovered-balanced-val.json`.
**Prevention:** Update `tables/evaluation_snapshot.tex` as the very first task in Phase 9. Update the TODO.md citation target for Chapter 5 to point to `eval-snapshot-task-scam-recovery.json`.
**Warning signs:** Any reference to "210 evaluated messages", "task-scam recall 0.44", "support 18" in thesis prose.

### Pitfall 2: Introducing GSD/process language into thesis prose
**What goes wrong:** Phrases like "Phase 7a", "BLOCK verdict", "UAT", "ROADMAP", "planning artifacts" appear in the chapter text.
**Root cause:** Directly copying from STATE.md or planning file summaries.
**Prevention:** All prose should be written fresh using thesis-facing vocabulary per WRITING_GUARDRAILS.md. Consult the terminology replacements table.
**Warning signs:** Digit-N phase references, GSD tool names, planning file names.

### Pitfall 3: Macro F1 not directly available in Phase 7a snapshot
**What goes wrong:** Chapter 5 tries to report macro F1 but the Phase 7a snapshot does not pre-compute it; the writer invents a number or leaves a placeholder.
**Root cause:** The Phase 7a eval snapshot JSON contains per-label metrics and accuracy but not a pre-aggregated macro_f1 field (unlike the Phase 5 manifest which had `"macro_f1": 0.7431`).
**Prevention:** Compute macro F1 from the per-label F1 scores in the snapshot: (0.9106 + 0.9796 + 0.9310 + 1.0) / 4 = 0.9553. This is the correct value to report for Phase 7a. Verify the computation before writing.
**Warning signs:** Use of the stale 0.7431 macro F1 in Phase 7a-era prose.

### Pitfall 4: Overclaiming model quality or deployment readiness
**What goes wrong:** Conclusion implies the system is production-ready based on the PASS verdict alone.
**Root cause:** PASS verdict sounds like a full endorsement.
**Prevention:** Always qualify with (a) 62-sample holdout for task_scam, (b) two explanation quality flags still stand, (c) this is a closeout academic snapshot not a production study.
**Warning signs:** "The system is ready", "meets production standards", "deployment-grade" in prose.

### Pitfall 5: Missing citation markers before enabling bibliography
**What goes wrong:** Bibliography is enabled in main.tex but `\cite{}` markers are absent from some sections, leaving dangling references or missing credits.
**Root cause:** Bibliography enabling and citation insertion happen in the wrong order.
**Prevention:** Insert all `\cite{}` markers across all chapters first; then and only then uncomment the bibliography block in main.tex.

### Pitfall 6: Confusing the two evaluation runs in Chapter 5
**What goes wrong:** The chapter mixes details from the two runs (Phase 5 BLOCK + Phase 7a PASS) without clearly distinguishing them.
**Prevention:** Present the Phase 7a result as the main final result. The Phase 5 run can appear as an earlier intermediate snapshot that showed the task_scam weakness before the recovery run. Label them distinctly in prose.

---

## Architecture Patterns for This Phase

### Pattern 1: Evidence-first prose expansion
**What:** Start each section by locating the evidence anchor, extract the concrete value, then write the sentence around it.
**When to use:** Every section that makes a quantitative or capability claim.
**Example:**
```
[Find] eval-snapshot: task_scam recall=0.871, support=62
[Write] "On 62 held-out task-scam examples, the model reached a recall of 0.871, clearing the 0.80 gate floor set for this class."
```
Never write a number from memory; always trace it to the artifact.

### Pattern 2: Citation-last expansion
**What:** Write full prose first, mark citation slots with `\cite{key}`, then run a single citation pass to verify each key exists in references.bib.
**When to use:** For every claim that has a literature source.
**Known valid keys:** `ais2024biometricwarning`, `groupib2022laser`, `lim2025explicate`, `rjoub2023surveyxai`, `nist2026privacyframework`, `oregonstate2026formatting`.

### Pattern 3: Guardrail check before commit
**What:** After expanding each chapter, scan for forbidden terms before marking it complete.
**Forbidden in prose:** GSD, roadmap, phase (with capital P followed by a digit), STATE.md, ROADMAP.md, UAT, PLAN.md, BLOCK (as a verdict label outside of tables/appendix), "planning artifacts", "internal workflow".
**Allowed:** "closeout evaluation", "saved evaluation artifact", "implementation record", "user-facing validation", "not release-ready under its own safety gate" (for the pre-7a framing).

---

## Recommended Task Sequence for the Planner

The planner should structure Phase 9 tasks in this order to avoid circular corrections:

1. **Task 1 (Pre-condition fix):** Update `tables/evaluation_snapshot.tex` with Phase 7a numbers. Update the TODO.md Chapter 5 citation target. This unblocks all Chapter 5 prose work.
2. **Task 2:** Expand Chapter 3 (Methodology and System Design) with full prose — data pipeline numbers, pilot comparison, 4B-vs-8B reconciliation, training artifacts, deployment profiles. Insert `\cite{}` markers for rjoub2023surveyxai and nist2026privacyframework.
3. **Task 3:** Expand Chapter 4 (Implementation) with full prose — module names, CLI entry points, runtime profiles, pyproject.toml dependency groups. (Read docs/user/USER_GUIDE.md and docs/user/LOCAL_MODELS.md before writing.)
4. **Task 4:** Expand Chapter 5 (Evaluation and Discussion) using corrected table + Phase 7a numbers. Update all stale numbers. Retain explanation flags as design caution notes. Insert `\cite{}` for lim2025explicate.
5. **Task 5:** Update Chapter 6 (Conclusion and Future Work) — correct 0.44 -> 0.871, revise verdict framing.
6. **Task 6:** Citation pass across all chapters — insert `\cite{}` markers in Ch1 and Ch2.
7. **Task 7:** Enable bibliography in main.tex (uncomment the two bibliography lines). Verify citation keys match references.bib entries.

---

## Files the Writer Must Read Before Expanding Each Chapter

| Chapter | Files to read first |
|---------|-------------------|
| Ch3 Methodology | `data/manifests/phase3-large-pilot-2026-05-14.json`, `data/manifests/manifest-phase1-recovered-balanced-claude-v2.json`, STATE.md training summary section |
| Ch4 Implementation | `docs/user/USER_GUIDE.md`, `docs/user/LOCAL_MODELS.md` |
| Ch5 Evaluation | `eval-snapshot-task-scam-recovery.json`, `phase5-release-eval-phase5-recovered-balanced-val.json` (for the intermediate story) |
| Ch6 Conclusion | Same as Ch5 |
| All chapters | `08-WRITING_GUARDRAILS.md` |

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| Macro F1 for Phase 7a | New evaluation run | Compute from per-label F1s in existing snapshot: (0.9106 + 0.9796 + 0.9310 + 1.0) / 4 = 0.9553 |
| New citations | Find new references | Use the 6 entries already in references.bib; only add if a specific claim has no coverage |
| System architecture figure | New TikZ diagram | Keep `system_overview_placeholder.tex` as-is; Phase 10 handles figure polish |
| New evaluation | Re-run model | All evaluation numbers come from frozen artifacts; no new runs in Phase 9 |

---

## State of the Art (Writing Conventions for Vietnamese CS Undergraduate Reports)

**Format conventions [ASSUMED]:** Vietnamese CS undergraduate theses at USTH typically follow a format similar to English-language IEEE/ACM report style — numbered chapters, numbered sections, IEEE citation style (ieeetr is already configured in main.tex), 11pt Times New Roman, A4 paper. The existing main.tex already matches this.

**Language:** The thesis is written in English (confirmed by existing chapter prose and main.tex `\usepackage[english]{babel}`).

**Tone [VERIFIED: 08-WRITING_GUARDRAILS.md]:** Short declarative sentences, measured verbs (shows, indicates, suggests, records, supports), no AI-like stock phrases, no inflated claims.

**Chapter length [ASSUMED]:** Undergraduate CS theses at Vietnamese universities typically run 40-80 pages total. The current scaffolds are short; Phase 9 should expand each chapter to 3-6 pages of substantive prose. Chapters 3 and 5 will likely need the most expansion.

---

## Environment Availability

| Dependency | Required By | Available | Notes |
|------------|------------|-----------|-------|
| LaTeX toolchain | Compilation verification | Not in execution env | Verify on Overleaf or local LaTeX install; Phase 8 confirmed this |
| Python (for artifact reading) | Pre-write evidence extraction | Available | Used throughout Phase 7a |
| Frozen eval JSON | Ch5 numbers | Available at .planning/phases/07a-task-scam-recall-recovery/ | Read-only; do not modify |
| docs/user/USER_GUIDE.md | Ch4 expansion | Available in repo | Must be read before Ch4 writing |
| docs/user/LOCAL_MODELS.md | Ch4 expansion | Available in repo | Must be read before Ch4 writing |

---

## Validation Architecture

This is a documentation phase. There is no automated test suite for prose quality. The validation approach is:

- **Per-chapter checklist:** After each chapter is expanded, scan for forbidden terms (guardrail check), verify every quantitative claim traces to a named artifact, and verify every `\cite{key}` key exists in references.bib.
- **Pre-bibliography gate:** All `\cite{}` markers inserted before uncomment of bibliography block in main.tex.
- **Phase gate:** All six chapters expanded, citation pass complete, bibliography enabled, and a human-readable review confirming no GSD language, no stale numbers, and no unsupported claims.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Chapter length target of 3-6 pages per chapter is appropriate for USTH undergraduate | State of the Art | Thesis may be too short or too long; supervisor review in Phase 10 will catch this |
| A2 | Macro F1 for Phase 7a computed as simple average of per-label F1 = 0.9553 | Honest Quantitative Claims | Small discrepancy if weighted differently; use this value with note that it is computed from per-label figures |
| A3 | docs/user/USER_GUIDE.md and docs/user/LOCAL_MODELS.md exist and contain current CLI surface | Chapter 4 evidence | If outdated, Ch4 writer must fall back to reading src/ package docstrings and pyproject.toml |

---

## Open Questions (RESOLVED)

1. **Does the Phase 5 evaluation run need to appear in Chapter 5 at all?**
   - What we know: The Phase 7a run is the final result. The Phase 5 run showed the pre-recovery state.
   - What's unclear: Whether the committee expects to see a before/after comparison or just the final numbers.
   - Recommendation: Include the Phase 5 intermediate result as a brief paragraph explaining the task_scam recovery motivation, then present Phase 7a as the final closeout. This shows the iterative improvement story, which is academically stronger than only showing the final numbers.

2. **Should weighted F1 or macro F1 be the headline metric?**
   - What we know: Phase 5 manifest reported both (weighted 0.8618, macro 0.7431). Phase 7a snapshot reports per-label metrics and accuracy but not pre-aggregated F1 averages.
   - Recommendation: Report per-label recall as the primary metric (because recall-first is the stated evaluation priority) and compute macro F1 from per-label F1s (=0.9553) as a summary. Avoid leading with weighted F1 since it can mask weak minority classes.

3. **Is the system_overview_placeholder.tex a blocking gap?**
   - What we know: It is a visible fbox placeholder in Chapter 3. It has correct suggested content.
   - Recommendation: Leave it as-is for Phase 9. Phase 10 can replace it. The thesis compiles with it present.

---

## Sources

### Primary (HIGH confidence)
- `.planning/phases/07a-task-scam-recall-recovery/eval-snapshot-task-scam-recovery.json` — Phase 7a authoritative evaluation numbers
- `data/manifests/phase5-release-eval-phase5-recovered-balanced-val.json` — Phase 5 intermediate evaluation numbers
- `data/manifests/phase3-large-pilot-2026-05-14.json` — Pilot comparison manifest
- `data/manifests/manifest-phase1-recovered-balanced-claude-v2.json` — Dataset split manifest
- `documents/reports/latex/chapters/01_introduction.tex` through `06_conclusion_and_future_work.tex` — Current chapter scaffold content
- `documents/reports/latex/tables/evaluation_snapshot.tex` — Current (stale) evidence table
- `documents/reports/latex/tables/milestone_summary.tex` — Implementation summary table
- `documents/reports/latex/references.bib` — Six seeded BibTeX entries
- `.planning/phases/08-thesis-structure-and-evidence-map/08-EVIDENCE_MAP.md` — Chapter evidence map
- `.planning/phases/08-thesis-structure-and-evidence-map/08-WRITING_GUARDRAILS.md` — Tone and honesty rules
- `.planning/STATE.md` — Locked decisions, session continuity, training artifact locations

### Secondary (MEDIUM confidence)
- `documents/internship-proposal.md` — Original proposal + execution update for 4B reconciliation
- `.planning/phases/03-local-model-adaptation-and-deployment-paths/03-07-SUMMARY.md` — Reconciliation note summary
- `documents/reports/latex/TODO.md` — Phase 9 drafting tasks list
- `documents/reports/latex/main.tex` — LaTeX document structure

---

## Metadata

**Confidence breakdown:**
- Chapter state assessment: HIGH — all chapter files read directly
- Evaluation mismatch: HIGH — both artifact files read and compared
- Evidence anchors: HIGH — manifest files read directly
- Writing conventions: MEDIUM (thesis length) / HIGH (tone and format) — format confirmed from main.tex; length is ASSUMED
- 4B-vs-8B reconciliation: HIGH — proposal and summary read directly

**Research date:** 2026-05-29
**Valid until:** Phase 9 completion (static documentation phase, no moving targets)
