"""Manifest-bound manual-check review sheet tooling (Phase 39).

Consumes judge_merge.py's merged-row output shape directly (no adapter
layer) and produces a single human-fillable Markdown review sheet mixing
judge-pass and judge-fail rows, so a genuine manual check validates the
Codex judge's calls in both directions rather than only checking one side
(see .planning/phases/39-independent-quality-re-judge/39-CONTEXT.md's
"Fixing Flagged Rows & Manual Check" decision).

The legacy Plan 39-01 renderer remains available for regression coverage.
The final-snapshot lane binds 100 deterministic rows to the promoted manifest,
per-row record/evidence digests, and judge provenance. It can carry an older
human verdict only for unique exact record+evidence identity, protects all
historical review paths, and validates completion without writing anything.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from src.data_pipeline.processing.splitter import _stable_bucket
from src.data_pipeline.judge_merge import (
    FinalJudgeProvenanceRow,
    dataset_record_digest,
    judge_evidence_digest,
    sha256_path,
    validate_final_release,
)

_DIMENSIONS = (
    "realism",
    "label_correctness",
    "code_switch_naturalness",
    "risk_tier_correctness",
    "suspicious_span_accuracy",
)

FINAL_SAMPLE_SALT = "phase39-final-manual-review-v1"
_FINAL_REVIEW_SCHEMA_VERSION = "phase39-final-manual-review-v1"
_FINAL_LABELS = (
    "bank_impersonation",
    "benign",
    "task_scam",
    "zalo_social_engineering",
)
_FINAL_JUDGE_ORIGINS = (
    "carried_forward_exact_record",
    "fresh_final_delta",
)
_SPLIT_ORDER = {"train": 0, "val": 1, "test": 2}
_FINAL_PHASE_RELATIVE = Path(
    ".planning/phases/39-independent-quality-re-judge"
)
_DEFAULT_FINAL_SHEET = _FINAL_PHASE_RELATIVE / "39-final-manual-review-sheet.md"
_DEFAULT_FINAL_TRIAGE = _FINAL_PHASE_RELATIVE / "FINALtriage.md"
_DEFAULT_HISTORICAL_SHEET = _FINAL_PHASE_RELATIVE / "39-manual-review-sheet.md"
_DEFAULT_HISTORICAL_MERGED = Path(
    "data/backup/pre-phase39-mislabel-triage/processed/judge-merged.jsonl"
)
_PROTECTED_HISTORICAL_NAMES = (
    "39-manual-review-sheet.md",
    "39-mislabel-triage-sheet.md",
    "MISLABEL triage.md",
)

# The user explicitly declared this exact FINALtriage.md revision to be the final
# human authority.  The importer intentionally has no CLI override for either
# digest: a changed decision file or a non-canonical starting sheet must stop.
_LOCKED_FINAL_TRIAGE_SHA256 = (
    "9073d8c6aaacea4f26fd75d3992c7a8b21772526b26a899ac4ebe07ae577684d"
)
_LOCKED_FINAL_SHEET_PREIMPORT_SHA256 = (
    "d49ae229fd22b1df675cb6988aed8b8e93c2570ab8fc8cd86fe3f5beb54150ae"
)
_FINAL_TRIAGE_REQUIRED_CARRIES = {35: "FAIL", 63: "PASS"}
_FINAL_TRIAGE_EXPECTED_COUNTS = {"PASS": 44, "FAIL": 56}


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


def _format_blockquote(text: str) -> str:
    """Render text as a Markdown blockquote, prefixing every line with
    '> ' -- a bare '> {text}' breaks the moment text contains an embedded
    newline (confirmed present in 57/2421 real corpus rows), since anything
    after the first line falls out of the blockquote."""
    return "\n".join(f"> {line}" for line in text.splitlines()) or ">"


def _render_example(index: int, total: int, row: dict[str, Any]) -> str:
    verdict_label = "PASS" if row["judge_pass"] else "FAIL"
    scores = ", ".join(f"{dim}={row[dim]}" for dim in _DIMENSIONS)
    lines = [
        f"## Example {index}/{total} -- split={row['split']} row_index={row['row_index']} "
        f"seed_id={row['seed_id']}",
        "",
        _format_blockquote(row["text"]),
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


_REQUIRED_MERGED_KEYS = (
    "split",
    "row_index",
    "seed_id",
    "text",
    "label",
    "risk_tier",
    "xai_explanation",
    "judge_pass",
    "judge_reason",
    *_DIMENSIONS,
)


def _load_merged(path: Path) -> list[dict[str, Any]]:
    """Read and validate judge_merge.py's merged-row output.

    Fails loudly with the 1-based line number and the missing key(s) rather
    than deferring to a bare KeyError deep inside sheet rendering.
    """
    rows: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                row = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"{path} line {line_number} is not valid JSON: {exc}"
                ) from exc
            missing = [key for key in _REQUIRED_MERGED_KEYS if key not in row]
            if missing:
                raise ValueError(
                    f"{path} line {line_number} is missing required key(s) {missing} "
                    "-- is this really judge_merge.py's merged output, not raw "
                    "split/judge-results input?"
                )
            rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# Promoted-final-snapshot review lane (Plan 39-06)
# ---------------------------------------------------------------------------


def _read_jsonl_objects(path: Path, *, context: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                raw = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"{context} line {line_number} is not valid JSON: {exc}"
                ) from exc
            if not isinstance(raw, dict):
                raise ValueError(
                    f"{context} line {line_number} must be a JSON object"
                )
            rows.append(raw)
    return rows


def _final_coordinate_key(row: Mapping[str, Any]) -> tuple[int, int]:
    try:
        return (_SPLIT_ORDER[str(row["split"])], int(row["row_index"]))
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("final evidence has an invalid split/row_index") from exc


def load_final_evidence(
    merged_path: Path,
    provenance_path: Path,
) -> list[dict[str, Any]]:
    """Load one digest-bound final record/evidence/provenance row per coordinate."""
    merged = _load_merged(Path(merged_path))
    provenance_raw = _read_jsonl_objects(
        Path(provenance_path), context="final judge provenance"
    )
    if len(merged) != len(provenance_raw):
        raise ValueError(
            "final merged/provenance counts differ: "
            f"{len(merged)} != {len(provenance_raw)}"
        )

    final_required = {
        "text",
        "label",
        "risk_tier",
        "suspicious_spans",
        "xai_explanation",
        "source",
        "seed_id",
    }
    evidence: list[dict[str, Any]] = []
    seen_record_digests: set[str] = set()
    coordinate_keys: list[tuple[int, int]] = []
    for ordinal, (row, raw_provenance) in enumerate(
        zip(merged, provenance_raw, strict=True), start=1
    ):
        missing = sorted(final_required - set(row))
        if missing:
            raise ValueError(
                f"final merged row {ordinal} is missing DatasetRecord field(s) {missing}"
            )
        try:
            provenance = FinalJudgeProvenanceRow.model_validate(raw_provenance)
        except Exception as exc:
            raise ValueError(
                f"final judge provenance line {ordinal} is invalid: {exc}"
            ) from exc

        identity = (row["split"], row["row_index"], row["seed_id"])
        provenance_identity = (
            provenance.split,
            provenance.row_index,
            provenance.seed_id,
        )
        if identity != provenance_identity:
            raise ValueError(
                f"final merged/provenance identity differs at ordinal {ordinal}: "
                f"{identity!r} != {provenance_identity!r}"
            )
        record_digest = dataset_record_digest(row)
        evidence_digest = judge_evidence_digest(row)
        recomputed_pass = all(row[dimension] >= 3 for dimension in _DIMENSIONS)
        if not isinstance(row["judge_pass"], bool) or row["judge_pass"] != recomputed_pass:
            raise ValueError(
                f"final merged judge_pass differs from five-score recomputation at {identity!r}"
            )
        if "recomputed_pass" in row and row["recomputed_pass"] != recomputed_pass:
            raise ValueError(
                f"final merged recomputed_pass differs at {identity!r}"
            )
        if provenance.record_digest != record_digest:
            raise ValueError(
                f"final provenance record digest differs at {identity!r}"
            )
        if provenance.evidence_digest != evidence_digest:
            raise ValueError(
                f"final provenance evidence digest differs at {identity!r}"
            )
        if record_digest in seen_record_digests:
            raise ValueError(
                f"final evidence repeats record digest {record_digest}"
            )
        seen_record_digests.add(record_digest)
        coordinate_keys.append(_final_coordinate_key(row))
        evidence.append(
            {
                **row,
                "record_digest": record_digest,
                "evidence_digest": evidence_digest,
                "judge_origin": provenance.verdict_origin,
                "provenance": provenance.model_dump(mode="json"),
            }
        )

    if coordinate_keys != sorted(coordinate_keys):
        raise ValueError("final evidence is not ordered train/val/test by row_index")
    by_split: dict[str, list[int]] = defaultdict(list)
    for row in evidence:
        by_split[row["split"]].append(row["row_index"])
    for split_name, indexes in by_split.items():
        if indexes != list(range(len(indexes))):
            raise ValueError(
                f"final evidence coordinates for {split_name} are not contiguous from zero"
            )
    return evidence


def _stratum_key(row: Mapping[str, Any]) -> tuple[str, str, str]:
    label = str(row["label"])
    status = "pass" if bool(row["judge_pass"]) else "fail"
    origin = str(row["judge_origin"])
    if label not in _FINAL_LABELS:
        raise ValueError(f"unknown final review label {label!r}")
    if origin not in _FINAL_JUDGE_ORIGINS:
        raise ValueError(f"unknown final judge origin {origin!r}")
    return (label, status, origin)


def _axis_counts(rows: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, int]]:
    labels = Counter(str(row["label"]) for row in rows)
    statuses = Counter("pass" if row["judge_pass"] else "fail" for row in rows)
    origins = Counter(str(row["judge_origin"]) for row in rows)
    return {
        "label": dict(sorted(labels.items())),
        "judge_status": dict(sorted(statuses.items())),
        "judge_origin": dict(sorted(origins.items())),
    }


def select_final_stratified_sample(
    evidence: Sequence[dict[str, Any]],
    sample_size: int = 100,
    salt: str = FINAL_SAMPLE_SALT,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Select a deterministic multi-axis final-snapshot review sample.

    Every available label x judge-status x judge-origin stratum receives one
    row when the sample is large enough. Sparse pools are exhausted honestly;
    every next slot goes to the least-represented remaining cross stratum and
    the legacy split:row_index stable bucket breaks ties.
    """
    if sample_size <= 0:
        raise ValueError("sample_size must be positive")
    if not evidence:
        raise ValueError("cannot sample an empty final evidence set")
    digests = [str(row.get("record_digest", "")) for row in evidence]
    if any(not digest for digest in digests):
        raise ValueError("every final evidence row requires record_digest")
    if len(set(digests)) != len(digests):
        raise ValueError("final evidence contains duplicate record digests")

    pools: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in evidence:
        pools[_stratum_key(row)].append(dict(row))
    stratum_keys = sorted(
        pools,
        key=lambda key: (
            _stable_bucket("|".join(key), f"{salt}:strata"),
            key,
        ),
    )
    for key in stratum_keys:
        pools[key].sort(
            key=lambda row: (
                _stable_bucket(
                    f"{row['split']}:{row['row_index']}", salt
                ),
                _SPLIT_ORDER[row["split"]],
                row["row_index"],
                str(row["record_digest"]),
            )
        )

    target_size = min(sample_size, len(evidence))
    selected: list[dict[str, Any]] = []
    positions: Counter[tuple[str, str, str]] = Counter()
    axis_selected = (Counter(), Counter(), Counter())

    def take(key: tuple[str, str, str]) -> None:
        row = pools[key][positions[key]]
        positions[key] += 1
        selected.append(row)
        for axis, value in enumerate(key):
            axis_selected[axis][value] += 1

    while len(selected) < target_size:
        available = [
            key for key in stratum_keys if positions[key] < len(pools[key])
        ]
        if not available:
            raise ValueError("final sampler exhausted pools before reaching target size")
        least_selected = min(positions[key] for key in available)
        underrepresented = [
            key for key in available if positions[key] == least_selected
        ]

        def next_row_key(key: tuple[str, str, str]) -> tuple[Any, ...]:
            row = pools[key][positions[key]]
            return (
                _stable_bucket(f"{row['split']}:{row['row_index']}", salt),
                _SPLIT_ORDER[row["split"]],
                row["row_index"],
                row["record_digest"],
                key,
            )

        take(min(underrepresented, key=next_row_key))

    selected.sort(
        key=lambda row: (
            _SPLIT_ORDER[row["split"]],
            row["row_index"],
            row["record_digest"],
        )
    )
    sample_strata = Counter("|".join(_stratum_key(row)) for row in selected)
    source_strata = Counter("|".join(_stratum_key(row)) for row in evidence)
    all_strata = {
        "|".join((label, status, origin))
        for label in _FINAL_LABELS
        for status in ("fail", "pass")
        for origin in _FINAL_JUDGE_ORIGINS
    }
    composition = {
        "sample_size": len(selected),
        "source_total": len(evidence),
        "sample_axes": _axis_counts(selected),
        "source_axes": _axis_counts(evidence),
        "sample_strata": dict(sorted(sample_strata.items())),
        "source_strata": dict(sorted(source_strata.items())),
        "unavailable_strata": sorted(all_strata - set(source_strata)),
    }
    if len(evidence) >= sample_size and len(selected) != sample_size:
        raise ValueError("final sampler did not produce the requested exact sample size")
    if sample_size >= len(source_strata) and set(sample_strata) != set(source_strata):
        raise ValueError("final sample omitted an available cross-product stratum")
    return selected, composition


_HISTORICAL_SECTION_RE = re.compile(
    r"^## Example (?P<index>\d+)/(?P<total>\d+) -- "
    r"split=(?P<split>train|val|test) row_index=(?P<row_index>\d+) "
    r"seed_id=(?P<seed_id>\S+)\s*$",
    re.MULTILINE,
)
_HISTORICAL_VERDICT_RE = re.compile(
    r"^\*\*Your verdict:\*\*\s*(?P<pass>\[[^\]\r\n]*\])\s*PASS\s+"
    r"(?P<fail>\[[^\]\r\n]*\])\s*FAIL\s*$",
    re.MULTILINE,
)


def _historical_marker_state(marker: str) -> str:
    token = marker[1:-1].strip().casefold()
    if token == "":
        return "blank"
    if token in {"x", "ok"}:
        return "checked"
    return "unknown"


