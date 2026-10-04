"""Guarded before-state snapshots for CLI and serialization compatibility."""

from __future__ import annotations

import argparse
import ast
from contextlib import redirect_stderr, redirect_stdout
from enum import Enum
import importlib.abc
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
from types import ModuleType
from typing import Any, Literal, get_args

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = Path(__file__).with_name("fixtures")
FIXTURE_PATHS = {
    "model": FIXTURE_ROOT / "model_cli_contract.json",
    "runtime": FIXTURE_ROOT / "runtime_cli_contract.json",
    "serialization": FIXTURE_ROOT / "serialization_contract.json",
}
EXPECTED_MODEL_COMMANDS = [
    "pilot",
    "train",
    "convert",
    "doctor",
    "phase40-preflight",
    "phase40-build-source-bundle",
    "phase40-build-input-bundle",
    "phase40-verify-input-bundle",
    "phase40-verify-run-request",
    "phase40-verify-run-evidence",
    "phase40-render-graphs",
    "phase40-validate-notebooks",
    "phase40-finalize-comparison",
    "phase40-freeze-scope-amendment",
    "phase40-verify-review-queue",
    "phase40-finalize-human-review",
    "phase41-prepare-evaluation",
    "phase41-verify-preauthorization",
    "phase41-authorize-evaluation",
    "phase41-run-once",
    "phase41-freeze-deployment-fit-disposition",
    "phase41-export-evidence",
    "phase41-verify-evidence",
]
EXPECTED_RUNTIME_COMMANDS = ["analyze", "doctor", "demo"]
OPTIONAL_IMPLEMENTATION_PREFIXES = (
    "torch",
    "transformers",
    "peft",
    "bitsandbytes",
    "sklearn",
    "numpy",
    "anthropic",
    "openai",
)


class _AdaptationMode(str, Enum):
    LORA = "lora"
    QLORA = "qlora"


class _RunKind(str, Enum):
    PROBE = "probe"
    FULL = "full"


class _ParserOnlyType:
    """Never-instantiated placeholder for parser-only eager imports."""


def _parser_only_call(*_args: object, **_kwargs: object) -> object:
    raise AssertionError("a synthetic parser stub was invoked")


