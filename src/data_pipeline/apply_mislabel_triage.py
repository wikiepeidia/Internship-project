"""Stage the Phase 39 human mislabel-triage migration without touching live data.

The human-edited compact audit is treated as untrusted input.  Decisions are
parsed with exact coverage, rebound to the current corpus by conservative
content identity, and written to an independently reload-validated candidate
bundle.  The command in this module is deliberately stage-only; promotion is
an explicit API for a later plan and uses verified all-file rollback.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import subprocess
import unicodedata
from collections import Counter, defaultdict
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Iterable, Literal, Mapping

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from src.data_pipeline.generate_mislabel_triage_sheet import select_mislabel_candidates
from src.data_pipeline.processing.dedup import fuzz
from src.data_pipeline.processing.normalizer import normalize_text
from src.data_pipeline.repair_corpus_split_governance import (
    assign_stratified_group_split,
    enforce_seed_cap,
)
from src.data_pipeline.schemas import DatasetRecord


SPLIT_NAMES = ("train", "val", "test")
LABELS = (
    "bank_impersonation",
    "task_scam",
    "benign",
    "zalo_social_engineering",
)
DATASET_FIELDS = (
    "text",
    "label",
    "risk_tier",
    "suspicious_spans",
    "xai_explanation",
    "source",
    "seed_id",
)
SPLIT_RATIOS = (0.8, 0.1, 0.1)
SPLIT_SALT = "phase39-mislabel-triage-v1"
DOMINANT_ZALO_SEED = "seed_157ce0adb043"
INDEPENDENT_ZALO_CANDIDATE = 47
INDEPENDENT_ZALO_SEED = "seed_c6c8772ac332"
EXPECTED_DECISION_COUNT = 324
EXPECTED_JUDGE_CANDIDATE_COUNT = 329
EXPECTED_POST_DISPOSITION_ROWS = 2_136
EXPECTED_OUTPUT_TOTAL = 2_103
EXPECTED_SPLIT_COUNTS = {"train": 1_665, "val": 218, "test": 220}
EXPECTED_SPLIT_DISTRIBUTION = {
    "train": {
        "bank_impersonation": 597,
        "task_scam": 306,
        "benign": 517,
        "zalo_social_engineering": 245,
    },
    "val": {
        "bank_impersonation": 76,
        "task_scam": 49,
        "benign": 72,
        "zalo_social_engineering": 21,
    },
    "test": {
        "bank_impersonation": 70,
        "task_scam": 49,
        "benign": 66,
        "zalo_social_engineering": 35,
    },
}
EXPECTED_TOTAL_DISTRIBUTION = {
    "bank_impersonation": 743,
    "task_scam": 404,
    "benign": 655,
    "zalo_social_engineering": 301,
}
SEMANTIC_QUARANTINE_SCHEMA_VERSION = "phase39-semantic-quarantine-v1"
SEMANTIC_QUARANTINE_REASON = "fresh_judge_unrepairable_label"
SEMANTIC_CAP_DROP_REASON = "global_iterative_seed_cap_after_semantic_quarantine"
EXPECTED_POST_QUARANTINE_ROWS = 2_097
EXPECTED_SEMANTIC_QUARANTINE_ROWS = 4
EXPECTED_SEMANTIC_QUARANTINE_CAP_DROPS = 2
EXPECTED_INPUT_SHA256 = {
    "train.jsonl": "6454a271c6133f1ebbd41010390b8ea6ceae0a8ab0a75b2ab545099db3319ee8",
    "val.jsonl": "7adfe8cd9a124dbb3d87046bb32f9fbd127d3e344c45be77c8bb9efa700aaa75",
    "test.jsonl": "019aec39979429ca8005dd299d2ddaf7d3ecfdade259eecc4d3129adaed25938",
    "manifest.json": "4794cedae52cc5531083a569c3e63c419335a0544f365f4a4d6245048efc2b90",
    "judge-merged.jsonl": "e8b4d947271717e56556a74136c57d83dd58589c78699d557999140a9fb55750",
    "MISLABEL triage.md": "c408dcf4161d84056b7c22e1fb3e975352a52cd5fbf2b111f11b5dfece0c089c",
}
EXPECTED_PROTECTED_AUDIT_SHA256 = {
    "39-manual-review-sheet.md": "e078b3bf6efd29c8f80f7ea8afaeb1121803c4ce8322fe4a497dd997b9b17743",
    "39-mislabel-triage-sheet.md": "39ca1768c0a114156aece97e7dff2269b074a5125d59b8592f215e3e36415cc7",
    "MISLABEL triage.md": "c408dcf4161d84056b7c22e1fb3e975352a52cd5fbf2b111f11b5dfece0c089c",
}

Label = Literal[
    "bank_impersonation", "zalo_social_engineering", "task_scam", "benign"
]
RiskTier = Literal["benign", "suspicious", "high-risk"]


class MislabelTriageError(ValueError):
    """Raised before live promotion when any migration invariant fails."""


class TriageDecision(BaseModel):
    """One normalized human decision with its original spelling retained."""

    model_config = ConfigDict(extra="forbid")

    candidate_number: int = Field(ge=1, le=EXPECTED_DECISION_COUNT)
    raw_decision: str = Field(min_length=1)
    normalized_action: Literal["drop", "relabel"]
    new_label: Label | None
    notes: str = Field(min_length=1)
    normalization_reason: str | None = None


class DecisionDisposition(BaseModel):
    """Auditable binding from one human decision to one current record."""

    model_config = ConfigDict(extra="forbid")

    candidate_number: int
    raw_decision: str
    normalized_action: Literal["drop", "relabel"]
    approved_label: Label | None
    notes: str
    normalization_reason: str | None
    disposition: Literal["drop", "admitted_relabel", "lineage_quarantine"]
    disposition_reason: str
    record_identity: str
    text_sha256: str
    historical_split: str
    historical_row_index: int
    live_split: Literal["train", "val", "test"]
    live_row_index: int
    record_digest_before: str
    record_digest_after: str | None
    original_record: DatasetRecord
    approved_record: DatasetRecord | None
    label_only_preservation_verified: bool | None


class CodexSemanticRepairDecision(BaseModel):
    """Closed semantic-repair contract consumed by the next Phase 39 plan.

    The four identity/meaning fields are intentionally absent.  Pydantic's
    closed model rejects attempts to replace label, text, source, or seed_id.
    """

    model_config = ConfigDict(extra="forbid")

    expected_record_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    new_risk_tier: RiskTier
    new_suspicious_spans: list[str]
    new_xai_explanation: str = Field(min_length=20)
    notes: str = Field(min_length=1)


class SemanticQuarantineHashArtifact(BaseModel):
    """One immutable, repository-relative artifact reference."""

    model_config = ConfigDict(extra="forbid", strict=True)

    path: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class SemanticQuarantineRowArtifact(SemanticQuarantineHashArtifact):
    records: int = Field(ge=0)


class SemanticQuarantineSplitArtifact(SemanticQuarantineRowArtifact):
    split: Literal["train", "val", "test"]


class SemanticQuarantineSourceCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    manifest: SemanticQuarantineHashArtifact
    splits: list[SemanticQuarantineSplitArtifact] = Field(min_length=3, max_length=3)

    @model_validator(mode="after")
    def validate_exact_split_coverage(self) -> "SemanticQuarantineSourceCandidate":
        names = [item.split for item in self.splits]
        if names != list(SPLIT_NAMES):
            raise ValueError(
                f"source_candidate splits must be ordered {list(SPLIT_NAMES)}, got {names}"
            )
        return self


class SemanticQuarantineFreshJudge(BaseModel):
    """Local closed copy of the fresh FinalJudgeResult evidence shape.

    Keeping the schema here avoids a circular import from ``judge_merge`` while
    still checking its critical score, digest, coordinate, and computed-pass
    invariants.
    """

    model_config = ConfigDict(
        extra="forbid", strict=True, populate_by_name=True
    )

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
    record_digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_computed_pass(self) -> "SemanticQuarantineFreshJudge":
        scores = (
            self.realism,
            self.label_correctness,
            self.code_switch_naturalness,
            self.risk_tier_correctness,
            self.suspicious_span_accuracy,
        )
        if self.judge_pass != all(score >= 3 for score in scores):
            raise ValueError("pass does not match the five fresh-judge scores")
        if self.label_correctness >= 3:
            raise ValueError("semantic quarantine requires label_correctness below 3")
        return self


class SemanticQuarantineContract(BaseModel):
    """Closed authorization for the sole 2,103 -> 2,097 candidate transition."""

    model_config = ConfigDict(extra="forbid", strict=True)

    schema_version: Literal["phase39-semantic-quarantine-v1"]
    status: Literal["applied"]
    reason: Literal["fresh_judge_unrepairable_label"]
    source_candidate: SemanticQuarantineSourceCandidate
    quarantine_artifact: SemanticQuarantineRowArtifact
    cap_drop_artifact: SemanticQuarantineRowArtifact
    cap_pct: float
    split_ratios: list[float] = Field(min_length=3, max_length=3)
    split_salt: str = Field(min_length=1)
    expected_profile: dict[str, Any]

    @model_validator(mode="after")
    def validate_locked_governance(self) -> "SemanticQuarantineContract":
        if self.cap_pct != 0.08:
            raise ValueError("semantic quarantine cap_pct must be exactly 0.08")
        if self.split_ratios != list(SPLIT_RATIOS):
            raise ValueError(
                f"semantic quarantine split_ratios must be {list(SPLIT_RATIOS)}"
            )
        if self.split_salt != SPLIT_SALT:
            raise ValueError(
                f"semantic quarantine split_salt must be exactly {SPLIT_SALT!r}"
            )
        if self.quarantine_artifact.records != EXPECTED_SEMANTIC_QUARANTINE_ROWS:
            raise ValueError(
                "semantic quarantine artifact must declare exactly "
                f"{EXPECTED_SEMANTIC_QUARANTINE_ROWS} records"
            )
        if self.cap_drop_artifact.records != EXPECTED_SEMANTIC_QUARANTINE_CAP_DROPS:
            raise ValueError(
                "semantic quarantine cap-drop artifact must declare exactly "
                f"{EXPECTED_SEMANTIC_QUARANTINE_CAP_DROPS} records"
            )
        return self


@dataclass(frozen=True)
class BoundCandidate:
    candidate_number: int
    historical_record: dict[str, Any]
    historical_split: str
    historical_row_index: int
    live_record: dict[str, Any]
    live_split: str
    live_row_index: int
    record_identity: str


@dataclass
class Projection:
    splits: dict[str, list[dict[str, Any]]]
    dispositions: list[DecisionDisposition]
    quarantine_rows: list[dict[str, Any]]
    cap_drop_rows: list[dict[str, Any]]
    cap_stats: dict[str, Any]
    validation: dict[str, Any]


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_path(path: Path) -> str:
    return sha256_bytes(Path(path).read_bytes())


def canonicalize_identity_text(text: str) -> str:
    """Apply only the conservative transformations approved for identity."""
    normalized = unicodedata.normalize("NFC", text.replace("\r\n", "\n").replace("\r", "\n"))
    if normalized.endswith("\n"):
        normalized = normalized[:-1]
    return normalized


def text_sha256(text: str) -> str:
    return sha256_bytes(canonicalize_identity_text(text).encode("utf-8"))


def record_identity(seed_id: str, text: str) -> str:
    return f"{seed_id}:{text_sha256(text)}"


def record_digest(record: Mapping[str, Any] | DatasetRecord) -> str:
    payload = record.model_dump(mode="json") if isinstance(record, DatasetRecord) else dict(record)
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256_bytes(encoded)


def validate_dataset_record(record: Mapping[str, Any], *, context: str) -> dict[str, Any]:
    actual_fields = set(record)
    expected_fields = set(DATASET_FIELDS)
    if actual_fields != expected_fields:
        missing = sorted(expected_fields - actual_fields)
        extra = sorted(actual_fields - expected_fields)
        raise MislabelTriageError(
            f"{context} does not have the exact seven-field DatasetRecord contract "
            f"(missing={missing}, extra={extra})"
        )
    try:
        payload = DatasetRecord.model_validate(dict(record)).model_dump(mode="json")
    except Exception as exc:
        raise MislabelTriageError(f"{context} is not schema-valid: {exc}") from exc
    invalid_spans = [
        span
        for span in payload["suspicious_spans"]
        if not span or span not in payload["text"]
    ]
    if invalid_spans:
        raise MislabelTriageError(
            f"{context} has {len(invalid_spans)} non-literal suspicious span(s): "
            f"{invalid_spans[:10]}"
        )
    return payload


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                value = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise MislabelTriageError(
                    f"{path} line {line_number} is not valid JSON: {exc}"
                ) from exc
            if not isinstance(value, dict):
                raise MislabelTriageError(f"{path} line {line_number} is not a JSON object")
            rows.append(value)
    return rows


def encode_jsonl(rows: Iterable[Mapping[str, Any]]) -> bytes:
    return "".join(
        json.dumps(dict(row), ensure_ascii=False, separators=(",", ":")) + "\n"
        for row in rows
    ).encode("utf-8")


def _decision_from_raw(
    candidate_number: int,
    raw_decision: str,
    notes: str,
) -> TriageDecision:
    stripped = raw_decision.strip()
    normalization_reason: str | None = None
    if stripped == "Drop row":
        action: Literal["drop", "relabel"] = "drop"
        new_label: Label | None = None
    elif candidate_number == 103 and stripped == "Drop":
        action = "drop"
        new_label = None
        normalization_reason = "candidate 103: exact raw `Drop` normalized to `drop`"
    elif candidate_number == 320 and stripped == "Relabel to: Beigin":
        action = "relabel"
        new_label = "benign"
        normalization_reason = (
            "candidate 320: exact raw `Beigin` spelling normalized to `benign`"
        )
    else:
        match = re.fullmatch(r"Relabel to: (.+)", stripped)
        if not match:
            raise MislabelTriageError(
                f"candidate {candidate_number} has unsupported decision spelling {raw_decision!r}"
            )
        requested_label = match.group(1)
        if requested_label not in LABELS:
            raise MislabelTriageError(
                f"candidate {candidate_number} names unsupported label {requested_label!r}"
            )
        action = "relabel"
        new_label = requested_label  # type: ignore[assignment]

    return TriageDecision(
        candidate_number=candidate_number,
        raw_decision=raw_decision,
        normalized_action=action,
        new_label=new_label,
        notes=notes,
        normalization_reason=normalization_reason,
    )


def parse_triage_decision_text(text: str) -> list[TriageDecision]:
    """Parse exactly 324 numbered decision/note blocks, aggregating errors."""
    lines = text.splitlines()
    parsed: list[TriageDecision] = []
    errors: list[str] = []
    consumed: set[int] = set()
    decision_pattern = re.compile(r"^(\d+)\.(.*)$")
    note_pattern = re.compile(r"^Notes?:\s*(.*)$")

    for index, line in enumerate(lines):
        match = decision_pattern.fullmatch(line)
        if not match:
            continue
        consumed.add(index)
        candidate_number = int(match.group(1))
        raw_decision = match.group(2)
        note_index = index + 1
        if note_index >= len(lines):
            errors.append(f"line {index + 1}: candidate {candidate_number} has no note line")
            continue
        consumed.add(note_index)
        note_match = note_pattern.fullmatch(lines[note_index])
        if not note_match:
            errors.append(
                f"line {note_index + 1}: candidate {candidate_number} note must use `Note:` or `Notes:`"
            )
            continue
        notes = note_match.group(1)
        if not notes.strip():
            errors.append(f"line {note_index + 1}: candidate {candidate_number} has an empty note")
            continue
        try:
            parsed.append(_decision_from_raw(candidate_number, raw_decision, notes))
        except (MislabelTriageError, ValidationError) as exc:
            errors.append(f"line {index + 1}: {exc}")

    for index, line in enumerate(lines):
        if line.strip() and index not in consumed:
            errors.append(f"line {index + 1}: unexpected nonblank content {line!r}")

    numbers = [decision.candidate_number for decision in parsed]
    duplicates = sorted(number for number, count in Counter(numbers).items() if count > 1)
    missing = sorted(set(range(1, EXPECTED_DECISION_COUNT + 1)) - set(numbers))
    extras = sorted(set(numbers) - set(range(1, EXPECTED_DECISION_COUNT + 1)))
    if duplicates:
        errors.append(f"duplicate candidate number(s): {duplicates[:20]}")
    if missing:
        errors.append(f"missing candidate number(s): {missing[:20]}")
    if extras:
        errors.append(f"out-of-range candidate number(s): {extras[:20]}")
    if len(parsed) != EXPECTED_DECISION_COUNT:
        errors.append(
            f"parsed {len(parsed)} decisions, expected exactly {EXPECTED_DECISION_COUNT}"
        )
    if errors:
        suffix = f" (+{len(errors) - 30} more)" if len(errors) > 30 else ""
        raise MislabelTriageError(
            f"triage decision parse failed with {len(errors)} problem(s): "
            + "; ".join(errors[:30])
            + suffix
        )
    return sorted(parsed, key=lambda decision: decision.candidate_number)


def parse_triage_decisions(path: Path) -> list[TriageDecision]:
    if not Path(path).is_file():
        raise FileNotFoundError(f"{path} does not exist")
    return parse_triage_decision_text(Path(path).read_text(encoding="utf-8"))


def load_semantic_repair_decisions(path: Path) -> list[CodexSemanticRepairDecision]:
    errors: list[str] = []
    decisions: list[CodexSemanticRepairDecision] = []
    for line_number, row in enumerate(read_jsonl(path), start=1):
        try:
            decisions.append(CodexSemanticRepairDecision.model_validate(row))
        except ValidationError as exc:
            errors.append(f"line {line_number}: {exc}")
    digests = [decision.expected_record_digest for decision in decisions]
    duplicates = sorted(digest for digest, count in Counter(digests).items() if count > 1)
    if duplicates:
        errors.append(f"duplicate expected_record_digest value(s): {duplicates[:20]}")
    if errors:
        raise MislabelTriageError(
            f"semantic repair input failed with {len(errors)} problem(s): "
            + "; ".join(errors[:20])
        )
    return decisions


def apply_semantic_repairs(
    records: list[dict[str, Any]],
    decisions: list[CodexSemanticRepairDecision],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Apply only explicit risk/spans/explanation replacements in memory."""
    requested_digests = [decision.expected_record_digest for decision in decisions]
    duplicate_digests = sorted(
        digest for digest, count in Counter(requested_digests).items() if count > 1
    )
    if duplicate_digests:
        raise MislabelTriageError(
            f"semantic repair contains duplicate record digest(s): {duplicate_digests[:20]}"
        )
    validated = [
        validate_dataset_record(record, context=f"semantic repair input row {index}")
        for index, record in enumerate(records)
    ]
    digest_index: dict[str, list[int]] = defaultdict(list)
    for index, record in enumerate(validated):
        digest_index[record_digest(record)].append(index)

    problems: list[str] = []
    replacements: dict[int, tuple[dict[str, Any], CodexSemanticRepairDecision]] = {}
    for decision in decisions:
        matches = digest_index.get(decision.expected_record_digest, [])
        if len(matches) != 1:
            problems.append(
                f"digest {decision.expected_record_digest} matched {len(matches)} current records"
            )
            continue
        index = matches[0]
        patched = copy.deepcopy(validated[index])
        patched["risk_tier"] = decision.new_risk_tier
        patched["suspicious_spans"] = list(decision.new_suspicious_spans)
        patched["xai_explanation"] = decision.new_xai_explanation
        try:
            patched = validate_dataset_record(
                patched, context=f"semantic repair result {decision.expected_record_digest}"
            )
        except MislabelTriageError as exc:
            problems.append(str(exc))
            continue
        for field in ("label", "text", "source", "seed_id"):
            if patched[field] != validated[index][field]:
                problems.append(
                    f"semantic repair {decision.expected_record_digest} changed forbidden field {field}"
                )
        replacements[index] = (patched, decision)
    if problems:
        raise MislabelTriageError(
            f"semantic repair refused with {len(problems)} problem(s): "
            + "; ".join(problems[:20])
        )

    output = copy.deepcopy(validated)
    provenance: list[dict[str, Any]] = []
    for index, (patched, decision) in replacements.items():
        before = output[index]
        output[index] = patched
        provenance.append(
            {
                "expected_record_digest": decision.expected_record_digest,
                "result_record_digest": record_digest(patched),
                "fields_replaced": [
                    "risk_tier",
                    "suspicious_spans",
                    "xai_explanation",
                ],
                "identity_fields_preserved": {
                    field: before[field] == patched[field]
                    for field in ("label", "text", "source", "seed_id")
                },
                "notes": decision.notes,
            }
        )
    return output, provenance


