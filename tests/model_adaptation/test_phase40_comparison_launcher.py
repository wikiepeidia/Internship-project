"""Synthetic integration tests for the fixed Phase 40 comparison launcher."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from src.model_adaptation import phase40_comparison_launch as launch


LAUNCHER_SOURCE = Path("scripts/phase40_comparison_launcher.ps1")


def _canonical(value: object) -> bytes:
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


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def _synthetic_repo(tmp_path: Path, *, finalizer_exit_code: int = 0) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir(parents=True)
    marker_relative = "data/models/phase40/synthetic-finalizer-invocation.json"
    stub = (
        "from pathlib import Path\n"
        "import json\n"
        "import sys\n"
        "receipt = Path('data/models/phase40/comparison-launch-receipt.json')\n"
        f"marker = Path({marker_relative!r})\n"
        "marker.parent.mkdir(parents=True, exist_ok=True)\n"
        "marker.write_text(json.dumps({\n"
        "    'argv': sys.argv[1:],\n"
        "    'receipt_existed_before_finalizer': receipt.is_file(),\n"
        "}, sort_keys=True), encoding='utf-8')\n"
        f"raise SystemExit({finalizer_exit_code})\n"
    ).encode("utf-8")
    source = {relative: b"" for relative in launch.FINALIZER_SOURCE_ALLOWLIST}
    source["pyproject.toml"] = b"[project]\nname='synthetic-phase40-launch'\n"
    source["src/model_adaptation/cli.py"] = stub
    for relative, payload in source.items():
        _write(repo / relative, payload)
    files = [
        {"path": relative, "bytes": len(payload), "sha256": _sha256(payload)}
        for relative, payload in sorted(source.items())
    ]
    tree_sha256 = _sha256(
        launch.FINALIZER_SOURCE_TREE_DOMAIN + _canonical(files)
    )
    request_payload = {
        "schema_version": "phase40-full-run-request-v1",
        "runs": [],
        "source_bundle": {},
        "input_bundle": {},
        "package_candidates": [],
        "expected_bundle_files": [],
        "control_template_by_run": {},
        "control_template_digest_by_run": {},
        "no_held_out_boundary": True,
        "git_commit": None,
    }
    request_path = repo / launch.FIXED_RUN_REQUEST_RELATIVE_PATH
    request_bytes = _canonical(request_payload)
    _write(request_path, request_bytes)
    active_ids = [
        "phase40-qwen-qlora-full-seed42-v1",
        "phase40-phobert-full-seed42-v1",
    ]
    amendment_payload = {
        "schema_version": "phase40-two-full-model-scope-amendment-v1",
        "original_run_request_path": (
            launch.FIXED_RUN_REQUEST_RELATIVE_PATH.as_posix()
        ),
        "original_run_request_sha256": _sha256(request_bytes),
        "active_full_run_ids": active_ids,
        "active_returned_roots": [
            "data/models/phase40/full/qwen-qlora",
            "data/models/phase40/full/phobert",
        ],
        "waived_full_run_id": "phase40-qwen-lora-full-seed42-v1",
        "waived_returned_root": "data/models/phase40/full/qwen-lora",
        "full_lora_disposition": "cancelled_before_start",
        "waiver_action": "withdrawn",
        "waiver_basis": (
            "bounded_local_probe_established_resource_pressure_and_deadline_mismatch"
        ),
        "lora_probe_authority": {"fixture": True},
        "comparison_finalizer_authority": {
            "schema_version": "phase40-comparison-finalizer-authority-v1",
            "runtime_origin": "local_hash_pinned_source_not_training_runtime_v3",
            "files": files,
            "source_tree_sha256": tree_sha256,
        },
        "quality_model_run_ids": active_ids,
        "review_model_run_ids": active_ids,
        "execution_policy": "local_primary",
        "colab_contingency_policy": (
            "validation_only_before_held_out_open_if_local_quality_unacceptable"
        ),
        "no_held_out_boundary": True,
    }
    _write(
        repo / launch.FIXED_SCOPE_AMENDMENT_RELATIVE_PATH,
        _canonical(amendment_payload),
    )
    _write(repo / launch.FIXED_LAUNCHER_RELATIVE_PATH, LAUNCHER_SOURCE.read_bytes())
    return repo


def _mutate_finalizer_authority(repo: Path, mutation) -> None:
    amendment_path = repo / launch.FIXED_SCOPE_AMENDMENT_RELATIVE_PATH
    amendment = json.loads(amendment_path.read_text(encoding="utf-8"))
    authority = amendment["comparison_finalizer_authority"]
    mutation(authority)
    authority["source_tree_sha256"] = _sha256(
        launch.FINALIZER_SOURCE_TREE_DOMAIN + _canonical(authority["files"])
    )
    amendment_path.write_bytes(_canonical(amendment))


def _run_launcher(
    repo: Path,
    *,
    script_path: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    pwsh = shutil.which("pwsh")
    if sys.platform != "win32" or pwsh is None:
        pytest.skip("the fixed comparison launcher requires PowerShell on Windows")
    return subprocess.run(
        [
            pwsh,
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-File",
            str(
                repo / launch.FIXED_LAUNCHER_RELATIVE_PATH
                if script_path is None
                else script_path
            ),
        ],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )


def _marker(repo: Path) -> Path:
    return repo / "data/models/phase40/synthetic-finalizer-invocation.json"


def test_launcher_writes_durable_receipt_before_exact_finalizer(tmp_path):
    repo = _synthetic_repo(tmp_path)

    result = _run_launcher(repo)

    assert result.returncode == 0, result.stderr
    receipt = launch.verify_phase40_comparison_launch_receipt(repo_root=repo)
    marker = json.loads(_marker(repo).read_text(encoding="utf-8"))
    assert marker["receipt_existed_before_finalizer"] is True
    assert marker["argv"] == list(launch.FIXED_FINALIZER_COMMAND[5:])
    assert receipt["finalizer_command"] == list(launch.FIXED_FINALIZER_COMMAND)
    assert receipt["prelaunch_state"] == {
        "python_launched": False,
        "model_bundle_opened": False,
        "reserved_split_access_attempted": False,
    }


def test_launcher_propagates_finalizer_nonzero_after_preflight(tmp_path):
    repo = _synthetic_repo(tmp_path, finalizer_exit_code=7)

    result = _run_launcher(repo)

    assert result.returncode == 7, result.stderr
    assert "exited with code 7" in result.stderr
    assert (repo / launch.FIXED_RECEIPT_RELATIVE_PATH).is_file()
    assert json.loads(_marker(repo).read_text(encoding="utf-8"))[
        "receipt_existed_before_finalizer"
    ] is True


def test_launcher_fails_closed_before_receipt_on_source_drift(tmp_path):
    repo = _synthetic_repo(tmp_path)
    (repo / "src/model_adaptation/cli.py").write_text(
        "raise SystemExit('tampered')\n",
        encoding="utf-8",
    )

    result = _run_launcher(repo)

    assert result.returncode != 0
    assert "source identity mismatch" in result.stderr.lower()
    assert not (repo / launch.FIXED_RECEIPT_RELATIVE_PATH).exists()
    assert not _marker(repo).exists()


def test_launcher_refuses_to_overwrite_existing_receipt(tmp_path):
    repo = _synthetic_repo(tmp_path)
    receipt = repo / launch.FIXED_RECEIPT_RELATIVE_PATH
    sentinel = b"do-not-overwrite\n"
    _write(receipt, sentinel)

    result = _run_launcher(repo)

    assert result.returncode != 0
    assert "refusing to overwrite" in result.stderr.lower()
    assert receipt.read_bytes() == sentinel
    assert not _marker(repo).exists()


@pytest.mark.parametrize(
    ("hostile_path", "message"),
    (
        ("data/splits/test.jsonl", "allowed Python source namespace"),
        ("src//__init__.py", "canonical POSIX relative"),
        ("src/./__init__.py", "canonical POSIX relative"),
        ("src/module.py:ads", "canonical POSIX relative"),
        ("src/module.py\x01", "control character"),
        (7, "must be a string"),
    ),
)
def test_launcher_rejects_reserved_or_noncanonical_paths_before_source_open(
    tmp_path,
    hostile_path,
    message,
):
    repo = _synthetic_repo(tmp_path)

    def mutate(authority):
        authority["files"][0]["path"] = hostile_path

    _mutate_finalizer_authority(repo, mutate)
    result = _run_launcher(repo)

    assert result.returncode != 0
    assert message.lower() in result.stderr.lower()
    assert not (repo / launch.FIXED_RECEIPT_RELATIVE_PATH).exists()
    assert not _marker(repo).exists()


@pytest.mark.parametrize("hostile_bytes", (True, 0.0, "0"))
def test_launcher_rejects_noninteger_source_byte_tokens(tmp_path, hostile_bytes):
    repo = _synthetic_repo(tmp_path)

    def mutate(authority):
        authority["files"][0]["bytes"] = hostile_bytes

    _mutate_finalizer_authority(repo, mutate)
    result = _run_launcher(repo)

    assert result.returncode != 0
    assert "byte count is not a nonnegative integer" in result.stderr.lower()
    assert not (repo / launch.FIXED_RECEIPT_RELATIVE_PATH).exists()
    assert not _marker(repo).exists()


def test_launcher_rejects_exponent_number_for_source_bytes(tmp_path):
    repo = _synthetic_repo(tmp_path)
    amendment_path = repo / launch.FIXED_SCOPE_AMENDMENT_RELATIVE_PATH
    amendment = json.loads(amendment_path.read_text(encoding="utf-8"))
    first_bytes = amendment["comparison_finalizer_authority"]["files"][0]["bytes"]
    canonical = _canonical(amendment)
    token = f'"bytes":{first_bytes}'.encode("ascii")
    assert token in canonical
    amendment_path.write_bytes(canonical.replace(token, b'"bytes":0e0', 1))

    result = _run_launcher(repo)

    assert result.returncode != 0
    assert "must be canonical json" in result.stderr.lower()
    assert not (repo / launch.FIXED_RECEIPT_RELATIVE_PATH).exists()
    assert not _marker(repo).exists()


def test_launcher_rejects_exponent_in_unvalidated_nested_field(tmp_path):
    repo = _synthetic_repo(tmp_path)
    amendment_path = repo / launch.FIXED_SCOPE_AMENDMENT_RELATIVE_PATH
    canonical = amendment_path.read_bytes()
    token = b'"lora_probe_authority":{"fixture":true}'
    assert token in canonical
    amendment_path.write_bytes(
        canonical.replace(
            token,
            b'"lora_probe_authority":{"fixture":true,"nested":1e0}',
            1,
        )
    )

    result = _run_launcher(repo)

    assert result.returncode != 0
    assert "must be canonical json" in result.stderr.lower()
    assert not (repo / launch.FIXED_RECEIPT_RELATIVE_PATH).exists()
    assert not _marker(repo).exists()


def test_launcher_rejects_utf16_ordered_supplementary_property_name(tmp_path):
    repo = _synthetic_repo(tmp_path)
    amendment_path = repo / launch.FIXED_SCOPE_AMENDMENT_RELATIVE_PATH
    raw = amendment_path.read_bytes()
    token = b'"lora_probe_authority":{"fixture":true}'
    hostile = (
        '"lora_probe_authority":{"\U00010000":1,"\ue000":2}'
    ).encode("utf-8")
    assert token in raw
    amendment_path.write_bytes(raw.replace(token, hostile, 1))

    result = _run_launcher(repo)

    assert result.returncode != 0
    assert "supplementary unicode json property names" in result.stderr.lower()
    assert not (repo / launch.FIXED_RECEIPT_RELATIVE_PATH).exists()
    assert not _marker(repo).exists()


def test_launcher_uses_ordinal_order_for_nested_unicode_properties(tmp_path):
    repo = _synthetic_repo(tmp_path)
    amendment_path = repo / launch.FIXED_SCOPE_AMENDMENT_RELATIVE_PATH
    amendment = json.loads(amendment_path.read_text(encoding="utf-8"))
    amendment["lora_probe_authority"] = {
        "ä": [1.0, 1e-6, 1e-5, 1e15, 1e16, 1e20, 1.2345678901234567, 0.0, -0.0],
        "z": 1,
    }
    amendment_path.write_bytes(_canonical(amendment))

    result = _run_launcher(repo)

    assert result.returncode == 0, result.stderr
    assert _marker(repo).is_file()


def test_late_namespace_error_precedes_earlier_source_identity_failure(tmp_path):
    repo = _synthetic_repo(tmp_path)
    (repo / launch.FINALIZER_SOURCE_ALLOWLIST[0]).write_bytes(
        b"earlier-source-is-invalid\n"
    )

    def mutate(authority):
        authority["files"][-1]["path"] = "data/splits/test.jsonl"

    _mutate_finalizer_authority(repo, mutate)
    result = _run_launcher(repo)

    assert result.returncode != 0
    assert "allowed Python source namespace" in result.stderr
    assert "source identity mismatch" not in result.stderr.lower()
    assert not (repo / launch.FIXED_RECEIPT_RELATIVE_PATH).exists()
    assert not _marker(repo).exists()


def test_launcher_rejects_single_object_instead_of_source_array(tmp_path):
    repo = _synthetic_repo(tmp_path)

    def mutate(authority):
        authority["files"] = authority["files"][0]

    _mutate_finalizer_authority(repo, mutate)
    result = _run_launcher(repo)

    assert result.returncode != 0
    assert "exact code-fixed source array" in result.stderr.lower()
    assert not (repo / launch.FIXED_RECEIPT_RELATIVE_PATH).exists()
    assert not _marker(repo).exists()


def test_launcher_rejects_alternate_script_location_before_authority_reads(tmp_path):
    repo = _synthetic_repo(tmp_path)
    alternate = repo / "tools/phase40_comparison_launcher.ps1"
    _write(alternate, LAUNCHER_SOURCE.read_bytes())

    result = _run_launcher(repo, script_path=alternate)

    assert result.returncode != 0
    assert "outside its fixed repository scripts directory" in result.stderr.lower()
    assert not (repo / launch.FIXED_RECEIPT_RELATIVE_PATH).exists()
    assert not _marker(repo).exists()


def test_launcher_ast_and_static_boundary_are_fixed():
    pwsh = shutil.which("pwsh")
    if pwsh is None:
        pytest.skip("PowerShell parser is unavailable")
    parser = (
        "$tokens=$null;$errors=$null;"
        "[System.Management.Automation.Language.Parser]::ParseFile("
        "$env:PHASE40_LAUNCHER_TEST_PATH,[ref]$tokens,[ref]$errors)>$null;"
        "if($errors.Count){$errors|% Message;exit 1}"
    )
    environment = dict(os.environ)
    environment["PHASE40_LAUNCHER_TEST_PATH"] = str(LAUNCHER_SOURCE.resolve())
    parsed = subprocess.run(
        [pwsh, "-NoLogo", "-NoProfile", "-Command", parser],
        text=True,
        capture_output=True,
        check=False,
        timeout=20,
        env=environment,
    )
    assert parsed.returncode == 0, parsed.stderr or parsed.stdout

    timestamp_semantics = r"""
