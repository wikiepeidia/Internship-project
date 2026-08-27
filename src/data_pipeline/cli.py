"""Thin compatibility CLI for data generation and review workflows."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from src.data_pipeline.core.records import DatasetRecord, SeedRecord


def _add_input_options(parser: argparse.ArgumentParser) -> None:
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


def _add_generation_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--bulk-provider",
        choices=(
            "auto",
            "claude",
            "gemini",
            "openrouter",
            "deepseek",
            "openai-compatible",
        ),
        default="auto",
        help=(
            "Preferred provider for synthetic generation. Use 'openai-compatible' "
            "to target a Colab or local vLLM OpenAI-style endpoint."
        ),
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
        help=(
            "Number of generation batches to run concurrently. Use 1 for sequential, "
            "2-4 for faster retained runs."
        ),
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
        help=(
            "Generate records only and skip all LLM judging, validation outputs, "
            "and split building."
        ),
    )


def _add_workflow_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--judge-existing",
        action="store_true",
        help="Judge and split an existing generated JSONL artifact without regenerating records.",
    )
    parser.add_argument(
        "--generated-input",
        type=Path,
        default=None,
        help=(
            "Existing generated JSONL artifact to judge. Defaults to "
            "data/synthetic/generated.jsonl."
        ),
    )
    parser.add_argument(
        "--salvage-partial",
        action="store_true",
        help=(
            "Merge generated-partial.jsonl into generated.jsonl (de-duplicate by text), "
            "then exit. Does not delete generated-partial.jsonl."
        ),
    )
    parser.add_argument(
        "--optimize-recovered",
        action="store_true",
        help=(
            "Merge recovered JSONL artifacts offline, de-duplicate, rebalance by class, "
            "and emit optimized outputs without API calls."
        ),
    )
    parser.add_argument(
        "--gap-fill-recovered",
        action="store_true",
        help=(
            "Compute missing per-label counts from recovered artifacts and generate only "
            "that remaining gap into dedicated gap-fill outputs."
        ),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m src.data_pipeline.cli",
        description=(
            "Run the Phase 1 scrape -> generate flow, with optional judging and split building."
        ),
    )
    _add_input_options(parser)
    _add_generation_options(parser)
    _add_workflow_options(parser)
    return parser


def get_settings() -> Any:
    from src.config.settings import get_settings as load_settings

    return load_settings()


def TieredGenerator(*args: Any, **kwargs: Any) -> Any:
    from src.data_pipeline.generation.generator import TieredGenerator as implementation

    return implementation(*args, **kwargs)


def QualityJudge(*args: Any, **kwargs: Any) -> Any:
    from src.data_pipeline.generation.quality_judge import QualityJudge as implementation

    return implementation(*args, **kwargs)


def DatasetBuilder(*args: Any, **kwargs: Any) -> Any:
    from src.data_pipeline.versioning.build import DatasetBuilder as implementation

    return implementation(*args, **kwargs)


def NCSCScraper(*args: Any, **kwargs: Any) -> Any:
    from src.data_pipeline.scraper.ncsc_scraper import NCSCScraper as implementation

    return implementation(*args, **kwargs)


def _build_anthropic_client(api_key: str) -> Any | None:
    from src.data_pipeline.workflows import _build_anthropic_client as implementation

    return implementation(api_key)


def _save_validated_records(
    records: list[dict[str, Any]],
    quality_stats: Any,
    data_dir: Path,
) -> tuple[Path, Path]:
    from src.data_pipeline.workflows import _save_validated_records as implementation

    return implementation(records, quality_stats, data_dir)


def _workflow_dependencies() -> Any:
    from src.data_pipeline.workflows import WorkflowDependencies

    return WorkflowDependencies(
        get_settings=get_settings,
        generator_factory=TieredGenerator,
        judge_factory=QualityJudge,
        builder_factory=DatasetBuilder,
        scraper_factory=NCSCScraper,
        anthropic_client_builder=_build_anthropic_client,
        optimize_records=optimize_recovered_records,
    )


def judge_existing_records(
    data_dir: Path,
    input_path: Path,
    version_tag: str = "phase1",
) -> dict[str, Any]:
    from src.data_pipeline.workflows import judge_existing_records as implementation

    return implementation(
        data_dir,
        input_path,
        version_tag,
        _dependencies=_workflow_dependencies(),
    )


def salvage_partial_records(data_dir: Path) -> dict[str, Any]:
    from src.data_pipeline.workflows import salvage_partial_records as implementation

    return implementation(data_dir)


def optimize_recovered_records(
    data_dir: Path,
    target_count: int = 2500,
    lexical_threshold: float = 0.97,
) -> dict[str, Any]:
    from src.data_pipeline.workflows import optimize_recovered_records as implementation

    return implementation(
        data_dir,
        target_count=target_count,
        lexical_threshold=lexical_threshold,
    )


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
    gap_fill_recovered: bool = False,
) -> dict[str, Any]:
    from src.data_pipeline.workflows import build_training_corpus as implementation

    return implementation(
        seed_input=seed_input,
        target_count=target_count,
        version_tag=version_tag,
        max_pages=max_pages,
        max_links_per_page=max_links_per_page,
        max_seeds=max_seeds,
        bulk_provider=bulk_provider,
        resume=resume,
        max_parallel_batches=max_parallel_batches,
        checkpoint_dir=checkpoint_dir,
        generate_only=generate_only,
        gap_fill_recovered=gap_fill_recovered,
        _dependencies=_workflow_dependencies(),
    )


def _print_result(result: dict[str, Any]) -> int:
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    settings = get_settings()
    if args.optimize_recovered:
        try:
            return _print_result(
                optimize_recovered_records(
                    settings.data_dir,
                    target_count=args.target_count,
                )
            )
        except Exception as error:
            print(str(error), file=sys.stderr)
            return 1
    if args.salvage_partial:
        try:
            return _print_result(salvage_partial_records(settings.data_dir))
        except Exception as error:
            print(str(error), file=sys.stderr)
            return 1
    if args.judge_existing:
        generated_input = args.generated_input or (
            settings.data_dir / "synthetic" / "generated.jsonl"
        )
        try:
            return _print_result(
                judge_existing_records(
                    data_dir=settings.data_dir,
                    input_path=generated_input,
                    version_tag=args.version_tag,
                )
            )
        except Exception as error:
            print(str(error), file=sys.stderr)
            return 1
    try:
        return _print_result(
            run_phase1(
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
                gap_fill_recovered=args.gap_fill_recovered,
            )
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


if __name__ == "__main__":  # pragma: no cover - CLI process boundary
    raise SystemExit(main())
