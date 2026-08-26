---
phase: 40-multi-model-training-evidence
verified: 2026-08-26T03:56:12Z
status: passed
score: 16/16 must-haves verified
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: passed
  previous_score: 16/16
  warnings_closed:
    - "Historical live-training report now has an explicit current-status banner"
    - "Plan 05 replay now names the frozen capability-gated comparison launcher"
  regressions: []
decision_coverage:
  honored: 0
  total: 0
  not_honored: []
---

# Phase 40: Multi-Model Training Evidence Verification Report

**Phase Goal:** Two fresh full local models—genuine Qwen QLoRA and PhoBERT—plus one bounded ordinary-LoRA feasibility probe provide logged evidence for the RTX 5050 adaptation decision without claiming unmeasured full-LoRA accuracy.

**Verified:** 2026-08-26T03:56:12Z  
**Status:** passed  
**Re-verification:** Yes — focused regression check after both documentation warnings were closed

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|---|---|---|
| 1 | Phase 40 is bound to the frozen 1,658-row train and 219-row validation identities while the 220-row Phase 41 split remains opaque. | ✓ VERIFIED | `phase40-verify-run-request` passed. Both full-run manifests carry train SHA `5fa46382...02e8b` and validation SHA `746ae6ed...5986d3`; the transfer ZIP contains only `phase40-input-manifest.json`, `train.jsonl`, and `val.jsonl`. `phase40_contract.py:482-515` opens only the authority, train, and validation files. This verification made zero filesystem operation on the reserved split; only its already-frozen opaque metadata was read from authorities. |
| 2 | Input paths, model family, adaptation mode, and run kind are typed and fail closed before model or output work. | ✓ VERIFIED | Plan 01 artifact/link checks passed 3/3 and 4/4. The focused behavioral suite exercises reject-before-open paths, explicit experiment identities, resume controls, and forbidden mode combinations. |
| 3 | Requested QLoRA can only proceed as genuine NF4 four-bit adapter training; Qwen supervision/parser/checkpoint selection remain strict and deterministic. | ✓ VERIFIED | Probe and full-run proofs record `resolved_mode=4bit-qlora`, NF4, double quantization, 252 `Linear4bit` modules, frozen base weights, 504 adapter trainables, and finite/nonzero adapter gradients. Quantization, parser, validation-order, and selection tests passed in the 226-test verifier run. |
| 4 | The ordinary-LoRA branch is a genuine bounded RTX 5050 feasibility result with its incomplete outcome and discard truth preserved. | ✓ VERIFIED | `lora-retry-1/outcome.json` records 31 observed/26 retained steps, median 53.2743492 s/step, peak 7,902 MiB device VRAM, 9 MiB minimum free, peak system RAM 22,479,200,256 bytes, no OOM, `status=error`, and `stop_reason=parent_controller_error`. The discard receipt proves the disposable runtime is absent. |
| 5 | The QLoRA probe completed the exact measured target and discarded its adapter. | ✓ VERIFIED | `python -m src.model_adaptation.phase40_qlora_session verify --repo-root .` passed. The retained outcome has 5 warm-up + 40 measured steps, median 3.46238915 s/step, 346.9835 tokens/s, 7,516 MiB peak VRAM, 22,136,381,440 bytes peak system RAM, 89°C, 90.36 W, and a verified discard receipt. |
| 6 | Ordinary LoRA remains resource evidence only; no full-LoRA accuracy or superiority claim exists. | ✓ VERIFIED | The final comparison marks full LoRA `cancelled_before_start`; the LoRA probe is non-comparison-eligible and supplies no predictions. The probe and comparison reports explicitly reject a completed full-LoRA, accuracy, OOM-impossibility, variance, t-test, significance, or stable-superiority claim. |
| 7 | A fresh full Qwen QLoRA run completed locally from step zero and its selected model was exported as verified Q8_0 GGUF. | ✓ VERIFIED | `phase40-verify-run-evidence` passed for `phase40-qwen-qlora-full-seed42-v1`. Raw events contain 1,245 optimizer-step records and a terminal `run_end`; selected step 200 has macro-F1 0.9885153110, accuracy 0.9908675799, zero invalid outputs, and passed safety gates. The portable GGUF receipt binds a 4,280,403,232-byte Q8_0 artifact, SHA `457f6f92...d18ab`, with original and independent load smokes passing. |
| 8 | A fresh full, non-quantized PhoBERT classification-head model completed locally on the same frozen train/validation identities. | ✓ VERIFIED | `phase40-verify-run-evidence` passed for `phase40-phobert-full-seed42-v12`. Identity is `phobert/classification-head/full`, quantization is null, events contain 312 optimizer steps and `run_end`, and selected step 100 has macro-F1 0.9848929140, accuracy 0.9863013699, zero invalid outputs, and passed safety gates. The resolved config has four locked labels, no PEFT/LoRA targets, and a fully trained sequence-classification task. |
| 9 | Both full bundles retain substantive, hash-verifiable evidence and exactly 219 ordered predictions each. | ✓ VERIFIED | Both real bundle verifiers passed. Each bundle contains events, resolved config, trainer state, validation metrics, selected/model artifacts, checkpoint predictions/metrics, curves, hardware/CUDA/package identity, and graph provenance. Independent inspection found 219 unique ordered validation IDs per model, exact sequence 0–218, identical row-ID order, and zero invalid states. |
| 10 | The final validation comparison honestly includes both models and preserves all safety/limitation disclosures. | ✓ VERIFIED | `comparison-manifest.json` is `complete`, `quality_comparison_admissible=true`, has exactly the Qwen/PhoBERT runs, 219 rows per model, both safety gates passing, and `speed_comparison_admissible=false`. Its limitations explicitly forbid held-out, variance, significance, and full-LoRA quality claims. The canonical comparison report and planning mirror are byte-identical at SHA `fb7424b7...8dd5`. |
| 11 | Every retained graph is mechanically traceable to raw events/metrics. | ✓ VERIFIED | Both run-evidence verifiers rehashed event, metric, normalized-data, renderer-option, PNG, and model-artifact identities. An independent rebuild reproduced Qwen PNG SHA `5d773f7b...d56e` and PhoBERT PNG SHA `40818556...246` byte-for-byte. |
| 12 | The train/validation transfer and optional Colab controllers are deterministic, pinned, and exclude held-out content. | ✓ VERIFIED | The run-request verifier passed; the input archive has exactly three members and no held-out member. `phase40-validate-notebooks --root notebooks/phase40` passed for all three controllers. The notebooks use repository APIs, fixed archive paths, exact package/model revisions, and pre-open bundle verification. |
| 13 | Plan 05’s selected model/comparison identities remain frozen, and the review queue contains only Qwen QLoRA and PhoBERT rows. | ✓ VERIFIED | The live queue verifier passed with 52 rows. Final comparison-authority SHA is `7ac5541d...89c7`, frozen source-tree SHA is `520aeb6a...cc2`, comparison-manifest SHA is `08f76337...55d5`, and queue SHA is `c79fff00...1010`. The queue contains 26 rows for each selected full model and no ordinary-LoRA row. |
| 14 | A Vietnamese-fluent reviewer assessed every frozen full-message queue row with exact immutable lineage. | ✓ VERIFIED | Queue, return, and normalized notes each have 52 rows and 52 unique `(model_run_id, validation_row_id)` keys. All ten frozen fields match at every position with zero mismatches; all 52 raw messages and mechanism notes are nonblank. Distribution is 46 supported, 4 unsupported, 1 gold-label concern, and 1 ambiguous. |
| 15 | Human review is qualitative-only, v3-lineage-bound, and byte-stably reproducible without mutating labels, predictions, metrics, or checkpoints. | ✓ VERIFIED | The v3 manifest binds comparison, final authority, superseded amendment, queue, reviewer return, notes, report, ordered validation IDs, and Vietnamese attestation. `--verify-only` passed repeatedly and a before/after hash fence reported `BYTE_STABLE=True`. Machine report and planning mirror are byte-identical at SHA `f4bfac79...e4ae0`. |
| 16 | The independent code-review findings are resolved, the local model identities are final, and the unused Colab contingency is closed without retraining. | ✓ VERIFIED | Review status is `resolved`; all 6 findings are mapped to fixes and regression tests. The verifier’s combined security/contract suite passed 226/226. Comparison origin is `local_primary`, both rows identify the RTX 5050, and the 52-row review did not alter frozen results. The final Plan 06 decision closes Colab unused; no external run was admitted. |

