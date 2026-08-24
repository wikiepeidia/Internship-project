"""Wave 0 training-data tests for Phase 3 fine-tuning helpers."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.data_pipeline.schemas import DatasetRecord
from src.model_adaptation.catalog import build_default_catalog
from src.model_adaptation.data import build_training_examples, load_split_records
from src.model_adaptation.registry import build_model_checksum
from src.model_adaptation.prompts import format_training_prompt
from src.model_adaptation.phase40_modes import (
    AdaptationMode,
    QuantizationProof,
    ResolvedQwenMode,
)
from src.model_adaptation.phase40_contract import (
    CanonicalSnapshotRow,
    CanonicalSplitSnapshot,
    HeldOutIdentity,
    Phase40DataContract,
    SplitIdentity,
    derive_snapshot_row_id,
)
from src.model_adaptation.phase40_metrics import (
    Phase40PredictionRow,
    evaluate_phase40_predictions,
    select_phase40_checkpoint,
)
from src.model_adaptation.registry import load_model_registry
from src.model_adaptation.schemas import PilotSelection
from src.model_adaptation.training import (
    Phase40ValidationRecorder,
    _build_validation_trainer_callback,
    build_training_config,
    run_training,
    save_adapter_artifacts,
)


def _write_split(path: Path, records: list[DatasetRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(record.model_dump_json() + "\n")


def _sample_records() -> list[DatasetRecord]:
    return [
        DatasetRecord(
            text=(
                "VPBank cảnh báo account Internet Banking của bạn sẽ bị khóa trong 24h. "
                "Không chia sẻ mã OTP và không bấm link đăng nhập https://vpbank-safe.example."
            ),
            label="bank_impersonation",
            risk_tier="high-risk",
            suspicious_spans=["mã OTP", "https://vpbank-safe.example", "trong 24h"],
            xai_explanation=(
                "Tin nhắn giả mạo ngân hàng kết hợp yêu cầu OTP, link xác minh, và áp lực thời gian."
            ),
            source="synthetic_claude",
            seed_id="seed_phase3_001",
        ),
        DatasetRecord(
            text=(
                "Chị ơi em vừa mất Facebook nên nhắn từ Zalo mới này. Chuyển giúp em 3 triệu nha, "
                "em đang kẹt tiền gấp và app banking login không được."
            ),
            label="task_scam",
            risk_tier="high-risk",
            suspicious_spans=["Zalo mới này", "3 triệu", "login không được"],
            xai_explanation=(
                "Tin nhắn mạo danh người quen, tạo áp lực khẩn cấp, và yêu cầu chuyển tiền trực tiếp."
            ),
            source="synthetic_claude",
            seed_id="seed_phase3_002",
        ),
    ]


def _fixture_contract(
    train_records: list[DatasetRecord],
    val_records: list[DatasetRecord],
) -> Phase40DataContract:
    labels = ("bank_impersonation", "zalo_social_engineering", "task_scam", "benign")

    def build(split_name, records):
        encoded_rows = tuple(record.model_dump_json().encode("utf-8") for record in records)
        payload = b"".join(row + b"\n" for row in encoded_rows)
        counts = tuple((label, sum(record.label == label for record in records)) for label in labels)
        identity = SplitIdentity(
            split_name=split_name,
            relative_path=f"data/splits/{split_name}.jsonl",
            records=len(records),
            bytes=len(payload),
            sha256=hashlib.sha256(payload).hexdigest(),
            label_counts=counts,
        )
        rows = []
        for index, (record, record_bytes) in enumerate(zip(records, encoded_rows, strict=True)):
            row_sha = hashlib.sha256(record_bytes).hexdigest()
            rows.append(
                CanonicalSnapshotRow(
                    split_name=split_name,
                    canonical_index=index,
                    record_bytes=record_bytes,
                    record=record,
                    raw_message=record.text,
                    source_row_sha256=row_sha,
                    snapshot_row_id=derive_snapshot_row_id(split_name, index, row_sha),
                )
            )
        return CanonicalSplitSnapshot(
            split_name=split_name,
            identity=identity,
            whole_file_bytes=payload,
            whole_file_sha256=identity.sha256,
            rows=tuple(rows),
        )

    train = build("train", train_records)
    val = build("val", val_records)
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


def _selection() -> PilotSelection:
    return PilotSelection(
        baseline_winner_id="qwen3.5-4b",
        runner_up_id="qwen2.5-7b-instruct",
        selection_notes="Winner and runner-up selected in the pilot.",
    )


def test_load_split_records_reads_typed_jsonl_records(tmp_path):
    split_path = tmp_path / "splits" / "train.jsonl"
    records = _sample_records()
    _write_split(split_path, records)

    loaded_records = load_split_records(split_path)

    assert [record.seed_id for record in loaded_records] == ["seed_phase3_001", "seed_phase3_002"]
    assert loaded_records[0].risk_tier == "high-risk"


def test_build_training_examples_preserves_mixed_language_text(tmp_path):
    split_path = tmp_path / "splits" / "val.jsonl"
    records = _sample_records()
    _write_split(split_path, records)
    candidate = build_default_catalog()[0]

    examples = build_training_examples(load_split_records(split_path), candidate)

    assert examples[0]["candidate_id"] == candidate.candidate_id
    assert "account Internet Banking" in examples[0]["text"]
    assert "mã OTP" in examples[0]["response"]
    assert "high-risk" in examples[0]["response"]
    assert examples[0]["suspicious_spans"] == ["mã OTP", "https://vpbank-safe.example", "trong 24h"]


def test_format_training_prompt_includes_schema_and_raw_text():
    candidate = build_default_catalog()[1]
    record = _sample_records()[0]

    prompt = format_training_prompt(record, candidate)

    assert candidate.hf_source in prompt
    assert "Response schema" in prompt
    assert record.text in prompt
    assert "xai_explanation" in prompt


def test_build_training_examples_preserves_explanation_fields(tmp_path):
    split_path = tmp_path / "splits" / "train.jsonl"
    records = _sample_records()
    _write_split(split_path, records)
    candidate = build_default_catalog()[0]

    examples = build_training_examples(load_split_records(split_path), candidate)
    response_payload = json.loads(examples[1]["response"])

    assert response_payload["label"] == "task_scam"
    assert response_payload["risk_tier"] == "high-risk"
    assert response_payload["xai_explanation"].startswith("Tin nhắn mạo danh")


def test_build_training_config_uses_selected_candidate(tmp_path):
    train_path = tmp_path / "splits" / "train.jsonl"
    val_path = tmp_path / "splits" / "val.jsonl"
    records = _sample_records()
    _write_split(train_path, records)
    _write_split(val_path, records[:1])

    config = build_training_config(
        candidate_id="qwen3.5-4b",
        train_split_path=train_path,
        val_split_path=val_path,
        version_tag="phase3-smoke",
        output_root=tmp_path / "models",
        registry_path=tmp_path / "manifests" / "model-registry.json",
        selection=_selection(),
        adaptation_mode=AdaptationMode.LORA,
        dry_run=True,
    )

    assert config.candidate_id == "qwen3.5-4b"
    assert config.baseline_winner_id == "qwen3.5-4b"
    assert config.runner_up_id == "qwen2.5-7b-instruct"
    assert config.dry_run is True


def test_build_training_config_smoke_test_uses_checkpoint_friendly_defaults(tmp_path):
    train_path = tmp_path / "splits" / "train.jsonl"
    val_path = tmp_path / "splits" / "val.jsonl"
    records = _sample_records()
    _write_split(train_path, records)
    _write_split(val_path, records[:1])

    config = build_training_config(
        candidate_id="qwen3.5-4b",
        train_split_path=train_path,
        val_split_path=val_path,
        version_tag="phase3-smoke",
        output_root=tmp_path / "models",
        registry_path=tmp_path / "manifests" / "model-registry.json",
        selection=_selection(),
        adaptation_mode=AdaptationMode.LORA,
        smoke_test=True,
    )

    assert config.smoke_test is True
    assert config.max_steps == 2
    assert config.save_steps == 1
    assert config.logging_steps == 1
    assert config.gradient_accumulation_steps == 1


def test_run_training_rejects_non_selected_candidate(tmp_path):
    train_path = tmp_path / "splits" / "train.jsonl"
    val_path = tmp_path / "splits" / "val.jsonl"
    records = _sample_records()
    _write_split(train_path, records)
    _write_split(val_path, records[:1])

    try:
        build_training_config(
            candidate_id="qwen3-4b-instruct-2507",
            train_split_path=train_path,
            val_split_path=val_path,
            version_tag="phase3-smoke",
            output_root=tmp_path / "models",
            registry_path=tmp_path / "manifests" / "model-registry.json",
            selection=_selection(),
            adaptation_mode=AdaptationMode.LORA,
            dry_run=True,
        )
    except ValueError as exc:
        assert "pilot-selected baseline winner and runner-up" in str(exc)
    else:
        raise AssertionError("Expected non-selected candidate to be rejected")


def test_save_adapter_artifacts_registers_metadata(tmp_path):
    train_path = tmp_path / "splits" / "train.jsonl"
    val_path = tmp_path / "splits" / "val.jsonl"
    records = _sample_records()
    _write_split(train_path, records)
    _write_split(val_path, records[:1])

    config = build_training_config(
        candidate_id="qwen2.5-7b-instruct",
        train_split_path=train_path,
        val_split_path=val_path,
        version_tag="phase3-smoke",
        output_root=tmp_path / "models",
        registry_path=tmp_path / "manifests" / "model-registry.json",
        selection=_selection(),
        adaptation_mode=AdaptationMode.LORA,
        dry_run=True,
    )

    artifact_record = save_adapter_artifacts(config, selection=_selection())
    loaded_registry = load_model_registry(config.registry_path)

    assert artifact_record.local_path.exists()
    assert loaded_registry.selection is not None
    assert loaded_registry.selection.runner_up_id == "qwen2.5-7b-instruct"
    assert loaded_registry.artifacts[0].candidate_id == "qwen2.5-7b-instruct"
    assert loaded_registry.artifacts[0].artifact_type == "adapter"


def test_run_training_dry_run_does_not_register_placeholder_artifact(tmp_path):
    train_path = tmp_path / "splits" / "train.jsonl"
    val_path = tmp_path / "splits" / "val.jsonl"
    records = _sample_records()
    _write_split(train_path, records)
    _write_split(val_path, records[:1])

    config = build_training_config(
        candidate_id="qwen3.5-4b",
        train_split_path=train_path,
        val_split_path=val_path,
        version_tag="phase3-smoke",
        output_root=tmp_path / "models",
        registry_path=tmp_path / "manifests" / "model-registry.json",
        selection=_selection(),
        adaptation_mode=AdaptationMode.LORA,
        dry_run=True,
    )

    result = run_training(
        config,
        data_contract=_fixture_contract(records, records[:1]),
        selection=_selection(),
    )

    assert result["dry_run"] is True
    assert result["candidate_id"] == "qwen3.5-4b"
    assert result["train_examples"] == 2
    assert result["val_examples"] == 1
    assert result["artifact_record"] is None
    assert not config.registry_path.exists()


def test_run_training_blocks_unbound_full_run_before_backend(tmp_path, monkeypatch):
    import src.model_adaptation.training as training_module
    torch = pytest.importorskip("torch")

    train_path = tmp_path / "splits" / "train.jsonl"
    val_path = tmp_path / "splits" / "val.jsonl"
    base_record = _sample_records()[0]
    labels = ("bank_impersonation", "zalo_social_engineering", "task_scam", "benign")
    records = [
        base_record.model_copy(update={"label": label, "seed_id": f"fixture-{label}"})
        for label in labels
    ]
    _write_split(train_path, records)
    _write_split(val_path, records)
    contract = _fixture_contract(records, records)

    config = build_training_config(
        candidate_id="qwen3.5-4b",
        train_split_path=train_path,
        val_split_path=val_path,
        version_tag="phase3-real-smoke",
        output_root=tmp_path / "models",
        registry_path=tmp_path / "manifests" / "model-registry.json",
        selection=_selection(),
        adaptation_mode=AdaptationMode.LORA,
        smoke_test=True,
    )

    trusted_identity: str | None = None
    final_identity: str | None = None
    publish_mismatched_state = False

    def fake_local_backend(config, train_examples, val_examples, data_contract):
        nonlocal final_identity, trusted_identity
        assert data_contract.validation_snapshot.split_name == "val"
        adapter_dir = training_module._adapter_output_dir(config)
        checkpoint_dir = training_module._training_output_dir(config) / "checkpoint-1"
        adapter_dir.mkdir(parents=True, exist_ok=True)
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        (adapter_dir / "adapter_config.json").write_text('{"peft_type": "LORA"}', encoding="utf-8")
        adapter_state = {
            "adapter.lora_A.weight": torch.tensor(
                [[9.0 if publish_mismatched_state else 1.0, 2.0]]
            )
        }
        torch.save(adapter_state, adapter_dir / "adapter_model.bin")
        summary_path = adapter_dir / "training-summary.json"
        summary_path.write_text('{"device": "cpu"}', encoding="utf-8")
        actual_identity = training_module._adapter_state_identity(
            adapter_state,
            torch_module=torch,
        )
        if trusted_identity is None:
            trusted_identity = actual_identity
        artifact_identity = trusted_identity
        final_state = {"adapter.lora_A.weight": torch.tensor([[7.0, 8.0]])}
        final_identity = training_module._adapter_state_identity(
            final_state,
            torch_module=torch,
        )
        final_dir = training_module._final_adapter_output_dir(config)
        final_dir.mkdir(parents=True, exist_ok=True)
        (final_dir / "adapter_config.json").write_text(
            '{"peft_type": "LORA"}',
            encoding="utf-8",
        )
        torch.save(final_state, final_dir / "adapter_model.bin")
        earlier_prediction_rows = tuple(
            Phase40PredictionRow.from_raw(
                validation_row_id=row.validation_row_id,
                sequence_index=index,
                gold_label=row.record.label,
                raw_prediction=json.dumps({"label": row.record.label}),
                artifact_identity=artifact_identity,
                checkpoint_step=1,
            )
            for index, row in enumerate(data_contract.validation_snapshot.rows)
        )
        earlier_metrics = evaluate_phase40_predictions(
            expected_validation_row_ids=data_contract.validation_snapshot.validation_row_ids,
            gold_labels=tuple(row.record.label for row in data_contract.validation_snapshot.rows),
            prediction_rows=earlier_prediction_rows,
        )
        final_prediction_rows = tuple(
            Phase40PredictionRow.from_raw(
                validation_row_id=row.validation_row_id,
                sequence_index=index,
                gold_label=row.record.label,
                raw_prediction=json.dumps({"label": "benign"}),
                artifact_identity=final_identity,
                checkpoint_step=2,
            )
            for index, row in enumerate(data_contract.validation_snapshot.rows)
        )
        final_metrics = evaluate_phase40_predictions(
            expected_validation_row_ids=data_contract.validation_snapshot.validation_row_ids,
            gold_labels=tuple(row.record.label for row in data_contract.validation_snapshot.rows),
            prediction_rows=final_prediction_rows,
        )
        checkpoint_selection = select_phase40_checkpoint((earlier_metrics, final_metrics))
        return {
            "artifact_path": adapter_dir,
            "device": "cpu",
            "quantization_mode": "full-precision-lora",
            "quantization_proof": QuantizationProof(
                requested_mode=AdaptationMode.LORA,
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
                adapter_trainable_count=2,
                backward_with_adapter_gradients=False,
                adapter_gradient_finite_count=0,
                adapter_gradient_nonzero_count=0,
            ),
            "checkpoint_path": checkpoint_dir,
            "summary_path": summary_path,
            "checkpoint_selection": checkpoint_selection,
            "checkpoint_candidates": (earlier_metrics, final_metrics),
            "selected_artifact_identity": artifact_identity,
            "formatter_sha256": "2" * 64,
            "formatter_version": training_module.PHASE40_FORMATTER_VERSION,
            "response_mask_version": training_module.PHASE40_RESPONSE_MASK_VERSION,
            "canonical_train_sha256": data_contract.train_snapshot.whole_file_sha256,
            "canonical_val_sha256": data_contract.validation_snapshot.whole_file_sha256,
            "canonical_train_row_ids_sha256": training_module._snapshot_row_id_digest(
                data_contract.train_snapshot
            ),
            "canonical_val_row_ids_sha256": training_module._snapshot_row_id_digest(
                data_contract.validation_snapshot
            ),
        }

    monkeypatch.setattr(training_module, "_run_local_adapter_training", fake_local_backend)

    with pytest.raises(RuntimeError, match="transfer authority"):
        run_training(
            config,
            data_contract=contract,
            selection=_selection(),
        )
    assert not config.registry_path.exists()


def test_trainer_save_callback_generates_against_the_actual_saved_checkpoint(tmp_path):
    contract = _fixture_contract(_sample_records(), _sample_records()[:1])

    class FakeTokenizer:
        chat_template = "fixture-template"

        def apply_chat_template(self, messages, **kwargs):
            return [101, 102]

        def decode(self, token_ids, **kwargs):
            assert token_ids == [700]
            return json.dumps({"label": "bank_impersonation"})

    class FakeModel:
        training = True

        def eval(self):
            self.training = False

        def train(self, mode=True):
            self.training = mode

        def generate(self, **kwargs):
            return [list(kwargs["input_ids"]) + [700]]

    training_root = tmp_path / "trainer"
    checkpoint = training_root / "checkpoint-50"
    checkpoint.mkdir(parents=True)
    (checkpoint / "adapter_config.json").write_text("{}", encoding="utf-8")
    (checkpoint / "adapter_model.bin").write_bytes(b"step-50")
    prove_fixture = lambda _model, path: (
        "adapter-state-sha256:"
        + hashlib.sha256((Path(path) / "adapter_model.bin").read_bytes()).hexdigest()
    )
    recorder = Phase40ValidationRecorder(
        tokenizer=FakeTokenizer(),
        candidate=build_default_catalog()[0],
        validation_snapshot=contract.validation_snapshot,
        training_output_dir=training_root,
        prediction_output_dir=tmp_path / "validation",
        retained_artifact_root=tmp_path / "retained",
        artifact_identity_prover=prove_fixture,
    )

    class FakeTransformers:
        class TrainerCallback:
            pass

    callback = _build_validation_trainer_callback(FakeTransformers, recorder)
    model = FakeModel()
    control = object()
    assert callback.on_save(
        None,
        SimpleNamespace(global_step=50),
        control,
        model=model,
    ) is control

    metric = next(iter(recorder.metrics_by_candidate.values()))
    assert metric.evaluated_rows == 1
    assert metric.prediction_rows[0].checkpoint_step == 50
    assert metric.prediction_rows[0].artifact_identity.startswith(
        "adapter-state-sha256:"
    )
    assert len(list((tmp_path / "validation").glob("predictions-checkpoint-step-50-*.jsonl"))) == 1


def test_validation_recorder_runs_unsaved_final_step_against_final_adapter(tmp_path):
    contract = _fixture_contract(_sample_records(), _sample_records()[:1])

    class FakeTokenizer:
        def apply_chat_template(self, messages, **kwargs):
            return [1]

        def decode(self, token_ids, **kwargs):
            return json.dumps({"label": "bank_impersonation"})

    class FakeModel:
        training = True

        def eval(self):
            self.training = False

        def train(self, mode=True):
            self.training = mode

        def generate(self, **kwargs):
            return [list(kwargs["input_ids"]) + [2]]

    adapter = tmp_path / "adapter"
    adapter.mkdir()
    (adapter / "adapter_config.json").write_text("{}", encoding="utf-8")
    (adapter / "adapter_model.bin").write_bytes(b"final-step-75")
    prove_fixture = lambda _model, path: (
        "adapter-state-sha256:"
        + hashlib.sha256((Path(path) / "adapter_model.bin").read_bytes()).hexdigest()
    )
    recorder = Phase40ValidationRecorder(
        tokenizer=FakeTokenizer(),
        candidate=build_default_catalog()[0],
        validation_snapshot=contract.validation_snapshot,
        training_output_dir=tmp_path / "trainer",
        prediction_output_dir=tmp_path / "validation",
        retained_artifact_root=tmp_path / "retained",
        artifact_identity_prover=prove_fixture,
    )
    recorder.record_final_if_needed(
        model=FakeModel(),
        final_step=75,
        final_artifact_path=adapter,
    )
    assert tuple(step for step, _ in recorder.metrics_by_candidate) == (75,)
    assert recorder.select().selected_step == 75


def test_build_training_arguments_supports_transformers_v5_names(tmp_path):
    import src.model_adaptation.training as training_module

    train_path = tmp_path / "splits" / "train.jsonl"
    val_path = tmp_path / "splits" / "val.jsonl"
    records = _sample_records()
    _write_split(train_path, records)
    _write_split(val_path, records[:1])

    config = build_training_config(
        candidate_id="qwen3.5-4b",
        train_split_path=train_path,
        val_split_path=val_path,
        version_tag="phase3-smoke",
        output_root=tmp_path / "models",
        registry_path=tmp_path / "manifests" / "model-registry.json",
        selection=_selection(),
        adaptation_mode=AdaptationMode.LORA,
        smoke_test=True,
    )
    captured_kwargs: dict[str, object] = {}

    class V5TrainingArguments:
        def __init__(
            self,
            output_dir,
            num_train_epochs,
            max_steps,
            per_device_train_batch_size,
            per_device_eval_batch_size,
            gradient_accumulation_steps,
            learning_rate,
            logging_steps,
            save_steps,
            save_total_limit,
            eval_strategy,
            eval_steps,
            remove_unused_columns,
            report_to,
            logging_first_step,
            save_safetensors,
            use_cpu,
            dataloader_pin_memory,
            fp16,
            bf16,
            gradient_checkpointing,
        ):
            captured_kwargs.update(locals())
            captured_kwargs.pop("self", None)

    fake_transformers = SimpleNamespace(TrainingArguments=V5TrainingArguments)

    training_module._build_training_arguments(
        fake_transformers,
        config,
        tmp_path / "trainer",
        has_eval_data=True,
        device="cpu",
        use_bf16=False,
    )

    assert captured_kwargs["eval_strategy"] == "steps"
    assert captured_kwargs["use_cpu"] is True


def test_build_training_arguments_supports_legacy_transformers_names(tmp_path):
    import src.model_adaptation.training as training_module

    train_path = tmp_path / "splits" / "train.jsonl"
    val_path = tmp_path / "splits" / "val.jsonl"
    records = _sample_records()
    _write_split(train_path, records)
    _write_split(val_path, records[:1])

    config = build_training_config(
        candidate_id="qwen3.5-4b",
        train_split_path=train_path,
        val_split_path=val_path,
        version_tag="phase3-smoke",
        output_root=tmp_path / "models",
        registry_path=tmp_path / "manifests" / "model-registry.json",
        selection=_selection(),
        adaptation_mode=AdaptationMode.LORA,
        smoke_test=True,
    )
    captured_kwargs: dict[str, object] = {}

    class LegacyTrainingArguments:
        def __init__(
            self,
            output_dir,
            overwrite_output_dir,
            num_train_epochs,
            max_steps,
            per_device_train_batch_size,
            per_device_eval_batch_size,
            gradient_accumulation_steps,
            learning_rate,
            logging_steps,
            save_steps,
            save_total_limit,
            evaluation_strategy,
            eval_steps,
            remove_unused_columns,
            report_to,
            logging_first_step,
            save_safetensors,
            no_cuda,
            dataloader_pin_memory,
            fp16,
            bf16,
            gradient_checkpointing,
        ):
            captured_kwargs.update(locals())
            captured_kwargs.pop("self", None)

    fake_transformers = SimpleNamespace(TrainingArguments=LegacyTrainingArguments)

    training_module._build_training_arguments(
        fake_transformers,
        config,
        tmp_path / "trainer",
        has_eval_data=True,
        device="cpu",
        use_bf16=False,
    )

    assert captured_kwargs["evaluation_strategy"] == "steps"
    assert captured_kwargs["no_cuda"] is True
    assert captured_kwargs["overwrite_output_dir"] is False