def build_historical_human_carry_index(
    historical_sheet_path: Path,
    historical_merged_rows: Sequence[dict[str, Any]],
) -> tuple[dict[tuple[str, str], dict[str, Any]], dict[str, int]]:
    """Index only unique, exact and unambiguous historical human verdicts."""
    text = Path(historical_sheet_path).read_text(encoding="utf-8")
    matches = list(_HISTORICAL_SECTION_RE.finditer(text))
    if not matches:
        raise ValueError("historical manual sheet contains no recognizable examples")
    expected_indexes = list(range(1, len(matches) + 1))
    actual_indexes = [int(match.group("index")) for match in matches]
    totals = {int(match.group("total")) for match in matches}
    if actual_indexes != expected_indexes or totals != {len(matches)}:
        raise ValueError(
            "historical manual sheet examples are duplicated, missing, or misnumbered"
        )

    historical_by_coordinate: dict[tuple[str, int], dict[str, Any]] = {}
    digest_counts: Counter[str] = Counter()
    for ordinal, row in enumerate(historical_merged_rows, start=1):
        coordinate = (str(row.get("split")), int(row.get("row_index", -1)))
        if coordinate in historical_by_coordinate:
            raise ValueError(
                f"historical merged evidence repeats coordinate {coordinate!r}"
            )
        historical_by_coordinate[coordinate] = row
        digest_counts[dataset_record_digest(row)] += 1

    candidates: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    stats: Counter[str] = Counter()
    stats["sections"] = len(matches)
    for offset, match in enumerate(matches):
        end = matches[offset + 1].start() if offset + 1 < len(matches) else len(text)
        section = text[match.start() : end]
        verdict_matches = list(_HISTORICAL_VERDICT_RE.finditer(section))
        if len(verdict_matches) != 1:
            stats["malformed_verdict"] += 1
            continue
        verdict_match = verdict_matches[0]
        pass_state = _historical_marker_state(verdict_match.group("pass"))
        fail_state = _historical_marker_state(verdict_match.group("fail"))
        if "unknown" in {pass_state, fail_state}:
            stats["unknown_verdict_token"] += 1
            continue
        if (pass_state == "checked") == (fail_state == "checked"):
            if pass_state == "blank":
                stats["blank_verdict"] += 1
            else:
                stats["dual_verdict"] += 1
            continue

        coordinate = (match.group("split"), int(match.group("row_index")))
        historical = historical_by_coordinate.get(coordinate)
        if historical is None:
            raise ValueError(
                f"historical sheet coordinate {coordinate!r} is absent from backup"
            )
        if historical["seed_id"] != match.group("seed_id"):
            raise ValueError(
                f"historical sheet seed differs from backup at {coordinate!r}"
            )
        record_digest = dataset_record_digest(historical)
        if digest_counts[record_digest] != 1:
            stats["ambiguous_record_digest"] += 1
            continue
        evidence_digest = judge_evidence_digest(historical)
        candidates[(record_digest, evidence_digest)].append(
            {
                "human_verdict": "PASS" if pass_state == "checked" else "FAIL",
                "historical_example": int(match.group("index")),
                "historical_split": coordinate[0],
                "historical_row_index": coordinate[1],
                "record_digest": record_digest,
                "evidence_digest": evidence_digest,
            }
        )

    carry_index: dict[tuple[str, str], dict[str, Any]] = {}
    for key, entries in candidates.items():
        if len(entries) == 1:
            carry_index[key] = entries[0]
            stats["valid_unambiguous"] += 1
        else:
            stats["ambiguous_sheet_mapping"] += len(entries)
    stats["carry_index_size"] = len(carry_index)
    return carry_index, dict(sorted(stats.items()))


