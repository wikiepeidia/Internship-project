# Phase 7a: task_scam Recall Recovery - Context

**Gathered:** 2026-05-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix the `task_scam` recall gap exposed by Phase 7 holdout evaluation. The current model achieves recall=0.44 against a target of ≥0.80. This phase audits existing training data, strengthens generation prompts, generates targeted new samples, retrains on Colab H100, and re-runs the held-out evaluation with a fixed gate. Thesis writing (Phase 8) is blocked until this phase closes with a PASS verdict.

**Scope guardrails:**

- Only fix `task_scam` recall — do not reopen `bank_impersonation` or `zalo_social_engineering` (already at 0.98 and 0.99).
- Keep the locked model: `qwen3-4b-instruct-2507 / baseline-winner`.
- Keep the locked dataset lineage: `data/synthetic/recovered-balanced.jsonl` (append only, no new lineage).
- Keep the locked split root: `data/splits/recovered-balanced/`.
- Do not rebuild Phase 5 evaluation artifacts that are still correct — only regenerate the snapshot and release-eval after retraining.
- Fix the gate bug in this phase; it blocks honest reporting.

</domain>

<decisions>
## Implementation Decisions

### Recall Target

- **D-01:** The recall target for `task_scam` is relaxed to **≥0.80** (down from the original 0.90 floor). `bank_impersonation` and `zalo_social_engineering` keep their 0.90 floors. Rationale: `task_scam` is linguistically closer to benign text and harder to separate; 0.80 is the honest achievable target given the class difficulty.
- **D-02:** The Phase 5 release gate code must be patched to enforce per-label recall floors correctly. The current bug: `audit.ready = true` and `blocker_reasons = []` even when `task_scam` recall is 0.44. The fix must make the gate produce `BLOCK` when any risky label's recall is below its floor.
- **D-03:** After the gate fix, re-run `evaluate-release-split` and `release-eval` against the new trained model. The phase closes when the release verdict is PASS.

### Data Strategy

- **D-04:** Audit the existing 750 `task_scam` samples from `data/synthetic/recovered-balanced.jsonl` first. Sample 30-50 examples and assess: are they linguistically distinct from benign? Are they diverse in scenario type (platform, job type, pay structure)?
- **D-05:** Based on the audit finding, generate targeted new task_scam rows. If existing samples are too similar or scenario coverage is narrow, generate 200 diverse new samples. If they are already well-distributed, generate fewer (50-100) with richer prompts.
- **D-06:** Strengthen the task_scam generation prompt in `src/data_pipeline/generation/prompts.py`. The new prompt must explicitly enumerate scenario diversity axes: part-time social media tasks (like/follow/comment farms), review-bombing on Shopee/Lazada, crypto referral schemes, online shop seeding (fake purchases), Zalo/Telegram livestream engagement tasks. Each scenario should have a distinctive trust-then-disappear or pay-after-task structure.
- **D-07:** Append new task_scam rows to `data/synthetic/recovered-balanced.jsonl` and rebuild splits at `data/splits/recovered-balanced/` using the existing split CLI. Keep the same 80/10/10 split ratio and seed-grouping logic.

### Colab Training Workflow

- **D-08:** Use Google Colab H100 for the retrain. Expected runtime: ~15 minutes (vs 8-9 hours on laptop GPU). The existing `src.model_adaptation.cli train` command works as-is on Colab — no script changes needed.
- **D-09:** Workflow sequence: (1) generate new data locally → (2) rebuild splits → (3) upload `data/splits/recovered-balanced/train.jsonl` and `val.jsonl` + the `src/` package to Colab → (4) run `train` command → (5) download adapter directory → (6) register adapter in off-repo model registry → (7) run `convert` command locally → (8) run `evaluate-release-split` → (9) run `release-eval`.
- **D-10:** Use version tag `task-scam-recovery-2026-05-28` for the new adapter and GGUF artifacts. This keeps them distinct from the Phase 7 closeout artifacts.

### Gate Bug Fix Scope

- **D-11:** The bug is in the audit logic that computes `blocker_reasons` and `ready`. Downstream agents should locate the per-label recall check and add enforcement: if any label with `recall_floor_applies: true` has `recall < floor`, append a blocker reason and set `ready = false`.
- **D-12:** After fixing the gate, re-run the existing Phase 7 snapshot through it to confirm it now correctly shows BLOCK. This validates the fix before re-evaluation begins.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Prior Phase Decisions

- `.planning/phases/05-recall-priority-evaluation-and-release-gates/05-CONTEXT.md` — D-01 through D-14 define the release gate model, recall floor policy, and artifact schema. D-03 locks per-label recall floor at 0.90 (this phase relaxes it to 0.80 for task_scam only).
- `.planning/phases/07-proposal-closeout-and-quantitative-validation/07-CONTEXT.md` — Locked decisions, canonical commands for train/convert/evaluate-release-split/release-eval, and confirmed artifact paths.

### Evaluation Artifacts (Current Broken State)

