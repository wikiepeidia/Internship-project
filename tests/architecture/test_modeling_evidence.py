from __future__ import annotations

import copy
import hashlib
import inspect
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.modeling.evaluation import TwoModelEvaluationResult
from src.modeling.evidence import (
    ReportingAuthorityError,
    ReportingAuthorityPins,
    _load_reporting_authority,
    load_reporting_authority,
)


LABELS = (
    "bank_impersonation",
    "zalo_social_engineering",
    "task_scam",
    "benign",
)
PREDICTION_COLUMNS = (*LABELS, "invalid_output")
EVIDENCE_NAMES = (
    "evaluation-request.json",
    "frozen-inference-protocols.json",
    "execution-source-manifest.json",
    "execution-materialization-receipt.json",
    "preauthorization-receipt.json",
    "one-shot-authorization.json",
    "one-shot-claim.json",
    "evaluation-access-receipt.json",
    "qwen-predictions.jsonl",
    "phobert-predictions.jsonl",
    "results.json",
    "results.md",
)


def _json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
        + "\n"
    ).encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _metric_payload(*, perfect: bool = False) -> dict[str, object]:
    if perfect:
        matrix = [[2, 0, 0, 0, 0], [0, 1, 0, 0, 0], [0, 0, 1, 0, 0], [0, 0, 0, 2, 0]]
        values = ((1.0, 1.0, 1.0),) * 4
        accuracy = macro_f1 = weighted_f1 = 1.0
    else:
        matrix = [[2, 0, 0, 0, 0], [0, 1, 0, 0, 0], [0, 0, 1, 0, 0], [1, 0, 0, 1, 0]]
        values = ((2 / 3, 1.0, 0.8), (1.0, 1.0, 1.0), (1.0, 1.0, 1.0), (1.0, 0.5, 2 / 3))
        accuracy, macro_f1, weighted_f1 = 5 / 6, 13 / 15, 37 / 45
    per_class = [
        {"label": label, "precision": precision, "recall": recall, "f1": f1, "support": support}
        for label, support, (precision, recall, f1) in zip(
            LABELS, (2, 1, 1, 2), values, strict=True
        )
    ]
    return {
        "accuracy": accuracy,
        "confusion_matrix": matrix,
        "evaluated_rows": 6,
        "invalid_output_count": 0,
        "invalid_output_rate": 0.0,
        "label_order": list(LABELS),
        "macro_f1": macro_f1,
        "per_class": per_class,
        "prediction_columns": list(PREDICTION_COLUMNS),
        "risky_to_benign_count": 0,
        "risky_to_invalid_count": 0,
        "weighted_f1": weighted_f1,
    }


def _result_payload() -> dict[str, object]:
    return {
        "authorization_sha256": "a" * 64,
        "claim_sha256": "b" * 64,
        "comparison_statements": [
            "PhoBERT higher on: macro_f1.",
            "Qwen higher on: none.",
            "Ties: invalid_output_count(lower_is_better).",
        ],
        "held_out": {"bytes": 321, "records": 6, "sha256": "c" * 64},
        "models": [
            {
                "artifact_sha256": "d" * 64,
                "metrics": _metric_payload(),
                "predictions_sha256": "e" * 64,
                "role": "qwen",
                "run_id": "qwen-frozen-run",
                "selected_checkpoint_identity": "adapter-state-sha256:" + "f" * 64,
            },
            {
                "artifact_sha256": "1" * 64,
                "metrics": _metric_payload(perfect=True),
                "predictions_sha256": "2" * 64,
                "role": "phobert",
                "run_id": "phobert-frozen-run",
                "selected_checkpoint_identity": "model-state-sha256:" + "3" * 64,
            },
        ],
        "prepared_sha256": "4" * 64,
        "prior_exposure": {
            "claim": "one_post_freeze_model_evaluation_pass",
            "human_content_exposure_disclosed": True,
        },
        "schema_version": "phase41-one-shot-results-v1",
        "status": "completed",
        "terminal_policy": {
            "rerun_permitted": False,
            "test_driven_checkpoint_selection_permitted": False,
            "test_driven_contingency_activation_permitted": False,
            "test_driven_dataset_repair_permitted": False,
            "test_driven_training_action_permitted": False,
        },
    }


