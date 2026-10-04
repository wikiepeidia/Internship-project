"""Tests for the Phase 39 Codex judge-output merge/validation tool.

Proves judge_merge.py end-to-end against realistic fixture data shaped
exactly like .planning/codex-judge-instructions.md's output schema. Real
Codex output (data/processed/codex-judge-pass.jsonl) does not exist yet --
these tests use only fixtures.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import pytest

from src.data_pipeline.judge_merge import (
    SemanticQuarantineTransition,
    _validate_semantic_quarantine_transition,
    ConvergenceArtifact,
    FinalJudgeResult,
    FinalJudgeProvenanceRow,
    FinalJudgeTarget,
    build_final_judge_partition,
    compose_final_judge_evidence,
    complete_batch,
    CodexJudgeResult,
    compute_aggregate_stats,
    dataset_record_digest,
    judge_evidence_digest,
    load_judge_results,
    load_source_splits,
    main,
    materialize_batch_bundle,
    merge_judge_results,
    render_downstream_data_contract_from_metadata,
    sha256_path,
    validate_batch_bundle,
    validate_carries_against_historical_backup,
    validate_downstream_data_contract,
    validate_downstream_data_contract_live,
    validate_semantic_convergence,
    write_merge_outputs,
)
from src.data_pipeline.apply_mislabel_triage import record_identity
from src.data_pipeline.repair_corpus_split_governance import assign_stratified_group_split

_DIMENSIONS = (
    "realism",
    "label_correctness",
    "code_switch_naturalness",
    "risk_tier_correctness",
    "suspicious_span_accuracy",
)


def _downstream_metadata_fixture() -> dict[str, Any]:
    split_rows = {"train": 8, "val": 1, "test": 1}
    split_distributions = {
        "train": {
            "bank_impersonation": 2,
            "task_scam": 2,
            "benign": 2,
            "zalo_social_engineering": 2,
        },
        "val": {
            "bank_impersonation": 1,
            "task_scam": 0,
            "benign": 0,
            "zalo_social_engineering": 0,
        },
        "test": {
            "bank_impersonation": 0,
            "task_scam": 1,
            "benign": 0,
            "zalo_social_engineering": 0,
        },
    }
    files = {
        name + ".jsonl": {
            "sha256": str(index + 1) * 64,
            "records": split_rows[name],
            "bytes": 100 + index,
        }
        for index, name in enumerate(("train", "val", "test"))
    }
    return {
        "manifest": {"version": "fixture-v1", "files": files},
        "split_class_distribution": split_distributions,
        "task_scam_mislabel_triage": {
            "split_governance": {"salt": "fixture-salt"},
            "validation": {"max_seed_share": 0.08},
        },
        "phase39_final_release": {"status": "promoted"},
    }


def test_downstream_contract_default_validation_is_metadata_only(tmp_path, monkeypatch):
    manifest_path = tmp_path / "manifest.json"
    contract_path = tmp_path / "contract.json"
    manifest_path.write_text(
        json.dumps(_downstream_metadata_fixture(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    contract = render_downstream_data_contract_from_metadata(
        manifest_path=manifest_path,
        generated_at="2026-08-26T00:00:00+07:00",
    )
    contract_path.write_text(
        json.dumps(contract, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    import src.data_pipeline.judge_merge as module

    monkeypatch.setattr(
        module,
        "load_source_splits",
        lambda *_args, **_kwargs: pytest.fail("metadata validation loaded split rows"),
    )
    monkeypatch.setattr(
        module,
        "render_downstream_data_contract",
        lambda *_args, **_kwargs: pytest.fail("metadata validation used live renderer"),
    )

    report = validate_downstream_data_contract(
        contract_path=contract_path,
        manifest_path=manifest_path,
    )

    assert report["validation_scope"] == "metadata_only"
    assert report["split_counts"] == {"train": 8, "val": 1, "test": 1}


def test_live_downstream_validator_rejects_trap_path_before_any_io(
    tmp_path, monkeypatch
):
    import src.data_pipeline.judge_merge as module

    trap_root = tmp_path / "reserved-split-trap"
    monkeypatch.delenv("VNPHISH_ENABLE_LIVE_SPLIT_INTEGRITY_AUDIT", raising=False)
    original_stat = Path.stat
    original_open = Path.open
    original_iterdir = Path.iterdir
    original_scandir = module.os.scandir
    original_sha256 = module.sha256_path

    def is_trap(path: Path) -> bool:
        candidate = Path(path)
        return candidate == trap_root or trap_root in candidate.parents

    def trap_stat(path: Path, *args, **kwargs):
        if is_trap(path):
            pytest.fail("live validator statted the trap path before opt-in")
        return original_stat(path, *args, **kwargs)

    def trap_open(path: Path, *args, **kwargs):
        if is_trap(path):
            pytest.fail("live validator opened the trap path before opt-in")
        return original_open(path, *args, **kwargs)

    def trap_iterdir(path: Path):
        if is_trap(path):
            pytest.fail("live validator enumerated the trap path before opt-in")
        return original_iterdir(path)

    def trap_scandir(path):
        if is_trap(Path(path)):
            pytest.fail("live validator scanned the trap path before opt-in")
        return original_scandir(path)

    def trap_sha256(path: Path):
        if is_trap(path):
            pytest.fail("live validator hashed the trap path before opt-in")
        return original_sha256(path)

    monkeypatch.setattr(Path, "stat", trap_stat)
    monkeypatch.setattr(Path, "open", trap_open)
    monkeypatch.setattr(Path, "iterdir", trap_iterdir)
    monkeypatch.setattr(module.os, "scandir", trap_scandir)
    monkeypatch.setattr(module, "sha256_path", trap_sha256)
    monkeypatch.setattr(
        module,
        "load_source_splits",
        lambda *_args, **_kwargs: pytest.fail("live validator parsed trap split rows"),
    )

    with pytest.raises(ValueError, match="disabled by default"):
        validate_downstream_data_contract_live(
            contract_path=tmp_path / "absent-contract.json",
            manifest_path=tmp_path / "absent-manifest.json",
            splits_dir=trap_root,
        )


def _make_source_row(
    seed_id: str,
    text: str,
    label: str = "bank_impersonation",
    spans: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "text": text,
        "label": label,
        "risk_tier": "benign" if label == "benign" else "high-risk",
        "suspicious_spans": spans if spans is not None else [],
        "xai_explanation": "Giai thich du dai cho ban ghi kiem thu cong cu gop judge ket qua that.",
        "source": "synthetic_claude",
        "seed_id": seed_id,
    }


def _make_judge_line(
    split: str,
    row_index: int,
    seed_id: str,
    *,
    realism: int = 4,
    label_correctness: int = 4,
    code_switch_naturalness: int = 4,
    risk_tier_correctness: int = 4,
    suspicious_span_accuracy: int = 4,
    judge_pass: bool = True,
    reason: str = "Reads naturally and label matches content.",
) -> dict[str, Any]:
    return {
        "split": split,
        "row_index": row_index,
        "seed_id": seed_id,
        "realism": realism,
        "label_correctness": label_correctness,
        "code_switch_naturalness": code_switch_naturalness,
        "risk_tier_correctness": risk_tier_correctness,
        "suspicious_span_accuracy": suspicious_span_accuracy,
        "pass": judge_pass,
        "reason": reason,
    }


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


# --- load_judge_results -------------------------------------------------


def test_load_judge_results_parses_well_formed_fixture(tmp_path):
    path = tmp_path / "judge.jsonl"
    _write_jsonl(
        path,
        [
            _make_judge_line("train", 0, "seed_abc123", judge_pass=True),
            _make_judge_line("train", 1, "seed_def456", judge_pass=False, realism=2),
        ],
    )

    results = load_judge_results(path)

    assert len(results) == 2
    assert all(isinstance(result, CodexJudgeResult) for result in results)
    first = results[0]
    assert isinstance(first.row_index, int)
    assert first.row_index == 0
    for dim in _DIMENSIONS:
        score = getattr(first, dim)
        assert isinstance(score, int)
        assert 1 <= score <= 5
    assert first.judge_pass is True
    assert results[1].judge_pass is False


def test_load_judge_results_raises_on_out_of_range_score(tmp_path):
    path = tmp_path / "judge.jsonl"
    _write_jsonl(
        path,
        [
            _make_judge_line("train", 0, "seed_abc123"),
            _make_judge_line("train", 1, "seed_def456", realism=6),
        ],
    )

    with pytest.raises(ValueError, match="line 2"):
        load_judge_results(path)


def test_load_judge_results_raises_on_missing_required_field(tmp_path):
    path = tmp_path / "judge.jsonl"
    good_row = _make_judge_line("train", 0, "seed_abc123")
    bad_row = _make_judge_line("train", 1, "seed_def456")
    del bad_row["seed_id"]
    _write_jsonl(path, [good_row, bad_row])

    with pytest.raises(ValueError, match="line 2"):
        load_judge_results(path)


# --- merge_judge_results --------------------------------------------------


def _fixture_source_splits() -> dict[str, list[dict[str, Any]]]:
    return {
        "train": [
            _make_source_row("seed_train_0", "Tin nhan train so 0 du dai hop le de test."),
            _make_source_row("seed_train_1", "Tin nhan train so 1 du dai hop le de test."),
            _make_source_row("seed_train_2", "Tin nhan train so 2 du dai hop le de test."),
        ],
        "val": [
            _make_source_row("seed_val_0", "Tin nhan val so 0 du dai hop le de test."),
            _make_source_row("seed_val_1", "Tin nhan val so 1 du dai hop le de test."),
        ],
        "test": [
            _make_source_row("seed_test_0", "Tin nhan test so 0 du dai hop le de test."),
            _make_source_row("seed_test_1", "Tin nhan test so 1 du dai hop le de test."),
        ],
    }


def _fixture_judge_results() -> list[CodexJudgeResult]:
    lines = [
        _make_judge_line("train", 0, "seed_train_0"),
        _make_judge_line("train", 1, "seed_train_1"),
        _make_judge_line("train", 2, "seed_train_2"),
        _make_judge_line("val", 0, "seed_val_0"),
        _make_judge_line("val", 1, "seed_val_1"),
        _make_judge_line("test", 0, "seed_test_0"),
        _make_judge_line("test", 1, "seed_test_1"),
    ]
    return [CodexJudgeResult.model_validate(line) for line in lines]


def test_merge_judge_results_joins_every_row_with_all_fields():
    source_splits = _fixture_source_splits()
    judge_results = _fixture_judge_results()

    merged, coverage = merge_judge_results(judge_results, source_splits)

    assert len(merged) == 7
    source_fields = {"text", "label", "risk_tier", "suspicious_spans", "xai_explanation", "source", "seed_id"}
    judge_fields = {
        "split",
        "row_index",
        "realism",
        "label_correctness",
        "code_switch_naturalness",
        "risk_tier_correctness",
        "suspicious_span_accuracy",
        "judge_pass",
        "judge_reason",
        "recomputed_pass",
    }
    for row in merged:
        assert source_fields | judge_fields <= set(row.keys())
    assert coverage["train"] == {"source_rows": 3, "judge_rows": 3}
    assert coverage["val"] == {"source_rows": 2, "judge_rows": 2}
    assert coverage["test"] == {"source_rows": 2, "judge_rows": 2}


def test_merge_judge_results_raises_on_seed_id_mismatch():
    source_splits = _fixture_source_splits()
    lines = [
        _make_judge_line("train", 0, "seed_WRONG"),
        _make_judge_line("train", 1, "seed_train_1"),
        _make_judge_line("train", 2, "seed_train_2"),
        _make_judge_line("val", 0, "seed_val_0"),
        _make_judge_line("val", 1, "seed_val_1"),
        _make_judge_line("test", 0, "seed_test_0"),
        _make_judge_line("test", 1, "seed_test_1"),
    ]
    judge_results = [CodexJudgeResult.model_validate(line) for line in lines]

    with pytest.raises(ValueError, match="train.*row_index 0"):
        merge_judge_results(judge_results, source_splits)


def test_merge_judge_results_raises_on_missing_row_index():
    source_splits = _fixture_source_splits()
    lines = [
        _make_judge_line("train", 0, "seed_train_0"),
        _make_judge_line("train", 1, "seed_train_1"),
        # train row_index 2 missing
        _make_judge_line("val", 0, "seed_val_0"),
        _make_judge_line("val", 1, "seed_val_1"),
        _make_judge_line("test", 0, "seed_test_0"),
        _make_judge_line("test", 1, "seed_test_1"),
    ]
    judge_results = [CodexJudgeResult.model_validate(line) for line in lines]

    with pytest.raises(ValueError, match=r"train.*missing row_index\(es\) \(first 20: \[2\]\)"):
        merge_judge_results(judge_results, source_splits)


def test_merge_judge_results_raises_on_duplicate_row_index():
    source_splits = _fixture_source_splits()
    lines = [
        _make_judge_line("train", 0, "seed_train_0"),
        _make_judge_line("train", 1, "seed_train_1"),
        _make_judge_line("train", 1, "seed_train_1"),  # duplicate row_index 1
        _make_judge_line("train", 2, "seed_train_2"),
        _make_judge_line("val", 0, "seed_val_0"),
        _make_judge_line("val", 1, "seed_val_1"),
        _make_judge_line("test", 0, "seed_test_0"),
        _make_judge_line("test", 1, "seed_test_1"),
    ]
    judge_results = [CodexJudgeResult.model_validate(line) for line in lines]

    with pytest.raises(ValueError, match=r"train.*duplicate row_index\(es\) \(first 20: \[1\]\)"):
        merge_judge_results(judge_results, source_splits)


# --- compute_aggregate_stats ----------------------------------------------


def _stats_fixture_merged() -> list[dict[str, Any]]:
    def row(split: str, row_index: int, score: int, judge_pass: bool) -> dict[str, Any]:
        scores = {dim: score for dim in _DIMENSIONS}
        return {
            "split": split,
            "row_index": row_index,
            **scores,
            "judge_pass": judge_pass,
            "judge_reason": "fixture reason",
            "recomputed_pass": all(s >= 3 for s in scores.values()),
        }

    return [
        row("train", 0, 5, True),
        row("train", 1, 4, True),
        row("val", 0, 2, False),
        row("test", 0, 3, True),
    ]


def test_compute_aggregate_stats_matches_hand_computed_values():
    merged = _stats_fixture_merged()

    stats = compute_aggregate_stats(merged)

    assert stats["total"] == 4
    assert stats["passed"] == 3
    assert stats["pass_rate"] == pytest.approx(0.75)
    for dim in _DIMENSIONS:
        assert stats[f"avg_{dim}"] == pytest.approx((5 + 4 + 2 + 3) / 4)
    assert stats["per_split"] == {
        "train": {"total": 2, "passed": 2, "pass_rate": pytest.approx(1.0)},
        "val": {"total": 1, "passed": 0, "pass_rate": pytest.approx(0.0)},
        "test": {"total": 1, "passed": 1, "pass_rate": pytest.approx(1.0)},
    }


def test_compute_aggregate_stats_reports_pass_mismatch_count():
    merged = _stats_fixture_merged()
    # Row 0 (train, all scores 5, recomputed_pass True) declares judge_pass False --
    # a self-reported disagreement with its own scores.
    merged[0]["judge_pass"] = False

    stats = compute_aggregate_stats(merged)

    assert stats["pass_mismatch_count"] == 1


# --- write_merge_outputs / end-to-end tracer ------------------------------


def test_end_to_end_tracer_round_trips_through_disk(tmp_path):
    splits_dir = tmp_path / "splits"
    source_splits = _fixture_source_splits()
    for split_name, rows in source_splits.items():
        _write_jsonl(splits_dir / f"{split_name}.jsonl", rows)

    judge_results_path = tmp_path / "codex-judge-pass.jsonl"
    _write_jsonl(
        judge_results_path,
        [
            _make_judge_line("train", 0, "seed_train_0"),
            _make_judge_line("train", 1, "seed_train_1"),
            _make_judge_line("train", 2, "seed_train_2"),
            _make_judge_line("val", 0, "seed_val_0"),
            _make_judge_line("val", 1, "seed_val_1"),
            _make_judge_line("test", 0, "seed_test_0"),
            _make_judge_line("test", 1, "seed_test_1", judge_pass=False, realism=2),
        ],
    )

    judge_results = load_judge_results(judge_results_path)
    loaded_source_splits = load_source_splits(splits_dir)
    merged, coverage = merge_judge_results(judge_results, loaded_source_splits)
    stats = compute_aggregate_stats(merged)
    stats["coverage"] = coverage

    merged_path = tmp_path / "out" / "judge-merged.jsonl"
    summary_path = tmp_path / "out" / "judge-summary.json"
    write_merge_outputs(merged, stats, merged_path, summary_path)

    assert merged_path.exists()
    assert summary_path.exists()

    read_back_merged = [
        json.loads(line) for line in merged_path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    assert read_back_merged == merged

    read_back_summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert read_back_summary == stats


def test_load_source_splits_raises_actionable_error_on_missing_split_file(tmp_path):
    splits_dir = tmp_path / "splits"
    source_splits = _fixture_source_splits()
    for split_name, rows in source_splits.items():
        if split_name == "test":
            continue  # simulate test.jsonl not written yet
        _write_jsonl(splits_dir / f"{split_name}.jsonl", rows)

    with pytest.raises(FileNotFoundError, match=r"test\.jsonl does not exist"):
        load_source_splits(splits_dir)


# --- main() fail-closed guard ----------------------------------------------


def test_main_raises_actionable_error_when_judge_results_missing(tmp_path, monkeypatch):
    missing_path = tmp_path / "does-not-exist.jsonl"
    monkeypatch.setattr(sys, "argv", ["judge_merge", "--judge-results", str(missing_path)])

    with pytest.raises(FileNotFoundError, match=r"\.planning/codex-judge-instructions\.md"):
        main()


# --- exact final-snapshot identity and carry/delta preparation ------------


def _historical_merged_row(
    record: dict[str, Any],
    *,
    split: str = "test",
    row_index: int = 91,
    score: int = 4,
    reason: str = "Historical evidence stays byte-for-evidence identical.",
) -> dict[str, Any]:
    return {
        **record,
        "split": split,
        "row_index": row_index,
        **{dimension: score for dimension in _DIMENSIONS},
        "judge_pass": score >= 3,
        "judge_reason": reason,
        "recomputed_pass": score >= 3,
    }


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("text", "Mot tin nhan hoan toan khac nhung van du dai de hop le."),
        ("label", "task_scam"),
        ("risk_tier", "suspicious"),
        ("suspicious_spans", ["Tin nhan"]),
        ("xai_explanation", "Mot giai thich khac du dai de chung minh digest nhay cam."),
        ("source", "synthetic_gemini"),
        ("seed_id", "seed_digest_changed"),
    ],
)
def test_dataset_record_digest_is_sensitive_to_every_dataset_field(field, replacement):
    record = _make_source_row(
        "seed_digest_base",
        "Tin nhan ngan hang gia mao du dai de kiem thu digest bay truong.",
        spans=[],
    )
    changed = {**record, field: replacement}

    assert dataset_record_digest(record) != dataset_record_digest(changed)


def test_build_final_partition_carries_only_unique_exact_record_and_rebases_coordinates():
    carried = _make_source_row(
        "seed_carried",
        "Tin nhan carried du dai de kiem thu viec rebase toa do cu sang moi.",
    )
    changed = _make_source_row(
        "seed_changed",
        "Tin nhan changed du dai de bat buoc mot lan danh gia hoan toan moi.",
        label="task_scam",
    )
    historical_changed = {**changed, "risk_tier": "suspicious"}
    historical = [
        _historical_merged_row(
            carried,
            split="test",
            row_index=91,
            score=5,
            reason="Exact old verdict must survive unchanged.",
        ),
        _historical_merged_row(historical_changed, split="train", row_index=3),
    ]

    carries, delta = build_final_judge_partition(
        {"train": [carried], "val": [changed], "test": []},
        historical,
        candidate_manifest_sha256="a" * 64,
        candidate_split_sha256={"train": "b" * 64, "val": "c" * 64, "test": "d" * 64},
        historical_merged_sha256="e" * 64,
    )

    assert len(carries) == 1
    assert len(delta) == 1
    carried_row = carries[0]
    assert carried_row.result.split == "train"
    assert carried_row.result.row_index == 0
    assert carried_row.result.reason == "Exact old verdict must survive unchanged."
    assert carried_row.provenance.historical_split == "test"
    assert carried_row.provenance.historical_row_index == 91
    assert carried_row.provenance.verdict_origin == "carried_forward_exact_record"
    assert carried_row.provenance.evidence_digest == judge_evidence_digest(
        carried_row.result
    )
    assert delta[0].split == "val"
    assert delta[0].row_index == 0
    assert delta[0].record_digest == dataset_record_digest(changed)


def test_ambiguous_historical_digest_routes_to_fresh_delta():
    record = _make_source_row(
        "seed_ambiguous",
        "Tin nhan trung lap lich su du dai de kiem thu unique-only carry policy.",
    )
    historical = [
        _historical_merged_row(record, split="train", row_index=1),
        _historical_merged_row(record, split="val", row_index=2),
    ]

    carries, delta = build_final_judge_partition(
        {"train": [record], "val": [], "test": []},
        historical,
        candidate_manifest_sha256="a" * 64,
        candidate_split_sha256={"train": "b" * 64, "val": "c" * 64, "test": "d" * 64},
        historical_merged_sha256="e" * 64,
    )

    assert carries == []
    assert [target.record_digest for target in delta] == [dataset_record_digest(record)]


# --- deterministic restartable judge batches -----------------------------


def _target(index: int) -> FinalJudgeTarget:
    record = _make_source_row(
        f"seed_batch_{index:04d}",
        f"Tin nhan batch {index:04d} du dai de kiem thu queue bat dau lai an toan.",
        label="task_scam",
    )
    return FinalJudgeTarget.from_record("train", index, record)


def _fresh_result(target: FinalJudgeTarget, *, score: int = 4) -> dict[str, Any]:
    return {
        "split": target.split,
        "row_index": target.row_index,
        "seed_id": target.seed_id,
        "record_digest": target.record_digest,
        **{dimension: score for dimension in _DIMENSIONS},
        "pass": score >= 3,
        "reason": "Current-session row judgment with a concrete concise reason.",
    }


def test_materialized_batches_are_fixed_size_hash_bound_and_pending(tmp_path):
    targets = [_target(index) for index in range(130)]
    aggregate = tmp_path / "phase39-final-judge-delta-targets.jsonl"
    carry = tmp_path / "phase39-final-judge-carry.jsonl"
    batch_dir = tmp_path / "iteration-00"

    manifest_path = materialize_batch_bundle(
        targets=targets,
        carries=[],
        aggregate_targets_path=aggregate,
        carry_path=carry,
        batch_dir=batch_dir,
        candidate_dir=tmp_path / "candidate",
        candidate_manifest_sha256="a" * 64,
        historical_merged_sha256="b" * 64,
        batch_size=64,
        iteration=0,
    )
    report = validate_batch_bundle(
        manifest_path,
        targets_path=aggregate,
        carry_path=carry,
        require_status="pending",
    )

    assert report["target_count"] == 130
    assert report["batch_counts"] == [64, 64, 2]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert [entry["status"] for entry in manifest["batches"]] == ["pending"] * 3
    assert [entry["result_sha256"] for entry in manifest["batches"]] == [None] * 3
    assert all(not Path(entry["result_path"]).exists() for entry in manifest["batches"])


def test_completed_batch_restart_is_idempotent_and_conflict_fails_closed(tmp_path):
    target = _target(0)
    aggregate = tmp_path / "targets.jsonl"
    carry = tmp_path / "carry.jsonl"
    batch_dir = tmp_path / "iteration-00"
    manifest_path = materialize_batch_bundle(
        targets=[target],
        carries=[],
        aggregate_targets_path=aggregate,
        carry_path=carry,
        batch_dir=batch_dir,
        candidate_dir=tmp_path / "candidate",
        candidate_manifest_sha256="a" * 64,
        historical_merged_sha256="b" * 64,
        batch_size=64,
        iteration=0,
    )
    result_path = batch_dir / "batch-0001-results.jsonl"
    _write_jsonl(result_path, [_fresh_result(target)])

    first = complete_batch(manifest_path, "batch-0001")
    before = manifest_path.read_bytes()
    second = complete_batch(manifest_path, "batch-0001")

    assert first["reused"] is False
    assert second["reused"] is True
    assert manifest_path.read_bytes() == before

    _write_jsonl(result_path, [_fresh_result(target, score=3)])
    with pytest.raises(ValueError, match="completed batch.*result SHA-256"):
        complete_batch(manifest_path, "batch-0001")
    assert json.loads(manifest_path.read_text(encoding="utf-8"))["batches"][0]["status"] == "complete"


def test_partial_or_wrong_result_never_marks_pending_batch_complete(tmp_path):
    targets = [_target(0), _target(1)]
    aggregate = tmp_path / "targets.jsonl"
    carry = tmp_path / "carry.jsonl"
    batch_dir = tmp_path / "iteration-00"
    manifest_path = materialize_batch_bundle(
        targets=targets,
        carries=[],
        aggregate_targets_path=aggregate,
        carry_path=carry,
        batch_dir=batch_dir,
        candidate_dir=tmp_path / "candidate",
        candidate_manifest_sha256="a" * 64,
        historical_merged_sha256="b" * 64,
        batch_size=64,
        iteration=0,
    )
    result_path = batch_dir / "batch-0001-results.jsonl"
    _write_jsonl(result_path, [_fresh_result(targets[0])])

    with pytest.raises(ValueError, match="result coverage"):
        complete_batch(manifest_path, "batch-0001")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["batches"][0]["status"] == "pending"
    assert manifest["batches"][0]["result_sha256"] is None
    assert result_path.exists()


# --- semantic convergence -------------------------------------------------


def _artifact(path: Path, *, records: int | None = None) -> dict[str, Any]:
    return ConvergenceArtifact(
        path=str(path), sha256=sha256_path(path), records=records
    ).model_dump(mode="json")


def test_convergence_validator_recomputes_hashes_and_requires_later_fresh_verdict(tmp_path):
    before = _make_source_row(
        "seed_repair",
        "Tin nhan can sua semantic du dai de kiem thu re-judgment digest.",
        label="task_scam",
    )
    after = {
        **before,
        "risk_tier": "suspicious",
        "xai_explanation": "Giai thich da sua va du dai de rang buoc ket qua semantic moi.",
    }
    before_digest = dataset_record_digest(before)
    after_digest = dataset_record_digest(after)

    initial_manifest = tmp_path / "initial-manifest.json"
    initial_manifest.write_text("{}\n", encoding="utf-8")
    carry = tmp_path / "carry.jsonl"
    carry.write_text("", encoding="utf-8")
    targets = tmp_path / "targets.jsonl"
    _write_jsonl(targets, [FinalJudgeTarget.from_record("train", 0, before).model_dump(mode="json")])
    initial_batch_manifest = tmp_path / "initial-batches.json"
    initial_batch_manifest.write_text("{}\n", encoding="utf-8")
    before_split = tmp_path / "candidate-before.jsonl"
    after_split = tmp_path / "candidate-after.jsonl"
    _write_jsonl(before_split, [before])
    _write_jsonl(after_split, [after])
    semantic_targets = tmp_path / "semantic-targets.jsonl"
    _write_jsonl(semantic_targets, [FinalJudgeTarget.from_record("train", 0, before).model_dump(mode="json")])
    repairs = tmp_path / "repairs.jsonl"
    _write_jsonl(
        repairs,
        [
            {
                "expected_record_digest": before_digest,
                "new_risk_tier": after["risk_tier"],
                "new_suspicious_spans": after["suspicious_spans"],
                "new_xai_explanation": after["xai_explanation"],
                "notes": "Explicit repair for the risk and explanation inconsistency.",
            }
        ],
    )
    rejudge_manifest = tmp_path / "rejudge-manifest.json"
    rejudge_manifest.write_text("{}\n", encoding="utf-8")
    rejudge_results = tmp_path / "rejudge-results.jsonl"
    _write_jsonl(
        rejudge_results,
        [_fresh_result(FinalJudgeTarget.from_record("train", 0, after))],
    )
    final_manifest = tmp_path / "final-manifest.json"
    final_manifest.write_text("{}\n", encoding="utf-8")

    convergence_path = tmp_path / "convergence.json"
    convergence = {
        "schema_version": "phase39-semantic-convergence-v1",
        "initial_candidate_manifest": _artifact(initial_manifest),
        "initial_candidate_files": [_artifact(before_split, records=1)],
        "initial_carry": _artifact(carry, records=0),
        "initial_targets": _artifact(targets, records=1),
        "initial_batch_manifest": _artifact(initial_batch_manifest),
        "iterations": [
            {
                "iteration": 0,
                "candidate_before": [_artifact(before_split, records=1)],
                "semantic_targets": _artifact(semantic_targets, records=1),
                "repair_decisions": _artifact(repairs, records=1),
                "candidate_after": [_artifact(after_split, records=1)],
                "rejudge_iteration": 1,
                "rejudge_batch_manifest": _artifact(rejudge_manifest),
                "rejudge_results": _artifact(rejudge_results, records=1),
                "repairs": [
                    {
                        "record_identity": f"{before['seed_id']}:{hashlib.sha256(before['text'].encode('utf-8')).hexdigest()}",
                        "before_digest": before_digest,
                        "after_digest": after_digest,
                    }
                ],
                "resolved_identities": [
                    f"{before['seed_id']}:{hashlib.sha256(before['text'].encode('utf-8')).hexdigest()}"
                ],
                "unresolved_identities": [],
            }
        ],
        "unresolved_identities": [],
        "unresolved_count": 0,
        "final_candidate_manifest": _artifact(final_manifest),
        "final_candidate_files": [_artifact(after_split, records=1)],
        "final_fresh_results": _artifact(rejudge_results, records=1),
    }
    convergence_path.write_text(json.dumps(convergence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    report = validate_semantic_convergence(convergence_path, require_zero_unresolved=True)
    assert report["unresolved_count"] == 0
    assert report["repair_count"] == 1

    convergence["iterations"][0]["rejudge_iteration"] = 0
    convergence_path.write_text(json.dumps(convergence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="later iteration"):
        validate_semantic_convergence(convergence_path, require_zero_unresolved=True)


def test_convergence_validator_rejects_nonzero_unresolved_and_hash_drift(tmp_path):
    artifact = tmp_path / "artifact.jsonl"
    artifact.write_text("{}\n", encoding="utf-8")
    ref = _artifact(artifact, records=1)
    convergence_path = tmp_path / "convergence.json"
    payload = {
        "schema_version": "phase39-semantic-convergence-v1",
        "initial_candidate_manifest": ref,
        "initial_candidate_files": [ref],
        "initial_carry": ref,
        "initial_targets": ref,
        "initial_batch_manifest": ref,
        "iterations": [],
        "unresolved_identities": ["seed:identity"],
        "unresolved_count": 1,
        "final_candidate_manifest": ref,
        "final_candidate_files": [ref],
        "final_fresh_results": ref,
    }
    convergence_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="unresolved_count is 1"):
        validate_semantic_convergence(convergence_path, require_zero_unresolved=True)

    payload["unresolved_identities"] = []
    payload["unresolved_count"] = 0
    convergence_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    artifact.write_text("{\"tampered\":true}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        validate_semantic_convergence(convergence_path, require_zero_unresolved=True)


def test_semantic_quarantine_transition_replays_removal_cap_and_group_split(tmp_path):
    source_rows = [
        _make_source_row(
            f"seed_quarantine_{index:02d}",
            f"Tin nhan Zalo thu {index:02d} du dai de kiem thu quarantine semantic.",
            label="zalo_social_engineering",
        )
        for index in range(14)
    ]
    source_splits = {"train": source_rows, "val": [], "test": []}
    quarantined = source_rows[0]
    remaining = source_rows[1:]
    assignments = assign_stratified_group_split(
        remaining,
        ratios=(0.8, 0.1, 0.1),
        salt="phase39-mislabel-triage-v1",
    )
    final_splits = {"train": [], "val": [], "test": []}
    for record in remaining:
        final_splits[assignments[record["seed_id"]]].append(record)

    before_dir = tmp_path / "before"
    after_dir = tmp_path / "after"
    before_dir.mkdir()
    after_dir.mkdir()
    for name in ("train", "val", "test"):
        _write_jsonl(before_dir / f"{name}.jsonl", source_splits[name])
        _write_jsonl(after_dir / f"{name}.jsonl", final_splits[name])

    digest = dataset_record_digest(quarantined)
    identity = record_identity(quarantined["seed_id"], quarantined["text"])
    quarantine_path = tmp_path / "quarantine.jsonl"
    quarantine_row = {
        "source_split": "train",
        "source_row_index": 0,
        "record_digest": digest,
        "record_identity": identity,
        "reason": "fresh_judge_unrepairable_label",
        "record": quarantined,
        "fresh_judge": {
            "split": "train",
            "row_index": 0,
            "seed_id": quarantined["seed_id"],
            "realism": 4,
            "label_correctness": 2,
            "code_switch_naturalness": 4,
            "risk_tier_correctness": 4,
            "suspicious_span_accuracy": 4,
            "pass": False,
            "reason": "The text is ordinary and does not contain a social-engineering cue.",
            "record_digest": digest,
        },
    }
    _write_jsonl(quarantine_path, [quarantine_row])
    cap_path = tmp_path / "cap-drops.jsonl"
    cap_path.write_text("", encoding="utf-8")

    transition = SemanticQuarantineTransition(
        schema_version="phase39-semantic-quarantine-v1",
        reason="fresh_judge_unrepairable_label",
        candidate_before=[
            ConvergenceArtifact(path=str(before_dir / f"{name}.jsonl"), sha256=sha256_path(before_dir / f"{name}.jsonl"), records=len(source_splits[name]))
            for name in ("train", "val", "test")
        ],
        quarantine_records=ConvergenceArtifact(
            path=str(quarantine_path), sha256=sha256_path(quarantine_path), records=1
        ),
        cap_drop_records=ConvergenceArtifact(
            path=str(cap_path), sha256=sha256_path(cap_path), records=0
        ),
        candidate_after=[
            ConvergenceArtifact(path=str(after_dir / f"{name}.jsonl"), sha256=sha256_path(after_dir / f"{name}.jsonl"), records=len(final_splits[name]))
            for name in ("train", "val", "test")
        ],
        cap_pct=0.08,
        split_ratios=(0.8, 0.1, 0.1),
        split_salt="phase39-mislabel-triage-v1",
        resolved_identities=[identity],
    )
    resolved, removed = _validate_semantic_quarantine_transition(
        transition,
        expected_before=source_splits,
        final_splits=final_splits,
    )
    assert resolved == {identity}
    assert removed == {digest}

    quarantine_row["fresh_judge"]["label_correctness"] = 3
    quarantine_row["fresh_judge"]["pass"] = True
    _write_jsonl(quarantine_path, [quarantine_row])
    with pytest.raises(ValueError, match="lacks a bound failing label verdict"):
        _validate_semantic_quarantine_transition(
            transition,
            expected_before=source_splits,
            final_splits=final_splits,
        )


def test_real_final_release_composition_is_exact_2097_snapshot():
    repo_root = Path(__file__).resolve().parents[2]
    combined, provenance = compose_final_judge_evidence(
        candidate_dir=repo_root / "data/processed/phase39-mislabel-candidate",
        convergence_path=repo_root / "data/processed/phase39-semantic-convergence.json",
        carry_path=repo_root / "data/processed/phase39-final-evidence/carry.jsonl",
        fresh_results_path=repo_root / "data/processed/codex-final-delta-judge.jsonl",
    )
    origins = {
        origin: sum(row.verdict_origin == origin for row in provenance)
        for origin in ("carried_forward_exact_record", "fresh_final_delta")
    }
    assert len(combined) == len(provenance) == 2_097
    assert origins == {
        "carried_forward_exact_record": 1_561,
        "fresh_final_delta": 536,
    }
    source = load_source_splits(
        repo_root / "data/processed/phase39-mislabel-candidate/splits"
    )
    merged, _ = merge_judge_results(combined, source)
    stats = compute_aggregate_stats(merged)
    assert stats["passed"] == 1_395
    assert stats["pass_mismatch_count"] == 0
    assert stats["per_split"]["train"]["passed"] == 1_130
    assert stats["per_split"]["val"]["passed"] == 110
    assert stats["per_split"]["test"]["passed"] == 155


def test_final_provenance_origin_contract_is_closed():
    with pytest.raises(ValueError, match="fresh provenance requires a source iteration"):
        FinalJudgeProvenanceRow(
            schema_version="phase39-final-judge-provenance-v1",
            split="train",
            row_index=0,
            seed_id="seed_test",
            record_digest="0" * 64,
            evidence_digest="1" * 64,
            verdict_origin="fresh_final_delta",
            source_iteration=None,
            source_path="data/processed/fresh.jsonl",
            source_sha256="2" * 64,
        )


def test_carried_evidence_is_bound_to_byte_preserved_historical_merge(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    backup = (
        repo_root
        / "data/backup/pre-phase39-mislabel-triage/processed/judge-merged.jsonl"
    )
    if not backup.is_file():
        backup = repo_root / "data/processed/judge-merged.jsonl"
    carry_source = repo_root / "data/processed/phase39-final-evidence/carry.jsonl"
    report = validate_carries_against_historical_backup(
        carry_path=carry_source,
        historical_merged_backup=backup,
    )
    assert report["carry_count"] == 1_561
    rows = [json.loads(line) for line in carry_source.read_text(encoding="utf-8").splitlines()]
    rows[0]["result"]["reason"] = "Tampered but internally rehashed carried verdict."
    rows[0]["provenance"]["evidence_digest"] = judge_evidence_digest(rows[0]["result"])
    tampered = tmp_path / "carry.jsonl"
    _write_jsonl(tampered, rows)
    with pytest.raises(ValueError, match="evidence differs"):
        validate_carries_against_historical_backup(
            carry_path=tampered,
            historical_merged_backup=backup,
        )
