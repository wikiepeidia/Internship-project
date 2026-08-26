"""Security and publication tests for the Phase 40 Plan 06 review consumer."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from src.model_adaptation import phase40_review


def _fixed_review_path(repo: Path, relative: str) -> Path:
    path = repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def test_review_regular_reader_rejects_hardlinked_authority(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    canonical = _fixed_review_path(
        repo, "data/models/phase40/comparison-manifest.json"
    )
    source = tmp_path / "outside-comparison.json"
    source.write_bytes(b"{}\n")
    try:
        os.link(source, canonical)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"hardlinks unavailable: {exc}")

    with pytest.raises(ValueError, match="missing, unreadable, or unsafe"):
        phase40_review.load_canonical_phase40_comparison_manifest(
            repo_root=repo,
            comparison_manifest_path=canonical,
        )


def test_review_regular_reader_rejects_symlink_leaf(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    canonical = _fixed_review_path(
        repo, "data/models/phase40/comparison-manifest.json"
    )
    source = tmp_path / "outside-comparison.json"
    source.write_bytes(b"{}\n")
    try:
        canonical.symlink_to(source)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"file symlinks unavailable: {exc}")

    with pytest.raises(ValueError, match="missing, unreadable, or unsafe"):
        phase40_review.load_canonical_phase40_comparison_manifest(
            repo_root=repo,
            comparison_manifest_path=canonical,
        )


def test_review_output_root_rejects_redirecting_ancestor(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    phase40_root = repo / "data/models/phase40"
    phase40_root.mkdir(parents=True)
    outside = tmp_path / "outside-review"
    outside.mkdir()
    review_root = phase40_root / "review"
    try:
        review_root.symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"directory symlinks unavailable: {exc}")

    with pytest.raises(ValueError, match="output root is missing, unreadable, or unsafe"):
        phase40_review.canonical_phase40_review_output_root(
            repo_root=repo,
            supplied_root=review_root,
        )


def test_review_output_preflight_rejects_same_byte_symlink(tmp_path: Path) -> None:
    target = tmp_path / "outside-notes.jsonl"
    target.write_bytes(b"{}\n")
    leaf = tmp_path / "human-review-notes.jsonl"
    try:
        leaf.symlink_to(target)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"file symlinks unavailable: {exc}")

    with pytest.raises(ValueError, match="missing, unreadable, or unsafe"):
        phase40_review._preflight_review_output_leaf(
            leaf,
            description="human-review notes",
        )
