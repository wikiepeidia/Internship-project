"""Contract tests for the Phase 2 offline runtime models."""

from typing import Protocol, get_args, get_type_hints

import pytest
from pydantic import ValidationError

from src.config.settings import Settings
from src.data_pipeline.schemas import DatasetRecord
from src.runtime.analyzers.base import AnalyzerBackend
from src.runtime.contracts import (
    AnalysisRequest,
    AnalysisResult,
    DoctorCheck,
    DoctorStatus,
    RiskTier,
    SuspiciousCue,
)


class TestAnalysisRequest:
    def test_accepts_text_with_optional_channel(self):
        request = AnalysisRequest(
            text="Ngân hàng yêu cầu xác minh OTP ngay hôm nay.",
            channel="sms",
        )

        assert request.text.startswith("Ngân hàng")
        assert request.channel == "sms"

    def test_defaults_channel_to_unknown(self):
        request = AnalysisRequest(text="Tài khoản của bạn cần được xác minh ngay.")

        assert request.channel == "unknown"

    def test_rejects_blank_text(self):
        with pytest.raises(ValidationError):
            AnalysisRequest(text="   ")


class TestSuspiciousCue:
    def test_rejects_blank_span(self):
        with pytest.raises(ValidationError):
            SuspiciousCue(span="   ", reason="Yêu cầu đăng nhập giả mạo")

    def test_rejects_blank_reason(self):
        with pytest.raises(ValidationError):
            SuspiciousCue(span="Smart OTP", reason="  ")


class TestAnalysisResult:
    def test_defaults_to_provisional(self):
        result = AnalysisResult(
            risk_tier="suspicious",
            summary="Tin nhắn có nhiều dấu hiệu cần xác minh thêm.",
            backend_name="heuristic",
        )

        assert result.provisional is True
        assert result.risk_tier == "suspicious"

    def test_analysis_result_caps_top_cues(self):
        cues = [
            SuspiciousCue(span=f"cue-{index}", reason="Lý do")
            for index in range(4)
        ]

        with pytest.raises(ValidationError):
            AnalysisResult(
                risk_tier="high-risk",
                summary="Có nhiều dấu hiệu phishing rõ ràng.",
                backend_name="heuristic",
                top_cues=cues,
            )


class TestDoctorContracts:
    def test_doctor_status_exposes_phase_two_fields(self):
        status = DoctorStatus(
            ready=False,
            backend_name="heuristic",
            checks=[
                DoctorCheck(
                    name="imports",
                    passed=False,
                    detail="Thiếu phụ thuộc cục bộ",
                    remediation_command="python -m pip install -e .[dev]",
                )
            ],
            setup_steps=["python -m src.runtime.cli doctor"],
        )

        assert status.ready is False
        assert status.local_only is True
        assert status.text_only is True
        assert status.checks[0].remediation_command == "python -m pip install -e .[dev]"
        assert status.setup_steps == ["python -m src.runtime.cli doctor"]


class TestProtocolAndSettings:
    def test_runtime_risk_tier_matches_dataset_schema(self):
        runtime_tiers = get_args(RiskTier)
        dataset_tiers = get_args(get_type_hints(DatasetRecord, include_extras=True)["risk_tier"])

        assert runtime_tiers == dataset_tiers

    def test_analyzer_backend_protocol_shape(self):
        assert issubclass(AnalyzerBackend, Protocol)

        annotations = getattr(AnalyzerBackend, "__annotations__", {})
        assert annotations["backend_name"] is str
        assert hasattr(AnalyzerBackend, "doctor")
        assert hasattr(AnalyzerBackend, "analyze")
        assert not hasattr(AnalyzerBackend, "cloud_fallback")

    def test_settings_expose_runtime_defaults(self):
        settings = Settings()

        assert settings.runtime_backend == "heuristic"
        assert settings.runtime_max_cues == 3
        assert settings.runtime_min_text_chars == 8
        assert settings.runtime_store_raw_text is False
        assert settings.runtime_fail_closed is True
        assert settings.runtime_allow_text_flag is True
        assert (
            settings.runtime_text_only_message
            == "Text-only v1: paste extracted text manually. Images/OCR and audio are not accepted in Phase 2."
        )