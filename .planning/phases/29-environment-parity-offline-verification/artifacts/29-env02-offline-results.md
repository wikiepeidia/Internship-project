# ENV-02 Offline Demo Verification Results

**Recorded:** 2026-07-05
**Status:** Complete with browser-extension noise noted
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
- Screenshot review note: the saved DevTools Network screenshot shows three `about:client`-initiated stylesheet entries (`common.css`, `style.css`, `content-script.css`) consistent with browser-extension/content-script noise. It shows no app/backend request to a non-loopback host and no Google Fonts request.

### Screenshot

- Expected path: `.planning/phases/29-environment-parity-offline-verification/artifacts/29-env02-devtools-screenshot.png`
- Current artifact status: present on disk.
- File size: 68,206 bytes.
- Last modified: 2026-07-05 21:25:17 Asia/Bangkok.

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

`python -m src.runtime.cli doctor` was run after network restoration and reported READY. It was rerun after screenshot capture and still reported READY:

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
- runtime-store-raw-text: PASS - runtime_store_raw_text=False
- backend-ready: PASS - backend=gguf ready=True
- release-gate-summary: PASS - latest_verdict=BLOCK run_id=phase5-recovered-balanced-val manifest=data\manifests\phase5-release-eval-phase5-recovered-balanced-val.json
```

## Closeout Judgment

ENV-02 is accepted as passing: both locked prompts rendered the expected verdicts offline, no non-loopback app/backend request or external Google Fonts request was observed, the screenshot artifact is present, and `vnphish doctor` returned READY after network restoration.

The only recorded deviation is browser-extension stylesheet noise in DevTools plus the non-network `SOURCE_LANG_VI` console warning. Neither changes the offline app dependency claim.
