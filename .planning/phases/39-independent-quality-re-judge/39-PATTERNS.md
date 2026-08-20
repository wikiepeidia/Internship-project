# Phase 39: Independent Quality Re-Judge - Pattern Map

**Mapped:** 2026-08-20
**Scope:** Remaining post-triage migration, final-snapshot judge evidence, and final human-review evidence
**Files classified:** 13 implementation/test/document targets plus generated data artifacts
**Analogs found:** 12 / 13 (the compact human-decision parser has no exact in-repo analog)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `src/data_pipeline/apply_mislabel_triage.py` | utility / migration | batch, file-I/O, transform | `apply_task_scam_risk_tier_repair.py` + `reconstruct_zalo_direct_catalog.py` + `repair_corpus_split_governance.py` | composite exact |
| `tests/data_pipeline/test_apply_mislabel_triage.py` | test | batch, file-I/O, failure injection | the three corresponding test modules above | composite exact |
| `src/data_pipeline/judge_merge.py` | utility / evidence joiner | batch, file-I/O, transform | its existing `CodexJudgeResult` and merge pipeline | exact role; new digest lane |
| `tests/data_pipeline/test_judge_merge.py` | test | batch, file-I/O | existing judge merge tests | exact |
| `src/data_pipeline/manual_review_sheet.py` | utility / review pack builder | batch, file-I/O, transform | its current deterministic sampler/renderer plus `model_adaptation/explanation_review.py` | role-match |
| `tests/data_pipeline/test_manual_review_sheet.py` | test | batch, file-I/O | existing manual sheet tests | exact |
| `.planning/codex-final-delta-judge-instructions.md` | config / operator handoff | request-response, batch | `.planning/codex-judge-instructions.md` | exact |
| `.planning/phases/39-independent-quality-re-judge/39-REPORT-NOTE.md` | documentation / evidence handoff | batch-derived | `39-RESEARCH.md` report notice + `39-01-SUMMARY.md` evidence style | role-match |
| `data/splits/{train,val,test}.jsonl` | canonical data | batch, file-I/O | candidate/promotion layout in `reconstruct_zalo_direct_catalog.py` | exact |
| `data/manifests/manifest.json` | config / immutable provenance | batch, file-I/O | `build_updated_manifest()` in `reconstruct_zalo_direct_catalog.py` | exact |
| `data/processed/phase39-mislabel-{audit,quarantine}.jsonl` | audit data | append-only batch artifact | catalog/audit payloads in `reconstruct_zalo_direct_catalog.py` | role-match |
| `data/processed/phase39-final-judge-{delta-targets,provenance}.jsonl` and final combined judge JSONL/summary | evidence data | batch, join, file-I/O | `judge_merge.py` outputs | role-match |
| `.planning/phases/39-independent-quality-re-judge/39-final-manual-review-sheet.md` plus machine summary | human-review data | batch, file-I/O | `manual_review_sheet.py` | exact role |

The old `39-manual-review-sheet.md`, `39-mislabel-triage-sheet.md`, and `MISLABEL triage.md` are immutable inputs/history. Do not overwrite them: the final sheet must be a new final-snapshot artifact.

## Pattern Assignments

### `src/data_pipeline/apply_mislabel_triage.py` (utility/migration, batch + file-I/O + transform)

**Primary analogs:**

- `src/data_pipeline/apply_task_scam_risk_tier_repair.py:32-123` for a closed Pydantic input contract, line-numbered parsing, exact coverage, and aggregated errors.
- `src/data_pipeline/generate_mislabel_triage_sheet.py:47-78` for reconstructing the ordered historical candidate set before checking live presence.
- `src/data_pipeline/repair_corpus_split_governance.py:230-450` for the global cap and deterministic whole-seed split.
- `src/data_pipeline/reconstruct_zalo_direct_catalog.py:466-668,726-847` for history-preserving manifest composition, candidate staging/reload, bundle promotion, post-write verification, and verified rollback.

