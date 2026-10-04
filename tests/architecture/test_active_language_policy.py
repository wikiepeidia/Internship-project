"""Import-free language and prose-preservation gates for active repository text."""

from __future__ import annotations

import ast
import copy
import glob
import hashlib
import importlib
import importlib.abc
import json
from pathlib import Path
import re
import sys
from typing import Any, Iterator

import pytest

from tests.architecture.json_contract import load_strict_json


REPO_ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = REPO_ROOT / "architecture" / "module-boundaries.json"
ACTIVE_TEXT_FIXTURE_PATH = (
    REPO_ROOT / "tests" / "architecture" / "fixtures" / "active_text_contract.json"
)
RUNTIME_PROSE_FIXTURE_PATH = (
    REPO_ROOT / "tests" / "architecture" / "fixtures" / "runtime_prose_contract.json"
)
MODEL_CLI_FIXTURE_PATH = (
    REPO_ROOT / "tests" / "architecture" / "fixtures" / "model_cli_contract.json"
)
RUNTIME_CLI_FIXTURE_PATH = (
    REPO_ROOT / "tests" / "architecture" / "fixtures" / "runtime_cli_contract.json"
)

_PHASE_PATTERN = re.compile(
    r"phase[\s_\-\u00a0\u2010-\u2015\u2212]*[0-9]+",
    re.IGNORECASE,
)
_LITERAL_BOUNDARY_CHARS = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_./\\:-"
)
_FROZEN_OWNER_REFERENCE_CONTEXTS = {
    "src/source_archiving/contracts.py": {
        "SOURCE_PHASE41_EVALUATION": (
            "SOURCE_PHASE41_EVALUATION",
            "_SOURCE_PATHS",
            "_WORKTREE_MISMATCHES",
        ),
    },
    "scripts/archive_phase41_source_closure.py": {
        "SOURCE_PHASE41_EVALUATION": ("SOURCE_PHASE41_EVALUATION",),
    },
}
_BLOCKED_IMPORT_PREFIXES = (
    "anthropic",
    "bitsandbytes",
    "datasets",
    "google.generativeai",
    "llama_cpp",
    "numpy",
    "openai",
    "pandas",
    "peft",
    "sklearn",
    "src",
    "torch",
    "transformers",
)
_PRE_REWRITE_GIT_BINDINGS = {
    "src/runtime/cli.py": ("5ef59ea44d3bfc203d46a343fd8850d1e068a925", "a3d0664caaf5c95e281b1b783809e5875935b23e", "ac11b3d51693c877fee805773bfab78a94c40620f342057e59adc2c990f5353e"),
    "src/runtime/contracts.py": ("5ef59ea44d3bfc203d46a343fd8850d1e068a925", "c5490de3cc1c614d3db3b6d7d73e6f09f8c1a15c", "7311c81086a9d25f5b4aef40392cc5b9e06dbb813cc8cabd1288e69cec435231"),
    "src/runtime/service.py": ("5ef59ea44d3bfc203d46a343fd8850d1e068a925", "c01bc3a24fc23c8d5a9e9a879353bfb7ff80ab8b", "9d679512536383fdc738ccde474dda969dd9c96ca9e7db2bbf47a03008426130"),
    "src/runtime/render.py": ("3596d5b2f2ef7ddd0467390a101f68f513714034", "4866bc3c2ce9a3c94007b45ef8f255f3c1a4587b", "8d9ca46a0ded76c5ac01f90536c6da3af5d3826c51b2bec395821fe22c469a25"),
    "src/runtime/demo.py": ("3596d5b2f2ef7ddd0467390a101f68f513714034", "a5dcc3cf4cf61e37329801cac507c2f603964ef7", "4defe80ccef4c842776ff0d05b60a6ad32dd5dd3bae7b4bbd070666864ebb93a"),
    "src/runtime/doctor.py": ("6d11e1f13fd6d37c8c786bcdf91df533a5b6987c", "318d9420d268f02a55cfd800c94d8439aa3ce2a9", "3834ddd16c881e73c645293768cffc4aca522ee2d524e91d89f0264bae249f4e"),
    "src/runtime/analyzers/accelerated.py": ("7856d7807f153f0342c402521026180dc0cb6dd0", "6e8623a61b5128052f7a12eee8d96b7656266e4f", "66b90eb46e599e7895fe6071cb65fd77e5cd0eb0a18fd6cb50c8f9a6bae15c32"),
    "src/runtime/analyzers/gguf.py": ("7856d7807f153f0342c402521026180dc0cb6dd0", "93e209c7c624e16b8849287366aa2344845a5c9e", "c1078fb6b2ea6a8c74f8bb9f5fb482e7b31d1c5fe97c96af5de0c106b3a8a399"),
    "src/runtime/analyzers/heuristic.py": ("da0874a4237a4753f5a7f5301dbf5072e396399f", "108b8caf5ea2148cf95e3d9c43339c66ab12292d", "69e3e4b291fd7174418338bb53177d177a1b78ecce7946a95efb48a4bb292b9c"),
    "src/runtime/analyzers/rules.py": ("da0874a4237a4753f5a7f5301dbf5072e396399f", "c00e144f9ba25d8032fa2c40569ed2b71b2eb6ca", "5f911a7342305fdbda0c23d5f33c0a7e9978df3ebfb7ec4a9ec1767299e8396d"),
    "src/runtime/analyzers/local_model.py": ("da0874a4237a4753f5a7f5301dbf5072e396399f", "b122677df743328aa37f9f78c40dcf86e3e8dd1d", "f94855a41478ecc48eb8549891b06caacb8a8a3f1ed755760396eec2f6ab9f72"),
    "src/runtime/demo_assets/demo.js": ("6d11e1f13fd6d37c8c786bcdf91df533a5b6987c", "83795ca3bd91aa4dec8db867ef0c55879639a3af", "1cb9a1a447e5badfa2275bacaee36c93b4f3498328f042424d05c600ff4998be"),
}


class _RejectExecutionImports(importlib.abc.MetaPathFinder):
    """Reject executable application, provider, model, and heavy-dependency imports."""

    marker = "phase411-static-language-import-guard-v1"

    def __init__(self) -> None:
        self.attempts: list[str] = []

    def find_spec(
        self,
        fullname: str,
        path: object = None,
        target: object = None,
    ) -> None:
        del path, target
        if any(
            fullname == prefix or fullname.startswith(prefix + ".")
            for prefix in _BLOCKED_IMPORT_PREFIXES
        ):
            self.attempts.append(fullname)
            raise ImportError(f"static language suite blocked executable import: {fullname}")
        return None


@pytest.fixture
def execution_import_guard() -> Iterator[_RejectExecutionImports]:
    guard = _RejectExecutionImports()
    assert not any(finder is guard for finder in sys.meta_path)
    sys.meta_path.insert(0, guard)
    try:
        yield guard
    finally:
        sys.meta_path[:] = [finder for finder in sys.meta_path if finder is not guard]
        assert guard not in sys.meta_path


def _load_json(path: Path) -> dict[str, Any]:
    return load_strict_json(path)


def _policy() -> dict[str, Any]:
    return _load_json(POLICY_PATH)


def _active_text_fixture() -> dict[str, Any]:
    return _load_json(ACTIVE_TEXT_FIXTURE_PATH)


def _runtime_prose_fixture() -> dict[str, Any]:
    return _load_json(RUNTIME_PROSE_FIXTURE_PATH)


