# Phase 39 Final-Snapshot Manual Quality Review

<!-- phase39-final-review-meta:{"carried_count":2,"composition":{"sample_axes":{"judge_origin":{"carried_forward_exact_record":51,"fresh_final_delta":49},"judge_status":{"fail":43,"pass":57},"label":{"bank_impersonation":33,"benign":26,"task_scam":32,"zalo_social_engineering":9}},"sample_size":100,"sample_strata":{"bank_impersonation|fail|carried_forward_exact_record":8,"bank_impersonation|fail|fresh_final_delta":8,"bank_impersonation|pass|carried_forward_exact_record":9,"bank_impersonation|pass|fresh_final_delta":8,"benign|fail|carried_forward_exact_record":9,"benign|fail|fresh_final_delta":1,"benign|pass|carried_forward_exact_record":9,"benign|pass|fresh_final_delta":7,"task_scam|fail|carried_forward_exact_record":8,"task_scam|fail|fresh_final_delta":8,"task_scam|pass|carried_forward_exact_record":8,"task_scam|pass|fresh_final_delta":8,"zalo_social_engineering|fail|fresh_final_delta":1,"zalo_social_engineering|pass|fresh_final_delta":8},"source_axes":{"judge_origin":{"carried_forward_exact_record":1561,"fresh_final_delta":536},"judge_status":{"fail":702,"pass":1395},"label":{"bank_impersonation":741,"benign":655,"task_scam":404,"zalo_social_engineering":297}},"source_strata":{"bank_impersonation|fail|carried_forward_exact_record":149,"bank_impersonation|fail|fresh_final_delta":16,"bank_impersonation|pass|carried_forward_exact_record":545,"bank_impersonation|pass|fresh_final_delta":31,"benign|fail|carried_forward_exact_record":323,"benign|fail|fresh_final_delta":1,"benign|pass|carried_forward_exact_record":324,"benign|pass|fresh_final_delta":7,"task_scam|fail|carried_forward_exact_record":155,"task_scam|fail|fresh_final_delta":57,"task_scam|pass|carried_forward_exact_record":65,"task_scam|pass|fresh_final_delta":127,"zalo_social_engineering|fail|fresh_final_delta":1,"zalo_social_engineering|pass|fresh_final_delta":296},"source_total":2097,"unavailable_strata":["zalo_social_engineering|fail|carried_forward_exact_record","zalo_social_engineering|pass|carried_forward_exact_record"]},"historical_merged_sha256":"e8b4d947271717e56556a74136c57d83dd58589c78699d557999140a9fb55750","historical_parse_stats":{"blank_verdict":2,"carry_index_size":94,"malformed_verdict":2,"sections":100,"unknown_verdict_token":2,"valid_unambiguous":94},"historical_sheet_sha256":"e078b3bf6efd29c8f80f7ea8afaeb1121803c4ce8322fe4a497dd997b9b17743","manifest_sha256":"e55d768b5aad05ba6946fbb0e7ed248180186b7cbaad21d257a134e2f1b3dbad","merged_sha256":"097924e544502f4ff318f89f47bb2489910928b0eda244f8e55d745253c9ac59","ordered_sample_digest_sha256":"ebdf0dc4aa09de8fccf187a75508d2a5de800fb9fcbb07b9a553914d8b499bbb","pending_count":98,"protected_historical_sha256":{"39-manual-review-sheet.md":"e078b3bf6efd29c8f80f7ea8afaeb1121803c4ce8322fe4a497dd997b9b17743","39-mislabel-triage-sheet.md":"39ca1768c0a114156aece97e7dff2269b074a5125d59b8592f215e3e36415cc7","MISLABEL triage.md":"c408dcf4161d84056b7c22e1fb3e975352a52cd5fbf2b111f11b5dfece0c089c"},"provenance_sha256":"7cc6f9086a582fd45583d463bab8ce470e3a64d0d786b28afff101219dc097dd","sample_salt":"phase39-final-manual-review-v1","sample_size":100,"schema_version":"phase39-final-manual-review-v1"} -->

- **Final manifest SHA-256:** `e55d768b5aad05ba6946fbb0e7ed248180186b7cbaad21d257a134e2f1b3dbad`
- **Sample:** 100 rows using `phase39-final-manual-review-v1`
- **Exact prior-human carries:** 2
- **Pending final-human decisions:** 98
- **Unavailable cross-strata:** zalo_social_engineering|fail|carried_forward_exact_record, zalo_social_engineering|pass|carried_forward_exact_record

This sheet is bound to the promoted final corpus and complete judge bundle. For every row with `human_verdict_origin=pending_final_human`, read the message, label, risk tier, literal spans, XAI explanation, and Codex evidence. Replace exactly one `[ ]` with `[x]`. Add a short note for each FAIL. Do not edit any hash, evidence field, heading, marker, or carried verdict.

There are four labels: `bank_impersonation`, `benign`, `task_scam`, and `zalo_social_engineering`. Risk tier is a separate three-value field: `benign`, `suspicious`, or `high-risk`.