def annotate_exact_human_carries(
    sample: Sequence[dict[str, Any]],
    carry_index: Mapping[tuple[str, str], Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Attach an old verdict only for the exact record+evidence digest pair."""
    annotated: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in sample:
        record_digest = str(row["record_digest"])
        evidence_digest = str(row["evidence_digest"])
        if record_digest in seen:
            raise ValueError(f"sample repeats record digest {record_digest}")
        seen.add(record_digest)
        carry = carry_index.get((record_digest, evidence_digest))
        if carry is None:
            annotated.append(
                {
                    **row,
                    "human_verdict": None,
                    "human_verdict_origin": "pending_final_human",
                    "historical_human_evidence": None,
                }
            )
        else:
            annotated.append(
                {
                    **row,
                    "human_verdict": carry["human_verdict"],
                    "human_verdict_origin": "carried_forward_exact_evidence",
                    "historical_human_evidence": dict(carry),
                }
            )
    return annotated


def _default_protected_paths(manifest_path: Path) -> dict[str, Path]:
    resolved = Path(manifest_path).resolve()
    if len(resolved.parents) < 3:
        raise ValueError("cannot resolve repository root from manifest path")
    root = resolved.parents[2]
    phase_dir = root / _FINAL_PHASE_RELATIVE
    return {name: phase_dir / name for name in _PROTECTED_HISTORICAL_NAMES}


def _validate_manifest_binding(
    manifest_path: Path,
    merged_path: Path,
    provenance_path: Path,
    historical_merged_path: Path,
    evidence_count: int,
) -> tuple[dict[str, Any], dict[str, str]]:
    try:
        manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"final manifest is invalid: {exc}") from exc
    if not isinstance(manifest, dict):
        raise ValueError("final manifest must be a JSON object")
    release = manifest.get("phase39_final_release")
    if not isinstance(release, dict):
        raise ValueError("manifest lacks phase39_final_release")
    if release.get("schema_version") != "phase39-final-release-v1":
        raise ValueError("manifest final-release schema version differs")
    if release.get("status") != "promoted":
        raise ValueError("manifest final release is not promoted")
    judge_evidence = release.get("judge_evidence")
    if not isinstance(judge_evidence, dict):
        raise ValueError("manifest lacks final judge evidence metadata")
    if judge_evidence.get("total_records") != evidence_count:
        raise ValueError("manifest final judge total differs from loaded evidence")
    artifacts = judge_evidence.get("artifacts")
    if not isinstance(artifacts, dict):
        raise ValueError("manifest lacks final judge artifact bindings")
    for key, path in (
        ("judge_merged", Path(merged_path)),
        ("judge_provenance", Path(provenance_path)),
    ):
        entry = artifacts.get(key)
        if not isinstance(entry, dict):
            raise ValueError(f"manifest lacks {key} binding")
        if entry.get("sha256") != sha256_path(path):
            raise ValueError(f"manifest {key} SHA-256 differs from live evidence")
        if entry.get("records") != evidence_count:
            raise ValueError(f"manifest {key} record count differs")
    backup = release.get("historical_judge_backup", {}).get("judge-merged.jsonl")
    if not isinstance(backup, dict):
        raise ValueError("manifest lacks historical merged judge backup binding")
    if backup.get("sha256") != sha256_path(Path(historical_merged_path)):
        raise ValueError("historical merged judge backup SHA-256 differs")
    protected = release.get("protected_human_artifacts")
    if not isinstance(protected, dict):
        raise ValueError("manifest lacks protected historical human artifact hashes")
    expected_protected: dict[str, str] = {}
    for name in _PROTECTED_HISTORICAL_NAMES:
        digest = protected.get(name)
        if not isinstance(digest, str) or len(digest) != 64:
            raise ValueError(f"manifest lacks protected hash for {name}")
        expected_protected[name] = digest
    return manifest, expected_protected


def _verify_protected_paths(
    protected_paths: Mapping[str, Path],
    expected_hashes: Mapping[str, str],
) -> dict[str, str]:
    if set(protected_paths) != set(_PROTECTED_HISTORICAL_NAMES):
        raise ValueError(
            "protected path mapping must contain exactly the three historical artifacts"
        )
    actual: dict[str, str] = {}
    for name in _PROTECTED_HISTORICAL_NAMES:
        path = Path(protected_paths[name])
        if not path.is_file():
            raise ValueError(f"protected historical artifact is missing: {path}")
        digest = sha256_path(path)
        if digest != expected_hashes[name]:
            raise ValueError(f"protected historical artifact changed: {name}")
        actual[name] = digest
    return actual


def _canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(
        dict(payload), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def _ordered_digest_sha256(items: Sequence[Mapping[str, Any]]) -> str:
    payload = _canonical_json(
        {"record_digests": [str(item["record_digest"]) for item in items]}
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _build_final_metadata(
    *,
    items: Sequence[Mapping[str, Any]],
    composition: Mapping[str, Any],
    manifest_path: Path,
    merged_path: Path,
    provenance_path: Path,
    historical_sheet_path: Path,
    historical_merged_path: Path,
    protected_hashes: Mapping[str, str],
    historical_parse_stats: Mapping[str, int],
    salt: str,
) -> dict[str, Any]:
    carried_count = sum(
        item["human_verdict_origin"] == "carried_forward_exact_evidence"
        for item in items
    )
    return {
        "schema_version": _FINAL_REVIEW_SCHEMA_VERSION,
        "sample_salt": salt,
        "sample_size": len(items),
        "carried_count": carried_count,
        "pending_count": len(items) - carried_count,
        "manifest_sha256": sha256_path(Path(manifest_path)),
        "merged_sha256": sha256_path(Path(merged_path)),
        "provenance_sha256": sha256_path(Path(provenance_path)),
        "historical_sheet_sha256": sha256_path(Path(historical_sheet_path)),
        "historical_merged_sha256": sha256_path(Path(historical_merged_path)),
        "ordered_sample_digest_sha256": _ordered_digest_sha256(items),
        "protected_historical_sha256": dict(sorted(protected_hashes.items())),
        "historical_parse_stats": dict(sorted(historical_parse_stats.items())),
        "composition": dict(composition),
    }


def _render_final_prefix(index: int, total: int, item: Mapping[str, Any]) -> str:
    verdict_label = "PASS" if item["judge_pass"] else "FAIL"
    scores = ", ".join(f"{dimension}={item[dimension]}" for dimension in _DIMENSIONS)
    provenance = item["provenance"]
    historical = item["historical_human_evidence"]
    historical_line = "none (fresh human verdict required)"
    if historical is not None:
        historical_line = (
            f"Example {historical['historical_example']} at "
            f"{historical['historical_split']}:{historical['historical_row_index']}"
        )
    lines = [
        f"## Final Example {index:03d}/{total:03d}",
        "",
        "<!-- BEGIN PHASE39 IMMUTABLE FINAL EVIDENCE -->",
        f"- **Current coordinate:** split={item['split']} row_index={item['row_index']}",
        f"- **Record digest:** `{item['record_digest']}`",
        f"- **Evidence digest:** `{item['evidence_digest']}`",
        f"- **Judge origin:** `{item['judge_origin']}`",
        f"- **Judge provenance source:** `{provenance['source_path']}` "
        f"(SHA-256 `{provenance['source_sha256']}`)",
        "- **Judge provenance iteration:** "
        + (
            "historical exact carry"
            if provenance["source_iteration"] is None
            else str(provenance["source_iteration"])
        ),
        "- **Historical judge coordinate:** "
        + (
            f"{provenance['historical_split']}:{provenance['historical_row_index']}"
            if provenance["historical_split"] is not None
            else "none (fresh final-delta judgment)"
        ),
        f"- **Human verdict origin:** `human_verdict_origin={item['human_verdict_origin']}`",
        f"- **Historical human evidence:** {historical_line}",
        "",
        "### Message text",
        "",
        _format_blockquote(item["text"]),
        "",
        f"- **Label:** `{item['label']}`",
        f"- **Risk tier:** `{item['risk_tier']}`",
        "- **Suspicious spans (JSON):** "
        + json.dumps(item["suspicious_spans"], ensure_ascii=False),
        f"- **Source:** `{item['source']}`",
        f"- **Seed ID:** `{item['seed_id']}`",
        "",
        "### XAI explanation",
        "",
        _format_blockquote(item["xai_explanation"]),
        "",
        f"- **Codex judge verdict:** {verdict_label} -- {scores}",
        "- **Judge reason:**",
        "",
        _format_blockquote(item["judge_reason"]),
        "<!-- END PHASE39 IMMUTABLE FINAL EVIDENCE -->",
        "",
    ]
    return "\n".join(lines)


def _render_final_sheet(
    items: Sequence[Mapping[str, Any]], metadata: Mapping[str, Any]
) -> str:
    header_text = _render_final_header(metadata)
    total = len(items)
    sections: list[str] = []
    for index, item in enumerate(items, start=1):
        verdict = item["human_verdict"]
        pass_marker = "x" if verdict == "PASS" else " "
        fail_marker = "x" if verdict == "FAIL" else " "
        sections.append(
            _render_final_prefix(index, total, item)
            + "<!-- BEGIN PHASE39 HUMAN REVIEW -->\n"
            + f"**Your verdict:** [{pass_marker}] PASS   [{fail_marker}] FAIL\n\n"
            + "**Notes:** \n"
            + "<!-- END PHASE39 HUMAN REVIEW -->\n\n"
            + "---\n\n"
        )
    return header_text + "".join(sections)


def _render_final_header(metadata: Mapping[str, Any]) -> str:
    header = [
        "# Phase 39 Final-Snapshot Manual Quality Review",
        "",
        f"<!-- phase39-final-review-meta:{_canonical_json(metadata)} -->",
        "",
        f"- **Final manifest SHA-256:** `{metadata['manifest_sha256']}`",
        f"- **Sample:** {metadata['sample_size']} rows using `{metadata['sample_salt']}`",
        f"- **Exact prior-human carries:** {metadata['carried_count']}",
        f"- **Pending final-human decisions:** {metadata['pending_count']}",
        "- **Unavailable cross-strata:** "
        + (
            ", ".join(metadata["composition"]["unavailable_strata"])
            if metadata["composition"]["unavailable_strata"]
            else "none"
        ),
        "",
        "This sheet is bound to the promoted final corpus and complete judge bundle. "
        "For every row with `human_verdict_origin=pending_final_human`, read the "
        "message, label, risk tier, literal spans, XAI explanation, and Codex evidence. "
        "Replace exactly one `[ ]` with `[x]`. Add a short note for each FAIL. "
        "Do not edit any hash, evidence field, heading, marker, or carried verdict.",
        "",
        "There are four labels: `bank_impersonation`, `benign`, `task_scam`, "
        "and `zalo_social_engineering`. Risk tier is a separate three-value field: "
        "`benign`, `suspicious`, or `high-risk`.",
        "",
        "---",
        "",
    ]
    return "\n".join(header)


_FINAL_META_RE = re.compile(
    r"^<!-- phase39-final-review-meta:(?P<json>\{.*\}) -->$", re.MULTILINE
)
_FINAL_SECTION_RE = re.compile(
    r"^## Final Example (?P<index>\d+)/(?P<total>\d+)\s*$", re.MULTILINE
)
_FINAL_HUMAN_MARKER_RE = re.compile(
    r"^<!-- BEGIN PHASE39 HUMAN REVIEW -->\s*$", re.MULTILINE
)
_FINAL_HUMAN_BLOCK_RE = re.compile(
    r"\A<!-- BEGIN PHASE39 HUMAN REVIEW -->\r?\n"
    r"\*\*Your verdict:\*\*\s*(?P<pass>\[[^\]\r\n]*\])\s*PASS\s+"
    r"(?P<fail>\[[^\]\r\n]*\])\s*FAIL\r?\n\r?\n"
    r"\*\*Notes:\*\* ?(?P<notes>[^\r\n]*)\r?\n"
    r"<!-- END PHASE39 HUMAN REVIEW -->\r?\n\r?\n"
    r"---\r?\n\r?\n?\Z"
)


def _final_marker_state(marker: str) -> str:
    token = marker[1:-1].strip().casefold()
    if token == "":
        return "blank"
    if token == "x":
        return "checked"
    raise ValueError(f"unknown final verdict token {marker!r}; use only [x] or [ ]")


def _prepare_expected_final_review(
    *,
    merged_path: Path,
    provenance_path: Path,
    manifest_path: Path,
    historical_sheet_path: Path,
    historical_merged_path: Path,
    protected_paths: Mapping[str, Path],
    sample_size: int,
    salt: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    evidence = load_final_evidence(merged_path, provenance_path)
    _, expected_protected = _validate_manifest_binding(
        manifest_path,
        merged_path,
        provenance_path,
        historical_merged_path,
        len(evidence),
    )
    protected_hashes = _verify_protected_paths(protected_paths, expected_protected)
    protected_manual = Path(protected_paths["39-manual-review-sheet.md"])
    if Path(historical_sheet_path).resolve() != protected_manual.resolve():
        raise ValueError(
            "historical_sheet_path must be the manifest-protected manual sheet"
        )
    if sha256_path(Path(historical_sheet_path)) != expected_protected[
        "39-manual-review-sheet.md"
    ]:
        raise ValueError("historical manual sheet differs from its protected hash")
    if len(evidence) < sample_size:
        raise ValueError(
            f"final evidence has only {len(evidence)} rows; {sample_size} are required"
        )
    historical_rows = _load_merged(Path(historical_merged_path))
    carry_index, historical_stats = build_historical_human_carry_index(
        historical_sheet_path, historical_rows
    )
    sample, composition = select_final_stratified_sample(
        evidence, sample_size=sample_size, salt=salt
    )
    items = annotate_exact_human_carries(sample, carry_index)
    metadata = _build_final_metadata(
        items=items,
        composition=composition,
        manifest_path=manifest_path,
        merged_path=merged_path,
        provenance_path=provenance_path,
        historical_sheet_path=historical_sheet_path,
        historical_merged_path=historical_merged_path,
        protected_hashes=protected_hashes,
        historical_parse_stats=historical_stats,
        salt=salt,
    )
    return items, metadata


def generate_final_review_sheet(
    *,
    merged_path: Path,
    provenance_path: Path,
    manifest_path: Path,
    historical_sheet_path: Path,
    historical_merged_path: Path,
    output_path: Path,
    protected_paths: Mapping[str, Path] | None = None,
    sample_size: int = 100,
    salt: str = FINAL_SAMPLE_SALT,
) -> dict[str, Any]:
    """Generate the immutable-evidence final review sheet without overwriting history."""
    manifest_path = Path(manifest_path)
    protected = (
        dict(protected_paths)
        if protected_paths is not None
        else _default_protected_paths(manifest_path)
    )
    output_path = Path(output_path)
    protected_resolved = {Path(path).resolve() for path in protected.values()}
    if output_path.resolve() in protected_resolved:
        raise ValueError("final review output may not overwrite a historical artifact")

    items, metadata = _prepare_expected_final_review(
        merged_path=Path(merged_path),
        provenance_path=Path(provenance_path),
        manifest_path=manifest_path,
        historical_sheet_path=Path(historical_sheet_path),
        historical_merged_path=Path(historical_merged_path),
        protected_paths=protected,
        sample_size=sample_size,
        salt=salt,
    )
    before_hashes = dict(metadata["protected_historical_sha256"])
    content = _render_final_sheet(items, metadata)
    encoded = content.encode("utf-8")
    validation_report: dict[str, Any]
    if output_path.exists():
        if output_path.read_bytes() != encoded:
            raise ValueError(
                "refusing to overwrite an existing final review sheet with different bytes"
            )
        validation_report = validate_final_review_sheet(
            sheet_path=output_path,
            merged_path=Path(merged_path),
            provenance_path=Path(provenance_path),
            manifest_path=manifest_path,
            historical_sheet_path=Path(historical_sheet_path),
            historical_merged_path=Path(historical_merged_path),
            protected_paths=protected,
            allow_pending=True,
        )
    else:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = output_path.with_suffix(output_path.suffix + ".tmp")
        try:
            with temp_path.open("wb") as handle:
                handle.write(encoded)
            validation_report = validate_final_review_sheet(
                sheet_path=temp_path,
                merged_path=Path(merged_path),
                provenance_path=Path(provenance_path),
                manifest_path=manifest_path,
                historical_sheet_path=Path(historical_sheet_path),
                historical_merged_path=Path(historical_merged_path),
                protected_paths=protected,
                allow_pending=True,
            )
            temp_path.replace(output_path)
        except Exception:
            if temp_path.exists():
                temp_path.unlink()
            raise
    after_hashes = _verify_protected_paths(protected, before_hashes)
    if after_hashes != before_hashes:
        raise ValueError("protected historical hashes changed during final-sheet generation")
    if output_path.read_bytes() != encoded:
        raise ValueError("final review output differs after atomic promotion")
    return validation_report


def validate_final_review_sheet(
    *,
    sheet_path: Path,
    merged_path: Path,
    provenance_path: Path,
    manifest_path: Path,
    historical_sheet_path: Path,
    historical_merged_path: Path,
    protected_paths: Mapping[str, Path] | None = None,
    allow_pending: bool = False,
    require_complete: bool = False,
) -> dict[str, Any]:
    """Strict, read-only validation of a pending or completed final review sheet."""
    if allow_pending == require_complete:
        raise ValueError("select exactly one validation mode: allow_pending/require_complete")
    manifest_path = Path(manifest_path)
    protected = (
        dict(protected_paths)
        if protected_paths is not None
        else _default_protected_paths(manifest_path)
    )
    text = Path(sheet_path).read_text(encoding="utf-8")
    meta_matches = list(_FINAL_META_RE.finditer(text))
    if len(meta_matches) != 1:
        raise ValueError("final review sheet must contain exactly one metadata record")
    try:
        actual_metadata = json.loads(meta_matches[0].group("json"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"final review metadata is invalid JSON: {exc}") from exc
    if not isinstance(actual_metadata, dict):
        raise ValueError("final review metadata must be an object")
    if actual_metadata.get("schema_version") != _FINAL_REVIEW_SCHEMA_VERSION:
        raise ValueError("final review schema version differs")
    if actual_metadata.get("sample_size") != 100:
        raise ValueError("final review must be bound to exactly 100 examples")
    if actual_metadata.get("sample_salt") != FINAL_SAMPLE_SALT:
        raise ValueError("final review uses an unexpected sampling salt")

    items, expected_metadata = _prepare_expected_final_review(
        merged_path=Path(merged_path),
        provenance_path=Path(provenance_path),
        manifest_path=manifest_path,
        historical_sheet_path=Path(historical_sheet_path),
        historical_merged_path=Path(historical_merged_path),
        protected_paths=protected,
        sample_size=100,
        salt=FINAL_SAMPLE_SALT,
    )
    if actual_metadata != expected_metadata:
        raise ValueError("final review metadata differs from current evidence/manifest")

    matches = list(_FINAL_SECTION_RE.finditer(text))
    if len(matches) != 100:
        raise ValueError(
            f"final review must contain exactly 100 sections, found {len(matches)}"
        )
    indexes = [int(match.group("index")) for match in matches]
    totals = {int(match.group("total")) for match in matches}
    if indexes != list(range(1, 101)) or totals != {100}:
        raise ValueError("final review sections are missing, duplicated, or misnumbered")
    if text[: matches[0].start()] != _render_final_header(expected_metadata):
        raise ValueError("final review header/instructions changed")

    completed_count = 0
    pending_count = 0
    carried_count = 0
    seen_digests: set[str] = set()
    for offset, (match, item) in enumerate(zip(matches, items, strict=True)):
        end = matches[offset + 1].start() if offset + 1 < len(matches) else len(text)
        section = text[match.start() : end]
        human_markers = list(_FINAL_HUMAN_MARKER_RE.finditer(section))
        if len(human_markers) != 1:
            raise ValueError(
                f"Final Example {offset + 1} has a missing/duplicate human-review marker"
            )
        actual_prefix = section[: human_markers[0].start()]
        expected_prefix = _render_final_prefix(offset + 1, 100, item)
        if actual_prefix != expected_prefix:
            raise ValueError(
                f"Final Example {offset + 1} immutable record/judge evidence changed"
            )
        record_digest = str(item["record_digest"])
        if record_digest in seen_digests:
            raise ValueError(f"final review repeats record digest {record_digest}")
        seen_digests.add(record_digest)
        human_block = section[human_markers[0].start() :]
        human_match = _FINAL_HUMAN_BLOCK_RE.fullmatch(human_block)
        if human_match is None:
            raise ValueError(
                f"Final Example {offset + 1} has a malformed verdict/notes/suffix block"
            )
        pass_state = _final_marker_state(human_match.group("pass"))
        fail_state = _final_marker_state(human_match.group("fail"))
        notes = human_match.group("notes").strip()
        if pass_state == "checked" and fail_state == "checked":
            raise ValueError(f"Final Example {offset + 1} has a dual verdict")
        actual_verdict: str | None
        if pass_state == "checked":
            actual_verdict = "PASS"
        elif fail_state == "checked":
            actual_verdict = "FAIL"
        else:
            actual_verdict = None

        if item["human_verdict_origin"] == "carried_forward_exact_evidence":
            carried_count += 1
            if actual_verdict != item["human_verdict"]:
                raise ValueError(
                    f"Final Example {offset + 1} altered or blanked an exact carried verdict"
                )
            if notes:
                raise ValueError(
                    f"Final Example {offset + 1} altered a carried row's notes"
                )
            completed_count += 1
        elif actual_verdict is None:
            if notes:
                raise ValueError(
                    f"Final Example {offset + 1} has notes without a human verdict"
                )
            pending_count += 1
        else:
            if allow_pending:
                raise ValueError(
                    f"Final Example {offset + 1} must remain blank in pending mode"
                )
            if actual_verdict == "FAIL" and not notes:
                raise ValueError(
                    f"Final Example {offset + 1} requires a short note for FAIL"
                )
            completed_count += 1

    if len(seen_digests) != 100:
        raise ValueError("final review does not contain 100 unique identities")
    sample_axes = expected_metadata["composition"]["sample_axes"]
    if set(sample_axes["label"]) != set(_FINAL_LABELS):
        raise ValueError("final review does not cover all four labels")
    if set(sample_axes["judge_status"]) != {"pass", "fail"}:
        raise ValueError("final review does not cover judge PASS and FAIL")
    if set(sample_axes["judge_origin"]) != set(_FINAL_JUDGE_ORIGINS):
        raise ValueError("final review does not cover both available judge origins")
    if require_complete and pending_count:
        raise ValueError(
            f"final review still has {pending_count} pending human verdict(s)"
        )
    return {
        "schema_version": _FINAL_REVIEW_SCHEMA_VERSION,
        "sample_size": 100,
        "carried_count": carried_count,
        "completed_count": completed_count,
        "pending_count": pending_count,
        "manifest_sha256": expected_metadata["manifest_sha256"],
        "merged_sha256": expected_metadata["merged_sha256"],
        "provenance_sha256": expected_metadata["provenance_sha256"],
        "ordered_sample_digest_sha256": expected_metadata[
            "ordered_sample_digest_sha256"
        ],
        "sample_axes": sample_axes,
        "check_only": True,
    }


_FINAL_TRIAGE_DECISION_RE = re.compile(
    r"^.*?\bFinal Example\s+(?P<index>\d{3})/(?P<total>\d{3})\b"
    r"[^\r\n]*?\b(?P<verdict>PASS|FAIL)\b(?P<note>[^\r\n]*)\r?$",
    re.IGNORECASE | re.MULTILINE,
)
_FINAL_HUMAN_END_MARKER = "<!-- END PHASE39 HUMAN REVIEW -->"


def parse_final_triage_decisions(text: str) -> list[dict[str, Any]]:
    """Parse the locked human triage without interpreting repair suggestions."""
    occurrences = re.findall(r"\bFinal Example\b", text, flags=re.IGNORECASE)
    matches = list(_FINAL_TRIAGE_DECISION_RE.finditer(text))
    if len(occurrences) != 100 or len(matches) != 100:
        raise ValueError(
            "FINALtriage must contain exactly 100 parseable Final Example decisions"
        )

    decisions: list[dict[str, Any]] = []
    for match in matches:
        verdict = match.group("verdict").upper()
        raw_note = re.sub(r"\s+", " ", match.group("note")).strip()
        raw_note = re.sub(r"^[\s*_`,:;.\-–—]+", "", raw_note)
        raw_note = raw_note.replace("**", "").strip()
        note = ""
        if verdict == "FAIL":
            note = (
                f"Final triage: {raw_note}"
                if raw_note
                else "Final triage decision: FAIL."
            )
        decisions.append(
            {
                "index": int(match.group("index")),
                "total": int(match.group("total")),
                "verdict": verdict,
                "note": note,
            }
        )

    indexes = [decision["index"] for decision in decisions]
    if indexes != list(range(1, 101)) or {d["total"] for d in decisions} != {100}:
        raise ValueError(
            "FINALtriage decisions must be unique and ordered exactly 001/100..100/100"
        )
    counts = Counter(decision["verdict"] for decision in decisions)
    if dict(counts) != _FINAL_TRIAGE_EXPECTED_COUNTS:
        raise ValueError(
            "FINALtriage verdict totals differ from the locked 44 PASS / 56 FAIL decision"
        )
    return decisions


def _final_human_regions(text: str) -> list[dict[str, Any]]:
    """Return verdict state and exact mutable spans for all final-sheet sections."""
    sections = list(_FINAL_SECTION_RE.finditer(text))
    if len(sections) != 100:
        raise ValueError("final review sheet must contain exactly 100 sections")
    regions: list[dict[str, Any]] = []
    for offset, section_match in enumerate(sections):
        section_end = (
            sections[offset + 1].start() if offset + 1 < len(sections) else len(text)
        )
        section = text[section_match.start() : section_end]
        markers = list(_FINAL_HUMAN_MARKER_RE.finditer(section))
        if len(markers) != 1:
            raise ValueError(
                f"Final Example {offset + 1} has a missing/duplicate human-review marker"
            )
        human_match = _FINAL_HUMAN_BLOCK_RE.fullmatch(section[markers[0].start() :])
        if human_match is None:
            raise ValueError(
                f"Final Example {offset + 1} has a malformed verdict/notes/suffix block"
            )
        pass_state = _final_marker_state(human_match.group("pass"))
        fail_state = _final_marker_state(human_match.group("fail"))
        if pass_state == "checked" and fail_state == "checked":
            raise ValueError(f"Final Example {offset + 1} has a dual verdict")
        verdict = (
            "PASS"
            if pass_state == "checked"
            else "FAIL"
            if fail_state == "checked"
            else None
        )
        region_start = section_match.start() + markers[0].start()
        end_relative = section.index(_FINAL_HUMAN_END_MARKER, markers[0].start())
        region_end = section_match.start() + end_relative + len(_FINAL_HUMAN_END_MARKER)
        regions.append(
            {
                "index": offset + 1,
                "verdict": verdict,
                "notes": human_match.group("notes").strip(),
                "start": region_start,
                "end": region_end,
            }
        )
    return regions


def _render_imported_human_region(decision: Mapping[str, Any]) -> str:
    verdict = str(decision["verdict"])
    pass_marker = "x" if verdict == "PASS" else " "
    fail_marker = "x" if verdict == "FAIL" else " "
    return (
        "<!-- BEGIN PHASE39 HUMAN REVIEW -->\n"
        f"**Your verdict:** [{pass_marker}] PASS   [{fail_marker}] FAIL\n\n"
        f"**Notes:** {decision['note']}\n"
        "<!-- END PHASE39 HUMAN REVIEW -->"
    )


def import_final_triage_decisions(
    *,
    triage_path: Path,
    sheet_path: Path,
    merged_path: Path,
    provenance_path: Path,
    manifest_path: Path,
    historical_sheet_path: Path,
    historical_merged_path: Path,
    protected_paths: Mapping[str, Path] | None = None,
    expected_triage_sha256: str = _LOCKED_FINAL_TRIAGE_SHA256,
    expected_sheet_preimport_sha256: str = _LOCKED_FINAL_SHEET_PREIMPORT_SHA256,
    required_carried_verdicts: Mapping[int, str] | None = None,
) -> dict[str, Any]:
    """Atomically port the user's locked final decisions into pending blocks only."""
    triage_path = Path(triage_path)
    sheet_path = Path(sheet_path)
    required_carries = dict(
        _FINAL_TRIAGE_REQUIRED_CARRIES
        if required_carried_verdicts is None
        else required_carried_verdicts
    )
    actual_triage_sha256 = sha256_path(triage_path)
    if actual_triage_sha256 != expected_triage_sha256:
        raise ValueError("FINALtriage SHA-256 differs from the locked human authority")
    decisions = parse_final_triage_decisions(
        triage_path.read_bytes().decode("utf-8-sig")
    )

    common_validation = {
        "merged_path": Path(merged_path),
        "provenance_path": Path(provenance_path),
        "manifest_path": Path(manifest_path),
        "historical_sheet_path": Path(historical_sheet_path),
        "historical_merged_path": Path(historical_merged_path),
        "protected_paths": protected_paths,
    }
    original_bytes = sheet_path.read_bytes()
    original_sha256 = hashlib.sha256(original_bytes).hexdigest()
    original_text = original_bytes.decode("utf-8")

    # Restart-safe success path: a prior atomic promotion is accepted only if the
    # strict validator and every locked triage verdict agree.
    if original_sha256 != expected_sheet_preimport_sha256:
        report = validate_final_review_sheet(
            sheet_path=sheet_path, require_complete=True, **common_validation
        )
        regions = _final_human_regions(original_text)
        if any(
            region["verdict"] != decision["verdict"]
            for region, decision in zip(regions, decisions, strict=True)
        ):
            raise ValueError(
                "completed final sheet verdicts differ from locked FINALtriage decisions"
            )
        for index, verdict in required_carries.items():
            if decisions[index - 1]["verdict"] != verdict:
                raise ValueError(f"FINALtriage contradicts carried Final Example {index}")
        return {
            **report,
            "triage_sha256": actual_triage_sha256,
            "sheet_sha256": original_sha256,
            "triage_pass_count": _FINAL_TRIAGE_EXPECTED_COUNTS["PASS"],
            "triage_fail_count": _FINAL_TRIAGE_EXPECTED_COUNTS["FAIL"],
            "already_complete": True,
        }

    pending_report = validate_final_review_sheet(
        sheet_path=sheet_path, allow_pending=True, **common_validation
    )
    regions = _final_human_regions(original_text)
    completed_indexes = {
        region["index"]: region["verdict"]
        for region in regions
        if region["verdict"] is not None
    }
    if completed_indexes != required_carries:
        raise ValueError(
            "canonical pre-import sheet does not contain exactly the required carries"
        )
    for index, verdict in required_carries.items():
        if decisions[index - 1]["verdict"] != verdict:
            raise ValueError(f"FINALtriage contradicts carried Final Example {index}")
    if pending_report["pending_count"] != 100 - len(required_carries):
        raise ValueError("canonical pre-import sheet has an unexpected pending count")

    pieces: list[str] = []
    cursor = 0
    for region, decision in zip(regions, decisions, strict=True):
        if region["verdict"] is not None:
            continue
        pieces.append(original_text[cursor : region["start"]])
        pieces.append(_render_imported_human_region(decision))
        cursor = region["end"]
    pieces.append(original_text[cursor:])
    candidate_bytes = "".join(pieces).encode("utf-8")

    sheet_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=sheet_path.parent,
            prefix=f".{sheet_path.name}.import-final-triage.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(candidate_bytes)
            temp_path = Path(handle.name)
        temp_report = validate_final_review_sheet(
            sheet_path=temp_path, require_complete=True, **common_validation
        )
        if sha256_path(triage_path) != expected_triage_sha256:
            raise ValueError("FINALtriage changed during import")
        if sha256_path(sheet_path) != expected_sheet_preimport_sha256:
            raise ValueError("canonical final sheet changed during import")
        temp_path.replace(sheet_path)
        temp_path = None
        final_report = validate_final_review_sheet(
            sheet_path=sheet_path, require_complete=True, **common_validation
        )
        if final_report != temp_report:
            raise ValueError("final validation differs from validated temporary output")
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()

    final_sha256 = sha256_path(sheet_path)
    return {
        **final_report,
        "triage_sha256": actual_triage_sha256,
        "sheet_preimport_sha256": original_sha256,
        "sheet_sha256": final_sha256,
        "triage_pass_count": _FINAL_TRIAGE_EXPECTED_COUNTS["PASS"],
        "triage_fail_count": _FINAL_TRIAGE_EXPECTED_COUNTS["FAIL"],
        "imported_pending_count": pending_report["pending_count"],
        "already_complete": False,
    }


# ---------------------------------------------------------------------------
# Report-bound final review evidence (Plan 39-07)
# ---------------------------------------------------------------------------

_FINAL_REVIEW_SUMMARY_SCHEMA = "phase39-final-manual-review-summary-v1"
_REPORT_NOTE_SCHEMA = "phase39-report-note-v1"
_LOCKED_COMPLETED_FINAL_SHEET_SHA256 = (
    "9c17be50796ddaf964c32ebb45080014d7dd1e8121778181491abe155aa5046b"
)


def _load_json_object(path: Path, *, context: str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"{context} is invalid: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{context} must be a JSON object")
    return value


def _atomic_write_text(path: Path, content: str) -> None:
    path = Path(path)
    encoded = content.encode("utf-8")
    if path.is_file() and path.read_bytes() == encoded:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.phase39-finalize.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(content)
            temporary = Path(handle.name)
        temporary.replace(path)
        temporary = None
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def _paths_alias(left: Path, right: Path) -> bool:
    left = Path(left)
    right = Path(right)
    if left.resolve() == right.resolve():
        return True
    if left.exists() and right.exists():
        try:
            return os.path.samefile(left, right)
        except OSError:
            return False
    return False


def _finalizer_protected_paths(kwargs: Mapping[str, Any]) -> dict[str, Path]:
    protected = {
        key: Path(value)
        for key, value in kwargs.items()
        if key.endswith("_path") and key not in {"output_path", "report_note_path"}
    }
    manifest_path = Path(kwargs["manifest_path"])
    for name, path in _default_protected_paths(manifest_path).items():
        protected[f"protected:{name}"] = path
    extra = kwargs.get("protected_paths")
    if isinstance(extra, Mapping):
        for name, path in extra.items():
            protected[f"protected-override:{name}"] = Path(path)
    return protected


def _assert_canonical_finalizer_outputs(
    *, output_path: Path, report_note_path: Path, manifest_path: Path, protected: Mapping[str, Path]
) -> None:
    root = Path(manifest_path).resolve().parents[2]
    expected_summary = (root / _FINAL_PHASE_RELATIVE / "39-final-manual-review-summary.json").resolve()
    expected_note = (root / _FINAL_PHASE_RELATIVE / "39-REPORT-NOTE.md").resolve()
    if Path(output_path).resolve() != expected_summary:
        raise ValueError("final review summary output must use the canonical Phase 39 path")
    if Path(report_note_path).resolve() != expected_note:
        raise ValueError("report note output must use the canonical Phase 39 path")
    if _paths_alias(Path(output_path), Path(report_note_path)):
        raise ValueError("final review summary and report note outputs must be distinct")
    for name, path in protected.items():
        if _paths_alias(Path(output_path), path) or _paths_alias(Path(report_note_path), path):
            raise ValueError(f"finalizer output aliases protected input: {name}")


def _validate_final_judge_summary(
    *,
    judge_summary_path: Path,
    evidence: Sequence[Mapping[str, Any]],
    manifest: Mapping[str, Any],
) -> dict[str, Any]:
    summary = _load_json_object(judge_summary_path, context="final judge summary")
    release = manifest.get("phase39_final_release")
    if not isinstance(release, Mapping):
        raise ValueError("manifest lacks phase39_final_release")
    judge_evidence = release.get("judge_evidence")
    if not isinstance(judge_evidence, Mapping):
        raise ValueError("manifest lacks final judge evidence")
    binding = judge_evidence.get("artifacts", {}).get("judge_summary")
    if not isinstance(binding, Mapping):
        raise ValueError("manifest lacks final judge summary binding")
    if binding.get("sha256") != sha256_path(Path(judge_summary_path)):
        raise ValueError("final judge summary SHA-256 differs from manifest")

    total = len(evidence)
    passed = sum(bool(row["judge_pass"]) for row in evidence)
    expected_means = {
        f"avg_{dimension}": sum(int(row[dimension]) for row in evidence) / total
        for dimension in _DIMENSIONS
    }
    expected = {
        "total": total,
        "passed": passed,
        "pass_rate": passed / total,
        **expected_means,
    }
    for key, value in expected.items():
        actual = summary.get(key)
        if not isinstance(actual, (int, float)) or abs(float(actual) - float(value)) > 1e-12:
            raise ValueError(f"final judge summary {key} differs from recomputation")
    if summary.get("pass_mismatch_count") != 0:
        raise ValueError("final judge summary contains pass mismatches")

    origins = Counter(str(row["judge_origin"]) for row in evidence)
    expected_origins = {
        "carried_forward_exact_record": origins["carried_forward_exact_record"],
        "fresh_final_delta": origins["fresh_final_delta"],
    }
    if {
        key: summary.get("evidence_origins", {}).get(key)
        for key in expected_origins
    } != expected_origins:
        raise ValueError("final judge origin counts differ from provenance")
    if {
        key: judge_evidence.get(key) for key in expected_origins
    } != expected_origins:
        raise ValueError("manifest final judge origin counts differ from provenance")
    return summary


def _validate_convergence_binding(
    *,
    convergence_path: Path,
    manifest: Mapping[str, Any],
    evidence_count: int,
) -> dict[str, Any]:
    convergence = _load_json_object(
        convergence_path, context="semantic convergence evidence"
    )
    release = manifest.get("phase39_final_release")
    binding = release.get("semantic_convergence") if isinstance(release, Mapping) else None
    if not isinstance(binding, Mapping):
        raise ValueError("manifest lacks semantic convergence binding")
    if binding.get("convergence_sha256") != sha256_path(Path(convergence_path)):
        raise ValueError("semantic convergence SHA-256 differs from manifest")
    for key in ("schema_version", "unresolved_count"):
        if convergence.get(key) != binding.get(key):
            raise ValueError(f"semantic convergence {key} differs from manifest")
    if convergence.get("unresolved_count") != 0:
        raise ValueError("semantic convergence still has unresolved rows")
    final_records = convergence.get("final_expected_profile", {}).get("total_rows")
    if final_records != binding.get("final_candidate_records"):
        raise ValueError("semantic convergence final record count differs from manifest")
    if final_records != evidence_count:
        raise ValueError("semantic convergence final record count differs")
    return convergence


def build_final_review_summary(
    *,
    sheet_path: Path,
    merged_path: Path,
    provenance_path: Path,
    manifest_path: Path,
    judge_summary_path: Path,
    convergence_path: Path,
    triage_path: Path,
    historical_sheet_path: Path,
    historical_merged_path: Path,
    protected_paths: Mapping[str, Path] | None = None,
    expected_sheet_sha256: str = _LOCKED_COMPLETED_FINAL_SHEET_SHA256,
) -> dict[str, Any]:
    """Recompute the completed 100-row result and bind it to release evidence."""
    sheet_path = Path(sheet_path)
    if sha256_path(sheet_path) != expected_sheet_sha256:
        raise ValueError("completed final review sheet SHA-256 differs from authority")
    if sha256_path(Path(triage_path)) != _LOCKED_FINAL_TRIAGE_SHA256:
        raise ValueError("FINALtriage SHA-256 differs from the locked human authority")

    validation = validate_final_review_sheet(
        sheet_path=sheet_path,
        merged_path=Path(merged_path),
        provenance_path=Path(provenance_path),
        manifest_path=Path(manifest_path),
        historical_sheet_path=Path(historical_sheet_path),
        historical_merged_path=Path(historical_merged_path),
        protected_paths=protected_paths,
        require_complete=True,
    )
    protected = (
        dict(protected_paths)
        if protected_paths is not None
        else _default_protected_paths(Path(manifest_path))
    )
    items, metadata = _prepare_expected_final_review(
        merged_path=Path(merged_path),
        provenance_path=Path(provenance_path),
        manifest_path=Path(manifest_path),
        historical_sheet_path=Path(historical_sheet_path),
        historical_merged_path=Path(historical_merged_path),
        protected_paths=protected,
        sample_size=100,
        salt=FINAL_SAMPLE_SALT,
    )
    regions = _final_human_regions(sheet_path.read_text(encoding="utf-8"))
    if any(region["verdict"] not in {"PASS", "FAIL"} for region in regions):
        raise ValueError("completed final review contains a pending verdict")

    evidence = load_final_evidence(Path(merged_path), Path(provenance_path))
    manifest = _load_json_object(Path(manifest_path), context="final manifest")
    judge = _validate_final_judge_summary(
        judge_summary_path=Path(judge_summary_path), evidence=evidence, manifest=manifest
    )
    convergence = _validate_convergence_binding(
        convergence_path=Path(convergence_path),
        manifest=manifest,
        evidence_count=len(evidence),
    )

    human_verdicts = Counter(str(region["verdict"]) for region in regions)
    human_origins = Counter(
        "carried_forward_exact_evidence"
        if item["human_verdict_origin"] == "carried_forward_exact_evidence"
        else "fresh_final_human"
        for item in items
    )
    agreement_count = sum(
        str(region["verdict"]) == ("PASS" if item["judge_pass"] else "FAIL")
        for item, region in zip(items, regions, strict=True)
    )
    sample_strata = Counter(
        "|".join(
            (
                str(item["label"]),
                "pass" if item["judge_pass"] else "fail",
                str(item["judge_origin"]),
            )
        )
        for item in items
    )
    label_by_human: dict[str, dict[str, int]] = {
        label: {"PASS": 0, "FAIL": 0} for label in _FINAL_LABELS
    }
    judge_status_by_human: dict[str, dict[str, int]] = {
        "fail": {"PASS": 0, "FAIL": 0},
        "pass": {"PASS": 0, "FAIL": 0},
    }
    for item, region in zip(items, regions, strict=True):
        human_verdict = str(region["verdict"])
        label_by_human[str(item["label"])][human_verdict] += 1
        judge_status = "pass" if item["judge_pass"] else "fail"
        judge_status_by_human[judge_status][human_verdict] += 1
    pass_count = human_verdicts["PASS"]
    fail_count = human_verdicts["FAIL"]
    if (pass_count, fail_count, agreement_count) != (44, 56, 87):
        raise ValueError(
            "completed human result differs from final authority (44 PASS, 56 FAIL, 87 agreements)"
        )

    return {
        "schema_version": _FINAL_REVIEW_SUMMARY_SCHEMA,
        "status": "complete",
        "sample_size": 100,
        "human_pass_count": pass_count,
        "human_fail_count": fail_count,
        "human_pass_rate": pass_count / 100,
        "judge_human_agreement_count": agreement_count,
        "judge_human_agreement_rate": agreement_count / 100,
        "composition": {
            "label": metadata["composition"]["sample_axes"]["label"],
            "judge_status": metadata["composition"]["sample_axes"]["judge_status"],
            "judge_origin": metadata["composition"]["sample_axes"]["judge_origin"],
            "human_verdict": dict(sorted(human_verdicts.items())),
            "human_verdict_origin": dict(sorted(human_origins.items())),
            "label_by_human_verdict": label_by_human,
            "judge_status_by_human_verdict": judge_status_by_human,
            "label_judge_status_judge_origin": dict(sorted(sample_strata.items())),
        },
        "reviewer_attestation": {
            "reviewer_role": "Vietnamese-fluent project reviewer",
            "statement": (
                "The reviewer personally reviewed all 98 previously pending "
                "final-snapshot rows in Vietnamese and declared FINALtriage.md final."
            ),
            "personally_reviewed_pending_rows": 98,
            "carried_exact_prior_human_rows": 2,
            "language": "Vietnamese",
            "authority": "user-declared final triage",
        },
        "judge_context": {
            "total": judge["total"],
            "passed": judge["passed"],
            "pass_rate": judge["pass_rate"],
            "carried_forward_exact_record": judge["evidence_origins"][
                "carried_forward_exact_record"
            ],
            "fresh_final_delta": judge["evidence_origins"]["fresh_final_delta"],
        },
        "semantic_convergence": {
            "schema_version": convergence["schema_version"],
            "iteration_count": len(convergence.get("iterations", [])),
            "unresolved_count": convergence["unresolved_count"],
            "final_candidate_records": convergence["final_expected_profile"][
                "total_rows"
            ],
        },
        "bindings": {
            "manifest_sha256": sha256_path(Path(manifest_path)),
            "judge_summary_sha256": sha256_path(Path(judge_summary_path)),
            "judge_merged_sha256": sha256_path(Path(merged_path)),
            "judge_provenance_sha256": sha256_path(Path(provenance_path)),
            "semantic_convergence_sha256": sha256_path(Path(convergence_path)),
            "completed_sheet_sha256": sha256_path(sheet_path),
            "final_triage_sha256": sha256_path(Path(triage_path)),
            "ordered_sample_digest_sha256": validation[
                "ordered_sample_digest_sha256"
            ],
        },
    }


def _report_facts(
    *, manifest: Mapping[str, Any], judge: Mapping[str, Any], human: Mapping[str, Any]
) -> dict[str, Any]:
    files = manifest.get("manifest", {}).get("files")
    distribution = manifest.get("split_class_distribution")
    triage = manifest.get("task_scam_mislabel_triage")
    if not isinstance(files, Mapping) or not isinstance(distribution, Mapping):
        raise ValueError("manifest lacks final split evidence")
    if not isinstance(triage, Mapping):
        raise ValueError("manifest lacks task-scam triage evidence")
    decisions = triage.get("decision_identity_dispositions")
    if not isinstance(decisions, list) or len(decisions) != 324:
        raise ValueError("manifest does not contain exactly 324 triage decisions")
    dispositions = Counter(str(row.get("disposition")) for row in decisions)
    approved = Counter(
        str(row.get("approved_label"))
        for row in decisions
        if row.get("normalized_action") == "relabel"
    )
    expected_dispositions = {"drop": 91, "admitted_relabel": 57, "lineage_quarantine": 176}
    if dict(dispositions) != expected_dispositions:
        raise ValueError("triage disposition counts differ from locked decision manifest")
    expected_approved = {
        "bank_impersonation": 48,
        "benign": 8,
        "zalo_social_engineering": 177,
    }
    if dict(approved) != expected_approved:
        raise ValueError("triage approved-label counts differ from locked decisions")
    validation = triage.get("validation")
    semantic_quarantine = triage.get("semantic_quarantine_contract")
    if not isinstance(validation, Mapping) or not isinstance(semantic_quarantine, Mapping):
        raise ValueError("manifest lacks final triage validation evidence")
    total = sum(int(entry["records"]) for entry in files.values())
    total_labels = {
        label: sum(int(split.get(label, 0)) for split in distribution.values())
        for label in _FINAL_LABELS
    }
    if total != validation.get("total_rows") or total_labels != validation.get(
        "total_class_distribution"
    ):
        raise ValueError("manifest final corpus totals are internally inconsistent")
    if validation.get("seed_disjointness") != "pass":
        raise ValueError("manifest final corpus seed-disjointness did not pass")

    reconstruction = manifest.get("zalo_direct_semantic_reconstruction")
    if not isinstance(reconstruction, Mapping):
        raise ValueError("manifest lacks Zalo semantic-reconstruction evidence")
    locked_reconstruction = {
        "finding_id": "F-01",
        "wording_status": "new-semantic-reconstruction-not-verbatim-recovery",
        "input_rows_replaced": 240,
        "output_rows_added": 300,
        "unique_seed_groups": 60,
        "variants_per_seed": 5,
        "non_zalo_records_preserved_exactly": True,
        "seed_to_split_assignments_preserved": True,
        "external_api_call_count": 0,
    }
    if any(
        reconstruction.get(key) != expected
        for key, expected in locked_reconstruction.items()
    ):
        raise ValueError("manifest Zalo semantic-reconstruction facts differ")
    generation = reconstruction.get("generation_provenance")
    if not isinstance(generation, Mapping) or any(
        generation.get(key) != expected
        for key, expected in {
            "authoring_runtime": "gpt-5.6-sol-codex-session",
            "generation_mode": "offline-static-direct-catalog",
            "wording_status": "new-semantic-reconstruction-not-verbatim-recovery",
            "external_api_calls": 0,
        }.items()
    ):
        raise ValueError("manifest Zalo reconstruction provenance differs")
    reconstruction_validation = reconstruction.get("validation")
    required_reconstruction_gates = {
        "schema_and_spans": "pass",
        "all_label_support": "pass",
        "seed_disjointness": "pass",
        "normalized_and_lexical_duplicates_at_0_95": "zero",
        "seed_cap_pct": 0.08,
    }
    if not isinstance(reconstruction_validation, Mapping) or any(
        reconstruction_validation.get(key) != expected
        for key, expected in required_reconstruction_gates.items()
    ):
        raise ValueError("manifest Zalo reconstruction validation differs")
    admitted_non_reconstruction_zalo = (
        expected_approved["zalo_social_engineering"]
        - expected_dispositions["lineage_quarantine"]
    )
    current_reconstructed_zalo = (
        total_labels["zalo_social_engineering"] - admitted_non_reconstruction_zalo
    )
    reconstructed_zalo_quarantined = (
        int(reconstruction["output_rows_added"]) - current_reconstructed_zalo
    )
    if (
        admitted_non_reconstruction_zalo != 1
        or current_reconstructed_zalo != 296
        or reconstructed_zalo_quarantined
        != int(semantic_quarantine["quarantine_artifact"]["records"])
    ):
        raise ValueError("final Zalo reconstruction overlap is inconsistent")
    return {
        "corpus_total": total,
        "split_files": files,
        "split_class_distribution": distribution,
        "total_class_distribution": total_labels,
        "triage_reviewed": len(decisions),
        "triage_drop": dispositions["drop"],
        "triage_admitted_relabel": dispositions["admitted_relabel"],
        "triage_lineage_quarantine": dispositions["lineage_quarantine"],
        "triage_approved_labels": expected_approved,
        "initial_seed_cap_drops": int(triage["seed_cap"]["rows_dropped"]),
        "semantic_quarantine_rows": int(
            semantic_quarantine["quarantine_artifact"]["records"]
        ),
        "semantic_quarantine_cap_drops": int(
            semantic_quarantine["cap_drop_artifact"]["records"]
        ),
        "judge": {
            key: judge[key]
            for key in (
                "total",
                "passed",
                "pass_rate",
                "avg_realism",
                "avg_label_correctness",
                "avg_code_switch_naturalness",
                "avg_risk_tier_correctness",
                "avg_suspicious_span_accuracy",
            )
        },
        "judge_carried": human["judge_context"]["carried_forward_exact_record"],
        "judge_fresh": human["judge_context"]["fresh_final_delta"],
        "human": {
            key: human[key]
            for key in (
                "sample_size",
                "human_pass_count",
                "human_fail_count",
                "human_pass_rate",
                "judge_human_agreement_count",
                "judge_human_agreement_rate",
            )
        },
        "human_composition": human["composition"],
        "semantic_convergence": human["semantic_convergence"],
        "historical_model_snapshot": {
            "train_rows": 2333,
            "validation_rows": 254,
            "then_designated_test_rows": 413,
            "recomputed_on_final_corpus": False,
        },
        "final_seed_disjointness": validation["seed_disjointness"],
        "zalo_reconstruction": {
            "input_rows_replaced": reconstruction["input_rows_replaced"],
            "output_rows_added": reconstruction["output_rows_added"],
            "semantic_root_count": reconstruction["unique_seed_groups"],
            "variants_per_lineage": reconstruction["variants_per_seed"],
            "non_zalo_records_preserved_exactly": reconstruction[
                "non_zalo_records_preserved_exactly"
            ],
            "seed_to_split_assignments_preserved": reconstruction[
                "seed_to_split_assignments_preserved"
            ],
            "external_api_call_count": reconstruction["external_api_call_count"],
            "current_final_rows": current_reconstructed_zalo,
            "later_semantic_quarantine_rows": reconstructed_zalo_quarantined,
            "other_final_zalo_rows": admitted_non_reconstruction_zalo,
            "validation": required_reconstruction_gates,
            "final_judge_generator_family_independent": False,
        },
        "bindings": human["bindings"],
    }


def render_report_note(
    *, manifest: Mapping[str, Any], judge: Mapping[str, Any], human: Mapping[str, Any]
) -> str:
    facts = _report_facts(manifest=manifest, judge=judge, human=human)
    split = facts["split_files"]
    labels = facts["total_class_distribution"]
    means = facts["judge"]
    reconstruction = facts["zalo_reconstruction"]
    human_zalo_rows = facts["human_composition"]["label"][
        "zalo_social_engineering"
    ]
    marker = _canonical_json({"schema_version": _REPORT_NOTE_SCHEMA, "facts": facts})
    return f"""# Phase 39 Report Evidence Note

<!-- phase39-report-note:{marker} -->

This note is generated from the promoted manifest, final judge bundle, semantic-convergence evidence, and completed manifest-bound human sheet. Do not hand-edit its values.

## Final corpus

- Total: **{facts['corpus_total']:,}** rows; train **{split['train.jsonl']['records']:,}**, validation **{split['val.jsonl']['records']:,}**, test **{split['test.jsonl']['records']:,}**.
- Labels: bank impersonation **{labels['bank_impersonation']:,}**, benign **{labels['benign']:,}**, task scam **{labels['task_scam']:,}**, Zalo social engineering **{labels['zalo_social_engineering']:,}**.
- Split SHA-256: train `{split['train.jsonl']['sha256']}`, validation `{split['val.jsonl']['sha256']}`, test `{split['test.jsonl']['sha256']}`.

## Targeted human triage and lineage governance

The Vietnamese-fluent reviewer examined **{facts['triage_reviewed']} judge-flagged task-scam candidates**. Decisions were **{facts['triage_drop']} drops** and **{facts['triage_admitted_relabel'] + facts['triage_lineage_quarantine']} relabel approvals** ({facts['triage_approved_labels']['bank_impersonation']} bank impersonation, {facts['triage_approved_labels']['zalo_social_engineering']} Zalo social engineering, {facts['triage_approved_labels']['benign']} benign). Admission was separate: **{facts['triage_admitted_relabel']} relabels were admitted**, while **{facts['triage_lineage_quarantine']} human-approved Zalo semantics were excluded solely because they share one non-independent lineage**. The initial global seed cap removed **{facts['initial_seed_cap_drops']}** rows. Final semantic convergence additionally quarantined **{facts['semantic_quarantine_rows']}** unrepairable-label rows and removed **{facts['semantic_quarantine_cap_drops']}** cap rows.

This was targeted candidate triage, not annotation of every corpus row. The lineage-quarantined records were not judged semantically wrong; they were excluded to prevent manufactured seed diversity.

## Zalo reconstruction provenance

An independent post-generation review identified systematic scenario-framing and narrative artifacts in the synthetic Zalo subset. The affected **{reconstruction['input_rows_replaced']} retained records were replaced, not recovered as originals**. A controlled offline, model-assisted reconstruction used **{reconstruction['semantic_root_count']} preserved semantic roots and seed lineages** to create **{reconstruction['output_rows_added']} new direct-message realizations** ({reconstruction['variants_per_lineage']} per lineage). Seed-to-split assignments and every non-Zalo record were preserved, and the static reconstruction made **{reconstruction['external_api_call_count']} external API calls**. Schema/span, label-support, seed-disjointness, duplicate, and seed-cap gates passed. These variants remain synthetic and are not independently observed real-world messages. The final-current corpus is the **{facts['corpus_total']:,}-row** promoted corpus reported above; earlier correction-snapshot counts are not current.

## Final judge evidence and independence scope

The final bundle contains **{means['total']:,}** joined verdicts: **{facts['judge_carried']:,} exact-record carries** plus **{facts['judge_fresh']:,} newly judged final-delta records**. It records **{means['passed']:,} passes ({means['pass_rate'] * 100:.2f}%)**. Mean scores were realism **{means['avg_realism']:.3f}**, label correctness **{means['avg_label_correctness']:.3f}**, code-switch naturalness **{means['avg_code_switch_naturalness']:.3f}**, risk-tier correctness **{means['avg_risk_tier_correctness']:.3f}**, and suspicious-span accuracy **{means['avg_suspicious_span_accuracy']:.3f}**, each on the 1--5 rubric. Semantic convergence ended with **{facts['semantic_convergence']['unresolved_count']} unresolved rows**.

The final judge used a model family different from the original synthetic-corpus generator, but that independence does not apply uniformly. The **{reconstruction['output_rows_added']}-row Zalo reconstruction batch** and the final judge share a model family. After **{reconstruction['later_semantic_quarantine_rows']} reconstructed rows** were semantically quarantined, **{reconstruction['current_final_rows']} reconstructed rows remain** in the final corpus and final judge bundle; their judgments are **not generator-family-independent**. The final Zalo total is {labels['zalo_social_engineering']}, including {reconstruction['other_final_zalo_rows']} separately admitted relabel. The bundle also combines exact-record carries and a newly judged delta; it must not be presented as an all-new judge pass over every row.

## Final stratified human sample

The separate manifest-bound sample contains **{facts['human']['sample_size']} rows**: **{facts['human']['human_pass_count']} PASS** and **{facts['human']['human_fail_count']} FAIL**, a descriptive pass rate of **{facts['human']['human_pass_rate'] * 100:.1f}%**. Human and judge verdicts agreed on **{facts['human']['judge_human_agreement_count']}/{facts['human']['sample_size']} ({facts['human']['judge_human_agreement_rate'] * 100:.1f}%)**. It includes all four labels, judge PASS and FAIL outcomes, both exact-carry and fresh-delta judge origins, and **{human_zalo_rows} Zalo rows**. This is separate partial human corroboration; it does not make the whole reconstructed Zalo subset generator-family-independent. The result describes a stratified 100-row quality check, not every corpus record.

## Current-versus-historical wording contract

Current data-quality claims must use the promoted **{facts['corpus_total']:,}-row corpus**, **{means['total']:,} joined judge verdicts**, the separate **{facts['human']['sample_size']}-row human sample**, and **zero cross-split seed leakage** (`seed_disjointness: {facts['final_seed_disjointness']}`). The **{facts['historical_model_snapshot']['train_rows']:,}-train / {facts['historical_model_snapshot']['validation_rows']}-validation / {facts['historical_model_snapshot']['then_designated_test_rows']}-then-designated-test** counts and their model metrics belong only to an earlier model-training snapshot and were **not recomputed on the promoted corpus**. Active prose, tables, slides, and defense material must visibly mark those values historical; they must not describe the current quality method as only a 50-record LLM sample, claim overlapping seed groups in the final split, or call the former {facts['historical_model_snapshot']['then_designated_test_rows']}-row partition the current test set.

## Exact replacement evidence

**Chapter III / methodology:** Report the promoted {facts['corpus_total']:,}-row corpus ({split['train.jsonl']['records']:,}/{split['val.jsonl']['records']:,}/{split['test.jsonl']['records']:,}), the {facts['triage_reviewed']}-candidate targeted review, {facts['triage_lineage_quarantine']} human-approved shared-lineage exclusions, {means['total']:,} final joined judge verdicts ({facts['judge_carried']:,} carries + {facts['judge_fresh']:,} fresh delta), the five descriptive means above, zero unresolved convergence rows, and the separate {facts['human']['human_pass_count']}/{facts['human']['sample_size']} human result.

**Chapter V / evaluation:** Treat the {means['pass_rate'] * 100:.2f}% judge pass rate and five means as descriptive data-quality evidence. Report the completed {facts['human']['human_pass_count']}/{facts['human']['sample_size']} human sample and {facts['human']['judge_human_agreement_count']}/{facts['human']['sample_size']} agreement without inferential testing.

**Data slide:** `Final corpus {facts['corpus_total']:,} | judge {means['passed']:,}/{means['total']:,} pass ({means['pass_rate'] * 100:.1f}%) | human {facts['human']['human_pass_count']}/{facts['human']['sample_size']} pass | agreement {facts['human']['judge_human_agreement_count']}/{facts['human']['sample_size']}`.
"""


def finalize_review(
    *, output_path: Path, report_note_path: Path, **kwargs: Any
) -> dict[str, Any]:
    protected = _finalizer_protected_paths(kwargs)
    _assert_canonical_finalizer_outputs(
        output_path=Path(output_path),
        report_note_path=Path(report_note_path),
        manifest_path=Path(kwargs["manifest_path"]),
        protected=protected,
    )
    before_hashes: dict[str, str] = {}
    for name, path in protected.items():
        if not path.is_file():
            raise ValueError(f"finalizer protected input is missing: {name}")
        before_hashes[name] = sha256_path(path)
    summary = build_final_review_summary(**kwargs)
    manifest = _load_json_object(Path(kwargs["manifest_path"]), context="final manifest")
    judge = _load_json_object(
        Path(kwargs["judge_summary_path"]), context="final judge summary"
    )
    note = render_report_note(manifest=manifest, judge=judge, human=summary)
    prohibited = (
        "fresh full-corpus judge rerun",
        "full-corpus human annotation",
        "quarantined semantics were wrong",
    )
    folded = note.casefold()
    if any(phrase in folded for phrase in prohibited):
        raise ValueError("report note contains prohibited scope wording")
    if {
        name: sha256_path(path) for name, path in protected.items()
    } != before_hashes:
        raise ValueError("finalizer protected input changed before output promotion")
    _atomic_write_text(
        Path(output_path),
        json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
    )
    _atomic_write_text(Path(report_note_path), note)
    if {
        name: sha256_path(path) for name, path in protected.items()
    } != before_hashes:
        raise ValueError("finalizer protected input changed during output promotion")
    if _load_json_object(Path(output_path), context="written final human summary") != summary:
        raise ValueError("written final human summary differs after promotion")
    if Path(report_note_path).read_text(encoding="utf-8") != note:
        raise ValueError("written report note differs after promotion")
    return {
        "status": "complete",
        "summary_path": str(output_path),
        "summary_sha256": sha256_path(Path(output_path)),
        "report_note_path": str(report_note_path),
        "report_note_sha256": sha256_path(Path(report_note_path)),
        "human_pass_count": summary["human_pass_count"],
        "human_fail_count": summary["human_fail_count"],
        "judge_human_agreement_count": summary["judge_human_agreement_count"],
    }


def _resolve_evidence_path(repo_root: Path, value: str, *, context: str) -> Path:
    path = Path(value)
    resolved = (repo_root / path).resolve() if not path.is_absolute() else path.resolve()
    try:
        resolved.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise ValueError(f"{context} path escapes repository root: {value}") from exc
    if not resolved.is_file():
        raise ValueError(f"{context} file is missing: {value}")
    return resolved


_EXPECTED_COMPILE_COMMANDS = {
    "thesis": [
        "xelatex -interaction=nonstopmode -halt-on-error -file-line-error main.tex",
        "bibtex main",
        "xelatex -interaction=nonstopmode -halt-on-error -file-line-error main.tex",
        "xelatex -interaction=nonstopmode -halt-on-error -file-line-error main.tex",
    ],
    "slides": [
        "xelatex -interaction=nonstopmode -halt-on-error -file-line-error slides.tex",
        "xelatex -interaction=nonstopmode -halt-on-error -file-line-error slides.tex",
    ],
}
_COMPILE_WORKING_DIRECTORY = "documents/reports/latex"
_EXPECTED_COMPILE_OUTPUTS = {
    "thesis": {
        "logs": [
            "documents/reports/latex/main.log",
            "documents/reports/latex/main.blg",
        ],
        "pdf": "documents/reports/latex/main.pdf",
    },
    "slides": {
        "logs": ["documents/reports/latex/slides.log"],
        "pdf": "documents/reports/latex/slides.pdf",
    },
}
_COMPILE_SOURCE_EXTENSIONS = {
    ".bib",
    ".cls",
    ".eps",
    ".jpeg",
    ".jpg",
    ".pdf",
    ".png",
    ".sty",
    ".svg",
    ".tex",
}
_COMPILE_GENERATED_SOURCE_EXCLUSIONS = {
    "documents/reports/latex/main.pdf",
    "documents/reports/latex/slides.pdf",
}
_COMPILE_REQUIRED_SOURCE_FILES = {
    "documents/reports/latex/main.tex",
    "documents/reports/latex/slides.tex",
    "documents/reports/latex/references.bib",
}
_COMPILE_REQUIRED_SOURCE_DIRS = {
    "documents/reports/latex/chapters",
    "documents/reports/latex/slides",
}
_COMPILE_LOG_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "fatal_error_hits": (
        re.compile(r"^!\s"),
        re.compile(r"Emergency stop", re.IGNORECASE),
        re.compile(r"Fatal error occurred", re.IGNORECASE),
        re.compile(r"No pages of output", re.IGNORECASE),
    ),
    "undefined_reference_hits": (
        re.compile(r"LaTeX Warning: Reference .* undefined", re.IGNORECASE),
        re.compile(r"There were undefined references", re.IGNORECASE),
    ),
    "undefined_citation_hits": (
        re.compile(r"LaTeX Warning: Citation .* undefined", re.IGNORECASE),
        re.compile(r"There were undefined citations", re.IGNORECASE),
    ),
}


def _parse_utc_timestamp(value: Any, *, field: str) -> datetime:
    if not isinstance(value, str) or not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,9})?Z", value
    ):
        raise ValueError(f"compile evidence {field} must be an ISO-8601 UTC Z timestamp")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError(f"compile evidence {field} is invalid") from exc
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError(f"compile evidence {field} is not UTC")
    return parsed


