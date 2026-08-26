---
phase: 41-one-shot-two-model-evaluation
verified: 2026-08-26T15:36:41Z
status: passed
score: 12/12 must-haves verified
behavior_unverified: 0
overrides_applied: 0
---

# Phase 41: Held-Out Evaluation Discipline Verification Report

**Phase Goal:** The reserved test split is evaluated exactly once against the finalized local Qwen QLoRA and PhoBERT models, after validation-stage contingency decisions are closed, producing one honest two-model comparison before any optional all-data deployment fit.

**Verified:** 2026-08-26T15:36:41Z  
**Status:** passed  
**Re-verification:** No — initial goal verification after release-review remediation

## Verification Boundary

This verification used committed source, plans, the protected operational evidence at `C:\ProgramData\VNPhish\phase41-evaluation-evidence`, the protected claim/completion records, the committed verified export, and the external provenance erratum.

It did **not** open, enumerate, stat, hash, or otherwise access the reserved split or its containing directory. It did not invoke either model or rerun evaluation. Only verify-only evidence checks and synthetic/temp-file tests were executed.

SUMMARY claims were treated as discovery aids, not proof. The verdict below rests on source tracing, protected records, recomputed prediction-artifact metrics, hash/link checks, and focused behavioral tests.

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---:|---|---|---|
| 1 | The production one-shot path was hardened end to end with synthetic authorities/messages/predictors before real evaluation. | ✓ VERIFIED | The synthetic suite exercises the state machine, shared snapshot, permanent post-claim failure, deployment disposition, replay prevention, and one-handle/one-read contract. Five selected state-machine tests passed during this verification; the release remediation did not alter those execution paths. |
| 2 | The state machine creates a durable content-SHA claim before the reserved-split handle and cannot regain an opportunity through a copied split, changed output root, deleted local receipt, or second process. | ✓ VERIFIED | `phase41_evaluation.py` creates the protected claim before `_open_snapshot_once`; the protected and operational claim hashes both equal `0806b927...`, and completion hashes both equal `1ec4d74f...`. Synthetic replay/copy/output-root tests passed. |
| 3 | Phase 40 closure, validation review, contingency closure, exact model identities, protocols, source closure, and synthetic model smokes were frozen before authorization. | ✓ VERIFIED | The preauthorization receipt is `prepared`, requires both models ready and validation contingency closed, and hash-binds the Phase 40 comparison/review, source manifest, runtime authorities, protocol authority, and passed model smokes. |
| 4 | The authorized models are exactly the finalized Qwen QLoRA and PhoBERT classification-head checkpoints. | ✓ VERIFIED | Qwen: `phase40-qwen-qlora-full-seed42-v1`, checkpoint `adapter-state-sha256:1387686e...`, artifact `466d107d...`, base `Qwen/Qwen3-4B-Instruct-2507`. PhoBERT: `phase40-phobert-full-seed42-v12`, checkpoint `model-state-sha256:f6d80111...`, artifact `60b66f40...`, base `vinai/phobert-base-v2`. Request, preauthorization, protocols, authorization, results, and disposition agree. |
| 5 | Explicit human authorization bound the exact prepared authority and precommitted deployment-fit choice before the successful invocation. | ✓ VERIFIED | `one-shot-authorization.json` records `AUTHORIZE PHASE 41 ONE-SHOT; DEPLOYMENT FIT DEFERRED` at `2026-08-26T14:22:00.950121Z`, binds prepared SHA `c3d378df...`, and lists both exact checkpoint identities. |
| 6 | Five superseded launcher attempts failed before their own claim/access boundaries and are not misrepresented as a global filesystem audit. | ✓ VERIFIED | Reparse `53082150...`, loader binding `4cf56b47...`, missing argument `9a934595...`, captured-helper identity `52b11b41...`, and Qwen lease identity `45b5698b...` each record no invocation-local claim/evaluation access/spend. The erratum correctly limits that statement to those invocations and disambiguates the legacy captured-helper/lease field. |
| 7 | Exactly one successful claimed launcher execution evaluated both models on one immutable cohort through one handle and one sequential payload read, with no retry. | ✓ VERIFIED | Access receipt: 220 records, 141,638 bytes, SHA `6f208fb6...`, `handle_acquisitions=1`, `sequential_payload_reads=1`, expected 70/35/49/66 support, raw content not retained. Claim time is `14:23:26Z`; terminal completion is `15:01:21Z`; `rerun_permitted=false`. A single protected claim/completion pair matches operational bytes. |
| 8 | Qwen and PhoBERT used the same ordered cohort while predictors did not receive gold labels. | ✓ VERIFIED | Source tracing shows a single tuple-backed snapshot and text-only predictor view passed to Qwen then PhoBERT, with gold retained by the evaluator. Both prediction artifacts contain 220 unique, aligned sequence/row/source identities and the same gold support; no raw message or raw model-output field is exported. |
| 9 | Both models have complete, independently reproducible metrics and safety/error accounting, and the comparison plainly reports every advantage/tie. | ✓ VERIFIED | Offline recomputation from prediction artifacts reproduces all confusion matrices, macro/weighted F1, accuracy, per-class precision/recall/F1/support, invalid outputs, and risky-to-benign counts. `results.md` plainly states the PhoBERT advantages and Qwen benign-class advantages without a winner/selection field. |
| 10 | Held-out results are terminal evidence and cannot trigger repair, retraining, threshold/checkpoint/model selection, contingency activation, or a repeated pass. | ✓ VERIFIED | Results, terminal, evidence manifest, protected completion seal, and source code all encode the no-retry/no-test-driven-action policy. The protected claim permanently blocks another governed evaluation for the same content SHA. No remediation invoked a model/evaluation command. |
| 11 | Prior exposure and all known automated integrity reads are disclosed honestly; global zero-filesystem-access wording is retracted without altering sealed results. | ✓ VERIFIED | `phase41-provenance-erratum.json` at SHA `c7be7434...` records at least two broad pre-run and one focused post-run parse/stat/hash reads, states their non-inference/non-selection impact, retracts untouched/global-zero-access claims, and is mandatory in Phase 42/43 handoffs. Frozen export tree `df5ae00a...` is unchanged. |
| 12 | Deployment fitting was precommitted and then deferred; no deployment fit or unbiased-score inheritance occurred. | ✓ VERIFIED | Authorization precommits `deferred`. `deployment-fit-disposition.json` reproduces both checkpoint identities, binds manifest/terminal/seal, sets `test_outcome_used_for_tuning=false` and `unbiased_test_score_claim=false`, and executes no fit. |

