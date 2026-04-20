"""Environment-based pipeline configuration using pydantic-settings.

Loads API keys and pipeline parameters from local files under .env/ or from
OS environment variables. Never hardcode secrets or environment-specific
values in source code.
"""

from pydantic_settings import BaseSettings
from pathlib import Path


ENV_FILE_CANDIDATES = (".env/APIKEY.json", ".env/.env")


class Settings(BaseSettings):
    """Global configuration for the Vietnamese phishing detection pipeline.

    Real local secret files live under .env/. OS environment variables still
    override file-based values when they are present.
    """
    # API Keys - no defaults, must be provided via environment
    anthropic_api_key: str = ""
    gemini_api_key: str = ""
    openrouter_api_key: str = ""
    deepseek_api_key: str = ""
    
    # Data Pipeline Paths
    data_dir: Path = Path("data")
    
    # Dataset Split Configuration
    split_ratios: tuple[float, float, float] = (0.8, 0.1, 0.1)  # train/val/test
    
    # Semantic Deduplication
    similarity_threshold: float = 0.85  # Cosine similarity threshold for near-duplicates
    
    # Scraper Configuration
    scrape_delay_min: float = 2.0  # Minimum delay between requests (seconds)
    scrape_delay_max: float = 5.0  # Maximum delay between requests (seconds)
    ncsc_base_url: str = "https://canhbao.khonggianmang.vn"
    
    model_config = {
        "env_file": list(ENV_FILE_CANDIDATES),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


def get_settings() -> Settings:
    """Build a Settings instance from .env/ files and OS environment vars."""
    return Settings()
