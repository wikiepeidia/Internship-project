"""Offline generation gates for the Codex-authored Zalo replacement corpus."""

from __future__ import annotations

import json
from collections import Counter

import pytest

from src.data_pipeline.generation.generator import TieredGenerator
from src.data_pipeline.generation.zalo_codex_catalog import (
    AUTHORING_RUNTIME,
    CATALOG_VERSION,
    SEED_NAMESPACE_VERSION,
    SCENARIO_ROOTS,
    raw_variants_for_root,
)
from src.data_pipeline.generation.zalo_direct_actions import DIRECT_ACTIONS
from src.data_pipeline.generation.zalo_direct_messages import DIRECT_MESSAGE_TEMPLATES
from src.data_pipeline.generation.zalo_codex_recovery import (
    BUILD_METADATA,
    CatalogValidationError,
    FORBIDDEN_DIRECT_ACTION_PATTERNS,
    materialize_catalog,
    seed_record_for_root,
    validate_direct_message,
    validate_records,
    write_jsonl,
)
from src.data_pipeline.processing.dedup import fuzz
from src.data_pipeline.processing.normalizer import normalize_text
from src.data_pipeline.schemas import DatasetRecord


def test_catalog_has_exactly_sixty_independent_roots_and_five_variants_each():
    assert len(SCENARIO_ROOTS) == 60
    assert len({root.anchor for root in SCENARIO_ROOTS}) == 60
    assert len({root.semantic_signature for root in SCENARIO_ROOTS}) == 60
    assert set(DIRECT_MESSAGE_TEMPLATES) == {root.anchor for root in SCENARIO_ROOTS}
    assert set(DIRECT_ACTIONS) == {root.anchor for root in SCENARIO_ROOTS}
    assert len(set(DIRECT_ACTIONS.values())) == 60
    assert all(len(templates) == 5 for templates in DIRECT_MESSAGE_TEMPLATES.values())
    assert all(
        template.count("{requested_action}") == 1
        for templates in DIRECT_MESSAGE_TEMPLATES.values()
        for template in templates
    )
    assert all(len(raw_variants_for_root(root)) == 5 for root in SCENARIO_ROOTS)


def test_catalog_content_version_does_not_change_frozen_seed_namespace():
    assert CATALOG_VERSION == "zalo-codex-direct-2026-08-17"
    assert SEED_NAMESPACE_VERSION == "zalo-codex-2026-08-08"
    assert CATALOG_VERSION != SEED_NAMESPACE_VERSION


def test_materialization_is_schema_valid_seed_grouped_and_leakage_safe():
    records = materialize_catalog()
    counts = Counter(record["seed_id"] for record in records)

    assert len(records) == 300
    assert len(counts) == 60
    assert set(counts.values()) == {5}
    assert all(record["label"] == "zalo_social_engineering" for record in records)
    assert all(record["source"] == "synthetic_openai_compatible" for record in records)
    assert all(DatasetRecord.model_validate(record) for record in records)
    assert all(span in record["text"] for record in records for span in record["suspicious_spans"])
    assert all(
        record["text"].count(DIRECT_ACTIONS[root.anchor]) == 1
        for root_index, root in enumerate(SCENARIO_ROOTS)
        for record in records[root_index * 5 : (root_index + 1) * 5]
    )
    assert all(
        record["suspicious_spans"] == [DIRECT_ACTIONS[root.anchor]]
        for root_index, root in enumerate(SCENARIO_ROOTS)
        for record in records[root_index * 5 : (root_index + 1) * 5]
    )

    normalized = [normalize_text(record["text"]).casefold() for record in records]
    assert len(normalized) == len(set(normalized))
    for index, left in enumerate(normalized):
        assert all(fuzz.ratio(left, right) < 95 for right in normalized[index + 1 :])


def test_each_root_uses_tiered_generator_seed_derivation():
    generator = object.__new__(TieredGenerator)
    records = materialize_catalog()
    for root_index, root in enumerate(SCENARIO_ROOTS):
        expected_seed = generator._derive_seed_id(seed_record_for_root(root))
        root_records = records[root_index * 5 : (root_index + 1) * 5]
        assert {record["seed_id"] for record in root_records} == {expected_seed}


