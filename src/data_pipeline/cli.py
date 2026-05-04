"""Operator-facing CLI for the Phase 1 dataset pipeline."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from src.config.settings import get_settings
from src.data_pipeline.generation.generator import TieredGenerator
from src.data_pipeline.generation.quality_judge import QualityJudge
from src.data_pipeline.schemas import DatasetRecord, SeedRecord
from src.data_pipeline.scraper.ncsc_scraper import NCSCScraper
from src.data_pipeline.versioning.build import DatasetBuilder


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m src.data_pipeline.cli",
        description="Run the Phase 1 scrape -> generate -> judge -> build dataset flow.",
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
    return parser


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
    with validated_path.open("w", encoding="utf-8") as handle:
        for record in records:
            validated = DatasetRecord.model_validate(record)
            handle.write(validated.model_dump_json() + "\n")

    stats_path = processed_dir / "quality-stats.json"
    if hasattr(quality_stats, "model_dump_json"):
        stats_path.write_text(quality_stats.model_dump_json(indent=2), encoding="utf-8")
    else:
        stats_path.write_text(json.dumps(quality_stats, ensure_ascii=False, indent=2), encoding="utf-8")

    return validated_path, stats_path


def run_phase1(
    seed_input: Path | None = None,
    target_count: int = 2500,
    version_tag: str = "phase1",
    max_pages: int = 1,
    max_links_per_page: int = 5,
    max_seeds: int | None = None,
) -> dict[str, Any]:
    settings = get_settings()

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
    generator = TieredGenerator(settings=settings, anthropic_client=anthropic_client)
    generated_records = generator.generate_dataset(seeds, target_count=target_count)
    generated_count = len(generated_records)

    if 2000 <= target_count <= 3000 and not (2000 <= generated_count <= 3000):
        raise ValueError(
            f"Generated record count {generated_count} is outside the required 2000-3000 band"
        )

    generated_path = generator.save_generated(generated_records)

    judge = QualityJudge(settings=settings, anthropic_client=anthropic_client)
    validated_records, quality_stats = judge.filter_passed(generated_records)
    if not validated_records:
        raise ValueError("Judge produced zero accepted records")

    validated_path, quality_stats_path = _save_validated_records(
        validated_records,
        quality_stats,
        settings.data_dir,
    )

    builder = DatasetBuilder(version_tag=version_tag)
    build_result = builder.build_splits(input_path=validated_path)

    return {
        "seed_count": len(seeds),
        "generated_count": generated_count,
        "validated_count": len(validated_records),
        "split_counts": build_result["splits"],
        "generated_path": str(generated_path),
        "validated_path": str(validated_path),
        "quality_stats_path": str(quality_stats_path),
        "manifest_path": build_result["manifest_path"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        summary = run_phase1(
            seed_input=args.seed_input,
            target_count=args.target_count,
            version_tag=args.version_tag,
            max_pages=args.max_pages,
            max_links_per_page=args.max_links_per_page,
            max_seeds=args.max_seeds,
        )
    except Exception as error:
        print(str(error), file=sys.stderr)
        return 1

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised via CLI entry point
    raise SystemExit(main())