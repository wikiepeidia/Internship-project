# Historical tooling

This directory contains reproducibility utilities from completed experiments and
runtime verification campaigns. They are retained for auditability, but they are
not installed application entry points and are not part of the maintained runtime.

- `runtime-validation/`: browser-driven checks and latency probes from completed
  validation work.
- `training/`: one-off remote QLoRA and GGUF export workflows retained as experiment
  provenance.

Current user entry points remain in `scripts/` and `src/runtime/`.
