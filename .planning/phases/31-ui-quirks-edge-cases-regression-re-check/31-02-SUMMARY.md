---
phase: 31-ui-quirks-edge-cases-regression-re-check
plan: "02"
subsystem: cli
tags: [argparse, cli-help, windows-launcher, batch-script, ux]

# Dependency graph
requires:
  - phase: 31-ui-quirks-edge-cases-regression-re-check plan 01
    provides: real-demo UI quirks verifier and D-02 launcher/help-text decision
provides:
  - Clearer argparse help/description text distinguishing `vnphish analyze` (terminal, text-only, no browser) from `vnphish demo` (browser web UI)
  - Two Windows double-click launchers (`scripts/START_DEMO_UI.bat`, `scripts/START_TEXT_ANALYZE.bat`) for non-technical committee use
  - Regression tests locking the CLI command set and help-text wording, plus static launcher safety assertions
affects: [32-fallback-recording-full-dry-rehearsal]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "argparse description/help/epilog text is the additive-clarity surface for CLI disambiguation; subcommand names, flags, and handler dispatch stay frozen."
    - "Windows .bat launchers cd /d \"%~dp0..\" to run from repo root, chcp 65001 for UTF-8 console, and invoke `python -m src.runtime.cli <cmd>` instead of assuming the `vnphish` console script is on PATH."

key-files:
  created:
    - scripts/START_DEMO_UI.bat
    - scripts/START_TEXT_ANALYZE.bat
  modified:
    - src/runtime/cli.py
    - tests/runtime/test_cli.py

key-decisions:
  - "Used TDD (RED/GREEN) for Task 1's help-text disambiguation per plan's tdd=\"true\" flag: failing help-text assertions committed first, then build_parser() updated to satisfy them."
  - "Launcher batch files intentionally never read pasted text into a %VAR%; python -m src.runtime.cli analyze reads stdin directly, avoiding cmd variable interpolation of untrusted pasted content (T-31-02-T mitigation)."
  - "Launchers do not request elevation or set permanent environment variables (T-31-02-E mitigation)."

patterns-established:
  - "Windows batch launcher template: @echo off / cd /d \"%~dp0..\" / chcp 65001 >nul 2>&1 / fixed python -m src.runtime.cli <subcommand> invocation / pause at end."

requirements-completed: [UIQ-03]

coverage:
  - id: D1
    description: "CLI help text (root, analyze, demo) clearly distinguishes terminal text-only analyze from browser-launching demo, with the exact command set unchanged"
    requirement: "UIQ-03"
    verification:
      - kind: unit
        ref: "tests/runtime/test_cli.py#test_cli_only_exposes_analyze_doctor_and_demo_commands"
        status: pass
      - kind: unit
        ref: "tests/runtime/test_cli.py#test_root_help_lists_analyze_demo_and_doctor_commands"
        status: pass
      - kind: unit
        ref: "tests/runtime/test_cli.py#test_analyze_help_states_terminal_text_only_no_browser"
        status: pass
      - kind: unit
        ref: "tests/runtime/test_cli.py#test_demo_help_states_starts_web_ui_and_opens_browser"
        status: pass
      - kind: other
        ref: "python -m src.runtime.cli --help / analyze --help / demo --help (all exit 0)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Double-click Windows launchers exist for the demo UI and terminal analyzer, run from repo root, set UTF-8 console mode, and never interpolate pasted text through cmd variables"
    requirement: "UIQ-03"
    verification:
      - kind: unit
        ref: "tests/runtime/test_cli.py#test_demo_launcher_batch_file_exists_and_runs_from_repo_root"
        status: pass
      - kind: unit
        ref: "tests/runtime/test_cli.py#test_text_analyze_launcher_batch_file_exists_and_runs_from_repo_root"
        status: pass
      - kind: unit
        ref: "tests/runtime/test_cli.py#test_launcher_batch_files_do_not_interpolate_pasted_text"
        status: pass
      - kind: other
        ref: "powershell static launcher check (cd/d, chcp 65001, no interpolation patterns, correct subcommand targets)"
        status: pass
    human_judgment: false

duration: 8min
completed: 2026-07-08
status: complete
---

# Phase 31 Plan 02: CLI Entrypoint Clarity & Windows Launchers Summary

**Added disambiguating argparse help text and two double-click `.bat` launchers so a non-technical committee member can tell `vnphish analyze` (terminal, text-only) apart from `vnphish demo` (browser web UI) without touching a shell.**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-07-08T12:53:00Z (approx, first file read)
- **Completed:** 2026-07-08T12:58:28Z
- **Tasks:** 2 completed
- **Files modified:** 4 (2 created, 2 modified)

## Accomplishments
- `src/runtime/cli.py` root/subcommand help and descriptions now explicitly state that `analyze` is terminal/text-only/no-browser and `demo` starts the browser web UI, with subcommand names, flags, defaults, and handler dispatch completely unchanged.
- New `scripts/START_DEMO_UI.bat` and `scripts/START_TEXT_ANALYZE.bat` let a non-technical presenter double-click to launch the correct mode; both run from repo root, force UTF-8 console mode, and invoke `python -m src.runtime.cli <subcommand>` rather than relying on the `vnphish` console script being on PATH.
- `tests/runtime/test_cli.py` grew from 7 to 13 tests: 3 new help-text disambiguation tests (TDD RED/GREEN) plus 3 new static launcher-safety tests (existence, repo-root/UTF-8 setup, and no pasted-text interpolation through cmd variables).

