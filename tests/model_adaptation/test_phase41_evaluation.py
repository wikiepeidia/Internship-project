"""Synthetic-only tests for the irreversible Phase 41 evaluation boundary."""

from __future__ import annotations

from contextlib import contextmanager
import hashlib
import inspect
import json
import os
from pathlib import Path

import pytest

import src.model_adaptation.phase41_evaluation as phase41_evaluation
from src.model_adaptation.phase41_evaluation import (
    EXPLICIT_AUTHORIZATION_STATEMENT,
    AlreadySpentError,
    ContractError,
    FrozenModelIdentity,
    OpaqueHeldOutAuthority,
    Prediction,
    authorize_phase41_evaluation,
    freeze_deployment_fit_disposition,
    prepare_phase41_evaluation,
    run_phase41_once,
    verify_phase41_evidence,
    verify_phase41_preauthorization,
    _phase41_test_runtime,
)
from src.model_adaptation.phase41_protocols import (
    FrozenPhoBertPredictor,
    FrozenQwenPredictor,
    build_synthetic_protocol_authority,
)


LABELS = (
    "bank_impersonation",
    "zalo_social_engineering",
    "task_scam",
    "benign",
)


def _payload() -> bytes:
    rows = []
    for index, label in enumerate(LABELS):
        rows.append(
            {
                "text": f"synthetic message {index}",
                "label": label,
                "risk_tier": "benign" if label == "benign" else "high-risk",
                "suspicious_spans": [],
                "xai_explanation": "synthetic fixture",
                "source": "synthetic_test",
                "seed_id": f"synthetic-seed-{index}",
            }
        )
    return b"".join(
        json.dumps(row, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
        + b"\n"
        for row in rows
    )


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


def _models() -> tuple[FrozenModelIdentity, FrozenModelIdentity]:
    return (
        FrozenModelIdentity(
            role="qwen",
            run_id="qwen-synthetic",
            model_family="qwen",
            adaptation_mode="qlora",
            artifact_sha256="1" * 64,
            selected_checkpoint_identity=f"adapter-state-sha256:{'2' * 64}",
        ),
        FrozenModelIdentity(
            role="phobert",
            run_id="phobert-synthetic",
            model_family="phobert",
            adaptation_mode="classification_head",
            artifact_sha256="3" * 64,
            selected_checkpoint_identity=f"model-state-sha256:{'4' * 64}",
        ),
    )


def _authority(path: Path, payload: bytes) -> OpaqueHeldOutAuthority:
    return OpaqueHeldOutAuthority(
        path=str(path),
        records=4,
        bytes=len(payload),
        sha256=hashlib.sha256(payload).hexdigest(),
        label_counts=tuple((label, 1) for label in LABELS),
    )


def _predictor_rows(snapshot):
    return tuple(
        Prediction(row_id=row.row_id, predicted_state=LABELS[row.sequence_index], raw_output=LABELS[row.sequence_index])
        for row in snapshot.rows
    )


def _prepare_authorize(root: Path, split: Path, payload: bytes):
    protocols = build_synthetic_protocol_authority(_models())
    prepared = prepare_phase41_evaluation(
        root,
        held_out=_authority(split, payload),
        models=_models(),
        protocols=protocols,
        comparison_authority_sha256="5" * 64,
        review_closure_sha256="6" * 64,
        comparison_launch_receipt_sha256="7" * 64,
        execution_source_manifest_sha256="8" * 64,
        prior_human_exposure_disclosed=True,
        deployment_fit_choice="deferred",
    )
    assert verify_phase41_preauthorization(root).prepared_sha256 == prepared.prepared_sha256
    authorize_phase41_evaluation(
        root,
        prepared_sha256=prepared.prepared_sha256,
        statement=EXPLICIT_AUTHORIZATION_STATEMENT,
    )
    return protocols


def test_synthetic_pass_is_claim_before_open_shared_snapshot_and_byte_stable(tmp_path):
    root = tmp_path / "phase41"
    split = tmp_path / "synthetic-held-out.jsonl"
    payload = _payload()
    split.write_bytes(payload)
    protocols = _prepare_authorize(root, split, payload)
    events: list[str] = []
    seen_snapshots: list[int] = []

    def qwen(snapshot):
        events.append("qwen")
        seen_snapshots.append(id(snapshot))
        return _predictor_rows(snapshot)

    def phobert(snapshot):
        events.append("phobert")
        seen_snapshots.append(id(snapshot))
        return _predictor_rows(snapshot)

    with _phase41_test_runtime(registry_root=tmp_path / "machine-claims", event_sink=events):
        manifest = run_phase41_once(
            root,
            FrozenQwenPredictor(protocols.qwen, qwen),
            FrozenPhoBertPredictor(protocols.phobert, phobert),
        )
        freeze_deployment_fit_disposition(root)
        before = {path.name: path.read_bytes() for path in root.iterdir() if path.is_file()}
        assert verify_phase41_evidence(root) == verify_phase41_evidence(root)
        after = {path.name: path.read_bytes() for path in root.iterdir() if path.is_file()}

    assert events.index("claim_durable") < events.index("handle_acquired")
    assert events.count("handle_acquired") == 1
    assert events.count("payload_read") == 1
    assert events[-2:] == ["qwen", "phobert"]
    assert seen_snapshots[0] == seen_snapshots[1]
    assert manifest.status == "completed"
    assert before == after


def test_post_claim_failure_is_permanently_spent_before_retry_callbacks(tmp_path):
    root = tmp_path / "phase41"
    split = tmp_path / "synthetic-held-out.jsonl"
    payload = _payload()
    split.write_bytes(payload)
    protocols = _prepare_authorize(root, split, payload)
    registry = tmp_path / "machine-claims"

    def fail(_snapshot):
        raise RuntimeError("synthetic predictor failure")

    with _phase41_test_runtime(registry_root=registry):
        with pytest.raises(RuntimeError, match="synthetic predictor failure"):
            run_phase41_once(
                root,
                FrozenQwenPredictor(protocols.qwen, fail),
                FrozenPhoBertPredictor(protocols.phobert, _predictor_rows),
            )
        terminal = json.loads((root / "terminal.json").read_text(encoding="utf-8"))
        assert terminal["status"] == "spent_failed"
        assert terminal["failure_stage"] == "qwen_prediction"
        assert "synthetic predictor failure" not in json.dumps(terminal)
        with pytest.raises(AlreadySpentError):
            run_phase41_once(
                root,
                FrozenQwenPredictor(protocols.qwen, _predictor_rows),
                FrozenPhoBertPredictor(protocols.phobert, _predictor_rows),
            )


def test_deployment_fit_disposition_reproduces_precommitted_choice(tmp_path):
    root = tmp_path / "phase41"
    split = tmp_path / "synthetic-held-out.jsonl"
    payload = _payload()
    split.write_bytes(payload)
    protocols = _prepare_authorize(root, split, payload)
    with _phase41_test_runtime(registry_root=tmp_path / "machine-claims"):
        run_phase41_once(
            root,
            FrozenQwenPredictor(protocols.qwen, _predictor_rows),
            FrozenPhoBertPredictor(protocols.phobert, _predictor_rows),
        )
        with pytest.raises(ContractError, match="disposition is mandatory"):
            verify_phase41_evidence(root)
        path = freeze_deployment_fit_disposition(root)
        verify_phase41_evidence(root)
    body = json.loads(path.read_text(encoding="utf-8"))
    assert body["choice"] == "deferred"
    assert body["terminal_sha256"] == hashlib.sha256(
        (root / "terminal.json").read_bytes()
    ).hexdigest()
    assert body["protected_completion_seal_sha256"] == hashlib.sha256(
        (root / "protected-completion-seal.json").read_bytes()
    ).hexdigest()
    assert body["unbiased_test_score_claim"] is False
    assert body["test_outcome_used_for_tuning"] is False


def test_public_run_and_verify_signatures_have_no_opener_registry_or_split_override():
    run_parameters = set(inspect.signature(run_phase41_once).parameters)
    verify_parameters = set(inspect.signature(verify_phase41_evidence).parameters)
    assert run_parameters == {"output_root", "qwen", "phobert"}
    assert verify_parameters == {"output_root"}
    assert {"opener", "registry", "split_path", "retry"}.isdisjoint(run_parameters)


def test_private_test_and_low_level_execution_seams_are_not_exported():
    exported = set(phase41_evaluation.__all__)
    assert {
        "_phase41_test_runtime",
        "_run_once",
        "_owned_split_opener",
        "prepare_evaluation",
        "authorize_evaluation",
        "verify_only",
    }.isdisjoint(exported)


def test_synthetic_predictors_cannot_enter_production_execution_mode(tmp_path):
    protocols = build_synthetic_protocol_authority(_models())
    qwen = FrozenQwenPredictor(protocols.qwen, _predictor_rows)
    phobert = FrozenPhoBertPredictor(protocols.phobert, _predictor_rows)
    with pytest.raises(ContractError, match="production run requires loader-created"):
        phase41_evaluation._validate_predictor_entry_mode(qwen, phobert)
    with _phase41_test_runtime(registry_root=tmp_path / "machine-claims"):
        phase41_evaluation._validate_predictor_entry_mode(qwen, phobert)


def test_programdata_environment_cannot_redirect_machine_registry(tmp_path, monkeypatch):
    known_folder = tmp_path / "trusted-program-data"
    monkeypatch.setenv("ProgramData", os.fspath(tmp_path / "hostile-redirect"))
    monkeypatch.setattr(
        phase41_evaluation, "_known_program_data_root", lambda: known_folder
    )
    assert phase41_evaluation._claim_registry_root() == (
        known_folder / "VNPhish" / "phase41-one-shot-claims"
    )


def test_claim_registry_acl_requires_protected_exact_trusted_writers():
    operator = "S-1-5-21-1000"
    trusted = (
        phase41_evaluation._RegistryAce(operator, 0x2, True, False),
        phase41_evaluation._RegistryAce("S-1-5-18", 0x2, True, False),
        phase41_evaluation._RegistryAce("S-1-5-32-544", 0x2, True, False),
    )
    phase41_evaluation._validate_registry_acl_snapshot(
        owner_sid=operator,
        dacl_protected=True,
        aces=trusted,
        operator_sid=operator,
    )
    with pytest.raises(ContractError, match="DACL must be protected"):
        phase41_evaluation._validate_registry_acl_snapshot(
            owner_sid=operator,
            dacl_protected=False,
            aces=trusted,
            operator_sid=operator,
        )
    with pytest.raises(ContractError, match="inherited"):
        phase41_evaluation._validate_registry_acl_snapshot(
            owner_sid=operator,
            dacl_protected=True,
            aces=trusted
            + (phase41_evaluation._RegistryAce(operator, 0x1, True, True),),
            operator_sid=operator,
        )
    with pytest.raises(ContractError, match="another SID"):
        phase41_evaluation._validate_registry_acl_snapshot(
            owner_sid=operator,
            dacl_protected=True,
            aces=trusted
            + (
                phase41_evaluation._RegistryAce(
                    "S-1-5-21-ATTACKER", 0x2, True, False
                ),
            ),
            operator_sid=operator,
        )


@pytest.mark.parametrize(
    "preexisting_name",
    (
        "evaluation-access-receipt.json",
        "evidence-manifest.json",
        "protected-completion-seal.json",
        "terminal.json",
        "deployment-fit-disposition.json",
    ),
)
def test_all_late_evidence_names_are_reserved_before_durable_claim(
    tmp_path, preexisting_name
):
    root = tmp_path / "phase41"
    split = tmp_path / "synthetic.jsonl"
    payload = _payload()
    split.write_bytes(payload)
    protocols = _prepare_authorize(root, split, payload)
    (root / preexisting_name).write_bytes(b"hostile preclaim payload")
    registry = tmp_path / "machine-claims"
    with _phase41_test_runtime(registry_root=registry):
        with pytest.raises(ContractError, match="pre-claim output already exists"):
            run_phase41_once(
                root,
                FrozenQwenPredictor(protocols.qwen, _predictor_rows),
                FrozenPhoBertPredictor(protocols.phobert, _predictor_rows),
            )
    assert not (registry / f"{hashlib.sha256(payload).hexdigest()}.claim.json").exists()


def test_completion_terminal_is_written_after_every_other_local_evidence(
    tmp_path, monkeypatch
):
    root = tmp_path / "phase41"
    split = tmp_path / "synthetic.jsonl"
    payload = _payload()
    split.write_bytes(payload)
    protocols = _prepare_authorize(root, split, payload)
    writes: list[str] = []
    real_write = phase41_evaluation._exclusive_write

    def recording_write(path: Path, content: bytes) -> Path:
        writes.append(path.name)
        return real_write(path, content)

    monkeypatch.setattr(phase41_evaluation, "_exclusive_write", recording_write)
    with _phase41_test_runtime(registry_root=tmp_path / "machine-claims"):
        run_phase41_once(
            root,
            FrozenQwenPredictor(protocols.qwen, _predictor_rows),
            FrozenPhoBertPredictor(protocols.phobert, _predictor_rows),
        )
    assert writes[-1] == "terminal.json"
    assert writes.index("evaluation-access-receipt.json") < writes.index(
        "evidence-manifest.json"
    )
    assert writes.index("evidence-manifest.json") < writes.index(
        "protected-completion-seal.json"
    )


def test_completion_evidence_failure_freezes_spent_failed_not_completed(
    tmp_path, monkeypatch
):
    root = tmp_path / "phase41"
    split = tmp_path / "synthetic.jsonl"
    payload = _payload()
    split.write_bytes(payload)
    protocols = _prepare_authorize(root, split, payload)
    registry = tmp_path / "machine-claims"
    real_write = phase41_evaluation._exclusive_write

    def fail_manifest(path: Path, content: bytes) -> Path:
        if path.name == "evidence-manifest.json":
            raise OSError("synthetic evidence persistence failure")
        return real_write(path, content)

    monkeypatch.setattr(phase41_evaluation, "_exclusive_write", fail_manifest)
    with _phase41_test_runtime(registry_root=registry):
        with pytest.raises(OSError, match="synthetic evidence persistence failure"):
            run_phase41_once(
                root,
                FrozenQwenPredictor(protocols.qwen, _predictor_rows),
                FrozenPhoBertPredictor(protocols.phobert, _predictor_rows),
            )
    terminal = json.loads((root / "terminal.json").read_text(encoding="utf-8"))
    assert terminal["status"] == "spent_failed"
    assert terminal["failure_stage"] == "freeze_completion_evidence"
    assert not (root / "protected-completion-seal.json").exists()
    assert (registry / f"{hashlib.sha256(payload).hexdigest()}.claim.json").is_file()


def test_fixed_evidence_inventory_rejects_traversal_before_artifact_access(tmp_path):
    sentinel = tmp_path / "sentinel"
    sentinel.write_bytes(b"must-not-be-read")
    with pytest.raises(ContractError, match="fixed allowlist"):
        phase41_evaluation._artifact_hashes(
            tmp_path / "output", ("../sentinel",)
        )
    assert sentinel.read_bytes() == b"must-not-be-read"


def test_protected_machine_seal_rejects_consistent_local_evidence_reseal(tmp_path):
    root = tmp_path / "phase41"
    split = tmp_path / "synthetic.jsonl"
    payload = _payload()
    split.write_bytes(payload)
    protocols = _prepare_authorize(root, split, payload)
    with _phase41_test_runtime(registry_root=tmp_path / "machine-claims"):
        run_phase41_once(
            root,
            FrozenQwenPredictor(protocols.qwen, _predictor_rows),
            FrozenPhoBertPredictor(protocols.phobert, _predictor_rows),
        )

        results_path = root / "results.json"
        results = json.loads(results_path.read_text(encoding="utf-8"))
        results["comparison_statements"] = ["forged local comparison"]
        results_bytes = _canonical_bytes(results)
        results_path.write_bytes(results_bytes)

        manifest_path = root / "evidence-manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for row in manifest["artifacts"]:
            if row["name"] == "results.json":
                row["sha256"] = hashlib.sha256(results_bytes).hexdigest()
        manifest_bytes = _canonical_bytes(manifest)
        manifest_path.write_bytes(manifest_bytes)

        terminal_path = root / "terminal.json"
        terminal = json.loads(terminal_path.read_text(encoding="utf-8"))
        terminal["results_sha256"] = hashlib.sha256(results_bytes).hexdigest()
        terminal["evidence_manifest_sha256"] = hashlib.sha256(
            manifest_bytes
        ).hexdigest()
        terminal_bytes = _canonical_bytes(terminal)
        terminal_path.write_bytes(terminal_bytes)

        local_seal_path = root / "protected-completion-seal.json"
        local_seal = json.loads(local_seal_path.read_text(encoding="utf-8"))
        local_seal["artifacts"] = manifest["artifacts"]
        local_seal["evidence_manifest_sha256"] = hashlib.sha256(
            manifest_bytes
        ).hexdigest()
        local_seal["terminal_sha256"] = hashlib.sha256(terminal_bytes).hexdigest()
        local_seal_path.write_bytes(_canonical_bytes(local_seal))

        with pytest.raises(ContractError, match="local and protected completion seals differ"):
            verify_phase41_evidence(root)


def test_same_content_at_another_path_and_output_root_cannot_replay(tmp_path):
    payload = _payload()
    first_split = tmp_path / "first.jsonl"
    copied_split = tmp_path / "copied.jsonl"
    first_split.write_bytes(payload)
    copied_split.write_bytes(payload)
    first_root = tmp_path / "first-output"
    copied_root = tmp_path / "copied-output"
    first_protocols = _prepare_authorize(first_root, first_split, payload)
    copied_protocols = _prepare_authorize(copied_root, copied_split, payload)
    registry = tmp_path / "machine-claims"
    with _phase41_test_runtime(registry_root=registry):
        run_phase41_once(
            first_root,
            FrozenQwenPredictor(first_protocols.qwen, _predictor_rows),
            FrozenPhoBertPredictor(first_protocols.phobert, _predictor_rows),
        )
        with pytest.raises(AlreadySpentError):
            run_phase41_once(
                copied_root,
                FrozenQwenPredictor(copied_protocols.qwen, _predictor_rows),
                FrozenPhoBertPredictor(copied_protocols.phobert, _predictor_rows),
            )
    assert not (copied_root / "evaluation-access-receipt.json").exists()


def test_access_receipt_proves_one_handle_and_read_without_content(tmp_path):
    root = tmp_path / "phase41"
    split = tmp_path / "synthetic.jsonl"
    payload = _payload()
    split.write_bytes(payload)
    protocols = _prepare_authorize(root, split, payload)
    with _phase41_test_runtime(registry_root=tmp_path / "machine-claims"):
        run_phase41_once(
            root,
            FrozenQwenPredictor(protocols.qwen, _predictor_rows),
            FrozenPhoBertPredictor(protocols.phobert, _predictor_rows),
        )
    receipt = json.loads((root / "evaluation-access-receipt.json").read_text(encoding="utf-8"))
    assert receipt["handle_acquisitions"] == 1
    assert receipt["sequential_payload_reads"] == 1
    assert receipt["raw_content_retained"] is False
    serialized = json.dumps(receipt)
    assert "synthetic message" not in serialized
    assert "volume_serial_number" in receipt
    assert "file_identity" in receipt


@pytest.mark.skipif(not hasattr(Path, "is_junction"), reason="Windows path checks required")
def test_alternate_data_stream_is_rejected_before_durable_claim(tmp_path):
    base = tmp_path / "ads-base.jsonl"
    base.write_bytes(b"base")
    ads = Path(f"{base}:phase41")
    payload = _payload()
    ads.write_bytes(payload)
    root = tmp_path / "phase41"
    with pytest.raises(ContractError, match="alternate data stream"):
        _prepare_authorize(root, ads, payload)
    assert not (root / "one-shot-claim.json").exists()
    assert not (root / "terminal.json").exists()
