---
phase: 07a-task-scam-recall-recovery
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/model_adaptation/release_evaluation.py
  - src/model_adaptation/schemas.py
  - src/data_pipeline/generation/prompts.py
  - tests/model_adaptation/test_release_evaluation.py
autonomous: true
requirements:
  - EVAL-02

must_haves:
  truths:
    - "The release gate correctly returns BLOCK when task_scam recall is below 0.80"
    - "The release gate correctly returns BLOCK when bank_impersonation or zalo_social_engineering recall is below 0.90"
    - "The gate returns PASS only when all three risky-label recall floors are simultaneously satisfied"
    - "task_scam generation prompts explicitly enumerate all five scenario axes with trust-then-disappear or advance-payment framing"
    - "Existing automated tests still pass after all code changes"
  artifacts:
    - path: "src/model_adaptation/schemas.py"
      provides: "Per-label recall floor constants and gate enforcement logic"
      contains: "RISKY_LABEL_RECALL_FLOORS"
    - path: "src/model_adaptation/release_evaluation.py"
      provides: "Patched _build_snapshot that enforces per-label recall floors"
      exports: ["_build_snapshot", "evaluate_release_split"]
    - path: "src/data_pipeline/generation/prompts.py"
      provides: "Enriched task_scam prompts with scenario axes constant"
      contains: "_TASK_SCAM_SCENARIO_AXES"
    - path: "tests/model_adaptation/test_release_evaluation.py"
      provides: "Tests proving gate blocks on per-label recall floor breach"
  key_links:
    - from: "src/model_adaptation/release_evaluation.py (_build_snapshot)"
      to: "src/model_adaptation/schemas.py (TASK_SCAM_RECALL_FLOOR, RISKY_LABEL_RECALL_FLOORS)"
      via: "per-label floor lookup after compute_release_metrics"
      pattern: "RISKY_LABEL_RECALL_FLOORS"
    - from: "src/data_pipeline/generation/prompts.py (build_bulk_prompt, build_complex_prompt)"
      to: "_TASK_SCAM_SCENARIO_AXES constant"
      via: "conditional injection when threat_class == 'task_scam'"
      pattern: "_TASK_SCAM_SCENARIO_AXES"
---

<objective>
Fix the Phase 5 release gate bug so per-label recall floors are actually enforced, and enrich the task_scam generation prompts with explicit scenario diversity axes. Both changes are prerequisites before any new data can be generated or the gate can be trusted.

Purpose: The gate bug means `audit.ready=true` and `blocker_reasons=[]` even when task_scam recall is 0.44, making every past and future release verdict untrustworthy. The prompt gap means new generated data would continue to be as narrow as the existing 750 rows.

Output: Patched `release_evaluation.py`, updated `schemas.py` with per-label floor map, enriched `prompts.py` with `_TASK_SCAM_SCENARIO_AXES`, and green tests proving the gate now blocks correctly.
</objective>

<execution_context>
@C:/Users/wikiepeidia/OneDrive - caugiay.edu.vn/bài tập/usth/GEN14/INTERNSHIP/Internship-project/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/wikiepeidia/OneDrive - caugiay.edu.vn/bài tập/usth/GEN14/INTERNSHIP/Internship-project/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/07a-task-scam-recall-recovery/07a-CONTEXT.md
@.planning/phases/05-recall-priority-evaluation-and-release-gates/05-evaluation-snapshot.json

<interfaces>
<!-- Key schemas and contracts the executor must understand before touching any file. -->

From src/model_adaptation/schemas.py:

```python
UNIFORM_RISKY_RECALL_FLOOR = 0.90  # current single floor — must be split into per-label map

class HeldOutSupportAudit(BaseModel):
    risky_recall_floor: float = Field(default=UNIFORM_RISKY_RECALL_FLOOR, ge=0.0, le=1.0)
    blocker_reasons: list[str] = Field(default_factory=list)
    ready: bool = False
    verdict: ReleaseVerdict = "BLOCK"

    @model_validator(mode="after")
    def align_status_with_blockers(self) -> "HeldOutSupportAudit":
        # BUG: only sets ready from blocker_reasons populated by audit_release_eval_support
        # audit_release_eval_support only checks zero-support, NOT recall floors
        self.ready = not self.blocker_reasons
        self.verdict = "PASS" if self.ready else "BLOCK"
        return self

class PerLabelMetricRow(BaseModel):
    label: ThreatLabel
    recall: float
    recall_floor_applies: bool = False   # True for all three risky labels

    @model_validator(mode="after")
    def align_risky_label_flag(self) -> "PerLabelMetricRow":
        self.recall_floor_applies = self.label in LOCKED_RISKY_LABELS
        return self
```

