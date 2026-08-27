"""Provider, review, recovery, and generation workflow orchestration."""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
import sys
from typing import Any, Callable

from src.data_pipeline.core.records import DatasetRecord, SeedRecord
from src.data_pipeline.core.text import RAPIDFUZZ_AVAILABLE, lexical_dedup


THREAT_CLASSES = ("bank_impersonation", "zalo_social_engineering", "task_scam", "benign")
@dataclass(frozen=True, slots=True)
class WorkflowDependencies:
    get_settings: Callable[[], Any]
    generator_factory: Callable[..., Any]
    judge_factory: Callable[..., Any]
    builder_factory: Callable[..., Any]
    scraper_factory: Callable[..., Any]
    anthropic_client_builder: Callable[[str], Any | None]
    optimize_records: Callable[..., dict[str, Any]]
def _default_dependencies() -> WorkflowDependencies:
    from src.config.settings import get_settings
    from src.data_pipeline.generation.generator import TieredGenerator
    from src.data_pipeline.generation.quality_judge import QualityJudge
    from src.data_pipeline.scraper.ncsc_scraper import NCSCScraper
    from src.data_pipeline.versioning.build import DatasetBuilder

    return WorkflowDependencies(
        get_settings=get_settings,
        generator_factory=TieredGenerator,
        judge_factory=QualityJudge,
        builder_factory=DatasetBuilder,
        scraper_factory=NCSCScraper,
        anthropic_client_builder=_build_anthropic_client,
        optimize_records=optimize_recovered_records,
    )
def _stderr_progress(message: str) -> None:
    print(message, file=sys.stderr, flush=True)
def _build_anthropic_client(api_key: str) -> Any | None:
    if not api_key:
        return None
    try:
        import anthropic
    except ImportError as error:  # pragma: no cover - real optional dependency
        raise ValueError(
            "Anthropic SDK is required when ANTHROPIC_API_KEY is configured"
        ) from error
    return anthropic.Anthropic(api_key=api_key)
def _load_seed_records(seed_path: Path) -> list[SeedRecord]:
    if not seed_path.exists():
        raise FileNotFoundError(f"Seed input not found: {seed_path}")
    seeds: list[SeedRecord] = []
    with seed_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if stripped := line.strip():
                seeds.append(SeedRecord.model_validate_json(stripped))
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
        rendered = quality_stats.model_dump_json(indent=2)
    else:
        rendered = json.dumps(quality_stats, ensure_ascii=False, indent=2)
    tmp_stats.write_text(rendered, encoding="utf-8")
    os.replace(tmp_stats, stats_path)
    return validated_path, stats_path
def _load_dataset_records(candidate: Any) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line in candidate.raw.splitlines():
        if stripped := line.strip():
            records.append(DatasetRecord.model_validate_json(stripped).model_dump())
    return records
def judge_existing_records(
    data_dir: Path,
    input_path: Path,
    version_tag: str = "dataset-v1",
    *,
    _dependencies: WorkflowDependencies | None = None,
) -> dict[str, Any]:
    """Judge an existing generated artifact and build validated splits."""

    from src.data_pipeline.generation_runs import resolve_generated_candidate

    dependencies = _dependencies or _default_dependencies()
    settings = dependencies.get_settings()
    candidate = resolve_generated_candidate(data_dir, input_path)
    generated_records = _load_dataset_records(candidate)
    if not generated_records:
        raise ValueError("No generated records found to judge")
    client = dependencies.anthropic_client_builder(settings.anthropic_api_key)
    judge = dependencies.judge_factory(settings=settings, anthropic_client=client)
    validated_records, quality_stats = judge.filter_passed(
        generated_records,
        progress_callback=_stderr_progress,
    )
    if not validated_records:
        raise ValueError("Judge produced zero accepted records")
    from src.data_pipeline.publication import publish_reviewed_dataset

    publication = publish_reviewed_dataset(
        validated_records,
        quality_stats,
        data_dir,
        version_tag,
        dependencies.builder_factory,
    )
    return {
        "generated_count": len(generated_records),
        "validated_count": len(validated_records),
        "split_counts": publication.split_counts,
        "generated_path": str(candidate.path),
        "generated_sha256": candidate.sha256,
        "generation_run_id": candidate.run_id,
        "validated_path": str(publication.validated_path),
        "quality_stats_path": str(publication.quality_stats_path),
        "manifest_path": str(publication.generation_manifest_path),
        "dataset_generation_id": publication.generation_id,
        "dataset_current_pointer": str(publication.current_pointer),
        "judge_existing": True,
    }