**Score:** 12/12 truths verified (0 present-but-behavior-unverified)

## Exact Invocation and Access History

| Event | Evidence | Claim/access result | Verification |
|---|---|---|---|
| Repository output-root reparse rejection | `41-02-preclaim-failure.json`, SHA `5308215048bd1ad08c6fe7fcaea4f579c7ec20056d85eae91aea26e4fa7481c5` | One failed invocation; no claim, access, or spend | ✓ VERIFIED |
| Staged loader source-path rejection | Failed-invocation receipt, SHA `4cf56b478bf9deeacf8fce5a9635692cb81ff0675281a2a3da7cb2ad4837b33f` | One failed invocation; no claim, access, or spend | ✓ VERIFIED |
| Missing `OutputRoot` rejection | Failed-invocation receipt, SHA `9a934595a7c011a03d3e38cc19f33d65360d9dce6693492096118a598247ef30` | One failed invocation; no claim, access, or spend | ✓ VERIFIED |
| Captured-helper identity rejection | Failed-invocation receipt, SHA `52b11b418e0ec322230343ccae054460335bdbb523289166b207bb54876d1a3e` | One failed invocation; no claim, access, or spend | ✓ VERIFIED |
| Qwen lease identity rejection | Failed-invocation receipt, SHA `45b5698b6b9d6d08a34d12bb5cf3ab625f5b013b1903b37b9e34b10b7b7dcb86` | One failed invocation; no claim, access, or spend | ✓ VERIFIED |
| Final authorized launcher | Claim `0806b927...`; access `803e5097...`; terminal `0a66f15d...`; completion `1ec4d74f...` | One successful claimed evaluation; one handle/read; completed; retry forbidden | ✓ VERIFIED |

