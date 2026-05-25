# Phase 5: Recall-Priority Evaluation and Release Gates - Context

**Gathered:** 2026-05-25
**Status:** Ready to plan

## Phase Boundary

Turn the completed local detector into a measurable offline release-decision workflow with held-out evaluation metrics, recall-priority blocking rules, and an explanation-quality acceptance check.

**Scope guardrails:**

- Keep v1 text-only and offline or local-first.
- Build on the completed Phase 4 runtime outputs instead of adding new detection features first.
- Reuse existing local evaluation and reporting seams where possible instead of introducing cloud judging or hosted evaluation dependencies.
- Do not build the proposal's mini frontend demo inside Phase 5; it is now locked as a separate Phase 6 deliverable in the same milestone.
- Do not reopen model-family selection, training-hardware strategy, or OCR or voice expansion in this phase.

## Implementation Decisions

- **D-01:** Release remains hard-blocked on recall misses for high-harm scam classes.
- **D-02:** All non-benign in-scope labels are hard-blocking for recall: `bank_impersonation`, `zalo_social_engineering`, and `task_scam`.
- **D-03:** The recall gate uses one uniform per-label recall floor of `0.90` across the risky labels.
- **D-04:** The explanation rubric must score grounding, label alignment, and safe recommendation quality.
- **D-05:** The explanation rubric applies to risky predictions rather than all benign outputs.
- **D-06:** Explanation quality is advisory unless it exposes fabricated evidence or unsafe recommendations, which should block release.
- **D-07:** Explanation quality should be judged with a hybrid method: deterministic checks plus a curated manual review sample.
- **D-08:** Phase 5 should extend the repo's existing recall-first selection logic instead of inventing a new balanced-score release philosophy.
- **D-09:** Phase 4's contract-stable runtime output remains the measurement boundary for Phase 5 release gates.
- **D-10:** The proposal-aligned minimal local demo UI is a separate Phase 6 deliverable after Phase 5, not part of the current phase implementation boundary.
- **D-11:** Phase 5 should emit both a human-readable markdown release report and a machine-readable JSON artifact.
- **D-12:** The release artifact verdict model is `PASS`, `BLOCK`, or `FLAG` rather than binary-only.
- **D-13:** The markdown report should live under the Phase 5 planning folder, while the JSON artifact should live under `data/manifests/`.
- **D-14:** Every release artifact must include overall and per-class metrics, explicit blocker or flag reasons, and an explanation-rubric summary.

## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Requirements and Status

- `.planning/REQUIREMENTS.md` - `EVAL-01`, `EVAL-02`, and `EVAL-03` define the Phase 5 acceptance surface.
- `.planning/PROJECT.md` - Core constraints remain text-only v1, offline or local-first behavior, and recall-priority safety.
- `.planning/ROADMAP.md` - Phase 5 goal, dependency on Phase 4, and release-gate success criteria.
- `.planning/STATE.md` - Phase 4 is complete and Phase 5 discussion is now active.
- `documents/internship-proposal.md` - Proposal includes a text-only UI task, which is now locked as a separate Phase 6 deliverable rather than being folded into Phase 5.

### Existing Implementation Surfaces

- `src/model_adaptation/pilot.py` - Existing pilot selection already weights recall above quality, memory fit, and latency.
- `src/model_adaptation/training.py` - Current training summaries persist trainer metrics, but not the held-out F1 and per-class release report required by Phase 5.
- `src/runtime/contracts.py` - Stable Phase 4 output contract defines the result surface that release evaluation must measure.
- `src/runtime/service.py` - Normalize-first analysis entrypoint that should remain the runtime orchestration seam.
- `src/runtime/doctor.py` - Existing operator-facing readiness report surface that may host gate summaries.
- `src/runtime/cli.py` - Existing CLI surface where release-gate reporting should integrate if operator commands are needed.

### Existing Test and Data Surfaces

- `tests/runtime/test_runtime_profiles.py` - Confirms cross-profile behavior remains aligned and explicit.
- `tests/runtime/test_doctor.py` - Covers existing doctor behavior and fail-closed local guidance.
- `data/splits/train.jsonl`, `data/splits/val.jsonl`, and `data/splits/test.jsonl` - Current offline split artifacts available for held-out evaluation design.

## Existing Code Insights

### Reusable Assets

- `src/model_adaptation/pilot.py` already encodes recall-first prioritization with recall weighted above quality, memory fit, and latency in `_effective_score()`.
- Phase 4 already stabilized the runtime result surface around risk tiers, threat labels, grounded cues, recommendations, backend identity, and fail-closed guidance.
- The repo already has operator-facing reporting surfaces in the runtime doctor and CLI paths, which can likely host release-gate summaries without inventing an unrelated control plane.

### Established Patterns

- Structured artifacts and manifests already exist across the repo, so Phase 5 should likely emit both a machine-readable result and a human-readable summary instead of choosing only one.
- Safety behavior is already fail-closed and explicit about runtime profile choice, so release-gate policy should preserve that same bias instead of allowing silent fallback or hidden overrides.
- The project already treats recall as the dominant safety signal during pilot selection, so Phase 5 should keep that policy consistent at release time.
- The repo already separates planning docs from machine-oriented manifests, which matches the newly selected markdown-plus-JSON release artifact split.

### Gaps Phase 5 Must Close

- No explanation-rubric implementation exists yet for grounding, label alignment, and safe recommendation checks.
- `src/model_adaptation/training.py` currently persists training-run metrics, but not the final held-out F1 and per-class report that Phase 5 requires.

## Deferred Ideas

- The detailed Phase 6 UI scope is still open even though the roadmap now includes that phase.
- The exact markdown and JSON filenames remain open.

## Current Re-entry Point

- Phase 5 discussion is complete enough to plan.
- The next actionable step is to break Phase 5 into plan waves around held-out evaluation, gating logic, artifact generation, and explanation-rubric validation.
- Planning should start from held-out evaluation design and artifact shape, not from frontend demo work or new model adaptation experiments.

---

*Phase: 05-recall-priority-evaluation-and-release-gates*
*Context created: 2026-05-25 after Phase 4 closeout and initial Phase 5 discussion*
