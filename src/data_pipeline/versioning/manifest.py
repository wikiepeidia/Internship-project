"""Manifest generation and integrity verification for dataset builds."""

from __future__ import annotations

import hashlib
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from src.data_pipeline.schemas import ManifestEntry, ManifestFile


def build_manifest(data_dir: Path, version_tag: str) -> ManifestEntry:
    """Build a SHA256 manifest for every JSONL file under a dataset directory."""
    git_commit = None
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            cwd=str(data_dir),
            check=False,
        )
        if result.returncode == 0:
            git_commit = result.stdout.strip()
    except FileNotFoundError:
        git_commit = None

    manifest = ManifestEntry(
        version=version_tag,
        build_timestamp=datetime.now(timezone.utc).isoformat(),
        git_commit=git_commit,
        files={},
    )

    for jsonl_file in sorted(data_dir.rglob("*.jsonl")):
        manifest.files[str(jsonl_file.relative_to(data_dir))] = ManifestFile(
            sha256=hashlib.sha256(jsonl_file.read_bytes()).hexdigest(),
            records=sum(1 for line in jsonl_file.open(encoding="utf-8") if line.strip()),
            bytes=jsonl_file.stat().st_size,
        )

    return manifest


def verify_manifest(manifest: ManifestEntry, data_dir: Path) -> tuple[bool, list[str]]:
    """Verify that every file in a manifest still exists and matches its recorded hash."""
    errors: list[str] = []

    for relative_path, file_info in manifest.files.items():
        file_path = data_dir / relative_path
        if not file_path.exists():
            errors.append(f"Missing file: {relative_path}")
            continue

        actual_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()
        if actual_hash != file_info.sha256:
            errors.append(
                f"Hash mismatch for {relative_path}: expected {file_info.sha256}, got {actual_hash}"
            )

    return len(errors) == 0, errors


def save_manifest(manifest: ManifestEntry, output_path: Path) -> Path:
    """Persist a manifest as formatted JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    return output_path