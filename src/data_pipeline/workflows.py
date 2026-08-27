"""Provider, review, recovery, and generation workflow orchestration."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import sys
from typing import Any, Callable

from src.data_pipeline.core.records import DatasetRecord, SeedRecord
from src.data_pipeline.core.splits import split_dataset
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
def _load_dataset_records(dataset_path: Path) -> list[dict[str, Any]]:
    if not dataset_path.exists():
        raise FileNotFoundError(f"Generated input not found: {dataset_path}")
    records: list[dict[str, Any]] = []
    with dataset_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if stripped := line.strip():
                records.append(
                    DatasetRecord.model_validate_json(stripped).model_dump()
                )
    return records
def judge_existing_records(
    data_dir: Path,
    input_path: Path,
    version_tag: str = "dataset-v1",
    *,
    _dependencies: WorkflowDependencies | None = None,
) -> dict[str, Any]:
    """Judge an existing generated artifact and build validated splits."""

    dependencies = _dependencies or _default_dependencies()
    settings = dependencies.get_settings()
    generated_records = _load_dataset_records(input_path)
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
    validated_path, stats_path = _save_validated_records(
        validated_records,
        quality_stats,
        data_dir,
    )
    build_result = dependencies.builder_factory(version_tag=version_tag).build_splits(
        input_path=validated_path
    )
    return {
        "generated_count": len(generated_records),
        "validated_count": len(validated_records),
        "split_counts": build_result["splits"],
        "generated_path": str(input_path),
        "validated_path": str(validated_path),
        "quality_stats_path": str(stats_path),
        "manifest_path": build_result["manifest_path"],
        "judge_existing": True,
    }
def _count_nonempty_jsonl_lines(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8") as handle:
        return sum(1 for line in handle if line.strip())
def salvage_partial_records(data_dir: Path) -> dict[str, Any]:
    """Merge partial generation output into the primary artifact by text."""

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
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    record = json.loads(stripped)
                except json.JSONDecodeError:
                    continue
                key = record.get("text") or stripped
                if key not in seen_texts:
                    seen_texts.add(key)
                    merged.append(stripped)
    before_generated = _count_nonempty_jsonl_lines(generated_path)
    before_partial = _count_nonempty_jsonl_lines(partial_path)
    tmp_path = generated_path.with_suffix(".tmp")
    generated_path.parent.mkdir(parents=True, exist_ok=True)
    with tmp_path.open("w", encoding="utf-8") as handle:
        handle.writelines(f"{line}\n" for line in merged)
    os.replace(tmp_path, generated_path)
    return {
        "generated_before": before_generated,
        "partial_before": before_partial,
        "merged_unique": len(merged),
        "duplicates_dropped": before_generated + before_partial - len(merged),
        "generated_path": str(generated_path),
        "partial_path_kept": str(partial_path),
    }
def _write_jsonl_records(
    output_path: Path,
    records: list[dict[str, Any]],
) -> Path:
    tmp_path = output_path.with_suffix(".tmp")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tmp_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(DatasetRecord.model_validate(record).model_dump_json() + "\n")
    os.replace(tmp_path, output_path)
    return output_path
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
) -> tuple[list[dict[str, Any]], int, int, dict[str, int]]:
    counts = {label: len(records) for label, records in by_label.items()}
    feasible = min(counts.values()) if counts else 0
    requested = max(target_count // len(THREAT_CLASSES), 0)
    selected_per_class = min(feasible, requested) if requested else feasible
    missing = {
        label: max(requested - counts.get(label, 0), 0)
        for label in THREAT_CLASSES
    }
    balanced: list[dict[str, Any]] = []
    for label in THREAT_CLASSES:
        balanced.extend(_select_seed_diverse_records(by_label[label], selected_per_class))
    return balanced, feasible, selected_per_class, missing
def _write_recovered_outputs(
    data_dir: Path,
    exact_records: list[dict[str, Any]],
    balanced_records: list[dict[str, Any]],
) -> tuple[Path, Path, Path, dict[str, int]]:
    from src.config.settings import get_data_settings

    merged = _write_jsonl_records(
        data_dir / "synthetic" / "recovered-merged.jsonl",
        exact_records,
    )
    balanced = _write_jsonl_records(
        data_dir / "synthetic" / "recovered-balanced.jsonl",
        balanced_records,
    )
    split_dir = data_dir / "splits" / "recovered-balanced"
    split_counts: dict[str, int] = {}
    ratios = get_data_settings().split_ratios
    for split_name, records in split_dataset(
        balanced_records,
        split_ratios=ratios,
    ).items():
        _write_jsonl_records(split_dir / f"{split_name}.jsonl", records)
        split_counts[split_name] = len(records)
    return merged, balanced, split_dir, split_counts
def optimize_recovered_records(
    data_dir: Path,
    target_count: int = 2500,
    lexical_threshold: float = 0.97,
) -> dict[str, Any]:
    """Merge, deduplicate, balance, and split recoverable local artifacts."""

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
    balanced, feasible, selected, missing = _balance_recovered_records(
        by_label,
        target_count,
    )
    merged_path, balanced_path, split_dir, split_counts = _write_recovered_outputs(
        data_dir,
        exact_records,
        balanced,
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
        "missing_by_label_for_target": missing,
        "generation_gap_total": sum(missing.values()),
        "feasible_balanced_per_class": feasible,
        "selected_per_class": selected,
        "balanced_total": len(balanced),
        "balanced_by_label": _count_labels(balanced),
        "merged_output_path": str(merged_path),
        "balanced_output_path": str(balanced_path),
        "split_dir": str(split_dir),
        "split_counts": split_counts,
    }
def _prepare_gap_fill(
    settings: Any,
    target_count: int,
    checkpoint_dir: Path | None,
    gap_fill_recovered: bool,
    dependencies: WorkflowDependencies,
) -> tuple[dict[str, Any] | None, dict[str, int] | None, int, Path]:
    checkpoint_base = checkpoint_dir or (settings.data_dir / "synthetic")
    if not gap_fill_recovered:
        return None, None, target_count, checkpoint_base
    recovered = dependencies.optimize_records(
        settings.data_dir,
        target_count=target_count,
    )
    targets = recovered["missing_by_label_for_target"]
    checkpoint_base = checkpoint_dir or (
        settings.data_dir / "backup" / "recovered-gap-fill" / "checkpoints"
    )
    return recovered, targets, recovered["generation_gap_total"], checkpoint_base
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
    validated_path, stats_path = _save_validated_records(
        validated_records,
        quality_stats,
        settings.data_dir,
    )
    build = dependencies.builder_factory(version_tag=version_tag).build_splits(
        input_path=validated_path
    )
    return {
        "validated_count": len(validated_records),
        "split_counts": build["splits"],
        "generated_path": str(generated_path),
        "validated_path": str(validated_path),
        "quality_stats_path": str(stats_path),
        "manifest_path": build["manifest_path"],
    }
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

    dependencies = _dependencies or _default_dependencies()
    settings = dependencies.get_settings()
    if gap_fill_recovered and not generate_only:
        raise ValueError("--gap-fill-recovered currently requires --generate-only")
    recovered, targets, target_count, checkpoint_base = _prepare_gap_fill(
        settings,
        target_count,
        checkpoint_dir,
        gap_fill_recovered,
        dependencies,
    )
    generated_path = settings.data_dir / "synthetic" / (
        "generated-gap-fill-recovered.jsonl"
        if gap_fill_recovered
        else "generated.jsonl"
    )
    incremental_path = generated_path if generate_only else (
        checkpoint_base / "generated-partial.jsonl"
    )
    if gap_fill_recovered and target_count <= 0:
        return _generate_only_summary(
            [], 0, Path(recovered["merged_output_path"]), bulk_provider,
            max_parallel_batches, recovered, targets,
        )
    if generate_only and resume and not gap_fill_recovered:
        if any(checkpoint_base.glob("checkpoint-*.jsonl")) and generated_path.exists():
            generated_path.unlink()
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
        "checkpoint_path": checkpoint_base,
        "partial_output_path": incremental_path,
        "resume": resume,
        "progress_callback": _stderr_progress,
    }
    if targets is not None:
        generation_kwargs["class_targets"] = targets
    generated_records = generator.generate_dataset(seeds, **generation_kwargs)
    generated_count = len(generated_records)
    if not gap_fill_recovered and 2000 <= target_count <= 3000:
        if not 2000 <= generated_count <= 3000:
            raise ValueError(
                f"Generated record count {generated_count} is outside the required 2000-3000 band"
            )
    if gap_fill_recovered and generate_only and generated_path.exists():
        generated_count = _count_nonempty_jsonl_lines(generated_path)
    else:
        generated_path = generator.save_generated(generated_records, output_path=generated_path)
    if generate_only:
        for checkpoint in checkpoint_base.glob("checkpoint-*.jsonl"):
            checkpoint.unlink(missing_ok=True)
        return _generate_only_summary(
            seeds, generated_count, generated_path, bulk_provider,
            max_parallel_batches, recovered, targets,
        )
    result = _judge_generated_records(
        generated_records, generated_path, settings, version_tag, dependencies
    )
    for checkpoint in checkpoint_base.glob("checkpoint-*.jsonl"):
        checkpoint.unlink(missing_ok=True)
    if incremental_path.exists() and incremental_path != generated_path:
        incremental_path.unlink()
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