**Score:** 16/16 truths verified (0 present-but-behavior-unverified)

## Roadmap Success Criteria Coverage

| Roadmap criterion | Covered by truths | Status |
|---|---:|---|
| Frozen train/validation contract and opaque test boundary | 1, 2, 12 | ✓ VERIFIED |
| Bounded probes with genuine measured outcomes, ETA/resource evidence, and discarded adapters | 4, 5 | ✓ VERIFIED |
| Fresh local Qwen/PhoBERT runs; ordinary LoRA resource-only; contingency discipline | 6, 7, 8, 16 | ✓ VERIFIED |
| QLoRA fails closed unless genuine four-bit proof succeeds | 3, 5, 7 | ✓ VERIFIED |
| Real full PhoBERT classifier, not artificial QLoRA | 8 | ✓ VERIFIED |
| Resource comparison separated from Qwen-versus-PhoBERT quality comparison | 6, 10 | ✓ VERIFIED |
| Complete retained evidence bundles | 7, 8, 9 | ✓ VERIFIED |
| Graphs mechanically derived from retained raw logs, never held-out data | 1, 11 | ✓ VERIFIED |

## Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `src/model_adaptation/phase40_contract.py`, `phase40_modes.py`, `phase40_metrics.py` | Canonical input/mode/parser/selection contract | ✓ VERIFIED | GSD artifact 3/3 and key-link 4/4 checks pass; substantive tests exercise behavior. |
| `src/model_adaptation/phase40_evidence.py`, callbacks, graphs, handoff | Evidence lifecycle, raw-log graphing, transfer/comparison/review wiring | ✓ VERIFIED | GSD artifact 5/5 and link 7/7 checks pass. |
| `src/model_adaptation/phobert_training.py` | Full non-quantized PhoBERT trainer | ✓ VERIFIED | Real completed bundle, substantive backend, strict tests, and shared metric/ID wiring. |
| `data/models/phase40/probes/rtx5050-local-decision/lora-retry-1/` | Honest bounded ordinary-LoRA outcome | ✓ VERIFIED | Outcome, raw optimizer/telemetry logs, full-precision proof, recovery seals, and discard receipt present and hash-bound. |
| `data/models/phase40/probes/rtx5050-qlora-session-20260825/` | Genuine exact-target QLoRA probe | ✓ VERIFIED | Session verifier passes; 22-artifact manifest and discard truth hold. |
| `data/models/phase40/full/qwen-qlora/run-evidence.json` | Complete local genuine-Qwen-QLoRA bundle | ✓ VERIFIED | Live verifier passes, evidence SHA `ce493f05...3f9da`. |
| `data/models/phase40/full/phobert/run-evidence.json` | Complete local PhoBERT bundle | ✓ VERIFIED | Live verifier passes, evidence SHA `48907892...855c`. |
| `data/models/phase40/qwen-gguf-verification-receipt.json` | Portable Q8_0 identity and load proof | ✓ VERIFIED | Status `verified`, selection lineage and two load-smoke results bound. |
| `data/models/phase40/final-comparison-authority.json` and `comparison-manifest.json` | Frozen two-model comparison authority/results | ✓ VERIFIED | Current source/authority/queue verifier passes; hashes above. |
| `data/models/phase40/review/review-queue.jsonl` | Deterministic mandatory/calibration queue | ✓ VERIFIED | 52 rows, 26/model, full message/source hash, exact queue verifier PASS. |
| `data/models/phase40/review/reviewer-return.jsonl`, notes, v3 manifest, report | Exact-coverage human closure | ✓ VERIFIED | Finalizer replay, independent field comparison, and all hashes pass. |
| `40-VALIDATION-COMPARISON.md`, `40-VIETNAMESE-ERROR-REVIEW.md` | Human-readable byte mirrors | ✓ VERIFIED | Byte-identical to canonical machine reports. |

