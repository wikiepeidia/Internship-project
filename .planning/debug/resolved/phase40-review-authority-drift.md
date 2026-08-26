---
status: resolved
trigger: "Phase 40 Plan 06 canonical queue verifier rejects the superseded scope amendment after Plan 05 froze the final comparison authority."
created: 2026-08-26
updated: 2026-08-26T09:44:29+07:00
---

# Debug Session: Phase 40 Review Authority Drift

## Symptoms

- expected_behavior: The Plan 06 queue verifier accepts the already-frozen Plan 05 comparison authority, verifies the 52-row immutable queue, and then validates the human reviewer return.
- actual_behavior: Verification stops before reading reviewer judgments because loading the historical scope amendment revalidates its old comparison-finalizer source allowlist against the newer repository source closure.
- error_message: "Phase40ScopeAmendment.comparison_finalizer_authority: comparison finalizer authority must bind the exact source allowlist"
- timeline: First observed immediately after the user completed reviewer-return.jsonl and Plan 06 was invoked against the successfully frozen Plan 05 artifacts.
- reproduction: "python -m src.model_adaptation.cli phase40-verify-review-queue --request-path data/models/phase40/full-run-request.json --repo-root . --scope-amendment-path data/models/phase40/two-full-model-scope-amendment.json --comparison-manifest-path data/models/phase40/comparison-manifest.json --selected-predictions-path data/models/phase40/selected-prediction-bundles.json --queue-path data/models/phase40/review/review-queue.jsonl"

## Current Focus

- hypothesis: Resolved: Plan 06 now consumes Plan 05 as frozen upstream provenance through the additive review module, while the immutable Plan 05 comparison closure remains unchanged.
- test: Human verification of the generated 52-row review report and manifest.
- expecting: The report preserves all 52 reviewer judgments, Vietnamese attestation, and the exact reviewer-return identity without diff-check errors.
- next_action: Archive this resolved session, commit the scoped fix, and append the recurrence pattern to the debug knowledge base.
- bug_class: bohrbug
- reasoning_checkpoint:
    hypothesis: "Plan 06 fails because its queue and human-review paths still load Phase40ScopeAmendment as live authority and reverify both comparison runs through the original request, while Plan 05 explicitly superseded that source closure with final-comparison-authority.json and a per-run recovery request."
    confirming_evidence:
      - "The final-authority loader succeeds on the current repository and selects Qwen QLoRA v1 plus PhoBERT v12."
      - "The unchanged Plan 06 queue command deterministically fails inside Phase40ScopeAmendment.comparison_finalizer_authority before queue bytes are validated."
      - "The v3 manifest contains the final-authority hash, historical amendment hash, current finalizer hash, and per-run origin hashes, but the Plan 06 human finalizer reads none of them and looks up both runs in the original request."
    falsification_test: "If Plan 06 can consume the verified final authority and still raises the same historical source-allowlist error before queue validation, or if its v3 per-run identities cannot be derived exactly from final.by_run_id, this hypothesis is false."
    fix_rationale: "Branching on the already-validated v3 manifest and consuming the frozen final authority restores the intended authority chain; it keeps the old amendment byte/hash as provenance while validating the current finalizer and each run against its own immutable origin request."
    blind_spots: "The reserved Phase 41 split is intentionally untested and inaccessible; verification covers only Phase 40 review inputs, synthetic regressions, and current Phase 40 artifacts."
    candidate_causes:
      - "code: stale legacy amendment loader plus original-request-only human-review bundle re-verifier"
      - "config: malformed or missing final-comparison-authority.json / v3 manifest binding (eliminated by successful canonical loader and manifest validation)"
      - "data: corrupted historical amendment bytes or hash drift (eliminated because the final-authority loader verifies the canonical historical bytes and hash)"
    and_gate: "no - the valid Plan 05 authority evolution is an intended input state; the stale Plan 06 code contract alone is sufficient to mis-handle it, while config and data branches are valid."
- tdd_checkpoint:
    test_file: tests/model_adaptation/test_phase40_final_authority.py
    test_name: test_review_handoff_accepts_hash_bound_historical_scope_source
    status: green
    failure_output: "Initial RED: AttributeError; current focused result: 1 passed"

## Evidence

- timestamp: 2026-08-26T00:00:00Z
  observation: The fixed Plan 06 queue verifier command exits with a Pydantic validation error on Phase40ScopeAmendment.comparison_finalizer_authority before reviewer-return validation begins.
- timestamp: 2026-08-26T00:15:00+07:00
  checked: .planning/debug/knowledge-base.md
  found: The only prior entry concerns PhoBERT launch and telemetry sealing; it does not match the Plan 06 authority-handoff validation failure.
  implication: No known-pattern hypothesis supersedes direct tracing of the Phase 40 final-authority handoff.