def salvage_partial_records(data_dir: Path) -> dict[str, Any]:
    """Validate and atomically salvage generated and partial artifacts."""

    from src.data_pipeline.recovery import salvage_partial_records as implementation

    return implementation(data_dir)
def _count_labels(records: list[dict[str, Any]]) -> dict[str, int]:
    counts = {label: 0 for label in THREAT_CLASSES}
    for record in records:
        if record.get("label") in counts:
            counts[record["label"]] += 1
    return counts
def _select_seed_diverse_records(
    records: list[dict[str, Any]],
    limit: int,
) -> list[dict[str, Any]]:
    if limit <= 0 or not records:
        return []
    grouped: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        grouped.setdefault(record["seed_id"], []).append(record)
    active = sorted(grouped)
    selected: list[dict[str, Any]] = []
    while active and len(selected) < limit:
        next_round: list[str] = []
        for seed_id in active:
            bucket = grouped[seed_id]
            if bucket:
                selected.append(bucket.pop(0))
            if bucket:
                next_round.append(seed_id)
            if len(selected) >= limit:
                break
        active = next_round
    return selected
def _recoverable_record_paths(data_dir: Path) -> list[Path]:
    from src.data_pipeline.recovery import recoverable_record_paths

    return recoverable_record_paths(data_dir)
def _load_recoverable_records(
    data_dir: Path,
    source_paths: list[Path],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, int]], int, int, int]:
    from src.data_pipeline.recovery import load_recoverable_records

    return load_recoverable_records(data_dir, source_paths)
def _deduplicate_recovered_by_label(
    records: list[dict[str, Any]],
    lexical_threshold: float,
) -> tuple[dict[str, list[dict[str, Any]]], bool]:
    apply_lexical = RAPIDFUZZ_AVAILABLE and lexical_threshold < 1.0
    by_label: dict[str, list[dict[str, Any]]] = {}
    for label in THREAT_CLASSES:
        class_records = [record for record in records if record["label"] == label]
        by_label[label] = (
            lexical_dedup(class_records, threshold=lexical_threshold)
            if apply_lexical
            else class_records
        )
    return by_label, apply_lexical
def _balance_recovered_records(
    by_label: dict[str, list[dict[str, Any]]],
    target_count: int,
    *,
    split_ratios: tuple[float, float, float] = (0.8, 0.1, 0.1),
) -> tuple[
    list[dict[str, Any]],
    int,
    int,
    dict[str, int],
    dict[str, int],
    dict[str, int],
]:
    counts = {label: len(records) for label, records in by_label.items()}
    feasible = min(counts.values()) if counts else 0
    quotient, remainder = divmod(target_count, len(THREAT_CLASSES))
    requested_by_label = {
        label: quotient + (index < remainder)
        for index, label in enumerate(THREAT_CLASSES)
    }
    missing = {
        label: max(requested_by_label[label] - counts.get(label, 0), 0)
        for label in THREAT_CLASSES
    }
    balanced: list[dict[str, Any]] = []
    selected_by_label: dict[str, int] = {}
    required_seed_groups = sum(1 for ratio in split_ratios if ratio > 0)
    for label in THREAT_CLASSES:
        requested = requested_by_label[label]
        selected = _select_seed_diverse_records(
            by_label[label], requested
        )
        if requested > 0 and len(selected) < requested:
            raise ValueError(
                f"label {label!r} has {len(selected)} recoverable rows; "
                f"{requested} were requested"
            )
        seed_groups = len({record["seed_id"] for record in selected})
        if requested > 0 and seed_groups < required_seed_groups:
            raise ValueError(
                f"label {label!r} has {seed_groups} seed groups; "
                f"{required_seed_groups} are required for recovery splitting"
            )
        selected_by_label[label] = len(selected)
        balanced.extend(selected)
    return (
        balanced,
        feasible,
        min(selected_by_label.values(), default=0),
        missing,
        requested_by_label,
        selected_by_label,
    )


