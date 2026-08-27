"""Synthetic integrity and artifact contracts for Phase 41.1 Plan 03."""

from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from src import artifacts
from src.core import integrity


REPO_ROOT = Path(__file__).parents[2]
SERIALIZATION_FIXTURE = Path(__file__).parent / "fixtures" / "serialization_contract.json"
PROTECTED_BASELINE = Path(__file__).parent / "fixtures" / "protected_authority_baseline.json"
HISTORICAL_HASHES = {
    "src/model_adaptation/training.py": (
        "59cea00005a6d0cd42183655610661ad1def981405480e1fc7d9fc3a538299a4"
    ),
    "src/model_adaptation/schemas.py": (
        "0641322680cc127af6eaf7909218d54df4b0c2d7a200a02eb04db0555f185bdb"
    ),
}
FORBIDDEN_ACTIVE_PREFIXES = ("src.artifacts", "src.modeling")


def _release_artifact(module: Any, temp_root: Path) -> Any:
    metrics = [
        module.PerLabelMetricRow(
            label=label,
            precision=0.9,
            recall=0.9,
            f1=0.9,
            support=1,
        )
        for label in module.LOCKED_RELEASE_LABELS
    ]
    audit = module.HeldOutSupportAudit(
        evaluated_split_path=temp_root / "synthetic-heldout.jsonl",
        support_by_label={label: 1 for label in module.LOCKED_RELEASE_LABELS},
    )
    return module.ReleaseEvaluationArtifact(
        run_id="synthetic-release",
        verdict="PASS",
        overall_metrics=module.OverallMetricSummary(
            macro_f1=0.9,
            weighted_f1=0.9,
            evaluated_rows=4,
        ),
        per_label_metrics=metrics,
        explanation_rubric_summary=module.ExplanationRubricSummary(
            evaluated_risky_predictions=3,
            manual_reviewed_predictions=3,
        ),
        readiness_audit=audit,
    )


def _normalize_temp_root(value: str, temp_root: Path) -> str:
    raw = os.fspath(temp_root)
    escaped = json.dumps(raw, ensure_ascii=False)[1:-1]
    return value.replace(escaped, "<TMP_ROOT>").replace(raw, "<TMP_ROOT>")


def _registry_payload() -> dict[str, Any]:
    return {
        "version_tag": "synthetic-v1",
        "selection": {
            "baseline_winner_id": "qwen3-4b-instruct-2507",
            "runner_up_id": "qwen3.5-4b",
            "selection_notes": "Synthetic registry contract",
        },
        "scorecards": [],
        "artifacts": [
            {
                "candidate_id": "qwen3-4b-instruct-2507",
                "artifact_type": "gguf",
                "version_tag": "synthetic-v1",
                "local_path": "synthetic/model.gguf",
                "sha256": "a" * 64,
                "tracked_in_git": False,
                "local_only": True,
                "profile_name": None,
            }
        ],
    }


def _strict_download_manifest(root: Path, candidate_id: str) -> dict[str, Any]:
    model_root = root / "base" / candidate_id
    model_root.mkdir(parents=True)
    (model_root / "config.json").write_text('{"model":"synthetic"}', encoding="utf-8")
    digest, file_count, total_bytes = integrity.artifact_digest(model_root)
    return {
        "schema_version": "model-download-manifest-v2",
        "models": [
            {
                "candidate_id": candidate_id,
                "local_path": model_root.relative_to(root).as_posix(),
                "revision": "synthetic-revision",
                "sha256": digest,
                "file_count": file_count,
                "total_bytes": total_bytes,
            }
        ],
    }


@pytest.mark.parametrize("token", ("NaN", "Infinity", "-Infinity"))
def test_strict_json_rejects_non_finite_tokens(tmp_path: Path, token: str) -> None:
    path = tmp_path / "non-finite.json"
    path.write_text('{"value":' + token + "}", encoding="utf-8")
    with pytest.raises(integrity.IntegrityError, match="non-standard JSON token"):
        integrity.strict_json_object(path, where="synthetic document")


