"""Locked Phase 3 catalog for the Qwen pilot candidates."""

from __future__ import annotations

from src.model_adaptation.schemas import LOCKED_CANDIDATE_IDS, ModelCandidate


def build_default_catalog() -> list[ModelCandidate]:
    """Return the locked candidate set captured during Phase 3 discussion."""

    return [
        ModelCandidate(
            candidate_id=LOCKED_CANDIDATE_IDS[0],
            hf_source="Qwen/Qwen3.5-4B",
            family="Qwen",
            role="primary",
            size_label="4B",
            notes="Primary 8GB-VRAM laptop baseline candidate.",
        ),
        ModelCandidate(
            candidate_id=LOCKED_CANDIDATE_IDS[1],
            hf_source="Qwen/Qwen3-4B-Instruct-2507",
            family="Qwen",
            role="fallback",
            size_label="4B",
            notes="Fallback 4B option favored for faster token output.",
        ),
        ModelCandidate(
            candidate_id=LOCKED_CANDIDATE_IDS[2],
            hf_source="Qwen/Qwen2.5-7B-Instruct",
            family="Qwen",
            role="fallback",
            size_label="7B",
            notes="Larger comparison candidate for backup or accelerated deployment.",
        ),
    ]


def get_candidate_by_id(candidate_id: str, catalog: list[ModelCandidate] | None = None) -> ModelCandidate:
    """Resolve one locked candidate by id."""

    for candidate in catalog or build_default_catalog():
        if candidate.candidate_id == candidate_id:
            return candidate
    raise KeyError(f"Unknown candidate_id: {candidate_id}")