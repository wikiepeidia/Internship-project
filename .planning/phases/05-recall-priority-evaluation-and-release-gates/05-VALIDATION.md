<!-- markdownlint-disable MD003 MD022 MD036 MD041 MD060 -->

---
phase: 05
slug: recall-priority-evaluation-and-release-gates
status: audited
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-25
---

# Phase 05 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `python -m pytest tests/model_adaptation/test_schemas.py tests/model_adaptation/test_release_readiness.py tests/model_adaptation/test_release_evaluation.py -q` |
| **Full suite command** | `python -m pytest tests/model_adaptation tests/runtime/test_doctor.py -q` |
| **Estimated runtime** | ~30-45 seconds for targeted checks; manual explanation review is separate |

---

## Sampling Rate

- **After every task commit:** Run the narrowest task-specific pytest command from the active plan.
- **After every plan wave:** Run the relevant Phase 5 grouped suite for that wave.
- **Before `/gsd-verify-work`:** Full Phase 5 model-adaptation suite plus the `tests/runtime/test_doctor.py` regression must be green, and the curated explanation review pack must be completed.
- **Max feedback latency:** 45 seconds for automated checks; manual review pack verification is human-gated.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 05-01-01 | 01 | 1 | EVAL-01, EVAL-02 | Contract drift | Typed Phase 5 models lock `PASS/BLOCK/FLAG`, risky-label metadata, evaluation rows, metrics, rubric summaries, and artifact structure before evaluator logic lands | unit | `python -m pytest tests/model_adaptation/test_schemas.py -q` | ✅ existing | ✅ green |
| 05-01-02 | 01 | 1 | EVAL-01, EVAL-02 | Held-out blind spot | Release readiness fails closed when any risky label has zero held-out support and records explicit blocker reasons | unit + regression | `python -m pytest tests/model_adaptation/test_release_readiness.py -q` | ✅ existing | ✅ green |
| 05-02-01 | 02 | 2 | EVAL-01 | Runtime-boundary drift | Held-out rows are evaluated through the shipped Phase 4 runtime contract without leaking backend-private payloads or inventing channel metadata | unit + integration | `python -m pytest tests/model_adaptation/test_release_evaluation.py -q` | ✅ existing | ✅ green |
| 05-02-02 | 02 | 2 | EVAL-01, EVAL-02 | Metric honesty | Overall and per-label metrics keep zero-support labels visible and preserve multilabel predictions for later recall gating | unit | `python -m pytest tests/model_adaptation/test_release_evaluation.py -q` | ✅ existing | ✅ green |
| 05-03-01 | 03 | 3 | EVAL-03 | Rubric-policy drift | Deterministic explanation scoring reuses Phase 4 grounding and safety semantics and keeps blockers limited to fabricated evidence or unsafe recommendations | unit + regression | `python -m pytest tests/runtime/test_local_model.py tests/model_adaptation/test_explanation_review.py -q` | ✅ existing | ✅ green |
| 05-03-02 | 03 | 3 | EVAL-03 | Review-pack instability | The curated manual review pack is risky-only, deterministic for the same inputs, and generated from one saved evaluation snapshot through a pre-verdict command | unit + integration | `python -m pytest tests/model_adaptation/test_explanation_review.py tests/model_adaptation/test_cli.py -q` | ✅ existing | ✅ green |
| 05-03-H1 | 03 | 3 | EVAL-03 | Human-review blind spot | The manual review pack is completed against the saved evaluation snapshot and only fabricated evidence or unsafe recommendations are marked as blockers | human verify | n/a | ✅ planned checkpoint | ✅ green |
| 05-04-01 | 04 | 4 | EVAL-01, EVAL-02, EVAL-03 | Verdict drift | Final gate blocks on zero support, recall misses below `0.90`, explanation blockers, and snapshot-to-review-pack run mismatches while preserving advisory flags | unit + integration | `python -m pytest tests/model_adaptation/test_release_gates.py -q` | ✅ existing | ✅ green |
| 05-04-02 | 04 | 4 | EVAL-01, EVAL-02, EVAL-03 | Operator-surface drift | One final operator command consumes the saved evaluation snapshot plus completed review pack, writes markdown plus JSON artifacts, prints verdict and paths, and doctor reads the latest summary without recomputing evaluation | integration | `python -m pytest tests/model_adaptation/test_cli.py tests/runtime/test_doctor.py -q` | ✅ existing | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/model_adaptation/test_schemas.py` - typed verdict, metric, rubric, and evaluation-row contract coverage
- [ ] `tests/model_adaptation/test_release_readiness.py` - held-out support audit and fail-closed risky-label coverage checks
- [ ] `tests/model_adaptation/test_release_evaluation.py` - contract-bound batch evaluation plus explicit-label metric coverage
- [ ] `tests/model_adaptation/test_explanation_review.py` - deterministic risky-only rubric and manual review-pack coverage
- [ ] `tests/model_adaptation/test_release_gates.py` - recall-first verdict synthesis and artifact-content coverage
- [ ] `tests/model_adaptation/test_cli.py` - release-eval command wiring and artifact-path output coverage
- [ ] `tests/runtime/test_doctor.py` - latest release-summary read path without recomputation coverage

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Curated explanation review pack is completed with blocker vs flag findings | EVAL-03 | The hybrid rubric explicitly requires human judgment for fabricated evidence and unsafe-advice confirmation | Open the generated review pack, review only risky predictions, mark `BLOCK` only for fabricated evidence or unsafe recommendations, and save the completed pack for Plan 05-04 |
| Final markdown release artifact is readable and free of raw message leakage | EVAL-01, EVAL-02, EVAL-03 | Automated tests can assert structure, but a human should confirm the operator-facing report is concise and privacy-safe | Run the release-eval command, inspect the markdown report, and confirm it includes metrics, reasons, and rubric summary without raw text dumps |

---

## Validation Sign-Off

- [x] All planned task slices have task-level automated verification commands or an explicit human checkpoint.
- [x] Sampling continuity: no three consecutive tasks without automated verify.
- [x] Wave 0 covers new schema, readiness, evaluator, rubric, gate, and operator test surfaces before broad release runs.
- [x] No watch-mode flags.
- [x] Feedback latency target stays under 45 seconds for automated checks.
- [x] `nyquist_compliant: true` set in frontmatter.

**Approval:** audited 2026-05-25

---

## Validation Audit 2026-05-25

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |

### Audit Notes

- `python -m pytest tests/model_adaptation/test_schemas.py tests/model_adaptation/test_release_readiness.py tests/model_adaptation/test_release_evaluation.py -q` passed with `15 passed`.
- `python -m pytest tests/runtime/test_local_model.py tests/model_adaptation/test_explanation_review.py tests/model_adaptation/test_release_gates.py tests/model_adaptation/test_cli.py tests/runtime/test_doctor.py -q` passed with `35 passed`.
- The saved review pack at `.planning/phases/05-recall-priority-evaluation-and-release-gates/05-explanation-review-pack.json` is marked `review_completed: true` with `review_notes: approved`.
- `python -m pytest tests/data_pipeline/test_splitter.py tests/data_pipeline/test_manifest.py -q` passed with `13 passed` after the post-audit split repair.
- The saved markdown and JSON release artifacts from `phase5-review-sample-val` were manually inspected and remain privacy-safe at the report level.
- Post-audit data repair: `audit_release_eval_support` on `data/splits/recovered-balanced/val.jsonl` now returns `PASS` with support `{bank_impersonation: 56, zalo_social_engineering: 75, task_scam: 18, benign: 61}`. The old `BLOCK` artifact remains a truthful historical result for the earlier `data/splits/val.jsonl` batch, but it is no longer the best current holdout slice.

<!-- markdownlint-enable MD003 MD022 MD036 MD041 MD060 -->