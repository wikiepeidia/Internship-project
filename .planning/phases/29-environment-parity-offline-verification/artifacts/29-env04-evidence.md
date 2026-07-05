# Phase 29 ENV-04 Evidence

Recorded: 2026-07-05

## ENV-04: setx + registry proof

Summary: PASS. `MODEL_ARTIFACT_ROOT` and `MODEL_REGISTRY_PATH` were written as permanent Windows user-level environment variables under `HKCU\Environment`. The current shell is not expected to see `setx` updates; the registry query is the authoritative proof for Task 1.

Commands:

```powershell
setx MODEL_ARTIFACT_ROOT "D:\PROJEct\AI MODELS"
setx MODEL_REGISTRY_PATH "D:\PROJEct\AI MODELS\manifests\model-registry.json"
reg query "HKCU\Environment" /v MODEL_ARTIFACT_ROOT
reg query "HKCU\Environment" /v MODEL_REGISTRY_PATH
```

Output:

```text
SUCCESS: Specified value was saved.

SUCCESS: Specified value was saved.

HKEY_CURRENT_USER\Environment
    MODEL_ARTIFACT_ROOT    REG_SZ    D:\PROJEct\AI MODELS


HKEY_CURRENT_USER\Environment
    MODEL_REGISTRY_PATH    REG_SZ    D:\PROJEct\AI MODELS\manifests\model-registry.json
```

## ENV-04: new-terminal cross-directory confirmation

Summary: PASS. The user opened a brand-new PowerShell terminal after `setx`, confirmed both environment variables were visible, changed to `C:\`, and ran `vnphish doctor`. The doctor command reported READY from outside the repo root.

Note: The current doctor output format reports `backend-ready: PASS - backend=gguf ready=True`; it does not print the resolved model path detail that the original plan expected. The fresh-terminal env-var output below supplies the path proof, and the `C:\` doctor run supplies the runtime proof.

Fresh-terminal env-var checks:

```powershell
PS C:\Users\wikiepeidia> $env:MODEL_ARTIFACT_ROOT
D:\PROJEct\AI MODELS
PS C:\Users\wikiepeidia> $env:MODEL_REGISTRY_PATH
D:\PROJEct\AI MODELS\manifests\model-registry.json
```

Fresh-terminal cross-directory doctor check:

```powershell
PS C:\Users\wikiepeidia> cd C:\
PS C:\> vnphish doctor
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
- release-gate-summary: PASS - No saved release evaluation artifact found.
```
