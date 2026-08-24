"""Regression coverage for the Phase 39 staged mislabel migration."""

from __future__ import annotations

import copy
import inspect
import json
import shutil
from collections import Counter
from pathlib import Path

import pytest
from pydantic import ValidationError

import src.data_pipeline.apply_mislabel_triage as module
from src.data_pipeline.apply_mislabel_triage import (
    CodexSemanticRepairDecision,
    EXPECTED_INPUT_SHA256,
    EXPECTED_PROTECTED_AUDIT_SHA256,
    MislabelTriageError,
    _build_payloads,
    _git_provenance,
    _stage_payloads,
    apply_semantic_repairs,
    build_dispositions,
    build_projection,
    canonicalize_identity_text,
    exclusive_run_lock,
    load_live_splits,
    parse_triage_decision_text,
    parse_triage_decisions,
    promote_candidate_bundle,
    read_jsonl,
    reconstruct_bound_candidates,
    record_digest,
    replace_payload_bundle,
    run_stage,
    sha256_path,
    validate_staged_candidate,
)
from src.data_pipeline.judge_merge import validate_downstream_data_contract


REPO_ROOT = Path(__file__).resolve().parents[2]
PHASE_DIR = REPO_ROOT / ".planning/phases/39-independent-quality-re-judge"
DECISIONS_PATH = PHASE_DIR / "MISLABEL triage.md"
PRE_PHASE39_ROOT = REPO_ROOT / "data/processed/f01-zalo-direct-candidate-20260817-verified"
MERGED_PATH = (
    REPO_ROOT
    / "data/backup/pre-phase39-mislabel-triage/processed/judge-merged.jsonl"
)
SPLITS_DIR = PRE_PHASE39_ROOT / "splits"
MANIFEST_PATH = PRE_PHASE39_ROOT / "manifest.json"
PROTECTED_PATHS = {
    "39-manual-review-sheet.md": PHASE_DIR / "39-manual-review-sheet.md",
    "39-mislabel-triage-sheet.md": PHASE_DIR / "39-mislabel-triage-sheet.md",
    "MISLABEL triage.md": DECISIONS_PATH,
}


@pytest.fixture(scope="session")
def locked_material():
    decisions = parse_triage_decisions(DECISIONS_PATH)
    merged = read_jsonl(MERGED_PATH)
    splits = load_live_splits(SPLITS_DIR)
    projection = build_projection(decisions, merged, splits)
    return decisions, merged, splits, projection


@pytest.fixture(scope="session")
def staged_bundle(tmp_path_factory, locked_material):
    _, _, _, projection = locked_material
    root = tmp_path_factory.mktemp("phase39-stage")
    candidate_dir = root / "candidate"
    audit_path = root / "39-MISLABEL-AUDIT.md"
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    payloads, audit_payload = _build_payloads(
        projection,
        manifest,
        EXPECTED_INPUT_SHA256,
        EXPECTED_PROTECTED_AUDIT_SHA256,
        _git_provenance(REPO_ROOT),
    )
    reused = _stage_payloads(
        candidate_dir,
        audit_path,
        payloads,
        audit_payload,
        verify_callback=lambda: None,
    )
    assert reused is False
    return candidate_dir, audit_path, payloads, audit_payload


SEMANTIC_QUARANTINE_DIGESTS = {
    "b6a6dc83c46696f1b54862bbb92944b28e1b7e6201d158dc1b6acc4f531693f2",
    "6f57b8846a34fb1252a2f511551749478e041c761bcb7ea5cf99c6f33d8e6399",
    "391791c09f4964057406509b89e312bd3dfcd294aaf57aef2a984f4f826fe1d3",
    "d0d885748feb932ca0e44053ca3121a9cc3fe31b946dad9274eae499f9c25677",
}


def _write_json(path: Path, value):
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _refresh_candidate_run_manifest_hash(candidate_dir: Path) -> None:
    run_path = candidate_dir / "run.json"
    run = json.loads(run_path.read_text(encoding="utf-8"))
    run["output_sha256"]["manifest.json"] = module.sha256_path(
        candidate_dir / "manifest.json"
    )
    _write_json(run_path, run)


