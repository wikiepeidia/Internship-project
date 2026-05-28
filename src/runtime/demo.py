"""Local demo UI server for the Phase 6 non-technical verification flow."""

from __future__ import annotations

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
        if method == "POST" and path == "/api/analyze":
            return self._handle_analyze(environ, start_response)

        return _json_response(start_response, "404 Not Found", {"error": {"message": "Not found", "steps": []}})

    def _handle_analyze(self, environ, start_response):
        content_length = int(environ.get("CONTENT_LENGTH") or 0)
        raw_body = environ["wsgi.input"].read(content_length) if content_length else b"{}"

        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            return _json_response(
                start_response,
                "400 Bad Request",
                {"error": {"message": "Request body must be valid JSON.", "steps": []}},
            )

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


def run_demo_server(*, host: str = "127.0.0.1", port: int = 8765, open_browser: bool = True) -> int:
    """Run the local demo UI server until interrupted."""

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