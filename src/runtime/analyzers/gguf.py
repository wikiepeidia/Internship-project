"""Laptop-baseline GGUF backend for the Phase 3 local runtime."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from src.config.settings import get_settings
from src.model_adaptation.registry import load_model_registry
from src.runtime.contracts import AnalysisRequest, AnalysisResult, DoctorCheck, DoctorStatus, SuspiciousCue


GGUF_SETUP_GUIDE = "Run the Phase 3 GGUF conversion flow to register the selected local artifact."


@dataclass
class GGUFAnalyzer:
    """Contract-compatible local analyzer backed by registered GGUF artifacts."""

    registry_path: Path = field(default_factory=lambda: get_settings().model_registry_path)
    runtime_profile: str = field(default_factory=lambda: get_settings().runtime_profile_gguf)
    backend_name: str = "gguf"

    def _allowed_profiles(self) -> dict[str, str]:
        settings = get_settings()
        return {
            settings.runtime_profile_gguf: "baseline_winner_id",
            settings.runtime_profile_gguf_runner_up: "runner_up_id",
        }

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

        lowered_text = request.text.casefold()
        cues: list[SuspiciousCue] = []
        url_match = re.search(r"https?://\S+|\b\S+\.\S+/\S*", request.text)
        if url_match is not None:
            cues.append(
                SuspiciousCue(
                    span=url_match.group(0),
                    reason="Contains a link that should be verified before any login or transfer.",
                    cue_type="link_prompt",
                )
            )
        if "otp" in lowered_text:
            cues.append(
                SuspiciousCue(
                    span="OTP",
                    reason="Mentions one-time-password credentials.",
                    cue_type="credential_request",
                )
            )
        if any(bank_name in lowered_text for bank_name in ("vietcombank", "vpbank", "techcombank", "mb bank")):
            cues.append(
                SuspiciousCue(
                    span="bank-brand",
                    reason="Mentions a bank brand in a high-risk context.",
                    cue_type="bank_impersonation",
                )
            )

        if len(cues) >= 2:
            risk_tier = "high-risk"
            summary = "Local GGUF baseline flagged strong phishing indicators."
        elif len(cues) == 1:
            risk_tier = "suspicious"
            summary = "Local GGUF baseline found a suspicious indicator that needs review."
        else:
            risk_tier = "benign"
            summary = "Local GGUF baseline found no strong phishing indicators."

        return AnalysisResult(
            risk_tier=risk_tier,
            summary=summary,
            top_cues=cues[:3],
            backend_name=self.backend_name,
            normalized_text=request.text,
        )