"""Tests for the Phase 39 Codex judge-output merge/validation tool.

Proves judge_merge.py end-to-end against realistic fixture data shaped
exactly like .planning/codex-judge-instructions.md's output schema. Real
Codex output (data/processed/codex-judge-pass.jsonl) does not exist yet --
these tests use only fixtures.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

from src.data_pipeline.judge_merge import (
    CodexJudgeResult,
    compute_aggregate_stats,
    load_judge_results,
    load_source_splits,
    main,
    merge_judge_results,
    write_merge_outputs,
)

_DIMENSIONS = (
    "realism",
    "label_correctness",
    "code_switch_naturalness",
    "risk_tier_correctness",
    "suspicious_span_accuracy",
)


def _make_source_row(
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
        "xai_explanation": "Giai thich du dai cho ban ghi kiem thu cong cu gop judge ket qua that.",
        "source": "synthetic_claude",
        "seed_id": seed_id,
    }


def _make_judge_line(
    split: str,
    row_index: int,
    seed_id: str,
    *,
    realism: int = 4,
    label_correctness: int = 4,
    code_switch_naturalness: int = 4,
    risk_tier_correctness: int = 4,
    suspicious_span_accuracy: int = 4,
    judge_pass: bool = True,
    reason: str = "Reads naturally and label matches content.",
) -> dict[str, Any]:
    return {
        "split": split,
        "row_index": row_index,
        "seed_id": seed_id,
        "realism": realism,
        "label_correctness": label_correctness,
        "code_switch_naturalness": code_switch_naturalness,
        "risk_tier_correctness": risk_tier_correctness,
        "suspicious_span_accuracy": suspicious_span_accuracy,
        "pass": judge_pass,
        "reason": reason,
    }


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


# --- load_judge_results -------------------------------------------------


def test_load_judge_results_parses_well_formed_fixture(tmp_path):
    path = tmp_path / "judge.jsonl"
    _write_jsonl(
        path,
        [
            _make_judge_line("train", 0, "seed_abc123", judge_pass=True),
            _make_judge_line("train", 1, "seed_def456", judge_pass=False, realism=2),
        ],
    )

    results = load_judge_results(path)

    assert len(results) == 2
    assert all(isinstance(result, CodexJudgeResult) for result in results)
    first = results[0]
    assert isinstance(first.row_index, int)
    assert first.row_index == 0
    for dim in _DIMENSIONS:
        score = getattr(first, dim)
        assert isinstance(score, int)
        assert 1 <= score <= 5
    assert first.judge_pass is True
    assert results[1].judge_pass is False


def test_load_judge_results_raises_on_out_of_range_score(tmp_path):
    path = tmp_path / "judge.jsonl"
    _write_jsonl(
        path,
        [
            _make_judge_line("train", 0, "seed_abc123"),
            _make_judge_line("train", 1, "seed_def456", realism=6),
        ],
    )

    with pytest.raises(ValueError, match="line 2"):
        load_judge_results(path)


def test_load_judge_results_raises_on_missing_required_field(tmp_path):
    path = tmp_path / "judge.jsonl"
    good_row = _make_judge_line("train", 0, "seed_abc123")
    bad_row = _make_judge_line("train", 1, "seed_def456")
    del bad_row["seed_id"]
    _write_jsonl(path, [good_row, bad_row])

    with pytest.raises(ValueError, match="line 2"):
        load_judge_results(path)


# --- merge_judge_results --------------------------------------------------


def _fixture_source_splits() -> dict[str, list[dict[str, Any]]]:
    return {
        "train": [
            _make_source_row("seed_train_0", "Tin nhan train so 0 du dai hop le de test."),
            _make_source_row("seed_train_1", "Tin nhan train so 1 du dai hop le de test."),
            _make_source_row("seed_train_2", "Tin nhan train so 2 du dai hop le de test."),
        ],
        "val": [
            _make_source_row("seed_val_0", "Tin nhan val so 0 du dai hop le de test."),
            _make_source_row("seed_val_1", "Tin nhan val so 1 du dai hop le de test."),
        ],
        "test": [
            _make_source_row("seed_test_0", "Tin nhan test so 0 du dai hop le de test."),
            _make_source_row("seed_test_1", "Tin nhan test so 1 du dai hop le de test."),
        ],
    }


def _fixture_judge_results() -> list[CodexJudgeResult]:
    lines = [
        _make_judge_line("train", 0, "seed_train_0"),
        _make_judge_line("train", 1, "seed_train_1"),
        _make_judge_line("train", 2, "seed_train_2"),
        _make_judge_line("val", 0, "seed_val_0"),
        _make_judge_line("val", 1, "seed_val_1"),
        _make_judge_line("test", 0, "seed_test_0"),
        _make_judge_line("test", 1, "seed_test_1"),
    ]
    return [CodexJudgeResult.model_validate(line) for line in lines]


def test_merge_judge_results_joins_every_row_with_all_fields():
    source_splits = _fixture_source_splits()
    judge_results = _fixture_judge_results()

    merged, coverage = merge_judge_results(judge_results, source_splits)

    assert len(merged) == 7
    source_fields = {"text", "label", "risk_tier", "suspicious_spans", "xai_explanation", "source", "seed_id"}
    judge_fields = {
        "split",
        "row_index",
        "realism",
        "label_correctness",
        "code_switch_naturalness",
        "risk_tier_correctness",
        "suspicious_span_accuracy",
        "judge_pass",
        "judge_reason",
        "recomputed_pass",
    }
    for row in merged:
        assert source_fields | judge_fields <= set(row.keys())
    assert coverage["train"] == {"source_rows": 3, "judge_rows": 3}
    assert coverage["val"] == {"source_rows": 2, "judge_rows": 2}
    assert coverage["test"] == {"source_rows": 2, "judge_rows": 2}


def test_merge_judge_results_raises_on_seed_id_mismatch():
    source_splits = _fixture_source_splits()
    lines = [
        _make_judge_line("train", 0, "seed_WRONG"),
        _make_judge_line("train", 1, "seed_train_1"),
        _make_judge_line("train", 2, "seed_train_2"),
        _make_judge_line("val", 0, "seed_val_0"),
        _make_judge_line("val", 1, "seed_val_1"),
        _make_judge_line("test", 0, "seed_test_0"),
        _make_judge_line("test", 1, "seed_test_1"),
    ]
    judge_results = [CodexJudgeResult.model_validate(line) for line in lines]

    with pytest.raises(ValueError, match="train.*row_index 0"):
        merge_judge_results(judge_results, source_splits)


def test_merge_judge_results_raises_on_missing_row_index():
    source_splits = _fixture_source_splits()
    lines = [
        _make_judge_line("train", 0, "seed_train_0"),
        _make_judge_line("train", 1, "seed_train_1"),
        # train row_index 2 missing
        _make_judge_line("val", 0, "seed_val_0"),
        _make_judge_line("val", 1, "seed_val_1"),
        _make_judge_line("test", 0, "seed_test_0"),
        _make_judge_line("test", 1, "seed_test_1"),
    ]
    judge_results = [CodexJudgeResult.model_validate(line) for line in lines]

    with pytest.raises(ValueError, match=r"train.*missing row_index\(es\) \[2\]"):
        merge_judge_results(judge_results, source_splits)


def test_merge_judge_results_raises_on_duplicate_row_index():
    source_splits = _fixture_source_splits()
    lines = [
        _make_judge_line("train", 0, "seed_train_0"),
        _make_judge_line("train", 1, "seed_train_1"),
        _make_judge_line("train", 1, "seed_train_1"),  # duplicate row_index 1
        _make_judge_line("train", 2, "seed_train_2"),
        _make_judge_line("val", 0, "seed_val_0"),
        _make_judge_line("val", 1, "seed_val_1"),
        _make_judge_line("test", 0, "seed_test_0"),
        _make_judge_line("test", 1, "seed_test_1"),
    ]
    judge_results = [CodexJudgeResult.model_validate(line) for line in lines]

    with pytest.raises(ValueError, match=r"train.*duplicate row_index\(es\) \[1\]"):
        merge_judge_results(judge_results, source_splits)


# --- compute_aggregate_stats ----------------------------------------------


def _stats_fixture_merged() -> list[dict[str, Any]]:
    def row(split: str, row_index: int, score: int, judge_pass: bool) -> dict[str, Any]:
        scores = {dim: score for dim in _DIMENSIONS}
        return {
            "split": split,
            "row_index": row_index,
            **scores,
            "judge_pass": judge_pass,
            "judge_reason": "fixture reason",
            "recomputed_pass": all(s >= 3 for s in scores.values()),
        }

    return [
        row("train", 0, 5, True),
        row("train", 1, 4, True),
        row("val", 0, 2, False),
        row("test", 0, 3, True),
    ]


def test_compute_aggregate_stats_matches_hand_computed_values():
    merged = _stats_fixture_merged()

    stats = compute_aggregate_stats(merged)

    assert stats["total"] == 4
    assert stats["passed"] == 3
    assert stats["pass_rate"] == pytest.approx(0.75)
    for dim in _DIMENSIONS:
        assert stats[f"avg_{dim}"] == pytest.approx((5 + 4 + 2 + 3) / 4)
    assert stats["per_split"] == {
        "train": {"total": 2, "passed": 2, "pass_rate": pytest.approx(1.0)},
        "val": {"total": 1, "passed": 0, "pass_rate": pytest.approx(0.0)},
        "test": {"total": 1, "passed": 1, "pass_rate": pytest.approx(1.0)},
    }


def test_compute_aggregate_stats_reports_pass_mismatch_count():
    merged = _stats_fixture_merged()
    # Row 0 (train, all scores 5, recomputed_pass True) declares judge_pass False --
    # a self-reported disagreement with its own scores.
    merged[0]["judge_pass"] = False

    stats = compute_aggregate_stats(merged)

    assert stats["pass_mismatch_count"] == 1


# --- write_merge_outputs / end-to-end tracer ------------------------------


def test_end_to_end_tracer_round_trips_through_disk(tmp_path):
    splits_dir = tmp_path / "splits"
    source_splits = _fixture_source_splits()
    for split_name, rows in source_splits.items():
        _write_jsonl(splits_dir / f"{split_name}.jsonl", rows)

    judge_results_path = tmp_path / "codex-judge-pass.jsonl"
    _write_jsonl(
        judge_results_path,
        [
            _make_judge_line("train", 0, "seed_train_0"),
            _make_judge_line("train", 1, "seed_train_1"),
            _make_judge_line("train", 2, "seed_train_2"),
            _make_judge_line("val", 0, "seed_val_0"),
            _make_judge_line("val", 1, "seed_val_1"),
            _make_judge_line("test", 0, "seed_test_0"),
            _make_judge_line("test", 1, "seed_test_1", judge_pass=False, realism=2),
        ],
    )

    judge_results = load_judge_results(judge_results_path)
    loaded_source_splits = load_source_splits(splits_dir)
    merged, coverage = merge_judge_results(judge_results, loaded_source_splits)
    stats = compute_aggregate_stats(merged)
    stats["coverage"] = coverage

    merged_path = tmp_path / "out" / "judge-merged.jsonl"
    summary_path = tmp_path / "out" / "judge-summary.json"
    write_merge_outputs(merged, stats, merged_path, summary_path)

    assert merged_path.exists()
    assert summary_path.exists()

    read_back_merged = [
        json.loads(line) for line in merged_path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    assert read_back_merged == merged

    read_back_summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert read_back_summary == stats


# --- main() fail-closed guard ----------------------------------------------


def test_main_raises_actionable_error_when_judge_results_missing(tmp_path, monkeypatch):
    missing_path = tmp_path / "does-not-exist.jsonl"
    monkeypatch.setattr(sys, "argv", ["judge_merge", "--judge-results", str(missing_path)])

    with pytest.raises(FileNotFoundError, match=r"\.planning/codex-judge-instructions\.md"):
        main()
