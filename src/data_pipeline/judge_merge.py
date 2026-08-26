"""Merge and validate Codex's independent judge-output file against the real
source split files, computing descriptive quality stats (Phase 39).

Codex judges ``data/splits/{train,val,test}.jsonl`` independently, following
``.planning/codex-judge-instructions.md``, and writes one JSON line per row
to ``data/processed/codex-judge-pass.jsonl``. This module joins that output
back to the source rows via ``split`` + ``row_index`` (cross-checked against
``seed_id``), and computes aggregate pass-rate / per-dimension-average
statistics -- never trusting Codex's self-reported ``pass`` blindly (see
``compute_aggregate_stats``'s ``pass_mismatch_count``).

The legacy merge entry point remains available, while the Phase 39 commands
also validate semantic convergence, compose exact carry/fresh evidence, and
promote the final corpus and judge bundle through a rollback-capable release.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Literal, Mapping, Sequence

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from src.data_pipeline.schemas import DatasetRecord

_SPLIT_NAMES = ("train", "val", "test")
_SCORE_DIMENSIONS = (
    "realism",
    "label_correctness",
    "code_switch_naturalness",
    "risk_tier_correctness",
    "suspicious_span_accuracy",
)
_DATASET_FIELDS = (
    "text",
    "label",
    "risk_tier",
    "suspicious_spans",
    "xai_explanation",
    "source",
    "seed_id",
)
_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_FINAL_BATCH_SCHEMA_VERSION = "phase39-final-judge-batches-v1"
_CONVERGENCE_SCHEMA_VERSION = "phase39-semantic-convergence-v1"
_DEFAULT_CARRY_COUNT = 1_562
_DEFAULT_DELTA_COUNT = 541
_DEFAULT_FINAL_COUNT = 2_103
_COORDINATE_SPLIT_ORDER = {name: index for index, name in enumerate(_SPLIT_NAMES)}
_FINAL_RELEASE_SCHEMA_VERSION = "phase39-final-release-v1"
_FINAL_PROVENANCE_SCHEMA_VERSION = "phase39-final-judge-provenance-v1"
_DOWNSTREAM_CONTRACT_SCHEMA_VERSION = "phase39-downstream-data-contract-v1"
_LIVE_SPLIT_INTEGRITY_ENV = "VNPHISH_ENABLE_LIVE_SPLIT_INTEGRITY_AUDIT"
_LIVE_SPLIT_INTEGRITY_TOKEN = "I_UNDERSTAND_THIS_READS_LIVE_SPLITS"
_HISTORICAL_JUDGE_SHA256 = {
    "codex-judge-pass.jsonl": "00f8b4116a6d9cd48317eb7bc7921d44d41c641d1fe9c49aeb8af8fc8e84b142",
    "judge-merged.jsonl": "e8b4d947271717e56556a74136c57d83dd58589c78699d557999140a9fb55750",
    "judge-summary.json": "b6880a32af17694c4dd8f26528fd2e1d60b9a819f8329be73b3b34704a5eea49",
}
_HISTORICAL_JUDGE_ROWS = 2_421


class CodexJudgeResult(BaseModel):
    """One judge-scored row, matching
    .planning/codex-judge-instructions.md's output schema exactly."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    split: Literal["train", "val", "test"]
    row_index: int = Field(ge=0)
    seed_id: str = Field(min_length=1)
    realism: int = Field(ge=1, le=5)
    label_correctness: int = Field(ge=1, le=5)
    code_switch_naturalness: int = Field(ge=1, le=5)
    risk_tier_correctness: int = Field(ge=1, le=5)
    suspicious_span_accuracy: int = Field(ge=1, le=5)
    judge_pass: bool = Field(alias="pass")
    reason: str = Field(min_length=1)


class FinalJudgeTarget(BaseModel):
    """One exact current-snapshot record awaiting a fresh judgment."""

    model_config = ConfigDict(extra="forbid")

    split: Literal["train", "val", "test"]
    row_index: int = Field(ge=0)
    record_digest: str = Field(pattern=_SHA256_PATTERN)
    text: str = Field(min_length=10)
    label: Literal[
        "bank_impersonation", "zalo_social_engineering", "task_scam", "benign"
    ]
    risk_tier: Literal["benign", "suspicious", "high-risk"]
    suspicious_spans: list[str]
    xai_explanation: str = Field(min_length=20)
    source: Literal[
        "ncsc_seed",
        "synthetic_claude",
        "synthetic_gemini",
        "synthetic_openrouter",
        "synthetic_deepseek",
        "synthetic_openai_compatible",
    ]
    seed_id: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_bound_digest(self) -> "FinalJudgeTarget":
        if self.record_digest != dataset_record_digest(self.dataset_record()):
            raise ValueError("record_digest does not match the seven DatasetRecord fields")
        return self

    def dataset_record(self) -> dict[str, Any]:
        return {field: getattr(self, field) for field in _DATASET_FIELDS}

    @classmethod
    def from_record(
        cls,
        split: Literal["train", "val", "test"],
        row_index: int,
        record: Mapping[str, Any] | DatasetRecord,
    ) -> "FinalJudgeTarget":
        payload = _validated_dataset_payload(record)
        return cls(
            split=split,
            row_index=row_index,
            record_digest=dataset_record_digest(payload),
            **payload,
        )


class FinalJudgeResult(CodexJudgeResult):
    """A fresh verdict bound to the exact seven-field target digest."""

    record_digest: str = Field(pattern=_SHA256_PATTERN)

    @model_validator(mode="after")
    def validate_computed_pass(self) -> "FinalJudgeResult":
        expected = all(getattr(self, dimension) >= 3 for dimension in _SCORE_DIMENSIONS)
        if self.judge_pass != expected:
            raise ValueError(
                "pass must equal whether all five judge scores are at least 3"
            )
        return self


class CarryProvenance(BaseModel):
    """Why a historical verdict is safe to reuse for one final coordinate."""

    model_config = ConfigDict(extra="forbid")

    verdict_origin: Literal["carried_forward_exact_record"]
    record_digest: str = Field(pattern=_SHA256_PATTERN)
    evidence_digest: str = Field(pattern=_SHA256_PATTERN)
    historical_split: Literal["train", "val", "test"]
    historical_row_index: int = Field(ge=0)
    candidate_manifest_sha256: str = Field(pattern=_SHA256_PATTERN)
    candidate_split_sha256: str = Field(pattern=_SHA256_PATTERN)
    historical_merged_sha256: str = Field(pattern=_SHA256_PATTERN)


class CarriedJudgeRow(BaseModel):
    """Original judge-result shape plus an explicit immutable provenance sidecar."""

    model_config = ConfigDict(extra="forbid")

    result: CodexJudgeResult
    provenance: CarryProvenance

    @model_validator(mode="after")
    def validate_evidence_binding(self) -> "CarriedJudgeRow":
        if self.result.seed_id == "":  # covered by Field; keeps invariant explicit
            raise ValueError("carried result seed_id is empty")
        if judge_evidence_digest(self.result) != self.provenance.evidence_digest:
            raise ValueError("carried evidence_digest does not match result evidence")
        return self


class FinalJudgeProvenanceRow(BaseModel):
    """One final-coordinate verdict origin, independent of the merged payload."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["phase39-final-judge-provenance-v1"]
    split: Literal["train", "val", "test"]
    row_index: int = Field(ge=0)
    seed_id: str = Field(min_length=1)
    record_digest: str = Field(pattern=_SHA256_PATTERN)
    evidence_digest: str = Field(pattern=_SHA256_PATTERN)
    verdict_origin: Literal["carried_forward_exact_record", "fresh_final_delta"]
    source_iteration: int | None = Field(default=None, ge=0)
    source_path: str = Field(min_length=1)
    source_sha256: str = Field(pattern=_SHA256_PATTERN)
    historical_split: Literal["train", "val", "test"] | None = None
    historical_row_index: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_origin_fields(self) -> "FinalJudgeProvenanceRow":
        if self.verdict_origin == "carried_forward_exact_record":
            if self.source_iteration is not None:
                raise ValueError("carried provenance cannot declare a fresh iteration")
            if self.historical_split is None or self.historical_row_index is None:
                raise ValueError("carried provenance requires historical coordinates")
        else:
            if self.source_iteration is None:
                raise ValueError("fresh provenance requires a source iteration")
            if self.historical_split is not None or self.historical_row_index is not None:
                raise ValueError("fresh provenance cannot declare historical coordinates")
        return self


class FinalCoordinate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    split: Literal["train", "val", "test"]
    row_index: int = Field(ge=0)
    seed_id: str = Field(min_length=1)
    record_digest: str = Field(pattern=_SHA256_PATTERN)


class BatchManifestEntry(BaseModel):
    """One restartable target/result pair."""

    model_config = ConfigDict(extra="forbid")

    batch_id: str = Field(pattern=r"^batch-[0-9]{4}$")
    target_path: str = Field(min_length=1)
    result_path: str = Field(min_length=1)
    target_count: int = Field(gt=0)
    target_sha256: str = Field(pattern=_SHA256_PATTERN)
    first_coordinate: FinalCoordinate
    last_coordinate: FinalCoordinate
    status: Literal["pending", "complete"]
    result_count: int | None = Field(default=None, ge=0)
    result_sha256: str | None = Field(default=None, pattern=_SHA256_PATTERN)

    @model_validator(mode="after")
    def validate_status_fields(self) -> "BatchManifestEntry":
        if self.status == "pending" and (
            self.result_count is not None or self.result_sha256 is not None
        ):
            raise ValueError("pending batch must not declare result count/hash")
        if self.status == "complete" and (
            self.result_count is None or self.result_sha256 is None
        ):
            raise ValueError("complete batch must declare result count/hash")
        return self


class FinalJudgeBatchManifest(BaseModel):
    """Versioned manifest for one deterministic judge iteration."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["phase39-final-judge-batches-v1"]
    iteration: int = Field(ge=0)
    candidate_dir: str = Field(min_length=1)
    candidate_manifest_path: str = Field(min_length=1)
    candidate_manifest_sha256: str = Field(pattern=_SHA256_PATTERN)
    historical_merged_path: str | None = None
    historical_merged_sha256: str = Field(pattern=_SHA256_PATTERN)
    carry_path: str = Field(min_length=1)
    carry_sha256: str = Field(pattern=_SHA256_PATTERN)
    carry_count: int = Field(ge=0)
    aggregate_targets_path: str = Field(min_length=1)
    aggregate_targets_sha256: str = Field(pattern=_SHA256_PATTERN)
    aggregate_target_count: int = Field(ge=0)
    batch_size: int = Field(gt=0)
    batches: list[BatchManifestEntry] = Field(min_length=1)
    preparation_origin: Literal["local_deterministic_preparation"]
    judgments_prefilled: Literal[False]
    external_api_call_count: Literal[0]

    @model_validator(mode="after")
    def validate_batch_sequence(self) -> "FinalJudgeBatchManifest":
        expected_ids = [f"batch-{index:04d}" for index in range(1, len(self.batches) + 1)]
        actual_ids = [entry.batch_id for entry in self.batches]
        if actual_ids != expected_ids:
            raise ValueError(
                f"batch IDs must be contiguous and ordered: expected {expected_ids}, got {actual_ids}"
            )
        if sum(entry.target_count for entry in self.batches) != self.aggregate_target_count:
            raise ValueError("batch target counts do not sum to aggregate_target_count")
        return self


class ConvergenceArtifact(BaseModel):
    """A path whose content is re-opened and re-hashed by convergence validation."""

    model_config = ConfigDict(extra="forbid")

    path: str = Field(min_length=1)
    sha256: str = Field(pattern=_SHA256_PATTERN)
    records: int | None = Field(default=None, ge=0)


