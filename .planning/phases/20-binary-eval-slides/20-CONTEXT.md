# Phase 20: Binary Evaluation Re-run + Eval Slide Updates — Context

**Gathered:** 2026-06-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Update evaluation slides (08_evaluation.tex and 09_confusion.tex) with binary scam/non-scam results and per-class metrics table format. No code execution required — binary results are derived analytically from the existing 4-class confusion matrix. All edits are LaTeX-only under `documents/reports/latex/slides/sections/`. Deck must compile clean with XeLaTeX after changes.

</domain>

<decisions>
## Implementation Decisions

### Binary Evaluation Results (Derived from 4-class Confusion Matrix)

4-class confusion matrix (254 held-out messages):
- Bank Impersonation (56 true): 56 correct, 0 elsewhere
- Zalo SE (75 true): 3 → Bank Imp, 72 correct
- Task Scam (62 true): 8 → Bank Imp, 54 correct
- Benign (61 true): 61 correct

Binary mapping (scam = bank_imp + zalo_se + task_scam; non-scam = benign):
- Predicted scam column: 56+3+8=67 bank_imp predictions, 72 zalo_se, 54 task_scam → ALL scam classes predict within scam super-class
- TP = 193 (scam correctly predicted as some scam class)
- TN = 61 (benign correctly predicted as benign)
- FP = 0 (no benign predicted as scam)
- FN = 0 (no scam predicted as benign)

Binary metrics:
- Precision: 1.000
- Recall: 1.000
- F1: 1.000
- Accuracy: 254/254 = 100%

Per-class metrics derived from confusion matrix:
| Class             | Precision | Recall | F1    | Support |
|-------------------|-----------|--------|-------|---------|
| Bank Impersonation| 0.836     | 1.000  | 0.911 | 56      |
| Zalo Social Eng.  | 1.000     | 0.960  | 0.980 | 75      |
| Task Scam         | 1.000     | 0.871  | 0.931 | 62      |
| Benign            | 1.000     | 1.000  | 1.000 | 61      |
| **Macro avg**     | **0.959** | **0.958** | **0.955** | 254 |

Precision formula for Bank Imp: predicted_bank_imp_col = 56+3+8 = 67; P = 56/67 = 0.836
All other classes: only true positives in their predicted column → P = 1.000.

### Slide 8 Update (08_evaluation.tex)

Replace the `\scalebox{0.82}{\input{slides/figures/recall_barchart_bare.tex}}` with a booktabs table showing per-class precision/recall/F1.
- Keep framesubtitle "Held-out Set (254 Messages)"
- Table columns: Class | Prec. | Recall | F1 | n
- Macro avg row with \midrule separator
- Keep the two existing bullet points: Macro F1 = 0.9553; lowest recall = Task Scam (0.871)
- Add a small block: "Binary (scam vs non-scam): Precision 1.000 · Recall 1.000 · F1 1.000 — zero scam/benign crossings"

### Slide 9 Update (09_confusion.tex)

Keep the 4-class confusion matrix (it shows the error analysis finding correctly).
Add a binary confusion matrix block alongside OR below as a \begin{block}{Binary Result}.

Two-column layout:
- Left: 4-class matrix (existing, scaled smaller)
- Right: Binary 2×2 table + key finding "Model perfectly separates scam from benign"

Binary 2×2:
| True \ Pred | Scam | Non-scam |
|-------------|------|----------|
| Scam        | 193  | 0        |
| Non-scam    | 0    | 61       |

### Claude's Discretion

- Exact table styling (column widths, \tabcolsep, \arraystretch)
- Whether to use a `\begin{block}` or inline \textbf for the binary summary on slide 8
- Whether [shrink=N] needed on either frame after adding content

</decisions>

<code_context>
## Existing Code Insights

### Files to Edit

- `documents/reports/latex/slides/sections/08_evaluation.tex` — replace TikZ barchart with table; add binary summary block
- `documents/reports/latex/slides/sections/09_confusion.tex` — add binary 2×2 matrix alongside existing 4-class matrix

### Established Patterns

- `\begin{columns}[t]` for 2-col layouts
- `\begin{block}{...}` for call-out boxes
- `\cellcolor{CVBLUE!15}` for diagonal cells in confusion matrices
- `\toprule / \midrule / \bottomrule` (booktabs)
- `[shrink=N]` on content-heavy frames
- `\footnotesize`, `\scriptsize` for dense tables
- `\setlength{\tabcolsep}{...}` and `\renewcommand{\arraystretch}{...}` for table spacing

### Integration Points

- 08_evaluation.tex and 09_confusion.tex are `\input{}`ed from slides.tex in the Evaluation section
- No new files needed — both are in-place edits
- After edits: XeLaTeX compile check from `documents/reports/latex/`

</code_context>

<specifics>
## Specific Numbers

- Supervisor feedback: wanted binary evaluation (scam vs non-scam) presented
- Binary result is perfect (F1=1.000) because all misclassifications are WITHIN scam super-class — strong result for defense
- Per-class table replaces bar chart (bar chart was informal; table is more rigorous)
- Macro F1 = 0.9553 locked — this is the authoritative value from evaluation_snapshot.tex and thesis

</specifics>

<deferred>
## Deferred

- Phase 21 updates the thesis report chapter 5 (evaluation section) to match these slides
- No code re-run needed — results derived from existing confusion matrix data

</deferred>
