"""Security and publication tests for the Phase 40 Plan 06 review consumer."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from src.model_adaptation import phase40_review
from src.model_adaptation.phase40_handoff import HumanReviewArtifacts


def _fixed_review_path(repo: Path, relative: str) -> Path:
    path = repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _review_artifacts(root: Path) -> HumanReviewArtifacts:
    root.mkdir(parents=True)
    return HumanReviewArtifacts(
        notes_path=root / "human-review-notes.jsonl",
        manifest_path=root / "human-review-manifest.json",
        report_path=root / "human-review-report.md",
    )


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


def test_review_publication_promotes_manifest_last(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    artifacts = _review_artifacts(tmp_path / "review")
    promoted: list[str] = []
    real_promote = phase40_review._promote_review_file

    def record(staged: Path, destination: Path) -> None:
        promoted.append(destination.name)
        real_promote(staged, destination)

    monkeypatch.setattr(phase40_review, "_promote_review_file", record)
    phase40_review._publish_human_review_artifacts(
        artifacts,
        notes_bytes=b"notes\n",
        report_bytes=b"report\n",
        manifest_bytes=b"manifest\n",
    )

    assert promoted == [
        "human-review-notes.jsonl",
        "human-review-report.md",
        "human-review-manifest.json",
    ]
    assert artifacts.notes_path.read_bytes() == b"notes\n"
    assert artifacts.report_path.read_bytes() == b"report\n"
    assert artifacts.manifest_path.read_bytes() == b"manifest\n"


@pytest.mark.parametrize("failed_promotion", (0, 1, 2))
def test_review_publication_failure_never_leaves_completion_marker_and_retries(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failed_promotion: int,
) -> None:
    artifacts = _review_artifacts(tmp_path / f"review-{failed_promotion}")
    real_promote = phase40_review._promote_review_file
    calls = 0

    def fail_once(staged: Path, destination: Path) -> None:
        nonlocal calls
        current = calls
        calls += 1
        if current == failed_promotion:
            raise OSError("injected promotion failure")
        real_promote(staged, destination)

    with monkeypatch.context() as patch:
        patch.setattr(phase40_review, "_promote_review_file", fail_once)
        with pytest.raises(OSError, match="injected promotion failure"):
            phase40_review._publish_human_review_artifacts(
                artifacts,
                notes_bytes=b"notes\n",
                report_bytes=b"report\n",
                manifest_bytes=b"manifest\n",
            )

    assert not os.path.lexists(artifacts.manifest_path)
    phase40_review._publish_human_review_artifacts(
        artifacts,
        notes_bytes=b"notes\n",
        report_bytes=b"report\n",
        manifest_bytes=b"manifest\n",
    )
    assert artifacts.notes_path.read_bytes() == b"notes\n"
    assert artifacts.report_path.read_bytes() == b"report\n"
    assert artifacts.manifest_path.read_bytes() == b"manifest\n"


def test_review_publication_preflights_all_destinations_before_side_changes(
    tmp_path: Path,
) -> None:
    artifacts = _review_artifacts(tmp_path / "review-conflict")
    artifacts.notes_path.write_bytes(b"notes\n")
    artifacts.report_path.write_bytes(b"conflicting report\n")
    artifacts.manifest_path.write_bytes(b"stale completion\n")

    with pytest.raises(RuntimeError, match="side artifact conflicts"):
        phase40_review._publish_human_review_artifacts(
            artifacts,
            notes_bytes=b"notes\n",
            report_bytes=b"report\n",
            manifest_bytes=b"manifest\n",
        )

    assert artifacts.notes_path.read_bytes() == b"notes\n"
    assert artifacts.report_path.read_bytes() == b"conflicting report\n"
    assert not os.path.lexists(artifacts.manifest_path)


def test_review_publication_migrates_one_exact_prior_manifest(tmp_path: Path) -> None:
    artifacts = _review_artifacts(tmp_path / "review-migration")
    artifacts.notes_path.write_bytes(b"notes\n")
    artifacts.report_path.write_bytes(b"report\n")
    artifacts.manifest_path.write_bytes(b"legacy manifest\n")

    phase40_review._publish_human_review_artifacts(
        artifacts,
        notes_bytes=b"notes\n",
        report_bytes=b"report\n",
        manifest_bytes=b"v3 manifest\n",
        accepted_prior_manifest_bytes=(b"legacy manifest\n",),
    )

    assert artifacts.notes_path.read_bytes() == b"notes\n"
    assert artifacts.report_path.read_bytes() == b"report\n"
    assert artifacts.manifest_path.read_bytes() == b"v3 manifest\n"
