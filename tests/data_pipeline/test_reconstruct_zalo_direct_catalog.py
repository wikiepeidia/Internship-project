"""Regression gates for the Phase 39 F-01 Zalo semantic reconstruction."""

from __future__ import annotations

import copy
import inspect
import json
from collections import defaultdict
from pathlib import Path

import pytest

import src.data_pipeline.reconstruct_zalo_direct_catalog as reconstruction_module
from src.data_pipeline.generation.zalo_codex_recovery import materialize_catalog
from src.data_pipeline.reconstruct_zalo_direct_catalog import (
    AUTHORING_SOURCE_PATHS,
    EXPECTED_OUTPUT_COUNTS,
    EXPECTED_OUTPUT_DISTRIBUTION,
    EXPECTED_ZALO_SEEDS_BY_SPLIT,
    ReconstructionError,
    build_updated_manifest,
    class_distribution,
    encode_jsonl,
    legacy_inner_narration_texts,
    promote_candidate,
    read_jsonl,
    reconstruct_splits,
    seed_to_root,
    stage_candidate_bundle,
    validate_legacy_inputs,
    validate_projected_corpus,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
SPLITS_DIR = REPO_ROOT / "data" / "splits"


def _implementation_provenance(*, dirty: bool) -> dict:
    return {
        "git_commit": "a" * 40,
        "worktree_dirty": dirty,
        "source_sha256": {
            path: f"{index:064x}" for index, path in enumerate(AUTHORING_SOURCE_PATHS, start=1)
        },
    }


def _live_non_zalo() -> dict[str, list[dict]]:
    return {
        name: [
            row
            for row in read_jsonl(SPLITS_DIR / f"{name}.jsonl")
            if row["label"] != "zalo_social_engineering"
        ]
        for name in ("train", "val", "test")
    }


@pytest.fixture(scope="module")
def legacy_fixture() -> dict[str, list[dict]]:
    """Build the exact legacy shape from immutable formulas plus live non-Zalo rows."""
    roots = seed_to_root()
    direct_by_seed: dict[str, list[dict]] = defaultdict(list)
    for row in materialize_catalog():
        direct_by_seed[row["seed_id"]].append(row)

    fixture = _live_non_zalo()
    for split_name in ("train", "val", "test"):
        for seed_id in sorted(EXPECTED_ZALO_SEEDS_BY_SPLIT[split_name]):
            root = roots[seed_id]
            base = direct_by_seed[seed_id][0]
            for text in legacy_inner_narration_texts(root):
                row = copy.deepcopy(base)
                row["text"] = text
                row["suspicious_spans"] = [root.requested_action]
                fixture[split_name].append(row)
    return fixture


@pytest.fixture(scope="module")
def reconstructed(legacy_fixture) -> dict[str, list[dict]]:
    return reconstruct_splits(legacy_fixture)


def test_locked_seed_layout_is_sixty_groups_with_38_8_14_assignment():
    assert {name: len(seeds) for name, seeds in EXPECTED_ZALO_SEEDS_BY_SPLIT.items()} == {
        "train": 38,
        "val": 8,
        "test": 14,
    }
    assert len(set().union(*EXPECTED_ZALO_SEEDS_BY_SPLIT.values())) == 60
    assert set(seed_to_root()) == set().union(*EXPECTED_ZALO_SEEDS_BY_SPLIT.values())


def test_legacy_gate_accepts_only_240_known_narrator_rows(legacy_fixture):
    assignments = validate_legacy_inputs(legacy_fixture)
    assert len(assignments) == 60
    assert sum(
        row["label"] == "zalo_social_engineering"
        for rows in legacy_fixture.values()
        for row in rows
    ) == 240

    contaminated = copy.deepcopy(legacy_fixture)
    first = next(
        row
        for row in contaminated["train"]
        if row["label"] == "zalo_social_engineering"
    )
    first["text"] += " thay đổi ngoài công thức"
    with pytest.raises(ReconstructionError, match="four known legacy narrator formulas"):
        validate_legacy_inputs(contaminated)


def test_reconstruction_replaces_four_with_five_without_touching_non_zalo(
    legacy_fixture, reconstructed
):
    stats = validate_projected_corpus(legacy_fixture, reconstructed)
    assert stats["total_rows"] == 2403
    assert stats["split_counts"] == EXPECTED_OUTPUT_COUNTS
    assert stats["split_class_distribution"] == EXPECTED_OUTPUT_DISTRIBUTION
    assert stats["unique_zalo_seeds"] == 60
    assert stats["max_seed_share"] <= 0.08

    for split_name in ("train", "val", "test"):
        before = [
            row for row in legacy_fixture[split_name] if row["label"] != "zalo_social_engineering"
        ]
        after = [
            row for row in reconstructed[split_name] if row["label"] != "zalo_social_engineering"
        ]
        assert after == before
        assert class_distribution(reconstructed[split_name]) == EXPECTED_OUTPUT_DISTRIBUTION[split_name]


def test_reconstruction_retains_all_task_scam_risk_repairs(legacy_fixture, reconstructed):
    for split_name in ("train", "val", "test"):
        before = [row for row in legacy_fixture[split_name] if row["label"] == "task_scam"]
        after = [row for row in reconstructed[split_name] if row["label"] == "task_scam"]
        assert after == before


def test_projected_gate_rejects_non_zalo_mutation(legacy_fixture, reconstructed):
    corrupted = copy.deepcopy(reconstructed)
    row = next(row for row in corrupted["train"] if row["label"] == "task_scam")
    row["risk_tier"] = "suspicious" if row["risk_tier"] == "high-risk" else "high-risk"
    with pytest.raises(ReconstructionError, match="non-Zalo records changed"):
        validate_projected_corpus(legacy_fixture, corrupted)


@pytest.mark.parametrize("field", ["seed_id", "source", "risk_tier", "suspicious_spans", "text"])
def test_projected_gate_binds_every_zalo_field_to_validated_catalog(
    field, legacy_fixture, reconstructed
):
    corrupted = copy.deepcopy(reconstructed)
    row = next(
        row for row in corrupted["train"] if row["label"] == "zalo_social_engineering"
    )
    if field == "seed_id":
        row[field] = "seed_forged000000"
    elif field == "source":
        row[field] = "synthetic_claude"
    elif field == "risk_tier":
        row[field] = "suspicious" if row[field] == "high-risk" else "high-risk"
    elif field == "suspicious_spans":
        row[field] = [row["text"][:10]]
    else:
        row[field] += " Xin xử lý đúng trong thời hạn này."

    with pytest.raises(ReconstructionError):
        validate_projected_corpus(legacy_fixture, corrupted)


def test_candidate_bundle_precedes_promotion_and_manifest_matches(
    tmp_path, legacy_fixture, reconstructed
):
    stats = validate_projected_corpus(legacy_fixture, reconstructed)
    payloads = {name: encode_jsonl(reconstructed[name]) for name in ("train", "val", "test")}
    catalog = materialize_catalog()
    old_manifest = {
        "repair_stats": {"preserved": True},
        "zalo_narrator_scaffold_repair": {"preserved": True},
        "task_scam_risk_tier_repair": {"preserved": True},
    }
    manifest = build_updated_manifest(
        old_manifest,
        payloads,
        stats,
        {"train.jsonl": "a", "val.jsonl": "b", "test.jsonl": "c", "manifest.json": "d"},
        encode_jsonl(catalog),
        _implementation_provenance(dirty=True),
    )
    paths = stage_candidate_bundle(tmp_path / "candidate", reconstructed, manifest, catalog)

    assert all(path.exists() for path in paths.values())
    loaded_manifest = json.loads(paths["manifest.json"].read_text(encoding="utf-8"))
    assert loaded_manifest["repair_stats"] == {"preserved": True}
    assert loaded_manifest["zalo_narrator_scaffold_repair"] == {"preserved": True}
    assert loaded_manifest["task_scam_risk_tier_repair"] == {"preserved": True}
    assert loaded_manifest["zalo_direct_semantic_reconstruction"]["external_api_call_count"] == 0
    provenance = loaded_manifest["zalo_direct_semantic_reconstruction"][
        "implementation_provenance"
    ]
    assert provenance == _implementation_provenance(dirty=True)
    assert loaded_manifest["manifest"]["git_commit"] is None
    for name in ("train", "val", "test"):
        entry = loaded_manifest["manifest"]["files"][f"{name}.jsonl"]
        assert entry["records"] == EXPECTED_OUTPUT_COUNTS[name]
        assert entry["bytes"] == paths[f"{name}.jsonl"].stat().st_size


def _promotion_fixture(tmp_path):
    candidate_dir = tmp_path / "candidate"
    canonical_dir = tmp_path / "canonical"
    candidate_dir.mkdir()
    canonical_dir.mkdir()
    keys = ("train.jsonl", "val.jsonl", "test.jsonl", "manifest.json", "catalog.jsonl")
    candidate_paths = {}
    canonical_paths = {}
    original_bytes = {}
    for key in keys:
        candidate_path = candidate_dir / key
        candidate_path.write_bytes(f"new-{key}".encode())
        candidate_paths[key] = candidate_path
        if key == "catalog.jsonl":
            original_bytes[key] = None
            continue
        canonical_path = canonical_dir / key
        old_payload = f"old-{key}".encode()
        canonical_path.write_bytes(old_payload)
        canonical_paths[key] = canonical_path
        original_bytes[key] = old_payload
    return (
        candidate_paths,
        canonical_paths,
        original_bytes,
        canonical_dir / "catalog.jsonl",
    )


def test_promotion_write_failure_restores_every_original_byte(tmp_path, monkeypatch):
    candidate_paths, canonical_paths, originals, catalog_output = _promotion_fixture(tmp_path)
    real_write = reconstruction_module._write_bytes_atomically

    def injected_failure(path, payload):
        if path == canonical_paths["manifest.json"] and payload == b"new-manifest.json":
            raise OSError("injected promotion write failure")
        real_write(path, payload)

    monkeypatch.setattr(reconstruction_module, "_write_bytes_atomically", injected_failure)
    with pytest.raises(OSError, match="injected promotion write failure"):
        promote_candidate(candidate_paths, canonical_paths, originals, catalog_output)

    for key, original in originals.items():
        destination = catalog_output if key == "catalog.jsonl" else canonical_paths[key]
        if original is None:
            assert not destination.exists()
        else:
            assert destination.read_bytes() == original


def test_verification_failure_rolls_back_new_catalog_and_all_canonical_files(
    tmp_path,
):
    candidate_paths, canonical_paths, originals, catalog_output = _promotion_fixture(tmp_path)

    def reject_promoted_bundle():
        raise RuntimeError("injected post-promotion verification failure")

    with pytest.raises(RuntimeError, match="injected post-promotion verification failure"):
        promote_candidate(
            candidate_paths,
            canonical_paths,
            originals,
            catalog_output,
            verify_promoted=reject_promoted_bundle,
        )
    assert not catalog_output.exists()
    for key in ("train.jsonl", "val.jsonl", "test.jsonl", "manifest.json"):
        assert canonical_paths[key].read_bytes() == originals[key]


def test_rollback_failure_is_composite_and_does_not_skip_other_restorations(
    tmp_path, monkeypatch
):
    candidate_paths, canonical_paths, originals, catalog_output = _promotion_fixture(tmp_path)
    real_write = reconstruction_module._write_bytes_atomically

    def injected_rollback_failure(path, payload):
        if path == canonical_paths["train.jsonl"] and payload == originals["train.jsonl"]:
            raise OSError("injected train rollback failure")
        real_write(path, payload)

    monkeypatch.setattr(
        reconstruction_module,
        "_write_bytes_atomically",
        injected_rollback_failure,
    )
    with pytest.raises(ReconstructionError, match=r"rollback incomplete:.*train\.jsonl"):
        promote_candidate(
            candidate_paths,
            canonical_paths,
            originals,
            catalog_output,
            verify_promoted=lambda: (_ for _ in ()).throw(RuntimeError("reject bundle")),
        )

    assert canonical_paths["train.jsonl"].read_bytes() == b"new-train.jsonl"
    for key in ("val.jsonl", "test.jsonl", "manifest.json"):
        assert canonical_paths[key].read_bytes() == originals[key]
    assert not catalog_output.exists()


def test_source_provenance_covers_every_authoring_file_with_content_hash():
    provenance = reconstruction_module._authoring_source_provenance(REPO_ROOT)
    assert isinstance(provenance["worktree_dirty"], bool)
    assert len(provenance["git_commit"]) >= 40
    assert set(provenance["source_sha256"]) == set(AUTHORING_SOURCE_PATHS)
    for relative_path, digest in provenance["source_sha256"].items():
        assert digest == reconstruction_module._sha256_bytes(
            (REPO_ROOT / relative_path).read_bytes()
        )


def test_reconstruction_module_has_no_external_provider_path():
    import src.data_pipeline.reconstruct_zalo_direct_catalog as module

    source = inspect.getsource(module)
    assert "requests" not in source
    assert "_call_claude" not in source
    assert "_call_gemini" not in source
    assert "_call_openrouter" not in source
    assert "_call_deepseek" not in source
    assert "_call_openai_compatible" not in source
