# Source and Evidence Provenance

The repository has two different truths that must not be collapsed. The current
active architecture is the maintainable code a reader should learn now. The
historical producer source and the sealed evidence authority are what support the
completed evaluation. Current source is not the metric-producing source.

## Authority chain

<!-- provenance-authority-identities:start -->
| Layer | Exact authority | What it establishes |
| --- | --- | --- |
| Current architecture | `architecture/module-boundaries.json` (`module-boundaries-v2`) | Active domain modules, compatibility adapters, historical modules, allowed edges, and static budgets |
| Historical producer source | `historical/phase41-source-closure/c3bbc8c8adaf7579fd2eb9c59a0081613be4b2cae05dfdb64472938c7e6d0434/` | A post-evaluation, content-addressed mirror of the 37-source producer closure plus its launcher |
| Frozen evaluation export | `data/models/phase41/verified-export/9ac54d58c273ab0a8c2f2b4b61e472a51ca94231a94b6847637ecad6ceee49f7/` | The completed 12-member evidence package and its terminal policy |
| Mandatory correction | `data/models/phase41/phase41-provenance-erratum.json` | The disclosure that corrects global prior-access wording without modifying the export |
<!-- provenance-authority-identities:end -->

The tracked archival receipt labels the mirror
`post_evaluation_archival_mirror_not_refactored_metric_producer`. That phrase is
important: the mirror preserves source identity after the event; neither the mirror
nor the refactored worktree is presented as a new producer of the frozen result.

## Historical source identity

- Source-tree SHA-256:
  `c3bbc8c8adaf7579fd2eb9c59a0081613be4b2cae05dfdb64472938c7e6d0434`.
- Archival-receipt SHA-256:
  `ca4ca1bf019b567d5bfa2380658a11245d76543b323ce5e2fcf6cfe3f525213a`.
- Execution-source-manifest SHA-256:
  `41a3a7e166dd5077b3b2c689868b862bd5665137e1824094eb5ff1cdce2b0c61`.
- Launcher SHA-256:
  `c5f15a32b2c8d8ee196e3ec484707c27c4c05e5389d958626e775e44f52d49e9`.
- The receipt records 37 source members and 38 payload members when the launcher
  is included. It also records that the then-current worktree already differed in
  the model-adaptation CLI and evaluator, which is why current source cannot be
  substituted for the closure.

The receipt records the clean-runtime origin under ProgramData. This document cites
that tracked receipt only; it does not inspect, copy, refresh, or modify the origin.

## Frozen export identity

The verified export identity is
`9ac54d58c273ab0a8c2f2b4b61e472a51ca94231a94b6847637ecad6ceee49f7`.
The two report-facing records retain these exact schema identifiers:

<!-- provenance-schema-identities:start -->
| Record | Exact schema identifier |
| --- | --- |
| `Verified evidence manifest` | `phase41-evidence-manifest-v1` |
| `Mandatory provenance erratum` | `phase41-provenance-erratum-v1` |
<!-- provenance-schema-identities:end -->

The evidence manifest reports
status `completed`, and names 12 hash-bound members. Those member hashes, names,
schemas, canonical bytes, selected model identities, and filenames are one package;
downstream code may read them but must not rewrite or reserialize them.

The manifest's terminal policy is exact:

- `rerun_permitted = false`
- `test_outcome_used_for_tuning = false`
- `unbiased_test_score_claim_after_deployment_fit = false`

This policy allows no replay, retry, tuning, repair, threshold selection, or new
unbiased score claim after an optional deployment fit.

## Mandatory erratum

The erratum uses the exact schema listed above and has tracked SHA-256
`c7be74346f0e217c382e556fbf0a730cb33be50356d4155356a5b024871a1672`.
It is an external non-sealed companion: the verified export was not modified or
resealed, and prediction or metric artifacts were not changed.

Its corrected claim is:

<!-- provenance-correction-quote:start -->
> Phase 41 contains exactly one terminal shared-cohort model-evaluation pass over the frozen Qwen QLoRA and PhoBERT models. It does not have zero prior filesystem access to the held-out file.
<!-- provenance-correction-quote:end -->

The access disclosure is narrower and more precise than a global claim. At least two
broad default test executions before the terminal model evaluation parsed, statted,
and hashed the live split files; the exact number may be higher. One focused
post-evaluation regression rerun also reread them. Those test processes displayed no
row content to a human, performed no model inference, used no external service, and
did not influence model selection, thresholds, retraining, or dataset repair. The
terminal model evaluation was not retried.

## Reporting rule

Every downstream result claim must cite the verified export and the erratum together.
The active architecture may be described from `overview.md`; quantitative or
selected-model claims remain bound to the frozen export. The provenance receipt may
explain which historical bytes produced that authority, but it supplies no new
metric and authorizes no rerun.

The architecture checks run inside one deliberately restricted Python interpreter,
not a general-purpose OS sandbox. Its append-only audit hook independently rejects
protected-path opens even when a Python wrapper's captured original is recovered.
Every reviewed native loader and process surface must be either denied before
collection or unavailable on the platform; collection refuses any other disposition.
This contract supports only the exact synthetic architecture suite and makes no
security-isolation claim for arbitrary Python or native extensions.
