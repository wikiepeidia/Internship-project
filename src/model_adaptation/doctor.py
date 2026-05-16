"""Local readiness checks and smoke guidance for Phase 3 training."""

from __future__ import annotations

import importlib
import importlib.util
import sys
from pathlib import Path

from src.config.settings import get_settings
from src.model_adaptation.registry import load_model_registry
from src.model_adaptation.training import _resolve_base_model_path, build_training_config
from src.runtime.contracts import DoctorCheck, DoctorStatus


INSTALL_COMMAND = "python -m pip install -e .[dev,train]"
TEST_COMMAND = "python -m pytest tests/model_adaptation -q"
DOCTOR_COMMAND = "python -m src.model_adaptation.cli doctor --candidate baseline-winner"


def _smoke_command(candidate: str) -> str:
    return (
        "python -m src.model_adaptation.cli train "
        f"--candidate {candidate} --version-tag phase3-smoke --smoke-test"
    )


def _resolve_candidate_alias(candidate_arg: str, baseline_winner_id: str, runner_up_id: str) -> str:
    if candidate_arg == "baseline-winner":
        return baseline_winner_id
    if candidate_arg == "runner-up":
        return runner_up_id
    return candidate_arg


class TrainingDoctor:
    """Evaluate whether the local Phase 3 training stack is ready."""

    def __init__(
        self,
        *,
        candidate: str = "baseline-winner",
        train_split: Path | None = None,
        val_split: Path | None = None,
        output_root: Path | None = None,
        registry_path: Path | None = None,
    ) -> None:
        self.candidate = candidate
        settings = get_settings()
        self.train_split = train_split or (settings.data_dir / "splits" / "train.jsonl")
        self.val_split = val_split or (settings.data_dir / "splits" / "val.jsonl")
        self.output_root = output_root or settings.model_artifact_root
        self.registry_path = registry_path or settings.model_registry_path

    def run(self) -> DoctorStatus:
        checks: list[DoctorCheck] = []
        checks.append(self._check_python_version())
        checks.extend(self._check_required_imports())

        registry = None
        selection = None
        resolved_candidate_id = self.candidate

        if self.registry_path.exists():
            try:
                registry = load_model_registry(self.registry_path)
                selection = registry.selection
                checks.append(
                    DoctorCheck(
                        name="model-registry",
                        passed=True,
                        detail=f"Loaded model registry from {self.registry_path}",
                    )
                )
            except Exception as exc:
                checks.append(
                    DoctorCheck(
                        name="model-registry",
                        passed=False,
                        detail=f"Failed to load model registry: {exc}",
                        remediation_command=DOCTOR_COMMAND,
                    )
                )
        else:
            checks.append(
                DoctorCheck(
                    name="model-registry",
                    passed=False,
                    detail=f"Missing model registry: {self.registry_path}",
                    remediation_command=DOCTOR_COMMAND,
                )
            )

        if selection is not None:
            resolved_candidate_id = _resolve_candidate_alias(
                self.candidate,
                selection.baseline_winner_id,
                selection.runner_up_id,
            )
            selected_candidates = {selection.baseline_winner_id, selection.runner_up_id}
            checks.append(
                DoctorCheck(
                    name="candidate-selection",
                    passed=resolved_candidate_id in selected_candidates,
                    detail=(
                        f"candidate={resolved_candidate_id} baseline={selection.baseline_winner_id} "
                        f"runner-up={selection.runner_up_id}"
                    ),
                    remediation_command=DOCTOR_COMMAND,
                )
            )
        else:
            checks.append(
                DoctorCheck(
                    name="candidate-selection",
                    passed=False,
                    detail="Model registry does not contain a pilot selection.",
                    remediation_command=DOCTOR_COMMAND,
                )
            )

        checks.extend(
            [
                DoctorCheck(
                    name="train-split",
                    passed=self.train_split.exists(),
                    detail=f"train_split={self.train_split}",
                    remediation_command=DOCTOR_COMMAND,
                ),
                DoctorCheck(
                    name="val-split",
                    passed=self.val_split.exists(),
                    detail=f"val_split={self.val_split}",
                    remediation_command=DOCTOR_COMMAND,
                ),
            ]
        )

        try:
            self.output_root.mkdir(parents=True, exist_ok=True)
            checks.append(
                DoctorCheck(
                    name="output-root",
                    passed=True,
                    detail=f"Writable output root: {self.output_root}",
                )
            )
        except Exception as exc:
            checks.append(
                DoctorCheck(
                    name="output-root",
                    passed=False,
                    detail=f"Failed to prepare output root {self.output_root}: {exc}",
                    remediation_command=DOCTOR_COMMAND,
                )
            )

        if selection is not None and resolved_candidate_id in {selection.baseline_winner_id, selection.runner_up_id}:
            try:
                config = build_training_config(
                    candidate_id=resolved_candidate_id,
                    train_split_path=self.train_split,
                    val_split_path=self.val_split,
                    version_tag="phase3-doctor",
                    output_root=self.output_root,
                    registry_path=self.registry_path,
                    selection=selection,
                )
                base_model_path = _resolve_base_model_path(config)
                checks.append(
                    DoctorCheck(
                        name="base-model-path",
                        passed=True,
                        detail=f"Resolved base model for {resolved_candidate_id}: {base_model_path}",
                    )
                )
            except Exception as exc:
                checks.append(
                    DoctorCheck(
                        name="base-model-path",
                        passed=False,
                        detail=f"Failed to resolve base model for {resolved_candidate_id}: {exc}",
                        remediation_command=DOCTOR_COMMAND,
                    )
                )

        checks.append(self._check_device())
        checks.append(self._check_optional_quantization_support())

        ready = all(check.passed for check in checks)
        return DoctorStatus(
            ready=ready,
            backend_name="training",
            checks=checks,
            setup_steps=self._build_setup_steps(checks),
        )

    def _check_python_version(self) -> DoctorCheck:
        version_ok = sys.version_info >= (3, 12)
        return DoctorCheck(
            name="python-version",
            passed=version_ok,
            detail=f"python={sys.version_info.major}.{sys.version_info.minor}",
            remediation_command=None if version_ok else INSTALL_COMMAND,
        )

    def _check_required_imports(self) -> list[DoctorCheck]:
        checks: list[DoctorCheck] = []
        for module_name in ("torch", "transformers", "peft", "accelerate"):
            try:
                importlib.import_module(module_name)
                checks.append(
                    DoctorCheck(
                        name=f"import:{module_name}",
                        passed=True,
                        detail=f"Imported {module_name} successfully.",
                    )
                )
            except ImportError:
                checks.append(
                    DoctorCheck(
                        name=f"import:{module_name}",
                        passed=False,
                        detail=f"Missing required dependency: {module_name}",
                        remediation_command=INSTALL_COMMAND,
                    )
                )
        return checks

    def _check_device(self) -> DoctorCheck:
        try:
            torch_module = importlib.import_module("torch")
        except ImportError:
            return DoctorCheck(
                name="training-device",
                passed=False,
                detail="torch is unavailable, so device readiness cannot be evaluated.",
                remediation_command=INSTALL_COMMAND,
            )

        if torch_module.cuda.is_available():
            total_memory_gib = torch_module.cuda.get_device_properties(0).total_memory / (1024**3)
            return DoctorCheck(
                name="training-device",
                passed=True,
                detail=(
                    f"CUDA ready on {torch_module.cuda.get_device_name(0)} "
                    f"with ~{total_memory_gib:.2f} GiB VRAM"
                ),
            )

        return DoctorCheck(
            name="training-device",
            passed=True,
            detail="CUDA unavailable; training will fall back to CPU and smoke tests may run slowly.",
        )

    def _check_optional_quantization_support(self) -> DoctorCheck:
        if importlib.util.find_spec("bitsandbytes") is None:
            return DoctorCheck(
                name="optional:bitsandbytes",
                passed=True,
                detail="bitsandbytes is not installed; the trainer will use full-precision LoRA instead of 4-bit QLoRA.",
            )
        return DoctorCheck(
            name="optional:bitsandbytes",
            passed=True,
            detail="bitsandbytes is available for 4-bit QLoRA loading when CUDA is present.",
        )

    def _build_setup_steps(self, checks: list[DoctorCheck]) -> list[str]:
        steps: list[str] = []
        for check in checks:
            if check.passed or not check.remediation_command:
                continue
            if check.remediation_command not in steps:
                steps.append(check.remediation_command)

        if TEST_COMMAND not in steps:
            steps.append(TEST_COMMAND)
        if DOCTOR_COMMAND not in steps:
            steps.append(DOCTOR_COMMAND)
        smoke_command = _smoke_command(self.candidate)
        if smoke_command not in steps:
            steps.append(smoke_command)
        return steps


def run_training_doctor(
    *,
    candidate: str = "baseline-winner",
    train_split: Path | None = None,
    val_split: Path | None = None,
    output_root: Path | None = None,
    registry_path: Path | None = None,
) -> DoctorStatus:
    """Run the Phase 3 training readiness checks."""

    return TrainingDoctor(
        candidate=candidate,
        train_split=train_split,
        val_split=val_split,
        output_root=output_root,
        registry_path=registry_path,
    ).run()


def format_training_doctor_report(status: DoctorStatus) -> str:
    """Format a concise terminal report for training readiness."""

    header = f"READY backend={status.backend_name}" if status.ready else f"NOT READY backend={status.backend_name}"
    lines = [header]
    lines.extend(
        f"- {check.name}: {'PASS' if check.passed else 'FAIL'} - {check.detail}"
        for check in status.checks
    )

    if status.setup_steps:
        lines.append("Suggested next steps:")
        lines.extend(f"- {step}" for step in status.setup_steps)

    return "\n".join(lines)