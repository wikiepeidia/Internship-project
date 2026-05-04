"""Operator-facing CLI for the Phase 1 dataset pipeline."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable

from src.config.settings import get_settings
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
        choices=("auto", "claude", "gemini", "openrouter"),
        default="auto",
        help="Preferred provider for bulk synthetic generation. Use 'claude' to keep retained runs on Anthropic.",
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
    bulk_provider: str = "auto",
    resume: bool = False,
    max_parallel_batches: int = 1,
    checkpoint_dir: Path | None = None,
    generate_only: bool = False,
) -> dict[str, Any]:
    settings = get_settings()
    checkpoint_base = checkpoint_dir or (settings.data_dir / "synthetic")
    checkpoint_path = checkpoint_base / ".checkpoint.jsonl"
    generated_path = settings.data_dir / "synthetic" / "generated.jsonl"
    incremental_generated_path = generated_path if generate_only else (checkpoint_base / "generated-partial.jsonl")

    if generate_only and resume and checkpoint_path.exists() and generated_path.exists():
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
        if checkpoint_path.exists():
            checkpoint_path.unlink()
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

    if checkpoint_path.exists():
        checkpoint_path.unlink()
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