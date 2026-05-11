"""Wave 0 service expectations for the Phase 2 runtime."""

import importlib

from src.config.settings import Settings
from src.runtime.contracts import AnalysisResult, DoctorStatus


def _load_service_module():
    return importlib.import_module("src.runtime.service")


def test_runtime_service_normalizes_once_before_analysis(monkeypatch, sample_mixed_vn_en_message):
    service_module = _load_service_module()

    calls: list[str] = []
    captured = {}

    def fake_normalize_text(text: str) -> str:
        calls.append(text)
        return "normalized Smart OTP link text"

    class FakeBackend:
        backend_name = "fake"

        def doctor(self):
            return DoctorStatus(ready=True, backend_name=self.backend_name, checks=[])

        def analyze(self, request):
            captured["request"] = request
            return AnalysisResult(
                risk_tier="suspicious",
                summary="Provisional suspicious result.",
                backend_name=self.backend_name,
            )

    monkeypatch.setattr(service_module, "normalize_text", fake_normalize_text)

    service = service_module.RuntimeService(backend=FakeBackend(), settings=Settings())
    result = service.analyze_text(sample_mixed_vn_en_message, channel="sms")

    assert calls == [sample_mixed_vn_en_message]
    assert captured["request"].text == "normalized Smart OTP link text"
    assert captured["request"].channel == "sms"
    assert result.backend_name == "fake"


def test_runtime_service_returns_top_three_quoted_cues(
    sample_mixed_vn_en_message,
    expected_runtime_cues,
):
    service_module = _load_service_module()

    class FakeBackend:
        backend_name = "fake"

        def doctor(self):
            return DoctorStatus(ready=True, backend_name=self.backend_name, checks=[])

        def analyze(self, request):
            return AnalysisResult(
                risk_tier="high-risk",
                summary="Provisional high-risk result.",
                top_cues=expected_runtime_cues[:3],
                backend_name=self.backend_name,
                normalized_text=request.text,
            )

    service = service_module.RuntimeService(backend=FakeBackend(), settings=Settings())
    result = service.analyze_text(sample_mixed_vn_en_message)

    assert [cue.span for cue in result.top_cues] == [
        "mã OTP",
        "Smart OTP",
        "link đăng nhập",
    ]
    assert [cue.reason for cue in result.top_cues] == [
        "Yêu cầu mã xác thực nhạy cảm",
        "Nhắc tới công cụ xác thực ngân hàng",
        "Dẫn người dùng tới liên kết đăng nhập",
    ]


def test_runtime_service_preserves_mixed_language_content(sample_mixed_vn_en_message):
    service_module = _load_service_module()

    captured = {}

    class FakeBackend:
        backend_name = "fake"

        def doctor(self):
            return DoctorStatus(ready=True, backend_name=self.backend_name, checks=[])

        def analyze(self, request):
            captured["text"] = request.text
            return AnalysisResult(
                risk_tier="suspicious",
                summary="Mixed-language content preserved.",
                backend_name=self.backend_name,
                normalized_text=request.text,
            )

    service = service_module.RuntimeService(backend=FakeBackend(), settings=Settings())
    service.analyze_text(sample_mixed_vn_en_message, channel="messenger")

    assert "OTP" in captured["text"]
    assert "Smart OTP" in captured["text"]
    assert "Internet Banking" in captured["text"]
    assert "link" in captured["text"]
    assert "account" in captured["text"]