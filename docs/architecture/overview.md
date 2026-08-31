# Current Architecture Overview

This page is the shortest safe route through the current repository. It describes
the active application in domain language, then places compatibility and historical
code at the boundary where it belongs. Historical phase-numbered names are compatibility/provenance labels only;
they are not the vocabulary for new features.

## 1. Installed application

The installed application is `vnphish`, with `analyze`, `doctor`, and `demo` as its
three public commands. `src.runtime.cli` owns that interface. Start here when
explaining what a user runs; the much larger model-adaptation command family is a
compatibility surface for old scripts and evidence, not the installed application.

<!-- ordered-flow:start -->
```mermaid
flowchart LR
  N1["1. Installed application"]
  N2["2. Runtime orchestration"]
  N3["3. Integrity, artifacts, and source archiving"]
  N4["4. Data core"]
  N5["5. External data workflows"]
  N6["6. Migration catalog"]
  N7["7. Modeling services"]
  N8["8. Runtime analyzers"]
  N9["9. Evaluation and evidence"]
  N10["10. Compatibility and provenance"]
  N1 --> N2
  N2 --> N3
  N3 --> N4
  N4 --> N5
  N5 --> N6
  N6 --> N7
  N7 --> N8
  N8 --> N9
  N9 --> N10
```
<!-- ordered-flow:end -->

## 2. Runtime orchestration

`src.runtime.service` coordinates one text-only analysis. Runtime contracts define
the result shape, renderers format safe terminal output, the doctor checks local
readiness, and the demo exposes the same runtime service through the local browser
UI. Runtime settings contain runtime and local-model locations but no provider or
data-generation credentials.

## 3. Integrity, artifacts, and source archiving

`src.core.integrity` owns strict JSON, hashing, safe-path, and atomic-write
primitives for new code. `src.core_binding` supplies the stable
descriptor-relative or protected Win32 parent handles used by those writes.
`src.artifacts` gives the application neutral readers for registered models and
release summaries. The archive compatibility facade -> `src.source_archiving` -> `src.source_archiving.service`
chain delegates immutable archive work to the bound
filesystem and contracts modules. These boundaries keep the active runtime separate
from training and completed experiment implementations.

## 4. Data core

`src.data_pipeline.core.records`, `.text`, and `.splits` own reusable records,
Unicode normalization, lexical deduplication, group-safe splitting, and manifest
construction. They are deterministic and dependency-light. Old schema, processing,
and versioning paths remain explicit forwards so existing callers continue to work.

## 5. External data workflows

`src.data_pipeline.workflows` coordinates scraping, generation, and judging, while
`src.data_pipeline.recovery` owns the closed, fail-closed recovery input boundary,
and `src.data_pipeline.generation_runs` owns resumable checkpoint lifecycles.
Those optional/provider-heavy imports stay inside selected handlers.
The canonical domain operation is `build_training_corpus`. The legacy CLI retains
one frozen compatibility identifier:

<!-- legacy-data-cli-identifier:start -->
`run_phase1`
<!-- legacy-data-cli-identifier:end -->

New code uses the domain operation; the retained identifier exists only for callers
that still depend on the compatibility seam.

## 6. Migration catalog

`src.data_pipeline.migrations` is a fixed catalog for five preserved one-off
repairs. A caller chooses a reviewed migration ID before the old module is imported.
These routes are audit history, not normal data preparation steps, and unknown IDs
fail before import.

## 7. Modeling services

`src.modeling.training`, `.inference`, `.evaluation`, and `.evidence` are the
phase-neutral ports for current code. `src.modeling.legacy_adapters` is the named
one-way bridge to retained implementations. New callers use these domain ports and
do not import historical producer modules directly.

## 8. Runtime analyzers

`src.runtime.analyzers` selects heuristic, GGUF, or accelerated-local analysis
behind one runtime contract. It may consume neutral artifact and inference
boundaries, but the checked graph prevents it from reaching training, provider,
scraper, or historical evaluator code.

## 9. Evaluation and evidence

