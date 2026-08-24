"""Response-only Qwen supervision and strict Phase 40 validation tests."""

from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path

import pytest

from src.data_pipeline.schemas import DatasetRecord
from src.model_adaptation.catalog import build_default_catalog
from src.model_adaptation.phase40_contract import (
    CanonicalSnapshotRow,
    CanonicalSplitSnapshot,
    SplitIdentity,
    derive_snapshot_row_id,
)
from src.model_adaptation.phase40_metrics import (
    LABEL_ORDER,
    CheckpointSelection,
    Phase40MetricResult,
    Phase40PredictionRow,
    PredictionState,
    evaluate_phase40_predictions,
    parse_qwen_prediction,
    select_phase40_checkpoint,
)
from src.model_adaptation.training import (
    Phase40ValidationRecorder,
    QwenValidationCheckpointSource,
    PHASE40_FORMATTER_VERSION,
    Phase40ResponseOnlyCollator,
    _build_validation_trainer_callback,
    build_phase40_chat_messages,
    generate_qwen_validation_predictions,
    generate_qwen_validation_schedule,
    tokenize_phase40_response_only,
)


def _example(raw_message: str = "Số tiền đã chuyển thành công qua ngân hàng.") -> dict[str, object]:
    return {
        "prompt": "\n".join(
            [
                "Candidate: fixture/qwen",
                "You are fine-tuning a local Vietnamese phishing detector.",
                "Response schema: fixture",
                f"Message text: {raw_message}",
            ]
        ),
        "response": json.dumps(
            {
                "label": "benign",
                "risk_tier": "benign",
                "suspicious_spans": [],
                "xai_explanation": "Thông báo giao dịch thông thường, không yêu cầu hành động nguy hiểm.",
            },
            ensure_ascii=False,
        ),
        "text": raw_message,
    }


class FakeTemplateTokenizer:
    def __init__(self, *, answer_tokens: tuple[int, ...] = (41, 42, 43), chat_template: str = "fixture-v1"):
        self.answer_tokens = list(answer_tokens)
        self.chat_template = chat_template
        self.pad_token_id = 0
        self.pad_token = "<pad>"
        self.eos_token = "<eos>"
        self.unk_token = "<unk>"
        self.calls: list[dict[str, object]] = []

    def apply_chat_template(self, messages, **kwargs):
        self.calls.append({"messages": messages, **kwargs})
        prompt = [11, 12, 13, 14]
        return prompt if len(messages) == 2 else prompt + self.answer_tokens


def test_chat_roles_are_separate_byte_faithful_and_formatter_hash_is_stable():
    raw = "Tài khoản đã chuyển 2.000.000₫ — không chia sẻ OTP."
    tokenizer = FakeTemplateTokenizer()
    messages = build_phase40_chat_messages(_example(raw))
    first = tokenize_phase40_response_only(_example(raw), tokenizer, max_length=32)
    second = tokenize_phase40_response_only(_example(raw), tokenizer, max_length=32)

    assert [message["role"] for message in messages] == ["system", "user", "assistant"]
    assert raw not in messages[0]["content"]
    assert raw in messages[1]["content"]
    assert messages[2]["content"] == _example(raw)["response"]
    assert first.formatter_version == PHASE40_FORMATTER_VERSION
    assert first.formatter_sha256 == second.formatter_sha256
    assert first.raw_message == raw
    assert tokenizer.calls[0]["enable_thinking"] is False
    assert tokenizer.calls[0]["return_dict"] is False
    assert tokenizer.calls[0]["truncation"] is False
    assert tokenizer.calls[0]["add_generation_prompt"] is True
    assert tokenizer.calls[1]["add_generation_prompt"] is False


