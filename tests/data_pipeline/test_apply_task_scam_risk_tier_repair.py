"""Tests for the Phase 39 task_scam risk_tier repair applier.

Built against fixture data shaped exactly like the real targets/instructions
schema -- no real Codex repair output exists yet (see
.planning/codex-task-scam-risk-tier-repair-instructions.md's handoff note).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from src.data_pipeline.apply_task_scam_risk_tier_repair import (
    RiskTierRepairResult,
    apply_repair,
    load_repair_results,
    load_targets,
    validate_coverage,
)


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _source_row(seed_id: str, text: str, risk_tier: str = "suspicious") -> dict[str, Any]:
    return {
        "text": text,
        "label": "task_scam",
        "risk_tier": risk_tier,
        "suspicious_spans": ["0987654321"],
        "xai_explanation": "Giai thich mau du dai cho bai kiem thu ap dung sua loi.",
        "source": "synthetic_claude",
        "seed_id": seed_id,
    }


def _repair_line(
    split: str,
    row_index: int,
    seed_id: str,
    new_risk_tier: str,
    new_spans: list[str],
    changed: bool = True,
) -> dict[str, Any]:
    return {
        "split": split,
        "row_index": row_index,
        "seed_id": seed_id,
        "new_risk_tier": new_risk_tier,
        "new_suspicious_spans": new_spans,
        "changed": changed,
        "notes": "fixture reason",
    }


# --- load_repair_results -------------------------------------------------------


def test_load_repair_results_reads_valid_lines(tmp_path: Path):
    path = tmp_path / "repair.jsonl"
    _write_jsonl(
        path,
        [_repair_line("train", 0, "seed_1", "high-risk", ["đặt cọc 200k"])],
    )
    results = load_repair_results(path)
    assert len(results) == 1
    assert isinstance(results[0], RiskTierRepairResult)
    assert results[0].new_risk_tier == "high-risk"


def test_load_repair_results_raises_actionable_error_when_missing(tmp_path: Path):
    with pytest.raises(FileNotFoundError, match="does not exist yet"):
        load_repair_results(tmp_path / "missing.jsonl")


def test_load_repair_results_rejects_unknown_fields(tmp_path: Path):
    path = tmp_path / "repair.jsonl"
    line = _repair_line("train", 0, "seed_1", "high-risk", [])
    line["extra_field"] = "should not be here"
    _write_jsonl(path, [line])
    with pytest.raises(ValueError, match="failed schema validation"):
        load_repair_results(path)


def test_load_repair_results_rejects_invalid_risk_tier(tmp_path: Path):
    path = tmp_path / "repair.jsonl"
    line = _repair_line("train", 0, "seed_1", "extremely-risky", [])
    _write_jsonl(path, [line])
    with pytest.raises(ValueError, match="failed schema validation"):
        load_repair_results(path)


# --- validate_coverage ----------------------------------------------------------


def test_validate_coverage_passes_on_exact_match():
    targets = [{"split": "train", "row_index": 0, "seed_id": "seed_1"}]
    results = [RiskTierRepairResult.model_validate(_repair_line("train", 0, "seed_1", "high-risk", []))]
    validate_coverage(targets, results)  # should not raise


def test_validate_coverage_raises_on_missing_target():
    targets = [
        {"split": "train", "row_index": 0, "seed_id": "seed_1"},
        {"split": "train", "row_index": 1, "seed_id": "seed_2"},
    ]
    results = [RiskTierRepairResult.model_validate(_repair_line("train", 0, "seed_1", "high-risk", []))]
    with pytest.raises(ValueError, match="missing target"):
        validate_coverage(targets, results)


def test_validate_coverage_raises_on_duplicate_result():
    targets = [{"split": "train", "row_index": 0, "seed_id": "seed_1"}]
    results = [
        RiskTierRepairResult.model_validate(_repair_line("train", 0, "seed_1", "high-risk", [])),
        RiskTierRepairResult.model_validate(_repair_line("train", 0, "seed_1", "suspicious", [])),
    ]
    with pytest.raises(ValueError, match="duplicate result"):
        validate_coverage(targets, results)


def test_validate_coverage_raises_on_unexpected_result():
    targets = [{"split": "train", "row_index": 0, "seed_id": "seed_1"}]
    results = [
        RiskTierRepairResult.model_validate(_repair_line("train", 0, "seed_1", "high-risk", [])),
        RiskTierRepairResult.model_validate(_repair_line("train", 5, "seed_9", "high-risk", [])),
    ]
    with pytest.raises(ValueError, match="unexpected result"):
        validate_coverage(targets, results)


# --- apply_repair ----------------------------------------------------------------


def test_apply_repair_updates_risk_tier_and_spans(tmp_path: Path):
    splits_dir = tmp_path / "splits"
    row = _source_row("seed_1", "Dat coc 200k qua vi dien tu de nhan thuong. Lien he 0987654321.")
    _write_jsonl(splits_dir / "train.jsonl", [row])
    _write_jsonl(splits_dir / "val.jsonl", [])
    _write_jsonl(splits_dir / "test.jsonl", [])

    results = [
        RiskTierRepairResult.model_validate(
            _repair_line(
                "train", 0, "seed_1", "high-risk", ["0987654321", "Dat coc 200k qua vi dien tu"]
            )
        )
    ]
    stats = apply_repair(results, splits_dir)

    assert stats["rows_changed"] == 1
    assert stats["suspicious_to_high_risk"] == 1

    with (splits_dir / "train.jsonl").open(encoding="utf-8") as handle:
        updated = json.loads(handle.readline())
    assert updated["risk_tier"] == "high-risk"
    assert updated["suspicious_spans"] == ["0987654321", "Dat coc 200k qua vi dien tu"]


def test_apply_repair_counts_kept_as_is_separately(tmp_path: Path):
    splits_dir = tmp_path / "splits"
    row = _source_row("seed_1", "Noi dung binh thuong lien he 0987654321 khong doi gi ca.")
    _write_jsonl(splits_dir / "train.jsonl", [row])
    _write_jsonl(splits_dir / "val.jsonl", [])
    _write_jsonl(splits_dir / "test.jsonl", [])

    results = [
        RiskTierRepairResult.model_validate(
            _repair_line("train", 0, "seed_1", "suspicious", ["0987654321"], changed=False)
        )
    ]
    stats = apply_repair(results, splits_dir)

    assert stats["rows_changed"] == 0
    assert stats["rows_kept_as_is"] == 1


def test_apply_repair_fails_closed_on_invalid_span_and_writes_nothing(tmp_path: Path):
    splits_dir = tmp_path / "splits"
    row = _source_row("seed_1", "Dat coc 200k qua vi dien tu de nhan thuong. Lien he 0987654321.")
    _write_jsonl(splits_dir / "train.jsonl", [row])
    _write_jsonl(splits_dir / "val.jsonl", [])
    _write_jsonl(splits_dir / "test.jsonl", [])
    original_bytes = (splits_dir / "train.jsonl").read_bytes()

    results = [
        RiskTierRepairResult.model_validate(
            _repair_line("train", 0, "seed_1", "high-risk", ["this text is not in the row"])
        )
    ]
    with pytest.raises(ValueError, match="not found in the row's real text"):
        apply_repair(results, splits_dir)

    assert (splits_dir / "train.jsonl").read_bytes() == original_bytes


def test_apply_repair_fails_closed_on_seed_id_mismatch(tmp_path: Path):
    splits_dir = tmp_path / "splits"
    row = _source_row("seed_1", "Dat coc 200k qua vi dien tu de nhan thuong. Lien he 0987654321.")
    _write_jsonl(splits_dir / "train.jsonl", [row])
    _write_jsonl(splits_dir / "val.jsonl", [])
    _write_jsonl(splits_dir / "test.jsonl", [])

    results = [
        RiskTierRepairResult.model_validate(
            _repair_line("train", 0, "seed_wrong", "high-risk", ["0987654321"])
        )
    ]
    with pytest.raises(ValueError, match="seed_id mismatch"):
        apply_repair(results, splits_dir)


# --- load_targets ----------------------------------------------------------------


def test_load_targets_raises_when_missing(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        load_targets(tmp_path / "missing.jsonl")


def test_load_targets_reads_real_shape(tmp_path: Path):
    path = tmp_path / "targets.jsonl"
    _write_jsonl(
        path,
        [
            {
                "split": "train",
                "row_index": 0,
                "seed_id": "seed_1",
                "current_risk_tier": "suspicious",
                "current_suspicious_spans": ["0987654321"],
                "original_judge_risk_tier_correctness": 2,
                "original_judge_reason": "fixture",
            }
        ],
    )
    targets = load_targets(path)
    assert len(targets) == 1
    assert targets[0]["seed_id"] == "seed_1"
