# Phase 28 Baseline Diagnostics Results

Recorded: 2026-07-02 13:56:06 +07:00

## DIAG-01: vnphish doctor

Command: vnphish doctor
Exit code: 0

Note: the release-gate-summary line may print latest_verdict=BLOCK while still reporting PASS; per Phase 28 research this is a stale pre-Phase-7a artifact reference and is not a doctor failure. The readiness decision is the top-line READY backend=gguf local_only=True text_only=True plus exit code 0.

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

llama_context: n_ctx_seq (512) < n_ctx_train (262144) -- the full capacity of the model will not be utilized
```

## DIAG-02: vnphish analyze correctness pass

Grounded-cue interpretation: threat-class rows must include non-empty suspicious evidence. The benign row explicitly records `count=0` because the runtime contract permits `top_cues: []` and the clearly benign fixture has no suspicious evidence to quote; it still records the rendered risk tier, threat label, and safe next step.

| class | message text used | channel | exit code | risk tier | threat labels | grounded cues captured | safe-step/Next steps captured | substituted-from-fallback y/n |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| bank_impersonation | Thông báo từ TPBank: OTP của bạn là 847291. KHÔNG chia sẻ mã này với bất kỳ ai. Nếu bạn ko thực hiện giao dịch, gọi ngay 0938.xxx.xxx để được hỗ trợ khóa account. | sms | 0 | Suspicious | Bank impersonation | count=3<br>"OTP của bạn là 847291" - Structured decision from sms local runtime.<br>"KHÔNG chia sẻ mã này với bất kỳ ai" - Structured decision from sms local runtime.<br>"0938.xxx.xxx" - Structured decision from sms local runtime. | count=3<br>Liên hệ trực tiếp với TPBank qua số điện thoại chính thức để xác minh thông tin.<br>Không gọi điện cho số điện thoại lạ nếu không có yêu cầu chính thức từ ngân hàng.<br>Kiểm tra lại lịch sử giao dịch gần đây trên ứng dụng ngân hàng chính thức. | n |
| zalo_social_engineering | Bro ơi mình đang ở nước ngoài, điện thoại hỏng ko gọi dc. Mày có thể mua giúp tao thẻ Viettel 500k rồi chụp mã gửi qua Zalo k? Tao về trả liền, cần gấp lắm 😭 | zalo | 0 | High risk | Zalo social engineering | count=3<br>"đang ở nước ngoài, điện thoại hỏng ko gọi dc" - Structured decision from zalo local runtime.<br>"mua giúp tao thẻ Viettel 500k rồi chụp mã gửi qua Zalo" - Structured decision from zalo local runtime.<br>"Tao về trả liền, cần gấp lắm" - Structured decision from zalo local runtime. | count=3<br>Không thực hiện yêu cầu mua thẻ và gửi mã cho bất kỳ ai qua Zalo hoặc tin nhắn.<br>Gọi trực tiếp số điện thoại của người đó để xác minh trước khi làm bất kỳ việc gì.<br>Nếu không thể gọi, hãy nhờ người thân hoặc bạn bè khác xác nhận. | n |
| task_scam | Bạn ơi, tài khoản của bạn đang có vấn đề. Vui lòng đăng nhập vào app và kiểm tra lại. Nếu cần hỗ trợ, gọi 0123456789. Thanks! | sms | 0 | Suspicious | Task scam | count=2<br>"Vui lòng đăng nhập vào app và kiểm tra lại" - Structured decision from sms local runtime.<br>"0123456789" - Structured decision from sms local runtime. | count=2<br>Không đăng nhập vào bất kỳ ứng dụng nào nếu không tự mình biết rõ nguồn gốc.<br>Liên hệ trực tiếp với ngân hàng hoặc tổ chức tài chính chính thức nếu có nghi ngờ. | n |
| benign | Chào bạn, lịch họp nhóm được dời sang 9h sáng mai tại phòng học tầng 3. Nếu bận thì báo lại giúp mình trước tối nay. | sms | 0 | Benign | Benign | count=0<br> | count=1<br>Neu ban van thay bat thuong, hay tu xac minh qua kenh chinh thuc ma ban tin cay. | n |

### Raw DIAG-02 outputs

#### bank_impersonation

Command: vnphish analyze --text "Thông báo từ TPBank: OTP của bạn là 847291. KHÔNG chia sẻ mã này với bất kỳ ai. Nếu bạn ko thực hiện giao dịch, gọi ngay 0938.xxx.xxx để được hỗ trợ khóa account." --channel sms
Exit code: 0

```text
Structured decision from sms local runtime.
Risk tier: Suspicious
Threat labels: Bank impersonation
Grounded cues:
- "OTP của bạn là 847291" - Structured decision from sms local runtime.
- "KHÔNG chia sẻ mã này với bất kỳ ai" - Structured decision from sms local runtime.
- "0938.xxx.xxx" - Structured decision from sms local runtime.
Next steps:
- Liên hệ trực tiếp với TPBank qua số điện thoại chính thức để xác minh thông tin.
- Không gọi điện cho số điện thoại lạ nếu không có yêu cầu chính thức từ ngân hàng.
- Kiểm tra lại lịch sử giao dịch gần đây trên ứng dụng ngân hàng chính thức.

