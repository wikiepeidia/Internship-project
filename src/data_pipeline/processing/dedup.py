"""Lexical and semantic deduplication helpers for dataset split governance."""

from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any

import numpy as np

try:
    from rapidfuzz import fuzz
    RAPIDFUZZ_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised only when rapidfuzz is absent
    RAPIDFUZZ_AVAILABLE = False

    class _FallbackFuzz:
        @staticmethod
        def ratio(left: str, right: str) -> float:
            return SequenceMatcher(None, left, right).ratio() * 100

    fuzz = _FallbackFuzz()

try:
    from sentence_transformers import SentenceTransformer
except ImportError:  # pragma: no cover - exercised through mocked encoder paths
    SentenceTransformer = None


def lexical_dedup(records: list[dict[str, Any]], threshold: float = 0.95) -> list[dict[str, Any]]:
    """Remove exact and near-exact duplicates from a record list."""
    seen_texts: list[str] = []
    unique_records: list[dict[str, Any]] = []

    for record in records:
        text = record["text"]
        if any(fuzz.ratio(text, seen) / 100.0 >= threshold for seen in seen_texts):
            continue
        seen_texts.append(text)
        unique_records.append(record)

    return unique_records


def cross_split_dedup(
    train_records: list[dict[str, Any]],
    val_records: list[dict[str, Any]],
    test_records: list[dict[str, Any]],
    threshold: float = 0.85,
    model_name: str = "paraphrase-multilingual-MiniLM-L12-v2",
    encoder: Any | None = None,
) -> dict[str, list[str]]:
    """Find semantically similar records across train, val, and test splits."""
    removals: dict[str, list[str]] = {"val": [], "test": []}
    if not train_records or (not val_records and not test_records):
        return removals

    model = encoder
    if model is None:
        if SentenceTransformer is None:
            raise ValueError("sentence-transformers is required for semantic deduplication")
        model = SentenceTransformer(model_name)

    train_texts = [record["text"] for record in train_records]
    val_texts = [record["text"] for record in val_records]
    test_texts = [record["text"] for record in test_records]

    train_embeddings = np.asarray(model.encode(train_texts, normalize_embeddings=True))

    if val_texts:
        val_embeddings = np.asarray(model.encode(val_texts, normalize_embeddings=True))
        similarity_matrix = val_embeddings @ train_embeddings.T
        for index, row in enumerate(similarity_matrix):
            if float(row.max()) >= threshold:
                removals["val"].append(str(index))

    comparison_embeddings = train_embeddings
    if val_texts:
        remaining_val_texts = [
            text for index, text in enumerate(val_texts) if str(index) not in removals["val"]
        ]
        if remaining_val_texts:
            remaining_val_embeddings = np.asarray(
                model.encode(remaining_val_texts, normalize_embeddings=True)
            )
            comparison_embeddings = np.vstack([comparison_embeddings, remaining_val_embeddings])

    if test_texts:
        test_embeddings = np.asarray(model.encode(test_texts, normalize_embeddings=True))
        similarity_matrix = test_embeddings @ comparison_embeddings.T
        for index, row in enumerate(similarity_matrix):
            if float(row.max()) >= threshold:
                removals["test"].append(str(index))

    return removals