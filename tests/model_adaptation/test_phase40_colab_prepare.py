from __future__ import annotations

import json

import pytest

from src.model_adaptation.phase40_colab_prepare import (
    GGUF_CONVERTER_SHA256,
    PHOBERT_FULL_OPTIMIZER_STEPS,
    QWEN_FULL_OPTIMIZER_STEPS,
    RUN_IDENTITIES,
    GgufToolAuthority,
    build_launch_ready_request,
    build_parser,
    verify_launch_ready_request,
)
from src.model_adaptation.phase40_contract import HeldOutIdentity
from src.model_adaptation.phase40_handoff import (
    INPUT_MEMBER_NAMES,
    InputBundleReference,
    InputDataMember,
    SourceBundleReference,
    SourceInventoryEntry,
)
from src.model_adaptation.phase40_modes import AdaptationMode, ResolvedQwenMode
from src.model_adaptation.phase40_evidence import QuantizationProofEvidence


def _input_reference() -> InputBundleReference:
    held_out = HeldOutIdentity(
        path="data/splits/test.jsonl",
        records=220,
        bytes=1234,
        sha256="9" * 64,
        evaluation_phase=41,
        touch_policy="opaque until Phase 41",
    )
    members = tuple(
        InputDataMember(
            logical_name=logical,
            member_name=f"{logical}.jsonl",
            records=1658 if logical == "train" else 219,
            bytes=1000 if logical == "train" else 200,
            sha256=("1" if logical == "train" else "2") * 64,
            crc32="1234abcd",
            ordered_row_ids_sha256=("3" if logical == "train" else "4") * 64,
        )
        for logical in ("train", "val")
    )
    return InputBundleReference(
        archive_sha256="5" * 64,
        manifest_sha256="6" * 64,
        members=INPUT_MEMBER_NAMES,
        data_members=members,
        phase39_data_contract_sha256="7" * 64,
        held_out_opaque=held_out,
    )


def _source_reference() -> SourceBundleReference:
    entry = SourceInventoryEntry(path="src/runtime.py", bytes=12, sha256="a" * 64)
    return SourceBundleReference(
        archive_sha256="b" * 64,
        inventory_sha256="c" * 64,
        files=(entry,),
    )


def _proof(mode: AdaptationMode) -> QuantizationProofEvidence:
    if mode == AdaptationMode.LORA:
        return QuantizationProofEvidence(
            requested_mode=mode,
            resolved_mode=ResolvedQwenMode.FULL_PRECISION_LORA,
            bitsandbytes_version=None,
            load_in_4bit=False,
            nf4=False,
            double_quantization=False,
            is_loaded_in_4bit=False,
            linear4bit_modules=0,
            kbit_preparation_applied=False,
            base_weights_frozen=True,
            adapter_only_trainables=True,
            adapter_trainable_count=504,
            backward_with_adapter_gradients=False,
            adapter_gradient_finite_count=0,
            adapter_gradient_nonzero_count=0,
        )
    return QuantizationProofEvidence(
        requested_mode=mode,
        resolved_mode=ResolvedQwenMode.FOUR_BIT_QLORA,
        bitsandbytes_version="0.50.1",
        load_in_4bit=True,
        nf4=True,
        double_quantization=True,
        is_loaded_in_4bit=True,
        linear4bit_modules=252,
        kbit_preparation_applied=True,
        base_weights_frozen=True,
        adapter_only_trainables=True,
        adapter_trainable_count=504,
        backward_with_adapter_gradients=True,
        adapter_gradient_finite_count=504,
        adapter_gradient_nonzero_count=252,
    )


def _request_and_controls():
    return build_launch_ready_request(
        input_reference=_input_reference(),
        source_reference=_source_reference(),
        lora_proof=_proof(AdaptationMode.LORA),
        qlora_proof=_proof(AdaptationMode.QLORA),
    )