**Imports pattern:** keep this a local, network-free stdlib/Pydantic pipeline. Reuse public corpus algorithms rather than reimplementing them.

```python
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from src.data_pipeline.generate_mislabel_triage_sheet import (
    partition_by_live_presence,
    select_mislabel_candidates,
)
from src.data_pipeline.repair_corpus_split_governance import (
    assign_stratified_group_split,
    enforce_seed_cap,
)
from src.data_pipeline.schemas import DatasetRecord
```

The authoritative record contract is `DatasetRecord` at `src/data_pipeline/schemas.py:82-114`; the only valid labels are the four literals at lines 90-91. Do not accept a free-form relabel value.

#### Fail-closed decision parsing

Copy the closed-schema posture from `RiskTierRepairResult` (`apply_task_scam_risk_tier_repair.py:32-45`):

```python
class RiskTierRepairResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    split: Literal["train", "val", "test"]
    row_index: int = Field(ge=0)
    seed_id: str = Field(min_length=1)
```

For the compact `MISLABEL triage.md`, add a dedicated `TriageDecision` model with `candidate_number`, `raw_decision`, `normalized_action`, optional `new_label`, `notes`, and `normalization_reason`. There is no exact parser analog, so implement one anchored regex for decision lines and one for `Note:`/`Notes:`. Require candidate numbers `1..324` exactly once each.

Only two normalization exceptions are allowed:

- candidate 103 raw `Drop` -> normalized `drop`, preserving the raw token and reason;
- candidate 320 raw `Relabel to: Beigin` -> normalized label `benign`, preserving the raw token and reason.

Every other unknown spelling, unknown label, duplicate number, omission, or extra decision must raise before any candidate file is written. Follow `load_repair_results()` (`apply_task_scam_risk_tier_repair.py:65-93`) by wrapping JSON/validation errors with the 1-based source line, and `validate_coverage()` (`:97-123`) by aggregating missing, duplicate, and unexpected items into one actionable error.

#### Identity binding: copy the selection flow, strengthen the key

Use `select_mislabel_candidates()` and `partition_by_live_presence()` (`generate_mislabel_triage_sheet.py:47-78`) to reconstruct the same ordered 324 live candidates from historical `judge-merged.jsonl`. Do **not** apply decisions by the old `split`/`row_index`: re-splitting and prior repairs made those coordinates stale.

The existing presence join uses `(seed_id, text)`; strengthen it to `(seed_id, SHA256(canonical_text))`, where canonicalization is deliberately conservative:

```python
def canonicalize_identity_text(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text[:-1] if text.endswith("\n") else text

def record_identity(record: dict[str, Any]) -> tuple[str, str]:
    payload = canonicalize_identity_text(record["text"]).encode("utf-8")
    return record["seed_id"], hashlib.sha256(payload).hexdigest()
```

Do not casefold, strip arbitrary whitespace, collapse spaces, or normalize punctuation. Require one and only one current match for each admitted/dropped/quarantined candidate. Zero or multiple matches are fatal.

#### Transform and quarantine

For admitted relabels, deep-copy the source row and mutate only `label`. Assert byte/value equality for `text`, `risk_tier`, `suspicious_spans`, `xai_explanation`, `source`, and `seed_id` before accepting the projection. This follows the preservation gate in `validate_projected_corpus()` (`reconstruct_zalo_direct_catalog.py:274-389`) and its regression tests at `test_reconstruct_zalo_direct_catalog.py:116-173`.

Each of the 324 decisions must end in exactly one disposition:

- drop (91 projected decisions),
- admitted relabel (57 projected decisions), or
- lineage quarantine (176 proposed Zalo relabels from `seed_157ce0adb043`).

Quarantine is a corpus-admission decision, not a semantic disagreement. Store the complete original row plus candidate number, raw decision, normalized decision, identity digest, disposition, and reason. The 176 rows must never enter the cap/split pool.

#### Global cap and whole-seed re-split

Call the existing functions directly:

