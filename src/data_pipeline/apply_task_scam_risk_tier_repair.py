"""Apply Codex's task_scam risk_tier/suspicious_spans repair output to the
live corpus (Phase 39 follow-up to the risk_tier_correctness finding).

Consumes `data/processed/task-scam-risk-tier-repair-targets.jsonl` (the 187
rows the independent judge flagged) and Codex's response,
`data/processed/codex-task-scam-risk-tier-repair.jsonl` (see
`.planning/codex-task-scam-risk-tier-repair-instructions.md`), validates full
coverage and every new suspicious_span against the row's REAL, CURRENT text
(not a cached copy -- the corpus may have shifted again between target
generation and this run), then rewrites `data/splits/{split}.jsonl` in place.

Applies the same fail-closed conventions established by judge_merge.py's
Phase 39 code review: aggregate all coverage/validation problems before
raising (never stop at the first one), truncate long lists in error messages
instead of dumping raw Python lists, and reject unknown risk_tier values
outright rather than silently accepting them.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

_SPLIT_NAMES = ("train", "val", "test")
_VALID_RISK_TIERS = ("benign", "suspicious", "high-risk")


class RiskTierRepairResult(BaseModel):
    """One repaired row, matching
    .planning/codex-task-scam-risk-tier-repair-instructions.md's output
    schema exactly."""

    model_config = ConfigDict(extra="forbid")

    split: Literal["train", "val", "test"]
    row_index: int = Field(ge=0)
    seed_id: str = Field(min_length=1)
    new_risk_tier: Literal["benign", "suspicious", "high-risk"]
    new_suspicious_spans: list[str]
    changed: bool
    notes: str = Field(min_length=1)


def load_targets(path: Path) -> list[dict[str, Any]]:
    """Read the target-row list generated before the Codex handoff."""
    if not Path(path).exists():
        raise FileNotFoundError(f"{path} does not exist")
    targets: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                targets.append(json.loads(stripped))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path} line {line_number} is not valid JSON: {exc}") from exc
    return targets


def load_repair_results(path: Path) -> list[RiskTierRepairResult]:
    """Read and validate Codex's repair-output JSONL file."""
    if not Path(path).exists():
        raise FileNotFoundError(
            f"{path} does not exist yet. Run the Codex repair pass first per "
            ".planning/codex-task-scam-risk-tier-repair-instructions.md, then re-run this tool."
        )
    results: list[RiskTierRepairResult] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                row = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path} line {line_number} is not valid JSON: {exc}") from exc
            try:
                results.append(RiskTierRepairResult.model_validate(row))
            except ValidationError as exc:
                raise ValueError(
                    f"{path} line {line_number} failed schema validation: {exc}"
                ) from exc
    return results


def _summarize(items: list[Any], limit: int = 20) -> str:
    if len(items) <= limit:
        return str(items)
    return f"{items[:limit]} (+{len(items) - limit} more)"


def validate_coverage(
    targets: list[dict[str, Any]],
    results: list[RiskTierRepairResult],
) -> None:
    """Fail closed, aggregating every problem, if results don't exactly
    cover the target set once each."""
    target_keys = {(t["split"], t["row_index"], t["seed_id"]) for t in targets}
    result_keys = [(r.split, r.row_index, r.seed_id) for r in results]
    result_key_set = set(result_keys)

    duplicates = sorted({key for key in result_keys if result_keys.count(key) > 1})
    missing = sorted(target_keys - result_key_set)
    unexpected = sorted(result_key_set - target_keys)

    if missing or duplicates or unexpected:
        problems = []
        if missing:
            problems.append(f"{len(missing)} missing target(s): {_summarize(missing)}")
        if duplicates:
            problems.append(f"{len(duplicates)} duplicate result(s): {_summarize(duplicates)}")
        if unexpected:
            problems.append(f"{len(unexpected)} unexpected result(s): {_summarize(unexpected)}")
        raise ValueError(
            f"repair-output coverage is incomplete ({len(result_key_set)} results / "
            f"{len(target_keys)} targets): " + "; ".join(problems)
        )