def test_response_only_mask_excludes_prompt_and_padding_but_keeps_every_answer_token():
    tokenizer = FakeTemplateTokenizer(answer_tokens=(51, 52, 53))
    tokenized = tokenize_phase40_response_only(_example(), tokenizer, max_length=16)
    collator = Phase40ResponseOnlyCollator(pad_token_id=tokenizer.pad_token_id, tensor_factory=lambda x: x)
    batch = collator([tokenized.as_item(), {"input_ids": [1, 2], "attention_mask": [1, 1], "labels": [-100, 2]}])

    assert tokenized.input_ids == (11, 12, 13, 14, 51, 52, 53)
    assert tokenized.labels == (-100, -100, -100, -100, 51, 52, 53)
    assert batch["input_ids"][1] == [1, 2, 0, 0, 0, 0, 0]
    assert batch["attention_mask"][1] == [1, 1, 0, 0, 0, 0, 0]
    assert batch["labels"][1] == [-100, 2, -100, -100, -100, -100, -100]


def test_answer_truncation_and_template_boundary_drift_fail_closed():
    with pytest.raises(ValueError, match="truncate|length"):
        tokenize_phase40_response_only(
            _example(),
            FakeTemplateTokenizer(answer_tokens=tuple(range(20))),
            max_length=8,
        )

    class BoundaryDriftTokenizer(FakeTemplateTokenizer):
        def apply_chat_template(self, messages, **kwargs):
            return [1, 2, 3] if len(messages) == 2 else [9, 2, 3, 4]

    with pytest.raises(ValueError, match="boundary"):
        tokenize_phase40_response_only(_example(), BoundaryDriftTokenizer(), max_length=16)


def test_formatter_hash_changes_when_template_or_mask_contract_changes():
    first = tokenize_phase40_response_only(_example(), FakeTemplateTokenizer(chat_template="a"), max_length=16)
    second = tokenize_phase40_response_only(_example(), FakeTemplateTokenizer(chat_template="b"), max_length=16)
    third = tokenize_phase40_response_only(_example(), FakeTemplateTokenizer(chat_template="a"), max_length=17)
    assert len(first.formatter_sha256) == 64
    assert first.formatter_sha256 != second.formatter_sha256
    assert first.formatter_sha256 != third.formatter_sha256


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "not-json",
        "```json\n{\"label\":\"benign\"}\n```",
        "[]",
        "{}",
        '{"label":"unknown"}',
        '{"label":"Benign"}',
        '{"label":" benign "}',
        '{"label":["benign","task_scam"]}',
        '{"label":"benign","label":"task_scam"}',
        '{"label":"benign"}{"label":"benign"}',
        '{"label":"benign","confidence":NaN}',
        '{"label":"benign","unexpected":true}',
    ],
)
def test_every_malformed_missing_duplicate_or_unknown_output_is_invalid(raw):
    parsed = parse_qwen_prediction(raw)
    assert parsed.state == PredictionState.INVALID_OUTPUT
    assert parsed.parser_exception


@pytest.mark.parametrize("label", LABEL_ORDER)
def test_exact_locked_labels_are_accepted_with_established_optional_fields(label):
    raw = json.dumps(
        {
            "label": label,
            "risk_tier": "high-risk",
            "suspicious_spans": ["OTP"],
            "xai_explanation": "Giải thích đầu ra kiểm thử.",
        },
        ensure_ascii=False,
    )
    parsed = parse_qwen_prediction(raw)
    assert parsed.state.value == label
    assert parsed.parser_exception is None


def test_parser_exception_is_retained_as_invalid(monkeypatch):
    import src.model_adaptation.phase40_metrics as metrics_module

    monkeypatch.setattr(metrics_module, "_load_qwen_json", lambda raw: (_ for _ in ()).throw(RuntimeError("boom")))
    parsed = metrics_module.parse_qwen_prediction('{"label":"benign"}')
    assert parsed.state == PredictionState.INVALID_OUTPUT
    assert parsed.parser_exception == "RuntimeError: boom"


def _record(label: str, index: int) -> DatasetRecord:
    return DatasetRecord(
        text=f"Tin nhắn kiểm thử validation số {index} thuộc nhãn {label}.",
        label=label,
        risk_tier="benign" if label == "benign" else "high-risk",
        suspicious_spans=[] if label == "benign" else [label],
        xai_explanation=f"Giải thích đủ dài cho validation số {index} và nhãn {label}.",
        source="synthetic_claude",
        seed_id=f"val-{index}",
    )


