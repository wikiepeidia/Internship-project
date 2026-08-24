"""Fixture-only proof tests for explicit Phase 40 LoRA and QLoRA modes."""

from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys
from types import ModuleType
from types import SimpleNamespace

import pytest

from src.data_pipeline.schemas import DatasetRecord
from src.model_adaptation.phase40_contract import (
    CanonicalSnapshotRow,
    CanonicalSplitSnapshot,
    HeldOutIdentity,
    Phase40DataContract,
    SplitIdentity,
    derive_snapshot_row_id,
)
from src.model_adaptation.phase40_modes import (
    APPROVED_BITSANDBYTES_VERSION,
    AdaptationMode,
    AdapterGradientCheck,
    ExperimentIdentity,
    ModelFamily,
    QuantizationProof,
    QwenPreloadCapabilities,
    ResolvedQwenMode,
    RunKind,
    prove_qwen_mode,
    prove_qwen_preload,
)
from src.model_adaptation.schemas import PilotSelection
from src.model_adaptation.training import (
    DEFAULT_TARGET_MODULES,
    _run_adapter_gradient_probe,
    _prove_saved_adapter_matches_live,
    _validate_qwen_training_device,
    build_training_config,
    run_training,
)


class Linear4bit:
    pass


Linear4bit.__module__ = "bitsandbytes.nn.modules"


@pytest.fixture(autouse=True)
def _fixture_bitsandbytes_runtime(monkeypatch):
    runtime = ModuleType("bitsandbytes")
    runtime.__version__ = APPROVED_BITSANDBYTES_VERSION
    runtime.nn = SimpleNamespace(Linear4bit=Linear4bit)
    monkeypatch.setitem(sys.modules, "bitsandbytes", runtime)


class Dense:
    pass


class FakeParameter:
    def __init__(self, *, requires_grad: bool) -> None:
        self.requires_grad = requires_grad


class FakeModel:
    def __init__(
        self,
        *,
        loaded_in_4bit: bool,
        modules: tuple[object, ...],
        parameters: tuple[tuple[str, FakeParameter], ...],
    ) -> None:
        self.is_loaded_in_4bit = loaded_in_4bit
        self._modules = modules
        self._parameters = parameters

    def modules(self):
        return iter(self._modules)

    def named_parameters(self):
        return iter(self._parameters)


def _identity(mode: AdaptationMode) -> ExperimentIdentity:
    return ExperimentIdentity(ModelFamily.QWEN, mode, RunKind.FULL)


def _qlora_capabilities(**changes) -> QwenPreloadCapabilities:
    values = {
        "cuda_available": True,
        "bitsandbytes_imported": True,
        "bitsandbytes_version": APPROVED_BITSANDBYTES_VERSION,
        "bitsandbytes_config_available": True,
        "linear4bit_type": Linear4bit,
        "kbit_preparation_available": True,
    }
    values.update(changes)
    return QwenPreloadCapabilities(**values)


def _lora_model() -> FakeModel:
    return FakeModel(
        loaded_in_4bit=False,
        modules=(Dense(),),
        parameters=(
            ("base.weight", FakeParameter(requires_grad=False)),
            ("adapter.lora_A.weight", FakeParameter(requires_grad=True)),
            ("adapter.lora_B.weight", FakeParameter(requires_grad=True)),
        ),
    )


def _qlora_model(**changes) -> FakeModel:
    values = {
        "loaded_in_4bit": True,
        "modules": (Dense(), Linear4bit()),
        "parameters": (
            ("base.weight", FakeParameter(requires_grad=False)),
            ("adapter.lora_A.weight", FakeParameter(requires_grad=True)),
            ("adapter.lora_B.weight", FakeParameter(requires_grad=True)),
        ),
    }
    values.update(changes)
    return FakeModel(**values)


def _quantization_config(**changes):
    values = {
        "load_in_4bit": True,
        "bnb_4bit_quant_type": "nf4",
        "bnb_4bit_use_double_quant": True,
    }
    values.update(changes)
    return SimpleNamespace(**values)


