# Architecture: LaTeX File Layout — Department Template Compliance

**Scope:** Phase 22+ LaTeX restructure  
**Researched:** 2026-06-15  
**Compiler:** XeLaTeX  
**Document class:** `report` (kept — `\chapter` infrastructure retained)

---

## Target File Tree

```
documents/reports/latex/
├── main.tex                                        ← full rewrite (orchestrator)
├── references.bib                                  ← unchanged
├── chapters/
│   ├── frontmatter/
│   │   ├── titlepage.tex                           ← keep (minor text edits only)
│   │   ├── certification.tex                       ← NEW: certification/declaration page
│   │   ├── abbreviations.tex                       ← NEW: List of Abbreviations table
│   │   └── abstract.tex                            ← NEW: extracted from preface.tex + 6 keywords
│   ├── body/
│   │   ├── I_introduction.tex                      ← MERGED: 01 (minus Objectives) + full 02
│   │   ├── II_objectives.tex                       ← SPLIT OUT: Objectives section from 01
│   │   ├── III_materials_and_methods.tex           ← MERGED: full 03 + full 04
│   │   ├── IV_results_and_discussion.tex           ← COPY: 05 (heading change only)
│   │   └── V_conclusion_and_perspective.tex        ← COPY: 06 (heading change only)
│   └── appendices/
│       └── appendices.tex                          ← NEW: appendix content
├── figures/                                        ← unchanged
└── tables/                                         ← unchanged
```

### New Files to Create (5)

| File | Purpose |
|------|---------|
| `chapters/frontmatter/certification.tex` | Certification/declaration page with supervisor signature block — required by department |
| `chapters/frontmatter/abbreviations.tex` | Acronym table: AI, NLP, LLM, LoRA, QLoRA, GGUF, OTP, SMS, F1, NF4, CUDA, CLI, API, SHA, OCR |
| `chapters/frontmatter/abstract.tex` | Existing abstract paragraph moved from `preface.tex`, plus a `\textbf{Keywords:}` line with 6 terms |
| `chapters/body/` (directory + 5 files) | Holds the five roman-numeral body sections under clean filenames |
| `chapters/appendices/appendices.tex` | Appendix section (training config detail, sample annotated outputs, etc.) |

### Source File Disposition

| Old File | Action | Destination |
|----------|--------|-------------|
| `chapters/frontmatter/preface.tex` | Gutted — Abstract and Ack blocks extracted; TOC/LoF/LoT infrastructure absorbed into `main.tex` | Mark `%% DEPRECATED` at top; do not delete until compile verified |
| `chapters/01_introduction.tex` | Split: drop "Report Organization", move "Objectives and Scope" to II/, merge remainder into I/ | Keep as dead file until Phase 22 compile passes |
| `chapters/02_related_work_and_background.tex` | Merge entire file into I/ after the ch01 content | Keep as dead file |
| `chapters/03_methodology_and_system_design.tex` | Merge entire file into III/ | Keep as dead file |
| `chapters/04_implementation.tex` | Merge entire file into III/ after ch03 content | Keep as dead file |
| `chapters/05_evaluation_and_discussion.tex` | Verbatim copy to IV/ (remove `\chapter{...}` line only) | Keep as dead file |
| `chapters/06_conclusion_and_future_work.tex` | Verbatim copy to V/ (title changes to "Conclusion and Perspective") | Keep as dead file |

**Rule:** Do NOT delete old `01`–`06` chapter files until the restructured `main.tex` compiles cleanly to PDF and has been visually spot-checked. Mark them `%% DEPRECATED — superseded Phase 22` and leave them in-place as a rollback safety net. Delete in a separate commit after confirmation.

---

## `main.tex` New `\input` Order

Replace everything between `\begin{document}` and `\end{document}` with:

```latex
\begin{document}

%% ── FRONT MATTER (roman page numbers) ───────────────────────────────────────
\pagenumbering{roman}

\input{chapters/frontmatter/titlepage}         % cover page — no printed number
\clearpage

\input{chapters/frontmatter/certification}     % certification/declaration page
\clearpage

\chapter*{Acknowledgements}
\addcontentsline{toc}{chapter}{Acknowledgements}
\markboth{Acknowledgements}{Acknowledgements}
[Acknowledgements text here, or \input a separate ack.tex]
\clearpage

{\singlespacing\tableofcontents}
\clearpage

\input{chapters/frontmatter/abbreviations}
\clearpage

{\singlespacing
  \addcontentsline{toc}{chapter}{\listtablename}
  \listoftables
}
\clearpage

{\singlespacing
  \addcontentsline{toc}{chapter}{\listfigurename}
  \listoffigures
}
\clearpage

\input{chapters/frontmatter/abstract}          % abstract + 6 keywords

\cleardoublepage
\pagenumbering{arabic}

%% ── BODY (arabic page numbers, roman-numeral headings) ───────────────────────
\input{chapters/body/I_introduction}
\input{chapters/body/II_objectives}
\input{chapters/body/III_materials_and_methods}
\input{chapters/body/IV_results_and_discussion}
\input{chapters/body/V_conclusion_and_perspective}

%% ── BACK MATTER ──────────────────────────────────────────────────────────────
\renewcommand{\bibname}{References}
\bibliography{references}

\appendix
\input{chapters/appendices/appendices}

\end{document}
```