- timestamp: 2026-08-26T00:25:00+07:00
  checked: Symbol search restricted to src/model_adaptation, tests/model_adaptation, and Phase 40 planning artifacts
  found: The CLI command is handled in src/model_adaptation/cli.py; legacy Phase40ScopeAmendment validation lives in phase40_handoff.py; the reviewed additive authority has its own frozen loader in phase40_final_authority.py and is already consumed by production-authority code.
  implication: The likely divergence is a stale downstream loader, not absence of a canonical final-authority implementation.
- timestamp: 2026-08-26T00:35:00+07:00
  checked: Complete `_load_phase40_review_authorities` and frozen final-authority validation paths
  found: The shared Plan 06 CLI loader directly calls `load_frozen_phase40_scope_amendment`; that constructs `Phase40ScopeAmendment`, whose `ComparisonFinalizerAuthority` enforces the current exact source allowlist during model validation. `load_frozen_phase40_final_comparison_authority` instead parses the old file as `HistoricalScopeAmendment`, verifies its canonical bytes/hash as provenance, and separately verifies the current finalizer authority.
  implication: The observed exception occurs at the stale loader seam before queue bytes and reviewer return bytes are examined, matching the reported ordering exactly.
- timestamp: 2026-08-26T00:45:00+07:00
  checked: Current final-comparison-authority.json, comparison-manifest.json, queue verifier, and human-review finalizer
  found: The final authority selects Qwen QLoRA v1 plus PhoBERT v12 and binds the historical amendment hash `c183...b84`; the comparison manifest is v3 and carries the same historical hash plus dedicated final-authority/current-finalizer fields. The human-review finalizer nevertheless reloads the legacy amendment, compares its old active IDs/source tree to the v3 manifest, and re-verifies both runs through the original request only.
  implication: Fixing only the first CLI load would expose later stale assumptions; the complete Plan 06 final-authority handoff must cover both queue loading and human-review provenance re-verification.
- timestamp: 2026-08-26T00:55:00+07:00
  checked: Phase40ComparisonManifest v3 validators and `finalize_phase40_final_comparison`
  found: The producer already freezes all required replacement identities: historical amendment hash, final authority hash, current finalizer source-tree hash, exact run order, per-run request/source hashes, shared input authority, and current queue/prediction hashes. The manifest validator enforces exact coverage and disallows a legacy global source authority in v3.
  implication: Plan 06 should consume and re-prove these existing v3 identities rather than reinterpret the historical amendment as live policy.
- timestamp: 2026-08-26T01:05:00+07:00
  checked: Plan 40-06 acceptance criteria
  found: Plan 06 requires queue/source/comparison hash verification, exact selected-run/artifact binding, and finalizer re-proof without mutation; it does not require re-establishing the superseded amendment's old source closure.
  implication: Consuming Plan 05's frozen v3 authority is within the Plan 06 handoff boundary and preserves the required trust checks.
- timestamp: 2026-08-26T01:10:00+07:00
  checked: `load_frozen_phase40_final_comparison_authority(repo_root=Path('.'))`
  found: The canonical loader succeeds and returns authority SHA-256 `7ac554...89c7` with selected runs Qwen QLoRA v1 and PhoBERT v12.
  implication: Malformed Plan 05 authority/configuration is eliminated; the current repository satisfies the intended live finalizer closure.
- timestamp: 2026-08-26T01:15:00+07:00
  checked: Sanitized Plan 06 queue-verifier reproduction against Phase 40 artifacts
  found: Exit code 1 with `Phase40ScopeAmendment.comparison_finalizer_authority: comparison finalizer authority must bind the exact source allowlist`, before queue verification output.
  implication: The differential experiment confirms the stale loader is the divergence point: the intended final authority accepts the same repository while Plan 06 rejects its historical provenance object.
- timestamp: 2026-08-26T01:20:00+07:00
  checked: Spectrum-based fault localization eligibility
  found: No agent-authored failing regression/per-test coverage spectrum exists yet; SBFL is skipped until a focused deterministic regression is added.
  implication: Direct differential tracing is the strongest current localization evidence.
- timestamp: 2026-08-26T01:30:00+07:00
  checked: Agent-authored regression `test_review_handoff_accepts_hash_bound_historical_scope_source`
  found: The test fails RED because no review-specific final-authority loader exists; the only Plan 06 loader is the legacy amendment path.
  implication: The regression directly captures the missing authority-handoff seam and provides a derived contract oracle over the final authority's historical hash/current source split.