llama_context: n_ctx_seq (512) < n_ctx_train (262144) -- the full capacity of the model will not be utilized
llama_context: n_ctx_seq (512) < n_ctx_train (262144) -- the full capacity of the model will not be utilized
```

## GOLD-01 / GOLD-02: Locked golden prompts

Machine-readable source: `.planning/phases/28-baseline-readiness-zero-code-diagnostics/artifacts/28-golden-prompt-results.json`

### Golden scam prompt

- Channel: `sms`
- STABLE=true
- Final locked text: "Thông báo từ TPBank: OTP của bạn là 847291. KHÔNG chia sẻ mã này với bất kỳ ai. Nếu bạn ko thực hiện giao dịch, gọi ngay 0938.xxx.xxx để được hỗ trợ khóa account."

| run | risk_tier | threat_labels | latency_ms |
| --- | --- | --- | --- |
| 1 | suspicious | bank_impersonation | 23993.489 |
| 2 | suspicious | bank_impersonation | 20014.696 |
| 3 | suspicious | bank_impersonation | 20640.250 |
| 4 | suspicious | bank_impersonation | 16957.768 |
| 5 | suspicious | bank_impersonation | 16089.349 |

### Golden benign prompt

- Channel: `sms`
- STABLE=true
- Final locked text: "Chào bạn, lịch họp nhóm được dời sang 9h sáng mai tại phòng học tầng 3. Nếu bận thì báo lại giúp mình trước tối nay."

| run | risk_tier | threat_labels | latency_ms |
| --- | --- | --- | --- |
| 1 | benign | benign | 7598.876 |
| 2 | benign | benign | 6609.536 |
| 3 | benign | benign | 6585.394 |
| 4 | benign | benign | 6559.911 |
| 5 | benign | benign | 6604.690 |

No candidate rejection/substitution was needed during locking. The default Phase 28 TPBank fallback scam prompt and the `sample_benign_message` fixture both locked cleanly through the real web demo.

## DIAG-03: Warm-latency reading

- Recorded: `2026-07-02T06:59:46.512347+00:00`
- Baseline warm-latency figure: `23993.489 ms`
- Method: Playwright captured `response.request.timing` for the first real browser `/api/analyze` response after the script-owned `vnphish demo` server became reachable. This is the same Resource Timing API data family exposed by the browser DevTools Network panel and is recorded as the Phase 30 comparison baseline.

#### zalo_social_engineering

Command: vnphish analyze --text "Bro ơi mình đang ở nước ngoài, điện thoại hỏng ko gọi dc. Mày có thể mua giúp tao thẻ Viettel 500k rồi chụp mã gửi qua Zalo k? Tao về trả liền, cần gấp lắm 😭" --channel zalo
Exit code: 0

```text
Structured decision from zalo local runtime.
Risk tier: High risk
Threat labels: Zalo social engineering
Grounded cues:
- "đang ở nước ngoài, điện thoại hỏng ko gọi dc" - Structured decision from zalo local runtime.
- "mua giúp tao thẻ Viettel 500k rồi chụp mã gửi qua Zalo" - Structured decision from zalo local runtime.
- "Tao về trả liền, cần gấp lắm" - Structured decision from zalo local runtime.
Next steps:
- Không thực hiện yêu cầu mua thẻ và gửi mã cho bất kỳ ai qua Zalo hoặc tin nhắn.
- Gọi trực tiếp số điện thoại của người đó để xác minh trước khi làm bất kỳ việc gì.
- Nếu không thể gọi, hãy nhờ người thân hoặc bạn bè khác xác nhận.

llama_context: n_ctx_seq (512) < n_ctx_train (262144) -- the full capacity of the model will not be utilized
llama_context: n_ctx_seq (512) < n_ctx_train (262144) -- the full capacity of the model will not be utilized
```

#### task_scam

Command: vnphish analyze --text "Bạn ơi, tài khoản của bạn đang có vấn đề. Vui lòng đăng nhập vào app và kiểm tra lại. Nếu cần hỗ trợ, gọi 0123456789. Thanks!" --channel sms
Exit code: 0

```text
Structured decision from sms local runtime.
Risk tier: Suspicious
Threat labels: Task scam
Grounded cues:
- "Vui lòng đăng nhập vào app và kiểm tra lại" - Structured decision from sms local runtime.
- "0123456789" - Structured decision from sms local runtime.
Next steps:
- Không đăng nhập vào bất kỳ ứng dụng nào nếu không tự mình biết rõ nguồn gốc.
- Liên hệ trực tiếp với ngân hàng hoặc tổ chức tài chính chính thức nếu có nghi ngờ.

llama_context: n_ctx_seq (512) < n_ctx_train (262144) -- the full capacity of the model will not be utilized
llama_context: n_ctx_seq (512) < n_ctx_train (262144) -- the full capacity of the model will not be utilized
```

#### benign

Command: vnphish analyze --text "Chào bạn, lịch họp nhóm được dời sang 9h sáng mai tại phòng học tầng 3. Nếu bận thì báo lại giúp mình trước tối nay." --channel sms
Exit code: 0

```text
Structured decision from sms local runtime.
Risk tier: Benign
Threat labels: Benign
Next steps:
- Neu ban van thay bat thuong, hay tu xac minh qua kenh chinh thuc ma ban tin cay.

llama_context: n_ctx_seq (512) < n_ctx_train (262144) -- the full capacity of the model will not be utilized
llama_context: n_ctx_seq (512) < n_ctx_train (262144) -- the full capacity of the model will not be utilized
```