def apply_repair(
    results: list[RiskTierRepairResult],
    splits_dir: Path,
) -> dict[str, Any]:
    """Rewrite data/splits/{split}.jsonl with each result's new_risk_tier /
    new_suspicious_spans, validating every span against the row's REAL
    current text first. Fails closed (no files written) if any row fails
    validation, aggregating all problems across the whole result set."""
    splits_dir = Path(splits_dir)
    per_split_rows: dict[str, list[dict[str, Any]]] = {}
    for split_name in _SPLIT_NAMES:
        split_path = splits_dir / f"{split_name}.jsonl"
        if not split_path.exists():
            raise FileNotFoundError(f"{split_path} does not exist")
        rows: list[dict[str, Any]] = []
        with split_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                stripped = line.strip()
                if stripped:
                    rows.append(json.loads(stripped))
        per_split_rows[split_name] = rows

    problems: list[str] = []
    changed_count = 0
    kept_count = 0
    to_high_risk = 0
    from_high_risk = 0

    for result in results:
        rows = per_split_rows[result.split]
        if result.row_index >= len(rows):
            problems.append(
                f"{result.split}:{result.row_index} (seed {result.seed_id}) -- "
                f"row_index out of range (split has {len(rows)} rows)"
            )
            continue
        row = rows[result.row_index]
        if row["seed_id"] != result.seed_id:
            problems.append(
                f"{result.split}:{result.row_index} -- seed_id mismatch: "
                f"repair result says {result.seed_id!r}, live row is {row['seed_id']!r}"
            )
            continue
        bad_spans = [span for span in result.new_suspicious_spans if span not in row["text"]]
        if bad_spans:
            problems.append(
                f"{result.split}:{result.row_index} (seed {result.seed_id}) -- "
                f"{len(bad_spans)} suspicious_span(s) not found in the row's real text: "
                f"{_summarize(bad_spans)}"
            )
            continue

        if result.changed:
            changed_count += 1
            if row["risk_tier"] != "high-risk" and result.new_risk_tier == "high-risk":
                to_high_risk += 1
            if row["risk_tier"] == "high-risk" and result.new_risk_tier != "high-risk":
                from_high_risk += 1
        else:
            kept_count += 1

        row["risk_tier"] = result.new_risk_tier
        row["suspicious_spans"] = result.new_suspicious_spans

    if problems:
        raise ValueError(
            f"{len(problems)} row(s) failed repair validation, refusing to write any file: "
            + "; ".join(problems[:20])
            + (f" (+{len(problems) - 20} more)" if len(problems) > 20 else "")
        )

    for split_name, rows in per_split_rows.items():
        path = splits_dir / f"{split_name}.jsonl"
        temp_path = path.with_suffix(path.suffix + ".tmp")
        with temp_path.open("w", encoding="utf-8", newline="\n") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
        temp_path.replace(path)

    return {
        "rows_changed": changed_count,
        "rows_kept_as_is": kept_count,
        "suspicious_to_high_risk": to_high_risk,
        "high_risk_to_other": from_high_risk,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Apply Codex's task_scam risk_tier/suspicious_spans repair output "
            "to data/splits/{train,val,test}.jsonl."
        )
    )
    parser.add_argument(
        "--targets-path",
        type=Path,
        default=Path("data/processed/task-scam-risk-tier-repair-targets.jsonl"),
    )
    parser.add_argument(
        "--repair-results-path",
        type=Path,
        default=Path("data/processed/codex-task-scam-risk-tier-repair.jsonl"),
    )
    parser.add_argument("--splits-dir", type=Path, default=Path("data/splits"))
    args = parser.parse_args()

    targets = load_targets(args.targets_path)
    results = load_repair_results(args.repair_results_path)
    validate_coverage(targets, results)
    stats = apply_repair(results, args.splits_dir)

    print(
        f"Changed {stats['rows_changed']}, kept as-is {stats['rows_kept_as_is']} "
        f"(suspicious->high-risk: {stats['suspicious_to_high_risk']}, "
        f"high-risk->other: {stats['high_risk_to_other']})"
    )


if __name__ == "__main__":
    main()
