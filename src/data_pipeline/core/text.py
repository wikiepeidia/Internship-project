"""Deterministic text normalization and lexical deduplication."""

from __future__ import annotations

from difflib import SequenceMatcher
import math
import re
from typing import Any, Protocol
import unicodedata

import ftfy

try:
    from rapidfuzz import fuzz

    RAPIDFUZZ_AVAILABLE = True
except ImportError:  # pragma: no cover - host dependency fallback
    RAPIDFUZZ_AVAILABLE = False

    class _FuzzRatio(Protocol):
        @staticmethod
        def ratio(left: str, right: str) -> float: ...

    class _FallbackFuzz:
        @staticmethod
        def ratio(left: str, right: str) -> float:
            return SequenceMatcher(None, left, right).ratio() * 100

    fuzz: _FuzzRatio = _FallbackFuzz()


def normalize_text(text: str) -> str:
    """Repair mojibake and normalize Vietnamese text without changing tokens."""

    repaired = ftfy.fix_text(text)
    normalized = unicodedata.normalize("NFC", repaired).strip()
    return re.sub(r"\s+", " ", normalized)


def lexical_dedup(
    records: list[dict[str, Any]],
    threshold: float = 0.95,
) -> list[dict[str, Any]]:
    """Keep the first record from every exact or near-exact text cluster."""

    if (
        isinstance(threshold, bool)
        or not isinstance(threshold, (int, float))
        or not math.isfinite(float(threshold))
        or not 0.0 <= float(threshold) <= 1.0
    ):
        raise ValueError("lexical threshold must be a finite value in [0, 1]")
    threshold = float(threshold)

    seen_texts: list[str] = []
    unique_records: list[dict[str, Any]] = []
    for record in records:
        text = record["text"]
        if any(fuzz.ratio(text, seen) / 100.0 >= threshold for seen in seen_texts):
            continue
        seen_texts.append(text)
        unique_records.append(record)
    return unique_records


__all__ = (
    "RAPIDFUZZ_AVAILABLE",
    "fuzz",
    "lexical_dedup",
    "normalize_text",
)
