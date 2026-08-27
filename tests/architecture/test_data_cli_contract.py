"""Synthetic parser and workflow-boundary contracts for the data CLI."""

from __future__ import annotations

import argparse
import inspect
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

from src.data_pipeline import cli


REPO_ROOT = Path(__file__).parents[2]
EXPECTED_OPTIONS = {
    "--seed-input": ("seed_input", None, None, "Path", "_StoreAction"),
    "--target-count": (
        "target_count",
        2500,
        None,
        "_nonnegative_int",
        "_StoreAction",
    ),
    "--version-tag": ("version_tag", "phase1", None, None, "_StoreAction"),
    "--max-pages": ("max_pages", 1, None, "int", "_StoreAction"),
    "--max-links-per-page": (
        "max_links_per_page",
        5,
        None,
        "int",
        "_StoreAction",
    ),
    "--max-seeds": ("max_seeds", None, None, "int", "_StoreAction"),
    "--bulk-provider": (
        "bulk_provider",
        "auto",
        (
            "auto",
            "claude",
            "gemini",
            "openrouter",
            "deepseek",
            "openai-compatible",
        ),
        None,
        "_StoreAction",
    ),
    "--resume": ("resume", False, None, None, "_StoreTrueAction"),
    "--max-parallel-batches": (
        "max_parallel_batches",
        1,
        None,
        "int",
        "_StoreAction",
    ),
    "--checkpoint-dir": ("checkpoint_dir", None, None, "Path", "_StoreAction"),
    "--generate-only": ("generate_only", False, None, None, "_StoreTrueAction"),
    "--judge-existing": ("judge_existing", False, None, None, "_StoreTrueAction"),
    "--generated-input": ("generated_input", None, None, "Path", "_StoreAction"),
    "--salvage-partial": (
        "salvage_partial",
        False,
        None,
        None,
        "_StoreTrueAction",
    ),
    "--optimize-recovered": (
        "optimize_recovered",
        False,
        None,
        None,
        "_StoreTrueAction",
    ),
    "--gap-fill-recovered": (
        "gap_fill_recovered",
        False,
        None,
        None,
        "_StoreTrueAction",
    ),
}


def _action_snapshot(action: argparse.Action) -> tuple[object, ...]:
    action_type = getattr(action.type, "__name__", None)
    choices = tuple(action.choices) if action.choices is not None else None
    return (
        action.dest,
        action.default,
        choices,
        action_type,
        type(action).__name__,
    )


def test_parser_preserves_exact_sixteen_option_grammar() -> None:
    parser = cli.build_parser()
    actions = {
        action.option_strings[0]: _action_snapshot(action)
        for action in parser._actions
        if action.option_strings and action.option_strings[0] != "-h"
    }

    assert parser.prog == "python -m src.data_pipeline.cli"
    assert parser.description == (
        "Run the Phase 1 scrape -> generate flow, with optional judging and split building."
    )
    assert actions == EXPECTED_OPTIONS


def test_parser_rejects_negative_target_count() -> None:
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args(["--target-count", "-1"])


def test_help_construction_imports_no_optional_or_workflow_graph() -> None:
    code = (
        "import json, sys; "
        "from src.data_pipeline import cli; cli.build_parser(); "
        "blocked=('anthropic','google','httpx','playwright','sentence_transformers',"
        "'src.data_pipeline.generation.generator',"
        "'src.data_pipeline.generation.quality_judge',"
        "'src.data_pipeline.scraper.ncsc_scraper',"
        "'src.data_pipeline.migrations'); "
        "print(json.dumps([name for name in blocked if name in sys.modules]))"
    )
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=REPO_ROOT,
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert json.loads(completed.stdout) == []


