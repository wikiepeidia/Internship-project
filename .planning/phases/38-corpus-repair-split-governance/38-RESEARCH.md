# Phase 38: Corpus Repair & Split Governance - Research

**Researched:** 2026-08-08
**Domain:** Offline dataset repair, deterministic group-based data splitting, dataset versioning/manifests (Python data pipeline, no ML training in this phase)
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Split Ratio & Grouping**
- Split ratio: 80/10/10 (train/val/test), by row count.
- Grouping key: `seed_id` — every row belonging to the same seed group must land in exactly one split.
- Group-to-split assignment: deterministic hash of `seed_id` (not `random.shuffle` with a stored seed) so re-running the split logic is reproducible without depending on RNG state.
- Stratification: best-effort per-class balance within the group constraint — greedily assign groups while tracking running per-class counts, preferring assignments that keep the four classes' proportions close across splits. Perfect stratification is not required when it would break group integrity.

**Seed Concentration Cap**
- Target cap: no single `seed_id` may account for more than 8% of the final corpus (down from the current ~25% for the dominant seed).
- Enforcement: drop excess rows from over-represented seed groups rather than generating new seeds or new synthetic rows.
- "Same seed" is defined as an exact `seed_id` match — no fuzzy/near-duplicate seed-text clustering.
- When trimming an over-represented seed group down to the cap, keep the most textually diverse subset (via the existing `lexical_dedup` distance function) and drop the rest, rather than arbitrary/first-N truncation.

