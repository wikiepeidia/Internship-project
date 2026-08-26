"""Plan 06 consumer for the frozen Phase 40 comparison and review queue.

The Plan 05 comparison runtime is immutable upstream provenance at this point.
This module re-verifies its canonical authority document, request roots, and
per-run identities without claiming that the current repository can rerun the
already-completed comparison from the same source bytes.
"""

from __future__ import annotations

import os
from pathlib import Path, PurePosixPath
import stat
from typing import Sequence

from src.model_adaptation import phase40_final_authority as _final
from src.model_adaptation import phase40_handoff as _handoff


FIXED_COMPARISON_MANIFEST_PATH = PurePosixPath(
    "data/models/phase40/comparison-manifest.json"
)


def _canonical_review_path(
    *,
    repo_root: Path,
    supplied_path: Path,
    expected_relative: PurePosixPath,
    description: str,
) -> Path:
    """Return one code-fixed Phase 40 review path without resolving redirects."""

    root = _handoff._trusted_repo_root(repo_root)
    expected = _handoff._lexical_absolute(root / expected_relative)
    supplied = Path(supplied_path)
    if not supplied.is_absolute():
        supplied = root / supplied
    candidate = _handoff._lexical_absolute(supplied)
    if os.path.normcase(os.fspath(candidate)) != os.path.normcase(
        os.fspath(expected)
    ):
        raise ValueError(f"{description} path is not the code-fixed authority")
    return expected


def _regular_file_identity(metadata: os.stat_result) -> tuple[object, ...]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_nlink,
        metadata.st_size,
        metadata.st_mtime_ns,
    )


def read_phase40_review_regular_bytes(path: Path, *, description: str) -> bytes:
    """Read one non-redirecting, single-link regular file through a stable handle."""

    candidate = _handoff._lexical_absolute(Path(path))
    try:
        _handoff._reject_redirecting_path_components((candidate,))
        lexical_metadata = os.lstat(candidate)
        if (
            not stat.S_ISREG(lexical_metadata.st_mode)
            or stat.S_ISLNK(lexical_metadata.st_mode)
            or lexical_metadata.st_nlink != 1
        ):
            raise ValueError(f"{description} is not a single-link regular file")
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
        flags |= getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(candidate, flags)
        try:
            before = os.fstat(descriptor)
            if (
                not stat.S_ISREG(before.st_mode)
                or before.st_nlink != 1
                or _regular_file_identity(before)
                != _regular_file_identity(lexical_metadata)
            ):
                raise ValueError(f"{description} changed before it was opened")
            with os.fdopen(descriptor, "rb", closefd=False) as handle:
                payload = handle.read()
            after = os.fstat(descriptor)
        finally:
            os.close(descriptor)
        final_metadata = os.lstat(candidate)
        if (
            _regular_file_identity(before) != _regular_file_identity(after)
            or _regular_file_identity(after)
            != _regular_file_identity(final_metadata)
        ):
            raise ValueError(f"{description} changed while it was read")
        return payload
    except ValueError:
        raise
    except OSError as exc:
        raise ValueError(f"{description} is missing, unreadable, or unsafe") from exc


def load_canonical_phase40_comparison_manifest(
    *, repo_root: Path, comparison_manifest_path: Path
) -> tuple[_handoff.Phase40ComparisonManifest, bytes]:
    """Load the exact code-fixed comparison with strict, canonical JSON bytes."""

    path = _canonical_review_path(
        repo_root=repo_root,
        supplied_path=comparison_manifest_path,
        expected_relative=FIXED_COMPARISON_MANIFEST_PATH,
        description="comparison manifest",
    )
    payload = read_phase40_review_regular_bytes(
        path, description="comparison manifest"
    )
    manifest = _handoff.Phase40ComparisonManifest.model_validate(
        _handoff._strict_json_object(payload, description="comparison manifest")
    )
    if payload != _handoff._canonical_json_bytes(manifest.model_dump(mode="json")):
        raise ValueError("comparison manifest is not canonical JSON")
    return manifest, payload


