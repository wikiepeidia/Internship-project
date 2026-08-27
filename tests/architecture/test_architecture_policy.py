"""Final static architecture policy for the Phase 41.1 boundary."""

from __future__ import annotations

import ast
import importlib
import json
from pathlib import Path
import re
import tomllib
from typing import Any, Mapping

from tests.architecture.test_data_core_contract import PUBLIC_RECORD_SYMBOLS
from tests.architecture.test_data_migration_shims import EXPECTED_MIGRATIONS
from tests.architecture.test_import_boundaries import (
    _data_module_classes,
    _import_edges,
    _module_paths,
    _path_to_target,
    _strong_components,
    _string_set,
)
from tests.architecture.test_model_cli_contract import (
    EXPECTED_COMMANDS,
    FIXTURE_PATH as MODEL_CLI_FIXTURE,
)


REPO_ROOT = Path(__file__).parents[2]
POLICY_PATH = REPO_ROOT / "architecture/module-boundaries.json"
RUNTIME_CLI_FIXTURE = REPO_ROOT / "tests/architecture/fixtures/runtime_cli_contract.json"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
EXCEPTION_FIELDS = {
    "path",
    "symbol",
    "measured_lines",
    "reason",
    "compatibility_evidence",
}
EXPECTED_BUDGETED_MODULES = {
    "src.artifacts",
    "src.core",
    "src.core.integrity",
    "src.data_pipeline.core",
    "src.data_pipeline.core.records",
    "src.data_pipeline.core.splits",
    "src.data_pipeline.core.text",
    "src.data_pipeline.generation_runs",
    "src.data_pipeline.migrations",
    "src.data_pipeline.publication",
    "src.data_pipeline.recovery",
    "src.data_pipeline.workflows",
    "src.model_adaptation.commands",
    "src.model_adaptation.commands.adaptation",
    "src.model_adaptation.commands.legacy_phase40",
    "src.model_adaptation.commands.legacy_phase41",
    "src.model_adaptation.commands.router",
    "src.model_adaptation.legacy.phase40",
    "src.model_adaptation.legacy.phase41",
    "src.modeling",
    "src.modeling.evaluation",
    "src.modeling.evidence",
    "src.modeling.inference",
    "src.modeling.legacy_adapters",
    "src.modeling.training",
}
EXPECTED_CLI_OWNERS = {
    "src.data_pipeline.cli": "data_modules.workflows",
    "src.model_adaptation.cli": "compatibility_adapters",
    "src.runtime.cli": "active_modules",
}
SAFE_COMPATIBILITY_CALLABLES = {
    "src.data_pipeline.processing.normalizer": ("normalize_text",),
    "src.data_pipeline.processing.splitter": (
        "assign_seed_split",
        "split_dataset",
    ),
    "src.data_pipeline.versioning.manifest": (
        "build_manifest",
        "save_manifest",
        "verify_manifest",
    ),
    "src.data_pipeline.migrations": (
        "get_migration",
        "load_migration_entrypoint",
    ),
}


def _policy() -> dict[str, Any]:
    payload = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    assert payload["schema_version"] == "module-boundaries-v2"
    return payload


def _policy_bucket(policy: Mapping[str, Any], owner: str) -> set[str]:
    root, _, nested = owner.partition(".")
    values = policy[root] if not nested else policy[root][nested]
    assert isinstance(values, list)
    return set(values)


def _source_path(module: str, modules: Mapping[str, Path]) -> Path:
    assert module in modules, f"classified module does not exist: {module}"
    return modules[module]


def _exception_map(
    exceptions: object,
) -> dict[tuple[str, str, int], Mapping[str, object]]:
    assert isinstance(exceptions, list)
    result: dict[tuple[str, str, int], Mapping[str, object]] = {}
    for item in exceptions:
        assert isinstance(item, dict)
        assert set(item) == EXCEPTION_FIELDS
        assert isinstance(item["path"], str) and item["path"]
        assert isinstance(item["symbol"], str) and item["symbol"]
        assert isinstance(item["measured_lines"], int) and item["measured_lines"] > 0
        assert isinstance(item["reason"], str) and item["reason"].strip()
        evidence = item["compatibility_evidence"]
        assert isinstance(evidence, str) and evidence.strip()
        key = (item["path"], item["symbol"], item["measured_lines"])
        assert key not in result
        result[key] = item
    return result


def _assert_with_exception(
    *,
    path: Path,
    symbol: str,
    measured: int,
    limit: int,
    exceptions: Mapping[tuple[str, str, int], Mapping[str, object]],
) -> None:
    if measured <= limit:
        return
    relative = path.relative_to(REPO_ROOT).as_posix()
    key = (relative, symbol, measured)
    assert key in exceptions, (
        f"{relative}:{symbol} is {measured} lines (limit {limit}) without "
        "an exact compatibility exception"
    )


def _fixture_commands(path: Path) -> tuple[str, ...]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return tuple(row["command"] for row in payload["parser"]["subcommands"])


def test_closed_classification_and_cli_owners_have_no_auto_admission() -> None:
    policy = _policy()
    modules = _module_paths()
    active = _string_set(policy, "active_modules")
    adapters = _string_set(policy, "compatibility_adapters")
    historical = _string_set(policy, "historical_modules")
    data_classes = _data_module_classes(policy)
    data_modules = set().union(*data_classes.values())
    ownership_indexes = set(policy["ownership_indexes"].values())
    groups = (active, adapters, historical, data_modules, ownership_indexes)
    for index, group in enumerate(groups):
        for other in groups[index + 1 :]:
            assert not group & other

    relevant = {
        module
        for module in modules
        if module == "src.artifacts"
        or module.startswith(
            (
                "src.artifacts.",
                "src.core",
                "src.data_pipeline",
                "src.model_adaptation",
                "src.modeling",
                "src.runtime",
            )
        )
    }
    assert set().union(*groups) == relevant

    static_policy = policy["static_policy"]
    assert static_policy["cli_owners"] == EXPECTED_CLI_OWNERS
    for module, owner in EXPECTED_CLI_OWNERS.items():
        assert module in modules
        assert module in _policy_bucket(policy, owner)
        assert sum(module in group for group in groups) == 1