def test_held_out_audit_rejects_self_authored_status(tmp_path: Path) -> None:
    zero_support = {label: 0 for label in artifacts.LOCKED_RELEASE_LABELS}
    with pytest.raises(ValidationError, match="blocker_reasons are inconsistent"):
        artifacts.HeldOutSupportAudit(
            evaluated_split_path=tmp_path / "heldout.jsonl",
            support_by_label=zero_support,
            blocker_reasons=[],
        )
    with pytest.raises(ValidationError, match="locked_label_order"):
        artifacts.HeldOutSupportAudit(
            evaluated_split_path=tmp_path / "heldout.jsonl",
            locked_label_order=tuple(reversed(artifacts.LOCKED_RELEASE_LABELS)),
            support_by_label={label: 1 for label in artifacts.LOCKED_RELEASE_LABELS},
        )
    audit = artifacts.HeldOutSupportAudit(
        evaluated_split_root=tmp_path,
        evaluated_split_path=Path("heldout.jsonl"),
        support_by_label={label: 1 for label in artifacts.LOCKED_RELEASE_LABELS},
    )
    assert audit.ready is True
    assert audit.verdict == "PASS"
    assert audit.evaluated_split_path == tmp_path / "heldout.jsonl"


def _import_targets(source: str) -> set[str]:
    targets: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            targets.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            targets.add(node.module)
    return targets


