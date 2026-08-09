# Phase 39 Manual Quality Review Sheet

Sample size: 100 (50 judge-pass, 50 judge-fail)
Source corpus: 2421 merged rows (1079 judge-pass, 1342 judge-fail) -- this is
the corpus state AT JUDGE TIME. It has since been repaired (see
data/manifests/manifest.json's `zalo_narrator_scaffold_repair` entry): the
zalo_social_engineering narrator-scaffold defect the judge itself flagged was
fixed, and a downstream seed-cap re-enforcement trimmed a few more rows. The
corpus is now 2343 rows.

**14 of the 100 examples below are `zalo_social_engineering` rows** (seeds
`f96fa34949cf`, `c1b8d1d09927` x2, `453f4123d6fb`, `a23c0ac8b044`,
`a236e34e7773`, `8f5da072ee2b`, `e2773f4d633e`, `9040926c38f5`,
`3ceb8f4aab76`, `a631c566f8db`, `8596de0b7d00`, `1ed2f91485cb`,
`d8eb5e399eb2`) and show the OLD, pre-repair narrator-scaffold text (e.g.
"Tin Zalo tu bac si: ..."), not the current corpus text. Their PASS/FAIL
verdict below reflects what the judge saw at the time -- this is still valid
for checking whether the judge's OWN call was reasonable, but if you go
looking for these seeds in the live `data/splits/*.jsonl`, the text there
has changed (or, for a small number, that specific near-duplicate variant
was dropped entirely -- see the manifest for which).

Instructions: for each example below, read the message text and the Codex judge's verdict, then mark Your verdict as PASS or FAIL based on your own independent read of whether the row is genuinely realistic Vietnamese text with a correctly matching label and risk tier -- not whether you agree with Codex's stated reason. Add any observations in the blank Notes field.

---
## Example 1/100 -- split=test row_index=33 seed_id=seed_5efd416f05fd

> Thông báo từ VietcomBank: Tài khoản của bạn vừa đăng nhập từ thiết bị lạ tại Úc. Nếu không phải bạn, hãy xác minh ngay tại: http://vietcom-bank-secure.net/xacminh để tránh bị khóa tài khoản trong 24h. Liên hệ CSKH: 1800.9999.88

- **Label:** bank_impersonation
- **Risk tier:** high-risk
- **Suspicious spans:** [http://vietcom-bank-secure.net/xacminh, đăng nhập từ thiết bị lạ tại Úc, bị khóa tài khoản trong 24h]
- **XAI explanation:** Tên miền giả mạo 'vietcom-bank-secure.net' không phải domain chính thức của Vietcombank (vietcombank.com.vn), kết hợp với cảnh báo đăng nhập từ nước ngoài để tạo áp lực khẩn cấp nhằm lừa người dùng nhấp vào link độc hại.
- **Codex judge verdict:** PASS -- realism=5, label_correctness=5, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:** Đăng nhập tại Úc và trang giả tạo cảnh báo high-risk rõ.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 2/100 -- split=test row_index=61 seed_id=seed_23882e611996

> Bạn ơi, mình thấy trên Facebook có hội nhóm "Hỗ trợ cập nhật sinh trắc học MB Bank 2024" hướng dẫn miễn phí nè. Vô link này nha: fb.com/groups/mbbank.htrobiometric – họ sẽ remote vào điện thoại mình để cài giúp, tiện lắm, mình dc rồi ko lo gì đâu 👍

- **Label:** bank_impersonation
- **Risk tier:** high-risk
- **Suspicious spans:** [fb.com/groups/mbbank.htrobiometric, remote vào điện thoại mình để cài giúp]
- **XAI explanation:** Tin nhắn dẫn dụ người dùng tham gia nhóm Facebook giả mạo MB Bank và chấp nhận cho kẻ lạ điều khiển từ xa điện thoại, tạo điều kiện đánh cắp toàn bộ dữ liệu tài khoản ngân hàng.
- **Codex judge verdict:** PASS -- realism=4, label_correctness=3, code_switch_naturalness=5, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:** Nhóm hỗ trợ MB giả dụ remote máy, dù không trực tiếp xưng ngân hàng.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 3/100 -- split=test row_index=77 seed_id=seed_d771851a922b

> Xin chào, tôi là nhân viên hỗ trợ khách hàng của Shopee. Chúng tôi đang tìm cộng tác viên để đánh giá sản phẩm. Bạn chỉ cần mua sản phẩm, đánh giá 5 sao, sau đó chúng tôi sẽ hoàn lại tiền mua hàng và trả thêm 20% hoa hồng. Hãy đăng ký ngay tại đây: shopee.vn/kiemtien. Liên hệ với tôi qua Zalo: 0987654321 nếu bạn muốn tham gia.

- **Label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [shopee.vn/kiemtien, 0987654321]
- **XAI explanation:** Lừa đảo thông qua việc yêu cầu nạn nhân mua hàng và đánh giá, sau đó không hoàn lại tiền và không trả hoa hồng.
- **Codex judge verdict:** FAIL -- realism=5, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=2, suspicious_span_accuracy=2
- **Judge reason:** Yêu cầu mua trước để hoàn tiền và hoa hồng là high-risk; spans chỉ giữ link và Zalo.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 4/100 -- split=test row_index=81 seed_id=seed_8e92a82e90b4

> Bạn ơi, mình là bot từ Telegram. Hiện tại chúng tôi đang có chương trình khuyến mãi dành cho những ai đăng ký tài khoản trên Binance qua link giới thiệu của mình. Bạn sẽ nhận được 5% hoa hồng từ mỗi giao dịch. Để kích hoạt tài khoản, vui lòng gửi 100k VND qua ví Momo 0123456789. Cảm ơn bạn, ak!

- **Label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [0123456789]
- **XAI explanation:** Không nên chuyển tiền cho bất kỳ ai yêu cầu phí kích hoạt tài khoản.
- **Codex judge verdict:** FAIL -- realism=2, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=2, suspicious_span_accuracy=2
- **Judge reason:** Placeholder makes this synthetic; span omits the pay-first cue requiring high-risk.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 5/100 -- split=test row_index=116 seed_id=seed_5efd416f05fd

> Chào bạn, mình là đại diện của Binance. Bạn đăng ký qua link của mình sẽ nhận được hoa hồng 5% từ mỗi giao dịch. Link: https://binancefake.com/signup. Đóng phí 100k để xác minh tài khoản. Rất mong hợp tác!

- **Label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [https://binancefake.com/signup, 100k]
- **XAI explanation:** Phí xác minh 100k sẽ không được hoàn lại và bạn không thể rút tiền từ tài khoản.
- **Codex judge verdict:** FAIL -- realism=2, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge reason:** Placeholder makes this synthetic; pay-first task warrants high-risk rather than suspicious.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 6/100 -- split=test row_index=130 seed_id=seed_d53ed10ecc4a

> Chào bạn, tài khoản của bạn đã nhận được 5,000,000 VND từ Nguyễn Văn A. Vui lòng kiểm tra lại thông tin giao dịch qua ứng dụng Internet Banking. Trân trọng, Ngân hàng ABC.

- **Label:** benign
- **Risk tier:** suspicious
- **Suspicious spans:** []
- **XAI explanation:** Thông báo này xác nhận một giao dịch chuyển tiền hợp lệ và yêu cầu khách hàng kiểm tra thông tin qua ứng dụng Internet Banking.
- **Codex judge verdict:** FAIL -- realism=5, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=1, suspicious_span_accuracy=5
- **Judge reason:** Khoản tiền đến và kiểm tra ứng dụng là benign.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 7/100 -- split=test row_index=143 seed_id=seed_eccbf8f246ed

> Thân chào khách hàng, chúng tôi vừa gửi cho bạn một mã OTP để xác minh danh tính. Vui lòng nhập mã này vào ứng dụng của chúng tôi để tiếp tục quá trình đăng nhập.

- **Label:** benign
- **Risk tier:** suspicious
- **Suspicious spans:** []
- **XAI explanation:** Thông báo gửi mã OTP để xác minh danh tính, thông thường và an toàn khi sử dụng dịch vụ ngân hàng trực tuyến.
- **Codex judge verdict:** FAIL -- realism=5, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge reason:** Routine notification is benign; assigned suspicious tier is too high.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 8/100 -- split=test row_index=148 seed_id=seed_93304f9cc9ab

> Xin chào, mã OTP của bạn là 123456. Vui lòng nhập mã này để xác minh giao dịch trên ứng dụng ngân hàng của bạn.

- **Label:** benign
- **Risk tier:** benign
- **Suspicious spans:** []
- **XAI explanation:** Thông báo gửi mã OTP để xác minh giao dịch trên ứng dụng ngân hàng.
- **Codex judge verdict:** PASS -- realism=5, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:** Mã xác minh giao dịch trong app là thông báo benign.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 9/100 -- split=test row_index=154 seed_id=seed_23882e611996

> Chào bạn, giao dịch chuyển tiền 500.000 VND của bạn đã thành công. Số dư hiện tại là 1.500.000 VND. Chi tiết: TK 123456789 -> 987654321.

- **Label:** benign
- **Risk tier:** suspicious
- **Suspicious spans:** []
- **XAI explanation:** Thông báo xác nhận giao dịch chuyển tiền thành công và hiển thị số dư hiện tại.
- **Codex judge verdict:** FAIL -- realism=5, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=1, suspicious_span_accuracy=5
- **Judge reason:** Biên nhận chuyển tiền và số dư hoàn toàn benign.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 10/100 -- split=test row_index=198 seed_id=seed_f96fa34949cf

> Cuộc gọi Zalo chỉ kéo dài vài giây. nhân viên chăm sóc khách hàng giao đồ ăn gửi tiếp: “Hệ thống cần hoàn lại giao dịch trùng. Khách hàng được báo đơn giao đồ ăn bị tính tiền hai lần. bật chia sẻ màn hình và đọc mã xác nhận hoàn tiền; Phiên hoàn tiền chỉ còn hiệu lực năm phút.”

- **Label:** zalo_social_engineering
- **Risk tier:** high-risk
- **Suspicious spans:** [bật chia sẻ màn hình và đọc mã xác nhận hoàn tiền]
- **XAI explanation:** Tài khoản tự xưng nhân viên chăm sóc khách hàng giao đồ ăn lợi dụng việc hệ thống cần hoàn lại giao dịch trùng và người gửi hướng dẫn chia sẻ màn hình khi mở ứng dụng ngân hàng để yêu cầu bật chia sẻ màn hình và đọc mã xác nhận hoàn tiền, có thể dẫn đến tài khoản ngân hàng bị chiếm đoạt.
- **Codex judge verdict:** PASS -- realism=3, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:** Cuộc gọi thúc đọc mã hoàn tiền trong năm phút là chiếm đoạt rõ.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 11/100 -- split=test row_index=201 seed_id=seed_c1b8d1d09927

> Tin Zalo từ quản trị viên sàn mua bán: “Người bán được báo đã có khách thanh toán. Tiền bán hàng đang bị giữ do tài khoản chưa xác minh. đăng nhập ngân hàng qua liên kết để mở khóa tiền bán. Đơn hàng sẽ tự hủy nếu không xác nhận.”

- **Label:** zalo_social_engineering
- **Risk tier:** high-risk
- **Suspicious spans:** [đăng nhập ngân hàng qua liên kết để mở khóa tiền bán]
- **XAI explanation:** Tài khoản tự xưng quản trị viên sàn mua bán lợi dụng việc tiền bán hàng đang bị giữ do tài khoản chưa xác minh và trang giả hiển thị đơn hàng và số tiền chờ nhận để yêu cầu đăng nhập ngân hàng qua liên kết để mở khóa tiền bán, có thể dẫn đến mất thông tin đăng nhập ngân hàng.
- **Codex judge verdict:** PASS -- realism=3, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:** Liên kết đăng nhập ngân hàng để mở tiền bán là đánh cắp tài khoản.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 12/100 -- split=test row_index=205 seed_id=seed_c1b8d1d09927

> Tin nhắn thoại trên Zalo được chép lại: “Người bán được báo đã có khách thanh toán. Người gửi nói trang giả hiển thị đơn hàng và số tiền chờ nhận. Tiền bán hàng đang bị giữ do tài khoản chưa xác minh. đăng nhập ngân hàng qua liên kết để mở khóa tiền bán. Đơn hàng sẽ tự hủy nếu không xác nhận.”

- **Label:** zalo_social_engineering
- **Risk tier:** high-risk
- **Suspicious spans:** [đăng nhập ngân hàng qua liên kết để mở khóa tiền bán]
- **XAI explanation:** Tài khoản tự xưng quản trị viên sàn mua bán lợi dụng việc tiền bán hàng đang bị giữ do tài khoản chưa xác minh và trang giả hiển thị đơn hàng và số tiền chờ nhận để yêu cầu đăng nhập ngân hàng qua liên kết để mở khóa tiền bán, có thể dẫn đến mất thông tin đăng nhập ngân hàng.
- **Codex judge verdict:** FAIL -- realism=2, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:** Narrator meta-scaffold describes deception instead of presenting an authentic message.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 13/100 -- split=test row_index=226 seed_id=seed_453f4123d6fb

> Tin Zalo từ bác sĩ điều trị: “Gia đình bệnh nhân được báo thuốc điều trị đã hết. Một lô thuốc nhập khẩu hiếm vừa được giữ chỗ. chuyển tiền mua thuốc vào tài khoản của người quen bác sĩ. Nhà thuốc chỉ giữ thuốc đến cuối giờ.”

- **Label:** zalo_social_engineering
- **Risk tier:** high-risk
- **Suspicious spans:** [chuyển tiền mua thuốc vào tài khoản của người quen bác sĩ]
- **XAI explanation:** Tài khoản tự xưng bác sĩ điều trị lợi dụng việc một lô thuốc nhập khẩu hiếm vừa được giữ chỗ và toa thuốc giả và ảnh hộp thuốc được gửi để tạo tin tưởng để yêu cầu chuyển tiền mua thuốc vào tài khoản của người quen bác sĩ, có thể dẫn đến mất tiền và trì hoãn điều trị thật.
- **Codex judge verdict:** PASS -- realism=3, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:** Giả bác sĩ thúc chuyển tiền thuốc vào tài khoản cá nhân là nguy hiểm.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 14/100 -- split=test row_index=247 seed_id=seed_a23c0ac8b044

> Một tài khoản Zalo mới tự xưng quản trị viên nhóm đồ thất lạc nhắn: “Người dùng được báo có ví giấy tờ được nhặt thấy.” Người này nói kẻ gửi mô tả đúng vài chi tiết công khai rồi xin thêm giấy tờ, sau đó yêu cầu “gửi ảnh căn cước và ảnh selfie cầm giấy tờ” và dặn “Đồ sẽ được giao cho người nhận khác nếu không xác minh”.

- **Label:** zalo_social_engineering
- **Risk tier:** high-risk
- **Suspicious spans:** [gửi ảnh căn cước và ảnh selfie cầm giấy tờ]
- **XAI explanation:** Tài khoản tự xưng quản trị viên nhóm đồ thất lạc lợi dụng việc người nhận phải chứng minh mình là chủ sở hữu và kẻ gửi mô tả đúng vài chi tiết công khai rồi xin thêm giấy tờ để yêu cầu gửi ảnh căn cước và ảnh selfie cầm giấy tờ, có thể dẫn đến danh tính bị dùng để mở tài khoản giả.
- **Codex judge verdict:** FAIL -- realism=2, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:** Narrator meta-scaffold describes deception instead of presenting an authentic message.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 15/100 -- split=train row_index=0 seed_id=seed_0dbd0f1e898c

> VIETCOMBANK: Tai khoan cua ban vua bi truy cap tu thiet bi la. De bao ve account, xac thuc ngay qua link: http://vcb-secure-verify.net/login . Neu khong xac thuc trong 15 phut, Internet Banking se bi khoa. Lien he: 0934.872.651

- **Label:** bank_impersonation
- **Risk tier:** high-risk
- **Suspicious spans:** [http://vcb-secure-verify.net/login, Tai khoan cua ban vua bi truy cap tu thiet bi la, Internet Banking se bi khoa]
- **XAI explanation:** Tin nhắn giả mạo Vietcombank dùng cảnh báo khẩn về thiết bị lạ và đường link không chính thức để ép người dùng nhấp vào trang lừa đảo.
- **Codex judge verdict:** PASS -- realism=4, label_correctness=5, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:** Convincing urgent bank lure with natural mixing and precise malicious cues.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 16/100 -- split=train row_index=10 seed_id=seed_441f08e9ca28

> MB BANK: Tai khoan cua ban vua bi truy cap tu thiet bi la luc 03:47. Neu khong phai ban, click ngay: http://mbbank-secure-vn.net/xacnhan de khoa lenh. OTP se duoc gui sau khi xac thuc. LH: 1900.8888 (phim 2).

- **Label:** bank_impersonation
- **Risk tier:** high-risk
- **Suspicious spans:** [http://mbbank-secure-vn.net/xacnhan, Tai khoan cua ban vua bi truy cap tu thiet bi la, OTP se duoc gui sau khi xac thuc]
- **XAI explanation:** Tin nhắn giả mạo MB Bank dùng URL không chính thức và tạo áp lực khẩn cấp để dụ người dùng nhấp vào link lừa đảo nhằm chiếm đoạt OTP và thông tin tài khoản.
- **Codex judge verdict:** PASS -- realism=4, label_correctness=5, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:** Natural SMS-style impersonation with urgent hostile URL and exact supporting spans.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 17/100 -- split=train row_index=50 seed_id=seed_db9fb32e2681

> VIETCOMBANK: Tai khoan cua ban vua co giao dich bat thuong 15,000,000 VND luc 02:47. Neu ban KHONG thuc hien giao dich nay, truy cap ngay http://vcb-secure-verify.net/xacnhan de khoa lenh hoac goi 1800.6868 (mien phi). OTP se het han sau 5 phut!

- **Label:** bank_impersonation
- **Risk tier:** high-risk
- **Suspicious spans:** [http://vcb-secure-verify.net/xacnhan, giao dich bat thuong 15,000,000 VND, OTP se het han sau 5 phut]
- **XAI explanation:** URL giả mạo tên miền Vietcombank kết hợp với cảnh báo giao dịch khẩn cấp và áp lực OTP hết hạn là dấu hiệu điển hình của tấn công lừa đảo ngân hàng.
- **Codex judge verdict:** PASS -- realism=4, label_correctness=5, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:** Coherent high-risk transaction scare; all selected phrases are exact and salient.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 18/100 -- split=train row_index=71 seed_id=seed_686d86ff091c

> Chào anh/chị, em là Linh từ bộ phận hỗ trợ Techcombank. TK Internet Banking của anh/chị đang có giao dịch lạ 15tr lúc 2h sáng. Anh/chị cần xác nhận ngay qua link này để huỷ GD: techcom-verify.cc/huy-gd — nếu k phản hồi trong 10p sẽ bị trừ tiền ak!

- **Label:** bank_impersonation
- **Risk tier:** high-risk
- **Suspicious spans:** [techcom-verify.cc/huy-gd, giao dịch lạ 15tr lúc 2h sáng, nếu k phản hồi trong 10p sẽ bị trừ tiền]
- **XAI explanation:** Kẻ lừa đảo giả danh nhân viên Techcombank tạo áp lực thời gian và dùng tên miền giả để chiếm đoạt thông tin đăng nhập Internet Banking.
- **Codex judge verdict:** PASS -- realism=5, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:** Natural abbreviated chat scam with malicious cancellation URL and immediate loss pressure.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 19/100 -- split=train row_index=96 seed_id=seed_c6c8772ac332

> Xin chào anh/chị, em là Nguyễn Linh từ bộ phận Hỗ Trợ Khách Hàng BIDV. Hệ thống ghi nhận Internet Banking của anh/chị đang đăng nhập từ thiết bị lạ tại Hà Nội lúc 11:23 sáng nay. Để đảm bảo an toàn, anh/chị vui lòng xác nhận OTP được gửi về số điện thoại đăng ký và KHÔNG chia sẻ mã này với bất kỳ ai kể cả nhân viên ngân hàng nhé 😊. Nếu không phải anh/chị thực hiện, hãy bấm vào link sau để đóng băng tài khoản ngay: https://bidv-hotro-kh.com/freeze-account?id=8821 hoặc liên hệ hotline nội bộ 0903.221.887 để được hỗ trợ 24/7 ạ.

- **Label:** bank_impersonation
- **Risk tier:** high-risk
- **Suspicious spans:** [https://bidv-hotro-kh.com/freeze-account?id=8821, đăng nhập từ thiết bị lạ, 0903.221.887]
- **XAI explanation:** Kẻ tấn công giả danh nhân viên BIDV, tạo cảm giác tin tưởng bằng lời cảnh báo an toàn rồi dẫn dụ bấm link giả mạo để chiếm đoạt thông tin tài khoản.
- **Codex judge verdict:** PASS -- realism=5, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:** Sophisticated reassurance surrounds a hostile freeze link and fake internal support contact.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 20/100 -- split=train row_index=141 seed_id=seed_9d35f25f7d8b

> ⚠️ MBBANK THÔNG BÁO: App MBBank của bạn sẽ bị khoá lúc 23:59 hôm nay do chưa cập nhật eKYC. Vào link sau để xác thực ngay, tránh bị gián đoạn dịch vụ: https://mbbank-ekyc-update.pages.dev/login — Cần hỗ trợ gọi 0398.XXX.XXX. Lưu ý: KHÔNG chia sẻ mã OTP hoặc account với bất kỳ ai kể cả nhân viên ngân hàng (đây là thông báo tự động).

- **Label:** bank_impersonation
- **Risk tier:** high-risk
- **Suspicious spans:** [https://mbbank-ekyc-update.pages.dev/login, App MBBank của bạn sẽ bị khoá lúc 23:59 hôm nay, 0398.XXX.XXX]
- **XAI explanation:** Tin nhắn giả danh MBBank dùng domain không chính thức trên Cloudflare Pages và tạo deadline giả để ép người dùng truy cập trang login giả mạo thu thập thông tin.
- **Codex judge verdict:** PASS -- realism=4, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:** Sophisticated eKYC lock notice pairs reassuring OTP advice with a malicious hosted page.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 21/100 -- split=train row_index=187 seed_id=seed_8226b8787914

> Ngân hàng Vietcombank thông báo: Tài khoản của bạn cần xác minh, chứng minh nguồn thu nhập và tài chính trước 17h hôm nay. Vui lòng đăng nhập tại http://vietcombank-xacminh.net và cung cấp thông tin để tránh bị khóa tài khoản vĩnh viễn.

- **Label:** bank_impersonation
- **Risk tier:** high-risk
- **Suspicious spans:** [http://vietcombank-xacminh.net, khóa tài khoản vĩnh viễn, trước 17h hôm nay]
- **XAI explanation:** URL giả mạo tên miền Vietcombank kết hợp áp lực thời gian và đe dọa khóa tài khoản là dấu hiệu điển hình của lừa đảo mạo danh ngân hàng.
- **Codex judge verdict:** PASS -- realism=4, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:** Plausible income-document harvesting lure with a fake site and permanent lock threat.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 22/100 -- split=train row_index=201 seed_id=seed_b6e080de275b

> Thông báo khẩn từ Vietcombank: Tài khoản của quý khách vừa bị đăng nhập từ thiết bị lạ lúc 02:47. Nếu không phải bạn, hãy xác minh ngay tại http://vietc0mbank-secure.net/verify hoặc gọi 1800.xxxx. OTP sẽ được gửi sau khi bạn truy cập link.

- **Label:** bank_impersonation
- **Risk tier:** high-risk
- **Suspicious spans:** [http://vietc0mbank-secure.net/verify, đăng nhập từ thiết bị lạ, OTP sẽ được gửi sau khi bạn truy cập link]
- **XAI explanation:** Link giả mạo dùng ký tự '0' thay chữ 'o' trong tên miền Vietcombank, kết hợp với việc yêu cầu truy cập URL để nhận OTP — đây là dấu hiệu điển hình của tấn công lừa đảo thu thập mã xác thực.
- **Codex judge verdict:** PASS -- realism=5, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:** Convincing typo-squatted verification lure with exact device and OTP cues.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 23/100 -- split=train row_index=202 seed_id=seed_b81d209eb87e

> Bạn đã nhận được một mã Smart OTP từ Ngân hàng LMN. Vui lòng nhập mã này tại [http://lmn-bank.net] để kích hoạt tài khoản mới. Nếu không, tài khoản sẽ bị vô hiệu hóa. Hạn chót: 48h.

- **Label:** bank_impersonation
- **Risk tier:** suspicious
- **Suspicious spans:** [[http://lmn-bank.net], mã Smart OTP]
- **XAI explanation:** Không nhập mã Smart OTP vào các trang web không rõ nguồn gốc, hãy liên hệ trực tiếp ngân hàng để xác minh.
- **Codex judge verdict:** FAIL -- realism=2, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge reason:** Bracketed placeholder formatting makes this read like generated text, not a real message.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 24/100 -- split=train row_index=216 seed_id=seed_e5463bf1077a

> Chị ơi, e là Linh, nhân viên VPBank. Tài khoản của chị đang có vấn đề về bảo mật. Chị vui lòng đăng nhập vào link dưới đây để thay đổi mật khẩu: https://vpbank-login.com. Nếu không, tài khoản sẽ bị khóa vĩnh viễn nha. Cảm ơn chị!

- **Label:** bank_impersonation
- **Risk tier:** suspicious
- **Suspicious spans:** [https://vpbank-login.com]
- **XAI explanation:** Luôn kiểm tra URL chính thức của ngân hàng trước khi đăng nhập.
- **Codex judge verdict:** FAIL -- realism=4, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge reason:** Fake password-change login plus permanent-lock threat warrants high risk.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 25/100 -- split=train row_index=223 seed_id=seed_13f16cf56dbe

> 【BIDV】 Chào anh/chị, tk của a/c có giao dịch chuyển 48.500.000đ lúc 22:14 hôm nay. Nếu k phải bạn thực hiện, bấm vào link sau để huỷ ngay: https://bidv-cancel-txn.com/huy?id=8821 — Smart OTP sẽ dc gửi về SĐT đăng ký. Xử lý trong 5 phút kẻo hết hạn nha!

- **Label:** bank_impersonation
- **Risk tier:** high-risk
- **Suspicious spans:** [https://bidv-cancel-txn.com/huy?id=8821, Xử lý trong 5 phút kẻo hết hạn, Smart OTP sẽ dc gửi về SĐT đăng ký]
- **XAI explanation:** Kẻ lừa đảo giả mạo BIDV tạo áp lực thời gian 5 phút và dẫn nạn nhân vào link giả để thu thập Smart OTP nhằm chiếm quyền kiểm soát tài khoản.
- **Codex judge verdict:** PASS -- realism=5, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:** Authentic-looking transfer alert uses hostile cancellation link and five-minute OTP pressure.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 26/100 -- split=train row_index=230 seed_id=seed_441f08e9ca28

> Thông báo từ MB Bank: Chúng tôi phát hiện giao dịch lạ 45,000,000 VND từ tài khoản của bạn. Nếu ko phải bạn thực hiện, hãy đăng nhập Smart OTP ngay tại mbbank-secure.vn/cancel để hủy giao dịch. Liên hệ hotline: 0912.345.678

- **Label:** bank_impersonation
- **Risk tier:** high-risk
- **Suspicious spans:** [mbbank-secure.vn/cancel, giao dịch lạ 45,000,000 VND, 0912.345.678]
- **XAI explanation:** Kẻ lừa đảo giả danh MB Bank tạo áp lực tâm lý bằng giao dịch giả mạo số tiền lớn, dẫn dụ người dùng vào link giả để chiếm đoạt thông tin Smart OTP.
- **Codex judge verdict:** PASS -- realism=4, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:** Plausible large-transfer lure routes Smart OTP through a hostile cancellation domain.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 27/100 -- split=train row_index=260 seed_id=seed_bfe4a6bbd16d

> Thong bao tu BIDV: HT Smart OTP cua ban sap het han vao 23:59 hom nay. Cap nhat ngay de tranh gian doan giao dich Internet Banking. Truy cap: bidv-update-otp[.]com va nhap ma OTP hien tai de kich hoat lai. Lien he hotline: 090-3345-6712 neu can ho tro.

- **Label:** bank_impersonation
- **Risk tier:** high-risk
- **Suspicious spans:** [bidv-update-otp[.]com, nhap ma OTP hien tai, Smart OTP cua ban sap het han]
- **XAI explanation:** Kẻ lừa đảo giả danh BIDV yêu cầu nạn nhân nhập mã OTP hiện tại lên website giả mạo, đây là thủ thuật đánh cắp mã xác thực để chiếm quyền tài khoản.
- **Codex judge verdict:** FAIL -- realism=2, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:** Bracketed placeholder formatting makes this read like generated text, not a real message.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 28/100 -- split=train row_index=293 seed_id=seed_977875fab0f0

> [MB BANK - THONG BAO KHAN]: He thong Smart OTP cua ban het hieu luc. De tranh gian doan giao dich Internet Banking, cap nhat ngay tai: mb-bank-otp.com/update. Luu y: Khong chia se ma xac thuc voi bat ky ai ke ca nhan vien ngan hang.

- **Label:** bank_impersonation
- **Risk tier:** high-risk
- **Suspicious spans:** [mb-bank-otp.com/update, Smart OTP cua ban het hieu luc, THONG BAO KHAN]
- **XAI explanation:** Tin nhắn giả mạo MB Bank tạo cảm giác khẩn cấp về Smart OTP hết hạn để lừa người dùng truy cập website giả mạo nhằm đánh cắp thông tin đăng nhập.
- **Codex judge verdict:** PASS -- realism=4, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:** Authentic-looking urgent Smart OTP update directs users to a hostile domain.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 29/100 -- split=train row_index=332 seed_id=seed_b2c9477c611a

> Bạn ơi, mình là CTV của Agribank đang hỗ trợ nâng cấp app mới. Tk của bạn cần xác minh lại để tránh bị đình chỉ dịch vụ. Bạn login vào link này nha: https://agribank-upgrade.info/dangnhap rồi nhập đầy đủ số tk + mật khẩu + mã Smart OTP là xong, k tốn quá 2 phút dc đâu 😊

- **Label:** bank_impersonation
- **Risk tier:** high-risk
- **Suspicious spans:** [https://agribank-upgrade.info/dangnhap, nhập đầy đủ số tk + mật khẩu + mã Smart OTP]
- **XAI explanation:** Kẻ lừa đảo dùng giọng điệu thân thiện, giả vai CTV Agribank và dẫn đến trang phishing để thu thập đồng thời mật khẩu lẫn mã Smart OTP của nạn nhân.
- **Codex judge verdict:** PASS -- realism=5, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:** Natural fake collaborator explicitly harvests account, password, and Smart OTP.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 30/100 -- split=train row_index=378 seed_id=seed_db9fb32e2681

> ACB: Phat hien login bat thuong vao account cua ban tu IP nuoc ngoai. De bao ve, ban can cap nhat lai mat khau qua link: http://acb-online.info/reset?id=8821 ngay bay gio. Ko lam se bi khoa vinh vien trong 24h.

- **Label:** bank_impersonation
- **Risk tier:** high-risk
- **Suspicious spans:** [http://acb-online.info/reset?id=8821, login bat thuong vao account, bi khoa vinh vien trong 24h]
- **XAI explanation:** URL giả mạo ACB dùng giao thức HTTP không bảo mật kết hợp đe dọa khóa tài khoản vĩnh viễn để ép nạn nhân nhập mật khẩu vào trang lừa đảo.
- **Codex judge verdict:** PASS -- realism=4, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:** Credible foreign-login warning routes password reset through a hostile URL with permanent-lock pressure.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 31/100 -- split=train row_index=405 seed_id=seed_aac4f3d94e74

> Chào bạn, mình là quản trị viên của nhóm TikTok. Hiện tại chúng tôi đang cần người like và comment video để tăng tương tác. Mỗi task chỉ 1k VND, thanh toán qua Internet Banking sau khi hoàn thành 10 task đầu tiên. Bạn có quan tâm không? Liên hệ zalo 0987654321 để biết thêm chi tiết. Chúc bạn ngày vui vẻ!

- **Label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [0987654321]
- **XAI explanation:** Đây là một kịch bản lừa đảo yêu cầu bạn like và comment trên TikTok với hứa hẹn trả tiền. Hãy cẩn thận với các đề nghị như vậy.
- **Codex judge verdict:** FAIL -- realism=4, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=4, suspicious_span_accuracy=2
- **Judge reason:** Contact-only spans miss the impersonation or paid-task lure that makes the message suspicious.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 32/100 -- split=train row_index=424 seed_id=seed_fda2464f98fe

> Chào bạn, mình là admin của nhóm TikTok @tiktokjobvn. Mình đang cần tuyển người like, follow, và comment video để tăng tương tác. Mỗi task trả 10k, nếu làm tốt sẽ được tăng lên 20k/task. Bạn quan tâm thì liên hệ qua Zalo 0971234567 để nhận hướng dẫn chi tiết. Chúc may mắn, ak!

- **Label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [@tiktokjobvn, 0971234567]
- **XAI explanation:** Admin yêu cầu bạn liên hệ qua Zalo để nhận hướng dẫn, nhưng không cung cấp thông tin cụ thể về công việc.
- **Codex judge verdict:** PASS -- realism=4, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=4, suspicious_span_accuracy=5
- **Judge reason:** Credible task-scam recruitment with escalating pay and direct Zalo migration.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 33/100 -- split=train row_index=438 seed_id=seed_686d86ff091c

> Xin chào, tớ là Mod của nhóm Shopee trên Facebook. Tớ cần người giúp mua sản phẩm và viết đánh giá 5 sao. Bạn sẽ được hoàn lại tiền mua hàng và nhận thêm 10% hoa hồng. Hãy đặt hàng qua link này: http://shopeebuyback.com/order. Liên hệ tớ qua Zalo 0123456789 nếu cần hỗ trợ. Cảm ơn bạn!

- **Label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [http://shopeebuyback.com/order, Zalo 0123456789]
- **XAI explanation:** Link và số điện thoại có thể là bẫy lừa đảo, hãy kiểm tra kỹ trước khi thực hiện giao dịch.
- **Codex judge verdict:** FAIL -- realism=2, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=3, suspicious_span_accuracy=5
- **Judge reason:** Sequential 0123456789 is an obvious placeholder, undermining real-world plausibility.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 34/100 -- split=train row_index=439 seed_id=seed_6b8624baa879

> Xin chào, mình là quản lý của cửa hàng Shopee. Hiện tại chúng tôi đang cần người mua sản phẩm và đánh giá 5 sao để nhận hoàn tiền 100% và hoa hồng 10%. Bạn chỉ cần đặt đơn hàng, sau khi nhận hàng và đánh giá, tiền sẽ được hoàn lại vào tài khoản của bạn. Hãy liên hệ với mình qua số 0123456789 để biết thêm chi tiết nha. Đừng bỏ lỡ cơ hội này!

- **Label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [0123456789]
- **XAI explanation:** Đây là một kịch bản lừa đảo yêu cầu nạn nhân mua hàng và đánh giá để nhận hoàn tiền, nhưng tiền hoàn sẽ không bao giờ được trả.
- **Codex judge verdict:** FAIL -- realism=2, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=3, suspicious_span_accuracy=2
- **Judge reason:** Synthetic placeholder undermines realism; spans also omit the decisive unsafe action.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 35/100 -- split=train row_index=447 seed_id=seed_977875fab0f0

> Xin chào, tôi là quản lý dự án tại Shopee. Chúng tôi đang tìm người viết đánh giá 5 sao cho sản phẩm. Bạn sẽ được hoàn lại 100% tiền mua hàng và nhận thêm 20% hoa hồng. Để bắt đầu, hãy mua sản phẩm này: [https://shopee.vn/product-link]. Sau khi nhận hàng, viết đánh giá 5 sao và gửi ảnh xác nhận cho tôi. Tôi sẽ chuyển khoản cho bạn ngay sau đó.

- **Label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [[https://shopee.vn/product-link]]
- **XAI explanation:** Lừa đảo này yêu cầu bạn mua hàng và viết đánh giá, nhưng tiền hoàn lại và hoa hồng sẽ không bao giờ được chuyển.
- **Codex judge verdict:** FAIL -- realism=2, label_correctness=4, code_switch_naturalness=5, risk_tier_correctness=3, suspicious_span_accuracy=2
- **Judge reason:** Bracketed placeholder formatting makes this read like generated text, not a real message.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 36/100 -- split=train row_index=487 seed_id=seed_7a59dacb935f

> Bạn ơi, mình đang cần người giúp đăng ký tài khoản trên Binance qua link này: http://fakebinance.com. Mỗi tài khoản đăng ký thành công, bạn sẽ nhận 5% hoa hồng. Liên hệ Telegram: @FakeCryptoBot để biết thêm chi tiết. Cơ hội tốt, nhanh tay nhé!

- **Label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [http://fakebinance.com, @FakeCryptoBot]
- **XAI explanation:** Đây có thể là một lừa đảo vì nó yêu cầu bạn đăng ký trên một trang web giả mạo và hứa hẹn hoa hồng mà không có bảo đảm.
- **Codex judge verdict:** FAIL -- realism=2, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=4, suspicious_span_accuracy=5
- **Judge reason:** Literal fake naming exposes synthetic construction and undermines real-world plausibility.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 37/100 -- split=train row_index=510 seed_id=seed_cf2be9f86411

> Bạn ơi, tài khoản Smart OTP của bạn cần cập nhật thông tin. Vui lòng truy cập [http://secureupdate.com] để thực hiện. Nếu không, tài khoản sẽ bị tạm ngừng sử dụng. ĐT: 0912345678.

- **Label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [http://secureupdate.com, 0912345678]
- **XAI explanation:** Kiểm tra lại thông tin tài khoản trực tiếp với ngân hàng trước khi thực hiện bất kỳ hành động nào.
- **Codex judge verdict:** FAIL -- realism=2, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge reason:** Bracketed placeholder formatting makes this read like generated text, not a real message.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 38/100 -- split=train row_index=511 seed_id=seed_d41d9b30081a

> Alo, em ơi, đây là anh Tùng, cán bộ Công an, có thông tin em liên quan đến vụ án rửa tiền lớn. Em cần xác minh tài khoản Internet Banking của mình qua số điện thoại 0978123456 ngay để tránh rắc rối. Cảm ơn em.

- **Label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [0978123456]
- **XAI explanation:** Không gọi điện thoại cho số lạ và không cung cấp thông tin tài khoản.
- **Codex judge verdict:** FAIL -- realism=4, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=2, suspicious_span_accuracy=2
- **Judge reason:** Contact-only spans miss the impersonation or paid-task lure that makes the message suspicious.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 39/100 -- split=train row_index=559 seed_id=seed_d87bcc048ee5

> Chào bạn, đây là Ngân hàng ABC. Chúng tôi phát hiện có giao dịch khả nghi trên tk của bạn. Vui lòng đăng nhập vào [https://fakebank.com] để xác minh. Nếu ko, tk sẽ bị khóa. Cảm ơn.

- **Label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [[https://fakebank.com]]
- **XAI explanation:** Không đăng nhập vào liên kết không rõ nguồn gốc và liên hệ trực tiếp với ngân hàng nếu bạn nghi ngờ.
- **Codex judge verdict:** FAIL -- realism=2, label_correctness=1, code_switch_naturalness=5, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge reason:** Literal fake naming exposes synthetic construction and undermines real-world plausibility.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 40/100 -- split=train row_index=566 seed_id=seed_13f16cf56dbe

> Xin chào anh/chị, em là nhân viên của Ngân hàng ABC. Hiện tại, chúng tôi đang có chương trình khuyến mãi dành cho khách hàng VIP. Chỉ cần anh/chị nạp 10 triệu đồng vào tài khoản Internet Banking của mình qua [fakeURL.vn], anh/chị sẽ nhận được 5 triệu đồng tiền thưởng. Hãy nhanh tay nhé!

- **Label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [[fakeURL.vn], 10 triệu đồng, 5 triệu đồng]
- **XAI explanation:** Đây có thể là lừa đảo qua Internet Banking, hãy kiểm tra kỹ nguồn gốc thông tin trước khi thực hiện giao dịch.
- **Codex judge verdict:** FAIL -- realism=2, label_correctness=2, code_switch_naturalness=5, risk_tier_correctness=1, suspicious_span_accuracy=2
- **Judge reason:** Synthetic placeholder undermines realism; spans also omit the decisive unsafe action.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 41/100 -- split=train row_index=608 seed_id=seed_fda2464f98fe

> Chào bạn, mình là admin của group Zalo @zalolive. Chúng tôi đang tổ chức livestream và cần người đặt đơn hàng ảo để tăng tương tác. Mỗi đơn hàng trả 30k, tổng cộng 500k/ngày. Để tham gia, bạn vui lòng chuyển khoản 200k để nâng cấp tài khoản. Liên hệ qua Zalo 0912345678 để biết thêm chi tiết. Đừng bỏ lỡ, nha!

- **Label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [@zalolive, 0912345678]
- **XAI explanation:** Admin group Zalo yêu cầu bạn chuyển khoản để nâng cấp tài khoản trước khi có thể đặt đơn hàng ảo, đây là dấu hiệu lừa đảo.
- **Codex judge verdict:** FAIL -- realism=5, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=1, suspicious_span_accuracy=2
- **Judge reason:** A 200k upgrade transfer is high risk; annotations omit the payment.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 42/100 -- split=train row_index=622 seed_id=seed_baafb1055e64

> Chào bạn! Mình là admin của group TikTok lớn. Hiện tại, chúng tôi đang cần người like, follow, và comment trên các video. Mỗi task chỉ mất vài phút và bạn sẽ được trả 5k/ task. Nếu quan tâm, hãy click vào link này để đăng ký: http://tiktokjob.vn. Đừng bỏ lỡ cơ hội này, nha!

- **Label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [http://tiktokjob.vn]
- **XAI explanation:** Link này có thể dẫn đến trang web lừa đảo yêu cầu thông tin cá nhân hoặc phí đăng ký.
- **Codex judge verdict:** PASS -- realism=4, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=4, suspicious_span_accuracy=5
- **Judge reason:** Standard paid-engagement recruitment with a suspicious task registration site.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 43/100 -- split=train row_index=656 seed_id=seed_7d16b8e41bee

> Chào bạn, mình là admin của nhóm Zalo về đầu tư tiền điện tử. Chúng tôi đang có chương trình khuyến mãi cho người mới đăng ký. Bạn chỉ cần đăng ký qua link này: http://crypto-offer.com/register và mời bạn bè tham gia, mỗi người bạn mời sẽ giúp bạn kiếm được 5% hoa hồng. Khi đạt 10 người, bạn sẽ nhận được 100k VND. Liên hệ mình qua Zalo 0123456789 nếu có thắc mắc nha!

- **Label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [http://crypto-offer.com/register, 0123456789]
- **XAI explanation:** Cẩn thận với các lời mời đăng ký và mời bạn bè tham gia nền tảng tiền điện tử, thường có rủi ro mất tiền.
- **Codex judge verdict:** FAIL -- realism=2, label_correctness=4, code_switch_naturalness=4, risk_tier_correctness=4, suspicious_span_accuracy=5
- **Judge reason:** Sequential 0123456789 is an obvious placeholder, undermining real-world plausibility.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 44/100 -- split=train row_index=664 seed_id=seed_d41d9b30081a

> Xin chào, mình là quản lý của shop Shopee. Hiện tại shop đang cần người đánh giá sản phẩm. Bạn chỉ cần mua sản phẩm, đánh giá 5 sao và gửi hình chụp lại, sau đó shop sẽ hoàn tiền 100% và trả thêm 20k hoa hồng. Bạn quan tâm thì ib mình nha, link sản phẩm: http://shopee.vn/fake-product

- **Label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [http://shopee.vn/fake-product, hoàn tiền 100%, ib mình]
- **XAI explanation:** Hãy cẩn thận với các lời mời đánh giá sản phẩm trên Shopee, đặc biệt khi họ hứa hẹn hoàn tiền 100% và yêu cầu bạn ib.
- **Codex judge verdict:** FAIL -- realism=2, label_correctness=5, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:** Literal fake naming exposes synthetic construction and undermines real-world plausibility.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 45/100 -- split=train row_index=676 seed_id=seed_93fafa81260d

> Chào bạn, mình là admin của nhóm TikTok. Mình đang cần người để like, comment các video, mỗi task 10k, thanh toán qua Momo sau khi hoàn thành 10 task. Liên hệ 0987654321 để biết thêm chi tiết nha!

- **Label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [like, comment, 10k, 0987654321]
- **XAI explanation:** Lưu ý: Đừng tin vào các lời mời làm việc trên mạng xã hội với mức lương hấp dẫn mà không cần kinh nghiệm.
- **Codex judge verdict:** PASS -- realism=5, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=4, suspicious_span_accuracy=5
- **Judge reason:** Các hành động, tiền công và số liên hệ đều là cue hữu ích.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 46/100 -- split=train row_index=737 seed_id=seed_bfe4a6bbd16d

> Chào bạn, mình là quản trị viên của nhóm TikTok @tiktok_job. Hiện nhóm đang cần người like, follow, và comment các video để tăng tương tác. Mỗi nhiệm vụ được trả 10k, nếu làm tốt có thể lên đến 200k/ngày. Bạn quan tâm thì add zalo 0978654321 để mình hướng dẫn chi tiết nha. Thử đi, rất dễ kiếm tiền đó!

- **Label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [@tiktok_job, 0978654321]
- **XAI explanation:** Cần cẩn thận với các lời mời tham gia nhóm hoặc trang mạng xã hội hứa hẹn việc làm dễ dàng với thu nhập cao.
- **Codex judge verdict:** FAIL -- realism=5, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=4, suspicious_span_accuracy=2
- **Judge reason:** Contact-only spans miss the impersonation or paid-task lure that makes the message suspicious.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 47/100 -- split=train row_index=739 seed_id=seed_cf2be9f86411

> Xin chào, tôi là quản lý của cửa hàng online. Chúng tôi đang cần người đặt đơn hàng ảo để tăng ranking. Mỗi đơn hàng 200k, bạn sẽ nhận được 10k hoa hồng. Nếu bạn đồng ý, vui lòng chuyển 500k vào tài khoản sau để kích hoạt tài khoản: 123456789. Sau đó, tôi sẽ gửi link đặt hàng.

- **Label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [123456789]
- **XAI explanation:** Đây là một lừa đảo yêu cầu bạn chuyển tiền trước để kích hoạt tài khoản, nhưng sau đó không trả hoa hồng.
- **Codex judge verdict:** FAIL -- realism=5, label_correctness=5, code_switch_naturalness=4, risk_tier_correctness=2, suspicious_span_accuracy=2
- **Judge reason:** Direct payment or credential request is high-risk; suspicious tier is too low.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 48/100 -- split=train row_index=740 seed_id=seed_d41d9b30081a

> Chào bạn, mình là bot từ Binance @binancejob. Bạn có thể đăng ký qua link: https://fakebinance.com và mời bạn bè tham gia. Mỗi lần mời thành công, bạn sẽ nhận được 10% hoa hồng. Gửi OTP để xác nhận tài khoản nha. Đừng quên chia sẻ link này cho bạn bè!

- **Label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [@binancejob, https://fakebinance.com]
- **XAI explanation:** Đây có thể là một chiêu lừa đảo yêu cầu bạn đăng ký và mời người khác vào nền tảng giả mạo, nhưng bạn sẽ không thể rút tiền.
- **Codex judge verdict:** FAIL -- realism=2, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=2, suspicious_span_accuracy=2
- **Judge reason:** Direct payment or credential request is high-risk; suspicious tier is too low.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 49/100 -- split=train row_index=755 seed_id=seed_baafb1055e64

> Xin chào, mình là quản lý nhóm livestream trên Zalo. Chúng tôi cần người tham gia vào nhóm và đặt đơn hàng ảo để tăng tương tác. Mỗi đơn hàng bạn sẽ được trả 30k VND. Hãy tham gia nhóm qua link này: [https://fake-zalo.com/group] và gửi mã đơn hàng cho mình. Để nhận hoa hồng, bạn cần nâng cấp tài khoản bằng cách chuyển 100k VND vào tài khoản ngân hàng sau.

- **Label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [[https://fake-zalo.com/group]]
- **XAI explanation:** Đây là một lừa đảo yêu cầu bạn tham gia nhóm Zalo và đặt đơn hàng ảo, nhưng sau đó bạn sẽ bị yêu cầu chuyển tiền để nâng cấp tài khoản.
- **Codex judge verdict:** FAIL -- realism=2, label_correctness=5, code_switch_naturalness=4, risk_tier_correctness=2, suspicious_span_accuracy=2
- **Judge reason:** Direct payment or credential request is high-risk; suspicious tier is too low.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 50/100 -- split=train row_index=757 seed_id=seed_c6c8772ac332

> Chào bạn, mình là quản lý của một nhóm livestream trên Zalo. Chúng tôi cần người tham gia vào các livestream và thực hiện các hoạt động tương tác. Mỗi hoạt động bạn sẽ được trả 10k. Để bắt đầu, vui lòng chuyển khoản 50k phí nâng cấp tài khoản. Liên hệ qua Zalo 0987654321. Đừng bỏ lỡ cơ hội này!

- **Label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [Zalo 0987654321]
- **XAI explanation:** Cẩn thận với các yêu cầu chuyển khoản phí nâng cấp tài khoản; có thể là lừa đảo.
- **Codex judge verdict:** FAIL -- realism=5, label_correctness=5, code_switch_naturalness=4, risk_tier_correctness=2, suspicious_span_accuracy=2
- **Judge reason:** Direct payment or credential request is high-risk; suspicious tier is too low.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 51/100 -- split=train row_index=798 seed_id=seed_3fb032fa699e

> Chào bạn, tài khoản của bạn vừa nhận được 5.000.000 VND từ chuyển khoản của Nguyễn Văn A. Cảm ơn bạn đã sử dụng dịch vụ của chúng tôi.

- **Label:** benign
- **Risk tier:** benign
- **Suspicious spans:** []
- **XAI explanation:** Thông báo này xác nhận một giao dịch chuyển khoản bình thường vào tài khoản của người dùng.
- **Codex judge verdict:** PASS -- realism=5, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:** Tin báo có tiền vào tài khoản rõ ràng là benign.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 52/100 -- split=train row_index=807 seed_id=seed_6b8624baa879

> Chào bạn, giao dịch chuyển tiền 500.000 VND của bạn từ tài khoản 123456789 đến tài khoản 987654321 đã thành công. Cảm ơn đã sử dụng dịch vụ Internet Banking của chúng tôi.

- **Label:** benign
- **Risk tier:** suspicious
- **Suspicious spans:** []
- **XAI explanation:** Thông báo xác nhận giao dịch chuyển tiền qua Internet Banking, không có dấu hiệu đáng ngờ.
- **Codex judge verdict:** FAIL -- realism=5, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=1, suspicious_span_accuracy=5
- **Judge reason:** Chỉ là xác nhận giao dịch thành công, không đọc như suspicious.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 53/100 -- split=train row_index=817 seed_id=seed_93fafa81260d

> Chào bạn, giao dịch của bạn qua Internet Banking đã thành công. Số tiền: 500.000 VND. Cảm ơn sự ủng hộ của bạn!

- **Label:** benign
- **Risk tier:** suspicious
- **Suspicious spans:** []
- **XAI explanation:** Thông báo xác nhận giao dịch thành công qua Internet Banking với số tiền cụ thể.
- **Codex judge verdict:** FAIL -- realism=5, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=1, suspicious_span_accuracy=5
- **Judge reason:** Xác nhận 500.000 VND không có yếu tố suspicious.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 54/100 -- split=train row_index=842 seed_id=seed_f28d49db789f

> Chào bạn, tài khoản Internet Banking của bạn đã được kích hoạt thành công. Bạn có thể đăng nhập ngay bây giờ.

- **Label:** benign
- **Risk tier:** suspicious
- **Suspicious spans:** []
- **XAI explanation:** Thông báo này xác nhận việc kích hoạt tài khoản Internet Banking, không chứa nội dung đáng ngờ.
- **Codex judge verdict:** FAIL -- realism=5, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=1, suspicious_span_accuracy=5
- **Judge reason:** Kích hoạt Internet Banking không thể hiện nguy cơ hay thúc ép.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 55/100 -- split=train row_index=843 seed_id=seed_f2ad8ed2c10d

> Chào bạn, giao dịch chuyển khoản 2,000,000 VND từ tài khoản của bạn đã được hoàn tất. Số dư hiện tại: 10,500,000 VND. Chi tiết giao dịch: MST: 00123456789, Ngày: 15/10/2023. Cảm ơn bạn đã sử dụng dịch vụ của chúng tôi.

- **Label:** benign
- **Risk tier:** benign
- **Suspicious spans:** []
- **XAI explanation:** Thông báo này xác nhận một giao dịch chuyển khoản đã được thực hiện và cung cấp chi tiết về số dư hiện tại và thông tin giao dịch.
- **Codex judge verdict:** FAIL -- realism=2, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:** Sequential 0123456789 is an obvious placeholder, undermining real-world plausibility.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 56/100 -- split=train row_index=883 seed_id=seed_aecabce08a90

> Chúng tôi xin thông báo rằng dịch vụ Smart OTP sẽ được nâng cấp vào ngày 15/10/2023. Trong thời gian này, bạn vẫn có thể sử dụng dịch vụ bình thường.

- **Label:** benign
- **Risk tier:** benign
- **Suspicious spans:** []
- **XAI explanation:** Thông báo về việc nâng cấp dịch vụ Smart OTP, không yêu cầu hành động cụ thể từ khách hàng.
- **Codex judge verdict:** PASS -- realism=5, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:** Lịch nâng cấp Smart OTP cụ thể và không yêu cầu hành động nguy hiểm.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 57/100 -- split=train row_index=945 seed_id=seed_b6e080de275b

> OTP của bạn là 123456. Vui lòng sử dụng OTP này để xác minh giao dịch trên ứng dụng Internet Banking.

- **Label:** benign
- **Risk tier:** benign
- **Suspicious spans:** []
- **XAI explanation:** Thông báo cung cấp OTP để xác minh giao dịch trên ứng dụng Internet Banking.
- **Codex judge verdict:** PASS -- realism=5, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:** OTP cho ứng dụng Internet Banking là thông báo benign ngắn gọn.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 58/100 -- split=train row_index=979 seed_id=seed_626f3be47e76

> Kính gửi quý khách, số dư tài khoản của bạn hiện tại là 5.000.000 VND. Nếu bạn cần hỗ trợ hoặc có bất kỳ thắc mắc nào, vui lòng liên hệ với chúng tôi qua số hotline 1900 1234.

- **Label:** benign
- **Risk tier:** benign
- **Suspicious spans:** []
- **XAI explanation:** Thông báo số dư tài khoản, không có nội dung gây nghi ngờ hay lừa đảo.
- **Codex judge verdict:** PASS -- realism=5, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:** Thông tin số dư và hotline hỗ trợ đọc tự nhiên.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 59/100 -- split=train row_index=997 seed_id=seed_aecabce08a90

> Tài khoản của bạn hiện có số dư 5,000,000 VND. Chúng tôi khuyên bạn nên kiểm tra tài khoản thường xuyên để đảm bảo an toàn.

- **Label:** benign
- **Risk tier:** benign
- **Suspicious spans:** []
- **XAI explanation:** Thông báo về số dư tài khoản, khuyến nghị kiểm tra tài khoản thường xuyên, không chứa yêu cầu hành động bất thường.
- **Codex judge verdict:** PASS -- realism=5, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:** Số dư và lời khuyên kiểm tra thường xuyên đều an toàn.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 60/100 -- split=train row_index=999 seed_id=seed_b6304b495511

> Mã OTP của bạn để đăng nhập Internet Banking là 123456. Vui lòng không chia sẻ mã này với bất kỳ ai. Hạn sử dụng: 15 phút.

- **Label:** benign
- **Risk tier:** suspicious
- **Suspicious spans:** []
- **XAI explanation:** Thông báo cung cấp mã OTP để đăng nhập, nhắc nhở khách hàng bảo mật, không có nội dung đáng ngờ.
- **Codex judge verdict:** FAIL -- realism=5, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=1, suspicious_span_accuracy=5
- **Judge reason:** Routine in-app OTP guidance is benign, so the suspicious tier is plainly wrong.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 61/100 -- split=train row_index=1121 seed_id=seed_13f16cf56dbe

> Chào bạn, chúng tôi xin gửi đến bạn ưu đãi đặc biệt: giảm 10% cho tất cả các giao dịch thanh toán trực tuyến trong tháng 10. Đừng bỏ lỡ!

- **Label:** benign
- **Risk tier:** benign
- **Suspicious spans:** []
- **XAI explanation:** Thông báo này giới thiệu một ưu đãi giảm giá cho các giao dịch thanh toán trực tuyến, khuyến khích khách hàng sử dụng dịch vụ.
- **Codex judge verdict:** PASS -- realism=5, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:** Ưu đãi thanh toán có thời hạn rõ và không dẫn ngoài.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 62/100 -- split=train row_index=1153 seed_id=seed_a236e34e7773

> Tin nhắn thoại trên Zalo được chép lại: “Con trai của người nhận vừa được đưa vào khoa cấp cứu. Người gửi nói cuộc gọi video chỉ hiện khuôn mặt vài giây rồi mất tiếng. Bệnh viện cần tạm ứng trước khi phẫu thuật. quét mã QR cá nhân để chuyển tiền viện phí. Phải hoàn tất trong mười phút.”

- **Label:** zalo_social_engineering
- **Risk tier:** high-risk
- **Suspicious spans:** [quét mã QR cá nhân để chuyển tiền viện phí]
- **XAI explanation:** Tài khoản tự xưng bác sĩ trực cấp cứu lợi dụng việc bệnh viện cần tạm ứng trước khi phẫu thuật và cuộc gọi video chỉ hiện khuôn mặt vài giây rồi mất tiếng để yêu cầu quét mã QR cá nhân để chuyển tiền viện phí, có thể dẫn đến mất tiền vào tài khoản cá nhân không thuộc bệnh viện.
- **Codex judge verdict:** FAIL -- realism=2, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:** Narrator scaffold describes a scenario rather than an authentic Zalo message.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 63/100 -- split=train row_index=1207 seed_id=seed_8f5da072ee2b

> Trong nhóm Zalo, tài khoản mang tên nhân viên Trung tâm hỗ trợ Zalo đăng “Người dùng nhận cảnh báo tài khoản vừa bị đăng nhập nơi khác. Phiên đăng nhập lạ cần được thu hồi”. Tin nhắn riêng sau đó ghi “nhập số điện thoại và mật khẩu vào trang khôi phục” và “Liên hệ bạn bè sẽ bị xóa sau mười phút”.

- **Label:** zalo_social_engineering
- **Risk tier:** high-risk
- **Suspicious spans:** [nhập số điện thoại và mật khẩu vào trang khôi phục]
- **XAI explanation:** Tài khoản tự xưng nhân viên Trung tâm hỗ trợ Zalo lợi dụng việc phiên đăng nhập lạ cần được thu hồi và tài khoản hỗ trợ giả gửi trang đăng nhập giống Zalo để yêu cầu nhập số điện thoại và mật khẩu vào trang khôi phục, có thể dẫn đến tài khoản Zalo bị chiếm và dùng lừa danh bạ.
- **Codex judge verdict:** FAIL -- realism=2, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:** Narrator scaffold describes a scenario rather than an authentic Zalo message.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 64/100 -- split=train row_index=1228 seed_id=seed_e2773f4d633e

> Tin nhắn thoại trên Zalo được chép lại: “Người lao động được báo còn khoản bảo hiểm chưa nhận. Người gửi nói cuộc gọi Zalo hướng dẫn chia sẻ màn hình từng bước. Ứng dụng định danh cần được kích hoạt lại. mở ứng dụng ngân hàng khi đang chia sẻ màn hình. Hồ sơ sẽ bị trả về nếu thoát cuộc gọi.”

- **Label:** zalo_social_engineering
- **Risk tier:** high-risk
- **Suspicious spans:** [mở ứng dụng ngân hàng khi đang chia sẻ màn hình]
- **XAI explanation:** Tài khoản tự xưng nhân viên bảo hiểm xã hội lợi dụng việc ứng dụng định danh cần được kích hoạt lại và cuộc gọi Zalo hướng dẫn chia sẻ màn hình từng bước để yêu cầu mở ứng dụng ngân hàng khi đang chia sẻ màn hình, có thể dẫn đến thông tin tài chính và mã xác thực bị lộ.
- **Codex judge verdict:** FAIL -- realism=2, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:** Narrator scaffold describes a scenario rather than an authentic Zalo message.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 65/100 -- split=train row_index=1236 seed_id=seed_9040926c38f5

> Cuộc gọi Zalo chỉ kéo dài vài giây. kỹ thuật viên công ty cấp nước gửi tiếp: “Thiết bị cũ bị cho là không đạt kiểm định. Cư dân được báo đồng hồ nước phải thay khẩn. đặt cọc chi phí thay đồng hồ nước; Nếu không đặt lịch hôm nay sẽ bị ngừng cấp nước.”

- **Label:** zalo_social_engineering
- **Risk tier:** high-risk
- **Suspicious spans:** [đặt cọc chi phí thay đồng hồ nước]
- **XAI explanation:** Tài khoản tự xưng kỹ thuật viên công ty cấp nước lợi dụng việc thiết bị cũ bị cho là không đạt kiểm định và lịch hẹn giả được xác nhận bằng ảnh phiếu công tác để yêu cầu đặt cọc chi phí thay đồng hồ nước, có thể dẫn đến mất tiền cọc cho kỹ thuật viên giả.
- **Codex judge verdict:** FAIL -- realism=2, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:** Narrator scaffold describes a scenario rather than an authentic Zalo message.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 66/100 -- split=train row_index=1239 seed_id=seed_3ceb8f4aab76

> Tin Zalo từ dược sĩ của nhà thuốc lớn: “Người mua hỏi thuốc hiếm cho người thân. Kho khác còn đúng một hộp thuốc. đặt cọc toàn bộ tiền thuốc trước khi giao. Có khách khác đang chờ thanh toán.”

- **Label:** zalo_social_engineering
- **Risk tier:** high-risk
- **Suspicious spans:** [đặt cọc toàn bộ tiền thuốc trước khi giao]
- **XAI explanation:** Tài khoản tự xưng dược sĩ của nhà thuốc lớn lợi dụng việc kho khác còn đúng một hộp thuốc và tài khoản giả sao chép ảnh quầy thuốc và phản hồi đánh giá để yêu cầu đặt cọc toàn bộ tiền thuốc trước khi giao, có thể dẫn đến mất tiền cọc và không nhận được thuốc.
- **Codex judge verdict:** FAIL -- realism=2, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:** Narrator scaffold describes a scenario rather than an authentic Zalo message.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 67/100 -- split=train row_index=1294 seed_id=seed_a631c566f8db

> Tin Zalo từ người yêu đang làm việc ở nước ngoài: “Người đang hẹn hò qua mạng nhận tin đối phương gặp nạn. Đối phương bị giữ hộ chiếu và cần tiền luật sư. chuyển tiền cứu trợ qua dịch vụ chuyển tiền quốc tế. Không thể gọi video vì đang ở khu vực an ninh.”

- **Label:** zalo_social_engineering
- **Risk tier:** high-risk
- **Suspicious spans:** [chuyển tiền cứu trợ qua dịch vụ chuyển tiền quốc tế]
- **XAI explanation:** Tài khoản tự xưng người yêu đang làm việc ở nước ngoài lợi dụng việc đối phương bị giữ hộ chiếu và cần tiền luật sư và mối quan hệ được vun đắp nhiều tuần trước khi hỏi tiền để yêu cầu chuyển tiền cứu trợ qua dịch vụ chuyển tiền quốc tế, có thể dẫn đến mất tiền vì quan hệ tình cảm giả.
- **Codex judge verdict:** PASS -- realism=3, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:** Kịch bản tình cảm và tiền cứu trợ hợp lý, dù câu mở đầu hơi khuôn.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 68/100 -- split=train row_index=1312 seed_id=seed_8596de0b7d00

> Trong nhóm Zalo, tài khoản mang tên thư ký hội đồng trao giải đăng “Người dùng được báo số điện thoại trúng chương trình quay thưởng. Giải tiền mặt cần hoàn tất nghĩa vụ thuế”. Tin nhắn riêng sau đó ghi “chuyển thuế giải thưởng trước khi nhận tiền” và “Kết quả sẽ bị hủy nếu tiết lộ cho người khác”.

- **Label:** zalo_social_engineering
- **Risk tier:** high-risk
- **Suspicious spans:** [chuyển thuế giải thưởng trước khi nhận tiền]
- **XAI explanation:** Tài khoản tự xưng thư ký hội đồng trao giải lợi dụng việc giải tiền mặt cần hoàn tất nghĩa vụ thuế và giấy chứng nhận có con dấu giả được gửi qua Zalo để yêu cầu chuyển thuế giải thưởng trước khi nhận tiền, có thể dẫn đến mất tiền cho giải thưởng không tồn tại.
- **Codex judge verdict:** PASS -- realism=3, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:** Bối cảnh Zalo hợp lớp; cụm thuế là substring chính xác và liên quan.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 69/100 -- split=train row_index=1382 seed_id=seed_825b9e38d185

> VPBank Smart OTP: Phiên đăng nhập Internet Banking của bạn được xác nhận lúc 09:15 ngày 16/07/2025 từ thiết bị iPhone 13. Nếu không phải bạn thực hiện, hãy liên hệ ngay 1900 54 54 15 hoặc khóa tài khoản tạm thời qua app VPBank NEO.

- **Label:** benign
- **Risk tier:** benign
- **Suspicious spans:** []
- **XAI explanation:** Thông báo xác nhận đăng nhập Internet Banking kèm thông tin thiết bị từ VPBank. Đây là biện pháp bảo mật chủ động giúp người dùng phát hiện đăng nhập trái phép. Tin nhắn cung cấp hướng dẫn xử lý rõ ràng nếu phát sinh bất thường. Được đánh giá low thay vì safe vì thông báo đăng nhập từ thiết bị cụ thể có thể gây lo ngại nhỏ cho người dùng không quen, nhưng nội dung hoàn toàn hợp lệ và minh bạch.
- **Codex judge verdict:** PASS -- realism=4, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=4, suspicious_span_accuracy=5
- **Judge reason:** Phiên đăng nhập được xác nhận qua kênh chính thức, đọc tự nhiên.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 70/100 -- split=train row_index=1391 seed_id=seed_825b9e38d185

> Agribank thân mến! Thẻ ATM của bạn số ****3421 đã được gia hạn thành công đến 06/2028. Vui lòng đến chi nhánh gần nhất để nhận thẻ mới. Hotline: 1900 558 818.

- **Label:** benign
- **Risk tier:** suspicious
- **Suspicious spans:** []
- **XAI explanation:** Thông báo dịch vụ về việc gia hạn thẻ ATM. Yêu cầu đến chi nhánh trực tiếp là quy trình hợp lệ, không yêu cầu thông tin nhạy cảm qua tin nhắn.
- **Codex judge verdict:** PASS -- realism=4, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=3, suspicious_span_accuracy=5
- **Judge reason:** Thông báo gia hạn và nhận thẻ tại chi nhánh đủ nhạy cảm để cảnh giác.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 71/100 -- split=train row_index=1457 seed_id=seed_825b9e38d185

> Agribank: Sao ke tai khoan thang 06/2025 cua ban da san sang. Vui long dang nhap app Agribank E-Mobile Banking hoac Internet Banking tai agribank.com.vn de xem chi tiet. Hotline: 1900 558 818.

- **Label:** benign
- **Risk tier:** suspicious
- **Suspicious spans:** []
- **XAI explanation:** Thông báo sao kê tài khoản định kỳ từ Agribank. Hướng dẫn người dùng truy cập qua app hoặc website chính thức, không yêu cầu cung cấp thông tin cá nhân. Hoàn toàn lành tính.
- **Codex judge verdict:** FAIL -- realism=4, label_correctness=5, code_switch_naturalness=4, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge reason:** Sao kê qua app hoặc website Agribank không đáng xếp suspicious.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 72/100 -- split=train row_index=1499 seed_id=seed_825b9e38d185

> VCB: Ma OTP cua ban la 847293. Co hieu luc trong 90 giay. Khong cung cap ma nay cho bat ky ai, ke ca nhan vien ngan hang. Neu ban khong thuc hien giao dich nay, vui long goi 1900 545 413 de duoc ho tro.

- **Label:** benign
- **Risk tier:** benign
- **Suspicious spans:** []
- **XAI explanation:** Tin nhắn OTP hợp lệ từ Vietcombank với cảnh báo bảo mật rõ ràng, nhắc người dùng không chia sẻ mã. Có thời hạn hiệu lực ngắn (90 giây) và số hotline chính thức. Đây là mẫu OTP chuẩn của ngân hàng.
- **Codex judge verdict:** PASS -- realism=5, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=3, suspicious_span_accuracy=5
- **Judge reason:** OTP hợp lệ, dù tier benign hơi thấp cho nội dung xác thực.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 73/100 -- split=train row_index=1507 seed_id=seed_825b9e38d185

> Sacombank: Ban vua dang nhap Internet Banking thanh cong luc 10:05 ngay 17/06/2024 tu thiet bi moi. Neu khong phai ban, vui long doi mat khau ngay va lien he 1800 5858 888. Bao mat tai khoan la trach nhiem cua chung ta.

- **Label:** benign
- **Risk tier:** benign
- **Suspicious spans:** []
- **XAI explanation:** Thông báo cảnh báo đăng nhập từ thiết bị mới của Sacombank — đây là tính năng bảo mật chủ động hợp lệ. Được xếp mức low vì cụm từ 'thiết bị mới' có thể tạo cảm giác lo lắng, nhưng nội dung hướng dẫn bảo mật đúng đắn và không yêu cầu cung cấp thông tin nhạy cảm.
- **Codex judge verdict:** PASS -- realism=4, label_correctness=5, code_switch_naturalness=4, risk_tier_correctness=3, suspicious_span_accuracy=5
- **Judge reason:** Đăng nhập từ thiết bị mới hợp lệ nhưng tier benign hơi nhẹ.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 74/100 -- split=train row_index=1509 seed_id=seed_825b9e38d185

> BIDV Smart Banking: Chào mừng bạn đã đăng ký thành công dịch vụ Internet Banking. Hãy tải app BIDV SmartBanking để quản lý tài khoản mọi lúc mọi nơi. Tải tại: App Store hoặc Google Play. Hỗ trợ: 1900 9247.

- **Label:** benign
- **Risk tier:** suspicious
- **Suspicious spans:** []
- **XAI explanation:** Thông báo chào mừng đăng ký dịch vụ Internet Banking từ BIDV. Hướng dẫn tải app từ các kho ứng dụng chính thống (App Store, Google Play) và cung cấp số hotline chính thức. Không có dấu hiệu lừa đảo.
- **Codex judge verdict:** PASS -- realism=4, label_correctness=5, code_switch_naturalness=4, risk_tier_correctness=4, suspicious_span_accuracy=5
- **Judge reason:** Đăng ký Internet Banking là sự kiện đủ nhạy cảm để tier suspicious.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 75/100 -- split=train row_index=1543 seed_id=seed_3f61921e9655

> Kính gửi Quý khách hàng VPBank. Chúng tôi ghi nhận yêu cầu đổi số điện thoại đăng ký. Nếu KO phải bạn, hãy xác nhận ngay: http://vpbk-secure.xyz/cancel?id=VN2024 trước 30 phút nữa kẻo mất quyền truy cập ak.

- **Label:** bank_impersonation
- **Risk tier:** high-risk
- **Suspicious spans:** [http://vpbk-secure.xyz/cancel, vpbk-secure.xyz, trước 30 phút nữa, KO phải bạn]
- **XAI explanation:** Domain '.xyz' và tên miền 'vpbk-secure' không liên quan VPBank (vpbank.com.vn). Deadline 30 phút tạo áp lực click link phishing. Kỹ thuật 'nếu không phải bạn' khiến nạn nhân hoảng sợ và hành động vội vàng.
- **Codex judge verdict:** PASS -- realism=3, label_correctness=5, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=4
- **Judge reason:** Câu kết ak hơi gượng; link giả và hạn ba mươi phút vẫn rõ.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 76/100 -- split=train row_index=1551 seed_id=seed_3f61921e9655

> Chào anh/chị, em là Nguyễn Thị Hoa - nhân viên CSKH Techcombank. Hệ thống ghi nhận tk Internet Banking của anh/chị đang có giao dịch bất thường trị giá 45.000.000đ. Để xác minh và hoàn tiền, anh/chị vui lòng cung cấp:
> 1. Số thẻ
> 2. OTP vừa nhận
> 3. Mã Smart OTP
> 
> Nếu ko phản hồi trong 15 phút, giao dịch sẽ dc tự động duyệt. Liên hệ ngay qua link: https://techcom-hotro.pages.dev

- **Label:** bank_impersonation
- **Risk tier:** high-risk
- **Suspicious spans:** [cung cấp:
1. Số thẻ
2. OTP vừa nhận
3. Mã Smart OTP, https://techcom-hotro.pages.dev, ko phản hồi trong 15 phút, giao dịch sẽ dc tự động duyệt]
- **XAI explanation:** Kẻ lừa đảo giả danh nhân viên CSKH Techcombank yêu cầu cung cấp đồng thời số thẻ, OTP và Smart OTP - ngân hàng thật KHÔNG BAO GIỜ yêu cầu thông tin này qua chat. Domain 'techcom-hotro.pages.dev' dùng dịch vụ hosting miễn phí Cloudflare Pages, không phải domain chính thức techcombank.com.vn. Chiến thuật tạo áp lực thời gian 15 phút là dấu hiệu điển hình của lừa đảo.
- **Codex judge verdict:** PASS -- realism=4, label_correctness=5, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:** Yêu cầu thẻ cùng hai loại OTP để hoàn tiền là phishing rõ.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 77/100 -- split=train row_index=1561 seed_id=seed_3f61921e9655

> Chào anh/chị, em là Nguyễn Linh từ bộ phận Chăm sóc Khách hàng Techcombank. Hệ thống chúng em ghi nhận Internet Banking của anh/chị có dấu hiệu bị truy cập trái phép từ IP nước ngoài lúc 03:47 sáng nay. Để bảo vệ tài khoản, anh/chị vui lòng xác minh danh tính qua link sau trong vòng 15 phút, nếu không hệ thống sẽ tự động tạm khóa: https://techcom-bank-verify.com/auth?token=TK99021. Anh/chị nhập Smart OTP và số thẻ để xác nhận nha. Xin cảm ơn!

- **Label:** bank_impersonation
- **Risk tier:** high-risk
- **Suspicious spans:** [https://techcom-bank-verify.com/auth?token=TK99021, IP nước ngoài lúc 03:47 sáng nay, nhập Smart OTP và số thẻ, hệ thống sẽ tự động tạm khóa]
- **XAI explanation:** Kẻ lừa đảo mạo danh nhân viên Techcombank, dùng tên miền giả 'techcom-bank-verify.com' không thuộc hệ thống chính thức. Yêu cầu nhập Smart OTP và số thẻ qua link bên ngoài là dấu hiệu đánh cắp thông tin. Ngân hàng thật không bao giờ yêu cầu OTP qua link lạ.
- **Codex judge verdict:** PASS -- realism=4, label_correctness=5, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:** Mạo danh CSKH, link giả, thẻ và Smart OTP đều chính xác.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 78/100 -- split=train row_index=1576 seed_id=seed_3f61921e9655

> 【VIETCOMBANK】TK cua ban vua dang nhap tu thiet bi la. De bao mat, xac nhan ngay: http://vcb-secure-login.net/verify hoac goi 1800.9999. Ko xac nhan trong 15p TK se bi khoa!

- **Label:** bank_impersonation
- **Risk tier:** high-risk
- **Suspicious spans:** [http://vcb-secure-login.net/verify, TK cua ban vua dang nhap tu thiet bi la, Ko xac nhan trong 15p TK se bi khoa]
- **XAI explanation:** Tin nhắn giả mạo Vietcombank với domain không chính thức 'vcb-secure-login.net' thay vì 'vietcombank.com.vn'. Thủ thuật tạo áp lực thời gian '15p TK se bi khoa' nhằm khiến nạn nhân hành động vội vàng mà không kiểm tra. Ngân hàng thật không bao giờ gửi link xác minh qua SMS dạng này.
- **Codex judge verdict:** PASS -- realism=4, label_correctness=5, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:** SMS giả VCB với link, hotline lạ và hạn mười lăm phút.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 79/100 -- split=train row_index=1685 seed_id=seed_3f61921e9655

> ⚠️ MBBANK THÔNG BÁO KHẨN: App MBBank của bạn cần cập nhật bảo mật bắt buộc trước 23:59 hôm nay. Nếu ko cập nhật, tài khoản sẽ bị hạn chế giao dịch. Tải bản cập nhật tại đây: https://mbbank-update-2024.pages.dev/download . Nhập Smart OTP để hoàn tất xác thực. Bỏ qua tin nhắn này nếu bạn đã cập nhật.

- **Label:** bank_impersonation
- **Risk tier:** high-risk
- **Suspicious spans:** [https://mbbank-update-2024.pages.dev/download, cập nhật bảo mật bắt buộc trước 23:59 hôm nay, tài khoản sẽ bị hạn chế giao dịch, Nhập Smart OTP để hoàn tất xác thực]
- **XAI explanation:** URL sử dụng dịch vụ hosting miễn phí 'pages.dev' thay vì domain chính thức mbbank.com.vn. Ứng dụng ngân hàng thật được cập nhật qua App Store/CH Play, không qua link lạ. Yêu cầu nhập Smart OTP sau khi tải file có thể dẫn đến chiếm đoạt tài khoản. Deadline giả tạo '23:59 hôm nay' nhằm tạo áp lực thời gian.
- **Codex judge verdict:** PASS -- realism=4, label_correctness=5, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:** Trang tải giả và yêu cầu Smart OTP trước hạn tạo high-risk.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 80/100 -- split=train row_index=1690 seed_id=seed_3f61921e9655

> Kính gửi Quý khách hàng của BIDV,
> 
> Chúng tôi phát hiện thiết bị lạ vừa đăng nhập Smart OTP của bạn từ IP: 103.45.67.89 (Hà Nội). Nếu không phải bạn thực hiện, hãy truy cập ngay:
> 
> 🔗 https://bidv.com.vn-dangnhap-baomat.info/lock
> 
> để khóa thiết bị và bảo vệ account. Sau 30 phút nếu không xác nhận, hệ thống sẽ tự động chuyển tiền theo lệnh đã đặt.
> 
> Trân trọng,
> Bộ phận An ninh mạng BIDV
> Hotline: 1900.8877

- **Label:** bank_impersonation
- **Risk tier:** high-risk
- **Suspicious spans:** [https://bidv.com.vn-dangnhap-baomat.info/lock, bidv.com.vn-dangnhap-baomat.info, IP: 103.45.67.89, hệ thống sẽ tự động chuyển tiền, 1900.8877, Bộ phận An ninh mạng BIDV]
- **XAI explanation:** Tin nhắn giả mạo BIDV với domain cực kỳ nguy hiểm 'bidv.com.vn-dangnhap-baomat.info' - kẻ tấn công chèn 'bidv.com.vn' vào đầu subdomain để đánh lừa người dùng nghĩ đây là trang chính thức. Địa chỉ IP cụ thể tạo cảm giác chuyên nghiệp và đáng tin. Đe dọa 'tự động chuyển tiền' sau 30 phút là chiến thuật gây hoảng loạn điển hình. Hotline 1900.8877 không phải số chính thức của BIDV (1900 9247).
- **Codex judge verdict:** PASS -- realism=3, label_correctness=5, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=4
- **Judge reason:** Logic tự chuyển tiền hơi dựng; tên miền giả và hotline bất thường vẫn rõ.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 81/100 -- split=train row_index=1691 seed_id=seed_3f61921e9655

> ⚠️ BIDV ALERT ⚠️
> TK 9***321 vừa phát sinh GD đáng ngờ: -15,000,000 VND
> Nếu ko phải bạn thực hiện → Bấm HỦY NGAY tại đây ak: bidv-khanghan.vn/huy-gd
> Hoặc gọi bộ phận bảo mật: 024.7300.9988
> Đừng chia sẻ OTP cho bất kỳ ai kể cả nhân viên ngân hàng 🔒

- **Label:** bank_impersonation
- **Risk tier:** high-risk
- **Suspicious spans:** [bidv-khanghan.vn/huy-gd, 024.7300.9988, Đừng chia sẻ OTP cho bất kỳ ai kể cả nhân viên ngân hàng]
- **XAI explanation:** Tin nhắn giả mạo BIDV với tên miền 'bidv-khanghan.vn' không phải bidv.com.vn. Số điện thoại '024.7300.9988' không phải hotline chính thức BIDV (1900 9247). Câu 'đừng chia sẻ OTP' được thêm vào để tạo vẻ tin cậy - đây là thủ thuật phổ biến của lừa đảo tinh vi nhằm hạ thấp cảnh giác trước khi dẫn nạn nhân vào link độc hại.
- **Codex judge verdict:** PASS -- realism=3, label_correctness=5, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=3
- **Judge reason:** Đuôi ak hơi gượng; cảnh báo không chia sẻ OTP là span lành tính.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 82/100 -- split=train row_index=1692 seed_id=seed_3f61921e9655

> Xin chào! Mình là CTV của VPBank. Hiện NH đang có chương trình nâng hạng thẻ tín dụng MIỄN PHÍ cho KH thân thiết. Bạn chỉ cần cung cấp: số thẻ, ngày hết hạn, CVV + mã OTP để xác nhận nâng hạng. Nhanh lên nha, còn 5 suất cuối 😊

- **Label:** bank_impersonation
- **Risk tier:** high-risk
- **Suspicious spans:** [số thẻ, ngày hết hạn, CVV, mã OTP, CTV của VPBank, còn 5 suất cuối]
- **XAI explanation:** Yêu cầu đồng thời số thẻ + CVV + OTP là đủ để thực hiện giao dịch gian lận ngay lập tức. Chiêu 'còn 5 suất' tạo khan hiếm giả. VPBank không có cộng tác viên liên hệ qua WhatsApp để thu thập thông tin thẻ.
- **Codex judge verdict:** PASS -- realism=4, label_correctness=5, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:** CTV giả xin dữ liệu thẻ cùng OTP và dùng khan hiếm giả.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 83/100 -- split=train row_index=1702 seed_id=seed_3f61921e9655

> 【HDBank】 Thông báo bảo mật: Chúng tôi ghi nhận login thất bại 5 lần vào Internet Banking của bạn. Tài khoản sẽ bị khóa sau 10 phút. Xác minh danh tính tại: hd-bank.io/verify?id=VN2024

- **Label:** bank_impersonation
- **Risk tier:** high-risk
- **Suspicious spans:** [hd-bank.io/verify?id=VN2024, login thất bại 5 lần, bị khóa sau 10 phút]
- **XAI explanation:** Giả mạo HDBank với domain '.io' — không phải tên miền ngân hàng Việt Nam (.com.vn). Dùng số liệu cụ thể '5 lần' và countdown '10 phút' để tạo urgency tối đa. Tham số URL 'id=VN2024' tạo cảm giác cá nhân hóa.
- **Codex judge verdict:** PASS -- realism=4, label_correctness=5, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:** Login thất bại, tên miền io và hạn mười phút đúng phishing.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 84/100 -- split=train row_index=1710 seed_id=seed_3f61921e9655

> Chào anh/chị, em là Nguyễn Thị Lan - nhân viên CSKH Techcombank chi nhánh Hà Nội ạ. Hiện tại hệ thống ghi nhận tài khoản của anh/chị đang bị tạm khóa do phát hiện giao dịch đáng ngờ trị giá 47.500.000đ. Để mở khóa ngay, anh/chị vui lòng cung cấp: Số thẻ, ngày hết hạn, và mã OTP được gửi về SĐT đã đăng ký. Hoặc truy cập link xác thực: https://techcom-bank-vn.info/unlock-account để tự xử lý. Nếu không xác thực trong 15 phút tài khoản sẽ bị đóng băng vĩnh viễn. Xin cảm ơn anh/chị đã sử dụng dịch vụ Techcombank!

- **Label:** bank_impersonation
- **Risk tier:** high-risk
- **Suspicious spans:** [https://techcom-bank-vn.info/unlock-account, cung cấp: Số thẻ, ngày hết hạn, và mã OTP, tài khoản sẽ bị đóng băng vĩnh viễn, giao dịch đáng ngờ trị giá 47.500.000đ, trong 15 phút]
- **XAI explanation:** Tin nhắn dài dạng Zalo/Messenger giả mạo nhân viên Techcombank với tên cụ thể tạo cảm giác tin cậy. Domain 'techcom-bank-vn.info' là tên miền giả mạo, không phải techcombank.com.vn. Ngân hàng thực sự KHÔNG BAO GIỜ yêu cầu cung cấp số thẻ, ngày hết hạn và OTP qua chat. Chiến thuật đóng băng tài khoản vĩnh viễn và số tiền cụ thể 47.5 triệu tạo áp lực tâm lý mạnh.
- **Codex judge verdict:** PASS -- realism=4, label_correctness=5, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:** Persona Techcombank xin thẻ, OTP và dẫn URL giả trước hạn.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 85/100 -- split=train row_index=1739 seed_id=seed_157ce0adb043

> Chị ơi e là Lan con dì Hoa đây ạ. E đang ở bệnh viện, mẹ e nhập viện cấp cứu rồi chị ơi 😭 Chị chuyển cho e 5tr trước đi ạ, e chưa rút dc tiền. NH: Techcombank - 9988776655 - Tran Thi Lan. E hoàn lại ngay khi ra viện ạ.

- **Label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [mẹ e nhập viện cấp cứu, chưa rút dc tiền, chuyển cho e 5tr trước, hoàn lại ngay khi ra viện]
- **XAI explanation:** Kẻ gian mạo danh người thân, dùng tình huống y tế khẩn cấp để kích động cảm xúc, viện lý do không rút được tiền để hợp lý hóa yêu cầu chuyển khoản, và hứa hoàn trả để giảm nghi ngờ.
- **Codex judge verdict:** FAIL -- realism=4, label_correctness=2, code_switch_naturalness=5, risk_tier_correctness=5, suspicious_span_accuracy=4
- **Judge reason:** Giả người thân xin viện phí không thuộc task; vài span có thể là yêu cầu thật.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 86/100 -- split=train row_index=1764 seed_id=seed_157ce0adb043

> Bro ơi cứu mình với!! Acc Facebook mình bị hack hết rồi, mình đang nhắn từ Zalo phụ. Mình đang cần nộp tiền học phí gấp trước 5h chiều nay không thì bị đuổi học, thiếu 5tr500k. Mày chuyển tạm cho tao qua MoMo số 0387 654 219 tên Minh Quân đi, tối mình gặp trả liền. Tao đang ở trường ko về đc lấy tiền mặt. Cảm ơn mày nhiều lắm!!

- **Label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [Acc Facebook mình bị hack hết rồi, Zalo phụ, nộp tiền học phí gấp trước 5h chiều nay, bị đuổi học, chuyển tạm cho tao qua MoMo số 0387 654 219, tối mình gặp trả liền, ko về đc lấy tiền mặt]
- **XAI explanation:** Kẻ lừa đảo kết hợp nhiều yếu tố gây áp lực: tài khoản bị hack (giải thích danh tính không xác minh được), deadline cụ thể tạo sự khẩn cấp, lý do hợp lý (học phí), và lý do không thể gặp trực tiếp. Yêu cầu chuyển tiền qua MoMo sang số lạ là phương thức phổ biến trong scam mạo danh bạn bè.
- **Codex judge verdict:** FAIL -- realism=3, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:** Đe đuổi học hơi cường điệu; bản chất là acc phụ mạo danh xin tiền.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 87/100 -- split=train row_index=1781 seed_id=seed_157ce0adb043

> Chị [Lan] ơi! Em là Hương đây ạ, acc Zalo cũ của em bị hack mất r nên em lập cái này. Chị ơi hiện tại em đang cần đóng học phí gấp cho con, ngân hàng app bị lỗi ko chuyển dc. Chị có thể giúp em chuyển tạm 5.500.000đ qua Momo số 0912374856 (Tran Thi Huong) ko ạ? Chiều nay chồng em về em trả liền, em hứa ạ. Em cảm ơn chị nhiều lắm 🙏🙏

- **Label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [acc Zalo cũ của em bị hack mất r nên em lập cái này, ngân hàng app bị lỗi ko chuyển dc, chuyển tạm 5.500.000đ qua Momo số 0912374856, Chiều nay chồng em về em trả liền, em hứa ạ]
- **XAI explanation:** Kẻ lừa đảo giả mạo người quen (Hương) bằng tài khoản Zalo mới lập, viện lý do 'bị hack' để tránh bị đối chiếu. Lý do 'đóng học phí gấp' và 'app ngân hàng bị lỗi' là chiêu tạo áp lực và cản trở nạn nhân tự kiểm tra. Yêu cầu chuyển tiền qua Momo — kênh khó truy vết hơn — với số điện thoại lạ. Cam kết 'trả liền chiều nay' là kỹ thuật tâm lý nhằm vô hiệu hóa sự cảnh giác. Đây là mẫu task_scam mạo danh người thân điển hình.
- **Codex judge verdict:** FAIL -- realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:** Zalo mới xin chuyển MoMo là social engineering rõ.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 88/100 -- split=train row_index=1790 seed_id=seed_157ce0adb043

> Em ơi! Chị là chị Hoa đây, chị đang dùng acc zalo mới vì acc cũ bị hack mất rồi em ạ 😭 Chị đang cần gấp 5 triệu để đóng viện phí cho mẹ, ngân hàng chị đang bị lỗi app Internet Banking ko chuyển dc. Em có thể chuyển giúp chị trước ko, chiều chị thanh toán lại liền. Chuyển vào Momo số 0387xxxxxx tên TRAN THI HOA nha em. Chị cảm ơn em nhiều lắm, tình huống khẩn cấp quá em ơi 🙏

- **Label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [acc zalo mới vì acc cũ bị hack mất rồi, cần gấp 5 triệu, đóng viện phí cho mẹ, app Internet Banking ko chuyển dc, Chuyển vào Momo số 0387xxxxxx, tình huống khẩn cấp quá]
- **XAI explanation:** Tin nhắn sử dụng tài khoản Zalo mới để mạo danh người thân, kết hợp nhiều yếu tố thao túng cảm xúc: (1) Lý do 'acc cũ bị hack' để giải thích tại sao tài khoản không quen thuộc; (2) Khai thác cảm xúc với tình huống 'viện phí cho mẹ' nhằm tạo áp lực đạo đức; (3) Lý do 'app Internet Banking bị lỗi' là cái cớ phổ biến để yêu cầu người khác chuyển thay; (4) Yêu cầu chuyển qua Momo — ví điện tử khó truy vết và hoàn tiền hơn ngân hàng truyền thống; (5) Từ 'khẩn cấp' và emoji 🙏 tạo áp lực tâm lý để nạn nhân hành động nhanh mà không kiểm tra.
- **Codex judge verdict:** FAIL -- realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:** Acc Zalo mới xin viện phí là mạo danh xã hội.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 89/100 -- split=train row_index=1805 seed_id=seed_157ce0adb043

> Tuấn đây mày ơi. Mày nhớ tao ko, hồi cấp 3 cùng lớp 12A2 đó. Tao đang kẹt tiền gấp quá, app Internet Banking tao bị lỗi ko login dc. Mày chuyển giúp tao 2.5k (2 triệu 5) vào Techcombank STK 1903 2281 7764 tên Nguyen Van Tuan đi. Tao Momo lại cho mày liền à, tao có tiền mà app lỗi thôi. OTP tao nhận ko dc nên mới phải nhờ mày.

- **Label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [app Internet Banking tao bị lỗi ko login dc, chuyển giúp tao 2.5k, Techcombank STK 1903 2281 7764, OTP tao nhận ko dc, Tao Momo lại cho mày liền]
- **XAI explanation:** Kẻ lừa đảo giả danh bạn học cũ (tạo sự quen thuộc giả tạo), viện nhiều lý do kỹ thuật như lỗi app, không nhận được OTP để tạo vẻ hợp lý. Cụm 'tao có tiền mà app lỗi thôi' nhằm xóa bỏ nghi ngờ. Yêu cầu chuyển khoản ngân hàng với số tài khoản cụ thể là dấu hiệu scam điển hình.
- **Codex judge verdict:** FAIL -- realism=2, label_correctness=2, code_switch_naturalness=3, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:** Ghi 2.5k rồi giải thích hai triệu rưỡi rất gượng; không có task.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 90/100 -- split=train row_index=1842 seed_id=seed_157ce0adb043

> Alo [Minh] ơi, đây là tài khoản mới của tao, điện thoại cũ bị mất r. Mày đang rảnh ko? Tao đang kẹt tiền gấp lắm, cần mượn 3 triệu để đóng viện phí cho mẹ, mai tao trả liền. Mày chuyển vào STK: 0981234567 Ngân hàng Vietcombank tên NGUYEN VAN MINH nha. Gấp lắm mày ơi, tao cảm ơn nhiều!

- **Label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [tài khoản mới của tao, điện thoại cũ bị mất r, cần mượn 3 triệu để đóng viện phí cho mẹ, mai tao trả liền, STK: 0981234567]
- **XAI explanation:** Tin nhắn mạo danh bạn bè với lý do điện thoại bị mất để giải thích tài khoản lạ. Tạo áp lực khẩn cấp bằng tình huống y tế (viện phí cho mẹ) và hứa hoàn trả ngay hôm sau — đây là kịch bản cổ điển của lừa đảo mượn tiền qua mạng xã hội. Người nhận không thể xác minh danh tính thật của người gửi.
- **Codex judge verdict:** FAIL -- realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:** Tài khoản mới xin viện phí là mạo danh bạn bè, không task.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 91/100 -- split=train row_index=1867 seed_id=seed_157ce0adb043

> Tuấn đây mày! Tao đang ở nước ngoài, SIM ko dùng dc. Mày bank giúp tao 8 triệu gấp nha, tao cần đặt cọc khách sạn. Chuyển vào: Vietinbank - 0398765432 - Lê Minh Tuấn. Mày chuyển xong gửi bill qua đây cho tao. Ko có OTP hay gì đâu mày cứ chuyển thẳng nha. Tao cảm ơn mày nhiều lắm!!!

- **Label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [SIM ko dùng dc, bank giúp tao 8 triệu gấp, Ko có OTP hay gì đâu mày cứ chuyển thẳng, đang ở nước ngoài, gửi bill qua đây]
- **XAI explanation:** Tin nhắn sử dụng kịch bản 'đang ở nước ngoài, mất SIM' để giải thích việc liên lạc qua kênh lạ và không thể xác minh. Câu 'Ko có OTP hay gì đâu mày cứ chuyển thẳng' là dấu hiệu đặc biệt đáng ngờ vì cố tình loại bỏ bước xác thực bảo mật, thúc đẩy nạn nhân chuyển tiền mà không kiểm tra.
- **Codex judge verdict:** FAIL -- realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:** Bạn ở nước ngoài xin cọc khách sạn thuộc social engineering.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 92/100 -- split=train row_index=1905 seed_id=seed_157ce0adb043

> Con ơi đây là má, má đang dùng zalo của dì Hai vì điện thoại má hết pin, sạc bị hỏng. Con chuyển cho má 3 triệu qua Internet Banking gấp nha, má đang ở bệnh viện cần đóng viện phí. Tài khoản: Techcombank - 1122334455 - Phạm Thị Ngọc. Má cần gấp lắm con ơi, đừng gọi lại số này vì dì Hai bận.

- **Label:** task_scam
- **Risk tier:** high-risk
- **Suspicious spans:** [đang dùng zalo của dì Hai vì điện thoại má hết pin, đang ở bệnh viện cần đóng viện phí, chuyển cho má 3 triệu qua Internet Banking gấp, đừng gọi lại số này vì dì Hai bận]
- **XAI explanation:** Đây là biến thể nguy hiểm nhất của scam mạo danh người thân: giả danh cha/mẹ, dùng tình huống bệnh viện để tạo hoảng loạn cảm xúc, và chủ động ngăn nạn nhân xác minh bằng cách yêu cầu 'đừng gọi lại'. Mức độ thao túng tâm lý cao, risk_tier critical.
- **Codex judge verdict:** FAIL -- realism=4, label_correctness=2, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:** Giả mẹ dùng Zalo người khác xin viện phí là social engineering.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 93/100 -- split=val row_index=17 seed_id=seed_af21a1369d7e

> Kính gửi Quý khách hàng BIDV. Chúng tôi ghi nhận giao dịch chuyển khoản 45.000.000 VNĐ từ tài khoản của bạn lúc 11:32. Để hủy giao dịch, nhập OTP xác nhận tại: bidv-cancel-txn.com/verify — Hotline hỗ trợ: 024.3220.1122

- **Label:** bank_impersonation
- **Risk tier:** high-risk
- **Suspicious spans:** [bidv-cancel-txn.com/verify, giao dịch chuyển khoản 45.000.000 VNĐ, Để hủy giao dịch]
- **XAI explanation:** Tin nhắn giả mạo BIDV tạo ra giao dịch chuyển tiền lớn không có thật để dụ nạn nhân nhập OTP vào trang web giả nhằm chiếm quyền kiểm soát tài khoản.
- **Codex judge verdict:** PASS -- realism=5, label_correctness=5, code_switch_naturalness=4, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:** Giao dịch lớn và trang nhập OTP hủy lệnh là high-risk rõ.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 94/100 -- split=val row_index=89 seed_id=seed_af21a1369d7e

> Xin chào, tôi là admin của nhóm Shopee trên Facebook. Chúng tôi đang tìm người để đánh giá 5 sao cho sản phẩm sau khi mua. Bạn sẽ được hoàn lại 100% tiền mua hàng và nhận thêm 20% hoa hồng. Hãy click vào link này để đặt hàng: http://fake-shop.com. Đặt hàng trước 12h hôm nay để nhận ưu đãi nha!

- **Label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [http://fake-shop.com]
- **XAI explanation:** Lưu ý rằng những lời mời đánh giá sản phẩm thường đi kèm với rủi ro không được hoàn tiền hoặc bị lừa đảo.
- **Codex judge verdict:** FAIL -- realism=2, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:** Placeholder/fake token makes this synthetic rather than a real message.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 95/100 -- split=val row_index=100 seed_id=seed_cd2758fc96b9

> Kính gửi quý khách, chúng tôi phát hiện có hoạt động khả nghi trên tài khoản của bạn. Vui lòng cập nhật thông tin bảo mật tại đây [phishing-site.vn] để tránh bị khóa tài khoản. Đừng bỏ qua, nha!

- **Label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [[phishing-site.vn]]
- **XAI explanation:** Không truy cập các liên kết từ email hoặc tin nhắn không rõ nguồn gốc để tránh mất thông tin cá nhân.
- **Codex judge verdict:** FAIL -- realism=2, label_correctness=1, code_switch_naturalness=4, risk_tier_correctness=2, suspicious_span_accuracy=5
- **Judge reason:** Placeholder makes this synthetic; phishing is mislabeled task scam and warrants high-risk.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 96/100 -- split=val row_index=115 seed_id=seed_9ca81c03f7cf

> Xin chào, mình là mod của group Zalo. Cần người tham gia livestream và đặt đơn hàng ảo để tăng tương tác. Mỗi đơn hàng trả hoa hồng 10%, thanh toán qua OTP. Bạn quan tâm thì add Zalo 0987654321 nha. Đảm bảo an toàn, ko lo lừa đảo.

- **Label:** task_scam
- **Risk tier:** suspicious
- **Suspicious spans:** [mod của group Zalo, đặt đơn hàng ảo, thanh toán qua OTP]
- **XAI explanation:** Lừa đảo này thường yêu cầu bạn đặt đơn hàng ảo, sau đó đòi phí nâng cấp tài khoản để tiếp tục nhận hoa hồng.
- **Codex judge verdict:** PASS -- realism=4, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=4, suspicious_span_accuracy=5
- **Judge reason:** Vai mod, đơn ảo và thanh toán OTP đều liên quan trực tiếp.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 97/100 -- split=val row_index=160 seed_id=seed_9ca81c03f7cf

> Kính gửi khách hàng, chúng tôi vừa cập nhật phiên bản mới của ứng dụng di động. Mời bạn tải về phiên bản mới nhất để trải nghiệm các tính năng mới và cải thiện hiệu suất.

- **Label:** benign
- **Risk tier:** suspicious
- **Suspicious spans:** []
- **XAI explanation:** Thông báo cập nhật phiên bản mới của ứng dụng di động với lời mời tải về và trải nghiệm.
- **Codex judge verdict:** FAIL -- realism=5, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=1, suspicious_span_accuracy=5
- **Judge reason:** Mời tải bản ứng dụng mới không thuộc tier suspicious.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 98/100 -- split=val row_index=164 seed_id=seed_c3c238c360c8

> Xin chào, bạn vừa nhận được một mã OTP: 123456 để xác minh đăng nhập vào ứng dụng. Vui lòng không chia sẻ mã này với bất kỳ ai. Nếu bạn không yêu cầu mã này, vui lòng liên hệ bộ phận hỗ trợ ngay lập tức.

- **Label:** benign
- **Risk tier:** benign
- **Suspicious spans:** []
- **XAI explanation:** Thông báo gửi mã OTP để xác minh đăng nhập, hướng dẫn an toàn rõ ràng, không có dấu hiệu lừa đảo.
- **Codex judge verdict:** PASS -- realism=5, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:** OTP đăng nhập có cảnh báo không chia sẻ và liên hệ khi lạ.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 99/100 -- split=val row_index=214 seed_id=seed_1ed2f91485cb

> Cuộc gọi Zalo chỉ kéo dài vài giây. tổng giám đốc doanh nghiệp gửi tiếp: “Nhà cung cấp mới cần được ứng tiền để giữ hợp đồng. Kế toán nhận lệnh kín từ người tự nhận là tổng giám đốc. chuyển gấp tiền công ty vào tài khoản nhà cung cấp mới; Hợp đồng sẽ mất hiệu lực trong ba mươi phút.”

- **Label:** zalo_social_engineering
- **Risk tier:** high-risk
- **Suspicious spans:** [chuyển gấp tiền công ty vào tài khoản nhà cung cấp mới]
- **XAI explanation:** Tài khoản tự xưng tổng giám đốc doanh nghiệp lợi dụng việc nhà cung cấp mới cần được ứng tiền để giữ hợp đồng và người gửi yêu cầu giữ bí mật và không qua quy trình phê duyệt để yêu cầu chuyển gấp tiền công ty vào tài khoản nhà cung cấp mới, có thể dẫn đến thất thoát quỹ doanh nghiệp.
- **Codex judge verdict:** PASS -- realism=3, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:** Câu ghép gượng nhưng lệnh tiền công ty và hạn phút rõ.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---

## Example 100/100 -- split=val row_index=224 seed_id=seed_d8eb5e399eb2

> Cuộc gọi Zalo chỉ kéo dài vài giây. đồng nghiệp cùng dự án gửi tiếp: “Nhóm dự án sắp có cuộc gọi khẩn. Đồng nghiệp nói cần đăng nhập Zalo trên máy họp. quét mã QR đăng nhập Zalo trên thiết bị lạ; Cuộc họp bắt đầu ngay bây giờ.”

- **Label:** zalo_social_engineering
- **Risk tier:** high-risk
- **Suspicious spans:** [quét mã QR đăng nhập Zalo trên thiết bị lạ]
- **XAI explanation:** Tài khoản tự xưng đồng nghiệp cùng dự án lợi dụng việc nhóm dự án sắp có cuộc gọi khẩn và ảnh chụp mã QR đăng nhập được gửi kèm lời nhờ quét hộ để yêu cầu quét mã QR đăng nhập Zalo trên thiết bị lạ, có thể dẫn đến tài khoản Zalo của nạn nhân bị chiếm.
- **Codex judge verdict:** PASS -- realism=3, label_correctness=5, code_switch_naturalness=5, risk_tier_correctness=5, suspicious_span_accuracy=5
- **Judge reason:** Cấu trúc ghép nhưng QR thiết bị lạ và cuộc họp gấp rõ.

**Your verdict:** [ ] PASS   [ ] FAIL

**Notes:** 

---