**Notes on order:**
- Acknowledgements appears before TOC per standard academic convention (USTH format matches this).
- List of Abbreviations immediately after TOC, before LoT/LoF — mirrors the milestone target order.
- LoT appears before LoF (as specified in the milestone context).
- `\cleardoublepage` before `\pagenumbering{arabic}` ensures body always starts on a recto page.

---

## Roman Numeral Heading Approach

### Decision: `\chapter*` with a `\thesissection` helper command

**Do NOT redefine `\chapter` globally.** The `report` class chapter counter drives figure and table caption numbering (e.g., "Figure 3.2"). Replacing `\thechapter` with `\Roman{\thechapter}` would corrupt all auto-numbered captions to "Figure III.2" format and break the existing `fig:`, `tab:`, and `eq:` cross-references throughout the document.

The correct approach is unnumbered chapters (`\chapter*`) with a one-time helper macro that:
1. Emits the correct visual heading
2. Adds a manual TOC entry at chapter indent level
3. Sets `\leftmark` for the running page header (required — `\chapter*` does not update `\leftmark` automatically)

**Add this block to `main.tex` preamble**, after the existing `\usepackage{titlesec}` and `\pagestyle{fancy}` setup:

```latex
%% ── Roman-numeral thesis section headings (Phase 22) ─────────────────────────
%% Usage: \thesissection{I}{Introduction}
%%   - emits unnumbered chapter heading "I/ Introduction"
%%   - adds TOC entry at chapter level
%%   - sets running header via \markboth
\newcommand{\thesissection}[2]{%
  \chapter*{#1/ #2}%
  \addcontentsline{toc}{chapter}{#1/ #2}%
  \markboth{#1/ #2}{#1/ #2}%
}
```

**Usage inside each body file** — the body files contain NO `\chapter{}` or `\chapter*{}` calls; heading emission is the caller's responsibility via `main.tex`:

```latex
%% Option A: emit heading from within the body file (simpler, more self-contained)
\thesissection{I}{Introduction}

\section{Background and Motivation}
...
```

```latex
%% Option B: emit heading from main.tex immediately before \input (alternative)
\thesissection{III}{Materials and Methods}
\input{chapters/body/III_materials_and_methods}
```

Option A (heading inside the body file) is preferred: it keeps each file self-contained and makes the PDF reproducible even if the file is compiled in isolation during editing.

**Why this approach wins over all alternatives:**

| Approach | Problem |
|----------|---------|
| Redefine `\chapter` to prepend `\Roman{\thechapter}/` | Breaks figure/table caption numbering; "Fig 3.2" becomes "Fig III.2" |
| Pure `\chapter*` with `\addcontentsline` repeated manually | Must remember 3-line boilerplate every time; `\markboth` gets forgotten, header shows stale text |
| Switch to `book` class | Introduces `\part` above `\chapter`; needless structural change; page margins differ |
| Use `titlesec` `\titleformat` with `\Roman` counter | Same counter-corruption problem as redefining `\chapter` |
| Use `\section` at top level (demote everything) | Breaks LoF/LoT; figures become "Figure 0.1" without a chapter counter |

**`titlesec` interaction:** The existing `\titleformat{\chapter}` definition applies to both `\chapter` and `\chapter*` in `titlesec`. The roman-numeral headings will inherit the same compact spacing (`-20pt` top, `10pt` bottom, `\LARGE` font) automatically. No additional `\titleformat` change is needed.

**`tocloft` interaction:** The existing `\setcounter{tocdepth}{1}` already limits TOC to chapter+section depth. The `\addcontentsline{toc}{chapter}{...}` call inside `\thesissection` places the roman-numeral entry at chapter indent level, matching all other chapter entries. No `tocloft` parameter changes needed.

---

## Content Mapping: What Moves Where

### I/ Introduction (`chapters/body/I_introduction.tex`)