## Task Commits

Each task was committed atomically:

1. **Task 1: Lock CLI help wording before updating parser text** - TDD cycle:
   - `0ee7300` (test) - failing help-text disambiguation tests (RED)
   - `8032f7b` (feat) - `build_parser()` description/help/epilog updates satisfying the tests (GREEN)
2. **Task 2: Add double-click Windows launchers** - `67a3740` (feat) - launcher batch files plus static regression assertions

**Plan metadata:** committed as part of this summary's final commit.

_Note: Task 1 used TDD (test → feat); Task 2 was a single `type="auto"` commit that included both the launcher scripts and their guarding tests together._

## TDD Gate Compliance

Task 1 had `tdd="true"`. Gate sequence verified in git log:
1. RED gate: `0ee7300 test(31-02): add failing CLI help-text disambiguation tests` - 2 of 4 new tests failed as expected before implementation.
2. GREEN gate: `8032f7b feat(31-02): clarify analyze vs demo CLI help text (UIQ-03/D-02)` - all tests passed after `build_parser()` updates.
3. No REFACTOR commit was needed; the GREEN implementation required no follow-up cleanup.

Both gates present and in order. Compliant.

## Files Created/Modified
- `src/runtime/cli.py` - Added `description=` to the root parser and `description=`/refined `help=` text to the `analyze` and `demo` subparsers; no argument, subcommand, or handler changes.
- `tests/runtime/test_cli.py` - Added `test_root_help_lists_analyze_demo_and_doctor_commands`, `test_analyze_help_states_terminal_text_only_no_browser`, `test_demo_help_states_starts_web_ui_and_opens_browser` (Task 1); added `REPO_ROOT`/launcher path constants, `USER_TEXT_INTERPOLATION_PATTERN`, and `test_demo_launcher_batch_file_exists_and_runs_from_repo_root`, `test_text_analyze_launcher_batch_file_exists_and_runs_from_repo_root`, `test_launcher_batch_files_do_not_interpolate_pasted_text` (Task 2).
- `scripts/START_DEMO_UI.bat` - New double-click launcher: `cd /d "%~dp0.."`, `chcp 65001`, runs `python -m src.runtime.cli demo`, pauses before closing.
- `scripts/START_TEXT_ANALYZE.bat` - New double-click launcher: `cd /d "%~dp0.."`, `chcp 65001`, prints paste/Ctrl+Z instructions, runs `python -m src.runtime.cli analyze` (reads stdin directly, no `%VAR%` interpolation of pasted text), pauses before closing.

## Decisions Made
- TDD applied to Task 1 exactly as the plan's `tdd="true"` flag required: help-text assertions written and confirmed failing first, then `build_parser()` updated minimally to pass them.
- Launcher scripts avoid `set /p`, `for /f`, `%1`/`%2`/`%*`, and any `%TEXT%`/`%MESSAGE%`/`%INPUT%` style variable capture of pasted content, per the plan's tampering mitigation (T-31-02-T) — `python -m src.runtime.cli analyze` reads stdin directly instead.
- No elevation request, no registry writes, no permanent environment variable changes in either launcher, per T-31-02-E.

## Deviations from Plan

None - plan executed exactly as written. Both tasks' `<action>`/`<behavior>` requirements were implemented as specified; all listed `<verify>` commands were run and passed, including the plan's own PowerShell static-check one-liner (adapted only for the Bash-tool's shell-quoting context, not in semantics — same literal checks, same result: PASS).

## Issues Encountered
- The plan's literal PowerShell verification one-liner uses `""` inside a double-quoted `-Command` argument, which is a cmd.exe/PowerShell command-line quote-doubling convention that only applies when the whole line is passed as a single shell argument (e.g., from `cmd.exe` or a `.bat` file). Running it verbatim through the Bash tool (which parses quotes differently) initially misfired. Resolved by re-expressing the identical check with single-quoted-string semantics for the Bash invocation; the underlying literal pattern checked (`cd /d "%~dp0.."`, `chcp 65001`, absence of interpolation patterns, presence of the correct subcommand) is unchanged and confirmed PASS.

## User Setup Required

None - no external service configuration required. The two `.bat` files are ready to double-click on the presentation laptop; no installation step beyond the existing Python/repo checkout is needed.

## Next Phase Readiness
- UIQ-03 is fully satisfied: CLI help text and launchers both ship, command set (`analyze`, `demo`, `doctor`) is unchanged, and 102/102 runtime tests pass.
- Plan 31-03 (UI quirks catalog/backend-intact fixes, UIQ-04) can proceed independently; no shared files with this plan besides the frozen CLI contract.
- Phase 32 (fallback recording) can safely reference these launchers in operator-facing instructions if desired, though the locked golden-prompt demo flow itself is unaffected.

---
*Phase: 31-ui-quirks-edge-cases-regression-re-check*
*Completed: 2026-07-08*
