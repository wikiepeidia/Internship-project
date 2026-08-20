# Phase 39 task_scam Mislabel Triage Sheet

There are 4 class labels:
bank_impersonation
benign
task_scam
zalo_social_engineering
Separately, there are 3 risk tiers: benign, suspicious, and high-risk
---

## Candidate 1/324 -- split=train row_index=383 seed_id=seed_1a0c3ea29c59

> Chào anh/chị, đây là thông báo từ Ngân hàng ACB. Vui lòng đăng nhập vào ứng dụng Internet Banking để xác nhận giao dịch gần đây. Nếu không, tài khoản của anh/chị có thể bị khóa. Link: <http://acb-bank-login.com>

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [http://acb-bank-login.com]
- **Judge scores:** realism=4, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge's stated reason:** This is bank impersonation phishing, not a task scam, and the direct login is high risk.

Decision: [ ] Keep as task_scam   [X] Relabel to: bank_impersonation   [ ] Drop row

Notes: Fake ACB login URL used to harvest credentials under threat of account suspension.

---

## Candidate 2/324 -- split=train row_index=385 seed_id=seed_2e3b203f546a

> Chào bạn, CCCD của bạn đã hết hạn, vui lòng truy cập [http://capnhatcccd.vn] để cập nhật thông tin. Chúng tôi sẽ hỗ trợ bạn hoàn thành quy trình này nhanh chóng. Liên hệ 19001234 nếu cần hỗ trợ thêm. Đừng bỏ lỡ cơ hội bảo vệ tài khoản Internet Banking của bạn, nha!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [http://capnhatcccd.vn, 19001234]
- **Judge scores:** realism=2, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=3, suspicious_span_accuracy=5
- **Judge's stated reason:** Bracketed placeholder formatting makes this read like generated text, not a real message.

Decision: [ ] Keep as task_scam   [ ] Relabel to: __________   [X] Drop row

Notes: Obvious synthetic artifact (bracketed placeholder URL syntax [http://...]). Alternatively relabel to government_impersonation_phishing if syntax is retained.

---

## Candidate 3/324 -- split=train row_index=386 seed_id=seed_369e01c8527a

> Chào bạn, tôi là nhân viên từ Ngân hàng Vietcombank. Hệ thống của chúng tôi phát hiện có sự cố với tài khoản Internet Banking của bạn. Vui lòng đăng nhập vào [https://vcb-fake.com] để xác nhận lại thông tin và bảo mật tài khoản. Cảm ơn sự hợp tác của bạn, ak.

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [[https://vcb-fake.com]]
- **Judge scores:** realism=2, label_correctness=1, code_switch_naturalness=4, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge's stated reason:** Literal fake naming exposes synthetic construction and undermines real-world plausibility.

Decision: [ ] Keep as task_scam   [ ] Relabel to: __________   [X] Drop row

Notes: Synthetic text artifact using literal placeholder vcb-fake.com and markdown brackets.

---

## Candidate 4/324 -- split=train row_index=388 seed_id=seed_44fbafb85650

> Chào anh, đây là hệ thống Internet Banking của ACB. Tài khoản của anh đã bị khóa do nghi ngờ gian lận. Để mở khóa, vui lòng đăng nhập vào [fakeURL.com] và nhập OTP được gửi đến điện thoại của anh, ak. Cảm ơn anh đã hợp tác.

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [[fakeURL.com], OTP]
- **Judge scores:** realism=2, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=1, suspicious_span_accuracy=5
- **Judge's stated reason:** Literal fake naming exposes synthetic construction and undermines real-world plausibility.

Decision: [ ] Keep as task_scam   [ ] Relabel to: __________   [X] Drop row

Notes: Unrealistic synthetic placeholder domain fakeURL.com and bracketed formatting.

---

## Candidate 5/324 -- split=train row_index=390 seed_id=seed_61a36fbd3ece

> Chào bạn, do giao dịch Internet Banking của bạn đang bị lỗi, vui lòng đăng nhập lại vào app của chúng tôi để xác nhận thông tin. Link: <http://fakebank.com/login>. Cảm ơn bạn!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [http://fakebank.com/login]
- **Judge scores:** realism=2, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge's stated reason:** Literal fake naming exposes synthetic construction and undermines real-world plausibility.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 6/324 -- split=train row_index=396 seed_id=seed_7d16b8e41bee

> Chào anh/chị, tôi là nhân viên từ ngân hàng XYZ. Hệ thống của chúng tôi cần xác minh thông tin sinh trắc học để bảo mật tài khoản Internet Banking của anh/chị. Vui lòng truy cập [http://xyz-bank-update.com] để cập nhật ngay, tránh trường hợp bị khóa tài khoản. Cảm ơn anh/chị.

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [[http://xyz-bank-update.com]]
- **Judge scores:** realism=2, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge's stated reason:** Bracketed placeholder formatting makes this read like generated text, not a real message.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 7/324 -- split=train row_index=398 seed_id=seed_85009090b32e

> Chào bạn, tài khoản Internet Banking của bạn cần xác minh OTP để đảm bảo an toàn. Vui lòng đăng nhập tại [http://ibanking-safe.com] và làm theo hướng dẫn. Nếu không, tài khoản sẽ bị khóa ngay lập tức. Cảm ơn, Admin.

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [[http://ibanking-safe.com]]
- **Judge scores:** realism=2, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=1, suspicious_span_accuracy=5
- **Judge's stated reason:** Bracketed placeholder formatting makes this read like generated text, not a real message.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 8/324 -- split=train row_index=400 seed_id=seed_93fafa81260d

> Chào bạn, đây là bộ phận hỗ trợ kỹ thuật của CAFC. Máy tính của bạn có dấu hiệu bị virus, vui lòng liên hệ 0987654321 để được hỗ trợ. Đừng bỏ lỡ cơ hội bảo vệ tài khoản Internet Banking của mình, nha!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [0987654321, Internet Banking]
- **Judge scores:** realism=3, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=3, suspicious_span_accuracy=2
- **Judge's stated reason:** Contact-only spans miss the impersonation or paid-task lure that makes the message suspicious.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 9/324 -- split=train row_index=402 seed_id=seed_97b0ca1e0c34

> Chào bạn, đây là nhân viên hỗ trợ của WhatsApp. Để nâng cấp lên phiên bản Gold và sử dụng các tính năng mới, vui lòng click vào [http://whatsappgold.vn] để cài đặt. Đừng bỏ lỡ cơ hội này nha!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [[http://whatsappgold.vn]]
- **Judge scores:** realism=2, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge's stated reason:** Bracketed placeholder formatting makes this read like generated text, not a real message.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 10/324 -- split=train row_index=411 seed_id=seed_baafb1055e64

> Chào bạn, đây là Paychex. Chúng tôi cần xác minh thông tin tài khoản Internet Banking của bạn để xử lý khoản lương. Vui lòng đăng nhập vào [http://paychex-login.com] và cập nhật thông tin. Nếu ko, việc thanh toán có thể bị hoãn. Cảm ơn!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [[http://paychex-login.com]]
- **Judge scores:** realism=2, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge's stated reason:** Bracketed placeholder formatting makes this read like generated text, not a real message.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 11/324 -- split=train row_index=412 seed_id=seed_bbd7273fd159

> Chào bạn, đây là thông báo từ Ngân hàng ABC. Chúng tôi phát hiện có giao dịch khả nghi trên tài khoản Internet Banking của bạn. Vui lòng đăng nhập vào [https://abc-bank-login.com] để xác nhận OTP và bảo vệ tài khoản của bạn. Nếu bạn ko làm, tài khoản sẽ bị khóa ngay lập tức. Liên hệ 19001234 nếu cần hỗ trợ. - Đội An ninh Ngân hàng ABC

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [https://abc-bank-login.com, 19001234]
- **Judge scores:** realism=2, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=1, suspicious_span_accuracy=5
- **Judge's stated reason:** Bracketed placeholder formatting makes this read like generated text, not a real message.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 12/324 -- split=train row_index=413 seed_id=seed_bfe4a6bbd16d

> Chào bạn, đây là Ngân hàng ACB. Chúng tôi phát hiện có giao dịch đáng ngờ trên tài khoản của bạn. Vui lòng xác nhận OTP để bảo mật tài khoản: 123456. Link xác nhận: <https://acb.vn/verify>. Đừng bỏ qua, nha!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [OTP, 123456, https://acb.vn/verify]
- **Judge scores:** realism=3, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=2, suspicious_span_accuracy=4
- **Judge's stated reason:** This is bank impersonation, not a task scam; OTP confirmation through a link is high risk.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 13/324 -- split=train row_index=414 seed_id=seed_c6c8772ac332

> Chào bạn, tài khoản Internet Banking của bạn đã bị khóa do có hoạt động bất thường. Vui lòng click vào [http://fakebank.com/unlock] để xác minh thông tin và mở lại tài khoản ngay lập tức. Nếu không, tài khoản sẽ bị đóng vĩnh viễn. Cảm ơn bạn, BIDV.

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [[http://fakebank.com/unlock]]
- **Judge scores:** realism=2, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=1, suspicious_span_accuracy=5
- **Judge's stated reason:** Literal fake naming exposes synthetic construction and undermines real-world plausibility.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 14/324 -- split=train row_index=418 seed_id=seed_cf2be9f86411

> Chào bạn, tài khoản Internet Banking của bạn đang có vấn đề. Vui lòng truy cập [http://fakebank.com] để xác minh OTP. Nếu không, tài khoản sẽ bị khóa ngay lập tức. Liên hệ 0987654321 nha.

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [http://fakebank.com, 0987654321]
- **Judge scores:** realism=2, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=1, suspicious_span_accuracy=5
- **Judge's stated reason:** Literal fake naming exposes synthetic construction and undermines real-world plausibility.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 15/324 -- split=train row_index=419 seed_id=seed_d41d9b30081a

> Chị T ơi, đây là anh Công an phường Trung Hòa, có thông tin khẩn về tài khoản Internet Banking của chị bị kẻ gian truy cập trái phép. Để bảo mật, vui lòng đăng nhập và thay đổi mật khẩu ngay tại link này: <http://bit.ly/CongAnTrungHoa>. Nếu ko dc, gọi lại cho em 0334567890 nha.

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [http://bit.ly/CongAnTrungHoa, 0334567890]
- **Judge scores:** realism=4, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge's stated reason:** This impersonates police to steal banking credentials, not to offer paid tasks.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 16/324 -- split=train row_index=421 seed_id=seed_d87bcc048ee5

> Chào bạn, tài khoản Internet Banking của bạn đang có dấu hiệu bất thường. Vui lòng click vào link này để xác nhận thông tin: <http://vcbank.com.vn/verify>. Nếu không, tài khoản sẽ bị khóa ngay lập tức. Cảm ơn!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [http://vcbank.com.vn/verify]
- **Judge scores:** realism=3, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge's stated reason:** This is bank account verification phishing, not task fraud, with immediate lock pressure.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 17/324 -- split=train row_index=422 seed_id=seed_db9fb32e2681

> Chào anh, em là Thu từ bộ phận Hỗ trợ Khách hàng của Paychex. Chúng tôi phát hiện có hoạt động đáng ngờ trên tài khoản Internet Banking của anh. Vui lòng xác minh OTP để bảo vệ tài khoản: <http://paychex.vn/verifyotp>. Cảm ơn anh, nha!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [http://paychex.vn/verifyotp]
- **Judge scores:** realism=3, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge's stated reason:** This is Paychex-themed OTP phishing, not a paid-task scam, and poses high risk.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 18/324 -- split=train row_index=429 seed_id=seed_1a0c3ea29c59

> Xin chào, tôi là Nguyễn Văn A, nhân viên hỗ trợ khách hàng của Vietcombank. Tài khoản của bạn có dấu hiệu gian lận. Vui lòng cung cấp OTP để chúng tôi xác minh và bảo vệ tài khoản của bạn. Liên hệ: 0987654321

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [0987654321]
- **Judge scores:** realism=4, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=2, suspicious_span_accuracy=2
- **Judge's stated reason:** Spans omit the decisive unsafe action, retaining only links, amounts, accounts, or contacts.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 19/324 -- split=train row_index=431 seed_id=seed_2e3b203f546a

> Xin chào, có vẻ như CCCD của bạn gặp sự cố. Để tránh ảnh hưởng đến việc sử dụng OTP và Internet Banking, hãy tải ứng dụng [CCCDUpdateApp] từ [https://app-cccdupdate.com]. Nhập mã xác nhận OTP gửi đến số điện thoại của bạn để tiếp tục. Nếu ko rõ, gọi 0987654321.

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [CCCDUpdateApp, https://app-cccdupdate.com, 0987654321]
- **Judge scores:** realism=2, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=2, suspicious_span_accuracy=4
- **Judge's stated reason:** Bracketed placeholder formatting makes this read like generated text, not a real message.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 20/324 -- split=train row_index=432 seed_id=seed_369e01c8527a

> Xin chào, đây là bộ phận hỗ trợ của Cục Thuế. Chúng tôi cần bạn xác nhận một số thông tin về việc hoàn thuế của bạn. Vui lòng gọi đến số 0987654321 để được hỗ trợ nhanh chóng, k? Đừng bỏ lỡ cơ hội này, nha!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [0987654321]
- **Judge scores:** realism=3, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=3, suspicious_span_accuracy=2
- **Judge's stated reason:** Contact-only spans miss the impersonation or paid-task lure that makes the message suspicious.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 21/324 -- split=train row_index=434 seed_id=seed_44fbafb85650

> Anh/chị cần xác minh lại thông tin tài khoản ngay lập tức để tránh bị khóa. Vui lòng đăng nhập vào ứng dụng ngân hàng của Vietcombank và nhập mã xác thực Smart OTP nhận được qua SMS, nha!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [Smart OTP]
- **Judge scores:** realism=3, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=3, suspicious_span_accuracy=3
- **Judge's stated reason:** This is banking verification pressure, not task fraud; Smart OTP alone is a broad cue.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 22/324 -- split=train row_index=436 seed_id=seed_61a36fbd3ece

> Xin chào, tài khoản ngân hàng của bạn cần xác minh OTP. Vui lòng nhập mã OTP nhận được vào app của chúng tôi tại đây: <http://verifyotp.com>. Nếu ko thấy mã, gọi 0987654321. Thanks!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [http://verifyotp.com, 0987654321]
- **Judge scores:** realism=3, label_correctness=1, code_switch_naturalness=3, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge's stated reason:** This is bank OTP credential phishing, not task fraud, with an awkward English sign-off.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 23/324 -- split=train row_index=442 seed_id=seed_7d16b8e41bee

> Anh/Chị ơi, em là nhân viên hỗ trợ của ngân hàng ABC đây. Tài khoản của anh/chị cần cập nhật thông tin sinh trắc học để tiếp tục sử dụng Smart OTP. Anh/chị vui lòng liên hệ 0987654321 để được hỗ trợ nhé. Cám ơn anh/chị.

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [0987654321]
- **Judge scores:** realism=2, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=3, suspicious_span_accuracy=2
- **Judge's stated reason:** Explicit generic or sequential placeholder makes the message artificial.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 24/324 -- split=train row_index=444 seed_id=seed_85009090b32e

> Xin chào, có vẻ như tài khoản của bạn đang gặp sự cố. Vui lòng cập nhật thông tin tài khoản qua app bằng cách click vào link này: <http://update-account.com>. Liên hệ 19001234 nếu cần hỗ trợ. ĐT Ngân hàng.

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [http://update-account.com]
- **Judge scores:** realism=3, label_correctness=1, code_switch_naturalness=4, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge's stated reason:** This is vague bank account-update phishing, not task fraud, through a malicious URL.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 25/324 -- split=train row_index=446 seed_id=seed_93fafa81260d

> Cảnh báo từ CAFC: Hệ thống phát hiện máy tính của bạn đang gặp vấn đề về bảo mật. Hãy truy cập link dưới đây để xác minh: <http://safecheck.vn>. Nếu không xử lý ngay, tài khoản Smart OTP của bạn có thể bị khóa, ak!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [http://safecheck.vn, Smart OTP]
- **Judge scores:** realism=3, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=2, suspicious_span_accuracy=4
- **Judge's stated reason:** This is security-support phishing, not task fraud; Smart OTP is only a generic cue.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 26/324 -- split=train row_index=448 seed_id=seed_97b0ca1e0c34

> Xin chào, bạn cần nâng cấp ứng dụng WhatsApp lên phiên bản Gold để tăng cường bảo mật. Click vào [https://upgrade.whatsapp.com] để đăng nhập và cài đặt ngay. Nếu ko muốn bỏ lỡ, hãy làm nhanh ak!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [[https://upgrade.whatsapp.com]]
- **Judge scores:** realism=2, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=2, suspicious_span_accuracy=4
- **Judge's stated reason:** Bracketed placeholder formatting makes this read like generated text, not a real message.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 27/324 -- split=train row_index=457 seed_id=seed_baafb1055e64

> Anh/chị ơi, e là admin của ứng dụng Smart OTP. Hệ thống phát hiện có hoạt động khả nghi trên tk của a/c. Vui lòng đăng nhập ngay vào [https://smartotp-update.com] để xác minh. Nhanh nha, ko thì tk có thể bị khóa đó.

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [[https://smartotp-update.com]]
- **Judge scores:** realism=2, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge's stated reason:** Bracketed placeholder formatting makes this read like generated text, not a real message.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 28/324 -- split=train row_index=458 seed_id=seed_bbd7273fd159

> Xin chào, đây là nhân viên chăm sóc khách hàng của ứng dụng Smart OTP. Chúng tôi nhận thấy tài khoản của bạn đang gặp sự cố. Để đảm bảo an toàn, vui lòng tải lại ứng dụng từ [https://smartotp-app.com] và tạo lại mật khẩu mới. Đừng lo, việc này chỉ mất vài phút. Nếu bạn cần giúp đỡ, gọi 0987654321. Cảm ơn sự hợp tác của bạn. - CSKH Smart OTP

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [https://smartotp-app.com, 0987654321]
- **Judge scores:** realism=2, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge's stated reason:** Bracketed placeholder formatting makes this read like generated text, not a real message.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 29/324 -- split=train row_index=459 seed_id=seed_bfe4a6bbd16d

> Xin chào, đây là CSKH Vietcombank. Tài khoản Internet Banking của bạn cần cập nhật thông tin ngay lập tức. Vui lòng đăng nhập vào ứng dụng và theo dõi hướng dẫn. Nếu không, tài khoản sẽ bị khóa. Liên hệ 0987654321 nếu cần hỗ trợ.

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [Internet Banking, 0987654321]
- **Judge scores:** realism=3, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=3, suspicious_span_accuracy=2
- **Judge's stated reason:** Contact-only spans miss the impersonation or paid-task lure that makes the message suspicious.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 30/324 -- split=train row_index=460 seed_id=seed_c6c8772ac332

> Xin chào, OTP xác nhận đăng nhập vào ứng dụng ngân hàng của bạn là 123456. Vui lòng nhập mã này ngay để hoàn tất quá trình đăng nhập. Mã này chỉ có hiệu lực trong 5 phút. ABBank.

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [123456]
- **Judge scores:** realism=5, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=1, suspicious_span_accuracy=2
- **Judge's stated reason:** This resembles a legitimate ABBank OTP notice, not a task scam or suspicious message.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 31/324 -- split=train row_index=464 seed_id=seed_cf2be9f86411

> Kính gửi khách hàng, chúng tôi nhận thấy có giao dịch đáng ngờ trên tài khoản của bạn. Vui lòng tải app [http://safeservice.vn] để kiểm tra và bảo mật tài khoản. Hotline hỗ trợ: 0123456789.

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [http://safeservice.vn, 0123456789]
- **Judge scores:** realism=2, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge's stated reason:** Sequential 0123456789 is an obvious placeholder, undermining real-world plausibility.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 32/324 -- split=train row_index=465 seed_id=seed_d41d9b30081a

> Chào bạn, tôi là nhân viên Ngân hàng ACB, tài khoản của bạn đang có vấn đề về bảo mật. Vui lòng đăng nhập vào [http://acb-login.com] để xác minh OTP và cập nhật thông tin cá nhân ngay, tránh mất tiền oan. Xin cảm ơn.

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [[http://acb-login.com]]
- **Judge scores:** realism=2, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=1, suspicious_span_accuracy=5
- **Judge's stated reason:** Bracketed placeholder formatting makes this read like generated text, not a real message.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 33/324 -- split=train row_index=467 seed_id=seed_d87bcc048ee5

> Xin chào, đây là bộ phận an ninh của BIDV. Chúng tôi phát hiện có người đang cố gắng truy cập tài khoản của bạn. Vui lòng cung cấp OTP để xác minh danh tính: 123456. Gọi 0987654321 nếu cần hỗ trợ.

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [123456, 0987654321]
- **Judge scores:** realism=3, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=2, suspicious_span_accuracy=2
- **Judge's stated reason:** Spans omit the decisive unsafe action, retaining only links, amounts, accounts, or contacts.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 34/324 -- split=train row_index=468 seed_id=seed_db9fb32e2681

> Alo, đây là Mr. Long từ VPBank. Hệ thống của chúng tôi phát hiện có giao dịch bất thường. Vui lòng liên hệ ngay 0987654321 để xác minh thông tin. Đừng để tài khoản của bạn bị khóa, ak!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [0987654321]
- **Judge scores:** realism=4, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=3, suspicious_span_accuracy=2
- **Judge's stated reason:** Contact-only spans miss the impersonation or paid-task lure that makes the message suspicious.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 35/324 -- split=train row_index=475 seed_id=seed_1a0c3ea29c59

> Anh/Chị ơi, em là nhân viên của BIDV. Hệ thống của chúng tôi đang nâng cấp, vui lòng đăng nhập lại vào app để xác nhận thông tin. Link: <https://bidv-upgrade.info>

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [https://bidv-upgrade.info]
- **Judge scores:** realism=3, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge's stated reason:** This is BIDV login phishing, not task fraud, and should carry high risk.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 36/324 -- split=train row_index=477 seed_id=seed_2e3b203f546a

> Thân gửi khách hàng, CCCD của bạn cần cập nhật dữ liệu. Vui lòng đăng nhập vào [http://cccd-updates.vn] để thực hiện các bước cần thiết. Nếu ko dc, hãy gọi 19005678 để được hướng dẫn. Đảm bảo tài khoản Smart OTP của bạn luôn an toàn, ak!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [http://cccd-updates.vn, 19005678]
- **Judge scores:** realism=2, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge's stated reason:** Bracketed placeholder formatting makes this read like generated text, not a real message.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 37/324 -- split=train row_index=478 seed_id=seed_369e01c8527a

> Thân gửi khách hàng, tài khoản Smart OTP của bạn đang gặp vấn đề và cần xác minh lại. Vui lòng nhập mã OTP gửi đến số điện thoại của bạn tại [https://smartotp-fake.vn] để tiếp tục sử dụng dịch vụ. Tránh mất quyền truy cập vào tài khoản, nha!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [[https://smartotp-fake.vn]]
- **Judge scores:** realism=2, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge's stated reason:** Literal fake naming exposes synthetic construction and undermines real-world plausibility.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 38/324 -- split=train row_index=480 seed_id=seed_44fbafb85650

> Chào anh, đây là bộ phận chăm sóc khách hàng của BIDV. Chúng tôi phát hiện có giao dịch đáng ngờ trên tài khoản của anh. Để đảm bảo an toàn, vui lòng gọi đến số 0987654321 để xác minh thông tin, dc?

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [0987654321]
- **Judge scores:** realism=4, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=3, suspicious_span_accuracy=2
- **Judge's stated reason:** Contact-only spans miss the impersonation or paid-task lure that makes the message suspicious.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 39/324 -- split=train row_index=481 seed_id=seed_4af17fdb851a

> Xin chào, mình là đại diện của Binance. Chúng tôi đang tìm người giới thiệu bạn bè đăng ký tài khoản trên Binance thông qua link của bạn. Mỗi người đăng ký thành công, bạn nhận 20% hoa hồng. Link đăng ký: <https://binance.com/register/123456>. Bạn có quan tâm không?

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [https://binance.com/register/123456]
- **Judge scores:** realism=5, label_correctness=2, code_switch_naturalness=5, risk_tier_correctness=2, suspicious_span_accuracy=2
- **Judge's stated reason:** This resembles legitimate affiliate recruitment, and the official Binance URL is not suspicious.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 40/324 -- split=train row_index=482 seed_id=seed_61a36fbd3ece

> Kính gửi quý khách, tài khoản của bạn đã bị khóa do nghi ngờ gian lận. Để kích hoạt lại, vui lòng truy cập link: <http://reactivateaccount.com> và làm theo hướng dẫn. Nhanh nhanh nha!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [http://reactivateaccount.com]
- **Judge scores:** realism=3, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge's stated reason:** This is generic account reactivation phishing, not paid-task fraud, with severe lock pressure.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 41/324 -- split=train row_index=488 seed_id=seed_7d16b8e41bee

> Xin chào, tôi là nhân viên bảo mật từ ngân hàng DEF. Tài khoản của bạn đang có dấu hiệu bất thường, cần cập nhật thông tin sinh trắc học ngay. Vui lòng đăng nhập vào ứng dụng và nhấp vào link này [https://defbank-update.info] để xác minh. Tránh trường hợp tài khoản bị khóa, cảm ơn.

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [[https://defbank-update.info]]
- **Judge scores:** realism=2, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge's stated reason:** Bracketed placeholder formatting makes this read like generated text, not a real message.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 42/324 -- split=train row_index=490 seed_id=seed_85009090b32e

> Bạn ơi, tài khoản Smart OTP của mình bị khóa r, cần xác minh lại nhanh kẻo mất tiền. Click vào link này đi: [http://smart-otp-update.com] nha, làm theo hướng dẫn là dc. Cảm ơn ak.

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [[http://smart-otp-update.com]]
- **Judge scores:** realism=2, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge's stated reason:** Bracketed placeholder formatting makes this read like generated text, not a real message.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 43/324 -- split=train row_index=492 seed_id=seed_93fafa81260d

> Bạn ơi, CAFC thông báo: Máy tính của bạn có thể đã bị virus. Vui lòng liên hệ 0912345678 để được hỗ trợ khẩn cấp. Đừng để mất tài khoản, nha!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [0912345678, tài khoản]
- **Judge scores:** realism=3, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=3, suspicious_span_accuracy=2
- **Judge's stated reason:** Contact-only spans miss the impersonation or paid-task lure that makes the message suspicious.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 44/324 -- split=train row_index=494 seed_id=seed_97b0ca1e0c34

> Bạn ơi, WhatsApp đang có chương trình nâng cấp ứng dụng lên phiên bản Gold. Vui lòng truy cập [http://gold.whatsapp.vn] để kích hoạt. Đảm bảo bạn không bị mất các tính năng mới nha!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [[http://gold.whatsapp.vn]]
- **Judge scores:** realism=2, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge's stated reason:** Bracketed placeholder formatting makes this read like generated text, not a real message.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 45/324 -- split=train row_index=503 seed_id=seed_baafb1055e64

> Xin chào, đây là bộ phận hỗ trợ của Paychex. Chúng tôi cần xác nhận thông tin để tránh gián đoạn việc trả lương. Vui lòng gọi đến 0987654321 hoặc gửi OTP về số này ngay lập tức. Cảm ơn sự hợp tác!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [0987654321]
- **Judge scores:** realism=4, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=1, suspicious_span_accuracy=2
- **Judge's stated reason:** Spans omit the decisive unsafe action, retaining only links, amounts, accounts, or contacts.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 46/324 -- split=train row_index=505 seed_id=seed_bfe4a6bbd16d

> Chào bạn, đây là BIDV. Chúng tôi cần xác minh thông tin tài khoản của bạn do có hoạt động bất thường. Vui lòng truy cập link này để hoàn thành xác minh: <http://bidv-auth.com>. Hạn chót: 24h. Cảm ơn bạn!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [xác minh, http://bidv-auth.com, 24h]
- **Judge scores:** realism=4, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=2, suspicious_span_accuracy=4
- **Judge's stated reason:** This is BIDV account phishing, not task fraud; generic time spans are less informative.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 47/324 -- split=train row_index=506 seed_id=seed_c6c8772ac332

> Bạn ơi, tài khoản ngân hàng của mình đang có vấn đề, cần bạn giúp đỡ xác minh thông tin qua số 0987654321. Mình đang rất lo lắng, nhanh lên nha. Cảm ơn nhiều.

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [0987654321]
- **Judge scores:** realism=2, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=3, suspicious_span_accuracy=2
- **Judge's stated reason:** Contact-only spans miss the impersonation or paid-task lure that makes the message suspicious.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 48/324 -- split=train row_index=510 seed_id=seed_cf2be9f86411

> Bạn ơi, tài khoản Smart OTP của bạn cần cập nhật thông tin. Vui lòng truy cập [http://secureupdate.com] để thực hiện. Nếu không, tài khoản sẽ bị tạm ngừng sử dụng. ĐT: 0912345678.

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [http://secureupdate.com, 0912345678]
- **Judge scores:** realism=2, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge's stated reason:** Bracketed placeholder formatting makes this read like generated text, not a real message.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 49/324 -- split=train row_index=511 seed_id=seed_d41d9b30081a

> Alo, em ơi, đây là anh Tùng, cán bộ Công an, có thông tin em liên quan đến vụ án rửa tiền lớn. Em cần xác minh tài khoản Internet Banking của mình qua số điện thoại 0978123456 ngay để tránh rắc rối. Cảm ơn em.

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [0978123456]
- **Judge scores:** realism=4, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=2, suspicious_span_accuracy=2
- **Judge's stated reason:** Contact-only spans miss the impersonation or paid-task lure that makes the message suspicious.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 50/324 -- split=train row_index=513 seed_id=seed_d87bcc048ee5

> Báo cáo khẩn: Có giao dịch đáng ngờ từ tài khoản của bạn trên Shopee. Để đảm bảo an toàn, vui lòng đăng nhập vào app và kiểm tra ngay. Nếu không, tài khoản sẽ bị tạm khóa. Cảm ơn bạn!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** []
- **Judge scores:** realism=3, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=3, suspicious_span_accuracy=1
- **Judge's stated reason:** This is a Shopee account alert, not a task offer, and has no annotated spans.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 51/324 -- split=train row_index=514 seed_id=seed_db9fb32e2681

> Xin chào, đây là Ngân hàng Techcombank. Chúng tôi cần xác minh thông tin tài khoản của bạn do nghi ngờ giao dịch lừa đảo. Hãy đăng nhập tại <https://techcombank.com.vn/verify> và làm theo hướng dẫn. Đừng để mất tiền oan, nha!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [https://techcombank.com.vn/verify]
- **Judge scores:** realism=4, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=3, suspicious_span_accuracy=2
- **Judge's stated reason:** This is Techcombank verification, not task fraud; its apparently official domain is a weak cue.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 52/324 -- split=train row_index=519 seed_id=seed_10a6b28919e6

> Chào bạn, mình là admin của chương trình khuyến mãi ZaloPay. Để nhận thưởng 200k, hãy đăng nhập vào [fake-link] và xác thực tài khoản của bạn. Nhớ nhập mã OTP để đảm bảo an toàn nha!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [[fake-link]]
- **Judge scores:** realism=2, label_correctness=2, code_switch_naturalness=5, risk_tier_correctness=1, suspicious_span_accuracy=4
- **Judge's stated reason:** Literal fake naming exposes synthetic construction and undermines real-world plausibility.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 53/324 -- split=train row_index=520 seed_id=seed_13f16cf56dbe

> Chào bạn, mình là admin của Nhóm Đầu Tư Online. Chúng tôi đang tổ chức chương trình đầu tư đặc biệt, chỉ cần bạn đăng nhập vào [fakeURL.com] và nạp 2 triệu đồng, bạn sẽ nhận được lãi suất 60% sau 7 ngày. Đừng bỏ lỡ cơ hội này!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [[fakeURL.com], 60%, 2 triệu đồng]
- **Judge scores:** realism=2, label_correctness=2, code_switch_naturalness=5, risk_tier_correctness=1, suspicious_span_accuracy=5
- **Judge's stated reason:** Literal fake naming exposes synthetic construction and undermines real-world plausibility.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 54/324 -- split=train row_index=521 seed_id=seed_1a0c3ea29c59

> Chào anh/chị, tài khoản ngân hàng của anh/chị cần xác nhận giao dịch OTP để tránh bị khóa. Vui lòng nhập mã OTP: 123456 vào app ngay lập tức. Đừng để lỡ nha!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [123456]
- **Judge scores:** realism=3, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=2, suspicious_span_accuracy=2
- **Judge's stated reason:** Spans omit the decisive unsafe action, retaining only links, amounts, accounts, or contacts.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 55/324 -- split=train row_index=523 seed_id=seed_2e3b203f546a

> Chào bạn, CCCD của bạn cần được cập nhật ngay lập tức. Hãy truy cập [http://cccdinfo.vn] để thực hiện các bước cần thiết. Nhập mã OTP gửi về số điện thoại của bạn để xác nhận. Nếu cần hỗ trợ, gọi 0912345678. Đừng để tài khoản của bạn gặp rủi ro, nha!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [http://cccdinfo.vn, 0912345678]
- **Judge scores:** realism=2, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=2, suspicious_span_accuracy=2
- **Judge's stated reason:** Synthetic placeholder undermines realism; spans also omit the decisive unsafe action.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 56/324 -- split=train row_index=524 seed_id=seed_369e01c8527a

> Kính gửi anh/chị, chúng tôi nhận thấy có giao dịch khả nghi trên tài khoản của bạn. Để đảm bảo an toàn, vui lòng đăng nhập vào [https://fake-bank.vn] và thay đổi mật khẩu ngay. Nếu không, tài khoản của bạn có thể bị khóa, ak!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [[https://fake-bank.vn]]
- **Judge scores:** realism=2, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge's stated reason:** Literal fake naming exposes synthetic construction and undermines real-world plausibility.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 57/324 -- split=train row_index=526 seed_id=seed_44fbafb85650

> Chị ơi, em là nhân viên hỗ trợ kỹ thuật của Techcombank. Hệ thống của chị đang gặp sự cố, cần phải cập nhật thông tin tài khoản. Vui lòng truy cập [fakeLink.vn] và làm theo hướng dẫn, nha. Cảm ơn chị!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [[fakeLink.vn]]
- **Judge scores:** realism=2, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge's stated reason:** Literal fake naming exposes synthetic construction and undermines real-world plausibility.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 58/324 -- split=train row_index=528 seed_id=seed_61a36fbd3ece

> Chào bạn, do có sự cố bảo mật, vui lòng cập nhật thông tin tài khoản trên app mới của chúng tôi. Link: <http://updateinfo.com>. Đừng bỏ lỡ, nha!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [http://updateinfo.com]
- **Judge scores:** realism=3, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge's stated reason:** This is generic account-update phishing, not task fraud, through a malicious site.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 59/324 -- split=train row_index=534 seed_id=seed_7d16b8e41bee

> Chào anh/chị, em là nhân viên chăm sóc khách hàng của ngân hàng GHI. Do hệ thống mới, anh/chị cần cập nhật thông tin sinh trắc học để đảm bảo an toàn cho tài khoản. Vui lòng truy cập [http://ghi-bank-update.net] và làm theo hướng dẫn. Nếu cần hỗ trợ, anh/chị liên hệ 0123456789. Cảm ơn anh/chị.

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [[http://ghi-bank-update.net], 0123456789]
- **Judge scores:** realism=2, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge's stated reason:** Sequential 0123456789 is an obvious placeholder, undermining real-world plausibility.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 60/324 -- split=train row_index=536 seed_id=seed_85009090b32e

> Chào bạn, đây là Ngân hàng ACB. Chúng tôi nhận thấy có giao dịch nghi ngờ từ tài khoản của bạn. Vui lòng đăng nhập vào [www.acb-bank-login.com] để xác nhận thông tin. Nếu ko, tài khoản sẽ bị khóa ngay lập tức. Đừng lo lắng, chỉ cần làm theo hướng dẫn. Cảm ơn.

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [[www.acb-bank-login.com]]
- **Judge scores:** realism=2, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge's stated reason:** Bracketed placeholder formatting makes this read like generated text, not a real message.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 61/324 -- split=train row_index=538 seed_id=seed_93fafa81260d

> Chào bạn, tài khoản Internet Banking của bạn cần xác minh OTP để tránh bị khóa. Vui lòng truy cập [http://verify-bank.com] và nhập mã OTP ngay. Nếu ko xong, hãy gọi 0987654321 để được hỗ trợ. Cảm ơn!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [http://verify-bank.com, 0987654321]
- **Judge scores:** realism=2, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=1, suspicious_span_accuracy=5
- **Judge's stated reason:** Bracketed placeholder formatting makes this read like generated text, not a real message.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 62/324 -- split=train row_index=540 seed_id=seed_97b0ca1e0c34

> Chào bạn, đây là Ngân hàng ABC. Để đảm bảo an toàn cho tài khoản Internet Banking của bạn, vui lòng đăng nhập vào [www.abc-bank-upgrade.com] để xác nhận thông tin. Nếu không, tài khoản của bạn sẽ bị khóa sau 24 giờ. Cảm ơn bạn!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [www.abc-bank-upgrade.com]
- **Judge scores:** realism=2, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge's stated reason:** Bracketed placeholder formatting makes this read like generated text, not a real message.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 63/324 -- split=train row_index=545 seed_id=seed_b2c9477c611a

> Chào bạn, đây là thông báo từ ngân hàng ACB. Bạn vừa nhận được 850 điểm thưởng tương ứng với 127 triệu đồng từ chương trình tham gia bình chọn. Để nhận thưởng, vui lòng đăng nhập vào tài khoản [Internet Banking] của bạn và làm theo hướng dẫn. Nếu cần hỗ trợ, hãy gọi 19001234. AK

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [19001234]
- **Judge scores:** realism=2, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=2, suspicious_span_accuracy=2
- **Judge's stated reason:** Implausible bank reward framing is not clearly task fraud, and the hotline-only span misses core cues.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 64/324 -- split=train row_index=549 seed_id=seed_baafb1055e64

> Chào bạn, đây là Paychex. Có sự cố về tk Internet Banking của bạn, vui lòng đăng nhập vào [https://paychexsecure.com] để xác nhận thông tin. Nếu ko, tk sẽ bị khóa tạm thời. Cảm ơn!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [[https://paychexsecure.com]]
- **Judge scores:** realism=2, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge's stated reason:** Bracketed placeholder formatting makes this read like generated text, not a real message.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 65/324 -- split=train row_index=551 seed_id=seed_bfe4a6bbd16d

> Chào bạn, đây là Ngân hàng XYZ. Chúng tôi đang tiến hành nâng cấp hệ thống Internet Banking. Vui lòng đăng nhập vào [http://xyzbank-upgrade.com] để xác thực tài khoản của bạn. Nếu không, dịch vụ của bạn sẽ bị ngắt kết nối sau 24 giờ. Cảm ơn sự hợp tác của bạn!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [[http://xyzbank-upgrade.com]]
- **Judge scores:** realism=2, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge's stated reason:** Bracketed placeholder formatting makes this read like generated text, not a real message.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 66/324 -- split=train row_index=552 seed_id=seed_c6c8772ac332

> Chào bạn, do lỗi hệ thống, bạn cần cập nhật thông tin tài khoản qua link sau: [https://updateaccount.vn] để tránh mất quyền truy cập. Hạn cuối 24/10. VPBank.

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [[https://updateaccount.vn]]
- **Judge scores:** realism=2, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge's stated reason:** Bracketed placeholder formatting makes this read like generated text, not a real message.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 67/324 -- split=train row_index=556 seed_id=seed_cf2be9f86411

> Chào anh/chị, có sự cố bảo mật với tài khoản ngân hàng của anh/chị. Vui lòng đăng nhập [http://safebanking.vn] để xác nhận. ĐT hỗ trợ: 0909090909.

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [http://safebanking.vn, 0909090909]
- **Judge scores:** realism=2, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge's stated reason:** Bracketed placeholder formatting makes this read like generated text, not a real message.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 68/324 -- split=train row_index=557 seed_id=seed_d41d9b30081a

> Chị ơi, đây là em Thu, nhân viên chăm sóc khách hàng Vietcombank. Hệ thống phát hiện giao dịch khả nghi trên tài khoản của chị. Chị vui lòng cung cấp mã Smart OTP để em kiểm tra giúp chị nha. Cảm ơn chị.

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [mã Smart OTP]
- **Judge scores:** realism=5, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=1, suspicious_span_accuracy=5
- **Judge's stated reason:** This is direct Vietcombank OTP theft, not task fraud, and is high risk.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 69/324 -- split=train row_index=559 seed_id=seed_d87bcc048ee5

> Chào bạn, đây là Ngân hàng ABC. Chúng tôi phát hiện có giao dịch khả nghi trên tk của bạn. Vui lòng đăng nhập vào [https://fakebank.com] để xác minh. Nếu ko, tk sẽ bị khóa. Cảm ơn.

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [[https://fakebank.com]]
- **Judge scores:** realism=2, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge's stated reason:** Literal fake naming exposes synthetic construction and undermines real-world plausibility.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 70/324 -- split=train row_index=560 seed_id=seed_db9fb32e2681

> Anh/Chị ơi, em là Hoa từ BIDV. Hệ thống của chúng tôi phát hiện có nhiều giao dịch nghi ngờ từ tài khoản của anh/chị. Vui lòng xác minh thông tin qua số 0912345678. Đừng để mất tài khoản, nha!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [0912345678]
- **Judge scores:** realism=4, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=3, suspicious_span_accuracy=2
- **Judge's stated reason:** Contact-only spans miss the impersonation or paid-task lure that makes the message suspicious.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 71/324 -- split=train row_index=566 seed_id=seed_13f16cf56dbe

> Xin chào anh/chị, em là nhân viên của Ngân hàng ABC. Hiện tại, chúng tôi đang có chương trình khuyến mãi dành cho khách hàng VIP. Chỉ cần anh/chị nạp 10 triệu đồng vào tài khoản Internet Banking của mình qua [fakeURL.vn], anh/chị sẽ nhận được 5 triệu đồng tiền thưởng. Hãy nhanh tay nhé!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [[fakeURL.vn], 10 triệu đồng, 5 triệu đồng]
- **Judge scores:** realism=2, label_correctness=2, code_switch_naturalness=5, risk_tier_correctness=1, suspicious_span_accuracy=2
- **Judge's stated reason:** Synthetic placeholder undermines realism; spans also omit the decisive unsafe action.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 72/324 -- split=train row_index=567 seed_id=seed_1a0c3ea29c59

> Chào anh/chị, tài khoản của anh/chị tại Techcombank có giao dịch nghi ngờ. Vui lòng liên hệ 0123456789 để xác minh. Nếu không, tài khoản sẽ bị khóa ngay lập tức. Cảm ơn anh/chị.

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [0123456789]
- **Judge scores:** realism=2, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=3, suspicious_span_accuracy=2
- **Judge's stated reason:** Synthetic placeholder undermines realism; spans also omit the decisive unsafe action.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 73/324 -- split=train row_index=569 seed_id=seed_2e3b203f546a

> Kính gửi quý khách, CCCD của bạn cần được kiểm tra và cập nhật. Vui lòng truy cập [http://cccdverify.vn] và làm theo hướng dẫn. Nếu ko dc, gọi 19001111 để được hỗ trợ. Đảm bảo tài khoản Internet Banking của bạn luôn an toàn, nha!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [http://cccdverify.vn, 19001111]
- **Judge scores:** realism=2, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge's stated reason:** Bracketed placeholder formatting makes this read like generated text, not a real message.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 74/324 -- split=train row_index=570 seed_id=seed_369e01c8527a

> Chào bạn, đây là bộ phận chăm sóc khách hàng của BIDV. Chúng tôi cần xác nhận lại thông tin cá nhân của bạn do có yêu cầu rút tiền từ tài khoản. Vui lòng click vào [https://bidv-fake.com] để cập nhật thông tin. Nếu không, giao dịch của bạn sẽ bị hủy, nha!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [[https://bidv-fake.com]]
- **Judge scores:** realism=2, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge's stated reason:** Literal fake naming exposes synthetic construction and undermines real-world plausibility.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 75/324 -- split=train row_index=572 seed_id=seed_44fbafb85650

> Chào anh, đây là bộ phận tài chính của VPBank. Chúng tôi cần xác nhận lại thông tin tài khoản của anh để hoàn thành thủ tục rút tiền. Vui lòng truy cập [phishingSite.com] và điền đầy đủ thông tin, nha. Xin cảm ơn!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [[phishingSite.com]]
- **Judge scores:** realism=2, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge's stated reason:** Bracketed placeholder formatting makes this read like generated text, not a real message.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 76/324 -- split=train row_index=574 seed_id=seed_61a36fbd3ece

> Bạn ơi, tài khoản của bạn đang có vấn đề. Vui lòng đăng nhập vào app và kiểm tra lại. Nếu cần hỗ trợ, gọi 0123456789. Thanks!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [0123456789]
- **Judge scores:** realism=2, label_correctness=1, code_switch_naturalness=3, risk_tier_correctness=3, suspicious_span_accuracy=2
- **Judge's stated reason:** Contact-only spans miss the impersonation or paid-task lure that makes the message suspicious.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 77/324 -- split=train row_index=580 seed_id=seed_7d16b8e41bee

> Alo anh/chị, e là nv hỗ trợ từ ngân hàng JKL đây. Hệ thống cần cập nhật sinh trắc học của anh/chị để đảm bảo an toàn. Anh/chị vui lòng truy cập [https://jkl-bank-update.org] và làm theo hướng dẫn nha. Nếu ko làm, tài khoản sẽ bị khóa ak. Thanks anh/chị.

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [[https://jkl-bank-update.org]]
- **Judge scores:** realism=2, label_correctness=1, code_switch_naturalness=3, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge's stated reason:** Bracketed placeholder formatting makes this read like generated text, not a real message.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 78/324 -- split=train row_index=582 seed_id=seed_85009090b32e

> Xin chào, đây là Techcombank. Bạn vừa nhận được 1 mã OTP để xác minh giao dịch qua Internet Banking. Mã này chỉ sử dụng 1 lần và hết hạn sau 5 phút. Vui lòng nhập mã OTP [123456] tại [techcombank-verify.com] để hoàn tất giao dịch. Mọi thắc mắc, gọi 0987654321.

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [[123456], [techcombank-verify.com], 0987654321]
- **Judge scores:** realism=2, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=1, suspicious_span_accuracy=5
- **Judge's stated reason:** Bracketed placeholder formatting makes this read like generated text, not a real message.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 79/324 -- split=train row_index=584 seed_id=seed_93fafa81260d

> Xin chào, có vẻ như tài khoản của bạn đang gặp vấn đề. Để đảm bảo an toàn, vui lòng đăng nhập vào ứng dụng và cập nhật thông tin cá nhân. Nếu ko dc, hãy gọi 0123456789. Cảm ơn sự hợp tác!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [0123456789]
- **Judge scores:** realism=2, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=3, suspicious_span_accuracy=2
- **Judge's stated reason:** Synthetic placeholder undermines realism; spans also omit the decisive unsafe action.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 80/324 -- split=train row_index=586 seed_id=seed_97b0ca1e0c34

> Xin chào, tôi là nhân viên hỗ trợ của VietPay. Hệ thống phát hiện có sự bất thường trong tài khoản Smart OTP của bạn. Vui lòng click vào [vietpay-update.com] để kiểm tra và xác nhận lại OTP. Nếu ko, tài khoản sẽ bị tạm khóa. Cảm ơn!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [vietpay-update.com]
- **Judge scores:** realism=2, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge's stated reason:** Bracketed placeholder formatting makes this read like generated text, not a real message.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 81/324 -- split=train row_index=591 seed_id=seed_b2c9477c611a

> Xin chào, tôi là nhân viên chăm sóc khách hàng của công ty tài chính XYZ. Chúng tôi đang có chương trình ưu đãi đặc biệt dành cho bạn. Chỉ cần chuyển 2,3 tỷ đồng vào tài khoản 0123456789 để nhận điểm thưởng. Liên hệ 0987654321 nếu cần hỗ trợ. Nhanh tay nha!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [0123456789, 0987654321]
- **Judge scores:** realism=1, label_correctness=2, code_switch_naturalness=5, risk_tier_correctness=1, suspicious_span_accuracy=2
- **Judge's stated reason:** Spans omit the decisive unsafe action, retaining only links, amounts, accounts, or contacts.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 82/324 -- split=train row_index=595 seed_id=seed_baafb1055e64

> Chào bạn, e là nhân viên hỗ trợ của Paychex. Hệ thống phát hiện có giao dịch khả nghi trên tk của bạn. Vui lòng đăng nhập vào app và xác nhận bằng Smart OTP ngay. Nếu ko, tk sẽ bị khóa. Cảm ơn!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** []
- **Judge scores:** realism=3, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=2, suspicious_span_accuracy=1
- **Judge's stated reason:** This is Paychex-themed Smart OTP phishing, not task fraud, with no annotated spans.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 83/324 -- split=train row_index=597 seed_id=seed_bfe4a6bbd16d

> Xin chào, mình là nhân viên hỗ trợ của ứng dụng ZaloPay. Hiện tại, tài khoản của bạn có vấn đề cần xác minh. Vui lòng liên hệ với chúng tôi qua số điện thoại 0912345678 để được hỗ trợ. Đừng lo lắng, nha!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [0912345678]
- **Judge scores:** realism=3, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=3, suspicious_span_accuracy=2
- **Judge's stated reason:** Contact-only spans miss the impersonation or paid-task lure that makes the message suspicious.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 84/324 -- split=train row_index=598 seed_id=seed_c6c8772ac332

> Cảnh báo! Có giao dịch đáng ngờ từ tài khoản của bạn. Vui lòng đăng nhập vào app ngân hàng và xác nhận thông tin tại đây: [https://securebanking.com/verify]. Nếu không, tài khoản sẽ bị khóa. Cảm ơn, Techcombank.

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [[https://securebanking.com/verify]]
- **Judge scores:** realism=2, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge's stated reason:** Bracketed placeholder formatting makes this read like generated text, not a real message.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 85/324 -- split=train row_index=602 seed_id=seed_cf2be9f86411

> Thưa quý khách, tài khoản của bạn cần xác minh lại thông tin. Vui lòng truy cập [http://verifyaccount.vn] để hoàn tất. Nếu không, tài khoản sẽ bị vô hiệu hóa. Hotline: 0988888888.

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [http://verifyaccount.vn, 0988888888]
- **Judge scores:** realism=2, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge's stated reason:** Bracketed placeholder formatting makes this read like generated text, not a real message.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 86/324 -- split=train row_index=603 seed_id=seed_d41d9b30081a

> Chào anh, đây là chị Hằng, quản lý tài khoản BIDV. Có người đang cố truy cập trái phép vào tài khoản của anh. Anh vui lòng đăng nhập vào app và đổi mật khẩu ngay, tránh mất tiền. Cảm ơn anh.

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** []
- **Judge scores:** realism=4, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=3, suspicious_span_accuracy=1
- **Judge's stated reason:** This is BIDV support impersonation, not task fraud, and contains no annotated cues.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 87/324 -- split=train row_index=605 seed_id=seed_d87bcc048ee5

> Anh/chị ơi, em là nhân viên của Shopee, có đơn hàng của anh/chị đang gặp vấn đề. Vui lòng kiểm tra OTP gửi về số điện thoại 0987654321 để xác nhận. Cảm ơn anh/chị nha.

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [0987654321]
- **Judge scores:** realism=3, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=2, suspicious_span_accuracy=2
- **Judge's stated reason:** This is Shopee OTP support phishing, not task fraud; the annotated phone is ambiguous.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 88/324 -- split=train row_index=606 seed_id=seed_db9fb32e2681

> Chào bạn, đây là hỗ trợ từ Momo. Chúng tôi cần xác minh tài khoản của bạn do có dấu hiệu lừa đảo. Vui lòng truy cập link này để xác nhận: <http://momo.vn/confirm>. Đừng để mất tài khoản Momo, nha!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [http://momo.vn/confirm]
- **Judge scores:** realism=4, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=2, suspicious_span_accuracy=2
- **Judge's stated reason:** This is Momo account verification, not task fraud; the apparently official domain is weak.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 89/324 -- split=train row_index=610 seed_id=seed_10a6b28919e6

> Chị ơi, em là nhân viên của MBBank, hiện hệ thống của chúng tôi đang gặp sự cố. Để đảm bảo an toàn cho tài khoản của chị, vui lòng đăng nhập vào ứng dụng MB Smart OTP và đổi mật khẩu ngay. Nếu cần hỗ trợ, hãy gọi 0987654321.

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [0987654321]
- **Judge scores:** realism=4, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=3, suspicious_span_accuracy=2
- **Judge's stated reason:** Contact-only spans miss the impersonation or paid-task lure that makes the message suspicious.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 90/324 -- split=train row_index=618 seed_id=seed_85009090b32e

> Bạn ơi, đây là VPBank. Có người đang cố gắng truy cập vào tài khoản của bạn. Vui lòng đăng nhập vào [vpbank-secure-login.com] để thay đổi mật khẩu ngay lập tức. Nếu ko, tài khoản sẽ bị khóa vĩnh viễn. Liên hệ 19001234 nếu cần hỗ trợ.

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [[vpbank-secure-login.com]]
- **Judge scores:** realism=2, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=1, suspicious_span_accuracy=5
- **Judge's stated reason:** Bracketed placeholder formatting makes this read like generated text, not a real message.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 91/324 -- split=train row_index=619 seed_id=seed_93fafa81260d

> Kính gửi quý khách, hệ thống phát hiện giao dịch bất thường từ tài khoản của bạn. Vui lòng xác nhận bằng cách gửi mã OTP đến 0976543210. Nếu ko, hãy liên hệ 19001234 để được hỗ trợ. Cảm ơn!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [0976543210, 19001234]
- **Judge scores:** realism=4, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=1, suspicious_span_accuracy=2
- **Judge's stated reason:** Spans omit the decisive unsafe action, retaining only links, amounts, accounts, or contacts.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 92/324 -- split=train row_index=620 seed_id=seed_97b0ca1e0c34

> Anh/Chị, đây là MBBank. Chúng tôi cần xác minh giao dịch gần đây của bạn. Vui lòng gọi ngay đến 0987654321 hoặc truy cập [mbbank-verify.com] để xác nhận. Tránh rủi ro không đáng có, nha!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [0987654321, mbbank-verify.com]
- **Judge scores:** realism=2, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge's stated reason:** Bracketed placeholder formatting makes this read like generated text, not a real message.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 93/324 -- split=train row_index=624 seed_id=seed_bfe4a6bbd16d

> Chào bạn, bạn vừa nhận được mã OTP 123456 từ Ngân hàng ABC. Vui lòng nhập mã này vào ứng dụng của chúng tôi để xác minh giao dịch. Nếu bạn không yêu cầu giao dịch này, vui lòng liên hệ với chúng tôi ngay lập tức.

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [123456]
- **Judge scores:** realism=2, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=1, suspicious_span_accuracy=2
- **Judge's stated reason:** Explicit generic or sequential placeholder makes the message artificial.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 94/324 -- split=train row_index=627 seed_id=seed_d41d9b30081a

> Em ơi, đây là anh Nam, cán bộ công an, có thông tin em liên quan đến một vụ án ma túy. Em cần xác minh tài khoản ngân hàng của mình qua link này [http://verify-account.vn] ngay để tránh bị bắt. Cảm ơn em.

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [[http://verify-account.vn]]
- **Judge scores:** realism=2, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=1, suspicious_span_accuracy=5
- **Judge's stated reason:** Bracketed placeholder formatting makes this read like generated text, not a real message.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 95/324 -- split=train row_index=628 seed_id=seed_d87bcc048ee5

> Xin chào, đây là Amazon. Tài khoản của bạn có dấu hiệu bị hack. Hãy nhanh chóng đổi mk qua ứng dụng của chúng tôi. Link: [https://amaz0n-login.com]. Đừng để lỡ nha!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [[https://amaz0n-login.com]]
- **Judge scores:** realism=2, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge's stated reason:** Bracketed placeholder formatting makes this read like generated text, not a real message.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 96/324 -- split=train row_index=630 seed_id=seed_10a6b28919e6

> Anh/chị ơi, t đang tổ chức chương trình tặng tiền mặt 1 triệu đồng cho 10 người đầu tiên đăng ký. Hãy nhấn vào link [fake-link] để đăng ký và nhận tiền ngay nhé. Đừng bỏ lỡ cơ hội này ak!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [[fake-link]]
- **Judge scores:** realism=2, label_correctness=2, code_switch_naturalness=5, risk_tier_correctness=3, suspicious_span_accuracy=5
- **Judge's stated reason:** Literal fake naming exposes synthetic construction and undermines real-world plausibility.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 97/324 -- split=train row_index=631 seed_id=seed_13f16cf56dbe

> Chào bạn, mình là Mod của Nhóm Đầu Tư Nhanh. Hiện tại, chúng tôi đang có chương trình đầu tư với lãi suất 50% trong 3 ngày. Bạn chỉ cần nạp 3 triệu đồng vào tài khoản của mình qua [fakeURL.net] và gửi mã Smart OTP cho mình. Hãy tham gia ngay để không bỏ lỡ cơ hội này!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [[fakeURL.net], 3 triệu đồng, Smart OTP]
- **Judge scores:** realism=2, label_correctness=2, code_switch_naturalness=5, risk_tier_correctness=1, suspicious_span_accuracy=2
- **Judge's stated reason:** Synthetic placeholder undermines realism; spans also omit the decisive unsafe action.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 98/324 -- split=train row_index=638 seed_id=seed_85009090b32e

> Chào bạn, đây là BIDV. Chúng tôi nhận thấy có giao dịch bất thường từ tài khoản của bạn. Vui lòng xác nhận thông tin tài khoản bằng cách nhấp vào [bidv-authenticate.com]. Nếu ko, tài khoản sẽ bị khóa. Đừng lo lắng, chỉ cần làm theo hướng dẫn. Cảm ơn.

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [[bidv-authenticate.com]]
- **Judge scores:** realism=2, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge's stated reason:** Bracketed placeholder formatting makes this read like generated text, not a real message.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 99/324 -- split=train row_index=639 seed_id=seed_93fafa81260d

> Chào bạn, để đảm bảo an toàn cho tài khoản Smart OTP, vui lòng truy cập [http://secure-bank.vn] và cập nhật mật khẩu ngay. Nếu ko dc, hãy gọi 0965432109 để được hỗ trợ. Cảm ơn!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [http://secure-bank.vn, 0965432109]
- **Judge scores:** realism=2, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge's stated reason:** Bracketed placeholder formatting makes this read like generated text, not a real message.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 100/324 -- split=train row_index=640 seed_id=seed_97b0ca1e0c34

> Chào bạn, đây là Techcombank. Chúng tôi đang nâng cấp hệ thống và cần bạn xác nhận thông tin tài khoản. Vui lòng truy cập [techcombank-update.com] để hoàn thành quy trình. Nếu ko, tài khoản của bạn có thể gặp rủi ro. Cảm ơn sự hợp tác!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [techcombank-update.com]
- **Judge scores:** realism=2, label_correctness=1, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Bracketed placeholder formatting makes this read like generated text, not a real message.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 101/324 -- split=train row_index=644 seed_id=seed_bfe4a6bbd16d

> Chào bạn, bạn đã trúng thưởng 10 triệu đồng từ chương trình khuyến mãi của chúng tôi. Để nhận giải thưởng, vui lòng đăng nhập vào [http://trungthuong10trieu.com] và nhập thông tin cá nhân. Đừng bỏ lỡ cơ hội này, nha!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [[http://trungthuong10trieu.com]]
- **Judge scores:** realism=2, label_correctness=2, code_switch_naturalness=5, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge's stated reason:** Direct payment or credential request is high-risk; suspicious tier is too low.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 102/324 -- split=train row_index=647 seed_id=seed_d87bcc048ee5

> Chào bạn, chúng tôi là Vietcombank. Có giao dịch đáng ngờ trên tk của bạn. Vui lòng xác nhận thông tin cá nhân qua hotline 0912345678 để tránh mất tiền. Cảm ơn bạn.

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [0912345678]
- **Judge scores:** realism=4, label_correctness=1, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=2
- **Judge's stated reason:** Contact-only spans miss the impersonation or paid-task lure that makes the message suspicious.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 103/324 -- split=train row_index=650 seed_id=seed_13f16cf56dbe

> Xin chào, mình là quản trị viên của Nhóm Đầu Tư Lợi Nhuận Cao. Chúng tôi đang có chương trình đầu tư cực kỳ hấp dẫn, chỉ cần bạn nạp 1 triệu đồng vào tài khoản của mình và gửi link xác nhận cho mình, bạn sẽ nhận được 30% lợi nhuận sau 24 giờ. Hãy tham gia ngay để không bỏ lỡ cơ hội kiếm tiền nhanh chóng!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [1 triệu đồng, 30%, link xác nhận]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=2, suspicious_span_accuracy=2
- **Judge's stated reason:** Direct payment or credential request is high-risk; suspicious tier is too low.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 104/324 -- split=train row_index=657 seed_id=seed_85009090b32e

> Xin chào, đây là Vietcombank. Bạn vừa nhận được 1 mã Smart OTP để xác minh giao dịch. Mã này chỉ sử dụng 1 lần và hết hạn sau 5 phút. Vui lòng nhập mã OTP [654321] tại [vcb-smartotp.com] để hoàn tất giao dịch. Mọi thắc mắc, gọi 0912345678.

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [[654321], [vcb-smartotp.com], 0912345678]
- **Judge scores:** realism=2, label_correctness=1, code_switch_naturalness=4, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge's stated reason:** Direct payment or credential request is high-risk; suspicious tier is too low.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 105/324 -- split=train row_index=658 seed_id=seed_93fafa81260d

> Chào bạn, có vẻ như tài khoản của bạn đang bị tấn công. Vui lòng xác nhận thông tin bằng cách gọi 0987654321 và cung cấp mã OTP. Nếu ko, hãy liên hệ 19001234 để được hỗ trợ. Cảm ơn!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [0987654321, 19001234]
- **Judge scores:** realism=4, label_correctness=1, code_switch_naturalness=4, risk_tier_correctness=2, suspicious_span_accuracy=2
- **Judge's stated reason:** Direct payment or credential request is high-risk; suspicious tier is too low.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 106/324 -- split=train row_index=659 seed_id=seed_97b0ca1e0c34

> Chào bạn, đây là VPBank. Chúng tôi cần bạn xác nhận lại thông tin tài khoản để tránh bị khóa. Vui lòng truy cập [vpbank-secure.com] và nhập mã OTP mà chúng tôi vừa gửi. Đừng bỏ lỡ, ak!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [vpbank-secure.com]
- **Judge scores:** realism=2, label_correctness=1, code_switch_naturalness=4, risk_tier_correctness=2, suspicious_span_accuracy=2
- **Judge's stated reason:** Direct payment or credential request is high-risk; suspicious tier is too low.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 107/324 -- split=train row_index=662 seed_id=seed_bfe4a6bbd16d

> Xin chào, mình là quản lý dự án từ công ty ABC. Chúng tôi đang tuyển dụng vị trí Kế toán viên với mức lương hấp dẫn. Vui lòng gửi CV của bạn đến email <tuyen.dung@abc.com.vn> để được xem xét. Cơ hội tuyệt vời, ak!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [tuyen.dung@abc.com.vn]
- **Judge scores:** realism=2, label_correctness=1, code_switch_naturalness=4, risk_tier_correctness=1, suspicious_span_accuracy=1
- **Judge's stated reason:** Explicit generic or sequential placeholder makes the message artificial.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 108/324 -- split=train row_index=665 seed_id=seed_d87bcc048ee5

> Chào bạn, đây là Techcombank. Tài khoản của bạn có dấu hiệu bị hack. Vui lòng đăng nhập vào Internet Banking và đổi mk ngay. Nếu ko, tk sẽ bị khóa. Cảm ơn.

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** []
- **Judge scores:** realism=5, label_correctness=1, code_switch_naturalness=4, risk_tier_correctness=2, suspicious_span_accuracy=2
- **Judge's stated reason:** Lời khuyên đổi mật khẩu không có yêu cầu chuyển tiền hay làm nhiệm vụ.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 109/324 -- split=train row_index=1345 seed_id=seed_825b9e38d185

> Chào anh/chị, chương trình khuyến mãi cuối năm của chúng tôi đang chờ anh/chị. Click [link] để đăng ký và nhận ngay voucher giảm giá 50%. Nhập OTP để hoàn tất thủ tục. Gọi 0312345678 nếu cần hỗ trợ.

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [[link], OTP, 0312345678]
- **Judge scores:** realism=3, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=2, suspicious_span_accuracy=4
- **Judge's stated reason:** Đây là phishing khuyến mãi xin OTP, không phải lừa làm nhiệm vụ.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 110/324 -- split=train row_index=1359 seed_id=seed_825b9e38d185

> Chào bạn, BIDV đang tổ chức sự kiện tặng 200k cho 100 khách hàng đầu tiên. Đăng ký ngay qua [link] để không bỏ lỡ. Share nha!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [[link]]
- **Judge scores:** realism=3, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=3, suspicious_span_accuracy=5
- **Judge's stated reason:** Đây là phishing quà tặng qua link, không có nhiệm vụ kiếm tiền.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 111/324 -- split=train row_index=1397 seed_id=seed_825b9e38d185

> Bạn ơi, tớ vừa trúng 1 giải thưởng lớn từ Vietcombank, bạn có muốn tham gia ko? Đăng ký ngay tại đây [link]. Nhập mã Smart OTP để xác nhận nhé. Chia sẻ cho bạn bè nữa nha!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [[link], Smart OTP]
- **Judge scores:** realism=3, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge's stated reason:** Phishing giải thưởng xin Smart OTP không phải lừa làm nhiệm vụ và có rủi ro cao.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 112/324 -- split=train row_index=1413 seed_id=seed_825b9e38d185

> Bạn đã được chọn nhận voucher 500k từ Techcombank. Để kích hoạt, hãy đăng ký tại [link]. Đừng quên chia sẻ cho bạn bè và người thân nhé!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [[link]]
- **Judge scores:** realism=3, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=3, suspicious_span_accuracy=5
- **Judge's stated reason:** Đây là phishing voucher qua link, không có nhiệm vụ hay hoa hồng.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 113/324 -- split=train row_index=1419 seed_id=seed_825b9e38d185

> Chào bạn, chương trình khuyến mãi đặc biệt từ Vietcombank. Click vào [link] để nhận ngay 1 triệu VND vào tài khoản của bạn. Đừng bỏ lỡ cơ hội này, hãy chia sẻ với bạn bè nha!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [[link]]
- **Judge scores:** realism=3, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=3, suspicious_span_accuracy=5
- **Judge's stated reason:** Mồi nhận tiền qua link là phishing, không phải mô hình nhiệm vụ.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 114/324 -- split=train row_index=1511 seed_id=seed_825b9e38d185

> Xin chào, bạn vừa trúng giải đặc biệt từ Agribank. Để nhận giải thưởng, vui lòng đăng nhập vào ứng dụng Internet Banking và nhập mã OTP gửi về số điện thoại của bạn. Liên hệ 0987654321 nếu cần hỗ trợ.

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [0987654321]
- **Judge scores:** realism=3, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=2, suspicious_span_accuracy=2
- **Judge's stated reason:** Phishing trúng thưởng xin OTP không phải task scam; span chỉ là số điện thoại.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 115/324 -- split=train row_index=1725 seed_id=seed_157ce0adb043

> Ơi [Tên], mày ơi cứu tao với!! Tao vừa mất đt, đang mượn máy bạn nhắn. Tao đang kẹt tiền gấp lắm, mày chuyển giúp tao 3 triệu vào STK 9021837465 Vietcombank tên NGUYEN THI LAN dc ko? Tao về tao trả liền, tao thề. Đừng gọi lại số cũ tao vì mất đt rồi nha!!

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [vừa mất đt, đang mượn máy bạn nhắn, chuyển giúp tao 3 triệu, STK 9021837465, Đừng gọi lại số cũ tao]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Đây là mạo danh bạn bè xin tiền, không phải lừa làm nhiệm vụ.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 116/324 -- split=train row_index=1726 seed_id=seed_157ce0adb043

> Bro! Tui Khoa đây, số cũ hư rồi xài tạm số này. Tui đang kẹt tiền gấp quá, nhờ bro chuyển 2tr trước đi, tối nay tui Grab qua đưa lại liền. Bank tui: MB Bank - 07820xxxxxx - TRAN MINH KHOA. Ko cần OTP hay gì hết, chuyển thẳng vô account đó là dc nha bro. Bro giúp tui lần này với!!

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [số cũ hư rồi xài tạm số này, chuyển 2tr trước đi, Ko cần OTP hay gì hết, chuyển thẳng vô account đó, 07820xxxxxx, tối nay tui Grab qua đưa lại liền]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=4
- **Judge's stated reason:** Mạo danh người quen chuyển tiền, không có task; câu không cần OTP là cue phụ.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 117/324 -- split=train row_index=1727 seed_id=seed_157ce0adb043

> Chị [Hoa] ơi! Em là [Lan] đây ạ, acc Zalo em bị hack nên em nhắn qua nick mới này. Chị ơi em đang cần gấp 5tr để đóng viện phí cho mẹ em, bệnh viện họ yêu cầu đóng trước 5h chiều nay không thì không cho mổ ạ 😭 Chị chuyển giúp em qua Momo số 0987654321 tên LE THI LAN được không ạ? Em sẽ trả chị ngay mai khi ba em lên. Chị đừng gọi acc cũ vì bị khoá rồi ạ. Em cảm ơn chị nhiều lắm ạ 🙏🙏

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [acc Zalo em bị hack nên em nhắn qua nick mới, đóng viện phí cho mẹ em, bệnh viện họ yêu cầu đóng trước 5h chiều nay không thì không cho mổ, chuyển giúp em qua Momo số 0987654321, Chị đừng gọi acc cũ vì bị khoá rồi]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Mạo danh Zalo mới và viện phí thuộc social engineering, không phải task scam.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 118/324 -- split=train row_index=1728 seed_id=seed_157ce0adb043

> Chị Hương ơi!! Em là Lan - con bé hay đi học cùng chị đó. Tài khoản Facebook của em bị hack rồi chị ơi 😭 Em đang nhắn từ acc phụ nè. Chị có thể giúp em ko? Em cần đóng tiền học phí gấp 5tr mà app Internet Banking của em bị lỗi đăng nhập ko dc. Chị chuyển hộ em qua Momo: 0987654321 đi, tối em qua nhà trả liền á. Chị nhắn lại giúp em nha!!

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [Tài khoản Facebook của em bị hack rồi, Em đang nhắn từ acc phụ nè, app Internet Banking của em bị lỗi đăng nhập ko dc, Chị chuyển hộ em qua Momo: 0987654321, tối em qua nhà trả liền á]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Kịch bản acc phụ xin tiền là mạo danh xã hội, không phải nhiệm vụ.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 119/324 -- split=train row_index=1729 seed_id=seed_157ce0adb043

> Alo [Minh] ơi, đây là tài khoản mới của tao, đt cũ bị mất r. Tao đang kẹt tiền gấp, mày chuyển cho tao 3 triệu đc ko? Tao trả lại sau 2 ngày thôi. STK: 0981234567 - Ngân hàng Vietcombank - Nguyễn Văn Minh. Gấp lắm mày ơi, tao đang cần đóng viện phí cho mẹ.

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [tài khoản mới của tao, đt cũ bị mất r, Tao đang kẹt tiền gấp, mày chuyển cho tao 3 triệu đc ko, Gấp lắm mày ơi, đóng viện phí cho mẹ]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Người quen số mới xin viện phí là social engineering, nhãn task sai.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 120/324 -- split=train row_index=1730 seed_id=seed_157ce0adb043

> Alo [Minh] ơi, đây là tài khoản mới của tao, đt cũ bị mất r nên lập acc mới. Tao đang kẹt tiền gấp lắm, mày có thể chuyển giúp tao 2 triệu ko? Tao sẽ trả lại sau. Chuyển vào STK: 0381927465 Ngân hàng Vietcombank, tên: NGUYEN VAN MINH. Cần gấp nha, tao đang ko có cash mà phải đóng tiền nhà tối nay. Thanks mày nhiều!

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [tài khoản mới của tao, đt cũ bị mất r nên lập acc mới, Tao đang kẹt tiền gấp lắm, chuyển giúp tao 2 triệu ko, STK: 0381927465, Cần gấp nha]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Mạo danh tài khoản mới vay tiền nhà không liên quan làm task.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 121/324 -- split=train row_index=1731 seed_id=seed_157ce0adb043

> Thằng Nam đây mày ơi!! Tao vừa bị hack account facebook + mất SIM nên nhắn từ số này. Đang kẹt ở Đà Nẵng công tác, ví để quên trên xe. Mày có thể chuyển tạm 2tr ko, tao Momo lại mày liền khi về HN tối nay. Nhanh lên mày, tao đang cần gấp. Bank: MB Bank - 19008888 - PHAM QUOC NAM

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [bị hack account facebook + mất SIM nên nhắn từ số này, Đang kẹt ở Đà Nẵng công tác, ví để quên trên xe, chuyển tạm 2tr, tao Momo lại mày liền, MB Bank - 19008888]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Mạo danh bạn bị hack để vay tiền, không có cơ chế nhiệm vụ.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 122/324 -- split=train row_index=1732 seed_id=seed_157ce0adb043

> Chị ơi!! Em là Lan Anh đây ạ, em vừa bị hack Facebook nên phải nhắn qua Zalo này. Chị ơi em đang cần đóng học phí gấp trước 5h chiều nay không là bị đuổi học, mà app Internet Banking của em đang bị lỗi không login dc. Chị có thể chuyển giúp em 5.500.000đ vào STK 9988776655 Techcombank - Trần Thị Lan Anh không ạ? Em sẽ chuyển lại cho chị ngay tối nay sau khi em ra ngân hàng fix xong ạ. Em cảm ơn chị rất nhiều ạ 🙏🙏

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [vừa bị hack Facebook nên phải nhắn qua Zalo này, app Internet Banking của em đang bị lỗi không login dc, đóng học phí gấp trước 5h chiều nay không là bị đuổi học, chuyển giúp em 5.500.000đ vào STK 9988776655 Techcombank, Em sẽ chuyển lại cho chị ngay tối nay]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Mạo danh Facebook và viện cớ học phí thuộc social engineering.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 123/324 -- split=train row_index=1733 seed_id=seed_157ce0adb043

> Alo [TÊN], mày ơi tao là Minh đây, tao vừa mất đt rồi, đang dùng số mới tạm. Mày có thể chuyển giúp tao 2 triệu k? Tao đang kẹt tiền gấp lắm, mai tao trả lại ngay. Số tài khoản: 0123456789 - Ngân hàng VCB - Nguyễn Văn Minh. Tao cảm ơn mày nhiều nha, gấp lắm ko có tiền về nhà đc.

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [tao vừa mất đt rồi, đang dùng số mới tạm, chuyển giúp tao 2 triệu k, đang kẹt tiền gấp lắm, mai tao trả lại ngay, gấp lắm ko có tiền về nhà đc]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Bạn bè số mới vay tiền là lừa mạo danh, không phải task scam.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 124/324 -- split=train row_index=1734 seed_id=seed_157ce0adb043

> Chị [Lan] ơi em là Hương đây ạ, tài khoản Zalo của em bị hack nên em phải lập acc mới. Chị có thể giúp em không ạ? Bên công ty em đang cần thanh toán hợp đồng gấp nhưng Internet Banking của em đang bị lỗi không login dc. Em chỉ cần chị chuyển hộ em 8.500.000đ vào số TK 19034782910 MB Bank - chủ TK: TRAN THI HUONG, em sẽ chuyển lại cho chị qua app ngay sau khi IT fix xong hệ thống, khoảng 2-3 tiếng nữa thôi ạ. Chị giúp em với, sếp em đang giục dữ lắm ạ 🙏🙏

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [tài khoản Zalo của em bị hack nên em phải lập acc mới, Internet Banking của em đang bị lỗi không login dc, chuyển hộ em 8.500.000đ, 19034782910 MB Bank, em sẽ chuyển lại cho chị qua app ngay sau khi IT fix xong hệ thống, sếp em đang giục dữ lắm]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Tài khoản Zalo mới xin ứng tiền công ty thuộc social engineering.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 125/324 -- split=train row_index=1735 seed_id=seed_157ce0adb043

> Bro ơi mình Khoa đây nè. Acc Facebook mình bị hack xong bọn nó đổi số đt luôn nên mình đang dùng tạm nick phụ nhắn. Bro đang rảnh ko, cho mình mượn 1tr5 được ko, mình đang cần mua gấp account Netflix cho thằng em, nó cần học online. Mình sẽ chuyển lại qua MoMo cho bro tối nay sau khi lấy lại acc chính. SĐT MoMo: 0987654321 tên Lê Hoàng Khoa. Bro giúp mình với, gấp lắm 🙏

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [Acc Facebook mình bị hack xong bọn nó đổi số đt luôn, đang dùng tạm nick phụ nhắn, cho mình mượn 1tr5 được ko, cần mua gấp account Netflix, chuyển lại qua MoMo cho bro tối nay sau khi lấy lại acc chính, SĐT MoMo: 0987654321, gấp lắm]
- **Judge scores:** realism=2, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Lý do mua Netflix để học rất gượng; đây vẫn là mạo danh bạn bè.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 126/324 -- split=train row_index=1736 seed_id=seed_157ce0adb043

> Sis ơi mình Hoa nè! Mình đang dùng acc Zalo mới vì acc cũ bị report xoá rồi huhu. Sis ơi mình nhờ sis một chuyện được không? Mình lỡ order đồ online mà app ngân hàng báo lỗi không thanh toán dc, mà shop họ chỉ chờ thêm 30 phút thôi là huỷ đơn. Sis có thể thanh toán hộ mình 3tr500 không? Mình chuyển khoản lại cho sis liền sau khi fix được app nha. STK VPBank của sis gửi mình đi, mình note lại để chuyển. Cảm ơn sis nhiều lắm 😘

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [acc Zalo mới vì acc cũ bị report xoá rồi, app ngân hàng báo lỗi không thanh toán dc, shop họ chỉ chờ thêm 30 phút thôi là huỷ đơn, thanh toán hộ mình 3tr500, Mình chuyển khoản lại cho sis liền sau khi fix được app]
- **Judge scores:** realism=3, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Lời hoàn tiền hơi mâu thuẫn, và nội dung là mạo danh chứ không task.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 127/324 -- split=train row_index=1737 seed_id=seed_157ce0adb043

> Alo [Minh] ơi, đây là tao [Tuấn] nè. Tao vừa mất điện thoại nên đang dùng số mới này nhắn tin cho mày. Tao đang kẹt tiền gấp lắm, cần mượn 3 triệu để đóng viện phí cho mẹ tao, mai tao trả liền. Mày chuyển vào STK 9021 8374 5610 Ngân hàng Vietcombank tên NGUYEN VAN TUAN giúp tao với nha. Gấp lắm mày ơi, mẹ tao đang nằm viện kìa 😢

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [đây là tao [Tuấn] nè, vừa mất điện thoại nên đang dùng số mới, cần mượn 3 triệu để đóng viện phí cho mẹ tao, mai tao trả liền, STK 9021 8374 5610]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Bạn cũ số mới xin viện phí là social engineering rõ.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 128/324 -- split=train row_index=1738 seed_id=seed_157ce0adb043

> Lan ơi! Mình Phương nè. SĐT cũ hỏng r nên nhắn số mới này. Bạn có thể giúp mình ko? Mình cần mua thẻ cào Viettel 500k gấp để nạp data cho con học online, ví mình đang lỗi ko vào app dc. Bạn mua giúp mình rồi chụp mã thẻ gửi mình nha, tối mình Momo lại cho bạn liền. Làm ơn nha Lan, gấp lắm!

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [SĐT cũ hỏng r nên nhắn số mới này, cần mua thẻ cào Viettel 500k gấp, ví mình đang lỗi ko vào app dc, chụp mã thẻ gửi mình nha, tối mình Momo lại cho bạn liền]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Dụ gửi mã thẻ cào bằng số mới là mạo danh xã hội.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 129/324 -- split=train row_index=1739 seed_id=seed_157ce0adb043

> Chị ơi e là Lan con dì Hoa đây ạ. E đang ở bệnh viện, mẹ e nhập viện cấp cứu rồi chị ơi 😭 Chị chuyển cho e 5tr trước đi ạ, e chưa rút dc tiền. NH: Techcombank - 9988776655 - Tran Thi Lan. E hoàn lại ngay khi ra viện ạ.

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [mẹ e nhập viện cấp cứu, chưa rút dc tiền, chuyển cho e 5tr trước, hoàn lại ngay khi ra viện]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=5, risk_tier_correctness=5, suspicious_span_accuracy=4
- **Judge's stated reason:** Giả người thân xin viện phí không thuộc task; vài span có thể là yêu cầu thật.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 130/324 -- split=train row_index=1740 seed_id=seed_157ce0adb043

> Hey [Linh], mk Hương nè. Mk đang cần gấp, thẻ ngân hàng mk bị khóa do nhập sai OTP mấy lần, giờ ko rút tiền dc. Mày có thể chuyển tạm cho mk 800k ko? Mk sẽ chuyển khoản lại qua Smart OTP ngay khi mở khóa xong. Vietinbank: 5544332211 - Ngô Thị Hương. Mk cần trước 5h chiều nay nha không là trễ deadline thanh toán r 😢

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [thẻ ngân hàng mk bị khóa do nhập sai OTP mấy lần, ko rút tiền dc, chuyển tạm cho mk 800k ko, chuyển khoản lại qua Smart OTP ngay khi mở khóa xong, cần trước 5h chiều nay nha không là trễ deadline]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Mạo danh bạn bị khóa thẻ để vay tiền, không có nhiệm vụ.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 131/324 -- split=train row_index=1741 seed_id=seed_157ce0adb043

> Chị [Lan] ơi em là [Hương] đây ạ. Tài khoản Zalo của em bị hack nên em nhắn qua nick mới này. Chị ơi chị có thể chuyển cho em 5tr qua Momo số 0987234561 giúp em với ko ạ? Em đang cần đóng tiền học gấp hôm nay là hạn cuối rồi, ba mẹ em chưa chuyển kịp. Em sẽ hoàn lại cho chị ngay khi ba mẹ chuyển tiền ạ. Chị cứu em với ạ 🙏🙏

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [Tài khoản Zalo của em bị hack, nhắn qua nick mới này, chuyển cho em 5tr qua Momo số 0987234561, đóng tiền học gấp hôm nay là hạn cuối, Em sẽ hoàn lại cho chị ngay]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Nick Zalo mới xin tiền học là social engineering, nhãn task sai.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 132/324 -- split=train row_index=1742 seed_id=seed_157ce0adb043

> B ơi! Tao - Hùng đây. Số mới nha, sim cũ mất r. Tao đang ở nước ngoài công tác, cần chuyển gấp tiền về cho vợ tao đóng viện phí, mà tk ngân hàng tao bị khóa do đăng nhập sai OTP mấy lần. Mày giúp tao chuyển 8tr vào số 0387 652 9104 Momo tên TRAN QUOC HUNG dc k? Hoặc chuyển khoản MB Bank STK 068204 19873 cũng được. Tao nhờ mày thôi chứ ko còn ai ở đây nhờ dc nữa 😭 Tao cam kết trả mày trong 3 ngày, tao gửi giấy tờ làm tin nếu mày cần.

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [Số mới nha, sim cũ mất r, tk ngân hàng tao bị khóa do đăng nhập sai OTP mấy lần, chuyển gấp tiền về cho vợ tao đóng viện phí, chuyển 8tr vào số 0387 652 9104 Momo, MB Bank STK 068204 19873, tao gửi giấy tờ làm tin nếu mày cần]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Giả bạn ở nước ngoài xin tiền viện phí không phải lừa nhiệm vụ.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 133/324 -- split=train row_index=1743 seed_id=seed_157ce0adb043

> Chị [Hương] ơi! Em là Lan đây ạ, em lập acc Zalo mới vì acc cũ bị hack mất rồi chị ơi 😭 Chị có thể giúp em chuyển tạm 5 triệu ko ạ? Em đang ở nước ngoài, thẻ ATM bị nuốt, ko rút dc tiền. Em cần đặt cọc khách sạn gấp tối nay không thì mất phòng. Chị chuyển qua MoMo số 0387xx6612 tên TRAN THI LAN giúp em với ạ. Em về là trả liền, chị yên tâm nha. Đừng nhắn vào acc cũ vì em ko vào dc nữa rồi ạ 🙏🙏

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [acc cũ bị hack mất rồi, Em đang ở nước ngoài, thẻ ATM bị nuốt, cần đặt cọc khách sạn gấp tối nay, Đừng nhắn vào acc cũ vì em ko vào dc nữa rồi, chuyển qua MoMo số 0387xx6612]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Acc mới xin cọc khách sạn là mạo danh xã hội, không phải task.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 134/324 -- split=train row_index=1744 seed_id=seed_157ce0adb043

> Alo [Tên], mày ơi tao đang kẹt tiền gấp lắm, điện thoại tao vừa mất hôm qua nên phải dùng acc mới này nhắn. Mày có thể chuyển tạm tao 3 triệu k? Tao đang cần đóng viện phí gấp cho mẹ, mai tao trả liền. STK: 0123456789 Ngân hàng Vietcombank tên NGUYEN VAN A. Mày giúp tao với nha, tao đang lo quá 😭

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [điện thoại tao vừa mất hôm qua nên phải dùng acc mới này, chuyển tạm tao 3 triệu, đang cần đóng viện phí gấp, mai tao trả liền, STK: 0123456789]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Giả bạn mất điện thoại để xin viện phí thuộc social engineering.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 135/324 -- split=train row_index=1746 seed_id=seed_157ce0adb043

> Alo [Minh] ơi, đây là tao [Nam] nè. Tao vừa làm mất điện thoại nên đang dùng tạm số này nhắn tin. Tao đang kẹt tiền gấp lắm, cần chuyển cho tao 3 triệu qua STK 9021 4857 3301 Ngân hàng TPBank tên TK: NGUYEN VAN NAM dc ko? Tao trả lại mày sau 2 ngày, tao thề. Đừng gọi lại số cũ vì điện thoại mất rồi nha.

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [vừa làm mất điện thoại nên đang dùng tạm số này, Đừng gọi lại số cũ vì điện thoại mất rồi, cần chuyển cho tao 3 triệu, STK 9021 4857 3301]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Bạn số mới xin chuyển tiền là mạo danh, không liên quan task.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 136/324 -- split=train row_index=1749 seed_id=seed_157ce0adb043

> Chị ơi, em là Linh đây ạ! Tài khoản Facebook em bị hack mất rồi nên em nhắn qua Zalo này. Chị có thể giúp em chuyển 5 triệu ko ạ? Em đang cần đóng viện phí gấp cho mẹ, Internet Banking của em đang bị lỗi không login dc. Chị chuyển vào STK này giúp em nhé: 9876543210 - MB Bank - Trần Thị Mai. Em sẽ hoàn lại ngay tối nay khi em ra ngân hàng đổi lại app. Chị đừng lo ạ, em là Linh hàng xóm nhà mình đó chị 🙏🙏

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [Tài khoản Facebook em bị hack mất rồi, Internet Banking của em đang bị lỗi không login dc, cần đóng viện phí gấp, Em sẽ hoàn lại ngay tối nay, chuyển 5 triệu ko ạ, nhắn qua Zalo này]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Facebook bị hack rồi xin viện phí là social engineering, không task scam.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 137/324 -- split=train row_index=1750 seed_id=seed_157ce0adb043

> Chào em, chị là Phương HR công ty mình đây. Hệ thống Internet Banking công ty đang bảo trì, anh Giám đốc cần chuyển gấp lương tháng 13 cho nhân viên. Em chuyển trước 15 triệu vào tk cá nhân chị: BIDV 3344556677 - Nguyen Thi Phuong, chiều nay kế toán hoàn ứng lại cho em nha.

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [Hệ thống Internet Banking công ty đang bảo trì, anh Giám đốc cần chuyển gấp, chuyển trước 15 triệu vào tk cá nhân chị, chiều nay kế toán hoàn ứng lại]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Giả HR và giám đốc xin ứng tiền là business impersonation, không task.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 138/324 -- split=train row_index=1751 seed_id=seed_157ce0adb043

> Chị ơi em là Lan Anh đây ạ! Tài khoản Zalo của em bị hack rồi chị ơi, em đang dùng tài khoản phụ nhắn chị. Chị ơi em đang cần gấp 5 triệu để đóng học phí cho con, deadline hôm nay 5h chiều mà app Internet Banking của em đang bị lỗi không login dc. Chị có thể chuyển giúp em trước ko ạ? Em sẽ hoàn lại chị ngay tối nay qua Momo hoặc chuyển khoản. STK Techcombank: 19038876541 - LAN ANH. Chị cứu em với ạ, em cảm ơn chị nhiều lắm 🙏🙏

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [Tài khoản Zalo của em bị hack rồi, em đang dùng tài khoản phụ, deadline hôm nay 5h chiều, app Internet Banking của em đang bị lỗi không login dc, STK Techcombank: 19038876541, Em sẽ hoàn lại chị ngay tối nay]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Zalo phụ xin tiền học là mạo danh xã hội, nhãn task không đúng.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 139/324 -- split=train row_index=1752 seed_id=seed_157ce0adb043

> Alo [TEN], mình là Hương đây! Điện thoại mình vừa bị mất hồi sáng, đang dùng số mới tạm thời. Mình đang kẹt tiền gấp, cần chuyển cho mình 3 triệu qua account Vietcombank số 1023456789 tên NGUYEN THI HUONG nha. Chiều mình trả lại liền, bạn thân mà, tin mình đi ak. Cảm ơn bạn nhiều lắm!

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [Điện thoại mình vừa bị mất hồi sáng, đang dùng số mới tạm thời, Mình đang kẹt tiền gấp, chuyển cho mình 3 triệu, Chiều mình trả lại liền]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Số mới vay tiền trực tiếp không có nhiệm vụ hay hoa hồng.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 140/324 -- split=train row_index=1753 seed_id=seed_157ce0adb043

> Chị [Lan] ơi! Em là Hương đây ạ, em vừa bị hack Facebook nên nhắn từ Zalo mới này. Chị ơi em đang ở bệnh viện với mẹ, tình huống khẩn cấp quá, app Internet Banking của em đang bị lỗi không login dc. Chị có thể chuyển hộ em 5 triệu trước ko ạ? Em cần đóng viện phí gấp trước 17h hôm nay không bác sĩ không cho mổ. Em sẽ hoàn lại ngay tối nay khi về nhà. Số tài khoản: 19034782650 – MB Bank – TRAN THI HUONG. Chị nhắn lại cho em sau khi chuyển nha ạ, em cảm ơn chị nhiều lắm 🙏

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [em vừa bị hack Facebook nên nhắn từ Zalo mới này, app Internet Banking của em đang bị lỗi không login dc, 5 triệu, đóng viện phí gấp trước 17h hôm nay không bác sĩ không cho mổ, 19034782650 – MB Bank, Em sẽ hoàn lại ngay tối nay]
- **Judge scores:** realism=3, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Đe không cho mổ hơi lố; bản chất vẫn là mạo danh người quen.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 141/324 -- split=train row_index=1754 seed_id=seed_157ce0adb043

> Chi ơi! Em đây, Lan đây ạ. Acc Facebook em bị hack nên em nhắn từ acc mới này. Chị ơi cho em mượn 5tr được ko ạ? Em đang cần đóng tiền học gấp hôm nay, nếu ko đóng là bị đuổi học ạ 😭 Em chuyển lại cho chị ngay tuần sau ạ. Bank em dùng là MB Bank nha chị: 9988776655 - Trần Thị Lan. Chị cứu em với ạ!!

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [Acc Facebook em bị hack nên em nhắn từ acc mới này, cho em mượn 5tr được ko ạ, cần đóng tiền học gấp hôm nay, nếu ko đóng là bị đuổi học ạ, Em chuyển lại cho chị ngay tuần sau ạ]
- **Judge scores:** realism=3, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Đe bị đuổi học hơi cường điệu; không có task hay công việc.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 142/324 -- split=train row_index=1755 seed_id=seed_157ce0adb043

> Chị ơi em Linh đây ạ! Em đang dùng nhờ đt bạn vì đt em hỏng rồi. Chị có thể chuyển giúp em 500k dc ko ạ? Em cần nạp tiền điện thoại gấp để liên lạc công việc, sếp đang đợi. Chuyển Techcombank 1190284736 tên LE THI LINH giúp em nha chị. Em cảm ơn chị nhìu lắm ạ 🙏

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [đang dùng nhờ đt bạn vì đt em hỏng rồi, chuyển giúp em 500k dc ko ạ, sếp đang đợi, Techcombank 1190284736]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=3, suspicious_span_accuracy=5
- **Judge's stated reason:** Mạo danh người quen xin khoản nhỏ; suspicious hợp mức nhưng nhãn task sai.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 143/324 -- split=train row_index=1756 seed_id=seed_157ce0adb043

> e [Mai] đây chị ơi. Chị nhớ e ko? E học cùng lớp hồi cấp 3 đó. Chị ơi e đang cần gấp lắm, e lỡ đặt cọc hàng online 2tr8 mà quên ko để tiền trong tk, giờ họ báo 15 phút nữa ko thanh toán là hủy đơn mất cọc. Chị chuyển hộ e vào Agribank 6600112233 tên PHAM THI MAI dc ko chị? E gửi lại ngay qua Smart OTP banking của e liền. Chị cứu e với 😭

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [15 phút nữa ko thanh toán là hủy đơn mất cọc, lỡ đặt cọc hàng online 2tr8, E gửi lại ngay qua Smart OTP banking, Chị cứu e với]
- **Judge scores:** realism=3, label_correctness=2, code_switch_naturalness=3, risk_tier_correctness=5, suspicious_span_accuracy=4
- **Judge's stated reason:** Cụm Smart OTP banking gượng; đây là vay hộ giả chứ không task.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 144/324 -- split=train row_index=1757 seed_id=seed_157ce0adb043

> Hey Tuấn! Tau là Đức nè mày. Tau đang ở nước ngoài, roaming ko dùng dc nên nhắn Messenger. Mày đang rảnh ko? Giúp tau chuyển khoản 2tr qua VPBank account: 9087654321 - Lê Hoàng Đức đi. Tau lỡ quên đổi tiền mà cần đặt khách sạn gấp tối nay. Tau sẽ Paypal lại mày ngay ak, tỷ giá tau tính thêm cho mày luôn 😂 Tau cần trước 9h tối nha mày!!

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [Tau đang ở nước ngoài, roaming ko dùng dc nên nhắn Messenger, Giúp tau chuyển khoản 2tr qua VPBank account, lỡ quên đổi tiền mà cần đặt khách sạn gấp tối nay, Tau sẽ Paypal lại mày ngay ak, Tau cần trước 9h tối nha mày]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Giả bạn ở nước ngoài vay gấp là social engineering, không nhiệm vụ.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 145/324 -- split=train row_index=1758 seed_id=seed_157ce0adb043

> Chào anh/chị! Đây là Phương - con gái cô Nga hàng xóm đó ạ. Em đang ở nước ngoài du học, tài khoản Internet Banking của em bị khóa đột xuất không rút được tiền. Anh/chị có thể chuyển giúp em 8.000.000đ không ạ? Em sẽ nhờ mẹ em hoàn lại ngay cho anh/chị hôm nay. Số TK: Techcombank - 1900 2345 678 - Lê Thị Phương. Anh/chị giúp em với, em cần tiền đóng tiền nhà gấp lắm ạ 🙏

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [tài khoản Internet Banking của em bị khóa đột xuất, chuyển giúp em 8.000.000đ, Em sẽ nhờ mẹ em hoàn lại ngay cho anh/chị hôm nay, đang ở nước ngoài du học, em cần tiền đóng tiền nhà gấp lắm ạ]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Giả con hàng xóm du học xin tiền nhà không thuộc task scam.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 146/324 -- split=train row_index=1759 seed_id=seed_157ce0adb043

> Bro, tao đây - Tuấn. Số mới nha, máy cũ rớt xuống nước hỏng rồi 😅 Đang cần gấp 1.5tr để sửa máy, mày chuyển qua Momo giúp tao dc ko? SĐT Momo: 0987123456. Tao Momo lại cho mày ngay tối nay. Tks bro!

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [Số mới nha, máy cũ rớt xuống nước hỏng rồi, Đang cần gấp 1.5tr, chuyển qua Momo giúp tao dc ko, Tao Momo lại cho mày ngay tối nay]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Bạn số mới vay tiền sửa máy là mạo danh xã hội, không task.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 147/324 -- split=train row_index=1760 seed_id=seed_157ce0adb043

> Cô Nga ơi, cháu là Bảo - con trai chị Liên hàng xóm cô đó ạ. Chị Liên nhờ cháu nhắn vì điện thoại chị đang sửa. Chị cần cô chuyển gấp 4tr500 vào tk MB Bank: 0123456789 - Nguyễn Thị Liên giúp chị với ạ. Chị đang cần đóng tiền cho đợt hàng nhập về sáng mai, chuyển qua Internet Banking hoặc app MBBank đều dc ạ. Chị nói sẽ ghé nhà cô cảm ơn sau ạ. Cô nhắn lại cho cháu biết nha cô 🙏

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [con trai chị Liên hàng xóm cô đó ạ, điện thoại chị đang sửa, cần cô chuyển gấp 4tr500, chuyển qua Internet Banking hoặc app MBBank đều dc ạ, Chị nói sẽ ghé nhà cô cảm ơn sau ạ]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Giả con hàng xóm nhờ chuyển tiền hàng không liên quan nhiệm vụ.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 148/324 -- split=train row_index=1761 seed_id=seed_157ce0adb043

> Chị [Lan] ơi e là [Hương] đây ạ. E đang bị khóa app Internet Banking của e rồi chị ơi, e cần chuyển tiền gấp cho con học phí hạn hôm nay. Chị có thể chuyển hộ e 5tr500 vào acc này ko ạ: MB Bank - 0398 2741 6653 - LE THI HUONG. Xong e sẽ chuyển lại qua Momo cho chị liền, e còn số dư trong Momo mà ko rút ra dc vì chưa xác minh eKYC. Chị giúp e với ạ, e đội ơn chị lắm 🙏🙏

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [bị khóa app Internet Banking, chuyển hộ e 5tr500, MB Bank - 0398 2741 6653, chuyển lại qua Momo cho chị liền, ko rút ra dc vì chưa xác minh eKYC]
- **Judge scores:** realism=3, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Lý do có tiền MoMo nhưng không rút hơi gượng; nhãn task sai.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 149/324 -- split=train row_index=1762 seed_id=seed_157ce0adb043

> Con ơi, mẹ đây. Điện thoại mẹ hỏng rồi con ơi, đang mượn máy hàng xóm nhắn. Mẹ đang ở bệnh viện Chợ Rẫy cần đóng viện phí gấp 8 triệu, họ không chờ lâu được. Con chuyển vào tài khoản này giúp mẹ nhé: 1048293756 Techcombank - CHU THI LAN. Xong con gọi lại số này 0912345678 cho mẹ. Mẹ thương con nhiều!

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [Điện thoại mẹ hỏng rồi, đang mượn máy hàng xóm, đang ở bệnh viện Chợ Rẫy, cần đóng viện phí gấp 8 triệu, họ không chờ lâu được, 1048293756 Techcombank, gọi lại số này 0912345678]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Giả mẹ mượn điện thoại xin viện phí là social engineering.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 150/324 -- split=train row_index=1763 seed_id=seed_157ce0adb043

> Chị ơi, em là Linh — em của chị Hoa đây ạ. Chị Hoa nhờ em nhắn vì chị ấy đang bận họp, điện thoại hết pin. Chị Hoa đang cần đóng viện phí gấp cho mẹ, nhờ chị chuyển hộ 5.500.000đ trước, tối chị Hoa gặp chị hoàn lại ngay ạ. Chuyển qua Momo hoặc Internet Banking đều được:
>
> - SĐT Momo: 0387 654 921 (Trần Thị Mai)
> - STK: 1903 4455 6677 - Vietcombank
> Chị chuyển xong báo em để em thông báo cho chị Hoa nhé ạ. Cảm ơn chị rất nhiều!

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [Chị Hoa nhờ em nhắn vì chị ấy đang bận họp, điện thoại hết pin, đang cần đóng viện phí gấp, chuyển hộ 5.500.000đ trước, tối chị Hoa gặp chị hoàn lại ngay ạ, SĐT Momo: 0387 654 921 (Trần Thị Mai)]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Người trung gian giả xin viện phí thuộc mạo danh xã hội, không task.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 151/324 -- split=train row_index=1764 seed_id=seed_157ce0adb043

> Bro ơi cứu mình với!! Acc Facebook mình bị hack hết rồi, mình đang nhắn từ Zalo phụ. Mình đang cần nộp tiền học phí gấp trước 5h chiều nay không thì bị đuổi học, thiếu 5tr500k. Mày chuyển tạm cho tao qua MoMo số 0387 654 219 tên Minh Quân đi, tối mình gặp trả liền. Tao đang ở trường ko về đc lấy tiền mặt. Cảm ơn mày nhiều lắm!!

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [Acc Facebook mình bị hack hết rồi, Zalo phụ, nộp tiền học phí gấp trước 5h chiều nay, bị đuổi học, chuyển tạm cho tao qua MoMo số 0387 654 219, tối mình gặp trả liền, ko về đc lấy tiền mặt]
- **Judge scores:** realism=3, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Đe đuổi học hơi cường điệu; bản chất là acc phụ mạo danh xin tiền.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 152/324 -- split=train row_index=1765 seed_id=seed_157ce0adb043

> Ba ơi đây con [Bảo] nè. Con đang mượn điện thoại bạn nhắn vì điện thoại con hết pin. Ba chuyển cho con 2tr5 nha, con cần đóng học phí bổ sung gấp, hạn hôm nay thôi ba ơi không thì bị đuổi học. Chuyển vào Agribank số 6200205xxxxxx tên NGUYEN HOANG BAO nha ba. Con về nhà tối giải thích sau ạ. Con cảm ơn ba 🙏

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [đang mượn điện thoại bạn nhắn vì điện thoại con hết pin, đóng học phí bổ sung gấp, hạn hôm nay thôi, không thì bị đuổi học, 6200205xxxxx]
- **Judge scores:** realism=3, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=4
- **Judge's stated reason:** Giả con mượn máy xin học phí, không phải task; vài span chỉ là hoàn cảnh.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 153/324 -- split=train row_index=1766 seed_id=seed_157ce0adb043

> Tuấn đây! Mày đang online k? Tao đang ở nước ngoài, SIM VN ko dùng dc nên nhắn qua Messenger account phụ này. Có việc nhờ mày gấp: tao cần mày chuyển 8tr vào acc này giúp tao, tao đang kẹt tiền mặt bên này, thẻ bị block hết rồi. Tao sẽ gửi lại mày 9tr sau khi về (thêm 1tr cảm ơn). Chuyển vào MBBank STK 068xxxxxxxx tên LE MINH TUAN nha. Mày chuyển xong chụp bill gửi tao để tao confirm. Nhanh lên giúp tao với bro 🙏

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [SIM VN ko dùng dc nên nhắn qua Messenger account phụ, thẻ bị block hết rồi, Tao sẽ gửi lại mày 9tr sau khi về (thêm 1tr cảm ơn), chuyển xong chụp bill gửi tao để tao confirm, Nhanh lên giúp tao với bro]
- **Judge scores:** realism=3, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Hứa trả thêm một triệu hơi lố; đây vẫn là mạo danh bạn bè.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 154/324 -- split=train row_index=1767 seed_id=seed_157ce0adb043

> Tuấn đây mày ơi! Tao đang ở nước ngoài, SIM bị khóa r ko gọi dc. Nhắn qua account này tạm. Mày giúp tao chuyển 8tr vào số này gấp nha: 0912.334.782 - ví MoMo - Lê Công Tuấn. Tao bị kẹt tiền ở sân bay, chuyến bay 2 tiếng nữa. Ko có tiền mua vé đổi chuyến r mày ơi 😭 Tao gửi OTP xác nhận sau khi mày chuyển xong nha. Mày làm ơn giúp tao với!!

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [SIM bị khóa r ko gọi dc, chuyển 8tr vào số này gấp nha, Tao bị kẹt tiền ở sân bay, chuyến bay 2 tiếng nữa, Tao gửi OTP xác nhận sau khi mày chuyển xong nha]
- **Judge scores:** realism=2, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Hứa gửi OTP sau chuyển tiền vô lý; không có nhiệm vụ nào.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 155/324 -- split=train row_index=1768 seed_id=seed_157ce0adb043

> A Tuấn ơi, em là Phong đây ạ. Em đang kẹt ở sân bay Tân Sơn Nhất, ví và điện thoại bị móc túi hết r anh ơi. Em cần 4 triệu để mua vé về gấp, chuyến bay lúc 17h. Anh chuyển giúp em vào Vietinbank STK: 108 7364 9201 - HOANG VAN PHONG nha anh. Em về là trả liền, em cảm ơn anh nhiều lắm ạ. Số này là máy người ta cho mượn nhắn tin ạ.

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [kẹt ở sân bay Tân Sơn Nhất, ví và điện thoại bị móc túi hết r, cần 4 triệu để mua vé về gấp, chuyến bay lúc 17h, Vietinbank STK: 108 7364 9201, Số này là máy người ta cho mượn]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Giả người quen bị móc túi ở sân bay là social engineering.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 156/324 -- split=train row_index=1769 seed_id=seed_157ce0adb043

> Ê Quân ơi, tao Bảo đây. Mày có zalo k? Tao nhắn zalo k đc nên nhắn sms. Tao đang cần mua card game gấp cho thằng em, app store k cho thanh toán. Mày mua giúp tao 3 thẻ Garena 500k rồi chụp mã gửi tao, tao chuyển khoản lại liền.

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [nhắn zalo k đc nên nhắn sms, mua card game gấp, app store k cho thanh toán, chụp mã gửi tao, tao chuyển khoản lại liền]
- **Judge scores:** realism=3, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Dụ mua mã thẻ game là mạo danh người quen, không task scam.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 157/324 -- split=train row_index=1770 seed_id=seed_157ce0adb043

> Bro ơi tao đây, Tuấn nè. Tao đổi số r, lưu lại nha 0912xx4478. Bro có đang rảnh ko? Tao nhờ chút việc. Tao đang cần nạp thẻ game gấp 2tr để giữ rank, thanh toán Internet Banking tao bị lỗi ko login dc. Bro chuyển hộ tao vào STK 112233xxxx Techcombank tên PHAM ANH TUAN đi, tao Zalo lại tiền mặt cho bro ngay khi gặp nhau chiều. Ko cần OTP hay gì đâu, chuyển thẳng là dc nha bro 🤙

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [Tao đổi số r, thanh toán Internet Banking tao bị lỗi ko login dc, Ko cần OTP hay gì đâu, chuyển hộ tao vào STK 112233xxxx Techcombank, nạp thẻ game gấp 2tr]
- **Judge scores:** realism=2, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge's stated reason:** Cụm Zalo lại tiền mặt vô nghĩa; nhãn task và tier suspicious đều yếu.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 158/324 -- split=train row_index=1771 seed_id=seed_157ce0adb043

> Alo [Minh] ơi, đây là tài khoản mới của tao, đt cũ bị mất r. Tao đang kẹt tiền gấp, mày chuyển cho tao 3 triệu đc ko? STK: 0123456789 - Ngân hàng VCB tên TK: NGUYEN VAN MINH. Tao trả mày sau nha, cảm ơn mày nhiều!

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [tài khoản mới của tao, đt cũ bị mất r, đang kẹt tiền gấp, chuyển cho tao 3 triệu đc ko, STK: 0123456789 - Ngân hàng VCB]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Tài khoản mới vay tiền trực tiếp thuộc mạo danh xã hội.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 159/324 -- split=train row_index=1773 seed_id=seed_157ce0adb043

> E chào a Quân ạ, e là Thảo đây a. E lỡ để quên đt ở nhà đi làm rồi nên nhắn từ đt của đồng nghiệp. A ơi a có thể chuyển giúp e 800k dc ko ạ? E cần nạp tiền điện thoại gấp để gọi cho khách hàng, sếp đang yêu cầu gấp lắm. Nạp vào số 0912345678 mạng Viettel giúp e nha a, hoặc chuyển khoản cũng dc ạ: VPBank - 214567890 - LE THI THAO. Chiều e gặp a e đưa lại liền ạ 🙏

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [để quên đt ở nhà, nhắn từ đt của đồng nghiệp, chuyển giúp e 800k, sếp đang yêu cầu gấp lắm, Nạp vào số 0912345678, chuyển khoản cũng dc ạ, Chiều e gặp a e đưa lại liền]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=2, suspicious_span_accuracy=4
- **Judge's stated reason:** Mượn điện thoại xin tiền là social engineering; chuyển tiền trực tiếp đáng high-risk.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 160/324 -- split=train row_index=1774 seed_id=seed_157ce0adb043

> Alo [Minh] ơi, đây là tao [Nam] nè. Tao vừa mất điện thoại nên đang dùng số mới này. Tao đang kẹt tiền gấp, mày chuyển giúp tao 3 triệu vào số TK 0123456789 - Ngân hàng VCB tên NGUYEN VAN NAM dc ko? Tao sẽ trả lại ngay chiều nay, tao hứa. Đừng gọi lại số cũ vì điện thoại mất rồi nha.

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [vừa mất điện thoại nên đang dùng số mới, Đừng gọi lại số cũ vì điện thoại mất rồi, chuyển giúp tao 3 triệu, 0123456789]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Giả bạn mất điện thoại để vay tiền, không có task.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 161/324 -- split=train row_index=1775 seed_id=seed_157ce0adb043

> Bạn ơi mình Hương đây. Mình đang dùng tạm app Zalo trên máy tính vì điện thoại hỏng màn hình rồi. Bạn có thể giúp mình một việc được không? Mình đang cần chuyển tiền học phí cho con gấp hôm nay là hạn cuối mà Internet Banking nhà mình đang bị lỗi không login được. Bạn chuyển hộ mình 8.500.000đ vào STK Techcombank 1903 2277 8899 tên LE THI HUONG giúp mình với. Mình sẽ chuyển khoản lại cho bạn qua Smart OTP ngay sau khi mình fix được app. Mình xin lỗi vì làm phiền bạn nha, cảm ơn bạn rất nhiều ạ!

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [dùng tạm app Zalo trên máy tính vì điện thoại hỏng màn hình, Internet Banking nhà mình đang bị lỗi không login được, chuyển hộ mình 8.500.000đ, STK Techcombank 1903 2277 8899, chuyển khoản lại cho bạn qua Smart OTP ngay sau khi mình fix được app]
- **Judge scores:** realism=3, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Hoàn tiền qua Smart OTP hơi gượng; nội dung là mạo danh Zalo.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 162/324 -- split=train row_index=1776 seed_id=seed_157ce0adb043

> Tuấn! Tau đây, Phong nè. Số cũ mất r dùng số này. Đang cần gấp 800k mày ơi, tau đang ở bệnh viện lo cho ba, ví để nhà hết tiền mặt mà ATM lại nuốt thẻ. Mày MoMo hoặc chuyển khoản dc ko? SĐT MoMo: 0912345678 tên Nguyen Thanh Phong. Tau sẽ hoàn lại ngay tối nay khi tau về. Gấp lắm mày ơi 🙏🙏

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [Số cũ mất r dùng số này, đang ở bệnh viện lo cho ba, ví để nhà hết tiền mặt mà ATM lại nuốt thẻ, SĐT MoMo: 0912345678, Gấp lắm mày ơi]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Số mới xin tiền bệnh viện là social engineering, nhãn task sai.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 163/324 -- split=train row_index=1777 seed_id=seed_157ce0adb043

> Ơi [Tên], mình là Hương nè. Điện thoại mình vừa bị mất hồi sáng, đang dùng nhờ máy bạn nhắn tin cho m. Mình đang cần gấp 3 triệu để đóng tiền học cho con, chuyển giúp mình vào STK 9021837465 Vietcombank tên NGUYEN THI HUONG nha. Chiều mình gặp trả liền, cảm ơn bạn nhiều lắm!

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [Điện thoại mình vừa bị mất hồi sáng, đang dùng nhờ máy bạn, cần gấp 3 triệu, STK 9021837465 Vietcombank, Chiều mình gặp trả liền]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Mạo danh người quen mất máy xin học phí không thuộc task scam.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 164/324 -- split=train row_index=1778 seed_id=seed_157ce0adb043

> Nam ơi! Mình Phương đây, số mới nha vì mình vừa đổi SIM. Mình đang kẹt ở bệnh viện với mẹ, cần chuyển viện gấp mà thẻ ATM của mình nuốt rồi ko rút dc. Mày có thể chuyển giúp mình 3.500.000đ ko? Chuyển vào Vietinbank STK: 108000234567 - CHU THI PHUONG. Mình chuyển lại cho mày tối nay khi về nhà lấy thẻ khác. Cảm ơn mày nhiều lắm, tình huống khẩn cấp quá 😢

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [số mới nha vì mình vừa đổi SIM, đang kẹt ở bệnh viện với mẹ, thẻ ATM của mình nuốt rồi ko rút dc, tình huống khẩn cấp quá, Mình chuyển lại cho mày tối nay]
- **Judge scores:** realism=3, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Câu thẻ ATM của mình nuốt hơi lỗi; đây vẫn là mạo danh xã hội.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 165/324 -- split=train row_index=1779 seed_id=seed_157ce0adb043

> A ơi e là Minh Tuấn đây ạ, acc Facebook e bị hack nên e nhắn qua Zalo này. A đang rảnh ko ạ? E cần nhờ a một việc gấp lắm. E đang ở nước ngoài công tác, thẻ bị block ko rút dc tiền, cần chuyển gấp 5tr để đặt cọc khách sạn tối nay không bị mất phòng. A có thể chuyển giúp e qua MoMo số 0387654219 tên TRAN MINH TUAN ko ạ? E về là trả ngay, a yên tâm đi ạ. E cảm ơn a nhiều lắm ạ!

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [acc Facebook e bị hack nên e nhắn qua Zalo này, E đang ở nước ngoài công tác, thẻ bị block ko rút dc tiền, chuyển gấp 5tr để đặt cọc khách sạn tối nay không bị mất phòng, chuyển giúp e qua MoMo số 0387654219, E về là trả ngay, a yên tâm đi ạ]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Facebook bị hack rồi xin cọc khách sạn là social engineering.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 166/324 -- split=train row_index=1780 seed_id=seed_157ce0adb043

> Chị [Lan] ơi! Em là Hương đây, em vừa bị hack Facebook nên lập acc mới. Chị đang rảnh ko ạ? Em nhờ chị một việc gấp được ko ạ 🙏 Em đang cần chuyển tiền học phí cho con gái nhưng app Internet Banking của em đang bị lỗi không login dc. Chị có thể chuyển hộ em 5.500.000đ vào STK 0387654321 MB Bank - Tran Thi Huong ko ạ? Chiều nay em về em trả chị liền, em cảm ơn chị nhiều lắm ạ. Chị chuyển xong chụp bill gửi em qua đây nha chị ❤️

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [em vừa bị hack Facebook nên lập acc mới, app Internet Banking của em đang bị lỗi không login dc, Chị có thể chuyển hộ em 5.500.000đ, STK 0387654321 MB Bank, Chiều nay em về em trả chị liền, chụp bill gửi em qua đây]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Acc mới xin tiền học thuộc mạo danh, không phải lừa nhiệm vụ.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 167/324 -- split=train row_index=1781 seed_id=seed_157ce0adb043

> Chị [Lan] ơi! Em là Hương đây ạ, acc Zalo cũ của em bị hack mất r nên em lập cái này. Chị ơi hiện tại em đang cần đóng học phí gấp cho con, ngân hàng app bị lỗi ko chuyển dc. Chị có thể giúp em chuyển tạm 5.500.000đ qua Momo số 0912374856 (Tran Thi Huong) ko ạ? Chiều nay chồng em về em trả liền, em hứa ạ. Em cảm ơn chị nhiều lắm 🙏🙏

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [acc Zalo cũ của em bị hack mất r nên em lập cái này, ngân hàng app bị lỗi ko chuyển dc, chuyển tạm 5.500.000đ qua Momo số 0912374856, Chiều nay chồng em về em trả liền, em hứa ạ]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Zalo mới xin chuyển MoMo là social engineering rõ.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 168/324 -- split=train row_index=1782 seed_id=seed_157ce0adb043

> Chị ơi em đây! Em đang dùng acc zalo mượn của bạn vì acc em bị hack mất r. Chị chuyển cho em 500k qua Momo giúp em với, em cần đóng tiền học gấp hôm nay. SĐT Momo: 0987-654-321 tên Trần Thị Lan. E gửi lại chị sau nha, e hứa đó 🙏

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [acc zalo mượn của bạn vì acc em bị hack mất r, chuyển cho em 500k qua Momo, cần đóng tiền học gấp hôm nay, E gửi lại chị sau nha]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=4, suspicious_span_accuracy=5
- **Judge's stated reason:** Giả mượn acc Zalo xin khoản nhỏ, không có nhiệm vụ.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 169/324 -- split=train row_index=1783 seed_id=seed_157ce0adb043

> Anh Tuấn ơi, em Hùng đây ạ — em làm cùng team với anh hồi ở cty cũ đó anh còn nhớ k ạ? Em đang kẹt tình huống xấu hổ lắm anh ơi. Em đang đi công tác Đà Nẵng, bị mất ví mất hết thẻ, điện thoại cũng sắp hết pin. Anh có thể chuyển cho em 1tr5 qua ViettelPay số 0912847365 - NGUYEN MANH HUNG dc ko anh? Em về HN thứ 6 là trả anh liền. Anh đừng gọi lại số này vì roaming tốn tiền lắm, nhắn tin thôi nha anh. Em cảm ơn anh nhiều 🙏

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [bị mất ví mất hết thẻ, điện thoại cũng sắp hết pin, chuyển cho em 1tr5 qua ViettelPay số 0912847365, Anh đừng gọi lại số này vì roaming tốn tiền lắm, nhắn tin thôi nha anh]
- **Judge scores:** realism=3, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Lý do không gọi vì roaming hơi gượng; đây là mạo danh đồng nghiệp.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 170/324 -- split=train row_index=1784 seed_id=seed_157ce0adb043

> Chị [Lan] ơi! Em là Hương đây ạ, em lập acc mới vì acc cũ bị hack mất rồi chị ơi 😭 Chị có thể giúp em ko ạ? Em đang cần đóng học phí gấp hạn hôm nay mà app Internet Banking của em đang bị lỗi không login dc. Chị chuyển hộ em 5.500.000đ vào STK: 19036xxxxxx8 Vietcombank tên NGUYEN THI HUONG được không ạ? Em sẽ chuyển lại cho chị qua MoMo ngay chiều nay, em hứa ạ. Chị cứu em với 🙏🙏

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [acc cũ bị hack mất rồi, app Internet Banking của em đang bị lỗi không login dc, chuyển hộ em 5.500.000đ, STK: 19036xxxxxx8 Vietcombank, chuyển lại cho chị qua MoMo ngay chiều nay, hạn hôm nay]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Acc hack xin học phí là social engineering, không task scam.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 171/324 -- split=train row_index=1785 seed_id=seed_157ce0adb043

> Con ơi bố đây. Bố đang dùng số mới vì điện thoại cũ bị hỏng màn hình rồi. Con save số này lại nha. Bố đang cần chuyển tiền gấp cho đối tác nhưng app MB Bank của bố đang bảo lỗi Smart OTP không xác thực được. Con có thể chuyển hộ bố 8 triệu vào tài khoản này không: BIDV - 31021847593 - PHAM VAN THANH. Bố sẽ trả con tối nay khi về. Đừng gọi số cũ vì máy hỏng rồi con nhé.

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [đang dùng số mới vì điện thoại cũ bị hỏng, app MB Bank của bố đang bảo lỗi Smart OTP không xác thực được, chuyển hộ bố 8 triệu, BIDV - 31021847593, Đừng gọi số cũ vì máy hỏng rồi]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Giả bố số mới nhờ chuyển tiền đối tác không thuộc task.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 172/324 -- split=train row_index=1786 seed_id=seed_157ce0adb043

> Bro ơi tao [Khoa] nè. Tao đang ở nước ngoài, roaming hết tiền r, mượn mày 2tr dc k? Chuyển khoản VCB số TK: 1048293756 - PHAM QUOC KHOA nha. Tao về sẽ trả liền. Gấp lắm bro 😭

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [đang ở nước ngoài, roaming hết tiền, mượn mày 2tr dc k, TK: 1048293756, Gấp lắm bro]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=3
- **Judge's stated reason:** Lời vay tiền có thể thật nhưng không có task; các span chỉ mang tính ngữ cảnh.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 173/324 -- split=train row_index=1787 seed_id=seed_157ce0adb043

> Hey Long! Tau đây - Khánh. Acc fb tau bị report die r, đang dùng nick phụ. Mày đang rảnh ko? Tau nhờ mày chuyển giúp 1tr5 vào số Vietinbank 113000456789 tên NGUYEN MANH KHANH. Tau đang cần nộp phí gia hạn domain cho khách, họ thanh toán qua link mà tau ko có thẻ. Mày chuyển giúp tau, chiều tau Momo lại liền. Gấp lắm mày ơi!!

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [Acc fb tau bị report die r, đang dùng nick phụ, nộp phí gia hạn domain cho khách, họ thanh toán qua link mà tau ko có thẻ, chiều tau Momo lại liền, Gấp lắm mày ơi!!]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Nick phụ xin ứng phí domain là mạo danh người quen.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 174/324 -- split=train row_index=1788 seed_id=seed_157ce0adb043

> Anh ơi! Em Thảo đây ạ, em lỡ chuyển nhầm 1.200.000đ vào tài khoản anh rồi. Anh kiểm tra lại giúp em và chuyển lại về số tk này giúp em với ạ: MB Bank - 0987654321 - Le Thi Thao. Em cảm ơn anh nhiều ạ 🙏

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [lỡ chuyển nhầm 1.200.000đ vào tài khoản anh, chuyển lại về số tk này, MB Bank - 0987654321]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=5, risk_tier_correctness=4, suspicious_span_accuracy=3
- **Judge's stated reason:** Đây là hoàn tiền nhầm giả, không task; yêu cầu có thể hợp lệ nếu tiền thật đến.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 175/324 -- split=train row_index=1789 seed_id=seed_157ce0adb043

> e Minh đây a ơi, a có nhớ e ko ạ? e học cùng lớp a hồi cấp 3 á. E đang cần gấp a ơi, e lỡ chuyển nhầm tiền vào tk của a rồi, a check Internet Banking giúp e xem có nhận dc 1.200k ko ạ? Nếu có thì a chuyển lại giúp e vào số này nha a: 0369112233 - Nguyễn Văn Minh - VPBank. E cần gấp lắm ạ, sếp e đang chờ 😭 link ck nhanh: vpbank.transfer-fast.net/ck

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [e lỡ chuyển nhầm tiền vào tk của a rồi, a check Internet Banking giúp e xem có nhận dc, vpbank.transfer-fast.net/ck, Nếu có thì a chuyển lại giúp e, sếp e đang chờ]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Hoàn tiền nhầm kèm link giả là phishing xã hội, không task scam.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 176/324 -- split=train row_index=1790 seed_id=seed_157ce0adb043

> Em ơi! Chị là chị Hoa đây, chị đang dùng acc zalo mới vì acc cũ bị hack mất rồi em ạ 😭 Chị đang cần gấp 5 triệu để đóng viện phí cho mẹ, ngân hàng chị đang bị lỗi app Internet Banking ko chuyển dc. Em có thể chuyển giúp chị trước ko, chiều chị thanh toán lại liền. Chuyển vào Momo số 0387xxxxxx tên TRAN THI HOA nha em. Chị cảm ơn em nhiều lắm, tình huống khẩn cấp quá em ơi 🙏

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [acc zalo mới vì acc cũ bị hack mất rồi, cần gấp 5 triệu, đóng viện phí cho mẹ, app Internet Banking ko chuyển dc, Chuyển vào Momo số 0387xxxxxx, tình huống khẩn cấp quá]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Acc Zalo mới xin viện phí là mạo danh xã hội.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 177/324 -- split=train row_index=1792 seed_id=seed_157ce0adb043

> Ba ơi đây con [Nam] nè ba. Con đang ở nước ngoài, điện thoại cũ mất rồi dùng sim mới này. Ba ơi con đang kẹt lắm, ví điện tử con bị khoá ko rút dc tiền, Internet Banking cũng đang lỗi ko login dc. Ba chuyển gấp cho con 8 triệu qua MoMo số 0387412965 (tên Tran Quoc Nam) để con lo việc trước nha ba. Con về sẽ trả ba liền. Đừng gọi lại số cũ vì mất rồi ba ơi 🙏

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [điện thoại cũ mất rồi dùng sim mới này, ví điện tử con bị khoá ko rút dc tiền, Internet Banking cũng đang lỗi ko login dc, chuyển gấp cho con 8 triệu, MoMo số 0387412965, Đừng gọi lại số cũ vì mất rồi]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Giả con ở nước ngoài xin MoMo là social engineering, không nhiệm vụ.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 178/324 -- split=train row_index=1793 seed_id=seed_157ce0adb043

> Bro ơi tao [Nam] đây. Tao đang ở nước ngoài, thẻ bị khóa ko rút dc tiền. Mày login vào Internet Banking chuyển gấp cho tao 8 củ qua acc này ko: MB Bank - 0034521987 - LE QUOC NAM. Tao sẽ chuyển lại qua Paypal hoặc tiền mặt khi về. Gấp lắm bro, tao đang kẹt ở sân bay, chuyến bay 2 tiếng nữa. Mày là cứu tinh của tao lúc này 😭

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [đang ở nước ngoài, thẻ bị khóa ko rút dc tiền, login vào Internet Banking chuyển gấp, MB Bank - 0034521987 - LE QUOC NAM, chuyển lại qua Paypal, kẹt ở sân bay, chuyến bay 2 tiếng nữa]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Bạn ở nước ngoài xin tiền sân bay không phải task scam.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 179/324 -- split=train row_index=1796 seed_id=seed_157ce0adb043

> Alo [TEN], mình là Hương nè! Điện thoại mình bị hỏng nên đang dùng SĐT mới tạm thời. Mình đang kẹt tiền gấp, cần chuyển 3 triệu để đóng viện phí cho mẹ trước 5h chiều nay. Nhờ bạn chuyển hộ mình vào STK: 0398271645 Ngân hàng Vietcombank - Nguyễn Thị Hương. Mình sẽ trả lại ngay tối nay nha. Cảm ơn bạn nhiều lắm!

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [Điện thoại mình bị hỏng nên đang dùng SĐT mới tạm thời, kẹt tiền gấp, đóng viện phí cho mẹ trước 5h chiều nay, Mình sẽ trả lại ngay tối nay]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Số mới xin viện phí thuộc social engineering, không có nhiệm vụ.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 180/324 -- split=train row_index=1797 seed_id=seed_157ce0adb043

> Tuấn! Tao Khoa đây. SĐT mới 0978.234.xxx nha, SĐT cũ mất rồi. Mày đang rảnh k? Tao nhờ mày 1 việc gấp được k. Tao đang ở nước ngoài, thẻ visa bị block ko rút dc tiền. Mày chuyển tạm cho tao 8tr vào MBBank 068xxx3421 - CHU VAN KHOA được k? Tao sẽ chuyển lại qua app ngay khi về. Ko lâu đâu mày, tao về thứ 6 này. Cần gấp lắm mày ơi!!

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [SĐT mới 0978.234.xxx, SĐT cũ mất rồi, đang ở nước ngoài, thẻ visa bị block ko rút dc tiền, chuyển tạm cho tao 8tr, MBBank 068xxx3421, chuyển lại qua app ngay khi về]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Giả bạn mất SIM ở nước ngoài để vay tiền, không task.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 181/324 -- split=train row_index=1798 seed_id=seed_157ce0adb043

> Thắng đây m ơi. Tao đang ở nước ngoài, thẻ bị khóa ko rút dc tiền. M có thể chuyển cho tao $200 (khoảng 5tr) qua Internet Banking ko? Tao dùng app đổi tiền gửi lại m ngay. Tao gửi link app đây để m thấy tỉ giá nha: vncurrency-exchange.net/app. Chuyển vào STK 112 000 874 512 Vietcombank tên DO QUANG THANG. Gấp lắm m ơi, chuyến bay tao sắp lên rồi.

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [thẻ bị khóa ko rút dc tiền, chuyển cho tao $200 (khoảng 5tr) qua Internet Banking, vncurrency-exchange.net/app, STK 112 000 874 512 Vietcombank, Gấp lắm m ơi, chuyến bay tao sắp lên rồi]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Xin tiền sân bay kèm link đổi tiền là phishing xã hội, không nhiệm vụ.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 182/324 -- split=train row_index=1799 seed_id=seed_157ce0adb043

> Anh [Tuấn] ơi, em [Phúc] đây. Anh lưu số mới này của em nha, số cũ em bị khóa SIM rồi. Anh ơi anh đang rảnh ko? Em nhờ anh một việc gấp được ko ạ. Sếp em vừa nhắn yêu cầu thanh toán hợp đồng đối tác 8 triệu trước 5h chiều nay, mà tk công ty em đang bị đóng băng do ngân hàng xác minh KYC. Em nhờ anh chuyển hộ em vào Vietinbank STK 113000987654 tên NGUYEN HOANG PHUC trước, xong em login Internet Banking công ty chuyển lại anh liền trong vòng 1 tiếng. Anh giúp em với ạ, em đang hoảng lắm 🙏

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [số cũ em bị khóa SIM rồi, tk công ty em đang bị đóng băng do ngân hàng xác minh KYC, thanh toán hợp đồng đối tác 8 triệu trước 5h chiều nay, em login Internet Banking công ty chuyển lại anh liền trong vòng 1 tiếng]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Giả đồng nghiệp xin ứng hợp đồng thuộc social engineering doanh nghiệp.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 183/324 -- split=train row_index=1800 seed_id=seed_157ce0adb043

> Nam ơi tao đây - Tuấn. Số này tao mượn tạm vì đt tao màn hình vỡ r. Mày đang rảnh ko? Tao nhờ mày 1 việc nhỏ thôi. Tao đang ở nước ngoài, cần mua 2 thẻ cào Viettel 500k gửi code cho tao qua đây dc ko? Tao Paypal lại cho mày sau. Gấp lắm mày ơi, tao cần nạp data roaming

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [Số này tao mượn tạm vì đt tao màn hình vỡ r, Tao đang ở nước ngoài, mua 2 thẻ cào Viettel 500k gửi code cho tao, Tao Paypal lại cho mày sau, Gấp lắm mày ơi, tao cần nạp data roaming]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Dụ gửi mã thẻ cào bằng số mượn không phải task scam.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 184/324 -- split=train row_index=1801 seed_id=seed_157ce0adb043

> Anh Tuấn ơi e Linh đây ạ. E đang mượn đt bạn nhắn vì đt e hết pin. A ơi a đang có tiền mặt hay tk ko ạ? E cần gấp 1tr5 để trả tiền ship COD không là bị hoàn hàng mất cọc. A chuyển giúp e Vietinbank STK 108 876 543 21 tên NGUYEN THI LINH nha a. E sẽ chuyển lại qua OTP banking cho a sau 30p ạ. E xin lỗi a vì làm phiền 😢

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [mượn đt bạn nhắn vì đt e hết pin, cần gấp 1tr5 để trả tiền ship COD, Vietinbank STK 108 876 543 21, chuyển lại qua OTP banking cho a sau 30p]
- **Judge scores:** realism=3, label_correctness=2, code_switch_naturalness=3, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge's stated reason:** OTP banking gượng; đây là mạo danh xin tiền trực tiếp và tier bị thấp.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 185/324 -- split=train row_index=1802 seed_id=seed_157ce0adb043

> Tuấn ơi tao Bình đây. Mất đt rồi đang nhờ đồng nghiệp nhắn. Ko liên lạc dc qua zalo hay fb đâu. Tao đang cần gấp 500k thôi, chuyển vào MB Bank: 0021 0000 8876 - Phạm Quốc Bình. Chiều tao gặp mày trả liền ak. Bận thì thôi ko sao đâu nhưng tao đang cần lắm 😅

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [Mất đt rồi đang nhờ đồng nghiệp nhắn, Ko liên lạc dc qua zalo hay fb đâu, cần gấp 500k, chuyển vào MB Bank: 0021 0000 8876, Bận thì thôi ko sao đâu nhưng tao đang cần lắm]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=4, suspicious_span_accuracy=5
- **Judge's stated reason:** Mượn máy xin 500k là mạo danh xã hội, không nhiệm vụ.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 186/324 -- split=train row_index=1803 seed_id=seed_157ce0adb043

> Ơi [Tên], mình là Hương đây! Điện thoại mình bị mất hôm qua nên đang dùng tạm số này. Mình đang kẹt tiền gấp, cần chuyển 3 triệu để đóng viện phí cho mẹ trước 5h chiều nay. Bạn chuyển giúp mình vào STK 9021837465 Vietcombank tên NGUYEN THI HUONG dc ko? Mình trả lại ngay tối nay nha, cảm ơn bạn nhiều lắm!

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [Điện thoại mình bị mất hôm qua nên đang dùng tạm số này, cần chuyển 3 triệu để đóng viện phí cho mẹ trước 5h chiều nay, STK 9021837465 Vietcombank, Mình trả lại ngay tối nay nha]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Số tạm xin viện phí là social engineering, nhãn task sai.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 187/324 -- split=train row_index=1804 seed_id=seed_157ce0adb043

> Alo [Minh] ơi, đây là t nè. Điện thoại t vừa bị mất hôm qua nên phải dùng số mới này nhắn cho m. T đang kẹt tiền gấp, cần chuyển cho t 3 triệu để t đặt cọc chỗ ở mới, mai t trả lại ngay. Chuyển vào STK 9021 8374 5610 Ngân hàng Vietcombank, tên TẠ VĂN HÙNG nha. M chuyển giúp t với, t cảm ơn nhiều lắm!!

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [Điện thoại t vừa bị mất hôm qua nên phải dùng số mới này, T đang kẹt tiền gấp, cần chuyển cho t 3 triệu, mai t trả lại ngay, STK 9021 8374 5610]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Giả bạn mất máy để vay cọc nhà không liên quan nhiệm vụ.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 188/324 -- split=train row_index=1805 seed_id=seed_157ce0adb043

> Tuấn đây mày ơi. Mày nhớ tao ko, hồi cấp 3 cùng lớp 12A2 đó. Tao đang kẹt tiền gấp quá, app Internet Banking tao bị lỗi ko login dc. Mày chuyển giúp tao 2.5k (2 triệu 5) vào Techcombank STK 1903 2281 7764 tên Nguyen Van Tuan đi. Tao Momo lại cho mày liền à, tao có tiền mà app lỗi thôi. OTP tao nhận ko dc nên mới phải nhờ mày.

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [app Internet Banking tao bị lỗi ko login dc, chuyển giúp tao 2.5k, Techcombank STK 1903 2281 7764, OTP tao nhận ko dc, Tao Momo lại cho mày liền]
- **Judge scores:** realism=2, label_correctness=2, code_switch_naturalness=3, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Ghi 2.5k rồi giải thích hai triệu rưỡi rất gượng; không có task.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 189/324 -- split=train row_index=1806 seed_id=seed_157ce0adb043

> Chị [Lan] ơi! Em là Hương đây ạ, acc Facebook cũ của em bị hack mất r nên em lập cái mới này. Chị ơi em đang cần gấp 5 triệu để đặt cọc nhà trọ, chủ nhà bắt đặt cọc trước 6h tối nay không thì mất phòng. Em chuyển lại cho chị ngay tuần sau khi lương về ạ. Chị banking giúp em qua số này nhé: MB Bank - 19038271645 - Trần Thị Hương. Em cảm ơn chị nhiều lắm ạ, gấp quá chị ơi 🙏🙏

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [acc Facebook cũ của em bị hack mất r nên em lập cái mới này, cần gấp 5 triệu, chủ nhà bắt đặt cọc trước 6h tối nay không thì mất phòng, Chị banking giúp em, gấp quá chị ơi]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Facebook mới xin cọc nhà trọ là mạo danh xã hội.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 190/324 -- split=train row_index=1807 seed_id=seed_157ce0adb043

> Alo [Tên], mày ơi tao đang kẹt tiền gấp lắm, điện thoại tao vừa mất nên phải nhắn từ acc mới này. Mày chuyển giúp tao 3 triệu đc ko? Tao gửi lại sau 2 ngày. STK: 0123456789 - Ngân hàng Vietcombank - Nguyễn Văn Hùng. Cần gấp lắm mày ơi, đừng gọi lại số cũ vì mất r.

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [acc mới này, điện thoại tao vừa mất, đừng gọi lại số cũ vì mất r, chuyển giúp tao 3 triệu đc ko, Tao gửi lại sau 2 ngày]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Acc mới vay tiền trực tiếp không phải lừa làm nhiệm vụ.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 191/324 -- split=train row_index=1808 seed_id=seed_157ce0adb043

> Thảo ơi, mình Ngọc nè. Mình đang ở nước ngoài công tác, điện thoại mình bị mất ví lẫn đt luôn rồi. Mình ko login dc Internet Banking vì quên pass, mà ko có đt để nhận OTP nữa. Mày chuyển giúp mình 8 triệu qua Techcombank số tk 19036xxxxxx tên Phạm Thị Ngọc dc ko? Mình về mình trả mày liền, mình đang kẹt ở đây ko có tiền ăn luôn á. Mày cứu mình với, mình nhớ ơn mày lắm 😢

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [đang ở nước ngoài công tác, điện thoại mình bị mất ví lẫn đt luôn, ko login dc Internet Banking, ko có đt để nhận OTP, chuyển giúp mình 8 triệu, 19036xxxxxx, ko có tiền ăn luôn á]
- **Judge scores:** realism=3, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Câu mất ví lẫn điện thoại hơi lỗi; nội dung vẫn là mạo danh.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 192/324 -- split=train row_index=1810 seed_id=seed_157ce0adb043

> Hey Tuấn! Đây là acc Facebook mới của tao - Hùng đây. Acc cũ bị hack hết rồi bro ơi 😭 Tao đang cần gấp 1,500k để nạp vào ví MoMo mua vé máy bay về quê mai. Mày chuyển qua SĐT MoMo: 0987654321 giúp tao với. Tao Payback mày ngay tuần sau khi lãnh lương nha. Bro cứu tao với!!

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [Đây là acc Facebook mới của tao, Acc cũ bị hack hết rồi, cần gấp 1,500k, nạp vào ví MoMo, SĐT MoMo: 0987654321, Payback mày ngay tuần sau]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Facebook mới xin tiền MoMo là mạo danh, không task scam.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 193/324 -- split=train row_index=1811 seed_id=seed_157ce0adb043

> Alo [Minh] ơi, mày ơi cứu tao với. Tao vừa làm mất đt, đang mượn máy người khác nhắn tin. Tài khoản bank của tao cũng bị khóa hết rồi, tao đang kẹt tiền gấp lắm. Mày chuyển giúp tao 3 củ vào STK 9021837465 Vietcombank tên NGUYEN VAN HUNG dc ko? Tao về tao trả liền, hứa đó. Đừng gọi lại số cũ tao vì mất đt rồi nha, nhắn zalo này thôi ak

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [vừa làm mất đt, đang mượn máy người khác, Tài khoản bank của tao cũng bị khóa hết rồi, chuyển giúp tao 3 củ, STK 9021837465 Vietcombank, Đừng gọi lại số cũ tao vì mất đt rồi]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Bạn mất điện thoại và tài khoản bị khóa xin tiền là social engineering.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 194/324 -- split=train row_index=1812 seed_id=seed_157ce0adb043

> Ba ơi con Thảo đây. Con đang ở bệnh viện Chợ Rẫy, điện thoại hết pin cạn rồi phải mượn máy người ta nhắn. Ba chuyển gấp cho con 8.500.000đ để đóng viện phí trước 4h chiều ko họ ko cho xuất viện. Chuyển vào STK Agribank 2109876543210 - Trần Thị Thảo nha ba. Con sẽ gọi lại cho ba sau khi sạc máy. Nhanh lên ba ơi!!!

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [Con đang ở bệnh viện Chợ Rẫy, điện thoại hết pin cạn rồi phải mượn máy người ta nhắn, chuyển gấp cho con 8.500.000đ, đóng viện phí trước 4h chiều ko họ ko cho xuất viện, Con sẽ gọi lại cho ba sau khi sạc máy]
- **Judge scores:** realism=3, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Đe không cho xuất viện hơi lố; giả con xin tiền không phải task.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 195/324 -- split=train row_index=1813 seed_id=seed_157ce0adb043

> Ê Phương! Mình Thảo nè. Mình đang nhắn từ acc Zalo mới vì acc cũ bị khóa do đăng nhập thiết bị lạ. Mình cần mày làm ơn chuyển giúp 1tr5 vào ví ZaloPay của mình trước 5h chiều nha. SĐT ZaloPay: 0776.482.193. Hoặc nếu mày dùng Smart OTP thì chuyển thẳng qua STK 79710003456789 MB Bank cũng dc. Lý do là mình đặt mua hàng online mà quên link thẻ, giờ k link kịp. Mày giúp mình lần này với, mình cần gấp lắm! Mình sẽ trả mày ngay tối nay.

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [acc cũ bị khóa do đăng nhập thiết bị lạ, chuyển giúp 1tr5, SĐT ZaloPay: 0776.482.193, Smart OTP, STK 79710003456789 MB Bank, quên link thẻ, mình cần gấp lắm]
- **Judge scores:** realism=2, label_correctness=2, code_switch_naturalness=3, risk_tier_correctness=5, suspicious_span_accuracy=4
- **Judge's stated reason:** Smart OTP như kênh chuyển và quên link thẻ đều gượng; nhãn task sai.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 196/324 -- split=train row_index=1814 seed_id=seed_157ce0adb043

> Nam ơi, chị Ngọc đây. Chị đang đi công tác Đà Nẵng, ví và điện thoại chính bị mất cắp trên xe buýt r. Chị đang dùng Smart OTP của khách sạn để nhắn cho em. Em có thể chuyển cho chị 8 triệu ko? Chị cần đặt vé máy bay về gấp tối nay. STK VPBank của chị: 8826 1039 4471 - Pham Thi Ngoc. Chị hứa về HCM là trả liền, em tin chị mà 🙏🙏 Đừng kể với ai nha em, chị ngại lắm.

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [ví và điện thoại chính bị mất cắp, đang dùng Smart OTP của khách sạn, chuyển cho chị 8 triệu, STK VPBank của chị: 8826 1039 4471, Đừng kể với ai nha em, cần đặt vé máy bay về gấp tối nay]
- **Judge scores:** realism=1, label_correctness=2, code_switch_naturalness=3, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Không thể dùng Smart OTP khách sạn để nhắn; nội dung mạo danh, không task.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 197/324 -- split=train row_index=1815 seed_id=seed_157ce0adb043

> Alo Bình! Tao Nam đây m ơi. Tao đang kẹt ở bệnh viện Chợ Rẫy với bố, điện thoại tao hết pin cắm nhờ máy người ta nhắn tin cho m. Bố tao cần đặt cọc phòng mổ 8 triệu trước 3h chiều nay mới giữ được lịch, mà tao quên mang thẻ ATM. M chuyển giúp tao vào VPBank app nha: 0912 345 678 hoặc STK 2109876543 tên PHAM VAN NAM. Tao về trả m liền, tao thề đó. Gấp lắm m ơi trả lời tao ngay nha!!

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [điện thoại tao hết pin cắm nhờ máy người ta nhắn tin, cần đặt cọc phòng mổ 8 triệu trước 3h chiều nay, tao quên mang thẻ ATM, STK 2109876543 tên PHAM VAN NAM, Gấp lắm m ơi trả lời tao ngay nha!!]
- **Judge scores:** realism=3, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Câu cắm nhờ máy người ta gượng; đây là mạo danh bạn bệnh viện.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 198/324 -- split=train row_index=1816 seed_id=seed_157ce0adb043

> Alo [Minh] ơi, tao là Hùng đây. Tao vừa làm mất đt, đang mượn máy bạn nhắn tin. Mày có thể chuyển giúp tao 2 triệu ko? Tao đang kẹt tiền gấp lắm, mai tao trả liền. Chuyển vào STK: 0381234567 Ngân hàng Vietcombank tên TK: NGUYEN VAN HUNG nha. Cảm ơn mày nhiều lắm!

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [vừa làm mất đt, đang mượn máy bạn nhắn tin, chuyển giúp tao 2 triệu ko, đang kẹt tiền gấp lắm, mai tao trả liền, STK: 0381234567]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Mượn máy vay tiền trực tiếp không có nhiệm vụ hay hoa hồng.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 199/324 -- split=train row_index=1817 seed_id=seed_157ce0adb043

> Alo [Tên], mình là Hương đây! Mình vừa mất đt, đang dùng tạm máy người khác. Mày có thể chuyển giúp mình 2 triệu ko? Mình cần gấp để đóng tiền học cho con, mai hạn rồi. Chuyển vào STK 9021384756 Vietcombank tên NGUYEN THI HUONG nha. Mình trả sau 2 ngày, hứa luôn!!

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [vừa mất đt, đang dùng tạm máy người khác, chuyển giúp mình 2 triệu ko, cần gấp, STK 9021384756 Vietcombank, Mình trả sau 2 ngày]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Giả người quen mất máy xin học phí thuộc social engineering.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 200/324 -- split=train row_index=1818 seed_id=seed_157ce0adb043

> Tuấn đây mày! Tao đang ở nước ngoài, acc zalo cũ bị hack r nên tao tạo acc mới. Mày có thể giúp tao ko? Tao cần mày đăng nhập Internet Banking mua giúp tao 1 thẻ Agribank E-Mobile Banking trị giá 2tr, chụp ảnh thẻ gửi tao. Tao Paypal lại cho mày ngay, tao đang kẹt ko rút tiền mặt đc. Làm ơn nha mày, tao cần gấp lắm!!

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [acc zalo cũ bị hack r nên tao tạo acc mới, mày đăng nhập Internet Banking mua giúp tao, chụp ảnh thẻ gửi tao, Tao Paypal lại cho mày ngay, tao đang kẹt ko rút tiền mặt đc]
- **Judge scores:** realism=1, label_correctness=2, code_switch_naturalness=3, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Không có thẻ Agribank E-Mobile Banking để mua; kịch bản phi thực tế và không task.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 201/324 -- split=train row_index=1819 seed_id=seed_157ce0adb043

> Bro ơi cứu mình vs!! Tài khoản FB của mình bị hack hết r, mình đang nhắn từ acc phụ này. Mình đang kẹt tiền gấp lắm, cần 5tr để xử lý việc gấp. Mày chuyển qua Momo số 0912 374 856 tên TRAN VAN LONG giúp mình với, mình sẽ chuyển lại qua Internet Banking cho mày ngay tối nay. Mày là người duy nhất mình nhờ được lúc này 😭

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [Tài khoản FB của mình bị hack hết r, đang nhắn từ acc phụ này, cần 5tr để xử lý việc gấp, chuyển qua Momo số 0912 374 856, Mày là người duy nhất mình nhờ được lúc này]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Acc phụ xin MoMo là mạo danh xã hội, không phải task scam.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 202/324 -- split=train row_index=1820 seed_id=seed_157ce0adb043

> Ê [Tên] ơi, mình là Phúc. Mình vừa lỡ tay xóa app ngân hàng, đang cài lại mà chưa xác thực OTP dc. Mình đang cần chuyển tiền gấp cho bên đối tác, họ chỉ nhận chuyển khoản thôi ko nhận tiền mặt. Mày có thể chuyển hộ mình 3.5 triệu vào ACB 2748301956 tên PHAM THANH PHUC ko? Mình sẽ Momo lại cho mày trong vòng 1 tiếng, mình đang ở văn phòng có wifi nên Momo được. Cảm ơn mày nhiều nha, gấp lắm rồi!!

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [lỡ tay xóa app ngân hàng, chưa xác thực OTP dc, chuyển hộ mình 3.5 triệu, ACB 2748301956, Momo lại cho mày trong vòng 1 tiếng, gấp lắm rồi]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Bạn xóa app xin chuyển hộ đối tác là social engineering.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 203/324 -- split=train row_index=1821 seed_id=seed_157ce0adb043

> Alo [Minh] ơi, đây là tao [Hùng] nè. Tao vừa mất điện thoại nên đang nhắn từ số mới. Mày giúp tao chuyển gấp 3 triệu qua account Vietcombank ko? Số TK: 1023456789 - Nguyễn Văn Hùng. Tao đang kẹt tiền gấp lắm, chiều tao trả lại liền nha. Đừng gọi lại số cũ vì tao mất máy rồi.

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [vừa mất điện thoại nên đang nhắn từ số mới, chuyển gấp 3 triệu, Đừng gọi lại số cũ vì tao mất máy rồi, Tao đang kẹt tiền gấp lắm]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Số mới vay tiền gấp không có nhiệm vụ, nhãn sai.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 204/324 -- split=train row_index=1822 seed_id=seed_157ce0adb043

> Chị ơi, em là Hương đây ạ. Chị có nhớ em ko? Em đang ở nước ngoài, tài khoản Internet Banking của em bị khóa đột xuất do đăng nhập sai OTP nhiều lần. Em cần chuyển tiền gấp để đóng học phí hạn hôm nay, không thì bị đuổi học. Chị có thể chuyển giúp em 5.500.000đ vào acc Techcombank số 1908374652 tên ĐỖ THU HƯƠNG không ạ? Em sẽ hoàn lại cho chị qua app ngay khi mở lại được tài khoản. Em cảm ơn chị nhiều lắm ạ 🙏🙏

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [tài khoản Internet Banking của em bị khóa đột xuất, đăng nhập sai OTP nhiều lần, chuyển tiền gấp để đóng học phí hạn hôm nay, không thì bị đuổi học, acc Techcombank số 1908374652, hoàn lại cho chị qua app ngay khi mở lại được tài khoản]
- **Judge scores:** realism=3, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Đe đuổi học hơi lố; đây là người quen xin tiền, không task.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 205/324 -- split=train row_index=1823 seed_id=seed_157ce0adb043

> Chị ơi em là Linh đây ạ, tài khoản Facebook của em bị hack rồi nên em nhắn qua Zalo này. Chị có thể giúp em chuyển 500k không ạ? Em đang cần đóng tiền học gấp, Internet Banking của em đang bị lỗi không login được. Chị chuyển vào số 0987654321 MoMo tên TRAN THI LINH giúp em với ạ. Em cảm ơn chị nhiều lắm ạ 🙏

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [tài khoản Facebook của em bị hack rồi nên em nhắn qua Zalo này, Internet Banking của em đang bị lỗi không login được, chuyển vào số 0987654321 MoMo, cần đóng tiền học gấp]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=4, suspicious_span_accuracy=5
- **Judge's stated reason:** Facebook bị hack xin 500k là mạo danh xã hội, không task.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 206/324 -- split=train row_index=1824 seed_id=seed_157ce0adb043

> Bro ơi, tài khoản Facebook của tao bị hack rồi, tao đang nhắn qua Zalo đây. Tao đang cần gấp 5 triệu để đóng tiền học cho con, chưa kịp rút tiền. Mày chuyển hộ tao trước dc k? Tao sẽ chuyển lại ngay chiều nay qua Internet Banking. Tên: Tran Van Minh | STK: 19036284710 | NH: Techcombank. Tao cần trước 11h trưa nha bro, quá giờ là hết hạn đóng rồi.

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [tài khoản Facebook của tao bị hack rồi, cần gấp 5 triệu, chuyển hộ tao trước dc k, Tao sẽ chuyển lại ngay chiều nay, quá giờ là hết hạn đóng rồi, STK: 19036284710]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Zalo xin học phí sau Facebook hack không phải lừa nhiệm vụ.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 207/324 -- split=train row_index=1825 seed_id=seed_157ce0adb043

> Ơi [Tên], mình là Hương đây! SĐT mới nha, máy cũ bị mất rồi. Đang cần gấp 3 triệu để đóng viện phí cho mẹ, chuyển giúp mình vào STK 0981234567 Vietcombank tên NGUYEN THI HUONG dc ko? Mình trả ngay chiều nay hứa luôn. Cảm ơn bạn nhiều lắm ❤️

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [SĐT mới nha, máy cũ bị mất rồi, Đang cần gấp 3 triệu, đóng viện phí cho mẹ, chuyển giúp mình vào STK 0981234567, Mình trả ngay chiều nay hứa luôn]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Số mới xin viện phí thuộc social engineering, nhãn task sai.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 208/324 -- split=train row_index=1826 seed_id=seed_157ce0adb043

> Alo [Minh] ơi, đây là tao [Tuấn] nè. Tao vừa mất đt, đang mượn máy bạn nhắn. Tao đang kẹt tiền gấp, mày chuyển giúp tao 3 triệu qua STK 9021384756 Vietcombank tên NGUYEN VAN TUAN dc ko? Tao về tao trả liền, bạn bè lâu năm mà mày, tao hứa!

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [vừa mất đt, đang mượn máy bạn nhắn, kẹt tiền gấp, chuyển giúp tao 3 triệu, STK 9021384756 Vietcombank]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Giả bạn mất điện thoại để vay tiền không có task.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 209/324 -- split=train row_index=1827 seed_id=seed_157ce0adb043

> Hey [Tuấn], mày nhớ tao [Khoa] ko? Tao đang ở nước ngoài, tài khoản Internet Banking bị khoá do đăng nhập sai OTP nhiều lần. Tao cần mày chuyển hộ tao 8 triệu để tao xử lý việc gấp bên này. TK Techcombank: 19038271645 - TRAN MINH KHOA. Mày chuyển xong báo tao qua đây nha, số VN tao ko dùng đc vì roaming. Tao về sẽ trả ngay.

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [tài khoản Internet Banking bị khoá do đăng nhập sai OTP nhiều lần, số VN tao ko dùng đc vì roaming, chuyển hộ tao 8 triệu, 19038271645]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Người quen ở nước ngoài xin chuyển hộ thuộc mạo danh xã hội.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 210/324 -- split=train row_index=1828 seed_id=seed_157ce0adb043

> Chị ơi! Em là Linh, em của chị Nga đây ạ. Chị Nga nhờ em nhắn vì chị ấy đang bận họp, đt chị ấy hết pin. Chị có thể chuyển giúp chị Nga 3.500.000đ trước k ạ? Chị Nga đang cần đặt cọc hàng gấp, nếu k đặt trước 3h chiều là mất đơn. Chị chuyển vào số này giúp ạ: 0909.374.821 MoMo hoặc STK 006704812930 BIDV. Chị Nga sẽ gọi lại cảm ơn chị sau ạ!

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [Chị Nga nhờ em nhắn vì chị ấy đang bận họp, đt chị ấy hết pin, chuyển giúp chị Nga 3.500.000đ, nếu k đặt trước 3h chiều là mất đơn, 0909.374.821 MoMo, STK 006704812930 BIDV]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Giả em gái chuyển lời xin tiền cọc không phải task.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 211/324 -- split=train row_index=1829 seed_id=seed_157ce0adb043

> Alo [Minh] ơi, đây là tao [Tuấn] nè. Máy tao vừa bị hỏng phải mượn số này nhắn. Tao đang kẹt tiền gấp, cần chuyển cho tao 3 triệu qua STK 9021847563 Vietcombank tên NGUYEN VAN TUAN dc ko? Tao trả lại mày sau 2 ngày, quan trọng lắm mày ơi, nhờ mày giúp nha!

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [Máy tao vừa bị hỏng phải mượn số này nhắn, cần chuyển cho tao 3 triệu, STK 9021847563 Vietcombank, Tao trả lại mày sau 2 ngày]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Máy hỏng rồi vay ba triệu là social engineering, không nhiệm vụ.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 212/324 -- split=train row_index=1830 seed_id=seed_157ce0adb043

> Alo [Minh] ơi, đây là tài khoản mới của tao, tao vừa mất điện thoại hôm qua nên phải dùng SĐT khác. Tao đang cần gấp 3 triệu để đóng viện phí cho mẹ, mày chuyển giúp tao qua STK 9934xxxx12 Vietcombank tên NGUYEN VAN MINH dc ko? Tao sẽ trả lại ngay chiều mai, tao thề đó. Đừng gọi lại số cũ vì đã mất rồi nha.

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [tài khoản mới của tao, tao vừa mất điện thoại hôm qua nên phải dùng SĐT khác, đang cần gấp 3 triệu, đóng viện phí cho mẹ, Đừng gọi lại số cũ vì đã mất rồi nha]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Tài khoản mới xin viện phí thuộc mạo danh bạn bè.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 213/324 -- split=train row_index=1831 seed_id=seed_157ce0adb043

> Chị [Hoa] ơi! Em là Linh đây ạ, em lỡ bị hack tài khoản Facebook nên phải nhắn qua Zalo mới này. Chị ơi em đang cần đóng học phí gấp hôm nay là hạn cuối rồi mà app MoMo em đang bị lỗi không chuyển dc. Chị có thể chuyển hộ em 5.500.000đ vào Techcombank số TK: 19038821xxxx chủ TK: TRAN THI LINH không ạ? Em sẽ chuyển lại cho chị qua Internet Banking ngay chiều nay ạ, em hứa đó chị. Chị cứu em với ạ 🙏🙏

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [bị hack tài khoản Facebook, Zalo mới này, đóng học phí gấp hôm nay là hạn cuối, app MoMo em đang bị lỗi không chuyển dc, chuyển hộ em 5.500.000đ, Techcombank số TK: 19038821xxxx, chuyển lại cho chị qua Internet Banking ngay chiều nay]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Facebook hack và Zalo mới xin tiền học không thuộc task scam.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 214/324 -- split=train row_index=1832 seed_id=seed_157ce0adb043

> Sis [Mai] ơi tao [Ngọc] đây! Tao lỡ bị khoá app ngân hàng, đang chờ mở lại mà có việc gấp quá. Mày có thể chuyển hộ tao 1tr5 ko? Tao sẽ chuyển lại qua Momo ngay khi app mở dc. STK VPBank của tao: 102938475 - LE THU NGOC. Nhanh lên nha sis tao cần trước 3h chiều. Cảm ơn mày nhìu 😘 À mà đừng inbox acc kia tao đang ko vào dc.

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [bị khoá app ngân hàng, Tao sẽ chuyển lại qua Momo ngay khi app mở dc, đừng inbox acc kia tao đang ko vào dc, cần trước 3h chiều, 102938475]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge's stated reason:** Xin chuyển hộ trực tiếp đáng high-risk và là mạo danh, không task.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 215/324 -- split=train row_index=1833 seed_id=seed_157ce0adb043

> Bro ơi cứu mình với! Acc Facebook mình bị hack hết rồi, mình đang nhắn từ Zalo mới tạo. Mình đang kẹt tiền gấp, shop online của mình cần thanh toán đơn hàng 5tr cho đối tác không thì bị phạt hợp đồng. Mày chuyển tạm giúp mình qua Momo số 0934127865 đi, tên hiện lên là TRAN VAN MINH. Mình sẽ bank lại cho mày ngay tối nay qua Internet Banking, mình có sao kê đàng hoàng nha bro. Đừng lo!!

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [Acc Facebook mình bị hack hết rồi, Zalo mới tạo, kẹt tiền gấp, chuyển tạm giúp mình qua Momo số 0934127865, bank lại cho mày ngay tối nay, phạt hợp đồng]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Zalo mới xin vốn shop là social engineering, không có task.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 216/324 -- split=train row_index=1834 seed_id=seed_157ce0adb043

> Tuấn đây mày! Tao đang ở nước ngoài, app ngân hàng của tao bị lỗi k login dc, OTP cũng k nhận được vì số VN của tao tạm thời bị khóa. Mày có thể chuyển hộ tao 8 triệu k? Tao cần trả tiền khách sạn gấp ko thì bị đuổi ra đường. Tao sẽ chuyển lại ngay khi về VN hoặc nhờ vợ tao chuyển lại cho mày hôm nay. STK nhận tiền: 0012000496318 - Vietinbank - Nguyen Thanh Tuan. Mày giúp tao với, tao đang rất kẹt!

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [app ngân hàng của tao bị lỗi k login dc, OTP cũng k nhận được, số VN của tao tạm thời bị khóa, chuyển hộ tao 8 triệu, bị đuổi ra đường, STK nhận tiền: 0012000496318]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Giả bạn ở nước ngoài xin tiền khách sạn không phải task scam.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 217/324 -- split=train row_index=1835 seed_id=seed_157ce0adb043

> Bro ơi t là Nam, mày nhớ t k? Học cùng hồi cấp 3 á. T đang kẹt ở Đà Nẵng, ví bị móc mất hết tiền + cmnd lun r 😭 Mày chuyển t 800k để mua vé xe về HN dc k? Vietinbank: 1122334455 - Nguyen Hoang Nam. T venmo lại mày sau nha.

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [kẹt ở Đà Nẵng, ví bị móc mất hết tiền + cmnd, chuyển t 800k để mua vé xe, venmo lại mày sau]
- **Judge scores:** realism=3, label_correctness=2, code_switch_naturalness=2, risk_tier_correctness=4, suspicious_span_accuracy=5
- **Judge's stated reason:** Venmo không tự nhiên trong ngữ cảnh Việt Nam; đây là mạo danh người quen.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 218/324 -- split=train row_index=1836 seed_id=seed_157ce0adb043

> Alo [Minh] ơi, đây là tài khoản mới của tao, đt cũ bị mất r. Tao đang kẹt tiền gấp, mày có thể chuyển cho tao 3 triệu k? Tao trả lại sau 2 ngày nha. Chuyển vào STK: 0398271645 Ngân hàng Vietcombank, tên: NGUYEN VAN MINH. Ko có thì 1 triệu cũng dc, cần gấp lắm!!

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [tài khoản mới của tao, đt cũ bị mất r, đang kẹt tiền gấp, chuyển cho tao 3 triệu k, Tao trả lại sau 2 ngày nha, STK: 0398271645]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Tài khoản mới vay tiền gấp không liên quan nhiệm vụ.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 219/324 -- split=train row_index=1837 seed_id=seed_157ce0adb043

> Alo [Minh] ơi, đây là tao [Nam] nè. Tao vừa mất điện thoại nên đang dùng số mới này. Tao đang cần gấp 3 triệu để đóng tiền viện phí cho mẹ, mày chuyển giúp tao vào STK 9021384756 Ngân hàng VPBank tên NGUYEN VAN NAM dc ko? Tao sẽ trả mày ngay chiều mai. Cảm ơn mày nhiều lắm!

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [vừa mất điện thoại nên đang dùng số mới, cần gấp 3 triệu, đóng tiền viện phí cho mẹ, STK 9021384756, Tao sẽ trả mày ngay chiều mai]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Số mới xin viện phí là mạo danh xã hội, nhãn task không đúng.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 220/324 -- split=train row_index=1839 seed_id=seed_157ce0adb043

> Alo [TÊN], mày ơi tao đang kẹt tiền gấp lắm, điện thoại tao vừa mất nên phải dùng acc mới nhắn. Mày chuyển giúp tao 3 triệu vào STK 9021 4857 3301 Ngân hàng VPBank tên NGUYEN VAN MINH dc ko? Tao trả mày sau 2 ngày, gấp lắm mày ơi đừng hỏi nhiều nha 🙏

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [điện thoại tao vừa mất nên phải dùng acc mới nhắn, chuyển giúp tao 3 triệu, STK 9021 4857 3301, đừng hỏi nhiều nha]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Acc mới xin tiền và cấm hỏi là mạo danh xã hội, không task.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 221/324 -- split=train row_index=1840 seed_id=seed_157ce0adb043

> Tuấn đây m ơi! T nhắn từ fb phụ vì acc chính bị khóa do đăng nhập lạ. Nhanh giúp t chút dc ko, t đang ở nước ngoài công tác, thẻ bị block ko rút tiền dc. Cần m chuyển tạm 8tr vào account này: 1234 5678 9900 - Techcombank - LE QUOC TUAN. T sẽ hoàn lại qua paypal hoặc chuyển khoản ngay khi về. Ko cần OTP hay gì hết, chuyển thẳng vào STK là xong. Gấp lắm m ơi, t đang kẹt ở sân bay!!

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [acc chính bị khóa do đăng nhập lạ, đang ở nước ngoài công tác, thẻ bị block ko rút tiền dc, 1234 5678 9900 - Techcombank - LE QUOC TUAN, Ko cần OTP hay gì hết, hoàn lại qua paypal hoặc chuyển khoản ngay khi về, t đang kẹt ở sân bay]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Giả bạn ở nước ngoài xin tiền sân bay không có nhiệm vụ.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 222/324 -- split=train row_index=1841 seed_id=seed_157ce0adb043

> Alo [Minh] ơi, đây là tao [Nam] nè. Tao vừa mất đt, đang mượn máy người khác nhắn. Tài khoản bank của tao bị lỗi ko rút dc tiền, mày chuyển giúp tao 3 triệu qua số 0987.654.321 (Nguyễn Văn Nam) được ko? Tao về tao trả liền, gấp lắm mày ơi!

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [vừa mất đt, mượn máy người khác, Tài khoản bank của tao bị lỗi ko rút dc tiền, chuyển giúp tao 3 triệu, 0987.654.321, gấp lắm mày ơi]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Mượn máy xin chuyển tiền trực tiếp thuộc social engineering.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 223/324 -- split=train row_index=1842 seed_id=seed_157ce0adb043

> Alo [Minh] ơi, đây là tài khoản mới của tao, điện thoại cũ bị mất r. Mày đang rảnh ko? Tao đang kẹt tiền gấp lắm, cần mượn 3 triệu để đóng viện phí cho mẹ, mai tao trả liền. Mày chuyển vào STK: 0981234567 Ngân hàng Vietcombank tên NGUYEN VAN MINH nha. Gấp lắm mày ơi, tao cảm ơn nhiều!

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [tài khoản mới của tao, điện thoại cũ bị mất r, cần mượn 3 triệu để đóng viện phí cho mẹ, mai tao trả liền, STK: 0981234567]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Tài khoản mới xin viện phí là mạo danh bạn bè, không task.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 224/324 -- split=train row_index=1843 seed_id=seed_157ce0adb043

> Chị [Hoa] ơi! Em là Linh — bạn cùng lớp chị hồi cấp 3 đó. Acc Facebook của em bị hack hết rồi chị ơi, em đang dùng tạm acc này nhắn chị. Chị ơi cho em mượn 5tr dc ko ạ? Em đang kẹt tiền đóng học phí gấp hôm nay là deadline rồi. Chị chuyển vào Momo số 0387654219 tên TRAN THI LINH giúp em nha. Em sẽ hoàn lại chị cuối tuần này khi ba em gửi tiền lên. Chị là người duy nhất em dám nhờ lúc này 🙏🙏

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [Acc Facebook của em bị hack hết rồi, đang dùng tạm acc này, cho em mượn 5tr dc ko, đóng học phí gấp hôm nay là deadline, chuyển vào Momo số 0387654219, Chị là người duy nhất em dám nhờ lúc này]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Giả bạn học cũ dùng acc tạm xin học phí không phải task.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 225/324 -- split=train row_index=1844 seed_id=seed_157ce0adb043

> Alo [TÊN BẠN] ơi, mình là Minh đây! Điện thoại mình vừa bị mất hôm qua nên phải dùng số mới này. Mình đang kẹt tiền gấp lắm, cần chuyển cho mình 3 triệu qua account Vietcombank ko? Số tk: 1023456789 - Nguyễn Văn Minh. Mình sẽ trả lại ngay chiều mai nha, cảm ơn bạn nhiều!

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [Điện thoại mình vừa bị mất hôm qua nên phải dùng số mới này, Mình đang kẹt tiền gấp lắm, cần chuyển cho mình 3 triệu, Mình sẽ trả lại ngay chiều mai nha]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Số mới vay tiền trực tiếp không có công việc hay hoa hồng.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 226/324 -- split=train row_index=1845 seed_id=seed_157ce0adb043

> Tuấn ơi mk Hùng nè. SĐT mk đổi r số mới 0987112233 nha. Mày đang rảnh ko? Mk nhờ mày việc này tí dc ko. Mk đang ở nước ngoài, thẻ ATM bị block ko rút dc, cần chuyển gấp 8tr cho đối tác trc 10h tối. Mày chuyển hộ mk vào acc này: MB Bank - 0765432198 - TRAN QUOC HUNG. Mk sẽ hoàn lại mày qua PayPal hoặc chuyển khoản ngay khi về. Gấp lắm Tuấn ơi 😭

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [SĐT mk đổi r số mới 0987112233 nha, đang ở nước ngoài, thẻ ATM bị block ko rút dc, chuyển gấp 8tr cho đối tác trc 10h tối, chuyển hộ mk vào acc này: MB Bank - 0765432198, hoàn lại mày qua PayPal hoặc chuyển khoản ngay khi về]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Giả bạn đổi số ở nước ngoài xin chuyển đối tác là social engineering.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 227/324 -- split=train row_index=1846 seed_id=seed_157ce0adb043

> Bro ơi tài khoản Facebook của tao bị hack r, tao đang nhắn từ acc phụ này. Mày cho tao mượn 5tr dc ko? Tao cần chuyển khoản gấp cho thằng bạn ngoài HN, chiều tao gặp mày trả liền. Chuyển vô Momo số 0387 654 921 giùm tao nha, tên hiển thị là Minh Tuan. Gấp lắm bro!!

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [tài khoản Facebook của tao bị hack r, đang nhắn từ acc phụ này, cho tao mượn 5tr dc ko, chuyển khoản gấp, Chuyển vô Momo số 0387 654 921, chiều tao gặp mày trả liền]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Facebook phụ xin MoMo là mạo danh xã hội, nhãn task sai.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 228/324 -- split=train row_index=1847 seed_id=seed_157ce0adb043

> Tuấn! Tau đây, Khoa nè. Tau đang kẹt ở Đà Nẵng công tác, ví bị móc mất hết tiền + cmnd. Mày chuyển cho tau 3 củ dc ko? Tau cần đặt vé xe về gấp tối nay. Chuyển vào Techcombank STK: 19028834712 tên LE MINH KHOA. Ko có mày tau chịu chết r 😅 Tau về tau trả liền, thề!

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [đang kẹt ở Đà Nẵng công tác, ví bị móc mất hết tiền, chuyển cho tau 3 củ dc ko, Techcombank STK: 19028834712, Ko có mày tau chịu chết r]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=3
- **Judge's stated reason:** Lời cầu cứu có thể thật nhưng không có task; các span chủ yếu là hoàn cảnh.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 229/324 -- split=train row_index=1848 seed_id=seed_157ce0adb043

> Chị Lan ơi!! Em là Thảo - con của chị Hoa hàng xóm đây ạ. Chị ơi mẹ em đang nằm viện cấp cứu, em cần đóng viện phí gấp 5 triệu mà ATM em bị nuốt thẻ rồi 😭😭 Tài khoản Internet Banking của em cũng đang bị lỗi ko đăng nhập dc. Chị có thể chuyển khoản giúp em trước ko ạ, em sẽ mang tiền mặt đến trả chị ngay chiều nay ạ. Số tài khoản: MB Bank - 19038847261 - Trần Thị Thảo. Chị cứu em với ạ, em cảm ơn chị nhiều lắm 🙏🙏

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [mẹ em đang nằm viện cấp cứu, cần đóng viện phí gấp 5 triệu, ATM em bị nuốt thẻ rồi, Internet Banking của em cũng đang bị lỗi ko đăng nhập dc, chuyển khoản giúp em trước ko ạ, em sẽ mang tiền mặt đến trả chị ngay chiều nay, MB Bank - 19038847261]
- **Judge scores:** realism=3, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Nhiều sự cố tài chính cùng lúc hơi dựng; đây là mạo danh người quen.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 230/324 -- split=train row_index=1849 seed_id=seed_157ce0adb043

> Sis [Mai] ơi mình [Ngọc] nè. Acc Facebook mình bị hack hết rồi nên mình lập nick mới này. Sis ơi sis đang có tiền trong ví MoMo hay app ngân hàng ko? Mình cần chuyển gấp 2tr500 để thanh toán đơn hàng online, thẻ mình bị từ chối ko hiểu sao. Sis chuyển giúp mình qua SHB số tk 0601234789 tên DO THI NGOC nha, mình Momo lại cho sis liền sau khi mình fix dc vấn đề thẻ. Mình cảm ơn sis nhiều lắm 🥺

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [Acc Facebook mình bị hack hết rồi, lập nick mới này, thẻ mình bị từ chối ko hiểu sao, SHB số tk 0601234789 tên DO THI NGOC, Momo lại cho sis liền]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Nick mới xin thanh toán đơn hàng thuộc social engineering, không task.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 231/324 -- split=train row_index=1850 seed_id=seed_157ce0adb043

> Ơi [Minh], mày ơi cứu tao với!! Tao vừa mất đt, đang mượn máy người ta nhắn. Tao cần gấp 3 triệu để đặt cọc chỗ trọ mới, mai trả ngay ak. Mày chuyển giúp tao vào STK: 0381927465 Ngân hàng Vietcombank tên NGUYEN VAN HUNG dc ko? Tao hứa mai trả, tao đang kẹt lắm 😭

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [mày ơi cứu tao với!!, Tao vừa mất đt, đang mượn máy người ta nhắn, Tao cần gấp 3 triệu, mai trả ngay ak, STK: 0381927465, tao đang kẹt lắm]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Giả bạn mất điện thoại để vay cọc trọ không liên quan task.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 232/324 -- split=train row_index=1851 seed_id=seed_157ce0adb043

> Chị [Hoa] ơi em là [Linh] đây ạ 😭 Em đang kẹt tiền gấp quá chị ơi. Hôm nay em lỡ chuyển nhầm 5 triệu vào tài khoản sai rồi, ngân hàng bảo phải có tiền trong acc mới hoàn lại dc. Em đang ko có internet banking để tự xử lý, chị có thể chuyển tạm cho em 5tr ko ạ? Chị chuyển vào Momo số 0387xxxxxx tên TRAN THI LINH giúp em với, chiều em trả liền ạ. Em đang dùng acc zalo mới vì acc cũ bị hack mất rồi chị ơi 😢 Chị tin em nha, em là Linh học cùng lớp chị hồi cấp 3 đó ạ.

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [acc zalo mới vì acc cũ bị hack mất rồi, ngân hàng bảo phải có tiền trong acc mới hoàn lại dc, chuyển tạm cho em 5tr ko ạ, Chị chuyển vào Momo số 0387xxxxxx, chiều em trả liền ạ, Em đang ko có internet banking]
- **Judge scores:** realism=3, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Lý do cần tiền để hoàn nhầm vô lý; vẫn là Zalo mạo danh.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 233/324 -- split=train row_index=1852 seed_id=seed_157ce0adb043

> Chị Lan ơi! Em là Thảo đây ạ, em đang dùng acc Zalo mới vì acc cũ bị hack mất rồi 😭 Chị ơi chị có thể giúp em chuyển khoản 5tr dc ko ạ? Em đang cần gấp để đóng học phí, deadline hôm nay mà em lỡ quên rút tiền. App Internet Banking của em cũng đăng nhập ko dc vì đổi số điện thoại rồi. Chị chuyển vào STK 9988776655 NH Techcombank tên DO THI THAO giúp em với ạ, em Momo lại cho chị ngay chiều nay 🙏🙏 Em cảm ơn chị nhiều lắm ạ!

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [acc cũ bị hack mất rồi, chuyển khoản 5tr dc ko ạ, deadline hôm nay, App Internet Banking của em cũng đăng nhập ko dc, STK 9988776655 NH Techcombank, em Momo lại cho chị ngay chiều nay]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Acc hack xin học phí trực tiếp là social engineering.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 234/324 -- split=train row_index=1853 seed_id=seed_157ce0adb043

> Chị ơi!! Em là Lan - bạn cùng lớp chị đó. Tài khoản Facebook em bị hack rồi nên em nhắn qua Zalo nha. Chị ơi cho em mượn 5tr dc ko ạ? Em đang cần đóng học phí gấp trước 5h chiều nay không là bị đuổi học. Chị chuyển qua MoMo giúp em nha: 0987.654.321 (Trần Thị Lan). Chị chuyển xong nhắn em biết với ạ, em cảm ơn chị nhiều lắm 🙏🙏 Tối nay em qua nhà trả chị liền ak.

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [Tài khoản Facebook em bị hack rồi nên em nhắn qua Zalo, cho em mượn 5tr dc ko, cần đóng học phí gấp trước 5h chiều nay không là bị đuổi học, chuyển qua MoMo giúp em nha: 0987.654.321, Tối nay em qua nhà trả chị liền]
- **Judge scores:** realism=3, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Đe đuổi học hơi lố; Facebook hack xin MoMo không phải task.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 235/324 -- split=train row_index=1854 seed_id=seed_157ce0adb043

> Alo [Minh] ơi, đây là tài khoản mới của tao, điện thoại cũ bị mất r. Mày có thể chuyển giúp tao 2 triệu ko? Tao đang kẹt tiền gấp lắm, mai tao trả lại nha. STK: 19038472910 Vietcombank - Nguyen Van Minh. Chuyển xong nhắn tao biết ak!

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [tài khoản mới của tao, điện thoại cũ bị mất r, chuyển giúp tao 2 triệu ko, đang kẹt tiền gấp lắm, mai tao trả lại nha, STK: 19038472910 Vietcombank]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Tài khoản mới vay hai triệu thuộc mạo danh xã hội.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 236/324 -- split=train row_index=1855 seed_id=seed_157ce0adb043

> e ơi! tài khoản zalo của a bị hack r, bọn nó đang nhắn tin cho mn trong danh bạ. e đừng tin nhé. a đang nhắn từ fb này. a cần gấp 5tr để đóng viện phí cho mẹ, a sẽ chuyển lại qua Internet Banking ngay tối nay. e có thể giúp a ko? số tk: MB Bank 0987123456 - TRAN VAN MINH. a cảm ơn e nhìu

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [tài khoản zalo của a bị hack r, cần gấp 5tr để đóng viện phí cho mẹ, a sẽ chuyển lại qua Internet Banking ngay tối nay, số tk: MB Bank 0987123456]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Cảnh báo Zalo hack rồi xin viện phí vẫn là social engineering, không task.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 237/324 -- split=train row_index=1856 seed_id=seed_157ce0adb043

> Alo [Minh] ơi, tao đây Hùng nè. Tao vừa mất đt, đang dùng số mới tạm thời. Mày có thể chuyển giúp tao 3 triệu ko? Tao đang kẹt tiền gấp lắm, mai tao trả lại liền. STK: 0123456789 Ngân hàng Vietcombank tên NGUYEN VAN HUNG. Tao hứa trả ngay sáng mai nha mày ơi 🙏

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [vừa mất đt, đang dùng số mới tạm thời, chuyển giúp tao 3 triệu ko, Tao đang kẹt tiền gấp lắm, mai tao trả lại liền, STK: 0123456789]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Số mới vay tiền gấp không liên quan làm nhiệm vụ.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 238/324 -- split=train row_index=1857 seed_id=seed_157ce0adb043

> Alo [Minh] ơi, tao là Hùng đây. Tao vừa bị mất đt, đang mượn máy bạn nhắn tin. Tài khoản bank của tao cũng bị khóa tạm thời rồi, đang cần gấp 3 triệu để đóng viện phí cho mẹ tao. Mày chuyển giúp tao vào STK 9034 5678 2211 Vietcombank - Nguyễn Văn Hùng nha. Tao về sẽ trả ngay, hứa luôn. Cảm ơn mày nhiều lắm!!

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [vừa bị mất đt, Tài khoản bank của tao cũng bị khóa tạm thời rồi, cần gấp 3 triệu để đóng viện phí, Mày chuyển giúp tao vào STK 9034 5678 2211 Vietcombank, đang mượn máy bạn nhắn tin]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Giả bạn mất máy xin viện phí thuộc mạo danh xã hội.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 239/324 -- split=train row_index=1858 seed_id=seed_157ce0adb043

> Cô [Phương] ơi con là [Bảo] đây ạ. Con đang ở bệnh viện Chợ Rẫy cần đóng viện phí gấp 12 triệu, họ ko cho mổ nếu chưa đóng. Đt con hết pin nên con nhờ bạn nhắn giúp. Cô chuyển giúp con qua Techcombank STK 19038821045 tên TRAN NGOC BAO dc ko ạ? Con sẽ hoàn lại cô ngay khi ra viện. Con sợ lắm cô ơi 😢 cô đừng gọi lại vì đt con chết rồi ạ

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [đang ở bệnh viện Chợ Rẫy cần đóng viện phí gấp 12 triệu, họ ko cho mổ nếu chưa đóng, Đt con hết pin nên con nhờ bạn nhắn giúp, Techcombank STK 19038821045, cô đừng gọi lại vì đt con chết rồi ạ]
- **Judge scores:** realism=3, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Đe không mổ hơi cường điệu; giả người thân không phải task.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 240/324 -- split=train row_index=1859 seed_id=seed_157ce0adb043

> Này m ơi, t là Hùng đây. Acc Facebook t bị hack xong bọn nó đổi số r. T đang cần nạp tiền gấp để gia hạn hợp đồng, m chuyển t 3.500k trước đc k? STK Agribank: 6677889900 - Pham Quoc Hung. T gửi lại sau 2 tiếng nha, cảm ơn m nhiều.

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [Acc Facebook t bị hack, bọn nó đổi số r, nạp tiền gấp để gia hạn hợp đồng, chuyển t 3.500k trước đc k, gửi lại sau 2 tiếng]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Facebook hack xin ứng hợp đồng là social engineering, không task.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 241/324 -- split=train row_index=1860 seed_id=seed_157ce0adb043

> Chị [Hoa] ơi em là [Linh] đây ạ, tài khoản Facebook em bị hack r nên em lập acc mới nhắn chị. Chị ơi em đang kẹt tiền quá, hôm nay deadline đóng học phí 5tr500 mà app Internet Banking em bị lỗi ko chuyển dc. Chị có thể chuyển hộ em vào Techcombank STK 19038871234 tên LE THI LINH ko ạ? Chiều em Momo lại chị liền, em cảm ơn chị nhìu lắm ạ 🙏🙏

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [tài khoản Facebook em bị hack r nên em lập acc mới, app Internet Banking em bị lỗi ko chuyển dc, deadline đóng học phí 5tr500, Chiều em Momo lại chị liền]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Acc mới xin học phí thuộc mạo danh, không lừa nhiệm vụ.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 242/324 -- split=train row_index=1861 seed_id=seed_157ce0adb043

> Chị ơi em là Linh đây ạ (acc Zalo cũ của em bị hack rồi chị ơi 😭). Em đang cần gấp 5tr để thanh toán đơn hàng online, bên shop họ chỉ chờ thêm 30 phút thôi là hủy đơn. Chị có thể chuyển qua MoMo số 0987xxxxxx tên TRAN THI LINH giúp em ko ạ? Em sẽ chuyển lại qua Internet Banking ngay tối nay khi về đến nhà. Chị đừng gọi vào số cũ vì em ko nghe dc, nhắn tin ở đây thôi ạ. Em cảm ơn chị nhiều lắm 🙏🙏

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [acc Zalo cũ của em bị hack rồi, chỉ chờ thêm 30 phút thôi là hủy đơn, chuyển qua MoMo số 0987xxxxxx, Chị đừng gọi vào số cũ vì em ko nghe dc, chuyển lại qua Internet Banking ngay tối nay]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Zalo mới xin tiền đơn hàng là social engineering rõ.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 243/324 -- split=train row_index=1862 seed_id=seed_157ce0adb043

> Alo [Minh] ơi, đây là tao [Nam] nè. Tao vừa mất đt, đang mượn máy bạn nhắn. Tao đang kẹt tiền gấp, mày chuyển giúp tao 3 triệu vào STK 9021 8834 5567 Vietcombank tên NGUYEN VAN NAM dc ko? Tao về tao trả liền, cảm ơn mày nhiều nha!

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [vừa mất đt, đang mượn máy bạn, kẹt tiền gấp, chuyển giúp tao 3 triệu, STK 9021 8834 5567 Vietcombank, Tao về tao trả liền]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Bạn mất điện thoại vay tiền trực tiếp không có task.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 244/324 -- split=train row_index=1863 seed_id=seed_157ce0adb043

> Alo [TÊN], mình là Hương đây! Mình vừa mất đt, đang dùng tạm số mới này. Mày có thể chuyển giúp mình 2 triệu k? Mình đang kẹt tiền gấp lắm, mai mình trả lại ngay. Chuyển vào STK: 0381920475 Ngân hàng Vietcombank tên Nguyen Thi Huong nha. Cảm ơn mày nhiều!

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [vừa mất đt, đang dùng tạm số mới này, chuyển giúp mình 2 triệu k, đang kẹt tiền gấp lắm, mai mình trả lại ngay, STK: 0381920475]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Số mới xin hai triệu là mạo danh xã hội, nhãn sai.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 245/324 -- split=train row_index=1864 seed_id=seed_157ce0adb043

> Chị ơi em đây, Lan đây ạ! Tài khoản Facebook của em bị hack nên em nhắn từ acc mới này. Chị ơi chị có thể chuyển cho em 5 triệu qua Momo được ko ạ? Số Momo của em là 0987654321. Em đang cần đóng viện phí gấp cho mẹ, bệnh viện họ yêu cầu đóng trước 5h chiều nay không thì mẹ em bị đuổi ra ngoài ạ. Em hứa cuối tuần này em gặp chị em trả liền ạ. Chị giúp em với ạ 🙏🙏

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [Tài khoản Facebook của em bị hack, acc mới này, chuyển cho em 5 triệu qua Momo, đóng viện phí gấp cho mẹ, bệnh viện họ yêu cầu đóng trước 5h chiều nay, bị đuổi ra ngoài]
- **Judge scores:** realism=2, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Đe đuổi bệnh nhân vì chậm viện phí rất lố; không phải task.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 246/324 -- split=train row_index=1865 seed_id=seed_157ce0adb043

> Chị ơi em là Lan Anh đây ạ, tài khoản Facebook của em bị hack nên em lập cái mới này. Chị có thể giúp em không ạ? Em đang cần thanh toán học phí online gấp mà app Internet Banking của em đang bị lỗi không login dc. Chị chuyển hộ em 5.500.000đ vào STK 1903 4471 8822 034 Techcombank - Trần Thị Bảo Ngọc giúp em với ạ, em sẽ chuyển lại qua MoMo cho chị ngay trong tối nay ạ. Em cảm ơn chị nhiều lắm 🙏🙏 Chị xác nhận giúp em nhé vì em đang gấp lắm ạ, deadline nộp học phí là 5h chiều nay thôi ạ

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [tài khoản Facebook của em bị hack nên em lập cái mới này, app Internet Banking của em đang bị lỗi không login dc, chuyển hộ em 5.500.000đ, em sẽ chuyển lại qua MoMo cho chị ngay trong tối nay, deadline nộp học phí là 5h chiều nay thôi ạ]
- **Judge scores:** realism=3, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Tên người gửi và chủ tài khoản lệch; đây là mạo danh, không task.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 247/324 -- split=train row_index=1866 seed_id=seed_157ce0adb043

> Chào em, anh Đức đây (bạn học cấp 3 của em đó). Anh đang dùng tạm fb này vì acc chính bị khóa. Anh đang cần gấp 2 triệu để thanh toán hóa đơn điện trước 11h59 hôm nay không bị cắt điện. Internet Banking anh đang bị lỗi xác thực OTP. Em có thể chuyển giúp anh vào Techcombank STK 1903 2847 5610 tên LE THANH DUC không? Anh sẽ chuyển lại cho em ngay chiều nay kèm thêm 100k cảm ơn em nha.

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [acc chính bị khóa, cần gấp 2 triệu để thanh toán hóa đơn điện trước 11h59 hôm nay, Internet Banking anh đang bị lỗi xác thực OTP, STK 1903 2847 5610 tên LE THANH DUC, chuyển lại cho em ngay chiều nay kèm thêm 100k]
- **Judge scores:** realism=3, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Hóa đơn bị cắt lúc 11h59 hơi dựng; không có nhiệm vụ.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 248/324 -- split=train row_index=1867 seed_id=seed_157ce0adb043

> Tuấn đây mày! Tao đang ở nước ngoài, SIM ko dùng dc. Mày bank giúp tao 8 triệu gấp nha, tao cần đặt cọc khách sạn. Chuyển vào: Vietinbank - 0398765432 - Lê Minh Tuấn. Mày chuyển xong gửi bill qua đây cho tao. Ko có OTP hay gì đâu mày cứ chuyển thẳng nha. Tao cảm ơn mày nhiều lắm!!!

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [SIM ko dùng dc, bank giúp tao 8 triệu gấp, Ko có OTP hay gì đâu mày cứ chuyển thẳng, đang ở nước ngoài, gửi bill qua đây]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Bạn ở nước ngoài xin cọc khách sạn thuộc social engineering.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 249/324 -- split=train row_index=1868 seed_id=seed_157ce0adb043

> Bro! Tao đây, Tuấn nè. SĐT cũ die r đang dùng tạm số này. Mày đang rảnh ko? Tao nhờ mày 1 việc gấp: chuyển hộ tao 2tr vào acc này nha — NH TPBank STK 19038821764 tên PHAM ANH TUAN. Tao đang ở nước ngoài, internet banking tao ko login dc do lỗi OTP, mà cần thanh toán deadline hôm nay. Mày chuyển xong tao Paypal lại liền hoặc tao đưa mặt khi về. Gấp lắm bro 🙏

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [SĐT cũ die r đang dùng tạm số này, internet banking tao ko login dc do lỗi OTP, cần thanh toán deadline hôm nay, STK 19038821764, tao Paypal lại liền, Gấp lắm bro]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Số mới xin thanh toán hộ là mạo danh xã hội, không task.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 250/324 -- split=train row_index=1869 seed_id=seed_157ce0adb043

> Chị Lan ơi, em là Minh con chị Hoa đây ạ. Em đang ở bệnh viện cấp cứu, điện thoại hết pin phải mượn máy người ta nhắn. Ba em nhập viện đột ngột cần đóng viện phí gấp 8.000.000đ trước 17h hôm nay không bác sĩ ko mổ. Chị chuyển giúp em vào tk MB Bank 0347 2291 8834 chủ tk PHAM QUOC MINH với ạ. Em sẽ báo lại mẹ em hoàn tiền chị ngay ạ. Em cảm ơn chị rất nhiều!!

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [đang ở bệnh viện cấp cứu, điện thoại hết pin phải mượn máy người ta, cần đóng viện phí gấp 8.000.000đ trước 17h hôm nay, không bác sĩ ko mổ, tk MB Bank 0347 2291 8834]
- **Judge scores:** realism=3, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Đe không mổ hơi lố; giả con hàng xóm không phải task.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 251/324 -- split=train row_index=1870 seed_id=seed_157ce0adb043

> Anh Long ơi, em là Kiên phòng kỹ thuật. Em cần anh xác nhận login vào hệ thống gấp để em reset lại quyền truy cập. Anh vào link này: <http://portal-noidbo-vietcombank.net/login> rồi nhập Smart OTP để em cấp lại quyền cho anh nha. Việc gấp lắm anh ơi.

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [http://portal-noidbo-vietcombank.net/login, nhập Smart OTP, reset lại quyền truy cập, Việc gấp lắm]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Đây là phishing cổng nội bộ xin Smart OTP, gần bank impersonation hơn task.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 252/324 -- split=train row_index=1871 seed_id=seed_157ce0adb043

> Bro!! Tài khoản zalo tao bị hack xong r, bọn nó đang nhắn lung tung. Tao lập acc mới đây. Bro đang rảnh ko, tao nhờ chút việc dc ko? Tao đang order hàng online gấp mà thẻ tao bị decline r, mày thanh toán hộ tao 2tr8 trước đi rồi tao chuyển khoản lại liền. Link order đây: shope-vn-flash.net/order/GH9921 mày vào xem thử. Chuyển vào Momo sdt 0387xx4521 tên Trần Bảo Long nha bro 🤙

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [Tài khoản zalo tao bị hack xong r, Tao lập acc mới đây, thẻ tao bị decline r, shope-vn-flash.net/order/GH9921, Chuyển vào Momo sdt 0387xx4521, mày thanh toán hộ tao 2tr8 trước]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Acc mới dẫn link Shopee giả và MoMo là social phishing, không task.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 253/324 -- split=train row_index=1872 seed_id=seed_157ce0adb043

> Chị Hương ơi, em là Tú bạn thân chị hồi đại học í. Em đang làm thủ tục vay ngân hàng cần có sao kê 3 tháng gần nhất trong tk có ít nhất 50tr. Chị cho em mượn tk 1 tuần thôi để em chạy sao kê dc k ạ? Chị vẫn giữ toàn bộ thông tin đăng nhập, em k đụng vào đâu ạ, e thề 🙏

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [cho em mượn tk 1 tuần, chạy sao kê, Chị vẫn giữ toàn bộ thông tin đăng nhập, em k đụng vào đâu ạ]
- **Judge scores:** realism=2, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=4
- **Judge's stated reason:** Mượn tài khoản nhưng không đụng đăng nhập không giải quyết sao kê; nhãn task yếu.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 254/324 -- split=train row_index=1873 seed_id=seed_157ce0adb043

> Ông Bình ơi! Con Ngọc đây ba ơi. Con đang ở bệnh viện, điện thoại con bị rớt xuống nước hỏng r nên nhắn từ máy bạn. Con cần 2tr500 để đặt cọc phòng trọ mới gấp, chủ nhà bắt đặt cọc trước 5h chiều nay. Ba chuyển vào số này giúp con nha: Agribank 3600205917834 - PHAM THI NGOC. Con sẽ về nhà tối giải thích hết. Cảm ơn ba!

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [điện thoại con bị rớt xuống nước hỏng r nên nhắn từ máy bạn, đặt cọc trước 5h chiều nay, Ba chuyển vào số này giúp con nha, Con sẽ về nhà tối giải thích hết]
- **Judge scores:** realism=3, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=4
- **Judge's stated reason:** Ở bệnh viện nhưng xin cọc trọ hơi rời rạc; đây là mạo danh con.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 255/324 -- split=train row_index=1874 seed_id=seed_157ce0adb043

> Anh Phong ơi! Em Dũng đây anh, em đang cần gấp anh ơi. Con em bị sốt cao co giật vừa vào cấp cứu Nhi Đồng 1. Vợ em ko mang theo đủ tiền, em đang trên đường chạy xuống. Anh có thể chuyển trước cho em 3tr5 để vợ em đóng tạm ko anh? Anh chuyển vào VPBank app: STK 214xxxxxxxx - Lê Văn Dũng. Em gọi lại cho anh ngay khi tới bệnh viện, em xin lỗi anh vì phải nhờ gấp như vậy 🙏🙏

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [Con em bị sốt cao co giật, vừa vào cấp cứu, Vợ em ko mang theo đủ tiền, chuyển trước cho em 3tr5, đóng tạm, 214xxxxxxxx, Em gọi lại cho anh ngay khi tới bệnh viện]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=5, risk_tier_correctness=5, suspicious_span_accuracy=3
- **Judge's stated reason:** Lời nhờ viện phí có thể thật, nhưng chắc chắn không phải task scam.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 256/324 -- split=train row_index=1875 seed_id=seed_157ce0adb043

> Con ơi đây ba nè. Ba đang ở bệnh viện, điện thoại ba hết pin nhờ người ta nhắn giúp. Ba cần chuyển gấp 8,500,000đ để đặt cọc phòng mổ trước 3h. Con login Internet Banking chuyển vào STK 9988776655 NH Techcombank - Lê Quốc Ba nha con. Xong rồi nhắn lại số này cho ba biết. Đừng lo, ba khoẻ, chỉ cần tiền gấp thôi. Ba thương con.

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [điện thoại ba hết pin nhờ người ta nhắn giúp, cần chuyển gấp 8,500,000đ để đặt cọc phòng mổ, login Internet Banking chuyển vào STK 9988776655, Đừng lo, ba khoẻ, chỉ cần tiền gấp thôi, trước 3h]
- **Judge scores:** realism=2, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Ba nói đang khỏe nhưng cần cọc phòng mổ tạo mâu thuẫn lớn; nhãn task sai.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 257/324 -- split=train row_index=1876 seed_id=seed_157ce0adb043

> Chị ơi em là Lan em gái chị đây ạ. Em đang ở bệnh viện với mẹ, mẹ cần phẫu thuật gấp mà em ko mang đủ tiền. Chị chuyển giúp em 10 triệu vào tài khoản Internet Banking này trước đi ạ: MB Bank - 0123 4567 8910 - Tran Thi Lan. Điện thoại em hết pin nên nhắn zalo mượn máy người ta, chị đừng gọi lại số này ạ. Em cảm ơn chị nhiều lắm ạ 🙏

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [mẹ cần phẫu thuật gấp, em ko mang đủ tiền, Chị chuyển giúp em 10 triệu, MB Bank - 0123 4567 8910, Điện thoại em hết pin nên nhắn zalo mượn máy người ta, chị đừng gọi lại số này ạ]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Giả em gái mượn máy xin tiền mổ là social engineering.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 258/324 -- split=train row_index=1877 seed_id=seed_157ce0adb043

> Ngọc ơi mình là Mai nè! Lâu quá ko gặp 😊 Mình đang có việc cần nhờ bạn gấp. Mình vừa đặt mua hàng online nhưng link thanh toán báo lỗi thẻ mình. Bạn có thể thanh toán hộ mình 1.800.000đ qua VNPay hoặc chuyển khoản vào Agribank STK 6200382917 - Trần Thị Mai ko? Đơn hàng sắp hết giờ giữ rồi, còn 15 phút thôi. Mình Momo lại cho bạn ngay liền nha, thêm 50k phí nhờ vả 😄

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [link thanh toán báo lỗi thẻ mình, Đơn hàng sắp hết giờ giữ rồi, còn 15 phút thôi, thanh toán hộ mình 1.800.000đ, thêm 50k phí nhờ vả]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=2, suspicious_span_accuracy=4
- **Judge's stated reason:** Nhờ thanh toán đơn hàng là social engineering; chuyển tiền trực tiếp bị đánh tier thấp.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 259/324 -- split=train row_index=1878 seed_id=seed_157ce0adb043

> Alo [TEN], mình là Hương nè, điện thoại mình vừa bị mất nên đang dùng số mới này. Mình đang cần gấp 3 triệu để đóng tiền học cho con, chuyển giúp mình vào STK 9021 8374 5561 Ngân hàng Vietcombank tên Nguyen Thi Huong nha. Mình sẽ trả lại ngay chiều nay, cảm ơn bạn nhiều lắm!

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [điện thoại mình vừa bị mất nên đang dùng số mới này, đang cần gấp 3 triệu, chuyển giúp mình vào STK 9021 8374 5561, Mình sẽ trả lại ngay chiều nay]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Số mới xin học phí là mạo danh xã hội, không task.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 260/324 -- split=train row_index=1879 seed_id=seed_157ce0adb043

> Bro! Mình Khoa đây. Số mới nha, số cũ mất r. Đang cần gấp 1tr5 để thanh toán đơn hàng online, app ngân hàng mình đang lỗi ko login dc. Mày chuyển hộ mình trước đi, tối mình Momo lại liền. ACB - 9988776655 - Lê Quốc Khoa. Gấp lắm bro 🙏🙏

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [Số mới nha, số cũ mất r, app ngân hàng mình đang lỗi ko login dc, chuyển hộ mình trước đi, tối mình Momo lại liền, Gấp lắm bro]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Bạn số mới xin thanh toán đơn hàng không thuộc task scam.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 261/324 -- split=train row_index=1880 seed_id=seed_157ce0adb043

> Alo [TÊN], mình là Hương đây! Mình vừa bị mất đt, đang dùng máy mượn. Mày có thể chuyển cho mình 2 triệu k? Mình cần gấp để đóng tiền nhà hôm nay, mai mình trả lại ngay. Chuyển vào STK 9034 8821 7765 Ngân hàng VCB tên NGUYEN THI HUONG nha. Cảm ơn mày nhiều lắm!

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [vừa bị mất đt, đang dùng máy mượn, chuyển cho mình 2 triệu k, cần gấp để đóng tiền nhà hôm nay, STK 9034 8821 7765]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Giả người quen mất điện thoại vay tiền nhà là social engineering.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 262/324 -- split=train row_index=1881 seed_id=seed_157ce0adb043

> Chị ơi! Em là Linh đây ạ, em lỡ bị hack Facebook nên nhắn qua Zalo số mới này. Chị đang rảnh k ạ? Em đang cần gấp 5 triệu để thanh toán đơn hàng online, app ngân hàng em đang lỗi ko chuyển dc. Nhờ chị chuyển hộ em vào STK Techcombank 19038xxxxxxx tên TRAN THI LINH trước 15h hôm nay nha chị, quá giờ họ hủy đơn mất ạ 😢 Em sẽ chuyển lại qua Internet Banking ngay tối nay ạ. Chị thương em với ạ!

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [bị hack Facebook nên nhắn qua Zalo số mới này, app ngân hàng em đang lỗi ko chuyển dc, chuyển hộ em vào STK Techcombank 19038xxxxxxx, trước 15h hôm nay nha chị, quá giờ họ hủy đơn mất, Em sẽ chuyển lại qua Internet Banking ngay tối nay]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Zalo số mới xin tiền đơn hàng là mạo danh xã hội.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 263/324 -- split=train row_index=1882 seed_id=seed_157ce0adb043

> Bro ơi tao là Minh nè! Account Facebook tao bị hack mất r, đang dùng tạm acc phụ nhắn. Tao đang kẹt tiền gấp, app MoMo tao cũng ko login dc vì đổi SĐT chưa xong. Mày chuyển banking giúp tao 5tr vào số 19036789012 Techcombank - TRAN VAN MINH đc ko? Tao Momo lại cho mày ngay khi fix xong account, chắc tối nay xong. Gấp lắm bro, deadline dự án mai rồi 🙏🙏

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [Account Facebook tao bị hack mất r, đang dùng tạm acc phụ, app MoMo tao cũng ko login dc, chuyển banking giúp tao 5tr, 19036789012 Techcombank, Tao Momo lại cho mày ngay, deadline dự án mai rồi]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Acc phụ xin ngân hàng giúp thuộc social engineering, không nhiệm vụ.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 264/324 -- split=train row_index=1883 seed_id=seed_157ce0adb043

> Chị ơi em là Lan - con gái chị Hoa hàng xóm đó ạ. Em đang ở bệnh viện với mẹ em, mẹ em nhập viện gấp tối qua. Chị có thể chuyển tạm cho em 5 triệu để đóng viện phí trước k ạ? Account của em: MB Bank - 038xxxxxxx - Trần Thị Lan. Em sẽ hoàn lại chị ngay khi chú em lên tới nơi ạ. Em cảm ơn chị rất nhiều ạ 🙏

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [mẹ em nhập viện gấp tối qua, chuyển tạm cho em 5 triệu, đóng viện phí trước, Em sẽ hoàn lại chị ngay, 038xxxxxxx]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=3
- **Judge's stated reason:** Lời xin viện phí có thể thật nhưng nhãn task sai và cue còn mơ hồ.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 265/324 -- split=train row_index=1884 seed_id=seed_157ce0adb043

> Alo [TÊN], mình là Hương đây! Điện thoại mình vừa bị mất hồi sáng, đang dùng số mới tạm thời. Mình đang kẹt tiền gấp, cần chuyển cho mình 3 triệu qua STK 9021 4857 3301 Vietcombank tên NGUYEN THI HUONG dc ko? Chiều mình trả liền, mình hứa nha. Đừng nhắn vào số cũ vì mất rồi.

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [Điện thoại mình vừa bị mất hồi sáng, đang dùng số mới tạm thời, cần chuyển cho mình 3 triệu, STK 9021 4857 3301 Vietcombank, Chiều mình trả liền, Đừng nhắn vào số cũ vì mất rồi]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Số mới vay ba triệu là mạo danh xã hội.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 266/324 -- split=train row_index=1885 seed_id=seed_157ce0adb043

> Lan ơi mình Phương đây nè! Mình đang dùng zalo mới vì tài khoản cũ bị khóa do đăng nhập nhầm máy. Lan ơi mình đang cần gấp tiền để thanh toán đơn hàng online, bên shop họ chỉ chờ thêm 30 phút thôi không là họ hủy đơn. Mình chuyển khoản qua Internet Banking bị lỗi hoài, Lan có thể chuyển hộ mình 4.500.000đ vào STK Techcombank 19038472610 - LE THI PHUONG trước không? Mình sẽ chuyển lại Lan qua app ngay sau khi xong. Lan giúp mình với nha, mình đang hoảng lắm 😢

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [tài khoản cũ bị khóa do đăng nhập nhầm máy, chỉ chờ thêm 30 phút thôi không là họ hủy đơn, chuyển khoản qua Internet Banking bị lỗi hoài, STK Techcombank 19038472610, Mình sẽ chuyển lại Lan qua app ngay sau khi xong, mình đang hoảng lắm]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Zalo mới xin thanh toán đơn hàng không có cơ chế task.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 267/324 -- split=train row_index=1886 seed_id=seed_157ce0adb043

> Bro! Tao đây, Hùng nè. Tao đang ở nước ngoài công tác, roaming data chậm lắm nên chỉ nhắn tin dc thôi. Tao lỡ quên ko mang đủ tiền mặt, cần chuyển gấp 8 củ (8.000.000đ) để đặt cọc khách sạn tối nay không mày ơi. Mày chuyển vào acc này giúp tao: NH Techcombank - 1409xxxx8821 - CHU VAN HUNG. Tao sẽ hoàn lại qua app ngân hàng ngay khi về. Đừng gọi tao vì tao đang họp, nhắn tin thôi nha bro. Gấp lắm!!

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [đang ở nước ngoài công tác, roaming data chậm lắm nên chỉ nhắn tin dc thôi, Đừng gọi tao vì tao đang họp, chuyển gấp 8 củ, NH Techcombank - 1409xxxx8821, hoàn lại qua app ngân hàng ngay khi về]
- **Judge scores:** realism=3, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Lý do chỉ nhắn vì data chậm nhưng đang họp hơi ghép; nhãn task sai.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 268/324 -- split=train row_index=1887 seed_id=seed_157ce0adb043

> Alo [Minh] ơi, đây là tao [Nam] nè. Tao vừa mất đt, đang mượn máy bạn nhắn tin. Tài khoản bank của tao bị lỗi ko rút đc tiền, mày chuyển giúp tao 3 triệu đc ko? Tao trả lại sau 2 ngày nha. Chuyển vào STK: 19021983746251 Vietcombank tên NGUYEN THANH NAM. Gấp lắm mày ơi, tao đang cần tiền đóng viện phí cho mẹ.

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [đây là tao [Nam] nè, vừa mất đt, đang mượn máy bạn, Tài khoản bank của tao bị lỗi ko rút đc tiền, chuyển giúp tao 3 triệu đc ko, tao đang cần tiền đóng viện phí cho mẹ]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Giả bạn mất máy xin viện phí thuộc social engineering.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 269/324 -- split=train row_index=1888 seed_id=seed_157ce0adb043

> Alo [Minh] ơi, đây là tài khoản mới của tao, điện thoại cũ bị mất r nên đổi số. Mày có thể chuyển giúp tao 3 triệu ko? Tao đang kẹt tiền gấp lắm, mai tao trả liền nha. STK: 0394827165 - Ngân hàng Vietcombank - Nguyễn Hữu Phát. Tao cần trước 8h tối nay ak 🙏

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [đây là tài khoản mới của tao, điện thoại cũ bị mất r nên đổi số, chuyển giúp tao 3 triệu ko, Tao đang kẹt tiền gấp lắm, mai tao trả liền nha, Tao cần trước 8h tối nay]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Tài khoản mới vay tiền trước hạn không phải task scam.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 270/324 -- split=train row_index=1889 seed_id=seed_157ce0adb043

> bro ơi tao là Minh đây, acc fb tao bị hack r nên nhắn zalo này. mày đang rảnh ko? tao cần mượn gấp 5tr, đang kẹt tiền quá. chuyển MoMo số 0387654219 tên Tran Van Minh giúp tao dc ko, tao Momo lại ngay. ko có thì bank cũng dc nha bro 🙏

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [acc fb tao bị hack r, mượn gấp 5tr, chuyển MoMo số 0387654219, tao Momo lại ngay, ko có thì bank cũng dc]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Facebook hack xin MoMo là mạo danh xã hội, không task.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 271/324 -- split=train row_index=1890 seed_id=seed_157ce0adb043

> Bro ơi tao Quân đây! Tài khoản FB tao bị khóa r nên nhắn qua đây. Mày đang rảnh ko? Tao cần mày giúp gấp 1 việc. Tao đang ở nước ngoài, thẻ bị block ko rút dc tiền, cần chuyển gấp 8 củ để đặt cọc khách sạn kẻo mất phòng. Mày chuyển vào acc này giúp tao: MB Bank - 0987654321 - TRAN MINH QUAN. Tao sẽ chuyển lại qua PayPal hoặc banking ngay khi về. Ko cần OTP hay gì đâu, chuyển thẳng vào STK là dc. Tao đang gấp lắm bro 🙏

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [Tài khoản FB tao bị khóa r nên nhắn qua đây, Tao đang ở nước ngoài, thẻ bị block ko rút dc tiền, cần chuyển gấp 8 củ, MB Bank - 0987654321 - TRAN MINH QUAN, Ko cần OTP hay gì đâu, chuyển lại qua PayPal hoặc banking ngay khi về]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Bạn ở nước ngoài xin tiền khách sạn thuộc social engineering.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 272/324 -- split=train row_index=1891 seed_id=seed_157ce0adb043

> Tuấn đây mày. Số mới nha, đt cũ bể màn rồi. Tao đang cần 2tr gấp để cọc chỗ trọ, mai hết hạn rồi. Mày bank Techcombank ko? Chuyển vào STK 1190284756 tên LE QUOC TUAN giúp tao. Ko thì chuyển qua link này cũng đc: <https://pay-vcb-fast.net/transfer?id=tuan99> — tao trả mày cuối tuần. Gọi số cũ ko bắt máy đc đâu mày ơi

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [Số mới nha, đt cũ bể màn rồi, cần 2tr gấp, mai hết hạn rồi, STK 1190284756, https://pay-vcb-fast.net/transfer?id=tuan99, Gọi số cũ ko bắt máy đc đâu]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Số mới xin cọc trọ kèm link giả không phải task scam.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 273/324 -- split=train row_index=1892 seed_id=seed_157ce0adb043

> Chị Lan ơi! Em Thảo đây ạ. Em đang ở nước ngoài, app ngân hàng bị lỗi ko login dc, Smart OTP cũng ko nhận đc. Chị có thể chuyển hộ em 8.500.000đ ko ạ? Gửi vào tk Techcombank: 19038271645 - LE THI THAO. Em sẽ gửi lại chị qua Western Union ngay khi về. Tình huống khẩn cấp lắm chị ơi, em cần trả tiền khách sạn không họ đuổi ra đường mất 😢

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [app ngân hàng bị lỗi ko login dc, Smart OTP cũng ko nhận đc, chuyển hộ em 8.500.000đ, Em sẽ gửi lại chị qua Western Union ngay khi về, Tình huống khẩn cấp lắm]
- **Judge scores:** realism=3, label_correctness=2, code_switch_naturalness=3, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Hoàn qua Western Union hơi gượng; đây là mạo danh người quen.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 274/324 -- split=train row_index=1893 seed_id=seed_157ce0adb043

> Tuấn đây mày ơi. SĐT cũ tao bị mất rồi đang dùng cái này. Mày đang rảnh ko? Tao cần nhờ mày 1 việc gấp. Sếp tao bảo chuyển tiền công tác phí qua Zalo Pay gấp mà tao đang bị lỗi app ko vào dc. Mày có thể chuyển hộ tao 8 triệu ko, tao sẽ chuyển lại mày ngay sau khi fix dc app. STK: 0387654321 MB Bank - Nguyễn Văn Tuấn. Ko mất nhiều time đâu mày 🙏

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [SĐT cũ tao bị mất rồi đang dùng cái này, đang bị lỗi app ko vào dc, chuyển hộ tao 8 triệu, tao sẽ chuyển lại mày ngay sau khi fix dc app]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Số mới xin ứng công tác phí là social engineering, không nhiệm vụ.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 275/324 -- split=train row_index=1894 seed_id=seed_157ce0adb043

> Tuấn ơi mk đây (Phương). Zalo mk bị lỗi đăng nhập dc nên nhắn qua số này. Mk đang ở nước ngoài, ví điện tử bị khóa do đăng nhập địa điểm lạ. Mk cần mày chuyển gấp 3.500.000đ vào tk này để mk mua vé máy bay về: MB Bank - 0369112233 - DO THI PHUONG. Mày chuyển xong chụp bill gửi mk nha, mk nhờ người nhà hoàn lại mày liền. Gấp lắm mày ơi 😭

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [Zalo mk bị lỗi đăng nhập dc, nhắn qua số này, đang ở nước ngoài, ví điện tử bị khóa, chuyển gấp 3.500.000đ, mua vé máy bay về, chụp bill gửi mk, nhờ người nhà hoàn lại mày liền]
- **Judge scores:** realism=3, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Câu Zalo bị lỗi đăng nhập được thiếu phủ định; bản chất vẫn mạo danh.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 276/324 -- split=train row_index=1895 seed_id=seed_157ce0adb043

> Hảo ơi tui Linh nè!! Tui đang kẹt ở BV Chợ Rẫy gấp lắm, mẹ tui nhập viện đột xuất tối qua. Tui ko mang theo ví, đt cũ hết pin chết rồi mượn máy y tá nhắn đây. Tui cần đóng viện phí 4.200.000đ trước 15h hôm nay không thì họ không cho mổ. Bạn chuyển giúp tui vào Vietinbank STK 108374920156 tên LÊ THỊ NGỌC LINH nha. Tui về tui trả bạn liền, tui có thể chuyển khoản qua VNPay sau. Cảm ơn bạn nhiều lắm 😭😭 tui đang hoảng lắm

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [mẹ tui nhập viện đột xuất tối qua, đt cũ hết pin chết rồi mượn máy y tá nhắn đây, đóng viện phí 4.200.000đ trước 15h hôm nay, không thì họ không cho mổ, Vietinbank STK 108374920156, tui có thể chuyển khoản qua VNPay sau]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Mượn máy y tá xin viện phí là social engineering, không task.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 277/324 -- split=train row_index=1896 seed_id=seed_157ce0adb043

> Alo [Minh] ơi, đây là tao [Nam] nè. Tao vừa mất điện thoại nên đang dùng số mới này. Tao đang kẹt tiền gấp lắm, cần chuyển 3 triệu để đóng viện phí cho mẹ tao trước 5h chiều nay không là trễ rồi. Mày chuyển giúp tao vào STK 19038472910384 Vietcombank tên NGUYEN HOANG NAM dc ko? Tao về tao trả liền. Làm ơn nha mày, gấp lắm!!

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [vừa mất điện thoại nên đang dùng số mới này, kẹt tiền gấp lắm, đóng viện phí cho mẹ tao trước 5h chiều nay không là trễ rồi, chuyển giúp tao vào STK 19038472910384, Tao về tao trả liền]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Bạn số mới xin viện phí thuộc mạo danh xã hội.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 278/324 -- split=train row_index=1897 seed_id=seed_157ce0adb043

> Chị Hương ơi! Em là Linh – em gái chị đây ạ. Tài khoản Zalo của em bị hack mất rồi nên em lập acc mới nhắn chị. Chị ơi em đang ở bệnh viện với mẹ, mẹ cần phẫu thuật gấp mà em ko mang đủ tiền theo. Chị có thể chuyển tạm cho em 5.000.000đ không ạ? Em chuyển lại chị ngay khi về nhà. Chị chuyển vào Momo số 0387 654 219 tên PHAM THI LINH giúp em với ạ. Em cảm ơn chị nhiều lắm, tình huống khẩn cấp quá chị ơi 😭😭

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [Tài khoản Zalo của em bị hack mất rồi nên em lập acc mới, mẹ cần phẫu thuật gấp, chuyển tạm cho em 5.000.000đ, Chị chuyển vào Momo số 0387 654 219, tình huống khẩn cấp quá]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Zalo mới giả em gái xin tiền mổ không phải task.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 279/324 -- split=train row_index=1898 seed_id=seed_157ce0adb043

> Em ơi, chị Lan đây. Chị đang ở nước ngoài công tác, roaming mắc lắm nên nhắn Zalo nha. Chị lỡ quên ko mang đủ tiền, thẻ credit bị block do giao dịch ngoại tệ. Anh chị cần em chuyển gấp 8 triệu để đặt cọc khách sạn tối nay, mai về chị trả liền. STK: 0369112233 - MB Bank - LE THI LAN. Đừng gọi lại số cũ nha em vì roaming tốn tiền lắm, nhắn Zalo thôi. Chị cảm ơn em nhiều lắm, xong chuyến này chị thưởng em 🙏

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [Chị đang ở nước ngoài công tác, thẻ credit bị block do giao dịch ngoại tệ, chuyển gấp 8 triệu, đặt cọc khách sạn tối nay, STK: 0369112233 - MB Bank, Đừng gọi lại số cũ nha em vì roaming tốn tiền, nhắn Zalo thôi, xong chuyến này chị thưởng em]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=3
- **Judge's stated reason:** Lời nhờ từ nước ngoài có thể thật nhưng không liên quan nhiệm vụ.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 280/324 -- split=train row_index=1899 seed_id=seed_157ce0adb043

> Chị ơi, em là Linh - bạn thân chị đây ạ. Tài khoản Facebook cũ của em bị hack rồi nên em lập cái mới này. Chị ơi em đang cần gấp tiền đóng học phí hạn chót hôm nay 5h chiều, Internet Banking của em đang bị lỗi không login được. Chị có thể chuyển hộ em 5.500.000đ vào tài khoản Techcombank số 1903 8821 4476 tên ĐỖ THỊ HƯƠNG LINH không ạ? Em sẽ chuyển lại chị ngay tối nay sau khi app ngân hàng của em hoạt động lại. Em cảm ơn chị nhiều lắm ạ, chị cứu em với 🥺

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [Tài khoản Facebook cũ của em bị hack rồi nên em lập cái mới này, Internet Banking của em đang bị lỗi không login được, hạn chót hôm nay 5h chiều, chuyển hộ em 5.500.000đ, 1903 8821 4476, app ngân hàng của em hoạt động lại]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Facebook mới xin học phí là social engineering rõ.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 281/324 -- split=train row_index=1900 seed_id=seed_157ce0adb043

> Bro ơi tao là Hùng đây. SĐT mới của tao là số này nha, máy cũ rớt xuống nước hỏng r. Đang cần gấp 1tr5 để đặt cọc phòng trọ, chủ nhà họ chỉ chờ đến tối nay thôi. Mày chuyển qua Internet Banking giúp tao nha: Techcombank - 19034567891 - TRAN VAN HUNG. Tao sẽ hoàn lại mày sau khi lương về tuần sau. Cảm ơn mày nhiều lắm!!

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [SĐT mới của tao, máy cũ rớt xuống nước hỏng r, cần gấp 1tr5, chủ nhà họ chỉ chờ đến tối nay thôi, chuyển qua Internet Banking, hoàn lại mày sau khi lương về tuần sau]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Số mới vay cọc trọ không phải lừa làm nhiệm vụ.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 282/324 -- split=train row_index=1901 seed_id=seed_157ce0adb043

> Hà ơi mình Ngọc nè! Mình đang rất cần nhờ mày 1 việc gấp. Thẻ ATM của mình bị nuốt sáng nay, mà mình có khoản thanh toán online cần trả trước 20h tối nay không bị phạt hợp đồng. Mày có thể chuyển hộ mình 4.500.000 đ vào account Vietinbank này không: 108 876 543 21 - NGUYEN THI NGOC. Mình sẽ chuyển lại mày qua app VNPay ngay sau khi mình ra ngân hàng lấy thẻ mới nhé. Mày cứu mình phát này nha bạn ơi 🙏🙏

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [Thẻ ATM của mình bị nuốt sáng nay, khoản thanh toán online cần trả trước 20h tối nay, account Vietinbank này không: 108 876 543 21, chuyển lại mày qua app VNPay ngay sau khi mình ra ngân hàng lấy thẻ mới]
- **Judge scores:** realism=3, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Có thể dùng VNPay nhưng viện cớ mất thẻ hơi mâu thuẫn; nhãn task sai.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 283/324 -- split=train row_index=1902 seed_id=seed_157ce0adb043

> Bro ơi, tao là Hùng đây. Tao đang ở nước ngoài, app ngân hàng tao bị khóa account do đăng nhập sai OTP nhiều lần rồi. Mày giúp tao chuyển 5 triệu cho đối tác của tao trước đi, tao Paypal lại cho mày ngay. Chuyển vào STK 19036789012 Techcombank - PHAM QUOC HUNG. Tao đang họp ko nghe máy dc, nhắn tin thôi nha bro 🙏🙏

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [app ngân hàng tao bị khóa account do đăng nhập sai OTP nhiều lần, tao Paypal lại cho mày ngay, Tao đang họp ko nghe máy dc, chuyển 5 triệu cho đối tác của tao]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Giả bạn ở nước ngoài xin chuyển đối tác là social engineering.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 284/324 -- split=train row_index=1903 seed_id=seed_157ce0adb043

> Con ơi, mẹ đây. Mẹ đang dùng điện thoại mượn vì máy mẹ hỏng rồi. Con chuyển cho mẹ 4 triệu để mẹ sửa máy với mua thuốc nha con. Gửi vào Sacombank số 7788990011 tên Tran Thi Mai nha. Mẹ nhớ hoàn lại con sau.

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [đang dùng điện thoại mượn, máy mẹ hỏng rồi, chuyển cho mẹ 4 triệu, sửa máy với mua thuốc, Mẹ nhớ hoàn lại con sau]
- **Judge scores:** realism=2, label_correctness=2, code_switch_naturalness=5, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Câu mẹ nhớ hoàn lại con rất gượng; đây là mạo danh gia đình.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 285/324 -- split=train row_index=1904 seed_id=seed_157ce0adb043

> Tuấn đây mày ơi! Tao đang ở nước ngoài, tài khoản VCB của tao bị khóa do đăng nhập ở nước ngoài, app Internet Banking ko vào dc. Tao cần mày chuyển gấp 8 triệu để tao book vé về, tao mắc kẹt ở đây rồi. Tao sẽ chuyển lại qua Smart OTP ngay khi về VN. Chuyển vào MB Bank 0387264910 tên DO THANH TUAN nha. Tao đang rất cần, mày giúp tao với!!!

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [tài khoản VCB của tao bị khóa, app Internet Banking ko vào dc, mắc kẹt ở đây rồi, chuyển gấp 8 triệu, chuyển lại qua Smart OTP ngay khi về VN, MB Bank 0387264910]
- **Judge scores:** realism=3, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Chuyển lại qua Smart OTP không tự nhiên; không có task.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 286/324 -- split=train row_index=1905 seed_id=seed_157ce0adb043

> Con ơi đây là má, má đang dùng zalo của dì Hai vì điện thoại má hết pin, sạc bị hỏng. Con chuyển cho má 3 triệu qua Internet Banking gấp nha, má đang ở bệnh viện cần đóng viện phí. Tài khoản: Techcombank - 1122334455 - Phạm Thị Ngọc. Má cần gấp lắm con ơi, đừng gọi lại số này vì dì Hai bận.

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [đang dùng zalo của dì Hai vì điện thoại má hết pin, đang ở bệnh viện cần đóng viện phí, chuyển cho má 3 triệu qua Internet Banking gấp, đừng gọi lại số này vì dì Hai bận]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Giả mẹ dùng Zalo người khác xin viện phí là social engineering.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 287/324 -- split=train row_index=1906 seed_id=seed_157ce0adb043

> Bro ơi! Tao đây - [Nam]. Acc Facebook tao bị hack hết rồi bro, tụi nó đổi cả SĐT lẫn email nên tao ko login dc nữa. Giờ tao nhắn qua Zalo số này tạm. Bro đang rảnh ko? Tao cần nhờ bro 1 việc gấp: giúp tao mua giúp 2 thẻ Viettel 100k gửi code thẻ qua đây cho tao nha. Tao đang cần nạp tiền vào game để thanh toán 1 khoản, ví điện tử tao đang bị lỗi ko nạp dc. Tao trả mày sau, chắc chắn luôn 🤙

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [Acc Facebook tao bị hack hết rồi, ko login dc nữa, Giờ tao nhắn qua Zalo số này tạm, mua giúp 2 thẻ Viettel 100k gửi code thẻ qua đây, ví điện tử tao đang bị lỗi ko nạp dc, Tao trả mày sau, chắc chắn luôn]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=3, suspicious_span_accuracy=5
- **Judge's stated reason:** Xin mã thẻ nhỏ hợp tier suspicious nhưng là mạo danh, không task.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 288/324 -- split=train row_index=1907 seed_id=seed_157ce0adb043

> Chị Lan ơi em là Phương đây ạ. Em lỡ chuyển nhầm 2.500.000đ vào tài khoản chị rồi ạ 😢 Chị kiểm tra Internet Banking giúp em xem có nhận dc ko ạ. Nếu có thì chị chuyển lại giúp em vào STK Techcombank 19038274651 - Lê Thị Phương nhé ạ. Em cần gấp để thanh toán đơn hàng. Cảm ơn chị nhiều ạ!

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [lỡ chuyển nhầm 2.500.000đ vào tài khoản chị rồi, Chị kiểm tra Internet Banking giúp em, chuyển lại giúp em, Em cần gấp để thanh toán đơn hàng]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=4, suspicious_span_accuracy=3
- **Judge's stated reason:** Hoàn tiền nhầm có thể hợp lệ nếu tiền đến; chắc chắn không phải task.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 289/324 -- split=train row_index=1908 seed_id=seed_157ce0adb043

> Bro ơi tau [Khoa] đây. Tau đang ở nước ngoài, SIM ko dùng dc nên nhắn zalo này. Bro làm ơn chuyển giúp tau $200 (khoảng 5tr VND) vào acc này: MB Bank - 0346789012 - TRAN MINH KHOA. Tau đang bị kẹt ở sân bay, mất ví, cần tiền mua vé về gấp. Tau về tau thanh toán lại qua banking liền. Bro save contact này nha, số cũ tau mất r.

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [đang ở nước ngoài, SIM ko dùng dc, bị kẹt ở sân bay, mất ví, cần tiền mua vé về gấp, save contact này nha, số cũ tau mất r]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Giả bạn ở sân bay dùng số mới không thuộc task scam.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 290/324 -- split=train row_index=1910 seed_id=seed_157ce0adb043

> Chị ơi em đây, em đang dùng acc zalo mượn của bạn vì điện thoại em đang sửa. Chị có thể chuyển giúp em 5tr ko ạ? Em cần đặt cọc hàng gấp chiều nay không là mất đơn. Chị chuyển vào Momo số 0769988123 tên Tran Thi Lan giúp em nha chị. Em sẽ chuyển khoản Internet Banking hoàn lại cho chị ngay tối nay ạ. Em cảm ơn chị nhiều lắm ạ 🙏

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [acc zalo mượn của bạn vì điện thoại em đang sửa, chuyển giúp em 5tr, chiều nay không là mất đơn, Momo số 0769988123, hoàn lại cho chị ngay tối nay]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Mượn acc Zalo xin tiền cọc hàng là social engineering.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 291/324 -- split=train row_index=1911 seed_id=seed_157ce0adb043

> Alo [Minh] ơi, tao là Hùng đây. Tao vừa làm mất đt, đang mượn máy bạn nhắn tin. Mày có thể chuyển giúp tao 2 triệu k? Tao đang kẹt tiền gấp lắm, mai tao trả lại liền. STK: 0123456789 - Ngân hàng Vietcombank - Nguyễn Văn Hùng. Tao hứa trả sớm nha mày ơi 🙏

- **Current label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [Tao vừa làm mất đt, đang mượn máy bạn nhắn tin, chuyển giúp tao 2 triệu k, đang kẹt tiền gấp lắm, mai tao trả lại liền, STK: 0123456789]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge's stated reason:** Bạn mất điện thoại vay tiền trực tiếp không phải task.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 292/324 -- split=val row_index=75 seed_id=seed_135fb131140f

> Chào bạn, do có sự cố với tài khoản Internet Banking của bạn, vui lòng đăng nhập vào [fakeurl.com] để xác nhận thông tin. Nếu không, giao dịch của bạn sẽ bị chặn. ĐT: 0987654321

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [[fakeurl.com], 0987654321]
- **Judge scores:** realism=2, label_correctness=1, code_switch_naturalness=4, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge's stated reason:** Placeholder makes this synthetic; bank phishing is mislabeled task scam and warrants high-risk.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 293/324 -- split=val row_index=81 seed_id=seed_c3c238c360c8

> Chào bạn, tôi là điều tra viên Nguyễn Văn A từ CAFC. Chúng tôi có thể giúp bạn lấy lại số tiền đã mất do lừa đảo. Hãy cung cấp OTP và thông tin Internet Banking của bạn để chúng tôi xác minh. Liên hệ 0987654321 hoặc truy cập [http://cafc-support.vn] nhanh để được hỗ trợ, nha! 🙏

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [OTP, 0987654321, http://cafc-support.vn]
- **Judge scores:** realism=2, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge's stated reason:** Placeholder makes this synthetic; recovery phishing is mislabeled task scam and warrants high-risk.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 294/324 -- split=val row_index=82 seed_id=seed_cd2758fc96b9

> Chào bạn, đây là Ngân hàng ACB. Chúng tôi cần xác nhận lại thông tin tài khoản của bạn do có giao dịch đáng ngờ. Vui lòng đăng nhập vào [fakeurl.com] để xác minh. Nếu không, tài khoản của bạn sẽ bị khóa ngay lập tức. Cảm ơn!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [[fakeurl.com]]
- **Judge scores:** realism=2, label_correctness=1, code_switch_naturalness=4, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge's stated reason:** Placeholder makes this synthetic; bank phishing is mislabeled task scam and warrants high-risk.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 295/324 -- split=val row_index=84 seed_id=seed_135fb131140f

> Xin chào, chúng tôi nhận thấy có hoạt động đáng ngờ trên tài khoản Smart OTP của bạn. Hãy liên hệ ngay với chúng tôi qua số 0909888777 để xác minh. Đừng bỏ lỡ!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [0909888777]
- **Judge scores:** realism=4, label_correctness=1, code_switch_naturalness=4, risk_tier_correctness=4, suspicious_span_accuracy=2
- **Judge's stated reason:** Bank alert is mislabeled task scam; contact-only span omits the decisive unsafe request.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 296/324 -- split=val row_index=90 seed_id=seed_c3c238c360c8

> Xin chào, tôi là Hoàng từ đội điều tra CAFC. Chúng tôi đang hỗ trợ nạn nhân lừa đảo lấy lại tiền. Bạn cần cung cấp thông tin Smart OTP và tài khoản Internet Banking. Hãy liên hệ 0345678910 hoặc truy cập [https://cafc-vn.com] ngay để được hỗ trợ, ak!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [Smart OTP, 0345678910, https://cafc-vn.com]
- **Judge scores:** realism=2, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge's stated reason:** Placeholder makes this synthetic; phishing is mislabeled task scam and warrants high-risk.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 297/324 -- split=val row_index=91 seed_id=seed_cd2758fc96b9

> Xin chào, đây là dịch vụ chăm sóc khách hàng của Techcombank. Bạn vừa nhận được một mã OTP: 123456. Vui lòng nhập mã này vào ứng dụng Internet Banking để hoàn tất giao dịch. Nếu bạn chưa yêu cầu, vui lòng gọi 0987654321 để xác minh.

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [0987654321]
- **Judge scores:** realism=5, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=2, suspicious_span_accuracy=2
- **Judge's stated reason:** Routine OTP is benign, not task scam; suspicious tier and contact-only span are wrong.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 298/324 -- split=val row_index=93 seed_id=seed_135fb131140f

> Chào bạn, bạn vừa nhận được một OTP để xác nhận giao dịch. Vui lòng nhập mã OTP: 123456 tại [linkscam.vn] để hoàn tất. Hạn chót: 15 phút. ĐT: 0912345678

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [123456, [linkscam.vn], 0912345678]
- **Judge scores:** realism=2, label_correctness=1, code_switch_naturalness=4, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge's stated reason:** Placeholder makes this synthetic; phishing is mislabeled task scam and warrants high-risk.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 299/324 -- split=val row_index=99 seed_id=seed_c3c238c360c8

> Đây là Trang từ CAFC, chúng tôi có thể giúp bạn lấy lại số tiền đã mất. Hãy cung cấp mã OTP và đăng nhập Internet Banking của bạn. Gọi 0976543210 hoặc truy cập [https://cafc-help.vn] để được hỗ trợ, nha. Cảm ơn bạn!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [OTP, 0976543210, https://cafc-help.vn]
- **Judge scores:** realism=2, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge's stated reason:** Placeholder makes this synthetic; phishing is mislabeled task scam and warrants high-risk.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 300/324 -- split=val row_index=100 seed_id=seed_cd2758fc96b9

> Kính gửi quý khách, chúng tôi phát hiện có hoạt động khả nghi trên tài khoản của bạn. Vui lòng cập nhật thông tin bảo mật tại đây [phishing-site.vn] để tránh bị khóa tài khoản. Đừng bỏ qua, nha!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [[phishing-site.vn]]
- **Judge scores:** realism=2, label_correctness=1, code_switch_naturalness=4, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge's stated reason:** Placeholder makes this synthetic; phishing is mislabeled task scam and warrants high-risk.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 301/324 -- split=val row_index=102 seed_id=seed_135fb131140f

> Chào anh/chị, có sự cố về thuế thu nhập cá nhân, vui lòng cập nhật thông tin tại [taxscam.com] để tránh phạt. Hotline: 0934567890

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [[taxscam.com], 0934567890]
- **Judge scores:** realism=2, label_correctness=1, code_switch_naturalness=4, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge's stated reason:** Placeholder makes this synthetic; phishing is mislabeled task scam and warrants high-risk.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 302/324 -- split=val row_index=108 seed_id=seed_c3c238c360c8

> Chào bạn, mình là điều tra viên của CAFC. Chúng tôi đang điều tra vụ lừa đảo mà bạn đã tố cáo. Để giúp chúng tôi phục hồi số tiền đã mất, vui lòng cung cấp OTP từ ứng dụng Internet Banking của bạn. Liên hệ qua số điện thoại 0987654321 để xác minh thêm thông tin. Cảm ơn sự hợp tác của bạn!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [OTP, 0987654321]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge's stated reason:** Giả điều tra viên xin OTP phục hồi tiền thuộc recovery scam high-risk.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 303/324 -- split=val row_index=109 seed_id=seed_cd2758fc96b9

> Chào bạn, đây là Vietcombank. Chúng tôi cần xác minh lại thông tin tài khoản của bạn. Vui lòng cung cấp tên, số CMND, và mật khẩu Internet Banking của bạn qua số điện thoại 0123456789. Nếu không, tài khoản của bạn sẽ bị khóa. Cảm ơn sự hợp tác của bạn!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [0123456789]
- **Judge scores:** realism=2, label_correctness=1, code_switch_naturalness=4, risk_tier_correctness=2, suspicious_span_accuracy=2
- **Judge's stated reason:** Placeholder makes this synthetic; phishing is mislabeled task scam, high-risk, and poorly spanned.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 304/324 -- split=val row_index=111 seed_id=seed_135fb131140f

> Chào bạn, tài khoản của bạn cần xác minh lại do có dấu hiệu lừa đảo. Vui lòng liên hệ 0976543210 hoặc truy cập [verifyaccount.vn] để xác nhận. Đừng bỏ qua!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [0976543210, [verifyaccount.vn]]
- **Judge scores:** realism=2, label_correctness=1, code_switch_naturalness=4, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge's stated reason:** Placeholder makes this synthetic; phishing is mislabeled task scam and warrants high-risk.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 305/324 -- split=val row_index=117 seed_id=seed_c3c238c360c8

> Xin chào, mình là điều tra viên từ CAFC. Chúng tôi đã phát hiện ra cách để lấy lại số tiền bạn đã mất. Vui lòng đăng nhập vào trang web [fakeurl.com] để xác nhận thông tin tài khoản của bạn. Nếu cần hỗ trợ, hãy gọi 0981234567. Cảm ơn sự hợp tác của bạn!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [[fakeurl.com], 0981234567]
- **Judge scores:** realism=2, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge's stated reason:** Placeholder makes this synthetic; phishing is mislabeled task scam and warrants high-risk.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 306/324 -- split=val row_index=118 seed_id=seed_cd2758fc96b9

> Xin chào, bạn vừa đăng ký thành công dịch vụ Smart OTP của BIDV. Để kích hoạt, vui lòng nhấn vào link sau [activation-link.com] và nhập mã xác nhận 678901. Nếu bạn chưa đăng ký, vui lòng liên hệ BIDV ngay lập tức. Cảm ơn!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [[activation-link.com], 678901]
- **Judge scores:** realism=2, label_correctness=1, code_switch_naturalness=4, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge's stated reason:** Placeholder makes this synthetic; phishing is mislabeled task scam and warrants high-risk.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 307/324 -- split=val row_index=121 seed_id=seed_c3c238c360c8

> Chào bạn, mình là điều tra viên từ CAFC. Chúng tôi đã tìm thấy cách để lấy lại số tiền đã mất của bạn. Vui lòng gửi mã Smart OTP từ ứng dụng Internet Banking đến số 0987654321 để chúng tôi xác minh. Cảm ơn sự hợp tác của bạn!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [Smart OTP, 0987654321]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge's stated reason:** Xin Smart OTP để lấy lại tiền là recovery scam high-risk.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 308/324 -- split=val row_index=124 seed_id=seed_c3c238c360c8

> Chào bạn, mình là điều tra viên từ CAFC. Chúng tôi đã tìm thấy cách để lấy lại số tiền đã mất của bạn. Vui lòng click vào link này [fakeurl.vn] để xác nhận thông tin tài khoản của bạn. Nếu cần hỗ trợ, hãy gọi 0981234567. Cảm ơn sự hợp tác của bạn!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [[fakeurl.vn], 0981234567]
- **Judge scores:** realism=2, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge's stated reason:** Placeholder makes this synthetic; phishing is mislabeled task scam and warrants high-risk.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 309/324 -- split=val row_index=127 seed_id=seed_c3c238c360c8

> Chào bạn, mình là điều tra viên từ CAFC. Chúng tôi đang cần xác minh thông tin tài khoản của bạn để lấy lại số tiền đã mất. Vui lòng cung cấp tên đăng nhập và mật khẩu của bạn qua số 0987654321. Cảm ơn sự hợp tác của bạn!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [tên đăng nhập và mật khẩu, 0987654321]
- **Judge scores:** realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge's stated reason:** Lấy đăng nhập dưới cớ phục hồi tiền là recovery scam nguy hiểm.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 310/324 -- split=test row_index=65 seed_id=seed_23882e611996

> Chào bạn, tôi là nhân viên của Ngân hàng XYZ. Theo quy định mới, bạn cần cập nhật thông tin sinh trắc học khuôn mặt trước ngày 15/06/2024 để tiếp tục sử dụng dịch vụ. Vui lòng click vào [link] để xác nhận. Nếu không, tài khoản của bạn sẽ bị khóa. ĐT: 0987654321

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [[link], 0987654321]
- **Judge scores:** realism=2, label_correctness=1, code_switch_naturalness=4, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge's stated reason:** Placeholder makes this synthetic; phishing is mislabeled task scam and warrants high-risk.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 311/324 -- split=test row_index=66 seed_id=seed_5efd416f05fd

> Chào bạn, đây là Ngân hàng Techcombank. Chúng tôi cần xác nhận lại thông tin tài khoản của bạn để đảm bảo an toàn. Vui lòng đăng nhập vào [http://techcombank-auth.com] và cập nhật thông tin. Nếu ko thực hiện, tài khoản của bạn sẽ bị khóa ngay lập tức. Cảm ơn sự hợp tác của bạn, nha!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [[http://techcombank-auth.com]]
- **Judge scores:** realism=2, label_correctness=1, code_switch_naturalness=4, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge's stated reason:** Placeholder makes this synthetic; phishing is mislabeled task scam and warrants high-risk.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 312/324 -- split=test row_index=69 seed_id=seed_d53ed10ecc4a

> Chào bạn, tài khoản Internet Banking của bạn đang gặp sự cố bảo mật. Vui lòng đăng nhập vào [https://fakebank.com.vn] để xác minh thông tin và đảm bảo an toàn. Cảm ơn bạn đã hợp tác, Đội Hỗ Trợ Khách Hàng.

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [[https://fakebank.com.vn]]
- **Judge scores:** realism=2, label_correctness=1, code_switch_naturalness=4, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge's stated reason:** Placeholder makes this synthetic; phishing is mislabeled task scam and warrants high-risk.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 313/324 -- split=test row_index=72 seed_id=seed_23882e611996

> Xin chào, tôi là Ms. Lan từ bộ phận chăm sóc khách hàng của Ngân hàng ABC. Để đảm bảo an toàn giao dịch, bạn cần xác nhận OTP qua SMS. Vui lòng nhập mã OTP vào đây [link] ngay lập tức. Nếu không, tài khoản của bạn có thể bị khóa. ĐT: 0912345678

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [[link], 0912345678]
- **Judge scores:** realism=2, label_correctness=1, code_switch_naturalness=4, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge's stated reason:** Placeholder makes this synthetic; phishing is mislabeled task scam and warrants high-risk.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 314/324 -- split=test row_index=73 seed_id=seed_5efd416f05fd

> Xin chào, tôi là nhân viên hỗ trợ từ Vietcombank. Có vẻ như có vấn đề với tài khoản Internet Banking của bạn. Để tránh mất quyền truy cập, vui lòng gọi ngay đến 0987654321 để xác minh. Đừng chần chừ, ak!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [0987654321]
- **Judge scores:** realism=4, label_correctness=1, code_switch_naturalness=4, risk_tier_correctness=4, suspicious_span_accuracy=2
- **Judge's stated reason:** Bank alert is mislabeled task scam; contact-only span omits the decisive unsafe request.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 315/324 -- split=test row_index=76 seed_id=seed_d53ed10ecc4a

> OTP cua bn la 123456, xin vui long nhap ma OTP nay de xac nhan giao dich. Neu ban khong co yeu cau nao, hay lien he 0987654321 de bao cao ngay luon nha. Cam on!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [0987654321, 123456]
- **Judge scores:** realism=4, label_correctness=1, code_switch_naturalness=4, risk_tier_correctness=2, suspicious_span_accuracy=2
- **Judge's stated reason:** Tin OTP an toàn không phải task và các span không phải cue scam.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 316/324 -- split=test row_index=79 seed_id=seed_23882e611996

> Kính gửi quý khách, theo quyết định mới của NHNN, bạn cần cập nhật thông tin sinh trắc học khuôn mặt trước 30/06/2024. Vui lòng tải app mới từ [link] để hoàn thành thủ tục. Nếu không, bạn sẽ không thể thực hiện giao dịch. ĐT: 0987654321

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [[link], 0987654321]
- **Judge scores:** realism=2, label_correctness=1, code_switch_naturalness=4, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge's stated reason:** Placeholder makes this synthetic; phishing is mislabeled task scam and warrants high-risk.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 317/324 -- split=test row_index=80 seed_id=seed_5efd416f05fd

> Bạn vừa nhận được mã OTP là 123456 từ BIDV. Hãy nhập mã này để xác nhận thanh toán mua sắm trực tuyến. Nếu bạn ko thực hiện giao dịch này, vui lòng bỏ qua tin nhắn này. Cảm ơn!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [123456]
- **Judge scores:** realism=5, label_correctness=1, code_switch_naturalness=4, risk_tier_correctness=2, suspicious_span_accuracy=2
- **Judge's stated reason:** Thông báo OTP thanh toán là benign, không phải nhiệm vụ.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 318/324 -- split=test row_index=83 seed_id=seed_d53ed10ecc4a

> Chào bạn, để nâng cấp dịch vụ, vui lòng cập nhật thông tin tài khoản tại đây: [http://updateaccount.info]. Đội ngũ hỗ trợ sẽ giúp bạn hoàn thành quy trình nhanh chóng. Cảm ơn sự hợp tác của bạn.

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [[http://updateaccount.info]]
- **Judge scores:** realism=2, label_correctness=1, code_switch_naturalness=4, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge's stated reason:** Placeholder makes this synthetic; phishing is mislabeled task scam and warrants high-risk.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 319/324 -- split=test row_index=86 seed_id=seed_23882e611996

> Chào bạn, tôi là Mr. Hùng từ bộ phận an ninh của Ngân hàng DEF. Chúng tôi phát hiện có hoạt động đáng ngờ trong tài khoản của bạn. Vui lòng xác minh thông tin bằng cách click [link] và nhập OTP. ĐT: 0912345678

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [[link], 0912345678]
- **Judge scores:** realism=2, label_correctness=1, code_switch_naturalness=4, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge's stated reason:** Placeholder makes this synthetic; phishing is mislabeled task scam and warrants high-risk.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 320/324 -- split=test row_index=87 seed_id=seed_5efd416f05fd

> Chào bạn, chúng tôi từ MBBank xin thông báo rằng tài khoản của bạn đang gặp rủi ro. Để bảo vệ tài khoản, hãy đăng nhập vào ứng dụng MBBank và thay đổi mật khẩu ngay lập tức. Nếu ko, tài khoản của bạn có thể bị khóa. Vui lòng thực hiện ngay, nha!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** []
- **Judge scores:** realism=5, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge's stated reason:** Đổi mật khẩu trong app là cảnh báo ngân hàng benign, không phải task.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 321/324 -- split=test row_index=90 seed_id=seed_d53ed10ecc4a

> Bạn vừa nhận được 1 triệu điểm thưởng từ chương trình khuyến mãi. Vui lòng đăng nhập vào app để nhận thưởng. Nếu bạn không đăng nhập trong 24 giờ, phần thưởng sẽ hết hạn. ĐT Hỗ Trợ: 0123456789.

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [0123456789]
- **Judge scores:** realism=2, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=4, suspicious_span_accuracy=2
- **Judge's stated reason:** Placeholder makes this synthetic; phishing is mislabeled task scam and poorly spanned.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 322/324 -- split=test row_index=93 seed_id=seed_23882e611996

> Xin chào, tôi là Ms. Hoa từ Ngân hàng GHI. Theo quy định mới, bạn cần cập nhật thông tin sinh trắc học khuôn mặt để tiếp tục sử dụng dịch vụ. Vui lòng click [link] để thực hiện. Nếu bạn ko làm, tài khoản của bạn sẽ bị khóa. ĐT: 0987654321

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [[link], 0987654321]
- **Judge scores:** realism=2, label_correctness=1, code_switch_naturalness=4, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge's stated reason:** Placeholder makes this synthetic; phishing is mislabeled task scam and warrants high-risk.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 323/324 -- split=test row_index=94 seed_id=seed_5efd416f05fd

> Xin chào, đây là Agribank. Chúng tôi cần xác nhận lại thông tin về tài khoản Smart OTP của bạn. Vui lòng truy cập [https://agribank-update.com] để cập nhật thông tin. Nếu ko, tài khoản của bạn sẽ bị khóa. Hành động ngay, nha!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [[https://agribank-update.com]]
- **Judge scores:** realism=2, label_correctness=1, code_switch_naturalness=4, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge's stated reason:** Placeholder makes this synthetic; phishing is mislabeled task scam and warrants high-risk.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---

## Candidate 324/324 -- split=test row_index=97 seed_id=seed_d53ed10ecc4a

> Xin chào, tài khoản của bạn đang có rủi ro bị hack. Vui lòng đổi mật khẩu ngay lập tức tại [http://securelogin.net]. Đội ngũ an ninh sẽ hỗ trợ bạn. Cảm ơn!

- **Current label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [[http://securelogin.net]]
- **Judge scores:** realism=2, label_correctness=1, code_switch_naturalness=4, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge's stated reason:** Placeholder makes this synthetic; phishing is mislabeled task scam and warrants high-risk.

**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row

**Notes:**

---
