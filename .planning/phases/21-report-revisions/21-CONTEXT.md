# Phase 21: Thesis Report Revisions — Context

**Gathered:** 2026-06-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Update Chapter 2 of the thesis to replace jailbreak/prompt-injection examples with ChatGPT/cloud API data leakage incidents. Add two new BibTeX entries. Remove the Amazon Rufus figure. Keep the cloud_vs_local_dataflow figure. Thesis must compile clean with XeLaTeX after changes.

Files: `documents/reports/latex/chapters/02_related_work_and_background.tex` and `documents/reports/latex/references.bib`.

Do NOT change: thesis title page, abstract (preface.tex), chapter 5 evaluation metrics (already correct), quantization documentation (already correct).

</domain>

<decisions>
## Implementation Decisions

### What to Change

**Target:** Section 2.2 "Local Inference as a Privacy Control" in `02_related_work_and_background.tex`

Current problematic content (lines 14–23):
- "Beyond privacy" paragraph: cites Chevrolet/Air Canada jailbreak and hallucination failures
- Second paragraph: Amazon Rufus prompt injection + `rufusai.png` figure

Replace with: two documented data leakage incidents showing that cloud API use = sensitive data risk:
1. OpenAI ChatGPT March 2023 — Redis cache bug exposed chat history + payment details of ~1.2% of ChatGPT Plus users
2. Samsung Semiconductor 2023 — engineers pasted confidential chip design code + meeting notes into ChatGPT; data stored on OpenAI servers

Keep intact (lines 9-13):
- The opening of Section 2.2 explaining local inference as privacy control
- The paragraph about cloud API logging risk and OTP/account numbers
- `\input{figures/cloud_vs_local_dataflow}` — this TikZ figure stays

Remove:
- The entire "Beyond privacy, generic API wrappers carry two well-documented failure modes" paragraph (Chevrolet/Air Canada)
- The entire "Beyond corporate liability" / Amazon Rufus paragraph
- The `\begin{figure}[H]...\end{figure}` block for rufusai.png
- Citations: `\cite{gizmodo2023chevy}`, `\cite{aibusiness2024aircanada}`, `\cite{tomshardware2024rufus}`, `\cite{owasp2025promptinjection}` (if only used in removed sections)

### New Paragraph (replacement content)

After the cloud-API-logging paragraph (line 12), insert:

```
Beyond passive logging risk, documented incidents show that cloud API deployments
can expose sensitive user data through active security failures. In March 2023,
OpenAI disclosed a Redis caching bug that exposed the chat history, payment card
details, and account information of approximately 1.2\% of ChatGPT Plus subscribers
to other users for a nine-hour window \cite{openai2023breach}. A similar failure of
the local-only design philosophy occurred at Samsung Semiconductor in 2023: engineers
pasted confidential chip design source code and internal meeting notes into ChatGPT
to assist with code review tasks, only to discover that these inputs were stored on
OpenAI's servers and could potentially be used for model training
\cite{bloomberg2023samsung}. Both incidents demonstrate that sensitive content
submitted to a cloud API --- whether through a security failure or routine service
operation --- can reach unauthorized parties. For a financial phishing detection
tool whose inputs are OTP codes, bank account numbers, and social-engineering
messages, this risk class is structurally more serious than domain hallucination or
off-task compliance: the user's sensitive financial data is precisely the content
that must not reach a third-party server.
```

Then keep `\input{figures/cloud_vs_local_dataflow}` (no change needed to that figure).

### New BibTeX Entries

Add to `references.bib`:

```bibtex
@misc{openai2023breach,
  author       = {{OpenAI}},
  title        = {{March 20 ChatGPT Outage: Here's What Happened}},
  year         = {2023},
  howpublished = {\url{https://openai.com/index/march-20-chatgpt-outage/}},
  note         = {OpenAI official incident report, published 2023-03-24, accessed 2026-06-09}
}

@misc{bloomberg2023samsung,
  author       = {Kim, Hyunjoo and Gurman, Mark},
  title        = {{Samsung Bans Employee Use of {AI} Tools Like {ChatGPT} After Sensitive Data Leak}},
  year         = {2023},
  howpublished = {\url{https://www.bloomberg.com/news/articles/2023-05-02/samsung-bans-chatgpt-and-other-generative-ai-use-by-staff-after-data-leak}},
  note         = {Bloomberg, published 2023-05-02, accessed 2026-06-09}
}
```

### Compile Check

After edits: run `xelatex -interaction=nonstopmode main.tex` twice (for cross-refs) from `documents/reports/latex/`. Verify: "Output written on main.pdf", zero `! LaTeX Error` lines.

If `\cite{gizmodo2023chevy}`, `\cite{aibusiness2024aircanada}`, `\cite{tomshardware2024rufus}` are only used in the removed paragraphs, their BibTeX entries can stay in references.bib (unused entries don't cause errors). Do NOT delete them unless they cause problems.

</decisions>

<code_context>
## Existing Code Insights

### File Structure

- `documents/reports/latex/chapters/02_related_work_and_background.tex`
  - Section 2.2 "Local Inference as a Privacy Control" — lines 9–25
  - Lines 9–12: keep (good privacy motivation text)
  - Lines 14–16: REMOVE (Chevrolet/Air Canada paragraph)
  - Lines 16–23: REMOVE (Amazon Rufus paragraph + figure)
  - Line 25: `\input{figures/cloud_vs_local_dataflow}` — KEEP

- `documents/reports/latex/references.bib`
  - Currently has: `gizmodo2023chevy`, `aibusiness2024aircanada`, `tomshardware2024rufus`, `owasp2025promptinjection`
  - Missing: `openai2023breach`, `bloomberg2023samsung`

### Established Patterns

- BibTeX entries use `@misc` type for web sources
- `howpublished = {\url{...}}` with `note` for access date
- Paragraph breaks between distinct ideas
- `\cite{key}` inline citations

</code_context>

<specifics>
## Supervisor Feedback That Drives This Phase

"api leak recommended + privacy issue, require researching for chatgpt leaked data problem"

Both the OpenAI March 2023 breach and the Samsung leak are:
- Well-documented (OpenAI official incident report; Bloomberg + multiple outlets)
- Directly relevant (cloud API sending sensitive text → data stored/exposed)
- More credible for a defense than jailbreak incidents

</specifics>
