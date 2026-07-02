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

Correction note: re-evaluated on 2026-07-02 after the original TPBank OTP-style scam prompt was judged too ambiguous for the live demo boundary. The corrected lock uses a clear malicious-link bank impersonation scam and a legitimate bank OTP notice that now returns benign.

### Golden scam prompt

- Channel: `sms`
- STABLE=true
- Final locked text: "【VIETCOMBANK】 Tai khoan cua ban vua bi truy cap tu thiet bi la luc 03:47 SA. Neu ko phai ban, bam vao link de khoa ngay: http://vcb-secure-alert.net/lock?id=9182736 hoac goi 1800.9999 (mien phi). OTP se het han sau 5 phut!"

| run | risk_tier | threat_labels | latency_ms |
| --- | --- | --- | --- |
| 1 | high-risk | bank_impersonation | 26627.258 |
| 2 | high-risk | bank_impersonation | 19944.812 |
| 3 | high-risk | bank_impersonation | 19888.596 |
| 4 | high-risk | bank_impersonation | 18855.780 |
| 5 | high-risk | bank_impersonation | 19283.566 |

### Golden benign prompt

- Channel: `sms`
- STABLE=true
- Final locked text: "VPBank Smart OTP: Mã xác thực của bạn là 847291. Mã này có hiệu lực trong 90 giây để xác nhận đăng nhập Internet Banking. Tuyệt đối KHÔNG chia sẻ mã này với bất kỳ ai, kể cả nhân viên ngân hàng."

| run | risk_tier | threat_labels | latency_ms |
| --- | --- | --- | --- |
| 1 | benign | benign | 24118.089 |
| 2 | benign | benign | 17171.970 |
| 3 | benign | benign | 17229.259 |
| 4 | benign | benign | 17004.724 |
| 5 | benign | benign | 17310.181 |

Candidate correction/substitution: the original TPBank OTP-style scam prompt and meeting-reschedule benign fixture were superseded for demo clarity. The reported Techcombank OTP benign candidate was first observed as a false positive, then passed as `Benign` after the legitimate-bank-OTP correction. The final locked benign prompt is the VPBank Smart OTP notice because it is shorter and matches the trained benign OTP style.

## DIAG-03: Warm-latency reading

- Recorded: `2026-07-02T08:15:06.049977+00:00`
- Baseline warm-latency figure: `26627.258 ms`
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