@pytest.fixture(scope="session")
def semantic_quarantine_bundle(tmp_path_factory, staged_bundle):
    staged_candidate, _, _, _ = staged_bundle
    root = tmp_path_factory.mktemp("phase39-semantic-quarantine") / "repo"
    processed = root / "data" / "processed"
    candidate_dir = processed / "phase39-mislabel-candidate"
    source_dir = processed / "phase39-pre-semantic-quarantine"
    artifacts_dir = processed / "phase39-semantic-quarantine"
    processed.mkdir(parents=True)
    shutil.copytree(staged_candidate, candidate_dir)
    source_dir.mkdir()
    artifacts_dir.mkdir()
    shutil.copy2(candidate_dir / "manifest.json", source_dir / "manifest.json")
    for split_name in module.SPLIT_NAMES:
        shutil.copy2(
            candidate_dir / "splits" / f"{split_name}.jsonl",
            source_dir / f"{split_name}.jsonl",
        )

    source_splits = {
        split_name: module.read_jsonl(source_dir / f"{split_name}.jsonl")
        for split_name in module.SPLIT_NAMES
    }
    quarantine_rows = []
    quarantine_coordinates = set()
    for split_name in module.SPLIT_NAMES:
        for row_index, record in enumerate(source_splits[split_name]):
            digest = module.record_digest(record)
            if digest not in SEMANTIC_QUARANTINE_DIGESTS:
                continue
            quarantine_coordinates.add((split_name, row_index))
            quarantine_rows.append(
                {
                    "source_split": split_name,
                    "source_row_index": row_index,
                    "record_digest": digest,
                    "record_identity": module.record_identity(
                        record["seed_id"], record["text"]
                    ),
                    "reason": module.SEMANTIC_QUARANTINE_REASON,
                    "record": copy.deepcopy(record),
                    "fresh_judge": {
                        "split": split_name,
                        "row_index": row_index,
                        "seed_id": record["seed_id"],
                        "realism": 4,
                        "label_correctness": 2,
                        "code_switch_naturalness": 4,
                        "risk_tier_correctness": 4,
                        "suspicious_span_accuracy": 4,
                        "pass": False,
                        "reason": "Fresh judge found no fraud cue supporting the assigned label.",
                        "record_digest": digest,
                    },
                }
            )
    assert {row["record_digest"] for row in quarantine_rows} == (
        SEMANTIC_QUARANTINE_DIGESTS
    )
    assert len(quarantine_rows) == 4
    quarantine_path = artifacts_dir / "quarantine.jsonl"
    quarantine_path.write_bytes(module.encode_jsonl(quarantine_rows))

    post_quarantine = [
        record
        for split_name in module.SPLIT_NAMES
        for row_index, record in enumerate(source_splits[split_name])
        if (split_name, row_index) not in quarantine_coordinates
    ]
    capped, cap_stats = module.enforce_seed_cap(post_quarantine, cap_pct=0.08)
    cap_drops = module._derive_cap_drops(post_quarantine, capped)
    for row in cap_drops:
        row["reason"] = module.SEMANTIC_CAP_DROP_REASON
    assert cap_stats["rows_dropped_seed_cap"] == 2
    assert len(cap_drops) == 2
    cap_drop_path = artifacts_dir / "cap-drops.jsonl"
    cap_drop_path.write_bytes(module.encode_jsonl(cap_drops))

    assignments = module.assign_stratified_group_split(
        capped,
        ratios=module.SPLIT_RATIOS,
        salt=module.SPLIT_SALT,
    )
    projected = {name: [] for name in module.SPLIT_NAMES}
    for record in capped:
        projected[assignments[record["seed_id"]]].append(record)
    stats = module.validate_candidate_splits(
        projected, enforce_locked_profile=False
    )
    assert stats["total_rows"] == 2_097
    for split_name in module.SPLIT_NAMES:
        (candidate_dir / "splits" / f"{split_name}.jsonl").write_bytes(
            module.encode_jsonl(projected[split_name])
        )

    relative = lambda path: path.relative_to(root).as_posix()
    manifest_path = candidate_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for split_name in module.SPLIT_NAMES:
        split_path = candidate_dir / "splits" / f"{split_name}.jsonl"
        payload = split_path.read_bytes()
        manifest["manifest"]["files"][f"{split_name}.jsonl"] = {
            "sha256": module.sha256_bytes(payload),
            "records": len(projected[split_name]),
            "bytes": len(payload),
        }
    manifest["split_class_distribution"] = stats["split_class_distribution"]
    triage = manifest["task_scam_mislabel_triage"]
    triage["split_governance"]["split_counts"] = stats["split_counts"]
    triage["split_governance"]["split_class_distribution"] = stats[
        "split_class_distribution"
    ]
    triage["candidate_output_sha256"] = {
        f"splits/{name}.jsonl": module.sha256_path(
            candidate_dir / "splits" / f"{name}.jsonl"
        )
        for name in module.SPLIT_NAMES
    }
    triage["validation"].update(stats)
    triage["semantic_quarantine_contract"] = {
        "schema_version": module.SEMANTIC_QUARANTINE_SCHEMA_VERSION,
        "status": "applied",
        "reason": module.SEMANTIC_QUARANTINE_REASON,
        "source_candidate": {
            "manifest": {
                "path": relative(source_dir / "manifest.json"),
                "sha256": module.sha256_path(source_dir / "manifest.json"),
            },
            "splits": [
                {
                    "split": split_name,
                    "path": relative(source_dir / f"{split_name}.jsonl"),
                    "sha256": module.sha256_path(
                        source_dir / f"{split_name}.jsonl"
                    ),
                    "records": len(source_splits[split_name]),
                }
                for split_name in module.SPLIT_NAMES
            ],
        },
        "quarantine_artifact": {
            "path": relative(quarantine_path),
            "sha256": module.sha256_path(quarantine_path),
            "records": len(quarantine_rows),
        },
        "cap_drop_artifact": {
            "path": relative(cap_drop_path),
            "sha256": module.sha256_path(cap_drop_path),
            "records": len(cap_drops),
        },
        "cap_pct": 0.08,
        "split_ratios": list(module.SPLIT_RATIOS),
        "split_salt": module.SPLIT_SALT,
        "expected_profile": stats,
    }
    _write_json(manifest_path, manifest)

    run_path = candidate_dir / "run.json"
    run = json.loads(run_path.read_text(encoding="utf-8"))
    for key in (
        "splits/train.jsonl",
        "splits/val.jsonl",
        "splits/test.jsonl",
        "manifest.json",
    ):
        run["output_sha256"][key] = module.sha256_path(candidate_dir / key)
    _write_json(run_path, run)
    return root, candidate_dir


