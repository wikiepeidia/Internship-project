"""Final static architecture policy for the Phase 41.1 boundary."""

from __future__ import annotations

import ast
from collections import Counter
import copy
import importlib
from pathlib import Path
import re
import shlex
import tomllib
from typing import Any, Callable, Mapping, Sequence

import pytest

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
from tests.architecture.json_contract import load_strict_json, strict_json


REPO_ROOT = Path(__file__).parents[2]
POLICY_PATH = REPO_ROOT / "architecture/module-boundaries.json"
RUNTIME_CLI_FIXTURE = REPO_ROOT / "tests/architecture/fixtures/runtime_cli_contract.json"
ACTIVE_TEXT_FIXTURE = REPO_ROOT / "tests/architecture/fixtures/active_text_contract.json"
PRE_ACTIVE_TEXT_FIXTURE = (
    REPO_ROOT
    / "tests/architecture/fixtures/active_text_contract.pre-extraction.json"
)
TOOL_INVENTORY_FIXTURE = REPO_ROOT / "tests/architecture/fixtures/tool_inventory_contract.json"
SCRIPT_ROOT = REPO_ROOT / "scripts"
DEMO_ASSET_ROOT = REPO_ROOT / "src/runtime/demo_assets"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
EXCEPTION_FIELDS = {
    "path",
    "symbol",
    "measured_lines",
    "reason",
    "compatibility_evidence",
}
DEBT_FIELDS = {"path", "symbol", "measured_lines", "owner", "reason"}
EXPECTED_BUDGETED_MODULES = {
    "src.artifacts",
    "src.config",
    "src.config.settings",
    "src.core",
    "src.core.integrity",
    "src.core_binding",
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
    "src.source_archiving",
    "src.source_archiving.contracts",
    "src.source_archiving.filesystem",
    "src.source_archiving.service",
}
EXPECTED_BUDGETED_TOOLS = {"scripts/archive_phase41_source_closure.py"}
EXPECTED_EXISTING_BUDGET_DEBT = [
    {
        "path": "src/runtime/analyzers/accelerated.py",
        "symbol": "AcceleratedAnalyzer.doctor",
        "measured_lines": 112,
        "owner": "runtime-accelerated-backend-maintenance",
        "reason": (
            "pre-existing active function exceeds the new-function budget outside "
            "the bounded extraction scope"
        ),
    },
    {
        "path": "src/runtime/analyzers/gguf.py",
        "symbol": "GGUFAnalyzer.doctor",
        "measured_lines": 115,
        "owner": "runtime-gguf-backend-maintenance",
        "reason": (
            "pre-existing active function exceeds the new-function budget outside "
            "the bounded extraction scope"
        ),
    },
    {
        "path": "src/runtime/analyzers/local_model.py",
        "symbol": "<module>",
        "measured_lines": 801,
        "owner": "runtime-analyzer-maintenance",
        "reason": (
            "pre-existing active module exceeds the new-module budget outside "
            "the bounded extraction scope"
        ),
    },
    {
        "path": "src/runtime/doctor.py",
        "symbol": "RuntimeDoctor.run",
        "measured_lines": 126,
        "owner": "runtime-doctor-maintenance",
        "reason": (
            "pre-existing active function exceeds the new-function budget outside "
            "the bounded extraction scope"
        ),
    },
]
EXPECTED_ACTIVE_IDENTIFIER_ALLOWLIST = {
    ("src.source_archiving.contracts", "SOURCE_PHASE41_EVALUATION"),
}
SEMANTIC_ARCHIVE_FIELDS = {
    "id",
    "literal",
    "path",
    "owner_symbol",
    "reason",
    "expected_occurrences",
}
_SEMANTIC_ARCHIVE_ROWS = [
    ("expected-schema-version", "phase41-execution-source-manifest-v1", "src/source_archiving/contracts.py", "EXPECTED_SCHEMA_VERSION", "preserve immutable source-manifest schema identity", 1),
    ("receipt-schema-version", "phase411-source-closure-archival-receipt-v1", "src/source_archiving/contracts.py", "RECEIPT_SCHEMA_VERSION", "preserve immutable archival-receipt schema identity", 1),
    ("expected-tree-sha256", "c3bbc8c8adaf7579fd2eb9c59a0081613be4b2cae05dfdb64472938c7e6d0434", "src/source_archiving/contracts.py", "EXPECTED_TREE_SHA256", "preserve immutable source-tree digest identity", 1),
    ("expected-launcher-sha256", "c5f15a32b2c8d8ee196e3ec484707c27c4c05e5389d958626e775e44f52d49e9", "src/source_archiving/contracts.py", "EXPECTED_LAUNCHER_SHA256", "preserve immutable launcher digest identity", 1),
    ("expected-manifest-sha256", "41a3a7e166dd5077b3b2c689868b862bd5665137e1824094eb5ff1cdce2b0c61", "src/source_archiving/contracts.py", "EXPECTED_MANIFEST_SHA256", "preserve immutable manifest digest identity", 1),
    ("provenance-label", "post_evaluation_archival_mirror_not_refactored_metric_producer", "src/source_archiving/contracts.py", "PROVENANCE_LABEL", "preserve immutable archive provenance identity", 1),
    ("source-phase40-callbacks", "src/model_adaptation/phase40_callbacks.py", "src/source_archiving/contracts.py", "_SOURCE_PATHS", "preserve immutable source-closure member identity", 1),
    ("source-phase40-comparison-launch", "src/model_adaptation/phase40_comparison_launch.py", "src/source_archiving/contracts.py", "_SOURCE_PATHS", "preserve immutable source-closure member identity", 1),
    ("source-phase40-contract", "src/model_adaptation/phase40_contract.py", "src/source_archiving/contracts.py", "_SOURCE_PATHS", "preserve immutable source-closure member identity", 1),
    ("source-phase40-evidence", "src/model_adaptation/phase40_evidence.py", "src/source_archiving/contracts.py", "_SOURCE_PATHS", "preserve immutable source-closure member identity", 1),
    ("source-phase40-final-authority", "src/model_adaptation/phase40_final_authority.py", "src/source_archiving/contracts.py", "_SOURCE_PATHS", "preserve immutable source-closure member identity", 1),
    ("source-phase40-gguf", "src/model_adaptation/phase40_gguf.py", "src/source_archiving/contracts.py", "_SOURCE_PATHS", "preserve immutable source-closure member identity", 1),
    ("source-phase40-graphs", "src/model_adaptation/phase40_graphs.py", "src/source_archiving/contracts.py", "_SOURCE_PATHS", "preserve immutable source-closure member identity", 1),
    ("source-phase40-handoff", "src/model_adaptation/phase40_handoff.py", "src/source_archiving/contracts.py", "_SOURCE_PATHS", "preserve immutable source-closure member identity", 1),
    ("source-phase40-metrics", "src/model_adaptation/phase40_metrics.py", "src/source_archiving/contracts.py", "_SOURCE_PATHS", "preserve immutable source-closure member identity", 1),
    ("source-phase40-modes", "src/model_adaptation/phase40_modes.py", "src/source_archiving/contracts.py", "_SOURCE_PATHS", "preserve immutable source-closure member identity", 1),
    ("source-phase40-notebooks", "src/model_adaptation/phase40_notebooks.py", "src/source_archiving/contracts.py", "_SOURCE_PATHS", "preserve immutable source-closure member identity", 1),
    ("source-phase40-phobert-release", "src/model_adaptation/phase40_phobert_release.py", "src/source_archiving/contracts.py", "_SOURCE_PATHS", "preserve immutable source-closure member identity", 1),
    ("source-phase40-production-authorities", "src/model_adaptation/phase40_production_authorities.py", "src/source_archiving/contracts.py", "_SOURCE_PATHS", "preserve immutable source-closure member identity", 1),
    ("source-phase40-release-authorities", "src/model_adaptation/phase40_release_authorities.py", "src/source_archiving/contracts.py", "_SOURCE_PATHS", "preserve immutable source-closure member identity", 1),
    ("source-phase40-review", "src/model_adaptation/phase40_review.py", "src/source_archiving/contracts.py", "_SOURCE_PATHS", "preserve immutable source-closure member identity", 1),
    ("source-phase40-runtime-materialize", "src/model_adaptation/phase40_runtime_materialize.py", "src/source_archiving/contracts.py", "_SOURCE_PATHS", "preserve immutable source-closure member identity", 1),
    ("source-model-cli", "src/model_adaptation/cli.py", "src/source_archiving/contracts.py", "SOURCE_MODEL_CLI", "preserve immutable source-closure member identity", 1),
    ("source-phase41-evaluation", "src/model_adaptation/phase41_evaluation.py", "src/source_archiving/contracts.py", "SOURCE_PHASE41_EVALUATION", "preserve immutable source-closure member identity", 1),
    ("source-phase41-protocols", "src/model_adaptation/phase41_protocols.py", "src/source_archiving/contracts.py", "_SOURCE_PATHS", "preserve immutable source-closure member identity", 1),
    ("production-evidence-root", r"C:\ProgramData\VNPhish\phase41-evaluation-evidence", "src/source_archiving/service.py", "PRODUCTION_EVIDENCE_ROOT", "preserve immutable production evidence authority identity", 1),
    ("launcher-relative-path", "scripts/phase41_one_shot_launcher.ps1", "src/source_archiving/contracts.py", "LAUNCHER_RELATIVE_PATH", "preserve immutable launcher manifest identity", 1),
    ("production-manifest-relative", "data/models/phase41/verified-export/9ac54d58c273ab0a8c2f2b4b61e472a51ca94231a94b6847637ecad6ceee49f7/execution-source-manifest.json", "src/source_archiving/service.py", "PRODUCTION_MANIFEST_PATH", "preserve composed repository manifest authority identity", 1),
    ("production-destination-relative", "historical/phase41-source-closure/c3bbc8c8adaf7579fd2eb9c59a0081613be4b2cae05dfdb64472938c7e6d0434", "src/source_archiving/service.py", "PRODUCTION_DESTINATION", "preserve composed archive destination identity", 1),
    ("manifest-archive-name", "execution-source-manifest.json", "src/source_archiving/contracts.py", "MANIFEST_ARCHIVE_NAME", "preserve archive manifest member name", 1),
    ("receipt-archive-name", "archival-receipt.json", "src/source_archiving/contracts.py", "RECEIPT_ARCHIVE_NAME", "preserve archive receipt member name", 1),
    ("tree-archive-name", "tree", "src/source_archiving/contracts.py", "TREE_ARCHIVE_NAME", "preserve archive tree member name", 1),
    ("archive-command", "archive", "scripts/archive_phase41_source_closure.py", "main", "preserve compatibility archive command token", 2),
    ("verify-command", "verify", "scripts/archive_phase41_source_closure.py", "main", "preserve compatibility verify command token", 1),
    ("windows-reparse-point", "0x00000400", "src/source_archiving/filesystem.py", "_WINDOWS_REPARSE_POINT", "preserve Windows reparse-point flag", 1),
    ("sha256-pattern", "^[0-9a-f]{64}$", "src/source_archiving/contracts.py", "_SHA256_RE", "preserve lowercase SHA-256 validation pattern", 1),
]
EXPECTED_SEMANTIC_ARCHIVE_OWNERS = [
    dict(zip(("id", "literal", "path", "owner_symbol", "reason", "expected_occurrences"), row))
    for row in _SEMANTIC_ARCHIVE_ROWS
]
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
    payload = load_strict_json(POLICY_PATH)
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
    payload = load_strict_json(path)
    return tuple(row["command"] for row in payload["parser"]["subcommands"])


