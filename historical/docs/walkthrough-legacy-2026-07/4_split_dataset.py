# ============================================================
# STEP 4 of 10 — Deterministic, Seed-Aware Train/Val/Test Split
# ============================================================
# Canonical source (this numbered copy exists ONLY for defense-day
# navigation — it is not a second implementation and is not imported
# by anything): src/data_pipeline/processing/splitter.py
#
# What this file does: assigns every judged-and-passed record (from
# step 3) to train/val/test using a deterministic hash of its seed_id,
# so all synthetic variants of one real seed stay in the same split —
# this is the anti-leakage mechanism referenced constantly in the Q&A
# prep doc. Calls into dedup.py for lexical + embedding-based cleanup.
#
# See also: documents/reports/supervisor/defense_code_navigation.md
# ============================================================

"""Deterministic split assignment with seed-level grouping and dedup integration."""

from __future__ import annotations

import hashlib
from typing import Any, Literal

from src.config.settings import get_settings
from src.data_pipeline.schemas import DatasetRecord


SplitName = Literal["train", "val", "test"]


def _stable_bucket(value: str, salt: str) -> float:
    """
    Core determinism primitive for the whole file: SHA256(salt:value),
    take the first 8 hex chars (32 bits) as an integer, normalize to a
    float in roughly [0, 1). This is a hash-based substitute for
    `random.random()` that's 100% REPRODUCIBLE — same value+salt always
    produces the exact same "random-looking" float, on any machine, any
    run, forever. That reproducibility is the entire point: it's what lets
    split_ratios stay honored while still being computable independently
    for any single seed_id without needing to look at the whole dataset
    (no global shuffling state, no RNG seed to keep in sync).
    """
    digest = hashlib.sha256(f"{salt}:{value}".encode("utf-8")).hexdigest()
    return int(digest[:8], 16) / 0xFFFFFFFF


def _seed_bucket(seed_id: str, salt: str) -> float:
    return _stable_bucket(seed_id, salt)


def _record_bucket(record: dict[str, Any], salt: str) -> float:
    # Used only for the "underdiverse label" fallback path further down —
    # when there aren't enough distinct seeds to group by, individual
    # records get their own deterministic bucket instead, keyed by
    # label+seed_id+text so two different records never collide onto
    # exactly the same bucket value.
    record_key = "|".join(
        [
            str(record.get("label", "")),
            str(record.get("seed_id", "")),
            str(record.get("text", "")),
        ]
    )
    return _stable_bucket(record_key, salt)


def _allocate_split_counts(
    total_seeds: int,
    split_ratios: tuple[float, float, float],
) -> dict[SplitName, int]:
    """
    Turns e.g. (total_seeds=1000, ratios=(0.8, 0.1, 0.1)) into exact integer
    counts {"train": 800, "val": 100, "test": 100} — handling the rounding
    and edge cases that naive `int(total * ratio)` gets wrong:
      1. Truncate each ratio's raw share down to an int first (floor).
      2. Whatever's left over from truncation (`remaining`) gets handed out
         one-by-one to the splits with the LARGEST fractional remainder
         first (largest-remainder rounding — the standard way to round a
         set of proportions so they still sum EXACTLY to the total, instead
         of every split independently rounding and the sum drifting off).
      3. Safety pass: if any split with a >0 ratio ended up with a ZERO
         count (possible with very small total_seeds, e.g. 2 seeds split
         80/10/10), steal one item from the split that can best afford to
         give one up. This guarantees every active split gets at least 1
         seed group when there are enough seeds to make that possible at
         all — an empty val or test split would be a silent, confusing
         failure mode you'd rather never happen.
    """
    split_names: tuple[SplitName, SplitName, SplitName] = ("train", "val", "test")
    raw_counts = {
        split_name: total_seeds * ratio
        for split_name, ratio in zip(split_names, split_ratios, strict=True)
    }
    counts = {
        split_name: int(raw_counts[split_name])
        for split_name in split_names
    }

    remaining = total_seeds - sum(counts.values())
    remainder_order = sorted(
        split_names,
        key=lambda split_name: (raw_counts[split_name] - counts[split_name], -split_names.index(split_name)),
        reverse=True,
    )
    for split_name in remainder_order:
        if remaining <= 0:
            break
        counts[split_name] += 1
        remaining -= 1

    active_splits = [split_name for split_name, ratio in zip(split_names, split_ratios, strict=True) if ratio > 0]
    if total_seeds >= len(active_splits):
        for split_name in active_splits:
            if counts[split_name] > 0:
                continue
            donor = max(
                (name for name in active_splits if counts[name] > 1),
                key=lambda name: (counts[name], raw_counts[name] - counts[name], -split_names.index(name)),
                default=None,
            )
            if donor is None:
                break
            counts[donor] -= 1
            counts[split_name] += 1

    return counts