**Invalid Evidence Span Repair**
- For the 131 rows with invalid evidence spans: attempt automatic re-extraction of a valid span from the row's existing `text` + `xai_explanation` fields first (no new API calls, no data loss where avoidable).
- Validation rule stays exact-substring: a span is valid only if it is an exact substring of `text` (matches the existing schema's intent — no fuzzy/normalized matching).
- If no valid span can be recovered after the repair attempt, drop the row entirely rather than keeping it with an empty span list (an empty span list would weaken the evidence-grounded design principle this whole system is built on).
- This repair logic lives in a new one-off script under `src/data_pipeline/` — it is a one-time corpus repair, not a permanent addition to the generation-time validators.

**Manifest & Recovery Narrative**
- The repair's output manifest extends the project's existing SHA-256 manifest pattern (same fields/style as the manifests already produced elsewhere in `src/data_pipeline/versioning/`), not a new ad-hoc format.
- Deliverable includes a standalone markdown snippet containing the drafted `task_scam` 0.44→0.871 recovery narrative, grounded in the real Phase 7a evidence artifacts, ready to paste into the report's Data Construction chapter during Phase 42 (Report Overhaul) — this phase drafts it, Phase 42 places it.
- The repair script is committed under `src/data_pipeline/` like the rest of the pipeline, not left as an uncommitted scratch script.
- Old pre-repair corpus files (`data/synthetic/recovered-balanced.jsonl`, `data/splits/recovered-balanced/*.jsonl`) are kept as a backup/reference, not deleted, consistent with how this project has handled prior data changes (e.g. the `data/backup/` directory already holds earlier snapshots).

### Claude's Discretion

None — all four grey areas were accepted as recommended without changes.

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope. (The independent Codex judge pass and manual 100-example human check are explicitly Phase 39's scope, not this phase's.)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DATA-04 | Corpus pooled (3,000 + 413 reserved rows), repaired, and re-split by seed-group hash (not row-level) — no `seed_id` may cross a split boundary. | Confirmed pooled size is 3,413 rows across 87 unique `seed_id`s; confirmed current cross-split leakage (10 shared seed_ids between the 3,000-row pool and the 413-row reserved test file); documented the existing `_stable_bucket`/`_seed_bucket` deterministic-hash primitive in `splitter.py` to reuse, and why the existing `split_dataset()` must be extended (not reused as-is) to add real greedy stratification. See Architecture Patterns, Code Examples. |
| DATA-05 | Seed concentration measurably reduced and capped at a stated, justified threshold (currently one seed = 25% of the corpus). | Measured actual pooled concentration: **two** seeds exceed the 8% cap post-pooling (24.41% and 11.90%), not just one — important correction to the phase description's "one seed" framing. Documented cap-enforcement algorithm using `lexical_dedup` + deterministic ordering. See Common Pitfalls, Code Examples. |
| DATA-06 | Zero rows with invalid evidence spans (currently 131) — repaired in place where fixable, dropped only where not. | Ran the actual repair logic against the real files: 131 bad rows / 141 bad span instances in the 3,000-row corpus (76 rows recoverable via case-insensitive re-extraction alone, all but 2 rows recoverable with at least one valid span retained); test.jsonl adds a further 40 bad rows / 41 bad span instances not captured in the phase description's "131" figure. See Common Pitfalls, Code Examples. |
| DATA-07 | Split ratio locked (80/10/10 proposed) and recorded in a manifest with per-split class distribution. | Confirmed `settings.split_ratios` default already matches 80/10/10; documented exact extension pattern for `ManifestEntry`/`ManifestFile` to carry per-split class distribution without breaking other manifest consumers. See Architecture Patterns, Code Examples. |
| DATA-08 | The genuine `task_scam` 0.44→0.871 recovery story restored into the report as an evidenced iteration narrative. | Pulled the exact verified numbers and their real source chain (Phase 7a `07a-CONTEXT.md`/`07a-03-PLAN.md`, `dataset_statistics.tex`, `05_evaluation_and_discussion.tex`) so the drafted narrative snippet cites real artifacts, not invented ones. See Summary and Code Examples (recovery narrative source data). |
</phase_requirements>

## Summary

This phase is a pure offline Python data-engineering task: pool two existing JSONL files, repair 171 rows total (131 + 40) with invalid evidence spans, cap seed over-representation, and re-split by seed-group with best-effort class stratification — then emit a manifest and a markdown narrative snippet. No ML training, no new external dependencies, no network calls.

The codebase already contains a working deterministic-hash seed-group splitter (`src/data_pipeline/processing/splitter.py`), a lexical dedup helper (`processing/dedup.py`), and a SHA-256 manifest builder (`versioning/manifest.py`). The right approach is to **extend these three modules from within the new one-off repair script**, not reinvent them — the existing `split_dataset()` already implements the "deterministic hash of `seed_id`" half of the CONTEXT.md decision, but it does **not** implement per-class greedy stratification (it only sorts seed groups by hash bucket and slices by count) — the new script must add a genuine greedy stratified-group-assignment pass on top of the existing hash primitive. `scikit-learn>=1.8` (with `StratifiedGroupKFold`) is already an installed project dependency, but its k-fold API doesn't map cleanly onto a single-shot 80/10/10 split with a hash-derived (not RNG-derived) ordering requirement, so a small hand-rolled greedy algorithm — modeled on `StratifiedGroupKFold`'s documented approach of minimizing per-class-per-fold distribution deviation — is the better fit and stays consistent with the codebase's existing pattern in `splitter.py`.

Direct inspection of the real data files overturned two assumptions baked into the phase description: (1) after pooling the 413-row reserved test file, **two** seed_ids exceed the 8% cap (24.41% and 11.90%), not one; and (2) the 413-row test file has its own 40 rows with invalid evidence spans that are not counted in the "131" figure — the repair logic must run against the full 3,413-row pooled set, not just the 3,000-row file. A concrete repair simulation against the real 131 bad rows also shows the CONTEXT.md-mandated repair strategy (case-insensitive re-extraction, then drop) is highly effective: only 2 of 131 rows in the 3,000-row file end up unrecoverable (0 of 40 in the test file) — most "invalid" spans are simple case-mismatches between an original-cased `text` field and a lower-cased `suspicious_spans` entry.

**Primary recommendation:** Write one new module, e.g. `src/data_pipeline/repair_corpus_split_governance.py`, that (1) pools and repairs spans using a case-insensitive re-extraction pass over `text`, (2) applies the 8% cap via `lexical_dedup` + deterministic-order truncation per over-cap seed group, (3) reuses `_stable_bucket`-style SHA-256 hashing but adds a real greedy stratified-group assignment loop, (4) writes new split files to a new versioned path (not overwriting `data/splits/recovered-balanced/`), and (5) calls `build_manifest()`/`save_manifest()` from `versioning/manifest.py` and layers per-split class-distribution + repair-stats metadata around it rather than modifying the shared `ManifestEntry`/`ManifestFile` Pydantic models.

## Architectural Responsibility Map

This is a single-tier, offline batch-processing phase — there is no browser/API/CDN split. Tiers below are this project's own established pipeline layers.

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Corpus pooling + span repair | Data Pipeline (`src/data_pipeline/`, new one-off script) | — | Pure offline transform of existing JSONL records; no network, no model calls (CONTEXT.md explicitly forbids new API calls here) |
| Seed concentration cap enforcement | Data Pipeline (new script), reusing `processing/dedup.py::lexical_dedup` | — | Diversity-aware trimming is a dataset-processing concern, already has a reusable helper in this tier |
| Seed-group stratified split assignment | Data Pipeline (new script), extending `processing/splitter.py` | — | Splitting is already owned by `splitter.py` in this codebase; the new greedy-stratification logic should live alongside/extend it, not duplicate it elsewhere |
| Manifest + per-split class distribution | Versioning (`src/data_pipeline/versioning/manifest.py`) | Data Pipeline (new script composes on top) | Manifest schema and SHA-256 discipline is already centralized here; new script should call into it rather than hand-roll a second hashing routine |
| Recovery narrative markdown snippet | Report/Docs (deliverable only, consumed later by Phase 42) | — | Pure content artifact; no code dependency, but content must be traceable to real Phase 7a artifacts (see Code Examples) |
| Downstream training/eval consumption | Model Adaptation (`src/model_adaptation/`) — **out of scope for Phase 38** | — | Phase 40 (training) and Phase 39 (re-judge) read this phase's output; Phase 38 must not touch `src/model_adaptation/cli.py`'s hardcoded `recovered-balanced` default paths (see Common Pitfalls) |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib `hashlib` | 3.13 stdlib | SHA-256 hashing for both seed-group bucketing and manifest file integrity | Already the exact mechanism used in `splitter.py::_stable_bucket` and `manifest.py::build_manifest` — zero new dependency, deterministic, no RNG |
| `pydantic` | >=2.12 (already a dependency) [VERIFIED: pyproject.toml] | Validate pooled/repaired records against `DatasetRecord` before writing splits | Already the schema-of-record for every pipeline stage (`schemas.py::DatasetRecord`) |
| Python stdlib `json` / `pathlib` | 3.13 stdlib | JSONL read/write, path handling | Matches every existing pipeline module (`versioning/build.py`, `cli.py`) |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `rapidfuzz` (via `dedup.py::lexical_dedup`) | >=3.14 (already a dependency) [VERIFIED: pyproject.toml] | Near-duplicate detection to select the "most diverse subset" when trimming an over-cap seed group | Only when a seed group exceeds the 8% row cap and needs trimming, per CONTEXT.md's locked decision |
| `scikit-learn` | >=1.8, installed 1.8.0 [VERIFIED: `python -c "import sklearn; print(sklearn.__version__)"` in this environment] | **Not recommended as the split mechanism for this phase** — see Alternatives Considered | Already installed; cite as the standard reference algorithm to model the hand-rolled greedy stratifier on (`StratifiedGroupKFold`'s documented deviation-minimization approach), but do not adopt it directly |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Hand-rolled greedy stratified-group assignment (recommended) | `sklearn.model_selection.StratifiedGroupKFold` | `StratifiedGroupKFold` is a k-fold cross-validator, not a single-shot ratio splitter. To get an 80/10/10 split you'd need `n_splits=10`, take 1 fold as test, then re-run for val — extra plumbing. Its `shuffle=False` mode uses row order, not a hash of `seed_id`, so satisfying CONTEXT.md's "deterministic hash, not RNG" requirement would still require pre-sorting the input by `hash(seed_id)` before calling it. A ~40-line hand-rolled loop (see Code Examples) gives full control over the 8%-cap interaction and matches the codebase's existing `splitter.py` style more closely. **This is a recommendation, not a hard block** — `StratifiedGroupKFold` is a legitimate, already-installed alternative if the planner prefers to depend on it. |
| `lexical_dedup` + deterministic-order truncation for the 8% cap (recommended) | A true "maximum diversity subset" selection (e.g. farthest-point sampling over embeddings) | `lexical_dedup` only removes near-duplicate pairs above a similarity threshold — it does not rank a fixed-size subset by diversity. True diversity-maximizing subset selection would need `sentence-transformers` embeddings (already a dependency) and an O(n²) or greedy farthest-point algorithm — overkill for a cap enforcement step and not what CONTEXT.md asked for (CONTEXT.md explicitly names `lexical_dedup`, the existing near-duplicate function, not a new diversity-maximization function). |

**Installation:** No new packages required. All modules above are already declared in `pyproject.toml` (confirmed via direct read) and importable in this environment (confirmed via `python -c "import sklearn"`).

**Version verification:** `scikit-learn` confirmed installed at `1.8.0` in this environment (`python -c "import sklearn; print(sklearn.__version__)"` → `1.8.0`), matching the `>=1.8` pin in `pyproject.toml`. `pydantic>=2.12` and `rapidfuzz>=3.14` confirmed present in `pyproject.toml` (not independently re-verified against PyPI since they are already installed and imported successfully by the existing test suite in this repo).

## Package Legitimacy Audit

**Not applicable — this phase introduces no new external packages.** All functionality is implemented using Python 3.13 stdlib (`hashlib`, `json`, `pathlib`) plus already-installed, already-declared project dependencies (`pydantic`, `rapidfuzz` via `dedup.py`, optionally `scikit-learn` — all confirmed present in `pyproject.toml` and importable in this environment). No `npm view` / `pip index versions` / registry check is needed because nothing new is being installed.

## Architecture Patterns

### System Architecture Diagram

```
data/synthetic/recovered-balanced.jsonl (3,000 rows)
data/splits/recovered-balanced/test.jsonl (413 rows)
            |
            v
   [1. POOL] concatenate both files -> 3,413 rows, 87 unique seed_id groups
            |
            v
   [2. SPAN REPAIR] for each row's suspicious_spans:
        - exact substring of text?          -> keep as-is
        - case-insensitive match in text?   -> re-extract exact-cased substring, keep
        - not found even case-insensitively -> drop that span
        row survives if >=1 span remains; else row is dropped entirely
            |
            v
   [3. SEED CONCENTRATION CAP] group remaining rows by seed_id
        for each seed_id group > 8% of surviving corpus:
          order group deterministically (hash) -> lexical_dedup(threshold) to drop
          near-duplicates -> truncate remainder to the 8% cap count
            |
            v
   [4. SEED-GROUP STRATIFIED SPLIT] deterministic hash(seed_id) orders all seed
        groups; greedy per-class running-count assignment places each group into
        train/val/test targeting 80/10/10 by row count and near-equal per-class
        proportions across splits (best-effort; group integrity always wins)
            |
            v
   [5. WRITE OUTPUTS]
        data/splits/<new-versioned-name>/{train,val,test}.jsonl  (DatasetRecord-validated)
        data/manifests/manifest-<new-versioned-name>.json         (SHA-256 + per-split class counts + repair stats)
        <recovery-narrative-snippet>.md                           (task_scam 0.44->0.871 narrative, for Phase 42)
            |
            v
   Phase 39 (independent re-judge) reads repaired corpus
   Phase 40 (training) reads new split files
```

### Recommended Project Structure

```
src/data_pipeline/
├── repair_corpus_split_governance.py   # NEW — the one-off repair script (name is a suggestion, not locked)
│   ├── pool_records()                  # load + concat the two input JSONL files
│   ├── repair_evidence_spans()         # case-insensitive re-extraction + drop logic
│   ├── enforce_seed_cap()              # 8% cap via lexical_dedup + deterministic truncation
│   ├── assign_stratified_group_split() # NEW greedy stratified-group split (extends splitter.py's hash primitive)
│   └── main()/CLI entrypoint           # writes splits + manifest + narrative snippet
├── processing/
│   ├── splitter.py                     # REUSE _stable_bucket/_seed_bucket hash primitive; do not duplicate hashing logic
│   └── dedup.py                        # REUSE lexical_dedup as-is (no changes needed)
├── versioning/
│   └── manifest.py                     # REUSE build_manifest()/save_manifest() for the file-hash part of the output manifest
└── schemas.py                          # REUSE DatasetRecord for validation of every written row
```

### Pattern 1: Reuse the existing deterministic-hash primitive, don't reinvent it

**What:** `splitter.py` already contains `_stable_bucket(value, salt)` which does `sha256(f"{salt}:{value}")` → take the first 8 hex chars → divide by `0xFFFFFFFF` to get a float in `[0, 1)`. This is the codebase's established "deterministic hash of a string, not RNG" pattern and is exactly the mechanism CONTEXT.md's split-ratio decision calls for.
**When to use:** Any place a seed_id (or other string key) needs a stable, reproducible position for bucketing.
**Example:**
```python
# Source: src/data_pipeline/processing/splitter.py (existing, verified in this codebase)
import hashlib

def _stable_bucket(value: str, salt: str) -> float:
    digest = hashlib.sha256(f"{salt}:{value}".encode("utf-8")).hexdigest()
    return int(digest[:8], 16) / 0xFFFFFFFF
```
The new repair script should import this directly from `splitter.py` (or a thin re-export) rather than re-implementing SHA-256 bucketing — this keeps the "deterministic hash of seed_id, not `random.shuffle`" property consistent with the rest of the codebase and testable against the existing `tests/data_pipeline/test_splitter.py` patterns.

### Pattern 2: Existing `split_dataset()` does NOT implement greedy per-class stratification — extend it, don't assume it already does what CONTEXT.md asks for

**What:** `split_dataset()` in `splitter.py` groups records by `(label, seed_id)`, flags "underdiverse" labels (labels with fewer seed groups than active splits) for a record-level fallback, but for the normal case it just does `_assign_seed_group_splits()` — which sorts **all** seed_ids together (across all four classes) by hash bucket and slices by count. It has **no per-class running-count tracking** and **no greedy rebalancing** — it will produce whatever class mix falls out of the hash ordering, which is not the "best-effort per-class balance" behavior CONTEXT.md locked in.
**When to use:** This gap is exactly what the new one-off script must add. Model the new logic on `StratifiedGroupKFold`'s documented approach ([scikit-learn docs](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.StratifiedGroupKFold.html)): process groups in a deterministic order, and for each group, assign it to whichever split currently minimizes the resulting deviation from the target per-class proportions, subject to the split's remaining row-count budget.
**Example:**
```python
# NEW logic for Phase 38 — models StratifiedGroupKFold's documented deviation-minimization
# approach on top of splitter.py's existing _stable_bucket() hash primitive.
from collections import defaultdict

def assign_stratified_group_split(
    seed_groups: dict[str, list[dict]],   # seed_id -> list of DatasetRecord dicts
    ratios: tuple[float, float, float] = (0.8, 0.1, 0.1),
    salt: str = "v38-repair",
) -> dict[str, str]:
    """Deterministic-hash-ordered, greedy per-class-balanced seed-group split assignment."""
    total_rows = sum(len(rows) for rows in seed_groups.values())
    split_names = ("train", "val", "test")
    target_rows = {name: total_rows * ratio for name, ratio in zip(split_names, ratios)}
    labels = sorted({r["label"] for rows in seed_groups.values() for r in rows})

    running_rows: dict[str, int] = {name: 0 for name in split_names}
    running_class_counts: dict[str, dict[str, int]] = {name: defaultdict(int) for name in split_names}
    assignments: dict[str, str] = {}

    # Deterministic order: sort seed groups by hash bucket (NOT random.shuffle)
    ordered_seed_ids = sorted(seed_groups, key=lambda sid: (_stable_bucket(sid, salt), sid))

    for seed_id in ordered_seed_ids:
        rows = seed_groups[seed_id]
        group_label_counts = defaultdict(int)
        for r in rows:
            group_label_counts[r["label"]] += 1

        best_split, best_score = None, float("inf")
        for name in split_names:
            # Respect row-count budget: skip a split once it's already at/over target,
            # unless every split is over budget (last-resort assignment).
            over_budget = running_rows[name] + len(rows) > target_rows[name] * 1.05
            if over_budget and any(
                running_rows[n] + len(rows) <= target_rows[n] * 1.05 for n in split_names
            ):
                continue
            # Score = how much this assignment would skew per-class proportions
            # in `name` away from the global per-class proportions (lower is better).
            hypothetical = dict(running_class_counts[name])
            for label, count in group_label_counts.items():
                hypothetical[label] = hypothetical.get(label, 0) + count
            hyp_total = running_rows[name] + len(rows)
            score = sum(
                abs(hypothetical.get(label, 0) / hyp_total - 0.25)  # 4 balanced classes -> target 25% each
                for label in labels
            ) if hyp_total else 0.0
            if score < best_score:
                best_split, best_score = name, score

        assignments[seed_id] = best_split
        running_rows[best_split] += len(rows)
        for label, count in group_label_counts.items():
            running_class_counts[best_split][label] += count

    return assignments
```
This is illustrative pseudocode-grade Python, not a drop-in file — the planner/executor should adapt the budget-tolerance (`1.05` above) and target-proportion logic (the `0.25` hardcodes 4-balanced-classes; make this data-driven from the actual observed global class proportions instead) to the real pooled/repaired/capped record set.

### Pattern 3: Manifest extension — compose, don't modify the shared schema

**What:** `ManifestEntry`/`ManifestFile` in `schemas.py` and `build_manifest()`/`save_manifest()` in `versioning/manifest.py` are shared by every pipeline stage (`versioning/build.py::DatasetBuilder` uses them for every prior split build). DATA-07 requires "a manifest with per-split class distribution" — but `ManifestFile` only has `sha256`, `records`, `bytes`. Adding a `class_distribution` field directly to the shared `ManifestFile` model would be a schema change that affects every other manifest consumer/writer in the codebase.
**When to use:** Compose instead — call the existing `build_manifest()` unchanged to get the SHA-256/`records`/`bytes` part (this satisfies "extends the... SHA-256 manifest pattern... not a new ad-hoc format"), then wrap it in a phase-specific dict/model that adds the extra fields alongside it.
**Example:**
```python
# Source: extends src/data_pipeline/versioning/manifest.py (existing, verified in this codebase)
import json
from src.data_pipeline.versioning.manifest import build_manifest, save_manifest

def build_repair_manifest(splits_dir, version_tag, split_class_counts, repair_stats):
    base_manifest = build_manifest(splits_dir, version_tag)  # existing SHA-256 builder, unchanged
    payload = {
        "manifest": json.loads(base_manifest.model_dump_json()),  # reuse existing ManifestEntry shape verbatim
        "split_class_distribution": split_class_counts,            # NEW: {"train": {"bank_impersonation": 1866, ...}, ...}
        "repair_stats": repair_stats,                              # NEW: {"rows_pooled": 3413, "rows_span_repaired": 115,
                                                                    #       "rows_dropped_unrecoverable_span": 2,
                                                                    #       "rows_dropped_seed_cap": <n>, "seed_cap_pct": 0.08}
    }
    return payload  # caller writes this dict via json.dump(), separate from save_manifest()'s ManifestEntry-only file
```

### Anti-Patterns to Avoid

- **Reusing `split_dataset()`/`split_and_dedup()` unmodified for this phase:** They implement hash-based grouping but not the greedy per-class stratification CONTEXT.md locked in, and `split_and_dedup()` also runs `cross_split_dedup()` (semantic near-duplicate removal across splits via `sentence-transformers`), which is a different, heavier concern not requested for this phase — don't pull it in accidentally by calling the wrong entrypoint.
- **Modifying the shared `ManifestEntry`/`ManifestFile` Pydantic models to add `class_distribution` fields:** This would ripple into every other manifest build/verify call site (`DatasetBuilder.build_splits`, `verify_manifest`). Compose around them instead (Pattern 3).
- **Treating "131 rows" as the complete invalid-span universe:** It is the count for `data/synthetic/recovered-balanced.jsonl` alone. The separately pooled `data/splits/recovered-balanced/test.jsonl` (413 rows) has an additional 40 bad rows not included in that figure — the repair pass must run on the full pooled 3,413-row set.
- **Overwriting `data/splits/recovered-balanced/`:** CONTEXT.md explicitly locks the old files as a kept backup/reference. Write to a new, clearly versioned directory (e.g. `data/splits/recovered-balanced-v2-repaired/` or a date/version-tagged name — exact name is Claude's/planner's call, just don't reuse the old path).
- **Touching `src/model_adaptation/cli.py`'s hardcoded `recovered-balanced` path defaults:** These are read by Phase 40 (training), which is out of scope for Phase 38. Updating them here would be scope creep into a later phase's job; the new manifest should simply document the new canonical path clearly enough for Phase 39/40 to pick up.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Near-duplicate detection within an over-cap seed group | A custom text-similarity function | `src/data_pipeline/processing/dedup.py::lexical_dedup` | Already implements `SequenceMatcher`/`rapidfuzz.fuzz.ratio`-based near-dup detection at a configurable threshold, already used for exactly this kind of dataset-hygiene pass elsewhere in the pipeline |
| SHA-256 file integrity manifest | A new hashing/manifest format | `src/data_pipeline/versioning/manifest.py::build_manifest`/`save_manifest` | Already the established pattern this exact project uses for every prior dataset release; CONTEXT.md explicitly requires reusing it |
| Deterministic reproducible string-to-bucket hashing | `random.shuffle(seed_list, ...)` with a stored seed, or a home-grown hash function | `hashlib.sha256` on `f"{salt}:{value}"`, truncated to an int and normalized (as `splitter.py::_stable_bucket` already does) | CONTEXT.md explicitly rejects RNG-based shuffling; SHA-256 truncation is the standard "hash bucketing" technique used by TensorFlow Data Validation and widely documented as more robust than seeded shuffling when the input dataset can grow over time |
| DatasetRecord shape validation | Ad-hoc dict key checks | `src/data_pipeline/schemas.py::DatasetRecord.model_validate(...)` | Already the schema of record for every pipeline stage; every written row (train/val/test) should be validated against it before being written to disk |

**Key insight:** Every piece of infrastructure this phase needs (hashing, dedup, manifesting, schema validation) already exists in this codebase in a working, tested form. The actual net-new code is narrow: the span-repair loop, the 8%-cap trimming loop, and the greedy stratification loop — everything else is composition of existing functions.

## Common Pitfalls

### Pitfall 1: Assuming only one seed_id needs capping

**What goes wrong:** The phase description says "one seed_id currently accounts for ~25% of the 3,000-row corpus," which is true for the 3,000-row file alone (`seed_1a4f7d4d7c53` = 758/3000 = 25.27%). But after pooling with the 413-row reserved test file (the phase's own required first step), a **second** seed_id also crosses the 8% cap: `seed_157ce0adb043` grows from 6.77% in the 3,000-row file to **11.90%** (406/3,413 rows) once its 203 rows in the main file are combined with additional rows for the same `seed_id` in the reserved test file.
**Why it happens:** The reserved test file was drawn from the same original synthetic pool, so it shares `seed_id`s with the main corpus (10 of 87 unique seed_ids overlap) — this is itself an instance of the DATA-04 cross-split-leakage bug this phase exists to fix.
**How to avoid:** Implement the 8% cap check as a general threshold sweep over **all** seed_ids in the pooled+repaired corpus (`for seed_id, count in Counter(...).items(): if count/total > 0.08: trim`), not as a special case for the one named seed.
**Warning signs:** If the repair script's cap-enforcement step only ever looks at one hardcoded seed_id, it will silently miss `seed_157ce0adb043` (and any other seed that crosses 8% after pooling).

### Pitfall 2: Treating the "131 invalid span rows" figure as complete

**What goes wrong:** 131 is the count for `data/synthetic/recovered-balanced.jsonl` (3,000 rows) only. `data/splits/recovered-balanced/test.jsonl` (413 rows) — which this phase is explicitly required to pool in — has its own 40 rows with invalid spans (41 bad span instances). If the repair script only processes the 3,000-row file, the pooled 3,413-row output will still contain up to 40 invalid-span rows, and DATA-06 ("Zero rows with invalid evidence spans") will not actually be satisfied.
**Why it happens:** The phase description's numbers were sourced from an earlier audit of the 3,000-row file alone, before the "pool first" requirement was locked in CONTEXT.md.
**How to avoid:** Run the span-validation/repair pass **after** pooling, over the full 3,413-row set, and verify zero invalid spans remain in the final output as a hard post-condition check (not just a spot check).
**Warning signs:** A verification script that greps only `data/synthetic/recovered-balanced.jsonl` for invalid spans instead of the final pooled+repaired output file.

### Pitfall 3: Most "invalid" spans are simple case mismatches — case-insensitive re-extraction alone resolves the majority

**What goes wrong / opportunity:** A live simulation of "exact substring valid, else case-insensitive re-extract, else drop the span" against the real 131 bad rows in the 3,000-row file shows: 80 of 141 bad span instances (57%) are pure case mismatches (e.g. span `"tai khoan cua ban vua bi truy cap tu thiet bi la"` vs. actual text `"...Tai khoan cua ban vua bi truy cap tu thiet bi la..."` — same text, different leading capitalization) and are fully recoverable by finding the span case-insensitively in `text` and replacing it with the exact-cased substring found there. Only 61 span instances across 2,349 total spans in the corpus are genuinely absent from `text` (usually because the span has Vietnamese diacritics while the corresponding `text` field is the ASCII-transliterated SMS-style version, or because the span is a paraphrase/reordering of nearby text rather than a literal substring). Applying this repair strategy leaves only **2 of 131 rows** in the 3,000-row file (and **0 of 40** in the 413-row test file) with zero valid spans remaining — i.e. almost the entire "131" figure is repairable in place, not droppable.
**Why it happens:** `prompts.py` instructs the generation LLM that "suspicious_spans must contain up to 3 exact substrings from the generated text" (a prompt-level instruction only — there is no code-level enforcement anywhere in the pipeline that validates this at generation time), so the LLM sometimes emitted a lower-cased or diacritic-normalized paraphrase of the actual substring instead of a literal copy-paste.
**How to avoid:** Implement the two-tier repair exactly as CONTEXT.md specifies (exact match → case-insensitive re-extraction → drop that individual span → drop the row only if zero spans remain), and don't assume the repair rate will be low — most rows survive with all their intended evidence intact.
**Warning signs:** A repair implementation that drops any row with an invalid span outright, without attempting the case-insensitive re-extraction step first — this would unnecessarily discard ~127 otherwise-good rows for no reason CONTEXT.md asked for.

### Pitfall 4: `split_dataset()`'s "underdiverse label" fallback silently reverts to non-group-aware splitting for scarce labels

**What goes wrong:** The existing `split_dataset()` in `splitter.py` has a fallback path: if a label has fewer unique `seed_id` groups than there are active splits (3), it moves that label's records out of seed-group splitting entirely and does **record-level** hash bucketing instead — meaning a single `seed_id`'s rows for that label could end up split across train/val/test, which is exactly the cross-split leakage bug DATA-04 requires eliminating.
**Why it happens:** This fallback exists to guarantee every split gets non-zero support for every label, even when a label has too few distinct seeds to distribute across 3 splits.
**How to avoid:** After pooling + repair + cap enforcement, check whether every one of the four labels (`bank_impersonation`, `zalo_social_engineering`, `task_scam`, `benign`) has at least 3 unique seed_ids (it does in the current data — 87 unique seed_ids across 4 roughly-balanced labels). If the new script reuses any part of `split_dataset()`'s logic, explicitly confirm this fallback path is never triggered for the final dataset, or reject its record-level behavior entirely and always keep seed-group integrity (accepting unequal per-split label support in the rare case a label is seed-scarce, rather than accepting leakage).
**Warning signs:** A downstream check (Phase 39/40) finding a `seed_id` present in more than one of the new `train.jsonl`/`val.jsonl`/`test.jsonl` files.

## Code Examples

### Real seed_id / row shape (verified by reading the actual files)

```json
// Source: data/synthetic/recovered-balanced.jsonl, row 1 (verified by direct read in this session)
{
  "text": "VIETCOMBANK: Tai khoan cua ban vua bi truy cap tu thiet bi la. De bao ve account, xac thuc ngay qua link: http://vcb-secure-verify.net/login . Neu khong xac thuc trong 15 phut, Internet Banking se bi khoa. Lien he: 0934.872.651",
  "label": "bank_impersonation",
  "risk_tier": "high-risk",
  "suspicious_spans": [
    "http://vcb-secure-verify.net/login",
    "tai khoan cua ban vua bi truy cap tu thiet bi la",
    "Internet Banking se bi khoa"
  ],
  "xai_explanation": "Tin nhắn giả mạo Vietcombank dùng cảnh báo khẩn về thiết bị lạ và đường link không chính thức để ép người dùng nhấp vào trang lừa đảo.",
  "source": "synthetic_claude",
  "seed_id": "seed_0dbd0f1e898c"
}
```
Note the second `suspicious_spans` entry above (`"tai khoan cua ban..."`) is itself an example of the case-mismatch bug from Pitfall 3 — the real `text` has `"Tai khoan cua ban..."` (capital T), so this exact row is one of the 131 currently-invalid rows, and is fully repairable via case-insensitive re-extraction.

`seed_id` format confirmed across both files: `seed_` + 12 lowercase hex chars (e.g. `seed_0dbd0f1e898c`, `seed_10a6b28919e6`). Same field name, same format, in both `data/synthetic/recovered-balanced.jsonl` and `data/splits/recovered-balanced/test.jsonl` — no transformation needed when pooling.

### Real pooled-corpus measurements (computed against the actual files in this session)

| Metric | Value | Source |
|--------|-------|--------|
| `recovered-balanced.jsonl` rows | 3,000 | direct file read + `wc -l` |
| `recovered-balanced/test.jsonl` rows | 413 | direct file read + `wc -l` |
| Pooled total rows | 3,413 | computed |
| Unique `seed_id`s (pooled) | 87 | computed |
| `seed_id`s shared between the two files (current leakage) | 10 | computed |
| Dominant seed share (pooled) | `seed_1a4f7d4d7c53` = 833 rows = 24.41% | computed |
| Second over-cap seed (pooled) | `seed_157ce0adb043` = 406 rows = 11.90% | computed — **not mentioned in the phase description, see Pitfall 1** |
| 8% cap in absolute rows (pre-repair pooled size) | ≈273 rows | computed (0.08 × 3,413); recompute against final post-repair row count for the real cap |
| Invalid-span rows, `recovered-balanced.jsonl` (3,000) | 131 rows / 141 bad span instances | computed — matches DATA-06's cited figure exactly |
| Invalid-span rows, `test.jsonl` (413) | 40 rows / 41 bad span instances | computed — **not included in DATA-06's "131" figure, see Pitfall 2** |
| Repairable via case-insensitive re-extraction (3,000-row file) | 80 of 141 bad span instances (57%) | computed |
| Rows fully unrecoverable after repair (3,000-row file) | 2 of 131 | computed |
| Rows fully unrecoverable after repair (413-row file) | 0 of 40 | computed |
| `settings.split_ratios` default | `(0.8, 0.1, 0.1)` | `src/config/settings.py` line 38 — already matches the locked 80/10/10 ratio |

### Recovery narrative source data (for the DATA-08 markdown snippet)

Real, verified numbers to ground the drafted narrative — do not invent figures beyond these:

| Fact | Value | Source |
|------|-------|--------|
| Original task_scam recall (pre-recovery) | 0.44 | `.planning/phases/07a-task-scam-recall-recovery/07a-CONTEXT.md` line 9; `documents/reports/latex/chapters/05_evaluation_and_discussion.tex` narrative |
| Root cause | 750 original `task_scam` rows were narrow in scenario coverage / linguistically too close to benign | `07a-CONTEXT.md` D-04/D-05 |
| Fix applied | 400 new targeted `task_scam` rows generated across 5 explicit scenario axes (like/follow/comment farms, Shopee/Lazada review-bombing, crypto referral schemes, fake purchase seeding, Zalo/Telegram livestream engagement), enriched via a conditional prompt block added in `src/data_pipeline/generation/prompts.py` | `07a-CONTEXT.md` D-06; `07a-01-SUMMARY.md` (`_TASK_SCAM_SCENARIO_AXES`); real file `data/synthetic/task-scam-recovery-2026-05-28.jsonl` (400 rows, all `label=task_scam`, confirmed by direct read in this session) |
| Recovered recall | 0.871 | `documents/reports/latex/tables/dataset_statistics.tex` line 24 and `chapters/05_evaluation_and_discussion.tex` line 36 (both compiled-report source, verified by direct read) |
| Held-out support for task_scam at 0.871 | 62 examples (val split) | `chapters/05_evaluation_and_discussion.tex` line 36; also matches `STATE.md`'s "task_scam support raised from 18 to 62" |
| Recall floor applied | ≥0.80 (relaxed from the original 0.90 floor used for the other two risky labels) | `07a-CONTEXT.md` D-01 |
| Adapter version tag | `task-scam-recovery-2026-05-28` | `07a-CONTEXT.md` D-10; `STATE.md` |
| Gate bug fixed alongside the data fix | `audit.ready` previously stayed `true` even when `task_scam` recall was 0.44 (per-label recall floors were computed but never actually gated `ready`); fixed in the same phase | `07a-CONTEXT.md` D-02; `07a-01-SUMMARY.md` "Task 1: Gate Bug Fix" |

This gives the recovery-narrative snippet a fully evidenced chain: original failure (0.44, gate bug) → root-cause audit → targeted 400-row generation with named scenario axes → retrain → 0.871 recall on 62 held-out examples, all traceable to real files already in this repo.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| `random.shuffle(seed_ids, random_state=N)` for split assignment | Deterministic hash of the group key (`hashlib.sha256`), independent of any stored RNG state | Established in this codebase since `splitter.py`'s current form (pre-existing, reused here) | Splits are reproducible even as the underlying dataset grows/changes, without needing to persist or replay an RNG seed — this is also the industry-documented pattern (e.g. the "hash-based splitting" technique described by TensorFlow Data Validation and multiple ML-engineering writeups) for exactly the reason CONTEXT.md gives |

**Deprecated/outdated:** None specific to this phase — the codebase's existing splitting/dedup/manifest infrastructure is already using current, sound patterns; this phase's job is to extend it with a stratification pass it currently lacks, not to replace anything.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The new repair script's exact filename/module path (`src/data_pipeline/repair_corpus_split_governance.py`) is a naming suggestion, not something locked by CONTEXT.md (which only locks the directory, `src/data_pipeline/`). | Recommended Project Structure | Low — purely cosmetic; the planner/executor can choose any reasonable filename under the locked directory. |
| A2 | The new output split directory name (e.g. `data/splits/recovered-balanced-v2-repaired/`) is a suggestion; CONTEXT.md only locks "a new, clearly versioned path (not overwriting the existing `recovered-balanced/` split directory)." | Anti-Patterns to Avoid | Low — any non-colliding, clearly-versioned name satisfies the locked constraint. |
| A3 | The greedy stratified-group-split pseudocode's exact scoring function (L1 deviation from a flat 25%-per-class target, with a 1.05x row-budget tolerance) is illustrative, not a specified algorithm from CONTEXT.md — CONTEXT.md only specifies the *goal* ("greedily assign groups while tracking running per-class counts, preferring assignments that keep the four classes' proportions close"), not the exact math. | Code Examples, Pattern 2 | Medium — if the planner/executor implements a materially different scoring function, the qualitative outcome (best-effort per-class balance, group integrity preserved) should still hold, but exact per-split class counts will differ from what's shown here. The planner should treat the target proportions as "whatever the pooled+repaired+capped corpus's actual global class mix is" (currently near-25%-each, but will shift slightly after the 8% cap trims two seed groups), not a hardcoded 25%. |

**If this table is empty:** N/A — see entries above. All core facts (row counts, seed_id format, existing code behavior, recall numbers) were verified by direct file/code inspection in this session, not assumed.

## Open Questions

1. **Exact final output split directory/version-tag name**
   - What we know: CONTEXT.md requires a "new, clearly versioned path (not overwriting the existing `recovered-balanced/` split directory)."
   - What's unclear: No specific name was locked (this was inside the "Claude's Discretion: None — all accepted as recommended" scope, but the *recommended* name itself wasn't specified in CONTEXT.md's text).
   - Recommendation: The planner should pick a name that encodes both the intent and a date/version, e.g. `data/splits/recovered-balanced-repaired-2026-08/` or `data/splits/v7-corpus-repair/`, and reference it consistently in the manifest and in Phase 39/40's future context.

2. **Exact scoring function for the greedy stratification pass**
   - What we know: CONTEXT.md specifies the goal (best-effort per-class balance, greedy, tracking running counts) but not exact math.
   - What's unclear: Whether "close proportions" should be measured against the global corpus's actual class mix (recommended, since the corpus should already be ~25%/25%/25%/25% per the original `DATA-02` generation design) or some other target.
   - Recommendation: Compute the actual global per-class proportions from the pooled+repaired+capped corpus first, then use those (not a hardcoded 25%) as the greedy algorithm's target — this stays correct even if the 8% cap trimming slightly shifts the class balance away from perfectly even.

## Security Domain

`security_enforcement` is not explicitly disabled in `.planning/config.json` (absent = enabled per policy), so this section is included for completeness, though almost nothing applies — this is an offline, local, no-network, no-user-input batch script operating only on files already inside the repo.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-------------------|
| V2 Authentication | No | No auth surface — local batch script |
| V3 Session Management | No | No sessions |
| V4 Access Control | No | No multi-user access control surface |
| V5 Input Validation | Yes (light) | Every written row must pass `DatasetRecord.model_validate(...)` (existing Pydantic schema) before being written to a split file — this is the one real "input validation" boundary in this phase, and it's already the established codebase pattern |
| V6 Cryptography | Yes (non-secret use only) | SHA-256 via stdlib `hashlib`, reusing `manifest.py`'s existing pattern — used only for content-integrity hashing and deterministic bucketing, never for secrets/passwords, so no key-management or crypto-library selection concerns apply |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|----------------------|
| Silent data corruption if the repair script is re-run against already-repaired output (double-repair changing spans that are already valid, or double-counting seed caps) | Tampering (of data integrity, not security) | Make the repair script idempotent: validate exact-substring first before attempting any re-extraction, and always read from the original two locked input files (`recovered-balanced.jsonl` + `recovered-balanced/test.jsonl`), never from its own prior output, so re-runs are safe and reproducible |
| Manifest hash mismatch going undetected by downstream phases (Phase 39/40 training on a corpus that silently changed after the manifest was written) | Tampering | Reuse `manifest.py::verify_manifest()` as a documented post-write check in the phase's own verification step, exactly as the existing pipeline does for prior releases |

## Sources

### Primary (HIGH confidence)
- Direct file reads in this session: `src/data_pipeline/schemas.py`, `src/data_pipeline/processing/dedup.py`, `src/data_pipeline/processing/splitter.py`, `src/data_pipeline/versioning/manifest.py`, `src/data_pipeline/versioning/build.py`, `src/data_pipeline/processing/normalizer.py`, `src/data_pipeline/cli.py`, `pyproject.toml`, `src/config/settings.py` — all `[VERIFIED: local codebase read]`
- Direct data inspection in this session (Python one-liners against the real files): `data/synthetic/recovered-balanced.jsonl`, `data/splits/recovered-balanced/{train,val,test}.jsonl` — row counts, seed_id distributions, span-validity simulation, cross-split overlap — all `[VERIFIED: local data read]`
- `.planning/phases/38-corpus-repair-split-governance/38-CONTEXT.md` — locked decisions `[VERIFIED: local planning artifact]`
- `.planning/phases/07a-task-scam-recall-recovery/07a-CONTEXT.md`, `07a-01-SUMMARY.md`, `07a-03-PLAN.md` — recovery narrative source data `[VERIFIED: local planning artifact]`
- `documents/reports/latex/tables/dataset_statistics.tex`, `documents/reports/latex/chapters/05_evaluation_and_discussion.tex` — the compiled 0.871/62-support numbers `[VERIFIED: local report source read]`
- Installed package check: `python -c "import sklearn; print(sklearn.__version__)"` → `1.8.0` `[VERIFIED: local environment]`

### Secondary (MEDIUM confidence)
- [scikit-learn StratifiedGroupKFold documentation](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.StratifiedGroupKFold.html) — `[CITED: scikit-learn.org]` — used to describe the standard algorithmic shape (deviation-minimizing greedy group assignment) that the hand-rolled Phase 38 stratifier should model itself on
- ["Improve the train-test split with the hashing function" — Towards Data Science](https://towardsdatascience.com/improve-the-train-test-split-with-the-hashing-function-f38f32b721fb/) and [TensorFlow Datasets: Splits and slicing](https://www.tensorflow.org/datasets/splits) — `[CITED]` — corroborate that deterministic hash-based bucketing (vs. RNG-seeded shuffling) is the standard, documented technique for reproducible splits on datasets that may grow over time, matching CONTEXT.md's locked rationale

### Tertiary (LOW confidence)
- None — all claims in this document are either direct codebase/data verification or cited from official scikit-learn/TensorFlow documentation.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every recommended piece is already an installed, verified dependency; no new packages
- Architecture: HIGH — directly inspected the real existing split/dedup/manifest code and confirmed exactly what it does and doesn't do
- Pitfalls: HIGH — every pitfall in this document was confirmed by actually running the repair/pooling/capping logic against the real 3,413-row pooled dataset, not inferred

**Research date:** 2026-08-08
**Valid until:** Valid as long as `data/synthetic/recovered-balanced.jsonl` and `data/splits/recovered-balanced/test.jsonl` remain unchanged (i.e., until this phase itself repairs/replaces them) — all row-count and span-validity figures in this document are a snapshot of the current, un-repaired corpus.