@pytest.mark.parametrize(
    ("argv", "expected_call"),
    [
        (
            ["--optimize-recovered", "--salvage-partial", "--judge-existing"],
            "optimize",
        ),
        (["--salvage-partial", "--judge-existing"], "salvage"),
        (["--judge-existing"], "judge"),
        ([], "run"),
    ],
)
def test_mode_precedence_and_json_output_are_preserved(
    argv: list[str],
    expected_call: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls: list[tuple[str, object]] = []
    monkeypatch.setattr(cli, "get_settings", lambda: SimpleNamespace(data_dir=tmp_path))
    monkeypatch.setattr(cli, "get_data_settings", lambda: SimpleNamespace(data_dir=tmp_path))
    monkeypatch.setattr(
        cli,
        "optimize_recovered_records",
        lambda data_dir, target_count=2500: calls.append(
            ("optimize", (data_dir, target_count))
        )
        or {"mode": "optimize", "text": "xin chào"},
    )
    monkeypatch.setattr(
        cli,
        "salvage_partial_records",
        lambda data_dir: calls.append(("salvage", data_dir))
        or {"mode": "salvage", "text": "xin chào"},
    )
    monkeypatch.setattr(
        cli,
        "judge_existing_records",
        lambda data_dir, input_path, version_tag="phase1": calls.append(
            ("judge", (data_dir, input_path, version_tag))
        )
        or {"mode": "judge", "text": "xin chào"},
    )
    monkeypatch.setattr(
        cli,
        "run_phase1",
        lambda **kwargs: calls.append(("run", kwargs))
        or {"mode": "run", "text": "xin chào"},
    )

    assert cli.main(argv) == 0
    output = capsys.readouterr()
    assert [name for name, _ in calls] == [expected_call]
    assert json.loads(output.out) == {"mode": expected_call, "text": "xin chào"}
    assert "xin chào" in output.out
    assert output.err == ""


def test_run_dispatch_preserves_all_flag_values(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    captured: dict[str, object] = {}
    monkeypatch.setattr(cli, "get_settings", lambda: SimpleNamespace(data_dir=tmp_path))
    monkeypatch.setattr(
        cli,
        "run_phase1",
        lambda **kwargs: captured.update(kwargs) or {"ok": True},
    )
    seed = tmp_path / "seed.jsonl"
    checkpoint = tmp_path / "checkpoints"

    assert cli.main(
        [
            "--seed-input",
            os.fspath(seed),
            "--target-count",
            "12",
            "--version-tag",
            "synthetic-v2",
            "--max-pages",
            "2",
            "--max-links-per-page",
            "3",
            "--max-seeds",
            "4",
            "--bulk-provider",
            "deepseek",
            "--resume",
            "--max-parallel-batches",
            "2",
            "--checkpoint-dir",
            os.fspath(checkpoint),
            "--generate-only",
            "--gap-fill-recovered",
        ]
    ) == 0
    capsys.readouterr()
    assert captured == {
        "seed_input": seed,
        "target_count": 12,
        "version_tag": "synthetic-v2",
        "max_pages": 2,
        "max_links_per_page": 3,
        "max_seeds": 4,
        "bulk_provider": "deepseek",
        "resume": True,
        "max_parallel_batches": 2,
        "checkpoint_dir": checkpoint,
        "generate_only": True,
        "gap_fill_recovered": True,
    }


def test_cli_translates_errors_and_interrupts_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(cli, "get_settings", lambda: SimpleNamespace(data_dir=tmp_path))
    monkeypatch.setattr(cli, "get_data_settings", lambda: SimpleNamespace(data_dir=tmp_path))
    monkeypatch.setattr(
        cli,
        "salvage_partial_records",
        lambda data_dir: (_ for _ in ()).throw(ValueError("synthetic failure")),
    )
    assert cli.main(["--salvage-partial"]) == 1
    assert capsys.readouterr().err == "synthetic failure\n"

    monkeypatch.setattr(
        cli,
        "run_phase1",
        lambda **kwargs: (_ for _ in ()).throw(KeyboardInterrupt()),
    )
    assert cli.main([]) == 130
    assert capsys.readouterr().err == (
        "Interrupted. Completed generation batches were checkpointed. Resume with --resume.\n"
    )


@pytest.mark.parametrize("offline_flag", ("--salvage-partial", "--optimize-recovered"))
def test_offline_modes_never_construct_provider_or_runtime_settings(
    offline_flag: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        cli,
        "get_settings",
        lambda: (_ for _ in ()).throw(AssertionError("full settings accessed")),
    )
    monkeypatch.setattr(
        cli,
        "get_data_settings",
        lambda: SimpleNamespace(data_dir=tmp_path),
    )
    monkeypatch.setattr(
        cli,
        "salvage_partial_records",
        lambda data_dir: {"mode": "salvage", "root": str(data_dir)},
    )
    monkeypatch.setattr(
        cli,
        "optimize_recovered_records",
        lambda data_dir, target_count: {
            "mode": "optimize",
            "root": str(data_dir),
            "target": target_count,
        },
    )

    assert cli.main([offline_flag]) == 0
    assert json.loads(capsys.readouterr().out)["root"] == str(tmp_path)


def test_offline_settings_validation_error_is_translated(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        cli,
        "get_data_settings",
        lambda: (_ for _ in ()).throw(ValueError("invalid data settings")),
    )

    assert cli.main(["--salvage-partial"]) == 1
    assert capsys.readouterr().err == "invalid data settings\n"


def test_canonical_workflow_functions_have_neutral_ownership_and_lazy_cli_forwards() -> None:
    from src.data_pipeline import workflows
    from src.data_pipeline.generation.generator import TieredGenerator
    from src.data_pipeline.generation.quality_judge import QualityJudge
    from src.data_pipeline.scraper.ncsc_scraper import NCSCScraper
    from src.data_pipeline.versioning.build import DatasetBuilder

    for name in (
        "judge_existing_records",
        "salvage_partial_records",
        "optimize_recovered_records",
    ):
        assert getattr(workflows, name).__module__ == "src.data_pipeline.workflows"
        assert getattr(cli, name).__module__ == "src.data_pipeline.cli"
    assert workflows.build_training_corpus.__module__ == "src.data_pipeline.workflows"
    assert (
        inspect.signature(workflows.build_training_corpus)
        .parameters["version_tag"]
        .default
        == "dataset-v1"
    )
    assert (
        inspect.signature(workflows.judge_existing_records)
        .parameters["version_tag"]
        .default
        == "dataset-v1"
    )
    assert inspect.signature(cli.run_phase1).parameters["version_tag"].default == "phase1"
    assert (
        inspect.signature(cli.judge_existing_records)
        .parameters["version_tag"]
        .default
        == "phase1"
    )
    assert "Phase 1 generation" not in (
        REPO_ROOT / "src/data_pipeline/workflows.py"
    ).read_text(encoding="utf-8")
    assert not hasattr(workflows, "run_phase1")
    assert cli.run_phase1.__module__ == "src.data_pipeline.cli"
    for seam in (
        "get_settings",
        "get_data_settings",
        "_build_anthropic_client",
        "_save_validated_records",
    ):
        assert callable(getattr(cli, seam))
    expected_classes = {
        "TieredGenerator": TieredGenerator,
        "QualityJudge": QualityJudge,
        "DatasetBuilder": DatasetBuilder,
        "NCSCScraper": NCSCScraper,
    }
    for name, expected in expected_classes.items():
        exported = getattr(cli, name)
        assert exported is expected
        assert isinstance(exported, type)

    class CompatibleBuilder(cli.DatasetBuilder):
        pass

    assert issubclass(CompatibleBuilder, DatasetBuilder)
    assert isinstance(object.__new__(CompatibleBuilder), DatasetBuilder)


def test_reviewed_dataset_publication_switches_one_complete_generation(
    tmp_path: Path,
) -> None:
    from src.data_pipeline.publication import publish_reviewed_dataset

    record = {
        "text": "Thông báo giao dịch tổng hợp hợp lệ để kiểm thử công bố.",
        "label": "benign",
        "risk_tier": "benign",
        "suspicious_spans": [],
        "xai_explanation": "Giải thích tổng hợp đủ dài cho kiểm thử công bố dữ liệu.",
        "source": "synthetic_openai_compatible",
        "seed_id": "publication-seed",
    }

    class SyntheticBuilder:
        def __init__(self, version_tag: str) -> None:
            self.version_tag = version_tag

        def build_splits(self, *, input_path: Path, output_dir: Path) -> dict[str, object]:
            raw = input_path.read_bytes()
            for name in ("train", "val", "test"):
                (output_dir / f"{name}.jsonl").write_bytes(raw)
            (output_dir.parent / "split-manifest.json").write_text(
                json.dumps({"version": self.version_tag}), encoding="utf-8"
            )
            return {"splits": {"train": 1, "val": 1, "test": 1}}

    published = publish_reviewed_dataset(
        [record], {"accepted": 1}, tmp_path, "synthetic-v1", SyntheticBuilder
    )
    pointer = json.loads(published.current_pointer.read_text(encoding="utf-8"))
    manifest = json.loads(published.generation_manifest_path.read_text(encoding="utf-8"))

    assert pointer["generation_id"] == published.generation_id
    assert published.root.name == published.generation_id
    assert {member["path"] for member in manifest["members"]} == {
        "validated.jsonl",
        "quality-stats.json",
        "split-manifest.json",
        "splits/train.jsonl",
        "splits/val.jsonl",
        "splits/test.jsonl",
    }


def test_reviewed_dataset_failure_leaves_previous_pointer_unchanged(
    tmp_path: Path,
) -> None:
    from src.data_pipeline.publication import publish_reviewed_dataset

    publication_root = tmp_path / "dataset-generations"
    publication_root.mkdir()
    pointer = publication_root / "current.json"
    previous = b'{"generation_id":"previous"}\n'
    pointer.write_bytes(previous)
    record = {
        "text": "Thông báo giao dịch tổng hợp hợp lệ để kiểm thử lỗi.",
        "label": "benign",
        "risk_tier": "benign",
        "suspicious_spans": [],
        "xai_explanation": "Giải thích tổng hợp đủ dài cho kiểm thử lỗi công bố.",
        "source": "synthetic_openai_compatible",
        "seed_id": "publication-failure-seed",
    }

    class FailingBuilder:
        def __init__(self, version_tag: str) -> None:
            self.version_tag = version_tag

        def build_splits(self, *, input_path: Path, output_dir: Path) -> dict[str, object]:
            (output_dir / "train.jsonl").write_bytes(input_path.read_bytes())
            raise RuntimeError("synthetic split failure")

    with pytest.raises(RuntimeError, match="synthetic split failure"):
        publish_reviewed_dataset(
            [record], {"accepted": 1}, tmp_path, "synthetic-v1", FailingBuilder
        )

    assert pointer.read_bytes() == previous


def test_compatibility_save_publishes_one_complete_generation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.data_pipeline import publication, workflows
    from src.data_pipeline.versioning.build import DatasetBuilder

    generation_root = tmp_path / "dataset-generations" / "versions" / "synthetic"
    expected = SimpleNamespace(
        validated_path=generation_root / "validated.jsonl",
        quality_stats_path=generation_root / "quality-stats.json",
    )
    captured: dict[str, object] = {}

    def publish(
        records: list[dict[str, object]],
        quality_stats: object,
        data_dir: Path,
        version_tag: str,
        builder_factory: object,
    ) -> object:
        captured.update(
            records=records,
            quality_stats=quality_stats,
            data_dir=data_dir,
            version_tag=version_tag,
            builder_factory=builder_factory,
        )
        return expected

    monkeypatch.setattr(publication, "publish_reviewed_dataset", publish)
    records = [{"synthetic": "record"}]
    stats = {"accepted": 1}

    result = workflows._save_validated_records(records, stats, tmp_path)

    assert result == (expected.validated_path, expected.quality_stats_path)
    assert captured == {
        "records": records,
        "quality_stats": stats,
        "data_dir": tmp_path,
        "version_tag": "dataset-v1",
        "builder_factory": DatasetBuilder,
    }
    assert not (tmp_path / "processed").exists()


def test_zero_gap_generation_returns_summary_without_constructing_runtime(
    tmp_path: Path,
) -> None:
    from src.data_pipeline import workflows

    def forbidden(*args: object, **kwargs: object) -> object:
        raise AssertionError("zero-gap recovery must not construct generation dependencies")

    recovered = {
        "missing_by_label_for_target": {
            label: 0 for label in workflows.THREAT_CLASSES
        },
        "generation_gap_total": 0,
        "merged_output_path": None,
    }
    dependencies = workflows.WorkflowDependencies(
        get_settings=lambda: SimpleNamespace(data_dir=tmp_path),
        generator_factory=forbidden,
        judge_factory=forbidden,
        builder_factory=forbidden,
        scraper_factory=forbidden,
        anthropic_client_builder=forbidden,
        optimize_records=lambda data_dir, target_count: recovered,
    )

    summary = workflows.build_training_corpus(
        target_count=0,
        generate_only=True,
        gap_fill_recovered=True,
        _dependencies=dependencies,
    )

    assert summary["generated_path"] is None
    assert summary["generated_count"] == 0
    assert summary["recovered_summary"] is recovered