def _scan_compile_logs(
    *, repo_root: Path, logs: Sequence[Mapping[str, Any]]
) -> dict[str, list[dict[str, Any]]]:
    findings = {field: [] for field in _COMPILE_LOG_PATTERNS}
    for entry in logs:
        relative = str(entry.get("path", "")).replace("\\", "/")
        path = _resolve_evidence_path(repo_root, relative, context="compile log")
        try:
            lines = path.read_text(encoding="utf-8", errors="strict").splitlines()
        except UnicodeDecodeError as exc:
            raise ValueError(f"compile log is not UTF-8: {relative}") from exc
        for line_number, line in enumerate(lines, start=1):
            context = line.strip()
            for field, patterns in _COMPILE_LOG_PATTERNS.items():
                if any(pattern.search(line) for pattern in patterns):
                    findings[field].append(
                        {"path": relative, "line": line_number, "context": context}
                    )
    return findings


def _compile_source_inventory(repo_root: Path) -> dict[str, Path]:
    repo_root = Path(repo_root).resolve()
    compile_root = repo_root / _COMPILE_WORKING_DIRECTORY
    if not compile_root.is_dir():
        raise ValueError("compile source root is missing")
    for relative in _COMPILE_REQUIRED_SOURCE_DIRS:
        if not (repo_root / relative).is_dir():
            raise ValueError(f"required compile source directory is missing: {relative}")
    for relative in _COMPILE_REQUIRED_SOURCE_FILES:
        if not (repo_root / relative).is_file():
            raise ValueError(f"required compile source file is missing: {relative}")
    inventory: dict[str, Path] = {}
    for path in compile_root.rglob("*"):
        if not path.is_file() or path.suffix.casefold() not in _COMPILE_SOURCE_EXTENSIONS:
            continue
        relative = path.relative_to(repo_root).as_posix()
        if relative in _COMPILE_GENERATED_SOURCE_EXCLUSIONS:
            continue
        inventory[relative] = path.resolve()
    if not _COMPILE_REQUIRED_SOURCE_FILES.issubset(inventory):
        raise ValueError("compile source inventory omitted a required root file")
    return dict(sorted(inventory.items()))