def _source_manifest_payload() -> dict[str, object]:
    return {
        "alternate_evaluators_permitted": False,
        "closed_import_roots": ["src.model_adaptation.phase41_evaluation"],
        "files": [{"bytes": 10, "path": "src/frozen.py", "sha256": "5" * 64}],
        "launcher": {
            "bytes": 20,
            "path": "scripts/frozen-launcher.ps1",
            "sha256": "6" * 64,
        },
        "launcher_host": {
            "external_launch_receipt_sha256": "a" * 64,
            "sha256": "b" * 64,
        },
        "preparation_scope": "production_canonical",
        "python": {
            "runtime_import_roots": ["C:/synthetic/site-packages"],
            "sha256": "c" * 64,
        },
        "schema_version": "phase41-execution-source-manifest-v1",
        "source_tree_sha256": "7" * 64,
        "upstream_declared_source_tree_sha256": "8" * 64,
    }


def _materialization_payload(source_manifest_sha256: str) -> dict[str, object]:
    return {
        "external_launcher_authority_sha256": "a" * 64,
        "launcher_sha256": "6" * 64,
        "launcher_host_sha256": "b" * 64,
        "mode": "locked-clean-runtime",
        "preparation_scope": "production_canonical",
        "python_executable_sha256": "c" * 64,
        "runtime_import_roots": ["C:/synthetic/site-packages"],
        "schema_version": "phase41-execution-materialization-v1",
        "source_file_count": 1,
        "source_handles_locked_at_launch": True,
        "source_manifest_sha256": source_manifest_sha256,
        "source_tree_sha256": "7" * 64,
    }


def _erratum_payload(evidence_manifest_sha256: str) -> dict[str, object]:
    return {
        "access_impact": {
            "model_inference_performed_by_these_tests": False,
            "terminal_model_evaluation_retried": False,
        },
        "automated_split_reads": [
            {
                "minimum_occurrences": 2,
                "operations": ["parse_jsonl_rows"],
                "period": "before_terminal_model_evaluation",
                "scope": "broad_default_pytest_runs",
                "statement": "Synthetic disclosure statement.",
            }
        ],
        "corrected_claim": "Exactly one terminal shared-cohort model-evaluation pass.",
        "downstream_requirement": "Consume this disclosure with the frozen export.",
        "retracted_claims": ["absolute global zero reserved-split access"],
        "schema_version": "phase41-provenance-erratum-v1",
        "sealed_export": {
            "erratum_location": "external_non_sealed_companion",
            "evidence_manifest_sha256": evidence_manifest_sha256,
            "modified_or_resealed": False,
            "prediction_or_metric_artifacts_modified": False,
        },
        "status": "corrective_disclosure",
    }


def _write_authority(tmp_path: Path) -> tuple[Path, Path, dict[str, bytes]]:
    source_bytes = _json_bytes(_source_manifest_payload())
    receipt_bytes = _json_bytes(_materialization_payload(_sha256(source_bytes)))
    payloads = {
        "evaluation-request.json": _json_bytes({"synthetic": "request"}),
        "frozen-inference-protocols.json": _json_bytes({"synthetic": "protocols"}),
        "execution-source-manifest.json": source_bytes,
        "execution-materialization-receipt.json": receipt_bytes,
        "preauthorization-receipt.json": _json_bytes({"synthetic": "preauthorization"}),
        "one-shot-authorization.json": _json_bytes({"synthetic": "authorization"}),
        "one-shot-claim.json": _json_bytes({"synthetic": "claim"}),
        "evaluation-access-receipt.json": _json_bytes({"synthetic": "access"}),
        "qwen-predictions.jsonl": b'{"synthetic":"qwen"}\n',
        "phobert-predictions.jsonl": b'{"synthetic":"phobert"}\n',
        "results.md": b"# Synthetic results\n",
    }
    result_payload = _result_payload()
    result_payload["prepared_sha256"] = _sha256(payloads["evaluation-request.json"])
    result_payload["authorization_sha256"] = _sha256(
        payloads["one-shot-authorization.json"]
    )
    result_payload["claim_sha256"] = _sha256(payloads["one-shot-claim.json"])
    result_payload["models"][0]["predictions_sha256"] = _sha256(
        payloads["qwen-predictions.jsonl"]
    )
    result_payload["models"][1]["predictions_sha256"] = _sha256(
        payloads["phobert-predictions.jsonl"]
    )
    payloads["results.json"] = _json_bytes(result_payload)
    evidence_manifest = {
        "artifacts": [
            {"name": name, "sha256": _sha256(payloads[name])}
            for name in EVIDENCE_NAMES
        ],
        "schema_version": "phase41-evidence-manifest-v1",
        "status": "completed",
        "terminal_policy": {
            "rerun_permitted": False,
            "test_outcome_used_for_tuning": False,
            "unbiased_test_score_claim_after_deployment_fit": False,
        },
    }
    manifest_bytes = _json_bytes(evidence_manifest)
    export_root = tmp_path / _sha256(manifest_bytes)
    export_root.mkdir(parents=True)
    for name, value in payloads.items():
        (export_root / name).write_bytes(value)
    (export_root / "evidence-manifest.json").write_bytes(manifest_bytes)

    erratum_path = tmp_path / "provenance-erratum.json"
    erratum_bytes = _json_bytes(_erratum_payload(_sha256(manifest_bytes)))
    erratum_path.write_bytes(erratum_bytes)
    payloads["evidence-manifest.json"] = manifest_bytes
    payloads["provenance-erratum.json"] = erratum_bytes
    return export_root, erratum_path, payloads