From src/model_adaptation/release_evaluation.py:

```python
def _build_snapshot(*, split_path, audit, rows, run_id) -> ReleaseEvaluationSnapshot:
    overall_metrics, per_label_metrics = compute_release_metrics(rows)
    # BUG: per_label_metrics are computed but NOT checked against floors before snapshot is built
    # audit is passed in as-is from audit_release_eval_support (which only checks zero support)
    return ReleaseEvaluationSnapshot(
        run_id=run_id,
        evaluated_split_path=split_path,
        audit=audit,   # <-- audit.ready is already True at this point (wrong)
        overall_metrics=overall_metrics,
        per_label_metrics=per_label_metrics,
        rows=list(rows),
    )
```

From src/data_pipeline/generation/prompts.py:

```python
def build_bulk_prompt(seed_text: str, threat_class: str, count: int = 10) -> str:
    # No task_scam-specific guidance — same generic diversity instructions for all classes

def build_complex_prompt(seed_text: str, threat_class: str, num_variants: int = 3) -> str:
    # Same — no task_scam scenario axes injected
```
</interfaces>
</context>

<tasks>

<task type="tdd">
  <name>Task 1: Add per-label recall floor map to schemas and patch gate enforcement in _build_snapshot</name>

  <read_first>
    - src/model_adaptation/schemas.py (full file — understand UNIFORM_RISKY_RECALL_FLOOR, HeldOutSupportAudit, PerLabelMetricRow)
    - src/model_adaptation/release_evaluation.py (full file — understand _build_snapshot flow)
    - .planning/phases/07a-task-scam-recall-recovery/07a-CONTEXT.md (D-01, D-02, D-12)
    - .planning/phases/05-recall-priority-evaluation-and-release-gates/05-evaluation-snapshot.json (confirm bug: ready=true, task_scam recall=0.44)
  </read_first>

  <files>
    src/model_adaptation/schemas.py
    src/model_adaptation/release_evaluation.py
    tests/model_adaptation/test_release_evaluation.py
  </files>

  <behavior>
    - Test A: Gate blocks when task_scam recall is 0.44 (below 0.80 floor) — blocker_reasons must be non-empty, ready must be False, verdict must be BLOCK
    - Test B: Gate blocks when bank_impersonation recall is 0.85 (below 0.90 floor)
    - Test C: Gate blocks when zalo_social_engineering recall is 0.88 (below 0.90 floor)
    - Test D: Gate passes when all three risky labels meet or exceed their individual floors (task_scam ≥0.80, bank ≥0.90, zalo ≥0.90)
    - Test E: Zero-support blockers from audit_release_eval_support still work (existing behavior must be preserved)
    - Test F: Running the existing broken 05-evaluation-snapshot.json data through the patched gate produces BLOCK (D-12 validation)
  </behavior>

  <action>
  ### schemas.py changes

  1. Add a `RISKY_LABEL_RECALL_FLOORS` dict after `UNIFORM_RISKY_RECALL_FLOOR`:
     ```python
     RISKY_LABEL_RECALL_FLOORS: dict[str, float] = {
         "bank_impersonation": 0.90,
         "zalo_social_engineering": 0.90,
         "task_scam": 0.80,          # D-01: relaxed from 0.90
     }
     ```

  2. Keep `UNIFORM_RISKY_RECALL_FLOOR = 0.90` in place — it is used by `HeldOutSupportAudit.risky_recall_floor` field default and tests may reference it. Do not remove it.

  3. Export `RISKY_LABEL_RECALL_FLOORS` at module level so `release_evaluation.py` can import it.

  ### release_evaluation.py changes

  1. Import `RISKY_LABEL_RECALL_FLOORS` from `src.model_adaptation.schemas`.

  2. Rewrite `_build_snapshot` to patch the audit after `compute_release_metrics` completes:

     ```python
     def _build_snapshot(*, split_path, audit, rows, run_id) -> ReleaseEvaluationSnapshot:
         overall_metrics, per_label_metrics = compute_release_metrics(rows)

         # D-02: enforce per-label recall floors after metrics are computed.
         # audit_release_eval_support only blocked on zero support; it does not see recall values.
         # Build a fresh blocker list that merges support blockers with recall floor violations.
         merged_blockers = list(audit.blocker_reasons)
         for metric_row in per_label_metrics:
             floor = RISKY_LABEL_RECALL_FLOORS.get(metric_row.label)
             if floor is not None and metric_row.recall < floor:
                 merged_blockers.append(
                     f"{metric_row.label} recall {metric_row.recall:.4f} is below the "
                     f"required floor of {floor:.2f}"
                 )

         # Rebuild audit with the merged blocker list.
         # HeldOutSupportAudit.align_status_with_blockers sets ready and verdict automatically.
         patched_audit = audit.model_copy(update={"blocker_reasons": merged_blockers})

         return ReleaseEvaluationSnapshot(
             run_id=run_id,
             evaluated_split_path=split_path,
             audit=patched_audit,
             overall_metrics=overall_metrics,
             per_label_metrics=per_label_metrics,
             rows=list(rows),
         )
     ```

  ### tests/model_adaptation/test_release_evaluation.py additions

  Add the six behavior tests listed above using `_build_row` and `compute_release_metrics` patterns already in the file. For Test F, load the real snapshot JSON from `.planning/phases/05-recall-priority-evaluation-and-release-gates/05-evaluation-snapshot.json`, reconstruct a `ReleaseEvaluationSnapshot`, extract its `per_label_metrics`, and feed them through the patched `_build_snapshot` logic by calling `evaluate_release_split` with a fake analyze callable that replays the snapshot's predicted labels from the rows list.
  </action>

  <verify>
    <automated>python -m pytest tests/model_adaptation/test_release_evaluation.py -q 2>&1 | tail -20</automated>
  </verify>

  <done>
    - `RISKY_LABEL_RECALL_FLOORS` dict present in schemas.py with task_scam=0.80, bank_impersonation=0.90, zalo_social_engineering=0.90
    - `_build_snapshot` in release_evaluation.py imports RISKY_LABEL_RECALL_FLOORS and merges per-label recall blocker reasons after compute_release_metrics
    - All six behavior tests pass: gate blocks on task_scam recall below 0.80, blocks on bank below 0.90, blocks on zalo below 0.90, passes when all floors met, preserves zero-support blocking, confirms existing snapshot would now return BLOCK
    - `python -m pytest tests/model_adaptation/test_release_evaluation.py -q` exits 0
  </done>
