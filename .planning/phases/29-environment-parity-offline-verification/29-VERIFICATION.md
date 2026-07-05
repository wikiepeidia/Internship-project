---
phase: 29-environment-parity-offline-verification
status: passed
verified: 2026-07-05T21:36:00+07:00
plans: [29-01, 29-02, 29-03, 29-04]
requirements: [ENV-01, ENV-02, ENV-03, ENV-04, ENV-05]
commits: [e38d2d5, 45beca3, 141544d, d677559, f54a30b, 26bc604, 3843f9d, 14cfe37, f3c1772, 6c34e4d]
score: 5/5 must-haves verified
---

# Phase 29 Verification

**Verdict:** PASS

## Goal Achievement

Phase 29 verified that the presentation-laptop demo environment is ready for local/offline use: the runtime reports READY, model paths are persisted as OS-level environment variables, the GGUF dependency is exact-pinned, Be Vietnam Pro is self-hosted, and the real browser demo completed the two locked golden prompts with physical network adapters disabled.

## Observable Truths

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | `vnphish doctor` reports READY on the presentation laptop. | VERIFIED | `29-env01-env05-evidence.md` records `READY backend=gguf local_only=True text_only=True`; post-offline `29-env02-offline-results.md` records the same after network restoration. |
| 2 | Demo font assets are self-hosted and no Google Fonts CDN dependency remains. | VERIFIED | `29-01-SUMMARY.md` records 12 vendored WOFF2 files, 12 local `@font-face` rules, and a sweep showing no `fonts.googleapis.com` / `fonts.gstatic.com` references. |
| 3 | `MODEL_ARTIFACT_ROOT` and `MODEL_REGISTRY_PATH` persist as OS-level user environment variables. | VERIFIED | `29-env04-evidence.md` records `setx`/registry proof and a fresh-terminal `vnphish doctor` run from `C:\`. |
| 4 | `llama-cpp-python` is exact-pinned to the validated version `0.3.23`. | VERIFIED | `29-02-SUMMARY.md` records the `pyproject.toml` exact pin and installed-version confirmation. |
| 5 | With network disabled, the real web demo renders the locked scam prompt as `high-risk` + `bank_impersonation` and the locked benign prompt as `benign` + `benign`, with no app/backend external request observed. | VERIFIED | `29-env02-offline-results.md` records the human offline run; `29-env02-devtools-screenshot.png` provides DevTools evidence. |

**Score:** 5/5 truths verified

## Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `artifacts/29-env02-runbook.md` | Human offline runbook with exact locked prompts | VERIFIED | Contains the Vietcombank scam and VPBank Smart OTP benign prompts copied from Phase 28 JSON, plus all 9 human steps. |
| `artifacts/29-env02-offline-results.md` | Final ENV-02 evidence record | VERIFIED | Records both offline verdicts, screenshot path, post-test doctor READY, and evidence deviations. |
| `artifacts/29-env02-devtools-screenshot.png` | DevTools Network screenshot | VERIFIED | Present on disk, 68,206 bytes. Shows no app/backend external host or Google Fonts request; browser-extension stylesheet noise is documented. |
| `artifacts/29-env04-evidence.md` | Permanent model env-var proof | VERIFIED | Records HKCU environment values and fresh-terminal runtime proof. |
| `src/runtime/demo_assets/fonts/*.woff2` | Self-hosted Be Vietnam Pro assets | VERIFIED | 12 WOFF2 files created and covered by demo route tests. |

## Behavioral Spot-Checks

| Check | Command / Evidence | Result | Status |
| --- | --- | --- | --- |
| Doctor readiness | `python -m src.runtime.cli doctor` | Exit 0, `READY backend=gguf local_only=True text_only=True` | PASS |
| Demo route/font regression | `python -m pytest tests\runtime\test_demo.py -x` | 7 passed during 29-01 execution | PASS |
| Local-model helper regression | `python -m pytest tests\runtime\test_local_model.py -q` | 19 passed after benign-copy fix | PASS |
| Offline scam verdict | Human offline run | `high-risk`, `bank_impersonation` | PASS |
| Offline benign verdict | Human offline run | `benign`, `benign` | PASS |
| DevTools external dependency check | `29-env02-devtools-screenshot.png` | No Google Fonts or app/backend non-loopback request observed | PASS_WITH_NOISE |

## Requirements Coverage

| Requirement | Status | Evidence |
| --- | --- | --- |
| ENV-01 | SATISFIED | `29-env01-env05-evidence.md`; post-offline doctor output in `29-env02-offline-results.md`. |
| ENV-02 | SATISFIED | Human offline run, screenshot artifact, and final evidence record. |
| ENV-03 | SATISFIED | Self-hosted font assets and demo route/CDN-removal tests in `29-01-SUMMARY.md`. |
| ENV-04 | SATISFIED | Registry and fresh-terminal env-var proof in `29-env04-evidence.md`. |
| ENV-05 | SATISFIED | Exact `llama-cpp-python==0.3.23` pin and installed-version confirmation in `29-02-SUMMARY.md`. |

## Deviations and Watchpoints

| Item | Status | Notes |
| --- | --- | --- |
| Browser-extension stylesheet entries in DevTools | ACCEPTED | Screenshot shows three `about:client`-initiated CSS entries consistent with extension/content-script noise. They are not demo app/backend traffic and do not affect the offline dependency claim. |
| `ERROR SOURCE_LANG_VI` console warning | ACCEPTED WATCHPOINT | User reported the warning during offline run; source search found no matching local runtime/frontend key. Carry to Phase 31 if console polish is in scope. |
| Awkward benign OTP recommendation copy | FIXED | `f3c1772` improved the fallback copy and added a regression assertion. |

## Human Verification Required

None remaining for Phase 29. The human offline checkpoint was completed and recorded.

## Gaps Summary

No blocking Phase 29 gaps remain. Phase 30 can start cold/warm latency diagnosis on the now-verified presentation-laptop environment.

---

_Verified: 2026-07-05T21:36:00+07:00_
_Verifier: Codex inline verifier with human offline evidence_