def _copy_semantic_quarantine_fixture(semantic_quarantine_bundle, tmp_path):
    source_root, _ = semantic_quarantine_bundle
    copied_root = tmp_path / "repo"
    shutil.copytree(source_root, copied_root)
    return copied_root, copied_root / "data/processed/phase39-mislabel-candidate"


def _mutate_quarantine_manifest(candidate_dir: Path, mutate) -> dict:
    manifest_path = candidate_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    mutate(
        manifest["task_scam_mislabel_triage"]["semantic_quarantine_contract"]
    )
    _write_json(manifest_path, manifest)
    _refresh_candidate_run_manifest_hash(candidate_dir)
    return manifest


def test_parser_real_file_has_exact_coverage_and_only_two_normalizations(locked_material):
    decisions, _, _, _ = locked_material
    assert [decision.candidate_number for decision in decisions] == list(range(1, 325))
    totals = Counter(
        "drop" if decision.normalized_action == "drop" else decision.new_label
        for decision in decisions
    )
    assert totals == {
        "drop": 91,
        "bank_impersonation": 48,
        "zalo_social_engineering": 177,
        "benign": 8,
    }
    normalized = [decision for decision in decisions if decision.normalization_reason]
    assert [(item.candidate_number, item.raw_decision, item.new_label) for item in normalized] == [
        (103, "Drop", None),
        (320, "Relabel to: Beigin", "benign"),
    ]


@pytest.mark.parametrize(
    "mutator, message",
    [
        (
            lambda text: text.replace(
                "1.Relabel to: bank_impersonation",
                "2.Relabel to: bank_impersonation",
                1,
            ),
            "duplicate candidate",
        ),
        (
            lambda text: text.replace(
                "1.Relabel to: bank_impersonation",
                "1.Relabel to: unsupported_class",
                1,
            ),
            "unsupported label",
        ),
        (
            lambda text: text.replace(
                "Notes: Fake ACB login URL used to harvest credentials under threat of account suspension.",
                "Notes: ",
                1,
            ),
            "empty note",
        ),
        (
            lambda text: text.replace("103.Drop", "103.Drop row", 1),
            "normalization",
        ),
    ],
)
def test_parser_fails_closed_on_malformed_human_input(mutator, message):
    text = DECISIONS_PATH.read_text(encoding="utf-8")
    if message == "normalization":
        # This is a valid canonical spelling, but it must remove the exception
        # rather than silently recording the original exceptional provenance.
        parsed = parse_triage_decision_text(mutator(text))
        assert parsed[102].normalization_reason is None
        return
    with pytest.raises(MislabelTriageError, match=message):
        parse_triage_decision_text(mutator(text))


def test_identity_canonicalization_is_conservative():
    assert canonicalize_identity_text("a\r\nb\r") == "a\nb"
    assert canonicalize_identity_text("e\u0301") == "é"
    assert canonicalize_identity_text("text\n\n") == "text\n"
    assert canonicalize_identity_text(" A  B ") == " A  B "
    assert canonicalize_identity_text("ABC") != canonicalize_identity_text("abc")


def test_identity_binding_ignores_historical_coordinates(locked_material):
    _, merged, splits, _ = locked_material
    changed = copy.deepcopy(merged)
    first = next(
        row
        for row in changed
        if row["label"] == "task_scam" and row["label_correctness"] < 3
    )
    first["split"] = "obsolete-split"
    first["row_index"] = 987_654
    bound = reconstruct_bound_candidates(changed, splits)
    assert len(bound) == 324
    assert bound[0].historical_split == "obsolete-split"
    assert bound[0].historical_row_index == 987_654
    assert bound[0].live_split in {"train", "val", "test"}