def _qualified_function_nodes(tree: ast.AST) -> list[tuple[str, ast.AST]]:
    functions: list[tuple[str, ast.AST]] = []

    class Visitor(ast.NodeVisitor):
        def __init__(self) -> None:
            self.scope: list[str] = []

        def visit_ClassDef(self, node: ast.ClassDef) -> None:  # noqa: N802
            self.scope.append(node.name)
            self.generic_visit(node)
            self.scope.pop()

        def _visit_function(
            self, node: ast.FunctionDef | ast.AsyncFunctionDef
        ) -> None:
            symbol = ".".join([*self.scope, node.name])
            functions.append((symbol, node))
            self.scope.append(node.name)
            self.generic_visit(node)
            self.scope.pop()

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
            self._visit_function(node)

        def visit_AsyncFunctionDef(  # noqa: N802
            self, node: ast.AsyncFunctionDef
        ) -> None:
            self._visit_function(node)

    Visitor().visit(tree)
    return functions


def _over_budget_measurements(
    *, path: Path, source: str, module_limit: int, function_limit: int
) -> set[tuple[str, str, int]]:
    relative = path.relative_to(REPO_ROOT).as_posix()
    measured: set[tuple[str, str, int]] = set()
    module_lines = len(source.splitlines())
    if module_lines > module_limit:
        measured.add((relative, "<module>", module_lines))
    for symbol, node in _qualified_function_nodes(ast.parse(source)):
        assert getattr(node, "end_lineno", None) is not None
        function_lines = int(node.end_lineno) - int(node.lineno) + 1
        if function_lines > function_limit:
            measured.add((relative, symbol, function_lines))
    return measured


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
        or module == "src.config"
        or module.startswith("src.config.")
        or module.startswith(
            (
                "src.artifacts.",
                "src.core",
                "src.data_pipeline",
                "src.model_adaptation",
                "src.modeling",
                "src.runtime",
                "src.source_archiving",
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
    assert set(static_policy["budgeted_tools"]) == EXPECTED_BUDGETED_TOOLS
    assert static_policy["budget_exceptions"] == []

    facade = _source_path("src.model_adaptation.cli", modules)
    facade_lines = len(facade.read_text(encoding="utf-8").splitlines())
    assert facade_lines <= limits["model_cli"]

    for module in sorted(budgeted):
        path = _source_path(module, modules)
        source = path.read_text(encoding="utf-8")
        assert not _over_budget_measurements(
            path=path,
            source=source,
            module_limit=limits["new_module"],
            function_limit=limits["new_function"],
        )

    for relative in sorted(EXPECTED_BUDGETED_TOOLS):
        path = REPO_ROOT / relative
        source = path.read_text(encoding="utf-8")
        assert not _over_budget_measurements(
            path=path,
            source=source,
            module_limit=limits["new_module"],
            function_limit=limits["new_function"],
        )

    debt = static_policy["existing_budget_debt"]
    assert debt == EXPECTED_EXISTING_BUDGET_DEBT
    assert all(set(row) == DEBT_FIELDS for row in debt)
    expected_debt_keys = {
        (row["path"], row["symbol"], row["measured_lines"]) for row in debt
    }
    derived_debt_keys: set[tuple[str, str, int]] = set()
    active = _string_set(policy, "active_modules")
    for module in sorted(active - budgeted):
        path = _source_path(module, modules)
        derived_debt_keys.update(
            _over_budget_measurements(
                path=path,
                source=path.read_text(encoding="utf-8"),
                module_limit=limits["new_module"],
                function_limit=limits["new_function"],
            )
        )
    assert derived_debt_keys == expected_debt_keys
    assert not {
        row["path"] for row in debt
    } & {
        _source_path(module, modules).relative_to(REPO_ROOT).as_posix()
        for module in budgeted
    }


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
        violations = {
            (module, name) for name in identifiers if pattern.search(name)
        }
        assert violations <= EXPECTED_ACTIVE_IDENTIFIER_ALLOWLIST, module

    active_text = _json_fixture(ACTIVE_TEXT_FIXTURE)
    owner = next(
        row
        for row in active_text["frozen_literal_owners"]
        if row["id"] == "archive-source-phase41-evaluation"
    )
    assert owner["path"] == "src/source_archiving/contracts.py"
    assert owner["owner_symbol"] == "SOURCE_PHASE41_EVALUATION"
    assert EXPECTED_ACTIVE_IDENTIFIER_ALLOWLIST == {
        ("src.source_archiving.contracts", owner["owner_symbol"])
    }


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


def _json_fixture(path: Path) -> dict[str, Any]:
    payload = load_strict_json(path)
    assert isinstance(payload, dict)
    return payload


def _must_reject(check: Callable[[], None]) -> None:
    try:
        check()
    except (AssertionError, SyntaxError, ValueError):
        return
    raise AssertionError("mutated contract was accepted")


def test_architecture_json_authorities_reject_duplicates_and_nonfinite() -> None:
    for raw in (
        b'{"schema_version":"first","schema_version":"second"}',
        b'{"value":NaN}',
        b'{"value":Infinity}',
        b'{"value":-Infinity}',
    ):
        with pytest.raises(AssertionError):
            strict_json(raw)


def _validate_active_edges(
    candidate: object,
    *,
    active: set[str],
    derived: list[list[str]],
) -> None:
    assert isinstance(candidate, list)
    assert candidate == derived
    normalized = [tuple(edge) for edge in candidate]
    assert len(normalized) == len(set(normalized))
    assert normalized == sorted(normalized)
    assert all(len(edge) == 2 and set(edge) <= active for edge in normalized)


def test_policy_closes_config_modules_and_exact_active_edges() -> None:
    policy = _policy()
    modules = _module_paths()
    imports = _import_edges(modules)
    active = _string_set(policy, "active_modules")
    assert {"src.config", "src.config.settings"} <= active
    assert {"src.config", "src.config.settings"} <= set(
        policy["static_policy"]["budgeted_modules"]
    )
    derived = sorted(
        [source, target]
        for source in active
        for target in imports[source]
        if target in active
    )
    declared = policy["static_policy"]["active_edges"]
    _validate_active_edges(declared, active=active, derived=derived)

    mutations: list[object] = [
        declared[:-1],
        [*declared, ["src.runtime.cli", "src.runtime.service"]],
        [*declared, ["src.runtime.cli", "src.model_adaptation"]],
        [*declared, list(reversed(declared[0]))],
    ]
    for mutation in mutations:
        _must_reject(
            lambda mutation=mutation: _validate_active_edges(
                mutation, active=active, derived=derived
            )
        )


def _ast_imports(source: str) -> list[str]:
    tree = ast.parse(source)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return sorted(imported)


def _embedded_imports(source: str) -> list[str]:
    imported: set[str] = set()
    for line in source.splitlines():
        stripped = line.strip()
        direct = re.fullmatch(r"import\s+([A-Za-z0-9_., ]+)", stripped)
        if direct:
            imported.update(
                item.strip().split()[0]
                for item in direct.group(1).split(",")
                if item.strip()
            )
            continue
        from_import = re.fullmatch(
            r"from\s+([A-Za-z0-9_.]+)\s+import\s+.+", stripped
        )
        if from_import:
            imported.add(from_import.group(1))
    return sorted(imported)


def _route_token(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if (
        isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == "sys"
        and node.attr == "executable"
    ):
        return "python"
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "str"
        and len(node.args) == 1
    ):
        value = node.args[0]
        if isinstance(value, ast.Name) and value.id == "port":
            return "{port}"
        if isinstance(value, ast.Name) and value.id == "BAT_PATH":
            return "{repo}/scripts/START_DEMO_UI.bat"
        if isinstance(value, ast.Name):
            return "{" + value.id.casefold() + "}"
        if (
            isinstance(value, ast.Attribute)
            and isinstance(value.value, ast.Name)
            and value.value.id == "args"
            and value.attr == "port"
        ):
            return "{port}"
        qualified = _qualified_call_name(value, {})
        if qualified is not None:
            return "{" + qualified.casefold() + "}"
    return None


def _execution_aliases(tree: ast.AST) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                aliases[alias.asname or alias.name.split(".", 1)[0]] = alias.name
        elif isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                aliases[alias.asname or alias.name] = f"{node.module}.{alias.name}"
    return aliases


def _qualified_call_name(node: ast.AST, aliases: Mapping[str, str]) -> str | None:
    if isinstance(node, ast.Name):
        return aliases.get(node.id, node.id)
    if isinstance(node, ast.Attribute):
        owner = _qualified_call_name(node.value, aliases)
        return f"{owner}.{node.attr}" if owner else None
    return None


def _static_route(node: ast.AST, *, where: str) -> list[str]:
    if isinstance(node, (ast.List, ast.Tuple)):
        tokens = [_route_token(item) for item in node.elts]
        if any(token is None for token in tokens):
            raise AssertionError(f"unreviewed executable statement at {where}")
        return [str(token) for token in tokens]
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return shlex.split(node.value, posix=True)
    raise AssertionError(f"unreviewed executable statement at {where}")


def _python_routes(source: str) -> list[list[str]]:
    tree = ast.parse(source)
    aliases = _execution_aliases(tree)
    execution_apis = {
        "subprocess.Popen", "subprocess.run", "subprocess.call",
        "subprocess.check_call", "subprocess.check_output", "os.system",
        "os.popen", "os.startfile",
    }
    command_keywords = {
        "subprocess.Popen": "args",
        "subprocess.run": "args",
        "subprocess.call": "args",
        "subprocess.check_call": "args",
        "subprocess.check_output": "args",
        "os.system": "command",
        "os.popen": "cmd",
        "os.startfile": "path",
    }
    delegated_wrapper = any(
        isinstance(node, ast.FunctionDef)
        and node.name == "command_output"
        and node.args.args
        and node.args.args[0].arg == "command"
        for node in tree.body
    )
    routes: list[tuple[int, list[str]]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        function_name = _qualified_call_name(node.func, aliases)
        if any(keyword.arg is None for keyword in node.keywords):
            if function_name in execution_apis or function_name == "command_output":
                raise AssertionError(f"unreviewed executable statement at line {node.lineno}")
            continue
        keyword_name = (
            "command" if function_name == "command_output" else command_keywords.get(function_name)
        )
        if keyword_name is None:
            continue
        keyword_nodes = [
            keyword.value for keyword in node.keywords if keyword.arg == keyword_name
        ]
        if len(node.args) > 1 or len(keyword_nodes) > 1 or (node.args and keyword_nodes):
            raise AssertionError(f"unreviewed executable statement at line {node.lineno}")
        command_node = node.args[0] if node.args else keyword_nodes[0] if keyword_nodes else None
        if command_node is None:
            raise AssertionError(f"unreviewed executable statement at line {node.lineno}")
        if function_name == "command_output" and delegated_wrapper:
            routes.append(
                (node.lineno, _static_route(command_node, where=f"line {node.lineno}"))
            )
            continue
        if function_name not in execution_apis:
            continue
        for keyword in node.keywords:
            if keyword.arg == "shell" and not (
                isinstance(keyword.value, ast.Constant) and keyword.value.value is False
            ):
                raise AssertionError(f"unreviewed executable statement at line {node.lineno}")
            if keyword.arg == "executable" and not (
                isinstance(keyword.value, ast.Constant) and keyword.value.value is None
            ):
                raise AssertionError(f"unreviewed executable statement at line {node.lineno}")
        if (
            delegated_wrapper
            and function_name == "subprocess.run"
            and isinstance(command_node, ast.Name)
            and command_node.id == "command"
        ):
            continue
        routes.append(
            (node.lineno, _static_route(command_node, where=f"line {node.lineno}"))
        )
    return [route for _line, route in sorted(routes)]


def _batch_routes(source: str) -> list[list[str]]:
    routes: list[list[str]] = []
    logical = re.sub(r"\^\s*\r?\n\s*", " ", source)
    for raw_line in logical.splitlines():
        line = raw_line.strip().lstrip("@").strip()
        lowered = line.casefold()
        if not line or lowered.startswith(("rem ", "::", "echo")):
            continue
        if re.match(r"(?i)^(?:cd(?:\s|$)|chcp(?:\s|$)|pause(?:\s|$))", line):
            continue
        if re.match(r"(?i)^(?:start|call)\b|^[&|]", line):
            raise AssertionError("unreviewed executable statement in batch tool")
        if re.match(
            r"(?i)^(?:python(?:3)?|py|cmd(?:\.exe)?|powershell(?:\.exe)?|pwsh(?:\.exe)?|bash|sh)\b",
            line,
        ):
            routes.append(shlex.split(line, posix=True))
            continue
        raise AssertionError("unreviewed executable statement in batch tool")
    return routes


def _powershell_routes(path: Path, source: str) -> list[list[str]]:
    forbidden_wrappers = re.findall(
        r"(?im)^\s*(?:Start-Process|cmd(?:\.exe)?\s+/c|powershell(?:\.exe)?\s+-Command|pwsh(?:\.exe)?\s+-Command)\b",
        source,
    )
    assert not forbidden_wrappers, "unreviewed executable statement in PowerShell tool"
    call_operators = re.findall(r"(?m)^\s*&\s+([^\r\n]+)", source)
    dot_operators = re.findall(r"(?m)^\s*\.\s+([^\r\n]+)", source)
    direct_process_heads = re.findall(
        r"(?im)^\s*(?:python(?:3)?|py|git|cmd(?:\.exe)?|powershell(?:\.exe)?|"
        r"pwsh(?:\.exe)?|bash|sh|[^\s]+\.(?:exe|com|cmd|bat|ps1|sh))\b[^\r\n]*",
        source,
    )
    dotnet_starts = re.findall(r"\[System\.Diagnostics\.Process\]::Start\s*\(", source)
    if path.name == "phase40_comparison_launcher.ps1":
        assert call_operators == [] and dot_operators == [] and len(dotnet_starts) == 1
        match = re.search(
            r"\$FinalizerArguments\s*=\s*@\((.*?)\)\s*\r?\n",
            source,
            re.DOTALL,
        )
        assert match is not None
        return [["python", *re.findall(r"'([^']*)'", match.group(1))]]
    if path.name == "phase41_one_shot_launcher.ps1":
        assert len(call_operators) == 1 and dot_operators == []
        assert call_operators[0].lstrip().startswith("$PythonPath ")
        assert len(dotnet_starts) == 1
        match = re.search(
            r"foreach\s*\(\$Argument\s+in\s+@\((.*?)\)\s*\)\s*\{",
            source,
            re.DOTALL,
        )
        assert match is not None
        argument_tokens: list[str] = []
        for literal, variable in re.findall(r"'([^']*)'|\$([A-Za-z][A-Za-z0-9]*)", match.group(1)):
            if literal:
                argument_tokens.append(literal)
            else:
                argument_tokens.append(
                    {
                        "Bootstrap": "{bootstrap}",
                        "CleanRoot": "{clean_root}",
                        "ResolvedOutput": "{resolved_output}",
                    }[variable]
                )
        block = re.search(r"\$Bootstrap\s*=\s*@'\r?\n(.*?)\r?\n'@", source, re.DOTALL)
        assert block is not None
        tree = ast.parse(block.group(1))
        argv: list[str] | None = None
        module: str | None = None
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Assign)
                and any(
                    isinstance(target, ast.Attribute)
                    and isinstance(target.value, ast.Name)
                    and target.value.id == "sys"
                    and target.attr == "argv"
                    for target in node.targets
                )
                and isinstance(node.value, ast.List)
            ):
                values: list[str] = []
                for item in node.value.elts:
                    if isinstance(item, ast.Constant) and isinstance(item.value, str):
                        values.append(item.value)
                    else:
                        values.append("{resolved_output}")
                argv = values
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "runpy"
                and node.func.attr == "run_module"
                and node.args
                and isinstance(node.args[0], ast.Constant)
            ):
                module = str(node.args[0].value)
        assert argv is not None and module is not None and argv[0] == module
        return [["python", *argument_tokens], ["runpy", module, *argv[1:]]]
    if call_operators or dot_operators or dotnet_starts or direct_process_heads:
        raise AssertionError("unreviewed executable statement in PowerShell tool")
    return []


