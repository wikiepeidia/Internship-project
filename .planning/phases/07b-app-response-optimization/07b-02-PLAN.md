---
phase: 07b-app-response-optimization
plan: 02
type: execute
wave: 2
depends_on:
  - 07b-01-PLAN.md
files_modified:
  - src/runtime/analyzers/gguf.py
autonomous: false
requirements:
  - UI-02

must_haves:
  truths:
    - "If CUDA wheel installs successfully, llama_supports_gpu_offload() returns True and n_gpu_layers=-1 is set in _load_runtime()"
    - "If CUDA wheel fails, the app continues to work on CPU with the prompt-stripped path from Plan 01 (no regression)"
    - "After any wheel change, pytest tests/runtime/test_gguf_backend.py passes"
  artifacts:
    - path: "src/runtime/analyzers/gguf.py"
      provides: "n_gpu_layers=-1 if CUDA wheel verified, otherwise n_gpu_layers=0 unchanged"
      contains: "n_gpu_layers"
  key_links:
    - from: "src/runtime/analyzers/gguf.py"
      to: "llama_cpp.Llama"
      via: "_load_runtime n_gpu_layers kwarg"
      pattern: "n_gpu_layers"
---

<objective>
Attempt to install a CUDA-enabled llama-cpp-python wheel for the RTX 5050 Laptop GPU (Blackwell, sm_120). If the wheel works, enable full GPU offload in _load_runtime() so warm latency drops from ~13s to ~3-5s. If the wheel fails for any reason, the system must continue working on CPU using the prompt-stripped path from Plan 01.

Purpose: The prompt-stripping fix (Plan 01) brings warm latency from ~30-44s to ~13s. Adding GPU offload brings it under 5s — the difference between "tolerable" and "fast" during live judging.
Output: Modified gguf.py with n_gpu_layers=-1 if GPU confirmed working; unchanged n_gpu_layers=0 if GPU attempt fails.
</objective>

<execution_context>
@C:/Users/wikiepeidia/OneDrive - caugiay.edu.vn/bài tập/usth/GEN14/INTERNSHIP/Internship-project/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/wikiepeidia/OneDrive - caugiay.edu.vn/bài tập/usth/GEN14/INTERNSHIP/Internship-project/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/phases/07b-app-response-optimization/07b-RESEARCH.md
@.planning/phases/07b-app-response-optimization/07b-01-SUMMARY.md

<interfaces>
<!-- Current state after Plan 01 completes. Executor reads gguf.py before touching it. -->

From src/runtime/analyzers/gguf.py (_load_runtime after Plan 01):
```python
GGUF_CONTEXT_WINDOW = 512
GGUF_COMPLETION_MAX_TOKENS = 250

def _load_runtime(self, artifact_path: Path) -> Any:
    if self._cached_runtime is not None and self._cached_artifact_path == artifact_path:
        return self._cached_runtime
    llama_cpp = importlib.import_module("llama_cpp")
    runtime = llama_cpp.Llama(
        model_path=str(artifact_path),
        n_ctx=GGUF_CONTEXT_WINDOW,
        n_gpu_layers=0,      # <- change to -1 if GPU wheel confirmed
        verbose=False,
    )
    self._cached_runtime = runtime
    self._cached_artifact_path = artifact_path
    return runtime
```

GPU verification command:
```
python -c "import llama_cpp; print('GPU offload supported:', llama_cpp.llama_supports_gpu_offload())"
```
Expected output if CUDA wheel works: `GPU offload supported: True`
Expected output if CPU-only: `GPU offload supported: False`
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Attempt CUDA wheel installation and verify GPU offload support</name>
  <files>src/runtime/analyzers/gguf.py</files>
  <read_first>
    - src/runtime/analyzers/gguf.py — confirm _load_runtime current n_gpu_layers value before attempting any change
  </read_first>
  <action>
**IMPORTANT: This task has two branches. Follow the branch that matches the outcome of the wheel installation attempt.**

**Step 1 — Attempt Option A: Community Blackwell wheel**

Download and install the community wheel from:
  https://huggingface.co/marcorez8/llama-cpp-python-windows-blackwell-cuda

