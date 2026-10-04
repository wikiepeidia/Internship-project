"""Synthetic packaging and installed-runtime ownership contracts for Plan 41.1-03."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import textwrap
import tomllib


REPO_ROOT = Path(__file__).parents[2]
EXPECTED_BASE = {
    "pydantic>=2.12",
    "pydantic-settings>=2.0",
    "ftfy>=6.0",
}
EXPECTED_EXTRAS = {
    "dev": {"pytest>=9.0"},
    "generation": {
        "beautifulsoup4>=4.14",
        "requests>=2.32",
        "playwright>=1.58",
        "anthropic>=0.93",
        "google-auth>=2.0",
        "httpx>=0.28",
    },
    "data": {
        "pymupdf>=1.27,<2",
        "polars>=1.38",
        "sentence-transformers>=5.2",
        "rapidfuzz>=3.14",
        "datasketch>=1.9",
        "underthesea>=9.2",
    },
    "training": {
        "torch>=2.4",
        "transformers>=4.45",
        "accelerate>=0.33",
        "peft>=0.12",
    },
    "train": {
        "torch>=2.4",
        "transformers>=4.45",
        "accelerate>=0.33",
        "peft>=0.12",
    },
    "evaluation": {"scikit-learn>=1.8"},
    "runtime": {"llama-cpp-python==0.3.23"},
}
BLOCKED_OPTIONAL_PREFIXES = (
    "src.model_adaptation",
    "bs4",
    "requests",
    "playwright",
    "anthropic",
    "google.auth",
    "httpx",
    "fitz",
    "pymupdf",
    "polars",
    "sentence_transformers",
    "rapidfuzz",
    "datasketch",
    "underthesea",
    "torch",
    "transformers",
    "accelerate",
    "peft",
    "sklearn",
)


def test_dependency_groups_are_exact_and_disjoint() -> None:
    metadata = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = metadata["project"]
    extras = {name: set(values) for name, values in project["optional-dependencies"].items()}

    assert set(project["dependencies"]) == EXPECTED_BASE
    assert extras == EXPECTED_EXTRAS
    assert extras["train"] == extras["training"]
    ownership_groups = [
        EXPECTED_BASE,
        extras["generation"],
        extras["data"],
        extras["training"],
        extras["evaluation"],
        extras["runtime"],
        extras["dev"],
    ]
    for index, group in enumerate(ownership_groups):
        for other in ownership_groups[index + 1 :]:
            assert group.isdisjoint(other)
    assert project["scripts"] == {"vnphish": "src.runtime.cli:main"}


def test_installed_runtime_imports_with_every_optional_owner_blocked() -> None:
    script = textwrap.dedent(
        f"""
        import importlib
        import importlib.abc
        import sys

        blocked = {BLOCKED_OPTIONAL_PREFIXES!r}

        class Blocker(importlib.abc.MetaPathFinder):
            def find_spec(self, fullname, path=None, target=None):
                if any(fullname == item or fullname.startswith(item + ".") for item in blocked):
                    raise ModuleNotFoundError("blocked optional import: " + fullname)
                return None

        sys.meta_path.insert(0, Blocker())
        for module_name in (
            "src.core.integrity",
            "src.artifacts",
            "src.config.settings",
            "src.runtime.doctor",
            "src.runtime.service",
            "src.runtime.cli",
        ):
            importlib.import_module(module_name)
        forbidden = sorted(
            name for name in sys.modules
            if any(name == item or name.startswith(item + ".") for item in blocked)
        )
        if forbidden:
            raise AssertionError("blocked modules loaded: " + repr(forbidden))
        """
    )
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=dict(os.environ),
    )

    assert completed.returncode == 0, completed.stderr