Evaluation consumes a frozen model/result contract; read-only evidence binds source,
materialization, result, export, and erratum identities. The arrows below describe
data and artifact movement, not Python import direction. Frozen result claims come
from the sealed evidence authority, never from replaying this flow.

<!-- data-flow:start -->
```mermaid
flowchart LR
  D1["External workflows"]
  D2["Data core"]
  D3["Model training port"]
  D4["Versioned artifacts"]
  D5["Model inference port"]
  D6["Runtime service"]
  D7["Installed vnphish CLI"]
  D8["Evaluation port"]
  D9["Read-only evidence"]
  D10["Report handoff"]
  DH["Historical producer closure"]
  D1 --> D2
  D2 --> D3
  D3 --> D4
  D4 --> D5
  D5 --> D6
  D6 --> D7
  D4 --> D8
  D8 --> D9
  DH -.-> D9
  D9 --> D10
```
<!-- data-flow:end -->

## 10. Compatibility and provenance

Compatibility adapters preserve old commands/imports and may cross into the exact
historical allowlist. Active modules do not. The historical source closure records
what produced the frozen evaluation, while current code is the maintained
architecture. This page does not claim that the refactored code produced frozen metrics.

<!-- dependency-flow:start -->
```mermaid
flowchart LR
  A["Active domain modules"]
  C["Compatibility adapters"]
  H["Historical implementations"]
  C --> H
```
<!-- dependency-flow:end -->

### Closed module groups

The following inventory is deliberately exhaustive. Adding a source module to any
covered boundary requires updating the policy and this table together; a filesystem
scan cannot silently admit it.

