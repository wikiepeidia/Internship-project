<!-- markdownlint-disable MD022 MD032 MD033 MD034 MD055 MD056 MD060 -->

# Phase 2: Offline Text Ingestion and Privacy Baseline - Research

**Researched:** 2026-05-04
**Domain:** Python CLI runtime, offline text screening, privacy-by-default local analysis
**Confidence:** MEDIUM

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Phase 2 should be CLI-first, backed by a reusable Python analyzer service rather than a web UI.
- **D-02:** The primary flow is one pasted message per run, not batch analysis or an interactive session.
- **D-03:** The main user path should be one obvious command with minimal flags.
- **D-04:** Before the trained local model exists, Phase 2 should use a local heuristic/rule-based screener behind an analyzer interface that later phases can swap out.
- **D-05:** The baseline should use the same three risk tiers already present in the dataset schema (`benign`, `suspicious`, `high-risk`), but clearly mark them as provisional.
- **D-06:** The default output should be a short human-readable summary rather than JSON-only or a bare verdict.
- **D-07:** Raw submitted messages must not be persisted by default.
- **D-08:** Non-text input stays out of scope in Phase 2; reject it and instruct the user to paste extracted text manually.
- **D-09:** If the local analyzer is unavailable or fails, the tool should fail closed, stay local, and give setup/error guidance instead of offering cloud fallback.
- **D-10:** Baseline suspicious cues should quote exact text spans from the pasted message and pair each span with a short plain-language reason.
- **D-11:** Show at most the top three cues in the default result.
- **D-12:** The main analyze command should run a self-check and print exact local setup steps automatically when the analyzer environment is not ready.
- **D-13:** Phase 2 should also expose a simple dedicated doctor/check command alongside the main analyze command.

### Claude's Discretion
- Exact command names, parser library, and package/module layout for the CLI/runtime surface.
- Exact heuristic rules, cue-ranking logic, and phrasing of setup guidance.
- Whether optional channel/source hints are added as a non-required input, as long as raw message text remains the only required payload and the text-only scope is preserved.

### Deferred Ideas (OUT OF SCOPE)
None - discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ING-01 | User can paste raw text messages for analysis from channels such as SMS, Zalo, Messenger, Telegram, and Facebook. | Recommends an stdin-first analyze command, a single-message request contract, optional channel metadata, and explicit text-only rejection behavior. |
| ING-02 | System can process Vietnamese and mixed Vietnamese-English text, including common code-switch patterns. | Recommends normalize-first handling via existing `normalize_text`, preserving code-switch tokens, and matching on a casefolded shadow copy while quoting exact spans from normalized text. |
| RUN-01 | User can run inference in local/offline mode without sending message content to cloud APIs in default operation. | Recommends a runtime package with no scraper/generation imports, a fail-closed doctor path, no cloud fallback, no raw-text persistence, and tests that assert no network access in the default path. |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Do not edit `PRD.md` without explicit human approval.
- Never hardcode secrets, credentials, or environment-specific values in source code.
- Run tests before marking implementation work complete.
- Consult `docs/technical/DECISIONS.md` before proposing changes that may conflict with prior architectural decisions. In this workspace, only template files exist under `.claude/templates/docs/technical/`; there is no active project decisions document yet.
- `CLAUDE.md` also contains generic multi-agent and TypeScript/Next.js placeholder content that does not match this Python repo. For this phase, the actionable repo-level rules above matter; the stack placeholders do not.

## Summary

Phase 2 should be planned as a small runtime package separate from `src/data_pipeline`. The existing `data_pipeline` code already gives the right shared primitives: environment-driven settings, normalization that preserves Vietnamese code-switching, and a stable three-tier risk vocabulary. The missing layer is a local runtime shell that accepts one pasted message, normalizes it, runs a provisional heuristic backend behind a swappable interface, and renders a short human-readable result without persisting raw text or reaching for network fallback.

The strongest planning constraint is privacy, not model accuracy. A CLI that takes message text only through a command-line flag is easy to build but leaks content into shell history and sometimes process listings. For a privacy-first Phase 2, the default path should be stdin-first: one analyze command reads a single message from stdin, runs a self-check, and prints a short result. An explicit `--text` flag can exist for tests and automation, but it should not be the privacy-default path.

