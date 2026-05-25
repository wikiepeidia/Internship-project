"""Tests for the Phase 1 operator CLI."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.data_pipeline.cli import main
from src.data_pipeline.generation.quality_judge import QualityStats
from src.data_pipeline.schemas import ManifestEntry, SeedRecord


def _write_seed_jsonl(path: Path, records: list[SeedRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(record.model_dump_json() + "\n")


def test_phase1_cli_help_shows_operator_flags(capsys):
    with pytest.raises(SystemExit) as error:
        main(["--help"])

    assert error.value.code == 0
    stdout = capsys.readouterr().out
    assert "--seed-input" in stdout
    assert "--target-count" in stdout
    assert "--version-tag" in stdout
    assert "--bulk-provider" in stdout
    assert "deepseek" in stdout
    assert "--resume" in stdout
    assert "--max-parallel-batches" in stdout
    assert "--generate-only" in stdout
    assert "--judge-existing" in stdout
    assert "--generated-input" in stdout


def test_phase1_cli_uses_seed_input_and_persists_outputs(tmp_path, monkeypatch, sample_seed_record, sample_dataset_record, capsys):
    settings = SimpleNamespace(
        anthropic_api_key="anthropic",
        gemini_api_key="gemini",
        openrouter_api_key="",
        data_dir=tmp_path,
    )
    seed_input = tmp_path / "raw" / "seeds.jsonl"
    _write_seed_jsonl(seed_input, [sample_seed_record])

    generated_records = [sample_dataset_record.model_dump()]
    validated_records = [sample_dataset_record.model_dump()]
    quality_stats = QualityStats(
        total=1,
        passed=1,
        failed=0,
        pass_rate=1.0,
        avg_realism=4.0,
        avg_label_correctness=5.0,
        avg_code_switch_naturalness=4.0,
    )

    class FakeGenerator:
        def __init__(self, settings, anthropic_client=None, bulk_provider="auto"):
            self.settings = settings
            self.bulk_provider = bulk_provider

        def generate_dataset(
            self,
            seeds,
            target_count=2500,
            max_parallel_batches=1,
            checkpoint_path=None,
            partial_output_path=None,
            resume=False,
            progress_callback=None,
        ):
            assert len(seeds) == 1
            assert target_count == 50
            assert self.bulk_provider == "claude"
            assert max_parallel_batches == 2
            assert resume is True
            assert checkpoint_path == tmp_path / "synthetic"
            assert partial_output_path == tmp_path / "synthetic" / "generated-partial.jsonl"
            assert progress_callback is not None
            return generated_records

        def save_generated(self, records, output_path=None):
            destination = output_path or (self.settings.data_dir / "synthetic" / "generated.jsonl")
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("w", encoding="utf-8") as handle:
                for record in records:
                    handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            return destination

    class FakeJudge:
        def __init__(self, settings, anthropic_client=None):
            self.settings = settings

        def filter_passed(self, records, progress_callback=None):
            assert records == generated_records
            assert progress_callback is not None
            return validated_records, quality_stats

    class FakeBuilder:
        def __init__(self, version_tag="phase1"):
            self.version_tag = version_tag

        def build_splits(self, input_path=None, output_dir=None, similarity_threshold=None):
            splits_dir = output_dir or (tmp_path / "splits")
            splits_dir.mkdir(parents=True, exist_ok=True)
            split_counts = {"train": 1, "val": 1, "test": 1}
            for split_name in split_counts:
                split_path = splits_dir / f"{split_name}.jsonl"
                split_path.write_text(json.dumps(sample_dataset_record.model_dump(), ensure_ascii=False) + "\n", encoding="utf-8")

            manifest = ManifestEntry(
                version=self.version_tag,
                build_timestamp="2026-05-04T00:00:00Z",
                git_commit="abc123",
                files={},
            )
            manifest_path = tmp_path / "manifests" / f"manifest-{self.version_tag}.json"
            manifest_path.parent.mkdir(parents=True, exist_ok=True)
            manifest_path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
            return {
                "version": self.version_tag,
                "splits": split_counts,
                "manifest_path": str(manifest_path),
                "total_records": sum(split_counts.values()),
            }

    class ScraperShouldNotRun:
        def __init__(self, *args, **kwargs):
            raise AssertionError("scraper should not run when --seed-input is provided")

    monkeypatch.setattr("src.data_pipeline.cli.get_settings", lambda: settings)
    monkeypatch.setattr("src.data_pipeline.cli.TieredGenerator", FakeGenerator)
    monkeypatch.setattr("src.data_pipeline.cli.QualityJudge", FakeJudge)
    monkeypatch.setattr("src.data_pipeline.cli.DatasetBuilder", FakeBuilder)
    monkeypatch.setattr("src.data_pipeline.cli.NCSCScraper", ScraperShouldNotRun)
    monkeypatch.setattr("src.data_pipeline.cli._build_anthropic_client", lambda api_key: object())

    exit_code = main([
        "--seed-input",
        str(seed_input),
        "--target-count",
        "50",
        "--version-tag",
        "phase1-uat-gap",
        "--bulk-provider",
        "claude",
        "--resume",
        "--max-parallel-batches",
        "2",
    ])

    assert exit_code == 0
    stdout = capsys.readouterr().out
    summary = json.loads(stdout)

    assert summary["seed_count"] == 1
    assert summary["generated_count"] == 1
    assert summary["validated_count"] == 1
    assert summary["split_counts"] == {"train": 1, "val": 1, "test": 1}
    assert (tmp_path / "synthetic" / "generated.jsonl").exists()
    assert (tmp_path / "processed" / "validated.jsonl").exists()
    assert (tmp_path / "processed" / "quality-stats.json").exists()


def test_phase1_cli_scrapes_when_seed_input_is_omitted(tmp_path, monkeypatch, sample_seed_record, sample_dataset_record, capsys):
    settings = SimpleNamespace(
        anthropic_api_key="anthropic",
        gemini_api_key="gemini",
        openrouter_api_key="",
        data_dir=tmp_path,
    )
    quality_stats = QualityStats(
        total=1,
        passed=1,
        failed=0,
        pass_rate=1.0,
        avg_realism=4.0,
        avg_label_correctness=5.0,
        avg_code_switch_naturalness=4.0,
    )

    class FakeScraper:
        def scrape_advisory_list(self, max_pages=1, max_links_per_page=5, max_seeds=None):
            assert max_pages == 1
            assert max_links_per_page == 5
            assert max_seeds is None
            return [sample_seed_record]

        def save_seeds(self, seeds, output_path=None):
            destination = output_path or (tmp_path / "raw" / "seeds.jsonl")
            _write_seed_jsonl(destination, seeds)
            return destination

    class FakeGenerator:
        def __init__(self, settings, anthropic_client=None, bulk_provider="auto"):
            self.settings = settings
            self.bulk_provider = bulk_provider

        def generate_dataset(
            self,
            seeds,
            target_count=2500,
            max_parallel_batches=1,
            checkpoint_path=None,
            partial_output_path=None,
            resume=False,
            progress_callback=None,
        ):
            assert self.bulk_provider == "auto"
            return [sample_dataset_record.model_dump()]

        def save_generated(self, records, output_path=None):
            destination = output_path or (self.settings.data_dir / "synthetic" / "generated.jsonl")
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(json.dumps(records[0], ensure_ascii=False) + "\n", encoding="utf-8")
            return destination

    class FakeJudge:
        def __init__(self, settings, anthropic_client=None):
            self.settings = settings

        def filter_passed(self, records, progress_callback=None):
            return [sample_dataset_record.model_dump()], quality_stats

    class FakeBuilder:
        def __init__(self, version_tag="phase1"):
            self.version_tag = version_tag

        def build_splits(self, input_path=None, output_dir=None, similarity_threshold=None):
            splits_dir = output_dir or (tmp_path / "splits")
            splits_dir.mkdir(parents=True, exist_ok=True)
            for split_name in ("train", "val", "test"):
                (splits_dir / f"{split_name}.jsonl").write_text("{}\n", encoding="utf-8")
            manifest_path = tmp_path / "manifests" / f"manifest-{self.version_tag}.json"
            manifest_path.parent.mkdir(parents=True, exist_ok=True)
            manifest_path.write_text("{}", encoding="utf-8")
            return {
                "version": self.version_tag,
                "splits": {"train": 1, "val": 1, "test": 1},
                "manifest_path": str(manifest_path),
                "total_records": 3,
            }

    monkeypatch.setattr("src.data_pipeline.cli.get_settings", lambda: settings)
    monkeypatch.setattr("src.data_pipeline.cli.NCSCScraper", FakeScraper)
    monkeypatch.setattr("src.data_pipeline.cli.TieredGenerator", FakeGenerator)
    monkeypatch.setattr("src.data_pipeline.cli.QualityJudge", FakeJudge)
    monkeypatch.setattr("src.data_pipeline.cli.DatasetBuilder", FakeBuilder)
    monkeypatch.setattr("src.data_pipeline.cli._build_anthropic_client", lambda api_key: object())

    exit_code = main(["--target-count", "50", "--version-tag", "phase1-uat-gap"])
    
    assert exit_code == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["seed_count"] == 1
    assert (tmp_path / "raw" / "seeds.jsonl").exists()


def test_phase1_cli_rejects_out_of_band_generation_count(tmp_path, monkeypatch, sample_seed_record, sample_dataset_record, capsys):
    settings = SimpleNamespace(
        anthropic_api_key="anthropic",
        gemini_api_key="gemini",
        openrouter_api_key="",
        data_dir=tmp_path,
    )
    seed_input = tmp_path / "raw" / "seeds.jsonl"
    _write_seed_jsonl(seed_input, [sample_seed_record])

    class FakeGenerator:
        def __init__(self, settings, anthropic_client=None, bulk_provider="auto"):
            self.settings = settings

        def generate_dataset(
            self,
            seeds,
            target_count=2500,
            max_parallel_batches=1,
            checkpoint_path=None,
            partial_output_path=None,
            resume=False,
            progress_callback=None,
        ):
            return [sample_dataset_record.model_dump()]

        def save_generated(self, records, output_path=None):
            raise AssertionError("save_generated should not run when band validation fails")

    monkeypatch.setattr("src.data_pipeline.cli.get_settings", lambda: settings)
    monkeypatch.setattr("src.data_pipeline.cli.TieredGenerator", FakeGenerator)
    monkeypatch.setattr("src.data_pipeline.cli._build_anthropic_client", lambda api_key: object())

    exit_code = main(["--seed-input", str(seed_input), "--target-count", "2500"])

    assert exit_code == 1
    assert "outside the required 2000-3000 band" in capsys.readouterr().err


def test_phase1_cli_fails_when_judge_accepts_zero_records(tmp_path, monkeypatch, sample_seed_record, sample_dataset_record, capsys):
    settings = SimpleNamespace(
        anthropic_api_key="anthropic",
        gemini_api_key="gemini",
        openrouter_api_key="",
        data_dir=tmp_path,
    )
    seed_input = tmp_path / "raw" / "seeds.jsonl"
    _write_seed_jsonl(seed_input, [sample_seed_record])

    quality_stats = QualityStats(
        total=1,
        passed=0,
        failed=1,
        pass_rate=0.0,
        avg_realism=2.0,
        avg_label_correctness=2.0,
        avg_code_switch_naturalness=2.0,
    )

    class FakeGenerator:
        def __init__(self, settings, anthropic_client=None, bulk_provider="auto"):
            self.settings = settings

        def generate_dataset(
            self,
            seeds,
            target_count=2500,
            max_parallel_batches=1,
            checkpoint_path=None,
            partial_output_path=None,
            resume=False,
            progress_callback=None,
        ):
            return [sample_dataset_record.model_dump()]

        def save_generated(self, records, output_path=None):
            destination = output_path or (self.settings.data_dir / "synthetic" / "generated.jsonl")
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(json.dumps(records[0], ensure_ascii=False) + "\n", encoding="utf-8")
            return destination

    class FakeJudge:
        def __init__(self, settings, anthropic_client=None):
            self.settings = settings

        def filter_passed(self, records, progress_callback=None):
            return [], quality_stats

    monkeypatch.setattr("src.data_pipeline.cli.get_settings", lambda: settings)
    monkeypatch.setattr("src.data_pipeline.cli.TieredGenerator", FakeGenerator)
    monkeypatch.setattr("src.data_pipeline.cli.QualityJudge", FakeJudge)
    monkeypatch.setattr("src.data_pipeline.cli._build_anthropic_client", lambda api_key: object())

    exit_code = main(["--seed-input", str(seed_input), "--target-count", "50"])

    assert exit_code == 1
    assert "Judge produced zero accepted records" in capsys.readouterr().err


def test_phase1_cli_fails_when_seed_input_is_missing(tmp_path, monkeypatch, capsys):
    settings = SimpleNamespace(
        anthropic_api_key="anthropic",
        gemini_api_key="gemini",
        openrouter_api_key="",
        data_dir=tmp_path,
    )
    missing_seed_path = tmp_path / "raw" / "missing.jsonl"

    monkeypatch.setattr("src.data_pipeline.cli.get_settings", lambda: settings)

    exit_code = main(["--seed-input", str(missing_seed_path)])

    assert exit_code == 1
    assert "Seed input not found" in capsys.readouterr().err


def test_phase1_cli_generate_only_skips_judge_and_build(tmp_path, monkeypatch, sample_seed_record, sample_dataset_record, capsys):
    settings = SimpleNamespace(
        anthropic_api_key="anthropic",
        gemini_api_key="gemini",
        openrouter_api_key="",
        data_dir=tmp_path,
    )
    seed_input = tmp_path / "raw" / "seeds.jsonl"
    _write_seed_jsonl(seed_input, [sample_seed_record])

    generated_records = [sample_dataset_record.model_dump()]

    class FakeGenerator:
        def __init__(self, settings, anthropic_client=None, bulk_provider="auto"):
            self.settings = settings
            self.bulk_provider = bulk_provider

        def generate_dataset(
            self,
            seeds,
            target_count=2500,
            max_parallel_batches=1,
            checkpoint_path=None,
            partial_output_path=None,
            resume=False,
            progress_callback=None,
        ):
            assert len(seeds) == 1
            assert target_count == 50
            assert self.bulk_provider == "auto"
            assert resume is True
            assert checkpoint_path == tmp_path / "synthetic"
            assert partial_output_path == tmp_path / "synthetic" / "generated.jsonl"
            assert progress_callback is not None
            return generated_records

        def save_generated(self, records, output_path=None):
            destination = output_path or (self.settings.data_dir / "synthetic" / "generated.jsonl")
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("w", encoding="utf-8") as handle:
                for record in records:
                    handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            return destination

    class ShouldNotRunJudge:
        def __init__(self, *args, **kwargs):
            raise AssertionError("judge should not run in --generate-only mode")

    class ShouldNotRunBuilder:
        def __init__(self, *args, **kwargs):
            raise AssertionError("split builder should not run in --generate-only mode")

    monkeypatch.setattr("src.data_pipeline.cli.get_settings", lambda: settings)
    monkeypatch.setattr("src.data_pipeline.cli.TieredGenerator", FakeGenerator)
    monkeypatch.setattr("src.data_pipeline.cli.QualityJudge", ShouldNotRunJudge)
    monkeypatch.setattr("src.data_pipeline.cli.DatasetBuilder", ShouldNotRunBuilder)
    monkeypatch.setattr("src.data_pipeline.cli._build_anthropic_client", lambda api_key: object())

    exit_code = main([
        "--seed-input",
        str(seed_input),
        "--target-count",
        "50",
        "--resume",
        "--generate-only",
    ])

    assert exit_code == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["seed_count"] == 1
    assert summary["generated_count"] == 1
    assert summary["validated_count"] == 0
    assert summary["split_counts"] == {}
    assert summary["generate_only"] is True
    assert summary["validated_path"] is None
    assert summary["quality_stats_path"] is None
    assert summary["manifest_path"] is None
    assert (tmp_path / "synthetic" / "generated.jsonl").exists()
    assert not (tmp_path / "processed" / "validated.jsonl").exists()


def test_phase1_cli_generate_only_resume_rebuilds_generated_output_from_checkpoint(
    tmp_path,
    monkeypatch,
    sample_seed_record,
    sample_dataset_record,
    capsys,
):
    settings = SimpleNamespace(
        anthropic_api_key="anthropic",
        gemini_api_key="gemini",
        openrouter_api_key="",
        data_dir=tmp_path,
    )
    seed_input = tmp_path / "raw" / "seeds.jsonl"
    _write_seed_jsonl(seed_input, [sample_seed_record])

    checkpoint_dir = tmp_path / "synthetic"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    (checkpoint_dir / "checkpoint-001.jsonl").write_text('{"batch_key":"bank_impersonation:bulk:0"}\n', encoding="utf-8")
    generated_path = tmp_path / "synthetic" / "generated.jsonl"
    generated_path.write_text('{"stale": true}\n', encoding="utf-8")

    generated_records = [sample_dataset_record.model_dump()]

    class FakeGenerator:
        def __init__(self, settings, anthropic_client=None, bulk_provider="auto"):
            self.settings = settings

        def generate_dataset(
            self,
            seeds,
            target_count=2500,
            max_parallel_batches=1,
            checkpoint_path=None,
            partial_output_path=None,
            resume=False,
            progress_callback=None,
        ):
            assert resume is True
            assert checkpoint_path == tmp_path / "synthetic"
            assert partial_output_path == generated_path
            assert not partial_output_path.exists()
            return generated_records

        def save_generated(self, records, output_path=None):
            destination = output_path or generated_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("w", encoding="utf-8") as handle:
                for record in records:
                    handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            return destination

    class ShouldNotRunJudge:
        def __init__(self, *args, **kwargs):
            raise AssertionError("judge should not run in --generate-only mode")

    class ShouldNotRunBuilder:
        def __init__(self, *args, **kwargs):
            raise AssertionError("split builder should not run in --generate-only mode")

    monkeypatch.setattr("src.data_pipeline.cli.get_settings", lambda: settings)
    monkeypatch.setattr("src.data_pipeline.cli.TieredGenerator", FakeGenerator)
    monkeypatch.setattr("src.data_pipeline.cli.QualityJudge", ShouldNotRunJudge)
    monkeypatch.setattr("src.data_pipeline.cli.DatasetBuilder", ShouldNotRunBuilder)
    monkeypatch.setattr("src.data_pipeline.cli._build_anthropic_client", lambda api_key: object())

    exit_code = main([
        "--seed-input",
        str(seed_input),
        "--target-count",
        "50",
        "--resume",
        "--generate-only",
    ])

    assert exit_code == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["generated_count"] == 1
    assert generated_path.exists()
    assert "stale" not in generated_path.read_text(encoding="utf-8")


def test_phase1_cli_judge_existing_uses_existing_generated_artifact(
    tmp_path,
    monkeypatch,
    sample_dataset_record,
    capsys,
):
    settings = SimpleNamespace(
        anthropic_api_key="",
        gemini_api_key="",
        openrouter_api_key="",
        deepseek_api_key="",
        openai_compatible_base_url="http://127.0.0.1:8000/v1",
        openai_compatible_api_key="token",
        openai_compatible_model="Qwen/Qwen2.5-72B-Instruct-GPTQ-Int8",
        data_dir=tmp_path,
    )
    generated_path = tmp_path / "synthetic" / "generated-partial-phase7.jsonl"
    generated_path.parent.mkdir(parents=True, exist_ok=True)
    generated_path.write_text(sample_dataset_record.model_dump_json() + "\n", encoding="utf-8")

    quality_stats = QualityStats(
        total=1,
        passed=1,
        failed=0,
        pass_rate=1.0,
        avg_realism=4.0,
        avg_label_correctness=5.0,
        avg_code_switch_naturalness=4.0,
    )

    class ShouldNotRunGenerator:
        def __init__(self, *args, **kwargs):
            raise AssertionError("generator should not run in --judge-existing mode")

    class FakeJudge:
        def __init__(self, settings, anthropic_client=None):
            self.settings = settings
            assert anthropic_client is None

        def filter_passed(self, records, progress_callback=None):
            assert len(records) == 1
            assert records[0]["text"] == sample_dataset_record.text
            assert progress_callback is not None
            return [sample_dataset_record.model_dump()], quality_stats

    class FakeBuilder:
        def __init__(self, version_tag="phase1"):
            self.version_tag = version_tag

        def build_splits(self, input_path=None, output_dir=None, similarity_threshold=None):
            splits_dir = output_dir or (tmp_path / "splits")
            splits_dir.mkdir(parents=True, exist_ok=True)
            for split_name in ("train", "val", "test"):
                (splits_dir / f"{split_name}.jsonl").write_text("{}\n", encoding="utf-8")
            manifest_path = tmp_path / "manifests" / f"manifest-{self.version_tag}.json"
            manifest_path.parent.mkdir(parents=True, exist_ok=True)
            manifest_path.write_text("{}", encoding="utf-8")
            return {
                "version": self.version_tag,
                "splits": {"train": 1, "val": 0, "test": 0},
                "manifest_path": str(manifest_path),
                "total_records": 1,
            }

    monkeypatch.setattr("src.data_pipeline.cli.get_settings", lambda: settings)
    monkeypatch.setattr("src.data_pipeline.cli.TieredGenerator", ShouldNotRunGenerator)
    monkeypatch.setattr("src.data_pipeline.cli.QualityJudge", FakeJudge)
    monkeypatch.setattr("src.data_pipeline.cli.DatasetBuilder", FakeBuilder)
    monkeypatch.setattr("src.data_pipeline.cli._build_anthropic_client", lambda api_key: None)

    exit_code = main([
        "--judge-existing",
        "--generated-input",
        str(generated_path),
        "--version-tag",
        "proposal-closeout-judge",
    ])

    assert exit_code == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["judge_existing"] is True
    assert summary["generated_count"] == 1
    assert summary["validated_count"] == 1
    assert summary["generated_path"] == str(generated_path)
    assert summary["manifest_path"].endswith("manifest-proposal-closeout-judge.json")


def test_phase1_cli_judge_existing_fails_when_generated_input_is_missing(tmp_path, monkeypatch, capsys):
    settings = SimpleNamespace(
        anthropic_api_key="",
        gemini_api_key="",
        openrouter_api_key="",
        deepseek_api_key="",
        openai_compatible_base_url="http://127.0.0.1:8000/v1",
        openai_compatible_api_key="token",
        openai_compatible_model="Qwen/Qwen2.5-72B-Instruct-GPTQ-Int8",
        data_dir=tmp_path,
    )

    monkeypatch.setattr("src.data_pipeline.cli.get_settings", lambda: settings)

    exit_code = main([
        "--judge-existing",
        "--generated-input",
        str(tmp_path / "synthetic" / "missing.jsonl"),
    ])

    assert exit_code == 1
    assert "Generated input not found" in capsys.readouterr().err


# ── NEW: Atomic write ────────────────────────────────────────────────────────


def test_save_validated_records_writes_atomically(tmp_path, sample_dataset_record):
    """validated.jsonl is never left in a partial state: write goes via .tmp then os.replace."""
    from src.data_pipeline.cli import _save_validated_records

    records = [sample_dataset_record.model_dump()]
    validated_path, stats_path = _save_validated_records(records, {"pass_rate": 1.0}, tmp_path)

    assert validated_path.exists()
    assert stats_path.exists()
    # No stray .tmp files should remain after a successful write
    assert not validated_path.with_suffix(".tmp").exists()
    assert not stats_path.with_suffix(".tmp").exists()
    # Content is valid
    lines = [l for l in validated_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) == 1


def test_save_validated_records_tmp_is_replaced_not_appended(tmp_path, sample_dataset_record):
    """Repeated calls overwrite via atomic replace — never double-append old content."""
    from src.data_pipeline.cli import _save_validated_records

    records = [sample_dataset_record.model_dump()]
    _save_validated_records(records, {"pass_rate": 1.0}, tmp_path)
    _save_validated_records(records, {"pass_rate": 1.0}, tmp_path)

    validated_path = tmp_path / "processed" / "validated.jsonl"
    lines = [l for l in validated_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) == 1  # second write replaces, not appends


# ── NEW: Numbered checkpoint scheme ──────────────────────────────────────────


def test_numbered_checkpoint_creates_sequentially(sample_seed_record, tmp_path):
    """Each completed batch produces a new checkpoint-NNN.jsonl file."""
    import json as _json
    from src.data_pipeline.generation.generator import TieredGenerator

    settings = SimpleNamespace(
        anthropic_api_key="anthropic",
        gemini_api_key="gemini",
        openrouter_api_key="",
        deepseek_api_key="",
        openai_compatible_base_url="",
        openai_compatible_api_key="",
        openai_compatible_model="",
        google_oauth_access_token="",
        google_application_credentials="",
        google_cloud_project="",
        gemini_use_adc=False,
        data_dir=tmp_path,
    )
    generator = TieredGenerator(settings=settings)
    call_count = [0]

    def fake_complex(seed, threat_class, num_variants=3):
        call_count[0] += 1
        return [{"text": f"msg {i}", "label": threat_class, "risk_tier": "high-risk",
                 "suspicious_spans": [], "xai_explanation": "Giải thích dài hơn 20 ký tự.",
                 "source": "synthetic_claude", "seed_id": "seed_x"} for i in range(num_variants)]

    def fake_bulk(seed, threat_class, count=5):
        return [{"text": f"bulk {i}", "label": threat_class, "risk_tier": "suspicious",
                 "suspicious_spans": [], "xai_explanation": "Giải thích dài hơn 20 ký tự.",
                 "source": "synthetic_gemini", "seed_id": "seed_x"} for i in range(count)]

    generator.generate_complex = fake_complex
    generator.generate_bulk = fake_bulk
    checkpoint_dir = tmp_path / "synthetic"

    generator.generate_dataset(
        [sample_seed_record],
        target_count=12,
        checkpoint_path=checkpoint_dir,
    )

    files = sorted(checkpoint_dir.glob("checkpoint-*.jsonl"))
    assert files, "At least one numbered checkpoint file must exist"
    # Each file must be named checkpoint-NNN.jsonl
    for f in files:
        num = f.stem.split("-")[-1]
        assert num.isdigit() and len(num) == 3, f"Unexpected checkpoint filename: {f.name}"


def test_numbered_checkpoint_keeps_at_most_five(sample_seed_record, tmp_path):
    """After many batches, only the last CHECKPOINT_KEEP_COUNT=5 files are retained."""
    from src.data_pipeline.generation.generator import TieredGenerator, CHECKPOINT_KEEP_COUNT

    settings = SimpleNamespace(
        anthropic_api_key="anthropic",
        gemini_api_key="gemini",
        openrouter_api_key="",
        deepseek_api_key="",
        openai_compatible_base_url="",
        openai_compatible_api_key="",
        openai_compatible_model="",
        google_oauth_access_token="",
        google_application_credentials="",
        google_cloud_project="",
        gemini_use_adc=False,
        data_dir=tmp_path,
    )
    generator = TieredGenerator(settings=settings)

    def fake_complex(seed, threat_class, num_variants=3):
        return [{"text": f"msg {i} {threat_class}", "label": threat_class, "risk_tier": "high-risk",
                 "suspicious_spans": [], "xai_explanation": "Giải thích dài hơn 20 ký tự.",
                 "source": "synthetic_claude", "seed_id": "seed_x"} for i in range(num_variants)]

    def fake_bulk(seed, threat_class, count=5):
        return [{"text": f"bulk {i} {threat_class}", "label": threat_class, "risk_tier": "suspicious",
                 "suspicious_spans": [], "xai_explanation": "Giải thích dài hơn 20 ký tự.",
                 "source": "synthetic_gemini", "seed_id": "seed_x"} for i in range(count)]

    generator.generate_complex = fake_complex
    generator.generate_bulk = fake_bulk
    checkpoint_dir = tmp_path / "synthetic"

    generator.generate_dataset(
        [sample_seed_record],
        target_count=100,
        checkpoint_path=checkpoint_dir,
    )

    files = sorted(checkpoint_dir.glob("checkpoint-*.jsonl"))
    assert len(files) <= CHECKPOINT_KEEP_COUNT


def test_numbered_checkpoint_resume_reads_latest_file(sample_seed_record, tmp_path):
    """Resume loads from the highest-numbered checkpoint file, ignoring older ones."""
    import json as _json
    from src.data_pipeline.generation.generator import TieredGenerator

    settings = SimpleNamespace(
        anthropic_api_key="anthropic",
        gemini_api_key="gemini",
        openrouter_api_key="",
        deepseek_api_key="",
        openai_compatible_base_url="",
        openai_compatible_api_key="",
        openai_compatible_model="",
        google_oauth_access_token="",
        google_application_credentials="",
        google_cloud_project="",
        gemini_use_adc=False,
        data_dir=tmp_path,
    )
    generator = TieredGenerator(settings=settings)
    checkpoint_dir = tmp_path / "synthetic"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    restored_record = {"text": "restored text unique xyzzy", "label": "bank_impersonation",
                       "risk_tier": "high-risk", "suspicious_spans": [],
                       "xai_explanation": "Giải thích dài hơn 20 ký tự.",
                       "source": "synthetic_claude", "seed_id": "seed_abc"}
    stale_entry = {"batch_key": "bank_impersonation:complex:0", "order": 0,
                   "threat_class": "bank_impersonation", "batch_type": "complex",
                   "batch_index": 0, "requested_count": 1, "returned_count": 1,
                   "provider": "synthetic_claude", "timestamp": "2026-05-04T00:00:00Z",
                   "records": [restored_record]}
    latest_entry = dict(stale_entry)

    # Write an old checkpoint (stale) and a newer one (latest)
    (checkpoint_dir / "checkpoint-002.jsonl").write_text(
        _json.dumps(stale_entry, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (checkpoint_dir / "checkpoint-003.jsonl").write_text(
        _json.dumps(latest_entry, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    completed = generator._load_checkpoint(checkpoint_dir)

    assert "bank_impersonation:complex:0" in completed
    assert completed["bank_impersonation:complex:0"][1][0]["text"] == "restored text unique xyzzy"


# ── NEW: Salvage partial records ─────────────────────────────────────────────


def test_salvage_partial_records_merges_and_deduplicates(tmp_path):
    """salvage_partial_records merges both files, drops duplicates by text, keeps partial."""
    from src.data_pipeline.cli import salvage_partial_records

    synthetic_dir = tmp_path / "synthetic"
    synthetic_dir.mkdir(parents=True, exist_ok=True)

    record_a = '{"text":"msg alpha","label":"bank_impersonation","risk_tier":"high-risk","suspicious_spans":[],"xai_explanation":"Tin nhan gia mao ngan hang alpha.","source":"synthetic_claude","seed_id":"s1"}'
    record_b = '{"text":"msg beta","label":"benign","risk_tier":"benign","suspicious_spans":[],"xai_explanation":"Tin nhan binh thuong khong lua dao.","source":"synthetic_claude","seed_id":"s2"}'
    record_c = '{"text":"msg gamma","label":"task_scam","risk_tier":"suspicious","suspicious_spans":[],"xai_explanation":"Tin nhan lua dao nhiem vu gia mao.","source":"synthetic_gemini","seed_id":"s3"}'

    # generated.jsonl has A + B; partial has B (duplicate) + C
    (synthetic_dir / "generated.jsonl").write_text(record_a + "\n" + record_b + "\n", encoding="utf-8")
    (synthetic_dir / "generated-partial.jsonl").write_text(record_b + "\n" + record_c + "\n", encoding="utf-8")

    result = salvage_partial_records(tmp_path)

    assert result["merged_unique"] == 3
    assert result["duplicates_dropped"] == 1
    # partial file must NOT be deleted
    assert (synthetic_dir / "generated-partial.jsonl").exists()
    # generated.jsonl must contain all three unique records
    lines = [l for l in (synthetic_dir / "generated.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) == 3


def test_salvage_partial_records_works_without_partial_file(tmp_path):
    """Salvage succeeds even if generated-partial.jsonl does not exist."""
    from src.data_pipeline.cli import salvage_partial_records

    synthetic_dir = tmp_path / "synthetic"
    synthetic_dir.mkdir(parents=True, exist_ok=True)
    record = '{"text":"only record","label":"benign","risk_tier":"benign","suspicious_spans":[],"xai_explanation":"explanation text","source":"synthetic_claude","seed_id":"s1"}'
    (synthetic_dir / "generated.jsonl").write_text(record + "\n", encoding="utf-8")

    result = salvage_partial_records(tmp_path)

    assert result["merged_unique"] == 1
    assert result["duplicates_dropped"] == 0


def test_salvage_cli_flag_runs_salvage_and_exits(tmp_path, monkeypatch, capsys):
    """--salvage-partial flag routes to salvage_partial_records and prints JSON summary."""
    settings = SimpleNamespace(data_dir=tmp_path)
    monkeypatch.setattr("src.data_pipeline.cli.get_settings", lambda: settings)

    synthetic_dir = tmp_path / "synthetic"
    synthetic_dir.mkdir(parents=True, exist_ok=True)
    record = '{"text":"test record text","label":"benign","risk_tier":"benign","suspicious_spans":[],"xai_explanation":"explanation here","source":"synthetic_claude","seed_id":"s1"}'
    (synthetic_dir / "generated.jsonl").write_text(record + "\n", encoding="utf-8")

    exit_code = main(["--salvage-partial"])

    assert exit_code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["merged_unique"] == 1
    assert "generated_path" in out


def test_optimize_recovered_records_merges_dedups_and_balances(tmp_path):
    from src.data_pipeline.cli import optimize_recovered_records

    synthetic_dir = tmp_path / "synthetic"
    processed_dir = tmp_path / "processed"
    splits_dir = tmp_path / "splits"
    synthetic_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)
    splits_dir.mkdir(parents=True, exist_ok=True)

    def record(text, label, seed_id):
        return json.dumps(
            {
                "text": text,
                "label": label,
                "risk_tier": "benign" if label == "benign" else "high-risk",
                "suspicious_spans": [] if label == "benign" else [text.split()[0]],
                "xai_explanation": f"Giải thích hợp lệ cho {label} với nội dung đủ dài.",
                "source": "synthetic_claude",
                "seed_id": seed_id,
            },
            ensure_ascii=False,
        )

    (processed_dir / "validated.jsonl").write_text(
        "\n".join(
            [
                record("bank alpha notice", "bank_impersonation", "s1"),
                record("bank beta alert", "bank_impersonation", "s2"),
                record("zalo confirm transfer", "zalo_social_engineering", "s3"),
                record("task complete bonus", "task_scam", "s4"),
                record("monthly balance summary", "benign", "s5"),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (synthetic_dir / "generated(1).jsonl").write_text(
        "\n".join(
            [
                record("bank gamma otp", "bank_impersonation", "s6"),
                record("zalo shipping refund", "zalo_social_engineering", "s7"),
                record("task receive payout", "task_scam", "s8"),
                "not json",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    checkpoint_entry = {
        "batch_key": "benign:bulk:0",
        "order": 0,
        "threat_class": "benign",
        "batch_type": "bulk",
        "batch_index": 0,
        "requested_count": 1,
        "returned_count": 1,
        "provider": "synthetic_claude",
        "timestamp": "2026-05-05T00:00:00Z",
        "records": [json.loads(record("payday reminder normal", "benign", "s9"))],
    }
    (synthetic_dir / ".checkpoint.jsonl").write_text(
        json.dumps(checkpoint_entry, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    result = optimize_recovered_records(tmp_path, target_count=8)

    assert result["invalid_items"] == 1
    assert result["balanced_total"] == 8
    assert result["requested_per_class"] == 2
    assert result["missing_by_label_for_target"] == {
        "bank_impersonation": 0,
        "zalo_social_engineering": 0,
        "task_scam": 0,
        "benign": 0,
    }
    assert result["balanced_by_label"] == {
        "bank_impersonation": 2,
        "zalo_social_engineering": 2,
        "task_scam": 2,
        "benign": 2,
    }
    assert (synthetic_dir / "recovered-merged.jsonl").exists()
    assert (synthetic_dir / "recovered-balanced.jsonl").exists()
    assert (splits_dir / "recovered-balanced" / "train.jsonl").exists()


def test_optimize_recovered_cli_flag_runs_and_prints_summary(tmp_path, monkeypatch, capsys):
    settings = SimpleNamespace(data_dir=tmp_path, split_ratios=(0.8, 0.1, 0.1))
    monkeypatch.setattr("src.data_pipeline.cli.get_settings", lambda: settings)

    synthetic_dir = tmp_path / "synthetic"
    synthetic_dir.mkdir(parents=True, exist_ok=True)

    records = [
        {"text": "bank one alert", "label": "bank_impersonation", "risk_tier": "high-risk", "suspicious_spans": [], "xai_explanation": "Giải thích dài hơn hai mươi ký tự cho bank one.", "source": "synthetic_claude", "seed_id": "a"},
        {"text": "zalo one notice", "label": "zalo_social_engineering", "risk_tier": "high-risk", "suspicious_spans": [], "xai_explanation": "Giải thích dài hơn hai mươi ký tự cho zalo one.", "source": "synthetic_claude", "seed_id": "b"},
        {"text": "task one payout", "label": "task_scam", "risk_tier": "suspicious", "suspicious_spans": [], "xai_explanation": "Giải thích dài hơn hai mươi ký tự cho task one.", "source": "synthetic_claude", "seed_id": "c"},
        {"text": "benign one memo", "label": "benign", "risk_tier": "benign", "suspicious_spans": [], "xai_explanation": "Giải thích dài hơn hai mươi ký tự cho benign one.", "source": "synthetic_claude", "seed_id": "d"},
    ]
    (synthetic_dir / "generated.jsonl").write_text(
        "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n",
        encoding="utf-8",
    )

    exit_code = main(["--optimize-recovered", "--target-count", "4"])

    assert exit_code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["balanced_total"] == 4
    assert out["selected_per_class"] == 1
    assert "balanced_output_path" in out


def test_optimize_recovered_records_spreads_balanced_selection_across_seeds(tmp_path):
    from src.data_pipeline.cli import optimize_recovered_records

    synthetic_dir = tmp_path / "synthetic"
    synthetic_dir.mkdir(parents=True, exist_ok=True)

    def record(text, label, seed_id):
        return {
            "text": text,
            "label": label,
            "risk_tier": "benign" if label == "benign" else "high-risk",
            "suspicious_spans": [] if label == "benign" else [text.split()[0]],
            "xai_explanation": f"Giải thích hợp lệ cho {label} với nội dung đủ dài.",
            "source": "synthetic_claude",
            "seed_id": seed_id,
        }

    records: list[dict[str, object]] = []
    for label in ("bank_impersonation", "zalo_social_engineering", "task_scam", "benign"):
        for seed_index in range(4):
            records.append(
                record(
                    f"{label} seed {seed_index} unique token {seed_index * 17 + 3}",
                    label,
                    f"{label}-seed-{seed_index}",
                )
            )

    (synthetic_dir / "generated.jsonl").write_text(
        "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n",
        encoding="utf-8",
    )

    result = optimize_recovered_records(tmp_path, target_count=16)

    assert result["balanced_total"] == 16
    assert result["selected_per_class"] == 4

    balanced_path = synthetic_dir / "recovered-balanced.jsonl"
    selected_seed_ids: dict[str, set[str]] = {
        "bank_impersonation": set(),
        "zalo_social_engineering": set(),
        "task_scam": set(),
        "benign": set(),
    }
    with balanced_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            item = json.loads(line)
            selected_seed_ids[item["label"]].add(item["seed_id"])

    assert all(len(seed_ids) == 4 for seed_ids in selected_seed_ids.values())


def test_optimize_recovered_records_includes_backup_artifacts_and_reports_missing_labels(tmp_path):
    from src.data_pipeline.cli import optimize_recovered_records

    synthetic_dir = tmp_path / "synthetic"
    backup_checkpoint_dir = tmp_path / "backup" / "run-01" / "checkpoints"
    synthetic_dir.mkdir(parents=True, exist_ok=True)
    backup_checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def record(text, label, seed_id):
        return {
            "text": text,
            "label": label,
            "risk_tier": "benign" if label == "benign" else "high-risk",
            "suspicious_spans": [] if label == "benign" else [text.split()[0]],
            "xai_explanation": f"Giải thích hợp lệ cho {label} với nội dung đủ dài.",
            "source": "synthetic_claude",
            "seed_id": seed_id,
        }

    current_records = [
        record("bank one urgent otp notice with fake login portal", "bank_impersonation", "b1"),
        record("bank two urgent transfer warning with fake hotline", "bank_impersonation", "b2"),
        record("zalo one refund confirmation asking to verify transfer", "zalo_social_engineering", "z1"),
        record("zalo two shipping support message requesting payment hold", "zalo_social_engineering", "z2"),
        record("task one remote payout message asking to finish bonus mission", "task_scam", "t1"),
        record("task two salary reward chat asking to prepay verification fee", "task_scam", "t2"),
    ]
    (synthetic_dir / "generated.jsonl").write_text(
        "\n".join(json.dumps(item, ensure_ascii=False) for item in current_records) + "\n",
        encoding="utf-8",
    )

    checkpoint_entry = {
        "batch_key": "benign:bulk:0",
        "order": 0,
        "threat_class": "benign",
        "batch_type": "bulk",
        "batch_index": 0,
        "requested_count": 1,
        "returned_count": 1,
        "provider": "synthetic_claude",
        "timestamp": "2026-05-05T00:00:00Z",
        "records": [record("benign one normal account reminder with no action needed", "benign", "n1")],
    }
    (backup_checkpoint_dir / "checkpoint-001.jsonl").write_text(
        json.dumps(checkpoint_entry, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    result = optimize_recovered_records(tmp_path, target_count=8)

    assert any("backup" in path and "checkpoint-001.jsonl" in path for path in result["source_files"])
    assert result["requested_per_class"] == 2
    assert result["missing_by_label_for_target"] == {
        "bank_impersonation": 0,
        "zalo_social_engineering": 0,
        "task_scam": 0,
        "benign": 1,
    }
    assert result["generation_gap_total"] == 1


def test_phase1_cli_gap_fill_recovered_generates_only_missing_labels(tmp_path, monkeypatch, sample_seed_record, capsys):
    settings = SimpleNamespace(
        anthropic_api_key="",
        gemini_api_key="",
        openrouter_api_key="",
        data_dir=tmp_path,
    )
    seed_input = tmp_path / "raw" / "seeds.jsonl"
    _write_seed_jsonl(seed_input, [sample_seed_record])

    expected_missing = {
        "bank_impersonation": 0,
        "zalo_social_engineering": 0,
        "task_scam": 171,
        "benign": 520,
    }

    class FakeGenerator:
        def __init__(self, settings, anthropic_client=None, bulk_provider="auto"):
            self.settings = settings
            self.bulk_provider = bulk_provider

        def generate_dataset(
            self,
            seeds,
            target_count=2500,
            max_parallel_batches=1,
            checkpoint_path=None,
            partial_output_path=None,
            resume=False,
            progress_callback=None,
            class_targets=None,
        ):
            assert len(seeds) == 1
            assert target_count == 691
            assert class_targets == expected_missing
            assert checkpoint_path == tmp_path / "backup" / "recovered-gap-fill" / "checkpoints"
            assert partial_output_path == tmp_path / "synthetic" / "generated-gap-fill-recovered.jsonl"
            assert resume is False
            return [
                {
                    "text": "task missing fill one",
                    "label": "task_scam",
                    "risk_tier": "high-risk",
                    "suspicious_spans": ["task"],
                    "xai_explanation": "Giải thích hợp lệ cho task missing fill one.",
                    "source": "synthetic_openai_compatible",
                    "seed_id": "gap-task-1",
                },
                {
                    "text": "benign missing fill one",
                    "label": "benign",
                    "risk_tier": "benign",
                    "suspicious_spans": [],
                    "xai_explanation": "Giải thích hợp lệ cho benign missing fill one.",
                    "source": "synthetic_openai_compatible",
                    "seed_id": "gap-benign-1",
                },
            ]

        def save_generated(self, records, output_path=None):
            destination = output_path or (self.settings.data_dir / "synthetic" / "generated-gap-fill-recovered.jsonl")
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("w", encoding="utf-8") as handle:
                for record in records:
                    handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            return destination

    monkeypatch.setattr("src.data_pipeline.cli.get_settings", lambda: settings)
    monkeypatch.setattr("src.data_pipeline.cli.TieredGenerator", FakeGenerator)
    monkeypatch.setattr("src.data_pipeline.cli._build_anthropic_client", lambda api_key: None)
    monkeypatch.setattr(
        "src.data_pipeline.cli.optimize_recovered_records",
        lambda data_dir, target_count: {
            "merged_output_path": str(tmp_path / "synthetic" / "recovered-merged.jsonl"),
            "missing_by_label_for_target": expected_missing,
            "generation_gap_total": 691,
        },
    )

    exit_code = main([
        "--seed-input",
        str(seed_input),
        "--target-count",
        "3000",
        "--bulk-provider",
        "openai-compatible",
        "--generate-only",
        "--gap-fill-recovered",
    ])

    assert exit_code == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["generated_count"] == 2
    assert summary["gap_fill_recovered"] is True
    assert summary["gap_fill_missing_by_label"] == expected_missing
    assert summary["generated_path"].endswith("generated-gap-fill-recovered.jsonl")


def test_phase1_cli_gap_fill_recovered_resume_preserves_existing_output(tmp_path, monkeypatch, sample_seed_record, capsys):
    settings = SimpleNamespace(
        anthropic_api_key="",
        gemini_api_key="",
        openrouter_api_key="",
        data_dir=tmp_path,
    )
    seed_input = tmp_path / "raw" / "seeds.jsonl"
    _write_seed_jsonl(seed_input, [sample_seed_record])

    generated_path = tmp_path / "synthetic" / "generated-gap-fill-recovered.jsonl"
    generated_path.parent.mkdir(parents=True, exist_ok=True)
    existing_record = {
        "text": "task gap already recovered",
        "label": "task_scam",
        "risk_tier": "high-risk",
        "suspicious_spans": ["task"],
        "xai_explanation": "Giải thích hợp lệ cho task gap already recovered.",
        "source": "synthetic_openai_compatible",
        "seed_id": "gap-task-1",
    }
    generated_path.write_text(json.dumps(existing_record, ensure_ascii=False) + "\n", encoding="utf-8")

    checkpoint_dir = tmp_path / "backup" / "recovered-gap-fill" / "checkpoints"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    (checkpoint_dir / "checkpoint-001.jsonl").write_text('{"batch_key":"task_scam:bulk:0"}\n', encoding="utf-8")

    new_record = {
        "text": "benign gap newly recovered",
        "label": "benign",
        "risk_tier": "benign",
        "suspicious_spans": [],
        "xai_explanation": "Giải thích hợp lệ cho benign gap newly recovered.",
        "source": "synthetic_openai_compatible",
        "seed_id": "gap-benign-1",
    }

    class FakeGenerator:
        def __init__(self, settings, anthropic_client=None, bulk_provider="auto"):
            self.settings = settings

        def generate_dataset(
            self,
            seeds,
            target_count=2500,
            max_parallel_batches=1,
            checkpoint_path=None,
            partial_output_path=None,
            resume=False,
            progress_callback=None,
            class_targets=None,
        ):
            assert resume is True
            assert checkpoint_path == checkpoint_dir
            assert partial_output_path == generated_path
            assert partial_output_path.exists()
            with partial_output_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(new_record, ensure_ascii=False) + "\n")
            return [new_record]

        def save_generated(self, records, output_path=None):
            raise AssertionError("save_generated should not overwrite cumulative gap-fill output on resume")

    monkeypatch.setattr("src.data_pipeline.cli.get_settings", lambda: settings)
    monkeypatch.setattr("src.data_pipeline.cli.TieredGenerator", FakeGenerator)
    monkeypatch.setattr("src.data_pipeline.cli._build_anthropic_client", lambda api_key: None)
    monkeypatch.setattr(
        "src.data_pipeline.cli.optimize_recovered_records",
        lambda data_dir, target_count: {
            "merged_output_path": str(tmp_path / "synthetic" / "recovered-merged.jsonl"),
            "missing_by_label_for_target": {
                "bank_impersonation": 0,
                "zalo_social_engineering": 0,
                "task_scam": 0,
                "benign": 1,
            },
            "generation_gap_total": 1,
        },
    )

    exit_code = main([
        "--seed-input",
        str(seed_input),
        "--target-count",
        "3000",
        "--bulk-provider",
        "openai-compatible",
        "--generate-only",
        "--gap-fill-recovered",
        "--checkpoint-dir",
        str(checkpoint_dir),
        "--resume",
    ])

    assert exit_code == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["generated_count"] == 2
    written_lines = generated_path.read_text(encoding="utf-8").splitlines()
    assert len(written_lines) == 2
    labels = [json.loads(line)["label"] for line in written_lines]
    assert labels == ["task_scam", "benign"]