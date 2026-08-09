"""Merge and validate Codex's independent judge-output file against the real
source split files, computing descriptive quality stats (Phase 39).

Codex judges ``data/splits/{train,val,test}.jsonl`` independently, following
``.planning/codex-judge-instructions.md``, and writes one JSON line per row
to ``data/processed/codex-judge-pass.jsonl``. This module joins that output
back to the source rows via ``split`` + ``row_index`` (cross-checked against
``seed_id``), and computes aggregate pass-rate / per-dimension-average
statistics -- never trusting Codex's self-reported ``pass`` blindly (see
``compute_aggregate_stats``'s ``pass_mismatch_count``).

This is a one-time judge-merge script, not a permanent addition to the
generation-time pipeline. It has not been run against real Codex output as
of this commit -- see .planning/phases/39-independent-quality-re-judge/
39-01-PLAN.md's Handoff section.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from src.data_pipeline.schemas import DatasetRecord

_SPLIT_NAMES = ("train", "val", "test")
_SCORE_DIMENSIONS = (
    "realism",
    "label_correctness",
    "code_switch_naturalness",
    "risk_tier_correctness",
    "suspicious_span_accuracy",
)


class CodexJudgeResult(BaseModel):
    """One judge-scored row, matching
    .planning/codex-judge-instructions.md's output schema exactly."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    split: Literal["train", "val", "test"]
    row_index: int = Field(ge=0)
    seed_id: str = Field(min_length=1)
    realism: int = Field(ge=1, le=5)
    label_correctness: int = Field(ge=1, le=5)
    code_switch_naturalness: int = Field(ge=1, le=5)
    risk_tier_correctness: int = Field(ge=1, le=5)
    suspicious_span_accuracy: int = Field(ge=1, le=5)
    judge_pass: bool = Field(alias="pass")
    reason: str = Field(min_length=1)


def load_judge_results(path: Path) -> list[CodexJudgeResult]:
    """Read and validate every line of a Codex judge-output JSONL file.

    Never skips a bad line silently -- any malformed JSON or schema
    violation is re-raised as a ValueError naming the offending 1-based
    line number.
    """
    results: list[CodexJudgeResult] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                row = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"judge-results line {line_number} is not valid JSON: {exc}"
                ) from exc
            try:
                results.append(CodexJudgeResult.model_validate(row))
            except ValidationError as exc:
                raise ValueError(
                    f"judge-results line {line_number} failed schema validation: {exc}"
                ) from exc
    return results


def load_source_splits(splits_dir: Path) -> dict[str, list[dict[str, Any]]]:
    """Read and validate data/splits/{train,val,test}.jsonl.

    Row order within each file is preserved -- this is what a judge result's
    row_index indexes into.
    """
    splits_dir = Path(splits_dir)
    source_splits: dict[str, list[dict[str, Any]]] = {}
    for split_name in _SPLIT_NAMES:
        rows: list[dict[str, Any]] = []
        split_path = splits_dir / f"{split_name}.jsonl"
        if not split_path.exists():
            raise FileNotFoundError(
                f"{split_path} does not exist. Expected all three of "
                f"{splits_dir}/{{train,val,test}}.jsonl -- if the corpus was "
                "moved or renamed, pass the right --splits-dir."
            )
        with split_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                stripped = line.strip()
                if not stripped:
                    continue
                rows.append(DatasetRecord.model_validate(json.loads(stripped)).model_dump())
        source_splits[split_name] = rows
    return source_splits


