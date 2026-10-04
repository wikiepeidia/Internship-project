"""Strict JSON authority readers shared by architecture tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _reject_constant(value: str) -> None:
    raise AssertionError(f"non-finite JSON value: {value}")


def strict_json(raw: bytes) -> dict[str, Any]:
    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            assert key not in result, f"duplicate JSON key: {key}"
            result[key] = value
        return result

    value = json.loads(
        raw.decode("utf-8"),
        object_pairs_hook=reject_duplicates,
        parse_constant=_reject_constant,
    )
    assert isinstance(value, dict)
    return value


def load_strict_json(path: Path) -> dict[str, Any]:
    return strict_json(path.read_bytes())