```python
capped, cap_stats = enforce_seed_cap(admitted, cap_pct=0.08)
assignments = assign_stratified_group_split(
    capped,
    ratios=(0.8, 0.1, 0.1),
    salt="phase39-mislabel-triage-v1",
)
```

`enforce_seed_cap()` (`repair_corpus_split_governance.py:230-319`) recomputes the denominator after each trim and deterministically orders survivors. `assign_stratified_group_split()` plus `_ensure_label_support()` (`:322-450`) assigns whole seed groups only and repairs missing label support without splitting a seed. Build each split by looking up `assignments[row["seed_id"]]`; never preserve old positional assignments and never move individual variants.

Revalidate after the cap and again after reloading staged files:

- every row passes `DatasetRecord.model_validate()`;
- every non-empty suspicious span is an exact substring of text;
- no normalized exact or >=0.95 lexical duplicate;
- every seed occurs in exactly one split;
- every split has every one of the four labels;
- no seed exceeds 8% of the final global corpus;
- split ratios meet the established tolerance;
- expected locked projection is 2,103 rows (`1,665/218/220`) only if all input hashes still match research; otherwise fail closed rather than forcing those numbers.

#### Manifest construction

Copy `build_updated_manifest()` (`reconstruct_zalo_direct_catalog.py:466-535`), not a fresh manifest from scratch:

```python
updated = copy.deepcopy(existing)
updated["manifest"] = {
    "version": version,
    "build_timestamp": timestamp,
    "git_commit": commit_or_none,
    "files": split_hash_entries,
}
updated["split_class_distribution"] = final_distribution
updated["task_scam_mislabel_triage"] = audit_block
```

The appended block must bind input split/manifest hashes, decision-sheet hash, historical judge hash, parser/source hashes, raw and normalized counts, the two explicit normalization events, all 324 identities/dispositions, quarantine policy/seed, cap drops, split salt/distribution, final hashes, and honest Git dirty status. `versioning/manifest.py:13-43` provides the SHA-256/records/bytes entry shape; `schemas.py:117-137` defines it.

#### Stage, promote, verify, roll back

Use the F-01 sequence exactly:

1. Build every output in memory.
2. Write splits, manifest, audit, and quarantine to an empty candidate directory.
3. Reload and re-run all validation (`stage_candidate_bundle()`, `reconstruct_zalo_direct_catalog.py:563-668`).
4. Re-hash locked canonical inputs immediately before promotion.
5. Promote one destination/payload bundle.
6. Verify promoted bytes and semantic invariants.
7. On any write or verification exception, restore and hash-check every original destination.

The transaction core is `_replace_payload_bundle()` (`reconstruct_zalo_direct_catalog.py:766-801`):

```python
try:
    for key, destination in destinations.items():
        _write_bytes_atomically(destination, payloads[key])
    for key, destination in destinations.items():
        actual = destination.read_bytes()
        expected = payloads[key]
        if len(actual) != len(expected) or sha256(actual) != sha256(expected):
            raise MigrationError(...)
    verify_promoted()
except Exception as exc:
    rollback_errors = _restore_and_verify_destinations(destinations, original_bytes)
    ...
```

Do not copy `apply_task_scam_risk_tier_repair.py:190-201` or `_write_splits_atomically()` (`repair_corpus_split_governance.py:497-515`) as the final transaction: both use temp files, but neither rolls back a partially promoted multi-file bundle.

---

### `tests/data_pipeline/test_apply_mislabel_triage.py` (test, batch/file-I/O)

**Analogs:**

- Parser/coverage fixtures: `test_apply_task_scam_risk_tier_repair.py:66-137`.
- Preservation and full projection gates: `test_reconstruct_zalo_direct_catalog.py:96-173`.
- Staging/rollback failure injection: `test_reconstruct_zalo_direct_catalog.py:175-312`.
- Cap and split determinism: `test_repair_corpus_split_governance.py:211-378`.
- Candidate reconstruction: `test_generate_mislabel_triage_sheet.py:54-94`.

