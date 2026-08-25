"""Contract tests for the standalone Phase 40 GGUF exporter."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
import hashlib
import importlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.model_adaptation import phase40_gguf as gguf
from src.model_adaptation.phase40_evidence import EvidenceStatus
from src.model_adaptation.phase40_modes import AdaptationMode, ModelFamily, RunKind
from src.model_adaptation.registry import build_model_checksum


MODEL_ID = "Qwen/Qwen3-4B-Instruct-2507"
MODEL_REVISION = "a" * 40
SELECTED_IDENTITY = "adapter-state-sha256:" + "b" * 64
QWEN_RUN_ID = gguf._final_authority.QWEN_QLORA_RUN_ID
_SYNTHETIC_REQUEST = {
    "schema_version": "synthetic-phase40-request-v1",
    "run_ids": [QWEN_RUN_ID, "phase40-phobert-full-seed42-v12"],
}
_SYNTHETIC_REQUEST_BYTES = gguf._canonical_json_bytes(_SYNTHETIC_REQUEST)
_SYNTHETIC_ORIGIN_REQUEST_SHA256 = hashlib.sha256(_SYNTHETIC_REQUEST_BYTES).hexdigest()
_SYNTHETIC_FINAL_AUTHORITY_SHA256 = hashlib.sha256(b"final-authority-v1\n").hexdigest()


class FakeOriginRequest:
    def __init__(self, requested_run: SimpleNamespace) -> None:
        self.runs = (requested_run,)

    def model_dump(self, *, mode: str) -> dict[str, object]:
        assert mode == "json"
        return dict(_SYNTHETIC_REQUEST)


def _fake_final_authority(
    *,
    authority_sha256: str = _SYNTHETIC_FINAL_AUTHORITY_SHA256,
    origin_request_sha256: str = _SYNTHETIC_ORIGIN_REQUEST_SHA256,
    run_id: str = QWEN_RUN_ID,
    model_family: ModelFamily = ModelFamily.QWEN,
    adaptation_mode: AdaptationMode = AdaptationMode.QLORA,
) -> SimpleNamespace:
    requested_run = SimpleNamespace(
        run_id=run_id,
        model_family=model_family,
        adaptation_mode=adaptation_mode,
        run_kind=RunKind.FULL.value,
        returned_root=gguf._final_authority.QWEN_QLORA_RETURNED_ROOT,
        step_origin=0,
        probe_parent=None,
    )
    origin_request = FakeOriginRequest(requested_run)
    resolution = SimpleNamespace(
        run_id=run_id,
        origin=SimpleNamespace(
            authority_id=gguf._final_authority.ORIGINAL_REQUEST_AUTHORITY_ID,
            root_policy="repository_root",
            request_sha256=origin_request_sha256,
        ),
        origin_request=origin_request,
        requested_run=requested_run,
    )
    return SimpleNamespace(
        authority_sha256=authority_sha256,
        by_run_id={QWEN_RUN_ID: resolution},
    )


@pytest.fixture(autouse=True)
def _stub_final_comparison_authority(monkeypatch):
    verified = _fake_final_authority()
    monkeypatch.setattr(
        gguf._final_authority,
        "load_frozen_phase40_final_comparison_authority",
        lambda *, repo_root: verified,
    )


@dataclass(frozen=True)
class FakeSnapshot:
    model_id: str
    model_revision: str
    snapshot_content_sha256: str
    manifest_sha256: str
    portable: dict[str, object]

    def portable_manifest(self) -> dict[str, object]:
        return self.portable


class FakeTokenizer:
    def save_pretrained(self, destination: str) -> None:
        (Path(destination) / "tokenizer_config.json").write_text("{}\n", encoding="utf-8")


class FakeMergedModel:
    is_loaded_in_4bit = False
    config = SimpleNamespace(quantization_config=None)

    def modules(self):
        return (self,)

    def save_pretrained(self, destination: str, *, safe_serialization: bool) -> None:
        assert safe_serialization is True
        root = Path(destination)
        (root / "config.json").write_text("{}\n", encoding="utf-8")
        (root / "model.safetensors").write_bytes(b"merged-weights")


class FakeBaseModel(FakeMergedModel):
    pass


class FakePeftModel(FakeMergedModel):
    def __init__(self, calls: list[object]):
        self.calls = calls

    def merge_and_unload(self, *, safe_merge: bool):
        self.calls.append(("merge_and_unload", safe_merge))
        return FakeMergedModel()


@dataclass
class Fixture:
    run_root: Path
    base_root: Path
    base_manifest: Path
    converter: Path
    converter_sha256: str
    output: Path
    manifest: Path
    dependencies: gguf.GGUFExportDependencies
    calls: list[object]
    smoke_paths: list[Path]
    run_hash: str
    base_hash: str


def _fixture(tmp_path: Path, *, run_kind: RunKind = RunKind.FULL) -> Fixture:
    calls: list[object] = []
    smoke_paths: list[Path] = []
    authority_root = tmp_path / "data" / "models" / "phase40"
    authority_root.mkdir(parents=True)
    base_root = tmp_path / "base"
    base_root.mkdir()
    (base_root / "config.json").write_text("{}\n", encoding="utf-8")
    (base_root / "tokenizer_config.json").write_text("{}\n", encoding="utf-8")
    (base_root / "model.safetensors").write_bytes(b"base-weights")
    portable = {
        "schema_version": "phase40-qwen-base-model-provenance-v1",
        "model_id": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "snapshot_content_sha256": "c" * 64,
        "files": [
            {
                "relative_path": "model.safetensors",
                "bytes": len(b"base-weights"),
                "sha256": hashlib.sha256(b"base-weights").hexdigest(),
            }
        ],
    }
    base_manifest = tmp_path / "authority" / gguf.BASE_PROVENANCE_FILENAME
    base_manifest.parent.mkdir()
    base_manifest.write_bytes(gguf._canonical_json_bytes(portable))
    snapshot = FakeSnapshot(
        model_id=MODEL_ID,
        model_revision=MODEL_REVISION,
        snapshot_content_sha256="c" * 64,
        manifest_sha256=hashlib.sha256(base_manifest.read_bytes()).hexdigest(),
        portable=portable,
    )
    base_hash = build_model_checksum(base_root)

    run_root = tmp_path / "returned" / "qwen-qlora"
    adapter = run_root / "adapter-or-model"
    adapter.mkdir(parents=True)
    (adapter / "adapter_config.json").write_text("{}\n", encoding="utf-8")
    (adapter / "adapter_model.safetensors").write_bytes(b"adapter-weights")
    (adapter / gguf.BASE_PROVENANCE_FILENAME).write_bytes(gguf._canonical_json_bytes(portable))
    (adapter / "training-summary.json").write_text(
        gguf.json.dumps(
            {
                "run_id": QWEN_RUN_ID,
                "run_kind": "full",
                "model_revision": MODEL_REVISION,
                "requested_adaptation_mode": "qlora",
                "selected_adapter": {"state_identity": SELECTED_IDENTITY},
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (run_root / "run-evidence.json").write_text('{"fixture":true}\n', encoding="utf-8")
    artifact = SimpleNamespace(
        role="model_artifact",
        kind="directory",
        relative_path="adapter-or-model",
        sha256=build_model_checksum(adapter),
    )
    evidence = SimpleNamespace(
        status=EvidenceStatus.COMPLETE,
        run_kind=run_kind,
        run_id=QWEN_RUN_ID,
        model_id=MODEL_ID,
        model_revision=MODEL_REVISION,
        experiment_identity=SimpleNamespace(
            run_kind=run_kind,
            model_family=ModelFamily.QWEN,
            adaptation_mode=AdaptationMode.QLORA,
        ),
        artifacts=(artifact,),
        selected_checkpoint=SimpleNamespace(
            optimizer_step=1245,
            artifact_identity=SELECTED_IDENTITY,
            safety_gate_passed=True,
        ),
    )
    run_hash = build_model_checksum(run_root)

    def verify_bundle(candidate: Path):
        calls.append(("verify_bundle", candidate))
        return evidence

    def verify_base(
        candidate: Path,
        *,
        expected_model_id: str,
        expected_model_revision: str,
        manifest_path: Path | None,
    ):
        calls.append(("verify_base", candidate, manifest_path))
        assert expected_model_id == MODEL_ID
        assert expected_model_revision == MODEL_REVISION
        assert manifest_path == base_manifest
        if build_model_checksum(candidate) != base_hash:
            raise RuntimeError("base drift")
        if hashlib.sha256(base_manifest.read_bytes()).hexdigest() != snapshot.manifest_sha256:
            raise RuntimeError("manifest drift")
        return snapshot

    def load_tokenizer(candidate: Path):
        calls.append(("load_tokenizer", candidate))
        return FakeTokenizer()

    def load_base(candidate: Path):
        calls.append(("load_base", candidate))
        return FakeBaseModel()

    def attach_adapter(model, candidate: Path):
        calls.append(("attach_adapter", model, candidate))
        return FakePeftModel(calls)

    def run_command(command, **kwargs):
        calls.append(("command", tuple(command), kwargs))
        assert command[-2:] == ["--outtype", "q8_0"]
        assert kwargs == {
            "cwd": str(tmp_path / "llama.cpp"),
            "check": False,
            "capture_output": True,
            "text": True,
        }
        Path(command[command.index("--outfile") + 1]).write_bytes(b"GGUF\x00fixture")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    def smoke(candidate: Path):
        smoke_paths.append(candidate)
        return gguf.LoadSmokeResult(
            passed=True,
            loader="fake.Llama",
            loader_version="1.0",
            detail="constructor load completed",
        )

    times = iter(
        (
            datetime(2026, 8, 25, 1, 0, tzinfo=timezone.utc),
            datetime(2026, 8, 25, 1, 2, tzinfo=timezone.utc),
        )
    )
    dependencies = gguf.GGUFExportDependencies(
        model_backend=gguf.ModelBackend(load_tokenizer, load_base, attach_adapter),
        command_runner=run_command,
        smoke_loader=smoke,
        bundle_verifier=verify_bundle,
        base_snapshot_verifier=verify_base,
        selected_adapter_identity_resolver=lambda candidate: (
            SELECTED_IDENTITY if candidate == adapter else "wrong-adapter"
        ),
        package_version_resolver=lambda name: (
            gguf.CONVERTER_PACKAGE_VERSION
            if name == gguf.CONVERTER_PACKAGE_NAME
            else "missing"
        ),
        authorized_converter_sha256=hashlib.sha256(b"# pinned converter").hexdigest(),
        now=lambda: next(times),
    )
    converter = tmp_path / "llama.cpp" / gguf.CONVERTER_FILENAME
    converter.parent.mkdir()
    converter.write_bytes(b"# pinned converter")
    output = tmp_path / "exports" / "qwen-qlora-q8_0.gguf"
    manifest = output.with_suffix(output.suffix + ".manifest.json")
    return Fixture(
        run_root=run_root,
        base_root=base_root,
        base_manifest=base_manifest,
        converter=converter,
        converter_sha256=hashlib.sha256(converter.read_bytes()).hexdigest(),
        output=output,
        manifest=manifest,
        dependencies=dependencies,
        calls=calls,
        smoke_paths=smoke_paths,
        run_hash=run_hash,
        base_hash=base_hash,
    )


def _export(fixture: Fixture) -> gguf.GGUFExportResult:
    return gguf.export_phase40_gguf(
        run_root=fixture.run_root,
        base_model_path=fixture.base_root,
        base_manifest_path=fixture.base_manifest,
        converter_script=fixture.converter,
        converter_sha256=fixture.converter_sha256,
        output_path=fixture.output,
        dependencies=fixture.dependencies,
    )


def _verification_context() -> gguf.GGUFVerificationContext:
    return gguf.GGUFVerificationContext(
        final_comparison_authority_sha256=_SYNTHETIC_FINAL_AUTHORITY_SHA256,
        origin_request_sha256=_SYNTHETIC_ORIGIN_REQUEST_SHA256,
        selected_run_id=QWEN_RUN_ID,
        selected_checkpoint_identity=SELECTED_IDENTITY,
    )


def _injected_manifest_verifier(fixture: Fixture, calls: list[bool]):
    def verify(manifest_path: Path, *, rerun_load_smoke: bool):
        calls.append(rerun_load_smoke)
        return gguf.verify_phase40_gguf_export(
            manifest_path,
            dependencies=fixture.dependencies,
            rerun_load_smoke=rerun_load_smoke,
        )

    return verify


def _receipt_path(tmp_path: Path) -> Path:
    return tmp_path / gguf.QWEN_GGUF_VERIFICATION_RECEIPT_RELATIVE_PATH


def _freeze_receipt(
    fixture: Fixture,
    tmp_path: Path,
    *,
    context: gguf.GGUFVerificationContext | None = None,
    verifier_calls: list[bool] | None = None,
) -> tuple[Path, dict[str, object], list[bool]]:
    calls = [] if verifier_calls is None else verifier_calls
    receipt = _receipt_path(tmp_path)
    payload = gguf.freeze_phase40_qwen_gguf_verification_receipt(
        repo_root=tmp_path,
        export_manifest_path=fixture.manifest,
        context=_verification_context() if context is None else context,
        manifest_verifier=_injected_manifest_verifier(fixture, calls),
        now=lambda: datetime(2026, 8, 25, 2, 5, tzinfo=timezone.utc),
    )
    return receipt, payload, calls


def test_export_merges_exact_selected_adapter_converts_q8_smokes_and_verifies(tmp_path):
    fixture = _fixture(tmp_path)
    result = _export(fixture)

    assert result.output_path == fixture.output
    assert result.manifest_path == fixture.manifest
    assert result.output_sha256 == hashlib.sha256(b"GGUF\x00fixture").hexdigest()
    assert fixture.smoke_paths == [fixture.output]
    assert ("merge_and_unload", True) in fixture.calls
    command = next(call for call in fixture.calls if call[0] == "command")[1]
    assert command[-2:] == ("--outtype", "q8_0")
    assert str(fixture.run_root) not in result.manifest["tool"]["sanitized_command"]
    assert result.manifest["browser_download"] == {
        "path": str(fixture.output.resolve()),
        "ready": True,
        "operator_action_required": True,
        "unattended_browser_download_claimed": False,
    }
    assert result.manifest["source"]["selected_checkpoint"]["artifact_identity"] == SELECTED_IDENTITY
    assert build_model_checksum(fixture.run_root) == fixture.run_hash
    assert build_model_checksum(fixture.base_root) == fixture.base_hash
    assert not list(fixture.output.parent.glob("phase40-gguf-*"))


def test_verify_rehashes_source_tool_output_and_repeats_load_smoke(tmp_path):
    fixture = _fixture(tmp_path)
    _export(fixture)

    verified = gguf.verify_phase40_gguf_export(
        fixture.manifest,
        dependencies=fixture.dependencies,
    )

    assert verified["status"] == "complete"
    assert fixture.smoke_paths == [fixture.output, fixture.output]


def test_freeze_and_verify_portable_self_hashed_qwen_gguf_receipt(tmp_path):
    fixture = _fixture(tmp_path)
    _export(fixture)
    receipt, payload, verifier_calls = _freeze_receipt(fixture, tmp_path)

    verified = gguf.verify_phase40_qwen_gguf_verification_receipt(
        repo_root=tmp_path,
        export_manifest_path=fixture.manifest,
        context=_verification_context(),
        manifest_verifier=_injected_manifest_verifier(fixture, verifier_calls),
    )

    core = dict(payload)
    receipt_sha256 = core.pop("receipt_sha256")
    assert receipt_sha256 == hashlib.sha256(gguf._canonical_json_bytes(core)).hexdigest()
    assert verified == payload
    assert payload["schema_version"] == "phase40-qwen-gguf-verification-receipt-v2"
    assert payload["upstream"] == {
        "final_comparison_authority_sha256": _SYNTHETIC_FINAL_AUTHORITY_SHA256,
        "origin_request_sha256": _SYNTHETIC_ORIGIN_REQUEST_SHA256,
    }
    assert verifier_calls == [True, True]
    assert fixture.smoke_paths == [fixture.output, fixture.output, fixture.output]
    assert payload["selection"]["selected_checkpoint"] == {
        "optimizer_step": 1245,
        "artifact_identity": SELECTED_IDENTITY,
        "safety_gate_passed": True,
    }
    assert payload["export"] == {
        "manifest_filename": fixture.manifest.name,
        "manifest_sha256": hashlib.sha256(fixture.manifest.read_bytes()).hexdigest(),
        "manifest_schema_version": gguf.SCHEMA_VERSION,
        "manifest_status": "complete",
        "outtype": "q8_0",
        "gguf_filename": fixture.output.name,
        "gguf_bytes": fixture.output.stat().st_size,
        "gguf_sha256": hashlib.sha256(fixture.output.read_bytes()).hexdigest(),
    }
    assert payload["converter"] == {
        "authority_type": "pypi-package-script-hash",
        "package_name": gguf.CONVERTER_PACKAGE_NAME,
        "package_version": gguf.CONVERTER_PACKAGE_VERSION,
        "script_filename": gguf.CONVERTER_FILENAME,
        "script_sha256": fixture.converter_sha256,
    }
    assert payload["load_smoke"]["original_export"]["passed"] is True
    assert payload["load_smoke"]["independent_rerun"] == {
        "passed": True,
        "verifier": "verify_phase40_gguf_export",
        "rerun_load_smoke": True,
        "manifest_sha256": payload["export"]["manifest_sha256"],
    }
    assert "comparison_manifest_sha256" not in receipt.read_text(encoding="utf-8")
    receipt_text = receipt.read_text(encoding="utf-8")
    assert str(tmp_path) not in receipt_text
    assert "run_root" not in receipt_text
    assert "base_model_path" not in receipt_text
    assert receipt.read_bytes() == gguf._canonical_json_bytes(payload)


def test_fixed_receipt_loader_authenticates_bytes_without_rerunning_gguf_smoke(tmp_path):
    fixture = _fixture(tmp_path)
    _export(fixture)
    receipt, payload, verifier_calls = _freeze_receipt(fixture, tmp_path)
    smoke_paths_before_load = tuple(fixture.smoke_paths)

    loaded = gguf.load_phase40_qwen_gguf_verification_receipt(repo_root=tmp_path)

    assert loaded == payload
    assert receipt.read_bytes() == gguf._canonical_json_bytes(loaded)
    assert tuple(fixture.smoke_paths) == smoke_paths_before_load
    assert verifier_calls == [True]


def test_fixed_receipt_loader_rejects_byte_tamper_before_upstream_load(tmp_path):
    fixture = _fixture(tmp_path)
    _export(fixture)
    receipt, payload, _verifier_calls = _freeze_receipt(fixture, tmp_path)
    tampered = dict(payload)
    tampered["export"] = {**payload["export"], "gguf_bytes": 999}
    receipt.write_bytes(gguf._canonical_json_bytes(tampered))

    with pytest.raises(RuntimeError, match="self-hash mismatch"):
        gguf.load_phase40_qwen_gguf_verification_receipt(repo_root=tmp_path)


@pytest.mark.parametrize(
    "upstream_field, value, message",
    [
        (
            "final_comparison_authority_sha256",
            "8" * 64,
            "stale.*final comparison authority",
        ),
        ("origin_request_sha256", "8" * 64, "wrong origin request"),
    ],
)
def test_fixed_receipt_loader_rejects_reself_hashed_upstream_drift(
    tmp_path,
    upstream_field,
    value,
    message,
):
    fixture = _fixture(tmp_path)
    _export(fixture)
    receipt, payload, _verifier_calls = _freeze_receipt(fixture, tmp_path)
    tampered = dict(payload)
    tampered["upstream"] = {**payload["upstream"], upstream_field: value}
    core = {key: item for key, item in tampered.items() if key != "receipt_sha256"}
    tampered["receipt_sha256"] = hashlib.sha256(
        gguf._canonical_json_bytes(core)
    ).hexdigest()
    receipt.write_bytes(gguf._canonical_json_bytes(tampered))

    with pytest.raises(RuntimeError, match=message):
        gguf.load_phase40_qwen_gguf_verification_receipt(repo_root=tmp_path)


@pytest.mark.parametrize(
    "selection_mutation, message",
    [
        (
            {"run_id": "phase40-qwen-qlora-full-seed42-v2"},
            "does not select.*Qwen QLoRA v1",
        ),
        (
            {
                "selected_checkpoint": {
                    "optimizer_step": 1245,
                    "artifact_identity": "checkpoint:unbound",
                    "safety_gate_passed": True,
                }
            },
            "checkpoint identity must be adapter-state-sha256",
        ),
    ],
)
def test_fixed_receipt_loader_rejects_reself_hashed_selection_drift(
    tmp_path,
    selection_mutation,
    message,
):
    fixture = _fixture(tmp_path)
    _export(fixture)
    receipt, payload, _verifier_calls = _freeze_receipt(fixture, tmp_path)
    tampered = dict(payload)
    tampered["selection"] = {**payload["selection"], **selection_mutation}
    core = {key: item for key, item in tampered.items() if key != "receipt_sha256"}
    tampered["receipt_sha256"] = hashlib.sha256(
        gguf._canonical_json_bytes(core)
    ).hexdigest()
    receipt.write_bytes(gguf._canonical_json_bytes(tampered))

    with pytest.raises((RuntimeError, ValueError), match=message):
        gguf.load_phase40_qwen_gguf_verification_receipt(repo_root=tmp_path)


def test_receipt_verifier_rejects_noncanonical_and_self_hash_tamper(tmp_path):
    fixture = _fixture(tmp_path)
    _export(fixture)
    receipt, payload, verifier_calls = _freeze_receipt(fixture, tmp_path)
    receipt.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="not canonical JSON"):
        gguf.verify_phase40_qwen_gguf_verification_receipt(
            repo_root=tmp_path,
            export_manifest_path=fixture.manifest,
            context=_verification_context(),
            manifest_verifier=_injected_manifest_verifier(fixture, verifier_calls),
        )

    tampered = dict(payload)
    tampered["export"] = {**payload["export"], "gguf_bytes": 999}
    receipt.write_bytes(gguf._canonical_json_bytes(tampered))
    with pytest.raises(RuntimeError, match="self-hash mismatch"):
        gguf.verify_phase40_qwen_gguf_verification_receipt(
            repo_root=tmp_path,
            export_manifest_path=fixture.manifest,
            context=_verification_context(),
            manifest_verifier=_injected_manifest_verifier(fixture, verifier_calls),
        )

    assert verifier_calls == [True]


@pytest.mark.parametrize(
    "context, message",
    [
        (
            replace(
                _verification_context(),
                final_comparison_authority_sha256="9" * 64,
            ),
            "stale.*final comparison authority",
        ),
        (
            replace(_verification_context(), origin_request_sha256="9" * 64),
            "wrong origin request",
        ),
        (
            replace(
                _verification_context(),
                selected_run_id="phase40-qwen-qlora-full-seed42-v2",
            ),
            "does not select.*Qwen QLoRA v1",
        ),
        (
            replace(
                _verification_context(),
                selected_checkpoint_identity="adapter-state-sha256:" + "9" * 64,
            ),
            "stale.*checkpoint",
        ),
    ],
)
def test_receipt_verifier_rejects_stale_upstream_or_selection_before_rerun(
    tmp_path,
    context,
    message,
):
    fixture = _fixture(tmp_path)
    _export(fixture)
    receipt, _payload, verifier_calls = _freeze_receipt(fixture, tmp_path)

    with pytest.raises(RuntimeError, match=message):
        gguf.verify_phase40_qwen_gguf_verification_receipt(
            repo_root=tmp_path,
            export_manifest_path=fixture.manifest,
            context=context,
            manifest_verifier=_injected_manifest_verifier(fixture, verifier_calls),
        )

    assert verifier_calls == [True]


@pytest.mark.parametrize(
    "verified, message",
    [
        (
            _fake_final_authority(origin_request_sha256="9" * 64),
            "wrong origin request",
        ),
        (
            _fake_final_authority(run_id="phase40-qwen-qlora-full-seed42-v2"),
            "fixed Qwen QLoRA v1 run",
        ),
        (
            _fake_final_authority(adaptation_mode=AdaptationMode.LORA),
            "non-canonical Qwen QLoRA v1 identity",
        ),
    ],
)
def test_receipt_freeze_rejects_final_authority_resolution_drift_before_export_rerun(
    tmp_path,
    monkeypatch,
    verified,
    message,
):
    fixture = _fixture(tmp_path)
    _export(fixture)
    verifier_calls: list[bool] = []
    monkeypatch.setattr(
        gguf._final_authority,
        "load_frozen_phase40_final_comparison_authority",
        lambda *, repo_root: verified,
    )

    with pytest.raises(RuntimeError, match=message):
        gguf.freeze_phase40_qwen_gguf_verification_receipt(
            repo_root=tmp_path,
            export_manifest_path=fixture.manifest,
            context=_verification_context(),
            manifest_verifier=_injected_manifest_verifier(fixture, verifier_calls),
        )

    assert verifier_calls == []
    assert not _receipt_path(tmp_path).exists()


def test_receipt_freeze_rejects_invalid_chronology_and_noncanonical_export_utc(tmp_path):
    fixture = _fixture(tmp_path)
    _export(fixture)
    calls: list[bool] = []

    with pytest.raises(RuntimeError, match="receipt chronology"):
        gguf.freeze_phase40_qwen_gguf_verification_receipt(
            repo_root=tmp_path,
            export_manifest_path=fixture.manifest,
            context=_verification_context(),
            manifest_verifier=_injected_manifest_verifier(fixture, calls),
            now=lambda: datetime(2026, 8, 25, 1, 1, tzinfo=timezone.utc),
        )
    assert calls == [True]
    assert not _receipt_path(tmp_path).exists()

    noncanonical_manifest = json.loads(fixture.manifest.read_text(encoding="utf-8"))
    noncanonical_manifest["started_at_utc"] = "2026-08-25T01:00:00.000000Z"
    fixture.manifest.write_bytes(gguf._canonical_json_bytes(noncanonical_manifest))
    with pytest.raises(RuntimeError, match="canonical UTC"):
        _freeze_receipt(fixture, tmp_path)


def test_receipt_freeze_rejects_traversal_and_absolute_path_leakage(tmp_path):
    fixture = _fixture(tmp_path)
    fixture.dependencies = replace(
        fixture.dependencies,
        smoke_loader=lambda _path: gguf.LoadSmokeResult(
            passed=True,
            loader=r"C:\Users\alice\private-loader.dll",
            loader_version="1.0",
            detail="constructor load completed",
        ),
    )
    _export(fixture)
    verifier_calls: list[bool] = []
    verifier = _injected_manifest_verifier(fixture, verifier_calls)

    traversing_repo_root = tmp_path / "child" / ".."
    with pytest.raises(ValueError, match="path traversal"):
        gguf.freeze_phase40_qwen_gguf_verification_receipt(
            repo_root=traversing_repo_root,
            export_manifest_path=fixture.manifest,
            context=_verification_context(),
            manifest_verifier=verifier,
        )

    traversing_manifest = (
        fixture.manifest.parent
        / ".."
        / fixture.manifest.parent.name
        / fixture.manifest.name
    )
    with pytest.raises(ValueError, match="path traversal"):
        gguf.freeze_phase40_qwen_gguf_verification_receipt(
            repo_root=tmp_path,
            export_manifest_path=traversing_manifest,
            context=_verification_context(),
            manifest_verifier=verifier,
        )

    original_manifest = fixture.manifest.read_bytes()
    traversing_payload = json.loads(original_manifest.decode("utf-8"))
    traversing_payload["output"]["path"] = str(
        fixture.output.parent
        / ".."
        / fixture.output.parent.name
        / fixture.output.name
    )
    fixture.manifest.write_bytes(gguf._canonical_json_bytes(traversing_payload))
    with pytest.raises(ValueError, match="path traversal"):
        gguf.freeze_phase40_qwen_gguf_verification_receipt(
            repo_root=tmp_path,
            export_manifest_path=fixture.manifest,
            context=_verification_context(),
            manifest_verifier=verifier,
            now=lambda: datetime(2026, 8, 25, 2, 5, tzinfo=timezone.utc),
        )
    fixture.manifest.write_bytes(original_manifest)

    with pytest.raises(ValueError, match="leaks an absolute filesystem path"):
        gguf.freeze_phase40_qwen_gguf_verification_receipt(
            repo_root=tmp_path,
            export_manifest_path=fixture.manifest,
            context=_verification_context(),
            manifest_verifier=verifier,
            now=lambda: datetime(2026, 8, 25, 2, 5, tzinfo=timezone.utc),
        )
    assert verifier_calls == [True, True]
    assert not _receipt_path(tmp_path).exists()


def test_receipt_verifier_rejects_changed_export_manifest_hash(tmp_path):
    fixture = _fixture(tmp_path)
    _export(fixture)
    receipt, _payload, verifier_calls = _freeze_receipt(fixture, tmp_path)
    changed_manifest = json.loads(fixture.manifest.read_text(encoding="utf-8"))
    changed_manifest["load_smoke"]["detail"] = "different valid smoke detail"
    fixture.manifest.write_bytes(gguf._canonical_json_bytes(changed_manifest))

    with pytest.raises(RuntimeError, match="stale for the export manifest"):
        gguf.verify_phase40_qwen_gguf_verification_receipt(
            repo_root=tmp_path,
            export_manifest_path=fixture.manifest,
            context=_verification_context(),
            manifest_verifier=_injected_manifest_verifier(fixture, verifier_calls),
        )

    assert verifier_calls == [True, True]


def test_receipt_freeze_rejects_non_q8_export_manifest(tmp_path):
    fixture = _fixture(tmp_path)
    _export(fixture)
    manifest = json.loads(fixture.manifest.read_text(encoding="utf-8"))
    manifest["outtype"] = "q4_0"
    fixture.manifest.write_bytes(gguf._canonical_json_bytes(manifest))
    verifier_calls: list[bool] = []

    with pytest.raises(RuntimeError, match="locked q8_0 outtype"):
        gguf.freeze_phase40_qwen_gguf_verification_receipt(
            repo_root=tmp_path,
            export_manifest_path=fixture.manifest,
            context=_verification_context(),
            manifest_verifier=_injected_manifest_verifier(fixture, verifier_calls),
            now=lambda: datetime(2026, 8, 25, 2, 5, tzinfo=timezone.utc),
        )

    assert verifier_calls == [True]
    assert not _receipt_path(tmp_path).exists()


@pytest.mark.parametrize("mutation", ["missing", "extra"])
def test_receipt_verifier_rejects_malformed_exact_schema(tmp_path, mutation):
    fixture = _fixture(tmp_path)
    _export(fixture)
    receipt, payload, verifier_calls = _freeze_receipt(fixture, tmp_path)
    malformed = dict(payload)
    if mutation == "missing":
        malformed.pop("converter")
    else:
        malformed["unexpected"] = True
    core = {key: value for key, value in malformed.items() if key != "receipt_sha256"}
    malformed["receipt_sha256"] = hashlib.sha256(
        gguf._canonical_json_bytes(core)
    ).hexdigest()
    receipt.write_bytes(gguf._canonical_json_bytes(malformed))

    with pytest.raises(RuntimeError, match="keys mismatch"):
        gguf.verify_phase40_qwen_gguf_verification_receipt(
            repo_root=tmp_path,
            export_manifest_path=fixture.manifest,
            context=_verification_context(),
            manifest_verifier=_injected_manifest_verifier(fixture, verifier_calls),
        )

    assert verifier_calls == [True]


def test_export_rejects_probe_before_model_load_or_output(tmp_path):
    fixture = _fixture(tmp_path, run_kind=RunKind.PROBE)

    with pytest.raises(RuntimeError, match="complete Phase 40 full run"):
        _export(fixture)

    assert not fixture.output.exists()
    assert not any(call[0] == "load_base" for call in fixture.calls)


def test_export_rejects_selected_adapter_tensor_identity_drift(tmp_path):
    fixture = _fixture(tmp_path)
    fixture.dependencies = replace(
        fixture.dependencies,
        selected_adapter_identity_resolver=lambda _path: "adapter-state-sha256:" + "0" * 64,
    )

    with pytest.raises(RuntimeError, match="adapter tensors differ"):
        _export(fixture)

    assert not any(call[0] == "load_base" for call in fixture.calls)
    assert not fixture.output.exists()


def test_export_fails_closed_when_merge_and_unload_is_unavailable(tmp_path):
    fixture = _fixture(tmp_path)
    fixture.dependencies = replace(
        fixture.dependencies,
        model_backend=replace(
            fixture.dependencies.model_backend,
            attach_adapter=lambda _model, _path: SimpleNamespace(
                is_loaded_in_4bit=False,
                config=SimpleNamespace(quantization_config=None),
                modules=lambda: (),
            ),
        ),
    )

    with pytest.raises(RuntimeError, match="merge_and_unload is unavailable"):
        _export(fixture)

    assert not fixture.output.exists()
    assert not fixture.manifest.exists()


def test_export_rejects_a_four_bit_base_before_adapter_attach(tmp_path):
    fixture = _fixture(tmp_path)
    fixture.dependencies = replace(
        fixture.dependencies,
        model_backend=replace(
            fixture.dependencies.model_backend,
            load_base_model=lambda _path: SimpleNamespace(
                is_loaded_in_4bit=True,
                config=SimpleNamespace(quantization_config=object()),
                modules=lambda: (),
            ),
        ),
    )

    with pytest.raises(RuntimeError, match="ordinary non-4bit base"):
        _export(fixture)

    assert not any(call[0] == "attach_adapter" for call in fixture.calls)
    assert not fixture.output.exists()


def test_export_rejects_unpinned_converter_before_model_load(tmp_path):
    fixture = _fixture(tmp_path)

    with pytest.raises(RuntimeError, match="fixed tool authority"):
        gguf.export_phase40_gguf(
            run_root=fixture.run_root,
            base_model_path=fixture.base_root,
            base_manifest_path=fixture.base_manifest,
            converter_script=fixture.converter,
            converter_sha256="0" * 64,
            output_path=fixture.output,
            dependencies=fixture.dependencies,
        )

    assert not any(call[0] == "load_base" for call in fixture.calls)


def test_export_rejects_wrong_converter_package_version(tmp_path):
    fixture = _fixture(tmp_path)
    fixture.dependencies = replace(
        fixture.dependencies,
        package_version_resolver=lambda _name: "0.18.0",
    )

    with pytest.raises(RuntimeError, match="gguf==0.19.0"):
        _export(fixture)

    assert not any(call[0] == "load_base" for call in fixture.calls)


def test_export_refuses_output_inside_immutable_run_root(tmp_path):
    fixture = _fixture(tmp_path)

    with pytest.raises(ValueError, match="outside the immutable full-run root"):
        gguf.export_phase40_gguf(
            run_root=fixture.run_root,
            base_model_path=fixture.base_root,
            base_manifest_path=fixture.base_manifest,
            converter_script=fixture.converter,
            converter_sha256=fixture.converter_sha256,
            output_path=fixture.run_root / "forbidden.gguf",
            dependencies=fixture.dependencies,
        )

    assert not (fixture.run_root / "forbidden.gguf").exists()


def test_verify_rejects_output_tamper_without_repeating_smoke(tmp_path):
    fixture = _fixture(tmp_path)
    _export(fixture)
    fixture.output.write_bytes(b"tampered")

    with pytest.raises(RuntimeError, match="byte count|SHA-256"):
        gguf.verify_phase40_gguf_export(
            fixture.manifest,
            dependencies=fixture.dependencies,
        )

    assert fixture.smoke_paths == [fixture.output]


def test_export_removes_published_output_when_load_smoke_fails(tmp_path):
    fixture = _fixture(tmp_path)
    fixture.dependencies = replace(
        fixture.dependencies,
        smoke_loader=lambda _path: gguf.LoadSmokeResult(
            passed=False,
            loader="fake.Llama",
            loader_version="1.0",
            detail="load failed",
        ),
    )

    with pytest.raises(RuntimeError, match="load smoke did not pass"):
        _export(fixture)

    assert not fixture.output.exists()
    assert not fixture.manifest.exists()


def test_default_merge_backend_never_executes_remote_model_code(monkeypatch, tmp_path):
    calls: list[tuple[str, dict[str, object]]] = []

    class FakeAutoTokenizer:
        @staticmethod
        def from_pretrained(path, **kwargs):
            calls.append((f"tokenizer:{path}", kwargs))
            return object()

    class FakeAutoModel:
        @staticmethod
        def from_pretrained(path, **kwargs):
            calls.append((f"model:{path}", kwargs))
            return object()

    fake_transformers = SimpleNamespace(
        AutoTokenizer=FakeAutoTokenizer,
        AutoModelForCausalLM=FakeAutoModel,
    )
    fake_torch = SimpleNamespace(bfloat16="bfloat16")
    real_import = importlib.import_module

    def fake_import(name):
        if name == "transformers":
            return fake_transformers
        if name == "torch":
            return fake_torch
        return real_import(name)

    monkeypatch.setattr(importlib, "import_module", fake_import)
    backend = gguf._default_model_backend()
    backend.load_tokenizer(tmp_path)
    backend.load_base_model(tmp_path)

    assert len(calls) == 2
    assert all(kwargs["local_files_only"] is True for _, kwargs in calls)
    assert all(kwargs["trust_remote_code"] is False for _, kwargs in calls)


def test_export_removes_partial_cross_device_publication_on_interrupt(tmp_path, monkeypatch):
    fixture = _fixture(tmp_path)

    def interrupted_copy(_source, destination, *, length):
        assert length == 16 * 1024 * 1024
        destination.write(b"partial")
        raise KeyboardInterrupt

    monkeypatch.setattr(gguf.shutil, "copyfileobj", interrupted_copy)
    with pytest.raises(KeyboardInterrupt):
        _export(fixture)

    assert not fixture.output.exists()
    assert not fixture.manifest.exists()


def test_export_refuses_overwrite_and_does_not_mutate_registry_like_files(tmp_path):
    fixture = _fixture(tmp_path)
    registry = tmp_path / "model-registry.json"
    registry.write_bytes(b"registry-before")
    fixture.output.parent.mkdir()
    fixture.output.write_bytes(b"existing")

    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        _export(fixture)

    assert fixture.output.read_bytes() == b"existing"
    assert registry.read_bytes() == b"registry-before"