def test_materialization_never_initializes_or_calls_a_provider(monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("provider/network path must not be used")

    monkeypatch.setattr(TieredGenerator, "__init__", forbidden)
    for method_name in (
        "_call_claude",
        "_call_gemini",
        "_call_openrouter",
        "_call_deepseek",
        "_call_openai_compatible",
    ):
        monkeypatch.setattr(TieredGenerator, method_name, forbidden)

    records = materialize_catalog()
    assert len(records) == 300
    assert BUILD_METADATA == {
        "catalog_version": "zalo-codex-direct-2026-08-17",
        "seed_namespace_version": "zalo-codex-2026-08-08",
        "authoring_runtime": AUTHORING_RUNTIME,
        "provider_contract": "openai-compatible",
        "schema_source": "synthetic_openai_compatible",
        "generation_mode": "offline-static-direct-catalog",
        "wording_status": "new-semantic-reconstruction-not-verbatim-recovery",
        "external_api_calls": 0,
    }


def test_direct_message_gate_rejects_the_old_inner_narration_catalog():
    root = SCENARIO_ROOTS[0]
    legacy_inner_text = (
        f"{root.relationship}. {root.pretext}. {root.requested_action}. {root.urgency}."
    )
    with pytest.raises(CatalogValidationError, match="direct-message gate|legacy narrator relationship"):
        validate_direct_message(legacy_inner_text, root=root)

    with pytest.raises(CatalogValidationError, match="narrator:sender-says"):
        validate_direct_message(
            f"Người gửi nói cần xử lý ngay rồi {root.requested_action}.", root=root
        )


def test_every_authored_variant_is_direct_and_preserves_semantic_root_action():
    for root in SCENARIO_ROOTS:
        for row in raw_variants_for_root(root):
            validate_direct_message(row["text"], root=root)
            assert root.relationship not in row["text"]
            assert row["text"].count(DIRECT_ACTIONS[root.anchor]) == 1
            assert row["suspicious_spans"] == [DIRECT_ACTIONS[root.anchor]]


def test_direct_actions_do_not_expose_analyst_or_third_person_language():
    for anchor, action in DIRECT_ACTIONS.items():
        assert all(
            pattern.search(action) is None
            for _name, pattern in FORBIDDEN_DIRECT_ACTION_PATTERNS
        ), (anchor, action)


def test_jsonl_writer_persists_exact_validated_records_deterministically(tmp_path):
    records = materialize_catalog()
    first = tmp_path / "first.jsonl"
    second = tmp_path / "second.jsonl"
    write_jsonl(first, records)
    write_jsonl(second, records)

    loaded = [json.loads(line) for line in first.read_text(encoding="utf-8").splitlines()]
    assert loaded == records
    assert first.read_bytes() == second.read_bytes()


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("label", "bank_impersonation", "wrong label"),
        ("suspicious_spans", ["không tồn tại trong tin nhắn"], "invalid evidence span"),
        ("xai_explanation", "quá ngắn", "schema-valid"),
    ],
)
def test_validator_rejects_malformed_rows(field, value, message):
    row = materialize_catalog()[0]
    row[field] = value
    with pytest.raises(CatalogValidationError, match=message):
        validate_records([row], min_seed_groups=1, min_variants_per_group=1)


def test_validator_rejects_normalized_and_lexical_duplicates():
    records = materialize_catalog()[:2]
    duplicate = [dict(records[0]), dict(records[1])]
    duplicate[1]["text"] = f"  {records[0]['text'].upper()}  "
    duplicate[1]["suspicious_spans"] = [records[0]["suspicious_spans"][0].upper()]
    with pytest.raises(CatalogValidationError, match="duplicate normalized text"):
        validate_records(duplicate, min_seed_groups=1, min_variants_per_group=1)

    near_duplicate = [dict(records[0]), dict(records[1])]
    near_duplicate[1]["text"] = records[0]["text"] + " !"
    near_duplicate[1]["suspicious_spans"] = list(records[0]["suspicious_spans"])
    with pytest.raises(CatalogValidationError, match="lexical near-duplicates"):
        validate_records(near_duplicate, min_seed_groups=1, min_variants_per_group=1)