class RepairDigestEdge(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_identity: str = Field(min_length=1)
    before_digest: str = Field(pattern=_SHA256_PATTERN)
    after_digest: str = Field(pattern=_SHA256_PATTERN)

    @model_validator(mode="after")
    def validate_changed_digest(self) -> "RepairDigestEdge":
        if self.before_digest == self.after_digest:
            raise ValueError("repair before_digest and after_digest must differ")
        return self


class SemanticConvergenceIteration(BaseModel):
    model_config = ConfigDict(extra="forbid")

    iteration: int = Field(ge=0)
    candidate_before: list[ConvergenceArtifact] = Field(min_length=1)
    semantic_targets: ConvergenceArtifact
    repair_decisions: ConvergenceArtifact
    candidate_after: list[ConvergenceArtifact] = Field(min_length=1)
    rejudge_iteration: int = Field(ge=0)
    rejudge_batch_manifest: ConvergenceArtifact
    rejudge_results: ConvergenceArtifact
    repairs: list[RepairDigestEdge]
    resolved_identities: list[str]
    unresolved_identities: list[str]


class CandidateLabelCounts(BaseModel):
    """Closed four-label count vector used by the final convergence profile."""

    model_config = ConfigDict(extra="forbid")

    bank_impersonation: int = Field(ge=0)
    task_scam: int = Field(ge=0)
    benign: int = Field(ge=0)
    zalo_social_engineering: int = Field(ge=0)


class CandidateSplitCounts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    train: int = Field(ge=0)
    val: int = Field(ge=0)
    test: int = Field(ge=0)


class CandidateSplitLabelCounts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    train: CandidateLabelCounts
    val: CandidateLabelCounts
    test: CandidateLabelCounts


class CandidateExpectedProfile(BaseModel):
    """Explicit final profile; avoids assuming the pre-quarantine 2,103 rows."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["phase39-candidate-profile-v1"]
    total_rows: int = Field(gt=0)
    split_counts: CandidateSplitCounts
    split_class_distribution: CandidateSplitLabelCounts
    total_class_distribution: CandidateLabelCounts
    unique_zalo_seeds: int = Field(gt=0)
    max_zalo_seed_count: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_internal_totals(self) -> "CandidateExpectedProfile":
        split_counts = self.split_counts.model_dump()
        if sum(split_counts.values()) != self.total_rows:
            raise ValueError("expected profile split counts do not sum to total_rows")
        total_labels = self.total_class_distribution.model_dump()
        if sum(total_labels.values()) != self.total_rows:
            raise ValueError("expected profile label counts do not sum to total_rows")
        for split_name, label_counts in self.split_class_distribution.model_dump().items():
            if sum(label_counts.values()) != split_counts[split_name]:
                raise ValueError(
                    f"expected profile {split_name} label counts do not sum to split count"
                )
        return self


class SemanticQuarantineTransition(BaseModel):
    """Hash-bound post-judge removal and deterministic cap/re-split transition."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["phase39-semantic-quarantine-v1"]
    reason: Literal["fresh_judge_unrepairable_label"]
    candidate_before: list[ConvergenceArtifact] = Field(min_length=1)
    quarantine_records: ConvergenceArtifact
    cap_drop_records: ConvergenceArtifact
    candidate_after: list[ConvergenceArtifact] = Field(min_length=1)
    cap_pct: Literal[0.08]
    split_ratios: tuple[Literal[0.8], Literal[0.1], Literal[0.1]]
    split_salt: Literal["phase39-mislabel-triage-v1"]
    resolved_identities: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_resolved_identities(self) -> "SemanticQuarantineTransition":
        if len(set(self.resolved_identities)) != len(self.resolved_identities):
            raise ValueError("semantic quarantine resolved_identities contains duplicates")
        return self


class SemanticConvergence(BaseModel):
    """Closed evidence ledger; fields are assertions only until revalidated."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["phase39-semantic-convergence-v1"]
    initial_candidate_manifest: ConvergenceArtifact
    initial_candidate_files: list[ConvergenceArtifact] = Field(min_length=1)
    initial_carry: ConvergenceArtifact
    initial_targets: ConvergenceArtifact
    initial_batch_manifest: ConvergenceArtifact
    iterations: list[SemanticConvergenceIteration]
    unresolved_identities: list[str]
    unresolved_count: int = Field(ge=0)
    final_candidate_manifest: ConvergenceArtifact
    final_candidate_files: list[ConvergenceArtifact] = Field(min_length=1)
    final_carry: ConvergenceArtifact | None = None
    final_fresh_results: ConvergenceArtifact
    final_expected_profile: CandidateExpectedProfile | None = None
    semantic_quarantine: SemanticQuarantineTransition | None = None

    @model_validator(mode="after")
    def validate_summary_shape(self) -> "SemanticConvergence":
        if self.unresolved_count != len(self.unresolved_identities):
            raise ValueError("unresolved_count does not equal unresolved_identities length")
        if len(set(self.unresolved_identities)) != len(self.unresolved_identities):
            raise ValueError("unresolved_identities contains duplicates")
        iteration_numbers = [item.iteration for item in self.iterations]
        if iteration_numbers != list(range(len(iteration_numbers))):
            raise ValueError("semantic iterations must be ordered contiguously from zero")
        if self.semantic_quarantine is not None:
            if self.final_expected_profile is None:
                raise ValueError("semantic quarantine requires final_expected_profile")
            if self.final_carry is None:
                raise ValueError("semantic quarantine requires final_carry")
        return self


def _validated_dataset_payload(
    record: Mapping[str, Any] | DatasetRecord,
) -> dict[str, Any]:
    if isinstance(record, DatasetRecord):
        payload = record.model_dump(mode="json")
    else:
        raw = dict(record)
        missing = sorted(set(_DATASET_FIELDS) - set(raw))
        if missing:
            raise ValueError(f"record is missing DatasetRecord field(s): {missing}")
        payload = {field: raw[field] for field in _DATASET_FIELDS}
        payload = DatasetRecord.model_validate(payload).model_dump(mode="json")
    invalid_spans = [
        span
        for span in payload["suspicious_spans"]
        if not span or span not in payload["text"]
    ]
    if invalid_spans:
        raise ValueError(f"record has non-literal suspicious span(s): {invalid_spans[:10]}")
    return payload


def _canonical_json_bytes(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(
        dict(payload), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def dataset_record_digest(record: Mapping[str, Any] | DatasetRecord) -> str:
    """Hash the Pydantic-normalized values of all seven DatasetRecord fields."""
    payload = _validated_dataset_payload(record)
    return hashlib.sha256(_canonical_json_bytes(payload)).hexdigest()


def _judge_evidence_payload(
    evidence: Mapping[str, Any] | CodexJudgeResult,
) -> dict[str, Any]:
    if isinstance(evidence, CodexJudgeResult):
        return {
            **{dimension: getattr(evidence, dimension) for dimension in _SCORE_DIMENSIONS},
            "pass": evidence.judge_pass,
            "reason": evidence.reason,
        }
    raw = dict(evidence)
    payload: dict[str, Any] = {}
    for dimension in _SCORE_DIMENSIONS:
        if dimension not in raw:
            raise ValueError(f"judge evidence is missing {dimension}")
        score = raw[dimension]
        if not isinstance(score, int) or isinstance(score, bool) or not 1 <= score <= 5:
            raise ValueError(f"judge evidence {dimension} must be an integer from 1 to 5")
        payload[dimension] = score
    if "pass" in raw:
        payload["pass"] = raw["pass"]
    elif "judge_pass" in raw:
        payload["pass"] = raw["judge_pass"]
    else:
        raise ValueError("judge evidence is missing pass/judge_pass")
    if not isinstance(payload["pass"], bool):
        raise ValueError("judge evidence pass must be boolean")
    if "reason" in raw:
        payload["reason"] = raw["reason"]
    elif "judge_reason" in raw:
        payload["reason"] = raw["judge_reason"]
    else:
        raise ValueError("judge evidence is missing reason/judge_reason")
    if not isinstance(payload["reason"], str) or not payload["reason"].strip():
        raise ValueError("judge evidence reason must be non-empty")
    return payload


def judge_evidence_digest(
    evidence: Mapping[str, Any] | CodexJudgeResult,
) -> str:
    """Hash only the five scores, declared pass, and reason."""
    return hashlib.sha256(_canonical_json_bytes(_judge_evidence_payload(evidence))).hexdigest()


def sha256_path(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _coordinate_key(value: FinalJudgeTarget | FinalCoordinate | CodexJudgeResult) -> tuple[int, int]:
    return (_COORDINATE_SPLIT_ORDER[value.split], value.row_index)


def _coordinate_from_target(target: FinalJudgeTarget) -> FinalCoordinate:
    return FinalCoordinate(
        split=target.split,
        row_index=target.row_index,
        seed_id=target.seed_id,
        record_digest=target.record_digest,
    )


def _final_identity(
    split: str, row_index: int, seed_id: str, record_digest: str
) -> tuple[str, int, str, str]:
    return (split, row_index, seed_id, record_digest)


def _historical_result(row: Mapping[str, Any]) -> CodexJudgeResult:
    raw = dict(row)
    try:
        return CodexJudgeResult.model_validate(
            {
                "split": raw["split"],
                "row_index": raw["row_index"],
                "seed_id": raw["seed_id"],
                **{dimension: raw[dimension] for dimension in _SCORE_DIMENSIONS},
                "pass": raw["judge_pass"],
                "reason": raw["judge_reason"],
            }
        )
    except (KeyError, ValidationError) as exc:
        raise ValueError(f"historical merged row has invalid judge evidence: {exc}") from exc


def build_final_judge_partition(
    candidate_splits: Mapping[str, Sequence[Mapping[str, Any]]],
    historical_merged_rows: Sequence[Mapping[str, Any]],
    *,
    candidate_manifest_sha256: str,
    candidate_split_sha256: Mapping[str, str],
    historical_merged_sha256: str,
) -> tuple[list[CarriedJudgeRow], list[FinalJudgeTarget]]:
    """Partition current rows into unique exact carries and fresh targets.

    Historical coordinates are parsed only as provenance.  The final coordinate
    comes exclusively from the candidate split traversal.
    """
    for name, digest in {
        "candidate manifest": candidate_manifest_sha256,
        "historical merged": historical_merged_sha256,
        **{f"candidate {name}": value for name, value in candidate_split_sha256.items()},
    }.items():
        if not isinstance(digest, str) or len(digest) != 64:
            raise ValueError(f"{name} SHA-256 must contain 64 lowercase hex characters")
        try:
            int(digest, 16)
        except ValueError as exc:
            raise ValueError(f"{name} SHA-256 is not hexadecimal") from exc

    missing_splits = sorted(set(_SPLIT_NAMES) - set(candidate_splits))
    if missing_splits:
        raise ValueError(f"candidate is missing split(s): {missing_splits}")
    missing_hashes = sorted(set(_SPLIT_NAMES) - set(candidate_split_sha256))
    if missing_hashes:
        raise ValueError(f"candidate split hashes are missing split(s): {missing_hashes}")

    historical_by_digest: dict[str, list[tuple[dict[str, Any], CodexJudgeResult]]] = (
        defaultdict(list)
    )
    for index, row in enumerate(historical_merged_rows):
        try:
            record = _validated_dataset_payload(row)
            digest = dataset_record_digest(record)
            result = _historical_result(row)
        except Exception as exc:
            raise ValueError(f"historical merged row {index} is invalid: {exc}") from exc
        if result.seed_id != record["seed_id"]:
            raise ValueError(f"historical merged row {index} has a seed_id mismatch")
        historical_by_digest[digest].append((record, result))

    carries: list[CarriedJudgeRow] = []
    targets: list[FinalJudgeTarget] = []
    final_digests: set[str] = set()
    final_identities: set[tuple[str, int, str, str]] = set()
    for split_name in _SPLIT_NAMES:
        rows = candidate_splits[split_name]
        for row_index, raw_record in enumerate(rows):
            record = _validated_dataset_payload(raw_record)
            digest = dataset_record_digest(record)
            identity = _final_identity(split_name, row_index, record["seed_id"], digest)
            if identity in final_identities:
                raise ValueError(f"candidate final identity repeats: {identity}")
            if digest in final_digests:
                raise ValueError(
                    "candidate contains a duplicate exact seven-field record digest: "
                    f"{digest}"
                )
            final_identities.add(identity)
            final_digests.add(digest)

            matches = historical_by_digest.get(digest, [])
            if len(matches) != 1:
                targets.append(
                    FinalJudgeTarget.from_record(split_name, row_index, record)  # type: ignore[arg-type]
                )
                continue

            historical_record, historical_result = matches[0]
            if historical_record != record:
                # A digest collision is not a carry authorization.
                targets.append(
                    FinalJudgeTarget.from_record(split_name, row_index, record)  # type: ignore[arg-type]
                )
                continue
            rebased = CodexJudgeResult(
                split=split_name,  # type: ignore[arg-type]
                row_index=row_index,
                seed_id=record["seed_id"],
                **{
                    dimension: getattr(historical_result, dimension)
                    for dimension in _SCORE_DIMENSIONS
                },
                **{
                    "pass": historical_result.judge_pass,
                    "reason": historical_result.reason,
                },
            )
            carries.append(
                CarriedJudgeRow(
                    result=rebased,
                    provenance=CarryProvenance(
                        verdict_origin="carried_forward_exact_record",
                        record_digest=digest,
                        evidence_digest=judge_evidence_digest(rebased),
                        historical_split=historical_result.split,
                        historical_row_index=historical_result.row_index,
                        candidate_manifest_sha256=candidate_manifest_sha256,
                        candidate_split_sha256=candidate_split_sha256[split_name],
                        historical_merged_sha256=historical_merged_sha256,
                    ),
                )
            )

    carry_identities = {
        _final_identity(
            row.result.split,
            row.result.row_index,
            row.result.seed_id,
            row.provenance.record_digest,
        )
        for row in carries
    }
    target_identities = {
        _final_identity(
            row.split, row.row_index, row.seed_id, row.record_digest
        )
        for row in targets
    }
    overlap = carry_identities & target_identities
    if overlap:
        raise ValueError(f"carry and delta overlap: {sorted(overlap)[:10]}")
    covered = carry_identities | target_identities
    if covered != final_identities:
        missing = sorted(final_identities - covered)
        extra = sorted(covered - final_identities)
        raise ValueError(
            f"carry/delta coverage differs from candidate (missing={missing[:10]}, extra={extra[:10]})"
        )
    return carries, targets


def _jsonl_bytes(rows: Iterable[BaseModel | Mapping[str, Any]]) -> bytes:
    encoded: list[str] = []
    for row in rows:
        payload = (
            row.model_dump(mode="json", by_alias=True)
            if isinstance(row, BaseModel)
            else dict(row)
        )
        encoded.append(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    return (("\n".join(encoded) + "\n") if encoded else "").encode("utf-8")


def _read_jsonl_objects(path: Path, *, context: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                raise ValueError(f"{context} line {line_number} is blank")
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"{context} line {line_number} is not valid JSON: {exc}"
                ) from exc
            if not isinstance(value, dict):
                raise ValueError(f"{context} line {line_number} is not a JSON object")
            rows.append(value)
    return rows


def _load_final_targets(path: Path) -> list[FinalJudgeTarget]:
    targets: list[FinalJudgeTarget] = []
    for line_number, row in enumerate(
        _read_jsonl_objects(path, context="final judge targets"), start=1
    ):
        try:
            targets.append(FinalJudgeTarget.model_validate(row))
        except ValidationError as exc:
            raise ValueError(
                f"final judge targets line {line_number} failed schema validation: {exc}"
            ) from exc
    return targets


def _load_carried_rows(path: Path) -> list[CarriedJudgeRow]:
    rows: list[CarriedJudgeRow] = []
    for line_number, row in enumerate(
        _read_jsonl_objects(path, context="carried judge evidence"), start=1
    ):
        try:
            rows.append(CarriedJudgeRow.model_validate(row))
        except ValidationError as exc:
            raise ValueError(
                f"carried judge evidence line {line_number} failed schema validation: {exc}"
            ) from exc
    return rows


def _load_final_results(path: Path) -> list[FinalJudgeResult]:
    rows: list[FinalJudgeResult] = []
    for line_number, row in enumerate(
        _read_jsonl_objects(path, context="fresh judge results"), start=1
    ):
        try:
            rows.append(FinalJudgeResult.model_validate(row))
        except ValidationError as exc:
            raise ValueError(
                f"fresh judge results line {line_number} failed schema validation: {exc}"
            ) from exc
    return rows


def _manifest_path_string(path: Path) -> str:
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return resolved.as_posix()


def _resolve_declared_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else Path.cwd() / path


def _write_bytes_atomically(path: Path, payload: bytes) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _write_or_verify_exact(path: Path, payload: bytes) -> bool:
    """Write only an absent file; an exact existing file is an idempotent reuse."""
    path = Path(path)
    if path.exists():
        if not path.is_file() or path.read_bytes() != payload:
            raise ValueError(f"refusing to overwrite conflicting existing artifact {path}")
        return True
    _write_bytes_atomically(path, payload)
    if path.read_bytes() != payload:
        raise ValueError(f"artifact failed byte-for-byte reload verification: {path}")
    return False


def materialize_batch_bundle(
    *,
    targets: Sequence[FinalJudgeTarget],
    carries: Sequence[CarriedJudgeRow],
    aggregate_targets_path: Path,
    carry_path: Path,
    batch_dir: Path,
    candidate_dir: Path,
    candidate_manifest_sha256: str,
    historical_merged_sha256: str,
    batch_size: int = 64,
    iteration: int = 0,
    historical_merged_path: Path | None = None,
) -> Path:
    """Materialize a deterministic pending queue without fabricating results.

    Existing exact preparation files are reused.  Any conflicting byte or any
    pre-existing pending result file stops the operation rather than silently
    replacing evidence.
    """
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")
    validated_targets = [FinalJudgeTarget.model_validate(item) for item in targets]
    validated_carries = [CarriedJudgeRow.model_validate(item) for item in carries]
    validated_targets.sort(key=_coordinate_key)
    identities = [
        _final_identity(item.split, item.row_index, item.seed_id, item.record_digest)
        for item in validated_targets
    ]
    duplicates = [identity for identity, count in Counter(identities).items() if count > 1]
    if duplicates:
        raise ValueError(f"fresh target identities repeat: {duplicates[:10]}")
    if not validated_targets:
        raise ValueError("at least one fresh target is required")

    aggregate_targets_path = Path(aggregate_targets_path)
    carry_path = Path(carry_path)
    batch_dir = Path(batch_dir)
    manifest_path = batch_dir / "manifest.json"
    target_payload = _jsonl_bytes(validated_targets)
    carry_payload = _jsonl_bytes(validated_carries)

    entries: list[BatchManifestEntry] = []
    batch_payloads: dict[Path, bytes] = {}
    for offset in range(0, len(validated_targets), batch_size):
        sequence = offset // batch_size + 1
        batch_id = f"batch-{sequence:04d}"
        batch_targets = validated_targets[offset : offset + batch_size]
        batch_target_path = batch_dir / f"{batch_id}-targets.jsonl"
        batch_result_path = batch_dir / f"{batch_id}-results.jsonl"
        if batch_result_path.exists():
            raise ValueError(
                f"pending preparation refuses pre-existing result path {batch_result_path}"
            )
        payload = _jsonl_bytes(batch_targets)
        batch_payloads[batch_target_path] = payload
        entries.append(
            BatchManifestEntry(
                batch_id=batch_id,
                target_path=_manifest_path_string(batch_target_path),
                result_path=_manifest_path_string(batch_result_path),
                target_count=len(batch_targets),
                target_sha256=hashlib.sha256(payload).hexdigest(),
                first_coordinate=_coordinate_from_target(batch_targets[0]),
                last_coordinate=_coordinate_from_target(batch_targets[-1]),
                status="pending",
                result_count=None,
                result_sha256=None,
            )
        )

    manifest = FinalJudgeBatchManifest(
        schema_version=_FINAL_BATCH_SCHEMA_VERSION,
        iteration=iteration,
        candidate_dir=_manifest_path_string(candidate_dir),
        candidate_manifest_path=_manifest_path_string(Path(candidate_dir) / "manifest.json"),
        candidate_manifest_sha256=candidate_manifest_sha256,
        historical_merged_path=(
            _manifest_path_string(historical_merged_path)
            if historical_merged_path is not None
            else None
        ),
        historical_merged_sha256=historical_merged_sha256,
        carry_path=_manifest_path_string(carry_path),
        carry_sha256=hashlib.sha256(carry_payload).hexdigest(),
        carry_count=len(validated_carries),
        aggregate_targets_path=_manifest_path_string(aggregate_targets_path),
        aggregate_targets_sha256=hashlib.sha256(target_payload).hexdigest(),
        aggregate_target_count=len(validated_targets),
        batch_size=batch_size,
        batches=entries,
        preparation_origin="local_deterministic_preparation",
        judgments_prefilled=False,
        external_api_call_count=0,
    )
    manifest_payload = (
        json.dumps(
            manifest.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    ).encode("utf-8")

    payloads: dict[Path, bytes] = {
        carry_path: carry_payload,
        aggregate_targets_path: target_payload,
        **batch_payloads,
        manifest_path: manifest_payload,
    }
    # Preflight every path before the first write so a conflict cannot leave a
    # newly-created subset beside older incompatible evidence.
    for path, payload in payloads.items():
        if path.exists() and (not path.is_file() or path.read_bytes() != payload):
            raise ValueError(f"refusing to overwrite conflicting existing artifact {path}")
    for path, payload in payloads.items():
        _write_or_verify_exact(path, payload)

    validate_batch_bundle(
        manifest_path,
        targets_path=aggregate_targets_path,
        carry_path=carry_path,
        require_status="pending",
    )
    return manifest_path


def _fresh_result_identity(result: FinalJudgeResult) -> tuple[str, int, str, str]:
    return _final_identity(
        result.split, result.row_index, result.seed_id, result.record_digest
    )


def _target_identity(target: FinalJudgeTarget) -> tuple[str, int, str, str]:
    return _final_identity(
        target.split, target.row_index, target.seed_id, target.record_digest
    )


def _validate_results_for_targets(
    targets: Sequence[FinalJudgeTarget],
    results: Sequence[FinalJudgeResult],
    *,
    context: str,
) -> None:
    target_identities = [_target_identity(item) for item in targets]
    result_identities = [_fresh_result_identity(item) for item in results]
    duplicate_results = [
        identity for identity, count in Counter(result_identities).items() if count > 1
    ]
    missing = sorted(set(target_identities) - set(result_identities))
    unexpected = sorted(set(result_identities) - set(target_identities))
    if (
        len(results) != len(targets)
        or duplicate_results
        or missing
        or unexpected
        or result_identities != target_identities
    ):
        raise ValueError(
            f"{context} result coverage differs from target order "
            f"(expected={len(targets)}, actual={len(results)}, "
            f"duplicates={duplicate_results[:10]}, missing={missing[:10]}, "
            f"unexpected={unexpected[:10]})"
        )


def _load_batch_manifest(path: Path) -> FinalJudgeBatchManifest:
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"batch manifest {path} is unreadable: {exc}") from exc
    try:
        return FinalJudgeBatchManifest.model_validate(raw)
    except ValidationError as exc:
        raise ValueError(f"batch manifest {path} failed schema validation: {exc}") from exc


def _candidate_final_identities(candidate_dir: Path) -> set[tuple[str, int, str, str]]:
    source = load_source_splits(Path(candidate_dir) / "splits")
    identities: set[tuple[str, int, str, str]] = set()
    for split_name in _SPLIT_NAMES:
        for row_index, record in enumerate(source[split_name]):
            digest = dataset_record_digest(record)
            identity = _final_identity(split_name, row_index, record["seed_id"], digest)
            if identity in identities:
                raise ValueError(f"candidate final identity repeats: {identity}")
            identities.add(identity)
    return identities


def validate_batch_bundle(
    batch_manifest_path: Path,
    *,
    candidate_dir: Path | None = None,
    targets_path: Path | None = None,
    carry_path: Path | None = None,
    combined_results_path: Path | None = None,
    require_status: Literal["pending", "complete"] | None = None,
    historical_merged_path_override: Path | None = None,
    _allow_pending_result_files: bool = False,
) -> dict[str, Any]:
    """Recompute every queue hash and all carry/delta coverage relations."""
    batch_manifest_path = Path(batch_manifest_path)
    manifest = _load_batch_manifest(batch_manifest_path)
    declared_targets_path = _resolve_declared_path(manifest.aggregate_targets_path)
    declared_carry_path = _resolve_declared_path(manifest.carry_path)
    if targets_path is not None and Path(targets_path).resolve() != declared_targets_path.resolve():
        raise ValueError("provided aggregate targets path differs from batch manifest")
    if carry_path is not None and Path(carry_path).resolve() != declared_carry_path.resolve():
        raise ValueError("provided carry path differs from batch manifest")
    targets_path = declared_targets_path
    carry_path = declared_carry_path

    if sha256_path(targets_path) != manifest.aggregate_targets_sha256:
        raise ValueError("aggregate targets SHA-256 mismatch")
    if sha256_path(carry_path) != manifest.carry_sha256:
        raise ValueError("carry SHA-256 mismatch")
    targets = _load_final_targets(targets_path)
    carries = _load_carried_rows(carry_path)
    if len(targets) != manifest.aggregate_target_count:
        raise ValueError("aggregate target count differs from batch manifest")
    if len(carries) != manifest.carry_count:
        raise ValueError("carry count differs from batch manifest")
    if [_coordinate_key(item) for item in targets] != sorted(
        [_coordinate_key(item) for item in targets]
    ):
        raise ValueError("aggregate targets are not in final-coordinate order")

    target_identities = {_target_identity(item) for item in targets}
    carry_identities = {
        _final_identity(
            item.result.split,
            item.result.row_index,
            item.result.seed_id,
            item.provenance.record_digest,
        )
        for item in carries
    }
    if len(target_identities) != len(targets):
        raise ValueError("aggregate targets contain duplicate final identities")
    if len(carry_identities) != len(carries):
        raise ValueError("carry artifact contains duplicate final identities")
    overlap = target_identities & carry_identities
    if overlap:
        raise ValueError(f"carry and target identities overlap: {sorted(overlap)[:10]}")

    if candidate_dir is not None:
        candidate_dir = Path(candidate_dir)
        candidate_manifest_path = candidate_dir / "manifest.json"
        if sha256_path(candidate_manifest_path) != manifest.candidate_manifest_sha256:
            raise ValueError("candidate manifest SHA-256 mismatch")
        # Plan 39-02's reload validation is deliberately reused when this is
        # the real candidate.  Import locally to keep legacy judge merge light.
        from src.data_pipeline.apply_mislabel_triage import validate_staged_candidate

        validate_staged_candidate(candidate_dir)
        final_identities = _candidate_final_identities(candidate_dir)
        covered = carry_identities | target_identities
        if covered != final_identities:
            missing = sorted(final_identities - covered)
            extra = sorted(covered - final_identities)
            raise ValueError(
                "carry/delta coverage is not exhaustive over candidate "
                f"(missing={missing[:10]}, extra={extra[:10]})"
            )

    if manifest.historical_merged_path is not None:
        historical_path = (
            Path(historical_merged_path_override)
            if historical_merged_path_override is not None
            else _resolve_declared_path(manifest.historical_merged_path)
        )
        if sha256_path(historical_path) != manifest.historical_merged_sha256:
            raise ValueError("historical merged SHA-256 mismatch")

    concatenated_target_bytes = bytearray()
    batch_counts: list[int] = []
    concatenated_result_bytes = bytearray()
    completed_results: list[FinalJudgeResult] = []
    for entry in manifest.batches:
        if require_status is not None and entry.status != require_status:
            raise ValueError(
                f"batch {entry.batch_id} status is {entry.status}, required {require_status}"
            )
        batch_target_path = _resolve_declared_path(entry.target_path)
        if sha256_path(batch_target_path) != entry.target_sha256:
            raise ValueError(f"batch {entry.batch_id} target SHA-256 mismatch")
        batch_targets = _load_final_targets(batch_target_path)
        if len(batch_targets) != entry.target_count:
            raise ValueError(f"batch {entry.batch_id} target count mismatch")
        if _coordinate_from_target(batch_targets[0]) != entry.first_coordinate:
            raise ValueError(f"batch {entry.batch_id} first coordinate mismatch")
        if _coordinate_from_target(batch_targets[-1]) != entry.last_coordinate:
            raise ValueError(f"batch {entry.batch_id} last coordinate mismatch")
        concatenated_target_bytes.extend(batch_target_path.read_bytes())
        batch_counts.append(len(batch_targets))

        result_path = _resolve_declared_path(entry.result_path)
        if entry.status == "pending":
            if result_path.exists() and not _allow_pending_result_files:
                raise ValueError(
                    f"pending batch {entry.batch_id} has an unvalidated result file"
                )
            continue
        if not result_path.is_file():
            raise ValueError(f"completed batch {entry.batch_id} result file is missing")
        actual_result_hash = sha256_path(result_path)
        if actual_result_hash != entry.result_sha256:
            raise ValueError(
                f"completed batch {entry.batch_id} result SHA-256 mismatch"
            )
        batch_results = _load_final_results(result_path)
        if len(batch_results) != entry.result_count:
            raise ValueError(f"completed batch {entry.batch_id} result count mismatch")
        _validate_results_for_targets(
            batch_targets, batch_results, context=f"batch {entry.batch_id}"
        )
        concatenated_result_bytes.extend(result_path.read_bytes())
        completed_results.extend(batch_results)

    if bytes(concatenated_target_bytes) != Path(targets_path).read_bytes():
        raise ValueError("batch target concatenation differs from aggregate targets")

    if combined_results_path is not None:
        if any(entry.status != "complete" for entry in manifest.batches):
            raise ValueError("combined results require every batch to be complete")
        combined_results_path = Path(combined_results_path)
        if combined_results_path.read_bytes() != bytes(concatenated_result_bytes):
            raise ValueError("combined results are not the exact ordered batch concatenation")
        combined_results = _load_final_results(combined_results_path)
        _validate_results_for_targets(targets, combined_results, context="combined results")

    return {
        "schema_version": manifest.schema_version,
        "iteration": manifest.iteration,
        "carry_count": len(carries),
        "target_count": len(targets),
        "covered_count": len(carries) + len(targets),
        "batch_counts": batch_counts,
        "batch_statuses": [entry.status for entry in manifest.batches],
        "batch_manifest_sha256": sha256_path(batch_manifest_path),
        "aggregate_targets_sha256": manifest.aggregate_targets_sha256,
        "carry_sha256": manifest.carry_sha256,
    }


def complete_batch(batch_manifest_path: Path, batch_id: str) -> dict[str, Any]:
    """Validate one result file and atomically mark only that batch complete."""
    batch_manifest_path = Path(batch_manifest_path)
    manifest = _load_batch_manifest(batch_manifest_path)
    matches = [entry for entry in manifest.batches if entry.batch_id == batch_id]
    if len(matches) != 1:
        raise ValueError(f"batch manifest has no unique entry for {batch_id}")
    entry = matches[0]
    target_path = _resolve_declared_path(entry.target_path)
    result_path = _resolve_declared_path(entry.result_path)
    if sha256_path(target_path) != entry.target_sha256:
        raise ValueError(f"batch {batch_id} target SHA-256 mismatch")
    targets = _load_final_targets(target_path)
    if not result_path.is_file():
        raise ValueError(f"batch {batch_id} result file is missing")
    results = _load_final_results(result_path)
    _validate_results_for_targets(targets, results, context=f"batch {batch_id}")
    result_hash = sha256_path(result_path)

    if entry.status == "complete":
        if result_hash != entry.result_sha256:
            raise ValueError(f"completed batch {batch_id} result SHA-256 mismatch")
        if len(results) != entry.result_count:
            raise ValueError(f"completed batch {batch_id} result count mismatch")
        return {"batch_id": batch_id, "status": "complete", "reused": True}

    original_manifest_bytes = batch_manifest_path.read_bytes()
    # Check the rest of the declared bundle before changing its state.  A
    # partial file for another pending batch is allowed to remain pending.
    validate_batch_bundle(
        batch_manifest_path,
        _allow_pending_result_files=True,
    )
    raw = json.loads(original_manifest_bytes.decode("utf-8"))
    raw_entries = [item for item in raw["batches"] if item["batch_id"] == batch_id]
    if len(raw_entries) != 1:
        raise ValueError(f"raw batch manifest has no unique entry for {batch_id}")
    raw_entry = raw_entries[0]
    raw_entry["status"] = "complete"
    raw_entry["result_count"] = len(results)
    raw_entry["result_sha256"] = result_hash
    updated = FinalJudgeBatchManifest.model_validate(raw)
    payload = (
        json.dumps(updated.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n"
    ).encode("utf-8")
    _write_bytes_atomically(batch_manifest_path, payload)
    try:
        # Validate the mixed restart state while allowing untouched pending
        # batches to retain an interrupted partial file.
        validate_batch_bundle(
            batch_manifest_path,
            _allow_pending_result_files=True,
        )
    except Exception:
        _write_bytes_atomically(batch_manifest_path, original_manifest_bytes)
        raise
    return {"batch_id": batch_id, "status": "complete", "reused": False}


def _validate_convergence_artifact(artifact: ConvergenceArtifact) -> Path:
    path = _resolve_declared_path(artifact.path)
    if not path.is_file():
        raise ValueError(f"convergence artifact is missing: {path}")
    actual_hash = sha256_path(path)
    if actual_hash != artifact.sha256:
        raise ValueError(
            f"convergence artifact SHA-256 mismatch for {path}: "
            f"expected {artifact.sha256}, got {actual_hash}"
        )
    if artifact.records is not None:
        try:
            rows = _read_jsonl_objects(path, context=f"convergence artifact {path}")
        except ValueError:
            raise
        if len(rows) != artifact.records:
            raise ValueError(
                f"convergence artifact record count mismatch for {path}: "
                f"expected {artifact.records}, got {len(rows)}"
            )
    return path


def _load_dataset_artifacts(
    artifacts: Sequence[ConvergenceArtifact], *, context: str
) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    records: list[dict[str, Any]] = []
    by_digest: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for artifact in artifacts:
        path = _resolve_declared_path(artifact.path)
        for row_index, raw in enumerate(
            _read_jsonl_objects(path, context=f"{context} {path}"), start=0
        ):
            try:
                record = _validated_dataset_payload(raw)
            except Exception as exc:
                raise ValueError(f"{context} {path} row {row_index} is invalid: {exc}") from exc
            records.append(record)
            by_digest[dataset_record_digest(record)].append(record)
    return records, by_digest


def _all_convergence_artifacts(model: SemanticConvergence) -> list[ConvergenceArtifact]:
    artifacts = [
        model.initial_candidate_manifest,
        *model.initial_candidate_files,
        model.initial_carry,
        model.initial_targets,
        model.initial_batch_manifest,
        model.final_candidate_manifest,
        *model.final_candidate_files,
        *([model.final_carry] if model.final_carry is not None else []),
        model.final_fresh_results,
    ]
    for iteration in model.iterations:
        artifacts.extend(
            [
                *iteration.candidate_before,
                iteration.semantic_targets,
                iteration.repair_decisions,
                *iteration.candidate_after,
                iteration.rejudge_batch_manifest,
                iteration.rejudge_results,
            ]
        )
    if model.semantic_quarantine is not None:
        artifacts.extend(
            [
                *model.semantic_quarantine.candidate_before,
                model.semantic_quarantine.quarantine_records,
                model.semantic_quarantine.cap_drop_records,
                *model.semantic_quarantine.candidate_after,
            ]
        )
    return artifacts


def _maybe_validate_declared_batch_manifest(
    path: Path, *, historical_merged_path_override: Path | None = None
) -> None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    if isinstance(payload, dict) and payload.get("schema_version") == _FINAL_BATCH_SCHEMA_VERSION:
        validate_batch_bundle(
            path,
            require_status="complete",
            historical_merged_path_override=historical_merged_path_override,
        )


def _load_named_candidate_artifacts(
    artifacts: Sequence[ConvergenceArtifact], *, context: str
) -> dict[str, list[dict[str, Any]]]:
    """Load train/val/test snapshot artifacts without trusting declaration order."""
    splits: dict[str, list[dict[str, Any]]] = {}
    for artifact in artifacts:
        path = _resolve_declared_path(artifact.path)
        split_name = path.stem
        if split_name not in _SPLIT_NAMES:
            raise ValueError(f"{context} artifact does not name a split: {path}")
        if split_name in splits:
            raise ValueError(f"{context} repeats split artifact {split_name}")
        raw_rows = _read_jsonl_objects(path, context=f"{context} {split_name}")
        splits[split_name] = [
            _validated_dataset_payload(row) for row in raw_rows
        ]
    if set(splits) != set(_SPLIT_NAMES):
        raise ValueError(f"{context} does not contain exact train/val/test artifacts")
    return splits


def _candidate_profile_from_splits(
    splits: Mapping[str, Sequence[Mapping[str, Any]]],
) -> dict[str, Any]:
    labels = (
        "bank_impersonation",
        "task_scam",
        "benign",
        "zalo_social_engineering",
    )
    split_counts = {name: len(splits[name]) for name in _SPLIT_NAMES}
    split_class_distribution: dict[str, dict[str, int]] = {}
    total_class_counts: Counter[str] = Counter()
    zalo_seed_counts: Counter[str] = Counter()
    for name in _SPLIT_NAMES:
        counts = Counter(row["label"] for row in splits[name])
        split_class_distribution[name] = {
            label: counts.get(label, 0) for label in labels
        }
        total_class_counts.update(counts)
        zalo_seed_counts.update(
            row["seed_id"]
            for row in splits[name]
            if row["label"] == "zalo_social_engineering"
        )
    return {
        "schema_version": "phase39-candidate-profile-v1",
        "total_rows": sum(split_counts.values()),
        "split_counts": split_counts,
        "split_class_distribution": split_class_distribution,
        "total_class_distribution": {
            label: total_class_counts.get(label, 0) for label in labels
        },
        "unique_zalo_seeds": len(zalo_seed_counts),
        "max_zalo_seed_count": max(zalo_seed_counts.values(), default=0),
    }


def _validate_semantic_quarantine_transition(
    transition: SemanticQuarantineTransition,
    *,
    expected_before: Mapping[str, Sequence[Mapping[str, Any]]],
    final_splits: Mapping[str, Sequence[Mapping[str, Any]]],
) -> tuple[set[str], set[str]]:
    """Recompute exact quarantine, iterative cap, and whole-seed split output."""
    from src.data_pipeline.apply_mislabel_triage import record_identity
    from src.data_pipeline.repair_corpus_split_governance import (
        assign_stratified_group_split,
        enforce_seed_cap,
    )

    before_splits = _load_named_candidate_artifacts(
        transition.candidate_before, context="semantic quarantine candidate-before"
    )
    after_splits = _load_named_candidate_artifacts(
        transition.candidate_after, context="semantic quarantine candidate-after"
    )
    for name in _SPLIT_NAMES:
        if before_splits[name] != list(expected_before[name]):
            raise ValueError(
                f"semantic quarantine candidate-before differs from prior semantic state in {name}"
            )
        if after_splits[name] != list(final_splits[name]):
            raise ValueError(
                f"semantic quarantine candidate-after differs from final candidate in {name}"
            )

    before_by_digest: dict[str, tuple[str, int, dict[str, Any]]] = {}
    before_flat: list[dict[str, Any]] = []
    for split_name in _SPLIT_NAMES:
        for row_index, record in enumerate(before_splits[split_name]):
            digest = dataset_record_digest(record)
            if digest in before_by_digest:
                raise ValueError("semantic quarantine candidate-before repeats a record digest")
            before_by_digest[digest] = (split_name, row_index, record)
            before_flat.append(record)

    quarantine_path = _resolve_declared_path(transition.quarantine_records.path)
    quarantine_rows = _read_jsonl_objects(
        quarantine_path, context="semantic quarantine records"
    )
    expected_quarantine_keys = {
        "source_split",
        "source_row_index",
        "record_digest",
        "record_identity",
        "reason",
        "record",
        "fresh_judge",
    }
    quarantine_digests: list[str] = []
    quarantine_identities: list[str] = []
    for index, row in enumerate(quarantine_rows):
        if set(row) != expected_quarantine_keys:
            raise ValueError(f"semantic quarantine row {index} has a non-closed schema")
        if row["reason"] != transition.reason:
            raise ValueError(f"semantic quarantine row {index} reason mismatch")
        record = _validated_dataset_payload(row["record"])
        digest = dataset_record_digest(record)
        if row["record_digest"] != digest:
            raise ValueError(f"semantic quarantine row {index} digest mismatch")
        identity = record_identity(record["seed_id"], record["text"])
        if row["record_identity"] != identity:
            raise ValueError(f"semantic quarantine row {index} identity mismatch")
        source = before_by_digest.get(digest)
        if source is None or source != (
            row["source_split"],
            row["source_row_index"],
            record,
        ):
            raise ValueError(f"semantic quarantine row {index} source binding mismatch")
        try:
            fresh = FinalJudgeResult.model_validate(row["fresh_judge"])
        except ValidationError as exc:
            raise ValueError(
                f"semantic quarantine row {index} fresh judge evidence is invalid: {exc}"
            ) from exc
        if (
            fresh.record_digest != digest
            or fresh.split != row["source_split"]
            or fresh.row_index != row["source_row_index"]
            or fresh.seed_id != record["seed_id"]
            or fresh.label_correctness >= 3
        ):
            raise ValueError(
                f"semantic quarantine row {index} lacks a bound failing label verdict"
            )
        quarantine_digests.append(digest)
        quarantine_identities.append(identity)
    if len(quarantine_digests) != len(set(quarantine_digests)):
        raise ValueError("semantic quarantine repeats a record digest")
    if set(quarantine_identities) != set(transition.resolved_identities):
        raise ValueError("semantic quarantine resolved identities differ from quarantined rows")

    quarantine_set = set(quarantine_digests)
    remaining = [
        record
        for record in before_flat
        if dataset_record_digest(record) not in quarantine_set
    ]
    if len(remaining) != len(before_flat) - len(quarantine_set):
        raise ValueError("semantic quarantine removal cardinality is not exact")
    capped, _ = enforce_seed_cap(remaining, cap_pct=transition.cap_pct)
    capped_counts = Counter(dataset_record_digest(record) for record in capped)
    deterministic_drops: list[dict[str, Any]] = []
    for record in remaining:
        digest = dataset_record_digest(record)
        if capped_counts[digest]:
            capped_counts[digest] -= 1
        else:
            deterministic_drops.append(record)
    if any(capped_counts.values()):
        raise ValueError("semantic quarantine cap output contains unknown records")

    cap_path = _resolve_declared_path(transition.cap_drop_records.path)
    cap_rows = _read_jsonl_objects(cap_path, context="semantic quarantine cap drops")
    expected_cap_keys = {
        "record_digest",
        "record_identity",
        "seed_id",
        "reason",
        "record",
    }
    if len(cap_rows) != len(deterministic_drops):
        raise ValueError("semantic quarantine cap-drop count is not deterministic")
    for index, (row, expected_record) in enumerate(zip(cap_rows, deterministic_drops, strict=True)):
        if set(row) != expected_cap_keys:
            raise ValueError(f"semantic quarantine cap row {index} has a non-closed schema")
        if row["reason"] != "global_iterative_seed_cap_after_semantic_quarantine":
            raise ValueError(f"semantic quarantine cap row {index} reason mismatch")
        record = _validated_dataset_payload(row["record"])
        digest = dataset_record_digest(record)
        identity = record_identity(record["seed_id"], record["text"])
        if (
            record != expected_record
            or row["record_digest"] != digest
            or row["record_identity"] != identity
            or row["seed_id"] != record["seed_id"]
        ):
            raise ValueError(f"semantic quarantine cap row {index} binding mismatch")

    assignments = assign_stratified_group_split(
        capped,
        ratios=transition.split_ratios,
        salt=transition.split_salt,
    )
    recomputed = {name: [] for name in _SPLIT_NAMES}
    for record in capped:
        recomputed[assignments[record["seed_id"]]].append(record)
    for name in _SPLIT_NAMES:
        if recomputed[name] != after_splits[name]:
            raise ValueError(
                f"semantic quarantine deterministic cap/re-split differs in {name}"
            )
    removed_digests = set(quarantine_digests) | {
        dataset_record_digest(record) for record in deterministic_drops
    }
    return set(quarantine_identities), removed_digests


def validate_semantic_convergence(
    convergence_path: Path,
    *,
    candidate_dir: Path | None = None,
    carry_path: Path | None = None,
    fresh_results_path: Path | None = None,
    require_zero_unresolved: bool = False,
    historical_merged_path_override: Path | None = None,
) -> dict[str, Any]:
    """Re-open and recompute a semantic-convergence ledger.

    The JSON document is never accepted as a self-declared completion flag:
    every artifact hash/count, candidate transition, restricted repair, and
    later fresh-verdict edge is independently checked.
    """
    convergence_path = Path(convergence_path)
    try:
        raw = json.loads(convergence_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"semantic convergence file is unreadable: {exc}") from exc
    try:
        convergence = SemanticConvergence.model_validate(raw)
    except ValidationError as exc:
        raise ValueError(f"semantic convergence schema validation failed: {exc}") from exc

    if require_zero_unresolved and convergence.unresolved_count != 0:
        raise ValueError(
            f"semantic convergence unresolved_count is {convergence.unresolved_count}, required 0"
        )

    # Validate each distinct path/hash/count declaration.  Repeated references
    # are allowed only when they make the same assertion.
    declarations: dict[str, tuple[str, int | None]] = {}
    validated_paths: list[Path] = []
    for artifact in _all_convergence_artifacts(convergence):
        normalized = str(_resolve_declared_path(artifact.path).resolve())
        declaration = (artifact.sha256, artifact.records)
        previous = declarations.get(normalized)
        if previous is not None and previous != declaration:
            raise ValueError(
                f"convergence artifact {normalized} has conflicting hash/count declarations"
            )
        declarations[normalized] = declaration
        validated_paths.append(_validate_convergence_artifact(artifact))

    _maybe_validate_declared_batch_manifest(
        _resolve_declared_path(convergence.initial_batch_manifest.path),
        historical_merged_path_override=historical_merged_path_override,
    )
    for iteration in convergence.iterations:
        _maybe_validate_declared_batch_manifest(
            _resolve_declared_path(iteration.rejudge_batch_manifest.path)
        )

    _, initial_by_digest = _load_dataset_artifacts(
        convergence.initial_candidate_files, context="initial candidate"
    )
    _, final_by_digest = _load_dataset_artifacts(
        convergence.final_candidate_files, context="final candidate"
    )
    repair_count = 0
    all_edges: list[tuple[int, int, RepairDigestEdge]] = []
    result_digests_by_iteration: dict[int, set[str]] = defaultdict(set)

    from src.data_pipeline.apply_mislabel_triage import (
        apply_semantic_repairs,
        load_semantic_repair_decisions,
        record_identity,
    )

    for iteration in convergence.iterations:
        if iteration.rejudge_iteration <= iteration.iteration:
            raise ValueError(
                f"semantic iteration {iteration.iteration} must use a later iteration "
                "for every repaired digest fresh verdict"
            )
        _, before_by_digest = _load_dataset_artifacts(
            iteration.candidate_before,
            context=f"semantic iteration {iteration.iteration} candidate-before",
        )
        _, after_by_digest = _load_dataset_artifacts(
            iteration.candidate_after,
            context=f"semantic iteration {iteration.iteration} candidate-after",
        )
        decisions = load_semantic_repair_decisions(
            _resolve_declared_path(iteration.repair_decisions.path)
        )
        decision_by_digest = {item.expected_record_digest: item for item in decisions}
        semantic_target_rows = _load_final_targets(
            _resolve_declared_path(iteration.semantic_targets.path)
        )
        semantic_target_digests = [row.record_digest for row in semantic_target_rows]
        if len(semantic_target_digests) != len(set(semantic_target_digests)):
            raise ValueError(
                f"semantic iteration {iteration.iteration} repeats a target digest"
            )
        if set(semantic_target_digests) != set(decision_by_digest):
            raise ValueError(
                f"semantic iteration {iteration.iteration} decision coverage differs "
                "from semantic targets"
            )
        target_identities = {
            record_identity(row.seed_id, row.text) for row in semantic_target_rows
        }
        rejudge_results = _load_final_results(
            _resolve_declared_path(iteration.rejudge_results.path)
        )
        result_digests = {item.record_digest for item in rejudge_results}
        if len(result_digests) != len(rejudge_results):
            raise ValueError(
                f"semantic iteration {iteration.iteration} rejudge results repeat a digest"
            )
        result_digests_by_iteration[iteration.rejudge_iteration].update(result_digests)

        edge_identities = [edge.record_identity for edge in iteration.repairs]
        if len(edge_identities) != len(set(edge_identities)):
            raise ValueError(
                f"semantic iteration {iteration.iteration} repeats a repair identity"
            )
        resolved = set(iteration.resolved_identities)
        unresolved = set(iteration.unresolved_identities)
        if resolved | unresolved != target_identities:
            raise ValueError(
                f"semantic iteration {iteration.iteration} resolved/unresolved identities "
                "do not cover its semantic targets"
            )
        if resolved & unresolved:
            raise ValueError(
                f"semantic iteration {iteration.iteration} identity is both resolved and unresolved"
            )
        if not set(edge_identities) <= resolved:
            raise ValueError(
                f"semantic iteration {iteration.iteration} repair edge is not resolved"
            )

        edge_by_before = {edge.before_digest: edge for edge in iteration.repairs}
        for target in semantic_target_rows:
            decision = decision_by_digest[target.record_digest]
            before_matches = before_by_digest.get(target.record_digest, [])
            if len(before_matches) != 1:
                raise ValueError(
                    f"semantic target {target.record_digest} does not uniquely bind candidate-before"
                )
            patched, _ = apply_semantic_repairs([before_matches[0]], [decision])
            patched_digest = dataset_record_digest(patched[0])
            edge = edge_by_before.get(target.record_digest)
            if edge is None and patched_digest != target.record_digest:
                raise ValueError(
                    f"semantic decision {target.record_digest} changed digest without a repair edge"
                )
            if edge is not None and patched_digest != edge.after_digest:
                raise ValueError(
                    f"semantic decision {target.record_digest} does not reproduce its after-digest"
                )

        for edge in iteration.repairs:
            before_matches = before_by_digest.get(edge.before_digest, [])
            after_matches = after_by_digest.get(edge.after_digest, [])
            if len(before_matches) != 1 or len(after_matches) != 1:
                raise ValueError(
                    f"repair edge {edge.record_identity} does not uniquely bind before/after candidates"
                )
            before = before_matches[0]
            after = after_matches[0]
            if record_identity(before["seed_id"], before["text"]) != edge.record_identity:
                raise ValueError(f"repair edge {edge.record_identity} before identity mismatch")
            if record_identity(after["seed_id"], after["text"]) != edge.record_identity:
                raise ValueError(f"repair edge {edge.record_identity} after identity mismatch")
            for field in ("label", "text", "source", "seed_id"):
                if before[field] != after[field]:
                    raise ValueError(
                        f"repair edge {edge.record_identity} changed forbidden field {field}"
                    )
            decision = decision_by_digest.get(edge.before_digest)
            if decision is None:
                raise ValueError(
                    f"repair edge {edge.record_identity} lacks an expected-digest decision"
                )
            patched, _ = apply_semantic_repairs([before], [decision])
            if dataset_record_digest(patched[0]) != edge.after_digest or patched[0] != after:
                raise ValueError(
                    f"repair edge {edge.record_identity} after record does not match decision"
                )
            if edge.after_digest not in result_digests:
                raise ValueError(
                    f"repair edge {edge.record_identity} lacks a fresh verdict for its after-digest"
                )
            repair_count += 1
            all_edges.append((iteration.iteration, iteration.rejudge_iteration, edge))

    if convergence.final_expected_profile is not None:
        final_named_splits = _load_named_candidate_artifacts(
            convergence.final_candidate_files, context="final candidate profile"
        )
        actual_profile = _candidate_profile_from_splits(final_named_splits)
        if actual_profile != convergence.final_expected_profile.model_dump(mode="json"):
            raise ValueError(
                "final candidate profile differs from convergence expected profile"
            )
    else:
        final_named_splits = None

    quarantine_removed_digests: set[str] = set()
    if convergence.semantic_quarantine is not None:
        if final_named_splits is None:  # guarded by the model, kept explicit.
            raise ValueError("semantic quarantine lacks a final expected profile")
        prior_splits = _load_named_candidate_artifacts(
            convergence.initial_candidate_files,
            context="semantic chain initial candidate",
        )
        for iteration in convergence.iterations:
            iteration_before = _load_named_candidate_artifacts(
                iteration.candidate_before,
                context=f"semantic iteration {iteration.iteration} chain before",
            )
            for name in _SPLIT_NAMES:
                if iteration_before[name] != prior_splits[name]:
                    raise ValueError(
                        f"semantic iteration {iteration.iteration} candidate-before "
                        f"does not follow prior state in {name}"
                    )
            prior_splits = _load_named_candidate_artifacts(
                iteration.candidate_after,
                context=f"semantic iteration {iteration.iteration} chain after",
            )
        quarantine_resolved, quarantine_removed_digests = _validate_semantic_quarantine_transition(
            convergence.semantic_quarantine,
            expected_before=prior_splits,
            final_splits=final_named_splits,
        )
        semantic_resolved = {
            identity
            for iteration in convergence.iterations
            for identity in iteration.resolved_identities
        }
        if not quarantine_resolved <= semantic_resolved:
            raise ValueError(
                "semantic quarantine resolves identities absent from semantic target decisions"
            )
        if quarantine_resolved & set(convergence.unresolved_identities):
            raise ValueError(
                "semantic quarantine identity remains declared globally unresolved"
            )

    final_results_path = _resolve_declared_path(convergence.final_fresh_results.path)
    final_results = _load_final_results(final_results_path)
    final_fresh_digests = {item.record_digest for item in final_results}
    for repair_iteration, rejudge_iteration, edge in all_edges:
        if rejudge_iteration <= repair_iteration:
            raise ValueError(
                f"repair edge {edge.record_identity} does not have a later iteration verdict"
            )
        if edge.after_digest not in result_digests_by_iteration[rejudge_iteration]:
            raise ValueError(
                f"repair edge {edge.record_identity} later iteration omits after-digest"
            )
        superseded_by_later_repair = any(
            edge.after_digest == later.before_digest for _, _, later in all_edges
        )
        removed_by_quarantine = edge.after_digest in quarantine_removed_digests
        if (
            not superseded_by_later_repair
            and not removed_by_quarantine
            and edge.after_digest not in final_fresh_digests
        ):
            raise ValueError(
                f"final fresh results omit repaired after-digest {edge.after_digest}"
            )
        if edge.before_digest not in initial_by_digest:
            # Later iterations may repair a digest produced by an earlier edge.
            prior_after = {prior.after_digest for _, _, prior in all_edges}
            if edge.before_digest not in prior_after:
                raise ValueError(
                    f"repair before-digest {edge.before_digest} has no initial/prior lineage"
                )
        if (
            edge.after_digest not in final_by_digest
            and not superseded_by_later_repair
            and not removed_by_quarantine
        ):
            raise ValueError(
                f"repair after-digest {edge.after_digest} has no final/later candidate lineage"
            )

    if candidate_dir is not None:
        actual_final_digests = {
            identity[3] for identity in _candidate_final_identities(Path(candidate_dir))
        }
        declared_final_digests = set(final_by_digest)
        if actual_final_digests != declared_final_digests:
            raise ValueError("final candidate artifact digests differ from candidate-dir")

    if carry_path is not None or fresh_results_path is not None:
        declared_final_carry_path = (
            _resolve_declared_path(convergence.final_carry.path)
            if convergence.final_carry is not None
            else _resolve_declared_path(convergence.initial_carry.path)
        )
        if (
            carry_path is not None
            and Path(carry_path).resolve() != declared_final_carry_path.resolve()
        ):
            raise ValueError("provided final carry path differs from convergence ledger")
        if (
            fresh_results_path is not None
            and Path(fresh_results_path).resolve() != final_results_path.resolve()
        ):
            raise ValueError("provided final fresh path differs from convergence ledger")
        actual_carry_path = (
            Path(carry_path)
            if carry_path is not None
            else declared_final_carry_path
        )
        actual_fresh_path = (
            Path(fresh_results_path)
            if fresh_results_path is not None
            else final_results_path
        )
        carry_rows = _load_carried_rows(actual_carry_path)
        fresh_rows = _load_final_results(actual_fresh_path)
        carry_digests = {row.provenance.record_digest for row in carry_rows}
        fresh_digests = {row.record_digest for row in fresh_rows}
        overlap = carry_digests & fresh_digests
        if overlap:
            raise ValueError(f"final carry/fresh digests overlap: {sorted(overlap)[:10]}")
        current_digests = set(final_by_digest)
        missing = current_digests - (carry_digests | fresh_digests)
        if missing:
            raise ValueError(f"final candidate digests lack judge evidence: {sorted(missing)[:10]}")
        extra = (carry_digests | fresh_digests) - current_digests
        if extra:
            raise ValueError(f"final judge evidence contains removed digests: {sorted(extra)[:10]}")
        carry_identities = {
            _final_identity(
                row.result.split,
                row.result.row_index,
                row.result.seed_id,
                row.provenance.record_digest,
            )
            for row in carry_rows
        }
        fresh_identities = {
            _fresh_result_identity(row) for row in fresh_rows
        }
        final_evidence_splits = _load_named_candidate_artifacts(
            convergence.final_candidate_files,
            context="final judge evidence candidate",
        )
        current_identities = {
            (split_name, row_index, record["seed_id"], dataset_record_digest(record))
            for split_name in _SPLIT_NAMES
            for row_index, record in enumerate(final_evidence_splits[split_name])
        }
        if carry_identities | fresh_identities != current_identities:
            raise ValueError("final carry/fresh coordinate evidence is not exact candidate coverage")
        if len(carry_identities) != len(carry_rows) or len(fresh_identities) != len(fresh_rows):
            raise ValueError("final carry/fresh evidence repeats a final coordinate")
        if candidate_dir is not None:
            candidate_manifest_hash = sha256_path(Path(candidate_dir) / "manifest.json")
            candidate_split_hashes = {
                name: sha256_path(Path(candidate_dir) / "splits" / f"{name}.jsonl")
                for name in _SPLIT_NAMES
            }
            for row in carry_rows:
                if row.provenance.candidate_manifest_sha256 != candidate_manifest_hash:
                    raise ValueError("final carry provenance has a stale candidate manifest hash")
                if (
                    row.provenance.candidate_split_sha256
                    != candidate_split_hashes[row.result.split]
                ):
                    raise ValueError("final carry provenance has a stale candidate split hash")

    return {
        "schema_version": convergence.schema_version,
        "artifact_count": len(declarations),
        "iteration_count": len(convergence.iterations),
        "repair_count": repair_count,
        "unresolved_count": convergence.unresolved_count,
        "final_candidate_records": sum(len(rows) for rows in final_by_digest.values()),
        "final_fresh_result_count": len(final_results),
        "convergence_sha256": sha256_path(convergence_path),
    }


def _load_semantic_convergence_model(path: Path) -> SemanticConvergence:
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        return SemanticConvergence.model_validate(raw)
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        raise ValueError(f"semantic convergence file is invalid: {exc}") from exc


def _base_judge_result(result: CodexJudgeResult) -> CodexJudgeResult:
    return CodexJudgeResult.model_validate(
        result.model_dump(mode="json", by_alias=True, exclude={"record_digest"})
    )


def _fresh_iteration_evidence(
    convergence: SemanticConvergence,
) -> dict[str, tuple[int, str]]:
    """Return the latest fresh iteration/evidence digest for each judged record.

    Coordinates can change after a whole-seed re-split, so this lineage is
    deliberately digest/evidence based rather than coordinate based.
    """
    by_digest: dict[str, tuple[int, str]] = {}
    initial_manifest = _load_batch_manifest(
        _resolve_declared_path(convergence.initial_batch_manifest.path)
    )
    for entry in initial_manifest.batches:
        if entry.status != "complete":
            raise ValueError("initial final-judge batch is not complete")
        for result in _load_final_results(_resolve_declared_path(entry.result_path)):
            evidence = judge_evidence_digest(result)
            previous = by_digest.get(result.record_digest)
            if previous is not None and previous != (0, evidence):
                raise ValueError("initial fresh evidence repeats a digest inconsistently")
            by_digest[result.record_digest] = (0, evidence)
    for iteration in convergence.iterations:
        for result in _load_final_results(
            _resolve_declared_path(iteration.rejudge_results.path)
        ):
            evidence = judge_evidence_digest(result)
            previous = by_digest.get(result.record_digest)
            if previous is not None and previous[1] != evidence:
                raise ValueError(
                    "fresh judgment artifacts conflict for one record digest"
                )
            if previous is None or iteration.rejudge_iteration >= previous[0]:
                by_digest[result.record_digest] = (iteration.rejudge_iteration, evidence)
    return by_digest


def compose_final_judge_evidence(
    *,
    candidate_dir: Path,
    convergence_path: Path,
    carry_path: Path,
    fresh_results_path: Path,
    historical_merged_path_override: Path | None = None,
) -> tuple[list[CodexJudgeResult], list[FinalJudgeProvenanceRow]]:
    """Compose one current-coordinate verdict and provenance row per record."""
    if historical_merged_path_override is None:
        resolved_candidate = Path(candidate_dir).resolve()
        if len(resolved_candidate.parents) >= 3:
            backup_candidate = (
                resolved_candidate.parents[2]
                / "data/backup/pre-phase39-mislabel-triage/processed/judge-merged.jsonl"
            )
            if (
                backup_candidate.is_file()
                and sha256_path(backup_candidate)
                == _HISTORICAL_JUDGE_SHA256["judge-merged.jsonl"]
            ):
                historical_merged_path_override = backup_candidate
    convergence = _load_semantic_convergence_model(convergence_path)
    validate_semantic_convergence(
        convergence_path,
        candidate_dir=candidate_dir,
        carry_path=carry_path,
        fresh_results_path=fresh_results_path,
        require_zero_unresolved=True,
        historical_merged_path_override=historical_merged_path_override,
    )
    candidate_splits = load_source_splits(Path(candidate_dir) / "splits")
    carries = _load_carried_rows(carry_path)
    fresh = _load_final_results(fresh_results_path)
    carry_source_sha = sha256_path(carry_path)
    fresh_source_sha = sha256_path(fresh_results_path)
    if convergence.final_carry is None:
        raise ValueError("final release requires an explicit final_carry artifact")
    if carry_source_sha != convergence.final_carry.sha256:
        raise ValueError("final carry differs from the convergence ledger")
    if fresh_source_sha != convergence.final_fresh_results.sha256:
        raise ValueError("final fresh results differ from the convergence ledger")

    carry_by_identity: dict[tuple[str, int, str, str], CarriedJudgeRow] = {}
    for item in carries:
        identity = _final_identity(
            item.result.split,
            item.result.row_index,
            item.result.seed_id,
            item.provenance.record_digest,
        )
        if identity in carry_by_identity:
            raise ValueError(f"final carry repeats identity {identity}")
        carry_by_identity[identity] = item
    fresh_by_identity: dict[tuple[str, int, str, str], FinalJudgeResult] = {}
    for item in fresh:
        identity = _fresh_result_identity(item)
        if identity in fresh_by_identity:
            raise ValueError(f"final fresh results repeat identity {identity}")
        fresh_by_identity[identity] = item
    if set(carry_by_identity) & set(fresh_by_identity):
        raise ValueError("final carry and fresh evidence overlap")

    iteration_evidence = _fresh_iteration_evidence(convergence)
    combined: list[CodexJudgeResult] = []
    provenance: list[FinalJudgeProvenanceRow] = []
    seen: set[tuple[str, int, str, str]] = set()
    carry_source_path = convergence.final_carry.path
    fresh_source_path = convergence.final_fresh_results.path
    for split_name in _SPLIT_NAMES:
        for row_index, record in enumerate(candidate_splits[split_name]):
            digest = dataset_record_digest(record)
            identity = _final_identity(
                split_name, row_index, record["seed_id"], digest
            )
            if identity in seen:
                raise ValueError(f"final candidate repeats identity {identity}")
            seen.add(identity)
            carried = carry_by_identity.get(identity)
            freshly_judged = fresh_by_identity.get(identity)
            if (carried is None) == (freshly_judged is None):
                raise ValueError(
                    f"final identity must have exactly one evidence origin: {identity}"
                )
            if carried is not None:
                result = _base_judge_result(carried.result)
                combined.append(result)
                provenance.append(
                    FinalJudgeProvenanceRow(
                        schema_version=_FINAL_PROVENANCE_SCHEMA_VERSION,
                        split=split_name,
                        row_index=row_index,
                        seed_id=record["seed_id"],
                        record_digest=digest,
                        evidence_digest=carried.provenance.evidence_digest,
                        verdict_origin="carried_forward_exact_record",
                        source_iteration=None,
                        source_path=carry_source_path,
                        source_sha256=carry_source_sha,
                        historical_split=carried.provenance.historical_split,
                        historical_row_index=carried.provenance.historical_row_index,
                    )
                )
                continue
            assert freshly_judged is not None
            result = _base_judge_result(freshly_judged)
            evidence_digest = judge_evidence_digest(result)
            lineage = iteration_evidence.get(digest)
            if lineage is None or lineage[1] != evidence_digest:
                raise ValueError(
                    f"fresh final digest lacks exact iteration evidence: {digest}"
                )
            combined.append(result)
            provenance.append(
                FinalJudgeProvenanceRow(
                    schema_version=_FINAL_PROVENANCE_SCHEMA_VERSION,
                    split=split_name,
                    row_index=row_index,
                    seed_id=record["seed_id"],
                    record_digest=digest,
                    evidence_digest=evidence_digest,
                    verdict_origin="fresh_final_delta",
                    source_iteration=lineage[0],
                    source_path=fresh_source_path,
                    source_sha256=fresh_source_sha,
                    historical_split=None,
                    historical_row_index=None,
                )
            )
    expected_count = sum(len(rows) for rows in candidate_splits.values())
    if len(combined) != expected_count or len(provenance) != expected_count:
        raise ValueError("final judge composition is not exhaustive")
    return combined, provenance


def ensure_historical_judge_backup(
    *,
    processed_dir: Path,
    backup_dir: Path,
) -> dict[str, dict[str, Any]]:
    """Create or verify the immutable pre-Phase-39 judge bundle backup."""
    from src.data_pipeline.apply_mislabel_triage import replace_payload_bundle

    processed_dir = Path(processed_dir)
    backup_dir = Path(backup_dir)
    source_paths = {
        name: processed_dir / name for name in _HISTORICAL_JUDGE_SHA256
    }
    backup_paths = {name: backup_dir / name for name in _HISTORICAL_JUDGE_SHA256}
    existing = [path for path in backup_paths.values() if path.exists()]
    if existing:
        if len(existing) != len(backup_paths):
            raise ValueError("historical judge backup is partial")
        extra = [
            path
            for path in backup_dir.iterdir()
            if path.is_file() and path.name not in backup_paths
        ]
        if extra:
            raise ValueError(f"historical judge backup has unexpected files: {extra}")
        for name, path in backup_paths.items():
            actual = sha256_path(path)
            if actual != _HISTORICAL_JUDGE_SHA256[name]:
                raise ValueError(
                    f"historical judge backup hash mismatch for {name}: {actual}"
                )
    else:
        for name, path in source_paths.items():
            if not path.is_file():
                raise ValueError(f"historical judge source is missing: {path}")
            actual = sha256_path(path)
            if actual != _HISTORICAL_JUDGE_SHA256[name]:
                raise ValueError(
                    f"historical judge source hash mismatch for {name}: {actual}"
                )
        raw_rows = load_judge_results(source_paths["codex-judge-pass.jsonl"])
        merged_rows = _read_jsonl_objects(
            source_paths["judge-merged.jsonl"], context="historical merged judge"
        )
        if len(raw_rows) != _HISTORICAL_JUDGE_ROWS or len(merged_rows) != _HISTORICAL_JUDGE_ROWS:
            raise ValueError("historical judge source is not the locked 2,421-row bundle")
        payloads = {name: path.read_bytes() for name, path in source_paths.items()}
        destinations = dict(backup_paths)
        originals = {name: None for name in backup_paths}

        def verify_backup() -> None:
            for name, path in backup_paths.items():
                if sha256_path(path) != _HISTORICAL_JUDGE_SHA256[name]:
                    raise ValueError(f"historical backup verification failed for {name}")
                if sha256_path(source_paths[name]) != _HISTORICAL_JUDGE_SHA256[name]:
                    raise ValueError(f"historical source changed during backup for {name}")

        replace_payload_bundle(
            destinations,
            payloads,
            originals,
            operation="Phase 39 historical judge backup",
            verify_written=verify_backup,
        )
    return {
        name: {
            "path": _manifest_path_string(path),
            "sha256": _HISTORICAL_JUDGE_SHA256[name],
            "bytes": path.stat().st_size,
        }
        for name, path in backup_paths.items()
    }


def validate_carries_against_historical_backup(
    *, carry_path: Path, historical_merged_backup: Path
) -> dict[str, Any]:
    """Prove every carried verdict still matches its backed-up source record."""
    backup_path = Path(historical_merged_backup)
    if sha256_path(backup_path) != _HISTORICAL_JUDGE_SHA256["judge-merged.jsonl"]:
        raise ValueError("historical merged backup is not the locked source evidence")
    historical = _read_jsonl_objects(
        backup_path, context="backed-up historical merged judge"
    )
    if len(historical) != _HISTORICAL_JUDGE_ROWS:
        raise ValueError("backed-up historical merged judge row count differs")
    by_coordinate: dict[tuple[str, int], dict[str, Any]] = {}
    for row in historical:
        key = (row.get("split"), row.get("row_index"))
        if key in by_coordinate:
            raise ValueError(f"historical merged judge repeats coordinate {key}")
        by_coordinate[key] = row
    carries = _load_carried_rows(carry_path)
    for item in carries:
        provenance = item.provenance
        if provenance.historical_merged_sha256 != _HISTORICAL_JUDGE_SHA256["judge-merged.jsonl"]:
            raise ValueError("carried row declares the wrong historical merged hash")
        key = (provenance.historical_split, provenance.historical_row_index)
        historical_row = by_coordinate.get(key)
        if historical_row is None:
            raise ValueError(f"carried row has no backed-up historical coordinate {key}")
        historical_record = _validated_dataset_payload(historical_row)
        if dataset_record_digest(historical_record) != provenance.record_digest:
            raise ValueError(f"carried row record digest differs at historical coordinate {key}")
        if historical_record["seed_id"] != item.result.seed_id:
            raise ValueError(f"carried row seed differs at historical coordinate {key}")
        historical_result = _historical_result(historical_row)
        if judge_evidence_digest(historical_result) != provenance.evidence_digest:
            raise ValueError(f"carried row evidence differs at historical coordinate {key}")
        if _judge_evidence_payload(historical_result) != _judge_evidence_payload(item.result):
            raise ValueError(f"carried row verdict changed at historical coordinate {key}")
    return {
        "carry_count": len(carries),
        "historical_rows": len(historical),
        "historical_merged_sha256": sha256_path(backup_path),
    }


def load_judge_results(path: Path) -> list[CodexJudgeResult]:
    """Read and validate every line of a Codex judge-output JSONL file.

    Never skips a bad line silently -- any malformed JSON or schema
    violation is re-raised as a ValueError naming the offending 1-based
    line number.
    """
    results: list[CodexJudgeResult] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                row = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"judge-results line {line_number} is not valid JSON: {exc}"
                ) from exc
            try:
                results.append(CodexJudgeResult.model_validate(row))
            except ValidationError as exc:
                raise ValueError(
                    f"judge-results line {line_number} failed schema validation: {exc}"
                ) from exc
    return results


def load_source_splits(splits_dir: Path) -> dict[str, list[dict[str, Any]]]:
    """Read and validate data/splits/{train,val,test}.jsonl.

    Row order within each file is preserved -- this is what a judge result's
    row_index indexes into.
    """
    splits_dir = Path(splits_dir)
    source_splits: dict[str, list[dict[str, Any]]] = {}
    for split_name in _SPLIT_NAMES:
        rows: list[dict[str, Any]] = []
        split_path = splits_dir / f"{split_name}.jsonl"
        if not split_path.exists():
            raise FileNotFoundError(
                f"{split_path} does not exist. Expected all three of "
                f"{splits_dir}/{{train,val,test}}.jsonl -- if the corpus was "
                "moved or renamed, pass the right --splits-dir."
            )
        with split_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                stripped = line.strip()
                if not stripped:
                    continue
                rows.append(DatasetRecord.model_validate(json.loads(stripped)).model_dump())
        source_splits[split_name] = rows
    return source_splits


def merge_judge_results(
    judge_results: list[CodexJudgeResult],
    source_splits: dict[str, list[dict[str, Any]]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Join judge results back to their source rows, failing loudly on any
    coverage gap or seed_id mismatch.

    Returns the full merged list (ordered train rows then val rows then test
    rows, ascending row_index within each) plus a per-split coverage dict.
    """
    by_split: dict[str, dict[int, CodexJudgeResult]] = {name: {} for name in _SPLIT_NAMES}
    duplicate_indices: dict[str, list[int]] = {name: [] for name in _SPLIT_NAMES}
    for result in judge_results:
        existing = by_split[result.split]
        if result.row_index in existing:
            duplicate_indices[result.split].append(result.row_index)
        existing[result.row_index] = result

    coverage: dict[str, dict[str, int]] = {}
    merged: list[dict[str, Any]] = []

    for split_name in _SPLIT_NAMES:
        source_rows = source_splits[split_name]
        expected_indices = set(range(len(source_rows)))
        actual_indices = set(by_split[split_name].keys())
        duplicates = sorted(set(duplicate_indices[split_name]))
        missing = sorted(expected_indices - actual_indices)
        unexpected = sorted(actual_indices - expected_indices)

        if missing or duplicates or unexpected:
            problems = []
            if missing:
                problems.append(
                    f"{len(missing)} missing row_index(es) (first 20: {missing[:20]})"
                )
            if duplicates:
                problems.append(
                    f"{len(duplicates)} duplicate row_index(es) (first 20: {duplicates[:20]}) "
                    "-- if Codex restarted numbering at 0 for each 50-100-row batch instead of "
                    "continuing from the previous batch, this is why: row_index must be the "
                    "0-based line number within the WHOLE split file, not within a batch"
                )
            if unexpected:
                problems.append(
                    f"{len(unexpected)} row_index(es) with no matching source row "
                    f"(first 20: {unexpected[:20]})"
                )
            raise ValueError(
                f"split {split_name!r} judge-results row_index coverage is incomplete "
                f"({len(actual_indices)} judged / {len(expected_indices)} expected): "
                + "; ".join(problems)
            )

        coverage[split_name] = {
            "source_rows": len(source_rows),
            "judge_rows": len(by_split[split_name]),
        }

        seed_mismatches: list[str] = []
        for row_index in sorted(actual_indices):
            result = by_split[split_name][row_index]
            source_row = source_rows[row_index]
            if result.seed_id != source_row["seed_id"]:
                seed_mismatches.append(
                    f"row_index {row_index}: judge seed_id {result.seed_id!r} != "
                    f"source seed_id {source_row['seed_id']!r}"
                )
        if seed_mismatches:
            preview = "; ".join(seed_mismatches[:20])
            more = f" (+{len(seed_mismatches) - 20} more)" if len(seed_mismatches) > 20 else ""
            raise ValueError(
                f"split {split_name!r} has {len(seed_mismatches)} seed_id mismatch(es): "
                f"{preview}{more}"
            )

        for row_index in sorted(actual_indices):
            result = by_split[split_name][row_index]
            source_row = source_rows[row_index]
            scores = {dim: getattr(result, dim) for dim in _SCORE_DIMENSIONS}
            merged.append(
                {
                    **source_row,
                    "split": split_name,
                    "row_index": row_index,
                    **scores,
                    "judge_pass": result.judge_pass,
                    "judge_reason": result.reason,
                    "recomputed_pass": all(score >= 3 for score in scores.values()),
                }
            )

    return merged, coverage


def compute_aggregate_stats(merged: list[dict[str, Any]]) -> dict[str, Any]:
    """Descriptive pass-rate and per-dimension-average stats over a merged
    dataset, guarding every division by max(total, 1)."""
    total = len(merged)
    denom = max(total, 1)
    passed = sum(1 for row in merged if row["judge_pass"])

    stats: dict[str, Any] = {
        "total": total,
        "passed": passed,
        "pass_rate": passed / denom,
    }
    for dim in _SCORE_DIMENSIONS:
        stats[f"avg_{dim}"] = sum(row[dim] for row in merged) / denom

    stats["pass_mismatch_count"] = sum(
        1 for row in merged if row["judge_pass"] != row["recomputed_pass"]
    )

    per_split: dict[str, dict[str, Any]] = {}
    for split_name in _SPLIT_NAMES:
        split_rows = [row for row in merged if row["split"] == split_name]
        split_total = len(split_rows)
        split_denom = max(split_total, 1)
        split_passed = sum(1 for row in split_rows if row["judge_pass"])
        per_split[split_name] = {
            "total": split_total,
            "passed": split_passed,
            "pass_rate": split_passed / split_denom,
        }
    stats["per_split"] = per_split

    return stats


def write_merge_outputs(
    merged: list[dict[str, Any]],
    stats: dict[str, Any],
    merged_path: Path,
    summary_path: Path,
) -> None:
    """Write merged.jsonl and summary.json atomically via temp-file-then-
    .replace(), matching repair_corpus_split_governance.py's convention."""
    merged_path = Path(merged_path)
    summary_path = Path(summary_path)
    merged_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    temp_merged = merged_path.with_suffix(merged_path.suffix + ".tmp")
    with temp_merged.open("w", encoding="utf-8", newline="\n") as handle:
        for record in merged:
            handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
    temp_merged.replace(merged_path)

    temp_summary = summary_path.with_suffix(summary_path.suffix + ".tmp")
    with temp_summary.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(stats, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    temp_summary.replace(summary_path)


def _pretty_json_bytes(payload: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(dict(payload), ensure_ascii=False, indent=2) + "\n"
    ).encode("utf-8")


def _final_release_destinations(repo_root: Path) -> dict[str, Path]:
    root = Path(repo_root)
    return {
        **{
            f"splits/{name}.jsonl": root / "data" / "splits" / f"{name}.jsonl"
            for name in _SPLIT_NAMES
        },
        "manifest.json": root / "data" / "manifests" / "manifest.json",
        "decision.jsonl": root
        / "data"
        / "processed"
        / "phase39-mislabel-decision-manifest.jsonl",
        "lineage-quarantine.jsonl": root
        / "data"
        / "processed"
        / "phase39-mislabel-quarantine.jsonl",
        "seed-cap-drops.jsonl": root
        / "data"
        / "processed"
        / "phase39-seed-cap-drops.jsonl",
        "judge-results.jsonl": root / "data" / "processed" / "codex-judge-pass.jsonl",
        "judge-merged.jsonl": root / "data" / "processed" / "judge-merged.jsonl",
        "judge-summary.json": root / "data" / "processed" / "judge-summary.json",
        "judge-provenance.jsonl": root
        / "data"
        / "processed"
        / "phase39-final-judge-provenance.jsonl",
    }


def _candidate_release_sources(candidate_dir: Path) -> dict[str, Path]:
    candidate_dir = Path(candidate_dir)
    return {
        **{
            f"splits/{name}.jsonl": candidate_dir / "splits" / f"{name}.jsonl"
            for name in _SPLIT_NAMES
        },
        "decision.jsonl": candidate_dir / "phase39-mislabel-decision-manifest.jsonl",
        "lineage-quarantine.jsonl": candidate_dir / "phase39-mislabel-quarantine.jsonl",
        "seed-cap-drops.jsonl": candidate_dir / "phase39-seed-cap-drops.jsonl",
    }


def _protected_phase39_paths(repo_root: Path) -> dict[str, Path]:
    phase_dir = (
        Path(repo_root)
        / ".planning"
        / "phases"
        / "39-independent-quality-re-judge"
    )
    return {
        "39-manual-review-sheet.md": phase_dir / "39-manual-review-sheet.md",
        "39-mislabel-triage-sheet.md": phase_dir / "39-mislabel-triage-sheet.md",
        "MISLABEL triage.md": phase_dir / "MISLABEL triage.md",
    }


def _hash_existing(paths: Mapping[str, Path], *, context: str) -> dict[str, str]:
    missing = [str(path) for path in paths.values() if not Path(path).is_file()]
    if missing:
        raise ValueError(f"{context} missing file(s): {missing}")
    return {key: sha256_path(path) for key, path in paths.items()}


def _release_summary(
    *,
    merged: list[dict[str, Any]],
    coverage: Mapping[str, Any],
    provenance: Sequence[FinalJudgeProvenanceRow],
    convergence_report: Mapping[str, Any],
    backup: Mapping[str, Any],
    split_profile: Mapping[str, Any],
    release_timestamp: str,
) -> dict[str, Any]:
    stats = compute_aggregate_stats(merged)
    stats["coverage"] = dict(coverage)
    origin_counts = Counter(row.verdict_origin for row in provenance)
    iteration_counts = Counter(
        str(row.source_iteration)
        for row in provenance
        if row.verdict_origin == "fresh_final_delta"
    )
    stats.update(
        {
            "schema_version": "phase39-final-judge-summary-v1",
            "release_timestamp": release_timestamp,
            "evidence_origins": {
                "carried_forward_exact_record": origin_counts.get(
                    "carried_forward_exact_record", 0
                ),
                "fresh_final_delta": origin_counts.get("fresh_final_delta", 0),
                "fresh_iterations": dict(sorted(iteration_counts.items())),
            },
            "convergence": dict(convergence_report),
            "historical_judge_backup": copy.deepcopy(dict(backup)),
            "final_snapshot": copy.deepcopy(dict(split_profile)),
            "external_api_call_count": 0,
        }
    )
    return stats


def _artifact_metadata(
    *, path: str, payload: bytes, records: int | None = None
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "path": path,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "bytes": len(payload),
    }
    if records is not None:
        result["records"] = records
    return result


def build_final_release_payloads(
    *,
    repo_root: Path,
    candidate_dir: Path,
    convergence_path: Path,
    carry_path: Path,
    fresh_results_path: Path,
    backup: Mapping[str, Any],
    release_timestamp: str,
) -> tuple[dict[str, bytes], dict[str, Any]]:
    """Build every canonical release byte before taking the promotion lock."""
    from src.data_pipeline.apply_mislabel_triage import validate_staged_candidate

    repo_root = Path(repo_root)
    candidate_dir = Path(candidate_dir)
    candidate_stats = validate_staged_candidate(candidate_dir)
    convergence_report = validate_semantic_convergence(
        convergence_path,
        candidate_dir=candidate_dir,
        carry_path=carry_path,
        fresh_results_path=fresh_results_path,
        require_zero_unresolved=True,
    )
    if convergence_report["final_candidate_records"] != candidate_stats["total_rows"]:
        raise ValueError("convergence and candidate row counts differ")
    carry_backup_report = validate_carries_against_historical_backup(
        carry_path=carry_path,
        historical_merged_backup=Path(backup["judge-merged.jsonl"]["path"]),
    )
    combined, provenance = compose_final_judge_evidence(
        candidate_dir=candidate_dir,
        convergence_path=convergence_path,
        carry_path=carry_path,
        fresh_results_path=fresh_results_path,
    )
    source_splits = load_source_splits(candidate_dir / "splits")
    merged, coverage = merge_judge_results(combined, source_splits)
    provenance_payload = _jsonl_bytes(provenance)
    judge_payload = _jsonl_bytes(combined)
    merged_payload = _jsonl_bytes(merged)
    summary = _release_summary(
        merged=merged,
        coverage=coverage,
        provenance=provenance,
        convergence_report=convergence_report,
        backup=backup,
        split_profile=candidate_stats,
        release_timestamp=release_timestamp,
    )
    summary_payload = _pretty_json_bytes(summary)

    candidate_sources = _candidate_release_sources(candidate_dir)
    source_payloads = {
        key: path.read_bytes() for key, path in candidate_sources.items()
    }
    candidate_manifest_path = candidate_dir / "manifest.json"
    candidate_manifest_bytes = candidate_manifest_path.read_bytes()
    candidate_manifest = json.loads(candidate_manifest_bytes.decode("utf-8"))
    final_manifest = copy.deepcopy(candidate_manifest)
    final_manifest["manifest"]["version"] = "phase39-mislabel-triage-final-v1"
    final_manifest["manifest"]["build_timestamp"] = release_timestamp
    final_manifest["manifest"]["git_commit"] = None
    final_manifest["task_scam_mislabel_triage"]["status"] = "promoted_final_release"

    evidence_metadata = {
        "judge_results": _artifact_metadata(
            path="data/processed/codex-judge-pass.jsonl",
            payload=judge_payload,
            records=len(combined),
        ),
        "judge_merged": _artifact_metadata(
            path="data/processed/judge-merged.jsonl",
            payload=merged_payload,
            records=len(merged),
        ),
        "judge_summary": _artifact_metadata(
            path="data/processed/judge-summary.json",
            payload=summary_payload,
        ),
        "judge_provenance": _artifact_metadata(
            path="data/processed/phase39-final-judge-provenance.jsonl",
            payload=provenance_payload,
            records=len(provenance),
        ),
    }
    provenance_metadata = {
        "decision_manifest": _artifact_metadata(
            path="data/processed/phase39-mislabel-decision-manifest.jsonl",
            payload=source_payloads["decision.jsonl"],
            records=len(
                _read_jsonl_objects(
                    candidate_sources["decision.jsonl"], context="decision manifest"
                )
            ),
        ),
        "lineage_quarantine": _artifact_metadata(
            path="data/processed/phase39-mislabel-quarantine.jsonl",
            payload=source_payloads["lineage-quarantine.jsonl"],
            records=len(
                _read_jsonl_objects(
                    candidate_sources["lineage-quarantine.jsonl"],
                    context="lineage quarantine",
                )
            ),
        ),
        "initial_seed_cap_drops": _artifact_metadata(
            path="data/processed/phase39-seed-cap-drops.jsonl",
            payload=source_payloads["seed-cap-drops.jsonl"],
            records=len(
                _read_jsonl_objects(
                    candidate_sources["seed-cap-drops.jsonl"],
                    context="seed cap drops",
                )
            ),
        ),
    }
    origin_counts = Counter(row.verdict_origin for row in provenance)
    final_manifest["phase39_final_release"] = {
        "schema_version": _FINAL_RELEASE_SCHEMA_VERSION,
        "status": "promoted",
        "release_timestamp": release_timestamp,
        "candidate_manifest": {
            "path": _manifest_path_string(candidate_manifest_path),
            "sha256": hashlib.sha256(candidate_manifest_bytes).hexdigest(),
        },
        "semantic_convergence": {
            "path": _manifest_path_string(convergence_path),
            **dict(convergence_report),
        },
        "historical_judge_backup": copy.deepcopy(dict(backup)),
        "judge_evidence": {
            "total_records": len(combined),
            "carried_forward_exact_record": origin_counts.get(
                "carried_forward_exact_record", 0
            ),
            "fresh_final_delta": origin_counts.get("fresh_final_delta", 0),
            "artifacts": evidence_metadata,
        },
        "migration_provenance": provenance_metadata,
        "protected_human_artifacts": copy.deepcopy(
            candidate_manifest["task_scam_mislabel_triage"][
                "protected_review_artifact_sha256"
            ]
        ),
        "external_api_call_count": 0,
    }
    manifest_payload = _pretty_json_bytes(final_manifest)
    payloads = {
        **source_payloads,
        "manifest.json": manifest_payload,
        "judge-results.jsonl": judge_payload,
        "judge-merged.jsonl": merged_payload,
        "judge-summary.json": summary_payload,
        "judge-provenance.jsonl": provenance_payload,
    }
    return payloads, {
        "candidate_stats": candidate_stats,
        "convergence": convergence_report,
        "carry_backup_validation": carry_backup_report,
        "judge_total": len(combined),
        "carry_count": origin_counts.get("carried_forward_exact_record", 0),
        "fresh_count": origin_counts.get("fresh_final_delta", 0),
        "pass_rate": summary["pass_rate"],
        "release_timestamp": release_timestamp,
        "payload_sha256": {
            key: hashlib.sha256(value).hexdigest() for key, value in payloads.items()
        },
    }


def _load_final_provenance(path: Path) -> list[FinalJudgeProvenanceRow]:
    rows: list[FinalJudgeProvenanceRow] = []
    for line_number, raw in enumerate(
        _read_jsonl_objects(path, context="final judge provenance"), start=1
    ):
        try:
            rows.append(FinalJudgeProvenanceRow.model_validate(raw))
        except ValidationError as exc:
            raise ValueError(
                f"final judge provenance line {line_number} is invalid: {exc}"
            ) from exc
    return rows


def validate_final_release(
    *,
    splits_dir: Path,
    manifest_path: Path,
    judge_results_path: Path,
    merged_path: Path,
    summary_path: Path,
    provenance_path: Path,
    convergence_path: Path,
    candidate_dir: Path = Path("data/processed/phase39-mislabel-candidate"),
    carry_path: Path = Path("data/processed/phase39-final-evidence/carry.jsonl"),
    fresh_results_path: Path = Path("data/processed/codex-final-delta-judge.jsonl"),
    backup_dir: Path = Path("data/backup/pre-phase39-mislabel-triage/processed"),
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Recompute the promoted corpus, evidence, stats, and backup bindings."""
    from src.data_pipeline.apply_mislabel_triage import (
        validate_candidate_splits,
        validate_staged_candidate,
    )

    root = Path(repo_root) if repo_root is not None else Path.cwd()
    candidate_dir = Path(candidate_dir)
    candidate_stats = validate_staged_candidate(candidate_dir)
    backup = ensure_historical_judge_backup(
        processed_dir=Path(judge_results_path).parent,
        backup_dir=backup_dir,
    )
    historical_merged_backup = Path(backup["judge-merged.jsonl"]["path"])
    convergence_report = validate_semantic_convergence(
        convergence_path,
        candidate_dir=candidate_dir,
        carry_path=carry_path,
        fresh_results_path=fresh_results_path,
        require_zero_unresolved=True,
        historical_merged_path_override=historical_merged_backup,
    )
    carry_backup_report = validate_carries_against_historical_backup(
        carry_path=carry_path,
        historical_merged_backup=historical_merged_backup,
    )

    live_splits = load_source_splits(splits_dir)
    live_stats = validate_candidate_splits(live_splits, enforce_locked_profile=False)
    if live_stats != candidate_stats:
        raise ValueError("promoted live split profile differs from staged candidate")
    for name in _SPLIT_NAMES:
        live_path = Path(splits_dir) / f"{name}.jsonl"
        candidate_path = candidate_dir / "splits" / f"{name}.jsonl"
        if live_path.read_bytes() != candidate_path.read_bytes():
            raise ValueError(f"promoted live split differs from candidate: {name}")

    try:
        manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"final manifest is unreadable: {exc}") from exc
    release = manifest.get("phase39_final_release")
    if not isinstance(release, dict) or release.get("schema_version") != _FINAL_RELEASE_SCHEMA_VERSION:
        raise ValueError("manifest lacks the final Phase 39 release contract")
    if release.get("status") != "promoted":
        raise ValueError("final release manifest status is not promoted")
    candidate_manifest_hash = sha256_path(candidate_dir / "manifest.json")
    if release.get("candidate_manifest", {}).get("sha256") != candidate_manifest_hash:
        raise ValueError("final release candidate manifest binding differs")
    if release.get("semantic_convergence", {}).get("convergence_sha256") != sha256_path(
        convergence_path
    ):
        raise ValueError("final release convergence binding differs")
    if release.get("semantic_convergence", {}).get("unresolved_count") != 0:
        raise ValueError("final release does not declare zero unresolved identities")
    if release.get("historical_judge_backup") != backup:
        raise ValueError("final release historical backup metadata differs")

    for name in _SPLIT_NAMES:
        live_path = Path(splits_dir) / f"{name}.jsonl"
        expected_entry = {
            "sha256": sha256_path(live_path),
            "records": len(live_splits[name]),
            "bytes": live_path.stat().st_size,
        }
        if manifest.get("manifest", {}).get("files", {}).get(f"{name}.jsonl") != expected_entry:
            raise ValueError(f"manifest split metadata differs for {name}")
    if manifest.get("split_class_distribution") != live_stats["split_class_distribution"]:
        raise ValueError("manifest class distribution differs from promoted splits")
    triage = manifest.get("task_scam_mislabel_triage", {})
    if triage.get("status") != "promoted_final_release":
        raise ValueError("triage manifest was not advanced to promoted final release")
    declared_validation = triage.get("validation")
    if not isinstance(declared_validation, dict) or any(
        declared_validation.get(key) != value
        for key, value in candidate_stats.items()
    ):
        raise ValueError("triage validation profile differs from promoted splits")
    required_validation_markers = {
        "schema_and_literal_spans": "pass",
        "normalized_and_lexical_duplicates_at_0_95": "zero",
        "seed_disjointness": "pass",
        "all_four_labels_in_each_split": "pass",
        "reload_validation": "pass",
    }
    if any(
        declared_validation.get(key) != value
        for key, value in required_validation_markers.items()
    ):
        raise ValueError("triage manifest lacks final integrity PASS markers")

    combined, expected_provenance = compose_final_judge_evidence(
        candidate_dir=candidate_dir,
        convergence_path=convergence_path,
        carry_path=carry_path,
        fresh_results_path=fresh_results_path,
        historical_merged_path_override=historical_merged_backup,
    )
    expected_judge_payload = _jsonl_bytes(combined)
    if Path(judge_results_path).read_bytes() != expected_judge_payload:
        raise ValueError("canonical final judge results differ from exact carry/fresh composition")
    actual_provenance = _load_final_provenance(provenance_path)
    if actual_provenance != expected_provenance:
        raise ValueError("canonical final judge provenance differs from recomputation")
    if Path(provenance_path).read_bytes() != _jsonl_bytes(expected_provenance):
        raise ValueError("canonical final judge provenance bytes are not canonical")

    merged, coverage = merge_judge_results(combined, live_splits)
    expected_merged_payload = _jsonl_bytes(merged)
    if Path(merged_path).read_bytes() != expected_merged_payload:
        raise ValueError("canonical merged judge evidence differs from recomputation")
    try:
        actual_summary = json.loads(Path(summary_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"final judge summary is unreadable: {exc}") from exc
    expected_summary = _release_summary(
        merged=merged,
        coverage=coverage,
        provenance=expected_provenance,
        convergence_report=convergence_report,
        backup=backup,
        split_profile=candidate_stats,
        release_timestamp=release["release_timestamp"],
    )
    if actual_summary != expected_summary:
        raise ValueError("canonical judge summary differs from recomputed descriptive stats")

    evidence_paths = {
        "judge_results": Path(judge_results_path),
        "judge_merged": Path(merged_path),
        "judge_summary": Path(summary_path),
        "judge_provenance": Path(provenance_path),
    }
    declared_evidence = release.get("judge_evidence", {}).get("artifacts", {})
    for key, path in evidence_paths.items():
        declared = declared_evidence.get(key, {})
        if declared.get("sha256") != sha256_path(path) or declared.get("bytes") != path.stat().st_size:
            raise ValueError(f"final manifest evidence metadata differs for {key}")
    if release.get("judge_evidence", {}).get("total_records") != len(combined):
        raise ValueError("final manifest judge total differs")
    origin_counts = Counter(row.verdict_origin for row in expected_provenance)
    for origin in ("carried_forward_exact_record", "fresh_final_delta"):
        if release.get("judge_evidence", {}).get(origin) != origin_counts.get(origin, 0):
            raise ValueError(f"final manifest judge origin count differs for {origin}")

    candidate_sources = _candidate_release_sources(candidate_dir)
    live_sidecars = {
        "decision.jsonl": root
        / "data"
        / "processed"
        / "phase39-mislabel-decision-manifest.jsonl",
        "lineage-quarantine.jsonl": root
        / "data"
        / "processed"
        / "phase39-mislabel-quarantine.jsonl",
        "seed-cap-drops.jsonl": root
        / "data"
        / "processed"
        / "phase39-seed-cap-drops.jsonl",
    }
    for key, path in live_sidecars.items():
        if path.read_bytes() != candidate_sources[key].read_bytes():
            raise ValueError(f"promoted migration sidecar differs from candidate: {key}")

    protected_paths = _protected_phase39_paths(root)
    expected_protected = triage.get("protected_review_artifact_sha256")
    if _hash_existing(protected_paths, context="protected Phase 39 artifact") != expected_protected:
        raise ValueError("protected Phase 39 human artifacts changed")

    return {
        "schema_version": _FINAL_RELEASE_SCHEMA_VERSION,
        "total_rows": len(combined),
        "split_counts": live_stats["split_counts"],
        "label_counts": live_stats["total_class_distribution"],
        "max_seed_share": live_stats["max_seed_share"],
        "judge_coverage": len(combined),
        "carry_count": origin_counts.get("carried_forward_exact_record", 0),
        "fresh_count": origin_counts.get("fresh_final_delta", 0),
        "pass_rate": expected_summary["pass_rate"],
        "manifest_sha256": sha256_path(manifest_path),
        "split_sha256": {
            name: sha256_path(Path(splits_dir) / f"{name}.jsonl")
            for name in _SPLIT_NAMES
        },
        "judge_sha256": {
            key: sha256_path(path) for key, path in evidence_paths.items()
        },
        "convergence_sha256": sha256_path(convergence_path),
        "historical_carry_validation": carry_backup_report,
        "rollback_status": "not_needed",
    }


def _stage_final_release_payloads(
    stage_dir: Path, payloads: Mapping[str, bytes]
) -> dict[str, Path]:
    from src.data_pipeline.apply_mislabel_triage import replace_payload_bundle

    stage_dir = Path(stage_dir)
    destinations = {key: stage_dir / key for key in payloads}
    existing = [path for path in destinations.values() if path.exists()]
    if existing:
        if len(existing) != len(destinations):
            raise ValueError("final release staging directory is partial")
        for key, path in destinations.items():
            if path.read_bytes() != payloads[key]:
                raise ValueError(f"final release staging conflict for {key}")
        return destinations
    originals = {key: None for key in destinations}

    def verify_stage() -> None:
        for key, path in destinations.items():
            if path.read_bytes() != payloads[key]:
                raise ValueError(f"final release stage verification failed for {key}")

    replace_payload_bundle(
        destinations,
        payloads,
        originals,
        operation="Phase 39 final release stage",
        verify_written=verify_stage,
    )
    return destinations


def promote_final_release(
    *,
    repo_root: Path,
    candidate_dir: Path,
    convergence_path: Path,
    carry_path: Path,
    fresh_results_path: Path,
    backup_dir: Path,
    stage_dir: Path,
    verify_promoted: Any | None = None,
) -> dict[str, Any]:
    """Promote all corpus/judge/provenance files under one verified rollback."""
    from src.data_pipeline.apply_mislabel_triage import (
        EXPECTED_INPUT_SHA256,
        exclusive_run_lock,
        replace_payload_bundle,
    )

    root = Path(repo_root).resolve()
    destinations = _final_release_destinations(root)
    manifest_path = destinations["manifest.json"]
    if manifest_path.is_file():
        try:
            existing_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing_manifest = {}
        if existing_manifest.get("phase39_final_release", {}).get("status") == "promoted":
            report = validate_final_release(
                splits_dir=root / "data" / "splits",
                manifest_path=manifest_path,
                judge_results_path=destinations["judge-results.jsonl"],
                merged_path=destinations["judge-merged.jsonl"],
                summary_path=destinations["judge-summary.json"],
                provenance_path=destinations["judge-provenance.jsonl"],
                convergence_path=convergence_path,
                candidate_dir=candidate_dir,
                carry_path=carry_path,
                fresh_results_path=fresh_results_path,
                backup_dir=backup_dir,
                repo_root=root,
            )
            report["promotion_reused"] = True
            return report

    convergence_report = validate_semantic_convergence(
        convergence_path,
        candidate_dir=candidate_dir,
        carry_path=carry_path,
        fresh_results_path=fresh_results_path,
        require_zero_unresolved=True,
    )
    if convergence_report["unresolved_count"] != 0:
        raise ValueError("promotion requires zero unresolved convergence")
    backup = ensure_historical_judge_backup(
        processed_dir=root / "data" / "processed",
        backup_dir=backup_dir,
    )

    stage_manifest = Path(stage_dir) / "manifest.json"
    if stage_manifest.is_file():
        try:
            staged_manifest = json.loads(stage_manifest.read_text(encoding="utf-8"))
            release_timestamp = staged_manifest["phase39_final_release"]["release_timestamp"]
        except (KeyError, json.JSONDecodeError) as exc:
            raise ValueError(f"existing final release stage is invalid: {exc}") from exc
    else:
        release_timestamp = datetime.now(
            timezone(timedelta(hours=7))
        ).isoformat(timespec="seconds")
    payloads, build_report = build_final_release_payloads(
        repo_root=root,
        candidate_dir=candidate_dir,
        convergence_path=convergence_path,
        carry_path=carry_path,
        fresh_results_path=fresh_results_path,
        backup=backup,
        release_timestamp=release_timestamp,
    )
    stage_paths = _stage_final_release_payloads(stage_dir, payloads)

    immutable_paths = {
        "candidate-manifest": Path(candidate_dir) / "manifest.json",
        **{
            f"candidate-{key}": path
            for key, path in _candidate_release_sources(candidate_dir).items()
        },
        "convergence": Path(convergence_path),
        "carry": Path(carry_path),
        "fresh": Path(fresh_results_path),
        **{f"backup-{name}": Path(item["path"]) for name, item in backup.items()},
    }
    immutable_hashes = _hash_existing(immutable_paths, context="final release input")
    protected_paths = _protected_phase39_paths(root)
    protected_hashes = _hash_existing(
        protected_paths, context="protected Phase 39 artifact"
    )

    expected_old = {
        "splits/train.jsonl": EXPECTED_INPUT_SHA256["train.jsonl"],
        "splits/val.jsonl": EXPECTED_INPUT_SHA256["val.jsonl"],
        "splits/test.jsonl": EXPECTED_INPUT_SHA256["test.jsonl"],
        "manifest.json": EXPECTED_INPUT_SHA256["manifest.json"],
        "judge-results.jsonl": _HISTORICAL_JUDGE_SHA256["codex-judge-pass.jsonl"],
        "judge-merged.jsonl": _HISTORICAL_JUDGE_SHA256["judge-merged.jsonl"],
        "judge-summary.json": _HISTORICAL_JUDGE_SHA256["judge-summary.json"],
    }
    lock_path = root / "data" / "processed" / ".phase39-finalization.lock"
    with exclusive_run_lock(lock_path):
        if _hash_existing(immutable_paths, context="pre-promotion final release input") != immutable_hashes:
            raise ValueError("final release immutable input changed before promotion")
        if _hash_existing(protected_paths, context="pre-promotion protected artifact") != protected_hashes:
            raise ValueError("protected Phase 39 artifact changed before promotion")
        for key, expected_hash in expected_old.items():
            path = destinations[key]
            if not path.is_file() or sha256_path(path) != expected_hash:
                raise ValueError(
                    f"live pre-promotion hash lock failed for {key}"
                )
        for key in ("decision.jsonl", "lineage-quarantine.jsonl", "seed-cap-drops.jsonl", "judge-provenance.jsonl"):
            if destinations[key].exists():
                raise ValueError(f"new final-release destination already exists: {destinations[key]}")

        originals = {
            key: path.read_bytes() if path.exists() else None
            for key, path in destinations.items()
        }
        promoted_payloads = {
            key: stage_paths[key].read_bytes() for key in destinations
        }

        def verify_release() -> None:
            report = validate_final_release(
                splits_dir=root / "data" / "splits",
                manifest_path=destinations["manifest.json"],
                judge_results_path=destinations["judge-results.jsonl"],
                merged_path=destinations["judge-merged.jsonl"],
                summary_path=destinations["judge-summary.json"],
                provenance_path=destinations["judge-provenance.jsonl"],
                convergence_path=convergence_path,
                candidate_dir=candidate_dir,
                carry_path=carry_path,
                fresh_results_path=fresh_results_path,
                backup_dir=backup_dir,
                repo_root=root,
            )
            if verify_promoted is not None:
                verify_promoted(report)
            if _hash_existing(protected_paths, context="post-promotion protected artifact") != protected_hashes:
                raise ValueError("protected Phase 39 artifact changed during promotion")
            if _hash_existing(immutable_paths, context="post-promotion final release input") != immutable_hashes:
                raise ValueError("final release immutable input changed during promotion")

        replace_payload_bundle(
            destinations,
            promoted_payloads,
            originals,
            operation="Phase 39 final corpus and judge promotion",
            verify_written=verify_release,
        )

    report = validate_final_release(
        splits_dir=root / "data" / "splits",
        manifest_path=destinations["manifest.json"],
        judge_results_path=destinations["judge-results.jsonl"],
        merged_path=destinations["judge-merged.jsonl"],
        summary_path=destinations["judge-summary.json"],
        provenance_path=destinations["judge-provenance.jsonl"],
        convergence_path=convergence_path,
        candidate_dir=candidate_dir,
        carry_path=carry_path,
        fresh_results_path=fresh_results_path,
        backup_dir=backup_dir,
        repo_root=root,
    )
    report.update(
        {
            "promotion_reused": False,
            "rollback_status": "not_needed_postcheck_passed",
            "release_timestamp": release_timestamp,
            "stage_sha256": build_report["payload_sha256"],
        }
    )
    return report


def _load_downstream_manifest(manifest_path: Path) -> dict[str, Any]:
    try:
        manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"canonical manifest is unreadable: {exc}") from exc
    if manifest.get("phase39_final_release", {}).get("status") != "promoted":
        raise ValueError("downstream contract requires a promoted Phase 39 manifest")
    return manifest


def _require_live_split_integrity_opt_in() -> None:
    """Fail before path handling unless a live-data audit was explicitly enabled."""

    if os.environ.get(_LIVE_SPLIT_INTEGRITY_ENV) != _LIVE_SPLIT_INTEGRITY_TOKEN:
        raise ValueError(
            "live split integrity validation is disabled by default; set "
            f"{_LIVE_SPLIT_INTEGRITY_ENV}={_LIVE_SPLIT_INTEGRITY_TOKEN} and use "
            "the explicit live-data audit entry point"
        )


def _manifest_split_metadata(manifest: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    files = manifest.get("manifest", {}).get("files", {})
    distributions = manifest.get("split_class_distribution", {})
    labels = (
        "bank_impersonation",
        "task_scam",
        "benign",
        "zalo_social_engineering",
    )
    result: dict[str, dict[str, Any]] = {}
    for name in _SPLIT_NAMES:
        file_metadata = files.get(f"{name}.jsonl")
        distribution = distributions.get(name)
        if not isinstance(file_metadata, dict) or not isinstance(distribution, dict):
            raise ValueError(f"canonical manifest lacks downstream metadata for {name}")
        if set(file_metadata) != {"sha256", "records", "bytes"}:
            raise ValueError(f"canonical manifest has invalid file metadata for {name}")
        sha256 = file_metadata.get("sha256")
        records = file_metadata.get("records")
        byte_count = file_metadata.get("bytes")
        if not isinstance(sha256, str) or re.fullmatch(_SHA256_PATTERN, sha256) is None:
            raise ValueError(f"canonical manifest has invalid sha256 for {name}")
        if not isinstance(records, int) or isinstance(records, bool) or records < 0:
            raise ValueError(f"canonical manifest has invalid record count for {name}")
        if not isinstance(byte_count, int) or isinstance(byte_count, bool) or byte_count < 0:
            raise ValueError(f"canonical manifest has invalid byte count for {name}")
        if set(distribution) != set(labels):
            raise ValueError(f"canonical manifest has invalid label metadata for {name}")
        label_counts: dict[str, int] = {}
        for label in labels:
            count = distribution.get(label)
            if not isinstance(count, int) or isinstance(count, bool) or count < 0:
                raise ValueError(
                    f"canonical manifest has invalid {label} count for {name}"
                )
            label_counts[label] = count
        if sum(label_counts.values()) != records:
            raise ValueError(f"canonical manifest label counts do not total {name}")
        result[name] = {
            "records": records,
            "bytes": byte_count,
            "sha256": sha256,
            "label_counts": label_counts,
        }
    return result


def render_downstream_data_contract_from_metadata(
    *, manifest_path: Path, generated_at: str
) -> dict[str, Any]:
    """Render the downstream contract without resolving or touching split paths."""

    manifest = _load_downstream_manifest(manifest_path)
    split_contract = _manifest_split_metadata(manifest)
    total_labels: Counter[str] = Counter()
    for metadata in split_contract.values():
        total_labels.update(metadata["label_counts"])
    total = sum(item["records"] for item in split_contract.values())
    test = split_contract["test"]
    split_governance = manifest.get("task_scam_mislabel_triage", {}).get(
        "split_governance", {}
    )
    split_salt = split_governance.get("salt")
    if not isinstance(split_salt, str) or not split_salt:
        raise ValueError("canonical manifest lacks a split-governance salt")
    max_seed_share = manifest.get("task_scam_mislabel_triage", {}).get(
        "validation", {}
    ).get("max_seed_share")
    if not isinstance(max_seed_share, (int, float)) or isinstance(max_seed_share, bool):
        raise ValueError("canonical manifest lacks a valid maximum seed share")
    return {
        "schema_version": _DOWNSTREAM_CONTRACT_SCHEMA_VERSION,
        "generated_at": generated_at,
        "source_manifest": {
            "path": _manifest_path_string(manifest_path),
            "sha256": sha256_path(manifest_path),
            "version": manifest["manifest"]["version"],
        },
        "total_records": total,
        "splits": split_contract,
        "total_label_counts": {
            label: total_labels.get(label, 0)
            for label in (
                "bank_impersonation",
                "task_scam",
                "benign",
                "zalo_social_engineering",
            )
        },
        "split_governance": {
            "salt": split_salt,
            "whole_seed_groups": True,
            "max_global_seed_share": max_seed_share,
        },
        "phase40_training_boundary": {
            "allowed_splits": ["train", "val"],
            "forbidden_split": "test",
            "rule": "Phase 40 may train/select on train and validation only; it must not read test rows.",
            "starts_after": "Phase 39 final human and report gates are complete",
        },
        "held_out_test": {
            "path": "data/splits/test.jsonl",
            "records": test["records"],
            "bytes": test["bytes"],
            "sha256": test["sha256"],
            "evaluation_phase": 41,
            "touch_policy": "evaluate once after all three checkpoints are frozen",
        },
        "phase41_post_evaluation_fit": {
            "all_data_records": total,
            "allowed_only_after": "held-out results and checkpoint identities are frozen",
            "unbiased_test_score_claim": False,
        },
    }


def render_downstream_data_contract(
    *, manifest_path: Path, splits_dir: Path, generated_at: str
) -> dict[str, Any]:
    """Render from live split bytes after an explicit integrity-audit opt-in."""

    _require_live_split_integrity_opt_in()
    manifest = _load_downstream_manifest(manifest_path)
    splits = load_source_splits(splits_dir)
    split_contract: dict[str, dict[str, Any]] = {}
    total_labels: Counter[str] = Counter()
    for name in _SPLIT_NAMES:
        path = Path(splits_dir) / f"{name}.jsonl"
        labels = Counter(row["label"] for row in splits[name])
        total_labels.update(labels)
        actual = {
            "records": len(splits[name]),
            "bytes": path.stat().st_size,
            "sha256": sha256_path(path),
            "label_counts": {
                label: labels.get(label, 0)
                for label in (
                    "bank_impersonation",
                    "task_scam",
                    "benign",
                    "zalo_social_engineering",
                )
            },
        }
        if manifest.get("manifest", {}).get("files", {}).get(f"{name}.jsonl") != {
            key: actual[key] for key in ("sha256", "records", "bytes")
        }:
            raise ValueError(f"manifest/split mismatch while rendering contract: {name}")
        split_contract[name] = actual
    total = sum(item["records"] for item in split_contract.values())
    test = split_contract["test"]
    split_salt = manifest.get("task_scam_mislabel_triage", {}).get(
        "split_governance", {}
    ).get("salt")
    if not isinstance(split_salt, str) or not split_salt:
        raise ValueError("canonical manifest lacks a split-governance salt")
    return {
        "schema_version": _DOWNSTREAM_CONTRACT_SCHEMA_VERSION,
        "generated_at": generated_at,
        "source_manifest": {
            "path": _manifest_path_string(manifest_path),
            "sha256": sha256_path(manifest_path),
            "version": manifest["manifest"]["version"],
        },
        "total_records": total,
        "splits": split_contract,
        "total_label_counts": {
            label: total_labels.get(label, 0)
            for label in (
                "bank_impersonation",
                "task_scam",
                "benign",
                "zalo_social_engineering",
            )
        },
        "split_governance": {
            "salt": split_salt,
            "whole_seed_groups": True,
            "max_global_seed_share": manifest["task_scam_mislabel_triage"][
                "validation"
            ]["max_seed_share"],
        },
        "phase40_training_boundary": {
            "allowed_splits": ["train", "val"],
            "forbidden_split": "test",
            "rule": "Phase 40 may train/select on train and validation only; it must not read test rows.",
            "starts_after": "Phase 39 final human and report gates are complete",
        },
        "held_out_test": {
            "path": "data/splits/test.jsonl",
            "records": test["records"],
            "bytes": test["bytes"],
            "sha256": test["sha256"],
            "evaluation_phase": 41,
            "touch_policy": "evaluate once after all three checkpoints are frozen",
        },
        "phase41_post_evaluation_fit": {
            "all_data_records": total,
            "allowed_only_after": "held-out results and checkpoint identities are frozen",
            "unbiased_test_score_claim": False,
        },
    }


def validate_downstream_data_contract(
    *, contract_path: Path, manifest_path: Path
) -> dict[str, Any]:
    """Validate committed metadata without accepting or touching a split path."""

    try:
        actual = json.loads(Path(contract_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"downstream data contract is unreadable: {exc}") from exc
    if actual.get("schema_version") != _DOWNSTREAM_CONTRACT_SCHEMA_VERSION:
        raise ValueError("downstream data contract schema version differs")
    generated_at = actual.get("generated_at")
    if not isinstance(generated_at, str) or not generated_at:
        raise ValueError("downstream data contract lacks generated_at")
    expected = render_downstream_data_contract_from_metadata(
        manifest_path=manifest_path,
        generated_at=generated_at,
    )
    if actual != expected:
        raise ValueError("downstream data contract differs from promoted manifest bytes")
    return {
        "schema_version": _DOWNSTREAM_CONTRACT_SCHEMA_VERSION,
        "contract_sha256": sha256_path(contract_path),
        "manifest_sha256": expected["source_manifest"]["sha256"],
        "total_records": expected["total_records"],
        "split_counts": {
            name: expected["splits"][name]["records"] for name in _SPLIT_NAMES
        },
        "held_out_test": expected["held_out_test"],
        "validation_scope": "metadata_only",
    }


def validate_downstream_data_contract_live(
    *, contract_path: Path, manifest_path: Path, splits_dir: Path
) -> dict[str, Any]:
    """Explicit audit entry point that parses, stats, and hashes live splits."""

    _require_live_split_integrity_opt_in()
    metadata_report = validate_downstream_data_contract(
        contract_path=contract_path,
        manifest_path=manifest_path,
    )
    try:
        actual = json.loads(Path(contract_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"downstream data contract is unreadable: {exc}") from exc
    expected = render_downstream_data_contract(
        manifest_path=manifest_path,
        splits_dir=splits_dir,
        generated_at=actual["generated_at"],
    )
    if actual != expected:
        raise ValueError("downstream data contract differs from live split bytes")
    return {**metadata_report, "validation_scope": "explicit_live_data_integrity_audit"}


def write_downstream_data_contract(
    *, contract_path: Path, manifest_path: Path, splits_dir: Path
) -> dict[str, Any]:
    _require_live_split_integrity_opt_in()
    if Path(contract_path).is_file():
        return validate_downstream_data_contract_live(
            contract_path=contract_path,
            manifest_path=manifest_path,
            splits_dir=splits_dir,
        )
    generated_at = datetime.now(
        timezone(timedelta(hours=7))
    ).isoformat(timespec="seconds")
    contract = render_downstream_data_contract(
        manifest_path=manifest_path,
        splits_dir=splits_dir,
        generated_at=generated_at,
    )
    _write_bytes_atomically(contract_path, _pretty_json_bytes(contract))
    return validate_downstream_data_contract_live(
        contract_path=contract_path,
        manifest_path=manifest_path,
        splits_dir=splits_dir,
    )


def prepare_final_judge_queue(
    *,
    candidate_dir: Path,
    historical_merged_path: Path,
    carry_path: Path,
    targets_path: Path,
    batch_dir: Path,
    batch_size: int = 64,
    enforce_locked_projection: bool = True,
) -> dict[str, Any]:
    """Reload Plan 39-02's candidate and prepare exact carry/delta artifacts."""
    candidate_dir = Path(candidate_dir)
    historical_merged_path = Path(historical_merged_path)
    from src.data_pipeline.apply_mislabel_triage import validate_staged_candidate

    validate_staged_candidate(candidate_dir)
    candidate_manifest_path = candidate_dir / "manifest.json"
    candidate_run_path = candidate_dir / "run.json"
    candidate_manifest_hash = sha256_path(candidate_manifest_path)
    historical_hash = sha256_path(historical_merged_path)
    run = json.loads(candidate_run_path.read_text(encoding="utf-8"))
    if run.get("status") != "complete" or run.get("mode") != "stage_only":
        raise ValueError("Plan 39-02 candidate run descriptor is not complete stage-only")
    if run.get("input_sha256", {}).get("judge-merged.jsonl") != historical_hash:
        raise ValueError("historical merged hash differs from the candidate's locked input")

    candidate_splits = load_source_splits(candidate_dir / "splits")
    candidate_split_hashes = {
        name: sha256_path(candidate_dir / "splits" / f"{name}.jsonl")
        for name in _SPLIT_NAMES
    }
    for name in _SPLIT_NAMES:
        declared = run.get("output_sha256", {}).get(f"splits/{name}.jsonl")
        if declared != candidate_split_hashes[name]:
            raise ValueError(f"candidate run descriptor split hash drifted for {name}")
    if run.get("output_sha256", {}).get("manifest.json") != candidate_manifest_hash:
        raise ValueError("candidate run descriptor manifest hash drifted")

    historical_rows = _read_jsonl_objects(
        historical_merged_path, context="historical merged judge"
    )
    carries, targets = build_final_judge_partition(
        candidate_splits,
        historical_rows,
        candidate_manifest_sha256=candidate_manifest_hash,
        candidate_split_sha256=candidate_split_hashes,
        historical_merged_sha256=historical_hash,
    )
    total = sum(len(rows) for rows in candidate_splits.values())
    if enforce_locked_projection:
        expected = {
            "total": _DEFAULT_FINAL_COUNT,
            "carry": _DEFAULT_CARRY_COUNT,
            "delta": _DEFAULT_DELTA_COUNT,
        }
        actual = {"total": total, "carry": len(carries), "delta": len(targets)}
        if actual != expected:
            raise ValueError(
                "locked Phase 39 carry/delta projection changed; refusing to force counts "
                f"(expected={expected}, actual={actual})"
            )

    manifest_path = materialize_batch_bundle(
        targets=targets,
        carries=carries,
        aggregate_targets_path=targets_path,
        carry_path=carry_path,
        batch_dir=batch_dir,
        candidate_dir=candidate_dir,
        candidate_manifest_sha256=candidate_manifest_hash,
        historical_merged_sha256=historical_hash,
        batch_size=batch_size,
        iteration=0,
        historical_merged_path=historical_merged_path,
    )
    validation = validate_batch_bundle(
        manifest_path,
        candidate_dir=candidate_dir,
        targets_path=targets_path,
        carry_path=carry_path,
        require_status="pending",
    )
    return {
        **validation,
        "candidate_manifest_sha256": candidate_manifest_hash,
        "historical_merged_sha256": historical_hash,
        "carry_path": str(Path(carry_path)),
        "targets_path": str(Path(targets_path)),
        "batch_manifest_path": str(manifest_path),
        "external_api_call_count": 0,
        "fresh_judgments_created": 0,
    }


def validate_batch_result(batch_manifest_path: Path, batch_id: str) -> dict[str, Any]:
    manifest = _load_batch_manifest(batch_manifest_path)
    matches = [entry for entry in manifest.batches if entry.batch_id == batch_id]
    if len(matches) != 1:
        raise ValueError(f"batch manifest has no unique entry for {batch_id}")
    entry = matches[0]
    target_path = _resolve_declared_path(entry.target_path)
    result_path = _resolve_declared_path(entry.result_path)
    if sha256_path(target_path) != entry.target_sha256:
        raise ValueError(f"batch {batch_id} target SHA-256 mismatch")
    if not result_path.is_file():
        raise ValueError(f"batch {batch_id} result file is missing")
    targets = _load_final_targets(target_path)
    results = _load_final_results(result_path)
    _validate_results_for_targets(targets, results, context=f"batch {batch_id}")
    result_hash = sha256_path(result_path)
    if entry.status == "complete" and result_hash != entry.result_sha256:
        raise ValueError(f"completed batch {batch_id} result SHA-256 mismatch")
    return {
        "batch_id": batch_id,
        "status": entry.status,
        "target_count": len(targets),
        "result_count": len(results),
        "target_sha256": entry.target_sha256,
        "result_sha256": result_hash,
    }


def _legacy_main(argv: Sequence[str]) -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Merge and validate Codex's independent judge-output file against "
            "the real data/splits/{train,val,test}.jsonl source rows, computing "
            "descriptive quality stats."
        )
    )
    parser.add_argument(
        "--judge-results",
        type=Path,
        default=Path("data/processed/codex-judge-pass.jsonl"),
    )
    parser.add_argument("--splits-dir", type=Path, default=Path("data/splits"))
    parser.add_argument(
        "--output-merged", type=Path, default=Path("data/processed/judge-merged.jsonl")
    )
    parser.add_argument(
        "--output-summary", type=Path, default=Path("data/processed/judge-summary.json")
    )
    args = parser.parse_args(list(argv))

    if not args.judge_results.exists():
        raise FileNotFoundError(
            f"{args.judge_results} does not exist yet. Run the Codex judge pass "
            "first per .planning/codex-judge-instructions.md (paste that file "
            "into Codex CLI, let it judge all three split files, then re-run "
            "this tool)."
        )

    judge_results = load_judge_results(args.judge_results)
    source_splits = load_source_splits(args.splits_dir)
    merged, coverage = merge_judge_results(judge_results, source_splits)
    stats = compute_aggregate_stats(merged)
    stats["coverage"] = coverage
    write_merge_outputs(merged, stats, args.output_merged, args.output_summary)

    print(f"Merged {stats['total']} rows (pass rate {stats['pass_rate']:.3f})")
    for dim in _SCORE_DIMENSIONS:
        print(f"  avg_{dim}: {stats[f'avg_{dim}']:.3f}")
    print(f"pass_mismatch_count: {stats['pass_mismatch_count']}")
    for split_name in _SPLIT_NAMES:
        split_stats = stats["per_split"][split_name]
        print(
            f"  {split_name}: {split_stats['passed']}/{split_stats['total']} passed "
            f"(rate {split_stats['pass_rate']:.3f})"
        )
    print(f"Merged output written to {args.output_merged}")
    print(f"Summary output written to {args.output_summary}")


def _prepare_final_cli(argv: Sequence[str]) -> None:
    parser = argparse.ArgumentParser(
        prog="judge_merge prepare-final",
        description="Prepare exact carries and deterministic fresh-delta judge batches.",
    )
    parser.add_argument(
        "--candidate-dir",
        type=Path,
        default=Path("data/processed/phase39-mislabel-candidate"),
    )
    parser.add_argument(
        "--historical-merged",
        type=Path,
        default=Path("data/processed/judge-merged.jsonl"),
    )
    parser.add_argument(
        "--carry",
        type=Path,
        default=Path("data/processed/phase39-final-judge-carry.jsonl"),
    )
    parser.add_argument(
        "--targets",
        type=Path,
        default=Path("data/processed/phase39-final-judge-delta-targets.jsonl"),
    )
    parser.add_argument(
        "--batch-dir",
        type=Path,
        default=Path("data/processed/phase39-final-judge-batches/iteration-00"),
    )
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument(
        "--allow-unlocked-projection",
        action="store_true",
        help="Allow counts other than the locked 1562/541/2103 projection.",
    )
    args = parser.parse_args(list(argv))
    report = prepare_final_judge_queue(
        candidate_dir=args.candidate_dir,
        historical_merged_path=args.historical_merged,
        carry_path=args.carry,
        targets_path=args.targets,
        batch_dir=args.batch_dir,
        batch_size=args.batch_size,
        enforce_locked_projection=not args.allow_unlocked_projection,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


def _validate_batches_cli(argv: Sequence[str]) -> None:
    parser = argparse.ArgumentParser(prog="judge_merge validate-batches")
    parser.add_argument("--candidate-dir", type=Path)
    parser.add_argument("--carry", type=Path)
    parser.add_argument("--targets", type=Path)
    parser.add_argument("--batch-manifest", type=Path, required=True)
    parser.add_argument("--combined-results", type=Path)
    parser.add_argument(
        "--require-status", choices=("pending", "complete"), required=True
    )
    args = parser.parse_args(list(argv))
    report = validate_batch_bundle(
        args.batch_manifest,
        candidate_dir=args.candidate_dir,
        targets_path=args.targets,
        carry_path=args.carry,
        combined_results_path=args.combined_results,
        require_status=args.require_status,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


def _validate_batch_cli(argv: Sequence[str]) -> None:
    parser = argparse.ArgumentParser(prog="judge_merge validate-batch")
    parser.add_argument("--batch-manifest", type=Path, required=True)
    parser.add_argument("--batch-id", required=True)
    parser.add_argument("--mark-complete", action="store_true")
    args = parser.parse_args(list(argv))
    report = (
        complete_batch(args.batch_manifest, args.batch_id)
        if args.mark_complete
        else validate_batch_result(args.batch_manifest, args.batch_id)
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


def _validate_convergence_cli(argv: Sequence[str]) -> None:
    parser = argparse.ArgumentParser(prog="judge_merge validate-convergence")
    parser.add_argument("--convergence", type=Path, required=True)
    parser.add_argument("--candidate-dir", type=Path)
    parser.add_argument("--carry", type=Path)
    parser.add_argument("--fresh-results", type=Path)
    parser.add_argument("--require-zero-unresolved", action="store_true")
    parser.add_argument("--historical-merged-backup", type=Path)
    args = parser.parse_args(list(argv))
    report = validate_semantic_convergence(
        args.convergence,
        candidate_dir=args.candidate_dir,
        carry_path=args.carry,
        fresh_results_path=args.fresh_results,
        require_zero_unresolved=args.require_zero_unresolved,
        historical_merged_path_override=args.historical_merged_backup,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


def _validate_final_release_cli(argv: Sequence[str]) -> None:
    parser = argparse.ArgumentParser(prog="judge_merge validate-final-release")
    parser.add_argument("--splits-dir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--judge-results", type=Path, required=True)
    parser.add_argument("--merged", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--provenance", type=Path, required=True)
    parser.add_argument("--convergence", type=Path, required=True)
    parser.add_argument(
        "--candidate-dir",
        type=Path,
        default=Path("data/processed/phase39-mislabel-candidate"),
    )
    parser.add_argument(
        "--carry",
        type=Path,
        default=Path("data/processed/phase39-final-evidence/carry.jsonl"),
    )
    parser.add_argument(
        "--fresh-results",
        type=Path,
        default=Path("data/processed/codex-final-delta-judge.jsonl"),
    )
    parser.add_argument(
        "--backup-dir",
        type=Path,
        default=Path("data/backup/pre-phase39-mislabel-triage/processed"),
    )
    args = parser.parse_args(list(argv))
    report = validate_final_release(
        splits_dir=args.splits_dir,
        manifest_path=args.manifest,
        judge_results_path=args.judge_results,
        merged_path=args.merged,
        summary_path=args.summary,
        provenance_path=args.provenance,
        convergence_path=args.convergence,
        candidate_dir=args.candidate_dir,
        carry_path=args.carry,
        fresh_results_path=args.fresh_results,
        backup_dir=args.backup_dir,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


def _promote_final_release_cli(argv: Sequence[str]) -> None:
    parser = argparse.ArgumentParser(prog="judge_merge promote-final-release")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--candidate-dir",
        type=Path,
        default=Path("data/processed/phase39-mislabel-candidate"),
    )
    parser.add_argument(
        "--convergence",
        type=Path,
        default=Path("data/processed/phase39-semantic-convergence.json"),
    )
    parser.add_argument(
        "--carry",
        type=Path,
        default=Path("data/processed/phase39-final-evidence/carry.jsonl"),
    )
    parser.add_argument(
        "--fresh-results",
        type=Path,
        default=Path("data/processed/codex-final-delta-judge.jsonl"),
    )
    parser.add_argument(
        "--backup-dir",
        type=Path,
        default=Path("data/backup/pre-phase39-mislabel-triage/processed"),
    )
    parser.add_argument(
        "--stage-dir",
        type=Path,
        default=Path("data/processed/phase39-final-release-staging"),
    )
    args = parser.parse_args(list(argv))
    report = promote_final_release(
        repo_root=args.repo_root,
        candidate_dir=args.candidate_dir,
        convergence_path=args.convergence,
        carry_path=args.carry,
        fresh_results_path=args.fresh_results,
        backup_dir=args.backup_dir,
        stage_dir=args.stage_dir,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


def _downstream_contract_cli(argv: Sequence[str], *, write: bool) -> None:
    command = "write-downstream-contract" if write else "validate-downstream-contract"
    parser = argparse.ArgumentParser(prog=f"judge_merge {command}")
    parser.add_argument(
        "--contract",
        type=Path,
        default=Path(
            ".planning/phases/39-independent-quality-re-judge/"
            "39-DOWNSTREAM-DATA-CONTRACT.json"
        ),
    )
    parser.add_argument(
        "--manifest", type=Path, default=Path("data/manifests/manifest.json")
    )
    parser.add_argument("--splits-dir", type=Path, default=Path("data/splits"))
    parser.add_argument(
        "--live-data-integrity-audit",
        action="store_true",
        help=(
            "Select the split-reading integrity audit; also requires "
            f"{_LIVE_SPLIT_INTEGRITY_ENV}={_LIVE_SPLIT_INTEGRITY_TOKEN}"
        ),
    )
    args = parser.parse_args(list(argv))
    if write:
        report = write_downstream_data_contract(
            contract_path=args.contract,
            manifest_path=args.manifest,
            splits_dir=args.splits_dir,
        )
    elif args.live_data_integrity_audit:
        report = validate_downstream_data_contract_live(
            contract_path=args.contract,
            manifest_path=args.manifest,
            splits_dir=args.splits_dir,
        )
    else:
        report = validate_downstream_data_contract(
            contract_path=args.contract,
            manifest_path=args.manifest,
        )
    print(json.dumps(report, ensure_ascii=False, indent=2))


def _write_downstream_contract_cli(argv: Sequence[str]) -> None:
    _downstream_contract_cli(argv, write=True)


def _validate_downstream_contract_cli(argv: Sequence[str]) -> None:
    _downstream_contract_cli(argv, write=False)


def main() -> None:
    commands = {
        "prepare-final": _prepare_final_cli,
        "validate-batches": _validate_batches_cli,
        "validate-batch": _validate_batch_cli,
        "validate-convergence": _validate_convergence_cli,
        "validate-final-release": _validate_final_release_cli,
        "promote-final-release": _promote_final_release_cli,
        "write-downstream-contract": _write_downstream_contract_cli,
        "validate-downstream-contract": _validate_downstream_contract_cli,
    }
    argv = sys.argv[1:]
    if argv and argv[0] in commands:
        commands[argv[0]](argv[1:])
        return
    _legacy_main(argv)


if __name__ == "__main__":
    main()
