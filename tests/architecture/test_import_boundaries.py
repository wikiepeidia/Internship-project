"""Static closed-graph policy for active modeling and historical compatibility."""

from __future__ import annotations

import ast
from collections import deque
import json
from pathlib import Path
from typing import Any, Mapping


REPO_ROOT = Path(__file__).parents[2]
SOURCE_ROOT = REPO_ROOT / "src"
POLICY_PATH = REPO_ROOT / "architecture/module-boundaries.json"
PHASE40_INDEX = REPO_ROOT / "src/model_adaptation/legacy/phase40/__init__.py"
PHASE41_INDEX = REPO_ROOT / "src/model_adaptation/legacy/phase41/__init__.py"
ADAPTATION_COMMANDS = REPO_ROOT / "src/model_adaptation/commands/adaptation.py"
ACTIVE_TARGET_PREFIXES = ("src.artifacts", "src.modeling")
POLICY_FIELDS = {
    "active_modules",
    "allowed_edges",
    "compatibility_adapters",
    "forbidden_historical_targets",
    "historical_modules",
    "historical_sccs",
    "ownership_indexes",
    "schema_version",
}


def _module_name(path: Path) -> str:
    parts = list(path.relative_to(REPO_ROOT).with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _module_paths() -> dict[str, Path]:
    return {_module_name(path): path for path in SOURCE_ROOT.rglob("*.py")}


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
                edges[source].update(
                    alias.name for alias in node.names if alias.name in modules
                )
            elif isinstance(node, ast.ImportFrom):
                base = _resolve_from(source, path, node)
                if base in modules:
                    edges[source].add(base)
                edges[source].update(
                    candidate
                    for alias in node.names
                    if (candidate := f"{base}.{alias.name}") in modules
                )
    return edges


def _policy() -> dict[str, Any]:
    payload = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    assert set(payload) == POLICY_FIELDS
    assert payload["schema_version"] == "module-boundaries-v1"
    return payload


def _string_set(policy: Mapping[str, Any], field: str) -> set[str]:
    values = policy[field]
    assert isinstance(values, list)
    assert all(isinstance(value, str) and value for value in values)
    assert len(values) == len(set(values))
    return set(values)


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
    relevant = {
        module
        for module in modules
        if module == "src.artifacts"
        or module.startswith(("src.runtime", "src.core", "src.modeling"))
        or module.startswith("src.model_adaptation")
    }
    assert relevant == active | adapters | historical | index_modules
    assert set(_owned_modules(PHASE40_INDEX)) | set(
        _owned_modules(PHASE41_INDEX)
    ) == historical
    assert not any("phase40" in name.lower() or "phase41" in name.lower() for name in active)


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
        assert "from src.modeling.training import qwen_training_service" in wrapper
        assert "src.model_adaptation.training" not in wrapper
        assert "qwen_training_service()" in wrapper
