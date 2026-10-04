"""Checksum-backed local registry helpers for Phase 3 model artifacts."""

from __future__ import annotations

import hashlib
from pathlib import Path

from src.model_adaptation.schemas import ArtifactType, ModelArtifactRecord, ModelRegistry


def _update_digest_from_file(digest: "hashlib._Hash", file_path: Path) -> None:
    with file_path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)


def build_model_checksum(file_path: Path) -> str:
    """Build a stable SHA256 checksum for one local artifact path."""

    if not file_path.exists():
        raise FileNotFoundError(f"Missing artifact file: {file_path}")
    if file_path.is_file():
        digest = hashlib.sha256()
        _update_digest_from_file(digest, file_path)
        return digest.hexdigest()

    digest = hashlib.sha256()
    for child in sorted(path for path in file_path.rglob("*") if path.is_file()):
        digest.update(child.relative_to(file_path).as_posix().encode("utf-8"))
        digest.update(b"\0")
        _update_digest_from_file(digest, child)
        digest.update(b"\0")
    return digest.hexdigest()


def save_model_registry(registry: ModelRegistry, output_path: Path) -> Path:
    """Persist model registry metadata as formatted JSON."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(registry.model_dump_json(indent=2), encoding="utf-8")
    return output_path


def load_model_registry(input_path: Path) -> ModelRegistry:
    """Load previously saved registry metadata into typed models."""

    return ModelRegistry.model_validate_json(input_path.read_text(encoding="utf-8"))


def find_latest_artifact(
    registry: ModelRegistry,
    *,
    candidate_id: str,
    artifact_type: ArtifactType,
) -> ModelArtifactRecord | None:
    """Return the most recently registered matching artifact for one candidate and type."""

    for artifact in reversed(registry.artifacts):
        if artifact.candidate_id == candidate_id and artifact.artifact_type == artifact_type:
            return artifact
    return None