"""Fixture-only tracer tests for the Phase 40 data and identity boundary."""

from __future__ import annotations

import argparse
import hashlib
import inspect
import io
import json
from pathlib import Path
import stat
from types import SimpleNamespace

import pytest

from src.data_pipeline.schemas import DatasetRecord
from src.model_adaptation.phase40_contract import (
    _CANONICAL_DOWNSTREAM_CONTRACT_RELATIVE_PATH,
    derive_snapshot_row_id,
    preflight_phase40_inputs,
)
from src.model_adaptation.phase40_metrics import (
    Phase40PredictionRow,
    PredictionState,
    evaluate_phase40_predictions,
)
from src.model_adaptation.phase40_modes import (
    AdaptationMode,
    ExperimentIdentity,
    ModelFamily,
    RunKind,
)


LABELS = (
    "bank_impersonation",
    "zalo_social_engineering",
    "task_scam",
    "benign",
)


def _record(label: str, seed_id: str, *, text_suffix: str = "") -> DatasetRecord:
    text = f"Tin nhắn kiểm thử độc lập cho {label} {seed_id}{text_suffix}."
    return DatasetRecord(
        text=text,
        label=label,
        risk_tier="benign" if label == "benign" else "high-risk",
        suspicious_spans=[] if label == "benign" else [label],
        xai_explanation=f"Giải thích kiểm thử đủ dài cho nhãn {label} và nguồn {seed_id}.",
        source="synthetic_claude",
        seed_id=seed_id,
    )


def _record_bytes(record: DatasetRecord) -> bytes:
    return record.model_dump_json().encode("utf-8")


def _jsonl_bytes(records: list[DatasetRecord], *, newline: bytes = b"\n", final_newline: bool = True) -> bytes:
    body = newline.join(_record_bytes(record) for record in records)
    return body + (newline if final_newline else b"")


def _split_metadata(payload: bytes, records: list[DatasetRecord]) -> dict[str, object]:
    counts = {label: 0 for label in LABELS}
    for record in records:
        counts[record.label] += 1
    return {
        "records": len(records),
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "label_counts": counts,
    }


def _refresh_authority_totals(authority: dict[str, object]) -> None:
    splits = authority["splits"]
    authority["total_records"] = sum(int(splits[name]["records"]) for name in ("train", "val", "test"))
    authority["total_label_counts"] = {
        label: sum(int(splits[name]["label_counts"][label]) for name in ("train", "val", "test"))
        for label in LABELS
    }


def _make_repo(
    tmp_path: Path,
    *,
    train_records: list[DatasetRecord] | None = None,
    val_records: list[DatasetRecord] | None = None,
    train_newline: bytes = b"\n",
    val_newline: bytes = b"\n",
    train_final_newline: bool = True,
    val_final_newline: bool = True,
) -> tuple[Path, Path, Path, bytes, bytes]:
    repo_root = tmp_path / "repo"
    train_records = train_records or [_record(label, f"train-{index}") for index, label in enumerate(LABELS)]
    val_records = val_records or [_record(label, f"val-{index}") for index, label in enumerate(LABELS)]
    train_bytes = _jsonl_bytes(train_records, newline=train_newline, final_newline=train_final_newline)
    val_bytes = _jsonl_bytes(val_records, newline=val_newline, final_newline=val_final_newline)

    train_path = repo_root / "data" / "splits" / "train.jsonl"
    val_path = repo_root / "data" / "splits" / "val.jsonl"
    authority_path = repo_root / Path(*_CANONICAL_DOWNSTREAM_CONTRACT_RELATIVE_PATH.parts)
    train_path.parent.mkdir(parents=True, exist_ok=True)
    authority_path.parent.mkdir(parents=True, exist_ok=True)
    train_path.write_bytes(train_bytes)
    val_path.write_bytes(val_bytes)

    train_metadata = _split_metadata(train_bytes, train_records)
    val_metadata = _split_metadata(val_bytes, val_records)
    test_metadata = {
        "records": 1,
        "bytes": 123,
        "sha256": "f" * 64,
        "label_counts": {
            "bank_impersonation": 1,
            "zalo_social_engineering": 0,
            "task_scam": 0,
            "benign": 0,
        },
    }
    total_label_counts = {
        label: int(train_metadata["label_counts"][label])
        + int(val_metadata["label_counts"][label])
        + int(test_metadata["label_counts"][label])
        for label in LABELS
    }

    authority = {
        "schema_version": "phase39-downstream-data-contract-v1",
        "source_manifest": {
            "path": "data/manifests/manifest.json",
            "sha256": "a" * 64,
            "version": "phase39-fixture-v1",
        },
        "total_records": len(train_records) + len(val_records) + 1,
        "splits": {
            "train": train_metadata,
            "val": val_metadata,
            "test": test_metadata,
        },
        "total_label_counts": total_label_counts,
        "phase40_training_boundary": {
            "allowed_splits": ["train", "val"],
            "forbidden_split": "test",
            "rule": "fixture boundary",
            "starts_after": "fixture",
        },
        "held_out_test": {
            "path": "data/splits/test.jsonl",
            "records": 1,
            "bytes": 123,
            "sha256": "f" * 64,
            "evaluation_phase": 41,
            "touch_policy": "fixture metadata only",
        },
    }
    authority_path.write_text(json.dumps(authority, ensure_ascii=False), encoding="utf-8")
    return repo_root, train_path, val_path, train_bytes, val_bytes


