"""Operator-facing CLI for the Phase 1 dataset pipeline."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Callable

from src.config.settings import get_settings
from src.data_pipeline.generation.prompts import THREAT_CLASSES
from src.data_pipeline.processing.dedup import RAPIDFUZZ_AVAILABLE, lexical_dedup
from src.data_pipeline.processing.splitter import split_dataset
from src.data_pipeline.generation.generator import TieredGenerator
from src.data_pipeline.generation.quality_judge import QualityJudge
from src.data_pipeline.schemas import DatasetRecord, SeedRecord
from src.data_pipeline.scraper.ncsc_scraper import NCSCScraper
from src.data_pipeline.versioning.build import DatasetBuilder


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m src.data_pipeline.cli",
        description="Run the Phase 1 scrape -> generate flow, with optional judging and split building.",
    )
    parser.add_argument(
        "--seed-input",
        type=Path,
        help="Existing raw seed JSONL file to use instead of scraping fresh advisories.",
    )
    parser.add_argument(
        "--target-count",
        type=int,
        default=2500,
        help="Synthetic record target count. Use 2000-3000 for the retained Phase 1 dataset.",
    )
    parser.add_argument(
        "--version-tag",
        default="phase1",
        help="Version tag used for the emitted manifest.",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=1,
        help="Maximum advisory listing pages to scrape when --seed-input is omitted.",
    )
    parser.add_argument(
        "--max-links-per-page",
        type=int,
        default=5,
        help="Maximum advisory links to inspect per listing page when scraping fresh seeds.",
    )
    parser.add_argument(
        "--max-seeds",
        type=int,
        default=None,
        help="Optional cap on scraped seed count when --seed-input is omitted.",
    )
    parser.add_argument(
        "--bulk-provider",
        choices=("auto", "claude", "gemini", "openrouter", "deepseek", "openai-compatible"),
        default="auto",
        help="Preferred provider for synthetic generation. Use 'openai-compatible' to target a Colab or local vLLM OpenAI-style endpoint.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from the last saved generation checkpoint instead of starting from scratch.",
    )
    parser.add_argument(
        "--max-parallel-batches",
        type=int,
        default=1,
        help="Number of generation batches to run concurrently. Use 1 for sequential, 2-4 for faster retained runs.",
    )
    parser.add_argument(
        "--checkpoint-dir",
        type=Path,
        default=None,
        help="Directory for incremental generation checkpoint files. Defaults to data/synthetic/.",
    )
    parser.add_argument(
        "--generate-only",
        action="store_true",
        help="Generate records only and skip all LLM judging, validation outputs, and split building.",
    )
    parser.add_argument(
        "--salvage-partial",
        action="store_true",
        help="Merge generated-partial.jsonl into generated.jsonl (de-duplicate by text), then exit. Does not delete generated-partial.jsonl.",
    )
    parser.add_argument(
        "--optimize-recovered",
        action="store_true",
        help="Merge recovered JSONL artifacts offline, de-duplicate, rebalance by class, and emit optimized outputs without API calls.",
    )
    return parser


def _stderr_progress(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def _build_anthropic_client(api_key: str) -> Any | None:
    if not api_key:
        return None
    try:
        import anthropic
    except ImportError as error:  # pragma: no cover - exercised only in real runtime environments
        raise ValueError("Anthropic SDK is required when ANTHROPIC_API_KEY is configured") from error
    return anthropic.Anthropic(api_key=api_key)


def _load_seed_records(seed_path: Path) -> list[SeedRecord]:
    if not seed_path.exists():
        raise FileNotFoundError(f"Seed input not found: {seed_path}")

    seeds: list[SeedRecord] = []
    with seed_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            seeds.append(SeedRecord.model_validate_json(line))

    return seeds


def _save_validated_records(
    records: list[dict[str, Any]],
    quality_stats: Any,
    data_dir: Path,
) -> tuple[Path, Path]:
    processed_dir = data_dir / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)

    validated_path = processed_dir / "validated.jsonl"
    tmp_validated = validated_path.with_suffix(".tmp")
    with tmp_validated.open("w", encoding="utf-8") as handle:
        for record in records:
            validated = DatasetRecord.model_validate(record)
            handle.write(validated.model_dump_json() + "\n")
    os.replace(tmp_validated, validated_path)

    stats_path = processed_dir / "quality-stats.json"
    tmp_stats = stats_path.with_suffix(".tmp")
    if hasattr(quality_stats, "model_dump_json"):
        tmp_stats.write_text(quality_stats.model_dump_json(indent=2), encoding="utf-8")
    else:
        tmp_stats.write_text(json.dumps(quality_stats, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp_stats, stats_path)

    return validated_path, stats_path


def salvage_partial_records(data_dir: Path) -> dict[str, Any]:
    """Merge generated-partial.jsonl into generated.jsonl, de-duplicating by text."""
    synthetic_dir = data_dir / "synthetic"
    generated_path = synthetic_dir / "generated.jsonl"
    partial_path = synthetic_dir / "generated-partial.jsonl"

    seen_texts: set[str] = set()
    merged: list[str] = []

    for source_path in (generated_path, partial_path):
        if not source_path.exists():
            continue
        with source_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                key = record.get("text") or line
                if key not in seen_texts:
                    seen_texts.add(key)
                    merged.append(line)

    before_generated = _count_nonempty_jsonl_lines(generated_path)
    before_partial = _count_nonempty_jsonl_lines(partial_path)
    duplicates_dropped = (before_generated + before_partial) - len(merged)

    tmp_path = generated_path.with_suffix(".tmp")
    generated_path.parent.mkdir(parents=True, exist_ok=True)
    with tmp_path.open("w", encoding="utf-8") as handle:
        for line in merged:
            handle.write(line + "\n")
    os.replace(tmp_path, generated_path)

    return {
        "generated_before": before_generated,
        "partial_before": before_partial,
        "merged_unique": len(merged),
        "duplicates_dropped": duplicates_dropped,
        "generated_path": str(generated_path),
        "partial_path_kept": str(partial_path),
    }


def _write_jsonl_records(output_path: Path, records: list[dict[str, Any]]) -> Path:
    tmp_path = output_path.with_suffix(".tmp")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tmp_path.open("w", encoding="utf-8") as handle:
        for record in records:
            validated = DatasetRecord.model_validate(record)
            handle.write(validated.model_dump_json() + "\n")
    os.replace(tmp_path, output_path)
    return output_path


def _count_nonempty_jsonl_lines(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8") as handle:
        return sum(1 for line in handle if line.strip())


def _count_labels(records: list[dict[str, Any]]) -> dict[str, int]:
    counts = {label: 0 for label in THREAT_CLASSES}
    for record in records:
        label = record.get("label")
        if label in counts:
            counts[label] += 1
    return counts


def _select_seed_diverse_records(records: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    if limit <= 0 or not records:
        return []

    grouped: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        grouped.setdefault(record["seed_id"], []).append(record)

    active_seed_ids = sorted(grouped)
    selected: list[dict[str, Any]] = []

    while active_seed_ids and len(selected) < limit:
        next_round: list[str] = []
        for seed_id in active_seed_ids:
            bucket = grouped[seed_id]
            if not bucket:
                continue
            selected.append(bucket.pop(0))
            if bucket:
                next_round.append(seed_id)
            if len(selected) >= limit:
                break
        active_seed_ids = next_round

    return selected


def _recoverable_record_paths(data_dir: Path) -> list[Path]:
    synthetic_dir = data_dir / "synthetic"
    processed_dir = data_dir / "processed"
    splits_dir = data_dir / "splits"

    output_names = {
        "recovered-merged.jsonl",
        "recovered-balanced.jsonl",
    }
    paths: list[Path] = []

    if processed_dir.exists():
        for path in sorted(processed_dir.glob("validated*.jsonl")):
            if path.name not in output_names:
                paths.append(path)

    if splits_dir.exists():
        for path in sorted(splits_dir.glob("*.jsonl")):
            if path.name not in output_names:
                paths.append(path)

    if synthetic_dir.exists():
        for pattern in ("generated*.jsonl", "checkpoint-*.jsonl", ".checkpoint*.jsonl"):
            for path in sorted(synthetic_dir.glob(pattern)):
                if path.name not in output_names:
                    paths.append(path)

    deduped_paths: list[Path] = []
    seen_paths: set[Path] = set()
    for path in paths:
        if path not in seen_paths:
            seen_paths.add(path)
            deduped_paths.append(path)
    return deduped_paths


def optimize_recovered_records(
    data_dir: Path,
    target_count: int = 2500,
    lexical_threshold: float = 0.97,
) -> dict[str, Any]:
    source_paths = _recoverable_record_paths(data_dir)
    if not source_paths:
        raise ValueError("No recoverable JSONL artifacts found under data/.")

    loaded_records = 0
    invalid_items = 0
    text_conflicts = 0
    unique_by_text: dict[str, dict[str, Any]] = {}
    source_stats: dict[str, dict[str, int]] = {}

    for path in source_paths:
        stats = source_stats.setdefault(path.name, {"valid_records": 0, "invalid_items": 0})
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    stats["invalid_items"] += 1
                    invalid_items += 1
                    continue

                candidates: list[dict[str, Any]] = []
                if isinstance(payload, dict) and isinstance(payload.get("records"), list):
                    candidates = [item for item in payload["records"] if isinstance(item, dict)]
                elif isinstance(payload, dict) and payload.get("text"):
                    candidates = [payload]

                for candidate in candidates:
                    try:
                        record = DatasetRecord.model_validate(candidate).model_dump()
                    except Exception:
                        stats["invalid_items"] += 1
                        invalid_items += 1
                        continue

                    loaded_records += 1
                    stats["valid_records"] += 1
                    text_key = record["text"].strip()
                    existing = unique_by_text.get(text_key)
                    if existing is None:
                        unique_by_text[text_key] = record
                    elif existing.get("label") != record.get("label"):
                        text_conflicts += 1

    exact_unique_records = list(unique_by_text.values())
    exact_counts = _count_labels(exact_unique_records)

    deduped_by_label: dict[str, list[dict[str, Any]]] = {}
    lexical_dedup_applied = RAPIDFUZZ_AVAILABLE and lexical_threshold < 1.0
    for label in THREAT_CLASSES:
        class_records = [record for record in exact_unique_records if record["label"] == label]
        if lexical_dedup_applied:
            deduped_by_label[label] = lexical_dedup(class_records, threshold=lexical_threshold)
        else:
            deduped_by_label[label] = class_records

    lexical_counts = {label: len(records) for label, records in deduped_by_label.items()}
    feasible_per_class = min(lexical_counts.values()) if lexical_counts else 0
    requested_per_class = max(target_count // len(THREAT_CLASSES), 0)
    selected_per_class = feasible_per_class
    if requested_per_class:
        selected_per_class = min(selected_per_class, requested_per_class)

    balanced_records: list[dict[str, Any]] = []
    for label in THREAT_CLASSES:
        balanced_records.extend(
            _select_seed_diverse_records(deduped_by_label[label], selected_per_class)
        )

    merged_output_path = _write_jsonl_records(data_dir / "synthetic" / "recovered-merged.jsonl", exact_unique_records)
    balanced_output_path = _write_jsonl_records(data_dir / "synthetic" / "recovered-balanced.jsonl", balanced_records)

    split_dir = data_dir / "splits" / "recovered-balanced"
    split_stats: dict[str, int] = {}
    for split_name, split_records in split_dataset(balanced_records).items():
        split_path = split_dir / f"{split_name}.jsonl"
        _write_jsonl_records(split_path, split_records)
        split_stats[split_name] = len(split_records)

    return {
        "source_files": [str(path) for path in source_paths],
        "source_stats": source_stats,
        "loaded_records": loaded_records,
        "invalid_items": invalid_items,
        "text_conflicts": text_conflicts,
        "exact_unique": len(exact_unique_records),
        "exact_unique_by_label": exact_counts,
        "lexical_dedup_applied": lexical_dedup_applied,
        "lexical_unique_by_label": lexical_counts,
        "requested_target_count": target_count,
        "feasible_balanced_per_class": feasible_per_class,
        "selected_per_class": selected_per_class,
        "balanced_total": len(balanced_records),
        "balanced_by_label": _count_labels(balanced_records),
        "merged_output_path": str(merged_output_path),
        "balanced_output_path": str(balanced_output_path),
        "split_dir": str(split_dir),
        "split_counts": split_stats,
    }


def run_phase1(
    seed_input: Path | None = None,
    target_count: int = 2500,
    version_tag: str = "phase1",
    max_pages: int = 1,
    max_links_per_page: int = 5,
    max_seeds: int | None = None,
    bulk_provider: str = "auto",
    resume: bool = False,
    max_parallel_batches: int = 1,
    checkpoint_dir: Path | None = None,
    generate_only: bool = False,
) -> dict[str, Any]:
    settings = get_settings()
    checkpoint_base = checkpoint_dir or (settings.data_dir / "synthetic")
    # checkpoint_path is now the directory containing numbered checkpoint-NNN.jsonl files
    checkpoint_path = checkpoint_base
    generated_path = settings.data_dir / "synthetic" / "generated.jsonl"
    incremental_generated_path = generated_path if generate_only else (checkpoint_base / "generated-partial.jsonl")

    if generate_only and resume and any(checkpoint_path.glob("checkpoint-*.jsonl")) and generated_path.exists():
        generated_path.unlink()

    if seed_input is not None:
        seeds = _load_seed_records(seed_input)
    else:
        scraper = NCSCScraper()
        seeds = scraper.scrape_advisory_list(
            max_pages=max_pages,
            max_links_per_page=max_links_per_page,
            max_seeds=max_seeds,
        )
        if seeds:
            scraper.save_seeds(seeds)

    if not seeds:
        raise ValueError("No seeds available for Phase 1 generation")

    anthropic_client = _build_anthropic_client(settings.anthropic_api_key)
    generator = TieredGenerator(
        settings=settings,
        anthropic_client=anthropic_client,
        bulk_provider=bulk_provider,
    )
    generated_records = generator.generate_dataset(
        seeds,
        target_count=target_count,
        max_parallel_batches=max_parallel_batches,
        checkpoint_path=checkpoint_path,
        partial_output_path=incremental_generated_path,
        resume=resume,
        progress_callback=_stderr_progress,
    )
    generated_count = len(generated_records)

    if 2000 <= target_count <= 3000 and not (2000 <= generated_count <= 3000):
        raise ValueError(
            f"Generated record count {generated_count} is outside the required 2000-3000 band"
        )

    generated_path = generator.save_generated(generated_records, output_path=generated_path)

    if generate_only:
        for cp_file in checkpoint_path.glob("checkpoint-*.jsonl"):
            cp_file.unlink(missing_ok=True)
        return {
            "seed_count": len(seeds),
            "generated_count": generated_count,
            "validated_count": 0,
            "split_counts": {},
            "generated_path": str(generated_path),
            "validated_path": None,
            "quality_stats_path": None,
            "manifest_path": None,
            "bulk_provider": bulk_provider,
            "max_parallel_batches": max_parallel_batches,
            "generate_only": True,
        }

    judge = QualityJudge(settings=settings, anthropic_client=anthropic_client)
    validated_records, quality_stats = judge.filter_passed(
        generated_records,
        progress_callback=_stderr_progress,
    )
    if not validated_records:
        raise ValueError("Judge produced zero accepted records")

    validated_path, quality_stats_path = _save_validated_records(
        validated_records,
        quality_stats,
        settings.data_dir,
    )

    builder = DatasetBuilder(version_tag=version_tag)
    build_result = builder.build_splits(input_path=validated_path)

    for cp_file in checkpoint_path.glob("checkpoint-*.jsonl"):
        cp_file.unlink(missing_ok=True)
    if incremental_generated_path.exists() and incremental_generated_path != generated_path:
        incremental_generated_path.unlink()

    return {
        "seed_count": len(seeds),
        "generated_count": generated_count,
        "validated_count": len(validated_records),
        "split_counts": build_result["splits"],
        "generated_path": str(generated_path),
        "validated_path": str(validated_path),
        "quality_stats_path": str(quality_stats_path),
        "manifest_path": build_result["manifest_path"],
        "bulk_provider": bulk_provider,
        "max_parallel_batches": max_parallel_batches,
    }


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.optimize_recovered:
        settings = get_settings()
        try:
            result = optimize_recovered_records(settings.data_dir, target_count=args.target_count)
        except Exception as error:
            print(str(error), file=sys.stderr)
            return 1
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if args.salvage_partial:
        settings = get_settings()
        try:
            result = salvage_partial_records(settings.data_dir)
        except Exception as error:
            print(str(error), file=sys.stderr)
            return 1
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    try:
        summary = run_phase1(
            seed_input=args.seed_input,
            target_count=args.target_count,
            version_tag=args.version_tag,
            max_pages=args.max_pages,
            max_links_per_page=args.max_links_per_page,
            max_seeds=args.max_seeds,
            bulk_provider=args.bulk_provider,
            resume=args.resume,
            max_parallel_batches=args.max_parallel_batches,
            checkpoint_dir=args.checkpoint_dir,
            generate_only=args.generate_only,
        )
    except KeyboardInterrupt:
        print(
            "Interrupted. Completed generation batches were checkpointed. Resume with --resume.",
            file=sys.stderr,
        )
        return 130
    except Exception as error:
        print(str(error), file=sys.stderr)
        return 1

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised via CLI entry point
    raise SystemExit(main())