def _gradient_checks(*, finite: bool = True, nonzero: bool = True):
    return (
        AdapterGradientCheck("adapter.lora_A.weight", is_finite=finite, is_nonzero=False),
        AdapterGradientCheck(
            "adapter.lora_B.weight",
            is_finite=finite,
            is_nonzero=nonzero and finite,
        ),
    )


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"cuda_available": False}, "CUDA"),
        ({"bitsandbytes_imported": False}, "bitsandbytes"),
        ({"bitsandbytes_version": "0.0.0"}, "approved bitsandbytes"),
        ({"bitsandbytes_config_available": False}, "BitsAndBytesConfig"),
        ({"linear4bit_type": None}, "Linear4bit"),
        ({"kbit_preparation_available": False}, "prepare_model_for_kbit_training"),
    ],
)
def test_qlora_preload_proof_fails_closed_for_each_missing_capability(changes, message):
    with pytest.raises(RuntimeError, match=message):
        prove_qwen_preload(_identity(AdaptationMode.QLORA), _qlora_capabilities(**changes))


def test_lora_preload_does_not_require_cuda_or_bitsandbytes():
    capabilities = QwenPreloadCapabilities(
        cuda_available=False,
        bitsandbytes_imported=False,
        bitsandbytes_version=None,
        bitsandbytes_config_available=False,
        linear4bit_type=None,
        kbit_preparation_available=False,
    )
    proof = prove_qwen_preload(_identity(AdaptationMode.LORA), capabilities)
    assert proof.requested_mode == AdaptationMode.LORA


def test_fabricated_incomplete_qlora_preload_proof_is_rejected():
    from src.model_adaptation.phase40_modes import QwenPreloadProof

    with pytest.raises(ValueError, match="must be issued by prove_qwen_preload"):
        QwenPreloadProof(
            requested_mode=AdaptationMode.QLORA,
            cuda_available=False,
            bitsandbytes_version=APPROVED_BITSANDBYTES_VERSION,
            bitsandbytes_config_available=True,
            linear4bit_type=Linear4bit,
            kbit_preparation_available=True,
        )


def test_preload_rejects_an_unrelated_python_type_as_linear4bit():
    with pytest.raises(RuntimeError, match="exact imported bitsandbytes.nn.Linear4bit"):
        prove_qwen_preload(
            _identity(AdaptationMode.QLORA),
            _qlora_capabilities(linear4bit_type=object),
        )


def test_preload_rejects_a_class_that_spoofs_linear4bit_metadata():
    class Spoof:
        pass

    Spoof.__name__ = "Linear4bit"
    Spoof.__module__ = "bitsandbytes.nn.modules"
    with pytest.raises(RuntimeError, match="exact imported bitsandbytes.nn.Linear4bit"):
        prove_qwen_preload(
            _identity(AdaptationMode.QLORA),
            _qlora_capabilities(linear4bit_type=Spoof),
        )


def test_qlora_rejects_an_explicit_cpu_device_before_model_construction():
    with pytest.raises(RuntimeError, match="resolved training device.*CUDA"):
        _validate_qwen_training_device(_identity(AdaptationMode.QLORA), "cpu")
    _validate_qwen_training_device(_identity(AdaptationMode.LORA), "cpu")


def test_genuine_qlora_resolves_only_after_complete_model_and_gradient_proof():
    preload = prove_qwen_preload(_identity(AdaptationMode.QLORA), _qlora_capabilities())
    proof = prove_qwen_mode(
        _identity(AdaptationMode.QLORA),
        preload_proof=preload,
        model=_qlora_model(),
        quantization_config=_quantization_config(),
        kbit_preparation_applied=True,
        backward_performed=True,
        adapter_gradients=_gradient_checks(),
    )

    assert proof.requested_mode == AdaptationMode.QLORA
    assert proof.resolved_mode == ResolvedQwenMode.FOUR_BIT_QLORA
    assert proof.linear4bit_modules == 1
    assert proof.adapter_gradient_nonzero_count == 1


def test_linear4bit_class_name_cannot_spoof_the_approved_runtime_type():
    class ImpostorLinear4bit:
        pass

    ImpostorLinear4bit.__name__ = "Linear4bit"
    preload = prove_qwen_preload(_identity(AdaptationMode.QLORA), _qlora_capabilities())
    with pytest.raises(RuntimeError, match="Linear4bit"):
        prove_qwen_mode(
            _identity(AdaptationMode.QLORA),
            preload_proof=preload,
            model=_qlora_model(modules=(Dense(), ImpostorLinear4bit())),
            quantization_config=_quantization_config(),
            kbit_preparation_applied=True,
            backward_performed=True,
            adapter_gradients=_gradient_checks(),
        )


