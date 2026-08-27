"""Synthetic contracts for the phase-neutral data core."""

from __future__ import annotations

import ast
import hashlib
from pathlib import Path
from types import SimpleNamespace
import unicodedata

import pytest
from pydantic import ValidationError

from src.core import integrity
from src.data_pipeline import schemas as legacy_records
from src.data_pipeline.core import records as core_records
from src.data_pipeline.core import splits as core_splits
from src.data_pipeline.core import text as core_text


REPO_ROOT = Path(__file__).parents[2]
PUBLIC_RECORD_SYMBOLS = (
    "SeedRecord",
    "ProvenancedSeedRecord",
    "DatasetRecord",
    "ManifestFile",
    "ManifestEntry",
    "RecordUnit",
    "AccessMethod",
    "RightsStatus",
    "RedactionState",
)


def _dataset_record(module: object):
    return module.DatasetRecord(
        text="Khẩn cấp: tài khoản của bạn cần xác minh ngay",
        label="bank_impersonation",
        risk_tier="high-risk",
        suspicious_spans=["Khẩn cấp", "xác minh ngay"],
        xai_explanation="Tin nhắn tạo áp lực và yêu cầu xác minh bất thường.",
        source="ncsc_seed",
        seed_id="seed_unicode_001",
    )


def test_old_and_new_record_imports_are_the_same_explicit_symbols() -> None:
    assert tuple(core_records.__all__) == PUBLIC_RECORD_SYMBOLS
    assert tuple(legacy_records.__all__) == PUBLIC_RECORD_SYMBOLS
    for name in PUBLIC_RECORD_SYMBOLS:
        assert getattr(legacy_records, name) is getattr(core_records, name), name

    for name in (
        "SeedRecord",
        "ProvenancedSeedRecord",
        "DatasetRecord",
        "ManifestFile",
        "ManifestEntry",
    ):
        assert getattr(core_records, name).__module__ == "src.data_pipeline.core.records"


def test_dataset_record_preserves_seven_field_utf8_bytes_and_defaults() -> None:
    record = _dataset_record(core_records)
    expected = (
        '{"text":"Khẩn cấp: tài khoản của bạn cần xác minh ngay",'
        '"label":"bank_impersonation","risk_tier":"high-risk",'
        '"suspicious_spans":["Khẩn cấp","xác minh ngay"],'
        '"xai_explanation":"Tin nhắn tạo áp lực và yêu cầu xác minh bất thường.",'
        '"source":"ncsc_seed","seed_id":"seed_unicode_001"}'
    ).encode("utf-8")

    assert record.model_dump_json().encode("utf-8") == expected
    assert legacy_records.DatasetRecord.model_validate_json(expected) == record
    assert list(record.model_dump()) == [
        "text",
        "label",
        "risk_tier",
        "suspicious_spans",
        "xai_explanation",
        "source",
        "seed_id",
    ]
    benign = core_records.DatasetRecord(
        text="Đây là thông báo giao dịch hợp lệ từ ngân hàng",
        label="benign",
        risk_tier="benign",
        xai_explanation="Thông báo không yêu cầu thao tác hoặc cung cấp thông tin.",
        source="synthetic_openai_compatible",
        seed_id="seed_unicode_002",
    )
    assert benign.suspicious_spans == []


@pytest.mark.parametrize(
    ("field", "value", "match"),
    (
        ("text", " " * 12, "human text fields"),
        ("xai_explanation", " " * 24, "human text fields"),
        ("seed_id", "   ", "seed_id must not be blank"),
        ("suspicious_spans", ["   "], "must not be blank"),
        (
            "suspicious_spans",
            ["Khẩn cấp", "Khẩn cấp"],
            "must be unique",
        ),
        (
            "suspicious_spans",
            ["cụm từ không có trong tin nhắn"],
            "exact substrings",
        ),
    ),
)
def test_dataset_record_rejects_fake_groups_and_invalid_spans(
    field: str, value: object, match: str
) -> None:
    payload = _dataset_record(core_records).model_dump()
    payload[field] = value
    with pytest.raises(ValidationError, match=match):
        core_records.DatasetRecord.model_validate(payload)


def test_dataset_record_normalizes_seed_identity_without_changing_message() -> None:
    payload = _dataset_record(core_records).model_dump()
    payload["seed_id"] = "  seed_unicode_001  "
    record = core_records.DatasetRecord.model_validate(payload)
    assert record.seed_id == "seed_unicode_001"
    assert record.text == payload["text"]


