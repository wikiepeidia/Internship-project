"""Wave 0 CLI tests for the Phase 3 operator tooling."""

from __future__ import annotations

import argparse
import importlib
from pathlib import Path
from types import SimpleNamespace

from src.model_adaptation.registry import save_model_registry
from src.model_adaptation.schemas import (
    ExplanationReviewItem,
    ExplanationReviewPack,
    LOCKED_RELEASE_LABELS,
    HeldOutSupportAudit,
    ModelRegistry,
    OverallMetricSummary,
    PerLabelMetricRow,
    PilotSelection,
    ReleaseEvaluationRow,
    ReleaseEvaluationSnapshot,
)
from src.runtime.contracts import SuspiciousCue


def _load_cli_module():
    return importlib.import_module("src.model_adaptation.cli")


def _write_registry(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    registry = ModelRegistry(
        version_tag="phase3-smoke",
        selection=PilotSelection(
            baseline_winner_id="qwen3-4b-instruct-2507",
            runner_up_id="qwen3.5-4b",
            selection_notes="Pilot winner and runner-up for CLI tests.",
        ),
    )
    save_model_registry(registry, path)


def _write_snapshot(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    audit = HeldOutSupportAudit(
        evaluated_split_path=Path("data/splits/val.jsonl"),
        support_by_label={label: 1 for label in LOCKED_RELEASE_LABELS},
        blocker_reasons=[],
    )
    snapshot = ReleaseEvaluationSnapshot(
        run_id="phase5-run-001",
        evaluated_split_path=Path("data/splits/val.jsonl"),
        audit=audit,
        overall_metrics=OverallMetricSummary(macro_f1=0.8, weighted_f1=0.9, evaluated_rows=1),
        per_label_metrics=[
            PerLabelMetricRow(label=label, precision=1.0, recall=1.0, f1=1.0, support=1)
            for label in LOCKED_RELEASE_LABELS
        ],
        rows=[
            ReleaseEvaluationRow(
                gold_label="bank_impersonation",
                predicted_labels=["bank_impersonation"],
                risk_tier="high-risk",
                summary="Tin nhan gia danh ngan hang va yeu cau OTP.",
                top_cues=[SuspiciousCue(span="OTP", reason="Tin nhan nhac ma OTP", cue_type="otp_request")],
                recommendations=["Khong chia se OTP cho nguoi gui tin nhan."],
                backend_name="fake-runtime",
                split_provenance="data/splits/val.jsonl",
                reviewable_source_text="VPBank yeu cau OTP de xac minh giao dich.",
            )
        ],
    )
    path.write_text(snapshot.model_dump_json(indent=2), encoding="utf-8")


def _write_review_pack(path: Path, *, run_id: str = "phase5-run-001", review_completed: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pack = ExplanationReviewPack(
        run_id=run_id,
        source_snapshot_path=Path(".planning/phases/05-recall-priority-evaluation-and-release-gates/05-evaluation-snapshot.json"),
        items=[
            ExplanationReviewItem(
                row_index=0,
                gold_label="bank_impersonation",
                predicted_labels=["bank_impersonation"],
                risk_tier="high-risk",
                reviewable_text="VPBank yeu cau OTP de xac minh giao dich.",
                top_cues=[SuspiciousCue(span="OTP", reason="Tin nhan nhac ma OTP", cue_type="otp_request")],
                recommendations=["Khong chia se OTP cho nguoi gui tin nhan."],
                deterministic_blocker_reasons=[],
                deterministic_flag_reasons=[],
                reviewer_blocker_reasons=[],
                reviewer_flag_reasons=[],
            )
        ],
        review_completed=review_completed,
        review_notes="approved" if review_completed else None,
    )
    path.write_text(pack.model_dump_json(indent=2), encoding="utf-8")


def test_cli_exposes_pilot_and_train_commands():
    cli_module = _load_cli_module()
    parser = cli_module.build_parser()

    subparsers_action = next(
        action for action in parser._actions if isinstance(action, argparse._SubParsersAction)
    )

    assert sorted(subparsers_action.choices.keys()) == [
        "convert",
        "doctor",
        "evaluate-release-split",
        "phase40-build-input-bundle",
        "phase40-build-source-bundle",
        "phase40-finalize-comparison",
        "phase40-finalize-human-review",
        "phase40-freeze-scope-amendment",
        "phase40-preflight",
        "phase40-render-graphs",
        "phase40-validate-notebooks",
        "phase40-verify-input-bundle",
        "phase40-verify-review-queue",
        "phase40-verify-run-evidence",
        "phase40-verify-run-request",
        "pilot",
        "prepare-explanation-review",
        "release-eval",
        "train",
    ]


def test_documented_phase40_notebook_validation_command_succeeds():
    cli_module = _load_cli_module()
    root = Path(__file__).resolve().parents[2] / "notebooks" / "phase40"

    assert cli_module.main(["phase40-validate-notebooks", "--root", str(root)]) == 0


def test_phase40_probe_and_review_cli_controls_parse_without_latest_alias(tmp_path):
    cli_module = _load_cli_module()
    parser = cli_module.build_parser()
    probe = parser.parse_args(
        [
            "train",
            "--candidate",
            "baseline-winner",
            "--version-tag",
            "probe-v1",
            "--train-split",
            "data/splits/train.jsonl",
            "--val-split",
            "data/splits/val.jsonl",
            "--adaptation-mode",
            "qlora",
            "--run-kind",
            "probe",
            "--post-warmup-steps",
            "30",
            "--run-id",
            "qwen-qlora-probe-v1",
        ]
    )
    assert probe.post_warmup_steps == 30
    assert probe.warmup_steps == 5
    assert probe.run_kind == "probe"

    human = parser.parse_args(
        [
            "phase40-finalize-human-review",
            "--request-path",
            str(tmp_path / "request.json"),
            "--scope-amendment-path",
            str(tmp_path / "scope-amendment.json"),
            "--comparison-manifest-path",
            str(tmp_path / "comparison.json"),
            "--selected-predictions-path",
            str(tmp_path / "predictions.json"),
            "--queue-path",
            str(tmp_path / "queue.jsonl"),
            "--queue-manifest-path",
            str(tmp_path / "queue-manifest.json"),
            "--reviewer-return-path",
            str(tmp_path / "review.jsonl"),
            "--output-root",
            str(tmp_path / "out"),
            "--vietnamese-fluent-attestation",
        ]
    )
    assert human.vietnamese_fluent_attestation is True


def test_phase40_comparison_cli_builds_typed_operator_return(tmp_path, monkeypatch):
    cli_module = _load_cli_module()
    request_path = tmp_path / "request.json"
    request_path.write_text("{}", encoding="utf-8")
    sentinel_request = object()

    def fake_load_request(*, repo_root, request_path: Path):
        assert request_path == tmp_path / "request.json"
        return sentinel_request

    captured = {}

    def fake_finalize(request, operator_return, **kwargs):
        captured["request"] = request
        captured["operator_return"] = operator_return
        return SimpleNamespace(
            manifest=SimpleNamespace(status="complete"),
            manifest_path=tmp_path / "comparison-manifest.json",
            report_path=tmp_path / "comparison-report.md",
        )

    monkeypatch.setattr(cli_module, "load_frozen_phase40_run_request", fake_load_request)
    monkeypatch.setattr(cli_module, "finalize_phase40_comparison", fake_finalize)
    argv = [
        "phase40-finalize-comparison",
        "--request-path",
        str(request_path),
        "--output-root",
        str(tmp_path / "out"),
        "--scope-amendment-path",
        str(tmp_path / "scope-amendment.json"),
    ]
    for run_id, path in (
        ("qwen-qlora", "data/models/phase40/full/qwen-qlora"),
        ("phobert", "data/models/phase40/full/phobert"),
    ):
        argv.extend(("--bundle-root", f"{run_id}={path}"))
        argv.extend(("--gpu-identity", f"{run_id}=NVIDIA L4"))
    assert cli_module.main(argv) == 0
    assert captured["request"] is sentinel_request
    assert len(captured["operator_return"].bundle_roots) == 2
    assert captured["operator_return"].bundle_roots[0].run_id == "qwen-qlora"
    assert captured["operator_return"].package_decisions == ()


def test_cli_exposes_prepare_explanation_review_command():
    cli_module = _load_cli_module()
    parser = cli_module.build_parser()

    subparsers_action = next(
        action for action in parser._actions if isinstance(action, argparse._SubParsersAction)
    )

    assert "prepare-explanation-review" in subparsers_action.choices


def test_cli_exposes_evaluate_release_split_command():
    cli_module = _load_cli_module()
    parser = cli_module.build_parser()

    subparsers_action = next(
        action for action in parser._actions if isinstance(action, argparse._SubParsersAction)
    )

    assert "evaluate-release-split" in subparsers_action.choices


def test_default_split_path_prefers_retained_lineage_when_present(tmp_path, monkeypatch):
    cli_module = _load_cli_module()
    retained_root = tmp_path / "data" / "splits" / "recovered-balanced-claude-v2"
    retained_root.mkdir(parents=True)
    (retained_root / "train.jsonl").write_text("", encoding="utf-8")

    class FakeSettings:
        data_dir = tmp_path / "data"

    monkeypatch.setattr(cli_module, "get_settings", lambda: FakeSettings())

    assert cli_module._default_split_path("train") == retained_root / "train.jsonl"


def test_train_dry_run_uses_baseline_winner_and_runner_up_only(tmp_path, monkeypatch):
    cli_module = _load_cli_module()
    registry_path = tmp_path / "manifests" / "model-registry.json"
    _write_registry(registry_path)
    captured_candidates: list[str] = []

    def fake_build_training_config(**kwargs):
        captured_candidates.append(kwargs["candidate_id"])
        return SimpleNamespace(candidate_id=kwargs["candidate_id"], dry_run=kwargs["dry_run"])

    def fake_run_training(config, *, data_contract, selection=None):
        assert data_contract is sentinel_contract
        return {
            "dry_run": config.dry_run,
            "candidate_id": config.candidate_id,
            "train_examples": 2,
            "val_examples": 1,
        }

    monkeypatch.setattr(cli_module, "build_training_config", fake_build_training_config)
    monkeypatch.setattr(cli_module, "run_training", fake_run_training)
    sentinel_contract = object()
    monkeypatch.setattr(
        cli_module,
        "preflight_phase40_inputs",
        lambda train_path, val_path, *, repo_root: sentinel_contract,
    )

    baseline_exit = cli_module.main(
        [
            "train",
            "--adaptation-mode",
            "lora",
            "--candidate",
            "baseline-winner",
            "--version-tag",
            "phase3-smoke",
            "--train-split",
            str(tmp_path / "train.jsonl"),
            "--val-split",
            str(tmp_path / "val.jsonl"),
            "--registry-path",
            str(registry_path),
            "--dry-run",
        ]
    )
    runner_up_exit = cli_module.main(
        [
            "train",
            "--adaptation-mode",
            "lora",
            "--candidate",
            "runner-up",
            "--version-tag",
            "phase3-smoke",
            "--train-split",
            str(tmp_path / "train.jsonl"),
            "--val-split",
            str(tmp_path / "val.jsonl"),
            "--registry-path",
            str(registry_path),
            "--dry-run",
        ]
    )

    assert baseline_exit == 0
    assert runner_up_exit == 0
    assert captured_candidates == ["qwen3-4b-instruct-2507", "qwen3.5-4b"]


def test_train_command_returns_error_for_non_selected_candidate(tmp_path):
    cli_module = _load_cli_module()
    registry_path = tmp_path / "manifests" / "model-registry.json"
    _write_registry(registry_path)

    exit_code = cli_module.main(
        [
            "train",
            "--adaptation-mode",
            "lora",
            "--candidate",
            "qwen2.5-7b-instruct",
            "--version-tag",
            "phase3-smoke",
            "--train-split",
            str(tmp_path / "train.jsonl"),
            "--val-split",
            str(tmp_path / "val.jsonl"),
            "--registry-path",
            str(registry_path),
            "--dry-run",
        ]
    )

    assert exit_code == 1


def test_train_rejects_data_paths_before_registry_or_output_resolution(tmp_path, monkeypatch):
    cli_module = _load_cli_module()
    calls: list[str] = []

    def reject_preflight(train_path, val_path, *, repo_root):
        calls.append("preflight")
        raise ValueError("non-canonical fixture path")

    monkeypatch.setattr(cli_module, "preflight_phase40_inputs", reject_preflight)
    monkeypatch.setattr(
        cli_module,
        "_load_selection",
        lambda *_: (_ for _ in ()).throw(AssertionError("registry opened before preflight")),
    )
    exit_code = cli_module.main(
        [
            "train",
            "--adaptation-mode",
            "lora",
            "--candidate",
            "baseline-winner",
            "--version-tag",
            "fixture",
            "--train-split",
            str(tmp_path / "decoy-train.jsonl"),
            "--val-split",
            str(tmp_path / "decoy-val.jsonl"),
        ]
    )
    assert exit_code == 1
    assert calls == ["preflight"]


def test_doctor_command_formats_report_and_returns_success(monkeypatch, capsys):
    cli_module = _load_cli_module()

    monkeypatch.setattr(
        cli_module,
        "run_training_doctor",
        lambda **kwargs: SimpleNamespace(ready=True),
    )
    monkeypatch.setattr(cli_module, "format_training_doctor_report", lambda status: "TRAIN READY")

    exit_code = cli_module.main(
        ["doctor", "--candidate", "baseline-winner", "--adaptation-mode", "lora"]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "TRAIN READY" in captured.out


def test_convert_command_resolves_baseline_winner_alias(tmp_path, monkeypatch, capsys):
    cli_module = _load_cli_module()
    registry_path = tmp_path / "manifests" / "model-registry.json"
    _write_registry(registry_path)
    captured: dict[str, object] = {}

    def fake_build_gguf_request(candidate_id, version_tag, **kwargs):
        captured["candidate_id"] = candidate_id
        captured["version_tag"] = version_tag
        return SimpleNamespace(candidate_id=candidate_id, profile_name="gguf-laptop", output_path=tmp_path / "artifact.gguf")

    def fake_convert_to_gguf(request, **kwargs):
        artifact_record = SimpleNamespace(
            candidate_id=request.candidate_id,
            profile_name=request.profile_name,
            local_path=request.output_path,
        )
        return {"dry_run": True, "artifact_record": artifact_record}

    monkeypatch.setattr(cli_module, "build_gguf_request", fake_build_gguf_request)
    monkeypatch.setattr(cli_module, "convert_to_gguf", fake_convert_to_gguf)

    exit_code = cli_module.main(
        [
            "convert",
            "--candidate",
            "baseline-winner",
            "--version-tag",
            "phase3-gguf",
            "--registry-path",
            str(registry_path),
            "--dry-run",
        ]
    )
    captured_output = capsys.readouterr()

    assert exit_code == 0
    assert captured["candidate_id"] == "qwen3-4b-instruct-2507"
    assert captured["version_tag"] == "phase3-gguf"
    assert "Conversion dry-run complete" in captured_output.out


def test_prepare_explanation_review_command_prints_saved_pack_path(tmp_path, capsys):
    cli_module = _load_cli_module()
    snapshot_path = tmp_path / "05-evaluation-snapshot.json"
    output_path = tmp_path / "05-explanation-review-pack.json"
    _write_snapshot(snapshot_path)

    exit_code = cli_module.main(
        [
            "prepare-explanation-review",
            "--snapshot-path",
            str(snapshot_path),
            "--output-path",
            str(output_path),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert str(output_path) in captured.out


def test_evaluate_release_split_command_prints_progress_and_snapshot_path(tmp_path, monkeypatch, capsys):
    cli_module = _load_cli_module()
    split_path = tmp_path / "recovered-balanced-val.jsonl"
    split_path.write_text("", encoding="utf-8")
    snapshot_path = tmp_path / "05-evaluation-snapshot.json"
    _write_snapshot(snapshot_path)
    snapshot = ReleaseEvaluationSnapshot.model_validate_json(snapshot_path.read_text(encoding="utf-8"))
    captured: dict[str, object] = {}

    def fake_evaluate_release_split(split_path_arg, **kwargs):
        captured["split_path"] = split_path_arg
        captured["snapshot_path"] = kwargs["snapshot_path"]
        captured["run_id"] = kwargs["run_id"]
        captured["checkpoint_interval"] = kwargs["checkpoint_interval"]
        progress_callback = kwargs.get("progress_callback")
        if progress_callback is not None:
            progress_callback(1, 3)
            progress_callback(3, 3)
        return snapshot.model_copy(update={"evaluated_split_path": split_path_arg, "run_id": kwargs["run_id"]})

    monkeypatch.setattr(cli_module, "evaluate_release_split", fake_evaluate_release_split)

    exit_code = cli_module.main(
        [
            "evaluate-release-split",
            "--split-path",
            str(split_path),
            "--snapshot-path",
            str(snapshot_path),
            "--run-id",
            "phase5-run-123",
            "--progress-every",
            "1",
            "--checkpoint-every",
            "2",
        ]
    )
    captured_output = capsys.readouterr()

    assert exit_code == 0
    assert captured["split_path"] == split_path
    assert captured["snapshot_path"] == snapshot_path
    assert captured["run_id"] == "phase5-run-123"
    assert captured["checkpoint_interval"] == 2
    assert "Phase 5 evaluation progress: 1/3" in captured_output.out
    assert "Phase 5 evaluation progress: 3/3" in captured_output.out
    assert "Evaluation snapshot ready:" in captured_output.out
    assert str(snapshot_path) in captured_output.out


def test_cli_exposes_release_eval_command():
    cli_module = _load_cli_module()
    parser = cli_module.build_parser()

    subparsers_action = next(
        action for action in parser._actions if isinstance(action, argparse._SubParsersAction)
    )

    assert "release-eval" in subparsers_action.choices


def test_release_eval_command_prints_verdict_and_artifact_paths(tmp_path, capsys):
    cli_module = _load_cli_module()
    snapshot_path = tmp_path / "05-evaluation-snapshot.json"
    review_pack_path = tmp_path / "05-explanation-review-pack.json"
    report_dir = tmp_path / "phase"
    manifest_dir = tmp_path / "manifests"
    _write_snapshot(snapshot_path)
    _write_review_pack(review_pack_path)

    exit_code = cli_module.main(
        [
            "release-eval",
            "--snapshot-path",
            str(snapshot_path),
            "--review-pack-path",
            str(review_pack_path),
            "--report-dir",
            str(report_dir),
            "--manifest-dir",
            str(manifest_dir),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "verdict=" in captured.out
    assert str(report_dir) in captured.out
    assert str(manifest_dir) in captured.out


    def test_release_eval_command_rejects_incomplete_or_mismatched_review_pack(tmp_path):
        cli_module = _load_cli_module()
        snapshot_path = tmp_path / "05-evaluation-snapshot.json"
        incomplete_review_pack_path = tmp_path / "05-explanation-review-pack-incomplete.json"
        mismatched_review_pack_path = tmp_path / "05-explanation-review-pack-mismatch.json"
        _write_snapshot(snapshot_path)
        _write_review_pack(incomplete_review_pack_path, review_completed=False)
        _write_review_pack(mismatched_review_pack_path, run_id="phase5-run-999")

        with pytest.raises(ValueError, match="incomplete"):
            cli_module.main(
                [
                    "release-eval",
                    "--snapshot-path",
                    str(snapshot_path),
                    "--review-pack-path",
                    str(incomplete_review_pack_path),
                    "--report-dir",
                    str(tmp_path / "phase"),
                    "--manifest-dir",
                    str(tmp_path / "manifests"),
                ]
            )

        with pytest.raises(ValueError, match="run_id"):
            cli_module.main(
                [
                    "release-eval",
                    "--snapshot-path",
                    str(snapshot_path),
                    "--review-pack-path",
                    str(mismatched_review_pack_path),
                    "--report-dir",
                    str(tmp_path / "phase"),
                    "--manifest-dir",
                    str(tmp_path / "manifests"),
                ]
            )