Copy the small local `_write_jsonl()`/record factory style, use `tmp_path`, and inject failures with `monkeypatch`. Required test groups:

1. Exact 324 coverage; duplicates, omissions, extras, and arbitrary spellings fail.
2. Candidates 103 and 320 normalize exactly while retaining raw values/reasons.
3. Historical candidate reconstruction yields 329 flagged / 324 live / 5 removed for the locked fixture.
4. Stale old row indices do not matter; zero-match and ambiguous identity joins fail.
5. Each admitted relabel changes only `label`; parameterize every preserved field as in `test_projected_gate_binds_every_zalo_field_to_validated_catalog` (`test_reconstruct_zalo_direct_catalog.py:152-173`).
6. All 176 dominant-seed Zalo decisions go only to quarantine; the independent Zalo relabel remains admissible.
7. Cap is global/iterative and final splits are deterministic, seed-disjoint, and four-label supported.
8. Candidate manifest hashes and disposition counts match reloaded bytes.
9. Write failure, post-promotion verification failure, and rollback failure exercise all destinations, including audit/quarantine.
10. Source inspection proves no requests/provider/API path, matching `test_reconstruction_module_has_no_external_provider_path()` (`test_reconstruct_zalo_direct_catalog.py:326-335`).

---

### `src/data_pipeline/judge_merge.py` (utility/evidence joiner, batch + file-I/O)

**Analog:** extend the current module rather than creating a parallel judge schema.

Keep `CodexJudgeResult` (`judge_merge.py:39-54`), line-numbered closed parsing (`:57-82`), source validation (`:85-109`), aggregate statistics (`:206-238`), and atomic output encoding (`:241-264`). The current `merge_judge_results()` (`:112-203`) remains correct for a fresh result set whose coordinates refer to the same snapshot.

Add a final-snapshot composition lane around it:

```python
def dataset_record_digest(row: dict[str, Any]) -> str:
    payload = DatasetRecord.model_validate(row).model_dump()
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
```

Digest all seven `DatasetRecord` fields. Index historical merged rows by digest and carry a verdict only when the digest has exactly one historical match. Rebase `split`/`row_index` to the final snapshot and put old coordinates in the provenance sidecar with `verdict_origin="carried_forward_exact_record"`. Any new/changed/ambiguous row becomes a delta target and later receives `verdict_origin="fresh_final_delta"`.

The combined final result must fail unless:

- every final `(split,row_index,seed_id,digest)` appears exactly once;
- carried and fresh sets are disjoint;
- carried judge evidence retains all five scores, pass, and reason unchanged;
- fresh results pass the existing Pydantic, coverage, coordinate, and seed checks;
- no historical coordinate is treated as a current coordinate;
- provenance counts sum to final corpus size (research projects 1,562 carried + 541 fresh = 2,103 when locked hashes match).

Write final combined JSONL, stats JSON, delta-target JSONL, and provenance JSONL atomically. If these are promoted as one evidence snapshot, use the same rollback-capable bundle helper as the corpus migration, not sequential `.replace()` calls.

**Instruction analog:** copy `.planning/codex-judge-instructions.md`'s scoring dimensions and exact output schema into `.planning/codex-final-delta-judge-instructions.md`, but point it only at the generated delta target file/current final rows. State clearly that this is an exact carry-forward plus fresh delta, not a fresh full-corpus rerun.

**Tests:** extend `tests/data_pipeline/test_judge_merge.py` following its realistic factories and end-to-end tracer (`:91-137`, `:175-251`, `:277-367`). Add tests for a one-field record change forcing fresh judgment, unique exact carry, digest ambiguity rejection, coordinate rebasing, carry/fresh overlap/gap rejection, all-seven-field hashing, provenance round-trip, and aggregate stats computed only from the final combined file.

---

### `src/data_pipeline/manual_review_sheet.py` (utility/review pack builder, batch + file-I/O)

**Primary analogs:**

