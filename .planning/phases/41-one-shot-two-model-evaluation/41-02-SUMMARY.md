---
phase: 41-one-shot-two-model-evaluation
plan: 02
subsystem: evaluation
tags: [held-out-evaluation, qwen, phobert, claim-before-open, evidence]
requires:
  - phase: 40-multi-model-training-evidence
    provides: frozen Qwen QLoRA and PhoBERT model authorities
provides:
  - one terminal shared-cohort held-out evaluation
  - hash-verified two-model metrics and prediction evidence
  - deferred deployment-fit disposition
  - mandatory external provenance erratum for downstream reporting
affects: [42-report-overhaul, 43-slide-defense-overhaul]
actuals:
  tokens: 65000
  tasks: 3
  commits: 10
tech-stack:
  added: []
  patterns: [protected ProgramData authority, claim-before-open, copy-only verified export]
key-files:
  created:
    - data/models/phase41/verified-export/9ac54d58c273ab0a8c2f2b4b61e472a51ca94231a94b6847637ecad6ceee49f7/results.json
    - data/models/phase41/verified-export/9ac54d58c273ab0a8c2f2b4b61e472a51ca94231a94b6847637ecad6ceee49f7/evidence-manifest.json
    - data/models/phase41/phase41-provenance-erratum.json
  modified:
    - src/model_adaptation/phase41_evaluation.py
    - src/model_adaptation/phase41_protocols.py
key-decisions:
  - "The one frozen held-out result is terminal and cannot drive repair, retraining, selection, or replay."
  - "Deployment fitting remains deferred; Phase 41 authorizes no all-data fit."
requirements-completed: [EVAL-08, EVAL-09]
coverage:
  - id: D1
    description: Exactly one claimed Qwen/PhoBERT evaluation over the shared 220-row cohort
    requirement: EVAL-08
    verification:
      - kind: integration
        ref: phase41-verify-evidence twice, manifest 9ac54d58c273ab0a8c2f2b4b61e472a51ca94231a94b6847637ecad6ceee49f7
        status: pass
    human_judgment: false
  - id: D2
    description: Both model results, safety counts, matrices, and deferred-fit policy are frozen
    requirement: EVAL-09
    verification:
      - kind: integration
        ref: verified-export-receipt.json, 16 destination artifacts byte-verified
        status: pass
    human_judgment: false
duration: 8h
completed: 2026-08-26
status: complete
---

# Phase 41 Plan 02: One-Shot Two-Model Evaluation Summary

**One irreversible shared-cohort evaluation produced hash-sealed Qwen and PhoBERT results, with deployment fitting explicitly deferred.**

## Performance

- **Tasks:** 3/3
- **Held-out cohort:** 220 rows, SHA-256 `6f208fb6cd9399b8934225e6a25efd65d49bbb4f4846360837f6835a2561b6d7`
- **Evidence manifest:** `9ac54d58c273ab0a8c2f2b4b61e472a51ca94231a94b6847637ecad6ceee49f7`
- **Export:** 16 artifacts plus receipt; every destination hash rechecked
- **Corrective erratum:** `data/models/phase41/phase41-provenance-erratum.json`, SHA-256 `c7be74346f0e217c382e556fbf0a730cb33be50356d4155356a5b024871a1672`

## Results

| Model | Accuracy | Macro F1 | Weighted F1 | Invalid | Risky -> benign |
|---|---:|---:|---:|---:|---:|
| Qwen QLoRA | 0.981818 | 0.980493 | 0.981848 | 0 | 1 |
| PhoBERT | 0.990909 | 0.990892 | 0.990925 | 0 | 1 |

Qwen confusion matrix: `[[66,3,0,1,0],[0,35,0,0,0],[0,0,49,0,0],[0,0,0,66,0]]`.

PhoBERT confusion matrix: `[[69,0,0,1,0],[0,35,0,0,0],[0,0,49,0,0],[0,1,0,65,0]]`.