def test_identity_binding_rejects_changed_identity_text(locked_material):
    _, merged, splits, _ = locked_material
    changed = copy.deepcopy(merged)
    first = next(
        row
        for row in changed
        if row["label"] == "task_scam" and row["label_correctness"] < 3
    )
    first["text"] += "x"
    with pytest.raises(MislabelTriageError, match="found 323 unique live rows"):
        reconstruct_bound_candidates(changed, splits)


def test_dispositions_are_exact_and_every_admitted_change_is_label_only(locked_material):
    decisions, merged, splits, _ = locked_material
    bound = reconstruct_bound_candidates(merged, splits)
    dispositions = build_dispositions(decisions, bound)
    assert Counter(item.disposition for item in dispositions) == {
        "drop": 91,
        "admitted_relabel": 57,
        "lineage_quarantine": 176,
    }
    independent = dispositions[46]
    assert independent.candidate_number == 47
    assert independent.original_record.seed_id == "seed_c6c8772ac332"
    assert independent.disposition == "admitted_relabel"
    preserved_fields = (
        "text",
        "risk_tier",
        "suspicious_spans",
        "xai_explanation",
        "source",
        "seed_id",
    )
    for item in dispositions:
        if item.disposition != "admitted_relabel":
            continue
        before = item.original_record.model_dump(mode="json")
        after = item.approved_record.model_dump(mode="json")
        assert before["label"] != after["label"]
        for field in preserved_fields:
            assert before[field] == after[field], (item.candidate_number, field)


def test_semantic_repair_contract_rejects_identity_and_label_fields(locked_material):
    _, _, _, projection = locked_material
    row = projection.splits["train"][0]
    base = {
        "expected_record_digest": record_digest(row),
        "new_risk_tier": row["risk_tier"],
        "new_suspicious_spans": row["suspicious_spans"],
        "new_xai_explanation": row["xai_explanation"],
        "notes": "Explicit fixture semantic decision.",
    }
    for field, value in (
        ("label", "benign"),
        ("text", "forbidden text replacement"),
        ("source", "synthetic_claude"),
        ("seed_id", "seed_forbidden"),
    ):
        with pytest.raises(ValidationError):
            CodexSemanticRepairDecision.model_validate({**base, field: value})


def test_semantic_repair_applies_only_three_permitted_fields(locked_material):
    _, _, _, projection = locked_material
    row = copy.deepcopy(projection.splits["train"][0])
    span = row["text"][:10]
    decision = CodexSemanticRepairDecision(
        expected_record_digest=record_digest(row),
        new_risk_tier="high-risk",
        new_suspicious_spans=[span],
        new_xai_explanation="Giải thích đã được thẩm định lại đầy đủ cho bản ghi này.",
        notes="Fixture permits only semantic repair fields.",
    )
    repaired, provenance = apply_semantic_repairs([row], [decision])
    for field in ("label", "text", "source", "seed_id"):
        assert repaired[0][field] == row[field]
    assert repaired[0]["risk_tier"] == "high-risk"
    assert repaired[0]["suspicious_spans"] == [span]
    assert provenance[0]["expected_record_digest"] == record_digest(row)
    assert all(provenance[0]["identity_fields_preserved"].values())


def test_semantic_repair_rejects_nonliteral_span_before_output(locked_material):
    _, _, _, projection = locked_material
    row = projection.splits["train"][0]
    decision = CodexSemanticRepairDecision(
        expected_record_digest=record_digest(row),
        new_risk_tier=row["risk_tier"],
        new_suspicious_spans=["this span does not occur"],
        new_xai_explanation="Giải thích đã được thẩm định lại đầy đủ cho bản ghi này.",
        notes="Fixture invalid span.",
    )
    with pytest.raises(MislabelTriageError, match="non-literal suspicious span"):
        apply_semantic_repairs([row], [decision])


def test_semantic_repair_rejects_duplicate_digest(locked_material):
    _, _, _, projection = locked_material
    row = projection.splits["train"][0]
    decision = CodexSemanticRepairDecision(
        expected_record_digest=record_digest(row),
        new_risk_tier=row["risk_tier"],
        new_suspicious_spans=row["suspicious_spans"],
        new_xai_explanation=row["xai_explanation"],
        notes="Duplicate fixture decision.",
    )
    with pytest.raises(MislabelTriageError, match="duplicate record digest"):
        apply_semantic_repairs([row], [decision, decision])