def test_gradient_probe_forwards_existing_response_only_labels_once():
    class FakeTensor:
        def __init__(self, values):
            self.values = values

        def to(self, _device):
            return self

    class FakeScalar:
        def detach(self):
            return self

        def all(self):
            return self

        def item(self):
            return 1

    class FakeLoss(FakeScalar):
        def backward(self):
            parameter.grad = FakeScalar()

    class GradientParameter:
        requires_grad = True
        device = "cuda:0"
        grad = None

    class ProbeModel:
        training = False

        def named_parameters(self):
            return iter((("adapter.lora_A.weight", parameter),))

        def train(self, mode=True):
            self.training = mode

        def zero_grad(self, *, set_to_none):
            if set_to_none:
                parameter.grad = None

        def __call__(self, **kwargs):
            assert set(kwargs) == {"input_ids", "attention_mask", "labels"}
            assert kwargs["labels"].values == [[-100, -100, 23, 24]]
            return SimpleNamespace(loss=FakeLoss())

    class FakeTorch:
        long = "long"

        @staticmethod
        def tensor(values, *, dtype):
            assert dtype == "long"
            return FakeTensor(values)

        @staticmethod
        def isfinite(_value):
            return FakeScalar()

        @staticmethod
        def count_nonzero(_value):
            return FakeScalar()

    parameter = GradientParameter()
    checks = _run_adapter_gradient_probe(
        ProbeModel(),
        {
            "input_ids": [10, 11, 23, 24],
            "attention_mask": [1, 1, 1, 1],
            "labels": [-100, -100, 23, 24],
        },
        torch_module=FakeTorch(),
    )
    assert checks == (AdapterGradientCheck("adapter.lora_A.weight", True, True),)


def test_saved_adapter_identity_is_proven_against_live_peft_tensors(tmp_path):
    torch = pytest.importorskip("torch")
    artifact = tmp_path / "adapter"
    artifact.mkdir()
    (artifact / "adapter_config.json").write_text("{}", encoding="utf-8")
    state = {"adapter.lora_A.weight": torch.tensor([[1.0, 2.0]])}
    torch.save(state, artifact / "adapter_model.bin")
    fake_model = SimpleNamespace(adapter_state=state)
    fake_peft = SimpleNamespace(
        get_peft_model_state_dict=lambda model: model.adapter_state,
    )

    identity = _prove_saved_adapter_matches_live(
        fake_model,
        artifact,
        torch_module=torch,
        peft_module=fake_peft,
    )
    assert identity.startswith("adapter-state-sha256:")

    torch.save(
        {"adapter.lora_A.weight": torch.tensor([[9.0, 2.0]])},
        artifact / "adapter_model.bin",
    )
    with pytest.raises(RuntimeError, match="does not match live state"):
        _prove_saved_adapter_matches_live(
            fake_model,
            artifact,
            torch_module=torch,
            peft_module=fake_peft,
        )


@pytest.mark.parametrize(
    ("case", "message"),
    [
        ("load_flag", "load_in_4bit"),
        ("nf4", "NF4"),
        ("double_quant", "double quantization"),
        ("model_flag", "is_loaded_in_4bit"),
        ("linear", "Linear4bit"),
        ("base_trainable", "base weights"),
        ("unexpected_trainable", "adapter-only"),
        ("no_adapter", "adapter trainable"),
        ("no_backward", "backward"),
        ("zero_gradient", "non-zero"),
        ("nonfinite_gradient", "finite"),
        ("no_kbit", "k-bit preparation"),
    ],
)
def test_each_incomplete_qlora_model_proof_is_rejected(case, message):
    model = _qlora_model()
    config = _quantization_config()
    gradients = _gradient_checks()
    kwargs = {
        "preload_proof": prove_qwen_preload(_identity(AdaptationMode.QLORA), _qlora_capabilities()),
        "model": model,
        "quantization_config": config,
        "kbit_preparation_applied": True,
        "backward_performed": True,
        "adapter_gradients": gradients,
    }
    if case == "load_flag":
        kwargs["quantization_config"] = _quantization_config(load_in_4bit=False)
    elif case == "nf4":
        kwargs["quantization_config"] = _quantization_config(bnb_4bit_quant_type="fp4")
    elif case == "double_quant":
        kwargs["quantization_config"] = _quantization_config(bnb_4bit_use_double_quant=False)
    elif case == "model_flag":
        kwargs["model"] = _qlora_model(loaded_in_4bit=False)
    elif case == "linear":
        kwargs["model"] = _qlora_model(modules=(Dense(),))
    elif case == "base_trainable":
        kwargs["model"] = _qlora_model(
            parameters=(
                ("base.weight", FakeParameter(requires_grad=True)),
                ("adapter.lora_A.weight", FakeParameter(requires_grad=True)),
            )
        )
    elif case == "unexpected_trainable":
        kwargs["model"] = _qlora_model(
            parameters=(
                ("base.weight", FakeParameter(requires_grad=False)),
                ("classifier.weight", FakeParameter(requires_grad=True)),
                ("adapter.lora_A.weight", FakeParameter(requires_grad=True)),
            )
        )
    elif case == "no_adapter":
        kwargs["model"] = _qlora_model(
            parameters=(("base.weight", FakeParameter(requires_grad=False)),)
        )
        kwargs["adapter_gradients"] = ()
    elif case == "no_backward":
        kwargs["backward_performed"] = False
    elif case == "zero_gradient":
        kwargs["adapter_gradients"] = _gradient_checks(nonzero=False)
    elif case == "nonfinite_gradient":
        kwargs["adapter_gradients"] = _gradient_checks(finite=False)
    else:
        kwargs["kbit_preparation_applied"] = False

    with pytest.raises(RuntimeError, match=message):
        prove_qwen_mode(_identity(AdaptationMode.QLORA), **kwargs)


