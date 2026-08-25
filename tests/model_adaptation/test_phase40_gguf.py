"""Contract tests for the standalone Phase 40 GGUF exporter."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
import hashlib
import importlib
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
                "run_id": "qwen-qlora-full",
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
        run_id="qwen-qlora-full",
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
