"""Synthetic fail-closed contracts for recovery-only data paths."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.core.integrity import IntegrityError
from src.data_pipeline import recovery
from src.data_pipeline import workflows


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


def test_recovery_publication_rejects_redirect_parent_without_side_effects(
    tmp_path: Path,
) -> None:
    root = tmp_path / "corpus"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    try:
        (root / "recovery").symlink_to(outside, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"directory symlinks unavailable: {exc}")

    with pytest.raises(IntegrityError, match="symlink or reparse"):
        recovery.publish_recovered_outputs(root, [], [])

    assert list(outside.iterdir()) == []


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


def test_salvage_absent_or_empty_sources_never_create_primary(tmp_path: Path) -> None:
    root = tmp_path / "corpus"
    partial = root / "synthetic" / "generated-partial.jsonl"
    partial.parent.mkdir(parents=True)
    partial.write_text("\n", encoding="utf-8")
    generated = partial.with_name("generated.jsonl")

    with pytest.raises(recovery.RecoveryValidationError, match="nonempty source"):
        recovery.salvage_partial_records(root)

    assert not generated.exists()
    assert not (root / "recovery").exists()


def test_salvage_aggregates_errors_and_preserves_previous_primary(tmp_path: Path) -> None:
    root = tmp_path / "corpus"
    generated = root / "synthetic" / "generated.jsonl"
    shared_text = "Thông báo trùng nội dung phải được phát hiện xung đột."
    _write_record(generated, _record(shared_text, "benign", "seed-old"))
    previous = generated.read_bytes()
    partial = generated.with_name("generated-partial.jsonl")
    partial.write_text(
        "{not-json}\n"
        + json.dumps(
            _record(shared_text, "task_scam", "seed-conflict"),
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(recovery.RecoveryValidationError) as exc_info:
        recovery.salvage_partial_records(root)

    message = str(exc_info.value)
    assert "invalid strict JSON" in message
    assert "conflicting duplicate text" in message
    assert generated.read_bytes() == previous
    assert not (root / "recovery").exists()


def test_salvage_success_retains_content_addressed_backup_and_receipt(
    tmp_path: Path,
) -> None:
    root = tmp_path / "corpus"
    generated = root / "synthetic" / "generated.jsonl"
    partial = generated.with_name("generated-partial.jsonl")
    _write_record(
        generated,
        _record("Thông báo hợp lệ đã có trong dữ liệu chính.", seed_id="seed-old"),
    )
    previous = generated.read_bytes()
    _write_record(
        partial,
        _record("Thông báo hợp lệ được phục hồi từ tệp tạm.", seed_id="seed-new"),
    )
    partial_before = partial.read_bytes()

    result = recovery.salvage_partial_records(root)

    assert result["generated_before"] == 1
    assert result["partial_before"] == 1
    assert result["merged_unique"] == 2
    assert Path(result["backup_path"]).read_bytes() == previous
    assert Path(result["receipt_path"]).is_file()
    assert partial.read_bytes() == partial_before
    lines = generated.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert all(json.loads(line)["seed_id"] in {"seed-old", "seed-new"} for line in lines)


@pytest.mark.parametrize("target_count", (13, 14, 15, 17))
def test_nondivisible_recovery_targets_never_expand(target_count: int) -> None:
    by_label: dict[str, list[dict[str, object]]] = {}
    for label in workflows.THREAT_CLASSES:
        by_label[label] = [
            _record(
                f"Tin nhắn {label} phục vụ cân bằng số {index}.",
                label,
                f"{label}-seed-{index}",
            )
            for index in range(5)
        ]

    balanced, _feasible, selected, missing, requested, selected_by_label = (
        workflows._balance_recovered_records(by_label, target_count)
    )

    assert len(balanced) == target_count
    assert sum(requested.values()) == target_count
    assert sum(selected_by_label.values()) == target_count
    assert selected == min(selected_by_label.values())
    assert not any(missing.values())


def test_recovery_balance_rejects_absent_partial_and_single_seed_classes() -> None:
    def rows(label: str, count: int, seed_count: int | None = None):
        groups = count if seed_count is None else seed_count
        return [
            _record(
                f"Tin nhắn tổng hợp {label} số {index} đủ dài.",
                label=label,
                seed_id=f"{label}-seed-{index % max(groups, 1)}",
            )
            for index in range(count)
        ]

    complete = {label: rows(label, 3) for label in workflows.THREAT_CLASSES}
    absent = {label: list(items) for label, items in complete.items()}
    absent["task_scam"] = []
    with pytest.raises(ValueError, match="task_scam.*0 recoverable rows"):
        workflows._balance_recovered_records(absent, 12)

    partial = {label: list(items) for label, items in complete.items()}
    partial["task_scam"] = rows("task_scam", 2)
    with pytest.raises(ValueError, match="task_scam.*2 recoverable rows"):
        workflows._balance_recovered_records(partial, 12)

    single_seed = {label: list(items) for label, items in complete.items()}
    single_seed["task_scam"] = rows("task_scam", 3, seed_count=1)
    with pytest.raises(ValueError, match="task_scam.*1 seed groups"):
        workflows._balance_recovered_records(single_seed, 12)


def test_zero_recovery_target_never_publishes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    record = _record("Tin nhắn tổng hợp hợp lệ đủ dài.")
    monkeypatch.setattr(workflows, "_recoverable_record_paths", lambda _root: [tmp_path / "owned.jsonl"])
    monkeypatch.setattr(
        workflows,
        "_load_recoverable_records",
        lambda *_args: ({"one": record}, {"owned": {"loaded": 1}}, 1, 0, 0),
    )
    monkeypatch.setattr(
        workflows,
        "_write_recovered_outputs",
        lambda *_args: (_ for _ in ()).throw(AssertionError("writer must not run")),
    )

    result = workflows.optimize_recovered_records(tmp_path, target_count=0)

    assert result["publication_status"] == "not_requested"
    assert result["recovery_generation_id"] is None
    assert result["split_counts"] == {}


def test_zero_recovery_target_is_explicitly_empty() -> None:
    by_label = {
        label: [
            _record(
                f"Tin nhắn {label} không được chọn khi mục tiêu bằng không.",
                label,
                f"{label}-seed",
            )
        ]
        for label in workflows.THREAT_CLASSES
    }

    balanced, _feasible, selected, missing, requested, selected_by_label = (
        workflows._balance_recovered_records(by_label, 0)
    )

    assert balanced == []
    assert selected == 0
    assert requested == selected_by_label == {
        label: 0 for label in workflows.THREAT_CLASSES
    }
    assert missing == {label: 0 for label in workflows.THREAT_CLASSES}


@pytest.mark.parametrize("target_count", (-1, True, 1, 11, 12.0))
def test_invalid_recovery_target_fails_before_discovery(
    target_count: object,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        workflows,
        "_recoverable_record_paths",
        lambda _root: (_ for _ in ()).throw(AssertionError("discovery ran")),
    )

    with pytest.raises(ValueError, match="target_count"):
        workflows.optimize_recovered_records(tmp_path, target_count=target_count)


@pytest.mark.parametrize(
    "threshold", (-0.1, 1.1, float("nan"), float("inf"), float("-inf"), True)
)
def test_recovery_rejects_invalid_lexical_threshold_before_discovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    threshold: object,
) -> None:
    monkeypatch.setattr(
        workflows,
        "_recoverable_record_paths",
        lambda _root: (_ for _ in ()).throw(AssertionError("discovery ran")),
    )
    with pytest.raises(ValueError, match="lexical_threshold"):
        workflows.optimize_recovered_records(
            tmp_path, target_count=12, lexical_threshold=threshold
        )


def _group_safe_recovery_records() -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for label in workflows.THREAT_CLASSES:
        for index in range(3):
            records.append(
                _record(
                    f"Tin nhắn {label} cho thế hệ phục hồi số {index}.",
                    label,
                    f"{label}-generation-seed-{index}",
                )
            )
    return records


def test_recovery_publication_switches_one_verified_generation_pointer(
    tmp_path: Path,
) -> None:
    from src.data_pipeline.core.records import ManifestEntry
    from src.data_pipeline.core.splits import verify_manifest

    root = tmp_path / "corpus"
    root.mkdir()
    records = _group_safe_recovery_records()

    result = recovery.publish_recovered_outputs(root, records, records)

    pointer = json.loads(Path(result["current_pointer"]).read_text(encoding="utf-8"))
    assert pointer["generation_id"] == result["generation_id"]
    assert Path(result["merged_path"]).parent == Path(result["manifest_path"]).parent
    assert Path(result["balanced_path"]).parent == Path(result["manifest_path"]).parent
    manifest = ManifestEntry.model_validate_json(
        Path(result["manifest_path"]).read_text(encoding="utf-8")
    )
    assert verify_manifest(manifest, Path(result["manifest_path"]).parent) == (True, [])


def test_failed_recovery_generation_leaves_previous_pointer_unchanged(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "corpus"
    root.mkdir()
    records = _group_safe_recovery_records()
    first = recovery.publish_recovered_outputs(root, records, records)
    pointer = Path(first["current_pointer"])
    previous = pointer.read_bytes()
    monkeypatch.setattr(
        recovery,
        "save_manifest",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            OSError("synthetic manifest failure")
        ),
    )

    with pytest.raises(OSError, match="synthetic manifest failure"):
        recovery.publish_recovered_outputs(root, records, records)

    assert pointer.read_bytes() == previous
    assert Path(first["manifest_path"]).is_file()