def _validation_snapshot(count: int = 4) -> CanonicalSplitSnapshot:
    labels = [LABEL_ORDER[index % len(LABEL_ORDER)] for index in range(count)]
    rows: list[CanonicalSnapshotRow] = []
    for index, label in enumerate(labels):
        record = _record(label, index)
        record_bytes = record.model_dump_json().encode("utf-8")
        source_sha = hashlib.sha256(record_bytes).hexdigest()
        rows.append(
            CanonicalSnapshotRow(
                split_name="val",
                canonical_index=index,
                record_bytes=record_bytes,
                record=record,
                raw_message=record.text,
                source_row_sha256=source_sha,
                snapshot_row_id=derive_snapshot_row_id("val", index, source_sha),
            )
        )
    payload = b"\n".join(row.record_bytes for row in rows) + b"\n"
    counts = tuple((label, labels.count(label)) for label in LABEL_ORDER)
    identity = SplitIdentity("val", "data/splits/val.jsonl", count, len(payload), hashlib.sha256(payload).hexdigest(), counts)
    return CanonicalSplitSnapshot("val", identity, payload, identity.sha256, tuple(rows))


class FakeGenerationTokenizer(FakeTemplateTokenizer):
    def __init__(self, raw_outputs: list[str]):
        super().__init__()
        self.raw_outputs = raw_outputs
        self._prompt_index = 0
        self._decoded = {700 + index: raw for index, raw in enumerate(raw_outputs)}

    def apply_chat_template(self, messages, **kwargs):
        self.calls.append({"messages": messages, **kwargs})
        index = self._prompt_index
        self._prompt_index += 1
        return [101, index, 102]

    def decode(self, token_ids, **kwargs):
        assert kwargs == {"skip_special_tokens": True, "clean_up_tokenization_spaces": False}
        assert len(token_ids) == 1
        return self._decoded[token_ids[0]]


class FakeGenerationModel:
    def __init__(self):
        self.training = True
        self.calls: list[dict[str, object]] = []

    def eval(self):
        self.training = False
        return self

    def train(self, mode=True):
        self.training = mode
        return self

    def generate(self, **kwargs):
        self.calls.append(kwargs)
        prompt = list(kwargs["input_ids"])
        return [prompt + [700 + len(self.calls) - 1]]


def test_generation_uses_snapshot_ids_locked_decoder_suffix_only_and_atomic_jsonl(tmp_path):
    snapshot = _validation_snapshot(4)
    raw_outputs = [json.dumps({"label": row.record.label}) for row in snapshot.rows]
    tokenizer = FakeGenerationTokenizer(raw_outputs)
    model = FakeGenerationModel()
    output_path = tmp_path / "predictions-step-50.jsonl"

    rows = generate_qwen_validation_predictions(
        model=model,
        tokenizer=tokenizer,
        candidate=build_default_catalog()[0],
        validation_snapshot=snapshot,
        artifact_identity="adapter-sha-fixture",
        checkpoint_step=50,
        output_path=output_path,
    )

    assert model.training is True
    assert tuple(row.validation_row_id for row in rows) == snapshot.validation_row_ids
    assert [row.raw_prediction for row in rows] == raw_outputs
    assert all(
        {key: call[key] for key in ("do_sample", "num_return_sequences", "max_new_tokens")}
        == {"do_sample": False, "num_return_sequences": 1, "max_new_tokens": 256}
        for call in model.calls
    )
    assert all(set(call) == {"input_ids", "attention_mask", "do_sample", "num_return_sequences", "max_new_tokens"} for call in model.calls)
    saved = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()]
    assert [row["validation_row_id"] for row in saved] == list(snapshot.validation_row_ids)
    assert [row["raw_prediction"] for row in saved] == raw_outputs
    assert not list(tmp_path.glob("*.tmp"))