Sources:
- `01_introduction.tex`: "Background and Motivation" and "Problem Statement" sections
- `02_related_work_and_background.tex`: all 5 sections (Vietnamese Phishing Context, Local Inference as Privacy Control, Explainability and User-Facing Safety, Open-Weight Local Models, Evaluation Priorities)

Exclusions:
- "Objectives and Scope" from ch01 moves to II/
- "Report Organization" from ch01 is deleted (see Cross-References below)

### II/ Objectives (`chapters/body/II_objectives.tex`)

Sources:
- "Objectives and Scope" section from `01_introduction.tex` — copy verbatim

### III/ Materials and Methods (`chapters/body/III_materials_and_methods.tex`)

Sources (in order):
1. All of `03_methodology_and_system_design.tex` (Development Structure, Data Construction, Offline Runtime, Local Model Selection, Explainability, Design Principles)
2. All of `04_implementation.tex` (Codebase Organization, Data Pipeline Implementation, Runtime Implementation, Model Adaptation Implementation)

The `\section{}` headings from both files coexist cleanly under one unnumbered chapter with no naming conflicts.

### IV/ Results and Discussion (`chapters/body/IV_results_and_discussion.tex`)

Source: verbatim copy of `05_evaluation_and_discussion.tex` body content. Remove only the `\chapter{Evaluation and Discussion}` line. All `\input{tables/...}` and `\input{figures/...}` calls are preserved unchanged.

### V/ Conclusion and Perspective (`chapters/body/V_conclusion_and_perspective.tex`)

Source: verbatim copy of `06_conclusion_and_future_work.tex` body content. Remove only the `\chapter{Conclusion and Future Work}` line. The roman-numeral heading "V/ Conclusion and Perspective" replaces it via `\thesissection` in the file header.

---

## Cross-Reference Handling

### `\label` / `\ref` audit — zero breakage risk

All `\label` definitions are in figure/table fragment files (`figures/*.tex`, `tables/*.tex`) or inline in content that stays co-located. Every label and the `\ref{}` that references it moves into the same merged body file. No cross-boundary ref exists.

| Label | Defined in | Referenced in | After restructure |
|-------|-----------|---------------|-------------------|
| `tab:confusion-matrix` | `tables/confusion_matrix.tex` | ch05 | Both in IV/ — safe |
| `tab:dataset-stats` | `tables/dataset_statistics.tex` | ch03 | Both in III/ — safe |
| `fig:cloud-vs-local-flow` | `figures/cloud_vs_local_dataflow.tex` | ch02 | Both in I/ — safe |
| `tab:evaluation-snapshot` | `tables/evaluation_snapshot.tex` | ch05 | Both in IV/ — safe |
| `fig:system-overview` | `figures/system_overview_placeholder.tex` | ch03 | Both in III/ — safe |
| `tab:milestone-summary` | `tables/milestone_summary.tex` | ch03 | Both in III/ — safe |
| `eq:qlora-forward` | `03_methodology_and_system_design.tex` inline | same file | Stays in III/ — safe |
| `tab:pilot-comparison` | `tables/pilot_comparison.tex` | ch03 | Both in III/ — safe |
| `fig:runtime-flow` | `04_implementation.tex` inline | same file | Stays in III/ — safe |
| `fig:recall-by-class` | `figures/recall_barchart.tex` | ch05 | Both in IV/ — safe |
| `tab:qlora-config` | `tables/qlora_config.tex` | ch03 | Both in III/ — safe |

### Prose "Chapter~N" references that will break

These are hardcoded text strings, NOT `\ref{}` commands. LaTeX cannot auto-update them. Three must be manually fixed:

| File | Text | Fix |
|------|------|-----|
| `01_introduction.tex` ("Report Organization" section) | "Chapter~2 summarizes… Chapter~3 presents… Chapter~4 maps… Chapter~5 reports… Chapter~6 closes…" | Delete the entire "Report Organization" section. It is meaningless after merges and adds no value in the new structure. |
| `04_implementation.tex` (line ~126) | "…discussed in Chapter~5." | Add `\label{sec:iv-results}` at the top of IV/ section "Expanded-Holdout Results". Change prose to `"…discussed in Section~\ref{sec:iv-results}."` |
| `06_conclusion_and_future_work.tex` | "error analysis in Chapter~5" | Change to `"error analysis in Section~\ref{sec:iv-results}."` using the same label. |

**Standing rule for new text:** Replace all future "Chapter~N" prose with `\nameref{sec:...}` or descriptive section-name prose ("see Results and Discussion") to survive any future restructure without breakage.

### Label naming convention for new sections

