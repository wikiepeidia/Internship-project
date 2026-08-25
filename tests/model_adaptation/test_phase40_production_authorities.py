"""Synthetic-only tests for the Phase 40 production authority closure."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
import inspect
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.model_adaptation import phase40_production_authorities as production
from src.model_adaptation import phase40_final_authority as final_authority


COMPARISON_SHA = "1" * 64
QWEN_RECEIPT_SHA = "2" * 64
PHOBERT_RECEIPT_SHA = "3" * 64
PHOBERT_TOKENIZER_SHA = "b" * 64
SEGMENTER_SHA = "4" * 64
RUNTIME_SHA = "5" * 64
RUNTIME_MATERIALIZATION_RECEIPT_SHA = "c" * 64
QWEN_CHECKPOINT = f"adapter-state-sha256:{'6' * 64}"
PHOBERT_CHECKPOINT = f"model-state-sha256:{'7' * 64}"
PHOBERT_ARTIFACT_SHA = "8" * 64
REQUEST_SHA = "9" * 64
FINAL_AUTHORITY_SHA = "a" * 64


def _canonical_json(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def _roots(tmp_path: Path) -> tuple[Path, Path, Path]:
    repository = tmp_path / "repository"
    qwen = tmp_path / "qwen-export"
    phobert = tmp_path / "phobert-transfer"
    for root in (repository, qwen, phobert):
        root.mkdir()
    runtime = repository / production.RUNTIME_DEPENDENCY_AUTHORITY_RELATIVE_PATH
    runtime.parent.mkdir(parents=True)
    runtime.write_bytes(b"synthetic-runtime-authority")
    receipt = repository / production.QWEN_GGUF_VERIFICATION_RECEIPT_RELATIVE_PATH
    receipt.write_bytes(
        _canonical_json(
            {
                "upstream": {
                    "final_comparison_authority_sha256": FINAL_AUTHORITY_SHA,
                    "origin_request_sha256": REQUEST_SHA,
                },
                "selection": {
                    "run_id": "phase40-qwen-qlora-full-seed42-v1",
                    "selected_checkpoint": {
                        "artifact_identity": QWEN_CHECKPOINT,
                    },
                },
            }
        )
    )
    (qwen / production.QWEN_GGUF_EXPORT_MANIFEST_RELATIVE_PATH).write_bytes(
        b"synthetic-manifest"
    )
    return repository, qwen, phobert


def _install_successful_verifiers(monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    calls: dict[str, object] = {}

    def verify_comparison(*, repo_root: Path):
        calls["comparison"] = repo_root
        return {"receipt_sha256": COMPARISON_SHA}

    def load_runtime(path: Path):
        calls["runtime"] = path
        return SimpleNamespace(
            segmenter_sha256=SEGMENTER_SHA,
            authority_sha256=RUNTIME_SHA,
        )

    def load_runtime_materialization(*, repo_root: Path):
        calls["runtime_materialization"] = repo_root
        return {
            "receipt_sha256": RUNTIME_MATERIALIZATION_RECEIPT_SHA,
            "authority": {"authority_sha256": RUNTIME_SHA},
        }

    def verify_qwen(
        *,
        repo_root: Path,
        export_manifest_path: Path,
        context,
    ):
        calls["qwen"] = (repo_root, export_manifest_path, context)
        return {
            "receipt_sha256": QWEN_RECEIPT_SHA,
            "selection": {
                "selected_checkpoint": {
                    "artifact_identity": QWEN_CHECKPOINT,
                }
            },
        }

    def verify_phobert(*, repo_root: Path, transfer_root: Path):
        calls["phobert"] = (repo_root, transfer_root)
        return SimpleNamespace(
            receipt=SimpleNamespace(
                authority_sha256=PHOBERT_RECEIPT_SHA,
                tokenizer_sha256=PHOBERT_TOKENIZER_SHA,
                selected_checkpoint_identity=PHOBERT_CHECKPOINT,
                selected_artifact_sha256=PHOBERT_ARTIFACT_SHA,
            )
        )

    monkeypatch.setattr(
        production,
        "verify_phase40_comparison_launch_receipt",
        verify_comparison,
    )
    monkeypatch.setattr(production, "load_runtime_dependency_authority", load_runtime)
    monkeypatch.setattr(
        production,
        "load_runtime_materialization_receipt",
        load_runtime_materialization,
    )
    monkeypatch.setattr(
        production,
        "verify_phase40_qwen_gguf_verification_receipt",
        verify_qwen,
    )
    monkeypatch.setattr(
        production,
        "verify_phobert_release_bundle",
        verify_phobert,
    )
    monkeypatch.setattr(
        production,
        "load_phase40_qwen_gguf_verification_receipt",
        lambda *, repo_root: {
            "receipt_sha256": QWEN_RECEIPT_SHA,
            "selection": {
                "selected_checkpoint": {
                    "artifact_identity": QWEN_CHECKPOINT,
                }
            },
        },
    )
    monkeypatch.setattr(
        production,
        "load_phobert_release_receipt",
        lambda *, repo_root: SimpleNamespace(
            upstream={
                "final_comparison_authority_sha256": FINAL_AUTHORITY_SHA,
                "origin_run_request_sha256": "b" * 64,
            },
            selected_run_id="phase40-phobert-full-seed42-v12",
            authority_sha256=PHOBERT_RECEIPT_SHA,
            tokenizer_sha256=PHOBERT_TOKENIZER_SHA,
            selected_checkpoint_identity=PHOBERT_CHECKPOINT,
            selected_artifact_sha256=PHOBERT_ARTIFACT_SHA,
        ),
    )
    return calls


def test_verifies_only_code_fixed_descendants_and_returns_frozen_closure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, qwen_root, phobert_root = _roots(tmp_path)
    calls = _install_successful_verifiers(monkeypatch)

    verified = production.verify_phase40_production_authorities(
        repo_root=repository,
        qwen_export_root=qwen_root,
        phobert_transfer_root=phobert_root,
    )

    assert verified.as_dict() == {
        "verification_mode": production.EXTERNAL_MODELS_PORTABLE_RUNTIME,
        "comparison_launch_receipt_sha256": COMPARISON_SHA,
        "qwen_gguf_verification_receipt_sha256": QWEN_RECEIPT_SHA,
        "phobert_release_receipt_authority_sha256": PHOBERT_RECEIPT_SHA,
        "phobert_segmenter_authority_sha256": SEGMENTER_SHA,
        "runtime_dependency_authority_sha256": RUNTIME_SHA,
        "runtime_materialization_receipt_sha256": (
            RUNTIME_MATERIALIZATION_RECEIPT_SHA
        ),
        "qwen_selected_checkpoint_identity": QWEN_CHECKPOINT,
        "phobert_selected_checkpoint_identity": PHOBERT_CHECKPOINT,
        "phobert_selected_artifact_sha256": PHOBERT_ARTIFACT_SHA,
    }
    assert calls["comparison"] == repository
    assert calls["runtime"] == (
        repository / production.RUNTIME_DEPENDENCY_AUTHORITY_RELATIVE_PATH
    )
    assert calls["runtime_materialization"] == repository
    qwen_call = calls["qwen"]
    assert isinstance(qwen_call, tuple)
    assert qwen_call[0] == repository
    assert qwen_call[1] == (
        qwen_root / production.QWEN_GGUF_EXPORT_MANIFEST_RELATIVE_PATH
    )
    assert qwen_call[2].final_comparison_authority_sha256 == FINAL_AUTHORITY_SHA
    assert qwen_call[2].origin_request_sha256 == REQUEST_SHA
    assert qwen_call[2].selected_checkpoint_identity == QWEN_CHECKPOINT
    assert calls["phobert"] == (repository, phobert_root)
    with pytest.raises(FrozenInstanceError):
        verified.runtime_dependency_authority_sha256 = "f" * 64  # type: ignore[misc]


def test_phobert_closure_binds_release_receipt_not_raw_tokenizer_digest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, qwen_root, phobert_root = _roots(tmp_path)
    _install_successful_verifiers(monkeypatch)

    verified = production.verify_phase40_production_authorities(
        repo_root=repository,
        qwen_export_root=qwen_root,
        phobert_transfer_root=phobert_root,
    )

    assert PHOBERT_RECEIPT_SHA != PHOBERT_TOKENIZER_SHA
    assert (
        verified.phobert_release_receipt_authority_sha256
        == PHOBERT_RECEIPT_SHA
    )
    assert (
        verified.phobert_release_receipt_authority_sha256
        != PHOBERT_TOKENIZER_SHA
    )


def test_runtime_materialization_receipt_must_bind_loaded_runtime_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, qwen_root, phobert_root = _roots(tmp_path)
    _install_successful_verifiers(monkeypatch)
    monkeypatch.setattr(
        production,
        "load_runtime_materialization_receipt",
        lambda *, repo_root: {
            "receipt_sha256": RUNTIME_MATERIALIZATION_RECEIPT_SHA,
            "authority": {"authority_sha256": "f" * 64},
        },
    )

    with pytest.raises(
        production.Phase40ProductionAuthorityError,
        match="binds a different runtime authority",
    ):
        production.verify_phase40_production_authorities(
            repo_root=repository,
            qwen_export_root=qwen_root,
            phobert_transfer_root=phobert_root,
        )


def test_loads_portable_byte_authority_closure_without_external_roots(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, _, _ = _roots(tmp_path)
    calls = _install_successful_verifiers(monkeypatch)
    qwen_resolution = SimpleNamespace(
        origin=SimpleNamespace(request_sha256=REQUEST_SHA)
    )
    phobert_resolution = SimpleNamespace(
        origin=SimpleNamespace(request_sha256="b" * 64)
    )
    monkeypatch.setattr(
        final_authority,
        "load_frozen_phase40_final_comparison_authority",
        lambda *, repo_root: SimpleNamespace(
            authority_sha256=FINAL_AUTHORITY_SHA,
            by_run_id={
                final_authority.QWEN_QLORA_RUN_ID: qwen_resolution,
                final_authority.RECOVERY_PHOBERT_RUN_ID: phobert_resolution,
            },
        ),
    )

    verified = production.load_phase40_portable_production_authorities(
        repo_root=repository
    )

    assert verified.as_dict() == {
        "verification_mode": production.PORTABLE_RECEIPTS_ONLY,
        "comparison_launch_receipt_sha256": COMPARISON_SHA,
        "qwen_gguf_verification_receipt_sha256": QWEN_RECEIPT_SHA,
        "phobert_release_receipt_authority_sha256": PHOBERT_RECEIPT_SHA,
        "phobert_segmenter_authority_sha256": SEGMENTER_SHA,
        "runtime_dependency_authority_sha256": RUNTIME_SHA,
        "runtime_materialization_receipt_sha256": (
            RUNTIME_MATERIALIZATION_RECEIPT_SHA
        ),
        "qwen_selected_checkpoint_identity": QWEN_CHECKPOINT,
        "phobert_selected_checkpoint_identity": PHOBERT_CHECKPOINT,
        "phobert_selected_artifact_sha256": PHOBERT_ARTIFACT_SHA,
    }
    assert calls["comparison"] == repository
    assert calls["runtime"] == (
        repository / production.RUNTIME_DEPENDENCY_AUTHORITY_RELATIVE_PATH
    )
    assert calls["runtime_materialization"] == repository
    assert "qwen" not in calls
    assert "phobert" not in calls


def test_public_verifier_exposes_roots_but_no_descendant_path_overrides() -> None:
    signature = inspect.signature(production.verify_phase40_production_authorities)
    assert tuple(signature.parameters) == (
        "repo_root",
        "qwen_export_root",
        "phobert_transfer_root",
    )
    assert all(
        parameter.kind is inspect.Parameter.KEYWORD_ONLY
        for parameter in signature.parameters.values()
    )


@pytest.mark.parametrize(
    "argument",
    ("repo_root", "qwen_export_root", "phobert_transfer_root"),
)
def test_relative_trust_root_fails_before_any_verifier(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    argument: str,
) -> None:
    repository, qwen_root, phobert_root = _roots(tmp_path)

    def forbidden(**_kwargs):
        raise AssertionError("authority verifier must not run")

    monkeypatch.setattr(
        production,
        "verify_phase40_comparison_launch_receipt",
        forbidden,
    )
    values = {
        "repo_root": repository,
        "qwen_export_root": qwen_root,
        "phobert_transfer_root": phobert_root,
    }
    values[argument] = Path("relative-root")
    with pytest.raises(
        production.Phase40ProductionAuthorityError,
        match="canonical bounded absolute path",
    ):
        production.verify_phase40_production_authorities(**values)


def test_nested_trust_roots_fail_before_any_verifier(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, qwen_root, _ = _roots(tmp_path)
    nested_phobert = qwen_root / "nested-transfer"
    nested_phobert.mkdir()
    monkeypatch.setattr(
        production,
        "verify_phase40_comparison_launch_receipt",
        lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("authority verifier must not run")
        ),
    )

    with pytest.raises(
        production.Phase40ProductionAuthorityError,
        match="Qwen/PhoBERT trust roots must be disjoint",
    ):
        production.verify_phase40_production_authorities(
            repo_root=repository,
            qwen_export_root=qwen_root,
            phobert_transfer_root=nested_phobert,
        )


def test_missing_code_fixed_manifest_fails_before_authority_verification(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, qwen_root, phobert_root = _roots(tmp_path)
    (qwen_root / production.QWEN_GGUF_EXPORT_MANIFEST_RELATIVE_PATH).unlink()
    calls = _install_successful_verifiers(monkeypatch)

    with pytest.raises(
        production.Phase40ProductionAuthorityError,
        match="fixed Qwen GGUF export manifest is missing",
    ):
        production.verify_phase40_production_authorities(
            repo_root=repository,
            qwen_export_root=qwen_root,
            phobert_transfer_root=phobert_root,
        )
    assert "comparison" in calls
    assert "runtime" in calls
    assert "qwen" not in calls
    assert "phobert" not in calls


def test_roots_on_different_volumes_are_treated_as_disjoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        production.os.path,
        "commonpath",
        lambda _paths: (_ for _ in ()).throw(ValueError("different drives")),
    )

    production._require_disjoint(  # type: ignore[attr-defined]
        Path("C:/synthetic-repository"),
        Path("D:/synthetic-export"),
        where="synthetic",
    )


def test_duplicate_qwen_receipt_key_fails_before_qwen_or_phobert_verification(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, qwen_root, phobert_root = _roots(tmp_path)
    receipt = repository / production.QWEN_GGUF_VERIFICATION_RECEIPT_RELATIVE_PATH
    receipt.write_text(
        '{"upstream":{},"upstream":{},"selection":{}}',
        encoding="utf-8",
    )
    calls = _install_successful_verifiers(monkeypatch)

    with pytest.raises(
        production.Phase40ProductionAuthorityError,
        match="duplicate JSON key 'upstream'",
    ):
        production.verify_phase40_production_authorities(
            repo_root=repository,
            qwen_export_root=qwen_root,
            phobert_transfer_root=phobert_root,
        )
    assert "comparison" in calls
    assert "runtime" in calls
    assert "qwen" not in calls
    assert "phobert" not in calls


def test_qwen_verifier_failure_prevents_phobert_bundle_access(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, qwen_root, phobert_root = _roots(tmp_path)
    calls = _install_successful_verifiers(monkeypatch)

    def reject_qwen(**_kwargs):
        calls["qwen-rejected"] = True
        raise RuntimeError("synthetic drift")

    monkeypatch.setattr(
        production,
        "verify_phase40_qwen_gguf_verification_receipt",
        reject_qwen,
    )
    with pytest.raises(
        production.Phase40ProductionAuthorityError,
        match="Qwen GGUF authority verification failed",
    ):
        production.verify_phase40_production_authorities(
            repo_root=repository,
            qwen_export_root=qwen_root,
            phobert_transfer_root=phobert_root,
        )
    assert calls["qwen-rejected"] is True
    assert "phobert" not in calls


def test_qwen_verifier_cannot_return_a_different_selected_checkpoint(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, qwen_root, phobert_root = _roots(tmp_path)
    calls = _install_successful_verifiers(monkeypatch)

    def forged_qwen(**_kwargs):
        return {
            "receipt_sha256": QWEN_RECEIPT_SHA,
            "selection": {
                "selected_checkpoint": {
                    "artifact_identity": f"adapter-state-sha256:{'f' * 64}"
                }
            },
        }

    monkeypatch.setattr(
        production,
        "verify_phase40_qwen_gguf_verification_receipt",
        forged_qwen,
    )
    with pytest.raises(
        production.Phase40ProductionAuthorityError,
        match="differs from its fixed receipt context",
    ):
        production.verify_phase40_production_authorities(
            repo_root=repository,
            qwen_export_root=qwen_root,
            phobert_transfer_root=phobert_root,
        )
    assert "phobert" not in calls


@pytest.mark.parametrize(
    ("field", "message"),
    (
        ("authority_sha256", "PhoBERT release receipt authority"),
        ("selected_artifact_sha256", "selected PhoBERT artifact"),
    ),
)
def test_malformed_phobert_hash_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    message: str,
) -> None:
    repository, qwen_root, phobert_root = _roots(tmp_path)
    _install_successful_verifiers(monkeypatch)
    values = {
        "authority_sha256": PHOBERT_RECEIPT_SHA,
        "selected_checkpoint_identity": PHOBERT_CHECKPOINT,
        "selected_artifact_sha256": PHOBERT_ARTIFACT_SHA,
    }
    values[field] = "not-a-sha"
    monkeypatch.setattr(
        production,
        "verify_phobert_release_bundle",
        lambda **_kwargs: SimpleNamespace(receipt=SimpleNamespace(**values)),
    )

    with pytest.raises(
        production.Phase40ProductionAuthorityError,
        match=message,
    ):
        production.verify_phase40_production_authorities(
            repo_root=repository,
            qwen_export_root=qwen_root,
            phobert_transfer_root=phobert_root,
        )


def test_dataclass_rejects_wrong_checkpoint_family_prefixes() -> None:
    common = {
        "verification_mode": production.PORTABLE_RECEIPTS_ONLY,
        "comparison_launch_receipt_sha256": COMPARISON_SHA,
        "qwen_gguf_verification_receipt_sha256": QWEN_RECEIPT_SHA,
        "phobert_release_receipt_authority_sha256": PHOBERT_RECEIPT_SHA,
        "phobert_segmenter_authority_sha256": SEGMENTER_SHA,
        "runtime_dependency_authority_sha256": RUNTIME_SHA,
        "runtime_materialization_receipt_sha256": (
            RUNTIME_MATERIALIZATION_RECEIPT_SHA
        ),
        "phobert_selected_artifact_sha256": PHOBERT_ARTIFACT_SHA,
    }
    with pytest.raises(
        production.Phase40ProductionAuthorityError,
        match="selected Qwen checkpoint identity is invalid",
    ):
        production.VerifiedPhase40ProductionAuthorities(
            **common,
            qwen_selected_checkpoint_identity=PHOBERT_CHECKPOINT,
            phobert_selected_checkpoint_identity=PHOBERT_CHECKPOINT,
        )
    with pytest.raises(
        production.Phase40ProductionAuthorityError,
        match="selected PhoBERT checkpoint identity is invalid",
    ):
        production.VerifiedPhase40ProductionAuthorities(
            **common,
            qwen_selected_checkpoint_identity=QWEN_CHECKPOINT,
            phobert_selected_checkpoint_identity=QWEN_CHECKPOINT,
        )


def test_dataclass_rejects_undeclared_verification_strength() -> None:
    with pytest.raises(
        production.Phase40ProductionAuthorityError,
        match="verification mode",
    ):
        production.VerifiedPhase40ProductionAuthorities(
            verification_mode="live_verified",  # type: ignore[arg-type]
            comparison_launch_receipt_sha256=COMPARISON_SHA,
            qwen_gguf_verification_receipt_sha256=QWEN_RECEIPT_SHA,
            phobert_release_receipt_authority_sha256=PHOBERT_RECEIPT_SHA,
            phobert_segmenter_authority_sha256=SEGMENTER_SHA,
            runtime_dependency_authority_sha256=RUNTIME_SHA,
            runtime_materialization_receipt_sha256=(
                RUNTIME_MATERIALIZATION_RECEIPT_SHA
            ),
            qwen_selected_checkpoint_identity=QWEN_CHECKPOINT,
            phobert_selected_checkpoint_identity=PHOBERT_CHECKPOINT,
            phobert_selected_artifact_sha256=PHOBERT_ARTIFACT_SHA,
        )
