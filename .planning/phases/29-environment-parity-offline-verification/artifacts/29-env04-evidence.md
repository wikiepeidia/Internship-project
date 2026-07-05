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
