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

import pytest


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
    assert "redirectstandardinput = $true" in lowered
    assert "production_canonical" in lowered
    assert "launcher_host" in lowered
    assert "phase40_external_launcher_authority" in lowered
    assert "external_launch_receipt_sha256" in lowered
    assert source.count('"runtime_materialization_receipt_sha256"') >= 3
    assert "getclienthandleasstring" not in lowered
    assert "_vnphish_phase41_launcher_capability" not in lowered
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


@pytest.mark.skipif(os.name != "nt", reason="launcher capability is Windows-only")
def test_embedded_receipt_and_bootstrap_execute_with_one_runtime_identity(tmp_path):
    blocks = _embedded_blocks()
    output = tmp_path / "output"
    clean = output / "clean-runtime"
    module_root = clean / "src" / "model_adaptation"
    module_root.mkdir(parents=True)
    files = {
        "src/__init__.py": b"",
        "src/model_adaptation/__init__.py": b"",
        "src/model_adaptation/bound_probe.py": b"BOUND_PROBE = True\n",
        "src/model_adaptation/phase41_evaluation.py": Path(
            "src/model_adaptation/phase41_evaluation.py"
        ).read_bytes(),
        "src/model_adaptation/cli.py": (
            b"import hashlib, json, os, sys\n"
            b"from pathlib import Path\n"
            b"from src.model_adaptation import bound_probe\n"
            b"output = Path(sys.argv[-1])\n"
            b"receipt = json.loads((output / 'execution-materialization-receipt.json').read_text(encoding='utf-8'))\n"
            b"nonce = os.read(0, 32)\n"
            b"if len(nonce) != 32 or hashlib.sha256(nonce).hexdigest() != receipt['launcher_capability_sha256']:\n"
            b"    raise RuntimeError('synthetic launcher capability drifted')\n"
            b"reuse_blocked = True\n"
            b"injected = output / 'clean-runtime' / 'src' / "
            b"'model_adaptation' / 'injected.py'\n"
            b"injected.write_text(\"from pathlib import Path\\n"
            b"Path(__file__).with_name('injected-ran').write_text('ran')\\n\", "
            b"encoding='utf-8')\n"
            b"try:\n"
            b"    import src.model_adaptation.injected\n"
            b"except ModuleNotFoundError:\n"
            b"    injection_blocked = True\n"
            b"else:\n"
            b"    injection_blocked = False\n"
            b"Path(output, 'bootstrap-marker.json').write_text("
            b"json.dumps({'argv': sys.argv, 'injection_blocked': injection_blocked, "
            b"'launcher_live': True, 'reuse_blocked': reuse_blocked, "
            b"'probe_file': bound_probe.__file__, "
            b"'probe_origin': bound_probe.__spec__.origin, "
            b"'probe_has_location': bound_probe.__spec__.has_location}), "
            b"encoding='utf-8')\n"
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
        "preparation_scope": "synthetic_test",
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
        "launcher_host": {
            "mode": "synthetic_test",
            "path": os.path.abspath(sys.executable),
            "bytes": len(python_payload),
            "sha256": hashlib.sha256(python_payload).hexdigest(),
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
        "preparation_scope": "synthetic_test",
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
            ],
            "qwen_gguf_verification_receipt_sha256": "d" * 64,
            "phobert_release_receipt_authority_sha256": "e" * 64,
            "phobert_segmenter_authority_sha256": "f" * 64,
            "runtime_dependency_authority_sha256": "1" * 64,
            "runtime_materialization_receipt_sha256": "2" * 64,
        }
    }
    protocol = {"schema_version": "synthetic-protocol"}
    source_path = output / "execution-source-manifest.json"
    request_path = output / "evaluation-request.json"
    protocol_path = output / "frozen-inference-protocols.json"
    receipt_path = output / "execution-materialization-receipt.json"
    capability_nonce = os.urandom(32)
    capability_sha256 = hashlib.sha256(capability_nonce).hexdigest()
    launcher_image = Path(sys.executable).absolute()
    launcher_image_sha256 = hashlib.sha256(launcher_image.read_bytes()).hexdigest()
    output.mkdir(exist_ok=True)
    source_path.write_bytes(_canonical_bytes(source_manifest))
    request_path.write_bytes(_canonical_bytes(request))
    protocol_path.write_bytes(_canonical_bytes(protocol))

    mismatched_host = dict(source_manifest)
    mismatched_host["launcher_host"] = dict(source_manifest["launcher_host"])
    mismatched_host["launcher_host"]["sha256"] = "0" * 64
    source_path.write_bytes(_canonical_bytes(mismatched_host))
    rejected_host = subprocess.run(
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
            capability_sha256,
            str(os.getpid()),
            os.fspath(launcher_image),
            launcher_image_sha256,
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert rejected_host.returncode != 0
    assert "launcher host" in rejected_host.stderr.casefold()
    assert not receipt_path.exists()
    source_path.write_bytes(_canonical_bytes(source_manifest))

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
            capability_sha256,
            str(os.getpid()),
            os.fspath(launcher_image),
            launcher_image_sha256,
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert receipt.returncode == 0, receipt.stderr
    receipt_payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert (
        receipt_payload["runtime_materialization_receipt_sha256"]
        == request["authorities"]["runtime_materialization_receipt_sha256"]
    )

    direct = subprocess.run(
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
    assert direct.returncode != 0
    assert "launcher capability" in direct.stderr or "stdin pipe" in direct.stderr
    assert not (output / "bootstrap-marker.json").exists()

    def run_capability_child() -> tuple[int, str]:
        child = subprocess.Popen(
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
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False,
        )
        try:
            assert child.stdin is not None
            child.stdin.write(capability_nonce)
            child.stdin.flush()
            child_returncode = child.wait(timeout=30)
            assert child.stderr is not None
            child_stderr = child.stderr.read().decode("utf-8", errors="replace")
            return child_returncode, child_stderr
        finally:
            if child.stdin is not None:
                child.stdin.close()

    tampered_receipt = dict(receipt_payload)
    tampered_receipt["runtime_materialization_receipt_sha256"] = "0" * 64
    receipt_path.write_bytes(_canonical_bytes(tampered_receipt))
    returncode, stderr = run_capability_child()
    assert returncode != 0
    assert "materialization receipt drifted" in stderr
    assert not (output / "bootstrap-marker.json").exists()
    receipt_path.write_bytes(_canonical_bytes(receipt_payload))

    returncode, stderr = run_capability_child()
    assert returncode == 0, stderr
    marker = json.loads(
        (output / "bootstrap-marker.json").read_text(encoding="utf-8")
    )
    assert marker["injection_blocked"] is True
    assert marker["launcher_live"] is True
    assert marker["reuse_blocked"] is True
    expected_probe = module_root / "bound_probe.py"
    assert Path(marker["probe_file"]) == expected_probe
    assert Path(marker["probe_origin"]) == expected_probe
    assert marker["probe_has_location"] is True
    assert not (module_root / "injected-ran").exists()
    assert Path(marker["argv"][0]) == module_root / "cli.py"
    assert marker["argv"][1:] == [
        "phase41-run-once",
        "--output-root",
        os.fspath(output.absolute()),
    ]

    (output / "bootstrap-marker.json").unlink()
    (module_root / "injected.py").unlink()
    wrong_image_receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    wrong_image_receipt["launcher_process_image_sha256"] = "0" * 64
    receipt_path.write_bytes(_canonical_bytes(wrong_image_receipt))
    returncode, stderr = run_capability_child()
    assert returncode != 0
    assert "materialization parent differs" in stderr
    assert not (output / "bootstrap-marker.json").exists()

    wrong_parent_receipt = dict(wrong_image_receipt)
    wrong_parent_receipt["launcher_process_image_sha256"] = launcher_image_sha256
    wrong_parent_receipt["launcher_process_id"] = os.getpid() + 100000
    receipt_path.write_bytes(_canonical_bytes(wrong_parent_receipt))
    returncode, stderr = run_capability_child()
    assert returncode != 0
    assert "materialization parent differs" in stderr
    assert not (output / "bootstrap-marker.json").exists()


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