- timestamp: 2026-08-26T01:40:00+07:00
  checked: Focused regression after adding `load_phase40_review_authority`
  found: The regression passes and confirms the review loader accepts a hash-bound historical source inventory while the verified final authority separately enforces the current source closure and two per-run origins.
  implication: The missing primitive is fixed; the remaining work is wiring Plan 06 consumers to it without weakening v2 compatibility.
- timestamp: 2026-08-26T02:05:00+07:00
  checked: Focused review regression suite after v3 wiring
  found: 17 tests passed, including the new historical-scope regression and all existing human-review tests selected by name.
  implication: The patched logic preserves legacy v2 behavior and satisfies the synthetic final-authority handoff contract.
- timestamp: 2026-08-26T02:10:00+07:00
  checked: Production Phase 40 queue verifier after v3 wiring
  found: The old Pydantic historical-allowlist failure is gone, but the command now stops with `local comparison finalizer source differs from the final authority` because the patched review files are themselves covered by the frozen current source inventory.
  implication: The first hypothesis was causally correct, but the implementation site conflicts with the self-protecting Plan 05 source closure; accepting the fix requires an authorized additive seam, not bypassing live verification.
- timestamp: 2026-08-26T02:25:00+07:00
  checked: Exact Plan 05 comparison finalizer allowlist and summary
  found: The frozen closure includes phase40_handoff.py and phase40_final_authority.py but excludes cli.py; Plan 05 records it as the completed comparison runtime and separately hands a frozen 52-row queue to Plan 06.
  implication: Plan 06 review logic must not edit/re-execute the frozen comparison closure as though it were still live. The viable seam is an additive review consumer outside that closure, with the Plan 05 source hash retained as upstream provenance.
- timestamp: 2026-08-26T02:35:00+07:00
  checked: `_authority_components` and final-authority verification internals
  found: `_authority_components` independently verifies the original request, recovery request, shared input identities, exact recovery delta, historical amendment canonical bytes/hash policy, and sealed LoRA probe before the separate live-source equality check. Final-authority models also validate the stored source inventory's exact allowlist and internal tree hash.
  implication: A Plan 06 frozen-upstream loader can retain all immutable artifact checks while deliberately omitting only re-execution-time equality between current repository bytes and the already-completed comparison runtime.
- timestamp: 2026-08-26T03:00:00+07:00
  checked: Source diff after relocating the fix
  found: phase40_handoff.py and phase40_final_authority.py have no content diff; the additive implementation now lives in phase40_review.py and is reached only from cli.py, both outside the Plan 05 comparison allowlist.
  implication: The fix no longer mutates the frozen comparison runtime it consumes.
- timestamp: 2026-08-26T03:10:00+07:00
  checked: Canonical Plan 05 loader, relocated regression, CLI review-byte forwarding test, and production queue command
  found: The canonical authority remains `7ac554...89c7`; 2 focused tests pass; the production queue verifier succeeds with exactly 52 rows.
  implication: The original issue is fixed at the queue boundary without changing the frozen comparison closure; end-to-end human finalization is the remaining verification step.
- timestamp: 2026-08-26T03:25:00+07:00
  checked: Real Plan 06 finalization and verify-only replay
  found: Normal finalization accepts all 52 reviewer-return rows and writes canonical notes/manifest/report; the immediate verify-only run succeeds byte-for-byte.
  implication: The per-run recovery authority is correctly resolved through PhoBERT v12 and the original end-to-end workflow is restored.
- timestamp: 2026-08-26T03:40:00+07:00
  checked: Adjacent Phase 40 review tests and syntax checks
  found: 19 relevant tests pass and `py_compile` passes for the new module, CLI, and regression. Ruff is not installed, so lint is explicitly unavailable rather than treated as passed.
  implication: Focused regression and adjacent behavior are green; the remaining automated guardrail is causal revert-and-reconfirm.
- timestamp: 2026-08-26T03:50:00+07:00
  checked: Revert-and-reconfirm guardrail
  found: With only cli.py and phase40_review.py stashed, the original Phase40ScopeAmendment allowlist error returns. After applying the same stash, the queue verifier again passes all 52 rows.
  implication: The additive fix is causally necessary and sufficient for the original queue failure.
- timestamp: 2026-08-26T04:05:00+07:00
  checked: Hardened authority regression and generated human-review manifest
  found: The regression proves a post-comparison source change invalidates the live loader but remains valid frozen review provenance; a same-bytes noncanonical scope path is rejected. The generated 52-row manifest binds both the historical scope hash and final authority SHA-256 `7ac554...89c7`.
  implication: The fix preserves the live-rerun/frozen-upstream distinction and records the controlling authority in the Plan 06 closure artifact.
