# Phase 32 Fallback Operator Checklist

Use this checklist for the manual fallback assets. The automated dry-run can prove the final launcher starts and the locked prompts still classify correctly, but it does not create the human fallback recording, the secondary screenshot package, or the live-to-fallback rehearsal.

## Locked Golden Prompts

### Scam prompt

Channel: `sms`

```text
【VIETCOMBANK】 Tai khoan cua ban vua bi truy cap tu thiet bi la luc 03:47 SA. Neu ko phai ban, bam vao link de khoa ngay: http://vcb-secure-alert.net/lock?id=9182736 hoac goi 1800.9999 (mien phi).
```

Expected verdict: non-benign / `high-risk`, with `bank_impersonation`.

### Benign prompt

Channel: `sms`

```text
VPBank Smart OTP: Mã xác thực của bạn là 847291. Mã này có hiệu lực trong 90 giây để xác nhận đăng nhập Internet Banking. Tuyệt đối KHÔNG chia sẻ mã này với bất kỳ ai, kể cả nhân viên ngân hàng.
```

Expected verdict: `benign`, with only `benign`.

## FB-01 Recording

- [ ] Launch the demo with `scripts/START_DEMO_UI.bat`.
- [ ] Start screen recording with your chosen local recorder.
- [ ] Submit the scam prompt and show the expected verdict.
- [ ] Submit the benign prompt and show the expected verdict.
- [ ] Save the video in local copy 1: `____________________________`.
- [ ] Save the video in local copy 2: `____________________________`.
- [ ] Confirm both files open locally before the defense.

## FB-02 Screenshot Sequence

- [ ] Capture launcher/demo-ready screen.
- [ ] Capture scam prompt before submission.
- [ ] Capture scam result showing `high-risk` / `bank_impersonation`.
- [ ] Capture benign prompt before submission.
- [ ] Capture benign result showing `benign`.
- [ ] Save screenshot folder/path: `____________________________`.

## FB-03 Pivot Rehearsal

Short script:

1. Say the live demo is unavailable or taking too long.
2. Switch immediately to the saved recording.
3. If video playback fails, switch to the screenshot sequence.
4. Narrate that the fallback shows the same two locked prompts as the planned live demo.

Evidence:

- [ ] Pivot rehearsed at least once.
- [ ] Fallback recording path opened successfully.
- [ ] Screenshot sequence path opened successfully.
- [ ] Notes/issues: `____________________________`.

## FB-04 Substitute Caveat

The automated Phase 32 dry-run is not a literal cold boot. It is a fresh-process proxy that starts a new demo process through `scripts/START_DEMO_UI.bat` and verifies the two locked prompts. It does not cover OS startup, driver reinitialization, OneDrive sync catch-up after power-on, or Windows Defender first-run scanning.