def test_locked_projection_has_expected_cap_split_and_lineage_profile(locked_material):
    _, _, _, projection = locked_material
    assert projection.validation["total_rows"] == 2_103
    assert projection.validation["split_counts"] == {"train": 1665, "val": 218, "test": 220}
    assert projection.validation["total_class_distribution"] == {
        "bank_impersonation": 743,
        "task_scam": 404,
        "benign": 655,
        "zalo_social_engineering": 301,
    }
    assert len(projection.quarantine_rows) == 176
    assert {row["original_record"]["seed_id"] for row in projection.quarantine_rows} == {
        "seed_157ce0adb043"
    }
    assert len(projection.cap_drop_rows) == 33
    assert Counter(row["seed_id"] for row in projection.cap_drop_rows) == {
        "seed_3f61921e9655": 19,
        "seed_825b9e38d185": 14,
    }
    assert projection.validation["unique_zalo_seeds"] == 61
    assert projection.validation["max_zalo_seed_count"] == 5


def test_stage_reloads_every_artifact_and_records_honest_audit(staged_bundle):
    candidate_dir, audit_path, payloads, _ = staged_bundle
    stats = validate_staged_candidate(candidate_dir, expected_payloads=payloads)
    assert stats["total_rows"] == 2_103
    assert len(read_jsonl(candidate_dir / "phase39-mislabel-decision-manifest.jsonl")) == 324
    assert len(read_jsonl(candidate_dir / "phase39-mislabel-quarantine.jsonl")) == 176
    assert len(read_jsonl(candidate_dir / "phase39-seed-cap-drops.jsonl")) == 33
    audit = audit_path.read_text(encoding="utf-8")
    assert "not independent annotation of the full corpus" in audit
    assert "human-approved Zalo semantics excluded" not in audit  # prose is explicit but not canned.
    assert "176 share the single seed" in audit
    assert "staged projection, not a frozen release" in audit


def test_semantic_quarantine_contract_recomputes_exact_2097_candidate(
    semantic_quarantine_bundle,
):
    _, candidate_dir = semantic_quarantine_bundle
    stats = validate_staged_candidate(candidate_dir)
    assert stats["total_rows"] == 2_097
    assert sum(stats["split_counts"].values()) == 2_097
    assert all(count > 0 for count in stats["total_class_distribution"].values())


@pytest.mark.parametrize(
    "mutator, message",
    [
        (
            lambda contract: contract.update(
                {"reason": "reviewer_requested_cleanup"}
            ),
            "fresh_judge_unrepairable_label",
        ),
        (
            lambda contract: contract.update({"split_salt": "wrong-salt"}),
            "split_salt",
        ),
        (
            lambda contract: contract["expected_profile"].update(
                {"total_rows": 2_096}
            ),
            "expected_profile",
        ),
        (
            lambda contract: contract["source_candidate"]["splits"].reverse(),
            "must be ordered",
        ),
    ],
)
def test_semantic_quarantine_contract_rejects_wrong_governance_or_profile(
    tmp_path,
    semantic_quarantine_bundle,
    mutator,
    message,
):
    _, candidate_dir = _copy_semantic_quarantine_fixture(
        semantic_quarantine_bundle, tmp_path
    )
    _mutate_quarantine_manifest(candidate_dir, mutator)
    with pytest.raises(MislabelTriageError, match=message):
        validate_staged_candidate(candidate_dir)


def test_post_quarantine_candidate_without_contract_uses_locked_2103_profile(
    tmp_path,
    semantic_quarantine_bundle,
):
    _, candidate_dir = _copy_semantic_quarantine_fixture(
        semantic_quarantine_bundle, tmp_path
    )
    manifest_path = candidate_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    del manifest["task_scam_mislabel_triage"]["semantic_quarantine_contract"]
    _write_json(manifest_path, manifest)
    _refresh_candidate_run_manifest_hash(candidate_dir)
    with pytest.raises(MislabelTriageError, match="expected 2103"):
        validate_staged_candidate(candidate_dir)


def test_semantic_quarantine_rejects_tampered_hash_bound_artifact(
    tmp_path,
    semantic_quarantine_bundle,
):
    root, candidate_dir = _copy_semantic_quarantine_fixture(
        semantic_quarantine_bundle, tmp_path
    )
    manifest = json.loads((candidate_dir / "manifest.json").read_text(encoding="utf-8"))
    artifact = manifest["task_scam_mislabel_triage"][
        "semantic_quarantine_contract"
    ]["quarantine_artifact"]
    (root / artifact["path"]).write_bytes(
        (root / artifact["path"]).read_bytes() + b"\n"
    )
    with pytest.raises(MislabelTriageError, match="artifact hash mismatch"):
        validate_staged_candidate(candidate_dir)