def test_generation_schedule_runs_each_declared_checkpoint_and_final_once(tmp_path):
    snapshot = _validation_snapshot(2)
    raw = [json.dumps({"label": row.record.label}) for row in snapshot.rows]
    step_50_model = FakeGenerationModel()
    step_100_model = FakeGenerationModel()
    results = generate_qwen_validation_schedule(
        candidate=build_default_catalog()[0],
        validation_snapshot=snapshot,
        checkpoint_sources=(
            QwenValidationCheckpointSource(
                checkpoint_step=50,
                model=step_50_model,
                tokenizer=FakeGenerationTokenizer(raw),
                artifact_identity="fixture-step-50",
            ),
            QwenValidationCheckpointSource(
                checkpoint_step=100,
                model=step_100_model,
                tokenizer=FakeGenerationTokenizer(raw),
                artifact_identity="fixture-step-100",
            ),
        ),
        evaluation_steps=(50, 100),
        final_step=100,
        output_dir=tmp_path,
    )
    assert tuple(results) == (50, 100)
    assert len(step_50_model.calls) == 2
    assert len(step_100_model.calls) == 2
    assert (tmp_path / "predictions-step-50.jsonl").exists()
    assert (tmp_path / "predictions-step-100.jsonl").exists()


def test_generation_schedule_rejects_relabeling_one_current_model_as_history(tmp_path):
    snapshot = _validation_snapshot(1)
    raw = [json.dumps({"label": snapshot.rows[0].record.label})]
    current_model = FakeGenerationModel()
    with pytest.raises(ValueError, match="reuse one current model"):
        generate_qwen_validation_schedule(
            candidate=build_default_catalog()[0],
            validation_snapshot=snapshot,
            checkpoint_sources=(
                QwenValidationCheckpointSource(50, current_model, FakeGenerationTokenizer(raw), "step-50"),
                QwenValidationCheckpointSource(100, current_model, FakeGenerationTokenizer(raw), "step-100"),
            ),
            evaluation_steps=(50, 100),
            final_step=100,
            output_dir=tmp_path,
        )


def test_real_trainer_save_callback_binds_generation_to_saved_checkpoint(tmp_path):
    snapshot = _validation_snapshot(1)
    raw = [json.dumps({"label": snapshot.rows[0].record.label})]
    checkpoint = tmp_path / "trainer" / "checkpoint-50"
    checkpoint.mkdir(parents=True)
    (checkpoint / "adapter_config.json").write_text("{}", encoding="utf-8")
    (checkpoint / "adapter_model.bin").write_bytes(b"checkpoint-50")
    prove_fixture = lambda _model, path: (
        "adapter-state-sha256:"
        + hashlib.sha256((Path(path) / "adapter_model.bin").read_bytes()).hexdigest()
    )
    recorder = Phase40ValidationRecorder(
        tokenizer=FakeGenerationTokenizer(raw),
        candidate=build_default_catalog()[0],
        validation_snapshot=snapshot,
        training_output_dir=tmp_path / "trainer",
        prediction_output_dir=tmp_path / "validation",
        retained_artifact_root=tmp_path / "retained",
        artifact_identity_prover=prove_fixture,
    )

    class FakeTransformers:
        class TrainerCallback:
            pass

    callback = _build_validation_trainer_callback(FakeTransformers, recorder)
    control = object()
    assert callback.on_save(
        None,
        type("State", (), {"global_step": 50})(),
        control,
        model=FakeGenerationModel(),
    ) is control
    row = next(iter(recorder.metrics_by_candidate.values())).prediction_rows[0]
    assert row.checkpoint_step == 50
    assert row.artifact_identity.startswith("adapter-state-sha256:")
    assert len(list((tmp_path / "validation").glob("predictions-checkpoint-step-50-*.jsonl"))) == 1


