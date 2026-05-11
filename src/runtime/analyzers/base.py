"""Protocol seam for swappable runtime analyzer backends."""

from typing import Protocol

from src.runtime.contracts import AnalysisRequest, AnalysisResult, DoctorStatus


class AnalyzerBackend(Protocol):
    """Local analyzer contract used by the runtime service and CLI."""

    backend_name: str

    def doctor(self) -> DoctorStatus:
        """Report local readiness for the selected backend."""

    def analyze(self, request: AnalysisRequest) -> AnalysisResult:
        """Analyze one normalized message and return a typed result."""
