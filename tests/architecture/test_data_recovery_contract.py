"""Synthetic fail-closed contracts for recovery-only data paths."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.core.integrity import IntegrityError
from src.data_pipeline import recovery


def _record(text: str, label: str = "benign", seed_id: str = "seed-a") -> dict[str, object]:
    return {
        "text": text,
        "label": label,
        "risk_tier": "benign" if label == "benign" else "high-risk",
        "suspicious_spans": [],
        "xai_explanation": "Giải thích tổng hợp đủ dài cho kiểm thử phục hồi.",
        "source": "synthetic_openai_compatible",
        "seed_id": seed_id,
    }


def _write_record(path: Path, record: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")


def test_discovery_never_recurses_or_admits_finalized_splits(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "corpus"
    generated = root / "synthetic" / "generated.jsonl"
    _write_record(generated, _record("Thông báo giao dịch hợp lệ từ ngân hàng."))
    finalized = root / "splits"
    for name in ("train.jsonl", "val.jsonl", "test.jsonl"):
        _write_record(finalized / name, _record(f"Dữ liệu giữ lại {name} không được đọc."))

    monkeypatch.setattr(
        Path,
        "rglob",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("recursive discovery is forbidden")
        ),
    )
    original_read_bytes = Path.read_bytes
    opened: list[Path] = []

    def guarded_read_bytes(path: Path) -> bytes:
        opened.append(path)
        if finalized in path.parents:
            raise AssertionError("finalized split was opened")
        return original_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", guarded_read_bytes)

    paths = recovery.recoverable_record_paths(root)
    records, stats, loaded, invalid, conflicts = recovery.load_recoverable_records(
        root, paths
    )

    assert paths == [generated]
    assert list(records) == ["Thông báo giao dịch hợp lệ từ ngân hàng."]
    assert stats == {"synthetic/generated.jsonl": {"valid_records": 1, "invalid_items": 0}}
    assert (loaded, invalid, conflicts) == (1, 0, 0)
    assert not any(finalized in path.parents for path in opened)


def test_discovery_rejects_redirecting_allowlisted_member(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "corpus"
    generated = root / "synthetic" / "generated.jsonl"
    _write_record(generated, _record("Thông báo hợp lệ để kiểm tra đường dẫn."))
    original_guard = recovery.reject_redirecting_ancestry

    def reject_generated(path: Path, *, where: str) -> Path:
        if Path(path).name == generated.name and where == "recovery input":
            raise IntegrityError("synthetic reparse input")
        return original_guard(path, where=where)

    monkeypatch.setattr(recovery, "reject_redirecting_ancestry", reject_generated)

    with pytest.raises(IntegrityError, match="synthetic reparse input"):
        recovery.recoverable_record_paths(root)


def test_loader_aggregates_strict_utf8_and_label_conflicts(tmp_path: Path) -> None:
    root = tmp_path / "corpus"
    invalid = root / "synthetic" / "generated.jsonl"
    invalid.parent.mkdir(parents=True)
    invalid.write_bytes(b"\xff\n")
    shared_text = "Tin nhắn trùng nội dung nhưng nhãn xung đột nghiêm trọng."
    _write_record(
        root / "synthetic" / "generated-partial.jsonl",
        _record(shared_text, "benign", "seed-benign"),
    )
    _write_record(
        root / "synthetic" / "generated-gap-fill-recovered.jsonl",
        _record(shared_text, "task_scam", "seed-scam"),
    )

    paths = recovery.recoverable_record_paths(root)
    with pytest.raises(recovery.RecoveryValidationError) as exc_info:
        recovery.load_recoverable_records(root, paths)

    message = str(exc_info.value)
    assert "not strict UTF-8" in message
    assert "conflicting label" in message
    assert "2 error(s)" in message


def test_source_statistics_use_distinct_root_relative_identities(tmp_path: Path) -> None:
    root = tmp_path / "corpus"
    first = root / "synthetic" / "generated-partial.jsonl"
    second = root / "generation-runs" / "run-a" / "checkpoints" / "generated-partial.jsonl"
    _write_record(first, _record("Thông báo hợp lệ từ nguồn trực tiếp.", seed_id="seed-one"))
    _write_record(second, _record("Thông báo hợp lệ từ lần chạy riêng.", seed_id="seed-two"))

    paths = recovery.recoverable_record_paths(root)
    _records, stats, loaded, invalid, conflicts = recovery.load_recoverable_records(
        root, paths
    )

    assert list(stats) == [
        "generation-runs/run-a/checkpoints/generated-partial.jsonl",
        "synthetic/generated-partial.jsonl",
    ]
    assert loaded == 2
    assert invalid == conflicts == 0