def _bash_routes(path: Path, source: str) -> list[list[str]]:
    if re.search(
        r"(?im)^\s*(?:sh\s+-c|bash\s+-c|cmd(?:\.exe)?\s+/c|powershell(?:\.exe)?\s+-Command|pwsh(?:\.exe)?\s+-Command|eval\b)",
        source,
    ):
        raise AssertionError("unreviewed executable statement in shell tool")
    shell_delegations = re.findall(r"(?m)^\s*(?:bash|sh)\s+([^\r\n]+)$", source)
    if path.name != "vastai_qlora_full.sh":
        direct_process_heads = re.findall(
            r"(?im)^\s*(?:python(?:3)?|py|git|cmd(?:\.exe)?|powershell(?:\.exe)?|"
            r"pwsh(?:\.exe)?|bash|sh|[^\s]+\.(?:exe|com|cmd|bat|ps1|sh))\b[^\r\n]*",
            source,
        )
        if shell_delegations or (path.name != "vastai_gguf_export.sh" and direct_process_heads):
            raise AssertionError("unreviewed executable statement in shell tool")
        return []
    logical = re.sub(r"\\\s*\r?\n\s*", " ", source)
    training = re.search(
        r"(?m)^python3\s+-m\s+src\.model_adaptation\.cli\s+train\s+([^\r\n]+)",
        logical,
    )
    delegation = re.search(
        r"(?m)^\s*bash\s+\"\$REPO/historical/tooling/training/vastai_gguf_export\.sh\"\s*$",
        source,
    )
    assert training is not None and delegation is not None
    assert shell_delegations == [
        '"$REPO/historical/tooling/training/vastai_gguf_export.sh"'
    ]
    tokens = shlex.split(
        "python3 -m src.model_adaptation.cli train " + training.group(1),
        posix=True,
    )
    replacements = {
        "$VERSION": "{version}",
        "$MODEL_ROOT": "{model_root}",
        "$REGISTRY": "{registry}",
    }
    return [
        [replacements.get(token, token) for token in tokens],
        ["bash", "{repo}/historical/tooling/training/vastai_gguf_export.sh"],
    ]


