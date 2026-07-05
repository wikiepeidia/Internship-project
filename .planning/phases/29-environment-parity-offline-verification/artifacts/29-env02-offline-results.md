# ENV-02 Offline Demo Verification Results

**Recorded:** 2026-07-05
**Status:** Pending screenshot artifact
**Requirement:** ENV-02

## Human-Reported Offline Run

The human reported completing the offline runbook section with the network disabled.

### Scam Golden Prompt

- Risk tier rendered: `high-risk`
- Threat labels rendered: `bank_impersonation`
- Observed UI summary: `Structured decision from sms local runtime.`
- Observed result: pass for the ENV-02 verdict criterion.

### Benign Golden Prompt

- Risk tier rendered: `benign` / low-no-threat UI state.
- Threat labels rendered: `benign`
- Observed UI summary: `Structured decision from sms local runtime: legitimate bank OTP notice.`
- Observed result: pass for the ENV-02 verdict criterion.
- Human note: the benign explanation/recommendation text was awkward before follow-up fix.

### DevTools Network

- Human reported no request entries in the Network tab during the offline run.
- Human reported no external host requests.
- No `fonts.googleapis.com` or `fonts.gstatic.com` request was reported.
- Console note: browser console showed `ERROR SOURCE_LANG_VI`. Source not found in local runtime/frontend source during follow-up search, so this is recorded as a non-network console deviation rather than an ENV-02 blocker.

### Screenshot

- Expected path: `.planning/phases/29-environment-parity-offline-verification/artifacts/29-env02-devtools-screenshot.png`
- Current artifact status: missing on disk at record time.
- ENV-02 should not be marked fully complete until the screenshot is saved or the missing screenshot is explicitly accepted as an evidence deviation.

## Follow-Up Fix

The awkward benign recommendation text came from `DEFAULT_BENIGN_RECOMMENDATION` in `src/runtime/analyzers/local_model.py`.

Follow-up commit:

- `f3c1772` - `fix(29-04): improve benign OTP recommendation copy`

Verified after the fix:

```text
Structured decision from sms local runtime: legitimate bank OTP notice.
Risk tier: Benign
Threat labels: Benign
Next steps:
- Không cần thao tác thêm nếu bạn nhận ra nội dung này. Nếu vẫn thấy bất thường, hãy tự kiểm tra qua ứng dụng, website hoặc tổng đài chính thức.
```

## Post-Test Doctor

`python -m src.runtime.cli doctor` was run after network restoration and reported READY:

```text
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
- runtime-store-raw-text: PASS - settings.runtime_store_raw_text=False
- backend-ready: PASS - backend=gguf ready=True
- release-gate-summary: PASS - latest_verdict=BLOCK run_id=phase5-recovered-balanced-val manifest=data\manifests\phase5-release-eval-phase5-recovered-balanced-val.json
```

## Remaining Gate

Save or provide the DevTools Network screenshot at:

`.planning/phases/29-environment-parity-offline-verification/artifacts/29-env02-devtools-screenshot.png`

After that, rerun `vnphish doctor`, update this artifact from pending to complete, and close `29-04`.

