"""Laptop-friendly GGUF analysis of Vietnamese phishing risk."""

from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.artifacts import (
    VerifiedArtifact,
    load_model_registry,
    resolve_registry_artifact,
    verify_artifact_identity,
)
from src.config.settings import get_runtime_settings as get_settings
from src.runtime.analyzers.local_model import (
    build_analysis_result,
    build_structured_analysis_prompt,
    extract_structured_payload,
)
from src.runtime.contracts import AnalysisRequest, AnalysisResult, DoctorCheck, DoctorStatus


GGUF_SETUP_GUIDE = (
    "Install GGUF runtime extras with python -m pip install -e .[dev,runtime] and register the selected local GGUF artifact."
)
GGUF_CONTEXT_WINDOW = 512
GGUF_COMPLETION_MAX_TOKENS = 250


@dataclass
class GGUFAnalyzer:
    """Contract-compatible local analyzer backed by registered GGUF artifacts."""

    registry_path: Path = field(
        default_factory=lambda: get_settings().resolved_model_registry_path
    )
    artifact_root: Path = field(
        default_factory=lambda: get_settings().resolved_model_artifact_root
    )
    storage_root: Path = field(
        default_factory=lambda: get_settings().resolved_model_storage_root
    )
    runtime_profile: str = field(default_factory=lambda: get_settings().runtime_profile_gguf)
    backend_name: str = "gguf"
    _cached_runtime: Any | None = field(default=None, init=False, repr=False)
    _cached_artifact: VerifiedArtifact | None = field(default=None, init=False, repr=False)
    _cached_doctor_status: DoctorStatus | None = field(default=None, init=False, repr=False)

    def _allowed_profiles(self) -> dict[str, str]:
        settings = get_settings()
        return {
            settings.runtime_profile_gguf: "baseline_winner_id",
            settings.runtime_profile_gguf_runner_up: "runner_up_id",
        }

    def _resolve_artifact(self) -> VerifiedArtifact:
        registry = load_model_registry(self.registry_path, storage_root=self.storage_root)
        if registry.selection is None:
            raise RuntimeError("Pilot selection metadata is missing")

        candidate_field = self._allowed_profiles()[self.runtime_profile]
        target_candidate_id = getattr(registry.selection, candidate_field)
        return resolve_registry_artifact(
            registry,
            artifact_root=self.artifact_root,
            candidate_id=target_candidate_id,
            artifact_type="gguf",
            profile_name=self.runtime_profile,
        )

    def _resolve_artifact_path(self) -> Path:
        return self._resolve_artifact().path

    def _load_runtime(self, artifact: VerifiedArtifact) -> Any:
        artifact_path = verify_artifact_identity(artifact)
        if self._cached_runtime is not None and self._cached_artifact == artifact:
            return self._cached_runtime

        llama_cpp = importlib.import_module("llama_cpp")
        runtime = llama_cpp.Llama(
            model_path=str(artifact_path),
            n_ctx=GGUF_CONTEXT_WINDOW,
            n_gpu_layers=0,
            verbose=False,
        )
        self._cached_runtime = runtime
        self._cached_artifact = artifact
        return runtime

    def _infer_payload(self, runtime: Any, text: str) -> dict[str, Any]:
        prompt = build_structured_analysis_prompt(text)
        if hasattr(runtime, "create_chat_completion"):
            chat_kwargs = {
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": GGUF_COMPLETION_MAX_TOKENS,
                "temperature": 0.0,
            }
            try:
                response = runtime.create_chat_completion(
                    **chat_kwargs,
                    response_format={"type": "json_object"},
                )
            except TypeError:
                response = runtime.create_chat_completion(**chat_kwargs)
            generated_text = str(response["choices"][0]["message"]["content"])
            return extract_structured_payload(generated_text)
        if hasattr(runtime, "create_completion"):
            response = runtime.create_completion(
                prompt=prompt,
                max_tokens=GGUF_COMPLETION_MAX_TOKENS,
                temperature=0.0,
            )
        else:
            response = runtime(
                prompt,
                max_tokens=GGUF_COMPLETION_MAX_TOKENS,
                temperature=0.0,
                echo=False,
            )
        generated_text = str(response["choices"][0]["text"])
        return extract_structured_payload(generated_text)

    def doctor(self) -> DoctorStatus:
        if self._cached_doctor_status is not None:
            return self._cached_doctor_status

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

        try:
            registry = load_model_registry(
                self.registry_path,
                storage_root=self.storage_root,
            )
        except Exception as exc:
            checks.append(
                DoctorCheck(
                    name="model-registry",
                    passed=False,
                    detail=f"Model registry is unavailable or invalid: {exc}",
                    remediation_command=GGUF_SETUP_GUIDE,
                )
            )
            return DoctorStatus(
                ready=False,
                backend_name=self.backend_name,
                checks=checks,
                setup_steps=[GGUF_SETUP_GUIDE],
            )

        checks.append(
            DoctorCheck(
                name="model-registry",
                passed=True,
                detail="Model registry passed its bounded integrity checks.",
                remediation_command=GGUF_SETUP_GUIDE,
            )
        )
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

        artifact: VerifiedArtifact | None = None
        artifact_error: Exception | None = None
        try:
            artifact = self._resolve_artifact()
        except Exception as exc:
            artifact_error = exc
        artifact_ready = artifact is not None
        checks.append(
            DoctorCheck(
                name="gguf-artifact",
                passed=artifact_ready,
                detail=(
                    "GGUF artifact passed bounded integrity verification."
                    if artifact_ready
                    else f"GGUF artifact is unavailable or invalid: {artifact_error}"
                ),
                remediation_command=GGUF_SETUP_GUIDE,
            )
        )

        if artifact_ready:
            try:
                assert artifact is not None
                self._load_runtime(artifact)
                checks.append(
                    DoctorCheck(
                        name="gguf-runtime-load",
                        passed=True,
                        detail="GGUF runtime loaded the verified artifact identity.",
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
        status = DoctorStatus(
            ready=ready,
            backend_name=self.backend_name,
            checks=checks,
            setup_steps=setup_steps,
        )
        if status.ready:
            self._cached_doctor_status = status
        return status

    def analyze(self, request: AnalysisRequest) -> AnalysisResult:
        status = self.doctor()
        if not status.ready:
            raise RuntimeError("GGUF backend is not ready")

        artifact = self._resolve_artifact()
        runtime = self._load_runtime(artifact)
        payload = self._infer_payload(runtime, request.text)
        return build_analysis_result(payload, request, self.backend_name)