@pytest.mark.parametrize(
    "payload",
    [
        {
            "text": "quá ngắn",
            "label": "benign",
            "risk_tier": "benign",
            "xai_explanation": "Giải thích này đủ dài cho hợp đồng dữ liệu.",
            "source": "ncsc_seed",
            "seed_id": "seed_bad_text",
        },
        {
            "text": "Nội dung hợp lệ nhưng nhãn không thuộc hợp đồng",
            "label": "unknown",
            "risk_tier": "benign",
            "xai_explanation": "Giải thích này đủ dài cho hợp đồng dữ liệu.",
            "source": "ncsc_seed",
            "seed_id": "seed_bad_label",
        },
    ],
)
def test_old_and_new_validation_errors_are_identical(payload: dict[str, object]) -> None:
    errors: list[list[dict[str, object]]] = []
    for record_type in (core_records.DatasetRecord, legacy_records.DatasetRecord):
        with pytest.raises(ValidationError) as exc_info:
            record_type.model_validate(payload)
        errors.append(exc_info.value.errors(include_url=False))
    assert errors[0] == errors[1]


def test_provenanced_seed_normalization_remains_unicode_exact() -> None:
    text = "  CẢNH BÁO   tài khoản ngân hàng  "
    normalized = unicodedata.normalize("NFC", text).casefold().strip()
    normalized = " ".join(normalized.split())
    record = core_records.ProvenancedSeedRecord(
        text=text,
        source_url="https://example.test/advisory",
        scrape_timestamp="2026-08-27T00:00:00Z",
        raw_label_hint=None,
        data_origin="real_public",
        record_unit="editorial_advisory",
        canonical_url="https://example.test/advisory",
        publisher="Synthetic Publisher",
        native_id=None,
        access_method="download",
        collection_status="allowed",
        redistribution_status="unknown",
        rights_url="https://example.test/rights",
        retrieved_at="2026-08-27T00:00:00Z",
        content_sha256=hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
        redaction_state="not_needed",
        contributing_urls=["https://example.test/advisory"],
        duplicate_count=0,
        provenance_confidence="high",
    )
    assert legacy_records.ProvenancedSeedRecord.model_validate(
        record.model_dump()
    ) == record


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("source_url", "not-a-url"),
        ("canonical_url", "ftp://example.test/advisory"),
        ("rights_url", "example.test/rights"),
        ("contributing_urls", ["javascript:alert(1)"]),
        ("scrape_timestamp", "not-a-dateZ"),
        ("retrieved_at", "2026-08-27T07:00:00+07:00"),
    ),
)
def test_public_provenance_rejects_fake_urls_and_timestamps(
    field: str,
    value: object,
) -> None:
    text = "Cảnh báo tài khoản cần kiểm tra nguồn công khai."
    payload: dict[str, object] = {
        "text": text,
        "source_url": "https://example.test/source",
        "scrape_timestamp": "2026-08-27T00:00:00Z",
        "raw_label_hint": None,
        "data_origin": "real_public",
        "record_unit": "editorial_advisory",
        "canonical_url": "https://example.test/advisory",
        "publisher": "Synthetic Publisher",
        "native_id": None,
        "access_method": "download",
        "collection_status": "allowed",
        "redistribution_status": "unknown",
        "rights_url": "https://example.test/rights",
        "retrieved_at": "2026-08-27T00:00:00Z",
        "content_sha256": hashlib.sha256(
            "cảnh báo tài khoản cần kiểm tra nguồn công khai.".encode("utf-8")
        ).hexdigest(),
        "redaction_state": "not_needed",
        "contributing_urls": ["https://example.test/advisory"],
        "duplicate_count": 0,
        "provenance_confidence": "high",
    }
    payload[field] = value

    with pytest.raises(ValidationError):
        core_records.ProvenancedSeedRecord.model_validate(payload)


