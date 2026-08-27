---
schema_version: 1
open_count: 0
waived_count: 0
fixed_count: 2
total_count: 2
last_updated: 2026-08-27T00:45:52.949Z
---

# Broken Windows Ledger

> Cross-phase defect register. With `workflow.windows_enforce` enabled, `/gsd-ship` blocks while `open_count > 0`.
> Waive with `gsd-tools windows waive <id> "<reason>"` (reason required).
> Mark fixed with `gsd-tools windows fixed <id>`.

| id | phase | kind | file | line | description | status | reason | recorded_at | resolved_at |
|----|-------|------|------|------|-------------|--------|--------|-------------|-------------|
| 1 | 41.1 | deviation | scripts/archive_phase41_source_closure.py |  | Archive success output needed encoding-safe console presentation on legacy Windows code pages | fixed |  | 2026-08-27T00:45:22.877Z | 2026-08-27T00:45:52.494Z |
| 2 | 41.1 | deviation | .gitattributes |  | Historical producer closure requires text conversion disabled and Git index-blob hash verification | fixed |  | 2026-08-27T00:45:23.237Z | 2026-08-27T00:45:52.949Z |

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
  }
]
````