**Controlled path deviation:** Plan 40-04’s initially anticipated `rtx5050-qwen-{lora,qlora}` roots are absent. The real immutable-clock/recovery design necessarily sealed ordinary LoRA under `rtx5050-local-decision/lora-retry-1` and QLoRA under the dated `rtx5050-qlora-session-20260825` root. The replacement artifacts fully satisfy the roadmap truths and are verified above; no result was manufactured or lost.

## Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| Canonical Phase 39 authority | Phase 40 run request and both full bundles | Preflight and exact split identities | ✓ WIRED | Request and both bundle verifiers pass; only train/validation identities appear in run evidence. |
| Quantization request | Qwen model construction/training | `ExperimentIdentity` and genuine mode proof | ✓ WIRED | Probe/full proof fields and fail-closed tests pass. |
| Raw events/metrics | Curves | Hash-bound graph provenance renderer | ✓ WIRED | Independent byte-identical rebuild for both models. |
| Full Qwen/PhoBERT predictions | Comparison and queue | Stable validation-row-ID joins | ✓ WIRED | 219 ordered IDs/model; queue verifier re-derives 52 rows. |
| Queue | Reviewer return | Exact ordered immutable fields | ✓ WIRED | Zero field mismatch across all 52 rows. |
| Reviewer return | v3 manifest/report | Strict finalizer, notes normalization, manifest-last publication | ✓ WIRED | Real verify-only replay passes; publication/security tests pass. |
| Human-review v3 manifest | Phase 41 closure loader | Strict schema branch and side-artifact rehash | ✓ WIRED | Synthetic downstream v3 ingestion and redirect/side-artifact regression tests pass without reserved access. |

