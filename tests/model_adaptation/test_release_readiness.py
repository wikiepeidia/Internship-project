"""Held-out release readiness tests for Phase 5."""

from __future__ import annotations

import json
from pathlib import Path

from src.model_adaptation.release_readiness import audit_release_eval_support, resolve_release_eval_path
from src.model_adaptation.schemas import LOCKED_RELEASE_LABELS


def _build_record(label: str, seed_id: str) -> dict[str, object]:
    risk_tier = "benign" if label == "benign" else "high-risk"
    return {
        "text": f"Tin nhan mau cho {label} voi noi dung du de kiem thu.",
        "label": label,
        "risk_tier": risk_tier,
        "suspicious_spans": ["tai khoan" if label != "benign" else "binh thuong"],
        "xai_explanation": "Giai thich du chi tiet de dap ung hop dong kiem thu Phase 5.",
        "source": "synthetic_claude",
        "seed_id": seed_id,
    }


def _write_split(split_path: Path, records: list[dict[str, object]]) -> None:
    split_path.parent.mkdir(parents=True, exist_ok=True)
    with split_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def test_release_readiness_reports_explicit_label_order_counts(tmp_path: Path):
    split_root = tmp_path / "splits"
    split_path = split_root / "test.jsonl"
    _write_split(
        split_path,
        [
            _build_record("bank_impersonation", "seed-1"),
            _build_record("zalo_social_engineering", "seed-2"),
            _build_record("task_scam", "seed-3"),
            _build_record("benign", "seed-4"),
            _build_record("benign", "seed-5"),
        ],
    )

    resolved_path = resolve_release_eval_path(split_root=split_root)
    audit = audit_release_eval_support(split_root=split_root)

    assert resolved_path == split_path
    assert list(audit.support_by_label.keys()) == list(LOCKED_RELEASE_LABELS)
    assert audit.support_by_label["bank_impersonation"] == 1
    assert audit.support_by_label["zalo_social_engineering"] == 1
    assert audit.support_by_label["task_scam"] == 1
    assert audit.support_by_label["benign"] == 2
    assert audit.ready is True
    assert audit.blocker_reasons == []
    assert audit.evaluated_split_path == split_path


def test_release_readiness_blocks_when_any_risky_label_has_zero_support(tmp_path: Path):
    split_path = tmp_path / "release-eval.jsonl"
    _write_split(
        split_path,
        [
            _build_record("bank_impersonation", "seed-1"),
            _build_record("benign", "seed-2"),
        ],
    )

    audit = audit_release_eval_support(split_path=split_path)

    assert audit.ready is False
    assert audit.verdict == "BLOCK"
    assert audit.support_by_label["zalo_social_engineering"] == 0
    assert audit.support_by_label["task_scam"] == 0
    assert any("zalo_social_engineering" in reason for reason in audit.blocker_reasons)
    assert any("task_scam" in reason for reason in audit.blocker_reasons)
    assert audit.evaluated_split_path == split_path