The future swap seam should be a narrow analyzer backend interface using `typing.Protocol`. Phase 2 implements one heuristic backend. Phase 3/4 can add a local model backend with the same `analyze()` contract. Keep the renderer, CLI, and doctor path backend-agnostic now so replacing the heuristic engine later does not require redoing the entry surface.

**Primary recommendation:** Add a new `src/runtime/` package with an stdin-first `analyze` command, a `doctor` command, Pydantic request/result contracts, and a `Protocol`-based heuristic backend that returns provisional tiers plus up to three quoted cues.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib `argparse` | Python 3.12.10 available | CLI parsing for `analyze` and `doctor` | Enough for a two-command CLI, explicit behavior, no new dependency, and matches the repo's minimal Python-first style. |
| `pydantic` | Repo floor `>=2.12`; installed `2.12.5`; current `2.13.3` | Request/result contracts and doctor status models | Already used in this repo, and current code already uses V2 idioms such as `model_validate()` and `model_dump()`. |
| `pydantic-settings` | Repo floor `>=2.0`; installed `2.13.1`; current `2.14.0` | Runtime configuration | Existing `Settings` pattern is already tested and appropriate for backend choice, cue limits, and privacy flags. |
| `ftfy` plus existing `normalize_text()` | Repo floor `>=6.0`; installed/current `6.3.1` | Unicode repair and NFC normalization | Already wired into the repo and proven by passing tests; preserves code-switching and teencode. |
| `pytest` | Repo floor `>=9.0`; installed `9.0.2`; current `9.0.3` | Validation and regression tests | Already configured in `pyproject.toml`; current settings/normalizer/schema tests pass. |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `typing.Protocol` | Python 3.12 stdlib | Swap-friendly analyzer backend interface | Use for the heuristic backend now and model backend later, without forcing inheritance coupling. |
| `re`, `pathlib`, `sys.stdin` | Python 3.12 stdlib | Rule matching, safe I/O, stdin handling | Use for baseline heuristics and stdin-first ingest; sufficient for Phase 2. |
| `rapidfuzz` | Repo floor `>=3.14`; current `3.14.5` | Optional fuzzy brand or phrase matching | Only use if exact match rules miss obvious bank-name variants; do not make fuzzy logic the baseline explanation path. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `argparse` | `pydantic-settings` CLI support | Same dependency family and supports subcommands, but its CLI/source priority behavior is more implicit. Phase 2 needs explicit separation between payload intake and settings loading. |
| `argparse` | `Typer` 0.24.1 | Cleaner decorators and rich help, but it adds a new project dependency and a new house style to a repo that currently has no CLI convention. |
| Dedicated runtime contracts | `DatasetRecord` directly | Avoids new models, but incorrectly drags in dataset-only fields like `label`, `source`, and `seed_id` and couples runtime output to training artifacts. |

**Installation:**

```bash
pip install -e .[dev]
```

No new project dependency is required for the recommended Phase 2 baseline.

**Version verification:** Verified on 2026-05-04 from the current workspace and PyPI:

- `pydantic` current `2.13.3` (installed `2.12.5`)
- `pydantic-settings` current `2.14.0` (installed `2.13.1`)
- `pytest` current `9.0.3` (installed `9.0.2`)
- `ftfy` current `6.3.1` (installed `6.3.1`)
- `rapidfuzz` current `3.14.5`

## Architecture Patterns

### Recommended Project Structure

```text
src/
├── config/
│   └── settings.py          # Existing env-driven settings; extend with runtime fields
├── data_pipeline/
│   ├── processing/
│   │   └── normalizer.py    # Existing normalize-first entry point
│   └── schemas.py           # Existing risk-tier vocabulary reference
└── runtime/
    ├── cli.py               # Thin argparse entry point
    ├── service.py           # normalize -> validate -> doctor -> analyze -> render orchestration
    ├── doctor.py            # readiness checks and setup guidance
    ├── contracts.py         # AnalysisRequest, AnalysisResult, SuspiciousCue, DoctorStatus
    ├── render.py            # human-readable output formatting
    └── analyzers/
        ├── base.py          # AnalyzerBackend Protocol
        ├── heuristic.py     # Phase 2 rule-based backend
        └── rules.py         # cue catalog, weights, reasons, ranking helpers
```

