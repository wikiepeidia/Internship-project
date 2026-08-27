"""Forward-only integrity primitives for active application code."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class IntegrityError(RuntimeError):
    """Raised when untrusted bytes fail an integrity boundary."""


def strict_json_object(path: Path, *, where: str) -> dict[str, Any]:
    """Read one strict UTF-8 JSON object while rejecting duplicate keys."""

    raw = Path(path).read_bytes()

    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise IntegrityError(f"{where} contains duplicate JSON key {key!r}")
            result[key] = value
        return result

    try:
        value = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=reject_duplicates,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise IntegrityError(f"{where} must be strict UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise IntegrityError(f"{where} must be a JSON object")
    return value