def _synthetic_pins(export_root: Path, erratum_path: Path) -> ReportingAuthorityPins:
    return ReportingAuthorityPins(
        export_manifest_sha256=_sha256((export_root / "evidence-manifest.json").read_bytes()),
        erratum_sha256=_sha256(erratum_path.read_bytes()),
        source_tree_sha256="7" * 64,
    )


def _load_synthetic(export_root: Path, erratum_path: Path):
    return _load_reporting_authority(
        export_root,
        erratum_path,
        _synthetic_pins(export_root, erratum_path),
    )


def _rewrite_manifest(
    export_root: Path,
    erratum_path: Path,
    mutate,
) -> Path:
    manifest_path = export_root / "evidence-manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    mutate(manifest)
    manifest_bytes = _json_bytes(manifest)
    erratum_path.write_bytes(_json_bytes(_erratum_payload(_sha256(manifest_bytes))))
    replacement = export_root.with_name(_sha256(manifest_bytes))
    replacement.mkdir()
    for name in EVIDENCE_NAMES:
        (replacement / name).write_bytes((export_root / name).read_bytes())
    (replacement / "evidence-manifest.json").write_bytes(manifest_bytes)
    return replacement


def _replace_member_and_rebind(
    export_root: Path,
    erratum_path: Path,
    name: str,
    payload: dict[str, object],
) -> Path:
    member_bytes = _json_bytes(payload)
    (export_root / name).write_bytes(member_bytes)

    def update(manifest: dict[str, object]) -> None:
        next(item for item in manifest["artifacts"] if item["name"] == name)[
            "sha256"
        ] = _sha256(member_bytes)

    return _rewrite_manifest(export_root, erratum_path, update)


@pytest.mark.parametrize(
    ("mutate", "match"),
    [
        (lambda value: value["models"].reverse(), "fixed order"),
        (
            lambda value: value["models"][0]["metrics"].update(
                label_order=list(reversed(LABELS))
            ),
            "label order",
        ),
        (
            lambda value: value["models"][0]["metrics"].update(
                confusion_matrix=[[1, 0], [0, 1]]
            ),
            "confusion matrix",
        ),
        (
            lambda value: value["terminal_policy"].update(rerun_permitted=True),
            "rerun",
        ),
        (
            lambda value: value.update(comparison_statements=["Models compared."]),
            "comparison statements",
        ),
        (
            lambda value: value["models"][0]["metrics"].update(
                risky_to_benign_count=1
            ),
            "risky-to-benign",
        ),
        (
            lambda value: value["models"][0].update(
                selected_checkpoint_identity="model-state-sha256:" + "f" * 64
            ),
            "checkpoint identity",
        ),
    ],
)
def test_two_model_contract_rejects_drift(mutate, match: str):
    payload = _result_payload()
    mutate(payload)
    with pytest.raises(ValidationError, match=match):
        TwoModelEvaluationResult.model_validate(payload)


