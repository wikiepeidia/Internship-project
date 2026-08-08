"""Full-scale acceptance-gate tests for Phase 38 (Corpus Repair & Split
Governance) Plan 02.

These tests read the REAL, final written output rebuilt from the 3,413-row
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
        --replacement-input data/synthetic/zalo-social-engineering-codex-2026-08-08.jsonl \
        --replacement-label zalo_social_engineering \
        --output-dir data/splits/phase38-corpus-repaired-v3 \
        --version-tag phase38-corpus-repaired-v3 \
        --cap-pct 0.08 --split-ratios 0.8,0.1,0.1
"""

from __future__ import annotations

import json
import hashlib
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pytest

from src.data_pipeline.processing.dedup import fuzz
from src.data_pipeline.processing.normalizer import normalize_text
from src.data_pipeline.schemas import DatasetRecord

REPO_ROOT = Path(__file__).resolve().parents[2]
SPLITS_DIR = REPO_ROOT / "data" / "splits" / "phase38-corpus-repaired-v3"
MANIFEST_PATH = REPO_ROOT / "data" / "manifests" / "manifest-phase38-corpus-repaired-v3.json"
ORIGINAL_MAIN_CORPUS = REPO_ROOT / "data" / "synthetic" / "recovered-balanced.jsonl"
ORIGINAL_RESERVED_TEST = REPO_ROOT / "data" / "splits" / "recovered-balanced" / "test.jsonl"
REPLACEMENT_CORPUS = REPO_ROOT / "data" / "synthetic" / "zalo-social-engineering-codex-2026-08-08.jsonl"
V2_SPLITS_DIR = REPO_ROOT / "data" / "splits" / "phase38-corpus-repaired-v2"
V2_MANIFEST_PATH = REPO_ROOT / "data" / "manifests" / "manifest-phase38-corpus-repaired-v2.json"

SPLIT_NAMES = ("train", "val", "test")
ALL_LABELS = ("bank_impersonation", "zalo_social_engineering", "task_scam", "benign")

LOCKED_HASHES = {
    ORIGINAL_MAIN_CORPUS: "009af0d2b298c25705e26830a5a7abb9e4aad34e69b1ab84a363d97030beafad",
    ORIGINAL_RESERVED_TEST: "371ac104ab6910d5e37db994672c1b6fcd9879317cb260ced7f3332b0d24a94e",
    V2_SPLITS_DIR / "train.jsonl": "3f8b286005a5440f43d2e23f7abfd4ada28824e28751d7de030358fa6b56e1b1",
    V2_SPLITS_DIR / "val.jsonl": "afd304528be0aadaf1d19b95d68b0c49c3fa0b07976ebcd4de1dfdb1c8cb62f1",
    V2_SPLITS_DIR / "test.jsonl": "f2b570bf6480fb34e1b23c8ac32074f3b504560a9862b22b593425a8d4b78797",
    V2_MANIFEST_PATH: "f0a11f60152c28052e103e8984eae2a6bcde9e886ae7a9e345a0659f6dae8048",
}


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


# --- Gate 2: DATA-05 every seed remains below 8% -----------------------------


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

    assert before
    assert set(after) == set(before)
    assert all(share <= 0.08 + 1e-9 for share in after.values())

    assert repair_stats["source_rows_pooled"] == 3413
    assert repair_stats["old_zalo_rows_removed"] == 825
    assert repair_stats["replacement_rows_added"] == 300
    assert repair_stats["replacement_unique_seed_count"] == 60
    assert repair_stats["external_api_call_count"] == 0
    provenance = repair_stats["generation_provenance"]
    assert provenance["authoring_runtime"] == "gpt-5.6-sol-codex-session"
    assert provenance["schema_source"] == "synthetic_openai_compatible"
    assert provenance["external_api_calls"] == 0


# --- Gate 3: DATA-06 zero invalid evidence spans ------------------------------


def test_zero_invalid_evidence_spans(split_records):
    violations = []
    for split_name, records in split_records.items():
        for record in records:
            for span in record.get("suspicious_spans", []):
                if span not in record["text"]:
                    violations.append((split_name, record["seed_id"], span))

    assert violations == [], f"{len(violations)} invalid (non-exact-substring) spans found: {violations[:5]}"


def test_no_normalized_or_lexical_duplicates_cross_split_boundaries(split_records):
    normalized = {
        name: [normalize_text(record["text"]).casefold() for record in records]
        for name, records in split_records.items()
    }
    for left_name, right_name in (("train", "val"), ("train", "test"), ("val", "test")):
        assert set(normalized[left_name]).isdisjoint(normalized[right_name])
        violations = [
            (left_index, right_index)
            for left_index, left in enumerate(normalized[left_name])
            for right_index, right in enumerate(normalized[right_name])
            if fuzz.ratio(left, right) / 100.0 >= 0.95
        ]
        assert violations == [], (
            f"{left_name}/{right_name} contains lexical near-duplicate pairs: {violations[:5]}"
        )


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


    for split_name in SPLIT_NAMES:
        path = SPLITS_DIR / f"{split_name}.jsonl"
        entry = base_files[f"{split_name}.jsonl"]
        assert entry["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
        assert entry["records"] == len(_read_jsonl(path))
        assert entry["bytes"] == path.stat().st_size


def test_all_labels_have_non_zero_support_in_every_split(manifest):
    dist = manifest["split_class_distribution"]
    for split_name in SPLIT_NAMES:
        for label in ALL_LABELS:
            assert dist[split_name][label] > 0, (
                f"{split_name}/{label} has zero rows despite adequate independent seed groups"
            )


def test_zalo_support_and_lineage_floors(split_records):
    row_floors = {"train": 150, "val": 25, "test": 25}
    for split_name, floor in row_floors.items():
        zalo_rows = [
            record
            for record in split_records[split_name]
            if record["label"] == "zalo_social_engineering"
        ]
        assert len(zalo_rows) >= floor
        seed_ids = {record["seed_id"] for record in zalo_rows}
        if split_name in {"val", "test"}:
            assert len(seed_ids) >= 5


# --- Gate 5: backup preservation ---------------------------------------------


def test_original_and_v2_backup_files_are_byte_unchanged():
    with ORIGINAL_MAIN_CORPUS.open(encoding="utf-8") as handle:
        main_lines = sum(1 for line in handle if line.strip())
    with ORIGINAL_RESERVED_TEST.open(encoding="utf-8") as handle:
        reserved_lines = sum(1 for line in handle if line.strip())

    assert main_lines == 3000, "data/synthetic/recovered-balanced.jsonl must remain 3,000 rows"
    assert reserved_lines == 413, "data/splits/recovered-balanced/test.jsonl must remain 413 rows"
    for path, expected_sha256 in LOCKED_HASHES.items():
        assert path.exists()
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected_sha256

    replacement_rows = _read_jsonl(REPLACEMENT_CORPUS)
    assert len(replacement_rows) == 300
    assert len({record["seed_id"] for record in replacement_rows}) == 60


# --- Cross-cutting: every DatasetRecord field survives the pipeline ----------


def test_every_written_row_has_required_schema_fields(split_records):
    required_fields = {"text", "label", "risk_tier", "suspicious_spans", "xai_explanation", "source", "seed_id"}
    for records in split_records.values():
        for record in records:
            assert required_fields <= set(record.keys())
            assert record["label"] in ALL_LABELS
            DatasetRecord.model_validate(record)