def _validate_recovery_target_count(target_count: int) -> int:
    if isinstance(target_count, bool) or not isinstance(target_count, int):
        raise ValueError("recovery target_count must be an integer")
    if target_count < 0:
        raise ValueError("recovery target_count must be non-negative")
    if 0 < target_count < len(THREAT_CLASSES) * 3:
        raise ValueError("positive recovery target_count must be at least 12")
    return target_count
def _write_recovered_outputs(
    data_dir: Path,
    exact_records: list[dict[str, Any]],
    balanced_records: list[dict[str, Any]],
) -> dict[str, Any]:
    from src.data_pipeline.recovery import publish_recovered_outputs

    return publish_recovered_outputs(data_dir, exact_records, balanced_records)
def optimize_recovered_records(
    data_dir: Path,
    target_count: int = 2500,
    lexical_threshold: float = 0.97,
) -> dict[str, Any]:
    """Merge, deduplicate, balance, and split recoverable local artifacts."""

    target_count = _validate_recovery_target_count(target_count)
    if (
        isinstance(lexical_threshold, bool)
        or not isinstance(lexical_threshold, (int, float))
        or not math.isfinite(float(lexical_threshold))
        or not 0.0 <= float(lexical_threshold) <= 1.0
    ):
        raise ValueError("recovery lexical_threshold must be a finite value in [0, 1]")
    lexical_threshold = float(lexical_threshold)
    source_paths = _recoverable_record_paths(data_dir)
    if not source_paths:
        raise ValueError("No recoverable JSONL artifacts found under data/.")
    unique, source_stats, loaded, invalid, conflicts = _load_recoverable_records(
        data_dir, source_paths
    )
    exact_records = list(unique.values())
    by_label, lexical_applied = _deduplicate_recovered_by_label(
        exact_records,
        lexical_threshold,
    )
    lexical_counts = {label: len(records) for label, records in by_label.items()}
    (
        balanced,
        feasible,
        selected,
        missing,
        requested_by_label,
        selected_by_label,
    ) = _balance_recovered_records(
        by_label,
        target_count,
    )
    publication = (
        _write_recovered_outputs(data_dir, exact_records, balanced)
        if target_count > 0
        else None
    )
    requested_per_class = max(target_count // len(THREAT_CLASSES), 0)
    return {
        "source_files": sorted(source_stats),
        "source_stats": source_stats,
        "loaded_records": loaded,
        "invalid_items": invalid,
        "text_conflicts": conflicts,
        "exact_unique": len(exact_records),
        "exact_unique_by_label": _count_labels(exact_records),
        "lexical_dedup_applied": lexical_applied,
        "lexical_unique_by_label": lexical_counts,
        "requested_target_count": target_count,
        "requested_per_class": requested_per_class,
        "requested_by_label": requested_by_label,
        "missing_by_label_for_target": missing,
        "generation_gap_total": sum(missing.values()),
        "feasible_balanced_per_class": feasible,
        "selected_per_class": selected,
        "selected_by_label": selected_by_label,
        "balanced_total": len(balanced),
        "balanced_by_label": _count_labels(balanced),
        "publication_status": "published" if publication is not None else "not_requested",
        "recovery_generation_id": publication["generation_id"] if publication else None,
        "recovery_current_pointer": str(publication["current_pointer"]) if publication else None,
        "recovery_manifest_path": str(publication["manifest_path"]) if publication else None,
        "merged_output_path": str(publication["merged_path"]) if publication else None,
        "balanced_output_path": str(publication["balanced_path"]) if publication else None,
        "split_dir": str(publication["split_dir"]) if publication else None,
        "split_counts": publication["split_counts"] if publication else {},
    }
def _prepare_gap_fill(
    settings: Any,
    target_count: int,
    gap_fill_recovered: bool,
    dependencies: WorkflowDependencies,
) -> tuple[dict[str, Any] | None, dict[str, int] | None, int]:
    if not gap_fill_recovered:
        return None, None, target_count
    recovered = dependencies.optimize_records(
        settings.data_dir,
        target_count=target_count,
    )
    targets = recovered["missing_by_label_for_target"]
    return recovered, targets, recovered["generation_gap_total"]
def _load_or_scrape_seeds(
    seed_input: Path | None,
    max_pages: int,
    max_links_per_page: int,
    max_seeds: int | None,
    dependencies: WorkflowDependencies,
) -> list[SeedRecord]:
    if seed_input is not None:
        return _load_seed_records(seed_input)
    scraper = dependencies.scraper_factory()
    seeds = scraper.scrape_advisory_list(
        max_pages=max_pages,
        max_links_per_page=max_links_per_page,
        max_seeds=max_seeds,
    )
    if seeds:
        scraper.save_seeds(seeds)
    return seeds
def _generate_only_summary(
    seeds: list[SeedRecord],
    generated_count: int,
    generated_path: Path,
    bulk_provider: str,
    max_parallel_batches: int,
    recovered: dict[str, Any] | None,
    targets: dict[str, int] | None,
) -> dict[str, Any]:
    summary: dict[str, Any] = {
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
    if recovered is not None:
        summary.update(
            gap_fill_recovered=True,
            gap_fill_missing_by_label=targets,
            recovered_summary=recovered,
        )
    return summary
def _judge_generated_records(
    generated_records: list[dict[str, Any]],
    generated_path: Path,
    settings: Any,
    version_tag: str,
    dependencies: WorkflowDependencies,
) -> dict[str, Any]:
    client = dependencies.anthropic_client_builder(settings.anthropic_api_key)
    judge = dependencies.judge_factory(settings=settings, anthropic_client=client)
    validated_records, quality_stats = judge.filter_passed(
        generated_records,
        progress_callback=_stderr_progress,
    )
    if not validated_records:
        raise ValueError("Judge produced zero accepted records")
    from src.data_pipeline.publication import publish_reviewed_dataset

    publication = publish_reviewed_dataset(
        validated_records,
        quality_stats,
        settings.data_dir,
        version_tag,
        dependencies.builder_factory,
    )
    return {
        "validated_count": len(validated_records),
        "split_counts": publication.split_counts,
        "generated_path": str(generated_path),
        "validated_path": str(publication.validated_path),
        "quality_stats_path": str(publication.quality_stats_path),
        "manifest_path": str(publication.generation_manifest_path),
        "dataset_generation_id": publication.generation_id,
        "dataset_current_pointer": str(publication.current_pointer),
    }


def _generate_owned_candidate(
    generator: Any,
    seeds: list[SeedRecord],
    run: Any,
    generation_kwargs: dict[str, Any],
) -> tuple[list[dict[str, Any]], Path, tuple[Any, ...]]:
    from src.data_pipeline.generation_runs import (
        newly_owned_files,
        snapshot_run_files,
        stage_generated_records,
        write_run_ledger,
    )

    before = snapshot_run_files(run)
    try:
        records = generator.generate_dataset(seeds, **generation_kwargs)
        candidate = stage_generated_records(run, records)
    except BaseException:
        created = newly_owned_files(before, snapshot_run_files(run))
        write_run_ledger(run, created)
        raise
    created = newly_owned_files(before, snapshot_run_files(run))
    write_run_ledger(run, created)
    return records, candidate, created
def build_training_corpus(
    seed_input: Path | None = None,
    target_count: int = 2500,
    version_tag: str = "dataset-v1",
    max_pages: int = 1,
    max_links_per_page: int = 5,
    max_seeds: int | None = None,
    bulk_provider: str = "auto",
    resume: bool = False,
    max_parallel_batches: int = 1,
    checkpoint_dir: Path | None = None,
    generate_only: bool = False,
    gap_fill_recovered: bool = False,
    *,
    _dependencies: WorkflowDependencies | None = None,
) -> dict[str, Any]:
    """Run the retained scrape, generation, review, and build workflow."""

    from src.data_pipeline.generation_runs import (
        cleanup_owned_files,
        prepare_generation_run,
        publish_generated_candidate,
    )

    dependencies = _dependencies or _default_dependencies()
    settings = dependencies.get_settings()
    if gap_fill_recovered and not generate_only:
        raise ValueError("--gap-fill-recovered currently requires --generate-only")
    recovered, targets, target_count = _prepare_gap_fill(
        settings,
        target_count,
        gap_fill_recovered,
        dependencies,
    )
    stable_name = (
        "generated-gap-fill-recovered.jsonl"
        if gap_fill_recovered
        else "generated.jsonl"
    )
    if gap_fill_recovered and target_count <= 0:
        return _generate_only_summary(
            [], 0, Path(recovered["merged_output_path"]), bulk_provider,
            max_parallel_batches, recovered, targets,
        )
    run = prepare_generation_run(
        settings.data_dir,
        version_tag=version_tag,
        checkpoint_dir=checkpoint_dir,
        resume=resume,
    )
    seeds = _load_or_scrape_seeds(
        seed_input, max_pages, max_links_per_page, max_seeds, dependencies
    )
    if not seeds:
        raise ValueError("No seeds available for dataset generation")
    client = dependencies.anthropic_client_builder(settings.anthropic_api_key)
    generator = dependencies.generator_factory(
        settings=settings,
        anthropic_client=client,
        bulk_provider=bulk_provider,
    )
    generation_kwargs: dict[str, Any] = {
        "target_count": target_count,
        "max_parallel_batches": max_parallel_batches,
        "checkpoint_path": run.checkpoints,
        "partial_output_path": run.checkpoints / "generated-partial.jsonl",
        "resume": resume,
        "progress_callback": _stderr_progress,
    }
    if targets is not None:
        generation_kwargs["class_targets"] = targets
    generated_records, candidate, created = _generate_owned_candidate(
        generator, seeds, run, generation_kwargs
    )
    generated_count = len(generated_records)
    if not gap_fill_recovered and 2000 <= target_count <= 3000:
        if not 2000 <= generated_count <= 3000:
            raise ValueError(
                f"Generated record count {generated_count} is outside the required 2000-3000 band"
            )
    if generate_only:
        generated_path = publish_generated_candidate(run, candidate, stable_name)
        cleanup_owned_files(created)
        return _generate_only_summary(
            seeds, generated_count, generated_path, bulk_provider,
            max_parallel_batches, recovered, targets,
        )
    result = _judge_generated_records(
        generated_records, candidate, settings, version_tag, dependencies
    )
    generated_path = publish_generated_candidate(run, candidate, stable_name)
    cleanup_owned_files(created)
    result["generated_path"] = str(generated_path)
    return {
        "seed_count": len(seeds),
        "generated_count": generated_count,
        "bulk_provider": bulk_provider,
        "max_parallel_batches": max_parallel_batches,
        **result,
    }


__all__ = (
    "WorkflowDependencies",
    "build_training_corpus",
    "judge_existing_records",
    "optimize_recovered_records",
    "salvage_partial_records",
)