def load_live_splits(splits_dir: Path) -> dict[str, list[dict[str, Any]]]:
    splits: dict[str, list[dict[str, Any]]] = {}
    for split_name in SPLIT_NAMES:
        path = Path(splits_dir) / f"{split_name}.jsonl"
        if not path.is_file():
            raise FileNotFoundError(f"{path} does not exist")
        splits[split_name] = [
            validate_dataset_record(row, context=f"{split_name}:{index}")
            for index, row in enumerate(read_jsonl(path))
        ]
    return splits


def reconstruct_bound_candidates(
    merged_rows: list[dict[str, Any]],
    live_splits: dict[str, list[dict[str, Any]]],
    *,
    expected_count: int = EXPECTED_DECISION_COUNT,
) -> list[BoundCandidate]:
    selected = select_mislabel_candidates(merged_rows)
    if expected_count == EXPECTED_DECISION_COUNT and len(selected) != EXPECTED_JUDGE_CANDIDATE_COUNT:
        raise MislabelTriageError(
            f"historical judge selected {len(selected)} candidates, expected "
            f"{EXPECTED_JUDGE_CANDIDATE_COUNT}"
        )

    index: dict[str, list[tuple[str, int, dict[str, Any]]]] = defaultdict(list)
    for split_name in SPLIT_NAMES:
        for row_index, record in enumerate(live_splits[split_name]):
            identity = record_identity(record["seed_id"], record["text"])
            index[identity].append((split_name, row_index, record))

    present: list[tuple[dict[str, Any], tuple[str, int, dict[str, Any]], str]] = []
    ambiguous: list[str] = []
    for historical in selected:
        missing_fields = [field for field in DATASET_FIELDS if field not in historical]
        if missing_fields:
            raise MislabelTriageError(
                f"historical candidate lacks DatasetRecord fields {missing_fields}"
            )
        historical_record = {field: historical[field] for field in DATASET_FIELDS}
        identity = record_identity(historical_record["seed_id"], historical_record["text"])
        matches = index.get(identity, [])
        if len(matches) > 1:
            ambiguous.append(f"{identity} ({len(matches)} live matches)")
        elif len(matches) == 1:
            present.append((historical, matches[0], identity))
    if ambiguous:
        raise MislabelTriageError(
            f"candidate identity binding is ambiguous: {ambiguous[:20]}"
        )
    if len(present) != expected_count:
        raise MislabelTriageError(
            f"candidate identity binding found {len(present)} unique live rows, "
            f"expected {expected_count}"
        )

    bound: list[BoundCandidate] = []
    seen_identities: set[str] = set()
    for candidate_number, (historical, live_match, identity) in enumerate(present, start=1):
        if identity in seen_identities:
            raise MislabelTriageError(f"historical candidate identity repeats: {identity}")
        seen_identities.add(identity)
        live_split, live_row_index, live_record = live_match
        historical_record = {field: historical[field] for field in DATASET_FIELDS}
        bound.append(
            BoundCandidate(
                candidate_number=candidate_number,
                historical_record=historical_record,
                historical_split=str(historical.get("split", "unknown")),
                historical_row_index=int(historical.get("row_index", -1)),
                live_record=copy.deepcopy(live_record),
                live_split=live_split,
                live_row_index=live_row_index,
                record_identity=identity,
            )
        )
    return bound