def _derive_tool_record_from_source(
    record: Mapping[str, Any],
    source: str,
) -> tuple[list[str], list[list[str]]]:
    path = REPO_ROOT / str(record["path"])
    language = record["language"]
    imports = _ast_imports(source) if language == "python" else _embedded_imports(source)
    if language == "python":
        routes = _python_routes(source)
    elif language == "batch":
        routes = _batch_routes(source)
    elif language == "powershell":
        routes = _powershell_routes(path, source)
    elif language == "bash":
        routes = _bash_routes(path, source)
    else:
        raise AssertionError(f"unreviewed tool language: {language}")
    return imports, routes


def _derive_tool_record(record: Mapping[str, Any]) -> tuple[list[str], list[list[str]]]:
    path = REPO_ROOT / str(record["path"])
    return _derive_tool_record_from_source(record, path.read_text(encoding="utf-8"))


def _validate_tool_contract(candidate: object, expected: Mapping[str, Any]) -> None:
    assert isinstance(candidate, dict)
    assert set(candidate) == {"contract_state", "tools"}
    assert candidate["contract_state"] == "post_extraction_v1"
    assert candidate == expected
    tools = candidate["tools"]
    assert isinstance(tools, list) and len(tools) == 5
    fields = {
        "path",
        "lifecycle",
        "language",
        "kind",
        "phase_language",
        "imports",
        "routes",
    }
    for row in tools:
        assert isinstance(row, dict) and set(row) == fields
        assert row["imports"] == sorted(set(row["imports"]))
        assert len(row["routes"]) == len({tuple(route) for route in row["routes"]})
    assert len({row["path"] for row in tools}) == 5
    assert Counter(row["lifecycle"] for row in tools) == Counter(
        active=2, compatibility=1, historical=2
    )
    assert Counter(row["language"] for row in tools) == Counter(
        python=1, powershell=2, batch=2
    )
    assert Counter(row["kind"] for row in tools) == Counter(
        runtime_launcher=2,
        provenance_cli=1,
        evidence_launcher=2,
    )
    assert Counter(row["phase_language"] for row in tools) == Counter(
        phase_neutral=2,
        phase_40=1,
        phase_41=2,
    )