def _assign_seed_group_splits(
    seed_ids: list[str],
    split_ratios: tuple[float, float, float],
    salt: str,
) -> dict[str, SplitName]:
    """
    Assigns a WHOLE seed_id (and therefore every synthetic record derived
    from it) to exactly one split. Sorts every seed_id by its deterministic
    hash bucket (tie-broken by the seed_id string itself, for total
    ordering stability), then slices that sorted list into train/val/test
    chunks per _allocate_split_counts. Sorting by hash bucket rather than
    e.g. insertion order means the split assignment doesn't depend on
    scrape/generation order — reshuffling the input list produces the exact
    same split assignment, because it's the HASH that determines position,
    not the list index.
    """
    ordered_seed_ids = sorted(seed_ids, key=lambda seed_id: (_seed_bucket(seed_id, salt), seed_id))
    counts = _allocate_split_counts(len(ordered_seed_ids), split_ratios)
    assignments: dict[str, SplitName] = {}
    cursor = 0
    for split_name in ("train", "val", "test"):
        next_cursor = cursor + counts[split_name]
        for seed_id in ordered_seed_ids[cursor:next_cursor]:
            assignments[seed_id] = split_name
        cursor = next_cursor
    return assignments


def assign_seed_split(
    seed_id: str,
    split_ratios: tuple[float, float, float] = (0.8, 0.1, 0.1),
    salt: str = "v1.0",
) -> SplitName:
    """
    Return a deterministic split name derived from the seed identifier.
    A simpler, STANDALONE alternative to _assign_seed_group_splits — this
    one doesn't need the full list of seed_ids up front, it just buckets
    ONE seed_id's hash value directly into train/val/test ranges (e.g.
    bucket < 0.8 → train, < 0.9 → val, else → test for the default 80/10/10
    ratios). Handy for a quick "which split would this seed land in"
    lookup without re-running the whole allocation algorithm, though the
    main split_dataset() pipeline below uses the seed-GROUP version above
    for its precise integer-count guarantees.
    """
    bucket = _seed_bucket(seed_id, salt)
    if bucket < split_ratios[0]:
        return "train"
    if bucket < split_ratios[0] + split_ratios[1]:
        return "val"
    return "test"


def split_dataset(
    records: list[dict[str, Any]],
    split_ratios: tuple[float, float, float] | None = None,
    salt: str = "v1.0",
) -> dict[SplitName, list[dict[str, Any]]]:
    """
    Split records while preserving seed groups when feasible and label support when not.

    THIS IS THE MOST IMPORTANT FUNCTION IN THIS FILE — it's the actual
    anti-leakage mechanism referenced throughout the Q&A prep doc. Core
    rule: every synthetic record sharing the same seed_id (i.e. every
    variant generated FROM the same real scraped seed message, step 1)
    must land in the SAME split. If train saw 5 paraphrases of one real
    scam message and test saw a 6th near-identical paraphrase of that same
    message, test accuracy would be inflated by memorization, not real
    generalization — that's the leak this whole function exists to prevent.

    Two-tier strategy, and WHY the second tier exists at all:
      TIER 1 (the normal case): group all records by (label, seed_id), then
      hand the seed_id groups to _assign_seed_group_splits so a whole group
      moves together as one unit.
      TIER 2 (the "underdiverse label" fallback): if some label has FEWER
      distinct seed groups than there are active splits (e.g. only 2 unique
      seeds exist for a rare label but we need train+val+test = 3 buckets),
      seed-level grouping literally cannot populate all 3 splits for that
      label — some split would get zero examples of it. So for JUST that
      label's records, fall back to splitting at the individual-RECORD
      level instead of the seed-group level (still deterministic, via
      _record_bucket) so every split still gets representation, accepting
      a small amount of extra leakage risk for that one under-represented
      label rather than leaving a split blind to it entirely. This is a
      deliberate, documented trade-off — perfect anti-leakage for common
      labels, graceful degradation only where there's genuinely not enough
      seed diversity to do better.
    """
    settings = get_settings()
    ratios = split_ratios or settings.split_ratios
    splits: dict[SplitName, list[dict[str, Any]]] = {"train": [], "val": [], "test": []}
    active_split_count = sum(1 for ratio in ratios if ratio > 0)
    label_seed_groups: dict[str, dict[str, list[dict[str, Any]]]] = {}
    retained_seed_groups: dict[str, list[dict[str, Any]]] = {}
    underdiverse_label_records: dict[str, list[dict[str, Any]]] = {}

    # Re-validate every record through the Pydantic schema HERE too (on top
    # of whatever validation already happened in earlier steps) — this
    # function might be called standalone/out of pipeline order in tests or
    # ad-hoc scripts, so it doesn't trust its caller to have already done
    # this.
    for record in records:
        validated = DatasetRecord.model_validate(record).model_dump()
        label_seed_groups.setdefault(validated["label"], {}).setdefault(validated["seed_id"], []).append(validated)

    # A label is "underdiverse" if it has fewer distinct seed_id groups
    # than there are splits to fill (active_split_count, normally 3) — that
    # means seed-level grouping literally cannot give every split a
    # representative of this label.
    underdiverse_labels = {
        label
        for label, seed_groups in label_seed_groups.items()
        if len(seed_groups) < active_split_count
    }

    # Route every record to either the seed-group path (retained_seed_groups,
    # the strong anti-leakage path) or the per-label fallback path
    # (underdiverse_label_records), based on whether ITS label was flagged
    # above. Note a single seed_id's records could theoretically span
    # multiple labels in unusual data — the inner check handles that by
    # splitting the group's own records between the two buckets rather than
    # assuming one seed_id implies one label.
    for label_seed_group in label_seed_groups.values():
        for seed_id, group_records in label_seed_group.items():
            if any(group_record["label"] in underdiverse_labels for group_record in group_records):
                for group_record in group_records:
                    if group_record["label"] in underdiverse_labels:
                        underdiverse_label_records.setdefault(group_record["label"], []).append(group_record)
                    else:
                        retained_seed_groups.setdefault(seed_id, []).append(group_record)
                continue
            retained_seed_groups.setdefault(seed_id, []).extend(group_records)

    # TIER 1: the strong path — whole seed groups assigned together.
    if retained_seed_groups:
        assignments = _assign_seed_group_splits(list(retained_seed_groups), ratios, salt)
        for seed_id, group_records in retained_seed_groups.items():
            splits[assignments[seed_id]].extend(group_records)

    # TIER 2: the fallback path, run independently PER underdiverse label
    # (not lumped together) so each rare label still gets its own correctly
    # proportioned train/val/test split of its own records.
    for label, label_records in underdiverse_label_records.items():
        ordered_records = sorted(
            label_records,
            key=lambda group_record: (
                _record_bucket(group_record, f"{salt}:{label}"),
                group_record["seed_id"],
                group_record["text"],
            ),
        )
        counts = _allocate_split_counts(len(ordered_records), ratios)
        cursor = 0
        for split_name in ("train", "val", "test"):
            next_cursor = cursor + counts[split_name]
            splits[split_name].extend(ordered_records[cursor:next_cursor])
            cursor = next_cursor

    return splits


