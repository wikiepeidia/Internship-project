# Command-Line Contracts

The installed console entry is `vnphish = src.runtime.cli:main`. Its three commands
are the public application. The 23 commands under
`python -m src.model_adaptation.cli` remain callable because evidence, launchers,
tests, and historical scripts name them, but their implementations are selected
through a fixed lazy router.

Compatibility command names are retained for evidence and scripts; they are not the forward domain model.

The table is mechanically compared with the two frozen parser fixtures and the
literal router. “Fixture return” describes the synthetic handler-double result in
the contract fixture, not a real model, server, training, or evaluation run.

<!-- cli-contracts:start -->
| Command | Group | Parser fact | Direct or lazy route | Exit/output contract |
| --- | --- | --- | --- | --- |
| `analyze` | `installed` | `flags: --text, --channel` | `src.runtime.cli.handle_analyze` | `fixture return 0; stdout and stderr preserved` |
| `doctor` | `installed` | `flags: none` | `src.runtime.cli.handle_doctor` | `fixture return 1; stdout and stderr preserved` |
| `demo` | `installed` | `flags: --host, --port, --no-browser` | `src.runtime.cli.handle_demo` | `fixture return 2; stdout and stderr preserved` |
| `pilot` | `adaptation` | `frozen argparse fixture` | `src.model_adaptation.commands.adaptation:handle_pilot` | `handler return preserved; stdout and stderr preserved; caught RuntimeError/ValueError/FileNotFoundError -> stderr and return 1` |
| `train` | `adaptation` | `frozen argparse fixture` | `src.model_adaptation.commands.adaptation:handle_train` | `handler return preserved; stdout and stderr preserved; caught RuntimeError/ValueError/FileNotFoundError -> stderr and return 1` |
| `convert` | `adaptation` | `frozen argparse fixture` | `src.model_adaptation.commands.adaptation:handle_convert` | `handler return preserved; stdout and stderr preserved; caught RuntimeError/ValueError/FileNotFoundError -> stderr and return 1` |
| `doctor` | `adaptation` | `required --adaptation-mode (preserved compatibility quirk)` | `src.model_adaptation.commands.adaptation:handle_doctor` | `handler return preserved; stdout and stderr preserved; caught RuntimeError/ValueError/FileNotFoundError -> stderr and return 1` |
| `phase40-preflight` | `phase40 compatibility` | `frozen argparse fixture` | `src.model_adaptation.commands.legacy_phase40:handle_phase40_preflight` | `handler return preserved; stdout and stderr preserved; caught RuntimeError/ValueError/FileNotFoundError -> stderr and return 1` |
| `phase40-build-source-bundle` | `phase40 compatibility` | `frozen argparse fixture` | `src.model_adaptation.commands.legacy_phase40:handle_phase40_build_source_bundle` | `handler return preserved; stdout and stderr preserved; caught RuntimeError/ValueError/FileNotFoundError -> stderr and return 1` |
| `phase40-build-input-bundle` | `phase40 compatibility` | `frozen argparse fixture` | `src.model_adaptation.commands.legacy_phase40:handle_phase40_build_input_bundle` | `handler return preserved; stdout and stderr preserved; caught RuntimeError/ValueError/FileNotFoundError -> stderr and return 1` |
| `phase40-verify-input-bundle` | `phase40 compatibility` | `frozen argparse fixture` | `src.model_adaptation.commands.legacy_phase40:handle_phase40_verify_input_bundle` | `handler return preserved; stdout and stderr preserved; caught RuntimeError/ValueError/FileNotFoundError -> stderr and return 1` |
| `phase40-verify-run-request` | `phase40 compatibility` | `frozen argparse fixture` | `src.model_adaptation.commands.legacy_phase40:handle_phase40_verify_run_request` | `handler return preserved; stdout and stderr preserved; caught RuntimeError/ValueError/FileNotFoundError -> stderr and return 1` |
| `phase40-verify-run-evidence` | `phase40 compatibility` | `frozen argparse fixture` | `src.model_adaptation.commands.legacy_phase40:handle_phase40_verify_run_evidence` | `handler return preserved; stdout and stderr preserved; caught RuntimeError/ValueError/FileNotFoundError -> stderr and return 1` |
| `phase40-render-graphs` | `phase40 compatibility` | `frozen argparse fixture` | `src.model_adaptation.commands.legacy_phase40:handle_phase40_render_graphs` | `handler return preserved; stdout and stderr preserved; caught RuntimeError/ValueError/FileNotFoundError -> stderr and return 1` |
| `phase40-validate-notebooks` | `phase40 compatibility` | `frozen argparse fixture` | `src.model_adaptation.commands.legacy_phase40:handle_phase40_validate_notebooks` | `handler return preserved; stdout and stderr preserved; caught RuntimeError/ValueError/FileNotFoundError -> stderr and return 1` |
| `phase40-finalize-comparison` | `phase40 compatibility` | `frozen argparse fixture` | `src.model_adaptation.commands.legacy_phase40:handle_phase40_finalize_comparison` | `handler return preserved; stdout and stderr preserved; caught RuntimeError/ValueError/FileNotFoundError -> stderr and return 1` |
| `phase40-freeze-scope-amendment` | `phase40 compatibility` | `frozen argparse fixture` | `src.model_adaptation.commands.legacy_phase40:handle_phase40_freeze_scope_amendment` | `handler return preserved; stdout and stderr preserved; caught RuntimeError/ValueError/FileNotFoundError -> stderr and return 1` |
| `phase40-verify-review-queue` | `phase40 compatibility` | `frozen argparse fixture` | `src.model_adaptation.commands.legacy_phase40:handle_phase40_verify_review_queue` | `handler return preserved; stdout and stderr preserved; caught RuntimeError/ValueError/FileNotFoundError -> stderr and return 1` |
| `phase40-finalize-human-review` | `phase40 compatibility` | `frozen argparse fixture` | `src.model_adaptation.commands.legacy_phase40:handle_phase40_finalize_human_review` | `handler return preserved; stdout and stderr preserved; caught RuntimeError/ValueError/FileNotFoundError -> stderr and return 1` |
| `phase41-prepare-evaluation` | `phase41 compatibility` | `frozen argparse fixture` | `src.model_adaptation.commands.legacy_phase41:handle_phase41_prepare_evaluation` | `handler return preserved; stdout and stderr preserved; caught RuntimeError/ValueError/FileNotFoundError -> stderr and return 1` |
| `phase41-verify-preauthorization` | `phase41 compatibility` | `frozen argparse fixture` | `src.model_adaptation.commands.legacy_phase41:handle_phase41_verify_preauthorization` | `handler return preserved; stdout and stderr preserved; caught RuntimeError/ValueError/FileNotFoundError -> stderr and return 1` |
| `phase41-authorize-evaluation` | `phase41 compatibility` | `frozen argparse fixture` | `src.model_adaptation.commands.legacy_phase41:handle_phase41_authorize_evaluation` | `handler return preserved; stdout and stderr preserved; caught RuntimeError/ValueError/FileNotFoundError -> stderr and return 1` |
| `phase41-run-once` | `phase41 compatibility` | `frozen argparse fixture` | `src.model_adaptation.commands.legacy_phase41:handle_phase41_run_once` | `handler return preserved; stdout and stderr preserved; caught RuntimeError/ValueError/FileNotFoundError -> stderr and return 1` |
| `phase41-freeze-deployment-fit-disposition` | `phase41 compatibility` | `frozen argparse fixture` | `src.model_adaptation.commands.legacy_phase41:handle_phase41_freeze_deployment_fit_disposition` | `handler return preserved; stdout and stderr preserved; caught RuntimeError/ValueError/FileNotFoundError -> stderr and return 1` |
| `phase41-export-evidence` | `phase41 compatibility` | `frozen argparse fixture` | `src.model_adaptation.commands.legacy_phase41:handle_phase41_export_evidence` | `handler return preserved; stdout and stderr preserved; caught RuntimeError/ValueError/FileNotFoundError -> stderr and return 1` |
| `phase41-verify-evidence` | `phase41 compatibility` | `frozen argparse fixture` | `src.model_adaptation.commands.legacy_phase41:handle_phase41_verify_evidence` | `handler return preserved; stdout and stderr preserved; caught RuntimeError/ValueError/FileNotFoundError -> stderr and return 1` |
<!-- cli-contracts:end -->

## Installed application behavior

- `analyze` accepts `--text` and `--channel`; without explicit text, the runtime
  keeps its stdin-first behavior.
- `doctor` has no command-specific flags in the installed CLI.
- `demo` accepts `--host`, `--port`, and `--no-browser`.
- The fixture proves handler selection and byte-preserved stdout/stderr plumbing.
  Real exit meanings remain owned by the handlers and are not generalized from the
  synthetic fixture values above.

## Compatibility shell behavior

- The model-adaptation parser retains exactly four adaptation commands, twelve
  training/evidence compatibility commands, and seven held-out-evaluation
  compatibility commands.
- Parser construction imports the thin command families; the literal router imports
  only the selected implementation route after parsing.
- Raw argv is retained for historical commands that need it.
- The legacy model `doctor` still requires `--adaptation-mode` with `lora` or
  `qlora`. This is a preserved parser quirk, not a recommendation for a new API.
- `RuntimeError`, `ValueError`, and `FileNotFoundError` are printed once to stderr
  through the console-safe boundary and return 1. Other exception types propagate.
- No command in this document was launched to write the document; the frozen
  fixtures and static literal route are the authorities.
