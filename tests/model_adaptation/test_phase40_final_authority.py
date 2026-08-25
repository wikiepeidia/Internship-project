from __future__ import annotations

import inspect
import json
from pathlib import Path, PurePosixPath
import shutil

import pytest

from src.model_adaptation import phase40_handoff as handoff
from src.model_adaptation import phase40_final_authority as final_authority
from src.model_adaptation.phase40_final_authority import (
    FIXED_FINAL_COMPARISON_AUTHORITY_PATH,
    FIXED_HISTORICAL_SCOPE_AMENDMENT_PATH,
    FIXED_ORIGINAL_REQUEST_PATH,
    FIXED_PHOBERT_V12_CAPSULE_ROOT,
    ORIGINAL_REQUEST_AUTHORITY_ID,
    QWEN_QLORA_RUN_ID,
    RECOVERY_PHOBERT_RUN_ID,
    RECOVERY_REQUEST_AUTHORITY_ID,
    build_phase40_final_comparison_authority,
    freeze_phase40_final_comparison_authority,
    load_frozen_phase40_final_comparison_authority,
)


_SOURCE_REPO = Path(__file__).resolve().parents[2]


def _canonical_json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def _copy_relative(source_root: Path, destination_root: Path, relative: str) -> None:
    source = source_root / PurePosixPath(relative)
    destination = destination_root / PurePosixPath(relative)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def _write_recovery_request(
    *,
    original: handoff.RunRequest,
    source_bundle: handoff.SourceBundleReference,
    capsule_root: Path,
) -> handoff.RunRequest:
    payload = original.model_dump(mode="json")
    payload["source_bundle"] = source_bundle.model_dump(mode="json")
    payload["runs"][2]["run_id"] = RECOVERY_PHOBERT_RUN_ID

    old_template = payload["control_template_by_run"].pop(
        "phase40-phobert-full-seed42-v1"
    )
    for entry in old_template["controls_without_accelerator"]["additional_controls"]:
        if entry["name"] == "source_archive_sha256":
            entry["value"] = source_bundle.archive_sha256
        elif entry["name"] == "source_inventory_sha256":
            entry["value"] = source_bundle.inventory_sha256
    recovery_template = handoff.RequestedControlTemplate.model_validate(old_template)
    payload["control_template_by_run"][RECOVERY_PHOBERT_RUN_ID] = (
        recovery_template.model_dump(mode="json")
    )
    payload["control_template_digest_by_run"].pop(
        "phase40-phobert-full-seed42-v1"
    )
    payload["control_template_digest_by_run"][RECOVERY_PHOBERT_RUN_ID] = (
        recovery_template.sha256
    )
    recovery = handoff.RunRequest.model_validate(payload)
    destination = capsule_root / PurePosixPath(FIXED_ORIGINAL_REQUEST_PATH)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(_canonical_json_bytes(recovery.model_dump(mode="json")))
    return recovery


@pytest.fixture()
def authority_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()

    fixed_upstream_files = (
        FIXED_ORIGINAL_REQUEST_PATH,
        handoff.FIXED_SOURCE_ARCHIVE_PATH,
        handoff.FIXED_SOURCE_INVENTORY_PATH,
        handoff.FIXED_INPUT_REPOSITORY_PATH,
        FIXED_HISTORICAL_SCOPE_AMENDMENT_PATH,
        *(f"{handoff.FIXED_LORA_PROBE_ROOT}/{name}" for name in handoff.FIXED_LORA_PROBE_FILES),
    )
    for relative in fixed_upstream_files:
        _copy_relative(_SOURCE_REPO, repo, relative)
    for relative in handoff.PHASE40_COMPARISON_FINALIZER_SOURCE_ALLOWLIST:
        _copy_relative(_SOURCE_REPO, repo, relative)

    original = handoff.load_frozen_phase40_run_request(repo_root=repo)
    capsule = repo / PurePosixPath(FIXED_PHOBERT_V12_CAPSULE_ROOT)
    capsule.mkdir(parents=True)
    for relative in handoff.PHASE40_SOURCE_ALLOWLIST:
        _copy_relative(_SOURCE_REPO, capsule, relative)
    # Ensure the recovery source is independently identified while retaining
    # the exact code-fixed inventory.  No data member is changed or discovered.
    recovery_pyproject = capsule / "pyproject.toml"
    recovery_pyproject.write_bytes(
        recovery_pyproject.read_bytes() + b"\n# phobert recovery fixture\n"
    )
    recovery_source = handoff.build_phase40_source_bundle(
        capsule,
        capsule / PurePosixPath(handoff.FIXED_SOURCE_ARCHIVE_PATH).parent,
    )
    _copy_relative(
        _SOURCE_REPO,
        capsule,
        handoff.FIXED_INPUT_REPOSITORY_PATH,
    )
    recovery = _write_recovery_request(
        original=original,
        source_bundle=recovery_source.reference,
        capsule_root=capsule,
    )
    recovery_bytes = _canonical_json_bytes(recovery.model_dump(mode="json"))
    monkeypatch.setattr(
        final_authority,
        "EXPECTED_RECOVERY_REQUEST_SHA256",
        final_authority._sha256(recovery_bytes),
    )
    monkeypatch.setattr(
        final_authority,
        "EXPECTED_RECOVERY_SOURCE_ARCHIVE_SHA256",
        recovery_source.reference.archive_sha256,
    )
    monkeypatch.setattr(
        final_authority,
        "EXPECTED_RECOVERY_SOURCE_INVENTORY_SHA256",
        recovery_source.reference.inventory_sha256,
    )
    return repo