def test_semantic_quarantine_rejects_nonfailing_fresh_label_evidence(
    tmp_path,
    semantic_quarantine_bundle,
):
    root, candidate_dir = _copy_semantic_quarantine_fixture(
        semantic_quarantine_bundle, tmp_path
    )
    manifest_path = candidate_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    contract = manifest["task_scam_mislabel_triage"][
        "semantic_quarantine_contract"
    ]
    artifact = contract["quarantine_artifact"]
    artifact_path = root / artifact["path"]
    rows = module.read_jsonl(artifact_path)
    rows[0]["fresh_judge"]["label_correctness"] = 3
    rows[0]["fresh_judge"]["pass"] = True
    artifact_path.write_bytes(module.encode_jsonl(rows))
    artifact["sha256"] = module.sha256_path(artifact_path)
    _write_json(manifest_path, manifest)
    _refresh_candidate_run_manifest_hash(candidate_dir)
    with pytest.raises(MislabelTriageError, match="label_correctness below 3"):
        validate_staged_candidate(candidate_dir)


def test_semantic_quarantine_rejects_wrong_row_reason_even_when_rehashed(
    tmp_path,
    semantic_quarantine_bundle,
):
    root, candidate_dir = _copy_semantic_quarantine_fixture(
        semantic_quarantine_bundle, tmp_path
    )
    manifest_path = candidate_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    contract = manifest["task_scam_mislabel_triage"][
        "semantic_quarantine_contract"
    ]
    artifact = contract["quarantine_artifact"]
    artifact_path = root / artifact["path"]
    rows = module.read_jsonl(artifact_path)
    rows[0]["reason"] = "fresh_judge_low_realism"
    artifact_path.write_bytes(module.encode_jsonl(rows))
    artifact["sha256"] = module.sha256_path(artifact_path)
    _write_json(manifest_path, manifest)
    _refresh_candidate_run_manifest_hash(candidate_dir)
    with pytest.raises(MislabelTriageError, match="wrong reason"):
        validate_staged_candidate(candidate_dir)


def test_semantic_quarantine_rejects_wrong_cap_drop_even_when_rehashed(
    tmp_path,
    semantic_quarantine_bundle,
):
    root, candidate_dir = _copy_semantic_quarantine_fixture(
        semantic_quarantine_bundle, tmp_path
    )
    manifest_path = candidate_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    contract = manifest["task_scam_mislabel_triage"][
        "semantic_quarantine_contract"
    ]
    artifact = contract["cap_drop_artifact"]
    artifact_path = root / artifact["path"]
    rows = module.read_jsonl(artifact_path)
    rows[0]["reason"] = "plausible but unauthorized cap drop"
    artifact_path.write_bytes(module.encode_jsonl(rows))
    artifact["sha256"] = module.sha256_path(artifact_path)
    _write_json(manifest_path, manifest)
    _refresh_candidate_run_manifest_hash(candidate_dir)
    with pytest.raises(MislabelTriageError, match="deterministic recomputation"):
        validate_staged_candidate(candidate_dir)


def test_identical_restart_succeeds_without_rewriting(staged_bundle):
    candidate_dir, audit_path, payloads, audit_payload = staged_bundle
    before = {
        path: path.stat().st_mtime_ns
        for path in candidate_dir.rglob("*")
        if path.is_file()
    }
    before[audit_path] = audit_path.stat().st_mtime_ns
    reused = _stage_payloads(
        candidate_dir,
        audit_path,
        payloads,
        audit_payload,
        verify_callback=lambda: None,
    )
    after = {path: path.stat().st_mtime_ns for path in before}
    assert reused is True
    assert after == before


def test_nonempty_nonidentical_candidate_fails_closed(tmp_path, staged_bundle):
    _, _, payloads, audit_payload = staged_bundle
    candidate_dir = tmp_path / "candidate"
    candidate_dir.mkdir()
    (candidate_dir / "unexpected.txt").write_text("do not overwrite", encoding="utf-8")
    with pytest.raises(MislabelTriageError, match="candidate file set differs"):
        _stage_payloads(
            candidate_dir,
            tmp_path / "audit.md",
            payloads,
            audit_payload,
            verify_callback=lambda: None,
        )
    assert (candidate_dir / "unexpected.txt").read_text(encoding="utf-8") == "do not overwrite"


def test_simultaneous_lock_acquisition_fails_closed(tmp_path, staged_bundle):
    _, _, payloads, audit_payload = staged_bundle
    candidate_dir = tmp_path / "candidate"
    lock_path = candidate_dir.parent / f".{candidate_dir.name}.lock"
    with exclusive_run_lock(lock_path):
        with pytest.raises(MislabelTriageError, match="another Phase 39 candidate writer"):
            _stage_payloads(
                candidate_dir,
                tmp_path / "audit.md",
                payloads,
                audit_payload,
                verify_callback=lambda: None,
            )
    assert not candidate_dir.exists() or not any(candidate_dir.rglob("*"))