### Pattern 1: Thin CLI, Fat Service

**What:** Keep `cli.py` as argument parsing plus exit-code wiring only. Put all runtime behavior in `service.py`.

**When to use:** Always. This keeps `analyze` and `doctor` testable without shell-level coupling.

**Example:**

```python
# Source: https://docs.python.org/3/library/argparse.html and workspace runtime design
import argparse

from src.runtime.service import RuntimeService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vnphish",
        description="Analyze one pasted message locally.",
        allow_abbrev=False,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze = subparsers.add_parser("analyze", help="Analyze one message")
    analyze.add_argument("--text", help="Optional explicit text; omit to read one message from stdin")
    analyze.add_argument("--channel", choices=["unknown", "sms", "zalo", "messenger", "telegram", "facebook"], default="unknown")
    analyze.set_defaults(handler="analyze")

    doctor = subparsers.add_parser("doctor", help="Check local analyzer readiness")
    doctor.set_defaults(handler="doctor")
    return parser
```

### Pattern 2: Protocol-Based Analyzer Backend

**What:** Define a narrow backend interface in `analyzers/base.py` with readiness and analyze methods.

**When to use:** Immediately. The heuristic backend uses it now, and the local model backend can implement the same interface later.

**Example:**

```python
# Source: https://docs.python.org/3/library/typing.html#typing.Protocol
from typing import Protocol

from src.runtime.contracts import AnalysisRequest, AnalysisResult, DoctorStatus


class AnalyzerBackend(Protocol):
    backend_name: str

    def doctor(self) -> DoctorStatus: ...

    def analyze(self, request: AnalysisRequest) -> AnalysisResult: ...
```

### Pattern 3: Normalize Once, Match on a Shadow Copy, Quote from Normalized Text

**What:** Call `normalize_text()` exactly once at the runtime boundary. Preserve the normalized text for cue quoting. Create a casefolded shadow copy for matching, but do not mutate the displayed text.

**When to use:** Every analyze request. Existing tests prove normalization behavior; cue matching should build on it, not replace it.

**Why:** This is the cleanest way to preserve Vietnamese diacritics, code-switch tokens, URLs, and exact quoted spans while still doing robust case-insensitive heuristics.

### Pattern 4: Contract Before Render

**What:** The analyzer returns a typed `AnalysisResult`; `render.py` converts that into the short default CLI summary.

**When to use:** Always. The backend should never print directly.

**Why:** Phase 4 will need richer explanations and recommendations. If Phase 2 prints strings directly from the heuristic backend, later backend swaps will break the CLI and tests.

### Integration With Existing Code

- `src/config/settings.py`: Extend the existing `Settings` model with a small set of runtime-specific fields such as backend name, max cues, min text chars, and privacy defaults. Do not create a parallel config system.
- `src/data_pipeline/processing/normalizer.py`: Reuse `normalize_text()` at the runtime boundary. Do not duplicate Unicode cleanup logic.
- `src/data_pipeline/schemas.py`: Keep the runtime risk-tier vocabulary exactly aligned with `benign`, `suspicious`, and `high-risk`, but do not reuse `DatasetRecord` as the runtime DTO.
- `tests/data_pipeline/test_normalizer.py` and `tests/data_pipeline/test_schemas.py`: Keep these as existing guardrails and add new runtime tests rather than rewriting old ones.
- Existing scraper/generation modules under `src/data_pipeline/`: treat them only as code-style references. The runtime path should not import them because they pull in network-facing concerns that are outside `RUN-01`.

### Anti-Patterns to Avoid

- **Putting the runtime under `src/data_pipeline/`:** runtime analysis is a separate concern from dataset building, and Phase 3/4 would inherit the wrong dependency graph.
- **Using `DatasetRecord` for runtime output:** it forces training-only fields into user-facing analysis.
- **Making `--text` the only primary intake path:** it leaks raw messages into shell history and sometimes process listings.
- **Lowercasing or reformatting the display string before cue extraction:** it breaks exact-span quoting.
- **Importing generation/scraper modules in the runtime path:** it undermines the offline guarantee and increases accidental network surface.