def _validate_pre_rewrite_git_bindings(candidate: dict[str, Any]) -> None:
    assert candidate["schema_version"] == "runtime-prose-contract-v2"
    rows = candidate["python_sources"] + candidate["javascript_sources"]
    bindings = {
        row["path"]: (
            row["source_commit"],
            row["git_blob_oid"],
            row["pre_edit_source_sha256"],
        )
        for row in rows
    }
    assert len(bindings) == len(rows) == 12
    assert bindings == _PRE_REWRITE_GIT_BINDINGS
    for commit, blob_oid, source_sha256 in bindings.values():
        assert re.fullmatch(r"[0-9a-f]{40}", commit)
        assert re.fullmatch(r"[0-9a-f]{40}", blob_oid)
        assert re.fullmatch(r"[0-9a-f]{64}", source_sha256)


def _assert_unique(values: list[Any], label: str) -> None:
    serialized = [json.dumps(value, ensure_ascii=False, sort_keys=True) for value in values]
    assert len(serialized) == len(set(serialized)), f"duplicate {label} entry"


def _validate_contract_structure(contract: dict[str, Any]) -> None:
    assert set(contract) == {
        "contract_state",
        "text_assets",
        "binary_assets",
        "active_documents",
        "historical_documents",
        "literal_markers",
        "frozen_literal_owners",
    }
    assert contract["contract_state"] in {"pre_extraction_v1", "post_extraction_v1"}
    for field in (
        "text_assets",
        "binary_assets",
        "active_documents",
        "historical_documents",
    ):
        assert contract[field]
        _assert_unique(contract[field], field)
        assert all(isinstance(path, str) and path for path in contract[field])
        assert all(not glob.has_magic(path) for path in contract[field])

    marker_keys: list[tuple[str, str]] = []
    for row in contract["literal_markers"]:
        assert set(row) == {
            "path",
            "marker_id",
            "start_marker",
            "end_marker",
            "reason",
            "owner",
        }
        assert all(isinstance(value, str) and value for value in row.values())
        assert not glob.has_magic(row["path"])
        assert row["start_marker"] == f"<!-- {row['marker_id']}:start -->"
        assert row["end_marker"] == f"<!-- {row['marker_id']}:end -->"
        assert row["start_marker"] != row["end_marker"]
        marker_keys.append((row["path"], row["marker_id"]))
    assert len(marker_keys) == len(set(marker_keys)), "duplicate path-scoped marker"

    owner_ids: list[str] = []
    owner_keys: list[tuple[str, str, str]] = []
    for row in contract["frozen_literal_owners"]:
        assert set(row) == {
            "id",
            "path",
            "literal",
            "owner_symbol",
            "reason",
            "lifecycle",
        }
        assert all(isinstance(value, str) and value for value in row.values())
        assert not glob.has_magic(row["path"])
        assert row["lifecycle"] in {"active", "compatibility"}
        owner_ids.append(row["id"])
        owner_keys.append((row["path"], row["literal"], row["owner_symbol"]))
    assert len(owner_ids) == len(set(owner_ids)), "duplicate frozen-literal id"
    assert len(owner_keys) == len(set(owner_keys)), "duplicate frozen-literal ownership"


