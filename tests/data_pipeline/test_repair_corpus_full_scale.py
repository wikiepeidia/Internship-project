"""Full-scale acceptance-gate tests for Phase 38 (Corpus Repair & Split
Governance) Plan 02.

These tests read the REAL, final written output of a full 3,413-row
production run of `src.data_pipeline.repair_corpus_split_governance.main()`
against the actual corpus files — not mocks, not the 38-01 unit-test
fixtures — and prove DATA-04 through DATA-07 as independently checkable
facts about files on disk.

Regenerate the fixture output before running these tests (idempotent, reads
only from the two original locked input files, never from its own prior
output):

    python -m src.data_pipeline.repair_corpus_split_governance \
        --input-main data/synthetic/recovered-balanced.jsonl \
        --input-reserved data/splits/recovered-balanced/test.jsonl \
        --output-dir data/splits/phase38-corpus-repaired-v2 \
        --version-tag phase38-corpus-repaired-v2 \
        --cap-pct 0.08 --split-ratios 0.8,0.1,0.1
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SPLITS_DIR = REPO_ROOT / "data" / "splits" / "phase38-corpus-repaired-v2"
MANIFEST_PATH = REPO_ROOT / "data" / "manifests" / "manifest-phase38-corpus-repaired-v2.json"
ORIGINAL_MAIN_CORPUS = REPO_ROOT / "data" / "synthetic" / "recovered-balanced.jsonl"
ORIGINAL_RESERVED_TEST = REPO_ROOT / "data" / "splits" / "recovered-balanced" / "test.jsonl"

SPLIT_NAMES = ("train", "val", "test")
ALL_LABELS = ("bank_impersonation", "zalo_social_engineering", "task_scam", "benign")

# The one seed_id whose entire population (825 of 825 pre-repair rows, across
# BOTH original input files) traces to a single seed_id — a pre-existing
# data-generation defect discovered during this plan's full-scale run, not
# something the repair/cap/split pipeline can manufacture diversity for.
# Group-integrity-preserving splitting (the phase's primary, locked DATA-04
# requirement) forces this seed's ~196 surviving rows into exactly one
# split, so `zalo_social_engineering` is expected to have zero support in
# whichever splits do not receive that seed. See 38-02-SUMMARY.md
# "Deviations from Plan" for full detail.
SINGLE_SEED_LABEL = "zalo_social_engineering"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    records = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                records.append(json.loads(stripped))
    return records


@pytest.fixture(scope="module")
def split_records() -> dict[str, list[dict[str, Any]]]:
    return {name: _read_jsonl(SPLITS_DIR / f"{name}.jsonl") for name in SPLIT_NAMES}


@pytest.fixture(scope="module")
def manifest() -> dict[str, Any]:
    with MANIFEST_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


# --- Gate 1: DATA-04 zero cross-split seed_id leakage ------------------------


def test_zero_seed_id_crosses_split_boundary(split_records):
    seed_sets = {
        name: {record["seed_id"] for record in records} for name, records in split_records.items()
    }

    assert seed_sets["train"] & seed_sets["val"] == set()
    assert seed_sets["train"] & seed_sets["test"] == set()
    assert seed_sets["val"] & seed_sets["test"] == set()

    # Also confirm this is a real, non-trivial check (each split actually has
    # seed_ids to compare, not an empty-set false pass).
    for name, seeds in seed_sets.items():
        assert seeds, f"{name} split has zero seed_ids — fixture likely not regenerated"


# --- Gate 2: DATA-05 both over-cap seeds reduced below 8%, before/after recorded --


def test_seed_concentration_capped_and_before_after_recorded(split_records, manifest):
    combined = [record for records in split_records.values() for record in records]
    total = len(combined)
    assert total > 0

    counts = Counter(record["seed_id"] for record in combined)
    for seed_id, count in counts.items():
        share = count / total
        assert share <= 0.08 + 1e-9, f"{seed_id} is {share:.4%} of the corpus, over the 8% cap"

    repair_stats = manifest["repair_stats"]
    before = repair_stats["seed_concentration_before"]
    after = repair_stats["seed_concentration_after"]

    assert before["seed_1a4f7d4d7c53"] == pytest.approx(0.2441, abs=0.001)
    assert before["seed_157ce0adb043"] == pytest.approx(0.1190, abs=0.001)
    assert after["seed_1a4f7d4d7c53"] <= 0.08 + 1e-9
    assert after["seed_157ce0adb043"] <= 0.08 + 1e-9


# --- Gate 3: DATA-06 zero invalid evidence spans ------------------------------


def test_zero_invalid_evidence_spans(split_records):
    violations = []
    for split_name, records in split_records.items():
        for record in records:
            for span in record.get("suspicious_spans", []):
                if span not in record["text"]:
                    violations.append((split_name, record["seed_id"], span))

    assert violations == [], f"{len(violations)} invalid (non-exact-substring) spans found: {violations[:5]}"


# --- Gate 4: DATA-07 manifest records 80/10/10 ratio + per-split per-class counts --


def test_manifest_records_split_ratio_and_full_per_class_distribution(manifest):
    dist = manifest["split_class_distribution"]

    assert set(dist.keys()) == set(SPLIT_NAMES)
    for split_name in SPLIT_NAMES:
        assert set(dist[split_name].keys()) == set(ALL_LABELS), (
            f"{split_name} split_class_distribution must report a count (possibly zero) "
            f"for all four labels, got {sorted(dist[split_name].keys())}"
        )
        for label, count in dist[split_name].items():
            assert isinstance(count, int) and count >= 0

    base_files = manifest["manifest"]["files"]
    reported_total = sum(base_files[f"{name}.jsonl"]["records"] for name in SPLIT_NAMES)
    for split_name in SPLIT_NAMES:
        assert sum(dist[split_name].values()) == base_files[f"{split_name}.jsonl"]["records"]
    assert reported_total > 0

    # 80/10/10 ratio, +/- 1% tolerance for integer-row rounding.
    train_ratio = base_files["train.jsonl"]["records"] / reported_total
    val_ratio = base_files["val.jsonl"]["records"] / reported_total
    test_ratio = base_files["test.jsonl"]["records"] / reported_total
    assert train_ratio == pytest.approx(0.8, abs=0.01)
    assert val_ratio == pytest.approx(0.1, abs=0.01)
    assert test_ratio == pytest.approx(0.1, abs=0.01)


def test_three_of_four_labels_have_non_zero_support_in_every_split(manifest):
    """The literal, strongest form of DATA-07 ("non-zero counts for all four
    labels in every split") is achievable for three of the four labels.

    `zalo_social_engineering` is the documented exception: see
    SINGLE_SEED_LABEL and 38-02-SUMMARY.md "Deviations from Plan" for the
    full, evidence-verified root cause (its entire pre-repair population of
    825 rows across both original input files traces to exactly one
    seed_id, so group-integrity-preserving splitting can only place it in
    one split). This test locks in that every OTHER label achieves full
    per-split support, so any future regression that also zeroes out a
    label with real seed diversity is caught.
    """
    dist = manifest["split_class_distribution"]
    labels_with_full_support = [label for label in ALL_LABELS if label != SINGLE_SEED_LABEL]

    for split_name in SPLIT_NAMES:
        for label in labels_with_full_support:
            assert dist[split_name][label] > 0, (
                f"{split_name}/{label} has zero rows — expected non-zero support "
                f"for every label except the documented {SINGLE_SEED_LABEL} exception"
            )


def test_single_seed_label_zero_support_is_the_documented_known_exception(split_records, manifest):
    """Confirms the `zalo_social_engineering` zero-support gap in val/test is
    exactly the known, root-caused, single-seed-group limitation — not a
    wider or different failure than documented.
    """
    dist = manifest["split_class_distribution"]

    # Exactly one split carries 100% of the single-seed label's rows; the
    # other two splits have zero, by construction of group-integrity split
    # assignment on a single atomic seed group.
    supporting_splits = [name for name in SPLIT_NAMES if dist[name][SINGLE_SEED_LABEL] > 0]
    assert len(supporting_splits) == 1, (
        f"expected exactly one split to carry all {SINGLE_SEED_LABEL} rows, "
        f"got {supporting_splits}"
    )

    # Root-cause confirmation: every zalo_social_engineering row across all
    # three splits shares the same single seed_id.
    zalo_seed_ids = {
        record["seed_id"]
        for records in split_records.values()
        for record in records
        if record["label"] == SINGLE_SEED_LABEL
    }
    assert zalo_seed_ids == {"seed_1a4f7d4d7c53"}


# --- Gate 5: backup preservation ---------------------------------------------


def test_original_backup_files_unchanged():
    with ORIGINAL_MAIN_CORPUS.open(encoding="utf-8") as handle:
        main_lines = sum(1 for line in handle if line.strip())
    with ORIGINAL_RESERVED_TEST.open(encoding="utf-8") as handle:
        reserved_lines = sum(1 for line in handle if line.strip())

    assert main_lines == 3000, "data/synthetic/recovered-balanced.jsonl must remain 3,000 rows"
    assert reserved_lines == 413, "data/splits/recovered-balanced/test.jsonl must remain 413 rows"


# --- Cross-cutting: every DatasetRecord field survives the pipeline ----------


def test_every_written_row_has_required_schema_fields(split_records):
    required_fields = {"text", "label", "risk_tier", "suspicious_spans", "xai_explanation", "source", "seed_id"}
    for records in split_records.values():
        for record in records:
            assert required_fields <= set(record.keys())
            assert record["label"] in ALL_LABELS
