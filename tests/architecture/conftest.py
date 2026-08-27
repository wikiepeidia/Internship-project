"""Synthetic-only safety fixtures for Phase 41.1 architecture tests."""

from __future__ import annotations

import ntpath
import os
from pathlib import Path
import sys

import pytest


_bootstrap = sys.modules.get("sitecustomize")
if os.environ.get("PHASE411_DENY_OPEN_SENTINEL") != "1":
    raise RuntimeError("Phase 41.1 tests require the pre-collection deny-open sentinel")
if not getattr(_bootstrap, "PHASE411_GUARD_INSTALLED", False):
    raise RuntimeError("Phase 41.1 deny-open guard was not installed before conftest")

_expected_origin = ntpath.normcase(
    ntpath.normpath(ntpath.join(ntpath.dirname(__file__), "bootstrap", "sitecustomize.py"))
)
_actual_file = ntpath.normcase(ntpath.normpath(str(getattr(_bootstrap, "__file__", ""))))
_actual_origin = ntpath.normcase(
    ntpath.normpath(str(getattr(getattr(_bootstrap, "__spec__", None), "origin", "")))
)
if _actual_file != _expected_origin or _actual_origin != _expected_origin:
    raise RuntimeError("Phase 41.1 sitecustomize origin is not the exact bootstrap file")
if getattr(_bootstrap, "PHASE411_GUARD_BOUNDARY", None) != (
    "audited-interpreter-native-load-denied"
):
    raise RuntimeError("Phase 41.1 audited interpreter boundary is not active")
if not getattr(_bootstrap, "PHASE411_AUDIT_GUARD_INSTALLED", False):
    raise RuntimeError("Phase 41.1 append-only audit guard is not active")
_native_dispositions = getattr(
    _bootstrap, "PHASE411_NATIVE_PROCESS_OPERATION_DISPOSITIONS", {}
)
if len(_native_dispositions) != 10 or any(
    disposition not in {"wrapped", "unavailable_on_platform"}
    for disposition in _native_dispositions.values()
):
    raise RuntimeError("Phase 41.1 native process surfaces are not fail-closed")

_repo_root = ntpath.normpath(ntpath.join(ntpath.dirname(__file__), "..", ".."))
_historical_root = ntpath.normcase(
    ntpath.normpath(ntpath.join(_repo_root, "historical", "phase41-source-closure"))
)
for _entry in sys.path:
    if not _entry:
        continue
    _candidate = ntpath.normcase(ntpath.normpath(ntpath.abspath(_entry)))
    if _candidate == _historical_root or _candidate.startswith(_historical_root + "\\"):
        raise RuntimeError("protected historical archive prefix is present in sys.path")
if any(
    name == "historical.phase41_source_closure"
    or name.startswith("historical.phase41_source_closure.")
    for name in sys.modules
):
    raise RuntimeError("protected historical module is loaded before collection")


@pytest.fixture(autouse=True)
def isolated_phase411_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    roots = {
        "DATA_DIR": tmp_path / "data",
        "MODEL_ARTIFACT_ROOT": tmp_path / "models",
        "MODEL_REGISTRY_PATH": tmp_path / "registry.json",
    }
    for name, path in roots.items():
        monkeypatch.setenv(name, os.fspath(path))
    monkeypatch.setenv("PHASE411_DENY_OPEN_SENTINEL", "1")
    yield


@pytest.fixture(autouse=True)
def phase411_windows_bound_descriptors(monkeypatch: pytest.MonkeyPatch):
    """Register BoundParent descriptors through the reviewed post-install seam."""

    captured: list[int] = []
    if os.name != "nt":
        yield captured
        return

    import msvcrt
    import sitecustomize

    implementation = msvcrt.open_osfhandle

    def registered(handle: int, flags: int) -> int:
        descriptor = implementation(handle, flags)
        sitecustomize.phase411_register_bound_descriptor(descriptor)
        captured.append(descriptor)
        return descriptor

    monkeypatch.setattr(msvcrt, "open_osfhandle", registered)
    yield captured