def _verified_pdf_page_count(path: Path) -> int:
    if path.read_bytes()[:5] != b"%PDF-":
        raise ValueError(f"compile PDF lacks PDF magic: {path.name}")
    try:
        import fitz  # type: ignore[import-not-found]
    except ImportError as exc:
        raise ValueError("PyMuPDF is required to verify compile PDF page counts") from exc
    try:
        with fitz.open(path) as document:
            if not document.is_pdf or document.needs_pass:
                raise ValueError(f"compile PDF is not an open canonical PDF: {path.name}")
            count = int(document.page_count)
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"compile PDF cannot be parsed: {path.name}") from exc
    if count <= 0:
        raise ValueError(f"compile PDF has no pages: {path.name}")
    return count


def validate_report_compile_evidence(
    *, evidence_path: Path, repo_root: Path, report_note_path: Path
) -> dict[str, Any]:
    evidence = _load_json_object(evidence_path, context="report compile evidence")
    if evidence.get("schema_version") != "phase39-report-compile-v1":
        raise ValueError("report compile evidence schema version differs")
    if evidence.get("status") != "clean":
        raise ValueError("report compile evidence is not clean")
    if evidence.get("report_note_sha256") != sha256_path(Path(report_note_path)):
        raise ValueError("compile evidence report-note binding differs")
    started = _parse_utc_timestamp(
        evidence.get("started_at_utc"), field="started_at_utc"
    )
    completed = _parse_utc_timestamp(
        evidence.get("completed_at_utc"), field="completed_at_utc"
    )
    if completed < started:
        raise ValueError("compile evidence completed_at_utc precedes started_at_utc")
    if evidence.get("source_inventory_root") != _COMPILE_WORKING_DIRECTORY:
        raise ValueError("compile evidence source inventory root differs")
    if evidence.get("source_inventory_excluded") != sorted(
        _COMPILE_GENERATED_SOURCE_EXCLUSIONS
    ):
        raise ValueError("compile evidence source exclusion set differs")
    expected_sources = _compile_source_inventory(repo_root)
    newest_source_mtime = max(path.stat().st_mtime for path in expected_sources.values())
    source_hashes = evidence.get("source_sha256")
    if not isinstance(source_hashes, Mapping) or set(source_hashes) != set(
        expected_sources
    ):
        raise ValueError("compile evidence source inventory differs")
    for relative, source in expected_sources.items():
        digest = source_hashes[relative]
        if digest != sha256_path(source):
            raise ValueError(f"compile source SHA-256 differs: {relative}")

    builds = evidence.get("builds")
    if not isinstance(builds, Mapping) or set(builds) != {"thesis", "slides"}:
        raise ValueError("compile evidence must contain thesis and slides builds")
    for name, expected_commands in _EXPECTED_COMPILE_COMMANDS.items():
        build = builds[name]
        if not isinstance(build, Mapping) or build.get("status") != "clean":
            raise ValueError(f"{name} build is not clean")
        if build.get("working_directory") != _COMPILE_WORKING_DIRECTORY:
            raise ValueError(f"{name} build working directory differs")
        commands = build.get("commands")
        exit_codes = build.get("exit_codes")
        if commands != expected_commands:
            raise ValueError(f"{name} build command/root sequence differs")
        if exit_codes != [0] * len(expected_commands):
            raise ValueError(f"{name} build contains a nonzero exit code")
        logs = build.get("logs")
        if not isinstance(logs, list) or not logs:
            raise ValueError(f"{name} build lacks log evidence")
        log_paths = [
            str(entry.get("path", "")).replace("\\", "/")
            if isinstance(entry, Mapping)
            else ""
            for entry in logs
        ]
        if log_paths != _EXPECTED_COMPILE_OUTPUTS[name]["logs"]:
            raise ValueError(f"{name} build log path set differs")
        for entry in logs:
            if not isinstance(entry, Mapping):
                raise ValueError(f"{name} build has malformed log evidence")
            path = _resolve_evidence_path(
                repo_root, str(entry.get("path", "")), context=f"{name} log"
            )
            if entry.get("sha256") != sha256_path(path):
                raise ValueError(f"{name} log SHA-256 differs")
            output_mtime = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
            if not (
                started - timedelta(seconds=2)
                <= output_mtime
                <= completed + timedelta(seconds=2)
            ):
                raise ValueError(f"{name} log mtime falls outside build window")
            if path.stat().st_mtime + 2 < newest_source_mtime:
                raise ValueError(f"{name} log predates a bound compile source")
        recomputed_log_findings = _scan_compile_logs(
            repo_root=repo_root, logs=logs
        )
        for field, recomputed in recomputed_log_findings.items():
            if build.get(field) != recomputed:
                raise ValueError(f"{name} build {field} differs from log scan")
            if recomputed:
                raise ValueError(f"{name} build has {field}")
        pdf = build.get("pdf")
        if not isinstance(pdf, Mapping):
            raise ValueError(f"{name} build lacks PDF evidence")
        pdf_relative = str(pdf.get("path", "")).replace("\\", "/")
        if pdf_relative != _EXPECTED_COMPILE_OUTPUTS[name]["pdf"]:
            raise ValueError(f"{name} PDF path differs")
        pdf_path = _resolve_evidence_path(
            repo_root, pdf_relative, context=f"{name} PDF"
        )
        if pdf.get("sha256") != sha256_path(pdf_path):
            raise ValueError(f"{name} PDF SHA-256 differs")
        if pdf.get("bytes") != pdf_path.stat().st_size or pdf_path.stat().st_size <= 0:
            raise ValueError(f"{name} PDF byte count differs")
        if pdf.get("pages") != _verified_pdf_page_count(pdf_path):
            raise ValueError(f"{name} PDF page count differs from parsed PDF")
        pdf_mtime = datetime.fromtimestamp(pdf_path.stat().st_mtime, timezone.utc)
        if not (
            started - timedelta(seconds=2)
            <= pdf_mtime
            <= completed + timedelta(seconds=2)
        ):
            raise ValueError(f"{name} PDF mtime falls outside build window")
        if pdf_path.stat().st_mtime + 2 < newest_source_mtime:
            raise ValueError(f"{name} PDF predates a bound compile source")
    return evidence