Use `sec:` prefix to avoid namespace collisions with existing `fig:`, `tab:`, `eq:` labels:
- `\label{sec:objectives-scope}` at the top of `II_objectives.tex`
- `\label{sec:iv-results}` at the start of the "Expanded-Holdout Results" section in IV/

---

## New Frontmatter Files: Content Templates

### `certification.tex`

```latex
% chapters/frontmatter/certification.tex
\thispagestyle{empty}
\begin{center}
  {\Large\bfseries CERTIFICATION\par}
\end{center}
\vspace{1.5cm}

I hereby certify that the work presented in this thesis entitled
\textit{``Localized Explainable AI Engine for Vietnamese Financial Phishing Detection''}
is my own original work carried out under the supervision of
\textbf{Giang Anh Tuan} (internal supervisor) and
\textbf{Nguyen Viet Anh} (external supervisor),
and has not been submitted for any other degree or professional qualification.

\vspace{3cm}
\begin{flushright}
  Hanoi, \today\\[2cm]
  \underline{\hspace{5cm}}\\
  Ph\d{a}m Th\d{e} Minh\\
  Student ID: 23BI14279
\end{flushright}
\clearpage
```

Adjust wording to match any exact department-provided text if a Word template exists. The structure above is a reasonable draft; treat as LOW confidence until verified against the department's official template.

### `abbreviations.tex`

```latex
% chapters/frontmatter/abbreviations.tex
\chapter*{List of Abbreviations}
\addcontentsline{toc}{chapter}{List of Abbreviations}
\markboth{List of Abbreviations}{List of Abbreviations}
\begin{tabular}{@{}lp{10cm}@{}}
  AI    & Artificial Intelligence \\
  NLP   & Natural Language Processing \\
  LLM   & Large Language Model \\
  LoRA  & Low-Rank Adaptation \\
  QLoRA & Quantized Low-Rank Adaptation \\
  GGUF  & GPT-Generated Unified Format (llama.cpp model format) \\
  OTP   & One-Time Password \\
  SMS   & Short Message Service \\
  F1    & F1-Score (harmonic mean of precision and recall) \\
  NF4   & Normal Float 4-bit quantization \\
  CUDA  & Compute Unified Device Architecture \\
  CLI   & Command-Line Interface \\
  API   & Application Programming Interface \\
  SHA   & Secure Hash Algorithm \\
  OCR   & Optical Character Recognition \\
\end{tabular}
\clearpage
```

### `abstract.tex`

```latex
% chapters/frontmatter/abstract.tex
\chapter*{Abstract}
\addcontentsline{toc}{chapter}{Abstract}
\markboth{Abstract}{Abstract}

[Paste existing abstract paragraph from preface.tex here verbatim]

\medskip
\noindent\textbf{Keywords:} Vietnamese financial phishing, explainable AI,
local inference, LoRA fine-tuning, privacy-preserving NLP, phishing detection.
\clearpage
```

---

## Safe Restructure Sequence

Execute in this order. Compile after every step. Do not proceed to the next step if the compile produces errors or unexpected warnings.

**Step 1 — Preamble-only change (zero content risk)**

Add `\newcommand{\thesissection}` to `main.tex` preamble. Compile existing `main.tex`. Verify clean compile. This is an additive-only change; nothing existing is touched.

**Step 2 — Create new frontmatter files without wiring them in**

Create `certification.tex`, `abbreviations.tex`, `abstract.tex` with their content. Do NOT yet reference them from `main.tex`. Compile unchanged `main.tex`. Verify it still compiles (unused files have no effect).

**Step 3 — Create `chapters/body/` stub files and a shadow `main_new.tex`**

Create stub body files with only their `\thesissection{X}{...}` call and a `% TODO: migrate content` comment. Create `main_new.tex` as a copy of `main.tex` that `\input`s the new body stubs instead of the old chapters. Compile `main_new.tex`. Verify the five roman-numeral headings appear in the PDF TOC with correct entries. Fix any `\thesissection` spacing issues before proceeding.

**Step 4 — Migrate IV/ and V/ (pure copy, lowest risk)**

`IV_results_and_discussion.tex` and `V_conclusion_and_perspective.tex` are almost verbatim copies. Copy content from `05` and `06`, remove the old `\chapter{...}` line, add `\thesissection{IV/V}{...}` at the top. Compile `main_new.tex`. Verify `\ref{fig:recall-by-class}`, `\ref{tab:confusion-matrix}`, `\ref{tab:evaluation-snapshot}` all resolve. Fix the two "Chapter~5" prose references in V/ using `\label{sec:iv-results}`.

**Step 5 — Migrate III/ (merge of 03 + 04)**