def test_source_hash_drift_stops_before_candidate_write(tmp_path):
    wrong = dict(EXPECTED_INPUT_SHA256)
    wrong["train.jsonl"] = "0" * 64
    with pytest.raises(MislabelTriageError, match="immutable input hash lock failed"):
        run_stage(
            splits_dir=SPLITS_DIR,
            manifest_path=MANIFEST_PATH,
            merged_judge_path=MERGED_PATH,
            decisions_path=DECISIONS_PATH,
            candidate_dir=tmp_path / "candidate",
            audit_output=tmp_path / "audit.md",
            protected_review_paths=PROTECTED_PATHS,
            expected_input_sha256=wrong,
            repo_root=REPO_ROOT,
        )
    assert not (tmp_path / "candidate").exists()


def test_bundle_write_failure_restores_every_original_byte(tmp_path, monkeypatch):
    destinations = {
        "one": tmp_path / "one.bin",
        "two": tmp_path / "two.bin",
        "three": tmp_path / "three.bin",
    }
    originals = {"one": b"old-one", "two": b"old-two", "three": None}
    destinations["one"].write_bytes(originals["one"])
    destinations["two"].write_bytes(originals["two"])
    payloads = {"one": b"new-one", "two": b"new-two", "three": b"new-three"}
    real_write = module._write_bytes_atomically

    def fail_second(path, payload):
        if path == destinations["two"] and payload == b"new-two":
            raise OSError("injected write failure")
        real_write(path, payload)

    monkeypatch.setattr(module, "_write_bytes_atomically", fail_second)
    with pytest.raises(OSError, match="injected write failure"):
        replace_payload_bundle(
            destinations,
            payloads,
            originals,
            operation="fixture",
        )
    assert destinations["one"].read_bytes() == b"old-one"
    assert destinations["two"].read_bytes() == b"old-two"
    assert not destinations["three"].exists()


def test_post_write_verification_failure_rolls_back_all_destinations(tmp_path):
    destinations = {"one": tmp_path / "one.bin", "two": tmp_path / "two.bin"}
    originals = {"one": b"old-one", "two": None}
    destinations["one"].write_bytes(b"old-one")
    with pytest.raises(RuntimeError, match="reject staged bytes"):
        replace_payload_bundle(
            destinations,
            {"one": b"new-one", "two": b"new-two"},
            originals,
            operation="fixture",
            verify_written=lambda: (_ for _ in ()).throw(RuntimeError("reject staged bytes")),
        )
    assert destinations["one"].read_bytes() == b"old-one"
    assert not destinations["two"].exists()


def test_rollback_failure_reports_composite_and_continues(tmp_path, monkeypatch):
    destinations = {"one": tmp_path / "one.bin", "two": tmp_path / "two.bin"}
    originals = {"one": b"old-one", "two": b"old-two"}
    for key, path in destinations.items():
        path.write_bytes(originals[key])
    real_write = module._write_bytes_atomically

    def fail_one_restore(path, payload):
        if path == destinations["one"] and payload == b"old-one":
            raise OSError("injected rollback failure")
        real_write(path, payload)

    monkeypatch.setattr(module, "_write_bytes_atomically", fail_one_restore)
    with pytest.raises(MislabelTriageError, match=r"rollback incomplete:.*restore one"):
        replace_payload_bundle(
            destinations,
            {"one": b"new-one", "two": b"new-two"},
            originals,
            operation="fixture",
            verify_written=lambda: (_ for _ in ()).throw(RuntimeError("reject")),
        )
    assert destinations["one"].read_bytes() == b"new-one"
    assert destinations["two"].read_bytes() == b"old-two"


def test_promotion_verification_failure_restores_all_live_destinations(
    tmp_path, staged_bundle, monkeypatch
):
    candidate_dir, _, _, _ = staged_bundle
    canonical = tmp_path / "canonical"
    canonical.mkdir()
    original_bytes = {}
    for name in ("train", "val", "test"):
        path = canonical / f"{name}.jsonl"
        payload = f"old-{name}".encode()
        path.write_bytes(payload)
        original_bytes[path] = payload
    manifest_path = canonical / "manifest.json"
    manifest_path.write_bytes(b"old-manifest")
    original_bytes[manifest_path] = b"old-manifest"

    # This test targets the transaction seam, not the already-covered costly
    # corpus gates; replace them with no-op validators around the injected
    # post-promotion failure.
    monkeypatch.setattr(module, "validate_staged_candidate", lambda *args, **kwargs: {})
    monkeypatch.setattr(module, "validate_candidate_splits", lambda *args, **kwargs: {})
    with pytest.raises(RuntimeError, match="reject promoted bundle"):
        promote_candidate_bundle(
            candidate_dir,
            canonical,
            manifest_path,
            verify_promoted=lambda: (_ for _ in ()).throw(
                RuntimeError("reject promoted bundle")
            ),
        )
    for path, payload in original_bytes.items():
        assert path.read_bytes() == payload


