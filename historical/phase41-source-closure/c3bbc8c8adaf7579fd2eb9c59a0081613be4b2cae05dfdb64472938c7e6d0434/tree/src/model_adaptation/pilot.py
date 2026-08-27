"""Deterministic Phase 3 pilot scoring and selection helpers."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Any, get_args

from src.model_adaptation.catalog import build_default_catalog, get_candidate_by_id
from src.model_adaptation.schemas import (
    LAPTOP_BASELINE_CANDIDATE_IDS,
    EvaluatedSplit,
    ModelCandidate,
    PilotScorecard,
    PilotSelection,
)
from src.runtime.contracts import RiskTier


PILOT_RISK_TIERS: tuple[RiskTier, ...] = get_args(RiskTier)


def _effective_score(scorecard: PilotScorecard) -> float:
    return (
        (scorecard.recall_score * 0.45)
        + (scorecard.quality_score * 0.30)
        + (scorecard.memory_fit_score * 0.15)
        + (scorecard.latency_score * 0.10)
        - scorecard.hardware_penalty
    )


def _rank_key(summary: dict[str, Any]) -> tuple[float, float, float, float, float, str]:
    return (
        -summary["effective_score"],
        -summary["recall_score"],
        -summary["memory_fit_score"],
        -summary["quality_score"],
        -summary["latency_score"],
        summary["candidate_id"],
    )


def _coerce_scorecard(
    candidate: ModelCandidate,
    row: PilotScorecard | Mapping[str, object],
    default_split: EvaluatedSplit,
) -> PilotScorecard:
    if isinstance(row, PilotScorecard):
        return row

    return PilotScorecard(
        candidate_id=candidate.candidate_id,
        hf_source=candidate.hf_source,
        evaluated_split=row.get("evaluated_split", default_split),
        quality_score=float(row["quality_score"]),
        recall_score=float(row["recall_score"]),
        latency_score=float(row["latency_score"]),
        memory_fit_score=float(row["memory_fit_score"]),
        hardware_penalty=float(row.get("hardware_penalty", 0.0)),
        profile_notes=str(row.get("profile_notes", "Pilot score recorded for local profile selection.")),
        local_output_path=row.get("local_output_path"),
    )


def select_baseline_and_runner_up(
    scorecards: Sequence[PilotScorecard],
    candidates: Sequence[ModelCandidate] | None = None,
) -> PilotSelection:
    """Select the 4B laptop baseline winner and the overall runner-up deterministically."""

    candidate_catalog = {candidate.candidate_id: candidate for candidate in (candidates or build_default_catalog())}
    grouped: dict[str, list[PilotScorecard]] = defaultdict(list)
    for scorecard in scorecards:
        grouped[scorecard.candidate_id].append(scorecard)

    missing_candidates = [candidate_id for candidate_id in candidate_catalog if candidate_id not in grouped]
    if missing_candidates:
        raise ValueError(f"Pilot scorecards missing candidates: {', '.join(sorted(missing_candidates))}")

    summaries: list[dict[str, Any]] = []
    for candidate_id, rows in grouped.items():
        candidate = candidate_catalog[candidate_id]
        total_rows = len(rows)
        effective_scores = [_effective_score(row) for row in rows]
        summaries.append(
            {
                "candidate_id": candidate_id,
                "size_label": candidate.size_label,
                "effective_score": sum(effective_scores) / total_rows,
                "recall_score": sum(row.recall_score for row in rows) / total_rows,
                "quality_score": sum(row.quality_score for row in rows) / total_rows,
                "latency_score": sum(row.latency_score for row in rows) / total_rows,
                "memory_fit_score": sum(row.memory_fit_score for row in rows) / total_rows,
            }
        )

    baseline_candidates = [
        summary
        for summary in summaries
        if summary["candidate_id"] in LAPTOP_BASELINE_CANDIDATE_IDS and summary["size_label"] == "4B"
    ]
    if not baseline_candidates:
        raise ValueError("No 4B candidate is eligible for the laptop baseline winner")

    baseline_winner = sorted(baseline_candidates, key=_rank_key)[0]
    remaining_candidates = [
        summary for summary in summaries if summary["candidate_id"] != baseline_winner["candidate_id"]
    ]
    if not remaining_candidates:
        raise ValueError("Pilot selection requires at least one runner-up candidate")

    runner_up = sorted(remaining_candidates, key=_rank_key)[0]
    selection_notes = (
        "Recall-first weighted pilot selection preserved the runtime risk tiers "
        f"{', '.join(PILOT_RISK_TIERS)} while constraining the laptop baseline to the locked 4B candidates."
    )
    return PilotSelection(
        baseline_winner_id=baseline_winner["candidate_id"],
        runner_up_id=runner_up["candidate_id"],
        selection_notes=selection_notes,
    )


def run_pilot(
    candidates: Sequence[ModelCandidate] | None,
    evaluation_rows: Sequence[PilotScorecard | Mapping[str, object]],
    evaluated_split: EvaluatedSplit = "val",
) -> tuple[list[PilotScorecard], PilotSelection]:
    """Build scorecards from lightweight pilot metrics and return the selection result."""

    catalog = list(candidates or build_default_catalog())
    rows_by_candidate = defaultdict(list)
    for row in evaluation_rows:
        candidate_id = row.candidate_id if isinstance(row, PilotScorecard) else row.get("candidate_id")
        if candidate_id is None:
            raise ValueError("Each evaluation row must include candidate_id")
        candidate = get_candidate_by_id(str(candidate_id), catalog)
        rows_by_candidate[candidate.candidate_id].append(_coerce_scorecard(candidate, row, evaluated_split))

    scorecards: list[PilotScorecard] = []
    for candidate in catalog:
        if candidate.candidate_id not in rows_by_candidate:
            raise ValueError(f"Pilot evaluation rows missing candidate_id={candidate.candidate_id}")
        scorecards.extend(rows_by_candidate[candidate.candidate_id])

    selection = select_baseline_and_runner_up(scorecards, catalog)
    return scorecards, selection