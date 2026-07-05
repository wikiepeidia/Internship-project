# Phase 29 ENV-01 / ENV-05 Evidence

Recorded: 2026-07-05

## ENV-01: doctor sanity re-check

Summary: PASS. `python -m src.runtime.cli doctor` exited 0 and printed `READY backend=gguf local_only=True text_only=True` with every listed check marked PASS.

Command:

```powershell
python -m src.runtime.cli doctor
```

Output:

```text
llama_context: n_ctx_seq (512) < n_ctx_train (262144) -- the full capacity of the model will not be utilized
READY backend=gguf local_only=True text_only=True
- python-version: PASS - python=3.13
- import:ftfy: PASS - Imported ftfy successfully.
- import:pydantic: PASS - Imported pydantic successfully.
- import:pydantic_settings: PASS - Imported pydantic_settings successfully.
- settings-load: PASS - Runtime settings loaded successfully.
- runtime-backend: PASS - settings.runtime_backend='gguf'
- runtime-profile: PASS - runtime_profile=gguf-laptop
- runtime-max-cues: PASS - runtime_max_cues=3
- runtime-fail-closed: PASS - runtime_fail_closed=True
- runtime-store-raw-text: PASS - runtime_store_raw_text=False
- backend-ready: PASS - backend=gguf ready=True
- release-gate-summary: PASS - latest_verdict=BLOCK run_id=phase5-recovered-balanced-val manifest=data\manifests\phase5-release-eval-phase5-recovered-balanced-val.json
```

## ENV-05: exact-pin confirmation

Summary: PASS. `pyproject.toml` now exact-pins `llama-cpp-python==0.3.23`, and the currently installed package version is already `0.3.23`. No reinstall, venv rebuild, uninstall, or force-reinstall was performed.

Pin diff:

```diff
 runtime = [
-    "llama-cpp-python>=0.3",
+    "llama-cpp-python==0.3.23",
 ]
```

Read-only installed-version confirmation:

```powershell
python -m pip show llama-cpp-python
```

Output:

```text
Name: llama_cpp_python
Version: 0.3.23
Summary: Python bindings for the llama.cpp library
Home-page: https://github.com/abetlen/llama-cpp-python
Author:
Author-email: Andrei Betlen <abetlen@gmail.com>
License: MIT
Location: C:\Users\wikiepeidia\AppData\Local\Programs\Python\Python313\Lib\site-packages
Requires: diskcache, jinja2, numpy, typing-extensions
Required-by:
```