def _load_frozen_upstream_authority(
    *, repo_root: Path
) -> _final.VerifiedPhase40FinalComparisonAuthority:
    (
        root,
        original_bytes,
        original,
        recovery_bytes,
        recovery,
        amendment_bytes,
        amendment,
    ) = _final._authority_components(repo_root=repo_root)
    path = _final._authority_path(root, must_exist=True)
    payload = path.read_bytes()
    authority = _final.Phase40FinalComparisonAuthority.model_validate(
        _final._strict_json_object(payload, where="final Phase 40 comparison authority")
    )
    if payload != _final._canonical_json_bytes(authority.model_dump(mode="json")):
        raise ValueError("final Phase 40 comparison authority bytes are not canonical JSON")

    request_hashes = tuple(
        entry.request_sha256 for entry in authority.request_authorities
    )
    if request_hashes != (
        _final._sha256(original_bytes),
        _final._sha256(recovery_bytes),
    ):
        raise ValueError("final authority request hashes differ from the two fixed roots")
    if authority.superseded_scope_amendment.sha256 != _final._sha256(
        amendment_bytes
    ):
        raise ValueError("final authority historical scope-amendment hash mismatch")
    if authority.shared_input_authority != original.input_bundle:
        raise ValueError("final authority shared input differs from the two requests")
    if original.input_bundle != recovery.input_bundle:
        raise ValueError("original and recovery requests do not share the exact input authority")
    if (
        authority.waived_full_run_id != amendment.waived_full_run_id
        or authority.waiver_action != amendment.waiver_action
        or authority.lora_probe_authority != amendment.lora_probe_authority
    ):
        raise ValueError("final authority changed the historical LoRA waiver or probe")

    requests = {
        _final.ORIGINAL_REQUEST_AUTHORITY_ID: original,
        _final.RECOVERY_REQUEST_AUTHORITY_ID: recovery,
    }
    origins = {
        entry.authority_id: entry for entry in authority.request_authorities
    }
    resolved: list[_final.ResolvedRunAuthority] = []
    for selection in authority.selected_runs:
        request = requests[selection.request_authority_id]
        requested = _final._by_run_id(request).get(selection.requested_run_id)
        if requested is None or requested.run_id != selection.run_id:
            raise ValueError(
                f"selected run is absent from its origin request: {selection.run_id}"
            )
        if requested.returned_root != selection.returned_root:
            raise ValueError(
                f"selected returned root differs from its request: {selection.run_id}"
            )
        template = request.control_template_by_run[selection.requested_run_id]
        if (
            request.control_template_digest_by_run[selection.requested_run_id]
            != template.sha256
        ):
            raise ValueError(f"selected template digest mismatch: {selection.run_id}")
        resolved.append(
            _final.ResolvedRunAuthority(
                run_id=selection.run_id,
                origin=origins[selection.request_authority_id],
                origin_request=request,
                requested_run=requested,
                control_template=template,
                transfer_authority=_handoff.transfer_authority_from_request(request),
            )
        )

    verified = _final.VerifiedPhase40FinalComparisonAuthority(
        authority=authority,
        authority_sha256=_final._sha256(payload),
        historical_scope_amendment=amendment,
        original_request=original,
        recovery_request=recovery,
        runs=(resolved[0], resolved[1]),
    )
    if verified.authority_sha256 != _final._sha256(payload):
        raise RuntimeError("final comparison authority changed during review loading")
    return verified


