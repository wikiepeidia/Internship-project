from __future__ import annotations

from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from src.data_pipeline.schemas import DatasetRecord
from src.model_adaptation.phase40_contract import (
    CanonicalSnapshotRow,
    CanonicalSplitSnapshot,
    HeldOutIdentity,
    Phase40DataContract,
    SplitIdentity,
)
from src.model_adaptation.phase40_evidence import (
    AcceleratorIdentity,
    RunEventKind,
    RuntimeHardwareEvidence,
    TransferAuthorityEvidence,
    load_run_events,
    verify_phase40_bundle,
)
from src.model_adaptation.phase40_metrics import LABEL_ORDER
from src.model_adaptation.phobert_training import (
    PHOBERT_ID_TO_LABEL,
    PHOBERT_LABEL_TO_ID,
    PHOBERT_MAX_LENGTH,
    PHOBERT_MODEL_ID,
    PHOBERT_MODEL_REVISION,
    PHOBERT_PREPROCESSOR_SHA256,
    PHOBERT_SEGMENTER_VERSION,
    PHOBERT_BASE_MODEL_MANIFEST_NAME,
    PhoBertTrainingConfig,
    PhoBertTrainingDependencies,
    build_phobert_prediction_rows,
    preprocess_phobert_snapshot,
    run_phobert_training,
    build_phobert_base_model_acquisition_request,
    seal_phobert_base_model_snapshot,
    segment_for_phobert,
    validate_phobert_base_model_snapshot,
    verify_phobert_base_model_provenance,
)


class FakeTokenizer:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def __call__(self, text: str, **kwargs: Any) -> dict[str, list[int]]:
        self.calls.append((text, dict(kwargs)))
        count = 300 if "DÀI" in text else max(3, len(text.split()) + 2)
        ids = list(range(1, count + 1))
        if kwargs.get("truncation"):
            ids = ids[: int(kwargs["max_length"])]
        return {"input_ids": ids, "attention_mask": [1] * len(ids)}


class FakeParameter:
    def __init__(self, requires_grad: bool = True) -> None:
        self.requires_grad = requires_grad


class FakeModel:
    def __init__(self, *, label_drift: bool = False, frozen: bool = False, peft: bool = False) -> None:
        self.config = SimpleNamespace(
            num_labels=4,
            id2label=({0: "benign", 1: "bank_impersonation"} if label_drift else dict(PHOBERT_ID_TO_LABEL)),
            label2id=({"benign": 0} if label_drift else dict(PHOBERT_LABEL_TO_ID)),
        )
        self._parameters = (
            ("roberta.encoder.layer.0.weight", FakeParameter(not frozen)),
            ("classifier.out_proj.weight", FakeParameter(True)),
        )
        self.peft_config = {"lora": object()} if peft else None
        self.is_loaded_in_4bit = False
        self.current_step = 0

    def named_parameters(self):  # noqa: ANN201
        return iter(self._parameters)

    def modules(self):  # noqa: ANN201
        return iter((self,))


class FakeTrainingArguments:
    def __init__(self, **kwargs: Any) -> None:
        self.__dict__.update(kwargs)


class FakeCollator:
    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs

    def __call__(self, rows):  # noqa: ANN001, ANN201
        return rows[0]


class FakeCudaTiming:
    def synchronize(self) -> None:
        return None

    def reset_peak_memory_stats(self) -> None:
        return None

    def max_memory_allocated(self) -> int:
        return 700

    def max_memory_reserved(self) -> int:
        return 900


class IncrementingClock:
    def __init__(self) -> None:
        self.value = 0.0

    def __call__(self) -> float:
        self.value += 1.0
        return self.value


class FakeState:
    def __init__(self) -> None:
        self.global_step = 0
        self.epoch = 0.0
        self.num_input_tokens_seen = 0


class FakeTrainer:
    """Two real callback checkpoints; final save repeats checkpoint step two."""

    def __init__(self, *, model, args, callbacks, **kwargs):  # noqa: ANN001
        self.model = model
        self.args = args
        self.callback = callbacks[0]
        self.state = FakeState()

    @staticmethod
    def _write_model(path: Path, step: int) -> None:
        path.mkdir(parents=True, exist_ok=True)
        (path / "model.safetensors").write_bytes(f"weights-{step}".encode())
        (path / "config.json").write_text("{}", encoding="utf-8")
        if path.name.startswith("checkpoint-"):
            (path / "trainer_state.json").write_text(
                json.dumps({"global_step": step}), encoding="utf-8"
            )

    def train(self, *, resume_from_checkpoint=None):  # noqa: ANN001, ANN201
        assert resume_from_checkpoint is None
        control = object()
        self.callback.on_train_begin(self.args, self.state, control)
        for step in (1, 2):
            self.callback.on_step_begin(self.args, self.state, control)
            self.state.global_step = step
            self.state.epoch = float(step)
            self.state.num_input_tokens_seen += 20
            self.model.current_step = step
            self.callback.on_step_end(self.args, self.state, control)
            self.callback.on_log(
                self.args,
                self.state,
                control,
                logs={"loss": 1.0 / step, "learning_rate": 2e-5},
            )
            self.callback.on_evaluate(
                self.args,
                self.state,
                control,
                metrics={"eval_loss": 0.8 / step, "eval_runtime": 0.05},
            )
            self._save_checkpoint()
            self.callback.on_save(self.args, self.state, control, model=self.model)
        self.callback.on_train_end(self.args, self.state, control)
        return SimpleNamespace()

    def _save_checkpoint(self) -> None:
        checkpoint = Path(self.args.output_dir) / f"checkpoint-{self.state.global_step}"
        self._write_model(checkpoint, self.state.global_step)

    def save_model(self, output_dir: str) -> None:
        self._write_model(Path(output_dir), self.state.global_step)

    def save_state(self) -> None:
        root = Path(self.args.output_dir)
        root.mkdir(parents=True, exist_ok=True)
        (root / "trainer_state.json").write_text(
            json.dumps({"global_step": self.state.global_step}), encoding="utf-8"
        )


