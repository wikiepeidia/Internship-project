# Script entry points

Only five tools intentionally remain at the repository's operational surface.

| Path | Status | Purpose |
| --- | --- | --- |
| `START_DEMO_UI.bat` | Active | Start the local browser demo |
| `START_TEXT_ANALYZE.bat` | Active | Start the terminal text analyzer |
| `archive_phase41_source_closure.py` | Compatibility | Provenance archive/verify facade |
| `phase40_comparison_launcher.ps1` | Frozen history | Path-bound comparison evidence launcher |
| `phase41_one_shot_launcher.ps1` | Frozen history | Path-bound terminal evaluation launcher |

The two frozen launchers remain here because their exact paths participate in tested
evidence contracts. Standalone historical probes and remote-training scripts live in
`historical/tooling/` and are not runtime entry points.
