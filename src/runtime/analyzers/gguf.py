"""Laptop-baseline GGUF backend for the Phase 3 local runtime."""

from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.config.settings import get_settings
from src.model_adaptation.registry import load_model_registry
from src.runtime.analyzers.local_model import (
    build_analysis_result,
    build_structured_analysis_prompt,
    extract_structured_payload,
)
from src.runtime.contracts import AnalysisRequest, AnalysisResult, DoctorCheck, DoctorStatus


GGUF_SETUP_GUIDE = (
    "Install GGUF runtime extras with python -m pip install -e .[dev,runtime] and run the Phase 3 GGUF conversion flow to register the selected local artifact."
)


@dataclass
class GGUFAnalyzer:
    """Contract-compatible local analyzer backed by registered GGUF artifacts."""

    registry_path: Path = field(default_factory=lambda: get_settings().model_registry_path)
    runtime_profile: str = field(default_factory=lambda: get_settings().runtime_profile_gguf)
    backend_name: str = "gguf"
    _cached_runtime: Any | None = field(default=None, init=False, repr=False)
    _cached_artifact_path: Path | None = field(default=None, init=False, repr=False)

    def _allowed_profiles(self) -> dict[str, str]:
        settings = get_settings()
        return {
            settings.runtime_profile_gguf: "baseline_winner_id",
            settings.runtime_profile_gguf_runner_up: "runner_up_id",
        }

    def _resolve_artifact_path(self) -> Path:
        registry = load_model_registry(self.registry_path)
        if registry.selection is None:
            raise RuntimeError("Pilot selection metadata is missing")

        candidate_field = self._allowed_profiles()[self.runtime_profile]
        target_candidate_id = getattr(registry.selection, candidate_field)
        gguf_artifact = next(
            (
                artifact
                for artifact in registry.artifacts
                if artifact.candidate_id == target_candidate_id and artifact.artifact_type == "gguf"
            ),
            None,
        )
        if gguf_artifact is None or not gguf_artifact.local_path.exists():
            raise FileNotFoundError(f"Missing GGUF artifact for candidate_id={target_candidate_id}")
        return gguf_artifact.local_path

    def _load_runtime(self, artifact_path: Path) -> Any:
        if self._cached_runtime is not None and self._cached_artifact_path == artifact_path:
            return self._cached_runtime

        llama_cpp = importlib.import_module("llama_cpp")
        runtime = llama_cpp.Llama(
            model_path=str(artifact_path),
            n_ctx=1024,
            n_gpu_layers=0,
            verbose=False,
        )
        self._cached_runtime = runtime
        self._cached_artifact_path = artifact_path
        return runtime

    def _infer_payload(self, runtime: Any, text: str) -> dict[str, Any]:
        prompt = build_structured_analysis_prompt(text)
        if hasattr(runtime, "create_completion"):
            response = runtime.create_completion(
                prompt=prompt,
                max_tokens=256,
                temperature=0.0,
            )
        else:
            response = runtime(
                prompt,
                max_tokens=256,
                temperature=0.0,
                echo=False,
            )
        generated_text = str(response["choices"][0]["text"])
        return extract_structured_payload(generated_text)

    def doctor(self) -> DoctorStatus:
        checks: list[DoctorCheck] = []
        allowed_profiles = self._allowed_profiles()
        checks.append(
            DoctorCheck(
                name="runtime-profile",
                passed=self.runtime_profile in allowed_profiles,
                detail=f"runtime_profile={self.runtime_profile}",
                remediation_command=GGUF_SETUP_GUIDE,
            )
        )

        if not self.registry_path.exists():
            checks.append(
                DoctorCheck(
                    name="model-registry",
                    passed=False,
                    detail=f"Missing model registry: {self.registry_path}",
                    remediation_command=GGUF_SETUP_GUIDE,
                )
            )
            return DoctorStatus(
                ready=False,
                backend_name=self.backend_name,
                checks=checks,
                setup_steps=[GGUF_SETUP_GUIDE],
            )

        registry = load_model_registry(self.registry_path)
        has_selection = registry.selection is not None
        checks.append(
            DoctorCheck(
                name="pilot-selection",
                passed=has_selection,
                detail="Pilot selection metadata is available." if has_selection else "Pilot selection metadata is missing.",
                remediation_command=GGUF_SETUP_GUIDE,
            )
        )

        if not has_selection or self.runtime_profile not in allowed_profiles:
            return DoctorStatus(
                ready=False,
                backend_name=self.backend_name,
                checks=checks,
                setup_steps=[GGUF_SETUP_GUIDE],
            )

        candidate_field = allowed_profiles[self.runtime_profile]
        target_candidate_id = getattr(registry.selection, candidate_field)
        gguf_artifact = next(
            (
                artifact
                for artifact in registry.artifacts
                if artifact.candidate_id == target_candidate_id and artifact.artifact_type == "gguf"
            ),
            None,
        )
        artifact_ready = gguf_artifact is not None and gguf_artifact.local_path.exists()
        checks.append(
            DoctorCheck(
                name="gguf-artifact",
                passed=artifact_ready,
                detail=(
                    f"GGUF artifact ready at {gguf_artifact.local_path}"
                    if artifact_ready
                    else f"Missing GGUF artifact for candidate_id={target_candidate_id}"
                ),
                remediation_command=GGUF_SETUP_GUIDE,
            )
        )

        if artifact_ready:
            try:
                artifact_path = self._resolve_artifact_path()
                self._load_runtime(artifact_path)
                checks.append(
                    DoctorCheck(
                        name="gguf-runtime-load",
                        passed=True,
                        detail=f"GGUF runtime can load {artifact_path}",
                        remediation_command=GGUF_SETUP_GUIDE,
                    )
                )
            except Exception as exc:
                checks.append(
                    DoctorCheck(
                        name="gguf-runtime-load",
                        passed=False,
                        detail=f"GGUF runtime failed to load local resources: {exc}",
                        remediation_command=GGUF_SETUP_GUIDE,
                    )
                )

        ready = all(check.passed for check in checks)
        setup_steps = [] if ready else [GGUF_SETUP_GUIDE]
        return DoctorStatus(
            ready=ready,
            backend_name=self.backend_name,
            checks=checks,
            setup_steps=setup_steps,
        )

    def analyze(self, request: AnalysisRequest) -> AnalysisResult:
        status = self.doctor()
        if not status.ready:
            raise RuntimeError("GGUF backend is not ready")

        artifact_path = self._resolve_artifact_path()
        runtime = self._load_runtime(artifact_path)
        payload = self._infer_payload(runtime, request.text)
        return build_analysis_result(payload, request, self.backend_name)