def _active_source_inventory(repo_root: Path) -> list[Path]:
    documents = repo_root / "documents"
    if not documents.is_dir():
        raise ValueError("active source root documents/ is missing")
    paths = [
        path
        for path in documents.rglob("*")
        if path.is_file() and path.suffix.casefold() in {".md", ".tex"}
    ]
    paths.extend(path for path in repo_root.glob("defense_*.md") if path.is_file())
    unique = {path.resolve(): path.resolve() for path in paths}
    return sorted(unique.values(), key=lambda path: path.as_posix().casefold())


_SUPERSEDED_TEST_SHA256 = (
    "019aec39979429ca8005dd299d2ddaf7d3ecfdade259eecc4d3129adaed25938"
)
_CURRENT_FINAL_TEST_SHA256 = (
    "6f208fb6cd9399b8934225e6a25efd65d49bbb4f4846360837f6835a2561b6d7"
)
_IMMUTABLE_HISTORY_ALLOWLIST = {"documents/Transcript defense.md"}
_STALE_CLAIM_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "retired_t_statistic",
        re.compile(r"\bt\s*=\s*(?:8[.,]7|53[.,]2)\b", re.IGNORECASE),
    ),
    (
        "retired_p_value",
        re.compile(r"\bp\s*<\s*0[.,]0001\b", re.IGNORECASE),
    ),
    (
        "retired_null_hypothesis",
        re.compile(
            r"(?:\bnull[- ]hypothesis\b|"
            r"\bH(?:₀|\$_?\{?0\}?\$|\\?_?\{?0\}?)(?![A-Za-z0-9]))",
            re.IGNORECASE,
        ),
    ),
    (
        "retired_94_of_100",
        re.compile(r"(?:\b94\s*/\s*100\b|\bNinety-four\s+passed\b)", re.IGNORECASE),
    ),
    (
        "retired_quality_49_of_50",
        re.compile(r"\b49\s*/\s*50\b", re.IGNORECASE),
    ),
    (
        "retired_quality_means_4_68_4_96",
        re.compile(r"\b4[.,](?:68|96)\b", re.IGNORECASE),
    ),
    (
        "retired_50_record_sample_review",
        re.compile(
            r"(?:\b50\s+(?:sampled\s+records?|record\s+sample|sample\s+records?)\b|"
            r"\b(?:LLM|model)[- ]based\s+(?:quality\s+)?review\s+of\s+50\b)",
            re.IGNORECASE,
        ),
    ),
    (
        "superseded_corpus_2403",
        re.compile(r"\b2(?:,|\{,\}|\\,)403\b"),
    ),
    (
        "superseded_split_1900_252_251",
        re.compile(
            r"\b1(?:,|\{,\}|\\,)900\b.{0,160}\b252\b.{0,160}\b251\b",
            re.IGNORECASE,
        ),
    ),
    (
        "superseded_test_sha256",
        re.compile(re.escape(_SUPERSEDED_TEST_SHA256), re.IGNORECASE),
    ),
    (
        "current_final_test_sha256",
        re.compile(re.escape(_CURRENT_FINAL_TEST_SHA256), re.IGNORECASE),
    ),
    (
        "historical_model_train_2333",
        re.compile(
            r"(?:\b2(?:,|\{,\}|\\,)333\b.{0,80}\b(?:train(?:ing)?|examples?|records?)\b|"
            r"\b(?:train(?:ing)?|examples?|records?)\b.{0,80}\b2(?:,|\{,\}|\\,)333\b)",
            re.IGNORECASE,
        ),
    ),
    (
        "historical_model_validation_254",
        re.compile(
            r"(?:\b254(?:-row|-message|-example)?\b.{0,80}\b(?:validation|model|metric|messages?|examples?|samples?|result|split)\b|"
            r"\b(?:validation|model|metric|messages?|examples?|samples?|result|split)\b.{0,80}\b254(?:-row|-message|-example)?\b)",
            re.IGNORECASE,
        ),
    ),
    (
        "historical_model_test_413",
        re.compile(
            r"(?:\b413(?:-row)?\b.{0,80}\b(?:test|records?|partition|split)\b|"
            r"\b(?:test|records?|partition|split)\b.{0,80}\b413(?:-row)?\b)",
            re.IGNORECASE,
        ),
    ),
    (
        "historical_seed_overlap",
        re.compile(
            r"(?:\b(?:final\s+)?splits?\b.{0,100}\boverlapping?\s+seed(?:_id)?(?:\s+groups?)?\b|"
            r"\bone\s+seed(?:_id)?\s+group\s+spans\s+multiple\s+splits\b|"
            r"\b(?:includes?|contains?)\s+seed(?:_id)?\s+overlap\b|"
            r"\bseed(?:_id)?\s+overlap\b)",
            re.IGNORECASE,
        ),
    ),
    (
        "false_universal_judge_independence",
        re.compile(
            r"(?:\bgenerator\s+never\s+grades\s+its\s+own\s+homework\b|"
            r"\balways\s+(?:uses?|is)\s+(?:a\s+)?different\s+model\b)",
            re.IGNORECASE,
        ),
    ),
    (
        "false_evaluate_release_default_reproduction",
        re.compile(
            r"\bdefaults?\s+(?:reproduce|recreate|replicate)\s+"
            r"(?:the\s+)?(?:reported|historical|held[- ]out)\s+"
            r"(?:run|results?|metrics?|evaluation)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "ambiguous_final_stack_internal_validation",
        re.compile(
            r"(?:\bfinal\s+stage\b.{0,80}\bevaluat(?:e|es|ed|ion)\b.{0,80}"
            r"\b(?:the\s+)?full\s+stack\b.{0,100}\binternal\s+validation\s+split\b|"
            r"\bfull\s+stack\b.{0,80}\bevaluat(?:e|es|ed|ion)\b.{0,100}"
            r"\binternal\s+validation\s+split\b)",
            re.IGNORECASE,
        ),
    ),
    (
        "false_promoted_corpus_model_completion",
        re.compile(
            r"(?:\b(?:model|adapter|checkpoint)\b.{0,100}"
            r"\b(?:was|is|has\s+been)\s+(?:trained|fine[- ]tuned|adapted|evaluated)\b"
            r".{0,120}\bpromoted\b.{0,40}\b2(?:,|\{,\}|\\,)097(?:-row)?\b|"
            r"\bpromoted\b.{0,40}\b2(?:,|\{,\}|\\,)097(?:-row)?\s+corpus\b"
            r".{0,120}\b(?:was|has\s+been|already)\s+"
            r"(?:used\s+(?:to|for)\s+)?(?:model\s+)?"
            r"(?:train(?:ing|ed)?|fine[- ]tun(?:e|ed|ing)|adapt(?:ed|ation)?|evaluat(?:e|ed|ion))\b)",
            re.IGNORECASE,
        ),
    ),
    (
        "false_historical_254_held_out",
        re.compile(
            r"(?:\bheld[- ]out\s+(?:(?:evaluation|test|split|result)\s+)?"
            r"(?:on\s+)?(?:the\s+)?(?:historical\s+)?"
            r"254(?:-row|-example|-message)?\b|"
            r"\b(?:historical\s+)?254(?:-row|-example|-message)?\s+"
            r"(?:(?:evaluation|test|split|result)\s+)?held[- ]out\b)",
            re.IGNORECASE,
        ),
    ),
    (
        "false_universal_threat_recall",
        re.compile(
            r"\b(?:the\s+)?model\s+never\s+(?:lets?|allows?|misses?)\s+"
            r"(?:a\s+)?(?:real\s+)?threats?(?:\s+(?:through|past))?\b",
            re.IGNORECASE,
        ),
    ),
)