def test_tool_inventory_exactly_classifies_scripts_imports_and_routes() -> None:
    policy = _policy()
    fixture = _json_fixture(TOOL_INVENTORY_FIXTURE)
    _validate_tool_contract(fixture, fixture)
    static = policy["static_policy"]
    assert static["tool_contract_state"] == fixture["contract_state"]
    assert static["tools"] == fixture["tools"]
    discovered = {
        path.relative_to(REPO_ROOT).as_posix()
        for path in SCRIPT_ROOT.iterdir()
        if path.is_file() and path.name != "README.md"
    }
    assert discovered == {row["path"] for row in fixture["tools"]}

    derived_edges: list[list[str]] = []
    for row in fixture["tools"]:
        imports, routes = _derive_tool_record(row)
        assert imports == row["imports"], row["path"]
        assert routes == row["routes"], row["path"]
        derived_edges.extend(
            [row["path"], imported]
            for imported in imports
            if imported.startswith("src.")
        )
    assert static["active_tool_edges"] == derived_edges == [
        ["scripts/archive_phase41_source_closure.py", "src.source_archiving"]
    ]
    assert not any(str(edge[0]).startswith("scripts/") for edge in policy["allowed_edges"])

    for field in ("path", "lifecycle", "language", "kind", "phase_language", "imports", "routes"):
        mutant = copy.deepcopy(fixture)
        mutant["tools"][0][field] = (
            "wrong"
            if field not in {"imports", "routes"}
            else ["wrong"]
            if field == "imports"
            else [["wrong"]]
        )
        _must_reject(lambda mutant=mutant: _validate_tool_contract(mutant, fixture))
    for mutant in (
        {**fixture, "contract_state": "pre_extraction_v1"},
        {**fixture, "tools": fixture["tools"][:-1]},
        {**fixture, "tools": [*fixture["tools"], copy.deepcopy(fixture["tools"][0])]},
    ):
        _must_reject(lambda mutant=mutant: _validate_tool_contract(mutant, fixture))

    python_mutations = {
        "import subprocess\nsubprocess.run(['python', '-m', 'src.runtime.cli', 'demo'])\n": [
            ["python", "-m", "src.runtime.cli", "demo"]
        ],
        "import subprocess\nsubprocess.call(['python', '-m', 'src.runtime.cli', 'demo'])\n": [
            ["python", "-m", "src.runtime.cli", "demo"]
        ],
        "import os\nos.system('python -m src.runtime.cli demo')\n": [
            ["python", "-m", "src.runtime.cli", "demo"]
        ],
        "import subprocess\nsubprocess.run(args=['python', '-m', 'src.runtime.cli', 'demo'])\n": [
            ["python", "-m", "src.runtime.cli", "demo"]
        ],
    }
    for source, expected_routes in python_mutations.items():
        assert _python_routes(source) == expected_routes
    for source in (
        "import subprocess\nsubprocess.run(command)\n",
        "import subprocess\nsubprocess.run('python -m src.runtime.cli demo', shell=True)\n",
        "import subprocess\nsubprocess.run(args=command)\n",
        "import subprocess\nsubprocess.run(['python'], args=['python'])\n",
        "import subprocess\nsubprocess.run(args=['python'], **options)\n",
        "import subprocess\nsubprocess.run(args=['python'], shell=dynamic)\n",
        "import subprocess\nsubprocess.run(args=['python'], executable='other-python')\n",
    ):
        with pytest.raises(AssertionError, match="unreviewed executable statement"):
            _python_routes(source)

    assert _batch_routes("cmd /c python -m src.runtime.cli demo\n") == [
        ["cmd", "/c", "python", "-m", "src.runtime.cli", "demo"]
    ]
    assert _batch_routes("powershell -Command python -m src.runtime.cli demo\n")
    for source in (
        "start powershell -File unsafe.ps1\n",
        "call python -m src.runtime.cli demo\n",
        "unsafe.exe --flag\n",
        "& unsafe.exe\n",
        "unclassified-command --flag\n",
    ):
        with pytest.raises(AssertionError, match="unreviewed executable statement"):
            _batch_routes(source)
    for source in (
        "Start-Process python -ArgumentList '-m src.runtime.cli demo'\n",
        "cmd /c python -m src.runtime.cli demo\n",
        "powershell -Command python -m src.runtime.cli demo\n",
        "& $UnreviewedExecutable -ArgumentList 'demo'\n",
        ". $UnreviewedExecutable -ArgumentList 'demo'\n",
        "unsafe.exe --flag\n",
    ):
        with pytest.raises(AssertionError, match="unreviewed executable statement"):
            _powershell_routes(Path("synthetic.ps1"), source)
    for source in (
        "sh -c 'python -m src.runtime.cli demo'\n",
        "bash other-script.sh\n",
        "unsafe.exe --flag\n",
        "python -m src.runtime.cli demo\n",
    ):
        with pytest.raises(AssertionError, match="unreviewed|shell-to-shell"):
            _bash_routes(Path("synthetic.sh"), source)


