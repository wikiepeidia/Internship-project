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
ORDERED_FLOW_NODES = {
    "N1": "1. Installed application",
    "N2": "2. Runtime orchestration",
    "N3": "3. Integrity and artifacts",
    "N4": "4. Data core",
    "N5": "5. External data workflows",
    "N6": "6. Migration catalog",
    "N7": "7. Modeling services",
    "N8": "8. Runtime analyzers",
    "N9": "9. Evaluation and evidence",
    "N10": "10. Compatibility and provenance",
}
ORDERED_FLOW_EDGES = {
    (f"N{number}", f"N{number + 1}") for number in range(1, 10)
}
DATA_FLOW_NODES = {
    "D1": "External workflows",
    "D2": "Data core",
    "D3": "Model training port",
    "D4": "Versioned artifacts",
    "D5": "Model inference port",
    "D6": "Runtime service",
    "D7": "Installed vnphish CLI",
    "D8": "Evaluation port",
    "D9": "Read-only evidence",
    "D10": "Report handoff",
    "DH": "Historical producer closure",
}
DATA_FLOW_EDGES = {
    ("D1", "D2"),
    ("D2", "D3"),
    ("D3", "D4"),
    ("D4", "D5"),
    ("D5", "D6"),
    ("D6", "D7"),
    ("D4", "D8"),
    ("D8", "D9"),
    ("DH", "D9"),
    ("D9", "D10"),
}


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


def _expected_policy_groups(policy: Mapping[str, Any]) -> dict[str, set[str]]:
    data = policy["data_modules"]
    return {
        "active": set(policy["active_modules"]),
        "compatibility_adapters": set(policy["compatibility_adapters"]),
        "historical": set(policy["historical_modules"]),
        "data.core": set(data["core"]),
        "data.compatibility": set(data["compatibility"]),
        "data.workflows": set(data["workflows"]),
        "data.migrations": set(data["migrations"]),
        "ownership_indexes": set(policy["ownership_indexes"].values()),
    }


def _validate_overview(document: str, policy: Mapping[str, Any]) -> None:
    headings = re.findall(r"^## ([0-9]+)\. ", document, flags=re.MULTILINE)
    assert headings == [str(number) for number in range(1, 11)]
    group_rows = _table_rows(document, "policy-groups", 2)
    groups = {
        _unquote(group): {
            _unquote(module)
            for module in modules.split("<br>")
            if module
        }
        for group, modules in group_rows
    }
    assert groups == _expected_policy_groups(policy)

    edge_rows = _table_rows(document, "policy-edges", 2)
    edges = [(_unquote(source), _unquote(target)) for source, target in edge_rows]
    assert edges == [tuple(edge) for edge in policy["allowed_edges"]]

    scc_rows = _table_rows(document, "historical-sccs", 1)
    sccs = {
        tuple(sorted(_unquote(module) for module in row[0].split("<br>")))
        for row in scc_rows
    }
    assert sccs == {
        tuple(sorted(component)) for component in policy["historical_sccs"]
    }

    dependency_nodes, dependency_edges = _mermaid_graph(document, "dependency-flow")
    assert dependency_nodes == {
        "A": "Active domain modules",
        "C": "Compatibility adapters",
        "H": "Historical implementations",
    }
    allowed = [tuple(edge) for edge in policy["allowed_edges"]]
    assert allowed
    assert all(edge[0] in policy["compatibility_adapters"] for edge in allowed)
    assert all(edge[1] in policy["historical_modules"] for edge in allowed)
    assert dependency_edges == {("C", "H")}

    ordered_nodes, ordered_edges = _mermaid_graph(document, "ordered-flow")
    assert ordered_nodes == ORDERED_FLOW_NODES
    assert ordered_edges == ORDERED_FLOW_EDGES
    data_nodes, data_edges = _mermaid_graph(document, "data-flow")
    assert data_nodes == DATA_FLOW_NODES
    assert data_edges == DATA_FLOW_EDGES

    assert "Historical phase-numbered names are compatibility/provenance labels only" in document
    assert "does not claim that the refactored code produced frozen metrics" in document


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
