"""Tests for the Phase 39 stratified manual-check review sheet generator.

Proves manual_review_sheet.py against a realistic merged-dataset fixture
shaped exactly like judge_merge.py's merge_judge_results() output.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from src.data_pipeline.manual_review_sheet import select_stratified_sample, write_review_sheet

_DIMENSIONS = (
    "realism",
    "label_correctness",
    "code_switch_naturalness",
    "risk_tier_correctness",
    "suspicious_span_accuracy",
)


def _merged_row(
    split: str,
    row_index: int,
    judge_pass: bool,
    *,
    seed_id: str | None = None,
    text: str | None = None,
    label: str = "bank_impersonation",
    risk_tier: str = "high-risk",
    score: int = 4,
) -> dict[str, Any]:
    row = {
        "text": text or f"Tin nhan {split} so {row_index} du dai hop le de test sheet.",
        "label": label,
        "risk_tier": risk_tier,
        "suspicious_spans": [],
        "xai_explanation": "Giai thich du dai cho ban ghi kiem thu sheet gop judge that.",
        "source": "synthetic_claude",
        "seed_id": seed_id or f"seed_{split}_{row_index}",
        "split": split,
        "row_index": row_index,
        "judge_pass": judge_pass,
        "judge_reason": "Fixture reason for review sheet test.",
        "recomputed_pass": judge_pass,
    }
    for dim in _DIMENSIONS:
        row[dim] = score
    return row


def _make_merged_fixture(pass_count: int, fail_count: int) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    for i in range(pass_count):
        merged.append(_merged_row("train", i, True, seed_id=f"seed_pass_{i}"))
    for i in range(fail_count):
        merged.append(
            _merged_row("val", i, False, seed_id=f"seed_fail_{i}", score=2)
        )
    return merged


# --- select_stratified_sample ----------------------------------------------


def test_select_stratified_sample_splits_evenly_when_both_pools_large_enough():
    merged = _make_merged_fixture(pass_count=12, fail_count=8)

    sample, composition = select_stratified_sample(merged, sample_size=10)

    assert len(sample) == 10
    pass_rows = [row for row in sample if row["judge_pass"]]
    fail_rows = [row for row in sample if not row["judge_pass"]]
    assert len(pass_rows) == 5
    assert len(fail_rows) == 5
    assert composition == {
        "sample_size": 10,
        "pass_count": 5,
        "fail_count": 5,
        "source_total": 20,
        "source_pass_total": 12,
        "source_fail_total": 8,
    }


def test_select_stratified_sample_never_pads_fail_pool_past_real_size():
    merged = _make_merged_fixture(pass_count=17, fail_count=3)

    sample, composition = select_stratified_sample(merged, sample_size=10)

    fail_rows = [row for row in sample if not row["judge_pass"]]
    pass_rows = [row for row in sample if row["judge_pass"]]
    assert len(fail_rows) == 3
    assert len(pass_rows) == 7
    assert len(sample) == 10
    assert composition["fail_count"] == 3
    assert composition["pass_count"] == 7


def test_select_stratified_sample_is_deterministic_across_calls():
    merged = _make_merged_fixture(pass_count=12, fail_count=8)

    sample_1, _ = select_stratified_sample(merged, sample_size=10, salt="fixed-salt")
    sample_2, _ = select_stratified_sample(merged, sample_size=10, salt="fixed-salt")

    ids_1 = [(row["split"], row["row_index"]) for row in sample_1]
    ids_2 = [(row["split"], row["row_index"]) for row in sample_2]
    assert ids_1 == ids_2


def test_select_stratified_sample_returns_everything_when_below_sample_size():
    merged = _make_merged_fixture(pass_count=4, fail_count=2)

    sample, composition = select_stratified_sample(merged, sample_size=10)

    assert len(sample) == 6
    assert composition["sample_size"] == 6
    assert composition["pass_count"] == 4
    assert composition["fail_count"] == 2


# --- write_review_sheet -----------------------------------------------------


def test_write_review_sheet_renders_one_section_per_row(tmp_path: Path):
    merged = _make_merged_fixture(pass_count=3, fail_count=2)
    sample, composition = select_stratified_sample(merged, sample_size=10)
    output_path = tmp_path / "review-sheet.md"

    write_review_sheet(sample, composition, output_path)

    content = output_path.read_text(encoding="utf-8")
    assert content.count("## Example") == 5
    assert content.count("[ ] PASS") == 5
    assert content.count("[ ] FAIL") == 5
    assert content.count("**Notes:**") == 5
    for row in sample:
        assert row["text"] in content
        assert row["label"] in content
        assert row["risk_tier"] in content
        assert row["judge_reason"] in content
        verdict_label = "PASS" if row["judge_pass"] else "FAIL"
        assert f"Codex judge verdict:** {verdict_label}" in content


# --- end-to-end --------------------------------------------------------------


def test_end_to_end_sample_then_write_matches_header_composition(tmp_path: Path):
    merged = _make_merged_fixture(pass_count=30, fail_count=15)
    sample, composition = select_stratified_sample(merged, sample_size=20)
    output_path = tmp_path / "39-manual-review-sheet.md"

    write_review_sheet(sample, composition, output_path)

    content = output_path.read_text(encoding="utf-8")

    header_match = re.search(
        r"Sample size: (\d+) \((\d+) judge-pass, (\d+) judge-fail\)", content
    )
    assert header_match is not None
    header_sample_size = int(header_match.group(1))
    header_pass_count = int(header_match.group(2))
    header_fail_count = int(header_match.group(3))

    actual_pair_count = content.count("[ ] PASS")
    assert actual_pair_count == content.count("[ ] FAIL")
    assert header_sample_size == actual_pair_count
    assert header_pass_count + header_fail_count == header_sample_size
    assert header_sample_size == composition["sample_size"]
    assert header_pass_count == composition["pass_count"]
    assert header_fail_count == composition["fail_count"]