def load_phase40_review_authority(
    *,
    repo_root: Path,
    request: _handoff.RunRequest,
    scope_amendment_path: Path,
) -> tuple[_final.VerifiedPhase40FinalComparisonAuthority, bytes]:
    """Authenticate Plan 05 as frozen upstream provenance for Plan 06."""

    root = _handoff._trusted_repo_root(repo_root)
    canonical_request = _handoff.require_canonical_phase40_run_request(
        request,
        repo_root=root,
    )
    verified = _load_frozen_upstream_authority(repo_root=root)
    if canonical_request != verified.original_request:
        raise ValueError("review request differs from the final comparison authority")

    expected = _final._fixed_regular_file(
        root,
        _final.FIXED_HISTORICAL_SCOPE_AMENDMENT_PATH,
        where="historical Phase 40 scope amendment",
    )
    supplied = Path(
        os.path.abspath(os.path.normpath(os.fspath(scope_amendment_path)))
    )
    _handoff._reject_redirecting_path_components((supplied,))
    if supplied != expected or not supplied.is_file() or supplied.is_symlink():
        raise ValueError("historical scope amendment path is not the canonical regular file")
    scope_bytes = supplied.read_bytes()
    if _handoff._sha256(scope_bytes) != (
        verified.authority.superseded_scope_amendment.sha256
    ):
        raise ValueError("historical scope amendment hash differs from final authority")
    return verified, scope_bytes


def verify_phase40_final_review_comparison(
    comparison: _handoff.Phase40ComparisonManifest,
    *,
    final_authority: _final.VerifiedPhase40FinalComparisonAuthority,
    scope_amendment_bytes: bytes,
) -> None:
    """Bind the review input to the exact v3 manifest and per-run origins."""

    typed = (
        comparison
        if isinstance(comparison, _handoff.Phase40ComparisonManifest)
        else _handoff.Phase40ComparisonManifest.model_validate(comparison)
    )
    if typed.schema_version != _handoff.PHASE40_COMPARISON_SCHEMA_VERSION:
        raise ValueError("final review authority requires a v3 comparison manifest")
    if not isinstance(scope_amendment_bytes, bytes):
        raise TypeError("historical scope amendment provenance must be bytes")
    authority = final_authority.authority
    resolutions = tuple(final_authority.runs)
    run_ids = tuple(resolution.run_id for resolution in resolutions)
    historical_sha256 = authority.superseded_scope_amendment.sha256
    expected_request_hashes = {
        resolution.run_id: resolution.origin.request_sha256
        for resolution in resolutions
    }
    expected_source_archives = {
        resolution.run_id: resolution.origin_request.source_bundle.archive_sha256
        for resolution in resolutions
    }
    expected_source_inventories = {
        resolution.run_id: resolution.origin_request.source_bundle.inventory_sha256
        for resolution in resolutions
    }
    if (
        _handoff._sha256(scope_amendment_bytes) != historical_sha256
        or typed.scope_amendment_sha256 != historical_sha256
        or typed.superseded_scope_amendment_sha256 != historical_sha256
        or typed.final_comparison_authority_sha256
        != final_authority.authority_sha256
        or typed.original_run_request_sha256
        != resolutions[0].origin.request_sha256
        or typed.comparison_finalizer_source_sha256
        != authority.comparison_finalizer_authority.source_tree_sha256
        or tuple(run.run_id for run in typed.runs) != run_ids
        or authority.review_model_run_ids != run_ids
        or typed.request_sha256_by_run != expected_request_hashes
        or typed.source_archive_sha256_by_run != expected_source_archives
        or typed.source_inventory_sha256_by_run != expected_source_inventories
        or typed.input_archive_sha256
        != authority.shared_input_authority.archive_sha256
        or typed.input_manifest_sha256
        != authority.shared_input_authority.manifest_sha256
        or typed.lora_probe.evidence_authority_sha256
        != authority.lora_probe_authority.sha256
    ):
        raise ValueError("review comparison differs from the final comparison authority")
    for record, resolution in zip(typed.runs, resolutions, strict=True):
        if (
            record.returned_root != resolution.requested_run.returned_root
            or record.origin_request_sha256 != resolution.origin.request_sha256
            or record.source_archive_sha256
            != resolution.origin_request.source_bundle.archive_sha256
            or record.source_inventory_sha256
            != resolution.origin_request.source_bundle.inventory_sha256
            or record.control_template_sha256 != resolution.control_template.sha256
        ):
            raise ValueError(
                f"review comparison run origin differs from final authority: {record.run_id}"
            )