def test_lora_proves_symmetric_absence_of_four_bit_modules_and_adapter_only_trainables():
    capabilities = QwenPreloadCapabilities(False, False, None, False, None, False)
    preload = prove_qwen_preload(_identity(AdaptationMode.LORA), capabilities)
    proof = prove_qwen_mode(
        _identity(AdaptationMode.LORA),
        preload_proof=preload,
        model=_lora_model(),
        quantization_config=None,
        kbit_preparation_applied=False,
        backward_performed=False,
        adapter_gradients=(),
    )
    assert proof.resolved_mode == ResolvedQwenMode.FULL_PRECISION_LORA

    with pytest.raises(RuntimeError, match="Linear4bit"):
        prove_qwen_mode(
            _identity(AdaptationMode.LORA),
            preload_proof=preload,
            model=_qlora_model(),
            quantization_config=None,
            kbit_preparation_applied=False,
            backward_performed=False,
            adapter_gradients=(),
        )

    with pytest.raises(RuntimeError, match="must not claim QLoRA"):
        prove_qwen_mode(
            _identity(AdaptationMode.LORA),
            preload_proof=preload,
            model=_lora_model(),
            quantization_config=None,
            kbit_preparation_applied=True,
            backward_performed=False,
            adapter_gradients=(),
        )


def test_requested_and_resolved_modes_cannot_form_an_invalid_pair():
    with pytest.raises(ValueError, match="requested.*resolved"):
        QuantizationProof(
            requested_mode=AdaptationMode.QLORA,
            resolved_mode=ResolvedQwenMode.FULL_PRECISION_LORA,
            bitsandbytes_version=APPROVED_BITSANDBYTES_VERSION,
            load_in_4bit=True,
            nf4=True,
            double_quantization=True,
            is_loaded_in_4bit=True,
            linear4bit_modules=1,
            kbit_preparation_applied=True,
            base_weights_frozen=True,
            adapter_only_trainables=True,
            adapter_trainable_count=2,
            backward_with_adapter_gradients=True,
            adapter_gradient_finite_count=2,
            adapter_gradient_nonzero_count=1,
        )


def test_resolved_qlora_name_cannot_bypass_incomplete_proof_fields():
    with pytest.raises(ValueError, match="incomplete genuine QLoRA"):
        QuantizationProof(
            requested_mode=AdaptationMode.QLORA,
            resolved_mode=ResolvedQwenMode.FOUR_BIT_QLORA,
            bitsandbytes_version=APPROVED_BITSANDBYTES_VERSION,
            load_in_4bit=False,
            nf4=False,
            double_quantization=False,
            is_loaded_in_4bit=False,
            linear4bit_modules=0,
            kbit_preparation_applied=False,
            base_weights_frozen=True,
            adapter_only_trainables=True,
            adapter_trainable_count=2,
            backward_with_adapter_gradients=False,
            adapter_gradient_finite_count=0,
            adapter_gradient_nonzero_count=0,
        )