def test_public_provenance_serializes_timestamps_in_canonical_utc_form() -> None:
    text = "Cảnh báo tài khoản cần kiểm tra nguồn công khai."
    content_hash = hashlib.sha256(
        "cảnh báo tài khoản cần kiểm tra nguồn công khai.".encode("utf-8")
    ).hexdigest()
    record = core_records.ProvenancedSeedRecord(
        text=text,
        source_url="https://example.test/source",
        scrape_timestamp="2026-08-27T00:00:00+00:00",
        raw_label_hint=None,
        data_origin="real_public",
        record_unit="editorial_advisory",
        canonical_url="https://example.test/advisory",
        publisher="Synthetic Publisher",
        native_id=None,
        access_method="download",
        collection_status="allowed",
        redistribution_status="unknown",
        rights_url="https://example.test/rights",
        retrieved_at="2026-08-27T00:00:00+00:00",
        content_sha256=content_hash,
        redaction_state="not_needed",
        contributing_urls=["https://example.test/advisory"],
        duplicate_count=0,
        provenance_confidence="high",
    )

    assert record.scrape_timestamp == "2026-08-27T00:00:00Z"
    assert record.retrieved_at == "2026-08-27T00:00:00Z"


def test_manifest_contract_keeps_field_order_and_nested_types() -> None:
    manifest = core_records.ManifestEntry(
        version="v-synthetic",
        build_timestamp="2026-08-27T00:00:00Z",
        files={
            "synthetic.jsonl": core_records.ManifestFile(
                sha256="a" * 64,
                records=2,
                bytes=321,
            )
        },
    )
    assert list(manifest.model_dump()) == [
        "version",
        "build_timestamp",
        "git_commit",
        "files",
    ]
    assert manifest.git_commit is None
    assert isinstance(manifest.files["synthetic.jsonl"], core_records.ManifestFile)


def test_legacy_schema_module_is_only_an_explicit_compatibility_surface() -> None:
    path = REPO_ROOT / "src/data_pipeline/schemas.py"
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = [node for node in tree.body if isinstance(node, ast.ImportFrom)]

    assert len(imports) == 1
    assert imports[0].module == "src.data_pipeline.core.records"
    assert tuple(alias.name for alias in imports[0].names) == PUBLIC_RECORD_SYMBOLS
    assert "import *" not in source
    assert "__getattr__" not in source
    assert not any(
        isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        for node in tree.body
    )


def test_text_core_preserves_unicode_normalization_and_lexical_order() -> None:
    from src.data_pipeline.processing.normalizer import normalize_text as legacy_normalize
    from src.data_pipeline.processing.dedup import lexical_dedup as legacy_dedup

    source = "  NgÃ¢n hÃ ng   Tiếng  Việt\tOTP  "
    assert core_text.normalize_text(source) == "Ngân hà ng Tiếng Việt OTP"
    assert legacy_normalize is core_text.normalize_text

    records = [
        {"text": "Tin nhắn OTP giả mạo ngân hàng", "seed_id": "seed-a"},
        {"text": "Tin nhắn OTP giả mạo ngân hàng", "seed_id": "seed-b"},
        {"text": "Thông báo giao dịch hợp lệ", "seed_id": "seed-c"},
    ]
    expected = [records[0], records[2]]
    assert core_text.lexical_dedup(records, threshold=0.95) == expected
    assert legacy_dedup is core_text.lexical_dedup


def test_group_split_core_is_deterministic_and_old_path_compatible() -> None:
    from src.data_pipeline.processing.splitter import (
        assign_seed_split as legacy_assign,
        split_dataset as legacy_split,
    )

    expected = {
        "seed-a": "test",
        "seed-b": "test",
        "seed-c": "val",
        "seed-d": "val",
        "seed-e": "train",
    }
    actual = {
        seed_id: core_splits.assign_seed_split(
            seed_id,
            split_ratios=(0.6, 0.2, 0.2),
            salt="synthetic-v1",
        )
        for seed_id in expected
    }
    assert actual == expected
    assert legacy_assign is core_splits.assign_seed_split

    records = [
        core_records.DatasetRecord(
            text=f"Tin nhắn tổng hợp hợp lệ số {index}",
            label="benign",
            risk_tier="benign",
            xai_explanation="Giải thích tổng hợp đủ dài cho kiểm thử phân chia.",
            source="synthetic_claude",
            seed_id="seed-shared",
        ).model_dump()
        for index in range(6)
    ]
    with pytest.raises(ValueError, match="seed groups.*group-safe"):
        core_splits.split_dataset(
            records,
            split_ratios=(0.8, 0.1, 0.1),
            salt="synthetic-group",
        )
    with pytest.raises(ValueError, match="seed groups.*group-safe"):
        legacy_split(
            records,
            split_ratios=(0.8, 0.1, 0.1),
            salt="synthetic-group",
        )


