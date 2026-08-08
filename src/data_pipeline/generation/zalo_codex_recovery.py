"""Materialize the locally authored Zalo recovery corpus without providers.

This module intentionally has no provider setup path.  It feeds the static
catalog's raw JSON-array-shaped rows through ``TieredGenerator``'s existing
finalization method using an uninitialized instance, which reuses the exact
label/risk/source/seed/schema behavior without reading settings, API keys, or
creating an HTTP client.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from src.data_pipeline.generation.generator import OPENAI_COMPATIBLE_SOURCE, TieredGenerator
from src.data_pipeline.generation.zalo_codex_catalog import (
    AUTHORING_RUNTIME,
    CATALOG_VERSION,
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
    "authoring_runtime": AUTHORING_RUNTIME,
    "provider_contract": "openai-compatible",
    "schema_source": OPENAI_COMPATIBLE_SOURCE,
    "generation_mode": "offline-static-catalog",
    "external_api_calls": 0,
}


class CatalogValidationError(ValueError):
    """Raised when locally authored data violates the release contract."""


def seed_record_for_root(root: ScenarioRoot) -> SeedRecord:
    """Build the immutable anchor used by the existing seed derivation."""
    return SeedRecord(
        text=f"Zalo semantic root: {root.anchor}",
        source_url=f"urn:vnphish:{CATALOG_VERSION}:{root.anchor}",
        scrape_timestamp="2026-08-08T00:00:00Z",
        raw_label_hint=TARGET_LABEL,
    )


def _normalized_key(text: str) -> str:
    return normalize_text(text).casefold()


def _validate_root_catalog(roots: tuple[ScenarioRoot, ...]) -> None:
    if len(roots) < MIN_ROOTS:
        raise CatalogValidationError(f"catalog has {len(roots)} roots; need at least {MIN_ROOTS}")

    anchors = [root.anchor for root in roots]
    if len(set(anchors)) != len(anchors):
        raise CatalogValidationError("catalog contains duplicate stable anchors")

    signatures = [root.semantic_signature for root in roots]
    if len(set(signatures)) != len(signatures):
        raise CatalogValidationError("catalog contains duplicate semantic root signatures")

    for root in roots:
        if not root.anchor or not all(part.strip() for part in root.semantic_signature):
            raise CatalogValidationError(f"root {root.anchor!r} has an empty semantic dimension")


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
        if len(raw_records) < MIN_VARIANTS_PER_ROOT:
            raise CatalogValidationError(
                f"root {root.anchor!r} has {len(raw_records)} variants; need {MIN_VARIANTS_PER_ROOT}"
            )
        if any(raw.get("label") != TARGET_LABEL for raw in raw_records):
            raise CatalogValidationError(f"root {root.anchor!r} contains a wrong raw label")
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

