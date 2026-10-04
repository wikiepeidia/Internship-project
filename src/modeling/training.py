"""Dependency-injected training services for active callers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class TrainingError(RuntimeError):
    """Raised when a configured training backend cannot complete its operation."""


class TrainingBackend(Protocol):
    """Common orchestration seam implemented by training-family adapters."""

    def build_config(self, *args: object, **kwargs: object) -> object:
        """Build one backend-owned configuration without copying its validation."""

    def train(self, *args: object, **kwargs: object) -> object:
        """Execute one already-authorized backend operation."""


@dataclass(frozen=True, slots=True)
class TrainingService:
    """Translate backend failures at the active training boundary."""

    backend: TrainingBackend

    def build_config(self, *args: object, **kwargs: object) -> object:
        try:
            return self.backend.build_config(*args, **kwargs)
        except TrainingError:
            raise
        except Exception as exc:
            raise TrainingError("Training configuration could not be prepared.") from exc

    def train(self, *args: object, **kwargs: object) -> object:
        try:
            return self.backend.train(*args, **kwargs)
        except TrainingError:
            raise
        except Exception as exc:
            raise TrainingError("Training backend could not complete the request.") from exc


def qwen_training_service(backend: TrainingBackend | None = None) -> TrainingService:
    """Create the Qwen service; resolve the legacy adapter only when requested."""

    if backend is None:
        from src.modeling.legacy_adapters import LegacyQwenTrainingAdapter

        backend = LegacyQwenTrainingAdapter()
    return TrainingService(backend=backend)


def phobert_training_service(backend: TrainingBackend | None = None) -> TrainingService:
    """Create the PhoBERT service; resolve the legacy adapter only when requested."""

    if backend is None:
        from src.modeling.legacy_adapters import LegacyPhoBertTrainingAdapter

        backend = LegacyPhoBertTrainingAdapter()
    return TrainingService(backend=backend)
