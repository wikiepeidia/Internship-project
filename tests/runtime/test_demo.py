"""Local demo UI expectations over the existing runtime contract."""

from __future__ import annotations

import importlib
import io
import json
from wsgiref.util import setup_testing_defaults

from src.runtime.contracts import AnalysisResult, SuspiciousCue
from src.runtime.service import RuntimeBoundaryError


def _load_demo_module():
    return importlib.import_module("src.runtime.demo")


def _call_app(app, *, method: str, path: str, body: bytes = b"", content_type: str = "application/json"):
    status_line: dict[str, str] = {}
    headers_out: dict[str, str] = {}

    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "CONTENT_TYPE": content_type,
        "CONTENT_LENGTH": str(len(body)),
        "wsgi.input": io.BytesIO(body),
    }
    setup_testing_defaults(environ)

    def start_response(status, headers):
        status_line["value"] = status
        headers_out.update(dict(headers))

    response_body = b"".join(app(environ, start_response))
    return status_line["value"], headers_out, response_body


def test_demo_index_serves_text_only_form():
    demo_module = _load_demo_module()
    app = demo_module.build_demo_app(service=object())

    status, headers, body = _call_app(app, method="GET", path="/")
    html = body.decode("utf-8")

    assert status.startswith("200")
    assert headers["Content-Type"].startswith("text/html")
    assert "fonts.googleapis.com" not in html
    assert "fonts.gstatic.com" not in html
    assert "/static/demo.css" in html
    assert "/static/demo.js" in html
    assert 'id="analysis-form"' in html
    assert 'id="message-input"' in html
    assert 'id="channel-select"' in html
    assert 'id="sample-button"' in html
    assert 'id="analyze-button"' in html
    assert 'id="clear-button"' in html
    assert 'id="result-panel"' in html
    assert 'role="log"' in html
    assert 'aria-live="polite"' in html
    assert 'data-i18n="WELCOME_TEXT"' in html
    assert "Text-only" in html
    assert 'id="user-message-template"' in html
    assert 'id="result-template"' in html
    assert 'id="typing-template"' in html
    assert 'id="error-template"' in html
    assert 'data-slot="risk-tier"' in html
    assert 'data-slot="verdict"' in html
    assert 'data-slot="labels"' in html
    assert 'data-slot="grounded-cues"' in html
    assert 'data-slot="recommendations"' in html
    forbidden_template_ids = [
        "result-summary",
        "result-risk-tier",
        "result-labels",
        "result-backend",
        "result-cues",
        "result-recommendations",
        "error-message",
        "error-steps",
    ]
    for template_id in forbidden_template_ids:
        assert f'id="{template_id}"' not in html
    assert "Phase 6" not in html
    assert "Text-only v1" not in html


def test_demo_api_returns_runtime_contract_fields(sample_mixed_vn_en_message):
    demo_module = _load_demo_module()

    class FakeService:
        def analyze_text(self, text: str, channel: str = "unknown") -> AnalysisResult:
            assert text == sample_mixed_vn_en_message
            assert channel == "sms"
            return AnalysisResult(
                risk_tier="high-risk",
                summary="Tin nhan co dau hieu lua dao ro rang.",
                threat_labels=["bank_impersonation"],
                top_cues=[SuspiciousCue(span="OTP", reason="Yeu cau ma xac thuc nhay cam")],
                recommendations=["Khong bam vao lien ket trong tin nhan."],
                backend_name="gguf",
            )

    app = demo_module.build_demo_app(service=FakeService())
    request_body = json.dumps({"text": sample_mixed_vn_en_message, "channel": "sms"}).encode("utf-8")

    status, headers, body = _call_app(app, method="POST", path="/api/analyze", body=request_body)
    payload = json.loads(body.decode("utf-8"))

    assert status.startswith("200")
    assert headers["Content-Type"].startswith("application/json")
    assert payload["risk_tier"] == "high-risk"
    assert payload["threat_labels"] == ["bank_impersonation"]
    assert payload["top_cues"][0]["span"] == "OTP"
    assert payload["recommendations"] == ["Khong bam vao lien ket trong tin nhan."]
    assert payload["backend_name"] == "gguf"


def test_demo_api_returns_boundary_error_payload(sample_short_message):
    demo_module = _load_demo_module()

    class FakeService:
        def analyze_text(self, text: str, channel: str = "unknown") -> AnalysisResult:
            raise RuntimeBoundaryError(
                "Message text is too short for reliable local analysis.",
                steps=["Paste extracted text manually. OCR, screenshots, and voice messages are not supported in this demo."],
            )

    app = demo_module.build_demo_app(service=FakeService())
    request_body = json.dumps({"text": sample_short_message, "channel": "unknown"}).encode("utf-8")

    status, headers, body = _call_app(app, method="POST", path="/api/analyze", body=request_body)
    payload = json.loads(body.decode("utf-8"))

    assert status.startswith("400")
    assert headers["Content-Type"].startswith("application/json")
    assert payload["error"]["message"] == "Message text is too short for reliable local analysis."
    assert payload["error"]["steps"] == [
        "Paste extracted text manually. OCR, screenshots, and voice messages are not supported in this demo."
    ]


def test_demo_static_assets_are_served():
    demo_module = _load_demo_module()
    app = demo_module.build_demo_app(service=object())

    status, headers, body = _call_app(app, method="GET", path="/static/demo.css")

    assert status.startswith("200")
    assert headers["Content-Type"].startswith("text/css")
    css = body.decode("utf-8")
    assert "Be Vietnam Pro" in css
    assert "100dvh" in css
    assert "min-height: 0" in css
    assert "flex: 1 1 0" in css
    assert "env(safe-area-inset-bottom)" in css
    assert "prefers-reduced-motion" in css


def test_demo_font_assets_are_served():
    demo_module = _load_demo_module()
    app = demo_module.build_demo_app(service=object())

    for filename in sorted(demo_module.KNOWN_FONT_FILES):
        status, headers, body = _call_app(app, method="GET", path=f"/static/fonts/{filename}")

        assert status.startswith("200")
        assert headers["Content-Type"] == "font/woff2"
        assert body


def test_demo_font_route_rejects_unlisted_and_path_traversal_names():
    demo_module = _load_demo_module()
    app = demo_module.build_demo_app(service=object())

    expected = {"error": {"message": "Not found", "steps": []}}
    for path in (
        "/static/fonts/not-a-real-font.woff2",
        "/static/fonts/../demo.css",
    ):
        status, headers, body = _call_app(app, method="GET", path=path)

        assert status.startswith("404")
        assert headers["Content-Type"].startswith("application/json")
        assert json.loads(body.decode("utf-8")) == expected


def test_demo_i18n_js_is_served():
    demo_module = _load_demo_module()
    app = demo_module.build_demo_app(service=object())

    status, headers, body = _call_app(app, method="GET", path="/static/i18n.js")
    js = body.decode("utf-8")

    assert status.startswith("200")
    assert headers["Content-Type"].startswith("application/javascript")
    assert "window.I18N" in js
    assert "PLACEHOLDER" in js
    assert "ANALYZE_BTN" in js
    assert "RISK_HIGH" in js