def test_final_adapter_at_same_step_is_revalidated_when_its_state_differs(tmp_path):
    snapshot = _validation_snapshot(1)
    raw = [json.dumps({"label": snapshot.rows[0].record.label})]
    checkpoint = tmp_path / "checkpoint"
    final_adapter = tmp_path / "final"
    for path, payload in ((checkpoint, b"checkpoint"), (final_adapter, b"different-final")):
        path.mkdir()
        (path / "adapter_config.json").write_text("{}", encoding="utf-8")
        (path / "adapter_model.bin").write_bytes(payload)
    prove_fixture = lambda _model, path: (
        "adapter-state-sha256:"
        + hashlib.sha256((Path(path) / "adapter_model.bin").read_bytes()).hexdigest()
    )
    recorder = Phase40ValidationRecorder(
        tokenizer=FakeGenerationTokenizer(raw * 2),
        candidate=build_default_catalog()[0],
        validation_snapshot=snapshot,
        training_output_dir=tmp_path,
        prediction_output_dir=tmp_path / "validation",
        retained_artifact_root=tmp_path / "retained",
        artifact_identity_prover=prove_fixture,
    )
    model = FakeGenerationModel()
    recorder.record(
        model=model,
        checkpoint_step=50,
        artifact_path=checkpoint,
        artifact_scope="checkpoint",
    )
    recorder.record_final_if_needed(
        model=model,
        final_step=50,
        final_artifact_path=final_adapter,
    )
    assert len(recorder.metrics_by_candidate) == 2
    assert len(list((tmp_path / "validation").glob("predictions-*-step-50-*.jsonl"))) == 2


def test_generation_preserves_full_219_row_snapshot_order(tmp_path):
    snapshot = _validation_snapshot(219)
    raw = [json.dumps({"label": row.record.label}) for row in snapshot.rows]
    model = FakeGenerationModel()
    rows = generate_qwen_validation_predictions(
        model=model,
        tokenizer=FakeGenerationTokenizer(raw),
        candidate=build_default_catalog()[0],
        validation_snapshot=snapshot,
        artifact_identity="fixture-219",
        checkpoint_step=50,
        output_path=tmp_path / "predictions-step-50.jsonl",
    )
    assert len(rows) == 219
    assert tuple(row.validation_row_id for row in rows) == snapshot.validation_row_ids
    assert [row.sequence_index for row in rows] == list(range(219))
    assert len(model.calls) == 219


def test_generation_refuses_to_replace_different_checkpoint_bytes(tmp_path):
    snapshot = _validation_snapshot(1)
    output = tmp_path / "predictions-step-1.jsonl"
    output.write_text("different\n", encoding="utf-8")
    with pytest.raises(FileExistsError, match="different"):
        generate_qwen_validation_predictions(
            model=FakeGenerationModel(),
            tokenizer=FakeGenerationTokenizer([json.dumps({"label": snapshot.rows[0].record.label})]),
            candidate=build_default_catalog()[0],
            validation_snapshot=snapshot,
            artifact_identity="fixture",
            checkpoint_step=1,
            output_path=output,
        )
    assert output.read_text(encoding="utf-8") == "different\n"


def _prediction_rows(snapshot: CanonicalSplitSnapshot, predicted: list[str], *, step: int = 10):
    return tuple(
        Phase40PredictionRow.from_raw(
            validation_row_id=row.validation_row_id,
            sequence_index=index,
            gold_label=row.record.label,
            raw_prediction=(
                json.dumps({"label": label}) if label != "invalid_output" else "invalid"
            ),
            artifact_identity=f"artifact-{step}",
            checkpoint_step=step,
        )
        for index, (row, label) in enumerate(zip(snapshot.rows, predicted, strict=True))
    )


def test_metrics_keep_invalid_in_all_denominators_and_fixed_four_by_five_matrix():
    snapshot = _validation_snapshot(8)
    predicted = [
        "bank_impersonation",
        "invalid_output",
        "benign",
        "benign",
        "task_scam",
        "zalo_social_engineering",
        "task_scam",
        "bank_impersonation",
    ]
    result = evaluate_phase40_predictions(
        expected_validation_row_ids=snapshot.validation_row_ids,
        gold_labels=tuple(row.record.label for row in snapshot.rows),
        prediction_rows=_prediction_rows(snapshot, predicted),
    )

    assert result.evaluated_rows == 8
    assert [metric.support for metric in result.per_class] == [2, 2, 2, 2]
    assert result.invalid_output_count == 1
    assert result.invalid_output_rate == pytest.approx(1 / 8)
    assert result.risky_to_benign_count == 1
    assert result.risky_to_invalid_count == 1
    assert len(result.confusion_matrix) == 4
    assert all(len(row) == 5 for row in result.confusion_matrix)
    assert sum(sum(row) for row in result.confusion_matrix) == 8
    assert len(result.risky_to_benign_row_ids) == 1
    assert len(result.risky_to_invalid_row_ids) == 1


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "reordered", "mutated"])
def test_metrics_reject_every_validation_id_drift(mutation):
    snapshot = _validation_snapshot(4)
    rows = list(_prediction_rows(snapshot, list(LABEL_ORDER)))
    if mutation == "missing":
        rows.pop()
    elif mutation == "duplicate":
        rows[1] = replace(rows[1], validation_row_id=rows[0].validation_row_id)
    elif mutation == "reordered":
        rows[0], rows[1] = rows[1], rows[0]
    else:
        rows[0] = replace(rows[0], validation_row_id="p40-row-v1-" + "0" * 64)
    with pytest.raises(ValueError, match="validation_row_id"):
        evaluate_phase40_predictions(
            expected_validation_row_ids=snapshot.validation_row_ids,
            gold_labels=tuple(row.record.label for row in snapshot.rows),
            prediction_rows=rows,
        )