class InterruptAfterFirstCheckpointTrainer(FakeTrainer):
    def train(self, *, resume_from_checkpoint=None):  # noqa: ANN001, ANN201
        assert resume_from_checkpoint is None
        control = object()
        self.callback.on_train_begin(self.args, self.state, control)
        self.callback.on_step_begin(self.args, self.state, control)
        self.state.global_step = 1
        self.state.epoch = 1.0
        self.state.num_input_tokens_seen = 20
        self.model.current_step = 1
        self.callback.on_step_end(self.args, self.state, control)
        self.callback.on_log(self.args, self.state, control, logs={"loss": 1.0})
        self.callback.on_evaluate(
            self.args,
            self.state,
            control,
            metrics={"eval_loss": 0.8, "eval_runtime": 0.05},
        )
        self._save_checkpoint()
        self.callback.on_save(self.args, self.state, control, model=self.model)
        raise RuntimeError("simulated interruption")


class InterruptAfterPostCheckpointWorkTrainer(FakeTrainer):
    """Seal step one, observe step-two work, then fail before checkpoint two."""

    def train(self, *, resume_from_checkpoint=None):  # noqa: ANN001, ANN201
        assert resume_from_checkpoint is None
        control = object()
        self.callback.on_train_begin(self.args, self.state, control)
        self.callback.on_step_begin(self.args, self.state, control)
        self.state.global_step = 1
        self.state.epoch = 1.0
        self.state.num_input_tokens_seen = 20
        self.model.current_step = 1
        self.callback.on_step_end(self.args, self.state, control)
        self.callback.on_log(self.args, self.state, control, logs={"loss": 1.0})
        self.callback.on_evaluate(
            self.args,
            self.state,
            control,
            metrics={"eval_loss": 0.8, "eval_runtime": 0.05},
        )
        self._save_checkpoint()
        self.callback.on_save(self.args, self.state, control, model=self.model)

        self.callback.on_step_begin(self.args, self.state, control)
        self.state.global_step = 2
        self.state.epoch = 2.0
        self.state.num_input_tokens_seen = 40
        self.model.current_step = 2
        self.callback.on_step_end(self.args, self.state, control)
        self.callback.on_log(self.args, self.state, control, logs={"loss": 0.5})
        self.callback.on_evaluate(
            self.args,
            self.state,
            control,
            metrics={"eval_loss": 0.4, "eval_runtime": 0.07},
        )
        raise RuntimeError("simulated post-checkpoint interruption")


class ResumeAtSecondCheckpointTrainer(FakeTrainer):
    def train(self, *, resume_from_checkpoint=None):  # noqa: ANN001, ANN201
        assert resume_from_checkpoint is not None
        assert Path(resume_from_checkpoint).name == "checkpoint-1"
        control = object()
        self.state.global_step = 1
        self.state.epoch = 1.0
        self.state.num_input_tokens_seen = 20
        self.callback.on_train_begin(self.args, self.state, control)
        self.callback.on_step_begin(self.args, self.state, control)
        self.state.global_step = 2
        self.state.epoch = 2.0
        self.state.num_input_tokens_seen = 40
        self.model.current_step = 2
        self.callback.on_step_end(self.args, self.state, control)
        self.callback.on_log(self.args, self.state, control, logs={"loss": 0.5})
        self.callback.on_evaluate(
            self.args,
            self.state,
            control,
            metrics={"eval_loss": 0.4, "eval_runtime": 0.05},
        )
        self._save_checkpoint()
        self.callback.on_save(self.args, self.state, control, model=self.model)
        self.callback.on_train_end(self.args, self.state, control)
        return SimpleNamespace()


class InterruptAfterFinalCheckpointTrainer(FakeTrainer):
    def train(self, *, resume_from_checkpoint=None):  # noqa: ANN001, ANN201
        assert resume_from_checkpoint is None
        control = object()
        self.callback.on_train_begin(self.args, self.state, control)
        for step in (1, 2):
            self.callback.on_step_begin(self.args, self.state, control)
            self.state.global_step = step
            self.state.epoch = float(step)
            self.state.num_input_tokens_seen += 20
            self.model.current_step = step
            self.callback.on_step_end(self.args, self.state, control)
            self.callback.on_log(self.args, self.state, control, logs={"loss": 1.0 / step})
            self.callback.on_evaluate(
                self.args,
                self.state,
                control,
                metrics={"eval_loss": 0.8 / step, "eval_runtime": 0.05},
            )
            self._save_checkpoint()
            self.callback.on_save(self.args, self.state, control, model=self.model)
        raise RuntimeError("simulated final-checkpoint interruption")


class ResumeAtFinalWithoutOptimizerWorkTrainer(FakeTrainer):
    def train(self, *, resume_from_checkpoint=None):  # noqa: ANN001, ANN201
        assert resume_from_checkpoint is not None
        assert Path(resume_from_checkpoint).name == "checkpoint-2"
        control = object()
        self.state.global_step = 2
        self.state.epoch = 2.0
        self.state.num_input_tokens_seen = 40
        self.model.current_step = 2
        self.callback.on_train_begin(self.args, self.state, control)
        self.callback.on_train_end(self.args, self.state, control)
        return SimpleNamespace()