PhoBERT is higher on accuracy, macro/weighted F1, bank-impersonation recall/F1, and Zalo precision/F1. Qwen is higher on benign precision/recall/F1. Task-scam metrics, invalid-output count, and both risky-error counts tie.

## Execution and Audit Trail

Five superseded attempts failed before claim and before held-out access, and each was preserved rather than retried:

1. Repository bootstrap rejected OneDrive reparse ancestry.
2. Staged loader rejected missing source-location metadata.
3. Staged launcher rejected a missing explicit `OutputRoot` argument.
4. Captured-helper identity used unstable marshal reference-table bytes.
5. Base leases were compared with semantic snapshot hashes instead of their bound tree hashes.

The final authority `c3d378dfdf920dc10f4f0656560d576055ad89c18bbe0c055ea03c32f3e01ab1` passed duplicate protected staged-source model/lease smokes. The exact staged launcher was then invoked once, created the durable claim before access, completed both models, and exited `0`. No retry is permitted.

### Corrective provenance disclosure

The terminal statistical result remains one two-model evaluation pass, but the absolute global zero-filesystem-access claim is retracted. The default downstream-contract regression parsed, statted, and hashed the live splits during at least two broad pre-run pytest executions, and the focused planning-label test repeated that read once after the terminal run. Those automated integrity reads did not expose row content to either model or the user, call an external service, or influence training, tuning, thresholds, model selection, repair, inference, or retry. The full machine-readable disclosure is the mandatory non-sealed erratum above; the frozen export was not modified or resealed.

The earlier captured-helper failure and later Qwen model-lease failure are distinct. The legacy frozen member named `captured_helper_preclaim_failure_audit` binds the lease audit; the actual captured-helper audit remains a separate committed record. Their exact paths, schemas, failure stages, and hashes are disambiguated in the erratum.

## Deviations from Plan

### Auto-fixed Issues

- **Rule 1:** Replaced marshal-byte callable identity with strict recursive code-object structure checks.
- **Rule 1:** Corrected base-lease identity comparison and validated both bundle/base roots for both models.
- **Rule 3:** Moved operational authority and staged source to protected non-reparse ProgramData storage.
- **Rule 1:** Fixed the stale planning-label test to accept the dated amended Phase 40 label while preserving the exactly-one-decision assertion.

The original export command completed its copy and receipt, then its console print hit the Windows legacy `charmap` encoder because the repository path contains Vietnamese characters. The completed frozen export was not rerun or altered. Release remediation now uses console-safe output and a transactional stage/verify/publish boundary, and accepts an already-complete identical export idempotently.

## Tests

- Phase 41 focused suite: 132 passed.
- Final protected full suite before the run: 1,353 passed; one stale planning-label assertion failed.
- Stale assertion after its bounded test-only fix: 1 passed.
- `phase41-verify-evidence`: passed twice with identical manifest SHA.
- Release remediation ran focused fixtures only: 3 downstream metadata/opt-in tests and 4 transactional-export/legacy-console tests passed. The broad suite and explicit live-data audit were not run.

## Commits

`4aa2bda`, `ded0349`, `bf05876`, `87d1d67`, `e2cb519`, `14954ed`, `85ecdf0`, `76c568e`, `b658ea4`, `6a3830d`, `9037404`, `dde319e`.

## Next Phase Readiness

Phase 42 and Phase 43 may consume only the committed verified export together with the hash-identified external erratum. They must disclose prior human/content exposure and the automated integrity reads, avoid literal untouched/zero-access claims, report PhoBERT's measured advantage plainly, give ordinary LoRA no held-out accuracy claim, and preserve the no-retraining/no-repair terminal policy.

## Self-Check: PASSED

The summary, committed export, evidence manifest, terminal record, deployment-fit disposition, mandatory external erratum, review resolution, and listed commits exist. The sealed export tree was not modified.
