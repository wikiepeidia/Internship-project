"""Phase-neutral contracts and readers for active runtime artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from src.core.integrity import IntegrityError, strict_json_object


class ArtifactError(RuntimeError):
    """Raised when an active artifact does not satisfy its contract."""


def _manifest_models(payload: Mapping[str, Any]) -> list[Any]:
    models = payload.get("models", [])
    if not isinstance(models, list):
        raise ArtifactError("download manifest models must be a list")
    return models


def load_download_manifest(output_root: Path) -> dict[str, Path]:
    """Load the candidate-to-local-path mapping from a download manifest."""

    manifest_path = Path(output_root) / "manifests" / "download-manifest.json"
    if not manifest_path.exists():
        return {}
    try:
        payload = strict_json_object(manifest_path, where="download manifest")
    except IntegrityError as exc:
        raise ArtifactError(str(exc)) from exc

    model_paths: dict[str, Path] = {}
    for index, model in enumerate(_manifest_models(payload)):
        if not isinstance(model, Mapping):
            raise ArtifactError(f"download manifest model {index} must be an object")
        candidate_id = model.get("candidate_id")
        local_path = model.get("local_path")
        if not isinstance(candidate_id, str) or not candidate_id:
            raise ArtifactError(
                f"download manifest model {index} requires a non-empty candidate_id"
            )
        if not isinstance(local_path, str) or not local_path:
            raise ArtifactError(
                f"download manifest model {index} requires a non-empty local_path"
            )
        if candidate_id in model_paths:
            raise ArtifactError(
                f"download manifest contains duplicate candidate_id {candidate_id!r}"
            )
        model_paths[candidate_id] = Path(local_path)
    return model_paths