def _module_name(relative: str) -> str:
    path = Path(relative)
    parts = list(path.with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def test_canonical_bytes_and_sha_match_frozen_synthetic_fixture(tmp_path: Path) -> None:
    fixture = json.loads(SERIALIZATION_FIXTURE.read_text(encoding="utf-8"))
    active = _release_artifact(artifacts, tmp_path)
    compact = _normalize_temp_root(active.model_dump_json(), tmp_path)

    assert compact == fixture["release_evaluation_artifact"]["compact_utf8"]
    assert _normalize_temp_root(active.model_dump_json(indent=2), tmp_path) == fixture["release_evaluation_artifact"][
        "indented_utf8"
    ]
    canonical = _normalize_temp_root(
        integrity.canonical_json_bytes(active.model_dump(mode="json")).decode("utf-8"),
        tmp_path,
    ).encode("utf-8")
    assert canonical.hex() == fixture["release_evaluation_artifact"][
        "canonical_lf_utf8_hex"
    ]
    assert canonical.endswith(b"\n") and not canonical.endswith(b"\n\n")
    assert integrity.sha256_bytes(canonical) == hashlib.sha256(canonical).hexdigest()


def test_file_sha_and_safe_path_primitives_use_only_bounded_synthetic_paths(
    tmp_path: Path,
) -> None:
    payload = "bằng chứng tổng hợp\n".encode("utf-8")
    source = tmp_path / "source.bin"
    source.write_bytes(payload)

    assert integrity.sha256_file(source) == hashlib.sha256(payload).hexdigest()
    with pytest.raises(FileNotFoundError, match="Missing artifact file"):
        integrity.sha256_file(tmp_path / "missing.bin")
    target = integrity.bounded_descendant(
        tmp_path,
        Path("nested") / "artifact.json",
        where="synthetic artifact",
    )
    assert target == tmp_path / "nested" / "artifact.json"
    for escape in (Path("..") / "escape", tmp_path / "absolute"):
        with pytest.raises(integrity.IntegrityError):
            integrity.bounded_descendant(tmp_path, escape, where="synthetic artifact")


def test_bounded_paths_reject_redirecting_ancestry_when_supported(tmp_path: Path) -> None:
    real = tmp_path / "real"
    real.mkdir()
    redirect = tmp_path / "redirect"
    try:
        redirect.symlink_to(real, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"directory symlinks unavailable: {exc}")

    with pytest.raises(integrity.IntegrityError, match="symlink or reparse"):
        integrity.bounded_descendant(
            tmp_path,
            Path("redirect") / "artifact.json",
            where="synthetic artifact",
        )


def test_exclusive_and_atomic_writes_never_overwrite_or_lose_races(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    exclusive = tmp_path / "exclusive.json"
    assert integrity.write_bytes_exclusive(exclusive, b"first") == exclusive
    with pytest.raises(integrity.IntegrityError, match="already exists"):
        integrity.write_bytes_exclusive(exclusive, b"second")
    assert exclusive.read_bytes() == b"first"

    atomic = tmp_path / "atomic.json"
    assert integrity.atomic_replace_new_artifact(atomic, b"complete") == atomic
    with pytest.raises(integrity.IntegrityError, match="already exists"):
        integrity.atomic_replace_new_artifact(atomic, b"replacement")
    assert atomic.read_bytes() == b"complete"

    raced = tmp_path / "raced.json"
    original_link = os.link

    def collide(source: str | bytes, destination: str | bytes, *args: Any, **kwargs: Any) -> None:
        Path(destination).write_bytes(b"racer")
        original_link(source, destination, *args, **kwargs)

    monkeypatch.setattr(integrity.os, "link", collide)
    with pytest.raises(integrity.IntegrityError, match="already exists"):
        integrity.atomic_replace_new_artifact(raced, b"ours")
    assert raced.read_bytes() == b"racer"
    assert not any(path.suffix == ".tmp" for path in tmp_path.iterdir())


def test_file_hash_rejects_final_redirect_when_supported(tmp_path: Path) -> None:
    source = tmp_path / "source.bin"
    source.write_bytes(b"trusted")
    redirect = tmp_path / "redirect.bin"
    try:
        redirect.symlink_to(source)
    except OSError as exc:
        pytest.skip(f"file symlinks unavailable: {exc}")

    with pytest.raises(integrity.IntegrityError, match="symlink or reparse"):
        integrity.sha256_file(redirect)


def test_model_artifact_digest_rejects_redirect_members_when_supported(
    tmp_path: Path,
) -> None:
    artifact_root = tmp_path / "artifact"
    artifact_root.mkdir()
    source = tmp_path / "outside.bin"
    source.write_bytes(b"outside")
    try:
        (artifact_root / "redirect.bin").symlink_to(source)
    except OSError as exc:
        pytest.skip(f"file symlinks unavailable: {exc}")

    with pytest.raises(integrity.IntegrityError, match="must not contain redirects"):
        integrity.artifact_digest(artifact_root)


def test_atomic_failure_never_unlinks_post_publication_replacement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "published.json"
    original_hash = integrity.sha256_file

    def replace_before_verification(path: Path) -> str:
        candidate = Path(path)
        if candidate == target:
            candidate.unlink()
            candidate.write_bytes(b"racer")
            raise integrity.IntegrityError("synthetic verification failure")
        return original_hash(candidate)

    monkeypatch.setattr(integrity, "sha256_file", replace_before_verification)

    with pytest.raises(integrity.IntegrityError, match="verification failure"):
        integrity.atomic_replace_new_artifact(target, b"ours")

    assert target.read_bytes() == b"racer"


def test_download_manifest_requires_strict_hashed_v2_contract(
    tmp_path: Path,
) -> None:
    absent = tmp_path / "absent"
    absent.mkdir()
    assert artifacts.load_download_manifest(absent) == {}

    valid = tmp_path / "valid"
    manifest = valid / "manifests" / "download-manifest.json"
    manifest.parent.mkdir(parents=True)
    payload = _strict_download_manifest(valid, "qwen3-4b-instruct-2507")
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    loaded = artifacts.load_download_manifest(valid)
    assert loaded["qwen3-4b-instruct-2507"].sha256 == payload["models"][0]["sha256"]
    resolved = artifacts.resolve_downloaded_model(valid, "qwen3-4b-instruct-2507")
    assert artifacts.verify_artifact_identity(resolved) == valid / "base/qwen3-4b-instruct-2507"

    legacy = tmp_path / "legacy"
    legacy_manifest = legacy / "manifests" / "download-manifest.json"
    legacy_manifest.parent.mkdir(parents=True)
    legacy_manifest.write_text(
        json.dumps({"models": [{"candidate_id": "qwen3.5-4b", "local_path": "base/model"}]}),
        encoding="utf-8",
    )
    with pytest.raises(artifacts.ArtifactError, match="schema_version"):
        artifacts.load_download_manifest(legacy)


def test_active_registry_matches_historical_bytes_and_validation(tmp_path: Path) -> None:
    from src.model_adaptation import registry as historical_registry
    from src.model_adaptation import schemas as historical_schemas

    payload = _registry_payload()
    active = artifacts.ModelRegistry.model_validate(payload)
    historical = historical_schemas.ModelRegistry.model_validate(payload)
    assert active.model_dump(mode="json") == historical.model_dump(mode="json")

    active_path = tmp_path / "active" / "manifests" / "registry.json"
    historical_path = tmp_path / "historical" / "registry.json"
    active_root = tmp_path / "active"
    active_root.mkdir()
    artifacts.save_model_registry(active, active_path, storage_root=active_root)
    historical_registry.save_model_registry(historical, historical_path)
    assert active_path.read_bytes() == historical_path.read_bytes()
    assert artifacts.load_model_registry(
        active_path, storage_root=active_root
    ).model_dump(mode="json") == (
        historical_registry.load_model_registry(historical_path).model_dump(mode="json")
    )

    with pytest.raises(artifacts.ArtifactError, match="already exists"):
        artifacts.save_model_registry(active, active_path, storage_root=active_root)
    malformed = tmp_path / "malformed-registry.json"
    malformed.write_bytes(b'{"version_tag":""}')
    with pytest.raises(Exception):
        historical_registry.load_model_registry(malformed)
    with pytest.raises(artifacts.ArtifactError):
        artifacts.load_model_registry(malformed, storage_root=tmp_path)


def test_registry_writer_rejects_unbounded_paths_without_side_effects(
    tmp_path: Path,
) -> None:
    registry = artifacts.ModelRegistry.model_validate(_registry_payload())
    storage_root = tmp_path / "trusted"
    storage_root.mkdir()
    escaped_parent = tmp_path / "escaped"

    with pytest.raises(artifacts.ArtifactError, match="below model storage root"):
        artifacts.save_model_registry(
            registry,
            escaped_parent / "registry.json",
            storage_root=storage_root,
        )

    assert not escaped_parent.exists()

    traversal = storage_root / "not-created" / ".." / "registry.json"
    with pytest.raises(artifacts.ArtifactError, match="must be canonical"):
        artifacts.save_model_registry(
            registry,
            traversal,
            storage_root=storage_root,
        )
    assert not (storage_root / "not-created").exists()


def test_registry_writer_rejects_redirecting_parent_without_side_effects(
    tmp_path: Path,
) -> None:
    registry = artifacts.ModelRegistry.model_validate(_registry_payload())
    storage_root = tmp_path / "trusted"
    external = tmp_path / "external"
    storage_root.mkdir()
    external.mkdir()
    redirect = storage_root / "redirect"
    try:
        redirect.symlink_to(external, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"directory symlinks unavailable: {exc}")

    with pytest.raises(artifacts.ArtifactError, match="symlink or reparse"):
        artifacts.save_model_registry(
            registry,
            redirect / "registry.json",
            storage_root=storage_root,
        )

    assert not (external / "registry.json").exists()


def test_registry_artifact_requires_exact_metadata_and_rechecks_hash(
    tmp_path: Path,
) -> None:
    artifact_root = tmp_path / "models"
    artifact_path = artifact_root / "gguf" / "synthetic.gguf"
    artifact_path.parent.mkdir(parents=True)
    artifact_path.write_bytes(b"verified-gguf")
    digest, _, _ = integrity.artifact_digest(artifact_path)
    payload = _registry_payload()
    payload["artifacts"][0].update(
        {
            "local_path": "gguf/synthetic.gguf",
            "sha256": digest,
            "profile_name": "gguf-laptop",
        }
    )
    registry = artifacts.ModelRegistry.model_validate(payload)

    verified = artifacts.resolve_registry_artifact(
        registry,
        artifact_root=artifact_root,
        candidate_id="qwen3-4b-instruct-2507",
        artifact_type="gguf",
        profile_name="gguf-laptop",
    )
    assert artifacts.verify_artifact_identity(verified) == artifact_path

    artifact_path.write_bytes(b"tampered-gguf")
    with pytest.raises(artifacts.ArtifactError, match="SHA-256 mismatch"):
        artifacts.verify_artifact_identity(verified)


@pytest.mark.parametrize("invalid_hash", ("A" * 64, "g" * 64, "a" * 63))
def test_registry_rejects_invalid_hash_and_version_metadata(invalid_hash: str) -> None:
    payload = _registry_payload()
    payload["artifacts"][0]["sha256"] = invalid_hash
    with pytest.raises(ValidationError):
        artifacts.ModelRegistry.model_validate(payload)

    payload = _registry_payload()
    payload["artifacts"][0]["version_tag"] = "different-version"
    with pytest.raises(ValidationError, match="must match registry"):
        artifacts.ModelRegistry.model_validate(payload)


def test_active_release_models_match_independent_historical_contract_and_reader(
    tmp_path: Path,
) -> None:
    from src.model_adaptation import schemas as historical_schemas

    active = _release_artifact(artifacts, tmp_path)
    historical = _release_artifact(historical_schemas, tmp_path)
    assert active.model_dump(mode="json") == historical.model_dump(mode="json")
    assert active.model_dump_json() == historical.model_dump_json()
    assert artifacts.LOCKED_RELEASE_LABELS == historical_schemas.LOCKED_RELEASE_LABELS
    assert artifacts.LOCKED_RISKY_LABELS == historical_schemas.LOCKED_RISKY_LABELS
    assert artifacts.RISKY_LABEL_RECALL_FLOORS == historical_schemas.RISKY_LABEL_RECALL_FLOORS

    path = tmp_path / "synthetic-release.json"
    path.write_text(active.model_dump_json(), encoding="utf-8")
    loaded = artifacts.load_release_evaluation_artifact(path)
    assert loaded == active

    invalid_payload = active.model_dump(mode="json")
    invalid_payload["per_label_metrics"] = list(reversed(invalid_payload["per_label_metrics"]))
    with pytest.raises(ValidationError, match="locked release label order"):
        historical_schemas.ReleaseEvaluationArtifact.model_validate(invalid_payload)
    with pytest.raises(ValidationError, match="locked release label order"):
        artifacts.ReleaseEvaluationArtifact.model_validate(invalid_payload)


def test_release_artifact_rejects_fail_open_pass_states(tmp_path: Path) -> None:
    valid = _release_artifact(artifacts, tmp_path).model_dump(mode="json")

    missing_metrics = dict(valid)
    missing_metrics["per_label_metrics"] = []
    with pytest.raises(ValidationError, match="locked release label order"):
        artifacts.ReleaseEvaluationArtifact.model_validate(missing_metrics)

    blocked_readiness = json.loads(json.dumps(valid))
    blocked_readiness["readiness_audit"]["support_by_label"]["task_scam"] = 0
    blocked_readiness["readiness_audit"]["blocker_reasons"] = [
        "missing held-out support for task_scam"
    ]
    blocked_readiness["readiness_audit"]["ready"] = False
    blocked_readiness["readiness_audit"]["verdict"] = "BLOCK"
    blocked_readiness["per_label_metrics"][2]["support"] = 0
    blocked_readiness["overall_metrics"]["evaluated_rows"] = 3
    with pytest.raises(ValidationError, match="verdict .* inconsistent"):
        artifacts.ReleaseEvaluationArtifact.model_validate(blocked_readiness)

    below_floor = json.loads(json.dumps(valid))
    below_floor["per_label_metrics"][0]["recall"] = 0.1
    below_floor["per_label_metrics"][0]["f1"] = 0.18
    below_floor["overall_metrics"]["macro_f1"] = 0.72
    below_floor["overall_metrics"]["weighted_f1"] = 0.72
    with pytest.raises(ValidationError, match="verdict .* inconsistent"):
        artifacts.ReleaseEvaluationArtifact.model_validate(below_floor)

    contradictory_blocker = json.loads(json.dumps(valid))
    contradictory_blocker["blocker_reasons"] = ["synthetic blocker"]
    with pytest.raises(ValidationError, match="verdict .* inconsistent"):
        artifacts.ReleaseEvaluationArtifact.model_validate(contradictory_blocker)


def test_release_artifact_reconciles_floor_and_metric_claims(tmp_path: Path) -> None:
    valid = _release_artifact(artifacts, tmp_path).model_dump(mode="json")

    contradictory_floor = json.loads(json.dumps(valid))
    contradictory_floor["risky_recall_floor"] = 1.0
    with pytest.raises(ValidationError, match="immutable release floor"):
        artifacts.ReleaseEvaluationArtifact.model_validate(contradictory_floor)

    audit_floor = json.loads(json.dumps(valid))
    audit_floor["readiness_audit"]["risky_recall_floor"] = 0.8
    with pytest.raises(ValidationError, match="immutable release floor"):
        artifacts.ReleaseEvaluationArtifact.model_validate(audit_floor)

    contradictory_f1 = json.loads(json.dumps(valid))
    contradictory_f1["per_label_metrics"][0]["f1"] = 0.2
    with pytest.raises(ValidationError, match="recomputed from precision and recall"):
        artifacts.ReleaseEvaluationArtifact.model_validate(contradictory_f1)

    for field in ("macro_f1", "weighted_f1"):
        contradictory_aggregate = json.loads(json.dumps(valid))
        contradictory_aggregate["overall_metrics"][field] = 0.2
        with pytest.raises(ValidationError, match=f"overall {field}"):
            artifacts.ReleaseEvaluationArtifact.model_validate(contradictory_aggregate)


def test_historical_sources_keep_archived_hashes_and_no_active_reverse_edges() -> None:
    baseline = json.loads(PROTECTED_BASELINE.read_text(encoding="utf-8"))
    recorded = {
        item["path"]: item["sha256"]
        for item in baseline["historical_mirror"]["sources"]
    }
    assert {path: recorded[path] for path in HISTORICAL_HASHES} == HISTORICAL_HASHES
    for relative, expected in HISTORICAL_HASHES.items():
        assert integrity.sha256_file(REPO_ROOT / relative) == expected

    source_paths = [
        item["path"]
        for item in baseline["historical_mirror"]["sources"]
        if item["path"].endswith(".py") and (REPO_ROOT / item["path"]).is_file()
    ]
    graph = {
        _module_name(relative): _import_targets(
            (REPO_ROOT / relative).read_text(encoding="utf-8")
        )
        for relative in source_paths
    }
    pending = ["src.model_adaptation.training", "src.model_adaptation.schemas"]
    visited: set[str] = set()
    while pending:
        module = pending.pop()
        if module in visited:
            continue
        visited.add(module)
        for target in graph.get(module, set()):
            assert not any(
                target == prefix or target.startswith(prefix + ".")
                for prefix in FORBIDDEN_ACTIVE_PREFIXES
            ), f"historical reverse edge: {module} -> {target}"
            if target in graph:
                pending.append(target)

    active_source = (REPO_ROOT / "src/artifacts.py").read_text(encoding="utf-8")
    assert "src.model_adaptation" not in active_source
    assert "src.modeling" not in active_source