def test_preflight_authorizes_before_open_and_preserves_canonical_snapshot(tmp_path, monkeypatch):
    import src.model_adaptation.phase40_contract as contract_module

    repeated = _record("bank_impersonation", "train-repeat")
    train_records = [repeated, repeated] + [
        _record("zalo_social_engineering", "train-zalo"),
        _record("task_scam", "train-task"),
        _record("benign", "train-benign"),
    ]
    val_records = [_record(label, f"val-{index}") for index, label in enumerate(LABELS)]
    repo_root, train_path, val_path, train_bytes, val_bytes = _make_repo(
        tmp_path,
        train_records=train_records,
        val_records=val_records,
    )
    opened: list[Path] = []
    real_open = contract_module._open_binary

    def spy_open(path: Path):
        opened.append(path)
        return real_open(path)

    monkeypatch.setattr(contract_module, "_open_binary", spy_open)
    result = preflight_phase40_inputs(train_path, val_path, repo_root=repo_root)

    authority_path = repo_root / Path(*_CANONICAL_DOWNSTREAM_CONTRACT_RELATIVE_PATH.parts)
    assert opened == [authority_path, train_path, val_path]
    assert [identity.split_name for identity in result.ordered_identities] == ["train", "val"]
    assert result.train_snapshot.whole_file_bytes == train_bytes
    assert result.validation_snapshot.whole_file_bytes == val_bytes
    assert result.train_snapshot.whole_file_sha256 == hashlib.sha256(train_bytes).hexdigest()
    assert result.validation_snapshot.whole_file_sha256 == hashlib.sha256(val_bytes).hexdigest()
    assert tuple(row.canonical_index for row in result.train_snapshot.rows) == tuple(range(5))
    assert result.train_snapshot.rows[0].record_bytes == _record_bytes(repeated)
    assert result.train_snapshot.rows[0].raw_message == repeated.text
    assert result.train_snapshot.rows[0].source_row_sha256 == hashlib.sha256(_record_bytes(repeated)).hexdigest()
    assert result.train_snapshot.rows[0].snapshot_row_id != result.train_snapshot.rows[1].snapshot_row_id
    with pytest.raises(Exception):
        result.train_snapshot.rows[0].record.text = "mutation must fail"
    with pytest.raises(Exception):
        result.train_snapshot.rows[0].record.suspicious_spans += ("mutation",)
    assert result.held_out_test.path == "data/splits/test.jsonl"
    assert result.held_out_test.sha256 == "f" * 64


