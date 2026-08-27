"""Synthetic contracts for the phase-neutral data core."""

from __future__ import annotations

import ast
import hashlib
from pathlib import Path
import unicodedata

import pytest
from pydantic import ValidationError

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
    assert core_text.normalize_text(source) == "Ngân hàng Tiếng Việt OTP"
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
    new_result = core_splits.split_dataset(
        records,
        split_ratios=(0.8, 0.1, 0.1),
        salt="synthetic-group",
    )
    old_result = legacy_split(
        records,
        split_ratios=(0.8, 0.1, 0.1),
        salt="synthetic-group",
    )
    assert old_result == new_result
    assert {name: len(rows) for name, rows in new_result.items()} == {
        "train": 4,
        "val": 1,
        "test": 1,
    }


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


def test_active_data_modules_are_neutral_and_within_static_budgets() -> None:
    paths = (
        "src/data_pipeline/core/records.py",
        "src/data_pipeline/core/text.py",
        "src/data_pipeline/core/splits.py",
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
