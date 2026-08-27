"""Deterministic, path-inert source-closure archiving API."""

from importlib import import_module
from typing import Any


_PUBLIC_MODULES = ("contracts", "filesystem", "service")


def __getattr__(name: str) -> Any:
    """Resolve compatibility names lazily without eager package import cycles."""

    for relative in _PUBLIC_MODULES:
        module = import_module(f"{__name__}.{relative}")
        try:
            value = getattr(module, name)
        except AttributeError:
            continue
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "ArchiveError",
    "ArchiveReceipt",
    "archive_bound_source_closure",
    "verify_archived_source_closure",
]
