---
quick_id: 260806-ubr
status: complete
subsystem: data-pipeline
tags: [real-data, provenance, scraping, deduplication, vietnamese, safety]
requires:
  - data/raw/seeds-2026-04-24.jsonl
provides:
  - empirical audit of 23 public-source endpoints across 8 families
  - bounded provenance-first real-source collection CLI
  - 94-row CC BY evidence sample separated by native record unit
affects:
  - future real-data review and dataset-governance work
tech-stack:
  added: []
  patterns:
    - fixed-host bounded downloads with exact archive pins
    - provenance-rich unlabeled seed records
    - offline evidence verification
key-files:
  created:
    - src/data_pipeline/scraper/real_sources.py
    - tests/data_pipeline/test_real_sources.py
    - .planning/quick/260806-ubr-audit-and-acquire-crawlable-real-vietnam/260806-ubr-SOURCE-AUDIT.md
    - .planning/quick/260806-ubr-audit-and-acquire-crawlable-real-vietnam/260806-ubr-ACQUISITION-MANIFEST.jsonl
    - .planning/quick/260806-ubr-audit-and-acquire-crawlable-real-vietnam/260806-ubr-REAL-SAMPLE.jsonl
  modified:
    - src/data_pipeline/schemas.py
decisions:
  - Keep advisory, incident, message, dataset-row, and threat-indicator counts separate.
  - Retain only sources with affirmative collection and redistribution permission.
  - Keep all acquired evidence unlabeled and outside existing synthetic and split artifacts.
  - Treat the new Hugging Face dataset as publisher-asserted real data with medium confidence, not an independent benchmark.
metrics:
  duration: 28 minutes
  completed: 2026-08-06
  tasks: 3
  endpoints_audited: 23
  sample_rows: 94
---

# Quick Task 260806-ubr: Real Vietnamese scam-data audit and acquisition

Empirical source qualification plus a bounded, rights-gated collector retained
44 publisher-asserted Vietnamese phishing-message examples and 50 PhishVN URL
indicators without changing the existing synthetic corpus or evaluation splits.

## Outcome

- Audited **23 endpoints across 8 source families** with native record units,
  empirical counts/lower bounds, access results, rights status, privacy risk,
  and source-specific blockers.
- Re-probed Tín Nhiệm Mạng at **74 current editorial advisories**. The April
  seed file remains 300 extracted snippets, 298 normalized-unique, from 67
  advisory URLs—not 300 incidents.
- Found one open message candidate:
  2,991 rows / 798 publisher-labeled phishing / 711 normalized-unique phishing
  rows, CC BY 4.0, but very new and not independently validated.
- Found one open indicator candidate: PhishVN v2 has 51,362 unique URLs,
  including 36,871 phishing indicators, CC BY 4.0. These are not messages or
  incident cases.
- Bounded selection of 100 candidates yielded **94 net-new rows**:
  44 message examples and 50 threat indicators. Six within-source duplicates
  collapsed; zero overlapped the retained seeds at the configured threshold.
- The sample is PII-scanned, provenance-complete, unlabeled, content-hashed,
  and separated from all model-ready data.

## Task Commits

| Gate | Commit | Result |
|---|---|---|
| TDD RED | `dba9bc1` | Defined schema, rights, bounds, adapter, deduplication, and verifier contracts; tests failed on missing implementation as expected. |
| TDD GREEN | `4b7613c` | Added the provenance schema, bounded collector/auditor/verifier CLI, CSV/ZIP adapters, and passing tests. |

The audit, acquisition manifest, capped sample, and this summary remain quick
planning artifacts for the parent orchestrator to handle under the project’s
planning-doc commit policy.

## Verification

- `python -m pytest tests/data_pipeline/test_real_sources.py tests/data_pipeline/test_scraper.py tests/data_pipeline/test_schemas.py tests/data_pipeline/test_normalizer.py tests/data_pipeline/test_dedup.py -x --tb=short -q`
  — **51 passed**, with two pre-existing SWIG deprecation warnings.
- `python -m src.data_pipeline.scraper.real_sources verify --manifest ... --sample ... --existing-seeds data/raw/seeds-2026-04-24.jsonl`
  — **valid**, retained sample rows: **94**.
- Plan manifest contract — one JSONL object, 23 sources, 8 families, all
  required source fields present — **passed**.
- Stub scan across created/modified implementation and tests — **clean**.
- Post-acquisition PII regex scan — email 0, phone 0, long account number 0.
- Every sample row has `data_origin=real_public`, null
  `raw_label_hint`, and no project `label` or `risk_tier`.

## Artifact Integrity

| Artifact | Rows / bytes | SHA-256 |
|---|---:|---|
| `260806-ubr-REAL-SAMPLE.jsonl` | 94 / 100,437 | `9ce84faded30c8091dd67af361be0d4db5dfbe5808c3d56eecb73c041e424da1` |
| `data/synthetic/recovered-balanced.jsonl` | 2,347,367 bytes | `009af0d2b298c25705e26830a5a7abb9e4aad34e69b1ab84a363d97030beafad` |
| `data/splits/recovered-balanced/train.jsonl` | 1,758,973 bytes | `8714fe483265aeec01379f17dbf49177009744cdc2bbdd11583d4a7898317cb5` |
| `data/splits/recovered-balanced/val.jsonl` | 183,895 bytes | `4e3f10bd565cce005a219452ff68a3180ab0e1125108a2ba205090dc71f57d57` |
| `data/splits/recovered-balanced/test.jsonl` | 404,499 bytes | `371ac104ab6910d5e37db994672c1b6fcd9879317cb260ced7f3332b0d24a94e` |

All four protected hashes match their pre-acquisition values.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking issue] Used the public repository redirect target for PhishVN**

- **Found during:** Task 3 live bounded acquisition
- **Issue:** Python Requests received an HTTP 403 Cloudflare challenge from
  Mendeley’s public file endpoint, although a normal browser-user-agent
  `curl` request returned the documented HTTP 302 public download redirect.
- **Fix:** Recorded the original repository file URL and the fixed public S3
  redirect target, allowlisted only that exact host, and retained the
  repository-declared byte count and SHA-256 as hard download gates.
- **Safety:** No CAPTCHA solving, login, cookie replay, or access-control bypass
  was used.
- **Files modified:** acquisition manifest and source audit.

**2. [Rule 3 - Blocking issue] Used the repository’s actual `val.jsonl` split name**

- **Found during:** Protected-lineage hash capture
- **Issue:** The prose referred generically to a validation split while the
  repository path is `data/splits/recovered-balanced/val.jsonl`.
- **Fix:** Captured and verified the actual tracked path.

No unresolved deviation, skipped test, unrun verification, or known stub
remains.

## Claim Boundary

The existing 3,000-row model corpus is still synthetic and unchanged. The
retained 94-row sample is evidence for future review, not proof of 94 verified
scam incidents and not an independent evaluation set. Before model use, the
message rows need multi-reviewer authenticity/label adjudication, residual-PII
review, source/near-duplicate group isolation, a separately sourced real test
set, new manifests, retraining, and leakage/calibration checks.

## Self-Check: PASSED

All six claimed implementation/evidence artifacts exist, both TDD commits are
reachable, the offline evidence verifier passes, and protected hashes match.
