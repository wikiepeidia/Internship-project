"""Synthetic contracts for phase-neutral modeling boundaries."""

from __future__ import annotations

import ast
import builtins
import importlib
import inspect
import os
from pathlib import Path
import subprocess
import sys
import textwrap

import pytest


REPO_ROOT = Path(__file__).parents[2]
MODELING_FILES = (
    "src/modeling/__init__.py",
    "src/modeling/training.py",
    "src/modeling/inference.py",
    "src/modeling/legacy_adapters.py",
)
BLOCKED_IMPORT_PREFIXES = (
    "src.model_adaptation",
    "torch",
    "transformers",
    "sklearn",
    "bitsandbytes",
    "peft",
    "accelerate",
    "safetensors",
    "underthesea",
    "anthropic",
    "openai",
    "google.generativeai",
)


def _run_isolated_imports() -> subprocess.CompletedProcess[str]:
    script = textwrap.dedent(
        f"""
        import importlib
        import importlib.abc
        import sys

        blocked = {BLOCKED_IMPORT_PREFIXES!r}

        class Blocker(importlib.abc.MetaPathFinder):
            def find_spec(self, fullname, path=None, target=None):
                if any(fullname == item or fullname.startswith(item + ".") for item in blocked):
                    raise ModuleNotFoundError("blocked modeling import: " + fullname)
                return None

        sys.meta_path.insert(0, Blocker())
        for name in (
            "src.modeling",
            "src.modeling.training",
            "src.modeling.inference",
            "src.modeling.legacy_adapters",
        ):
            importlib.import_module(name)
        loaded = sorted(
            name for name in sys.modules
            if any(name == item or name.startswith(item + ".") for item in blocked)
        )
        if loaded:
            raise AssertionError("forbidden modeling imports loaded: " + repr(loaded))
        """
    )
    return subprocess.run(
        [sys.executable, "-c", script],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def test_modeling_ports_import_with_historical_and_optional_graph_blocked() -> None:
    completed = _run_isolated_imports()

    assert completed.returncode == 0, completed.stderr


class _RecordingTrainingBackend:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...], dict[str, object]]] = []

    def build_config(self, *args: object, **kwargs: object) -> object:
        self.calls.append(("build_config", args, kwargs))
        return {"candidate": kwargs["candidate_id"]}

    def train(self, *args: object, **kwargs: object) -> object:
        self.calls.append(("train", args, kwargs))
        return {"status": "synthetic-complete"}


def test_training_service_delegates_once_and_factories_accept_doubles() -> None:
    training = importlib.import_module("src.modeling.training")
    backend = _RecordingTrainingBackend()

    qwen_service = training.qwen_training_service(backend=backend)
    config = qwen_service.build_config(candidate_id="synthetic-qwen")
    result = qwen_service.train(config, data_contract="synthetic-contract")

    assert config == {"candidate": "synthetic-qwen"}
    assert result == {"status": "synthetic-complete"}
    assert backend.calls == [
        ("build_config", (), {"candidate_id": "synthetic-qwen"}),
        ("train", (config,), {"data_contract": "synthetic-contract"}),
    ]
    assert training.phobert_training_service(backend=backend).backend is backend


@pytest.mark.parametrize("method_name", ["build_config", "train"])
def test_training_service_translates_backend_errors_once(method_name: str) -> None:
    training = importlib.import_module("src.modeling.training")

    class ExplodingBackend:
        def build_config(self, *args: object, **kwargs: object) -> object:
            raise ValueError("synthetic config failure")

        def train(self, *args: object, **kwargs: object) -> object:
            raise ValueError("synthetic training failure")

    service = training.TrainingService(backend=ExplodingBackend())

    with pytest.raises(training.TrainingError) as error:
        getattr(service, method_name)("synthetic")

    assert type(error.value.__cause__) is ValueError
    assert error.value.__cause__.__cause__ is None


