"""Phase 3 model-adaptation primitives."""

from src.model_adaptation.catalog import build_default_catalog, get_candidate_by_id
from src.model_adaptation.pilot import run_pilot, select_baseline_and_runner_up
from src.model_adaptation.registry import build_model_checksum, load_model_registry, save_model_registry
from src.model_adaptation.schemas import (
    LAPTOP_BASELINE_CANDIDATE_IDS,
    LOCKED_CANDIDATE_IDS,
    ModelArtifactRecord,
    ModelCandidate,
    ModelRegistry,
    PilotScorecard,
    PilotSelection,
)

__all__ = [
    "LAPTOP_BASELINE_CANDIDATE_IDS",
    "LOCKED_CANDIDATE_IDS",
    "ModelArtifactRecord",
    "ModelCandidate",
    "ModelRegistry",
    "PilotScorecard",
    "PilotSelection",
    "build_model_checksum",
    "build_default_catalog",
    "get_candidate_by_id",
    "load_model_registry",
    "run_pilot",
    "save_model_registry",
    "select_baseline_and_runner_up",
]