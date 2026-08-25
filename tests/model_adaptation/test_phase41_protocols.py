"""Protocol-freeze and alternate-route tests for Phase 41."""

from __future__ import annotations

from dataclasses import replace
import ast
import hashlib
import json
from pathlib import Path
from types import MappingProxyType
from types import SimpleNamespace

import pytest

from src.model_adaptation.phase41_evaluation import (
    ContractError,
    FrozenModelIdentity,
    OpaqueHeldOutAuthority,
    PHASE40_COMPARISON_LAUNCH_RECEIPT_REQUIRED,
    prepare_phase41_evaluation,
    prepare_phase41_from_canonical_authorities,
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


def test_frozen_protocols_match_phase40_qwen_and_phobert_inference_policies():
    authority = build_synthetic_protocol_authority(_models())
    assert authority.qwen.body["decoder"] == {
        "do_sample": False,
        "num_return_sequences": 1,
        "temperature": 0.0,
        "top_p": 1.0,
        "max_new_tokens": 16,
    }
    assert authority.qwen.body["retry_policy"] == {"retries": 0, "repairs": False}
    assert authority.phobert.body["segmenter_package"] == "underthesea"
    assert authority.phobert.body["segmenter_version"] == "9.5.0"
    assert authority.phobert.body["max_length"] == 256
    assert authority.phobert.body["truncation"] == "right"
    assert authority.phobert.body["padding"] == "dynamic-longest"
    assert "segmenter_sha256" not in authority.phobert.body
    assert authority.phobert.body["preprocessing"][0] == (
        "raw_text_utf8_strict_no_normalization"
    )


def test_production_runtime_identity_requires_exact_packages_and_cuda_index():
    authority = build_synthetic_protocol_authority(_models())
    qwen_body = json.loads(canonical_json_bytes(authority.qwen.body))
    phobert_body = json.loads(canonical_json_bytes(authority.phobert.body))
    qwen_body["runtime"] = {
        "python": "3.12.4",
        "packages": {
            "torch": "2.8.0",
            "transformers": "4.55.0",
            "peft": "0.17.0",
            "bitsandbytes": "0.50.1",
            "huggingface-hub": "0.34.4",
        },
        "device": "cuda:0",
    }
    from src.model_adaptation.phase41_protocols import build_protocol_authority

    build_protocol_authority(qwen_body, phobert_body)

    qwen_body["runtime"]["device"] = "cuda"
    with pytest.raises(ProtocolContractError, match="production runtime identity"):
        build_protocol_authority(qwen_body, phobert_body)

    qwen_body["runtime"]["device"] = "cuda:0"
    del qwen_body["runtime"]["packages"]["huggingface-hub"]
    with pytest.raises(ProtocolContractError, match="production runtime identity"):
        build_protocol_authority(qwen_body, phobert_body)


def test_qwen_loader_rejects_overlength_input_before_generation():
    source = Path("src/model_adaptation/phase41_protocols.py").read_text(encoding="utf-8")
    guard = 'if input_length > int(authority.qwen.body["max_sequence_length"]):'
    generate = "qwen_model.generate(**encoded, **generation_controls)"
    assert guard in source
    assert source.index(guard) < source.index(generate)
    assert "qwen_input_exceeds_frozen_max_sequence_length" in source


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
    source_paths = {row["path"] for row in manifest["files"]}
    assert "src/model_adaptation/phase41_evaluation.py" in source_paths
    assert "src/model_adaptation/phase41_protocols.py" in source_paths
    assert "src/model_adaptation/registry.py" in source_paths
    assert "src/model_adaptation/release_evaluation.py" in source_paths
    assert manifest["closed_import_roots"] == [
        "src.model_adaptation.cli",
        "src.model_adaptation.phase41_evaluation",
        "src.model_adaptation.phase41_protocols",
    ]
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


def _write_phase40_closure_fixture(tmp_path: Path, monkeypatch):
    import src.model_adaptation.phase40_evidence as phase40_evidence
    import src.model_adaptation.phase41_evaluation as phase41_evaluation
    from src.model_adaptation.phase40_handoff import (
        PHASE40_COMPARISON_LIMITATIONS,
        Phase40ComparisonManifest,
    )

    repo = tmp_path / "repo"
    phase39_path = (
        repo
        / ".planning/phases/39-independent-quality-re-judge/39-DOWNSTREAM-DATA-CONTRACT.json"
    )
    phase39_path.parent.mkdir(parents=True)
    labels = {
        "bank_impersonation": 1,
        "zalo_social_engineering": 1,
        "task_scam": 1,
        "benign": 1,
    }
    split = lambda token: {  # noqa: E731 - compact synthetic authority builder
        "records": 4,
        "bytes": 100,
        "sha256": token * 64,
        "label_counts": labels,
    }
    phase39 = {
        "schema_version": "phase39-downstream-data-contract-v1",
        "generated_at": "2026-08-25T00:00:00+07:00",
        "source_manifest": {"path": "data/manifests/manifest.json", "sha256": "a" * 64, "version": "synthetic"},
        "total_records": 12,
        "splits": {"train": split("1"), "val": split("2"), "test": split("3")},
        "total_label_counts": {label: 3 for label in labels},
        "split_governance": {"whole_seed_groups": True},
        "phase40_training_boundary": {
            "allowed_splits": ["train", "val"],
            "forbidden_split": "test",
            "rule": "synthetic",
            "starts_after": "synthetic",
        },
        "held_out_test": {
            "path": "data/splits/test.jsonl",
            "records": 4,
            "bytes": 100,
            "sha256": "3" * 64,
            "evaluation_phase": 41,
            "touch_policy": "one shot only",
        },
        "phase41_post_evaluation_fit": {
            "all_data_records": 12,
            "allowed_only_after": "frozen",
            "unbiased_test_score_claim": False,
        },
    }
    phase39_path.write_text(json.dumps(phase39, ensure_ascii=False), encoding="utf-8")
    _, phase39_identity = phase41_evaluation._phase39_opaque_authority(phase39_path)

    comparison_path = repo / "data/models/phase40/comparison-manifest.json"
    comparison_path.parent.mkdir(parents=True)
    evidence_by_role = {}
    runs = []
    for role, family, adaptation, returned_root, artifact_sha, checkpoint_prefix in (
        (
            "qwen",
            "qwen",
            "qlora",
            "data/models/phase40/full/qwen-qlora",
            "4" * 64,
            "adapter-state-sha256:",
        ),
        (
            "phobert",
            "phobert",
            "classification-head",
            "data/models/phase40/full/phobert",
            "5" * 64,
            "model-state-sha256:",
        ),
    ):
        run_id = f"{role}-synthetic"
        checkpoint = checkpoint_prefix + ("6" if role == "qwen" else "7") * 64
        run_root = repo / returned_root
        run_root.mkdir(parents=True)
        evidence_bytes = (f"synthetic-{role}-evidence\n").encode()
        (run_root / "run-evidence.json").write_bytes(evidence_bytes)
        metrics = {"eval_macro_f1": 0.9}
        packages = (
            {"bitsandbytes": "0.50.1", "transformers": "5.0.0"}
            if role == "qwen"
            else {"transformers": "5.0.0", "underthesea": "9.5.0"}
        )
        evidence_by_role[role] = SimpleNamespace(
            status="complete",
            run_id=run_id,
            resume_digest="8" * 64,
            experiment_identity=SimpleNamespace(
                run_kind="full", model_family=family, adaptation_mode=adaptation
            ),
            selected_checkpoint=SimpleNamespace(
                artifact_identity=checkpoint,
                optimizer_step=10,
                safety_gate_passed=True,
            ),
            comparison_eligible=True,
            validation_metrics=metrics,
            package_versions=packages,
            artifacts=(SimpleNamespace(role="model_artifact", sha256=artifact_sha),),
        )
        runs.append(
            {
                "run_id": run_id,
                "model_family": family,
                "adaptation_mode": adaptation,
                "returned_root": returned_root,
                "evidence_sha256": hashlib.sha256(evidence_bytes).hexdigest(),
                "resume_digest": "8" * 64,
                "selected_checkpoint_identity": checkpoint,
                "selected_optimizer_step": 10,
                "safety_gate_passed": True,
                "comparison_eligible": True,
                "validation_rows": 4,
                "validation_metrics": metrics,
                "macro_f1": 0.9,
                "invalid_output_count": 0,
                "risky_recall_by_label": {
                    "bank_impersonation": 1.0,
                    "zalo_social_engineering": 1.0,
                    "task_scam": 1.0,
                },
                "gpu_identity": "synthetic-gpu",
                "package_versions": packages,
                "required_tool_pins": packages,
            }
        )
    comparison = Phase40ComparisonManifest(
        status="complete",
        package_decisions=(),
        original_run_request_sha256="9" * 64,
        scope_amendment_sha256="a" * 64,
        comparison_finalizer_source_sha256="b" * 64,
        lora_probe={
            "run_id": "lora-probe",
            "evidence_authority_sha256": "c" * 64,
            "observed_optimizer_steps": 40,
            "retained_optimizer_steps": 40,
            "steady_state_step_seconds_median": 10.0,
            "peak_device_vram_used_mib": 7900.0,
            "minimum_device_vram_free_mib": 100.0,
            "peak_system_ram_used_bytes": 30_000_000_000.0,
            "memory_constrained": True,
            "oom_observed": False,
            "discarded_runtime_path_absent": True,
            "comparison_eligible": False,
            "predictions_included": False,
        },
        source_archive_sha256="d" * 64,
        source_inventory_sha256="e" * 64,
        input_archive_sha256="f" * 64,
        input_manifest_sha256="0" * 64,
        validation_rows=4,
        runs=tuple(runs),
        quality_comparison_admissible=True,
        hardware_confounded=False,
        speed_comparison_admissible=False,
        review_queue_rows=8,
        review_queue_sha256="1" * 64,
        selected_prediction_bundles_sha256="2" * 64,
        limitations=PHASE40_COMPARISON_LIMITATIONS,
        failure_reason=None,
    )
    comparison_bytes = canonical_json_bytes(comparison.model_dump(mode="json"))
    comparison_path.write_bytes(comparison_bytes)

    review_path = repo / "data/models/phase40/review/human-review-manifest.json"
    review_path.parent.mkdir(parents=True)
    review = {
        "schema_version": "phase40-human-review-v2",
        "vietnamese_fluent_attestation": True,
        "rows": 8,
        "queue_sha256": "1" * 64,
        "reviewer_return_sha256": "3" * 64,
        "notes_sha256": "4" * 64,
        "report_sha256": "5" * 64,
        "comparison_manifest_sha256": hashlib.sha256(comparison_bytes).hexdigest(),
        "scope_amendment_sha256": "a" * 64,
        "review_queue_manifest_sha256": "6" * 64,
        "phase39_data_contract_sha256": phase39_identity,
        "validation_ordered_row_ids_sha256": "7" * 64,
        "frozen_results_sha256": "8" * 64,
        "summary": {"reviewed": 8},
        "limitations": list(PHASE40_COMPARISON_LIMITATIONS),
    }
    review_path.write_bytes(canonical_json_bytes(review))

    def fake_verify_bundle(path: Path):
        return evidence_by_role["qwen" if Path(path).name == "qwen-qlora" else "phobert"]

    monkeypatch.setattr(phase40_evidence, "verify_phase40_bundle", fake_verify_bundle)
    return repo, phase39_path, comparison_path, review_path


def test_canonical_prepare_validates_existing_closure_then_fails_at_missing_receipt(
    tmp_path, monkeypatch
):
    repo, phase39_path, comparison_path, review_path = _write_phase40_closure_fixture(
        tmp_path, monkeypatch
    )
    output_root = repo / "data/models/phase41"
    with pytest.raises(
        ContractError, match=PHASE40_COMPARISON_LAUNCH_RECEIPT_REQUIRED
    ):
        prepare_phase41_from_canonical_authorities(
            output_root,
            repo_root=repo,
            phase39_contract_path=phase39_path,
            phase40_comparison_manifest_path=comparison_path,
            phase40_review_manifest_path=review_path,
        )
    assert not output_root.exists()


def test_canonical_prepare_rejects_ordinary_lora_before_bundle_access(
    tmp_path, monkeypatch
):
    repo, phase39_path, comparison_path, review_path = _write_phase40_closure_fixture(
        tmp_path, monkeypatch
    )
    comparison = json.loads(comparison_path.read_text(encoding="utf-8"))
    comparison["runs"][0]["adaptation_mode"] = "lora"
    comparison_path.write_bytes(canonical_json_bytes(comparison))
    with pytest.raises(ContractError, match="comparison manifest schema|two-model"):
        prepare_phase41_from_canonical_authorities(
            repo / "out",
            repo_root=repo,
            phase39_contract_path=phase39_path,
            phase40_comparison_manifest_path=comparison_path,
            phase40_review_manifest_path=review_path,
        )