def test_build_freeze_load_derives_per_run_authorities(authority_repo: Path) -> None:
    authority = build_phase40_final_comparison_authority(repo_root=authority_repo)
    assert tuple(item.authority_id for item in authority.request_authorities) == (
        ORIGINAL_REQUEST_AUTHORITY_ID,
        RECOVERY_REQUEST_AUTHORITY_ID,
    )
    assert authority.shared_input_authority == (
        handoff.load_frozen_phase40_run_request(repo_root=authority_repo).input_bundle
    )
    # The old source pin is historical only; the new live authority supersedes
    # it without mutating or pretending to revalidate those old source bytes.
    historical = json.loads(
        (authority_repo / FIXED_HISTORICAL_SCOPE_AMENDMENT_PATH).read_text(
            encoding="utf-8"
        )
    )
    assert (
        historical["comparison_finalizer_authority"]["source_tree_sha256"]
        != authority.comparison_finalizer_authority.source_tree_sha256
    )

    frozen = freeze_phase40_final_comparison_authority(repo_root=authority_repo)
    assert frozen == authority_repo / PurePosixPath(
        FIXED_FINAL_COMPARISON_AUTHORITY_PATH
    )
    verified = load_frozen_phase40_final_comparison_authority(
        repo_root=authority_repo
    )
    assert tuple(verified.by_run_id) == (
        QWEN_QLORA_RUN_ID,
        RECOVERY_PHOBERT_RUN_ID,
    )
    assert verified.by_run_id[QWEN_QLORA_RUN_ID].origin.authority_id == (
        ORIGINAL_REQUEST_AUTHORITY_ID
    )
    assert verified.by_run_id[RECOVERY_PHOBERT_RUN_ID].origin.authority_id == (
        RECOVERY_REQUEST_AUTHORITY_ID
    )
    assert (
        verified.by_run_id[QWEN_QLORA_RUN_ID].transfer_authority
        != verified.by_run_id[RECOVERY_PHOBERT_RUN_ID].transfer_authority
    )
    assert (
        verified.by_run_id[RECOVERY_PHOBERT_RUN_ID].control_template.sha256
        == verified.recovery_request.control_template_digest_by_run[
            RECOVERY_PHOBERT_RUN_ID
        ]
    )


def test_public_apis_accept_no_authority_or_capsule_path(authority_repo: Path) -> None:
    assert tuple(inspect.signature(build_phase40_final_comparison_authority).parameters) == (
        "repo_root",
    )
    assert tuple(inspect.signature(freeze_phase40_final_comparison_authority).parameters) == (
        "repo_root",
    )
    assert tuple(
        inspect.signature(load_frozen_phase40_final_comparison_authority).parameters
    ) == ("repo_root",)
    freeze_phase40_final_comparison_authority(repo_root=authority_repo)


@pytest.mark.parametrize("malformation", ("extra", "noncanonical", "duplicate"))
def test_loader_rejects_noncanonical_or_extra_authority_fields(
    authority_repo: Path,
    malformation: str,
) -> None:
    path = freeze_phase40_final_comparison_authority(repo_root=authority_repo)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if malformation == "extra":
        payload["comparison_launch_receipt_sha256"] = "0" * 64
        path.write_bytes(_canonical_json_bytes(payload))
    elif malformation == "noncanonical":
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    else:
        raw = path.read_text(encoding="utf-8")
        path.write_text(
            raw.replace(
                '{"comparison_finalizer_authority":',
                '{"schema_version":"phase40-final-comparison-authority-v1",'
                '"comparison_finalizer_authority":',
                1,
            ),
            encoding="utf-8",
        )
    with pytest.raises((ValueError, RuntimeError)):
        load_frozen_phase40_final_comparison_authority(repo_root=authority_repo)


def test_loader_rejects_request_hash_not_matching_fixed_capsule(
    authority_repo: Path,
) -> None:
    path = freeze_phase40_final_comparison_authority(repo_root=authority_repo)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["request_authorities"][1]["request_sha256"] = "0" * 64
    path.write_bytes(_canonical_json_bytes(payload))
    with pytest.raises(ValueError, match="request hashes"):
        load_frozen_phase40_final_comparison_authority(repo_root=authority_repo)