The five failure receipts audit only their own launcher invocations. They do not erase or contradict the separately disclosed pytest integrity reads outside the launcher.

## Result Verification

| Model | Accuracy | Macro F1 | Weighted F1 | Invalid outputs | Risky → benign | Status |
|---|---:|---:|---:|---:|---:|---|
| Qwen QLoRA | 0.981818 | 0.980493 | 0.981848 | 0 | 1 | ✓ VERIFIED |
| PhoBERT | 0.990909 | 0.990892 | 0.990925 | 0 | 1 | ✓ VERIFIED |

The prediction artifacts independently reproduce the recorded matrices:

- Qwen: `[[66,3,0,1,0],[0,35,0,0,0],[0,0,49,0,0],[0,0,0,66,0]]`
- PhoBERT: `[[69,0,0,1,0],[0,35,0,0,0],[0,0,49,0,0],[0,1,0,65,0]]`

PhoBERT is reported unhedged as higher on macro F1, weighted F1, accuracy, bank-impersonation recall/F1, and Zalo precision/F1. Qwen is higher on benign precision/recall/F1. Task-scam precision/recall/F1 and the listed safety/error counts tie.

## Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `src/model_adaptation/phase41_evaluation.py` | Claim-before-open evaluator, metrics, terminal evidence, verifier, export | ✓ VERIFIED | Substantive, wired through CLI/launcher, protected registry, and focused tests. |
| `src/model_adaptation/phase41_protocols.py` | Frozen Qwen/PhoBERT protocols and adapters | ✓ VERIFIED | Exact checkpoint, base-model, preprocessing/decoder, package, retry, and smoke identities are hash-bound. |
| `scripts/phase41_one_shot_launcher.ps1` | Fixed protected staged launcher | ✓ VERIFIED | Enforces the ProgramData operational root and locked staged authority. |
| `C:\ProgramData\VNPhish\phase41-evaluation-evidence` | Authoritative terminal evidence | ✓ VERIFIED | Verify-only passes at manifest SHA `9ac54d58...`; all manifest links validate. |
| `C:\ProgramData\VNPhish\phase41-one-shot-claims` | Protected global claim and completion | ✓ VERIFIED | Operational/protected claim and completion bytes match exactly. |
| `data/models/phase41/verified-export/9ac54d58...` | Immutable repository mirror | ✓ VERIFIED | 16 receipt-listed artifacts; zero source/export hash mismatches; no raw messages; source remains authoritative. |
| `data/models/phase41/phase41-provenance-erratum.json` | Corrected provenance disclosure | ✓ VERIFIED | SHA `c7be74346f0e217c382e556fbf0a730cb33be50356d4155356a5b024871a1672`; mandatory downstream companion. |
| Phase 41 synthetic and release-remediation tests | State-machine, protocol, replay, boundary, export regressions | ✓ VERIFIED | Synthetic/temp-only focused checks pass; no live split test was run. |

The Plan 41-02 frontmatter retains historical root-level artifact aliases such as `data/models/phase41/results.json`. The executed architecture deliberately uses protected ProgramData authority plus the content-addressed committed export above. Manual Level 2–4 verification follows that documented execution architecture; the absent root aliases are not missing result evidence.

## Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| Phase 40 comparison/review authorities | Evaluation request and frozen protocols | Preauthorization hash and exact checkpoint identity checks | ✓ WIRED | Exactly Qwen QLoRA and PhoBERT selected; Colab contingency closed. |
| Explicit authorization | Protected claim | Prepared/auth/precommit hashes; durable exclusive claim before open | ✓ WIRED | Protected claim SHA equals operational claim SHA. |
| Claim | Access receipt | Claim SHA plus fixed path/content identities | ✓ WIRED | One handle, one sequential read, 220 records. |
| Shared snapshot | Qwen then PhoBERT prediction artifacts | Text-only predictor view; evaluator-held gold | ✓ WIRED | Cohort identities/support align across both files. |
| Prediction artifacts | Results/report | Verify-only metric recomputation | ✓ WIRED | Recomputed metrics and matrices match. |
| Results/report/access | Manifest → terminal → protected completion | SHA-linked terminal transaction | ✓ WIRED | Verify-only passes; protected completion matches operational copy. |
| Pre-result deployment choice | Post-result disposition | Precommit SHA and exact checkpoint identities | ✓ WIRED | Choice remains `deferred`; no unbiased-score claim. |
| External erratum | Phase 42/43 plans | Exact erratum SHA and mandatory limitation language | ✓ WIRED | Downstream plans require both export and erratum and reject untouched/global-zero-access wording. |

## Data-Flow Trace (Level 4)

| Artifact | Data variable | Source | Produces real evidence | Status |
|---|---|---|---|---|
| `evaluation-request.json` | selected models/held-out metadata | Frozen Phase 39/40 authorities | Yes — exact identities and opaque held-out metadata | ✓ FLOWING |
| `qwen-predictions.jsonl` / `phobert-predictions.jsonl` | aligned predictions | One immutable evaluator snapshot | Yes — 220 aligned rows each, no raw text | ✓ FLOWING |
| `results.json` / `results.md` | metrics, matrices, comparison | Both prediction artifacts | Yes — independently recomputed | ✓ FLOWING |
| `terminal.json` / protected completion | final status/no-retry | Manifest, claim, results, report, access receipt | Yes — complete hash chain | ✓ FLOWING |
| `phase41-provenance-erratum.json` | corrected access limitation | Release review plus committed failure/audit records | Yes — exact hash required downstream | ✓ FLOWING |

No evaluated value terminates in a static fallback, placeholder, or mock. Synthetic predictors are confined to tests/preauthorization smokes and are not the source of the terminal result artifacts.

## Behavioral Spot-Checks

| Behavior | Command/check | Result | Status |
|---|---|---|---|
| Frozen operational evidence verifies without models/split access | `python -m src.model_adaptation.cli phase41-verify-evidence --output-root C:\ProgramData\VNPhish\phase41-evaluation-evidence` | Exit 0; manifest `9ac54d58...` | ✓ PASS |
| Claim-before-open, shared snapshot, permanent failure, replay prevention, one handle/read | Five exact synthetic Phase 41 tests | 5 passed | ✓ PASS |
| Metadata-only default and pre-I/O live-audit rejection | Two exact fixture/trap-path tests | 2 passed | ✓ PASS |
| Transactional/idempotent export and Unicode-safe CLI | Four exact temp-only tests | 4 passed | ✓ PASS |
| Verified export matches operational evidence | Receipt-guided SHA-256 comparison | 16/16 match; 0 bad | ✓ PASS |
| Frozen export was not changed by remediation | Git tree-object comparison and exact-path diff | Tree remains `df5ae00a...`; diff empty | ✓ PASS |
| Metrics reproduce from prediction evidence | Offline fixed-label recomputation | Both matrices and all recorded aggregate/per-class values match | ✓ PASS |

The broad suite and explicit `live_split_integrity` test were deliberately not run. Running either was unnecessary for this verification and could cross the reserved-data boundary.

## Probe Execution

No standalone `probe-*.sh` is declared for Phase 41. The production-safe verify-only CLI is the phase's evidence probe and passed as recorded above.