def _assert_label_only(before: Mapping[str, Any], after: Mapping[str, Any]) -> None:
    for field in DATASET_FIELDS:
        if field == "label":
            continue
        if before[field] != after[field]:
            raise MislabelTriageError(f"label-only relabel changed forbidden field {field}")


def build_dispositions(
    decisions: list[TriageDecision],
    candidates: list[BoundCandidate],
    *,
    enforce_locked_totals: bool = True,
) -> list[DecisionDisposition]:
    decision_map = {decision.candidate_number: decision for decision in decisions}
    if len(decision_map) != len(decisions):
        raise MislabelTriageError("decision list contains duplicate candidate numbers")
    if set(decision_map) != {candidate.candidate_number for candidate in candidates}:
        raise MislabelTriageError("decision coverage does not equal bound candidate coverage")

    dispositions: list[DecisionDisposition] = []
    for candidate in candidates:
        decision = decision_map[candidate.candidate_number]
        original = validate_dataset_record(
            candidate.live_record,
            context=f"bound candidate {candidate.candidate_number}",
        )
        if original["label"] != "task_scam":
            raise MislabelTriageError(
                f"candidate {candidate.candidate_number} is no longer labeled task_scam"
            )

        approved: dict[str, Any] | None = None
        preservation: bool | None = None
        if decision.normalized_action == "drop":
            disposition = "drop"
            disposition_reason = "human reviewer selected removal"
        else:
            if decision.new_label is None:
                raise MislabelTriageError(
                    f"candidate {candidate.candidate_number} relabel has no target label"
                )
            approved = copy.deepcopy(original)
            approved["label"] = decision.new_label
            approved = validate_dataset_record(
                approved,
                context=f"approved candidate {candidate.candidate_number}",
            )
            _assert_label_only(original, approved)
            preservation = True
            if (
                decision.new_label == "zalo_social_engineering"
                and original["seed_id"] == DOMINANT_ZALO_SEED
            ):
                disposition = "lineage_quarantine"
                disposition_reason = (
                    "human-approved Zalo semantics excluded because 176 rows share "
                    f"the non-independent lineage {DOMINANT_ZALO_SEED}"
                )
            else:
                disposition = "admitted_relabel"
                disposition_reason = "human-approved label-only relabel admitted"

        dispositions.append(
            DecisionDisposition(
                candidate_number=candidate.candidate_number,
                raw_decision=decision.raw_decision,
                normalized_action=decision.normalized_action,
                approved_label=decision.new_label,
                notes=decision.notes,
                normalization_reason=decision.normalization_reason,
                disposition=disposition,  # type: ignore[arg-type]
                disposition_reason=disposition_reason,
                record_identity=candidate.record_identity,
                text_sha256=text_sha256(original["text"]),
                historical_split=candidate.historical_split,
                historical_row_index=candidate.historical_row_index,
                live_split=candidate.live_split,  # type: ignore[arg-type]
                live_row_index=candidate.live_row_index,
                record_digest_before=record_digest(original),
                record_digest_after=record_digest(approved) if approved else None,
                original_record=DatasetRecord.model_validate(original),
                approved_record=DatasetRecord.model_validate(approved) if approved else None,
                label_only_preservation_verified=preservation,
            )
        )

    if enforce_locked_totals:
        normalized = Counter(
            "drop" if item.normalized_action == "drop" else item.approved_label
            for item in dispositions
        )
        if normalized != Counter(
            {
                "drop": 91,
                "bank_impersonation": 48,
                "zalo_social_engineering": 177,
                "benign": 8,
            }
        ):
            raise MislabelTriageError(f"normalized decision totals drifted: {normalized}")
        disposition_counts = Counter(item.disposition for item in dispositions)
        if disposition_counts != Counter(
            {"drop": 91, "admitted_relabel": 57, "lineage_quarantine": 176}
        ):
            raise MislabelTriageError(f"disposition totals drifted: {disposition_counts}")
        independent = dispositions[INDEPENDENT_ZALO_CANDIDATE - 1]
        if not (
            independent.candidate_number == INDEPENDENT_ZALO_CANDIDATE
            and independent.approved_label == "zalo_social_engineering"
            and independent.original_record.seed_id == INDEPENDENT_ZALO_SEED
            and independent.disposition == "admitted_relabel"
        ):
            raise MislabelTriageError("candidate 47 independent-Zalo admission policy drifted")
        quarantined = [
            item for item in dispositions if item.disposition == "lineage_quarantine"
        ]
        if {item.original_record.seed_id for item in quarantined} != {DOMINANT_ZALO_SEED}:
            raise MislabelTriageError("lineage quarantine includes an unexpected seed")
    return dispositions


