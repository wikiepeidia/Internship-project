# Phase 2: Offline Text Ingestion and Privacy Baseline - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-04
**Phase:** 02-offline-text-ingestion-and-privacy-baseline
**Areas discussed:** User entry surface, Offline baseline result, Privacy and failure behavior, Cue presentation style, Local setup and diagnostics experience

---

## User Entry Surface

| Option | Description | Selected |
|--------|-------------|----------|
| CLI first, backed by a reusable Python service | Fits the current pure-Python codebase and preserves later UI flexibility. | ✓ |
| Python service/API only | Keeps Phase 2 developer-facing only. | |
| Simple local web UI now | Adds a new interface stack immediately. | |

**User's choice:** CLI first, backed by a reusable Python service
**Notes:** Keep Phase 2 user-facing, but do it with the shortest local path that matches the existing repository.

| Option | Description | Selected |
|--------|-------------|----------|
| Analyze one pasted message at a time | Keeps scope tight and aligns with the baseline intake goal. | ✓ |
| Support both single-message and batch input in Phase 2 | Broader ingestion surface. | |
| Interactive session mode | Adds session/state design work early. | |

**User's choice:** Analyze one pasted message at a time
**Notes:** Phase 2 should optimize for a focused, one-message local check.

| Option | Description | Selected |
|--------|-------------|----------|
| One obvious command with minimal flags | Lowest-friction primary flow. | ✓ |
| Command plus advanced flags from day one | Larger surface area early. | |
| Expose both a simple mode and an advanced mode immediately | More flexibility, more complexity. | |

**User's choice:** One obvious command with minimal flags
**Notes:** The default launch path should stay obvious and lean.

---

## Offline Baseline Result

| Option | Description | Selected |
|--------|-------------|----------|
| Local heuristic/rule-based screener behind a reusable analyzer interface | Meets offline needs now while leaving space for the later trained model. | ✓ |
| Validation-only intake with no verdict yet | Weak against the need for a usable offline result. | |
| Bundle a lightweight local model immediately | Pulls future model work into this phase. | |

**User's choice:** Local heuristic/rule-based screener behind a reusable analyzer interface
**Notes:** Phase 2 should return something useful offline without collapsing the roadmap into one phase.

| Option | Description | Selected |
|--------|-------------|----------|
| Use the same three tiers as the dataset schema, but mark them as provisional | Keeps the contract aligned with existing schema vocabulary. | ✓ |
| Use softer screening labels such as low concern / review / suspicious | Introduces a second vocabulary. | |
| Binary suspicious vs not suspicious only | Drops useful middle ground. | |

**User's choice:** Use the same three tiers as the dataset schema, but mark them as provisional
**Notes:** Contract continuity matters more than inventing a temporary label set.

| Option | Description | Selected |
|--------|-------------|----------|
| A short human-readable summary plus the top suspicious cues | Best fit for direct CLI use. | ✓ |
| Structured JSON-style output only | Better for automation than manual use. | |
| A plain text verdict only | Too thin for later continuity. | |

**User's choice:** A short human-readable summary plus the top suspicious cues
**Notes:** The baseline should still feel useful to a human, not just to tests.

---

## Privacy and Failure Behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Do not persist raw messages by default | Strongest match for the privacy-first promise. | ✓ |
| Keep an explicit local history by default | More convenient, less private. | |
| Save only sanitized/redacted copies by default | Still introduces retention policy complexity. | |

**User's choice:** Do not persist raw messages by default
**Notes:** Runtime behavior should not inherit the dataset pipeline's write-to-disk habits.

| Option | Description | Selected |
|--------|-------------|----------|
| Reject non-text input and tell the user to paste extracted text manually | Keeps the scope boundary explicit and recoverable. | ✓ |
| Accept non-text placeholders and warn that analysis is incomplete | Blurs the text-only boundary. | |
| Try to infer meaning from filenames or attachment descriptions | Produces false confidence. | |

**User's choice:** Reject non-text input and tell the user to paste extracted text manually
**Notes:** The product should be honest about what it can and cannot analyze in v1.

| Option | Description | Selected |
|--------|-------------|----------|
| Fail closed with clear local setup/error guidance and no cloud fallback | Preserves the privacy contract in the failure path. | ✓ |
| Offer an explicit opt-in cloud fallback | More flexible, but weakens the same-phase privacy story. | |
| Return a generic warning with no setup guidance | Too weak for first-run usability. | |

**User's choice:** Fail closed with clear local setup/error guidance and no cloud fallback
**Notes:** Local-only should remain true even when the analyzer cannot run.

---

## Cue Presentation Style

| Option | Description | Selected |
|--------|-------------|----------|
| Quote exact text spans and add a short plain-language reason for each | Strong continuity with `suspicious_spans` and useful for humans. | ✓ |
| Show generalized reasons only | Less directly tied to user input. | |
| Quote exact spans only | Precise, but less clear without reasons. | |

**User's choice:** Quote exact text spans and add a short plain-language reason for each
**Notes:** Even the baseline result should point back to the pasted text itself.

| Option | Description | Selected |
|--------|-------------|----------|
| Show the top 3 cues at most | Balanced level of detail for CLI output. | ✓ |
| Show only the single strongest cue | Very concise, but may feel too thin. | |
| Show every detected cue | Can become noisy. | |

**User's choice:** Show the top 3 cues at most
**Notes:** The baseline should explain enough without turning into a wall of output.

---

## Local Setup and Diagnostics Experience

| Option | Description | Selected |
|--------|-------------|----------|
| Run a self-check and print exact local setup steps automatically | Best match for a single-command default flow. | ✓ |
| Fail immediately and tell the user to run a separate diagnostic command | Clearer separation, rougher onboarding. | |
| Assume the environment is prepared and return a generic error | Poor first-run usability. | |

**User's choice:** Run a self-check and print exact local setup steps automatically
**Notes:** The main command should remain humane even when it fails.

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, add a simple explicit doctor/check command alongside the main command | Gives users a dedicated readiness path without replacing the main flow. | ✓ |
| No, keep everything inside the one analyze command only | Simplest surface, but less explicit for diagnostics. | |
| Add a heavier interactive setup wizard | Overkill for this phase. | |

**User's choice:** Yes, add a simple explicit doctor/check command alongside the main command
**Notes:** Diagnostics should be available explicitly, but still lightweight.

## the agent's Discretion

- Exact command names and parser library.
- Exact heuristic rules and cue-ranking implementation.
- Exact wording and formatting of setup guidance.

## Deferred Ideas

None.