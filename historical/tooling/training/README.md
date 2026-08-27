# Retained training utilities

These shell scripts document a completed one-off remote training/export workflow.
They are not the maintained local training interface.

| Utility | Original purpose |
| --- | --- |
| `vastai_qlora_full.sh` | Remote QLoRA workflow with baseline and adapter evaluation |
| `vastai_gguf_export.sh` | Resume-safe adapter merge and GGUF conversion |

The maintained code-facing entry point is the `vnphish` package and the current
modeling interfaces under `src/modeling/`.
