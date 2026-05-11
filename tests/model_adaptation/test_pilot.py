"""Wave 0 pilot tests for deterministic Phase 3 model selection."""

from src.model_adaptation.catalog import build_default_catalog
from src.model_adaptation.pilot import run_pilot, select_baseline_and_runner_up
from src.model_adaptation.schemas import PilotScorecard


def _scorecard(
    candidate_id: str,
    hf_source: str,
    *,
    quality: float,
    recall: float,
    latency: float,
    memory_fit: float,
    penalty: float = 0.0,
    notes: str = "Pilot metrics captured for selection.",
) -> PilotScorecard:
    return PilotScorecard(
        candidate_id=candidate_id,
        hf_source=hf_source,
        evaluated_split="val",
        quality_score=quality,
        recall_score=recall,
        latency_score=latency,
        memory_fit_score=memory_fit,
        hardware_penalty=penalty,
        profile_notes=notes,
    )


def test_select_baseline_and_runner_up_is_deterministic():
    scorecards = [
        _scorecard(
            "qwen3-4b-instruct-2507",
            "Qwen/Qwen3-4B-Instruct-2507",
            quality=0.90,
            recall=0.92,
            latency=0.85,
            memory_fit=0.95,
        ),
        _scorecard(
            "qwen3.5-4b",
            "Qwen/Qwen3.5-4B",
            quality=0.90,
            recall=0.92,
            latency=0.85,
            memory_fit=0.95,
        ),
        _scorecard(
            "qwen2.5-7b-instruct",
            "Qwen/Qwen2.5-7B-Instruct",
            quality=0.94,
            recall=0.93,
            latency=0.62,
            memory_fit=0.58,
            penalty=0.08,
        ),
    ]

    first_selection = select_baseline_and_runner_up(scorecards, build_default_catalog())
    second_selection = select_baseline_and_runner_up(list(reversed(scorecards)), build_default_catalog())

    assert first_selection == second_selection
    assert first_selection.baseline_winner_id in {"qwen3.5-4b", "qwen3-4b-instruct-2507"}
    assert first_selection.runner_up_id != first_selection.baseline_winner_id


def test_pilot_selection_returns_4b_baseline_winner_and_runner_up_from_locked_catalog():
    evaluation_rows = [
        {
            "candidate_id": "qwen3.5-4b",
            "quality_score": 0.91,
            "recall_score": 0.94,
            "latency_score": 0.83,
            "memory_fit_score": 0.95,
            "profile_notes": "Balanced 4B candidate for the laptop baseline.",
        },
        {
            "candidate_id": "qwen3-4b-instruct-2507",
            "quality_score": 0.89,
            "recall_score": 0.90,
            "latency_score": 0.90,
            "memory_fit_score": 0.94,
            "profile_notes": "Faster 4B fallback with slightly lower recall.",
        },
        {
            "candidate_id": "qwen2.5-7b-instruct",
            "quality_score": 0.96,
            "recall_score": 0.95,
            "latency_score": 0.64,
            "memory_fit_score": 0.57,
            "hardware_penalty": 0.10,
            "profile_notes": "Stronger capacity, but weaker laptop feasibility.",
        },
    ]

    scorecards, selection = run_pilot(build_default_catalog(), evaluation_rows, evaluated_split="val")

    assert [scorecard.candidate_id for scorecard in scorecards] == [
        "qwen3.5-4b",
        "qwen3-4b-instruct-2507",
        "qwen2.5-7b-instruct",
    ]
    assert selection.baseline_winner_id == "qwen3.5-4b"
    assert selection.runner_up_id == "qwen3-4b-instruct-2507"
    assert "benign, suspicious, high-risk" in (selection.selection_notes or "")


def test_run_pilot_requires_exact_candidate_coverage():
    incomplete_rows = [
        {
            "candidate_id": "qwen3.5-4b",
            "quality_score": 0.90,
            "recall_score": 0.91,
            "latency_score": 0.84,
            "memory_fit_score": 0.95,
            "profile_notes": "Only one candidate provided.",
        }
    ]

    try:
        run_pilot(build_default_catalog(), incomplete_rows)
    except ValueError as exc:
        assert "missing candidate_id" in str(exc)
    else:
        raise AssertionError("run_pilot should reject incomplete candidate coverage")