def _selection() -> PilotSelection:
    return PilotSelection(
        baseline_winner_id="qwen3.5-4b",
        runner_up_id="qwen2.5-7b-instruct",
        selection_notes="Fixture selection.",
    )


def _config(tmp_path: Path, mode: AdaptationMode, *, dry_run: bool = False):
    return build_training_config(
        candidate_id="qwen3.5-4b",
        train_split_path=tmp_path / "train.jsonl",
        val_split_path=tmp_path / "val.jsonl",
        version_tag="phase40-fixture",
        output_root=tmp_path / "models",
        registry_path=tmp_path / "registry.json",
        selection=_selection(),
        adaptation_mode=mode,
        run_kind=RunKind.FULL,
        dry_run=dry_run,
    )


def _write_training_rows(config) -> Phase40DataContract:
    rows = [
        DatasetRecord(
            text="Tin nhắn giả danh ngân hàng yêu cầu cung cấp mã OTP ngay lập tức.",
            label="bank_impersonation",
            risk_tier="high-risk",
            suspicious_spans=["mã OTP"],
            xai_explanation="Tin nhắn yêu cầu mã OTP dưới danh nghĩa ngân hàng giả mạo.",
            source="synthetic_claude",
            seed_id="fixture-train",
        )
    ]
    for path in (config.train_split_path, config.val_split_path):
        path.write_text("".join(row.model_dump_json() + "\n" for row in rows), encoding="utf-8")
    record = rows[0]

    def snapshot(split_name: str) -> CanonicalSplitSnapshot:
        record_bytes = record.model_dump_json().encode("utf-8")
        payload = record_bytes + b"\n"
        row_sha = hashlib.sha256(record_bytes).hexdigest()
        identity = SplitIdentity(
            split_name=split_name,
            relative_path=f"data/splits/{split_name}.jsonl",
            records=1,
            bytes=len(payload),
            sha256=hashlib.sha256(payload).hexdigest(),
            label_counts=(("bank_impersonation", 1), ("zalo_social_engineering", 0), ("task_scam", 0), ("benign", 0)),
        )
        row = CanonicalSnapshotRow(
            split_name=split_name,
            canonical_index=0,
            record_bytes=record_bytes,
            record=record,
            raw_message=record.text,
            source_row_sha256=row_sha,
            snapshot_row_id=derive_snapshot_row_id(split_name, 0, row_sha),
        )
        return CanonicalSplitSnapshot(
            split_name=split_name,
            identity=identity,
            whole_file_bytes=payload,
            whole_file_sha256=identity.sha256,
            rows=(row,),
        )

    train = snapshot("train")
    val = snapshot("val")
    return Phase40DataContract(
        ordered_identities=(train.identity, val.identity),
        train_snapshot=train,
        validation_snapshot=val,
        held_out_test=HeldOutIdentity(
            path="data/splits/test.jsonl",
            records=1,
            bytes=1,
            sha256="0" * 64,
            evaluation_phase=41,
            touch_policy="opaque fixture metadata only",
        ),
    )


def test_lora_and_qlora_share_all_adapter_controls(tmp_path):
    lora = _config(tmp_path / "lora", AdaptationMode.LORA)
    qlora = _config(tmp_path / "qlora", AdaptationMode.QLORA)
    assert (lora.lora_r, lora.lora_alpha, lora.lora_dropout, lora.lora_bias, lora.target_modules) == (
        qlora.lora_r,
        qlora.lora_alpha,
        qlora.lora_dropout,
        qlora.lora_bias,
        qlora.target_modules,
    )
    assert lora.target_modules == DEFAULT_TARGET_MODULES
    assert len(lora.target_modules) == 7


def test_programmatic_training_config_cannot_infer_an_omitted_mode(tmp_path):
    with pytest.raises(TypeError, match="adaptation_mode"):
        build_training_config(
            candidate_id="qwen3.5-4b",
            train_split_path=tmp_path / "train.jsonl",
            val_split_path=tmp_path / "val.jsonl",
            version_tag="phase40-fixture",
            output_root=tmp_path / "models",
            registry_path=tmp_path / "registry.json",
            selection=_selection(),
        )


