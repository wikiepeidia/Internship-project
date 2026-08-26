---
phase: 41-one-shot-two-model-evaluation
review: 41-REVIEW.md
resolved: 2026-08-26T15:27:19Z
status: passed_with_external_erratum
sealed_manifest_sha256: 9ac54d58c273ab0a8c2f2b4b61e472a51ca94231a94b6847637ecad6ceee49f7
erratum_sha256: c7be74346f0e217c382e556fbf0a730cb33be50356d4155356a5b024871a1672
---

# Phase 41 Review Resolution

The release blockers are corrected without rerunning either model and without modifying or resealing the frozen export. The external provenance erratum is a mandatory companion for every Phase 42/43/report consumer.

| Finding | Resolution | Verification | Disposition |
|---|---|---|---|
| CR-01 | `validate_downstream_data_contract` is now metadata-only and has no split-directory parameter. Live parsing/stat/hash moved to `validate_downstream_data_contract_live`, which requires the exact `VNPHISH_ENABLE_LIVE_SPLIT_INTEGRITY_AUDIT=I_UNDERSTAND_THIS_READS_LIVE_SPLITS` opt-in. The live test is marked and excluded by default. | `test_downstream_contract_default_validation_is_metadata_only`, `test_live_downstream_validator_rejects_trap_path_before_any_io`, and the actual contract/planning metadata test: 3 passed. | Resolved in `9037404`. |
| CR-02 | Phase 41 export success and CLI errors use an encoding-aware `backslashreplace` console writer, so an unencodable Windows path cannot change a successful mutation into exit 1. | Strict CP-1252-like stdout/stderr tests verify a real temp export receipt and a safe error: included in 4 passed. | Resolved in `dde319e`. |
| WR-01 | Export copies into a uniquely named sibling stage, verifies source/copy/receipt, atomically renames the complete directory, and cleans only its validated stage on failure. An existing complete byte-identical export is accepted idempotently; partial or differing content fails closed. | Temp-only copy/idempotency and corrupt-copy cleanup tests: included in 4 passed. | Resolved in `dde319e`. |
| WR-02 | The immutable final receipt cannot be rewritten. The external erratum independently identifies the captured-helper audit and the later model-lease audit by path, schema, stage, and SHA-256, and explains that the legacy captured-helper-named member binds the lease audit. | Erratum JSON parse passed; both source audit hashes were independently recomputed before publication. | Resolved by mandatory external clarification. |

## Corrective Provenance

`data/models/phase41/phase41-provenance-erratum.json` records:

- at least two broad pre-run pytest executions that parsed, statted, and hashed the live split files;
- one post-run focused planning-label test that repeated those reads;
- no model inference, external API call, human row display, training, tuning, model selection, dataset repair, or retry caused by those test reads;
- retraction of absolute global zero-filesystem-access wording while retaining the accurate claim of one terminal two-model evaluation pass; and
- the limited meaning of the five failed launcher records: each failed before its own claim/access boundary, but those records do not audit unrelated pytest processes.

## Immutable Boundary

- Frozen evidence-manifest SHA-256: `9ac54d58c273ab0a8c2f2b4b61e472a51ca94231a94b6847637ecad6ceee49f7`.
- Frozen export Git tree object before remediation: `df5ae00a1ad5d7400c084e8a19280fb660d1fd96`.
- Frozen export exact-path diff after code/document remediation: clean.
- Model/evaluation/authentication/launcher commands invoked during remediation: none.
- Reserved split or containing directory accessed during remediation: none.

## Safe Test Record

Only focused fixture/temp tests were executed:

- downstream metadata/opt-in boundary: 3 passed;
- transactional export and legacy-console behavior: 4 passed.

The broad suite and the explicit live-data integration audit were deliberately not run.
