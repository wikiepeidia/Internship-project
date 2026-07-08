# Phase 31 Plan 03: Final D-05 Regression Evidence

**Recorded:** 2026-07-08
**Scope:** Re-run Phase 28's golden-prompt stability check and Phase 29's touched test suites after Plan 31-01's real-demo verifier fixture, Plan 31-02's CLI help/launcher additions, and this plan's Task 1 `demo.js` double-submit fix — confirming none of Phases 28-30's work regressed.

## 1. Golden-prompt regression (5 scam + 5 benign runs)

**Command:**

```
python -c "
import importlib.util, pathlib
spec = importlib.util.spec_from_file_location('verify_golden_prompts', pathlib.Path('scripts/verify_golden_prompts.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.RESULTS_PATH = pathlib.Path('.planning/phases/31-ui-quirks-edge-cases-regression-re-check/artifacts/31-golden-regression-results.json')
raise SystemExit(module.main(['--runs', '5', '--port', '8766']))
"
```

**Exit code:** 0

**Output artifact:** `.planning/phases/31-ui-quirks-edge-cases-regression-re-check/artifacts/31-golden-regression-results.json` (the Phase 28 source artifact `28-golden-prompt-results.json` was not touched — `RESULTS_PATH` was redirected before `main()` ran).

**Scam verdict — stable:**

| Run | risk_tier | threat_labels | latency_ms |
|-----|-----------|----------------|------------|
| 1 | high-risk | bank_impersonation | 21821.6 |
| 2 | high-risk | bank_impersonation | 17574.8 |
| 3 | high-risk | bank_impersonation | 17067.4 |
| 4 | high-risk | bank_impersonation | 17753.4 |
| 5 | high-risk | bank_impersonation | 18113.6 |

`golden_scam.stable = true` — 5/5 runs agree on `high-risk` / `bank_impersonation`, matching the Phase 28-locked no-OTP malicious-link Vietcombank scam verdict.

**Benign verdict — stable:**

| Run | risk_tier | threat_labels | latency_ms |
|-----|-----------|----------------|------------|
| 1 | benign | benign | 21549.1 |
| 2 | benign | benign | 18333.8 |
| 3 | benign | benign | 15909.2 |
| 4 | benign | benign | 16792.3 |
| 5 | benign | benign | 16254.99 |

`golden_benign.stable = true` — 5/5 runs agree on `benign` / `benign`, matching the Phase 28-locked VPBank Smart OTP benign verdict.

Both `stable` booleans are `true` in the artifact, confirming the 2 runtime bugs fixed in Phase 28 (legitimate-OTP-as-benign, no-OTP-link-based scam detection) are still correctly handled after Phase 29's font-route/env-var changes and this plan's `demo.js` fix.

## 2. Focused runtime/CLI pytest suites

**Command:**

```
python -m pytest tests/runtime/test_local_model.py tests/runtime/test_demo.py tests/runtime/test_cli.py -q
```

**Exit code:** 0

**Result:** `39 passed in 0.17s` — full pytest pass, zero failures, zero skips, across the local-model analyzer suite, the demo WSGI/static-contract suite, and the CLI help/launcher suite (all three touched by Phase 29 and/or Phase 31).

## 3. Doctor readiness

**Command:**

```
python -m src.runtime.cli doctor
```

**Exit code:** 0

**Output:** `READY backend=gguf local_only=True text_only=True` — every doctor check (`python-version`, `import:ftfy`, `import:pydantic`, `import:pydantic_settings`, `settings-load`, `runtime-backend`, `runtime-profile`, `runtime-max-cues`, `runtime-fail-closed`, `runtime-store-raw-text`, `backend-ready`, `release-gate-summary`) reports `PASS`.

## 4. Phase 30 latency note

Phase 30 (Latency Diagnosis & Targeted Fix) closed with decision **`NO_FIX_APPLIED`** (`.planning/phases/30-latency-diagnosis-targeted-fix/artifacts/30-fix-decision.md`, confirmed in `30-02-SUMMARY.md`): no source changes were made to `src/runtime/analyzers/gguf.py` or any other runtime file. There is therefore no Phase 30 source diff to regression-test beyond confirming the demo still starts and serves correctly — which this run's golden-prompt regression (Section 1, real `vnphish demo` subprocess, 10 total real requests) and doctor readiness (Section 3) both confirm.

## Summary

| Check | Command | Exit code | Result |
|-------|---------|-----------|--------|
| Golden-prompt regression | `verify_golden_prompts.py --runs 5 --port 8766` (redirected `RESULTS_PATH`) | 0 | scam stable=true, benign stable=true |
| Focused pytest | `pytest tests/runtime/test_local_model.py tests/runtime/test_demo.py tests/runtime/test_cli.py -q` | 0 | 39 passed |
| Doctor | `python -m src.runtime.cli doctor` | 0 | READY backend=gguf local_only=True text_only=True |
| Phase 30 regression scope | n/a | n/a | `NO_FIX_APPLIED` — no source diff beyond demo startup/serving, covered above |

All D-05 regression checks pass. No model thresholds, golden prompt texts, backend service code, or test expectations were altered to force a pass.
