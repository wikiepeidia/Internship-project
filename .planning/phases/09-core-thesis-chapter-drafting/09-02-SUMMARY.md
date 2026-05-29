---
phase: "09"
plan: "02"
subsystem: thesis-methodology-implementation-chapters
tags: [latex, thesis, methodology, implementation, chapter-drafting]
dependency_graph:
  requires: [09-01]
  provides: [expanded-chapter-3, expanded-chapter-4]
  affects:
    - documents/reports/latex/chapters/03_methodology_and_system_design.tex
    - documents/reports/latex/chapters/04_implementation.tex
tech_stack:
  added: []
  patterns: [latex-prose-expansion, evidence-grounded-academic-writing]
key_files:
  created: []
  modified:
    - documents/reports/latex/chapters/03_methodology_and_system_design.tex
    - documents/reports/latex/chapters/04_implementation.tex
decisions:
  - "Pilot manifest shows all three candidates had equal risky_recall=0.5 in the raw pilot scoring; the 4B-vs-8B reconciliation is framed as a hardware-fit decision (5.6 GB vs 2.8 GB peak VRAM) rather than a recall-quality decision, consistent with the proposal execution update framing"
  - "Chapter 3 training numbers sourced exclusively from STATE.md session continuity (2018 train, 210 val, checkpoint-505, loss 0.4951) rather than the earlier Phase 3 smoke run (476/207), because the plan explicitly requires the final baseline refresh numbers"
  - "Chapter 4 cite{nist2026privacyframework} placed at the service-layer normalization sentence per plan instruction; Chapter 3 cite{rjoub2023surveyxai} placed at the explainability design sentence and cite{nist2026privacyframework} at the privacy boundary sentence"
metrics:
  duration: "~10 minutes"
  completed: "2026-05-29T01:51:00Z"
  tasks_completed: 2
  tasks_total: 2
---

# Phase 09 Plan 02: Expand Chapters 3 and 4 with Evidence-Grounded Prose Summary

Chapters 3 and 4 rewritten from scaffold sentences to full substantive prose. Chapter 3 now reports all concrete data pipeline and training numbers with the 4B-vs-8B reconciliation explained as a hardware-fit decision. Chapter 4 now names all three packages, both runtime profiles, three CLI entry points, and three dependency groups.

## What Was Done

### Task 1: Expand Chapter 3 — Methodology and System Design

Rewrote `03_methodology_and_system_design.tex`. Kept the chapter opening paragraph, both `\input{}` calls, and all six section headings. Replaced section bodies with full evidence-grounded prose.

Key content added:

- **Data Construction and Split Governance** (3 paragraphs): 3,000-row corpus across four classes; versioned manifest lineage with SHA-256 hashes; quality-judge pass (49/50, realism 4.68, label-correctness 4.96); seed-disjoint split governance; final split counts (2,018 train, 210 val); held-out support breakdown (56 bank-impersonation, 75 social-engineering, 62 task-scam, 61 benign).

- **Offline Text Runtime Baseline** (3 paragraphs): stable text-only contract; privacy-first design with text-only v1 boundary (OCR/image/audio explicitly out of scope); fail-closed doctor command. Added `\cite{nist2026privacyframework}` at the privacy boundary sentence.

- **Local Model Selection and Deployment Paths** (5 paragraphs): three pilot candidates evaluated on 33 balanced examples; 4B-vs-8B reconciliation (hardware-fit basis: 5.6 GB vs 2.8 GB peak VRAM; 7B retained as comparison option; proposal execution update records this decision); qwen3-4b-instruct-2507 as winner, qwen3.5-4b as runner-up; QLoRA three-epoch training run (2,018 train, 210 val, loss 0.4951, checkpoint-505); GGUF q8\_0 export with warm latency ~13 seconds on CPU.

- **Explainable Threat Decisioning** (3 paragraphs): four-element output structure (risk tier, threat labels, grounded cues, recommendations); two honesty constraints (cues from text, recommendations from safe set); fail-closed runtime boundary. Added `\cite{rjoub2023surveyxai}` at the explainability design sentence.

- **Development Structure** and **Design Principles** kept as-is per plan instruction.

### Task 2: Expand Chapter 4 — Implementation

Rewrote `04_implementation.tex`. Kept the chapter opening paragraph and all six section headings. Expanded each section with concrete implementation detail from USER_GUIDE.md and LOCAL_MODELS.md.

Key content added:

- **Codebase Organization** (2 paragraphs): roles of all three packages (data_pipeline, runtime, model_adaptation) named explicitly; operator entry points named (`vnphish demo`, `python -m src.runtime.cli demo`, `vnphish doctor`).

