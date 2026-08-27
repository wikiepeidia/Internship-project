"""Synthetic runtime-boundary tests for Phase 41.1 Plan 03."""

from __future__ import annotations

import ast
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import textwrap

import pytest


REPO_ROOT = Path(__file__).parents[2]
BLOCKED_IMPORT_PREFIXES = (
    "src.model_adaptation.training",
    "src.model_adaptation.phase40",
    "src.model_adaptation.phase41",
    "torch",
    "transformers",
    "sklearn",
    "accelerate",
    "peft",
    "openai",
    "google.generativeai",
)


def _write_manifest(root: Path, payload: object) -> Path:
    path = root / "manifests" / "download-manifest.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def _run_isolated_lookup(root: Path, candidate_id: str) -> subprocess.CompletedProcess[str]:
    script = textwrap.dedent(
        f"""
        import importlib.abc
        import pathlib
        import sys

        blocked = {BLOCKED_IMPORT_PREFIXES!r}

        class Blocker(importlib.abc.MetaPathFinder):
            def find_spec(self, fullname, path=None, target=None):
                if any(fullname == item or fullname.startswith(item + ".") for item in blocked):
                    raise ModuleNotFoundError("blocked optional import: " + fullname)
                return None

        sys.meta_path.insert(0, Blocker())
        module = __import__("src.runtime.analyzers.local_model", fromlist=["resolve_base_model_path"])
        resolved = module.resolve_base_model_path(sys.argv[2], pathlib.Path(sys.argv[1]))
        print(resolved)
        forbidden = sorted(
            name for name in sys.modules
            if any(name == item or name.startswith(item + ".") for item in blocked)
        )
        if forbidden:
            raise AssertionError("blocked modules loaded: " + repr(forbidden))
        """
    )
    return subprocess.run(
        [sys.executable, "-c", script, os.fspath(root), candidate_id],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def test_runtime_manifest_lookup_succeeds_with_optional_graph_blocked(tmp_path: Path) -> None:
    candidate = tmp_path / "synthetic-model"
    candidate.mkdir()
    _write_manifest(
        tmp_path,
        {"models": [{"candidate_id": "synthetic-qwen", "local_path": os.fspath(candidate)}]},
    )

    completed = _run_isolated_lookup(tmp_path, "synthetic-qwen")

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == os.fspath(candidate)


def test_runtime_missing_candidate_preserves_frozen_error_contract(tmp_path: Path) -> None:
    _write_manifest(tmp_path, {"models": []})

    completed = _run_isolated_lookup(tmp_path, "missing-candidate")

    assert completed.returncode != 0
    assert "Missing base model for candidate_id=missing-candidate" in completed.stderr
    assert os.fspath(tmp_path / "manifests" / "download-manifest.json") in completed.stderr
    assert os.fspath(tmp_path / "base" / "missing-candidate") in completed.stderr


@pytest.mark.parametrize(
    ("raw", "message"),
    [
        (b"\xff", "strict UTF-8 JSON"),
        (b'{"models": [], "models": []}', "duplicate JSON key"),
        (b"[]", "must be a JSON object"),
    ],
)
def test_download_manifest_rejects_invalid_json(
    tmp_path: Path, raw: bytes, message: str
) -> None:
    artifacts = importlib.import_module("src.artifacts")
    path = tmp_path / "manifests" / "download-manifest.json"
    path.parent.mkdir(parents=True)
    path.write_bytes(raw)

    with pytest.raises(artifacts.ArtifactError, match=message):
        artifacts.load_download_manifest(tmp_path)


@pytest.mark.parametrize(
    "payload",
    [
        {"models": {}},
        {"models": ["not-an-object"]},
        {"models": [{}]},
        {"models": [{"candidate_id": "candidate"}]},
        {"models": [{"candidate_id": "", "local_path": "model"}]},
        {"models": [{"candidate_id": "candidate", "local_path": ""}]},
        {
            "models": [
                {"candidate_id": "duplicate", "local_path": "first"},
                {"candidate_id": "duplicate", "local_path": "second"},
            ]
        },
    ],
)
def test_download_manifest_rejects_malformed_candidates(
    tmp_path: Path, payload: object
) -> None:
    artifacts = importlib.import_module("src.artifacts")
    _write_manifest(tmp_path, payload)

    with pytest.raises(artifacts.ArtifactError):
        artifacts.load_download_manifest(tmp_path)


def test_absent_download_manifest_is_an_empty_mapping(tmp_path: Path) -> None:
    artifacts = importlib.import_module("src.artifacts")

    assert artifacts.load_download_manifest(tmp_path) == {}


def test_neutral_boundary_is_closed_and_within_static_budgets() -> None:
    for relative in ("src/core/integrity.py", "src/artifacts.py"):
        source = (REPO_ROOT / relative).read_text(encoding="utf-8")
        assert ".rglob(" not in source
        assert "os.walk(" not in source
        assert "src.model_adaptation" not in source
        tree = ast.parse(source)
        assert len(source.splitlines()) <= 600
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                assert node.end_lineno is not None
                assert node.end_lineno - node.lineno + 1 <= 100, node.name

    local_source = (REPO_ROOT / "src/runtime/analyzers/local_model.py").read_text(
        encoding="utf-8"
    )
    assert "from src.artifacts import load_download_manifest" in local_source
    assert "src.model_adaptation.training" not in local_source

