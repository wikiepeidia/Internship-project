# Phase 40 Report and Slide Handoff

**Prepared:** 2026-08-25 during the active local Qwen QLoRA run

**Purpose:** Remove report/slide integration delay without inventing results or editing the locked live documents before Phase 40/41 evidence freezes.
**Status:** Structure ready; all result-bearing values remain mechanically gated.

## Non-Negotiable Gates

1. Do not insert a metric, graph, model conclusion, checkpoint identity, wall time, or GGUF claim until its canonical artifact verifies.
2. Do not create `WRITING_GUARDRAILS_REPORT.md` until the actual passed-student reference report has been obtained and reviewed. Phase 42 cannot guess this file.
3. Do not edit the live report or deck during the active Phase 40 training/finalizer-authority window. This handoff is staging only.
4. Before Phase 43 edits, archive the whole imported slide source tree or preserve it on an immutable branch/tag. Saving only `slides.tex` does not preserve its mutable `slides/sections/` and figure dependencies.
5. Phase 41 is the first and only model-quality evaluation of the current canonical test snapshot, not the first human exposure to its content. Phase 39 quality work inspected test rows, and `chapters/03_methodology_and_system_design.tex` currently quotes one promoted-test message. That exposure must be disclosed and must not influence training, validation acceptance, checkpoint selection, thresholds, Colab activation, or repair.

## Mechanical Placeholder Contract

| Placeholder | Required canonical input | Destination |
|---|---|---|
| `[P40_LORA_RESOURCE_PROBE]` | `40-LOCAL-PROBE-REPORT.md` plus sealed probe evidence | Methodology, evaluation resource subsection, training slides |
| `[P40_QWEN_TRAINING_CONFIG]` | QLoRA `resolved-config.json`, package/runtime identity, step-zero lineage | Methodology and implementation |
| `[P40_PHOBERT_TRAINING_CONFIG]` | PhoBERT `resolved-config.json`, package/runtime identity, step-zero lineage | Methodology and implementation |
| `[P40_QWEN_CURVE]` | QLoRA `curves/loss-curves.png` plus normalized data and provenance | Evaluation and slides |
| `[P40_PHOBERT_CURVE]` | PhoBERT `curves/loss-curves.png` plus normalized data and provenance | Evaluation and slides |
| `[P40_VALIDATION_COMPARISON]` | `comparison-manifest.json`, `comparison-report.md`, and `40-VALIDATION-COMPARISON.md` | Evaluation and discussion |
| `[P40_GGUF_VERIFICATION]` | `data/models/phase40/qwen-gguf-verification-receipt.json`, binding the verified Q8_0 manifest, converter/tool identity, and independent load smoke | Implementation and model slides |
| `[P40_QUALITATIVE_REVIEW]` | `40-VIETNAMESE-ERROR-REVIEW.md` and review manifest | Evaluation limitations/error analysis |
| `[P41_HELDOUT_COMPARISON]` | Frozen Phase 41 result manifest and report | Evaluation, conclusion, result slides |
| `[P41_CONFUSION_MATRICES]` | Mechanically generated matrices plus raw-prediction hashes | Evaluation and slides |
| `[P41_TERMINAL_LIMITATIONS]` | One-pass access receipt and no-retraining declaration | Evaluation, conclusion, limitations slide |

No placeholder token is permitted in a compiled final PDF.

## Phase 40 Evidence Inputs

Expected repository-side inputs after both local runs finish:

- `data/models/phase40/comparison-manifest.json`
- `data/models/phase40/comparison-report.md`
- `data/models/phase40/full/qwen-qlora/run-evidence.json`
- `data/models/phase40/full/phobert/run-evidence.json`
- Both runs' `curves/loss-curves.png`
- Both runs' `curves/normalized-loss-curves.json`
- Both runs' `curves/graph-provenance.json`
- Verified validation metrics and raw prediction artifacts
- `.planning/phases/40-multi-model-training-evidence/40-LOCAL-PROBE-REPORT.md`
- `.planning/phases/40-multi-model-training-evidence/40-VALIDATION-COMPARISON.md`
- `.planning/phases/40-multi-model-training-evidence/40-VIETNAMESE-ERROR-REVIEW.md`
- `data/models/phase40/review/human-review-manifest.json`
- `data/models/phase40/review/human-review-report.md`
- `data/models/phase40/qwen-gguf-verification-receipt.json`, created only after the D-drive export manifest and independent load-smoke result verify and are copied into one canonical tracked receipt

