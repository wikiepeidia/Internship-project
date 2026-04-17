"""
Schema validation tests for Pydantic models.

Tests enforce the JSONL contract expectations at every pipeline stage.
"""

import pytest
from pydantic import ValidationError
from src.data_pipeline.schemas import SeedRecord, DatasetRecord, ManifestFile, ManifestEntry


class TestSeedRecord:
    """Test SeedRecord validation rules."""
    
    def test_valid_seed_record(self, sample_seed_record):
        """SeedRecord validates a correct seed record with all required fields."""
        assert sample_seed_record.text.startswith("Khẩn cấp")
        assert "vpbank-update.vip" in sample_seed_record.text
        assert sample_seed_record.source_url == "https://canhbao.khonggianmang.vn/example-alert-123"
        assert sample_seed_record.scrape_timestamp == "2026-04-17T10:30:00Z"
        assert sample_seed_record.raw_label_hint == "bank_impersonation"
    
    def test_seed_record_min_text_length(self):
        """SeedRecord rejects record with text shorter than 10 characters."""
        with pytest.raises(ValidationError) as exc_info:
            SeedRecord(
                text="Short",
                source_url="https://example.com",
                scrape_timestamp="2026-04-17T10:30:00Z"
            )
        assert "text" in str(exc_info.value)
    
    def test_seed_record_missing_source_url(self):
        """SeedRecord rejects record missing required field source_url."""
        with pytest.raises(ValidationError) as exc_info:
            SeedRecord(
                text="This is a valid length message for testing",
                scrape_timestamp="2026-04-17T10:30:00Z"
            )
        assert "source_url" in str(exc_info.value)
    
    def test_seed_record_optional_label_hint(self):
        """SeedRecord accepts None for optional raw_label_hint field."""
        record = SeedRecord(
            text="This is a valid length message for testing",
            source_url="https://example.com",
            scrape_timestamp="2026-04-17T10:30:00Z",
            raw_label_hint=None
        )
        assert record.raw_label_hint is None


class TestDatasetRecord:
    """Test DatasetRecord validation rules."""
    
    def test_valid_dataset_record(self, sample_dataset_record):
        """DatasetRecord validates a correct record with all 7 fields."""
        assert len(sample_dataset_record.text) > 10
        assert sample_dataset_record.label == "bank_impersonation"
        assert sample_dataset_record.risk_tier == "high-risk"
        assert len(sample_dataset_record.suspicious_spans) == 3
        assert len(sample_dataset_record.xai_explanation) >= 20
        assert sample_dataset_record.source == "ncsc_seed"
        assert sample_dataset_record.seed_id == "seed_20260417_001"
    
    def test_dataset_record_invalid_label(self):
        """DatasetRecord rejects invalid label value."""
        with pytest.raises(ValidationError) as exc_info:
            DatasetRecord(
                text="This is a test message",
                label="invalid_label",
                risk_tier="high-risk",
                xai_explanation="This is an explanation with sufficient length",
                source="ncsc_seed",
                seed_id="test_001"
            )
        assert "label" in str(exc_info.value)
    
    def test_dataset_record_invalid_risk_tier(self):
        """DatasetRecord rejects invalid risk_tier value."""
        with pytest.raises(ValidationError) as exc_info:
            DatasetRecord(
                text="This is a test message",
                label="benign",
                risk_tier="invalid_tier",
                xai_explanation="This is an explanation with sufficient length",
                source="ncsc_seed",
                seed_id="test_001"
            )
        assert "risk_tier" in str(exc_info.value)
    
    def test_dataset_record_invalid_source(self):
        """DatasetRecord rejects invalid source value."""
        with pytest.raises(ValidationError) as exc_info:
            DatasetRecord(
                text="This is a test message",
                label="benign",
                risk_tier="benign",
                xai_explanation="This is an explanation with sufficient length",
                source="invalid_source",
                seed_id="test_001"
            )
        assert "source" in str(exc_info.value)
    
    def test_dataset_record_short_explanation(self):
        """DatasetRecord rejects xai_explanation shorter than 20 characters."""
        with pytest.raises(ValidationError) as exc_info:
            DatasetRecord(
                text="This is a test message",
                label="benign",
                risk_tier="benign",
                xai_explanation="Too short",
                source="ncsc_seed",
                seed_id="test_001"
            )
        assert "xai_explanation" in str(exc_info.value)
    
    def test_dataset_record_empty_suspicious_spans(self, sample_benign_record):
        """DatasetRecord accepts suspicious_spans as empty list (default_factory)."""
        assert sample_benign_record.suspicious_spans == []
        assert sample_benign_record.label == "benign"
    
    def test_dataset_record_all_valid_labels(self):
        """DatasetRecord accepts all defined threat labels."""
        valid_labels = ["bank_impersonation", "zalo_social_engineering", "task_scam", "benign"]
        for label in valid_labels:
            record = DatasetRecord(
                text="This is a test message with sufficient length",
                label=label,
                risk_tier="benign",
                xai_explanation="This is an explanation with sufficient length for testing",
                source="ncsc_seed",
                seed_id="test_001"
            )
            assert record.label == label
    
    def test_dataset_record_all_valid_risk_tiers(self):
        """DatasetRecord accepts all defined risk tiers."""
        valid_tiers = ["benign", "suspicious", "high-risk"]
        for tier in valid_tiers:
            record = DatasetRecord(
                text="This is a test message with sufficient length",
                label="benign",
                risk_tier=tier,
                xai_explanation="This is an explanation with sufficient length for testing",
                source="ncsc_seed",
                seed_id="test_001"
            )
            assert record.risk_tier == tier
    
    def test_dataset_record_all_valid_sources(self):
        """DatasetRecord accepts all defined source values."""
        valid_sources = ["ncsc_seed", "synthetic_claude", "synthetic_deepseek", "synthetic_openrouter"]
        for source in valid_sources:
            record = DatasetRecord(
                text="This is a test message with sufficient length",
                label="benign",
                risk_tier="benign",
                xai_explanation="This is an explanation with sufficient length for testing",
                source=source,
                seed_id="test_001"
            )
            assert record.source == source