- Existing deterministic sampler and Markdown renderer at `manual_review_sheet.py:37-176`.
- Fail-closed merged-row loader at `manual_review_sheet.py:179-205`.
- Typed human-review fields and deterministic ordering at `model_adaptation/explanation_review.py:103-152`.

Retain `_stable_bucket` selection and the multiline-safe blockquote renderer. Replace simple pass/fail-only sampling with deterministic allocation across these dimensions:

- judge PASS/FAIL;
- all four labels;
- `carried_forward_exact_record` / `fresh_final_delta` origin.

When a full cross-product stratum is sparse, allocate available rows then fill deterministically from underrepresented label/status/origin groups. Final output must still be exactly 100 rows when the corpus has at least 100.

Carry an old human verdict only when both are uniquely identical:

1. the seven-field record digest; and
2. a judge-evidence digest over five scores, judge pass, and judge reason.

Mark a carried decision explicitly as `human_verdict_origin=carried_forward_exact_evidence`. Leave every changed, ambiguous, blank, or contradictory old decision blank. The current old sheet has two blank decisions and 14 superseded Zalo texts, so it cannot itself close JUDGE-02.

Write a fresh final sheet and a machine-readable summary bound to the final manifest SHA-256. The summary must reject fewer/more than 100 sections, missing/dual verdicts, unknown verdict tokens, duplicate record identities, or a manifest hash mismatch.

**Tests:** extend `tests/data_pipeline/test_manual_review_sheet.py:75-228` with label/origin coverage, deterministic sparse-stratum fill, exact-evidence carry, changed-score/reason/text no-carry, blank/dual mark rejection, exactly 100 unique records, and summary-manifest binding. Preserve existing embedded-newline and malformed-input regression tests.

---

### `data/manifests/manifest.json` and generated audit artifacts (config/data, batch file-I/O)

**Analog:** `build_updated_manifest()` in `reconstruct_zalo_direct_catalog.py:466-535` plus generic hash metadata in `versioning/manifest.py:13-43`.

Preserve every existing top-level history block (`repair_stats`, `zalo_narrator_scaffold_repair`, `task_scam_risk_tier_repair`, `zalo_direct_semantic_reconstruction`) and append `task_scam_mislabel_triage`. Do not replace chronology with only the latest event. Audit/quarantine JSONL uses the same canonical compact encoder as `encode_jsonl()` (`reconstruct_zalo_direct_catalog.py:127-132`).

The final judge provenance is evidence tied to, but not part of, the training record schema. Keep it in a sidecar rather than adding judge fields to `DatasetRecord` or canonical split rows.

---

### `.planning/phases/39-independent-quality-re-judge/39-REPORT-NOTE.md` (documentation/evidence handoff)

**Analog:** the recommended notice in `39-RESEARCH.md` under “Immutable Audit and Report Provenance”; there is no code-level analog.

Generate numbers from the final manifest/judge/manual summaries, and cite their hashes/paths. Preserve these distinctions:

- 324 `task_scam` candidates received human label decisions;
- 176 semantically plausible Zalo relabels were quarantined for shared-lineage dominance, not called “wrong”;
- the corpus was re-capped and re-split by whole seed;
- final judge coverage used exact-record carry-forward plus a fresh delta unless all final rows are actually judged again;
- the old 100-row sheet is diagnostic history, while the fresh completed final sheet is report evidence;
- Phase 39 performs the actual Chapter III and Chapter V t-test removal after
  the blocking final human review, then compiles and stale-claim scans the
  report/slide/defense sources. Phase 42 may later overhaul surrounding prose.

Never state “fresh full-corpus re-judge” for a carry-forward+delta run, and never state that a human completed the final sheet until the machine summary validates 100 unambiguous human marks.

## Shared Patterns

### Validation and error handling

**Sources:** `apply_task_scam_risk_tier_repair.py:65-123`, `judge_merge.py:57-203`.