def test_recovery_request_rejects_phobert_non_source_control_delta(
    authority_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    capsule_request = (
        authority_repo
        / PurePosixPath(FIXED_PHOBERT_V12_CAPSULE_ROOT)
        / PurePosixPath(FIXED_ORIGINAL_REQUEST_PATH)
    )
    payload = json.loads(capsule_request.read_text(encoding="utf-8"))
    template = payload["control_template_by_run"][RECOVERY_PHOBERT_RUN_ID]
    template["controls_without_accelerator"]["max_sequence_length"] = 128
    typed_template = handoff.RequestedControlTemplate.model_validate(template)
    payload["control_template_by_run"][RECOVERY_PHOBERT_RUN_ID] = (
        typed_template.model_dump(mode="json")
    )
    payload["control_template_digest_by_run"][RECOVERY_PHOBERT_RUN_ID] = (
        typed_template.sha256
    )
    request = handoff.RunRequest.model_validate(payload)
    mutated = _canonical_json_bytes(request.model_dump(mode="json"))
    capsule_request.write_bytes(mutated)
    # Let this test exercise the independent structural delta gate; a separate
    # test covers rejection by the presealed exact request identity.
    monkeypatch.setattr(
        final_authority,
        "EXPECTED_RECOVERY_REQUEST_SHA256",
        final_authority._sha256(mutated),
    )
    with pytest.raises(ValueError, match="beyond the two source hashes"):
        build_phase40_final_comparison_authority(repo_root=authority_repo)


def test_recovery_request_rejects_qwen_template_drift(
    authority_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    capsule_request = (
        authority_repo
        / PurePosixPath(FIXED_PHOBERT_V12_CAPSULE_ROOT)
        / PurePosixPath(FIXED_ORIGINAL_REQUEST_PATH)
    )
    payload = json.loads(capsule_request.read_text(encoding="utf-8"))
    for run_id in ("phase40-qwen-lora-full-seed42-v1", QWEN_QLORA_RUN_ID):
        template = payload["control_template_by_run"][run_id]
        template["controls_without_accelerator"]["optimizer"]["learning_rate"] = 0.0001
        typed_template = handoff.RequestedControlTemplate.model_validate(template)
        payload["control_template_by_run"][run_id] = typed_template.model_dump(
            mode="json"
        )
        payload["control_template_digest_by_run"][run_id] = typed_template.sha256
    request = handoff.RunRequest.model_validate(payload)
    mutated = _canonical_json_bytes(request.model_dump(mode="json"))
    capsule_request.write_bytes(mutated)
    monkeypatch.setattr(
        final_authority,
        "EXPECTED_RECOVERY_REQUEST_SHA256",
        final_authority._sha256(mutated),
    )
    with pytest.raises(ValueError, match="changed Qwen controls"):
        build_phase40_final_comparison_authority(repo_root=authority_repo)


def test_live_finalizer_source_drift_invalidates_frozen_authority(
    authority_repo: Path,
) -> None:
    freeze_phase40_final_comparison_authority(repo_root=authority_repo)
    source = authority_repo / "pyproject.toml"
    source.write_bytes(source.read_bytes() + b"\n# post-freeze drift\n")
    with pytest.raises(ValueError, match="local comparison finalizer source differs"):
        load_frozen_phase40_final_comparison_authority(repo_root=authority_repo)


def test_active_authority_rejects_unbound_local_import_before_freeze(
    authority_repo: Path,
) -> None:
    entrypoint = authority_repo / "src/model_adaptation/phase40_finalize.py"
    entrypoint.write_bytes(
        entrypoint.read_bytes()
        + b"\nimport src.model_adaptation.phase41_evaluation\n"
    )

    with pytest.raises(ValueError, match="imports an unbound local module"):
        build_phase40_final_comparison_authority(repo_root=authority_repo)
    assert not (
        authority_repo / PurePosixPath(FIXED_FINAL_COMPARISON_AUTHORITY_PATH)
    ).exists()


def test_freezer_allows_identical_replay_but_never_replaces(authority_repo: Path) -> None:
    path = freeze_phase40_final_comparison_authority(repo_root=authority_repo)
    assert freeze_phase40_final_comparison_authority(repo_root=authority_repo) == path
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(RuntimeError, match="refusing to replace"):
        freeze_phase40_final_comparison_authority(repo_root=authority_repo)


def test_live_recovery_capsule_matches_presealed_exact_identities() -> None:
    authority = build_phase40_final_comparison_authority(repo_root=_SOURCE_REPO)
    by_id = {entry.authority_id: entry for entry in authority.request_authorities}
    assert (
        by_id[ORIGINAL_REQUEST_AUTHORITY_ID].request_sha256
        == final_authority.EXPECTED_ORIGINAL_REQUEST_SHA256
    )
    assert (
        by_id[RECOVERY_REQUEST_AUTHORITY_ID].request_sha256
        == final_authority.EXPECTED_RECOVERY_REQUEST_SHA256
    )
