"""Wave 0 and Phase 3 doctor expectations for the local runtime."""

import importlib
from pathlib import Path

from src.model_adaptation.schemas import PilotSelection
from src.model_adaptation.training import build_training_config, save_adapter_artifacts


def _load_doctor_module():
    return importlib.import_module("src.runtime.doctor")


def _selection() -> PilotSelection:
    return PilotSelection(
        baseline_winner_id="qwen3.5-4b",
        runner_up_id="qwen2.5-7b-instruct",
        selection_notes="Winner and runner-up selected in the pilot.",
    )


def _stage_accelerated_registry(tmp_path: Path) -> Path:
    registry_path = tmp_path / "manifests" / "model-registry.json"
    config = build_training_config(
        candidate_id="qwen2.5-7b-instruct",
        train_split_path=tmp_path / "splits" / "train.jsonl",
        val_split_path=tmp_path / "splits" / "val.jsonl",
        version_tag="phase3-smoke",
        output_root=tmp_path / "models",
        registry_path=registry_path,
        selection=_selection(),
        dry_run=True,
    )
    save_adapter_artifacts(config, selection=_selection())
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
                backend_name="heuristic",
                checks=[
                    doctor_module.DoctorCheck(
                        name="backend",
                        passed=False,
                        detail="Heuristic backend is unavailable.",
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

    class FakeSettings:
        runtime_backend = "accelerated"
        runtime_profile = "accelerated-local"
        runtime_profile_gguf = "gguf-laptop"
        runtime_profile_gguf_runner_up = "gguf-runner-up"
        runtime_profile_accelerated = "accelerated-local"
        model_registry_path = registry_path
        runtime_max_cues = 3
        runtime_fail_closed = True
        runtime_store_raw_text = False

    monkeypatch.setattr(doctor_module, "get_settings", lambda: FakeSettings())

    status = doctor_module.run_runtime_doctor()
    report = doctor_module.format_doctor_report(status)

    assert status.ready is True
    assert status.backend_name == "accelerated"
    assert "accelerated-local" in report
    assert "cloud" not in report.casefold()