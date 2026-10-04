"""Static closed-graph policy for active modeling and historical compatibility."""

from __future__ import annotations

import ast
from collections import deque
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Mapping


REPO_ROOT = Path(__file__).parents[2]
SOURCE_ROOT = REPO_ROOT / "src"
POLICY_PATH = REPO_ROOT / "architecture/module-boundaries.json"
PHASE40_INDEX = REPO_ROOT / "src/model_adaptation/legacy/phase40/__init__.py"
PHASE41_INDEX = REPO_ROOT / "src/model_adaptation/legacy/phase41/__init__.py"
ADAPTATION_COMMANDS = REPO_ROOT / "src/model_adaptation/commands/adaptation.py"
ACTIVE_TARGET_PREFIXES = ("src.artifacts", "src.modeling")
RELEVANT_NON_DATA_SINGLETON_MODULES = ("src.artifacts", "src.config")
RELEVANT_NON_DATA_MODULE_PREFIXES = (
    "src.artifacts.",
    "src.config.",
    "src.core",
    "src.model_adaptation",
    "src.modeling",
    "src.runtime",
    "src.source_archiving",
)
POLICY_FIELDS = {
    "active_modules",
    "allowed_edges",
    "compatibility_adapters",
    "data_modules",
    "forbidden_historical_targets",
    "historical_modules",
    "historical_sccs",
    "ownership_indexes",
    "schema_version",
    "static_policy",
}