- **Data Pipeline Implementation** (3 paragraphs): Pydantic schema validation; explicit CLI steps for generation and quality-judging; versioned manifests with SHA-256 hash, timestamp, and git commit identifier.

- **Runtime Contracts and Service Boundary** (3 paragraphs): `AnalysisRequest` and `AnalysisResult` as the only cross-boundary types; service layer normalization and dispatch; rendering separation; doctor readiness check detail. Added `\cite{nist2026privacyframework}` at the service-layer sentence.

- **Backend Implementations** (2 paragraphs): `gguf-laptop` as default CPU profile; `accelerated-local` for stronger GPU hardware; heuristic backend as fallback; explicit profile selection with fail-closed doctor check.

- **Model Adaptation Workflow** (3 paragraphs): three-step coordination (pilot selection, QLoRA training, GGUF registration); q8\_0 export via convert_hf_to_gguf.py; registry-based artifact resolution to prevent stale artifact selection.

- **Operator Surface and Packaging** (2 paragraphs): three `pyproject.toml` dependency groups (dev, train, runtime); demo launch with `vnphish demo`; model warm-up at startup; ~13 s warm latency.

## Deviations from Plan

### Auto-fixed Issues

None. Both tasks executed exactly as specified.

### Scope Notes

The pilot manifest (phase3-large-pilot-2026-05-14.json) shows that all three candidates achieved equal `risky_recall=0.5` in the raw pilot run. The prose correctly frames the 4B selection on hardware-fit grounds (the 7B model used 5.6 GB peak vs 2.8 GB for the 4B winner) rather than on raw recall differences, consistent with the plan's threat model (T-09-06) and the "hardware-fit pilot" framing specified in the plan action section.

## Known Stubs

None. Both chapters report real evidence-grounded numbers from named artifacts. No placeholder text or hardcoded empty values remain.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes introduced. All changes are LaTeX prose edits in thesis output files (gitignored).

## Threat Mitigation Check

- **T-09-04 (Information Disclosure — scope claims):** Verified. No OCR, image, audio, or mobile claims appear in either chapter. Both chapters state text-only v1 boundary explicitly.
- **T-09-05 (Tampering — training numbers):** Verified. Numbers sourced from STATE.md session continuity section only. Exact values used: 2018 train (not 2000), 210 val (not 200), loss 0.4951, checkpoint-505.
- **T-09-06 (Repudiation — 4B-vs-8B reconciliation):** Verified. Decision presented as hardware-fit pilot result (5.6 GB vs 2.8 GB peak VRAM) with reference to a dated execution update in the proposal record. Not framed as scope reduction or apology.

## Self-Check

### Files created/modified

- `documents/reports/latex/chapters/03_methodology_and_system_design.tex` — FOUND (gitignored, not committed)
- `documents/reports/latex/chapters/04_implementation.tex` — FOUND (gitignored, not committed)

### Verification results

| Check | Expected | Actual | Status |
|-------|----------|--------|--------|
| `3{,}000` in Ch3 | >= 1 | 1 | PASS |
| `qwen3-4b-instruct-2507` in Ch3 | >= 1 | 2 | PASS |
| `qwen2.5-7b` in Ch3 | >= 1 | 1 | PASS |
| `2{,}018` in Ch3 | >= 1 | 2 | PASS |
| `q8` in Ch3 | >= 1 | 1 | PASS |
| `13` in Ch3 | >= 1 | 1 | PASS |
| `rjoub2023surveyxai` in Ch3 | >= 1 | 1 | PASS |
| `nist2026privacyframework` in Ch3 | >= 1 | 1 | PASS |
| `Phase 3` in Ch3 | 0 | 0 | PASS |
| `BLOCK` in Ch3 | 0 | 0 | PASS |
| `GSD` in Ch3 | 0 | 0 | PASS |
| `vnphish` in Ch4 | >= 1 | 2 | PASS |
| `gguf-laptop` in Ch4 | >= 1 | 1 | PASS |
| `accelerated-local` in Ch4 | >= 1 | 1 | PASS |
| `runtime` + `dev` + `train` in Ch4 | >= 1 each | 9, 4, 6 | PASS |
| `pyproject.toml` in Ch4 | >= 1 | 2 | PASS |
| `AnalysisRequest` in Ch4 | >= 1 | 1 | PASS |
| `nist2026privacyframework` in Ch4 | >= 1 | 1 | PASS |
| `Phase 3` in Ch4 | 0 | 0 | PASS |
| `GSD` in Ch4 | 0 | 0 | PASS |

## Self-Check: PASSED
