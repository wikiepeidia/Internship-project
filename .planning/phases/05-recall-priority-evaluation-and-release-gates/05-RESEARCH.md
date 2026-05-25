<!-- markdownlint-disable MD022 MD032 MD033 MD034 MD055 MD056 MD060 -->

# Phase 5: Recall-Priority Evaluation and Release Gates - Research

**Researched:** 2026-05-25  
**Domain:** Offline release evaluation over the contract-stable Phase 4 runtime with recall-blocking safety gates and explanation-quality review  
**Confidence:** MEDIUM

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
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

### the agent's Discretion
- No explicit discretion section was recorded in [CITED: 05-CONTEXT.md](.planning/phases/05-recall-priority-evaluation-and-release-gates/05-CONTEXT.md). Research therefore focuses on the locked evaluation policy, the current repo seams, and the most defensible implementation surface.

### Deferred Ideas (OUT OF SCOPE)
- The detailed Phase 6 UI scope is still open even though the roadmap now includes that phase.
- The exact markdown and JSON filenames remain open.
</user_constraints>

<phase_requirements>
## Phase Requirements

Derived from [CITED: REQUIREMENTS.md](.planning/REQUIREMENTS.md) and [CITED: ROADMAP.md](.planning/ROADMAP.md).

| ID | Description | Research Support |
|----|-------------|------------------|
| EVAL-01 | Offline evaluation reports include overall F1 score and per-class metrics on held-out data. | Use the existing typed `DatasetRecord` loader plus the Phase 4 public `AnalysisResult` contract, then compute explicit-label per-class metrics with `scikit-learn`, which is already a project dependency and officially supports per-class precision, recall, F-score, support, and confusion matrices. [CITED: src/data_pipeline/schemas.py](src/data_pipeline/schemas.py); [CITED: src/model_adaptation/data.py](src/model_adaptation/data.py); [CITED: src/runtime/contracts.py](src/runtime/contracts.py); [CITED: pyproject.toml](pyproject.toml); [CITED: https://scikit-learn.org/stable/modules/generated/sklearn.metrics.precision_recall_fscore_support.html](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.precision_recall_fscore_support.html); [CITED: https://scikit-learn.org/stable/modules/generated/sklearn.metrics.classification_report.html](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.classification_report.html) |
| EVAL-02 | Release gating enforces recall-priority thresholds that minimize false negatives for high-harm scam classes. | Keep the gate label-specific and fail-closed over the three risky labels, mirroring the existing recall-first pilot philosophy instead of introducing a new blended score. [CITED: 05-CONTEXT.md](.planning/phases/05-recall-priority-evaluation-and-release-gates/05-CONTEXT.md); [CITED: src/model_adaptation/pilot.py](src/model_adaptation/pilot.py) |
| EVAL-03 | Release gating includes explanation quality checks using a defined rubric for correctness, relevance, and actionability. | Reuse the existing Phase 4 grounding and recommendation-safety semantics for deterministic checks, then add a small manual review layer over risky outputs only so advisory quality issues become `FLAG` while unsafe or fabricated output becomes `BLOCK`. [CITED: src/runtime/analyzers/local_model.py](src/runtime/analyzers/local_model.py); [CITED: tests/runtime/test_local_model.py](tests/runtime/test_local_model.py); [CITED: tests/runtime/test_service.py](tests/runtime/test_service.py) |

</phase_requirements>

## Project Constraints

- v1 remains text-only and offline or local-first. Phase 5 should evaluate the shipped local runtime instead of reopening cloud judging, hosted evaluation, or frontend work. [CITED: .planning/PROJECT.md](.planning/PROJECT.md); [CITED: .planning/ROADMAP.md](.planning/ROADMAP.md); [CITED: 05-CONTEXT.md](.planning/phases/05-recall-priority-evaluation-and-release-gates/05-CONTEXT.md)
- Phase 4 is complete and the current default runtime is the local `gguf-laptop` profile with explicit profile selection and fail-closed behavior still enforced. Phase 5 should measure that shipped behavior, not raw model internals. [CITED: .planning/STATE.md](.planning/STATE.md); [CITED: src/config/settings.py](src/config/settings.py); [CITED: tests/runtime/test_contracts.py](tests/runtime/test_contracts.py)
- The measurement boundary is the public runtime contract, not the internal Phase 4 decision object. `AnalysisResult` only publishes `risk_tier`, up to 3 `top_cues`, up to 2 `threat_labels`, up to 3 `recommendations`, and `normalized_text`. The release gate should score exactly what the product publishes. [CITED: src/runtime/contracts.py](src/runtime/contracts.py)
- `RuntimeService.analyze_text()` is already the normalize-first, fail-closed seam. It handles boundary checks, local readiness, and result cue-capping, so Phase 5 should batch through this seam or an equivalent backend-injected instance instead of bypassing it. [CITED: src/runtime/service.py](src/runtime/service.py)
- The repo already keeps offline model-selection and artifact workflows under `src/model_adaptation/` rather than `src/runtime/`. Phase 5 offline evaluation and release-artifact generation fit that same package boundary. [CITED: src/model_adaptation/cli.py](src/model_adaptation/cli.py); [CITED: src/model_adaptation/data.py](src/model_adaptation/data.py); [CITED: src/model_adaptation/registry.py](src/model_adaptation/registry.py)
- Nyquist validation is enabled in project config, so the planner should expect executable tests around gating logic, report generation, and runtime-bound evaluation rather than doc-only acceptance. [CITED: .planning/config.json](.planning/config.json)
- Repo copilot instructions add GSD workflow routing but no extra code-level restriction that changes the implementation surface for Phase 5. [CITED: .github/copilot-instructions.md](.github/copilot-instructions.md)

## Summary

Phase 5 should be implemented as an offline, model-adaptation-owned evaluation workflow that measures the existing Phase 4 runtime surface rather than the training stack or raw model payload. The repo already has the necessary pieces: typed held-out records in [src/data_pipeline/schemas.py](src/data_pipeline/schemas.py), a split loader in [src/model_adaptation/data.py](src/model_adaptation/data.py), a stable public result contract in [src/runtime/contracts.py](src/runtime/contracts.py), and a normalize-first runtime seam in [src/runtime/service.py](src/runtime/service.py). The missing piece is a batch evaluator and verdict engine that can turn those surfaces into held-out metrics, recall-blocking gates, and release artifacts. [CITED: src/data_pipeline/schemas.py](src/data_pipeline/schemas.py); [CITED: src/model_adaptation/data.py](src/model_adaptation/data.py); [CITED: src/runtime/contracts.py](src/runtime/contracts.py); [CITED: src/runtime/service.py](src/runtime/service.py)

The most important design choice is to keep the gate logic strictly recall-first for the three risky labels and to treat explanation quality as a second, separate verdict lane. That means recall on `bank_impersonation`, `zalo_social_engineering`, and `task_scam` determines hard release blocking at the locked `0.90` floor, while the explanation rubric only hard-blocks if it catches fabricated evidence or unsafe advice. Everything else in the rubric should surface as `FLAG`, not `BLOCK`, so the repo preserves the locked recall-first safety philosophy already used in Phase 3 pilot selection and reinforced in Phase 5 context. [CITED: 05-CONTEXT.md](.planning/phases/05-recall-priority-evaluation-and-release-gates/05-CONTEXT.md); [CITED: src/model_adaptation/pilot.py](src/model_adaptation/pilot.py)

The largest repo-specific planning constraint is the current split topology. The top-level `data/splits/test.jsonl` is empty, and the retained split root that Phase 3 defaults to is label-segmented across files rather than class-complete per split. Local inspection found `data/splits/recovered-balanced-claude-v2/train.jsonl` contains only `bank_impersonation` and `zalo_social_engineering`, `val.jsonl` contains only `benign`, and `test.jsonl` contains only `task_scam`. That means the repo does not currently expose a single held-out file that can support all-class release gating. Phase 5 therefore needs a true release-eval slice or it must fail closed on missing support. [CITED: src/model_adaptation/cli.py](src/model_adaptation/cli.py); [VERIFIED: workspace split counts]

**Primary recommendation:** Build a `src/model_adaptation` offline evaluator that loads typed held-out records, calls the existing runtime contract surface, computes explicit-label per-class metrics with `scikit-learn`, applies a fail-closed recall gate plus a hybrid explanation rubric, and emits paired markdown plus JSON release artifacts; keep `src/runtime/` limited to live analysis, rendering, and readiness checks. [CITED: src/model_adaptation/data.py](src/model_adaptation/data.py); [CITED: src/model_adaptation/cli.py](src/model_adaptation/cli.py); [CITED: src/runtime/service.py](src/runtime/service.py); [CITED: pyproject.toml](pyproject.toml)

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|--------------|----------------|-----------|
| Held-out record loading and evaluation-run orchestration | Model adaptation evaluation layer | Runtime service | The repo already loads offline splits under `src/model_adaptation`, while `RuntimeService` owns one-message normalization and fail-closed execution. [CITED: src/model_adaptation/data.py](src/model_adaptation/data.py); [CITED: src/runtime/service.py](src/runtime/service.py) |
| Published prediction boundary for measurement | Runtime contract | Shared local-model helpers | Phase 5 is locked to the contract-stable Phase 4 output surface, while local-model helpers remain the source of grounding and recommendation semantics underneath that boundary. [CITED: src/runtime/contracts.py](src/runtime/contracts.py); [CITED: src/runtime/analyzers/local_model.py](src/runtime/analyzers/local_model.py) |
| Per-label metrics, recall gate, and verdict synthesis | Model adaptation release-gate engine | `scikit-learn` metrics helpers | This is offline batch logic, not request-time runtime logic, and the dependency already exists in-project. [CITED: pyproject.toml](pyproject.toml); [CITED: https://scikit-learn.org/stable/modules/generated/sklearn.metrics.precision_recall_fscore_support.html](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.precision_recall_fscore_support.html) |
| Deterministic explanation checks | Evaluation helper | Phase 4 local-model guardrails | Phase 4 already validates exact cue grounding and sanitizes unsafe recommendations; Phase 5 should score against the published result while reusing the same safety logic as the standard. [CITED: src/runtime/analyzers/local_model.py](src/runtime/analyzers/local_model.py); [CITED: tests/runtime/test_local_model.py](tests/runtime/test_local_model.py) |
| Human-readable release reporting | Phase docs writer | Model adaptation CLI | The report belongs with phase planning docs and should not overload terminal rendering intended for single-message analysis. [CITED: 05-CONTEXT.md](.planning/phases/05-recall-priority-evaluation-and-release-gates/05-CONTEXT.md); [CITED: src/runtime/render.py](src/runtime/render.py); [CITED: src/model_adaptation/cli.py](src/model_adaptation/cli.py) |
| Machine-readable release artifact | Manifest-style JSON writer | Model registry conventions | The repo already persists JSON artifacts and manifest-like metadata under `data/manifests/`; Phase 5 should extend that pattern rather than inventing a second storage location. [CITED: src/data_pipeline/versioning/manifest.py](src/data_pipeline/versioning/manifest.py); [CITED: src/model_adaptation/registry.py](src/model_adaptation/registry.py); [CITED: data/manifests/phase3-large-pilot-2026-05-14.json](data/manifests/phase3-large-pilot-2026-05-14.json) |
| Optional operator-facing summary of latest gate state | Runtime doctor or CLI summary | Release artifact reader | If operator visibility is useful, doctor should read the latest artifact summary rather than becoming the primary generator of release metrics. [CITED: src/runtime/doctor.py](src/runtime/doctor.py); [CITED: src/runtime/cli.py](src/runtime/cli.py) |

## Standard Stack

No new external package is required for the recommended Phase 5 path. The repo already includes the two important building blocks: `scikit-learn` for metrics and `pytest` for validation. [CITED: pyproject.toml](pyproject.toml)

### Core

| Component or Library | Repo Version Floor or Current Use | Phase 5 Role | Why Standard Here |
|----------------------|-----------------------------------|--------------|-------------------|
| Python | 3.13 | Batch evaluation orchestration and artifact writing | Already the project baseline and the runtime used by Phase 2 through Phase 4 tooling. [CITED: pyproject.toml](pyproject.toml) |
| `scikit-learn` | `>=1.8` | Per-label precision, recall, F1, support, macro or weighted summaries, and confusion matrices | Already a declared dependency, and official docs confirm it supports explicit-label per-class metrics for multiclass and multilabel targets. [CITED: pyproject.toml](pyproject.toml); [CITED: https://scikit-learn.org/stable/modules/generated/sklearn.metrics.precision_recall_fscore_support.html](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.precision_recall_fscore_support.html); [CITED: https://scikit-learn.org/stable/modules/generated/sklearn.metrics.classification_report.html](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.classification_report.html) |
| `pydantic` | `>=2.12` | Typed evaluation-row, verdict, rubric-summary, and release-artifact models | The repo already uses Pydantic for dataset, runtime, doctor, and model-registry contracts. Phase 5 should extend that same pattern. [CITED: pyproject.toml](pyproject.toml); [CITED: src/runtime/contracts.py](src/runtime/contracts.py); [CITED: src/model_adaptation/schemas.py](src/model_adaptation/schemas.py) |
| `pytest` | `>=9.0` | Gate logic, artifact writer, and evaluator regression tests | Existing project test framework and the best fit for narrow offline verification. [CITED: pyproject.toml](pyproject.toml); [CITED: https://docs.pytest.org/en/stable/how-to/usage.html](https://docs.pytest.org/en/stable/how-to/usage.html) |
| `DatasetRecord` plus `load_split_records()` | Repo code | Typed held-out input loading | Prevents evaluation code from drifting away from the existing dataset contract. [CITED: src/data_pipeline/schemas.py](src/data_pipeline/schemas.py); [CITED: src/model_adaptation/data.py](src/model_adaptation/data.py) |
| `RuntimeService` plus `AnalysisResult` | Repo code | Contract-bound evaluation calls | Keeps Phase 5 anchored to the same public output that downstream UI and tests will consume. [CITED: src/runtime/service.py](src/runtime/service.py); [CITED: src/runtime/contracts.py](src/runtime/contracts.py) |

### Supporting

| Component | Current Role | Phase 5 Use |
|-----------|--------------|-------------|
| [src/runtime/analyzers/local_model.py](src/runtime/analyzers/local_model.py) | Shared grounding, label normalization, safety-floor, and recommendation-sanitizer logic | Reuse its semantics as the deterministic standard for grounding and unsafe-recommendation checks instead of inventing a second explanation policy. [CITED: src/runtime/analyzers/local_model.py](src/runtime/analyzers/local_model.py); [CITED: tests/runtime/test_local_model.py](tests/runtime/test_local_model.py) |
| [src/model_adaptation/registry.py](src/model_adaptation/registry.py) and [src/data_pipeline/versioning/manifest.py](src/data_pipeline/versioning/manifest.py) | Persist JSON artifacts and integrity metadata | Follow the same JSON-plus-checksum conventions for release artifacts in `data/manifests/`. [CITED: src/model_adaptation/registry.py](src/model_adaptation/registry.py); [CITED: src/data_pipeline/versioning/manifest.py](src/data_pipeline/versioning/manifest.py) |
| [tests/runtime/test_service.py](tests/runtime/test_service.py), [tests/runtime/test_local_model.py](tests/runtime/test_local_model.py), and [tests/runtime/test_runtime_profiles.py](tests/runtime/test_runtime_profiles.py) | Existing Phase 4 semantic guardrails | Preserve grounding, label, and recommendation behavior while adding offline gate tests around them. [CITED: tests/runtime/test_service.py](tests/runtime/test_service.py); [CITED: tests/runtime/test_local_model.py](tests/runtime/test_local_model.py); [CITED: tests/runtime/test_runtime_profiles.py](tests/runtime/test_runtime_profiles.py) |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `scikit-learn` metrics helpers | Hand-rolled metric math | Unnecessary and easier to get wrong, especially once runtime outputs can publish up to two threat labels. [CITED: pyproject.toml](pyproject.toml); [CITED: https://scikit-learn.org/stable/modules/generated/sklearn.metrics.precision_recall_fscore_support.html](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.precision_recall_fscore_support.html) |
| `src/model_adaptation` as the offline gate owner | `src/runtime/cli.py` or `src/runtime/service.py` as the batch evaluator | That would mix release-eval orchestration into per-message runtime code and make Phase 4 boundaries blur. [CITED: src/model_adaptation/cli.py](src/model_adaptation/cli.py); [CITED: src/runtime/cli.py](src/runtime/cli.py); [CITED: src/runtime/service.py](src/runtime/service.py) |
| Metric computation over explicit label indicators | Silently reduce predictions to the first threat label | The runtime contract allows up to two labels, so “first label wins” hides false positives and loses useful gate signal. [CITED: src/runtime/contracts.py](src/runtime/contracts.py); [ASSUMED] |
| Evaluation over `AnalysisResult` | Evaluation over raw local-model payload or internal `ThreatDecision` | That would violate the locked Phase 4 measurement boundary and score unpublished internal details rather than shipped output. [CITED: 05-CONTEXT.md](.planning/phases/05-recall-priority-evaluation-and-release-gates/05-CONTEXT.md); [CITED: src/runtime/contracts.py](src/runtime/contracts.py); [CITED: src/runtime/analyzers/local_model.py](src/runtime/analyzers/local_model.py) |

## Held-Out Split Reality Check

The current workspace does not expose a release-ready all-class held-out split.

| Split Surface | Observed Reality | Why It Matters |
|---------------|------------------|----------------|
| `data/splits/` top-level files | Local inspection found `train.jsonl` contains 37 rows across `bank_impersonation`, `zalo_social_engineering`, and `benign`; `val.jsonl` contains 12 rows of `task_scam` only; `test.jsonl` is empty. [VERIFIED: workspace split counts] | A direct Phase 5 evaluation over these files cannot compute all-class held-out metrics and cannot support a real release gate. |
| `data/splits/recovered-balanced-claude-v2/` retained root | `src/model_adaptation/cli.py` prefers this root if present. Local inspection found `train.jsonl` contains only `bank_impersonation` and `zalo_social_engineering`, `val.jsonl` contains only `benign`, and `test.jsonl` contains only `task_scam`. [CITED: src/model_adaptation/cli.py](src/model_adaptation/cli.py); [VERIFIED: workspace split counts] | The Phase 3 default split root is still not class-complete per held-out file, so Phase 5 must not assume those names already encode a valid release-eval set. |
| Dataset channel metadata | `DatasetRecord` has `text`, `label`, `risk_tier`, cues, explanation, provenance, and `seed_id`, but no `channel` field. [CITED: src/data_pipeline/schemas.py](src/data_pipeline/schemas.py) | The offline evaluator cannot fully replay channel-specific runtime hints unless it derives them from text or introduces separate evaluation metadata. |

The planner should treat this as the primary Phase 5 wave-0 research outcome: a release gate cannot honestly `PASS` unless every risky label has held-out support in the evaluated dataset. If support is missing, the gate should `BLOCK` with an explicit “unsupported held-out label” reason rather than skipping the label or letting `zero_division` hide the gap. [CITED: https://scikit-learn.org/stable/modules/generated/sklearn.metrics.precision_recall_fscore_support.html](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.precision_recall_fscore_support.html); [ASSUMED]

## Architecture Patterns

### Pattern 1: Contract-Bound Offline Evaluation Harness

The offline evaluator should load typed `DatasetRecord` rows, run them through the same normalize-first runtime seam the product already uses, and collect only the public `AnalysisResult` fields for scoring and rubric checks. This keeps Phase 5 honest to the shipped product surface and avoids re-implementing normalization, fail-closed behavior, or cue capping in a second code path. [CITED: src/model_adaptation/data.py](src/model_adaptation/data.py); [CITED: src/runtime/service.py](src/runtime/service.py); [CITED: src/runtime/contracts.py](src/runtime/contracts.py)

Because the dataset contract currently lacks `channel`, the safest default is to evaluate with `channel="unknown"` unless the planner explicitly adds non-breaking evaluation metadata outside the Phase 1 dataset schema. That limitation should be recorded in the release artifact so channel-blind evaluation is explicit. [CITED: src/data_pipeline/schemas.py](src/data_pipeline/schemas.py); [CITED: src/runtime/contracts.py](src/runtime/contracts.py); [ASSUMED]

### Pattern 2: Explicit-Label Metrics With Fail-Closed Support Checks

The runtime can publish up to two threat labels, while the dataset stores one gold label per record. The cleanest Phase 5 metric pattern is therefore explicit-label one-vs-rest scoring over the locked label vocabulary instead of collapsing predictions to a single string. `scikit-learn` officially supports per-label precision, recall, F1, and support when labels are supplied explicitly, and it also supports multilabel targets when predictions are represented as per-class indicators. [CITED: src/runtime/contracts.py](src/runtime/contracts.py); [CITED: src/data_pipeline/schemas.py](src/data_pipeline/schemas.py); [CITED: https://scikit-learn.org/stable/modules/generated/sklearn.metrics.precision_recall_fscore_support.html](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.precision_recall_fscore_support.html)

For the release gate itself, risky-label support must be treated as a gate input, not just descriptive metadata. If `support == 0` for any risky label in the evaluated held-out slice, the release artifact should `BLOCK` because the repo has not actually measured recall for that label. This matches the repo’s existing fail-closed posture in runtime readiness and Phase 5’s hard-blocking safety policy. [CITED: src/runtime/service.py](src/runtime/service.py); [CITED: src/runtime/doctor.py](src/runtime/doctor.py); [CITED: 05-CONTEXT.md](.planning/phases/05-recall-priority-evaluation-and-release-gates/05-CONTEXT.md); [ASSUMED]

For reporting, the most defensible “overall F1” is macro F1 over the full label set, with weighted F1 reported as secondary context. Macro F1 keeps the release summary from being dominated by whichever label happens to have more support in an imbalanced held-out slice, while the hard release decision still comes from per-label recall floors rather than any averaged score. [CITED: https://scikit-learn.org/stable/modules/generated/sklearn.metrics.classification_report.html](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.classification_report.html); [ASSUMED]

### Pattern 3: Recall Gate As Its Own Verdict Lane

The locked release policy is not a single blended threshold. The evaluator should compute metrics first, then run a separate gate pass that produces explicit blocker reasons. That gate should:

1. Evaluate the risky labels `bank_impersonation`, `zalo_social_engineering`, and `task_scam` only.
2. `BLOCK` if any risky label has `support == 0` in the evaluated held-out slice.
3. `BLOCK` if any risky label recall is below `0.90`.
4. `PASS` the recall lane only if all three risky labels meet both support and recall requirements.
5. Keep overall F1 and non-risky metrics descriptive unless the user later locks stronger policy. [CITED: 05-CONTEXT.md](.planning/phases/05-recall-priority-evaluation-and-release-gates/05-CONTEXT.md); [CITED: src/model_adaptation/pilot.py](src/model_adaptation/pilot.py); [ASSUMED]

This pattern stays aligned with the repo’s existing “recall first, everything else second” philosophy instead of inventing a new weighted acceptance score that could hide a dangerous false negative behind good averages. [CITED: src/model_adaptation/pilot.py](src/model_adaptation/pilot.py)

### Pattern 4: Hybrid Explanation Rubric Over Risky Predictions Only

The deterministic half of the rubric should score the published risky outputs on three locked dimensions:

- **Grounding:** every published cue span in `AnalysisResult.top_cues` must appear in `normalized_text`, and risky outputs should not publish an empty cue list. This matches the Phase 4 exact-span validation already enforced in shared local-model helpers and tests. [CITED: src/runtime/contracts.py](src/runtime/contracts.py); [CITED: src/runtime/analyzers/local_model.py](src/runtime/analyzers/local_model.py); [CITED: tests/runtime/test_local_model.py](tests/runtime/test_local_model.py); [CITED: tests/runtime/test_service.py](tests/runtime/test_service.py)
- **Label alignment:** the rubric should record whether the gold label is represented in the predicted threat-label set for risky held-out cases, but this should remain advisory because label miss handling already belongs primarily to the recall gate. [CITED: src/runtime/contracts.py](src/runtime/contracts.py); [CITED: src/data_pipeline/schemas.py](src/data_pipeline/schemas.py); [ASSUMED]
- **Safe recommendation quality:** every published recommendation for risky outputs must avoid unsafe action markers, and risky outputs should still publish at least one user-safe next step. This matches the existing Phase 4 recommendation sanitizer. [CITED: src/runtime/analyzers/local_model.py](src/runtime/analyzers/local_model.py); [CITED: tests/runtime/test_local_model.py](tests/runtime/test_local_model.py)

The manual half of the rubric should review only risky predictions from the held-out run, because that is the locked scope. The manual sample should check whether the explanation summary or cues introduce fabricated claims not supported by the message text and whether the recommendations remain safe and practically useful. Only two explanation findings should `BLOCK`: fabricated evidence and unsafe recommendations. Everything else, including generic wording or weak label alignment, should `FLAG` and be summarized in the report. [CITED: 05-CONTEXT.md](.planning/phases/05-recall-priority-evaluation-and-release-gates/05-CONTEXT.md); [CITED: src/runtime/analyzers/local_model.py](src/runtime/analyzers/local_model.py)

### Pattern 5: Paired Markdown Plus JSON Release Artifacts

The report should be generated in two forms from one evaluation run:

- A human-readable markdown report stored under the Phase 5 planning folder.
- A machine-readable JSON artifact stored under `data/manifests/`.

The repo already has both patterns: phase-local markdown research and security docs under `.planning/phases/`, plus JSON manifests and model artifacts under `data/manifests/`. Phase 5 should mirror that separation. [CITED: 05-CONTEXT.md](.planning/phases/05-recall-priority-evaluation-and-release-gates/05-CONTEXT.md); [CITED: src/data_pipeline/versioning/manifest.py](src/data_pipeline/versioning/manifest.py); [CITED: data/manifests/phase3-large-pilot-2026-05-14.json](data/manifests/phase3-large-pilot-2026-05-14.json)

The JSON artifact should be typed and explicit about why a verdict happened. A practical shape for the planner is:

```json
{
  "phase": 5,
  "version_tag": "phase5-release-eval-...",
  "verdict": "PASS | BLOCK | FLAG",
  "runtime": {
    "backend": "gguf",
    "profile": "gguf-laptop"
  },
  "dataset": {
    "split_path": "...",
    "support_by_label": {
      "bank_impersonation": 0,
      "zalo_social_engineering": 0,
      "task_scam": 0,
      "benign": 0
    }
  },
  "metrics": {
    "overall_f1": 0.0,
    "overall_f1_kind": "macro",
    "weighted_f1": 0.0,
    "per_label": {
      "bank_impersonation": {"precision": 0.0, "recall": 0.0, "f1": 0.0, "support": 0},
      "zalo_social_engineering": {"precision": 0.0, "recall": 0.0, "f1": 0.0, "support": 0},
      "task_scam": {"precision": 0.0, "recall": 0.0, "f1": 0.0, "support": 0},
      "benign": {"precision": 0.0, "recall": 0.0, "f1": 0.0, "support": 0}
    }
  },
  "recall_gate": {
    "floor": 0.9,
    "risky_labels": ["bank_impersonation", "zalo_social_engineering", "task_scam"],
    "passed": false,
    "blocker_reasons": []
  },
  "explanation_rubric": {
    "scope": "risky_predictions_only",
    "deterministic_summary": {},
    "manual_sample_summary": {},
    "blocker_reasons": [],
    "flag_reasons": []
  },
  "blocker_reasons": [],
  "flag_reasons": []
}
```

## Integration With Existing Code

- [src/model_adaptation/data.py](src/model_adaptation/data.py): reuse `load_split_records()` as the typed loader for held-out rows. Do not duplicate JSONL parsing in a second offline-eval utility. [CITED: src/model_adaptation/data.py](src/model_adaptation/data.py)
- [src/model_adaptation/cli.py](src/model_adaptation/cli.py): this is the most natural CLI surface for Phase 5 because it already owns pilot, train, and convert workflows. Add release-eval orchestration here rather than to `vnphish analyze` or `vnphish doctor`. [CITED: src/model_adaptation/cli.py](src/model_adaptation/cli.py); [CITED: src/runtime/cli.py](src/runtime/cli.py)
- [src/runtime/service.py](src/runtime/service.py): keep this file focused on request normalization, boundary checks, fail-closed runtime execution, and cue capping. It should not grow batch metrics, release verdict logic, or artifact writing. [CITED: src/runtime/service.py](src/runtime/service.py)
- [src/runtime/contracts.py](src/runtime/contracts.py): this is the public evaluation boundary. Score `AnalysisResult` exactly as shipped, including the published caps on cues, labels, and recommendations. [CITED: src/runtime/contracts.py](src/runtime/contracts.py)
- [src/runtime/analyzers/local_model.py](src/runtime/analyzers/local_model.py): reuse Phase 4’s exact-grounding, label normalization, safety-floor, and recommendation-sanitizer behavior as the deterministic explanation standard. Do not re-implement unsafe-marker logic in a third place if a shared helper can be exposed. [CITED: src/runtime/analyzers/local_model.py](src/runtime/analyzers/local_model.py); [CITED: tests/runtime/test_local_model.py](tests/runtime/test_local_model.py)
- [src/runtime/doctor.py](src/runtime/doctor.py): if the planner wants an operator summary of the latest release verdict, doctor should read the newest artifact summary rather than become the evaluator itself. [CITED: src/runtime/doctor.py](src/runtime/doctor.py)
- [src/data_pipeline/versioning/manifest.py](src/data_pipeline/versioning/manifest.py) and [src/model_adaptation/registry.py](src/model_adaptation/registry.py): follow their JSON persistence and checksum style for machine-readable artifacts under `data/manifests/`. [CITED: src/data_pipeline/versioning/manifest.py](src/data_pipeline/versioning/manifest.py); [CITED: src/model_adaptation/registry.py](src/model_adaptation/registry.py)

## Validation Architecture

Phase 5 needs both deterministic unit tests and one narrow offline integration test path. The repo already uses `pytest`, and the official docs confirm narrow path or node-id execution is the standard way to run targeted slices. [CITED: pyproject.toml](pyproject.toml); [CITED: https://docs.pytest.org/en/stable/how-to/usage.html](https://docs.pytest.org/en/stable/how-to/usage.html)

| Validation Slice | What It Should Prove | Likely Command |
|------------------|----------------------|----------------|
| Evaluator unit tests | Explicit-label metric mapping, support accounting, overall F1 calculation, and fail-closed zero-support handling | `python -m pytest tests/model_adaptation -q` [ASSUMED] |
| Gate-verdict tests | `PASS/BLOCK/FLAG` synthesis from recall and rubric inputs | `python -m pytest tests/model_adaptation -q` [ASSUMED] |
| Runtime-bound integration test | A fake or stub backend evaluated through `RuntimeService` still yields the expected artifact schema and blocker reasons | `python -m pytest tests/runtime tests/model_adaptation -q` [ASSUMED] |
| Existing runtime regressions | Grounding, recommendation sanitization, profile parity, and privacy-safe failures remain intact after Phase 5 additions | `python -m pytest tests/runtime -q` [CITED: tests/runtime/test_local_model.py](tests/runtime/test_local_model.py); [CITED: tests/runtime/test_runtime_profiles.py](tests/runtime/test_runtime_profiles.py); [CITED: tests/runtime/test_privacy.py](tests/runtime/test_privacy.py) |
| Manual explanation review | Curated risky-prediction sample only; fabricated evidence or unsafe advice blocks, everything else flags | Manual checklist or report appendix [ASSUMED] |

The planner should avoid treating markdown diff review as sufficient validation for this phase. Nyquist validation is enabled, and the release gate itself is executable logic that should have narrow automated tests before full offline runs. [CITED: .planning/config.json](.planning/config.json)

## Likely Plan and Wave Split

This phase should probably be planned in at least three waves, with a wave-0 sanity step if the planner confirms the split issue is real and in-scope to repair.

1. **Wave 0: held-out evaluation surface sanity.** Confirm the actual release-eval dataset source, support counts per risky label, and whether Phase 5 needs a dedicated release-eval artifact because the current split layout is not class-complete per held-out file. This is the most likely blocker for honest release gating. [CITED: src/model_adaptation/cli.py](src/model_adaptation/cli.py); [VERIFIED: workspace split counts]
2. **Wave 1: offline evaluator and metric schema.** Add typed evaluation-row and artifact contracts, batch through the runtime measurement boundary, and emit overall plus per-label metrics with explicit label order and support counts. [CITED: src/model_adaptation/data.py](src/model_adaptation/data.py); [CITED: src/runtime/contracts.py](src/runtime/contracts.py); [CITED: src/runtime/service.py](src/runtime/service.py)
3. **Wave 2: recall gate and paired artifact emission.** Turn the metric output into `PASS/BLOCK/FLAG` release verdicts with blocker and flag reasons, then emit both phase-local markdown and JSON manifest artifacts. [CITED: 05-CONTEXT.md](.planning/phases/05-recall-priority-evaluation-and-release-gates/05-CONTEXT.md); [CITED: src/data_pipeline/versioning/manifest.py](src/data_pipeline/versioning/manifest.py)
4. **Wave 3: explanation-rubric integration and validation.** Reuse deterministic Phase 4 safety checks, add manual risky-sample summary handling, and lock regression coverage so explanation issues only block on fabricated evidence or unsafe recommendations. [CITED: src/runtime/analyzers/local_model.py](src/runtime/analyzers/local_model.py); [CITED: tests/runtime/test_local_model.py](tests/runtime/test_local_model.py); [CITED: tests/runtime/test_service.py](tests/runtime/test_service.py)

If the planner wants an even tighter split, Wave 2 and Wave 3 can be separated by artifact-first versus rubric-first work. What should not be merged is Wave 0 and Wave 1, because the current split topology is too risky to leave implicit.

## Anti-Patterns and Codebase-Specific Traps

- **Scoring raw model payloads instead of `AnalysisResult`:** this breaks the locked Phase 4 measurement boundary and can accidentally score unpublished internal evidence fields. [CITED: 05-CONTEXT.md](.planning/phases/05-recall-priority-evaluation-and-release-gates/05-CONTEXT.md); [CITED: src/runtime/contracts.py](src/runtime/contracts.py); [CITED: src/runtime/analyzers/local_model.py](src/runtime/analyzers/local_model.py)
- **Adding batch evaluation logic to `src/runtime/service.py` or `src/runtime/cli.py`:** those files are the live runtime path, not the offline release-eval control plane. [CITED: src/runtime/service.py](src/runtime/service.py); [CITED: src/runtime/cli.py](src/runtime/cli.py)
- **Using `labels=None` with `scikit-learn`:** the docs state that absent labels are dropped by default, which is dangerous here because a risky label could disappear from the report entirely if the held-out slice has no support. Always pass the full locked label order explicitly. [CITED: https://scikit-learn.org/stable/modules/generated/sklearn.metrics.precision_recall_fscore_support.html](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.precision_recall_fscore_support.html)
- **Letting zero-support risky labels produce warnings instead of blockers:** the repo’s fail-closed posture means missing measurement should block release, not downgrade into a warning that the operator can miss. [CITED: src/runtime/service.py](src/runtime/service.py); [CITED: src/runtime/doctor.py](src/runtime/doctor.py); [ASSUMED]
- **Silently reducing multi-label runtime outputs to one label:** `AnalysisResult.threat_labels` can publish up to two labels, so first-label-only evaluation can hide false positives and distort recall or precision. [CITED: src/runtime/contracts.py](src/runtime/contracts.py); [ASSUMED]
- **Treating all explanation rubric misses as blockers:** the Phase 5 context explicitly locks explanation quality to advisory status except for fabricated evidence or unsafe recommendations. [CITED: 05-CONTEXT.md](.planning/phases/05-recall-priority-evaluation-and-release-gates/05-CONTEXT.md)
- **Assuming the current `train/val/test` names already imply a valid release-eval split:** local inspection shows the current split roots are class-segmented or empty, so Phase 5 must verify support before trusting any filename convention. [CITED: src/model_adaptation/cli.py](src/model_adaptation/cli.py); [VERIFIED: workspace split counts]
- **Forgetting that the dataset lacks `channel`:** the runtime accepts a channel hint, but the current held-out records do not store one. Evaluation design must either be channel-blind or explicitly add evaluation-only metadata without breaking the Phase 1 dataset contract. [CITED: src/data_pipeline/schemas.py](src/data_pipeline/schemas.py); [CITED: src/runtime/contracts.py](src/runtime/contracts.py)
- **Logging raw message text or raw model output when report generation fails:** the privacy tests already guard against leaking user text or raw invalid model payloads in failures, and Phase 5 should preserve that behavior. [CITED: tests/runtime/test_privacy.py](tests/runtime/test_privacy.py)

## Open Questions (RESOLVED INTO PLAN)

1. **Canonical held-out release-eval dataset**
Resolution for planning: no split filename is trusted as canonical by default. Plan `05-01` turns this into an explicit fail-closed readiness audit that requires an operator-supplied held-out path or root, records the audited source, and blocks any `PASS` verdict until all risky labels have non-zero support. [CITED: 05-01-PLAN.md](.planning/phases/05-recall-priority-evaluation-and-release-gates/05-01-PLAN.md)

1. **Evaluation profile scope**
Resolution for planning: Phase 5 stays anchored to the shipped Phase 4 runtime contract and default local delivery path. The default `gguf-laptop` profile is the minimum release-verdict surface for milestone readiness, while any additional local-profile evaluation must remain explicit and may only add context or flags rather than replace the default-profile verdict. This remains an implementation checkpoint inside the evaluator and final gate plans rather than a free-floating research unknown. [CITED: 05-02-PLAN.md](.planning/phases/05-recall-priority-evaluation-and-release-gates/05-02-PLAN.md); [CITED: 05-04-PLAN.md](.planning/phases/05-recall-priority-evaluation-and-release-gates/05-04-PLAN.md)

1. **Manual review burden per run**
Resolution for planning: the first implementation uses a deterministic risky-only curated review pack with explicit sample-size settings and reviewer fields, rather than an open-ended review obligation. Plan `05-03` owns this explicitly, and Plan `05-04` consumes the completed pack when synthesizing the final verdict. [CITED: 05-03-PLAN.md](.planning/phases/05-recall-priority-evaluation-and-release-gates/05-03-PLAN.md); [CITED: 05-04-PLAN.md](.planning/phases/05-recall-priority-evaluation-and-release-gates/05-04-PLAN.md)

## Research Outcome

Phase 5 is best treated as a release-engineering phase over the existing local runtime, not as another modeling phase and not as a frontend phase. The strongest fit for the current repo is an offline evaluator under `src/model_adaptation` that reuses the existing split loader, calls the public runtime contract, computes explicit-label metrics with the already-installed `scikit-learn` stack, and emits paired markdown plus JSON artifacts with `PASS/BLOCK/FLAG` verdicts. [CITED: src/model_adaptation/data.py](src/model_adaptation/data.py); [CITED: src/model_adaptation/cli.py](src/model_adaptation/cli.py); [CITED: src/runtime/contracts.py](src/runtime/contracts.py); [CITED: src/runtime/service.py](src/runtime/service.py); [CITED: pyproject.toml](pyproject.toml)

The planner should not gloss over the current split topology. Without a true held-out slice that gives non-zero support to all three risky labels, the locked recall gate cannot be satisfied honestly. That is the main structural risk in this phase, and it is more important than the exact CLI spelling or the exact filename of the release report. [VERIFIED: workspace split counts]

## RESEARCH COMPLETE

<!-- markdownlint-enable MD022 MD032 MD033 MD034 MD055 MD056 MD060 -->