# ============================================================
# STEP 8 of 10 — The Orchestrator (Privacy Boundary + Backend Dispatch)
# ============================================================
# Canonical source (this numbered copy exists ONLY for defense-day
# navigation — it is not a second implementation and is not imported
# by anything): src/runtime/service.py
#
# What this file does: RuntimeService.analyze_text() (line ~84) is the
# real brain of request handling. It normalizes the text, refuses to
# proceed if raw-text persistence is somehow enabled (privacy boundary,
# enforced in code not just docs), rejects empty/too-short/non-text
# payloads (the "text-only, no OCR" boundary), fails closed if the
# backend isn't ready, and only THEN calls backend.analyze() — the
# actual model call, which lives in step 9/10.
#
# See also: documents/reports/supervisor/defense_code_navigation.md
# ============================================================

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
    """
    Raised when the input violates the local runtime boundary.
    "Boundary" here means a DESIGN boundary of the system, not a bug —
    this project deliberately only handles pasted text, never images/audio/
    screenshots directly (no OCR, no speech-to-text pipeline). Raising a
    typed exception (not just printing a warning) means this boundary is
    enforced IN CODE, not just documented and hoped-for — every caller
    (CLI, browser demo) is forced to handle this case explicitly.
    """

    def __init__(self, message: str, steps: list[str] | None = None):
        super().__init__(message)
        self.steps = steps or []


class RuntimeUnavailableError(Exception):
    """Raised when the local backend is unavailable or fails closed."""

    def __init__(self, message: str, steps: list[str] | None = None):
        super().__init__(message)
        self.steps = steps or []


def looks_like_non_text_payload(text: str) -> bool:
    # A deliberately simple heuristic, not a full file-type sniffer: catches
    # the OBVIOUS ways a non-text payload might end up here (a bare
    # filename, a data: URI, or one of a few placeholder strings a upstream
    # UI might substitute for an unsupported attachment) — this isn't meant
    # to be airtight, it's a defense-in-depth check backing up the fact
    # that the UI/CLI simply never offers an image/audio upload path in the
    # first place. Three checks: file-extension suffix, data-URI prefix,
    # and known placeholder strings.
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
    """
    Constructs whichever concrete AnalyzerBackend implementation matches
    Settings — this is the ONE place backend selection happens. Three
    possible backends, all implementing the same AnalyzerBackend interface
    (so RuntimeService itself never needs to know or care which one it
    has):
      - "heuristic": HeuristicAnalyzer — pure regex/rule-based, no model at
        all. Useful as a zero-dependency fallback/baseline.
      - "gguf": GGUFAnalyzer (step 10) — the real fine-tuned model, running
        locally via llama.cpp/llama-cpp-python, CPU-friendly.
      - "accelerated": AcceleratedAnalyzer — a GPU-accelerated backend
        variant for machines that have one available.
    allowed_profiles double-checks BOTH that runtime_backend is a
    recognized value AND that runtime_profile is a valid profile name FOR
    that specific backend (e.g. "gguf-laptop" only makes sense under
    backend="gguf") — catches a mismatched backend/profile combination in
    Settings immediately at startup rather than failing confusingly deep
    inside model loading.
    """
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
        """
        THE REAL ORCHESTRATOR — every entry point into this project (CLI
        `analyze`, the browser demo's POST /api/analyze) calls exactly this
        one method, and NOTHING here is backend-specific. Read it top to
        bottom as a sequence of GATES, each of which can stop the request
        before it ever reaches a model:

          GATE 1 — privacy: if raw-text persistence is somehow enabled in
          settings, refuse outright. This check runs FIRST, before even
          looking at the text, because it's a policy check about the
          SYSTEM's configuration, not about this particular message.

          GATE 2 — normalize, then check for emptiness. normalize_text is
          the exact same function used back in step 1 on scraped seeds —
          one shared normalizer for training data and live input, so the
          model always sees text in the same canonical shape it was
          trained on.

          GATE 3 — the text-only boundary (looks_like_non_text_payload) —
          this is the "no OCR, no screenshots" boundary enforced in code.

          GATE 4 — minimum length — too-short text isn't reliably
          classifiable, so it's rejected with a clear reason rather than
          silently returning a low-confidence guess.

          GATE 5 — backend readiness (doctor()) — and this is where
          "fail closed" actually happens: if runtime_fail_closed is True
          (the deployed default) and the backend reports NOT ready, this
          refuses to even attempt analysis rather than risk a partial/
          broken/misleading result. "Fail closed" is a deliberate security/
          reliability posture, not an accident — better to clearly refuse
          than to silently produce a wrong answer.

          ONLY AFTER ALL FIVE GATES does this build an AnalysisRequest and
          call self.backend.analyze(request) — the actual model call,
          which for the GGUF backend leads into step 9/10.

          Error handling around the backend call: RuntimeBoundaryError is
          re-raised as-is (the backend can itself detect a boundary
          violation, e.g. if a backend-specific check catches something
          this service's own gates missed) — everything else gets wrapped
          into a RuntimeUnavailableError with actionable setup guidance,
          so a caller never has to deal with raw, backend-specific
          exception types (a missing model file, a llama.cpp load error,
          etc.) — they all surface through this one consistent error
          shape.

          Final step: cap the number of returned "top_cues" to
          runtime_max_cues — a display/UX limit (avoid overwhelming a user
          with dozens of flagged spans), applied here, AFTER grounding
          already happened deeper in the backend, not a substitute for it.
        """
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
    # The one-line factory both the CLI (step 7) and the browser demo call
    # — reads Settings, resolves the right backend via
    # _build_backend_from_settings, and wires it into a RuntimeService.
    # This is WHY the CLI and the browser UI are guaranteed to behave
    # identically for the same input: they both start from this exact same
    # construction path, there's no divergent "web version" of the
    # analysis logic anywhere.
    settings = get_settings()
    return RuntimeService(backend=_build_backend_from_settings(settings), settings=settings)
