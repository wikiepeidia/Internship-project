"""Local browser service for interactive Vietnamese phishing-risk analysis."""

from __future__ import annotations

import ipaddress
import json
import webbrowser
from pathlib import Path
from typing import Callable, get_args
from wsgiref.simple_server import make_server

from src.runtime.contracts import ChannelName
from src.runtime.service import (
    RuntimeBoundaryError,
    RuntimeUnavailableError,
    build_default_runtime_service,
)


ASSET_DIR = Path(__file__).with_name("demo_assets")
FONT_DIR = ASSET_DIR / "fonts"
FONT_CONTENT_TYPE = "font/woff2"
MAX_REQUEST_BYTES = 64 * 1024
MALFORMED_REQUEST = {
    "error": {
        "message": "Request body must be a valid JSON object.",
        "steps": [],
    }
}
KNOWN_FONT_FILES = frozenset(
    {
        "be-vietnam-pro-400-vietnamese.woff2",
        "be-vietnam-pro-400-latin-ext.woff2",
        "be-vietnam-pro-400-latin.woff2",
        "be-vietnam-pro-500-vietnamese.woff2",
        "be-vietnam-pro-500-latin-ext.woff2",
        "be-vietnam-pro-500-latin.woff2",
        "be-vietnam-pro-600-vietnamese.woff2",
        "be-vietnam-pro-600-latin-ext.woff2",
        "be-vietnam-pro-600-latin.woff2",
        "be-vietnam-pro-700-vietnamese.woff2",
        "be-vietnam-pro-700-latin-ext.woff2",
        "be-vietnam-pro-700-latin.woff2",
    }
)


def _json_response(start_response: Callable, status: str, payload: dict[str, object]) -> list[bytes]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    start_response(
        status,
        [
            ("Content-Type", "application/json; charset=utf-8"),
            ("Content-Length", str(len(body))),
            ("Cache-Control", "no-store"),
        ],
    )
    return [body]


def _text_response(start_response: Callable, status: str, content_type: str, body: bytes) -> list[bytes]:
    start_response(
        status,
        [
            ("Content-Type", content_type),
            ("Content-Length", str(len(body))),
        ],
    )
    return [body]


def _load_asset(name: str) -> bytes:
    return (ASSET_DIR / name).read_bytes()


def _expected_origin(environ) -> str:
    host = environ.get("HTTP_HOST")
    if not host:
        server_name = environ.get("SERVER_NAME", "")
        server_port = environ.get("SERVER_PORT", "")
        host = f"{server_name}:{server_port}" if server_port else server_name
    return f"http://{host}"


def _is_same_origin_request(environ) -> bool:
    """Reject cross-origin requests unless neither Origin nor Referer is sent (CR-02)."""

    expected = _expected_origin(environ)
    origin = environ.get("HTTP_ORIGIN")
    if origin is not None:
        return origin == expected
    referer = environ.get("HTTP_REFERER")
    if referer is not None:
        return referer == expected or referer.startswith(expected + "/")
    return True


class DemoApp:
    """Minimal WSGI app that serves the local demo page and runtime analysis endpoint."""

    def __init__(self, service) -> None:
        self.service = service

    def __call__(self, environ, start_response):
        method = environ.get("REQUEST_METHOD", "GET").upper()
        path = environ.get("PATH_INFO", "/") or "/"

        if method == "GET" and path == "/":
            return _text_response(start_response, "200 OK", "text/html; charset=utf-8", _load_asset("index.html"))
        if method == "GET" and path == "/static/demo.css":
            return _text_response(start_response, "200 OK", "text/css; charset=utf-8", _load_asset("demo.css"))
        if method == "GET" and path == "/static/demo.js":
            return _text_response(start_response, "200 OK", "application/javascript; charset=utf-8", _load_asset("demo.js"))
        if method == "GET" and path == "/static/i18n.js":
            return _text_response(start_response, "200 OK", "application/javascript; charset=utf-8", _load_asset("i18n.js"))
        if method == "GET" and path.startswith("/static/fonts/"):
            filename = path.removeprefix("/static/fonts/")
            if filename in KNOWN_FONT_FILES:
                return _text_response(start_response, "200 OK", FONT_CONTENT_TYPE, (FONT_DIR / filename).read_bytes())
        if method == "POST" and path == "/api/analyze":
            return self._handle_analyze(environ, start_response)

        return _json_response(start_response, "404 Not Found", {"error": {"message": "Not found", "steps": []}})

    def _handle_analyze(self, environ, start_response):
        content_type = (environ.get("CONTENT_TYPE") or "").split(";", 1)[0].strip().lower()
        if content_type != "application/json":
            return _json_response(
                start_response,
                "400 Bad Request",
                {"error": {"message": "Content-Type must be application/json.", "steps": []}},
            )
        if not _is_same_origin_request(environ):
            return _json_response(
                start_response,
                "403 Forbidden",
                {"error": {"message": "Cross-origin requests are not allowed.", "steps": []}},
            )

        try:
            content_length = int(environ.get("CONTENT_LENGTH") or 0)
            if content_length < 0 or content_length > MAX_REQUEST_BYTES:
                raise ValueError("request body length is outside the local demo bound")
            raw_body = (
                environ["wsgi.input"].read(content_length)
                if content_length
                else b"{}"
            )
            payload = json.loads(raw_body.decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("request body is not a JSON object")
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
            return _json_response(start_response, "400 Bad Request", MALFORMED_REQUEST)

        text = payload.get("text", "")
        channel = payload.get("channel", "unknown")
        if not isinstance(text, str):
            return _json_response(
                start_response,
                "400 Bad Request",
                {"error": {"message": "text must be a string.", "steps": []}},
            )
        if channel not in get_args(ChannelName):
            return _json_response(
                start_response,
                "400 Bad Request",
                {"error": {"message": "channel must be one of the supported text channels.", "steps": []}},
            )

        try:
            result = self.service.analyze_text(text, channel=channel)
        except RuntimeBoundaryError as exc:
            return _json_response(
                start_response,
                "400 Bad Request",
                {"error": {"message": str(exc), "steps": exc.steps}},
            )
        except RuntimeUnavailableError as exc:
            return _json_response(
                start_response,
                "503 Service Unavailable",
                {"error": {"message": str(exc), "steps": exc.steps}},
            )

        return _json_response(start_response, "200 OK", result.model_dump(mode="json"))


def build_demo_app(service=None) -> DemoApp:
    """Build the local demo WSGI app around the existing runtime service."""

    return DemoApp(service=service or build_default_runtime_service())


def require_loopback_host(host: str) -> str:
    """Return a normalized IPv4 local host or reject unsupported binding."""

    candidate = host.strip()
    if candidate.lower().rstrip(".") == "localhost":
        return candidate
    try:
        address = ipaddress.ip_address(candidate)
    except ValueError as exc:
        raise ValueError("demo host must be localhost or an IPv4 loopback address") from exc
    if address.version != 4 or not address.is_loopback:
        raise ValueError("demo host must be localhost or an IPv4 loopback address")
    return candidate


def run_demo_server(*, host: str = "127.0.0.1", port: int = 8765, open_browser: bool = True) -> int:
    """Run the local demo UI server until interrupted."""

    host = require_loopback_host(host)
    app = build_demo_app()
    url = f"http://{host}:{port}"
    print("Warming up local model...")
    app.service.backend.doctor()
    print(f"Local demo UI: {url}")

    if open_browser:
        webbrowser.open_new_tab(url)

    try:
        with make_server(host, port, app) as server:
            server.serve_forever()
    except KeyboardInterrupt:
        print("Demo server stopped.")
        return 0
    return 0
