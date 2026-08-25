from __future__ import annotations

import ast
from dataclasses import dataclass
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.model_adaptation import phase40_operator as operator


class _Template:
    sha256 = "a" * 64

    def __init__(self, controlled: object | None = None) -> None:
        self.controlled = controlled
        self.verified: list[object] = []

    def materialize_for_validation(self):  # noqa: ANN201
        return self.controlled

    def verify_runtime_config(self, value: object) -> None:
        self.verified.append(value)


def _run(
    run_id: str,
    family: str,
    mode: str,
    *,
    returned_root: str | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        run_id=run_id,
        model_family=SimpleNamespace(value=family),
        adaptation_mode=SimpleNamespace(value=mode),
        run_kind="full",
        returned_root=returned_root or f"data/models/phase40/full/{run_id}",
        step_origin=0,
        probe_parent=None,
    )


def _request(run: SimpleNamespace, template: _Template | None = None) -> SimpleNamespace:
    if template is None:
        if run.model_family.value == "qwen":
            model_id = "Qwen/Qwen3-4B-Instruct-2507"
            model_revision = "cdbee75f17c01a7cc42f958dc650907174af0554"
            controls = (
                SimpleNamespace(name="local_files_only", value=True),
                SimpleNamespace(name="trust_remote_code", value=False),
            )
        else:
            model_id = "vinai/phobert-base-v2"
            model_revision = "e966aac8cb889325e073aa5f28ff70aca4dbc8c3"
            controls = (SimpleNamespace(name="local_files_only", value=True),)
        template = _Template(
            SimpleNamespace(
                model_id=model_id,
                model_revision=model_revision,
                additional_controls=controls,
            )
        )
    selected_template = template
    return SimpleNamespace(
        runs=(run,),
        control_template_by_run={run.run_id: selected_template},
        control_template_digest_by_run={run.run_id: selected_template.sha256},
        input_bundle=SimpleNamespace(),
    )


def _base_model_args(tmp_path: Path, family: str) -> tuple[str, ...]:
    snapshot, manifest = operator._canonical_base_model_paths(tmp_path, family)
    return (
        "--base-model-path",
        str(snapshot),
        "--base-model-manifest-path",
        str(manifest),
    )


def test_module_import_surface_is_standard_library_only() -> None:
    tree = ast.parse(Path(operator.__file__).read_text(encoding="utf-8"))
    imports = tuple(
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    )
    assert not any(name == "src" or name.startswith("src.") for name in imports)


def test_parser_exposes_only_the_eleven_slim_phase40_commands() -> None:
    parser = operator.build_parser()
    choices = next(
        action.choices
        for action in parser._actions  # noqa: SLF001 - argparse contract inspection
        if getattr(action, "choices", None)
    )
    assert set(choices) == {
        "phase40-verify-input-bundle",
        "phase40-verify-run-request",
        "phase40-acquire-model",
        "phase40-doctor",
        "phase40-verify-resume",
        "phase40-train-qwen",
        "phase40-train-phobert",
        "phase40-verify-run-evidence",
        "phase40-render-graphs",
        "phase40-validate-notebooks",
        "phase40-local-decision",
    }


def test_local_decision_command_delegates_lazily(monkeypatch, tmp_path: Path) -> None:
    calls: list[object] = []
    fake = SimpleNamespace(
        run_operator_stage=lambda args: calls.append(args) or {"status": "preflighted"}
    )
    monkeypatch.setattr(operator, "_import_module", lambda name: fake)
    result = operator.main(
        (
            "phase40-local-decision",
            "--stage",
            "verify",
            "--decision-root",
            str(tmp_path / "decision"),
        )
    )
    assert result == 0
    assert len(calls) == 1


def test_local_decision_parser_exposes_exact_single_lora_retry_stage() -> None:
    args = operator.build_parser().parse_args(
        (
            "phase40-local-decision",
            "--stage",
            "lora-retry-1",
            "--decision-root",
            "decision",
            "--repo-root",
            ".",
        )
    )
    assert args.stage == "lora-retry-1"


def test_model_acquisition_requires_explicit_positive_authority_before_request_load(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        operator,
        "_load_verified_request",
        lambda *args, **kwargs: pytest.fail("request loaded without acquisition authority"),
    )
    assert operator.main(
        (
            "phase40-acquire-model",
            "--request-path",
            "data/models/phase40/full-run-request.json",
            "--run-id",
            "qwen-lora",
        )
    ) == 1


