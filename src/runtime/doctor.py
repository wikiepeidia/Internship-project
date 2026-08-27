"""Local readiness checks and guidance for the promoted Phase 4 runtime."""

import importlib
from pathlib import Path
import sys

from src.artifacts import load_release_evaluation_artifact
from src.config.settings import MINIMUM_PYTHON_VERSION
from src.config.settings import get_runtime_settings as get_settings
from src.core.integrity import IntegrityError, reject_redirecting_ancestry
from src.runtime.analyzers.accelerated import AcceleratedAnalyzer
from src.runtime.analyzers.gguf import GGUFAnalyzer
from src.runtime.analyzers.heuristic import HeuristicAnalyzer
from src.runtime.contracts import DoctorCheck, DoctorStatus


INSTALL_COMMAND = "python -m pip install -e .[dev]"
TEST_COMMAND = "python -m pytest tests/runtime -q"
DOCTOR_COMMAND = "python -m src.runtime.cli doctor"
RELEASE_MANIFEST_PATTERNS = (
    "release-evaluation-*.json",
    "phase5-release-eval-*.json",
)


class RuntimeDoctor:
    """Evaluate whether the selected local runtime is ready for use."""

    def run(self) -> DoctorStatus:
        checks: list[DoctorCheck] = []

        checks.append(self._check_python_version())
        checks.extend(self._check_required_imports())

        settings = None
        try:
            settings = get_settings()
            checks.append(
                DoctorCheck(
                    name="settings-load",
                    passed=True,
                    detail="Runtime settings loaded successfully.",
                )
            )
        except Exception as exc:
            checks.append(
                DoctorCheck(
                    name="settings-load",
                    passed=False,
                    detail=f"Runtime settings failed to load: {exc}",
                    remediation_command=INSTALL_COMMAND,
                )
            )

        backend_name = "unknown"
        supported_backends = {"heuristic", "gguf", "accelerated"}
        if settings is not None:
            backend_name = settings.runtime_backend
            runtime_profile = getattr(
                settings,
                "runtime_profile",
                "heuristic" if settings.runtime_backend == "heuristic" else "",
            )
            gguf_profiles = {
                getattr(settings, "runtime_profile_gguf", "gguf-laptop"),
                getattr(settings, "runtime_profile_gguf_runner_up", "gguf-runner-up"),
            }
            accelerated_profile = getattr(settings, "runtime_profile_accelerated", "accelerated-local")
            checks.extend(
                [
                    DoctorCheck(
                        name="runtime-backend",
                        passed=settings.runtime_backend in supported_backends,
                        detail=f"settings.runtime_backend={settings.runtime_backend!r}",
                        remediation_command=DOCTOR_COMMAND,
                    ),
                    DoctorCheck(
                        name="runtime-profile",
                        passed=(
                            runtime_profile == "heuristic"
                            if settings.runtime_backend == "heuristic"
                            else runtime_profile in gguf_profiles
                            if settings.runtime_backend == "gguf"
                            else runtime_profile == accelerated_profile
                        ),
                        detail=f"runtime_profile={runtime_profile}",
                        remediation_command=DOCTOR_COMMAND,
                    ),
                    DoctorCheck(
                        name="runtime-max-cues",
                        passed=settings.runtime_max_cues == 3,
                        detail=f"runtime_max_cues={settings.runtime_max_cues}",
                        remediation_command=DOCTOR_COMMAND,
                    ),
                    DoctorCheck(
                        name="runtime-fail-closed",
                        passed=settings.runtime_fail_closed is True,
                        detail=f"runtime_fail_closed={settings.runtime_fail_closed}",
                        remediation_command=DOCTOR_COMMAND,
                    ),
                    DoctorCheck(
                        name="runtime-store-raw-text",
                        passed=settings.runtime_store_raw_text is False,
                        detail=f"runtime_store_raw_text={settings.runtime_store_raw_text}",
                        remediation_command=DOCTOR_COMMAND,
                    ),
                ]
            )

            if settings.runtime_backend == "heuristic":
                backend_status = HeuristicAnalyzer().doctor()
            elif settings.runtime_backend == "gguf":
                backend_status = GGUFAnalyzer(
                    registry_path=settings.resolved_model_registry_path,
                    artifact_root=settings.resolved_model_artifact_root,
                    storage_root=settings.resolved_model_storage_root,
                    runtime_profile=settings.runtime_profile,
                ).doctor()
            elif settings.runtime_backend == "accelerated":
                backend_status = AcceleratedAnalyzer(
                    registry_path=settings.resolved_model_registry_path,
                    artifact_root=settings.resolved_model_artifact_root,
                    storage_root=settings.resolved_model_storage_root,
                    runtime_profile=runtime_profile,
                ).doctor()
            else:
                backend_status = DoctorStatus(
                    ready=False,
                    backend_name=settings.runtime_backend,
                    checks=[],
                    setup_steps=[DOCTOR_COMMAND],
                )

            checks.append(
                DoctorCheck(
                    name="backend-ready",
                    passed=backend_status.ready,
                    detail=f"backend={backend_status.backend_name} ready={backend_status.ready}",
                    remediation_command=(backend_status.setup_steps[0] if backend_status.setup_steps else DOCTOR_COMMAND),
                )
            )

        release_root = settings.runtime_release_manifest_root if settings is not None else None
        checks.append(self._check_latest_release_gate_summary(release_root))

        ready = all(check.passed for check in checks)
        setup_steps = self._build_setup_steps(checks)

        return DoctorStatus(
            ready=ready,
            backend_name=backend_name,
            checks=checks,
            setup_steps=setup_steps,
        )

    def _check_python_version(self) -> DoctorCheck:
        version_ok = sys.version_info >= MINIMUM_PYTHON_VERSION
        detail = f"python={sys.version_info.major}.{sys.version_info.minor}"
        return DoctorCheck(
            name="python-version",
            passed=version_ok,
            detail=detail,
            remediation_command=None if version_ok else DOCTOR_COMMAND,
        )

    def _check_required_imports(self) -> list[DoctorCheck]:
        checks: list[DoctorCheck] = []
        for module_name in ("ftfy", "pydantic", "pydantic_settings"):
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

    def _build_setup_steps(self, checks: list[DoctorCheck]) -> list[str]:
        steps: list[str] = []
        for check in checks:
            if check.passed or not check.remediation_command:
                continue
            if check.remediation_command not in steps:
                steps.append(check.remediation_command)
        if not steps:
            return []
        if TEST_COMMAND not in steps:
            steps.append(TEST_COMMAND)
        if DOCTOR_COMMAND not in steps:
            steps.append(DOCTOR_COMMAND)
        return steps

    def _check_latest_release_gate_summary(self, release_root: Path | None) -> DoctorCheck:
        if release_root is None:
            return DoctorCheck(
                name="release-gate-summary",
                passed=False,
                detail="Release evidence root is unavailable because settings did not load.",
                remediation_command=DOCTOR_COMMAND,
            )
        try:
            root = reject_redirecting_ancestry(release_root, where="release manifest root")
        except IntegrityError as exc:
            return DoctorCheck(
                name="release-gate-summary",
                passed=False,
                detail=f"Release evidence root is unsafe: {exc}",
                remediation_command=DOCTOR_COMMAND,
            )
        if not root.is_dir():
            return DoctorCheck(
                name="release-gate-summary",
                passed=False,
                detail=f"Release evidence root is missing: {root}",
                remediation_command=DOCTOR_COMMAND,
            )
        artifact_set = {
            path
            for pattern in RELEASE_MANIFEST_PATTERNS
            for path in root.glob(pattern)
        }
        artifacts = sorted(
            artifact_set,
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        if not artifacts:
            return DoctorCheck(
                name="release-gate-summary",
                passed=False,
                detail=f"No release evaluation artifact found in {root}.",
                remediation_command=DOCTOR_COMMAND,
            )

        latest_path = artifacts[0]
        try:
            artifact = load_release_evaluation_artifact(latest_path)
        except Exception as exc:
            return DoctorCheck(
                name="release-gate-summary",
                passed=False,
                detail=f"Failed to read latest release artifact: {exc}",
                remediation_command=DOCTOR_COMMAND,
            )

        return DoctorCheck(
            name="release-gate-summary",
            passed=artifact.verdict == "PASS",
            detail=(
                f"latest_verdict={artifact.verdict} run_id={artifact.run_id} "
                f"manifest={latest_path}"
            ),
            remediation_command=(
                None if artifact.verdict == "PASS" else DOCTOR_COMMAND
            ),
        )


def run_runtime_doctor() -> DoctorStatus:
    """Run the local readiness checks for the Phase 4 runtime."""

    return RuntimeDoctor().run()


def format_doctor_report(status: DoctorStatus) -> str:
    """Format a concise terminal report for runtime readiness."""

    header = (
        f"READY backend={status.backend_name} local_only={status.local_only} text_only={status.text_only}"
        if status.ready
        else f"NOT READY backend={status.backend_name} local_only={status.local_only} text_only={status.text_only}"
    )

    lines = [header]
    lines.extend(
        f"- {check.name}: {'PASS' if check.passed else 'FAIL'} - {check.detail}"
        for check in status.checks
    )

    if status.setup_steps:
        lines.append("Setup steps:")
        lines.extend(f"- {step}" for step in status.setup_steps)

    return "\n".join(lines)
