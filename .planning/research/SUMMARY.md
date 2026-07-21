# Project Research Summary

**Project:** Vietnamese scam-detection thesis — v6.0 Report Revision
**Domain:** Academic thesis defense-response revision (NLP/ML methodology writing, not software development)
**Researched:** 2026-07-21
**Confidence:** MEDIUM-HIGH

## Executive Summary

The defense transcript shows one root failure repeated in six shapes: the report never made its own methodology *explicit and findable*, so the judges could not verify content that in fact exists and is technically sound. The judge asked "how do you label them" roughly ten times and was never pointed to a locatable answer; asked why classification uses a generative QLoRA-tuned decoder instead of an encoder + classification head and got no written justification; asked why Qwen instead of PhoBERT and received a weak, contradicted live answer (English extension, when the judge correctly noted the stated scope is Vietnamese); flagged that confusion-matrix and train/val/test counts don't reconcile across report/slides; and, compounding all of this, invoked the supervisor because the writing style read as AI-generated with no counterbalancing evidence of ownership. None of these are code or methodology defects — the underlying pipeline (label-conditioned synthetic generation, QLoRA fine-tuning, structured JSON output) is legitimate and well-precedented in the literature. The problem is entirely that the report doesn't say so, anywhere, explicitly.

Research across all four files converges on the same fix pattern: this is a **documentation and evidentiary-writing task**, not a research or redesign task. Four research threads each supply the citable vocabulary and structure needed to close a specific transcript gap: (1) STACK.md supplies the academic terminology ("generative classification," "verbalizer," "instruction-based classification") and direct precedent papers proving generative-decoder classification without a classification head is a named, legitimate, chosen paradigm — not a workaround. (2) FEATURES.md supplies the standard "Dataset Construction and Labeling Methodology" section structure (per Datasheets for Datasets) and the "condition-on-label" precedent that directly answers "how do you label them." (3) ARCHITECTURE.md supplies a rigorous, honest Qwen-vs-PhoBERT comparison grounded in task shape (structured multi-field generation vs. PhoBERT's encoder-only, non-generative limits), replacing the weak live "English extension" answer with the correct primary argument. (4) PITFALLS.md supplies the meta-strategy: fix content and traceability, not tone — the judge explicitly said AI-assisted drafting is acceptable if genuine understanding can be demonstrated evidentially (schema tables, worked examples, specific pipeline detail, cross-document numeric consistency).

The key risk to manage during revision is scope creep into unneeded rewriting: the existing report voice and already-strong sections (e.g., privacy/cloud-leakage motivation) should not be touched, per the student's own constraint (`WRITING_GUARDRAILS.md`) and per the pitfalls research's explicit warning that padding already-good sections reads as evasive, not thorough. The revision should be laser-targeted at the six documented transcript gaps, written with maximum specificity and citation density, and paired with a numeric consistency audit (confusion matrix vs. split counts) that removes the strongest actual evidence the judges had for "fabricated/borrowed work."

## Key Findings

### Recommended Stack (Academic Terminology & Framing)

STACK.md establishes that generative/instruction-based classification (the judge's exact objection — "why not add a classification head to QLoRA") is a real, named, actively-studied paradigm, not an improvised justification. The umbrella terms to use in the new subsection are **"generative classification"** and **"instruction-based (text-generation) classification with a verbalizer,"** explicitly contrasted with the judge's expected "embedding-based classification-head" approach.

**Core terminology/precedent to cite:**
- Text-to-text classification / classification-as-generation (Raffel et al., T5, 2020) — foundational framing for emitting labels as generated tokens.
- Verbalizer (Schick & Schütze, PET, 2021; Liu et al. survey, 2023) — the named mechanism by which free-text output collapses onto a fixed label set; this is what makes the label field genuine classification without extra layers.
- Embedding-based vs. instruction-based comparison (Yousefiramandi & Cooney, 2025, arXiv:2512.12677) — directly compares the *exact two architectures* the judge was asking about on the same causal LLM base, treating both as legitimate.
- Domain-analogous precedent: phishing-detection small-LLM generative classification (Lin et al., 2025) and a Korean phishing framework producing the same output shape (label + tactic + evidence span) as this thesis (Electronics, 2026).
- Joint label+explanation generation is *more faithful* than a two-stage predict-then-explain pipeline (Narang et al., WT5, 2020) — the strongest available citation for why label + evidence + recommendation are generated together in one forward pass rather than split across a head and a separate explainer.

**Bottom line:** QLoRA does not need "additional layers" for classification because the classification signal is supplied by the training objective (next-token loss on the label field), and the fixed vocabulary of class strings the model reproduces *is* the verbalizer. This is the precise, citable rebuttal to the judge's core question.

### Expected Methodology Content (Dataset & Labeling Section)

FEATURES.md identifies the single highest-value fix: a new, explicitly-named **"Dataset Construction and Labeling Methodology"** subsection, structured per the Datasheets for Datasets framework (Gebru et al., 2018), the field's standard reference for dataset documentation.

**Must include (directly responsive to transcript gaps):**
- Explicit problem-framing sentence before any data discussion: "This is a supervised multi-class text classification problem with 4 classes: [list]" — the judge's #1 complaint ("we are missing... the Goal: Supervised classification").
- Class taxonomy with definitions and boundary notes between adjacent classes.
- Full JSON schema shown as a real example record (listing) plus a field-by-field table, with the `label` field's role explicitly called out ("the ground-truth training class assigned at generation time").
- **Label assignment methodology, stated plainly**: labels are assigned *at generation time* via label-conditioned prompts (each record is generated *for* a target class), not via a separate post-hoc labeling pass. This is the precise, direct answer to "how do you label them," asked ~10 times and never answered.
- Citable precedent for this exact mechanism: ZeroGen (Ye et al., EMNLP 2022) and "Condition on the Label" (arXiv:2407.12813, 2024) — both establish label-conditioned synthetic generation as standard, recommended practice, not an ad hoc shortcut.
- Provenance (NCSC seed %), generation pipeline, quality-control/judge-gate pass counts, class distribution table, train/val/test split methodology (with an explicit note that val/test don't need the same generation-time label assumption as training — directly answers the judge's "for val/test you dont need but for training you need it" line), and a crisp SHA-256 integrity sentence.
- A first-person worked-example walkthrough of one record end-to-end — cheap to write, highest defense-proofing value, since this is literally what the judge demanded live and the student could not produce fast enough.

**Defer:** page-count as a target. The transcript's "~14 substantive pages" complaint is a symptom of missing content, not a padding target — closing the six named gaps should organically add 3–5+ pages; adding unrelated material to hit a number is explicitly flagged as counterproductive.

### Architecture Approach (Qwen vs. PhoBERT)

ARCHITECTURE.md establishes the correct, honest, task-shape-driven justification for choosing Qwen — replacing the live "English extension" answer, which the judge directly and correctly undermined.

**Primary argument (task shape, not language):** The task requires jointly producing (1) a risk tier, (2) a 4-class label, (3) grounded extractive evidence spans, and (4) free-form recommendation text — a combined classification + span-extraction + generation task. PhoBERT is a pure encoder (RoBERTa-based, masked-LM pretraining, no decoder, cannot generate text at all); it can produce (1)–(2) well via a classification head but has no native mechanism for (3) or (4). Vietnamese NLP literature's own answer to "classification + evidence + generation" is to couple *two separate models* (an extractive encoder + a BART-based generator, e.g. RExC); Qwen unifies this into one model, one forward pass, one JSON schema, with fields conditioned on each other by construction.

**Secondary/supporting argument (multilingual):** Qwen3 is pretrained on ~36T tokens across 119 languages (incl. Vietnamese and English) in a shared representation space; PhoBERT's tokenizer and 20GB corpus are Vietnamese-only, requiring a wholesale second model/stack to extend to English. This is legitimate but should be explicitly subordinated to the task-shape argument — presenting it as primary is what got the live answer discredited.

**Honest limitation to state, not hide:** generative structured output's field *assembly* (e.g., evidence-to-label linking) is implicit in decoding rather than architecturally guaranteed, a documented weakness class; the report should acknowledge this rather than overclaim.

### Critical Pitfalls (Revision-Process Risks)

1. **Locatability over existence.** The judges' core failure mode was not "work wasn't done" but "evidence of the work wasn't a named, findable section." Every fix must be an explicit, labeled subsection — not something inferable from code or appendices.
2. **Missing explicit problem formalization** let the entire "is this even classification?" line of questioning start. Fix: one early, explicit paragraph stating task type, input/output space, and the 4-class label set, before any architecture discussion.
3. **Unjustified architectural choice reads as either not having considered alternatives or not understanding your own design.** Fix: explicit comparative-rationale subsections (classification-head alternative; PhoBERT alternative) with concrete tradeoffs, not just description of what was built.
4. **Cross-document numeric inconsistency (confusion matrix vs. split counts) functions as a fabrication tell even when work is genuine**, because it's exactly what a copy-pasted-without-understanding error looks like. This must be audited and reconciled — state train/val/test counts once, consistently, referenced everywhere else.
5. **The burden of proof for "did you do this yourself" is evidentiary, not stylistic.** The judge explicitly said AI-assisted drafting is acceptable *if* genuine understanding can be demonstrated. Do not change tone/register — add traceable artifacts (schema tables, real example records, pipeline-specific detail only the author would know, first-person worked examples, explicit rejected-alternatives reasoning). Padding already-strong sections is counterproductive and reads as evasive.

## Implications for Roadmap

This is a **report-revision milestone**, not a software build. "Phases" below are revision work packages, sequenced by dependency and by directly answering the transcript's ordering of complaints.

### Phase 1: Problem Framing & Structural Fixes
**Rationale:** The judge's very first complaint ("we are missing... the Goal: Supervised classification") is what let every downstream question spiral. Cheap, load-bearing, should exist before other new content references it.
**Delivers:** An explicit, early "Problem Formalization" subsection: task type, input/output space, the 4-class taxonomy named and briefly defined.
**Addresses:** FEATURES.md components #1 (problem framing) and #2 (class taxonomy).
**Avoids:** PITFALLS.md #2 (missing problem formalization).

### Phase 2: Architecture Rationale (QLoRA-as-Classification & Qwen-vs-PhoBERT)
**Rationale:** Both architecture questions were asked live and unanswered in text; they share one underlying argument (unified generation vs. coupled/bolted-on mechanisms), so should be written together.
**Delivers:** Two new subsections — "Why Generative Classification, Not a Classification Head" and "Why Qwen, Not PhoBERT" (task-shape as primary argument, multilingual as secondary, honest tradeoff table).
**Uses:** STACK.md citation set (verbalizer, T5, Yousefiramandi & Cooney, WT5) and ARCHITECTURE.md's task-shape comparison and tradeoff table.
**Avoids:** PITFALLS.md #3 and the live contradiction (English-extension answer undermined by Vietnamese-only scope).

### Phase 3: Dataset Construction and Labeling Methodology
**Rationale:** The single most-repeated transcript gap (~10 times) and most directly tied to the "did you use ChatGPT" accusation. Depends on Phase 1's taxonomy and benefits from Phase 2's terminology.
**Delivers:** New subsection per FEATURES.md's 9-part structure: problem/taxonomy pointers, provenance/generation pipeline, full JSON schema listing + field table, explicit "labels assigned at generation time" statement with ZeroGen/condition-on-label citations, quality-control gate description, class distribution table, train/val/test split methodology (with val/test vs. train label-necessity distinction stated explicitly), SHA-256 integrity sentence, and a first-person worked-example walkthrough.
**Addresses:** PITFALLS.md #1 (locatability) directly.

### Phase 4: Consistency Audit & Ownership-Evidence Pass
**Rationale:** Must come last — audits numbers across all sections (including new ones) and adds evidentiary/ownership content that references material now in place.
**Delivers:** (a) Reconciled confusion-matrix and train/val/test counts stated once and referenced consistently across report, tables, and slides; (b) short error-analysis subsection with 2–3 concrete worked misclassification examples; (c) verification that new content matches `WRITING_GUARDRAILS.md` voice and does not touch/pad already-strong sections.
**Avoids:** PITFALLS.md #4 and the anti-pattern of padding working sections.

### Phase Ordering Rationale

- Phase 1 before all others: every later phase's writing implicitly assumes the reader already knows "this is supervised 4-class classification."
- Phase 2 before Phase 3: the labeling section reads more rigorously once the verbalizer/generative-classification vocabulary is already established.
- Phase 4 last by necessity: it audits and cross-references everything written or already present; ownership-evidence content is most credible once the substantive gaps it reinforces already exist.
- This ordering mirrors the transcript's own sequence of escalating judge frustration (classification framing → architecture choice → labeling → "show me the dataset" → numeric inconsistency → AI-authorship accusation).

### Research Flags

Needs additional verification during execution (not literature research):
- **Phase 2:** Verify the specific Qwen-vs-PhoBERT technical claims (e.g., code-switched Vietnamese-English handling) against what is actually true for this project's data before writing — flagged explicitly in ARCHITECTURE.md as unverified.
- **Phase 4:** Requires pulling actual numbers from existing eval artifacts/code (confusion matrix, split counts) — empirical verification, not literature research.

Standard patterns, research already sufficient:
- **Phase 1:** Well-established, uncontested convention; no further research needed.
- **Phase 3:** Structure, citations, and precedent are fully resolved in FEATURES.md — ready to write directly.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack (terminology/precedent) | MEDIUM-HIGH | All claims traced to arXiv/peer-reviewed sources; not Context7-curated docs, but every citation is checkable and several were directly fetched and read in full. |
| Features (methodology-section content) | MEDIUM | Structural checklist corroborated by a canonical reference (Datasheets for Datasets) plus multiple synthetic-data-generation papers; length-calibration guidance is LOW (generic web advice). |
| Architecture (Qwen vs. PhoBERT) | MEDIUM-HIGH | Cross-checked against arXiv papers, official PhoBERT repo/paper, and Qwen3 technical report (primary sources); one comparison source flagged as not like-for-like, used only as directional color. |
| Pitfalls (revision-process risks) | MEDIUM-HIGH | Grounded directly in the actual defense transcript (primary source); general academic-integrity guidance cross-checked against multiple sources but not USTH-specific policy. |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

- **Project-specific verification of Qwen-vs-PhoBERT claims** (e.g., actual code-switched Vietnamese-English text presence) — confirm against real data before finalizing Phase 2 text.
- **Actual numeric reconciliation of confusion matrix vs. train/val/test counts** was not performed by research agents (out of scope) — must happen during Phase 4 by inspecting real eval artifacts/code.
- **USTH-specific thesis-length/formatting policy** not found (only generic guidance, LOW confidence) — check separately if an institutional requirement exists.
- **Supervisor/department revision requirements** — confirm current institutional deadline/requirements are captured in `.planning/PROJECT.md` before treating this research as complete scope guidance.

## Sources

### Primary (HIGH confidence)
- `documents/Transcript defense.md` — ground truth for every gap identified.
- Raffel et al. (2020), T5, JMLR 21(140).
- Schick & Schütze (2021), PET, EACL.
- Gebru et al. (2018), "Datasheets for Datasets," arXiv:1803.09010.
- PhoBERT (VinAI, EMNLP 2020 Findings) and official GitHub repo.
- Qwen3 Technical Report (arXiv:2505.09388) and QwenLM/Qwen3 GitHub.
- BARTpho (arXiv:2109.09701).

### Secondary (MEDIUM confidence)
- Yousefiramandi & Cooney (2025), arXiv:2512.12677.
- Narang et al. (2020), WT5, arXiv:2004.14546.
- Ye et al. (2022), ZeroGen, EMNLP.
- "Data Generation using LLMs for Text Classification," arXiv:2407.12813.
- "Garbage In, Garbage Out?", arXiv:1912.08320 / arXiv:2107.02278.
- "A Culturally Aware LLM Framework for Analyzing Social Engineering Tactics in Korean Phishing Messages," Electronics 15(10), 2196 (2026).
- Editorial-policy/AI-assisted-writing ethics reviews (PMC12170296, PMC12007126, openpraxis.org/10.55982/openpraxis.16.1.654).

### Tertiary (LOW confidence)
- General bachelor-thesis length guidance (non-institution-specific).
- GPT-3.5-turbo vs. PhoBERT comparison (Springer chapter) — not like-for-like.
- LaTeX `lstlisting`/JSON listing convention — standard/uncontested.

---
*Research completed: 2026-07-21*
*Ready for roadmap: yes*
