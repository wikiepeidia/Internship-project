"""Synthetic contract tests for the external Phase 40 comparison preflight."""

from __future__ import annotations

import base64
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
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
    phobert_request: Path
    amendment: Path
    final_authority: Path
    receipt: Path
    launcher_host: launch.ExecutableAuthority
    python: launch.ExecutableAuthority


def _write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def test_external_preflight_allowlist_matches_final_authority_producer():
    assert launch.FINALIZER_SOURCE_ALLOWLIST == (
        PHASE40_COMPARISON_FINALIZER_SOURCE_ALLOWLIST
    )
    assert "src/model_adaptation/cli.py" not in launch.FINALIZER_SOURCE_ALLOWLIST
    assert "src/model_adaptation/phase40_finalize.py" in (
        launch.FINALIZER_SOURCE_ALLOWLIST
    )
    assert "src/model_adaptation/phase40_final_authority.py" in (
        launch.FINALIZER_SOURCE_ALLOWLIST
    )
    assert "src/model_adaptation/phase40_production_authorities.py" in (
        launch.FINALIZER_SOURCE_ALLOWLIST
    )


def _fixture(tmp_path: Path) -> Fixture:
    repo = tmp_path / "repo"
    repo.mkdir(parents=True)
    source = {relative: b"" for relative in launch.FINALIZER_SOURCE_ALLOWLIST}
    source["pyproject.toml"] = b"[project]\nname='synthetic-phase40'\n"
    launcher_payload = Path("scripts/phase40_comparison_launcher.ps1").read_bytes()
    source[launch.FIXED_LAUNCHER_RELATIVE_PATH.as_posix()] = launcher_payload
    source["src/model_adaptation/phase40_finalize.py"] = b"raise SystemExit(0)\n"
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
    shared_input = {
        "archive_sha256": _sha256(b"shared-input"),
        "repository_relative_path": (
            "data/models/phase40/input/phase40-train-validation.zip"
        ),
    }

    def request_payload(run_id: str, *, capsule: bool) -> dict[str, object]:
        source_zip = b"phobert-source-zip" if capsule else b"qwen-source-zip"
        source_manifest = _canonical({"fixture": "source-inventory"})
        run_ids = (
            "phase40-qwen-lora-full-seed42-v1",
            "phase40-qwen-qlora-full-seed42-v1",
            run_id,
        )
        return {
        "schema_version": "phase40-full-run-request-v1",
        "runs": [{"run_id": current} for current in run_ids],
        "source_bundle": {
            "archive_sha256": _sha256(source_zip),
            "inventory_sha256": _sha256(source_manifest),
            "repository_relative_archive_path": (
                "data/models/phase40/source/phase40-source.zip"
            ),
            "repository_relative_inventory_path": (
                "data/models/phase40/source/phase40-source-manifest.json"
            ),
        },
        "input_bundle": shared_input,
        "package_candidates": [],
        "expected_bundle_files": [],
        "control_template_by_run": {
            current: {"fixture": True} for current in run_ids
        },
        "control_template_digest_by_run": {
            current: _sha256(current.encode()) for current in run_ids
        },
        "no_held_out_boundary": True,
        "git_commit": None,
    }
    qwen_run_id = "phase40-qwen-qlora-full-seed42-v1"
    phobert_run_id = "phase40-phobert-full-seed42-v12"
    qwen_request_payload = request_payload(
        "phase40-phobert-full-seed42-v1",
        capsule=False,
    )
    phobert_request_payload = request_payload(phobert_run_id, capsule=True)
    request = repo / launch.FIXED_RUN_REQUEST_RELATIVE_PATH
    _write(request, _canonical(qwen_request_payload))
    request_sha256 = _sha256(request.read_bytes())
    phobert_request = repo / launch.FIXED_PHOBERT_REQUEST_RELATIVE_PATH
    _write(phobert_request, _canonical(phobert_request_payload))
    phobert_request_sha256 = _sha256(phobert_request.read_bytes())
    capsule_payloads = (
        b"phobert-source-zip",
        _canonical({"fixture": "source-inventory"}),
        b"shared-input",
    )
    for relative, payload in zip(
        launch.FIXED_PHOBERT_CAPSULE_ASSET_RELATIVE_PATHS,
        capsule_payloads,
        strict=True,
    ):
        _write(repo / relative, payload)
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
    final_authority_payload = {
        "schema_version": "phase40-final-comparison-authority-v1",
        "superseded_scope_amendment": {
            "relative_path": launch.FIXED_SCOPE_AMENDMENT_RELATIVE_PATH.as_posix(),
            "sha256": _sha256(amendment.read_bytes()),
            "schema_version": "phase40-two-full-model-scope-amendment-v1",
        },
        "request_authorities": [
            {
                "authority_id": "qwen-v1-origin",
                "root_policy": "repository_root",
                "request_sha256": request_sha256,
            },
            {
                "authority_id": "phobert-v12-recovery",
                "root_policy": "fixed_phobert_v12_capsule",
                "request_sha256": phobert_request_sha256,
            },
        ],
        "selected_runs": [
            {
                "run_id": qwen_run_id,
                "request_authority_id": "qwen-v1-origin",
                "requested_run_id": qwen_run_id,
                "returned_root": "data/models/phase40/full/qwen-qlora",
            },
            {
                "run_id": phobert_run_id,
                "request_authority_id": "phobert-v12-recovery",
                "requested_run_id": phobert_run_id,
                "returned_root": "data/models/phase40/full/phobert",
            },
        ],
        "quality_model_run_ids": [qwen_run_id, phobert_run_id],
        "review_model_run_ids": [qwen_run_id, phobert_run_id],
        "shared_input_authority": shared_input,
        "waived_full_run_id": "phase40-qwen-lora-full-seed42-v1",
        "waiver_action": "withdrawn",
        "lora_probe_authority": amendment_payload["lora_probe_authority"],
        "comparison_finalizer_authority": (
            amendment_payload["comparison_finalizer_authority"]
        ),
        "recovery_policy": (
            "additive_per_run_request_authority_no_evidence_rewrite_v1"
        ),
        "execution_policy": "local_primary",
        "no_held_out_boundary": True,
    }
    final_authority = repo / launch.FIXED_FINAL_AUTHORITY_RELATIVE_PATH
    _write(final_authority, _canonical(final_authority_payload))
    launcher = repo / launch.FIXED_LAUNCHER_RELATIVE_PATH
    _write(launcher, launcher_payload)

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
        phobert_request=phobert_request,
        amendment=amendment,
        final_authority=final_authority,
        receipt=repo / launch.FIXED_RECEIPT_RELATIVE_PATH,
        launcher_host=host,
        python=python,
    )