def _validate_active_text_contract(candidate: object, expected: Mapping[str, Any]) -> None:
    assert isinstance(candidate, dict)
    assert set(candidate) == {
        "contract_state",
        "text_assets",
        "binary_assets",
        "active_documents",
        "historical_documents",
        "literal_markers",
        "frozen_literal_owners",
    }
    assert candidate["contract_state"] == "post_extraction_v1"
    assert candidate == expected
    assert len(candidate["text_assets"]) == 4
    assert len(candidate["binary_assets"]) == 12
    assert len(candidate["active_documents"]) == 8
    assert candidate["historical_documents"] == ["walkthrough/README.md"]
    for key in ("text_assets", "binary_assets", "active_documents", "historical_documents"):
        assert len(candidate[key]) == len(set(candidate[key]))
    markers = candidate["literal_markers"]
    owners = candidate["frozen_literal_owners"]
    assert len(markers) == 15
    assert len(owners) == 31
    assert all(
        set(row) == {"path", "marker_id", "start_marker", "end_marker", "reason", "owner"}
        for row in markers
    )
    assert len({(row["path"], row["marker_id"]) for row in markers}) == 15
    marker_tokens = [token for row in markers for token in (row["start_marker"], row["end_marker"])]
    assert len(marker_tokens) == len(set(marker_tokens)) == 30
    assert all(
        set(row) == {"id", "path", "literal", "owner_symbol", "reason", "lifecycle"}
        for row in owners
    )
    assert len({row["id"] for row in owners}) == 31
    assert {row["lifecycle"] for row in owners} == {"active"}


def _owner_ast_node(source: str, owner_symbol: str) -> ast.AST:
    tree = ast.parse(source)
    if owner_symbol == "<module>.__doc__":
        assert tree.body and isinstance(tree.body[0], ast.Expr)
        return tree.body[0]

    class_name, separator, member_name = owner_symbol.partition(".")
    candidates: list[ast.AST] = []
    if separator:
        for node in tree.body:
            if not isinstance(node, ast.ClassDef) or node.name != class_name:
                continue
            for child in node.body:
                targets: Sequence[ast.expr] = ()
                if isinstance(child, ast.Assign):
                    targets = child.targets
                elif isinstance(child, ast.AnnAssign):
                    targets = (child.target,)
                if any(isinstance(target, ast.Name) and target.id == member_name for target in targets):
                    candidates.append(child)
    else:
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == owner_symbol:
                candidates.append(node)
        for node in tree.body:
            targets: Sequence[ast.expr] = ()
            if isinstance(node, ast.Assign):
                targets = node.targets
            elif isinstance(node, ast.AnnAssign):
                targets = (node.target,)
            if any(isinstance(target, ast.Name) and target.id == owner_symbol for target in targets):
                candidates.append(node)
    assert len(candidates) == 1, owner_symbol
    return candidates[0]


def _owner_source_segment(source: str, owner_symbol: str) -> str:
    segment = ast.get_source_segment(source, _owner_ast_node(source, owner_symbol))
    assert segment is not None
    return segment


def _validate_present_marker_regions(contract: Mapping[str, Any]) -> None:
    by_path: dict[str, list[Mapping[str, str]]] = {}
    for row in contract["literal_markers"]:
        by_path.setdefault(row["path"], []).append(row)
    for relative, rows in by_path.items():
        source = (REPO_ROOT / relative).read_text(encoding="utf-8")
        events: list[tuple[int, str, str]] = []
        for row in rows:
            start_count = source.count(row["start_marker"])
            end_count = source.count(row["end_marker"])
            assert start_count == end_count
            assert start_count in {0, 1}
            if start_count:
                start = source.index(row["start_marker"])
                end = source.index(row["end_marker"])
                assert start < end
                events.extend(((start, "start", row["marker_id"]), (end, "end", row["marker_id"])))
        stack: list[str] = []
        for _position, kind, marker_id in sorted(events):
            if kind == "start":
                assert not stack, f"nested marker region: {relative}:{marker_id}"
                stack.append(marker_id)
            else:
                assert stack == [marker_id]
                stack.pop()
        assert not stack


def test_active_text_contract_exactly_classifies_assets_documents_and_markers() -> None:
    policy = _policy()
    fixture = _json_fixture(ACTIVE_TEXT_FIXTURE)
    _validate_active_text_contract(fixture, fixture)
    assert policy["static_policy"]["active_text_scan"] == fixture

    discovered_assets = {
        path.relative_to(REPO_ROOT).as_posix()
        for path in DEMO_ASSET_ROOT.rglob("*")
        if path.is_file()
    }
    assert discovered_assets == set(fixture["text_assets"]) | set(fixture["binary_assets"])
    assert all((REPO_ROOT / path).is_file() for path in fixture["active_documents"])
    assert all((REPO_ROOT / path).is_file() for path in fixture["historical_documents"])
    _validate_present_marker_regions(fixture)

    for row in fixture["frozen_literal_owners"]:
        source = (REPO_ROOT / row["path"]).read_text(encoding="utf-8")
        segment = _owner_source_segment(source, row["owner_symbol"])
        assert segment.count(row["literal"]) == 1, row["id"]

    list_fields = (
        "text_assets",
        "binary_assets",
        "active_documents",
        "historical_documents",
        "literal_markers",
        "frozen_literal_owners",
    )
    for field in list_fields:
        missing = copy.deepcopy(fixture)
        missing[field] = missing[field][:-1]
        _must_reject(lambda missing=missing: _validate_active_text_contract(missing, fixture))
        duplicate = copy.deepcopy(fixture)
        duplicate[field].append(copy.deepcopy(duplicate[field][0]))
        _must_reject(lambda duplicate=duplicate: _validate_active_text_contract(duplicate, fixture))
    for field in ("path", "marker_id", "start_marker", "end_marker", "reason", "owner"):
        mutant = copy.deepcopy(fixture)
        mutant["literal_markers"][0][field] += "-wrong"
        _must_reject(lambda mutant=mutant: _validate_active_text_contract(mutant, fixture))
    for field in ("id", "path", "literal", "owner_symbol", "reason", "lifecycle"):
        mutant = copy.deepcopy(fixture)
        mutant["frozen_literal_owners"][0][field] += "-wrong"
        _must_reject(lambda mutant=mutant: _validate_active_text_contract(mutant, fixture))
    stale = copy.deepcopy(fixture)
    stale["contract_state"] = "pre_extraction_v1"
    _must_reject(lambda: _validate_active_text_contract(stale, fixture))