Copy full content of `03_methodology_and_system_design.tex` then `04_implementation.tex` into `III_materials_and_methods.tex`. Remove both old `\chapter{...}` lines. Add `\thesissection{III}{Materials and Methods}` at the top. Compile. Verify all table/figure/equation refs resolve: `\ref{tab:dataset-stats}`, `\ref{tab:pilot-comparison}`, `\ref{tab:qlora-config}`, `\ref{eq:qlora-forward}`, `\ref{fig:runtime-flow}`, `\ref{fig:system-overview}`, `\ref{tab:milestone-summary}`. Fix "Chapter~5" reference in former ch04 content (line ~126).

**Step 6 — Migrate I/ and II/ (split + merge)**

Extract "Objectives and Scope" from `01_introduction.tex` into `II_objectives.tex`. Delete "Report Organization" section from `01_introduction.tex`. Append full content of `02_related_work_and_background.tex` after the trimmed ch01 content into `I_introduction.tex`. Add `\thesissection{I}{Introduction}` at top of I/, `\thesissection{II}{Objectives}` at top of II/. Compile. Verify `\ref{fig:cloud-vs-local-flow}` resolves.

**Step 7 — Wire new frontmatter into `main_new.tex`**

Replace the `\input{chapters/frontmatter/preface}` line in `main_new.tex` with the full new frontmatter sequence (certification, Acknowledgements, TOC, abbreviations, LoT, LoF, abstract). Compile. Verify: roman page numbers on frontmatter, arabic from I/ onward, TOC shows all five roman-numeral body entries plus all frontmatter entries (Acknowledgements, List of Abbreviations, List of Tables, List of Figures, Abstract).

**Step 8 — Promote `main_new.tex` to `main.tex`**

Rename existing `main.tex` to `main_old.tex` (backup). Rename `main_new.tex` to `main.tex`. Compile two full passes (for `natbib` label resolution). Perform visual spot-check on the PDF: cover page, certification, TOC page numbers, first body section heading "I/ Introduction", References, page header content.

**Step 9 — Add appendices**

Write `chapters/appendices/appendices.tex` with `\chapter{Appendix A: ...}` content. Verify it appears in TOC and that the appendix chapter letter renders correctly (LaTeX `\appendix` resets `\thechapter` to letters).

**Step 10 — Cleanup commit (deferred)**

After the next milestone's compile is confirmed clean, delete the deprecated old chapter files (`01` through `06`, `preface.tex`) in a dedicated cleanup commit. Do not co-mingle cleanup with content changes.

---

## `fancyhdr` Running Header Behavior

The current `main.tex` defines:
```latex
\fancyhead[L]{\small\leftmark}
```

For `\chapter*`, LaTeX does NOT auto-update `\leftmark`. Without the `\markboth` call inside `\thesissection`, the page header would display the previous section's name throughout the entire following body section.

The `\markboth{#1/ #2}{#1/ #2}` call in `\thesissection` is therefore mandatory, not optional. This applies to ALL frontmatter `\chapter*` calls as well. The certification, abbreviations, and abstract files must each call `\markboth{...}{...}` or use `\thispagestyle{plain}` to suppress the header on those pages.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| `\chapter*` + `\addcontentsline` approach | HIGH | Standard LaTeX idiom; safe with `titlesec` and `tocloft` |
| `\titlesec` inheritance to `\chapter*` | HIGH | `titlesec` documents that `\titleformat{\chapter}` applies to starred form |
| `\markboth` requirement for `fancyhdr` | HIGH | Documented `fancyhdr` behavior; verified by inspection of current `main.tex` |
| Label/ref safety across all merges | HIGH | All 11 labels audited; no cross-boundary reference pairs exist |
| Prose "Chapter~N" breakages | HIGH | Three instances found by grep; all fixable before Step 4 |
| Restructure step ordering | MEDIUM | Based on dependency analysis; compile-test at each step is the primary safety net |
| `certification.tex` exact wording | LOW | No official department `.tex` template available; draft is reasonable but must be verified against department's Word template before submission |

---

---

# Software Pipeline Architecture (Phases 1–21)

**Domain:** Localized explainable LLM for Vietnamese financial phishing/social engineering text detection
**Project:** Localized Explainable AI (XAI) Engine for Vietnamese phishing triage
**Researched:** 2026-03-18

## Recommended Architecture

Use an offline-first, modular pipeline with strict stage boundaries:

1. Ingestion and normalization
2. Threat analysis (rules + retrieval + LLM classifier)
3. Explanation synthesis (evidence-grounded)
4. User recommendation generation
5. Logging and evaluation feedback loop

Design principle: high recall on threat detection, deterministic evidence capture, and explainable outputs that are safe for non-technical users.

## Component Boundaries and Interfaces