def test_authorized_model_acquisition_uses_only_request_pins_and_seals_snapshot(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    controlled = SimpleNamespace(
        model_id="Qwen/Qwen3-4B-Instruct-2507",
        model_revision="cdbee75f17c01a7cc42f958dc650907174af0554",
        additional_controls=(
            SimpleNamespace(name="local_files_only", value=True),
            SimpleNamespace(name="trust_remote_code", value=False),
        ),
    )
    run = _run("qwen-lora", "qwen", "lora")
    request = _request(run, _Template(controlled))
    seen: dict[str, object] = {}
    snapshot = SimpleNamespace(
        manifest_sha256="a" * 64,
        snapshot_content_sha256="b" * 64,
    )

    class Acquisition:
        def snapshot_download_kwargs(self):  # noqa: ANN201
            return {
                "repo_id": controlled.model_id,
                "revision": controlled.model_revision,
                "local_dir": str(
                    tmp_path / "data/models/phase40/base/qwen3-4b-instruct-2507"
                ),
            }

    def build(path, **kwargs):  # noqa: ANN001, ANN003, ANN202
        seen["build"] = (path, kwargs)
        return Acquisition()

    def download(**kwargs):  # noqa: ANN003, ANN202
        seen["download"] = kwargs
        destination = Path(kwargs["local_dir"])
        destination.mkdir(parents=True)
        return str(destination)

    def seal(path, **kwargs):  # noqa: ANN001, ANN003, ANN202
        seen["seal"] = (path, kwargs)
        kwargs["manifest_path"].write_text("{}\n", encoding="utf-8")
        return snapshot

    def validate(path, **kwargs):  # noqa: ANN001, ANN003, ANN202
        seen["validate"] = (path, kwargs)
        return snapshot

    fake_backend = SimpleNamespace(
        build_qwen_base_model_acquisition_request=build,
        seal_qwen_base_model_snapshot=seal,
        validate_qwen_base_model_snapshot=validate,
    )
    fake_hub = SimpleNamespace(snapshot_download=download)
    monkeypatch.setattr(
        operator,
        "_load_verified_request",
        lambda *args, **kwargs: (request, tmp_path.resolve()),
    )
    monkeypatch.setattr(operator, "_package_version", lambda name: "1.16.1")
    monkeypatch.setattr(
        operator,
        "_import_module",
        lambda name: fake_hub if name == "huggingface_hub" else fake_backend,
    )
    assert operator.main(
        (
            "phase40-acquire-model",
            "--request-path",
            "data/models/phase40/full-run-request.json",
            "--repo-root",
            str(tmp_path),
            "--run-id",
            "qwen-lora",
            "--authorize-model-acquisition",
        )
    ) == 0
    assert seen["download"] == {
        "repo_id": controlled.model_id,
        "revision": controlled.model_revision,
        "local_dir": str(
            tmp_path / "data/models/phase40/base/qwen3-4b-instruct-2507"
        ),
        "force_download": False,
        "local_files_only": False,
        "token": False,
    }
    report = json.loads(capsys.readouterr().out)
    assert report["model_acquisition_performed"] is True
    assert report["verified"] is True


def test_existing_phobert_snapshot_is_reverified_without_network(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    controlled = SimpleNamespace(
        model_id="vinai/phobert-base-v2",
        model_revision="e966aac8cb889325e073aa5f28ff70aca4dbc8c3",
        additional_controls=(SimpleNamespace(name="local_files_only", value=True),),
    )
    run = _run("phobert", "phobert", "classification-head")
    request = _request(run, _Template(controlled))
    snapshot_path, manifest_path = operator._canonical_base_model_paths(
        tmp_path, "phobert"
    )
    snapshot_path.mkdir(parents=True)
    manifest_path.write_text("{}\n", encoding="utf-8")
    snapshot = SimpleNamespace(
        manifest_sha256="c" * 64,
        snapshot_content_sha256="d" * 64,
    )
    seen: dict[str, object] = {}

    def validate(path, **kwargs):  # noqa: ANN001, ANN003, ANN202
        seen["validate"] = (path, kwargs)
        return snapshot

    fake_backend = SimpleNamespace(
        build_phobert_base_model_acquisition_request=lambda *args, **kwargs: pytest.fail(
            "existing verified snapshot triggered acquisition"
        ),
        seal_phobert_base_model_snapshot=lambda *args, **kwargs: pytest.fail(
            "existing verified snapshot was resealed"
        ),
        validate_phobert_base_model_snapshot=validate,
    )
    monkeypatch.setattr(
        operator,
        "_load_verified_request",
        lambda *args, **kwargs: (request, tmp_path.resolve()),
    )
    monkeypatch.setattr(operator, "_package_version", lambda name: "1.16.1")

    def import_only_backend(name: str):  # noqa: ANN202
        if name == "huggingface_hub":
            pytest.fail("verified existing snapshot imported a network client")
        return fake_backend

    monkeypatch.setattr(operator, "_import_module", import_only_backend)
    assert operator.main(
        (
            "phase40-acquire-model",
            "--request-path",
            "data/models/phase40/full-run-request.json",
            "--repo-root",
            str(tmp_path),
            "--run-id",
            "phobert",
            "--authorize-model-acquisition",
        )
    ) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["model_acquisition_performed"] is False
    assert seen["validate"][1]["manifest_path"] == manifest_path  # type: ignore[index]


def test_acquisition_backend_cannot_change_download_identity_before_hub_import(
    tmp_path: Path,
    monkeypatch,
) -> None:
    run = _run("qwen-lora", "qwen", "lora")
    request = _request(run)

    class DriftedAcquisition:
        def snapshot_download_kwargs(self):  # noqa: ANN201
            return {
                "repo_id": "attacker/alternate",
                "revision": "0" * 40,
                "local_dir": str(tmp_path / "alternate"),
            }

    fake_backend = SimpleNamespace(
        build_qwen_base_model_acquisition_request=lambda *args, **kwargs: DriftedAcquisition(),
        seal_qwen_base_model_snapshot=lambda *args, **kwargs: None,
        validate_qwen_base_model_snapshot=lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        operator,
        "_load_verified_request",
        lambda *args, **kwargs: (request, tmp_path.resolve()),
    )
    monkeypatch.setattr(operator, "_package_version", lambda name: "1.16.1")

    def import_without_hub(name: str):  # noqa: ANN202
        if name == "huggingface_hub":
            pytest.fail("drifted acquisition imported the network client")
        return fake_backend

    monkeypatch.setattr(operator, "_import_module", import_without_hub)
    assert operator.main(
        (
            "phase40-acquire-model",
            "--request-path",
            "data/models/phase40/full-run-request.json",
            "--repo-root",
            str(tmp_path),
            "--run-id",
            "qwen-lora",
            "--authorize-model-acquisition",
        )
    ) == 1


def test_request_root_is_inferred_only_from_the_canonical_relative_path(tmp_path: Path) -> None:
    request_path = tmp_path / "data/models/phase40/full-run-request.json"
    assert operator._repo_root_for_request(request_path, None) == tmp_path.resolve()
    with pytest.raises(ValueError, match="canonical repository-relative"):
        operator._repo_root_for_request(tmp_path / "request.json", tmp_path)


def test_verify_input_bundle_delegates_to_archive_verifier(tmp_path: Path, monkeypatch, capsys) -> None:
    reference_path = tmp_path / "reference.json"
    reference_path.write_text('{"archive_sha256":"value"}', encoding="utf-8")
    seen: dict[str, object] = {}
    reference = SimpleNamespace(archive_sha256="f" * 64)
    contract = SimpleNamespace(
        train_snapshot=SimpleNamespace(rows=(1, 2)),
        validation_snapshot=SimpleNamespace(rows=(3,)),
    )

    class ReferenceModel:
        @classmethod
        def model_validate(cls, payload):  # noqa: ANN001, ANN206
            seen["payload"] = payload
            return reference

    def verify(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
        seen["verify_args"] = args
        seen["verify_kwargs"] = kwargs
        return contract

    fake_handoff = SimpleNamespace(
        InputBundleReference=ReferenceModel,
        verify_phase40_input_bundle=verify,
    )
    monkeypatch.setattr(operator, "_import_module", lambda name: fake_handoff)
    status = operator.main(
        (
            "phase40-verify-input-bundle",
            "--archive-path",
            "bundle.zip",
            "--reference-path",
            str(reference_path),
            "--repo-root",
            ".",
            "--extraction-root",
            "input",
        )
    )
    assert status == 0
    assert seen["verify_kwargs"]["materialize"] is True
    assert json.loads(capsys.readouterr().out)["validation_records"] == 1


def test_duplicate_json_keys_fail_closed(tmp_path: Path) -> None:
    path = tmp_path / "duplicate.json"
    path.write_text('{"run_id":"one","run_id":"two"}', encoding="utf-8")
    with pytest.raises(ValueError, match="invalid strict JSON"):
        operator._read_json_object(path)


def test_doctor_checks_request_input_and_capabilities_without_training(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    controlled = SimpleNamespace(
        model_id="Qwen/Qwen3-4B-Instruct-2507",
        model_revision="b" * 40,
        additional_controls=(
            SimpleNamespace(name="local_files_only", value=True),
            SimpleNamespace(name="trust_remote_code", value=False),
        ),
    )
    template = _Template(controlled)
    run = _run("qwen-lora", "qwen", "lora")
    request = _request(run, template)
    request.input_bundle = SimpleNamespace()
    checked: list[str] = []
    monkeypatch.setattr(
        operator,
        "_load_verified_request",
        lambda *args, **kwargs: (request, tmp_path),
    )
    monkeypatch.setattr(
        operator,
        "_verify_materialized_input",
        lambda *args, **kwargs: checked.append("input"),
    )
    monkeypatch.setattr(
        operator,
        "_runtime_capabilities",
        lambda *args: {
            "cuda_available": True,
            "dependencies": {"torch": "pinned"},
            "model_acquisition_performed": False,
            "training_performed": False,
        },
    )
    monkeypatch.setattr(
        operator,
        "_validate_base_model_cli_paths",
        lambda **kwargs: SimpleNamespace(
            manifest_sha256="a" * 64,
            snapshot_content_sha256="b" * 64,
        ),
    )
    status = operator.main(
        (
            "phase40-doctor",
            "--model-family",
            "qwen",
            "--adaptation-mode",
            "lora",
            "--run-kind",
            "full",
            "--model-revision",
            "b" * 40,
            "--run-request-path",
            str(tmp_path / "request.json"),
            "--input-root",
            "input",
        )
        + _base_model_args(tmp_path, "qwen")
    )
    assert status == 0
    assert checked == ["input"]
    report = json.loads(capsys.readouterr().out)
    assert report["request_identity_verified"] is True
    assert report["training_performed"] is False


def test_doctor_capability_probe_blocks_pin_drift_before_runtime_import(monkeypatch) -> None:
    monkeypatch.setattr(
        operator,
        "_package_version",
        lambda distribution: "unexpected" if distribution == "torch" else {
            **operator._QWEN_DEPENDENCIES,
            "bitsandbytes": "0.50.1",
        }[distribution],
    )
    monkeypatch.setattr(
        operator,
        "_import_module",
        lambda name: pytest.fail(f"runtime import occurred before pin validation: {name}"),
    )
    with pytest.raises(RuntimeError, match="package version mismatch for torch"):
        operator._runtime_capabilities("qwen", "qlora")


def test_latest_resume_is_rejected_before_backend_import(monkeypatch) -> None:
    monkeypatch.setattr(
        operator,
        "_import_module",
        lambda name: pytest.fail(f"unexpected import: {name}"),
    )
    selected = _run("qwen-lora", "qwen", "lora")
    with pytest.raises(ValueError, match="latest"):
        operator._verify_resume_checkpoint(
            Path("latest"),
            request=_request(selected),
            selected_run=selected,
            repo_root=Path.cwd(),
            base_model_path=Path("unused-model"),
            base_model_manifest_path=Path("unused-manifest.json"),
        )


def test_exact_qwen_resume_uses_backend_manifest_verifier(
    tmp_path: Path,
    monkeypatch,
) -> None:
    checkpoint = tmp_path / "qwen-lora" / "trainer" / "checkpoint-4"
    checkpoint.mkdir(parents=True)
    (checkpoint / "phase40-resume-manifest.json").write_text(
        json.dumps({"controlled_config": {"identity": "frozen"}}),
        encoding="utf-8",
    )
    controlled = object()
    calls: list[tuple[Path, dict[str, object]]] = []

    class ResumeModel:
        @classmethod
        def model_validate(cls, payload):  # noqa: ANN001, ANN206
            assert payload == {"identity": "frozen"}
            return controlled

    fake_evidence = SimpleNamespace(ResumeControlledConfig=ResumeModel)

    def verify(path, **kwargs):  # noqa: ANN001, ANN003, ANN202
        calls.append((path, kwargs))
        return None

    fake_training = SimpleNamespace(
        PHASE40_RESUME_MANIFEST_NAME="phase40-resume-manifest.json",
        _read_checkpoint_resume_manifest=verify,
    )
    monkeypatch.setattr(
        operator,
        "_import_module",
        lambda name: fake_training if name.endswith("training") else fake_evidence,
    )
    request_controlled = SimpleNamespace(
        model_id="Qwen/Qwen3-4B-Instruct-2507",
        model_revision="cdbee75f17c01a7cc42f958dc650907174af0554",
        additional_controls=(
            SimpleNamespace(name="local_files_only", value=True),
            SimpleNamespace(name="trust_remote_code", value=False),
        ),
    )
    template = _Template(request_controlled)
    selected = _run("qwen-lora", "qwen", "lora")
    base_model_snapshot = object()
    monkeypatch.setattr(
        operator,
        "_validate_base_model_cli_paths",
        lambda **kwargs: base_model_snapshot,
    )
    base_model_path, base_model_manifest_path = operator._canonical_base_model_paths(
        tmp_path, "qwen"
    )
    payload = operator._verify_resume_checkpoint(
        checkpoint,
        request=_request(selected, template),
        selected_run=selected,
        repo_root=tmp_path,
        base_model_path=base_model_path,
        base_model_manifest_path=base_model_manifest_path,
    )
    assert payload["controlled_config"] == {"identity": "frozen"}
    assert calls == [
        (
            checkpoint.resolve(),
            {
                "controlled_config": controlled,
                "event_path": (
                    tmp_path / "data/models/phase40/full/qwen-lora/events.jsonl"
                ).resolve(),
                "base_model_snapshot": base_model_snapshot,
                "require_cumulative_history": True,
            },
        )
    ]
    assert template.verified == [controlled]


def test_exact_phobert_resume_uses_public_backend_verifier() -> None:
    checkpoint = Path("work/trainer/checkpoint-7")
    manifest = SimpleNamespace(
        model_dump=lambda **kwargs: {"checkpoint_step": 7, "run_id": "phobert"}
    )
    seen: dict[str, object] = {}

    def verify(path, **kwargs):  # noqa: ANN001, ANN003, ANN202
        seen["path"] = path
        seen["kwargs"] = kwargs
        return manifest, (object(),)

    config = object()
    controlled = object()
    validation = object()
    payload = operator._verify_phobert_resume_checkpoint(
        checkpoint,
        phobert=SimpleNamespace(verify_phobert_resume_checkpoint=verify),
        config=config,
        controlled_config=controlled,
        validation_snapshot=validation,
    )
    assert payload == {"checkpoint_step": 7, "run_id": "phobert"}
    assert seen == {
        "path": checkpoint,
        "kwargs": {
            "config": config,
            "controlled_config": controlled,
            "validation_snapshot": validation,
            "base_model_snapshot": None,
        },
    }


def test_qwen_command_uses_only_typed_request_archive_contract_and_new_runner(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    run = _run(
        "qwen-lora",
        "qwen",
        "lora",
        returned_root="data/models/phase40/full/qwen-lora",
    )
    request = _request(run)
    contract = object()
    seen: dict[str, object] = {}
    fake_evidence = SimpleNamespace(status=SimpleNamespace(value="complete"))

    def build(**kwargs):  # noqa: ANN003, ANN202
        seen["build"] = kwargs
        return object()

    def execute(config, **kwargs):  # noqa: ANN001, ANN003, ANN202
        seen["execute"] = (config, kwargs)
        return {
            "verified_evidence": fake_evidence,
            "safety_gate_passed": True,
        }

    fake_training = SimpleNamespace(
        build_phase40_qwen_training_config=build,
        run_phase40_qwen_training=execute,
    )
    monkeypatch.setattr(
        operator,
        "_load_verified_request",
        lambda *args, **kwargs: (request, tmp_path.resolve()),
    )
    monkeypatch.setattr(operator, "_sanitize_raw_argv", lambda raw: tuple(raw))
    monkeypatch.setattr(operator, "_verify_input_archive", lambda **kwargs: contract)
    monkeypatch.setattr(
        operator,
        "_validate_base_model_cli_paths",
        lambda **kwargs: object(),
    )
    monkeypatch.setattr(operator, "_import_module", lambda name: fake_training)
    argv = (
        "phase40-train-qwen",
        "--adaptation-mode",
        "lora",
        "--run-kind",
        "full",
        "--request-path",
        "data/models/phase40/full-run-request.json",
        "--repo-root",
        str(tmp_path),
        "--input-archive",
        "bundle.zip",
        "--extraction-root",
        "input",
        "--run-id",
        "qwen-lora",
        "--output-root",
        str(tmp_path / "work"),
    ) + _base_model_args(tmp_path, "qwen")
    assert operator.main(argv) == 0
    assert seen["build"]["data_contract"] is contract
    assert seen["build"]["run_request"] is request
    assert seen["build"]["base_model_path"] == (
        tmp_path / "data/models/phase40/base/qwen3-4b-instruct-2507"
    ).resolve()
    assert seen["build"]["base_model_manifest_path"] == (
        tmp_path / "data/models/phase40/base/qwen3-4b-instruct-2507.provenance.json"
    ).resolve()
    assert seen["build"]["sanitized_argv"] == argv
    assert seen["execute"][1]["data_contract"] is contract
    assert json.loads(capsys.readouterr().out)["verified"] is True
    source = Path(operator.__file__).read_text(encoding="utf-8")
    assert "preflight_phase40_inputs" not in source
    assert "ModelRegistry" not in source


def test_qwen_command_rejects_run_mode_drift_before_training(tmp_path: Path, monkeypatch) -> None:
    run = _run("qwen-qlora", "qwen", "qlora")
    request = _request(run)
    monkeypatch.setattr(
        operator,
        "_load_verified_request",
        lambda *args, **kwargs: (request, tmp_path),
    )
    status = operator.main(
        (
            "phase40-train-qwen",
            "--adaptation-mode",
            "lora",
            "--run-kind",
            "full",
            "--request-path",
            "request.json",
            "--input-archive",
            "bundle.zip",
            "--extraction-root",
            "input",
            "--run-id",
            "qwen-qlora",
            "--output-root",
            "work",
        )
        + _base_model_args(tmp_path, "qwen")
    )
    assert status == 1


def _phobert_controlled() -> SimpleNamespace:
    return SimpleNamespace(
        experiment_identity=SimpleNamespace(model_family=SimpleNamespace(value="phobert")),
        model_id="vinai/phobert-base-v2",
        model_revision="e" * 40,
        seed=42,
        data_seed=42,
        max_sequence_length=256,
        per_device_train_batch_size=16,
        gradient_accumulation_steps=1,
        world_size=1,
        num_train_epochs=3.0,
        max_optimizer_steps=312,
        gradient_checkpointing=False,
        optimizer=SimpleNamespace(
            learning_rate=2e-5,
            weight_decay=0.01,
            optimizer="adamw_torch",
            lr_scheduler_type="linear",
            warmup_steps=0,
            warmup_ratio=0.1,
            max_grad_norm=1.0,
        ),
        precision=SimpleNamespace(bf16=False, fp16=True, tf32=False),
        cadence=SimpleNamespace(
            logging_steps=10,
            evaluation_steps=50,
            save_steps=50,
            save_total_limit=2,
        ),
        additional_controls=(SimpleNamespace(name="local_files_only", value=True),),
        accelerator=object(),
    )


def test_phobert_command_builds_all_controls_from_request_and_uses_work_root(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    controlled = _phobert_controlled()
    template = _Template(controlled)
    run = _run(
        "phobert",
        "phobert",
        "classification-head",
        returned_root="data/models/phase40/full/phobert",
    )
    request = _request(run, template)
    contract = object()
    seen: dict[str, object] = {}

    class FakeConfig:
        __dataclass_fields__ = {"work_root": object()}

        def __init__(self, **kwargs) -> None:  # noqa: ANN003
            self.values = kwargs
            seen["config"] = kwargs

    def build_control(config, supplied_contract, *, accelerator):  # noqa: ANN001, ANN202
        assert supplied_contract is contract
        assert accelerator is controlled.accelerator
        return controlled

    result = SimpleNamespace(
        selection=SimpleNamespace(safety_gate_passed=True),
        evidence=SimpleNamespace(status=SimpleNamespace(value="complete")),
    )
    fake_phobert = SimpleNamespace(
        PhoBertTrainingConfig=FakeConfig,
        build_phobert_controlled_config=build_control,
        run_phobert_training=lambda *args, **kwargs: result,
    )
    fake_handoff = SimpleNamespace(transfer_authority_from_request=lambda value: "authority")
    monkeypatch.setattr(
        operator,
        "_load_verified_request",
        lambda *args, **kwargs: (request, tmp_path.resolve()),
    )
    monkeypatch.setattr(operator, "_sanitize_raw_argv", lambda raw: tuple(raw))
    monkeypatch.setattr(operator, "_verify_input_archive", lambda **kwargs: contract)
    monkeypatch.setattr(
        operator,
        "_validate_base_model_cli_paths",
        lambda **kwargs: object(),
    )
    monkeypatch.setattr(
        operator,
        "_import_module",
        lambda name: fake_handoff if name.endswith("phase40_handoff") else fake_phobert,
    )
    argv = (
        "phase40-train-phobert",
        "--request-path",
        "data/models/phase40/full-run-request.json",
        "--repo-root",
        str(tmp_path),
        "--input-archive",
        "bundle.zip",
        "--extraction-root",
        "input",
        "--run-id",
        "phobert",
        "--output-root",
        str(tmp_path / "work"),
    ) + _base_model_args(tmp_path, "phobert")
    assert operator.main(argv) == 0
    assert seen["config"]["work_root"] == (tmp_path / "work").resolve()
    assert seen["config"]["run_bundle_root"] == (
        tmp_path / "data/models/phase40/full/phobert"
    ).resolve()
    assert seen["config"]["max_optimizer_steps"] == 312
    assert seen["config"]["local_base_model_path"] == (
        tmp_path / "data/models/phase40/base/phobert-base-v2"
    ).resolve()
    assert seen["config"]["base_model_provenance_path"] == (
        tmp_path / "data/models/phase40/base/phobert-base-v2.provenance.json"
    ).resolve()
    assert template.verified == [controlled]
    assert json.loads(capsys.readouterr().out)["status"] == "complete"


def test_evidence_command_verifies_complete_bundle_lazily(tmp_path: Path, monkeypatch, capsys) -> None:
    evidence = SimpleNamespace(run_id="run-one", status=SimpleNamespace(value="complete"))
    fake = SimpleNamespace(verify_phase40_bundle=lambda root: evidence)
    monkeypatch.setattr(operator, "_import_module", lambda name: fake)
    assert operator.main(
        ("phase40-verify-run-evidence", "--run-root", str(tmp_path))
    ) == 0
    assert json.loads(capsys.readouterr().out)["run_id"] == "run-one"


def test_graph_command_verifies_before_and_after_render(tmp_path: Path, monkeypatch) -> None:
    evidence = SimpleNamespace(run_id="run-one")
    calls: list[str] = []

    def verify(root):  # noqa: ANN001, ANN202
        calls.append("verify")
        return evidence

    def render(root, **kwargs):  # noqa: ANN001, ANN003, ANN202
        calls.append("render")
        return SimpleNamespace(graph_id="loss-curves")

    monkeypatch.setattr(
        operator,
        "_import_module",
        lambda name: (
            SimpleNamespace(render_phase40_graphs=render)
            if name.endswith("phase40_graphs")
            else SimpleNamespace(verify_phase40_bundle=verify)
        ),
    )
    assert operator.main(("phase40-render-graphs", "--run-root", str(tmp_path))) == 0
    assert calls == ["verify", "render", "verify"]


def test_notebook_validator_returns_nonzero_and_prints_every_issue(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    fake = SimpleNamespace(
        validate_phase40_notebooks=lambda root: ("first issue", "second issue")
    )
    monkeypatch.setattr(operator, "_import_module", lambda name: fake)
    assert operator.main(
        ("phase40-validate-notebooks", "--root", str(tmp_path))
    ) == 1
    assert capsys.readouterr().err.splitlines() == ["first issue", "second issue"]