def _exact_literal_spans(text: str, literal: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    for match in re.finditer(re.escape(literal), text):
        before = text[match.start() - 1] if match.start() else ""
        after = text[match.end()] if match.end() < len(text) else ""
        if before in _LITERAL_BOUNDARY_CHARS or after in _LITERAL_BOUNDARY_CHARS:
            continue
        spans.append(match.span())
    return spans


def _marker_spans(
    logical_path: str,
    text: str,
    contract: dict[str, Any],
) -> list[tuple[int, int]]:
    pairs: list[tuple[int, int]] = []
    rows = [row for row in contract["literal_markers"] if row["path"] == logical_path]
    for row in rows:
        start_positions = [
            match.start() for match in re.finditer(re.escape(row["start_marker"]), text)
        ]
        end_positions = [
            match.start() for match in re.finditer(re.escape(row["end_marker"]), text)
        ]
        assert len(start_positions) == 1, f"missing or duplicate start marker: {row['marker_id']}"
        assert len(end_positions) == 1, f"missing or duplicate end marker: {row['marker_id']}"
        start = start_positions[0]
        end = end_positions[0] + len(row["end_marker"])
        assert start < end_positions[0], f"reversed marker pair: {row['marker_id']}"
        pairs.append((start, end))

    ordered = sorted(pairs)
    for previous, current in zip(ordered, ordered[1:]):
        assert previous[1] <= current[0], "nested or overlapping marker regions"
    return ordered


def _assert_exact_marker_block(
    logical_path: str,
    text: str,
    row: dict[str, str],
    expected_body: str,
) -> None:
    assert row["path"] == logical_path
    _marker_spans(logical_path, text, {"literal_markers": [row]})
    expected = f"{row['start_marker']}\n{expected_body}\n{row['end_marker']}"
    start = text.index(row["start_marker"])
    end = text.index(row["end_marker"]) + len(row["end_marker"])
    assert text[start:end] == expected, (
        f"{row['marker_id']} must contain only its exact compatibility command block"
    )


def _marker_row(
    contract: dict[str, Any],
    logical_path: str,
    marker_id: str,
) -> dict[str, str]:
    rows = [
        row
        for row in contract["literal_markers"]
        if row["path"] == logical_path and row["marker_id"] == marker_id
    ]
    assert len(rows) == 1, f"marker must have exactly one owner: {logical_path}:{marker_id}"
    return rows[0]


def _markdown_table_rows(body: str, width: int) -> list[tuple[str, ...]]:
    lines = [line.strip() for line in body.splitlines()]
    raw_rows = [line for line in lines if line.startswith("|") and line.endswith("|")]
    parsed = [tuple(cell.strip() for cell in row.strip("|").split("|")) for row in raw_rows]
    assert len(parsed) >= 2
    assert all(len(row) == width for row in parsed)
    assert all(set(cell) <= {"-", ":", " "} for cell in parsed[1])
    return parsed[2:]


def _marker_body(text: str, row: dict[str, str]) -> str:
    assert text.count(row["start_marker"]) == 1
    assert text.count(row["end_marker"]) == 1
    body = text.split(row["start_marker"], 1)[1].split(row["end_marker"], 1)[0]
    assert body.startswith("\n") and body.endswith("\n")
    return body[1:-1]


def _assert_table_only_marker(text: str, row: dict[str, str], width: int) -> None:
    body = _marker_body(text, row)
    nonempty = [line.strip() for line in body.splitlines() if line.strip()]
    assert nonempty and all(line.startswith("|") and line.endswith("|") for line in nonempty)
    _markdown_table_rows(body, width)


def _expected_policy_groups_body(policy: dict[str, Any]) -> str:
    from tests.architecture.test_architecture_docs import render_overview_blocks

    return render_overview_blocks(policy)["policy-groups"]


def _expected_policy_edges_body(policy: dict[str, Any]) -> str:
    from tests.architecture.test_architecture_docs import render_overview_blocks

    return render_overview_blocks(policy)["policy-edges"]


def _expected_historical_scc_body(policy: dict[str, Any]) -> str:
    from tests.architecture.test_architecture_docs import render_overview_blocks

    return render_overview_blocks(policy)["historical-sccs"]


def _expected_cli_contract_body() -> str:
    runtime_fixture = _load_json(RUNTIME_CLI_FIXTURE_PATH)
    model_fixture = _load_json(MODEL_CLI_FIXTURE_PATH)
    runtime_results = {
        row["command"]: row
        for row in runtime_fixture["main_contract"]["installed_command_handler_doubles"]
    }
    rows = [
        "| Command | Group | Parser fact | Direct or lazy route | Exit/output contract |",
        "| --- | --- | --- | --- | --- |",
    ]
    for command_row in runtime_fixture["parser"]["subcommands"]:
        command = command_row["command"]
        parser = command_row["parser"]
        options = [
            action["option_strings"][0]
            for action in parser["actions"]
            if action["option_strings"] and action["dest"] != "help"
        ]
        parser_fact = "flags: " + (", ".join(options) if options else "none")
        result = runtime_results[command]
        exit_contract = (
            f"fixture return {result['return_value']}; stdout and stderr preserved"
        )
        rows.append(
            f"| `{command}` | `installed` | `{parser_fact}` | "
            f"`{parser['defaults']['handler']}` | `{exit_contract}` |"
        )

    model_exit_contract = (
        "handler return preserved; stdout and stderr preserved; caught "
        "RuntimeError/ValueError/FileNotFoundError -> stderr and return 1"
    )
    for command_row in model_fixture["parser"]["subcommands"]:
        command = command_row["command"]
        if command in {"pilot", "train", "convert", "doctor"}:
            group = "adaptation"
            route_module = "src.model_adaptation.commands.adaptation"
        elif command.startswith("phase40-"):
            group = "phase40 compatibility"
            route_module = "src.model_adaptation.commands.legacy_phase40"
        else:
            assert command.startswith("phase41-")
            group = "phase41 compatibility"
            route_module = "src.model_adaptation.commands.legacy_phase41"
        parser_fact = (
            "required --adaptation-mode (preserved compatibility quirk)"
            if command == "doctor"
            else "frozen argparse fixture"
        )
        route = f"{route_module}:handle_{command.replace('-', '_')}"
        rows.append(
            f"| `{command}` | `{group}` | `{parser_fact}` | `{route}` | "
            f"`{model_exit_contract}` |"
        )
    return "\n".join(rows)


def _assignment_owns_name(node: ast.AST, name: str) -> bool:
    targets: list[ast.expr] = []
    if isinstance(node, ast.Assign):
        targets = list(node.targets)
    elif isinstance(node, ast.AnnAssign):
        targets = [node.target]
    return any(isinstance(target, ast.Name) and target.id == name for target in targets)


def _owner_ast_node(tree: ast.Module, owner_symbol: str) -> ast.AST | None:
    if owner_symbol == "<module>.__doc__":
        return _docstring_expression(tree.body, "module")

    parts = owner_symbol.split(".")
    if len(parts) == 2:
        class_name, member_name = parts
        classes = [
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == class_name
        ]
        if len(classes) != 1:
            return None
        members = [
            node
            for node in classes[0].body
            if (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                and node.name == member_name
            )
            or _assignment_owns_name(node, member_name)
        ]
        return members[0] if len(members) == 1 else None

    if len(parts) != 1:
        return None
    name = parts[0]
    owners = [
        node
        for node in tree.body
        if (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
            and node.name == name
        )
        or _assignment_owns_name(node, name)
    ]
    return owners[0] if len(owners) == 1 else None


def _source_offset(lines: list[str], line_number: int, byte_column: int) -> int:
    prefix = lines[line_number - 1].encode("utf-8")[:byte_column].decode("utf-8")
    return sum(len(line) for line in lines[: line_number - 1]) + len(prefix)


def _ast_node_span(text: str, node: ast.AST) -> tuple[int, int]:
    assert hasattr(node, "lineno") and hasattr(node, "end_lineno")
    lines = text.splitlines(keepends=True)
    return (
        _source_offset(lines, node.lineno, node.col_offset),
        _source_offset(lines, node.end_lineno, node.end_col_offset),
    )


def _python_owner_reference_spans(
    logical_path: str,
    text: str,
    contract: dict[str, Any],
) -> list[tuple[int, int]]:
    references = _FROZEN_OWNER_REFERENCE_CONTEXTS.get(logical_path, {})
    if not references:
        return []
    declared_symbols = {
        row["owner_symbol"] for row in contract["frozen_literal_owners"]
    }
    assert set(references) <= declared_symbols
    try:
        tree = ast.parse(text, filename=logical_path)
    except SyntaxError:
        return []

    spans: list[tuple[int, int]] = []
    for identifier, owner_symbols in references.items():
        identifier_pattern = re.compile(
            rf"(?<![A-Za-z0-9_]){re.escape(identifier)}(?![A-Za-z0-9_])"
        )
        occurrences = [match.span() for match in identifier_pattern.finditer(text)]
        for owner_symbol in owner_symbols:
            owner = _owner_ast_node(tree, owner_symbol)
            if owner is None:
                continue
            owner_start, owner_end = _ast_node_span(text, owner)
            spans.extend(
                (start, end)
                for start, end in occurrences
                if owner_start <= start and end <= owner_end
            )
    return spans


def _literal_exception_spans(
    logical_path: str,
    text: str,
    contract: dict[str, Any],
) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    for row in contract["frozen_literal_owners"]:
        if row["path"] != logical_path:
            continue
        literal_spans = _exact_literal_spans(text, row["literal"])
        if not logical_path.endswith(".py"):
            spans.extend(literal_spans)
            continue
        try:
            tree = ast.parse(text, filename=logical_path)
        except SyntaxError:
            continue
        owner = _owner_ast_node(tree, row["owner_symbol"])
        if owner is None:
            continue
        owner_start, owner_end = _ast_node_span(text, owner)
        spans.extend(
            (start, end)
            for start, end in literal_spans
            if owner_start <= start and end <= owner_end
        )
    return spans


def _scan_text(
    logical_path: str,
    text: str,
    contract: dict[str, Any] | None = None,
) -> list[str]:
    active_contract = contract or _active_text_fixture()
    allowed = _marker_spans(logical_path, text, active_contract)
    allowed.extend(_literal_exception_spans(logical_path, text, active_contract))
    allowed.extend(_python_owner_reference_spans(logical_path, text, active_contract))
    violations: list[str] = []
    for match in _PHASE_PATTERN.finditer(text):
        if any(start <= match.start() and match.end() <= end for start, end in allowed):
            continue
        violations.append(
            f"{logical_path}:{text.count(chr(10), 0, match.start()) + 1}:{match.group(0)}"
        )
    return violations


def _scan_file(path: Path, logical_path: str | None = None) -> list[str]:
    return _scan_text(
        logical_path or path.as_posix(),
        path.read_text(encoding="utf-8"),
    )


def _module_source_path(module: str) -> str:
    stem = REPO_ROOT.joinpath(*module.split("."))
    candidates = [stem.with_suffix(".py"), stem / "__init__.py"]
    existing = [candidate for candidate in candidates if candidate.is_file()]
    assert len(existing) == 1, f"module must resolve to exactly one source path: {module}"
    return existing[0].relative_to(REPO_ROOT).as_posix()


def _active_scan_paths(policy: dict[str, Any]) -> list[str]:
    static_policy = policy["static_policy"]
    text_contract = static_policy["active_text_scan"]
    paths = [_module_source_path(module) for module in policy["active_modules"]]
    paths.extend(
        row["path"]
        for row in static_policy["tools"]
        if row["lifecycle"] in {"active", "compatibility"}
    )
    paths.extend(text_contract["text_assets"])
    paths.extend(text_contract["active_documents"])
    _assert_unique(paths, "active scan path")
    return paths


def _validate_exception_ownership(contract: dict[str, Any]) -> None:
    _validate_contract_structure(contract)
    marker_paths = sorted({row["path"] for row in contract["literal_markers"]})
    for logical_path in marker_paths:
        source = (REPO_ROOT / logical_path).read_text(encoding="utf-8")
        declared = [
            row for row in contract["literal_markers"] if row["path"] == logical_path
        ]
        if contract["contract_state"] == "pre_extraction_v1":
            declared = [
                row
                for row in declared
                if row["start_marker"] in source or row["end_marker"] in source
            ]
            if not declared:
                continue
        partial = dict(contract)
        partial["literal_markers"] = declared
        _marker_spans(logical_path, source, partial)
    for row in contract["frozen_literal_owners"]:
        source = (REPO_ROOT / row["path"]).read_text(encoding="utf-8")
        literal_spans = _exact_literal_spans(source, row["literal"])
        single_owner_contract = dict(contract)
        single_owner_contract["frozen_literal_owners"] = [row]
        owned_spans = _literal_exception_spans(
            row["path"], source, single_owner_contract
        )
        assert literal_spans and owned_spans == literal_spans, (
            f"stale or near-match frozen literal: {row['id']}"
        )


def _docstring_expression(body: list[ast.stmt], label: str) -> ast.Expr:
    assert body, f"missing {label} body"
    node = body[0]
    assert isinstance(node, ast.Expr), f"missing {label} docstring expression"
    assert isinstance(node.value, ast.Constant) and isinstance(node.value.value, str), (
        f"missing {label} string docstring"
    )
    return node


def _mask_python_slot(tree: ast.Module, slot: dict[str, str]) -> None:
    replacement = f"<runtime-prose-slot:{slot['id']}>"
    kind = slot["kind"]
    if kind == "module_docstring":
        expression = _docstring_expression(tree.body, "module")
        expression.value.value = replacement
        return
    if kind == "function_docstring":
        matches = [
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == slot["name"]
        ]
        assert len(matches) == 1, f"function prose slot must resolve once: {slot['name']}"
        expression = _docstring_expression(matches[0].body, slot["name"])
        expression.value.value = replacement
        return
    if kind == "assignment_string":
        matches: list[ast.Assign | ast.AnnAssign] = []
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == slot["name"]
                for target in node.targets
            ):
                matches.append(node)
            elif (
                isinstance(node, ast.AnnAssign)
                and isinstance(node.target, ast.Name)
                and node.target.id == slot["name"]
            ):
                matches.append(node)
        assert len(matches) == 1, f"assignment prose slot must resolve once: {slot['name']}"
        value = matches[0].value
        assert isinstance(value, ast.Constant) and isinstance(value.value, str), (
            f"assignment prose slot must be one static string: {slot['name']}"
        )
        value.value = replacement
        return
    raise AssertionError(f"unsupported prose slot kind: {kind}")


