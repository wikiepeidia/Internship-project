"""Protocol-freeze and alternate-route tests for Phase 41."""

from __future__ import annotations

from dataclasses import replace
import ast
import hashlib
import inspect
import json
import os
from pathlib import Path
import threading
from types import MappingProxyType
from types import SimpleNamespace

import pytest

from src.model_adaptation.phase41_evaluation import (
    ContractError,
    FrozenModelIdentity,
    OpaqueHeldOutAuthority,
    PHASE41_PRODUCTION_BOOTSTRAP_REQUIRED,
    _phase41_test_runtime,
    _prepare_phase41_synthetic_for_test,
    prepare_phase41_from_canonical_authorities,
)
from src.model_adaptation.phase41_protocols import (
    FrozenInferenceProtocol,
    FrozenQwenPredictor,
    ProtocolContractError,
    _ImmutableTreeLease,
    _bound_bundle_root,
    _build_qwen_qlora_loader_kwargs,
    _qwen_generation_controls,
    _run_with_immutable_leases,
    build_synthetic_protocol_authority,
    build_protocol_authority,
    canonical_json_bytes,
    load_phase41_production_predictors,
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


def _production_protocol_bodies() -> tuple[dict[str, object], dict[str, object]]:
    authority = build_synthetic_protocol_authority(_models())
    qwen_body = json.loads(canonical_json_bytes(authority.qwen.body))
    phobert_body = json.loads(canonical_json_bytes(authority.phobert.body))
    qwen_body["bundle_root"] = str((Path.cwd() / ".gsd/qwen-bundle").absolute())
    phobert_body["bundle_root"] = str((Path.cwd() / ".gsd/phobert-bundle").absolute())
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
    phobert_body["runtime"] = {
        "python": "3.12.4",
        "packages": {
            "torch": "2.8.0",
            "transformers": "4.55.0",
            "underthesea": "9.5.0",
            "huggingface-hub": "0.34.4",
        },
        "device": "cuda:0",
    }
    return qwen_body, phobert_body


def test_protocol_bodies_are_deeply_immutable():
    authority = build_synthetic_protocol_authority(_models())
    assert isinstance(authority.qwen.body, MappingProxyType)
    with pytest.raises(TypeError):
        authority.qwen.body["role"] = "drift"  # type: ignore[index]
    with pytest.raises(TypeError):
        authority.qwen.body["decoder"]["temperature"] = 1.0  # type: ignore[index]


def test_public_predictor_constructor_is_synthetic_test_only():
    authority = build_synthetic_protocol_authority(_models())
    predictor = FrozenQwenPredictor(authority.qwen, lambda snapshot: ())
    assert predictor.synthetic_test_only is True
    assert predictor.production_verified is False
    assert predictor.loaded is False
    assert predictor.smoke_verified is False
    with pytest.raises(TypeError, match="loaded"):
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
        "max_new_tokens": 256,
    }
    assert authority.qwen.body["quantization"] == {
        "load_in_4bit": True,
        "bnb_4bit_compute_dtype": "float16",
        "bnb_4bit_quant_type": "nf4",
        "bnb_4bit_use_double_quant": True,
        "device_map": {"": 0},
        "low_cpu_mem_usage": True,
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
    qwen_body, phobert_body = _production_protocol_bodies()
    build_protocol_authority(qwen_body, phobert_body)

    qwen_body["runtime"]["device"] = "cuda"
    with pytest.raises(ProtocolContractError, match="production runtime identity"):
        build_protocol_authority(qwen_body, phobert_body)

    qwen_body["runtime"]["device"] = "cuda:0"
    del qwen_body["runtime"]["packages"]["huggingface-hub"]
    with pytest.raises(ProtocolContractError, match="production runtime identity"):
        build_protocol_authority(qwen_body, phobert_body)


def test_public_callback_cannot_claim_production_verification():
    qwen_body, phobert_body = _production_protocol_bodies()
    authority = build_protocol_authority(qwen_body, phobert_body)
    with pytest.raises(ProtocolContractError, match="synthetic test-only"):
        FrozenQwenPredictor(authority.qwen, lambda snapshot: ())
    assert tuple(inspect.signature(FrozenQwenPredictor).parameters) == (
        "protocol",
        "predictor",
    )
    source = Path("src/model_adaptation/phase41_protocols.py").read_text(
        encoding="utf-8"
    )
    assert "def _verified_qwen_predictor" not in source
    assert "def _verified_phobert_predictor" not in source


def test_object_new_and_recovered_python_state_cannot_forge_production_predictor(
    tmp_path,
):
    qwen_body, phobert_body = _production_protocol_bodies()
    authority = build_protocol_authority(qwen_body, phobert_body)
    callback_calls: list[object] = []

    def arbitrary_callback(snapshot):
        callback_calls.append(snapshot)
        return ()

    forged = object.__new__(FrozenQwenPredictor)
    object.__setattr__(forged, "protocol", authority.qwen)
    object.__setattr__(forged, "predictor", arbitrary_callback)
    object.__setattr__(forged, "loaded", True)
    object.__setattr__(forged, "smoke_verified", True)
    object.__setattr__(forged, "_leases", ())
    object.__setattr__(forged, "_authority_sha256", authority.authority_sha256)
    object.__setattr__(forged, "_output_root", tmp_path.absolute())
    object.__setattr__(forged, "_launcher_binding", object())
    object.__setattr__(forged, "_launcher_capability_sha256", "a" * 64)

    assert load_phase41_production_predictors.__closure__ is None
    assert forged.production_verified is False
    assert forged.launcher_capability_sha256 is None
    assert forged._has_launcher_binding(object()) is False
    with pytest.raises(ProtocolContractError, match="exactly two live model leases"):
        forged.assert_lifetime_integrity()

    closed_leases = []
    for index in range(2):
        lease = object.__new__(_ImmutableTreeLease)
        lease.root = tmp_path / f"forged-lease-{index}"
        lease.description = "forged closed lease"
        lease._closed = True
        lease._inventory = ((".", "directory", 0),)
        lease._handles = [object()]
        closed_leases.append(lease)
    object.__setattr__(forged, "_leases", tuple(closed_leases))
    assert forged.production_verified is False
    with pytest.raises(ProtocolContractError, match="live OS-backed"):
        forged.assert_lifetime_integrity()

    object.__setattr__(forged, "_leases", ())
    with pytest.raises(ProtocolContractError, match="exactly two live model leases"):
        forged(object())
    assert callback_calls == []

    source = Path("src/model_adaptation/phase41_protocols.py").read_text(
        encoding="utf-8"
    )
    assert "LoaderCapability" not in source
    assert "_loader_capability" not in source


@pytest.mark.parametrize(
    ("field", "drift"),
    (
        ("load_in_4bit", False),
        ("bnb_4bit_compute_dtype", "float32"),
        ("bnb_4bit_quant_type", "fp4"),
        ("bnb_4bit_use_double_quant", False),
        ("device_map", {"": 1}),
        ("low_cpu_mem_usage", False),
    ),
)
def test_qwen_protocol_rejects_any_quantization_drift(field, drift):
    qwen_body, phobert_body = _production_protocol_bodies()
    qwen_body["quantization"][field] = drift
    with pytest.raises(ProtocolContractError, match="NF4 QLoRA"):
        build_protocol_authority(qwen_body, phobert_body)


def test_qwen_loader_constructs_exact_bitsandbytes_and_model_arguments():
    qwen_body, phobert_body = _production_protocol_bodies()
    protocol = build_protocol_authority(qwen_body, phobert_body).qwen
    calls: list[dict[str, object]] = []
    float16 = object()

    class SpyBitsAndBytesConfig:
        def __init__(self, **kwargs):
            calls.append(dict(kwargs))
            for key, value in kwargs.items():
                setattr(self, key, value)

    kwargs = _build_qwen_qlora_loader_kwargs(
        protocol,
        transformers_module=SimpleNamespace(BitsAndBytesConfig=SpyBitsAndBytesConfig),
        torch_module=SimpleNamespace(float16=float16),
    )
    assert calls == [
        {
            "load_in_4bit": True,
            "bnb_4bit_compute_dtype": float16,
            "bnb_4bit_quant_type": "nf4",
            "bnb_4bit_use_double_quant": True,
        }
    ]
    assert kwargs == {
        "revision": "synthetic-qwen-revision",
        "local_files_only": True,
        "trust_remote_code": False,
        "low_cpu_mem_usage": True,
        "quantization_config": kwargs["quantization_config"],
        "device_map": {"": 0},
    }


def test_generation_passes_every_frozen_decoder_control():
    authority = build_synthetic_protocol_authority(_models())
    assert _qwen_generation_controls(authority.qwen) == {
        "do_sample": False,
        "num_return_sequences": 1,
        "temperature": 0.0,
        "top_p": 1.0,
        "max_new_tokens": 256,
    }
    source = Path("src/model_adaptation/phase41_protocols.py").read_text(encoding="utf-8")
    assert "qwen_model.generate(**encoded, **generation_controls)" in source


def test_production_bundle_roots_are_absolute_and_hash_bound():
    qwen_body, phobert_body = _production_protocol_bodies()
    authority = build_protocol_authority(qwen_body, phobert_body)
    assert Path(str(authority.qwen.body["bundle_root"])).is_absolute()
    assert authority.qwen.body["bundle_root_sha256"] == "8" * 64
    qwen_body["bundle_root"] = "data/models/phase40/qwen"
    with pytest.raises(ProtocolContractError, match="absolute non-root"):
        build_protocol_authority(qwen_body, phobert_body)


@pytest.mark.skipif(os.name != "nt", reason="Windows share-mode locks required")
def test_bundle_root_whole_tree_digest_is_checked_before_loading(tmp_path):
    from src.model_adaptation.registry import build_model_checksum

    qwen_root = tmp_path / "qwen-bundle"
    qwen_root.mkdir()
    artifact = qwen_root / "adapter.bin"
    artifact.write_bytes(b"sealed")
    qwen_body, phobert_body = _production_protocol_bodies()
    qwen_body["bundle_root"] = str(qwen_root.absolute())
    qwen_body["bundle_root_sha256"] = build_model_checksum(qwen_root)
    protocol = build_protocol_authority(qwen_body, phobert_body).qwen
    lease = _bound_bundle_root(protocol, checksum_builder=build_model_checksum)
    assert lease.root == qwen_root
    assert lease.identity_sha256 == protocol.body["bundle_root_sha256"]

    with pytest.raises(PermissionError):
        artifact.write_bytes(b"tampered")
    with pytest.raises(PermissionError):
        artifact.unlink()
    lease.close()
    artifact.write_bytes(b"tampered")
    with pytest.raises(ProtocolContractError, match="identity drifted"):
        _bound_bundle_root(protocol, checksum_builder=build_model_checksum)


@pytest.mark.skipif(os.name != "nt", reason="Windows share-mode locks required")
def test_added_file_between_hash_and_loader_is_detected(tmp_path):
    root = (tmp_path / "leased-model").absolute()
    root.mkdir()
    (root / "model.bin").write_bytes(b"sealed")
    lease = _ImmutableTreeLease(
        root,
        description="synthetic selected model",
        checksum_builder=lambda value: hashlib.sha256(
            (value / "model.bin").read_bytes()
        ).hexdigest(),
        expected_sha256=hashlib.sha256(b"sealed").hexdigest(),
    )
    called: list[str] = []

    def hostile_loader():
        called.append("loader")
        (root / "injected-config.json").write_text("{}", encoding="utf-8")
        return object()

    try:
        with pytest.raises(ProtocolContractError, match="changed during"):
            _run_with_immutable_leases((lease,), hostile_loader)
    finally:
        lease.close()
    assert called == ["loader"]


@pytest.mark.skipif(os.name != "nt", reason="Windows change fence required")
def test_transient_add_consume_delete_during_loader_permanently_taints_lease(tmp_path):
    root = (tmp_path / "transient-loader-root").absolute()
    root.mkdir()
    (root / "model.bin").write_bytes(b"sealed")
    lease = _ImmutableTreeLease(root, description="transient hostile loader")
    lease.bind_semantic_identity("b" * 64)
    consumed: list[bytes] = []

    def hostile_loader():
        injected = root / "config.json"
        injected.write_bytes(b'{"architectures":["InjectedModel"]}')
        consumed.append(injected.read_bytes())
        injected.unlink()
        return "loaded-injected-config"

    try:
        with pytest.raises(ProtocolContractError, match="changed during"):
            _run_with_immutable_leases((lease,), hostile_loader)
        assert not (root / "config.json").exists()
        with pytest.raises(ProtocolContractError, match="changed during"):
            lease.assert_intact()
    finally:
        lease.close()
    assert consumed == [b'{"architectures":["InjectedModel"]}']


@pytest.mark.skipif(os.name != "nt", reason="Windows share-mode locks required")
def test_base_snapshot_semantic_identity_stays_locked_for_lifetime(tmp_path):
    root = (tmp_path / "base-snapshot").absolute()
    root.mkdir()
    weight = root / "model.safetensors"
    weight.write_bytes(b"base")
    lease = _ImmutableTreeLease(root, description="synthetic base snapshot")
    lease.bind_semantic_identity("a" * 64)
    try:
        assert lease.identity_sha256 == "a" * 64
        with pytest.raises(PermissionError):
            weight.write_bytes(b"drift")
        lease.assert_intact()
    finally:
        lease.close()


@pytest.mark.skipif(os.name != "nt", reason="Windows ancestor handles required")
def test_access_denied_ancestor_never_uses_token_relative_acl_fallback(
    tmp_path, monkeypatch
):
    import ctypes

    root = (tmp_path / "denied-parent" / "base-snapshot").absolute()
    root.mkdir(parents=True)
    (root / "model.safetensors").write_bytes(b"base")
    denied_ancestor = root.parent
    invalid_handle = ctypes.c_void_p(-1).value

    class FakeKernel32:
        def __init__(self) -> None:
            self.next_handle = 100
            self.closed: list[int] = []

        def CreateFileW(self, path, *_args):
            if Path(path) == denied_ancestor:
                ctypes.set_last_error(5)
                return invalid_handle
            self.next_handle += 1
            return self.next_handle

        def CloseHandle(self, handle):
            self.closed.append(handle)
            return True

    fake = FakeKernel32()

    def configure_fake_handle_api(lease):
        lease._handle_kernel32 = fake
        lease._handle_info_type = object

    monkeypatch.setattr(
        _ImmutableTreeLease,
        "_configure_windows_handle_api",
        configure_fake_handle_api,
    )
    with pytest.raises(ProtocolContractError, match="winerror=5"):
        _ImmutableTreeLease(root, description="denied synthetic ancestor")

    source = Path("src/model_adaptation/phase41_protocols.py").read_text(
        encoding="utf-8"
    )
    assert "allow_acl_protected" not in source
    assert "_assert_acl_protected_ancestor" not in source
    assert fake.closed


@pytest.mark.skipif(os.name != "nt", reason="Windows ancestor handles required")
@pytest.mark.parametrize("target_depth", range(4))
def test_root_and_each_synthetic_ancestor_deny_direct_transient_rename(
    tmp_path, monkeypatch, target_depth
):
    import src.model_adaptation.phase41_protocols as phase41_protocols

    anchor = (tmp_path / "lease-anchor").absolute()
    root = anchor / "ancestor-a" / "ancestor-b" / "base-snapshot"
    root.mkdir(parents=True)
    (root / "model.safetensors").write_bytes(b"trusted")
    targets = (root, root.parent, root.parent.parent, anchor)
    target = targets[target_depth]
    parked = target.with_name(f"{target.name}-parked")
    begin_rename = threading.Event()
    rename_finished = threading.Event()
    rename_succeeded: list[bool] = []
    attack_errors: list[OSError] = []

    def attacker() -> None:
        assert begin_rename.wait(5), "lease never reached the rename attack point"
        try:
            target.rename(parked)
        except OSError as exc:
            attack_errors.append(exc)
        else:  # pragma: no cover - reachable only if ancestry locking regresses
            rename_succeeded.append(True)
            parked.rename(target)
        finally:
            rename_finished.set()

    original_inventory = phase41_protocols._tree_inventory
    synchronized = False

    def synchronized_inventory(path: Path):
        nonlocal synchronized
        if Path(path) == root and not synchronized:
            synchronized = True
            begin_rename.set()
            assert rename_finished.wait(5), "direct rename attack did not finish"
        return original_inventory(path)

    monkeypatch.setattr(
        phase41_protocols,
        "_tree_inventory",
        synchronized_inventory,
    )
    attack = threading.Thread(target=attacker, daemon=True)
    attack.start()
    lease = _ImmutableTreeLease(root, description="direct-rename synthetic root")
    try:
        lease.assert_intact()
    finally:
        lease.close()
        attack.join(5)

    assert not attack.is_alive()
    assert attack_errors and isinstance(attack_errors[0], PermissionError)
    assert rename_succeeded == []


@pytest.mark.skipif(os.name != "nt", reason="Windows share-mode locks required")
def test_ancestor_swap_to_equal_shape_redirect_is_blocked_before_inventory(
    tmp_path, monkeypatch
):
    import src.model_adaptation.phase41_protocols as phase41_protocols

    parent = (tmp_path / "trusted-parent").absolute()
    root = parent / "base-snapshot"
    root.mkdir(parents=True)
    (root / "model.safetensors").write_bytes(b"trusted")
    malicious_parent = (tmp_path / "malicious-parent").absolute()
    malicious_root = malicious_parent / "base-snapshot"
    malicious_root.mkdir(parents=True)
    (malicious_root / "model.safetensors").write_bytes(b"evil!!!")
    parked_parent = (tmp_path / "parked-parent").absolute()

    begin_swap = threading.Event()
    swap_finished = threading.Event()
    rename_succeeded: list[bool] = []
    attack_errors: list[OSError] = []
    consumed: list[bytes] = []

    def attacker() -> None:
        assert begin_swap.wait(5), "lease never reached the synchronized attack point"
        try:
            parent.rename(parked_parent)
        except OSError as exc:
            attack_errors.append(exc)
        else:  # pragma: no cover - reachable only if the lifetime fence regresses
            rename_succeeded.append(True)
            try:
                os.symlink(
                    malicious_parent,
                    parent,
                    target_is_directory=True,
                )
                consumed.append((root / "model.safetensors").read_bytes())
            finally:
                if parent.is_symlink():
                    parent.unlink()
                parked_parent.rename(parent)
        finally:
            swap_finished.set()

    original_inventory = phase41_protocols._tree_inventory
    inventory_calls = 0

    def synchronized_inventory(path: Path):
        nonlocal inventory_calls
        inventory_calls += 1
        if inventory_calls == 1 and Path(path) == root:
            begin_swap.set()
            assert swap_finished.wait(5), "ancestor-swap attack did not finish"
        return original_inventory(path)

    monkeypatch.setattr(
        phase41_protocols,
        "_tree_inventory",
        synchronized_inventory,
    )
    attack = threading.Thread(target=attacker, daemon=True)
    attack.start()
    lease = _ImmutableTreeLease(root, description="PhoBERT base snapshot")
    try:
        observed = _run_with_immutable_leases(
            (lease,),
            lambda: (root / "model.safetensors").read_bytes(),
        )
        assert observed == b"trusted"
    finally:
        lease.close()
        attack.join(5)

    assert not attack.is_alive()
    assert attack_errors and isinstance(attack_errors[0], PermissionError)
    assert rename_succeeded == []
    assert consumed == []


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
    with _phase41_test_runtime(registry_root=tmp_path / "registry"):
        with pytest.raises(ContractError, match="artifact|protocol"):
            _prepare_phase41_synthetic_for_test(
                tmp_path / "out",
                held_out=_held_out(),
                models=(drifted_qwen, models[1]),
                protocols=protocols,
                comparison_authority_sha256="5" * 64,
                review_closure_sha256="6" * 64,
                comparison_launch_receipt_sha256="7" * 64,
                execution_source_manifest_sha256="8" * 64,
                prior_human_exposure_disclosed=True,
                deployment_fit_choice="deferred",
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


def test_protocol_authority_write_flushes_file_durably(tmp_path, monkeypatch):
    calls: list[int] = []
    monkeypatch.setattr(os, "fsync", lambda descriptor: calls.append(descriptor))
    path = write_protocol_authority(
        tmp_path,
        build_synthetic_protocol_authority(_models()),
    )
    assert path.is_file()
    assert len(calls) == 1


def test_execution_source_manifest_binds_inventory_and_launcher(tmp_path):
    models = _models()
    protocols = build_synthetic_protocol_authority(models)
    with _phase41_test_runtime(registry_root=tmp_path / "registry"):
        _prepare_phase41_synthetic_for_test(
            tmp_path,
            held_out=_held_out(),
            models=models,
            protocols=protocols,
            comparison_authority_sha256="5" * 64,
            review_closure_sha256="6" * 64,
            comparison_launch_receipt_sha256="7" * 64,
            execution_source_manifest_sha256="8" * 64,
            prior_human_exposure_disclosed=True,
            deployment_fit_choice="deferred",
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
    import src.model_adaptation.phase40_production_authorities as production
    import src.model_adaptation.phase41_evaluation as phase41_evaluation
    from src.model_adaptation.phase40_handoff import (
        PHASE40_COMPARISON_SCHEMA_VERSION,
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
        "source_manifest": {
            "path": "data/manifests/manifest.json",
            "sha256": "a" * 64,
            "version": "synthetic",
        },
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
        origin_request_sha = ("a" if role == "qwen" else "b") * 64
        source_archive_sha = ("c" if role == "qwen" else "d") * 64
        source_inventory_sha = ("e" if role == "qwen" else "f") * 64
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
                "origin_request_sha256": origin_request_sha,
                "source_archive_sha256": source_archive_sha,
                "source_inventory_sha256": source_inventory_sha,
                "control_template_sha256": ("1" if role == "qwen" else "2") * 64,
            }
        )
    comparison = Phase40ComparisonManifest(
        schema_version=PHASE40_COMPARISON_SCHEMA_VERSION,
        status="complete",
        package_decisions=(),
        original_run_request_sha256="9" * 64,
        scope_amendment_sha256="a" * 64,
        superseded_scope_amendment_sha256="a" * 64,
        final_comparison_authority_sha256="3" * 64,
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
        source_archive_sha256=None,
        source_inventory_sha256=None,
        request_sha256_by_run={
            run["run_id"]: run["origin_request_sha256"] for run in runs
        },
        source_archive_sha256_by_run={
            run["run_id"]: run["source_archive_sha256"] for run in runs
        },
        source_inventory_sha256_by_run={
            run["run_id"]: run["source_inventory_sha256"] for run in runs
        },
        input_archive_sha256="f" * 64,
        input_manifest_sha256="0" * 64,
        comparison_launch_receipt_sha256="4" * 64,
        qwen_gguf_verification_receipt_sha256="5" * 64,
        phobert_release_receipt_authority_sha256="6" * 64,
        phobert_segmenter_authority_sha256="7" * 64,
        runtime_dependency_authority_sha256="8" * 64,
        runtime_materialization_receipt_sha256="9" * 64,
        production_authority_verification_mode="portable_receipts_only",
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
    portable_closure = production.VerifiedPhase40ProductionAuthorities(
        verification_mode=production.PORTABLE_RECEIPTS_ONLY,
        comparison_launch_receipt_sha256="4" * 64,
        qwen_gguf_verification_receipt_sha256="5" * 64,
        phobert_release_receipt_authority_sha256="6" * 64,
        phobert_segmenter_authority_sha256="7" * 64,
        runtime_dependency_authority_sha256="8" * 64,
        runtime_materialization_receipt_sha256="9" * 64,
        qwen_selected_checkpoint_identity=(
            evidence_by_role["qwen"].selected_checkpoint.artifact_identity
        ),
        phobert_selected_checkpoint_identity=(
            evidence_by_role["phobert"].selected_checkpoint.artifact_identity
        ),
        phobert_selected_artifact_sha256="5" * 64,
    )
    monkeypatch.setattr(
        production,
        "load_phase40_portable_production_authorities",
        lambda *, repo_root: portable_closure,
    )
    return repo, phase39_path, comparison_path, review_path


def test_canonical_prepare_validates_existing_closure_then_requires_live_bootstrap(
    tmp_path, monkeypatch
):
    repo, phase39_path, comparison_path, review_path = _write_phase40_closure_fixture(
        tmp_path, monkeypatch
    )
    output_root = repo / "data/models/phase41"
    with pytest.raises(ContractError, match=PHASE41_PRODUCTION_BOOTSTRAP_REQUIRED):
        prepare_phase41_from_canonical_authorities(
            output_root,
            repo_root=repo,
            phase39_contract_path=phase39_path,
            phase40_comparison_manifest_path=comparison_path,
            phase40_review_manifest_path=review_path,
            deployment_fit_choice="deferred",
        )
    assert not output_root.exists()


def test_canonical_prepare_rejects_materialization_receipt_manifest_drift(
    tmp_path, monkeypatch
):
    repo, phase39_path, comparison_path, review_path = _write_phase40_closure_fixture(
        tmp_path, monkeypatch
    )
    comparison = json.loads(comparison_path.read_text(encoding="utf-8"))
    comparison["runtime_materialization_receipt_sha256"] = "0" * 64
    comparison_path.write_bytes(canonical_json_bytes(comparison))

    with pytest.raises(ContractError, match="portable receipt closure differs"):
        prepare_phase41_from_canonical_authorities(
            repo / "data/models/phase41",
            repo_root=repo,
            phase39_contract_path=phase39_path,
            phase40_comparison_manifest_path=comparison_path,
            phase40_review_manifest_path=review_path,
            deployment_fit_choice="deferred",
        )


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
            deployment_fit_choice="deferred",
        )