- **Client Adapter** — Accepts raw text from UI, clipboard, or message paste. Input: `POST /analyze` request payload. Output: canonical analysis request object. Talks to: Preprocessor.
- **Preprocessor** — Language normalization, typo/slang cleanup, PII masking tags, URL/phone/entity extraction. Input: canonical analysis request. Output: enriched text document with extracted artifacts. Talks to: Retrieval, Rule Engine, LLM Orchestrator.
- **Rule Engine** — Fast deterministic high-recall signals (domain spoofing, urgency, payment pressure, impersonation markers). Input: enriched text document. Output: rule signal set with confidence priors. Talks to: LLM Orchestrator, Evidence Store.
- **Retrieval Layer** — Fetches known scam patterns, local financial entity knowledge, phrase templates. Input: enriched text + extracted entities. Output: ranked context snippets. Talks to: LLM Orchestrator.
- **LLM Orchestrator** — Runs local model prompt chain for threat class, confidence, rationale candidates. Input: enriched text + rule signals + retrieved context. Output: structured threat assessment JSON. Talks to: Explanation Engine.
- **Explanation Engine** — Converts model output + evidence into user-readable explanation with citation links to evidence spans. Input: structured threat assessment + evidence bundle. Output: explanation object. Talks to: Recommendation Engine.
- **Recommendation Engine** — Generates action checklist (block/report/verify channel) by risk level. Input: explanation object + threat level. Output: user action plan. Talks to: Response Assembler.
- **Response Assembler** — Composes final API response in stable schema. Input: assessment + explanation + recommendations. Output: API response payload. Talks to: Client Adapter.
- **Event Logger** — Persists anonymized events, model metadata, latency, confidence, and user feedback. Input: events from all stages. Output: append-only local log records. Talks to: Eval Harness, Monitoring.
- **Eval Harness** — Replays benchmark datasets, computes metrics, compares against release gates. Input: dataset + model bundle + pipeline version. Output: scorecards and pass/fail report. Talks to: CI, Release Manager.
- **Model Runtime** — Offline inference engine (GGUF model + tokenizer + runtime config). Input: prompt requests. Output: token stream/JSON output. Talks to: LLM Orchestrator.
- **Model/Rules Registry** — Versioned model, prompts, rules, and retrieval snapshots. Input: version query. Output: immutable artifact references. Talks to: Orchestrator, Eval Harness.

## Interface Contracts (Suggested)

### 1. Analyze Request

```json
{
  "request_id": "uuid",
  "channel": "sms|zalo|messenger|telegram|facebook|other",
  "text": "raw user-provided text",
  "locale_hint": "vi|en|mixed",
  "timestamp": "ISO-8601"
}
```

### 2. Threat Assessment

```json
{
  "request_id": "uuid",
  "threat_label": "safe|suspicious|phishing|social_engineering|job_scam",
  "risk_score": 0.0,
  "confidence": 0.0,
  "signals": [
    {"type": "spoofed_domain", "value": "example-paypa1.com", "source": "rule"},
    {"type": "urgency_language", "value": "khoa tai khoan ngay", "source": "llm"}
  ],
  "evidence_spans": [
    {"start": 14, "end": 41, "text": "...", "reason": "impersonation cue"}
  ],
  "model_version": "xai-vi-8b-lora-q4_0@2026-03-18",
  "policy_version": "ruleset-0.1.0"
}
```

### 3. Explanation and Recommendation

```json
{
  "summary": "High risk financial phishing likely.",
  "why": [
    "Message creates urgency to bypass verification.",
    "Sender requests credential or transfer action.",
    "Link/domain pattern is inconsistent with official institution naming."
  ],
  "recommendations": [
    "Do not click links or share OTP/password.",
    "Call official hotline from bank website, not message contact.",
    "Report message in the platform and block sender."
  ],
  "user_safe_mode": true
}
```

### 4. Logging Event

```json
{
  "event_id": "uuid",
  "request_id": "uuid",
  "stage": "preprocess|rules|retrieval|llm|explanation|recommendation",
  "latency_ms": 0,
  "artifact_versions": {
    "model": "...",
    "prompt": "...",
    "rules": "..."
  },
  "risk_score": 0.0,
  "decision": "...",
  "feedback": "optional_user_feedback"
}
```

## Data Flow (Ingestion -> Analysis -> Explanation -> Recommendation -> Logging/Eval)

