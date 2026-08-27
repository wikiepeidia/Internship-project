---
schema_version: 1
open_count: 0
waived_count: 0
fixed_count: 8
total_count: 8
last_updated: 2026-08-27T03:23:27.869Z
---

# Broken Windows Ledger

> Cross-phase defect register. With `workflow.windows_enforce` enabled, `/gsd-ship` blocks while `open_count > 0`.
> Waive with `gsd-tools windows waive <id> "<reason>"` (reason required).
> Mark fixed with `gsd-tools windows fixed <id>`.

| id | phase | kind | file | line | description | status | reason | recorded_at | resolved_at |
|----|-------|------|------|------|-------------|--------|--------|-------------|-------------|
| 1 | 41.1 | deviation | scripts/archive_phase41_source_closure.py |  | Archive success output needed encoding-safe console presentation on legacy Windows code pages | fixed |  | 2026-08-27T00:45:22.877Z | 2026-08-27T00:45:52.494Z |
| 2 | 41.1 | deviation | .gitattributes |  | Historical producer closure requires text conversion disabled and Git index-blob hash verification | fixed |  | 2026-08-27T00:45:23.237Z | 2026-08-27T00:45:52.949Z |
| 3 | 41.1 | deviation | src/artifacts.py |  | Preserved historical Windows registry newline parity in the neutral writer | fixed |  | 2026-08-27T01:47:31.167Z | 2026-08-27T01:48:04.860Z |
| 4 | 41.1 | deviation | src/runtime/service.py |  | Closed remaining runtime settings and historical registry ownership leaks | fixed |  | 2026-08-27T01:47:31.573Z | 2026-08-27T01:48:05.313Z |
| 5 | 41.1 | deviation | src/modeling/evidence.py |  | Closed result, export-directory, unopened-member, and materialization provenance links after the Task 2 independent audit. | fixed |  | 2026-08-27T02:24:50.246Z | 2026-08-27T02:25:19.969Z |
| 6 | 41.1 | deviation | tests/architecture/test_modeling_evidence.py |  | Construct hash-named synthetic authorities directly to avoid OneDrive directory-rename races. | fixed |  | 2026-08-27T02:24:50.725Z | 2026-08-27T02:25:20.429Z |
| 7 | 41.1 | deviation | src/data_pipeline/workflows.py | 487 | Resolved active workflow naming contract by exposing build_training_corpus and retaining run_phase1 only at the legacy CLI seam | fixed |  | 2026-08-27T02:56:31.000Z | 2026-08-27T02:56:51.625Z |
| 8 | 41.1 | deviation | tests/architecture/test_import_boundaries.py |  | Plan 06 v2 static_policy required the prior exact-field import-boundary gate to accept the additive policy field and schema version. | fixed |  | 2026-08-27T03:22:56.445Z | 2026-08-27T03:23:27.869Z |

````json
[
  {
    "id": 1,
    "kind": "deviation",
    "phase": "41.1",
    "file": "scripts/archive_phase41_source_closure.py",
    "line": null,
    "description": "Archive success output needed encoding-safe console presentation on legacy Windows code pages",
    "status": "fixed",
    "reason": "",
    "recorded_at": "2026-08-27T00:45:22.877Z",
    "resolved_at": "2026-08-27T00:45:52.494Z"
  },
  {
    "id": 2,
    "kind": "deviation",
    "phase": "41.1",
    "file": ".gitattributes",
    "line": null,
    "description": "Historical producer closure requires text conversion disabled and Git index-blob hash verification",
    "status": "fixed",
    "reason": "",
    "recorded_at": "2026-08-27T00:45:23.237Z",
    "resolved_at": "2026-08-27T00:45:52.949Z"
  },
  {
    "id": 3,
    "kind": "deviation",
    "phase": "41.1",
    "file": "src/artifacts.py",
    "line": null,
    "description": "Preserved historical Windows registry newline parity in the neutral writer",
    "status": "fixed",
    "reason": "",
    "recorded_at": "2026-08-27T01:47:31.167Z",
    "resolved_at": "2026-08-27T01:48:04.860Z"
  },
  {
    "id": 4,
    "kind": "deviation",
    "phase": "41.1",
    "file": "src/runtime/service.py",
    "line": null,
    "description": "Closed remaining runtime settings and historical registry ownership leaks",
    "status": "fixed",
    "reason": "",
    "recorded_at": "2026-08-27T01:47:31.573Z",
    "resolved_at": "2026-08-27T01:48:05.313Z"
  },
  {
    "id": 5,
    "kind": "deviation",
    "phase": "41.1",
    "file": "src/modeling/evidence.py",
    "line": null,
    "description": "Closed result, export-directory, unopened-member, and materialization provenance links after the Task 2 independent audit.",
    "status": "fixed",
    "reason": "",
    "recorded_at": "2026-08-27T02:24:50.246Z",
    "resolved_at": "2026-08-27T02:25:19.969Z"
  },
  {
    "id": 6,
    "kind": "deviation",
    "phase": "41.1",
    "file": "tests/architecture/test_modeling_evidence.py",
    "line": null,
    "description": "Construct hash-named synthetic authorities directly to avoid OneDrive directory-rename races.",
    "status": "fixed",
    "reason": "",
    "recorded_at": "2026-08-27T02:24:50.725Z",
    "resolved_at": "2026-08-27T02:25:20.429Z"
  },
  {
    "id": 7,
    "kind": "deviation",
    "phase": "41.1",
    "file": "src/data_pipeline/workflows.py",
    "line": 487,
    "description": "Resolved active workflow naming contract by exposing build_training_corpus and retaining run_phase1 only at the legacy CLI seam",
    "status": "fixed",
    "reason": "",
    "recorded_at": "2026-08-27T02:56:31.000Z",
    "resolved_at": "2026-08-27T02:56:51.625Z"
  },
  {
    "id": 8,
    "kind": "deviation",
    "phase": "41.1",
    "file": "tests/architecture/test_import_boundaries.py",
    "line": null,
    "description": "Plan 06 v2 static_policy required the prior exact-field import-boundary gate to accept the additive policy field and schema version.",
    "status": "fixed",
    "reason": "",
    "recorded_at": "2026-08-27T03:22:56.445Z",
    "resolved_at": "2026-08-27T03:23:27.869Z"
  }
]
````
