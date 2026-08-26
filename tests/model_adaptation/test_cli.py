"""Wave 0 CLI tests for the Phase 3 operator tooling."""

from __future__ import annotations

import argparse
import importlib
import inspect
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.model_adaptation.registry import save_model_registry
from src.model_adaptation.schemas import (
    ModelRegistry,
    PilotSelection,
)


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


def test_cli_exposes_pilot_and_train_commands():
    cli_module = _load_cli_module()
    parser = cli_module.build_parser()

    subparsers_action = next(
        action for action in parser._actions if isinstance(action, argparse._SubParsersAction)
    )

    assert sorted(subparsers_action.choices.keys()) == [
        "convert",
        "doctor",
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
        "phase41-authorize-evaluation",
        "phase41-export-evidence",
        "phase41-freeze-deployment-fit-disposition",
        "phase41-prepare-evaluation",
        "phase41-run-once",
        "phase41-verify-evidence",
        "phase41-verify-preauthorization",
        "pilot",
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


def test_phase40_human_review_cli_passes_exact_reviewer_return_bytes(
    tmp_path, monkeypatch, capsys
):
    cli_module = _load_cli_module()
    reviewer_return_path = (
        tmp_path / "data/models/phase40/review/reviewer-return.jsonl"
    )
    reviewer_return_path.parent.mkdir(parents=True)
    original_bytes = b'  {"assessment":"ambiguous"}\r\n'
    reviewer_return_path.write_bytes(original_bytes)
    sentinels = tuple(object() for _ in range(5))
    queue_bytes = b'{"model_run_id":"qwen-qlora"}\n'
    sentinel_reviews = (object(),)
    captured = {}

    monkeypatch.setattr(
        cli_module,
        "_load_phase40_review_authorities",
        lambda args: (*sentinels, queue_bytes),
    )
    monkeypatch.setattr(
        cli_module,
        "_load_jsonl_models_from_bytes",
        lambda payload, path, model_type, **kwargs: sentinel_reviews,
    )

    def fake_finalize(queue, reviews, **kwargs):
        captured["queue"] = queue
        captured["reviews"] = reviews
        captured.update(kwargs)
        return SimpleNamespace(
            notes_path=tmp_path / "human-review-notes.jsonl",
            report_path=tmp_path / "human-review-report.md",
        )

    monkeypatch.setattr(cli_module, "finalize_phase40_human_review", fake_finalize)
    args = SimpleNamespace(
        reviewer_return_path=reviewer_return_path,
        repo_root=tmp_path,
        queue_manifest_path=tmp_path / "queue-manifest.json",
        comparison_manifest_path=tmp_path / "comparison.json",
        scope_amendment_path=tmp_path / "scope-amendment.json",
        output_root=tmp_path / "out",
        vietnamese_fluent_attestation=True,
        verify_only=False,
    )

    assert cli_module.handle_phase40_finalize_human_review(args) == 0
    assert captured["queue"] is sentinels[4]
    assert captured["reviews"] is sentinel_reviews
    assert captured["queue_bytes"] == queue_bytes
    assert captured["reviewer_return_bytes"] == original_bytes
    output = capsys.readouterr().out
    assert str(tmp_path) not in output
    assert "notes=data/models/phase40/review/human-review-notes.jsonl" in output
    assert "report=data/models/phase40/review/human-review-report.md" in output


def test_phase40_human_review_cli_sanitizes_unreadable_reviewer_input(
    tmp_path, monkeypatch
):
    cli_module = _load_cli_module()
    reviewer_return_path = (
        tmp_path / "data/models/phase40/review/reviewer-return.jsonl"
    )
    reviewer_return_path.mkdir(parents=True)
    sentinels = tuple(object() for _ in range(5))
    monkeypatch.setattr(
        cli_module,
        "_load_phase40_review_authorities",
        lambda args: (*sentinels, b"{}\n"),
    )
    args = SimpleNamespace(
        reviewer_return_path=reviewer_return_path,
        repo_root=tmp_path,
        queue_manifest_path=tmp_path / "queue-manifest.json",
        comparison_manifest_path=tmp_path / "comparison.json",
        scope_amendment_path=tmp_path / "scope-amendment.json",
        output_root=tmp_path / "out",
        vietnamese_fluent_attestation=True,
        verify_only=False,
    )

    with pytest.raises(ValueError) as exc_info:
        cli_module.handle_phase40_finalize_human_review(args)

    assert str(exc_info.value) == "reviewer return is missing, unreadable, or unsafe"
    assert str(tmp_path) not in str(exc_info.value)


def test_phase40_human_review_cli_hides_path_for_malformed_reviewer_input(
    tmp_path, monkeypatch
):
    cli_module = _load_cli_module()
    reviewer_return_path = (
        tmp_path / "data/models/phase40/review/reviewer-return.jsonl"
    )
    reviewer_return_path.parent.mkdir(parents=True)
    reviewer_return_path.write_bytes(b"{not-json}\n")
    sentinels = tuple(object() for _ in range(5))
    monkeypatch.setattr(
        cli_module,
        "_load_phase40_review_authorities",
        lambda args: (*sentinels, b"{}\n"),
    )
    args = SimpleNamespace(
        reviewer_return_path=reviewer_return_path,
        repo_root=tmp_path,
        queue_manifest_path=tmp_path / "queue-manifest.json",
        comparison_manifest_path=tmp_path / "comparison.json",
        scope_amendment_path=tmp_path / "scope-amendment.json",
        output_root=tmp_path / "out",
        vietnamese_fluent_attestation=True,
        verify_only=False,
    )

    with pytest.raises(ValueError) as exc_info:
        cli_module.handle_phase40_finalize_human_review(args)

    assert str(exc_info.value) == "invalid JSONL row 0: reviewer return"
    assert str(tmp_path) not in str(exc_info.value)


def test_phase40_v3_review_loader_uses_frozen_upstream_authority(
    tmp_path, monkeypatch
):
    cli_module = _load_cli_module()
    request = SimpleNamespace(
        input_bundle=SimpleNamespace(repository_relative_path="phase40-input.zip")
    )
    contract = object()
    comparison = SimpleNamespace(schema_version="phase40-comparison-v3")
    final = object()
    bundles = (object(),)
    queue = (object(),)
    queue_path = tmp_path / "data/models/phase40/review/review-queue.jsonl"
    queue_path.parent.mkdir(parents=True)
    queue_bytes = b'{"model_run_id":"qwen-qlora"}\n'
    queue_path.write_bytes(queue_bytes)
    selected_path = (
        tmp_path / "data/models/phase40/selected-prediction-bundles.json"
    )
    selected_path.parent.mkdir(parents=True, exist_ok=True)
    selected_path.write_text("[]\n", encoding="utf-8")
    comparison_path = tmp_path / "data/models/phase40/comparison-manifest.json"
    comparison_path.write_text("{}\n", encoding="utf-8")
    calls: list[str] = []

    monkeypatch.setattr(
        cli_module,
        "load_frozen_phase40_run_request",
        lambda **kwargs: request,
    )
    monkeypatch.setattr(
        cli_module,
        "verify_phase40_input_bundle",
        lambda *args, **kwargs: contract,
    )
    monkeypatch.setattr(
        cli_module,
        "load_canonical_phase40_comparison_manifest",
        lambda **kwargs: (comparison, b"{}\n"),
    )
    monkeypatch.setattr(
        cli_module,
        "load_frozen_phase40_scope_amendment",
        lambda **kwargs: (_ for _ in ()).throw(
            AssertionError("v3 review reactivated the legacy amendment")
        ),
    )

    def load_review_authority(**kwargs):
        calls.append("final-authority")
        assert kwargs["request"] is request
        return final, b"historical-scope\n"

    def verify_review_comparison(value, **kwargs):
        calls.append("comparison")
        assert value is comparison
        assert kwargs["final_authority"] is final

    monkeypatch.setattr(
        cli_module, "load_phase40_review_authority", load_review_authority
    )
    monkeypatch.setattr(
        cli_module,
        "verify_phase40_final_review_comparison",
        verify_review_comparison,
    )
    monkeypatch.setattr(
        cli_module,
        "load_phase40_selected_prediction_bundles",
        lambda *args, **kwargs: bundles,
    )
    monkeypatch.setattr(
        cli_module,
        "_load_jsonl_models_from_bytes",
        lambda *args, **kwargs: queue,
    )
    monkeypatch.setattr(
        cli_module,
        "verify_phase40_review_queue",
        lambda rows, **kwargs: calls.append("queue"),
    )
    args = SimpleNamespace(
        repo_root=tmp_path,
        request_path=tmp_path / "request.json",
        scope_amendment_path=tmp_path / "scope.json",
        comparison_manifest_path=comparison_path,
        selected_predictions_path=selected_path,
        queue_path=queue_path,
    )

    loaded = cli_module._load_phase40_review_authorities(args)

    assert loaded == (request, contract, comparison, bundles, queue, queue_bytes)
    assert calls == ["final-authority", "comparison", "queue"]


@pytest.mark.parametrize("malformation", ("duplicate", "noncanonical", "partial"))
def test_phase40_verify_review_queue_rejects_ambiguous_comparison_bytes(
    tmp_path, monkeypatch, malformation, capsys
):
    cli_module = _load_cli_module()
    source_repo = Path(__file__).resolve().parents[2]
    repo = tmp_path / "repo"
    comparison_path = repo / "data/models/phase40/comparison-manifest.json"
    comparison_path.parent.mkdir(parents=True)
    original = (
        source_repo / "data/models/phase40/comparison-manifest.json"
    ).read_bytes()
    if malformation == "duplicate":
        payload = original.replace(
            b"{",
            b'{"schema_version":"phase40-comparison-v3",',
            1,
        )
    elif malformation == "noncanonical":
        payload = b" " + original
    else:
        payload = original[:-1]
    comparison_path.write_bytes(payload)

    request = SimpleNamespace(
        input_bundle=SimpleNamespace(repository_relative_path="phase40-input.zip")
    )
    monkeypatch.setattr(
        cli_module,
        "load_frozen_phase40_run_request",
        lambda **kwargs: request,
    )
    monkeypatch.setattr(
        cli_module,
        "verify_phase40_input_bundle",
        lambda *args, **kwargs: object(),
    )
    monkeypatch.setattr(
        cli_module,
        "load_phase40_review_authority",
        lambda **kwargs: (_ for _ in ()).throw(
            AssertionError("ambiguous comparison reached authority verification")
        ),
    )
    exit_code = cli_module.main(
        [
            "phase40-verify-review-queue",
            "--repo-root",
            str(repo),
            "--request-path",
            str(repo / "request.json"),
            "--scope-amendment-path",
            str(repo / "scope.json"),
            "--comparison-manifest-path",
            str(comparison_path),
            "--selected-predictions-path",
            str(repo / "predictions.json"),
            "--queue-path",
            str(repo / "queue.jsonl"),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "review queue verified" not in captured.out


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


def test_cli_removes_all_legacy_public_evaluation_commands():
    cli_module = _load_cli_module()
    parser = cli_module.build_parser()

    subparsers_action = next(
        action for action in parser._actions if isinstance(action, argparse._SubParsersAction)
    )

    legacy_commands = {
        "evaluate-release-split",
        "prepare-explanation-review",
        "release-eval",
    }
    assert legacy_commands.isdisjoint(subparsers_action.choices)
    assert not hasattr(cli_module, "handle_evaluate_release_split")
    assert not hasattr(cli_module, "evaluate_release_split")
    assert not hasattr(cli_module, "handle_prepare_explanation_review")
    assert not hasattr(cli_module, "handle_release_eval")


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


@pytest.mark.parametrize(
    ("command", "arguments"),
    [
        (
            "evaluate-release-split",
            ["--split-path", "synthetic-hardlink-or-reparse-alias.jsonl"],
        ),
        (
            "prepare-explanation-review",
            ["--snapshot-path", "synthetic-hardlink-or-reparse-alias.jsonl"],
        ),
        (
            "release-eval",
            ["--snapshot-path", "synthetic-hardlink-or-reparse-alias.jsonl"],
        ),
    ],
)
def test_legacy_evaluation_cli_routes_are_not_recognized(
    command: str, arguments: list[str]
):
    cli_module = _load_cli_module()
    with pytest.raises(SystemExit) as exc_info:
        cli_module.main([command, *arguments])

    assert exc_info.value.code == 2


def test_phase41_cli_surface_is_fixed_and_run_once_accepts_only_output_root():
    cli_module = _load_cli_module()
    parser = cli_module.build_parser()
    subparsers_action = next(
        action for action in parser._actions if isinstance(action, argparse._SubParsersAction)
    )
    expected = {
        "phase41-prepare-evaluation",
        "phase41-verify-preauthorization",
        "phase41-authorize-evaluation",
        "phase41-run-once",
        "phase41-freeze-deployment-fit-disposition",
        "phase41-verify-evidence",
    }
    assert expected <= set(subparsers_action.choices)
    run_parser = subparsers_action.choices["phase41-run-once"]
    option_strings = {
        option
        for action in run_parser._actions
        for option in action.option_strings
    }
    assert option_strings == {"-h", "--help", "--output-root"}
    forbidden = {"--split-path", "--model-path", "--registry-root", "--retry"}
    assert option_strings.isdisjoint(forbidden)
    handler_source = inspect.getsource(cli_module.handle_phase41_run_once)
    assert "load_phase41_production_predictors" not in handler_source
    assert "run_phase41_once(_phase41_output_root(args.output_root))" in handler_source

    prepare_parser = subparsers_action.choices["phase41-prepare-evaluation"]
    prepare_options = {
        option
        for action in prepare_parser._actions
        for option in action.option_strings
    }
    assert "--deployment-fit-choice" not in prepare_options

    authorize_parser = subparsers_action.choices["phase41-authorize-evaluation"]
    authorize_options = {
        option
        for action in authorize_parser._actions
        for option in action.option_strings
    }
    assert authorize_options == {
        "-h",
        "--help",
        "--output-root",
        "--prepared-sha256",
        "--statement",
    }

    disposition_parser = subparsers_action.choices[
        "phase41-freeze-deployment-fit-disposition"
    ]
    disposition_options = {
        option
        for action in disposition_parser._actions
        for option in action.option_strings
    }
    assert disposition_options == {"-h", "--help", "--output-root"}
    assert "--choice" not in disposition_options


def test_phase41_prepare_cli_defers_deployment_fit_choice_to_authorization():
    parser = _load_cli_module().build_parser()
    required_authorities = [
        "--phase39-contract-path",
        "phase39-contract.json",
        "--phase40-comparison-manifest-path",
        "phase40-comparison.json",
        "--phase40-review-manifest-path",
        "phase40-review.json",
    ]

    args = parser.parse_args(["phase41-prepare-evaluation", *required_authorities])
    assert not hasattr(args, "deployment_fit_choice")
    assert args.output_root is None
    assert args.preclaim_rejection_audit_path.name == "41-02-preclaim-failure.json"
    assert (
        args.staged_preclaim_failure_audit_path.name
        == "claim-capable-preclaim-failure.json"
    )
    assert (
        args.argument_preclaim_failure_audit_path.name
        == "claim-capable-preclaim-failure.json"
    )
    assert args.autonomous_reseal_delegation_path.name == (
        "autonomous-reseal-delegation.json"
    )
    assert (
        args.captured_helper_preclaim_failure_audit_path.name
        == "claim-capable-preclaim-failure.json"
    )

    with pytest.raises(SystemExit):
        parser.parse_args(
            [
                "phase41-prepare-evaluation",
                *required_authorities,
                "--deployment-fit-choice",
                "deferred",
            ]
        )


@pytest.mark.parametrize(
    "statement",
    (
        "AUTHORIZE PHASE 41 ONE-SHOT; DEPLOYMENT FIT DEFERRED",
        "AUTHORIZE PHASE 41 ONE-SHOT; SEPARATE DEPLOYMENT FIT AUTHORIZED",
    ),
)
def test_phase41_authorize_cli_accepts_exact_signal_as_sole_fit_choice(
    statement: str,
):
    parser = _load_cli_module().build_parser()
    base = [
        "phase41-authorize-evaluation",
        "--prepared-sha256",
        "a" * 64,
        "--statement",
        statement,
    ]

    args = parser.parse_args(base)
    assert args.statement == statement
    assert not hasattr(args, "deployment_fit_choice")
    with pytest.raises(SystemExit):
        parser.parse_args([*base, "--deployment-fit-choice", "deferred"])


def test_phase41_authorize_handler_forwards_only_exact_signal(monkeypatch):
    cli_module = _load_cli_module()
    import src.model_adaptation.phase41_evaluation as evaluation_module

    captured: dict[str, object] = {}

    def fake_authorize(output_root, **kwargs):
        captured["output_root"] = output_root
        captured.update(kwargs)
        return Path("synthetic-one-shot-authorization.json")

    monkeypatch.setattr(
        evaluation_module, "authorize_phase41_evaluation", fake_authorize
    )
    signal = "AUTHORIZE PHASE 41 ONE-SHOT; DEPLOYMENT FIT DEFERRED"
    args = SimpleNamespace(
        output_root=Path("synthetic-output"),
        prepared_sha256="a" * 64,
        statement=signal,
    )

    assert cli_module.handle_phase41_authorize_evaluation(args) == 0
    assert captured == {
        "output_root": Path("synthetic-output"),
        "prepared_sha256": "a" * 64,
        "statement": signal,
    }


def test_phase41_prepare_handler_does_not_invent_deployment_fit_precommit(monkeypatch):
    cli_module = _load_cli_module()
    import src.model_adaptation.phase41_evaluation as evaluation_module

    captured: dict[str, object] = {}

    def fake_prepare(output_root, **kwargs):
        captured["output_root"] = output_root
        captured.update(kwargs)
        return SimpleNamespace(
            path=Path("synthetic-prepared-request.json"),
            prepared_sha256="a" * 64,
        )

    monkeypatch.setattr(
        evaluation_module, "prepare_phase41_from_canonical_authorities", fake_prepare
    )
    args = SimpleNamespace(
        output_root=Path("synthetic-output"),
        repo_root=Path("synthetic-repository"),
        phase39_contract_path=Path("phase39-contract.json"),
        phase40_comparison_manifest_path=Path("phase40-comparison.json"),
        phase40_review_manifest_path=Path("phase40-review.json"),
    )

    assert cli_module.handle_phase41_prepare_evaluation(args) == 0
    assert "deployment_fit_choice" not in captured


def test_phase41_disposition_handler_cannot_supply_post_result_choice(monkeypatch):
    cli_module = _load_cli_module()
    import src.model_adaptation.phase41_evaluation as evaluation_module

    captured: list[Path] = []

    def fake_freeze(output_root):
        captured.append(output_root)
        return Path("synthetic-deployment-fit-disposition.json")

    monkeypatch.setattr(
        evaluation_module, "freeze_deployment_fit_disposition", fake_freeze
    )
    args = SimpleNamespace(output_root=Path("synthetic-output"))

    assert cli_module.handle_phase41_freeze_deployment_fit_disposition(args) == 0
    assert captured == [Path("synthetic-output")]


class _StrictLegacyConsole:
    encoding = "cp1252"

    def __init__(self) -> None:
        self.text = ""

    def write(self, value: str) -> int:
        value.encode(self.encoding, errors="strict")
        self.text += value
        return len(value)

    def flush(self) -> None:
        return None


def test_phase41_export_cli_returns_success_on_legacy_console_after_real_temp_export(
    tmp_path, monkeypatch
):
    cli_module = _load_cli_module()
    import src.model_adaptation.phase41_evaluation as evaluation_module

    operational = tmp_path / "operational"
    repository_output = (
        tmp_path / "bai-tap-tập" / "data" / "models" / "phase41"
    )
    operational.mkdir()
    export_names = (
        *evaluation_module.EVIDENCE_ARTIFACT_NAMES,
        evaluation_module.EVIDENCE_MANIFEST_NAME,
        evaluation_module.COMPLETION_SEAL_NAME,
        evaluation_module.TERMINAL_NAME,
        evaluation_module.DEPLOYMENT_DISPOSITION_NAME,
    )
    for name in export_names:
        (operational / name).write_bytes(f"{name}\n".encode())
    (operational / evaluation_module.PREPARED_NAME).write_bytes(
        evaluation_module._canonical_json_bytes(
            {"preparation_scope": evaluation_module.SYNTHETIC_PREPARATION_SCOPE}
        )
    )
    manifest_sha = "c" * 64
    monkeypatch.setattr(
        evaluation_module,
        "verify_phase41_evidence",
        lambda root: SimpleNamespace(evidence_manifest_sha256=manifest_sha),
    )
    monkeypatch.setattr(
        evaluation_module,
        "_code_fixed_authority_path",
        lambda repo_root, supplied, expected_relative, description: repository_output,
    )
    console = _StrictLegacyConsole()
    monkeypatch.setattr(cli_module.sys, "stdout", console)

    exit_code = cli_module.main(
        [
            "phase41-export-evidence",
            "--output-root",
            str(operational),
            "--repository-output-root",
            str(repository_output),
        ]
    )

    receipt = (
        repository_output
        / "verified-export"
        / manifest_sha
        / evaluation_module.EXPORT_RECEIPT_NAME
    )
    parsed, _ = evaluation_module._load_canonical_json(
        receipt, "temporary export receipt"
    )
    assert exit_code == 0
    assert parsed["evidence_manifest_sha256"] == manifest_sha
    assert "\\u1eadp" in console.text


def test_phase41_export_cli_error_is_safe_on_legacy_console(tmp_path, monkeypatch):
    cli_module = _load_cli_module()
    import src.model_adaptation.phase41_evaluation as evaluation_module

    def fail_export(*_args, **_kwargs):
        raise evaluation_module.ContractError("không thể xuất vào thư mục tập")

    monkeypatch.setattr(
        evaluation_module, "export_phase41_evidence_to_repository", fail_export
    )
    console = _StrictLegacyConsole()
    monkeypatch.setattr(cli_module.sys, "stderr", console)

    exit_code = cli_module.main(
        [
            "phase41-export-evidence",
            "--output-root",
            str(tmp_path / "operational"),
            "--repository-output-root",
            str(tmp_path / "repository"),
        ]
    )

    assert exit_code == 1
    assert "\\u1eadp" in console.text
