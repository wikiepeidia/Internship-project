"""Contract tests for the fixed, lazy data-migration catalog."""

from __future__ import annotations

import ast
import hashlib
import importlib
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest


REPO_ROOT = Path(__file__).parents[2]
MIGRATION_MODULE = "src.data_pipeline.migrations"
EXPECTED_MIGRATIONS = {
    "task-scam-risk-tier": (
        "src.data_pipeline.apply_task_scam_risk_tier_repair",
        "main",
        "Repair task-level scam risk tiers",
        "preserved-repair",
    ),
    "zalo-narrator-extraction": (
        "src.data_pipeline.repair_zalo_narrator_scaffold",
        "main",
        "Extract Zalo narrator scaffolds",
        "superseded-by-direct-reconstruction",
    ),
    "zalo-direct-reconstruction": (
        "src.data_pipeline.reconstruct_zalo_direct_catalog",
        "main",
        "Reconstruct direct Zalo catalog entries",
        "preserved-repair",
    ),
    "mislabel-triage": (
        "src.data_pipeline.apply_mislabel_triage",
        "main",
        "Apply reviewed mislabel triage decisions",
        "preserved-repair",
    ),
    "corpus-split-governance": (
        "src.data_pipeline.repair_corpus_split_governance",
        "main",
        "Repair corpus split governance metadata",
        "preserved-repair",
    ),
}
FROZEN_MODULE_BLOBS = {
    "src/data_pipeline/apply_task_scam_risk_tier_repair.py": (
        "3183ab18b846fa67cdb710ed50689d1a0907b232"
    ),
    "src/data_pipeline/repair_zalo_narrator_scaffold.py": (
        "199e7e53b6506c298eb7f3a80877073bbc9ea439"
    ),
    "src/data_pipeline/reconstruct_zalo_direct_catalog.py": (
        "602d042f8ba1c3a21878c3550654be472f02efba"
    ),
    "src/data_pipeline/apply_mislabel_triage.py": (
        "acab8956f9d15a548b414ba370038e1c1084f817"
    ),
    "src/data_pipeline/repair_corpus_split_governance.py": (
        "230d0a36bc3f344abdc7a905a69cd43c159b6129"
    ),
}


def _catalog():
    return importlib.import_module(MIGRATION_MODULE)


def _git_blob_id(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()  # noqa: S324 - Git identity


def test_catalog_is_frozen_literal_and_import_safe() -> None:
    repair_modules = {route[0] for route in EXPECTED_MIGRATIONS.values()}
    assert not repair_modules.intersection(sys.modules)

    catalog = _catalog()

    assert not repair_modules.intersection(sys.modules)
    assert tuple(catalog.MIGRATIONS) == tuple(EXPECTED_MIGRATIONS)
    actual = {
        migration_id: (
            spec.module,
            spec.entry_symbol,
            spec.purpose,
            spec.provenance_status,
        )
        for migration_id, spec in catalog.MIGRATIONS.items()
    }
    assert actual == EXPECTED_MIGRATIONS
    assert all(spec.migration_id == migration_id for migration_id, spec in catalog.MIGRATIONS.items())
    assert all("phase" not in migration_id for migration_id in catalog.MIGRATIONS)
    with pytest.raises(TypeError):
        catalog.MIGRATIONS["unreviewed-route"] = next(iter(catalog.MIGRATIONS.values()))


def test_selected_entrypoint_imports_only_its_literal_module(monkeypatch: pytest.MonkeyPatch) -> None:
    catalog = _catalog()
    selected_id = "zalo-direct-reconstruction"
    selected_module = EXPECTED_MIGRATIONS[selected_id][0]
    selected_entrypoint = lambda: None
    selected_entrypoint.__module__ = selected_module
    imports: list[str] = []

    def fake_import(module: str):
        imports.append(module)
        assert module == selected_module
        return SimpleNamespace(main=selected_entrypoint)

    monkeypatch.setattr(catalog.importlib, "import_module", fake_import)

    assert catalog.load_migration_entrypoint(selected_id) is selected_entrypoint
    assert imports == [selected_module]


def test_unknown_id_fails_before_any_import(monkeypatch: pytest.MonkeyPatch) -> None:
    catalog = _catalog()
    imports: list[str] = []
    monkeypatch.setattr(
        catalog.importlib,
        "import_module",
        lambda module: imports.append(module),
    )

    with pytest.raises(catalog.UnknownMigrationError, match="unknown-migration"):
        catalog.get_migration("unknown-migration")
    with pytest.raises(catalog.UnknownMigrationError, match="unknown-migration"):
        catalog.load_migration_entrypoint("unknown-migration")

    assert imports == []


def test_selected_symbol_must_exist_and_be_callable(monkeypatch: pytest.MonkeyPatch) -> None:
    catalog = _catalog()
    migration_id = "task-scam-risk-tier"

    monkeypatch.setattr(
        catalog.importlib,
        "import_module",
        lambda module: SimpleNamespace(main=None),
    )

    with pytest.raises(catalog.InvalidMigrationEntrypointError, match=migration_id):
        catalog.load_migration_entrypoint(migration_id)


@pytest.mark.parametrize("invalid_kind", ("async", "class", "instance", "reexport", "argument"))
def test_selected_entrypoint_requires_exact_synchronous_function_shape(
    invalid_kind: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    catalog = _catalog()
    migration_id = "task-scam-risk-tier"
    selected_module = EXPECTED_MIGRATIONS[migration_id][0]

    async def async_entrypoint() -> None:
        return None

    class CallableEntrypoint:
        def __call__(self) -> None:
            return None

    def reexported_entrypoint() -> None:
        return None

    def argument_entrypoint(required: str) -> None:
        del required

    candidates = {
        "async": async_entrypoint,
        "class": CallableEntrypoint,
        "instance": CallableEntrypoint(),
        "reexport": reexported_entrypoint,
        "argument": argument_entrypoint,
    }
    candidate = candidates[invalid_kind]
    if invalid_kind in {"async", "argument"}:
        candidate.__module__ = selected_module
    monkeypatch.setattr(
        catalog.importlib,
        "import_module",
        lambda _module: SimpleNamespace(main=candidate),
    )

    with pytest.raises(catalog.InvalidMigrationEntrypointError, match=migration_id):
        catalog.load_migration_entrypoint(migration_id)


@pytest.mark.parametrize("relative_path, expected_blob", FROZEN_MODULE_BLOBS.items())
def test_preserved_repair_module_and_main_are_byte_identical(
    relative_path: str,
    expected_blob: str,
) -> None:
    data = (REPO_ROOT / relative_path).read_bytes()
    assert _git_blob_id(data) == expected_blob

    tree = ast.parse(data.decode("utf-8"))
    entrypoints = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "main"
    ]
    assert len(entrypoints) == 1
    assert not any(
        isinstance(node, ast.AsyncFunctionDef) and node.name == "main"
        for node in tree.body
    )
    arguments = entrypoints[0].args
    assert not (
        arguments.posonlyargs
        or arguments.args
        or arguments.vararg
        or arguments.kwonlyargs
        or arguments.kwarg
    )
