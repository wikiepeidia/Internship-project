"""Synthetic ownership contracts for resumable generation runs."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.core.integrity import IntegrityError
from src.data_pipeline import generation_runs
from src.data_pipeline import workflows


def _dataset_record() -> dict[str, object]:
    return {
        "text": "Thông báo giao dịch hợp lệ dùng cho lần chạy tổng hợp.",
        "label": "benign",
        "risk_tier": "benign",
        "suspicious_spans": [],
        "xai_explanation": "Giải thích tổng hợp đủ dài cho kiểm thử lần chạy.",
        "source": "synthetic_openai_compatible",
        "seed_id": "synthetic-run-seed",
    }


def _seed_file(path: Path) -> Path:
    payload = {
        "text": "Cảnh báo nguồn tổng hợp hợp lệ để thử lần chạy.",
        "source_url": "urn:synthetic:generation-run",
        "scrape_timestamp": "2026-08-27T00:00:00Z",
        "raw_label_hint": None,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def test_external_checkpoint_directory_is_rejected_without_mutation(tmp_path: Path) -> None:
    root = tmp_path / "corpus"
    root.mkdir()
    outside = tmp_path / "external" / "checkpoints"

    with pytest.raises(IntegrityError, match="escaped the data root"):
        generation_runs.prepare_generation_run(
            root,
            version_tag="synthetic-run",
            checkpoint_dir=outside,
            resume=False,
        )

    assert not outside.exists()
    assert not (root / "generation-runs").exists()


def test_generation_run_rejects_redirect_parent_before_side_effects(tmp_path: Path) -> None:
    root = tmp_path / "corpus"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    try:
        (root / "generation-runs").symlink_to(outside, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"directory symlinks unavailable: {exc}")

    with pytest.raises(IntegrityError, match="symlink or reparse"):
        generation_runs.prepare_generation_run(
            root,
            version_tag="redirected-run",
            checkpoint_dir=None,
            resume=False,
        )

    assert list(outside.iterdir()) == []


def test_failing_generator_preserves_previous_completed_artifact_and_ledger(
    tmp_path: Path,
) -> None:
    root = tmp_path / "corpus"
    synthetic = root / "synthetic"
    synthetic.mkdir(parents=True)
    stable = synthetic / "generated.jsonl"
    previous = (json.dumps(_dataset_record(), ensure_ascii=False) + "\n").encode("utf-8")
    stable.write_bytes(previous)
    seed_path = _seed_file(root / "seed.jsonl")

    class FailingGenerator:
        def generate_dataset(self, _seeds: object, **kwargs: object) -> list[dict[str, object]]:
            checkpoint_root = Path(kwargs["checkpoint_path"])
            partial = Path(kwargs["partial_output_path"])
            checkpoint_root.joinpath("checkpoint-001.jsonl").write_text(
                '{"synthetic":true}\n', encoding="utf-8"
            )
            partial.write_text(
                json.dumps(_dataset_record(), ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            raise RuntimeError("synthetic generator failure")

    dependencies = workflows.WorkflowDependencies(
        get_settings=lambda: SimpleNamespace(data_dir=root, anthropic_api_key=""),
        generator_factory=lambda **_kwargs: FailingGenerator(),
        judge_factory=lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("judge must not run")
        ),
        builder_factory=lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("builder must not run")
        ),
        scraper_factory=lambda: (_ for _ in ()).throw(
            AssertionError("scraper must not run")
        ),
        anthropic_client_builder=lambda _key: None,
        optimize_records=lambda *_args, **_kwargs: {},
    )

    with pytest.raises(RuntimeError, match="synthetic generator failure"):
        workflows.build_training_corpus(
            seed_input=seed_path,
            target_count=12,
            version_tag="synthetic-run",
            checkpoint_dir=Path("run-a"),
            generate_only=True,
            _dependencies=dependencies,
        )

    assert stable.read_bytes() == previous
    run_root = root / "generation-runs" / "run-a"
    ledger = json.loads((run_root / "ledger.json").read_text(encoding="utf-8"))
    assert {Path(row["path"]).name for row in ledger["owned_files"]} == {
        "checkpoint-001.jsonl",
        "generated-partial.jsonl",
    }
    assert (run_root / "checkpoints" / "checkpoint-001.jsonl").is_file()
    assert (run_root / "checkpoints" / "generated-partial.jsonl").is_file()


def test_cleanup_leaves_identity_replaced_run_file_untouched(tmp_path: Path) -> None:
    root = tmp_path / "corpus"
    root.mkdir()
    run = generation_runs.prepare_generation_run(
        root,
        version_tag="synthetic-run",
        checkpoint_dir=Path("run-a"),
        resume=False,
    )
    checkpoint = run.checkpoints / "checkpoint-001.jsonl"
    checkpoint.write_bytes(b"owned\n")
    owned = tuple(generation_runs.snapshot_run_files(run).values())
    checkpoint.unlink()
    checkpoint.write_bytes(b"replacement\n")

    generation_runs.cleanup_owned_files(owned)

    assert checkpoint.read_bytes() == b"replacement\n"


def test_successful_generation_publishes_candidate_then_cleans_exact_run_files(
    tmp_path: Path,
) -> None:
    root = tmp_path / "corpus"
    root.mkdir()
    seed_path = _seed_file(root / "seed.jsonl")

    class SuccessfulGenerator:
        def generate_dataset(self, _seeds: object, **kwargs: object) -> list[dict[str, object]]:
            checkpoint_root = Path(kwargs["checkpoint_path"])
            checkpoint_root.joinpath("checkpoint-001.jsonl").write_text(
                '{"synthetic":true}\n', encoding="utf-8"
            )
            return [_dataset_record()]

    dependencies = workflows.WorkflowDependencies(
        get_settings=lambda: SimpleNamespace(data_dir=root, anthropic_api_key=""),
        generator_factory=lambda **_kwargs: SuccessfulGenerator(),
        judge_factory=lambda **_kwargs: None,
        builder_factory=lambda **_kwargs: None,
        scraper_factory=lambda: None,
        anthropic_client_builder=lambda _key: None,
        optimize_records=lambda *_args, **_kwargs: {},
    )

    result = workflows.build_training_corpus(
        seed_input=seed_path,
        target_count=1,
        version_tag="synthetic-run",
        checkpoint_dir=Path("run-a"),
        generate_only=True,
        _dependencies=dependencies,
    )

    stable = Path(result["generated_path"])
    assert json.loads(stable.read_text(encoding="utf-8"))["seed_id"] == (
        "synthetic-run-seed"
    )
    checkpoint_root = root / "generation-runs" / "run-a" / "checkpoints"
    assert list(checkpoint_root.iterdir()) == []
    assert (checkpoint_root.parent / "ledger.json").is_file()
    candidate = generation_runs.resolve_generated_candidate(root, stable)
    assert candidate.path == stable
    assert candidate.run_id == "run-a"
    assert candidate.row_count == 1


def test_generated_candidate_rejects_unmarked_finalized_and_changed_inputs(
    tmp_path: Path,
) -> None:
    root = tmp_path / "corpus"
    synthetic = root / "synthetic"
    synthetic.mkdir(parents=True)
    unmarked = synthetic / "generated.jsonl"
    unmarked.write_text(json.dumps(_dataset_record()) + "\n", encoding="utf-8")
    with pytest.raises(IntegrityError):
        generation_runs.resolve_generated_candidate(root, unmarked)

    finalized = root / "splits" / "validation.jsonl"
    finalized.parent.mkdir()
    finalized.write_text(json.dumps(_dataset_record()) + "\n", encoding="utf-8")
    with pytest.raises(IntegrityError, match="finalized dataset trees"):
        generation_runs.resolve_generated_candidate(root, finalized)

    run = generation_runs.prepare_generation_run(
        root, version_tag="run-b", checkpoint_dir=Path("run-b"), resume=False
    )
    candidate_path = generation_runs.stage_generated_records(run, [_dataset_record()])
    published = generation_runs.publish_generated_candidate(
        run, candidate_path, "generated.jsonl"
    )
    published.write_bytes(published.read_bytes() + b"\n")
    with pytest.raises(IntegrityError, match="hash does not match"):
        generation_runs.resolve_generated_candidate(root, published)


def test_judge_existing_rejects_finalized_input_before_dependencies_run(
    tmp_path: Path,
) -> None:
    root = tmp_path / "corpus"
    finalized = root / "splits" / "validation.jsonl"
    finalized.parent.mkdir(parents=True)
    finalized.write_text(json.dumps(_dataset_record()) + "\n", encoding="utf-8")
    trap = lambda *_args, **_kwargs: (_ for _ in ()).throw(
        AssertionError("judge dependency must not run")
    )
    dependencies = workflows.WorkflowDependencies(
        get_settings=lambda: SimpleNamespace(data_dir=root, anthropic_api_key=""),
        generator_factory=trap,
        judge_factory=trap,
        builder_factory=trap,
        scraper_factory=trap,
        anthropic_client_builder=trap,
        optimize_records=trap,
    )

    with pytest.raises(IntegrityError, match="finalized dataset trees"):
        workflows.judge_existing_records(
            root, finalized, _dependencies=dependencies
        )
