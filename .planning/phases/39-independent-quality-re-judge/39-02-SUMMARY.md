---
phase: 39-independent-quality-re-judge
plan: 02
subsystem: data-pipeline
tags: [human-audit, provenance, seed-lineage, deterministic-split, rollback]

requires:
  - phase: 39-independent-quality-re-judge
    provides: independent Codex judge output, repaired 2,403-row live corpus, and the completed 324-item compact human audit
provides:
  - Strict, identity-bound interpretation of all 324 human triage decisions
  - Audited 91-drop / 57-admitted-relabel / 176-lineage-quarantine disposition
  - Reload-validated 2,103-row provisional candidate with whole-seed splits and global 8% cap
  - Closed, full-record-digest semantic-repair contract for the next judge step
  - Defense-safe report note distinguishing semantic approval from training admission
affects: [39-03, 39-04, 39-05, phase-40, phase-42-report]

actuals:
  tokens: 22117
  tasks: 2
  commits: 0

tech-stack:
  added: []
  patterns: [conservative content identity, label-only mutation, OS-released run lock, verified multi-file rollback, deterministic restart]

key-files:
  created:
    - src/data_pipeline/apply_mislabel_triage.py
    - tests/data_pipeline/test_apply_mislabel_triage.py
    - data/processed/phase39-mislabel-candidate/
    - .planning/phases/39-independent-quality-re-judge/39-MISLABEL-AUDIT.md
  modified: []

key-decisions:
  - "Human label approval and training admission are separate: 176 Zalo relabels from seed_157ce0adb043 are retained in evidence but quarantined."
  - "Candidate 47 from seed_c6c8772ac332 is the only independently seeded Zalo relabel admitted from this targeted audit."
  - "Human triage changes only label; risk tier, spans, and explanation require a separate hash-bound semantic decision."
  - "The canonical corpus remains unchanged until later judge and promotion gates pass."

patterns-established:
  - "Identity binding: seed_id plus SHA-256 of NFC/newline-normalized complete text; historical row coordinates are evidence only."
  - "Stage transaction: build bytes first, acquire nonblocking OS lock, atomically replace all outputs, reload-verify, and restore every original byte on failure."

requirements-completed: []

coverage:
  - id: D1
    description: All 324 compact human decisions are parsed exactly once and uniquely rebound to current records.
    requirement: JUDGE-01
    verification:
      - kind: unit
        ref: tests/data_pipeline/test_apply_mislabel_triage.py#parser_identity_and_disposition_tests
        status: pass
      - kind: integration
        ref: python -m pytest tests/data_pipeline/test_apply_mislabel_triage.py -q --basetemp .pytest_tmp_3902_final (25 passed)
        status: pass
    human_judgment: false
  - id: D2
    description: A lineage-safe 2,103-row candidate and complete decision/quarantine/cap provenance are staged without touching live data.
    requirement: JUDGE-01
    verification:
      - kind: integration
        ref: python -m src.data_pipeline.apply_mislabel_triage --stage-only
        status: pass
      - kind: integration
        ref: identical second stage returned candidate_reused_without_rewrite=true
        status: pass
      - kind: integration
        ref: python -m pytest tests/data_pipeline/ -q --basetemp .pytest_tmp_data_pipeline (260 passed)
        status: pass
    human_judgment: false
  - id: D3
    description: Final semantic judge coverage and final report integration remain later Phase 39/42 gates.
    requirement: JUDGE-03
    verification: []
    human_judgment: true
    rationale: The staged candidate deliberately awaits hash-bound semantic review and is not yet the frozen corpus or final report state.

duration: about 2h 15m
completed: 2026-08-20
status: complete
---

# Phase 39 Plan 02: Mislabel Triage Candidate Summary

**All 324 human decisions are now machine-auditable, while 176 non-independent Zalo variants are quarantined and a structurally clean 2,103-row candidate is staged without changing the live corpus.**

## Performance

- **Duration:** about 2h 15m
- **Completed:** 2026-08-20T22:30:00+07:00
- **Tasks:** 2
- **Implementation/evidence files created:** 4 logical deliverables plus the ignored candidate bundle

## Accomplishments

- Parsed candidates 1–324 exactly once, preserving raw decisions and notes. Only candidate 103 (`Drop`) and candidate 320 (`Beigin`) use explicit documented normalization.
- Reconstructed the 329 historical judge flags and uniquely rebound the 324 still-live records by `seed_id` plus conservative full-text SHA-256; stale split/row coordinates never authorize mutation.
- Applied exactly 91 drops, 57 admitted label-only relabels, and 176 lineage quarantines. Candidate 47 is the sole independently seeded Zalo admission from this targeted set.
- Applied the existing iterative global 8% cap, recorded all 33 additional removals, and reassigned complete seed groups with salt `phase39-mislabel-triage-v1`.
- Staged and reload-validated 2,103 rows: train 1,665, validation 218, test 220; totals are bank 743, task scam 404, benign 655, and Zalo 301.
- Added a closed semantic-repair contract that accepts only risk tier, literal spans, and XAI explanation against an exact seven-field record digest.
- Generated `39-MISLABEL-AUDIT.md` with report-safe language: targeted review of judge-flagged records, not independent annotation of the full corpus.

## Task Commits

No staging or commits were performed. The user explicitly prohibited `git add`/commit for this work, so all implementation, test, audit, and raw-review evidence remains in the worktree. The plan's force-track/commit acceptance clause is intentionally **not claimed as passed**.

