# 03-05 Summary

- Replaced the non-dry-run GGUF stub with a real conversion path in `src/model_adaptation/convert.py`, including converter-script dispatch, post-write registry updates, and a quantizer-aware split between direct llama.cpp outtypes and profiles that need `llama-quantize`.
- Added the operator-facing `convert` command in `src/model_adaptation/cli.py`, keeping alias resolution for `baseline-winner` and `runner-up` and preserving `--dry-run` as the safe preflight path.
- Reworked `src/runtime/analyzers/gguf.py` so doctor and analyze now load the registered GGUF artifact instead of stopping at placeholder metadata, while the touched conversion and GGUF runtime tests were updated to the locked 4B pair.
- Verified the unit and integration slices with `pytest` and produced real D-drive GGUF artifacts for both `qwen3-4b-instruct-2507` and `qwen3.5-4b`; the baseline `gguf-laptop` profile also passed real doctor plus live analyze smoke.