MODEL_STUBS: dict[str, dict[str, object]] = {
    "src.config.settings": {"get_settings": _parser_only_call},
    "src.model_adaptation.catalog": {"build_default_catalog": _parser_only_call},
    "src.model_adaptation.convert": {
        "build_gguf_request": _parser_only_call,
        "convert_to_gguf": _parser_only_call,
    },
    "src.model_adaptation.doctor": {
        "format_training_doctor_report": _parser_only_call,
        "run_training_doctor": _parser_only_call,
    },
    "src.model_adaptation.pilot": {"run_pilot": _parser_only_call},
    "src.model_adaptation.phase40_contract": {
        "preflight_phase40_inputs": _parser_only_call,
    },
    "src.model_adaptation.phase40_handoff": {
        name: _ParserOnlyType
        for name in (
            "InputBundleReference LocalTwoModelOperatorReturn PackageDecision "
            "Phase40ComparisonManifest ReturnedBundleRoot ReturnedGpuIdentity "
            "ReviewQueueManifest ReviewQueueRow ReviewerReturnRow RunRequest "
            "build_phase40_input_bundle build_phase40_source_bundle "
            "finalize_phase40_comparison freeze_phase40_scope_amendment "
            "load_frozen_phase40_run_request load_frozen_phase40_scope_amendment "
            "load_phase40_selected_prediction_bundles transfer_authority_from_request "
            "verify_phase40_input_bundle verify_phase40_review_queue "
            "verify_phase40_run_request"
        ).split()
    },
    "src.model_adaptation.phase40_review": {
        "FIXED_REVIEW_QUEUE_PATH": Path("synthetic/review-queue.jsonl"),
        "FIXED_REVIEWER_RETURN_PATH": Path("synthetic/reviewer-return.jsonl"),
        "FIXED_SELECTED_PREDICTIONS_PATH": Path("synthetic/predictions.json"),
        "finalize_phase40_human_review": _parser_only_call,
        "load_canonical_phase40_comparison_manifest": _parser_only_call,
        "load_phase40_review_authority": _parser_only_call,
        "read_canonical_phase40_review_regular_bytes": _parser_only_call,
        "verify_phase40_final_review_comparison": _parser_only_call,
    },
    "src.model_adaptation.phase40_evidence": {
        "verify_phase40_bundle": _parser_only_call,
    },
    "src.model_adaptation.phase40_graphs": {
        "render_phase40_graphs": _parser_only_call,
    },
    "src.model_adaptation.phase40_modes": {
        "AdaptationMode": _AdaptationMode,
        "RunKind": _RunKind,
    },
    "src.model_adaptation.registry": {
        "load_model_registry": _parser_only_call,
        "save_model_registry": _parser_only_call,
    },
    "src.model_adaptation.schemas": {
        "ModelRegistry": _ParserOnlyType,
        "PilotSelection": _ParserOnlyType,
    },
    "src.model_adaptation.training": {
        "build_training_config": _parser_only_call,
        "run_training": _parser_only_call,
    },
}
RUNTIME_STUBS: dict[str, dict[str, object]] = {
    "src.runtime.contracts": {
        "ChannelName": Literal[
            "unknown", "sms", "zalo", "messenger", "telegram", "facebook"
        ],
    },
    "src.runtime.demo": {
        "run_demo_server": _parser_only_call,
        "require_loopback_host": _parser_only_call,
    },
    "src.runtime.doctor": {
        "format_doctor_report": _parser_only_call,
        "run_runtime_doctor": _parser_only_call,
    },
    "src.runtime.render": {
        "render_analysis_result": _parser_only_call,
        "render_runtime_error": _parser_only_call,
    },
    "src.runtime.service": {
        "RuntimeBoundaryError": type("RuntimeBoundaryError", (RuntimeError,), {}),
        "RuntimeUnavailableError": type("RuntimeUnavailableError", (RuntimeError,), {}),
        "build_default_runtime_service": _parser_only_call,
    },
}

MODEL_PARSER_SUPPORT = (
    "adaptation",
    "legacy_phase40",
    "legacy_phase41",
    "router",
)


class _ClosedImportFinder(importlib.abc.MetaPathFinder):
    """Reject any internal/optional import not already supplied by the stub table."""

    def find_spec(self, fullname: str, path=None, target=None):  # noqa: ANN001
        if fullname.startswith("src.") or fullname.split(".", 1)[0] in (
            OPTIONAL_IMPLEMENTATION_PREFIXES
        ):
            raise ImportError(f"closed Phase 41.1 capture rejected import: {fullname}")
        return None


def _install_package(name: str, path: Path, installed: list[str]) -> None:
    module = ModuleType(name)
    module.__path__ = [os.fspath(path)]  # type: ignore[attr-defined]
    module.__package__ = name
    module.__file__ = "<phase411-synthetic-package>"
    sys.modules[name] = module
    installed.append(name)


def _install_stub(name: str, symbols: dict[str, object], installed: list[str]) -> None:
    module = ModuleType(name)
    module.__package__ = name.rpartition(".")[0]
    module.__file__ = "<phase411-synthetic-stub>"
    for symbol_name, value in symbols.items():
        setattr(module, symbol_name, value)
    sys.modules[name] = module
    installed.append(name)


