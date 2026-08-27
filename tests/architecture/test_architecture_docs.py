"""Machine-bind architecture and CLI prose to the checked policy fixtures."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import re
from typing import Any, Mapping

import pytest

from tests.architecture.test_model_cli_contract import _literal_route_rows


REPO_ROOT = Path(__file__).parents[2]
POLICY_PATH = REPO_ROOT / "architecture/module-boundaries.json"
OVERVIEW_PATH = REPO_ROOT / "docs/architecture/overview.md"
CLI_DOCUMENT_PATH = REPO_ROOT / "docs/architecture/cli-contracts.md"
MODEL_FIXTURE_PATH = REPO_ROOT / "tests/architecture/fixtures/model_cli_contract.json"
RUNTIME_FIXTURE_PATH = REPO_ROOT / "tests/architecture/fixtures/runtime_cli_contract.json"
MODEL_ERROR_CLAIM = (
    "handler return preserved; stdout and stderr preserved; caught "
    "RuntimeError/ValueError/FileNotFoundError -> stderr and return 1"
)
SECTION_HEADINGS = (
    "1. Installed application",
    "2. Runtime orchestration",
    "3. Integrity, artifacts, and source archiving",
    "4. Data core",
    "5. External data workflows",
    "6. Migration catalog",
    "7. Modeling services",
    "8. Runtime analyzers",
    "9. Evaluation and evidence",
    "10. Compatibility and provenance",
)
ORDERED_FLOW_NODES = tuple(
    (f"N{number}", heading) for number, heading in enumerate(SECTION_HEADINGS, 1)
)
ORDERED_FLOW_EDGES = tuple(
    (f"N{number}", "-->", f"N{number + 1}") for number in range(1, 10)
)
DATA_FLOW_NODES = (
    ("D1", "External workflows"),
    ("D2", "Data core"),
    ("D3", "Model training port"),
    ("D4", "Versioned artifacts"),
    ("D5", "Model inference port"),
    ("D6", "Runtime service"),
    ("D7", "Installed vnphish CLI"),
    ("D8", "Evaluation port"),
    ("D9", "Read-only evidence"),
    ("D10", "Report handoff"),
    ("DH", "Historical producer closure"),
)
DATA_FLOW_EDGES = (
    ("D1", "-->", "D2"),
    ("D2", "-->", "D3"),
    ("D3", "-->", "D4"),
    ("D4", "-->", "D5"),
    ("D5", "-->", "D6"),
    ("D6", "-->", "D7"),
    ("D4", "-->", "D8"),
    ("D8", "-->", "D9"),
    ("DH", "-.->", "D9"),
    ("D9", "-->", "D10"),
)
DEPENDENCY_FLOW_NODES = (
    ("A", "Active domain modules"),
    ("C", "Compatibility adapters"),
    ("H", "Historical implementations"),
)
DEPENDENCY_FLOW_EDGES = (("C", "-->", "H"),)


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _marked_block(document: str, name: str) -> str:
    start = f"<!-- {name}:start -->"
    end = f"<!-- {name}:end -->"
    assert document.count(start) == document.count(end) == 1
    return document.split(start, 1)[1].split(end, 1)[0]


def _table_rows(document: str, name: str, width: int) -> list[tuple[str, ...]]:
    lines = [line.strip() for line in _marked_block(document, name).splitlines()]
    rows = [line for line in lines if line.startswith("|") and line.endswith("|")]
    assert len(rows) >= 2
    parsed = [tuple(cell.strip() for cell in row.strip("|").split("|")) for row in rows]
    assert all(len(row) == width for row in parsed)
    assert all(set(cell) <= {"-", ":", " "} for cell in parsed[1])
    return parsed[2:]


def _unquote(value: str) -> str:
    assert value.startswith("`") and value.endswith("`")
    return value[1:-1]


def _mermaid_graph(document: str, name: str) -> tuple[dict[str, str], set[tuple[str, str]]]:
    block = _marked_block(document, name)
    nodes: dict[str, str] = {}
    edges: set[tuple[str, str]] = set()
    for raw in block.splitlines():
        line = raw.strip()
        node_match = re.fullmatch(r'([A-Za-z][A-Za-z0-9]*)\["([^"]+)"\]', line)
        if node_match:
            node_id, label = node_match.groups()
            assert node_id not in nodes
            nodes[node_id] = label
        edge_match = re.fullmatch(
            r"([A-Za-z][A-Za-z0-9]*)\s+(-+>|-\.->)\s+([A-Za-z][A-Za-z0-9]*)",
            line,
        )
        if edge_match:
            source, _, target = edge_match.groups()
            edges.add((source, target))
    assert set().union(*(set(edge) for edge in edges)) <= set(nodes)
    return nodes, edges


def _policy_groups(policy: Mapping[str, Any]) -> list[tuple[str, list[str]]]:
    data = policy["data_modules"]
    assert isinstance(data, dict) and data
    groups: list[tuple[str, list[str]]] = [
        ("active", list(policy["active_modules"])),
        ("compatibility_adapters", list(policy["compatibility_adapters"])),
        ("historical", list(policy["historical_modules"])),
    ]
    groups.extend((f"data.{name}", list(data[name])) for name in sorted(data))
    groups.append(("ownership_indexes", list(policy["ownership_indexes"].values())))
    return groups


def _render_mermaid(
    nodes: tuple[tuple[str, str], ...],
    edges: tuple[tuple[str, str, str], ...],
) -> str:
    rows = ["```mermaid", "flowchart LR"]
    rows.extend(f'  {node_id}["{label}"]' for node_id, label in nodes)
    rows.extend(f"  {source} {arrow} {target}" for source, arrow, target in edges)
    rows.append("```")
    return "\n".join(rows)


def _render_policy_groups(policy: Mapping[str, Any]) -> str:
    static = policy["static_policy"]
    rows = ["| Policy group | Modules |", "| --- | --- |"]
    rows.extend(
        f"| `{group}` | " + "<br>".join(f"`{module}`" for module in modules) + " |"
        for group, modules in _policy_groups(policy)
    )
    rows.extend(
        [
            "",
            "#### Tool inventory",
            "",
            "| Path | Lifecycle | Language | Kind | Language scope | Imports | Routes |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for tool in static["tools"]:
        imports = "<br>".join(f"`{value}`" for value in tool["imports"]) or "—"
        routes = "<br>".join(
            "`" + " ".join(route) + "`" for route in tool["routes"]
        ) or "—"
        rows.append(
            f"| `{tool['path']}` | `{tool['lifecycle']}` | `{tool['language']}` | "
            f"`{tool['kind']}` | `{tool['phase_language']}` | {imports} | {routes} |"
        )
    rows.extend(
        [
            "",
            "#### Static line budgets",
            "",
            "| Budget | Maximum physical or AST lines |",
            "| --- | ---: |",
        ]
    )
    rows.extend(
        f"| `{name}` | {limit} |"
        for name, limit in static["line_limits"].items()
    )
    rows.extend(
        [
            "",
            "#### Budgeted code",
            "",
            "| Kind | Path |",
            "| --- | --- |",
        ]
    )
    rows.extend(
        f"| `module` | `{module}` |" for module in static["budgeted_modules"]
    )
    rows.extend(
        f"| `tool` | `{path}` |" for path in static["budgeted_tools"]
    )
    rows.extend(
        [
            "",
            "#### Existing budget debt",
            "",
            "| Path | Symbol | Measured lines | Owner | Reason |",
            "| --- | --- | ---: | --- | --- |",
        ]
    )
    rows.extend(
        f"| `{item['path']}` | `{item['symbol']}` | {item['measured_lines']} | "
        f"`{item['owner']}` | {item['reason']} |"
        for item in static["existing_budget_debt"]
    )
    return "\n".join(rows)


def _render_policy_edges(policy: Mapping[str, Any]) -> str:
    static = policy["static_policy"]
    rows = [
        "| Relation | Source | Target |",
        "| --- | --- | --- |",
    ]
    rows.extend(
        f"| `active import` | `{source}` | `{target}` |"
        for source, target in static["active_edges"]
    )
    rows.extend(
        f"| `active tool import` | `{source}` | `{target}` |"
        for source, target in static["active_tool_edges"]
    )
    rows.extend(
        f"| `compatibility to history` | `{source}` | `{target}` |"
        for source, target in policy["allowed_edges"]
    )
    return "\n".join(rows)


def _render_historical_sccs(policy: Mapping[str, Any]) -> str:
    rows = ["| Historical SCC members |", "| --- |"]
    rows.extend(
        "| " + "<br>".join(f"`{module}`" for module in component) + " |"
        for component in policy["historical_sccs"]
    )
    return "\n".join(rows)


def render_overview_blocks(policy: Mapping[str, Any]) -> dict[str, str]:
    """Render every generated overview block from the machine policy."""

    return {
        "ordered-flow": _render_mermaid(ORDERED_FLOW_NODES, ORDERED_FLOW_EDGES),
        "data-flow": _render_mermaid(DATA_FLOW_NODES, DATA_FLOW_EDGES),
        "dependency-flow": _render_mermaid(
            DEPENDENCY_FLOW_NODES, DEPENDENCY_FLOW_EDGES
        ),
        "policy-groups": _render_policy_groups(policy),
        "policy-edges": _render_policy_edges(policy),
        "historical-sccs": _render_historical_sccs(policy),
    }


def _assert_exact_generated_block(document: str, name: str, expected: str) -> None:
    assert _marked_block(document, name) == f"\n{expected}\n"


def _validate_overview(document: str, policy: Mapping[str, Any]) -> None:
    headings = re.findall(r"^## (.+)$", document, flags=re.MULTILINE)
    assert tuple(headings) == SECTION_HEADINGS
    rendered = render_overview_blocks(policy)
    for name, expected in rendered.items():
        _assert_exact_generated_block(document, name, expected)

    active = set(policy["active_modules"])
    active_edges = [tuple(edge) for edge in policy["static_policy"]["active_edges"]]
    assert active_edges == sorted(set(active_edges))
    assert all(set(edge) <= active for edge in active_edges)
    allowed = [tuple(edge) for edge in policy["allowed_edges"]]
    assert allowed == sorted(set(allowed))
    assert allowed
    assert all(edge[0] in policy["compatibility_adapters"] for edge in allowed)
    assert all(edge[1] in policy["historical_modules"] for edge in allowed)
    tools = policy["static_policy"]["tools"]
    assert len(tools) == 11 and len({tool["path"] for tool in tools}) == 11
    tool_paths = {tool["path"] for tool in tools}
    assert all(
        source in tool_paths and target in active
        for source, target in policy["static_policy"]["active_tool_edges"]
    )
    assert len(policy["historical_sccs"]) == 4
    assert {
        "src.config",
        "src.config.settings",
        "src.source_archiving",
        "src.source_archiving.contracts",
        "src.source_archiving.filesystem",
        "src.source_archiving.service",
    } <= active
    assert [
        "scripts/archive_phase41_source_closure.py",
        "src.source_archiving",
    ] in policy["static_policy"]["active_tool_edges"]
    assert [
        "src.source_archiving.filesystem",
        "src.core_binding",
    ] in policy["static_policy"]["active_edges"]
    assert [
        "src.source_archiving.service",
        "src.source_archiving.filesystem",
    ] in policy["static_policy"]["active_edges"]

    dependency_nodes, dependency_edges = _mermaid_graph(document, "dependency-flow")
    assert dependency_nodes == dict(DEPENDENCY_FLOW_NODES)
    assert dependency_edges == {("C", "H")}
    ordered_nodes, ordered_edges = _mermaid_graph(document, "ordered-flow")
    assert ordered_nodes == dict(ORDERED_FLOW_NODES)
    assert ordered_edges == {
        (source, target) for source, _arrow, target in ORDERED_FLOW_EDGES
    }
    data_nodes, data_edges = _mermaid_graph(document, "data-flow")
    assert data_nodes == dict(DATA_FLOW_NODES)
    assert data_edges == {
        (source, target) for source, _arrow, target in DATA_FLOW_EDGES
    }

    assert "Historical phase-numbered names are compatibility/provenance labels only" in document
    assert "does not claim that the refactored code produced frozen metrics" in document
    assert "archive compatibility facade -> `src.source_archiving` -> `src.source_archiving.service`" in document


def _runtime_rows(fixture: Mapping[str, Any]) -> list[tuple[str, str, str, str, str]]:
    results = {
        row["command"]: row
        for row in fixture["main_contract"]["installed_command_handler_doubles"]
    }
    rows: list[tuple[str, str, str, str, str]] = []
    for command_row in fixture["parser"]["subcommands"]:
        command = command_row["command"]
        parser = command_row["parser"]
        options = [
            action["option_strings"][0]
            for action in parser["actions"]
            if action["option_strings"] and action["dest"] != "help"
        ]
        parser_fact = "flags: " + (", ".join(options) if options else "none")
        assert command in results
        result = results[command]
        assert result["stdout"] and result["stderr"]
        claim = f"fixture return {result['return_value']}; stdout and stderr preserved"
        rows.append(
            (
                command,
                "installed",
                parser_fact,
                parser["defaults"]["handler"],
                claim,
            )
        )
    return rows


def _model_rows(fixture: Mapping[str, Any]) -> list[tuple[str, str, str, str, str]]:
    routes = _literal_route_rows()
    caught = fixture["main_contract"]["caught_exceptions"]
    assert [row["caught_exception"] for row in caught] == [
        "RuntimeError",
        "ValueError",
        "FileNotFoundError",
    ]
    assert all(row["return_value"] == 1 and row["stderr"] for row in caught)
    rows: list[tuple[str, str, str, str, str]] = []
    for command_row in fixture["parser"]["subcommands"]:
        command = command_row["command"]
        if command in {"pilot", "train", "convert", "doctor"}:
            group = "adaptation"
        elif command.startswith("phase40-"):
            group = "phase40 compatibility"
        elif command.startswith("phase41-"):
            group = "phase41 compatibility"
        else:  # pragma: no cover - exact fixtures make this a hard failure
            raise AssertionError(command)
        parser_fact = (
            "required --adaptation-mode (preserved compatibility quirk)"
            if command == "doctor"
            else "frozen argparse fixture"
        )
        module, symbol = routes[command]
        rows.append(
            (command, group, parser_fact, f"{module}:{symbol}", MODEL_ERROR_CLAIM)
        )
    return rows


def _validate_cli_document(
    document: str,
    model_fixture: Mapping[str, Any],
    runtime_fixture: Mapping[str, Any],
) -> None:
    rows = [tuple(_unquote(cell) for cell in row) for row in _table_rows(document, "cli-contracts", 5)]
    expected = _runtime_rows(runtime_fixture) + _model_rows(model_fixture)
    assert rows == expected
    assert len(rows) == 26
    assert sum(row[1] == "installed" for row in rows) == 3
    assert sum(row[1] == "adaptation" for row in rows) == 4
    assert sum(row[1] == "phase40 compatibility" for row in rows) == 12
    assert sum(row[1] == "phase41 compatibility" for row in rows) == 7
    assert "vnphish = src.runtime.cli:main" in document
    assert "Compatibility command names are retained for evidence and scripts; they are not the forward domain model." in document


def test_overview_matches_module_boundaries() -> None:
    _validate_overview(
        OVERVIEW_PATH.read_text(encoding="utf-8"),
        _load_json(POLICY_PATH),
    )


def test_cli_document_matches_contract_fixtures() -> None:
    _validate_cli_document(
        CLI_DOCUMENT_PATH.read_text(encoding="utf-8"),
        _load_json(MODEL_FIXTURE_PATH),
        _load_json(RUNTIME_FIXTURE_PATH),
    )


def test_overview_validator_rejects_policy_or_document_drift() -> None:
    document = OVERVIEW_PATH.read_text(encoding="utf-8")
    policy = _load_json(POLICY_PATH)
    mutated_policy = deepcopy(policy)
    mutated_policy["active_modules"].append("src.unreviewed.auto_admitted")
    with pytest.raises(AssertionError):
        _validate_overview(document, mutated_policy)

    extra_edge = document.replace(
        "<!-- policy-edges:end -->",
        "| `src.runtime` | `src.model_adaptation.training` |\n<!-- policy-edges:end -->",
    )
    with pytest.raises(AssertionError):
        _validate_overview(extra_edge, policy)

    extra_node = document.replace(
        "<!-- ordered-flow:end -->",
        '  NX["Undocumented node"]\n<!-- ordered-flow:end -->',
    )
    with pytest.raises(AssertionError):
        _validate_overview(extra_node, policy)

    policy_mutations: list[dict[str, Any]] = []

    new_data_group = deepcopy(policy)
    new_data_group["data_modules"]["unreviewed"] = ["src.unreviewed.module"]
    policy_mutations.append(new_data_group)

    reordered_module = deepcopy(policy)
    reordered_module["active_modules"][0:2] = reversed(
        reordered_module["active_modules"][0:2]
    )
    policy_mutations.append(reordered_module)

    reordered_edge = deepcopy(policy)
    reordered_edge["allowed_edges"][0:2] = reversed(
        reordered_edge["allowed_edges"][0:2]
    )
    policy_mutations.append(reordered_edge)

    reordered_scc = deepcopy(policy)
    reordered_scc["historical_sccs"][0][0:2] = reversed(
        reordered_scc["historical_sccs"][0][0:2]
    )
    policy_mutations.append(reordered_scc)

    duplicate_active_edge = deepcopy(policy)
    duplicate_active_edge["static_policy"]["active_edges"].append(
        deepcopy(duplicate_active_edge["static_policy"]["active_edges"][0])
    )
    policy_mutations.append(duplicate_active_edge)

    endpoint_misclassified = deepcopy(policy)
    endpoint_misclassified["allowed_edges"][0][1] = endpoint_misclassified[
        "active_modules"
    ][0]
    policy_mutations.append(endpoint_misclassified)

    for mutation in policy_mutations:
        with pytest.raises(AssertionError):
            _validate_overview(document, mutation)

    duplicate_mermaid_edge = document.replace(
        "  D1 --> D2\n",
        "  D1 --> D2\n  D1 --> D2\n",
        1,
    )
    with pytest.raises(AssertionError):
        _validate_overview(duplicate_mermaid_edge, policy)

    missing_mermaid_edge = document.replace("  D1 --> D2\n", "", 1)
    with pytest.raises(AssertionError):
        _validate_overview(missing_mermaid_edge, policy)

    reversed_mermaid_edge = document.replace("  D1 --> D2", "  D2 --> D1", 1)
    with pytest.raises(AssertionError):
        _validate_overview(reversed_mermaid_edge, policy)

    nested_marker = document.replace(
        "<!-- policy-groups:start -->",
        "<!-- policy-groups:start -->\n<!-- policy-groups:start -->",
        1,
    )
    with pytest.raises(AssertionError):
        _validate_overview(nested_marker, policy)

    renamed_heading = document.replace(
        "## 1. Installed application",
        "## 1. Renamed application",
        1,
    )
    with pytest.raises(AssertionError):
        _validate_overview(renamed_heading, policy)

    for marker_name in render_overview_blocks(policy):
        injected_prose = document.replace(
            f"<!-- {marker_name}:start -->",
            f"<!-- {marker_name}:start -->\nPhase 91 narrative bypass",
            1,
        )
        with pytest.raises(AssertionError):
            _validate_overview(injected_prose, policy)


def test_cli_validator_rejects_fixture_command_or_behavior_drift() -> None:
    document = CLI_DOCUMENT_PATH.read_text(encoding="utf-8")
    model_fixture = _load_json(MODEL_FIXTURE_PATH)
    runtime_fixture = _load_json(RUNTIME_FIXTURE_PATH)
    mutated_fixture = deepcopy(runtime_fixture)
    mutated_fixture["parser"]["subcommands"].append(
        deepcopy(mutated_fixture["parser"]["subcommands"][0])
    )
    mutated_fixture["parser"]["subcommands"][-1]["command"] = "undocumented"
    with pytest.raises(AssertionError):
        _validate_cli_document(document, model_fixture, mutated_fixture)

    extra_command = document.replace(
        "<!-- cli-contracts:end -->",
        "| `invented` | `installed` | `flags: none` | `src.runtime.cli:invented` | `unsupported` |\n<!-- cli-contracts:end -->",
    )
    with pytest.raises(AssertionError):
        _validate_cli_document(extra_command, model_fixture, runtime_fixture)

    unsupported_claim = document.replace(
        "`fixture return 0; stdout and stderr preserved`",
        "`fixture return 0; always succeeds`",
        1,
    )
    with pytest.raises(AssertionError):
        _validate_cli_document(unsupported_claim, model_fixture, runtime_fixture)