If a named artifact is absent or fails verification, its corresponding report/slide claim remains absent.

## Phase 41 Output Contract to Freeze Before Integration

Phase 41 planning must assign canonical filenames for:

- one-pass model-evaluation authorization/access receipt;
- exact Qwen QLoRA and PhoBERT checkpoint/model identities;
- per-model macro F1 and weighted F1;
- per-class precision, recall, and F1 in canonical label order;
- confusion matrices and invalid-output counts;
- raw predictions and their hashes;
- explicit statements of every metric on which PhoBERT wins, if any;
- known prior human/content exposure;
- terminal-result/no-test-driven-retraining declaration.

The Phase 41 evaluator must not expose results incrementally. It should produce the complete two-model result transaction or fail without publishing a partial comparison.

## Report Insertion Map

All paths below are relative to `documents/reports/latex/`.

### `chapters/03_methodology_and_system_design.tex`

- Separate historical model work from the new controlled QLoRA/PhoBERT experiment.
- Describe PhoBERT as a full label-only classification-head baseline.
- Include ordinary LoRA only as bounded resource/ETA evidence; never create a LoRA accuracy row.
- Preserve the existing truthful statement that a worked example came from the promoted test split, then carry that exposure into the evaluation limitations. Replacing the example cannot restore blindness.

### `chapters/04_implementation.tex`

- Insert the verified step-zero QLoRA → Q8_0 GGUF → PhoBERT sequence.
- Describe evidence bundles, exact package identities, telemetry, source/input hashes, checkpoint selection, and GGUF verification.

### `chapters/05_evaluation_and_discussion.tex`

- Keep the earlier 254-row result under an explicitly historical heading.
- Add sections for current validation protocol, Qwen-versus-PhoBERT validation, ordinary-LoRA resource evidence, Vietnamese qualitative error review, one-pass held-out comparison, and terminal limitations.

### `chapters/06_conclusion_and_future_work.tex`

- Replace historical main findings and the current future-tense held-out paragraph only after Phase 41 freezes.

### `chapters/appendices.tex`

- Add exact hashes, commands, revisions, packages, checkpoint identities, GGUF verification, and evaluation timestamp.
- Keep primary graphs and conclusions in the main chapters.

### `EVIDENCE_MAP.md`

- Extend the evidence map only after Phase 40/41 filenames and hashes freeze.

## Slide Storyboard

The revised deck should follow the real pipeline:

1. Get data
2. Repair and independently verify data
3. Train: bounded LoRA probe, full Qwen QLoRA, full PhoBERT
4. Same-laptop resource evidence
5. Real training curves
6. Verified Q8_0 GGUF export
7. Two-model validation comparison
8. One-pass held-out comparison
9. Local demo
10. Contributions and limitations

Use progressive `\pause` reveals for training and evaluation results. Later edit targets are:

- `slides/sections/04_architecture.tex`
- `slides/sections/05_data.tex`
- `slides/sections/07_model.tex`
- `slides/sections/08_evaluation.tex`
- `slides/sections/11_contributions.tex`
- `slides/sections/14_backup.tex`
- `slides.tex`

The existing `06_why_local.tex`, `09_confusion.tex`, and `12_future.tex` files are not currently imported; Phase 43 must either include them deliberately or leave them excluded explicitly.

## Build and Stale-Placeholder Checks

Run from `documents/reports/latex` after real insertion:

```powershell
xelatex -interaction=nonstopmode -halt-on-error -file-line-error main.tex
bibtex main
xelatex -interaction=nonstopmode -halt-on-error -file-line-error main.tex
xelatex -interaction=nonstopmode -halt-on-error -file-line-error main.tex

xelatex -interaction=nonstopmode -halt-on-error -file-line-error slides.tex
xelatex -interaction=nonstopmode -halt-on-error -file-line-error slides.tex
```

Then fail on compile problems or leaked placeholders:

```powershell
$hits = Select-String -Path main.log,slides.log -Pattern 'Fatal error|Emergency stop|Undefined control sequence|LaTeX Error|undefined references|undefined citations'
if ($hits) { $hits; throw 'LaTeX log gate failed' }

rg -n "PENDING_PHASE|P40_|P41_|TODO_EVIDENCE" .
if ($LASTEXITCODE -eq 0) { throw 'Placeholder gate failed' }
if ($LASTEXITCODE -gt 1) { throw 'Placeholder scan failed' }
```

Phase 39 compile evidence remains historical and hash-bound. Phases 42/43 must create new compile evidence instead of overwriting it.