@pytest.mark.parametrize("bad_argument", ["train", "val"])
def test_rejected_data_path_causes_zero_open_calls(tmp_path, monkeypatch, bad_argument):
    import src.model_adaptation.phase40_contract as contract_module

    repo_root, train_path, val_path, _, _ = _make_repo(tmp_path)
    decoy = repo_root / "data" / "splits" / "reserved-decoy.jsonl"
    opened: list[Path] = []
    monkeypatch.setattr(contract_module, "_open_binary", lambda path: opened.append(path) or io.BytesIO(b""))

    with pytest.raises(ValueError, match="canonical"):
        preflight_phase40_inputs(
            decoy if bad_argument == "train" else train_path,
            decoy if bad_argument == "val" else val_path,
            repo_root=repo_root,
        )

    assert opened == []


def test_mutated_private_authority_path_causes_zero_open_calls(tmp_path, monkeypatch):
    import src.model_adaptation.phase40_contract as contract_module

    repo_root, train_path, val_path, _, _ = _make_repo(tmp_path)
    opened: list[Path] = []
    monkeypatch.setattr(
        contract_module,
        "_CANONICAL_DOWNSTREAM_CONTRACT_RELATIVE_PATH",
        Path(".planning/decoy-authority.json"),
    )
    monkeypatch.setattr(contract_module, "_open_binary", lambda path: opened.append(path) or io.BytesIO(b""))

    with pytest.raises(RuntimeError, match="authority"):
        preflight_phase40_inputs(train_path, val_path, repo_root=repo_root)

    assert opened == []


@pytest.mark.parametrize("target_name", ["authority", "train", "val"])
@pytest.mark.parametrize("redirect_kind", ["symlink", "junction"])
def test_redirecting_canonical_path_component_causes_zero_open_calls(
    tmp_path,
    monkeypatch,
    target_name,
    redirect_kind,
):
    import src.model_adaptation.phase40_contract as contract_module

    repo_root, train_path, val_path, _, _ = _make_repo(tmp_path)
    authority_path = repo_root / Path(*_CANONICAL_DOWNSTREAM_CONTRACT_RELATIVE_PATH.parts)
    targets = {
        "authority": authority_path,
        "train": train_path,
        "val": val_path,
    }
    redirect_target = targets[target_name]
    real_lstat = contract_module.os.lstat
    opened: list[Path] = []

    def fake_lstat(path):
        if Path(path) == redirect_target:
            if redirect_kind == "symlink":
                return SimpleNamespace(st_mode=stat.S_IFLNK, st_reparse_tag=0)
            return SimpleNamespace(
                st_mode=stat.S_IFDIR,
                st_reparse_tag=getattr(stat, "IO_REPARSE_TAG_MOUNT_POINT", 0xA0000003),
            )
        return real_lstat(path)

    monkeypatch.setattr(contract_module.os, "lstat", fake_lstat)
    monkeypatch.setattr(contract_module, "_open_binary", lambda path: opened.append(path) or io.BytesIO(b""))

    with pytest.raises(ValueError, match="symbolic link or junction"):
        preflight_phase40_inputs(train_path, val_path, repo_root=repo_root)

    assert opened == []


def test_public_preflight_signature_has_no_authority_override():
    parameters = inspect.signature(preflight_phase40_inputs).parameters
    assert tuple(parameters) == ("train_path", "val_path", "repo_root")
    assert "authority" not in " ".join(parameters).lower()


def test_authority_duplicate_keys_are_rejected(tmp_path):
    repo_root, train_path, val_path, _, _ = _make_repo(tmp_path)
    authority_path = repo_root / Path(*_CANONICAL_DOWNSTREAM_CONTRACT_RELATIVE_PATH.parts)
    authority_bytes = authority_path.read_bytes()
    authority_path.write_bytes(b'{"schema_version":"shadow",' + authority_bytes[1:])

    with pytest.raises(ValueError, match="duplicate JSON key: schema_version"):
        preflight_phase40_inputs(train_path, val_path, repo_root=repo_root)