def test_archive_contract_fixtures_transition_atomically() -> None:
    policy = _policy()["static_policy"]
    tools = _json_fixture(TOOL_INVENTORY_FIXTURE)
    active_text = _json_fixture(ACTIVE_TEXT_FIXTURE)

    assert tools["contract_state"] == policy["tool_contract_state"] == "post_extraction_v1"
    assert active_text["contract_state"] == "post_extraction_v1"
    assert policy["active_text_scan"] == active_text
    archive_tool = next(
        row for row in tools["tools"]
        if row["path"] == "scripts/archive_phase41_source_closure.py"
    )
    assert archive_tool["imports"] == [
        "__future__", "argparse", "contextlib", "dataclasses", "datetime",
        "hashlib", "json", "os", "pathlib", "re", "secrets",
        "src.source_archiving", "stat", "sys", "typing",
    ]
    assert policy["tools"] == tools["tools"]
    assert policy["active_tool_edges"] == [
        ["scripts/archive_phase41_source_closure.py", "src.source_archiving"]
    ]

    owners = active_text["frozen_literal_owners"]
    assert len(owners) == 31
    by_id = {row["id"]: row for row in owners}
    assert len(by_id) == 31
    assert {
        "archive-facade-description",
        "archive-worktree-phase41-evaluation",
        "archive-production-launcher-filename",
    }.isdisjoint(by_id)
    assert by_id["archive-source-manifest-schema"] == {
        "id": "archive-source-manifest-schema",
        "path": "src/source_archiving/contracts.py",
        "literal": "phase41-execution-source-manifest-v1",
        "owner_symbol": "EXPECTED_SCHEMA_VERSION",
        "reason": "preserve immutable source-closure schema compatibility",
        "lifecycle": "active",
    }
    assert by_id["archive-source-phase41-evaluation"]["owner_symbol"] == (
        "SOURCE_PHASE41_EVALUATION"
    )
    assert by_id["archive-launcher-relative-path"]["owner_symbol"] == (
        "LAUNCHER_RELATIVE_PATH"
    )
    assert all(row["lifecycle"] == "active" for row in owners)


def _validate_final_tool_policy(candidate: Mapping[str, Any]) -> None:
    fixture = _json_fixture(TOOL_INVENTORY_FIXTURE)
    static = candidate["static_policy"]
    _validate_tool_contract(
        {"contract_state": static["tool_contract_state"], "tools": static["tools"]},
        fixture,
    )
    assert static["active_tool_edges"] == [
        ["scripts/archive_phase41_source_closure.py", "src.source_archiving"]
    ]
    assert not any(str(edge[0]).startswith("scripts/") for edge in candidate["allowed_edges"])


def test_source_archiving_replaces_only_the_compatibility_import_edge() -> None:
    policy = _policy()
    fixture = _json_fixture(TOOL_INVENTORY_FIXTURE)
    _validate_final_tool_policy(policy)
    assert fixture["contract_state"] == "post_extraction_v1"

    facade_path = REPO_ROOT / "scripts/archive_phase41_source_closure.py"
    facade_source = facade_path.read_text(encoding="utf-8")
    direct_imports = [
        alias.name
        for node in ast.walk(ast.parse(facade_source))
        if isinstance(node, ast.Import)
        for alias in node.names
        if alias.name.startswith("src.")
    ]
    assert direct_imports == ["src.source_archiving"]
    assert "src.core_binding" not in direct_imports
    assert not any(name.startswith("src.source_archiving.") for name in direct_imports)

    post_archive = next(
        row
        for row in fixture["tools"]
        if row["path"] == "scripts/archive_phase41_source_closure.py"
    )
    pre = copy.deepcopy(fixture)
    pre["contract_state"] = "pre_extraction_v1"
    pre_archive = next(
        row
        for row in pre["tools"]
        if row["path"] == "scripts/archive_phase41_source_closure.py"
    )
    pre_archive["imports"] = [
        "src.core_binding" if value == "src.source_archiving" else value
        for value in pre_archive["imports"]
    ]
    assert len(pre["tools"]) == len(fixture["tools"]) == 5
    assert all(
        before == after
        for before, after in zip(pre["tools"], fixture["tools"])
        if before["path"] != "scripts/archive_phase41_source_closure.py"
    )
    assert {
        key
        for key in post_archive
        if post_archive[key] != pre_archive[key]
    } == {"imports"}
    assert set(post_archive["imports"]) ^ set(pre_archive["imports"]) == {
        "src.core_binding",
        "src.source_archiving",
    }

    mutants: list[dict[str, Any]] = []
    for imports in (
        [value for value in post_archive["imports"] if value != "src.source_archiving"],
        sorted([*post_archive["imports"], "src.core_binding"]),
        [
            "src.source_archiving.service"
            if value == "src.source_archiving"
            else value
            for value in post_archive["imports"]
        ],
    ):
        mutant = copy.deepcopy(policy)
        row = next(
            item
            for item in mutant["static_policy"]["tools"]
            if item["path"] == "scripts/archive_phase41_source_closure.py"
        )
        row["imports"] = imports
        mutants.append(mutant)
    route_drift = copy.deepcopy(policy)
    route_drift["static_policy"]["tools"][0]["routes"] = [["python", "wrong"]]
    mutants.append(route_drift)
    lifecycle_drift = copy.deepcopy(policy)
    lifecycle_drift["static_policy"]["tools"][3]["lifecycle"] = "active"
    mutants.append(lifecycle_drift)
    old_edge = copy.deepcopy(policy)
    old_edge["static_policy"]["active_tool_edges"] = [
        ["scripts/archive_phase41_source_closure.py", "src.core_binding"]
    ]
    mutants.append(old_edge)
    both_edges = copy.deepcopy(policy)
    both_edges["static_policy"]["active_tool_edges"].append(
        ["scripts/archive_phase41_source_closure.py", "src.core_binding"]
    )
    mutants.append(both_edges)
    relation_in_allowlist = copy.deepcopy(policy)
    relation_in_allowlist["allowed_edges"].append(
        ["scripts/archive_phase41_source_closure.py", "src.source_archiving"]
    )
    mutants.append(relation_in_allowlist)
    for mutant in mutants:
        _must_reject(lambda mutant=mutant: _validate_final_tool_policy(mutant))