1. Ingestion receives raw text and metadata from the client adapter.
2. Preprocessor normalizes Vietnamese/mixed text, extracts URLs, entities, and suspicious lexical cues.
3. Rule Engine computes deterministic risk signals to protect recall and catch obvious fraud patterns.
4. Retrieval Layer pulls local threat patterns and institution references to ground model reasoning.
5. LLM Orchestrator runs offline model inference and emits a structured threat assessment.
6. Explanation Engine transforms assessment into human-readable rationale tied to evidence spans.
7. Recommendation Engine maps risk level and scam type to concrete user actions.
8. Response Assembler returns stable schema to client.
9. Event Logger stores per-stage telemetry and prediction artifacts.
10. Eval Harness consumes logs plus benchmark sets to produce quality, recall, and latency reports.
11. Release Manager promotes model/rules only if evaluation gates are met.

## Offline Deployment Architecture

### Topology

- Desktop or local service host (consumer laptop, CPU/iGPU baseline)
- Embedded model runtime process (GGUF + quantized 8B LoRA merge)
- Local vector/rule store and retrieval index (on-device)
- Local encrypted event store (SQLite or append-only JSONL + encryption)
- Optional air-gapped update package import for model/rule updates

### Runtime Packaging

- Single installer bundle contains:
  - Inference runtime binaries
  - Quantized model artifacts
  - Prompt templates and rules
  - Local knowledge snapshot (financial entities, known patterns)
- No outbound network requirement for inference path.
- Update mechanism is explicit and versioned (manual package or signed internal updater).

### Security/Privacy Boundaries

- Raw user text never leaves local device in production mode.
- PII masking for logs by default; full raw text logging disabled unless debug mode is explicitly enabled.
- Tamper-evident version metadata for model and rules to preserve auditability.

## Evaluation Harness Architecture

### Core Harness Components

- **Dataset Manager** — Curates train/validation/test sets (real + synthetic Vietnamese scams, mixed-language edge cases).
- **Scenario Generator** — Builds adversarial and mutation tests (typo, slang, obfuscation, unicode confusables).
- **Runner** — Executes pipeline versions against fixed benchmark suites.
- **Metrics Engine** — Computes recall, precision, F1, calibration, explanation quality, latency.
- **Threshold Gate** — Enforces release criteria with recall-priority policy.
- **Regression Tracker** — Compares current run vs previous approved baseline.
- **Error Analyzer** — Clusters false negatives/positives and maps to remediation actions.

### Evaluation Data Flow

1. Select immutable benchmark suite by version.
2. Run full pipeline end-to-end (not model-only) to capture system behavior.
3. Store predictions, explanations, and recommendations.
4. Score across detection, explanation fidelity, and user-action quality.
5. Produce fail report highlighting high-severity false negatives.
6. Feed errors into data improvement loop (rules update, retrieval update, fine-tune data updates).

### Minimum Release Gates (suggested)

- Recall on phishing/social-engineering classes: prioritize as primary gate.
- Macro F1 for overall classification stability.
- Explanation quality checks:
  - Evidence-grounded reasons present
  - No hallucinated institution/action claims
- Latency budget on consumer hardware.

## Patterns to Follow

### Pattern 1: Hybrid Detection (Rules + Retrieval + LLM)

**What:** Combine deterministic rules with grounded LLM reasoning.
**When:** Safety-critical scam detection where recall is critical.
**Why:** Rules catch known high-risk patterns quickly; LLM handles nuanced language and social context.

### Pattern 2: Structured Output First

**What:** Force model outputs into fixed JSON schema before user rendering.
**When:** Need stable downstream explanation/recommendation logic and evaluability.
**Why:** Prevent brittle parsing and enable robust regression testing.

### Pattern 3: Evidence-Bound Explanations

**What:** Every explanation claim should map to explicit text spans/rule hits.
**When:** XAI requirements and trust-sensitive product context.
**Why:** Improves user trust and reduces unsafe overclaiming.

## Anti-Patterns to Avoid

### Anti-Pattern 1: LLM-Only Classification Without Rules

- What goes wrong: misses simple but dangerous patterns under prompt variance.
- Consequence: preventable false negatives in phishing detection.
- Instead: always include deterministic high-recall guards.

### Anti-Pattern 2: Binary Output Without Action Layer

- What goes wrong: user knows something is risky but has no safe next steps.
- Consequence: reduced practical safety impact.
- Instead: attach scenario-specific recommendations.

### Anti-Pattern 3: Evaluating Model in Isolation

- What goes wrong: hidden failures in retrieval, rules, or rendering are missed.
- Consequence: production regressions despite good offline model scores.
- Instead: evaluate full pipeline end-to-end.

## Build-Order Implications for Phase Planning

Suggested build order for a greenfield milestone:

