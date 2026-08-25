"""Static synthetic tests for the self-bound Phase 41 Windows launcher."""

from __future__ import annotations

import os
from pathlib import Path
import re
import subprocess
import sys


LAUNCHER = Path("scripts/phase41_one_shot_launcher.ps1")


def test_launcher_is_clean_runtime_self_bound_and_has_no_authority_overrides():
    source = LAUNCHER.read_text(encoding="utf-8")
    lowered = source.casefold()
    assert "commonapplicationdata" in lowered
    assert "phase41-one-shot-claims" in lowered
    assert "-i" in lowered and "-s" in lowered and "-b" in lowered
    assert "-s -s -b" in lowered
    assert "pythonpath" in lowered
    assert "execution-source-manifest.json" in lowered
    assert "execution-materialization-receipt.json" in lowered
    assert "phase41_one_shot_launcher.ps1" in lowered
    assert "fileshare]::read" in lowered
    assert "filemode]::createnew" in lowered
    assert ".flush($true)" in lowered
    assert "get-command python" not in lowered
    assert "areaccessrulesprotected" in lowered
    assert "get-acl -literalpath" in lowered
    assert "s-1-5-18" in lowered and "s-1-5-32-544" in lowered
    assert not re.search(
        r"param\s*\([^)]*\$(?:split|model|claim|registry|retry)",
        source,
        flags=re.IGNORECASE | re.DOTALL,
    )


def test_launcher_exposes_only_output_root_and_requires_canonical_run_command():
    source = LAUNCHER.read_text(encoding="utf-8")
    assert re.search(r"param\s*\([^)]*\$OutputRoot", source, flags=re.IGNORECASE | re.DOTALL)
    assert "phase41-run-once" in source
    for forbidden in ("--split-path", "--model-path", "--registry-root", "--retry"):
        assert forbidden not in source


def test_launcher_embedded_python_is_syntax_valid_and_bootstrap_is_source_only():
    source = LAUNCHER.read_text(encoding="utf-8")
    blocks = dict(
        re.findall(
            r"\$(ReceiptBuilder|Bootstrap)\s*=\s*@'\r?\n(.*?)\r?\n'@",
            source,
            flags=re.DOTALL,
        )
    )
    assert set(blocks) == {"ReceiptBuilder", "Bootstrap"}
    for name, body in blocks.items():
        compile(body, f"<{name}>", "exec")
    assert "Manifest.files" in source
    assert "model_bundle_authorities" in blocks["Bootstrap"]
    assert "runpy.run_module" in blocks["Bootstrap"]
    assert "models/" not in source


def test_isolated_no_site_bootstrap_ignores_hostile_sitecustomize(tmp_path):
    marker = tmp_path / "sitecustomize-ran"
    (tmp_path / "sitecustomize.py").write_text(
        f"from pathlib import Path\nPath({os.fspath(marker)!r}).write_text('ran')\n",
        encoding="utf-8",
    )
    environment = dict(os.environ)
    environment["PYTHONPATH"] = os.fspath(tmp_path)
    completed = subprocess.run(
        [
            sys.executable,
            "-I",
            "-S",
            "-s",
            "-B",
            "-c",
            "import sys; assert 'sitecustomize' not in sys.modules",
        ],
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    assert not marker.exists()
