"""Environment-based configuration split by domain ownership.

Each active owner loads only the fields it needs. The legacy ``Settings``
composition remains available for historical callers with the same env-file
order, defaults, and OS-environment precedence.
"""

from functools import lru_cache
import math
import os
from pathlib import Path

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings


ENV_FILE_CANDIDATES = (".env/APIKEY.json", ".env/.env")
MINIMUM_PYTHON_VERSION = (3, 13)
DEFAULT_RELEASE_MANIFEST_ROOT = Path(__file__).parents[2] / "data" / "manifests"
PROJECT_ROOT = Path(__file__).parents[2]
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

    @field_validator("split_ratios")
    @classmethod
    def require_valid_split_ratios(
        cls, value: tuple[float, float, float]
    ) -> tuple[float, float, float]:
        if len(value) != 3 or any(
            not math.isfinite(ratio) or ratio < 0.0 for ratio in value
        ):
            raise ValueError("split_ratios must contain three finite non-negative values")
        if not math.isclose(sum(value), 1.0, rel_tol=0.0, abs_tol=1e-9):
            raise ValueError("split_ratios must sum to one")
        return value

    @field_validator("similarity_threshold")
    @classmethod
    def require_valid_similarity_threshold(cls, value: float) -> float:
        if not math.isfinite(value) or not 0.0 <= value <= 1.0:
            raise ValueError("similarity_threshold must be a finite value in [0, 1]")
        return value


class ModelingSettings(_OwnedSettings):
    """Local model artifact locations shared by modeling and runtime."""

    model_storage_root: Path = Path("data")
    model_artifact_root: Path = Path("data/models")
    model_registry_path: Path = Path("data/manifests/model-registry.json")

    @field_validator(
        "model_storage_root",
        "model_artifact_root",
        "model_registry_path",
        mode="before",
    )
    @classmethod
    def reject_noncanonical_model_paths(cls, value: object) -> object:
        candidate = Path(value) if isinstance(value, (str, os.PathLike)) else None
        if candidate is not None and (
            "\x00" in os.fspath(candidate) or ".." in candidate.parts
        ):
            raise ValueError("model paths must not contain NUL or parent traversal")
        return value

    @staticmethod
    def _project_absolute(path: Path) -> Path:
        candidate = path if path.is_absolute() else PROJECT_ROOT / path
        return Path(os.path.abspath(os.path.normpath(os.fspath(candidate))))

    @property
    def resolved_model_storage_root(self) -> Path:
        return self._project_absolute(self.model_storage_root)

    @property
    def resolved_model_artifact_root(self) -> Path:
        return self._project_absolute(self.model_artifact_root)

    @property
    def resolved_model_registry_path(self) -> Path:
        return self._project_absolute(self.model_registry_path)

    @model_validator(mode="after")
    def require_bounded_model_paths(self) -> "ModelingSettings":
        configured = self.model_fields_set
        if (
            "model_storage_root" not in configured
            and {"model_artifact_root", "model_registry_path"}.issubset(configured)
        ):
            common = Path(
                os.path.commonpath(
                    (
                        self.resolved_model_artifact_root,
                        self.resolved_model_registry_path,
                    )
                )
            )
            if common.parent == common:
                raise ValueError("explicit model paths require model_storage_root")
            self.model_storage_root = common
        root = self.resolved_model_storage_root
        for name, candidate in (
            ("model_artifact_root", self.resolved_model_artifact_root),
            ("model_registry_path", self.resolved_model_registry_path),
        ):
            if candidate == root or root not in candidate.parents:
                raise ValueError(f"{name} must be below model_storage_root")
        return self


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

    @model_validator(mode="after")
    def reject_colliding_gguf_profiles(self) -> "RuntimeSettings":
        if self.runtime_profile_gguf == self.runtime_profile_gguf_runner_up:
            raise ValueError(
                "runtime_profile_gguf and runtime_profile_gguf_runner_up must be distinct"
            )
        return self


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
