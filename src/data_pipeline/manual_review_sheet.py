"""Stratified 100-row manual-check review sheet generator (Phase 39).

Consumes judge_merge.py's merged-row output shape directly (no adapter
layer) and produces a single human-fillable Markdown review sheet mixing
judge-pass and judge-fail rows, so a genuine manual check validates the
Codex judge's calls in both directions rather than only checking one side
(see .planning/phases/39-independent-quality-re-judge/39-CONTEXT.md's
"Fixing Flagged Rows & Manual Check" decision).

Sample selection is fully deterministic (via _stable_bucket hashing, never
`random`), so the same input + salt always produces the same sample.

This is a one-time review-sheet-generation script. It has not been run
against a real merged dataset as of this commit -- see
.planning/phases/39-independent-quality-re-judge/39-01-PLAN.md's Handoff
section.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from src.data_pipeline.processing.splitter import _stable_bucket

_DIMENSIONS = (
    "realism",
    "label_correctness",
    "code_switch_naturalness",
    "risk_tier_correctness",
    "suspicious_span_accuracy",
)


def select_stratified_sample(
    merged: list[dict[str, Any]],
    sample_size: int = 100,
    salt: str = "phase39-manual-review-v1",
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Select a deterministic, stratified pass/fail sample from a merged
    dataset.

    Never pads the fail pool past its real size -- a shortfall (fewer fail
    rows than half of sample_size) is filled from the pass pool instead.
    """
    passed = [row for row in merged if row["judge_pass"]]
    failed = [row for row in merged if not row["judge_pass"]]
    source_total = len(merged)

    if source_total <= sample_size:
        sample = list(merged)
    else:
        target_fail = min(len(failed), sample_size // 2)
        target_pass = sample_size - target_fail
        if target_pass > len(passed):
            target_pass = len(passed)
            target_fail = min(len(failed), sample_size - target_pass)

        def _sort_key(row: dict[str, Any]) -> float:
            return _stable_bucket(f"{row['split']}:{row['row_index']}", salt)

        sorted_failed = sorted(failed, key=_sort_key)
        sorted_passed = sorted(passed, key=_sort_key)
        sample = sorted_failed[:target_fail] + sorted_passed[:target_pass]

    sample = sorted(sample, key=lambda row: (row["split"], row["row_index"]))

    pass_count = sum(1 for row in sample if row["judge_pass"])
    fail_count = len(sample) - pass_count
    composition = {
        "sample_size": len(sample),
        "pass_count": pass_count,
        "fail_count": fail_count,
        "source_total": source_total,
        "source_pass_total": len(passed),
        "source_fail_total": len(failed),
    }
    return sample, composition


def _format_spans(spans: list[str]) -> str:
    if not spans:
        return "[]"
    return "[" + ", ".join(spans) + "]"


def _render_example(index: int, total: int, row: dict[str, Any]) -> str:
    verdict_label = "PASS" if row["judge_pass"] else "FAIL"
    scores = ", ".join(f"{dim}={row[dim]}" for dim in _DIMENSIONS)
    lines = [
        f"## Example {index}/{total} -- split={row['split']} row_index={row['row_index']} "
        f"seed_id={row['seed_id']}",
        "",
        f"> {row['text']}",
        "",
        f"- **Label:** {row['label']}",
        f"- **Risk tier:** {row['risk_tier']}",
        f"- **Suspicious spans:** {_format_spans(row.get('suspicious_spans', []))}",
        f"- **XAI explanation:** {row['xai_explanation']}",
        f"- **Codex judge verdict:** {verdict_label} -- {scores}",
        f"- **Judge reason:** {row['judge_reason']}",
        "",
        "**Your verdict:** [ ] PASS   [ ] FAIL",
        "",
        "**Notes:** ",
        "",
        "---",
        "",
    ]
    return "\n".join(lines)


def write_review_sheet(
    sample: list[dict[str, Any]],
    composition: dict[str, Any],
    output_path: Path,
) -> None:
    """Write a human-fillable Markdown review sheet, atomically via
    temp-file-then-.replace()."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    header_lines = [
        "# Phase 39 Manual Quality Review Sheet",
        "",
        f"Sample size: {composition['sample_size']} "
        f"({composition['pass_count']} judge-pass, {composition['fail_count']} judge-fail)",
        f"Source corpus: {composition['source_total']} merged rows "
        f"({composition['source_pass_total']} judge-pass, {composition['source_fail_total']} judge-fail)",
        "",
        "Instructions: for each example below, read the message text and the "
        "Codex judge's verdict, then mark Your verdict as PASS or FAIL based on "
        "your own independent read of whether the row is genuinely realistic "
        "Vietnamese text with a correctly matching label and risk tier -- not "
        "whether you agree with Codex's stated reason. Add any observations in "
        "the blank Notes field.",
        "",
        "---",
        "",
    ]

    total = len(sample)
    body_sections = [
        _render_example(index, total, row) for index, row in enumerate(sample, start=1)
    ]

    content = "\n".join(header_lines) + "\n".join(body_sections)

    temp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    with temp_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(content)
    temp_path.replace(output_path)


def _load_merged(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                rows.append(json.loads(stripped))
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Select a stratified pass/fail sample from judge_merge.py's merged "
            "output and write a human-fillable Markdown manual-check review sheet."
        )
    )
    parser.add_argument(
        "--merged-path", type=Path, default=Path("data/processed/judge-merged.jsonl")
    )
    parser.add_argument("--sample-size", type=int, default=100)
    parser.add_argument("--salt", type=str, default="phase39-manual-review-v1")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            ".planning/phases/39-independent-quality-re-judge/39-manual-review-sheet.md"
        ),
    )
    args = parser.parse_args()

    if not args.merged_path.exists():
        raise FileNotFoundError(
            f"{args.merged_path} does not exist yet. Run judge_merge.py first "
            "(python -m src.data_pipeline.judge_merge), then re-run this tool."
        )

    merged = _load_merged(args.merged_path)
    sample, composition = select_stratified_sample(
        merged, sample_size=args.sample_size, salt=args.salt
    )
    write_review_sheet(sample, composition, args.output)

    print(
        f"Wrote {composition['sample_size']}-row review sheet "
        f"({composition['pass_count']} pass / {composition['fail_count']} fail) "
        f"to {args.output}"
    )


if __name__ == "__main__":
    main()
