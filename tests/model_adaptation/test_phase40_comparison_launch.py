"""Synthetic contract tests for the external Phase 40 comparison preflight."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import pytest

from src.model_adaptation import phase40_comparison_launch as launch
from src.model_adaptation.phase40_handoff import (
    PHASE40_COMPARISON_FINALIZER_SOURCE_ALLOWLIST,
)


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


@dataclass(frozen=True)
class Fixture:
    repo: Path
    request: Path
    amendment: Path
    receipt: Path
    launcher_host: launch.ExecutableAuthority
    python: launch.ExecutableAuthority


def _write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def test_external_preflight_allowlist_matches_scope_amendment_producer():
    assert launch.FINALIZER_SOURCE_ALLOWLIST == (
        PHASE40_COMPARISON_FINALIZER_SOURCE_ALLOWLIST
    )
    assert "src/model_adaptation/cli.py" in launch.FINALIZER_SOURCE_ALLOWLIST


def _fixture(tmp_path: Path) -> Fixture:
    repo = tmp_path / "repo"
    repo.mkdir(parents=True)
    source = {relative: b"" for relative in launch.FINALIZER_SOURCE_ALLOWLIST}
    source["pyproject.toml"] = b"[project]\nname='synthetic-phase40'\n"
    source["src/model_adaptation/cli.py"] = b"raise SystemExit(0)\n"
    for relative, payload in source.items():
        _write(repo / relative, payload)
    files = [
        {
            "path": relative,
            "bytes": len(payload),
            "sha256": _sha256(payload),
        }
        for relative, payload in sorted(source.items())
    ]
    source_tree_sha256 = _sha256(
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
    request = repo / launch.FIXED_RUN_REQUEST_RELATIVE_PATH
    _write(request, _canonical(request_payload))
    request_sha256 = _sha256(request.read_bytes())
    amendment_payload = {
        "schema_version": "phase40-two-full-model-scope-amendment-v1",
        "original_run_request_path": launch.FIXED_RUN_REQUEST_RELATIVE_PATH.as_posix(),
        "original_run_request_sha256": request_sha256,
        "active_full_run_ids": [
            "phase40-qwen-qlora-full-seed42-v1",
            "phase40-phobert-full-seed42-v1",
        ],
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
            "source_tree_sha256": source_tree_sha256,
        },
        "quality_model_run_ids": [
            "phase40-qwen-qlora-full-seed42-v1",
            "phase40-phobert-full-seed42-v1",
        ],
        "review_model_run_ids": [
            "phase40-qwen-qlora-full-seed42-v1",
            "phase40-phobert-full-seed42-v1",
        ],
        "execution_policy": "local_primary",
        "colab_contingency_policy": (
            "validation_only_before_held_out_open_if_local_quality_unacceptable"
        ),
        "no_held_out_boundary": True,
    }
    amendment = repo / launch.FIXED_SCOPE_AMENDMENT_RELATIVE_PATH
    _write(amendment, _canonical(amendment_payload))
    launcher_source = Path("scripts/phase40_comparison_launcher.ps1")
    launcher = repo / launch.FIXED_LAUNCHER_RELATIVE_PATH
    _write(launcher, launcher_source.read_bytes())

    executable_root = tmp_path / "executables"
    host_path = executable_root / "pwsh.exe"
    python_path = executable_root / "python.exe"
    _write(host_path, b"synthetic-pwsh")
    _write(python_path, b"synthetic-python")
    host = launch.ExecutableAuthority(
        path=host_path,
        path_policy="windows_known_folder_program_files",
        portable_path="PowerShell/7/pwsh.exe",
        expected_sha256=_sha256(host_path.read_bytes()),
        version="7.6.1",
    )
    python = launch.ExecutableAuthority(
        path=python_path,
        path_policy="path_resolution_exact_hash",
        portable_path="python.exe",
        expected_sha256=_sha256(python_path.read_bytes()),
        version="3.13.13",
    )
    return Fixture(
        repo=repo,
        request=request,
        amendment=amendment,
        receipt=repo / launch.FIXED_RECEIPT_RELATIVE_PATH,
        launcher_host=host,
        python=python,
    )


def _freeze(fixture: Fixture) -> dict[str, object]:
    return launch.freeze_phase40_comparison_launch_receipt(
        repo_root=fixture.repo,
        launcher_host_authority=fixture.launcher_host,
        python_authority=fixture.python,
        preflight_started_at_utc="2026-08-26T01:00:00Z",
        preflight_completed_at_utc="2026-08-26T01:00:01Z",
        receipt_created_at_utc="2026-08-26T01:00:02Z",
    )


def test_freeze_and_verify_portable_self_hashed_pass_receipt(tmp_path):
    fixture = _fixture(tmp_path)
    payload = _freeze(fixture)

    verified = launch.verify_phase40_comparison_launch_receipt(
        repo_root=fixture.repo,
        launcher_host_authority=fixture.launcher_host,
        python_authority=fixture.python,
    )

    core = dict(payload)
    self_hash = core.pop("receipt_sha256")
    assert self_hash == _sha256(_canonical(core))
    assert verified == payload
    assert payload["status"] == "PASS"
    assert payload["request"] == {
        "relative_path": launch.FIXED_RUN_REQUEST_RELATIVE_PATH.as_posix(),
        "sha256": _sha256(fixture.request.read_bytes()),
    }
    assert payload["scope_amendment"]["sha256"] == _sha256(
        fixture.amendment.read_bytes()
    )
    assert payload["finalizer_authority"]["files"]
    assert payload["launcher"]["relative_path"] == (
        launch.FIXED_LAUNCHER_RELATIVE_PATH.as_posix()
    )
    assert payload["finalizer_command"] == list(launch.FIXED_FINALIZER_COMMAND)
    text = fixture.receipt.read_text(encoding="utf-8")
    assert str(tmp_path) not in text
    assert "C:\\Users\\" not in text
    assert fixture.receipt.read_bytes() == _canonical(payload)


def test_verify_rejects_noncanonical_tampered_fail_or_schema_drift(tmp_path):
    fixture = _fixture(tmp_path)
    payload = _freeze(fixture)
    fixture.receipt.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="canonical JSON"):
        launch.verify_phase40_comparison_launch_receipt(
            repo_root=fixture.repo,
            launcher_host_authority=fixture.launcher_host,
            python_authority=fixture.python,
        )

    failed = dict(payload)
    failed["status"] = "FAIL"
    failed_core = {key: value for key, value in failed.items() if key != "receipt_sha256"}
    failed["receipt_sha256"] = _sha256(_canonical(failed_core))
    fixture.receipt.write_bytes(_canonical(failed))
    with pytest.raises(RuntimeError, match="PASS"):
        launch.verify_phase40_comparison_launch_receipt(
            repo_root=fixture.repo,
            launcher_host_authority=fixture.launcher_host,
            python_authority=fixture.python,
        )

    malformed = dict(payload)
    malformed["unexpected"] = True
    malformed_core = {
        key: value for key, value in malformed.items() if key != "receipt_sha256"
    }
    malformed["receipt_sha256"] = _sha256(_canonical(malformed_core))
    fixture.receipt.write_bytes(_canonical(malformed))
    with pytest.raises(RuntimeError, match="keys mismatch"):
        launch.verify_phase40_comparison_launch_receipt(
            repo_root=fixture.repo,
            launcher_host_authority=fixture.launcher_host,
            python_authority=fixture.python,
        )


def test_verify_reopens_request_amendment_launcher_and_every_source(tmp_path):
    fixture = _fixture(tmp_path)
    _freeze(fixture)
    (fixture.repo / "src/model_adaptation/cli.py").write_text(
        "raise SystemExit(7)\n",
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="source identity mismatch"):
        launch.verify_phase40_comparison_launch_receipt(
            repo_root=fixture.repo,
            launcher_host_authority=fixture.launcher_host,
            python_authority=fixture.python,
        )

    fixture = _fixture(tmp_path / "second")
    _freeze(fixture)
    fixture.request.write_bytes(_canonical({"changed": True}))
    with pytest.raises(RuntimeError, match="request.*(?:stale|differs|keys mismatch)"):
        launch.verify_phase40_comparison_launch_receipt(
            repo_root=fixture.repo,
            launcher_host_authority=fixture.launcher_host,
            python_authority=fixture.python,
        )


def test_freeze_rejects_amendment_request_mismatch_and_traversal(tmp_path):
    fixture = _fixture(tmp_path)
    amendment = json.loads(fixture.amendment.read_text(encoding="utf-8"))
    amendment["original_run_request_sha256"] = "0" * 64
    fixture.amendment.write_bytes(_canonical(amendment))
    with pytest.raises(RuntimeError, match="different canonical run request"):
        _freeze(fixture)
    assert not fixture.receipt.exists()

    fixture = _fixture(tmp_path / "second")
    amendment = json.loads(fixture.amendment.read_text(encoding="utf-8"))
    files = amendment["comparison_finalizer_authority"]["files"]
    files[0]["path"] = "../escape.py"
    amendment["comparison_finalizer_authority"]["source_tree_sha256"] = _sha256(
        launch.FINALIZER_SOURCE_TREE_DOMAIN + _canonical(files)
    )
    fixture.amendment.write_bytes(_canonical(amendment))
    with pytest.raises(ValueError, match="safe repository-relative"):
        _freeze(fixture)
    assert not fixture.receipt.exists()


def test_freeze_rejects_invalid_chronology_and_absolute_payload_identity(tmp_path):
    fixture = _fixture(tmp_path)
    with pytest.raises(RuntimeError, match="chronology"):
        launch.freeze_phase40_comparison_launch_receipt(
            repo_root=fixture.repo,
            launcher_host_authority=fixture.launcher_host,
            python_authority=fixture.python,
            preflight_started_at_utc="2026-08-26T01:00:02Z",
            preflight_completed_at_utc="2026-08-26T01:00:01Z",
            receipt_created_at_utc="2026-08-26T01:00:00Z",
        )
    assert not fixture.receipt.exists()

    leaking_host = replace(
        fixture.launcher_host,
        portable_path=r"C:\Users\alice\pwsh.exe",
    )
    with pytest.raises(ValueError, match="portable"):
        launch.freeze_phase40_comparison_launch_receipt(
            repo_root=fixture.repo,
            launcher_host_authority=leaking_host,
            python_authority=fixture.python,
            preflight_started_at_utc="2026-08-26T01:00:00Z",
            preflight_completed_at_utc="2026-08-26T01:00:01Z",
            receipt_created_at_utc="2026-08-26T01:00:02Z",
        )


@pytest.mark.parametrize(
    ("hostile_path", "message"),
    (
        ("data/splits/test.jsonl", "allowed Python source namespace"),
        ("src//__init__.py", "safe repository-relative POSIX path"),
        ("src/./__init__.py", "safe repository-relative POSIX path"),
        ("src/module.py:ads", "safe repository-relative POSIX path"),
        ("src/module.py\x01", "safe repository-relative POSIX path"),
        (7, "safe repository-relative POSIX path"),
    ),
)
def test_freeze_rejects_reserved_noncanonical_or_nonstring_source_path(
    tmp_path,
    hostile_path,
    message,
):
    fixture = _fixture(tmp_path)
    amendment = json.loads(fixture.amendment.read_text(encoding="utf-8"))
    files = amendment["comparison_finalizer_authority"]["files"]
    files[0]["path"] = hostile_path
    amendment["comparison_finalizer_authority"]["source_tree_sha256"] = _sha256(
        launch.FINALIZER_SOURCE_TREE_DOMAIN + _canonical(files)
    )
    fixture.amendment.write_bytes(_canonical(amendment))

    with pytest.raises(ValueError, match=message):
        _freeze(fixture)
    assert not fixture.receipt.exists()


def test_freeze_rejects_string_coerced_source_byte_count(tmp_path):
    fixture = _fixture(tmp_path)
    amendment = json.loads(fixture.amendment.read_text(encoding="utf-8"))
    files = amendment["comparison_finalizer_authority"]["files"]
    files[0]["bytes"] = str(files[0]["bytes"])
    amendment["comparison_finalizer_authority"]["source_tree_sha256"] = _sha256(
        launch.FINALIZER_SOURCE_TREE_DOMAIN + _canonical(files)
    )
    fixture.amendment.write_bytes(_canonical(amendment))

    with pytest.raises(ValueError, match="invalid byte count"):
        _freeze(fixture)
    assert not fixture.receipt.exists()


def test_complete_namespace_gate_precedes_every_source_filesystem_call(
    tmp_path,
    monkeypatch,
):
    fixture = _fixture(tmp_path)
    amendment = json.loads(fixture.amendment.read_text(encoding="utf-8"))
    files = amendment["comparison_finalizer_authority"]["files"]
    files[-1]["path"] = "data/splits/test.jsonl"
    amendment["comparison_finalizer_authority"]["source_tree_sha256"] = _sha256(
        launch.FINALIZER_SOURCE_TREE_DOMAIN + _canonical(files)
    )
    fixture.amendment.write_bytes(_canonical(amendment))
    (fixture.repo / launch.FINALIZER_SOURCE_ALLOWLIST[0]).write_bytes(
        b"earlier-source-is-invalid\n"
    )

    source_paths = {
        (fixture.repo / relative).resolve()
        for relative in launch.FINALIZER_SOURCE_ALLOWLIST
    }
    opened_sources: list[Path] = []
    original_regular_file = launch._regular_file

    def filesystem_spy(path: Path, *, where: str) -> Path:
        if Path(path).resolve() in source_paths:
            opened_sources.append(Path(path))
        return original_regular_file(path, where=where)

    monkeypatch.setattr(launch, "_regular_file", filesystem_spy)
    with pytest.raises(ValueError, match="allowed Python source namespace"):
        _freeze(fixture)

    assert opened_sources == []
    assert not fixture.receipt.exists()


def test_freeze_rejects_supplementary_unicode_property_names(tmp_path):
    fixture = _fixture(tmp_path)
    amendment = json.loads(fixture.amendment.read_text(encoding="utf-8"))
    amendment["lora_probe_authority"] = {"\U00010000": 1, "\ue000": 2}
    fixture.amendment.write_bytes(_canonical(amendment))

    with pytest.raises(ValueError, match="supplementary Unicode property name"):
        _freeze(fixture)
    assert not fixture.receipt.exists()
