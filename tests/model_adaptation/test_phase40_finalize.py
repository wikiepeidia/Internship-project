"""Tests for the narrow Phase 40 comparison-finalizer entrypoint."""

from __future__ import annotations

import inspect
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.model_adaptation import phase40_finalize as finalizer
from src.model_adaptation.phase40_handoff import finalize_phase40_final_comparison


def _arguments(repo: Path) -> list[str]:
    return [
        "--repo-root",
        str(repo),
        "--output-root",
        "data/models/phase40",
        "--bundle-root",
        "phase40-qwen-qlora-full-seed42-v1=data/models/phase40/full/qwen-qlora",
        "--bundle-root",
        "phase40-phobert-full-seed42-v12=data/models/phase40/full/phobert",
        "--gpu-identity",
        "phase40-qwen-qlora-full-seed42-v1=NVIDIA GeForce RTX 5050 Laptop GPU",
        "--gpu-identity",
        "phase40-phobert-full-seed42-v12=NVIDIA GeForce RTX 5050 Laptop GPU",
    ]


def test_narrow_entrypoint_consumes_capability_before_finalizing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls: dict[str, object] = {"events": []}

    def consume(**kwargs):
        calls["events"].append("consume")
        calls["consume"] = kwargs

    def run(args):
        calls["events"].append("finalize")
        calls["args"] = args
        return SimpleNamespace(
            manifest=SimpleNamespace(status="complete"),
            manifest_path=Path("comparison-manifest.json"),
            report_path=Path("comparison-report.md"),
        )

    monkeypatch.setattr(
        finalizer,
        "consume_phase40_comparison_launch_capability",
        consume,
    )
    monkeypatch.setattr(finalizer, "_run_finalizer", run)
    assert finalizer.main(_arguments(tmp_path)) == 0
    assert calls["events"] == ["consume", "finalize"]
    assert calls["consume"] == {
        "repo_root": Path.cwd(),
        "argv": _arguments(tmp_path),
    }
    assert calls["args"].bundle_root == [
        "phase40-qwen-qlora-full-seed42-v1=data/models/phase40/full/qwen-qlora",
        "phase40-phobert-full-seed42-v12=data/models/phase40/full/phobert",
    ]
    assert "comparison complete" in capsys.readouterr().out


def test_narrow_entrypoint_does_not_finalize_when_capability_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def reject(**_kwargs):
        raise RuntimeError("requires a fresh launcher capability")

    monkeypatch.setattr(
        finalizer,
        "consume_phase40_comparison_launch_capability",
        reject,
    )
    monkeypatch.setattr(
        finalizer,
        "_run_finalizer",
        lambda _args: pytest.fail("finalizer ran without a capability"),
    )
    with pytest.raises(RuntimeError, match="fresh launcher capability"):
        finalizer.main(_arguments(tmp_path))


def test_parser_exposes_no_request_scope_or_external_authority_path_flags() -> None:
    options = {
        option
        for action in finalizer.build_parser()._actions
        for option in action.option_strings
    }
    assert "--request-path" not in options
    assert "--scope-amendment-path" not in options
    assert "--qwen-export-root" not in options
    assert "--phobert-transfer-root" not in options
    assert "production_authorities" not in inspect.signature(
        finalize_phase40_final_comparison
    ).parameters
    assert not hasattr(finalizer, "finalize_phase40_final_comparison")


def test_assignment_requires_one_nonempty_run_id_and_value() -> None:
    with pytest.raises(Exception, match="RUN_ID=VALUE"):
        finalizer._bundle_root("missing-separator")
    with pytest.raises(Exception, match="edge whitespace"):
        finalizer._gpu_identity("run= gpu")