_HISTORICAL_MODEL_PATTERN_NAMES = {
    "historical_model_train_2333",
    "historical_model_validation_254",
    "historical_model_test_413",
    "historical_seed_overlap",
    "ambiguous_final_stack_internal_validation",
}
_EXPLICIT_HISTORICAL_MODEL_CONTEXT = re.compile(
    r"(?:\b(?:historical|earlier|older|former|legacy)\b|"
    r"\bnot\s+(?:been\s+)?recomputed\b|\bthen[- ]designated\b)",
    re.IGNORECASE,
)


def _has_explicit_historical_model_context(
    *, relative: str, lines: Sequence[str], line_index: int
) -> bool:
    line = lines[line_index]
    if _EXPLICIT_HISTORICAL_MODEL_CONTEXT.search(line):
        return True
    normalized = relative.replace("\\", "/")
    if "/tables/" in normalized or "/figures/" in normalized:
        return any(
            "\\caption" in candidate
            and _EXPLICIT_HISTORICAL_MODEL_CONTEXT.search(candidate)
            for candidate in lines
        )
    if "/slides/" in normalized:
        start = max(
            (index for index in range(line_index, -1, -1) if "\\begin{frame}" in lines[index]),
            default=line_index,
        )
        end = next(
            (index for index in range(line_index, len(lines)) if "\\end{frame}" in lines[index]),
            line_index,
        )
        return any(
            _EXPLICIT_HISTORICAL_MODEL_CONTEXT.search(candidate)
            for candidate in lines[start : end + 1]
        )
    return False