def test_unbound_full_run_cannot_reach_backend_or_publish_adapter(tmp_path, monkeypatch):
    import src.model_adaptation.training as training_module

    config = _config(tmp_path, AdaptationMode.QLORA)
    contract = _write_training_rows(config)
    published: list[object] = []
    monkeypatch.setattr(training_module, "save_adapter_artifacts", lambda *a, **k: published.append((a, k)))
    monkeypatch.setattr(
        training_module,
        "_run_local_adapter_training",
        lambda *_: pytest.fail("unbound full run reached the training backend"),
    )

    with pytest.raises(RuntimeError, match="transfer authority"):
        run_training(
            config,
            data_contract=contract,
            selection=_selection(),
        )

    assert published == []


def test_dry_run_does_not_publish_fake_qlora_adapter(tmp_path, monkeypatch):
    import src.model_adaptation.training as training_module

    config = _config(tmp_path, AdaptationMode.QLORA, dry_run=True)
    contract = _write_training_rows(config)
    published: list[object] = []
    monkeypatch.setattr(training_module, "save_adapter_artifacts", lambda *a, **k: published.append((a, k)))

    result = run_training(config, data_contract=contract, selection=_selection())
    assert result["dry_run"] is True
    assert result["artifact_record"] is None
    assert published == []


def test_probe_cannot_start_or_publish_before_discard_lifecycle_exists(tmp_path, monkeypatch):
    import src.model_adaptation.training as training_module

    config = replace(_config(tmp_path, AdaptationMode.LORA), run_kind=RunKind.PROBE)
    contract = _write_training_rows(config)
    monkeypatch.setattr(
        training_module,
        "_run_local_adapter_training",
        lambda *_: (_ for _ in ()).throw(AssertionError("probe trainer started")),
    )
    published: list[object] = []
    monkeypatch.setattr(
        training_module,
        "save_adapter_artifacts",
        lambda *args, **kwargs: published.append((args, kwargs)),
    )
    with pytest.raises(RuntimeError, match="discard/evidence lifecycle"):
        run_training(config, data_contract=contract, selection=_selection())
    assert published == []


def test_doctor_is_mode_specific_and_never_creates_output_directory(tmp_path, monkeypatch):
    import src.model_adaptation.doctor as doctor_module

    missing_root = tmp_path / "must-not-be-created"
    doctor = doctor_module.TrainingDoctor(
        adaptation_mode=AdaptationMode.QLORA,
        train_split=tmp_path / "train.jsonl",
        val_split=tmp_path / "val.jsonl",
        output_root=missing_root,
        registry_path=tmp_path / "registry.json",
    )
    monkeypatch.setattr(
        doctor,
        "_collect_preload_capabilities",
        lambda: _qlora_capabilities(bitsandbytes_imported=False),
    )
    check = doctor._check_mode_support()

    assert check.passed is False
    assert "QLoRA NOT READY" in check.detail
    assert not missing_root.exists()


def test_lora_doctor_does_not_consult_bitsandbytes(monkeypatch, tmp_path):
    import src.model_adaptation.doctor as doctor_module

    doctor = doctor_module.TrainingDoctor(
        adaptation_mode=AdaptationMode.LORA,
        train_split=tmp_path / "train.jsonl",
        val_split=tmp_path / "val.jsonl",
        output_root=tmp_path / "models",
        registry_path=tmp_path / "registry.json",
    )

    def fail_if_called():
        raise AssertionError("LoRA doctor consulted bitsandbytes")

    monkeypatch.setattr(doctor, "_collect_preload_capabilities", fail_if_called)
    assert doctor._check_mode_support().passed is True


def test_programmatic_doctor_cannot_infer_an_omitted_mode(tmp_path):
    import src.model_adaptation.doctor as doctor_module

    with pytest.raises(TypeError, match="adaptation_mode"):
        doctor_module.TrainingDoctor(output_root=tmp_path / "models")


def test_cli_requires_positive_adaptation_mode_for_train_and_doctor():
    from src.model_adaptation.cli import build_parser

    parser = build_parser()
    subparsers = next(action for action in parser._actions if action.dest == "command")
    for command in ("train", "doctor"):
        mode_action = next(
            action for action in subparsers.choices[command]._actions if action.dest == "adaptation_mode"
        )
        assert mode_action.required is True
        assert tuple(mode_action.choices) == ("lora", "qlora")
    train_actions = {action.dest: action for action in subparsers.choices["train"]._actions}
    assert train_actions["train_split"].required is True
    assert train_actions["val_split"].required is True
    assert all(action.dest != "full_precision" for action in subparsers.choices["train"]._actions)
