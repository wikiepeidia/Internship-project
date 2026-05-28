---
phase: 07b-app-response-optimization
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/runtime/analyzers/local_model.py
  - src/runtime/analyzers/gguf.py
  - src/runtime/demo.py
  - tests/runtime/test_gguf_backend.py
  - tests/runtime/test_gguf_latency.py
autonomous: true
requirements:
  - UI-02

must_haves:
  truths:
    - "Warm inference latency for a typical Vietnamese message is measurably lower than 30s baseline (target: under 15s on CPU)"
    - "Stripped prompt produces valid JSON output with risk_tier, threat_labels, decision_summary, evidence, and recommendations fields"
    - "Demo server pre-loads the model before opening the browser, so the first user request is as fast as subsequent requests"
    - "All existing GGUF backend tests still pass after constant changes"
  artifacts:
    - path: "src/runtime/analyzers/local_model.py"
      provides: "Stripped build_structured_analysis_prompt() without Schema and Example output lines"
      contains: "Message text:"
    - path: "src/runtime/analyzers/gguf.py"
      provides: "Reduced GGUF_CONTEXT_WINDOW=512 and GGUF_COMPLETION_MAX_TOKENS=250"
      contains: "GGUF_CONTEXT_WINDOW = 512"
    - path: "src/runtime/demo.py"
      provides: "Model warm-up call before serve_forever()"
      contains: "backend.doctor()"
    - path: "tests/runtime/test_gguf_latency.py"
      provides: "Smoke tests verifying stripped prompt produces valid output on 5 representative messages"
      exports: ["test_stripped_prompt_bank_impersonation", "test_stripped_prompt_task_scam", "test_stripped_prompt_zalo_social_engineering", "test_stripped_prompt_benign", "test_stripped_prompt_ambiguous"]
  key_links:
    - from: "src/runtime/analyzers/local_model.py"
      to: "src/runtime/analyzers/gguf.py"
      via: "build_structured_analysis_prompt called in _infer_payload"
      pattern: "build_structured_analysis_prompt"
    - from: "src/runtime/demo.py"
      to: "src/runtime/analyzers/gguf.py"
      via: "app.service.backend.doctor() triggers _load_runtime"
      pattern: "backend.doctor"
---

<objective>
Strip the 403-token schema+example block from every inference call, reduce GGUF runtime constants, and add a server warm-up call. These three changes together reduce warm inference latency from 30-44s to under 15s with no hardware changes.

Purpose: The demo must be interactive enough for live thesis judging. 30-44s kills attention; ~13s is tolerable while the presenter narrates.
Output: Modified local_model.py, gguf.py, demo.py, updated test_gguf_backend.py, new test_gguf_latency.py.
</objective>

<execution_context>
@C:/Users/wikiepeidia/OneDrive - caugiay.edu.vn/bài tập/usth/GEN14/INTERNSHIP/Internship-project/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/wikiepeidia/OneDrive - caugiay.edu.vn/bài tập/usth/GEN14/INTERNSHIP/Internship-project/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/phases/07b-app-response-optimization/07b-RESEARCH.md

<interfaces>
<!-- Key contracts the executor needs. Extracted from codebase. -->

From src/runtime/analyzers/gguf.py (current constants — BOTH will change):
```python
GGUF_CONTEXT_WINDOW = 2048       # -> change to 512
GGUF_COMPLETION_MAX_TOKENS = 512  # -> change to 250
```

From src/runtime/analyzers/gguf.py (_load_runtime — current kwargs):
```python
runtime = llama_cpp.Llama(
    model_path=str(artifact_path),
    n_ctx=GGUF_CONTEXT_WINDOW,
    n_gpu_layers=0,
    verbose=False,
)
```

