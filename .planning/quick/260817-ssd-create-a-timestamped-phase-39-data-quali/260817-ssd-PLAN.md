---
quick_id: 260817-ssd
phase: quick-260817-ssd
plan: 01
type: quick
wave: 1
depends_on: []
status: planned
autonomous: true
requirements: []
description: Create a timestamped Phase 39 data-quality correction record and add truthful report-ready methodology wording
files_modified:
  - .planning/quick/260817-ssd-create-a-timestamped-phase-39-data-quali/260817-ssd-DATA-QUALITY-CORRECTION.md
  - documents/reports/latex/chapters/03_methodology_and_system_design.tex
must_haves:
  truths:
    - "A timestamped internal record candidly preserves the detection, intermediate repair, controlled reconstruction, authorship runtime, and exact final evidence for the Zalo narrative-artifact incident."
    - "Chapter III immediately discloses the systematic scenario-framing problem and controlled model-assisted reconstruction in neutral academic language."
    - "Neither artifact presents the replacement messages as recovered originals, and the thesis does not conceal model-assisted synthetic authoring."
    - "The corrected 2,403-row snapshot is clearly distinguished from historical training and evaluation results that still refer to the earlier corpus."
    - "The user's completed Phase 39 manual-review sheet remains byte-identical and unstaged."
  artifacts:
    - path: ".planning/quick/260817-ssd-create-a-timestamped-phase-39-data-quali/260817-ssd-DATA-QUALITY-CORRECTION.md"
      provides: "Timestamped candid provenance record and report-wording contract"
      contains: "3713eb2765ede818c19e5d0fb7fe14c93d4c8f00"
    - path: "documents/reports/latex/chapters/03_methodology_and_system_design.tex"
      provides: "Concise academic disclosure in the dataset quality-check narrative"
      contains: "model-assisted"
  key_links:
    - from: "data/manifests/manifest.json"
      to: ".planning/quick/260817-ssd-create-a-timestamped-phase-39-data-quali/260817-ssd-DATA-QUALITY-CORRECTION.md"
      via: "Manifest version, timestamp, counts, validation results, catalog hash, split hashes, and implementation commit are transcribed exactly"
    - from: ".planning/quick/260817-ssd-create-a-timestamped-phase-39-data-quali/260817-ssd-DATA-QUALITY-CORRECTION.md"
      to: "documents/reports/latex/chapters/03_methodology_and_system_design.tex"
      via: "The note's report-ready wording contract is inserted into the existing quality-check discussion"
---

# Quick Task 260817-ssd: Record and disclose the Phase 39 Zalo data-quality correction

<objective>
Create one timestamped, candid provenance record for the Phase 39 Zalo narrative-artifact incident and insert a concise, truthful academic account into Chapter III now.

Purpose: Preserve the complete engineering history for later report revision while giving the current thesis a defensible disclosure that describes the defect, model-assisted synthetic reconstruction, and validation without casual provider wording or an implied recovery of original messages.

Output: A new internal correction note and one in-place Chapter III methodology insertion; the user's manual-review sheet is preserved exactly.
</objective>

<execution_context>
@C:/Users/wikiepeidia/.codex/gsd-core/workflows/execute-plan.md
@documents/reports/latex/WRITING_GUARDRAILS.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/STATE.md
@.planning/phases/39-independent-quality-re-judge/39-CONTEXT.md
@.planning/phases/39-independent-quality-re-judge/39-01-SUMMARY.md
@data/manifests/manifest.json
@src/data_pipeline/reconstruct_zalo_direct_catalog.py
@tests/data_pipeline/test_reconstruct_zalo_direct_catalog.py
@documents/reports/latex/WRITING_GUARDRAILS.md
@documents/reports/latex/chapters/03_methodology_and_system_design.tex

Locked local evidence verified during planning:

- Correction manifest version: `phase39-f01-zalo-direct-reconstruction-v1`; build timestamp: `2026-08-17T20:12:53.817089+07:00`.
- Implementation commit: `3713eb2765ede818c19e5d0fb7fe14c93d4c8f00` (`fix(data): repair F-01 Zalo narration`).
- Final canonical corpus: 2,403 rows: train 1,900, validation 252, test 251.
- Final split SHA-256 values: train `6454a271c6133f1ebbd41010390b8ea6ceae0a8ab0a75b2ab545099db3319ee8`; validation `7adfe8cd9a124dbb3d87046bb32f9fbd127d3e344c45be77c8bb9efa700aaa75`; test `019aec39979429ca8005dd299d2ddaf7d3ecfdade25938`.
- Current manifest SHA-256: `4794cedae52cc5531083a569c3e63c419335a0544f365f4a4d6245048efc2b90`; authored catalog SHA-256: `f3e1f2f0bdcb5229fc672729eac25879fb8d914ba310695b5939fb57241561fe`.
- F-01 replacement: 240 retained narrator-derived Zalo rows (60 semantic roots x 4 legacy formulas) became 300 new direct-message realizations (60 lineages x 5); corpus size changed 2,343 to 2,403.
- Zalo split support changed train 152 to 190, validation 32 to 40, and test 56 to 70 while seed-to-split assignments and every non-Zalo record remained unchanged.
- Validation passed for schema/spans, all-label support, cross-split seed disjointness, and normalized/lexical duplicates at the 0.95 threshold; the largest seed is 187/2,403 = 0.077819392426134, below the 8% cap.
- Manifested generation provenance: authoring runtime `gpt-5.6-sol-codex-session`, mode `offline-static-direct-catalog`, wording status `new-semantic-reconstruction-not-verbatim-recovery`, external API calls 0.
- The user's dirty `.planning/phases/39-independent-quality-re-judge/39-manual-review-sheet.md` has pre-task SHA-256 `6ad84867229c1d42eebc9f270aae5ca513f52cc8fabfb125baf7a1660a7407a5`. It is outside this plan's ownership: do not edit, normalize line endings, stage, or commit it.

<interfaces>
The manifest is the numerical and provenance source of truth. The internal note may name the exact authoring runtime and incident chronology. The thesis insertion follows `WRITING_GUARDRAILS.md`: short measured prose, no internal phase/workflow/file-path language, and a named manifest version for the corrected snapshot. “Offline” means the static no-external-API reconstruction mode recorded by the manifest; it must not be expanded into a claim that a local inference model authored the replacement text.
</interfaces>
</context>

<tasks>

<task type="tracer">
  <name>Task 1: Preserve the candid incident record and publish the academic correction</name>
  <read_first>
    data/manifests/manifest.json
    src/data_pipeline/reconstruct_zalo_direct_catalog.py
    tests/data_pipeline/test_reconstruct_zalo_direct_catalog.py
    .planning/phases/39-independent-quality-re-judge/39-CONTEXT.md
    documents/reports/latex/WRITING_GUARDRAILS.md
    documents/reports/latex/chapters/03_methodology_and_system_design.tex
  </read_first>
  <files>
    .planning/quick/260817-ssd-create-a-timestamped-phase-39-data-quali/260817-ssd-DATA-QUALITY-CORRECTION.md
    documents/reports/latex/chapters/03_methodology_and_system_design.tex
  </files>
  <action>
Before writing, hash the dirty manual-review sheet and require the locked value from context. Treat a mismatch as a stop condition; never “restore” or rewrite that file.

Create `260817-ssd-DATA-QUALITY-CORRECTION.md` as the complete timestamped engineering record. Use the manifest build timestamp as the correction timestamp and separate the note into: detection, first mechanical repair, deeper F-01 finding, controlled reconstruction, validation evidence, provenance, report wording, and remaining limitations. Record candidly that the independent Codex judge assigned realism 2/5 to 195 of the original 300 Zalo rows for scenario-description framing and that inspection found the outer wrapper on all 300. Record the first repair exactly as manifested: 300 wrappers were mechanically stripped, 60 same-seed near-duplicates were removed, the smaller denominator forced an 18-row seed-cap re-enforcement, and the corpus moved from 2,421 to 2,343 rows. Then record that deeper review proved all 240 retained Zalo rows still matched four narrator-derived formulas across the 60 preserved semantic roots.

Describe F-01 without euphemism: the 240 retained rows were replaced, not recovered, by 300 newly authored direct-message realizations. State that this was model-assisted synthetic authoring in the named GPT-5.6 Sol Codex session, using the preserved semantic roots and existing seed lineages; variants retained their lineage identity and split assignment. State that the static catalog path made zero external API calls. Include every locked final count and hash from context, the exact Zalo before/after split supports, all validation gates, the maximum seed count/share, and the full implementation commit. Explain that these controls preserve group integrity and artifact traceability but do not turn synthetic messages into independently observed real-world data. Also state that training/evaluation results produced from an older snapshot are historical until retraining is run against this corrected corpus.

Add a short “Report-ready wording contract” to the note, then insert its compact academic form into Chapter III immediately after the existing independent-judge limitation paragraph and before the split-summary paragraph in the `sec:quality-check` discussion. Do not create a standalone section. Use measured academic wording: an independent post-generation quality review identified systematic scenario-framing and narrative artifacts in the synthetic Zalo subset; a controlled offline, model-assisted reconstruction used preserved semantic roots and seed lineages to create new direct-message realizations; the affected records were not treated as recoverable originals; group assignments and all non-Zalo rows were preserved; and the listed integrity gates passed. Name manifest version `phase39-f01-zalo-direct-reconstruction-v1` and report the corrected total/split counts. End by distinguishing this 2,403-row corpus prepared for subsequent retraining from the historical model results elsewhere in the thesis. Avoid casual product-brand phrasing, internal workflow terminology, and claims that the authoring model was local.