def test_production_request_is_three_fresh_runs_and_full_not_probe_capped() -> None:
    request, controls = _request_and_controls()
    assert verify_launch_ready_request(request) == request
    assert tuple(run.run_id for run in request.runs) == tuple(item[0] for item in RUN_IDENTITIES)
    assert all(run.step_origin == 0 and run.probe_parent is None for run in request.runs)

    lora = controls[RUN_IDENTITIES[0][0]]
    qlora = controls[RUN_IDENTITIES[1][0]]
    phobert = controls[RUN_IDENTITIES[2][0]]
    assert lora.max_optimizer_steps == qlora.max_optimizer_steps == QWEN_FULL_OPTIMIZER_STEPS
    assert lora.num_train_epochs == qlora.num_train_epochs == 3.0
    assert QWEN_FULL_OPTIMIZER_STEPS == 1245
    assert lora.max_optimizer_steps != 45
    assert phobert.max_optimizer_steps == PHOBERT_FULL_OPTIMIZER_STEPS == 312


def test_qwen_scientific_controls_match_except_quantization() -> None:
    _, controls = _request_and_controls()
    lora = controls[RUN_IDENTITIES[0][0]]
    qlora = controls[RUN_IDENTITIES[1][0]]
    assert lora.max_sequence_length == qlora.max_sequence_length == 1024
    assert lora.effective_batch_size == qlora.effective_batch_size == 4
    assert lora.optimizer == qlora.optimizer
    assert lora.precision == qlora.precision
    assert lora.cadence == qlora.cadence
    assert lora.formatter_or_preprocessor_sha256 == qlora.formatter_or_preprocessor_sha256
    assert lora.quantization_proof != qlora.quantization_proof


def test_production_verifier_rejects_probe_cap_even_when_generic_schema_accepts() -> None:
    request, _ = _request_and_controls()
    run_id = RUN_IDENTITIES[1][0]
    payload = request.model_dump(mode="python")
    control = dict(payload["control_template_by_run"][run_id]["controls_without_accelerator"])
    control["max_optimizer_steps"] = 45
    payload["control_template_by_run"][run_id]["controls_without_accelerator"] = control
    # Generic request equality also catches this because Qwen modes must match;
    # mutating both demonstrates the additional production-profile gate.
    for qwen_id in (RUN_IDENTITIES[0][0], RUN_IDENTITIES[1][0]):
        values = payload["control_template_by_run"][qwen_id]["controls_without_accelerator"]
        values["max_optimizer_steps"] = 45
        from src.model_adaptation.phase40_handoff import RequestedControlTemplate

        template = RequestedControlTemplate(controls_without_accelerator=values)
        payload["control_template_by_run"][qwen_id] = template.model_dump(mode="python")
        payload["control_template_digest_by_run"][qwen_id] = template.sha256
    from src.model_adaptation.phase40_handoff import RunRequest

    generic = RunRequest.model_validate(payload)
    with pytest.raises(ValueError, match="1,245-step"):
        verify_launch_ready_request(generic)


def test_gguf_converter_authority_is_fixed_not_self_authorized() -> None:
    authority = GgufToolAuthority()
    assert authority.package == "gguf"
    assert authority.package_version == "0.19.0"
    assert authority.converter_sha256 == GGUF_CONVERTER_SHA256
    assert authority.outtype == "q8_0"
    payload = authority.model_dump(mode="json")
    payload["converter_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="reviewed fixed identity"):
        GgufToolAuthority.model_validate(payload)


def test_standalone_cli_has_prepare_and_verify_without_training_flags() -> None:
    parser = build_parser()
    prepare = parser.parse_args(["prepare", "--repo-root", "."])
    verify = parser.parse_args(["verify", "--repo-root", "."])
    assert prepare.command == "prepare"
    assert verify.command == "verify"
    serialized = json.dumps(vars(prepare), default=str)
    assert "max-steps" not in serialized
    assert "test.jsonl" not in serialized
