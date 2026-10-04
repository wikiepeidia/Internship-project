"""Tests for the Phase 39 task_scam mislabel triage sheet generator."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.data_pipeline.generate_mislabel_triage_sheet import (
    partition_by_live_presence,
    select_mislabel_candidates,
    write_triage_sheet,
)

_DIMENSIONS = (
    "realism",
    "label_correctness",
    "code_switch_naturalness",
    "risk_tier_correctness",
    "suspicious_span_accuracy",
)


def _row(
    label: str,
    label_correctness: int,
    *,
    seed_id: str = "seed_1",
    text: str = "Noi dung tin nhan mau de kiem thu triage sheet nay day du.",
    split: str = "train",
    row_index: int = 0,
) -> dict[str, Any]:
    row = {
        "text": text,
        "label": label,
        "risk_tier": "suspicious",
        "suspicious_spans": [],
        "xai_explanation": "Giai thich mau du dai cho bai kiem thu triage.",
        "seed_id": seed_id,
        "split": split,
        "row_index": row_index,
        "judge_pass": label_correctness >= 3,
        "judge_reason": "Fixture reason for triage test.",
    }
    for dim in _DIMENSIONS:
        row[dim] = 5
    row["label_correctness"] = label_correctness
    return row


# --- select_mislabel_candidates ----------------------------------------------


def test_select_mislabel_candidates_filters_by_label_and_threshold():
    merged = [
        _row("task_scam", 1),
        _row("task_scam", 5),
        _row("bank_impersonation", 1),
        _row("task_scam", 2),
    ]
    candidates = select_mislabel_candidates(merged)
    assert len(candidates) == 2
    assert all(row["label"] == "task_scam" for row in candidates)
    assert all(row["label_correctness"] < 3 for row in candidates)


def test_select_mislabel_candidates_respects_custom_threshold():
    merged = [_row("task_scam", 3), _row("task_scam", 4)]
    assert select_mislabel_candidates(merged, threshold=5) == merged


# --- partition_by_live_presence -----------------------------------------------


def test_partition_by_live_presence_splits_present_vs_dropped(tmp_path: Path):
    splits_dir = tmp_path / "splits"
    splits_dir.mkdir()
    live_row = _row("task_scam", 1, seed_id="s1", text="Con day roi nay trong corpus song.")
    with (splits_dir / "train.jsonl").open("w", encoding="utf-8") as handle:
        handle.write(json.dumps({"seed_id": "s1", "text": live_row["text"]}) + "\n")

    candidates = [
        live_row,
        _row("task_scam", 1, seed_id="s2", text="Da bi xoa boi mot lan sua khac roi."),
    ]
    present, dropped = partition_by_live_presence(candidates, splits_dir)

    assert len(present) == 1
    assert present[0]["seed_id"] == "s1"
    assert len(dropped) == 1
    assert dropped[0]["seed_id"] == "s2"


# --- write_triage_sheet --------------------------------------------------------


def test_write_triage_sheet_renders_one_section_per_present_candidate(tmp_path: Path):
    present = [
        _row("task_scam", 1, seed_id="s1"),
        _row("task_scam", 2, seed_id="s2"),
    ]
    dropped = [_row("task_scam", 1, seed_id="s3")]
    output_path = tmp_path / "triage.md"

    write_triage_sheet(present, dropped, output_path)

    content = output_path.read_text(encoding="utf-8")
    assert content.count("## Candidate") == 2
    assert "Candidates: 2 still in the live corpus" in content
    assert "1 more were flagged" in content
    assert "**Decision:**" in content
    for row in present:
        assert row["seed_id"] in content
        assert row["judge_reason"] in content


def test_write_triage_sheet_preserves_embedded_newlines(tmp_path: Path):
    present = [_row("task_scam", 1, text="Dong mot.\nDong hai.")]
    output_path = tmp_path / "triage.md"

    write_triage_sheet(present, [], output_path)

    content = output_path.read_text(encoding="utf-8")
    assert "> Dong mot." in content
    assert "> Dong hai." in content