def _python_behavior_sha256(path: Path, slots: list[dict[str, str]]) -> str:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=path.as_posix())
    ids = [slot["id"] for slot in slots]
    assert len(ids) == len(set(ids)), f"duplicate prose slot id for {path}"
    for slot in slots:
        _mask_python_slot(tree, slot)
    payload = ast.dump(tree, annotate_fields=True, include_attributes=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _strip_javascript_comments(source: str) -> str:
    output: list[str] = []
    index = 0
    quote = ""
    escaped = False
    while index < len(source):
        current = source[index]
        following = source[index + 1] if index + 1 < len(source) else ""
        if quote:
            output.append(current)
            if escaped:
                escaped = False
            elif current == "\\":
                escaped = True
            elif current == quote:
                quote = ""
            index += 1
            continue
        if current in {"'", '"', "`"}:
            quote = current
            output.append(current)
            index += 1
            continue
        if current == "/" and following == "/":
            index += 2
            while index < len(source) and source[index] not in "\r\n":
                index += 1
            continue
        if current == "/" and following == "*":
            index += 2
            while index < len(source):
                if source[index] == "*" and index + 1 < len(source) and source[index + 1] == "/":
                    index += 2
                    break
                if source[index] in "\r\n":
                    output.append(source[index])
                index += 1
            else:
                raise AssertionError("unterminated JavaScript block comment")
            continue
        output.append(current)
        index += 1
    assert not quote, "unterminated JavaScript string"
    return "".join(output)


def _javascript_behavior_sha256(path: Path) -> str:
    stripped = _strip_javascript_comments(path.read_text(encoding="utf-8"))
    return hashlib.sha256(stripped.encode("utf-8")).hexdigest()


def test_static_language_suite_blocks_execution_imports(
    execution_import_guard: _RejectExecutionImports,
) -> None:
    assert sys.meta_path[0] is execution_import_guard
    probes = (
        "src.__phase411_static_probe__",
        "transformers.__phase411_static_probe__",
        "openai.__phase411_static_probe__",
    )
    assert all(name not in sys.modules for name in probes)
    for name in probes:
        attempt_count = len(execution_import_guard.attempts)
        with pytest.raises(ImportError, match="static language suite blocked executable import"):
            importlib.import_module(name)
        assert len(execution_import_guard.attempts) == attempt_count + 1
        rejected_name = execution_import_guard.attempts[-1]
        assert name == rejected_name or name.startswith(rejected_name + ".")
    assert all(name not in sys.modules for name in execution_import_guard.attempts)


@pytest.mark.parametrize(
    ("suffix", "payload"),
    [
        (".py", '"""Phase 91 module prose."""\n'),
        (".py", 'VALUE = "phase-91 string"\n'),
        (".py", "# phase_91 comment\nVALUE = 1\n"),
        (".bat", "@rem Phase 91 batch text\r\n"),
        (".ps1", "# Phase-91 PowerShell text\n"),
        (".sh", "# phase_91 shell text\n"),
        (".html", "<p>Phase 91 prose</p>"),
        (".html", "<script>const note = 'Phase-91 inline code';</script>"),
        (".css", "/* Phase_91 CSS text */\nbody { color: black; }"),
        (".js", "// Phase 91 JavaScript text\nconst safe = true;"),
        (".md", "## Phase-91 Markdown text\n"),
        (".md", "## Phase\t91 tab-separated text\n"),
        (".md", "## Phase\u00a091 non-breaking-space text\n"),
        (".md", "## Phase\u201391 Unicode-dash text\n"),
        (".md", "## Phase\u221291 Unicode-minus text\n"),
    ],
)
def test_active_text_scanner_rejects_every_supported_source_language(
    tmp_path: Path,
    suffix: str,
    payload: str,
) -> None:
    sample = tmp_path / f"mutation{suffix}"
    sample.write_text(payload, encoding="utf-8")
    violations = _scan_file(sample, f"synthetic/mutation{suffix}")
    assert len(violations) == 1
    assert _PHASE_PATTERN.search(violations[0])


def test_active_text_allowlist_is_exact_and_marker_scoped() -> None:
    policy = _policy()
    fixture = _active_text_fixture()
    policy_contract = policy["static_policy"]["active_text_scan"]
    assert policy_contract == fixture
    _validate_exception_ownership(fixture)

    active_paths = _active_scan_paths(policy)
    assert all((REPO_ROOT / path).is_file() for path in active_paths)
    assert not set(fixture["historical_documents"]) & set(active_paths)
    assert all((REPO_ROOT / path).is_file() for path in fixture["historical_documents"])
    assert all(path.endswith(".woff2") for path in fixture["binary_assets"])
    assert all((REPO_ROOT / path).is_file() for path in fixture["binary_assets"])

    literal = fixture["frozen_literal_owners"][0]
    literal_source = (REPO_ROOT / literal["path"]).read_text(encoding="utf-8")
    assert _scan_text(literal["path"], literal_source, fixture) == []
    moved_literal = literal_source.replace(literal["literal"], "terminal-results-v1", 1)
    moved_literal += f"\nMOVED_LITERAL = {literal['literal']!r}\n"
    assert _scan_text(literal["path"], moved_literal, fixture)
    assert _literal_exception_spans(literal["path"], moved_literal, fixture) == []
    assert _scan_text("synthetic/moved.py", literal["literal"], fixture)
    assert _scan_text(literal["path"], literal["literal"] + "-near-match", fixture)

    marker = next(row for row in fixture["literal_markers"] if row["path"] == "README.md")
    allowed = f"{marker['start_marker']}\nPhase 91\n{marker['end_marker']}"
    assert _scan_text(marker["path"], allowed, fixture) == []
    assert _scan_text(marker["path"], allowed + "\nPhase 92", fixture)
    with pytest.raises(AssertionError, match="missing or duplicate start marker"):
        _scan_text(marker["path"], marker["end_marker"], fixture)
    nested = (
        f"{marker['start_marker']}\n{marker['start_marker']}\nPhase 91\n"
        f"{marker['end_marker']}\n{marker['end_marker']}"
    )
    with pytest.raises(AssertionError, match="missing or duplicate start marker"):
        _scan_text(marker["path"], nested, fixture)

    wildcard = copy.deepcopy(fixture)
    wildcard["literal_markers"][0]["path"] = "docs/**/*.md"
    with pytest.raises(AssertionError):
        _validate_contract_structure(wildcard)
    stale = copy.deepcopy(fixture)
    stale["frozen_literal_owners"][0]["literal"] = "phase999-stale-literal"
    with pytest.raises(AssertionError, match="stale or near-match frozen literal"):
        _validate_exception_ownership(stale)
    moved_owner = copy.deepcopy(fixture)
    moved_owner["frozen_literal_owners"][0]["owner_symbol"] = "MOVED_LITERAL"
    with pytest.raises(AssertionError, match="stale or near-match frozen literal"):
        _validate_exception_ownership(moved_owner)
    duplicate = copy.deepcopy(fixture)
    duplicate["frozen_literal_owners"].append(copy.deepcopy(duplicate["frozen_literal_owners"][0]))
    with pytest.raises(AssertionError, match="duplicate frozen-literal"):
        _validate_contract_structure(duplicate)


def test_runtime_prose_behavior_fingerprints_match_characterization() -> None:
    fixture = _runtime_prose_fixture()
    _validate_pre_rewrite_git_bindings(fixture)
    assert fixture["source_state"] == "pre_domain_prose_rewrite"
    assert len(fixture["python_sources"]) == 11
    assert len(fixture["javascript_sources"]) == 1
    paths = [row["path"] for row in fixture["python_sources"]]
    paths.extend(row["path"] for row in fixture["javascript_sources"])
    _assert_unique(paths, "runtime prose source")

    actual_python = {
        row["path"]: _python_behavior_sha256(REPO_ROOT / row["path"], row["prose_slots"])
        for row in fixture["python_sources"]
    }
    expected_python = {row["path"]: row["masked_ast_sha256"] for row in fixture["python_sources"]}
    assert actual_python == expected_python, json.dumps(actual_python, indent=2, sort_keys=True)

    actual_javascript = {
        row["path"]: _javascript_behavior_sha256(REPO_ROOT / row["path"])
        for row in fixture["javascript_sources"]
    }
    expected_javascript = {
        row["path"]: row["comment_stripped_sha256"]
        for row in fixture["javascript_sources"]
    }
    assert actual_javascript == expected_javascript, json.dumps(
        actual_javascript, indent=2, sort_keys=True
    )

    for field in ("source_commit", "git_blob_oid", "pre_edit_source_sha256"):
        mutant = copy.deepcopy(fixture)
        mutant["python_sources"][0][field] = "0" * (64 if field.endswith("sha256") else 40)
        with pytest.raises(AssertionError):
            _validate_pre_rewrite_git_bindings(mutant)
    duplicate = copy.deepcopy(fixture)
    duplicate["python_sources"].append(copy.deepcopy(duplicate["python_sources"][0]))
    with pytest.raises(AssertionError):
        _validate_pre_rewrite_git_bindings(duplicate)
    for row in fixture["protected_command_literals"]:
        source = (REPO_ROOT / row["path"]).read_text(encoding="utf-8")
        assert source.count(row["literal"]) == row["expected_count"] == 1


def test_active_runtime_entrypoint_language_is_domain_named() -> None:
    paths = (
        "src/runtime/cli.py",
        "src/runtime/contracts.py",
        "src/runtime/service.py",
    )
    violations = [
        violation
        for logical_path in paths
        for violation in _scan_text(
            logical_path,
            (REPO_ROOT / logical_path).read_text(encoding="utf-8"),
        )
    ]
    assert violations == []


def test_active_backend_analyzer_language_is_domain_named() -> None:
    paths = (
        "src/runtime/analyzers/accelerated.py",
        "src/runtime/analyzers/gguf.py",
    )
    violations = [
        violation
        for logical_path in paths
        for violation in _scan_text(
            logical_path,
            (REPO_ROOT / logical_path).read_text(encoding="utf-8"),
        )
    ]
    assert violations == []


def test_active_rule_analyzer_language_is_domain_named() -> None:
    paths = (
        "src/runtime/analyzers/heuristic.py",
        "src/runtime/analyzers/rules.py",
        "src/runtime/analyzers/local_model.py",
    )
    violations = [
        violation
        for logical_path in paths
        for violation in _scan_text(
            logical_path,
            (REPO_ROOT / logical_path).read_text(encoding="utf-8"),
        )
    ]
    assert violations == []


def test_active_runtime_render_and_demo_language_is_domain_named() -> None:
    paths = (
        "src/runtime/render.py",
        "src/runtime/demo.py",
    )
    violations = [
        violation
        for logical_path in paths
        for violation in _scan_text(
            logical_path,
            (REPO_ROOT / logical_path).read_text(encoding="utf-8"),
        )
    ]
    assert violations == []


def test_active_runtime_doctor_and_browser_language_is_domain_named() -> None:
    paths = (
        "src/runtime/doctor.py",
        "src/runtime/demo_assets/demo.js",
    )
    sources = {
        logical_path: (REPO_ROOT / logical_path).read_text(encoding="utf-8")
        for logical_path in paths
    }
    violations = [
        violation
        for logical_path, source in sources.items()
        for violation in _scan_text(logical_path, source)
    ]
    assert violations == []

    legacy_artifact = [
        row
        for row in _active_text_fixture()["frozen_literal_owners"]
        if row["id"] == "legacy-release-artifact-glob"
    ]
    assert legacy_artifact == [
        {
            "id": "legacy-release-artifact-glob",
            "path": "src/runtime/doctor.py",
            "literal": "phase5-release-eval-*.json",
            "owner_symbol": "RELEASE_MANIFEST_PATTERNS",
            "reason": "preserve legacy release-evaluation artifact discovery",
            "lifecycle": "active",
        }
    ]
    assert sources["src/runtime/doctor.py"].count(legacy_artifact[0]["literal"]) == 1


def test_readme_and_user_guide_use_domain_language_and_scoped_cli_markers() -> None:
    fixture = _active_text_fixture()
    assert _policy()["static_policy"]["active_text_scan"] == fixture

    readme_path = "README.md"
    guide_path = "documents/user/USER_GUIDE.md"
    readme = (REPO_ROOT / readme_path).read_text(encoding="utf-8")
    guide = (REPO_ROOT / guide_path).read_text(encoding="utf-8")
    assert _scan_text(readme_path, readme, fixture) == []
    assert _scan_text(guide_path, guide, fixture) == []

    retired_prose = (
        "Phase 2 Local Runtime",
        "Phase 2 adds a stdin-first local runtime",
        "not accepted in Phase 2",
        "Phase 3 Local Model Profiles",
        "Phase 3 adds two explicit local-only model profiles",
        "Phase 6 Local Demo UI",
        "Phase 6 adds a local browser demo",
        "Phase 1 Operator Flow",
        "Phase 1 builds and retains",
        "reproduce Phase 1 outputs",
        "retained Phase 1 dataset target band",
        "# Phase 2 User Guide",
        "The Phase 2 runtime",
        "Supported options in Phase 2",
        "Supported demo options in Phase 6",
    )
    combined_active_prose = f"{readme}\n{guide}"
    assert all(fragment not in combined_active_prose for fragment in retired_prose)

    readme_markers = [
        row for row in fixture["literal_markers"] if row["path"] == readme_path
    ]
    assert readme_markers == [
        {
            "path": "README.md",
            "marker_id": "legacy-readme-data-cli",
            "start_marker": "<!-- legacy-readme-data-cli:start -->",
            "end_marker": "<!-- legacy-readme-data-cli:end -->",
            "reason": "preserve frozen data CLI version-tag examples",
            "owner": "user-data-cli-compatibility",
        }
    ]
    marker = readme_markers[0]
    expected_commands = "\n\n".join(
        (
            "```bash\npython -m src.data_pipeline.cli --seed-input data/raw/seeds-2026-04-24.jsonl --target-count 2500 --version-tag phase1-uat-gap\n```",
            "```bash\npython -m src.data_pipeline.cli --seed-input data/raw/seeds-2026-04-24.jsonl --target-count 3000 --version-tag phase1-uat-gap --bulk-provider auto --max-parallel-batches 2 --resume --generate-only\n```",
            "```bash\npython -m src.data_pipeline.cli --seed-input data/raw/seeds-2026-04-24.jsonl --target-count 50 --version-tag phase1-uat-gap\n```",
            "```bash\npython -m src.data_pipeline.cli --seed-input data/raw/seeds-2026-04-24.jsonl --target-count 3000 --version-tag phase1-uat-gap --bulk-provider auto --max-parallel-batches 2 --generate-only\n```",
            "```bash\npython -m src.data_pipeline.cli --seed-input data/raw/seeds-2026-04-24.jsonl --target-count 3000 --version-tag phase1-uat-gap --bulk-provider auto --max-parallel-batches 2 --resume --generate-only\n```",
            "```bash\npython -m src.data_pipeline.cli --target-count 2500 --version-tag phase1-fresh\n```",
        )
    )
    _assert_exact_marker_block(readme_path, readme, marker, expected_commands)

    local_models_link = "[Local Model Profiles](documents/user/LOCAL_MODELS.md)"
    assert readme.count(local_models_link) == 1
    assert (REPO_ROOT / "documents/user/LOCAL_MODELS.md").is_file()

    moved_token = readme.replace("phase1-fresh", "release-fresh", 1)
    moved_token += "\nCompatibility token: phase1-fresh\n"
    assert _scan_text(readme_path, moved_token, fixture)
    prose_in_marker = readme.replace(
        marker["start_marker"],
        f"{marker['start_marker']}\nPhase 91 narrative bypass",
        1,
    )
    with pytest.raises(AssertionError, match="exact compatibility command block"):
        _assert_exact_marker_block(readme_path, prose_in_marker, marker, expected_commands)


def test_local_model_guide_scopes_cli_literals_and_declares_qlora_debt() -> None:
    fixture = _active_text_fixture()
    policy = _policy()
    assert policy["static_policy"]["active_text_scan"] == fixture

    guide_path = "documents/user/LOCAL_MODELS.md"
    qlora_path = "documents/user/QLORA.md"
    handoff_path = (
        ".planning/phases/41.1-codebase-architecture-overhaul/"
        "41.1-REPORT-HANDOFF.md"
    )
    guide = (REPO_ROOT / guide_path).read_text(encoding="utf-8")
    qlora = (REPO_ROOT / qlora_path).read_text(encoding="utf-8")
    handoff = (REPO_ROOT / handoff_path).read_text(encoding="utf-8")
    assert _scan_text(guide_path, guide, fixture) == []

    retired_prose = (
        "Phase 3 keeps the runtime",
        "Phase 3 training path",
        "CPU baseline in Phase 3",
        "Run the Phase 3 pilot dry-run",
        "Run the Phase 3 training doctor",
        "short Phase 3 smoke training job",
        "Phase 3 training dry-run or full run",
        "Phase 3 operator commands",
        "for Phase 1 or Phase 7",
    )
    assert all(fragment not in guide for fragment in retired_prose)

    local_model_markers = [
        row for row in fixture["literal_markers"] if row["path"] == guide_path
    ]
    assert local_model_markers == [
        {
            "path": "documents/user/LOCAL_MODELS.md",
            "marker_id": "legacy-local-model-cli",
            "start_marker": "<!-- legacy-local-model-cli:start -->",
            "end_marker": "<!-- legacy-local-model-cli:end -->",
            "reason": "preserve frozen local-model training version-tag examples",
            "owner": "local-model-cli-compatibility",
        }
    ]
    marker = local_model_markers[0]
    expected_commands = (
        "```bash\n"
        "python -m src.model_adaptation.cli doctor --candidate baseline-winner\n"
        "python -m src.model_adaptation.cli train --candidate baseline-winner --version-tag phase3-smoke --smoke-test\n"
        "python -m src.model_adaptation.cli train --candidate baseline-winner --version-tag phase3-main --resume-from-checkpoint latest\n"
        "```"
    )
    _assert_exact_marker_block(guide_path, guide, marker, expected_commands)
    assert guide.count("phase3-smoke") == 1
    assert guide.count("phase3-main") == 1

    assert fixture["active_documents"].count(qlora_path) == 1
    assert _active_scan_paths(policy).count(qlora_path) == 1
    assert qlora.strip(), "QLORA.md remains a visible active document"
    assert _scan_text(qlora_path, qlora + "\nPhase 91", fixture)
    assert "current typo-heavy explanatory wording is not defense-ready" in handoff
    assert "later report/user-document work" in handoff
    assert "does not rewrite it or" in handoff
    assert "claim that its prose quality has been reviewed" in handoff

    moved_token = guide.replace("phase3-main", "release-main", 1)
    moved_token += "\nCompatibility token: phase3-main\n"
    assert _scan_text(guide_path, moved_token, fixture)


def test_overview_and_cli_contracts_use_domain_narrative_or_exact_markers() -> None:
    fixture = _active_text_fixture()
    policy = _policy()
    assert policy["static_policy"]["active_text_scan"] == fixture

    overview_path = "docs/architecture/overview.md"
    cli_path = "docs/architecture/cli-contracts.md"
    overview = (REPO_ROOT / overview_path).read_text(encoding="utf-8")
    cli_document = (REPO_ROOT / cli_path).read_text(encoding="utf-8")
    assert _scan_text(overview_path, overview, fixture) == []
    assert _scan_text(cli_path, cli_document, fixture) == []

    expected_overview_markers = [
        {
            "path": overview_path,
            "marker_id": "legacy-data-cli-identifier",
            "start_marker": "<!-- legacy-data-cli-identifier:start -->",
            "end_marker": "<!-- legacy-data-cli-identifier:end -->",
            "reason": "preserve the run_phase1 compatibility identifier",
            "owner": "data-cli-compatibility",
        },
        {
            "path": overview_path,
            "marker_id": "policy-groups",
            "start_marker": "<!-- policy-groups:start -->",
            "end_marker": "<!-- policy-groups:end -->",
            "reason": "preserve policy-generated module identifiers",
            "owner": "module-boundaries-policy",
        },
        {
            "path": overview_path,
            "marker_id": "policy-edges",
            "start_marker": "<!-- policy-edges:start -->",
            "end_marker": "<!-- policy-edges:end -->",
            "reason": "preserve policy-generated compatibility edges",
            "owner": "module-boundaries-policy",
        },
        {
            "path": overview_path,
            "marker_id": "historical-sccs",
            "start_marker": "<!-- historical-sccs:start -->",
            "end_marker": "<!-- historical-sccs:end -->",
            "reason": "preserve policy-generated historical cycle identifiers",
            "owner": "module-boundaries-policy",
        },
    ]
    assert [
        row for row in fixture["literal_markers"] if row["path"] == overview_path
    ] == expected_overview_markers
    cli_marker = _marker_row(fixture, cli_path, "cli-contracts")
    assert cli_marker == {
        "path": cli_path,
        "marker_id": "cli-contracts",
        "start_marker": "<!-- cli-contracts:start -->",
        "end_marker": "<!-- cli-contracts:end -->",
        "reason": "preserve frozen command rows",
        "owner": "command-contract-policy",
    }

    _marker_spans(overview_path, overview, fixture)
    _marker_spans(cli_path, cli_document, fixture)
    _assert_exact_marker_block(
        overview_path,
        overview,
        expected_overview_markers[0],
        "`run_phase1`",
    )
    _assert_exact_marker_block(
        overview_path,
        overview,
        expected_overview_markers[1],
        _expected_policy_groups_body(policy),
    )
    _assert_exact_marker_block(
        overview_path,
        overview,
        expected_overview_markers[2],
        _expected_policy_edges_body(policy),
    )
    _assert_exact_marker_block(
        overview_path,
        overview,
        expected_overview_markers[3],
        _expected_historical_scc_body(policy),
    )
    expected_cli_body = _expected_cli_contract_body()
    _assert_exact_marker_block(cli_path, cli_document, cli_marker, expected_cli_body)

    command_rows = _markdown_table_rows(expected_cli_body, 5)
    command_names = tuple(row[0].strip("`") for row in command_rows)
    assert command_names == (
        "analyze",
        "doctor",
        "demo",
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
    groups = [row[1].strip("`") for row in command_rows]
    assert groups.count("installed") == 3
    assert groups.count("adaptation") == 4
    assert groups.count("phase40 compatibility") == 12
    assert groups.count("phase41 compatibility") == 7

    retired_prose = (
        "The chronological `run_phase1` name survives",
        "12 Phase 40",
        "7 Phase 41",
    )
    assert all(fragment not in f"{overview}\n{cli_document}" for fragment in retired_prose)
    assert "four adaptation commands" in cli_document
    assert "twelve\n  training/evidence compatibility commands" in cli_document
    assert "seven held-out-evaluation\n  compatibility commands" in cli_document

    moved_identifier = overview.replace("`run_phase1`", "`build_training_corpus`", 1)
    moved_identifier += "\nLegacy identifier: `run_phase1`\n"
    assert _scan_text(overview_path, moved_identifier, fixture)
    nested_marker = overview.replace(
        expected_overview_markers[0]["start_marker"],
        expected_overview_markers[0]["start_marker"]
        + "\n"
        + expected_overview_markers[0]["start_marker"],
        1,
    )
    with pytest.raises(AssertionError, match="missing or duplicate start marker"):
        _marker_spans(overview_path, nested_marker, fixture)
    prose_in_cli_marker = cli_document.replace(
        cli_marker["start_marker"],
        f"{cli_marker['start_marker']}\nPhase 91 narrative bypass",
        1,
    )
    with pytest.raises(AssertionError, match="exact compatibility command block"):
        _assert_exact_marker_block(
            cli_path,
            prose_in_cli_marker,
            cli_marker,
            expected_cli_body,
        )


def test_provenance_and_storage_use_domain_narrative_or_exact_authority_markers() -> None:
    from tests.architecture import test_report_handoff as report_contract

    fixture = _active_text_fixture()
    policy = _policy()
    assert policy["static_policy"]["active_text_scan"] == fixture

    provenance_path = "docs/architecture/provenance.md"
    storage_path = "docs/architecture/storage-retention.md"
    provenance = (REPO_ROOT / provenance_path).read_text(encoding="utf-8")
    storage = (REPO_ROOT / storage_path).read_text(encoding="utf-8")
    assert _scan_text(provenance_path, provenance, fixture) == []
    assert _scan_text(storage_path, storage, fixture) == []

    expected_provenance_markers = [
        {
            "path": provenance_path,
            "marker_id": "provenance-authority-identities",
            "start_marker": "<!-- provenance-authority-identities:start -->",
            "end_marker": "<!-- provenance-authority-identities:end -->",
            "reason": "preserve exact source export and erratum authority paths",
            "owner": "provenance-report-contract",
        },
        {
            "path": provenance_path,
            "marker_id": "provenance-schema-identities",
            "start_marker": "<!-- provenance-schema-identities:start -->",
            "end_marker": "<!-- provenance-schema-identities:end -->",
            "reason": "preserve exact evidence and erratum schema identifiers",
            "owner": "provenance-report-contract",
        },
        {
            "path": provenance_path,
            "marker_id": "provenance-correction-quote",
            "start_marker": "<!-- provenance-correction-quote:start -->",
            "end_marker": "<!-- provenance-correction-quote:end -->",
            "reason": "preserve the mandatory correction quote byte-for-byte",
            "owner": "provenance-report-contract",
        },
    ]
    expected_storage_markers = [
        {
            "path": storage_path,
            "marker_id": "sealed-roots",
            "start_marker": "<!-- sealed-roots:start -->",
            "end_marker": "<!-- sealed-roots:end -->",
            "reason": "preserve exact sealed model-root identities",
            "owner": "storage-retention-contract",
        },
        {
            "path": storage_path,
            "marker_id": "optional-gguf",
            "start_marker": "<!-- optional-gguf:start -->",
            "end_marker": "<!-- optional-gguf:end -->",
            "reason": "preserve the exact optional GGUF identity",
            "owner": "storage-retention-contract",
        },
        {
            "path": storage_path,
            "marker_id": "cleanup-candidates",
            "start_marker": "<!-- cleanup-candidates:start -->",
            "end_marker": "<!-- cleanup-candidates:end -->",
            "reason": "preserve exact informational cleanup-candidate identities",
            "owner": "storage-retention-contract",
        },
        {
            "path": storage_path,
            "marker_id": "nested-candidates",
            "start_marker": "<!-- nested-candidates:start -->",
            "end_marker": "<!-- nested-candidates:end -->",
            "reason": "preserve exact reviewed nested-duplicate identities",
            "owner": "storage-retention-contract",
        },
        {
            "path": storage_path,
            "marker_id": "older-bases",
            "start_marker": "<!-- older-bases:start -->",
            "end_marker": "<!-- older-bases:end -->",
            "reason": "preserve exact older-base identities",
            "owner": "storage-retention-contract",
        },
    ]
    assert [
        row for row in fixture["literal_markers"] if row["path"] == provenance_path
    ] == expected_provenance_markers
    assert [
        row for row in fixture["literal_markers"] if row["path"] == storage_path
    ] == expected_storage_markers
    _marker_spans(provenance_path, provenance, fixture)
    _marker_spans(storage_path, storage, fixture)

    authority_body = (
        "| Layer | Exact authority | What it establishes |\n"
        "| --- | --- | --- |\n"
        "| Current architecture | `architecture/module-boundaries.json` (`module-boundaries-v2`) | Active domain modules, compatibility adapters, historical modules, allowed edges, and static budgets |\n"
        "| Historical producer source | `historical/phase41-source-closure/c3bbc8c8adaf7579fd2eb9c59a0081613be4b2cae05dfdb64472938c7e6d0434/` | A post-evaluation, content-addressed mirror of the 37-source producer closure plus its launcher |\n"
        "| Frozen evaluation export | `data/models/phase41/verified-export/9ac54d58c273ab0a8c2f2b4b61e472a51ca94231a94b6847637ecad6ceee49f7/` | The completed 12-member evidence package and its terminal policy |\n"
        "| Mandatory correction | `data/models/phase41/phase41-provenance-erratum.json` | The disclosure that corrects global prior-access wording without modifying the export |"
    )
    schema_body = (
        "| Record | Exact schema identifier |\n"
        "| --- | --- |\n"
        "| `Verified evidence manifest` | `phase41-evidence-manifest-v1` |\n"
        "| `Mandatory provenance erratum` | `phase41-provenance-erratum-v1` |"
    )
    correction_quote = (
        "> Phase 41 contains exactly one terminal shared-cohort model-evaluation pass "
        "over the frozen Qwen QLoRA and PhoBERT models. It does not have zero prior "
        "filesystem access to the held-out file."
    )
    _assert_exact_marker_block(
        provenance_path,
        provenance,
        expected_provenance_markers[0],
        authority_body,
    )
    _assert_exact_marker_block(
        provenance_path,
        provenance,
        expected_provenance_markers[1],
        schema_body,
    )
    _assert_exact_marker_block(
        provenance_path,
        provenance,
        expected_provenance_markers[2],
        correction_quote,
    )
    for marker, width in zip(expected_storage_markers, (4, 4, 3, 2, 2)):
        _assert_table_only_marker(storage, marker, width)

    report_facts = _load_json(
        REPO_ROOT / "tests/architecture/fixtures/report_fact_contract.json"
    )
    report_contract._validate_provenance(provenance, report_facts)
    report_contract._validate_storage(storage)
    assert "recorded phase root" not in storage
    assert "final Phase 40/41 system" not in storage
    assert "recorded experiment root" in storage
    assert "retained final system" in storage

    moved_token = provenance.replace("phase41-evidence-manifest-v1", "evidence-manifest-v1", 1)
    moved_token += "\nSchema compatibility: `phase41-evidence-manifest-v1`\n"
    assert _scan_text(provenance_path, moved_token, fixture)
    near_match = storage.replace(r"\phase40\full", r"\phase400\full", 1)
    with pytest.raises(AssertionError):
        report_contract._validate_storage(near_match)
    nested_marker = storage.replace(
        expected_storage_markers[0]["start_marker"],
        expected_storage_markers[0]["start_marker"]
        + "\n"
        + expected_storage_markers[1]["start_marker"],
        1,
    )
    with pytest.raises(AssertionError, match="missing or duplicate start marker|nested or overlapping"):
        _marker_spans(storage_path, nested_marker, fixture)
    prose_in_marker = storage.replace(
        expected_storage_markers[0]["start_marker"],
        f"{expected_storage_markers[0]['start_marker']}\nPhase 91 narrative bypass",
        1,
    )
    with pytest.raises(AssertionError):
        _assert_table_only_marker(prose_in_marker, expected_storage_markers[0], 4)


def test_complete_active_text_inventory_is_clean() -> None:
    fixture = _active_text_fixture()
    policy = _policy()
    expected_active = [
        "README.md",
        "docs/architecture/overview.md",
        "docs/architecture/cli-contracts.md",
        "docs/architecture/provenance.md",
        "docs/architecture/storage-retention.md",
        "documents/user/LOCAL_MODELS.md",
        "documents/user/QLORA.md",
        "documents/user/USER_GUIDE.md",
    ]
    assert fixture["active_documents"] == expected_active
    assert fixture["historical_documents"] == ["walkthrough/README.md"]

    scan_paths = _active_scan_paths(policy)
    expected_scan_paths = [
        _module_source_path(module) for module in policy["active_modules"]
    ]
    expected_scan_paths.extend(
        row["path"]
        for row in policy["static_policy"]["tools"]
        if row["lifecycle"] in {"active", "compatibility"}
    )
    expected_scan_paths.extend(fixture["text_assets"])
    expected_scan_paths.extend(expected_active)
    assert scan_paths == expected_scan_paths
    assert len(scan_paths) == 44
    assert len(scan_paths) == len(set(scan_paths))

    excluded_tool_paths = {
        row["path"]
        for row in policy["static_policy"]["tools"]
        if row["lifecycle"] not in {"active", "compatibility"}
    }
    assert len(excluded_tool_paths) == 2
    assert excluded_tool_paths.isdisjoint(scan_paths)
    assert "walkthrough/README.md" not in scan_paths

    violations: list[str] = []
    for logical_path in scan_paths:
        source = (REPO_ROOT / logical_path).read_text(encoding="utf-8")
        violations.extend(_scan_text(logical_path, source, fixture))
        mutated = source + "\n# Phase\u00a091 active-inventory mutation\n"
        mutated_violations = _scan_text(logical_path, mutated, fixture)
        assert any(
            violation.rsplit(":", 1)[-1] == "Phase\u00a091"
            for violation in mutated_violations
        ), f"active scan mutation escaped: {logical_path}"
    assert violations == []

    _validate_exception_ownership(fixture)
    handoff = (
        REPO_ROOT
        / ".planning/phases/41.1-codebase-architecture-overhaul/"
        "41.1-REPORT-HANDOFF.md"
    ).read_text(encoding="utf-8")
    assert "current typo-heavy explanatory wording is not defense-ready" in handoff
    assert "later report/user-document work" in handoff
    assert "does not rewrite it or" in handoff
    assert "claim that its prose quality has been reviewed" in handoff