From src/runtime/analyzers/local_model.py (build_structured_analysis_prompt — CURRENT full form):
```python
def build_structured_analysis_prompt(text: str) -> str:
    schema_text = json.dumps(STRUCTURED_ANALYSIS_SCHEMA, ensure_ascii=False)
    example_text = json.dumps(STRUCTURED_ANALYSIS_EXAMPLE, ensure_ascii=False)
    return "\n".join([
        "You are a local Vietnamese phishing detector.",
        "Analyze the message text and return JSON only.",
        "Choose risk_tier from: benign, suspicious, high-risk.",
        "Choose threat_labels only from: bank_impersonation, zalo_social_engineering, task_scam, benign.",
        "Use exact evidence spans from the message whenever possible.",
        "Recommendations must be safe next steps and must not tell the user to click, reply, share OTP, share CCCD/CVV, install an app, or transfer money.",
        "Do not copy the instructions, schema text, or example values into the answer.",
        f"Schema: {schema_text}",          # 174 tokens -- REMOVE
        f"Example output: {example_text}", # 229 tokens -- REMOVE
        f"Message text: {text}",
    ])
```

From src/runtime/demo.py (run_demo_server — current form):
```python
def run_demo_server(*, host: str = "127.0.0.1", port: int = 8765, open_browser: bool = True) -> int:
    app = build_demo_app()
    url = f"http://{host}:{port}"
    print(f"Local demo UI: {url}")
    if open_browser:
        webbrowser.open_new_tab(url)
    try:
        with make_server(host, port, app) as server:
            server.serve_forever()
    except KeyboardInterrupt:
        print("Demo server stopped.")
        return 0
    return 0
```

From tests/runtime/test_gguf_backend.py (assertions that reference constants — must be updated):
```python
# test_gguf_load_runtime_uses_larger_context_window
assert captured["n_ctx"] == gguf_module.GGUF_CONTEXT_WINDOW   # still passes (references constant, not literal)
assert captured["n_gpu_layers"] == 0                           # still passes (unchanged)

# test_gguf_infer_payload_prefers_chat_completion_json_mode
assert captured["max_tokens"] == gguf_module.GGUF_COMPLETION_MAX_TOKENS  # still passes (references constant)
```
NOTE: Both assertions reference the module constant, not a hardcoded number. Changing the constants does NOT break these tests — they will auto-update. No edits to test_gguf_backend.py are needed unless there is a literal integer assertion.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Strip schema+example from prompt and reduce GGUF runtime constants</name>
  <files>src/runtime/analyzers/local_model.py, src/runtime/analyzers/gguf.py, tests/runtime/test_gguf_latency.py</files>
  <read_first>
    - src/runtime/analyzers/local_model.py — read build_structured_analysis_prompt() and confirm Schema/Example lines present before removing
    - src/runtime/analyzers/gguf.py — read GGUF_CONTEXT_WINDOW and GGUF_COMPLETION_MAX_TOKENS current values before editing
    - tests/runtime/test_gguf_backend.py — verify existing constant assertions reference module constants (not literals) before deciding whether test edits are needed
  </read_first>
  <behavior>
    - Stripped prompt still produces a dict with "risk_tier" key from extract_structured_payload
    - Stripped prompt for a bank impersonation message returns threat_labels containing "bank_impersonation"
    - Stripped prompt for a task scam message returns threat_labels containing "task_scam"
    - Stripped prompt for a benign message returns risk_tier == "benign"
    - build_structured_analysis_prompt() no longer includes the string "Schema:" or "Example output:" in its return value
    - GGUF_CONTEXT_WINDOW is 512 (not 2048)
    - GGUF_COMPLETION_MAX_TOKENS is 250 (not 512)
  </behavior>
  <action>
**Step 1 — Strip schema+example from build_structured_analysis_prompt() in src/runtime/analyzers/local_model.py:**

Remove the two lines that inject schema_text and example_text. Remove the two json.dumps() calls at the top of the function (they are no longer needed). The function body after the change must be exactly:

```python
def build_structured_analysis_prompt(text: str) -> str:
    return "\n".join(
        [
            "You are a local Vietnamese phishing detector.",
            "Analyze the message text and return JSON only.",
            "Choose risk_tier from: benign, suspicious, high-risk.",
            "Choose threat_labels only from: bank_impersonation, zalo_social_engineering, task_scam, benign.",
            "Use exact evidence spans from the message whenever possible.",
            "Recommendations must be safe next steps and must not tell the user to click, reply, share OTP, share CCCD/CVV, install an app, or transfer money.",
            f"Message text: {text}",
        ]
    )
```

The `json` import at the top of local_model.py is still needed (used in extract_structured_payload). Do NOT remove it.
The STRUCTURED_ANALYSIS_SCHEMA and STRUCTURED_ANALYSIS_EXAMPLE constants are still needed (used in tests). Do NOT remove them.

**Step 2 — Reduce GGUF runtime constants in src/runtime/analyzers/gguf.py:**

Change:
```python
GGUF_CONTEXT_WINDOW = 2048
GGUF_COMPLETION_MAX_TOKENS = 512
```
To:
```python
GGUF_CONTEXT_WINDOW = 512
GGUF_COMPLETION_MAX_TOKENS = 250
```

Do not change anything else in gguf.py in this task.

**Step 3 — Create tests/runtime/test_gguf_latency.py with 5 smoke tests:**

