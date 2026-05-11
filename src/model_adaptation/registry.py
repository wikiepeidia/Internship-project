"""Checksum-backed local registry helpers for Phase 3 model artifacts."""

from __future__ import annotations

import hashlib
from pathlib import Path

from src.model_adaptation.schemas import ModelRegistry


def build_model_checksum(file_path: Path) -> str:
    """Build a stable SHA256 checksum for one local artifact file."""

    if not file_path.exists():
        raise FileNotFoundError(f"Missing artifact file: {file_path}")
    return hashlib.sha256(file_path.read_bytes()).hexdigest()


def save_model_registry(registry: ModelRegistry, output_path: Path) -> Path:
    """Persist model registry metadata as formatted JSON."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(registry.model_dump_json(indent=2), encoding="utf-8")
    return output_path


def load_model_registry(input_path: Path) -> ModelRegistry:
    """Load previously saved registry metadata into typed models."""

    return ModelRegistry.model_validate_json(input_path.read_text(encoding="utf-8"))