def test_locked_sources_and_user_artifacts_are_still_byte_identical():
    actual_inputs = {
        "train.jsonl": sha256_path(SPLITS_DIR / "train.jsonl"),
        "val.jsonl": sha256_path(SPLITS_DIR / "val.jsonl"),
        "test.jsonl": sha256_path(SPLITS_DIR / "test.jsonl"),
        "manifest.json": sha256_path(MANIFEST_PATH),
        "judge-merged.jsonl": sha256_path(MERGED_PATH),
        "MISLABEL triage.md": sha256_path(DECISIONS_PATH),
    }
    assert actual_inputs == EXPECTED_INPUT_SHA256
    assert {key: sha256_path(path) for key, path in PROTECTED_PATHS.items()} == (
        EXPECTED_PROTECTED_AUDIT_SHA256
    )


def test_module_has_no_external_provider_or_network_path():
    source = inspect.getsource(module)
    forbidden = (
        "req" + "uests",
        "url" + "lib",
        "http" + "x",
        "anth" + "ropic",
        "open" + "ai",
        "_call_" + "claude",
        "_call_" + "gemini",
    )
    assert not any(token in source.lower() for token in forbidden)


def _between_once(text: str, start: str, end: str) -> str:
    assert text.count(start) == 1
    assert text.count(end) == 1
    return text.split(start, 1)[1].split(end, 1)[0]


def test_downstream_contract_matches_live_manifest_and_active_planning_regions():
    contract_path = (
        PHASE_DIR / "39-DOWNSTREAM-DATA-CONTRACT.json"
    )
    report = validate_downstream_data_contract(
        contract_path=contract_path,
        manifest_path=REPO_ROOT / "data/manifests/manifest.json",
        splits_dir=REPO_ROOT / "data/splits",
    )
    assert report["total_records"] == 2_097
    assert report["split_counts"] == {"train": 1_658, "val": 219, "test": 220}
    assert report["held_out_test"]["sha256"] == (
        "6f208fb6cd9399b8934225e6a25efd65d49bbb4f4846360837f6835a2561b6d7"
    )

    project = (REPO_ROOT / ".planning/PROJECT.md").read_text(encoding="utf-8")
    project_active = _between_once(project, "### Active", "### Out of Scope")
    project_target = _between_once(
        project, "**Target features:**", "**Explicit non-goals:**"
    )
    requirements = (REPO_ROOT / ".planning/REQUIREMENTS.md").read_text(encoding="utf-8")
    eval_region = _between_once(
        requirements, "### Held-Out Evaluation Discipline", "### Report Overhaul"
    )
    roadmap = (REPO_ROOT / ".planning/ROADMAP.md").read_text(encoding="utf-8")
    phase40 = _between_once(
        roadmap,
        "### Phase 40: Multi-Model Training Evidence",
        "### Phase 41: Held-Out Evaluation Discipline",
    )
    phase41 = _between_once(
        roadmap,
        "### Phase 41: Held-Out Evaluation Discipline",
        "### Phase 42: Report Overhaul",
    )
    state = (REPO_ROOT / ".planning/STATE.md").read_text(encoding="utf-8")
    state_focus = next(
        line for line in state.splitlines() if line.startswith("- Current milestone focus:")
    )
    phase40_decisions = [
        line for line in state.splitlines() if line.startswith("- [Phase 40 planning]:")
    ]
    assert len(phase40_decisions) == 1
    context = (
        REPO_ROOT / ".planning/phases/40-multi-model-training-evidence/40-CONTEXT.md"
    ).read_text(encoding="utf-8")
    context_decisions = _between_once(context, "<decisions>", "</decisions>")

    active_regions = (
        project_active,
        project_target,
        eval_region,
        phase40,
        phase41,
        state_focus,
        phase40_decisions[0],
        context_decisions,
    )
    stale_tokens = (
        "2,403",
        "1,900",
        "251-row",
        "251 test",
        "019aec39979429ca8005dd299d2ddaf7d3ecfdade259eecc4d3129adaed25938",
        "6454a271c6133f1ebbd41010390b8ea6ceae0a8ab0a75b2ab545099db3319ee8",
        "7adfe8cd9a124dbb3d87046bb32f9fbd127d3e344c45be77c8bb9efa700aaa75",
    )
    for region in active_regions:
        assert not any(token in region for token in stale_tokens)
    assert "1,658 training rows, 219 validation rows, and 220 held-out test rows" in phase40
    assert "Phase 42 is not a training prerequisite" in phase40
    assert "220-row test partition" in eval_region
    assert "all-2,097-row deployment fit" in eval_region
    assert report["manifest_sha256"] in context_decisions
    assert report["held_out_test"]["sha256"] in "\n".join(active_regions)
    # The dated quick-task statement remains historical and intentionally old.
    assert "corrected 2,403-row retraining snapshot" in state
