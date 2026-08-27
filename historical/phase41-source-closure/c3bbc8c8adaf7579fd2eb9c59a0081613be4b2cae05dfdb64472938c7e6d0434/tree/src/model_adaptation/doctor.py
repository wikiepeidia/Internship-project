"""Local readiness checks and smoke guidance for Phase 3 training."""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

from src.config.settings import get_settings
from src.model_adaptation.registry import load_model_registry
from src.model_adaptation.phase40_modes import (
    AdaptationMode,
    ExperimentIdentity,
    ModelFamily,
    QwenPreloadCapabilities,
    RunKind,
    prove_qwen_preload,
)
from src.model_adaptation.training import _resolve_base_model_path, build_training_config
from src.runtime.contracts import DoctorCheck, DoctorStatus


INSTALL_COMMAND = "python -m pip install -e .[dev,train]"
QLORA_ENVIRONMENT_REMEDIATION = (
    "Verify CUDA and obtain operator approval before installing bitsandbytes==0.50.1"
)
TEST_COMMAND = "python -m pytest tests/model_adaptation -q"


def _doctor_command(candidate: str, adaptation_mode: AdaptationMode) -> str:
    return (
        "python -m src.model_adaptation.cli doctor "
        f"--candidate {candidate} --adaptation-mode {adaptation_mode.value}"
    )


def _smoke_command(candidate: str, adaptation_mode: AdaptationMode) -> str:
    return (
        "python -m src.model_adaptation.cli train "
        f"--candidate {candidate} --adaptation-mode {adaptation_mode.value} "
        "--run-kind probe --version-tag phase40-smoke --smoke-test"
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
        adaptation_mode: AdaptationMode | str,
        train_split: Path | None = None,
        val_split: Path | None = None,
        output_root: Path | None = None,
        registry_path: Path | None = None,
    ) -> None:
        self.candidate = candidate
        self.adaptation_mode = AdaptationMode(adaptation_mode)
        self.doctor_command = _doctor_command(candidate, self.adaptation_mode)
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
                        remediation_command=self.doctor_command,
                    )
                )
        else:
            checks.append(
                DoctorCheck(
                    name="model-registry",
                    passed=False,
                    detail=f"Missing model registry: {self.registry_path}",
                    remediation_command=self.doctor_command,
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
                    remediation_command=self.doctor_command,
                )
            )
        else:
            checks.append(
                DoctorCheck(
                    name="candidate-selection",
                    passed=False,
                    detail="Model registry does not contain a pilot selection.",
                    remediation_command=self.doctor_command,
                )
            )

        checks.extend(
            [
                DoctorCheck(
                    name="train-split",
                    passed=self.train_split.exists(),
                    detail=f"train_split={self.train_split}",
                    remediation_command=self.doctor_command,
                ),
                DoctorCheck(
                    name="val-split",
                    passed=self.val_split.exists(),
                    detail=f"val_split={self.val_split}",
                    remediation_command=self.doctor_command,
                ),
            ]
        )

        checks.append(self._check_output_root_without_creating())

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
                    adaptation_mode=self.adaptation_mode,
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
                        remediation_command=self.doctor_command,
                    )
                )

        checks.append(self._check_device())
        checks.append(self._check_mode_support())

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

        if self.adaptation_mode == AdaptationMode.QLORA:
            return DoctorCheck(
                name="training-device",
                passed=False,
                detail="QLoRA NOT READY: CUDA is unavailable; no LoRA fallback is permitted.",
                remediation_command=self.doctor_command,
            )
        return DoctorCheck(
            name="training-device",
            passed=True,
            detail="LoRA mode can run without consulting the bitsandbytes runtime.",
        )

    def _check_output_root_without_creating(self) -> DoctorCheck:
        if self.output_root.exists():
            passed = self.output_root.is_dir() and os.access(self.output_root, os.W_OK)
            return DoctorCheck(
                name="output-root",
                passed=passed,
                detail=(
                    f"Existing writable output root: {self.output_root}"
                    if passed
                    else f"Output root is not a writable directory: {self.output_root}"
                ),
                remediation_command=None if passed else self.doctor_command,
            )
        ancestor = self.output_root.parent
        while not ancestor.exists() and ancestor != ancestor.parent:
            ancestor = ancestor.parent
        passed = ancestor.is_dir() and os.access(ancestor, os.W_OK)
        return DoctorCheck(
            name="output-root",
            passed=passed,
            detail=(
                f"Output root is absent and was not created; writable ancestor={ancestor}"
                if passed
                else f"Output root is absent and no writable ancestor was found: {self.output_root}"
            ),
            remediation_command=None if passed else self.doctor_command,
        )

    def _collect_preload_capabilities(self) -> QwenPreloadCapabilities:
        try:
            torch_module = importlib.import_module("torch")
            transformers_module = importlib.import_module("transformers")
            peft_module = importlib.import_module("peft")
        except ImportError:
            return QwenPreloadCapabilities(False, False, None, False, None, False)
        try:
            bitsandbytes_module = importlib.import_module("bitsandbytes")
        except ImportError:
            bitsandbytes_module = None
        linear4bit_type = (
            getattr(getattr(bitsandbytes_module, "nn", None), "Linear4bit", None)
            if bitsandbytes_module is not None
            else None
        )
        return QwenPreloadCapabilities(
            cuda_available=bool(torch_module.cuda.is_available()),
            bitsandbytes_imported=bitsandbytes_module is not None,
            bitsandbytes_version=(
                str(getattr(bitsandbytes_module, "__version__", ""))
                if bitsandbytes_module is not None
                else None
            ),
            bitsandbytes_config_available=hasattr(transformers_module, "BitsAndBytesConfig"),
            linear4bit_type=linear4bit_type,
            kbit_preparation_available=hasattr(peft_module, "prepare_model_for_kbit_training"),
        )

    def _check_mode_support(self) -> DoctorCheck:
        if self.adaptation_mode == AdaptationMode.LORA:
            return DoctorCheck(
                name="adaptation-mode:lora",
                passed=True,
                detail="LoRA READY: non-quantized mode does not consult bitsandbytes.",
            )
        identity = ExperimentIdentity(ModelFamily.QWEN, self.adaptation_mode, RunKind.FULL)
        try:
            proof = prove_qwen_preload(identity, self._collect_preload_capabilities())
        except RuntimeError as exc:
            return DoctorCheck(
                name="adaptation-mode:qlora",
                passed=False,
                detail=f"QLoRA NOT READY: {exc}",
                remediation_command=QLORA_ENVIRONMENT_REMEDIATION,
            )
        return DoctorCheck(
            name="adaptation-mode:qlora",
            passed=True,
            detail=(
                "QLoRA Stage 1 READY: model-level NF4, Linear4bit, frozen-base, and "
                f"gradient proof remain required after load (bitsandbytes={proof.bitsandbytes_version})."
            ),
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
        if self.doctor_command not in steps:
            steps.append(self.doctor_command)
        smoke_command = _smoke_command(self.candidate, self.adaptation_mode)
        if smoke_command not in steps:
            steps.append(smoke_command)
        return steps


def run_training_doctor(
    *,
    candidate: str = "baseline-winner",
    adaptation_mode: AdaptationMode | str,
    train_split: Path | None = None,
    val_split: Path | None = None,
    output_root: Path | None = None,
    registry_path: Path | None = None,
) -> DoctorStatus:
    """Run the Phase 3 training readiness checks."""

    return TrainingDoctor(
        candidate=candidate,
        adaptation_mode=adaptation_mode,
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