<!-- policy-groups:start -->
| Policy group | Modules |
| --- | --- |
| `active` | `src.artifacts`<br>`src.config`<br>`src.config.settings`<br>`src.core`<br>`src.core_binding`<br>`src.core.integrity`<br>`src.modeling`<br>`src.modeling.evaluation`<br>`src.modeling.evidence`<br>`src.modeling.inference`<br>`src.modeling.training`<br>`src.runtime`<br>`src.runtime.analyzers`<br>`src.runtime.analyzers.accelerated`<br>`src.runtime.analyzers.base`<br>`src.runtime.analyzers.gguf`<br>`src.runtime.analyzers.heuristic`<br>`src.runtime.analyzers.local_model`<br>`src.runtime.analyzers.rules`<br>`src.runtime.cli`<br>`src.runtime.contracts`<br>`src.runtime.demo`<br>`src.runtime.doctor`<br>`src.runtime.render`<br>`src.runtime.service`<br>`src.source_archiving`<br>`src.source_archiving.contracts`<br>`src.source_archiving.filesystem`<br>`src.source_archiving.service` |
| `compatibility_adapters` | `src.model_adaptation.cli`<br>`src.model_adaptation.commands`<br>`src.model_adaptation.commands.adaptation`<br>`src.model_adaptation.commands.legacy_phase40`<br>`src.model_adaptation.commands.legacy_phase41`<br>`src.model_adaptation.commands.router`<br>`src.model_adaptation.convert`<br>`src.model_adaptation.doctor`<br>`src.model_adaptation.explanation_review`<br>`src.model_adaptation.release_evaluation`<br>`src.model_adaptation.release_gates`<br>`src.model_adaptation.release_readiness`<br>`src.modeling.legacy_adapters` |
| `historical` | `src.model_adaptation`<br>`src.model_adaptation.catalog`<br>`src.model_adaptation.data`<br>`src.model_adaptation.phase40_callbacks`<br>`src.model_adaptation.phase40_colab_prepare`<br>`src.model_adaptation.phase40_comparison_launch`<br>`src.model_adaptation.phase40_contract`<br>`src.model_adaptation.phase40_evidence`<br>`src.model_adaptation.phase40_final_authority`<br>`src.model_adaptation.phase40_finalize`<br>`src.model_adaptation.phase40_gguf`<br>`src.model_adaptation.phase40_graphs`<br>`src.model_adaptation.phase40_handoff`<br>`src.model_adaptation.phase40_local_experiment`<br>`src.model_adaptation.phase40_lora_recovery`<br>`src.model_adaptation.phase40_metrics`<br>`src.model_adaptation.phase40_modes`<br>`src.model_adaptation.phase40_notebooks`<br>`src.model_adaptation.phase40_operator`<br>`src.model_adaptation.phase40_phobert_release`<br>`src.model_adaptation.phase40_production_authorities`<br>`src.model_adaptation.phase40_qlora_session`<br>`src.model_adaptation.phase40_release_authorities`<br>`src.model_adaptation.phase40_review`<br>`src.model_adaptation.phase40_runtime_materialize`<br>`src.model_adaptation.phase41_evaluation`<br>`src.model_adaptation.phase41_protocols`<br>`src.model_adaptation.phobert_training`<br>`src.model_adaptation.pilot`<br>`src.model_adaptation.prompts`<br>`src.model_adaptation.registry`<br>`src.model_adaptation.schemas`<br>`src.model_adaptation.training` |
| `data.compatibility` | `src.data_pipeline.processing`<br>`src.data_pipeline.processing.dedup`<br>`src.data_pipeline.processing.normalizer`<br>`src.data_pipeline.processing.splitter`<br>`src.data_pipeline.schemas`<br>`src.data_pipeline.versioning`<br>`src.data_pipeline.versioning.manifest` |
| `data.core` | `src.data_pipeline`<br>`src.data_pipeline.core`<br>`src.data_pipeline.core.records`<br>`src.data_pipeline.core.splits`<br>`src.data_pipeline.core.text` |
| `data.migrations` | `src.data_pipeline.apply_mislabel_triage`<br>`src.data_pipeline.apply_task_scam_risk_tier_repair`<br>`src.data_pipeline.migrations`<br>`src.data_pipeline.reconstruct_zalo_direct_catalog`<br>`src.data_pipeline.repair_corpus_split_governance`<br>`src.data_pipeline.repair_zalo_narrator_scaffold` |
| `data.workflows` | `src.data_pipeline.cli`<br>`src.data_pipeline.generate_mislabel_triage_sheet`<br>`src.data_pipeline.generation`<br>`src.data_pipeline.generation.gemini_auth`<br>`src.data_pipeline.generation.generator`<br>`src.data_pipeline.generation.prompts`<br>`src.data_pipeline.generation.quality_judge`<br>`src.data_pipeline.generation.zalo_codex_catalog`<br>`src.data_pipeline.generation.zalo_codex_recovery`<br>`src.data_pipeline.generation.zalo_direct_actions`<br>`src.data_pipeline.generation.zalo_direct_messages`<br>`src.data_pipeline.generation.zalo_direct_messages_01_20`<br>`src.data_pipeline.generation.zalo_direct_messages_21_40`<br>`src.data_pipeline.generation.zalo_direct_messages_41_60`<br>`src.data_pipeline.generation_runs`<br>`src.data_pipeline.judge_merge`<br>`src.data_pipeline.manual_review_sheet`<br>`src.data_pipeline.publication`<br>`src.data_pipeline.recovery`<br>`src.data_pipeline.scraper`<br>`src.data_pipeline.scraper.extractors`<br>`src.data_pipeline.scraper.ncsc_scraper`<br>`src.data_pipeline.scraper.rate_limiter`<br>`src.data_pipeline.scraper.real_sources`<br>`src.data_pipeline.versioning.build`<br>`src.data_pipeline.workflows` |
| `ownership_indexes` | `src.model_adaptation.legacy.phase40`<br>`src.model_adaptation.legacy.phase41` |

#### Tool inventory

