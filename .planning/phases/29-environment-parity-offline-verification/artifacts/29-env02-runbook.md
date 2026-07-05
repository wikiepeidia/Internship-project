# ENV-02 Offline Demo Verification Runbook

**Prepared:** 2026-07-05
**Pre-flight doctor:** PASS - `python -m src.runtime.cli doctor` reported `READY backend=gguf local_only=True text_only=True`.
**Source prompts:** `.planning/phases/28-baseline-readiness-zero-code-diagnostics/artifacts/28-golden-prompt-results.json`

## Locked Golden Prompts

### Scam Golden Prompt

**Channel:** `sms`

```text
【VIETCOMBANK】 Tai khoan cua ban vua bi truy cap tu thiet bi la luc 03:47 SA. Neu ko phai ban, bam vao link de khoa ngay: http://vcb-secure-alert.net/lock?id=9182736 hoac goi 1800.9999 (mien phi).
```

Expected result: `high-risk` risk tier with `bank_impersonation` in the threat labels.

### Benign Golden Prompt

**Channel:** `sms`

```text
VPBank Smart OTP: Mã xác thực của bạn là 847291. Mã này có hiệu lực trong 90 giây để xác nhận đăng nhập Internet Banking. Tuyệt đối KHÔNG chia sẻ mã này với bất kỳ ai, kể cả nhân viên ngân hàng.
```

Expected result: `benign` risk tier with `benign` as the only threat label.

## Human Offline Test Steps

1. Open the demo normally with the network still on:

   ```powershell
   vnphish demo
   ```

   Confirm the browser opens and the demo is usable before going offline.

2. Open browser DevTools with `F12`, switch to the Network tab, and enable `Preserve log`.

3. Using Windows Settings -> Network and Internet, turn OFF all of these physical adapter entries: Wi-Fi, Ethernet, and Ethernet 2. After those are off, glance at the same Settings page or tray network icon and confirm Radmin VPN and both VMware virtual adapters are disconnected or no-internet.

4. In the browser, paste the locked scam golden prompt from this runbook, select channel `sms`, and submit. Confirm the result renders `high-risk` and includes `bank_impersonation` in the threat labels.

5. Clear or reset the form, paste the locked benign golden prompt from this runbook, select channel `sms`, and submit. Confirm the result renders `benign` and has `benign` as the only threat label.

6. In the DevTools Network tab, confirm every request targets `127.0.0.1` on the demo port. There must be zero requests to any other host and zero failed/red entries for `fonts.googleapis.com` or `fonts.gstatic.com`.

7. Save a screenshot of the DevTools Network tab here:

   ```text
   .planning/phases/29-environment-parity-offline-verification/artifacts/29-env02-devtools-screenshot.png
   ```

8. Re-enable Wi-Fi and both Ethernet adapters through the same Windows Settings page.

9. Report back with `offline-verified` plus:

   - the exact risk tier and threat labels rendered for the scam prompt;
   - the exact risk tier and threat labels rendered for the benign prompt;
   - confirmation that DevTools showed no non-`127.0.0.1` requests and no failed external font entries;
   - confirmation that the screenshot was saved to the path above;
   - any deviation, such as a wrong verdict, an unexpected external request, or an adapter that would not disable.