Look for a file matching: `llama_cpp_python-0.3.x-cp313-cp313-win_amd64.whl`

If a matching file exists for Python 3.13 (cp313) on win_amd64, attempt install:
```
pip install <downloaded_wheel_file>
```

Then verify:
```
python -c "import llama_cpp; print('GPU offload supported:', llama_cpp.llama_supports_gpu_offload())"
```

**If output is `GPU offload supported: True` — BRANCH A (GPU confirmed):**

Update _load_runtime in src/runtime/analyzers/gguf.py to enable full GPU offload:

```python
def _load_runtime(self, artifact_path: Path) -> Any:
    if self._cached_runtime is not None and self._cached_artifact_path == artifact_path:
        return self._cached_runtime
    llama_cpp = importlib.import_module("llama_cpp")
    runtime = llama_cpp.Llama(
        model_path=str(artifact_path),
        n_ctx=GGUF_CONTEXT_WINDOW,
        n_gpu_layers=-1,
        n_threads=10,
        n_threads_batch=16,
        verbose=False,
    )
    self._cached_runtime = runtime
    self._cached_artifact_path = artifact_path
    return runtime
```

Note: n_gpu_layers=-1 means full offload of all model layers to VRAM. The q8_0 model (4.28 GB) fits in the RTX 5050's 8 GB VRAM. n_threads and n_threads_batch are kept for CPU-side tokenization/batching.

Run: `pytest tests/runtime/test_gguf_backend.py -x -q`
The test `test_gguf_load_runtime_uses_larger_context_window` checks captured["n_gpu_layers"]. This assertion currently expects 0. Update it:

In tests/runtime/test_gguf_backend.py, find:
```python
assert captured["n_gpu_layers"] == 0
```
Change to:
```python
assert captured["n_gpu_layers"] == -1
```

Proceed to the human verification checkpoint.

**If output is still `GPU offload supported: False` — attempt Option B: compile from source:**

```
set CMAKE_ARGS="-DGGML_CUDA=on -DCMAKE_CUDA_ARCHITECTURES=120"
pip install llama-cpp-python==0.3.23 --no-cache-dir --force-reinstall --upgrade
```

Then verify again:
```
python -c "import llama_cpp; print('GPU offload supported:', llama_cpp.llama_supports_gpu_offload())"
```

If still False after source compile: **BRANCH B (GPU unavailable — CPU fallback).**

