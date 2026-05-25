"""Wave 0 schema tests for the Phase 3 model-adaptation foundation."""

from pathlib import Path

import pytest
from pydantic import TypeAdapter, ValidationError

from src.config.settings import Settings
from src.model_adaptation.catalog import build_default_catalog, get_candidate_by_id
from src.model_adaptation.schemas import (
    LOCKED_RELEASE_LABELS,
    LOCKED_RISKY_LABELS,
    UNIFORM_RISKY_RECALL_FLOOR,
    ExplanationRubricSummary,
    HeldOutSupportAudit,
    ModelArtifactRecord,
    ModelCandidate,
    OverallMetricSummary,
    PerLabelMetricRow,
    PilotSelection,
    ReleaseEvaluationArtifact,
    ReleaseEvaluationRow,
    ReleaseVerdict,
)
from src.runtime.contracts import SuspiciousCue


def test_catalog_contains_locked_qwen_candidates():
    catalog = build_default_catalog()

    assert [candidate.candidate_id for candidate in catalog] == [
        "qwen3.5-4b",
        "qwen3-4b-instruct-2507",
        "qwen2.5-7b-instruct",
    ]
    assert [candidate.hf_source for candidate in catalog] == [
        "Qwen/Qwen3.5-4B",
        "Qwen/Qwen3-4B-Instruct-2507",
        "Qwen/Qwen2.5-7B-Instruct",
    ]
    assert [candidate.role for candidate in catalog] == ["primary", "fallback", "fallback"]
    assert [candidate.size_label for candidate in catalog] == ["4B", "4B", "7B"]
    assert get_candidate_by_id("qwen3.5-4b").hf_source == "Qwen/Qwen3.5-4B"


def test_model_candidate_rejects_blank_identifiers():
    with pytest.raises(ValidationError):
        ModelCandidate(
            candidate_id="qwen3.5-4b",
            hf_source="   ",
            family="Qwen",
            role="primary",
            size_label="4B",
            notes="Laptop baseline.",
        )


def test_pilot_selection_requires_4b_baseline_winner():
    with pytest.raises(ValidationError):
        PilotSelection(
            baseline_winner_id="qwen2.5-7b-instruct",
            runner_up_id="qwen3.5-4b",
        )


def test_model_artifact_record_defaults_to_local_only():
    record = ModelArtifactRecord(
        candidate_id="qwen3.5-4b",
        artifact_type="adapter",
        version_tag="phase3-smoke",
        local_path=Path("data/models/qwen3.5-4b/adapter.bin"),
        sha256="a" * 64,
    )

    assert record.local_only is True
    assert record.tracked_in_git is False


def test_model_artifact_record_rejects_blank_path():
    with pytest.raises(ValidationError):
        ModelArtifactRecord(
            candidate_id="qwen3.5-4b",
            artifact_type="gguf",
            version_tag="phase3-smoke",
            local_path="   ",
            sha256="b" * 64,
        )


def test_settings_expose_phase3_model_defaults_without_changing_runtime_defaults(monkeypatch: pytest.MonkeyPatch):
    for env_name in (
        "RUNTIME_BACKEND",
        "RUNTIME_PROFILE",
        "RUNTIME_PROFILE_GGUF",
        "RUNTIME_PROFILE_ACCELERATED",
        "MODEL_ARTIFACT_ROOT",
        "MODEL_REGISTRY_PATH",
    ):
        monkeypatch.delenv(env_name, raising=False)

    settings = Settings(_env_file=None)

    assert settings.runtime_backend == "gguf"
    assert settings.runtime_profile == "gguf-laptop"
    assert settings.runtime_profile_gguf == "gguf-laptop"
    assert settings.runtime_profile_accelerated == "accelerated-local"
    assert settings.model_artifact_root == Path("data/models")
    assert settings.model_registry_path == Path("data/manifests/model-registry.json")


def test_release_verdict_and_risky_label_contracts_are_locked():
    verdict_adapter = TypeAdapter(ReleaseVerdict)

    assert verdict_adapter.validate_python("PASS") == "PASS"
    with pytest.raises(ValidationError):
        verdict_adapter.validate_python("WARN")

    audit = HeldOutSupportAudit(
        evaluated_split_path=Path("data/splits/test.jsonl"),
        support_by_label={label: 0 for label in LOCKED_RELEASE_LABELS},
        blocker_reasons=["Missing support for risky label task_scam"],
    )

    assert audit.risky_labels == LOCKED_RISKY_LABELS
    assert audit.risky_recall_floor == UNIFORM_RISKY_RECALL_FLOOR
    assert audit.verdict == "BLOCK"

    row = ReleaseEvaluationRow(
        gold_label="task_scam",
        predicted_labels=["task_scam"],
        risk_tier="high-risk",
        summary="Tin nhan yeu cau chuyen tien vao tai khoan la dau hieu lua dao.",
        top_cues=[SuspiciousCue(span="chuyen tien", reason="yeu cau chuyen tien gap")],
        recommendations=["Khong chuyen tien truoc khi xac minh."],
        backend_name="gguf-laptop",
        split_provenance="data/splits/test.jsonl",
        reviewable_source_text="Anh chuyen tien gap vao tai khoan nay giup em.",
    )

    assert row.channel == "unknown"

    with pytest.raises(ValidationError):
        ReleaseEvaluationRow(
            gold_label="task_scam",
            predicted_labels=["task_scam"],
            risk_tier="high-risk",
            summary="Tin nhan yeu cau chuyen tien vao tai khoan la dau hieu lua dao.",
            top_cues=[SuspiciousCue(span="chuyen tien", reason="yeu cau chuyen tien gap")],
            recommendations=["Khong chuyen tien truoc khi xac minh."],
            backend_name="gguf-laptop",
            split_provenance="data/splits/test.jsonl",
        )


def test_release_artifact_requires_metrics_reasons_and_rubric_summary():
    overall_metrics = OverallMetricSummary(
        macro_f1=0.91,
        weighted_f1=0.93,
        evaluated_rows=12,
    )
    per_label_metrics = [
        PerLabelMetricRow(
            label=label,
            precision=0.9,
            recall=0.9,
            f1=0.9,
            support=1,
        )
        for label in LOCKED_RELEASE_LABELS
    ]
    rubric_summary = ExplanationRubricSummary(
        evaluated_risky_predictions=3,
        manual_reviewed_predictions=2,
        blocker_reasons=[],
        flag_reasons=["One prediction used generic safe advice."],
    )

    artifact = ReleaseEvaluationArtifact(
        run_id="phase5-run-001",
        verdict="FLAG",
        risky_recall_floor=UNIFORM_RISKY_RECALL_FLOOR,
        overall_metrics=overall_metrics,
        per_label_metrics=per_label_metrics,
        blocker_reasons=[],
        flag_reasons=["One prediction used generic safe advice."],
        explanation_rubric_summary=rubric_summary,
    )

    assert artifact.verdict == "FLAG"
    assert artifact.explanation_rubric_summary.manual_reviewed_predictions == 2

    with pytest.raises(ValidationError):
        ReleaseEvaluationArtifact(
            run_id="phase5-run-001",
            verdict="PASS",
            risky_recall_floor=UNIFORM_RISKY_RECALL_FLOOR,
            per_label_metrics=per_label_metrics,
            blocker_reasons=[],
            flag_reasons=[],
        )