"""Normalize-first orchestration for the Phase 2 local runtime."""

from dataclasses import dataclass, field

from src.config.settings import Settings, get_settings
from src.data_pipeline.processing.normalizer import normalize_text
from src.runtime.analyzers.accelerated import AcceleratedAnalyzer
from src.runtime.analyzers.base import AnalyzerBackend
from src.runtime.analyzers.gguf import GGUFAnalyzer
from src.runtime.analyzers.heuristic import HeuristicAnalyzer
from src.runtime.contracts import AnalysisRequest, AnalysisResult, ChannelName


TEXT_ONLY_BOUNDARY_MESSAGE = (
    "Paste extracted text manually. OCR, screenshots, and voice messages are not supported in this demo."
)


class RuntimeBoundaryError(Exception):
    """Raised when the input violates the local runtime boundary."""

    def __init__(self, message: str, steps: list[str] | None = None):
        super().__init__(message)
        self.steps = steps or []


class RuntimeUnavailableError(Exception):
    """Raised when the local backend is unavailable or fails closed."""

    def __init__(self, message: str, steps: list[str] | None = None):
        super().__init__(message)
        self.steps = steps or []


def looks_like_non_text_payload(text: str) -> bool:
    lowered = text.strip().casefold()
    if lowered.endswith((".png", ".jpg", ".jpeg", ".gif", ".wav", ".mp3")):
        return True
    if lowered.startswith(("data:image/", "data:audio/")):
        return True
    if lowered in {"[image attached]", "[audio attached]", "[voice message]"}:
        return True
    return False


def _default_setup_steps() -> list[str]:
    return ["python -m pip install -e .[dev]", "python -m src.runtime.cli doctor"]


def _build_backend_from_settings(settings: Settings) -> AnalyzerBackend:
    allowed_profiles = {
        "heuristic": {"heuristic"},
        "gguf": {
            getattr(settings, "runtime_profile_gguf", "gguf-laptop"),
            getattr(settings, "runtime_profile_gguf_runner_up", "gguf-runner-up"),
        },
        "accelerated": {getattr(settings, "runtime_profile_accelerated", "accelerated-local")},
    }
    if settings.runtime_backend not in allowed_profiles:
        raise ValueError(f"Unknown runtime backend: {settings.runtime_backend}")
    if settings.runtime_profile not in allowed_profiles[settings.runtime_backend]:
        raise ValueError(f"Unknown runtime profile: {settings.runtime_profile}")

    if settings.runtime_backend == "heuristic":
        return HeuristicAnalyzer()
    if settings.runtime_backend == "gguf":
        return GGUFAnalyzer(
            registry_path=settings.model_registry_path,
            runtime_profile=settings.runtime_profile,
        )
    return AcceleratedAnalyzer(
        registry_path=settings.model_registry_path,
        runtime_profile=settings.runtime_profile,
    )


@dataclass
class RuntimeService:
    """Thin runtime service that normalizes input and delegates to a backend."""

    backend: AnalyzerBackend
    settings: Settings = field(default_factory=get_settings)

    def analyze_text(self, text: str, channel: ChannelName = "unknown") -> AnalysisResult:
        if self.settings.runtime_store_raw_text:
            raise RuntimeUnavailableError(
                "Raw-text persistence must stay disabled for the local runtime.",
                steps=_default_setup_steps(),
            )

        normalized_text = normalize_text(text)
        boundary_message = self.settings.runtime_text_only_message or TEXT_ONLY_BOUNDARY_MESSAGE

        if not normalized_text.strip():
            raise RuntimeBoundaryError("Message text is empty after normalization.", steps=[boundary_message])

        if looks_like_non_text_payload(normalized_text):
            raise RuntimeBoundaryError(boundary_message, steps=[boundary_message])

        if len(normalized_text) < self.settings.runtime_min_text_chars:
            raise RuntimeBoundaryError(
                "Message text is too short for reliable local analysis.",
                steps=[boundary_message],
            )

        doctor_status = self.backend.doctor()
        if self.settings.runtime_fail_closed and not doctor_status.ready:
            raise RuntimeUnavailableError(
                "Local runtime is not ready.",
                steps=doctor_status.setup_steps or _default_setup_steps(),
            )

        request = AnalysisRequest(text=normalized_text, channel=channel)

        try:
            result = self.backend.analyze(request)
        except RuntimeBoundaryError:
            raise
        except Exception as exc:
            raise RuntimeUnavailableError(
                "Local runtime is unavailable. Run the doctor command for setup guidance.",
                steps=_default_setup_steps(),
            ) from exc

        if len(result.top_cues) > self.settings.runtime_max_cues:
            result = result.model_copy(update={"top_cues": result.top_cues[: self.settings.runtime_max_cues]})

        return result


def build_default_runtime_service() -> RuntimeService:
    settings = get_settings()
    return RuntimeService(backend=_build_backend_from_settings(settings), settings=settings)