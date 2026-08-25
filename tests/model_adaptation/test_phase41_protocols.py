"""Protocol-freeze and alternate-route tests for Phase 41."""

from __future__ import annotations

from dataclasses import replace
import ast
import hashlib
import json
from pathlib import Path
from types import MappingProxyType

import pytest

from src.model_adaptation.phase41_evaluation import (
    ContractError,
    FrozenModelIdentity,
    OpaqueHeldOutAuthority,
    prepare_phase41_evaluation,
)
from src.model_adaptation.phase41_protocols import (
    FrozenInferenceProtocol,
    FrozenQwenPredictor,
    ProtocolContractError,
    build_synthetic_protocol_authority,
    canonical_json_bytes,
    load_protocol_authority,
    write_protocol_authority,
)


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


def _held_out() -> OpaqueHeldOutAuthority:
    return OpaqueHeldOutAuthority(
        path=r"C:\synthetic-only\opaque.jsonl",
        records=4,
        bytes=100,
        sha256="9" * 64,
        label_counts=(
            ("bank_impersonation", 1),
            ("zalo_social_engineering", 1),
            ("task_scam", 1),
            ("benign", 1),
        ),
    )


def test_protocol_bodies_are_deeply_immutable():
    authority = build_synthetic_protocol_authority(_models())
    assert isinstance(authority.qwen.body, MappingProxyType)
    with pytest.raises(TypeError):
        authority.qwen.body["role"] = "drift"  # type: ignore[index]
    with pytest.raises(TypeError):
        authority.qwen.body["decoder"]["temperature"] = 1.0  # type: ignore[index]


def test_predictor_requires_preloaded_and_smoke_verified_markers():
    authority = build_synthetic_protocol_authority(_models())
    with pytest.raises(ProtocolContractError, match="loaded and smoke-verified"):
        FrozenQwenPredictor(
            authority.qwen,
            lambda snapshot: (),
            loaded=False,
            smoke_verified=True,
        )


def test_prepare_rejects_protocol_artifact_identity_drift(tmp_path):
    models = _models()
    protocols = build_synthetic_protocol_authority(models)
    drifted_qwen = replace(models[0], artifact_sha256="a" * 64)
    with pytest.raises(ContractError, match="artifact|protocol"):
        prepare_phase41_evaluation(
            tmp_path / "out",
            held_out=_held_out(),
            models=(drifted_qwen, models[1]),
            protocols=protocols,
            comparison_authority_sha256="5" * 64,
            review_closure_sha256="6" * 64,
            comparison_launch_receipt_sha256="7" * 64,
            execution_source_manifest_sha256="8" * 64,
            prior_human_exposure_disclosed=True,
        )


def test_protocol_loader_rejects_nested_duplicate_and_nonfinite_json(tmp_path):
    authority = build_synthetic_protocol_authority(_models())
    path = write_protocol_authority(tmp_path, authority)
    valid = path.read_text(encoding="utf-8")
    duplicate = valid.replace('"role":"qwen"', '"role":"qwen","role":"qwen"', 1)
    path.write_text(duplicate, encoding="utf-8")
    with pytest.raises(ProtocolContractError, match="duplicate"):
        load_protocol_authority(tmp_path)

    path.unlink()
    write_protocol_authority(tmp_path, authority)
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw["models"][0]["body"]["decoder"]["temperature"] = float("nan")
    path.write_text(json.dumps(raw, allow_nan=True), encoding="utf-8")
    with pytest.raises(ProtocolContractError, match="non-finite|strict JSON"):
        load_protocol_authority(tmp_path)


def test_execution_source_manifest_binds_inventory_and_launcher(tmp_path):
    models = _models()
    protocols = build_synthetic_protocol_authority(models)
    prepare_phase41_evaluation(
        tmp_path,
        held_out=_held_out(),
        models=models,
        protocols=protocols,
        comparison_authority_sha256="5" * 64,
        review_closure_sha256="6" * 64,
        comparison_launch_receipt_sha256="7" * 64,
        execution_source_manifest_sha256="8" * 64,
        prior_human_exposure_disclosed=True,
    )
    manifest = json.loads((tmp_path / "execution-source-manifest.json").read_text(encoding="utf-8"))
    assert manifest["launcher"]["path"] == "scripts/phase41_one_shot_launcher.ps1"
    assert len(manifest["launcher"]["sha256"]) == 64
    assert manifest["files"]
    assert all(set(row) == {"path", "bytes", "sha256"} for row in manifest["files"])
    assert len(manifest["source_tree_sha256"]) == 64


def test_phase41_import_graph_has_no_legacy_or_runtime_evaluation_route():
    evaluation_path = Path("src/model_adaptation/phase41_evaluation.py")
    source = evaluation_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    assert "src.model_adaptation.release_evaluation" not in imported
    assert not any(name.startswith("src.runtime") for name in imported)
    assert "evaluate_release_split(" not in source
    assert "progress_callback" not in source