## Data-Flow Trace (Level 4)

| Artifact | Data variable | Source | Produces real data | Status |
|---|---|---|---|---|
| Qwen/PhoBERT validation metrics | `validation_metrics` | 219 ordered selected-checkpoint prediction rows | Yes | ✓ FLOWING |
| Comparison results | `runs`, recall/F1/safety fields | Reverified full-run evidence and selected prediction bundles | Yes | ✓ FLOWING |
| Loss curves | normalized train/eval points | Append-only `events.jsonl` plus validation metrics | Yes | ✓ FLOWING |
| Review queue | full message, source hash, gold/prediction state, slices | Canonical validation snapshot joined to frozen predictions | Yes | ✓ FLOWING |
| Review report | assessments and per-slice counts | Exact reviewer return normalized into notes/manifest | Yes | ✓ FLOWING |

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| Immutable run request/source/input verification | `phase40-verify-run-request ...` | Request verified | ✓ PASS |
| Genuine dated QLoRA probe replay | `python -m src.model_adaptation.phase40_qlora_session verify --repo-root .` | `verified=true`, measured target reached | ✓ PASS |
| Full Qwen evidence replay | `phase40-verify-run-evidence --run-root .../qwen-qlora` | complete | ✓ PASS |
| Full PhoBERT evidence replay | `phase40-verify-run-evidence --run-root .../phobert` | complete | ✓ PASS |
| Static notebook boundary | `phase40-validate-notebooks --root notebooks/phase40` | 3 notebooks valid | ✓ PASS |
| Review queue re-derivation | `phase40-verify-review-queue ...` | 52 rows | ✓ PASS |
| Human review v3 replay | `phase40-finalize-human-review ... --verify-only` | PASS repeatedly; byte-stable fence true | ✓ PASS |
| Focused contract/security regression | selected Phase 40/41 boundary tests | 226 passed in 31.43s | ✓ PASS |