- timestamp: 2026-08-26T04:15:00+07:00
  checked: Persistent CLI routing regression and final source checks
  found: Three hardened routing/authority tests pass; `git diff --check` and `py_compile` pass. The canonical Plan 05 closure still verifies at SHA-256 `7ac554...89c7`.
  implication: The implementation is syntactically valid, whitespace-clean, regression-protected, and does not rewrite the controlling upstream authority.

## Eliminated

- hypothesis: The Plan 05 final comparison authority or repository source closure is malformed.
  evidence: The canonical final-authority loader succeeds and verifies the current source closure and both request roots.
  timestamp: 2026-08-26T01:10:00+07:00
- hypothesis: The historical amendment bytes/hash are corrupted rather than intentionally superseded.
  evidence: The final-authority loader parses the same bytes with the strict historical schema and verifies the hash bound by final-comparison-authority.json.
  timestamp: 2026-08-26T01:10:00+07:00

## Resolution

- root_cause: Plan 06 retained the pre-Plan-05 live scope-amendment/single-request authority contract in both its shared CLI loader and human-review re-verifier, so it rejects the intentionally historical source inventory and cannot resolve the selected PhoBERT v12 run through its recovery request.
- fix: Added an additive Plan 06 review consumer outside the frozen Plan 05 comparison closure. It authenticates the canonical final-authority artifact and both request roots as frozen upstream provenance, binds the v3 manifest/queue to that authority, and resolves human-review bundle checks through each run's own origin; CLI routing retains the legacy v2 path.
- verification:
    target_test:
      result: pass
      evidence: "Queue verifier passes exactly 52 rows; real human finalization and immediate verify-only replay both succeed."
    mutation_check:
      result: skipped
      reason_if_skipped: "No Python mutation framework is configured; Stryker is not applicable. A semantic regression explicitly proves live-loader failure after source drift while the frozen-upstream review loader succeeds."
      mutant_killed: null
    no_op_deletion:
      result: pass
      deletion_justified_by_rca: false
      evidence: "The diff adds a strict review consumer and CLI routing; it does not delete, short-circuit, weaken, or bypass artifact/hash/origin checks."
    adjacent_tests:
      result: pass
      suites_run:
        - "19 Phase 40 review/authority/CLI tests"
        - "3 hardened routing/authority regression tests"
        - "py_compile and git diff --check"
      constraint: "Full model-adaptation suite intentionally not run because the hard boundary forbids Phase 41 test-split access; relevant Phase 40-only coverage passed."
    revert_and_reconfirm:
      result: pass
      bug_returned_on_revert: true
      fixed_on_reapply: true
      evidence: "Path-scoped stash restored the original Pydantic allowlist error; stash pop restored 52-row success."
    guardrail_verdict: accepted
    human_verification:
      result: pass
      evidence: "The reviewer confirmed the 52-row report/manifest distribution (46 supported, 4 unsupported, 1 gold-label concern, 1 ambiguous), Vietnamese attestation true, reviewer-return SHA-256 96ff351e03ba7fee37fef09c1660372dd9ab36a289d8171ffb06893650692074 at 62,558 bytes, and no diff-check error."
- oracle_type: derived
- files_changed:
  - tests/model_adaptation/test_phase40_final_authority.py
  - src/model_adaptation/phase40_review.py
  - src/model_adaptation/cli.py
  - tests/model_adaptation/test_cli.py
  - data/models/phase40/review/human-review-notes.jsonl
  - data/models/phase40/review/human-review-manifest.json
  - data/models/phase40/review/human-review-report.md

## Prevention

- branching_5_whys:
  - code: Plan 06 kept a live `Phase40ScopeAmendment` consumer because its downstream review seam predated the version-3 final-comparison authority; that made an intentionally historical source inventory look invalid after Plan 05 evolved and froze the comparison authority.
  - config_data: The final authority, both request roots, and historical amendment were internally valid and hash-bound, but no downstream contract test required Plan 06 to interpret those frozen identities together; valid provenance therefore exposed the stale code path instead of protecting against it.
  - and_gate: No. The stale Plan 06 authority contract alone reproduced the failure; malformed configuration or corrupt data were eliminated.
- why_not_caught: The Phase 40 test gate covered the Plan 05 authority producer and the legacy Plan 06 path separately, but no regression exercised a v3 review consumer after legitimate source-closure drift with a recovery-request-selected run.
- recurrence_guard: `tests/model_adaptation/test_phase40_final_authority.py::test_review_handoff_accepts_hash_bound_historical_scope_source`, `tests/model_adaptation/test_phase40_final_authority.py::test_review_handoff_rejects_noncanonical_scope_path`, and `tests/model_adaptation/test_cli.py::test_phase40_v3_review_loader_uses_frozen_upstream_authority` now enforce the live-rerun versus frozen-upstream boundary and persistent v3 CLI routing.
