"""Guarded compatibility contract for the lazy model-adaptation CLI shell."""

from __future__ import annotations

import argparse
import ast
from contextlib import redirect_stderr, redirect_stdout
from enum import Enum
import importlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_PATH = Path(__file__).with_name("fixtures") / "model_cli_contract.json"
BOOTSTRAP_ROOT = Path(__file__).with_name("bootstrap")
ROUTER_PATH = REPO_ROOT / "src/model_adaptation/commands/router.py"
FACADE_PATH = REPO_ROOT / "src/model_adaptation/cli.py"
COMMAND_MODULE_PATHS = (
    REPO_ROOT / "src/model_adaptation/commands/adaptation.py",
    REPO_ROOT / "src/model_adaptation/commands/legacy_phase40.py",
    REPO_ROOT / "src/model_adaptation/commands/legacy_phase41.py",
    ROUTER_PATH,
)
EXPECTED_COMMANDS = (
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
)
PHASE40_ROUTES = {
    command: ("src.model_adaptation.commands.legacy_phase40", f"handle_{command.replace('-', '_')}")
    for command in EXPECTED_COMMANDS
    if command.startswith("phase40-")
}
PHASE41_ROUTES = {
    command: ("src.model_adaptation.commands.legacy_phase41", f"handle_{command.replace('-', '_')}")
    for command in EXPECTED_COMMANDS
    if command.startswith("phase41-")
}
OPTIONAL_OR_IMPLEMENTATION_PREFIXES = (
    "numpy",
    "sklearn",
    "torch",
    "transformers",
    "peft",
    "bitsandbytes",
    "anthropic",
    "openai",
    "src.model_adaptation.convert",
    "src.model_adaptation.doctor",
    "src.model_adaptation.training",
    "src.model_adaptation.phase40_",
    "src.model_adaptation.phase41_",
)