## Files Created

- `src/data_pipeline/apply_mislabel_triage.py` — strict parser, content-identity binder, label-only dispositions, semantic-repair schema, cap/split projection, integrity gates, stage transaction, and rollback-capable promotion seam.
- `tests/data_pipeline/test_apply_mislabel_triage.py` — parser, identity, preservation, lineage, semantic contract, full projection, idempotence, lock, drift, write/reload/promotion failure, and rollback tests.
- `data/processed/phase39-mislabel-candidate/` — ignored staged splits, manifest, 324-row decision manifest, 176-row quarantine, 33-row cap-drop log, and deterministic run descriptor.
- `.planning/phases/39-independent-quality-re-judge/39-MISLABEL-AUDIT.md` — immutable-evidence and future-report note.

The protected `39-manual-review-sheet.md`, protected historical `39-mislabel-triage-sheet.md`, and authoritative raw `MISLABEL triage.md` were not written.

## Candidate Result

| Split | Rows | Bank | Task scam | Benign | Zalo | SHA-256 |
|---|---:|---:|---:|---:|---:|---|
| train | 1,665 | 597 | 306 | 517 | 245 | `9aff01cc3bc0300e5ef92c8c8463d25c9daccf6afcf9ebd2452b8fa32fdde2af` |
| val | 218 | 76 | 49 | 72 | 21 | `7eaafe13a354feb81e6fa8b6a1ae55d74067362cc942332ee4bbd9c57945b81d` |
| test | 220 | 70 | 49 | 66 | 35 | `84ffc0620d3d0e57af300e1bf2e9330e0bbd7fa0178258a640de85f02c4f4bc3` |

- Run ID: `ca975024dcd64ead9359bdbd9a80d56f1b941b87a6ba3c7befc3ab2bf2d1e004`
- Global maximum seed share: 168/2,103 = 7.9886%
- Zalo lineage: 301 rows across 61 seeds; maximum 5/301 = 1.6611%
- Cross-split seed leakage: zero
- Invalid literal spans: zero
- Normalized or lexical duplicates at 0.95: zero
- Live promotion: false

## Verification

- Focused tracer command: 10 passed.
- Final semantic-repair focused command: 4 passed, including duplicate-digest rejection.
- Dedicated module: **25 passed**, 2 unchanged third-party SWIG deprecation warnings.
- Full data-pipeline regression: **260 passed**, 2 third-party SWIG deprecation warnings, no failures.
- Real stage command: passed; a later identical rerun returned `candidate_reused_without_rewrite=true`.

Input and protected artifact hashes remained byte-identical before/after:

- live train: `6454a271c6133f1ebbd41010390b8ea6ceae0a8ab0a75b2ab545099db3319ee8`
- live val: `7adfe8cd9a124dbb3d87046bb32f9fbd127d3e344c45be77c8bb9efa700aaa75`
- live test: `019aec39979429ca8005dd299d2ddaf7d3ecfdade259eecc4d3129adaed25938`
- live manifest: `4794cedae52cc5531083a569c3e63c419335a0544f365f4a4d6245048efc2b90`
- historical merged judge: `e8b4d947271717e56556a74136c57d83dd58589c78699d557999140a9fb55750`
- manual review sheet: `e078b3bf6efd29c8f80f7ea8afaeb1121803c4ce8322fe4a497dd997b9b17743`
- historical triage sheet: `39ca1768c0a114156aece97e7dff2269b074a5125d59b8592f215e3e36415cc7`
- authoritative compact audit: `c408dcf4161d84056b7c22e1fb3e975352a52cd5fbf2b111f11b5dfece0c089c`

## Decisions Made

- Human semantic approval does not override group-integrity requirements. The 176 dominant-seed Zalo rows remain available as evidence but are excluded from training.
- Risk tier is contextual, not mechanically derived from label. The human applier therefore does not silently rewrite risk, spans, or explanation.
- The candidate uses an OS-released nonblocking file lock, so a crashed process cannot leave a permanent logical lock; multi-file writes still receive verified rollback.
- Manifest history is deep-copied and extended; the candidate is explicitly marked `staged_projection_awaiting_semantic_judgment`.

## Deviations from Plan

### User-directed commit deferral

- **Issue:** The plan originally requested force-tracking the raw audit and atomic task commits.
- **Resolution:** The parent task explicitly prohibited all staging and commit operations. No Git index operation was run, and the summary does not claim force-track/commit acceptance.
- **Impact:** Runtime/test acceptance passes; repository-history acceptance remains deferred.

### Sandbox-local pytest base directory

- **Issue:** The managed Windows sandbox denied pytest access to its default `%TEMP%/pytest-of-wikiepeidia` directory.
- **Resolution:** Full write-path suites used a workspace-local `--basetemp`; those test-only directories were verified to be inside the workspace and removed after each run.
- **Impact:** No implementation defect and no change to test semantics.

## Issues Encountered

No implementation-related test failure remains. Two third-party SWIG deprecation warnings are unchanged and non-blocking.

## User Setup Required

None. The workflow is entirely local and made zero external API calls.

## Next Phase Readiness

- Plan 39-03 can consume the staged candidate and exact record-digest contract to author semantic delta decisions.
- The live 2,403-row corpus and manifest are intentionally unchanged.
- JUDGE-01 and JUDGE-03 are not marked complete here: final semantic judge composition, promotion/freeze, and final report placement remain later gates.

---
*Phase: 39-independent-quality-re-judge*
*Completed: 2026-08-20*