def _validate_pre_active_text_contract(
    candidate: object,
    expected: Mapping[str, Any],
) -> None:
    assert isinstance(candidate, dict)
    assert set(candidate) == {
        "schema_version",
        "contract_state",
        "source_commit",
        "source_blobs",
        "frozen_literal_owners",
    }
    assert candidate == expected
    assert candidate["schema_version"] == "active-text-pre-extraction-binding-v1"
    assert candidate["contract_state"] == "pre_extraction_v1"
    assert candidate["source_commit"] == (
        "de11be785f52aab40be0ff19df3009ba88b51737"
    )
    assert candidate["source_blobs"] == [
        {
            "path": "scripts/archive_phase41_source_closure.py",
            "blob_oid": "b19b22dd06192720eb77ab6c91081f699afdbe7f",
            "sha256": "0d7ab3529936fe3bc9f0cd67cfa2fa9509e632be2330fe7a735fc091eb836f80",
        }
    ]
    owners = candidate["frozen_literal_owners"]
    assert len(owners) == 34
    assert all(
        set(row) == {"id", "path", "literal", "owner_symbol", "reason", "lifecycle"}
        for row in owners
    )
    assert len({row["id"] for row in owners}) == 34
    assert {row["lifecycle"] for row in owners} == {"active", "compatibility"}


def _validate_semantic_archive_contract(candidate: object) -> None:
    assert isinstance(candidate, list)
    assert candidate == EXPECTED_SEMANTIC_ARCHIVE_OWNERS
    assert len(candidate) == 36
    assert all(set(row) == SEMANTIC_ARCHIVE_FIELDS for row in candidate)
    assert len({row["id"] for row in candidate}) == 36
    assert all(
        isinstance(row["expected_occurrences"], int)
        and row["expected_occurrences"] > 0
        and isinstance(row["reason"], str)
        and row["reason"].strip()
        for row in candidate
    )


def _semantic_owner_occurrences(row: Mapping[str, Any]) -> int:
    source = (REPO_ROOT / row["path"]).read_text(encoding="utf-8")
    node = _owner_ast_node(source, row["owner_symbol"])
    segment = ast.get_source_segment(source, node)
    assert segment is not None
    if row["id"] in {"archive-command", "verify-command"}:
        return sum(
            isinstance(child, ast.Constant) and child.value == row["literal"]
            for child in ast.walk(node)
        )
    if row["id"] == "production-manifest-relative":
        base = "data/models/phase41/verified-export"
        digest = "9ac54d58c273ab0a8c2f2b4b61e472a51ca94231a94b6847637ecad6ceee49f7"
        assert row["literal"] == f"{base}/{digest}/execution-source-manifest.json"
        assert segment.count(base) == segment.count(digest) == 1
        assert segment.count("MANIFEST_ARCHIVE_NAME") == 1
        return 1
    if row["id"] == "production-destination-relative":
        base = "historical/phase41-source-closure"
        digest = "c3bbc8c8adaf7579fd2eb9c59a0081613be4b2cae05dfdb64472938c7e6d0434"
        assert row["literal"] == f"{base}/{digest}"
        assert segment.count(base) == segment.count("EXPECTED_TREE_SHA256") == 1
        return 1
    return segment.count(str(row["literal"]))


def test_archive_frozen_literal_ownership_transfers_exactly_once() -> None:
    policy = _policy()["static_policy"]
    final = _json_fixture(ACTIVE_TEXT_FIXTURE)
    _validate_active_text_contract(final, final)
    assert final["contract_state"] == "post_extraction_v1"
    assert policy["active_text_scan"] == final
    assert len(final["frozen_literal_owners"]) == 31

    pre = _json_fixture(PRE_ACTIVE_TEXT_FIXTURE)
    _validate_pre_active_text_contract(pre, pre)
    _must_reject(lambda: _validate_active_text_contract(pre, final))
    post_mislabeled_pre = copy.deepcopy(final)
    post_mislabeled_pre["contract_state"] = "pre_extraction_v1"
    _must_reject(
        lambda: _validate_active_text_contract(post_mislabeled_pre, final)
    )
    pre_mislabeled_post = copy.deepcopy(pre)
    pre_mislabeled_post["contract_state"] = "post_extraction_v1"
    _must_reject(
        lambda: _validate_pre_active_text_contract(pre_mislabeled_post, pre)
    )

    final_by_id = {row["id"]: row for row in final["frozen_literal_owners"]}
    pre_by_id = {row["id"]: row for row in pre["frozen_literal_owners"]}
    final_ids = set(final_by_id)
    removed = {
        "archive-facade-description",
        "archive-worktree-phase41-evaluation",
        "archive-production-launcher-filename",
    }
    assert set(pre_by_id) - final_ids == removed
    assert final_ids < set(pre_by_id)
    for owner_id in sorted(final_ids):
        before = pre_by_id[owner_id]
        after = final_by_id[owner_id]
        assert (before["literal"], before["reason"]) == (
            after["literal"],
            after["reason"],
        )
        if not owner_id.startswith("archive-"):
            assert before == after
            continue
        assert before["path"] == "scripts/archive_phase41_source_closure.py"
        assert before["lifecycle"] == "compatibility"
        assert after["path"].startswith("src/source_archiving/")
        assert after["lifecycle"] == "active"
        expected_before_symbol = {
            "archive-source-phase41-evaluation": "_SOURCE_PATHS",
            "archive-launcher-relative-path": "_manifest_records",
        }.get(owner_id, after["owner_symbol"])
        assert before["owner_symbol"] == expected_before_symbol

    for field in ("source_commit", "source_blobs", "frozen_literal_owners"):
        mutant = copy.deepcopy(pre)
        if field == "source_commit":
            mutant[field] = "0" * 40
        elif field == "source_blobs":
            mutant[field][0]["blob_oid"] = "0" * 40
        else:
            mutant[field][0]["literal"] += "-drift"
        _must_reject(
            lambda mutant=mutant: _validate_pre_active_text_contract(mutant, pre)
        )
    mixed = copy.deepcopy(pre)
    mixed["frozen_literal_owners"][7] = copy.deepcopy(
        final_by_id["archive-receipt-schema"]
    )
    _must_reject(lambda: _validate_pre_active_text_contract(mixed, pre))

    facade_source = (
        REPO_ROOT / "scripts/archive_phase41_source_closure.py"
    ).read_text(encoding="utf-8")
    for row in pre["frozen_literal_owners"]:
        if row["id"].startswith("archive-") and re.search(
            r"phase[0-9]+|ProgramData|data/models|historical/", row["literal"], re.IGNORECASE
        ):
            assert row["literal"] not in facade_source, row["id"]

    semantic = policy["semantic_archive_owners"]
    _validate_semantic_archive_contract(semantic)
    for row in semantic:
        assert _semantic_owner_occurrences(row) == row["expected_occurrences"], row["id"]

    semantic_mutants: list[object] = [
        semantic[:-1],
        [*semantic, copy.deepcopy(semantic[0])],
        [*semantic, {**semantic[0], "id": "new-unregistered-chronology"}],
    ]
    for field in SEMANTIC_ARCHIVE_FIELDS:
        mutant = copy.deepcopy(semantic)
        mutant[0][field] = (
            2 if field == "expected_occurrences" else f"{mutant[0][field]}-wrong"
        )
        semantic_mutants.append(mutant)
    for mutant in semantic_mutants:
        _must_reject(lambda mutant=mutant: _validate_semantic_archive_contract(mutant))

    for field in ("path", "literal", "owner_symbol", "reason", "lifecycle"):
        mutant = copy.deepcopy(final)
        mutant["frozen_literal_owners"][6][field] += "-moved"
        _must_reject(lambda mutant=mutant: _validate_active_text_contract(mutant, final))
