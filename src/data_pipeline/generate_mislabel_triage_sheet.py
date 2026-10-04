"""One-off triage-sheet generator for task_scam rows the independent Codex
judge flagged as wrong-class entirely (Phase 39).

Unlike manual_review_sheet.py's stratified pass/fail sample (which checks
whether the JUDGE's calls were right), this covers every row where the
judge's `label_correctness` score was low (<3) for a currently-`task_scam`
row -- i.e. rows where the judge's own stated reason says the text looks
like a different class (e.g. "This is bank impersonation phishing, not a
task scam"). Every candidate is included, not a sample, since this is a
labeling decision that needs a human call per row, not a spot-check.

Reads judge_merge.py's original merged output (data/processed/judge-merged.jsonl,
generated before the zalo_social_engineering narrator-scaffold repair and the
subsequent seed-cap re-enforcement touched data/splits/*.jsonl) and
cross-checks each candidate against the CURRENT live corpus by
(seed_id, text): a handful of candidates were dropped by the later seed-cap
trim and are reported separately as no longer relevant, not as items to
triage.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

_DIMENSIONS = (
    "realism",
    "label_correctness",
    "code_switch_naturalness",
    "risk_tier_correctness",
    "suspicious_span_accuracy",
)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                rows.append(json.loads(stripped))
    return rows


def select_mislabel_candidates(
    merged: list[dict[str, Any]],
    label: str = "task_scam",
    threshold: int = 3,
) -> list[dict[str, Any]]:
    """Every row currently tagged `label` where the judge's
    label_correctness score is below `threshold` -- the judge believes this
    row is actually a different class."""
    return [
        row
        for row in merged
        if row["label"] == label and row["label_correctness"] < threshold
    ]


def partition_by_live_presence(
    candidates: list[dict[str, Any]],
    live_splits_dir: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split candidates into (still present, dropped) by exact
    (seed_id, text) match against the current live split files -- some
    candidates may have been removed by a later, unrelated repair pass
    (e.g. seed-cap re-enforcement) and are no longer actionable."""
    live_keys: set[tuple[str, str]] = set()
    for split_path in Path(live_splits_dir).glob("*.jsonl"):
        for row in _read_jsonl(split_path):
            live_keys.add((row["seed_id"], row["text"]))

    present = [row for row in candidates if (row["seed_id"], row["text"]) in live_keys]
    dropped = [row for row in candidates if (row["seed_id"], row["text"]) not in live_keys]
    return present, dropped


def _format_spans(spans: list[str]) -> str:
    if not spans:
        return "[]"
    return "[" + ", ".join(spans) + "]"


def _format_blockquote(text: str) -> str:
    return "\n".join(f"> {line}" for line in text.splitlines()) or ">"


def _render_candidate(index: int, total: int, row: dict[str, Any]) -> str:
    scores = ", ".join(f"{dim}={row[dim]}" for dim in _DIMENSIONS)
    lines = [
        f"## Candidate {index}/{total} -- split={row['split']} row_index={row['row_index']} "
        f"seed_id={row['seed_id']}",
        "",
        _format_blockquote(row["text"]),
        "",
        f"- **Current label:** {row['label']}",
        f"- **Risk tier:** {row['risk_tier']}",
        f"- **Suspicious spans:** {_format_spans(row.get('suspicious_spans', []))}",
        f"- **Judge scores:** {scores}",
        f"- **Judge's stated reason:** {row['judge_reason']}",
        "",
        "**Decision:** [ ] Keep as task_scam   [ ] Relabel to: __________   [ ] Drop row",
        "",
        "**Notes:** ",
        "",
        "---",
        "",
    ]
    return "\n".join(lines)


def write_triage_sheet(
    present: list[dict[str, Any]],
    dropped: list[dict[str, Any]],
    output_path: Path,
) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    header = [
        "# Phase 39 task_scam Mislabel Triage Sheet",
        "",
        f"Candidates: {len(present)} still in the live corpus "
        f"({len(dropped)} more were flagged by the same judge pass but have since "
        "been removed by an unrelated repair step -- not included below, nothing to do for them).",
        "",
        "Instructions: each candidate below is currently labeled `task_scam`, but the "
        "independent Codex judge scored `label_correctness` below 3/5 -- meaning the "
        "judge believes the text actually reads as a different class (see its stated "
        "reason). For each row, decide: keep the task_scam label if you disagree with "
        "the judge, relabel to the class you believe is correct, or drop the row if "
        "it's neither cleanly task_scam nor any other defined class.",
        "",
        "---",
        "",
    ]

    total = len(present)
    body = [_render_candidate(i, total, row) for i, row in enumerate(present, start=1)]

    content = "\n".join(header) + "\n".join(body)
    temp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    with temp_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(content)
    temp_path.replace(output_path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a manual triage sheet for task_scam rows the independent "
            "Codex judge flagged as mislabeled entirely (label_correctness < 3)."
        )
    )
    parser.add_argument(
        "--merged-path", type=Path, default=Path("data/processed/judge-merged.jsonl")
    )
    parser.add_argument("--live-splits-dir", type=Path, default=Path("data/splits"))
    parser.add_argument("--label", type=str, default="task_scam")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            ".planning/phases/39-independent-quality-re-judge/39-mislabel-triage-sheet.md"
        ),
    )
    args = parser.parse_args()

    if not args.merged_path.exists():
        raise FileNotFoundError(
            f"{args.merged_path} does not exist yet. Run judge_merge.py first."
        )

    merged = _read_jsonl(args.merged_path)
    candidates = select_mislabel_candidates(merged, label=args.label)
    present, dropped = partition_by_live_presence(candidates, args.live_splits_dir)
    write_triage_sheet(present, dropped, args.output)

    print(
        f"{len(candidates)} candidates found, {len(present)} still live "
        f"({len(dropped)} dropped by a later repair), written to {args.output}"
    )


if __name__ == "__main__":
    main()