## Recommended Contracts

### Input Contract

Use a dedicated `AnalysisRequest` Pydantic model.

Recommended fields:

- `text: str` - the only required payload
- `channel: Literal["unknown", "sms", "zalo", "messenger", "telegram", "facebook"] = "unknown"` - optional metadata only
- `source_hint: str | None = None` - optional free-text metadata only if needed later; not required in Phase 2

Recommended rules:

- Input is one message per run.
- Accept UTF-8 Vietnamese and mixed Vietnamese-English text.
- Preserve teencode, URLs, OTP strings, bank names, punctuation, and code-switch phrases.
- Normalize with `normalize_text()` before any heuristics run.
- Reject empty or whitespace-only input.
- Use a soft lower bound such as 8 non-space characters for analysis; if the text is shorter, fail closed with guidance instead of guessing.
- Do not promise raw-character offsets from the pre-normalized string. If offsets are included later, define them relative to normalized text only.

### Result Contract

Use a dedicated `AnalysisResult` Pydantic model rather than `DatasetRecord`.

Recommended fields:

- `risk_tier: Literal["benign", "suspicious", "high-risk"]`
- `provisional: bool = True`
- `summary: str`
- `top_cues: list[SuspiciousCue]` with a hard cap of 3
- `backend_name: str`
- `normalized_text: str | None = None` only if the planner decides the service layer needs it for tests; do not print it by default

Recommended `SuspiciousCue` fields:

- `span: str` - exact quoted substring from normalized text
- `reason: str` - short plain-language explanation
- `cue_type: str | None = None` - optional internal grouping such as `url`, `urgency`, `credential_request`

Recommended result behavior:

- `summary` should explicitly state that the tier is provisional.
- `top_cues` should be sorted by severity first, then by clarity and specificity.
- `benign` results may return an empty cue list.
- Do not include calibrated probabilities or confidence scores in Phase 2.
- Keep space for later fields such as `threat_labels` and `recommendations`, but do not require them now.

## Privacy-By-Default Behavior

### Default Intake

The privacy-default path should be stdin-first:

```bash
vnphish analyze
```

The command reads one pasted message from stdin and analyzes it locally.

Why this should be the default:

- It avoids placing raw message text in shell history.
- It reduces accidental exposure through process lists.
- It still satisfies the single-message-per-run requirement.

`--text` can still exist for tests and automation, but it should not be the recommended privacy-default path.

### Retention Rules

- Raw input must stay in memory only for the duration of the process.
- Do not write raw text to disk, temp files, cache files, or debug logs by default.
- Do not echo the full message back in error paths.
- If the planner wants debug mode later, it should redact or truncate user text rather than print it verbatim.
- `doctor` must never require or retain user message content.

### Failure Behavior

- If the runtime is not ready, exit non-zero and print exact local setup steps.
- If the backend fails unexpectedly, fail closed: no verdict, no cloud fallback, no network suggestion, no partial remote rescue path.
- The error path should direct the user to `vnphish doctor` and a small set of exact remediation commands.
- Unsupported non-text input should be rejected explicitly with a message such as: `Text-only v1: paste extracted text manually. Images/OCR and audio are not accepted in Phase 2.`

## CLI Ergonomics

### Recommended Commands

Primary command:

```bash
vnphish analyze
```

Secondary check path:

```bash
vnphish doctor
```

Developer/testing equivalent if a console script is not yet added:

```bash
python -m src.runtime.cli analyze
python -m src.runtime.cli doctor
```

### Recommended Analyze Behavior

- With no `--text`, read one message from stdin.
- Optional `--channel` metadata can exist but should default to `unknown` and should not be required.
- Optional `--text` should exist for tests and automation.
- The command should run a lightweight self-check before analysis and show setup guidance automatically if the environment is not ready.
- Default output should be a short human-readable summary plus up to three cues.

### Recommended Doctor Behavior

`doctor` should check only local readiness:

- Python version compatibility
- required package imports
- settings load success via `get_settings()`
- backend selection and rule table load
- text-only boundary messaging available
- confirmation that the selected default backend is local-only

It should not:

- analyze user content
- require cloud API keys for Phase 2
- touch scraper or generation modules

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CLI parsing | ad-hoc `sys.argv` parsing | `argparse` | Built-in subcommands, help text, and error handling are already enough for a two-command CLI. |
| Settings loading | custom dotenv/env parser | existing `Settings` plus `pydantic-settings` | Already present and tested in this repo. |
| Unicode cleanup | custom Vietnamese text repair pipeline | existing `normalize_text()` and `ftfy` | Already proven to preserve code-switch tokens and NFC normalize text. |
| Runtime output | raw dicts or direct `print()` from backend | Pydantic contracts plus a renderer | Keeps Phase 2 swappable and testable. |
| Offline fallback handling | cloud rescue path | fail-closed local guidance | Cloud fallback violates the locked privacy posture. |

**Key insight:** The most expensive Phase 2 mistakes are not heuristic misses; they are boundary mistakes that make later model swap, privacy enforcement, and CLI validation harder than they need to be.

## Common Pitfalls

### Pitfall 1: Command-Line Arguments Leak Private Text

**What goes wrong:** The user passes the suspicious message via `--text`, and the message lands in shell history or process listings.

**Why it happens:** CLI tools often default to explicit arguments because they are easy to demo and test.

**How to avoid:** Make stdin the default intake path and keep `--text` as an explicit non-default escape hatch.

**Warning signs:** Documentation examples all use `--text`, or tests never exercise stdin.

### Pitfall 2: Normalization Breaks Raw Offsets

**What goes wrong:** The system reports offsets or spans that do not line up with the user-visible text.

**Why it happens:** `normalize_text()` fixes mojibake, applies NFC normalization, trims, and collapses whitespace. Those steps can shift character positions.

**How to avoid:** Quote exact spans from normalized text. If offsets are added, define them relative to normalized text only.

**Warning signs:** Tests compare offsets against pre-normalized input, or the service lowercases and rewrites the display text in place.

### Pitfall 3: Offline Runtime Accidentally Imports Network Surfaces

**What goes wrong:** The default analyzer path pulls in generation or scraper code and accidentally carries network clients or cloud-oriented behavior.

**Why it happens:** Reusing modules by directory proximity instead of dependency intent.

**How to avoid:** Keep `src/runtime/` isolated from `src/data_pipeline/generation/` and `src/data_pipeline/scraper/`.

**Warning signs:** Runtime imports from modules that reference `requests`, `httpx`, `anthropic`, Playwright, or live seed URLs.

### Pitfall 4: Dataset Schema and Runtime Schema Get Tangled

**What goes wrong:** The CLI result is forced to include training-only fields, or the runtime contract becomes hard to evolve when Phase 4 adds threat labels and recommendations.

**Why it happens:** `DatasetRecord` looks superficially similar to the runtime result.

**How to avoid:** Share only vocabulary and validation style, not the full DTO.

**Warning signs:** Planner wants to fill `source`, `seed_id`, or `label` in the runtime path just to satisfy a reused model.

### Pitfall 5: Over-Fuzzy Heuristics Become Hard to Explain

**What goes wrong:** A fuzzy score marks a message as suspicious, but the tool cannot quote a clear, exact cue.

**Why it happens:** Fuzzy matching is tempting for mixed spelling and brand variants.

**How to avoid:** Make exact, quotable rules the baseline. If `rapidfuzz` is used at all, use it as a helper to find candidate matches and still emit exact spans.

**Warning signs:** The backend can produce a tier but cannot name the span that triggered it.

## Code Examples

Verified patterns from official sources and the current workspace:

### Request and Result Models

```python
# Source: https://docs.pydantic.dev/latest/concepts/models/
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class AnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1)
    channel: Literal["unknown", "sms", "zalo", "messenger", "telegram", "facebook"] = "unknown"


class SuspiciousCue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    span: str = Field(min_length=1)
    reason: str = Field(min_length=3)


class AnalysisResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    risk_tier: Literal["benign", "suspicious", "high-risk"]
    provisional: bool = True
    summary: str = Field(min_length=10)
    top_cues: list[SuspiciousCue] = Field(default_factory=list)
    backend_name: str
```