| Path | Lifecycle | Language | Kind | Language scope | Imports | Routes |
| --- | --- | --- | --- | --- | --- | --- |
| `scripts/START_DEMO_UI.bat` | `active` | `batch` | `runtime_launcher` | `phase_neutral` | — | `python -m src.runtime.cli demo` |
| `scripts/START_TEXT_ANALYZE.bat` | `active` | `batch` | `runtime_launcher` | `phase_neutral` | — | `python -m src.runtime.cli analyze` |
| `scripts/archive_phase41_source_closure.py` | `compatibility` | `python` | `provenance_cli` | `phase_41` | `__future__`<br>`argparse`<br>`contextlib`<br>`dataclasses`<br>`datetime`<br>`hashlib`<br>`json`<br>`os`<br>`pathlib`<br>`re`<br>`secrets`<br>`src.source_archiving`<br>`stat`<br>`sys`<br>`typing` | — |
| `scripts/phase40_comparison_launcher.ps1` | `historical` | `powershell` | `evidence_launcher` | `phase_40` | — | `python -s -B -m src.model_adaptation.phase40_finalize --repo-root . --output-root data/models/phase40 --bundle-root phase40-qwen-qlora-full-seed42-v1=data/models/phase40/full/qwen-qlora --bundle-root phase40-phobert-full-seed42-v12=data/models/phase40/full/phobert --gpu-identity phase40-qwen-qlora-full-seed42-v1=NVIDIA GeForce RTX 5050 Laptop GPU --gpu-identity phase40-phobert-full-seed42-v12=NVIDIA GeForce RTX 5050 Laptop GPU` |
| `scripts/phase41_one_shot_launcher.ps1` | `historical` | `powershell` | `evidence_launcher` | `phase_41` | `datetime`<br>`hashlib`<br>`importlib.abc`<br>`importlib.util`<br>`json`<br>`os`<br>`pathlib`<br>`platform`<br>`runpy`<br>`sys` | `python -I -S -s -B -c {bootstrap} {clean_root} {resolved_output}`<br>`runpy src.model_adaptation.cli phase41-run-once --output-root {resolved_output}` |

#### Static line budgets

| Budget | Maximum physical or AST lines |
| --- | ---: |
| `model_cli` | 250 |
| `new_function` | 100 |
| `new_module` | 600 |

#### Budgeted code

| Kind | Path |
| --- | --- |
| `module` | `src.artifacts` |
| `module` | `src.config` |
| `module` | `src.config.settings` |
| `module` | `src.core` |
| `module` | `src.core_binding` |
| `module` | `src.core.integrity` |
| `module` | `src.data_pipeline.core` |
| `module` | `src.data_pipeline.core.records` |
| `module` | `src.data_pipeline.core.splits` |
| `module` | `src.data_pipeline.core.text` |
| `module` | `src.data_pipeline.generation_runs` |
| `module` | `src.data_pipeline.migrations` |
| `module` | `src.data_pipeline.publication` |
| `module` | `src.data_pipeline.recovery` |
| `module` | `src.data_pipeline.workflows` |
| `module` | `src.model_adaptation.commands` |
| `module` | `src.model_adaptation.commands.adaptation` |
| `module` | `src.model_adaptation.commands.legacy_phase40` |
| `module` | `src.model_adaptation.commands.legacy_phase41` |
| `module` | `src.model_adaptation.commands.router` |
| `module` | `src.model_adaptation.legacy.phase40` |
| `module` | `src.model_adaptation.legacy.phase41` |
| `module` | `src.modeling` |
| `module` | `src.modeling.evaluation` |
| `module` | `src.modeling.evidence` |
| `module` | `src.modeling.inference` |
| `module` | `src.modeling.legacy_adapters` |
| `module` | `src.modeling.training` |
| `module` | `src.source_archiving` |
| `module` | `src.source_archiving.contracts` |
| `module` | `src.source_archiving.filesystem` |
| `module` | `src.source_archiving.service` |
| `tool` | `scripts/archive_phase41_source_closure.py` |

#### Existing budget debt

| Path | Symbol | Measured lines | Owner | Reason |
| --- | --- | ---: | --- | --- |
| `src/runtime/analyzers/accelerated.py` | `AcceleratedAnalyzer.doctor` | 118 | `runtime-accelerated-backend-maintenance` | pre-existing active function exceeds the new-function budget outside the bounded extraction scope (grew from 112 to 118 lines in the 41.1 code-review-fix pass, WR-01: doctor-status caching) |
| `src/runtime/analyzers/gguf.py` | `GGUFAnalyzer.doctor` | 115 | `runtime-gguf-backend-maintenance` | pre-existing active function exceeds the new-function budget outside the bounded extraction scope |
| `src/runtime/analyzers/local_model.py` | `<module>` | 801 | `runtime-analyzer-maintenance` | pre-existing active module exceeds the new-module budget outside the bounded extraction scope |
| `src/runtime/doctor.py` | `RuntimeDoctor.run` | 126 | `runtime-doctor-maintenance` | pre-existing active function exceeds the new-function budget outside the bounded extraction scope |
<!-- policy-groups:end -->

