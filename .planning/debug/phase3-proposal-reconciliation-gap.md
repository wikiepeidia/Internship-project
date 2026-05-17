---
status: diagnosed
trigger: "Phase 3 closeout verification found the project still lacks an external note reconciling the proposal's original 8B wording with the locked 4B execution path."
created: 2026-05-17
updated: 2026-05-17
---

# Phase 3 Proposal Reconciliation Gap

## Symptoms

- Expected: The repo should contain a concise university-facing note that explains why the original 8B fine-tuning wording narrowed to a 4B-primary delivery path without weakening the technical intent.
- Actual: Internal planning files justify the 4B choice, but `documents/internship-proposal.md` still says Task 3 fine-tunes an 8B model and there is no dedicated reconciliation note for external reporting.
- Error messages: None.
- Timeline: First noted during Phase 3 UAT and still open after both 4B adapter runs completed.
- Reproduction: Compare `documents/internship-proposal.md` with `.planning/PROJECT.md` and `.planning/ROADMAP.md`.

## Resolution

root_cause: "The proposal text predates the local pilot that locked the 4B baseline winner, and the resulting rationale was captured in planning files but not yet translated into a supervisor-facing progress note."
fix_direction: "Add a short supervisor-facing reconciliation note that frames the 8B-to-4B shift as a hardware-fit and quality-delivery optimization, while noting that the 7B path remains available as a comparison or accelerated-path option."
files_involved:

- documents/internship-proposal.md
- .planning/PROJECT.md
- .planning/ROADMAP.md