## Probe Execution

| Probe | Command | Result | Status |
|---|---|---|---|
| Dated QLoRA evidence verifier | `python -m src.model_adaptation.phase40_qlora_session verify --repo-root .` | Source tree `46bce0f7...e9271`, measured/evidence target reached | PASS |
| Ordinary-LoRA sealed evidence | Independent authority/outcome/discard rehash inspection | Genuine incomplete pressure outcome, no OOM claim, runtime absent | PASS |
| Qwen full bundle | `phase40-verify-run-evidence` | Complete | PASS |
| PhoBERT full bundle | `phase40-verify-run-evidence` | Complete | PASS |
| Review closure | Queue verifier plus v3 verify-only finalizer | Exact 52-row coverage and stable outputs | PASS |

## Requirements Coverage

| Requirement | Source plans | Description | Status | Evidence |
|---|---|---|---|---|
| TRAIN-01 | 40-02, 40-04, 40-05 | Bounded non-quantized LoRA feasibility evidence and discard | ✓ SATISFIED | Truth 4; real incomplete run, timing/resources, full-precision proof, discard receipt. |
| TRAIN-02 | 40-01, 40-02, 40-04, 40-05 | QLoRA probe plus fresh genuine full QLoRA and GGUF | ✓ SATISFIED | Truths 3, 5, 7. |
| TRAIN-03 | 40-01 through 40-05 | Resource-only LoRA/QLoRA conclusion, no full-LoRA accuracy claim | ✓ SATISFIED | Truths 6 and 10. |
| TRAIN-04 | 40-03, 40-05 | Full PhoBERT classification-head baseline | ✓ SATISFIED | Truth 8. |
| TRAIN-05 | 40-02, 40-03, 40-05, 40-06 | Honest two-model validation comparison and qualitative review | ✓ SATISFIED | Truths 10, 13, 14, 15. |
| TRAIN-06 | 40-01 through 40-06 | Hash-linked evidence, graphs, environment/resources, contingency isolation | ✓ SATISFIED | Truths 9, 11, 12, 15, 16. |

No Phase 40 requirement is orphaned: TRAIN-01 through TRAIN-06 all appear in plan frontmatter and are marked complete in `.planning/REQUIREMENTS.md`.

## Test Quality Audit

| Test group | Linked requirements | Active result | Disabled/skip impact | Circularity | Assertion level | Verdict |
|---|---|---:|---|---|---|---|
| Contract, quantization, evidence, PhoBERT, QLoRA session | TRAIN-01–04, TRAIN-06 | Included in 226-pass verifier suite | Platform capability skips are conditional only; verifier run reported 0 skips | No self-generated oracle used for the real artifacts | Value + behavioral | PASS |
| CLI, Plan 06 review, final authority, Phase 41 v3 boundary | TRAIN-05, TRAIN-06 | Included in 226-pass verifier suite | 0 skips in verifier run | Synthetic fixtures test failure paths; real 52-row replay is separately verified | Behavioral/end-to-end | PASS |
| Independent evidence/authority/GGUF/recovery audit | TRAIN-01–06 | 109 passed | No requirement depends solely on a skipped test | Graph reconstruction compared to retained independent raw artifacts | Value + behavioral | PASS |

**Disabled tests on requirements:** 0 active omissions in the verifier run.  
**Circular expected-value patterns:** 0 affecting requirement evidence.  
**Insufficient assertions:** 0; real artifact rehash/replay supplements synthetic tests.

## Negative Contract / Prohibition Checks