def _apply_dispositions(
    live_splits: dict[str, list[dict[str, Any]]],
    dispositions: list[DecisionDisposition],
) -> list[dict[str, Any]]:
    by_identity = {item.record_identity: item for item in dispositions}
    if len(by_identity) != len(dispositions):
        raise MislabelTriageError("disposition identities are not unique")
    encountered: Counter[str] = Counter()
    admitted: list[dict[str, Any]] = []
    for split_name in SPLIT_NAMES:
        for record in live_splits[split_name]:
            identity = record_identity(record["seed_id"], record["text"])
            item = by_identity.get(identity)
            if item is None:
                admitted.append(copy.deepcopy(record))
                continue
            encountered[identity] += 1
            if item.disposition in {"drop", "lineage_quarantine"}:
                continue
            if item.approved_record is None:
                raise MislabelTriageError(
                    f"admitted candidate {item.candidate_number} lacks approved record"
                )
            transformed = item.approved_record.model_dump(mode="json")
            _assert_label_only(record, transformed)
            admitted.append(transformed)
    bad_coverage = {
        identity: count
        for identity, count in encountered.items()
        if count != 1
    }
    missing = sorted(set(by_identity) - set(encountered))
    if bad_coverage or missing:
        raise MislabelTriageError(
            f"disposition application coverage failed (bad={bad_coverage}, missing={missing[:20]})"
        )
    if len(admitted) != EXPECTED_POST_DISPOSITION_ROWS:
        raise MislabelTriageError(
            f"post-disposition pool has {len(admitted)} rows, expected "
            f"{EXPECTED_POST_DISPOSITION_ROWS}"
        )
    return admitted


def _derive_cap_drops(
    before: list[dict[str, Any]], after: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    after_counts = Counter(record_digest(record) for record in after)
    drops: list[dict[str, Any]] = []
    for record in before:
        digest = record_digest(record)
        if after_counts[digest]:
            after_counts[digest] -= 1
            continue
        drops.append(
            {
                "record_digest": digest,
                "record_identity": record_identity(record["seed_id"], record["text"]),
                "seed_id": record["seed_id"],
                "reason": "global iterative seed cap at 8% after human triage",
                "record": copy.deepcopy(record),
            }
        )
    if any(after_counts.values()):
        raise MislabelTriageError("seed-cap output contains records absent from its input")
    return drops


def _normalized_duplicate_text(text: str) -> str:
    return normalize_text(text).casefold()


def _assert_no_duplicates(splits: dict[str, list[dict[str, Any]]]) -> None:
    indexed: list[tuple[str, int, str]] = []
    seen: dict[str, tuple[str, int]] = {}
    for split_name in SPLIT_NAMES:
        for row_index, record in enumerate(splits[split_name]):
            normalized = _normalized_duplicate_text(record["text"])
            if normalized in seen:
                raise MislabelTriageError(
                    f"normalized duplicate at {seen[normalized]} and {(split_name, row_index)}"
                )
            seen[normalized] = (split_name, row_index)
            indexed.append((split_name, row_index, normalized))
    for left_index, (left_split, left_row, left_text) in enumerate(indexed):
        for right_split, right_row, right_text in indexed[left_index + 1 :]:
            ratio = fuzz.ratio(left_text, right_text) / 100.0
            if ratio >= 0.95:
                raise MislabelTriageError(
                    "lexical near-duplicate at "
                    f"{left_split}:{left_row}/{right_split}:{right_row} ({ratio:.3f})"
                )


def class_distribution(rows: Iterable[Mapping[str, Any]]) -> dict[str, int]:
    counts = Counter(row["label"] for row in rows)
    return {label: counts.get(label, 0) for label in LABELS}


def validate_candidate_splits(
    splits: dict[str, list[dict[str, Any]]],
    *,
    enforce_locked_profile: bool = True,
) -> dict[str, Any]:
    if set(splits) != set(SPLIT_NAMES):
        raise MislabelTriageError(f"candidate split set is wrong: {sorted(splits)}")
    seed_splits: dict[str, set[str]] = defaultdict(set)
    combined: list[dict[str, Any]] = []
    distributions: dict[str, dict[str, int]] = {}
    for split_name in SPLIT_NAMES:
        validated_rows: list[dict[str, Any]] = []
        for row_index, row in enumerate(splits[split_name]):
            payload = validate_dataset_record(
                row, context=f"candidate {split_name}:{row_index}"
            )
            seed_splits[payload["seed_id"]].add(split_name)
            validated_rows.append(payload)
        distributions[split_name] = class_distribution(validated_rows)
        if any(distributions[split_name][label] <= 0 for label in LABELS):
            raise MislabelTriageError(f"candidate {split_name} lacks one or more labels")
        combined.extend(validated_rows)

    leaking = {seed: sorted(names) for seed, names in seed_splits.items() if len(names) > 1}
    if leaking:
        raise MislabelTriageError(f"candidate has cross-split seed leakage: {leaking}")
    _assert_no_duplicates(splits)

    total = len(combined)
    if total == 0:
        raise MislabelTriageError("candidate is empty")
    seed_counts = Counter(row["seed_id"] for row in combined)
    max_seed, max_count = max(seed_counts.items(), key=lambda item: (item[1], item[0]))
    max_share = max_count / total
    if max_share > 0.08 + 1e-9:
        raise MislabelTriageError(f"seed {max_seed} exceeds 8% cap at {max_share:.6%}")
    ratios = {name: len(splits[name]) / total for name in SPLIT_NAMES}
    targets = dict(zip(SPLIT_NAMES, SPLIT_RATIOS, strict=True))
    if any(abs(ratios[name] - targets[name]) > 0.01 for name in SPLIT_NAMES):
        raise MislabelTriageError(f"candidate split ratios exceed tolerance: {ratios}")

    total_distribution = class_distribution(combined)
    zalo_rows = [row for row in combined if row["label"] == "zalo_social_engineering"]
    zalo_seed_counts = Counter(row["seed_id"] for row in zalo_rows)
    stats = {
        "total_rows": total,
        "split_counts": {name: len(splits[name]) for name in SPLIT_NAMES},
        "split_class_distribution": distributions,
        "total_class_distribution": total_distribution,
        "max_seed_id": max_seed,
        "max_seed_count": max_count,
        "max_seed_share": max_share,
        "split_ratios": ratios,
        "unique_zalo_seeds": len(zalo_seed_counts),
        "max_zalo_seed_count": max(zalo_seed_counts.values()),
        "max_zalo_seed_share": max(zalo_seed_counts.values()) / len(zalo_rows),
    }
    if enforce_locked_profile:
        if total != EXPECTED_OUTPUT_TOTAL:
            raise MislabelTriageError(
                f"candidate has {total} rows, expected {EXPECTED_OUTPUT_TOTAL}"
            )
        if stats["split_counts"] != EXPECTED_SPLIT_COUNTS:
            raise MislabelTriageError(
                f"candidate split counts drifted: {stats['split_counts']}"
            )
        if distributions != EXPECTED_SPLIT_DISTRIBUTION:
            raise MislabelTriageError(
                f"candidate split distribution drifted: {distributions}"
            )
        if total_distribution != EXPECTED_TOTAL_DISTRIBUTION:
            raise MislabelTriageError(
                f"candidate total distribution drifted: {total_distribution}"
            )
        if len(zalo_seed_counts) != 61 or max(zalo_seed_counts.values()) != 5:
            raise MislabelTriageError(
                "candidate Zalo lineage profile must be 301 rows across 61 seeds, max 5"
            )
    return stats


def build_projection(
    decisions: list[TriageDecision],
    merged_rows: list[dict[str, Any]],
    live_splits: dict[str, list[dict[str, Any]]],
) -> Projection:
    candidates = reconstruct_bound_candidates(merged_rows, live_splits)
    dispositions = build_dispositions(decisions, candidates)
    admitted = _apply_dispositions(live_splits, dispositions)
    capped, cap_stats = enforce_seed_cap(admitted, cap_pct=0.08)
    cap_drop_rows = _derive_cap_drops(admitted, capped)
    if len(cap_drop_rows) != 33 or cap_stats.get("rows_dropped_seed_cap") != 33:
        raise MislabelTriageError(
            f"seed cap dropped {len(cap_drop_rows)} rows / stats={cap_stats}, expected 33"
        )
    assignments = assign_stratified_group_split(
        capped,
        ratios=SPLIT_RATIOS,
        salt=SPLIT_SALT,
    )
    projected = {name: [] for name in SPLIT_NAMES}
    for record in capped:
        projected[assignments[record["seed_id"]]].append(record)
    validation = validate_candidate_splits(projected)

    quarantine_rows = [
        {
            "candidate_number": item.candidate_number,
            "record_identity": item.record_identity,
            "approved_label": item.approved_label,
            "reason": item.disposition_reason,
            "notes": item.notes,
            "original_record": item.original_record.model_dump(mode="json"),
            "approved_label_record": (
                item.approved_record.model_dump(mode="json") if item.approved_record else None
            ),
        }
        for item in dispositions
        if item.disposition == "lineage_quarantine"
    ]
    if len(quarantine_rows) != 176:
        raise MislabelTriageError("lineage quarantine row count drifted")
    return Projection(
        splits=projected,
        dispositions=dispositions,
        quarantine_rows=quarantine_rows,
        cap_drop_rows=cap_drop_rows,
        cap_stats=cap_stats,
        validation=validation,
    )


def _git_provenance(repo_root: Path) -> dict[str, Any]:
    def run(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args],
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
        )

    head = run("rev-parse", "HEAD")
    status = run("status", "--porcelain", "--untracked-files=normal")
    return {
        "git_commit": head.stdout.strip() if head.returncode == 0 else None,
        "worktree_dirty": status.returncode != 0 or bool(status.stdout.strip()),
    }