def test_metrics_are_byte_deterministic_across_identical_runs_with_adjacent_error_kinds():
    snapshot = _validation_snapshot(4)
    predictions = _prediction_rows(
        snapshot,
        ["invalid_output", "benign", "task_scam", "bank_impersonation"],
    )
    kwargs = {
        "expected_validation_row_ids": snapshot.validation_row_ids,
        "gold_labels": tuple(row.record.label for row in snapshot.rows),
        "prediction_rows": predictions,
    }
    assert evaluate_phase40_predictions(**kwargs) == evaluate_phase40_predictions(**kwargs)


def test_prediction_rows_reject_forged_parse_state_and_parser_exception():
    snapshot = _validation_snapshot(1)
    row = _prediction_rows(snapshot, ["bank_impersonation"])[0]

    with pytest.raises(ValueError, match="parsed_state.*raw_prediction"):
        replace(row, parsed_state=PredictionState.BENIGN)
    with pytest.raises(ValueError, match="parser_exception.*raw_prediction"):
        replace(row, parser_exception="fabricated parser failure")


def test_evaluator_revalidates_raw_parse_consistency_at_its_trust_boundary():
    snapshot = _validation_snapshot(1)
    row = _prediction_rows(snapshot, ["bank_impersonation"])[0]
    object.__setattr__(row, "parsed_state", PredictionState.BENIGN)

    with pytest.raises(ValueError, match="parsed_state.*raw_prediction"):
        evaluate_phase40_predictions(
            expected_validation_row_ids=snapshot.validation_row_ids,
            gold_labels=(snapshot.rows[0].record.label,),
            prediction_rows=(row,),
        )


def test_metric_result_rejects_non_finite_and_all_inconsistent_derived_fields():
    snapshot = _validation_snapshot(8)
    gold = [row.record.label for row in snapshot.rows]
    result = evaluate_phase40_predictions(
        expected_validation_row_ids=snapshot.validation_row_ids,
        gold_labels=gold,
        prediction_rows=_prediction_rows(snapshot, gold),
    )
    bad_support = replace(result.per_class[0], support=result.per_class[0].support + 1)
    mutations = (
        {"macro_f1": float("nan")},
        {"accuracy": float("inf")},
        {"evaluated_rows": result.evaluated_rows + 1},
        {"invalid_output_count": 1},
        {"invalid_output_rate": 0.5},
        {"risky_to_benign_count": 1},
        {"risky_to_invalid_count": 1},
        {"confusion_matrix": ((0, 0, 0, 0, 0),) * 4},
        {"per_class": tuple(reversed(result.per_class))},
        {"per_class": (bad_support, *result.per_class[1:])},
        {"risky_to_benign_row_ids": (snapshot.validation_row_ids[0],)},
        {"risky_to_invalid_row_ids": (snapshot.validation_row_ids[0],)},
    )
    for mutation in mutations:
        with pytest.raises(ValueError):
            replace(result, **mutation)