def _reverify_model_bundles(
    comparison: _handoff.Phase40ComparisonManifest,
    *,
    final_authority: _final.VerifiedPhase40FinalComparisonAuthority,
    repo_root: Path,
    contract: object,
    prediction_bundles: Sequence[_handoff.SelectedPredictionBundle],
) -> None:
    root = _handoff._trusted_repo_root(repo_root)
    final_by_id = dict(final_authority.by_run_id)
    bundles = tuple(prediction_bundles)
    if tuple(bundle.model_run_id for bundle in bundles) != tuple(
        run.run_id for run in comparison.runs
    ):
        raise ValueError("human-review prediction-bundle order differs from comparison")
    for record, bundle in zip(comparison.runs, bundles, strict=True):
        resolution = final_by_id.get(record.run_id)
        if resolution is None or record.returned_root != (
            resolution.requested_run.returned_root
        ):
            raise ValueError("comparison run root differs from the final authority")
        run_root = _handoff._lexical_absolute(
            root / PurePosixPath(record.returned_root)
        )
        try:
            run_root.relative_to(root)
        except ValueError as exc:
            raise ValueError("comparison run root escaped the repository") from exc
        _handoff._reject_redirecting_path_components((run_root,))
        if not run_root.is_dir() or run_root.is_symlink():
            raise ValueError("comparison run root is missing or unsafe")
        for required in resolution.origin_request.expected_bundle_files:
            required_path = run_root / PurePosixPath(required)
            if (
                not required_path.exists()
                or required_path.is_symlink()
                or (required_path.is_file() and required_path.stat().st_size == 0)
            ):
                raise ValueError(
                    f"comparison run required evidence is missing: {record.run_id}/{required}"
                )

        evidence = _handoff.verify_phase40_bundle(run_root)
        if _handoff.build_model_checksum(run_root / "run-evidence.json") != (
            record.evidence_sha256
        ):
            raise ValueError("comparison run-evidence hash drifted before human review")
        identity = evidence.experiment_identity
        requested = resolution.requested_run
        if (
            evidence.status != _handoff.EvidenceStatus.COMPLETE
            or evidence.run_kind != _handoff.RunKind.FULL
            or evidence.run_id != record.run_id
            or evidence.transfer_authority != resolution.transfer_authority
            or identity.model_family != record.model_family
            or identity.adaptation_mode != record.adaptation_mode
            or identity.run_kind != _handoff.RunKind.FULL
            or identity.model_family != requested.model_family
            or identity.adaptation_mode != requested.adaptation_mode
        ):
            raise ValueError("comparison run identity drifted before human review")

        config = _handoff._load_resume_config(run_root, evidence)
        resolution.control_template.verify_runtime_config(config)
        if (
            evidence.model_revision != config.model_revision
            or config.accelerator.accelerator_name != record.gpu_identity
        ):
            raise ValueError("comparison model/config/GPU identity drifted")
        for split, member in zip(
            evidence.splits,
            resolution.origin_request.input_bundle.data_members,
            strict=True,
        ):
            if (
                split.logical_name != member.logical_name
                or split.records != member.records
                or split.bytes != member.bytes
                or split.sha256 != member.sha256
                or split.ordered_row_ids_sha256 != member.ordered_row_ids_sha256
            ):
                raise ValueError("comparison split identity drifted before human review")

        recomputed_selection, recomputed_metrics = (
            _handoff._recompute_checkpoint_selection(
                run_root,
                evidence,
                contract.validation_snapshot,
            )
        )
        retained_bundle = _handoff._load_selected_prediction_bundle(
            run_root, evidence
        )
        _handoff._prediction_by_snapshot(
            retained_bundle, contract.validation_snapshot
        )
        if retained_bundle != bundle:
            raise ValueError("selected prediction bundle drifted before human review")
        selected = evidence.selected_checkpoint
        if selected is None:
            raise ValueError("selected checkpoint is missing before human review")
        selected_metrics = recomputed_metrics[
            (
                recomputed_selection.selected_step,
                recomputed_selection.selected_artifact_identity,
            )
        ]
        risky_recall = {
            label: next(
                row.recall
                for row in selected_metrics.per_class
                if row.label == label
            )
            for label in _handoff.RISKY_RECALL_FLOORS
        }
        expected_tool_pins = {
            "matplotlib": next(iter(evidence.graph_provenance)).renderer_version
        }
        if identity.adaptation_mode == _handoff.AdaptationMode.QLORA:
            if evidence.quantization is None:
                raise ValueError("QLoRA quantization proof is missing before human review")
            expected_tool_pins["bitsandbytes"] = (
                evidence.quantization.bitsandbytes_version
            )
        if (
            record.resume_digest != evidence.resume_digest
            or record.selected_checkpoint_identity != selected.artifact_identity
            or record.selected_optimizer_step != selected.optimizer_step
            or record.safety_gate_passed != selected.safety_gate_passed
            or record.comparison_eligible != evidence.comparison_eligible
            or record.validation_rows != len(retained_bundle.predictions)
            or record.validation_metrics != evidence.validation_metrics
            or not _handoff._run_metric_summary_matches(evidence, selected_metrics)
            or record.macro_f1 != selected_metrics.macro_f1
            or record.invalid_output_count != selected_metrics.invalid_output_count
            or record.risky_recall_by_label != risky_recall
            or record.package_versions != evidence.package_versions
            or record.required_tool_pins != expected_tool_pins
        ):
            raise ValueError("comparison metrics/safety/tool evidence drifted before human review")