def split_and_dedup(
    records: list[dict[str, Any]],
    split_ratios: tuple[float, float, float] | None = None,
    similarity_threshold: float | None = None,
    salt: str = "v1.0",
) -> dict[SplitName, list[dict[str, Any]]]:
    """
    Run lexical dedup, deterministic splitting, and semantic cross-split cleanup.

    Three-stage pipeline, IN THIS ORDER for a reason:
      1. lexical_dedup FIRST, on the full unsplit pool — cheap exact/
         near-exact string-level duplicate removal before doing any
         expensive work, so split_dataset never wastes effort assigning
         a duplicate record that's just going to get removed anyway.
      2. split_dataset — the seed-aware deterministic split covered above.
      3. cross_split_dedup LAST — this is the semantic (embedding-based)
         check: even after seed-grouping, two DIFFERENT seed_ids could
         have generated near-identical text by coincidence (two different
         real scam reports that happen to describe a very similar scam
         wording). This step catches THAT kind of leak, which seed-id
         grouping alone cannot, by comparing val/test records against the
         train set using semantic similarity and removing close matches.
         This is the ONLY place in the entire src/ tree an embedding model
         is loaded/used — worth knowing cold, since it directly answers
         "why do I have to know about RAG/embeddings" (see
         defense_code_navigation.md): there's no RAG at runtime, embeddings
         only ever run here, offline, during dataset prep.
    Import of dedup functions is local (inside the function, not at module
    top) specifically so this function stays optional to call — a caller
    that only needs split_dataset() shouldn't be forced to load the
    (heavier, sentence-transformer-dependent) dedup module just to import
    this file.
    """
    from src.data_pipeline.processing.dedup import cross_split_dedup, lexical_dedup

    settings = get_settings()
    threshold = similarity_threshold or settings.similarity_threshold

    deduped_records = lexical_dedup(records)
    splits = split_dataset(deduped_records, split_ratios=split_ratios, salt=salt)
    removals = cross_split_dedup(
        splits["train"],
        splits["val"],
        splits["test"],
        threshold=threshold,
    )

    # cross_split_dedup returns removal sets keyed by POSITIONAL index
    # (as strings) within val/test, not by record identity — so removal is
    # done here via enumerate() + membership check against that index set.
    # train is never pruned by this step: the convention is that when a
    # val/test record is too similar to something in train, the val/test
    # copy is the one removed (train is treated as the fixed reference set).
    val_remove_set = set(removals.get("val", []))
    test_remove_set = set(removals.get("test", []))
    splits["val"] = [record for index, record in enumerate(splits["val"]) if str(index) not in val_remove_set]
    splits["test"] = [record for index, record in enumerate(splits["test"]) if str(index) not in test_remove_set]
    return splits