_NONCE = bytes(range(32))
_LAUNCHER_PID = 4242
_CHILD_PID = 4343
_NOW = datetime(2026, 8, 26, 1, 0, 2, tzinfo=timezone.utc)


def _freeze(fixture: Fixture) -> dict[str, object]:
    payload = launch._pending_receipt_payload(
        root=fixture.repo,
        launcher_host_authority=fixture.launcher_host,
        python_authority=fixture.python,
        preflight_started_at_utc="2026-08-26T01:00:00Z",
        preflight_completed_at_utc="2026-08-26T01:00:01Z",
        receipt_created_at_utc="2026-08-26T01:00:02Z",
        nonce_sha256=_sha256(_NONCE),
        launcher_process_id=_LAUNCHER_PID,
        expires_at_utc="2026-08-26T01:01:02Z",
    )
    _write(fixture.receipt, _canonical(payload))
    return payload


def _arm_consumer(fixture: Fixture, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        launch.CAPABILITY_NONCE_ENV,
        base64.b64encode(_NONCE).decode("ascii"),
    )
    monkeypatch.setenv(launch.CAPABILITY_LAUNCHER_PID_ENV, str(_LAUNCHER_PID))
    monkeypatch.setenv(
        launch.CAPABILITY_PENDING_SHA256_ENV,
        _sha256(fixture.receipt.read_bytes()),
    )
    monkeypatch.setattr(launch, "default_launcher_host_authority", lambda: fixture.launcher_host)
    monkeypatch.setattr(launch, "default_python_authority", lambda: fixture.python)
    monkeypatch.setattr(launch, "_parent_process_id", lambda: _LAUNCHER_PID)
    monkeypatch.setattr(
        launch,
        "_parent_process_image_path",
        lambda process_id: fixture.launcher_host.path,
    )
    monkeypatch.setattr(launch, "_current_process_id", lambda: _CHILD_PID)
    monkeypatch.setattr(launch, "_current_working_directory", lambda: fixture.repo)
    monkeypatch.setattr(launch, "_current_python_executable", lambda: fixture.python.path)
    monkeypatch.setattr(launch, "_python_invocation_flags_are_hardened", lambda: True)
    monkeypatch.setattr(launch, "_utc_now", lambda: _NOW)


def _consume(
    fixture: Fixture,
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, object]:
    _arm_consumer(fixture, monkeypatch)
    return launch.consume_phase40_comparison_launch_capability(
        repo_root=fixture.repo,
        argv=list(launch.FIXED_FINALIZER_COMMAND[5:]),
    )


