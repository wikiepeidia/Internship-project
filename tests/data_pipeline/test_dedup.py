"""Tests for lexical and semantic deduplication."""

from __future__ import annotations

import numpy as np

from src.data_pipeline.processing.dedup import cross_split_dedup, lexical_dedup


def test_lexical_dedup():
    records = [
        {"text": "Tin nhắn OTP giả mạo ngân hàng", "seed_id": "seed-a"},
        {"text": "Tin nhắn OTP giả mạo ngân hàng", "seed_id": "seed-b"},
        {"text": "Thong bao OTP gia mao ngan hang", "seed_id": "seed-c"},
        {"text": "Tin nhắn hoàn toàn khác", "seed_id": "seed-d"},
    ]

    deduped = lexical_dedup(records, threshold=0.95)

    assert len(deduped) == 3


def test_cross_split_dedup(monkeypatch):
    embeddings = {
        "train-close": np.array([1.0, 0.0]),
        "val-close": np.array([0.99, 0.01]),
        "val-far": np.array([0.0, 1.0]),
        "test-close-to-val": np.array([0.02, 0.98]),
        "test-far": np.array([0.6, 0.2]),
    }

    class FakeSentenceTransformer:
        def __init__(self, model_name):
            self.model_name = model_name

        def encode(self, texts, normalize_embeddings=True):
            return np.asarray([embeddings[text] for text in texts])

    monkeypatch.setattr("src.data_pipeline.processing.dedup.SentenceTransformer", FakeSentenceTransformer)

    removals = cross_split_dedup(
        [{"text": "train-close"}],
        [{"text": "val-close"}, {"text": "val-far"}],
        [{"text": "test-close-to-val"}, {"text": "test-far"}],
        threshold=0.85,
    )

    assert removals == {"val": ["0"], "test": ["0"]}


def test_cross_split_dedup_keeps_below_threshold(monkeypatch):
    class FakeSentenceTransformer:
        def __init__(self, model_name):
            self.model_name = model_name

        def encode(self, texts, normalize_embeddings=True):
            return np.asarray(
                [
                    [1.0, 0.0] if text == "train" else [0.1, 0.9]
                    for text in texts
                ]
            )

    monkeypatch.setattr("src.data_pipeline.processing.dedup.SentenceTransformer", FakeSentenceTransformer)

    removals = cross_split_dedup(
        [{"text": "train"}],
        [{"text": "val"}],
        [{"text": "test"}],
        threshold=0.95,
    )

    assert removals == {"val": [], "test": []}