## Requirements Coverage

| Requirement | Source plan | Description | Status | Evidence |
|---|---|---|---|---|
| EVAL-08 | 41-01, 41-02, ROADMAP | One shared-cohort model-evaluation pass over the canonical 220-row identity after both local models froze; honest exposure disclosure; no test-driven model action | ✓ SATISFIED | One protected claim/completion, one handle/read receipt, exact two models, terminal no-retry policy, and mandatory erratum disclosing prior human exposure plus automated pre/post integrity reads. |
| EVAL-09 | 41-01, 41-02, ROADMAP | Freeze/report both models plainly, include PhoBERT win, no ordinary-LoRA score, separate deployment fit with no unbiased claim | ✓ SATISFIED | Both full-model results/matrices are sealed; PhoBERT's advantage is explicit; ordinary LoRA has no result row; deployment fit is deferred with unbiased claim false. |

No additional Phase 41 requirement is orphaned in `REQUIREMENTS.md`.

## Anti-Patterns Found

| File/scope | Pattern | Severity | Impact |
|---|---|---|---|
| Phase 41 production, remediation, test, review, and erratum files | `TBD`, `FIXME`, `XXX`, `TODO`, `HACK`, `PLACEHOLDER`, or incomplete-stub wording | None | No blocker debt markers found. |
| `41-02-PLAN.md` frontmatter | Historical repository-root artifact aliases | ℹ️ Info | Automated path-only checking misses the protected-authority/content-addressed-export architecture; the actual artifacts are substantive, wired, and hash-verified. |
| Frozen preauthorization schema | Legacy captured-helper-named field binds the later lease audit | ℹ️ Info | Sealed evidence is immutable; mandatory erratum separately identifies and hashes both records. |

## Release Review Remediation

The review's two critical and two warning findings are closed without model/evaluation rerun:

- Default downstream-contract validation is metadata-only and has no split-directory parameter.
- Live split integrity validation is a separate entry point requiring the exact `VNPHISH_ENABLE_LIVE_SPLIT_INTEGRITY_AUDIT=I_UNDERSTAND_THIS_READS_LIVE_SPLITS` opt-in; its marked test is excluded from default pytest runs.
- A trap-path regression proves absent opt-in fails before open, parse, stat, enumerate, or hash.
- Export publication is staging-based, verified before atomic rename, cleans failed staging safely, and accepts an identical complete export idempotently.
- CLI output is encoding-safe on legacy Windows consoles.
- The external erratum corrects the access narrative and disambiguates the captured-helper versus Qwen-lease failure records.

## Residual Disclosures (Not Gaps)

1. The held-out file was **not** globally untouched before the launcher. At least two broad pre-run pytest executions and one post-run focused regression parsed, statted, and hashed the live split files. Those reads performed no model inference, external API call, human row display, training, tuning, selection, repair, or retry.
2. The five failed launcher receipts prove zero claim/evaluation access only within those five invocations. They are not a machine-wide access audit.
3. The frozen evidence retains historical self-assertion/legacy-field wording that cannot be rewritten without breaking its seal. Every consumer must pair the frozen export with erratum SHA `c7be7434...`.
4. Deployment fitting remains deferred. Phase 41 authorizes no all-data fit and makes no deployment-fit test-score claim.

## Human Verification Required

None. This is an evidence/infrastructure phase, and all goal-level truths have deterministic artifact, source, hash-chain, or focused synthetic behavioral evidence. A live split integrity audit is intentionally outside this verification boundary and is not needed to establish the phase goal.

## Gaps Summary

No blocking gaps remain. The phase goal is achieved provided downstream consumers treat the immutable verified export **and** the hash-identified external provenance erratum as one reporting authority. The result is accurately described as one terminal two-model evaluation pass—not as zero prior filesystem access.

---

_Verified: 2026-08-26T15:36:41Z_  
_Verifier: the agent (gsd-verifier)_