</task>

<task type="auto">
  <name>Task 2: Enrich task_scam generation prompts with scenario axes constant</name>

  <read_first>
    - src/data_pipeline/generation/prompts.py (full file — understand build_bulk_prompt and build_complex_prompt signatures)
    - .planning/phases/07a-task-scam-recall-recovery/07a-CONTEXT.md (D-06 scenario axes list, D-04 audit finding: 78% bank-impersonation-style content)
    - .planning/phases/07a-task-scam-recall-recovery/07a-RESEARCH.md (scenario axes detail)
  </read_first>

  <files>
    src/data_pipeline/generation/prompts.py
  </files>

  <action>
  Add a module-level constant `_TASK_SCAM_SCENARIO_AXES` immediately after the `THREAT_CLASSES` list:

  ```python
  _TASK_SCAM_SCENARIO_AXES = """
  Task-scam scenario axes — each axis has a distinct vocabulary and trust structure:
  (a) Part-time social media task farms: the victim is asked to like, follow, comment, or share posts on
      Facebook, TikTok, YouTube, or Shopee before receiving pay. Payment is withheld until a deposit or
      "activation fee" is paid. Key cues: nhiệm vụ, like, follow, comment, cộng tác viên, hoa hồng.
  (b) Shopee / Lazada review-bombing: the victim is sent a product link and asked to buy, review 5 stars,
      and then receive a refund plus commission. The refund never arrives. Key cues: đặt hàng, hoàn tiền,
      đánh giá 5 sao, Shopee, Lazada, hoa hồng, đơn hàng.
  (c) Crypto / token referral schemes: the victim earns commissions by recruiting new members or buying a
      token "package". The platform disappears or blocks withdrawals. Key cues: coin, token, đầu tư,
      hoa hồng giới thiệu, rút tiền, ví điện tử.
  (d) Fake purchase seeding (online shop): the victim is recruited to seed fake orders for a seller's
      statistics. They pay upfront for the order value and never receive reimbursement. Key cues: tạo đơn
      ảo, shop online, doanh số, hệ thống, tài khoản ảo.
  (e) Zalo / Telegram livestream engagement: the victim is paid to join a livestream, heart-react, send
      stickers, or comment on cue. They must pay a deposit first to "prove seriousness". Key cues: livestream,
      tim, sticker, bình luận, Telegram, nhóm kín, cọc.
  Each scenario follows one of two trust structures:
  - Trust-then-disappear: the operator pays small early tasks to build confidence, then raises the stakes
    (larger deposit, more orders) and vanishes.
  - Advance-payment: the victim must pay before any task assignment, with the promise that the fee will be
    deducted from their first payout.
  Linguistic distinctiveness from benign: use specific platform names, task verbs (like/follow/đặt hàng),
  and Vietnamese informal phrasing (nha, ak, ib, zl) that do NOT appear in bank-notification contexts.
  """
  ```

  Then modify `build_bulk_prompt` to inject the axes when `threat_class == "task_scam"`:

  After the `Seed text anchor:` block and before `Target threat class:`, add a conditional block:

  ```python
  task_scam_guidance = ""
  if threat_class == "task_scam":
      task_scam_guidance = f"\n  Task-scam scenario coverage (use all five axes across the {count} examples):\n  {_TASK_SCAM_SCENARIO_AXES.strip()}\n"
  ```

  Then insert `{task_scam_guidance}` into the dedent string between `Target threat class: {threat_class}` and `Diversity instructions:`.

  Apply the same pattern to `build_complex_prompt`: inject a `task_scam_guidance` block between `Target threat class:` and `Requirements:`, instructing the model to cover at least three of the five axes across the `{num_variants}` variants.

  Do not change any other prompt function. Do not change function signatures.
  </action>

  <verify>
    <automated>python -c "from src.data_pipeline.generation.prompts import build_bulk_prompt, build_complex_prompt, _TASK_SCAM_SCENARIO_AXES; p = build_bulk_prompt('mẫu', 'task_scam', 10); assert 'nhiệm vụ' in p or 'like' in p or 'Shopee' in p, 'scenario axes not injected'; p2 = build_bulk_prompt('mẫu', 'bank_impersonation', 10); assert 'Task-scam scenario' not in p2, 'axes leaked into wrong class'; print('PASS')"</automated>
  </verify>

  <done>
    - `_TASK_SCAM_SCENARIO_AXES` constant defined in prompts.py with all five axes: (a) like/follow farms, (b) Shopee/Lazada review-bombing, (c) crypto referral, (d) fake purchase seeding, (e) Zalo/Telegram livestream
    - `build_bulk_prompt` injects the axes block when and only when `threat_class == "task_scam"`
    - `build_complex_prompt` injects a parallel guidance block when and only when `threat_class == "task_scam"`
    - Verification command prints PASS
    - No other prompt functions are changed
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| snapshot JSON → gate logic | Snapshot on disk could have stale `ready=true` if loaded directly; the patched gate must recompute from per_label_metrics at runtime, not trust cached audit fields |
| generated prompt → LLM output | Injected scenario axes guide the LLM; malformed axes cannot break the pipeline because output is JSON-validated downstream |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-7a01-01 | Tampering | _build_snapshot audit patching | mitigate | Use model_copy with explicit merged_blockers list; HeldOutSupportAudit validator recomputes ready and verdict from the new list automatically |
| T-7a01-02 | Repudiation | Gate fix does not affect historical snapshot file | accept | Historical snapshot at 05-evaluation-snapshot.json remains on disk as evidence of the pre-fix state; new evaluation run overwrites it with honest result |
| T-7a01-03 | Information Disclosure | _TASK_SCAM_SCENARIO_AXES injected into prompts sent to vLLM | accept | Prompt content is dataset guidance only, contains no secrets or PII |
</threat_model>