Do not revise the surrounding legacy 3,000-row claims, t-test paragraph, tables, training configuration, evaluation metrics, or other chapters in this quick task; the chronology sentence must prevent the new snapshot from silently being mistaken for the earlier training snapshot. Do not add a citation: this paragraph reports project-generated evidence tied to the named manifest. Preserve existing LaTeX style and escape underscores in prose.

After both writes, re-read the manifest and recompute the final split hashes rather than trusting copied prose. Run the content/provenance gate, `git diff --check`, and the established clean XeLaTeX/BibTeX/XeLaTeX/XeLaTeX build. Recheck the manual-review sheet hash and ensure it is absent from the staged file list before committing only this task's two owned artifacts.
  </action>
  <verify>
    <automated>python -c "import hashlib,json; from pathlib import Path; m=json.loads(Path('data/manifests/manifest.json').read_text(encoding='utf-8')); core=m['manifest']; f=m['zalo_direct_semantic_reconstruction']; note=Path('.planning/quick/260817-ssd-create-a-timestamped-phase-39-data-quali/260817-ssd-DATA-QUALITY-CORRECTION.md').read_text(encoding='utf-8'); report=Path('documents/reports/latex/chapters/03_methodology_and_system_design.tex').read_text(encoding='utf-8'); required_note=[core['version'],core['build_timestamp'],core['git_commit'],f['catalog_sha256'],*[v['sha256'] for v in core['files'].values()],'4794cedae52cc5531083a569c3e63c419335a0544f365f4a4d6245048efc2b90','240','300','2,403','187','0.077819392426134','gpt-5.6-sol-codex-session']; assert all(str(x) in note for x in required_note),[x for x in required_note if str(x) not in note]; required_report=['independent post-generation quality review','scenario-framing','model-assisted','not recovered','2{,}403','1{,}900','252','251',core['version']]; assert all(x in report for x in required_report),[x for x in required_report if x not in report]; forbidden=['Chat'+'GPT','G'+'SD','Phase'+' 39']; assert not any(x in report for x in forbidden),[x for x in forbidden if x in report]; manual=Path('.planning/phases/39-independent-quality-re-judge/39-manual-review-sheet.md'); assert hashlib.sha256(manual.read_bytes()).hexdigest()=='6ad84867229c1d42eebc9f270aae5ca513f52cc8fabfb125baf7a1660a7407a5'; split_root=Path('data/splits'); assert all(hashlib.sha256((split_root/name).read_bytes()).hexdigest()==meta['sha256'] for name,meta in core['files'].items()); print('provenance/report/manual-sheet gate: PASS')"</automated>
    <automated>git diff --check -- .planning/quick/260817-ssd-create-a-timestamped-phase-39-data-quali/260817-ssd-DATA-QUALITY-CORRECTION.md documents/reports/latex/chapters/03_methodology_and_system_design.tex</automated>
    <automated>powershell -NoProfile -Command "$ErrorActionPreference='Stop'; Push-Location 'documents/reports/latex'; try { Remove-Item -Force -ErrorAction SilentlyContinue -LiteralPath @('main.aux','main.bbl','main.blg','main.log','main.out','main.toc','main.lof','main.lot'); xelatex -interaction=nonstopmode -halt-on-error main.tex | Out-Null; bibtex main | Out-Null; xelatex -interaction=nonstopmode -halt-on-error main.tex | Out-Null; xelatex -interaction=nonstopmode -halt-on-error main.tex | Out-Null; if (Select-String -LiteralPath 'main.log' -Pattern 'LaTeX Error|Fatal error|undefined references' -CaseSensitive:$false) { throw 'LaTeX log contains blocking errors' }; Write-Output 'clean thesis compile: PASS' } finally { Pop-Location }"</automated>
  </verify>
  <acceptance_criteria>
    - The timestamped correction note contains the full detection-to-reconstruction chronology, exact runtime/provenance facts, all locked counts and hashes, validation results, and the historical-snapshot limitation.
    - Chapter III contains one concise in-place correction paragraph in the existing quality-check discussion, not a new standalone section.
    - The thesis paragraph discloses independent detection, systematic narrative artifacts, controlled offline model-assisted authoring, new rather than recovered messages, preserved lineages, validation, and current split counts.
    - The paragraph names the corrected manifest and distinguishes it from the earlier corpus underlying historical training/evaluation results.
    - The manifest and live split hashes still match, the clean thesis build succeeds without blocking LaTeX/reference errors, and `git diff --check` passes.
    - `.planning/phases/39-independent-quality-re-judge/39-manual-review-sheet.md` remains SHA-256 `6ad84867229c1d42eebc9f270aae5ca513f52cc8fabfb125baf7a1660a7407a5` and is not staged or committed.
  </acceptance_criteria>
  <done>The repair has a candid timestamped audit trail and the thesis contains a truthful, academically worded disclosure tied to the verified corrected snapshot.</done>