- Treat human-edited Markdown and external judge JSONL as untrusted input.
- Preserve line numbers/raw values in errors and provenance.
- Aggregate coverage errors before raising; truncate previews rather than dumping hundreds of values.
- Validate all proposed output rows before the first canonical write.

### Deterministic identity and ordering

**Sources:** `_stable_bucket` use in `repair_corpus_split_governance.py:275-280,357-398` and `manual_review_sheet.py:61-72`.

- Use SHA-256/deterministic salts, never `random`.
- Old row positions are evidence metadata, never durable identity.
- Full-record judge carry-forward hashes all seven schema fields; triage identity uses seed plus conservatively canonicalized full text.

### Transactional file writes

**Source:** `reconstruct_zalo_direct_catalog.py:538-668,726-847`.

- Temp-file replacement is necessary but insufficient for a multi-file release.
- Stage/reload first, verify locked inputs immediately before promotion, verify all promoted bytes/semantics, and restore/verify every original on failure.

### Manifest chronology

**Sources:** `reconstruct_zalo_direct_catalog.py:466-535`, `versioning/manifest.py:13-43`.

- Deep-copy the old manifest, replace only current file metadata/distribution, append a named repair block.
- Record SHA-256, record count, byte count, implementation provenance, and honest dirty state.

### Test structure

**Sources:** relevant `tests/data_pipeline/test_*.py` modules.

- Use `tmp_path` for every write.
- Use realistic seven-field records and exact operator-output schemas.
- Pair success tests with malformed, stale, duplicate, omission, ambiguity, and injected-failure tests.
- Include one locked full-scale tracer after unit fixtures; projected constants are assertions only when input hashes match.

## Patterns Not to Copy Unchanged

| Existing pattern | Why it is insufficient here | Required replacement |
|---|---|---|
| `apply_task_scam_risk_tier_repair.apply_repair()` joins by `split,row_index,seed_id` | coordinates are stale after repairs/re-split | `seed_id` + conservative full-text digest with unique-match requirement |
| `generate_mislabel_triage_sheet.partition_by_live_presence()` uses raw `(seed_id,text)` set membership | does not report ambiguity or canonical newline differences | identity index with canonical text SHA-256 and cardinality checks |
| `repair_corpus_split_governance._write_splits_atomically()` | can leave a partial multi-file release | staged rollback-capable payload bundle |
| `judge_merge.merge_judge_results()` uses current positional coverage | correct only when judge file targets that exact snapshot | full-record carry-forward plus rebased final coordinates and fresh delta |
| `manual_review_sheet.select_stratified_sample()` balances PASS/FAIL only | final evidence also needs label and verdict-origin coverage | deterministic multi-axis stratification |
| `versioning.manifest.save_manifest()` writes directly | not safe for the corpus+manifest+audit transaction | include manifest in the verified promotion bundle |

## No Exact Analog Found

| File/Capability | Role | Data Flow | Reason |
|---|---|---|---|
| Compact `MISLABEL triage.md` decision parser inside `apply_mislabel_triage.py` | utility | file-I/O, transform | No existing parser handles numbered human decisions with explicitly audited typo normalization; build it narrowly and fail closed. |

## Metadata

**Analog search scope:** `src/data_pipeline/`, `tests/data_pipeline/`, `src/model_adaptation/explanation_review.py`, `tests/model_adaptation/test_explanation_review.py`, Phase 39 artifacts, and the live manifest.

**Strong analog files read:**

- `src/data_pipeline/apply_task_scam_risk_tier_repair.py`
- `src/data_pipeline/generate_mislabel_triage_sheet.py`
- `src/data_pipeline/reconstruct_zalo_direct_catalog.py`
- `src/data_pipeline/repair_corpus_split_governance.py`
- `src/data_pipeline/judge_merge.py`
- `src/data_pipeline/manual_review_sheet.py`
- `src/data_pipeline/versioning/manifest.py`
- corresponding tests plus Phase 5's typed manual-review pack tests

**Pattern extraction date:** 2026-08-20