- `.planning/phases/05-recall-priority-evaluation-and-release-gates/05-evaluation-snapshot.json` — Current snapshot with task_scam recall=0.44. Gate bug confirmed: `ready=true` despite floor breach.
- `.planning/phases/05-recall-priority-evaluation-and-release-gates/05-explanation-review-pack.json` — Current review pack.
- `data/splits/recovered-balanced/val.jsonl` — Held-out val split. task_scam support=18.

### Data and Training

- `data/synthetic/recovered-balanced.jsonl` — Active dataset lineage (3,000 rows, 750 per class). Append new task_scam rows here.
- `data/splits/recovered-balanced/` — Active split root. Rebuild after appending.
- `src/data_pipeline/generation/prompts.py` — Contains `build_bulk_prompt` and `build_complex_prompt`. `task_scam` prompt guidance must be strengthened here.
- `src/data_pipeline/cli.py` — Dataset generation CLI (`--bulk-provider openai-compatible` flag for Colab-served endpoint or local generation).

### Model and Runtime

- `src/model_adaptation/cli.py` — Contains `train`, `convert`, `evaluate-release-split`, `prepare-explanation-review`, `release-eval` commands. All reused without modification.
- Off-repo model registry: `D:/PROJEct/AI MODELS/manifests/model-registry.json`
- Base model checkpoint: `D:/PROJEct/AI MODELS/base/qwen3-4b-instruct-2507`
- Existing Phase 7 adapter (reference): `D:/PROJEct/AI MODELS/proposal-closeout-full-2026-05-26/qwen3-4b-instruct-2507/`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- `src/model_adaptation/cli.py train` — Full training command already supports `--device cuda`, `--train-split`, `--val-split`, `--version-tag`. Works on Colab unchanged.
- `src/model_adaptation/cli.py convert` — GGUF conversion. On this machine: requires `GGUF_CONVERTER_SCRIPT` env var pointing at Python 3.13 `convert_hf_to_gguf.py` and `--quantization-profile q8_0`.
- `src/model_adaptation/cli.py evaluate-release-split` — Held-out evaluation with progress printing and checkpoint writes. Reuse directly.
- `src/data_pipeline/cli.py` — Supports `--bulk-provider auto|claude|gemini|openrouter|openai-compatible`, `--resume`, checkpointing. Use for targeted task_scam generation.

### The Gate Bug

- Bug location: the audit logic inside `evaluate-release-split` or `release-eval` that populates `audit.blocker_reasons` and `audit.ready`. Per-label recall check exists (`recall_floor_applies: true` in output) but does not actually gate `ready`.
- Evidence: `05-evaluation-snapshot.json` shows `task_scam` recall=0.44, `recall_floor_applies=true`, yet `audit.blocker_reasons=[]` and `audit.ready=true`.
- Fix: find where `blocker_reasons` is assembled and add: `if label.recall_floor_applies and label.recall < risky_recall_floor: blocker_reasons.append(...)`.

### Established Patterns

- Append-then-rebuild is the established split-update pattern (used in Phase 7 gap closure).
- Seed-grouping in the splitter keeps all variants of one seed together in a single split — important for task_scam if the new samples have matching seeds.
- Version tags on adapter and GGUF artifacts use date-stamped strings (`proposal-closeout-full-2026-05-26`, etc.).

### Integration Points

- New adapter replaces the Phase 7 adapter in the model registry for the `baseline-winner` profile.
- New GGUF replaces the Phase 7 GGUF for the `gguf-laptop` runtime profile.
- Phase 5 evaluation snapshot at `.planning/phases/05-recall-priority-evaluation-and-release-gates/05-evaluation-snapshot.json` is overwritten by `evaluate-release-split` — this is the intended update path.

</code_context>

<specifics>
## Specific Ideas

- User confirmed: Colab H100 for retraining. Not interested in CPU-based fallback for this phase.
- Task_scam scenario axes for prompt enrichment: **part-time like/follow/comment farms, Shopee/Lazada review-bombing, crypto referral links, fake purchase seeding, Zalo/Telegram livestream engagement**. Each scenario should follow the trust-then-disappear or advance-payment structure characteristic of task scams.
- Audit sample size: 30-50 rows from existing 750 task_scam samples — look for scenario variety and linguistic distinctiveness from benign.
- Data generation quantity: audit-determined. If existing data is narrow: 200 new rows. If already diverse: 50-100 richer rows.

</specifics>

<deferred>
## Deferred Ideas

- App response speed (llama.cpp threading optimization) — routed to Phase 7b as a separate quick task, not part of this recovery phase.
- Gate bug for Phase 5 legacy snapshot (`data/splits/val.jsonl` run) — that older run is historical only; no need to fix its verdict.
- Runner-up model (`qwen3.5-4b`) evaluation — not in scope; only the baseline-winner is the active released model.

</deferred>

---

*Phase: 07a-task-scam-recall-recovery*
*Context gathered: 2026-05-28*
