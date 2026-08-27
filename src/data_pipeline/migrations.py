"""Fixed lazy catalog for preserved one-off data repairs.

Catalog import is side-effect free. A preserved repair module is imported only
after its literal migration identifier has been selected explicitly.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import importlib
from types import MappingProxyType
from typing import Literal, cast


ProvenanceStatus = Literal[
    "preserved-repair",
    "superseded-by-direct-reconstruction",
]
MigrationEntrypoint = Callable[[], None]


@dataclass(frozen=True, slots=True)
class MigrationSpec:
    """Auditable route to one preserved repair entrypoint."""

    migration_id: str
    module: str
    entry_symbol: str
    purpose: str
    provenance_status: ProvenanceStatus


class UnknownMigrationError(LookupError):
    """Raised before import when a migration identifier is not catalogued."""


class InvalidMigrationEntrypointError(RuntimeError):
    """Raised when a preserved route no longer exposes its callable symbol."""


MIGRATIONS: Mapping[str, MigrationSpec] = MappingProxyType(
    {
        "task-scam-risk-tier": MigrationSpec(
            migration_id="task-scam-risk-tier",
            module="src.data_pipeline.apply_task_scam_risk_tier_repair",
            entry_symbol="main",
            purpose="Repair task-level scam risk tiers",
            provenance_status="preserved-repair",
        ),
        "zalo-narrator-extraction": MigrationSpec(
            migration_id="zalo-narrator-extraction",
            module="src.data_pipeline.repair_zalo_narrator_scaffold",
            entry_symbol="main",
            purpose="Extract Zalo narrator scaffolds",
            provenance_status="superseded-by-direct-reconstruction",
        ),
        "zalo-direct-reconstruction": MigrationSpec(
            migration_id="zalo-direct-reconstruction",
            module="src.data_pipeline.reconstruct_zalo_direct_catalog",
            entry_symbol="main",
            purpose="Reconstruct direct Zalo catalog entries",
            provenance_status="preserved-repair",
        ),
        "mislabel-triage": MigrationSpec(
            migration_id="mislabel-triage",
            module="src.data_pipeline.apply_mislabel_triage",
            entry_symbol="main",
            purpose="Apply reviewed mislabel triage decisions",
            provenance_status="preserved-repair",
        ),
        "corpus-split-governance": MigrationSpec(
            migration_id="corpus-split-governance",
            module="src.data_pipeline.repair_corpus_split_governance",
            entry_symbol="main",
            purpose="Repair corpus split governance metadata",
            provenance_status="preserved-repair",
        ),
    }
)


def get_migration(migration_id: str) -> MigrationSpec:
    """Return one reviewed route, rejecting unknown identifiers before import."""

    try:
        return MIGRATIONS[migration_id]
    except (KeyError, TypeError):
        raise UnknownMigrationError(f"Unknown migration id: {migration_id!r}") from None


def load_migration_entrypoint(migration_id: str) -> MigrationEntrypoint:
    """Import and return only the explicitly selected preserved entrypoint."""

    spec = get_migration(migration_id)
    module = importlib.import_module(spec.module)
    entrypoint = getattr(module, spec.entry_symbol, None)
    if not callable(entrypoint):
        raise InvalidMigrationEntrypointError(
            f"Migration {migration_id!r} does not expose callable "
            f"{spec.module}:{spec.entry_symbol}"
        )
    return cast(MigrationEntrypoint, entrypoint)


__all__ = [
    "InvalidMigrationEntrypointError",
    "MIGRATIONS",
    "MigrationEntrypoint",
    "MigrationSpec",
    "ProvenanceStatus",
    "UnknownMigrationError",
    "get_migration",
    "load_migration_entrypoint",
]
