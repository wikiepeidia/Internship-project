"""Wave 0 privacy expectations for the Phase 2 runtime."""

import builtins
import importlib
from pathlib import Path

import pytest

from src.config.settings import Settings
from src.runtime.contracts import AnalysisResult, DoctorStatus


def _load_service_module():
    return importlib.import_module("src.runtime.service")


def test_default_runtime_path_never_requests_network_fallback(sample_benign_message, monkeypatch):
    service_module = _load_service_module()

    network_calls: list[str] = []

    def unexpected_network_call(*args, **kwargs):
        network_calls.append("called")
        raise AssertionError("network access is forbidden in the default runtime path")

    monkeypatch.setattr("requests.sessions.Session.request", unexpected_network_call)
    monkeypatch.setattr("httpx.Client.request", unexpected_network_call)

    class FakeBackend:
        backend_name = "heuristic"

        def doctor(self):
            return DoctorStatus(ready=True, backend_name=self.backend_name, checks=[])

        def analyze(self, request):
            return AnalysisResult(
                risk_tier="benign",
                summary="Local-only benign result.",
                backend_name=self.backend_name,
            )

    service = service_module.RuntimeService(backend=FakeBackend(), settings=Settings())
    result = service.analyze_text(sample_benign_message)

    assert result.risk_tier == "benign"
    assert network_calls == []


def test_runtime_does_not_persist_raw_text_by_default(sample_benign_message, monkeypatch):
    service_module = _load_service_module()
    settings = Settings()

    def forbidden_open(*args, **kwargs):
        raise AssertionError("raw text must not be persisted")

    def forbidden_write_text(self, *args, **kwargs):
        raise AssertionError("raw text must not be written to disk")

    def forbidden_write_bytes(self, *args, **kwargs):
        raise AssertionError("raw text must not be written to disk")

    monkeypatch.setattr(builtins, "open", forbidden_open)
    monkeypatch.setattr(Path, "write_text", forbidden_write_text)
    monkeypatch.setattr(Path, "write_bytes", forbidden_write_bytes)

    class FakeBackend:
        backend_name = "heuristic"

        def doctor(self):
            return DoctorStatus(ready=True, backend_name=self.backend_name, checks=[])

        def analyze(self, request):
            return AnalysisResult(
                risk_tier="benign",
                summary="No persistence occurred.",
                backend_name=self.backend_name,
            )

    service = service_module.RuntimeService(backend=FakeBackend(), settings=settings)
    result = service.analyze_text(sample_benign_message)

    assert result.summary == "No persistence occurred."


def test_failure_output_redacts_user_message(sample_mixed_vn_en_message):
    service_module = _load_service_module()
    render_module = importlib.import_module("src.runtime.render")

    class ExplodingBackend:
        backend_name = "heuristic"

        def doctor(self):
            return DoctorStatus(ready=True, backend_name=self.backend_name, checks=[])

        def analyze(self, request):
            raise RuntimeError(f"backend exploded while handling: {request.text}")

    service = service_module.RuntimeService(backend=ExplodingBackend(), settings=Settings())

    with pytest.raises(service_module.RuntimeUnavailableError) as exc_info:
        service.analyze_text(sample_mixed_vn_en_message)

    output = render_module.render_runtime_error(str(exc_info.value), exc_info.value.steps)

    assert sample_mixed_vn_en_message not in output
    assert "cloud" not in output.casefold()