### Permitted adapter-to-history imports

Every row below is an actual allowed import edge. There is no wildcard and no
reverse-edge allowlist.

<!-- policy-edges:start -->
| Relation | Source | Target |
| --- | --- | --- |
| `active import` | `src.artifacts` | `src.core` |
| `active import` | `src.artifacts` | `src.core.integrity` |
| `active import` | `src.core` | `src.core` |
| `active import` | `src.core` | `src.core.integrity` |
| `active import` | `src.core.integrity` | `src.core_binding` |
| `active import` | `src.modeling.evidence` | `src.core` |
| `active import` | `src.modeling.evidence` | `src.core.integrity` |
| `active import` | `src.modeling.evidence` | `src.modeling` |
| `active import` | `src.modeling.evidence` | `src.modeling.evaluation` |
| `active import` | `src.modeling.inference` | `src.runtime` |
| `active import` | `src.modeling.inference` | `src.runtime.contracts` |
| `active import` | `src.modeling.training` | `src.modeling` |
| `active import` | `src.runtime` | `src.runtime` |
| `active import` | `src.runtime` | `src.runtime.contracts` |
| `active import` | `src.runtime.analyzers` | `src.runtime` |
| `active import` | `src.runtime.analyzers` | `src.runtime.analyzers` |
| `active import` | `src.runtime.analyzers` | `src.runtime.analyzers.base` |
| `active import` | `src.runtime.analyzers.accelerated` | `src.artifacts` |
| `active import` | `src.runtime.analyzers.accelerated` | `src.config` |
| `active import` | `src.runtime.analyzers.accelerated` | `src.config.settings` |
| `active import` | `src.runtime.analyzers.accelerated` | `src.runtime` |
| `active import` | `src.runtime.analyzers.accelerated` | `src.runtime.analyzers` |
| `active import` | `src.runtime.analyzers.accelerated` | `src.runtime.analyzers.local_model` |
| `active import` | `src.runtime.analyzers.accelerated` | `src.runtime.contracts` |
| `active import` | `src.runtime.analyzers.base` | `src.runtime` |
| `active import` | `src.runtime.analyzers.base` | `src.runtime.contracts` |
| `active import` | `src.runtime.analyzers.gguf` | `src.artifacts` |
| `active import` | `src.runtime.analyzers.gguf` | `src.config` |
| `active import` | `src.runtime.analyzers.gguf` | `src.config.settings` |
| `active import` | `src.runtime.analyzers.gguf` | `src.runtime` |
| `active import` | `src.runtime.analyzers.gguf` | `src.runtime.analyzers` |
| `active import` | `src.runtime.analyzers.gguf` | `src.runtime.analyzers.local_model` |
| `active import` | `src.runtime.analyzers.gguf` | `src.runtime.contracts` |
| `active import` | `src.runtime.analyzers.heuristic` | `src.runtime` |
| `active import` | `src.runtime.analyzers.heuristic` | `src.runtime.analyzers` |
| `active import` | `src.runtime.analyzers.heuristic` | `src.runtime.analyzers.rules` |
| `active import` | `src.runtime.analyzers.heuristic` | `src.runtime.contracts` |
| `active import` | `src.runtime.analyzers.local_model` | `src.artifacts` |
| `active import` | `src.runtime.analyzers.local_model` | `src.runtime` |
| `active import` | `src.runtime.analyzers.local_model` | `src.runtime.analyzers` |
| `active import` | `src.runtime.analyzers.local_model` | `src.runtime.analyzers.rules` |
| `active import` | `src.runtime.analyzers.local_model` | `src.runtime.contracts` |
| `active import` | `src.runtime.analyzers.rules` | `src.runtime` |
| `active import` | `src.runtime.analyzers.rules` | `src.runtime.contracts` |
| `active import` | `src.runtime.cli` | `src.runtime` |
| `active import` | `src.runtime.cli` | `src.runtime.contracts` |
| `active import` | `src.runtime.cli` | `src.runtime.demo` |
| `active import` | `src.runtime.cli` | `src.runtime.doctor` |
| `active import` | `src.runtime.cli` | `src.runtime.render` |
| `active import` | `src.runtime.cli` | `src.runtime.service` |
| `active import` | `src.runtime.demo` | `src.runtime` |
| `active import` | `src.runtime.demo` | `src.runtime.contracts` |
| `active import` | `src.runtime.demo` | `src.runtime.service` |
| `active import` | `src.runtime.doctor` | `src.artifacts` |
| `active import` | `src.runtime.doctor` | `src.config` |
| `active import` | `src.runtime.doctor` | `src.config.settings` |
| `active import` | `src.runtime.doctor` | `src.core` |
| `active import` | `src.runtime.doctor` | `src.core.integrity` |
| `active import` | `src.runtime.doctor` | `src.runtime` |
| `active import` | `src.runtime.doctor` | `src.runtime.analyzers` |
| `active import` | `src.runtime.doctor` | `src.runtime.analyzers.accelerated` |
| `active import` | `src.runtime.doctor` | `src.runtime.analyzers.gguf` |
| `active import` | `src.runtime.doctor` | `src.runtime.analyzers.heuristic` |
| `active import` | `src.runtime.doctor` | `src.runtime.contracts` |
| `active import` | `src.runtime.render` | `src.runtime` |
| `active import` | `src.runtime.render` | `src.runtime.contracts` |
| `active import` | `src.runtime.service` | `src.config` |
| `active import` | `src.runtime.service` | `src.config.settings` |
| `active import` | `src.runtime.service` | `src.modeling` |
| `active import` | `src.runtime.service` | `src.modeling.inference` |
| `active import` | `src.runtime.service` | `src.runtime` |
| `active import` | `src.runtime.service` | `src.runtime.analyzers` |
| `active import` | `src.runtime.service` | `src.runtime.analyzers.accelerated` |
| `active import` | `src.runtime.service` | `src.runtime.analyzers.base` |
| `active import` | `src.runtime.service` | `src.runtime.analyzers.gguf` |
| `active import` | `src.runtime.service` | `src.runtime.analyzers.heuristic` |
| `active import` | `src.runtime.service` | `src.runtime.contracts` |
| `active import` | `src.source_archiving.filesystem` | `src.core_binding` |
| `active import` | `src.source_archiving.filesystem` | `src.source_archiving` |
| `active import` | `src.source_archiving.filesystem` | `src.source_archiving.contracts` |
| `active import` | `src.source_archiving.service` | `src.source_archiving` |
| `active import` | `src.source_archiving.service` | `src.source_archiving.contracts` |
| `active import` | `src.source_archiving.service` | `src.source_archiving.filesystem` |
| `active tool import` | `scripts/archive_phase41_source_closure.py` | `src.source_archiving` |
| `compatibility to history` | `src.model_adaptation.cli` | `src.model_adaptation` |
| `compatibility to history` | `src.model_adaptation.commands.adaptation` | `src.model_adaptation` |
| `compatibility to history` | `src.model_adaptation.commands.adaptation` | `src.model_adaptation.catalog` |
| `compatibility to history` | `src.model_adaptation.commands.adaptation` | `src.model_adaptation.phase40_contract` |
| `compatibility to history` | `src.model_adaptation.commands.adaptation` | `src.model_adaptation.phase40_handoff` |
| `compatibility to history` | `src.model_adaptation.commands.adaptation` | `src.model_adaptation.phase40_modes` |
| `compatibility to history` | `src.model_adaptation.commands.adaptation` | `src.model_adaptation.pilot` |
| `compatibility to history` | `src.model_adaptation.commands.adaptation` | `src.model_adaptation.registry` |
| `compatibility to history` | `src.model_adaptation.commands.adaptation` | `src.model_adaptation.schemas` |
| `compatibility to history` | `src.model_adaptation.commands.legacy_phase40` | `src.model_adaptation` |
| `compatibility to history` | `src.model_adaptation.commands.legacy_phase40` | `src.model_adaptation.phase40_contract` |
| `compatibility to history` | `src.model_adaptation.commands.legacy_phase40` | `src.model_adaptation.phase40_evidence` |
| `compatibility to history` | `src.model_adaptation.commands.legacy_phase40` | `src.model_adaptation.phase40_graphs` |
| `compatibility to history` | `src.model_adaptation.commands.legacy_phase40` | `src.model_adaptation.phase40_handoff` |
| `compatibility to history` | `src.model_adaptation.commands.legacy_phase40` | `src.model_adaptation.phase40_notebooks` |
| `compatibility to history` | `src.model_adaptation.commands.legacy_phase40` | `src.model_adaptation.phase40_review` |
| `compatibility to history` | `src.model_adaptation.commands.legacy_phase41` | `src.model_adaptation` |
| `compatibility to history` | `src.model_adaptation.commands.legacy_phase41` | `src.model_adaptation.phase41_evaluation` |
| `compatibility to history` | `src.model_adaptation.convert` | `src.model_adaptation` |
| `compatibility to history` | `src.model_adaptation.convert` | `src.model_adaptation.registry` |
| `compatibility to history` | `src.model_adaptation.convert` | `src.model_adaptation.schemas` |
| `compatibility to history` | `src.model_adaptation.convert` | `src.model_adaptation.training` |
| `compatibility to history` | `src.model_adaptation.doctor` | `src.model_adaptation` |
| `compatibility to history` | `src.model_adaptation.doctor` | `src.model_adaptation.phase40_modes` |
| `compatibility to history` | `src.model_adaptation.doctor` | `src.model_adaptation.registry` |
| `compatibility to history` | `src.model_adaptation.doctor` | `src.model_adaptation.training` |
| `compatibility to history` | `src.model_adaptation.explanation_review` | `src.model_adaptation` |
| `compatibility to history` | `src.model_adaptation.explanation_review` | `src.model_adaptation.schemas` |
| `compatibility to history` | `src.model_adaptation.release_evaluation` | `src.model_adaptation` |
| `compatibility to history` | `src.model_adaptation.release_evaluation` | `src.model_adaptation.schemas` |
| `compatibility to history` | `src.model_adaptation.release_gates` | `src.model_adaptation` |
| `compatibility to history` | `src.model_adaptation.release_gates` | `src.model_adaptation.schemas` |
| `compatibility to history` | `src.model_adaptation.release_readiness` | `src.model_adaptation` |
| `compatibility to history` | `src.model_adaptation.release_readiness` | `src.model_adaptation.data` |
| `compatibility to history` | `src.model_adaptation.release_readiness` | `src.model_adaptation.schemas` |
| `compatibility to history` | `src.modeling.legacy_adapters` | `src.model_adaptation` |
| `compatibility to history` | `src.modeling.legacy_adapters` | `src.model_adaptation.phobert_training` |
| `compatibility to history` | `src.modeling.legacy_adapters` | `src.model_adaptation.training` |
<!-- policy-edges:end -->

### Historical cycles retained as debt

The active graph has zero strongly connected components. Only these four
historical components are allowed to remain:

<!-- historical-sccs:start -->
| Historical SCC members |
| --- |
| `src.model_adaptation`<br>`src.model_adaptation.catalog`<br>`src.model_adaptation.pilot`<br>`src.model_adaptation.registry` |
| `src.model_adaptation.phase40_evidence`<br>`src.model_adaptation.phase40_graphs` |
| `src.model_adaptation.phase40_final_authority`<br>`src.model_adaptation.phase40_gguf`<br>`src.model_adaptation.phase40_handoff`<br>`src.model_adaptation.phase40_phobert_release`<br>`src.model_adaptation.phase40_production_authorities`<br>`src.model_adaptation.training` |
| `src.model_adaptation.phase41_evaluation`<br>`src.model_adaptation.phase41_protocols` |
<!-- historical-sccs:end -->
