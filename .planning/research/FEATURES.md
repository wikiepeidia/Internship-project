# Expected Methodology Section Content Research

**Context:** v6.0 report revision — judges asked, in roughly ten phrasings, where the dataset's training labels were documented. The actual data has a `label` field on every JSONL record; the report never made the schema and labeling methodology explicit or findable. This file researches what a rigorous "dataset construction and labeling" section normally contains, for a **synthetically generated** (LLM-authored, not manually annotated) multi-class dataset, so the student can write a new section in the existing report voice.

**Researched:** 2026-07-21
**Confidence:** MEDIUM overall — the structural/precedent claims are corroborated across multiple independent sources (a canonical, 3000+-citation reference paper plus multiple peer-reviewed synthetic-data-generation papers); LOW-confidence items (general web summaries, LaTeX convention blog posts) are flagged individually.

## Standard Components Checklist

These are the components examiners expect to find, explicitly labeled, in a "Dataset Construction and Labeling" (or equivalent) subsection of a Data/Methodology chapter. This checklist is synthesized primarily from **Datasheets for Datasets** (Gebru et al., 2018, arXiv:1803.09010) — the field's standard reference for what a dataset description must disclose — adapted to thesis-chapter form rather than a standalone datasheet appendix.

| # | Component | What examiners are checking for | Confidence |
|---|-----------|----------------------------------|------------|
| 1 | **Explicit problem framing statement** | A single unambiguous sentence stating the task type before any data discussion: "This is a supervised multi-class text classification problem with 4 classes: [list]." Must appear *before* the dataset section, not be inferable from it. This is the #1 miss flagged in this project's defense — a judge said "we are missing this in report, the Goal: Supervised classification" was never stated. | HIGH (directly corroborated by defense transcript + is the standard opening move of every classification paper's Methods section) |
| 2 | **Class/label taxonomy definition** | A short definition of what each class *means* semantically (not just a list of string names) — e.g. what distinguishes "bank_impersonation" from "account_takeover" conceptually, with a boundary case noted if two classes could plausibly overlap. | HIGH |
| 3 | **Explicit schema definition** | A canonical example record (JSON) shown as a figure/listing, with every field named and explained, ideally in a table. Must include the field that carries the label explicitly identified as *the* training signal. | HIGH — this is literally what the judges asked for and could not find |
| 4 | **Label assignment / construction methodology** | A dedicated paragraph or subsection stating *how* each record came to have the label it has — for a synthetic dataset, this means stating explicitly that generation was label-conditioned (see Synthetic-Dataset Labeling Precedent below), not a downstream annotation pass. | HIGH |
| 5 | **Data source / provenance statement** | Where seed material came from (this project: NCSC-sourced seed threats), and what portion of the final corpus is synthetic vs. seed-derived — stated as a number/percentage, not implied. | HIGH |
| 6 | **Generation methodology** | Model/API used to generate synthetic examples, prompt strategy (e.g., one prompt template per target class, temperature/sampling settings if relevant), and how diversity was encouraged (topic variation, seed variation, etc.). | HIGH |
| 7 | **Quality control / validation methodology** | How generated examples were filtered or judged before inclusion — LLM-as-judge passes, schema validation (Pydantic gate, in this project's case), deduplication, manual spot-checks. State pass/fail/reject counts if available. | HIGH |
| 8 | **Class distribution table** | A table showing sample counts per class (and per split), so an examiner can see the data is not degenerate/imbalanced without inspection, and so any imbalance is acknowledged rather than hidden. | HIGH |
| 9 | **Train/validation/test split methodology** | Split ratios, whether the split was stratified by class, whether it was done before or after quality filtering, and the resulting counts per split per class. Explicitly state this is disclosed for the *training* label field vs. what val/test need (a judge specifically flagged: "for val, test you dont need [a label] but for training you need it" — meaning the concern was really about whether train examples had recoverable, explicit labels, which they do). | HIGH — directly responsive to the transcript's repeated question |
| 10 | **Integrity / reproducibility statement** | How the frozen dataset artifact is verified (this project: SHA-256 manifest) — a short, explicit sentence, not just a technical implementation detail assumed to speak for itself. | HIGH (already partially present per PROJECT.md; needs a crisper explicit sentence) |
| 11 | **Worked example walkthrough** | Optional but strong: take one concrete record end-to-end — "raw input text -> generation prompt with target label X -> resulting record with label=X, risk_tier=Y, spans=Z" — so the reader (or a judge) can trace the labeling logic without needing the code. | MEDIUM — not in every paper, but is the single most defense-proofing addition given exactly this was demanded live and the student "barely manage[d] to find it" reading from code |

## Synthetic-Dataset Labeling Precedent

**Core finding: "generated FOR a target class, so the label is assigned at generation time by construction" is not just defensible — it is the standard, textbook framing in the LLM-synthetic-data-for-classification literature, usually called "condition on the label."** This is well precedented and citable.

### Precedent 1 — ZeroGen (Ye et al., "ZeroGen: Efficient Zero-shot Learning via Dataset Generation," EMNLP 2022)

One of the most-cited papers establishing this pattern for zero-shot dataset generation via LLMs. Its pipeline is exactly this project's shape:
1. A **pseudo-label is sampled** from the target class distribution *before* generation.
2. That label is inserted into a **task-specific prompt template**.
3. The generator model (a large PLM) produces text **conditioned on** that label.
4. **"The final dataset is composed of these generated (text, label) pairs"** — the label is not inferred afterward; it is the generation target.

This is the cleanest possible citable precedent for "label assigned at generation time, by construction" — it is literally the field's name for this technique.

### Precedent 2 — "Data Generation using Large Language Models for Text Classification: An Empirical Case Study" (arXiv:2407.12813, 2024)

This paper explicitly compares two prompting strategies and recommends the one this project effectively used:

- **"Condition on the Label"**: *generate an example text where the label must be Class X* — label fixed before generation.
- **"Left-to-right prompt"**: generate the text first, infer/generate its label afterward (a post-hoc pattern).

The paper's own recommendation: *"It is recommended to use Condition on the Label for each generation as it saves effort in parsing the label and avoids the LLM generating unknown labels [and] provides the user control over the label distribution in the synthetic dataset."*

This gives the student a direct, citable methodological justification sentence they can adapt, e.g.: *"Following the label-conditioned generation approach established in synthetic data generation literature (Ye et al., 2022; [2407.12813 authors], 2024), each synthetic record was generated with its target class fixed as part of the generation prompt, rather than labeled post-hoc. This guarantees label correctness by construction and avoids the risk of the generator producing an off-target or ambiguous example that a separate labeling pass would then have to adjudicate."*

### Precedent 3 — TarGEN (Gupta et al., "TarGEN: Targeted Data Generation with Large Language Models," arXiv:2310.17876)

Another well-known targeted-generation paper in the same family; useful as a second citation if the student wants to show the pattern isn't a one-off (strengthens the "this is standard practice" framing an examiner skeptical of AI-authorship will respond well to).

### Why this precedent directly defuses the defense's core objection

The judges' central confusion (re-read against the transcript) was **not** that generation-time labeling is illegitimate — it was that **the report never stated the mechanism at all**, so from the outside it looked like there was *no* labeling methodology, which is what triggered "did you use ChatGPT to construct the thesis" and "did someone else do this for you." The fix is not a methodological change (the underlying approach — generate-for-class — is already correct and standard) — it is making the *existing* mechanism explicit, named, and cited against precedent, exactly as above.

## Recommended Schema Presentation Format

Two complementary elements, used together (not either/or):

1. **A `lstlisting` (or `listings`/`minted`) code block with `language=json`**, syntax-highlighted, wrapped in a numbered `figure` or `listing` float with a proper caption — e.g. *"Listing 3.1: Example training record from the synthetic dataset."* This is the standard LaTeX-thesis convention for showing real data structures as documentation rather than a raw code dump (confirmed by LaTeX thesis-template packages and multiple thesis style guides using `\lstinputlisting`/`lstlisting` with captions for this exact purpose). Show one **complete real record**, not a truncated one, so the `label` field is visibly present with its actual value (e.g., `"label": "bank_impersonation"`).
2. **A schema table directly below or beside the listing**, one row per field, columns: `Field`, `Type`, `Meaning`, `Example value`. This is what turns the listing from "here is some JSON" into documentation — it lets the reader map every field to its role without parsing JSON syntax themselves. The `label` row should have its `Meaning` column explicitly say something like *"the ground-truth training class assigned at generation time (see §X for methodology)"* — this single row, if it had existed, would likely have prevented the entire defense exchange.

Recommended field breakdown for this project's actual schema (bank_impersonation example, per PROJECT.md):

| Field | Type | Meaning |
|---|---|---|
| `text` | string | The synthetic (or seed-derived) message text presented to the model as input |
| `label` | enum (4 classes) | **The ground-truth training class**, fixed at generation time via the label-conditioned prompt — this is the supervised training target |
| `risk_tier` | enum | Severity/urgency tier used for the recall-first release framing, separate from the class label |
| `suspicious_spans` | array | Character/phrase spans grounding *why* the message is suspicious — supports the explainability output, not the classification label itself |
| `xai_explanation` | string | Natural-language rationale generated alongside the record, used to train the explanation-generation behavior |
| `source` | string | Provenance tag (e.g. `synthetic_claude`) — distinguishes generation origin, supports the reproducibility/integrity narrative |
| `seed_id` | string | Traceability back to the NCSC seed record that inspired this synthetic example, where applicable |

A short worked-example paragraph directly under the table (see Standard Components #11) is worth including here: walk through one record and narrate "this record was generated by prompting the model to produce a bank-impersonation-style message; the resulting `label` field is `bank_impersonation` because that was the class the generation call targeted, not because it was labeled afterward."

## Recommended Section Structure

Proposed as a new subsection inside the existing Data/Methodology chapter — sized to run roughly 3-5 pages of substantive content (see length calibration note below), matching the depth of an already-present QLoRA config subsection in this report per PROJECT.md history.

```
3.X Dataset Construction and Labeling Methodology

  3.X.1 Problem Framing
      - One explicit paragraph: supervised multi-class text classification,
        4 classes, stated before any data discussion.

  3.X.2 Class Taxonomy
      - Definition of each of the 4 classes with a short example and
        boundary note vs. adjacent classes.

  3.X.3 Data Provenance and Generation Pipeline
      - NCSC seed sourcing -> synthetic expansion via [model] ->
        target sample count, with synthetic-vs-seed percentage stated.

  3.X.4 Record Schema
      - Listing (full JSON example record) + field-by-field table
        (as above), with the label field's role called out explicitly.

  3.X.5 Label Assignment Methodology  <-- the section that was missing
      - States plainly: labels are assigned AT GENERATION TIME, not
        via a separate manual/statistical labeling pass, because each
        record is generated FOR a target class via a label-conditioned
        prompt.
      - Cites precedent (ZeroGen / condition-on-label literature) to
        show this is standard practice, not an ad hoc shortcut.
      - One short worked example walking a single record end-to-end.

  3.X.6 Quality Control and Validation
      - Judge/validation pass (the "Pydantic Judge" gate), what it
        checks, reject/accept counts if available.

  3.X.7 Class Distribution
      - Table: sample count per class, and per split.

  3.X.8 Train/Validation/Test Split
      - Ratios, whether stratified, resulting counts, and an explicit
        note that val/test do not require the generation-time label
        assumption to hold in the same way training does (directly
        answers the judge's "for val/test you dont need but for
        training you need it" line).

  3.X.9 Integrity Verification
      - SHA-256 manifest — one crisp explicit sentence on what it
        guarantees and why it matters for a frozen dataset artifact.
```

This structure maps 1:1 onto every gap PROJECT.md's Active requirements list flags for this milestone (labeling section, explicit classification framing, SHA-256 rationale), so it can be dropped in without restructuring the rest of the chapter.

## Length Calibration

- General bachelor thesis guidance: whole theses commonly run 40-60 pages (range ~30-80), varying heavily by field/institution — not narrowly prescriptive for a single chapter. Confidence: LOW (generic web guidance, not USTH-specific).
- More useful signal: **the judges' complaint was concrete and specific** — "if you remove conclusion, table of content etc, it is only somehow 14 pages" of substantive content, called "too short" independently by two judges. The fix target is not a page-count number in isolation but **closing the named content gaps with real depth**: the 9-subsection structure above, if written with the same density as this project's existing QLoRA-config subsection (which already includes an equation, a config table, and hardware rationale per PROJECT.md's v1.5 milestone log), would plausibly add on the order of 3-5 pages by itself, and the other requested additions (classification framing, QLoRA-vs-classification-head justification, Qwen-vs-PhoBERT comparison) would each plausibly add 0.5-1.5 pages if done with genuine substance (tables, cited comparisons, worked examples) rather than a paragraph each.
- The operative principle from the transcript itself: *"try to improve it if you do by yourself"* — the judges' real ask was findable, explicit, cited substance, not padding. Page count should be a byproduct of closing the named gaps, not a target pursued independently.

## Sources

- **Datasheets for Datasets** (Gebru et al., 2018) — https://arxiv.org/pdf/1803.09010 — HIGH confidence (canonical, foundational reference for dataset documentation structure; used here for the "standard components" checklist)
- **ZeroGen: Efficient Zero-shot Learning via Dataset Generation** (Ye et al., 2022) — https://arxiv.org/pdf/2202.07922 / summarized via https://dmytro-kuzmenko.medium.com/overview-zerogen-efficient-zero-shot-learning-via-dataset-generation-8ebca0c72620 — MEDIUM confidence (well-cited EMNLP paper; direct precedent for label-conditioned generation)
- **Data Generation using Large Language Models for Text Classification: An Empirical Case Study** — https://arxiv.org/html/2407.12813v1 — MEDIUM confidence (directly fetched and read; explicit "Condition on the Label" vs. "Left-to-right prompt" framing and recommendation)
- **TarGEN: Targeted Data Generation with Large Language Models** — https://arxiv.org/pdf/2310.17876 — LOW-MEDIUM confidence (found via search, not directly read in full; offered as a secondary citation)
- **Synthetic Data Generation with Large Language Models for Text Classification: Potential and Limitations** — https://arxiv.org/pdf/2310.07849 — LOW confidence (abstract-level only; full methodology not verified in this session)
- LaTeX `lstlisting`/JSON listing convention — general search corroboration (LaTeX thesis template repos, texdoc listings package documentation) — LOW confidence, standard/uncontested convention rather than a single authoritative source
- General bachelor-thesis length guidance (multiple thesis-writing advice sites) — LOW confidence, generic, non-institution-specific
- `documents/Transcript defense.md` (this repo) — HIGH confidence, primary source; used to ground every recommendation directly in what the judges actually asked and where the student's answer failed
- `.planning/PROJECT.md` (this repo) — HIGH confidence, primary source for current milestone scope and constraints
