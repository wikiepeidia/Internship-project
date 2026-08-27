"""Environment-based configuration split by domain ownership.

Each active owner loads only the fields it needs. The legacy ``Settings``
composition remains available for historical callers with the same env-file
order, defaults, and OS-environment precedence.
"""

from functools import lru_cache
import os
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings


ENV_FILE_CANDIDATES = (".env/APIKEY.json", ".env/.env")
MINIMUM_PYTHON_VERSION = (3, 13)
DEFAULT_RELEASE_MANIFEST_ROOT = Path(__file__).parents[2] / "data" / "manifests"
_SETTINGS_CONFIG = {
    "env_file": list(ENV_FILE_CANDIDATES),
    "env_file_encoding": "utf-8",
    "extra": "ignore",
}


class _OwnedSettings(BaseSettings):
    """Shared env-file contract for every settings owner."""

    model_config = _SETTINGS_CONFIG


class ProviderSettings(_OwnedSettings):
    """Credentials and provider-specific generation configuration."""

    anthropic_api_key: str = ""
    gemini_api_key: str = ""
    google_oauth_access_token: str = ""
    openrouter_api_key: str = ""
    deepseek_api_key: str = ""
    openai_compatible_base_url: str = ""
    openai_compatible_api_key: str = ""
    openai_compatible_model: str = ""
    google_application_credentials: str = ""
    google_cloud_project: str = ""
    gemini_use_adc: bool = False


class DataSettings(_OwnedSettings):
    """Corpus, deduplication, and scraper configuration."""

    data_dir: Path = Path("data")
    split_ratios: tuple[float, float, float] = (0.8, 0.1, 0.1)
    similarity_threshold: float = 0.85
    scrape_delay_min: float = 2.0
    scrape_delay_max: float = 5.0
    ncsc_base_url: str = "https://canhbao.khonggianmang.vn"


class ModelingSettings(_OwnedSettings):
    """Local model artifact locations shared by modeling and runtime."""

    model_artifact_root: Path = Path("data/models")
    model_registry_path: Path = Path("data/manifests/model-registry.json")


class RuntimeSettings(ModelingSettings):
    """Secret-free installed-runtime configuration."""

    runtime_backend: str = "gguf"
    runtime_profile: str = "gguf-laptop"
    runtime_profile_gguf: str = "gguf-laptop"
    runtime_profile_gguf_runner_up: str = "gguf-runner-up"
    runtime_profile_accelerated: str = "accelerated-local"
    runtime_max_cues: int = 3
    runtime_min_text_chars: int = 8
    runtime_store_raw_text: bool = False
    runtime_fail_closed: bool = True
    runtime_allow_text_flag: bool = True
    runtime_release_manifest_root: Path = DEFAULT_RELEASE_MANIFEST_ROOT
    runtime_text_only_message: str = (
        "Paste extracted text manually. OCR, screenshots, and voice messages are not supported in this demo."
    )

    @field_validator("runtime_release_manifest_root")
    @classmethod
    def require_absolute_release_root(cls, value: Path) -> Path:
        if not value.is_absolute():
            raise ValueError("runtime_release_manifest_root must be absolute")
        return Path(os.path.abspath(os.path.normpath(os.fspath(value))))


class Settings(ProviderSettings, DataSettings, RuntimeSettings):
    """Full compatibility composition for historical pipeline callers."""


@lru_cache(maxsize=1)
def get_runtime_settings() -> RuntimeSettings:
    """Return the cached secret-free settings used by installed runtime code."""

    return RuntimeSettings()


@lru_cache(maxsize=1)
def get_provider_settings() -> ProviderSettings:
    """Return cached provider-owned credentials and generation settings."""

    return ProviderSettings()


@lru_cache(maxsize=1)
def get_data_settings() -> DataSettings:
    """Return cached corpus and scraper settings."""

    return DataSettings()


@lru_cache(maxsize=1)
def get_modeling_settings() -> ModelingSettings:
    """Return cached local modeling artifact locations."""

    return ModelingSettings()


def get_settings() -> Settings:
    """Build a fresh full compatibility composition for legacy callers."""

    return Settings()