@pytest.mark.parametrize(
    ("wrapper_name", "error_type"),
    (
        ("build_training_config", ValueError),
        ("run_training", FileNotFoundError),
        ("run_training", RuntimeError),
    ),
)
def test_compatibility_training_wrappers_preserve_frozen_errors(
    monkeypatch: pytest.MonkeyPatch,
    wrapper_name: str,
    error_type: type[Exception],
) -> None:
    adaptation = importlib.import_module("src.model_adaptation.commands.adaptation")
    training = importlib.import_module("src.modeling.training")
    message = f"frozen {error_type.__name__} message"

    class FailingService:
        def build_config(self, *args: object, **kwargs: object) -> object:
            try:
                raise error_type(message)
            except Exception as exc:
                raise training.TrainingError("generic wrapper") from exc

        train = build_config

    monkeypatch.setattr(training, "qwen_training_service", lambda: FailingService())
    with pytest.raises(error_type, match=message) as error:
        getattr(adaptation, wrapper_name)()
    assert type(error.value) is error_type


def test_legacy_training_adapters_are_injectable_without_historical_imports(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapters = importlib.import_module("src.modeling.legacy_adapters")
    calls: list[tuple[str, tuple[object, ...], dict[str, object]]] = []

    def build(*args: object, **kwargs: object) -> object:
        calls.append(("qwen-build", args, kwargs))
        return "qwen-config"

    def run_qwen(*args: object, **kwargs: object) -> object:
        calls.append(("qwen-run", args, kwargs))
        return "qwen-result"

    def build_phobert(*args: object, **kwargs: object) -> object:
        calls.append(("phobert-build", args, kwargs))
        return "phobert-config"

    def run_phobert(*args: object, **kwargs: object) -> object:
        calls.append(("phobert-run", args, kwargs))
        return "phobert-result"

    original_import = builtins.__import__

    def guarded_import(name: str, *args: object, **kwargs: object) -> object:
        if name == "src.model_adaptation" or name.startswith("src.model_adaptation."):
            raise AssertionError(f"injected adapter imported historical module: {name}")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    qwen = adapters.LegacyQwenTrainingAdapter(config_builder=build, runner=run_qwen)
    phobert = adapters.LegacyPhoBertTrainingAdapter(
        config_factory=build_phobert,
        runner=run_phobert,
    )

    qwen_config = qwen.build_config(
        "synthetic-qwen",
        Path("train.jsonl"),
        Path("val.jsonl"),
        "synthetic-v1",
        Path("models"),
        adaptation_mode="qlora",
    )
    assert qwen.train(qwen_config, data_contract="qwen-data") == "qwen-result"
    phobert_config = phobert.build_config(run_id="synthetic-phobert")
    assert phobert.train(phobert_config, "phobert-data") == "phobert-result"
    assert [item[0] for item in calls] == [
        "qwen-build",
        "qwen-run",
        "phobert-build",
        "phobert-run",
    ]


def test_legacy_imports_are_handler_local_fixed_edges() -> None:
    path = REPO_ROOT / "src/modeling/legacy_adapters.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    parents: dict[ast.AST, ast.AST] = {
        child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)
    }
    historical_imports: list[ast.ImportFrom] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and (node.module or "").startswith(
            "src.model_adaptation"
        ):
            historical_imports.append(node)
            parent = parents.get(node)
            while parent is not None and not isinstance(
                parent, (ast.FunctionDef, ast.AsyncFunctionDef)
            ):
                parent = parents.get(parent)
            assert parent is not None, ast.unparse(node)

    imported_modules = {node.module for node in historical_imports}
    assert imported_modules == {
        "src.model_adaptation.training",
        "src.model_adaptation.phobert_training",
    }


