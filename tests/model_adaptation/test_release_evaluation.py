"""Offline release-evaluation tests for Phase 5."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import src.model_adaptation.release_evaluation as release_evaluation_module
from src.model_adaptation.release_evaluation import (
    _apply_recall_floor_to_audit,
    compute_release_metrics,
    evaluate_release_split,
)
from src.model_adaptation.release_readiness import audit_release_eval_support
from src.model_adaptation.schemas import LOCKED_RELEASE_LABELS, PerLabelMetricRow, ReleaseEvaluationRow
from src.runtime.contracts import AnalysisResult, SuspiciousCue


def _build_record(label: str, seed_id: str, text: str) -> dict[str, object]:
    risk_tier = "benign" if label == "benign" else "high-risk"
    return {
        "text": text,
        "label": label,
        "risk_tier": risk_tier,
        "suspicious_spans": ["OTP" if label != "benign" else "hop le"],
        "xai_explanation": "Giai thich du chi tiet de dap ung hop dong kiem thu Phase 5.",
        "source": "synthetic_claude",
        "seed_id": seed_id,
    }


def _write_split(split_path: Path, records: list[dict[str, object]]) -> None:
    split_path.parent.mkdir(parents=True, exist_ok=True)
    with split_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def _build_row(gold_label: str, predicted_labels: list[str]) -> ReleaseEvaluationRow:
    return ReleaseEvaluationRow(
        gold_label=gold_label,
        predicted_labels=predicted_labels,
        risk_tier="benign" if gold_label == "benign" else "high-risk",
        summary="Tom tat du de hop le cho hang danh gia Phase 5.",
        top_cues=[SuspiciousCue(span="OTP", reason="Tin nhan de cap ma xac thuc nhay cam")],
        recommendations=["Khong chuyen tien truoc khi xac minh."],
        backend_name="fake-runtime",
        split_provenance="data/splits/test.jsonl",
        reviewable_source_text="Tin nhan mau de phuc vu kiem thu Phase 5.",
    )


def test_release_evaluator_uses_runtime_service_contract_boundary(tmp_path: Path):
    split_path = tmp_path / "test.jsonl"
    _write_split(
        split_path,
        [
            _build_record("bank_impersonation", "seed-1", "VPBank can OTP de xac minh giao dich ngay."),
            _build_record("benign", "seed-2", "Hen gap luc 3 gio chieu tai van phong nhe ban."),
        ],
    )
    audit = audit_release_eval_support(split_path=split_path)
    captured_calls: list[tuple[str, str]] = []

    def fake_analyze(text: str, channel: str = "unknown") -> AnalysisResult:
        captured_calls.append((text, channel))
        if "OTP" in text:
            return AnalysisResult(
                risk_tier="high-risk",
                summary="Tin nhan gia danh ngan hang va yeu cau OTP.",
                top_cues=[SuspiciousCue(span="OTP", reason="Yeu cau ma OTP nhay cam")],
                threat_labels=["bank_impersonation"],
                recommendations=["Khong cung cap OTP cho bat ky ai."],
                backend_name="fake-runtime",
                normalized_text=text.casefold(),
            )
        return AnalysisResult(
            risk_tier="benign",
            summary="Noi dung binh thuong.",
            top_cues=[],
            threat_labels=["benign"],
            recommendations=["Khong co hanh dong nguy hiem duoc de xuat."],
            backend_name="fake-runtime",
            normalized_text=text.casefold(),
        )

    snapshot_path = tmp_path / "05-evaluation-snapshot.json"
    snapshot = evaluate_release_split(
        split_path,
        audit=audit,
        analyze_text=fake_analyze,
        snapshot_path=snapshot_path,
        run_id="phase5-run-001",
    )

    assert captured_calls == [
        ("VPBank can OTP de xac minh giao dich ngay.", "unknown"),
        ("Hen gap luc 3 gio chieu tai van phong nhe ban.", "unknown"),
    ]
    assert snapshot.run_id == "phase5-run-001"
    assert snapshot.rows[0].gold_label == "bank_impersonation"
    assert snapshot.rows[0].predicted_labels == ["bank_impersonation"]
    assert snapshot.rows[0].backend_name == "fake-runtime"
    assert snapshot.rows[0].split_provenance == str(split_path)
    assert snapshot.rows[0].reviewable_source_text == "VPBank can OTP de xac minh giao dich ngay."
    assert snapshot_path.exists()

    saved_snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    assert saved_snapshot["run_id"] == "phase5-run-001"
    assert len(saved_snapshot["rows"]) == 2


def test_release_evaluator_marks_channel_unknown_when_dataset_lacks_channel(tmp_path: Path):
    split_path = tmp_path / "test.jsonl"
    _write_split(
        split_path,
        [_build_record("task_scam", "seed-1", "Cong viec online luong cao, nop phi kich hoat ngay.")],
    )
    audit = audit_release_eval_support(split_path=split_path)
    captured_channels: list[str] = []

    def fake_analyze(text: str, channel: str = "unknown") -> AnalysisResult:
        captured_channels.append(channel)
        return AnalysisResult(
            risk_tier="high-risk",
            summary="Cong viec online luong cao la dau hieu task scam.",
            top_cues=[SuspiciousCue(span="luong cao", reason="Hua hen thu nhap bat thuong")],
            threat_labels=["task_scam"],
            recommendations=["Khong nop phi kich hoat hay chuyen tien truoc."],
            backend_name="fake-runtime",
            normalized_text=text.casefold(),
        )

    snapshot = evaluate_release_split(
        split_path,
        audit=audit,
        analyze_text=fake_analyze,
        snapshot_path=tmp_path / "05-evaluation-snapshot.json",
    )

    assert captured_channels == ["unknown"]
    assert snapshot.rows[0].channel == "unknown"


def test_release_evaluator_writes_periodic_checkpoints_and_reports_progress(tmp_path: Path, monkeypatch):
    split_path = tmp_path / "test.jsonl"
    _write_split(
        split_path,
        [
            _build_record("bank_impersonation", "seed-1", "VPBank can OTP de xac minh giao dich ngay."),
            _build_record("benign", "seed-2", "Hen gap luc 3 gio chieu tai van phong nhe ban."),
        ],
    )
    audit = audit_release_eval_support(split_path=split_path)
    written_row_counts: list[int] = []
    progress_events: list[tuple[int, int]] = []

    def fake_write_snapshot(snapshot, snapshot_path):
        written_row_counts.append(snapshot.overall_metrics.evaluated_rows)

    def fake_analyze(text: str, channel: str = "unknown") -> AnalysisResult:
        if "OTP" in text:
            return AnalysisResult(
                risk_tier="high-risk",
                summary="Tin nhan gia danh ngan hang va yeu cau OTP.",
                top_cues=[SuspiciousCue(span="OTP", reason="Yeu cau ma OTP nhay cam")],
                threat_labels=["bank_impersonation"],
                recommendations=["Khong cung cap OTP cho bat ky ai."],
                backend_name="fake-runtime",
                normalized_text=text.casefold(),
            )
        return AnalysisResult(
            risk_tier="benign",
            summary="Noi dung binh thuong.",
            top_cues=[],
            threat_labels=["benign"],
            recommendations=["Khong co hanh dong nguy hiem duoc de xuat."],
            backend_name="fake-runtime",
            normalized_text=text.casefold(),
        )

    monkeypatch.setattr(release_evaluation_module, "_write_snapshot", fake_write_snapshot)

    release_evaluation_module.evaluate_release_split(
        split_path,
        audit=audit,
        analyze_text=fake_analyze,
        snapshot_path=tmp_path / "05-evaluation-snapshot.json",
        run_id="phase5-run-002",
        progress_callback=lambda current, total: progress_events.append((current, total)),
        checkpoint_interval=1,
    )

    assert progress_events == [(1, 2), (2, 2)]
    assert written_row_counts == [1, 2]


def test_release_evaluator_resumes_from_matching_snapshot(tmp_path: Path):
    split_path = tmp_path / "test.jsonl"
    records = [
        _build_record("bank_impersonation", "seed-1", "VPBank can OTP de xac minh giao dich ngay."),
        _build_record("benign", "seed-2", "Hen gap luc 3 gio chieu tai van phong nhe ban."),
        _build_record("task_scam", "seed-3", "Cong viec online luong cao, nop phi kich hoat ngay."),
    ]
    _write_split(split_path, records)
    audit = audit_release_eval_support(split_path=split_path)
    snapshot_path = tmp_path / "05-evaluation-snapshot.json"

    first_pass_calls: list[str] = []

    def flaky_analyze(text: str, channel: str = "unknown") -> AnalysisResult:
        del channel
        first_pass_calls.append(text)
        if len(first_pass_calls) == 3:
            raise RuntimeError("transient runtime failure")
        if "OTP" in text:
            return AnalysisResult(
                risk_tier="high-risk",
                summary="Tin nhan gia danh ngan hang va yeu cau OTP.",
                top_cues=[SuspiciousCue(span="OTP", reason="Yeu cau ma OTP nhay cam")],
                threat_labels=["bank_impersonation"],
                recommendations=["Khong cung cap OTP cho bat ky ai."],
                backend_name="fake-runtime",
                normalized_text=text.casefold(),
            )
        return AnalysisResult(
            risk_tier="benign" if "Hen gap" in text else "high-risk",
            summary="Noi dung binh thuong." if "Hen gap" in text else "Cong viec online luong cao la dau hieu task scam.",
            top_cues=[] if "Hen gap" in text else [SuspiciousCue(span="luong cao", reason="Hua hen thu nhap bat thuong")],
            threat_labels=["benign"] if "Hen gap" in text else ["task_scam"],
            recommendations=["Khong co hanh dong nguy hiem duoc de xuat."] if "Hen gap" in text else ["Khong nop phi kich hoat hay chuyen tien truoc."],
            backend_name="fake-runtime",
            normalized_text=text.casefold(),
        )

    with pytest.raises(RuntimeError, match="transient runtime failure"):
        evaluate_release_split(
            split_path,
            audit=audit,
            analyze_text=flaky_analyze,
            snapshot_path=snapshot_path,
            run_id="phase5-run-003",
            checkpoint_interval=1,
        )

    partial_snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    assert len(partial_snapshot["rows"]) == 2

    resumed_calls: list[str] = []

    def steady_analyze(text: str, channel: str = "unknown") -> AnalysisResult:
        del channel
        resumed_calls.append(text)
        return AnalysisResult(
            risk_tier="high-risk",
            summary="Cong viec online luong cao la dau hieu task scam.",
            top_cues=[SuspiciousCue(span="luong cao", reason="Hua hen thu nhap bat thuong")],
            threat_labels=["task_scam"],
            recommendations=["Khong nop phi kich hoat hay chuyen tien truoc."],
            backend_name="fake-runtime",
            normalized_text=text.casefold(),
        )

    snapshot = evaluate_release_split(
        split_path,
        audit=audit,
        analyze_text=steady_analyze,
        snapshot_path=snapshot_path,
        run_id="phase5-run-003",
        checkpoint_interval=1,
    )

    assert resumed_calls == [records[2]["text"]]
    assert snapshot.overall_metrics.evaluated_rows == 3
    assert [row.gold_label for row in snapshot.rows] == ["bank_impersonation", "benign", "task_scam"]


def test_release_metrics_keep_zero_support_labels_visible():
    overall_metrics, per_label_metrics = compute_release_metrics(
        [
            _build_row("bank_impersonation", ["bank_impersonation"]),
            _build_row("benign", ["benign"]),
        ]
    )

    assert overall_metrics.evaluated_rows == 2
    assert [row.label for row in per_label_metrics] == list(LOCKED_RELEASE_LABELS)
    assert next(row for row in per_label_metrics if row.label == "zalo_social_engineering").support == 0
    assert next(row for row in per_label_metrics if row.label == "task_scam").support == 0


def test_release_metrics_report_macro_and_weighted_f1():
    overall_metrics, _ = compute_release_metrics(
        [
            _build_row("bank_impersonation", ["bank_impersonation"]),
            _build_row("benign", ["benign"]),
        ]
    )

    assert overall_metrics.macro_f1 == pytest.approx(0.5)
    assert overall_metrics.weighted_f1 == pytest.approx(1.0)


def test_release_metrics_preserve_multilabel_predictions():
    _, per_label_metrics = compute_release_metrics(
        [
            _build_row("bank_impersonation", ["task_scam", "bank_impersonation"]),
            _build_row("task_scam", ["task_scam"]),
        ]
    )

    bank_metrics = next(row for row in per_label_metrics if row.label == "bank_impersonation")
    task_metrics = next(row for row in per_label_metrics if row.label == "task_scam")

    assert bank_metrics.recall == pytest.approx(1.0)
    assert task_metrics.precision == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# Gate bug regression tests (Phase 7a-01)
# ---------------------------------------------------------------------------


def _task_scam_recall_low_split(split_path: Path, *, task_scam_rows: int = 9) -> None:
    """Write a split where task_scam is mostly predicted as benign (recall < floor)."""
    records = []
    for i in range(task_scam_rows):
        records.append(_build_record("task_scam", f"seed-ts-{i}", f"Cong viec like/follow luong cao nop phi truoc row {i}."))
    records.append(_build_record("bank_impersonation", "seed-bi-1", "VPBank can OTP xac minh tai khoan ngay."))
    records.append(_build_record("benign", "seed-bn-1", "Hen gap luc 3 gio chieu tai van phong."))
    split_path.parent.mkdir(parents=True, exist_ok=True)
    with split_path.open("w", encoding="utf-8") as handle:
        for r in records:
            handle.write(json.dumps(r, ensure_ascii=False) + "\n")


def test_gate_blocks_when_task_scam_recall_is_below_floor(tmp_path: Path):
    """Regression test: snapshot.audit.verdict must be BLOCK when task_scam recall < 0.80."""
    split_path = tmp_path / "val.jsonl"
    _task_scam_recall_low_split(split_path, task_scam_rows=9)
    audit = audit_release_eval_support(split_path=split_path)
    call_count = {"n": 0}

    def fake_analyze(text: str, channel: str = "unknown") -> AnalysisResult:
        call_count["n"] += 1
        if "OTP" in text:
            return AnalysisResult(
                risk_tier="high-risk",
                summary="Tin nhan gia danh ngan hang va yeu cau OTP.",
                top_cues=[SuspiciousCue(span="OTP", reason="Yeu cau ma OTP nhay cam")],
                threat_labels=["bank_impersonation"],
                recommendations=["Khong cung cap OTP cho bat ky ai."],
                backend_name="fake-runtime",
                normalized_text=text.casefold(),
            )
        if "van phong" in text:
            return AnalysisResult(
                risk_tier="benign",
                summary="Noi dung binh thuong.",
                top_cues=[],
                threat_labels=["benign"],
                recommendations=["Khong co hanh dong nguy hiem duoc de xuat."],
                backend_name="fake-runtime",
                normalized_text=text.casefold(),
            )
        # task_scam rows are predicted as benign — simulating low recall
        return AnalysisResult(
            risk_tier="benign",
            summary="Noi dung binh thuong.",
            top_cues=[],
            threat_labels=["benign"],
            recommendations=["Khong co hanh dong."],
            backend_name="fake-runtime",
            normalized_text=text.casefold(),
        )

    snapshot = evaluate_release_split(
        split_path,
        audit=audit,
        analyze_text=fake_analyze,
        snapshot_path=tmp_path / "05-evaluation-snapshot.json",
        run_id="phase7a-gate-regression-001",
    )

    task_scam_row = next(r for r in snapshot.per_label_metrics if r.label == "task_scam")
    assert task_scam_row.recall < 0.80, "test assumption: recall should be below floor"
    assert snapshot.audit.ready is False, "gate must report not-ready when task_scam recall is below floor"
    assert snapshot.audit.verdict == "BLOCK", "gate must report BLOCK when task_scam recall is below floor"
    assert any("task_scam" in reason for reason in snapshot.audit.blocker_reasons), (
        "blocker_reasons must name the failing label"
    )


def test_gate_passes_when_all_risky_labels_meet_recall_floor(tmp_path: Path):
    """Regression test: snapshot.audit.verdict must be PASS when all risky recalls >= floor."""
    split_path = tmp_path / "val.jsonl"
    split_path.parent.mkdir(parents=True, exist_ok=True)
    records = [
        _build_record("bank_impersonation", "seed-bi-1", "VPBank can OTP xac minh tai khoan ngay."),
        _build_record("zalo_social_engineering", "seed-ze-1", "Ban cua ban gui link doi thuong qua Zalo."),
        _build_record("task_scam", "seed-ts-1", "Cong viec like/follow luong cao nop phi truoc."),
        _build_record("benign", "seed-bn-1", "Hen gap luc 3 gio chieu tai van phong."),
    ]
    with split_path.open("w", encoding="utf-8") as handle:
        for r in records:
            handle.write(json.dumps(r, ensure_ascii=False) + "\n")

    audit = audit_release_eval_support(split_path=split_path)

    def perfect_analyze(text: str, channel: str = "unknown") -> AnalysisResult:
        if "OTP" in text:
            label, tier, cue = "bank_impersonation", "high-risk", "OTP"
        elif "Zalo" in text:
            label, tier, cue = "zalo_social_engineering", "high-risk", "Zalo"
        elif "like/follow" in text or "luong cao" in text:
            label, tier, cue = "task_scam", "high-risk", "luong cao"
        else:
            return AnalysisResult(
                risk_tier="benign",
                summary="Noi dung binh thuong.",
                top_cues=[],
                threat_labels=["benign"],
                recommendations=["Khong co hanh dong."],
                backend_name="fake-runtime",
                normalized_text=text.casefold(),
            )
        return AnalysisResult(
            risk_tier=tier,
            summary=f"Phat hien {label}.",
            top_cues=[SuspiciousCue(span=cue, reason=f"Dau hieu {label}")],
            threat_labels=[label],
            recommendations=["Khong hanh dong theo yeu cau."],
            backend_name="fake-runtime",
            normalized_text=text.casefold(),
        )

    snapshot = evaluate_release_split(
        split_path,
        audit=audit,
        analyze_text=perfect_analyze,
        snapshot_path=tmp_path / "05-evaluation-snapshot.json",
    )

    assert snapshot.audit.ready is True, "gate must report ready when all risky recalls >= floor"
    assert snapshot.audit.verdict == "PASS", "gate must report PASS when all risky recalls >= floor"
    assert snapshot.audit.blocker_reasons == [], "no blocker reasons should be added for passing recalls"


def test_gate_passes_when_task_scam_recall_is_between_080_and_090(tmp_path: Path):
    """task_scam floor is 0.80 (not 0.90). Recall of 0.82 must produce PASS, not BLOCK."""
    from src.model_adaptation.release_evaluation import _apply_recall_floor_to_audit
    from src.model_adaptation.schemas import PerLabelMetricRow

    split_path = tmp_path / "val.jsonl"
    split_path.parent.mkdir(parents=True, exist_ok=True)
    records = [
        _build_record("bank_impersonation", "s1", "VPBank yeu cau OTP xac minh tai khoan."),
        _build_record("zalo_social_engineering", "s2", "Ban cua ban gui link Zalo nhan qua."),
        _build_record("task_scam", "s3", "Cong viec like follow luong cao nop phi truoc."),
        _build_record("benign", "s4", "Hen gap luc 3 gio chieu tai van phong."),
    ]
    split_path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n",
        encoding="utf-8",
    )
    audit = audit_release_eval_support(split_path=split_path)

    per_label_metrics = [
        PerLabelMetricRow(label="bank_impersonation", recall=0.95, precision=0.95, f1=0.95, support=10),
        PerLabelMetricRow(label="zalo_social_engineering", recall=0.91, precision=0.91, f1=0.91, support=10),
        PerLabelMetricRow(label="task_scam", recall=0.82, precision=0.82, f1=0.82, support=10),
        PerLabelMetricRow(label="benign", recall=0.85, precision=0.85, f1=0.85, support=10),
    ]
    result = _apply_recall_floor_to_audit(audit, per_label_metrics)

    assert result.ready is True, (
        "task_scam recall=0.82 >= floor 0.80 — gate must PASS, not BLOCK at 0.90"
    )
    assert result.verdict == "PASS"
    assert not any("task_scam" in r for r in result.blocker_reasons)


def test_apply_recall_floor_to_audit_adds_blocker_for_failing_label(tmp_path: Path):
    """Unit test for the _apply_recall_floor_to_audit helper.

    Uses a full four-class split so the support audit starts clean (no missing-support
    blockers), then supplies per_label_metrics with task_scam recall below the floor.
    """
    split_path = tmp_path / "val.jsonl"
    split_path.parent.mkdir(parents=True, exist_ok=True)
    full_split_records = [
        _build_record("bank_impersonation", "seed-bi-1", "VPBank can OTP xac minh ngay."),
        _build_record("zalo_social_engineering", "seed-ze-1", "Ban cua ban gui link Zalo."),
        _build_record("task_scam", "seed-ts-1", "Cong viec like/follow luong cao nop phi truoc."),
        _build_record("benign", "seed-bn-1", "Hen gap tai van phong luc 3h."),
    ]
    with split_path.open("w", encoding="utf-8") as handle:
        for r in full_split_records:
            handle.write(json.dumps(r, ensure_ascii=False) + "\n")
    audit = audit_release_eval_support(split_path=split_path)
    assert audit.blocker_reasons == [], "setup: all four classes present so audit has no blockers"

    low_recall_metrics = [
        PerLabelMetricRow(label="bank_impersonation", precision=1.0, recall=1.0, f1=1.0, support=10),
        PerLabelMetricRow(label="zalo_social_engineering", precision=1.0, recall=1.0, f1=1.0, support=10),
        PerLabelMetricRow(label="task_scam", precision=0.5, recall=0.44, f1=0.47, support=18),
        PerLabelMetricRow(label="benign", precision=1.0, recall=1.0, f1=1.0, support=10),
    ]
    updated_audit = _apply_recall_floor_to_audit(audit, low_recall_metrics)

    assert updated_audit.ready is False
    assert updated_audit.verdict == "BLOCK"
    assert any("task_scam" in r for r in updated_audit.blocker_reasons)
    assert any("0.44" in r for r in updated_audit.blocker_reasons)


def test_apply_recall_floor_to_audit_returns_unchanged_audit_when_all_floors_met(tmp_path: Path):
    """Unit test: _apply_recall_floor_to_audit returns original audit when recall meets floor."""
    split_path = tmp_path / "val.jsonl"
    split_path.parent.mkdir(parents=True, exist_ok=True)
    full_split_records = [
        _build_record("bank_impersonation", "seed-bi-1", "VPBank can OTP xac minh ngay."),
        _build_record("zalo_social_engineering", "seed-ze-1", "Ban cua ban gui link Zalo."),
        _build_record("task_scam", "seed-ts-1", "Cong viec like/follow luong cao nop phi truoc."),
        _build_record("benign", "seed-bn-1", "Hen gap tai van phong luc 3h."),
    ]
    with split_path.open("w", encoding="utf-8") as handle:
        for r in full_split_records:
            handle.write(json.dumps(r, ensure_ascii=False) + "\n")
    audit = audit_release_eval_support(split_path=split_path)

    # All risky recalls are above the 0.90 floor
    passing_metrics = [
        PerLabelMetricRow(label="bank_impersonation", precision=1.0, recall=0.95, f1=0.97, support=10),
        PerLabelMetricRow(label="zalo_social_engineering", precision=1.0, recall=0.92, f1=0.96, support=10),
        PerLabelMetricRow(label="task_scam", precision=0.9, recall=0.91, f1=0.90, support=18),
        PerLabelMetricRow(label="benign", precision=1.0, recall=1.0, f1=1.0, support=10),
    ]
    updated_audit = _apply_recall_floor_to_audit(audit, passing_metrics)

    # No extra blockers were added — the function should return the original audit unchanged
    assert updated_audit is audit