def _run_id(input_hashes: Mapping[str, str]) -> str:
    return sha256_bytes(
        json.dumps(dict(sorted(input_hashes.items())), separators=(",", ":")).encode("utf-8")
    )


def _decision_manifest_rows(projection: Projection) -> list[dict[str, Any]]:
    return [item.model_dump(mode="json") for item in projection.dispositions]


def build_candidate_manifest(
    existing_manifest: dict[str, Any],
    projection: Projection,
    split_payloads: dict[str, bytes],
    decision_payload: bytes,
    quarantine_payload: bytes,
    cap_drop_payload: bytes,
    input_hashes: Mapping[str, str],
    protected_hashes: Mapping[str, str],
    git_provenance: Mapping[str, Any],
) -> dict[str, Any]:
    updated = copy.deepcopy(existing_manifest)
    split_files = {
        f"{name}.jsonl": {
            "sha256": sha256_bytes(split_payloads[name]),
            "records": len(projection.splits[name]),
            "bytes": len(split_payloads[name]),
        }
        for name in SPLIT_NAMES
    }
    previous_timestamp = existing_manifest.get("manifest", {}).get("build_timestamp")
    updated["manifest"] = {
        "version": "phase39-mislabel-triage-candidate-v1",
        # A candidate is deterministic.  Its chronology is the prior release
        # timestamp plus the immutable run id, not a wall-clock regeneration.
        "build_timestamp": previous_timestamp,
        "git_commit": (
            None if git_provenance["worktree_dirty"] else git_provenance["git_commit"]
        ),
        "files": split_files,
    }
    updated["split_class_distribution"] = projection.validation[
        "split_class_distribution"
    ]
    updated["task_scam_mislabel_triage"] = {
        "status": "staged_projection_awaiting_semantic_judgment",
        "run_id": _run_id(input_hashes),
        "description": (
            "Targeted human review of 324 live task_scam records previously scored "
            "below 3/5 for label correctness; not a full-corpus human annotation."
        ),
        "input_sha256": dict(input_hashes),
        "protected_review_artifact_sha256": dict(protected_hashes),
        "human_decisions": {
            "reviewed": 324,
            "drop": 91,
            "relabel_total": 233,
            "relabel_bank_impersonation": 48,
            "relabel_zalo_social_engineering": 177,
            "relabel_benign": 8,
            "normalization_events": [
                {
                    "candidate_number": item.candidate_number,
                    "raw_decision": item.raw_decision,
                    "normalization_reason": item.normalization_reason,
                }
                for item in projection.dispositions
                if item.normalization_reason
            ],
        },
        "decision_identity_dispositions": [
            {
                "candidate_number": item.candidate_number,
                "record_identity": item.record_identity,
                "normalized_action": item.normalized_action,
                "approved_label": item.approved_label,
                "disposition": item.disposition,
            }
            for item in projection.dispositions
        ],
        "lineage_policy": {
            "shared_seed": DOMINANT_ZALO_SEED,
            "human_approved_but_quarantined": 176,
            "independent_candidate_admitted": INDEPENDENT_ZALO_CANDIDATE,
            "independent_seed": INDEPENDENT_ZALO_SEED,
            "quarantine_artifact_sha256": sha256_bytes(quarantine_payload),
        },
        "seed_cap": {
            "cap_pct": 0.08,
            "rows_dropped": len(projection.cap_drop_rows),
            "stats": projection.cap_stats,
            "drop_artifact_sha256": sha256_bytes(cap_drop_payload),
        },
        "split_governance": {
            "ratios": list(SPLIT_RATIOS),
            "salt": SPLIT_SALT,
            "whole_seed_groups": True,
            "split_counts": projection.validation["split_counts"],
            "split_class_distribution": projection.validation[
                "split_class_distribution"
            ],
        },
        "decision_manifest_sha256": sha256_bytes(decision_payload),
        "candidate_output_sha256": {
            f"splits/{name}.jsonl": split_files[f"{name}.jsonl"]["sha256"]
            for name in SPLIT_NAMES
        },
        "semantic_repair_contract": {
            "status": "pending_plan_39_03",
            "identity": "exact seven-field record digest",
            "permitted_replacements": [
                "risk_tier",
                "suspicious_spans",
                "xai_explanation",
            ],
            "forbidden_replacements": ["label", "text", "source", "seed_id"],
        },
        "validation": {
            **projection.validation,
            "schema_and_literal_spans": "pass",
            "normalized_and_lexical_duplicates_at_0_95": "zero",
            "seed_disjointness": "pass",
            "all_four_labels_in_each_split": "pass",
            "reload_validation": "pass",
        },
        "implementation_provenance": dict(git_provenance),
        "external_api_call_count": 0,
    }
    return updated


def render_audit_markdown(
    projection: Projection,
    input_hashes: Mapping[str, str],
    protected_hashes: Mapping[str, str],
    split_hashes: Mapping[str, str],
) -> bytes:
    validation = projection.validation
    text = f"""# Phase 39 Mislabel Audit and Lineage Disposition

## Scope and wording for the report

A Vietnamese-fluent project reviewer manually examined all **324 live `task_scam` records** that the independent Codex pass scored below 3/5 for label correctness. This was a targeted review of judge-flagged candidates, **not independent annotation of the full corpus**.

The review selected **91 records for removal** and made **233 semantic relabel decisions**: 48 as `bank_impersonation`, 177 as `zalo_social_engineering`, and 8 as `benign`. Candidate 103's exact raw `Drop` was normalized to `drop`; candidate 320's exact raw `Beigin` was normalized to `benign`. No decision was inferred from the reviewer's free-text note.

## Lineage-safe admission

The label judgment and training admission decision are separate. Of the 177 human-approved Zalo relabels, **176 share the single seed `{DOMINANT_ZALO_SEED}`**. Those 176 records remain documented as semantically approved but are quarantined from training because they are variants of one non-independent root scenario. Candidate {INDEPENDENT_ZALO_CANDIDATE} (`{INDEPENDENT_ZALO_SEED}`) is the one independently seeded Zalo relabel admitted from this audit.

The resulting human dispositions are therefore:

- 91 human drops
- 57 admitted label-only relabels
- 176 shared-lineage quarantines

Every admitted relabel changes only `label`; text, risk tier, suspicious spans, XAI explanation, source, and seed ID are byte/value-preserved. Risk tier, spans, and explanation are awaiting the separately hash-bound semantic judge step.

## Staged projection

After the human dispositions, 2,136 rows remained. The existing iterative global 8% seed cap removed 33 additional rows with a dedicated audit trail. Whole seed groups were then reassigned deterministically with salt `{SPLIT_SALT}`.

| Split | Rows | Bank | Task scam | Benign | Zalo |
|---|---:|---:|---:|---:|---:|
| train | 1,665 | 597 | 306 | 517 | 245 |
| val | 218 | 76 | 49 | 72 | 21 |
| test | 220 | 70 | 49 | 66 | 35 |
| **total** | **2,103** | **743** | **404** | **655** | **301** |

The Zalo subset has 301 rows across 61 seed groups; its largest seed contributes 5/301 ({validation['max_zalo_seed_share']:.4%}). The largest seed in the full staged corpus contributes {validation['max_seed_count']}/2,103 ({validation['max_seed_share']:.4%}). No seed crosses splits, every split contains all four labels, all listed suspicious spans are literal substrings, and normalized/lexical duplicates at the 0.95 threshold are zero.

This **2,103-row result is a staged projection, not a frozen release**. It still requires the Phase 39 semantic delta judge and final promotion gate.

## Immutable evidence

- Compact 324-decision audit SHA-256: `{input_hashes['MISLABEL triage.md']}`
- Historical merged judge SHA-256: `{input_hashes['judge-merged.jsonl']}`
- Candidate train SHA-256: `{split_hashes['train.jsonl']}`
- Candidate val SHA-256: `{split_hashes['val.jsonl']}`
- Candidate test SHA-256: `{split_hashes['test.jsonl']}`
- Protected 100-row review sheet SHA-256: `{protected_hashes['39-manual-review-sheet.md']}`
- Protected historical triage sheet SHA-256: `{protected_hashes['39-mislabel-triage-sheet.md']}`

The live `data/splits/{{train,val,test}}.jsonl`, live manifest, historical judge output, and all three user review artifacts were read-only inputs during this stage.
"""
    return text.encode("utf-8")


def _write_bytes_atomically(path: Path, payload: bytes) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.phase39.tmp")
    temporary.write_bytes(payload)
    os.replace(temporary, path)