@pytest.mark.parametrize(
    ("corruption", "message"),
    [
        ("empty", "empty"),
        ("invalid_utf8", "UTF-8"),
        ("bare_cr", "bare CR"),
        ("blank_record", "blank"),
        ("hash", "SHA-256"),
        ("count", "record count"),
        ("support", "label support"),
        ("seed_overlap", "seed"),
        ("duplicate_key", "duplicate JSON key"),
        ("extra_field", "fields mismatch"),
    ],
)
def test_preflight_fails_explicitly_for_invalid_inputs(tmp_path, corruption, message):
    repo_root, train_path, val_path, _, _ = _make_repo(tmp_path)
    authority_path = repo_root / Path(*_CANONICAL_DOWNSTREAM_CONTRACT_RELATIVE_PATH.parts)
    authority = json.loads(authority_path.read_text(encoding="utf-8"))

    if corruption == "empty":
        train_path.write_bytes(b"")
        authority["splits"]["train"].update(_split_metadata(b"", []))
    elif corruption == "invalid_utf8":
        payload = b"\xff\n"
        train_path.write_bytes(payload)
        authority["splits"]["train"].update(
            {"records": 1, "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}
        )
        authority["splits"]["train"]["label_counts"] = {
            "bank_impersonation": 1,
            "zalo_social_engineering": 0,
            "task_scam": 0,
            "benign": 0,
        }
    elif corruption == "bare_cr":
        payload = train_path.read_bytes().replace(b"\n", b"\r", 1)
        train_path.write_bytes(payload)
        authority["splits"]["train"].update(
            {"bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}
        )
    elif corruption == "blank_record":
        payload = train_path.read_bytes().replace(b"\n", b"\n\n", 1)
        train_path.write_bytes(payload)
        authority["splits"]["train"].update(
            {"records": authority["splits"]["train"]["records"] + 1, "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}
        )
        authority["splits"]["train"]["label_counts"]["benign"] += 1
    elif corruption == "hash":
        authority["splits"]["train"]["sha256"] = "0" * 64
    elif corruption == "count":
        authority["splits"]["train"]["records"] += 1
        authority["splits"]["train"]["label_counts"]["benign"] += 1
    elif corruption == "support":
        authority["splits"]["train"]["label_counts"]["bank_impersonation"] += 1
        authority["splits"]["train"]["label_counts"]["benign"] -= 1
    elif corruption == "seed_overlap":
        train_records = [_record(label, f"shared-{index}") for index, label in enumerate(LABELS)]
        val_records = [_record(label, f"shared-{index}") for index, label in enumerate(LABELS)]
        repo_root, train_path, val_path, _, _ = _make_repo(
            tmp_path / "overlap",
            train_records=train_records,
            val_records=val_records,
        )
        authority_path = repo_root / Path(*_CANONICAL_DOWNSTREAM_CONTRACT_RELATIVE_PATH.parts)
        authority = json.loads(authority_path.read_text(encoding="utf-8"))
    elif corruption in {"duplicate_key", "extra_field"}:
        lines = train_path.read_bytes().splitlines()
        if corruption == "duplicate_key":
            lines[0] = b'{"text":"shadow duplicate",' + lines[0][1:]
        else:
            first = json.loads(lines[0])
            first["unexpected"] = "must fail"
            lines[0] = json.dumps(first, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        payload = b"\n".join(lines) + b"\n"
        train_path.write_bytes(payload)
        authority["splits"]["train"].update(
            {"bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}
        )

    _refresh_authority_totals(authority)
    authority_path.write_text(json.dumps(authority), encoding="utf-8")
    with pytest.raises((ValueError, UnicodeDecodeError), match=message):
        preflight_phase40_inputs(train_path, val_path, repo_root=repo_root)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("source_manifest", "source_manifest"),
        ("total_records", "total record count"),
        ("total_labels", "total label support"),
        ("held_out", "held_out_test"),
    ],
)
def test_authority_reconciliation_is_fail_closed(tmp_path, mutation, message):
    repo_root, train_path, val_path, _, _ = _make_repo(tmp_path)
    authority_path = repo_root / Path(*_CANONICAL_DOWNSTREAM_CONTRACT_RELATIVE_PATH.parts)
    authority = json.loads(authority_path.read_text(encoding="utf-8"))
    if mutation == "source_manifest":
        authority["source_manifest"]["path"] = "data/manifests/decoy.json"
    elif mutation == "total_records":
        authority["total_records"] += 1
    elif mutation == "total_labels":
        authority["total_label_counts"]["benign"] += 1
    else:
        authority["held_out_test"]["sha256"] = "e" * 64
    authority_path.write_text(json.dumps(authority), encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        preflight_phase40_inputs(train_path, val_path, repo_root=repo_root)


def test_record_ids_are_line_ending_invariant_but_index_and_bytes_sensitive(tmp_path):
    records = [_record(label, f"seed-{index}") for index, label in enumerate(LABELS)]
    lf_root, lf_train, lf_val, _, _ = _make_repo(tmp_path / "lf", train_records=records, val_records=[_record(label, f"val-lf-{i}") for i, label in enumerate(LABELS)])
    crlf_root, crlf_train, crlf_val, _, _ = _make_repo(
        tmp_path / "crlf",
        train_records=records,
        val_records=[_record(label, f"val-crlf-{i}") for i, label in enumerate(LABELS)],
        train_newline=b"\r\n",
        train_final_newline=False,
        val_final_newline=False,
    )
    lf = preflight_phase40_inputs(lf_train, lf_val, repo_root=lf_root)
    crlf = preflight_phase40_inputs(crlf_train, crlf_val, repo_root=crlf_root)

    assert [row.record_bytes for row in lf.train_snapshot.rows] == [row.record_bytes for row in crlf.train_snapshot.rows]
    assert [row.snapshot_row_id for row in lf.train_snapshot.rows] == [row.snapshot_row_id for row in crlf.train_snapshot.rows]
    original = lf.train_snapshot.rows[0]
    assert derive_snapshot_row_id("train", 1, original.source_row_sha256) != original.snapshot_row_id
    mutated_sha = hashlib.sha256(original.record_bytes + b" ").hexdigest()
    assert derive_snapshot_row_id("train", 0, mutated_sha) != original.snapshot_row_id


def test_snapshot_row_id_matches_independent_literal_contract_vector():
    source_row_sha256 = "00" * 32

    assert derive_snapshot_row_id("val", 7, source_row_sha256) == (
        "p40-row-v1-fdf83e752eb4aeba1241165f3d5e136daf0ef7bc6805135366decc37d032a806"
    )


def test_unicode_normalization_forms_remain_byte_distinct(tmp_path):
    composed = _record("bank_impersonation", "train-composed", text_suffix=" số tiền đã chuyển")
    decomposed = _record("bank_impersonation", "train-decomposed", text_suffix=" số tiền đã chuyển")
    train_records = [composed, decomposed] + [
        _record("zalo_social_engineering", "train-zalo"),
        _record("task_scam", "train-task"),
        _record("benign", "train-benign"),
    ]
    repo_root, train_path, val_path, _, _ = _make_repo(tmp_path, train_records=train_records)
    contract = preflight_phase40_inputs(train_path, val_path, repo_root=repo_root)

    first, second = contract.train_snapshot.rows[:2]
    assert first.raw_message != second.raw_message
    assert first.record_bytes != second.record_bytes
    assert first.source_row_sha256 != second.source_row_sha256
    assert first.snapshot_row_id != second.snapshot_row_id


SUPPORTED_IDENTITIES = {
    (ModelFamily.QWEN, AdaptationMode.LORA, RunKind.PROBE),
    (ModelFamily.QWEN, AdaptationMode.LORA, RunKind.FULL),
    (ModelFamily.QWEN, AdaptationMode.QLORA, RunKind.PROBE),
    (ModelFamily.QWEN, AdaptationMode.QLORA, RunKind.FULL),
    (ModelFamily.PHOBERT, AdaptationMode.CLASSIFICATION_HEAD, RunKind.FULL),
}


@pytest.mark.parametrize(
    ("family", "mode", "kind"),
    [
        (family, mode, kind)
        for family in ModelFamily
        for mode in AdaptationMode
        for kind in RunKind
    ],
)
def test_experiment_identity_accepts_exactly_supported_tuples(family, mode, kind):
    values = (family, mode, kind)
    if values in SUPPORTED_IDENTITIES:
        assert ExperimentIdentity(family, mode, kind).as_tuple() == tuple(value.value for value in values)
    else:
        with pytest.raises(ValueError, match="unsupported"):
            ExperimentIdentity(family, mode, kind)


def test_tracer_reaches_strict_metric_boundary_without_dropping_invalid_row(tmp_path):
    repo_root, train_path, val_path, _, _ = _make_repo(tmp_path)
    contract = preflight_phase40_inputs(train_path, val_path, repo_root=repo_root)
    validation_rows = contract.validation_snapshot.rows[:2]
    predictions = (
        Phase40PredictionRow.from_raw(
            validation_row_id=validation_rows[0].validation_row_id,
            sequence_index=0,
            gold_label=validation_rows[0].record.label,
            raw_prediction=json.dumps({"label": validation_rows[0].record.label}),
            artifact_identity="fixture-adapter",
            checkpoint_step=1,
        ),
        Phase40PredictionRow.from_raw(
            validation_row_id=validation_rows[1].validation_row_id,
            sequence_index=1,
            gold_label=validation_rows[1].record.label,
            raw_prediction="not-json",
            artifact_identity="fixture-adapter",
            checkpoint_step=1,
        ),
    )
    metrics = evaluate_phase40_predictions(
        expected_validation_row_ids=tuple(row.validation_row_id for row in validation_rows),
        gold_labels=tuple(row.record.label for row in validation_rows),
        prediction_rows=predictions,
    )

    assert metrics.evaluated_rows == 2
    assert metrics.invalid_output_count == 1
    assert metrics.prediction_rows[0].parsed_state == PredictionState.BANK_IMPERSONATION
    assert metrics.prediction_rows[1].parsed_state == PredictionState.INVALID_OUTPUT
    assert sum(sum(row) for row in metrics.confusion_matrix) == 2


def test_phase40_preflight_cli_has_only_two_required_data_inputs():
    from src.model_adaptation.cli import build_parser

    parser = build_parser()
    subparsers = next(action for action in parser._actions if isinstance(action, argparse._SubParsersAction))
    phase40_parser = subparsers.choices["phase40-preflight"]
    required = {action.dest for action in phase40_parser._actions if action.required}
    destinations = {action.dest for action in phase40_parser._actions}

    assert required == {"train_split", "val_split"}
    assert "test_split" not in destinations
    assert all("authority" not in destination for destination in destinations)


def test_phase40_preflight_cli_runs_fixture_contract_in_stable_open_order(
    tmp_path,
    monkeypatch,
    capsys,
):
    import src.model_adaptation.cli as cli_module
    import src.model_adaptation.phase40_contract as contract_module

    repo_root, train_path, val_path, _, _ = _make_repo(tmp_path)
    authority_path = repo_root / Path(*_CANONICAL_DOWNSTREAM_CONTRACT_RELATIVE_PATH.parts)
    opened: list[Path] = []
    real_open = contract_module._open_binary

    def spy_open(path: Path):
        opened.append(path)
        return real_open(path)

    monkeypatch.chdir(repo_root)
    monkeypatch.setattr(contract_module, "_open_binary", spy_open)

    exit_code = cli_module.main(
        [
            "phase40-preflight",
            "--train-split",
            str(train_path),
            "--val-split",
            str(val_path),
        ]
    )

    assert exit_code == 0
    assert opened == [authority_path, train_path, val_path]
    output = capsys.readouterr().out.splitlines()
    assert output[0].startswith("train: records=")
    assert output[1].startswith("val: records=")


def test_building_phase40_cli_parser_does_not_resolve_legacy_paths(monkeypatch):
    import src.model_adaptation.cli as cli_module

    def forbidden_default(*args, **kwargs):
        raise AssertionError("legacy filesystem/settings default resolved while building parser")

    monkeypatch.setattr(cli_module, "_default_split_path", forbidden_default)
    monkeypatch.setattr(cli_module, "_default_registry_path", forbidden_default)
    monkeypatch.setattr(cli_module, "_default_phase_five_split_path", forbidden_default)

    parser = cli_module.build_parser()
    assert parser.prog == "python -m src.model_adaptation.cli"
