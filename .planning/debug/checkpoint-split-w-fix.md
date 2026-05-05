---
status: resolved
trigger: "cli.py _save_validated_records opens in 'w' mode - single error mid-loop truncates file with no atomic safety. Plus single .checkpoint.jsonl gets overwritten destroying all prior progress. Need numbered checkpoint files (001, 002...) and salvage of 290-line generated.jsonl + 480-line generated-partial.jsonl before any new write."
created: 2026-05-05
updated: 2026-05-05
---

# Checkpoint Split W Fix

## Symptoms

- **Expected:** Validated records written safely; checkpoint history preserved across runs; both partial files salvageable as starting state
- **Actual:** `validated_path.open("w", ...)` truncates destination before writing — a mid-loop ValidationError leaves a partial/empty file; single `.checkpoint.jsonl` replaced by every new run erasing prior progress
- **Error messages:** None yet (risk identified before hitting it again)
- **Timeline:** Identified after losing ~1000 checkpoint entries to a fresh overwrite run overnight
- **Reproduction:** Run `--generate-only --resume` after a prior run has finished — the resume rebuild path deletes `generated.jsonl` and rewrites checkpoint from scratch if the file timestamps do not match

## Current Focus

hypothesis: "Three separate bugs: (1) non-atomic validated.jsonl write in _save_validated_records, (2) single .checkpoint.jsonl has no history so any fresh run erases all prior progress, (3) no salvage path merges generated-partial.jsonl into the resumable state"
test: "Inspect_save_validated_records, generator checkpoint write, and current artifact contents"
expecting: "Fix (1) with atomic tmp+rename write, fix (2) with rolling numbered checkpoint files checkpoint-001.jsonl etc., fix (3) by deduplicating and merging partial into generated.jsonl before resuming"
next_action: "Read generator.py checkpoint write logic, then apply all three fixes and verify salvage result"
reasoning_checkpoint: ""
tdd_checkpoint: ""

## Evidence

- timestamp: 2026-05-05T02:00Z
  observation: ".checkpoint.jsonl had 44 entries (290 records) at investigation start; generated-partial.jsonl has 480 records from prior non-generate-only run; these are independent non-overlapping artifacts"
  significance: "480 partial + 290 generated = up to 770 unique records potentially salvageable before any new generation starts"

- timestamp: 2026-05-05T02:06Z
  observation: "Generated.jsonl and .checkpoint.jsonl were rewritten together at 09:05 local time this morning while generated-partial.jsonl was unchanged from yesterday evening"
  significance: "Confirms a fresh non-resume run replaced the larger checkpoint state"

- timestamp: 2026-05-05T09:XX
  observation: "_save_validated_records opens with mode 'w' — Python truncates the file immediately on open, before any record is written"
  significance: "Any ValidationError inside the loop leaves validated.jsonl empty or partial; unrecoverable without re-judging"

## Eliminated

## Resolution

root_cause: "Three independent bugs: (1)_save_validated_records used open('w') which truncates before writing — a ValidationError mid-loop leaves the file empty; (2) _save_batch_checkpoint appended to a single .checkpoint.jsonl which any fresh run would delete, losing all prior checkpoint history; (3) no merge path existed for the 480-record generated-partial.jsonl stranded from a prior non-generate-only run."
fix: "BUG1: write to validated_path.with_suffix('.tmp') + os.replace() (same for quality-stats.json). BUG2: numbered checkpoint scheme — each batch completion writes checkpoint-NNN+1.jsonl containing ALL cumulative entries, keeps last 5, resume loads from highest-numbered file; checkpoint_path arg in generate_dataset/run_phase1 is now the directory not a file. BUG3: salvage_partial_records() added to cli.py, exposed as --salvage-partial flag; deduplicates by text field, writes merged result atomically, leaves generated-partial.jsonl intact. EXTRA: COMPLEX_BATCH_SIZE 5→3, BULK_BATCH_SIZE 10→5."
verification: "92 tests pass (pytest tests/data_pipeline/ -x -q). Salvage merged 908 unique records from 430+480 source records (2 duplicates dropped). generated-partial.jsonl intact (480 lines). No data files deleted."
files_changed:

- src/data_pipeline/cli.py
- src/data_pipeline/generation/generator.py
- tests/data_pipeline/test_generation.py
- tests/data_pipeline/test_phase1_cli.py

## Recovery Addendum

- timestamp: 2026-05-05T11:45Z
  observation: "OneDrive recovery surfaced older generated and checkpoint snapshots. Offline merge across recovered JSONL artifacts produced 3,074 exact-unique DatasetRecord rows in data/synthetic/recovered-merged.jsonl. Offline balancing produced 956 records in data/synthetic/recovered-balanced.jsonl, capped at 239 per class because benign remains the limiting class."
  significance: "Phase 1 generation work now has enough recovered volume to satisfy the 2,000-3,000 target band at merged-corpus level, but final acceptance is blocked on judging and curation rather than more raw generation."

- timestamp: 2026-05-05T11:45Z
  observation: "Recovered checkpoint files are still useful as salvage sources, but they should no longer be treated as authoritative resume state because they are overlapping historical snapshots and the project now has explicit recovered-merged/recovered-balanced outputs."
  significance: "Resume logic should use fresh generation state only if new generation is started; current Phase 1 tracking should point to judging the recovered corpus instead of continuing from old checkpoints."
