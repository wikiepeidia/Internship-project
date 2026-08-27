"""Synthetic-only safety fixtures for the Phase 41.1 architecture tests."""

from __future__ import annotations

import os
from pathlib import Path
import sys

import pytest


_bootstrap = sys.modules.get("sitecustomize")
if os.environ.get("PHASE411_DENY_OPEN_SENTINEL") != "1":
    raise RuntimeError("Phase 41.1 tests require the pre-collection deny-open sentinel")
if not getattr(_bootstrap, "PHASE411_GUARD_INSTALLED", False):
    raise RuntimeError("Phase 41.1 deny-open guard was not installed before conftest")


@pytest.fixture(autouse=True)
def isolated_phase411_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Force every architecture test onto per-test data and model roots."""

    roots = {
        "DATA_DIR": tmp_path / "data",
        "MODEL_ARTIFACT_ROOT": tmp_path / "models",
        "MODEL_REGISTRY_PATH": tmp_path / "registry.json",
    }
    for name, path in roots.items():
        monkeypatch.setenv(name, os.fspath(path))
    monkeypatch.setenv("PHASE411_DENY_OPEN_SENTINEL", "1")
    yield