def finalize_phase40_human_review(
    queue_rows: Sequence[_handoff.ReviewQueueRow],
    reviewer_rows: Sequence[_handoff.ReviewerReturnRow],
    *,
    request: _handoff.RunRequest,
    repo_root: Path,
    contract: object,
    prediction_bundles: Sequence[_handoff.SelectedPredictionBundle],
    queue_manifest_path: Path,
    comparison_manifest_path: Path,
    scope_amendment_path: Path,
    output_root: Path,
    queue_bytes: bytes,
    reviewer_return_bytes: bytes,
    vietnamese_fluent_attestation: bool,
    verify_only: bool = False,
) -> _handoff.HumanReviewArtifacts:
    comparison_bytes = Path(comparison_manifest_path).read_bytes()
    comparison = _handoff.Phase40ComparisonManifest.model_validate(
        _handoff._strict_json_object(
            comparison_bytes, description="comparison manifest"
        )
    )
    if comparison.schema_version != _handoff.PHASE40_COMPARISON_SCHEMA_VERSION:
        return _handoff.finalize_phase40_human_review(
            queue_rows,
            reviewer_rows,
            request=request,
            repo_root=repo_root,
            contract=contract,
            prediction_bundles=prediction_bundles,
            queue_manifest_path=queue_manifest_path,
            comparison_manifest_path=comparison_manifest_path,
            scope_amendment_path=scope_amendment_path,
            output_root=output_root,
            queue_bytes=queue_bytes,
            reviewer_return_bytes=reviewer_return_bytes,
            vietnamese_fluent_attestation=vietnamese_fluent_attestation,
            verify_only=verify_only,
        )
    canonical_request = _handoff.require_canonical_phase40_run_request(
        request,
        repo_root=repo_root,
    )
    if comparison_bytes != _handoff._canonical_json_bytes(
        comparison.model_dump(mode="json")
    ):
        raise ValueError("comparison manifest is not canonical JSON")
    if comparison.status != "complete":
        raise ValueError("human review requires a complete comparison manifest")
    final, amendment_bytes = load_phase40_review_authority(
        repo_root=repo_root,
        request=canonical_request,
        scope_amendment_path=scope_amendment_path,
    )
    verify_phase40_final_review_comparison(
        comparison,
        final_authority=final,
        scope_amendment_bytes=amendment_bytes,
    )
    if vietnamese_fluent_attestation is not True:
        raise ValueError("human review requires a Vietnamese-fluent reviewer attestation")

    queue = tuple(
        row
        if isinstance(row, _handoff.ReviewQueueRow)
        else _handoff.ReviewQueueRow.model_validate(row)
        for row in queue_rows
    )
    _handoff.verify_phase40_review_queue(
        queue,
        contract=contract,
        prediction_bundles=prediction_bundles,
    )
    canonical_queue_bytes = _handoff._queue_jsonl(queue)
    if not isinstance(queue_bytes, bytes) or queue_bytes != canonical_queue_bytes:
        raise ValueError(
            "original review-queue bytes are not canonical or differ from parsed queue rows"
        )
    reviews = tuple(
        row
        if isinstance(row, _handoff.ReviewerReturnRow)
        else _handoff.ReviewerReturnRow.model_validate(row)
        for row in reviewer_rows
    )
    if _handoff._reviewer_rows_from_original_bytes(reviewer_return_bytes) != reviews:
        raise ValueError("original reviewer-return bytes differ from parsed reviewer rows")
    queue_keys = tuple(row.key for row in queue)
    review_keys = tuple(row.key for row in reviews)
    if len(set(queue_keys)) != len(queue_keys):
        raise ValueError("review queue contains duplicate model-row keys")
    if review_keys != queue_keys or len(set(review_keys)) != len(review_keys):
        raise ValueError("reviewer return must cover every queue key exactly in canonical order")
    if any(
        review.as_queue_row() != queue_row
        for queue_row, review in zip(queue, reviews, strict=True)
    ):
        raise ValueError("reviewer return immutable queue fields differ from the queue")

    notes_bytes = _handoff._review_jsonl(reviews)
    comparison_report_path = Path(comparison_manifest_path).with_name(
        "comparison-report.md"
    )
    if (
        not comparison_report_path.is_file()
        or comparison_report_path.is_symlink()
        or comparison_report_path.read_bytes()
        != _handoff._comparison_report(comparison)
    ):
        raise ValueError("comparison report differs from the frozen manifest")
    if (
        comparison.review_queue_rows != len(queue)
        or comparison.review_queue_sha256 != _handoff._sha256(queue_bytes)
    ):
        raise ValueError("human-review queue differs from the frozen comparison")

    authority = final.authority
    expected_lora_probe = _handoff.verify_lora_probe_authority(
        authority.lora_probe_authority,
        repo_root=repo_root,
    )
    expected_validation_rows = len(contract.validation_snapshot.rows)
    expected_hardware_confounded = len(
        {run.gpu_identity for run in comparison.runs}
    ) != 1
    if (
        comparison.original_run_request_sha256
        != final.runs[0].origin.request_sha256
        or comparison.input_archive_sha256
        != canonical_request.input_bundle.archive_sha256
        or comparison.input_manifest_sha256
        != canonical_request.input_bundle.manifest_sha256
        or expected_validation_rows
        != canonical_request.input_bundle.data_members[1].records
        or comparison.validation_rows != expected_validation_rows
        or comparison.lora_probe != expected_lora_probe
        or comparison.hardware_confounded != expected_hardware_confounded
        or comparison.limitations != _handoff.PHASE40_COMPARISON_LIMITATIONS
        or comparison.execution_policy != authority.execution_policy
        or comparison.full_lora_disposition
        != final.historical_scope_amendment.full_lora_disposition
    ):
        raise ValueError(
            "human review comparison provenance differs from frozen authorities"
        )
    _reverify_model_bundles(
        comparison,
        final_authority=final,
        repo_root=repo_root,
        contract=contract,
        prediction_bundles=prediction_bundles,
    )
    if (
        comparison.selected_prediction_bundles_sha256 is None
        or _handoff._sha256(
            _handoff._selected_prediction_bundles_bytes(prediction_bundles)
        )
        != comparison.selected_prediction_bundles_sha256
    ):
        raise ValueError("human-review predictions differ from the frozen comparison")

    queue_manifest_bytes = Path(queue_manifest_path).read_bytes()
    queue_manifest = _handoff.ReviewQueueManifest.model_validate(
        _handoff._strict_json_object(
            queue_manifest_bytes, description="review queue manifest"
        )
    )
    if queue_manifest_bytes != _handoff._canonical_json_bytes(
        queue_manifest.model_dump(mode="json")
    ):
        raise ValueError("review queue manifest is not canonical JSON")
    if (
        queue_manifest.rows != len(queue)
        or queue_manifest.queue_sha256 != _handoff._sha256(queue_bytes)
        or queue_manifest.reviewer_template_sha256
        != _handoff._sha256(_handoff._reviewer_template_jsonl(queue))
        or queue_manifest.comparison_manifest_sha256
        != _handoff._sha256(comparison_bytes)
        or queue_manifest.phase39_data_contract_sha256
        != _handoff._contract_identity(contract)
        or queue_manifest.validation_ordered_row_ids_sha256
        != _handoff._ordered_row_ids_sha256(contract.validation_snapshot)
    ):
        raise ValueError("review queue provenance differs from comparison/input authorities")

    pairs = tuple(zip(queue, reviews, strict=True))
    summary = _handoff._human_review_summary(pairs, comparison=comparison)
    report_bytes = _handoff._human_review_report(
        pairs,
        summary=summary,
        limitations=comparison.limitations,
    )
    manifest = {
        "schema_version": _handoff.PHASE40_HUMAN_REVIEW_SCHEMA_VERSION,
        "vietnamese_fluent_attestation": True,
        "rows": len(queue),
        "queue_sha256": _handoff._sha256(queue_bytes),
        "reviewer_return_sha256": _handoff._sha256(reviewer_return_bytes),
        "notes_sha256": _handoff._sha256(notes_bytes),
        "report_sha256": _handoff._sha256(report_bytes),
        "comparison_manifest_sha256": _handoff._sha256(comparison_bytes),
        "scope_amendment_sha256": _handoff._sha256(amendment_bytes),
        "superseded_scope_amendment_sha256": _handoff._sha256(amendment_bytes),
        "final_comparison_authority_sha256": final.authority_sha256,
        "review_queue_manifest_sha256": _handoff._sha256(queue_manifest_bytes),
        "phase39_data_contract_sha256": _handoff._contract_identity(contract),
        "validation_ordered_row_ids_sha256": _handoff._ordered_row_ids_sha256(
            contract.validation_snapshot
        ),
        "frozen_results_sha256": _handoff._sha256(
            _handoff._canonical_json_bytes(
                [
                    {
                        "model_run_id": row.model_run_id,
                        "validation_row_id": row.validation_row_id,
                        "gold_label": row.gold_label,
                        "predicted_label": row.predicted_label,
                        "selected_checkpoint_identity": row.selected_checkpoint_identity,
                        "model_artifact_identity": row.model_artifact_identity,
                    }
                    for row in queue
                ]
            )
        ),
        "summary": summary,
        "limitations": list(comparison.limitations),
    }
    manifest_bytes = _handoff._canonical_json_bytes(manifest)
    root = Path(output_root)
    artifacts = _handoff.HumanReviewArtifacts(
        root / "human-review-notes.jsonl",
        root / "human-review-manifest.json",
        root / "human-review-report.md",
    )
    payloads = (
        (artifacts.notes_path, notes_bytes),
        (artifacts.manifest_path, manifest_bytes),
        (artifacts.report_path, report_bytes),
    )
    if verify_only:
        for path, payload in payloads:
            if not path.is_file() or path.read_bytes() != payload:
                raise ValueError(f"human-review artifact verification failed: {path}")
        return artifacts
    for path, payload in payloads:
        _handoff._write_frozen_bytes(path, payload)
    return artifacts


__all__ = [
    "finalize_phase40_human_review",
    "load_phase40_review_authority",
    "verify_phase40_final_review_comparison",
]
