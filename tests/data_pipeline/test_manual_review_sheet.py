"""Tests for the Phase 39 stratified manual-check review sheet generator.

Proves manual_review_sheet.py against a realistic merged-dataset fixture
shaped exactly like judge_merge.py's merge_judge_results() output.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from src.data_pipeline.manual_review_sheet import (
    FINAL_SAMPLE_SALT,
    _final_human_regions,
    _load_merged,
    _recompute_stale_claim_hits,
    _verified_pdf_page_count,
    annotate_exact_human_carries,
    build_final_review_summary,
    build_historical_human_carry_index,
    finalize_review,
    generate_final_review_sheet,
    import_final_triage_decisions,
    load_final_evidence,
    select_final_stratified_sample,
    select_stratified_sample,
    parse_final_triage_decisions,
    render_report_note,
    validate_canonical_final_release,
    validate_final_review_sheet,
    validate_report_compile_evidence,
    validate_stale_claim_scan,
    verify_report_closure,
    write_review_sheet,
)
from src.data_pipeline.judge_merge import dataset_record_digest, judge_evidence_digest

_DIMENSIONS = (
    "realism",
    "label_correctness",
    "code_switch_naturalness",
    "risk_tier_correctness",
    "suspicious_span_accuracy",
)


def _merged_row(
    split: str,
    row_index: int,
    judge_pass: bool,
    *,
    seed_id: str | None = None,
    text: str | None = None,
    label: str = "bank_impersonation",
    risk_tier: str = "high-risk",
    score: int = 4,
) -> dict[str, Any]:
    row = {
        "text": text or f"Tin nhan {split} so {row_index} du dai hop le de test sheet.",
        "label": label,
        "risk_tier": risk_tier,
        "suspicious_spans": [],
        "xai_explanation": "Giai thich du dai cho ban ghi kiem thu sheet gop judge that.",
        "source": "synthetic_claude",
        "seed_id": seed_id or f"seed_{split}_{row_index}",
        "split": split,
        "row_index": row_index,
        "judge_pass": judge_pass,
        "judge_reason": "Fixture reason for review sheet test.",
        "recomputed_pass": judge_pass,
    }
    for dim in _DIMENSIONS:
        row[dim] = score
    return row


def _make_merged_fixture(pass_count: int, fail_count: int) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    for i in range(pass_count):
        merged.append(_merged_row("train", i, True, seed_id=f"seed_pass_{i}"))
    for i in range(fail_count):
        merged.append(
            _merged_row("val", i, False, seed_id=f"seed_fail_{i}", score=2)
        )
    return merged


# --- select_stratified_sample ----------------------------------------------


def test_select_stratified_sample_splits_evenly_when_both_pools_large_enough():
    merged = _make_merged_fixture(pass_count=12, fail_count=8)

    sample, composition = select_stratified_sample(merged, sample_size=10)

    assert len(sample) == 10
    pass_rows = [row for row in sample if row["judge_pass"]]
    fail_rows = [row for row in sample if not row["judge_pass"]]
    assert len(pass_rows) == 5
    assert len(fail_rows) == 5
    assert composition == {
        "sample_size": 10,
        "pass_count": 5,
        "fail_count": 5,
        "source_total": 20,
        "source_pass_total": 12,
        "source_fail_total": 8,
    }


def test_select_stratified_sample_never_pads_fail_pool_past_real_size():
    merged = _make_merged_fixture(pass_count=17, fail_count=3)

    sample, composition = select_stratified_sample(merged, sample_size=10)

    fail_rows = [row for row in sample if not row["judge_pass"]]
    pass_rows = [row for row in sample if row["judge_pass"]]
    assert len(fail_rows) == 3
    assert len(pass_rows) == 7
    assert len(sample) == 10
    assert composition["fail_count"] == 3
    assert composition["pass_count"] == 7


def test_select_stratified_sample_is_deterministic_across_calls():
    merged = _make_merged_fixture(pass_count=12, fail_count=8)

    sample_1, _ = select_stratified_sample(merged, sample_size=10, salt="fixed-salt")
    sample_2, _ = select_stratified_sample(merged, sample_size=10, salt="fixed-salt")

    ids_1 = [(row["split"], row["row_index"]) for row in sample_1]
    ids_2 = [(row["split"], row["row_index"]) for row in sample_2]
    assert ids_1 == ids_2


def test_select_stratified_sample_returns_everything_when_below_sample_size():
    merged = _make_merged_fixture(pass_count=4, fail_count=2)

    sample, composition = select_stratified_sample(merged, sample_size=10)

    assert len(sample) == 6
    assert composition["sample_size"] == 6
    assert composition["pass_count"] == 4
    assert composition["fail_count"] == 2


# --- write_review_sheet -----------------------------------------------------


def test_write_review_sheet_renders_one_section_per_row(tmp_path: Path):
    merged = _make_merged_fixture(pass_count=3, fail_count=2)
    sample, composition = select_stratified_sample(merged, sample_size=10)
    output_path = tmp_path / "review-sheet.md"

    write_review_sheet(sample, composition, output_path)

    content = output_path.read_text(encoding="utf-8")
    assert content.count("## Example") == 5
    assert content.count("[ ] PASS") == 5
    assert content.count("[ ] FAIL") == 5
    assert content.count("**Notes:**") == 5
    for row in sample:
        assert row["text"] in content
        assert row["label"] in content
        assert row["risk_tier"] in content
        assert row["judge_reason"] in content
        verdict_label = "PASS" if row["judge_pass"] else "FAIL"
        assert f"Codex judge verdict:** {verdict_label}" in content


def test_write_review_sheet_preserves_embedded_newlines_in_blockquote(tmp_path: Path):
    merged = [
        _merged_row(
            "train", 0, True, text="Dong thu nhat.\nDong thu hai.\nDong thu ba."
        )
    ]
    sample, composition = select_stratified_sample(merged, sample_size=10)
    output_path = tmp_path / "review-sheet.md"

    write_review_sheet(sample, composition, output_path)

    content = output_path.read_text(encoding="utf-8")
    assert "> Dong thu nhat." in content
    assert "> Dong thu hai." in content
    assert "> Dong thu ba." in content


# --- _load_merged ------------------------------------------------------------


def test_load_merged_raises_on_missing_required_key(tmp_path: Path):
    row = _merged_row("train", 0, True)
    del row["judge_reason"]
    path = tmp_path / "merged.jsonl"
    path.write_text(json.dumps(row) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match=r"line 1.*judge_reason"):
        _load_merged(path)


def test_load_merged_raises_on_malformed_json(tmp_path: Path):
    path = tmp_path / "merged.jsonl"
    path.write_text("{not valid json\n", encoding="utf-8")

    with pytest.raises(ValueError, match=r"line 1.*not valid JSON"):
        _load_merged(path)


def test_load_merged_accepts_well_formed_rows(tmp_path: Path):
    row = _merged_row("train", 0, True)
    path = tmp_path / "merged.jsonl"
    path.write_text(json.dumps(row) + "\n", encoding="utf-8")

    rows = _load_merged(path)

    assert len(rows) == 1
    assert rows[0]["seed_id"] == row["seed_id"]


# --- end-to-end --------------------------------------------------------------


def test_end_to_end_sample_then_write_matches_header_composition(tmp_path: Path):
    merged = _make_merged_fixture(pass_count=30, fail_count=15)
    sample, composition = select_stratified_sample(merged, sample_size=20)
    output_path = tmp_path / "39-manual-review-sheet.md"

    write_review_sheet(sample, composition, output_path)

    content = output_path.read_text(encoding="utf-8")

    header_match = re.search(
        r"Sample size: (\d+) \((\d+) judge-pass, (\d+) judge-fail\)", content
    )
    assert header_match is not None
    header_sample_size = int(header_match.group(1))
    header_pass_count = int(header_match.group(2))
    header_fail_count = int(header_match.group(3))

    actual_pair_count = content.count("[ ] PASS")
    assert actual_pair_count == content.count("[ ] FAIL")
    assert header_sample_size == actual_pair_count
    assert header_pass_count + header_fail_count == header_sample_size
    assert header_sample_size == composition["sample_size"]
    assert header_pass_count == composition["pass_count"]
    assert header_fail_count == composition["fail_count"]


# --- promoted-final-snapshot lane ------------------------------------------


_LABELS = (
    "bank_impersonation",
    "benign",
    "task_scam",
    "zalo_social_engineering",
)
_ORIGINS = ("carried_forward_exact_record", "fresh_final_delta")


def _provenance_row(row: dict[str, Any], origin: str) -> dict[str, Any]:
    carried = origin == "carried_forward_exact_record"
    return {
        "schema_version": "phase39-final-judge-provenance-v1",
        "split": row["split"],
        "row_index": row["row_index"],
        "seed_id": row["seed_id"],
        "record_digest": dataset_record_digest(row),
        "evidence_digest": judge_evidence_digest(row),
        "verdict_origin": origin,
        "source_iteration": None if carried else 0,
        "source_path": "fixture-evidence.jsonl",
        "source_sha256": "a" * 64,
        "historical_split": row["split"] if carried else None,
        "historical_row_index": row["row_index"] if carried else None,
    }


def _final_evidence_fixture(rows_per_stratum: int = 8) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    row_index = 0
    for label in _LABELS:
        for judge_pass in (False, True):
            for origin in _ORIGINS:
                for _ in range(rows_per_stratum):
                    score = 4 if judge_pass else 2
                    row = _merged_row(
                        "train",
                        row_index,
                        judge_pass,
                        seed_id=f"seed_final_{row_index}",
                        text=(
                            f"Noi dung kiem thu cuoi cung so {row_index} du dai, "
                            "ro rang va khong trung lap."
                        ),
                        label=label,
                        risk_tier="benign" if label == "benign" else "high-risk",
                        score=score,
                    )
                    provenance = _provenance_row(row, origin)
                    rows.append(
                        {
                            **row,
                            "record_digest": provenance["record_digest"],
                            "evidence_digest": provenance["evidence_digest"],
                            "judge_origin": origin,
                            "provenance": provenance,
                        }
                    )
                    row_index += 1
    return rows


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def _write_historical_sheet(
    path: Path,
    rows: list[dict[str, Any]],
    verdict_lines: list[str],
) -> None:
    composition = {
        "sample_size": len(rows),
        "pass_count": sum(bool(row["judge_pass"]) for row in rows),
        "fail_count": sum(not bool(row["judge_pass"]) for row in rows),
        "source_total": len(rows),
        "source_pass_total": sum(bool(row["judge_pass"]) for row in rows),
        "source_fail_total": sum(not bool(row["judge_pass"]) for row in rows),
    }
    write_review_sheet(rows, composition, path)
    content = path.read_text(encoding="utf-8")
    for replacement in verdict_lines:
        content = content.replace(
            "**Your verdict:** [ ] PASS   [ ] FAIL", replacement, 1
        )
    path.write_text(content, encoding="utf-8")


def _carry_for(
    current: dict[str, Any],
    historical: dict[str, Any],
    tmp_path: Path,
    verdict_line: str = "**Your verdict:** [x] PASS   [ ] FAIL",
) -> dict[str, Any]:
    sheet = tmp_path / "historical-sheet.md"
    _write_historical_sheet(sheet, [historical], [verdict_line])
    index, _ = build_historical_human_carry_index(sheet, [historical])
    item = {
        **current,
        "record_digest": dataset_record_digest(current),
        "evidence_digest": judge_evidence_digest(current),
        "judge_origin": "carried_forward_exact_record",
    }
    return annotate_exact_human_carries([item], index)[0]


def test_final_sampler_is_exactly_100_deterministic_and_multi_axis():
    evidence = _final_evidence_fixture(rows_per_stratum=8)

    sample_1, composition_1 = select_final_stratified_sample(
        evidence, sample_size=100, salt=FINAL_SAMPLE_SALT
    )
    sample_2, composition_2 = select_final_stratified_sample(
        evidence, sample_size=100, salt=FINAL_SAMPLE_SALT
    )

    assert len(sample_1) == 100
    assert len({row["record_digest"] for row in sample_1}) == 100
    assert [row["record_digest"] for row in sample_1] == [
        row["record_digest"] for row in sample_2
    ]
    assert composition_1 == composition_2
    assert {row["label"] for row in sample_1} == set(_LABELS)
    assert {bool(row["judge_pass"]) for row in sample_1} == {False, True}
    assert {row["judge_origin"] for row in sample_1} == set(_ORIGINS)
    assert set(composition_1["sample_strata"]) == set(
        composition_1["source_strata"]
    )


def test_final_sampler_fills_after_a_sparse_cross_stratum():
    evidence = _final_evidence_fixture(rows_per_stratum=8)
    sparse_key = ("benign", "fail", "fresh_final_delta")
    sparse = [
        row
        for row in evidence
        if (row["label"], "pass" if row["judge_pass"] else "fail", row["judge_origin"])
        == sparse_key
    ]
    evidence = [
        row
        for row in evidence
        if (row["label"], "pass" if row["judge_pass"] else "fail", row["judge_origin"])
        != sparse_key
    ] + sparse[:1]

    sample, composition = select_final_stratified_sample(evidence, sample_size=100)

    assert len(sample) == 100
    assert composition["sample_strata"]["|".join(sparse_key)] == 1
    assert any(row["record_digest"] == sparse[0]["record_digest"] for row in sample)


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("text", "Noi dung da thay doi hoan toan va van du dai de kiem thu."),
        ("label", "task_scam"),
        ("risk_tier", "suspicious"),
        ("suspicious_spans", ["Tin nhan"]),
        ("xai_explanation", "Giai thich da thay doi va van du dai theo schema."),
        ("source", "synthetic_gemini"),
        ("seed_id", "seed_changed"),
    ],
)
def test_exact_human_carry_rejects_each_record_field_change(
    field: str, replacement: Any, tmp_path: Path
):
    historical = _merged_row(
        "train", 0, True, text="Tin nhan goc du dai de kiem tra carry chinh xac."
    )
    current = deepcopy(historical)
    current[field] = replacement

    result = _carry_for(current, historical, tmp_path)

    assert result["human_verdict"] is None
    assert result["human_verdict_origin"] == "pending_final_human"


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("realism", 5),
        ("label_correctness", 5),
        ("code_switch_naturalness", 5),
        ("risk_tier_correctness", 5),
        ("suspicious_span_accuracy", 5),
        ("judge_pass", False),
        ("judge_reason", "Judge reason changed while remaining non-empty."),
    ],
)
def test_exact_human_carry_rejects_each_evidence_field_change(
    field: str, replacement: Any, tmp_path: Path
):
    historical = _merged_row("train", 0, True)
    current = deepcopy(historical)
    current[field] = replacement

    result = _carry_for(current, historical, tmp_path)

    assert result["human_verdict"] is None
    assert result["human_verdict_origin"] == "pending_final_human"


def test_exact_human_carry_accepts_one_identical_record_and_evidence(tmp_path: Path):
    historical = _merged_row("train", 0, True)

    result = _carry_for(deepcopy(historical), historical, tmp_path)

    assert result["human_verdict"] == "PASS"
    assert result["human_verdict_origin"] == "carried_forward_exact_evidence"


@pytest.mark.parametrize(
    "verdict_line",
    [
        "**Your verdict:** [ ] PASS   [ ] FAIL",
        "**Your verdict:** [x] PASS   [x] FAIL",
        "**Your verdict:** [okok] PASS   [ ] FAIL",
        "**Your verdict:** x[x] PASS   [ ] FAIL",
    ],
)
def test_historical_blank_dual_unknown_or_malformed_marks_do_not_carry(
    verdict_line: str, tmp_path: Path
):
    historical = _merged_row("train", 0, True)

    result = _carry_for(
        deepcopy(historical), historical, tmp_path, verdict_line=verdict_line
    )

    assert result["human_verdict"] is None


def test_changed_stale_zalo_record_does_not_carry(tmp_path: Path):
    historical = _merged_row(
        "train",
        0,
        False,
        label="zalo_social_engineering",
        text="Nguoi ke chuyen mo ta mot tin nhan Zalo thay vi dua tin nhan truc tiep.",
        score=2,
    )
    current = deepcopy(historical)
    current["text"] = "Anh oi ket ban Zalo voi em qua ma QR nay de nhan ho tro nhe."

    result = _carry_for(current, historical, tmp_path)

    assert result["human_verdict"] is None


def _write_final_bundle(
    tmp_path: Path,
    *,
    rows_per_stratum: int = 8,
    multiline: bool = False,
) -> tuple[Path, Path, Path, Path, Path, dict[str, Path]]:
    evidence = _final_evidence_fixture(rows_per_stratum=rows_per_stratum)
    if multiline:
        pre_sample, _ = select_final_stratified_sample(evidence, sample_size=100)
        target_coordinate = (pre_sample[0]["split"], pre_sample[0]["row_index"])
        target = next(
            row
            for row in evidence
            if (row["split"], row["row_index"]) == target_coordinate
        )
        target["text"] = "Dong mot cua thong diep.\nDong hai cua thong diep."
        target["suspicious_spans"] = [
            "Dong mot cua thong diep.\nDong hai cua thong diep."
        ]
        target["judge_reason"] = "Ly do dong mot.\nLy do dong hai."
        target["record_digest"] = dataset_record_digest(target)
        target["evidence_digest"] = judge_evidence_digest(target)
        target["provenance"] = _provenance_row(
            target, target["judge_origin"]
        )
    sample, _ = select_final_stratified_sample(evidence, sample_size=100)
    historical = [deepcopy(sample[0])]
    for key in ("record_digest", "evidence_digest", "judge_origin", "provenance"):
        historical[0].pop(key, None)

    merged_path = tmp_path / "judge-merged.jsonl"
    provenance_path = tmp_path / "provenance.jsonl"
    historical_merged_path = tmp_path / "historical-merged.jsonl"
    historical_sheet_path = tmp_path / "historical-sheet.md"
    final_sheet_path = tmp_path / "final-sheet.md"
    protected_paths = {
        "39-manual-review-sheet.md": historical_sheet_path,
        "39-mislabel-triage-sheet.md": tmp_path / "triage-sheet.md",
        "MISLABEL triage.md": tmp_path / "compact-triage.md",
    }
    _write_jsonl(
        merged_path,
        [
            {key: value for key, value in row.items() if key not in {"record_digest", "evidence_digest", "judge_origin", "provenance"}}
            for row in evidence
        ],
    )
    _write_jsonl(provenance_path, [row["provenance"] for row in evidence])
    _write_jsonl(historical_merged_path, historical)
    _write_historical_sheet(
        historical_sheet_path,
        historical,
        ["**Your verdict:** [x] PASS   [ ] FAIL"],
    )
    protected_paths["39-mislabel-triage-sheet.md"].write_text(
        "historical triage\n", encoding="utf-8"
    )
    protected_paths["MISLABEL triage.md"].write_text(
        "authoritative compact triage\n", encoding="utf-8"
    )

    from hashlib import sha256

    def digest(path: Path) -> str:
        return sha256(path.read_bytes()).hexdigest()

    manifest_path = tmp_path / "manifest.json"
    manifest = {
        "phase39_final_release": {
            "schema_version": "phase39-final-release-v1",
            "status": "promoted",
            "historical_judge_backup": {
                "judge-merged.jsonl": {
                    "path": str(historical_merged_path),
                    "sha256": digest(historical_merged_path),
                    "bytes": historical_merged_path.stat().st_size,
                }
            },
            "judge_evidence": {
                "total_records": len(evidence),
                "artifacts": {
                    "judge_merged": {
                        "path": str(merged_path),
                        "sha256": digest(merged_path),
                        "records": len(evidence),
                    },
                    "judge_provenance": {
                        "path": str(provenance_path),
                        "sha256": digest(provenance_path),
                        "records": len(evidence),
                    },
                },
            },
            "protected_human_artifacts": {
                name: digest(path) for name, path in protected_paths.items()
            },
        }
    }
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return (
        merged_path,
        provenance_path,
        manifest_path,
        historical_merged_path,
        final_sheet_path,
        protected_paths,
    )


def test_final_sheet_generation_carries_exact_one_and_validates_pending(
    tmp_path: Path,
):
    (
        merged_path,
        provenance_path,
        manifest_path,
        historical_merged_path,
        final_sheet_path,
        protected_paths,
    ) = _write_final_bundle(tmp_path)
    old_hashes = {name: path.read_bytes() for name, path in protected_paths.items()}

    generated = generate_final_review_sheet(
        merged_path=merged_path,
        provenance_path=provenance_path,
        manifest_path=manifest_path,
        historical_sheet_path=protected_paths["39-manual-review-sheet.md"],
        historical_merged_path=historical_merged_path,
        output_path=final_sheet_path,
        protected_paths=protected_paths,
    )
    validated = validate_final_review_sheet(
        sheet_path=final_sheet_path,
        merged_path=merged_path,
        provenance_path=provenance_path,
        manifest_path=manifest_path,
        historical_sheet_path=protected_paths["39-manual-review-sheet.md"],
        historical_merged_path=historical_merged_path,
        protected_paths=protected_paths,
        allow_pending=True,
    )

    assert generated["sample_size"] == validated["sample_size"] == 100
    assert generated["carried_count"] == validated["carried_count"] == 1
    assert generated["pending_count"] == validated["pending_count"] == 99
    assert final_sheet_path.read_text(encoding="utf-8").count(
        "## Final Example"
    ) == 100
    assert "human_verdict_origin=carried_forward_exact_evidence" in final_sheet_path.read_text(
        encoding="utf-8"
    )
    assert "human_verdict_origin=pending_final_human" in final_sheet_path.read_text(
        encoding="utf-8"
    )
    assert {name: path.read_bytes() for name, path in protected_paths.items()} == old_hashes


def test_final_completion_validator_is_read_only_and_requires_all_100(
    tmp_path: Path,
):
    bundle = _write_final_bundle(tmp_path)
    merged, provenance, manifest, historical_merged, sheet, protected = bundle
    generate_final_review_sheet(
        merged_path=merged,
        provenance_path=provenance,
        manifest_path=manifest,
        historical_sheet_path=protected["39-manual-review-sheet.md"],
        historical_merged_path=historical_merged,
        output_path=sheet,
        protected_paths=protected,
    )
    with pytest.raises(ValueError, match="pending"):
        validate_final_review_sheet(
            sheet_path=sheet,
            merged_path=merged,
            provenance_path=provenance,
            manifest_path=manifest,
            historical_sheet_path=protected["39-manual-review-sheet.md"],
            historical_merged_path=historical_merged,
            protected_paths=protected,
            require_complete=True,
        )

    completed = sheet.read_text(encoding="utf-8").replace(
        "**Your verdict:** [ ] PASS   [ ] FAIL",
        "**Your verdict:** [x] PASS   [ ] FAIL",
    )
    sheet.write_text(completed, encoding="utf-8")
    before = sheet.read_bytes()
    report = validate_final_review_sheet(
        sheet_path=sheet,
        merged_path=merged,
        provenance_path=provenance,
        manifest_path=manifest,
        historical_sheet_path=protected["39-manual-review-sheet.md"],
        historical_merged_path=historical_merged,
        protected_paths=protected,
        require_complete=True,
    )
    assert report["completed_count"] == 100
    assert sheet.read_bytes() == before


@pytest.mark.parametrize(
    "mutation",
    [
        "evidence",
        "manifest",
        "count_99",
        "count_101",
        "header",
        "suffix",
        "pending_marked",
        "unknown_token",
        "dual_mark",
        "fail_without_note",
    ],
)
def test_final_validator_rejects_tampering_drift_and_wrong_section_count(
    mutation: str, tmp_path: Path
):
    bundle = _write_final_bundle(tmp_path)
    merged, provenance, manifest, historical_merged, sheet, protected = bundle
    generate_final_review_sheet(
        merged_path=merged,
        provenance_path=provenance,
        manifest_path=manifest,
        historical_sheet_path=protected["39-manual-review-sheet.md"],
        historical_merged_path=historical_merged,
        output_path=sheet,
        protected_paths=protected,
    )
    if mutation == "evidence":
        sheet.write_text(
            sheet.read_text(encoding="utf-8").replace(
                "Fixture reason for review sheet test.", "Tampered judge reason.", 1
            ),
            encoding="utf-8",
        )
    elif mutation == "manifest":
        manifest.write_text(manifest.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    elif mutation == "count_99":
        text = sheet.read_text(encoding="utf-8")
        last = text.rfind("## Final Example")
        sheet.write_text(text[:last], encoding="utf-8")
    elif mutation == "count_101":
        text = sheet.read_text(encoding="utf-8")
        first = text.index("## Final Example")
        second = text.index("## Final Example", first + 1)
        sheet.write_text(text + "\n" + text[first:second], encoding="utf-8")
    elif mutation == "header":
        sheet.write_text(
            sheet.read_text(encoding="utf-8").replace(
                "# Phase 39 Final-Snapshot Manual Quality Review",
                "# Altered review heading",
                1,
            ),
            encoding="utf-8",
        )
    elif mutation == "suffix":
        sheet.write_text(
            sheet.read_text(encoding="utf-8").replace(
                "<!-- END PHASE39 HUMAN REVIEW -->", "<!-- altered end -->", 1
            ),
            encoding="utf-8",
        )
    elif mutation == "pending_marked":
        sheet.write_text(
            sheet.read_text(encoding="utf-8").replace(
                "**Your verdict:** [ ] PASS   [ ] FAIL",
                "**Your verdict:** [x] PASS   [ ] FAIL",
                1,
            ),
            encoding="utf-8",
        )
    elif mutation == "unknown_token":
        sheet.write_text(
            sheet.read_text(encoding="utf-8").replace(
                "**Your verdict:** [ ] PASS   [ ] FAIL",
                "**Your verdict:** [ok] PASS   [ ] FAIL",
                1,
            ),
            encoding="utf-8",
        )
    elif mutation == "dual_mark":
        sheet.write_text(
            sheet.read_text(encoding="utf-8").replace(
                "**Your verdict:** [ ] PASS   [ ] FAIL",
                "**Your verdict:** [x] PASS   [x] FAIL",
                1,
            ),
            encoding="utf-8",
        )
    else:
        text = sheet.read_text(encoding="utf-8").replace(
            "**Your verdict:** [ ] PASS   [ ] FAIL",
            "**Your verdict:** [x] PASS   [ ] FAIL",
        )
        text = text.replace(
            "**Your verdict:** [x] PASS   [ ] FAIL",
            "**Your verdict:** [ ] PASS   [x] FAIL",
            1,
        )
        sheet.write_text(text, encoding="utf-8")

    with pytest.raises(ValueError):
        validate_final_review_sheet(
            sheet_path=sheet,
            merged_path=merged,
            provenance_path=provenance,
            manifest_path=manifest,
            historical_sheet_path=protected["39-manual-review-sheet.md"],
            historical_merged_path=historical_merged,
            protected_paths=protected,
            allow_pending=mutation != "fail_without_note",
            require_complete=mutation == "fail_without_note",
        )


def test_final_sheet_preserves_embedded_newlines_in_immutable_message(tmp_path: Path):
    merged, provenance, manifest, historical_merged, sheet, protected = (
        _write_final_bundle(tmp_path, multiline=True)
    )
    generate_final_review_sheet(
        merged_path=merged,
        provenance_path=provenance,
        manifest_path=manifest,
        historical_sheet_path=protected["39-manual-review-sheet.md"],
        historical_merged_path=historical_merged,
        output_path=sheet,
        protected_paths=protected,
    )
    validate_final_review_sheet(
        sheet_path=sheet,
        merged_path=merged,
        provenance_path=provenance,
        manifest_path=manifest,
        historical_sheet_path=protected["39-manual-review-sheet.md"],
        historical_merged_path=historical_merged,
        protected_paths=protected,
        allow_pending=True,
    )
    content = sheet.read_text(encoding="utf-8")
    assert "> Dong mot cua thong diep.\n> Dong hai cua thong diep." in content
    assert "> Ly do dong mot.\n> Ly do dong hai." in content


def test_final_generation_rejects_alternate_unprotected_historical_sheet(
    tmp_path: Path,
):
    merged, provenance, manifest, historical_merged, sheet, protected = (
        _write_final_bundle(tmp_path)
    )
    alternate = tmp_path / "alternate-old-sheet.md"
    alternate.write_bytes(protected["39-manual-review-sheet.md"].read_bytes())

    with pytest.raises(ValueError, match="manifest-protected"):
        generate_final_review_sheet(
            merged_path=merged,
            provenance_path=provenance,
            manifest_path=manifest,
            historical_sheet_path=alternate,
            historical_merged_path=historical_merged,
            output_path=sheet,
            protected_paths=protected,
        )


def test_final_generation_rejects_protected_output_alias(tmp_path: Path):
    merged, provenance, manifest, historical_merged, _, protected = (
        _write_final_bundle(tmp_path)
    )

    with pytest.raises(ValueError, match="may not overwrite"):
        generate_final_review_sheet(
            merged_path=merged,
            provenance_path=provenance,
            manifest_path=manifest,
            historical_sheet_path=protected["39-manual-review-sheet.md"],
            historical_merged_path=historical_merged,
            output_path=protected["39-mislabel-triage-sheet.md"],
            protected_paths=protected,
        )


def test_final_generation_fails_before_write_when_corpus_has_under_100_rows(
    tmp_path: Path,
):
    merged, provenance, manifest, historical_merged, sheet, protected = (
        _write_final_bundle(tmp_path, rows_per_stratum=4)
    )

    with pytest.raises(ValueError, match="100 are required"):
        generate_final_review_sheet(
            merged_path=merged,
            provenance_path=provenance,
            manifest_path=manifest,
            historical_sheet_path=protected["39-manual-review-sheet.md"],
            historical_merged_path=historical_merged,
            output_path=sheet,
            protected_paths=protected,
        )

    assert not sheet.exists()


def _final_triage_fixture(*, pass_indexes: set[int] | None = None) -> str:
    passes = set(range(1, 45)) if pass_indexes is None else pass_indexes
    lines = []
    for index in range(1, 101):
        verdict = "PASS" if index in passes else "FAIL"
        detail = "(Keep): fixture approval." if verdict == "PASS" else "(Drop row): fixture rejection."
        lines.append(
            f"* **Final Example {index:03d}/100** - **{verdict} {detail}"
        )
    return "\r\n".join(lines) + "\r\n"


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _without_human_regions(text: str) -> str:
    return re.sub(
        r"<!-- BEGIN PHASE39 HUMAN REVIEW -->.*?"
        r"<!-- END PHASE39 HUMAN REVIEW -->",
        "<HUMAN-REVIEW>",
        text,
        flags=re.DOTALL,
    )


def test_import_final_triage_is_atomic_restart_safe_and_changes_only_pending_blocks(
    tmp_path: Path,
):
    merged, provenance, manifest, historical_merged, sheet, protected = (
        _write_final_bundle(tmp_path)
    )
    generate_final_review_sheet(
        merged_path=merged,
        provenance_path=provenance,
        manifest_path=manifest,
        historical_sheet_path=protected["39-manual-review-sheet.md"],
        historical_merged_path=historical_merged,
        output_path=sheet,
        protected_paths=protected,
    )
    triage = tmp_path / "FINALtriage.md"
    triage.write_bytes(_final_triage_fixture().encode("utf-8"))
    original = sheet.read_bytes()
    original_text = original.decode("utf-8")
    original_regions = _final_human_regions(original_text)
    carried_block = original_text[
        original_regions[0]["start"] : original_regions[0]["end"]
    ]

    kwargs = {
        "triage_path": triage,
        "sheet_path": sheet,
        "merged_path": merged,
        "provenance_path": provenance,
        "manifest_path": manifest,
        "historical_sheet_path": protected["39-manual-review-sheet.md"],
        "historical_merged_path": historical_merged,
        "protected_paths": protected,
        "expected_triage_sha256": _sha256_bytes(triage.read_bytes()),
        "expected_sheet_preimport_sha256": _sha256_bytes(original),
        "required_carried_verdicts": {1: "PASS"},
    }
    report = import_final_triage_decisions(**kwargs)

    assert report["completed_count"] == 100
    assert report["pending_count"] == 0
    assert report["triage_pass_count"] == 44
    assert report["triage_fail_count"] == 56
    assert report["imported_pending_count"] == 99
    assert report["already_complete"] is False
    completed = sheet.read_bytes()
    completed_text = completed.decode("utf-8")
    completed_regions = _final_human_regions(completed_text)
    assert _without_human_regions(completed_text) == _without_human_regions(
        original_text
    )
    assert (
        completed_text[
            completed_regions[0]["start"] : completed_regions[0]["end"]
        ]
        == carried_block
    )
    assert [region["verdict"] for region in completed_regions].count("PASS") == 44
    assert [region["verdict"] for region in completed_regions].count("FAIL") == 56
    assert completed_regions[44]["notes"].startswith("Final triage:")

    rerun = import_final_triage_decisions(**kwargs)
    assert rerun["already_complete"] is True
    assert sheet.read_bytes() == completed
    assert not list(tmp_path.glob(".*.import-final-triage.*.tmp"))


def test_import_final_triage_rejects_source_or_sheet_drift_without_writing(
    tmp_path: Path,
):
    merged, provenance, manifest, historical_merged, sheet, protected = (
        _write_final_bundle(tmp_path)
    )
    generate_final_review_sheet(
        merged_path=merged,
        provenance_path=provenance,
        manifest_path=manifest,
        historical_sheet_path=protected["39-manual-review-sheet.md"],
        historical_merged_path=historical_merged,
        output_path=sheet,
        protected_paths=protected,
    )
    triage = tmp_path / "FINALtriage.md"
    triage.write_bytes(_final_triage_fixture().encode("utf-8"))
    original = sheet.read_bytes()
    base_kwargs = {
        "triage_path": triage,
        "sheet_path": sheet,
        "merged_path": merged,
        "provenance_path": provenance,
        "manifest_path": manifest,
        "historical_sheet_path": protected["39-manual-review-sheet.md"],
        "historical_merged_path": historical_merged,
        "protected_paths": protected,
        "expected_sheet_preimport_sha256": _sha256_bytes(original),
        "required_carried_verdicts": {1: "PASS"},
    }

    with pytest.raises(ValueError, match="FINALtriage SHA-256"):
        import_final_triage_decisions(
            **base_kwargs, expected_triage_sha256="0" * 64
        )
    assert sheet.read_bytes() == original

    sheet.write_bytes(original + b"\n")
    drifted = sheet.read_bytes()
    with pytest.raises(ValueError):
        import_final_triage_decisions(
            **base_kwargs,
            expected_triage_sha256=_sha256_bytes(triage.read_bytes()),
        )
    assert sheet.read_bytes() == drifted


def test_import_final_triage_rejects_a_carried_verdict_conflict(tmp_path: Path):
    merged, provenance, manifest, historical_merged, sheet, protected = (
        _write_final_bundle(tmp_path)
    )
    generate_final_review_sheet(
        merged_path=merged,
        provenance_path=provenance,
        manifest_path=manifest,
        historical_sheet_path=protected["39-manual-review-sheet.md"],
        historical_merged_path=historical_merged,
        output_path=sheet,
        protected_paths=protected,
    )
    # Preserve the locked 44/56 totals while contradicting carried Example 001.
    triage = tmp_path / "FINALtriage.md"
    triage.write_bytes(
        _final_triage_fixture(pass_indexes=set(range(2, 46))).encode("utf-8")
    )
    original = sheet.read_bytes()

    with pytest.raises(ValueError, match="contradicts carried Final Example 1"):
        import_final_triage_decisions(
            triage_path=triage,
            sheet_path=sheet,
            merged_path=merged,
            provenance_path=provenance,
            manifest_path=manifest,
            historical_sheet_path=protected["39-manual-review-sheet.md"],
            historical_merged_path=historical_merged,
            protected_paths=protected,
            expected_triage_sha256=_sha256_bytes(triage.read_bytes()),
            expected_sheet_preimport_sha256=_sha256_bytes(original),
            required_carried_verdicts={1: "PASS"},
        )
    assert sheet.read_bytes() == original


def test_parse_final_triage_rejects_duplicate_or_out_of_order_decisions():
    text = _final_triage_fixture()
    assert len(parse_final_triage_decisions(text)) == 100
    malformed = text.replace("Final Example 002/100", "Final Example 001/100", 1)
    with pytest.raises(ValueError, match="unique and ordered"):
        parse_final_triage_decisions(malformed)


def _live_phase39_finalizer_kwargs() -> dict[str, Path]:
    root = Path(__file__).resolve().parents[2]
    phase = root / ".planning/phases/39-independent-quality-re-judge"
    return {
        "sheet_path": phase / "39-final-manual-review-sheet.md",
        "merged_path": root / "data/processed/judge-merged.jsonl",
        "provenance_path": root
        / "data/processed/phase39-final-judge-provenance.jsonl",
        "manifest_path": root / "data/manifests/manifest.json",
        "judge_summary_path": root / "data/processed/judge-summary.json",
        "convergence_path": root
        / "data/processed/phase39-semantic-convergence.json",
        "triage_path": phase / "FINALtriage.md",
        "historical_sheet_path": phase / "39-manual-review-sheet.md",
        "historical_merged_path": root
        / "data/backup/pre-phase39-mislabel-triage/processed/judge-merged.jsonl",
    }


def test_finalize_review_reproduces_counts_crosstabs_and_honest_report_note(
):
    kwargs = _live_phase39_finalizer_kwargs()
    phase = kwargs["sheet_path"].parent
    summary_path = phase / "39-final-manual-review-summary.json"
    note_path = phase / "39-REPORT-NOTE.md"
    before = {
        path: path.read_bytes()
        for path in (
            summary_path,
            note_path,
            kwargs["triage_path"],
            kwargs["historical_sheet_path"],
            kwargs["manifest_path"],
        )
    }

    result = finalize_review(
        **kwargs, output_path=summary_path, report_note_path=note_path
    )
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    note = note_path.read_text(encoding="utf-8")

    assert result["human_pass_count"] == 44
    assert result["human_fail_count"] == 56
    assert result["judge_human_agreement_count"] == 87
    assert summary["composition"]["label_by_human_verdict"] == {
        "bank_impersonation": {"PASS": 15, "FAIL": 18},
        "benign": {"PASS": 13, "FAIL": 13},
        "task_scam": {"PASS": 8, "FAIL": 24},
        "zalo_social_engineering": {"PASS": 8, "FAIL": 1},
    }
    assert summary["composition"]["judge_status_by_human_verdict"] == {
        "fail": {"PASS": 0, "FAIL": 43},
        "pass": {"PASS": 44, "FAIL": 13},
    }
    assert summary["composition"]["human_verdict_origin"] == {
        "carried_forward_exact_evidence": 2,
        "fresh_final_human": 98,
    }
    assert "**1,561 exact-record carries**" in note
    assert "**536 newly judged final-delta records**" in note
    assert "**176 human-approved Zalo semantics" in note
    assert "**44 PASS** and **56 FAIL**" in note
    assert "87/100 (87.0%)" in note
    assert "systematic scenario-framing and narrative artifacts" in note
    assert "240 retained records were replaced, not recovered as originals" in note
    assert "60 preserved semantic roots and seed lineages" in note
    assert "300 new direct-message realizations" in note
    assert "4 reconstructed rows** were semantically quarantined" in note
    assert "296 reconstructed rows remain" in note
    assert "final Zalo total is 297, including 1 separately admitted relabel" in note
    assert "**0 external API calls**" in note
    assert "not generator-family-independent" in note
    assert "**9 Zalo rows**" in note
    folded = note.casefold()
    assert "fresh full-corpus judge rerun" not in folded
    assert "full-corpus human annotation" not in folded
    assert "quarantined semantics were wrong" not in folded
    assert "2,403" not in note
    assert "gpt" not in folded
    assert "claude" not in folded
    assert "generator never grades its own homework" not in folded
    assert "always a different model" not in folded
    assert {path: path.read_bytes() for path in before} == before


@pytest.mark.parametrize(
    ("output_key", "alias_key"),
    [
        ("output_path", "triage_path"),
        ("report_note_path", "historical_sheet_path"),
        ("output_path", "manifest_path"),
        ("report_note_path", "output_path"),
    ],
)
def test_finalize_review_rejects_destructive_output_aliases_without_writing(
    output_key: str, alias_key: str
):
    kwargs = _live_phase39_finalizer_kwargs()
    phase = kwargs["sheet_path"].parent
    call = {
        **kwargs,
        "output_path": phase / "39-final-manual-review-summary.json",
        "report_note_path": phase / "39-REPORT-NOTE.md",
    }
    alias = call[alias_key]
    call[output_key] = alias
    protected_before = {
        key: Path(value).read_bytes()
        for key, value in call.items()
        if key.endswith("_path") and Path(value).is_file()
    }
    with pytest.raises(ValueError, match="canonical|distinct|aliases protected"):
        finalize_review(**call)
    assert {
        key: Path(call[key]).read_bytes() for key in protected_before
    } == protected_before


def test_final_summary_and_report_note_are_hash_bound_and_reproducible(
    tmp_path: Path,
):
    kwargs = _live_phase39_finalizer_kwargs()
    summary = build_final_review_summary(**kwargs)
    manifest = json.loads(kwargs["manifest_path"].read_text(encoding="utf-8"))
    judge = json.loads(kwargs["judge_summary_path"].read_text(encoding="utf-8"))
    assert render_report_note(manifest=manifest, judge=judge, human=summary) == (
        Path(__file__).resolve().parents[2]
        / ".planning/phases/39-independent-quality-re-judge/39-REPORT-NOTE.md"
    ).read_text(encoding="utf-8")

    altered_sheet = tmp_path / "altered-sheet.md"
    altered_sheet.write_bytes(kwargs["sheet_path"].read_bytes() + b"\n")
    with pytest.raises(ValueError, match="completed final review sheet SHA-256"):
        build_final_review_summary(**{**kwargs, "sheet_path": altered_sheet})

    altered_judge = tmp_path / "judge-summary.json"
    judge["passed"] -= 1
    altered_judge.write_text(json.dumps(judge), encoding="utf-8")
    with pytest.raises(ValueError, match="judge summary SHA-256"):
        build_final_review_summary(
            **{**kwargs, "judge_summary_path": altered_judge}
        )

    altered_manifest = json.loads(json.dumps(manifest))
    altered_manifest["zalo_direct_semantic_reconstruction"][
        "external_api_call_count"
    ] = 1
    with pytest.raises(ValueError, match="Zalo semantic-reconstruction facts differ"):
        render_report_note(manifest=altered_manifest, judge=judge, human=summary)


def _write_clean_compile_fixture(repo: Path, note: Path) -> Path:
    sources = [
        "documents/reports/latex/main.tex",
        "documents/reports/latex/slides.tex",
        "documents/reports/latex/references.bib",
        "documents/reports/latex/chapters/03_methodology_and_system_design.tex",
        "documents/reports/latex/chapters/05_evaluation_and_discussion.tex",
        "documents/reports/latex/chapters/extra_bound_source.tex",
        "documents/reports/latex/slides/sections/05_data.tex",
        "documents/reports/latex/pics/logo.png",
    ]
    source_hashes = {}
    for relative in sources:
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix == ".png":
            path.write_bytes(b"fixture-png-input")
        else:
            path.write_text(f"source {relative}\n", encoding="utf-8")
        source_hashes[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    started_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    builds = {}
    for name, commands in {
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
    }.items():
        output_paths = {
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
        }[name]
        logs = []
        for relative in output_paths["logs"]:
            log = repo / relative
            log.parent.mkdir(parents=True, exist_ok=True)
            log.write_text("clean log\n", encoding="utf-8")
            logs.append(
                {
                    "path": relative,
                    "sha256": hashlib.sha256(log.read_bytes()).hexdigest(),
                }
            )
        pdf = repo / output_paths["pdf"]
        import fitz

        document = fitz.open()
        document.new_page()
        document.save(pdf)
        document.close()
        builds[name] = {
            "status": "clean",
            "working_directory": "documents/reports/latex",
            "commands": commands,
            "exit_codes": [0] * len(commands),
            "logs": logs,
            "pdf": {
                "path": output_paths["pdf"],
                "sha256": hashlib.sha256(pdf.read_bytes()).hexdigest(),
                "bytes": pdf.stat().st_size,
                "pages": 1,
            },
            "fatal_error_hits": [],
            "undefined_reference_hits": [],
            "undefined_citation_hits": [],
        }
    completed_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    evidence = {
        "schema_version": "phase39-report-compile-v1",
        "status": "clean",
        "started_at_utc": started_at,
        "completed_at_utc": completed_at,
        "report_note_sha256": hashlib.sha256(note.read_bytes()).hexdigest(),
        "source_inventory_root": "documents/reports/latex",
        "source_inventory_excluded": [
            "documents/reports/latex/main.pdf",
            "documents/reports/latex/slides.pdf",
        ],
        "source_sha256": source_hashes,
        "builds": builds,
    }
    path = repo / "compile.json"
    path.write_text(json.dumps(evidence), encoding="utf-8")
    return path


def test_compile_evidence_validator_is_hash_bound_and_fail_closed(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    note = repo / "report-note.md"
    note.write_text("bound report note\n", encoding="utf-8")
    evidence_path = _write_clean_compile_fixture(repo, note)

    assert validate_report_compile_evidence(
        evidence_path=evidence_path, repo_root=repo, report_note_path=note
    )["status"] == "clean"

    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    evidence["builds"]["slides"]["exit_codes"][-1] = 1
    evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
    with pytest.raises(ValueError, match="nonzero exit code"):
        validate_report_compile_evidence(
            evidence_path=evidence_path, repo_root=repo, report_note_path=note
        )

    command_repo = tmp_path / "command-repo"
    command_repo.mkdir()
    command_note = command_repo / "report-note.md"
    command_note.write_text("bound report note\n", encoding="utf-8")
    command_evidence_path = _write_clean_compile_fixture(command_repo, command_note)
    command_evidence = json.loads(
        command_evidence_path.read_text(encoding="utf-8")
    )
    command_evidence["builds"]["thesis"]["commands"][0] = "xelatex main.tex"
    command_evidence_path.write_text(json.dumps(command_evidence), encoding="utf-8")
    with pytest.raises(ValueError, match="command/root sequence differs"):
        validate_report_compile_evidence(
            evidence_path=command_evidence_path,
            repo_root=command_repo,
            report_note_path=command_note,
        )

    log_repo = tmp_path / "log-repo"
    log_repo.mkdir()
    log_note = log_repo / "report-note.md"
    log_note.write_text("bound report note\n", encoding="utf-8")
    log_evidence_path = _write_clean_compile_fixture(log_repo, log_note)
    log_evidence = json.loads(log_evidence_path.read_text(encoding="utf-8"))
    log_path = log_repo / log_evidence["builds"]["slides"]["logs"][0]["path"]
    log_path.write_text(
        "clean log\nLaTeX Warning: Reference `missing' undefined on input line 9.\n",
        encoding="utf-8",
    )
    log_evidence["builds"]["slides"]["logs"][0]["sha256"] = hashlib.sha256(
        log_path.read_bytes()
    ).hexdigest()
    log_evidence_path.write_text(json.dumps(log_evidence), encoding="utf-8")
    with pytest.raises(ValueError, match="undefined_reference_hits differs"):
        validate_report_compile_evidence(
            evidence_path=log_evidence_path,
            repo_root=log_repo,
            report_note_path=log_note,
        )


def test_compile_evidence_rejects_bound_source_drift_and_missing_source(
    tmp_path: Path,
):
    drift_repo = tmp_path / "drift-repo"
    drift_repo.mkdir()
    drift_note = drift_repo / "report-note.md"
    drift_note.write_text("bound report note\n", encoding="utf-8")
    drift_evidence_path = _write_clean_compile_fixture(drift_repo, drift_note)
    drift_source = (
        drift_repo
        / "documents/reports/latex/chapters/extra_bound_source.tex"
    )
    drift_source.write_text("changed after build\n", encoding="utf-8")
    with pytest.raises(ValueError, match="compile source SHA-256 differs"):
        validate_report_compile_evidence(
            evidence_path=drift_evidence_path,
            repo_root=drift_repo,
            report_note_path=drift_note,
        )

    missing_repo = tmp_path / "missing-repo"
    missing_repo.mkdir()
    missing_note = missing_repo / "report-note.md"
    missing_note.write_text("bound report note\n", encoding="utf-8")
    missing_evidence_path = _write_clean_compile_fixture(missing_repo, missing_note)
    (
        missing_repo
        / "documents/reports/latex/chapters/extra_bound_source.tex"
    ).unlink()
    with pytest.raises(ValueError, match="compile evidence source inventory differs"):
        validate_report_compile_evidence(
            evidence_path=missing_evidence_path,
            repo_root=missing_repo,
            report_note_path=missing_note,
        )

    added_repo = tmp_path / "added-repo"
    added_repo.mkdir()
    added_note = added_repo / "report-note.md"
    added_note.write_text("bound report note\n", encoding="utf-8")
    added_evidence_path = _write_clean_compile_fixture(added_repo, added_note)
    added_source = added_repo / "documents/reports/latex/chapters/added_after_build.tex"
    added_source.write_text("new source after build\n", encoding="utf-8")
    with pytest.raises(ValueError, match="compile evidence source inventory differs"):
        validate_report_compile_evidence(
            evidence_path=added_evidence_path,
            repo_root=added_repo,
            report_note_path=added_note,
        )


def test_compile_evidence_rejects_noncanonical_outputs_and_pdf_spoofs(
    tmp_path: Path,
):
    log_repo = tmp_path / "spoof-log-repo"
    log_repo.mkdir()
    log_note = log_repo / "report-note.md"
    log_note.write_text("bound report note\n", encoding="utf-8")
    log_evidence_path = _write_clean_compile_fixture(log_repo, log_note)
    unrelated_log = log_repo / "clean-unrelated.log"
    unrelated_log.write_text("clean log\n", encoding="utf-8")
    log_evidence = json.loads(log_evidence_path.read_text(encoding="utf-8"))
    log_evidence["builds"]["thesis"]["logs"][0] = {
        "path": "clean-unrelated.log",
        "sha256": hashlib.sha256(unrelated_log.read_bytes()).hexdigest(),
    }
    log_evidence_path.write_text(json.dumps(log_evidence), encoding="utf-8")
    with pytest.raises(ValueError, match="log path set differs"):
        validate_report_compile_evidence(
            evidence_path=log_evidence_path,
            repo_root=log_repo,
            report_note_path=log_note,
        )

    pdf_repo = tmp_path / "spoof-pdf-repo"
    pdf_repo.mkdir()
    pdf_note = pdf_repo / "report-note.md"
    pdf_note.write_text("bound report note\n", encoding="utf-8")
    pdf_evidence_path = _write_clean_compile_fixture(pdf_repo, pdf_note)
    pdf_evidence = json.loads(pdf_evidence_path.read_text(encoding="utf-8"))
    canonical_pdf = pdf_repo / "documents/reports/latex/slides.pdf"
    unrelated_pdf = pdf_repo / "clean-unrelated.pdf"
    unrelated_pdf.write_bytes(canonical_pdf.read_bytes())
    pdf_evidence["builds"]["slides"]["pdf"] = {
        "path": "clean-unrelated.pdf",
        "sha256": hashlib.sha256(unrelated_pdf.read_bytes()).hexdigest(),
        "bytes": unrelated_pdf.stat().st_size,
        "pages": 1,
    }
    pdf_evidence_path.write_text(json.dumps(pdf_evidence), encoding="utf-8")
    with pytest.raises(ValueError, match="PDF path differs"):
        validate_report_compile_evidence(
            evidence_path=pdf_evidence_path,
            repo_root=pdf_repo,
            report_note_path=pdf_note,
        )

    magic_repo = tmp_path / "spoof-magic-repo"
    magic_repo.mkdir()
    magic_note = magic_repo / "report-note.md"
    magic_note.write_text("bound report note\n", encoding="utf-8")
    magic_evidence_path = _write_clean_compile_fixture(magic_repo, magic_note)
    magic_evidence = json.loads(magic_evidence_path.read_text(encoding="utf-8"))
    magic_pdf = magic_repo / "documents/reports/latex/main.pdf"
    magic_pdf.write_bytes(b"clean text posing as a PDF")
    magic_evidence["builds"]["thesis"]["pdf"].update(
        {
            "sha256": hashlib.sha256(magic_pdf.read_bytes()).hexdigest(),
            "bytes": magic_pdf.stat().st_size,
            "pages": 1,
        }
    )
    magic_evidence_path.write_text(json.dumps(magic_evidence), encoding="utf-8")
    with pytest.raises(ValueError, match="lacks PDF magic"):
        validate_report_compile_evidence(
            evidence_path=magic_evidence_path,
            repo_root=magic_repo,
            report_note_path=magic_note,
        )

    pages_repo = tmp_path / "spoof-pages-repo"
    pages_repo.mkdir()
    pages_note = pages_repo / "report-note.md"
    pages_note.write_text("bound report note\n", encoding="utf-8")
    pages_evidence_path = _write_clean_compile_fixture(pages_repo, pages_note)
    pages_evidence = json.loads(pages_evidence_path.read_text(encoding="utf-8"))
    pages_evidence["builds"]["slides"]["pdf"]["pages"] = 2
    pages_evidence_path.write_text(json.dumps(pages_evidence), encoding="utf-8")
    with pytest.raises(ValueError, match="page count differs"):
        validate_report_compile_evidence(
            evidence_path=pages_evidence_path,
            repo_root=pages_repo,
            report_note_path=pages_note,
        )


def test_pdf_page_verification_fails_closed_when_parser_is_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    import sys

    pdf = tmp_path / "fixture.pdf"
    pdf.write_bytes(b"%PDF-fixture")
    monkeypatch.setitem(sys.modules, "fitz", None)
    with pytest.raises(ValueError, match="PyMuPDF is required"):
        _verified_pdf_page_count(pdf)


def test_compile_evidence_rejects_outputs_older_than_refreshed_source_inventory(
    tmp_path: Path,
):
    repo = tmp_path / "stale-output-repo"
    repo.mkdir()
    note = repo / "report-note.md"
    note.write_text("bound report note\n", encoding="utf-8")
    evidence_path = _write_clean_compile_fixture(repo, note)
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    source_relative = "documents/reports/latex/chapters/extra_bound_source.tex"
    source = repo / source_relative
    source.write_text("dishonestly refreshed source inventory\n", encoding="utf-8")
    newest_output_mtime = max(
        (repo / "documents/reports/latex/main.log").stat().st_mtime,
        (repo / "documents/reports/latex/main.pdf").stat().st_mtime,
        (repo / "documents/reports/latex/slides.log").stat().st_mtime,
        (repo / "documents/reports/latex/slides.pdf").stat().st_mtime,
    )
    os.utime(source, (newest_output_mtime + 10, newest_output_mtime + 10))
    evidence["source_sha256"][source_relative] = hashlib.sha256(
        source.read_bytes()
    ).hexdigest()
    evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
    with pytest.raises(ValueError, match="predates a bound compile source"):
        validate_report_compile_evidence(
            evidence_path=evidence_path,
            repo_root=repo,
            report_note_path=note,
        )


def _write_clean_scan_fixture(repo: Path) -> Path:
    required = [
        "documents/Transcript defense.md",
        "documents/reports/latex/chapters/03_methodology_and_system_design.tex",
        "documents/reports/latex/chapters/05_evaluation_and_discussion.tex",
        "documents/reports/latex/slides/sections/05_data.tex",
    ]
    for relative in required:
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("current source\n", encoding="utf-8")
    defense = repo / "defense_notes.md"
    defense.write_text("current defense source\n", encoding="utf-8")
    files = sorted(
        [path for path in (repo / "documents").rglob("*") if path.is_file()]
        + [defense]
    )
    inventory = [
        {
            "path": path.relative_to(repo).as_posix(),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "classification": (
                "immutable_history"
                if path.name == "Transcript defense.md"
                else "active_current"
            ),
        }
        for path in files
    ]
    evidence = {
        "schema_version": "phase39-stale-claim-scan-v1",
        "status": "clean",
        "expected_roots": ["documents", ".:defense_*.md"],
        "expected_files": required,
        "inventory": inventory,
        "inventory_count": len(inventory),
        "hits": [],
        "unclassified_current_hits": [],
    }
    output = repo / "scan.json"
    output.write_text(json.dumps(evidence), encoding="utf-8")
    return output


def test_stale_claim_scan_validator_recomputes_complete_inventory(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    evidence_path = _write_clean_scan_fixture(repo)
    assert validate_stale_claim_scan(
        evidence_path=evidence_path, repo_root=repo
    )["status"] == "clean"

    extra = repo / "documents/uninventoried.md"
    extra.write_text("new active source\n", encoding="utf-8")
    with pytest.raises(ValueError, match="inventory differs"):
        validate_stale_claim_scan(evidence_path=evidence_path, repo_root=repo)

    repo_tampered = tmp_path / "repo-tampered"
    repo_tampered.mkdir()
    tampered_evidence_path = _write_clean_scan_fixture(repo_tampered)
    target = (
        repo_tampered
        / "documents/reports/latex/chapters/05_evaluation_and_discussion.tex"
    )
    target.write_text("Retired claim p < 0.0001 must not survive.\n", encoding="utf-8")
    evidence = json.loads(tampered_evidence_path.read_text(encoding="utf-8"))
    target_relative = target.relative_to(repo_tampered).as_posix()
    next(
        row for row in evidence["inventory"] if row["path"] == target_relative
    )["sha256"] = hashlib.sha256(target.read_bytes()).hexdigest()
    # A dishonest scanner updates the source hash but keeps claiming zero hits.
    tampered_evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
    with pytest.raises(ValueError, match="hit set differs"):
        validate_stale_claim_scan(
            evidence_path=tampered_evidence_path, repo_root=repo_tampered
        )

    spoof_repo = tmp_path / "spoof-repo"
    spoof_repo.mkdir()
    spoof_path = _write_clean_scan_fixture(spoof_repo)
    spoof = json.loads(spoof_path.read_text(encoding="utf-8"))
    active_chapter = (
        "documents/reports/latex/chapters/03_methodology_and_system_design.tex"
    )
    next(row for row in spoof["inventory"] if row["path"] == active_chapter)[
        "classification"
    ] = "immutable_history"
    spoof_path.write_text(json.dumps(spoof), encoding="utf-8")
    with pytest.raises(ValueError, match="classification differs"):
        validate_stale_claim_scan(evidence_path=spoof_path, repo_root=spoof_repo)

    deleted_repo = tmp_path / "deleted-repo"
    deleted_repo.mkdir()
    deleted_path = _write_clean_scan_fixture(deleted_repo)
    transcript_relative = "documents/Transcript defense.md"
    (deleted_repo / transcript_relative).unlink()
    deleted = json.loads(deleted_path.read_text(encoding="utf-8"))
    deleted["inventory"] = [
        row for row in deleted["inventory"] if row["path"] != transcript_relative
    ]
    deleted["inventory_count"] = len(deleted["inventory"])
    deleted_path.write_text(json.dumps(deleted), encoding="utf-8")
    with pytest.raises(ValueError, match="required active source is missing"):
        validate_stale_claim_scan(evidence_path=deleted_path, repo_root=deleted_repo)


def test_stale_claim_recomputation_covers_every_locked_pattern(tmp_path: Path):
    source = tmp_path / "claims.tex"
    source.write_text(
        "\n".join(
            [
                r"$t = 8.7$ and $t = 53.2$",
                r"$p < 0.0001$",
                r"H$_0$ and null hypothesis",
                "H₀",
                "94/100 and Ninety-four passed",
                "49/50 passed",
                "Quality means were 4.68 / 4.96",
                "LLM-based quality review of 50 sampled records",
                r"2{,}403 examples",
                r"1{,}900 / 252 / 251",
                "019aec39979429ca8005dd299d2ddaf7d3ecfdade259eecc4d3129adaed25938",
                "6f208fb6cd9399b8934225e6a25efd65d49bbb4f4846360837f6835a2561b6d7",
                "2,333 training examples and 254 validation examples",
                "Historical model snapshot: 2,333 training examples and 254 validation examples",
                "413-row test reserved for future work",
                "Historical model snapshot: former 413-row test partition",
                "The final split contains overlapping seed groups",
                "Historical model snapshot includes seed overlap",
                "The generator never grades its own homework",
                "The judge is always a different model",
                "The defaults reproduce the reported run",
                "The final stage evaluates the full stack on the internal validation split",
                "Historical snapshot: the final stage evaluated the full stack on the earlier internal validation split",
                "The model was trained and evaluated on the promoted 2,097-row corpus",
                "Defaults target data/splits/val.jsonl (219-row development validation) and do not reproduce the historical 254-row metrics; the 220-row test is reserved",
                "The promoted 2,097-row corpus has not yet been used for model retraining or evaluation",
                "The historical 254-row held-out split produced the reported metrics",
                "In the historical 254-row validation snapshot, zero scam-to-benign errors were observed",
                "The model never lets a real threat through",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    current = {"claims.tex": source}
    recorded = {"claims.tex": {"classification": "active_current"}}
    hits, unresolved = _recompute_stale_claim_hits(
        current=current, recorded=recorded
    )
    assert {hit["pattern"] for hit in hits} == {
        "retired_t_statistic",
        "retired_p_value",
        "retired_null_hypothesis",
        "retired_94_of_100",
        "retired_quality_49_of_50",
        "retired_quality_means_4_68_4_96",
        "retired_50_record_sample_review",
        "superseded_corpus_2403",
        "superseded_split_1900_252_251",
        "superseded_test_sha256",
        "current_final_test_sha256",
        "historical_model_train_2333",
        "historical_model_validation_254",
        "historical_model_test_413",
        "historical_seed_overlap",
        "false_universal_judge_independence",
        "false_evaluate_release_default_reproduction",
        "ambiguous_final_stack_internal_validation",
        "false_promoted_corpus_model_completion",
        "false_historical_254_held_out",
        "false_universal_threat_recall",
    }
    assert sum(
        hit["disposition"] == "historical_model_snapshot" for hit in hits
    ) >= 5
    assert {
        "historical_model_train_2333",
        "historical_model_validation_254",
        "historical_model_test_413",
        "historical_seed_overlap",
    }.issubset({hit["pattern"] for hit in unresolved})
    assert "false_universal_judge_independence" in {
        hit["pattern"] for hit in unresolved
    }
    assert {
        "false_evaluate_release_default_reproduction",
        "ambiguous_final_stack_internal_validation",
        "false_promoted_corpus_model_completion",
        "false_historical_254_held_out",
        "false_universal_threat_recall",
    }.issubset({hit["pattern"] for hit in unresolved})
    clean_contexts = {
        "Defaults target data/splits/val.jsonl (219-row development validation) and do not reproduce the historical 254-row metrics; the 220-row test is reserved",
        "The promoted 2,097-row corpus has not yet been used for model retraining or evaluation",
        "In the historical 254-row validation snapshot, zero scam-to-benign errors were observed",
    }
    assert not clean_contexts.intersection({hit["context"] for hit in unresolved})
    assert sum(
        hit["pattern"] == "retired_null_hypothesis" for hit in hits
    ) == 2
    assert next(
        hit for hit in hits if hit["pattern"] == "current_final_test_sha256"
    )["disposition"] == "current_final_test_hash"


def test_report_closure_rejects_altered_human_summary_before_other_gates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    root = Path(__file__).resolve().parents[2]
    phase = root / ".planning/phases/39-independent-quality-re-judge"
    human = json.loads(
        (phase / "39-final-manual-review-summary.json").read_text(encoding="utf-8")
    )
    human["human_pass_count"] = 45
    altered = tmp_path / "human.json"
    altered.write_text(json.dumps(human), encoding="utf-8")
    monkeypatch.setattr(
        "src.data_pipeline.manual_review_sheet.validate_canonical_final_release",
        lambda **_: {"status": "fixture-valid"},
    )
    with pytest.raises(ValueError, match="human summary differs"):
        verify_report_closure(
            manifest_path=root / "data/manifests/manifest.json",
            judge_summary_path=root / "data/processed/judge-summary.json",
            human_summary_path=altered,
            report_note_path=phase / "39-REPORT-NOTE.md",
            compile_evidence_path=tmp_path / "missing-compile.json",
            scan_evidence_path=tmp_path / "missing-scan.json",
            requirements_path=root / ".planning/REQUIREMENTS.md",
        )


def test_canonical_release_validation_rejects_live_split_byte_drift(tmp_path: Path):
    root = Path(__file__).resolve().parents[2]
    copied_splits = tmp_path / "splits"
    copied_splits.mkdir()
    for name in ("train", "val", "test"):
        source = root / f"data/splits/{name}.jsonl"
        (copied_splits / f"{name}.jsonl").write_bytes(source.read_bytes())
    train = copied_splits / "train.jsonl"
    train.write_bytes(train.read_bytes() + b"\n")

    with pytest.raises(ValueError, match="promoted live split differs from candidate"):
        validate_canonical_final_release(
            repo_root=root, splits_dir=copied_splits
        )


def test_report_closure_rejects_substitute_requirements_before_validation(
    tmp_path: Path,
):
    root = Path(__file__).resolve().parents[2]
    phase = root / ".planning/phases/39-independent-quality-re-judge"
    substitute = tmp_path / "REQUIREMENTS.md"
    substitute.write_bytes((root / ".planning/REQUIREMENTS.md").read_bytes())
    with pytest.raises(ValueError, match="canonical repository .planning/REQUIREMENTS"):
        verify_report_closure(
            manifest_path=root / "data/manifests/manifest.json",
            judge_summary_path=root / "data/processed/judge-summary.json",
            human_summary_path=phase / "39-final-manual-review-summary.json",
            report_note_path=phase / "39-REPORT-NOTE.md",
            compile_evidence_path=phase / "39-REPORT-COMPILE.json",
            scan_evidence_path=phase / "39-STALE-CLAIM-SCAN.json",
            requirements_path=substitute,
        )
