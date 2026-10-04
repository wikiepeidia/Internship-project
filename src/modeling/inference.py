"""Runtime-safe inference protocol and service."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from src.runtime.contracts import AnalysisRequest, AnalysisResult


class InferenceError(RuntimeError):
    """Raised when an inference backend fails at the active domain boundary."""


class InferenceBackend(Protocol):
    """Small structural contract shared by installed analyzer backends."""

    backend_name: str

    def analyze(self, request: AnalysisRequest) -> AnalysisResult:
        """Analyze one normalized request without owning runtime policy."""


@dataclass(frozen=True, slots=True)
class InferenceService:
    """Delegate once and translate implementation failures without leaking details."""

    backend: InferenceBackend

    def infer(self, request: AnalysisRequest) -> AnalysisResult:
        try:
            return self.backend.analyze(request)
        except InferenceError:
            raise
        except Exception as exc:
            raise InferenceError("Inference backend could not complete the request.") from exc
