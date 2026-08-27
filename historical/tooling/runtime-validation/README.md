# Retained runtime-validation utilities

These scripts reproduce completed browser and latency checks. They are historical
tools, not normal test-suite or application entry points.

| Utility | Original purpose |
| --- | --- |
| `measure_cold_latency.py` | Controlled local-demo cold-start latency probe |
| `verify_golden_prompts.py` | Repeated golden-message browser verification |
| `verify_phase32_fresh_process.py` | Fresh-process launcher rehearsal |
| `verify_ui_quirks.py` | Browser edge-case and double-submit verification |

Run them from the repository root so their retained relative artifact paths resolve.