---
## Final Example 001/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=65
- **Record digest:** `bc338df70d5527aee7f3539fe2ea1b59ebf99e2e557594ff551e9a91f96ae508`
- **Evidence digest:** `728b2245152dec424ca7c4397db74aef389e7ec781f38baca2a90571afcfeee2`
- **Judge origin:** `carried_forward_exact_record`
- **Judge provenance source:** `data/processed/phase39-final-evidence/carry.jsonl` (SHA-256 `593b34ab8eb01d817b849e26aea1022dac422d2a1ef16822ffe44f5cb24b5ea8`)
- **Judge provenance iteration:** historical exact carry
- **Historical judge coordinate:** train:88
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Bạn ơi, đây là Vietcombank nè. Tài khoản của bạn đang bị khóa tạm thời vì nghi ngờ gian lận. Để kích hoạt lại, vui lòng đăng nhập vào ứng dụng của chúng tôi qua link này: [https://vcbbank.com.vn/login]. Nhớ nha!

- **Label:** `bank_impersonation`
- **Risk tier:** `suspicious`
- **Suspicious spans (JSON):** ["[https://vcbbank.com.vn/login]"]
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_aecabce08a90`

### XAI explanation

> Nên kiểm tra kỹ địa chỉ URL trước khi đăng nhập và không chia sẻ thông tin tài khoản với người lạ.

- **Codex judge verdict:** FAIL -- realism=2, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=2, suspicious_span_accuracy=4
- **Judge reason:**

> Overly casual bank voice is artificial, while the fake login and lock scenario is high risk.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [ ] PASS   [x] FAIL

**Notes:** Final triage: (Drop row): Overly casual unnatural tone for a bank notice, bracketed URL syntax artifact ([https://...]), and risk tier mismatch (fake login + account lock warrants high-risk instead of suspicious).
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 002/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=77
- **Record digest:** `1f26d2bd9e5bbde426e6698b99048d73b6c0a5da47adb59e161f276e343a1acf`
- **Evidence digest:** `d4fd6f0570839f3a5ffec8442668f4b96e44943e90e08165152ee1b07e7ad890`
- **Judge origin:** `carried_forward_exact_record`
- **Judge provenance source:** `data/processed/phase39-final-evidence/carry.jsonl` (SHA-256 `593b34ab8eb01d817b849e26aea1022dac422d2a1ef16822ffe44f5cb24b5ea8`)
- **Judge provenance iteration:** historical exact carry
- **Historical judge coordinate:** train:102
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Chào anh/chị, em là Nguyễn Minh Tuấn – chuyên viên hỗ trợ khách hàng Techcombank khu vực HN. Hệ thống vừa ghi nhận có 1 thiết bị lạ đăng nhập Internet Banking tài khoản của anh/chị lúc 02:47 sáng nay từ IP nước ngoài. Để tạm dừng giao dịch đáng ngờ này, anh/chị cần cung cấp mã OTP vừa nhận được và xác nhận lại số tài khoản để bên em hỗ trợ khóa thiết bị đó nha. Nếu ko xử lý trong 30 phút thì toàn bộ số dư có thể bị chuyển đi ak. Anh/chị phản hồi ngay giúp em với ạ!

- **Label:** `bank_impersonation`
- **Risk tier:** `high-risk`
- **Suspicious spans (JSON):** ["cung cấp mã OTP vừa nhận được", "toàn bộ số dư có thể bị chuyển đi", "thiết bị lạ đăng nhập Internet Banking"]
- **Source:** `synthetic_claude`
- **Seed ID:** `seed_d41d9b30081a`

### XAI explanation

> Nhân viên ngân hàng thật sự tuyệt đối không bao giờ yêu cầu khách hàng cung cấp mã OTP qua Zalo hoặc bất kỳ kênh nhắn tin nào.

- **Codex judge verdict:** PASS -- realism=5, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:**

> Natural fake specialist requests OTP and account details under severe balance-loss pressure.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [x] PASS   [ ] FAIL

**Notes:** 
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 003/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=131
- **Record digest:** `7ed9de3dcb18d50b674950364f5ae2fbced455fc9683bd5ec46fa103f6e43943`
- **Evidence digest:** `b94e45809818d6af803c4d5b5e0102488064af4d066877fb0f5c9c00e5988e22`
- **Judge origin:** `carried_forward_exact_record`
- **Judge provenance source:** `data/processed/phase39-final-evidence/carry.jsonl` (SHA-256 `593b34ab8eb01d817b849e26aea1022dac422d2a1ef16822ffe44f5cb24b5ea8`)
- **Judge provenance iteration:** historical exact carry
- **Historical judge coordinate:** train:181
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> ACB thông báo: Tài khoản iCloud liên kết với ACB Pay của bạn cần được xác minh lại. Nếu bạn chưa có tài khoản iCloud, phía ngân hàng sẽ cấp 1 tài khoản miễn phí. Liên hệ CSKH: 028.7300.xxxx hoặc truy cập acb-iosvn.com/xacminh để biết thêm chi tiết. Xử lý trong 24h nha!

- **Label:** `bank_impersonation`
- **Risk tier:** `high-risk`
- **Suspicious spans (JSON):** ["acb-iosvn.com/xacminh", "phía ngân hàng sẽ cấp 1 tài khoản miễn phí", "Tài khoản iCloud liên kết với ACB Pay"]
- **Source:** `synthetic_claude`
- **Seed ID:** `seed_686d86ff091c`

### XAI explanation

> Tin nhắn giả mạo ACB khai thác thủ thuật yêu cầu tài khoản iCloud — đúng với phương thức lừa đảo vay tiền qua iCloud — để chiếm quyền kiểm soát thiết bị và tài khoản ngân hàng của nạn nhân.

- **Codex judge verdict:** FAIL -- realism=1, label_correctness=4, code_switch_naturalness=5, risk_tier_correctness=4, suspicious_span_accuracy=5
- **Judge reason:**

> A bank offering free iCloud accounts is implausible and reads like an artificial premise.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [ ] PASS   [x] FAIL

**Notes:** Final triage: (Drop row): Unrealistic synthetic premise (bank offering free iCloud accounts); lacks real-world plausibility.
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 004/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=214
- **Record digest:** `bd7cf9ae682868f6682b014ecd3e8ba777df5270be7ff2aa3840c5775db94f91`
- **Evidence digest:** `ad9591cd0847298d8a2a98f224f98c2809ec4c6b5f823bc89530f1f8ec62cbe7`
- **Judge origin:** `carried_forward_exact_record`
- **Judge provenance source:** `data/processed/phase39-final-evidence/carry.jsonl` (SHA-256 `593b34ab8eb01d817b849e26aea1022dac422d2a1ef16822ffe44f5cb24b5ea8`)
- **Judge provenance iteration:** historical exact carry
- **Historical judge coordinate:** train:292
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> [MBBANK] TK cua ban co giao dich chuyen khoan 45,000,000 VND luc 02:17 sang nay. Neu ban ko thuc hien giao dich nay, click vao day de huy ngay: mb-bank.security-alert.com/huy-gd?id=8821. Lien he hotline ky thuat: 1800.9999.02 de duoc ho tro. Vui long cung cap ma OTP khi nhan vien yeu cau de xac nhan huy lenh.

- **Label:** `bank_impersonation`
- **Risk tier:** `high-risk`
- **Suspicious spans (JSON):** ["mb-bank.security-alert.com/huy-gd?id=8821", "cung cap ma OTP khi nhan vien yeu cau", "1800.9999.02"]
- **Source:** `synthetic_claude`
- **Seed ID:** `seed_93fafa81260d`

### XAI explanation

> Tin nhắn giả mạo MB Bank dùng tên miền không chính thức và tạo áp lực giả về giao dịch lớn lúc đêm khuya để ép nạn nhân cung cấp OTP nhằm chiếm đoạt tài khoản.

- **Codex judge verdict:** PASS -- realism=5, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:**

> Detailed transaction cancellation scam explicitly requests OTP via fake technical support.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [x] PASS   [ ] FAIL

**Notes:** 
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 005/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=221
- **Record digest:** `d8353e8fde32c26aa9eb3587b3a8dc93daa098562485da137ea3e2f5bae97fa4`
- **Evidence digest:** `5bffd22632cae414bab342668b04bbc2be103a9d9ff5a0efee9ba570a79287c4`
- **Judge origin:** `carried_forward_exact_record`
- **Judge provenance source:** `data/processed/phase39-final-evidence/carry.jsonl` (SHA-256 `593b34ab8eb01d817b849e26aea1022dac422d2a1ef16822ffe44f5cb24b5ea8`)
- **Judge provenance iteration:** historical exact carry
- **Historical judge coordinate:** train:300
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> MB Bank thông báo: Smart OTP của bạn sắp hết hạn sau 24h. Để gia hạn miễn phí, tải lại app tại mbbank-update.com/app và nhập số CCCD + mã PIN hiện tại. Hotline hỗ trợ: 0398.765.432

- **Label:** `bank_impersonation`
- **Risk tier:** `high-risk`
- **Suspicious spans (JSON):** ["mbbank-update.com/app", "nhập số CCCD + mã PIN hiện tại", "Smart OTP của bạn sắp hết hạn"]
- **Source:** `synthetic_claude`
- **Seed ID:** `seed_bbd7273fd159`

### XAI explanation

> Không có ngân hàng nào yêu cầu bạn nhập CCCD và mã PIN trên website bên ngoài để 'gia hạn Smart OTP' — đây là trang giả mạo thu thập thông tin đăng nhập.

- **Codex judge verdict:** PASS -- realism=5, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:**

> Convincing fake app renewal explicitly harvests identity and PIN through a hostile site.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [x] PASS   [ ] FAIL

**Notes:** 
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 006/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=282
- **Record digest:** `5153450793a9f582d06e5c6d2c8aa0f1c0bdb31e5af9baab20f3e0b2852d6e02`
- **Evidence digest:** `64f26f36c71adc604777b4a87e8d9bf22ed4c495b784b42f27b6d10a6b3e25c7`
- **Judge origin:** `carried_forward_exact_record`
- **Judge provenance source:** `data/processed/phase39-final-evidence/carry.jsonl` (SHA-256 `593b34ab8eb01d817b849e26aea1022dac422d2a1ef16822ffe44f5cb24b5ea8`)
- **Judge provenance iteration:** historical exact carry
- **Historical judge coordinate:** train:377
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> ACB thong bao: tk cua ban vua thuc hien giao dich chuyen khoan 8,500,000d den so TK 019xxxxxxx ma ban k xac nhan. De khieu nai va lay lai tien, nhan vien ho tro se lien he ban qua Zalo: 0987.654.321 - gui CCCD 2 mat + ma OTP de chung toi xu ly gap. Xu ly trong 15p neu dc xac nhan som.

- **Label:** `bank_impersonation`
- **Risk tier:** `high-risk`
- **Suspicious spans (JSON):** ["gui CCCD 2 mat + ma OTP", "0987.654.321", "giao dich chuyen khoan 8,500,000d"]
- **Source:** `synthetic_claude`
- **Seed ID:** `seed_d87bcc048ee5`

### XAI explanation

> Yêu cầu gửi ảnh CCCD hai mặt kèm mã OTP qua Zalo là thủ đoạn thu thập đủ dữ liệu để chiếm đoạt tài khoản ngân hàng và định danh điện tử của nạn nhân.

- **Codex judge verdict:** PASS -- realism=5, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:**

> Plausible Zalo refund scam solicits identity images and OTP under transaction pressure.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [x] PASS   [ ] FAIL

**Notes:** 
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 007/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=284
- **Record digest:** `bc1ba9eaa7c03235201018e3330e12b5ffbbbdd6f82a9f5af60d8422181add2f`
- **Evidence digest:** `f15d2d5e377d787f199c88548268f3eb9d5c11ab9e8e8596b1d0f54c220c88a9`
- **Judge origin:** `fresh_final_delta`
- **Judge provenance source:** `data/processed/codex-final-delta-judge.jsonl` (SHA-256 `8c152b519ca70ac9329b382dcafd8a91f09fcc8f0ed81600cbed0e6b98b584d5`)
- **Judge provenance iteration:** 0
- **Historical judge coordinate:** none (fresh final-delta judgment)
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Chào bạn, mình là admin của ứng dụng Zing Mp3. Để nhận thưởng 100k, vui lòng truy cập link này: https://zingmp3vn.com/ va làm theo hướng dẫn. Cần đặt cọc 200k để đảm bảo tính minh bạch. Liên hệ 0987654321 nếu cần hỗ trợ. Cảm ơn!

- **Label:** `task_scam`
- **Risk tier:** `high-risk`
- **Suspicious spans (JSON):** ["https://zingmp3vn.com/", "đặt cọc 200k"]
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_10a6b28919e6`

### XAI explanation

> Đặt cọc tiền trước khi nhận thưởng có thể là dấu hiệu của lừa đảo, hãy thận trọng.

- **Codex judge verdict:** PASS -- realism=4, label_correctness=5, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:**

> Plausible reward-task solicitation; the advance deposit and disguised Zing link support the task-scam label, high risk, and both marked cues.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [x] PASS   [ ] FAIL

**Notes:** 
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 008/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=294
- **Record digest:** `18d912876e96dcc3bf71dec2c83591e58f74834941e05a0ece19ba0d5f0fc337`
- **Evidence digest:** `4cff59a99718fbc0b08484ec3873a9608e0f9d54ac4ff2a5455e5013b46d471c`
- **Judge origin:** `fresh_final_delta`
- **Judge provenance source:** `data/processed/codex-final-delta-judge.jsonl` (SHA-256 `8c152b519ca70ac9329b382dcafd8a91f09fcc8f0ed81600cbed0e6b98b584d5`)
- **Judge provenance iteration:** 1
- **Historical judge coordinate:** none (fresh final-delta judgment)
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Chào bạn, đây là bộ phận hỗ trợ kỹ thuật của CAFC. Máy tính của bạn có dấu hiệu bị virus, vui lòng liên hệ 0987654321 để được hỗ trợ. Đừng bỏ lỡ cơ hội bảo vệ tài khoản Internet Banking của mình, nha!

- **Label:** `bank_impersonation`
- **Risk tier:** `suspicious`
- **Suspicious spans (JSON):** ["0987654321", "Internet Banking"]
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_93fafa81260d`

### XAI explanation

> Cảnh báo virus dẫn người nhận tới số hỗ trợ lạ 0987654321 và gắn với tài khoản Internet Banking, có thể mở đầu cho việc thu thập thông tin tài chính.

- **Codex judge verdict:** FAIL -- realism=3, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=4, suspicious_span_accuracy=4
- **Judge reason:**

> The repaired XAI and spans now describe the strange virus callback accurately, but CAFC technical-support impersonation is still not bank impersonation.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [ ] PASS   [x] FAIL

**Notes:** Final triage: DROP
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 009/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=295
- **Record digest:** `51b649f8724ea7da59869bf374e070bb8624f235f6c0ae0366af78a6fec85a9f`
- **Evidence digest:** `0c50f66f492e1a0c8e14e549699783a8f8ec2bb761073b7f56be442a46af1819`
- **Judge origin:** `carried_forward_exact_record`
- **Judge provenance source:** `data/processed/phase39-final-evidence/carry.jsonl` (SHA-256 `593b34ab8eb01d817b849e26aea1022dac422d2a1ef16822ffe44f5cb24b5ea8`)
- **Judge provenance iteration:** historical exact carry
- **Historical judge coordinate:** train:401
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Chào bạn! Mình là quản trị viên của nhóm TikTok lớn. Bạn có muốn kiếm thêm thu nhập không? Công việc đơn giản, chỉ cần like, follow và comment trên các video TikTok. Mỗi task được trả 5k, có thể làm part-time. Để tham gia, vui lòng click vào link này: [http://tiktok-earn.com] và đăng ký tài khoản. Đừng bỏ lỡ cơ hội này, nha!

- **Label:** `task_scam`
- **Risk tier:** `suspicious`
- **Suspicious spans (JSON):** ["[http://tiktok-earn.com]"]
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_977875fab0f0`

### XAI explanation

> Đây có thể là một lừa đảo yêu cầu bạn thực hiện các task trên TikTok nhưng không trả tiền sau khi bạn hoàn thành.

- **Codex judge verdict:** FAIL -- realism=2, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=4, suspicious_span_accuracy=5
- **Judge reason:**

> Bracketed placeholder formatting makes this read like generated text, not a real message.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [ ] PASS   [x] FAIL

**Notes:** Final triage: (Drop row): Synthetic bracketed markdown URL formatting artifact ([[http://tiktok-earn.com](http://tiktok-earn.com)]).
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 010/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=307
- **Record digest:** `c243e46a6f85140e8884326a25d5075de856ac9b26e5557efd8bb1cb63e547f6`
- **Evidence digest:** `184b8a4c01907a89299ec5d3163193f0a56e28b289e4d9575949bc948b1611e7`
- **Judge origin:** `fresh_final_delta`
- **Judge provenance source:** `data/processed/codex-final-delta-judge.jsonl` (SHA-256 `8c152b519ca70ac9329b382dcafd8a91f09fcc8f0ed81600cbed0e6b98b584d5`)
- **Judge provenance iteration:** 1
- **Historical judge coordinate:** none (fresh final-delta judgment)
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Chị T ơi, đây là anh Công an phường Trung Hòa, có thông tin khẩn về tài khoản Internet Banking của chị bị kẻ gian truy cập trái phép. Để bảo mật, vui lòng đăng nhập và thay đổi mật khẩu ngay tại link này: http://bit.ly/CongAnTrungHoa. Nếu ko dc, gọi lại cho em 0334567890 nha.

- **Label:** `bank_impersonation`
- **Risk tier:** `high-risk`
- **Suspicious spans (JSON):** ["http://bit.ly/CongAnTrungHoa", "0334567890"]
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_d41d9b30081a`

### XAI explanation

> Không click vào link hoặc gọi số điện thoại lạ khi nhận được tin nhắn yêu cầu thay đổi mật khẩu tài khoản ngân hàng.

- **Codex judge verdict:** FAIL -- realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=3
- **Judge reason:**

> The high-risk link and callback are credible and accurately marked, but the sender explicitly impersonates police rather than a bank.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [ ] PASS   [x] FAIL

**Notes:** Final triage: (Relabel label): Mislabeled as bank_impersonation; relabel to zalo_social_engineering (police authority impersonation credential phishing; keep high-risk).
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 011/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=308
- **Record digest:** `b9d9c88eb35d68e03b138356dc16eab8a954b9e715df934dd6ccede6d266e258`
- **Evidence digest:** `e8dea7d002c15dfd0d6099aaf11065e40d2e0f2c4c7dd7c8cee630159ec4b050`
- **Judge origin:** `fresh_final_delta`
- **Judge provenance source:** `data/processed/codex-final-delta-judge.jsonl` (SHA-256 `8c152b519ca70ac9329b382dcafd8a91f09fcc8f0ed81600cbed0e6b98b584d5`)
- **Judge provenance iteration:** 1
- **Historical judge coordinate:** none (fresh final-delta judgment)
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Chào bạn, tài khoản Internet Banking của bạn đang có dấu hiệu bất thường. Vui lòng click vào link này để xác nhận thông tin: http://vcbank.com.vn/verify. Nếu không, tài khoản sẽ bị khóa ngay lập tức. Cảm ơn!

- **Label:** `bank_impersonation`
- **Risk tier:** `high-risk`
- **Suspicious spans (JSON):** ["http://vcbank.com.vn/verify"]
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_d87bcc048ee5`

### XAI explanation

> Hãy cẩn thận với các link lạ và không nên click vào nếu không chắc chắn về nguồn gốc.

- **Codex judge verdict:** PASS -- realism=4, label_correctness=5, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:**

> The account-lock threat directs Internet Banking users to a lookalike verification host, supporting bank impersonation, high risk, and the repaired URL cue.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [x] PASS   [ ] FAIL

**Notes:** 
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 012/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=309
- **Record digest:** `b61485d662022fc9d107850ce27f827f21ab00ea47c4622a9e6eb0982e53949d`
- **Evidence digest:** `e776cf8632137cebd776a0d8a7baa7f636726f3d36293bba3da3bfab953d2497`
- **Judge origin:** `fresh_final_delta`
- **Judge provenance source:** `data/processed/codex-final-delta-judge.jsonl` (SHA-256 `8c152b519ca70ac9329b382dcafd8a91f09fcc8f0ed81600cbed0e6b98b584d5`)
- **Judge provenance iteration:** 1
- **Historical judge coordinate:** none (fresh final-delta judgment)
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Chào anh, em là Thu từ bộ phận Hỗ trợ Khách hàng của Paychex. Chúng tôi phát hiện có hoạt động đáng ngờ trên tài khoản Internet Banking của anh. Vui lòng xác minh OTP để bảo vệ tài khoản: http://paychex.vn/verifyotp. Cảm ơn anh, nha!

- **Label:** `bank_impersonation`
- **Risk tier:** `high-risk`
- **Suspicious spans (JSON):** ["xác minh OTP", "http://paychex.vn/verifyotp"]
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_db9fb32e2681`

### XAI explanation

> Tin nhắn Paychex thúc giục xác minh OTP qua đường dẫn paychex.vn/verifyotp, có thể làm lộ mã xác thực và quyền truy cập tài khoản.

- **Codex judge verdict:** FAIL -- realism=3, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:**

> The new OTP and URL spans correctly capture high-risk credential theft, but Paychex payroll support is not a bank identity.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [ ] PASS   [x] FAIL

**Notes:** Final triage: DROP
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 013/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=317
- **Record digest:** `cb06c431eb40f317b6fc6e2c1f5f3cf985b6ac39726f9f0cddd73d41f8696618`
- **Evidence digest:** `aa4ac464b89074ece9aacabb3f8d797a190f84e26affc21790c0979e04c928c3`
- **Judge origin:** `fresh_final_delta`
- **Judge provenance source:** `data/processed/codex-final-delta-judge.jsonl` (SHA-256 `8c152b519ca70ac9329b382dcafd8a91f09fcc8f0ed81600cbed0e6b98b584d5`)
- **Judge provenance iteration:** 1
- **Historical judge coordinate:** none (fresh final-delta judgment)
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Xin chào, tài khoản ngân hàng của bạn cần xác minh OTP. Vui lòng nhập mã OTP nhận được vào app của chúng tôi tại đây: http://verifyotp.com. Nếu ko thấy mã, gọi 0987654321. Thanks!

- **Label:** `bank_impersonation`
- **Risk tier:** `high-risk`
- **Suspicious spans (JSON):** ["Vui lòng nhập mã OTP nhận được vào app của chúng tôi tại đây", "http://verifyotp.com", "0987654321"]
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_61a36fbd3ece`

### XAI explanation

> Không nên cung cấp OTP cho bất kỳ ai và hãy liên hệ ngân hàng chính thức nếu nghi ngờ.

- **Codex judge verdict:** PASS -- realism=4, label_correctness=5, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:**

> The message sends a bank customer to an outside app page to enter OTP and provides a callback; repaired tier, spans, label, and XAI are consistent.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [x] PASS   [ ] FAIL

**Notes:** 
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 014/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=325
- **Record digest:** `6d252f91b21ff7c7f272111420768a4b9d2e9198877ebaa851f3e9b8feac01ec`
- **Evidence digest:** `8a6c82467a787efcc51e9e8a37d162bbd45fa5d8801f22a8ffc5620b4ab8a41d`
- **Judge origin:** `fresh_final_delta`
- **Judge provenance source:** `data/processed/codex-final-delta-judge.jsonl` (SHA-256 `8c152b519ca70ac9329b382dcafd8a91f09fcc8f0ed81600cbed0e6b98b584d5`)
- **Judge provenance iteration:** 1
- **Historical judge coordinate:** none (fresh final-delta judgment)
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Xin chào, có vẻ như tài khoản của bạn đang gặp sự cố. Vui lòng cập nhật thông tin tài khoản qua app bằng cách click vào link này: http://update-account.com. Liên hệ 19001234 nếu cần hỗ trợ. ĐT Ngân hàng.

- **Label:** `bank_impersonation`
- **Risk tier:** `high-risk`
- **Suspicious spans (JSON):** ["http://update-account.com"]
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_85009090b32e`

### XAI explanation

> Hãy gọi trực tiếp cho ngân hàng để xác nhận thông tin trước khi nhấp vào bất kỳ liên kết nào.

- **Codex judge verdict:** PASS -- realism=3, label_correctness=4, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:**

> A generic bank sign-off pushes an account update through an unrelated domain; the external credential route justifies high risk and the URL span.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [x] PASS   [ ] FAIL

**Notes:** 
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 015/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=345
- **Record digest:** `973bb595f2605b9693c45f51a0ebe8b4c3b5bf681b5381cb173cc01f85832abb`
- **Evidence digest:** `a9f20ab80af3fbab34e306499be3d79d795f9791395a5d9d9d4549f80ab3c203`
- **Judge origin:** `fresh_final_delta`
- **Judge provenance source:** `data/processed/codex-final-delta-judge.jsonl` (SHA-256 `8c152b519ca70ac9329b382dcafd8a91f09fcc8f0ed81600cbed0e6b98b584d5`)
- **Judge provenance iteration:** 0
- **Historical judge coordinate:** none (fresh final-delta judgment)
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Bạn ơi, mình là bot của Binance. Hiện tại, chúng tôi có chương trình khuyến mãi, bạn chỉ cần đăng ký qua link này: http://binance-fake.com và giới thiệu bạn bè. Mỗi người đăng ký thành công, bạn sẽ nhận 5% hoa hồng. Để rút tiền, bạn cần trả phí xác minh 100k. Đừng bỏ lỡ cơ hội này nha!

- **Label:** `task_scam`
- **Risk tier:** `high-risk`
- **Suspicious spans (JSON):** ["http://binance-fake.com", "trả phí xác minh 100k"]
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_441f08e9ca28`

### XAI explanation

> Bot yêu cầu bạn đăng ký và giới thiệu người khác, nhưng sau đó sẽ yêu cầu phí xác minh và không cho rút tiền.

- **Codex judge verdict:** PASS -- realism=4, label_correctness=5, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:**

> A fake Binance bot couples referral commissions with a fee needed to withdraw, so task scam, high-risk, the domain, and the 100k fee all align.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [ ] PASS   [x] FAIL

**Notes:** Final triage: (Drop row): Literal synthetic placeholder domain (`binance-fake.com`) undermines real-world plausibility.
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 016/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=362
- **Record digest:** `b64e7c2c0efdc8b58617f378bc0ee2c1c96f93b2279e5c0cfc9f5c8c922d569e`
- **Evidence digest:** `3c84b3cfd0c0be75ac2316e9ac623957753f0afdb91816d499ab2ce5385429cd`
- **Judge origin:** `fresh_final_delta`
- **Judge provenance source:** `data/processed/codex-final-delta-judge.jsonl` (SHA-256 `8c152b519ca70ac9329b382dcafd8a91f09fcc8f0ed81600cbed0e6b98b584d5`)
- **Judge provenance iteration:** 0
- **Historical judge coordinate:** none (fresh final-delta judgment)
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Chào bạn! Mình là bot của Binance. Đang có chương trình khuyến mãi: đăng ký qua link này [fake URL] và giới thiệu bạn bè, bạn sẽ nhận 20% hoa hồng từ giao dịch của họ. Để xác minh tài khoản, bạn cần chuyển 500k vào địa chỉ ví [địa chỉ ví]. Sau khi xác minh, bạn có thể rút tiền bất kỳ lúc nào. Liên hệ [số điện thoại] nếu cần hỗ trợ.

- **Label:** `task_scam`
- **Risk tier:** `high-risk`
- **Suspicious spans (JSON):** ["[fake URL]", "[địa chỉ ví]", "[số điện thoại]", "chuyển 500k vào địa chỉ ví [địa chỉ ví]"]
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_b81d209eb87e`

### XAI explanation

> Lừa đảo yêu cầu chuyển tiền để xác minh tài khoản trên nền tảng crypto.

- **Codex judge verdict:** FAIL -- realism=2, label_correctness=5, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:**

> The crypto referral scam and 500k wallet transfer are semantically correct, but three bracketed placeholders make the record look like a generation template.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [ ] PASS   [x] FAIL

**Notes:** Final triage: (Drop row): Unrealistic synthetic generation template containing bracketed placeholders (`[fake URL]`, `[địa chỉ ví]`, `[số điện thoại]`).
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 017/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=364
- **Record digest:** `195f0d4240dce933cbfd37ab094c6e327e0aa7424a26289315c591500e7c6c19`
- **Evidence digest:** `56bcbb8ae56e469e527161f6b2f7ff75726e12b8b94e30c26d5778c485aa7d8a`
- **Judge origin:** `carried_forward_exact_record`
- **Judge provenance source:** `data/processed/phase39-final-evidence/carry.jsonl` (SHA-256 `593b34ab8eb01d817b849e26aea1022dac422d2a1ef16822ffe44f5cb24b5ea8`)
- **Judge provenance iteration:** historical exact carry
- **Historical judge coordinate:** train:504
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Chào bạn, mình là admin của nhóm TikTok lớn. Chúng tôi đang cần người like, follow, comment trên các video TikTok. Mỗi nhiệm vụ chỉ 1k VND, thanh toán qua Momo sau mỗi 100 nhiệm vụ. Bạn quan tâm thì liên hệ mình qua Zalo 0987654321 hoặc nhấn link này để đăng ký: http://bit.ly/tiktokjob. Chúc bạn một ngày tốt lành!

- **Label:** `task_scam`
- **Risk tier:** `suspicious`
- **Suspicious spans (JSON):** ["http://bit.ly/tiktokjob", "0987654321"]
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_bbd7273fd159`

### XAI explanation

> Đây có thể là một hình thức lừa đảo yêu cầu bạn thực hiện các nhiệm vụ trên TikTok nhưng không bao giờ trả tiền.

- **Codex judge verdict:** PASS -- realism=4, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=4, suspicious_span_accuracy=5
- **Judge reason:**

> Credible low-paid TikTok task recruitment with shortened link and Zalo contact.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [x] PASS   [ ] FAIL

**Notes:** 
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 018/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=376
- **Record digest:** `a446ea35ea04b4bfc421fba200b1062262b88325513d8264e41a1bc851883e34`
- **Evidence digest:** `4415ddc1751b32516afdaa4cddc33f751d9b141ac7bbd04d13af011b26a225dc`
- **Judge origin:** `fresh_final_delta`
- **Judge provenance source:** `data/processed/codex-final-delta-judge.jsonl` (SHA-256 `8c152b519ca70ac9329b382dcafd8a91f09fcc8f0ed81600cbed0e6b98b584d5`)
- **Judge provenance iteration:** 0
- **Historical judge coordinate:** none (fresh final-delta judgment)
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Xin chào, mình là người quản lý của shop online. Shop đang cần người đặt đơn hàng ảo để tăng xếp hạng. Mỗi đơn hàng bạn đặt sẽ được trả 10k. Bạn chỉ cần thanh toán và gửi mã đơn hàng cho mình. Link shop: http://order-boosting.vn. Nếu quan tâm, liên hệ qua Zalo 0123456789. 🛍️

- **Label:** `task_scam`
- **Risk tier:** `high-risk`
- **Suspicious spans (JSON):** ["http://order-boosting.vn", "0123456789", "thanh toán và gửi mã đơn hàng cho mình"]
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_626f3be47e76`

### XAI explanation

> Đây có thể là lừa đảo vì nó yêu cầu bạn đặt hàng ảo và thanh toán trước nhưng không đảm bảo việc nhận tiền hoa hồng.

- **Codex judge verdict:** PASS -- realism=4, label_correctness=5, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:**

> The order-boosting offer requires payment and proof through an outside shop and Zalo contact, matching a high-risk task scam with complete actionable spans.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [ ] PASS   [x] FAIL

**Notes:** Final triage: (Drop row): Contains obvious sequential synthetic placeholder phone number (`0123456789`).
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 019/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=386
- **Record digest:** `b1ae4a4590012213990d903e69e1b3dbe021292a23b88c48a864569d0dd4425b`
- **Evidence digest:** `9ce8bf6f81a4e498263b4f77c98f3b5bedc602f0fa72e41739ab49ae205e938c`
- **Judge origin:** `fresh_final_delta`
- **Judge provenance source:** `data/processed/codex-final-delta-judge.jsonl` (SHA-256 `8c152b519ca70ac9329b382dcafd8a91f09fcc8f0ed81600cbed0e6b98b584d5`)
- **Judge provenance iteration:** 1
- **Historical judge coordinate:** none (fresh final-delta judgment)
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Chào bạn, đây là thông báo từ ngân hàng ACB. Bạn vừa nhận được 850 điểm thưởng tương ứng với 127 triệu đồng từ chương trình tham gia bình chọn. Để nhận thưởng, vui lòng đăng nhập vào tài khoản [Internet Banking] của bạn và làm theo hướng dẫn. Nếu cần hỗ trợ, hãy gọi 19001234. AK

- **Label:** `bank_impersonation`
- **Risk tier:** `suspicious`
- **Suspicious spans (JSON):** ["đăng nhập vào tài khoản [Internet Banking] của bạn", "19001234"]
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_b2c9477c611a`

### XAI explanation

> Giải thưởng phi lý được dùng để thúc giục đăng nhập Internet Banking và gọi số 19001234; người nhận cần xác minh trực tiếp với ACB.

- **Codex judge verdict:** FAIL -- realism=2, label_correctness=4, code_switch_naturalness=3, risk_tier_correctness=4, suspicious_span_accuracy=4
- **Judge reason:**

> The repaired spans and XAI now cover the banking login lure, but 850 points supposedly worth 127 million remains conspicuously implausible template content.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [ ] PASS   [x] FAIL

**Notes:** Final triage: (Drop row): Synthetic bracketed text formatting (`[Internet Banking]`) and absurdly implausible reward numbers (850 points = 127 million VND).
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 020/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=388
- **Record digest:** `fa728cb33d5d5cec26ea13bcc02a0fcef2e17b10109b8aea10ddd141d6c422a9`
- **Evidence digest:** `9f1020380c9a798bfa5e3a43959c24eaa2baaaebf993bcd41d16756d9d1b7f24`
- **Judge origin:** `fresh_final_delta`
- **Judge provenance source:** `data/processed/codex-final-delta-judge.jsonl` (SHA-256 `8c152b519ca70ac9329b382dcafd8a91f09fcc8f0ed81600cbed0e6b98b584d5`)
- **Judge provenance iteration:** 0
- **Historical judge coordinate:** none (fresh final-delta judgment)
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Chào bạn, mình là đại diện của Binance. Chúng tôi đang có chương trình khuyến mãi: bạn đăng ký qua link này [fake-link] và giới thiệu bạn bè, bạn sẽ nhận được 5% hoa hồng từ mỗi giao dịch. Để kích hoạt tài khoản, bạn cần chuyển 100k phí xác minh. OTP: [123456].

- **Label:** `task_scam`
- **Risk tier:** `high-risk`
- **Suspicious spans (JSON):** ["[fake-link]", "[123456]", "chuyển 100k phí xác minh"]
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_b6e080de275b`

### XAI explanation

> Không nên chuyển tiền hoặc cung cấp OTP cho bất kỳ ai yêu cầu kích hoạt tài khoản trên nền tảng đầu tư.

- **Codex judge verdict:** FAIL -- realism=2, label_correctness=5, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:**

> The advance-fee referral scam is labeled and spanned correctly, but [fake-link] and bracketed OTP [123456] are obvious construction placeholders.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [ ] PASS   [x] FAIL

**Notes:** Final triage: (Drop row): Obvious synthetic placeholder artifacts (`[fake-link]` and `[123456]`).
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 021/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=415
- **Record digest:** `0f9ca920b1cb5ef5f8d8212eabd0a91cb69dc18f8e0dc246a18206b08cb0cc97`
- **Evidence digest:** `15f74a4fac5e2f3be51139535ac7b7de5aa43fbefb78946b3a9c9c1f4b61ce64`
- **Judge origin:** `fresh_final_delta`
- **Judge provenance source:** `data/processed/codex-final-delta-judge.jsonl` (SHA-256 `8c152b519ca70ac9329b382dcafd8a91f09fcc8f0ed81600cbed0e6b98b584d5`)
- **Judge provenance iteration:** 0
- **Historical judge coordinate:** none (fresh final-delta judgment)
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Xin chào, mình là nhân viên hỗ trợ của ứng dụng ZaloPay. Hiện tại, tài khoản của bạn có vấn đề cần xác minh. Vui lòng liên hệ với chúng tôi qua số điện thoại 0912345678 để được hỗ trợ. Đừng lo lắng, nha!

- **Label:** `bank_impersonation`
- **Risk tier:** `suspicious`
- **Suspicious spans (JSON):** ["0912345678"]
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_bfe4a6bbd16d`

### XAI explanation

> Số điện thoại này có thể là của kẻ lừa đảo, hãy cẩn thận và không chia sẻ thông tin cá nhân.

- **Codex judge verdict:** PASS -- realism=4, label_correctness=3, code_switch_naturalness=4, risk_tier_correctness=4, suspicious_span_accuracy=4
- **Judge reason:**

> ZaloPay is a wallet rather than a bank, but under the four-class taxonomy its account-support impersonation is a defensible financial-impersonation fit; the callback cue is clear.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [ ] PASS   [x] FAIL

**Notes:** Final triage: (Drop row): Contains an obvious sequential dummy phone number (`0912345678`) and wallet service (ZaloPay) is misaligned with strict bank impersonation.
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 022/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=419
- **Record digest:** `b7cad1fd22dbaa9557e638c2a7a0098256a597df345423cfc728d61cdbbaeb07`
- **Evidence digest:** `74728415a34c54853a48b58caa57e73292520cfdf3bd7712efc65997608ed868`
- **Judge origin:** `fresh_final_delta`
- **Judge provenance source:** `data/processed/codex-final-delta-judge.jsonl` (SHA-256 `8c152b519ca70ac9329b382dcafd8a91f09fcc8f0ed81600cbed0e6b98b584d5`)
- **Judge provenance iteration:** 0
- **Historical judge coordinate:** none (fresh final-delta judgment)
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Chào anh, đây là chị Hằng, quản lý tài khoản BIDV. Có người đang cố truy cập trái phép vào tài khoản của anh. Anh vui lòng đăng nhập vào app và đổi mật khẩu ngay, tránh mất tiền. Cảm ơn anh.

- **Label:** `bank_impersonation`
- **Risk tier:** `suspicious`
- **Suspicious spans (JSON):** []
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_d41d9b30081a`

### XAI explanation

> Kiểm tra nguồn gốc tin nhắn và không thực hiện thao tác ngay nếu chưa chắc chắn.

- **Codex judge verdict:** FAIL -- realism=3, label_correctness=2, code_switch_naturalness=5, risk_tier_correctness=2, suspicious_span_accuracy=1
- **Judge reason:**

> This only tells the user to open the official BIDV app and change a password, with no link, callback, or credential-sharing request; empty spans confirm there is no clear scam cue.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [ ] PASS   [x] FAIL

**Notes:** Final triage: (Drop row): Non-malicious text that directs the user to the official bank app with no phishing payload, link, or data harvesting, resulting in empty suspicious spans.
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 023/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=420
- **Record digest:** `6efe0bd76f1707bc5782d1c860e26d88ac70149f7a4ecf602e02b2ff71b735de`
- **Evidence digest:** `da2d443dd8e6b5ed50c6a07359b12812b8f5e4685e92dcac6ae716ae0e058a19`
- **Judge origin:** `fresh_final_delta`
- **Judge provenance source:** `data/processed/codex-final-delta-judge.jsonl` (SHA-256 `8c152b519ca70ac9329b382dcafd8a91f09fcc8f0ed81600cbed0e6b98b584d5`)
- **Judge provenance iteration:** 1
- **Historical judge coordinate:** none (fresh final-delta judgment)
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Anh/chị ơi, em là nhân viên của Shopee, có đơn hàng của anh/chị đang gặp vấn đề. Vui lòng kiểm tra OTP gửi về số điện thoại 0987654321 để xác nhận. Cảm ơn anh/chị nha.

- **Label:** `bank_impersonation`
- **Risk tier:** `high-risk`
- **Suspicious spans (JSON):** ["kiểm tra OTP gửi về số điện thoại 0987654321 để xác nhận", "0987654321"]
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_d87bcc048ee5`

### XAI explanation

> Không cung cấp OTP cho bất kỳ ai và kiểm tra trực tiếp với Shopee nếu cần.

- **Codex judge verdict:** FAIL -- realism=3, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=4, suspicious_span_accuracy=4
- **Judge reason:**

> The repaired OTP phrase supports elevated risk, but the sender explicitly impersonates Shopee support rather than a bank.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [ ] PASS   [x] FAIL

**Notes:** Final triage: DROP
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 024/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=433
- **Record digest:** `a4a822edf4a30476d95f5b15906a8f28a158245f54c68d04a25b41a0269c2d83`
- **Evidence digest:** `2977965f6a1f3cae12a3237ca220d0a3c74ac127909d9aea424a53b558c49679`
- **Judge origin:** `fresh_final_delta`
- **Judge provenance source:** `data/processed/codex-final-delta-judge.jsonl` (SHA-256 `8c152b519ca70ac9329b382dcafd8a91f09fcc8f0ed81600cbed0e6b98b584d5`)
- **Judge provenance iteration:** 1
- **Historical judge coordinate:** none (fresh final-delta judgment)
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Chào bạn, bạn vừa nhận được mã OTP 123456 từ Ngân hàng ABC. Vui lòng nhập mã này vào ứng dụng của chúng tôi để xác minh giao dịch. Nếu bạn không yêu cầu giao dịch này, vui lòng liên hệ với chúng tôi ngay lập tức.

- **Label:** `benign`
- **Risk tier:** `benign`
- **Suspicious spans (JSON):** []
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_bfe4a6bbd16d`

### XAI explanation

> Tin nhắn cung cấp OTP cho một giao dịch và hướng dẫn liên hệ nếu người nhận không yêu cầu; mã chỉ nên dùng trong ứng dụng chính thức và không chia sẻ.

- **Codex judge verdict:** PASS -- realism=4, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:**

> This resembles a routine bank OTP notification that directs entry only in the app and advises contact for an unknown transaction; benign fields are now coherent.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [x] PASS   [ ] FAIL

**Notes:** 
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 025/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=437
- **Record digest:** `a2bc24f77ef861d2a4784a11184dfc112c9218f0dee760166c4ba715bee0b893`
- **Evidence digest:** `07da809263f930a92e3628d7e685b02beb78d746f9b360dd390d46a6c530baf9`
- **Judge origin:** `fresh_final_delta`
- **Judge provenance source:** `data/processed/codex-final-delta-judge.jsonl` (SHA-256 `8c152b519ca70ac9329b382dcafd8a91f09fcc8f0ed81600cbed0e6b98b584d5`)
- **Judge provenance iteration:** 0
- **Historical judge coordinate:** none (fresh final-delta judgment)
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Xin chào, mình là Zalo contact của shop Shopee. Shop đang cần người giúp mua hàng và viết đánh giá 5 sao. Mỗi đơn hàng bạn sẽ nhận được hoàn tiền 100% + 10% hoa hồng. Để tham gia, bạn vui lòng chuyển khoản 100k vào số tài khoản sau: 123456789. Sau khi xác nhận, shop sẽ hoàn lại tiền cho bạn. Liên hệ mình nếu có thắc mắc nha! 🛍️

- **Label:** `task_scam`
- **Risk tier:** `high-risk`
- **Suspicious spans (JSON):** ["100%", "10% hoa hồng", "100k", "chuyển khoản 100k vào số tài khoản sau: 123456789"]
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_61a36fbd3ece`

### XAI explanation

> Hãy cẩn thận với các yêu cầu chuyển khoản trước khi nhận công việc. Đảm bảo rằng bạn hiểu rõ quy trình hoàn tiền.

- **Codex judge verdict:** FAIL -- realism=3, label_correctness=5, code_switch_naturalness=2, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:**

> The advance-payment review scam is clear, but 'mình là Zalo contact của shop' is forced English-Vietnamese mixing that a natural Vietnamese solicitation would not use.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [ ] PASS   [x] FAIL

**Notes:** Final triage: (Drop row): Unnatural English-Vietnamese code-switching ("Zalo contact của shop") and sequential synthetic account placeholder (`123456789`).
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 026/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=446
- **Record digest:** `62c03803b2ad9de88e9d87d027b9e7b5f6529dcc8379d99471414e7334eba206`
- **Evidence digest:** `0ad2ddaaeac232f25a7cd5b272070d60aa1cef499dc75355ebe0fa87aaeb46a2`
- **Judge origin:** `fresh_final_delta`
- **Judge provenance source:** `data/processed/codex-final-delta-judge.jsonl` (SHA-256 `8c152b519ca70ac9329b382dcafd8a91f09fcc8f0ed81600cbed0e6b98b584d5`)
- **Judge provenance iteration:** 0
- **Historical judge coordinate:** none (fresh final-delta judgment)
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Xin chào, mình là bot từ Binance @binancevn. Bạn có thể kiếm tiền bằng cách giới thiệu bạn bè đăng ký trên nền tảng của chúng tôi qua link này: http://example.com/binance. Mỗi người đăng ký thành công, bạn sẽ nhận được hoa hồng 5%. Để kích hoạt tài khoản, vui lòng chuyển 100k qua số tài khoản 123456789. Chúng tôi sẽ xác nhận sau khi nhận thanh toán.

- **Label:** `task_scam`
- **Risk tier:** `high-risk`
- **Suspicious spans (JSON):** ["@binancevn", "http://example.com/binance", "chuyển 100k"]
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_369e01c8527a`

### XAI explanation

> Hãy cẩn thận với các đề nghị kiếm tiền qua việc giới thiệu người dùng, đặc biệt khi yêu cầu chuyển khoản để kích hoạt tài khoản.

- **Codex judge verdict:** FAIL -- realism=2, label_correctness=5, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=4
- **Judge reason:**

> The referral and activation-transfer mechanics are valid task-scam signals, but example.com is an unmistakable placeholder domain rather than a realistic attack link.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [ ] PASS   [x] FAIL

**Notes:** Final triage: (Drop row): Obvious synthetic placeholder domain (`example.com`) and sequential dummy account number (`123456789`).
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 027/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=450
- **Record digest:** `fda393bee583d991d7f207afb55e18e194b8e27be610dfaec55c0ade77ae7744`
- **Evidence digest:** `975cb09f12b921363b58bb969678ba90a0808d92bc984d9d4ee39eba54960304`
- **Judge origin:** `fresh_final_delta`
- **Judge provenance source:** `data/processed/codex-final-delta-judge.jsonl` (SHA-256 `8c152b519ca70ac9329b382dcafd8a91f09fcc8f0ed81600cbed0e6b98b584d5`)
- **Judge provenance iteration:** 1
- **Historical judge coordinate:** none (fresh final-delta judgment)
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Chào bạn, có vẻ như tài khoản của bạn đang bị tấn công. Vui lòng xác nhận thông tin bằng cách gọi 0987654321 và cung cấp mã OTP. Nếu ko, hãy liên hệ 19001234 để được hỗ trợ. Cảm ơn!

- **Label:** `bank_impersonation`
- **Risk tier:** `high-risk`
- **Suspicious spans (JSON):** ["gọi 0987654321 và cung cấp mã OTP", "19001234"]
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_93fafa81260d`

### XAI explanation

> Không chia sẻ mã OTP qua điện thoại, hãy liên hệ trực tiếp với ngân hàng nếu cần xác minh.

- **Codex judge verdict:** PASS -- realism=4, label_correctness=5, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:**

> An account-attack pretext directs the victim to call and disclose OTP; the repaired tier and full credential/callback spans accurately express high-risk financial impersonation.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [x] PASS   [ ] FAIL

**Notes:** 
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 028/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=453
- **Record digest:** `711c891a572bcf4966b8a60de5f0ca2128c087b663715fb6f6c4927c1fefcf45`
- **Evidence digest:** `447bca6101da0ef9653fe3916ddcc5ef80405522eb6dc1490f734ffbc2bfd49d`
- **Judge origin:** `fresh_final_delta`
- **Judge provenance source:** `data/processed/codex-final-delta-judge.jsonl` (SHA-256 `8c152b519ca70ac9329b382dcafd8a91f09fcc8f0ed81600cbed0e6b98b584d5`)
- **Judge provenance iteration:** 1
- **Historical judge coordinate:** none (fresh final-delta judgment)
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Xin chào, mình là quản lý dự án từ công ty ABC. Chúng tôi đang tuyển dụng vị trí Kế toán viên với mức lương hấp dẫn. Vui lòng gửi CV của bạn đến email tuyen.dung@abc.com.vn để được xem xét. Cơ hội tuyệt vời, ak!

- **Label:** `benign`
- **Risk tier:** `benign`
- **Suspicious spans (JSON):** []
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_bfe4a6bbd16d`

### XAI explanation

> Lời mời tuyển dụng chỉ yêu cầu gửi CV tới địa chỉ tuyen.dung@abc.com.vn cùng miền với công ty; người nhận vẫn nên xác minh nhà tuyển dụng trước khi gửi hồ sơ.

- **Codex judge verdict:** PASS -- realism=3, label_correctness=5, code_switch_naturalness=3, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:**

> Aside from a stray informal 'ak', this is an ordinary matching-domain recruitment invitation; benign risk, empty spans, and cautious XAI are now consistent.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [x] PASS   [ ] FAIL

**Notes:** 
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 029/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=456
- **Record digest:** `6eb4bbcf19a775fddfe3b9568b8bf437d024e149d49abbaf96b12002307630d6`
- **Evidence digest:** `d065a3fc62c68b3deecccfc59862a3a6df1dca874f9984cf8a23a5a9f8156372`
- **Judge origin:** `fresh_final_delta`
- **Judge provenance source:** `data/processed/codex-final-delta-judge.jsonl` (SHA-256 `8c152b519ca70ac9329b382dcafd8a91f09fcc8f0ed81600cbed0e6b98b584d5`)
- **Judge provenance iteration:** 0
- **Historical judge coordinate:** none (fresh final-delta judgment)
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Chào bạn, mình đang quản lý một nhóm Zalo chuyên livestream bán hàng. Chúng tôi cần người giúp đặt đơn hàng ảo để tăng tương tác. Mỗi đơn hàng ảo sẽ được trả 50k. Bạn vui lòng chuyển khoản 100k để kích hoạt tài khoản, sau đó sẽ được hướng dẫn chi tiết. Liên hệ: 0987654321. - Quản Lý Zalo Livestream

- **Label:** `task_scam`
- **Risk tier:** `high-risk`
- **Suspicious spans (JSON):** ["0987654321", "chuyển khoản 100k để kích hoạt tài khoản"]
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_db9fb32e2681`

### XAI explanation

> Yêu cầu chuyển khoản trước để kích hoạt tài khoản, sau đó mới hướng dẫn làm nhiệm vụ, có thể là lừa đảo.

- **Codex judge verdict:** PASS -- realism=4, label_correctness=5, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:**

> The livestream sales task requires 100k activation money before guidance, with the transfer and telephone cues correctly supporting a high-risk task scam.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [x] PASS   [ ] FAIL

**Notes:** 
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 030/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=463
- **Record digest:** `71e2265c25dba5ffebd1a65287fb3b2f66b67eaa70a9abf27f3ff66f54c1b4fa`
- **Evidence digest:** `3fd88569467dd8b795609047cba0f7c2017b4b8f791419b1a450668079f7c924`
- **Judge origin:** `carried_forward_exact_record`
- **Judge provenance source:** `data/processed/phase39-final-evidence/carry.jsonl` (SHA-256 `593b34ab8eb01d817b849e26aea1022dac422d2a1ef16822ffe44f5cb24b5ea8`)
- **Judge provenance iteration:** historical exact carry
- **Historical judge coordinate:** train:675
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Chào bạn, mình là quản trị viên của nhóm TikTok. Hiện tại chúng tôi đang cần người like, follow và comment trên các video để tăng tương tác. Bạn sẽ được trả 5k cho mỗi task hoàn thành. Nếu quan tâm, vui lòng đăng ký qua link: http://tiktokjobs.vn/ nha. Đảm bảo uy tín và thanh toán nhanh chóng ak!

- **Label:** `task_scam`
- **Risk tier:** `suspicious`
- **Suspicious spans (JSON):** ["http://tiktokjobs.vn/", "5k", "task"]
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_85009090b32e`

### XAI explanation

> Bạn nên cẩn thận với các lời mời like, follow, comment trên TikTok vì chúng thường yêu cầu thực hiện nhiều task nhưng không thanh toán như cam kết.

- **Codex judge verdict:** PASS -- realism=4, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=4, suspicious_span_accuracy=4
- **Judge reason:**

> Mẫu tuyển task rõ, dù các span 5k và task hơi rộng.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [x] PASS   [ ] FAIL

**Notes:** 
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 031/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=472
- **Record digest:** `3c1f3a51fa5e5160a38c3577dbb02dabdd23beeb5c239e26f423eea8e074f623`
- **Evidence digest:** `63d58b0f646caecbcaa23a44b6b36e40271bd4a6d5d5b5e22d0732205a6445d4`
- **Judge origin:** `carried_forward_exact_record`
- **Judge provenance source:** `data/processed/phase39-final-evidence/carry.jsonl` (SHA-256 `593b34ab8eb01d817b849e26aea1022dac422d2a1ef16822ffe44f5cb24b5ea8`)
- **Judge provenance iteration:** historical exact carry
- **Historical judge coordinate:** train:686
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Bạn ơi, mình đang cần người đặt đơn hàng ảo trên Shopee để tăng rating. Bạn chỉ cần đặt 1 đơn hàng 200k, sau đó mình sẽ hoàn lại 100% tiền và trả thêm 20k hoa hồng. Đặt hàng qua link này: https://shopeevn.com/offer. Nhớ xác nhận đã nhận hàng và đánh giá 5 sao nhé. Gọi mình 0987654321 nếu có thắc mắc.

- **Label:** `task_scam`
- **Risk tier:** `suspicious`
- **Suspicious spans (JSON):** ["https://shopeevn.com/offer", "0987654321"]
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_10a6b28919e6`

### XAI explanation

> Cẩn thận với các yêu cầu đặt hàng ảo trên sàn thương mại điện tử, vì bạn có thể mất tiền mà không được hoàn lại.

- **Codex judge verdict:** PASS -- realism=5, label_correctness=5, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:**

> Đơn ảo hoàn tiền qua link giả là nhiệm vụ lừa đảo rõ.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [ ] PASS   [x] FAIL

**Notes:** Final triage: drop
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 032/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=475
- **Record digest:** `a0972dc9180c324881f62be3a789e141485c6e4b16cefb1f0962ec75384d64d2`
- **Evidence digest:** `80f4b95cb02cec67ae62ae1698a9457e9ed1703edcf96a1109979af195e2baf7`
- **Judge origin:** `carried_forward_exact_record`
- **Judge provenance source:** `data/processed/phase39-final-evidence/carry.jsonl` (SHA-256 `593b34ab8eb01d817b849e26aea1022dac422d2a1ef16822ffe44f5cb24b5ea8`)
- **Judge provenance iteration:** historical exact carry
- **Historical judge coordinate:** train:691
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Xin chào, mình là quản lý của cửa hàng online trên Shopee. Bạn có muốn kiếm tiền bằng cách mua sản phẩm, đánh giá 5 sao và nhận hoàn tiền cộng hoa hồng 10% không? Liên hệ qua app Shopee để biết thêm chi tiết. Hãy đăng ký ngay, cơ hội này rất hiếm nha!

- **Label:** `task_scam`
- **Risk tier:** `suspicious`
- **Suspicious spans (JSON):** ["hoàn tiền cộng hoa hồng 10%", "app Shopee"]
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_44fbafb85650`

### XAI explanation

> Thông điệp này có thể là lừa đảo vì nó hứa hẹn hoàn tiền và hoa hồng sau khi bạn mua sản phẩm, nhưng thực tế có thể không bao giờ được trả lại.

- **Codex judge verdict:** PASS -- realism=4, label_correctness=4, code_switch_naturalness=4, risk_tier_correctness=4, suspicious_span_accuracy=3
- **Judge reason:**

> Hoàn tiền hoa hồng là cue tốt, còn app Shopee không tự thân đáng ngờ.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [ ] PASS   [x] FAIL

**Notes:** Final triage: DROP
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 033/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=496
- **Record digest:** `cdb57268b22f0ad85e76575d2098e2621f56434168b2bc5301faf10191265920`
- **Evidence digest:** `1c8d70a2164fb221b1675229ee1bc71ccf44cc01bd2778757d95d10083be3c54`
- **Judge origin:** `fresh_final_delta`
- **Judge provenance source:** `data/processed/codex-final-delta-judge.jsonl` (SHA-256 `8c152b519ca70ac9329b382dcafd8a91f09fcc8f0ed81600cbed0e6b98b584d5`)
- **Judge provenance iteration:** 0
- **Historical judge coordinate:** none (fresh final-delta judgment)
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Bạn ơi, mình là bot Telegram. Hiện tại đang có chương trình khuyến mãi trên Binance. Bạn chỉ cần đăng ký qua link này: https://binance-promo.com và mời bạn bè tham gia. Mỗi người bạn mời, bạn sẽ nhận được 5% hoa hồng từ giao dịch của họ. Để kích hoạt tài khoản, bạn cần nạp 100$ vào ví. Liên hệ mình qua Telegram @CryptoBot nha. Chúc bạn thành công!

- **Label:** `task_scam`
- **Risk tier:** `high-risk`
- **Suspicious spans (JSON):** ["nạp 100$", "Telegram @CryptoBot"]
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_b2c9477c611a`

### XAI explanation

> Cẩn thận với các yêu cầu nạp tiền để kích hoạt tài khoản, đặc biệt khi liên kết dẫn đến trang web không chính thức.

- **Codex judge verdict:** PASS -- realism=4, label_correctness=5, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=3
- **Judge reason:**

> The fake Binance promotion conditions referral earnings on a 100-dollar wallet deposit; payment and Telegram contact are marked, though the suspicious domain is omitted.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [x] PASS   [ ] FAIL

**Notes:** 
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 034/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=510
- **Record digest:** `481443fcff02c340781f4166bd594c6aa2fe060f9f47021e2e4609ffe1bc63ad`
- **Evidence digest:** `603eb7cf8fb5496fd466c15525bcd2647815766951e85c7bb5372f3b2a7c018a`
- **Judge origin:** `carried_forward_exact_record`
- **Judge provenance source:** `data/processed/phase39-final-evidence/carry.jsonl` (SHA-256 `593b34ab8eb01d817b849e26aea1022dac422d2a1ef16822ffe44f5cb24b5ea8`)
- **Judge provenance iteration:** historical exact carry
- **Historical judge coordinate:** train:734
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Chào bạn, mình là admin của nhóm TikTok lớn. Mình đang cần người để like, comment và share video. Mỗi task chỉ mất 5 phút và bạn sẽ nhận được 10k/ task. Hãy đăng ký tại [link] để bắt đầu kiếm tiền. Chúc bạn thành công, ak!

- **Label:** `task_scam`
- **Risk tier:** `suspicious`
- **Suspicious spans (JSON):** ["[link]"]
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_97b0ca1e0c34`

### XAI explanation

> Đây là một chiêu lừa đảo thông qua việc yêu cầu nạn nhân thực hiện các task trên TikTok với hứa hẹn trả tiền nhưng không bao giờ thanh toán.

- **Codex judge verdict:** FAIL -- realism=2, label_correctness=5, code_switch_naturalness=4, risk_tier_correctness=4, suspicious_span_accuracy=5
- **Judge reason:**

> Bracketed placeholder formatting makes this read like generated text, not a real message.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [ ] PASS   [x] FAIL

**Notes:** Final triage: (Drop row): Obvious synthetic placeholder token (`[link]`) undermines realism.
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 035/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=513
- **Record digest:** `7eb0b9a5d371af14396fbacc2f46b64ba9826484ec9fa9b9d195726b87bb96e0`
- **Evidence digest:** `9bfca573b67b2a9af35ff652bbf0cb35b8f1bddf6136fd9404414938e19452e6`
- **Judge origin:** `carried_forward_exact_record`
- **Judge provenance source:** `data/processed/phase39-final-evidence/carry.jsonl` (SHA-256 `593b34ab8eb01d817b849e26aea1022dac422d2a1ef16822ffe44f5cb24b5ea8`)
- **Judge provenance iteration:** historical exact carry
- **Historical judge coordinate:** train:737
- **Human verdict origin:** `human_verdict_origin=carried_forward_exact_evidence`
- **Historical human evidence:** Example 46 at train:737

### Message text

> Chào bạn, mình là quản trị viên của nhóm TikTok @tiktok_job. Hiện nhóm đang cần người like, follow, và comment các video để tăng tương tác. Mỗi nhiệm vụ được trả 10k, nếu làm tốt có thể lên đến 200k/ngày. Bạn quan tâm thì add zalo 0978654321 để mình hướng dẫn chi tiết nha. Thử đi, rất dễ kiếm tiền đó!

- **Label:** `task_scam`
- **Risk tier:** `suspicious`
- **Suspicious spans (JSON):** ["@tiktok_job", "0978654321"]
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_bfe4a6bbd16d`

### XAI explanation

> Cần cẩn thận với các lời mời tham gia nhóm hoặc trang mạng xã hội hứa hẹn việc làm dễ dàng với thu nhập cao.

- **Codex judge verdict:** FAIL -- realism=5, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=4, suspicious_span_accuracy=2
- **Judge reason:**

> Contact-only spans miss the impersonation or paid-task lure that makes the message suspicious.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [ ] PASS   [x] FAIL

**Notes:** 
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 036/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=531
- **Record digest:** `f7361d27b0526f61d524604b5755547eee237db23548097a3242856e4c932367`
- **Evidence digest:** `1390dad44a15ec9bc28c291fd2567edfbf4b186083667a90c09e650d836d9340`
- **Judge origin:** `fresh_final_delta`
- **Judge provenance source:** `data/processed/codex-final-delta-judge.jsonl` (SHA-256 `8c152b519ca70ac9329b382dcafd8a91f09fcc8f0ed81600cbed0e6b98b584d5`)
- **Judge provenance iteration:** 0
- **Historical judge coordinate:** none (fresh final-delta judgment)
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Chào bạn, mình là admin của nhóm Zalo livestream. Cần người tham gia các buổi livestream và đặt đơn hàng ảo. Mỗi đơn hàng 50k, bạn sẽ nhận được 10k hoa hồng. Sau khi hoàn thành 10 đơn hàng, bạn cần nâng cấp tài khoản để nhận hoa hồng. Phí nâng cấp là 200k. Link nhóm: [zalo-fake-link.com]. Gửi OTP để xác nhận tham gia nha!

- **Label:** `task_scam`
- **Risk tier:** `high-risk`
- **Suspicious spans (JSON):** ["[zalo-fake-link.com]", "200k", "Phí nâng cấp là 200k", "Gửi OTP để xác nhận tham gia nha"]
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_db9fb32e2681`

### XAI explanation

> Đây có thể là một lừa đảo yêu cầu bạn trả phí nâng cấp tài khoản trước khi có thể nhận hoa hồng.

- **Codex judge verdict:** FAIL -- realism=2, label_correctness=5, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:**

> The fee-before-commission and OTP request correctly indicate high-risk task scam, but [zalo-fake-link.com] is overt template text rather than a natural message artifact.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [ ] PASS   [x] FAIL

**Notes:** Final triage: (Drop row): Obvious synthetic template token (`[zalo-fake-link.com]`).
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 037/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=561
- **Record digest:** `8c1b291d6b19fd2c86c02df821add4243281229e826da033a17de64b4be097d4`
- **Evidence digest:** `5984b7f6d2cda159132491822300e98a7dcb03681803ca1931a1e9b90e694c35`
- **Judge origin:** `carried_forward_exact_record`
- **Judge provenance source:** `data/processed/phase39-final-evidence/carry.jsonl` (SHA-256 `593b34ab8eb01d817b849e26aea1022dac422d2a1ef16822ffe44f5cb24b5ea8`)
- **Judge provenance iteration:** historical exact carry
- **Historical judge coordinate:** train:793
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Xin chào, chúng tôi đã cập nhật ứng dụng Mobile Banking. Hãy tải phiên bản mới để trải nghiệm các tính năng tiện ích hơn.

- **Label:** `benign`
- **Risk tier:** `suspicious`
- **Suspicious spans (JSON):** []
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_214e71ab9e14`

### XAI explanation

> Thông báo về việc cập nhật ứng dụng Mobile Banking nhằm cải thiện trải nghiệm người dùng, không có dấu hiệu đáng ngờ.

- **Codex judge verdict:** FAIL -- realism=5, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=1, suspicious_span_accuracy=5
- **Judge reason:**

> Thông báo cập nhật ứng dụng không link là benign, không đáng tier suspicious.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [ ] PASS   [x] FAIL

**Notes:** Final triage: (Fix tier): Keep label `benign`, but fix risk tier from `suspicious` to `benign` (routine app update announcement without external links).
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 038/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=579
- **Record digest:** `cef189a80eae52bb92ecf2e89dca8da148e5237af3eb0c284a46a100abe3311b`
- **Evidence digest:** `bc887916e9a762a09020c88f9b1220180918dd3fb68e2d4b2ab1c327ffe665f9`
- **Judge origin:** `carried_forward_exact_record`
- **Judge provenance source:** `data/processed/phase39-final-evidence/carry.jsonl` (SHA-256 `593b34ab8eb01d817b849e26aea1022dac422d2a1ef16822ffe44f5cb24b5ea8`)
- **Judge provenance iteration:** historical exact carry
- **Historical judge coordinate:** train:818
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Chào bạn, giao dịch của bạn vừa được xác nhận thành công qua Internet Banking. Vui lòng kiểm tra lại thông tin chi tiết trong tài khoản của bạn.

- **Label:** `benign`
- **Risk tier:** `suspicious`
- **Suspicious spans (JSON):** []
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_977875fab0f0`

### XAI explanation

> Thông báo này xác nhận một giao dịch đã được thực hiện qua Internet Banking và không có dấu hiệu đáng ngờ.

- **Codex judge verdict:** FAIL -- realism=5, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=1, suspicious_span_accuracy=5
- **Judge reason:**

> Yêu cầu kiểm tra trong tài khoản là hành vi an toàn, bình thường.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [ ] PASS   [x] FAIL

**Notes:** Final triage: (Fix tier): Keep label `benign`, but fix risk tier from `suspicious` to `benign` (standard safe in-app transaction notice).
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 039/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=588
- **Record digest:** `befdec32f50036d3fad810f52ffbe5f99f3554b7c77e013940762236a3ec9904`
- **Evidence digest:** `1399278fad43ba7669c979a1b8f5806637722983b08614f8c42a6858f5e25c68`
- **Judge origin:** `carried_forward_exact_record`
- **Judge provenance source:** `data/processed/phase39-final-evidence/carry.jsonl` (SHA-256 `593b34ab8eb01d817b849e26aea1022dac422d2a1ef16822ffe44f5cb24b5ea8`)
- **Judge provenance iteration:** historical exact carry
- **Historical judge coordinate:** train:828
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Chào quý khách, giao dịch của bạn vừa được thực hiện thành công qua ứng dụng Internet Banking. Số tiền: 5,000,000 VND. Tài khoản: 123456789. Cảm ơn sự tin tưởng của bạn!

- **Label:** `benign`
- **Risk tier:** `benign`
- **Suspicious spans (JSON):** []
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_baafb1055e64`

### XAI explanation

> Thông báo này xác nhận một giao dịch thành công qua ứng dụng Internet Banking, không có dấu hiệu đáng ngờ.

- **Codex judge verdict:** PASS -- realism=5, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:**

> Xác nhận giao dịch qua ứng dụng rất đúng thông báo benign.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [x] PASS   [ ] FAIL

**Notes:** 
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 040/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=594
- **Record digest:** `00fb82ebf524120eb932d768ce7a5009a0a2f5b7d2d87a907fc0b054335349b3`
- **Evidence digest:** `142097866ce3d441543d2e9fcae535e2665a6867f6ac8d75885fde73ccba7ee2`
- **Judge origin:** `carried_forward_exact_record`
- **Judge provenance source:** `data/processed/phase39-final-evidence/carry.jsonl` (SHA-256 `593b34ab8eb01d817b849e26aea1022dac422d2a1ef16822ffe44f5cb24b5ea8`)
- **Judge provenance iteration:** historical exact carry
- **Historical judge coordinate:** train:836
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Chào bạn, tài khoản của bạn đã được cập nhật thành công. Hãy kiểm tra lại thông tin tài khoản trong ứng dụng Internet Banking.

- **Label:** `benign`
- **Risk tier:** `suspicious`
- **Suspicious spans (JSON):** []
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_cf9ce2ec8d64`

### XAI explanation

> Thông báo này thông báo về việc cập nhật tài khoản thành công và nhắc nhở khách hàng kiểm tra thông tin trong ứng dụng Internet Banking.

- **Codex judge verdict:** FAIL -- realism=5, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=1, suspicious_span_accuracy=5
- **Judge reason:**

> Cập nhật thành công và kiểm tra trong app hoàn toàn benign.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [ ] PASS   [x] FAIL

**Notes:** Final triage: (Fix tier): Keep label `benign`, but fix risk tier from `suspicious` to `benign` (routine account update confirmation).
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 041/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=632
- **Record digest:** `ecca1659481d4a41088dc86c55ea1449ece91ca3032111f71a6dbac73d668a10`
- **Evidence digest:** `557d3498c6211b513e5f188e5108544da0767d55af35a7cd05819f60fa5cbb77`
- **Judge origin:** `carried_forward_exact_record`
- **Judge provenance source:** `data/processed/phase39-final-evidence/carry.jsonl` (SHA-256 `593b34ab8eb01d817b849e26aea1022dac422d2a1ef16822ffe44f5cb24b5ea8`)
- **Judge provenance iteration:** historical exact carry
- **Historical judge coordinate:** train:890
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Chào bạn, chúng tôi vừa gửi mã OTP đến số điện thoại của bạn. Vui lòng kiểm tra và nhập mã OTP này để xác minh giao dịch của bạn.

- **Label:** `benign`
- **Risk tier:** `benign`
- **Suspicious spans (JSON):** []
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_bfe4a6bbd16d`

### XAI explanation

> Thông báo này yêu cầu người dùng xác minh giao dịch bằng mã OTP, là một quy trình an toàn và phổ biến trong các giao dịch ngân hàng.

- **Codex judge verdict:** PASS -- realism=5, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:**

> Hướng dẫn nhập OTP cho giao dịch là quy trình ngân hàng thông thường.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [x] PASS   [ ] FAIL

**Notes:** 
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 042/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=681
- **Record digest:** `2c8d5bf1b430125c15f9c08bff4d36294b6029736fd965e2b770f355c1b05e35`
- **Evidence digest:** `590b93798560fa3be5850f7740cfaebf972b03db0b87aa9455770876a912c080`
- **Judge origin:** `carried_forward_exact_record`
- **Judge provenance source:** `data/processed/phase39-final-evidence/carry.jsonl` (SHA-256 `593b34ab8eb01d817b849e26aea1022dac422d2a1ef16822ffe44f5cb24b5ea8`)
- **Judge provenance iteration:** historical exact carry
- **Historical judge coordinate:** train:959
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Kính gửi khách hàng, chúng tôi xin thông báo về việc nâng cấp hệ thống Smart OTP. Từ ngày 1/10/2023, bạn sẽ nhận được mã xác thực qua ứng dụng thay vì SMS. Vui lòng cập nhật ứng dụng của bạn để tiếp tục sử dụng dịch vụ.

- **Label:** `benign`
- **Risk tier:** `suspicious`
- **Suspicious spans (JSON):** []
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_d87bcc048ee5`

### XAI explanation

> Thông báo về việc nâng cấp hệ thống Smart OTP, cung cấp thông tin chi tiết và hướng dẫn rõ ràng.

- **Codex judge verdict:** FAIL -- realism=5, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge reason:**

> Nâng cấp Smart OTP trong ứng dụng chỉ tạo rủi ro nhẹ.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [ ] PASS   [x] FAIL

**Notes:** Final triage: (Fix tier): Keep label `benign`, but fix risk tier from `suspicious` to `benign` (routine official Smart OTP system upgrade announcement).
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 043/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=755
- **Record digest:** `93e59a00336b003948da95137223c53d47dab468735a63c443f37a985db126b3`
- **Evidence digest:** `9ed2c16aaf0f90866a9a2e39f6730234306ce5f93e0584134a9f096ecb47dba7`
- **Judge origin:** `carried_forward_exact_record`
- **Judge provenance source:** `data/processed/phase39-final-evidence/carry.jsonl` (SHA-256 `593b34ab8eb01d817b849e26aea1022dac422d2a1ef16822ffe44f5cb24b5ea8`)
- **Judge provenance iteration:** historical exact carry
- **Historical judge coordinate:** train:1060
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Chào bạn, tài khoản của bạn hiện có số dư là 10,000,000 VND. Hãy kiểm tra thường xuyên để quản lý tài chính hiệu quả.

- **Label:** `benign`
- **Risk tier:** `suspicious`
- **Suspicious spans (JSON):** []
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_cf9ce2ec8d64`

### XAI explanation

> Thông báo về số dư tài khoản hiện tại,提醒客户定期检查以有效管理财务.

- **Codex judge verdict:** FAIL -- realism=5, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=1, suspicious_span_accuracy=5
- **Judge reason:**

> Lời nhắc quản lý số dư là nội dung benign.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [ ] PASS   [x] FAIL

**Notes:** Final triage: DROP: Trash message but correct tier also AI explaination is grabage
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 044/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=795
- **Record digest:** `4aed142a313d0b4a4d6a07d805f82317204ad08f50c14adc4584b011e6ec2d2b`
- **Evidence digest:** `f4f73b06171a7a4f61b2228fae4f47c281cc5c62068fac380a5ea72db6aefcd4`
- **Judge origin:** `carried_forward_exact_record`
- **Judge provenance source:** `data/processed/phase39-final-evidence/carry.jsonl` (SHA-256 `593b34ab8eb01d817b849e26aea1022dac422d2a1ef16822ffe44f5cb24b5ea8`)
- **Judge provenance iteration:** historical exact carry
- **Historical judge coordinate:** train:1115
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Kính gửi quý khách, chúng tôi xin thông báo rằng ứng dụng Mobile Banking mới đã sẵn sàng để tải xuống. Hãy cập nhật ngay để trải nghiệm giao diện mới và nhiều tính năng tiện lợi hơn!

- **Label:** `benign`
- **Risk tier:** `suspicious`
- **Suspicious spans (JSON):** []
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_ca1f966326fb`

### XAI explanation

> Thông báo về bản cập nhật ứng dụng Mobile Banking, không có nội dung đáng ngờ.

- **Codex judge verdict:** FAIL -- realism=5, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=1, suspicious_span_accuracy=5
- **Judge reason:**

> Thông báo Mobile Banking mới không thuộc tier suspicious.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [ ] PASS   [x] FAIL

**Notes:** Final triage: (Fix tier): Keep label `benign`, but fix risk tier from `suspicious` to `benign` (routine mobile app update notice without external links).
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 045/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=802
- **Record digest:** `4ed14b2486df69a3de8bd7fc99831eff3231022a7b764546d74d8c45263dc7bb`
- **Evidence digest:** `15e7bcbaaa6af200b2389357b682fa5660199563c402d08b12f46121b0c67606`
- **Judge origin:** `carried_forward_exact_record`
- **Judge provenance source:** `data/processed/phase39-final-evidence/carry.jsonl` (SHA-256 `593b34ab8eb01d817b849e26aea1022dac422d2a1ef16822ffe44f5cb24b5ea8`)
- **Judge provenance iteration:** historical exact carry
- **Historical judge coordinate:** train:1124
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Số dư tài khoản của bạn hiện tại là 10,000,000 VND. Nếu có bất kỳ thắc mắc, vui lòng liên hệ bộ phận hỗ trợ khách hàng.

- **Label:** `benign`
- **Risk tier:** `benign`
- **Suspicious spans (JSON):** []
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_441f08e9ca28`

### XAI explanation

> Thông báo về số dư tài khoản hiện tại và hướng dẫn liên hệ hỗ trợ nếu cần.

- **Codex judge verdict:** PASS -- realism=5, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:**

> Số dư và hỗ trợ khách hàng đúng nội dung benign.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [x] PASS   [ ] FAIL

**Notes:** 
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 046/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=823
- **Record digest:** `077b166818c11034d4f8e7d6b99672643cb8ae3588d1e8e90323669fc3e51941`
- **Evidence digest:** `ecac50687e3efdfec695a911a73d26ae5ee8a5de93411d1238f8809e22f8810b`
- **Judge origin:** `fresh_final_delta`
- **Judge provenance source:** `data/processed/codex-final-delta-judge.jsonl` (SHA-256 `8c152b519ca70ac9329b382dcafd8a91f09fcc8f0ed81600cbed0e6b98b584d5`)
- **Judge provenance iteration:** 0
- **Historical judge coordinate:** none (fresh final-delta judgment)
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Anh/chị là người nhà của bệnh nhân phải không? Tôi đang trực cấp cứu, cháu cần vào phòng mổ ngay nhưng quầy thu viện phí chưa xác nhận tạm ứng. Anh/chị vui lòng quét mã QR này để chuyển khoản viện phí; bên tôi chỉ giữ lịch mổ thêm mười phút.

- **Label:** `zalo_social_engineering`
- **Risk tier:** `high-risk`
- **Suspicious spans (JSON):** ["quét mã QR này để chuyển khoản viện phí"]
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_a236e34e7773`

### XAI explanation

> Tin nhắn tạo áp lực xử lý gấp và yêu cầu quét mã QR này để chuyển khoản viện phí, có thể dẫn đến mất tiền vào tài khoản cá nhân không thuộc bệnh viện.

- **Codex judge verdict:** PASS -- realism=5, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:**

> A supposed emergency clinician uses a ten-minute surgery deadline to solicit a QR hospital transfer, a highly plausible high-risk social-engineering message with the decisive cue exact.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [x] PASS   [ ] FAIL

**Notes:** 
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 047/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=865
- **Record digest:** `06665ff674912e7adfdb06fca7c6476f41ad2ac9db48b8fec9e0eebf56f37965`
- **Evidence digest:** `b5f8bf8c2af510558acb02bef712f20c9bb9c9563931bd59b32dcb9f752bcc9a`
- **Judge origin:** `fresh_final_delta`
- **Judge provenance source:** `data/processed/codex-final-delta-judge.jsonl` (SHA-256 `8c152b519ca70ac9329b382dcafd8a91f09fcc8f0ed81600cbed0e6b98b584d5`)
- **Judge provenance iteration:** 0
- **Historical judge coordinate:** none (fresh final-delta judgment)
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Bạn xác nhận gấp giao dịch vừa rồi giúp mình nhé. Nếu không gửi mã OTP cho tôi để đóng hồ sơ khiếu nại, hồ sơ hoàn tiền sẽ được duyệt và tài khoản mua hàng bị tạm khóa.

- **Label:** `zalo_social_engineering`
- **Risk tier:** `high-risk`
- **Suspicious spans (JSON):** ["gửi mã OTP cho tôi để đóng hồ sơ khiếu nại"]
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_e65835eb3d29`

### XAI explanation

> Tin nhắn tạo áp lực xử lý gấp và yêu cầu gửi mã OTP cho tôi để đóng hồ sơ khiếu nại, có thể dẫn đến giao dịch trái phép được xác nhận.

- **Codex judge verdict:** FAIL -- realism=2, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:**

> The OTP theft setup is clear, but the conditional says refusing the OTP makes the refund approved, which is internally illogical for a real pressure message.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [ ] PASS   [x] FAIL

**Notes:** Final triage: (Drop row): Contradictory and illogical condition phrasing ("nếu không gửi OTP thì hồ sơ hoàn tiền sẽ được duyệt") undermines realism.
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 048/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=882
- **Record digest:** `16f858eb7a1c45bc6621c4fac85215c67d8222ee6b6a0710d624f30ceb2ab1fc`
- **Evidence digest:** `f37c269143498d347ef802ce9f4cd7d6d25cf744375c0465bfce8d2dd4634973`
- **Judge origin:** `fresh_final_delta`
- **Judge provenance source:** `data/processed/codex-final-delta-judge.jsonl` (SHA-256 `8c152b519ca70ac9329b382dcafd8a91f09fcc8f0ed81600cbed0e6b98b584d5`)
- **Judge provenance iteration:** 0
- **Historical judge coordinate:** none (fresh final-delta judgment)
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Anh/chị kiểm tra giúp hóa đơn điện: hệ thống báo chưa thu được tiền nên đã điều đội xuống khu vực. Để tránh bị ngắt nguồn, anh/chị quét mã QR tôi gửi để thanh toán lại hóa đơn trong vài phút tới rồi báo mã giao dịch cho tôi.

- **Label:** `zalo_social_engineering`
- **Risk tier:** `high-risk`
- **Suspicious spans (JSON):** ["quét mã QR tôi gửi để thanh toán lại hóa đơn"]
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_bb3b10a9913f`

### XAI explanation

> Tin nhắn tạo áp lực xử lý gấp và yêu cầu quét mã QR tôi gửi để thanh toán lại hóa đơn, có thể dẫn đến mất tiền nhưng hóa đơn thật vẫn chưa thanh toán.

- **Codex judge verdict:** PASS -- realism=4, label_correctness=4, code_switch_naturalness=5, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:**

> The message naturally combines an alleged collection failure, dispatched crew, QR repayment, and transaction-code request; the selected span identifies the core danger.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [x] PASS   [ ] FAIL

**Notes:** 
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 049/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=888
- **Record digest:** `ce54b2094830b08ee4557b35f738caf1758bc3c33fe0ffa20d53360ef9461815`
- **Evidence digest:** `74d7b2a23a469850dedd35657fafe566d4a33ffb899969a0daa8b04ad06a7041`
- **Judge origin:** `fresh_final_delta`
- **Judge provenance source:** `data/processed/codex-final-delta-judge.jsonl` (SHA-256 `8c152b519ca70ac9329b382dcafd8a91f09fcc8f0ed81600cbed0e6b98b584d5`)
- **Judge provenance iteration:** 1
- **Historical judge coordinate:** none (fresh final-delta judgment)
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Nhà thuốc đã kiểm tra toàn hệ thống và kho bên kia còn đúng một hộp loại anh/chị hỏi. Có khách khác đang chờ, anh/chị thanh toán trước toàn bộ tiền thuốc để em khóa đơn và chuyển thuốc về.

- **Label:** `zalo_social_engineering`
- **Risk tier:** `high-risk`
- **Suspicious spans (JSON):** ["thanh toán trước toàn bộ tiền thuốc"]
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_3ceb8f4aab76`

### XAI explanation

> Tin nhắn tạo áp lực khan hiếm và yêu cầu thanh toán trước toàn bộ tiền thuốc, có thể khiến người nhận mất toàn bộ khoản thanh toán mà không nhận được thuốc.

- **Codex judge verdict:** PASS -- realism=5, label_correctness=4, code_switch_naturalness=5, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:**

> The rare-medicine scarcity story pressures full advance payment before transfer between pharmacies, a credible high-risk social-engineering sale scam.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [x] PASS   [ ] FAIL

**Notes:** 
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 050/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=906
- **Record digest:** `8c9751d858378f100a9e25ca0c6f479d919c64860a25cf01a2954e3b324292fb`
- **Evidence digest:** `cc18212d70ba1889233a3ec1ec0779050958eabd08c9becf8f34a406784b4bbc`
- **Judge origin:** `fresh_final_delta`
- **Judge provenance source:** `data/processed/codex-final-delta-judge.jsonl` (SHA-256 `8c152b519ca70ac9329b382dcafd8a91f09fcc8f0ed81600cbed0e6b98b584d5`)
- **Judge provenance iteration:** 0
- **Historical judge coordinate:** none (fresh final-delta judgment)
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Phòng trong xác nhận cũ vừa phát sinh lỗi kỹ thuật nên chúng tôi đã bố trí hạng phòng cao hơn ở khách sạn bên cạnh. Anh/chị chuyển thêm tiền cọc để giữ phòng thay thế ngay trước khi phương án cuối cùng hết hiệu lực.

- **Label:** `zalo_social_engineering`
- **Risk tier:** `high-risk`
- **Suspicious spans (JSON):** ["chuyển thêm tiền cọc để giữ phòng thay thế"]
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_a8e1aabe0a03`

### XAI explanation

> Tin nhắn tạo áp lực xử lý gấp và yêu cầu chuyển thêm tiền cọc để giữ phòng thay thế, có thể dẫn đến mất tiền cọc và không có chỗ ở.

- **Codex judge verdict:** PASS -- realism=4, label_correctness=3, code_switch_naturalness=5, risk_tier_correctness=4, suspicious_span_accuracy=5
- **Judge reason:**

> The urgent extra-deposit request is risky and compatible with booking fraud, but the text lacks an unmistakable scam-only cue beyond the unusual payment demand.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [x] PASS   [ ] FAIL

**Notes:** 
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 051/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=973
- **Record digest:** `5b8cfbd3d2f94da63130b532c40fdfbcf27ca30639c4bc3a9d740cbfdc952c64`
- **Evidence digest:** `b49ceb7dfdb16c2c1c84bdcb2aa9ada8c8effbfb396ff7d41b9812b97d4806f8`
- **Judge origin:** `carried_forward_exact_record`
- **Judge provenance source:** `data/processed/phase39-final-evidence/carry.jsonl` (SHA-256 `593b34ab8eb01d817b849e26aea1022dac422d2a1ef16822ffe44f5cb24b5ea8`)
- **Judge provenance iteration:** historical exact carry
- **Historical judge coordinate:** train:1794
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Này Tuấn, tau Phong nè. Tau đang dùng Messenger web vì điện thoại gửi sửa rồi. Mày có đang rảnh ko? Tau cần nhờ mày một việc gấp. Tau đang làm dự án freelance, khách hàng yêu cầu thanh toán qua Internet Banking nhưng acc của tau đang bị limit giao dịch do xác minh CCCD chưa xong. Mày cho tau mượn acc nhận tiền dc ko? Tau chuyển link thanh toán cho mày, khách chuyển vào acc mày xong mày rút ra đưa lại tau. Có 15tr thôi, tau cho mày 200k công.

- **Label:** `task_scam`
- **Risk tier:** `high-risk`
- **Suspicious spans (JSON):** ["dùng Messenger web vì điện thoại gửi sửa rồi", "acc của tau đang bị limit giao dịch", "xác minh CCCD chưa xong", "cho tau mượn acc nhận tiền", "Tau chuyển link thanh toán cho mày", "khách chuyển vào acc mày xong mày rút ra đưa lại tau", "tau cho mày 200k công"]
- **Source:** `synthetic_claude`
- **Seed ID:** `seed_157ce0adb043`

### XAI explanation

> Đây là biến thể tinh vi hơn: không chỉ xin tiền mà còn yêu cầu 'mượn tài khoản ngân hàng' – hành vi có thể biến nạn nhân thành người tiếp tay rửa tiền. Lý do 'limit Internet Banking' và 'link thanh toán' sử dụng thuật ngữ fintech để tạo vẻ hợp lệ. Phần thưởng nhỏ 200k được dùng để thuyết phục. Đây là dấu hiệu của cả scam lẫn money mule fraud.

- **Codex judge verdict:** PASS -- realism=4, label_correctness=4, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:**

> Việc nhận hộ tiền có công gần task scam và tạo nguy cơ money mule.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [ ] PASS   [x] FAIL

**Notes:** Final triage: (Relabel label): Mislabeled as `task_scam`; relabel to `zalo_social_engineering` (friend impersonation money mule scam with commission lure; keep `high-risk`).
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 052/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=987
- **Record digest:** `6cbba71f22f5f089b4db8ee56446653b59e56e418e6177355a7e8c3ca173a40f`
- **Evidence digest:** `2a970ad800045102d9ddc95a7577140435ffc0406ce089f2a79b2373cc577b62`
- **Judge origin:** `carried_forward_exact_record`
- **Judge provenance source:** `data/processed/phase39-final-evidence/carry.jsonl` (SHA-256 `593b34ab8eb01d817b849e26aea1022dac422d2a1ef16822ffe44f5cb24b5ea8`)
- **Judge provenance iteration:** historical exact carry
- **Historical judge coordinate:** val:12
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Chào anh/chị, em là Nguyễn Linh - nhân viên hỗ trợ khách hàng VPBank. Hệ thống ghi nhận tài khoản Internet Banking của anh/chị đang có giao dịch bất thường lúc 2:47 sáng nay với số tiền 45.000.000 VNĐ. Để huỷ giao dịch này và bảo vệ account, anh/chị cần cung cấp mã Smart OTP gửi về số điện thoại đăng ký, hoặc truy cập ngay: http://vpbank-hotro24h.com/xacthuc để xác minh danh tính. Nếu không xử lý kịp, giao dịch sẽ được duyệt tự động sau 15 phút nha. Em xin cảm ơn anh/chị đã tin dùng VPBank!

- **Label:** `bank_impersonation`
- **Risk tier:** `high-risk`
- **Suspicious spans (JSON):** ["cung cấp mã Smart OTP", "http://vpbank-hotro24h.com/xacthuc", "giao dịch sẽ được duyệt tự động sau 15 phút"]
- **Source:** `synthetic_claude`
- **Seed ID:** `seed_24cd9d0d3396`

### XAI explanation

> Kẻ lừa đảo giả danh nhân viên VPBank yêu cầu cung cấp mã Smart OTP và dẫn đến link giả mạo, đây là dấu hiệu điển hình của tấn công phishing nhằm chiếm đoạt tài khoản ngân hàng.

- **Codex judge verdict:** PASS -- realism=5, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:**

> Lấy Smart OTP qua trang VPBank giả và ép thời gian rất rõ.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [x] PASS   [ ] FAIL

**Notes:** 
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 053/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=994
- **Record digest:** `a90939394b904d28713f1bbfe2763f5effee22e5ccf64f4749dd7e92b07b8a7f`
- **Evidence digest:** `c9081773682c857b21b18f34fb2257c570a6540894e8c1e4240707f80c3a2674`
- **Judge origin:** `carried_forward_exact_record`
- **Judge provenance source:** `data/processed/phase39-final-evidence/carry.jsonl` (SHA-256 `593b34ab8eb01d817b849e26aea1022dac422d2a1ef16822ffe44f5cb24b5ea8`)
- **Judge provenance iteration:** historical exact carry
- **Historical judge coordinate:** val:21
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Xin chào, tôi là nhân viên chăm sóc khách hàng của ngân hàng XYZ. Tài khoản của bạn đang có vấn đề về bảo mật. Để khắc phục, vui lòng cung cấp mã OTP đã gửi đến điện thoại của bạn qua SMS. Số điện thoại liên hệ: 0123456789

- **Label:** `bank_impersonation`
- **Risk tier:** `suspicious`
- **Suspicious spans (JSON):** ["OTP", "0123456789"]
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_d34a4cd1d365`

### XAI explanation

> Không bao giờ chia sẻ mã OTP cho bất kỳ ai, kể cả người tự xưng là nhân viên ngân hàng.

- **Codex judge verdict:** FAIL -- realism=2, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=2, suspicious_span_accuracy=4
- **Judge reason:**

> Placeholder makes this synthetic; direct credential request warrants high-risk rather than suspicious.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [ ] PASS   [x] FAIL

**Notes:** Final triage: (Drop row): Contains obvious sequential synthetic phone placeholder (`0123456789`), generic "ngân hàng XYZ", and risk tier mismatch (direct OTP solicitation requires `high-risk`).
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 054/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=1033
- **Record digest:** `27233d7da7f6c5310d1bbb3667b439d3119f5741724731da39896b4711c17d78`
- **Evidence digest:** `ba27889f7a2cfecc68229cd4b8b3baec223a3e1113561894e661efaccab3bc0c`
- **Judge origin:** `carried_forward_exact_record`
- **Judge provenance source:** `data/processed/phase39-final-evidence/carry.jsonl` (SHA-256 `593b34ab8eb01d817b849e26aea1022dac422d2a1ef16822ffe44f5cb24b5ea8`)
- **Judge provenance iteration:** historical exact carry
- **Historical judge coordinate:** val:83
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Chào bạn, mình là admin của nhóm TikTok. Bạn có thể giúp mình like và comment cho video, mỗi task sẽ được trả 10k. Hãy đăng nhập vào app TikTok và làm theo hướng dẫn tại link này: http://bit.ly/tiktoktask. Chúc bạn thành công! - Admin

- **Label:** `task_scam`
- **Risk tier:** `suspicious`
- **Suspicious spans (JSON):** ["http://bit.ly/tiktoktask"]
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_d34a4cd1d365`

### XAI explanation

> Link dẫn đến trang web không an toàn, có thể là lừa đảo.

- **Codex judge verdict:** PASS -- realism=5, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=4, suspicious_span_accuracy=5
- **Judge reason:**

> Link rút gọn tuyển like và comment đúng kịch bản nhiệm vụ.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [x] PASS   [ ] FAIL

**Notes:** 
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 055/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=1037
- **Record digest:** `4db3a0002033774596850e7a7edae6b50c87f249511e42a1a5b221a403c213f3`
- **Evidence digest:** `756f4e1b00fb769f7dad01d1868293f6cc68f3f28d0e69595b8fa21a7c13b80b`
- **Judge origin:** `fresh_final_delta`
- **Judge provenance source:** `data/processed/codex-final-delta-judge.jsonl` (SHA-256 `8c152b519ca70ac9329b382dcafd8a91f09fcc8f0ed81600cbed0e6b98b584d5`)
- **Judge provenance iteration:** 0
- **Historical judge coordinate:** none (fresh final-delta judgment)
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Xin chào, đây là dịch vụ chăm sóc khách hàng của Techcombank. Bạn vừa nhận được một mã OTP: 123456. Vui lòng nhập mã này vào ứng dụng Internet Banking để hoàn tất giao dịch. Nếu bạn chưa yêu cầu, vui lòng gọi 0987654321 để xác minh.

- **Label:** `benign`
- **Risk tier:** `suspicious`
- **Suspicious spans (JSON):** ["0987654321"]
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_cd2758fc96b9`

### XAI explanation

> Không chia sẻ mã OTP với bất kỳ ai và chỉ sử dụng nó trong giao dịch của bạn.

- **Codex judge verdict:** FAIL -- realism=2, label_correctness=3, code_switch_naturalness=5, risk_tier_correctness=4, suspicious_span_accuracy=3
- **Judge reason:**

> The enter-OTP-in-app guidance can be benign and the callback number supports suspicion, but the obvious 123456 and 0987654321 placeholders make the message look synthetic rather than real.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [ ] PASS   [x] FAIL

**Notes:** Final triage: (Drop row): Contradictory mix of benign in-app OTP instruction with obvious synthetic dummy placeholders (`0987654321` and `123456`).
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 056/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=1038
- **Record digest:** `f868bb7151e7964f2e1ee059e4a528a1d6f687c06e5f06816e6c6ec865391169`
- **Evidence digest:** `6760a36bc4526ce5c705fb9061f614e1de7ad222d23e09a2354c1c77106789d4`
- **Judge origin:** `carried_forward_exact_record`
- **Judge provenance source:** `data/processed/phase39-final-evidence/carry.jsonl` (SHA-256 `593b34ab8eb01d817b849e26aea1022dac422d2a1ef16822ffe44f5cb24b5ea8`)
- **Judge provenance iteration:** historical exact carry
- **Historical judge coordinate:** val:92
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Xin chào, tôi là quản lý của cửa hàng Shopee. Bạn có thể mua sản phẩm và viết đánh giá 5 sao, sau đó sẽ được hoàn lại tiền và nhận thêm 10% hoa hồng. Hãy đặt hàng ngay qua link: https://shopee.vn/fakeoffer. Đừng bỏ lỡ cơ hội này!

- **Label:** `task_scam`
- **Risk tier:** `suspicious`
- **Suspicious spans (JSON):** ["https://shopee.vn/fakeoffer"]
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_d34a4cd1d365`

### XAI explanation

> Link mua hàng có thể là lừa đảo, tiền sẽ không được hoàn lại.

- **Codex judge verdict:** FAIL -- realism=2, label_correctness=5, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:**

> Placeholder/fake token makes this synthetic rather than a real message.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [ ] PASS   [x] FAIL

**Notes:** Final triage: (Drop row): Synthetic placeholder path token (`fakeoffer`) in the URL undermines real-world realism.
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 057/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=1042
- **Record digest:** `2d69ad42a0c70fdc8e3356a4818c515943881e162c09e7858366186ee66a2709`
- **Evidence digest:** `0297f6d1a318b055c6db55b9520ce634349f61e0f2853ced6468a29f8624f746`
- **Judge origin:** `fresh_final_delta`
- **Judge provenance source:** `data/processed/codex-final-delta-judge.jsonl` (SHA-256 `8c152b519ca70ac9329b382dcafd8a91f09fcc8f0ed81600cbed0e6b98b584d5`)
- **Judge provenance iteration:** 0
- **Historical judge coordinate:** none (fresh final-delta judgment)
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Bạn ơi, mình là bot trên Telegram. Bạn có thể tham gia nhóm livestream của chúng tôi và đặt đơn hàng ảo để tăng tương tác. Mỗi đơn hàng sẽ được trả 20k. Sau khi hoàn thành 5 đơn hàng, hãy chuyển 50k để nâng cấp tài khoản và nhận thanh toán. Liên hệ mình qua Zalo: 0987654321.

- **Label:** `task_scam`
- **Risk tier:** `high-risk`
- **Suspicious spans (JSON):** ["0987654321", "hãy chuyển 50k để nâng cấp tài khoản và nhận thanh toán"]
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_d34a4cd1d365`

### XAI explanation

> Yêu cầu chuyển tiền để nâng cấp tài khoản là dấu hiệu lừa đảo.

- **Codex judge verdict:** FAIL -- realism=2, label_correctness=5, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=4
- **Judge reason:**

> The virtual-order and upgrade-fee mechanics correctly identify a task scam, but self-identifying as a bot and using the obvious 0987654321 placeholder make it conspicuously synthetic.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [ ] PASS   [x] FAIL

**Notes:** Final triage: (Drop row): Synthetic sequential placeholder phone number (`0987654321`) and unnatural self-identification as a bot.
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 058/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=1046
- **Record digest:** `139c163457051a7d561aa13881acccfb123d621aab8230876d6ca6ac4887589b`
- **Evidence digest:** `40312fdb91e6c137910c155773a37c791f8c6788268a22d8436babe4d3c654a2`
- **Judge origin:** `fresh_final_delta`
- **Judge provenance source:** `data/processed/codex-final-delta-judge.jsonl` (SHA-256 `8c152b519ca70ac9329b382dcafd8a91f09fcc8f0ed81600cbed0e6b98b584d5`)
- **Judge provenance iteration:** 1
- **Historical judge coordinate:** none (fresh final-delta judgment)
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Chào bạn, mình là điều tra viên của CAFC. Chúng tôi đang điều tra vụ lừa đảo mà bạn đã tố cáo. Để giúp chúng tôi phục hồi số tiền đã mất, vui lòng cung cấp OTP từ ứng dụng Internet Banking của bạn. Liên hệ qua số điện thoại 0987654321 để xác minh thêm thông tin. Cảm ơn sự hợp tác của bạn!

- **Label:** `bank_impersonation`
- **Risk tier:** `high-risk`
- **Suspicious spans (JSON):** ["cung cấp OTP từ ứng dụng Internet Banking của bạn", "0987654321"]
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_c3c238c360c8`

### XAI explanation

> Không cung cấp OTP hoặc thông tin tài khoản cho bất kỳ ai yêu cầu qua điện thoại hoặc tin nhắn.

- **Codex judge verdict:** FAIL -- realism=4, label_correctness=2, code_switch_naturalness=5, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:**

> The OTP-recovery fraud is high-risk and fully spanned, but the actor explicitly impersonates a CAFC investigator rather than a bank.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [ ] PASS   [x] FAIL

**Notes:** Final triage: DROP
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 059/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=1053
- **Record digest:** `3e0d0bbb583aa20f3dd3e0961c2f74e139a89c09c0fdc121a21d82154b6f194e`
- **Evidence digest:** `815fd4804a26be60b3cb925cb59f1e3aa631d9655721e9d958b31abc93b55d85`
- **Judge origin:** `fresh_final_delta`
- **Judge provenance source:** `data/processed/codex-final-delta-judge.jsonl` (SHA-256 `8c152b519ca70ac9329b382dcafd8a91f09fcc8f0ed81600cbed0e6b98b584d5`)
- **Judge provenance iteration:** 1
- **Historical judge coordinate:** none (fresh final-delta judgment)
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Chào bạn, mình là điều tra viên từ CAFC. Chúng tôi đã tìm thấy cách để lấy lại số tiền đã mất của bạn. Vui lòng gửi mã Smart OTP từ ứng dụng Internet Banking đến số 0987654321 để chúng tôi xác minh. Cảm ơn sự hợp tác của bạn!

- **Label:** `bank_impersonation`
- **Risk tier:** `high-risk`
- **Suspicious spans (JSON):** ["gửi mã Smart OTP từ ứng dụng Internet Banking đến số 0987654321", "0987654321"]
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_c3c238c360c8`

### XAI explanation

> Không gửi mã Smart OTP hoặc thông tin tài khoản cho bất kỳ ai yêu cầu qua điện thoại hoặc tin nhắn.

- **Codex judge verdict:** FAIL -- realism=4, label_correctness=2, code_switch_naturalness=5, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:**

> The Smart-OTP recovery pretext is high-risk and precisely marked, but CAFC investigator impersonation does not genuinely belong to the bank-impersonation class.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [ ] PASS   [x] FAIL

**Notes:** Final triage: DROP
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 060/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=1059
- **Record digest:** `82f957652257e4cdc573210331888cf39f84bc53593e2120c2447d0e617cd08d`
- **Evidence digest:** `e7ddc05a2902124e716cb315bff07af14fb2d7f4e58cd9768feeee7a1a7ee44e`
- **Judge origin:** `carried_forward_exact_record`
- **Judge provenance source:** `data/processed/phase39-final-evidence/carry.jsonl` (SHA-256 `593b34ab8eb01d817b849e26aea1022dac422d2a1ef16822ffe44f5cb24b5ea8`)
- **Judge provenance iteration:** historical exact carry
- **Historical judge coordinate:** val:131
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Bạn ơi, mình là admin của group Zalo @zaloshopgroup. Cần tuyển người mua sản phẩm trên Shopee, sau đó đánh giá 5 sao và nhận hoàn tiền 100% + hoa hồng 10%. Bạn chỉ cần đăng ký qua link: https://fake-shopee-link.com. Liên hệ mình qua Zalo 0912345678 nha!

- **Label:** `task_scam`
- **Risk tier:** `suspicious`
- **Suspicious spans (JSON):** ["@zaloshopgroup", "https://fake-shopee-link.com", "0912345678"]
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_cd2758fc96b9`

### XAI explanation

> Thông điệp này có thể là lừa đảo vì nó yêu cầu bạn mua sản phẩm và đánh giá, nhưng hoàn tiền và hoa hồng có thể không bao giờ được trả.

- **Codex judge verdict:** FAIL -- realism=2, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:**

> Placeholder/fake token makes this synthetic rather than a real message.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [ ] PASS   [x] FAIL

**Notes:** Final triage: (Drop row): Obvious synthetic placeholder domain (`fake-shopee-link.com`) and sequential phone number (`0912345678`).
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 061/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=1069
- **Record digest:** `efd04335688b67600b67aced73a6f3147b717ea0f3085a78cdf17306f898f4ae`
- **Evidence digest:** `15fa201adbbb97a24ead3f8ada243a38b92a820f6a71ffba461f9984ff1f2a7f`
- **Judge origin:** `fresh_final_delta`
- **Judge provenance source:** `data/processed/codex-final-delta-judge.jsonl` (SHA-256 `8c152b519ca70ac9329b382dcafd8a91f09fcc8f0ed81600cbed0e6b98b584d5`)
- **Judge provenance iteration:** 0
- **Historical judge coordinate:** none (fresh final-delta judgment)
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Chào bạn, mình là admin của group Zalo livestream. Hiện group đang cần người tham gia đặt đơn hàng ảo trong livestream để tăng tương tác. Mỗi đơn hàng hoàn thành, bạn sẽ nhận 20k. Bạn quan tâm thì chuyển 100k vào tài khoản 0987654321012345 để nâng cấp tài khoản, sau đó mình sẽ gửi link tham gia livestream.

- **Label:** `task_scam`
- **Risk tier:** `high-risk`
- **Suspicious spans (JSON):** ["0987654321012345", "chuyển 100k vào tài khoản 0987654321012345 để nâng cấp tài khoản"]
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_c3c238c360c8`

### XAI explanation

> Đây là một hình thức lừa đảo yêu cầu bạn đặt đơn hàng ảo trong livestream và chuyển tiền trước, nhưng không bao giờ nhận được tiền hoa hồng.

- **Codex judge verdict:** FAIL -- realism=2, label_correctness=5, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:**

> The livestream fake-order work and required upgrade transfer are valid task-scam cues, but the sequential placeholder account makes the sample visibly synthetic.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [ ] PASS   [x] FAIL

**Notes:** Final triage: (Drop row): Contains obvious sequential synthetic placeholder bank account (`0987654321012345`).
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 062/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=1074
- **Record digest:** `253594410968e4c678b4695477098942b90db68c75983317088d8e70a1dd2c77`
- **Evidence digest:** `0c584ff81de18d71a1cde08f69603eb815fd342626f2ab1fda7cb7d133391148`
- **Judge origin:** `carried_forward_exact_record`
- **Judge provenance source:** `data/processed/phase39-final-evidence/carry.jsonl` (SHA-256 `593b34ab8eb01d817b849e26aea1022dac422d2a1ef16822ffe44f5cb24b5ea8`)
- **Judge provenance iteration:** historical exact carry
- **Historical judge coordinate:** val:153
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Chào quý khách, giao dịch chuyển tiền 5.000.000 VND từ tài khoản của bạn đã được hoàn tất. Vui lòng kiểm tra lại thông tin. Cảm ơn bạn đã sử dụng dịch vụ Internet Banking của chúng tôi.

- **Label:** `benign`
- **Risk tier:** `benign`
- **Suspicious spans (JSON):** []
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_c3c238c360c8`

### XAI explanation

> Thông báo xác nhận giao dịch chuyển tiền qua Internet Banking, không có dấu hiệu đáng ngờ.

- **Codex judge verdict:** PASS -- realism=5, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:**

> Xác nhận giao dịch và lời nhắc kiểm tra đều an toàn.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [x] PASS   [ ] FAIL

**Notes:** 
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 063/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=1174
- **Record digest:** `cb25f46bd8d26023bc87e60ebb40c09bdfbd914b6da7e3126570992ccfe1b667`
- **Evidence digest:** `30805a7146279c1932270e624c6b4357fc21029323454266b53c8ec672b8739a`
- **Judge origin:** `carried_forward_exact_record`
- **Judge provenance source:** `data/processed/phase39-final-evidence/carry.jsonl` (SHA-256 `593b34ab8eb01d817b849e26aea1022dac422d2a1ef16822ffe44f5cb24b5ea8`)
- **Judge provenance iteration:** historical exact carry
- **Historical judge coordinate:** test:33
- **Human verdict origin:** `human_verdict_origin=carried_forward_exact_evidence`
- **Historical human evidence:** Example 1 at test:33

### Message text

> Thông báo từ VietcomBank: Tài khoản của bạn vừa đăng nhập từ thiết bị lạ tại Úc. Nếu không phải bạn, hãy xác minh ngay tại: http://vietcom-bank-secure.net/xacminh để tránh bị khóa tài khoản trong 24h. Liên hệ CSKH: 1800.9999.88

- **Label:** `bank_impersonation`
- **Risk tier:** `high-risk`
- **Suspicious spans (JSON):** ["http://vietcom-bank-secure.net/xacminh", "đăng nhập từ thiết bị lạ tại Úc", "bị khóa tài khoản trong 24h"]
- **Source:** `synthetic_claude`
- **Seed ID:** `seed_5efd416f05fd`

### XAI explanation

> Tên miền giả mạo 'vietcom-bank-secure.net' không phải domain chính thức của Vietcombank (vietcombank.com.vn), kết hợp với cảnh báo đăng nhập từ nước ngoài để tạo áp lực khẩn cấp nhằm lừa người dùng nhấp vào link độc hại.

- **Codex judge verdict:** PASS -- realism=5, label_correctness=5, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:**

> Đăng nhập tại Úc và trang giả tạo cảnh báo high-risk rõ.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [x] PASS   [ ] FAIL

**Notes:** 
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 064/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=1182
- **Record digest:** `2c3a262cc74a83f7bbfa318754b1637d3fe45e0a21f9540ce475b23f8a183611`
- **Evidence digest:** `e7ddc05a2902124e716cb315bff07af14fb2d7f4e58cd9768feeee7a1a7ee44e`
- **Judge origin:** `carried_forward_exact_record`
- **Judge provenance source:** `data/processed/phase39-final-evidence/carry.jsonl` (SHA-256 `593b34ab8eb01d817b849e26aea1022dac422d2a1ef16822ffe44f5cb24b5ea8`)
- **Judge provenance iteration:** historical exact carry
- **Historical judge coordinate:** test:44
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Techcombank thông báo: Tài khoản của bạn bị khóa tạm thời do đăng nhập bất thường từ IP lạ. Vui lòng xác minh danh tính qua link: https://techcom-id-unlock.com/verify hoặc nhập OTP sau: [hệ thống sẽ gửi riêng]. Nếu k xác minh trong 30 phút, tk sẽ bị đóng vĩnh viễn nha!

- **Label:** `bank_impersonation`
- **Risk tier:** `high-risk`
- **Suspicious spans (JSON):** ["https://techcom-id-unlock.com/verify", "tk sẽ bị đóng vĩnh viễn", "đăng nhập bất thường từ IP lạ"]
- **Source:** `synthetic_claude`
- **Seed ID:** `seed_8e92a82e90b4`

### XAI explanation

> Kẻ lừa đảo giả danh Techcombank tạo áp lực thời gian 30 phút và dùng domain giả để thu thập OTP và thông tin đăng nhập Internet Banking của nạn nhân.

- **Codex judge verdict:** FAIL -- realism=2, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:**

> Placeholder/fake token makes this synthetic rather than a real message.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [ ] PASS   [x] FAIL

**Notes:** Final triage: (Drop row): Obvious synthetic placeholder bracket token (`[hệ thống sẽ gửi riêng]`) undermines realism.
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 065/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=1189
- **Record digest:** `a61279e644e73d9e908abe15910795f6f3a9188ef0b177cbbf7425ae7c66f25d`
- **Evidence digest:** `826755466aa8a7c4d8616d84c57b766cdfa99351f65f4fb1a5a23dbb3dadcf90`
- **Judge origin:** `carried_forward_exact_record`
- **Judge provenance source:** `data/processed/phase39-final-evidence/carry.jsonl` (SHA-256 `593b34ab8eb01d817b849e26aea1022dac422d2a1ef16822ffe44f5cb24b5ea8`)
- **Judge provenance iteration:** historical exact carry
- **Historical judge coordinate:** test:55
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> 📢 [MB Bank] Chúc mừng! Số tài khoản của bạn được chọn nhận thưởng 50 TRIỆU từ chương trình khách hàng thân thiết 2024. Để nhận tiền, login vào link sau và xác minh danh tính: mb-bank.reward-vn.click/nhan-thuong — Ưu đãi hết hạn sau 24h!

- **Label:** `bank_impersonation`
- **Risk tier:** `high-risk`
- **Suspicious spans (JSON):** ["mb-bank.reward-vn.click/nhan-thuong", "nhận thưởng 50 TRIỆU", "Ưu đãi hết hạn sau 24h"]
- **Source:** `synthetic_claude`
- **Seed ID:** `seed_1a4f7d4d7c53`

### XAI explanation

> Tên miền 'reward-vn.click' không liên quan đến MB Bank; kết hợp phần thưởng giá trị lớn và thời hạn ngắn là dấu hiệu điển hình của lừa đảo giả mạo ngân hàng.

- **Codex judge verdict:** PASS -- realism=4, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:**

> Giải thưởng 50 triệu và domain click giả đúng phishing trúng thưởng.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [x] PASS   [ ] FAIL

**Notes:** 
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 066/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=1204
- **Record digest:** `5d1026dc5e924110e85ff2e8a6e35a85aea1df6bab0851e29c2da02fdafbcae5`
- **Evidence digest:** `5dbc111abc0b9dfea301d8756533d7a69dc6863cc31ccd0aa2ccea88e6d9d7ea`
- **Judge origin:** `fresh_final_delta`
- **Judge provenance source:** `data/processed/codex-final-delta-judge.jsonl` (SHA-256 `8c152b519ca70ac9329b382dcafd8a91f09fcc8f0ed81600cbed0e6b98b584d5`)
- **Judge provenance iteration:** 1
- **Historical judge coordinate:** none (fresh final-delta judgment)
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Bạn vừa nhận được mã OTP là 123456 từ BIDV. Hãy nhập mã này để xác nhận thanh toán mua sắm trực tuyến. Nếu bạn ko thực hiện giao dịch này, vui lòng bỏ qua tin nhắn này. Cảm ơn!

- **Label:** `benign`
- **Risk tier:** `benign`
- **Suspicious spans (JSON):** []
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_5efd416f05fd`

### XAI explanation

> Đây là thông báo OTP thanh toán thông thường của BIDV và hướng dẫn bỏ qua nếu không thực hiện giao dịch; người nhận không nên chia sẻ mã.

- **Codex judge verdict:** PASS -- realism=5, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:**

> This is a conventional BIDV OTP notice for a purchase and tells users to ignore an unrecognized transaction; benign tier, empty spans, and XAI fit.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [x] PASS   [ ] FAIL

**Notes:** 
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 067/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=1206
- **Record digest:** `c75e71976d88b4ed5c551054a5d08fae9e451b12351f0aff877ef4cb5a00d2e7`
- **Evidence digest:** `f0a532fc0906ba5b22827146e973f366d5124169cb019865af432d4d1268626c`
- **Judge origin:** `fresh_final_delta`
- **Judge provenance source:** `data/processed/codex-final-delta-judge.jsonl` (SHA-256 `8c152b519ca70ac9329b382dcafd8a91f09fcc8f0ed81600cbed0e6b98b584d5`)
- **Judge provenance iteration:** 0
- **Historical judge coordinate:** none (fresh final-delta judgment)
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Chào bạn, mình là đại diện của Binance Việt Nam. Hiện chúng tôi đang có chương trình khuyến mãi dành cho người dùng mới. Đăng ký thông qua link này [fake-url.com] và giới thiệu bạn bè, bạn sẽ nhận được 10% hoa hồng từ mỗi giao dịch của họ. Để kích hoạt tài khoản, bạn cần nạp 500k vào ví. Liên hệ Zalo 0987654321 nếu cần hỗ trợ. Chúc bạn thành công!

- **Label:** `task_scam`
- **Risk tier:** `high-risk`
- **Suspicious spans (JSON):** ["[fake-url.com]", "0987654321", "bạn cần nạp 500k vào ví"]
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_93304f9cc9ab`

### XAI explanation

> Đề nghị nạp tiền để kích hoạt tài khoản thường là lừa đảo, hãy cẩn thận và kiểm tra kỹ nguồn gốc của các liên kết.

- **Codex judge verdict:** FAIL -- realism=1, label_correctness=5, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:**

> Referral commission plus a 500k activation deposit correctly signals task fraud, but literal [fake-url.com] and 0987654321 are glaring placeholder artifacts.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [ ] PASS   [x] FAIL

**Notes:** Final triage: (Drop row): Obvious synthetic bracketed placeholder (`[fake-url.com]`) and dummy contact number (`0987654321`).
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 068/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=1209
- **Record digest:** `d9cb4b099bc6afc754bc24a15aadb1790bff420ee49b7911797b4bbd11c25444`
- **Evidence digest:** `a95f4792b242c4a72e78c33241d145b576fe58561a1018b36f19e1e797f8a001`
- **Judge origin:** `fresh_final_delta`
- **Judge provenance source:** `data/processed/codex-final-delta-judge.jsonl` (SHA-256 `8c152b519ca70ac9329b382dcafd8a91f09fcc8f0ed81600cbed0e6b98b584d5`)
- **Judge provenance iteration:** 1
- **Historical judge coordinate:** none (fresh final-delta judgment)
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Chào bạn, chúng tôi từ MBBank xin thông báo rằng tài khoản của bạn đang gặp rủi ro. Để bảo vệ tài khoản, hãy đăng nhập vào ứng dụng MBBank và thay đổi mật khẩu ngay lập tức. Nếu ko, tài khoản của bạn có thể bị khóa. Vui lòng thực hiện ngay, nha!

- **Label:** `benign`
- **Risk tier:** `benign`
- **Suspicious spans (JSON):** []
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_5efd416f05fd`

### XAI explanation

> Tin nhắn hướng dẫn người nhận tự mở ứng dụng MBBank để đổi mật khẩu; nên xác minh thông báo trong ứng dụng chính thức và không chia sẻ thông tin đăng nhập.

- **Codex judge verdict:** PASS -- realism=4, label_correctness=5, code_switch_naturalness=4, risk_tier_correctness=4, suspicious_span_accuracy=5
- **Judge reason:**

> Although urgent, it directs the customer to open the official MBBank app and does not request credentials or an external channel; benign annotations are defensible.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [x] PASS   [ ] FAIL

**Notes:** 
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 069/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=1211
- **Record digest:** `442779859fffc8108e1e022caa5e2952c2afd3f995650a968212fffd73f96565`
- **Evidence digest:** `03f38ff585dc8a4f36d19f5494b302f8fe2a203c3349939d1824948f8a305ebc`
- **Judge origin:** `carried_forward_exact_record`
- **Judge provenance source:** `data/processed/phase39-final-evidence/carry.jsonl` (SHA-256 `593b34ab8eb01d817b849e26aea1022dac422d2a1ef16822ffe44f5cb24b5ea8`)
- **Judge provenance iteration:** historical exact carry
- **Historical judge coordinate:** test:89
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Chào bạn, mình là quản lý của shop online trên Shopee. Chúng tôi đang cần người đặt đơn hàng ảo để tăng lượng bán. Mỗi đơn hàng, bạn sẽ nhận được 50k hoa hồng. Bạn chỉ cần đặt hàng thông qua app Shopee, sau đó chụp ảnh màn hình và gửi lại cho mình. Tiền hoa hồng sẽ được chuyển sau khi xác nhận. Nếu quan tâm, liên hệ Zalo 0987654321. Chúc bạn một ngày tốt lành!

- **Label:** `task_scam`
- **Risk tier:** `suspicious`
- **Suspicious spans (JSON):** ["0987654321", "app Shopee"]
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_93304f9cc9ab`

### XAI explanation

> Cần cảnh giác với các đề nghị đặt đơn hàng ảo, vì rất có thể bạn sẽ không nhận được bất kỳ khoản hoa hồng nào.

- **Codex judge verdict:** FAIL -- realism=5, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=4, suspicious_span_accuracy=2
- **Judge reason:**

> Spans retain neutral contact evidence and omit the decisive task-scam cue.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [ ] PASS   [x] FAIL

**Notes:** Final triage: DROP.
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 070/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=1233
- **Record digest:** `198c8ef01e2a0cf4ae454176a1f2014720b1c573421a8d1e3e20000ebac924d9`
- **Evidence digest:** `bbb4b647c0ab8fe47074e8d282a7b9f257e26d26029d26a50e402d56ceedab4e`
- **Judge origin:** `carried_forward_exact_record`
- **Judge provenance source:** `data/processed/phase39-final-evidence/carry.jsonl` (SHA-256 `593b34ab8eb01d817b849e26aea1022dac422d2a1ef16822ffe44f5cb24b5ea8`)
- **Judge provenance iteration:** historical exact carry
- **Historical judge coordinate:** test:135
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Xin chào, bạn vừa nhận được một khoản chuyển tiền từ tài khoản 123456789 vào tài khoản của bạn. Số tiền: 2,000,000 VND. Nếu bạn không thực hiện giao dịch này, vui lòng liên hệ ngay với ngân hàng.

- **Label:** `benign`
- **Risk tier:** `benign`
- **Suspicious spans (JSON):** []
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_4e13065249e6`

### XAI explanation

> Thông báo xác nhận giao dịch chuyển tiền, thông tin rõ ràng và không có dấu hiệu đáng ngờ.

- **Codex judge verdict:** PASS -- realism=3, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:**

> Người nhận không thực hiện khoản tiền đến hơi thiếu logic.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [ ] PASS   [x] FAIL

**Notes:** Final triage: (Drop row): Illogical premise ("nhận được chuyển tiền" contradicts "nếu không thực hiện giao dịch") and contains a sequential placeholder account (`123456789`).
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 071/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=1277
- **Record digest:** `03a845498f5a8b4d36055719ba7a0388eb5dc350b079da364de6c2016e9b95f2`
- **Evidence digest:** `f9b69f0ae3c8dfd3590f4302ae0f6e4512ed88e8bb9d0376a9e3cd0a406f4445`
- **Judge origin:** `fresh_final_delta`
- **Judge provenance source:** `data/processed/codex-final-delta-judge.jsonl` (SHA-256 `8c152b519ca70ac9329b382dcafd8a91f09fcc8f0ed81600cbed0e6b98b584d5`)
- **Judge provenance iteration:** 0
- **Historical judge coordinate:** none (fresh final-delta judgment)
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Hệ thống đã tạo mã hoàn cho giao dịch đồ ăn của anh/chị nhưng chỉ giữ trong năm phút. Anh/chị cần bật chia sẻ màn hình rồi đọc mã xác nhận hoàn tiền để mình kích hoạt khoản trả lại.

- **Label:** `zalo_social_engineering`
- **Risk tier:** `high-risk`
- **Suspicious spans (JSON):** ["bật chia sẻ màn hình rồi đọc mã xác nhận hoàn tiền"]
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_f96fa34949cf`

### XAI explanation

> Tin nhắn tạo áp lực xử lý gấp và yêu cầu bật chia sẻ màn hình rồi đọc mã xác nhận hoàn tiền, có thể dẫn đến tài khoản ngân hàng bị chiếm đoạt.

- **Codex judge verdict:** PASS -- realism=4, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:**

> A five-minute refund window and request to share the screen and code are coherent scam cues, correctly labeled and rated high-risk.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [x] PASS   [ ] FAIL

**Notes:** 
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 072/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=1302
- **Record digest:** `26489ad5ff0afbb2e596eeeeee336987701a31f5ccb58b83861877caf88c1b1e`
- **Evidence digest:** `a835cb9404e69209416dfaeba74f76dbdf41649527a8647d9fd171b09b9008b7`
- **Judge origin:** `fresh_final_delta`
- **Judge provenance source:** `data/processed/codex-final-delta-judge.jsonl` (SHA-256 `8c152b519ca70ac9329b382dcafd8a91f09fcc8f0ed81600cbed0e6b98b584d5`)
- **Judge provenance iteration:** 0
- **Historical judge coordinate:** none (fresh final-delta judgment)
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Em là nhân viên kỹ thuật nhà mạng đang xử lý lỗi mất sóng cho số của anh/chị. Mình đọc mã OTP đổi SIM trong vòng mười lăm phút nhé, chậm hơn mã hết hạn và SIM vật lý sẽ bị khóa.

- **Label:** `zalo_social_engineering`
- **Risk tier:** `high-risk`
- **Suspicious spans (JSON):** ["đọc mã OTP đổi SIM"]
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_3662ea861e45`

### XAI explanation

> Tin nhắn tạo áp lực xử lý gấp và yêu cầu đọc mã OTP đổi SIM, có thể dẫn đến số điện thoại bị chiếm để nhận mã ngân hàng.

- **Codex judge verdict:** PASS -- realism=5, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:**

> The informal technician message is particularly natural Vietnamese and uses a credible expiry threat to solicit a SIM-transfer OTP.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [x] PASS   [ ] FAIL

**Notes:** 
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 073/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=1323
- **Record digest:** `4ab3208231409710f1dc669b14b4b4993e8d2aa52f7b43e56c8d1a18da917d8a`
- **Evidence digest:** `f019e72d034ebb653a06ea28f1b1fdcf0834d76efe168cd86ce88887406731de`
- **Judge origin:** `fresh_final_delta`
- **Judge provenance source:** `data/processed/codex-final-delta-judge.jsonl` (SHA-256 `8c152b519ca70ac9329b382dcafd8a91f09fcc8f0ed81600cbed0e6b98b584d5`)
- **Judge provenance iteration:** 0
- **Historical judge coordinate:** none (fresh final-delta judgment)
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Tôi đã đối chiếu vài chi tiết và có thể đây là giấy tờ của bạn. Làm giúp bước gửi ảnh căn cước và ảnh selfie cầm giấy tờ, hoàn tất tôi sẽ giữ ví lại thay vì chuyển cho người khác.

- **Label:** `zalo_social_engineering`
- **Risk tier:** `high-risk`
- **Suspicious spans (JSON):** ["gửi ảnh căn cước và ảnh selfie cầm giấy tờ"]
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_a23c0ac8b044`

### XAI explanation

> Tin nhắn tạo áp lực xử lý gấp và yêu cầu gửi ảnh căn cước và ảnh selfie cầm giấy tờ, có thể dẫn đến danh tính bị dùng để mở tài khoản giả.

- **Codex judge verdict:** PASS -- realism=4, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:**

> The promise to reserve found documents creates a credible lure for ID and selfie collection; high risk and the exact suspicious phrase are appropriate.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [x] PASS   [ ] FAIL

**Notes:** 
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 074/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=1355
- **Record digest:** `7517e4a4aca7060357b82f3c2796657c55ee2be8dd3bad66e3c323efb7ded013`
- **Evidence digest:** `ebafdbce2f8536a8c71fa2ca88eaffd0c292f738c4d6d6bfb97ab37ef3df244f`
- **Judge origin:** `carried_forward_exact_record`
- **Judge provenance source:** `data/processed/phase39-final-evidence/carry.jsonl` (SHA-256 `593b34ab8eb01d817b849e26aea1022dac422d2a1ef16822ffe44f5cb24b5ea8`)
- **Judge provenance iteration:** historical exact carry
- **Historical judge coordinate:** train:1563
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> ⚠️ AGRIBANK: Phát hiện đăng nhập bất thường vào app của bạn. Tài khoản sẽ bị tạm khóa sau 30 phút nếu ko xác minh danh tính. Nhấp vào đây để xác minh ngay: bit.ly/agri-verify2024 — Nhập CMND + mật khẩu Internet Banking để mở khóa. Bỏ qua tin nhắn này nếu bạn đã xác nhận.

- **Label:** `bank_impersonation`
- **Risk tier:** `high-risk`
- **Suspicious spans (JSON):** ["bit.ly/agri-verify2024", "Nhập CMND + mật khẩu Internet Banking để mở khóa", "Tài khoản sẽ bị tạm khóa sau 30 phút"]
- **Source:** `synthetic_claude`
- **Seed ID:** `seed_3f61921e9655`

### XAI explanation

> Tin nhắn giả mạo Agribank sử dụng URL rút gọn 'bit.ly' để che giấu tên miền thật của trang web lừa đảo. Yêu cầu nhập đồng thời CMND và mật khẩu Internet Banking là cực kỳ nguy hiểm - không ngân hàng nào yêu cầu thông tin nhạy cảm như vậy qua link nhắn tin. Đây là trang web giả mạo nhằm đánh cắp toàn bộ thông tin đăng nhập.

- **Codex judge verdict:** PASS -- realism=4, label_correctness=5, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:**

> Bitly và yêu cầu CMND cùng mật khẩu đúng phishing ngân hàng.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [x] PASS   [ ] FAIL

**Notes:** 
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 075/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=1371
- **Record digest:** `1a37c71c57ce51a22ab6c174c46e12017218434b7fd7d5783b8276c6edc42ac1`
- **Evidence digest:** `c6cf2dfa916cfd2c8bf1926c0c3204b531df1bea12c3f0cf566db83ddd132bda`
- **Judge origin:** `carried_forward_exact_record`
- **Judge provenance source:** `data/processed/phase39-final-evidence/carry.jsonl` (SHA-256 `593b34ab8eb01d817b849e26aea1022dac422d2a1ef16822ffe44f5cb24b5ea8`)
- **Judge provenance iteration:** historical exact carry
- **Historical judge coordinate:** train:1579
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Bạn ơi mình là ctv hdbank nè. Hôm nay NH có ct ưu đãi hoàn tiền 15% cho khách mở tk mới qua link này nha: hdbank-promo.page.link/moitk - đăng ký dc ngay hôm nay thôi ak, ct chỉ còn 50 suất. Bạn chỉ cần nhập CMND + ảnh selfie + login internet banking cũ (nếu có) để verify. Nhanh lên không hết slot 😅

- **Label:** `bank_impersonation`
- **Risk tier:** `high-risk`
- **Suspicious spans (JSON):** ["hdbank-promo.page.link/moitk", "nhập CMND + ảnh selfie + login internet banking cũ", "ct chỉ còn 50 suất", "ctv hdbank"]
- **Source:** `synthetic_claude`
- **Seed ID:** `seed_3f61921e9655`

### XAI explanation

> Tin nhắn dùng phong cách thân thiện, teencode (nè, nha, ak, dc) để giảm cảnh giác, giả mạo 'cộng tác viên HDBank'. Link dùng page.link (Firebase Dynamic Links) để che giấu URL thật thay vì domain chính thức hdbank.com.vn. Yêu cầu kết hợp CMND + ảnh selfie + thông tin Internet Banking là bộ dữ liệu đủ để làm giả danh tính và chiếm tài khoản. Chiêu 'chỉ còn 50 suất' là kỹ thuật khan hiếm giả tạo để thúc đẩy hành động nhanh không suy nghĩ.

- **Codex judge verdict:** PASS -- realism=4, label_correctness=5, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:**

> Mạo danh cộng tác viên, link lạ và xin selfie cùng login rất nguy hiểm.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [x] PASS   [ ] FAIL

**Notes:** 
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 076/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=1460
- **Record digest:** `d1ff861f9d4f8aaaa8f893c76ba401d6f0856af6c5422aba80a62ed4c9dd6bb7`
- **Evidence digest:** `7243a6773b25a5f0fad6e1804a2968f7596078f82d6f28e7dd1b07163628a6cc`
- **Judge origin:** `carried_forward_exact_record`
- **Judge provenance source:** `data/processed/phase39-final-evidence/carry.jsonl` (SHA-256 `593b34ab8eb01d817b849e26aea1022dac422d2a1ef16822ffe44f5cb24b5ea8`)
- **Judge provenance iteration:** historical exact carry
- **Historical judge coordinate:** train:1668
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> MB Bank: Tai khoan cua ban bi han che giao dich do chua xac thuc eKYC. Dang nhap app MB ngay tai: mb-bank-ekyc.vn/verify hoac tk se bi khoa vinh vien. Lien he hotline gia mao: 0938.112.334

- **Label:** `bank_impersonation`
- **Risk tier:** `high-risk`
- **Suspicious spans (JSON):** ["mb-bank-ekyc.vn/verify", "tk se bi khoa vinh vien", "0938.112.334"]
- **Source:** `synthetic_claude`
- **Seed ID:** `seed_3f61921e9655`

### XAI explanation

> Tin nhắn SMS giả danh MB Bank với tên miền 'mb-bank-ekyc.vn' không phải domain chính thức của ngân hàng (mbbank.com.vn). Cụm từ 'khóa vĩnh viễn' tạo áp lực giả tạo. Số hotline 0938.112.334 là đầu số cá nhân, không phải tổng đài ngân hàng.

- **Codex judge verdict:** FAIL -- realism=2, label_correctness=5, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:**

> Cụm hotline giả mạo tự tiết lộ phishing, làm tin thiếu hiện thực.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [ ] PASS   [x] FAIL

**Notes:** Final triage: (Drop row): Unrealistic synthetic text containing the literal self-exposing phrase "hotline gia mao" (fake hotline).
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 077/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=1517
- **Record digest:** `b5badd15a51567ec021ebca448287db85595243b7eadda797db32a358a34f5a1`
- **Evidence digest:** `1e001c6187bbd9986ca87994bea29c8f8e8470917acba6d04d9e1d2240da4b0b`
- **Judge origin:** `carried_forward_exact_record`
- **Judge provenance source:** `data/processed/phase39-final-evidence/carry.jsonl` (SHA-256 `593b34ab8eb01d817b849e26aea1022dac422d2a1ef16822ffe44f5cb24b5ea8`)
- **Judge provenance iteration:** historical exact carry
- **Historical judge coordinate:** train:1367
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> BIDV Sao Kê Tháng 6/2025 — Tài khoản: ***4521
> Tổng thu: 18,200,000 VND
> Tổng chi: 11,750,000 VND
> Số dư cuối kỳ: 6,450,000 VND
> Xem chi tiết sao kê tại quầy giao dịch hoặc đăng nhập Internet Banking tại bidv.com.vn

- **Label:** `benign`
- **Risk tier:** `suspicious`
- **Suspicious spans (JSON):** []
- **Source:** `synthetic_claude`
- **Seed ID:** `seed_825b9e38d185`

### XAI explanation

> Thông báo sao kê tháng định kỳ từ BIDV. Tin nhắn trình bày thông tin tài chính tóm tắt rõ ràng theo định dạng chuẩn của ngân hàng. Số tài khoản được che một phần để bảo mật. Đường dẫn được đề cập là tên miền chính thức bidv.com.vn và hướng dẫn đến quầy giao dịch — không có yêu cầu bất thường.

- **Codex judge verdict:** FAIL -- realism=4, label_correctness=5, code_switch_naturalness=4, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge reason:**

> Sao kê chỉ dẫn kênh BIDV chính thức, không có dấu hiệu suspicious.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [ ] PASS   [x] FAIL

**Notes:** Final triage: (Fix tier): Keep label `benign`, but fix risk tier from `suspicious` to `benign` (standard official e-statement summary).
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 078/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=1611
- **Record digest:** `a514524e2d156bd11fd98aa7f587ed526f539cb89bef1387cc41b12501f4e1b3`
- **Evidence digest:** `6d018a2a72f468581da18b6976e17979d4f1785a5e9abc1e16b9350405311aa5`
- **Judge origin:** `carried_forward_exact_record`
- **Judge provenance source:** `data/processed/phase39-final-evidence/carry.jsonl` (SHA-256 `593b34ab8eb01d817b849e26aea1022dac422d2a1ef16822ffe44f5cb24b5ea8`)
- **Judge provenance iteration:** historical exact carry
- **Historical judge coordinate:** train:1464
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> VCB: Ma OTP cua ban la 847291. OTP co hieu luc trong 90 giay. Khong chia se ma OTP nay voi bat ky ai, ke ca nhan vien ngan hang. Moi thac mac lien he 1800 545 413.

- **Label:** `benign`
- **Risk tier:** `suspicious`
- **Suspicious spans (JSON):** []
- **Source:** `synthetic_claude`
- **Seed ID:** `seed_825b9e38d185`

### XAI explanation

> Tin nhắn OTP hợp lệ từ Vietcombank. Tin nhắn chủ động cảnh báo người dùng không chia sẻ OTP, đây là dấu hiệu của tin nhắn chính thống. Không có liên kết hay yêu cầu hành động đáng ngờ.

- **Codex judge verdict:** PASS -- realism=5, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=4, suspicious_span_accuracy=5
- **Judge reason:**

> OTP chuẩn có cảnh báo và hotline, phù hợp mức suspicious.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [ ] PASS   [x] FAIL

**Notes:** Final triage: DROP because i am sure this message is a damn narrator
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 079/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=train row_index=1619
- **Record digest:** `45f1b3b168d04be713b494aaa19de6b57778049c696ccb65f55e7b17f0ad8f8f`
- **Evidence digest:** `8d63d6f3f2f133ed8acd505f440f9bf2ec8b47e20196aa63b15872033c1c67eb`
- **Judge origin:** `carried_forward_exact_record`
- **Judge provenance source:** `data/processed/phase39-final-evidence/carry.jsonl` (SHA-256 `593b34ab8eb01d817b849e26aea1022dac422d2a1ef16822ffe44f5cb24b5ea8`)
- **Judge provenance iteration:** historical exact carry
- **Historical judge coordinate:** train:1472
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> BIDV gui ban: Uu dai dac biet thang 7 - Hoan tien 10% khi thanh toan hoa don dien, nuoc, internet qua BIDV SmartBanking. Toi da hoan tien 200,000 VND/thang. Dang ky ngay tai app BIDV SmartBanking. Hotline: 1900 9247.

- **Label:** `benign`
- **Risk tier:** `benign`
- **Suspicious spans (JSON):** []
- **Source:** `synthetic_claude`
- **Seed ID:** `seed_825b9e38d185`

### XAI explanation

> Tin nhắn marketing hợp lệ từ BIDV về chương trình hoàn tiền. Được xếp mức low vì có yếu tố khuyến mại tạo cảm giác khẩn cấp nhẹ, nhưng thông tin đầy đủ, không yêu cầu dữ liệu nhạy cảm và hotline chính thức được cung cấp.

- **Codex judge verdict:** PASS -- realism=4, label_correctness=5, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:**

> Ưu đãi hóa đơn qua BIDV SmartBanking và hotline phù hợp benign.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [x] PASS   [ ] FAIL

**Notes:** 
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 080/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=val row_index=15
- **Record digest:** `160ff1d49d9da38bd033ccee2cf030e861dd3546bf6572bf9e1ebdba92234851`
- **Evidence digest:** `57fa81e435162e09ab9fecd5cc985a0954ea9271bad4ef606804d692d834d6e2`
- **Judge origin:** `carried_forward_exact_record`
- **Judge provenance source:** `data/processed/phase39-final-evidence/carry.jsonl` (SHA-256 `593b34ab8eb01d817b849e26aea1022dac422d2a1ef16822ffe44f5cb24b5ea8`)
- **Judge provenance iteration:** historical exact carry
- **Historical judge coordinate:** train:123
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Chị ơi, em là nhân viên hỗ trợ của BIDV. Hệ thống phát hiện có giao dịch khả nghi từ tài khoản của chị. Để xác nhận, chị vui lòng chuyển 10% số dư hiện tại vào tài khoản 1234567890123456 để kiểm tra. Cảm ơn chị!

- **Label:** `bank_impersonation`
- **Risk tier:** `suspicious`
- **Suspicious spans (JSON):** ["1234567890123456"]
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_56fbdd095f41`

### XAI explanation

> Tin nhắn này có thể là giả mạo, yêu cầu bạn chuyển tiền vào tài khoản không rõ nguồn gốc.

- **Codex judge verdict:** FAIL -- realism=2, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=1, suspicious_span_accuracy=2
- **Judge reason:**

> Explicit generic or sequential placeholder makes the message artificial.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [ ] PASS   [x] FAIL

**Notes:** Final triage: (Drop row): Contains an obvious sequential synthetic placeholder bank account (`1234567890123456`) and risk tier mismatch (10% balance transfer demand requires `high-risk` tier).
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 081/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=val row_index=18
- **Record digest:** `83227bdfa6fbdea03fd110ac0a70fd81c60cff525f5d49067c8f34923810d4f1`
- **Evidence digest:** `efd0d6519bf2820e3444f2112de10bc75967dd2a6696dcc939fc2a0d7fa38127`
- **Judge origin:** `carried_forward_exact_record`
- **Judge provenance source:** `data/processed/phase39-final-evidence/carry.jsonl` (SHA-256 `593b34ab8eb01d817b849e26aea1022dac422d2a1ef16822ffe44f5cb24b5ea8`)
- **Judge provenance iteration:** historical exact carry
- **Historical judge coordinate:** train:161
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Chị ơi, em là Mai, nhân viên của Agribank. Hệ thống của chúng tôi phát hiện có giao dịch khả nghi từ tài khoản của chị. Để đảm bảo an toàn, chị vui lòng đăng nhập vào app Agribank và xác minh lại OTP nha. Nếu cần hỗ trợ, chị có thể liên hệ 0987654321.

- **Label:** `bank_impersonation`
- **Risk tier:** `suspicious`
- **Suspicious spans (JSON):** ["0987654321"]
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_e5463bf1077a`

### XAI explanation

> Không chia sẻ OTP hoặc thông tin cá nhân qua điện thoại hoặc email.

- **Codex judge verdict:** FAIL -- realism=4, label_correctness=3, code_switch_naturalness=5, risk_tier_correctness=3, suspicious_span_accuracy=2
- **Judge reason:**

> Contact-only spans miss the impersonation or paid-task lure that makes the message suspicious.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [ ] PASS   [x] FAIL

**Notes:** Final triage: DROP
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 082/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=val row_index=42
- **Record digest:** `efc4e0bb8a2473e171579104b48d49c8874506b7303327a728631c5464454053`
- **Evidence digest:** `402c77e08a1953d60b879e16844d9d3701db654c492893b164dc230e9fda224e`
- **Judge origin:** `fresh_final_delta`
- **Judge provenance source:** `data/processed/codex-final-delta-judge.jsonl` (SHA-256 `8c152b519ca70ac9329b382dcafd8a91f09fcc8f0ed81600cbed0e6b98b584d5`)
- **Judge provenance iteration:** 0
- **Historical judge coordinate:** none (fresh final-delta judgment)
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Bạn ơi, tớ là admin của Shopee shop ABC. Hiện tại shop đang cần người mua sản phẩm và đánh giá 5 sao. Bạn sẽ được hoàn lại tiền mua hàng và nhận thêm 10% hoa hồng. Để bắt đầu, vui lòng chuyển tiền trước 200k vào tài khoản XYZ123456789. Sau khi xác nhận đơn hàng, shop sẽ hoàn tiền và trả hoa hồng. Rất mong hợp tác!

- **Label:** `task_scam`
- **Risk tier:** `high-risk`
- **Suspicious spans (JSON):** ["XYZ123456789", "chuyển tiền trước 200k vào tài khoản XYZ123456789"]
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_0dbd0f1e898c`

### XAI explanation

> Hãy cẩn thận với các yêu cầu chuyển tiền trước khi nhận công việc.

- **Codex judge verdict:** PASS -- realism=3, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:**

> The shop-review task pitch is somewhat scripted but realistic enough, and the advance 200k transfer is an exact high-risk task-scam cue.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [x] PASS   [ ] FAIL

**Notes:** 
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 083/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=val row_index=44
- **Record digest:** `23789c2cfaa987f8c7e5751d913c3f1451e2f9172e252019ea8967175d88176e`
- **Evidence digest:** `0164ae6d2a44f3f2327e7bba546df706f5f0df8da50a49ebfc4cbad0af0606ac`
- **Judge origin:** `fresh_final_delta`
- **Judge provenance source:** `data/processed/codex-final-delta-judge.jsonl` (SHA-256 `8c152b519ca70ac9329b382dcafd8a91f09fcc8f0ed81600cbed0e6b98b584d5`)
- **Judge provenance iteration:** 1
- **Historical judge coordinate:** none (fresh final-delta judgment)
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Xin chào, OTP xác nhận đăng nhập vào ứng dụng ngân hàng của bạn là 123456. Vui lòng nhập mã này ngay để hoàn tất quá trình đăng nhập. Mã này chỉ có hiệu lực trong 5 phút. ABBank.

- **Label:** `benign`
- **Risk tier:** `benign`
- **Suspicious spans (JSON):** []
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_c6c8772ac332`

### XAI explanation

> Đây là thông báo OTP đăng nhập thông thường của ABBank; người nhận chỉ nên dùng mã cho giao dịch do mình khởi tạo và không chia sẻ mã.

- **Codex judge verdict:** PASS -- realism=5, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:**

> This is a standard time-limited ABBank login OTP notice with no outside contact or sharing request; benign risk, empty spans, and safety XAI agree.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [x] PASS   [ ] FAIL

**Notes:** 
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 084/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=val row_index=46
- **Record digest:** `2b2cbc2acb8a700bb657a31960f837c4d5c8863b37dfc733bbfd058cbd24b05b`
- **Evidence digest:** `d8df59689e60a5a9ad4a62925baabc5f7eea04b519e959fc738bef44359c5ce2`
- **Judge origin:** `fresh_final_delta`
- **Judge provenance source:** `data/processed/codex-final-delta-judge.jsonl` (SHA-256 `8c152b519ca70ac9329b382dcafd8a91f09fcc8f0ed81600cbed0e6b98b584d5`)
- **Judge provenance iteration:** 0
- **Historical judge coordinate:** none (fresh final-delta judgment)
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Xin chào, mình là đại diện của Binance. Chúng tôi đang tìm người giới thiệu bạn bè đăng ký tài khoản trên Binance thông qua link của bạn. Mỗi người đăng ký thành công, bạn nhận 20% hoa hồng. Link đăng ký: https://binance.com/register/123456. Bạn có quan tâm không?

- **Label:** `benign`
- **Risk tier:** `suspicious`
- **Suspicious spans (JSON):** ["https://binance.com/register/123456"]
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_4af17fdb851a`

### XAI explanation

> Cẩn thận với các chương trình giới thiệu, đặc biệt khi yêu cầu đăng ký qua link cá nhân.

- **Codex judge verdict:** PASS -- realism=4, label_correctness=4, code_switch_naturalness=4, risk_tier_correctness=4, suspicious_span_accuracy=4
- **Judge reason:**

> An unsolicited but otherwise ordinary referral offer using the legitimate Binance domain can be benign yet suspicious; the link is a reasonable caution cue.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [x] PASS   [ ] FAIL

**Notes:** 
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 085/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=val row_index=56
- **Record digest:** `3e15813dd350a6ec97174b2295c8cb2993e439c4934779433964635e71fbf6f3`
- **Evidence digest:** `9bfca573b67b2a9af35ff652bbf0cb35b8f1bddf6136fd9404414938e19452e6`
- **Judge origin:** `carried_forward_exact_record`
- **Judge provenance source:** `data/processed/phase39-final-evidence/carry.jsonl` (SHA-256 `593b34ab8eb01d817b849e26aea1022dac422d2a1ef16822ffe44f5cb24b5ea8`)
- **Judge provenance iteration:** historical exact carry
- **Historical judge coordinate:** train:681
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Chào bạn, mình là admin của nhóm TikTok lớn. Mình đang tìm người để like, follow và comment cho các video. Mỗi task bạn sẽ được trả 10k. Làm ngay hôm nay nhé! Liên hệ qua Zalo 0987654321. Đừng bỏ lỡ cơ hội kiếm tiền dễ dàng này!

- **Label:** `task_scam`
- **Risk tier:** `suspicious`
- **Suspicious spans (JSON):** ["Zalo 0987654321"]
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_c6c8772ac332`

### XAI explanation

> Cần cẩn thận với các lời mời like, follow, comment trên TikTok; có thể là lừa đảo.

- **Codex judge verdict:** FAIL -- realism=5, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=4, suspicious_span_accuracy=2
- **Judge reason:**

> Contact-only spans miss the impersonation or paid-task lure that makes the message suspicious.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [ ] PASS   [x] FAIL

**Notes:** Final triage: (Fix spans): Keep label `task_scam` and tier `suspicious`, but expand contact-only spans to include task and reward cues ("10k", "like, follow và comment").
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 086/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=val row_index=91
- **Record digest:** `29f445f54d88599cb6196a2f955171eff87ed16e85c39f6c45f25ba1d640ee35`
- **Evidence digest:** `e20b0c13dd501dcb52da6ab562c5366d74b3e8e09383282c4295d8fed161381d`
- **Judge origin:** `carried_forward_exact_record`
- **Judge provenance source:** `data/processed/phase39-final-evidence/carry.jsonl` (SHA-256 `593b34ab8eb01d817b849e26aea1022dac422d2a1ef16822ffe44f5cb24b5ea8`)
- **Judge provenance iteration:** historical exact carry
- **Historical judge coordinate:** train:1018
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Thông báo từ ngân hàng: Chúng tôi sẽ nâng cấp hệ thống từ 23h ngày 15/10 đến 2h ngày 16/10. Trong thời gian này, một số dịch vụ có thể bị tạm ngưng.

- **Label:** `benign`
- **Risk tier:** `suspicious`
- **Suspicious spans (JSON):** []
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_0dbd0f1e898c`

### XAI explanation

> Thông báo về việc nâng cấp hệ thống, nội dung thông tin minh bạch và rõ ràng.

- **Codex judge verdict:** FAIL -- realism=5, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=1, suspicious_span_accuracy=5
- **Judge reason:**

> Lịch bảo trì cụ thể là tier benign, không suspicious.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [ ] PASS   [x] FAIL

**Notes:** Final triage: (Fix tier): Keep label `benign`, but fix risk tier from `suspicious` to `benign` (standard official scheduled maintenance notice).
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 087/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=val row_index=104
- **Record digest:** `3f77606f7a065f24bbca960ec81090cecedd6789608fda155f8b885610d25983`
- **Evidence digest:** `53fbe33ef5f8bf03a2a5dec2667655db227b1286a5295a48843481675a27eee7`
- **Judge origin:** `fresh_final_delta`
- **Judge provenance source:** `data/processed/codex-final-delta-judge.jsonl` (SHA-256 `8c152b519ca70ac9329b382dcafd8a91f09fcc8f0ed81600cbed0e6b98b584d5`)
- **Judge provenance iteration:** 0
- **Historical judge coordinate:** none (fresh final-delta judgment)
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Bạn còn thiếu bước xác nhận trong cuộc bỏ phiếu quản trị viên của khu mình. Vui lòng quét mã QR này để xác nhận phiếu bầu ngay, hệ thống chốt kết quả lúc hết mười phút.

- **Label:** `zalo_social_engineering`
- **Risk tier:** `high-risk`
- **Suspicious spans (JSON):** ["quét mã QR này để xác nhận phiếu bầu"]
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_c91388584205`

### XAI explanation

> Tin nhắn tạo áp lực xử lý gấp và yêu cầu quét mã QR này để xác nhận phiếu bầu, có thể dẫn đến tài khoản Zalo bị đăng nhập trên máy của kẻ gian.

- **Codex judge verdict:** PASS -- realism=4, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:**

> The missing-vote reminder naturally pressures an immediate QR scan, consistent with high-risk Zalo social engineering and literal evidence.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [x] PASS   [ ] FAIL

**Notes:** 
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 088/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=val row_index=178
- **Record digest:** `291bf36956991d4cd70a717ee11b5d6cac6fe217ac9d0a7c1792a832a324be32`
- **Evidence digest:** `a76793e7d6718f679d6b03a9e6ea2f1de292b856659c5cba7e038b9d6e5e38ba`
- **Judge origin:** `fresh_final_delta`
- **Judge provenance source:** `data/processed/codex-final-delta-judge.jsonl` (SHA-256 `8c152b519ca70ac9329b382dcafd8a91f09fcc8f0ed81600cbed0e6b98b584d5`)
- **Judge provenance iteration:** 0
- **Historical judge coordinate:** none (fresh final-delta judgment)
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> OTP cua bn la 123456, xin vui long nhap ma OTP nay de xac nhan giao dich. Neu ban khong co yeu cau nao, hay lien he 0987654321 de bao cao ngay luon nha. Cam on!

- **Label:** `benign`
- **Risk tier:** `suspicious`
- **Suspicious spans (JSON):** ["0987654321", "123456"]
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_d53ed10ecc4a`

### XAI explanation

> Không chia sẻ mã OTP cho bất kỳ ai và kiểm tra lại yêu cầu giao dịch của bạn.

- **Codex judge verdict:** PASS -- realism=3, label_correctness=4, code_switch_naturalness=5, risk_tier_correctness=3, suspicious_span_accuracy=3
- **Judge reason:**

> The unaccented shorthand resembles a low-quality transactional SMS; it can be benign, while the separate callback number justifies caution and suspicious risk.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [ ] PASS   [x] FAIL

**Notes:** Final triage: (Drop row): Synthetic unaccented text containing obvious dummy placeholders (`123456` and `0987654321`).
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 089/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=val row_index=180
- **Record digest:** `070d5d75bb1c9efff07727606c6fe3b2674ff9e62eaf915e9cc67fe37124f669`
- **Evidence digest:** `3843b2525946324616f11626c2eb4f4b42b26b2e7882b518404b623479123ef4`
- **Judge origin:** `carried_forward_exact_record`
- **Judge provenance source:** `data/processed/phase39-final-evidence/carry.jsonl` (SHA-256 `593b34ab8eb01d817b849e26aea1022dac422d2a1ef16822ffe44f5cb24b5ea8`)
- **Judge provenance iteration:** historical exact carry
- **Historical judge coordinate:** test:102
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Chào bạn, mình là quản trị viên của nhóm TikTok. Hiện tại, mình đang cần người like, follow, và comment trên các video. Mỗi tác vụ được trả 5k, thanh toán qua Momo sau mỗi 50 task. Nếu quan tâm, vui lòng add Zalo 0987654321 để biết thêm chi tiết. Đừng bỏ lỡ cơ hội kiếm tiền dễ dàng này, nha! 🤑

- **Label:** `task_scam`
- **Risk tier:** `suspicious`
- **Suspicious spans (JSON):** ["0987654321", "Momo"]
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_d53ed10ecc4a`

### XAI explanation

> Tin nhắn này yêu cầu bạn thực hiện các tác vụ trên TikTok để nhận thù lao, nhưng có thể là một chiêu trò lừa đảo để lấy thông tin cá nhân.

- **Codex judge verdict:** FAIL -- realism=5, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=4, suspicious_span_accuracy=2
- **Judge reason:**

> Số Zalo và Momo là bằng chứng trung tính, bỏ sót nhiệm vụ tương tác trả tiền.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [ ] PASS   [x] FAIL

**Notes:** Final triage: (Fix spans): Keep label `task_scam` and tier `suspicious`, but expand spans to include task engagement cues ("5k", "like, follow, và comment") instead of neutral "Momo".
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 090/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=val row_index=182
- **Record digest:** `fc9962bd363f0b19e55037848569cd53b17f37844ad94fc49931861bbcdb8945`
- **Evidence digest:** `fb97b5b962c4c7defd59fb05604170da42e08603a13f4d558ee3c4c9625a5aa9`
- **Judge origin:** `carried_forward_exact_record`
- **Judge provenance source:** `data/processed/phase39-final-evidence/carry.jsonl` (SHA-256 `593b34ab8eb01d817b849e26aea1022dac422d2a1ef16822ffe44f5cb24b5ea8`)
- **Judge provenance iteration:** historical exact carry
- **Historical judge coordinate:** test:105
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Xin chào, mình là admin của group Binance Việt Nam. Bạn có muốn kiếm tiền từ việc giới thiệu người mới đăng ký tài khoản không? Chỉ cần gửi link giới thiệu của mình cho bạn bè, bạn sẽ nhận được 10% hoa hồng từ giao dịch của họ. Liên hệ với mình qua Telegram @CryptoAdmin để biết thêm chi tiết. Cơ hội này không thể bỏ qua, nha! 🚀

- **Label:** `task_scam`
- **Risk tier:** `suspicious`
- **Suspicious spans (JSON):** ["@CryptoAdmin", "10% hoa hồng"]
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_d53ed10ecc4a`

### XAI explanation

> Tin nhắn này đề nghị bạn giới thiệu người mới đăng ký tài khoản Binance để nhận hoa hồng, nhưng có thể là một chiêu trò lừa đảo để thu thập thông tin cá nhân.

- **Codex judge verdict:** PASS -- realism=4, label_correctness=3, code_switch_naturalness=5, risk_tier_correctness=3, suspicious_span_accuracy=4
- **Judge reason:**

> Có thể là affiliate hợp lệ, nhưng recruiter Telegram và lời hứa khá đáng ngờ.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [ ] PASS   [x] FAIL

**Notes:** Final triage: relabel to benign, retain suspicious; it describes affiliate recruitment without a fraudulent task/payment mechanism.
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 091/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=test row_index=42
- **Record digest:** `a9dd19dbff9ca25f14cf688786ab5a70dc52f8dc8e4c0019043a31000eedc972`
- **Evidence digest:** `5ad5a9dbc47040b17a8ab9fe2d7c749890c5bf640b87d7123fa1cc2eefe8c360`
- **Judge origin:** `carried_forward_exact_record`
- **Judge provenance source:** `data/processed/phase39-final-evidence/carry.jsonl` (SHA-256 `593b34ab8eb01d817b849e26aea1022dac422d2a1ef16822ffe44f5cb24b5ea8`)
- **Judge provenance iteration:** historical exact carry
- **Historical judge coordinate:** train:272
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Chào anh/chị, đây là MB Bank. Chúng tôi cần xác minh lại thông tin tài khoản của anh/chị. Vui lòng đăng nhập vào app MB và làm theo hướng dẫn. Nếu ko, tài khoản của anh/chị sẽ bị khóa ngay lập tức.

- **Label:** `bank_impersonation`
- **Risk tier:** `suspicious`
- **Suspicious spans (JSON):** []
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_f2ad8ed2c10d`

### XAI explanation

> Thông báo yêu cầu xác minh thông tin qua ứng dụng, có thể là lừa đảo.

- **Codex judge verdict:** FAIL -- realism=4, label_correctness=3, code_switch_naturalness=5, risk_tier_correctness=3, suspicious_span_accuracy=1
- **Judge reason:**

> Official-app guidance is ambiguous, and the empty span list omits the lock threat.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [ ] PASS   [x] FAIL

**Notes:** Final triage: (Drop row): Directs users solely to the official MB app without an external link or credential-harvesting payload, resulting in empty suspicious spans.
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 092/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=test row_index=57
- **Record digest:** `c4fd7bf94462d8e93ecfc514c4f38a37dfd8ea8758951d2bb3d0b49348e9c1ca`
- **Evidence digest:** `4b7676f7c033059bd5a51f7885ed52e09e15d774251ec045ee80bffe99ebdf22`
- **Judge origin:** `fresh_final_delta`
- **Judge provenance source:** `data/processed/codex-final-delta-judge.jsonl` (SHA-256 `8c152b519ca70ac9329b382dcafd8a91f09fcc8f0ed81600cbed0e6b98b584d5`)
- **Judge provenance iteration:** 1
- **Historical judge coordinate:** none (fresh final-delta judgment)
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Chào anh/chị, đây là thông báo từ Ngân hàng ACB. Vui lòng đăng nhập vào ứng dụng Internet Banking để xác nhận giao dịch gần đây. Nếu không, tài khoản của anh/chị có thể bị khóa. Link: http://acb-bank-login.com

- **Label:** `bank_impersonation`
- **Risk tier:** `high-risk`
- **Suspicious spans (JSON):** ["http://acb-bank-login.com"]
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_1a0c3ea29c59`

### XAI explanation

> Tên miền acb-bank-login.com giả mạo ACB và yêu cầu đăng nhập dưới áp lực khóa tài khoản, có thể làm lộ thông tin Internet Banking.

- **Codex judge verdict:** PASS -- realism=5, label_correctness=5, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:**

> The ACB lock threat directs a login to the lookalike acb-bank-login.com domain, a clear high-risk bank phishing attempt with precise XAI and span.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [x] PASS   [ ] FAIL

**Notes:** 
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 093/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=test row_index=58
- **Record digest:** `e71e332f4e2005d8495aa449a787e1d91bdc2650068389a10ba08255f87ae340`
- **Evidence digest:** `6eacdf07dc00e0d76cd9a06a2a6522918d9ca085d56b921cce8335c2cc62f234`
- **Judge origin:** `carried_forward_exact_record`
- **Judge provenance source:** `data/processed/phase39-final-evidence/carry.jsonl` (SHA-256 `593b34ab8eb01d817b849e26aea1022dac422d2a1ef16822ffe44f5cb24b5ea8`)
- **Judge provenance iteration:** historical exact carry
- **Historical judge coordinate:** train:399
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Chào bạn, mình là quản trị viên của nhóm TikTok 'Cộng Đồng Kiếm Tiền Online'. Hiện tại, chúng tôi đang cần người like, follow và comment cho các video. Mức lương: 10k/like, 15k/follow, 20k/comment. Để bắt đầu, hãy truy cập link này: http://tiktokjob.com/registration. Đừng bỏ lỡ cơ hội kiếm tiền dễ dàng này!.

- **Label:** `task_scam`
- **Risk tier:** `suspicious`
- **Suspicious spans (JSON):** ["http://tiktokjob.com/registration"]
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_874917391eac`

### XAI explanation

> Link dẫn đến trang web không rõ nguồn gốc yêu cầu đăng ký để thực hiện các nhiệm vụ like/follow/comment.

- **Codex judge verdict:** PASS -- realism=4, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=4, suspicious_span_accuracy=5
- **Judge reason:**

> Classic easy-money engagement recruitment with a suspicious registration domain.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [x] PASS   [ ] FAIL

**Notes:** 
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 094/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=test row_index=69
- **Record digest:** `1b7a5ad64a56bc09d32b5888d9e6470b1749b729ffa64f9d72e3008f32141da9`
- **Evidence digest:** `6e52749f41adb33ffdbfd506c4e1d09f8a8a89fd30faf0aa875f4dff740e78ba`
- **Judge origin:** `fresh_final_delta`
- **Judge provenance source:** `data/processed/codex-final-delta-judge.jsonl` (SHA-256 `8c152b519ca70ac9329b382dcafd8a91f09fcc8f0ed81600cbed0e6b98b584d5`)
- **Judge provenance iteration:** 1
- **Historical judge coordinate:** none (fresh final-delta judgment)
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Anh/Chị ơi, em là nhân viên của BIDV. Hệ thống của chúng tôi đang nâng cấp, vui lòng đăng nhập lại vào app để xác nhận thông tin. Link: https://bidv-upgrade.info

- **Label:** `bank_impersonation`
- **Risk tier:** `high-risk`
- **Suspicious spans (JSON):** ["https://bidv-upgrade.info"]
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_1a0c3ea29c59`

### XAI explanation

> Tránh click vào link lạ, hãy mở app hoặc truy cập web chính thức của BIDV trực tiếp.

- **Codex judge verdict:** PASS -- realism=5, label_correctness=5, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:**

> The fake BIDV upgrade directs reauthentication through a nonofficial .info domain, cleanly supporting bank impersonation, high risk, and the URL span.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [x] PASS   [ ] FAIL

**Notes:** 
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 095/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=test row_index=71
- **Record digest:** `723a54fba48a2312196a8095042f54be3c03ed575a21f844e93e3b0a4f17975b`
- **Evidence digest:** `b99f579bff1eff7eba9220d35c29b5701a45304e8da19548573c4b2cebe797a1`
- **Judge origin:** `fresh_final_delta`
- **Judge provenance source:** `data/processed/codex-final-delta-judge.jsonl` (SHA-256 `8c152b519ca70ac9329b382dcafd8a91f09fcc8f0ed81600cbed0e6b98b584d5`)
- **Judge provenance iteration:** 0
- **Historical judge coordinate:** none (fresh final-delta judgment)
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Chào bạn, mình là support của Binance. Hiện tại chúng tôi có chương trình khuyến mãi: Đăng ký tài khoản qua link của mình, bạn sẽ nhận được 10% hoa hồng từ mỗi giao dịch. Link đăng ký: http://fakebinance.com/register. Nếu muốn rút tiền, bạn cần trả phí xác minh 100k VND. Cơ hội tuyệt vời, nhanh tay đăng ký nhé!

- **Label:** `task_scam`
- **Risk tier:** `high-risk`
- **Suspicious spans (JSON):** ["http://fakebinance.com/register", "trả phí xác minh 100k VND"]
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_aac4f3d94e74`

### XAI explanation

> Đây là một kịch bản lừa đảo yêu cầu bạn đăng ký trên một trang web giả mạo. Phí xác minh sẽ không bao giờ được hoàn lại.

- **Codex judge verdict:** PASS -- realism=4, label_correctness=5, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:**

> A support impersonator offers referral commission but blocks withdrawal behind a fee; the fake link and fee are accurate high-risk evidence.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [ ] PASS   [x] FAIL

**Notes:** Final triage: (Drop row): Literal synthetic placeholder domain (fakebinance.com) undermines real-world plausibility.
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 096/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=test row_index=75
- **Record digest:** `c103fa405a3cb92a41cf24b180d64dad23c6086c9f9babba6e433eb404490916`
- **Evidence digest:** `ea6d71015bd008ac24a33253911115e8dd484b3f46dd80279bc4c9b9d76d5627`
- **Judge origin:** `fresh_final_delta`
- **Judge provenance source:** `data/processed/codex-final-delta-judge.jsonl` (SHA-256 `8c152b519ca70ac9329b382dcafd8a91f09fcc8f0ed81600cbed0e6b98b584d5`)
- **Judge provenance iteration:** 0
- **Historical judge coordinate:** none (fresh final-delta judgment)
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Chào anh/chị, tài khoản ngân hàng của anh/chị cần xác nhận giao dịch OTP để tránh bị khóa. Vui lòng nhập mã OTP: 123456 vào app ngay lập tức. Đừng để lỡ nha!

- **Label:** `bank_impersonation`
- **Risk tier:** `suspicious`
- **Suspicious spans (JSON):** ["123456"]
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_1a0c3ea29c59`

### XAI explanation

> Không nhập mã OTP vào bất kỳ nguồn không rõ ràng, hãy liên hệ ngân hàng để xác minh.

- **Codex judge verdict:** PASS -- realism=3, label_correctness=3, code_switch_naturalness=5, risk_tier_correctness=3, suspicious_span_accuracy=3
- **Judge reason:**

> The account-lock language suggests bank impersonation, though directing entry inside an app could also be legitimate; suspicious risk and the OTP cue are defensible.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [ ] PASS   [x] FAIL

**Notes:** Final triage: (Drop row): Obvious synthetic placeholder OTP (123456) and contradictory text instructing the victim to input OTP into their own app without an exfiltration channel.
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 097/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=test row_index=111
- **Record digest:** `f373c8769058bb0e48d97e904d2dc5f21200ac3a5a609f8a7a11ce853cc80c59`
- **Evidence digest:** `e50e6e6fe4244061e48c3654cc20703faa46373892184cddfe7f1cc55a514878`
- **Judge origin:** `carried_forward_exact_record`
- **Judge provenance source:** `data/processed/phase39-final-evidence/carry.jsonl` (SHA-256 `593b34ab8eb01d817b849e26aea1022dac422d2a1ef16822ffe44f5cb24b5ea8`)
- **Judge provenance iteration:** historical exact carry
- **Historical judge coordinate:** train:845
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Chào bạn, giao dịch của bạn qua Internet Banking đã được xác nhận thành công. Số tiền 5.000.000 VND đã được chuyển đến tài khoản 123456789. Cảm ơn sự tin tưởng của bạn.

- **Label:** `benign`
- **Risk tier:** `benign`
- **Suspicious spans (JSON):** []
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_fda2464f98fe`

### XAI explanation

> Thông báo xác nhận giao dịch qua Internet Banking với thông tin chi tiết về số tiền và tài khoản.

- **Codex judge verdict:** PASS -- realism=5, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:**

> Xác nhận chuyển tiền không có lời mời hay thông tin cần cung cấp.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [x] PASS   [ ] FAIL

**Notes:** 
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 098/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=test row_index=138
- **Record digest:** `299317f292bc8215a13df09ed334bde93e182f54211a37b78bdf8c52e23bd5a2`
- **Evidence digest:** `4b581b3578db9cbca8d2788b65a62f9b68ae932580dd45285f1b5792dd19d691`
- **Judge origin:** `carried_forward_exact_record`
- **Judge provenance source:** `data/processed/phase39-final-evidence/carry.jsonl` (SHA-256 `593b34ab8eb01d817b849e26aea1022dac422d2a1ef16822ffe44f5cb24b5ea8`)
- **Judge provenance iteration:** historical exact carry
- **Historical judge coordinate:** train:993
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Thư ngỏ: Tài khoản của bạn hiện có số dư 10,000,000 VND. Chúng tôi khuyên bạn nên kiểm tra và quản lý tài khoản thường xuyên.

- **Label:** `benign`
- **Risk tier:** `suspicious`
- **Suspicious spans (JSON):** []
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_97c420c2e870`

### XAI explanation

> Thông báo về số dư tài khoản hiện tại và lời khuyên về việc quản lý tài khoản.

- **Codex judge verdict:** FAIL -- realism=3, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=1, suspicious_span_accuracy=5
- **Judge reason:**

> Mở đầu Thư ngỏ hơi giả tạo; nội dung số dư vẫn benign.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [ ] PASS   [x] FAIL

**Notes:** Final triage: (Fix tier): Keep label benign, but fix risk tier from suspicious to benign (routine balance alert; opening "Thư ngỏ:" is also slightly unnatural).
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 099/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=test row_index=148
- **Record digest:** `6fceff054530f21e2a51223051ea45f3251db6eb527a765fada9ed2437d76185`
- **Evidence digest:** `356e8e015f6a9ad0963f615f1a9cadb728cae0330f94b5606c6c5c1663b5b4b2`
- **Judge origin:** `carried_forward_exact_record`
- **Judge provenance source:** `data/processed/phase39-final-evidence/carry.jsonl` (SHA-256 `593b34ab8eb01d817b849e26aea1022dac422d2a1ef16822ffe44f5cb24b5ea8`)
- **Judge provenance iteration:** historical exact carry
- **Historical judge coordinate:** train:1062
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Số dư tài khoản của bạn hiện tại là 20,000,000 VND. Nếu có bất kỳ thắc mắc nào, vui lòng liên hệ bộ phận chăm sóc khách hàng.

- **Label:** `benign`
- **Risk tier:** `benign`
- **Suspicious spans (JSON):** []
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_d5aa34656582`

### XAI explanation

> Thông báo về số dư tài khoản, không có dấu hiệu đáng ngờ hoặc gian lận.

- **Codex judge verdict:** PASS -- realism=5, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:**

> Số dư và chăm sóc khách hàng hoàn toàn benign.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [x] PASS   [ ] FAIL

**Notes:** 
<!-- END PHASE39 HUMAN REVIEW -->

---

## Final Example 100/100

<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->
- **Current coordinate:** split=test row_index=210
- **Record digest:** `c56aeb4fc9a2e62ac8d8168e75417cd6ae3800569c6346e95dbf32b65797cdda`
- **Evidence digest:** `c8f7fb5cf013c68d104cb029645b98a54779b5b7af5f24e6267de648c5ed9a91`
- **Judge origin:** `fresh_final_delta`
- **Judge provenance source:** `data/processed/codex-final-delta-judge.jsonl` (SHA-256 `8c152b519ca70ac9329b382dcafd8a91f09fcc8f0ed81600cbed0e6b98b584d5`)
- **Judge provenance iteration:** 0
- **Historical judge coordinate:** none (fresh final-delta judgment)
- **Human verdict origin:** `human_verdict_origin=pending_final_human`
- **Historical human evidence:** none (fresh human verdict required)

### Message text

> Xin chào, mình là support của Binance, đang chạy chương trình giới thiệu người dùng mới. Bạn đăng ký qua link của mình và kiếm 10% hoa hồng từ giao dịch của họ. Rút tiền sẽ được mở khóa sau khi bạn gửi 100k phí xác minh. Link: https://binance-fake.com/register nha.

- **Label:** `task_scam`
- **Risk tier:** `high-risk`
- **Suspicious spans (JSON):** ["https://binance-fake.com/register", "sau khi bạn gửi 100k phí xác minh"]
- **Source:** `synthetic_openai_compatible`
- **Seed ID:** `seed_135fb131140f`

### XAI explanation

> Đây là lừa đảo vì yêu cầu bạn gửi phí xác minh trước khi có thể rút tiền, link đăng ký cũng không chính thức.

- **Codex judge verdict:** PASS -- realism=4, label_correctness=5, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:**

> Binance support impersonation combines a fake registration domain with a 100k withdrawal-unlock fee, correctly marked as high-risk task scam.
<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->
<!-- BEGIN PHASE39 HUMAN REVIEW -->
**Your verdict:** [ ] PASS   [x] FAIL

**Notes:** Final triage: (Drop row): Literal synthetic placeholder domain (binance-fake.com) undermines real-world plausibility.
<!-- END PHASE39 HUMAN REVIEW -->

---

