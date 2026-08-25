"""Static synthetic tests for the self-bound Phase 41 Windows launcher."""

from __future__ import annotations

import os
import hashlib
import json
from pathlib import Path
import platform
import re
import subprocess
import sys


LAUNCHER = Path("scripts/phase41_one_shot_launcher.ps1")


def _canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _embedded_blocks() -> dict[str, str]:
    source = LAUNCHER.read_text(encoding="utf-8")
    return dict(
        re.findall(
            r"\$(ReceiptBuilder|Bootstrap)\s*=\s*@'\r?\n(.*?)\r?\n'@",
            source,
            flags=re.DOTALL,
        )
    )


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
    blocks = _embedded_blocks()
    assert set(blocks) == {"ReceiptBuilder", "Bootstrap"}
    for name, body in blocks.items():
        compile(body, f"<{name}>", "exec")
    assert "Manifest.files" in source
    assert "model_bundle_authorities" in blocks["Bootstrap"]
    assert "runpy.run_module" in blocks["Bootstrap"]
    assert "models/" not in source


def test_embedded_receipt_and_bootstrap_execute_with_one_runtime_identity(tmp_path):
    blocks = _embedded_blocks()
    output = tmp_path / "output"
    clean = output / "clean-runtime"
    module_root = clean / "src" / "model_adaptation"
    module_root.mkdir(parents=True)
    files = {
        "src/__init__.py": b"",
        "src/model_adaptation/__init__.py": b"",
        "src/model_adaptation/cli.py": (
            b"import json, sys\n"
            b"from pathlib import Path\n"
            b"Path(sys.argv[-1], 'bootstrap-marker.json').write_text("
            b"json.dumps(sys.argv), encoding='utf-8')\n"
        ),
    }
    for name, payload in files.items():
        destination = clean / Path(name)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(payload)

    python_payload = Path(sys.executable).read_bytes()
    launcher_payload = LAUNCHER.read_bytes()
    source_manifest = {
        "schema_version": "phase41-execution-source-manifest-v1",
        "source_tree_sha256": "a" * 64,
        "files": [
            {
                "path": name,
                "bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
            for name, payload in sorted(files.items())
        ],
        "launcher": {
            "path": "scripts/phase41_one_shot_launcher.ps1",
            "bytes": len(launcher_payload),
            "sha256": hashlib.sha256(launcher_payload).hexdigest(),
        },
        "python": {
            "path": os.path.abspath(sys.executable),
            "bytes": len(python_payload),
            "sha256": hashlib.sha256(python_payload).hexdigest(),
            "version": platform.python_version(),
            "runtime_import_roots": [],
        },
    }
    request = {
        "authorities": {
            "model_bundle_authorities": [
                {
                    "role": "qwen",
                    "bundle_root": "synthetic/qwen",
                    "bundle_root_sha256": "b" * 64,
                },
                {
                    "role": "phobert",
                    "bundle_root": "synthetic/phobert",
                    "bundle_root_sha256": "c" * 64,
                },
            ]
        }
    }
    protocol = {"schema_version": "synthetic-protocol"}
    source_path = output / "execution-source-manifest.json"
    request_path = output / "evaluation-request.json"
    protocol_path = output / "frozen-inference-protocols.json"
    receipt_path = output / "execution-materialization-receipt.json"
    output.mkdir(exist_ok=True)
    source_path.write_bytes(_canonical_bytes(source_manifest))
    request_path.write_bytes(_canonical_bytes(request))
    protocol_path.write_bytes(_canonical_bytes(protocol))

    receipt = subprocess.run(
        [
            sys.executable,
            "-I",
            "-S",
            "-s",
            "-B",
            "-c",
            blocks["ReceiptBuilder"],
            os.fspath(receipt_path),
            os.fspath(source_path),
            os.fspath(request_path),
            os.fspath(protocol_path),
            os.fspath(clean),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert receipt.returncode == 0, receipt.stderr

    bootstrap = subprocess.run(
        [
            sys.executable,
            "-I",
            "-S",
            "-s",
            "-B",
            "-c",
            blocks["Bootstrap"],
            os.fspath(clean),
            os.fspath(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert bootstrap.returncode == 0, bootstrap.stderr
    marker = json.loads(
        (output / "bootstrap-marker.json").read_text(encoding="utf-8")
    )
    assert Path(marker[0]) == module_root / "cli.py"
    assert marker[1:] == [
        "phase41-run-once",
        "--output-root",
        os.fspath(output.absolute()),
    ]


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
