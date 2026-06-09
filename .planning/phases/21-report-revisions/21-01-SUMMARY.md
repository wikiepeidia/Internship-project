---
phase: 21
plan: 01
subsystem: thesis-report
tags: [report, chapter2, bibtex, privacy, cloud-api]
key-files:
  modified:
    - documents/reports/latex/chapters/02_related_work_and_background.tex
    - documents/reports/latex/references.bib
decisions:
  - Replaced jailbreak/prompt-injection examples with documented cloud API data leakage incidents (OpenAI March 2023 breach, Samsung 2023 leak) per supervisor feedback
  - Removed Amazon Rufus figure (rufusai.png) and associated figure block
  - Kept cloud_vs_local_dataflow TikZ figure intact
metrics:
  duration: ~10 minutes
  completed: 2026-06-09
requirements: [REPORT-01, REPORT-02]
---

# Phase 21 Plan 01: Thesis Report Revisions Summary

**One-liner:** Replaced jailbreak examples in Section 2.2 with the OpenAI March 2023 Redis breach and Samsung 2023 confidential-data-leak incidents, adding two new BibTeX entries and recompiling clean.

## Changes Per Task

### Task 1 — Add BibTeX entries to references.bib

Added two new `@misc` entries to `documents/reports/latex/references.bib`:

- `openai2023breach`: OpenAI official incident report for the March 20 2023 ChatGPT outage (Redis caching bug exposing chat history and payment details of ~1.2% of ChatGPT Plus users).
- `bloomberg2023samsung`: Bloomberg report on Samsung banning employee use of AI tools after engineers leaked confidential chip design source code and meeting notes to ChatGPT.

Both entries follow the established pattern: `@misc` type, `howpublished = {\url{...}}`, `note` with publication date and access date.

### Task 2 — Rewrite Section 2.2 jailbreak content

Removed from `02_related_work_and_background.tex`:

- "Beyond privacy, generic API wrappers carry two well-documented failure modes..." paragraph (Chevrolet/Air Canada jailbreak and hallucination examples, citing `gizmodo2023chevy` and `aibusiness2024aircanada`)
- "Beyond corporate liability and domain hallucination..." paragraph (OWASP prompt injection, Amazon Rufus example, citing `owasp2025promptinjection`, `tomshardware2024rufus`)
- `\begin{figure}[H]...\end{figure}` block for `rufusai.png` (Figure ref: `fig:rufus-jailbreak`)

Inserted replacement paragraph between the cloud-API-logging paragraph and `\input{figures/cloud_vs_local_dataflow}`:

The new paragraph cites `\cite{openai2023breach}` and `\cite{bloomberg2023samsung}`, arguing that the OpenAI Redis bug and Samsung leak demonstrate that sensitive content submitted to a cloud API — whether through a security failure or routine service operation — can reach unauthorized parties. This reframes the risk from jailbreak/compliance failures to data leakage, which is more directly relevant to a financial phishing detection tool handling OTP codes and bank account numbers.

Old citation keys `gizmodo2023chevy`, `aibusiness2024aircanada`, `tomshardware2024rufus`, `owasp2025promptinjection` remain in `references.bib` (unused entries cause no errors).

### Task 3 — XeLaTeX compile check

Compile sequence: `xelatex` → `bibtex` → `xelatex` → `xelatex`

Results:
- "Output written on main.pdf (23 pages)" on both final passes
- Zero lines starting with `! ` in `main.log` (no fatal errors)
- Zero undefined citations after bibtex run
- Pre-existing `Underfull \hbox` warnings for long URLs in bibliography (unchanged from before this edit; not introduced by this phase)
- Pre-existing bibtex warning for `gerganov2023llamacpp` `@software` entry type (not defined in ieeetr.bst style; pre-existing, not introduced here)

## Deviations from Plan

**1. [Rule 3 - Blocking issue] Bibtex pass required between xelatex runs**

The plan specified running xelatex twice. After two xelatex passes, the new citations (`openai2023breach`, `bloomberg2023samsung`) remained undefined because bibtex had not yet processed the updated `references.bib`. Added `bibtex main` between the xelatex passes (standard LaTeX workflow). Full sequence: xelatex → bibtex → xelatex → xelatex. All citations resolved cleanly.

## Requirements Covered

- **REPORT-01:** Section 2.2 now cites documented cloud API data leakage incidents directly relevant to the tool's threat model (ChatGPT/OTP/financial data exposure).
- **REPORT-02:** Both new BibTeX entries are from credible primary sources (OpenAI official incident report; Bloomberg news article) replacing weaker jailbreak anecdotes.

## Self-Check

- [x] `documents/reports/latex/chapters/02_related_work_and_background.tex` modified correctly — rufusai figure removed, new paragraph inserted
- [x] `documents/reports/latex/references.bib` — two new entries added (`openai2023breach`, `bloomberg2023samsung`)
- [x] Compile: "Output written on main.pdf", zero `! ` fatal errors, zero undefined citations
