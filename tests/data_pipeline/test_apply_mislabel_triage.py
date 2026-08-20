"""Regression coverage for the Phase 39 staged mislabel migration."""

from __future__ import annotations

import copy
import inspect
import json
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


REPO_ROOT = Path(__file__).resolve().parents[2]
PHASE_DIR = REPO_ROOT / ".planning/phases/39-independent-quality-re-judge"
DECISIONS_PATH = PHASE_DIR / "MISLABEL triage.md"
MERGED_PATH = REPO_ROOT / "data/processed/judge-merged.jsonl"
SPLITS_DIR = REPO_ROOT / "data/splits"
MANIFEST_PATH = REPO_ROOT / "data/manifests/manifest.json"
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
