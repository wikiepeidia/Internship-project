"""Optional accelerated local backend for stronger Phase 3 hardware."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from src.config.settings import get_settings
from src.model_adaptation.registry import load_model_registry
from src.runtime.contracts import AnalysisRequest, AnalysisResult, DoctorCheck, DoctorStatus, SuspiciousCue


ACCELERATED_SETUP_GUIDE = (
    "Run the Phase 3 training flow for the selected runner-up model and prepare the accelerated local environment."
)


@dataclass
class AcceleratedAnalyzer:
    """Contract-compatible accelerated backend backed by the selected runner-up artifact."""

    registry_path: Path = field(default_factory=lambda: get_settings().model_registry_path)
    runtime_profile: str = field(default_factory=lambda: get_settings().runtime_profile_accelerated)
    backend_name: str = "accelerated"

    def doctor(self) -> DoctorStatus:
        settings = get_settings()
        checks = [
            DoctorCheck(
                name="runtime-profile",
                passed=self.runtime_profile == settings.runtime_profile_accelerated,
                detail=f"runtime_profile={self.runtime_profile}",
                remediation_command=ACCELERATED_SETUP_GUIDE,
            )
        ]

        if not self.registry_path.exists():
            checks.append(
                DoctorCheck(
                    name="model-registry",
                    passed=False,
                    detail=f"Missing model registry: {self.registry_path}",
                    remediation_command=ACCELERATED_SETUP_GUIDE,
                )
            )
            return DoctorStatus(
                ready=False,
                backend_name=self.backend_name,
                checks=checks,
                setup_steps=[ACCELERATED_SETUP_GUIDE],
            )

        registry = load_model_registry(self.registry_path)
        has_selection = registry.selection is not None
        checks.append(
            DoctorCheck(
                name="pilot-selection",
                passed=has_selection,
                detail="Pilot selection metadata is available." if has_selection else "Pilot selection metadata is missing.",
                remediation_command=ACCELERATED_SETUP_GUIDE,
            )
        )
        if not has_selection:
            return DoctorStatus(
                ready=False,
                backend_name=self.backend_name,
                checks=checks,
                setup_steps=[ACCELERATED_SETUP_GUIDE],
            )

        target_candidate_id = registry.selection.runner_up_id
        adapter_artifact = next(
            (
                artifact
                for artifact in registry.artifacts
                if artifact.candidate_id == target_candidate_id and artifact.artifact_type == "adapter"
            ),
            None,
        )
        artifact_ready = adapter_artifact is not None and adapter_artifact.local_path.exists()
        checks.append(
            DoctorCheck(
                name="accelerated-artifact",
                passed=artifact_ready,
                detail=(
                    f"Accelerated artifact ready at {adapter_artifact.local_path}"
                    if artifact_ready
                    else f"Missing accelerated adapter artifact for candidate_id={target_candidate_id}"
                ),
                remediation_command=ACCELERATED_SETUP_GUIDE,
            )
        )

        ready = all(check.passed for check in checks)
        setup_steps = [] if ready else [ACCELERATED_SETUP_GUIDE]
        return DoctorStatus(
            ready=ready,
            backend_name=self.backend_name,
            checks=checks,
            setup_steps=setup_steps,
        )

    def analyze(self, request: AnalysisRequest) -> AnalysisResult:
        status = self.doctor()
        if not status.ready:
            raise RuntimeError("Accelerated backend is not ready")

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
        if any(keyword in lowered_text for keyword in ("tài khoản", "chuyển", "ngân hàng", "internet banking")):
            cues.append(
                SuspiciousCue(
                    span="financial-context",
                    reason="Mentions a financial action or account context.",
                    cue_type="financial_context",
                )
            )

        if len(cues) >= 2:
            risk_tier = "high-risk"
            summary = "Accelerated local profile flagged strong phishing indicators."
        elif len(cues) == 1:
            risk_tier = "suspicious"
            summary = "Accelerated local profile found a suspicious indicator that needs review."
        else:
            risk_tier = "benign"
            summary = "Accelerated local profile found no strong phishing indicators."

        return AnalysisResult(
            risk_tier=risk_tier,
            summary=summary,
            top_cues=cues[:3],
            backend_name=self.backend_name,
            normalized_text=request.text,
        )