1. Foundation and contracts first — define canonical schemas, establish artifact versioning.
2. Ingestion + preprocessing + logging skeleton — wire end-to-end request tracing before model work.
3. Rule Engine v1 + baseline retrieval — implement high-recall deterministic signals.
4. Offline model runtime integration — structured output constraints, initial threat labels.
5. Explanation and recommendation layers — evidence-to-rationale mapping, safe guidance wording.
6. Evaluation harness and release gates — benchmark runner, metrics, regression dashboard.
7. Data flywheel and hardening — use error clusters to update data, rules, prompts, retrieval.

## Architecture Risks to Track During Planning

- Retrieval contamination from low-quality synthetic patterns can degrade explanations.
- Over-aggressive normalization can erase signal (slang/spoof tokens).
- Quantization settings may impact calibration and confidence reliability.
- Recommendation policy drift can produce unsafe or outdated advice.

---

## Chat-Bubble UI Integration Architecture (Milestone v2.0)

**Researched:** 2026-06-08
**Scope:** Frontend redesign only — Python WSGI backend (`demo.py`) is unchanged.

### Integration Point Summary

The existing system provides a single stable integration seam: `POST /api/analyze` returning `AnalysisResult` JSON. Everything else — HTML, CSS, JS — is static asset serving with no server-side templating. The chat-bubble redesign is a purely frontend concern.

**Backend contract (unchanged):**

Request body:

```json
{ "text": "<string>", "channel": "<ChannelName>" }
```

Response on success (`200`):

```json
{
  "risk_tier": "benign | suspicious | high-risk",
  "summary": "<string>",
  "top_cues": [{"span": "<string>", "reason": "<string>", "cue_type": "<string|null>"}],
  "threat_labels": ["bank_impersonation | zalo_social_engineering | task_scam | benign"],
  "recommendations": ["<string>"],
  "backend_name": "<string>",
  "provisional": true,
  "normalized_text": "<string|null>"
}
```

Response on error (`400` or `503`):

```json
{ "error": { "message": "<string>", "steps": ["<string>"] } }
```

`demo.py` needs zero changes for the core API contract. No new routes. No server-side rendering.

### File Change Map

All paths below are relative to `src/runtime/demo_assets/` unless otherwise noted.

**Modified files (in-place rewrites):**

- **index.html** — Replace card-layout shell with chat-window shell. Remove old result/error templates. Add `#chat-thread` scroll container, `#composer` input bar with channel pill, and new bubble templates (`bubble-user`, `bubble-bot`, `bubble-error`, `bubble-typing`).
- **demo.css** — Remove panel/grid rules. Add chat-window, bubble, typing-indicator, composer-bar, and channel-pill rules. Retain all existing CSS variables and font stack.
- **demo.js** — Replace `renderResult`, `renderError`, `resetPanel`, and `setBusyState` with bubble-append functions and typing lifecycle. Keep the fetch call to `POST /api/analyze` intact.

**New files:**

- **demo_assets/i18n.js** — Bilingual string table (Vietnamese primary, English for technical terms). Plain JS object global, no module bundler needed. Served by a new static route in `demo.py`.

No new Python files beyond the one added route. No `package.json`, no build step.

### Data Flow: User Input to Bot Bubble

```text
User types text + selects channel
  -> clicks Send (or Ctrl+Enter)
  -> appendUserBubble(text, channel)         // instant, right-aligned
  -> appendTypingIndicator()                  // animated dots, left-aligned
  -> scrollToBottom()
  -> fetch POST /api/analyze {text, channel}
       [demo.py: DemoApp._handle_analyze -> service.analyze_text -> AnalysisResult]
  -> response.json()
  -> removeTypingIndicator()
  -> if response.ok:
       appendBotBubble(result)               // structured left-aligned bubble
     else:
       appendErrorBubble(error)             // error left-aligned bubble
  -> scrollToBottom()
  -> clear textarea, re-enable send
```

### Constraints Carried From Existing Architecture

- No framework, no build step, no npm — pure vanilla HTML/CSS/JS.
- Python WSGI backend `demo.py` serves static files from `demo_assets/` via `_load_asset()`. Any new static file needs a matching route in `demo.py`.
- The `AnalysisResult` contract (`contracts.py`) is frozen. JS must consume fields as-is: `risk_tier`, `summary`, `top_cues[].span`, `top_cues[].reason`, `threat_labels`, `recommendations`, `backend_name`.
- `ChannelName` values are the literal option `value` attributes in the channel select: `unknown`, `sms`, `zalo`, `messenger`, `telegram`, `facebook`.
- Inference on consumer hardware is slow (13+ seconds on CPU). The typing indicator is not cosmetic — it is the primary loading affordance. It must appear before the `fetch` resolves, not after.
