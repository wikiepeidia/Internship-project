"""Materialize the locally authored Zalo direct-message corpus without providers.

This module intentionally has no provider setup path.  It feeds the static
catalog's raw JSON-array-shaped rows through ``TieredGenerator``'s existing
finalization method using an uninitialized instance, which reuses the exact
label/risk/source/seed/schema behavior without reading settings, API keys, or
creating an HTTP client.

The 2026-08-17 content is a semantic reconstruction from the 60 frozen roots.
It does not claim to recover any original direct wording from the defective
2026-08-08 narrator catalog.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from src.data_pipeline.generation.generator import OPENAI_COMPATIBLE_SOURCE, TieredGenerator
from src.data_pipeline.generation.zalo_direct_actions import DIRECT_ACTIONS
from src.data_pipeline.generation.zalo_codex_catalog import (
    AUTHORING_RUNTIME,
    CATALOG_VERSION,
    SEED_NAMESPACE_VERSION,
    SCENARIO_ROOTS,
    ScenarioRoot,
    raw_variants_for_root,
)
from src.data_pipeline.processing.dedup import fuzz
from src.data_pipeline.processing.normalizer import normalize_text
from src.data_pipeline.schemas import DatasetRecord, SeedRecord


TARGET_LABEL = "zalo_social_engineering"
MIN_ROOTS = 60
MIN_VARIANTS_PER_ROOT = 5
LEXICAL_DUPLICATE_THRESHOLD = 0.95
DATASET_FIELDS = {
    "text",
    "label",
    "risk_tier",
    "suspicious_spans",
    "xai_explanation",
    "source",
    "seed_id",
}
BUILD_METADATA: dict[str, Any] = {
    "catalog_version": CATALOG_VERSION,
    "seed_namespace_version": SEED_NAMESPACE_VERSION,
    "authoring_runtime": AUTHORING_RUNTIME,
    "provider_contract": "openai-compatible",
    "schema_source": OPENAI_COMPATIBLE_SOURCE,
    "generation_mode": "offline-static-direct-catalog",
    "wording_status": "new-semantic-reconstruction-not-verbatim-recovery",
    "external_api_calls": 0,
}

FORBIDDEN_MESSAGE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("narrator:recipient-was-told", re.compile(r"\b(?:người dùng|người nhận|ứng viên|hành khách|cư dân|chủ hộ|người lao động)\s+được\s+(?:báo|thông báo)\b", re.IGNORECASE)),
    ("narrator:sender-says", re.compile(r"\b(?:người gửi|kẻ gửi)\s+(?:nói|tạo|phát|dùng|yêu cầu)\b", re.IGNORECASE)),
    ("narrator:account-claims", re.compile(r"\b(?:một\s+)?tài khoản(?:\s+Zalo)?\s+(?:mới\s+)?tự xưng\b", re.IGNORECASE)),
    ("narrator:outer-scaffold", re.compile(r"\b(?:tin Zalo từ|cuộc gọi Zalo chỉ|trong nhóm Zalo|được chép lại|tài khoản mang tên)\b", re.IGNORECASE)),
    ("meta:self-disclosure", re.compile(r"\b(?:giả|kẻ lừa đảo|nạn nhân)\b", re.IGNORECASE)),
    ("placeholder:brackets", re.compile(r"[\[\]{}<>]")),
    ("broken:lowercase-action-after-period", re.compile(r"\.\s+(?:quét|chuyển|đặt|nộp|thanh toán|bật|đăng nhập|gửi|cài|tải|mở|cung cấp|điền|đóng|trả|góp|nhập)\b")),
)
FORBIDDEN_DIRECT_ACTION_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("analyst:unknown-target", re.compile(r"\b(?:lạ|không thuộc)\b", re.IGNORECASE)),
    ("analyst:off-store", re.compile(r"\bngoài kho chính thức\b", re.IGNORECASE)),
    ("third-person:support", re.compile(r"\bcho nhân viên hỗ trợ\b", re.IGNORECASE)),
    ("third-person:personal-account", re.compile(r"\b(?:của người quen|của điều phối viên|của môi giới|tài khoản nhân viên)\b", re.IGNORECASE)),
)


class CatalogValidationError(ValueError):
    """Raised when locally authored data violates the release contract."""


def seed_record_for_root(root: ScenarioRoot) -> SeedRecord:
    """Build the immutable anchor used by the existing seed derivation."""
    return SeedRecord(
        text=f"Zalo semantic root: {root.anchor}",
        source_url=f"urn:vnphish:{SEED_NAMESPACE_VERSION}:{root.anchor}",
        scrape_timestamp="2026-08-08T00:00:00Z",
        raw_label_hint=TARGET_LABEL,
    )


def _normalized_key(text: str) -> str:
    return normalize_text(text).casefold()


def _validate_root_catalog(roots: tuple[ScenarioRoot, ...]) -> None:
    if len(roots) != MIN_ROOTS:
        raise CatalogValidationError(f"catalog has {len(roots)} roots; need exactly {MIN_ROOTS}")

    anchors = [root.anchor for root in roots]
    if len(set(anchors)) != len(anchors):
        raise CatalogValidationError("catalog contains duplicate stable anchors")

    signatures = [root.semantic_signature for root in roots]
    if len(set(signatures)) != len(signatures):
        raise CatalogValidationError("catalog contains duplicate semantic root signatures")

    for root in roots:
        if not root.anchor or not all(part.strip() for part in root.semantic_signature):
            raise CatalogValidationError(f"root {root.anchor!r} has an empty semantic dimension")
    anchors = set(anchors)
    if set(DIRECT_ACTIONS) != anchors:
        raise CatalogValidationError("direct-action catalog does not exactly cover the 60 roots")
    if len(set(DIRECT_ACTIONS.values())) != MIN_ROOTS:
        raise CatalogValidationError("direct-action catalog must contain 60 distinct actions")
    for anchor, action in DIRECT_ACTIONS.items():
        if not action or action != action.strip() or action[0] != action[0].lower():
            raise CatalogValidationError(f"root {anchor!r} has a malformed direct action")
        for name, pattern in FORBIDDEN_DIRECT_ACTION_PATTERNS:
            if pattern.search(action):
                raise CatalogValidationError(
                    f"root {anchor!r} direct action violates gate {name!r}: {action!r}"
                )


def validate_direct_message(text: str, *, root: ScenarioRoot | None = None) -> None:
    """Reject narrator/meta prose, placeholders, and known legacy root wording."""
    for name, pattern in FORBIDDEN_MESSAGE_PATTERNS:
        if pattern.search(text):
            raise CatalogValidationError(f"message violates direct-message gate {name!r}: {text!r}")

    roots = (root,) if root is not None else SCENARIO_ROOTS
    normalized = _normalized_key(text)
    for candidate_root in roots:
        relationship = _normalized_key(candidate_root.relationship)
        if relationship and relationship in normalized:
            raise CatalogValidationError(
                f"message copies legacy narrator relationship for root {candidate_root.anchor!r}"
            )


def validate_records(
    records: Iterable[dict[str, Any]],
    *,
    min_seed_groups: int = MIN_ROOTS,
    min_variants_per_group: int = MIN_VARIANTS_PER_ROOT,
) -> list[dict[str, Any]]:
    """Fail closed on schema, lineage, span, and duplicate violations."""
    validated: list[dict[str, Any]] = []
    normalized_texts: list[str] = []
    normalized_to_index: dict[str, int] = {}

    for index, record in enumerate(records):
        if set(record) != DATASET_FIELDS:
            raise CatalogValidationError(f"row {index} does not contain exactly the dataset fields")
        try:
            payload = DatasetRecord.model_validate(record).model_dump()
        except Exception as exc:  # Pydantic exposes several version-specific subclasses.
            raise CatalogValidationError(f"row {index} is not schema-valid: {exc}") from exc
        if payload["label"] != TARGET_LABEL:
            raise CatalogValidationError(f"row {index} has wrong label {payload['label']!r}")
        if payload["source"] != OPENAI_COMPATIBLE_SOURCE:
            raise CatalogValidationError(f"row {index} has dishonest source {payload['source']!r}")
        if len(payload["xai_explanation"].strip()) < 20:
            raise CatalogValidationError(f"row {index} has a short explanation")
        validate_direct_message(payload["text"])
        spans = payload["suspicious_spans"]
        if not spans or any(not span or span not in payload["text"] for span in spans):
            raise CatalogValidationError(f"row {index} has an invalid evidence span")

        normalized = _normalized_key(payload["text"])
        if normalized in normalized_to_index:
            other = normalized_to_index[normalized]
            raise CatalogValidationError(f"rows {other} and {index} duplicate normalized text")
        normalized_to_index[normalized] = index
        normalized_texts.append(normalized)
        validated.append(payload)

    for left_index, left in enumerate(normalized_texts):
        for right_index in range(left_index + 1, len(normalized_texts)):
            ratio = fuzz.ratio(left, normalized_texts[right_index]) / 100.0
            if ratio >= LEXICAL_DUPLICATE_THRESHOLD:
                raise CatalogValidationError(
                    f"rows {left_index} and {right_index} are lexical near-duplicates ({ratio:.3f})"
                )

    group_counts = Counter(record["seed_id"] for record in validated)
    if (
        min_seed_groups == MIN_ROOTS
        and min_variants_per_group == MIN_VARIANTS_PER_ROOT
        and (len(group_counts) != MIN_ROOTS or set(group_counts.values()) != {MIN_VARIANTS_PER_ROOT})
    ):
        raise CatalogValidationError(
            f"catalog must contain exactly {MIN_ROOTS} seed groups x "
            f"{MIN_VARIANTS_PER_ROOT} variants; got {dict(group_counts)}"
        )
    if len(group_counts) < min_seed_groups:
        raise CatalogValidationError(
            f"corpus has {len(group_counts)} seed groups; need at least {min_seed_groups}"
        )
    undersized = {seed_id: count for seed_id, count in group_counts.items() if count < min_variants_per_group}
    if undersized:
        raise CatalogValidationError(f"seed groups have too few variants: {undersized}")
    return validated


def materialize_catalog(
    roots: tuple[ScenarioRoot, ...] = SCENARIO_ROOTS,
) -> list[dict[str, Any]]:
    """Finalize and validate every catalog root, making no external calls."""
    _validate_root_catalog(roots)
    finalizer = object.__new__(TieredGenerator)
    records: list[dict[str, Any]] = []

    for root in roots:
        raw_records = raw_variants_for_root(root)
        if len(raw_records) != MIN_VARIANTS_PER_ROOT:
            raise CatalogValidationError(
                f"root {root.anchor!r} has {len(raw_records)} variants; need exactly "
                f"{MIN_VARIANTS_PER_ROOT}"
            )
        if any(raw.get("label") != TARGET_LABEL for raw in raw_records):
            raise CatalogValidationError(f"root {root.anchor!r} contains a wrong raw label")
        for raw in raw_records:
            validate_direct_message(raw["text"], root=root)
            direct_action = DIRECT_ACTIONS[root.anchor]
            if raw["text"].count(direct_action) != 1:
                raise CatalogValidationError(
                    f"root {root.anchor!r} variant must contain its direct action exactly once"
                )
        seed = seed_record_for_root(root)
        records.extend(
            finalizer._finalize_records(
                raw_records,
                seed,
                TARGET_LABEL,
                OPENAI_COMPATIBLE_SOURCE,
            )
        )

    return validate_records(records)


def catalog_sha256(records: Iterable[dict[str, Any]]) -> str:
    payload = "\n".join(
        json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        for record in records
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def materialization_metadata(records: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter(record["seed_id"] for record in records)
    return {
        **BUILD_METADATA,
        "records": len(records),
        "unique_seed_groups": len(counts),
        "minimum_variants_per_seed": min(counts.values()) if counts else 0,
        "catalog_sha256": catalog_sha256(records),
    }


def write_jsonl(output_path: Path, records: list[dict[str, Any]]) -> None:
    """Atomically write exactly the already validated rows."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_suffix(output_path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
    temporary.replace(output_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Materialize the offline Codex-authored Zalo corpus.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/synthetic/zalo-social-engineering-codex-2026-08-08.jsonl"),
    )
    args = parser.parse_args()

    records = materialize_catalog()
    write_jsonl(args.output, records)
    print(json.dumps(materialization_metadata(records), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
