"""Tests for environment-based configuration loading from .env/ folder."""

import pytest
from pathlib import Path


SETTINGS_ENV_VARS = [
    "ANTHROPIC_API_KEY",
    "GEMINI_API_KEY",
    "OPENROUTER_API_KEY",
    "DATA_DIR",
    "SPLIT_RATIOS",
    "SIMILARITY_THRESHOLD",
    "SCRAPE_DELAY_MIN",
    "SCRAPE_DELAY_MAX",
    "NCSC_BASE_URL",
]


@pytest.fixture(autouse=True)
def clear_settings_environment(monkeypatch):
    """Keep tests isolated from the developer's real local environment."""
    for env_var in SETTINGS_ENV_VARS:
        monkeypatch.delenv(env_var, raising=False)


class TestEnvironmentLoading:
    """Test that Settings loads from .env/ folder with correct precedence."""
    
    def test_loads_from_env_folder_apikey_json(self, monkeypatch, tmp_path):
        """Settings loads API keys from .env/APIKEY.json format."""
        # Create a temporary .env/ directory structure
        env_dir = tmp_path / ".env"
        env_dir.mkdir()
        apikey_file = env_dir / "APIKEY.json"
        apikey_file.write_text(
            "ANTHROPIC_API_KEY=test-anthropic-key\n"
            "GEMINI_API_KEY=test-gemini-key\n"
            "OPENROUTER_API_KEY=test-openrouter-key\n"
        )
        
        # Change to tmp directory so Settings finds our test .env/
        monkeypatch.chdir(tmp_path)
        
        from src.config.settings import Settings
        settings = Settings()
        
        assert settings.anthropic_api_key == "test-anthropic-key"
        assert settings.gemini_api_key == "test-gemini-key"
        assert settings.openrouter_api_key == "test-openrouter-key"
    
    def test_loads_from_env_folder_dotenv_file(self, monkeypatch, tmp_path):
        """Settings loads from .env/.env standard file when present."""
        env_dir = tmp_path / ".env"
        env_dir.mkdir()
        dotenv_file = env_dir / ".env"
        dotenv_file.write_text(
            "ANTHROPIC_API_KEY=standard-anthropic\n"
            "SIMILARITY_THRESHOLD=0.92\n"
        )
        
        monkeypatch.chdir(tmp_path)
        
        from src.config.settings import Settings
        settings = Settings()
        
        assert settings.anthropic_api_key == "standard-anthropic"
        assert settings.similarity_threshold == 0.92
    
    def test_dotenv_takes_precedence_over_apikey_json(self, monkeypatch, tmp_path):
        """When both .env/.env and .env/APIKEY.json exist, .env/.env takes precedence."""
        env_dir = tmp_path / ".env"
        env_dir.mkdir()
        
        # Create both files with different values
        dotenv_file = env_dir / ".env"
        dotenv_file.write_text("ANTHROPIC_API_KEY=from-dotenv\n")
        
        apikey_file = env_dir / "APIKEY.json"
        apikey_file.write_text("ANTHROPIC_API_KEY=from-apikey\n")
        
        monkeypatch.chdir(tmp_path)
        
        from src.config.settings import Settings
        settings = Settings()
        
        # .env/.env should take precedence (listed last in env_file - last wins in pydantic-settings)
        assert settings.anthropic_api_key == "from-dotenv"
    
    def test_os_environment_overrides_env_files(self, monkeypatch, tmp_path):
        """OS environment variables override values from .env/ files."""
        env_dir = tmp_path / ".env"
        env_dir.mkdir()
        apikey_file = env_dir / "APIKEY.json"
        apikey_file.write_text("ANTHROPIC_API_KEY=file-value\n")
        
        # Set OS environment variable
        monkeypatch.setenv("ANTHROPIC_API_KEY", "os-override-value")
        monkeypatch.chdir(tmp_path)
        
        from src.config.settings import Settings
        settings = Settings()
        
        # OS environment should win
        assert settings.anthropic_api_key == "os-override-value"
    
    def test_graceful_when_env_folder_missing(self, monkeypatch, tmp_path):
        """Settings works when .env/ folder doesn't exist (uses defaults)."""
        # No .env/ folder created
        monkeypatch.chdir(tmp_path)
        
        from src.config.settings import Settings
        settings = Settings()
        
        # Should use defaults without error
        assert settings.data_dir == Path("data")
        assert settings.split_ratios == (0.8, 0.1, 0.1)
        # API keys default to empty string
        assert settings.anthropic_api_key == ""
    
    def test_mixed_sources(self, monkeypatch, tmp_path):
        """Settings correctly merges values from file + OS environment."""
        env_dir = tmp_path / ".env"
        env_dir.mkdir()
        apikey_file = env_dir / "APIKEY.json"
        apikey_file.write_text(
            "ANTHROPIC_API_KEY=file-anthropic\n"
            "GEMINI_API_KEY=file-gemini\n"
        )
        
        # Override only one key via OS env
        monkeypatch.setenv("GEMINI_API_KEY", "os-gemini")
        monkeypatch.chdir(tmp_path)
        
        from src.config.settings import Settings
        settings = Settings()
        
        # File value preserved where not overridden
        assert settings.anthropic_api_key == "file-anthropic"
        # OS override applied
        assert settings.gemini_api_key == "os-gemini"
        # Unset key uses default
        assert settings.openrouter_api_key == ""


class TestSettingsDefaults:
    """Test Settings default values and validation."""
    
    def test_settings_defaults_unchanged(self):
        """Settings default values remain consistent."""
        from src.config.settings import Settings
        
        settings = Settings()
        assert settings.data_dir == Path("data")
        assert settings.split_ratios == (0.8, 0.1, 0.1)
        assert settings.similarity_threshold == 0.85
        assert settings.scrape_delay_min == 2.0
        assert settings.scrape_delay_max == 5.0
        assert settings.ncsc_base_url == "https://canhbao.khonggianmang.vn"
    
    def test_split_ratios_sum_to_one(self):
        """Split ratios sum to 1.0."""
        from src.config.settings import Settings
        
        settings = Settings()
        assert sum(settings.split_ratios) == pytest.approx(1.0)
    
    def test_similarity_threshold_in_range(self):
        """Similarity threshold is between 0.0 and 1.0."""
        from src.config.settings import Settings
        
        settings = Settings()
        assert 0.0 <= settings.similarity_threshold <= 1.0
    
    def test_scrape_delays_positive(self):
        """Scrape delays are positive and max > min."""
        from src.config.settings import Settings
        
        settings = Settings()
        assert settings.scrape_delay_min > 0
        assert settings.scrape_delay_max > settings.scrape_delay_min


class TestGetSettings:
    """Test get_settings() factory function."""
    
    def test_get_settings_returns_settings_instance(self):
        """get_settings() returns a Settings instance."""
        from src.config.settings import Settings, get_settings
        
        settings = get_settings()
        assert isinstance(settings, Settings)
    
    def test_get_settings_returns_new_instance_each_time(self):
        """get_settings() returns a new instance on each call (not cached)."""
        from src.config.settings import get_settings
        
        settings1 = get_settings()
        settings2 = get_settings()
        # They should be separate instances (pydantic-settings creates new on each call)
        assert settings1 is not settings2
