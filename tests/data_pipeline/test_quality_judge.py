"""Tests for the synthetic data quality judge."""

from __future__ import annotations

import json
from types import SimpleNamespace

from src.data_pipeline.generation.quality_judge import CLAUDE_MODEL, GEMINI_MODEL, QualityJudge


def _settings(gemini_key: str = "gemini", anthropic_key: str = "anthropic"):
    return SimpleNamespace(gemini_api_key=gemini_key, anthropic_api_key=anthropic_key)


def _response_text(realism: int, label_correctness: int, code_switch_naturalness: int, reason: str) -> str:
    return json.dumps(
        {
            "realism": realism,
            "label_correctness": label_correctness,
            "code_switch_naturalness": code_switch_naturalness,
            "pass": realism >= 3 and label_correctness >= 3 and code_switch_naturalness >= 3,
            "reason": reason,
        }
    )


def test_judge_record_pass(sample_dataset_record):
    response = SimpleNamespace(
        raise_for_status=lambda: None,
        json=lambda: {
            "candidates": [
                {"content": {"parts": [{"text": _response_text(4, 4, 5, "Looks realistic")}]}}
            ]
        },
    )
    judge = QualityJudge(
        settings=_settings(),
        http_client=SimpleNamespace(post=lambda *args, **kwargs: response),
    )
    record = sample_dataset_record.model_dump() | {"source": "synthetic_claude"}

    verdict = judge.judge_record(record)

    assert verdict.pass_verdict is True
    assert verdict.realism == 4


def test_judge_record_fail(sample_dataset_record):
    response = SimpleNamespace(
        raise_for_status=lambda: None,
        json=lambda: {
            "candidates": [
                {"content": {"parts": [{"text": _response_text(2, 4, 4, "Too templated")}]}}
            ]
        },
    )
    judge = QualityJudge(
        settings=_settings(),
        http_client=SimpleNamespace(post=lambda *args, **kwargs: response),
    )
    record = sample_dataset_record.model_dump() | {"source": "synthetic_claude"}

    verdict = judge.judge_record(record)

    assert verdict.pass_verdict is False
    assert verdict.reason == "Too templated"


def test_filter_passed(sample_dataset_record, sample_benign_record):
    judge = QualityJudge(settings=_settings())
    judge.judge_batch = lambda records: [
        (records[0], judge.judge_record(records[0])),
        (records[1], judge.judge_record(records[1])),
    ]
    judge.judge_record = lambda record: SimpleNamespace(
        realism=4,
        label_correctness=4,
        code_switch_naturalness=4,
        pass_verdict=record["label"] != "benign",
        reason="ok",
    )

    passed, stats = judge.filter_passed([sample_dataset_record.model_dump(), sample_benign_record.model_dump()])

    assert len(passed) == 1
    assert stats.passed == 1
    assert stats.failed == 1


def test_quality_stats(sample_dataset_record, sample_benign_record):
    judge = QualityJudge(settings=_settings())
    judge.judge_batch = lambda records: [
        (
            records[0],
            SimpleNamespace(
                realism=5,
                label_correctness=4,
                code_switch_naturalness=5,
                pass_verdict=True,
                reason="good",
            ),
        ),
        (
            records[1],
            SimpleNamespace(
                realism=2,
                label_correctness=3,
                code_switch_naturalness=2,
                pass_verdict=False,
                reason="weak",
            ),
        ),
    ]

    _, stats = judge.filter_passed([sample_dataset_record.model_dump(), sample_benign_record.model_dump()])

    assert stats.pass_rate == 0.5
    assert stats.avg_realism == 3.5
    assert stats.avg_label_correctness == 3.5
    assert stats.avg_code_switch_naturalness == 3.5


def test_uses_different_model_than_generator():
    judge = QualityJudge(settings=_settings())

    assert judge._select_judge_model("synthetic_claude") == GEMINI_MODEL

    claude_judge = QualityJudge(settings=_settings(gemini_key="", anthropic_key="anthropic"), anthropic_client=object())
    assert claude_judge._select_judge_model("synthetic_gemini") == CLAUDE_MODEL