### Service Boundary

```python
# Source: workspace pattern from src/data_pipeline/processing/normalizer.py
from src.config.settings import get_settings
from src.data_pipeline.processing.normalizer import normalize_text

from src.runtime.contracts import AnalysisRequest


class RuntimeService:
    def __init__(self, backend):
        self.backend = backend
        self.settings = get_settings()

    def analyze_once(self, request: AnalysisRequest):
        normalized_text = normalize_text(request.text)
        shadow_text = normalized_text.casefold()
        return self.backend.analyze(
            request.model_copy(update={"text": normalized_text}),
            shadow_text=shadow_text,
        )
```

### Argparse Subcommands With Explicit Dispatch

```python
# Source: https://docs.python.org/3/library/argparse.html#subcommands
import argparse


def handle_analyze(args: argparse.Namespace) -> int:
    ...


def handle_doctor(args: argparse.Namespace) -> int:
    ...


parser = argparse.ArgumentParser(prog="vnphish", allow_abbrev=False)
subparsers = parser.add_subparsers(required=True)

analyze = subparsers.add_parser("analyze")
analyze.set_defaults(func=handle_analyze)

doctor = subparsers.add_parser("doctor")
doctor.set_defaults(func=handle_doctor)

args = parser.parse_args()
raise SystemExit(args.func(args))
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Pydantic V1 `parse_obj()` / `dict()` naming | Pydantic V2 `model_validate()` / `model_dump()` | Pydantic v2 | Match the API style already used in this repo and avoid writing new code against outdated examples. |
| Base-class-only backend coupling | `typing.Protocol` structural interfaces | Standard in modern Python; documented in current Python docs | Lets Phase 3/4 swap the backend without inheritance refactors. |
| `typing.List` / `typing.Dict` aliases | built-in `list[...]` / `dict[...]` generics | Python 3.9+ | Matches current repo style and avoids older typing syntax. |
| `argparse.FileType` convenience objects | explicit `sys.stdin.read()` / `Path.read_text()` after parse | `FileType` deprecated in Python 3.14 docs | Safer resource handling and easier privacy-aware stdin control. |

**Deprecated/outdated:**

- `argparse.FileType` for new CLI I/O handling.
- Pydantic V1-style serialization/parsing names in new code.
- Reusing training DTOs as runtime DTOs.

## Open Questions

1. **What should the installed command name be?**
   - What we know: the CLI should have one obvious command plus `doctor`.
   - What's unclear: whether the script name should be `vnphish`, `vn-phishing`, or something else.
   - Recommendation: choose a short lowercase command in planning and add a `[project.scripts]` entry once the implementation starts.

2. **What is the minimum acceptable analyzed text length?**
   - What we know: empty or tiny inputs should not produce confident output, but the runtime should still accept short SMS-like content.
   - What's unclear: whether the threshold should be 5, 8, or 10 non-space characters.
   - Recommendation: start with a soft gate around 8 non-space characters and return guidance instead of forcing a verdict.

3. **Should optional `channel` hint affect heuristic ranking in Phase 2?**
   - What we know: optional metadata is allowed, but raw text is the only required payload.
   - What's unclear: whether channel metadata should influence risk ranking before there is a learned model.
   - Recommendation: keep `channel` metadata-only in Phase 2 to reduce false coupling and make tests easier.

4. **Should shared risk-tier vocabulary be extracted now or just locked by tests?**
   - What we know: runtime and dataset tiers must stay aligned.
   - What's unclear: whether to introduce a shared alias module in Phase 2 or keep the literal set duplicated with tests.
   - Recommendation: only extract shared aliases if the change stays small; otherwise duplicate the literal set and add a compatibility test immediately.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | runtime and tests | Yes | 3.12.10 | - |
| pip | local install/update steps | Yes | 26.0.1 | - |
| pytest | validation | Yes | 9.0.2 | `python -m pytest` |
| `pydantic` | runtime contracts | Yes | installed 2.12.5 | reinstall via `pip install -e .[dev]` |
| `pydantic-settings` | runtime config | Yes | installed 2.13.1 | reinstall via `pip install -e .[dev]` |
| `ftfy` | normalization | Yes | 6.3.1 | reinstall via `pip install -e .[dev]` |
| Typer | optional only, not recommended | Yes | 0.24.1 | `argparse` recommended |

**Missing dependencies with no fallback:**

- None for the recommended heuristic Phase 2 baseline.

**Missing dependencies with fallback:**

- None.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | `pytest` 9.0.2 installed (`9.0.3` current on PyPI) |
| Config file | `pyproject.toml` via `[tool.pytest.ini_options]` |
| Quick run command | `python -m pytest tests/runtime/test_cli.py tests/runtime/test_service.py -q` |
| Full suite command | `python -m pytest -q` |

Current baseline check in this workspace:

- `python -m pytest tests/config/test_settings.py tests/data_pipeline/test_normalizer.py tests/data_pipeline/test_schemas.py -q` -> 36 passed

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ING-01 | `analyze` accepts one pasted text message, supports optional channel metadata, and clearly rejects empty/unsupported non-text paths | CLI integration | `python -m pytest tests/runtime/test_cli.py -q` | No - Wave 0 |
| ING-02 | runtime analysis preserves Vietnamese and mixed Vietnamese-English text behavior after normalization and quotes exact cues from normalized text | unit + service integration | `python -m pytest tests/runtime/test_service.py tests/data_pipeline/test_normalizer.py -q` | Partial - existing normalizer tests exist, runtime tests are Wave 0 |
| RUN-01 | default path stays local, performs no network submission, persists no raw text by default, and fails closed with guidance | unit + integration | `python -m pytest tests/runtime/test_privacy.py tests/runtime/test_doctor.py -q` | No - Wave 0 |

### Sampling Rate

- **Per task commit:** `python -m pytest tests/runtime/test_contracts.py tests/runtime/test_service.py -q`
- **Per wave merge:** `python -m pytest tests/runtime -q`
- **Phase gate:** `python -m pytest -q` plus one manual stdin smoke test for `analyze` and one manual `doctor` run

### Wave 0 Gaps

- [ ] `tests/runtime/test_contracts.py` - request/result model validation and risk-tier compatibility
- [ ] `tests/runtime/test_service.py` - normalize-first orchestration, cue ordering, and exact-span quoting
- [ ] `tests/runtime/test_cli.py` - stdin-first analyze flow, `--text` escape hatch, and text-only rejection messaging
- [ ] `tests/runtime/test_privacy.py` - assert no raw-text persistence and no network usage in default path
- [ ] `tests/runtime/test_doctor.py` - readiness checks and setup guidance text

## Sources

### Primary (HIGH confidence)

- Workspace files: `src/config/settings.py`, `src/data_pipeline/processing/normalizer.py`, `src/data_pipeline/schemas.py`, `tests/config/test_settings.py`, `tests/data_pipeline/test_normalizer.py`, `tests/data_pipeline/test_schemas.py`
- Official Python docs: https://docs.python.org/3/library/argparse.html - subcommands, parser behavior, `allow_abbrev`, stdin/file handling caveats
- Official Python docs: https://docs.python.org/3/library/typing.html#typing.Protocol - structural interfaces via `Protocol`
- Official Pydantic docs: https://docs.pydantic.dev/latest/concepts/models/ - current V2 `model_validate()` / `model_dump()` contract patterns
- Official Pydantic settings docs: https://docs.pydantic.dev/latest/concepts/pydantic_settings/ - current settings behavior and CLI/source priority behavior
- Official pytest docs: https://docs.pytest.org/en/stable/ - test organization and execution conventions
- Official PyPI JSON metadata queried on 2026-05-04 for package versions and publish timestamps

### Secondary (MEDIUM confidence)

- None

### Tertiary (LOW confidence)

- None

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH - almost all recommendations reuse the repo's current Python/Pydantic/pytest stack and official docs.
- Architecture: MEDIUM - module boundaries and CLI defaults are prescriptive design recommendations, not existing code.
- Pitfalls: HIGH - grounded in current normalization behavior, official CLI/docs behavior, and the locked privacy requirements.

**Research date:** 2026-05-04
**Valid until:** 2026-06-03

<!-- markdownlint-enable MD022 MD032 MD033 MD034 MD055 MD056 MD060 -->
