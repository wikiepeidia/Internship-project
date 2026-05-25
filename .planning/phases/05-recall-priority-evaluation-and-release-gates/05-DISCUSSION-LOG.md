# Phase 5: Recall-Priority Evaluation and Release Gates - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in `05-CONTEXT.md` - this log preserves the alternatives considered.

**Date:** 2026-05-25
**Phase:** 05-recall-priority-evaluation-and-release-gates
**Areas discussed:** release gate strictness, explanation rubric, proposal UI scope check

---

## UPDATE SESSION (2026-05-25)

### Release Gate Strictness

| Option | Description | Selected |
| --- | --- | --- |
| Hard block on high-harm recall misses | If any high-harm scam class falls below its recall threshold, release is blocked even when overall F1 looks acceptable | ✓ |
| Balanced gate across overall metrics | Allow some recall tradeoff if overall metrics remain strong | |
| Advisory gate only | Report misses and allow human release judgment without a hard blocker | |

**User's choice:** Hard block on high-harm recall misses.

### Hard-Blocking Label Set

| Option | Description | Selected |
| --- | --- | --- |
| All risky labels are hard-blocking | Any recall miss on any non-benign in-scope label blocks release | ✓ |
| Only bank impersonation and social engineering | Task scam remains reported but does not hard-block release | |
| Only bank impersonation | One strict blocker class; other labels remain advisory | |

**User's choice:** All risky labels are hard-blocking.

### Recall Floor Shape

| Option | Description | Selected |
| --- | --- | --- |
| One uniform recall floor | Use one minimum recall target for all risky labels | ✓ |
| Different floors by label severity | Use stricter floors for the most harmful labels and a looser one for task scam | |
| Not sure yet | Keep the principle but defer the gate shape | |

**User's choice:** One uniform recall floor.

### Recall Floor Number

| Option | Description | Selected |
| --- | --- | --- |
| `0.90` per risky label | Strong safety bias without assuming near-perfect recall on a smaller offline benchmark | ✓ |
| `0.85` per risky label | More permissive floor with lower block risk from benchmark variance | |
| `0.95` per risky label | Very strict release gate, likely to block often | |
| Leave the number open for now | Lock the policy shape first and set the exact threshold later | |

**User's final choice:** `0.90` per risky label.

### Explanation Rubric Dimensions

| Option | Description | Selected |
| --- | --- | --- |
| Grounding + label alignment + safe recommendation | Check that explanations cite real evidence, fit the predicted threat, and give safe next steps | ✓ |
| Grounding only | Only check whether cues are anchored in the text | |
| Full response quality | Score grounding, label fit, recommendations, tone, clarity, and readability | |

**User's choice:** Grounding + label alignment + safe recommendation.

### Explanation Evaluation Scope

| Option | Description | Selected |
| --- | --- | --- |
| All risky predictions only | Score suspicious and high-risk outputs; benign outputs are lower priority | ✓ |
| All predictions including benign | Require rubric coverage for benign, suspicious, and high-risk outputs | |
| Only sampled showcase cases | Use the rubric on a smaller demonstration slice only | |

**User's choice:** All risky predictions only.

### Explanation Gate Severity

| Option | Description | Selected |
| --- | --- | --- |
| Advisory unless unsafe output appears | Fabricated evidence or unsafe recommendations block release; weaker explanation quality is reported but not release-blocking | ✓ |
| Hard block on any rubric failure | Any failed explanation criterion blocks release | |
| Purely advisory | Explanation quality never blocks release | |

**User's choice:** Advisory unless unsafe output appears.

### Explanation Judging Method

| Option | Description | Selected |
| --- | --- | --- |
| Hybrid: deterministic checks + manual review sample | Use automated grounding or safety checks plus a curated manual review sample | ✓ |
| Manual review only | Use a human rubric without deterministic checks | |
| Deterministic checks only | Keep the gate fully automatic and skip manual review | |

**User's choice:** Hybrid: deterministic checks + manual review sample.

### Proposal UI Scope Check

The user asked whether the mini frontend demo mentioned in `documents/internship-proposal.md` should be built in this stage. The answer from the current roadmap context is no: the proposal includes a text-only UI task, but the active Phase 5 scope is evaluation and release gates, not frontend delivery.

**Decision:** Keep the mini frontend demo out of current Phase 5 scope unless the roadmap is explicitly revised.

### Demo UI Roadmap Treatment

| Option | Description | Selected |
| --- | --- | --- |
| Add a separate post-Phase-5 demo UI phase | Finish evaluation gates first, then build a minimal local demo frontend as its own roadmap slice | ✓ |
| Fold a tiny demo UI into Phase 5 | Treat the UI as part of the same phase after the release-gate work | |
| Treat the existing CLI as sufficient for v1 | Do not add a new frontend phase unless a reviewer explicitly asks for it | |
| Not sure yet | Keep it deferred and decide later | |

**User's choice:** Add a separate post-Phase-5 demo UI phase.

### Demo UI Milestone Placement

| Option | Description | Selected |
| --- | --- | --- |
| Keep it post-v1 backlog only | Finish Phase 5 first and treat the demo UI as a follow-up idea | |
| Extend the current v1 milestone with a new Phase 6 | Add the demo UI as a required final phase in the active roadmap | ✓ |
| Not sure yet | Record the idea and delay the milestone decision | |

**User's choice:** Extend the current v1 milestone with a new Phase 6.

### Release Artifact Format

| Option | Description | Selected |
| --- | --- | --- |
| Both markdown report and JSON artifact | Emit a human-readable release report plus a machine-readable structured result | ✓ |
| Markdown report only | Optimize for human review and skip structured automation output | |
| JSON artifact only | Optimize for automation and keep human review to ad hoc console output | |

**User's choice:** Both markdown report and JSON artifact.

### Release Artifact Verdict Shape

| Option | Description | Selected |
| --- | --- | --- |
| PASS / BLOCK / FLAG | Preserve both blocking failures and non-blocking concerns | ✓ |
| PASS / FAIL only | Keep the gate binary | |
| Score only | Publish metrics without an explicit verdict state | |

**User's choice:** PASS / BLOCK / FLAG.

### Release Artifact Location

| Option | Description | Selected |
| --- | --- | --- |
| Markdown in phase docs, JSON in manifests | Keep the report under `.planning/phases/05-.../` and the structured artifact under `data/manifests/` | ✓ |
| Keep both in the Phase 5 docs folder | Optimize for planning review only | |
| Keep both under data/manifests | Optimize for artifact-driven automation only | |

**User's choice:** Markdown in phase docs, JSON in manifests.

### Release Artifact Required Content

| Option | Description | Selected |
| --- | --- | --- |
| Metrics + blocker reasons + rubric summary | Include overall and per-class metrics, explicit blocking or flagged reasons, and explanation-rubric results | ✓ |
| Metrics only | Let readers infer the decision from the numbers | |
| Verdict summary only | Keep the artifact minimal and rely on other files for detail | |

**User's choice:** Metrics + blocker reasons + rubric summary.

## Deferred Ideas

- Detailed Phase 6 UI scope is still open even though the roadmap direction is now locked.
