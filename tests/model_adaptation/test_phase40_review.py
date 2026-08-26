"""Security and publication tests for the Phase 40 Plan 06 review consumer."""

from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.model_adaptation import phase40_review
from src.model_adaptation import phase40_handoff as handoff
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


@pytest.fixture()
def v3_review_fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    source_repo = Path(__file__).resolve().parents[2]
    repo = tmp_path / "repo"
    fixed_files = (
        "data/models/phase40/comparison-manifest.json",
        "data/models/phase40/comparison-report.md",
        "data/models/phase40/review/review-queue.jsonl",
        "data/models/phase40/review/review-queue-manifest.json",
        "data/models/phase40/selected-prediction-bundles.json",
        "data/models/phase40/two-full-model-scope-amendment.json",
    )
    for relative in fixed_files:
        destination = repo / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((source_repo / relative).read_bytes())

    comparison_path = repo / "data/models/phase40/comparison-manifest.json"
    amendment_bytes = (
        repo / "data/models/phase40/two-full-model-scope-amendment.json"
    ).read_bytes()
    amendment_sha256 = handoff._sha256(amendment_bytes)
    comparison = handoff.Phase40ComparisonManifest.model_validate_json(
        comparison_path.read_text(encoding="utf-8")
    )
    comparison = comparison.model_copy(
        update={
            "scope_amendment_sha256": amendment_sha256,
            "superseded_scope_amendment_sha256": amendment_sha256,
        }
    )
    comparison_bytes = handoff._canonical_json_bytes(
        comparison.model_dump(mode="json")
    )
    comparison_path.write_bytes(comparison_bytes)
    comparison_path.with_name("comparison-report.md").write_bytes(
        handoff._comparison_report(comparison)
    )
    queue_path = repo / "data/models/phase40/review/review-queue.jsonl"
    queue = tuple(
        handoff.ReviewQueueRow.model_validate_json(line)
        for line in queue_path.read_text(encoding="utf-8").splitlines()
    )
    reviews = tuple(
        handoff.ReviewerReturnRow(
            **row.model_dump(mode="json"),
            assessment="prediction_supported",
            mechanism_note_vi="Đã đối chiếu đầy đủ ngữ cảnh của hàng đánh giá.",
            shortcut_pattern_note_vi=None,
        )
        for row in queue
    )
    reviewer_bytes = handoff._review_jsonl(reviews)
    selected_bytes = (
        repo / "data/models/phase40/selected-prediction-bundles.json"
    ).read_bytes()
    queue_manifest = handoff.ReviewQueueManifest.model_validate_json(
        (
            repo / "data/models/phase40/review/review-queue-manifest.json"
        ).read_text(encoding="utf-8")
    )
    queue_manifest = queue_manifest.model_copy(
        update={
            "comparison_manifest_sha256": handoff._sha256(comparison_bytes)
        }
    )
    (
        repo / "data/models/phase40/review/review-queue-manifest.json"
    ).write_bytes(
        handoff._canonical_json_bytes(queue_manifest.model_dump(mode="json"))
    )
    request = SimpleNamespace(
        input_bundle=SimpleNamespace(
            archive_sha256=comparison.input_archive_sha256,
            manifest_sha256=comparison.input_manifest_sha256,
            data_members=(
                SimpleNamespace(records=1),
                SimpleNamespace(records=comparison.validation_rows),
            ),
        )
    )
    contract = SimpleNamespace(
        validation_snapshot=SimpleNamespace(
            rows=tuple(range(comparison.validation_rows))
        )
    )
    final = SimpleNamespace(
        authority=SimpleNamespace(
            lora_probe_authority=object(),
            execution_policy=comparison.execution_policy,
        ),
        authority_sha256=comparison.final_comparison_authority_sha256,
        historical_scope_amendment=SimpleNamespace(
            full_lora_disposition=comparison.full_lora_disposition,
        ),
        runs=(
            SimpleNamespace(
                origin=SimpleNamespace(
                    request_sha256=comparison.original_run_request_sha256
                )
            ),
            SimpleNamespace(origin=SimpleNamespace(request_sha256="f" * 64)),
        ),
    )
    monkeypatch.setattr(
        handoff,
        "require_canonical_phase40_run_request",
        lambda request, **kwargs: request,
    )
    monkeypatch.setattr(
        phase40_review,
        "load_phase40_review_authority",
        lambda **kwargs: (final, amendment_bytes),
    )
    monkeypatch.setattr(
        phase40_review,
        "verify_phase40_final_review_comparison",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        phase40_review,
        "_reverify_model_bundles",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        handoff,
        "verify_phase40_review_queue",
        lambda rows, **kwargs: tuple(rows),
    )
    monkeypatch.setattr(
        handoff,
        "verify_lora_probe_authority",
        lambda *args, **kwargs: comparison.lora_probe,
    )
    monkeypatch.setattr(
        handoff,
        "_selected_prediction_bundles_bytes",
        lambda bundles: selected_bytes,
    )
    monkeypatch.setattr(
        handoff,
        "_contract_identity",
        lambda value: queue_manifest.phase39_data_contract_sha256,
    )
    monkeypatch.setattr(
        handoff,
        "_ordered_row_ids_sha256",
        lambda value: queue_manifest.validation_ordered_row_ids_sha256,
    )
    output_root = repo / "data/models/phase40/review"
    return SimpleNamespace(
        repo=repo,
        comparison=comparison,
        comparison_path=comparison_path,
        queue_manifest_path=(
            repo / "data/models/phase40/review/review-queue-manifest.json"
        ),
        scope_path=(
            repo / "data/models/phase40/two-full-model-scope-amendment.json"
        ),
        output_root=output_root,
        request=request,
        contract=contract,
        queue=queue,
        queue_bytes=queue_path.read_bytes(),
        reviews=reviews,
        reviewer_bytes=reviewer_bytes,
        prediction_bundles=(object(), object()),
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
        with pytest.raises(RuntimeError, match="publication failed before completion"):
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


def _finalize_v3_fixture(fixture, *, reviews=None, reviewer_bytes=None, verify_only=False):
    return phase40_review.finalize_phase40_human_review(
        fixture.queue,
        fixture.reviews if reviews is None else reviews,
        request=fixture.request,
        repo_root=fixture.repo,
        contract=fixture.contract,
        prediction_bundles=fixture.prediction_bundles,
        queue_manifest_path=fixture.queue_manifest_path,
        comparison_manifest_path=fixture.comparison_path,
        scope_amendment_path=fixture.scope_path,
        output_root=fixture.output_root,
        queue_bytes=fixture.queue_bytes,
        reviewer_return_bytes=(
            fixture.reviewer_bytes if reviewer_bytes is None else reviewer_bytes
        ),
        vietnamese_fluent_attestation=True,
        verify_only=verify_only,
    )


def test_v3_finalizer_publishes_and_verify_only_replays_exact_closure(
    v3_review_fixture,
) -> None:
    artifacts = _finalize_v3_fixture(v3_review_fixture)
    manifest = handoff._strict_json_object(
        artifacts.manifest_path.read_bytes(),
        description="v3 review manifest",
    )

    assert manifest["schema_version"] == "phase40-human-review-v3"
    assert manifest["superseded_scope_amendment_sha256"] == (
        v3_review_fixture.comparison.superseded_scope_amendment_sha256
    )
    assert manifest["final_comparison_authority_sha256"] == (
        v3_review_fixture.comparison.final_comparison_authority_sha256
    )
    before = tuple(
        path.read_bytes()
        for path in (
            artifacts.notes_path,
            artifacts.report_path,
            artifacts.manifest_path,
        )
    )
    assert _finalize_v3_fixture(v3_review_fixture, verify_only=True) == artifacts
    assert tuple(
        path.read_bytes()
        for path in (
            artifacts.notes_path,
            artifacts.report_path,
            artifacts.manifest_path,
        )
    ) == before


def test_v3_finalizer_migrates_the_exact_misversioned_v2_manifest(
    v3_review_fixture,
) -> None:
    artifacts = _finalize_v3_fixture(v3_review_fixture)
    manifest = handoff._strict_json_object(
        artifacts.manifest_path.read_bytes(),
        description="v3 review manifest",
    )
    manifest["schema_version"] = "phase40-human-review-v2"
    artifacts.manifest_path.write_bytes(handoff._canonical_json_bytes(manifest))

    replayed = _finalize_v3_fixture(v3_review_fixture)
    migrated = handoff._strict_json_object(
        replayed.manifest_path.read_bytes(),
        description="migrated review manifest",
    )

    assert migrated["schema_version"] == "phase40-human-review-v3"
    assert "superseded_scope_amendment_sha256" in migrated
    assert "final_comparison_authority_sha256" in migrated


@pytest.mark.parametrize("malformation", ("missing", "duplicate", "reordered"))
def test_v3_finalizer_rejects_inexact_reviewer_coverage(
    v3_review_fixture,
    malformation: str,
) -> None:
    if malformation == "missing":
        reviews = v3_review_fixture.reviews[:-1]
    elif malformation == "duplicate":
        reviews = (*v3_review_fixture.reviews[:-1], v3_review_fixture.reviews[0])
    else:
        reviews = tuple(reversed(v3_review_fixture.reviews))
    reviewer_bytes = handoff._review_jsonl(reviews)

    with pytest.raises(ValueError, match="cover every queue key"):
        _finalize_v3_fixture(
            v3_review_fixture,
            reviews=reviews,
            reviewer_bytes=reviewer_bytes,
        )
