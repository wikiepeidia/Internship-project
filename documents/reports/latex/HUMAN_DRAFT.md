# Review pass — the prose is converted, now make it yours

**Status: the whole report has been rewritten into plain student English.** You no longer
start from a blank page. Your job is now to read it and change anything that doesn't sound
like you or that you couldn't defend out loud.

You still never touch a `.tex` file. Write your changes in here and I apply them.

## What I actually changed

Register only. **Not one number, citation, or claim was altered** — I ran an automated check
after every chapter that compares every number, `\cite`, `\ref` and `\label` against the
pre-rewrite backup. All chapters came back clean.

| Chapter | Words | Status |
|---|---|---|
| 1 Introduction | +8 | rewritten |
| 2 Objectives | +14 | rewritten |
| 2 Related Work | — | **left alone** (citation-dense, low voice value) |
| 3 Methodology | **−53** | rewritten |
| 4 Implementation | +156 | rewritten + one added paragraph |
| 5 Evaluation | +210 | rewritten |
| 6 Conclusion | +60 | rewritten |
| Appendices | — | **left alone** (tables and file paths) |

Report went from 51 to **50 pages**. Build is clean: zero undefined references, zero
undefined citations, zero errors, 18 figures.

**The one thing I added:** a paragraph in Chapter 4 explaining where the 14.87 hours went —
1.36 h of optimizer steps plus 25 validation passes over 219 rows each, 5,475 generations
total. I also added two sentences referencing the run-timeline and checkpoint-sweep figures,
because they had no in-text mention. Everything else is the same content in plainer words.

---

## How to review

Open `main.pdf` and read. For anything you want changed, write it here in this form:

```
CH5, section "Bounded Resource Evidence"
The sentence starting "Both probes ran on the same laptop..."
→ change to: <your version, however rough>
```

Rough is fine. Bullet points are fine. I fix the English and place it.

**The test to apply while reading:** could you say this sentence out loud, in your own words,
if a juror stopped you on it? If not, flag it. That is the only test that matters.

---

## Where to spend your limited hours

**Priority 1 — Chapter 5, sections 5.1 to 5.5.** This is what jurors interrogate. Read these
five sections properly and make sure every sentence is one you could defend.

**Priority 2 — Chapter 4, the training sections.** Especially the QLoRA explanation and the
14.87-hour paragraph. If the QLoRA description doesn't match how you'd explain it, rewrite it.

**Priority 3 — Chapter 3, "Data Construction and Split Governance".** The longest section in
the report and the one most likely to be attacked. The Pydantic-vs-judge distinction has to be
something you can say cold.

**Skip unless you have spare time:** Chapters 1, 2, 6. They read fine and jurors rarely dig.

---

## Two sections I did not soften, on purpose

**Chapter 5, "Preclaim Failures and Provenance Correction"** and **"Limits of the Evidence"**.
I rewrote the sentences to be plainer but kept every hedge, every disclosure, and every
number exactly. These two passages are what let you survive cross-examination — the report
volunteers its own weaknesses before a juror can produce them. Don't let anyone talk you into
cutting them for length.

---

## Still open

1. **Chapter 2 Related Work (2,085 words)** is untouched and is the longest single trim
   target if the report needs to be shorter. The reference thesis that passed had no separate
   related-work chapter at all — its literature review sat inside the Introduction. Tell me if
   you want it folded in or cut; it's the one structural edit still worth considering.
2. **Close Foxit before every build**, or the build dies with a confusing dvipdfmx error.
3. Build command: `pwsh -File documents\reports\latex\build_report.ps1`

---

## Never write these

t-test · p-value · confidence interval · statistical significance · "stable winner" ·
"LoRA ran out of memory" · a full-LoRA accuracy number · PhoBERT GGUF · completed deployment
fitting · a fair Qwen-vs-PhoBERT speed comparison · 44/100 as a corpus-wide failure rate ·
"Pydantic judged quality" · "the security review is closed" · any SHA-256 · "Phase 40/41"