def _module_name(path: Path) -> str:
    parts = list(path.relative_to(REPO_ROOT).with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _module_paths() -> dict[str, Path]:
    return {_module_name(path): path for path in SOURCE_ROOT.rglob("*.py")}


def _relevant_non_data_modules(modules: Mapping[str, Path]) -> set[str]:
    return {
        module
        for module in modules
        if module in RELEVANT_NON_DATA_SINGLETON_MODULES
        or module.startswith(RELEVANT_NON_DATA_MODULE_PREFIXES)
    }


def _resolve_from(source: str, path: Path, node: ast.ImportFrom) -> str:
    if node.level == 0:
        return node.module or ""
    package = source if path.name == "__init__.py" else source.rpartition(".")[0]
    parts = package.split(".") if package else []
    if node.level > 1:
        parts = parts[: -(node.level - 1)]
    if node.module:
        parts.extend(node.module.split("."))
    return ".".join(parts)


def _import_edges(modules: Mapping[str, Path]) -> dict[str, set[str]]:
    edges = {module: set() for module in modules}
    for source, path in modules.items():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                targets = {alias.name for alias in node.names}
                edges[source].update(target for target in targets if target in modules)
            elif isinstance(node, ast.ImportFrom):
                base = _resolve_from(source, path, node)
                targets = {base}
                if base in modules:
                    edges[source].add(base)
                for alias in node.names:
                    candidate = f"{base}.{alias.name}"
                    targets.add(candidate)
                    if candidate in modules:
                        edges[source].add(candidate)
                # Importing a submodule executes every parent package
                # initializer first; model those implicit live edges.
                for target in targets:
                    parts = target.split(".")
                    edges[source].update(
                        parent
                        for index in range(1, len(parts))
                        if (parent := ".".join(parts[:index])) in modules
                    )
    return edges


def _policy() -> dict[str, Any]:
    payload = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    assert set(payload) == POLICY_FIELDS
    assert payload["schema_version"] == "module-boundaries-v2"
    return payload


def _string_set(policy: Mapping[str, Any], field: str) -> set[str]:
    values = policy[field]
    assert isinstance(values, list)
    assert all(isinstance(value, str) and value for value in values)
    assert len(values) == len(set(values))
    return set(values)


def _data_module_classes(policy: Mapping[str, Any]) -> dict[str, set[str]]:
    values = policy["data_modules"]
    assert isinstance(values, dict)
    assert set(values) == {"compatibility", "core", "migrations", "workflows"}
    classes: dict[str, set[str]] = {}
    for category, modules in values.items():
        assert isinstance(modules, list)
        assert all(isinstance(module, str) and module for module in modules)
        assert len(modules) == len(set(modules))
        classes[category] = set(modules)
    classified: set[str] = set()
    for category, modules in classes.items():
        overlap = classified & modules
        assert not overlap, f"duplicate data modules in {category}: {sorted(overlap)}"
        classified.update(modules)
    return classes


def _owned_modules(path: Path) -> tuple[str, ...]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    assert not any(isinstance(node, (ast.Import, ast.ImportFrom)) for node in ast.walk(tree))
    for node in tree.body:
        target: ast.expr | None = None
        value: ast.expr | None = None
        if isinstance(node, ast.Assign):
            target = node.targets[0]
            value = node.value
        elif isinstance(node, ast.AnnAssign):
            target = node.target
            value = node.value
        if isinstance(target, ast.Name) and target.id == "OWNED_MODULES" and value:
            result = ast.literal_eval(value)
            assert isinstance(result, tuple)
            assert all(isinstance(item, str) and item for item in result)
            return result
    raise AssertionError(f"{path} must declare literal OWNED_MODULES")


def _strong_components(
    nodes: set[str], edges: Mapping[str, set[str]]
) -> set[tuple[str, ...]]:
    index = 0
    stack: list[str] = []
    stacked: set[str] = set()
    indices: dict[str, int] = {}
    lowlinks: dict[str, int] = {}
    components: set[tuple[str, ...]] = set()

    def visit(node: str) -> None:
        nonlocal index
        indices[node] = index
        lowlinks[node] = index
        index += 1
        stack.append(node)
        stacked.add(node)
        for target in sorted(edges[node] & nodes):
            if target not in indices:
                visit(target)
                lowlinks[node] = min(lowlinks[node], lowlinks[target])
            elif target in stacked:
                lowlinks[node] = min(lowlinks[node], indices[target])
        if lowlinks[node] != indices[node]:
            return
        component: list[str] = []
        while True:
            member = stack.pop()
            stacked.remove(member)
            component.append(member)
            if member == node:
                break
        if len(component) > 1:
            components.add(tuple(sorted(component)))

    for node in sorted(nodes):
        if node not in indices:
            visit(node)
    return components


def _path_to_target(
    start: str,
    edges: Mapping[str, set[str]],
    targets: set[str],
) -> tuple[str, ...] | None:
    queue = deque([(start, (start,))])
    seen = {start}
    while queue:
        node, path = queue.popleft()
        for target in sorted(edges[node]):
            if target in targets:
                return (*path, target)
            if target not in seen:
                seen.add(target)
                queue.append((target, (*path, target)))
    return None


def test_policy_closes_every_relevant_module_and_ownership_index() -> None:
    policy = _policy()
    modules = _module_paths()
    active = _string_set(policy, "active_modules")
    adapters = _string_set(policy, "compatibility_adapters")
    historical = _string_set(policy, "historical_modules")
    indexes = policy["ownership_indexes"]
    assert indexes == {
        "phase40": "src.model_adaptation.legacy.phase40",
        "phase41": "src.model_adaptation.legacy.phase41",
    }
    index_modules = set(indexes.values())
    assert not (active & adapters or active & historical or adapters & historical)
    relevant = _relevant_non_data_modules(modules)
    assert relevant == active | adapters | historical | index_modules
    assert set(_owned_modules(PHASE40_INDEX)) | set(
        _owned_modules(PHASE41_INDEX)
    ) == historical
    assert not any("phase40" in name.lower() or "phase41" in name.lower() for name in active)


def test_data_pipeline_classification_is_closed_and_migrations_are_isolated() -> None:
    policy = _policy()
    modules = _module_paths()
    edges = _import_edges(modules)
    classes = _data_module_classes(policy)
    classified = set().union(*classes.values())
    data_pipeline_modules = {
        module
        for module in modules
        if module == "src.data_pipeline" or module.startswith("src.data_pipeline.")
    }
    migration_catalog = "src.data_pipeline.migrations"
    preserved_repairs = {
        "src.data_pipeline.apply_mislabel_triage",
        "src.data_pipeline.apply_task_scam_risk_tier_repair",
        "src.data_pipeline.reconstruct_zalo_direct_catalog",
        "src.data_pipeline.repair_corpus_split_governance",
        "src.data_pipeline.repair_zalo_narrator_scaffold",
    }

    assert classified == data_pipeline_modules
    assert classes["migrations"] == preserved_repairs | {migration_catalog}
    assert not any(
        target in classes["migrations"]
        for source in _string_set(policy, "active_modules")
        for target in edges[source]
    )
    assert not any(target == migration_catalog for source in classes["workflows"] for target in edges[source])


def test_only_named_compatibility_adapters_cross_into_history() -> None:
    policy = _policy()
    modules = _module_paths()
    edges = _import_edges(modules)
    active = _string_set(policy, "active_modules")
    adapters = _string_set(policy, "compatibility_adapters")
    historical = _string_set(policy, "historical_modules")
    allowed = {tuple(edge) for edge in policy["allowed_edges"]}
    assert all(len(edge) == 2 for edge in allowed)
    actual = {
        (source, target)
        for source in active | adapters
        for target in edges[source]
        if target in historical
    }
    assert actual == allowed
    assert all(source in adapters and target in historical for source, target in allowed)
    assert not any("reverse" in key.lower() for key in policy)


def test_active_graph_is_acyclic_and_historical_sccs_are_exact() -> None:
    policy = _policy()
    modules = _module_paths()
    edges = _import_edges(modules)
    active = _string_set(policy, "active_modules")
    historical = _string_set(policy, "historical_modules")
    expected = {tuple(sorted(component)) for component in policy["historical_sccs"]}
    assert _strong_components(active, edges) == set()
    assert _strong_components(set(modules), edges) == expected
    assert all(set(component) <= historical for component in expected)


def test_historical_closure_cannot_reach_active_modeling() -> None:
    policy = _policy()
    modules = _module_paths()
    edges = _import_edges(modules)
    historical = _string_set(policy, "historical_modules")
    forbidden_prefixes = tuple(policy["forbidden_historical_targets"])
    assert forbidden_prefixes == ACTIVE_TARGET_PREFIXES
    targets = {
        module
        for module in modules
        if module == "src.artifacts"
        or module.startswith("src.artifacts.")
        or module == "src.modeling"
        or module.startswith("src.modeling.")
    }
    for source in sorted(historical):
        path = _path_to_target(source, edges, targets)
        assert path is None, " -> ".join(path or ())


def test_runtime_import_does_not_initialize_training_package() -> None:
    script = (
        "import sys; import src.runtime.service; "
        "assert 'src.modeling.training' not in sys.modules"
    )
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr


def test_training_command_uses_the_neutral_service_bridge() -> None:
    source = ADAPTATION_COMMANDS.read_text(encoding="utf-8")
    tree = ast.parse(source)
    wrappers = {
        node.name: ast.get_source_segment(source, node) or ""
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name in {"build_training_config", "run_training"}
    }
    assert set(wrappers) == {"build_training_config", "run_training"}
    for wrapper in wrappers.values():
        assert (
            "from src.modeling.training import TrainingError, qwen_training_service"
            in wrapper
        )
        assert "src.model_adaptation.training" not in wrapper
        assert "qwen_training_service()" in wrapper
