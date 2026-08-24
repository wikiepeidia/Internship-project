Final Example 001/100 - FAIL (Drop row): Overly casual unnatural tone for a bank notice, bracketed URL syntax artifact ([https://...]), and risk tier mismatch (fake login + account lock warrants high-risk instead of suspicious).

Final Example 002/100 - PASS (Keep): Realistic conversational bank_impersonation scam harvesting OTP under threat of total balance loss; risk tier high-risk is accurate.

Final Example 003/100 - FAIL (Drop row): Unrealistic synthetic premise (bank offering free iCloud accounts); lacks real-world plausibility.

Final Example 004/100 - PASS (Keep): Authentic bank_impersonation transfer-cancellation lure harvesting OTP via fake domain and support contact; correct high-risk tier.

Final Example 005/100 - PASS (Keep): Realistic bank_impersonation Smart OTP expiration lure harvesting CCCD and PIN via malicious URL; correct high-risk tier.

Final Example 006/100 - PASS (Keep): Realistic unaccented bank_impersonation refund scam harvesting 2-sided CCCD and OTP via Zalo; correct high-risk tier.

Final Example 007/100 - PASS (Keep): Valid task_scam with advance deposit demand (200k) and lookalike Zing link; correct high-risk tier.

Final Example 008/100 - FAIL DROP

Final Example 009/100 - FAIL (Drop row): Synthetic bracketed markdown URL formatting artifact ([[http://tiktok-earn.com](http://tiktok-earn.com)]).

Final Example 010/100 - FAIL (Relabel label): Mislabeled as bank_impersonation; relabel to zalo_social_engineering (police authority impersonation credential phishing; keep high-risk).

* **Final Example 011/100** - **PASS (Keep):** Realistic lookalike domain (`vcbank.com.vn`) with account lock urgency; accurate label `bank_impersonation` and `high-risk` tier.
* **Final Example 012/100** - **FAIL, DROP
* **Final Example 013/100** - **PASS (Keep):** Credible bank OTP phishing lure directing to an external site (`verifyotp.com`); accurate label `bank_impersonation` and `high-risk` tier.
* **Final Example 014/100** - **PASS (Keep):** Realistic bank issue lure pushing credentials to a malicious domain (`update-account.com`); accurate label `bank_impersonation` and `high-risk` tier.
* **Final Example 015/100** - **FAIL (Drop row):** Literal synthetic placeholder domain (`binance-fake.com`) undermines real-world plausibility.
* **Final Example 016/100** - **FAIL (Drop row):** Unrealistic synthetic generation template containing bracketed placeholders (`[fake URL]`, `[địa chỉ ví]`, `[số điện thoại]`).
* **Final Example 017/100** - **PASS (Keep):** Realistic low-paid TikTok engagement recruitment with shortened link and Zalo contact; accurate label `task_scam` and `suspicious` tier.
* **Final Example 018/100** - **FAIL (Drop row):** Contains obvious sequential synthetic placeholder phone number (`0123456789`).
* **Final Example 019/100** - **FAIL (Drop row):** Synthetic bracketed text formatting (`[Internet Banking]`) and absurdly implausible reward numbers (850 points = 127 million VND).
* **Final Example 020/100** - **FAIL (Drop row):** Obvious synthetic placeholder artifacts (`[fake-link]` and `[123456]`).
*
* **Final Example 021/100** - **FAIL (Drop row):** Contains an obvious sequential dummy phone number (`0912345678`) and wallet service (ZaloPay) is misaligned with strict bank impersonation.
* **Final Example 022/100** - **FAIL (Drop row):** Non-malicious text that directs the user to the official bank app with no phishing payload, link, or data harvesting, resulting in empty suspicious spans.
* **Final Example 023/100** - **FAIL DROP
* **Final Example 024/100** - **PASS (Keep):** Standard benign bank OTP delivery notification directing users solely to the official app; accurate `benign` label and tier.
* **Final Example 025/100** - **FAIL (Drop row):** Unnatural English-Vietnamese code-switching ("Zalo contact của shop") and sequential synthetic account placeholder (`123456789`).
* **Final Example 026/100** - **FAIL (Drop row):** Obvious synthetic placeholder domain (`example.com`) and sequential dummy account number (`123456789`).
* **Final Example 027/100** - **PASS (Keep):** Realistic bank attack lure soliciting OTP disclosure via phone callback; accurate `bank_impersonation` label and `high-risk` tier.
* **Final Example 028/100** - **PASS (Keep):** Routine benign recruitment invitation directing CV submission to a matching corporate domain; accurate `benign` label and tier.
* **Final Example 029/100** - **PASS (Keep):** Realistic fake livestream order task scam requiring an upfront activation deposit (100k); accurate `task_scam` label and `high-risk` tier.
* **Final Example 030/100** - **PASS (Keep):** Realistic TikTok social interaction task recruitment directing to an external site (`tiktokjobs.vn`); accurate `task_scam` label and `suspicious` tier.
* **Final Example 031/100** - **FAIL drop
* **Final Example 032/100** - *FAIL DROP
* **Final Example 033/100** - **PASS (Keep):** Realistic fake Binance promo scam conditioning referral rewards on an advance $100 wallet deposit; accurate label `task_scam` and `high-risk` tier.but the hostile binance-promo.com domain should be added to spans.
* **Final Example 034/100** - **FAIL (Drop row):** Obvious synthetic placeholder token (`[link]`) undermines realism.
* **Final Example 035/100** - **FAIL (Fix spans):** Keep label `task_scam` and tier `suspicious`, but expand contact-only spans to include task compensation cues ("10k", "200k/ngày").

* **Final Example 036/100** - **FAIL (Drop row):** Obvious synthetic template token (`[zalo-fake-link.com]`).
* **Final Example 037/100** - **FAIL (Fix tier):** Keep label `benign`, but fix risk tier from `suspicious` to `benign` (routine app update announcement without external links).
* **Final Example 038/100** - **FAIL (Fix tier):** Keep label `benign`, but fix risk tier from `suspicious` to `benign` (standard safe in-app transaction notice).
* **Final Example 039/100** - **PASS (Keep):** Routine benign transaction confirmation notice; accurate label `benign` and `benign` tier.
* **Final Example 040/100** - **FAIL (Fix tier):** Keep label `benign`, but fix risk tier from `suspicious` to `benign` (routine account update confirmation).
* **Final Example 041/100** - **PASS (Keep):** Standard benign in-app transaction OTP delivery SMS; accurate label `benign` and `benign` tier.
* **Final Example 042/100** - **FAIL (Fix tier):** Keep label `benign`, but fix risk tier from `suspicious` to `benign` (routine official Smart OTP system upgrade announcement).
* **Final Example 043/100** - **FAIL DROP:** Trash message but correct tier also AI explaination is grabage
* **Final Example 044/100** - **FAIL (Fix tier):** Keep label `benign`, but fix risk tier from `suspicious` to `benign` (routine mobile app update notice without external links).
* **Final Example 045/100** - **PASS (Keep):** Standard benign balance notice with official support advisory; accurate label `benign` and `benign` tier.
* **Final Example 046/100** - **PASS (Keep):** Realistic emergency medical deposit pressure via QR code transfer; accurate label `zalo_social_engineering` and `high-risk` tier.
* **Final Example 047/100** - **FAIL (Drop row):** Contradictory and illogical condition phrasing ("nếu không gửi OTP thì hồ sơ hoàn tiền sẽ được duyệt") undermines realism.
* **Final Example 048/100** - **PASS (Keep):** Realistic utility disconnection pressure scam redirecting payment via fake QR code; accurate label `zalo_social_engineering` and `high-risk` tier.
* **Final Example 049/100** - **PASS (Keep):** Realistic rare medicine scarcity scam demanding full upfront payment; accurate label `zalo_social_engineering` and `high-risk` tier.
* **Final Example 050/100** - **PASS (Keep):** Realistic hotel booking modification scam soliciting an urgent extra deposit; accurate label `zalo_social_engineering` and `high-risk` tier.
* **Final Example 051/100** - **FAIL (Relabel label):** Mislabeled as `task_scam`; relabel to `zalo_social_engineering` (friend impersonation money mule scam with commission lure; keep `high-risk`).
* **Final Example 052/100** - **PASS (Keep):** Realistic VPBank CSKH impersonation harvesting Smart OTP via a malicious URL; accurate label `bank_impersonation` and `high-risk` tier.
* **Final Example 053/100** - **FAIL (Drop row):** Contains obvious sequential synthetic phone placeholder (`0123456789`), generic "ngân hàng XYZ", and risk tier mismatch (direct OTP solicitation requires `high-risk`).
* **Final Example 054/100** - **PASS (Keep):** Realistic TikTok engagement recruitment task scam with a shortened URL; accurate label `task_scam` and `suspicious` tier.
* * **Final Example 055/100** - **FAIL (Drop row):** Contradictory mix of benign in-app OTP instruction with obvious synthetic dummy placeholders (`0987654321` and `123456`).
* **Final Example 056/100** - **FAIL (Drop row):** Synthetic placeholder path token (`fakeoffer`) in the URL undermines real-world realism.
* **Final Example 057/100** - **FAIL (Drop row):** Synthetic sequential placeholder phone number (`0987654321`) and unnatural self-identification as a bot.
* **Final Example 058/100** - **FAIL DROP
* **Final Example 059/100** - **FAIL DROP
* **Final Example 060/100** - **FAIL (Drop row):** Obvious synthetic placeholder domain (`fake-shopee-link.com`) and sequential phone number (`0912345678`).
* **Final Example 061/100** - **FAIL (Drop row):** Contains obvious sequential synthetic placeholder bank account (`0987654321012345`).
* **Final Example 062/100** - **PASS (Keep):** Standard benign bank transfer confirmation notice; accurate label `benign` and `benign` tier.
* **Final Example 063/100** - **PASS (Keep):** Realistic Vietcombank foreign-login phishing alert with fake domain; accurate label `bank_impersonation` and `high-risk` tier.
* **Final Example 064/100** - **FAIL (Drop row):** Obvious synthetic placeholder bracket token (`[hệ thống sẽ gửi riêng]`) undermines realism.
* **Final Example 065/100** - **PASS (Keep):** Realistic MB Bank loyalty lottery phishing lure using lookalike domain; accurate label `bank_impersonation` and `high-risk` tier.
* **Final Example 066/100** - **PASS (Keep):** Standard benign e-commerce purchase OTP delivery notification; accurate label `benign` and `benign` tier.
* **Final Example 067/100** - **FAIL (Drop row):** Obvious synthetic bracketed placeholder (`[fake-url.com]`) and dummy contact number (`0987654321`).
** **Final Example 068/100** - **PASS (Keep):** Benign security recommendation directing the user solely to the official app without external links or credential harvesting; accurate label `benign` and `benign` tier.
* **Final Example 069/100** - **FAIL DROP.
* **Final Example 070/100** - **FAIL (Drop row):** Illogical premise ("nhận được chuyển tiền" contradicts "nếu không thực hiện giao dịch") and contains a sequential placeholder account (`123456789`).
* **Final Example 071/100** - **PASS (Keep):** Realistic food delivery refund social engineering lure demanding screen sharing and verification code; accurate label `zalo_social_engineering` and `high-risk` tier.
* **Final Example 072/100** - **PASS (Keep):** Authentic telecom technician impersonation for SIM-swap OTP theft under urgency; accurate label `zalo_social_engineering` and `high-risk` tier.
* **Final Example 073/100** - **PASS (Keep):** Realistic lost property return lure soliciting citizen ID and selfie photos; accurate label `zalo_social_engineering` and `high-risk` tier.
* **Final Example 074/100** - **PASS (Keep):** Realistic Agribank credential phishing SMS using a bit.ly link under account lockout threat; accurate label `bank_impersonation` and `high-risk` tier.
* **Final Example 075/100** - **PASS (Keep):** Authentic fake collaborator phishing lure harvesting ID, selfie, and login credentials via Firebase dynamic link; accurate label `bank_impersonation` and `high-risk` tier.
* **Final Example 076/100** - **FAIL (Drop row):** Unrealistic synthetic text containing the literal self-exposing phrase "hotline gia mao" (fake hotline).
* **Final Example 077/100** - **FAIL (Fix tier):** Keep label `benign`, but fix risk tier from `suspicious` to `benign` (standard official e-statement summary).
* **Final Example 078/100** - **FAIL DROP because i am sure this message is a damn narrator
* **Final Example 079/100** - **PASS (Keep):** Standard legitimate bank marketing notification directing to official app and hotline; accurate label `benign` and `benign` tier.
** **Final Example 080/100** - **FAIL (Drop row):** Contains an obvious sequential synthetic placeholder bank account (`1234567890123456`) and risk tier mismatch (10% balance transfer demand requires `high-risk` tier).
* **Final Example 081/100** - **FAIL DROP
* **Final Example 082/100** - **PASS (Keep):** Standard e-commerce review task scam demanding an advance fee deposit (200k); accurate label `task_scam` and `high-risk` tier.
* **Final Example 083/100** - **PASS (Keep):** Standard legitimate ABBank time-limited login OTP notification; accurate label `benign` and `benign` tier.
* **Final Example 084/100** - **PASS (Keep):** Unsolicited referral promotion linking to the legitimate official Binance domain; acceptable as `benign` under `suspicious` tier.
* **Final Example 085/100** - **FAIL (Fix spans):** Keep label `task_scam` and tier `suspicious`, but expand contact-only spans to include task and reward cues ("10k", "like, follow và comment").
* **Final Example 086/100** - **FAIL (Fix tier):** Keep label `benign`, but fix risk tier from `suspicious` to `benign` (standard official scheduled maintenance notice).
* **Final Example 087/100** - **PASS (Keep):** Realistic missing-vote pretext soliciting an urgent QR code scan under a 10-minute timer; accurate label `zalo_social_engineering` and `high-risk` tier.
* **Final Example 088/100** - **FAIL (Drop row):** Synthetic unaccented text containing obvious dummy placeholders (`123456` and `0987654321`).
* **Final Example 089/100** - **FAIL (Fix spans):** Keep label `task_scam` and tier `suspicious`, but expand spans to include task engagement cues ("5k", "like, follow, và comment") instead of neutral "Momo".
* **Final Example 090/100** - FAIL—relabel to benign, retain suspicious; it describes affiliate recruitment without a fraudulent task/payment mechanism.
* **Final Example 091/100** - **FAIL (Drop row):** Directs users solely to the official MB app without an external link or credential-harvesting payload, resulting in empty suspicious spans.
* **Final Example 092/100** - **PASS (Keep):** Realistic ACB lookalike domain phishing lure (`acb-bank-login.com`) with an urgent account lockout threat; accurate label `bank_impersonation` and `high-risk` tier.
* Final Example 093/100 - PASS (Keep): Standard TikTok paid-engagement recruitment lure directing users to an external registration domain; accurate label task_scam and suspicious tier.

Final Example 094/100 - PASS (Keep): Realistic BIDV system upgrade phishing lure linking to an unauthorized .info domain; accurate label bank_impersonation and high-risk tier.

Final Example 095/100 - FAIL (Drop row): Literal synthetic placeholder domain (fakebinance.com) undermines real-world plausibility.

Final Example 096/100 - FAIL (Drop row): Obvious synthetic placeholder OTP (123456) and contradictory text instructing the victim to input OTP into their own app without an exfiltration channel.

Final Example 097/100 - PASS (Keep): Standard benign Internet Banking transfer confirmation; accurate label benign and benign tier.

Final Example 098/100 - FAIL (Fix tier): Keep label benign, but fix risk tier from suspicious to benign (routine balance alert; opening "Thư ngỏ:" is also slightly unnatural).

Final Example 099/100 - PASS (Keep): Standard benign account balance notification with official support advice; accurate label benign and benign tier.

Final Example 100/100 - FAIL (Drop row): Literal synthetic placeholder domain (binance-fake.com) undermines real-world plausibility.