def test_consume_and_verify_portable_self_hashed_pass_receipt(tmp_path, monkeypatch):
    fixture = _fixture(tmp_path)
    pending = _freeze(fixture)
    assert pending["status"] == "PENDING"
    assert base64.b64encode(_NONCE).decode("ascii") not in fixture.receipt.read_text(
        encoding="utf-8"
    )
    payload = _consume(fixture, monkeypatch)

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
    assert payload["launch_capability"]["state"] == "consumed"
    assert payload["launch_capability"]["launcher_process_id"] == _LAUNCHER_PID
    assert payload["launch_capability"]["child_process_id"] == _CHILD_PID
    assert payload["launch_capability"]["pending_receipt_sha256"] == _sha256(
        _canonical(pending)
    )
    assert payload["final_comparison_authority"] == {
        "relative_path": launch.FIXED_FINAL_AUTHORITY_RELATIVE_PATH.as_posix(),
        "sha256": _sha256(fixture.final_authority.read_bytes()),
    }
    assert payload["request_authorities"][0]["request"] == {
        "relative_path": launch.FIXED_RUN_REQUEST_RELATIVE_PATH.as_posix(),
        "sha256": _sha256(fixture.request.read_bytes()),
    }
    assert payload["request_authorities"][1]["request"] == {
        "relative_path": launch.FIXED_PHOBERT_REQUEST_RELATIVE_PATH.as_posix(),
        "sha256": _sha256(fixture.phobert_request.read_bytes()),
    }
    assert len(payload["request_authorities"][1]["assets"]) == 3
    assert payload["superseded_scope_amendment"]["sha256"] == _sha256(
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


def test_direct_python_cannot_mint_or_consume_without_launcher_environment(
    tmp_path,
    monkeypatch,
):
    assert not hasattr(launch, "freeze_phase40_comparison_launch_receipt")
    fixture = _fixture(tmp_path)
    pending = _freeze(fixture)
    for name in (
        launch.CAPABILITY_NONCE_ENV,
        launch.CAPABILITY_LAUNCHER_PID_ENV,
        launch.CAPABILITY_PENDING_SHA256_ENV,
    ):
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(RuntimeError, match="fresh launcher capability"):
        launch.consume_phase40_comparison_launch_capability(
            repo_root=fixture.repo,
            argv=list(launch.FIXED_FINALIZER_COMMAND[5:]),
        )

    assert json.loads(fixture.receipt.read_text(encoding="utf-8")) == pending
    assert not (fixture.repo / launch.FIXED_CLAIM_RELATIVE_PATH).exists()


def test_consumed_capability_refuses_replay(tmp_path, monkeypatch):
    fixture = _fixture(tmp_path)
    _freeze(fixture)
    passed = _consume(fixture, monkeypatch)
    _arm_consumer(fixture, monkeypatch)

    with pytest.raises(RuntimeError, match="not pending"):
        launch.consume_phase40_comparison_launch_capability(
            repo_root=fixture.repo,
            argv=list(launch.FIXED_FINALIZER_COMMAND[5:]),
        )

    assert fixture.receipt.read_bytes() == _canonical(passed)


def test_pass_verification_rejects_a_self_consistent_tampered_claim(
    tmp_path,
    monkeypatch,
):
    fixture = _fixture(tmp_path)
    _freeze(fixture)
    _consume(fixture, monkeypatch)
    claim_path = fixture.repo / launch.FIXED_CLAIM_RELATIVE_PATH
    claim = json.loads(claim_path.read_text(encoding="utf-8"))
    claim["child_process_id"] += 1
    claim_core = {key: value for key, value in claim.items() if key != "claim_sha256"}
    claim["claim_sha256"] = _sha256(_canonical(claim_core))
    claim_path.write_bytes(_canonical(claim))

    with pytest.raises(RuntimeError, match="differs from PASS receipt"):
        launch.verify_phase40_comparison_launch_receipt(
            repo_root=fixture.repo,
            launcher_host_authority=fixture.launcher_host,
            python_authority=fixture.python,
        )


def test_failed_or_expired_capability_cannot_be_consumed(tmp_path, monkeypatch):
    fixture = _fixture(tmp_path)
    pending = _freeze(fixture)
    failed = dict(pending)
    failed["status"] = "FAILED"
    failed_core = {
        key: value for key, value in failed.items() if key != "receipt_sha256"
    }
    failed["receipt_sha256"] = _sha256(_canonical(failed_core))
    fixture.receipt.write_bytes(_canonical(failed))
    _arm_consumer(fixture, monkeypatch)
    with pytest.raises(RuntimeError, match="unsupported"):
        launch.consume_phase40_comparison_launch_capability(
            repo_root=fixture.repo,
            argv=list(launch.FIXED_FINALIZER_COMMAND[5:]),
        )

    fixture = _fixture(tmp_path / "expired")
    _freeze(fixture)
    _arm_consumer(fixture, monkeypatch)
    monkeypatch.setattr(launch, "_utc_now", lambda: _NOW + timedelta(minutes=2))
    with pytest.raises(RuntimeError, match="not currently fresh"):
        launch.consume_phase40_comparison_launch_capability(
            repo_root=fixture.repo,
            argv=list(launch.FIXED_FINALIZER_COMMAND[5:]),
        )
    assert not (fixture.repo / launch.FIXED_CLAIM_RELATIVE_PATH).exists()


def test_consumer_rejects_argv_parent_and_python_identity_drift(tmp_path, monkeypatch):
    fixture = _fixture(tmp_path)
    _freeze(fixture)
    _arm_consumer(fixture, monkeypatch)
    with pytest.raises(RuntimeError, match="argv"):
        launch.consume_phase40_comparison_launch_capability(
            repo_root=fixture.repo,
            argv=[*launch.FIXED_FINALIZER_COMMAND[5:], "--verify-only"],
        )

    _arm_consumer(fixture, monkeypatch)
    monkeypatch.setattr(launch, "_parent_process_id", lambda: _LAUNCHER_PID + 1)
    with pytest.raises(RuntimeError, match="not spawned"):
        launch.consume_phase40_comparison_launch_capability(
            repo_root=fixture.repo,
            argv=list(launch.FIXED_FINALIZER_COMMAND[5:]),
        )

    _arm_consumer(fixture, monkeypatch)
    monkeypatch.setattr(
        launch,
        "_current_python_executable",
        lambda: fixture.python.path.with_name("other-python.exe"),
    )
    with pytest.raises(RuntimeError, match="Python executable identity"):
        launch.consume_phase40_comparison_launch_capability(
            repo_root=fixture.repo,
            argv=list(launch.FIXED_FINALIZER_COMMAND[5:]),
        )
    assert not (fixture.repo / launch.FIXED_CLAIM_RELATIVE_PATH).exists()


def test_verify_rejects_noncanonical_tampered_fail_or_schema_drift(
    tmp_path,
    monkeypatch,
):
    fixture = _fixture(tmp_path)
    _freeze(fixture)
    payload = _consume(fixture, monkeypatch)
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
    with pytest.raises(RuntimeError, match="unsupported"):
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


def test_verify_reopens_final_requests_assets_amendment_launcher_and_sources(
    tmp_path,
    monkeypatch,
):
    fixture = _fixture(tmp_path)
    _freeze(fixture)
    _consume(fixture, monkeypatch)
    (fixture.repo / "src/model_adaptation/phase40_finalize.py").write_text(
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
    _consume(fixture, monkeypatch)
    fixture.request.write_bytes(_canonical({"changed": True}))
    with pytest.raises(RuntimeError, match="run request keys mismatch"):
        launch.verify_phase40_comparison_launch_receipt(
            repo_root=fixture.repo,
            launcher_host_authority=fixture.launcher_host,
            python_authority=fixture.python,
        )

    fixture = _fixture(tmp_path / "third")
    _freeze(fixture)
    _consume(fixture, monkeypatch)
    (fixture.repo / launch.FIXED_PHOBERT_CAPSULE_ASSET_RELATIVE_PATHS[0]).write_bytes(
        b"tampered"
    )
    with pytest.raises(RuntimeError, match="capsule asset identity mismatch"):
        launch.verify_phase40_comparison_launch_receipt(
            repo_root=fixture.repo,
            launcher_host_authority=fixture.launcher_host,
            python_authority=fixture.python,
        )


def test_pending_builder_rejects_final_request_mismatch_and_traversal(tmp_path):
    fixture = _fixture(tmp_path)
    authority = json.loads(fixture.final_authority.read_text(encoding="utf-8"))
    authority["request_authorities"][0]["request_sha256"] = "0" * 64
    fixture.final_authority.write_bytes(_canonical(authority))
    with pytest.raises(RuntimeError, match="request authorities drifted"):
        _freeze(fixture)
    assert not fixture.receipt.exists()

    fixture = _fixture(tmp_path / "second")
    authority = json.loads(fixture.final_authority.read_text(encoding="utf-8"))
    files = authority["comparison_finalizer_authority"]["files"]
    files[0]["path"] = "../escape.py"
    authority["comparison_finalizer_authority"]["source_tree_sha256"] = _sha256(
        launch.FINALIZER_SOURCE_TREE_DOMAIN + _canonical(files)
    )
    fixture.final_authority.write_bytes(_canonical(authority))
    with pytest.raises(ValueError, match="safe repository-relative"):
        _freeze(fixture)
    assert not fixture.receipt.exists()


def test_pending_builder_rejects_invalid_chronology_and_absolute_payload_identity(
    tmp_path,
):
    fixture = _fixture(tmp_path)
    with pytest.raises(RuntimeError, match="chronology"):
        launch._pending_receipt_payload(
            root=fixture.repo,
            launcher_host_authority=fixture.launcher_host,
            python_authority=fixture.python,
            preflight_started_at_utc="2026-08-26T01:00:02Z",
            preflight_completed_at_utc="2026-08-26T01:00:01Z",
            receipt_created_at_utc="2026-08-26T01:00:00Z",
            nonce_sha256=_sha256(_NONCE),
            launcher_process_id=_LAUNCHER_PID,
            expires_at_utc="2026-08-26T01:01:00Z",
        )
    assert not fixture.receipt.exists()

    leaking_host = replace(
        fixture.launcher_host,
        portable_path=r"C:\Users\alice\pwsh.exe",
    )
    with pytest.raises(ValueError, match="portable"):
        launch._pending_receipt_payload(
            root=fixture.repo,
            launcher_host_authority=leaking_host,
            python_authority=fixture.python,
            preflight_started_at_utc="2026-08-26T01:00:00Z",
            preflight_completed_at_utc="2026-08-26T01:00:01Z",
            receipt_created_at_utc="2026-08-26T01:00:02Z",
            nonce_sha256=_sha256(_NONCE),
            launcher_process_id=_LAUNCHER_PID,
            expires_at_utc="2026-08-26T01:01:02Z",
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
def test_pending_builder_rejects_reserved_noncanonical_or_nonstring_source_path(
    tmp_path,
    hostile_path,
    message,
):
    fixture = _fixture(tmp_path)
    authority = json.loads(fixture.final_authority.read_text(encoding="utf-8"))
    files = authority["comparison_finalizer_authority"]["files"]
    files[0]["path"] = hostile_path
    authority["comparison_finalizer_authority"]["source_tree_sha256"] = _sha256(
        launch.FINALIZER_SOURCE_TREE_DOMAIN + _canonical(files)
    )
    fixture.final_authority.write_bytes(_canonical(authority))

    with pytest.raises(ValueError, match=message):
        _freeze(fixture)
    assert not fixture.receipt.exists()


def test_pending_builder_rejects_string_coerced_source_byte_count(tmp_path):
    fixture = _fixture(tmp_path)
    authority = json.loads(fixture.final_authority.read_text(encoding="utf-8"))
    files = authority["comparison_finalizer_authority"]["files"]
    files[0]["bytes"] = str(files[0]["bytes"])
    authority["comparison_finalizer_authority"]["source_tree_sha256"] = _sha256(
        launch.FINALIZER_SOURCE_TREE_DOMAIN + _canonical(files)
    )
    fixture.final_authority.write_bytes(_canonical(authority))

    with pytest.raises(ValueError, match="invalid byte count"):
        _freeze(fixture)
    assert not fixture.receipt.exists()


def test_complete_namespace_gate_precedes_every_source_filesystem_call(
    tmp_path,
    monkeypatch,
):
    fixture = _fixture(tmp_path)
    authority = json.loads(fixture.final_authority.read_text(encoding="utf-8"))
    files = authority["comparison_finalizer_authority"]["files"]
    files[-1]["path"] = "data/splits/test.jsonl"
    authority["comparison_finalizer_authority"]["source_tree_sha256"] = _sha256(
        launch.FINALIZER_SOURCE_TREE_DOMAIN + _canonical(files)
    )
    fixture.final_authority.write_bytes(_canonical(authority))
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


def test_pending_builder_rejects_supplementary_unicode_property_names(tmp_path):
    fixture = _fixture(tmp_path)
    authority = json.loads(fixture.final_authority.read_text(encoding="utf-8"))
    authority["lora_probe_authority"] = {"\U00010000": 1, "\ue000": 2}
    fixture.final_authority.write_bytes(_canonical(authority))

    with pytest.raises(ValueError, match="supplementary Unicode property name"):
        _freeze(fixture)
    assert not fixture.receipt.exists()
