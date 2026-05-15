<!-- markdownlint-disable MD003 MD022 MD036 MD041 MD060 -->

---
phase: 03
slug: local-model-adaptation-and-deployment-paths
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-05-09
---

# Phase 03 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `python -m pytest tests/model_adaptation/test_registry.py tests/model_adaptation/test_pilot.py -q` |
| **Full suite command** | `python -m pytest tests/model_adaptation tests/runtime -q` |
| **Estimated runtime** | ~30 seconds for dry-run and mock-heavy checks |

---

## Sampling Rate

- **After every task commit:** Run the narrowest task-specific pytest command from the active plan.
- **After every plan wave:** Run `python -m pytest tests/model_adaptation tests/runtime -q`
- **Before `/gsd-verify-work`:** Full Phase 3 model-adaptation and runtime-profile suites must be green.
- **Max feedback latency:** 30 seconds for automated checks; hardware smoke checks may be manual.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | MOD-01 | Shared-config drift | Candidate schemas and settings extensions lock the three Qwen checkpoints while preserving the shipped Phase 2 heuristic backend defaults | unit + regression | `python -m pytest tests/model_adaptation/test_schemas.py tests/runtime/test_contracts.py tests/runtime/test_doctor.py tests/runtime/test_cli.py -q` | ❌ W0 | ⬜ pending |
| 03-01-02 | 01 | 1 | MOD-01 | Artifact lineage drift | Local registry persists pilot selections and artifact metadata with checksums and local-only paths | unit | `python -m pytest tests/model_adaptation/test_registry.py -q` | ❌ W0 | ⬜ pending |
| 03-01-03 | 01 | 1 | MOD-01 | Irreproducible selection | Pilot scorecard and baseline-winner/runner-up selection stay deterministic, checksum-backed, and consistent with the locked 4B-primary rule | unit + integration | `python -m pytest tests/model_adaptation/test_pilot.py tests/model_adaptation/test_registry.py -q` | ❌ W0 | ⬜ pending |
| 03-02-01 | 02 | 2 | MOD-01 | Data-format drift | Split-loading and training-example formatting preserve dataset semantics, mixed-language text, and explanation fields | unit | `python -m pytest tests/model_adaptation/test_training.py -q` | ❌ W0 | ⬜ pending |
| 03-02-02 | 02 | 2 | MOD-01 | Training-scope drift | QLoRA training config and dry-run execution are limited to the baseline winner and runner-up | unit | `python -m pytest tests/model_adaptation/test_training.py -q` | ❌ W0 | ⬜ pending |
| 03-02-03 | 02 | 2 | MOD-01 | Operator-flow drift | Model-adaptation CLI exposes pilot/train dry-runs and resolves baseline-winner plus runner-up aliases correctly | unit + dry-run | `python -m pytest tests/model_adaptation/test_cli.py tests/model_adaptation/test_training.py -q` | ❌ W0 | ⬜ pending |
| 03-03-01 | 03 | 3 | RUN-02 | Conversion drift | GGUF conversion produces artifacts for both baseline winner and runner-up with registered metadata | unit | `python -m pytest tests/model_adaptation/test_convert.py -q` | ❌ W0 | ⬜ pending |
| 03-03-02 | 03 | 3 | RUN-02 | Quantization regression | The laptop runtime profile stays pinned to the selected 4B baseline winner, fail-closed, and schema-compatible with the Phase 2 runtime contract | unit + integration | `python -m pytest tests/runtime/test_gguf_backend.py tests/runtime/test_runtime_profiles.py tests/runtime/test_cli.py -q` | ❌ W0 | ⬜ pending |
| 03-04-01 | 04 | 4 | RUN-03 | Backend parity drift | Accelerated local backend returns the same contract shape and explicit profile-selection behavior as the GGUF path | unit + integration | `python -m pytest tests/runtime/test_accelerated_backend.py tests/runtime/test_runtime_profiles.py tests/runtime/test_cli.py -q` | ❌ W0 | ⬜ pending |
| 03-04-02 | 04 | 4 | RUN-03 | Doctor/docs drift | Doctor guidance and local-model documentation stay profile-aware, local-only, and regression-safe under the shipped CLI | integration + docs | `python -m pytest tests/runtime/test_doctor.py tests/runtime/test_runtime_profiles.py tests/runtime/test_cli.py -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/model_adaptation/test_schemas.py` - candidate, artifact, and scorecard DTO validation
- [ ] `tests/model_adaptation/test_registry.py` - manifest/checksum persistence and local-only artifact registration
- [ ] `tests/model_adaptation/test_pilot.py` - three-model pilot selection logic and deterministic winner/runner-up output
- [ ] `tests/model_adaptation/test_training.py` - dry-run training config and adapter-save behavior
- [ ] `tests/model_adaptation/test_convert.py` - GGUF conversion request and artifact metadata behavior
- [ ] `tests/runtime/test_gguf_backend.py` - baseline CPU/iGPU backend contract compatibility
- [ ] `tests/runtime/test_runtime_profiles.py` - explicit backend/profile selection and fail-closed switching
- [ ] `tests/runtime/test_accelerated_backend.py` - optional accelerated profile contract parity and readiness behavior
- [ ] `tests/runtime/test_cli.py` - shipped CLI surface stays stable while service, doctor, and profile logic evolve

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Three-model pilot produces a usable scorecard on the project dataset | MOD-01 | A human should confirm the scorecard is intelligible and the selected winner/runner-up make sense before starting longer training runs | Completed 2026-05-14 with a larger local pilot on 33 balanced validated samples (11 benign, 11 suspicious, 11 high-risk). Result: `qwen3-4b-instruct-2507` locked as laptop baseline winner, `qwen3.5-4b` locked as runner-up, and the saved scorecards live in `D:\PROJEct\AI MODELS\manifests\model-registry.json` plus `data/manifests/phase3-large-pilot-2026-05-14.json`. |
| GGUF baseline works on real laptop hardware | RUN-02 | Mocked tests cannot prove actual local throughput and memory fit on the target class of machine | Run the GGUF profile on the intended laptop baseline, analyze representative suspicious text, and confirm doctor + runtime output stay local-only and contract-compatible |
| Accelerated profile works on stronger hardware without schema drift | RUN-03 | GPU availability and local driver behavior cannot be trusted from mocked CI checks alone | Run the accelerated profile on compatible local hardware and compare the output schema and doctor report against the GGUF baseline |

---

## Validation Sign-Off

- [x] All plans have task-level automated verification commands.
- [x] Sampling continuity: no three consecutive tasks without automated verify.
- [x] Wave 0 covers candidate registry, pilot selection, training dry-run, GGUF baseline, and accelerated profile switching.
- [x] No watch-mode flags.
- [x] Feedback latency target stays under 30 seconds for automated checks.
- [x] `nyquist_compliant: true` set in frontmatter.

**Approval:** pending

<!-- markdownlint-enable MD003 MD022 MD036 MD041 MD060 -->