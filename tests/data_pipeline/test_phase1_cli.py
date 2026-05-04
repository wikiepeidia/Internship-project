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
        def __init__(self, settings, anthropic_client=None):
            self.settings = settings

        def generate_dataset(self, seeds, target_count=2500):
            assert len(seeds) == 1
            assert target_count == 50
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

        def filter_passed(self, records):
            assert records == generated_records
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
        def __init__(self, settings, anthropic_client=None):
            self.settings = settings

        def generate_dataset(self, seeds, target_count=2500):
            return [sample_dataset_record.model_dump()]

        def save_generated(self, records, output_path=None):
            destination = output_path or (self.settings.data_dir / "synthetic" / "generated.jsonl")
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(json.dumps(records[0], ensure_ascii=False) + "\n", encoding="utf-8")
            return destination

    class FakeJudge:
        def __init__(self, settings, anthropic_client=None):
            self.settings = settings

        def filter_passed(self, records):
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
        def __init__(self, settings, anthropic_client=None):
            self.settings = settings

        def generate_dataset(self, seeds, target_count=2500):
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
        def __init__(self, settings, anthropic_client=None):
            self.settings = settings

        def generate_dataset(self, seeds, target_count=2500):
            return [sample_dataset_record.model_dump()]

        def save_generated(self, records, output_path=None):
            destination = output_path or (self.settings.data_dir / "synthetic" / "generated.jsonl")
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(json.dumps(records[0], ensure_ascii=False) + "\n", encoding="utf-8")
            return destination

    class FakeJudge:
        def __init__(self, settings, anthropic_client=None):
            self.settings = settings

        def filter_passed(self, records):
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