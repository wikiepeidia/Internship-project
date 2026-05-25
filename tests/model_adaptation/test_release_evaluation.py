"""Offline release-evaluation tests for Phase 5."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.model_adaptation.release_evaluation import compute_release_metrics, evaluate_release_split
from src.model_adaptation.release_readiness import audit_release_eval_support
from src.model_adaptation.schemas import LOCKED_RELEASE_LABELS, ReleaseEvaluationRow
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

    snapshot = evaluate_release_split(split_path, audit=audit, analyze_text=fake_analyze)

    assert captured_channels == ["unknown"]
    assert snapshot.rows[0].channel == "unknown"


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