def _stable(value: object, temp_root: Path) -> object:
    if value is argparse.SUPPRESS:
        return "<argparse.SUPPRESS>"
    if isinstance(value, Path):
        return os.fspath(value).replace(os.fspath(temp_root), "<TMP_ROOT>")
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
        actions.append(
            {
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
        )
        if isinstance(action, argparse._SubParsersAction):
            subcommands.extend(
                {"command": name, "parser": _parser_graph(child, temp_root)}
                for name, child in action.choices.items()
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
        except Exception as exc:  # The frozen contract includes uncaught behavior.
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


def _parse_cases(parser: argparse.ArgumentParser) -> list[dict[str, object]]:
    subparsers = next(
        action
        for action in parser._actions
        if isinstance(action, argparse._SubParsersAction)
    )
    cases: list[tuple[str, list[str]]] = [("root_help", ["--help"])]
    cases.extend((f"{name}_help", [name, "--help"]) for name in subparsers.choices)
    cases.extend((("missing_command", []), ("unknown_command", ["not-a-command"])))
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
        (
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
        )
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
        except Exception as exc:
            exception = {"type": type(exc).__name__, "message": str(exc)}
    return (
        {
            "return_value": returned,
            "system_exit_code": system_exit,
            "exception": exception,
            "stdout": stdout.text,
            "stderr": stderr.text,
            "stdout_utf8_hex": stdout.text.encode("utf-8").hex(),
            "stderr_utf8_hex": stderr.text.encode("utf-8").hex(),
        },
        events,
    )


def _model_main_contract(module, temp_root: Path) -> dict[str, object]:  # noqa: ANN001
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


def test_default_pilot_registry_persists_below_trusted_absolute_root(
    tmp_path: Path,
    monkeypatch,
) -> None:
    artifacts = importlib.import_module("src.artifacts")
    commands = importlib.import_module("src.model_adaptation.commands.adaptation")
    storage_root = tmp_path / "model-storage"
    registry_path = storage_root / "manifests" / "model-registry.json"
    storage_root.mkdir()
    settings = argparse.Namespace(
        resolved_model_storage_root=storage_root,
        resolved_model_registry_path=registry_path,
    )
    monkeypatch.setattr(commands, "get_settings", lambda: settings)
    args = argparse.Namespace(
        dry_run=True,
        version_tag="synthetic-pilot",
        evaluated_split="pilot",
        registry_path=None,
    )

    assert commands.handle_pilot(args) == 0
    registry = artifacts.load_model_registry(
        registry_path,
        storage_root=storage_root,
    )
    assert registry.version_tag == "synthetic-pilot"
    assert registry.selection is not None


def _loaded_forbidden_modules() -> list[str]:
    return sorted(
        name
        for name in sys.modules
        if name.startswith(OPTIONAL_OR_IMPLEMENTATION_PREFIXES)
    )


def _capture(temp_root: Path) -> dict[str, object]:
    before = _loaded_forbidden_modules()
    module = importlib.import_module("src.model_adaptation.cli")
    parser = module.build_parser()
    parse_cases = _parse_cases(parser)
    main_contract = _model_main_contract(module, temp_root)
    return {
        "before": before,
        "after": _loaded_forbidden_modules(),
        "parser": _parser_graph(parser, temp_root),
        "parse_cases": parse_cases,
        "main_contract": main_contract,
    }


def _fresh_capture(tmp_path: Path) -> dict[str, object]:
    capture_root = tmp_path / "capture"
    capture_root.mkdir()
    env = dict(os.environ)
    env.update(
        {
            "PHASE411_DENY_OPEN_SENTINEL": "1",
            "PHASE411_REQUIRE_HISTORICAL_ARCHIVE": "1",
            "DATA_DIR": os.fspath(capture_root / "data"),
            "MODEL_ARTIFACT_ROOT": os.fspath(capture_root / "models"),
            "MODEL_REGISTRY_PATH": os.fspath(capture_root / "registry.json"),
            "COLUMNS": "120",
            "LINES": "40",
        }
    )
    env["PYTHONPATH"] = os.pathsep.join((os.fspath(BOOTSTRAP_ROOT), os.fspath(REPO_ROOT)))
    completed = subprocess.run(
        [sys.executable, os.fspath(Path(__file__).resolve()), "--capture", os.fspath(capture_root)],
        cwd=capture_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


def _literal_route_rows() -> dict[str, tuple[str, str]]:
    tree = ast.parse(ROUTER_PATH.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == "_ROUTE_ROWS" for target in node.targets):
            continue
        rows: dict[str, tuple[str, str]] = {}
        assert isinstance(node.value, (ast.Tuple, ast.List))
        for item in node.value.elts:
            assert isinstance(item, ast.Tuple) and len(item.elts) == 3
            values = tuple(
                element.value
                for element in item.elts
                if isinstance(element, ast.Constant) and isinstance(element.value, str)
            )
            assert len(values) == 3
            rows[values[0]] = (values[1], values[2])
        return rows
    raise AssertionError("router must define a literal _ROUTE_ROWS table")


def test_adaptation_family_matches_frozen_contract(tmp_path: Path) -> None:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    capture = _fresh_capture(tmp_path)
    assert capture["before"] == []
    assert capture["after"] == []
    assert capture["parser"] == fixture["parser"]
    assert capture["parse_cases"] == fixture["parse_cases"]
    assert capture["main_contract"] == fixture["main_contract"]


def test_router_is_closed_and_adaptation_routes_are_lazy() -> None:
    rows = _literal_route_rows()
    assert tuple(rows) == EXPECTED_COMMANDS
    assert rows["pilot"] == ("src.model_adaptation.commands.adaptation", "handle_pilot")
    assert rows["train"] == ("src.model_adaptation.commands.adaptation", "handle_train")
    assert rows["convert"] == ("src.model_adaptation.commands.adaptation", "handle_convert")
    assert rows["doctor"] == ("src.model_adaptation.commands.adaptation", "handle_doctor")
    source = ROUTER_PATH.read_text(encoding="utf-8")
    assert "MappingProxyType" in source
    assert "import_module(route.module)" in source
    assert "import_module(command" not in source


def test_phase40_routes_are_closed_and_lazy() -> None:
    rows = _literal_route_rows()
    assert {command: rows[command] for command in PHASE40_ROUTES} == PHASE40_ROUTES
    facade_source = (REPO_ROOT / "src/model_adaptation/cli.py").read_text(encoding="utf-8")
    for command, (_, symbol) in PHASE40_ROUTES.items():
        assert f'dispatch("{command}", args)' in facade_source
        assert f"def {symbol}(" in facade_source


def test_phase41_routes_are_closed_and_lazy() -> None:
    rows = _literal_route_rows()
    assert {command: rows[command] for command in PHASE41_ROUTES} == PHASE41_ROUTES
    facade_source = FACADE_PATH.read_text(encoding="utf-8")
    for command, (_, symbol) in PHASE41_ROUTES.items():
        assert f'dispatch("{command}", args)' in facade_source
        assert f"def {symbol}(" in facade_source
    run_once = next(
        node
        for node in ast.parse(facade_source).body
        if isinstance(node, ast.FunctionDef) and node.name == "handle_phase41_run_once"
    )
    run_once_source = ast.get_source_segment(facade_source, run_once)
    assert run_once_source is not None
    assert "run_phase41_once(_phase41_output_root(args.output_root))" in run_once_source


def test_facade_and_command_modules_fit_static_budgets() -> None:
    assert len(FACADE_PATH.read_text(encoding="utf-8").splitlines()) <= 250
    for path in COMMAND_MODULE_PATHS:
        source = path.read_text(encoding="utf-8")
        assert len(source.splitlines()) <= 600, path
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                assert node.end_lineno is not None
                assert node.end_lineno - node.lineno + 1 <= 100, (path, node.name)


if __name__ == "__main__" and len(sys.argv) == 3 and sys.argv[1] == "--capture":
    payload = _capture(Path(sys.argv[2]))
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