**BRANCH B — GPU not available:** Do NOT change n_gpu_layers in gguf.py. Leave it at 0. Document the outcome in the plan summary. The CPU-only path with prompt stripping from Plan 01 is the shipped configuration. Do not fail the plan — this is the documented fallback.
  </action>
  <verify>
    <automated>pytest tests/runtime/test_gguf_backend.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - BRANCH A (GPU confirmed): llama_supports_gpu_offload() returns True; n_gpu_layers=-1 in gguf.py _load_runtime; test_gguf_backend.py assertion updated to expect -1; pytest tests/runtime/test_gguf_backend.py passes
    - BRANCH B (CPU fallback): n_gpu_layers remains 0 in gguf.py; no code changes made; pytest tests/runtime/test_gguf_backend.py passes; summary records that GPU wheel was attempted but not compatible with Python 3.13 / sm_120
    - In both branches: pytest tests/runtime/ -x -q exits 0
  </acceptance_criteria>
  <done>CUDA wheel attempt completed. Either GPU offload is enabled and verified, or CPU-fallback is confirmed clean with no regression.</done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <what-built>
    Task 1 either: (A) installed a CUDA wheel and enabled n_gpu_layers=-1 in gguf.py, or (B) confirmed the GPU wheel is incompatible and left the CPU path unchanged.
  </what-built>
  <how-to-verify>
    **If BRANCH A (GPU wheel installed):**

    1. Start the demo server: `python -m src.runtime.cli demo --no-browser`
    2. Watch terminal output — you should see "Warming up local model..." followed by llama.cpp output that includes GPU-related lines like "llm_load_tensors: offloaded 28/28 layers to GPU"
    3. In a separate terminal, send a test request:
       ```
       curl -X POST http://127.0.0.1:8765/api/analyze -H "Content-Type: application/json" -d "{\"text\": \"VPBank yeu cau xac minh OTP de mo khoa tai khoan. Truy cap https://vpbank.example ngay.\", \"channel\": \"sms\"}"
       ```
    4. Measure time from sending to receiving response. Target: under 8 seconds (ideally 3-5s).
    5. Verify response JSON contains risk_tier, threat_labels, top_cues, recommendations fields.
    6. Stop the server with Ctrl+C.

    **If BRANCH B (CPU fallback):**

    1. Start the demo server: `python -m src.runtime.cli demo --no-browser`
    2. Watch terminal output — should show "Warming up local model..." without GPU layer offload messages.
    3. Send the same curl request above.
    4. Measure time. Target: under 15 seconds (prompt-stripped CPU path).
    5. Verify response JSON contains risk_tier, threat_labels, top_cues, recommendations fields.
    6. Stop the server with Ctrl+C.

    **In both branches, also verify:**
    - The response is valid JSON with no error field
    - risk_tier is "high-risk" or "suspicious" (not "benign") for the VPBank OTP test message
    - The demo UI loads correctly at http://127.0.0.1:8765 in the browser
  </how-to-verify>
  <resume-signal>
    Type one of:
    - "gpu-confirmed: Xs" where X is the measured response time in seconds (confirms BRANCH A success)
    - "cpu-fallback: Xs" where X is the measured response time in seconds (confirms BRANCH B, CPU path working)
    - "failed: [describe issue]" if either path produces errors or incorrect output
  </resume-signal>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| pip install (community wheel) | Third-party binary executed with pip; runs with user-level permissions |
| n_gpu_layers=-1 (full GPU offload) | All model weights loaded into VRAM; unchanged inference path otherwise |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-07b-04 | Tampering | Community CUDA wheel (marcorez8/llama-cpp-python-windows-blackwell-cuda) | mitigate | Verify the wheel hash matches the HuggingFace repo checksum before install. Alternatively, build from source (CUDA 13.1 + nvcc available) to avoid third-party binary trust. |
| T-07b-05 | Denial of Service | n_gpu_layers=-1 + 8GB VRAM | accept | The q8_0 model is 4.28 GB; it fits in 8 GB VRAM. If VRAM is exhausted by another process, llama.cpp falls back to partial CPU offload automatically. Demo is single-user local-only. |
| T-07b-06 | Elevation of Privilege | GPU driver exposure via llama_cpp | accept | llama_cpp is a well-maintained library; GPU interaction is through CUDA RT API, not raw driver access. Risk is standard for any CUDA application. |
</threat_model>

<verification>
After human verification checkpoint:

```
pytest tests/runtime/ -x -q
```

All tests must pass regardless of GPU branch outcome.

Additionally verify: `python -c "from src.runtime.analyzers.gguf import GGUF_CONTEXT_WINDOW, GGUF_COMPLETION_MAX_TOKENS; print(GGUF_CONTEXT_WINDOW, GGUF_COMPLETION_MAX_TOKENS)"` prints `512 250`.
</verification>

<success_criteria>
1. CUDA wheel installation attempt completed (either succeeded or failed gracefully)
2. If GPU: llama_supports_gpu_offload() returns True; n_gpu_layers=-1 in gguf.py; warm latency under 8s confirmed by human
3. If CPU fallback: n_gpu_layers=0 unchanged; warm latency under 15s confirmed by human; no regression in test suite
4. pytest tests/runtime/ -x -q exits 0 in both branches
5. UI-02 fully satisfied: demo is presentation-ready for judging — response under 15s minimum, under 8s if GPU works
</success_criteria>

<output>
After completion, create `.planning/phases/07b-app-response-optimization/07b-02-SUMMARY.md`

Record in the summary:
- Which branch was taken (GPU or CPU fallback)
- Measured warm latency (in seconds) from human checkpoint
- llama_supports_gpu_offload() return value
- Any wheel compatibility issues encountered
</output>