def test_inference_service_delegates_once_and_translates_errors() -> None:
    inference = importlib.import_module("src.modeling.inference")
    contracts = importlib.import_module("src.runtime.contracts")
    request = contracts.AnalysisRequest(text="Tin nhan tong hop", channel="sms")
    expected = contracts.AnalysisResult(
        risk_tier="suspicious",
        summary="Synthetic inference result.",
        backend_name="synthetic",
        normalized_text=request.text,
    )

    class Backend:
        backend_name = "synthetic"

        def __init__(self) -> None:
            self.requests: list[object] = []

        def analyze(self, supplied: object) -> object:
            self.requests.append(supplied)
            return expected

    backend = Backend()
    service = inference.InferenceService(backend=backend)

    assert service.infer(request) is expected
    assert backend.requests == [request]

    class ExplodingBackend:
        backend_name = "synthetic"

        def analyze(self, supplied: object) -> object:
            raise LookupError("synthetic inference failure")

    with pytest.raises(inference.InferenceError) as error:
        inference.InferenceService(backend=ExplodingBackend()).infer(request)
    assert type(error.value.__cause__) is LookupError
    assert error.value.__cause__.__cause__ is None


def test_runtime_service_traverses_neutral_inference_port_and_preserves_contract() -> None:
    inference = importlib.import_module("src.modeling.inference")
    settings_module = importlib.import_module("src.config.settings")
    service_module = importlib.import_module("src.runtime.service")
    contracts = importlib.import_module("src.runtime.contracts")
    calls: list[tuple[str, object]] = []

    class Backend:
        backend_name = "synthetic"

        def doctor(self) -> object:
            calls.append(("doctor", None))
            return contracts.DoctorStatus(
                ready=True,
                backend_name=self.backend_name,
                checks=[],
            )

        def analyze(self, request: object) -> object:
            calls.append(("analyze", request))
            return contracts.AnalysisResult(
                risk_tier="high-risk",
                summary="Tin nhan tong hop co dau hieu gia mao.",
                top_cues=[
                    contracts.SuspiciousCue(
                        span="kiem tra",
                        reason="Yeu cau hanh dong khan cap.",
                        cue_type="urgent_action",
                    )
                ],
                threat_labels=["bank_impersonation"],
                recommendations=["Xac minh bang ung dung ngan hang chinh thuc."],
                backend_name=self.backend_name,
                normalized_text=request.text,
            )

    settings = settings_module.RuntimeSettings(
        _env_file=None,
        runtime_backend="heuristic",
        runtime_profile="heuristic",
    )
    runtime = service_module.RuntimeService(backend=Backend(), settings=settings)
    result = runtime.analyze_text(
        "Canh bao dang nhap la, vui long kiem tra ngay.",
        channel="sms",
    )

    assert isinstance(runtime._inference, inference.InferenceService)
    assert [name for name, _ in calls] == ["doctor", "analyze"]
    request = calls[1][1]
    assert request.channel == "sms"
    assert result.model_dump(mode="json") == {
        "risk_tier": "high-risk",
        "summary": "Tin nhan tong hop co dau hieu gia mao.",
        "top_cues": [
            {
                "span": "kiem tra",
                "reason": "Yeu cau hanh dong khan cap.",
                "cue_type": "urgent_action",
            }
        ],
        "threat_labels": ["bank_impersonation"],
        "recommendations": ["Xac minh bang ung dung ngan hang chinh thuc."],
        "backend_name": "synthetic",
        "provisional": True,
        "normalized_text": "Canh bao dang nhap la, vui long kiem tra ngay.",
    }
    assert list(inspect.signature(service_module.RuntimeService).parameters) == [
        "backend",
        "settings",
    ]


def test_modeling_modules_are_phase_neutral_and_within_static_budgets() -> None:
    for relative in MODELING_FILES:
        source = (REPO_ROOT / relative).read_text(encoding="utf-8")
        tree = ast.parse(source)
        assert len(source.splitlines()) <= 600, relative
        assert "data/splits" not in source.replace("\\", "/")
        for node in ast.walk(tree):
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                assert not any(
                    f"phase{number}" in node.name.casefold() for number in (40, 41)
                ), node.name
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                assert node.end_lineno is not None
                assert node.end_lineno - node.lineno + 1 <= 100, (
                    relative,
                    node.name,
                )

    runtime_source = (REPO_ROOT / "src/runtime/service.py").read_text(encoding="utf-8")
    assert "from src.modeling.inference import InferenceService" in runtime_source
    assert "self._inference.infer(request)" in runtime_source
    assert "src.model_adaptation" not in runtime_source