def test_group_split_keeps_every_seed_in_exactly_one_partition() -> None:
    records = []
    for label, risk_tier in (
        ("bank_impersonation", "high-risk"),
        ("zalo_social_engineering", "suspicious"),
        ("task_scam", "high-risk"),
        ("benign", "benign"),
    ):
        for index in range(3):
            records.append(
                core_records.DatasetRecord(
                    text=f"Tin nhắn tổng hợp {label} số {index} đủ dài.",
                    label=label,
                    risk_tier=risk_tier,
                    xai_explanation="Giải thích tổng hợp đủ dài cho kiểm thử nhóm.",
                    source="synthetic_claude",
                    seed_id=f"{label}-seed-{index}",
                ).model_dump()
            )

    result = core_splits.split_dataset(
        records,
        split_ratios=(0.6, 0.2, 0.2),
        salt="synthetic-groups",
    )
    locations: dict[str, set[str]] = {}
    for split_name, rows in result.items():
        for row in rows:
            locations.setdefault(row["seed_id"], set()).add(split_name)
    assert len(locations) == len(records)
    assert all(len(split_names) == 1 for split_names in locations.values())
    assert sum(map(len, result.values())) == len(records)
    for label in {row["label"] for row in records}:
        assert all(any(row["label"] == label for row in result[name]) for name in result)


@pytest.mark.parametrize(
    "ratios",
    (
        (0.8, 0.2),
        (-0.1, 0.5, 0.6),
        (0.5, 0.2, 0.2),
        (float("nan"), 0.5, 0.5),
        (float("inf"), 0.0, 0.0),
    ),
)
def test_split_ratio_contract_fails_closed(ratios: tuple[float, ...]) -> None:
    from src.config.settings import DataSettings

    with pytest.raises(ValueError, match="split ratios"):
        core_splits.assign_seed_split("synthetic-seed", split_ratios=ratios)
    with pytest.raises(ValueError, match="split ratios"):
        core_splits.split_dataset([], split_ratios=ratios)
    with pytest.raises(ValueError, match="split_ratios"):
        DataSettings(split_ratios=ratios, _env_file=None)


def test_explicit_zero_similarity_threshold_reaches_dedup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.data_pipeline.processing import dedup, splitter

    captured: dict[str, float] = {}
    monkeypatch.setattr(dedup, "lexical_dedup", lambda records: records)
    monkeypatch.setattr(
        splitter,
        "split_dataset",
        lambda records, *, split_ratios, salt: {
            "train": list(records),
            "val": [],
            "test": [],
        },
    )

    def capture_threshold(*_splits: object, threshold: float) -> dict[str, list[str]]:
        captured["threshold"] = threshold
        return {"val": [], "test": []}

    monkeypatch.setattr(dedup, "cross_split_dedup", capture_threshold)

    splitter.split_and_dedup([], similarity_threshold=0.0)

    assert captured == {"threshold": 0.0}