| Prohibition group | Evidence | Status |
|---|---|---|
| No held-out access during training, graphing, comparison, or review | Code carries held-out identity as opaque metadata; transfer archive has no test member; comparison launch receipt records `reserved_split_access_attempted=false`; this verifier maintained the same zero-access boundary | ✓ VERIFIED |
| No QLoRA-to-LoRA fallback | Genuine probe/full quantization proofs plus failure-path tests | ✓ VERIFIED |
| No malformed-output-to-benign coercion | Strict parser and zero-invalid selected outputs; parser tests | ✓ VERIFIED |
| No probe resume/publication/parent lineage | Both discard receipts, full-run `step_origin=0`, `probe_parent=null`, comparison excludes probe predictions | ✓ VERIFIED |
| No hand-drawn graphs | Hash-linked raw-log provenance and byte-identical rebuild | ✓ VERIFIED |
| No full-LoRA quality/statistical claim | Final manifest/report limitations and absence of LoRA predictions | ✓ VERIFIED |
| No human-review mutation or omitted key | Exact 52-row immutable comparison, v3 finalizer, and replay tests | ✓ VERIFIED |
| No external review consumer in implementation | Review input is a user-authored local file; finalizer is local-only and the manifest carries Vietnamese attestation | ✓ VERIFIED |

## Anti-Patterns and Non-Blocking Findings

| File / area | Pattern | Severity | Impact |
|---|---|---|---|
| Phase 40 implementation files | No unreferenced `TBD`, `FIXME`, `XXX`, `TODO`, `HACK`, or placeholder implementation affecting Phase 40 | None | No blocker. |
| `40-LOCAL-FULL-QLORA-REPORT.md` | Prior warning: historical live-progress text could be mistaken for current status | ✓ RESOLVED | The file now opens with an explicit historical-log banner, states both models and review completed, and routes current claims to the frozen comparison, review, and verification reports. |
| Plan 05 comparison replay | Prior warning: the documented general CLI route was superseded | ✓ RESOLVED | The verification block now invokes `pwsh -NoProfile -File scripts/phase40_comparison_launcher.ps1`. The launcher exists and exactly matches the final authority: 59,842 bytes, SHA `f42f21b5...3196`. |
| External 4.28 GB Q8_0 file | Verified through a portable receipt and two load-smoke records, not freshly rehashed/loaded during this audit | ℹ️ Limitation | Disclosed as portable-receipt evidence; no false fresh-load claim is made here. |

## Focused Re-verification — Documentation Closure

| Check | Evidence | Status |
|---|---|---|
| Historical-log warning | The first block of `40-LOCAL-FULL-QLORA-REPORT.md` explicitly says the time-stamped running/queued sections are historical and not current status | ✓ CLOSED |
| Active replay command | `40-05-PLAN.md` uses the capability-gated PowerShell launcher; the referenced script's byte count and SHA match `final-comparison-authority.json` exactly | ✓ CLOSED |
| Closure record | `40-06-SUMMARY.md` records both warning closures and retains TRAIN-01–TRAIN-06 completion | ✓ CLOSED |
| Frozen comparison/review regression | Real review-queue verification still passes with 52 rows after the documentation-only edits | ✓ PASS |
| Reserved boundary | No filesystem operation was performed on the reserved Phase 41 split during re-verification | ✓ PRESERVED |

## Decision Coverage

The configured decision-coverage query reported: **No trackable decisions in CONTEXT.md** (`0/0`, non-blocking). The roadmap and plan-level decisions were instead checked directly through the observable truths above.

## Human Verification Required

N/A — Phase 40 is an evidence-pipeline/model-training foundation phase with no user-facing UI. The genuine Vietnamese review gate was already completed with exact 52-row coverage, and all remaining acceptance criteria are programmatically verifiable. No behavior-dependent truth remains untested.

## Gaps Summary

No goal-blocking gaps and no remaining documentation warnings. TRAIN-01 through TRAIN-06 and all eight roadmap success criteria remain achieved; the focused re-verification found no regression in the frozen comparison or 52-row review closure.

---

_Verified: 2026-08-26T03:56:12Z_  
_Verifier: the agent (gsd-verifier)_