def _recompute_stale_claim_hits(
    *,
    current: Mapping[str, Path],
    recorded: Mapping[str, Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    hits: list[dict[str, Any]] = []
    for relative in sorted(current, key=str.casefold):
        classification = recorded[relative]["classification"]
        try:
            lines = current[relative].read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError as exc:
            raise ValueError(f"active source is not UTF-8: {relative}") from exc
        for line_number, line in enumerate(lines, start=1):
            context = line.strip()
            for pattern_name, pattern in _STALE_CLAIM_PATTERNS:
                if pattern.search(line) is None:
                    continue
                if classification == "immutable_history":
                    disposition = "immutable_history"
                elif pattern_name == "current_final_test_sha256":
                    disposition = "current_final_test_hash"
                elif pattern_name in _HISTORICAL_MODEL_PATTERN_NAMES and (
                    _has_explicit_historical_model_context(
                        relative=relative,
                        lines=lines,
                        line_index=line_number - 1,
                    )
                ):
                    disposition = "historical_model_snapshot"
                else:
                    disposition = "unclassified_current"
                hits.append(
                    {
                        "pattern": pattern_name,
                        "path": relative,
                        "line": line_number,
                        "context": context,
                        "disposition": disposition,
                    }
                )
    unresolved = [hit for hit in hits if hit["disposition"] == "unclassified_current"]
    return hits, unresolved


def validate_stale_claim_scan(*, evidence_path: Path, repo_root: Path) -> dict[str, Any]:
    evidence = _load_json_object(evidence_path, context="stale-claim scan evidence")
    if evidence.get("schema_version") != "phase39-stale-claim-scan-v1":
        raise ValueError("stale-claim scan schema version differs")
    if evidence.get("status") != "clean":
        raise ValueError("stale-claim scan is not clean")
    if evidence.get("expected_roots") != ["documents", ".:defense_*.md"]:
        raise ValueError("stale-claim scan expected roots differ")
    required = {
        "documents/Transcript defense.md",
        "documents/reports/latex/chapters/03_methodology_and_system_design.tex",
        "documents/reports/latex/chapters/05_evaluation_and_discussion.tex",
        "documents/reports/latex/slides/sections/05_data.tex",
    }
    expected_files = evidence.get("expected_files")
    if not isinstance(expected_files, list) or not required.issubset(set(expected_files)):
        raise ValueError("stale-claim scan is missing an expected active source")
    current = {
        path.relative_to(repo_root.resolve()).as_posix(): path
        for path in _active_source_inventory(repo_root.resolve())
    }
    if not required.issubset(current):
        missing = sorted(required - set(current))
        raise ValueError(f"required active source is missing from live inventory: {missing}")
    inventory = evidence.get("inventory")
    if not isinstance(inventory, list):
        raise ValueError("stale-claim scan lacks source inventory")
    recorded: dict[str, Mapping[str, Any]] = {}
    for entry in inventory:
        if not isinstance(entry, Mapping) or not isinstance(entry.get("path"), str):
            raise ValueError("stale-claim source inventory is malformed")
        path = str(entry["path"]).replace("\\", "/")
        if path in recorded:
            raise ValueError(f"stale-claim source inventory repeats {path}")
        expected_classification = (
            "immutable_history"
            if path in _IMMUTABLE_HISTORY_ALLOWLIST
            else "active_current"
        )
        if entry.get("classification") != expected_classification:
            raise ValueError(f"stale-claim source classification differs: {path}")
        recorded[path] = entry
    if set(recorded) != set(current):
        raise ValueError("stale-claim source inventory differs from live source tree")
    if evidence.get("inventory_count") != len(current):
        raise ValueError("stale-claim inventory count differs")
    for relative, path in current.items():
        if recorded[relative].get("sha256") != sha256_path(path):
            raise ValueError(f"stale-claim source SHA-256 differs: {relative}")
    hits = evidence.get("hits")
    if not isinstance(hits, list):
        raise ValueError("stale-claim scan lacks hit records")
    for hit in hits:
        if not isinstance(hit, Mapping):
            raise ValueError("stale-claim hit is malformed")
        path = str(hit.get("path", "")).replace("\\", "/")
        if path not in recorded:
            raise ValueError("stale-claim hit references a non-inventoried source")
        disposition = hit.get("disposition")
        classification = recorded[path]["classification"]
        if disposition == "immutable_history" and classification != "immutable_history":
            raise ValueError("active-current stale claim cannot use historical disposition")
        if disposition not in {
            "immutable_history",
            "current_final_test_hash",
            "historical_model_snapshot",
            "unclassified_current",
        }:
            raise ValueError("stale-claim hit has an unknown disposition")
    recomputed_hits, recomputed_unresolved = _recompute_stale_claim_hits(
        current=current, recorded=recorded
    )
    if hits != recomputed_hits:
        raise ValueError("stale-claim hit set differs from live source recomputation")
    if evidence.get("unclassified_current_hits") != recomputed_unresolved:
        raise ValueError(
            "stale-claim unresolved set differs from live source recomputation"
        )
    if recomputed_unresolved:
        raise ValueError("stale-claim scan has unclassified current hits")
    return evidence


def _requirements_are_closed(requirements_path: Path) -> None:
    text = Path(requirements_path).read_text(encoding="utf-8")
    for requirement in ("JUDGE-01", "JUDGE-02", "JUDGE-03"):
        if not re.search(
            rf"^- \[[xX]\] \*\*{re.escape(requirement)}\*\*:", text, re.MULTILINE
        ):
            raise ValueError(f"{requirement} checklist is not complete")
        if not re.search(
            rf"^\| {re.escape(requirement)} \| Phase 39 \| Complete \|$",
            text,
            re.MULTILINE,
        ):
            raise ValueError(f"{requirement} traceability is not complete")
    for requirement in ("REPORT-03", "REPORT-04", "REPORT-05", "REPORT-06"):
        if re.search(
            rf"^- \[[xX]\] \*\*{re.escape(requirement)}\*\*:", text, re.MULTILINE
        ):
            raise ValueError(f"Phase 42 requirement was completed prematurely: {requirement}")


def validate_canonical_final_release(
    *, repo_root: Path, splits_dir: Path | None = None
) -> dict[str, Any]:
    """Run judge_merge's complete promoted-release validator on canonical evidence."""
    root = Path(repo_root).resolve()
    return validate_final_release(
        splits_dir=(root / "data/splits" if splits_dir is None else Path(splits_dir)),
        manifest_path=root / "data/manifests/manifest.json",
        judge_results_path=root / "data/processed/codex-judge-pass.jsonl",
        merged_path=root / "data/processed/judge-merged.jsonl",
        summary_path=root / "data/processed/judge-summary.json",
        provenance_path=root
        / "data/processed/phase39-final-judge-provenance.jsonl",
        convergence_path=root / "data/processed/phase39-semantic-convergence.json",
        candidate_dir=root / "data/processed/phase39-mislabel-candidate",
        carry_path=root / "data/processed/phase39-final-evidence/carry.jsonl",
        fresh_results_path=root / "data/processed/codex-final-delta-judge.jsonl",
        backup_dir=root / "data/backup/pre-phase39-mislabel-triage/processed",
        repo_root=root,
    )


def verify_report_closure(
    *,
    manifest_path: Path,
    judge_summary_path: Path,
    human_summary_path: Path,
    report_note_path: Path,
    compile_evidence_path: Path,
    scan_evidence_path: Path,
    requirements_path: Path,
) -> dict[str, Any]:
    """Fail-closed final gate over release, human, report, build, and scan proof."""
    manifest_path = Path(manifest_path).resolve()
    repo_root = manifest_path.parents[2]
    canonical_manifest = (repo_root / "data/manifests/manifest.json").resolve()
    if manifest_path != canonical_manifest:
        raise ValueError("closure requires the canonical repository manifest")
    canonical_judge_summary = (repo_root / "data/processed/judge-summary.json").resolve()
    if Path(judge_summary_path).resolve() != canonical_judge_summary:
        raise ValueError("closure requires the canonical final judge summary")
    canonical_requirements = (repo_root / ".planning/REQUIREMENTS.md").resolve()
    if Path(requirements_path).resolve() != canonical_requirements:
        raise ValueError("closure requires canonical repository .planning/REQUIREMENTS.md")
    release_validation = validate_canonical_final_release(repo_root=repo_root)
    manifest = _load_json_object(manifest_path, context="final manifest")
    release = manifest.get("phase39_final_release")
    if not isinstance(release, Mapping) or release.get("status") != "promoted":
        raise ValueError("final release is not promoted")
    convergence = release.get("semantic_convergence")
    if not isinstance(convergence, Mapping) or convergence.get("unresolved_count") != 0:
        raise ValueError("final release has unresolved semantic rows")

    expected_human = build_final_review_summary(
        sheet_path=repo_root / _DEFAULT_FINAL_SHEET,
        merged_path=repo_root / "data/processed/judge-merged.jsonl",
        provenance_path=repo_root
        / "data/processed/phase39-final-judge-provenance.jsonl",
        manifest_path=manifest_path,
        judge_summary_path=Path(judge_summary_path),
        convergence_path=repo_root
        / "data/processed/phase39-semantic-convergence.json",
        triage_path=repo_root / _DEFAULT_FINAL_TRIAGE,
        historical_sheet_path=repo_root / _DEFAULT_HISTORICAL_SHEET,
        historical_merged_path=repo_root / _DEFAULT_HISTORICAL_MERGED,
    )
    human = _load_json_object(human_summary_path, context="final human summary")
    if human != expected_human:
        raise ValueError("final human summary differs from recomputed evidence")
    judge = _load_json_object(judge_summary_path, context="final judge summary")
    expected_note = render_report_note(manifest=manifest, judge=judge, human=human)
    if Path(report_note_path).read_text(encoding="utf-8") != expected_note:
        raise ValueError("report note differs from recomputed evidence")
    compile_evidence = validate_report_compile_evidence(
        evidence_path=Path(compile_evidence_path),
        repo_root=repo_root,
        report_note_path=Path(report_note_path),
    )
    scan_evidence = validate_stale_claim_scan(
        evidence_path=Path(scan_evidence_path), repo_root=repo_root
    )
    _requirements_are_closed(Path(requirements_path))
    return {
        "schema_version": "phase39-report-closure-v1",
        "status": "closed",
        "manifest_sha256": sha256_path(manifest_path),
        "judge_summary_sha256": sha256_path(Path(judge_summary_path)),
        "human_summary_sha256": sha256_path(Path(human_summary_path)),
        "report_note_sha256": sha256_path(Path(report_note_path)),
        "compile_evidence_sha256": sha256_path(Path(compile_evidence_path)),
        "scan_evidence_sha256": sha256_path(Path(scan_evidence_path)),
        "compile_status": compile_evidence["status"],
        "scan_status": scan_evidence["status"],
        "requirements": ["JUDGE-01", "JUDGE-02", "JUDGE-03"],
        "release_validation": release_validation,
    }


def _legacy_main(argv: Sequence[str]) -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Select a stratified pass/fail sample from judge_merge.py's merged "
            "output. Historical Phase 39 paths are immutable; choose a new output."
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
    args = parser.parse_args(list(argv))

    if not args.merged_path.exists():
        raise FileNotFoundError(
            f"{args.merged_path} does not exist yet. Run judge_merge.py first "
            "(python -m src.data_pipeline.judge_merge), then re-run this tool."
        )

    protected = {
        (Path.cwd() / _FINAL_PHASE_RELATIVE / name).resolve()
        for name in _PROTECTED_HISTORICAL_NAMES
    }
    if args.output.resolve() in protected:
        raise ValueError(
            "the historical Phase 39 review paths are immutable; choose a new --output"
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


def _add_final_evidence_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--merged", type=Path, default=Path("data/processed/judge-merged.jsonl")
    )
    parser.add_argument(
        "--provenance",
        type=Path,
        default=Path("data/processed/phase39-final-judge-provenance.jsonl"),
    )
    parser.add_argument(
        "--manifest", type=Path, default=Path("data/manifests/manifest.json")
    )
    parser.add_argument(
        "--historical-sheet", type=Path, default=_DEFAULT_HISTORICAL_SHEET
    )
    parser.add_argument(
        "--historical-merged", type=Path, default=_DEFAULT_HISTORICAL_MERGED
    )


def _final_cli(argv: Sequence[str]) -> None:
    parser = argparse.ArgumentParser(
        description="Generate or strictly validate the promoted-final Phase 39 review."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser(
        "generate-final", description="Generate the pending 100-row final review sheet."
    )
    _add_final_evidence_arguments(generate)
    generate.add_argument("--output", type=Path, default=_DEFAULT_FINAL_SHEET)
    generate.add_argument("--sample-size", type=int, default=100)
    generate.add_argument("--salt", default=FINAL_SAMPLE_SALT)

    validate = subparsers.add_parser(
        "validate-final", description="Read-only validation of the final review sheet."
    )
    _add_final_evidence_arguments(validate)
    validate.add_argument("--sheet", type=Path, default=_DEFAULT_FINAL_SHEET)
    mode = validate.add_mutually_exclusive_group(required=True)
    mode.add_argument("--allow-pending", action="store_true")
    mode.add_argument("--require-complete", action="store_true")
    validate.add_argument(
        "--check-only",
        action="store_true",
        required=True,
        help="Required declaration that validation must not write any artifact.",
    )
    importer = subparsers.add_parser(
        "import-final-triage",
        description=(
            "Atomically port the locked human FINALtriage decisions into the "
            "canonical pending review sheet."
        ),
    )
    _add_final_evidence_arguments(importer)
    importer.add_argument("--triage", type=Path, default=_DEFAULT_FINAL_TRIAGE)
    importer.add_argument("--sheet", type=Path, default=_DEFAULT_FINAL_SHEET)
    finalizer = subparsers.add_parser(
        "finalize-review",
        description="Finalize the completed review and generate report-bound evidence.",
    )
    _add_final_evidence_arguments(finalizer)
    finalizer.add_argument("--sheet", type=Path, default=_DEFAULT_FINAL_SHEET)
    finalizer.add_argument("--triage", type=Path, default=_DEFAULT_FINAL_TRIAGE)
    finalizer.add_argument(
        "--judge-summary",
        type=Path,
        default=Path("data/processed/judge-summary.json"),
    )
    finalizer.add_argument(
        "--convergence",
        type=Path,
        default=Path("data/processed/phase39-semantic-convergence.json"),
    )
    finalizer.add_argument(
        "--output",
        type=Path,
        default=_FINAL_PHASE_RELATIVE / "39-final-manual-review-summary.json",
    )
    finalizer.add_argument(
        "--report-note",
        type=Path,
        default=_FINAL_PHASE_RELATIVE / "39-REPORT-NOTE.md",
    )
    closure = subparsers.add_parser(
        "verify-report-closure",
        description="Fail-closed Phase 39 report and requirement evidence gate.",
    )
    closure.add_argument("--manifest", type=Path, required=True)
    closure.add_argument("--judge-summary", type=Path, required=True)
    closure.add_argument("--human-summary", type=Path, required=True)
    closure.add_argument("--report-note", type=Path, required=True)
    closure.add_argument("--compile-evidence", type=Path, required=True)
    closure.add_argument("--scan-evidence", type=Path, required=True)
    closure.add_argument("--requirements", type=Path, required=True)
    args = parser.parse_args(list(argv))

    if args.command == "generate-final":
        if args.sample_size != 100:
            raise ValueError("the final Phase 39 review sample size is locked to 100")
        if args.salt != FINAL_SAMPLE_SALT:
            raise ValueError(
                f"the final Phase 39 review salt is locked to {FINAL_SAMPLE_SALT!r}"
            )
        report = generate_final_review_sheet(
            merged_path=args.merged,
            provenance_path=args.provenance,
            manifest_path=args.manifest,
            historical_sheet_path=args.historical_sheet,
            historical_merged_path=args.historical_merged,
            output_path=args.output,
            sample_size=args.sample_size,
            salt=args.salt,
        )
    elif args.command == "validate-final":
        report = validate_final_review_sheet(
            sheet_path=args.sheet,
            merged_path=args.merged,
            provenance_path=args.provenance,
            manifest_path=args.manifest,
            historical_sheet_path=args.historical_sheet,
            historical_merged_path=args.historical_merged,
            allow_pending=args.allow_pending,
            require_complete=args.require_complete,
        )
    elif args.command == "import-final-triage":
        report = import_final_triage_decisions(
            triage_path=args.triage,
            sheet_path=args.sheet,
            merged_path=args.merged,
            provenance_path=args.provenance,
            manifest_path=args.manifest,
            historical_sheet_path=args.historical_sheet,
            historical_merged_path=args.historical_merged,
        )
    elif args.command == "finalize-review":
        report = finalize_review(
            sheet_path=args.sheet,
            merged_path=args.merged,
            provenance_path=args.provenance,
            manifest_path=args.manifest,
            judge_summary_path=args.judge_summary,
            convergence_path=args.convergence,
            triage_path=args.triage,
            historical_sheet_path=args.historical_sheet,
            historical_merged_path=args.historical_merged,
            output_path=args.output,
            report_note_path=args.report_note,
        )
    else:
        report = verify_report_closure(
            manifest_path=args.manifest,
            judge_summary_path=args.judge_summary,
            human_summary_path=args.human_summary,
            report_note_path=args.report_note,
            compile_evidence_path=args.compile_evidence,
            scan_evidence_path=args.scan_evidence,
            requirements_path=args.requirements,
        )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))


def main(argv: Sequence[str] | None = None) -> None:
    cli_args = list(sys.argv[1:] if argv is None else argv)
    if cli_args and cli_args[0] in {
        "generate-final",
        "validate-final",
        "import-final-triage",
        "finalize-review",
        "verify-report-closure",
    }:
        _final_cli(cli_args)
    else:
        _legacy_main(cli_args)


if __name__ == "__main__":
    main()
