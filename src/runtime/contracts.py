"""Typed contracts for the Phase 2 offline runtime."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


ChannelName = Literal["unknown", "sms", "zalo", "messenger", "telegram", "facebook"]
RiskTier = Literal["benign", "suspicious", "high-risk"]


class SuspiciousCue(BaseModel):
    """A quoted suspicious text span paired with a plain-language explanation."""

    span: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    cue_type: str | None = None

    @field_validator("span", "reason")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value must not be blank")
        return value


class AnalysisRequest(BaseModel):
    """One-message request contract for local runtime analysis."""

    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1)
    channel: ChannelName = "unknown"

    @field_validator("text")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("text must not be blank")
        return value


class AnalysisResult(BaseModel):
    """Typed result for a provisional offline threat analysis."""

    risk_tier: RiskTier
    summary: str = Field(min_length=1)
    top_cues: list[SuspiciousCue] = Field(default_factory=list, max_length=3)
    backend_name: str = Field(min_length=1)
    provisional: bool = True
    normalized_text: str | None = None

    @field_validator("summary", "backend_name")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value must not be blank")
        return value


class DoctorCheck(BaseModel):
    """One readiness check for the runtime doctor report."""

    name: str = Field(min_length=1)
    passed: bool
    detail: str = Field(min_length=1)
    remediation_command: str | None = None

    @field_validator("name", "detail")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value must not be blank")
        return value


class DoctorStatus(BaseModel):
    """Readiness snapshot for local runtime analysis."""

    ready: bool
    backend_name: str = Field(min_length=1)
    local_only: bool = True
    text_only: bool = True
    checks: list[DoctorCheck] = Field(default_factory=list)
    setup_steps: list[str] = Field(default_factory=list)

    @field_validator("backend_name")
    @classmethod
    def reject_blank_backend_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("backend_name must not be blank")
        return value