def test_active_graph_is_acyclic_and_runtime_cannot_reach_training_or_providers() -> None:
    policy = _policy()
    modules = _module_paths()
    edges = _import_edges(modules)
    active = _string_set(policy, "active_modules")
    historical = _string_set(policy, "historical_modules")
    expected_sccs = {
        tuple(sorted(component)) for component in policy["historical_sccs"]
    }
    assert _strong_components(active, edges) == set()
    assert _strong_components(set(modules), edges) == expected_sccs
    assert all(set(component) <= historical for component in expected_sccs)

    forbidden_prefixes = tuple(policy["static_policy"]["runtime_forbidden_targets"])
    forbidden_targets = {
        module
        for module in modules
        if any(
            module == prefix or module.startswith(prefix + ".")
            for prefix in forbidden_prefixes
        )
    }
    runtime_modules = {
        module
        for module in modules
        if module == "src.runtime" or module.startswith("src.runtime.")
    }
    for source in sorted(runtime_modules):
        path = _path_to_target(source, edges, forbidden_targets)
        assert path is None, " -> ".join(path or ())


def test_new_modules_and_functions_fit_exact_static_budgets() -> None:
    policy = _policy()
    modules = _module_paths()
    static_policy = policy["static_policy"]
    limits = static_policy["line_limits"]
    assert limits == {
        "model_cli": 250,
        "new_module": 600,
        "new_function": 100,
    }
    budgeted = set(static_policy["budgeted_modules"])
    assert budgeted == EXPECTED_BUDGETED_MODULES
    exceptions = _exception_map(static_policy["budget_exceptions"])

    facade = _source_path("src.model_adaptation.cli", modules)
    facade_lines = len(facade.read_text(encoding="utf-8").splitlines())
    _assert_with_exception(
        path=facade,
        symbol="<module>",
        measured=facade_lines,
        limit=limits["model_cli"],
        exceptions=exceptions,
    )

    measured_keys: set[tuple[str, str, int]] = set()
    for module in sorted(budgeted):
        path = _source_path(module, modules)
        source = path.read_text(encoding="utf-8")
        module_lines = len(source.splitlines())
        _assert_with_exception(
            path=path,
            symbol="<module>",
            measured=module_lines,
            limit=limits["new_module"],
            exceptions=exceptions,
        )
        if module_lines > limits["new_module"]:
            measured_keys.add((path.relative_to(REPO_ROOT).as_posix(), "<module>", module_lines))
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                assert node.end_lineno is not None
                function_lines = node.end_lineno - node.lineno + 1
                _assert_with_exception(
                    path=path,
                    symbol=node.name,
                    measured=function_lines,
                    limit=limits["new_function"],
                    exceptions=exceptions,
                )
                if function_lines > limits["new_function"]:
                    measured_keys.add(
                        (path.relative_to(REPO_ROOT).as_posix(), node.name, function_lines)
                    )
    assert set(exceptions) == measured_keys


def test_active_identifiers_use_domain_names_outside_compatibility_allowlist() -> None:
    policy = _policy()
    modules = _module_paths()
    static_policy = policy["static_policy"]
    pattern = re.compile(static_policy["forbidden_active_name_pattern"], re.IGNORECASE)
    excluded = (
        _string_set(policy, "compatibility_adapters")
        | _string_set(policy, "historical_modules")
        | set(policy["ownership_indexes"].values())
    )
    checked = set(static_policy["budgeted_modules"]) - excluded
    for module in sorted(checked):
        path = _source_path(module, modules)
        assert not pattern.search(module), module
        tree = ast.parse(path.read_text(encoding="utf-8"))
        identifiers = {
            node.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Name)
        }
        identifiers.update(
            node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        )
        identifiers.update(
            node.arg for node in ast.walk(tree) if isinstance(node, ast.arg)
        )
        assert not {name for name in identifiers if pattern.search(name)}, module


def test_public_and_compatibility_contracts_are_bound_to_frozen_fixtures() -> None:
    assert _fixture_commands(MODEL_CLI_FIXTURE) == EXPECTED_COMMANDS
    assert len(EXPECTED_COMMANDS) == 23
    assert _fixture_commands(RUNTIME_CLI_FIXTURE) == ("analyze", "doctor", "demo")
    project = tomllib.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))
    assert project["project"]["scripts"] == {"vnphish": "src.runtime.cli:main"}

    legacy_records = importlib.import_module("src.data_pipeline.schemas")
    core_records = importlib.import_module("src.data_pipeline.core.records")
    for symbol in PUBLIC_RECORD_SYMBOLS:
        assert getattr(legacy_records, symbol) is getattr(core_records, symbol)

    for module_name, symbols in SAFE_COMPATIBILITY_CALLABLES.items():
        module = importlib.import_module(module_name)
        for symbol in symbols:
            assert callable(getattr(module, symbol)), f"{module_name}:{symbol}"

    catalog = importlib.import_module("src.data_pipeline.migrations")
    assert tuple(catalog.MIGRATIONS) == tuple(EXPECTED_MIGRATIONS)