def _dataset_record(label: str, index: int) -> DatasetRecord:
    return DatasetRecord(
        text=f"Tin nhắn kiểm thử số {index} cho nhãn {label}",
        label=label,
        risk_tier="benign" if label == "benign" else "high-risk",
        suspicious_spans=[],
        xai_explanation="Giải thích kiểm thử đủ dài cho bản ghi này.",
        source="synthetic_openai_compatible",
        seed_id=f"seed-{label}-{index}",
    )


def _snapshot(split_name: str, labels: tuple[str, ...]) -> CanonicalSplitSnapshot:
    rows = []
    lines = []
    for index, label in enumerate(labels):
        record = _dataset_record(label, index)
        record_bytes = json.dumps(
            record.model_dump(mode="json"), ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        source_sha = hashlib.sha256(record_bytes).hexdigest()
        row_id = f"p40-row-v1-{hashlib.sha256(f'{split_name}-{index}-{source_sha}'.encode()).hexdigest()}"
        rows.append(
            CanonicalSnapshotRow(
                split_name=split_name,
                canonical_index=index,
                record_bytes=record_bytes,
                record=record,
                raw_message=record.text,
                source_row_sha256=source_sha,
                snapshot_row_id=row_id,
            )
        )
        lines.append(record_bytes)
    payload = b"\n".join(lines) + b"\n"
    digest = hashlib.sha256(payload).hexdigest()
    counts = tuple((label, labels.count(label)) for label in LABEL_ORDER)
    identity = SplitIdentity(
        split_name=split_name,
        relative_path=f"data/splits/{split_name}.jsonl",
        records=len(rows),
        bytes=len(payload),
        sha256=digest,
        label_counts=counts,
    )
    return CanonicalSplitSnapshot(split_name, identity, payload, digest, tuple(rows))


def _contract() -> Phase40DataContract:
    train = _snapshot("train", ("bank_impersonation", "benign"))
    val = _snapshot("val", tuple(LABEL_ORDER))
    return Phase40DataContract(
        ordered_identities=(train.identity, val.identity),
        train_snapshot=train,
        validation_snapshot=val,
        held_out_test=HeldOutIdentity(
            path="data/splits/test.jsonl",
            records=220,
            bytes=100,
            sha256="f" * 64,
            evaluation_phase=41,
            touch_policy="opaque-phase41-only",
        ),
    )


def _transfer_authority() -> TransferAuthorityEvidence:
    return TransferAuthorityEvidence(
        schema_version="phase40-transfer-authority-v1",
        source_archive_sha256="1" * 64,
        source_inventory_sha256="2" * 64,
        input_archive_sha256="3" * 64,
        input_manifest_sha256="4" * 64,
        source_repository_relative_archive_path="data/models/phase40/source/phase40-source.zip",
        source_repository_relative_inventory_path="data/models/phase40/source/phase40-source-manifest.json",
        input_repository_relative_path="data/models/phase40/input/phase40-train-validation.zip",
        input_drive_path="/content/drive/MyDrive/internship-phase40/phase40-train-validation.zip",
        input_extraction_root="/content/phase40-input-v1",
        input_members=("phase40-input-manifest.json", "train.jsonl", "val.jsonl"),
        no_held_out_boundary=True,
    )


def _hardware() -> RuntimeHardwareEvidence:
    return RuntimeHardwareEvidence(
        python_version="3.13.7",
        platform="test-platform",
        cuda_version="13.2",
        cudnn_version="9.0",
        gpu_name="fake-gpu",
        gpu_compute_capability="12.0",
        gpu_total_memory_bytes=1024,
        bf16_enabled=False,
        fp16_enabled=True,
        tf32_enabled=False,
    )


def _dependencies(
    *,
    predictor=None,  # noqa: ANN001
    model: FakeModel | None = None,
    captures: dict[str, Any] | None = None,
    trainer_factory=FakeTrainer,  # noqa: ANN001
    telemetry_clock=None,  # noqa: ANN001
) -> PhoBertTrainingDependencies:
    tokenizer = FakeTokenizer()
    model = model or FakeModel()
    captures = captures if captures is not None else {}

    def tokenizer_factory(model_id: str, **kwargs: Any) -> FakeTokenizer:
        captures["tokenizer"] = (model_id, kwargs)
        return tokenizer

    def model_factory(model_id: str, **kwargs: Any) -> FakeModel:
        captures["model"] = (model_id, kwargs)
        return model

    def default_predictor(active_model, records, collator):  # noqa: ANN001, ANN202
        # Step one and two are both perfect, proving the earlier-step tie-break.
        rows = []
        for record in records:
            logits = [-2.0, -2.0, -2.0, -2.0]
            logits[record.label_id] = 3.0
            rows.append(logits)
        return rows

    return PhoBertTrainingDependencies(
        segmenter=lambda text: text.replace("xác minh", "xác_minh"),
        segmenter_version=PHOBERT_SEGMENTER_VERSION,
        tokenizer_factory=tokenizer_factory,
        model_factory=model_factory,
        training_arguments_factory=FakeTrainingArguments,
        data_collator_factory=FakeCollator,
        trainer_factory=trainer_factory,
        trainer_callback_base=object,
        logits_predictor=predictor or default_predictor,
        graph_renderer=lambda data, options: b"fake-png",
        graph_renderer_name="fake-renderer",
        graph_renderer_version="1.0",
        package_versions={
            "python": "3.13.7",
            "torch": "2.12.0+cu132",
            "transformers": "5.9.0",
            "underthesea": "9.5.0",
        },
        accelerator=AcceleratorIdentity(
            accelerator_type="cuda",
            accelerator_name="fake-gpu",
            compute_capability="12.0",
            total_memory_bytes=1024,
        ),
        hardware=_hardware(),
        cuda_timing_adapter=FakeCudaTiming(),
        telemetry_clock=telemetry_clock or IncrementingClock(),
    )


def _config(
    tmp_path: Path,
    *,
    run_id: str = "phobert-test",
    resume_from_checkpoint: Path | None = None,
) -> PhoBertTrainingConfig:
    base_model_path = (tmp_path / "phobert-base-v2").resolve()
    if not base_model_path.exists():
        base_model_path.mkdir(parents=True)
        (base_model_path / "config.json").write_text("{}", encoding="utf-8")
        (base_model_path / "model.safetensors").write_bytes(b"pinned-base-weights")
        (base_model_path / "tokenizer.json").write_text('{"version":"1.0"}', encoding="utf-8")
    seal_phobert_base_model_snapshot(base_model_path)
    return PhoBertTrainingConfig(
        run_id=run_id,
        run_bundle_root=(tmp_path / run_id).resolve(),
        work_root=(tmp_path / "work" / run_id).resolve(),
        local_base_model_path=base_model_path,
        transfer_authority=_transfer_authority(),
        sanitized_argv=("phase40-train-phobert", "--run-id", run_id),
        max_optimizer_steps=2,
        evaluation_steps=1,
        logging_steps=1,
        resume_from_checkpoint=resume_from_checkpoint,
    )


def test_segmentation_preserves_raw_text_and_records_right_truncation() -> None:
    tokenizer = FakeTokenizer()
    raw = "DÀI cần xác minh tài khoản"
    result = segment_for_phobert(
        raw,
        tokenizer=tokenizer,
        segmenter=lambda text: text.replace("xác minh", "xác_minh"),
    )

    assert result.raw_text == raw
    assert result.segmented_text == "DÀI cần xác_minh tài khoản"
    assert result.token_count == 300
    assert result.retained_token_count == PHOBERT_MAX_LENGTH
    assert result.truncated is True
    assert result.preprocessor_sha256 == PHOBERT_PREPROCESSOR_SHA256
    assert tokenizer.calls[0][1]["truncation"] is False
    assert tokenizer.calls[1][1] == {
        "add_special_tokens": True,
        "truncation": True,
        "max_length": 256,
        "padding": False,
    }


def test_offline_base_model_acquisition_and_external_snapshot_seal(tmp_path: Path) -> None:
    snapshot_path = (tmp_path / "models" / "phobert-base-v2").resolve()
    request = build_phobert_base_model_acquisition_request(snapshot_path)
    assert request.snapshot_download_kwargs() == {
        "repo_id": PHOBERT_MODEL_ID,
        "revision": PHOBERT_MODEL_REVISION,
        "local_dir": str(snapshot_path),
    }
    snapshot_path.mkdir(parents=True)
    (snapshot_path / "config.json").write_text("{}", encoding="utf-8")
    (snapshot_path / "model.safetensors").write_bytes(b"base-weights")
    (snapshot_path / "tokenizer.json").write_text('{"version":"1.0"}', encoding="utf-8")
    manifest_path = snapshot_path.with_name(f"{snapshot_path.name}.provenance.json")

    sealed = seal_phobert_base_model_snapshot(
        snapshot_path,
        manifest_path=manifest_path,
        model_id=PHOBERT_MODEL_ID,
        model_revision=PHOBERT_MODEL_REVISION,
    )
    assert sealed.manifest_path == manifest_path
    assert manifest_path.parent == snapshot_path.parent
    assert snapshot_path not in manifest_path.parents
    assert validate_phobert_base_model_snapshot(
        snapshot_path,
        manifest_path=manifest_path,
        expected_model_id=PHOBERT_MODEL_ID,
        expected_model_revision=PHOBERT_MODEL_REVISION,
    ) == sealed
    assert verify_phobert_base_model_provenance(snapshot_path, manifest_path) == sealed

    (snapshot_path / "model.safetensors").write_bytes(b"tampered")
    with pytest.raises(RuntimeError, match="does not match"):
        validate_phobert_base_model_snapshot(snapshot_path, manifest_path=manifest_path)


@pytest.mark.parametrize(
    ("raw_text", "segmenter", "version", "match"),
    [
        ("Tin nhắn hợp lệ", lambda text: "", PHOBERT_SEGMENTER_VERSION, "empty output"),
        ("Tin nhắn hợp lệ", lambda text: text, "9.4.0", "frozen 9.5.0"),
        ("Lỗi \ud800 UTF", lambda text: text, PHOBERT_SEGMENTER_VERSION, "surrogates"),
    ],
)
def test_segmentation_fails_closed(raw_text, segmenter, version, match) -> None:  # noqa: ANN001
    with pytest.raises((ValueError, UnicodeEncodeError), match=match):
        segment_for_phobert(
            raw_text,
            tokenizer=FakeTokenizer(),
            segmenter=segmenter,
            segmenter_version=version,
        )


def test_prediction_rows_copy_exact_snapshot_ids_and_reject_local_reconstruction() -> None:
    contract = _contract()
    records = preprocess_phobert_snapshot(
        contract.validation_snapshot,
        tokenizer=FakeTokenizer(),
        segmenter=lambda text: text,
        segmenter_version=PHOBERT_SEGMENTER_VERSION,
    )
    logits = tuple(
        tuple(4.0 if index == record.label_id else -1.0 for index in range(4))
        for record in records
    )
    identity = "model-state-sha256:" + "a" * 64
    rows = build_phobert_prediction_rows(
        validation_snapshot=contract.validation_snapshot,
        preprocessing_records=records,
        logits=logits,
        artifact_identity=identity,
        checkpoint_step=10,
    )

    assert tuple(row.validation_row_id for row in rows) == contract.validation_snapshot.validation_row_ids
    assert all(len(row.logits) == 4 for row in rows)
    mutated = (replace(records[0], snapshot_row_id="locally-reconstructed"),) + records[1:]
    with pytest.raises(ValueError, match="exactly match"):
        build_phobert_prediction_rows(
            validation_snapshot=contract.validation_snapshot,
            preprocessing_records=mutated,
            logits=logits,
            artifact_identity=identity,
            checkpoint_step=10,
        )


@pytest.mark.parametrize(
    "logits",
    [
        ((1.0, 2.0, 3.0),) * 4,
        ((1.0, 2.0, 3.0, float("nan")),) * 4,
        ((1.0, 2.0, 3.0, 4.0),) * 3,
    ],
)
def test_prediction_rows_reject_wrong_width_nonfinite_and_partial_logits(logits) -> None:  # noqa: ANN001
    contract = _contract()
    records = preprocess_phobert_snapshot(
        contract.validation_snapshot,
        tokenizer=FakeTokenizer(),
        segmenter=lambda text: text,
        segmenter_version=PHOBERT_SEGMENTER_VERSION,
    )
    with pytest.raises(ValueError, match="four finite|count"):
        build_phobert_prediction_rows(
            validation_snapshot=contract.validation_snapshot,
            preprocessing_records=records,
            logits=logits,
            artifact_identity="model-state-sha256:" + "a" * 64,
            checkpoint_step=1,
        )


@pytest.mark.parametrize(
    ("model", "match"),
    [
        (FakeModel(label_drift=True), "label mapping"),
        (FakeModel(frozen=True), "frozen parameters"),
        (FakeModel(peft=True), "PEFT"),
    ],
)
def test_full_training_rejects_label_drift_frozen_encoder_or_peft(
    tmp_path: Path, model: FakeModel, match: str
) -> None:
    with pytest.raises(RuntimeError, match=match):
        run_phobert_training(
            _config(tmp_path, run_id=f"reject-{match.casefold().replace(' ', '-')}") ,
            _contract(),
            dependencies=_dependencies(model=model),
        )


def test_full_fake_training_finalizes_complete_four_logit_evidence(tmp_path: Path) -> None:
    captures: dict[str, Any] = {}
    config = _config(tmp_path)
    result = run_phobert_training(
        config,
        _contract(),
        dependencies=_dependencies(captures=captures),
    )

    assert result.selection.safety_gate_passed is True
    assert result.selection.selected_step == 1  # identical perfect metrics -> earlier step
    assert len(result.checkpoint_metrics) == 2  # final step two was de-duplicated
    assert result.evidence.experiment_identity.model_family.value == "phobert"
    assert result.evidence.experiment_identity.adaptation_mode.value == "classification-head"
    assert result.evidence.model_id == PHOBERT_MODEL_ID
    assert result.evidence.model_revision == PHOBERT_MODEL_REVISION
    assert result.evidence.quantization is None
    assert result.evidence.decoder_contract is None
    assert result.evidence.selected_checkpoint.artifact_identity.startswith("model-state-sha256:")
    assert result.evidence.peak_allocated_bytes == 700
    assert result.evidence.peak_reserved_bytes == 900
    assert result.evidence.steady_step_seconds_median is not None
    assert len(result.preprocessing_records) == 6
    assert verify_phase40_bundle(result.run_root) == result.evidence
    retained_provenance = result.run_root / "adapter-or-model" / PHOBERT_BASE_MODEL_MANIFEST_NAME
    assert retained_provenance.read_bytes() == config.resolved_base_model_provenance_path.read_bytes()

    model_id, model_kwargs = captures["model"]
    assert model_id == str(config.local_base_model_path)
    assert model_kwargs["revision"] == PHOBERT_MODEL_REVISION
    assert model_kwargs["num_labels"] == 4
    assert model_kwargs["id2label"] == PHOBERT_ID_TO_LABEL
    assert model_kwargs["label2id"] == PHOBERT_LABEL_TO_ID
    assert "quantization_config" not in model_kwargs
    assert "peft_config" not in model_kwargs
    tokenizer_source, tokenizer_kwargs = captures["tokenizer"]
    assert tokenizer_source == str(config.local_base_model_path)
    assert tokenizer_kwargs["revision"] == PHOBERT_MODEL_REVISION
    assert tokenizer_kwargs["local_files_only"] is True

    prediction_rows = [
        json.loads(line)
        for line in (result.run_root / "predictions.json").read_text(encoding="utf-8").splitlines()
    ]
    assert [row["validation_row_id"] for row in prediction_rows] == list(
        _contract().validation_snapshot.validation_row_ids
    )
    assert all(len(row["logits"]) == 4 for row in prediction_rows)
    assert all(row["checkpoint_step"] == 1 for row in prediction_rows)
    preprocessing = [
        json.loads(line)
        for line in (result.run_root / "preprocessing.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert [row["raw_text"] for row in preprocessing] == [
        row.raw_message for row in _contract().train_snapshot.rows + _contract().validation_snapshot.rows
    ]


def test_no_passing_checkpoint_remains_visible_as_safety_failure(tmp_path: Path) -> None:
    def all_benign(model, records, collator):  # noqa: ANN001, ANN202
        return [[-1.0, -1.0, -1.0, 4.0] for _ in records]

    result = run_phobert_training(
        _config(tmp_path, run_id="phobert-failing-safety"),
        _contract(),
        dependencies=_dependencies(predictor=all_benign),
    )

    assert result.selection.safety_gate_passed is False
    assert result.evidence.selected_checkpoint.safety_gate_passed is False
    assert "no checkpoint passed safety admission" in result.evidence.selected_checkpoint.rationale
    assert result.evidence.status.value == "complete"
    assert len(result.evidence.validation_checkpoints) == 2


def test_empty_contract_blocks_before_model_factory(tmp_path: Path) -> None:
    contract = _contract()
    empty = replace(
        contract,
        train_snapshot=replace(contract.train_snapshot, rows=()),
    )
    captures: dict[str, Any] = {}
    with pytest.raises(ValueError, match="empty train or validation"):
        run_phobert_training(
            _config(tmp_path, run_id="empty-contract"),
            empty,
            dependencies=_dependencies(captures=captures),
        )
    assert "model" not in captures


def test_exact_resume_verifies_manifest_history_and_completes_in_separate_work_root(
    tmp_path: Path,
) -> None:
    fresh = _config(tmp_path, run_id="resume-run")
    with pytest.raises(RuntimeError, match="simulated interruption"):
        run_phobert_training(
            fresh,
            _contract(),
            dependencies=_dependencies(trainer_factory=InterruptAfterFirstCheckpointTrainer),
        )

    checkpoint = fresh.work_root / "trainer" / "checkpoint-1"
    manifest_path = checkpoint / "phase40-resume-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["run_id"] == "resume-run"
    assert manifest["checkpoint_step"] == 1
    assert manifest["controlled_config_digest"]
    assert len(manifest["candidates"]) == 1
    assert (fresh.run_bundle_root / "events.jsonl").is_file()
    assert not (fresh.run_bundle_root / "trainer-work").exists()

    resumed = _config(
        tmp_path,
        run_id="resume-run",
        resume_from_checkpoint=checkpoint,
    )
    result = run_phobert_training(
        resumed,
        _contract(),
        dependencies=_dependencies(trainer_factory=ResumeAtSecondCheckpointTrainer),
    )

    assert result.selection.selected_step == 1
    assert len(result.evidence.validation_checkpoints) == 2
    assert verify_phase40_bundle(result.run_root) == result.evidence
    second_manifest = json.loads(
        (resumed.work_root / "trainer" / "checkpoint-2" / "phase40-resume-manifest.json").read_text(
            encoding="utf-8"
        )
    )
    assert [item["optimizer_step"] for item in second_manifest["candidates"]] == [1, 2]


def _post_checkpoint_interrupted_run(
    tmp_path: Path,
    *,
    run_id: str,
) -> tuple[PhoBertTrainingConfig, Path, dict[str, Any]]:
    config = _config(tmp_path, run_id=run_id)
    with pytest.raises(RuntimeError, match="post-checkpoint interruption"):
        run_phobert_training(
            config,
            _contract(),
            dependencies=_dependencies(
                trainer_factory=InterruptAfterPostCheckpointWorkTrainer,
                telemetry_clock=IncrementingClock(),
            ),
        )
    checkpoint = config.work_root / "trainer" / "checkpoint-1"
    manifest = json.loads(
        (checkpoint / "phase40-resume-manifest.json").read_text(encoding="utf-8")
    )
    assert (config.run_bundle_root / "events.jsonl").stat().st_size > manifest["sealed_event_bytes"]
    return config, checkpoint, manifest


def test_exact_resume_accepts_terminal_post_checkpoint_suffix_and_carries_telemetry(
    tmp_path: Path,
) -> None:
    fresh, checkpoint, manifest = _post_checkpoint_interrupted_run(
        tmp_path,
        run_id="post-checkpoint-resume",
    )
    sealed_telemetry = manifest["telemetry"]
    assert sealed_telemetry["observed_optimizer_steps"] == 1
    resumed = replace(fresh, resume_from_checkpoint=checkpoint)
    result = run_phobert_training(
        resumed,
        _contract(),
        dependencies=_dependencies(
            trainer_factory=ResumeAtSecondCheckpointTrainer,
            telemetry_clock=IncrementingClock(),
        ),
    )

    events = load_run_events(
        result.run_root / "events.jsonl",
        expected_run_id="post-checkpoint-resume",
    )
    starts = [event for event in events if event.event_kind == RunEventKind.RUN_START]
    assert [event.optimizer_step for event in starts] == [0, 1]
    assert events[-1].trainer_values["observed_optimizer_steps"] == 3
    assert events[-1].trainer_values["evaluation_overhead_seconds"] == pytest.approx(0.17)
    assert events[-1].trainer_values["checkpoint_overhead_seconds"] == pytest.approx(2.0)
    assert events[-1].trainer_values["actual_wall_seconds"] > sealed_telemetry["actual_wall_seconds"]
    assert result.evidence.steady_step_seconds_median == pytest.approx(1.0)
    assert result.evidence.peak_allocated_bytes == 700
    assert result.evidence.peak_reserved_bytes == 900
    assert len(result.evidence.validation_checkpoints) == 2
    assert verify_phase40_bundle(result.run_root) == result.evidence


@pytest.mark.parametrize(
    "tamper",
    [
        "suffix-duration",
        "suffix-wall-regression",
        "foreign-run",
        "nonterminal",
        "truncated-prefix",
        "mutated-prefix",
    ],
)
def test_exact_resume_rejects_invalid_unsealed_suffix_before_model_factory(
    tmp_path: Path,
    tamper: str,
) -> None:
    fresh, checkpoint, manifest = _post_checkpoint_interrupted_run(
        tmp_path,
        run_id=f"reject-suffix-{tamper}",
    )
    event_path = fresh.run_bundle_root / "events.jsonl"
    payload = event_path.read_bytes()
    sealed_bytes = int(manifest["sealed_event_bytes"])
    if tamper == "truncated-prefix":
        event_path.write_bytes(payload[: sealed_bytes - 1])
        match = "sealed event history mismatch"
    elif tamper == "mutated-prefix":
        mutated = payload[:sealed_bytes].replace(b'"origin_step":0', b'"origin_step":1', 1)
        assert mutated != payload[:sealed_bytes] and len(mutated) == sealed_bytes
        event_path.write_bytes(mutated + payload[sealed_bytes:])
        match = "sealed event history mismatch"
    else:
        prefix = payload[:sealed_bytes]
        suffix_payloads = [
            json.loads(line)
            for line in payload[sealed_bytes:].decode("utf-8", errors="strict").splitlines()
        ]
        if tamper == "suffix-duration":
            step_event = next(
                item for item in suffix_payloads if item["event_kind"] == "step_timing"
            )
            step_event["trainer_values"]["duration_seconds"] = -1.0
            match = "optimizer-step duration"
        elif tamper == "suffix-wall-regression":
            resource_event = next(
                item
                for item in suffix_payloads
                if item["event_kind"] == "resource"
                and item["trainer_values"].get("attempt_terminal") is True
            )
            resource_event["trainer_values"]["actual_wall_seconds"] = 0.001
            match = "wall time moved backward"
        elif tamper == "foreign-run":
            suffix_payloads[0]["source_run_id"] = "foreign-run"
            match = "mixes source run IDs|identity drift"
        else:
            assert tamper == "nonterminal"
            suffix_payloads = suffix_payloads[:-1]
            match = "lacks terminal resource/failure|nonterminal"
        rewritten_suffix = b"".join(
            (
                json.dumps(
                    item,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                + "\n"
            ).encode("utf-8")
            for item in suffix_payloads
        )
        event_path.write_bytes(prefix + rewritten_suffix)
    captures: dict[str, Any] = {}
    with pytest.raises(RuntimeError, match=match):
        run_phobert_training(
            replace(fresh, resume_from_checkpoint=checkpoint),
            _contract(),
            dependencies=_dependencies(
                trainer_factory=ResumeAtSecondCheckpointTrainer,
                captures=captures,
            ),
        )
    assert "model" not in captures


def test_resume_rejects_tampered_checkpoint_before_model_factory(tmp_path: Path) -> None:
    fresh = _config(tmp_path, run_id="tamper-resume")
    with pytest.raises(RuntimeError, match="simulated interruption"):
        run_phobert_training(
            fresh,
            _contract(),
            dependencies=_dependencies(trainer_factory=InterruptAfterFirstCheckpointTrainer),
        )
    checkpoint = fresh.work_root / "trainer" / "checkpoint-1"
    (checkpoint / "config.json").write_text('{"tampered":true}', encoding="utf-8")
    captures: dict[str, Any] = {}
    resumed = _config(
        tmp_path,
        run_id="tamper-resume",
        resume_from_checkpoint=checkpoint,
    )
    with pytest.raises(RuntimeError, match="checkpoint payload mismatch"):
        run_phobert_training(
            resumed,
            _contract(),
            dependencies=_dependencies(
                trainer_factory=ResumeAtSecondCheckpointTrainer,
                captures=captures,
            ),
        )
    assert "model" not in captures


def test_resume_rejects_control_digest_or_run_id_drift(tmp_path: Path) -> None:
    fresh = _config(tmp_path, run_id="drift-resume")
    with pytest.raises(RuntimeError, match="simulated interruption"):
        run_phobert_training(
            fresh,
            _contract(),
            dependencies=_dependencies(trainer_factory=InterruptAfterFirstCheckpointTrainer),
        )
    checkpoint = fresh.work_root / "trainer" / "checkpoint-1"
    changed_control = replace(
        _config(tmp_path, run_id="drift-resume", resume_from_checkpoint=checkpoint),
        learning_rate=3e-5,
    )
    with pytest.raises(RuntimeError, match="controlled config mismatch"):
        run_phobert_training(
            changed_control,
            _contract(),
            dependencies=_dependencies(trainer_factory=ResumeAtSecondCheckpointTrainer),
        )

    changed_run = replace(changed_control, run_id="different-run", learning_rate=2e-5)
    with pytest.raises(RuntimeError, match="run ID mismatch"):
        run_phobert_training(
            changed_run,
            _contract(),
            dependencies=_dependencies(trainer_factory=ResumeAtSecondCheckpointTrainer),
        )


def test_resume_forbids_latest_and_requires_disjoint_absolute_roots(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="latest is forbidden"):
        replace(_config(tmp_path, run_id="latest-run"), resume_from_checkpoint=Path("latest"))
    with pytest.raises(ValueError, match="disjoint"):
        replace(
            _config(tmp_path, run_id="overlap-run"),
            work_root=(_config(tmp_path, run_id="overlap-run").run_bundle_root / "work"),
        )


def test_resume_restores_cumulative_telemetry_and_finalizes_without_new_optimizer_work(
    tmp_path: Path,
) -> None:
    clean = run_phobert_training(
        _config(tmp_path / "clean", run_id="clean-run"),
        _contract(),
        dependencies=_dependencies(telemetry_clock=IncrementingClock()),
    )
    interrupted = _config(tmp_path / "resumed", run_id="resume-final")
    with pytest.raises(RuntimeError, match="final-checkpoint interruption"):
        run_phobert_training(
            interrupted,
            _contract(),
            dependencies=_dependencies(
                trainer_factory=InterruptAfterFinalCheckpointTrainer,
                telemetry_clock=IncrementingClock(),
            ),
        )
    checkpoint = interrupted.work_root / "trainer" / "checkpoint-2"
    first_manifest = json.loads(
        (checkpoint / "phase40-resume-manifest.json").read_text(encoding="utf-8")
    )
    assert first_manifest["schema_version"] == "phase40-phobert-resume-v2"
    assert first_manifest["telemetry"]["observed_optimizer_steps"] == 2
    assert first_manifest["telemetry"]["attempt_count"] == 1
    assert first_manifest["base_model_content_sha256"]
    assert first_manifest["base_model_manifest_sha256"]

    resumed = replace(interrupted, resume_from_checkpoint=checkpoint)
    result = run_phobert_training(
        resumed,
        _contract(),
        dependencies=_dependencies(
            trainer_factory=ResumeAtFinalWithoutOptimizerWorkTrainer,
            telemetry_clock=IncrementingClock(),
        ),
    )

    assert result.evidence.validation_metrics == clean.evidence.validation_metrics
    assert result.evidence.validation_checkpoints == clean.evidence.validation_checkpoints
    assert result.evidence.peak_allocated_bytes == clean.evidence.peak_allocated_bytes == 700
    assert result.evidence.peak_reserved_bytes == clean.evidence.peak_reserved_bytes == 900
    assert (
        result.evidence.steady_step_seconds_median
        == clean.evidence.steady_step_seconds_median
    )
    events = load_run_events(result.run_root / "events.jsonl", expected_run_id="resume-final")
    restored = [
        event
        for event in events
        if event.trainer_values.get("restored_resume_history") is True
    ]
    assert [event.event_kind for event in restored] == [
        RunEventKind.STEP_TIMING,
        RunEventKind.EVALUATION,
        RunEventKind.CHECKPOINT,
    ]
    assert events[-1].event_kind == RunEventKind.RUN_END
    assert events[-1].trainer_values["observed_optimizer_steps"] == 2
    assert events[-1].trainer_values["evaluation_overhead_seconds"] == pytest.approx(0.1)
    assert events[-1].trainer_values["checkpoint_overhead_seconds"] == pytest.approx(2.0)
    assert events[-1].trainer_values["actual_wall_seconds"] > 0
    final_manifest = json.loads(
        (checkpoint / "phase40-resume-manifest.json").read_text(encoding="utf-8")
    )
    assert final_manifest["telemetry"]["attempt_count"] == 2
    assert (
        final_manifest["telemetry"]["actual_wall_seconds"]
        > first_manifest["telemetry"]["actual_wall_seconds"]
    )
    assert final_manifest["telemetry"]["peak_allocated_bytes"] == 700
    assert final_manifest["telemetry"]["peak_reserved_bytes"] == 900
    assert verify_phase40_bundle(result.run_root) == result.evidence


def test_resume_rejects_tampered_sealed_telemetry_before_model_factory(tmp_path: Path) -> None:
    fresh = _config(tmp_path, run_id="tamper-telemetry")
    with pytest.raises(RuntimeError, match="simulated interruption"):
        run_phobert_training(
            fresh,
            _contract(),
            dependencies=_dependencies(trainer_factory=InterruptAfterFirstCheckpointTrainer),
        )
    checkpoint = fresh.work_root / "trainer" / "checkpoint-1"
    manifest_path = checkpoint / "phase40-resume-manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["telemetry"]["observed_optimizer_steps"] = 2
    telemetry_bytes = json.dumps(
        payload["telemetry"],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    payload["telemetry_sha256"] = hashlib.sha256(
        b"phase40-phobert-resume-telemetry-v1\0" + telemetry_bytes
    ).hexdigest()
    manifest_path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    captures: dict[str, Any] = {}
    with pytest.raises(RuntimeError, match="sealed telemetry mismatch"):
        run_phobert_training(
            replace(fresh, resume_from_checkpoint=checkpoint),
            _contract(),
            dependencies=_dependencies(
                trainer_factory=ResumeAtSecondCheckpointTrainer,
                captures=captures,
            ),
        )
    assert "model" not in captures


def _symlink_or_skip(target: Path, link: Path, *, directory: bool) -> None:
    try:
        os.symlink(target, link, target_is_directory=directory)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"symlink creation is unavailable: {exc}")


def test_config_rejects_symlinked_output_ancestor(tmp_path: Path) -> None:
    config = _config(tmp_path, run_id="symlink-ancestor")
    real = tmp_path / "real-output-parent"
    real.mkdir()
    linked = tmp_path / "linked-output-parent"
    _symlink_or_skip(real, linked, directory=True)
    with pytest.raises(ValueError, match="traverses a symlink"):
        replace(config, run_bundle_root=(linked / "returned").absolute())


@pytest.mark.parametrize("directory", [False, True])
def test_resume_checkpoint_hash_rejects_omitted_symlink_entries(
    tmp_path: Path,
    directory: bool,
) -> None:
    fresh = _config(tmp_path, run_id=f"symlink-checkpoint-{str(directory).casefold()}")
    with pytest.raises(RuntimeError, match="simulated interruption"):
        run_phobert_training(
            fresh,
            _contract(),
            dependencies=_dependencies(trainer_factory=InterruptAfterFirstCheckpointTrainer),
        )
    checkpoint = fresh.work_root / "trainer" / "checkpoint-1"
    if directory:
        target = tmp_path / "external-directory"
        target.mkdir()
        (target / "payload.bin").write_bytes(b"not-hashed")
        link = checkpoint / "linked-directory"
    else:
        target = tmp_path / "external-file.bin"
        target.write_bytes(b"not-hashed")
        link = checkpoint / "linked-file.bin"
    _symlink_or_skip(target, link, directory=directory)
    captures: dict[str, Any] = {}
    with pytest.raises(ValueError, match="contains a symlink"):
        run_phobert_training(
            replace(fresh, resume_from_checkpoint=checkpoint),
            _contract(),
            dependencies=_dependencies(
                trainer_factory=ResumeAtSecondCheckpointTrainer,
                captures=captures,
            ),
        )
    assert "model" not in captures