$tokens=$null
$errors=$null
$ast=[System.Management.Automation.Language.Parser]::ParseFile(
    $env:PHASE40_LAUNCHER_TEST_PATH,[ref]$tokens,[ref]$errors
)
$wanted=@('Format-CanonicalUtcTimestamp','ConvertFrom-CanonicalUtcTimestamp')
$definitions=$ast.FindAll({
    param($node)
    $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and
        $wanted -contains $node.Name
},$true)
if($definitions.Count -ne 2){exit 11}
Invoke-Expression (($definitions | ForEach-Object {$_.Extent.Text}) -join "`n")
$zero=[DateTime]::new(2026,8,26,0,0,0,[DateTimeKind]::Utc)
$micro=$zero.AddTicks(1234560)
$zeroText=Format-CanonicalUtcTimestamp -Value $zero
$microText=Format-CanonicalUtcTimestamp -Value $micro
if($zeroText -cne '2026-08-26T00:00:00Z'){exit 12}
if($microText -cne '2026-08-26T00:00:00.123456Z'){exit 13}
if((ConvertFrom-CanonicalUtcTimestamp -Value $zeroText).Ticks -ne $zero.Ticks){exit 14}
if((ConvertFrom-CanonicalUtcTimestamp -Value $microText).Ticks -ne $micro.Ticks){exit 15}
foreach($subMicroTick in 1..9){
    $subMicroText=Format-CanonicalUtcTimestamp -Value $zero.AddTicks($subMicroTick)
    if($subMicroText -cne $zeroText){exit (20+$subMicroTick)}
    if((ConvertFrom-CanonicalUtcTimestamp -Value $subMicroText).Ticks -ne $zero.Ticks){
        exit (30+$subMicroTick)
    }
}
"""
    timestamp_check = subprocess.run(
        [pwsh, "-NoLogo", "-NoProfile", "-Command", timestamp_semantics],
        text=True,
        capture_output=True,
        check=False,
        timeout=20,
        env=environment,
    )
    assert timestamp_check.returncode == 0, (
        timestamp_check.stderr or timestamp_check.stdout
    )

    text = LAUNCHER_SOURCE.read_text(encoding="utf-8")
    assert "[System.IO.FileMode]::CreateNew" in text
    assert "[System.IO.FileOptions]::WriteThrough" in text
    assert "$Stream.Flush($true)" in text
    assert "[System.Diagnostics.ProcessStartInfo]::new()" in text
    assert "--verify-only" not in text
    assert "D:\\" not in text
    assert "C:\\Users\\" not in text
    assert "param()" in text