def _load_model_parser_support(installed: list[str]) -> None:
    """Load only dependency-light parser/route modules before closing imports."""

    package_name = "src.model_adaptation.commands"
    package_path = REPO_ROOT / "src" / "model_adaptation" / "commands"
    _install_package(package_name, package_path, installed)
    for leaf in MODEL_PARSER_SUPPORT:
        module_name = f"{package_name}.{leaf}"
        spec = importlib.util.spec_from_file_location(
            module_name, package_path / f"{leaf}.py"
        )
        if spec is None or spec.loader is None:
            raise AssertionError(f"unable to load parser support module {module_name}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        installed.append(module_name)
        spec.loader.exec_module(module)


def _load_cli(kind: str) -> tuple[ModuleType, list[str], dict[str, object]]:
    before = _implementation_modules_loaded()
    installed: list[str] = []
    _install_package("src", REPO_ROOT / "src", installed)
    package_name = f"src.{kind}"
    package_path = REPO_ROOT / "src" / kind
    _install_package(package_name, package_path, installed)
    stubs = MODEL_STUBS if kind == "model_adaptation" else RUNTIME_STUBS
    for name, symbols in stubs.items():
        parent = name.rpartition(".")[0]
        if parent not in sys.modules:
            _install_package(parent, REPO_ROOT / parent.replace(".", "/"), installed)
        _install_stub(name, symbols, installed)
    if kind == "model_adaptation":
        _load_model_parser_support(installed)
    module_name = f"{package_name}.cli"
    module_path = package_path / "cli.py"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"unable to load parser leaf: {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    installed.append(module_name)
    finder = _ClosedImportFinder()
    sys.meta_path.insert(0, finder)
    try:
        spec.loader.exec_module(module)
    finally:
        sys.meta_path.remove(finder)
    isolation = {
        "before_real_implementation_modules": before,
        "synthetic_stub_modules": sorted(stubs),
        "all_stubs_have_synthetic_file": all(
            str(getattr(sys.modules[name], "__file__", "")).startswith("<phase411-")
            for name in stubs
        ),
    }
    return module, installed, isolation


def _implementation_modules_loaded() -> list[str]:
    risky = (
        "src.model_adaptation.phase41_evaluation",
        "src.model_adaptation.training",
        "src.runtime.analyzers",
        *OPTIONAL_IMPLEMENTATION_PREFIXES,
    )
    return sorted(name for name in sys.modules if name.startswith(risky))


def _stable(value: object, temp_root: Path) -> object:
    if value is argparse.SUPPRESS:
        return "<argparse.SUPPRESS>"
    if isinstance(value, Path):
        text = os.fspath(value)
        root = os.fspath(temp_root)
        return text.replace(root, "<TMP_ROOT>")
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, type):
        return f"{value.__module__}.{value.__qualname__}"
    if callable(value):
        return f"{value.__module__}.{value.__qualname__}"
    if isinstance(value, dict):
        return {str(key): _stable(item, temp_root) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_stable(item, temp_root) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        if isinstance(value, str):
            return value.replace(os.fspath(temp_root), "<TMP_ROOT>")
        return value
    return f"<{type(value).__module__}.{type(value).__qualname__}>"


def _parser_graph(parser: argparse.ArgumentParser, temp_root: Path) -> dict[str, object]:
    actions: list[dict[str, object]] = []
    subcommands: list[dict[str, object]] = []
    for index, action in enumerate(parser._actions):
        action_row = {
            "index": index,
            "class": type(action).__name__,
            "option_strings": list(action.option_strings),
            "dest": action.dest,
            "default": _stable(action.default, temp_root),
            "required": action.required,
            "nargs": _stable(action.nargs, temp_root),
            "type": _stable(action.type, temp_root),
            "choices": (
                list(action.choices)
                if isinstance(action, argparse._SubParsersAction)
                else _stable(action.choices, temp_root)
            ),
            "help": _stable(action.help, temp_root),
            "metavar": _stable(action.metavar, temp_root),
            "const": _stable(action.const, temp_root),
        }
        actions.append(action_row)
        if isinstance(action, argparse._SubParsersAction):
            for command, child in action.choices.items():
                subcommands.append(
                    {"command": command, "parser": _parser_graph(child, temp_root)}
                )
    return {
        "prog": parser.prog,
        "usage": parser.usage,
        "description": parser.description,
        "epilog": parser.epilog,
        "prefix_chars": parser.prefix_chars,
        "allow_abbrev": parser.allow_abbrev,
        "conflict_handler": parser.conflict_handler,
        "formatter_class": _stable(parser.formatter_class, temp_root),
        "defaults": _stable(parser._defaults, temp_root),
        "actions": actions,
        "subcommands": subcommands,
    }


def _captured_call(call, *args: object) -> dict[str, object]:  # noqa: ANN001
    stdout = io.StringIO()
    stderr = io.StringIO()
    returned: object = None
    system_exit: int | str | None = None
    exception: dict[str, str] | None = None
    with redirect_stdout(stdout), redirect_stderr(stderr):
        try:
            returned = call(*args)
        except SystemExit as exc:
            system_exit = exc.code
        except Exception as exc:  # Contract capture intentionally records uncaught behavior.
            exception = {"type": type(exc).__name__, "message": str(exc)}
    out_text = stdout.getvalue()
    err_text = stderr.getvalue()
    return {
        "return_value": returned,
        "system_exit_code": system_exit,
        "exception": exception,
        "stdout": out_text,
        "stderr": err_text,
        "stdout_utf8_hex": out_text.encode("utf-8").hex(),
        "stderr_utf8_hex": err_text.encode("utf-8").hex(),
    }


def _parse_cases(kind: str, parser: argparse.ArgumentParser) -> list[dict[str, object]]:
    subparser_action = next(
        action
        for action in parser._actions
        if isinstance(action, argparse._SubParsersAction)
    )
    cases: list[tuple[str, list[str]]] = [("root_help", ["--help"])]
    cases.extend(
        (f"{name}_help", [name, "--help"]) for name in subparser_action.choices
    )
    cases.extend(
        [("missing_command", []), ("unknown_command", ["not-a-command"])]
    )
    if kind == "model":
        train = [
            "train",
            "--candidate",
            "baseline-winner",
            "--version-tag",
            "snapshot",
            "--train-split",
            "synthetic-train.jsonl",
            "--val-split",
            "synthetic-val.jsonl",
            "--adaptation-mode",
            "lora",
        ]
        cases.extend(
            [
                ("missing_required_option", ["pilot"]),
                (
                    "invalid_choice",
                    ["pilot", "--version-tag", "snapshot", "--evaluated-split", "bad"],
                ),
                ("invalid_type", [*train, "--max-steps", "not-an-integer"]),
                (
                    "parser_error",
                    ["pilot", "--version-tag", "snapshot", "--unknown-option"],
                ),
            ]
        )
    else:
        cases.extend(
            [
                ("invalid_choice", ["analyze", "--channel", "carrier-pigeon"]),
                ("invalid_type", ["demo", "--port", "not-an-integer"]),
                ("parser_error", ["doctor", "--unknown-option"]),
            ]
        )
    return [
        {"name": name, "argv": argv, **_captured_call(parser.parse_args, argv)}
        for name, argv in cases
    ]


class _StrictEventStream:
    encoding = "cp1252"

    def __init__(self, channel: str, events: list[dict[str, str]]) -> None:
        self.channel = channel
        self.events = events
        self.text = ""

    def write(self, value: str) -> int:
        value.encode(self.encoding, errors="strict")
        self.text += value
        self.events.append({"channel": self.channel, "text": value})
        return len(value)

    def flush(self) -> None:
        return None


def _invoke_with_streams(call) -> tuple[dict[str, object], list[dict[str, str]]]:  # noqa: ANN001
    events: list[dict[str, str]] = []
    stdout = _StrictEventStream("stdout", events)
    stderr = _StrictEventStream("stderr", events)
    returned: object = None
    system_exit: int | str | None = None
    exception: dict[str, str] | None = None
    with redirect_stdout(stdout), redirect_stderr(stderr):
        try:
            returned = call()
        except SystemExit as exc:
            system_exit = exc.code
        except Exception as exc:  # Contract capture intentionally records uncaught behavior.
            exception = {"type": type(exc).__name__, "message": str(exc)}
    captured = {
        "return_value": returned,
        "system_exit_code": system_exit,
        "exception": exception,
        "stdout": stdout.text,
        "stderr": stderr.text,
        "stdout_utf8_hex": stdout.text.encode("utf-8").hex(),
        "stderr_utf8_hex": stderr.text.encode("utf-8").hex(),
    }
    return captured, events


def _model_main_contract(module: ModuleType, temp_root: Path) -> dict[str, object]:
    argv = ["pilot", "--version-tag", "snapshot", "--dry-run"]
    invocations: list[dict[str, object]] = []

    def success_handler(namespace: argparse.Namespace) -> int:
        invocations.append(_stable(vars(namespace), temp_root))  # type: ignore[arg-type]
        print("model stdout one")
        print("model stderr one", file=sys.stderr)
        print("model stdout two")
        return 7

    module.handle_pilot = success_handler
    success, events = _invoke_with_streams(lambda: module.main(argv))
    caught: list[dict[str, object]] = []
    for exception_type in (RuntimeError, ValueError, FileNotFoundError):
        def fail_handler(_namespace, selected=exception_type):  # noqa: ANN001
            raise selected("lỗi tiếng Việt")

        module.handle_pilot = fail_handler
        result, _ = _invoke_with_streams(lambda: module.main(argv))
        caught.append({"caught_exception": exception_type.__name__, **result})

    def uncaught_handler(_namespace):  # noqa: ANN001
        raise KeyError("uncaught-marker")

    module.handle_pilot = uncaught_handler
    uncaught, _ = _invoke_with_streams(lambda: module.main(argv))
    return {
        "successful_handler": {**success, "events": events, "invocations": invocations},
        "caught_exceptions": caught,
        "uncaught_exception": uncaught,
    }


def _runtime_main_contract(module: ModuleType, temp_root: Path) -> dict[str, object]:
    cases = [
        ("analyze", ["analyze", "--text", "xin chào", "--channel", "zalo"], 0),
        ("doctor", ["doctor"], 1),
        (
            "demo",
            ["demo", "--host", "127.0.0.9", "--port", "9001", "--no-browser"],
            2,
        ),
    ]
    results: list[dict[str, object]] = []
    for handler_name, argv, return_code in cases:
        invocations: list[dict[str, object]] = []

        def handler(namespace: argparse.Namespace, code=return_code) -> int:
            invocations.append(_stable(vars(namespace), temp_root))  # type: ignore[arg-type]
            print(f"{handler_name} stdout")
            print(f"{handler_name} stderr", file=sys.stderr)
            return code

        setattr(module, f"handle_{handler_name}", handler)
        captured, events = _invoke_with_streams(lambda: module.main(argv))
        results.append(
            {
                "command": handler_name,
                "argv": argv,
                **captured,
                "events": events,
                "invocations": invocations,
            }
        )
    return {"installed_command_handler_doubles": results}


def _capture_cli(kind: str, temp_root: Path) -> dict[str, object]:
    package_kind = "model_adaptation" if kind == "model" else "runtime"
    module, installed, isolation = _load_cli(package_kind)
    try:
        parser = module.build_parser()
        graph = _parser_graph(parser, temp_root)
        parse_cases = _parse_cases(kind, parser)
        main_contract = (
            _model_main_contract(module, temp_root)
            if kind == "model"
            else _runtime_main_contract(module, temp_root)
        )
    finally:
        for name in reversed(installed):
            sys.modules.pop(name, None)
    isolation["after_real_implementation_modules"] = _implementation_modules_loaded()
    return {
        "schema_version": f"phase411-{kind}-cli-contract-v1",
        "environment_roots": {
            name: _stable(os.environ[name], temp_root)
            for name in ("DATA_DIR", "MODEL_ARTIFACT_ROOT", "MODEL_REGISTRY_PATH")
        },
        "isolation": isolation,
        "parser": graph,
        "parse_cases": parse_cases,
        "main_contract": main_contract,
    }


def _load_contract_modules() -> tuple[ModuleType, ModuleType, ModuleType, list[str]]:
    installed: list[str] = []
    _install_package("src", REPO_ROOT / "src", installed)
    modules: list[ModuleType] = []
    for package, leaf in (
        ("runtime", "contracts"),
        ("data_pipeline", "schemas"),
        ("model_adaptation", "schemas"),
    ):
        package_name = f"src.{package}"
        _install_package(package_name, REPO_ROOT / "src" / package, installed)
        module_name = f"{package_name}.{leaf}"
        spec = importlib.util.spec_from_file_location(
            module_name, REPO_ROOT / "src" / package / f"{leaf}.py"
        )
        if spec is None or spec.loader is None:
            raise AssertionError(f"unable to load contract module {module_name}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        installed.append(module_name)
        spec.loader.exec_module(module)
        modules.append(module)
    return modules[0], modules[1], modules[2], installed


def _phase41_literal_contract() -> dict[str, object]:
    source = (REPO_ROOT / "src/model_adaptation/phase41_evaluation.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(source)
    names: dict[str, str] = {}
    schema_versions: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if (
                isinstance(target, ast.Name)
                and target.id.endswith("_NAME")
                and isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, str)
            ):
                names[target.id] = node.value.value
        if isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values):
                if (
                    isinstance(key, ast.Constant)
                    and key.value == "schema_version"
                    and isinstance(value, ast.Constant)
                    and isinstance(value.value, str)
                ):
                    schema_versions.append(value.value)
    return {
        "artifact_names": names,
        "schema_versions": sorted(set(schema_versions)),
    }


def _capture_serialization(temp_root: Path) -> dict[str, object]:
    runtime, data, adaptation, installed = _load_contract_modules()
    try:
        analysis = runtime.AnalysisResult(
            risk_tier="high-risk",
            summary="Cảnh báo chuyển khoản khẩn cấp",
            top_cues=[runtime.SuspiciousCue(span="chuyển ngay", reason="Gây áp lực")],
            threat_labels=["bank_impersonation", "task_scam"],
            recommendations=["Không bấm liên kết lạ"],
            backend_name="bộ phân tích cục bộ",
            normalized_text="Tin nhắn tiếng Việt đã chuẩn hóa",
        )
        dataset = data.DatasetRecord(
            text="Ngân hàng yêu cầu chuyển khoản ngay hôm nay",
            label="bank_impersonation",
            risk_tier="high-risk",
            suspicious_spans=["chuyển khoản ngay"],
            xai_explanation="Yêu cầu khẩn cấp và giả danh ngân hàng là dấu hiệu đáng ngờ.",
            source="synthetic_claude",
            seed_id="synthetic-seed-001",
        )
        support = {label: 1 for label in adaptation.LOCKED_RELEASE_LABELS}
        audit = adaptation.HeldOutSupportAudit(
            evaluated_split_path=temp_root / "synthetic-heldout.jsonl",
            support_by_label=support,
        )
        metrics = [
            adaptation.PerLabelMetricRow(
                label=label, precision=0.9, recall=0.9, f1=0.9, support=1
            )
            for label in adaptation.LOCKED_RELEASE_LABELS
        ]
        artifact = adaptation.ReleaseEvaluationArtifact(
            run_id="synthetic-release",
            verdict="PASS",
            overall_metrics=adaptation.OverallMetricSummary(
                macro_f1=0.9, weighted_f1=0.9, evaluated_rows=4
            ),
            per_label_metrics=metrics,
            explanation_rubric_summary=adaptation.ExplanationRubricSummary(
                evaluated_risky_predictions=3, manual_reviewed_predictions=3
            ),
            readiness_audit=audit,
        )

        def bytes_contract(model) -> dict[str, object]:  # noqa: ANN001
            root_text = os.fspath(temp_root)
            escaped_root = root_text.replace("\\", "\\\\")

            def normalize_root(text: str) -> str:
                return text.replace(escaped_root, "<TMP_ROOT>").replace(
                    root_text, "<TMP_ROOT>"
                )

            compact = normalize_root(model.model_dump_json()).encode("utf-8")
            indented = normalize_root(model.model_dump_json(indent=2)).encode("utf-8")
            canonical_text = (
                json.dumps(
                    model.model_dump(mode="json"),
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
                + "\n"
            )
            canonical = normalize_root(canonical_text).encode("utf-8")
            return {
                "field_order": list(type(model).model_fields),
                "compact_utf8": compact.decode("utf-8"),
                "compact_utf8_hex": compact.hex(),
                "compact_has_final_newline": compact.endswith(b"\n"),
                "indented_utf8": indented.decode("utf-8"),
                "indented_has_final_newline": indented.endswith(b"\n"),
                "canonical_lf_utf8_hex": canonical.hex(),
                "canonical_has_one_final_newline": canonical.endswith(b"\n")
                and not canonical.endswith(b"\n\n"),
            }

        return {
            "schema_version": "phase411-serialization-contract-v1",
            "enums": {
                "channel": list(get_args(runtime.ChannelName)),
                "risk_tier": list(get_args(runtime.RiskTier)),
                "threat_label": list(get_args(runtime.ThreatLabel)),
                "release_verdict": list(get_args(adaptation.ReleaseVerdict)),
            },
            "release_constants": {
                "locked_labels": list(adaptation.LOCKED_RELEASE_LABELS),
                "risky_labels": list(adaptation.LOCKED_RISKY_LABELS),
                "uniform_risky_recall_floor": adaptation.UNIFORM_RISKY_RECALL_FLOOR,
                "per_label_recall_floors": adaptation.RISKY_LABEL_RECALL_FLOORS,
            },
            "analysis_result": bytes_contract(analysis),
            "dataset_record": bytes_contract(dataset),
            "release_evaluation_artifact": bytes_contract(artifact),
            "phase41_literals": _phase41_literal_contract(),
            "newline_policy": {
                "pydantic_model_dump_json": "no trailing newline",
                "canonical_json_artifact": "exactly one LF trailing newline",
            },
        }
    finally:
        for name in reversed(installed):
            sys.modules.pop(name, None)


def _fixture_bytes(kind: str, temp_root: Path) -> bytes:
    payload = (
        _capture_serialization(temp_root)
        if kind == "serialization"
        else _capture_cli(kind, temp_root)
    )
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _run_fresh_capture(kind: str, temp_root: Path) -> bytes:
    temp_root = Path(os.path.abspath(temp_root))
    temp_root.mkdir(parents=True, exist_ok=False)
    bootstrap = REPO_ROOT / "tests/architecture/bootstrap"
    env = dict(os.environ)
    env.update(
        {
            "PYTHONPATH": os.fspath(bootstrap),
            "PHASE411_DENY_OPEN_SENTINEL": "1",
            "PHASE411_REQUIRE_HISTORICAL_ARCHIVE": "0",
            "DATA_DIR": os.fspath(temp_root / "data"),
            "MODEL_ARTIFACT_ROOT": os.fspath(temp_root / "models"),
            "MODEL_REGISTRY_PATH": os.fspath(temp_root / "registry.json"),
            "COLUMNS": "120",
            "LINES": "40",
        }
    )
    completed = subprocess.run(
        [
            sys.executable,
            os.fspath(Path(__file__).resolve()),
            "--capture",
            kind,
            "--temp-root",
            os.fspath(temp_root),
        ],
        cwd=temp_root,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(
            f"fresh {kind} capture failed ({completed.returncode}): "
            f"{completed.stderr.decode('utf-8', errors='replace')}"
        )
    return completed.stdout


@pytest.mark.parametrize("kind", ("model", "runtime", "serialization"))
def test_contract_fixture_is_fresh_deterministic_and_current(
    kind: str, tmp_path: Path
) -> None:
    first = _run_fresh_capture(kind, tmp_path / f"{kind}-a")
    second = _run_fresh_capture(kind, tmp_path / f"{kind}-b")
    assert first == second
    assert first.endswith(b"\n") and not first.endswith(b"\n\n")
    assert FIXTURE_PATHS[kind].read_bytes() == first


def test_model_fixture_freezes_complete_parser_and_main_contract() -> None:
    fixture = json.loads(FIXTURE_PATHS["model"].read_text(encoding="utf-8"))
    commands = [row["command"] for row in fixture["parser"]["subcommands"]]
    assert commands == EXPECTED_MODEL_COMMANDS
    assert fixture["parser"]["allow_abbrev"] is False
    assert fixture["parser"]["actions"][1]["required"] is True
    doctor = next(
        row["parser"]
        for row in fixture["parser"]["subcommands"]
        if row["command"] == "doctor"
    )
    adaptation_mode = next(
        action for action in doctor["actions"] if action["dest"] == "adaptation_mode"
    )
    assert adaptation_mode["required"] is True
    assert adaptation_mode["choices"] == ["lora", "qlora"]
    case_names = {case["name"] for case in fixture["parse_cases"]}
    assert {
        "root_help",
        "missing_command",
        "unknown_command",
        "missing_required_option",
        "invalid_choice",
        "invalid_type",
        "parser_error",
    } <= case_names
    main = fixture["main_contract"]
    assert main["successful_handler"]["return_value"] == 7
    assert [row["caught_exception"] for row in main["caught_exceptions"]] == [
        "RuntimeError",
        "ValueError",
        "FileNotFoundError",
    ]
    assert {row["return_value"] for row in main["caught_exceptions"]} == {1}
    assert all("\\u1ed7i" in row["stderr"] for row in main["caught_exceptions"])
    assert [event["channel"] for event in main["successful_handler"]["events"]] == [
        "stdout",
        "stdout",
        "stderr",
        "stderr",
        "stdout",
        "stdout",
    ]
    assert main["uncaught_exception"]["exception"]["type"] == "KeyError"


def test_runtime_fixture_freezes_three_installed_commands() -> None:
    fixture = json.loads(FIXTURE_PATHS["runtime"].read_text(encoding="utf-8"))
    commands = [row["command"] for row in fixture["parser"]["subcommands"]]
    assert commands == EXPECTED_RUNTIME_COMMANDS
    handler_cases = fixture["main_contract"]["installed_command_handler_doubles"]
    assert [row["command"] for row in handler_cases] == EXPECTED_RUNTIME_COMMANDS
    assert [row["return_value"] for row in handler_cases] == [0, 1, 2]
    assert all(row["invocations"] for row in handler_cases)


def test_cli_fixtures_prove_real_implementations_stayed_unloaded() -> None:
    for kind in ("model", "runtime"):
        fixture = json.loads(FIXTURE_PATHS[kind].read_text(encoding="utf-8"))
        isolation = fixture["isolation"]
        assert isolation["before_real_implementation_modules"] == []
        assert isolation["after_real_implementation_modules"] == []
        assert isolation["all_stubs_have_synthetic_file"] is True


def test_serialization_fixture_freezes_unicode_enums_keys_and_newlines() -> None:
    fixture = json.loads(
        FIXTURE_PATHS["serialization"].read_text(encoding="utf-8")
    )
    assert fixture["enums"]["risk_tier"] == ["benign", "suspicious", "high-risk"]
    assert fixture["enums"]["threat_label"] == [
        "bank_impersonation",
        "zalo_social_engineering",
        "task_scam",
        "benign",
    ]
    assert "Cảnh báo" in fixture["analysis_result"]["compact_utf8"]
    assert fixture["dataset_record"]["field_order"] == [
        "text",
        "label",
        "risk_tier",
        "suspicious_spans",
        "xai_explanation",
        "source",
        "seed_id",
    ]
    for key in ("analysis_result", "dataset_record", "release_evaluation_artifact"):
        assert fixture[key]["compact_has_final_newline"] is False
        assert fixture[key]["canonical_has_one_final_newline"] is True
    assert fixture["phase41_literals"]["artifact_names"]["RESULTS_NAME"] == (
        "results.json"
    )
    assert "phase41-evidence-manifest-v1" in fixture["phase41_literals"][
        "schema_versions"
    ]


def _main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--capture", choices=tuple(FIXTURE_PATHS))
    mode.add_argument("--write-fixtures", action="store_true")
    parser.add_argument("--temp-root", type=Path)
    args = parser.parse_args()
    if args.temp_root is None:
        parser.error("--temp-root is required")
    if args.write_fixtures:
        args.temp_root.mkdir(parents=True, exist_ok=False)
        for kind, fixture_path in FIXTURE_PATHS.items():
            fixture_path.write_bytes(
                _run_fresh_capture(kind, args.temp_root / f"capture-{kind}")
            )
    else:
        sys.stdout.buffer.write(_fixture_bytes(args.capture, args.temp_root))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