@pytest.mark.parametrize(
    ("field", "match"),
    (
        ("precision", "precision must match"),
        ("recall", "recall must match"),
        ("f1", "f1 must match"),
    ),
)
def test_metric_contract_recomputes_each_class_metric(field: str, match: str) -> None:
    payload = _result_payload()
    payload["models"][0]["metrics"]["per_class"][0][field] = 0.123
    with pytest.raises(ValidationError, match=match):
        TwoModelEvaluationResult.model_validate(payload)


@pytest.mark.parametrize(
    ("field", "match"),
    (("macro_f1", "macro F1"), ("weighted_f1", "weighted F1")),
)
def test_metric_contract_recomputes_aggregate_f1(field: str, match: str) -> None:
    payload = _result_payload()
    payload["models"][0]["metrics"][field] = 0.123
    with pytest.raises(ValidationError, match=match):
        TwoModelEvaluationResult.model_validate(payload)


def test_comparison_contract_rejects_reversed_claim() -> None:
    payload = _result_payload()
    payload["comparison_statements"][1] = "Qwen higher on: macro_f1."
    with pytest.raises(ValidationError, match="reverses metric fact"):
        TwoModelEvaluationResult.model_validate(payload)


def test_reporting_authority_returns_typed_facts_and_raw_byte_hashes(tmp_path: Path):
    export_root, erratum_path, payloads = _write_authority(tmp_path)

    authority = _load_synthetic(export_root, erratum_path)

    assert [model.role for model in authority.result.models] == ["qwen", "phobert"]
    assert authority.source_tree_sha256 == "7" * 64
    assert authority.refactored_source_is_metric_producer is False
    assert authority.export_manifest_sha256 == _sha256(payloads["evidence-manifest.json"])
    assert authority.results_sha256 == _sha256(payloads["results.json"])
    assert authority.source_manifest_sha256 == _sha256(
        payloads["execution-source-manifest.json"]
    )
    assert authority.materialization_receipt_sha256 == _sha256(
        payloads["execution-materialization-receipt.json"]
    )
    assert authority.erratum_sha256 == _sha256(payloads["provenance-erratum.json"])
    assert authority.results_raw == payloads["results.json"]
    assert dict(authority.artifact_raw) == {
        name: payloads[name] for name in EVIDENCE_NAMES
    }
    assert authority.erratum_raw == payloads["provenance-erratum.json"]
    assert authority.retracted_claims == (
        "absolute global zero reserved-split access",
    )
    assert authority.access_impact == (
        ("model_inference_performed_by_these_tests", False),
        ("terminal_model_evaluation_retried", False),
    )
    assert authority.automated_access_statements == ("Synthetic disclosure statement.",)