<verification>
After both tasks complete:

1. Gate fix confirmed: `python -m pytest tests/model_adaptation/test_release_evaluation.py -q` passes all tests including the six new per-label-floor tests.
2. Schema constant present: `python -c "from src.model_adaptation.schemas import RISKY_LABEL_RECALL_FLOORS; assert RISKY_LABEL_RECALL_FLOORS['task_scam'] == 0.80; print('floor OK')"` prints `floor OK`.
3. Prompt enrichment confirmed: `python -c "from src.data_pipeline.generation.prompts import build_bulk_prompt; p = build_bulk_prompt('x', 'task_scam'); assert 'Shopee' in p; print('prompt OK')"` prints `prompt OK`.
4. No regressions: `python -m pytest tests/ -q --ignore=tests/runtime` passes (runtime tests require model artifacts).
</verification>

<success_criteria>
- Gate bug is fixed: `_build_snapshot` enforces per-label recall floors from `RISKY_LABEL_RECALL_FLOORS` after computing metrics
- task_scam floor is 0.80 (per D-01); bank_impersonation and zalo_social_engineering floors are 0.90
- All existing release evaluation tests still pass
- New tests prove gate returns BLOCK when any risky label is below its floor
- task_scam prompts in both `build_bulk_prompt` and `build_complex_prompt` inject `_TASK_SCAM_SCENARIO_AXES` when `threat_class == "task_scam"`
- No other classes are affected by the prompt change
</success_criteria>

<output>
After completion, create `.planning/phases/07a-task-scam-recall-recovery/07a-01-SUMMARY.md` with:
- Which files were changed and what was changed
- Exact RISKY_LABEL_RECALL_FLOORS values as committed
- Number of new tests added and their names
- Command outputs confirming both verification steps passed
</output>