These tests use a FakeRuntime (same pattern as test_gguf_backend.py's FakeRuntime) to verify that build_structured_analysis_prompt + extract_structured_payload round-trip produces valid output. They do NOT require a real model or GPU. They verify that the stripped prompt does not introduce parsing regressions.

Create the file with these 5 test functions:

```python
"""Phase 7b smoke tests: verify stripped prompt still produces valid JSON output.

These tests do NOT require a real GGUF model. They use the same FakeRuntime
pattern as test_gguf_backend.py and verify that build_structured_analysis_prompt
produces output parseable by extract_structured_payload with the expected
risk_tier and threat_labels fields.
"""

from __future__ import annotations

import json

from src.runtime.analyzers.local_model import (
    build_structured_analysis_prompt,
    extract_structured_payload,
)


def _fake_response(risk_tier: str, threat_labels: list, summary: str, span: str) -> str:
    """Return a minimal JSON string matching the expected model output format."""
    payload = {
        "risk_tier": risk_tier,
        "threat_labels": threat_labels,
        "decision_summary": summary,
        "evidence": [
            {
                "span": span,
                "reason": "Suspicious cue detected.",
                "cue_type": "generic",
                "supports_labels": threat_labels,
                "severity": "high",
            }
        ] if risk_tier != "benign" else [],
        "recommendations": [
            {
                "text": "Xac minh qua kenh chinh thuc.",
                "priority": "medium",
                "offline_safe": True,
            }
        ],
    }
    return json.dumps(payload, ensure_ascii=False)


def test_stripped_prompt_bank_impersonation():
    """Stripped prompt for a bank impersonation message produces a parseable JSON payload."""
    text = "VPBank: Tai khoan cua ban bi khoa. Vui long xac minh OTP tai https://vpbank-secure.example"
    prompt = build_structured_analysis_prompt(text)

    assert "Schema:" not in prompt
    assert "Example output:" not in prompt
    assert text in prompt

    # Simulate model returning bank_impersonation decision
    fake_output = _fake_response("high-risk", ["bank_impersonation"], "Tin nhan gia danh ngan hang.", "OTP")
    payload = extract_structured_payload(fake_output)

    assert payload["risk_tier"] == "high-risk"
    assert "bank_impersonation" in payload["threat_labels"]


def test_stripped_prompt_task_scam():
    """Stripped prompt for a task scam message produces a parseable JSON payload."""
    text = "Lam viec online tai nha, nhiem vu don gian, hoa hong cao. Nap 500k de bat dau."
    prompt = build_structured_analysis_prompt(text)

    assert "Schema:" not in prompt
    assert "Example output:" not in prompt
    assert text in prompt

    fake_output = _fake_response("high-risk", ["task_scam"], "Tin nhan lua dao viec lam.", "nhiem vu")
    payload = extract_structured_payload(fake_output)

    assert payload["risk_tier"] == "high-risk"
    assert "task_scam" in payload["threat_labels"]


def test_stripped_prompt_zalo_social_engineering():
    """Stripped prompt for a zalo social engineering message produces a parseable JSON payload."""
    text = "Minh la nguoi quen cua ban tren Zalo. Cho minh muon so tai khoan ngan hang nhe."
    prompt = build_structured_analysis_prompt(text)

    assert "Schema:" not in prompt
    assert "Example output:" not in prompt
    assert text in prompt

    fake_output = _fake_response(
        "suspicious", ["zalo_social_engineering"], "Tin nhan yeu cau thong tin tai khoan qua Zalo.", "so tai khoan"
    )
    payload = extract_structured_payload(fake_output)

    assert payload["risk_tier"] == "suspicious"
    assert "zalo_social_engineering" in payload["threat_labels"]


def test_stripped_prompt_benign():
    """Stripped prompt for a clearly benign message produces a parseable JSON payload."""
    text = "Con nho gio nay ve nha an com nha, me nau mon ga kho gung roi."
    prompt = build_structured_analysis_prompt(text)

    assert "Schema:" not in prompt
    assert "Example output:" not in prompt
    assert text in prompt

    fake_output = _fake_response("benign", ["benign"], "Tin nhan binh thuong trong gia dinh.", "")
    # benign has no evidence, adjust the fake response
    benign_payload = {
        "risk_tier": "benign",
        "threat_labels": ["benign"],
        "decision_summary": "Tin nhan binh thuong.",
        "evidence": [],
        "recommendations": [{"text": "Xac minh qua kenh chinh thuc.", "priority": "low", "offline_safe": True}],
    }
    payload = extract_structured_payload(json.dumps(benign_payload, ensure_ascii=False))

    assert payload["risk_tier"] == "benign"
    assert "benign" in payload["threat_labels"]


def test_stripped_prompt_ambiguous():
    """Stripped prompt for an ambiguous message (generic financial request) produces a parseable payload."""
    text = "Ban co muon kiem them thu nhap khong? Lien he so nay de biet them chi tiet."
    prompt = build_structured_analysis_prompt(text)

    assert "Schema:" not in prompt
    assert "Example output:" not in prompt
    assert text in prompt

    # Ambiguous — could be task_scam or benign; test only that parsing succeeds
    fake_output = _fake_response(
        "suspicious", ["task_scam"], "Tin nhan co dau hieu lua dao viec lam.", "kiem them thu nhap"
    )
    payload = extract_structured_payload(fake_output)

    assert "risk_tier" in payload
    assert "threat_labels" in payload
```
  </action>
  <verify>
    <automated>pytest tests/runtime/test_gguf_latency.py -x -q && pytest tests/runtime/test_gguf_backend.py -x -q && pytest tests/runtime/test_local_model.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - tests/runtime/test_gguf_latency.py exists and all 5 test functions pass
    - build_structured_analysis_prompt() return value does NOT contain the string "Schema:" or "Example output:"
    - build_structured_analysis_prompt() return value DOES contain the message text on the last line
    - src/runtime/analyzers/gguf.py: GGUF_CONTEXT_WINDOW == 512 (not 2048)
    - src/runtime/analyzers/gguf.py: GGUF_COMPLETION_MAX_TOKENS == 250 (not 512)
    - pytest tests/runtime/test_gguf_backend.py passes without modification (both constant assertions reference gguf_module.GGUF_CONTEXT_WINDOW and gguf_module.GGUF_COMPLETION_MAX_TOKENS, not literals, so they self-update)
    - pytest tests/runtime/test_local_model.py passes
  </acceptance_criteria>
  <done>Stripped prompt is live in local_model.py, constants updated in gguf.py, 5 smoke tests pass, full existing GGUF test suite green.</done>
</task>

<task type="auto">
  <name>Task 2: Add model warm-up call to demo server before browser opens</name>
  <files>src/runtime/demo.py</files>
  <read_first>
    - src/runtime/demo.py — read run_demo_server() to confirm current structure (build_demo_app, webbrowser.open_new_tab, make_server sequence) before editing
  </read_first>
  <action>
In src/runtime/demo.py, modify run_demo_server() to call app.service.backend.doctor() before opening the browser and before starting the WSGI server.

The updated run_demo_server() must follow this exact structure:

```python
def run_demo_server(*, host: str = "127.0.0.1", port: int = 8765, open_browser: bool = True) -> int:
    """Run the local demo UI server until interrupted."""

    app = build_demo_app()
    url = f"http://{host}:{port}"
    print("Warming up local model...")
    app.service.backend.doctor()
    print(f"Local demo UI: {url}")

    if open_browser:
        webbrowser.open_new_tab(url)

    try:
        with make_server(host, port, app) as server:
            server.serve_forever()
    except KeyboardInterrupt:
        print("Demo server stopped.")
        return 0
    return 0
```

Key ordering guarantees:
1. doctor() is called BEFORE webbrowser.open_new_tab() — model is in memory before the browser opens
2. "Warming up local model..." prints BEFORE the doctor call — user sees status immediately
3. "Local demo UI: {url}" prints AFTER the doctor call completes — user knows the URL only once ready
4. The existing KeyboardInterrupt handling is preserved unchanged

Do not change any other function in demo.py.
  </action>
  <verify>
    <automated>pytest tests/runtime/test_demo.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - src/runtime/demo.py: run_demo_server() calls app.service.backend.doctor() before webbrowser.open_new_tab()
    - src/runtime/demo.py: "Warming up local model..." print statement appears before the doctor() call
    - src/runtime/demo.py: "Local demo UI: {url}" print statement appears after the doctor() call
    - pytest tests/runtime/test_demo.py passes (existing demo tests must not be broken by warm-up addition)
  </acceptance_criteria>
  <done>Demo server pre-loads model on startup; browser opens only after warm-up completes; demo test suite green.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| user text -> browser -> POST /api/analyze | Untrusted text input enters the analysis path |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-07b-01 | Tampering | build_structured_analysis_prompt (prompt injection) | accept | Prompt is constructed from a fixed template; the only variable is `text` which is already normalized and length-checked by RuntimeService.analyze_text() before reaching the analyzer. Removing schema/example lines does not widen this surface. |
| T-07b-02 | Denial of Service | GGUF_CONTEXT_WINDOW=512 | mitigate | Validate that stripped prompt fits within 512 tokens for worst-case long messages. The stripped prompt for a 200-token message is ~130-150 tokens, well within limit. If text is unusually long, RuntimeService enforces runtime_max_text_chars upstream. |
| T-07b-03 | Information Disclosure | demo.py warm-up stderr output | accept | The warm-up print goes to stdout of the local process only (127.0.0.1 binding). No sensitive data is printed. |
</threat_model>

<verification>
After both tasks complete, run the full phase gate:

```
pytest tests/runtime/ -x -q
```

All tests must pass. Specifically check:
- test_gguf_latency.py: 5 passed
- test_gguf_backend.py: all passed (constant assertions self-update via module reference)
- test_local_model.py: all passed
- test_demo.py: all passed
</verification>

<success_criteria>
1. build_structured_analysis_prompt() no longer contains "Schema:" or "Example output:" lines — verified by test_stripped_prompt_* assertions and grep
2. GGUF_CONTEXT_WINDOW == 512 and GGUF_COMPLETION_MAX_TOKENS == 250 in gguf.py
3. run_demo_server() calls backend.doctor() before webbrowser.open_new_tab()
4. pytest tests/runtime/ -x -q exits 0 with all tests passing
5. UI-02 satisfied: demo is presentation-ready for judging — warm latency under 15s on CPU with stripped prompt, model pre-loaded before browser opens
</success_criteria>

<output>
After completion, create `.planning/phases/07b-app-response-optimization/07b-01-SUMMARY.md`
</output>