class TestManifestEntry:
    """Test ManifestEntry and ManifestFile validation rules."""
    
    def test_valid_manifest_entry(self, sample_manifest_entry):
        """ManifestEntry contains version, build_timestamp, git_commit, files dict."""
        assert sample_manifest_entry.version == "v1.0.0"
        assert sample_manifest_entry.build_timestamp == "2026-04-17T12:00:00Z"
        assert sample_manifest_entry.git_commit == "abc123def456"
        assert len(sample_manifest_entry.files) == 3
        assert "train.jsonl" in sample_manifest_entry.files
    
    def test_manifest_file_structure(self, sample_manifest_entry):
        """ManifestFile contains sha256, records, bytes fields."""
        train_file = sample_manifest_entry.files["train.jsonl"]
        assert isinstance(train_file, ManifestFile)
        assert len(train_file.sha256) == 64
        assert train_file.records == 2400
        assert train_file.bytes == 1048576
    
    def test_manifest_entry_optional_git_commit(self):
        """ManifestEntry accepts None for optional git_commit field."""
        manifest = ManifestEntry(
            version="v0.1.0",
            build_timestamp="2026-04-17T12:00:00Z",
            git_commit=None
        )
        assert manifest.git_commit is None
        assert manifest.files == {}
    
    def test_manifest_entry_default_empty_files(self):
        """ManifestEntry defaults to empty files dict."""
        manifest = ManifestEntry(
            version="v0.1.0",
            build_timestamp="2026-04-17T12:00:00Z"
        )
        assert manifest.files == {}


class TestSettings:
    """Test Settings configuration loading."""
    
    def test_settings_import(self):
        """Settings loads from environment and has sensible defaults."""
        from src.config.settings import Settings, get_settings
        
        settings = get_settings()
        assert isinstance(settings, Settings)
        assert settings.data_dir.name == "data"
        assert settings.split_ratios == (0.8, 0.1, 0.1)
        assert settings.similarity_threshold == 0.85
        assert settings.scrape_delay_min == 2.0
        assert settings.scrape_delay_max == 5.0
        assert settings.ncsc_base_url == "https://canhbao.khonggianmang.vn"
    
    def test_settings_defaults(self):
        """Settings has sensible defaults for DATA_DIR, SPLIT_RATIOS, SIMILARITY_THRESHOLD."""
        from src.config.settings import Settings
        
        settings = Settings()
        # Verify split ratios sum to 1.0
        assert sum(settings.split_ratios) == pytest.approx(1.0)
        # Verify similarity threshold is in valid range
        assert 0.0 <= settings.similarity_threshold <= 1.0
        # Verify scrape delays are positive
        assert settings.scrape_delay_min > 0
        assert settings.scrape_delay_max > settings.scrape_delay_min