def test_reporting_reader_is_read_only_and_captures_prediction_bytes(tmp_path: Path):
    export_root, erratum_path, _ = _write_authority(tmp_path)
    before = {path.relative_to(tmp_path): path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    pins = _synthetic_pins(export_root, erratum_path)
    authority = _load_reporting_authority(export_root, erratum_path, pins)
    after = {path.relative_to(tmp_path): path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}

    assert after == before
    assert dict(authority.artifact_raw)["qwen-predictions.jsonl"].startswith(b"{")
    assert tuple(inspect.signature(load_reporting_authority).parameters) == (
        "export_root",
        "erratum_path",
    )


def test_reporting_authority_binds_export_directory_and_result_links(tmp_path: Path):
    export_root, erratum_path, _ = _write_authority(tmp_path)
    wrong_named_root = export_root.with_name("wrong-export-name")
    wrong_named_root.mkdir()
    for name in (*EVIDENCE_NAMES, "evidence-manifest.json"):
        (wrong_named_root / name).write_bytes((export_root / name).read_bytes())
    with pytest.raises(ReportingAuthorityError, match="directory identity"):
        _load_reporting_authority(
            wrong_named_root,
            erratum_path,
            _synthetic_pins(export_root, erratum_path),
        )

    export_root, erratum_path, _ = _write_authority(tmp_path / "second")

    result = json.loads((export_root / "results.json").read_bytes())
    result["prepared_sha256"] = "f" * 64
    export_root = _replace_member_and_rebind(
        export_root, erratum_path, "results.json", result
    )
    with pytest.raises(ReportingAuthorityError, match="prepared request link"):
        _load_synthetic(export_root, erratum_path)


@pytest.mark.parametrize("case", ("missing", "changed", "unexpected", "redirect"))
def test_reporting_authority_requires_exact_stable_membership(
    tmp_path: Path, case: str
) -> None:
    export_root, erratum_path, _ = _write_authority(tmp_path)
    pins = _synthetic_pins(export_root, erratum_path)
    prediction = export_root / "qwen-predictions.jsonl"
    if case == "missing":
        prediction.unlink()
    elif case == "changed":
        prediction.write_bytes(b'{"synthetic":"changed"}\n')
    elif case == "unexpected":
        (export_root / "unexpected.txt").write_text("unexpected", encoding="utf-8")
    else:
        target = tmp_path / "redirect-target.jsonl"
        target.write_bytes(prediction.read_bytes())
        prediction.unlink()
        try:
            prediction.symlink_to(target)
        except OSError as exc:
            pytest.skip(f"file symlink creation is unavailable: {exc}")

    with pytest.raises(ReportingAuthorityError):
        _load_reporting_authority(export_root, erratum_path, pins)


def test_reporting_authority_binds_materialization_environment(tmp_path: Path):
    export_root, erratum_path, _ = _write_authority(tmp_path)
    receipt_path = export_root / "execution-materialization-receipt.json"
    receipt = json.loads(receipt_path.read_bytes())
    receipt["runtime_import_roots"] = ["C:/wrong/site-packages"]
    export_root = _replace_member_and_rebind(
        export_root,
        erratum_path,
        "execution-materialization-receipt.json",
        receipt,
    )

    with pytest.raises(ReportingAuthorityError, match="runtime import roots"):
        _load_synthetic(export_root, erratum_path)


@pytest.mark.parametrize(
    "case",
    [
        "tampered-result",
        "duplicate-key",
        "absent-erratum",
        "wrong-manifest-link",
        "wrong-source-link",
        "reserialized-result",
    ],
)
def test_reporting_authority_fails_closed(tmp_path: Path, case: str):
    export_root, erratum_path, _ = _write_authority(tmp_path)
    pins = _synthetic_pins(export_root, erratum_path)

    if case == "tampered-result":
        (export_root / "results.json").write_bytes(b"{}\n")
    elif case == "duplicate-key":
        duplicate = b'{"schema_version":"a","schema_version":"b"}\n'
        (export_root / "results.json").write_bytes(duplicate)
        manifest = json.loads((export_root / "evidence-manifest.json").read_bytes())
        next(item for item in manifest["artifacts"] if item["name"] == "results.json")[
            "sha256"
        ] = _sha256(duplicate)
        manifest_bytes = _json_bytes(manifest)
        (export_root / "evidence-manifest.json").write_bytes(manifest_bytes)
        erratum_path.write_bytes(_json_bytes(_erratum_payload(_sha256(manifest_bytes))))
    elif case == "absent-erratum":
        erratum_path.unlink()
    elif case == "wrong-manifest-link":
        erratum_path.write_bytes(_json_bytes(_erratum_payload("f" * 64)))
    elif case == "wrong-source-link":
        receipt_path = export_root / "execution-materialization-receipt.json"
        receipt = json.loads(receipt_path.read_bytes())
        receipt["source_manifest_sha256"] = "f" * 64
        receipt_bytes = _json_bytes(receipt)
        receipt_path.write_bytes(receipt_bytes)
        manifest = json.loads((export_root / "evidence-manifest.json").read_bytes())
        next(
            item
            for item in manifest["artifacts"]
            if item["name"] == "execution-materialization-receipt.json"
        )["sha256"] = _sha256(receipt_bytes)
        manifest_bytes = _json_bytes(manifest)
        (export_root / "evidence-manifest.json").write_bytes(manifest_bytes)
        erratum_path.write_bytes(_json_bytes(_erratum_payload(_sha256(manifest_bytes))))
    else:
        result_path = export_root / "results.json"
        result_path.write_text(
            json.dumps(json.loads(result_path.read_bytes()), indent=2),
            encoding="utf-8",
        )

    with pytest.raises(ReportingAuthorityError):
        _load_reporting_authority(export_root, erratum_path, pins)


def test_public_reporting_loader_rejects_self_signed_bundle(tmp_path: Path) -> None:
    export_root, erratum_path, _ = _write_authority(tmp_path)
    with pytest.raises(ReportingAuthorityError, match="canonical reporting authority"):
        load_reporting_authority(export_root, erratum_path)
