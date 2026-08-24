"""Wave 0 and Phase 3 doctor expectations for the local runtime."""

import importlib
import json
from pathlib import Path

import src.runtime.analyzers.accelerated as accelerated_module
import src.runtime.analyzers.gguf as gguf_module
from src.model_adaptation.convert import build_gguf_request, convert_to_gguf
from src.model_adaptation.phase40_modes import AdaptationMode
from src.model_adaptation.schemas import (
    ExplanationRubricSummary,
    HeldOutSupportAudit,
    LOCKED_RELEASE_LABELS,
    OverallMetricSummary,
    PerLabelMetricRow,
    PilotSelection,
    ReleaseEvaluationArtifact,
)
from src.model_adaptation.training import build_training_config, save_adapter_artifacts


def _load_doctor_module():
    return importlib.import_module("src.runtime.doctor")


def _selection() -> PilotSelection:
    return PilotSelection(
        baseline_winner_id="qwen3-4b-instruct-2507",
        runner_up_id="qwen3.5-4b",
        selection_notes="Winner and runner-up selected in the pilot.",
    )


def _stage_accelerated_registry(tmp_path: Path) -> Path:
    registry_path = tmp_path / "manifests" / "model-registry.json"
    (tmp_path / "models" / "base" / "qwen3.5-4b").mkdir(parents=True, exist_ok=True)
    config = build_training_config(
        candidate_id="qwen3.5-4b",
        train_split_path=tmp_path / "splits" / "train.jsonl",
        val_split_path=tmp_path / "splits" / "val.jsonl",
        version_tag="phase3-smoke",
        output_root=tmp_path / "models",
        registry_path=registry_path,
        selection=_selection(),
        adaptation_mode=AdaptationMode.LORA,
        dry_run=True,
    )
    save_adapter_artifacts(config, selection=_selection())
    return registry_path


def _stage_gguf_registry(tmp_path: Path) -> Path:
    registry_path = tmp_path / "manifests" / "model-registry-gguf.json"
    (tmp_path / "models" / "base" / "qwen3-4b-instruct-2507").mkdir(parents=True, exist_ok=True)
    config = build_training_config(
        candidate_id="qwen3-4b-instruct-2507",
        train_split_path=tmp_path / "splits" / "train.jsonl",
        val_split_path=tmp_path / "splits" / "val.jsonl",
        version_tag="phase3-smoke",
        output_root=tmp_path / "models",
        registry_path=registry_path,
        selection=_selection(),
        adaptation_mode=AdaptationMode.LORA,
        dry_run=True,
    )
    save_adapter_artifacts(config, selection=_selection())
    request = build_gguf_request(
        "qwen3-4b-instruct-2507",
        "phase3-smoke",
        registry_path=registry_path,
        output_root=tmp_path / "models",
        selection=_selection(),
    )
    convert_to_gguf(request, registry_path=registry_path, selection=_selection(), dry_run=True)
    return registry_path


def test_doctor_reports_missing_runtime_dependency_with_exact_command(monkeypatch):
    doctor_module = _load_doctor_module()

    real_import_module = doctor_module.importlib.import_module

    def fake_import_module(name: str):
        if name == "ftfy":
            raise ImportError("ftfy missing")
        return real_import_module(name)

    monkeypatch.setattr(doctor_module.importlib, "import_module", fake_import_module)

    status = doctor_module.run_runtime_doctor()
    report = doctor_module.format_doctor_report(status)

    assert status.ready is False
    assert any(
        check.remediation_command == "python -m pip install -e .[dev]"
        for check in status.checks
    )
    assert "python -m pip install -e .[dev]" in report
    assert "cloud" not in report.casefold()
    assert "api key" not in report.casefold()


def test_analyze_self_check_returns_setup_guidance_when_backend_unavailable(monkeypatch):
    doctor_module = _load_doctor_module()

    class FakeDoctor:
        def run(self):
            return doctor_module.DoctorStatus(
                ready=False,
                backend_name="gguf",
                checks=[
                    doctor_module.DoctorCheck(
                        name="backend",
                        passed=False,
                        detail="GGUF backend is unavailable.",
                        remediation_command="python -m src.runtime.cli doctor",
                    )
                ],
                setup_steps=["python -m src.runtime.cli doctor"],
            )

    monkeypatch.setattr(doctor_module, "RuntimeDoctor", lambda: FakeDoctor())

    status = doctor_module.run_runtime_doctor()
    report = doctor_module.format_doctor_report(status)

    assert status.ready is False
    assert status.setup_steps == ["python -m src.runtime.cli doctor"]
    assert "python -m src.runtime.cli doctor" in report


def test_doctor_rejects_non_local_backend_configuration(monkeypatch):
    doctor_module = _load_doctor_module()

    class FakeSettings:
        runtime_backend = "remote"
        runtime_max_cues = 3
        runtime_fail_closed = True
        runtime_store_raw_text = False

    monkeypatch.setattr(doctor_module, "get_settings", lambda: FakeSettings())

    status = doctor_module.run_runtime_doctor()
    report = doctor_module.format_doctor_report(status)

    assert status.ready is False
    assert status.backend_name == "remote"
    assert any(check.name == "runtime-backend" and check.passed is False for check in status.checks)
    assert "cloud" not in report.casefold()
    assert "api key" not in report.casefold()


