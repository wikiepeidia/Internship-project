"""Local-only HTTP demo boundary tests."""

from __future__ import annotations

from io import BytesIO
import json

import pytest

from src.runtime.cli import build_parser
from src.runtime.demo import DemoApp, MAX_REQUEST_BYTES, run_demo_server


class _UnusedService:
    def analyze_text(self, *_args: object, **_kwargs: object) -> object:
        raise AssertionError("malformed requests must not reach the runtime service")


def _request(raw: bytes, content_length: object | None = None) -> tuple[str, dict[str, object]]:
    status: list[str] = []

    def start_response(value: str, _headers: list[tuple[str, str]]) -> None:
        status.append(value)

    environ = {
        "REQUEST_METHOD": "POST",
        "PATH_INFO": "/api/analyze",
        "CONTENT_LENGTH": str(len(raw)) if content_length is None else content_length,
        "wsgi.input": BytesIO(raw),
    }
    response = DemoApp(_UnusedService())(environ, start_response)
    return status[0], json.loads(b"".join(response).decode("utf-8"))


@pytest.mark.parametrize(
    ("raw", "content_length"),
    [
        (b"{}", "not-an-integer"),
        (b"{}", "-1"),
        (b"{}", str(MAX_REQUEST_BYTES + 1)),
        (b"\xff", "1"),
        (b"{", "1"),
        (b"[]", "2"),
        (b"null", "4"),
        (b'"text"', "6"),
    ],
)
def test_demo_returns_one_json_400_contract_for_malformed_request_envelopes(
    raw: bytes,
    content_length: object,
) -> None:
    status, payload = _request(raw, content_length)
    assert status == "400 Bad Request"
    assert payload == {
        "error": {
            "message": "Request body must be a valid JSON object.",
            "steps": [],
        }
    }


@pytest.mark.parametrize("host", ["0.0.0.0", "192.168.1.20", "example.invalid"])
def test_demo_cli_rejects_non_loopback_hosts(host: str) -> None:
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args(["demo", "--host", host])
    assert exc.value.code == 2


def test_server_rejects_non_loopback_before_runtime_construction(monkeypatch) -> None:
    calls = {"build": 0}

    def forbidden_build() -> None:
        calls["build"] += 1
        raise AssertionError("runtime construction must not occur")

    monkeypatch.setattr("src.runtime.demo.build_demo_app", forbidden_build)
    with pytest.raises(ValueError, match="loopback"):
        run_demo_server(host="0.0.0.0", open_browser=False)
    assert calls == {"build": 0}


@pytest.mark.parametrize("host", ["localhost", "LOCALHOST.", "127.0.0.2", "::1"])
def test_demo_cli_accepts_loopback_hosts(host: str) -> None:
    args = build_parser().parse_args(["demo", "--host", host])
    assert args.host == host