def merge_judge_results(
    judge_results: list[CodexJudgeResult],
    source_splits: dict[str, list[dict[str, Any]]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Join judge results back to their source rows, failing loudly on any
    coverage gap or seed_id mismatch.

    Returns the full merged list (ordered train rows then val rows then test
    rows, ascending row_index within each) plus a per-split coverage dict.
    """
    by_split: dict[str, dict[int, CodexJudgeResult]] = {name: {} for name in _SPLIT_NAMES}
    duplicate_indices: dict[str, list[int]] = {name: [] for name in _SPLIT_NAMES}
    for result in judge_results:
        existing = by_split[result.split]
        if result.row_index in existing:
            duplicate_indices[result.split].append(result.row_index)
        existing[result.row_index] = result

    coverage: dict[str, dict[str, int]] = {}
    merged: list[dict[str, Any]] = []

    for split_name in _SPLIT_NAMES:
        source_rows = source_splits[split_name]
        expected_indices = set(range(len(source_rows)))
        actual_indices = set(by_split[split_name].keys())
        duplicates = sorted(set(duplicate_indices[split_name]))
        missing = sorted(expected_indices - actual_indices)
        unexpected = sorted(actual_indices - expected_indices)

        if missing or duplicates or unexpected:
            problems = []
            if missing:
                problems.append(
                    f"{len(missing)} missing row_index(es) (first 20: {missing[:20]})"
                )
            if duplicates:
                problems.append(
                    f"{len(duplicates)} duplicate row_index(es) (first 20: {duplicates[:20]}) "
                    "-- if Codex restarted numbering at 0 for each 50-100-row batch instead of "
                    "continuing from the previous batch, this is why: row_index must be the "
                    "0-based line number within the WHOLE split file, not within a batch"
                )
            if unexpected:
                problems.append(
                    f"{len(unexpected)} row_index(es) with no matching source row "
                    f"(first 20: {unexpected[:20]})"
                )
            raise ValueError(
                f"split {split_name!r} judge-results row_index coverage is incomplete "
                f"({len(actual_indices)} judged / {len(expected_indices)} expected): "
                + "; ".join(problems)
            )

        coverage[split_name] = {
            "source_rows": len(source_rows),
            "judge_rows": len(by_split[split_name]),
        }

        seed_mismatches: list[str] = []
        for row_index in sorted(actual_indices):
            result = by_split[split_name][row_index]
            source_row = source_rows[row_index]
            if result.seed_id != source_row["seed_id"]:
                seed_mismatches.append(
                    f"row_index {row_index}: judge seed_id {result.seed_id!r} != "
                    f"source seed_id {source_row['seed_id']!r}"
                )
        if seed_mismatches:
            preview = "; ".join(seed_mismatches[:20])
            more = f" (+{len(seed_mismatches) - 20} more)" if len(seed_mismatches) > 20 else ""
            raise ValueError(
                f"split {split_name!r} has {len(seed_mismatches)} seed_id mismatch(es): "
                f"{preview}{more}"
            )

        for row_index in sorted(actual_indices):
            result = by_split[split_name][row_index]
            source_row = source_rows[row_index]
            scores = {dim: getattr(result, dim) for dim in _SCORE_DIMENSIONS}
            merged.append(
                {
                    **source_row,
                    "split": split_name,
                    "row_index": row_index,
                    **scores,
                    "judge_pass": result.judge_pass,
                    "judge_reason": result.reason,
                    "recomputed_pass": all(score >= 3 for score in scores.values()),
                }
            )

    return merged, coverage


def compute_aggregate_stats(merged: list[dict[str, Any]]) -> dict[str, Any]:
    """Descriptive pass-rate and per-dimension-average stats over a merged
    dataset, guarding every division by max(total, 1)."""
    total = len(merged)
    denom = max(total, 1)
    passed = sum(1 for row in merged if row["judge_pass"])

    stats: dict[str, Any] = {
        "total": total,
        "passed": passed,
        "pass_rate": passed / denom,
    }
    for dim in _SCORE_DIMENSIONS:
        stats[f"avg_{dim}"] = sum(row[dim] for row in merged) / denom

    stats["pass_mismatch_count"] = sum(
        1 for row in merged if row["judge_pass"] != row["recomputed_pass"]
    )

    per_split: dict[str, dict[str, Any]] = {}
    for split_name in _SPLIT_NAMES:
        split_rows = [row for row in merged if row["split"] == split_name]
        split_total = len(split_rows)
        split_denom = max(split_total, 1)
        split_passed = sum(1 for row in split_rows if row["judge_pass"])
        per_split[split_name] = {
            "total": split_total,
            "passed": split_passed,
            "pass_rate": split_passed / split_denom,
        }
    stats["per_split"] = per_split

    return stats


def write_merge_outputs(
    merged: list[dict[str, Any]],
    stats: dict[str, Any],
    merged_path: Path,
    summary_path: Path,
) -> None:
    """Write merged.jsonl and summary.json atomically via temp-file-then-
    .replace(), matching repair_corpus_split_governance.py's convention."""
    merged_path = Path(merged_path)
    summary_path = Path(summary_path)
    merged_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    temp_merged = merged_path.with_suffix(merged_path.suffix + ".tmp")
    with temp_merged.open("w", encoding="utf-8", newline="\n") as handle:
        for record in merged:
            handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
    temp_merged.replace(merged_path)

    temp_summary = summary_path.with_suffix(summary_path.suffix + ".tmp")
    with temp_summary.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(stats, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    temp_summary.replace(summary_path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Merge and validate Codex's independent judge-output file against "
            "the real data/splits/{train,val,test}.jsonl source rows, computing "
            "descriptive quality stats."
        )
    )
    parser.add_argument(
        "--judge-results",
        type=Path,
        default=Path("data/processed/codex-judge-pass.jsonl"),
    )
    parser.add_argument("--splits-dir", type=Path, default=Path("data/splits"))
    parser.add_argument(
        "--output-merged", type=Path, default=Path("data/processed/judge-merged.jsonl")
    )
    parser.add_argument(
        "--output-summary", type=Path, default=Path("data/processed/judge-summary.json")
    )
    args = parser.parse_args()

    if not args.judge_results.exists():
        raise FileNotFoundError(
            f"{args.judge_results} does not exist yet. Run the Codex judge pass "
            "first per .planning/codex-judge-instructions.md (paste that file "
            "into Codex CLI, let it judge all three split files, then re-run "
            "this tool)."
        )

    judge_results = load_judge_results(args.judge_results)
    source_splits = load_source_splits(args.splits_dir)
    merged, coverage = merge_judge_results(judge_results, source_splits)
    stats = compute_aggregate_stats(merged)
    stats["coverage"] = coverage
    write_merge_outputs(merged, stats, args.output_merged, args.output_summary)

    print(f"Merged {stats['total']} rows (pass rate {stats['pass_rate']:.3f})")
    for dim in _SCORE_DIMENSIONS:
        print(f"  avg_{dim}: {stats[f'avg_{dim}']:.3f}")
    print(f"pass_mismatch_count: {stats['pass_mismatch_count']}")
    for split_name in _SPLIT_NAMES:
        split_stats = stats["per_split"][split_name]
        print(
            f"  {split_name}: {split_stats['passed']}/{split_stats['total']} passed "
            f"(rate {split_stats['pass_rate']:.3f})"
        )
    print(f"Merged output written to {args.output_merged}")
    print(f"Summary output written to {args.output_summary}")


if __name__ == "__main__":
    main()