def test_doctor_reports_profile_specific_readiness_for_accelerated_backend(tmp_path, monkeypatch):
    doctor_module = _load_doctor_module()
    registry_path = _stage_accelerated_registry(tmp_path)

    settings = type(
        "FakeSettings",
        (),
        {
            "runtime_backend": "accelerated",
            "runtime_profile": "accelerated-local",
            "runtime_profile_gguf": "gguf-laptop",
            "runtime_profile_gguf_runner_up": "gguf-runner-up",
            "runtime_profile_accelerated": "accelerated-local",
            "model_registry_path": registry_path,
            "model_artifact_root": tmp_path / "models",
            "runtime_max_cues": 3,
            "runtime_fail_closed": True,
            "runtime_store_raw_text": False,
        },
    )()

    monkeypatch.setattr(doctor_module, "get_settings", lambda: settings)
    monkeypatch.setattr(accelerated_module, "get_settings", lambda: settings)
    monkeypatch.setattr(
        doctor_module.AcceleratedAnalyzer,
        "_load_runtime",
        lambda self, *, adapter_path, base_model_path: {"adapter_path": adapter_path, "base_model_path": base_model_path},
    )

    status = doctor_module.run_runtime_doctor()
    report = doctor_module.format_doctor_report(status)

    assert status.ready is True
    assert status.backend_name == "accelerated"
    assert "accelerated-local" in report
    assert "cloud" not in report.casefold()


def test_doctor_uses_gguf_laptop_as_phase_four_default(tmp_path, monkeypatch):
    doctor_module = _load_doctor_module()
    registry_path = _stage_gguf_registry(tmp_path)
    settings = type(
        "FakeSettings",
        (),
        {
            "runtime_backend": "gguf",
            "runtime_profile": "gguf-laptop",
            "runtime_profile_gguf": "gguf-laptop",
            "runtime_profile_gguf_runner_up": "gguf-runner-up",
            "runtime_profile_accelerated": "accelerated-local",
            "model_registry_path": registry_path,
            "model_artifact_root": tmp_path / "models",
            "runtime_max_cues": 3,
            "runtime_fail_closed": True,
            "runtime_store_raw_text": False,
        },
    )()

    monkeypatch.setattr(doctor_module, "get_settings", lambda: settings)
    monkeypatch.setattr(gguf_module, "get_settings", lambda: settings)
    monkeypatch.setattr(
        doctor_module.GGUFAnalyzer,
        "_load_runtime",
        lambda self, artifact_path: {"artifact_path": artifact_path},
    )

    status = doctor_module.run_runtime_doctor()
    report = doctor_module.format_doctor_report(status)

    assert status.ready is True
    assert status.backend_name == "gguf"
    assert "READY backend=gguf" in report
    assert "gguf-laptop" in report


def test_doctor_reads_latest_release_gate_summary(tmp_path, monkeypatch):
    doctor_module = _load_doctor_module()
    manifest_dir = tmp_path / "manifests"
    manifest_dir.mkdir(parents=True)
    artifact = ReleaseEvaluationArtifact(
        run_id="phase5-run-001",
        verdict="FLAG",
        risky_recall_floor=0.9,
        overall_metrics=OverallMetricSummary(macro_f1=0.75, weighted_f1=0.82, evaluated_rows=12),
        per_label_metrics=[
            PerLabelMetricRow(label=label, precision=1.0, recall=1.0, f1=1.0, support=1)
            for label in LOCKED_RELEASE_LABELS
        ],
        blocker_reasons=[],
        flag_reasons=["One risky prediction used generic safe advice."],
        explanation_rubric_summary=ExplanationRubricSummary(
            evaluated_risky_predictions=3,
            manual_reviewed_predictions=3,
            blocker_reasons=[],
            flag_reasons=["One risky prediction used generic safe advice."],
        ),
        readiness_audit=HeldOutSupportAudit(
            evaluated_split_path=Path("data/splits/val.jsonl"),
            support_by_label={label: 1 for label in LOCKED_RELEASE_LABELS},
            blocker_reasons=[],
        ),
    )
    artifact_path = manifest_dir / "phase5-release-eval-phase5-run-001.json"
    artifact_path.write_text(json.dumps(artifact.model_dump(mode="json"), ensure_ascii=False, indent=2), encoding="utf-8")

    settings = type(
        "FakeSettings",
        (),
        {
            "runtime_backend": "heuristic",
            "runtime_profile": "heuristic",
            "runtime_profile_gguf": "gguf-laptop",
            "runtime_profile_gguf_runner_up": "gguf-runner-up",
            "runtime_profile_accelerated": "accelerated-local",
            "model_registry_path": tmp_path / "manifests" / "model-registry.json",
            "runtime_max_cues": 3,
            "runtime_fail_closed": True,
            "runtime_store_raw_text": False,
        },
    )()

    monkeypatch.setattr(doctor_module, "get_settings", lambda: settings)
    monkeypatch.setattr(
        doctor_module.HeuristicAnalyzer,
        "doctor",
        lambda self: doctor_module.DoctorStatus(ready=True, backend_name="heuristic", checks=[], setup_steps=[]),
    )
    monkeypatch.setattr(doctor_module, "RELEASE_MANIFEST_DIR", manifest_dir)

    status = doctor_module.run_runtime_doctor()
    report = doctor_module.format_doctor_report(status)

    assert status.ready is True
    assert "release-gate-summary: PASS - latest_verdict=FLAG" in report
    assert "phase5-run-001" in report