def test_semantic_cleanup_cannot_remove_last_label_support(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.data_pipeline.processing import dedup, splitter

    rows = [
        {
            "text": f"Tin nhắn ngân hàng tổng hợp đủ dài số {index}",
            "label": "bank_impersonation",
            "risk_tier": "high-risk",
            "suspicious_spans": ["ngân hàng"],
            "xai_explanation": "Giải thích tổng hợp đủ dài cho kiểm thử phủ nhãn.",
            "source": "synthetic_claude",
            "seed_id": f"coverage-seed-{index}",
        }
        for index in range(3)
    ]
    monkeypatch.setattr(dedup, "lexical_dedup", lambda records: records)
    monkeypatch.setattr(
        splitter,
        "split_dataset",
        lambda _records, *, split_ratios, salt: {
            "train": [rows[0]],
            "val": [rows[1]],
            "test": [rows[2]],
        },
    )
    monkeypatch.setattr(
        dedup,
        "cross_split_dedup",
        lambda *_splits, threshold: {"val": ["0"], "test": []},
    )

    with pytest.raises(
        ValueError, match="post-dedup split coverage failed.*val/bank_impersonation"
    ):
        splitter.split_and_dedup(
            rows, split_ratios=(0.6, 0.2, 0.2), similarity_threshold=0.9
        )


def test_dataset_builder_preserves_explicit_zero_similarity_threshold(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from src.data_pipeline.versioning import build as build_module

    captured: dict[str, float] = {}
    builder = object.__new__(build_module.DatasetBuilder)
    builder.settings = SimpleNamespace(
        data_dir=tmp_path,
        similarity_threshold=0.85,
    )
    builder.version_tag = "synthetic-v1"
    monkeypatch.setattr(builder, "load_records", lambda _path: [])

    def capture_threshold(
        _records: list[dict[str, object]], *, similarity_threshold: float
    ) -> dict[str, list[dict[str, object]]]:
        captured["threshold"] = similarity_threshold
        return {}

    monkeypatch.setattr(build_module, "split_and_dedup", capture_threshold)
    monkeypatch.setattr(
        build_module,
        "build_manifest",
        lambda _root, version: SimpleNamespace(version=version),
    )
    monkeypatch.setattr(
        build_module,
        "save_manifest",
        lambda _manifest, _path, **_options: None,
    )

    builder.build_splits(
        input_path=tmp_path / "input.jsonl",
        output_dir=tmp_path / "output",
        similarity_threshold=0.0,
    )

    assert captured == {"threshold": 0.0}


@pytest.mark.parametrize("threshold", (-0.1, 1.1, float("nan"), float("inf")))
def test_similarity_threshold_contract_fails_closed(threshold: float) -> None:
    from src.config.settings import DataSettings
    from src.data_pipeline.processing.splitter import split_and_dedup

    with pytest.raises(ValueError, match="similarity_threshold"):
        DataSettings(similarity_threshold=threshold, _env_file=None)
    with pytest.raises(ValueError, match="similarity_threshold"):
        split_and_dedup([], similarity_threshold=threshold)


@pytest.mark.parametrize(
    "threshold", (-0.1, 1.1, float("nan"), float("inf"), float("-inf"), True)
)
def test_public_dedup_helpers_reject_invalid_thresholds(threshold: object) -> None:
    from src.data_pipeline.processing.dedup import cross_split_dedup

    with pytest.raises(ValueError, match="finite value"):
        core_text.lexical_dedup([], threshold=threshold)
    with pytest.raises(ValueError, match="finite value"):
        cross_split_dedup([], [], [], threshold=threshold)


def test_manifest_facade_versions_only_an_explicit_synthetic_root(tmp_path: Path) -> None:
    from src.data_pipeline.versioning.manifest import (
        build_manifest as legacy_build,
        save_manifest as legacy_save,
        verify_manifest as legacy_verify,
    )

    payload = "{\"synthetic\":true}\n\n{\"synthetic\":false}\n".encode("utf-8")
    dataset = tmp_path / "fixture.jsonl"
    dataset.write_bytes(payload)
    manifest = core_splits.build_manifest(tmp_path, "synthetic-v1")

    assert legacy_build is core_splits.build_manifest
    assert legacy_save is core_splits.save_manifest
    assert legacy_verify is core_splits.verify_manifest
    assert manifest.version == "synthetic-v1"
    assert manifest.files["fixture.jsonl"].sha256 == hashlib.sha256(payload).hexdigest()
    assert manifest.files["fixture.jsonl"].records == 2
    assert manifest.files["fixture.jsonl"].bytes == len(payload)
    assert core_splits.verify_manifest(manifest, tmp_path) == (True, [])

    saved = core_splits.save_manifest(manifest, tmp_path / "manifest.json")
    assert core_records.ManifestEntry.model_validate_json(
        saved.read_text(encoding="utf-8")
    ).version == "synthetic-v1"


@pytest.mark.parametrize(
    "member",
    (
        "../escape.jsonl",
        "/absolute.jsonl",
        "nested\\windows.jsonl",
        "C:/drive.jsonl",
        "./dot.jsonl",
        "not-json.txt",
    ),
)
def test_manifest_contract_rejects_unbounded_member_names(member: str) -> None:
    with pytest.raises(ValidationError, match="manifest members"):
        core_records.ManifestEntry(
            version="synthetic-v1",
            build_timestamp="2026-08-27T00:00:00Z",
            files={
                member: core_records.ManifestFile(
                    sha256="a" * 64,
                    records=0,
                    bytes=0,
                )
            },
        )


@pytest.mark.parametrize(
    "updates",
    (
        {"sha256": "A" * 64},
        {"sha256": "g" * 64},
        {"records": -1},
        {"bytes": -1},
    ),
)
def test_manifest_file_contract_rejects_invalid_facts(updates: dict[str, object]) -> None:
    payload: dict[str, object] = {"sha256": "a" * 64, "records": 0, "bytes": 0}
    payload.update(updates)
    with pytest.raises(ValidationError):
        core_records.ManifestFile.model_validate(payload)


def test_manifest_verification_reconciles_members_bytes_rows_and_utf8(
    tmp_path: Path,
) -> None:
    member = tmp_path / "fixture.jsonl"
    member.write_text('{"row":1}\n', encoding="utf-8")
    manifest = core_splits.build_manifest(tmp_path, "synthetic-v1")

    extra = tmp_path / "unexpected.jsonl"
    extra.write_text('{"row":2}\n', encoding="utf-8")
    ok, errors = core_splits.verify_manifest(manifest, tmp_path)
    assert not ok
    assert errors == ["Unexpected file: unexpected.jsonl"]
    extra.unlink()

    original = manifest.files["fixture.jsonl"]
    wrong_facts = core_records.ManifestEntry(
        version=manifest.version,
        build_timestamp=manifest.build_timestamp,
        files={
            "fixture.jsonl": core_records.ManifestFile(
                sha256=original.sha256,
                records=original.records + 1,
                bytes=original.bytes + 1,
            )
        },
    )
    ok, errors = core_splits.verify_manifest(wrong_facts, tmp_path)
    assert not ok
    assert "Byte-count mismatch for fixture.jsonl" in errors
    assert "Record-count mismatch for fixture.jsonl" in errors

    member.write_bytes(b"\xff\n")
    ok, errors = core_splits.verify_manifest(manifest, tmp_path)
    assert not ok
    assert any("strict UTF-8" in error for error in errors)


def test_manifest_verification_rejects_redirected_members(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.core.integrity import IntegrityError

    member = tmp_path / "redirected.jsonl"
    member.write_text('{"row":1}\n', encoding="utf-8")
    manifest = core_splits.build_manifest(tmp_path, "synthetic-v1")
    original_guard = core_splits.reject_redirecting_ancestry

    def reject_member(path: Path, *, where: str) -> Path:
        if Path(path).name == member.name:
            raise IntegrityError("synthetic reparse member")
        return original_guard(path, where=where)

    monkeypatch.setattr(core_splits, "reject_redirecting_ancestry", reject_member)

    ok, errors = core_splits.verify_manifest(manifest, tmp_path)
    assert not ok
    assert errors == ["synthetic reparse member"]


def test_manifest_atomic_replace_preserves_previous_bytes_on_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "manifest.json"
    previous = b'{"previous":true}\n'
    target.write_bytes(previous)
    manifest = core_records.ManifestEntry(
        version="synthetic-v2",
        build_timestamp="2026-08-27T00:00:00Z",
    )
    monkeypatch.setattr(
        integrity.os,
        "replace",
        lambda _source, _target: (_ for _ in ()).throw(OSError("synthetic failure")),
    )

    with pytest.raises(OSError, match="synthetic failure"):
        core_splits.save_manifest(manifest, target, replace=True)

    assert target.read_bytes() == previous
    assert not any(path.suffix == ".tmp" for path in tmp_path.iterdir())


def test_active_data_modules_are_neutral_and_within_static_budgets() -> None:
    paths = (
        "src/data_pipeline/core/records.py",
        "src/data_pipeline/core/text.py",
        "src/data_pipeline/core/splits.py",
        "src/data_pipeline/generation_runs.py",
        "src/data_pipeline/recovery.py",
        "src/data_pipeline/workflows.py",
        "src/data_pipeline/cli.py",
    )
    forbidden_import_roots = (
        "src.data_pipeline.generation",
        "src.data_pipeline.scraper",
        "src.data_pipeline.judge_merge",
        "src.data_pipeline.migrations",
        "src.model_adaptation",
        "src.modeling",
        "sentence_transformers",
    )
    for relative in paths:
        source = (REPO_ROOT / relative).read_text(encoding="utf-8")
        tree = ast.parse(source)
        assert len(source.splitlines()) <= 600, relative
        assert "data/splits" not in source.replace("\\", "/")
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = tuple(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = (node.module,)
            else:
                names = ()
            if relative.startswith("src/data_pipeline/core/"):
                assert not any(
                    name == root or name.startswith(f"{root}.")
                    for name in names
                    for root in forbidden_import_roots
                ), (relative, names)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                assert node.end_lineno is not None
                assert node.end_lineno - node.lineno + 1 <= 100, (
                    relative,
                    node.name,
                )
