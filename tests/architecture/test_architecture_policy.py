"""Final static architecture policy for the Phase 41.1 boundary."""

from __future__ import annotations

import ast
from collections import Counter
import copy
import importlib
import json
from pathlib import Path
import re
import shlex
import tomllib
from typing import Any, Callable, Mapping, Sequence

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
ACTIVE_TEXT_FIXTURE = REPO_ROOT / "tests/architecture/fixtures/active_text_contract.json"
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


def _json_fixture(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _must_reject(check: Callable[[], None]) -> None:
    try:
        check()
    except (AssertionError, SyntaxError, ValueError):
        return
    raise AssertionError("mutated contract was accepted")


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
        if (
            isinstance(value, ast.Attribute)
            and isinstance(value.value, ast.Name)
            and value.value.id == "args"
            and value.attr == "port"
        ):
            return "{port}"
    return None


def _python_routes(source: str) -> list[list[str]]:
    tree = ast.parse(source)
    routes: list[tuple[int, list[str]]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        function = node.func
        if not (
            isinstance(function, ast.Attribute)
            and function.attr == "Popen"
            and isinstance(function.value, ast.Name)
            and function.value.id == "subprocess"
        ):
            continue
        sequence = node.args[0]
        if not isinstance(sequence, (ast.List, ast.Tuple)):
            continue
        tokens = [_route_token(item) for item in sequence.elts]
        if any(token is None for token in tokens):
            continue
        route = [str(token) for token in tokens]
        if any(
            token == "vnphish"
            or token.startswith("src.")
            or "/scripts/" in token
            for token in route
        ):
            routes.append((node.lineno, route))
    return [route for _line, route in sorted(routes)]


def _batch_routes(source: str) -> list[list[str]]:
    routes: list[list[str]] = []
    logical = re.sub(r"\^\s*\r?\n\s*", " ", source)
    for raw_line in logical.splitlines():
        line = raw_line.strip()
        lowered = line.casefold()
        if not line or lowered.startswith(("rem ", "::", "echo", "@echo")):
            continue
        if re.match(r"(?i)^python\s+-m\s+src\.", line):
            routes.append(shlex.split(line, posix=True))
    return routes


def _powershell_routes(path: Path, source: str) -> list[list[str]]:
    if path.name == "phase40_comparison_launcher.ps1":
        match = re.search(
            r"\$FinalizerArguments\s*=\s*@\((.*?)\)\s*\r?\n",
            source,
            re.DOTALL,
        )
        assert match is not None
        return [["python", *re.findall(r"'([^']*)'", match.group(1))]]
    if path.name == "phase41_one_shot_launcher.ps1":
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
    return []


def _bash_routes(path: Path, source: str) -> list[list[str]]:
    if path.name != "vastai_qlora_full.sh":
        return []
    logical = re.sub(r"\\\s*\r?\n\s*", " ", source)
    training = re.search(
        r"(?m)^python3\s+-m\s+src\.model_adaptation\.cli\s+train\s+([^\r\n]+)",
        logical,
    )
    delegation = re.search(
        r"(?m)^\s*bash\s+\"\$REPO/scripts/vastai_gguf_export\.sh\"\s*$",
        source,
    )
    assert training is not None and delegation is not None
    tokens = shlex.split(
        "python3 -m src.model_adaptation.cli train " + training.group(1),
        posix=True,
    )
    replacements = {
        "$VERSION": "{version}",
        "$MODEL_ROOT": "{model_root}",
        "$REGISTRY": "{registry}",
    }
    return [[replacements.get(token, token) for token in tokens], ["bash", "{repo}/scripts/vastai_gguf_export.sh"]]


def _derive_tool_record(record: Mapping[str, Any]) -> tuple[list[str], list[list[str]]]:
    path = REPO_ROOT / str(record["path"])
    source = path.read_text(encoding="utf-8")
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


def _validate_tool_contract(candidate: object, expected: Mapping[str, Any]) -> None:
    assert isinstance(candidate, dict)
    assert set(candidate) == {"contract_state", "tools"}
    assert candidate["contract_state"] == "pre_extraction_v1"
    assert candidate == expected
    tools = candidate["tools"]
    assert isinstance(tools, list) and len(tools) == 11
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
    assert len({row["path"] for row in tools}) == 11
    assert Counter(row["lifecycle"] for row in tools) == Counter(
        active=2, compatibility=1, historical=8
    )
    assert Counter(row["language"] for row in tools) == Counter(
        python=5, powershell=2, batch=2, bash=2
    )
    assert Counter(row["kind"] for row in tools) == Counter(
        runtime_launcher=2,
        provenance_cli=1,
        latency_probe=1,
        evidence_launcher=2,
        model_export_workflow=1,
        training_workflow=1,
        verification_runner=3,
    )
    assert Counter(row["phase_language"] for row in tools) == Counter(
        phase_neutral=4,
        phase_28=1,
        phase_30=1,
        phase_31=1,
        phase_32=1,
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
        if path.is_file()
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
        ["scripts/archive_phase41_source_closure.py", "src.core_binding"]
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
        {**fixture, "contract_state": "post_extraction_v1"},
        {**fixture, "tools": fixture["tools"][:-1]},
        {**fixture, "tools": [*fixture["tools"], copy.deepcopy(fixture["tools"][0])]},
    ):
        _must_reject(lambda mutant=mutant: _validate_tool_contract(mutant, fixture))


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
    assert candidate["contract_state"] == "pre_extraction_v1"
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
    assert len(owners) == 34
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
    assert len({row["id"] for row in owners}) == 34
    assert {row["lifecycle"] for row in owners} == {"active", "compatibility"}


def _owner_source_segment(source: str, owner_symbol: str) -> str:
    tree = ast.parse(source)
    if owner_symbol == "<module>.__doc__":
        assert tree.body and isinstance(tree.body[0], ast.Expr)
        segment = ast.get_source_segment(source, tree.body[0])
        assert segment is not None
        return segment

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
    segment = ast.get_source_segment(source, candidates[0])
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
    stale["contract_state"] = "post_extraction_v1"
    _must_reject(lambda: _validate_active_text_contract(stale, fixture))
