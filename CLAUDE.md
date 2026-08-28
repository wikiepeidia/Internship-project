<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **internship-project-local** (12073 symbols, 24431 relationships, 300 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> Index stale? Run `node .gitnexus/run.cjs analyze` from the project root — it auto-selects an available runner. No `.gitnexus/run.cjs` yet? `npx gitnexus analyze` (npm 11 crash → `npm i -g gitnexus`; #1939).

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows. For regression review, compare against the default branch: `detect_changes({scope: "compare", base_ref: "main"})`.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `query({search_query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `context({name: "symbolName"})`.
- For security review, `explain({target: "fileOrSymbol"})` lists taint findings (source→sink flows; needs `analyze --pdg`).

## Never Do

- NEVER edit a function, class, or method without first running `impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `rename` which understands the call graph.
- NEVER commit changes without running `detect_changes()` to check affected scope.

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/internship-project-local/context` | Codebase overview, check index freshness |
| `gitnexus://repo/internship-project-local/clusters` | All functional areas |
| `gitnexus://repo/internship-project-local/processes` | All execution flows |
| `gitnexus://repo/internship-project-local/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->

# VNPhish project handoff

This section is the project-specific authority for the next Claude session. Keep
the GitNexus instructions above. Do not replace this file with a generic assistant
template.

## Purpose and current state

VNPhish is a local, text-only Vietnamese phishing-analysis research prototype. It
uses a governed four-label corpus, compares a Qwen NF4 QLoRA structured-output
model with a full PhoBERT four-class classifier, preserves one frozen terminal
evaluation, and exposes `vnphish analyze`, `doctor`, and `demo`.

The active cleanup branch is `gsd/phase-41.1-final-defense-handoff`. The prior
report/code cleanup commits on `main` are:

- `3990d3a` — archive historical tooling;
- `495e7c6` — integrate final report evidence.

Do not call the milestone shipped yet. The Phase 41.1 verification status is
`gaps_found`, and the latest architecture review has six critical and three warning
findings. A Codex `gsd-ship` run therefore stopped before push/PR rather than
falsely marking the phase complete.

## Read order

1. `CLAUDE.md`
2. `documents/defense/CODE_WORKFLOW.md`
3. `documents/defense/DEFENSE_QA_WORKSHEET.md`
4. `documents/reports/latex/EVIDENCE_MAP.md`
5. `docs/architecture/overview.md`
6. `docs/architecture/training-evaluation.md`
7. `.planning/phases/41.1-codebase-architecture-overhaul/41.1-VERIFICATION.md`
8. `.planning/phases/41.1-codebase-architecture-overhaul/41.1-REVIEW.md`

Current source and the evidence map beat stale planning prose, old defense scripts,
and July walkthrough snapshots. Historical defense/walkthrough files live under
`historical/docs/` and must not be used as current authority.

## Authority order

For code behavior:

1. current source and tests;
2. machine-readable architecture policy;
3. current architecture/defense documents;
4. planning history.

For dataset/model/report facts:

1. verified manifest/export plus mandatory erratum;
2. `documents/reports/latex/EVIDENCE_MAP.md`;
3. phase verification/review records;
4. historical notes only when explicitly labelled historical.

Never replace frozen evidence with a plausible number from an older Markdown file.

## Current numerical anchors

- Final corpus: 2,097 rows.
- Partitions: 1,658 train, 219 validation, 220 terminal evaluation.
- Class totals: 741 bank impersonation, 655 benign, 404 task scam, 297 Zalo
  social engineering.
- Joined automated judge: 1,395/2,097 PASS, 66.52%.
- Human stratified sample: 44/100 PASS; judge-human agreement 87/100.
- Qwen validation macro F1: 0.9885153110, selected step 200.
- PhoBERT validation macro F1: 0.9848929140, selected step 100.
- Qwen terminal macro F1: 0.980493.
- PhoBERT terminal macro F1: 0.990892.
- Both accepted full runs used seed 42 and three epochs; Qwen completed 1,245
  steps and PhoBERT 312.
- Verified Qwen Q8_0 GGUF: 4,280,403,232 bytes, SHA-256
  `457f6f92d36a7d54da9916fd80a4028dcd055a653a015c4877370a0fea4d18ab`.
- Current architecture debt: six critical and three warnings.

The current report PDF build receipt records SHA-256
`255db98de4d8a90a2d06150063edf2fcf4c0b5baa808ec6e02d785299726395e`.
Treat it as a build identity, not as proof that student voice or final defense
approval is complete.

## Protected evidence and no-replay boundary

Routine documentation, cleanup, testing, and coaching must not:

- enumerate, stat, hash, or open `data/splits/test.jsonl` or its containing
  `data/splits` directory;
- run terminal evaluation, inference, training, providers, or model loading;
- access or mutate D-drive model roots;
- access ProgramData evaluation evidence;
- access or mutate `historical/phase41-source-closure/`;
- mutate the sealed export, erratum, manifests, or frozen model roots;
- run broad pytest selections that could discover protected paths.

Use exact bounded tests with the architecture startup guard and isolated temporary
roots. Do not infer that silence means a protected operation succeeded.

The correct terminal-access wording is: there was exactly one shared-cohort model
evaluation pass; earlier automated integrity tests had parsed, statted, and hashed
the files without model inference or human row display. Never say “untouched” or
“zero prior filesystem access.”

## Active, compatibility, and historical code

Preferred active surfaces:

- `src/runtime/` — installed application and local UI;
- `src/data_pipeline/core/` and `workflows.py` — schemas, text, splitting, and
  orchestration;
- `src/modeling/` — maintained training, inference, evaluation contracts, and
  evidence loading;
- `src/source_archiving/` — provenance archive services.

Compatibility/provenance surfaces:

- `src/model_adaptation/` retains experiment implementations and fixed commands;
- `src/modeling/legacy_adapters.py` is the intended bridge;
- `src/data_pipeline/migrations.py` routes five preserved one-off repairs;
- `scripts/phase40_comparison_launcher.ps1` and
  `scripts/phase41_one_shot_launcher.ps1` retain path-bound evidence identities.

Historical surfaces:

- `historical/tooling/`;
- `historical/docs/`;
- phase-numbered planning records.

The Codex/Zalo catalog files are intentionally preserved one-off reconstruction
provenance. Their paths are referenced by migrations, tests, and implementation
hashes. Do not delete or cosmetically rename them without a provenance-aware plan.
They are not an external-provider dependency of the installed runtime.

## Open technical debt

### Retained generation path

`TieredGenerator._build_batch_specs()` can reuse a `SeedRecord` across classes,
while `_derive_seed_id()` hashes only `source_url|text`. The maintained splitter
correctly rejects a seed spanning labels. The provider-generation CLI is therefore
not guaranteed to publish a realistic full rebuild.

Do not “fix” this by appending the class name to otherwise identical root IDs. A
valid fix must assign genuinely independent semantic roots to each class, preserve
variant grouping, and prove all active classes have enough groups for train,
validation, and terminal partitions.

### Phase 41.1 verification gaps

The current goal verifier records four gaps:

1. active runtime still contains phase-number chronology outside explicit
   compatibility/provenance boundaries;
2. `src.config`/`src.config.settings` are missing from the supposedly closed module
   inventory;
3. `scripts/archive_phase41_source_closure.py` violates its declared size budget
   without an exception;
4. the report handoff previously had an architecture-cycle count inconsistency.

Read the current verification file before assuming any gap has been closed.

### Architecture/security review

The latest review reports six critical and three warning findings, including
guard-bypass surfaces, incomplete pre-collection attestation, fail-open command
discovery, loopback demo request protections, terminal escape sanitization, and
shell-chain/report scanning. Do not call the code secure or production-ready until
they are fixed, tested, and re-reviewed.

### Report and defense

- The report is an evidence-enriched review draft. Student voice/style approval and
  comparison with a real passed-student reference remain pending.
- The current slide deck may still include old historical training/evaluation
  material. Audit slides against the evidence map before presenting.
- Defense answers must come from the student. A polished AI rewrite is coaching,
  not evidence of understanding.

## Report wording rules

Never claim:

- a t-test, confidence interval, statistical significance, stable winner, or
  run-to-run variance;
- ordinary-LoRA OOM or completed full-LoRA accuracy;
- PhoBERT GGUF;
- completed deployment fitting;
- a fair Qwen-versus-PhoBERT speed comparison;
- 44/100 as a corpus-wide pass/failure rate;
- that Pydantic is the semantic judge;
- that one model family generated the whole final corpus;
- that the architecture refactor produced the frozen metrics;
- that the architecture/security review is closed.

Qwen and PhoBERT scores are descriptive one-seed results. PhoBERT's higher terminal
macro F1 is not proof of stable superiority. Qwen's role includes richer structured
output; this is a design tradeoff, not permission to deny the measured result.

## Defense-coach protocol

When the student asks to practice:

1. read `documents/defense/DEFENSE_QA_WORKSHEET.md`;
2. ask exactly one question;
3. wait for the unaided answer;
4. quote that answer verbatim in the worksheet;
5. score correctness, mechanism, evidence, limitation, and ownership;
6. mark unsupported precision as wrong;
7. require a retry below 6/8 or after a critical contradiction;
8. do not reveal the model answer before the first attempt;
9. do not count Claude-authored wording as student mastery.

The two must-pass themes are “What did you contribute?” and “How does it work in
the code?” Require a file/function, a mechanism, an evidence artifact, and a
limitation—not a slogan or metric alone.

## Safe routine commands

```powershell
python -m src.runtime.cli --help
python -m src.runtime.cli doctor
python -m src.runtime.cli analyze --text "<Vietnamese message>" --channel zalo
python -m src.runtime.cli demo --host 127.0.0.1 --port 8765 --no-browser
```

Provider generation is networked, credentialed, mutating, and affected by the open
root-assignment caveat. Training and terminal evaluation are not casual tutorial
commands.

## Git and change discipline

- Preserve unrelated dirty files. At this handoff they include `.gitignore`,
  `.gsd/dispatch-isolation-sentinel.json`, `TODO.md`, and
  `.planning/milestone.lock`.
- Never use `git reset --hard` or destructive checkout commands.
- Run GitNexus impact before symbol edits and `detect_changes()` before commits.
- Use exact, bounded tests. Do not run a broad suite that can touch protected data.
- Do not push or open a PR while `verification.status` is `gaps_found`.
- The appropriate GSD next step for shipping is `/gsd-plan-phase 41.1 --gaps`,
  followed by execution, re-verification, and only then `gsd-ship`.
