"""Tests for the Phase 38 corpus repair / seed-cap / stratified-split pipeline."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import pytest

import src.data_pipeline.repair_corpus_split_governance as repair_module
from src.data_pipeline.repair_corpus_split_governance import (
    assign_stratified_group_split,
    build_repair_manifest,
    enforce_seed_cap,
    pool_records,
    repair_all_evidence_spans,
    repair_evidence_spans,
)
from src.data_pipeline.schemas import ManifestEntry

REPO_ROOT = Path(__file__).resolve().parents[2]
# The original pre-repair sources were consolidated out of the live data/ tree
# (260808-otp data-directory cleanup) into data/backup/ — these tests read the
# retained backup copies, which are byte-identical to what repair_corpus_split_governance
# actually pooled when it built the current data/splits/{train,val,test}.jsonl.
_BACKUP_ROOT = REPO_ROOT / "data" / "backup" / "pre-260808-consolidation"
REAL_MAIN_CORPUS = _BACKUP_ROOT / "synthetic" / "recovered-balanced.jsonl"
REAL_RESERVED_TEST = _BACKUP_ROOT / "splits" / "recovered-balanced" / "test.jsonl"


def _make_record(
    seed_id: str,
    text: str,
    label: str = "bank_impersonation",
    spans: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "text": text,
        "label": label,
        "risk_tier": "benign" if label == "benign" else "high-risk",
        "suspicious_spans": spans if spans is not None else [],
        "xai_explanation": "Giai thich du dai cho ban ghi kiem thu pipeline sua loi du lieu that.",
        "source": "synthetic_claude",
        "seed_id": seed_id,
    }


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def _skewed_class_fixture() -> list[dict[str, Any]]:
    """40% task_scam, 20% each of the other three labels.

    Uses many small seed groups (2 rows each) so even the smaller val/test
    splits have enough group-assignment granularity to reflect the observed
    class mix, rather than being dominated by a single coarse group's label.
    """
    records: list[dict[str, Any]] = []
    label_seed_counts = {
        "task_scam": 40,
        "bank_impersonation": 20,
        "zalo_social_engineering": 20,
        "benign": 20,
    }
    for label, seed_count in label_seed_counts.items():
        for seed_index in range(seed_count):
            seed_id = f"seed-{label}-{seed_index}"
            for row_index in range(2):
                records.append(
                    _make_record(
                        seed_id=seed_id,
                        text=f"{label} mau cau so {seed_index}-{row_index} du dai hop le",
                        label=label,
                    )
                )
    return records


# --- Task 1: pool_records ----------------------------------------------------


def test_pool_records_combines_files_without_dropping_rows(tmp_path):
    file_a = tmp_path / "a.jsonl"
    file_b = tmp_path / "b.jsonl"
    records_a = [_make_record(seed_id=f"seed-a-{i}", text=f"Noi dung A so {i}") for i in range(3)]
    records_b = [_make_record(seed_id=f"seed-b-{i}", text=f"Noi dung B so {i}") for i in range(2)]
    _write_jsonl(file_a, records_a)
    _write_jsonl(file_b, records_b)

    pooled = pool_records([file_a, file_b])

    assert len(pooled) == len(records_a) + len(records_b)
    assert pooled[0]["text"] == records_a[0]["text"]
    assert pooled[-1]["text"] == records_b[-1]["text"]
    required_fields = {"text", "label", "risk_tier", "suspicious_spans", "xai_explanation", "source", "seed_id"}
    for record in pooled:
        assert required_fields <= set(record.keys())


# --- Task 1: repair_evidence_spans -------------------------------------------


def test_repair_evidence_spans_keeps_exact_substring_unchanged():
    record = _make_record(
        seed_id="seed-exact",
        text="Canh bao: tai khoan cua ban bi khoa ngay lap tuc.",
        spans=["tai khoan cua ban bi khoa"],
    )

    repaired = repair_evidence_spans(record)

    assert repaired is not None
    assert repaired["suspicious_spans"] == ["tai khoan cua ban bi khoa"]


def test_repair_evidence_spans_real_row1_case_mismatch():
    with REAL_MAIN_CORPUS.open(encoding="utf-8") as handle:
        row1 = json.loads(handle.readline())

    original_spans = row1["suspicious_spans"]
    assert original_spans[1] == "tai khoan cua ban vua bi truy cap tu thiet bi la"

    repaired = repair_evidence_spans(row1)

    assert repaired is not None
    assert repaired["suspicious_spans"][1] == "Tai khoan cua ban vua bi truy cap tu thiet bi la"
    assert repaired["suspicious_spans"][0] == original_spans[0]
    assert repaired["suspicious_spans"][2] == original_spans[2]
    for span in repaired["suspicious_spans"]:
        assert span in repaired["text"]


def test_repair_evidence_spans_drops_unmatched_diacritic_span_but_keeps_row():
    record = _make_record(
        seed_id="seed-partial",
        text="Tai khoan bi khoa, vui long lien he 0909 123 456 de duoc ho tro.",
        spans=[
            "Tai khoan bi khoa",
            "vui lòng liên hệ",  # diacritics not present in text -> unrecoverable
        ],
    )

    repaired = repair_evidence_spans(record)

    assert repaired is not None
    assert repaired["suspicious_spans"] == ["Tai khoan bi khoa"]


def test_repair_evidence_spans_drops_row_when_all_spans_unrecoverable():
    record = _make_record(
        seed_id="seed-unrecoverable",
        text="Noi dung binh thuong khong co gi dang ngo ca.",
        spans=["hoàn toàn không khớp", "một câu khác không khớp nốt"],
    )

    assert repair_evidence_spans(record) is None


def test_repair_evidence_spans_keeps_row_that_originally_had_zero_spans():
    """A row that never had suspicious_spans (e.g. benign, per
    DatasetRecord.suspicious_spans's schema default_factory=list) must NOT
    be treated as an unrecoverable-evidence row. Regression test for a real
    bug found during 38-02 full-scale execution: the original repair loop
    conflated "originally empty" with "became empty after repair", which
    would have silently dropped all 750 benign rows (each begins with
    suspicious_spans=[] since a benign message has no suspicious evidence).
    """
    record = _make_record(
        seed_id="seed-benign",
        text="Cam on ban da lien he. Don hang cua ban da duoc xac nhan thanh cong.",
        label="benign",
        spans=[],
    )

    repaired = repair_evidence_spans(record)

    assert repaired is not None
    assert repaired["suspicious_spans"] == []


def test_repair_all_evidence_spans_drops_unrecoverable_row_and_counts_it():
    good_record = _make_record(
        seed_id="seed-good",
        text="Canh bao lua dao that su nghiem trong.",
        spans=["Canh bao lua dao"],
    )
    bad_record = _make_record(
        seed_id="seed-bad",
        text="Noi dung hoan toan binh thuong khong co gi ca.",
        spans=["câu hoàn toàn không khớp"],
    )

    survivors, stats = repair_all_evidence_spans([good_record, bad_record])

    assert len(survivors) == 1
    assert survivors[0]["seed_id"] == "seed-good"
    assert all(record["seed_id"] != "seed-bad" for record in survivors)
    assert stats["rows_dropped_unrecoverable_span"] == 1
    assert stats["rows_pooled"] == 2


# --- Task 1: enforce_seed_cap -------------------------------------------------


def test_enforce_seed_cap_before_snapshot_uses_original_total_not_shrinking_total():
    """Regression test for a real bug found during 38-02 full-scale execution:
    when multiple seed_ids are over cap_pct, the SECOND (and later) over-cap
    seed's `seed_concentration_before` must reflect its share against the
    ORIGINAL pre-any-trim total, not an intermediate total already shrunk by
    trimming the first over-cap seed. Otherwise a seed_id that was genuinely
    ~11.9% of the original pool gets misreported as ~14%+ once the dominant
    seed's rows are already removed from the denominator.
    """
    records: list[dict[str, Any]] = []
    # Dominant seed: 40% of a 100-row corpus (over cap).
    for row_index in range(40):
        records.append(
            _make_record(
                seed_id="seed-dominant",
                text=f"Tin nhan seed thong tri dong {row_index} noi dung rieng biet a",
            )
        )
    # Second seed: 12% of the ORIGINAL 100-row corpus (also over the 8% cap
    # even before any trimming happens).
    for row_index in range(12):
        records.append(
            _make_record(
                seed_id="seed-second",
                text=f"Tin nhan seed thu hai dong {row_index} noi dung rieng biet b",
            )
        )
    # Remaining 48 rows spread across many small, under-cap seed groups.
    for seed_index in range(24):
        for row_index in range(2):
            records.append(
                _make_record(
                    seed_id=f"seed-small-{seed_index}",
                    text=f"Tin nhan nho seed {seed_index} dong {row_index} c",
                )
            )

    assert len(records) == 100

    _, stats = enforce_seed_cap(records, cap_pct=0.08)

    assert stats["seed_concentration_before"]["seed-dominant"] == pytest.approx(0.40)
    # Must reflect the ORIGINAL 100-row total (12/100 = 0.12), not a total
    # already shrunk by the dominant seed's trim.
    assert stats["seed_concentration_before"]["seed-second"] == pytest.approx(0.12)


def test_enforce_seed_cap_trims_over_cap_seed_using_lexical_dedup(monkeypatch):
    records: list[dict[str, Any]] = []
    for seed_index in range(34):
        seed_id = f"seed-small-{seed_index}"
        for row_index in range(5):
            records.append(
                _make_record(
                    seed_id=seed_id,
                    text=f"Tin nhan nho seed {seed_index} dong {row_index} noi dung khac nhau",
                )
            )
    big_seed_id = "seed-big"
    for row_index in range(30):
        records.append(
            _make_record(
                seed_id=big_seed_id,
                text=f"Tin nhan lon dong {row_index} noi dung rieng biet khong trung",
            )
        )

    assert len(records) == 200
    big_seed_before_count = sum(1 for r in records if r["seed_id"] == big_seed_id)
    assert big_seed_before_count == 30  # 15% of 200

    call_log: list[list[dict[str, Any]]] = []
    original_lexical_dedup = repair_module.lexical_dedup

    def spy_lexical_dedup(records_arg, threshold=0.95):
        call_log.append(list(records_arg))
        return original_lexical_dedup(records_arg, threshold=threshold)

    monkeypatch.setattr(repair_module, "lexical_dedup", spy_lexical_dedup)

    trimmed, stats = enforce_seed_cap(records, cap_pct=0.08)

    final_total = len(trimmed)
    big_seed_after = [r for r in trimmed if r["seed_id"] == big_seed_id]
    assert len(big_seed_after) <= 0.08 * final_total + 1e-9

    assert call_log, "lexical_dedup was never invoked"
    assert any(
        call_records and all(r["seed_id"] == big_seed_id for r in call_records)
        for call_records in call_log
    )

    assert stats["seed_concentration_before"][big_seed_id] == pytest.approx(30 / 200)
    assert stats["seed_concentration_after"][big_seed_id] <= 0.08 + 1e-9
    assert stats["rows_dropped_seed_cap"] > 0


# --- Task 1: end-to-end tracer on the real 70-row subset ---------------------


def test_end_to_end_tracer_real_70_row_subset(tmp_path):
    main_subset = tmp_path / "main_subset.jsonl"
    reserved_subset = tmp_path / "reserved_subset.jsonl"

    with REAL_MAIN_CORPUS.open(encoding="utf-8") as handle:
        main_lines = [next(handle) for _ in range(60)]
    main_subset.write_text("".join(main_lines), encoding="utf-8")

    with REAL_RESERVED_TEST.open(encoding="utf-8") as handle:
        reserved_lines = [next(handle) for _ in range(10)]
    reserved_subset.write_text("".join(reserved_lines), encoding="utf-8")

    pooled = pool_records([main_subset, reserved_subset])
    assert len(pooled) == 70

    repaired, _repair_stats = repair_all_evidence_spans(pooled)
    for record in repaired:
        assert record["suspicious_spans"], "surviving row must keep at least one span"
        for span in record["suspicious_spans"]:
            assert span in record["text"], "every surviving span must be an exact substring of text"

    capped, _cap_stats = enforce_seed_cap(repaired, cap_pct=0.08)

    assignments = assign_stratified_group_split(capped, salt="tracer-test-salt")

    # No seed_id in this subset is assigned to more than one split name.
    assert len(assignments) == len({record["seed_id"] for record in capped})

    seed_to_split_names_seen: dict[str, set[str]] = defaultdict(set)
    for record in capped:
        seed_to_split_names_seen[record["seed_id"]].add(assignments[record["seed_id"]])
    assert all(len(names) == 1 for names in seed_to_split_names_seen.values())


# --- Task 2: determinism ------------------------------------------------------


def test_assign_stratified_group_split_is_deterministic():
    records = _skewed_class_fixture()

    first = assign_stratified_group_split(records, salt="determinism-salt")
    second = assign_stratified_group_split(records, salt="determinism-salt")

    assert first == second


# --- Task 2: observed-class-mix stratification (not hardcoded 25%) ----------


def test_assign_stratified_group_split_targets_observed_class_mix_not_25_25_25_25():
    records = _skewed_class_fixture()

    assignments = assign_stratified_group_split(records, salt="skew-salt")

    splits: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        splits[assignments[record["seed_id"]]].append(record)

    for split_name, split_records in splits.items():
        if not split_records:
            continue
        task_scam_share = sum(r["label"] == "task_scam" for r in split_records) / len(split_records)
        # The fixture's actual global mix is 40% task_scam; the stratifier
        # must target that observed mix, not a hardcoded flat 25%.
        assert abs(task_scam_share - 0.4) < abs(task_scam_share - 0.25)


# --- Task 2: build_repair_manifest composes around build_manifest() --------


def test_build_repair_manifest_calls_build_manifest_and_composes_dict(tmp_path, monkeypatch):
    splits_dir = tmp_path / "splits"
    splits_dir.mkdir()
    (splits_dir / "train.jsonl").write_text("", encoding="utf-8")

    call_args: dict[str, Any] = {}

    def fake_build_manifest(data_dir: Path, version_tag: str) -> ManifestEntry:
        call_args["data_dir"] = data_dir
        call_args["version_tag"] = version_tag
        return ManifestEntry(
            version=version_tag,
            build_timestamp="2026-08-08T00:00:00Z",
            git_commit=None,
            files={},
        )

    monkeypatch.setattr(repair_module, "build_manifest", fake_build_manifest)

    split_class_counts = {
        "train": {"bank_impersonation": 10, "zalo_social_engineering": 10, "task_scam": 10, "benign": 10},
        "val": {"bank_impersonation": 2, "zalo_social_engineering": 2, "task_scam": 2, "benign": 2},
        "test": {"bank_impersonation": 2, "zalo_social_engineering": 2, "task_scam": 2, "benign": 2},
    }
    repair_stats = {"rows_pooled": 100, "rows_span_repaired": 5, "rows_dropped_unrecoverable_span": 0}

    payload = build_repair_manifest(splits_dir, "v-test", split_class_counts, repair_stats)

    assert call_args == {"data_dir": splits_dir, "version_tag": "v-test"}
    assert payload["manifest"]["version"] == "v-test"
    assert payload["split_class_distribution"] == split_class_counts
    assert payload["repair_stats"] == repair_stats
    for split_name in ("train", "val", "test"):
        assert set(payload["split_class_distribution"][split_name]) == {
            "bank_impersonation",
            "zalo_social_engineering",
            "task_scam",
            "benign",
        }


# --- Reuse verification (key_links) ------------------------------------------


def test_module_imports_stable_bucket_and_lexical_dedup_directly():
    source = Path(repair_module.__file__).read_text(encoding="utf-8")
    assert "from src.data_pipeline.processing.splitter import _stable_bucket" in source
    assert "from src.data_pipeline.processing.dedup import lexical_dedup" in source
