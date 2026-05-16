"""Wave 0 training-data tests for Phase 3 fine-tuning helpers."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from src.data_pipeline.schemas import DatasetRecord
from src.model_adaptation.catalog import build_default_catalog
from src.model_adaptation.data import build_training_examples, load_split_records
from src.model_adaptation.registry import build_model_checksum
from src.model_adaptation.prompts import format_training_prompt
from src.model_adaptation.registry import load_model_registry
from src.model_adaptation.schemas import PilotSelection
from src.model_adaptation.training import build_training_config, run_training, save_adapter_artifacts


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
        dry_run=True,
    )

    artifact_record = save_adapter_artifacts(config, selection=_selection())
    loaded_registry = load_model_registry(config.registry_path)

    assert artifact_record.local_path.exists()
    assert loaded_registry.selection is not None
    assert loaded_registry.selection.runner_up_id == "qwen2.5-7b-instruct"
    assert loaded_registry.artifacts[0].candidate_id == "qwen2.5-7b-instruct"
    assert loaded_registry.artifacts[0].artifact_type == "adapter"


def test_run_training_dry_run_registers_placeholder_artifact(tmp_path):
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
        dry_run=True,
    )

    result = run_training(config, selection=_selection())

    assert result["dry_run"] is True
    assert result["candidate_id"] == "qwen3.5-4b"
    assert result["train_examples"] == 2
    assert result["val_examples"] == 1
    assert result["artifact_record"].local_path.exists()


def test_run_training_non_dry_run_uses_local_backend_and_registers_directory_artifact(tmp_path, monkeypatch):
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
        version_tag="phase3-real-smoke",
        output_root=tmp_path / "models",
        registry_path=tmp_path / "manifests" / "model-registry.json",
        selection=_selection(),
        smoke_test=True,
    )

    def fake_local_backend(config, train_examples, val_examples):
        adapter_dir = tmp_path / "models" / "phase3-real-smoke" / "qwen3.5-4b" / "adapter"
        checkpoint_dir = tmp_path / "models" / "phase3-real-smoke" / "qwen3.5-4b" / "trainer" / "checkpoint-1"
        adapter_dir.mkdir(parents=True, exist_ok=True)
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        (adapter_dir / "adapter_config.json").write_text('{"peft_type": "LORA"}', encoding="utf-8")
        (adapter_dir / "adapter_model.safetensors").write_bytes(b"weights")
        summary_path = adapter_dir / "training-summary.json"
        summary_path.write_text('{"device": "cpu"}', encoding="utf-8")
        return {
            "artifact_path": adapter_dir,
            "device": "cpu",
            "quantization_mode": "full-precision-lora",
            "checkpoint_path": checkpoint_dir,
            "summary_path": summary_path,
        }

    monkeypatch.setattr(training_module, "_run_local_adapter_training", fake_local_backend)

    result = run_training(config, selection=_selection())
    loaded_registry = load_model_registry(config.registry_path)

    assert result["dry_run"] is False
    assert result["device"] == "cpu"
    assert result["checkpoint_path"].name == "checkpoint-1"
    assert result["artifact_record"].local_path.is_dir()
    assert result["artifact_record"].sha256 == build_model_checksum(result["artifact_record"].local_path)
    assert loaded_registry.artifacts[0].local_path.is_dir()


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