@contextmanager
def exclusive_run_lock(path: Path):
    """Hold a nonblocking process lock that the OS releases after a crash."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("a+b")
    locked = False
    try:
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"\0")
            handle.flush()
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:  # pragma: no cover - exercised on POSIX CI rather than Windows.
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            locked = True
        except OSError as exc:
            raise MislabelTriageError(
                f"another Phase 39 candidate writer holds {path}"
            ) from exc
        yield
    finally:
        if locked:
            handle.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:  # pragma: no cover - exercised on POSIX CI rather than Windows.
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()


def _restore_and_verify_destinations(
    destinations: Mapping[str, Path],
    originals: Mapping[str, bytes | None],
) -> list[str]:
    errors: list[str] = []
    for key, destination in destinations.items():
        try:
            original = originals[key]
            if original is None:
                if destination.exists():
                    destination.unlink()
            else:
                _write_bytes_atomically(destination, original)
        except Exception as exc:
            errors.append(f"restore {key}: {type(exc).__name__}: {exc}")
    for key, destination in destinations.items():
        try:
            original = originals[key]
            if original is None:
                if destination.exists():
                    errors.append(f"verify {key}: expected destination to be absent")
            elif not destination.is_file() or destination.read_bytes() != original:
                errors.append(f"verify {key}: restored bytes differ")
        except Exception as exc:
            errors.append(f"verify {key}: {type(exc).__name__}: {exc}")
    return errors


def replace_payload_bundle(
    destinations: Mapping[str, Path],
    payloads: Mapping[str, bytes],
    originals: Mapping[str, bytes | None],
    *,
    operation: str,
    verify_written: Callable[[], None] | None = None,
) -> None:
    expected = set(destinations)
    if set(payloads) != expected or set(originals) != expected:
        raise MislabelTriageError(f"{operation} bundle keys are inconsistent")
    try:
        for key, destination in destinations.items():
            _write_bytes_atomically(destination, payloads[key])
        for key, destination in destinations.items():
            actual = destination.read_bytes()
            if actual != payloads[key]:
                raise MislabelTriageError(f"{operation} post-write mismatch for {key}")
        if verify_written is not None:
            verify_written()
    except Exception as exc:
        rollback_errors = _restore_and_verify_destinations(destinations, originals)
        if rollback_errors:
            raise MislabelTriageError(
                f"{operation} failed ({type(exc).__name__}: {exc}); rollback incomplete: "
                + "; ".join(rollback_errors)
            ) from exc
        raise


def _candidate_paths(candidate_dir: Path) -> dict[str, Path]:
    candidate_dir = Path(candidate_dir)
    return {
        "splits/train.jsonl": candidate_dir / "splits" / "train.jsonl",
        "splits/val.jsonl": candidate_dir / "splits" / "val.jsonl",
        "splits/test.jsonl": candidate_dir / "splits" / "test.jsonl",
        "manifest.json": candidate_dir / "manifest.json",
        "phase39-mislabel-decision-manifest.jsonl": candidate_dir
        / "phase39-mislabel-decision-manifest.jsonl",
        "phase39-mislabel-quarantine.jsonl": candidate_dir
        / "phase39-mislabel-quarantine.jsonl",
        "phase39-seed-cap-drops.jsonl": candidate_dir / "phase39-seed-cap-drops.jsonl",
        "run.json": candidate_dir / "run.json",
    }


def _semantic_quarantine_repo_root(candidate_dir: Path) -> Path:
    """Return the repository root for a contract-bearing standard candidate.

    Contract paths are repository-relative so that the manifest remains
    portable.  Requiring the normal ``data/processed/<candidate>`` location
    prevents a caller from silently changing what those relative paths mean.
    """
    resolved = Path(candidate_dir).resolve()
    if resolved.parent.name != "processed" or resolved.parent.parent.name != "data":
        raise MislabelTriageError(
            "semantic quarantine candidate must live at data/processed/<candidate>"
        )
    return resolved.parent.parent.parent


def _resolve_semantic_quarantine_artifact(
    repo_root: Path,
    artifact: SemanticQuarantineHashArtifact,
    *,
    context: str,
) -> Path:
    raw = artifact.path
    pure = PurePosixPath(raw)
    if (
        "\\" in raw
        or pure.is_absolute()
        or not pure.parts
        or any(part in {"", ".", ".."} for part in pure.parts)
        or pure.as_posix() != raw
    ):
        raise MislabelTriageError(
            f"{context} path must be a normalized repository-relative POSIX path"
        )
    resolved_root = Path(repo_root).resolve()
    path = resolved_root.joinpath(*pure.parts).resolve()
    try:
        path.relative_to(resolved_root)
    except ValueError as exc:
        raise MislabelTriageError(f"{context} path escapes the repository") from exc
    if not path.is_file():
        raise MislabelTriageError(f"{context} artifact does not exist: {raw}")
    actual_sha256 = sha256_path(path)
    if actual_sha256 != artifact.sha256:
        raise MislabelTriageError(
            f"{context} hash mismatch: actual={actual_sha256}, expected={artifact.sha256}"
        )
    return path


def _load_semantic_quarantine_contract(
    manifest: Mapping[str, Any],
) -> SemanticQuarantineContract | None:
    triage = manifest.get("task_scam_mislabel_triage")
    if not isinstance(triage, Mapping):
        return None
    if "semantic_quarantine_contract" not in triage:
        return None
    try:
        return SemanticQuarantineContract.model_validate(
            triage["semantic_quarantine_contract"]
        )
    except ValidationError as exc:
        raise MislabelTriageError(
            f"semantic quarantine contract is invalid: {exc}"
        ) from exc


def _load_bound_row_artifact(
    repo_root: Path,
    artifact: SemanticQuarantineRowArtifact,
    *,
    context: str,
) -> list[dict[str, Any]]:
    path = _resolve_semantic_quarantine_artifact(
        repo_root, artifact, context=context
    )
    rows = read_jsonl(path)
    if len(rows) != artifact.records:
        raise MislabelTriageError(
            f"{context} row count mismatch: actual={len(rows)}, "
            f"expected={artifact.records}"
        )
    return rows


def _validate_semantic_quarantine_transition(
    candidate_dir: Path,
    paths: Mapping[str, Path],
    manifest: Mapping[str, Any],
    current_splits: dict[str, list[dict[str, Any]]],
    contract: SemanticQuarantineContract,
) -> dict[str, Any]:
    """Recompute and authorize the exact post-judge quarantine transition."""
    repo_root = _semantic_quarantine_repo_root(candidate_dir)

    source_manifest_path = _resolve_semantic_quarantine_artifact(
        repo_root,
        contract.source_candidate.manifest,
        context="semantic quarantine source manifest",
    )
    try:
        source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MislabelTriageError(
            f"semantic quarantine source manifest is invalid JSON: {exc}"
        ) from exc
    if not isinstance(source_manifest, dict):
        raise MislabelTriageError("semantic quarantine source manifest is not an object")

    source_splits: dict[str, list[dict[str, Any]]] = {}
    for descriptor in contract.source_candidate.splits:
        split_name = descriptor.split
        source_path = _resolve_semantic_quarantine_artifact(
            repo_root,
            descriptor,
            context=f"semantic quarantine source {split_name}",
        )
        if PurePosixPath(descriptor.path).name != f"{split_name}.jsonl":
            raise MislabelTriageError(
                f"semantic quarantine source {split_name} path has the wrong basename"
            )
        rows = [
            validate_dataset_record(
                row, context=f"semantic quarantine source {split_name}:{row_index}"
            )
            for row_index, row in enumerate(read_jsonl(source_path))
        ]
        if len(rows) != descriptor.records:
            raise MislabelTriageError(
                f"semantic quarantine source {split_name} row count mismatch"
            )
        try:
            manifest_entry = source_manifest["manifest"]["files"][f"{split_name}.jsonl"]
        except (KeyError, TypeError) as exc:
            raise MislabelTriageError(
                f"semantic quarantine source manifest lacks {split_name}.jsonl metadata"
            ) from exc
        expected_entry = {
            "sha256": descriptor.sha256,
            "records": descriptor.records,
            "bytes": source_path.stat().st_size,
        }
        if manifest_entry != expected_entry:
            raise MislabelTriageError(
                f"semantic quarantine source manifest mismatch for {split_name}"
            )
        source_splits[split_name] = rows

    source_stats = validate_candidate_splits(source_splits, enforce_locked_profile=True)
    if source_manifest.get("split_class_distribution") != source_stats[
        "split_class_distribution"
    ]:
        raise MislabelTriageError(
            "semantic quarantine source manifest class distribution mismatch"
        )

    quarantine_rows = _load_bound_row_artifact(
        repo_root,
        contract.quarantine_artifact,
        context="semantic quarantine artifact",
    )
    expected_quarantine_fields = {
        "source_split",
        "source_row_index",
        "record_digest",
        "record_identity",
        "reason",
        "record",
        "fresh_judge",
    }
    remove_coordinates: set[tuple[str, int]] = set()
    remove_digests: set[str] = set()
    remove_identities: set[str] = set()
    coordinate_order = {name: index for index, name in enumerate(SPLIT_NAMES)}
    artifact_coordinates: list[tuple[str, int]] = []
    for artifact_index, row in enumerate(quarantine_rows):
        if set(row) != expected_quarantine_fields:
            raise MislabelTriageError(
                f"semantic quarantine row {artifact_index} has wrong fields"
            )
        split_name = row["source_split"]
        row_index = row["source_row_index"]
        if split_name not in SPLIT_NAMES or type(row_index) is not int or row_index < 0:
            raise MislabelTriageError(
                f"semantic quarantine row {artifact_index} has invalid source coordinate"
            )
        coordinate = (split_name, row_index)
        if coordinate in remove_coordinates:
            raise MislabelTriageError(
                f"semantic quarantine repeats source coordinate {coordinate}"
            )
        if row_index >= len(source_splits[split_name]):
            raise MislabelTriageError(
                f"semantic quarantine source coordinate is out of range: {coordinate}"
            )
        if row["reason"] != SEMANTIC_QUARANTINE_REASON:
            raise MislabelTriageError(
                f"semantic quarantine row {artifact_index} has wrong reason"
            )
        record = validate_dataset_record(
            row["record"], context=f"semantic quarantine row {artifact_index} record"
        )
        source_record = source_splits[split_name][row_index]
        if record != source_record:
            raise MislabelTriageError(
                f"semantic quarantine row {artifact_index} does not equal its source record"
            )
        digest = record_digest(record)
        identity = record_identity(record["seed_id"], record["text"])
        if row["record_digest"] != digest or row["record_identity"] != identity:
            raise MislabelTriageError(
                f"semantic quarantine row {artifact_index} digest/identity binding failed"
            )
        if digest in remove_digests or identity in remove_identities:
            raise MislabelTriageError(
                f"semantic quarantine row {artifact_index} repeats a digest or identity"
            )
        try:
            evidence = SemanticQuarantineFreshJudge.model_validate(row["fresh_judge"])
        except ValidationError as exc:
            raise MislabelTriageError(
                f"semantic quarantine row {artifact_index} has invalid fresh judge: {exc}"
            ) from exc
        if (
            evidence.split != split_name
            or evidence.row_index != row_index
            or evidence.seed_id != record["seed_id"]
            or evidence.record_digest != digest
        ):
            raise MislabelTriageError(
                f"semantic quarantine row {artifact_index} fresh-judge binding failed"
            )
        remove_coordinates.add(coordinate)
        remove_digests.add(digest)
        remove_identities.add(identity)
        artifact_coordinates.append(coordinate)

    if artifact_coordinates != sorted(
        artifact_coordinates,
        key=lambda item: (coordinate_order[item[0]], item[1]),
    ):
        raise MislabelTriageError(
            "semantic quarantine rows must be ordered by source split and row index"
        )

    post_quarantine_pool = [
        record
        for split_name in SPLIT_NAMES
        for row_index, record in enumerate(source_splits[split_name])
        if (split_name, row_index) not in remove_coordinates
    ]
    expected_pre_cap_count = EXPECTED_OUTPUT_TOTAL - EXPECTED_SEMANTIC_QUARANTINE_ROWS
    if len(post_quarantine_pool) != expected_pre_cap_count:
        raise MislabelTriageError(
            f"semantic quarantine produced {len(post_quarantine_pool)} pre-cap rows, "
            f"expected {expected_pre_cap_count}"
        )

    capped, cap_stats = enforce_seed_cap(
        post_quarantine_pool, cap_pct=contract.cap_pct
    )
    expected_cap_drops = _derive_cap_drops(post_quarantine_pool, capped)
    for row in expected_cap_drops:
        row["reason"] = SEMANTIC_CAP_DROP_REASON
    if (
        len(expected_cap_drops) != EXPECTED_SEMANTIC_QUARANTINE_CAP_DROPS
        or cap_stats.get("rows_dropped_seed_cap")
        != EXPECTED_SEMANTIC_QUARANTINE_CAP_DROPS
    ):
        raise MislabelTriageError(
            "semantic quarantine recomputation did not produce exactly two cap drops"
        )
    cap_drop_rows = _load_bound_row_artifact(
        repo_root,
        contract.cap_drop_artifact,
        context="semantic quarantine cap-drop artifact",
    )
    if cap_drop_rows != expected_cap_drops:
        raise MislabelTriageError(
            "semantic quarantine cap-drop artifact differs from deterministic recomputation"
        )

    assignments = assign_stratified_group_split(
        capped,
        ratios=tuple(contract.split_ratios),  # exact length/value checked by the model
        salt=contract.split_salt,
    )
    recomputed_splits = {name: [] for name in SPLIT_NAMES}
    for record in capped:
        recomputed_splits[assignments[record["seed_id"]]].append(record)
    recomputed_stats = validate_candidate_splits(
        recomputed_splits, enforce_locked_profile=False
    )
    if recomputed_stats["total_rows"] != EXPECTED_POST_QUARANTINE_ROWS:
        raise MislabelTriageError(
            f"semantic quarantine candidate has {recomputed_stats['total_rows']} rows, "
            f"expected {EXPECTED_POST_QUARANTINE_ROWS}"
        )
    if contract.expected_profile != recomputed_stats:
        raise MislabelTriageError(
            "semantic quarantine expected_profile differs from recomputed profile"
        )

    for split_name in SPLIT_NAMES:
        if current_splits[split_name] != recomputed_splits[split_name]:
            raise MislabelTriageError(
                f"semantic quarantine candidate values differ for {split_name}"
            )
        expected_payload = encode_jsonl(recomputed_splits[split_name])
        if paths[f"splits/{split_name}.jsonl"].read_bytes() != expected_payload:
            raise MislabelTriageError(
                f"semantic quarantine candidate bytes differ for {split_name}"
            )

    triage = manifest["task_scam_mislabel_triage"]
    if manifest.get("split_class_distribution") != recomputed_stats[
        "split_class_distribution"
    ]:
        raise MislabelTriageError(
            "semantic quarantine manifest split_class_distribution mismatch"
        )
    split_governance = triage.get("split_governance")
    if not isinstance(split_governance, Mapping) or (
        split_governance.get("ratios") != list(SPLIT_RATIOS)
        or split_governance.get("salt") != SPLIT_SALT
        or split_governance.get("whole_seed_groups") is not True
        or split_governance.get("split_counts") != recomputed_stats["split_counts"]
        or split_governance.get("split_class_distribution")
        != recomputed_stats["split_class_distribution"]
    ):
        raise MislabelTriageError(
            "semantic quarantine manifest split_governance mismatch"
        )
    validation = triage.get("validation")
    if not isinstance(validation, Mapping) or any(
        validation.get(key) != value for key, value in recomputed_stats.items()
    ):
        raise MislabelTriageError(
            "semantic quarantine manifest validation profile mismatch"
        )
    expected_output_sha256 = {
        f"splits/{name}.jsonl": sha256_path(paths[f"splits/{name}.jsonl"])
        for name in SPLIT_NAMES
    }
    if triage.get("candidate_output_sha256") != expected_output_sha256:
        raise MislabelTriageError(
            "semantic quarantine manifest candidate_output_sha256 mismatch"
        )
    return recomputed_stats


def validate_staged_candidate(
    candidate_dir: Path,
    *,
    expected_payloads: Mapping[str, bytes] | None = None,
) -> dict[str, Any]:
    paths = _candidate_paths(candidate_dir)
    existing_files = {
        path.relative_to(candidate_dir).as_posix()
        for path in Path(candidate_dir).rglob("*")
        if path.is_file()
    }
    if existing_files != set(paths):
        raise MislabelTriageError(
            f"candidate file set differs (actual={sorted(existing_files)}, expected={sorted(paths)})"
        )
    if expected_payloads is not None:
        for key, path in paths.items():
            if path.read_bytes() != expected_payloads[key]:
                raise MislabelTriageError(f"existing candidate differs for {key}")

    splits = {
        name: read_jsonl(paths[f"splits/{name}.jsonl"])
        for name in SPLIT_NAMES
    }
    try:
        manifest = json.loads(paths["manifest.json"].read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MislabelTriageError(f"candidate manifest is invalid JSON: {exc}") from exc
    if not isinstance(manifest, dict):
        raise MislabelTriageError("candidate manifest is not an object")
    quarantine_contract = _load_semantic_quarantine_contract(manifest)
    if quarantine_contract is None:
        stats = validate_candidate_splits(splits)
    else:
        stats = _validate_semantic_quarantine_transition(
            candidate_dir,
            paths,
            manifest,
            splits,
            quarantine_contract,
        )
    for name in SPLIT_NAMES:
        payload = paths[f"splits/{name}.jsonl"].read_bytes()
        entry = manifest["manifest"]["files"][f"{name}.jsonl"]
        expected_entry = {
            "sha256": sha256_bytes(payload),
            "records": len(splits[name]),
            "bytes": len(payload),
        }
        if entry != expected_entry:
            raise MislabelTriageError(f"candidate manifest mismatch for {name}")
    decisions = read_jsonl(paths["phase39-mislabel-decision-manifest.jsonl"])
    quarantine = read_jsonl(paths["phase39-mislabel-quarantine.jsonl"])
    cap_drops = read_jsonl(paths["phase39-seed-cap-drops.jsonl"])
    if len(decisions) != 324 or len({row["candidate_number"] for row in decisions}) != 324:
        raise MislabelTriageError("candidate decision manifest is not exact 324 coverage")
    if len(quarantine) != 176:
        raise MislabelTriageError("candidate quarantine count is not 176")
    if len(cap_drops) != 33:
        raise MislabelTriageError("candidate seed-cap drop count is not 33")
    run = json.loads(paths["run.json"].read_text(encoding="utf-8"))
    if run.get("status") != "complete" or run.get("mode") != "stage_only":
        raise MislabelTriageError("candidate run descriptor is not complete stage-only")
    for key, digest in run.get("output_sha256", {}).items():
        if key == "audit_markdown":
            continue
        if key not in paths:
            raise MislabelTriageError(f"run descriptor names unexpected artifact {key}")
        if key == "run.json":
            raise MislabelTriageError("run descriptor must not self-hash")
        if sha256_path(paths[key]) != digest:
            raise MislabelTriageError(f"run descriptor hash mismatch for {key}")
    return stats


def _build_payloads(
    projection: Projection,
    existing_manifest: dict[str, Any],
    input_hashes: Mapping[str, str],
    protected_hashes: Mapping[str, str],
    git_provenance: Mapping[str, Any],
) -> tuple[dict[str, bytes], bytes]:
    split_payloads = {name: encode_jsonl(projection.splits[name]) for name in SPLIT_NAMES}
    decision_payload = encode_jsonl(_decision_manifest_rows(projection))
    quarantine_payload = encode_jsonl(projection.quarantine_rows)
    cap_drop_payload = encode_jsonl(projection.cap_drop_rows)
    manifest = build_candidate_manifest(
        existing_manifest,
        projection,
        split_payloads,
        decision_payload,
        quarantine_payload,
        cap_drop_payload,
        input_hashes,
        protected_hashes,
        git_provenance,
    )
    manifest_payload = (
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    ).encode("utf-8")
    split_hashes = {f"{name}.jsonl": sha256_bytes(split_payloads[name]) for name in SPLIT_NAMES}
    audit_payload = render_audit_markdown(
        projection,
        input_hashes,
        protected_hashes,
        split_hashes,
    )
    payloads: dict[str, bytes] = {
        **{f"splits/{name}.jsonl": split_payloads[name] for name in SPLIT_NAMES},
        "manifest.json": manifest_payload,
        "phase39-mislabel-decision-manifest.jsonl": decision_payload,
        "phase39-mislabel-quarantine.jsonl": quarantine_payload,
        "phase39-seed-cap-drops.jsonl": cap_drop_payload,
    }
    run = {
        "run_id": _run_id(input_hashes),
        "status": "complete",
        "mode": "stage_only",
        "input_sha256": dict(input_hashes),
        "protected_review_artifact_sha256": dict(protected_hashes),
        "output_sha256": {
            **{key: sha256_bytes(payload) for key, payload in payloads.items()},
            "audit_markdown": sha256_bytes(audit_payload),
        },
        "counts": {
            "decision_manifest": 324,
            "lineage_quarantine": 176,
            "seed_cap_drops": 33,
            "candidate_rows": 2_103,
        },
        "external_api_call_count": 0,
    }
    payloads["run.json"] = (
        json.dumps(run, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    return payloads, audit_payload


def _hash_map(paths: Mapping[str, Path]) -> dict[str, str]:
    missing = [str(path) for path in paths.values() if not Path(path).is_file()]
    if missing:
        raise FileNotFoundError(f"required input file(s) missing: {missing}")
    return {key: sha256_path(path) for key, path in paths.items()}


def _assert_hashes(
    actual: Mapping[str, str], expected: Mapping[str, str], *, context: str
) -> None:
    if dict(actual) != dict(expected):
        raise MislabelTriageError(
            f"{context} hash lock failed: actual={dict(actual)}, expected={dict(expected)}"
        )


def _stage_payloads(
    candidate_dir: Path,
    audit_output: Path,
    payloads: Mapping[str, bytes],
    audit_payload: bytes,
    *,
    verify_callback: Callable[[], None],
) -> bool:
    candidate_dir = Path(candidate_dir)
    audit_output = Path(audit_output)
    paths = _candidate_paths(candidate_dir)
    lock_path = candidate_dir.parent / f".{candidate_dir.name}.lock"
    with exclusive_run_lock(lock_path):
        existing_files = [path for path in candidate_dir.rglob("*") if path.is_file()]
        if existing_files:
            validate_staged_candidate(candidate_dir, expected_payloads=payloads)
            if not audit_output.is_file() or audit_output.read_bytes() != audit_payload:
                raise MislabelTriageError(
                    "existing candidate is complete but audit Markdown is absent or differs"
                )
            verify_callback()
            return True
        if audit_output.exists() and audit_output.read_bytes() != audit_payload:
            raise MislabelTriageError(
                f"audit output already exists with different bytes: {audit_output}"
            )
        destinations: dict[str, Path] = dict(paths)
        write_payloads: dict[str, bytes] = dict(payloads)
        originals: dict[str, bytes | None] = {key: None for key in paths}
        if not audit_output.exists():
            destinations["audit_markdown"] = audit_output
            write_payloads["audit_markdown"] = audit_payload
            originals["audit_markdown"] = None

        def verify_written() -> None:
            validate_staged_candidate(candidate_dir, expected_payloads=payloads)
            if audit_output.read_bytes() != audit_payload:
                raise MislabelTriageError("staged audit Markdown differs after write")
            verify_callback()

        replace_payload_bundle(
            destinations,
            write_payloads,
            originals,
            operation="Phase 39 mislabel candidate stage",
            verify_written=verify_written,
        )
        return False


def promote_candidate_bundle(
    candidate_dir: Path,
    splits_dir: Path,
    manifest_path: Path,
    *,
    verify_promoted: Callable[[], None] | None = None,
) -> None:
    """Rollback-capable promotion seam; intentionally not exposed by the CLI."""
    validate_staged_candidate(candidate_dir)
    candidate_paths = _candidate_paths(candidate_dir)
    destinations = {
        **{
            f"splits/{name}.jsonl": Path(splits_dir) / f"{name}.jsonl"
            for name in SPLIT_NAMES
        },
        "manifest.json": Path(manifest_path),
    }
    payloads = {
        key: candidate_paths[key].read_bytes()
        for key in destinations
    }
    originals = {
        key: path.read_bytes() if path.exists() else None
        for key, path in destinations.items()
    }

    def verify() -> None:
        for key, path in destinations.items():
            if path.read_bytes() != payloads[key]:
                raise MislabelTriageError(f"promoted destination differs for {key}")
        promoted = {
            name: read_jsonl(Path(splits_dir) / f"{name}.jsonl")
            for name in SPLIT_NAMES
        }
        validate_candidate_splits(promoted)
        if verify_promoted is not None:
            verify_promoted()

    replace_payload_bundle(
        destinations,
        payloads,
        originals,
        operation="Phase 39 candidate promotion",
        verify_written=verify,
    )


def run_stage(
    *,
    splits_dir: Path,
    manifest_path: Path,
    merged_judge_path: Path,
    decisions_path: Path,
    candidate_dir: Path,
    audit_output: Path,
    protected_review_paths: Mapping[str, Path],
    expected_input_sha256: Mapping[str, str] = EXPECTED_INPUT_SHA256,
    expected_protected_sha256: Mapping[str, str] | None = EXPECTED_PROTECTED_AUDIT_SHA256,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    input_paths = {
        **{f"{name}.jsonl": Path(splits_dir) / f"{name}.jsonl" for name in SPLIT_NAMES},
        "manifest.json": Path(manifest_path),
        "judge-merged.jsonl": Path(merged_judge_path),
        "MISLABEL triage.md": Path(decisions_path),
    }
    input_hashes = _hash_map(input_paths)
    _assert_hashes(input_hashes, expected_input_sha256, context="immutable input")
    protected_hashes = _hash_map(protected_review_paths)
    if expected_protected_sha256 is not None:
        _assert_hashes(
            protected_hashes,
            expected_protected_sha256,
            context="protected human-review artifact",
        )

    decisions = parse_triage_decisions(decisions_path)
    merged = read_jsonl(merged_judge_path)
    live_splits = load_live_splits(splits_dir)
    projection = build_projection(decisions, merged, live_splits)
    existing_manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    root = Path(repo_root) if repo_root is not None else Path(__file__).resolve().parents[2]
    git_provenance = _git_provenance(root)
    payloads, audit_payload = _build_payloads(
        projection,
        existing_manifest,
        input_hashes,
        protected_hashes,
        git_provenance,
    )

    def verify_immutable_inputs() -> None:
        _assert_hashes(_hash_map(input_paths), input_hashes, context="post-stage input")
        _assert_hashes(
            _hash_map(protected_review_paths),
            protected_hashes,
            context="post-stage protected artifact",
        )

    # Recheck immediately before the first output byte, then again inside the
    # bundle verifier so a concurrent input edit triggers full output rollback.
    verify_immutable_inputs()
    reused = _stage_payloads(
        candidate_dir,
        audit_output,
        payloads,
        audit_payload,
        verify_callback=verify_immutable_inputs,
    )
    verify_immutable_inputs()
    return {
        **projection.validation,
        "candidate_dir": str(Path(candidate_dir)),
        "audit_output": str(Path(audit_output)),
        "run_id": _run_id(input_hashes),
        "candidate_reused_without_rewrite": reused,
        "input_sha256_before_after": {
            key: {"before": digest, "after": _hash_map(input_paths)[key]}
            for key, digest in input_hashes.items()
        },
        "protected_sha256_before_after": {
            key: {"before": digest, "after": _hash_map(protected_review_paths)[key]}
            for key, digest in protected_hashes.items()
        },
        "promoted": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Stage the strict Phase 39 mislabel-triage candidate bundle."
    )
    parser.add_argument("--stage-only", action="store_true")
    parser.add_argument("--splits-dir", type=Path, default=Path("data/splits"))
    parser.add_argument(
        "--manifest-path", type=Path, default=Path("data/manifests/manifest.json")
    )
    parser.add_argument(
        "--merged-judge-path",
        type=Path,
        default=Path("data/processed/judge-merged.jsonl"),
    )
    parser.add_argument(
        "--decisions-path",
        type=Path,
        default=Path(
            ".planning/phases/39-independent-quality-re-judge/MISLABEL triage.md"
        ),
    )
    parser.add_argument(
        "--candidate-dir",
        type=Path,
        default=Path("data/processed/phase39-mislabel-candidate"),
    )
    parser.add_argument(
        "--audit-output",
        type=Path,
        default=Path(
            ".planning/phases/39-independent-quality-re-judge/39-MISLABEL-AUDIT.md"
        ),
    )
    args = parser.parse_args()
    if not args.stage_only:
        parser.error("this plan permits only --stage-only; promotion is deferred")
    phase_dir = args.decisions_path.parent
    protected = {
        "39-manual-review-sheet.md": phase_dir / "39-manual-review-sheet.md",
        "39-mislabel-triage-sheet.md": phase_dir / "39-mislabel-triage-sheet.md",
        "MISLABEL triage.md": args.decisions_path,
    }
    stats = run_stage(
        splits_dir=args.splits_dir,
        manifest_path=args.manifest_path,
        merged_judge_path=args.merged_judge_path,
        decisions_path=args.decisions_path,
        candidate_dir=args.candidate_dir,
        audit_output=args.audit_output,
        protected_review_paths=protected,
    )
    print(json.dumps(stats, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