</task>

</tasks>

<threat_model>

## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Manifest to provenance note | Machine-recorded counts, hashes, and runtime provenance are translated into human-readable incident history. |
| Provenance note to thesis | Candid implementation details are condensed into academic prose without hiding model assistance or overstating recovery. |
| Quick-task files to dirty manual sheet | Executor writes share a worktree with the user's completed, uncommitted review judgments. |
| LaTeX source to compiled thesis | New prose can introduce syntax or reference failures in the report artifact. |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-SSD-01 | Tampering | Counts and hashes in both documents | high | mitigate | Derive all exact values from the live manifest, recompute split hashes, and gate required values automatically. |
| T-SSD-02 | Repudiation | Reconstruction description | high | mitigate | Record the exact authoring runtime, zero external API calls, model-assisted status, and new-not-original wording in the candid note and thesis contract. |
| T-SSD-03 | Tampering | User-completed manual-review sheet | high | mitigate | Lock its pre-task SHA-256, exclude it from owned files, recheck after writes, and refuse to stage it. |
| T-SSD-04 | Information Disclosure | Internal process language in thesis | medium | mitigate | Keep product/runtime detail in the provenance note; use measured methodology terminology and a named manifest version in Chapter III. |
| T-SSD-05 | Tampering | Historical versus corrected dataset claims | medium | mitigate | Add an explicit chronology sentence stating that the corrected snapshot is for subsequent retraining and later reported model results remain historical. |
| T-SSD-06 | Denial of Service | Thesis compilation | low | mitigate | Run the established clean four-command compile sequence and fail on LaTeX or unresolved-reference errors. |
</threat_model>

<verification>
Completion requires three independent checks: manifest/hash-to-prose consistency, byte preservation of the user's manual-review sheet, and a clean thesis compile. The task fails closed on any mismatch and never updates an evidence value to make the prose pass.
</verification>

<success_criteria>
- The timestamped correction note exists and is sufficient to reconstruct what was detected, what was mechanically repaired, what was newly authored, by which runtime, and under which validation controls.
- Chapter III immediately contains neutral, truthful, report-ready methodology prose tied to manifest `phase39-f01-zalo-direct-reconstruction-v1`.
- The corrected and historical dataset snapshots are not conflated.
- Exact counts, hashes, commit provenance, validation claims, and manual-sheet preservation pass automated checks.
- The thesis compiles clean through XeLaTeX/BibTeX/XeLaTeX/XeLaTeX.
</success_criteria>

## Artifacts this quick task produces

- `.planning/quick/260817-ssd-create-a-timestamped-phase-39-data-quali/260817-ssd-DATA-QUALITY-CORRECTION.md` — candid timestamped provenance plus the report wording contract.
- `documents/reports/latex/chapters/03_methodology_and_system_design.tex` — one concise correction paragraph in the existing data-quality discussion.

## Source Coverage Audit

| SOURCE | ID | Feature/Requirement | Task | Status | Notes |
|--------|----|---------------------|------|--------|-------|
| GOAL | — | Preserve the incident for later documentation and update the report now | 1 | COVERED | Both the internal record and in-place thesis disclosure are owned by the tracer task. |
| REQ | — | No ROADMAP requirement IDs are assigned to this quick task | — | N/A | The caller supplied the bounded quick-task scope; ROADMAP.md must not change. |
| RESEARCH | — | No external research or new dependency | — | EXCLUDED | Local manifest, implementation commit, tests, and writing guardrails are sufficient. |
| CONTEXT | Phase 39 report integration | Keep quality evidence in Chapter III's existing quality-check area | 1 | COVERED | The correction is inserted in place and does not create a new standalone section. |
| CALLER | Provenance | Candid timestamped facts, including model assistance, without casual provider wording in the report | 1 | COVERED | Runtime detail stays in the note; neutral but explicit model-assisted wording goes into the thesis. |
| CALLER | Preservation | Do not alter the user's completed manual-review sheet or ROADMAP.md | 1 | COVERED | Fixed SHA-256 and staging gates protect the sheet; ROADMAP.md is absent from owned files. |
| MANIFEST | F-01 | Use only locally verified final numbers, hashes, validation results, and commit provenance | 1 | COVERED | Required-value and live-split-hash gates bind prose to the manifest. |

<output>
Execution creates the timestamped correction note, updates only Chapter III's quality-check prose, and creates `260817-ssd-SUMMARY.md`; it does not change ROADMAP.md or the Phase 39 manual-review sheet.
</output>