def _selection_metric(
    snapshot: CanonicalSplitSnapshot,
    *,
    step: int,
    predicted: list[str],
) -> Phase40MetricResult:
    return evaluate_phase40_predictions(
        expected_validation_row_ids=snapshot.validation_row_ids,
        gold_labels=tuple(row.record.label for row in snapshot.rows),
        prediction_rows=_prediction_rows(snapshot, predicted, step=step),
    )


def test_checkpoint_selection_applies_admission_macro_and_both_tie_breaks():
    snapshot = _validation_snapshot(40)
    gold = [row.record.label for row in snapshot.rows]
    floor_fail_predictions = gold.copy()
    floor_fail_predictions[0] = "task_scam"
    floor_fail_predictions[4] = "task_scam"
    invalid_predictions = gold.copy()
    invalid_predictions[3] = "invalid_output"
    lower_predictions = gold.copy()
    lower_predictions[0] = "task_scam"
    dangerous_predictions = gold.copy()
    dangerous_predictions[0] = "benign"

    floor_fail = _selection_metric(snapshot, step=5, predicted=floor_fail_predictions)
    invalid = _selection_metric(snapshot, step=6, predicted=invalid_predictions)
    lower = _selection_metric(snapshot, step=7, predicted=lower_predictions)
    more_dangerous = _selection_metric(snapshot, step=8, predicted=dangerous_predictions)
    later = _selection_metric(snapshot, step=20, predicted=gold)
    earlier = _selection_metric(snapshot, step=10, predicted=gold)

    selected = select_phase40_checkpoint(
        [floor_fail, invalid, lower, more_dangerous, later, earlier]
    )
    assert isinstance(selected, CheckpointSelection)
    assert selected.safety_gate_passed is True
    assert selected.selected_step == 10
    assert selected.selected_artifact_identity == "artifact-10"
    assert selected.status == "passed_safety_gate"


def test_checkpoint_selection_uses_risky_to_benign_before_earlier_step():
    snapshot = _validation_snapshot(40)
    gold = [row.record.label for row in snapshot.rows]
    safer_predictions = gold.copy()
    safer_predictions[0] = "task_scam"
    dangerous_predictions = gold.copy()
    dangerous_predictions[0] = "benign"
    safer = _selection_metric(snapshot, step=20, predicted=safer_predictions)
    dangerous = _selection_metric(snapshot, step=10, predicted=dangerous_predictions)

    assert safer.macro_f1 == dangerous.macro_f1
    selected = select_phase40_checkpoint([dangerous, safer])
    assert selected.selected_step == 20
    assert selected.selected_metrics.risky_to_benign_count == 0


def test_checkpoint_selection_retains_visible_failed_safety_fallback():
    snapshot = _validation_snapshot(40)
    gold = [row.record.label for row in snapshot.rows]
    higher_predictions = gold.copy()
    higher_predictions[3] = "invalid_output"
    lower = _selection_metric(
        snapshot,
        step=10,
        predicted=["invalid_output"] * len(gold),
    )
    higher = _selection_metric(snapshot, step=20, predicted=higher_predictions)
    selected = select_phase40_checkpoint([lower, higher])
    assert selected.selected_step == 20
    assert selected.safety_gate_passed is False
    assert selected.status == "failed_safety_gate"
    assert selected.violations


def test_checkpoint_selection_rejects_different_validation_cohorts():
    first_snapshot = _validation_snapshot(4)
    second_snapshot = _validation_snapshot(8)
    first_gold = [row.record.label for row in first_snapshot.rows]
    second_gold = [row.record.label for row in second_snapshot.rows]

    with pytest.raises(ValueError, match="same canonical validation cohort"):
        select_phase40_checkpoint(
            [
                _selection_metric(first_snapshot, step=10, predicted=first_gold),
                _selection_metric(second_snapshot, step=20, predicted=second_gold),
            ]
        )


def test_checkpoint_selection_revalidates_tampered_metric_values():
    snapshot = _validation_snapshot(8)
    gold = [row.record.label for row in snapshot.rows]
    result = _selection_metric(snapshot, step=10, predicted=gold)
    object.__setattr__(result, "macro_f1", 0.123)

    with pytest.raises(ValueError, match="macro_f1.*retained prediction rows"):
        select_phase40_checkpoint([result])
